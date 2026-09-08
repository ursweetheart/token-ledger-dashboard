## Why

Dashboard hiện chủ yếu hiển thị số liệu và so sánh, nhưng chưa chủ động giải thích khi token/chi phí vượt ngưỡng, nguyên nhân đến từ đâu và người quản trị nên làm gì. Đồng thời cách hiển thị `$`, `M`, `K` chưa phù hợp với người dùng Việt Nam và gây khó đọc khi báo cáo nội bộ.

## What Changes

- Bổ sung insight theo cấu trúc: biến động hiện tại, trạng thái so với ngưỡng, contributor chính và khuyến nghị hành động.
- Phát hiện token tăng bất thường, token/request tăng, tốc độ chi phí vượt tiến độ ngân sách, forecast vượt ngân sách, chi phí tập trung, lỗi/latency vượt ngưỡng và agent không hoạt động.
- Giữ màu delta theo quy ước đã chốt: tăng màu xanh, giảm màu đỏ; cảnh báo ngưỡng hiển thị riêng bằng badge/viền vàng hoặc đỏ.
- Chuyển giá trị tiền hiển thị chính từ USD sang VNĐ, dùng ký hiệu `₫`, dấu phân cách và locale `vi-VN`.
- Giữ giá trị USD gốc ở tooltip hoặc dòng phụ để truy vết phép quy đổi.
- Thay hậu tố token quốc tế bằng đơn vị tiếng Việt: `nghìn`, `triệu`, `tỷ`; tooltip/bảng chi tiết vẫn có thể hiển thị số nguyên đầy đủ.
- Hiển thị tỷ giá đang áp dụng và phân biệt tỷ giá cấu hình với dữ liệu tỷ giá realtime.
- Không tạo insight, forecast hoặc baseline giả khi dữ liệu đầu vào không đủ.
- Loại các KPI card `Tỉ lệ cache hit` khỏi dashboard; dữ liệu cache thô vẫn có thể giữ trong cấu trúc token để đối soát kỹ thuật.

## Capabilities

### New Capabilities

- `actionable-token-insights`: Phát hiện cảnh báo, giải thích contributor và tạo khuyến nghị có thể truy vết cho các KPI token, chi phí, adoption và vận hành.
- `vietnamese-metric-formatting`: Chuẩn hóa cách hiển thị tiền VNĐ, giá trị USD tham chiếu và đơn vị token nghìn/triệu/tỷ trên toàn dashboard.

### Modified Capabilities

Không có baseline spec đã archive cần sửa đổi.

## Impact

- Logic tổng hợp, threshold, forecast, contributor và định dạng số trong `app.js`.
- Nội dung KPI card, tooltip và metadata tỷ giá trong `index.html`.
- Style badge cảnh báo, insight hành động và trạng thái card trong `dashboard.css`.
- Các card, biểu đồ, bảng và tooltip đang gọi hàm `money`, `vnd` hoặc `fmtTok`.
- Không thêm dependency hay API tỷ giá; tỷ giá mặc định tiếp tục là cấu hình cục bộ cho đến khi có nguồn dữ liệu chính thức.
