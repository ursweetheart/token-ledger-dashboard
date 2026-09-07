# postgres-rebuild-equivalence Specification

## Purpose
TBD - created by archiving change switch-default-dsn-to-postgres. Update Purpose after archive.
## Requirements
### Requirement: Đường ống dựng thẳng vào PostgreSQL phải chạy được

`scripts/rebuild_db.py` SHALL dựng lại toàn bộ database vào PostgreSQL từ `data/`, không
qua trung gian SQLite và không dùng `scripts/copy_to_postgres.py`.

Yêu cầu này tồn tại vì bản Postgres hiện có là **bản sao 1:1 từ file SQLite**, còn đường
dựng thẳng chưa từng chạy. Xoá SQLite trước khi chứng minh đường này là bỏ con đường duy
nhất đã hoạt động để chỉ còn con đường chưa kiểm.

#### Scenario: Bảy bước nạp đều đạt nghiệm thu trên PostgreSQL

- **WHEN** chạy `python scripts/rebuild_db.py` với DSN Postgres trên một database rỗng
- **THEN** cả bảy bước nạp kết thúc với mã thoát 0
- **AND** không bước nào cần `--from-step` để đi tiếp

#### Scenario: Soi database sau khi dựng lại

- **WHEN** chạy `python scripts/audit_db.py` trên database Postgres vừa dựng
- **THEN** mọi phép kiểm đều đạt
- **AND** không phép kiểm nào bị bỏ qua vì thiếu bảng

### Requirement: Số liệu sau khi dựng lại phải khớp mốc đã chốt

Database dựng thẳng vào PostgreSQL SHALL cho ra cùng số liệu với bản sao đã đối chiếu.
Các mốc dưới đây được đo trên cả hai database trước thay đổi và SHALL dùng làm nghiệm thu:

| Phép đo trên `usage_resolved` | Giá trị |
|---|---|
| Khoảng ngày | 2026-01-01 → 2026-08-13 |
| Số dòng | 1.161 |
| `SUM(input_tokens)` | 539.827.701 |
| `SUM(output_tokens)` | 87.459.865 |
| `SUM(cached_tokens)` | 227.679.097 |
| `SUM(total_tokens)` | 851.897.312 |
| `SUM(cost_usd)` | 285,18 USD |
| Nguồn được chọn | billing 942 · app 164 · monitoring 45 · NULL 10 |

Đối chiếu MUST đọc qua view `usage_resolved`, KHÔNG phải `SUM` thẳng trên
`fact_usage_daily`. Khoá chính của bảng đó gồm cả `source`, nên cộng thẳng là **đếm trùng
qua các nguồn** — đã đo: ra 897.452.165 thay vì 539.827.701, và con số sai đó trông hoàn
toàn hợp lý.

#### Scenario: Đối chiếu từng con số sau khi dựng lại

- **WHEN** truy vấn `usage_resolved` trên database Postgres vừa dựng từ `data/`
- **THEN** cả tám phép đo trong bảng trên khớp đúng giá trị đã chốt
- **AND** số bảng là 18 và số view là 3

#### Scenario: Mọi hàm của tầng truy vấn chạy được

- **WHEN** gọi cả 11 hàm công khai của `backend/store.py` trên database Postgres
- **THEN** không hàm nào ném lỗi
- **AND** số dòng trả về khớp: `agents` 8 · `models` 10 · `units` 130 · `accounts` 937 ·
  `adoption` 8 · `usage` 1.161 · `usage_by_account` 314 · `thinking` 408

### Requirement: Chênh lệch kiểu dữ liệu giữa hai hệ quản trị phải vô hại tới frontend

Hai hệ quản trị trả về kiểu Python khác nhau cho cùng một cột. Các chênh lệch đã biết SHALL
không làm đổi JSON mà frontend nhận được.

Đã đo hai chênh lệch:

1. **Token: `Decimal` (Postgres) vs `int` (SQLite).** `jsonable_encoder` của FastAPI đổi
   `Decimal` có phần thập phân bằng 0 thành `int`, nên JSON ra số nguyên ở cả hai bên. Đây
   là chỗ nguy hiểm nhất nếu sai: nếu `cached_tokens` ra JSON dạng **chuỗi**, thì
   `ti + to + cached` trong `web/js/app.js` thành **nối chuỗi** thay vì phép cộng — số sai
   âm thầm, không lỗi nào ném ra.
2. **`is_technical`: `true` (Postgres) vs `1` (SQLite).** SQLite không có BOOLEAN thật.
   Hiện không thành phần nào trong `web/` đọc cột này, nên vô hại; nhưng nó SHALL được ghi
   lại để phần hiển thị sau này không so bằng `=== true`.

#### Scenario: JSON của số token giống nhau trên hai hệ quản trị

- **WHEN** gọi `/api/usage` cùng khoảng ngày trên Postgres rồi trên SQLite
- **THEN** giá trị `total_tokens`, `input_tokens`, `output_tokens`, `cached_tokens` trong
  JSON là **số**, không phải chuỗi
- **AND** hai bên cho cùng con số

#### Scenario: Tổng token trên màn hình không bị nối chuỗi

- **WHEN** dashboard nạp từ backend chạy trên Postgres và cộng `ti + to + cached`
- **THEN** kết quả là tổng số học
- **AND** không giá trị nào hiện dưới dạng các chữ số bị nối liền nhau
