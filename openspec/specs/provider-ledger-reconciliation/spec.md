# provider-ledger-reconciliation Specification

## Purpose
TBD - created by archiving change stop-treating-a-failed-call-as-a-free-call. Update Purpose after archive.
## Requirements
### Requirement: Sổ Gateway phải đối chiếu được với sổ của chính nhà cung cấp
Hệ thống SHALL giữ số liệu quan sát từ phía nhà cung cấp — số lượt, token vào, token ra theo
ngày — trong một bảng riêng, để so với `fact_call`. Bảng này MUST NOT được `usage_resolved`
hay bất kỳ phép tổng hợp lưu lượng nào đọc: nó là ý kiến thứ hai dùng để đối chiếu, không
phải một nguồn để cộng vào tổng.

#### Scenario: Bảng nhà cung cấp không lọt vào tổng lưu lượng
- **WHEN** `usage_resolved` được dựng lại
- **THEN** tổng token của nó SHALL không đổi so với trước khi bảng nhà cung cấp có dữ liệu

#### Scenario: Project của Gateway không phải một agent
- **WHEN** một project chỉ dùng để quan sát Gateway được nạp vào
- **THEN** nó SHALL được lưu theo mã project, và MUST NOT sinh thêm dòng nào trong `dim_agent`

### Requirement: Đối chiếu phải so trên cả ba trục, ở mức ngày
Phép kiểm SHALL so `fact_call` với sổ nhà cung cấp trên **số lượt**, **token vào** và
**token ra**, và SHALL so ở mức ngày. Không được so ở mức giờ, vì nhà cung cấp gắn nhãn ô
theo thời điểm kết thúc còn sổ Gateway ghi theo thời điểm bắt đầu, nên một lượt vắt qua
ranh giới giờ sẽ rơi vào hai ô khác nhau ở hai sổ.

#### Scenario: Chỉ khớp token nhưng lệch số lượt
- **WHEN** token của hai sổ khớp nhau nhưng số lượt lệch
- **THEN** phép kiểm SHALL báo lệch, MUST NOT coi việc khớp một trục là đủ

#### Scenario: Lượt vắt qua ranh giới giờ
- **WHEN** một lượt bắt đầu ở giờ trước và kết thúc ở giờ sau
- **THEN** phép kiểm SHALL vẫn tính nó vào đúng một ngày ở cả hai sổ

### Requirement: Ngưỡng phải một chiều, vì chiều ngược lại là bất khả
Phép kiểm SHALL báo HỎNG khi sổ Gateway khai **nhiều hơn** sổ nhà cung cấp, ở bất kỳ trục
nào — ta không thể ghi nhiều lượt hơn số lượt nhà cung cấp đã phục vụ, cũng không thể tiêu
nhiều token hơn số token họ đã bán. Khi sổ nhà cung cấp nhiều hơn, phép kiểm SHALL ghi một
lưu ý kèm **con số chênh lệch**, và MUST NOT báo hỏng: đó là khoản thiếu hụt đã biết, và
đo nó chính là mục đích của phép kiểm.

#### Scenario: Gateway khai nhiều hơn nhà cung cấp
- **WHEN** số lượt hoặc số token trong `fact_call` lớn hơn của nhà cung cấp trong cùng ngày
- **THEN** phép kiểm SHALL báo HỎNG

#### Scenario: Nhà cung cấp nhiều hơn Gateway
- **WHEN** nhà cung cấp ghi nhiều token hơn `fact_call` trong cùng ngày
- **THEN** phép kiểm SHALL ghi lưu ý kèm con số chênh lệch tuyệt đối và tỷ lệ, và SHALL
  không báo hỏng

#### Scenario: Không đặt ngưỡng phần trăm hậu nghiệm
- **WHEN** ai đó muốn thêm một ngưỡng phần trăm cho chiều thiếu hụt
- **THEN** ngưỡng đó SHALL được ban hành trước một kỳ đo mới, MUST NOT được chọn theo kết quả
  đã biết của kỳ đo cũ

### Requirement: Không có ngày giao nhau thì phải nói ra
Khi không có ngày nào mà cả `fact_call` lẫn sổ nhà cung cấp cùng có dữ liệu, phép kiểm SHALL
báo *chưa kiểm được* và SHALL in ra khoảng ngày của từng sổ. Nó MUST NOT báo đạt.

