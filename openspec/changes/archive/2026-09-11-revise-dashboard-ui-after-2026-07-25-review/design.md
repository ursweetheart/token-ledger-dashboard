## Context

Dashboard hiện là ứng dụng HTML/JavaScript chạy offline và lưu dữ liệu trong localStorage. Dữ liệu tiêu thụ theo ngày được nhóm theo agent, phòng ban, model và nhóm user (`ug`), trong khi danh sách tài khoản demo nằm ở cấu trúc riêng. Vì vậy bộ lọc có nhãn “User” hiện không lọc được token/request của một tài khoản cụ thể.

Tab Tổng quan đã có đúng thứ tự xu hướng Chi phí → Token → Request, nhưng vẫn thiếu tỷ lệ user hoạt động và biểu đồ đơn vị đang dùng chi phí thay vì request. Tab Phòng ban và User lặp lại nhiều nội dung. Tab Chi phí chỉ có ngân sách toàn cục. Tab Hiệu năng đang hiển thị p95/p99 và tỷ lệ 4xx/5xx/429 suy diễn, không phải số đo trực tiếp.

Change này sắp xếp lại UI và bổ sung hợp đồng dữ liệu phía client để backend sau này có thể thay thế localStorage mà không phải thiết kế lại trải nghiệm.

## Goals / Non-Goals

**Goals:**

- Thực hiện đầy đủ các thay đổi UI đã thống nhất trong cuộc họp ngày 25/7.
- Làm rõ kỳ so sánh và định nghĩa user hoạt động.
- Tạo một luồng Phòng ban → User thống nhất.
- Bảo đảm bộ lọc user không hiển thị số liệu sai khi thiếu định danh user.
- Làm ma trận Agent × Phòng ban dễ đọc và có khả năng drilldown.
- Tạo trực quan chi phí/cảnh báo có thể truy vết từ dữ liệu hiện tại.
- Loại bỏ KPI, badge và nội dung hiệu năng không cần thiết hoặc không có nguồn đo thật.

**Non-Goals:**

- Không xây backend, database, authentication hoặc API.
- Không triển khai import Excel trong change này.
- Không tự tạo lịch sử user, ngân sách agent, lỗi 429 hoặc cây phòng ban nếu nguồn không cung cấp.
- Không thay đổi quy ước màu delta tăng/giảm của change `standardize-kpi-card-insights`.
- Không triển khai thu thập tự động từ middleware hoặc Google AI Studio.

## Decisions

### 1. Gộp Phòng ban và User thành một tab

Tab mới có tên `Phòng ban & User`. Phần đầu trình bày KPI/biểu đồ phòng ban; phần dưới trình bày user thuộc phạm vi phòng ban đang chọn. Tab User cũ được loại khỏi điều hướng để tránh hai nguồn điều hướng đến cùng một dữ liệu.

Khi chưa chọn phòng ban, bảng user hiển thị toàn bộ tài khoản trong phạm vi bộ lọc. Khi chọn một phòng ban hoặc click biểu đồ/bảng phòng ban, phần user cập nhật theo phòng đó.

### 2. User filter chỉ dùng định danh tài khoản thực

`state.filters.user` lưu `userId` hoặc username, không lưu `ug`. Nhóm user nếu còn cần sẽ dùng một filter riêng trong tương lai.

Usage row có thêm `userId` tùy chọn. Với agent `loginRequired=true`, dòng nhập tay phải chọn user. Với dữ liệu tổng hợp/Excel cũ không có `userId`, hệ thống không được quy toàn bộ token của agent cho một user; khi lọc user, các dòng đó bị loại và UI nêu rõ nguồn không hỗ trợ phân rã user.

### 3. Định nghĩa user hoạt động

Trong kỳ và phạm vi bộ lọc:

`activeUsers = count(distinct userId where requestCount > 0 and agent.loginRequired = true)`.

`activeUserRate = activeUsers / enabledProvisionedUsers`.

Nếu không có dữ liệu usage theo user, card hiển thị “Chưa có dữ liệu theo user” thay vì lấy trạng thái `active` tĩnh của danh sách tài khoản làm lịch sử theo kỳ.

### 4. Tổng quan dùng một hierarchy trực quan cố định

Hàng xu hướng giữ thứ tự Chi phí → Token → Request → Tỷ lệ thành công. Hàng phân tích gồm Top agent theo chi phí, phân bổ chi phí theo agent, Top đơn vị theo request và heatmap thời gian.

Card user hiển thị `active/total · rate%`. Bảng chi tiết dùng nhãn tiếng Việt `Tỷ lệ thành công`.

### 5. Delta gọi tên baseline

Dòng delta dùng một trong hai mẫu:

