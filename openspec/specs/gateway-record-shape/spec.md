# gateway-record-shape Specification

## Purpose
TBD - created by archiving change measure-what-the-gateway-records. Update Purpose after archive.
## Requirements
### Requirement: Hình dạng bản ghi Gateway phải đo được, không được suy đoán

Hình dạng bản ghi Gateway SHALL được xác lập bằng **một bản ghi thật đã chạy qua
LiteLLM**, không phải bằng suy luận từ tài liệu, và phải có trước khi dự án tạo bảng lưu
bản ghi từng request (`fact_request`).

Lý do: một trường thiếu ở tầng Gateway không gây lỗi — nó chỉ làm cột tương ứng trên
dashboard trống rỗng. Thứ hỏng im lặng phải được bắt bằng đo đạc, không bắt được bằng đọc.

#### Scenario: Có bằng chứng tra lại được

- **WHEN** hỏi *"LiteLLM ghi lại những trường nào cho mỗi request?"*
- **THEN** trả lời được bằng một dòng `LiteLLM_SpendLogs` đã chép ra, kèm ngày đo và
  phiên bản LiteLLM
- **AND** MUST NOT trả lời bằng trích dẫn tài liệu của LiteLLM

#### Scenario: Đối chiếu được hai chiều với hợp đồng dữ liệu

- **WHEN** đọc kết quả đo
- **THEN** mỗi trường trong 25 trường của sheet `Data Out` được đánh dấu **có** / **không
  có** / **tên khác** ở phía LiteLLM
- **AND** những trường LiteLLM ghi mà `Data Out` không có cũng được liệt kê

---

### Requirement: Hai giả định đã ban hành phải được kiểm chứng

Quyết định A3 (20/08/2026) và A5 SHALL được kiểm chứng bằng đo đạc trước khi 8 agent
triển khai theo, vì cả hai đều đứng trên giả định về hành vi của LiteLLM.

| Quyết định | Giả định phải kiểm |
|---|---|
| **A3** | LiteLLM **giữ lại** header danh tính do agent gửi và **ghi nó xuống** bản ghi |
| **A5** | LiteLLM **phơi ra** `thinking_enabled` và `output_modality` |

#### Scenario: Header danh tính sống sót xuống bản ghi

- **WHEN** gửi một request kèm header định danh người dùng
- **THEN** đọc `LiteLLM_SpendLogs` và xác định được giá trị đó **có** hay **không** xuất
  hiện, và nếu có thì nằm ở cột nào
- **AND** nếu **không** xuất hiện, kết quả MUST được ghi lại là phát hiện chặn quy ước A3,
  chứ không được lặng lẽ bỏ qua

#### Scenario: Hai trường của cột "think" được phán quyết

- **WHEN** đọc bản ghi thật
- **THEN** kết luận rõ `thinking_enabled` và `output_modality` **có** nguồn từ Gateway hay
  **không**
- **AND** sheet `Data Out` được sửa theo kết quả đo, không theo dự đoán

---

### Requirement: Phép đo không được chạm vào dữ liệu thật

Môi trường đo SHALL tách rời hoàn toàn khỏi database sản xuất và khỏi 8 project GCP thật,
vì LiteLLM tự chạy migration và tự tạo bảng trong database mà nó được trỏ vào.

#### Scenario: Database của phép đo tách khỏi database dự án

- **WHEN** dựng môi trường đo
- **THEN** LiteLLM trỏ vào một database riêng, trên một cổng riêng, trong một volume riêng
- **AND** MUST NOT trỏ vào `token_ledger` hay bất kỳ database nào của dự án
- **AND** mọi truy vấn tới `token_ledger` trong change này MUST là chỉ-đọc

#### Scenario: Không chiếm cổng của dịch vụ đang chạy

- **WHEN** khởi động môi trường đo trong lúc `token-ledger-postgres` đang chạy
- **THEN** cả hai cùng sống, không cái nào bị dừng hay bị tranh cổng

#### Scenario: Không mở ra ngoài máy

- **WHEN** liệt kê cổng mà môi trường đo phơi ra
- **THEN** mọi cổng đều gắn vào `127.0.0.1`
- **AND** MUST NOT có cổng nào gắn `0.0.0.0`

#### Scenario: Lưu lượng đo nằm ngoài project thật

- **WHEN** request đo được gửi đi
- **THEN** nó tính vào project GCP dành riêng cho thử nghiệm
- **AND** MUST NOT tính vào hạn mức, hoá đơn hay dữ liệu của 8 agent thật

---

### Requirement: Khoá API không được nhân bản

Khoá của nhà cung cấp SHALL tồn tại ở đúng một chỗ trên đĩa.

#### Scenario: Khoá không bị chép sang chỗ thứ hai

- **WHEN** cấu hình LiteLLM dùng khoá
- **THEN** file cấu hình chứa **tham chiếu biến môi trường**, không chứa chuỗi khoá
- **AND** khoá MUST NOT được ghi vào file thứ hai, kể cả trong thư mục bản fork

#### Scenario: Khoá không rơi ra nhật ký

- **WHEN** một phép thử thất bại và in thông báo lỗi
- **THEN** chuỗi khoá được thay bằng chỗ giữ chỗ trước khi in
- **AND** MUST NOT xuất hiện nguyên văn trong bất kỳ đầu ra nào

---

### Requirement: Đo trên model đại diện được cho hệ thống thật

Model dùng để đo SHALL được chọn theo lưu lượng thật đã ghi nhận, không chọn tuỳ tiện.

Đo 24/08/2026 trên `usage_resolved`: `gemini-2.5-flash` chiếm **401.227.817 / 867.657.110
token = 46,2%**, và là model đông nhất mà khoá hiện có gọi được.

#### Scenario: Model đo nằm trong danh mục dự án

- **WHEN** chọn model để gửi request đo
- **THEN** tên model đó có mặt trong `dim_model`
- **AND** nó nằm trong nhóm model chiếm phần lớn lưu lượng thật, không phải model bên lề

#### Scenario: Model không gọi được thì phải ghi lại

- **WHEN** một model chiếm lưu lượng đáng kể mà khoá không gọi được
- **THEN** sự việc được ghi lại kèm số token và tỷ lệ phần trăm
- **AND** MUST NOT bị bỏ qua chỉ vì nó không chặn phép đo hiện tại

