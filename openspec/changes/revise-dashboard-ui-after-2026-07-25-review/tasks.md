> **Lưu ý:** các task 2.1, 3.1, 3.3, 3.5, 3.6, 5.1, 5.4, 5.5, 5.6 đã được thay thế bởi change
> `unify-dept-user-workspace-and-agent-matrix`. Task 5.1 bị **đảo chiều** ở change đó
> (ma trận nay là hàng = project, cột = phòng ban).

## 1. Data Contract and Compatibility

- [x] 1.1 Bổ sung `userId` tùy chọn cho usage row và `loginRequired` cho metadata agent — **ĐO 04/09:** `userId` đã có trong `web/`; `loginRequired` **không còn đối tượng** — panel nhập tay đã bị bỏ (`index.html:399`, `app.js:529`)
- [ ] 1.2 Tách bộ lọc username khỏi trường nhóm user `ug` và giữ adapter đọc state/localStorage cũ
- [x] 1.3 Bổ sung metadata phòng ban `id`, `parentId`, `level` với fallback danh sách phẳng
- [ ] 1.4 Tạo helper xác định dữ liệu hỗ trợ phân rã user và trạng thái unavailable
- [x] 1.5 Loại phòng ban `Đang trong quá trình thử nghiệm` khỏi seed, state cũ và mọi bộ lọc

## 2. Period Comparison and Overview

- [x] 2.1 Chuẩn hóa delta thành nhãn rõ kỳ trước/cùng kỳ, viết tắt KT/CK và giá trị nền — **THAY THẾ** bởi change `unify-dept-user-workspace-and-agent-matrix`
- [ ] 2.2 Giữ thứ tự hàng xu hướng Chi phí → Token → Request → Tỷ lệ thành công — **ĐO 04/09: CHƯA.** Thứ tự hiện tại là Mức độ sử dụng → Request → Token (`index.html:568,573,578`), và không có hàng Tỷ lệ thành công
- [ ] 2.3 Đổi biểu đồ Top đơn vị theo chi phí thành Top đơn vị theo request — **ĐO 04/09: CHƯA.** `index.html:598` vẫn là “Top đơn vị theo mức độ sử dụng (VNĐ)”, tức vẫn theo tiền
- [x] 2.4 Hiển thị card User hoạt động theo dạng `active/total · rate%` khi có dữ liệu hợp lệ — **ĐO 04/09:** `app.js:3115-3116` hiện phần trăm + `<b>N/M</b> tài khoản đã dùng`
- [x] 2.5 Đổi cột `Success Rate` thành `Tỷ lệ thành công` — **ĐO 04/09:** `Success Rate` 0 kết quả trong `web/`
- [ ] 2.6 Kiểm tra insight/delta không đưa baseline giả trở lại
- [x] 2.7 Đổi heatmap theo giờ thành ma trận Agent × 7 ngày gần nhất theo request
- [x] 2.8 Thay dữ liệu demo tháng 7 bằng dữ liệu Excel thật của đủ 4 tuần

## 3. Department and User Workspace

- [x] 3.1 Đổi tab Phòng ban thành `Phòng ban & User` và loại tab User khỏi điều hướng chính — **THAY THẾ** bởi change `unify-dept-user-workspace-and-agent-matrix`
- [x] 3.2 Đổi card “Phòng tốn nhiều nhất” thành “Mức độ sử dụng” — **ĐO 04/09:** chuỗi cũ 0 kết quả, chuỗi mới 13 kết quả
- [x] 3.3 Chuyển KPI tài khoản, bảng user, DAU và tài khoản không hoạt động vào tab hợp nhất — **THAY THẾ** bởi change `unify-dept-user-workspace-and-agent-matrix`
- [x] 3.4 Đổi “Tỷ lệ áp dụng” thành “Tài khoản hoạt động” — **ĐO 04/09:** nhãn hiển thị nay là “Tỷ lệ tài khoản được sử dụng theo Agent” (`index.html:693`); “Tỷ lệ áp dụng” chỉ còn trong 2 ghi chú mã nguồn. Khác câu chữ đề xuất, đúng ý định
- [x] 3.5 Xóa section trạng thái đồng bộ và mọi nút/nội dung “Nhắc đào tạo” — **THAY THẾ** bởi change `unify-dept-user-workspace-and-agent-matrix`
- [x] 3.6 Cho phép click phòng ban để cập nhật danh sách và KPI user tương ứng — **THAY THẾ** bởi change `unify-dept-user-workspace-and-agent-matrix`
- [x] 3.7 Hiển thị trạng thái không hỗ trợ khi nguồn usage thiếu userId — **ĐO 04/09:** `app.js:3110` báo “Kỳ đang chọn nằm ngoài khoảng có dữ liệu định danh”
- [x] 3.8 Xóa nút và nội dung “Nhắc đào tạo” khỏi danh sách tài khoản không hoạt động
- [x] 3.9 Đổi biểu đồ phòng ban sang dạng tròn và Việt hóa nhãn “Adoption”

## 4. Global User Filter and Manual Entry

- [ ] 4.1 Điền dropdown User từ danh mục tài khoản thực và dùng id ổn định làm value
- [ ] 4.2 Làm dropdown User phụ thuộc phòng ban và agent đang chọn
- [ ] 4.3 Áp user filter đồng bộ lên KPI, chart, table và cảnh báo có dữ liệu user-level
- [x] 4.4 Bổ sung trường User vào bảng nhập tay, bắt buộc với agent cần đăng nhập — **KHÔNG CÒN ĐỐI TƯỢNG:** luồng nhập tay đã bị bỏ khi dashboard chuyển sang chỉ đọc database (`index.html:399`, `app.js:529`)
- [ ] 4.5 Cảnh báo rõ các bản ghi tổng hợp không thể quy về user

