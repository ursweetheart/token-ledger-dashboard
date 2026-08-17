## 1. Chuẩn bị và chốt mốc đối chiếu

- [ ] 1.1 Xác nhận `git status` sạch trên `db/`, `scripts/`, `backend/` để quay lui được từng bước
- [ ] 1.2 Xác nhận `docker compose ps` cho thấy `token-ledger-postgres` là `Up (healthy)`
- [ ] 1.3 Ghi lại 8 con số mốc từ SQLite hiện tại qua view `usage_resolved` (1.161 dòng · input 539.827.701 · output 87.459.865 · cached 227.679.097 · total 851.897.312 · 285,18 USD · khoảng 2026-01-01→2026-08-13 · nguồn billing 942/app 164/monitoring 45/NULL 10) vào file tạm để đối chiếu ở nhóm 4
- [ ] 1.4 Xác nhận `python -m pytest` hoặc phép kiểm tương đương của `db/` (nếu có) và `node --test tests/date-range-filter.test.js` đang xanh

## 2. Sửa mã: một nguồn sự thật về DSN

- [x] 2.1 `db/connect.py`: thêm `import os`; dựng `DEFAULT_DSN` từ `PGHOST`/`PGPORT`/`PGUSER`/`PGPASSWORD`/`PGDATABASE` với mặc định khớp `docker-compose.yml`, và cho `TOKEN_LEDGER_DSN` ưu tiên cao nhất
- [x] 2.2 `db/connect.py`: cập nhật docstring — SQLite từ mặc định thành đường ghi đè để đối chiếu; giữ nguyên đoạn giải thích vì sao `01_schema.sql` chạy được cả hai hệ
- [x] 2.3 `db/connect.py`: thêm `mask_dsn(dsn)` che mật khẩu, giữ nguyên chuỗi khi DSN là đường dẫn file
- [x] 2.4 `scripts/rebuild_db.py`: thêm `sys.path.insert` + `import connect` theo khuôn `scripts/audit_db.py`; đổi `default=` của `--db` sang `connect.DEFAULT_DSN`
- [x] 2.5 `scripts/rebuild_db.py`: xoá hàm `che()` cục bộ, gọi `connect.mask_dsn()`; cập nhật docstring dòng 3-4 cho đúng mặc định mới
- [x] 2.6 `db/load_billing.py:67`: che mật khẩu trong dòng in `args.db`
- [x] 2.7 Tìm toàn bộ mã nguồn (`db/`, `scripts/`, `backend/`, `tools/`) xác nhận không còn chỗ nào dựng chuỗi kết nối mặc định riêng hay in DSN thô
- [x] 2.8 `backend/requirements.txt`: sửa ghi chú đang nói `psycopg2` là tuỳ chọn — nay bắt buộc
- [x] 2.9 `scripts/merge_billing.py`: **phát hiện khi soát ở 2.7** — nó gọi `sqlite3.connect()` trực tiếp trong `project_id_trong_dim_agent()`, nhận `Path` chứ không nhận DSN, và `dung()` nếu không thấy file. Là bước `[6/10]` nên xoá SQLite sẽ làm vỡ đường ống. Đã đổi sang `connect.open_db()`, giữ chế độ chỉ-đọc ở mức máy chủ, và bỏ hằng số `DB_MAC_DINH`
- [x] 2.10 Kiểm `mask_dsn` bốn trường hợp (đường dẫn file giữ nguyên · ẩn mật khẩu · giữ user/host/port/db · không để lộ mật khẩu) và bốn mức ưu tiên DSN (mặc định · `TOKEN_LEDGER_DSN` · `PG*` · chuỗi rỗng rơi về mặc định)
- [x] 2.11 Kiểm 4 script đã sửa vẫn import được (`--help` chạy hết phần import)

## 3. Chứng minh đường ống dựng thẳng vào PostgreSQL

