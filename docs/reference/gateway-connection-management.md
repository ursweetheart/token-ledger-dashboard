# Quản trị kết nối Gateway

Feature mặc định tắt. UI nằm trong tab Kết nối agent; tab Setting giữ phần hạn mức. Đây là hệ thống có worker vận hành Docker trên host; API web không cần Docker socket. Quota là trần spend tích luỹ từng Virtual Key, không cộng gộp theo project. Chỉ vận hành một operator khi có màn hình quota cũ cùng sửa metadata.

Để setup và chạy trên Windows/Linux, dùng [hướng dẫn setup chung](dashboard-setup.md): `python scripts/dashboard.py setup` một lần, sau đó `python scripts/dashboard.py start`. Git Bash và Linux Bash dùng được `bash start-dashboard.sh`.

## Kiểm thử cách ly

`tests/gateway-connections/compose.yaml` có project cố định `gateway-connections-test`, PostgreSQL ở loopback 55439, hai LiteLLM pin ở 4401/4402 và provider giả trong network internal. Không load `.env` production. Dùng một database ledger riêng `connection_ledger_test` trên server fixture, apply migrations ở đó; không migrate database `connection_test` mà Prisma đang quản lý.

```powershell
docker compose -f tests/gateway-connections/compose.yaml up -d
python tests/gateway-connections/setup_ledger.py
python tests/gateway-connections/probe.py
$env:CONNECTION_TEST_DSN='postgresql://connection_test:isolated-test-only@127.0.0.1:55439/connection_ledger_test'
python -m pytest tests/connection_config_cases.py tests/connection_auth_cases.py tests/connection_admin_cases.py tests/connection_migration_cases.py -q
```

Chờ `/health/liveliness` của cả hai instance trước probe. Shutdown bằng `docker compose -f tests/gateway-connections/compose.yaml down`; chỉ xóa volume fixture nếu không cần evidence nữa.

## Cấu hình triển khai

1. Backup dữ liệu/cấu hình rồi apply migration additive 015 vào ledger bằng quy trình migration hiện có. Không chạy rebuild, gen_catalog hoặc load_org. Tạo login riêng, cấp membership `connection_admin` cho API; role này không được ghi ledger facts. Worker dùng credential có quyền registry/ingest phù hợp, giữ riêng trên host.
2. Tạo thư mục secret **ngoài repo**, giới hạn ACL cho tài khoản chạy worker. Trên Linux dùng thư mục mode 0700 và umask 077. Trên Windows dùng `icacls` với đường dẫn tuyệt đối đã kiểm tra: bỏ inheritance, chỉ cấp quyền tài khoản worker và SYSTEM. Không đặt key trong command history; nạp từ secret manager/file ACL hoặc hộp nhập mật khẩu. File snapshot có secret nên cũng phải nằm trong thư mục hạn chế.
3. Đặt cấu hình worker: `CONNECTION_REPO_ROOT`, `CONNECTION_SECRET_DIR`, `CONNECTION_WORKER_DSN`, `CONNECTION_GATEWAY_DSN`, `CONNECTION_GATEWAY_ENDPOINTS` (hai URL riêng của instance, cách nhau dấu phẩy), `CONNECTION_GATEWAY_MASTER_KEY`, `CONNECTION_HOST_ENDPOINT`, `CONNECTION_DOCKER_ENDPOINT`, `CONNECTION_DOCKER_NETWORK`, `CONNECTION_WORKER_KEY`. Network và endpoint lấy từ deployment thật. Không dùng master key như Virtual Key trong agent.
4. `python scripts/connection_worker.py bootstrap` ghi baseline/ownership rỗng; không thay route/registry. Agent legacy và route không owned không được tự import. `python scripts/connection_worker.py serve` chạy loopback RPC 8766 và consumer. Nếu API ở container/host khác, đặt TLS reverse proxy tới loopback RPC; không mở RPC HTTP ngoài loopback.
5. API cần `CONNECTIONS_ENABLED=1`, `CONNECTION_ADMIN_KEY` khác DASHBOARD_KEY, `CONNECTION_ADMIN_DSN`, `CONNECTION_WORKER_URL`, `CONNECTION_WORKER_KEY`. Credential quản trị không lưu localStorage; đổi backend yêu cầu nhập lại. Feature bật thiếu config sẽ từ chối khởi động. Container API chỉ nhận config API/DSN, không mount secret directory hoặc Docker socket.

Worker đọc Compose trong root cố định, sinh override ngoài repo cho `litellm-1` và `litellm-2`, thêm env_file chứa key managed và quota chat tags. Những lệnh vận hành Gateway sau đó phải dùng **cùng override**; deploy chỉ base Compose sẽ mất key managed và bị phát hiện drift/health failure. Các biến legacy explicit trong Compose vẫn ưu tiên hơn env_file. Không sửa environment bằng API path tùy ý.

