# gop-billing-console Specification

## Purpose
TBD - created by archiving change transform-billing-tu-console. Update Purpose after archive.
## Requirements
### Requirement: Chọn file đầu vào theo mẫu, không ghim tên

Script SHALL tìm file đầu vào bằng mẫu glob trên `data/billing/`, KHÔNG được ghim tên file đầy đủ trong mã nguồn. Tên file Console chứa khoảng ngày do người dùng chọn (`… 2026-01-01 — 2026-08-31, …`) nên đổi theo mỗi lần xuất; ghim tên sẽ khiến bản xuất mới bị bỏ qua mà script vẫn báo thành công.

Script SHALL in ra danh sách file đã chọn kèm số dòng của từng file trước khi xử lý.

#### Scenario: Tìm thấy đủ file
- **WHEN** thư mục `data/billing/` chứa 7 file khớp mẫu `*GMSSub*.csv`
- **THEN** script chọn cả 7 file và in ra tên cùng số dòng từng file

#### Scenario: Có bản xuất mới với khoảng ngày khác
- **WHEN** một file mới tên `… 2026-01-01 — 2026-09-30, AI-sale_agent.csv` được thêm vào
- **THEN** script vẫn chọn được file đó vì khớp mẫu, không cần sửa mã nguồn

#### Scenario: Không tìm thấy file nào
- **WHEN** không file nào khớp mẫu
- **THEN** script dừng với lỗi nêu rõ thư mục đã tìm và mẫu đã dùng, KHÔNG ghi file đầu ra

### Requirement: Ánh xạ project theo khai báo tường minh

Script SHALL dùng một bảng ánh xạ khai báo tường minh từ tên hiển thị sang project ID, và SHALL so khớp **chính xác tuyệt đối**. Script MUST NOT dùng so khớp gần đúng, chuẩn hoá chuỗi, hay bất kỳ suy đoán nào.

Lý do: file CSV của Console KHÔNG chứa cột nào định danh project; thông tin đó chỉ nằm ở phần cuối tên file, và phần đó là **tên hiển thị** của project chứ không phải **project ID**. Hai định danh này không suy ra nhau được (`AI-sale_agent` ↔ `tranquil-post-471401-c1`).

Project ID trong bảng ánh xạ SHALL khớp với `dim_agent.gcp_project_id` trong `db/token_ledger.sqlite`.

#### Scenario: Tên hiển thị có trong bảng ánh xạ
- **WHEN** xử lý file có phần cuối tên là `AI-sale_agent`
- **THEN** mọi dòng của file mang `project = tranquil-post-471401-c1`

#### Scenario: Tên hiển thị lạ
- **WHEN** xử lý file có phần cuối tên không nằm trong bảng ánh xạ
- **THEN** script dừng, in ra tên hiển thị lạ đó cùng đường dẫn file, và KHÔNG ghi file đầu ra

#### Scenario: Bảng ánh xạ lệch với dim_agent
- **WHEN** một project ID trong bảng ánh xạ không tồn tại trong `dim_agent.gcp_project_id`
- **THEN** script dừng và nêu rõ project ID nào không tra được

### Requirement: Đọc đúng định dạng thô của Console

Script SHALL mở file bằng `encoding="utf-8-sig"` để xử lý BOM UTF-8.

Script SHALL bóc dấu phẩy ngăn nghìn khỏi cột `Usage amount` trước khi chuyển sang số nguyên (`"21,235"` → `21235`).

Script SHALL đọc mọi cột tiền bằng `decimal.Decimal` từ chuỗi gốc, KHÔNG qua `float`. Đẳng thức tiền tệ ở `nghiem-thu-gop-billing` không kiểm được nếu giá trị đã đi qua dấu phẩy động.

#### Scenario: Lượng dùng có dấu phẩy ngăn nghìn
- **WHEN** dòng có `Usage amount = "1,234,567"`
- **THEN** cột `so_luong` của đầu ra bằng số nguyên `1234567`

