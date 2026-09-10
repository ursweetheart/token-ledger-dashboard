> **Lưu ý:** các task 2.1, 3.1, 3.3, 3.5, 3.6, 5.1, 5.4, 5.5, 5.6 đã được thay thế bởi change
> `unify-dept-user-workspace-and-agent-matrix`. Task 5.1 bị **đảo chiều** ở change đó
> (ma trận nay là hàng = project, cột = phòng ban).

## 1. Data Contract and Compatibility

- [x] 1.1 Bổ sung `userId` tùy chọn cho usage row và `loginRequired` cho metadata agent — **ĐO 04/09:** `userId` đã có trong `web/`; `loginRequired` **không còn đối tượng** — panel nhập tay đã bị bỏ (`index.html:399`, `app.js:529`)
- [x] 1.2 Tách bộ lọc username khỏi trường nhóm user `ug` và giữ adapter đọc state/localStorage cũ
      → **ĐÃ TÁCH TỪ TRƯỚC, đo 08/09.** `state.filters` là
      `{dept, user, provider, model, agent}` — **không còn khoá `ug` nào**. Trường `ug` trên
      dòng dữ liệu đã bị đổi công dụng: nó mang **nhãn user thật**
      (`ug: displayUser || a.username`), không còn là nhóm user, và bộ lọc so thẳng với nó.
      Adapter đọc state cũ cũng đã có: `loadState()` chỉ nhận khoá trong `PREF_KEYS`, mọi
      khoá lạ trong cache cũ bị bỏ.
      **Còn sót về TÊN GỌI:** trường vẫn tên `ug` dù không còn nghĩa "user group". Không đổi
      trong change này vì nó là hợp đồng dữ liệu do `api.js` sinh ra — đổi tên phải sửa cả
      hai phía, không cân với lợi ích
- [x] 1.3 Bổ sung metadata phòng ban `id`, `parentId`, `level` với fallback danh sách phẳng
- [x] 1.4 Tạo helper xác định dữ liệu hỗ trợ phân rã user và trạng thái unavailable
      → **LÀM 08/09.** `rowHasUserIdentity(r)` + `userScopeGap()`.
      Helper **dùng lại `userFilterLabel`** chứ không viết lại phép nhận biết: hàm đó đã
      biết trả `""` khi nhãn **trùng tên agent** — tức chỗ đó không có danh tính người nào,
      chỉ có tên agent. Viết lại ở chỗ thứ hai là tạo cơ hội cho hai chỗ lệch nhau
- [x] 1.5 Loại phòng ban `Đang trong quá trình thử nghiệm` khỏi seed, state cũ và mọi bộ lọc

## 2. Period Comparison and Overview

- [x] 2.1 Chuẩn hóa delta thành nhãn rõ kỳ trước/cùng kỳ, viết tắt KT/CK và giá trị nền — **THAY THẾ** bởi change `unify-dept-user-workspace-and-agent-matrix`
- [x] 2.2 Giữ thứ tự hàng xu hướng Chi phí → Token → Request → Tỷ lệ thành công — **ĐO 04/09: CHƯA.** Thứ tự hiện tại là Mức độ sử dụng → Request → Token (`index.html:568,573,578`), và không có hàng Tỷ lệ thành công
      → **LÀM 08/09.** Đảo Request↔Token, thêm hàng thứ tư `c-ov-success-trend` và chuỗi
      `success` vào `trendSeries()`, thêm nhánh `percent` cho tick và tooltip của
      `mkOverviewLine`, điền `ov-success-total`.
      **Chỗ phải cẩn thận:** `aggregate()` trả `er = 0` khi `r = 0`, nên `100-er` cho ra
      **100%** — một ngày không ai gọi sẽ trông thành một ngày hoàn hảo. Đã trả `null` cho
      ngày không có request (Chart.js vẽ thành chỗ đứt) và hiện “Chưa có request nào” thay
      cho “100%” ở ô tổng. Bộ kiểm 30/30.
