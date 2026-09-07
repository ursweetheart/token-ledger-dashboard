# database-connection Specification

## Purpose
TBD - created by archiving change switch-default-dsn-to-postgres. Update Purpose after archive.
## Requirements
### Requirement: Một nguồn sự thật duy nhất về DSN mặc định

Mọi script nạp, script chẩn đoán, và backend SHALL lấy DSN mặc định từ **đúng một** hằng
số: `connect.DEFAULT_DSN`. Không file nào khác được phép dựng chuỗi kết nối mặc định của
riêng mình.

Quy tắc này tồn tại vì đã có sự cố hình dạng đó: `scripts/rebuild_db.py` từng khai
`default=str(ROOT / "var" / "token_ledger.sqlite")` độc lập với `connect.DEFAULT_DSN`, và
`scripts/update_dashboard.py` gọi nó không truyền `--db`. Hệ quả là đổi `connect.py` mà
đường ống vẫn dựng lại database cũ, không lỗi nào báo ra.

#### Scenario: Đổi một chỗ là đổi toàn bộ đường ống

- **WHEN** đổi giá trị `connect.DEFAULT_DSN` rồi chạy `python scripts/rebuild_db.py` không
  kèm `--db`
- **THEN** database được dựng tại đích mới
- **AND** không script nào trong `db/` hoặc `scripts/` còn dựng chuỗi kết nối mặc định của
  riêng nó

#### Scenario: Tìm hằng số DSN trong toàn bộ mã nguồn

- **WHEN** tìm chuỗi `token_ledger.sqlite` trong `db/`, `scripts/`, và `backend/`
- **THEN** chỉ thấy nó trong tài liệu hướng dẫn cách ghi đè về SQLite
- **AND** không thấy nó làm giá trị mặc định của bất kỳ tham số nào

#### Scenario: Không script nào của đường ống ghim cứng một hệ quản trị

- **WHEN** tìm lời gọi `sqlite3.connect` trong `scripts/` và `db/`
- **THEN** mọi lời gọi còn lại đều nằm sau một phép kiểm `connect.is_sqlite(dsn)`
- **AND** không script nào nhận `Path` thay cho DSN ở tham số `--db`

#### Scenario: Kiểm chéo hoá đơn chạy được trên cả hai hệ

- **WHEN** gọi phép kiểm chéo `ANH_XA_PROJECT` với `dim_agent` lần lượt trên PostgreSQL rồi
  trên SQLite
- **THEN** cả hai đọc được đủ 8 `gcp_project_id` và phép kiểm chéo đạt
- **AND** kết nối PostgreSQL ở chế độ chỉ-đọc mức máy chủ, vì script này chỉ kiểm không ghi

### Requirement: DSN mặc định trỏ vào PostgreSQL

