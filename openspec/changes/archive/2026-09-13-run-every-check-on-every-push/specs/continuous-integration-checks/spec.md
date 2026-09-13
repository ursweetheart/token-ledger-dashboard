## ADDED Requirements

### Requirement: Mỗi lần đẩy code lên kho chung đều phải chạy đủ bộ kiểm hiện có

Khi code được đẩy lên kho chung hoặc được mở pull request, hệ thống SHALL chạy toàn bộ phép kiểm tự
động đang có trong repo, không cần ai gõ lệnh.

Kết quả SHALL nhìn thấy được ở nơi người ta quyết định gộp code. Một bộ kiểm chỉ chạy khi có người
nhớ chạy MUST NOT được coi là đã thoả yêu cầu này — đó chính là tình trạng trước change, và nó đã để
lọt một cấu hình dành riêng cho máy phát triển vào cây làm việc mà không ai bị nhắc.

#### Scenario: Đẩy code có phép kiểm hỏng

- **WHEN** code được đẩy lên kho chung và có ít nhất một phép kiểm không đạt
- **THEN** kết quả SHALL là hỏng
- **AND** SHALL nêu rõ nhóm nào hỏng và phép kiểm nào hỏng

#### Scenario: Đẩy code mà mọi phép kiểm đều đạt

- **WHEN** mọi phép kiểm đều đạt
- **THEN** kết quả SHALL là đạt
- **AND** SHALL nêu số phép kiểm đã chạy của từng nhóm

#### Scenario: Một nhóm kiểm hỏng, các nhóm khác vẫn phải chạy

- **WHEN** một nhóm kiểm hỏng
- **THEN** các nhóm còn lại SHALL vẫn chạy tới cùng và vẫn báo kết quả riêng
- **AND** MUST NOT dừng theo nhóm hỏng đầu tiên

### Requirement: Bộ kiểm phải báo số phép đã chạy, không chỉ báo đạt

Mỗi nhóm kiểm SHALL báo số phép kiểm nó thực sự chạy, và số đó SHALL được so với mốc đã chốt. Một
lần chạy không thực hiện phép kiểm nào MUST NOT cho ra kết quả đạt.

Mã thoát bằng 0 không đủ làm bằng chứng. Lệnh gọi bộ kiểm JavaScript dựa vào việc vỏ lệnh nở được
mẫu tên tệp; nở hụt thì lệnh vẫn thoát sạch mà không kiểm gì. Đây là cùng nguyên tắc mà
`automated-check-coverage` đã chốt cho bộ kiểm dữ liệu, nay áp cho bộ kiểm mã.

Mốc đã đo ngày 13/09: **51** phép kiểm JavaScript, **11** phép kiểm Python.

#### Scenario: Mẫu tên tệp không khớp tệp nào

- **WHEN** lệnh chạy kiểm không tìm thấy tệp kiểm nào
- **THEN** kết quả SHALL là hỏng
- **AND** MUST NOT là đạt, kể cả khi mã thoát bằng 0

#### Scenario: Số phép kiểm ít hơn mốc đã chốt

- **WHEN** số phép kiểm chạy được ít hơn số đã chốt
- **THEN** kết quả SHALL là hỏng
- **AND** SHALL nêu số mong đợi, số thật, và chỗ phải sửa nếu việc giảm là có chủ ý

#### Scenario: Thêm phép kiểm mới

- **WHEN** người phát triển thêm phép kiểm mới và số thật lớn hơn mốc
- **THEN** kết quả SHALL là hỏng cho tới khi mốc được cập nhật
- **AND** thông điệp SHALL nói rõ đây là việc cập nhật mốc, không phải lỗi mã

### Requirement: Bộ kiểm phải chạy được trên một máy sạch, không cài thêm gói

Bộ kiểm SHALL chạy được trên một máy chỉ có trình thông dịch, không cần cài gói phụ thuộc nào,
không cần PostgreSQL, không cần Docker.

Đây là tính chất đang có thật chứ không phải mong muốn: repo không có `package.json`, `pytest.ini`,
`pyproject.toml`, `setup.cfg`, `tox.ini` hay `Makefile`; phần JavaScript dùng bộ chạy kiểm có sẵn
của Node; `psycopg2` được nạp bên trong hàm chứ không ở đầu tệp. Tính chất này rẻ và dễ mất — chỉ
cần một lời `import` đặt sai chỗ. Chạy trên máy ảo sạch chính là phép đo giữ nó.

#### Scenario: Một gói bên ngoài bị nạp ở đầu tệp

- **WHEN** một tệp trong đường nạp của bộ kiểm nạp gói bên ngoài ở mức tệp
- **AND** máy chạy kiểm không cài gói đó
- **THEN** kết quả SHALL là hỏng ngay ở lần chạy kế tiếp

#### Scenario: Bộ kiểm cần database

- **WHEN** một phép kiểm đòi kết nối tới database thật mới chạy được
- **THEN** kết quả SHALL là hỏng
- **AND** phép kiểm đó SHALL được viết lại bằng vật giả, hoặc tách khỏi nhóm kiểm chạy theo mỗi lần
  đẩy code

### Requirement: Cấu hình dành riêng cho một môi trường MUST NOT đi lên nhánh chính

Tệp cấu hình đi theo git MUST NOT ghim địa chỉ mạng của một môi trường cụ thể. Địa chỉ khác nhau
giữa các máy SHALL được đọc từ cấu hình ngoài git.

Trước change này, phần địa chỉ trong khai báo cổng của dịch vụ `web` bị ghi cứng trong khi phần số
cổng đã là biến, nên mỗi lần đổi môi trường phải sửa tay — và ngày 13/09 đã đo được đúng trạng thái
quên sửa, ngay dưới một dòng chú thích in hoa nhắc phải sửa.

Yêu cầu này viết theo **nguyên tắc**, không theo một địa chỉ cụ thể, để nó còn đúng khi có thêm máy
chủ thứ ba.

#### Scenario: Địa chỉ của một môi trường bị ghi cứng

- **WHEN** một tệp cấu hình theo git khai địa chỉ mạng cố định ở phần cổng
- **THEN** kết quả SHALL là hỏng
- **AND** SHALL nêu tệp, dòng, và biến nên dùng thay cho nó

#### Scenario: Địa chỉ đọc từ biến, có giá trị mặc định

- **WHEN** địa chỉ được đọc từ biến môi trường và mặc định là địa chỉ cục bộ
- **THEN** kết quả SHALL là đạt

#### Scenario: Máy chủ cần địa chỉ khác máy phát triển

- **WHEN** máy chủ cần mở dịch vụ ra mạng nội bộ
- **THEN** việc đó SHALL làm được bằng cấu hình ngoài git
- **AND** MUST NOT đòi sửa tệp theo git
