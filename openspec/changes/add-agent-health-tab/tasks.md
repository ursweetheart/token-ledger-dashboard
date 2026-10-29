## 1. Database

- [x] 1.1 Viết `db/migrations/sql/016_agent_health.sql`: ba bảng theo design D6, index duy nhất có điều kiện trên run `queued`/`running`, gieo dòng setting `id = 1, run_at = '08:00'`, `GRANT SELECT, UPDATE ON agent_health_setting` và `GRANT SELECT, INSERT ON agent_health_run TO connection_admin`
- [x] 1.2 Thêm `db/migrations/versions/016_agent_health.py` theo khuôn `015_gateway_connections.py`
- [x] 1.3 Thêm `agent_health_setting`, `agent_health_run` vào `KEEP_ON_REBUILD` trong `db/connect.py`
- [x] 1.4 Chạy `tests/test_connect_migrations.py`; chạy migration trên database dev; kiểm `api_readonly` đọc được ba bảng; kiểm `INSERT` run thứ hai khi đã có run `queued` bị database từ chối; kiểm trên PostgreSQL thật rằng `claim_schedule` gặp run tay đang giữ thì `last_run_date` KHÔNG bị ghi, và `take_manual` không đổi `last_run_date`

## 2. Cấu hình

- [x] 2.1 Viết `config/agent-health.yaml` với khối Trợ lý ảo Ralli (design D3): `capabilities` + `llm`, `allow_post: [/ctda/v2/analyze]`, không có `gateway_tag`
- [x] 2.2 Thêm `RALLI_PARTNER_KEY=` vào `.env.example`, ghi chú: key do quản trị Ralli cấp, nên chỉ có quyền `action:ctda`

## 3. Service kiểm tra

- [x] 3.1 Viết `scripts/watch_agents.py`: nạp YAML, kiểm danh sách trắng POST và method khi khởi động; import `env`, `VN` từ `watch_gateway.py`
- [x] 3.2 Hàm đọc trường `a.b` và `list[key=value]`; ba loại điều kiện `equals`, `not_equals`, `days_until`; xếp mức `ok`/`warn`/`fail` theo D4; lý do lấy `title` + `detail` của `problem+json`, cắt 500 ký tự
- [x] 3.3 Vòng lặp 5 giây theo D2: ① nhận run `manual` đang chờ trước, ② rồi mới xét lịch, giữ chỗ + `INSERT` run `schedule` trong một transaction; một phép kiểm lỗi không dừng các phép khác, một vòng lỗi không giết vòng lặp
- [x] 3.4 Ghi tiến độ theo D9: `total` lúc bắt đầu, `current_label` trước mỗi phép kiểm, `done` sau mỗi phép kiểm, `status = done` + `finished_at` khi xong
- [x] 3.5 Lúc khởi động vòng lặp, chuyển mọi run `running` sang `interrupted` (không đụng run `queued`); `--once` không làm bước này
- [x] 3.6 Phép kiểm `gateway-log` tuỳ chọn theo `gateway_tag` qua `GATEWAY_DSN` (D5)
- [x] 3.7 Cờ `--once` (chạy ngay, bỏ qua giờ, báo rõ nếu đang có run khác) và `--dry-run` (in kết quả, không ghi DB, bỏ qua mọi `POST`)
- [x] 3.8 Viết `tests/test_watch_agents.py`: đọc trường, ba mức, 429 → `warn`, `clarification` → `fail`, thiếu biến key → `fail`, từ chối POST ngoài danh sách trắng, quyết định "đến giờ chưa" cho các trường hợp trong spec (UTC 01:00 = 08:00 VN, restart sau khi đã chạy, lỡ giờ), run tay đang chờ được chạy trước lịch, `INSERT` lịch thất bại thì `last_run_date` không bị ghi, run tay không đổi `last_run_date`
- [x] 3.9 Chạy `--once --dry-run` với Ralli thật (chỉ `GET /capabilities` được gọi); xem kết quả có khớp lần thử 29/10 không

## 4. Compose

- [x] 4.1 Thêm service `agent-health-watch` vào `docker-compose.yml` theo khuôn `gateway-watch`: profile `gateway`, `read_only`, `cap_drop: [ALL]`, không cổng, `PYTHONIOENCODING: utf-8`, `TOKEN_LEDGER_DSN` vai admin, `GATEWAY_DSN` vai chỉ-đọc, `RALLI_PARTNER_KEY`, mount `./config:/app/config:ro`
- [x] 4.3 Thêm `agent-health-watch` vào danh sách service của `scripts/dashboard.py start` (thiếu thì lịch không chạy và "Chạy ngay" nằm `queued` mãi; phát hiện lúc thử 29/10)
- [x] 4.2 Hỏi người dùng trước khi chạy lần thật đầu tiên (`--once` không dry-run gọi `POST /ctda/v2/analyze`); ghi kết quả câu hỏi thử vào `verification.md`

