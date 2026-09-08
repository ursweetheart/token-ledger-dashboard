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

## 1. Insight Data Model

- [ ] 1.1 Tạo cấu trúc view-model chung cho value, unit, comparison, direction, semantic status, driver, freshness và definition
- [ ] 1.2 Định nghĩa ma trận semantics và threshold cấu hình được cho chín KPI card Tổng quan
- [ ] 1.3 Thay logic baseline mock bằng trạng thái thiếu dữ liệu kỳ trước/cùng kỳ có thể phân biệt với giá trị zero

## 2. Metric Accuracy

- [ ] 2.1 Đồng bộ công thức và định nghĩa tổng token, bảo đảm cached/thinking token không bị bỏ sót hoặc cộng trùng
- [ ] 2.2 Xác minh ý nghĩa trường latency và ngừng hiển thị p95 khi nguồn không hỗ trợ p95 tổng hợp chính xác
- [ ] 2.3 Tính contributor hiện tại hoặc contributor tạo biến động lớn nhất theo agent/model/phòng ban khi có đủ dữ liệu

## 3. Card Rendering

- [ ] 3.1 Tạo renderer chung cho giá trị, delta, trạng thái unavailable, driver và metadata nguồn/độ mới
- [ ] 3.2 Chuyển chín KPI card Tổng quan sang renderer mới và giới hạn mỗi card ở một comparison cùng một driver
- [ ] 3.3 Bổ sung tooltip 12px giải thích công thức, giá trị thành phần và kỳ so sánh

## 4. Excel Semantic Styling

- [x] 4.1 Thêm semantic color tokens tăng `#00ff00`, giảm `#ff0000`, warning `#ffff00` và neutral tham chiếu `#1c4b73`
- [ ] 4.2 Áp dụng đồng bộ status class cho value, icon/mũi tên, dòng insight và viền/tint của card
- [ ] 4.3 Áp dụng hierarchy typography của workbook: value chính 24px, label tối thiểu 12px và tooltip 12px
- [ ] 4.4 Tạo override dark/light theme để màu Excel vẫn đọc được và luôn kèm tín hiệu không dựa riêng vào màu

## 5. Verification

- [ ] 5.1 Kiểm tra các trường hợp tăng, giảm, bằng nhau, zero, thiếu dữ liệu và thiếu kỳ so sánh cho từng nhóm semantics
- [ ] 5.2 Kiểm tra bộ lọc toàn cục cập nhật đồng bộ value, comparison, driver và status của mọi card
- [ ] 5.3 Kiểm tra trực quan chín card ở dark/light theme và các kích thước màn hình hiện được hỗ trợ
- [ ] 5.4 Xác nhận không còn delta giả, không hiển thị latency thiếu dữ liệu thành `0.0 s`, và mọi insight truy ngược được về dữ liệu
