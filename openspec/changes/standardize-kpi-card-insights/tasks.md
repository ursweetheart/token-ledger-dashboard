> **RÀ SOÁT 04/09/2026 — đọc trước khi làm bất kỳ ô nào.** Change này soạn 22/07/2026,
> trước khi dashboard chuyển sang chỉ đọc database. Ba điều đã đo lại:
>
> - **Số thẻ đã trôi 9 → 8.** Tab Tổng quan hiện có 8 thẻ (`index.html:505-554`), không
>   phải 9 như mọi ô trong file này viết. Đếm lại trước khi trích dẫn con số đó.
> - **Nửa ô 1.3 đã xong, nửa còn lại là lỗi đang sống.** Số giả đã gỡ — `deltaBaseline()`
>   trả `mock:false` ở cả hai nhánh và tham số `mockFactor` không còn được dùng. Nhưng
>   `app.js:1095` trả về `{v:0}` khi thiếu kỳ nền, tức **gộp “chưa có kỳ trước” vào “kỳ
>   trước bằng 0”** — đúng thứ ô 1.3 dặn phải phân biệt.
> - **Vế latency của ô 5.4 đã xong.** `app.js:3548` hiện `A.latAvailable ? ... : chuaCo`,
>   không còn in `0.0 s`. Nhưng ô 2.2 (“ngừng hiển thị p95 khi nguồn không hỗ trợ”) nay
>   **cần xét lại**: migration 010 (03/09) dựng `latency_resolved`, p95 Gateway tính chính
>   xác từ `duration_ms` thô, nên gỡ p95 bây giờ là gỡ một phép đo có thật.

> **THỰC HIỆN 10/09/2026.** Frontend được mở phạm vi cho RIÊNG change này (anh Tuấn chốt
> 10/09), quy ước "không đụng frontend" ngày 14/08 vẫn giữ nguyên ở mọi chỗ khác.
>
> **Đường nghiệm thu.** Container `token-ledger-web` bind `192.168.20.111` (IP máy chủ) nên
> không bật được ở máy dev, và **không sửa `docker-compose.yml` để lách** — theo đúng quyết
> định đã chốt 07/09. Thay vào đó phục vụ `web/` tĩnh ở `127.0.0.1:8080` (cổng này đã nằm
> sẵn trong `DEFAULT_ORIGINS` của backend) rồi trỏ API bằng `?api=http://127.0.0.1:8000`.
> Mọi con số dưới đây đo trên Chrome thật, dữ liệu thật, kỳ `19/07/2026 → 17/08/2026`.

## 1. Insight Data Model

- [x] 1.1 Tạo cấu trúc view-model chung cho value, unit, comparison, direction, semantic status, driver, freshness và definition
      → `kpiView()` trong `web/js/app.js`. Đủ 8 trường ô này liệt kê.
      **`direction` được TÍNH trong hàm, không nhận từ người gọi** — để khai thì sẽ có ngày
      mũi tên và con số nói ngược nhau mà không ai phát hiện. Đã kiểm 6 trường hợp: tăng,
      giảm, phẳng, thiếu kỳ nền, `0 → n`, `0 → 0`.
- [x] 1.2 Định nghĩa ma trận semantics và threshold cấu hình được cho ~~chín~~ **tám** KPI card Tổng quan
      → `OVERVIEW_KPI_SEMANTICS` (8 dòng, không phải 9) + `kpiStatus()`, dùng lại ngưỡng có
      sẵn trong `INSIGHT_THRESHOLDS` thay vì dựng bảng thứ hai.
      **Hai trục tách rời** — điểm chính của ô này: ① chiều biến động tô màu theo DẤU của số
      (`deltaLine`), ② đánh giá tô theo NGƯỠNG (`kpi-warning` / `kpi-critical`). Thấy rõ trên
      màn hình: thẻ AI Agent hiện `▼ 13% KT` (mũi tên đỏ, đang giảm) trên một thẻ viền vàng
      `CẦN THEO DÕI`. Hai tín hiệu, hai chuyện, cả hai đúng.
      **4/8 thẻ để `threshold: null`** vì chưa có ngưỡng THẬT. Bịa ngưỡng cho đủ ma trận là
      dựng cảnh báo giả, đúng loại lỗi ô 1.3 vừa gỡ ở baseline.