- [x] 2.3 Đổi biểu đồ Top đơn vị theo chi phí thành Top đơn vị theo request — **ĐO 04/09: CHƯA.** `index.html:598` vẫn là “Top đơn vị theo mức độ sử dụng (VNĐ)”, tức vẫn theo tiền
      → **LÀM 08/09.** Tiêu đề đổi thành “Top đơn vị theo request”; xếp hạng, lọc và giá trị
      vẽ đều chuyển từ `g.cost` sang `g.r`; bỏ `money:true`. Đổi luôn id canvas
      `c-ov-unit-cost` → `c-ov-unit-req` vì tên cũ nói sai về thứ nó vẽ (2 chỗ, không dính CSS).
      Lý do đổi đã ghi vào mã: tiền của một phòng ban là số **suy ra** — 28,2% tiền trên
      dashboard nhân từ `ref_price` chứ không từ hoá đơn, và phần suy ra dồn vào ít phòng ban,
      nên thứ hạng theo tiền đổi theo chỗ hoá đơn về sớm hay muộn. Request đếm trực tiếp.
      `node --check` sạch, bộ kiểm 30/30.
- [x] 2.4 Hiển thị card User hoạt động theo dạng `active/total · rate%` khi có dữ liệu hợp lệ — **ĐO 04/09:** `app.js:3115-3116` hiện phần trăm + `<b>N/M</b> tài khoản đã dùng`
- [x] 2.5 Đổi cột `Success Rate` thành `Tỷ lệ thành công` — **ĐO 04/09:** `Success Rate` 0 kết quả trong `web/`
- [x] 2.6 Kiểm tra insight/delta không đưa baseline giả trở lại
      → **KIỂM 08/09: mã KHÔNG bịa baseline — nhưng TRÔNG NHƯ CÓ, và đã dọn.**
      `deltaBaseline()` bỏ qua hoàn toàn tham số hệ số: không có kỳ gốc thật thì trả `0` và
      `deltaLine` hiện "chưa có dữ liệu". Đúng như mục này yêu cầu.
      **Nhưng ba thứ chết vẫn nằm đó:** lời gọi ở tab Chi phí vẫn truyền `0.88, 0.57`;
      `renderDelta` vẫn nhận `mockPrev`/`mockSame`; `deltaLine` vẫn còn nhánh vẽ dấu `≈`
      cho baseline giả. Ai đọc dòng `renderDelta(..., 0.88, 0.57)` đều có quyền kết luận
      dashboard đang bịa kỳ gốc ở mức 88%/57%. Đó chính là đường để nó quay lại.
      Đã bỏ hẳn cả ba, và ghim bằng `tests/no-fake-baseline.test.js` (6 phép kiểm), trong đó
      có một **phép kiểm ngược** chứng minh nó thật sự đỏ khi hệ số được thêm lại.
      Bản đầu của phép kiểm dùng ranh giới từ quanh "mock" — **bỏ sót đúng thứ cần bắt**,
      vì `mockFactor` có ký tự từ ngay sau. Đã sửa và ghi lý do trong chính file kiểm
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

- [x] 4.1 Điền dropdown User từ danh mục tài khoản thực và dùng id ổn định làm value
      → **Vế đầu ĐÃ CÓ; vế "id ổn định" KHÔNG LÀM ĐƯỢC, và đã đo để chứng minh.**
      Dropdown dựng từ `filterAccounts()` tức danh mục tài khoản thật từ database — vế đầu
      xong từ trước.
      **Vì sao id ổn định không giải quyết được vấn đề nó nhắm tới:** dòng usage KHÔNG mang
      `userId`, chỉ mang nhãn (`r.ug`) — chú thích ở `app.js` cũng ghi "không nguồn nào ghi
      userId". Không có khoá để ghép thì id ở dropdown cũng không tách được usage của hai
      người trùng tên; nó chỉ tạo cảm giác chính xác mà dữ liệu không đỡ nổi.
      **Và trùng tên là chuyện có thật, không phải lý thuyết** — đo trên database 08/09:
      938 tài khoản `kind='real'` nhưng chỉ **890 nhãn** khác nhau; **41 nhãn trùng, phủ 89
      tài khoản**, nặng nhất "Nguyễn Trang" = **6 tài khoản**. Tức cứ ~10 lần chọn một tên
      thì 1 lần đang xem số của nhiều người gộp lại.
      **Thứ làm được là NÓI RA:** `userLabelAccountCount()` + cảnh báo "Nhãn X ứng với N tài
      khoản khác nhau — số đang xem là của cả N người gộp lại". Có phép kiểm riêng
- [x] 4.2 Làm dropdown User phụ thuộc phòng ban và agent đang chọn
      → **ĐÃ CÓ SẴN, không phải làm.** Đo 08/09: `filterAccounts()` lọc tài khoản theo
      phòng ban (kèm **đơn vị con** qua `unitDescendants`) và theo agent; dropdown dựng từ
      chính nó, có tạm gỡ bộ lọc user ra để danh sách không tự thu về một tên
