## 1. Baseline và phối hợp change đang dở

- [ ] 1.1 Đọc lại proposal/design/specs và `/tu-soat`; ghi baseline source revision, DB revision, row counts/IDs/tổng theo nguồn, pricing/grants trên môi trường kiểm thử; không dùng số snapshot trong design làm fixture expected cố định.
- [x] 1.2 Đối chiếu working tree với `keep-a-person-visible-in-every-agent-they-use`; giữ lookup directory/service hiện có và tests chiều âm, không ghi đè thay đổi chưa commit của người dùng.
- [ ] 1.3 Chuẩn bị PostgreSQL dashboard + Gateway fixture cách ly; có legacy single, directory multi, hai usernames trùng giữa agent, failed/cache/missing tags, logs trước global watermark. Không dùng model thật có phí.

## 2. Schema và bảo vệ dữ liệu

- [x] 2.1 Thêm migration sau head thực tế cho gateway_agent_registry và gateway_observed_identity với FK/unique/check/index, ownership và pending backfill; không sửa migration cũ.
- [x] 2.2 Thêm allocator sequence an toàn cho agent/account, seed theo dữ liệu hiện hữu, cơ chế serialize cấp ID và kiểm namespace; xác minh không đổi ID/username legacy.
- [x] 2.3 Cấp quyền SELECT cho API role trên bảng mới theo chuẩn migration hiện hữu; Gateway DSN vẫn chỉ đọc, API không có quyền ghi.
- [x] 2.4 Thêm preflight guard trước mutation/migration cho load_org, connect.rebuild/load_billing --rebuild, rebuild_db và entrypoint bulk liên quan khi registry có dữ liệu; thông báo workflow mới.
- [x] 2.5 Test upgrade từ revision 012 và current head trên DB cách ly; kiểm toàn bộ IDs, facts, financial values, pricing rows và grants trước/sau; thử lệnh legacy bị chặn và xác minh không có mutation.

## 3. YAML và lệnh apply

- [x] 3.1 Thêm config/gateway-agents.yaml version 1 với agents rỗng, ví dụ single/multiple trong docs; khai dependency PyYAML và parser safe từ chối duplicate/unknown keys.
- [x] 3.2 Implement validation code/name/user_mode/date/active, giới hạn type rõ ràng, không secret/env interpolation; test file lỗi, duplicate codes, YAML null/boolean/date quirks và lỗi một entry không áp phần còn lại.
- [x] 3.3 Implement scripts/apply_gateway_agents.py --config và --dry-run: đọc schema/ownership, in diff, áp một transaction, tạo agent/unit/anchor/unattributed và pending backfill, không gọi generator/org/rebuild.
- [x] 3.4 Implement giữ nguyên agent khi bỏ entry, active=false vẫn giữ logs/history, name update; từ chối legacy takeover và đổi code ownership/user_mode/start_date; trả lỗi trước ghi.
- [x] 3.5 Test apply lặp, hai process cạnh tranh, lỗi giữa transaction; test dry-run bằng snapshot cả bảng và sequence; agent chưa có call không cần source files vẫn đăng ký được.

## 4. Identity từ Gateway request

- [x] 4.1 Implement resolve policy từ DB registry với legacy fallback khi registry chưa tồn tại/rỗng; không dùng YAML trong refresh và không nới directory-only cho legacy.
- [x] 4.2 Implement single service identity svc.<code>, giữ raw user_id, missing/invalid/mismatch counters và fallback; không tự tạo người thật trong single mode.
- [x] 4.3 Implement multiple discovery theo (agent_id, exact external_user_id), limit 256 UTF-8 bytes/control chars/blank, kind gateway_observed, namespace injective, unknown personal fields và first/last source timestamps.
- [x] 4.4 Đưa discovery sau xác định agent và loại duplicate/out-of-scope logs; discovery + facts atomic; review model auto-registration commit để không phá dry-run/rollback.
- [ ] 4.5 Test Alice/Bob, hai agent cùng admin, tên trùng legacy real, Alice khác alice, unicode/multibyte, whitespace-only, control chars, identity quá dài, failure-only, cache duplicate, unknown/multiple tags; assert account_id và counters bên cạnh token/tiền.
- [ ] 4.6 Test concurrent discovery, repeated replay và rollback sau tạo account; không orphan, không trùng và legacy regression tests vẫn giữ cùng kết quả.

## 5. Backfill và refresh

