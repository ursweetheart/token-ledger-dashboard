# crm-gateway-routing Specification

## Purpose
TBD - created by archiving change route-the-crm-agent-through-the-gateway. Update Purpose after archive.
## Requirements
### Requirement: Agent phải gọi được LLM qua Gateway mà không sửa logic nghiệp vụ
Khi một agent được đưa qua Gateway, hệ thống SHALL chỉ thay đổi lớp gọi LLM của agent ấy.
Logic nghiệp vụ — phân loại, đọc/ghi dữ liệu, thông báo — MUST NOT bị sửa.

#### Scenario: Đưa một agent qua Gateway
- **WHEN** một agent được cấu hình gọi qua Gateway
- **THEN** kết quả nghiệp vụ của nó SHALL không đổi so với khi gọi thẳng nhà cung cấp
- **AND** các đường gọi thẳng nhà cung cấp đang có MUST NOT bị sửa

#### Scenario: Đường lùi
- **WHEN** cần đưa agent trở lại gọi thẳng nhà cung cấp
- **THEN** việc đó SHALL làm được bằng cấu hình
- **AND** MUST NOT đòi sửa mã nguồn hay dựng lại ảnh container

#### Scenario: Mặc định khi chưa cấu hình gì
- **WHEN** biến cấu hình chọn đường gọi không được đặt
- **THEN** agent SHALL dùng đường gọi thẳng nhà cung cấp như trước
- **AND** MUST NOT tự đi qua Gateway

### Requirement: Mỗi lượt gọi phải quy được về đúng agent
Mọi lượt gọi đi qua Gateway SHALL mang đủ thông tin để sổ quy được nó về **đúng một** agent.
Một lượt gọi không quy được về agent nào MUST NOT bị bỏ qua trong im lặng.

#### Scenario: Lượt gọi mang tag định danh
- **WHEN** một lượt gọi của agent đi qua Gateway
- **THEN** dòng sổ tương ứng SHALL quy được về đúng agent ấy

#### Scenario: Một tuyến mang nhiều tag định danh
- **WHEN** một tuyến được cấu hình mang nhiều hơn một tag định danh agent
- **THEN** đó SHALL bị coi là cấu hình sai
- **AND** hệ thống MUST NOT quy các dòng ấy về một agent chọn tuỳ ý trong số đó

#### Scenario: Lượt gọi không có tag định danh
- **WHEN** một lượt gọi đi qua Gateway mà không mang tag định danh nào
- **THEN** số lượng và token của những dòng ấy SHALL được đếm và phơi ra
- **AND** MUST NOT bị loại bỏ mà không ai biết

### Requirement: Tên model agent gọi phải trỏ tới đúng model được khai
Tên model mà agent gửi lên SHALL giải ra đúng deployment mà người vận hành khai cho tên đó.
Hệ thống MUST NOT phục vụ một model khác trong im lặng.

#### Scenario: Vừa có tuyến thật vừa có bí danh cùng tên
- **WHEN** một tên model vừa là tên nhóm của một tuyến thật, vừa là khoá của một bí danh
- **THEN** đó SHALL bị coi là cấu hình sai và phải gỡ một trong hai
- **AND** MUST NOT để bí danh âm thầm che tuyến thật

#### Scenario: Model được khai không tồn tại ở nhà cung cấp
- **WHEN** nhà cung cấp không phục vụ model được khai
- **THEN** hệ thống SHALL báo lỗi
- **AND** MUST NOT tự đổi sang một model khác

#### Scenario: Đối chiếu model trong sổ
- **WHEN** một lượt gọi được ghi vào sổ
- **THEN** sổ SHALL ghi cả tên nhóm agent đã gọi và tên model thật đã phục vụ

### Requirement: Bí mật xác thực MUST NOT nằm trong mã nguồn
Thông tin xác thực với nhà cung cấp SHALL được tham chiếu từ bên ngoài mã nguồn và bên ngoài
tệp cấu hình được quản lý phiên bản.

#### Scenario: Khai khoá cho một tuyến
- **WHEN** một tuyến cần thông tin xác thực của nhà cung cấp
- **THEN** tệp cấu hình SHALL chỉ chứa tham chiếu, không chứa giá trị bí mật

#### Scenario: Agent giữ khoá nhà cung cấp
- **WHEN** một agent đã đi qua Gateway
- **THEN** agent ấy SHALL chỉ giữ khoá để tự xưng danh với Gateway
- **AND** MUST NOT còn giữ khoá của nhà cung cấp, để nó không thể đi vòng qua Gateway

### Requirement: Tín hiệu quá hạn mức phải tới được cơ chế lùi lịch của agent
Khi Gateway từ chối vì quá hạn mức, lỗi trả về agent SHALL ở dạng mà cơ chế lùi lịch sẵn có
của agent nhận ra được.

#### Scenario: Gateway trả quá hạn mức
- **WHEN** Gateway từ chối một lượt gọi vì quá hạn mức
- **THEN** agent SHALL đi vào nhánh lùi lịch dành cho quá hạn mức
- **AND** MUST NOT đi vào nhánh lùi lịch chung dành cho lỗi khác

#### Scenario: Ngưỡng hạn mức cao hơn nhịp tự giới hạn của agent
- **WHEN** hạn mức của Gateway cao hơn nhịp mà agent tự giới hạn
- **THEN** nhánh quá hạn mức SHALL được coi là **chưa kiểm chứng**
- **AND** MUST NOT được coi là đạt chỉ vì vận hành bình thường không thấy lỗi

### Requirement: Nghiệm thu MUST NOT gây tác dụng phụ ra bên ngoài
Phép nghiệm thu đường gọi LLM SHALL chỉ chạy đúng phần đã thay đổi. Nó MUST NOT ghi vào hệ
thống bên ngoài hay gửi thông báo cho người thật.

#### Scenario: Nghiệm thu đường gọi mới
- **WHEN** đường gọi LLM qua Gateway được nghiệm thu
- **THEN** phép nghiệm thu SHALL chứng minh được: xác thực, quy về agent, dòng trong sổ, và
  số hiện trên dashboard
- **AND** MUST NOT tải hay ghi dữ liệu nghiệp vụ thật, và MUST NOT gửi thông báo

#### Scenario: Agent không có chế độ chạy thử
- **WHEN** agent không có cờ tắt được các tác dụng phụ ấy
- **THEN** phép nghiệm thu SHALL gọi trực tiếp lớp gọi LLM
- **AND** MUST NOT chạy toàn bộ tiến trình nghiệp vụ để nghiệm thu
