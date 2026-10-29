## ADDED Requirements

### Requirement: Phép kiểm khai bằng cấu hình, không bằng code
Hệ thống SHALL đọc danh sách agent và phép kiểm từ `config/agent-health.yaml`. Thêm một agent dùng kiểu
xác thực và kiểu điều kiện đã có SHALL chỉ cần thêm một khối YAML. Key SHALL đọc từ biến môi trường do
YAML chỉ tên, và YAML SHALL NOT chứa giá trị key.

#### Scenario: Thêm agent mới
- **WHEN** người vận hành thêm một khối agent với `base_url`, `auth.env` và một phép kiểm `GET`
- **THEN** lần chạy kế tiếp SHALL gọi phép kiểm đó và ghi kết quả, không cần sửa file Python nào

#### Scenario: Thiếu biến key
- **WHEN** biến môi trường do `auth.env` chỉ ra không có hoặc rỗng
- **THEN** mọi phép kiểm của agent đó SHALL được ghi `fail` với lý do nêu tên biến bị thiếu
- **AND** SHALL NOT bị bỏ qua im lặng

### Requirement: POST chỉ được gọi khi có trong danh sách trắng
Phép kiểm SHALL chỉ dùng `GET` hoặc `POST`. Một phép kiểm `POST` SHALL chỉ chạy khi path của nó nằm trong
`allow_post` của chính agent đó. Một phép kiểm `POST` SHALL chạy đúng một lần trong mỗi lần chạy, dù lần
chạy đó là theo lịch hay do bấm "Chạy ngay".

#### Scenario: POST không được duyệt
- **WHEN** YAML khai một phép kiểm `POST` có path không nằm trong `allow_post`
- **THEN** service SHALL từ chối khởi động và nêu tên agent cùng path

#### Scenario: Method khác
- **WHEN** YAML khai `PUT`, `PATCH` hoặc `DELETE`
- **THEN** service SHALL từ chối khởi động

### Requirement: Lịch chạy đúng một lần mỗi ngày theo giờ VN đã đặt
Service SHALL đọc `run_at` (giờ VN) và `last_run_date` từ database ở mỗi vòng, không quá 5 giây một
vòng. Khi giờ VN hiện tại đã qua hoặc bằng `run_at` và `last_run_date` khác ngày VN hôm nay, service SHALL
giữ chỗ bằng một `UPDATE` có điều kiện và tạo run `schedule` **trong cùng một transaction**, rồi mới chạy.
Chỉ lần giữ chỗ thành công SHALL chạy.

#### Scenario: Đến giờ
- **WHEN** `run_at = 08:00`, hôm nay chưa chạy, và giờ VN là 08:00:30
- **THEN** service SHALL chạy mọi phép kiểm đúng một lần và đặt `last_run_date` là hôm nay

#### Scenario: Container khởi động lại sau khi đã chạy
- **WHEN** hôm nay đã chạy lúc 08:00 và container khởi động lại lúc 08:05
- **THEN** service SHALL NOT chạy lại hôm nay

#### Scenario: Lỡ giờ
- **WHEN** `run_at = 08:00` và container chỉ lên lúc 09:00 cùng ngày
- **THEN** service SHALL chạy bù ở vòng đầu tiên

#### Scenario: Container chạy giờ UTC
- **WHEN** đồng hồ hệ thống là `2026-10-29T01:00:00Z` và `run_at = 08:00`
- **THEN** service SHALL coi đó là 08:00 giờ VN và chạy

#### Scenario: Đến giờ khi đang có một lần chạy tay
- **WHEN** đến 08:00 trong lúc một run `manual` đang chờ hoặc đang chạy
- **THEN** run `manual` SHALL chạy xong trước
- **AND** run `schedule` của hôm nay SHALL chạy ở vòng ngay sau, không bị mất

#### Scenario: Một lần chạy lỗi
- **WHEN** một phép kiểm ném ngoại lệ ngoài dự kiến
- **THEN** các phép kiểm còn lại SHALL vẫn chạy
- **AND** vòng lặp SHALL tiếp tục

### Requirement: Chạy ngay, độc lập với lịch
`POST /api/agent-health/run` SHALL đòi khoá quản trị kết nối, tạo một run `manual` và trả 202 kèm `id`.
Service SHALL bắt đầu run đó trong vòng kế tiếp, trước khi xét lịch. Run `manual` SHALL NOT đọc hay ghi
`last_run_date`. Tại một thời điểm SHALL có nhiều nhất một run đang chờ hoặc đang chạy, và database SHALL
bảo đảm điều này.

#### Scenario: Bấm trước giờ lịch
- **WHEN** quản trị viên bấm "Chạy ngay" lúc 07:00 và `run_at = 08:00`
- **THEN** mọi phép kiểm SHALL chạy ngay
- **AND** lúc 08:00 lịch SHALL vẫn chạy như thường

