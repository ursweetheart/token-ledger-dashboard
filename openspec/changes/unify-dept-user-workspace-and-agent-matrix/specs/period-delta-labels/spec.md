## ADDED Requirements

### Requirement: Every delta names its baseline as KT or CK
Mọi chú thích delta trên scorecard SHALL gọi tên baseline bằng `so với KT` cho kỳ trước hoặc `so với CK` cho cùng kỳ năm trước, và SHALL NOT dùng chú thích chỉ nêu tên kỳ mà không nói rõ loại baseline.

#### Scenario: Card compares against the previous period
- **WHEN** scorecard so sánh với kỳ liền trước
- **THEN** chú thích ghi `so với KT` kèm giá trị nền

#### Scenario: Card compares against the same period last year
- **WHEN** scorecard so sánh với cùng kỳ năm trước
- **THEN** chú thích ghi `so với CK` kèm giá trị nền

#### Scenario: Card compares against both baselines
- **WHEN** scorecard trình bày cả hai baseline
- **THEN** dòng đầu ghi `so với KT` và dòng sau ghi `so với CK`, mỗi dòng có phần trăm và hướng biến động riêng

### Requirement: Abbreviations are explained on screen
UI SHALL hiển thị chú giải cho `KT` và `CK` ở vị trí người xem thấy được cùng lúc với các scorecard.

#### Scenario: Dashboard is loaded
- **WHEN** người dùng mở dashboard
- **THEN** UI hiển thị chú giải `KT = kỳ trước` và `CK = cùng kỳ năm trước`

### Requirement: Concrete comparison window remains traceable
Chú thích delta SHALL cho phép truy vết kỳ so sánh cụ thể mà không làm scorecard dài thêm.

#### Scenario: User inspects a delta
- **WHEN** người dùng đưa con trỏ lên chú thích delta
- **THEN** hệ thống hiển thị tên baseline đầy đủ, kỳ cụ thể và giá trị nền

### Requirement: Missing baseline is stated, never fabricated
Khi không có dữ liệu nền, hệ thống SHALL nêu rõ thiếu dữ liệu và SHALL NOT dựng baseline bằng hệ số hoặc giá trị suy diễn.

#### Scenario: Baseline data is absent
- **WHEN** kỳ so sánh không có dữ liệu
- **THEN** chú thích ghi `so với KT: chưa có dữ liệu` hoặc `so với CK: chưa có dữ liệu` và không hiển thị phần trăm

#### Scenario: Baseline value is zero
- **WHEN** giá trị nền bằng zero
- **THEN** hệ thống không hiển thị phần trăm thay đổi và không chia cho zero