- `▲ 30% so với kỳ trước (KT: <giá trị>)`
- `▼ 12% so với cùng kỳ (CK: <giá trị>)`

Nếu thiếu baseline, UI hiển thị `Chưa có dữ liệu kỳ trước/cùng kỳ`. Direction và màu tiếp tục tuân theo capability semantic hiện có.

### 6. Ma trận dùng phòng ban theo chiều dọc và hỗ trợ lọc user

Phòng ban luôn là hàng; agent luôn là cột. Cột phòng ban được sticky, nhãn agent wrap tối đa hai dòng, cell căn giữa. Toolbar ma trận có bộ lọc user riêng; khi chọn user, ma trận chỉ giữ request có định danh user đó và không được gán tổng request của agent cho user.

Drilldown dùng `parentId` và `level` của metadata phòng ban. Click hàng phòng ban có đơn vị con sẽ cập nhật ma trận và breadcrumb. Khi chưa có metadata cây, ma trận vẫn hoạt động ở một cấp và ẩn điều khiển drilldown.

### 7. Cảnh báo chi phí dùng mức trung bình của agent hoạt động

`averageAgentCost = total active-agent cost / active agent count`.

Agent được cảnh báo khi:

`agentCost > averageAgentCost × 1.30`.

Cảnh báo phải hiển thị agent, chi phí, mức trung bình, phần trăm vượt và kỳ dữ liệu. Ngân sách theo agent chỉ hiển thị khi có cấu hình; nếu chưa có thì biểu đồ nêu “Chưa cấu hình ngân sách agent”.

### 8. Hiệu năng chỉ giữ số liệu có thể giải thích

KPI chính còn lại là Tỷ lệ thành công. p95/p99, tổng request và các KPI tỷ lệ 4xx/5xx/429 suy diễn bị bỏ khỏi dải card.

Biểu đồ donut có thể hiển thị tỷ trọng lỗi theo agent hoặc nhóm lỗi khi dữ liệu thật tồn tại. Chú giải 429 luôn giải thích đây là lỗi vượt RPM/TPM/quota, nhưng không hiển thị tỷ lệ 429 giả nếu nguồn không cung cấp.

### 9. Hai chế độ nhập dữ liệu được tách khỏi change UI này

Luồng nhập tay hiện tại chỉ được bổ sung trường user tùy chọn/bắt buộc theo metadata agent để hỗ trợ prototype bộ lọc. Màn hình import Excel song song và backend xử lý xung đột sẽ nằm trong change backend/ingestion riêng.

## Risks / Trade-offs

- [Dữ liệu hiện tại không có userId theo từng usage row] → Hiển thị unavailable và bổ sung dữ liệu demo có định danh để kiểm thử; không suy diễn từ agent.
- [Gộp tab làm trang dài] → Dùng section rõ ràng, sticky filter và collapse cho bảng phụ.
- [Cây phòng ban chưa có nguồn] → Drilldown là progressive enhancement; ẩn khi chỉ có danh sách phẳng.
- [Ngân sách agent chưa cấu hình] → Không chia đều ngân sách toàn cục; hiển thị trạng thái thiếu cấu hình.
- [Cảnh báo 30% nhạy khi ít agent] → Chỉ tính với agent có chi phí và request trong kỳ; luôn hiển thị số agent dùng làm mẫu.
- [Change chồng với chuẩn KPI đang mở] → Tái sử dụng renderer, formatter và semantic token; chỉ sửa nội dung/bố cục cần thiết.

## Migration Plan

1. Thêm schema client `userId`, `loginRequired` và metadata phòng ban nhưng giữ khả năng đọc dữ liệu cũ.
2. Chuẩn hóa delta label và Tổng quan trước.
3. Gộp Phòng ban/User và chuyển bộ lọc user.
4. Cập nhật ma trận Agent, Chi phí và Hiệu năng.
5. Loại bỏ DOM renderer, chart ID, style và event handler không còn dùng.
6. Kiểm thử dữ liệu cũ không có userId, dữ liệu demo có userId, dữ liệu rỗng và cả hai theme.
7. Có thể rollback bằng cách giữ adapter dữ liệu cũ và khôi phục tab User; không cần migration phá hủy localStorage.

## Open Questions

- Danh mục phòng ban phân cấp chính thức sẽ lấy từ hệ thống nào?
- Ngân sách theo agent sẽ được cấu hình ở UI hay chỉ do backend cung cấp?
- Biểu đồ donut lỗi ưu tiên phân bổ theo agent hay theo nhóm mã lỗi khi cả hai nguồn đều có?
- Có giữ route/tab User cũ dưới dạng redirect sang `Phòng ban & User` trong giai đoạn chuyển tiếp không?
