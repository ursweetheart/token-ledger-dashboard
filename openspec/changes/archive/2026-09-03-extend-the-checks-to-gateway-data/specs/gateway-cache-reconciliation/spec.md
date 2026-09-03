## ADDED Requirements

### Requirement: Đối chiếu token cache chỉ trên khoảng hai nguồn cùng có dữ liệu
Phép đối chiếu token cache giữa Gateway và hoá đơn nhà cung cấp SHALL chỉ so trên những
ngày mà **cả hai** nguồn đều có dữ liệu. Hệ thống MUST NOT so tổng của hai khoảng thời
gian khác nhau rồi kết luận về chênh lệch.

#### Scenario: Hai nguồn có ngày chung
- **WHEN** tồn tại ngày mà cả hai nguồn đều có dữ liệu
- **THEN** phép đối chiếu SHALL so theo từng cặp ngày và agent trên đúng những ngày đó
- **AND** MUST NOT đưa ngày chỉ một nguồn có vào phép so

#### Scenario: Một nguồn phủ khoảng dài hơn hẳn
- **WHEN** một nguồn có dữ liệu trên nhiều ngày hơn nguồn kia
- **THEN** phần dôi ra MUST NOT được tính vào chênh lệch
- **AND** kết quả SHALL nêu khoảng ngày thực sự đã so

#### Scenario: Báo cáo chênh lệch
- **WHEN** phép đối chiếu tìm thấy chênh lệch vượt ngưỡng
- **THEN** kết quả SHALL nêu từng cặp ngày và agent bị lệch kèm mức lệch
- **AND** MUST NOT chỉ đưa ra một con số tổng

### Requirement: Không đủ dữ liệu để đối chiếu thì phải nói ra, không được báo đạt
Khi phép đối chiếu không có gì để so, hệ thống SHALL báo là **chưa kiểm được** kèm lý do
đo được. Hệ thống MUST NOT báo đạt.

#### Scenario: Hai khoảng ngày rời nhau hoàn toàn
- **WHEN** không có ngày nào cả hai nguồn cùng có dữ liệu
- **THEN** kết quả SHALL là chưa kiểm được
- **AND** SHALL nêu khoảng ngày của **cả hai** nguồn, để người đọc thấy ngay vì sao
- **AND** MUST NOT là kết quả đạt

#### Scenario: Có ngày chung nhưng một vế rỗng
- **WHEN** có ngày chung nhưng nguồn Gateway chưa ghi được token cache nào
- **THEN** kết quả SHALL là chưa kiểm được, nêu rõ vế nào rỗng
- **AND** MUST NOT coi giá trị vắng mặt là bằng không

#### Scenario: Mục kế hoạch phụ thuộc phép đối chiếu này
- **WHEN** một mục kế hoạch lấy phép đối chiếu này làm sản phẩm
- **THEN** mục đó MUST NOT được coi là hoàn thành khi phép đối chiếu chưa kiểm được lần
  nào
- **AND** trạng thái SHALL nêu lý do đo được, không phải nêu tiến độ công việc

### Requirement: Ngưỡng chấp nhận sai lệch phải ban hành trước kỳ đo
Ngưỡng chấp nhận sai lệch SHALL được ghi lại **trước** khi có số đối chiếu đầu tiên, và
SHALL ghi rõ nó là ngưỡng chốt trước hay đã hiệu chỉnh theo số đo.

#### Scenario: Chốt ngưỡng khi chưa có số
- **WHEN** ngưỡng được đặt ra mà chưa có kỳ đo nào
- **THEN** ngưỡng SHALL được ghi kèm ghi chú rằng nó chưa có cơ sở đo đạc

#### Scenario: Số đo đầu tiên vượt ngưỡng
- **WHEN** kỳ đo đầu tiên cho chênh lệch vượt ngưỡng đã chốt
- **THEN** kết quả SHALL là hỏng
- **AND** ngưỡng MUST NOT được nới ra để kết quả thành đạt, trừ khi chứng minh được bản
  thân ngưỡng đặt sai

#### Scenario: Đổi ngưỡng
- **WHEN** ngưỡng được thay đổi
- **THEN** thay đổi SHALL kèm bằng chứng đo đạc cho giá trị mới
