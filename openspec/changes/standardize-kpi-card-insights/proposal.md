## Why

Các KPI card hiện đã có giá trị, câu hỏi và một số so sánh, nhưng màu sắc và ý nghĩa tăng/giảm chưa được áp dụng nhất quán theo bảng chuẩn hóa Excel. Một số insight còn được tạo từ baseline giả khi thiếu dữ liệu, khiến người dùng có thể hiểu nhầm trạng thái vận hành và chi phí.

## What Changes

- Chuẩn hóa cấu trúc insight cho các KPI card Tổng quan: giá trị, đơn vị, so sánh, đánh giá trạng thái, nguyên nhân đóng góp chính và độ mới dữ liệu.
- Áp dụng màu delta trực tiếp theo hướng biến động và bảng Excel: tăng dùng xanh, giảm dùng đỏ, không đổi dùng màu trung tính; vàng/cam dành cho cảnh báo ngưỡng ở cấp card.
- Tách màu delta khỏi đánh giá tốt/xấu của KPI để mũi tên và màu luôn nhất quán về mặt trực quan.
- Không tạo số so sánh giả khi thiếu kỳ trước/cùng kỳ; card phải hiển thị trạng thái chưa đủ dữ liệu.
- Bổ sung ngưỡng và nội dung insight có thể kiểm chứng cho token, cache hit, adoption, chi phí, lỗi, độ trễ và chi phí/người dùng.
- Đồng bộ màu giá trị, mũi tên, dòng insight và viền card mà không làm mất khả năng đọc trên giao diện tối/sáng.
- Giữ nguyên mô hình chạy offline, dữ liệu localStorage và Chart.js hiện tại.

## Capabilities

### New Capabilities

- `kpi-card-insights`: Quy định cấu trúc, phép so sánh, trạng thái, nội dung giải thích và fallback dữ liệu cho KPI card.
- `semantic-kpi-colors`: Quy định ánh xạ màu Excel theo ngữ nghĩa KPI, trạng thái và theme.

### Modified Capabilities

Không có capability hiện hữu cần thay đổi; dự án chưa có baseline spec.

## Impact

- Giao diện KPI card và insight trên tab Tổng quan trong `index.html`.
- Logic tổng hợp, so sánh kỳ và tạo nội dung insight trong `app.js`.
- Style card, delta, trạng thái và theme trong `dashboard.css` cùng các override hiện có.
- Không thay đổi API hoặc thêm thư viện; cần hiệu chỉnh cách hiển thị khi dữ liệu lịch sử, ngưỡng hoặc nguồn đo chưa sẵn có.
