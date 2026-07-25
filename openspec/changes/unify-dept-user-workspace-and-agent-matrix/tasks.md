## 1. Nền móng: định danh đơn vị và cây tổ chức

- [x] 1.1 Thêm `ORG_UNITS` (3 cấp demo) và `UNIT_ALIASES` liệt kê tường minh mọi biến thể tên đang có trong dữ liệu
- [x] 1.2 Viết `unitOf(deptString)` trả về unit, tự sinh unit cấp 1 cho chuỗi lạ thay vì loại bỏ
- [x] 1.3 Viết `unitChildren(unitId)`, `unitPath(unitId)`, `unitAccounts(unitId)` làm API truy vấn cây
- [x] 1.4 Chuyển `DEPT_PROVISIONED` sang khoá theo `unitId`, bổ sung số cấp cho các đơn vị đang thiếu
- [x] 1.5 Cộng dồn số cấp của đơn vị cha từ các đơn vị con, không khai báo trùng
- [x] 1.6 Chuyển `isExcludedDepartment` sang kiểm tra theo `unitId`
- [x] 1.7 Đối chiếu: tổng token/request/cost toàn dashboard không đổi sau khi gom alias

## 2. Nền móng: tầng tài khoản demo khớp tổng phòng ban

- [x] 2.1 Viết lại `buildDemoUserAccounts()` sinh tài khoản cho mọi đơn vị có usage, gán vào cấp sâu nhất
- [x] 2.2 Phân bổ `req`/`ti`/`to` của đơn vị cho các tài khoản active theo trọng số tiền định theo `unitId`
- [x] 2.3 Ép `Σ req(user) === req(unit)` và `Σ token(user) === token(unit)` bằng cách dồn phần dư
- [x] 2.4 Bảo đảm kết quả tiền định: cùng kỳ và cùng bộ lọc luôn cho cùng số liệu qua các lần render
- [x] 2.5 Bảo toàn các trường `role`, `created`, `disabled`, `quotaPct`, `last` mà UI hiện tại đang dùng
- [x] 2.6 Thêm nhãn dùng chung `Dữ liệu phân bổ (demo)` kèm tooltip giải thích nguồn không có userId
- [x] 2.7 Kiểm tra `filterAccounts()` vẫn đúng khi số tài khoản tăng và phòng ban đi qua `unitOf()`

## 3. Chú thích delta KT / CK

- [x] 3.1 Thêm `DELTA_BASIS` với cặp viết tắt và tên đầy đủ cho `KT` và `CK`
- [x] 3.2 Đổi `deltaLine` nhận `basis` thay cho chuỗi nhãn tự do
- [x] 3.3 Cho `renderSingleDelta` dùng `basis = KT`; cho `renderDelta` dùng `KT` ở dòng 1 và `CK` ở dòng 2
- [x] 3.4 Đưa kỳ cụ thể và tên baseline đầy đủ vào `title` của chú thích
- [x] 3.5 Thêm dòng chú giải `KT = kỳ trước · CK = cùng kỳ năm trước` cạnh dải tab
- [x] 3.6 Giữ nguyên trạng thái `chưa có dữ liệu` khi thiếu baseline, không dựng baseline bằng hệ số
- [x] 3.7 Rà mọi scorecard trong `index.html` xác nhận không còn chú thích thiếu tên baseline

## 4. Gộp tab Phòng ban và User

- [x] 4.1 Xoá nút tab `👥 User`, đổi nhãn tab phòng ban thành `🏢 Phòng ban & User`
- [x] 4.2 Chuyển KPI tài khoản, bảng tài khoản, biểu đồ DAU và danh sách không hoạt động vào `div#departments`
- [x] 4.3 Xoá `div#users` và nhánh `case "users"` trong bộ điều phối chart
- [x] 4.4 Sửa banner tab để không còn nhắc `trạng thái đồng bộ`
- [x] 4.5 Cập nhật banner câu hỏi dẫn dắt của tab hợp nhất cho khớp nội dung mới
- [x] 4.6 Gộp `renderUsers`/`chartsUsers` vào luồng render của tab hợp nhất, xoá chart instance mồ côi
- [x] 4.7 Grep xác nhận không còn chuỗi `đồng bộ` trong `index.html`, `app.js`, `dashboard.css`

## 5. Bảng chi tiết phòng ban: drilldown 3 cấp