- [x] 3.0 Xác định lại **cái gì thật sự chưa được chứng minh**: `scripts/copy_to_postgres.py:183` đã chạy `01_schema.sql` trên Postgres rồi, nên schema KHÔNG phải phần chưa test. Phần chưa từng chạy là **7 bước `load_*`/`build_*`** với `--db` trỏ vào Postgres
- [x] 3.1 Giữ nguyên `var/token_ledger.sqlite` làm mốc đối chiếu (chưa xoá)
- [x] 3.2 Dựng database tạm **rỗng** `token_ledger_rebuild` trong cùng container, tách hẳn khỏi `token_ledger` đang chạy — nếu đường ống hỏng thì không mất gì
- [x] 3.3 **Lát mỏng trước**: `connect.rebuild()` trên database rỗng → 18/18 bảng, 3/3 view, danh mục nạp đủ (dim_agent 8 · dim_model 10 · ref_price 10 · ref_budget 7 · ref_fx 1 · 44+44 alias)
- [x] 3.4 **Bản đầy đủ**: `PGDATABASE=token_ledger_rebuild python scripts/rebuild_db.py` — cả 7 bước NGHIEM THU DAT, mã thoát 0, xong sau **56s**, không bước nào cần `--from-step`
- [x] 3.5 Không có bước nào hỏng vì khác biệt SQL — `01_schema.sql` và cả 7 module nạp chạy được trên PostgreSQL không sửa dòng SQL nào
- [x] 3.6 Xác nhận đích in ra là Postgres và **mật khẩu đã được che** (`postgresql://token:***@127.0.0.1:5432/...`)

## 4. Nghiệm thu bằng số

- [x] 4.1 Đối chiếu 8 mốc trên database vừa dựng qua view `usage_resolved` — **8/8 KHỚP**. Thêm phép so chính xác tuyệt đối với `token_ledger`, gồm cả `cost_usd` thô: `285.181995` cả hai bên
- [x] 4.2 18/18 bảng khớp từng dòng, 3/3 view có mặt
- [x] 4.3 `audit_db.py` trên database vừa dựng: **30 phép kiểm · 26 đạt · 4 lưu ý · 0 hỏng**. Chạy trên cả hai database rồi so hash toàn bộ đầu ra: **giống nhau từng byte** (`a6f9982d…`), kể cả chi tiết 4 lưu ý — nên không lưu ý nào là mới
- [x] 4.4 Đã gọi cả 11 hàm `backend/store.py` trên Postgres ở bước khảo sát: không hàm nào ném lỗi, số dòng khớp đủ
- [x] 4.5 Kiểm JSON qua **HTTP thật** (không qua `jsonable_encoder`): cả 6 cột số trong JSON thô là **số**, không dấu ngoặc kép; tổng `ti+to+cached` trên 93 dòng ra `int`
- [x] 4.6 Ghi lại chênh lệch `units.is_technical` (`true` trên Postgres, `1` trên SQLite) vào `docs/reference/mo-ta-database.md`, kèm cảnh báo không so bằng `=== true` — xem 7.7
- [x] 4.8 Chạy **chính `web/js/api.js`** trong Node nối vào backend Postgres — lớp dịch cho ra đúng con số `app.js` sẽ hiện: **10/10 phép kiểm khớp**, mọi kiểu là `number`
- [x] 4.9 Hai chỗ lệch tìm ra ở 4.8 đã phân loại, **không nới phép kiểm nào**:
  - `cached` 224.609.584 (không phải 227.679.097) — **mốc tôi đặt sai**. `api.js:157` cố ý chỉ chuyển tiếp `cached` khi nguồn là `billing`; `app` có 3.069.513 token cached là TẬP CON của prompt_tokens nên cộng vào là đếm hai lần. 224.609.584 khớp đúng `db/01_schema.sql:380`
  - `total` lệch 162 — **phát hiện thật**, khoanh vùng: đúng 23 dòng, model `gemini-2.5-flash-lite`, nguồn `app`; chính app báo `total` khác `prompt+completion`, bước `build_usage_daily` cũng báo. Giống nhau trên cả hai hệ quản trị → không do đổi Postgres. Đã **ghim thành phép kiểm riêng** để nếu con số đổi thì biết ngay
