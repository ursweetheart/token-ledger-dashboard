## ADDED Requirements

### Requirement: Cảnh báo ở ba bậc, mỗi lần đổi bậc gửi đúng một thư

Hệ thống SHALL theo dõi tỉ lệ *đã tiêu / hạn mức* của từng project và gửi email khi tỉ lệ đó bước
sang một bậc mới trong ba bậc: **90%**, **100%**, **đã vượt**. Mỗi lần đổi bậc SHALL gửi đúng một
thư. Khi bậc không đổi, hệ thống MUST NOT gửi thư nào.

#### Scenario: Vượt mốc 90% lần đầu
- **WHEN** tỉ lệ của một project đi từ dưới 90% lên trên 90%
- **THEN** SHALL gửi đúng một thư báo bậc 90%

#### Scenario: Ở yên trong một bậc
- **WHEN** tỉ lệ tăng từ 91% lên 95% mà chưa qua bậc kế tiếp
- **THEN** MUST NOT gửi thêm thư nào

#### Scenario: Nhảy qua nhiều bậc trong một nhịp kiểm
- **WHEN** giữa hai nhịp kiểm, tỉ lệ đi thẳng từ 40% lên 105%
- **THEN** SHALL gửi thư cho bậc cao nhất đã đạt
- **AND** MUST NOT im lặng chỉ vì các bậc trung gian bị nhảy qua

#### Scenario: Nạp thêm làm tỉ lệ tụt xuống
- **WHEN** hạn mức được nâng và tỉ lệ rơi về dưới 90%
- **THEN** bậc SHALL được đặt lại
- **AND** lần vượt 90% sau đó SHALL lại gửi thư

#### Scenario: Khởi động lại tiến trình cảnh báo
- **WHEN** tiến trình cảnh báo dừng rồi chạy lại trong khi một project đang ở bậc 100%
- **THEN** MUST NOT gửi lại thư của bậc đó

### Requirement: Thư phải đủ để người nhận biết làm gì tiếp

Mỗi thư SHALL nêu: tên agent và project, hạn mức, số đã tiêu, tỉ lệ, bậc vừa chạm, và việc cần làm
tiếp. Với project mà hạn mức không chặn được lưu lượng, thư SHALL nói rõ đây là cảnh báo suông.

Thư MUST NOT chứa nội dung câu hỏi hay câu trả lời của người dùng.

#### Scenario: Thư báo đã vượt
- **WHEN** một project vượt hạn mức
- **THEN** thư SHALL nêu rằng lưu lượng của project đó đang bị chặn
- **AND** SHALL nêu cách mở lại: nạp thêm hạn mức ở tab Setting

#### Scenario: Thư cho project không chặn được
- **WHEN** project đó chưa nối vào Gateway
- **THEN** thư SHALL nói rõ lưu lượng vẫn đang đi và không có gì chặn nó

#### Scenario: Gọi tên agent
- **WHEN** thư nhắc tới một agent
- **THEN** SHALL gọi bằng tên hiển thị của agent
- **AND** MUST NOT chỉ ghi mã số

### Requirement: Đường gửi thư hỏng thì việc chặn vẫn phải chạy

Việc thi hành hạn mức SHALL độc lập với việc gửi thư. Khi máy chủ thư không gọi được, hoặc cấu hình
thư thiếu, hệ thống SHALL vẫn chặn đúng như khi thư gửi được, và SHALL ghi lại việc thư không gửi
được.

Lý do: cảnh báo là thứ giúp người biết; chặn là thứ giữ tiền. Buộc hai thứ vào nhau thì một máy chủ
thư hỏng sẽ lặng lẽ mở cửa cho chi tiêu.

#### Scenario: Máy chủ thư không gọi được
- **WHEN** không kết nối được máy chủ thư lúc cần gửi cảnh báo
- **THEN** hệ thống SHALL ghi lại lỗi đó
- **AND** việc chặn theo hạn mức SHALL vẫn hoạt động bình thường

#### Scenario: Thiếu cấu hình thư
- **WHEN** địa chỉ nhận hoặc máy chủ thư chưa được cấu hình
- **THEN** hệ thống SHALL nói rõ là chưa cấu hình
- **AND** MUST NOT coi đó là "đã gửi thành công"

#### Scenario: Ghi lỗi gửi thư
- **WHEN** ghi lại một lỗi gửi thư
- **THEN** dòng ghi MUST NOT chứa mật khẩu hay tên đăng nhập của máy chủ thư