- [x] 1.3 Thay logic baseline mock bằng trạng thái thiếu dữ liệu kỳ trước/cùng kỳ có thể phân biệt với giá trị zero
      → **Đây là lỗi đang sống, không phải dọn dẹp.** `deltaBaseline` cũ ép CẢ HAI trạng thái
      về cùng một giá trị `0`, rồi `deltaLine` in `b.v<=0` thành "chưa có dữ liệu". Hệ quả đo
      được: kỳ trước **không có lỗi (0%)** là phép đo thật và là tin tốt, nhưng màn hình nói
      "chưa có dữ liệu" — nghe như máy không đo được.
      Nay tách `has` khỏi `v`, ba trạng thái ba câu: `– KT chưa có kỳ so sánh` · `▲ mới KT · 0`
      · `▲ 75% KT · 40`. Nhánh `0` **không in phần trăm** vì chia cho 0 không định nghĩa được.
      Hai thẻ `users` và `costuser` đổi từ truyền số `0` sang `null`: không tính được số user
      kỳ trước (`applyRealAccountUsage()` ghi đè `USER_ACCOUNTS` toàn cục; `aggregate().u` luôn
      bằng 0 ở đường database), nên câu đúng là "chưa có kỳ so sánh". Xem trên màn hình: đúng
      2/8 thẻ hiện câu đó.

## 2. Metric Accuracy

- [ ] 2.1 Đồng bộ công thức và định nghĩa tổng token, bảo đảm cached/thinking token không bị bỏ sót hoặc cộng trùng
      → **ĐỌC XONG NHƯNG MỞ LẠI, CHƯA DÁM ĐÓNG.**
      Phần `cached`: **đúng, không phải sửa.** `aggregate()` cộng `ti + to + cached`, và
      `api.js:350` chỉ chuyển tiếp `cached` khi `token_source === "billing"` (lúc đó nó là SKU
      nằm NGOÀI input). Nguồn `app` thì cache là tập con của input nên bị ép về 0. Không sót,
      không trùng. Công thức trên thẻ đã sửa lại cho nói đúng điều này.
      Phần `thinking`: **có nghi vấn mới, đo ngày 10/09.** Google trả `28 vào + 5 ra` nhưng
      `tổng = 58`; 25 token chênh là token suy luận, `gemini-2.5-flash` để chúng ở **pool thứ
      ba**, ngoài cả input lẫn output. Dashboard đang cộng `ti + to + cached`, **không cộng**
      `think` — và tới giờ điều đó vẫn đúng, vì `store.py:469` lấy `thinking_tokens` từ nhãn
      `thinking_enabled` trên `monitoring_ai`, tức một LÁT CẮT của chính token monitoring đã
      đếm, cộng vào là đếm hai lần.
      **Câu chưa trả lời được:** hoá đơn có tách pool thứ ba đó ra không. Nếu có thì tổng token
      đang thiếu đúng phần đó — cùng loại lỗi cache hồi 15/08 làm rơi 26% token. Phải đối chiếu
      `fact_billing_daily` với usage metadata rồi mới kết luận. **Không đóng ô này bằng suy luận.**
