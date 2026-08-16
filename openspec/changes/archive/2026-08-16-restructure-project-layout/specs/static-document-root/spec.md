## ADDED Requirements

### Requirement: Máy chủ tĩnh chỉ phục vụ được nội dung công khai

Máy chủ tĩnh phục vụ dashboard SHALL có document root là `web/`, và MUST NOT có bất kỳ
đường đi nào tới nội dung ngoài `web/`. Ranh giới này SHALL được bảo đảm bởi **vị trí
thư mục**, không bởi cấu hình, danh sách loại trừ, hay quy tắc viết lại đường dẫn — vì
mọi cơ chế cấu hình đều có thể bị quên khi người khác chạy lại.

Mọi tài liệu hướng dẫn chạy dashboard SHALL ghi lệnh khởi động ở dạng đã đứng trong
`web/` và đã ràng buộc địa chỉ nghe về loopback.

#### Scenario: Bí mật và dữ liệu cá nhân không tải được

- **WHEN** máy chủ tĩnh đang chạy và ai đó yêu cầu `/.env`, `/db/token_ledger.sqlite`,
  `/var/token_ledger.sqlite`, hoặc `/.git/config`
- **THEN** máy chủ trả về 404 cho cả bốn đường dẫn
- **AND** không đường dẫn nào trong số đó trả về nội dung file thật, kể cả một phần

#### Scenario: Đi ngược lên trên bị chặn

- **WHEN** ai đó yêu cầu một đường dẫn chứa `..` nhằm thoát khỏi document root, kể cả
  dạng mã hoá `..%2f` hoặc `%2e%2e/`
- **THEN** máy chủ trả về 404 và không phục vụ nội dung nằm ngoài `web/`

#### Scenario: Không liệt kê được thư mục chứa dữ liệu

- **WHEN** ai đó yêu cầu `/.git/`, `/data/`, hoặc `/var/`
- **THEN** máy chủ trả về 404, không trả về bảng liệt kê nội dung thư mục
- **AND** người truy cập không tra được tên file để yêu cầu tiếp

#### Scenario: Không nghe trên mạng ngoài

- **WHEN** máy chủ tĩnh khởi động theo đúng lệnh trong tài liệu
- **THEN** nó chỉ nghe trên `127.0.0.1`, không phải `0.0.0.0`
- **AND** một máy khác trong cùng mạng LAN không kết nối được tới cổng đó

#### Scenario: Dashboard vẫn nạp đủ tài nguyên

- **WHEN** trình duyệt mở `http://127.0.0.1:8080/` với máy chủ chạy trong `web/`
- **THEN** cả 6 tài nguyên mà `index.html` tham chiếu — CSS, thư viện biểu đồ, ảnh
  logo, và 3 file JavaScript — đều trả về 200
- **AND** không yêu cầu **cùng gốc** nào trả về 404
- **AND** phép kiểm này bỏ qua yêu cầu tới máy chủ ngoài, vì `dashboard.css` có
  `@import` phông chữ từ Google — trạng thái của nó phụ thuộc máy có mạng hay không,
  không phụ thuộc cấu trúc thư mục

#### Scenario: Bấm đúp file vẫn xem được, không cần máy chủ

- **WHEN** người dùng mở `web/index.html` trực tiếp bằng giao thức `file://`
- **THEN** trang nạp đủ CSS, thư viện biểu đồ và JavaScript qua đường dẫn tương đối
- **AND** dashboard hiển thị bằng dữ liệu dự phòng đã vá sẵn, đúng như trước khi dời
- **AND** trang vẫn dùng được khi không có mạng, chỉ hiển thị bằng phông dự phòng của
  hệ thống thay vì phông tải từ Google
