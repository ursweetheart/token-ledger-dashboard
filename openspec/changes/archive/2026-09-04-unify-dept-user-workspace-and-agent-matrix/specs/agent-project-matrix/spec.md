## ADDED Requirements

### Requirement: Agent usage is shown as a circular chart
Biểu đồ mức độ sử dụng agent SHALL là biểu đồ tròn có legend, và SHALL NOT là biểu đồ cột.

#### Scenario: Agents have usage in the period
- **WHEN** có agent phát sinh request trong kỳ
- **THEN** biểu đồ hiển thị tỷ trọng request của từng agent dưới dạng tròn kèm legend và nhãn loại biểu đồ ghi đúng là tròn

#### Scenario: Many agents are active
- **WHEN** số agent có request vượt ngưỡng hiển thị
- **THEN** các agent nhỏ nhất được gộp thành một lát `Agent khác` theo cùng quy tắc gộp đang dùng cho biểu đồ phòng ban

#### Scenario: No agent has usage
- **WHEN** không có agent nào phát sinh request
- **THEN** biểu đồ hiển thị trạng thái chưa có dữ liệu thay vì biểu đồ rỗng không giải thích

### Requirement: Matrix places projects on the vertical axis and units on the horizontal axis
Ma trận SHALL đặt project (agent) trên trục dọc làm các hàng và đơn vị trên trục ngang làm các cột.

#### Scenario: Matrix is rendered
- **WHEN** ma trận hiển thị
- **THEN** mỗi hàng là một project và mỗi cột là một đơn vị, tiêu đề ma trận phản ánh đúng chiều này

#### Scenario: Matrix is scrolled horizontally
- **WHEN** số cột vượt chiều rộng khả dụng
- **THEN** cột nhãn project dính bên trái và chỉ vùng ô dữ liệu cuộn ngang, trang không cuộn ngang theo

#### Scenario: Cell values are compared
- **WHEN** người dùng xem các ô
- **THEN** cường độ màu tương ứng số request và có chú giải ít/nhiều

### Requirement: Matrix drills down along the unit axis by level
Ma trận SHALL cho phép đi sâu theo cấp trên trục đơn vị từ phòng ban xuống đơn vị con rồi tới tài khoản, và SHALL cho phép quay lại cấp trên.

#### Scenario: Column header has child units
- **WHEN** người dùng click tiêu đề cột của một đơn vị có cấp con
- **THEN** các cột được thay bằng các đơn vị con của đơn vị đó, hàng project giữ nguyên, và số liệu chỉ còn trong phạm vi đơn vị đã chọn

#### Scenario: Column header is at the child-unit level
- **WHEN** người dùng click tiêu đề cột của một đơn vị con
- **THEN** các cột được thay bằng các tài khoản thuộc đơn vị con đó

#### Scenario: Column header has no child level
- **WHEN** đơn vị không có cấp con và không có tài khoản
- **THEN** tiêu đề cột không có chỉ dấu đi sâu và không phản hồi khi click

#### Scenario: User navigates back up
- **WHEN** người dùng click một cấp trên breadcrumb
- **THEN** ma trận trở về đúng cấp đó với đầy đủ các cột của cấp đó

#### Scenario: Current level is displayed
- **WHEN** ma trận đang ở bất kỳ cấp nào
- **THEN** breadcrumb hiển thị đường đi từ cấp gốc tới cấp hiện tại

#### Scenario: Global department filter changes
- **WHEN** người dùng đổi bộ lọc phòng ban toàn cục
- **THEN** ma trận trở về cấp gốc thay vì giữ đường đi không còn hợp lệ

#### Scenario: A specific user is selected in the matrix filter
- **WHEN** người dùng chọn một tài khoản trong bộ lọc user của ma trận
- **THEN** ma trận đi tới cấp chứa tài khoản đó và nêu rõ khi tài khoản không phát sinh usage trong kỳ

#### Scenario: Columns have no activity
- **WHEN** một đơn vị hoặc tài khoản không có request nào trong kỳ
- **THEN** cột đó bị ẩn, trừ khi tài khoản đó đang được chọn ở bộ lọc user
