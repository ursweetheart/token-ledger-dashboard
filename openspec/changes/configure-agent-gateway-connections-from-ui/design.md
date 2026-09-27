## Context

Dashboard dùng FastAPI và HTML/JS; `backend/main.py` hiện xác thực bằng shared dashboard key và có development open mode, chưa có role người dùng. Registry đã có parser, transaction và operation lock trong `db/gateway_registry.py`; CLI apply không tự migrate. Compose mount config của refresh read-only. Gateway chạy hai instance với route YAML và key từ environment. Tài liệu gateway là mô tả snapshot, không phải kiểm chứng hệ thống đang chạy.

## Goals / Non-Goals

**Goals:** Cấu hình kết nối từ UI, áp dụng có revision và bằng chứng, bảo toàn dữ liệu và cô lập route theo agent, quản lý key an toàn.

**Non-Goals:** Deploy agent từ xa; editor YAML tùy ý; tạo Google Cloud project hoặc Google API key; sửa identity/ledger/quota semantics; chuyển agent legacy tự động; retry/fallback tự động trong agent.

## Decisions

### D1 — UI theo hồ sơ kết nối và trạng thái từng phần

Trang Kết nối agent có danh sách và wizard: thông tin → provider/model → quota → preview → apply → hướng dẫn agent → kiểm tra. Tách draft revision, applied revision, key state, verification state và reporting state. Code, user_mode, reporting_start_date giữ bất biến sau đăng ký theo registry v1. Chỉ agent mới hoặc agent thuộc registry được quản lý; legacy hiển thị read-only kèm giải thích.

Không dùng một cờ connected vì Gateway, agent và reporting có thể hoàn tất ở thời điểm khác nhau.

### D2 — Desired state trong DB, YAML là artifact triển khai

Migration additive tạo connection profile/revision, operation/stage và audit. Secret không lưu trong profile: chỉ opaque reference. Với agent được UI quản lý, DB là nguồn desired state; worker export registry YAML đầy đủ theo thứ tự ổn định và apply bằng parser/transaction hiện có. Giữ mọi entry không thuộc UI; không suy xóa từ entry vắng mặt.

Gateway vẫn nhận YAML qua renderer: giữ nguyên cấu hình global và route unmanaged, chỉ sửa route thuộc manifest ownership của UI. Trước apply so hash file/môi trường hiện tại với baseline: drift ngoài UI làm operation dừng và yêu cầu import/reconcile có preview, không tự ghi đè. CLI tiếp tục dùng được; thay đổi CLI vào agent managed là drift phải giải quyết. Chọn cách này thay vì cho UI và YAML độc lập cùng ghi vì cần một desired state rõ ràng.

### D3 — API quản trị và worker tách quyền

API mới dưới `/api/gateway-connections`: list/detail, save draft, preview, apply, operation status, issue/revoke key, verify, audit và config template. Mutation dùng expected revision và idempotency key; lỗi validation trả 422, conflict/drift trả 409, thiếu auth 401, thiếu quyền 403. Browser poll operation; request HTTP không giữ chờ recreate.

Thêm credential quản trị riêng xác thực phía server; dashboard key hiện tại không cấp quyền quản trị connection. Development open mode cũng không cho mutation. Audit actor là credential identifier, không giả tên người khi chưa có user auth. Credential quản trị chỉ ở memory browser, không lưu localStorage. API ghi qua role chuyên biệt; role đọc hiện tại giữ nguyên.

Worker nhận operation ID và schema allowlist, không nhận shell command/path tùy ý. FastAPI không mount Docker socket. Worker triển khai ban đầu là service vận hành trên host, dùng Compose trong thư mục cố định, file secret ngoài repo với ACL giới hạn; thay đổi secret ghi atomic và không chứa trong YAML/download/audit. Chỉ worker được đọc Google key và credential quản trị LiteLLM. Đây là thành phần tin cậy có quyền vận hành host; không coi allowlist là sandbox hệ điều hành.

### D4 — Apply là saga có checkpoint

Preview validate registry, alias/model từ catalog hiện có, positive RPM/TPM, secret reference, unique ownership, tag filtering và quota. Không gửi request AI, không cấp key hoặc ghi config. Apply khóa toàn deployment, kiểm revision/drift lại, lưu snapshot cấu hình/secret references, ghi candidate atomic, recreate lần lượt hai instance và kiểm health/revision/routing từng instance. Không báo thành công khi còn một instance cũ; rolling rollout có trạng thái riêng và không hứa zero downtime.

