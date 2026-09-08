## 1. Chuẩn bị

- [x] 1.1 Xác nhận change `switch-default-dsn-to-postgres` đã xong — dashboard phải nối được database ổn định trước khi bỏ đường dự phòng
- [x] 1.2 Xác nhận `git status` sạch trên `web/`, `scripts/` để quay lui được từng bước
- [x] 1.3 Chạy `node --test tests/date-range-filter.test.js`, ghi lại baseline 6/6 xanh
- [x] 1.4 Mở dashboard với backend chạy, chụp lại con số mốc từng tab để đối chiếu ở nhóm 8 (851.897.312 token · 285,18 USD · 8 agent · 2026-01-01→2026-08-13)
- [x] 1.5 Điểm neo: **thay chính vị trí `.proto-note`** (dòng 258 cũ) bằng `#load-note`, và thay hai chỉ báo tĩnh trong `.status-bar` bằng `#conn-*` / `#freshness-*`. Trên cùng, thấy ngay, `hidden` thì không chiếm chỗ
- [x] 1.6 Đối chiếu 8 agent với `ref_budget` — **đã làm, và ra ba nhóm chứ không phải hai**:
  - 6 agent có `budget_usd` (30 · 50 · 20 · 20 · 20 · 20 USD)
  - `Trợ lý ảo Ralli` có `budget_tokens` = 50.000.000, **không** có USD
  - `Tools Quizzer` **không có dòng `ref_budget` nào**
  - `ref_budget`: 7 dòng · 6 có USD · 1 có token · 0 dòng không tra ra agent
  - `api.js` hiện cho ra đúng 6 hạn mức. Nên requirement 5.4 phải phân biệt **ba** trạng thái, không phải hai: *có hạn mức USD* · *có hạn mức nhưng không phải USD* · *chưa đặt hạn mức*. Gộp hai cái sau thành một sẽ nói sai về Ralli
  - `aliases`: quyết định ở bước 5.5 sau khi bỏ hằng số gõ tay; 8 tên trong `dim_agent` tra ra `ref_budget` không cần alias nào

## 2. `api.js` — trả về lý do hỏng thay cho `null`

- [x] 2.1 Đổi `catch` ở `web/js/api.js:250` trả về đối tượng phân biệt được bốn trường hợp: không nối được backend · endpoint trả mã lỗi · database chưa có dữ liệu usage · chạy từ `file://`
- [x] 2.2 Kèm trong kết quả: địa chỉ đã thử (`base()`), endpoint hỏng, mã HTTP nếu có
- [x] 2.3 Giữ nguyên hợp đồng "chỉ bơm dữ liệu, không đụng giao diện" — `api.js` MUST NOT vẽ gì
- [x] 2.4 Giữ nguyên việc không `reject`, chỉ đổi từ im lặng sang nói rõ
- [x] 2.5 Chạy test — phải xanh 6/6

## 3. `app.js` — đảo luồng thành nạp trước, vẽ sau

- [x] 3.1 Thêm `renderShell()` vẽ khung kèm trạng thái "đang nạp…", KHÔNG vẽ số và KHÔNG vẽ biểu đồ rỗng
- [x] 3.2 Thêm `renderError(lyDo)` hiện thông báo tại điểm neo đã chọn ở 1.5, nói được: không nối được, địa chỉ đã thử, cách khắc phục
- [x] 3.3 Sửa `init()` (`web/js/app.js:5245`): gọi `renderShell()` thay cho `renderAll()`; `renderAll()` chỉ chạy sau khi có dữ liệu thật
- [x] 3.4 Sửa `napTuBackend()`: nhánh hỏng gọi `renderError()` thay vì `return` im lặng; xoá docstring nói "Không có backend thì không có gì xảy ra"
- [x] 3.5 Xác nhận trạng thái lỗi không hiện con số nào ở bất kỳ tab nào
- [x] 3.6 Chạy test — phải xanh 6/6

## 4. `app.js` — tách `localStorage` thành lựa chọn và dữ liệu

> ⚠ **ƯU TIÊN CAO HƠN NHÓM 6.** Đã đo trên trình duyệt thật 17/08: `localStorage` đang giữ
> **345 KB dữ liệu backend** (224 ngày · 1.154 dòng · `cached` khớp đúng con số billing-only
> của `api.js`), và khi backend chết thì màn hình hiện **`localStorage`, KHÔNG hiện
> `SEED_DAYS`**. Xoá dữ liệu nhúng ở nhóm 6 mà chưa sửa nhóm 4 thì **không đóng được đường
> dữ liệu cũ nào** — chỉ đổi từ hiện số nhúng sang hiện số phiên trước.

