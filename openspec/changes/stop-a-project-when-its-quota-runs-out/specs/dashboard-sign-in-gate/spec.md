## ADDED Requirements

### Requirement: Chưa có khoá thì dashboard không hiện ra

Khi chưa có khoá hợp lệ, trình duyệt SHALL chỉ hiển thị màn hình nhập khoá phủ kín khung nhìn.
Không phần nào của dashboard — thanh tab, bảng số, biểu đồ, thanh lọc — được hiện ra phía sau hay
bên dưới màn hình đó.

#### Scenario: Mở dashboard lần đầu trên một máy
- **WHEN** người dùng mở địa chỉ dashboard mà trình duyệt chưa nhớ khoá nào
- **THEN** SHALL thấy màn hình nhập khoá phủ kín
- **AND** MUST NOT thấy bất kỳ thành phần nào của dashboard

#### Scenario: Nhập đúng khoá
- **WHEN** người dùng nhập khoá đúng
- **THEN** màn hình nhập SHALL biến mất và dashboard hiện ra
- **AND** lần mở sau trên cùng máy SHALL không hỏi lại

#### Scenario: Nhập sai khoá
- **WHEN** máy chủ trả 401 cho khoá vừa nhập
- **THEN** màn hình SHALL ở nguyên, nói rõ khoá không đúng
- **AND** khoá sai MUST NOT được nhớ lại

#### Scenario: Khoá bị đổi ở máy chủ
- **WHEN** trình duyệt đang nhớ một khoá nay đã không còn đúng
- **THEN** màn hình nhập SHALL hiện lại
- **AND** SHALL nói rõ khoá có thể đã bị đổi

### Requirement: Cổng khoá không được chỉ là một lớp che

Màn hình nhập khoá SHALL là lớp hiển thị của một cơ chế thật: khi chưa có khoá, trình duyệt MUST
NOT tải về bất kỳ dòng dữ liệu nghiệp vụ nào.

Lý do: một trang tải hết dữ liệu rồi phủ một lớp lên trên thì mở công cụ nhà phát triển là thấy
hết. Cơ chế thật nằm ở máy chủ, và màn hình này chỉ làm cho nó trông đúng như nó vốn là.

#### Scenario: Soi lưu lượng mạng khi chưa nhập khoá
- **WHEN** kiểm tra các yêu cầu mạng mà trang gửi đi trước khi có khoá
- **THEN** MUST NOT có yêu cầu nào trả về dữ liệu nghiệp vụ

#### Scenario: Gọi thẳng API không qua trình duyệt
- **WHEN** một công cụ dòng lệnh gọi thẳng API mà không mang khoá
- **THEN** SHALL nhận 401
- **AND** kết quả MUST NOT phụ thuộc vào việc trình duyệt có hiện màn hình nhập hay không

### Requirement: Khoá không được đi qua địa chỉ URL

Trang SHALL nhận khoá từ ô nhập của người dùng. MUST NOT đọc khoá từ tham số trên địa chỉ URL, và
MUST NOT đặt khoá vào địa chỉ sau khi đăng nhập.

Lý do: khoá nằm trong URL là khoá đi vào lịch sử trình duyệt, vào nhật ký máy chủ, và vào mọi đường
liên kết được chia sẻ — những nơi không xoá lại được.

#### Scenario: Có người dán khoá vào URL
- **WHEN** địa chỉ mở ra mang một tham số trông như khoá
- **THEN** trang MUST NOT dùng giá trị đó để xác thực

#### Scenario: Sau khi đăng nhập thành công
- **WHEN** người dùng nhập khoá đúng
- **THEN** địa chỉ trên thanh URL MUST NOT chứa khoá
