# provider-ledger-reconciliation

## ADDED Requirements

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