- [x] 4.1 Sửa `saveState()` (`web/js/app.js:2639`) chỉ ghi **danh sách cho phép** các khoá lựa chọn (tab, giao diện, khoảng ngày, bung/thu cây, bộ lọc) — không ghi `days`, `dayOrder`, `pricing`, hay bảng dẫn xuất nào
- [x] 4.2 Sửa `loadState()` chỉ đọc các khoá đó; không còn đường nào để số liệu quay về từ `localStorage`
- [x] 4.3 Đổi tên khoá `STORE` (`web/js/app.js:11`) một lần để bỏ state cũ trên máy đang dùng
- [x] 4.4 Xác nhận 9 chỗ gọi `saveState()` đều không còn ghi được số liệu ra `localStorage`
- [x] 4.5 Kiểm bằng tay: mở dashboard, đổi bộ lọc, tải lại với backend TẮT → phải báo lỗi, MUST NOT hiện số của lần nạp trước
- [x] 4.6 Kiểm bằng tay: đổi tab + giao diện tối + khoảng ngày, tải lại với backend CHẠY → ba lựa chọn được giữ
- [x] 4.7 Chạy test — phải xanh 6/6

## 5. `app.js` — bảng giá và hạn mức chỉ từ API

- [x] 5.1 `basePricing` (`web/js/app.js:454`) khai rỗng, chỉ nhận từ `/api/catalog`
- [x] 5.2 `AGENT_MONTHLY_BUDGETS` (`web/js/app.js:15`) khai rỗng, chỉ nhận từ `ref_budget`
- [x] 5.3 `MONTHLY_BUDGET` tính từ những agent **có** hạn mức; agent chưa đặt không bị suy ra 0
- [x] 5.4 Giao diện nói được "chưa đặt hạn mức", phân biệt với "hết hạn mức" (0) — Ralli đặt theo token nên thuộc nhóm chưa đặt
- [x] 5.5 Xử lý `aliases` theo kết luận ở 1.6: bỏ nếu không còn tác dụng, không để lại cấu hình chết
- [x] 5.6 Chạy test — phải xanh 6/6

## 6. Xoá dữ liệu nhúng

- [x] 6.1 Xoá `SEED_DAYS` (`web/js/app.js:482`, ~267.787 ký tự)
- [x] 6.2 Xoá `buildJuneExcelWeeks()` (`web/js/app.js:2314`, ~3.634 ký tự)
- [x] 6.3 Sửa `defaultState()` (`web/js/app.js:2590`) không còn trộn hai nguồn nhúng; trả về state rỗng kèm lựa chọn người dùng
- [x] 6.4 Xoá `SEED_DAY`. `minDataDate()`/`maxDataDate()` từng lùi về hằng số `"2026-07-01"` khi `dayOrder` rỗng — tức **bịa một ngày** rồi mọi thứ tính từ nó trông như số đo. Nay lùi về hôm nay qua `today0()`, và `dayOrder` rỗng chỉ xảy ra khi `renderError()` đã chiếm màn hình
- [x] 6.5 Chạy test — nó nạp trọn `app.js` trong `vm` nên đây là phép kiểm bắt tham chiếu treo; phải xanh 6/6
- [x] 6.6 Xoá `web/js/fallback/ralli-users.js`; xoá cả thư mục `fallback/` nếu trống
- [x] 6.7 Bỏ thẻ `<script>` nạp `ralli-users.js` trong `web/index.html` nếu có
- [x] 6.8 Xoá `web/js/app.js.bak` (194 KB)
- [x] 6.9 Tìm trong `web/js/` xác nhận không định danh nào (`SEED_DAYS`, `buildJuneExcelWeeks`, `RALLI_USERS`, `basePricing`, `AGENT_MONTHLY_BUDGETS`) còn mang dữ liệu gán cứng
- [x] 6.10 Chạy test — phải xanh 6/6

## 7. Gọn đường ống