- [x] 4.7 Xoá database tạm — còn lại đúng `token_ledger` (186 MB) trong container

## 4b. Vòng lặp tự soát trên chính change này (17/08)

- [x] 4b.1 Đọc lại toàn bộ diff bằng mắt trước khi kết luận xong
- [x] 4b.2 **Lỗi tự tìm ra #1:** `mask_dsn` cắt ở `@` **đầu** nên mật khẩu chứa `@` bị lộ một phần — `u:p@ss` làm đoạn `ss` chảy sang vế host rồi in nguyên văn. Sửa sang `rsplit("@", 1)`; thêm nhánh không chèn `:***` khi DSN vốn không có mật khẩu. Bản `che()` cũ trong `rebuild_db.py` có đúng lỗi này
- [x] 4b.3 **Lỗi tự tìm ra #2:** `rebuild_db.py` đưa DSN lên **dòng lệnh** của 7 tiến trình con → mật khẩu nhìn thấy được qua `ps`/Task Manager. Rủi ro này do chính việc đổi sang Postgres tạo ra. Chuyển sang truyền qua `TOKEN_LEDGER_DSN` trong `env`
- [x] 4b.4 Kiểm `mask_dsn` **6 ca biên**: đường dẫn file · mật khẩu thường · mật khẩu có `@` · nhiều `@` · không có mật khẩu · mật khẩu có `:`. 6/6 đúng, và không ca nào để lộ ký tự nào của mật khẩu
- [x] 4b.5 Chạy lại **bản đầy đủ** qua đường mới, trỏ `--db` vào database **khác mặc định** (không thì phép kiểm đạt oan vì con tự suy ra đúng database đó từ `PG*`): 7/7 bước đạt trong 61s, `Dich:` in ra `token:***`, grep `token_local` không khớp dòng nào
- [x] 4b.6 Đối chiếu lại: 18/18 bảng · 8/8 mốc · `285.181995` · 8/8 agent lệch +0
- [x] 4b.7 Dọn database tạm — còn lại đúng `token_ledger`
- [x] 4b.8 Hồi quy: 5/5 script import · test frontend 6/6 · `audit_db.py` 0 hỏng

## 5. Nghiệm thu bằng mắt

- [x] 5.1 Chạy `python -m uvicorn backend.main:app --port 8000` không đặt biến môi trường nào — nối vào Postgres, `/api/health` trả lời
- [x] 5.2 Đã soát **cả 6 tab** trên trang thật qua Chrome: Tổng quan · Phòng ban & User · Agents · Provider & Model · Chi phí · Hiệu năng. Mọi tab vẽ đủ, không tab nào trống, không biểu đồ nào vỡ, console **sạch** (không có `console.warn` của `api.js` → backend nạp thành công). Số khớp: 937 tài khoản · 8 agent · 10 model · tỷ lệ thành công 99,9%
- [x] 5.5 Sáu phát hiện về **cách giao diện NÓI về dữ liệu** — đều có trước change này, đã ghi vào proposal + spec của `serve-dashboard-from-database-only`: 4 chỗ chữ gán cứng nói sai (gồm `"Gateway hoạt động"` và `"lần cuối 2 phút trước"` là chữ tĩnh), và 2 lỗi tính/định dạng (`2/1 · 200%`, `04/26T17:59:49.958000/2026`)
- [x] 5.3 Tổng token là tổng số học — kiểm ở 4.5 và 4.8, mọi kiểu là `number`/`int`, không chuỗi nào bị nối
- [x] 5.4 Máy chủ tĩnh chạy được từ `web/` với `--bind 127.0.0.1`

