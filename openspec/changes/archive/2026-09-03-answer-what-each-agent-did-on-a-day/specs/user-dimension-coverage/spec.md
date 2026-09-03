## ADDED Requirements

### Requirement: Mọi agent phải có mặt trong chiều người dùng
Hệ thống SHALL cung cấp số liệu sử dụng quy về tài khoản cho **mọi** agent có lưu lượng, không
riêng những agent mà nguồn dữ liệu ghi được danh tính từng người. Agent chạy bằng một tài khoản
dịch vụ SHALL xuất hiện với đúng một tài khoản, và MUST NOT bị loại khỏi chiều này chỉ vì tài
khoản đó không phải một con người.

#### Scenario: Agent chạy bằng một tài khoản dịch vụ
- **WHEN** một agent chạy toàn bộ lưu lượng qua một tài khoản dịch vụ
- **THEN** agent đó SHALL có mặt trong chiều người dùng với đúng một tài khoản
- **AND** toàn bộ lưu lượng của nó SHALL quy về tài khoản ấy

#### Scenario: Agent có nhiều người dùng thật
- **WHEN** một agent được nhiều người dùng thật sử dụng
- **THEN** lưu lượng SHALL chia tới từng tài khoản người dùng, không gộp về mức agent

#### Scenario: Nguồn không ghi danh tính người gọi
- **WHEN** số liệu của một agent đến từ nguồn chỉ báo ở mức project
- **THEN** agent đó SHALL vẫn có mặt trong chiều người dùng
- **AND** lưu lượng ấy SHALL quy về tài khoản đại diện tương ứng, thay vì bị loại bỏ

### Requirement: Chiều người dùng MUST NOT đếm một lưu lượng nhiều lần
Khi nhiều nguồn cùng ghi lại một lưu lượng, chiều người dùng SHALL chỉ tính lưu lượng ấy một
lần, theo đúng nguồn mà hệ thống đã chọn cho từng chỉ tiêu. Hệ thống MUST NOT cộng số liệu của
nhiều nguồn cho cùng một khoá.

#### Scenario: Một lưu lượng được nhiều nguồn ghi lại
- **WHEN** hai nguồn trở lên cùng có số liệu cho cùng một ngày, agent và model
- **THEN** chiều người dùng SHALL lấy số của đúng nguồn đã được chọn cho chỉ tiêu đó
- **AND** tổng của chiều người dùng SHALL bằng đúng tổng đã chọn ở mức không có tài khoản

#### Scenario: Chỉ tiêu khác nhau được chọn từ nguồn khác nhau
- **WHEN** hệ thống chọn nguồn A cho số token và nguồn B cho số lượt gọi của cùng một khoá
- **THEN** chiều người dùng SHALL lấy token từ nguồn A và lượt gọi từ nguồn B
- **AND** MUST NOT bỏ số liệu của một chỉ tiêu chỉ vì nó đến từ nguồn khác

#### Scenario: Một khoá chỉ có lượt gọi mà không có token
- **WHEN** một khoá có số lượt gọi nhưng không nguồn nào cho số token
- **THEN** khoá đó SHALL vẫn xuất hiện trong chiều người dùng với số lượt gọi của nó

#### Scenario: Nghiệm thu tổng của chiều người dùng
- **WHEN** nghiệm thu chiều người dùng
- **THEN** phép kiểm SHALL đối chiếu **cả** tổng token **và** tổng lượt gọi
- **AND** MUST NOT kết luận đạt khi mới đối chiếu một trong hai

### Requirement: Phần không quy được về tài khoản phải nhìn thấy được
Hệ thống SHALL giữ và hiện ra phần lưu lượng không quy được về bất kỳ tài khoản nào. Hệ thống
MUST NOT lọc phần đó khỏi chiều người dùng để độ phủ trông cao hơn thực tế.

#### Scenario: Lưu lượng không kèm danh tính người gọi
- **WHEN** một bản ghi có lượt gọi nhưng không kèm danh tính
- **THEN** lưu lượng đó SHALL xuất hiện dưới một mục nói rõ là chưa quy được
- **AND** MUST NOT bị loại khỏi kết quả

#### Scenario: Nguồn chỉ báo ở mức toàn agent
- **WHEN** nguồn chỉ báo được ở mức toàn agent cho một agent có nhiều người dùng thật
- **THEN** phần đó SHALL phân biệt được với phần đã quy về từng người

#### Scenario: Đối chiếu độ phủ với chỉ tiêu đang có
- **WHEN** chiều người dùng được thay đổi
- **THEN** các chỉ tiêu độ phủ đang công bố SHALL giữ nguyên giá trị
- **AND** lệch giá trị SHALL bị coi là lỗi, không phải là kết quả mới
