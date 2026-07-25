## Context

Tab Tổng quan hiện có chín KPI card. Card chứa giá trị, câu hỏi, công thức, nguồn dữ liệu và một số delta, nhưng chưa có một mô hình trạng thái chung. Hàm so sánh hiện tạo baseline ước lượng khi không có dữ liệu lịch sử; màu của card/value/delta chưa được dẫn xuất thống nhất từ ý nghĩa của từng KPI.

Workbook chuẩn hóa quy định scorecard chính dùng tiêu đề 15px, giá trị 24px; scorecard phụ dùng tiêu đề 12px, giá trị 15px; tăng tích cực dùng xanh, giảm tiêu cực dùng đỏ và cảnh báo dùng vàng/cam. Dashboard phải áp dụng quy chuẩn này trong cả dark và light theme.

## Goals / Non-Goals

**Goals:**

- Tạo một mô hình insight dùng chung cho mọi KPI card.
- Tách hướng biến động khỏi đánh giá tốt/xấu.
- Dùng màu chuẩn Excel một cách nhất quán và có khả năng đọc.
- Chỉ hiển thị so sánh, nguyên nhân và forecast khi có dữ liệu kiểm chứng.
- Giữ card gọn, nhưng cung cấp chi tiết qua dòng insight và tooltip.

**Non-Goals:**

- Không tích hợp Google AI Studio, Cloud Monitoring hoặc BigQuery thật.
- Không thay đổi cơ chế nhập dữ liệu và localStorage.
- Không sửa các biểu đồ hoặc bảng ngoài phạm vi cần thiết để hỗ trợ KPI card.
- Không tự phát minh SLO, ngân sách hoặc baseline khi cấu hình chưa tồn tại.

## Decisions

### 1. Dùng mô hình view-model cho insight

Mỗi card được render từ một cấu trúc gồm `value`, `unit`, `comparison`, `status`, `driver`, `freshness` và `definition`. Logic tính toán trả về dữ liệu có cấu trúc; DOM renderer chỉ định dạng nội dung và class.

Cách này được chọn thay cho việc nối HTML riêng trong từng hàm vì giúp kiểm thử phép tính và màu độc lập.

### 2. Màu delta đi theo direction

`direction` nhận `up`, `down`, `flat` hoặc `unknown`. `status` nhận `positive`, `negative`, `warning`, `neutral` hoặc `unavailable`.

Màu của dòng delta được lấy trực tiếp từ direction: `up` dùng xanh, `down` dùng đỏ và `flat` dùng trung tính. Status tốt/xấu có thể được diễn giải bằng câu chữ hoặc trạng thái tổng thể của card, nhưng không được đảo màu mũi tên delta.

### 3. Ánh xạ màu theo workbook

Các semantic token cốt lõi:

- Increase/up: `#00ff00`
- Decrease/down: `#ff0000`
- Warning: `#ffff00`
- Neutral: màu chữ/viền trung tính của theme; tham chiếu màu nội dung `#1c4b73`
- Actual/primary series khi không mang trạng thái: `#2cc01f` hoặc màu accent hiện hành của dashboard

Do ba màu Excel có độ chói cao trên nền tối/sáng, giá trị chính dùng màu chuẩn; nền tint và viền dùng cùng màu với alpha để duy trì tương phản. Không dùng màu làm tín hiệu duy nhất: luôn có mũi tên, nhãn hoặc icon trạng thái.

### 4. Ma trận ý nghĩa KPI

- Agent hoạt động, tổng người dùng: mặc định neutral; chỉ cảnh báo khi có target hoặc tỷ lệ idle được cấu hình.
- Mọi KPI: delta tăng dùng xanh và delta giảm dùng đỏ, không phụ thuộc KPI tăng là tốt hay xấu.
- Token, cache hit, adoption, chi phí, lỗi và latency vẫn có thể có trạng thái cảnh báo riêng ở cấp card dựa trên threshold, nhưng trạng thái đó không đổi màu của delta.

### 5. Không fallback sang baseline giả

Khi phạm vi so sánh không có dữ liệu, renderer hiển thị “Chưa đủ dữ liệu kỳ trước/cùng kỳ” với trạng thái unavailable. Không tính phần trăm và không dùng ký hiệu xấp xỉ để thay thế dữ liệu.

### 6. Insight nguyên nhân chỉ xuất hiện khi xác định được contributor

Driver được tìm bằng cách nhóm metric theo agent/model/phòng ban và chọn phần đóng góp lớn nhất vào giá trị hoặc biến động. Nếu không đủ dữ liệu theo hai kỳ, card chỉ nêu contributor lớn nhất của kỳ hiện tại và dùng câu chữ đúng bản chất.

### 7. Quy tắc typography

Card chính trên Tổng quan dùng giá trị 24px và label tối thiểu 12px để phù hợp workbook trong khi vẫn tương thích layout hiện tại. Dòng so sánh/insight không nhỏ hơn 11px; tooltip dùng 12px, nhãn thường và giá trị bold.

## Risks / Trade-offs

- [Màu Excel quá chói hoặc tương phản kém trên light theme] → Chỉ dùng màu nguyên bản cho text/icon quan trọng; dùng tint alpha cho nền/viền và kiểm tra tương phản ở cả hai theme.
- [Không có dữ liệu lịch sử khiến card ít insight] → Hiển thị contributor hiện tại và thông báo rõ dữ liệu còn thiếu, không tạo số giả.
- [Ngưỡng nghiệp vụ chưa được xác nhận] → Tách threshold thành cấu hình; trạng thái giữ neutral khi chưa cấu hình.
- [Không thể tổng hợp p95 chính xác từ các percentile con] → Không đổi nhãn thành p95 tổng hợp nếu nguồn chỉ có trung bình; task triển khai phải xác minh schema latency trước khi render.
- [Card dài và gây quá tải] → Giới hạn phần hiển thị thường trực ở một comparison và một driver; thông tin còn lại nằm trong tooltip.

## Migration Plan

1. Thêm semantic tokens và style card mới nhưng giữ class cũ làm fallback.
2. Thêm view-model/renderer và chuyển lần lượt từng KPI card.
3. Loại bỏ baseline mock sau khi toàn bộ card đã dùng trạng thái unavailable.
4. Kiểm tra với dữ liệu hiện có, dữ liệu rỗng, thiếu kỳ so sánh và cả hai theme.
5. Có thể rollback bằng cách trả các card về renderer/class cũ; không cần migration localStorage.

## Open Questions

- Ngưỡng chính thức cho cache hit, adoption, error rate và latency là bao nhiêu?
- Ngân sách áp dụng toàn công ty hay cần theo phòng ban/agent?
- Dữ liệu latency hiện nhập là p95 đã tổng hợp hay độ trễ trung bình?