- [x] 4.3 Áp user filter đồng bộ lên KPI, chart, table và cảnh báo có dữ liệu user-level
      → **ĐẠT bằng kiến trúc, không phải bằng cách kiểm từng chỗ.** `scopedRows()` =
      `applyFilters(scopeBase())` là **điểm nghẽn duy nhất**, và `renderAll()` lấy đúng một
      `rows` rồi truyền cho toàn bộ renderer (Tổng quan, Phòng ban, Agents, Providers,
      Models, Users, Chi phí, Hiệu năng, biểu đồ). Không có đường nào để một chỗ lệch khỏi
      bộ lọc.
      Vế "cảnh báo có dữ liệu user-level" chính là khối cảnh báo ở mục 4.5, nay gánh thêm
      cảnh báo nhãn trùng của 4.1
- [x] 4.4 Bổ sung trường User vào bảng nhập tay, bắt buộc với agent cần đăng nhập — **KHÔNG CÒN ĐỐI TƯỢNG:** luồng nhập tay đã bị bỏ khi dashboard chuyển sang chỉ đọc database (`index.html:399`, `app.js:529`)
- [x] 4.5 Cảnh báo rõ các bản ghi tổng hợp không thể quy về user
      → **LÀM 08/09.** Khối cảnh báo ngay dưới thanh lọc, chỉ hiện khi đang lọc user **và**
      thực sự có phần bị loại. Nói bằng con số cụ thể — số dòng, số request, số token, và
      thuộc agent nào — chứ không nói “một số dòng bị bỏ”, vì người đọc không biết là 3 hay
      3.000.
      **Vì sao cần:** bộ lọc user vốn đã loại các dòng này (`r.ug !== f.user`), nhưng loại
      **im lặng**. Người xem thấy agent về 0 và tưởng nó không hoạt động trong kỳ, trong khi
      thật ra nguồn không ghi được người dùng. Câu chữ nói thẳng “không phải vì chúng bằng
      không”.
      Có phép kiểm riêng cho việc `userScopeGap()` **khôi phục lại** `filters.user` sau khi
      tạm gỡ — quên trả lại thì mọi renderer chạy sau đó mất bộ lọc mà không ai báo

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
- [x] 6.4 Tính cảnh báo agent có chi phí cao hơn 30% trung bình agent hoạt động
      → **LÀM 08/09.** `agentCostOutliers(rows)`: mẫu là agent có **CẢ** chi phí lẫn request
      trong kỳ (agent có request mà chưa quy được tiền không được kéo mẫu số xuống).
      Ngưỡng đặt tên `AGENT_COST_OUTLIER_RATIO = 1.30`, không rải số 1.3 giữa mã.
      **Tính chất đã ghim bằng phép kiểm, không phải lỗi:** một agent quá lớn tự kéo trung
      bình lên và che agent lớn vừa — `[200, 900, 10, 10]` cho trung bình 280, ngưỡng 364,
      nên 200 KHÔNG bị cảnh báo dù gấp 20 lần hai agent nhỏ. Ai đổi công thức thì phép kiểm
      gãy chứ không im
- [x] 6.5 Tạo bảng cảnh báo gồm bằng chứng, mức vượt, kỳ và thao tác lọc theo agent
      → **LÀM 08/09.** Bảng 5 cột: Agent · Chi phí trong kỳ · Trung bình agent · Vượt ·
      Lượt gọi. Dòng ghi chú phía trên nêu mức trung bình, **số agent làm mẫu** và khoảng
      ngày. Bấm một hàng là đặt `state.filters.agent` rồi `renderAll()`.
      **Ô tiền dùng `moneyCell(g.cost, ..., g)`** chứ không `money()`: spec chính
      `visible-data-provenance` buộc mọi ô tiền tự khai nguồn, mà cảnh báo này đứng hay đổ
      hoàn toàn dựa vào con số đó — 28,2% tiền trên dashboard là suy từ bảng giá.
      Mẫu dưới 3 agent bị **đánh dấu chứ không giấu**: vẫn cảnh báo, kèm câu nhắc trung bình
      bị chính agent đang xét kéo lên