## Luồng quản trị

- Nhập mã/tên/user mode/ngày báo cáo; import Google key để nhận opaque reference hoặc tái dùng reference đã có. Chọn upstream trong catalog/model đã deploy. Lưu draft rồi preview. Preview không cấp key, không gọi provider, không ghi cấu hình.
- Review preview rồi apply. Theo dõi riêng draft/applied revision, deployment và reporting. Worker cập nhật hai instance, kiểm config/env/health, đăng ký DB bằng registry lock, export YAML và chạy refresh ngoài lock subprocess. Applied chưa có nghĩa agent đã nhận key.
- Cấp Virtual Key riêng sau apply, chọn ngân sách key rõ ràng và copy response ngay. Rotate là cấp replacement rồi thu hồi key cũ khi agent đã đổi cấu hình; overlap có hai budget độc lập. Zero chặn key; unlimited gỡ riêng quota_usd và giữ tags.
- Hướng dẫn host/Docker chỉ là mẫu. Áp dụng endpoint/key/model/X-User vào agent server, giữ network default cùng gateway và recreate container.
- Test Gateway cần Virtual Key thật nhập transient và chấp nhận khả năng có phí. Worker không lưu key thử và không retry request billable. Kết quả pending chờ log/ledger tối đa 60 giây, sau đó inconclusive nếu thiếu bằng chứng. Gateway verified không tự chứng minh external agent đã triển khai.

## Drift và phục hồi

File/YAML/môi trường hoặc DB registry thay đổi ngoài worker làm preview/apply conflict. Reconciliation có hai bước qua endpoint `POST /api/gateway-connections/{code}/reconcile`: trước lấy review_hash với expected_revision, sau gửi lại accept_hash. Review nêu baseline cũ, hashes quan sát và registry/draft. Acknowledge không cấp ownership cho route unmanaged; nếu cần takeover agent/route legacy phải dùng change migration riêng. Sau acknowledge vẫn phải preview desired UI settings trước apply, vì name/active từ CLI có thể khác bản nháp.

`recovery-required` khóa mutation mới. Endpoint `POST /api/gateway-connections/{code}/recover` nhận expected_revision/idempotency_key, phục hồi snapshot trên cả instance hoặc xác minh thu hồi key lỗi. Không xóa registry/history đã commit. Không tự kích hoạt lại key đã revoke. Nếu recovery tiếp tục lỗi, giữ khóa và kiểm worker/Compose/ACL ở host; không rebuild để làm phép kiểm qua.

Mất issuance response: operation có alias xác định từ UUID. Không resend với idempotency key mới một cách mù; kiểm trạng thái, thu hồi key chưa nhận rồi tạo replacement. Polling/audit không trả plaintext. Sau worker crash lúc issuance, reconcile alias và revoke trước khi cấp lại. Trước shutdown hoặc đổi trình duyệt, lưu key vào secret store của agent.

## Hợp đồng image đã đo

Image `b7657e95b1650f75551404f62e134ae54dfc5740`:

- `/key/generate` nhận key_alias/models/metadata.tags; `/key/delete` nhận key_aliases.
- `/key/update` thay metadata nên phải merge giữ tags; quota 0 trên key batch nhận HTTP 429 ở instance thứ hai.
- Response chat có `x-litellm-call-id` và `x-litellm-model-id`. Trong fixture, call header ID nằm ở log `metadata.litellm_call_id`, còn log `request_id` là ID response provider; hai giá trị khác nhau. Ledger `fact_call.call_id` nhận log request_id.
- Log xuất hiện sau flush; không mặc định log đã sẵn khi HTTP response về. Header route ID cùng deployment revision là bằng chứng route; không suy Google project từ một answer thành công. Quota chat HTTP 200 không có call/route header trong fixture; worker nhận diện đúng thông báo hook để báo quota-blocked, không gắn nhầm request_id với response chat ID.

Đối chiếu request external qua UI yêu cầu request_id. Image pin hiện không giữ đủ provider-route và origin evidence trong SpendLogs, nên sau khi xác nhận tag/identity, kết quả vẫn inconclusive. Request do worker tạo bị nhận diện riêng và không được dùng để báo external-agent verified. Không có phép kiểm nào nới tiêu chí để biến thiếu bằng chứng thành success.

Tắt feature/worker là rollback phần mềm; giữ schema, audit, registry và usage. Rollback cấu hình là operation có snapshot và kiểm chứng, không chỉ rollback UI.
