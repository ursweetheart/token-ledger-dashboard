## Context

Change này triển khai một đường onboarding Gateway-only trong cùng một change: cấu hình, ghi registry, tài khoản dịch vụ, định danh quan sát từ request, nạp lịch sử, API/UI, Docker và runbook. Đây là thiết kế để triển khai; các lệnh/file mới bên dưới chưa tồn tại.

### Bằng chứng đã kiểm ngày 24/09/2026

- `db/gen_catalog.py` tạo SQL từ billing/monitoring/app exports; `ranges[proj] if google else ranges['__ralli__']` không xử lý agent Gateway-only mới. Nó không kết nối database để áp dụng SQL.
- `db/load_org.py` tạo `svc.<code>` nhưng xóa `fact_usage_daily`, `fact_call`, `dim_function`, `dim_user`, `account`, `dim_unit` trước khi nạp. Không dùng đường này để thêm riêng agent.
- `db/load_gateway.py` chỉ tự đăng ký model. Nó tra agent theo tag; người gọi theo `connect.directory_account_lookup()`. Người lạ về neo và tăng `identity_unresolvable`.
- `account.username` UNIQUE toàn hệ thống; ID của `account`/`dim_agent` là INT không có default cấp số. Không thể đơn giản chèn `alice` cho hai app hay dùng MAX+1 ngoài transaction.
- Kiểm constraint trong database thật: `dim_agent.code` UNIQUE, `account.username` UNIQUE, `dim_user` PK `(agent_id,user_id)`; không có CHECK kind trên account trong snapshot. Namespace `gw:%` và kind `gateway_observed` hiện đều có 0 dòng. Vẫn phải kiểm xung đột ở lúc apply, không dựa vào snapshot này mãi mãi.
- `/api/accounts` chỉ trả `kind='real'`; adoption lấy mẫu số từ `dim_user.found_in='directory'`. `usage_by_account_resolved` không lọc kind và chọn nguồn riêng cho token/calls. UI vẫn có chỗ chỉ nhận `real` và coi số account là số người đã cấp.
- PostgreSQL đang chạy healthy; truy vấn READ ONLY trên `token_ledger_v2`: revision `012_nhip_tim_lam_moi`, 8 agents, 938 real accounts, 6 service accounts, 8 unattributed, 2 whole_agent. Chưa có `ref_model_catalog`.
- Source hiện có migration 013 tạo `ref_model_catalog`. `connect.rebuild()` gọi upgrade head trước rồi từ chối khi bảng này tồn tại. Kết luận về lần rebuild tiếp theo là suy luận từ code; KHÔNG chạy migration/rebuild trên database thật để thử.
- Snapshot cùng phiên: dashboard Gateway DMS 395 calls/50,991 tokens; CRM 105/183,429. Gateway DMS 397/51,031; CRM 105/183,429; other/missing tags 82/1,684. Chênh DMS 2 calls/40 tokens chưa xác định nguyên nhân, không gọi đó là lỗi identity và không dùng số này làm expected cố định trong test.
- Change `keep-a-person-visible-in-every-agent-they-use` đang dở và có chỉnh sửa chưa commit trong các file lookup. Giữ nguyên directory-only policy cho legacy agents; chính sách quan sát mới chỉ bật cho agent đăng ký qua registry mới.

## Goals / Non-Goals

**Goals:**

- Operator chỉ sửa `config/gateway-agents.yaml` ở phía dashboard rồi chạy lệnh apply; không sửa Python cho từng agent, không crawl, không cần billing/monitoring/users exports.
- Đăng ký được cả agent chưa gọi lần nào và agent có Gateway history; single/multiple có hành vi rõ, xem được usage trên dashboard.
- Không thay ID hoặc số liệu cũ; không tự gộp hai người trùng username ở hai agent; không giả danh bạ từ dữ liệu request.

**Non-Goals:**

- Không cấp key, sửa route, thực thi quota hoặc đổi giao thức AI request. Agent/Gateway vẫn chịu trách nhiệm tag và `X-User`.
- Không đồng bộ danh bạ/phòng ban, xác minh người thật, đếm nhân viên chưa từng gọi, hoặc liên kết danh tính xuyên agent.
- Không sửa pricing engine, bật lại full rebuild hay chuyển đổi hàng loạt 8 agent cũ.

## Decisions

### D1 — Một YAML là đầu vào vận hành, database là cấu hình đã áp dụng

Schema v1, strict keys/types, duplicate YAML keys là lỗi, không nội suy env/secret:

```yaml
version: 1
agents:
  - code: support-helper
    name: Trợ lý hỗ trợ
    user_mode: multiple
    reporting_start_date: "2026-09-24"
    active: true
  - code: batch-classifier
    name: Phân loại tự động
    user_mode: single
    reporting_start_date: "2026-09-24"
    active: true
```

