## ADDED Requirements

### Requirement: Xem identity Gateway và usage trong dashboard
Hệ thống SHALL có endpoint read-only có xác thực `/api/gateway-identities` và bảng định danh Gateway theo agent trên UI. Endpoint SHALL hỗ trợ filter agent/date và pagination, trả external ID dễ đọc, account_id, agent, kind/provenance, first/last seen; không trả API key hoặc internal encoded username làm tên hiển thị. Single service account SHALL xem được cùng usage của nó.

#### Scenario: Hai người dùng một agent
- **WHEN** agent multiple có calls của Alice và Bob
- **THEN** UI SHALL hiển thị hai identity riêng cùng usage tương ứng, không cần account directory

#### Scenario: Không có quyền đọc API
- **WHEN** client gọi endpoint thiếu/sai dashboard credential
- **THEN** endpoint SHALL từ chối theo cơ chế xác thực API hiện hữu

#### Scenario: Đổi filter
- **WHEN** operator chọn agent hoặc khoảng ngày khác
- **THEN** danh sách identity và usage SHALL dùng cùng filter và không lẫn usage agent khác

#### Scenario: Agent chưa gọi
- **WHEN** agent được đăng ký nhưng chưa có log
- **THEN** UI SHALL hiển thị agent cùng trạng thái chưa có dữ liệu, không báo lỗi import

### Requirement: Không coi identity đã quan sát là nhân viên đã cấp quyền
Gateway-observed accounts MUST NOT lọt vào `/api/accounts` chỉ dành cho kind real, hoặc làm tăng mẫu số nhân viên/danh bạ/adoption. Với multiple Gateway-only, API/UI SHALL biểu diễn số identity quan sát riêng; provisioned denominator và adoption rate SHALL là NULL/chưa biết nếu không có danh bạ. Metadata người dùng/phòng ban không được tự suy từ username.

#### Scenario: Tất cả identity đã có request
- **WHEN** 10 identity được khám phá từ logs của agent multiple không có directory
- **THEN** UI SHALL báo 10 định danh đã quan sát và không báo adoption 100% hoặc 0%

#### Scenario: Một observed identity trùng tên nhân viên cũ
- **WHEN** Gateway identity có chuỗi tên bằng account real hiện hữu
- **THEN** danh bạ nhân viên và tài khoản real SHALL không bị sửa/gộp; UI SHALL phân biệt nguồn

### Requirement: Tổng usage và phần chưa quy được phải giữ đúng
Chiều tài khoản SHALL giữ quy tắc chọn nguồn theo từng chỉ tiêu hiện hữu; tổng identity cộng fallback SHALL khớp tổng cùng phạm vi. Cost Gateway nếu hiển thị SHALL lấy từ source Gateway và mang nhãn ước tính, giữ missing khác zero; MUST NOT chia đều tiền hóa đơn cho users. Failure SHALL giữ phân loại hiện tại, không tính thành successful usage.

#### Scenario: Một request thiếu identity
- **WHEN** agent có usage định danh được và usage thiếu X-User
- **THEN** UI SHALL giữ mục chưa quy được và tổng token/calls SHALL không hụt hoặc đếm đôi

#### Scenario: Đồng thời có nhiều nguồn lịch sử
- **WHEN** kiểm hồi quy dữ liệu legacy có billing, monitoring, app và gateway
- **THEN** tổng token và calls resolved của legacy SHALL giữ nguyên, không cộng tất cả nguồn

#### Scenario: Định danh chỉ có lượt lỗi
- **WHEN** identity mới chỉ có failed calls
- **THEN** identity SHALL xuất hiện với provenance đã quan sát trong danh sách phù hợp phạm vi request, nhưng SHALL không được tính là người có successful usage
