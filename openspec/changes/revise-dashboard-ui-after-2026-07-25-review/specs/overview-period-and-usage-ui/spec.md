## ADDED Requirements

### Requirement: Comparison labels identify their baseline
Mọi KPI có so sánh SHALL gọi tên kỳ so sánh là kỳ trước hoặc cùng kỳ và SHALL hiển thị giá trị nền khi dữ liệu nền tồn tại.

#### Scenario: Previous-period comparison is available
- **WHEN** KPI có dữ liệu hiện tại và kỳ trước hợp lệ
- **THEN** delta hiển thị hướng, phần trăm, nhãn `so với kỳ trước` hoặc `KT` và giá trị kỳ trước

#### Scenario: Same-period comparison is available
- **WHEN** KPI có dữ liệu hiện tại và cùng kỳ hợp lệ
- **THEN** delta hiển thị hướng, phần trăm, nhãn `so với cùng kỳ` hoặc `CK` và giá trị cùng kỳ

#### Scenario: Baseline is unavailable
- **WHEN** kỳ so sánh không có dữ liệu hợp lệ
- **THEN** UI hiển thị trạng thái chưa có dữ liệu và không tạo phần trăm thay đổi

### Requirement: Overview trend charts follow the agreed decision order
Hàng biểu đồ xu hướng Tổng quan SHALL sắp xếp Chi phí, Token, Request rồi Tỷ lệ thành công từ trái sang phải trên màn hình đủ rộng và theo cùng thứ tự khi xếp dọc.

#### Scenario: Overview renders on desktop
- **WHEN** người dùng mở Tổng quan ở viewport desktop
- **THEN** các chart xuất hiện theo thứ tự Chi phí → Token → Request → Tỷ lệ thành công

#### Scenario: Overview renders responsively
- **WHEN** grid chuyển thành hai hoặc một cột
- **THEN** thứ tự đọc trong DOM vẫn là Chi phí → Token → Request → Tỷ lệ thành công

### Requirement: Overview presents active-user coverage
Card User hoạt động SHALL hiển thị số user có request, tổng tài khoản được cấp còn hiệu lực và tỷ lệ hoạt động trong phạm vi bộ lọc khi dữ liệu user-level tồn tại.

#### Scenario: User-level usage is available
- **WHEN** có 127 user distinct phát sinh request trên 186 tài khoản hợp lệ
- **THEN** card hiển thị `127/186` và `68%`

#### Scenario: Usage is aggregate-only
- **WHEN** dữ liệu chỉ có tổng agent/phòng ban và không có userId
- **THEN** card hiển thị trạng thái chưa có dữ liệu theo user thay vì suy diễn từ tổng request

### Requirement: Overview ranks departments by requests
Biểu đồ Top đơn vị trên Tổng quan SHALL xếp hạng theo tổng request trong kỳ, không theo chi phí.

#### Scenario: Department request totals are available
- **WHEN** nhiều phòng ban có request trong phạm vi
- **THEN** biểu đồ sắp xếp giảm dần theo request và tooltip hiển thị số request đầy đủ

### Requirement: Success terminology is Vietnamese
Bảng chi tiết Tổng quan SHALL dùng nhãn `Tỷ lệ thành công` thay cho `Success Rate`.

#### Scenario: Detail table is rendered
- **WHEN** bảng chi tiết sử dụng AI Agent xuất hiện
- **THEN** header cột và tooltip liên quan dùng tiếng Việt

### Requirement: Overview heatmap shows the latest seven days
Heatmap Tổng quan SHALL dùng agent làm hàng, bảy ngày gần nhất trong phạm vi làm cột và độ đậm biểu thị số request; heatmap SHALL NOT dùng giờ trong ngày.

#### Scenario: Seven daily data points are available
- **WHEN** phạm vi chứa ít nhất bảy ngày và có dữ liệu đến ngày cuối kỳ
- **THEN** heatmap hiển thị bảy cột ngày liên tiếp kết thúc ở ngày dữ liệu gần nhất

#### Scenario: The selected range is shorter than seven days
- **WHEN** phạm vi được chọn có ít hơn bảy ngày
- **THEN** heatmap chỉ hiển thị các ngày nằm trong phạm vi thay vì lấy thêm ngày ngoài phạm vi

#### Scenario: A day has no requests for an agent
- **WHEN** agent không có request trong một ngày hiển thị
- **THEN** ô tương ứng có cường độ zero và tooltip ghi `0 request`
