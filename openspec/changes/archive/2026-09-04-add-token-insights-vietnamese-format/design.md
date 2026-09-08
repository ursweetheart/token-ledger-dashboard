## Context

Dashboard hiện tính chi phí từ bảng giá USD/1M token, dùng `VND_RATE = 25200`, nhưng giá trị chính vẫn gọi `money()` và hiển thị USD. Token được rút gọn bằng hậu tố `k` và `M`. Card có delta nhưng chưa có engine đánh giá ngưỡng, contributor và khuyến nghị theo mẫu người dùng cung cấp.

Change `standardize-kpi-card-insights` đang xử lý cấu trúc/màu card. Change này bổ sung lớp insight có hành động và chuẩn hiển thị Việt Nam, đồng thời giữ nguyên nguyên tắc `▲ tăng = xanh`, `▼ giảm = đỏ`; badge/viền cảnh báo là tín hiệu độc lập.

## Goals / Non-Goals

**Goals:**

- Tạo insight có bằng chứng theo chuỗi “điều gì xảy ra → nguyên nhân → hành động”.
- Cảnh báo token, chi phí và vận hành theo threshold cấu hình được.
- Hiển thị VNĐ làm tiền tệ chính nhưng vẫn truy vết được USD và tỷ giá.
- Hiển thị token bằng nghìn/triệu/tỷ theo locale Việt Nam.
- Áp dụng formatter thống nhất cho card, chart, bảng, tooltip và delta.

**Non-Goals:**

- Không lấy tỷ giá realtime từ internet.
- Không tự đặt SLO hoặc ngân sách theo phòng ban nếu chưa có cấu hình.
- Không dùng mô hình AI để tạo câu insight; insight phải deterministic và truy vết được.
- Không thay đổi đơn vị lưu trữ gốc: token vẫn là số nguyên và chi phí vẫn tính bằng USD.
- Không duy trì cache hit như KPI card; chỉ giữ dữ liệu cache thô trong cấu trúc token khi cần đối soát kỹ thuật.

## Decisions

### 1. Giữ đơn vị tính gốc, chỉ Việt hóa presentation

Tất cả phép tính chi phí tiếp tục dùng USD để khớp bảng giá model. Formatter chuyển sang VNĐ ở bước render bằng `VND_RATE`; điều này tránh sai số tích lũy và không cần migration localStorage.

Giá trị chính dùng `Intl.NumberFormat("vi-VN", {style:"currency", currency:"VND", maximumFractionDigits:0})`. USD xuất hiện trong tooltip hoặc dòng tham chiếu, ví dụ `≈ 46,85 USD · tỷ giá 25.200`.

### 2. Token dùng thang đơn vị Việt Nam

- `< 1.000`: số đầy đủ
- `1.000–999.999`: `nghìn token`
- `1.000.000–999.999.999`: `triệu token`
- `≥ 1.000.000.000`: `tỷ token`

Card dùng tối đa một chữ số thập phân và dấu phẩy thập phân; bảng/tooltip có thể hiển thị số nguyên với dấu chấm phân nhóm. Ví dụ `69.100.000` thành `69,1 triệu token`.

### 3. Insight được tạo từ rule và evidence

Mỗi rule trả về `severity`, `headline`, `evidence`, `driver`, `recommendation` và `ruleId`. Renderer chỉ hiển thị insight nếu evidence hợp lệ. Mỗi con số trong câu insight phải truy ngược được về aggregate hoặc cấu hình.

### 4. Cảnh báo độc lập với màu delta

Delta tiếp tục dùng xanh khi tăng và đỏ khi giảm. Cảnh báo sử dụng badge/viền:

- `normal`: trung tính hoặc xanh trạng thái
- `warning`: vàng `#ffff00`
- `critical`: đỏ `#ff0000`
- `unavailable`: xám

Ví dụ chi phí tăng vẫn có delta xanh, nhưng card có badge vàng “SÁT TRẦN” nếu forecast gần ngân sách.

### 5. Bộ rule phiên bản đầu

- Token anomaly: cảnh báo khi token tăng vượt threshold và không được giải thích tương ứng bởi request.
- Token/request anomaly: cảnh báo theo mức tăng so kỳ trước.
- Budget pace: so `% ngân sách đã dùng` với `% thời gian đã qua`.
- Budget forecast: cảnh báo khi forecast vượt ngưỡng ngân sách.
- Concentration: cảnh báo khi một agent/phòng ban/model chiếm tỷ trọng vượt threshold.
- Reliability: error rate và latency chỉ cảnh báo khi threshold/SLO tương ứng được cấu hình.
- Inactivity/adoption: cảnh báo agent không hoạt động trong số ngày cấu hình hoặc adoption dưới threshold.

Threshold mặc định là cấu hình tập trung, không nằm rải rác trong hàm render. Nếu không có baseline, budget hoặc SLO thì rule trả `unavailable` thay vì suy đoán.

### 6. Ưu tiên insight trên card

Mỗi card hiển thị tối đa:

1. Một badge severity.
2. Hai dòng delta có dữ liệu thật.
3. Một câu evidence/forecast.
4. Một khuyến nghị hành động.

Nếu nhiều rule cùng kích hoạt, chọn severity cao nhất rồi mức vượt ngưỡng lớn nhất; các rule còn lại có thể nằm trong tooltip.

## Risks / Trade-offs

- [Tỷ giá cấu hình nhanh lỗi thời] → Luôn hiển thị tỷ giá và nhãn “tỷ giá cấu hình”; không gọi là realtime.
- [Quy đổi làm người dùng khó đối soát hóa đơn USD] → Giữ USD gốc trong tooltip/dòng phụ và không đổi phép tính gốc.
- [Threshold chung không phù hợp mọi agent] → Cho phép override theo loại agent; không đánh giá latency nếu thiếu SLO.
- [Insight cảnh báo quá nhiều] → Giới hạn một insight chính/card và ưu tiên theo severity.
- [Token tăng do request tăng hợp lý] → Rule token anomaly phải xét đồng thời request và token/request.
- [Formatter làm chart label dài] → Chart trục dùng dạng rút gọn; tooltip dùng số đầy đủ.

## Migration Plan

1. Thêm formatter VNĐ/token mới song song với formatter cũ.
2. Chuyển card Tổng quan và tab Chi phí trước, sau đó chart/bảng/tooltip.
3. Thêm cấu hình threshold và engine rule, bật từng rule với dữ liệu có thể kiểm chứng.
4. Kiểm tra số liệu trước/sau quy đổi bằng cùng giá trị USD gốc.
5. Có thể rollback renderer/formatter mà không đổi dữ liệu localStorage.

## Open Questions

- `VND_RATE = 25.200` có phải tỷ giá nội bộ chính thức hay cần cho phép nhập trong panel cấu hình?
- Ngân sách hiện tại `30 USD/tháng` là dữ liệu demo hay ngân sách thật?
- Có SLO latency riêng theo loại agent hay chỉ một ngưỡng toàn hệ thống?
