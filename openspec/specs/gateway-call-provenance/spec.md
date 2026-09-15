# gateway-call-provenance Specification

## Purpose
TBD - created by archiving change read-the-gateway-columns-we-still-ignore. Update Purpose after archive.
## Requirements
### Requirement: Bản ghi lượt gọi phải giữ tên model như nhà cung cấp nhận được
Bảng lượt gọi SHALL lưu tên model đúng như Gateway nhận được, nguyên văn, bên cạnh mã model đã
ánh xạ. Hệ thống MUST NOT chỉ giữ mã đã ánh xạ, vì khi ánh xạ không ra kết quả thì không còn gì
để tra lại.

#### Scenario: Tên model ánh xạ được
- **WHEN** một lượt gọi mang tên model đã có trong danh mục
- **THEN** lượt đó SHALL được lưu kèm cả tên nguyên văn lẫn mã model

#### Scenario: Tên model chưa có trong danh mục
- **WHEN** một lượt gọi mang tên model mà danh mục chưa khai
- **THEN** mã model SHALL để rỗng, nhưng tên nguyên văn SHALL vẫn được lưu
- **AND** nhờ đó tra được cần khai thêm tuyến nào

#### Scenario: Nguồn không ghi tên model gốc
- **WHEN** dữ liệu đến từ nguồn không cung cấp tên model nguyên văn
- **THEN** cột tên nguyên văn SHALL để rỗng, và MUST NOT được suy ngược từ mã model

### Requirement: Bản ghi lượt gọi phải giữ khoá đã gọi
Bảng lượt gọi SHALL lưu định danh của khoá đã thực hiện lượt gọi, nguyên văn như Gateway ghi.
Hệ thống MUST NOT chuẩn hoá giá trị này về một dạng duy nhất, vì khoá cấp riêng cho agent và
khoá quản trị chung được ghi ở hai dạng khác nhau, và đó chính là điều cần phân biệt.

#### Scenario: Lượt gọi bằng khoá cấp riêng cho agent
- **WHEN** một lượt gọi dùng khoá cấp riêng cho một agent
- **THEN** lượt đó SHALL được lưu kèm định danh khoá đó

#### Scenario: Lượt gọi bằng khoá quản trị chung
- **WHEN** một lượt gọi dùng khoá quản trị chung thay vì khoá cấp riêng
- **THEN** lượt đó SHALL được lưu kèm định danh khoá đó nguyên văn
- **AND** báo cáo của lần chạy SHALL nêu riêng số lượt thuộc loại này, vì chúng chỉ quy được
  về agent bằng nhãn chứ không bằng khoá

### Requirement: Lượt trả từ bộ nhớ đệm MUST NOT cộng vào số liệu sử dụng
Mọi phép tổng hợp lưu lượng và chi phí SHALL loại lượt được trả từ bộ nhớ đệm. Lượt đó MUST NOT
đóng góp token hay tiền, vì nhà cung cấp không thực hiện và không tính tiền lượt đó — dù nó vẫn
là một lượt gọi thành công đối với agent.

Đo 11/09/2026: nguồn ghi lượt trúng đệm thành một dòng mang chính mã yêu cầu của dòng gốc cộng
hậu tố, và **lặp lại nguyên số token** của dòng gốc. Nên cách loại đúng là bỏ ngay ở tầng nạp,
chứ không phải giữ lại rồi lọc lúc tổng hợp. Bản đầu của yêu cầu này viết ngược, và đã sửa cùng
ngày.

#### Scenario: Tổng hợp theo ngày khi có lượt trúng đệm
- **WHEN** bảng tổng hợp theo ngày được dựng lại từ bảng lượt gọi
- **THEN** chỉ lượt thực sự tới nhà cung cấp SHALL đóng góp số token và số tiền

#### Scenario: Lượt trúng đệm là BẢN SAO, không phải bản ghi mới
- **WHEN** nguồn ghi lượt trúng đệm thành một dòng riêng mang lại NGUYÊN số token của dòng gốc
- **THEN** dòng đó MUST NOT được nạp vào bảng lượt gọi
- **AND** lý do SHALL là chống đếm đôi token, không phải vì lượt đó không có thật

#### Scenario: Dòng bị bỏ phải được đếm vào phép đối chiếu
- **WHEN** một dòng bị loại vì là bản sao của lượt trúng đệm
- **THEN** phép đối chiếu toàn sổ SHALL đếm dòng đó vào vế "bị bỏ qua"
- **AND** MUST NOT để nó rơi ra ngoài cả hai vế, vì khi đó phép đối chiếu báo lệch rồi dừng
  hẳn đường nạp

#### Scenario: Đếm tỷ lệ trúng đệm
- **WHEN** cần biết bộ nhớ đệm đang có tác dụng đến đâu
- **THEN** tỷ lệ trúng đệm SHALL lấy từ sổ gốc của Gateway
- **AND** MUST NOT lấy từ bảng lượt gọi, vì dòng trúng đệm đã bị bỏ trước khi tới đó

### Requirement: Trạng thái bộ nhớ đệm phải giữ đủ ba trạng thái
Cột trạng thái bộ nhớ đệm SHALL phân biệt được ba trường hợp: trúng đệm, không trúng đệm, và
không có thông tin. Hệ thống MUST NOT gộp "không có thông tin" thành "không trúng đệm".

#### Scenario: Nguồn không ghi trạng thái đệm
- **WHEN** một lượt gọi đến từ nguồn không ghi trạng thái bộ nhớ đệm
- **THEN** cột đó SHALL để rỗng, và MUST NOT được gán giá trị "không trúng"

#### Scenario: Lọc lượt trúng đệm
- **WHEN** một phép tổng hợp cần loại lượt trúng đệm
- **THEN** phép lọc SHALL giữ lại cả dòng rỗng lẫn dòng không trúng, và MUST NOT loại bỏ dòng
  rỗng như một tác dụng phụ của phép so sánh

#### Scenario: Nguồn đánh dấu "không có thông tin" bằng một giá trị quy ước
- **WHEN** nguồn ghi trạng thái bộ nhớ đệm bằng một giá trị quy ước thay cho ô rỗng
- **THEN** giá trị đó SHALL được quy về rỗng khi nạp, và MUST NOT được lưu như một trạng thái
  thứ tư hay bị nhầm là "không trúng đệm"