- [x] 7.1 `scripts/update_dashboard.py`: xoá bước `[10/10] Va du lieu du phong vao app.js` cùng hai lời gọi bên trong
- [x] 7.2 Đánh số lại nhãn các bước thành `[n/9]` liên tục
- [x] 7.3 Cập nhật docstring của `update_dashboard.py` cho đúng số bước
- [x] 7.4 Xoá `scripts/sinh_du_lieu_dashboard.py` và `scripts/va_app_js.py`
- [x] 7.5 Đọc toàn bộ lời gọi lệnh trong `update_dashboard.py`, xác nhận không lời gọi nào sinh hoặc sửa file trong `web/`
- [x] 7.6 `tools/doi_chieu_web_vs_file.py:38` tìm file **cạnh chính nó** trong `tools/`, nhưng file nằm ở `tests/fixtures/` — nên công cụ đó **đang hỏng**. Đã `git mv` về `tools/`: vừa đúng quy ước layout, vừa sửa một thứ hỏng từ trước. Xác nhận công cụ chạy lại được. `tests/fixtures/` đã rỗng nên xoá
- [ ] 7.7 Chạy trọn đường ống rồi kiểm `git status` trên `web/` — không file nào bị đường ống sửa — **CHƯA chạy trọn, nhưng đã chứng minh bằng đường khác (07/09/2026).** Quét toàn bộ 6 script mà `update_dashboard.py` gọi qua 9 bước: **không script nào có đường ghi vào `web/`**. Ba chỗ duy nhất nhắc tới tên đó đều vô hại — `update_dashboard.py:19` là docstring khẳng định đúng điều này, `:21` là ghi chú lịch sử về bước 10 đã xoá, `rebuild_db.py:26` là `data/raw_web/` (khác thư mục). Dấu vết hai lần chạy `rebuild_db.py` + `audit_db.py` ngày 02/09 và 04/09 còn trong `var/rebuild-cuoi.txt`, `var/audit-cuoi.txt`; `git status web/` hôm nay chỉ hiện `M web/js/app.js` — sửa tay bằng Edit cho lỗi BOM/CSV, không phải đường ống sinh ra. **Giữ ô trống có chủ ý:** soát tĩnh mạnh hơn một lần chạy (nó phủ mọi lần chạy, không chỉ lần này) nhưng nó KHÔNG phải là việc mà mục này yêu cầu, và các bước 1–7 gọi API ngoài nên chưa được chạy lần nào trong phiên. Không tự tick để khỏi biến "chứng minh kiểu khác" thành "đã làm đúng như ghi"

## 8. Nghiệm thu bằng mắt

- [x] 8.1 Backend chạy: mở dashboard, soát **từng tab**, đối chiếu với con số chụp ở 1.4
- [x] 8.2 Xác nhận không biểu đồ nào trống bất thường và không con số nào về 0 vô cớ
- [x] 8.3 Xác nhận khoảng ngày của dữ liệu hiện ra mà không phải bấm vào đâu, khớp `ranges.usage` của `/api/health`
- [x] 8.4 Xác nhận cảnh báo độ phủ từ `/api/usage-by-account` hiện cùng bảng theo người dùng
- [x] 8.5 Xác nhận dòng có `token_estimated` được đánh dấu là số ước tính
- [x] 8.6 Backend tắt: tải lại → báo lỗi, không con số nào
- [x] 8.7 Backend chạy nhưng một endpoint lỗi → nói rõ endpoint nào và mã trả về
- [x] 8.8 Database không có dữ liệu usage → nói rõ, phân biệt với không nối được backend
- [x] 8.9 Mở `web/index.html` bằng bấm đúp → nói cần chạy backend, không hiện số

## 9. Tài liệu

- [x] 9.1 `README.md`: bỏ lời hứa "bấm đúp `index.html` vẫn xem được"; nói rõ cần backend
- [x] 9.2 `README.md`: cập nhật 10 bước → 9 bước
- [x] 9.3 `docs/reference/toan-trinh-du-lieu.md`: bỏ chặng vá dữ liệu dự phòng, đánh số lại
- [x] 9.4 `docs/reference/huong-dan-cap-nhat-dashboard.md`: bỏ hướng dẫn liên quan hai script đã xoá
- [x] 9.5 `docs/reference/cay-thu-muc.md`: cập nhật bảng "thêm file mới thì để đâu" nếu có mục về `fallback/`
- [x] 9.6 Xác nhận `docs/archive/` KHÔNG bị sửa — nó ghi điều đã đúng lúc viết

## 10. Panel nhập liệu tay — phát hiện khi thực thi, artifacts không lường tới

