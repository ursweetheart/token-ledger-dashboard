# data-source-registry Specification

## Purpose
TBD - created by archiving change admit-gateway-as-a-fourth-source. Update Purpose after archive.
## Requirements
### Requirement: Nguồn dữ liệu tự khai năng lực, và phép đọc hỏi năng lực chứ không hỏi tên

Mọi truy vấn CẦN chọn dòng theo *"nguồn này biết ai là người dùng không"* SHALL hỏi qua
một khai báo tập trung. MUST NOT so sánh trực tiếp với tên nguồn (`source = 'app'`).

Lý do: đo 21/08/2026 có **24 chỗ** so với chuỗi `'app'` ở 8 file, trong đó **10 chỗ đầu
đọc** dùng tên nguồn để trả lời câu hỏi *"nguồn nào biết người dùng"*. Hai khái niệm này
trùng nhau hôm nay và **tách ra** ngày Gateway xuất hiện, vì Gateway cũng biết người dùng.

#### Scenario: Thêm nguồn thứ tư biết người dùng

- **WHEN** một nguồn mới được khai là `knows_user = TRUE`
- **THEN** mọi phép đọc "quy về người" SHALL tính cả dòng của nguồn đó
- **AND** MUST NOT phải sửa bất kỳ câu SQL nào để điều đó xảy ra

#### Scenario: Nguồn chỉ có tiền, không biết người

- **WHEN** một nguồn khai `knows_user = FALSE, has_cost = TRUE`
- **THEN** dòng của nó SHALL vào tổng tiền
- **AND** MUST NOT vào tử số của chỉ tiêu tỷ lệ áp dụng

#### Scenario: Nguồn lạ lọt vào dữ liệu

- **WHEN** `fact_usage_daily` có một `source` không có dòng trong bảng khai báo
- **THEN** `audit_db.py` SHALL báo hỏng
- **AND** MUST NOT im lặng bỏ qua

### Requirement: `usage_resolved` ưu tiên Gateway trước hoá đơn

Khi một `(ngày, agent, model)` có mặt ở nhiều nguồn, `usage_resolved` SHALL chọn theo thứ
tự `gateway` → `billing` → `monitoring` → `app`, và `token_source` SHALL nói nguồn nào
được chọn.

Lý do: Gateway là bộ đếm của chính ta và có mặt **ngay trong ngày**, trong khi hoá đơn
Google về trễ ~1 ngày. Trong kỳ chạy song song (giai đoạn 7, tối thiểu 2 tuần) cả bốn
nguồn cùng có dữ liệu cho cùng một ngày; nếu không chốt thứ tự thì con số sẽ đổi tuỳ theo
nguồn nào nạp sau.

#### Scenario: Một ngày có cả bốn nguồn

- **WHEN** cùng `(day, agent_id, model_id)` xuất hiện ở `gateway`, `billing`, `monitoring`
  và `app`
- **THEN** `usage_resolved` SHALL trả **đúng một dòng**
- **AND** `token_source` SHALL bằng `'gateway'`

#### Scenario: Tổng không được đổi khi thêm nguồn không có dữ liệu

- **WHEN** `ref_source` có dòng `gateway` nhưng chưa có bản ghi nào
- **THEN** mọi con số trên dashboard SHALL giữ nguyên đến từng đơn vị nhỏ nhất
- **AND** tổng token SHALL vẫn là 867.657.110 (mốc đo 21/08/2026)

### Requirement: Dòng Gateway phải tra ra được một tài khoản

Mỗi dòng `source='gateway'` mang username SHALL tra ra đúng một `account_id`. Dòng không
tra ra được SHALL làm `audit_db.py` báo hỏng.

Lý do: quyết định 21/08 là **không đợi** một token nhân viên thường trước khi viết code —
hình dạng claim đã đo trên tài khoản quản trị (`sub` với Ralli, `username` với Hợp Đồng).
Phép kiểm này là lưới an toàn thay cho việc chờ, và nó bắt được nhiều hơn: agent trích
nhầm claim, app đổi claim sau một lần nâng cấp, hoặc ai đó viết `sub` cho cả hai app.

Hai vế đã đo và trùng khít: `account` (kind='real') có **814/937** username dạng có dấu
chấm và **0/937** dạng ObjectId; Ralli `/users/list` có **814/891** và **0/891**.

#### Scenario: Agent trích nhầm claim

- **WHEN** một dòng `gateway` mang `user-admin` (giá trị claim `sub` của Trợ Lý Ảo Hợp Đồng)
- **THEN** phép kiểm SHALL kêu, nêu rõ username không tra được
- **AND** MUST NOT âm thầm quy dòng đó về "không xác định"

#### Scenario: Agent một-người-dùng

- **WHEN** một dòng `gateway` đến từ một trong 6 agent một-người-dùng
- **THEN** username SHALL là hằng số dạng `svc.<code>`
- **AND** SHALL tra ra dòng `account` có `kind = 'service_account'`

### Requirement: Có một kịch bản nghiệm thu chạy được, không để lại dấu vết

Kho mã SHALL có một kịch bản chèn dữ liệu Gateway giả, chạy toàn bộ phép kiểm, so số
trước/sau, rồi hoàn tác. Kịch bản MUST NOT để lại bất kỳ dòng nào trong database.

Lý do: câu *"đã sẵn sàng đón Gateway chưa"* hôm nay là một ý kiến. Kịch bản này biến nó
thành con số. Và nó chỉ có giá trị nếu dùng username **thật** — bịa `account_id` thì chỉ
chứng minh SQL chạy được, không chứng minh Gateway nối được vào dữ liệu đang có.

#### Scenario: Chạy trước khi sửa code

- **WHEN** kịch bản chạy trên code chưa sửa
- **THEN** nó SHALL báo **TRƯỢT**, liệt kê từng chỗ số không nhúc nhích
- **AND** danh sách đó SHALL là phạm vi thật của change này

#### Scenario: Chạy sau khi sửa xong

- **WHEN** kịch bản chạy trên code đã sửa
- **THEN** `usage_by_account` SHALL có thêm dòng
- **AND** tỷ lệ quy về người SHALL tăng khỏi 12,4%
- **AND** mọi phép kiểm của `audit_db.py` và `check_api.py` SHALL vẫn xanh

#### Scenario: Không để lại dấu vết

- **WHEN** kịch bản kết thúc, dù đạt hay trượt hay gặp lỗi giữa chừng
- **THEN** database SHALL trở về đúng trạng thái trước khi chạy
- **AND** MUST NOT ghi vào database đang phục vụ dashboard mà không hoàn tác
