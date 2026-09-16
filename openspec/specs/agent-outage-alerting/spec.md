# agent-outage-alerting Specification

## Purpose
TBD - created by archiving change keep-the-crm-agent-running-when-the-gateway-dies. Update Purpose after archive.
## Requirements
### Requirement: Đổi đường vì hạ tầng hỏng phải báo cho người vận hành

Khi agent đổi đường gọi vì Gateway hỏng, hệ thống SHALL báo cho người vận hành bằng thư điện tử.

Một dòng log MUST NOT được coi là đã báo. Sự cố ngày 10/09 đã đi qua hoàn toàn im lặng theo cách
đó: agent bỏ ba lô, ghi ba dòng log, và không ai biết cho tới khi có người đọc lại nhật ký.

#### Scenario: Agent chuyển sang đường thẳng

- **WHEN** agent chuyển từ Gateway sang gọi thẳng nhà cung cấp
- **THEN** hệ thống SHALL gửi một thư báo
- **AND** thư SHALL nói rõ thời điểm, lý do đổi đường, và đường đang dùng

#### Scenario: Agent quay về Gateway

- **WHEN** agent quay về gọi qua Gateway
- **THEN** hệ thống SHALL gửi một thư báo
- **AND** thư SHALL nói rõ sự cố kéo dài bao lâu

### Requirement: Thư gộp theo sự cố, không gộp theo lượt gọi

Một sự cố SHALL sinh ra đúng **hai** thư: một khi đổi sang đường thẳng, một khi quay về. Hệ thống
MUST NOT gửi một thư cho mỗi lượt gọi hỏng.

Một lô cỡ production có hàng nghìn lượt gọi. Gửi mỗi lỗi một thư SHALL làm người nhận tắt thông
báo, tức phép cảnh báo tự huỷ chính nó.

#### Scenario: Sự cố xảy ra giữa một lô lớn

- **WHEN** Gateway chết giữa một lô có hàng nghìn lượt gọi
- **THEN** hệ thống SHALL gửi đúng một thư cho lần đổi đường đó
- **AND** MUST NOT gửi thư cho từng lượt gọi hỏng

#### Scenario: Gateway chập chờn trong một khoảng ngắn

- **WHEN** agent đổi đường rồi quay về rồi lại đổi trong một khoảng ngắn
- **THEN** mỗi lần đổi trạng thái SHALL sinh đúng một thư
- **AND** số thư SHALL tỷ lệ với số lần đổi trạng thái, MUST NOT tỷ lệ với số lượt gọi

### Requirement: Gửi thư hỏng không được làm hỏng công việc đang chạy

Việc gửi thư SHALL không bao giờ làm lỗi lan ra công việc đang chạy. Gửi hỏng thì hệ thống SHALL
ghi log rồi chạy tiếp.

Báo động là việc phụ; xử lý dữ liệu là việc chính. Đây là cùng một thứ tự ưu tiên mà quyết định
ngày 10/09 đặt ra cho Gateway.

#### Scenario: Máy chủ thư không phản hồi

- **WHEN** việc gửi thư thất bại vì bất kỳ lý do gì
- **THEN** agent SHALL ghi log mức lỗi
- **AND** lô đang xử lý SHALL chạy tiếp bình thường
- **AND** lỗi gửi thư MUST NOT làm dừng agent

### Requirement: Đường gửi thư thường đứng cạnh đường sẵn có, không thay thế

Hệ thống SHALL có một đường gửi thư dùng được ngay mà không cần thông tin đăng nhập của tổ chức,
và đường này SHALL đứng **cạnh** đường gửi qua dịch vụ thư của tổ chức chứ không thay thế nó.

Đường của tổ chức là đường cho production. Nó hiện chưa gửi được thư nào vì thiếu thông tin đăng
nhập, không phải vì sai thiết kế.

#### Scenario: Chọn đường gửi

- **WHEN** hệ thống cần gửi một thư báo
- **THEN** đường gửi SHALL chọn được bằng cấu hình
- **AND** cả hai đường SHALL cùng tồn tại trong mã nguồn

#### Scenario: Mật khẩu của đường gửi thư thường

- **WHEN** đường gửi thư thường cần mật khẩu
- **THEN** mật khẩu SHALL đọc từ biến môi trường
- **AND** MUST NOT nằm trong bất kỳ tệp nào được theo dõi bởi git

### Requirement: Đường báo động phải được kiểm chứng bằng một thư thật

Trước khi đường báo động được coi là dùng được, hệ thống SHALL gửi thành công một thư thật và thư
ấy SHALL được xác nhận là đã tới hộp thư người nhận.

Thư rời khỏi máy MUST NOT được coi là thư đã tới. Máy chủ thư có thể xếp thư vào thư rác hoặc chặn
hẳn, và một phép báo động không tới nơi thì không khác gì không có.

#### Scenario: Nghiệm thu đường báo động

- **WHEN** nghiệm thu đường gửi thư
- **THEN** phép nghiệm thu SHALL dựa trên việc người nhận xác nhận đã thấy thư
- **AND** MUST NOT dựa chỉ vào việc lệnh gửi không báo lỗi
