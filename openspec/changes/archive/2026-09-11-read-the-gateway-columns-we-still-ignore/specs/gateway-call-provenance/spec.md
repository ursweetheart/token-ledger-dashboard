## ADDED Requirements

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

> **ĐÃ SỬA Ở BẢN ĐẶC TẢ CHÍNH, 11/09/2026.** Hai kịch bản dưới đây nói rằng dòng trúng đệm
> *"còn tra cứu được trong bảng lượt gọi"* và tỷ lệ trúng đệm *"tính được trực tiếp từ bảng
> lượt gọi"*. Cả hai đều SAI: bộ nạp bỏ dòng đó ngay từ đầu vì nó lặp lại nguyên token của
> dòng gốc. Đọc bản đúng ở `openspec/specs/gateway-call-provenance/spec.md`. Giữ nguyên văn ở
> đây để còn thấy change này đã đề xuất gì.
Mọi phép tổng hợp lưu lượng và chi phí SHALL loại lượt được trả từ bộ nhớ đệm. Lượt đó MUST NOT
đóng góp token hay tiền, vì nhà cung cấp không thực hiện và không tính tiền lượt đó — dù nó vẫn
là một lượt gọi thành công đối với agent.

#### Scenario: Tổng hợp theo ngày khi có lượt trúng đệm
- **WHEN** bảng tổng hợp theo ngày được dựng lại từ bảng lượt gọi
- **THEN** chỉ lượt thực sự tới nhà cung cấp SHALL đóng góp số token và số tiền

#### Scenario: Lượt trúng đệm vẫn mang số token
- **WHEN** một lượt trúng đệm được ghi kèm đầy đủ số token nhưng chi phí bằng không
- **THEN** số token đó MUST NOT được cộng vào lưu lượng, nhưng SHALL còn tra cứu được trong
  bảng lượt gọi

#### Scenario: Đếm tỷ lệ trúng đệm
- **WHEN** cần biết bộ nhớ đệm đang có tác dụng đến đâu
- **THEN** tỷ lệ trúng đệm SHALL tính được trực tiếp từ bảng lượt gọi

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