Sau Gateway healthy: apply registry với lock hiện có, export YAML và enqueue refresh theo khóa refresh hiện có. Cấp key/đặt quota là operation issuance riêng sau apply; applied không đồng nghĩa access-ready. Issuance dùng kênh RPC nội bộ xác thực đến worker, trả plaintext trực tiếp trong response đang chờ, không đặt plaintext vào operation DB/polling. Timeout hoặc crash phải reconcile bằng alias duy nhất theo operation, thu hồi key có kết quả nhận không rõ trước khi cho phép replacement; không tự cấp lại. Mỗi stage lưu checkpoint; resume đối chiếu trạng thái thực trước retry. Không giả một transaction chung cho Docker, LiteLLM và PostgreSQL.

Lỗi trước hoàn tất deployment phục hồi snapshot trên cả instance. Lỗi sau registry commit giữ lịch sử DB và khôi phục config nếu deployment phải abort; trạng thái failed/recovery-required chỉ rõ stage. Issuance lỗi sau deployment không rollback deployment thành công, nhưng phải thu hồi key tạo dở. Nếu phục hồi cấu hình hoặc thu hồi key không rõ kết quả, recovery-required khóa mutation tiếp theo đến khi operator xử lý. Key đã thu hồi không được tự kích hoạt lại.

### D5 — Secret, quota và vòng đời

Google key nhập là secret mới hoặc reference key chung; không tạo project/key Google. Tên environment do hệ thống sinh, agent code không thành shell/path. Không dùng wildcard; tag route và key khớp code; enable_tag_filtering bắt buộc. Key chung phải hiển thị rằng upstream project/quota dùng chung, dù log vẫn phân biệt agent.

Virtual Key chỉ trả ở response cấp mới cho admin và không xuất hiện ở list/audit/template. Nếu mất response, revoke key chưa nhận và cấp thay thế bằng operation riêng; không tái trả plaintext đã mất. Rotate cấp replacement và thu hồi key cũ bằng thao tác rõ; UI theo dõi từng bước. Chọn quota hữu hạn hoặc xác nhận unlimited rõ ràng; không diễn giải bỏ trống thành zero. Quota hiện có là trần spend tích lũy CỦA TỪNG KEY, không phải ngân sách cộng gộp agent/project. UI hiển thị quota/spend từng key; rotation phải yêu cầu chọn ngân sách key mới và cảnh báo overlap có hai hạn mức độc lập, không tự sao chép toàn ngân sách cũ. Hỗ trợ zero để chặn key. Unlimited cho key mới là không đặt quota_usd; chuyển key có quota sang unlimited cần adapter gỡ riêng trường quota_usd, giữ tags/metadata/audit, vì set_quota hiện chỉ nhận số. Không tạo quota engine khác. active=false không revoke key; disconnect thu hồi tất cả key managed đã biết, báo phạm vi unmanaged chưa kiểm chứng và giữ usage.

### D6 — Kiểm chứng có bằng chứng

Template chỉ chứa placeholder Virtual Key, endpoint theo ngữ cảnh Docker/host, alias, X-User đúng user_mode, hai network và hướng dẫn recreate. Nhắc agent server gán identity và giữ fallback/retry theo hợp đồng hiện có. UI không cam kết thay đổi app đã triển khai.

Verify thực hiện request nhỏ có operation correlation ID sau thao tác rõ ràng báo khả năng có phí. Admin nhập Virtual Key cho lần test; secret đi qua kênh worker xác thực, chỉ giữ trong memory trong lần gọi và không persist/log. Không dùng LiteLLM master key để giả kiểm tra quyền agent. Adapter phải xác minh correlation ID được image pin ghi lại hoặc ánh xạ sang request_id thực; không mặc định custom header tự trở thành request_id. Tra Gateway log theo ID, tag và route/provider reference không chứa secret; nếu log chưa có bằng chứng upstream thì kết quả inconclusive, không đoán từ answer. Sau refresh, đối chiếu fact_call.call_id (nguồn gateway) với request_id và agent, token/cost fields; missing cost được báo chưa đủ bằng chứng, không gán zero. Quota chat có thể trả HTTP 200 với câu thông báo: phải đọc bằng chứng quota_block/failure, không coi mọi 200 là AI success. Dùng timeout cấu hình và trạng thái pending; phân biệt verified, failed, inconclusive. Kết quả test do worker gửi chỉ là Gateway verified; External agent verified đòi request có correlation từ chính agent đã triển khai và bằng chứng identity tương ứng. Acceptance fixture gồm route sai tag và quota 429/chat 200; không tạo wrong-tag route trên production tự động.