- [x] 5.1 Thêm `state.deptExpanded` và adapter đọc `localStorage` cũ bỏ qua khoá lạ
- [x] 5.2 Render bảng theo cây: dòng phòng ban, dòng đơn vị con, dòng tài khoản, thụt lề theo cấp
- [x] 5.3 Gắn toggle mở/đóng có chỉ dấu `▶`/`▼`; đơn vị một cấp mở trực tiếp ra tài khoản
- [x] 5.4 Giữ trạng thái mở khi đổi khoảng thời gian hoặc bộ lọc
- [x] 5.5 Hiển thị dấu không áp dụng cho các cột không có nghĩa ở cấp tài khoản
- [x] 5.6 Gắn nhãn `Dữ liệu phân bổ (demo)` cho vùng cấp tài khoản
- [x] 5.7 Kiểm tra tổng dòng con khớp đúng dòng cha ở cả hai cấp

## 6. Bảng chi tiết phòng ban: hai cột mới

- [x] 6.1 Thêm cột `Tổng Users` lấy từ số cấp theo `unitId`
- [x] 6.2 Thêm cột `Tỷ lệ active/tổng` hiển thị dạng `active/total · rate%`
- [x] 6.3 Sửa `Users active` để đếm tài khoản có request trong kỳ, thay cho snapshot `g.u`
- [x] 6.4 Tô màu tỷ lệ theo `thresholds.adoptionWarning` và `thresholds.adoptionCritical` đã có
- [x] 6.5 Hiển thị trạng thái chưa có dữ liệu khi thiếu số cấp, không suy ra 100% và không chia cho zero
- [x] 6.6 Cập nhật `emptyRow()` theo số cột mới

## 7. Ma trận Project × Phòng ban

- [x] 7.1 Lật trục: hàng là project, cột là đơn vị; đổi tiêu đề section cho khớp
- [x] 7.2 Đảo lại task `5.1` của change `revise-dashboard-ui-after-2026-07-25-review` đã hiện thực ngược chiều
- [x] 7.3 Thêm `state.matrixPath` và breadcrumb `Tất cả phòng ban › … › …` click được để lên cấp
- [x] 7.4 Cho click tiêu đề cột để xuống cấp: phòng ban → đơn vị con → tài khoản
- [x] 7.5 Hiển thị chỉ dấu `⌄` chỉ trên cột có cấp con; cột không có cấp con không click được
- [x] 7.6 Ẩn cột không có request, trừ tài khoản đang được chọn ở bộ lọc user
- [x] 7.7 Reset `matrixPath` khi đổi bộ lọc phòng ban toàn cục
- [x] 7.8 Cho `matrix-user-filter` nhảy breadcrumb tới đơn vị của tài khoản được chọn
- [x] 7.9 Sticky cột nhãn project ở mọi cấp, cuộn ngang trong container riêng
- [x] 7.10 Gắn nhãn `Dữ liệu phân bổ (demo)` khi ma trận ở cấp tài khoản

## 8. Biểu đồ tròn mức độ sử dụng agent

- [x] 8.1 Đổi `c-ag-usage` từ `mkBar` sang `mkDonut`, thêm `div#lg-ag-usage` cho legend
- [x] 8.2 Đổi badge `wf-type` từ `Bar` sang `Tròn`
- [x] 8.3 Gộp phần đuôi thành `Agent khác` khi số agent vượt ngưỡng hiển thị
- [x] 8.4 Hiển thị trạng thái chưa có dữ liệu khi không có agent nào phát sinh request

## 9. Style, dọn dẹp và kiểm thử

- [x] 9.1 Style hàng mở rộng, thụt cấp, chỉ dấu toggle, breadcrumb ma trận, nhãn dữ liệu demo
- [x] 9.2 Kiểm tra contrast và trạng thái thiếu dữ liệu trên cả dark và light theme
- [x] 9.3 Kiểm tra responsive: bảng drilldown và ma trận 3 cấp trên màn hình hẹp
- [x] 9.4 Xoá CSS, DOM id và chart instance của `div#users` và của biểu đồ bar cũ
- [x] 9.5 Kiểm thử kết hợp bộ lọc thời gian, phòng ban, user, agent, provider, model
- [x] 9.6 Kiểm thử đơn vị một cấp, đơn vị nhiều cấp, đơn vị thiếu số cấp, đơn vị không có usage, dữ liệu rỗng
- [x] 9.7 Đối chiếu tổng ở cả ba cấp của bảng và cả ba cấp của ma trận
- [x] 9.8 Cập nhật `tasks.md` của change `revise-dashboard-ui-after-2026-07-25-review`, đánh dấu các task bị thay thế