## 5. API

- [x] 5.1 Thêm hàm đọc vào `backend/store.py` và `GET /api/agent-health` vào `backend/main.py`: setting, run mới nhất đã xong cùng kết quả, run đang chờ/chạy nếu có
- [x] 5.2 Thêm `GET /api/agent-health/runs/{id}`: `status`, `done`, `total`, `current_label`, `started_at`, kết quả đã có; 404 nếu không có run
- [x] 5.3 Thêm `PUT /api/agent-health/schedule` vào `backend/connection_api.py` (router thứ hai, dùng chung `authorize()`), kiểm `HH:MM`, 422/403/503 theo spec
- [x] 5.4 Thêm `POST /api/agent-health/run` cùng router: `INSERT` run `manual` → 202 + `id`; vướng index duy nhất → 409 + `id` của run đang có; ghi `requested_by`
- [x] 5.5 Test API: giờ hợp lệ, 25:00 → 422, khoá dashboard → 403 (cả hai endpoint ghi), quản trị tắt → 503, bấm chồng → 409 kèm `id`

## 6. Giao diện

- [x] 6.1 Thêm nút tab "🩺 Sức khỏe Agent" và khung `<div class="tab-content" id="agent-health">` vào `web/index.html`
- [x] 6.2 Thêm `agentHealth()`, `agentHealthRun(id)`, `setAgentHealthSchedule()`, `startAgentHealthRun()` vào `web/js/api.js`
- [x] 6.3 Viết `web/js/agent-health.js`: `<input type="time">`, ô khoá quản trị chỉ giữ trong bộ nhớ, nút Apply, bảng ✅/⚠️/❌/⏳ kèm loại lần chạy, trạng thái "chưa có lần chạy nào" và "hôm nay chưa có kết quả"
- [x] 6.4 Nút "Chạy ngay" + thanh `<progress>`: hỏi `runs/{id}` mỗi giây, hiện %, `current_label`, số giây; tắt nút khi đang chạy; 409 thì theo dõi run đang có; mở tab khi có run dở thì hiện thanh ngay; xong thì ngừng hỏi và tải lại bảng
- [ ] 6.5 Mở dashboard thật: đặt giờ bằng Apply và xác nhận lịch chạy ở vòng kế tiếp; bấm "Chạy ngay" (hỏi người dùng trước, vì nó gọi `POST /ctda/v2/analyze`), xem thanh đi 0 → 50 → 100%, bấm lần hai khi đang chạy thì nút bị tắt; xác nhận `last_run_date` không đổi sau lần chạy tay

## 8. Kết quả JSON ở DB và tệp (người dùng chốt 29/10/2026)

- [x] 8.1 Migration 016: bỏ `agent_health_result`, thêm `agent_health_run.result jsonb`; bỏ khỏi `KEEP_ON_REBUILD`
- [x] 8.2 `watch_agents.py`: dựng tài liệu (`document`), ghi cột sau mỗi phép kiểm, ghi `result.json` nguyên tử khi xong; lỗi ghi tệp vào `limitations`
- [x] 8.3 YAML: `kind`, `app_url`, `test_identity` cho mỗi agent; `question`, `question_field`, `answer` cho case
- [x] 8.4 `store.py` dàn phẳng `result` thành `results` (tab không đổi); compose mount `./var/agent-checks`; `.gitignore` chặn `var/agent-checks/`
- [x] 8.5 Test: case giữ câu hỏi/response, health không giữ, body gửi đúng trường, tệp giống bản DB, mức agent là mức tệ nhất, không ghi được tệp vẫn xong
- [x] 8.6 Viết `docs/reference/agent-health-result.md` (khuôn đầu vào/đầu ra cho module chụp màn hình)
- [x] 8.7 Áp lại migration 016 trên DB dev (bỏ bảng cũ) và chạy lại script kiểm DB — hỏi người dùng trước
- [ ] 8.8 Chạy thật một lần, đọc `body` của câu hỏi Ralli, điền `answer:` trong YAML — hỏi người dùng trước (một câu LLM)

## 7. Hoàn tất

- [x] 7.1 Nâng `EXPECTED_PY` trong `.github/workflows/ci.yml` theo số test mới, kèm ghi chú mốc
- [x] 7.2 Viết `docs/reference/agent-health.md`: thêm agent mới thế nào, ba mức nghĩa là gì, "Chạy ngay" độc lập với lịch và mỗi lần bấm tốn một lần gọi LLM, vì sao thanh đứng ở 50%, chỉ chạy một bản service, token của lần kiểm tính cho tài khoản nào, rủi ro key `admin`
- [x] 7.3 Chạy toàn bộ test; dừng lại báo người dùng, không tự commit