- [x] 10.1 Panel `✎ Dữ liệu nguồn` (`index.html:385-409`) sau thay đổi này thành cái bẫy: người dùng gõ số, bấm Lưu, số **hiện lên và cộng vào tổng** — trộn với số database mà không gì nói ra — rồi tải lại là mất sạch vì `localStorage` không còn giữ số liệu. Nó cũng vi phạm requirement *"dashboard SHALL lấy mọi con số từ database"*
- [x] 10.2 Đã chọn **phương án A**: xoá hẳn panel. Xoá `#data-panel`, nút `#btn-data`, và cụm 12 hàm chỉ phục vụ nó (`renderDataPanel`, `renderDataDay`, `renderDataDayHint`, `dataMsg`, `saveDay`, `delDay`, `insertDayOrdered`, `textInput`, `numInput`, `modelSelect`, `tdNum`, `sanitizeUsageRows`)
- [x] 10.3 **Giữ** panel `⚙ Cấu hình giá`: nó sửa `state.pricing` trong phiên để thử "nếu đơn giá khác thì tiền bao nhiêu", vẫn có ích, và không giả vờ là số đo
- [x] 10.4 Soát hàm mồ côi bằng cách **so với bản trước change B**: 13 hàm đã chết từ trước (không phải việc của change này), 4 hàm mới mồ côi do change B — `rid`, `adoptionRatio`, `splitCombinedDepartment`, `isExcludedAgent` — đã xoá cùng `EXCLUDED_AGENTS`
- [x] 10.5 Kiểm `sanitizeUsageRows` có cần cho dữ liệu API không trước khi xoá: **không**. Bản cũ chưa bao giờ áp nó lên dữ liệu API (`napTuBackend` gán `state.days` thẳng), và `dim_unit` không có nhãn phòng ban gộp nào nên `splitCombinedDepartment` vô dụng với dữ liệu database

## 11. Định danh tiếng Anh cho mã mới (phần ① của kế hoạch đổi tên)

- [x] 11.1 Đổi định danh tiếng Việt trong `renderDataProvenance` — **theo phạm vi hàm**, không thay toàn file, vì `y` cũng là biến năm ở ba chỗ khác: `ngayCuoi`→`lastDay` · `soNgayCu`→`daysStale` · `tienHoaDon`→`invoicedUsd` · `tienUoc`→`estimatedUsd` · `dongUoc`→`estimatedRows` · `dongTong`→`totalRows` · `tong`→`totalUsd` · `y`→`notes`
- [x] 11.2 Hàm mới đặt tên tiếng Anh ngay: `loadNote`, `hideLoadNote`, `setConnIndicator`, `renderShell`, `renderError`, `renderDataProvenance`, `today0`, `makeError`, `PREF_KEYS`
- [x] 11.3 Ghi chú giữ nguyên tiếng Việt; **không** đổi chuỗi hiển thị nào — người dùng đọc chúng
- [x] 11.4 `napTuBackend` (có sẵn) và `cachedNgoai` (`api.js`) vẫn là tiếng Việt — thuộc phần ② của kế hoạch, làm ở change riêng `rename-identifiers-to-english` sau khi change này lành — **ĐO 07/09/2026: mô tả trên đã lỗi thời, việc ĐÃ xong.** `grep` toàn bộ `web/js/` không còn dòng nào mang hai tên đó: `napTuBackend` → `loadFromBackend` (`app.js:21,521,891,903`), `cachedNgoai` → `cachedOutsideInput` (`api.js:350`). Không cần change `rename-identifiers-to-english` riêng cho hai tên này nữa. **Còn sót ở ghi chú, không ở mã:** tên cũ vẫn nằm trong chú thích tại `tools/chay_dashboard_trong_node.js:143,199,209` và `tests/load-failure-states.test.js:6,111` — đã kiểm từng dòng, **tất cả đều là comment `//`, không dòng nào là lời gọi hàm**, nên không có gì gãy. Chỉ là chú thích gọi tên đã đổi

## 12. Bộ kiểm mới, thường trực

- [x] 12.1 Thêm `tests/load-failure-states.test.js` — 7 phép kiểm, **không cần backend** (thay `fetch` bằng bản giả), nạp trọn `api.js`+`app.js` trong `vm` với DOM giả lấy đúng 184 `id` từ `index.html`
- [x] 12.2 Nội dung: 4 nhánh lỗi mỗi nhánh báo lên màn hình và **không hiện số nào** · 4 thông báo phải KHÁC nhau · `index.html` không còn khẳng định gán cứng · frontend không còn khai báo dữ liệu nhúng
- [x] 12.3 Chuyển hai bộ kiểm **cần backend** sang `tools/` theo quy ước layout: `tools/chay_dashboard_trong_node.js`, `tools/kiem_so_qua_api_js.js`