- [x] 6.6 Kiểm tra cảnh báo cập nhật theo time range và bộ lọc toàn cục
      → **LÀM 08/09 bằng thiết kế chứ không bằng cách kiểm sau.** `renderAgentCostAlerts(rows)`
      gọi trong `chartsCost(rows)` và tính lại từ chính `rows` **đã lọc**, không giữ bản tính
      sẵn — nên không có đường nào để nó lệch khỏi bộ lọc. Sự kiện click gắn một lần
      (`data-alert-bound`) nên vẽ lại nhiều lần không chồng handler

## 7. Performance UI

> **RÀ SOÁT 04/09/2026 — TIỀN ĐỀ CỦA CẢ NHÓM NÀY ĐÃ SAI.** Các ô 7.1, 7.2, 7.4 và 7.6
> yêu cầu **gỡ bỏ** p95/p99 và các KPI 4xx/5xx/429 với lý do chúng là số **suy diễn,
> không có nguồn**. Lý do đó đúng vào 25/07/2026 nhưng **không còn đúng**: migration 006
> (31/08) thêm `fact_call.outcome` và `error_code` — mã lỗi nay là số đo thật của từng
> lượt gọi; migration 010 (03/09) dựng `latency_resolved`, p95 Gateway tính CHÍNH XÁC từ
> `duration_ms` thô thay vì nội suy trong ô histogram rộng 33,6 giây. Làm theo nguyên văn
> bây giờ sẽ **xoá đi bốn phép đo có thật**. Nhóm này cần một quyết định phạm vi trước khi
> đụng vào, không phải cần người gõ phím.

- [x] 7.1 Tinh gọn dải KPI còn Tỷ lệ thành công
      → **LÀM 08/09.** Dải KPI tab Hiệu năng từ 7 thẻ còn **1**. Mô tả thẻ giữ lại được
      viết rõ mẫu số: “tổng request CÓ ĐO ĐƯỢC mã trả về” — agent không qua Google thì
      không ai biết nó lỗi bao nhiêu, đưa vào mẫu số là ngầm khai chúng đều thành công
- [x] 7.2 Loại tổng request, p95/p99 và KPI 4xx/5xx/429 suy diễn
      → **LÀM 08/09.** Bỏ 6 thẻ: `m-pf-req`, `m-pf-4xx`, `m-pf-5xx`, `m-pf-429`,
      `m-pf-p95`, `m-pf-p99`, kèm 6 lệnh `set()` tương ứng trong `app.js`.
      **Phát hiện khi làm:** hai thẻ p95/p99 ghi nhãn “mốc mà 95%/99% lượt gọi nhanh hơn”
      nhưng số đưa vào là `A.lat`/`A.lat99` — **bình quân có trọng số theo lượt gọi, không
      phải phân vị**. Nhãn hứa nhiều hơn thứ đo được, và sai theo kiểu không ai phát hiện
      vì con số vẫn trông hợp lý. Đã ghi lý do vào chú thích ngay chỗ xoá.
      Ba tỷ lệ mã lỗi vẫn còn ở biểu đồ tròn ngay dưới, nơi có chú giải kèm mẫu số
- [x] 7.3 Đổi biểu đồ tỷ lệ lỗi theo agent thành donut
      → **LÀM 08/09, nhưng KHÔNG đổi thẳng như câu chữ của mục này.** Biểu đồ cũ vẽ `g.er`
      — **tỷ lệ** lỗi của từng agent. Donut biểu diễn *phần của một tổng*, mà các tỷ lệ độc
      lập cộng lại không ra gì cả: donut của tỷ lệ là một cái bánh không có nghĩa.
      Nên vẽ **tỷ trọng**: lát bánh = SỐ lượt lỗi agent đó đóng góp (`e4+e5+e429`), còn tỷ
      lệ riêng của nó đưa vào chú giải (`descs`) nên không mất thông tin nào.
      Không lỗi nào đo được thì hiện một lát “Không ghi nhận lỗi nào” — vẽ bánh rỗng hay
      chia đều các lát là bịa ra một cơ cấu không ai đo được.
      Design §8 vốn viết “**tỷ trọng** lỗi”, nên đây là bám design chứ không phải đi lệch