- Required: code (lowercase ASCII letters/digits, hyphen-separated), nonblank name, user_mode enum, valid ISO date. active boolean defaults true. Không nhận agent_id từ operator; cấp trong DB.
- Single username luôn suy ra `svc.<code>`; không thêm một biến có thể lệch code. Identity source luôn Gateway với registry này, không thêm selector crawler.
- Agent mới: `gcp_project_id=NULL`, `has_google_source=false`, `has_org_tree=false`, `project_created_at=NULL`, `data_from=reporting_start_date`, `data_to=NULL`. Không bịa project hay ngày thành lập. Có thể bổ sung nguồn Google ở change khác.
- Ngày bắt đầu là ranh giới nạp/report cho agent mới theo giờ Việt Nam; chưa có traffic vẫn có ngày hợp lệ. Request trước ngày đó bị loại khỏi phạm vi có đếm riêng, không gọi là mất tag. Không suy ngày từ Ralli.
- code, user_mode và reporting_start_date bất biến sau đăng ký trong v1. name và active đổi được. Bỏ entry khỏi YAML không xóa/vô hiệu hóa agent: in cảnh báo retained; active=false đánh dấu ngừng hoạt động, không thu hồi key, không xóa hoặc chặn ghi log đến muộn.
- Lệnh mới `python scripts/apply_gateway_agents.py --config config/gateway-agents.yaml --dry-run` chỉ đọc/validate schema và database, không chạy migration, không ghi sequence/model/heartbeat. Bỏ `--dry-run` apply toàn file trong một transaction. Refresh đọc registry trong DB, không đọc YAML từng vòng; giữ hợp đồng refresh không phụ thuộc file chuẩn bị tay.
- Repo ship `version: 1; agents: []` (YAML nhiều dòng), example ở docs. Không tự áp một agent giả hay chuyển agent cũ lúc deploy.

### D2 — Đăng ký tăng dần, không gọi bulk loader

Migration sau head thực tế tại thời điểm apply tạo `gateway_agent_registry`: agent_id FK/PK, user_mode, reporting_start_date, config version/hash/applied time, trạng thái backfill. Code/name/active giữ ở dim_agent; registry xác định ownership.

Apply tạo đầy đủ unit kỹ thuật và account trước commit: single có một `service_account` làm neo; multiple có một `whole_agent` làm neo. Cả hai có một `unattributed` account. Không ghi observed users vào dim_user và không giả found_in='directory'. Đơn vị của multi observed là đơn vị kỹ thuật với nhãn chưa biết phòng ban, không phải một phòng ban thật.

Giữ INT PK hiện có, thêm allocator sequence cho agent/account trên database đang có và seed lớn hơn mọi ID hiện hữu. Unique constraints + transaction/advisory lock bảo vệ cạnh tranh. Nạp cũ dùng ID tự tính phải bị guard khi registry có dữ liệu, không được reset sequence. Test hai process apply/discover đồng thời; không dùng MAX+1 không khóa.

Nếu code đã có trong dim_agent nhưng chưa có registry, từ chối takeover và nêu ID bị trùng. Không silently thay policy của agent cũ. Nếu không có bảng registry (chưa migration), loader cũ tiếp tục legacy path; CLI apply yêu cầu migration trước, không tự upgrade.

`load_org.py`, `load_billing --rebuild`, `scripts/rebuild_db.py` và entrypoint gọi chúng phải dừng trước mutation/migration khi registry đã có dữ liệu. Không vô hiệu guard pricing. Generator vẫn là công cụ legacy, không được hướng dẫn là đường onboarding mới. Bộ guard này là phạm vi bảo vệ dữ liệu, không cải tạo toàn bộ pipeline crawl.

### D3 — Định danh request tách theo agent, không coi là danh bạ

Tạo `gateway_observed_identity` với PK `(agent_id, external_user_id)` và unique account_id FK, first_seen/last_seen UTC, raw display identity. Giữ external ID như trong log, phân biệt hoa/thường; trim chỉ để kiểm blank, không gộp `Alice` với `alice` bằng suy đoán. Agent phải gửi stable ID. Log raw user_id không bị ghi đè.

Account mới có `kind='gateway_observed'`, is_shared=1 (chưa xác minh là một người), full_name/email/role/is_enabled=NULL; account.username là khóa nội bộ namespace `gw:<agent_id>:<hex-utf8-external-id>`, raw external ID nằm ở mapping và dùng khi hiển thị. Encoding injective, không truncate/hash collision. Kiểm reserved namespace và identity length <=256 UTF-8 bytes, cấm control chars; log invalid phải đếm/fallback, không crash cả batch. Kiểm xung đột với account hiện hữu rồi fail, không nhận bừa.

