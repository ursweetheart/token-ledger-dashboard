## ADDED Requirements

### Requirement: Mỗi lượt gọi qua Gateway phải ghi được độ trễ
Bảng lượt gọi SHALL lưu độ trễ của từng lượt gọi qua Gateway, ở dạng số thô chứ không phải số
đã tổng hợp. Nhờ đó phân vị theo ngày tính lại được chính xác, thay vì phải suy từ histogram
đã gộp.

#### Scenario: Lượt gọi tới được nhà cung cấp
- **WHEN** một lượt gọi qua Gateway nhận được phản hồi từ nhà cung cấp
- **THEN** độ trễ của lượt đó SHALL được lưu nguyên giá trị mà Gateway đo được

#### Scenario: Gateway ghi độ trễ bằng không
- **WHEN** Gateway ghi độ trễ của một lượt gọi là không
- **THEN** cột độ trễ SHALL để rỗng, và MUST NOT lưu giá trị không — vì không phải một phép
  đo mà là sự vắng mặt của phép đo
- **AND** điều này SHALL áp dụng bất kể lượt gọi đó đã đi được tới đâu, vì đo được rằng cả
  lượt đã gọi tới nhà cung cấp lẫn lượt bị chặn ngay tại Gateway đều mang giá trị không

#### Scenario: Tính lại phân vị
- **WHEN** cần phân vị độ trễ theo ngày cho lưu lượng Gateway
- **THEN** phân vị SHALL tính được trực tiếp từ các giá trị thô đã lưu, và MUST NOT phải đi
  qua một bước gộp histogram trung gian

### Requirement: Lượt gọi hỏng phải được ghi lại kèm lý do
Bảng lượt gọi SHALL chứa cả lượt thành công lẫn lượt hỏng, kèm mã lỗi khi có. Hệ thống MUST NOT
loại bỏ lượt hỏng khỏi bản ghi, vì khi đó chỉ còn biết là có hỏng mà không biết vì sao.

#### Scenario: Lượt gọi bị từ chối vì khoá
- **WHEN** một lượt gọi hỏng và Gateway ghi lại một mã lỗi
- **THEN** lượt đó SHALL được lưu kèm kết cục và mã lỗi

#### Scenario: Mã lỗi rỗng
- **WHEN** Gateway ghi mã lỗi là một chuỗi rỗng
- **THEN** cột mã lỗi SHALL để rỗng, và MUST NOT lưu chuỗi rỗng như một mã hợp lệ

#### Scenario: Lượt hỏng không quy được về agent
- **WHEN** một lượt hỏng không mang nhãn định danh nào
- **THEN** lượt đó MUST NOT được lưu, và SHALL được đếm vào báo cáo của lần chạy

### Requirement: Lượt gọi hỏng MUST NOT lọt vào số liệu sử dụng
Mọi phép tổng hợp lưu lượng và chi phí SHALL lọc theo kết cục của lượt gọi. Lượt hỏng MUST NOT
đóng góp token hay tiền vào bảng tổng hợp theo ngày, dù nó có mặt trong bảng lượt gọi.

#### Scenario: Tổng hợp theo ngày
- **WHEN** bảng tổng hợp theo ngày được dựng lại từ bảng lượt gọi
- **THEN** chỉ lượt thành công SHALL đóng góp số token và số tiền

#### Scenario: Lượt hỏng vẫn mang token
- **WHEN** một lượt hỏng vẫn tiêu tốn token trước khi hỏng
- **THEN** số token đó MUST NOT được cộng vào lưu lượng, nhưng SHALL còn tra cứu được trong
  bảng lượt gọi

### Requirement: Nguồn không đo được kết cục phải để rỗng
Với nguồn dữ liệu không cung cấp thông tin kết cục, cột kết cục SHALL để rỗng. Hệ thống MUST NOT
mặc định coi chúng là thành công.

#### Scenario: Dữ liệu có từ trước khi thêm cột
- **WHEN** cột kết cục được thêm vào một bảng đã có sẵn dữ liệu từ nguồn không ghi kết cục
- **THEN** các dòng cũ SHALL mang giá trị rỗng, và MUST NOT được gán một kết cục suy đoán
