## ADDED Requirements

### Requirement: Độ trễ phải hiện một con số duy nhất cho mỗi ngày và agent
Khi nhiều nguồn cùng cho phân vị độ trễ của một ngày và một agent, hệ thống SHALL chọn đúng một
nguồn và trả về một con số. Hệ thống MUST NOT trung bình hoặc cộng phân vị của nhiều nguồn.

#### Scenario: Hai nguồn cùng có phân vị cho một ngày
- **WHEN** hai nguồn cùng cho phân vị của cùng một ngày và cùng một agent
- **THEN** hệ thống SHALL chọn một nguồn theo thứ tự ưu tiên đã chốt
- **AND** MUST NOT tạo ra một con số không thuộc về phép đo nào

#### Scenario: Chỉ một nguồn có phân vị
- **WHEN** chỉ một nguồn có phân vị cho một ngày và một agent
- **THEN** hệ thống SHALL trả về con số của nguồn đó

#### Scenario: Không nguồn nào có phân vị
- **WHEN** không nguồn nào có phân vị cho một ngày và một agent
- **THEN** hệ thống SHALL cho biết là chưa có dữ liệu
- **AND** MUST NOT trả về số không như thể đó là một phép đo

#### Scenario: Kết quả sau khi chọn
- **WHEN** kết quả độ trễ được trả về
- **THEN** SHALL có đúng một dòng cho mỗi cặp ngày và agent

### Requirement: Việc chọn nguồn độ trễ phải xảy ra ở tầng dữ liệu
Việc chọn nguồn SHALL diễn ra trong dữ liệu trả về, không phải ở tầng hiển thị. Tầng hiển thị
MUST NOT phải phân giải giữa nhiều dòng của cùng một khoá.

#### Scenario: Tầng hiển thị nhận dữ liệu độ trễ
- **WHEN** tầng hiển thị nhận kết quả độ trễ
- **THEN** mỗi khoá SHALL chỉ có một giá trị
- **AND** tầng hiển thị MUST NOT quyết định giữ giá trị nào khi có nhiều giá trị

#### Scenario: Truy vết nguồn đã chọn
- **WHEN** một phép kiểm cần biết nguồn nào đã được chọn
- **THEN** nguồn đó SHALL tra được ngay trong dữ liệu trả về

#### Scenario: Con số hiển thị cho người xem
- **WHEN** độ trễ được hiện lên màn hình
- **THEN** SHALL hiện con số, và MUST NOT kèm nhãn nguồn

### Requirement: Phân vị tính từ số thô MUST NOT mang sai số của histogram
Với nguồn lưu độ trễ thô của từng lượt gọi, phân vị SHALL tính trực tiếp từ các giá trị đó, và
các trường mô tả sai số nội suy histogram SHALL để rỗng.

#### Scenario: Nguồn có độ trễ thô từng lượt
- **WHEN** một nguồn lưu độ trễ của từng lượt gọi
- **THEN** phân vị SHALL tính trực tiếp từ các giá trị đó
- **AND** các trường mô tả bề rộng ô histogram SHALL để rỗng

#### Scenario: Nguồn chỉ có histogram đã gộp
- **WHEN** một nguồn chỉ cho histogram đã gộp
- **THEN** các trường mô tả bề rộng ô SHALL giữ nguyên giá trị của nó
- **AND** phép kiểm về quan hệ giữa phân vị và ô chứa nó SHALL tiếp tục áp dụng được

#### Scenario: Trường sai số không áp dụng
- **WHEN** một trường mô tả sai số không áp dụng cho nguồn của dòng đó
- **THEN** trường ấy SHALL để rỗng
- **AND** MUST NOT ghi số không, vì số không nghĩa là đã đo và bằng không

### Requirement: Thứ tự ưu tiên nguồn độ trễ phải chốt ở một chỗ duy nhất
Thứ tự ưu tiên giữa các nguồn độ trễ SHALL nằm ở một chỗ duy nhất, đổi được mà không phải sửa
nơi khác. Thứ tự này MUST NOT nằm rải ở tầng đọc hoặc tầng hiển thị.

#### Scenario: Đổi thứ tự ưu tiên
- **WHEN** thứ tự ưu tiên giữa các nguồn cần đổi
- **THEN** việc đổi SHALL chỉ động vào một chỗ
- **AND** tầng đọc và tầng hiển thị MUST NOT phải sửa theo

#### Scenario: Thứ tự ưu tiên chưa có cơ sở đo đạc
- **WHEN** chưa chứng minh được nguồn nào phản ánh đúng hơn
- **THEN** thứ tự đang dùng SHALL được ghi rõ là tạm thời
- **AND** SHALL nêu phép đo nào sẽ trả lời câu đó

#### Scenario: Con số đang hiển thị khi thứ tự ưu tiên còn tạm
- **WHEN** thứ tự ưu tiên còn ở trạng thái tạm
- **THEN** con số đang hiển thị trước thay đổi SHALL giữ nguyên
- **AND** con số đổi giá trị SHALL bị coi là dấu hiệu chọn sai nguồn
