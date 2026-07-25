## ADDED Requirements

### Requirement: KPI card presents a complete insight
Mỗi KPI card Tổng quan SHALL hiển thị giá trị và đơn vị, định nghĩa, độ mới hoặc nguồn dữ liệu, cùng tối đa một so sánh chính và một insight nguyên nhân khi dữ liệu tương ứng tồn tại.

#### Scenario: Card has current and historical data
- **WHEN** KPI có giá trị hiện tại và dữ liệu kỳ so sánh hợp lệ
- **THEN** card hiển thị giá trị, phần trăm thay đổi, kỳ so sánh được gọi tên và insight nguyên nhân có thể kiểm chứng

#### Scenario: Card has only current data
- **WHEN** KPI có giá trị hiện tại nhưng không có dữ liệu kỳ so sánh
- **THEN** card hiển thị giá trị hiện tại và thông báo chưa đủ dữ liệu thay vì tạo phần trăm thay đổi

### Requirement: Comparison values are derived only from real data
Hệ thống MUST chỉ tính delta từ các bản ghi nằm trong kỳ hiện tại và kỳ so sánh thực sự có dữ liệu; hệ thống MUST NOT tạo baseline bằng hệ số hoặc số mock.

#### Scenario: Previous period is empty
- **WHEN** không có bản ghi hợp lệ trong kỳ trước
- **THEN** card hiển thị “Chưa đủ dữ liệu kỳ trước” và không hiển thị delta giả

#### Scenario: Same period last year is empty
- **WHEN** không có bản ghi hợp lệ trong cùng kỳ năm trước
- **THEN** card hiển thị “Chưa đủ dữ liệu cùng kỳ” và không hiển thị delta giả

### Requirement: KPI direction determines delta color
Hệ thống SHALL dùng hướng thay đổi để xác định màu của delta, độc lập với việc thay đổi đó được đánh giá là tốt hay xấu.

#### Scenario: Error rate decreases
- **WHEN** error rate kỳ hiện tại thấp hơn kỳ trước
- **THEN** delta hiển thị mũi tên xuống và màu đỏ

#### Scenario: Cost increases
- **WHEN** chi phí kỳ hiện tại cao hơn kỳ trước
- **THEN** delta hiển thị mũi tên lên và màu xanh

#### Scenario: Token usage changes without a threshold
- **WHEN** tổng token tăng hoặc giảm nhưng không có ngân sách hay ngưỡng token
- **THEN** delta tăng dùng xanh, delta giảm dùng đỏ và không phát sinh cảnh báo ngưỡng

### Requirement: Insight driver is traceable
Insight nguyên nhân SHALL được tính từ dữ liệu trong phạm vi bộ lọc và SHALL gọi đúng chiều phân tích như agent, model hoặc phòng ban.

#### Scenario: A contributor dominates current cost
- **WHEN** một agent có tỷ trọng chi phí lớn nhất trong kỳ
- **THEN** card chi phí có thể nêu agent đó cùng tỷ trọng được tính từ dữ liệu hiện tại

#### Scenario: Driver cannot be determined
- **WHEN** dữ liệu không đủ để xác định contributor
- **THEN** card không hiển thị câu nguyên nhân suy đoán

### Requirement: Unavailable and zero are distinct states
Hệ thống MUST phân biệt giá trị bằng không với dữ liệu không tồn tại hoặc không đo được.

#### Scenario: Measured error rate is zero
- **WHEN** có request hợp lệ và không có request lỗi
- **THEN** card hiển thị `0%` như một giá trị đo được

#### Scenario: Latency is not supplied
- **WHEN** không có dữ liệu latency hợp lệ
- **THEN** card hiển thị “Chưa có dữ liệu” thay vì `0.0 s`

### Requirement: Metric definitions match calculations
Nội dung định nghĩa trên card SHALL khớp với công thức thực tế và SHALL không gọi một số liệu là p95 nếu nó được tính bằng trung bình các percentile con.

#### Scenario: Total token card is rendered
- **WHEN** tổng token được tính từ các trường dữ liệu
- **THEN** tooltip hoặc định nghĩa liệt kê đúng các thành phần được cộng và tránh cộng trùng cached/thinking token

#### Scenario: Aggregate p95 is unavailable
- **WHEN** nguồn dữ liệu không cung cấp histogram hoặc p95 đã tổng hợp cho phạm vi
- **THEN** hệ thống không trình bày giá trị trung bình có trọng số dưới nhãn p95
