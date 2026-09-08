# provider-source-reach Specification

## Purpose
TBD - created by archiving change stop-treating-a-failed-call-as-a-free-call. Update Purpose after archive.
## Requirements
### Requirement: Đường kéo phải với được tới project ngoài danh sách sản xuất
`scripts/pull_monitoring.py` SHALL kéo được số liệu của một project bất kỳ được gọi tên, kể cả
project không thuộc danh sách bảy project sản xuất. Hành vi mặc định khi không truyền tham số
nào SHALL không đổi.

#### Scenario: Kéo một project ngoài danh sách
- **WHEN** người chạy truyền tên một project không có trong danh sách mặc định
- **THEN** script SHALL kéo project đó và MUST NOT báo lỗi vì nó lạ

#### Scenario: Chạy không tham số
- **WHEN** script chạy không có tham số nào
- **THEN** nó SHALL kéo đúng bảy project sản xuất như trước

### Requirement: Đường kéo phải chọn được tài khoản Google
Script SHALL nhận tham số chọn tài khoản Google, vì project mà Gateway gọi tới nằm trên một
tài khoản khác với bảy project sản xuất. Khi không truyền, script SHALL dùng tài khoản đang
hoạt động của `gcloud`, đúng như hành vi hiện tại.

#### Scenario: Kéo bằng tài khoản thứ hai
- **WHEN** người chạy chỉ định một tài khoản đã đăng nhập khác tài khoản mặc định
- **THEN** script SHALL lấy khoá truy cập của đúng tài khoản đó

#### Scenario: Tài khoản chưa đăng nhập
- **WHEN** tài khoản được chỉ định chưa có khoá truy cập
- **THEN** script SHALL dừng và nói rõ tài khoản nào thiếu, MUST NOT lặng lẽ lùi về tài khoản mặc định

### Requirement: Thư mục kết quả phải phân biệt được theo tài khoản
Tên thư mục của mỗi lần kéo SHALL mang cả tài khoản, để hai tài khoản kéo cùng một ngày với
cùng độ mịn không ghi đè nhau.

#### Scenario: Hai tài khoản kéo cùng ngày
- **WHEN** hai lần kéo diễn ra cùng ngày, cùng độ mịn, bằng hai tài khoản khác nhau
- **THEN** chúng SHALL ghi vào hai thư mục khác nhau và không lần nào mất dữ liệu

### Requirement: Phép đo hạn mức trả về nhiều nhánh phải được chọn, và phải chứng minh là trùng
Bộ nạp SHALL lấy đúng một nhánh khi phép đo token của nhà cung cấp trả về nhiều chuỗi cho cùng
một lượng token — tách theo tên hạn mức — và SHALL so nhánh đó với các nhánh còn lại. Nếu các
nhánh không bằng nhau, bộ nạp SHALL dừng và báo. Nó MUST NOT cộng gộp các nhánh, và MUST NOT
tự chọn một nhánh mà không kiểm.

#### Scenario: Hai nhánh hạn mức mang cùng một con số
- **WHEN** nhánh theo ngày và nhánh theo phút cùng báo một lượng token
- **THEN** bộ nạp SHALL nạp con số đó đúng một lần

#### Scenario: Các nhánh không bằng nhau
- **WHEN** hai nhánh hạn mức báo hai con số khác nhau
- **THEN** bộ nạp SHALL dừng và nêu cả hai con số, MUST NOT chọn bừa một bên

