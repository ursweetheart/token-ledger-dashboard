## ADDED Requirements

### Requirement: Department and user analytics share one workspace
Hệ thống SHALL cung cấp một tab `Phòng ban & User` chứa cả tổng hợp phòng ban và chi tiết tài khoản, và SHALL không duy trì hai tab độc lập có nội dung trùng lặp.

#### Scenario: No department is selected
- **WHEN** người dùng mở tab hợp nhất mà chưa chọn phòng ban
- **THEN** UI hiển thị tổng quan mọi phòng ban và danh sách user trong toàn bộ phạm vi

#### Scenario: A department is selected
- **WHEN** người dùng chọn hoặc click một phòng ban
- **THEN** KPI, biểu đồ và bảng user cập nhật theo phòng ban đó

### Requirement: User activity naming and actions match the meeting decision
KPI user SHALL dùng tên `Tài khoản hoạt động`; section trạng thái đồng bộ và hành động nhắc đào tạo SHALL bị loại bỏ.

#### Scenario: User section is rendered
- **WHEN** phần user xuất hiện trong tab hợp nhất
- **THEN** không có nhãn `Tỷ lệ áp dụng`, không có bảng trạng thái đồng bộ và không có nút `Nhắc đào tạo`

### Requirement: Global user filter targets a real account
Bộ lọc User SHALL sử dụng userId hoặc username thực và SHALL NOT sử dụng nhóm user làm giá trị thay thế.

#### Scenario: User is selected
- **WHEN** người dùng chọn một tài khoản có usage gắn userId
- **THEN** mọi thành phần có dữ liệu user-level chỉ tổng hợp các bản ghi của tài khoản đó

#### Scenario: Selected user has no usage
- **WHEN** user tồn tại nhưng không phát sinh request trong kỳ
- **THEN** KPI hiển thị zero đo được và bảng không gán dữ liệu tổng của agent cho user

#### Scenario: Source cannot identify users
- **WHEN** bản ghi nguồn không có userId
- **THEN** bản ghi không tham gia kết quả user filter và UI thông báo giới hạn nguồn dữ liệu

### Requirement: Active users are derived from requests in the selected period
Hệ thống SHALL tính user hoạt động bằng số user distinct có ít nhất một request trong phạm vi thời gian và bộ lọc, chỉ đối với agent yêu cầu đăng nhập.

#### Scenario: User requested a login-required agent
- **WHEN** user có request lớn hơn zero với agent `loginRequired=true`
- **THEN** user được tính hoạt động đúng một lần trong kỳ

#### Scenario: Agent does not identify users
- **WHEN** agent không yêu cầu đăng nhập hoặc usage không có userId
- **THEN** usage đó không làm tăng active-user count

### Requirement: Department hierarchy supports progressive drilldown
Không gian phòng ban SHALL hỗ trợ cây đơn vị khi metadata `parentId` tồn tại và SHALL hoạt động một cấp khi metadata phân cấp chưa có.

#### Scenario: Department has children
- **WHEN** người dùng click một phòng ban có đơn vị con
- **THEN** UI cập nhật cấp hiện tại, breadcrumb và dữ liệu con

#### Scenario: Department hierarchy is flat
- **WHEN** mọi phòng ban không có parentId
- **THEN** UI ẩn điều khiển drilldown mà không làm mất bảng và biểu đồ phòng ban
