# hourly-time-series Specification

## Purpose
TBD - created by archiving change fill-the-declared-fields-and-log-by-the-hour. Update Purpose after archive.
## Requirements
### Requirement: Lưu lượng phải tổng hợp được theo giờ
Hệ thống SHALL cung cấp số liệu sử dụng ở độ mịn theo giờ cho mọi nguồn ghi được thời điểm của
từng lượt gọi. Độ mịn theo giờ SHALL nằm ở một bảng riêng, và MUST NOT trộn chung một bảng với
số liệu theo ngày.

#### Scenario: Nguồn ghi thời điểm từng lượt gọi
- **WHEN** một nguồn lưu thời điểm của từng lượt gọi
- **THEN** số liệu của nguồn đó SHALL tổng hợp được theo giờ

#### Scenario: Tổng theo giờ so với tổng theo ngày
- **WHEN** cộng toàn bộ số liệu theo giờ của một ngày
- **THEN** kết quả SHALL bằng đúng số liệu theo ngày của ngày đó, cho cùng một nguồn

#### Scenario: Khoá của bảng theo giờ
- **WHEN** bảng theo giờ được dựng
- **THEN** khoá SHALL giữ đủ các chiều mà bảng theo ngày đang có, và MUST NOT rút bớt chiều để
  giảm số dòng

### Requirement: Nguồn không có độ mịn theo giờ MUST NOT bị suy diễn ra giờ
Với nguồn chỉ cung cấp số liệu theo ngày, hệ thống MUST NOT chia nhỏ số liệu đó thành từng giờ.
Bảng theo giờ SHALL cho biết nguồn nào có mặt, để người đọc thấy được nguồn nào vắng.

#### Scenario: Nguồn chỉ có số liệu theo ngày
- **WHEN** một nguồn chỉ cung cấp tổng theo ngày
- **THEN** nguồn đó MUST NOT xuất hiện trong bảng theo giờ với số đã chia đều

#### Scenario: Đọc số liệu theo giờ
- **WHEN** ai đó đọc số liệu theo giờ
- **THEN** nguồn của từng dòng SHALL tra được ngay trong dữ liệu, và MUST NOT chỉ được nêu ở
  tầng hiển thị

### Requirement: Phân vị độ trễ phải giữ nguyên nguồn gốc phép đo
Bảng phân vị độ trễ SHALL phân biệt được phân vị nào tính từ giá trị thô và phân vị nào nội suy
từ histogram đã gộp. Hệ thống MUST NOT đặt hai loại vào cùng một dòng mà không phân biệt được.

#### Scenario: Phân vị tính từ giá trị thô
- **WHEN** một nguồn lưu độ trễ thô của từng lượt gọi
- **THEN** phân vị SHALL tính trực tiếp từ các giá trị đó
- **AND** các trường mô tả sai số của histogram SHALL để rỗng, vì chúng không áp dụng

#### Scenario: Hai nguồn cùng có phân vị cho một ngày
- **WHEN** hai nguồn cùng cho phân vị của cùng một ngày và cùng một agent
- **THEN** mỗi nguồn SHALL giữ một dòng riêng, và MUST NOT bị gộp thành một con số trung bình

#### Scenario: Số mẫu dưới ngưỡng
- **WHEN** một ngày có ít lượt gọi hơn ngưỡng tối thiểu
- **THEN** dòng đó SHALL được đánh dấu là không đủ mẫu, theo đúng ngưỡng đang áp dụng cho các
  nguồn khác

### Requirement: Endpoint đọc theo giờ phải giới hạn khoảng thời gian
Endpoint trả số liệu theo giờ SHALL đòi khoảng thời gian bắt đầu và kết thúc. Hệ thống MUST NOT
trả toàn bộ lịch sử theo giờ cho một lời gọi không nêu khoảng.

#### Scenario: Gọi không nêu khoảng thời gian
- **WHEN** endpoint theo giờ được gọi mà không nêu khoảng thời gian
- **THEN** lời gọi SHALL bị từ chối kèm thông báo nói rõ thiếu gì

#### Scenario: Truy vấn số liệu theo giờ
- **WHEN** endpoint theo giờ phục vụ một lời gọi hợp lệ
- **THEN** mọi câu truy vấn SHALL là chỉ-đọc, đúng kỷ luật đang áp dụng cho các endpoint khác