- [x] 5.1 Implement initial per-agent backfill bỏ qua global watermark, ranh giới reporting_start_date giờ Việt Nam, giữ overlap legacy và counter out-of-scope; không clear pending khi chỉ chạy loader trực tiếp.
- [x] 5.2 Thêm shared DB lock cho apply/direct load/full refresh cycle; giải quyết parent/subprocess ownership không deadlock hoặc bypass bằng cờ không kiểm chứng; second worker timeout/skip có log.
- [x] 5.3 Clear pending chỉ sau load/daily/hourly/performance/heartbeat thành công; test Gateway unavailable, crash sau facts commit và lỗi mỗi rollup rồi retry.
- [x] 5.4 Test whole replay không đổi account attribution cũ, count/token/cost không nhân đôi; initial request trước watermark vẫn vào, trước start_date không vào và được đếm riêng.
- [x] 5.5 Chạy refresh không có YAML/source exports trong worker; kiểm mọi rollup nhận dữ liệu mới, nguồn khác giữ nguyên, counters không bị nuốt trong loop.

## 6. API và giao diện

- [x] 6.1 Thêm read-only authenticated /api/gateway-identities với filters/pagination, raw display identity và provenance; nối service single và observed multiple, không lộ encoded username/key/PII suy đoán.
- [x] 6.2 Thêm bảng Định danh qua Gateway trong phạm vi agent, đồng bộ filters với usage; hiển thị fallback, no-traffic, inactive và failure-only đúng nghĩa, không bị bộ lọc kind=real loại mất.
- [x] 6.3 Bổ sung denominator-known/provenance cho adoption, hiển thị NULL/chưa biết với multiple Gateway-only; giữ real-person counters, /api/accounts và legacy membership không đổi.
- [x] 6.4 Kiểm tổng token và calls identity + fallback bằng resolved totals; chi phí Gateway nếu hiển thị lấy source đúng và có nhãn ước tính, missing khác zero; không sửa source precedence.
- [ ] 6.5 Test auth, pagination/filter boundary, unknown kind, duplicate external IDs khác agent, 10 observed không thành adoption 100%, single không thành nhân viên; chạy UI harness và kiểm trực quan với fixture khi triển khai.

## 7. Docker và hướng dẫn vận hành

- [ ] 7.1 Đóng gói CLI/module/dependency vào tools image, mount thư mục config read-only cho one-off apply; refresh không yêu cầu file hiện diện; test atomic save trên host được container đọc bản mới.
- [x] 7.2 Viết runbook một-file: migrate/build lần nâng cấp, sửa YAML, stop worker, dry-run, apply, one-shot refresh, kiểm exit/counters rồi up; tách rõ Gateway key/tag/X-User vẫn cấu hình phía Gateway/agent.
- [x] 7.3 Cập nhật docs/reference/noi-agent-vao-gateway-hai-phia.md, onboard-a-new-agent.md và gateway-connection-simple-english.md để bỏ chỉ dẫn gen_catalog/load_org/rebuild cho agent Gateway-only; giữ phần legacy có nhãn.
- [x] 7.4 Ghi quy tắc immutable fields, retained entries, active=false không thu hồi key, phạm vi retention, rollback giữ schema/data và không trộn observed với danh bạ.

## 8. Nghiệm thu toàn bộ theo tu-soat

- [x] 8.1 Đọc lại toàn bộ diff; chạy unit tests lát mỏng, phân loại lỗi test/script và phát hiện dữ liệu thật; sửa rồi đọc lại, không nới assertion cho qua.
- [x] 8.2 Chạy PostgreSQL integration suite đầy đủ từ migration đến YAML apply, single/two-multiple discovery, pending replay, locks, API và rollups; fixture không có Google/app exports.
- [ ] 8.3 Chạy một vòng container end-to-end với Gateway fake-provider/fixture, xác nhận tag + X-User đi vào end_user/mapping/UI; không gửi request trả phí hoặc ghi vào sổ thật.
- [ ] 8.4 Đối chiếu trước/sau toàn bộ legacy counts/IDs/tokens/costs, model pricing, grants và danh bạ; lưu các lệch nền có lượng hóa, không gọi dữ liệu chưa kiểm là đạt.
- [ ] 8.5 Chạy OpenSpec strict validation và bộ kiểm CI liên quan; ghi báo cáo bằng chứng, giới hạn còn lại và lệnh vận hành đã chạy thật trước khi đánh dấu implementation hoàn tất.
