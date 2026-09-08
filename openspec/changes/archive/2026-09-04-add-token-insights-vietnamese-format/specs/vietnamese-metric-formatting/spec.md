## ADDED Requirements

### Requirement: Vietnamese dong is the primary display currency
Hệ thống SHALL hiển thị các giá trị chi phí chính bằng VNĐ theo locale `vi-VN`, ký hiệu `₫` và không có chữ số thập phân.

#### Scenario: USD cost is rendered on a KPI card
- **WHEN** chi phí gốc là `46.85 USD` và tỷ giá cấu hình là `25.200 VNĐ/USD`
- **THEN** giá trị chính hiển thị `1.180.620 ₫`

### Requirement: USD remains available for reconciliation
Hệ thống SHALL giữ giá trị USD gốc và tỷ giá cấu hình trong tooltip hoặc dòng tham chiếu của các giá trị đã quy đổi.

#### Scenario: User inspects converted cost
- **WHEN** người dùng xem tooltip hoặc chi tiết của giá trị VNĐ
- **THEN** hệ thống hiển thị giá trị USD gốc và tỷ giá đã dùng để quy đổi

### Requirement: Exchange rate provenance is explicit
Hệ thống MUST phân biệt tỷ giá cấu hình với tỷ giá realtime và SHALL hiển thị thời điểm/nguồn nếu metadata đó tồn tại.

#### Scenario: Static configured rate is used
- **WHEN** dashboard sử dụng hằng số hoặc giá trị localStorage làm tỷ giá
- **THEN** UI ghi “tỷ giá cấu hình” và không mô tả là realtime

### Requirement: Token quantities use Vietnamese compact units
Hệ thống SHALL định dạng token rút gọn bằng `nghìn`, `triệu`, `tỷ` và dấu phẩy thập phân theo locale Việt Nam.

#### Scenario: Millions of tokens
- **WHEN** giá trị token là `69.100.000`
- **THEN** card hiển thị `69,1 triệu token`

#### Scenario: Thousands of tokens
- **WHEN** giá trị token là `54.400`
- **THEN** card hiển thị `54,4 nghìn token`

#### Scenario: Billions of tokens
- **WHEN** giá trị token là `1.250.000.000`
- **THEN** card hiển thị `1,3 tỷ token`

#### Scenario: Small token count
- **WHEN** giá trị token nhỏ hơn `1.000`
- **THEN** card hiển thị số đầy đủ mà không gắn hậu tố rút gọn

### Requirement: Full precision remains discoverable
Hệ thống SHALL cung cấp số token nguyên đầy đủ trong tooltip hoặc bảng chi tiết khi card/chart dùng đơn vị rút gọn.

#### Scenario: User inspects a compact token value
- **WHEN** người dùng xem tooltip của `69,1 triệu token`
- **THEN** tooltip hiển thị `69.100.000 token`

### Requirement: Formatting is consistent across dashboard surfaces
Card, delta, chart label, chart tooltip và bảng SHALL dùng cùng formatter theo loại metric; trục chart có thể rút gọn nhưng tooltip SHALL ưu tiên số đầy đủ.

#### Scenario: Same cost appears in card and table
- **WHEN** cùng một chi phí xuất hiện ở KPI card và bảng chi tiết
- **THEN** cả hai dùng VNĐ làm đơn vị chính và quy đổi từ cùng giá trị USD/tỷ giá

### Requirement: Conversion does not change calculation precision
Hệ thống MUST thực hiện aggregate, comparison, threshold và forecast bằng giá trị gốc trước khi định dạng hoặc làm tròn.

#### Scenario: Rounded values are compared
- **WHEN** hai chi phí VNĐ có giá trị hiển thị làm tròn giống nhau nhưng USD gốc khác nhau
- **THEN** delta và threshold được tính từ giá trị USD gốc thay vì chuỗi hiển thị