### D7 — Đóng các khoảng trống tích hợp vận hành

Worker sinh Compose override ngoài repo, cố định service litellm-1/litellm-2 theo tên thực trong Compose, thêm env_file secret ngoài repo cho CẢ HAI instance và kiểm environment effective không in giá trị. Giữ environment explicit cũ vì Compose environment có ưu tiên hơn env_file; không dùng env_file để âm thầm override key legacy. Cập nhật entrypoint preflight để kiểm danh sách managed secret references ngoài các biến bắt buộc cũ; fixture/CI dùng dummy tương ứng. Snapshot/recovery bao gồm override, secret version và preflight manifest, không chỉ route YAML. Compose hiện bind mount từng file config; sau atomic replace phải recreate để container đọc inode mới.

Trong stage registry/export, worker giữ operation_lock hiện có xuyên suốt re-read DB, drift validation, apply transaction và YAML export; deployment lock lấy trước registry lock theo thứ tự cố định. Không gọi CLI con trông đợi ContextVar truyền qua process. Phát hiện DB name/active đổi qua CLI cũng là drift. Route/secret changes của admin ngoài worker cần quy trình vận hành phối hợp; hash không phải khóa chống mọi chỉnh sửa ngoài hệ thống.

Admin credential dùng Authorization Bearer, so bytes bằng compare_digest, gắn với backend origin đã xác nhận; đổi ?api= không được chuyển secret cũ. Feature bật mà thiếu credential/worker/secret config phải fail closed. Profile thêm quota_response_mode=batch/chat, độc lập single/multiple; renderer cập nhật QUOTA_CHAT_TAGS giữ tag unmanaged. Budget adapter merge metadata giữ tags và tránh race với màn hình quota cũ: lưu baseline metadata, read-after-write, kiểm conflict; v1 yêu cầu single operator, không tuyên bố CAS xuyên LiteLLM khi API chưa hỗ trợ.

## Risks / Trade-offs

- Quyền vận hành host lớn → worker riêng, allowlist, ACL, không shell đầu vào, audit; review deployment trước bật feature.
- DB/files/LiteLLM không atomic → lock, revision/hash, checkpoint, recovery-required và diễn tập lỗi từng stage.
- LiteLLM version/API/log fields khác snapshot → xác minh adapter với image được pin trong repo trên môi trường cách ly; thiếu bằng chứng phải inconclusive.
- Key chung không cô lập quota Google project → thông báo rõ trong UI, chọn dedicated reference nếu cần cô lập upstream.
- Credential chung không xác định cá nhân → audit theo credential identifier; user RBAC để change khác.

## Migration Plan

1. Kiểm hợp đồng registry/quota và khả năng key API của image pin; diễn tập trên Compose/DB cách ly với fake provider.
2. Additive migration và grants riêng; triển khai API/UI/worker dưới feature flag mặc định tắt, không import legacy tự động.
3. Bootstrap ownership/baseline config read-only; diễn tập một agent mới single và multiple, drift, concurrency, restart và rollback.
4. Bật quản trị sau cấu hình credential/secret directory/worker; operator preview/apply từng agent, giữ baseline usage/pricing.
5. Rollback phần mềm bằng tắt feature và worker, giữ schema/history/config đang hoạt động; rollback cấu hình là operation phục hồi có kiểm chứng, không rebuild/drop dữ liệu.

## Open Questions

- Endpoint Gateway từ host và Docker phải lấy từ deployment thực, không hardcode hostname theo snapshot.
- Xác nhận trường log nào chứng minh provider route cho image pin; task đầu tiên phải đóng câu hỏi này hoặc giữ verification inconclusive cho phần không có bằng chứng.
- Chưa kiểm Gateway đang chạy hoặc chạy test trong lượt propose; validator chỉ xác minh artifacts.
