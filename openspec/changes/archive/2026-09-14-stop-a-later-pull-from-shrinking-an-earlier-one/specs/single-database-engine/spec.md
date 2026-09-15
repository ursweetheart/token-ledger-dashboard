## MODIFIED Requirements

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
- **THEN** nó SHALL chỉ có một đường: chạy migration tại chỗ, rồi xoá dòng của mọi bảng dữ liệu trong một giao dịch (trừ bảng mà migration ghi dòng), rồi nạp danh mục
- **AND** MUST NOT còn nhánh xoá file
- **AND** MUST NOT gọi `DROP SCHEMA` (xem `schema-migrations`)
- **AND** SHALL vẫn trả về `(connection, placeholder)` như trước, để mọi chỗ gọi `rebuild()` không phải đổi