`connect.DEFAULT_DSN` SHALL là chuỗi kết nối PostgreSQL. Nó SHALL được dựng từ các biến
môi trường `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, với giá trị mặc định
**khớp `docker-compose.yml`** — nên `docker compose up -d` rồi chạy script là nối được
ngay, không phải đặt biến nào.

SQLite SHALL vẫn mở được, nhưng chỉ khi người dùng chỉ định tường minh. Cơ chế phân biệt
theo đuôi file (`.sqlite`/`.db`) MUST NOT bị bỏ — nó là đường đối chiếu độc lập khi cần.

#### Scenario: Chạy được ngay sau khi dựng container

- **WHEN** chạy `docker compose up -d`, chờ Postgres healthy, rồi chạy một script nạp mà
  không đặt biến môi trường nào và không truyền `--db`
- **THEN** script nối được vào Postgres trong container
- **AND** không cần sửa file nào

#### Scenario: Ghi đè bằng biến môi trường có hiệu lực toàn hệ thống

- **WHEN** đặt `TOKEN_LEDGER_DSN` trỏ vào một database khác rồi chạy backend, các script
  nạp, và `scripts/audit_db.py`
- **THEN** cả ba đều đọc/ghi đúng database đó
- **AND** không thành phần nào bỏ qua biến này để về mặc định

#### Scenario: Vẫn quay về SQLite được khi cần đối chiếu

- **WHEN** truyền `--db <đường dẫn>.sqlite` cho một script nạp
- **THEN** script mở SQLite thay vì Postgres
- **AND** đặt chỗ tham số đổi từ `%s` sang `?` đúng theo hệ quản trị

### Requirement: Mật khẩu không lọt ra màn hình hay log

Mọi chỗ in DSN ra `stdout`, `stderr`, hoặc log SHALL đi qua một hàm che mật khẩu dùng
chung, đặt cùng nơi với `DEFAULT_DSN`. Không thành phần nào được in DSN thô.

Trước thay đổi này DSN là đường dẫn file nên in thẳng vô hại, và `db/load_billing.py` in
`args.db` không che. Khi mặc định thành chuỗi Postgres có mật khẩu, chính dòng đó thành
chỗ rò.

#### Scenario: Dựng lại database không in mật khẩu

- **WHEN** chạy `python scripts/rebuild_db.py` với DSN Postgres và đọc toàn bộ đầu ra
- **THEN** đầu ra hiện tên user, máy, cổng, và tên database
- **AND** phần mật khẩu hiện dưới dạng đã che, không phải giá trị thật

#### Scenario: Nạp hoá đơn kèm dựng lại schema không in mật khẩu

- **WHEN** chạy `python db/load_billing.py --rebuild` với DSN Postgres
- **THEN** dòng thông báo dựng lại schema không chứa mật khẩu

#### Scenario: Đường dẫn file in nguyên vẹn

- **WHEN** che một DSN là đường dẫn file SQLite
- **THEN** chuỗi trả về y hệt chuỗi vào, không bị cắt hay thay ký tự

#### Scenario: Mật khẩu chứa ký tự `@` vẫn được che kín

Mật khẩu được phép chứa `@`. Cắt ở `@` đầu tiên làm một phần mật khẩu chảy sang vế host rồi
được in nguyên văn — vế host của URL không bao giờ chứa `@`, nên phải cắt ở `@` cuối.

- **WHEN** che `postgresql://u:p@ss@may:5432/db`
- **THEN** kết quả là `postgresql://u:***@may:5432/db`
- **AND** không ký tự nào của mật khẩu `p@ss` còn xuất hiện trong kết quả

#### Scenario: DSN không có mật khẩu thì không bị thêm mật khẩu giả

- **WHEN** che `postgresql://u@may:5432/db`
- **THEN** kết quả giữ nguyên, không chèn `:***`
- **AND** người đọc log không tưởng là có một mật khẩu mà thực ra không có

### Requirement: Mật khẩu không đi qua dòng lệnh của tiến trình con

Script điều phối SHALL truyền DSN cho tiến trình con qua **biến môi trường**, MUST NOT đặt
DSN lên dòng lệnh.

Dòng lệnh của một tiến trình đọc được từ ngoài (`ps`, Task Manager) bởi tiến trình khác trên
cùng máy. Trước khi PostgreSQL thành mặc định, DSN là đường dẫn file nên không có gì để lộ;
rủi ro này do chính việc đổi mặc định tạo ra, nên phải xử lý cùng lúc.

#### Scenario: Dựng lại database không phơi mật khẩu ra dòng lệnh

- **WHEN** chạy `scripts/rebuild_db.py` với DSN PostgreSQL có mật khẩu
- **THEN** không tiến trình con nào có mật khẩu trên dòng lệnh của nó
- **AND** cả 7 bước nạp vẫn nối được vào đúng database đã chỉ định

#### Scenario: DSN tường minh vẫn tới được tiến trình con

- **WHEN** chạy `scripts/rebuild_db.py --db <dsn của một database KHÁC mặc định>`
- **THEN** cả 7 bước nạp ghi vào database đó, không ghi vào database mặc định
- **AND** database mặc định không bị thay đổi