## 5. Department-Agent Matrix and Drilldown

- [x] 5.1 Cố định trục hàng Phòng ban và trục cột Agent — **THAY THẾ** bởi change `unify-dept-user-workspace-and-agent-matrix` (ĐÃ ĐẢO CHIỀU)
- [x] 5.2 Căn lề cell, wrap header, sticky cột phòng ban và tối ưu cuộn ngang
- [x] 5.3 Thêm bộ lọc user riêng cho ma trận và trạng thái khi user không có usage
- [x] 5.4 Thêm breadcrumb và điều khiển cấp phòng ban — **THAY THẾ** bởi change `unify-dept-user-workspace-and-agent-matrix`
- [x] 5.5 Cho phép click phòng ban có cấp con để drilldown và quay lại cấp cha — **THAY THẾ** bởi change `unify-dept-user-workspace-and-agent-matrix`
- [x] 5.6 Ẩn drilldown khi metadata phòng ban chỉ có một cấp — **THAY THẾ** bởi change `unify-dept-user-workspace-and-agent-matrix`
- [x] 5.7 Bỏ badge `MỚI` khỏi tiêu đề ma trận
- [x] 5.8 Đồng bộ cây phân quyền và số user Ralli từ `phong_ban_phan_quyen.xlsx`

## 6. Cost UI and Alerts

- [x] 6.1 Chuyển biểu đồ chi phí theo agent từ bar sang donut
- [ ] 6.2 Bổ sung bộ chọn agent cho biểu đồ thực tế so với ngân sách
- [x] 6.3 Hiển thị trạng thái chưa cấu hình thay vì tự chia ngân sách toàn cục cho agent — **ĐÃ XONG 17/08** ở change `serve-dashboard-from-database-only`: hạn mức chỉ đến từ `ref_budget` qua `/api/catalog`, ba trạng thái (có USD / chỉ có token / chưa đặt), không suy 0. Xem `app.js:20-31`
- [ ] 6.4 Tính cảnh báo agent có chi phí cao hơn 30% trung bình agent hoạt động
- [ ] 6.5 Tạo bảng cảnh báo gồm bằng chứng, mức vượt, kỳ và thao tác lọc theo agent
- [ ] 6.6 Kiểm tra cảnh báo cập nhật theo time range và bộ lọc toàn cục

## 7. Performance UI

> **RÀ SOÁT 04/09/2026 — TIỀN ĐỀ CỦA CẢ NHÓM NÀY ĐÃ SAI.** Các ô 7.1, 7.2, 7.4 và 7.6
> yêu cầu **gỡ bỏ** p95/p99 và các KPI 4xx/5xx/429 với lý do chúng là số **suy diễn,
> không có nguồn**. Lý do đó đúng vào 25/07/2026 nhưng **không còn đúng**: migration 006
> (31/08) thêm `fact_call.outcome` và `error_code` — mã lỗi nay là số đo thật của từng
> lượt gọi; migration 010 (03/09) dựng `latency_resolved`, p95 Gateway tính CHÍNH XÁC từ
> `duration_ms` thô thay vì nội suy trong ô histogram rộng 33,6 giây. Làm theo nguyên văn
> bây giờ sẽ **xoá đi bốn phép đo có thật**. Nhóm này cần một quyết định phạm vi trước khi
> đụng vào, không phải cần người gõ phím.

- [ ] 7.1 Tinh gọn dải KPI còn Tỷ lệ thành công
- [ ] 7.2 Loại tổng request, p95/p99 và KPI 4xx/5xx/429 suy diễn
- [ ] 7.3 Đổi biểu đồ tỷ lệ lỗi theo agent thành donut
- [ ] 7.4 Thêm chú giải 429 là vượt RPM/TPM/quota và chỉ hiển thị tỷ lệ khi có dữ liệu thật
- [ ] 7.5 Đổi nhãn còn lại sang tiếng Việt và bỏ mọi badge `MỚI` — **ĐO 04/09: CHƯA.** Còn 4 badge ở `index.html:1154,1159,1164,1188`, tất cả trong tab Hiệu năng
- [ ] 7.6 Cập nhật bảng hiệu năng để không trình bày percentile hoặc số lỗi không có nguồn

## 8. Styling, Cleanup, and Verification

- [ ] 8.1 Bổ sung style responsive cho tab hợp nhất, sticky matrix và donut mới
- [ ] 8.2 Kiểm tra contrast và trạng thái unavailable trên dark/light theme
- [ ] 8.3 Xóa chart instance, DOM id, renderer và CSS của section đã loại bỏ
- [ ] 8.4 Kiểm thử bộ lọc time range, phòng ban, user, agent, provider và model kết hợp
- [ ] 8.5 Kiểm thử dữ liệu có userId, thiếu userId, thiếu budget, cây phòng ban một cấp/nhiều cấp và dữ liệu rỗng
- [ ] 8.6 Đối chiếu toàn bộ nội dung biên bản 25/7 và xác nhận không còn nhãn `Success Rate`, `Tỷ lệ áp dụng`, `Nhắc đào tạo` hoặc badge `MỚI` trong phạm vi — **ĐO 04/09: 3/4 sạch.** `Success Rate` 0 · `Nhắc đào tạo` 0 · `Tỷ lệ áp dụng` chỉ còn trong ghi chú mã nguồn · badge `MỚI` **còn 4**
