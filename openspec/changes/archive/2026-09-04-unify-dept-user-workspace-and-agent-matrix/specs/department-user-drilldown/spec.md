## ADDED Requirements

### Requirement: Department and user analytics live in one tab
Hệ thống SHALL cung cấp một tab duy nhất tên `Phòng ban & User` chứa cả tổng hợp phòng ban và chi tiết tài khoản, và SHALL NOT còn tab `User` riêng trong dải điều hướng.

#### Scenario: User inspects the tab bar
- **WHEN** người dùng xem dải tab
- **THEN** có tab `Phòng ban & User` và không có tab `User` độc lập

#### Scenario: Tab is opened
- **WHEN** người dùng mở tab hợp nhất
- **THEN** KPI phòng ban, biểu đồ phòng ban, bảng chi tiết drilldown, KPI tài khoản, biểu đồ người dùng theo ngày và danh sách tài khoản không hoạt động đều hiển thị trong cùng tab

### Requirement: No sync-status content remains in the user area
Phần user SHALL NOT chứa bảng, nhãn hoặc mô tả nào về trạng thái đồng bộ người dùng.

#### Scenario: User area is rendered
- **WHEN** phần user hiển thị
- **THEN** không có bảng trạng thái đồng bộ và không có văn bản nào nhắc tới trạng thái đồng bộ, kể cả trong banner giới thiệu tab

### Requirement: Department detail table drills down to accounts
Bảng chi tiết theo phòng ban SHALL cho phép mở từng phòng ban để xem đơn vị con và tài khoản thuộc phòng ban đó, giữ nguyên bộ lọc và kỳ đang áp dụng của dashboard.

#### Scenario: Department with child units is expanded
- **WHEN** người dùng click một phòng ban có đơn vị con
- **THEN** bảng chèn các dòng đơn vị con ngay dưới dòng phòng ban, thụt lề theo cấp, với số liệu của cùng kỳ và cùng bộ lọc đang áp dụng

#### Scenario: Child unit is expanded
- **WHEN** người dùng click một đơn vị con
- **THEN** bảng chèn các dòng tài khoản của đơn vị đó, thụt lề sâu hơn một cấp

#### Scenario: Department without child units is expanded
- **WHEN** người dùng click một phòng ban không có đơn vị con
- **THEN** bảng chèn trực tiếp các dòng tài khoản, không chèn cấp trung gian rỗng

#### Scenario: Row is collapsed
- **WHEN** người dùng click lại một dòng đang mở
- **THEN** mọi dòng con của dòng đó bị thu lại

#### Scenario: Filters change while rows are expanded
- **WHEN** người dùng đổi khoảng thời gian hoặc bộ lọc trong khi có dòng đang mở
- **THEN** các dòng đang mở giữ nguyên trạng thái mở và số liệu cập nhật theo phạm vi mới

#### Scenario: Child totals are compared with parent
- **WHEN** người dùng cộng số liệu các dòng con của một dòng cha
- **THEN** tổng bằng đúng số liệu của dòng cha

### Requirement: Department detail table reports provisioning and adoption
Bảng chi tiết theo phòng ban SHALL có cột tổng số tài khoản được cấp và cột tỷ lệ tài khoản hoạt động trên tổng số cấp.

#### Scenario: Unit has provisioned users and activity
- **WHEN** đơn vị có số cấp được khai báo và có tài khoản phát sinh request
- **THEN** bảng hiển thị tổng số cấp, số tài khoản hoạt động và tỷ lệ hoạt động trên tổng

#### Scenario: Adoption rate is below configured thresholds
- **WHEN** tỷ lệ hoạt động thấp hơn ngưỡng cảnh báo hoặc ngưỡng nghiêm trọng đã cấu hình
- **THEN** ô tỷ lệ được tô màu theo đúng mức ngưỡng đó

#### Scenario: Provisioned count is unavailable
- **WHEN** đơn vị không có số tài khoản được cấp
- **THEN** cột tổng số tài khoản và cột tỷ lệ hiển thị trạng thái chưa có dữ liệu, không hiển thị 100% và không chia cho zero

#### Scenario: Row is an account
- **WHEN** dòng đang hiển thị là một tài khoản
- **THEN** các cột chỉ có nghĩa ở cấp đơn vị hiển thị dấu không áp dụng thay vì số

### Requirement: Active users are counted from requests in the period
Số tài khoản hoạt động SHALL là số tài khoản distinct có ít nhất một request trong kỳ và trong phạm vi bộ lọc, và SHALL NOT là số tài khoản được cấp theo snapshot.

#### Scenario: Account has requests in the period
- **WHEN** tài khoản có request lớn hơn zero trong kỳ
- **THEN** tài khoản được tính hoạt động đúng một lần

#### Scenario: Account is provisioned but has no requests
- **WHEN** tài khoản tồn tại nhưng không có request trong kỳ
- **THEN** tài khoản được tính vào tổng số cấp nhưng không tính vào số hoạt động