- [x] 7.4 Thêm chú giải 429 là vượt RPM/TPM/quota và chỉ hiển thị tỷ lệ khi có dữ liệu thật
      → **LÀM 08/09 — và hoá ra là VÁ LẠI thứ chính mục 7.1-7.2 vừa làm hỏng.**
      Lời giải nghĩa bốn nhóm mã trước đây nằm trên dòng mô tả của bốn thẻ KPI, và chú giải
      biểu đồ **cố ý bỏ trống để khỏi lặp** — có ghi rõ trong chú thích mã. Bỏ bốn thẻ đó
      xong thì lời giải nghĩa biến mất theo, người xem còn lại bốn con số không ai giải
      thích. Đã đưa hẳn vào `descs` của chú giải, chỗ không phụ thuộc thẻ nào.
      429 nói rõ: **vượt hạn mức RPM/TPM/quota của nhà cung cấp, không phải lỗi mã nguồn**.
      Vế “chỉ hiển thị khi có dữ liệu thật” đã đúng từ trước: không có `codeAvailable` thì
      biểu đồ rút còn hai lát thành công/lỗi, không chia bốn lát giả
- [x] 7.5 Đổi nhãn còn lại sang tiếng Việt và bỏ mọi badge `MỚI` — **ĐO 04/09: CHƯA.** Còn 4 badge ở `index.html:1154,1159,1164,1188`, tất cả trong tab Hiệu năng
      → **LÀM 08/09.** Cả 4 badge đã bỏ: 3 cái đi theo các thẻ KPI bị xoá ở 7.2, cái thứ tư
      ở tiêu đề biểu đồ tròn. **Xoá luôn quy tắc CSS `.pill-new`** vì không còn ai dùng —
      `grep pill-new` nay trả 0 ở cả `index.html`, `app.js` và `dashboard.css`.
      Sửa thêm hai chỗ ghi “Tỉ lệ thành công” thành “Tỷ lệ thành công” cho khớp spec
- [x] 7.6 Cập nhật bảng hiệu năng để không trình bày percentile hoặc số lỗi không có nguồn
      → **LÀM 08/09.** Bỏ hai cột “Thời gian phản hồi” và “Trường hợp chậm nhất” — cùng lỗi
      nhãn-hứa-phân-vị-mà-đưa-trung-bình như 7.2. Sửa `emptyRow(7)` → `emptyRow(5)` cho khớp;
      kiểm lại header 5 cột = 5 ô `<td>` = `emptyRow(5)`.
      Số lỗi không có nguồn đã được xử lý từ trước: agent không đo được mã trả về hiện “—”
      chứ không hiện 0%

## 8. Styling, Cleanup, and Verification

- [x] 8.1 Bổ sung style responsive cho tab hợp nhất, sticky matrix và donut mới
      → **Donut mới KHÔNG cần style mới**: nó dùng lại `.wf-donut-wrap` + `.legend-described`
      đã có, và `.wf-donut-wrap` xuất hiện trong **4 `@media`**. Bảng cảnh báo dùng lại
      `.table-container` (**6 `@media`**). Tab hợp nhất và sticky matrix đã làm ở đợt trước.
      **CHƯA kiểm bằng mắt:** `.user-scope-note` là class mới duy nhất **không nằm trong
      `@media` nào** — nó là một hàng flex hai span, chữ tự xuống dòng nên về lý thuyết
      không vỡ, nhưng nó có `margin-top:-6px` để nép sát thanh lọc. Màn hình hẹp làm thanh
      lọc xuống dòng thì -6px đó có thể chồng lên. **Chưa nhìn thấy nó dựng ra nên không
      khẳng định**
- [x] 8.2 Kiểm tra contrast và trạng thái unavailable trên dark/light theme
      → **ĐO 08/09 bằng số, không bằng mắt.** Quét mọi class change này thêm hoặc dùng lại:
      cái nào **mang màu** đều có quy tắc light-theme — `.user-scope-note` 2, `.li-desc` 1,
      `.wf-legend` 1, `.metric-card` 1, `.table-container` 2. Hai class **0 quy tắc**
      (`.wf-donut-wrap`, `.legend-described`) đã kiểm: chúng chỉ khai bố cục (`flex`, `gap`),
      không màu nào — nên 0 là **đúng, không phải thiếu**.
      Tính hẳn tỷ số tương phản WCAG cho khối mới, trên nền đã hoà alpha với nền trang:
      · tối, chữ thường **11,97:1** · tối, chữ đậm **13,86:1**
      · sáng, chữ thường **5,84:1** · sáng, chữ đậm **7,47:1**
      **Cả bốn đạt AA (≥4,5:1)**, biên rộng.
      Trạng thái unavailable: đã kiểm ở 8.4 — kỳ rỗng và tổ hợp không ra dòng nào đều không
      ném lỗi
