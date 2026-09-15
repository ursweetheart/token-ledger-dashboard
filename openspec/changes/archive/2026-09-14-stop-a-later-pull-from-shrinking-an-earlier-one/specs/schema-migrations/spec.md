## MODIFIED Requirements

### Requirement: Đổi schema KHÔNG được đòi xoá dữ liệu

Mọi thay đổi cấu trúc database SHALL áp dụng được lên một database **đang có dữ liệu**,
giữ nguyên dữ liệu đó. MUST NOT đòi `DROP SCHEMA`, `DROP DATABASE`, hay nạp lại từ `data/`.

Đường *"dựng lại toàn bộ từ `data/`"* (`connect.rebuild()` → `rebuild_db.py`) được phép xoá
**dòng**, vì nó nạp lại mọi thứ từ `data/`. Nhưng nó MUST NOT xoá **schema**. Nó SHALL đưa
schema lên bản mới nhất bằng chính chuỗi migration, tại chỗ, rồi xoá dòng của mọi bảng dữ liệu
trong **một** giao dịch, trước khi nạp danh mục. Bảng, view, schema, và mọi quyền đã cấp SHALL
còn nguyên sau khi dựng lại.

Bảng mà **chính migration ghi dòng** (hôm nay là `alembic_version` và `ref_source`) MUST NOT bị xoá
dòng. Database đã có sẵn không chạy lại migration, nên xoá những dòng đó là mất vĩnh viễn. Đo ngày
14/09/2026 trên database diễn tập: bản đầu của change này xoá cả `ref_source`, và bước nạp Ralli
chết với `fact_call_source_fkey`. Danh sách bảng giữ lại SHALL được một phép kiểm canh, bằng cách quét
mọi migration tìm câu ghi dòng.

Lý do bản trước cho phép `DROP SCHEMA` là `load_billing.py --rebuild` cần bảng danh mục **trống**
để nạp mà không đụng khoá chính. Xoá dòng cũng cho bảng trống, mà không kéo theo schema.

Lý do cấm, đo được: `DROP SCHEMA public CASCADE` xoá mọi GRANT, kể cả quyền đọc của vai mà
container `api` dùng. Ngày 02/09/2026, sau một lần dựng lại, `api_readonly` đọc được 0/20 bảng và
0/3 view, và container `api` chạy 38 phút trên một database nó không đọc nổi. Hơn nữa, đường
dựng lại này đang bị chặn bởi một lỗi khác ở bước 7 của `scripts/update_dashboard.py`. Sửa lỗi đó mà
còn giữ `DROP SCHEMA` thì sẽ mở lại đúng sự cố trên.

Lý do gốc của yêu cầu này vẫn giữ: trước change `change-the-schema-without-dropping-it`,
`db/connect.py` là **cách duy nhất** đổi schema, và nó bắt đầu bằng `DROP SCHEMA public CASCADE`.
Điều đó vô hại chừng nào mọi dòng còn dựng lại được từ `data/`, và hết vô hại vào ngày Gateway ghi
dòng đầu tiên, vì dòng Gateway không có bản sao ở `data/`.

#### Scenario: Thêm một cột vào bảng đang có dữ liệu

- **WHEN** một migration thêm cột vào bảng đã có dòng
- **THEN** dữ liệu cũ SHALL còn nguyên sau khi áp
- **AND** MUST NOT phải chạy lại bất kỳ script `load_*` nào

#### Scenario: Dựng database trên máy trắng

- **WHEN** một người clone repo về và chưa có database nào
- **THEN** chạy migration từ đầu SHALL cho ra schema giống hệt database đang chạy
- **AND** MUST NOT cần `db/01_schema.sql` — file đó không còn tồn tại

#### Scenario: Dựng lại toàn bộ từ data/ không làm mất quyền đọc

- **WHEN** chạy `python scripts/rebuild_db.py` trên một database mà `api_readonly` đang đọc được mọi bảng và view
- **THEN** sau khi dựng lại, `api_readonly` SHALL vẫn đọc được mọi bảng và view
- **AND** bước `scripts/check_db_grants.py` SHALL đạt mà không cần chạy lại `docker/read-only-api.sql`

#### Scenario: Dựng lại giữ dòng do migration gieo

- **WHEN** chạy `connect.rebuild()` trên một database đã có sẵn, mà `ref_source` đang có 4 dòng
- **THEN** sau khi dựng lại, `ref_source` SHALL vẫn có đúng 4 dòng đó
- **AND** mọi bước nạp của `scripts/rebuild_db.py` SHALL đạt

#### Scenario: Có migration mới gieo dữ liệu vào một bảng khác

- **WHEN** một migration mới ghi dòng vào một bảng chưa nằm trong danh sách giữ lại
- **THEN** phép kiểm quét migration SHALL đỏ trước khi code đó tới được database thật

#### Scenario: Dựng lại không xoá schema

- **WHEN** `connect.rebuild()` chạy
- **THEN** không câu lệnh nào nó gửi đi SHALL chứa `DROP SCHEMA` hoặc `DROP DATABASE`
