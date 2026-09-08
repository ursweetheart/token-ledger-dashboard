## MODIFIED Requirements

### Requirement: Lượt gọi hỏng MUST NOT lọt vào số liệu sử dụng
Mọi phép tổng hợp lưu lượng và chi phí SHALL lọc theo kết cục của lượt gọi. Lượt hỏng MUST NOT
đóng góp token hay tiền vào bảng tổng hợp theo ngày, dù nó có mặt trong bảng lượt gọi.

Việc loại ra này tạo ra một khoản **thiếu hụt đã biết**, và khoản đó MUST NOT được ngầm hiểu
bằng không. Đo được ngày 04/09/2026 trên dữ liệu 31/08/2026: nhà cung cấp phục vụ 41 request
với `response_code = 200` cho **tất cả**, trong khi sổ Gateway ghi 5 lượt hỏng — hai trong số
đó đã được phục vụ xong và đã tiêu token thật. Sổ ghi chúng bằng 0. Chênh lệch **12,21%**
token của ngày đó nằm ở chỗ này; phần còn lại của khoảng cách 12,29% giữa sổ nhà cung cấp và
`fact_call` là 39 token do bộ nạp đánh rơi — một nguyên nhân khác.

Hệ thống SHALL đo khoản thiếu hụt bằng cách so với sổ của nhà cung cấp ở mức tổng theo ngày.
Nó MUST NOT suy đoán token cho từng lượt hỏng.

#### Scenario: Tổng hợp theo ngày
- **WHEN** bảng tổng hợp theo ngày được dựng lại từ bảng lượt gọi
- **THEN** chỉ lượt thành công SHALL đóng góp số token và số tiền

#### Scenario: Lượt hỏng vẫn mang token
- **WHEN** một lượt hỏng vẫn tiêu tốn token trước khi hỏng
- **THEN** số token đó MUST NOT được cộng vào lưu lượng, nhưng SHALL còn tra cứu được trong
  bảng lượt gọi

#### Scenario: Sổ ghi lượt hỏng bằng không dù nhà cung cấp đã phục vụ xong
- **WHEN** nhà cung cấp trả về thành công và đã tính token, nhưng proxy hỏng sau đó nên sổ ghi
  lượt ấy là hỏng với 0 token
- **THEN** phần token đó SHALL lộ ra khi đối chiếu với sổ nhà cung cấp theo ngày, và MUST NOT
  được coi là bằng không chỉ vì sổ Gateway ghi như vậy

#### Scenario: Không được lấp khoảng thiếu bằng số suy ra
- **WHEN** đã biết tổng chênh lệch của một ngày
- **THEN** hệ thống MUST NOT phân bổ con số đó về từng lượt hỏng
