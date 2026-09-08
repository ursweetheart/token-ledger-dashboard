## ADDED Requirements

### Requirement: Every department string resolves to exactly one canonical unit
Hệ thống SHALL phân giải mọi giá trị phòng ban trong dữ liệu usage và dữ liệu tài khoản về một định danh đơn vị (`unitId`) duy nhất, và SHALL NOT hiển thị nhiều biến thể tên của cùng một đơn vị thành các dòng hoặc cột riêng biệt.

#### Scenario: Data contains name variants of the same unit
- **WHEN** dữ liệu chứa cả `PBH1` và `Phòng Bán hàng 1`
- **THEN** cả hai phân giải về cùng một `unitId` và mọi bảng, biểu đồ, ma trận hiển thị chúng thành một đơn vị duy nhất với số liệu đã cộng dồn

#### Scenario: Data contains a department with no declared alias
- **WHEN** dữ liệu chứa một tên phòng ban không có trong bảng alias
- **THEN** hệ thống tự sinh một đơn vị cấp 1 cho tên đó và giữ nguyên toàn bộ số liệu, không loại bỏ và không gán vào đơn vị khác

#### Scenario: Excluded department is present
- **WHEN** tên phòng ban thuộc danh sách loại trừ
- **THEN** đơn vị đó không xuất hiện trong bất kỳ bảng, biểu đồ hoặc bộ lọc nào

### Requirement: Provisioned user counts are keyed by unit identifier
Số tài khoản được cấp SHALL được tra cứu theo `unitId` và SHALL NOT được tra cứu theo chuỗi tên phòng ban.

#### Scenario: Provisioned count is configured for a unit
- **WHEN** đơn vị có số cấp được khai báo
- **THEN** hệ thống dùng đúng số đó làm mẫu số cho mọi tỷ lệ áp dụng của đơn vị

#### Scenario: Provisioned count is not configured
- **WHEN** đơn vị không có số cấp được khai báo
- **THEN** hệ thống hiển thị trạng thái chưa có dữ liệu cho tỷ lệ áp dụng và SHALL NOT dùng số user hoạt động làm mẫu số

#### Scenario: Parent unit aggregates children
- **WHEN** một đơn vị có các đơn vị con
- **THEN** số tài khoản được cấp của đơn vị cha bằng tổng số cấp của các đơn vị con

### Requirement: Organization tree supports three levels with graceful degradation
Hệ thống SHALL hỗ trợ cây đơn vị tối đa ba cấp `phòng ban → đơn vị con → tài khoản`, và SHALL hoạt động đúng khi một đơn vị chỉ có một cấp.

#### Scenario: Unit has child units
- **WHEN** đơn vị có đơn vị con
- **THEN** UI cho phép mở xuống đơn vị con trước khi tới danh sách tài khoản

#### Scenario: Unit has no child units
- **WHEN** đơn vị không có đơn vị con
- **THEN** UI mở trực tiếp ra danh sách tài khoản và không hiển thị cấp trung gian rỗng

### Requirement: Demo account layer covers every unit with usage and reconciles to unit totals
Danh sách tài khoản demo SHALL phủ mọi đơn vị có usage, và tổng số liệu của các tài khoản thuộc một đơn vị SHALL bằng đúng tổng số liệu của đơn vị đó.

#### Scenario: Unit has usage in the period
- **WHEN** một đơn vị có request lớn hơn zero trong kỳ
- **THEN** đơn vị đó có tài khoản để mở drilldown, không hiển thị danh sách rỗng

#### Scenario: Account figures are summed
- **WHEN** cộng request và token của mọi tài khoản thuộc một đơn vị
- **THEN** tổng bằng đúng request và token của đơn vị đó ở mọi cấp của cây

#### Scenario: Rendering is repeated
- **WHEN** dashboard render lại cùng một kỳ và cùng bộ lọc
- **THEN** số liệu của từng tài khoản không thay đổi giữa các lần render

### Requirement: Account-level figures are labelled as allocated demo data
Mọi khối UI hiển thị số liệu ở cấp tài khoản SHALL mang nhãn cho biết đây là dữ liệu phân bổ demo, không phải số đo theo tài khoản.

#### Scenario: Account rows are displayed
- **WHEN** người dùng mở drilldown tới cấp tài khoản
- **THEN** khối đó hiển thị nhãn dữ liệu phân bổ demo kèm giải thích rằng nguồn hiện tại không có định danh user

#### Scenario: Matrix drills down to accounts
- **WHEN** ma trận hiển thị cột ở cấp tài khoản
- **THEN** ma trận hiển thị cùng nhãn dữ liệu phân bổ demo
