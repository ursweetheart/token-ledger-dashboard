## ADDED Requirements

### Requirement: Insight explains condition, cause, and action
Hệ thống SHALL tạo insight theo cấu trúc điều kiện hiện tại, evidence định lượng, contributor chính và khuyến nghị hành động khi các dữ liệu đó tồn tại.

#### Scenario: Token anomaly has a dominant contributor
- **WHEN** token vượt threshold bất thường và một agent đóng góp lớn nhất vào mức tăng
- **THEN** card nêu mức tăng, agent đóng góp chính cùng tỷ trọng và hành động kiểm tra token/request hoặc context của agent

#### Scenario: Cause cannot be established
- **WHEN** một cảnh báo kích hoạt nhưng không đủ dữ liệu xác định contributor
- **THEN** insight chỉ nêu điều kiện/evidence và không tạo nguyên nhân suy đoán

### Requirement: Token alerts account for request volume
Hệ thống SHALL đánh giá token tăng đồng thời với request và token/request để phân biệt tăng trưởng sử dụng với mức tiêu thụ bất thường trên mỗi request.

#### Scenario: Token and request grow proportionally
- **WHEN** token và request cùng tăng với tỷ lệ tương đương trong tolerance cấu hình
- **THEN** hệ thống mô tả nhu cầu tăng và không gắn cảnh báo token/request bất thường

#### Scenario: Token grows faster than requests
- **WHEN** token tăng vượt threshold nhưng request không tăng tương ứng
- **THEN** hệ thống cảnh báo token/request tăng và đề nghị kiểm tra prompt, context hoặc output

### Requirement: Budget insight compares money and time
Hệ thống SHALL so sánh phần trăm ngân sách đã dùng với phần trăm thời gian đã qua và SHALL dự báo chi phí cuối kỳ khi có đủ dữ liệu.

#### Scenario: Spending is ahead of schedule
- **WHEN** phần trăm ngân sách đã dùng cao hơn phần trăm thời gian đã qua quá threshold
- **THEN** card hiển thị cảnh báo tốc độ chi tiêu, forecast cuối kỳ và mức chênh ngân sách

#### Scenario: Budget is unavailable
- **WHEN** không có ngân sách hợp lệ cho phạm vi hiện tại
- **THEN** hệ thống không tạo badge sát trần hoặc forecast vượt ngân sách

### Requirement: Concentration alerts identify the dimension
Hệ thống SHALL cảnh báo khi một agent, phòng ban, model hoặc nhóm người dùng chiếm tỷ trọng vượt threshold và SHALL gọi đúng chiều phân tích trong nội dung.

#### Scenario: One agent dominates cost
- **WHEN** một agent chiếm tỷ trọng chi phí vượt threshold
- **THEN** insight nêu tên agent, tỷ trọng và liên kết hành động đến drill-down Agent hoặc Chi phí

### Requirement: Reliability alerts require configured thresholds
Hệ thống MUST chỉ đánh giá lỗi, latency hoặc quota là warning/critical khi có threshold hoặc SLO hợp lệ cho metric và phạm vi tương ứng.

#### Scenario: Error rate exceeds configured threshold
- **WHEN** error rate vượt threshold critical đã cấu hình
- **THEN** card hiển thị severity critical, evidence và contributor lỗi chính nếu xác định được

#### Scenario: Latency SLO is missing
- **WHEN** có số latency nhưng không có SLO phù hợp
- **THEN** hệ thống hiển thị số liệu nhưng không gắn kết luận vượt chuẩn

### Requirement: Inactivity and adoption alerts are actionable
Hệ thống SHALL phát hiện agent không hoạt động và tỷ lệ adoption thấp bằng cửa sổ thời gian/threshold cấu hình.

#### Scenario: Agent has no activity
- **WHEN** agent không phát sinh request trong số ngày cấu hình
- **THEN** insight nêu số agent không hoạt động và đề nghị rà soát owner, đào tạo, hợp nhất hoặc ngừng agent

### Requirement: Alert severity is independent from delta direction
Hệ thống SHALL giữ màu delta tăng/giảm theo direction và SHALL hiển thị severity bằng badge, viền hoặc dòng cảnh báo riêng.

#### Scenario: Cost increases and forecast is near budget
- **WHEN** chi phí tăng so kỳ trước và forecast chạm mức warning
- **THEN** delta tăng vẫn màu xanh trong khi card hiển thị badge/viền cảnh báo màu vàng

### Requirement: Insights use only verifiable data
Hệ thống MUST NOT tạo baseline, contributor, forecast hoặc recommendation định lượng từ dữ liệu mock hay phạm vi không có dữ liệu.

#### Scenario: Previous period has no data
- **WHEN** không có dữ liệu kỳ trước
- **THEN** hệ thống hiển thị chưa đủ dữ liệu so sánh và không tạo phần trăm thay đổi
