# schema-migrations Specification

## Purpose
TBD - created by archiving change change-the-schema-without-dropping-it. Update Purpose after archive.
## Requirements
### Requirement: Đổi schema KHÔNG được đòi xoá dữ liệu

Mọi thay đổi cấu trúc database SHALL áp dụng được lên một database **đang có dữ liệu**,
giữ nguyên dữ liệu đó. MUST NOT đòi `DROP SCHEMA`, `DROP DATABASE`, hay nạp lại từ `data/`.

Yêu cầu này nói về **đổi schema**, không cấm bản thân thao tác xoá sạch. Đường *"dựng lại
toàn bộ từ `data/`"* (`connect.rebuild()` → `rebuild_db.py`) vẫn được phép `DROP SCHEMA`,
vì `load_billing.py --rebuild` cần một schema trắng để nạp lại danh mục mà không đụng khoá
chính. Hai đường dùng chung một chuỗi migration; điều bị cấm là **bắt buộc phải xoá thì mới
đổi được schema**.

Lý do: hôm nay `db/connect.py:132-154` là **cách duy nhất** đổi schema, và nó bắt đầu bằng
`DROP SCHEMA public CASCADE`. Điều đó vô hại chừng nào mọi dòng còn dựng lại được từ
`data/` — và hết vô hại vào ngày Gateway ghi dòng đầu tiên, vì dòng Gateway không có bản
sao ở `data/`. Master Plan giai đoạn 4 và quyết định A1-2 (20/08, *"CÓ ghi `fact_attempt`"*)
đều dẫn tới ngày đó.

#### Scenario: Thêm một cột vào bảng đang có dữ liệu

- **WHEN** một migration thêm cột vào bảng đã có dòng
- **THEN** dữ liệu cũ SHALL còn nguyên sau khi áp
- **AND** MUST NOT phải chạy lại bất kỳ script `load_*` nào

#### Scenario: Dựng database trên máy trắng

- **WHEN** một người clone repo về và chưa có database nào
- **THEN** chạy migration từ đầu SHALL cho ra schema giống hệt database đang chạy
- **AND** MUST NOT cần `db/01_schema.sql` — file đó không còn tồn tại

### Requirement: Chỉ có MỘT chỗ mô tả schema

Cấu trúc database SHALL được mô tả **duy nhất** bởi chuỗi migration. MUST NOT tồn tại song
song một file schema đầy đủ thứ hai.

Lý do: hai chỗ cùng mô tả một sự thật thì chúng sẽ trôi khỏi nhau, và trôi trong im lặng —
người dựng máy trắng và người migrate máy cũ nhận hai schema khác nhau mà không có lỗi nào
báo. Xoá `db/01_schema.sql` sau khi nội dung nó vào migration `001` khiến bài toán này
**không tồn tại**, thay vì phải dựng thêm một phép kiểm để canh nó.

#### Scenario: Có người sửa schema

- **WHEN** cần đổi cấu trúc
- **THEN** cách duy nhất SHALL là thêm một migration mới
- **AND** MUST NOT sửa một migration đã chạy

### Requirement: Migration đã áp thì bất biến

Một migration đã chạy trên bất kỳ database nào SHALL không bao giờ được sửa nội dung.

Lý do: máy anh áp bản cũ, máy đồng nghiệp áp bản mới, hai database khác nhau mà bảng theo
dõi ở cả hai đều nói *"đã áp"*. Đây là lỗi im lặng đúng loại mà dự án này dựng ra để chống.

#### Scenario: Migration nền bị sửa

- **WHEN** nội dung một migration đã áp bị đổi
- **THEN** hệ thống SHALL phát hiện được bằng checksum hoặc bằng quy ước ghi tại chỗ
- **AND** MUST NOT âm thầm bỏ qua

#### Scenario: Cần gỡ một thay đổi đã áp

- **WHEN** một thay đổi schema cần được gỡ bỏ
- **THEN** cách làm SHALL là thêm một migration **tiến** khác để gỡ
- **AND** MUST NOT dùng `alembic downgrade` — change này chọn forward-only, `downgrade()`
  ném `NotImplementedError` kèm lý do

### Requirement: DSN vẫn chỉ có một nguồn sự thật

