## Why

Rà soát `index.html` ngày 25/07/2026 phát hiện 5 nhóm vấn đề còn tồn tại:

1. Chú thích delta trên scorecard chỉ ghi `so với tháng 6/2026`, không nói rõ đang so với **kỳ trước** hay **cùng kỳ năm trước**. Người xem không biết baseline nào đang được dùng.
2. Tab User còn sót nội dung nhắc tới `trạng thái đồng bộ` dù bảng đã bị loại bỏ.
3. Tab `Phòng ban` và tab `User` vẫn tách rời. Không xem được nhân viên của một phòng ban cùng với số liệu của phòng đó.
4. Tab Agents: biểu đồ `Mức độ sử dụng các agent` đang là bar; ma trận `Phòng ban × Agent` đặt phòng ban ở trục dọc và không có drilldown theo cấp đơn vị.
5. Bảng `Chi tiết theo phòng ban` thiếu tổng số user được cấp và tỷ lệ user hoạt động — hai số cần thiết để đánh giá mức độ áp dụng.

Ngoài phần UI, quá trình rà soát phát hiện **hai lỗi dữ liệu nền** làm mọi tính toán về user theo phòng ban bị sai, buộc phải xử lý trong cùng change:

- `DEPT_PROVISIONED` có 2/5 khoá không bao giờ khớp dữ liệu thực (`"P.NCTT, TTDL&ĐHS"` vs `"P.NCTT , TTDL&ĐHS"`; `"Cty CPBĐ PN Rạng Đông"` vs `"Công ty CPBĐ PN Rạng Đông"`). Kết quả: mẫu số fallback về số user active nên tỷ lệ áp dụng của hai phòng đó luôn là 100%.
- Tên phòng ban tồn tại song song nhiều biến thể của cùng một đơn vị (`PBH1` ↔ `Phòng Bán hàng 1`, `PBH2` ↔ `Phòng Bán hàng 2`, `PBH3` ↔ `Phòng Bán hàng 3`, `TT C4LED` ↔ `C4LED`, `TT&TMĐT` ↔ `TMĐT`). Chúng hiển thị thành các dòng ngang cấp riêng biệt trong mọi bảng và biểu đồ phòng ban.

## What Changes

- Chuẩn hoá chú thích delta: gọi tên baseline bằng `so với KT` (kỳ trước) hoặc `so với CK` (cùng kỳ năm trước), kèm chú giải viết tắt và giá trị nền.
- Loại bỏ mọi nội dung còn sót về `trạng thái đồng bộ` trong phần User.
- Gộp tab `Phòng ban` và tab `User` thành một tab `Phòng ban & User`; bảng chi tiết phòng ban trở thành drilldown 3 cấp: **Phòng ban → Đơn vị con (Vùng) → Tài khoản**.
- Bổ sung `Tổng Users` và `Tỷ lệ active/tổng` vào bảng chi tiết theo phòng ban, dùng ngưỡng `adoptionWarning`/`adoptionCritical` đã có để tô màu.
- Đổi biểu đồ `Mức độ sử dụng các agent` từ bar sang biểu đồ tròn có legend.
- Lật ma trận: **trục dọc = project (agent), trục ngang = phòng ban**; bổ sung drilldown theo cấp trên trục phòng ban qua breadcrumb.
- Thêm metadata cây đơn vị 3 cấp (demo) và chuẩn hoá tên phòng ban về một định danh duy nhất.
- Mở rộng danh sách tài khoản demo để phủ đủ mọi phòng ban có usage, và chuẩn hoá số liệu user sao cho tổng của các user khớp đúng tổng của phòng ban.
- Dán nhãn rõ tầng dữ liệu user là **dữ liệu demo/phân bổ**, không phải số đo theo tài khoản.

## Capabilities

### New Capabilities

- `org-unit-hierarchy`: Định danh phòng ban chuẩn hoá, cây đơn vị 3 cấp, và hợp đồng dữ liệu tài khoản demo phủ đủ phòng ban kèm quy tắc chuẩn hoá tổng.
- `period-delta-labels`: Quy định cách gọi tên và trình bày baseline so sánh `KT`/`CK` trên mọi scorecard.
- `department-user-drilldown`: Quy định tab hợp nhất `Phòng ban & User`, bảng chi tiết phòng ban mở rộng và drilldown 3 cấp tới tài khoản.
- `agent-project-matrix`: Quy định biểu đồ tròn mức độ sử dụng agent và ma trận Project × Phòng ban có drilldown theo cấp đơn vị.

## Impact

- `index.html`: danh sách tab, banner tab User, bảng chi tiết phòng ban, khối biểu đồ tab Agents, toolbar/breadcrumb ma trận, xoá `div#users`.
- `app.js`: `DEPT_PROVISIONED`, `buildDemoUserAccounts`, `renderDepartments`, `renderUsers`, `chartsUsers`, `chartsDepartments`, `chartsAgents`, `buildAgentDeptHeatmap`, `deltaLine`, `renderDelta`, `renderSingleDelta`, nhánh `case "users"` trong bộ điều phối chart.
- `dashboard.css`: style hàng mở rộng, thụt cấp, breadcrumb ma trận, nhãn dữ liệu demo, sticky trục dọc mới.
- **Quan hệ với change `revise-dashboard-ui-after-2026-07-25-review`**: change này thay thế các task `2.1`, `3.1`, `3.3`, `3.5`, `3.6`, `5.1`, `5.4`, `5.5`, `5.6` của change đó. Task `5.1` phải được **đảo lại** vì đã hiện thực sai chiều so với yêu cầu mới. Các task còn lại của change cũ (tab Chi phí, tab Hiệu năng, bộ lọc user toàn cục, nhập tay) không thuộc phạm vi change này.
- Không xây backend, API, database, authentication hoặc import Excel.