## 6. Kiểm đường ghi đè vẫn còn hoạt động

- [x] 6.1 `TOKEN_LEDGER_DSN=var/token_ledger.sqlite` — `audit_db.py` chạy đủ 30 phép kiểm trên SQLite; `backend.store` đọc đúng DSN đó, placeholder `?`, 1.161 dòng. Bỏ biến ra thì về Postgres, placeholder `%s`, cũng 1.161 dòng
- [x] 6.2 `--db <đường dẫn>.sqlite` — kiểm qua `merge_billing.project_id_trong_dim_agent()`: chạy được trên **cả hai** hệ, mỗi bên đọc đủ 8 `gcp_project_id`, kiểm chéo đạt. KHÔNG chạy loader ghi lên file SQLite vì đang giữ nó làm mốc đối chiếu

## 7. Tài liệu

- [x] 7.1 `README.md`: thêm `docker compose up -d` làm bước 1; giải thích vì sao Postgres; cách ghi đè bằng `TOKEN_LEDGER_DSN`; cảnh báo `down -v` xoá sạch `pgdata`
- [x] 7.2 `docs/reference/toan-trinh-du-lieu.md`: chặng ③ ghi vào PostgreSQL; lệnh dựng lại nêu `docker compose up -d`; giải thích một-nguồn-sự-thật về DSN
- [x] 7.3 `docs/reference/cay-thu-muc.md`: `var/` trống, database nằm trong volume `pgdata`; `var/` vẫn là nơi duy nhất được chứa `.sqlite` đối chiếu
- [x] 7.4 `docs/reference/mo-ta-database.md`: PostgreSQL là mặc định; lệnh dựng lại kèm thời gian đo được (~56s vs ~14s)
- [x] 7.5 `scripts/copy_to_postgres.py`: sửa tên file sai (`tai_tao_postgres.py` → `copy_to_postgres.py`); ghi rõ là công cụ phụ; giữ lý do cũ nhưng đánh dấu đã hết đúng
- [x] 7.6 `docs/reference/huong-dan-cap-nhat-dashboard.md`: `rebuild_db.py` không còn dựng `var/token_ledger.sqlite`
- [x] 7.7 Task 4.6: ghi hai chênh lệch kiểu (`Decimal`/`int`, `is_technical`) vào `mo-ta-database.md` kèm cảnh báo không so `=== true`
- [x] 7.8 Kiểm hồi quy sau khi sửa: 5/5 script import được · test frontend 6/6 xanh · `audit_db.py` 0 hỏng

## 8. Xoá SQLite — CHỜ ĐỒNG Ý TRƯỚC KHI CHẠY

- [x] 8.1 Nhóm 3, 4, 4b, 5 đều đạt trước khi xoá
- [x] 8.2 Đã được đồng ý, xoá `var/token_ledger.sqlite` (177 MB · 18 bảng · 577.819 dòng)
- [x] 8.3 `var/` trống; `db/` chỉ còn `.sql` và `.py`
- [x] 8.4 Sau khi xoá, kiểm lại 5 đường: `audit_db.py` 30 phép kiểm 0 hỏng · `store.py` placeholder `%s`, 1.161 dòng + 937 tài khoản · `api.js` qua backend thật 10/10 · `merge_billing` kiểm chéo 8 project_id đạt (bước `[6/10]`, chính chỗ lẽ ra sẽ vỡ) · test frontend 6/6
- [x] 8.5 Bốn chỗ còn nhắc `token_ledger.sqlite` đều **không** trên đường chính: `connect.SQLITE_DSN` (dùng trong thông báo lỗi để chỉ nơi tạo bản đối chiếu) · docstring `connect.py` · `copy_to_postgres.SQLITE_MAC_DINH` (công cụ phụ, docstring đã nói rõ cần dựng bản SQLite trước) · ví dụ trong docstring `rebuild_db.py`
