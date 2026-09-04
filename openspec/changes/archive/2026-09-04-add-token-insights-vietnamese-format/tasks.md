## 1. Vietnamese Formatters

- [x] 1.1 Tạo formatter VNĐ theo locale `vi-VN` và formatter USD tham chiếu dùng chung
- [x] 1.2 Tạo formatter token rút gọn `nghìn/triệu/tỷ` và formatter số token đầy đủ
- [x] 1.3 Bổ sung metadata tỷ giá cấu hình và helper quy đổi không làm thay đổi giá trị USD gốc

## 2. Apply Vietnamese Formatting

- [x] 2.0 Loại các KPI card Tỉ lệ cache hit và chỉ giữ dữ liệu cache thô để đối soát kỹ thuật
- [x] 2.1 Chuyển card Tổng quan và tab Chi phí sang VNĐ chính, USD/tỷ giá ở dòng phụ hoặc tooltip
- [x] 2.2 Chuyển chi phí trên các tab Phòng ban, Agent, Provider, Model và User sang formatter VNĐ
- [x] 2.3 Chuyển token trên card, delta, chart label và bảng sang nghìn/triệu/tỷ theo ngữ cảnh
- [x] 2.4 Bảo đảm chart tooltip và bảng chi tiết cung cấp số đầy đủ để đối soát

## 3. Insight Rule Engine

- [x] 3.1 Tạo cấu hình threshold tập trung và cấu trúc kết quả rule gồm severity, evidence, driver, recommendation và ruleId
- [x] 3.2 Tạo rule token anomaly xét đồng thời token, request và token/request
- [x] 3.3 Tạo rule budget pace và forecast cuối kỳ từ ngân sách cùng tiến độ thời gian
- [x] 3.4 Tạo rule concentration theo agent, phòng ban, model và nhóm người dùng
- [x] 3.5 Tạo rule reliability cho error/latency/quota chỉ khi có threshold hoặc SLO hợp lệ
- [x] 3.6 Tạo rule inactivity/adoption theo cửa sổ thời gian và threshold cấu hình

## 4. Insight Card Presentation

- [x] 4.1 Bổ sung renderer badge normal/warning/critical/unavailable độc lập với màu delta
- [x] 4.2 Bổ sung dòng evidence/forecast và khuyến nghị hành động cho KPI card phù hợp
- [x] 4.3 Ưu tiên tối đa một insight chính mỗi card theo severity và mức vượt ngưỡng
- [x] 4.4 Thêm style viền, badge và action text cho dark/light theme theo màu Excel

## 5. Verification

- [x] 5.1 Kiểm tra các mốc token nhỏ hơn nghìn, nghìn, triệu, tỷ và quy tắc làm tròn dấu phẩy Việt Nam
- [x] 5.2 Kiểm tra phép quy đổi `46,85 USD × 25.200 = 1.180.620 ₫` và tính nhất quán giữa card, chart, bảng
- [x] 5.3 Kiểm tra token tăng theo request không cảnh báo sai và token/request tăng bất thường có cảnh báo
- [x] 5.4 Kiểm tra budget thiếu dữ liệu không tạo forecast và budget vượt tiến độ tạo đúng severity/evidence
- [x] 5.5 Kiểm tra mọi insight truy vết được, không dùng baseline/contributor giả và delta vẫn giữ tăng xanh, giảm đỏ
- [x] 5.6 Kiểm tra trực quan card insight trên dark/light theme và màn hình responsive
