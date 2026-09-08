# gateway-ledger-loading Specification

## Purpose
TBD - created by archiving change load-the-gateway-ledger-into-the-database. Update Purpose after archive.
## Requirements
### Requirement: Sổ Gateway phải đi được vào database của dashboard
Hệ thống SHALL có một bộ nạp đưa các lượt gọi đã ghi trong `LiteLLM_SpendLogs` vào bảng lượt
gọi của dashboard, để lưu lượng qua Gateway hiển thị được cùng ba nguồn cũ. Bộ nạp MUST NOT
sửa đổi sổ gốc dưới bất kỳ hình thức nào — sổ Gateway là bằng chứng gốc và chỉ được đọc.

#### Scenario: Nạp lượt gọi thành công
- **WHEN** bộ nạp chạy trên một sổ Gateway có ít nhất một lượt gọi thành công
- **THEN** mỗi lượt gọi thành công SHALL sinh đúng một dòng trong bảng lượt gọi, mang đủ
  số token vào, ra và tổng đúng như trong sổ gốc

#### Scenario: Chạy lại nhiều lần
- **WHEN** bộ nạp chạy lần thứ hai trên cùng một sổ không có lượt gọi mới
- **THEN** số dòng trong bảng lượt gọi SHALL không đổi, và bộ nạp MUST NOT nhân đôi dữ liệu

#### Scenario: Gateway đang tắt
- **WHEN** bộ nạp chạy mà không kết nối được tới sổ Gateway
- **THEN** nó SHALL báo lỗi rõ ràng và dừng, và MUST NOT kết thúc thành công với 0 dòng nạp

### Requirement: Lượt gọi hỏng phải bị loại nhưng vẫn được đếm
Bộ nạp SHALL nạp mọi lượt gọi của sổ nguồn kèm kết cục của chúng, và lượt hỏng MUST NOT đóng
góp vào lưu lượng thật ở bảng tổng hợp theo ngày. Câu cũ *"chỉ nạp lượt gọi có trạng thái
thành công"* đã lạc hậu từ migration 006 — đo được 04/09/2026: `fact_call` nguồn gateway ngày
31/08 chứa **3 dòng hỏng** bên cạnh 38 dòng thành công, và `fact_usage_daily` ghi 38 calls.

Đếm **số lượng** lượt hỏng là chưa đủ. Một dòng hỏng có thể mang token thật mà sổ ghi bằng 0,
nên số lượt hỏng không nói được gì về lượng token đã mất. Báo cáo của lần chạy SHALL nêu số
lượt hỏng **kèm số token mà sổ ghi cho chúng**, và SHALL nói rõ rằng con số ấy là *điều sổ
khai*, không phải *điều đã tiêu*.

Bộ nạp SHALL đếm và in ra **số bản ghi của sổ nguồn mà nó không nạp được**, kèm tổng token của
chúng và lý do từng nhóm. Bản ghi rơi mất trong im lặng MUST NOT được chấp nhận: đo được
05/09/2026 trên **toàn sổ** có **6 bản ghi** không vào được `fact_call`, mang tổng **760
token** — trong đó một bản ghi là lượt **thành công mang 25 token** — và trước change này
không phép kiểm nào phát hiện ra. Riêng ngày 31/08 phần đó là 3 bản ghi / 39 token.

Nguyên nhân **đã chứng minh, không phải suy đoán**: cả 6 bản ghi đều **không có tag nào khớp
`dim_agent.code`**, và `fact_call.agent_id` là `NOT NULL`. Nhận định trước đó — *"một bản ghi
là lượt thành công **có tag định danh đầy đủ**"* — là **SAI**: nó đếm mọi tag, kể cả
`User-Agent:` do LiteLLM tự thêm. Chạy lại với mốc nạp rút hẳn (`--full`) vẫn cho `inserted 0`,
nên hai giả thuyết *mốc nước* và *ranh giới ngày* đều **bị bác bỏ**.

Đây là một **khoản nợ đã biết, chưa trả**: lưu lượng không quy được về agent nào cũng không
phải lưu lượng miễn phí — cùng hình dạng lỗi với `failed_is_not_free`, chỉ khác trục. Sửa được
nó cần một agent "không quy được" hoặc `agent_id` cho phép NULL, cả hai đều ngoài phạm vi
change này. Cho tới lúc đó, bộ nạp SHALL nêu khoản nợ ấy ra ở mọi lần chạy.

Bộ nạp SHALL loại **tường minh** những bản ghi mà sổ nguồn tự nhân đôi. Đo được: LiteLLM ghi
thêm một dòng cho cú cache hit, mang chính `request_id` của dòng gốc cộng hậu tố
`_cache_hit<epoch>` và **lặp lại nguyên token** (1 dòng, 352 token, dòng gốc tồn tại với đúng
352 token; nhà cung cấp xác nhận độc lập rằng ngày đó họ phục vụ 1 lượt). Bản sao ấy MUST NOT
được loại nhờ một điều kiện chẳng liên quan — hôm nay nó rớt vì thiếu tag định danh, nên ngày
nào khâu định danh được nới ra thì nó sẽ theo cùng cửa đó mà vào và đếm đôi, trong khi tổng
vẫn "khớp sổ nguồn" vì chính sổ nguồn đã đếm đôi.

#### Scenario: Sổ có lẫn lượt gọi hỏng
- **WHEN** sổ chứa cả lượt gọi thành công và lượt gọi hỏng
- **THEN** cả hai SHALL vào bảng lượt gọi kèm kết cục, chỉ lượt thành công SHALL đóng góp vào
  bảng tổng hợp theo ngày, và báo cáo của lần chạy SHALL nêu số lượt hỏng

