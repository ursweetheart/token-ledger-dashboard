## MODIFIED Requirements

### Requirement: Khâu nối chiều dữ liệu hỏng phải lộ ra, không được im lặng
Khi một lượt gọi không quy được về agent hoặc về model, bộ nạp MUST NOT âm thầm bỏ dòng đó.
Số dòng không quy được SHALL được đếm theo từng loại và in ra ở mỗi lần chạy.

**Định danh người dùng cuối SHALL được phân giải theo cặp (agent, định danh), không theo định danh
một mình.** Một người có thể có mặt trong danh bạ của nhiều agent; hệ thống MUST NOT vì thế mà từ
chối định danh của họ ở agent này chỉ vì một agent khác cũng có họ.

Phép phân giải SHALL hỏi *"định danh này có mặt trong danh bạ của agent gửi request không"*. Nó
MUST NOT hỏi *"tài khoản này thuộc về agent nào"* — tài khoản gộp chỉ mang được **một** agent, nên
câu hỏi ấy luôn sai với người dùng nhiều agent.

Nới lỏng theo chiều ngược lại cũng bị cấm: định danh **không** có trong danh bạ của agent gửi
request SHALL vẫn bị từ chối và vẫn được đếm. Một agent gửi tên đăng nhập cục bộ của chính nó
(ví dụ `admin`) MUST NOT được quy về một người dùng có thật của agent khác.

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

#### Scenario: Người dùng có mặt trong danh bạ của nhiều agent
- **WHEN** một người có mặt trong danh bạ của hai agent trở lên, và một lượt gọi mang định danh
  của họ cùng nhãn của một trong những agent ấy
- **THEN** lượt gọi đó SHALL quy về đúng tài khoản của người ấy
- **AND** bộ đếm định danh không phân giải được MUST NOT tăng
- **AND** kết quả MUST NOT phụ thuộc vào việc agent nào được chọn làm nguồn phòng ban cho người ấy

#### Scenario: Định danh không có trong danh bạ của agent gửi request
- **WHEN** một lượt gọi mang định danh không có trong danh bạ của agent gửi nó
- **THEN** định danh đó SHALL bị từ chối
- **AND** bộ đếm định danh không phân giải được SHALL tăng
- **AND** dòng SHALL quy về tài khoản đại diện mức agent, MUST NOT để rỗng
- **AND** định danh đó MUST NOT được quy về một tài khoản trùng tên thuộc agent khác

#### Scenario: Agent chạy bằng một tài khoản dịch vụ
- **WHEN** một agent một-người-dùng gửi định danh tài khoản dịch vụ của chính nó
- **THEN** kết quả phân giải SHALL không khác gì trước khi đổi sang tra theo cặp (agent, định danh)

#### Scenario: Định danh gửi lên khác cách viết hoa với bản trong danh bạ

- **WHEN** một lượt gọi mang định danh chỉ khác bản trong danh bạ ở cách viết hoa, hoặc có khoảng
  trắng thừa ở hai đầu
- **THEN** định danh đó SHALL vẫn phân giải về đúng tài khoản ấy
- **AND** bộ đếm định danh không phân giải được MUST NOT tăng
- **AND** quy ước chuẩn hoá SHALL giống nhau ở cả hai đầu — chỗ dựng bảng tra và chỗ tra cứu

#### Scenario: Một định danh ứng với nhiều dòng danh bạ trong cùng một agent
- **WHEN** danh bạ của một agent ghi cùng một tên đăng nhập bằng nhiều dạng khoá khác nhau
- **THEN** phép tra SHALL gộp chúng lại nếu chúng cùng trỏ về một tài khoản
- **AND** nếu chúng trỏ về hai tài khoản khác nhau thì phép dựng bảng tra SHALL dừng và báo lỗi,
  MUST NOT im lặng chọn một trong hai
