# Chuyển DSN mặc định sang PostgreSQL

## Why

SQLite là **một file trên đĩa**. Nó không đi qua mạng, nên một tiến trình trong
container khác không đọc được; nó không có schema riêng lẫn `GRANT` theo user, nên
không chia quyền theo service được. Cả hai là chặn đường cứng cho mọi thứ đã vẽ trong
`docs/reference/Tài_liệu_triển_khai_API_Gateway.docx`: nhiều instance Gateway sau một
load balancer, và về sau là phân quyền dữ liệu theo từng service.

PostgreSQL đã nằm sẵn trong `docker-compose.yml` từ đợt trước, nhưng chưa bao giờ là
mặc định. Hệ quả đo được: bản Postgres đang chạy là **bản sao 1:1 từ file SQLite**
(`scripts/copy_to_postgres.py`), còn đường ống dựng thẳng vào Postgres
(`rebuild_db.py --db <dsn>`) **chưa từng chạy một lần nào**. Đổi mặc định bây giờ vừa
dỡ chặn đường, vừa buộc đường ống chưa test đó phải được chứng minh.

Đã đối chiếu hai database trước khi đề xuất: 18/18 bảng khớp từng dòng, 3/3 view,
`usage_resolved` khớp từng con số (1.161 dòng · 851.897.312 token · 285,18 USD), và
11/11 hàm của `backend/store.py` chạy được trên Postgres không lỗi nào.

## What Changes

- `connect.DEFAULT_DSN` trỏ vào PostgreSQL thay vì `var/token_ledger.sqlite`. Giá trị
  dựng từ biến môi trường `PGHOST`/`PGPORT`/`PGUSER`/`PGPASSWORD`/`PGDATABASE` — **cùng
  tên và cùng mặc định** với `docker-compose.yml`, nên `docker compose up -d` rồi chạy
  script là nối được ngay, không phải đặt gì.
- `TOKEN_LEDGER_DSN` được `DEFAULT_DSN` tôn trọng, nên **một** biến môi trường đổi được
  database cho **toàn bộ** script, không chỉ backend như hiện nay. Đây cũng là đường quay
  về SQLite khi cần đối chiếu.
- `scripts/rebuild_db.py` dùng chung `connect.DEFAULT_DSN`. Hiện nó có hằng số riêng
  (`default=str(ROOT / "var" / "token_ledger.sqlite")`) và `update_dashboard.py` gọi nó
  **không truyền `--db`** — nên nếu chỉ đổi `connect.py` thì đường ống vẫn dựng lại
  SQLite. Sửa để chỉ còn một nguồn sự thật.
- `scripts/merge_billing.py` **ghim cứng vào SQLite**, phát hiện khi soát: nó gọi
  `sqlite3.connect()` trực tiếp, nhận `Path` chứ không nhận DSN, và `dung()` — dừng hẳn —
  nếu không thấy file. Nó là bước `[6/10]` của đường ống. Nghĩa là **xoá SQLite sẽ làm vỡ
  đường ống**, với thông báo lỗi *"khong thay database"* trông như thiếu file chứ không như
  ghim cứng hệ quản trị. Sửa để nó đọc qua `connect.open_db()`, và giữ nguyên chế độ
  chỉ-đọc ở mức máy chủ.
- Hàm che mật khẩu chuyển vào `db/connect.py` dùng chung. `db/load_billing.py:67` đang
  in `args.db` **chưa che** — hôm nay vô hại vì DSN là đường dẫn file, nhưng sau khi đổi
  sẽ in mật khẩu ra terminal và log.
- Hàm che phải cắt ở `@` **cuối**, không phải `@` đầu. Mật khẩu được phép chứa `@`; với
  `postgresql://u:p@ss@may/db` thì cắt ở `@` đầu làm đoạn `ss` của mật khẩu **chảy sang vế
  host** rồi được in nguyên văn. Vế host của URL không bao giờ chứa `@` nên `rsplit` mới
  đúng. Bản `che()` cũ trong `rebuild_db.py` có đúng lỗi này.
