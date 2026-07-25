## ADDED Requirements

### Requirement: Delta directions use the Excel color standard
Hệ thống SHALL ánh xạ chiều tăng sang `#00ff00`, chiều giảm sang `#ff0000`, cảnh báo ngưỡng sang `#ffff00`, và trạng thái không đổi/unavailable sang màu trung tính của theme tham chiếu `#1c4b73`.

#### Scenario: Increasing delta
- **WHEN** giá trị KPI tăng so với kỳ so sánh
- **THEN** mũi tên và phần trăm delta sử dụng màu `#00ff00`

#### Scenario: Decreasing delta
- **WHEN** giá trị KPI giảm so với kỳ so sánh
- **THEN** mũi tên và phần trăm delta sử dụng màu `#ff0000`

#### Scenario: Warning insight
- **WHEN** KPI chạm ngưỡng cảnh báo nhưng chưa vi phạm ngưỡng nghiêm trọng
- **THEN** giá trị hoặc indicator insight sử dụng semantic warning color `#ffff00`

### Requirement: Color is applied consistently across card elements
Direction SHALL điều khiển đồng bộ màu mũi tên và phần trăm delta; nội dung định nghĩa, metadata và giá trị chính SHALL giữ style riêng của card.

#### Scenario: Error rate decreases
- **WHEN** error rate giảm so với kỳ trước
- **THEN** mũi tên và phần trăm delta dùng màu đỏ trong khi công thức và nguồn dữ liệu vẫn dùng secondary text styling

### Requirement: Direction remains visible independently of color
Mọi delta SHALL có mũi tên hoặc nhãn hướng thay đổi ngoài màu sắc để người dùng không phải dựa riêng vào màu.

#### Scenario: Delta increases
- **WHEN** giá trị hiện tại lớn hơn baseline
- **THEN** delta hiển thị mũi tên lên và nhãn kỳ so sánh dù status là positive, negative hay neutral

#### Scenario: Delta decreases
- **WHEN** giá trị hiện tại nhỏ hơn baseline
- **THEN** delta hiển thị mũi tên xuống và nhãn kỳ so sánh dù status là positive, negative hay neutral

### Requirement: Semantic colors support both themes
Hệ thống SHALL duy trì khả năng đọc của màu semantic trên dark và light theme bằng tint, border alpha hoặc foreground phù hợp mà không thay đổi ý nghĩa màu gốc.

#### Scenario: Theme changes
- **WHEN** người dùng chuyển giữa dark và light theme
- **THEN** trạng thái của card không đổi, text vẫn đọc được và indicator vẫn nhận diện được

### Requirement: Card typography follows the workbook hierarchy
KPI card chính SHALL dùng giá trị 24px và label tối thiểu 12px; tooltip SHALL dùng cỡ 12px với giá trị được nhấn mạnh.

#### Scenario: Main KPI card renders
- **WHEN** card được hiển thị trên tab Tổng quan
- **THEN** giá trị chính dùng 24px và label/tooltip tuân thủ hierarchy quy định