#### Scenario: Bản ghi nguồn không nạp được
- **WHEN** một bản ghi của sổ nguồn không vào được bảng lượt gọi vì bất kỳ lý do gì
- **THEN** báo cáo của lần chạy SHALL nêu số bản ghi đó, tổng token của chúng và lý do, và
  MUST NOT bỏ qua trong im lặng

#### Scenario: Điều kiện lọc dựa trên giá trị đo được
- **WHEN** bộ nạp xác định một dòng là thành công
- **THEN** nó SHALL so trạng thái với giá trị thật mà sổ ghi, và MUST NOT giả định trạng thái
  thành công được biểu diễn bằng giá trị rỗng

#### Scenario: Báo cáo nêu cả token của lượt hỏng
- **WHEN** lần chạy loại ra một số lượt hỏng
- **THEN** báo cáo SHALL in cả số lượt lẫn tổng token mà sổ ghi cho những lượt đó

#### Scenario: Lượt hỏng ghi 0 token và 0 mili-giây
- **WHEN** một lượt hỏng mang 0 token và 0 mili-giây trong sổ
- **THEN** bộ nạp MUST NOT kết luận rằng lượt đó chưa tới nhà cung cấp, vì hai giá trị ấy là
  điều sổ khai chứ không phải điều đã đo

#### Scenario: Bản ghi bị sổ nguồn nhân đôi
- **WHEN** sổ nguồn chứa hai bản ghi cho cùng một lượt gọi, bản thứ hai mang `request_id` của
  bản gốc kèm hậu tố và lặp lại nguyên token
- **THEN** bộ nạp SHALL loại bản sao đó **theo đúng lý do là bản sao**, đếm nó riêng, và MUST
  NOT dựa vào một điều kiện lọc khác tình cờ cũng loại nó

#### Scenario: Lưu lượng không quy được về agent nào
- **WHEN** một bản ghi thành công mang token thật nhưng không có tag nào khớp một agent
- **THEN** bộ nạp SHALL nêu nó ra kèm token, và MUST NOT để lần chạy trông như đã nạp trọn vẹn

### Requirement: Thời điểm phải quy về giờ Việt Nam mà vẫn giữ được bản gốc
Thời điểm trong sổ Gateway không mang múi giờ và được ghi theo UTC. Bộ nạp SHALL lưu đồng thời
thời điểm gốc nguyên vẹn và thời điểm đã quy về giờ Việt Nam, và SHALL đánh dấu rằng múi giờ
gốc đã được xác nhận.

#### Scenario: Lượt gọi sau 17 giờ Việt Nam
- **WHEN** một lượt gọi xảy ra sau 17 giờ giờ Việt Nam, tức là đã sang ngày hôm sau theo lịch
  Việt Nam nhưng vẫn là ngày hôm trước theo UTC
- **THEN** thời điểm đã quy đổi SHALL rơi đúng vào ngày theo lịch Việt Nam

#### Scenario: Kiểm lại về sau
- **WHEN** cần đối chiếu lại một dòng đã nạp với sổ gốc
- **THEN** thời điểm gốc SHALL còn nguyên trong bảng lượt gọi, chưa bị quy đổi đè lên

### Requirement: Khâu nối chiều dữ liệu hỏng phải lộ ra, không được im lặng
Khi một lượt gọi không quy được về agent hoặc về model, bộ nạp MUST NOT âm thầm bỏ dòng đó.
Số dòng không quy được SHALL được đếm theo từng loại và in ra ở mỗi lần chạy.

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

### Requirement: Trường thiếu phải nạp rỗng, không được nạp số không
Khi sổ Gateway không cung cấp một giá trị, bộ nạp SHALL lưu giá trị rỗng. Nó MUST NOT thay
bằng số không, vì số không là một số đo thật và trộn hai thứ đó lại làm sai mọi phép trung bình.

#### Scenario: Không có số token đọc từ bộ nhớ đệm
- **WHEN** một lượt gọi không có thông tin về token đọc từ bộ nhớ đệm
- **THEN** cột tương ứng SHALL để rỗng, và số dòng rỗng SHALL được in ra ở báo cáo

#### Scenario: Không xác định được người dùng cuối
- **WHEN** một lượt gọi không mang định danh người dùng cuối
- **THEN** cột người dùng SHALL để rỗng, và bộ nạp MUST NOT tự gán một nhãn thay thế

### Requirement: Chi phí lấy từ Gateway phải được ghi nhãn là ước tính
Mọi chỗ hiển thị số tiền có nguồn gốc Gateway SHALL mang nhãn cho biết đó là số ước tính, vì
số tiền do Gateway tính ra đến từ bảng giá nội bộ của nó chứ không phải từ hoá đơn của nhà
cung cấp.

#### Scenario: Hiển thị chi phí nguồn Gateway
- **WHEN** dashboard hiển thị chi phí của dữ liệu có nguồn là Gateway
- **THEN** số đó SHALL kèm nhãn ước tính, và MUST NOT trình bày lẫn lộn với số lấy từ hoá đơn
  như thể cùng độ tin cậy

#### Scenario: Bảng giá có chiết khấu hoặc phụ phí
- **WHEN** số tiền của Gateway đã bị áp thêm chiết khấu hoặc phụ phí khác không
- **THEN** bộ nạp SHALL dừng và báo, vì khi đó giá trị tổng không còn là giá gốc của nhà cung cấp

