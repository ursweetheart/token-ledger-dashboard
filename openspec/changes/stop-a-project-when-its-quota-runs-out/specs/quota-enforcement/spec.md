## ADDED Requirements

### Requirement: Vượt hạn mức thì Gateway thôi chuyển request đi

Khi tổng đã tiêu của một project đã bằng hoặc vượt hạn mức đang hiệu lực, Gateway SHALL từ chối
chuyển request tiếp theo của project đó tới nhà cung cấp. Việc từ chối SHALL xảy ra **trước** khi
gọi ra ngoài, để lượt bị chặn không phát sinh chi phí.

Vì chi phí của một request chỉ biết sau khi gọi xong, luật thi hành là *đã tiêu ≥ hạn mức thì chặn
lượt kế tiếp*. Hệ thống SHALL chấp nhận khoản vượt nhỏ của một hai lượt cuối, và MUST NOT chặn sớm
ở một ngưỡng thấp hơn để tránh khoản vượt đó.

#### Scenario: Project còn hạn mức
- **WHEN** tổng đã tiêu của project nhỏ hơn hạn mức
- **THEN** request SHALL đi tới nhà cung cấp như bình thường

#### Scenario: Project vừa chạm hạn mức
- **WHEN** tổng đã tiêu bằng hoặc vượt hạn mức
- **THEN** request kế tiếp SHALL bị chặn
- **AND** MUST NOT có lượt gọi nào tới nhà cung cấp cho request đó

#### Scenario: Project không đặt hạn mức
- **WHEN** project chưa có hạn mức nào
- **THEN** request SHALL đi qua bình thường
- **AND** MUST NOT bị chặn vì lý do hạn mức

#### Scenario: Không đọc được hạn mức hoặc số đã tiêu
- **WHEN** hạn mức hoặc số đã tiêu không đọc được, hoặc có nhưng sai định dạng
- **THEN** Gateway SHALL cho request đi qua
- **AND** SHALL ghi lại sự kiện đó để người vận hành thấy
- **AND** MUST NOT chặn toàn bộ lưu lượng vì một lỗi tra cứu

#### Scenario: Số đã tiêu là số cũ
- **WHEN** số đã tiêu mà Gateway nhìn thấy đến từ một bản đã nhớ đệm
- **THEN** quyết định chặn SHALL vẫn dựa trên số đó
- **AND** khoảng vượt sinh ra vì độ trễ này SHALL nằm trong mức đã chấp nhận, chứ MUST NOT đòi hạ
  thời gian nhớ đệm của khoá

### Requirement: Kiểu trả lời khi bị chặn chọn theo loại agent

Gateway SHALL trả về một trong hai dạng, chọn theo tag định danh của agent gửi request:

- agent có người dùng đọc trực tiếp câu trả lời → **HTTP 200**, thân trả lời mang đúng hình dạng
  một câu trả lời của model, nội dung là câu thông báo hết hạn mức;
- agent xử lý theo lô và phân tích kết quả thành dữ liệu → **HTTP 429**, và thông báo lỗi SHALL
  chứa chuỗi `429`.

MUST NOT trả dạng thứ nhất cho agent xử lý theo lô.

Lý do: hai agent phân loại đang đợi JSON. Một câu văn xuôi đi vào đó sẽ bị phân tích hỏng và báo
thành lỗi JSON — người vận hành đi tìm bệnh ở chỗ phân tích dữ liệu, trong khi bệnh là hết tiền.
Đường 429 thì đã có sẵn trong các agent đó và đã được viết có chủ ý.

#### Scenario: Agent có người chat bị chặn
- **WHEN** một agent loại có người dùng gửi request lúc project đã hết hạn mức
- **THEN** Gateway SHALL trả HTTP 200
- **AND** thân trả lời SHALL có cùng hình dạng với một câu trả lời bình thường của model
- **AND** nội dung SHALL là câu thông báo hết hạn mức, đọc lên hiểu được

#### Scenario: Agent chạy theo lô bị chặn
- **WHEN** một agent loại xử lý theo lô gửi request lúc project đã hết hạn mức
- **THEN** Gateway SHALL trả HTTP 429
- **AND** thông báo SHALL chứa chuỗi `429`
- **AND** MUST NOT trả về một thân trả lời trông giống câu trả lời của model

#### Scenario: Agent gọi ở chế độ luồng
- **WHEN** request bị chặn được gửi ở chế độ luồng
- **THEN** câu trả lời SHALL vẫn về đúng dạng luồng mà agent đang đợi
- **AND** MUST NOT làm agent treo vì không nhận được gì

#### Scenario: Loại agent chưa được khai
- **WHEN** tag của agent gửi request chưa được xếp vào loại nào
- **THEN** Gateway SHALL trả HTTP 429
- **AND** SHALL ghi lại việc thiếu khai báo đó

### Requirement: Mỗi lượt bị chặn để lại một bản ghi, tách khỏi số lượt gọi thật

Mỗi lần chặn SHALL ghi một bản ghi gồm: thời điểm, agent, project, tên model được xin gọi, hạn mức
lúc đó, số đã tiêu lúc đó, và kiểu trả lời đã dùng. Bản ghi SHALL là một dòng JSON trên đầu ra của
tiến trình, đọc được bằng máy. Bản ghi này MUST NOT bị cộng vào số lượt gọi, số token hay chi phí
của các phép thống kê hiện có.

Lý do: trộn vào thì số lượt gọi phồng lên và token trung bình mỗi lượt tụt xuống, không ai hiểu vì
sao. Nhưng bỏ hẳn thì câu "sáng nay agent không trả lời, có phải hỏng không" không có gì trả lời.

#### Scenario: Một lượt bị chặn
- **WHEN** Gateway chặn một request vì hết hạn mức
- **THEN** SHALL có đúng một dòng JSON mới mang đủ bảy trường trên
- **AND** dòng đó SHALL phân tích được bằng máy, không phải câu văn tự do

#### Scenario: Bản ghi không chứa nội dung người dùng
- **WHEN** một request mang nội dung do người dùng nhập bị chặn
- **THEN** dòng ghi MUST NOT chứa nội dung câu hỏi hay câu trả lời

#### Scenario: Thống kê lưu lượng sau khi có lượt bị chặn
- **WHEN** dashboard tính số lượt gọi và token trong kỳ
- **THEN** các lượt bị chặn MUST NOT được tính vào đó

#### Scenario: Truy nguyên một khoảng agent im lặng
- **WHEN** người vận hành hỏi vì sao một agent ngừng trả lời trong một khoảng thời gian
- **THEN** các bản ghi chặn SHALL đủ để chỉ ra thời điểm bắt đầu và project nào hết hạn mức

### Requirement: Nạp thêm hạn mức thì lưu lượng thông trở lại, không phải khởi động lại

Sau khi hạn mức được nâng lên trên số đã tiêu, request tiếp theo của project đó SHALL đi qua được
mà không cần khởi động lại Gateway, không cần cấp lại khoá, và không cần thao tác nào trên agent.

Khoảng trễ từ lúc nạp tới lúc thông SHALL có giới hạn trên xác định và được nêu trong tài liệu.

#### Scenario: Nạp thêm khi đang bị chặn
- **WHEN** người quản trị nâng hạn mức của một project đang bị chặn
- **THEN** trong khoảng trễ đã nêu, request của project đó SHALL đi qua được
- **AND** MUST NOT đòi khởi động lại dịch vụ nào

#### Scenario: Nạp thêm nhưng vẫn chưa đủ
- **WHEN** hạn mức mới vẫn thấp hơn số đã tiêu
- **THEN** project đó SHALL vẫn bị chặn
