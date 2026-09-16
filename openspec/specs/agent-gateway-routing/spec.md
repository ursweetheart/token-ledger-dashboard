# agent-gateway-routing Specification

## Purpose
TBD - created by archiving change route-the-first-agent-through-the-gateway. Update Purpose after archive.
## Requirements
### Requirement: Agent chỉ được tới nhà cung cấp qua Gateway
Một agent đã nối vào Gateway MUST NOT giữ khoá API của nhà cung cấp trong cấu hình của
nó. Thứ agent cầm SHALL là một Virtual Key chỉ dùng được với Gateway, để việc đi qua Gateway
là **bắt buộc về mặt kỹ thuật** chứ không phải một thoả thuận.

#### Scenario: Agent đã chuyển sang Gateway
- **WHEN** một agent đã được nối vào Gateway và đang chạy ở chế độ đó
- **THEN** cấu hình của agent MUST NOT chứa khoá nhà cung cấp (với Google AI Studio là
  chuỗi bắt đầu `AQ.`), và SHALL chứa một Virtual Key `sk-…`

#### Scenario: Virtual Key bị thu hồi
- **WHEN** Virtual Key của một agent bị xoá hoặc hết hạn
- **THEN** agent đó SHALL dừng gọi được nhà cung cấp, chứ MUST NOT tự đi đường vòng thành
  công — và các agent khác SHALL không bị ảnh hưởng

### Requirement: Mỗi request phải tính vào đúng khoá project của agent gửi nó
Gateway SHALL chọn khoá nhà cung cấp theo **danh tính của agent gửi request**, không được
chọn theo thứ tự khai báo trong cấu hình. Nhờ đó hoá đơn của nhà cung cấp vẫn tách được
theo project và còn dùng làm nguồn đối chiếu độc lập với sổ của Gateway.

#### Scenario: Hai agent, hai project, cùng một model
- **WHEN** hai agent thuộc hai project khác nhau cùng gửi request tới cùng một tên model
  công bố (ví dụ `gemini-flash-lite`)
- **THEN** mỗi request SHALL đi ra bằng khoá của đúng project của agent gửi nó, và hoá đơn
  nhà cung cấp SHALL ghi hai project riêng biệt

#### Scenario: Thêm agent thứ N
- **WHEN** một agent mới được nối vào Gateway với project riêng
- **THEN** việc nối SHALL hoàn tất bằng cách thêm khoá project vào cấu hình Gateway và cấp
  một Virtual Key mới, MUST NOT đòi sửa mã nguồn Gateway hay đổi cách các agent cũ hoạt
  động

#### Scenario: Cơ chế chọn khoá theo agent bị vô hiệu hoá
- **WHEN** cơ chế chọn khoá theo danh tính agent không được bật, hoặc bị bỏ qua vì bất kỳ lý
  do gì
- **THEN** tình huống đó SHALL phát hiện được bằng một phép kiểm âm có chủ đích (một tuyến
  cùng tên nhưng khoá sai phải không bao giờ bị chạm tới), chứ MUST NOT chỉ dựa vào việc
  request trả về thành công — khi cơ chế này hỏng, request vẫn thành công, sổ vẫn ghi đúng
  token và chi phí, chỉ riêng khoá project là sai

### Requirement: Sổ của Gateway phải ghi đủ và ghi đúng cho mỗi lượt gọi của agent
Mỗi lượt gọi thành công của agent SHALL để lại đúng một bản ghi mang số token khác 0, chi
phí khác 0, đúng tên model thật đã gọi, và nhận diện được agent gửi. Bản ghi MUST NOT
chứa nội dung câu hỏi hay câu trả lời.

#### Scenario: Một lượt phân loại của agent
- **WHEN** agent gửi một request qua Gateway và nhà cung cấp trả về thành công
- **THEN** SHALL có đúng một bản ghi mới với `total_tokens > 0`, `spend > 0`, trường model
  bằng đúng model thật đã gọi (không phải bí danh), và trường nhận diện agent khác rỗng

#### Scenario: Bí danh model bị khai sai
- **WHEN** tên model mà agent gửi lên trỏ tới một tuyến khác với tuyến dự định
- **THEN** sai lệch đó SHALL phát hiện được từ bản ghi (trường model thật khác với model
  mong đợi), chứ MUST NOT chỉ dựa vào việc request có trả về thành công hay không

#### Scenario: Nội dung không được ghi
- **WHEN** một request mang nội dung do người dùng nhập đi qua Gateway
- **THEN** chuỗi nội dung đó SHALL không xuất hiện ở bất kỳ cột nào của bản ghi, kể cả cột
  giữ nguyên văn request

### Requirement: Chuyển sang Gateway không được đổi kết quả agent trả về
Việc đổi đường đi của lưu lượng MUST NOT làm đổi ý nghĩa kết quả mà agent trả cho người
dùng. Riêng chế độ trả lời có cấu trúc SHALL được kiểm riêng, vì nó có thể mất đi mà không
sinh ra lỗi nào.

#### Scenario: Cùng một đầu vào, trước và sau khi chuyển
- **WHEN** cùng một đầu vào được gửi cho agent trước và sau khi chuyển sang Gateway
- **THEN** các trường kết quả SHALL giữ nguyên ý nghĩa

#### Scenario: Chế độ trả lời có cấu trúc
- **WHEN** agent yêu cầu nhà cung cấp trả lời theo cấu trúc (JSON)
- **THEN** kết quả trả về SHALL vẫn parse được thành cấu trúc đó; nếu tham số yêu cầu cấu
  trúc bị Gateway bỏ qua, tình huống này SHALL bị phát hiện bằng một phép kiểm riêng chứ
  MUST NOT để lọt vì không có lỗi nào được ném ra

### Requirement: Số lượt gọi tới nhà cung cấp không được nhân lên khi có nhiều lớp thử lại
Khi cả agent lẫn Gateway đều có cơ chế thử lại, hệ thống SHALL chỉ định **một** nơi chịu
trách nhiệm thử lại. Một request hỏng MUST NOT biến thành tích số lượt gọi của hai lớp.

#### Scenario: Nhà cung cấp lỗi liên tiếp
- **WHEN** nhà cung cấp trả lỗi cho mọi lượt thử của một request
- **THEN** tổng số lượt gọi thật tới nhà cung cấp SHALL không vượt quá giới hạn thử lại của
  một lớp duy nhất
