# layout-migration-equivalence Specification

## Purpose
TBD - created by archiving change restructure-project-layout. Update Purpose after archive.
## Requirements
### Requirement: Ảnh chụp chuẩn được lấy trước khi dời bất cứ thứ gì

Trước lệnh `git mv` đầu tiên, toàn bộ ảnh chụp chuẩn SHALL được sinh và lưu ngoài repo.
Sau khi dời xong, cùng bộ lệnh đó SHALL được chạy lại và kết quả đối chiếu **bằng máy**
với ảnh chụp chuẩn.

Nghiệm thu SHALL căn cứ trên kết quả `diff`, MUST NOT căn cứ trên việc người xem thấy
màn hình trông ổn. Một bảng số sai trông y hệt một bảng số đúng — đó là kiểu hỏng đắt
nhất và mắt người không bắt được.

Bất kỳ khác biệt nào MUST được giải thích bằng một nguyên nhân đã biết và vô hại, hoặc
dẫn tới hoàn tác. Diff khác rỗng mà không giải thích được SHALL không được bỏ qua.

#### Scenario: Ảnh chụp chuẩn đủ năm hạng mục

- **WHEN** hoàn tất bước chụp ảnh chuẩn
- **THEN** có đủ: mã băm SHA-256 của file database, kết quả 30 phép kiểm database, JSON
  của cả 8 endpoint tách thành 8 file, kết quả đối chiếu hai hệ quản trị, và trạng thái
  nạp của dashboard
- **AND** tất cả nằm ngoài repo, không được commit

#### Scenario: Ảnh chụp không phụ thuộc đồng hồ

- **WHEN** gọi các endpoint để chụp ảnh chuẩn
- **THEN** mọi lời gọi đều truyền `start` và `end` ghi rõ, không dùng giá trị mặc định
- **AND** chụp lại vào ngày khác vẫn cho cùng kết quả nếu database không đổi

### Requirement: Database không bị biến đổi, chỉ đổi vị trí

Việc dời database SHALL là thao tác đổi vị trí thuần tuý. Nội dung file MUST NOT thay
đổi dù chỉ một byte.

#### Scenario: Mã băm file trùng khớp

- **WHEN** so SHA-256 của file database trước và sau khi dời
- **THEN** hai mã băm giống hệt nhau

#### Scenario: Ba mươi phép kiểm cho kết quả y hệt

- **WHEN** chạy lại phép soi database sau khi dời và diff với ảnh chụp chuẩn
- **THEN** diff rỗng
- **AND** vẫn là 30 phép kiểm, cùng số đạt và cùng số cảnh báo như trước

#### Scenario: Đường dẫn sai không tạo được database rỗng

- **WHEN** một chỗ khai báo đường dẫn bị sửa sai sau khi dời
- **THEN** lệnh bị ảnh hưởng báo lỗi hoặc phép kiểm bắt được sai lệch
- **AND** hệ thống không lặng lẽ chạy tiếp trên một database rỗng vừa được tạo mới

### Requirement: Backend trả về nội dung không đổi

Cả 8 endpoint SHALL trả về JSON giống hệt trước và sau khi dời, so đến từng byte, với
cùng tham số và cùng chuỗi kết nối.

#### Scenario: Từng endpoint được đối chiếu riêng

- **WHEN** gọi lại cả 8 endpoint và diff với ảnh chụp chuẩn
- **THEN** cả 8 diff đều rỗng
- **AND** kết quả chỉ ra được endpoint nào lệch nếu có, không chỉ báo là có lệch

#### Scenario: Hai hệ quản trị vẫn khớp nhau

- **WHEN** chạy phép đối chiếu SQLite với PostgreSQL sau khi dời
- **THEN** số phép kiểm đạt bằng đúng số đạt trong ảnh chụp chuẩn

### Requirement: Dashboard nạp và vẽ như trước

Dashboard SHALL nạp mọi tài nguyên và vẽ mọi biểu đồ y như trước khi dời, cả khi phục
vụ qua máy chủ tĩnh lẫn khi mở trực tiếp bằng `file://`.

#### Scenario: Số biểu đồ vẽ được không đổi

- **WHEN** mở dashboard và duyệt qua toàn bộ các tab
- **THEN** số canvas vẽ được bằng đúng số trong ảnh chụp chuẩn

#### Scenario: Không phát sinh lỗi JavaScript mới

- **WHEN** đọc console trình duyệt sau khi duyệt hết các tab
- **THEN** không có lỗi JavaScript nào
- **AND** không yêu cầu **cùng gốc** nào trả về 404, không kể yêu cầu tới máy chủ ngoài

#### Scenario: Trình duyệt không phục vụ bản cũ trong bộ nhớ đệm

- **WHEN** nạp lại dashboard sau khi đường dẫn JavaScript đã đổi
- **THEN** phép kiểm buộc trình duyệt lấy bản mới thay vì bản đệm
- **AND** kết luận "giống trước" không rút ra từ một trang đang chạy mã cũ

### Requirement: Lỗ hở được chứng minh là đã đóng

Phép kiểm tiêu cực SHALL được chạy **cả trước lẫn sau** khi dời. Chạy trước để ghi nhận
lỗ hở là có thật; chạy sau để chứng minh nó đã đóng.

Không đủ nếu chỉ chứng minh thứ cần chạy vẫn chạy — mục đích của thay đổi này là chặn,
nên vế chặn phải được đo.

#### Scenario: Trước khi dời, lỗ hở tái hiện được

- **WHEN** chạy máy chủ tĩnh tại gốc repo theo đúng lệnh trong tài liệu cũ và yêu cầu
  `/.env`
- **THEN** máy chủ trả về 200 kèm nội dung file
- **AND** kết quả này được ghi lại làm bằng chứng

#### Scenario: Sau khi dời, lỗ hở đã đóng

- **WHEN** chạy máy chủ tĩnh theo lệnh mới và yêu cầu lại đúng bốn đường dẫn nhạy cảm
- **THEN** cả bốn trả về 404

### Requirement: Lịch sử file truy được sau khi dời

Mọi lần dời SHALL dùng `git mv` để git ghi nhận là đổi tên. MUST NOT xoá rồi tạo lại
file ở vị trí mới.

#### Scenario: Truy được lịch sử qua chỗ dời

- **WHEN** chạy `git log --follow` trên một file đã dời
- **THEN** lịch sử hiện đủ các commit từ trước khi dời

#### Scenario: Mỗi commit để lại repo chạy được

- **WHEN** dừng lại ở bất kỳ commit nào trong loạt commit dời
- **THEN** đường ống và dashboard tại commit đó vẫn chạy
- **AND** không commit nào dời file mà bỏ lại đường dẫn trỏ vào chỗ cũ

