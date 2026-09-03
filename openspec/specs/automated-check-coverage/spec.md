# automated-check-coverage Specification

## Purpose
TBD - created by archiving change extend-the-checks-to-gateway-data. Update Purpose after archive.
## Requirements
### Requirement: Phép kiểm khoá ngoại phải phủ đúng cấu trúc thật của database
Bộ kiểm tự động SHALL xác định các quan hệ khoá ngoại từ **chính database** tại thời
điểm chạy. Bộ kiểm MUST NOT dựa vào một danh sách quan hệ khai sẵn trong mã, vì cấu trúc
đi tiếp còn danh sách khai sẵn thì đứng lại.

#### Scenario: Thêm bảng mới có khoá ngoại
- **WHEN** một bảng mới có khoá ngoại được thêm vào database
- **THEN** phép kiểm khoá ngoại SHALL phủ luôn quan hệ đó
- **AND** MUST NOT đòi ai sửa một danh sách trong mã trước

#### Scenario: Báo cáo độ phủ
- **WHEN** phép kiểm khoá ngoại chạy xong
- **THEN** kết quả SHALL nêu số quan hệ đã kiểm
- **AND** con số đó SHALL là số quan hệ **có thật**, không phải số quan hệ được khai

#### Scenario: Một khoá ngoại biến mất khỏi database
- **WHEN** số quan hệ khoá ngoại đọc được ít hơn mốc đã ghi
- **THEN** bộ kiểm SHALL báo hỏng và nêu tên quan hệ đã biến mất
- **AND** MUST NOT im lặng chỉ vì các quan hệ còn lại đều hợp lệ

### Requirement: Phép kiểm phải phân biệt "đã kiểm và đạt" với "không có gì để kiểm"
Phép kiểm khẳng định một tính chất trên một tập dữ liệu SHALL cho biết nó đã quan sát
bao nhiêu dòng. Chạy trên tập rỗng, phép kiểm MUST NOT báo đạt.

#### Scenario: Không có dòng nào để kiểm
- **WHEN** một phép kiểm theo nguồn chạy mà nguồn đó không có dòng nào
- **THEN** kết quả SHALL là cảnh báo nói rõ chưa kiểm được
- **AND** MUST NOT là kết quả đạt

#### Scenario: Có dữ liệu và không dòng nào vi phạm
- **WHEN** phép kiểm quan sát được ít nhất một dòng và không dòng nào vi phạm
- **THEN** kết quả SHALL là đạt
- **AND** SHALL nêu số dòng đã quan sát

#### Scenario: Khâu nạp một nguồn hỏng im lặng
- **WHEN** một khâu nạp không ghi được dòng nào cho nguồn của nó
- **THEN** bộ kiểm SHALL làm chuyện đó nhìn thấy được
- **AND** MUST NOT cho ra một báo cáo toàn màu đạt

### Requirement: Ngưỡng thời gian phải tính từ thời điểm chạy
Phép kiểm phát hiện dòng mang thời điểm ở tương lai SHALL lấy mốc từ thời điểm chạy.
Bộ kiểm MUST NOT ghim một mốc thời gian cố định trong mã.

#### Scenario: Sang năm mới
- **WHEN** bộ kiểm chạy ở một năm muộn hơn năm lúc nó được viết
- **THEN** dữ liệu thật của năm đó SHALL không bị coi là thời điểm tương lai

#### Scenario: Lệch múi giờ giữa dữ liệu và máy chủ
- **WHEN** một dòng mang thời điểm của chính ngày đang chạy
- **THEN** dòng đó MUST NOT bị coi là thời điểm tương lai chỉ vì lệch múi giờ

#### Scenario: Mọi bảng có cột thời gian
- **WHEN** phép kiểm thời điểm tương lai chạy
- **THEN** nó SHALL soi mọi bảng có cột thời gian, kể cả bảng ghi từng lượt gọi
- **AND** MUST NOT chỉ soi bảng tổng hợp

### Requirement: Phép kiểm ở tầng API phải hỏi máy chủ
Phép kiểm về hành vi của API SHALL hỏi qua chính giao diện mà người dùng gọi. Nó MUST
NOT chép lại câu truy vấn của bộ kiểm cấu trúc, vì hai bản sao của cùng một phép đo sẽ
trôi khỏi nhau.

#### Scenario: Kiểm số liệu một nguồn qua API
- **WHEN** cần kiểm số liệu của một nguồn ở tầng API
- **THEN** phép kiểm SHALL gọi endpoint và đọc thứ endpoint trả về

#### Scenario: Bộ kiểm cấu trúc và bộ kiểm API bất đồng
- **WHEN** bộ kiểm cấu trúc báo đạt còn bộ kiểm API báo hỏng
- **THEN** kết quả SHALL giữ nguyên cả hai, và MUST NOT bị hoà làm một

