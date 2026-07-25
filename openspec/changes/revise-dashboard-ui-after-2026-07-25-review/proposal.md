## Why

Biên bản họp ngày 25/7 xác định nhiều điểm chưa phù hợp trong cách tổ chức dashboard: kỳ so sánh chưa được gọi tên rõ, card user chưa thể hiện tỷ lệ hoạt động, tab Phòng ban và User bị tách rời, bộ lọc User hiện lọc theo nhóm thay vì tài khoản, ma trận Agent × Phòng ban khó đọc, còn tab Chi phí và Hiệu năng chứa biểu đồ/KPI chưa đúng nhu cầu vận hành.

Dashboard cần được chỉnh lại về cấu trúc và ngôn ngữ trước khi kết nối backend để hợp đồng dữ liệu backend sau này bám theo đúng trải nghiệm đã thống nhất. UI không được suy đoán số liệu user, ngân sách hoặc mã lỗi khi nguồn hiện tại không cung cấp dữ liệu tương ứng.

## What Changes

- Gọi tên rõ mọi delta theo `kỳ trước` hoặc `cùng kỳ`, kèm giá trị nền khi có dữ liệu.
- Giữ thứ tự biểu đồ Tổng quan theo Chi phí → Token → Request → Tỷ lệ thành công.
- Bổ sung tỷ lệ user hoạt động và đổi “Top đơn vị theo chi phí” thành “Top đơn vị theo request”.
- Đổi toàn bộ nhãn `Success Rate` thuộc phạm vi chỉnh sửa sang `Tỷ lệ thành công`.
- Gộp tab Phòng ban và User thành không gian `Phòng ban & User`, cho phép chọn phòng ban rồi xem mức sử dụng và danh sách user tương ứng.
- Đổi “Tỷ lệ áp dụng” thành “Tài khoản hoạt động”; loại bỏ trạng thái đồng bộ và nút nhắc đào tạo.
- Chuyển bộ lọc User sang tài khoản thực; dữ liệu không có định danh user phải hiển thị trạng thái không hỗ trợ thay vì gán số liệu tổng của agent cho user.
- Căn chỉnh lại ma trận Phòng ban × Agent, giữ phòng ban ở chiều dọc, agent ở chiều ngang, thêm bộ lọc user và bổ sung drilldown theo cây đơn vị.
- Chuyển biểu đồ chi phí theo agent thành donut, cho phép xem ngân sách theo agent và hiển thị cảnh báo khi chi phí agent cao hơn 30% mức trung bình.
- Tinh gọn tab Hiệu năng còn KPI Tỷ lệ thành công, dùng donut cho phân bổ lỗi theo agent/nhóm lỗi, giải thích lỗi 429 và bỏ các badge `MỚI`.
- Bổ sung trường user cho luồng nhập tay khi agent yêu cầu đăng nhập; phần import Excel và lưu trữ backend không thuộc change này.

## Capabilities

### New Capabilities

- `overview-period-and-usage-ui`: Quy định cách trình bày kỳ so sánh, user hoạt động, thứ tự biểu đồ và bảng chi tiết trên Tổng quan.
- `department-user-workspace`: Quy định không gian Phòng ban & User, bộ lọc user thực và drilldown phòng ban.
- `agent-cost-performance-ui`: Quy định ma trận agent, trực quan chi phí/cảnh báo và tab Hiệu năng tinh gọn.

### Modified Capabilities

- `kpi-card-insights`: Bổ sung yêu cầu gọi tên kỳ so sánh và giá trị nền; không thay đổi quy tắc direction/màu đã có.

## Impact

- Cấu trúc tab, card, chart và bảng trong `index.html`.
- Logic lọc, tổng hợp user, biểu đồ, cảnh báo và ma trận trong `app.js`.
- Layout, responsive, sticky matrix, donut, drilldown và dark/light theme trong `dashboard.css`.
- Dữ liệu client cần trường `userId` tùy chọn và metadata `loginRequired` cho agent để prototype lọc user chính xác.
- Không xây API, database, xác thực hoặc import Excel trong change này.
- Change này phụ thuộc vào các formatter/insight đã có và không được đưa baseline giả trở lại.