- [x] 2.2 ~~Xác minh ý nghĩa trường latency và ngừng hiển thị p95 khi nguồn không hỗ trợ p95 tổng hợp chính xác~~
      → **CỐ Ý KHÔNG LÀM VẾ SAU. Làm theo nguyên văn là XOÁ MỘT PHÉP ĐO ĐANG ĐÚNG.**
      Ô này soạn 22/07, khi p95 còn là số bịa ở tầng hiển thị. Migration 010 (03/09) đã dựng
      `latency_resolved`, và p95 của Gateway tính từ `duration_ms` thô nên **chính xác thật**.
      Gỡ nó bây giờ là làm dashboard nghèo đi chứ không trung thực hơn.
      Vế ĐẦU (xác minh ý nghĩa trường latency) thì đã xong và giữ: `api.js` không chia p95 vì
      nó là phân vị chứ không phải số đếm, `app.js` lấy trung bình có trọng số theo số lượt.
      Vế "ngừng hiển thị khi nguồn không hỗ trợ" cũng đã có sẵn dưới dạng `A.latAvailable` /
      `A.lat99Available`, tức đúng tinh thần ô này mà không phải gỡ gì.
- [x] 2.3 Tính contributor hiện tại hoặc contributor tạo biến động lớn nhất theo agent/model/phòng ban khi có đủ dữ liệu
      → Ô này cho phép "hoặc", và bản đang chạy chọn **contributor hiện tại**. Đã có sẵn
      (`topAgent` / `topUnit` / `topRequest` / `topError`), việc của change là đưa nó vào
      view-model thành trường `driver` để mỗi thẻ có đúng MỘT driver.
      Kiểm trên màn hình khi lọc theo `Sale Agent`: driver thẻ token đổi từ "Trợ Lý Ảo Hợp Đồng
      chiếm 11% token" sang "Sale Agent chiếm 100% token" — driver bám theo bộ lọc, không phải
      chuỗi tĩnh.

## 3. Card Rendering

- [x] 3.1 Tạo renderer chung cho giá trị, delta, trạng thái unavailable, driver và metadata nguồn/độ mới
      → `renderKpiCard(v)`. Cố ý **không tạo/sửa phần tử nào có sẵn**: nó ghi vào đúng ba chỗ
      `index.html` đã có (value · delta-badge · insight) cộng một khối tooltip.
      Trạng thái unavailable đi qua `metric-na` — cùng lớp mà bảng Hiệu năng đã dùng, không
      dựng kiểu mới.
- [x] 3.2 Chuyển ~~chín~~ **tám** KPI card Tổng quan sang renderer mới và giới hạn mỗi card ở một comparison cùng một driver
      → Cả 8 thẻ. **Việc gộp này bắt được một khối mã chết**: thẻ tiền trước đây đặt insight
      HAI lần — dòng "top agent chiếm x%" rồi bị dòng "suy từ bảng giá" ghi đè ngay dưới. Đọc
      code thì tưởng cả hai đều chạy. Nay đúng một driver, chọn theo thứ tự quan trọng.
      Đã gỡ `renderSingleDelta()` vì không còn ai gọi: để lại một đường vẽ delta KHÔNG đi qua
      view-model thì lần sau ai thêm thẻ sẽ dựng lại đúng cấu trúc ba-lời-gọi-rời-rạc vừa gộp.
- [x] 3.3 Bổ sung tooltip 12px giải thích công thức, giá trị thành phần và kỳ so sánh
      → `.kpi-tip` + `kpiTipText()`. Thuộc tính `title` của HTML **không đặt được cỡ chữ**
      (trình duyệt tự vẽ) nên phải có khối riêng; `title` vẫn giữ song song cho trình đọc màn
      hình. Đo trên Chrome: `font-size: 12px`, 4 dòng, cao 162px.
      Nội dung thật của thẻ Tổng token: `= Σ token vào + token ra + token cache (SKU riêng của
      hoá đơn).` · `Vào: 71,3 triệu · Ra: 13,6 triệu · Cache: 35,7 triệu` · `So với kỳ trước
      (19/06–18/07): 222,8 triệu` · `Dữ liệu: 2026-09-10`.
      **Hai lỗi chỉ lộ ra khi nhìn màn hình thật, không phép kiểm nào bắt được:**
      · tooltip vẽ phía TRÊN thẻ → hàng thẻ đầu trồi lên đè vào thanh tab, chữ chìm không đọc
        được. Đổi sang vẽ xuống dưới.
      · `z-index` đặt trên riêng tooltip KHÔNG đủ: thẻ cha `position: relative` nhưng
        `z-index: auto` nên không tạo ngữ cảnh xếp lớp, nửa dưới tooltip bị `.wf-chart` đè.
        Phải nâng CẢ THẺ lúc `:hover`. Kiểm lại 3 điểm dọc tooltip, cả 3 đều ở trên cùng.

