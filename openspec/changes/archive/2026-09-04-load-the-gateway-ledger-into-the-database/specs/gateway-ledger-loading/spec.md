## ADDED Requirements

### Requirement: Sổ Gateway phải đi được vào database của dashboard
Hệ thống SHALL có một bộ nạp đưa các lượt gọi đã ghi trong `LiteLLM_SpendLogs` vào bảng lượt
gọi của dashboard, để lưu lượng qua Gateway hiển thị được cùng ba nguồn cũ. Bộ nạp MUST NOT
sửa đổi sổ gốc dưới bất kỳ hình thức nào — sổ Gateway là bằng chứng gốc và chỉ được đọc.

#### Scenario: Nạp lượt gọi thành công
- **WHEN** bộ nạp chạy trên một sổ Gateway có ít nhất một lượt gọi thành công
- **THEN** mỗi lượt gọi thành công SHALL sinh đúng một dòng trong bảng lượt gọi, mang đủ
  số token vào, ra và tổng đúng như trong sổ gốc

#### Scenario: Chạy lại nhiều lần
- **WHEN** bộ nạp chạy lần thứ hai trên cùng một sổ không có lượt gọi mới
- **THEN** số dòng trong bảng lượt gọi SHALL không đổi, và bộ nạp MUST NOT nhân đôi dữ liệu

#### Scenario: Gateway đang tắt
- **WHEN** bộ nạp chạy mà không kết nối được tới sổ Gateway
- **THEN** nó SHALL báo lỗi rõ ràng và dừng, và MUST NOT kết thúc thành công với 0 dòng nạp

### Requirement: Lượt gọi hỏng phải bị loại nhưng vẫn được đếm
Bộ nạp SHALL chỉ nạp lượt gọi có trạng thái thành công. Lượt gọi hỏng MUST NOT được nạp thành
lưu lượng thật, nhưng số lượng của chúng SHALL được đếm và in ra, vì đó là chỉ báo sức khoẻ
của Gateway.

#### Scenario: Sổ có lẫn lượt gọi hỏng
- **WHEN** sổ chứa cả lượt gọi thành công và lượt gọi hỏng
- **THEN** chỉ lượt thành công SHALL vào bảng lượt gọi, và báo cáo của lần chạy SHALL nêu số
  lượt hỏng đã loại

#### Scenario: Điều kiện lọc dựa trên giá trị đo được
- **WHEN** bộ nạp xác định một dòng là thành công
- **THEN** nó SHALL so trạng thái với giá trị thật mà sổ ghi, và MUST NOT giả định trạng thái
  thành công được biểu diễn bằng giá trị rỗng

### Requirement: Thời điểm phải quy về giờ Việt Nam mà vẫn giữ được bản gốc
Thời điểm trong sổ Gateway không mang múi giờ và được ghi theo UTC. Bộ nạp SHALL lưu đồng thời
thời điểm gốc nguyên vẹn và thời điểm đã quy về giờ Việt Nam, và SHALL đánh dấu rằng múi giờ
gốc đã được xác nhận.

#### Scenario: Lượt gọi sau 17 giờ Việt Nam
- **WHEN** một lượt gọi xảy ra sau 17 giờ giờ Việt Nam, tức là đã sang ngày hôm sau theo lịch
  Việt Nam nhưng vẫn là ngày hôm trước theo UTC
- **THEN** thời điểm đã quy đổi SHALL rơi đúng vào ngày theo lịch Việt Nam

#### Scenario: Kiểm lại về sau
- **WHEN** cần đối chiếu lại một dòng đã nạp với sổ gốc
- **THEN** thời điểm gốc SHALL còn nguyên trong bảng lượt gọi, chưa bị quy đổi đè lên

### Requirement: Khâu nối chiều dữ liệu hỏng phải lộ ra, không được im lặng
Khi một lượt gọi không quy được về agent hoặc về model, bộ nạp MUST NOT âm thầm bỏ dòng đó.
Số dòng không quy được SHALL được đếm theo từng loại và in ra ở mỗi lần chạy.

#### Scenario: Model chưa có trong chiều dữ liệu
- **WHEN** sổ chứa lượt gọi tới một model chưa có trong bảng chiều model
- **THEN** bộ nạp SHALL báo số dòng không nối được, và MUST NOT để toàn bộ dữ liệu biến mất
  mà vẫn kết thúc thành công

#### Scenario: Nhãn định danh bị lẫn nhãn tự động
- **WHEN** một lượt gọi mang nhiều nhãn, trong đó có nhãn do hệ thống tự thêm bên cạnh nhãn
  định danh agent
- **THEN** bộ nạp SHALL chỉ coi nhãn khớp với mã agent đã khai báo là nhãn định danh, và một
  lượt gọi MUST NOT bị quy về nhiều hơn một agent

#### Scenario: Không xác định được agent
- **WHEN** một lượt gọi không mang nhãn định danh nào, hoặc mang từ hai nhãn định danh trở lên
- **THEN** dòng đó MUST NOT được nạp, và SHALL được đếm vào báo cáo của lần chạy

### Requirement: Trường thiếu phải nạp rỗng, không được nạp số không
Khi sổ Gateway không cung cấp một giá trị, bộ nạp SHALL lưu giá trị rỗng. Nó MUST NOT thay
bằng số không, vì số không là một số đo thật và trộn hai thứ đó lại làm sai mọi phép trung bình.

#### Scenario: Không có số token đọc từ bộ nhớ đệm
- **WHEN** một lượt gọi không có thông tin về token đọc từ bộ nhớ đệm
- **THEN** cột tương ứng SHALL để rỗng, và số dòng rỗng SHALL được in ra ở báo cáo

#### Scenario: Không xác định được người dùng cuối
- **WHEN** một lượt gọi không mang định danh người dùng cuối
- **THEN** cột người dùng SHALL để rỗng, và bộ nạp MUST NOT tự gán một nhãn thay thế

### Requirement: Chi phí lấy từ Gateway phải được ghi nhãn là ước tính
Mọi chỗ hiển thị số tiền có nguồn gốc Gateway SHALL mang nhãn cho biết đó là số ước tính, vì
số tiền do Gateway tính ra đến từ bảng giá nội bộ của nó chứ không phải từ hoá đơn của nhà
cung cấp.

#### Scenario: Hiển thị chi phí nguồn Gateway
- **WHEN** dashboard hiển thị chi phí của dữ liệu có nguồn là Gateway
- **THEN** số đó SHALL kèm nhãn ước tính, và MUST NOT trình bày lẫn lộn với số lấy từ hoá đơn
  như thể cùng độ tin cậy

#### Scenario: Bảng giá có chiết khấu hoặc phụ phí
- **WHEN** số tiền của Gateway đã bị áp thêm chiết khấu hoặc phụ phí khác không
- **THEN** bộ nạp SHALL dừng và báo, vì khi đó giá trị tổng không còn là giá gốc của nhà cung cấp