Công cụ migration SHALL lấy chuỗi kết nối từ `connect.DEFAULT_DSN`. MUST NOT tự đọc biến
môi trường riêng của nó, và MUST NOT khai DSN trong `alembic.ini`.

Lý do: `db/connect.py` tự nhận là *"chỗ DUY NHẤT quyết định database mặc định"*, và nó ghi
lại một sự cố đúng hình dạng này: `scripts/rebuild_db.py` từng khai DSN mặc định riêng còn
`scripts/update_dashboard.py` gọi nó không truyền `--db`. Hệ quả là đổi `connect.py` xong
mà đường ống vẫn dựng database cũ — **không lỗi nào báo ra**.

#### Scenario: Đổi database bằng một biến

- **WHEN** `TOKEN_LEDGER_DSN` được đặt sang một database khác
- **THEN** cả migration lẫn mọi script nạp SHALL cùng trỏ vào database đó
- **AND** MUST NOT có công cụ nào còn trỏ vào database cũ

### Requirement: Danh mục KHÔNG nằm trong migration

`db/02_catalog.sql` SHALL tiếp tục được nạp bởi đường nạp dữ liệu, không bởi migration.

Lý do: nó là **dữ liệu gieo** (8 agent, 10 model, bảng giá, ánh xạ tên), không phải cấu
trúc — và nó được **sinh tự động** bởi `db/gen_catalog.py`. Đóng băng nó vào một migration
bất biến sẽ làm hỏng đường sinh lại đó: sửa quy tắc trong `db/rules.py` rồi chạy lại
`gen_catalog.py` sẽ không còn tác dụng.

#### Scenario: Danh mục được sinh lại

- **WHEN** `db/gen_catalog.py` chạy lại và cho ra `02_catalog.sql` khác
- **THEN** lần dựng database kế tiếp SHALL dùng bản mới
- **AND** MUST NOT cần thêm migration nào

### Requirement: Chuyển đổi phải chứng minh được bằng số, không bằng lời

Việc chuyển sang migration SHALL được nghiệm thu bằng cách dựng lại toàn bộ database từ
`data/` rồi so với bộ số mốc đo trước khi bắt đầu. MUST NOT đổi `DEFAULT_DSN` trước khi
mọi con số khớp.

Bộ số mốc, đo trên PostgreSQL ngày 24/08/2026 qua `usage_resolved` (đã khử trùng lặp —
cộng thẳng `fact_usage_daily` là đếm ba lần):

| | |
|---|---|
| `usage_resolved` | 1.189 dòng · 867.657.110 token · $291,985601 · 2026-01-01 → 2026-08-17 |
| `usage_by_account` | 320 dòng · 107.926.810 token |
| `account` | 953 = `real` 937 · `service_account` 6 · `whole_agent` 2 · `unattributed` 8 |
| `fact_usage_daily` | 1.845 — `billing` 965 · `monitoring` 539 · `app` 341 |
| `fact_monitoring` | 583.917 |
| `fact_billing_daily` | 2.441 |
| `fact_call` | 8.330 |
| `fact_app_daily` | 77 |
| `ref_source` | 4 |

#### Scenario: Một con số lệch

- **WHEN** database dựng lại cho ra con số khác bộ mốc
- **THEN** quá trình SHALL dừng lại và điều tra nguyên nhân
- **AND** MUST NOT nới phép so cho vừa ý, MUST NOT xoá database cũ

#### Scenario: Hai database được giữ song song

- **WHEN** `token_ledger_v2` đã qua nghiệm thu và trở thành runtime ledger
- **THEN** `token_ledger` SHALL được giữ nguyên làm bản legacy để đối chiếu và rollback
- **AND** hệ thống MUST NOT yêu cầu xoá database cũ hoặc rename database mới
- **AND** ingestion Gateway mới SHALL chỉ ghi vào `token_ledger_v2`, MUST NOT ghi cùng một
  dòng nghiệp vụ vào cả hai ledger

#### Scenario: Database vận hành của LiteLLM

- **WHEN** Gateway LiteLLM khởi động và ghi SpendLogs
- **THEN** LiteLLM SHALL dùng database riêng tên `litellm`
- **AND** `token_ledger` và `token_ledger_v2` MUST NOT chứa bảng vận hành `LiteLLM_*`