- `rebuild_db.py` truyền DSN cho 7 tiến trình con qua **biến môi trường**
  `TOKEN_LEDGER_DSN`, không qua `--db` trên dòng lệnh. Dòng lệnh của một tiến trình nhìn
  thấy được từ ngoài (`ps` / Task Manager), nên để DSN Postgres ở đó là phơi mật khẩu ra cả
  7 tiến trình. Trước đây DSN là đường dẫn file nên không có gì để lộ — rủi ro này do chính
  việc đổi sang Postgres tạo ra.
- Chứng minh `rebuild_db.py --db <postgres>` dựng lại được toàn bộ database từ `data/`,
  và đối chiếu kết quả với các con số đã chốt ở trên.
- **BREAKING** Xoá `var/token_ledger.sqlite`. Sau thay đổi này SQLite chỉ còn là đường
  ghi đè bằng tay để đối chiếu, không còn là database của dự án.

## Capabilities

### New Capabilities

- `database-connection`: DSN mặc định trỏ vào đâu, thứ tự ưu tiên khi ghi đè, quy tắc
  không để mật khẩu lọt ra màn hình/log, và yêu cầu rằng mọi script nạp cùng đọc một
  nguồn sự thật về DSN.
- `postgres-rebuild-equivalence`: đường ống dựng thẳng vào PostgreSQL từ `data/` phải ra
  đúng database mà bản sao từ SQLite đang có — nêu rõ các con số dùng làm mốc đối chiếu,
  và các chênh lệch kiểu dữ liệu đã biết là vô hại.

### Modified Capabilities

- `project-layout`: requirement *"Mã nguồn tách khỏi dữ liệu chạy"* hiện nói *"Database
  SQLite SHALL nằm trong `var/`"*. Sau thay đổi này không còn database SQLite nào, nên
  phát biểu đó phải nói về dữ liệu chạy nói chung (volume Docker `pgdata`) thay vì về
  một file trong `var/`. Ranh giới *"`data/` mất là vĩnh viễn, dữ liệu chạy dựng lại
  được"* KHÔNG đổi — đó là điều thay đổi này củng cố.

## Impact

| Nơi | Thay đổi |
|---|---|
| `db/connect.py` | `DEFAULT_DSN` → Postgres; thêm `mask_dsn()`; đọc biến môi trường |
| `scripts/rebuild_db.py` | bỏ hằng số DSN riêng, dùng `connect.DEFAULT_DSN` và `connect.mask_dsn()` |
| `db/load_billing.py` | che mật khẩu khi in DSN |
| `scripts/merge_billing.py` | bỏ `sqlite3` trực tiếp và hằng số `DB_MAC_DINH`; đọc qua `connect.open_db()` chỉ-đọc — **nếu không sửa, xoá SQLite làm vỡ bước `[6/10]`** |
| `var/token_ledger.sqlite` | **xoá** sau khi đường ống Postgres đã được chứng minh |
| `README.md`, `docs/reference/` | cách chạy: phải `docker compose up -d` trước |
| 7 script nạp trong `db/`, `scripts/audit_db.py` | không sửa — đã dùng `connect.DEFAULT_DSN` |

**Phụ thuộc mới:** `psycopg2-binary` chuyển từ tuỳ chọn thành **bắt buộc**. Hiện
`backend/requirements.txt` ghi *"psycopg2 chi can khi doc PostgreSQL. Chay tren SQLite
thi bo qua duoc"* — ghi chú đó hết đúng.

**Rủi ro cần chặn:** `docker compose down -v` xoá sạch volume `pgdata`. Trước thay đổi
này còn file SQLite làm lớp đệm; sau thì không. Dựng lại được từ `data/` nhưng mất
~15 phút, nên `data/` vẫn là thứ duy nhất không được mất.
