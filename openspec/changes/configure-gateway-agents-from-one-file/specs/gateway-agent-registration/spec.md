## ADDED Requirements

### Requirement: Cấu hình agent Gateway trong một file
Dashboard SHALL nhận khai báo agent mới từ `config/gateway-agents.yaml` schema version 1 với `code`, `name`, `user_mode` (`single` hoặc `multiple`), `reporting_start_date` ISO và `active` boolean mặc định true. Hệ thống MUST NOT yêu cầu sửa Python, crawl app, billing/monitoring exports hoặc user directory. Parser SHALL từ chối unknown keys, duplicate keys/codes, blank name, code sai định dạng, kiểu dữ liệu sai và ngày không hợp lệ trước khi ghi DB. YAML MUST NOT chứa credential.

#### Scenario: Agent chưa có request
- **WHEN** operator khai một agent hợp lệ chưa có Gateway logs
- **THEN** apply SHALL tạo đăng ký đầy đủ với ngày bắt đầu đã khai và không cần suy ngày từ agent khác
- **AND** agent SHALL xuất hiện trong catalog với trạng thái chưa có usage

#### Scenario: Cấu hình sai trong một entry
- **WHEN** file có nhiều agents và một entry không hợp lệ
- **THEN** toàn bộ apply SHALL thất bại, nêu field/entry sai và không tạo agent nào

#### Scenario: Parser YAML nhận khóa trùng
- **WHEN** một entry khai `user_mode` hai lần
- **THEN** validation SHALL báo lỗi thay vì âm thầm chọn giá trị cuối

### Requirement: Apply tăng dần và dry-run không ghi dữ liệu
Hệ thống SHALL cung cấp CLI `scripts/apply_gateway_agents.py --config <path>` và `--dry-run`. Apply SHALL tạo/cập nhật toàn bộ cấu hình trong một transaction, không rebuild/truncate và không gọi `load_org.py`/`gen_catalog.py`. Dry-run SHALL chỉ đọc, không chạy migration hoặc thay sequence, model, registry, fact hay heartbeat. Migration SHALL là bước triển khai riêng.

#### Scenario: Áp dụng lại cùng cấu hình
- **WHEN** apply chạy hai lần với cùng file
- **THEN** ID và số lượng agent/account/unit SHALL không đổi ở lần hai
- **AND** usage và pricing history SHALL không thay đổi

#### Scenario: Dry-run
- **WHEN** operator chạy dry-run trên schema tương thích
- **THEN** CLI SHALL mô tả các thay đổi dự kiến và mọi bảng/sequence SHALL giữ nguyên

#### Scenario: Chưa có migration
- **WHEN** CLI chạy với database chưa có schema registry
- **THEN** CLI SHALL yêu cầu migrate rõ ràng và không tự nâng cấp database

### Requirement: ID và ownership phải được bảo vệ
Hệ thống SHALL cấp ID không trùng trong môi trường cạnh tranh và tạo đúng một account neo mỗi agent. Existing legacy agent codes MUST NOT bị takeover bằng YAML. Agent code, user_mode và reporting_start_date SHALL bất biến sau đăng ký trong v1; name/active được cập nhật. Single SHALL có `svc.<code>` loại service_account; multiple SHALL có whole_agent fallback; cả hai có unattributed account và đơn vị kỹ thuật phù hợp.

#### Scenario: Hai tiến trình cùng đăng ký
- **WHEN** hai apply đồng thời xử lý cùng agent
- **THEN** chỉ một bộ agent/unit/account SHALL tồn tại, không trùng ID và không commit một phần

#### Scenario: Code đã thuộc agent cũ
- **WHEN** YAML dùng code tồn tại trong dim_agent nhưng chưa thuộc registry
- **THEN** apply SHALL từ chối và nêu xung đột, không chuyển policy hoặc sửa lịch sử agent cũ

#### Scenario: Thay đổi chế độ nhận diện
- **WHEN** operator đổi user_mode hoặc reporting_start_date của agent đã đăng ký
- **THEN** apply SHALL từ chối trước khi ghi và yêu cầu quy trình migration riêng

### Requirement: Giữ lịch sử khi ngừng hoặc bỏ khai báo
Apply SHALL giữ agent đã đăng ký nếu entry biến mất khỏi file và báo retained. `active=false` SHALL đánh dấu không hoạt động nhưng không xóa dữ liệu hoặc chặn nạp log đến muộn, không thu hồi Gateway key.

#### Scenario: Entry bị xóa khỏi YAML
- **WHEN** apply chạy trên file không còn chứa agent từng đăng ký
- **THEN** agent, mapping và facts SHALL còn nguyên và CLI SHALL cảnh báo retained

#### Scenario: Log đến muộn
- **WHEN** agent active=false có một log hợp lệ mới hoặc đến muộn trong phạm vi ngày
- **THEN** loader SHALL vẫn nạp đúng danh tính và giữ trạng thái inactive

### Requirement: Cấu hình Docker và bảo vệ luồng legacy
Service dùng để apply SHALL đọc cùng file operator sửa qua mount thư mục read-only. Refresh SHALL dùng registry trong DB, không phụ thuộc file YAML hay exports mỗi vòng. Khi đã có registry rows, các bulk loader có thể xóa registry-owned dữ liệu SHALL từ chối trước mutation/migration.

#### Scenario: Thay file YAML trên host
- **WHEN** operator thay YAML bằng atomic save rồi chạy container one-off apply
- **THEN** CLI SHALL đọc phiên bản mới mà không cần rebuild image chỉ vì đổi cấu hình

#### Scenario: Refresh không có source exports
- **WHEN** registry đã áp dụng và không có thư mục data exports hoặc YAML trong worker
- **THEN** refresh SHALL nạp được Gateway usage dựa trên DB

#### Scenario: Chạy nhầm org loader hoặc rebuild
- **WHEN** operator chạy destructive legacy loader trên DB có registry-owned agents
- **THEN** lệnh SHALL dừng trước mọi thay đổi, nêu workflow thay thế, và số liệu/ID/grants SHALL giữ nguyên