- [x] 8.3 Xóa chart instance, DOM id, renderer và CSS của section đã loại bỏ
      → **KIỂM 08/09 bằng quét máy, không bằng mắt.** Hai chiều đều sạch:
      · **180 id** khai trong `index.html`, **0 cái mồ côi** (không được `app.js`, markup hay
        CSS tham chiếu)
      · **0 chart id** trong `app.js` vẽ vào canvas không tồn tại
      · `.pill-new` đã xoá cùng badge; `grep` trả 0 ở cả ba file
      · 6 lệnh `set()` của các thẻ KPI đã bỏ cũng đã gỡ
      Chú thích đầu `index.html` còn kê “pill MỚI” như một thứ file này có — đã sửa.
- [x] 8.4 Kiểm thử bộ lọc time range, phòng ban, user, agent, provider và model kết hợp
      → **LÀM BẰNG CÔNG CỤ, không bằng mắt** — `tools/soat_to_hop_bo_loc.js`. Đặt **43 tổ
      hợp** (từng bộ lọc một mình × mọi giá trị, cặp phòng ban×agent, cặp user×agent, tổ hợp
      không thể có dòng nào, và một khoảng ngày rỗng), sau mỗi tổ hợp gọi `renderAll()` rồi
      kiểm. **Không tổ hợp nào ném lỗi hay vượt tổng.**
      **Phép kiểm chính là BẤT BIẾN SỐ HỌC**, không phải quét chuỗi: mỗi dòng có đúng một
      agent, nên cộng tổng của **8 agent** phải bằng tổng không lọc — khớp cả `r`, `tokens`,
      `cost`. Bộ lọc hỏng kiểu gì cũng làm đẳng thức này gãy
- [x] 8.5 Kiểm thử dữ liệu có userId, thiếu userId, thiếu budget, cây phòng ban một cấp/nhiều cấp và dữ liệu rỗng
      → **Cả bốn trường hợp đều CÓ THẬT trong dữ liệu sống**, nên 43 tổ hợp ở 8.4 đã đi qua
      chúng thật chứ không phải qua dữ liệu dựng:
      · **thiếu định danh user** — `/api/usage` trả 201 dòng, và log api.js báo *"201 dòng sử
        dụng (20.322 lượt) không ghép được vào tài khoản nào trong 944 tài khoản"*
      · **thiếu budget** — 6/8 agent có `budget_usd`, **2 agent không**: Tools Quizzer và
        Trợ lý ảo Ralli
      · **cây nhiều cấp** — 130 đơn vị trải **6 cấp** (0→5), không phải danh sách phẳng
      · **dữ liệu rỗng** — công cụ đặt hẳn khoảng 1999-01-01→1999-01-31 và một tổ hợp bộ lọc
        không thể khớp dòng nào; cả hai đều render sạch
- [x] 8.6 Đối chiếu toàn bộ nội dung biên bản 25/7 và xác nhận không còn nhãn `Success Rate`, `Tỷ lệ áp dụng`, `Nhắc đào tạo` hoặc badge `MỚI` trong phạm vi — **ĐO 04/09: 3/4 sạch.** `Success Rate` 0 · `Nhắc đào tạo` 0 · `Tỷ lệ áp dụng` chỉ còn trong ghi chú mã nguồn · badge `MỚI` **còn 4**
      → **ĐO LẠI 08/09: 4/4 SẠCH.** `Success Rate` 0/0/0 · `Nhắc đào tạo` 0/0/0 ·
      `Tỷ lệ áp dụng` 0 ở markup, chỉ còn **2 chú thích** mô tả endpoint `/api/adoption`
      (đó là tên của API, không phải nhãn hiển thị) · badge `MỚI` **0** ở markup, chỗ duy
      nhất còn lại là chú thích đầu file và đã sửa.
      **Một chỗ lệch nhẹ so với proposal, không sửa:** proposal viết đổi “Tỷ lệ áp dụng”
      thành **“Tài khoản hoạt động”**, thực tế nhãn đang là **“Tài khoản đang dùng (%)”**.
      Đồng nghĩa, và đổi một nhãn người dùng đang quen chỉ vì khác từ là churn — nêu ra để
      anh Tuấn quyết nếu muốn khớp đúng chữ
