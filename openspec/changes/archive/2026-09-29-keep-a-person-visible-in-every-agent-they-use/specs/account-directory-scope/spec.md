## ADDED Requirements

### Requirement: Danh bạ phải cho thấy mọi agent mà một người có mặt

Một người có thể có mặt trong danh bạ của nhiều agent. Danh bạ SHALL cho thấy **đủ** các agent ấy.
Nó MUST NOT rút gọn xuống một agent duy nhất.

Hệ thống chọn một agent làm **nguồn cây tổ chức** cho mỗi người, vì một người chỉ mang được một
phòng ban. Giá trị ấy SHALL không được dùng để trả lời câu hỏi *"người này dùng agent nào"*. Hai
câu hỏi khác nhau, và dùng chung một câu trả lời làm danh bạ lọc theo agent thiếu người.

Khi lọc danh bạ theo một agent, kết quả SHALL gồm mọi người có mặt trong danh bạ của agent ấy, kể
cả người mà nguồn cây tổ chức của họ là một agent khác.

Danh bạ SHALL vẫn cho thấy agent nào đang cấp phòng ban cho mỗi người, và SHALL vẫn giữ dấu hiệu
cho biết các nguồn đã không đồng ý về phòng ban. Bỏ hai thứ đó đi thì màn hình hiện một phòng ban
mà không ai nói được nó đến từ đâu.

#### Scenario: Người dùng có mặt ở hai agent
- **WHEN** một người có mặt trong danh bạ của hai agent
- **THEN** danh bạ SHALL cho thấy cả hai agent cho người ấy
- **AND** người ấy SHALL xuất hiện khi lọc theo **mỗi** agent trong hai agent đó

#### Scenario: Lọc danh bạ theo một agent
- **WHEN** người xem lọc danh bạ theo một agent
- **THEN** số người trả về SHALL bằng số người có mặt trong danh bạ của agent ấy
- **AND** MUST NOT thiếu người chỉ vì phòng ban của họ lấy theo cây của agent khác

#### Scenario: Hai nguồn xếp một người vào hai phòng ban khác nhau
- **WHEN** hai agent xếp cùng một người vào hai phòng ban khác nhau
- **THEN** danh bạ SHALL cho thấy phòng ban đã chọn, agent cấp phòng ban ấy, và dấu hiệu có xung đột
- **AND** việc chọn MUST NOT diễn ra mà không để lại dấu vết nào trên màn hình

#### Scenario: Đếm tổng số người dùng
- **WHEN** hệ thống hiển thị tổng số tài khoản người dùng
- **THEN** mỗi con người SHALL được đếm đúng một lần
- **AND** người có mặt ở nhiều agent MUST NOT làm con số ấy tăng lên nhiều lần
