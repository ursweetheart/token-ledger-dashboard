## ADDED Requirements

### Requirement: Sổ dashboard phải tự hội tụ về sổ Gateway mà không cần người can thiệp
Khi một lượt gọi đi qua Gateway và được ghi vào sổ của Gateway, dữ liệu ấy SHALL xuất hiện
trong sổ dashboard mà **không** cần bất kỳ ai chạy lệnh nào. Hệ thống MUST NOT trông vào
việc có người nhớ ra phải làm mới.

#### Scenario: Một lượt gọi mới đi qua Gateway
- **WHEN** một lượt gọi được ghi vào sổ của Gateway
- **AND** không ai chạy lệnh nào
- **THEN** trong vòng một khoảng thời gian đã công bố, lượt gọi ấy SHALL có mặt trong bảng
  bản-ghi-từng-lượt của dashboard
- **AND** SHALL có mặt trong **mọi** bảng tổng hợp mà nguồn Gateway nuôi

#### Scenario: Đường tự làm mới bị tắt
- **WHEN** đường tự làm mới không chạy
- **THEN** hệ thống MUST NOT hiển thị số cũ như thể là số mới
- **AND** tình trạng ấy SHALL bị một phép kiểm phát hiện

#### Scenario: Làm mới bằng tay vẫn phải dùng được
- **WHEN** một người chạy đường làm mới bằng tay
- **THEN** kết quả SHALL không khác so với khi đường tự động chạy

### Requirement: Độ trễ phải đo bằng chính sổ Gateway, không đo bằng bảng nội bộ
Phép kiểm độ trễ SHALL so sổ dashboard với **sổ của Gateway** — nguồn nằm ngoài
database dashboard. Nó MUST NOT chỉ so các bảng dẫn xuất bên trong dashboard với nhau, vì
phép so nội bộ vẫn đạt khi toàn bộ đường nạp đứng im.

#### Scenario: Sổ Gateway đi trước sổ dashboard quá ngưỡng
- **WHEN** dòng mới nhất của sổ Gateway mới hơn phần Gateway của sổ dashboard quá ngưỡng
- **THEN** phép kiểm SHALL báo hỏng
- **AND** SHALL nêu độ trễ đo được, không chỉ nêu đạt hay hỏng

#### Scenario: Sổ Gateway chưa có dòng nào
- **WHEN** sổ Gateway chưa có dòng nào để so
- **THEN** kết quả SHALL là **chưa kiểm được**
- **AND** MUST NOT là đạt

#### Scenario: Dashboard chưa có dòng Gateway nào nhưng sổ Gateway thì có
- **WHEN** sổ Gateway có dòng còn phần Gateway của sổ dashboard rỗng
- **THEN** phép kiểm SHALL báo hỏng
- **AND** MUST NOT coi bảng rỗng là "không có gì để so"

#### Scenario: Dòng mới nhất bị tầng nạp loại bỏ hợp lệ
- **WHEN** dòng mới nhất của sổ Gateway bị tầng nạp loại theo đúng bộ lọc của nó
- **THEN** phép kiểm MUST NOT báo hỏng
- **AND** phép so SHALL thực hiện trên đúng tập dòng mà tầng nạp nhận

### Requirement: Ngưỡng độ trễ phải suy ra từ nhịp làm mới
Ngưỡng của phép kiểm độ trễ SHALL được tính từ nhịp làm mới đang cấu hình. Nó MUST NOT là
một con số viết cứng độc lập với nhịp.

#### Scenario: Nhịp làm mới được đổi
- **WHEN** nhịp làm mới đổi sang một giá trị khác
- **THEN** ngưỡng của phép kiểm SHALL đổi theo
- **AND** MUST NOT phải sửa tay ở một chỗ thứ hai

### Requirement: Đường tự làm mới phải đo bằng kết quả, không đo bằng tiến trình
Việc xác định đường tự làm mới còn hoạt động SHALL dựa trên **sổ có tươi không**. Nó MUST
NOT chỉ dựa trên việc tiến trình còn sống, vì một tiến trình còn sống mà không làm gì sẽ
qua được phép kiểm ấy.

#### Scenario: Tiến trình còn sống nhưng không làm mới được
- **WHEN** tiến trình làm mới còn chạy nhưng không lượt nào thành công
- **THEN** phép kiểm SHALL báo hỏng

#### Scenario: Một lượt làm mới hỏng
- **WHEN** một lượt làm mới hỏng
- **THEN** vòng lặp SHALL tiếp tục các lượt sau
- **AND** lỗi SHALL lộ ra trong log, MUST NOT bị nuốt

### Requirement: Độ trễ phải nhìn thấy được ở chỗ người đọc số
Độ trễ giữa hai sổ SHALL phơi ra được cho người đang đọc số, chứ không chỉ nằm trong một
phép kiểm phải có người chạy mới biết.

#### Scenario: Số đang cũ
- **WHEN** phần Gateway của sổ dashboard đang cũ hơn ngưỡng
- **THEN** người đọc số SHALL có cách biết được điều đó
- **AND** MUST NOT phải tự đi so hai database mới biết
