# container-log-output Specification

## Purpose
TBD - created by archiving change speak-one-language-in-the-container-logs. Update Purpose after archive.
## Requirements
### Requirement: Log của tiến trình chạy trong container phải viết bằng một ngôn ngữ
Mọi thông báo do mã của dự án ghi ra luồng log của container SHALL viết bằng tiếng Anh, để đọc
liền mạch với thông báo của các thành phần bên thứ ba trong cùng luồng. Chữ hiển thị cho người
dùng cuối trên giao diện MUST NOT bị đổi theo quy tắc này.

#### Scenario: Thông báo của tiến trình nền
- **WHEN** một tiến trình chạy trong container ghi thông báo về tiến độ, cảnh báo hay lỗi
- **THEN** thông báo đó SHALL viết bằng tiếng Anh

#### Scenario: Thông báo hiển thị trên giao diện
- **WHEN** một thông báo được hiển thị cho người dùng cuối trên màn hình
- **THEN** thông báo đó SHALL giữ tiếng Việt có dấu, và MUST NOT bị đổi sang tiếng Anh

#### Scenario: Cùng một sự việc xuất hiện ở hai nơi
- **WHEN** một sự việc vừa được ghi vào log vừa được hiển thị trên giao diện
- **THEN** mỗi nơi SHALL dùng ngôn ngữ của người đọc nơi đó, và hai bản SHALL nhận ra được là
  cùng một sự việc

### Requirement: Mức chi tiết của log phải điều chỉnh được từ bên ngoài
Hệ thống SHALL cho phép chọn mức chi tiết của log mà không phải sửa mã. Mức đã chọn SHALL áp
dụng cho toàn bộ chuỗi tiến trình của một lần chạy, kể cả tiến trình do tiến trình khác gọi ra.

#### Scenario: Chạy ở mức mặc định
- **WHEN** không chỉ định mức nào
- **THEN** log SHALL chỉ gồm tiến độ từng bước, cảnh báo, lỗi và các dòng số đo

#### Scenario: Chạy ở mức chi tiết nhất
- **WHEN** người vận hành yêu cầu mức chi tiết nhất
- **THEN** toàn bộ thông báo chi tiết SHALL xuất hiện trở lại, và MUST NOT có thông tin nào chỉ
  tồn tại ở phiên bản trước khi thay đổi này

#### Scenario: Tiến trình gọi tiến trình khác
- **WHEN** một tiến trình gọi ra tiến trình con
- **THEN** mức chi tiết đã chọn SHALL có hiệu lực với tiến trình con, mà không phải truyền tay
  qua từng lời gọi

### Requirement: Thứ tự dòng log phải phản ánh thứ tự sự việc
Các dòng log SHALL xuất hiện theo đúng thứ tự sự việc đã xảy ra, kể cả khi chúng do nhiều tiến
trình khác nhau ghi ra. Hệ thống MUST NOT để dòng của tiến trình con xuất hiện trước dòng đánh
dấu bước đã sinh ra nó.

#### Scenario: Một bước gọi ra tiến trình con
- **WHEN** một bước ghi dòng đánh dấu rồi gọi tiến trình con, và tiến trình con cũng ghi log
- **THEN** dòng của tiến trình con SHALL xuất hiện sau dòng đánh dấu bước đó

#### Scenario: Tiến trình con báo lỗi
- **WHEN** một tiến trình con hỏng và ghi thông báo lỗi
- **THEN** thông báo đó SHALL nằm sau dòng đánh dấu bước của nó, để người đọc quy được lỗi về
  đúng bước
- **AND** thứ tự này SHALL đúng cả khi đọc qua công cụ xem log của container, không chỉ khi
  chạy trực tiếp trên terminal

### Requirement: Số đo và kết quả kiểm tra MUST NOT bị rút gọn
Các dòng mang số đo, kết quả đối chiếu và kết quả kiểm tra SHALL xuất hiện ở mức mặc định. Hệ
thống MUST NOT đẩy chúng xuống mức chi tiết hơn, vì chúng là lý do người vận hành đọc log.

#### Scenario: Kết thúc một bước nạp dữ liệu
- **WHEN** một bước nạp dữ liệu chạy xong
- **THEN** số dòng và số token đã nạp SHALL có mặt trong log ở mức mặc định

#### Scenario: Phát hiện một chênh lệch trong dữ liệu
- **WHEN** một phép đối chiếu tìm thấy chênh lệch
- **THEN** chênh lệch đó SHALL được ghi kèm số đo cụ thể, ở mức mặc định

### Requirement: Cảnh báo an toàn MUST NOT bị làm nhẹ đi
Thông báo cảnh báo hệ thống đang chạy ở trạng thái kém an toàn hơn bình thường SHALL giữ nguyên
mức độ nổi bật. Hệ thống MUST NOT rút gọn hay hạ mức chúng vì lý do gọn gàng.

#### Scenario: Máy chủ chạy không xác thực
- **WHEN** máy chủ khởi động ở chế độ không đòi xác thực
- **THEN** cảnh báo SHALL xuất hiện ở mọi lần khởi động, và SHALL giữ nguyên hình thức khiến
  người đọc không thể bỏ qua

#### Scenario: Thiếu cấu hình bắt buộc
- **WHEN** một biến cấu hình bắt buộc không được đặt
- **THEN** tiến trình SHALL từ chối khởi động, và thông báo SHALL nêu đủ các bước để sửa

### Requirement: Log của container MUST NOT lớn vô hạn
Luồng log của mỗi container SHALL có giới hạn kích thước và số tệp giữ lại. Hệ thống MUST NOT
để log tăng không giới hạn trên ổ đĩa đang chứa dữ liệu.

#### Scenario: Container chạy dài ngày
- **WHEN** một container chạy liên tục và ghi log đều đặn
- **THEN** dung lượng log SHALL dừng ở một mức đã định, và phần cũ nhất SHALL bị loại bỏ trước

