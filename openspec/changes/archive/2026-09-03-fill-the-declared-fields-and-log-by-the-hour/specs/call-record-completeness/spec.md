## ADDED Requirements

### Requirement: Mỗi trường đã khai phải có dữ liệu, không chỉ có cột
Với mỗi trường mà bản ghi lượt gọi đã khai là bắt buộc, hệ thống SHALL điền dữ liệu cho những
dòng suy ra được. Việc bảng có cột MUST NOT được coi là đã đáp ứng, khi cột đó rỗng trên toàn bộ
dữ liệu của một nguồn.

#### Scenario: Trường suy ra được từ dữ liệu đã có
- **WHEN** một trường bắt buộc suy ra được từ dữ liệu đã nạp
- **THEN** trường đó SHALL được điền cho mọi dòng suy ra được

#### Scenario: Kiểm độ đầy của bản ghi
- **WHEN** cần biết bản ghi lượt gọi đã đủ trường chưa
- **THEN** phép kiểm SHALL đếm số dòng CÓ DỮ LIỆU ở từng trường, và MUST NOT chỉ kiểm sự tồn
  tại của cột

### Requirement: Phòng ban của lượt gọi phải tra từ tài khoản
Đơn vị của một lượt gọi SHALL tra từ tài khoản đã quy được của lượt đó. Hệ thống MUST NOT suy
đơn vị từ nhãn định danh của agent, vì nhãn đó cho biết agent nào gửi chứ không cho biết người
gửi thuộc đơn vị nào.

#### Scenario: Lượt gọi của một tài khoản dịch vụ
- **WHEN** lượt gọi quy về một tài khoản dịch vụ không thuộc phòng ban thật nào
- **THEN** đơn vị kỹ thuật của tài khoản đó SHALL được lưu, và MUST NOT bị bỏ trống hay thay
  bằng một phòng ban có thật

#### Scenario: Agent có nhiều người dùng đi qua Gateway
- **WHEN** một agent có nhiều người dùng gửi lượt gọi
- **THEN** đơn vị SHALL lấy theo tài khoản của từng lượt, và MUST NOT lấy chung một đơn vị cho
  cả agent

### Requirement: Trường nhà cung cấp không báo phải để rỗng
Khi nguồn dữ liệu không cung cấp giá trị cho một trường, cột đó SHALL để rỗng. Hệ thống MUST NOT
ghi số không thay cho giá trị vắng mặt, vì số không là một phép đo còn rỗng là sự vắng mặt của
phép đo.

#### Scenario: Nhà cung cấp trả về giá trị rỗng
- **WHEN** nguồn ghi khoá của một trường nhưng giá trị là rỗng
- **THEN** cột tương ứng SHALL để rỗng

#### Scenario: Tính tỷ lệ trên một trường có thể rỗng
- **WHEN** một phép tính tỷ lệ dùng trường đó làm tử số
- **THEN** phép tính SHALL phân biệt được "bằng không" với "không đo được", và MUST NOT gộp hai
  trường hợp thành một

#### Scenario: Trường rỗng chặn một phép đối chiếu
- **WHEN** một phép đối chiếu đã lên kế hoạch cần trường đang rỗng
- **THEN** hệ thống SHALL ghi lại rằng phép đối chiếu đó chưa thực hiện được, kèm lý do đo được,
  và MUST NOT báo là đã đối chiếu xong