#### Scenario: Bấm sau khi lịch đã chạy
- **WHEN** lịch đã chạy lúc 08:00 và quản trị viên bấm "Chạy ngay" lúc 10:00
- **THEN** mọi phép kiểm SHALL chạy lại, kể cả `POST /ctda/v2/analyze`

#### Scenario: Bấm chồng
- **WHEN** đang có một run chờ hoặc chạy và có request `POST /api/agent-health/run` mới
- **THEN** API SHALL trả 409 kèm `id` của run đang có
- **AND** SHALL NOT tạo run mới

#### Scenario: Dùng khoá dashboard
- **WHEN** request `POST /api/agent-health/run` mang khoá dashboard
- **THEN** API SHALL trả 403 và không tạo run

#### Scenario: Service chết giữa lần chạy
- **WHEN** service khởi động lại trong khi một run đang ở `running`
- **THEN** run đó SHALL chuyển sang `interrupted`
- **AND** nút "Chạy ngay" SHALL bấm được trở lại

### Requirement: Tiến độ lần chạy đếm theo phép kiểm
Mỗi run SHALL có `total` (tổng số phép kiểm của mọi agent, tính lúc bắt đầu), `done`, và `current_label`
(tên agent và tên phép kiểm đang chạy). Service SHALL ghi `current_label` trước mỗi phép kiểm và tăng
`done` sau mỗi phép kiểm. `GET /api/agent-health/runs/{id}` SHALL trả các trường này cùng các dòng kết quả đã
có, với chứng danh dashboard.

#### Scenario: Giữa lần chạy Ralli
- **WHEN** `capabilities` đã xong và `llm` đang chờ LLM
- **THEN** run SHALL có `done = 1`, `total = 2`, `current_label` chỉ tới phép kiểm `llm` của Trợ lý ảo Ralli

#### Scenario: Xong
- **WHEN** mọi phép kiểm đã ghi kết quả
- **THEN** run SHALL có `status = done`, `done = total`, và `finished_at` có giá trị

### Requirement: Kết quả có ba mức và đủ bằng chứng
Mỗi phép kiểm SHALL có trong tài liệu kết quả của lần chạy, gồm tên phép kiểm, mức (`ok`, `warn`,
`fail`), mã HTTP, thời gian (ms), lý do, `X-Request-ID` nếu có, và thời điểm gửi theo giờ VN. HTTP 429
SHALL là `warn`. Ngưỡng `days_until` chưa tới SHALL là `warn`. Mọi lỗi khác SHALL là `fail`. Phép kiểm có
câu hỏi (case) SHALL giữ câu hỏi nguyên văn và nguyên response; phép kiểm health SHALL NOT giữ response.
Tài liệu SHALL NOT chứa key hay header xác thực.

#### Scenario: capabilities khỏe
- **WHEN** `GET /capabilities` trả 200, feature `ctda` có `enabled: true`, và `expires_at` còn hơn 30 ngày
- **THEN** phép kiểm SHALL là `ok`

#### Scenario: Key sắp hết hạn
- **WHEN** `expires_at` còn 10 ngày
- **THEN** phép kiểm SHALL là `warn` và lý do SHALL nêu số ngày còn lại

#### Scenario: Câu chào soạn sẵn
- **WHEN** `POST /ctda/v2/analyze` trả 200, `status: "success"`, `data.feature: "clarification"`
- **THEN** phép kiểm `llm` SHALL là `fail` với lý do nêu `data.feature`

#### Scenario: Bị giới hạn
- **WHEN** agent trả 429
- **THEN** phép kiểm SHALL là `warn`

#### Scenario: Lỗi problem+json
- **WHEN** agent trả 503 với `application/problem+json`
- **THEN** phép kiểm SHALL là `fail` và lý do SHALL chứa `title` và `detail`, tối đa 500 ký tự

### Requirement: Một tài liệu kết quả ở cả database và tệp
Mỗi lần chạy SHALL có một tài liệu JSON theo khuôn `docs/reference/agent-health-result.md`, trong cột
`agent_health_run.result`. Khi lần chạy xong, cùng tài liệu đó SHALL được ghi vào
`var/agent-checks/<run_id>/result.json`.

#### Scenario: Lần chạy xong
- **WHEN** mọi phép kiểm đã xong
- **THEN** `result.json` SHALL tồn tại và giống hệt cột `result` của lần chạy đó

#### Scenario: Module chụp màn hình đọc giữa chừng
- **WHEN** service đang ghi `result.json`
- **THEN** người đọc SHALL thấy tệp cũ hoặc tệp đủ, không bao giờ thấy tệp viết dở