#### Scenario: Cột tiền giữ nguyên độ chính xác
- **WHEN** dòng có `Unrounded subtotal ($) = 0.053087`
- **THEN** giá trị được giữ nguyên 6 chữ số thập phân, không bị sai lệch dấu phẩy động

### Requirement: Giữ đủ năm cột tiền, `Unrounded subtotal` là cột chuẩn

Đầu ra SHALL chứa cả năm cột tiền của Google: `Cost`, `Savings programs`, `Other savings`, `Unrounded subtotal`, `Subtotal`.

Cột `chi_phi_usd` SHALL lấy giá trị từ `Unrounded subtotal ($)`. Script MUST NOT dùng `Cost ($)` hay `Subtotal ($)` cho cột này: hai cột đó làm tròn tới xu ở mức từng dòng, khiến 740/2.259 dòng hiện $0,00 dù mang tiền thật, và sai số lệch một chiều theo hướng báo thiếu.

#### Scenario: Dòng nhỏ hơn nửa xu
- **WHEN** dòng có `Unrounded subtotal = 0.001356` và `Subtotal = 0.00`
- **THEN** `chi_phi_usd` bằng `0.001356`, không phải `0.00`

#### Scenario: Đủ cột kiểm chứng
- **WHEN** đọc một dòng bất kỳ của file thô
- **THEN** đầu ra có đủ `chi_phi_usd`, `chi_phi_niem_yet_usd`, `giam_cam_ket_usd`, `giam_khac_usd`, `chi_phi_hoa_don_usd`

### Requirement: Phân loại SKU dùng lại quy tắc chung

Script SHALL gọi `db/quy_tac.py::suy_loai()` để phân loại SKU thành `cached` / `output` / `input`. Script MUST NOT chứa bản sao của quy tắc phân loại này.

Thứ tự kiểm bắt buộc là `cached → output → input`, và nằm ở `quy_tac.py`. Tên SKU chứa cả hai từ `output` và `input` (ví dụ `911A-8880-A243`: *"Generate content OUTPUT token count … short INPUT text"*), nên kiểm sai thứ tự làm 38,9% chi phí nhảy nhầm cột trong khi tổng vẫn đúng — hỏng im lặng.

#### Scenario: SKU chứa cả hai từ khoá
- **WHEN** gặp SKU `911A-8880-A243` tên `Generate content output token count gemini 2.5 flash short input text`
- **THEN** `loai` bằng `output`

#### Scenario: SKU không phân loại được
- **WHEN** `suy_loai()` trả về `None` cho một SKU
- **THEN** script dừng, in ra mã SKU, tên SKU đầy đủ và tổng tiền của SKU đó, và KHÔNG ghi file đầu ra

### Requirement: Ghi đầu ra có ngày trong tên

Script SHALL ghi kết quả vào `data/da_xu_ly/billing/billing_<YYYY-MM-DD>.csv`, trong đó `<YYYY-MM-DD>` là ngày chạy. Thư mục `data/da_xu_ly/` là nơi dành cho dữ liệu dẫn xuất; file thô ở `data/billing/` SHALL giữ nguyên, không bị sửa hay xoá.

Script MUST NOT ghi đè `data/billing/billing_gop_tru_CTDA.csv` — file này giữ vai trò mốc đối chiếu.

Đầu ra SHALL sắp xếp ổn định theo `(project, ngay, sku_id)` để hai lần chạy trên cùng đầu vào cho ra file giống hệt nhau.

#### Scenario: Chạy hai lần liên tiếp
- **WHEN** chạy script hai lần trên cùng bộ file đầu vào trong cùng một ngày
- **THEN** hai file đầu ra giống hệt nhau tới từng byte

#### Scenario: File thô và mốc đối chiếu không bị đụng
- **WHEN** script chạy xong
- **THEN** mọi file trong `data/billing/` giữ nguyên nội dung và thời điểm sửa đổi

