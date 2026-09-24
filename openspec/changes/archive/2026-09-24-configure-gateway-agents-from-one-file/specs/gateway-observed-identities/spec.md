## ADDED Requirements

### Requirement: Single agent dùng một service identity
Với registry user_mode=single, loader SHALL nhận `svc.<code>` theo chuẩn trim/lower của service hiện hữu và gán vào service account đã đăng ký. Loader MUST NOT tự tạo người dùng từ một tên khác gửi vào single agent. Raw identity của fact SHALL được giữ.

#### Scenario: Service identity hợp lệ
- **WHEN** agent single gửi `X-User: svc.batch-classifier` khớp code
- **THEN** call SHALL trỏ tới service account duy nhất của agent

#### Scenario: Tên người được gửi vào single agent
- **WHEN** agent single gửi `X-User: alice`
- **THEN** loader SHALL tăng identity_unresolvable, dùng neo và không tạo Alice

### Requirement: Multiple agent nhận identity từ Gateway log
Với registry user_mode=multiple, loader SHALL tạo/lấy mapping bằng `(agent_id, external_user_id)` từ `end_user` của log. External ID SHALL bảo toàn hoa/thường, không chứa control chars, không blank và dài tối đa 256 UTF-8 bytes. Account SHALL mang kind gateway_observed, provenance Gateway, không tự thành real/directory và không gộp với username legacy. First/last seen SHALL dùng min/max timestamp nguồn.

#### Scenario: Request đầu tiên của một identity
- **WHEN** log hợp lệ của agent multiple có external ID chưa từng thấy
- **THEN** loader SHALL tạo đúng một mapping và account rồi gán fact vào account đó mà không đọc danh bạ

#### Scenario: Hai agent cùng gửi admin
- **WHEN** agent A và B cùng gửi external ID `admin`
- **THEN** hai mapping SHALL trỏ tới hai account khác nhau, không trộn với account admin legacy

#### Scenario: Phân biệt hoa thường
- **WHEN** cùng agent gửi `Alice` và `alice`
- **THEN** hai external IDs SHALL được giữ riêng, không tự suy chúng là cùng người

#### Scenario: Nạp log cũ sau log mới
- **WHEN** replay gặp timestamp sớm hơn first_seen hiện có
- **THEN** first_seen SHALL cập nhật về min, last_seen SHALL không lùi và account_id SHALL không đổi

### Requirement: Identity thiếu hoặc không hợp lệ phải nhìn thấy được
Loader SHALL giữ call hợp lệ về agent nhưng thiếu/blank/invalid identity ở fallback và ghi counter theo lý do. Loader MUST NOT tạo account có identity rỗng hoặc giả tên/phòng ban/email. Các tag không nhận diện được agent, tag mâu thuẫn và cache duplicate SHALL bị xử lý trước khám phá identity.

#### Scenario: Không gửi X-User
- **WHEN** một call của multiple agent không có end_user
- **THEN** call SHALL vào fallback, raw user_id rỗng được giữ và missing counter SHALL tăng

#### Scenario: Identity vượt giới hạn
- **WHEN** end_user dài hơn 256 UTF-8 bytes hoặc chứa control chars
- **THEN** loader SHALL đếm invalid identity, không tạo account, giữ call ở fallback mà không làm hỏng cả batch

#### Scenario: Agent tag chưa được khai
- **WHEN** log có một tag lạ và identity hợp lệ
- **THEN** loader MUST NOT tạo agent/account và SHALL báo dòng không phân giải được agent

#### Scenario: Cache duplicate
- **WHEN** log là bản sao cache bị quy tắc hiện hữu loại
- **THEN** loader SHALL không tạo identity chỉ vì dòng bản sao đó

### Requirement: Khám phá phải idempotent và không phá legacy policy
Khám phá identity và ghi facts trong batch SHALL atomic, chống cạnh tranh bằng constraint/lock, dry-run không ghi. Agent không thuộc registry SHALL tiếp tục dùng directory/service lookup hiện hữu với kết quả không đổi.

#### Scenario: Cùng identity xuất hiện trong hai worker
- **WHEN** hai tiến trình xử lý cùng cặp agent/external ID
- **THEN** database SHALL có một mapping/account, không orphan và không fact trùng

#### Scenario: Lỗi sau khi tạo account
- **WHEN** batch gặp lỗi trước khi commit fact
- **THEN** account/mapping mới của batch SHALL rollback cùng facts

#### Scenario: Agent legacy nhận người không có danh bạ
- **WHEN** agent không có registry nhận identity chưa được phép bởi lookup cũ
- **THEN** identity_unresolvable và fallback SHALL giữ hành vi cũ, không tự đăng ký người đó