## 4. Excel Semantic Styling

- [x] 4.1 Thêm semantic color tokens tăng `#00ff00`, giảm `#ff0000`, warning `#ffff00` và neutral tham chiếu `#1c4b73`
- [x] 4.2 Áp dụng đồng bộ status class cho value, icon/mũi tên, dòng insight và viền/tint của card
      → `.metric-card.kpi-warning` / `.kpi-critical` áp cho viền, tint nền, màu giá trị, dải
      màu `::before` của lưới 8 thẻ, và nhãn dòng insight.
      **CỐ TÌNH LÀM KHÁC NGUYÊN VĂN một chỗ.** Ô này dặn áp status class cho cả "mũi tên", mà
      mũi tên ▲▼ thuộc trục CHIỀU BIẾN ĐỘNG — tô nó theo status là gộp lại đúng hai trục mà
      proposal của chính change này yêu cầu tách. Nên "icon" hiểu là icon CỦA STATUS
      (`.kpi-flag`), mũi tên delta giữ màu theo dấu của số.
      Dải màu `::before` phải ghi đè riêng: nó vẽ ĐÈ lên `border-left`, thiếu bước này thì viền
      cảnh báo vô hình.
- [x] 4.3 Áp dụng hierarchy typography của workbook: value chính 24px, label tối thiểu 12px và tooltip 12px
      → Đo trên Chrome ở bề rộng 1536px: value **25,34px** · label **12px** · tooltip **12px**.
      Sàn của `clamp` nâng 21px → 24px và **giữ trần 30px**, để màn rộng không bị thu nhỏ lại.
      `min-height` của nhãn nâng 44px → 50px: 12px × 1,35 × 3 dòng ≈ 49px, sàn cũ tính cho chữ
      11px nên nhãn dài nhất sẽ vượt sàn và đẩy lệch hàng giá trị của 8 thẻ.
- [x] 4.4 Tạo override dark/light theme để màu Excel vẫn đọc được và luôn kèm tín hiệu không dựa riêng vào màu
      → Ba màu Excel là RGB thuần, trên nền trắng thì `#ffff00` gần như vô hình và `#00ff00`
      tương phản rất thấp. `.delta-line` đã có override từ trước; **viền mức độ của thẻ thì
      chưa** — nên thẻ đang CẢNH BÁO trông y hệt thẻ thường khi bật theme sáng. Đã thêm cho cả
      `.kpi-*` lẫn `.insight-*` (thẻ tab Chi phí, cùng lỗi, cũng chưa từng có).
      Giữ đúng nghĩa màu, chỉ hạ độ sáng: vàng → `#a16207`, đỏ → `#b91c1c`, xanh → `#15803d`.
      Tín hiệu không dựa vào màu: nhãn `.kpi-flag` mang CHỮ (`CẦN THEO DÕI` / `CẢNH BÁO`) và
      icon. **Icon đã phải sửa sau khi nhìn màn hình thật**: bản đầu dùng `▲` cho mức cảnh báo,
      hiện ra ngay dưới `▼ 13% KT` — hai tam giác ngược chiều, hai nghĩa khác hẳn. Đổi sang
      `⚠` và `■` vì chúng không chỉ hướng.
      Đã xem cả hai theme trên Chrome thật.

## 5. Verification