#### Scenario: Không ghi được tệp
- **WHEN** thư mục `var/agent-checks` không ghi được
- **THEN** lần chạy SHALL vẫn `done`, và `limitations` trong cột `result` SHALL nêu lý do thiếu tệp

### Requirement: Đối chiếu log Gateway khi agent đã đi qua Gateway
Khi agent khai `gateway_tag`, sau phép kiểm gọi LLM service SHALL tìm trong `LiteLLM_SpendLogs`, qua vai
chỉ-đọc, một dòng có tag đó trong khoảng thời gian của lần gọi. Agent không khai `gateway_tag` SHALL NOT
có phép kiểm này.

#### Scenario: Có dòng log
- **WHEN** có ít nhất một dòng tag `ralli` trong khoảng [bắt đầu − 5 s, kết thúc + 60 s]
- **THEN** phép kiểm `gateway-log` SHALL là `ok`

#### Scenario: Không đọc được log Gateway
- **WHEN** không kết nối được `GATEWAY_DSN`
- **THEN** phép kiểm `gateway-log` SHALL là `fail`, không phải `ok`

### Requirement: Đặt giờ chạy từ dashboard cần khoá quản trị
`PUT /api/agent-health/schedule` SHALL nhận `{"run_at": "HH:MM"}` (00:00–23:59) và SHALL đòi khoá quản trị
kết nối. Khoá dashboard SHALL NOT đủ để đặt giờ.

#### Scenario: Đặt giờ hợp lệ
- **WHEN** quản trị viên gửi `{"run_at": "07:30"}` với khoá quản trị đúng
- **THEN** `agent_health_setting.run_at` SHALL là 07:30
- **AND** service SHALL dùng giờ mới ở vòng kế tiếp, không cần khởi động lại

#### Scenario: Giờ sai định dạng
- **WHEN** body là `{"run_at": "25:00"}` hoặc `{"run_at": "7h"}`
- **THEN** API SHALL trả 422 và không ghi gì

#### Scenario: Dùng khoá dashboard
- **WHEN** request mang khoá dashboard thay vì khoá quản trị
- **THEN** API SHALL trả 403

#### Scenario: Quản trị đang tắt
- **WHEN** `CONNECTIONS_ENABLED` khác `1`
- **THEN** API SHALL trả 503

### Requirement: Tab Sức khỏe Agent hiện kết quả mới nhất
Dashboard SHALL có tab "🩺 Sức khỏe Agent" gồm: ô giờ chạy, nút Apply, nút Chạy ngay, thanh tiến độ ngang,
và bảng kết quả của lần chạy gần nhất cho từng agent, kèm ngày giờ và loại (theo lịch / chạy tay) của lần
chạy đó. Agent SHALL hiện bằng tên hiển thị.

#### Scenario: Theo dõi một lần chạy
- **WHEN** quản trị viên bấm "Chạy ngay"
- **THEN** thanh tiến độ SHALL hiện `done/total` dưới dạng %, kèm `current_label` và số giây đã trôi qua
- **AND** nút "Chạy ngay" SHALL bị tắt cho tới khi run kết thúc
- **AND** khi run kết thúc, bảng SHALL tải lại với kết quả mới

#### Scenario: Mở tab khi đang có run chạy dở
- **WHEN** người xem mở tab trong lúc một run (theo lịch hoặc do người khác bấm) đang chạy
- **THEN** thanh tiến độ SHALL hiện ngay và theo dõi run đó

#### Scenario: Xem kết quả
- **WHEN** người xem mở tab với khoá dashboard hợp lệ
- **THEN** bảng SHALL hiện mỗi phép kiểm một dòng với ✅/⚠️/❌, thời gian (ms) và lý do

#### Scenario: Chưa từng chạy
- **WHEN** `agent_health_run` chưa có lần chạy nào đã kết thúc
- **THEN** tab SHALL nói rõ là chưa có lần chạy nào, không hiện bảng trống không lời

#### Scenario: Thiếu một ngày
- **WHEN** lần chạy gần nhất là từ hôm qua hoặc cũ hơn, trong khi giờ chạy hôm nay đã qua
- **THEN** tab SHALL hiện ngày của lần chạy đó và một cảnh báo rằng hôm nay chưa có kết quả

### Requirement: Dữ liệu sức khỏe sống sót qua rebuild
`agent_health_setting` và `agent_health_run` SHALL nằm trong `KEEP_ON_REBUILD`.

#### Scenario: Dựng lại database
- **WHEN** chạy `scripts/rebuild_db.py` sau khi đã đặt giờ 07:30 và có kết quả
- **THEN** giờ chạy và các dòng kết quả SHALL còn nguyên