#### Scenario: Hai sổ không giao nhau ngày nào
- **WHEN** sổ Gateway phủ một khoảng ngày và sổ nhà cung cấp phủ một khoảng khác, không giao nhau
- **THEN** phép kiểm SHALL báo chưa kiểm được, kèm hai khoảng ngày và số ngày giao nhau bằng 0

#### Scenario: Có ngày giao nhau
- **WHEN** hai sổ cùng có dữ liệu ở ít nhất một ngày
- **THEN** phép kiểm SHALL nêu số ngày đã đối chiếu như mẫu số của kết luận

### Requirement: Khoản thiếu hụt do loại lượt hỏng MUST NOT bị suy đoán
Hệ thống MUST NOT gán, nội suy hay phân bổ token cho lượt gọi mà sổ ghi bằng không. Chênh
lệch giữa hai sổ SHALL được báo cáo ở mức **tổng theo ngày**, vì đó là mức duy nhất có bằng
chứng; quy nó về từng lượt gọi là bịa số.

#### Scenario: Có người muốn điền số cho lượt hỏng
- **WHEN** biết tổng chênh lệch của một ngày
- **THEN** hệ thống MUST NOT viết số đó vào bất kỳ dòng nào của `fact_call`

### Requirement: Token suy nghĩ phải truy ra được nằm ở đâu trong hoá đơn

Hệ thống SHALL xác định được token suy nghĩ rơi vào loại token nào của hoá đơn nhà cung cấp, và phép xác định đó MUST NOT dựa trên việc hai con số tổng gần nhau.

Lý do: bảng giá của nhà cung cấp có SKU mang thẳng chữ `non-thinking` trong tên, nên bảng giá đó CÓ phân biệt suy nghĩ. Nhưng bảng phân loại của ta chỉ có ba loại `input` / `output` / `cached`. Nếu token suy nghĩ về dưới một SKU bị xếp sai loại thì tổng token của dashboard sai, mà không phép kiểm nào hiện có phát hiện được.

#### Scenario: Một SKU nhắc tới suy nghĩ xuất hiện trong hoá đơn

- **WHEN** hoá đơn có một SKU mà tên nhắc tới suy nghĩ
- **THEN** SKU đó SHALL được xếp vào đúng loại token mà nhà cung cấp tính tiền
- **AND** việc xếp loại SHALL tra được về một dòng trong bảng ánh xạ, MUST NOT suy từ tên SKU

#### Scenario: Kết luận dựa trên hai con số tổng

- **WHEN** hai nguồn cho hai con số tổng gần nhau
- **THEN** điều đó MUST NOT được coi là bằng chứng hai bên đang đo cùng một thứ
- **AND** phép đối chiếu SHALL được ghép ở mức chi tiết hơn tổng, ít nhất là theo ngày

#### Scenario: Phần lệch không giải thích được

- **WHEN** phép đối chiếu còn một phần lệch mà chưa ai giải thích được
- **THEN** phần đó SHALL được ghi lại thành con số
- **AND** MUST NOT được làm tròn đi hay mô tả bằng chữ "không đáng kể"

### Requirement: SKU chưa biết MUST NOT rơi âm thầm

Đường nạp hoá đơn SHALL dừng khi gặp một SKU chưa có trong bảng ánh xạ, và MUST NOT bỏ qua, đoán, hay gán một giá trị mặc định cho nó.

Lý do: đây là lớp bảo vệ duy nhất ngăn một loại token mới rơi ra ngoài mà không ai biết. Cùng hạng lỗi với lần mất 26% token vì cache ngày 15/08. Khác ở chỗ lần này việc dừng là CỐ Ý và là hành vi đúng — giống phép đối chiếu của đường nạp Gateway, thứ đã dừng đúng lúc ngày 11/09 khi hai dòng trúng cache không được đếm vào đâu.

#### Scenario: Hoá đơn có SKU chưa khai

- **WHEN** một mã SKU chưa có trong bảng ánh xạ xuất hiện trong dữ liệu hoá đơn
- **THEN** đường nạp SHALL dừng và nêu tên SKU đó
- **AND** MUST NOT ghi dòng nào của lượt nạp đó vào bảng đích

#### Scenario: Lớp bảo vệ này KHÔNG bắt được lỗi xếp sai loại

- **WHEN** một SKU đã có trong bảng ánh xạ nhưng bị gán sai loại token
- **THEN** đường nạp SHALL chạy bình thường
- **AND** việc phát hiện SHALL dựa vào một phép soát bảng ánh xạ riêng, MUST NOT trông chờ vào việc đường nạp tự dừng

