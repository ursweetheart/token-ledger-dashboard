## ADDED Requirements

### Requirement: Vai đọc phải còn đọc được sau khi dựng lại database
Sau khi quy trình dựng lại database chạy xong, vai mà API dùng để đọc SHALL vẫn đọc được toàn bộ
bảng và view mà nó được cấp quyền. Quy trình dựng lại MUST NOT kết thúc thành công khi vai đó đã
mất quyền đọc.

#### Scenario: Dựng lại database xoá sạch phân quyền
- **WHEN** một bước của quy trình dựng lại xoá schema và tạo lại nó
- **THEN** quy trình SHALL phát hiện vai đọc đã mất quyền
- **AND** SHALL dừng lại kèm thông báo nói rõ vai nào mất quyền gì

#### Scenario: Phân quyền còn nguyên
- **WHEN** vai đọc còn đủ quyền trên schema, mọi bảng và mọi view
- **THEN** quy trình dựng lại SHALL kết thúc bình thường

#### Scenario: Phân quyền mất không đều
- **WHEN** vai đọc còn quyền trên một số bảng nhưng mất trên số khác
- **THEN** phép kiểm SHALL phát hiện được
- **AND** MUST NOT kết luận đạt sau khi chỉ thử một bảng

#### Scenario: Quy trình dựng lại báo lỗi thay vì tự chữa
- **WHEN** phát hiện vai đọc mất quyền
- **THEN** quy trình SHALL báo cho người vận hành
- **AND** MUST NOT tự cấp lại quyền rồi tiếp tục im lặng

### Requirement: Phép kiểm chỉ-đọc phải phân biệt chặn ghi với mất quyền đọc
Phép kiểm kỷ luật chỉ-đọc SHALL khẳng định hai điều độc lập: lệnh ghi bị từ chối, **và** kết nối
vẫn đọc được dữ liệu. Phép kiểm MUST NOT kết luận đạt khi mới xác nhận được điều thứ nhất.

#### Scenario: Kết nối chỉ-đọc còn nguyên vẹn
- **WHEN** lệnh ghi bị từ chối và câu đọc thành công
- **THEN** phép kiểm SHALL báo đạt

#### Scenario: Kết nối mất quyền đọc
- **WHEN** lệnh ghi bị từ chối nhưng câu đọc cũng thất bại
- **THEN** phép kiểm SHALL báo hỏng
- **AND** thông báo SHALL nói rõ đây là mất quyền đọc, không phải kỷ luật chỉ-đọc

#### Scenario: Kết nối cho phép ghi
- **WHEN** lệnh ghi được chấp nhận
- **THEN** phép kiểm SHALL báo hỏng

#### Scenario: Câu đọc dùng để kiểm phải chạm dữ liệu thật
- **WHEN** phép kiểm thực hiện câu đọc
- **THEN** câu đó SHALL đọc một bảng thật trong schema
- **AND** MUST NOT dùng một câu đọc chạy được cả khi vai đã mất quyền trên schema