- [x] 5.1 Kiểm tra các trường hợp tăng, giảm, bằng nhau, zero, thiếu dữ liệu và thiếu kỳ so sánh cho từng nhóm semantics
      → `scratchpad/soat_the_kpi.js`, **63 phép kiểm · 63 đạt · 0 hỏng**. Phép kiểm CẮT hàm
      thẳng từ `app.js` chứ không chép lại, nên không bao giờ kiểm nhầm một bản sao đã cũ.
      Vòng đầu 1 phép hỏng, và phân loại ra **lỗi của phép kiểm**: nó quét cả chuỗi HTML kể cả
      tooltip, mà câu giải thích trong tooltip có ký tự `%`. Đã **siết lại chứ không nới**: chỉ
      đọc phần người dùng thấy, và cấm đúng thứ cần cấm là một CHỮ SỐ đi trước dấu `%`.
      Phép kiểm siết lại đó lộ ra **một lỗi thật**: nhánh `b.v === 0` viết thẳng chuỗi `"0"`
      thay vì qua `fmtFn`, nên thẻ Tỷ lệ lỗi hiện `KT · 0` trong khi mọi nhánh khác của chính
      thẻ đó hiện `KT · 2,5%`. Thẻ tiền thì mất chữ `đ`. Đã sửa.
- [x] 5.2 Kiểm tra bộ lọc toàn cục cập nhật đồng bộ value, comparison, driver và status của mọi card
      → Đo trên Chrome: lọc theo agent `Sale Agent` → **8/8 thẻ đổi, 0 thẻ đứng yên**. Ví dụ
      thẻ token: `120,6 triệu / ▼ 46% KT 222,8 triệu / Trợ Lý Ảo Hợp Đồng chiếm 11% token` →
      `35,8 triệu / ▼ 59% KT 86,4 triệu / Sale Agent chiếm 100% token`. Cả ba phần đổi cùng
      nhau, không phần nào kẹt lại giá trị cũ.
- [ ] 5.3 Kiểm tra trực quan ~~chín~~ **tám** card ở dark/light theme và các kích thước màn hình hiện được hỗ trợ
      → **Xong một nửa, ghi rõ nửa nào.** Hai theme đã xem trên Chrome thật và đạt — chính lần
      xem đó bắt được hai lỗi tooltip (ô 3.3) và lỗi icon (ô 4.4) mà 63 phép kiểm tự động không
      bắt được.
      **Chưa làm:** các kích thước màn hình. Mới đo đúng một bề rộng 1536px (8 cột). Lưới có
      `@media` ở `dashboard.css` nhưng chưa xem thật ở bề rộng hẹp, mà đây lại là chỗ dễ vỡ
      nhất sau khi nâng cỡ chữ nhãn 11px → 12px và sàn giá trị 21px → 24px.
- [x] 5.4 Xác nhận không còn delta giả, không hiển thị latency thiếu dữ liệu thành `0.0 s`, và mọi insight truy ngược được về dữ liệu
      → Delta giả: `mockFactor` đã chết từ 08/09; nay `deltaBaseline` cũng không dựng nổi một
      kỳ nền không có thật vì `has` chỉ bật khi số là thật và hữu hạn.
      Latency: `A.latAvailable` đã có sẵn, không in `0.0 s`.
      **Thêm một chỗ CÙNG LOẠI LỖI mà ô này chưa nêu**: thẻ Tỷ lệ lỗi in thẳng `A.er`, mà
      `aggregate()` trả `er = 0` khi không dòng nào biết mã trả về — một kỳ KHÔNG ĐO ĐƯỢC trông
      thành một kỳ hoàn hảo `0,0`. Bảng Hiệu năng đã chặn bằng `A.codeAvailable` từ trước, thẻ
      này thì chưa. Nay dùng chung cái cổng đó.
      Truy ngược: mỗi thẻ có công thức trên mặt thẻ, và tooltip nêu từng giá trị thành phần
      cộng tên kỳ so sánh.
