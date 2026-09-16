## ADDED Requirements

### Requirement: Department-agent matrix uses departments as rows
Ma trận Phòng ban × Agent SHALL dùng phòng ban làm hàng, agent làm cột và giữ cột tên phòng ban dễ đọc khi cuộn ngang.

#### Scenario: Matrix exceeds viewport width
- **WHEN** số phòng ban làm bảng rộng hơn vùng hiển thị
- **THEN** người dùng có thể cuộn ngang trong khi cột tên phòng ban vẫn sticky

#### Scenario: Agent label is long
- **WHEN** tên agent vượt quá chiều rộng cột
- **THEN** nhãn được wrap hoặc tooltip mà không thay bằng chỉ số 0, 1, 2

### Requirement: Matrix provides a user filter
Ma trận SHALL có bộ lọc user riêng và SHALL chỉ hiển thị request gắn với user được chọn khi nguồn có định danh user.

#### Scenario: All users are selected
- **WHEN** bộ lọc ma trận ở trạng thái `Tất cả user`
- **THEN** mỗi ô hiển thị tổng request của phòng ban và agent trong phạm vi toàn cục

#### Scenario: A user is selected
- **WHEN** người dùng chọn một tài khoản có usage được định danh
- **THEN** ma trận chỉ tổng hợp request của tài khoản đó và hiển thị phòng ban/agent liên quan

#### Scenario: Selected user has no usage
- **WHEN** tài khoản không có request trong kỳ
- **THEN** ma trận hiển thị zero hoặc trạng thái không có hoạt động và không dùng tổng request của agent thay thế

### Requirement: Agent cost distribution uses a donut chart
Trực quan chi phí theo agent trên tab Chi phí SHALL dùng donut và SHALL hiển thị tên agent, giá trị VNĐ và tỷ trọng.

#### Scenario: Multiple agents have cost
- **WHEN** có từ hai agent phát sinh chi phí
- **THEN** donut và legend hiển thị mỗi agent cùng tỷ trọng được tính từ tổng chi phí đã lọc

### Requirement: Agent budget view does not invent allocations
Biểu đồ ngân sách theo agent SHALL chỉ hiển thị ngân sách khi agent có cấu hình ngân sách hợp lệ.

#### Scenario: Agent budget exists
- **WHEN** người dùng chọn agent có ngân sách cho kỳ
- **THEN** UI hiển thị chi phí thực tế, ngân sách, phần còn lại và tỷ lệ sử dụng

#### Scenario: Agent budget is missing
- **WHEN** agent chưa có ngân sách
- **THEN** UI hiển thị `Chưa cấu hình ngân sách agent` và không tự chia ngân sách toàn cục

### Requirement: Cost anomaly alert uses the thirty-percent-above-average rule
Hệ thống SHALL cảnh báo agent có chi phí lớn hơn 130% chi phí trung bình của các agent hoạt động trong phạm vi.

#### Scenario: Agent exceeds the threshold
- **WHEN** chi phí agent lớn hơn `averageAgentCost × 1.30`
- **THEN** bảng cảnh báo hiển thị agent, chi phí, mức trung bình, phần trăm vượt và kỳ dữ liệu

#### Scenario: Agent does not exceed the threshold
- **WHEN** chi phí agent nhỏ hơn hoặc bằng ngưỡng
- **THEN** hệ thống không tạo cảnh báo bất thường cho agent đó

#### Scenario: Alert is selected
- **WHEN** người dùng click một cảnh báo agent
- **THEN** tab Chi phí áp bộ lọc agent tương ứng

### Requirement: Performance view is success-focused
Tab Hiệu năng SHALL giữ KPI Tỷ lệ thành công làm KPI chính và SHALL loại bỏ KPI tổng request, p95/p99 cùng tỷ lệ lỗi thành phần suy diễn.

#### Scenario: Performance data is rendered
- **WHEN** người dùng mở tab Hiệu năng
- **THEN** dải KPI không chứa tổng request, p95, p99 hoặc phần trăm 4xx/5xx/429 được tạo từ hệ số cố định

### Requirement: Error visualization and 429 explanation use real data
Biểu đồ lỗi SHALL dùng donut và SHALL chỉ hiển thị nhóm lỗi có dữ liệu thật; chú giải SHALL giải thích lỗi 429 là vượt RPM, TPM hoặc quota.

#### Scenario: Real error categories are available
- **WHEN** dữ liệu chứa số request 4xx, 5xx và 429
- **THEN** donut hiển thị phân bổ theo các số đo đó

#### Scenario: Error categories are unavailable
- **WHEN** nguồn chỉ cung cấp error rate tổng
- **THEN** UI không tạo tỷ lệ 4xx/5xx/429 giả và hiển thị trạng thái thiếu dữ liệu phân loại

### Requirement: New badges are removed from reviewed areas
Các tab Phòng ban & User, Agent, Chi phí và Hiệu năng SHALL không hiển thị badge `MỚI` cho các thành phần đã được chấp thuận trong cuộc họp.

#### Scenario: Reviewed tabs are rendered
- **WHEN** người dùng mở bất kỳ tab thuộc phạm vi
- **THEN** không có badge `MỚI` trên KPI, chart hoặc section