Identity này chỉ là phát biểu của client được Gateway nhận, không phải danh tính đã được xác minh. Agent server đặt X-User từ người dùng đã đăng nhập; tag phải gắn với Virtual Key. Giữ nguyên quy tắc đúng một tag agent; không tự tạo agent từ tag bất kỳ. Không mở đường quản trị public.

Single: chỉ `svc.<code>` được nhận diện (quy tắc trim/lower tương thích service hiện tại); gửi tên người lạ không tạo account, tăng identity_unresolvable và gán neo. Multiple: identity hợp lệ mới được tạo tự động từ log có status success/failure được chấp nhận; first/last_seen dựa trên timestamp nguồn, không phải thời điểm chạy loader. Missing/blank/invalid dùng neo, giữ counter; cache duplicate/unknown/ambiguous tag bị loại trước khi discover. Lượt failure không biến thành usage thành công hay user hoạt động thành công.

Legacy agents tiếp tục dùng directory/service lookup hiện hữu. Không đổi rule directory-only, không merge gateway_observed với real dựa trên cùng chuỗi username. Đây là alternative được chọn thay cho bỏ UNIQUE toàn bộ account hoặc nhét observed thành real; hai cách đó phá KPI và lịch sử legacy.

### D4 — Nạp lịch sử, idempotency và khóa vận hành

Registry mới đánh dấu pending initial backfill. Lượt refresh kế tiếp đọc lịch sử còn giữ của agent từ reporting_start_date, bỏ qua global watermark đối với agent đó; agent khác giữ incremental overlap hiện tại. Chỉ clear pending khi load và tất cả rollups/heartbeat của cycle thành công. Nếu Gateway không kết nối được, giữ pending, báo lỗi, không báo zero thành công. CLI load trực tiếp không được tự clear pending của cycle.

Refresh giữ một session-level PostgreSQL advisory lock xuyên toàn bộ cycle và subprocess; apply dùng cùng lock để không xen thay registry giữa chừng. Lệnh load trực tiếp acquire lock nếu không ở supervised refresh. Cần triển khai ownership giữa parent/subprocess có kiểm chứng, hoặc gọi loader trong cùng process giữ lock; không cho subprocess xin lại cùng lock từ connection khác gây deadlock, không thêm cờ bypass lock tùy ý. Manual refresh khi worker đang giữ lock phải fail rõ hoặc skip có log, không chạy hai rollup song song. `--full` vẫn hỗ trợ replay; batch khám phá identity và chèn fact phải rollback cùng nhau khi lỗi. Model registration hiện có phải được rà transaction để dry-run và rollback không ghi ngoài ý muốn.

Fact trùng call_id không tự sửa account_id/unit_id lịch sử; change này không backfill lại identity của agent legacy. Agent registry mới chưa có fact trước đó vì code chưa được nhận; nếu gặp preexisting/conflicting ownership phải fail. Pending replay xử lý crash sau fact commit trước rollup bằng idempotency, không tăng count hoặc tạo account mới.

### D5 — API/UI riêng cho định danh đã quan sát, không làm adoption 100% giả

Thêm endpoint read-only `/api/gateway-identities`, cùng auth và connection role của API, filter agent/date, pagination; trả raw external ID, account_id, agent, kind/provenance, first/last seen. Bao gồm service identity single; không trả secret, email giả hoặc internal encoded username như tên người. Usage đọc đường account-resolved đã chọn nguồn cho token/calls; panel riêng có thể lấy chi phí Gateway từ fact_call với nhãn ước tính và quy tắc missing/failure hiện tại, không chia tiền Google cho từng user.

UI trong phạm vi agent hiển thị bảng 'Định danh qua Gateway', usage và fallback chưa quy được. Hiển thị agent chưa có call với trạng thái chưa có dữ liệu. `/api/accounts`, real-person counters và membership legacy không đổi. `/api/adoption` bổ sung provenance/denominator-known để UI hiển thị 'Chưa có danh bạ để tính tỷ lệ' cho multiple Gateway-only, không 0%/100% giả; mẫu số/tỷ lệ là NULL, số identity quan sát là metric riêng. Single vẫn biểu diễn tài khoản dịch vụ, không cộng vào nhân viên. Bộ lọc agent/ngày phải áp đồng nhất để tổng token/calls theo identity + fallback khớp resolved totals.

### D6 — Docker và một-file workflow

Thêm PyYAML vào dependency image tools với safe parser có duplicate-key rejection. Build image chứa module/CLI mới. Compose mount cả thư mục `./config:/app/config:ro` cho service chạy apply (dùng ledger-refresh làm one-off); không mount chỉ file để tránh atomic replacement giữ inode cũ. Refresh thường đọc DB, YAML không phải nguồn dữ liệu hoạt động bắt buộc.

Runbook sau khi triển khai và migrate trên môi trường đã duyệt:

