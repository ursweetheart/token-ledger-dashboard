# single-database-engine Specification

## Purpose
TBD - created by archiving change drop-the-sqlite-escape-hatch. Update Purpose after archive.
## Requirements
### Requirement: PostgreSQL là hệ quản trị duy nhất được đỡ

Mọi đường mở kết nối SHALL chỉ mở PostgreSQL. MUST NOT còn nhánh rẽ theo hệ quản trị trong
`db/connect.py`, `backend/store.py`, `scripts/audit_db.py` hay `scripts/merge_billing.py`.

Lý do: ba điều kiện của một đường quay về đều đã hỏng, đo ngày 24/08/2026 —
`var/token_ledger.sqlite` bị xoá từ 17/08 nên **không còn dữ liệu để quay về**;
`01_schema.sql` hỏng cú pháp trên SQLite từ 21/08 (nối chuỗi liền kề ở `INSERT INTO
ref_source`) nên **không dựng lại được**; và không phép kiểm nào chạy trên SQLite nên
**không ai canh**. Mã chết mang hình dạng một bảo hiểm còn tệ hơn không có gì: nó khiến
người đọc tin rằng có đường lui.

#### Scenario: Đưa vào một DSN trỏ file SQLite

- **WHEN** một script nhận `--db` là đường dẫn `.sqlite` hoặc `.db`
- **THEN** nó SHALL dừng ngay với thông báo nói rõ SQLite không còn được đỡ
- **AND** MUST NOT im lặng tạo một file rồi chạy nửa vời

#### Scenario: Dựng lại database

- **WHEN** `connect.rebuild()` được gọi
- **THEN** nó SHALL chỉ có một đường: `DROP SCHEMA public CASCADE` rồi chạy migration
- **AND** MUST NOT còn nhánh xoá file

### Requirement: Migration được phép dùng cú pháp riêng của PostgreSQL

Migration trong `db/migrations/` SHALL không còn bị ràng buộc phải chạy được trên nhiều hệ.

Lý do: ràng buộc "trung lập hai hệ" chỉ tồn tại để phục vụ đường SQLite. Giữ nó sau khi
đường đó bị gỡ là cấm mọi migration về sau dùng `JSONB`, `GENERATED`, partial index — để
phục vụ một thứ không còn.

#### Scenario: Migration mới cần kiểu dữ liệu của PostgreSQL

- **WHEN** một migration cần `JSONB` hoặc cú pháp riêng khác
- **THEN** nó SHALL được phép dùng
- **AND** MUST NOT phải tìm cách viết vòng cho SQLite hiểu

### Requirement: Gỡ hệ quản trị KHÔNG được lan vào tầng truy vấn

`open_db()` SHALL vẫn trả về `(connection, placeholder)`. MUST NOT sửa 19 chỗ nối chuỗi
`{ph}` trong câu truy vấn, và MUST NOT sửa 15 chỗ gọi `open_db()` / `rebuild()`.

Lý do: `placeholder` nay là hằng `"%s"`, nhưng gỡ hẳn abstraction đó là sửa 34 chỗ nằm rải
khắp `db/`, `scripts/`, `backend/` — một diff lớn, rủi ro thật, và không mua thêm năng lực
nào. Ranh giới này giữ cho change chỉ gỡ **nhánh rẽ**, không chạm tầng truy vấn, nên nghiệm
thu được bằng cách đếm lại hai con số.

#### Scenario: Đếm lại sau khi gỡ

- **WHEN** change hoàn tất
- **THEN** vẫn SHALL còn đúng 15 chỗ gọi `open_db()`/`rebuild()` và 19 chuỗi `{ph}`
- **AND** hai con số đó SHALL được kiểm bằng lệnh, không bằng mắt

### Requirement: Backend giữ nguyên kỷ luật chỉ-đọc

Sau khi gỡ nhánh SQLite, `backend/store.py` SHALL vẫn mở kết nối PostgreSQL ở chế độ
chỉ-đọc.

Lý do: `check_api.py` có một phép kiểm khẳng định *"Kết nối của backend là chỉ đọc
(ReadOnlySqlTransaction)"*. Nhánh SQLite trước đây mở bằng `?mode=ro`; nhánh PostgreSQL có
cơ chế riêng. Gỡ nhánh này mà vô ý làm mất tính chỉ-đọc của nhánh kia là biến một backend
chỉ-đọc thành backend ghi được, và phép kiểm đó là lưới duy nhất.

#### Scenario: Sau khi gỡ nhánh SQLite

- **WHEN** `check_api.py` chạy
- **THEN** phép kiểm chỉ-đọc SHALL nằm trong số đạt
- **AND** tổng số phép đạt MUST NOT thấp hơn mốc 19/19 đo ngày 24/08/2026

### Requirement: Số liệu không được suy suyển

Change này SHALL không đụng tới dữ liệu. Bộ 23 khoá bất biến SHALL khớp tuyệt đối trước và
sau.

#### Scenario: So bộ số sau khi gỡ

- **WHEN** `tools/baseline_db.py --compare` chạy sau change
- **THEN** kết quả SHALL là 23/23 khớp
- **AND** MUST NOT có khoá nào lệch, kể cả lệch một token