```powershell
docker compose --profile refresh build ledger-refresh
docker compose --profile refresh stop ledger-refresh
docker compose --profile refresh run --rm ledger-refresh python3 scripts/apply_gateway_agents.py --config /app/config/gateway-agents.yaml --dry-run
docker compose --profile refresh run --rm ledger-refresh python3 scripts/apply_gateway_agents.py --config /app/config/gateway-agents.yaml
docker compose --profile refresh run --rm ledger-refresh python3 scripts/refresh_gateway.py
docker compose --profile refresh up -d ledger-refresh
```

Runbook phải nêu kiểm exit code từng bước; lỗi apply thì không chạy bước tiếp. Việc build/migrate chỉ cần khi nâng phiên bản, không mỗi lần thêm agent. Không dùng `gen_catalog.py`, `load_org.py`, `rebuild_db.py` trong workflow mới. Không sửa `SINGLE_USER_AGENTS` cho agent registry.

## Risks / Trade-offs

- Trùng local username giữa app → key theo agent, giữ riêng legacy real accounts; không hứa deduplicate nhân viên toàn công ty.
- Request headers sai/thiếu → counter + fallback; unknown agent không tự đăng ký. Quyền gán identity thuộc agent server, không coi header là xác thực người dùng.
- Legacy bulk loader xóa dữ liệu mới → preflight guard trước bất kỳ mutation; test snapshots trước/sau lệnh bị từ chối.
- Source/DB lệch migration 012/013 → diễn tập upgrade trên DB cách ly, kiểm pricing history và grants; không thử rebuild trên DB đang dùng.
- API/UI lọc mất kind mới hoặc tăng mẫu số adoption → tests cả backend và UI với fixtures 2 agents cùng `admin`, missing user, single service, no traffic.
- Chênh số liệu DMS nền chưa rõ → ghi evidence, không ép reconcile thành zero bằng sửa bộ lọc; kiểm hồi quy bằng baseline và fixture kiểm soát.
- Không có đủ Gateway retention để nạp lịch sử → thông báo phạm vi dữ liệu có thực; không hứa phục hồi call đã xóa khỏi nguồn.

## Migration Plan

1. Lưu baseline/backup theo vận hành trước rollout; chạy migration additive trên DB cách ly từ revision 012 và current head. Giữ row counts, IDs, financial values, pricing rows, API grants.
2. Ship migration/module/UI tương thích registry rỗng; deploy chưa tự đăng ký agent. Không thay đổi change danh bạ đang dở.
3. Diễn tập một single và hai multiple trên Gateway log fixture PostgreSQL cách ly (fake provider nếu cần full HTTP); không dùng real API key hoặc gọi model có phí.
4. Validate/apply YAML, chạy initial refresh/backfill, đối chiếu coverage và counters rồi bật lịch định kỳ.
5. Rollback vận hành: dừng worker mới, giữ schema/data; trước khi quay về reader cũ phải kiểm nó hiểu kind mới. Không drop mapping, không xóa account/fact. Đặt active=false chỉ đổi trạng thái hiển thị, không thu hồi Gateway key. Lỗi UI ưu tiên rollback UI hoặc tắt panel, không chạy bulk rebuild.

## Open Questions

- Chênh 2 calls/40 tokens DMS: chưa truy nguyên; là việc đo baseline, không phải blocker của contract mới.
- Chưa có hợp đồng định danh của agent mới cụ thể để xác nhận username có phân biệt hoa/thường; v1 bảo toàn exact external ID và yêu cầu sender ổn định, không tự gộp. Không cần export để vận hành. Đổi policy sau này cần migration riêng.
- Không còn lựa chọn sản phẩm chặn viết tasks: việc nhận identity chỉ áp cho registry mới; agent legacy muốn chuyển policy cần change migration riêng.

## Verification Record

Áp dụng `/tu-soat`: đọc lại contract rồi đối chiếu source và truy vấn READ ONLY toàn tập agents/account/Gateway counts. Đã sửa thiếu sót trong thiết kế về pending backfill, bảo vệ bulk loader, phân biệt observed với danh bạ và ownership khóa parent/subprocess. Không có code triển khai trong lượt propose nên chưa chạy thử tính năng, concurrency hay UI mới; các phép đó là tiêu chí tasks bắt buộc, không đánh dấu đạt trước. Không hạ ngưỡng để che dữ liệu nền lệch.

Ngày 24/09/2026, `openspec validate configure-gateway-agents-from-one-file --strict` đạt; `openspec status` báo proposal/design/specs/tasks đều done (apply-ready). Đây là hoàn tất artifacts, không phải hoàn tất implementation. Validator chỉ xác nhận cấu trúc, không chứng minh tính năng đã chạy. PostgreSQL healthy là container duy nhất cần cho đối chiếu hiện tại; không chạy migration, refresh hoặc gửi request AI trong lượt propose.
