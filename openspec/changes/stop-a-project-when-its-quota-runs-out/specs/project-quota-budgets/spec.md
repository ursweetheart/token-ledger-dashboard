## ADDED Requirements

### Requirement: Hạn mức là số do người nhập, không tự sinh và không tự reset

Mỗi project SHALL có nhiều nhất một hạn mức đang hiệu lực, và giá trị đó SHALL chỉ đến từ thao tác
nhập của người quản trị. Hệ thống MUST NOT tự đặt, tự suy ra, hay tự làm mới hạn mức theo chu kỳ
thời gian.

Lý do: "hết là hết" — hết thì người nạp thêm, chứ không phải sang tháng tự có tiền lại. Một hạn mức
tự hồi phục sẽ che mất chính sự kiện đáng để ý nhất.

#### Scenario: Chưa ai nhập hạn mức cho một project
- **WHEN** một project chưa có hạn mức nào
- **THEN** hệ thống SHALL coi project đó là **không đặt hạn mức**
- **AND** MUST NOT chặn lưu lượng của project đó

#### Scenario: Sang tháng mới
- **WHEN** đồng hồ bước sang tháng mới, hoặc sang năm mới
- **THEN** hạn mức và số đã tiêu của mọi project SHALL giữ nguyên
- **AND** MUST NOT có bất kỳ giá trị nào được đặt lại

#### Scenario: Nhập một giá trị không hợp lệ
- **WHEN** giá trị nhập vào là số âm, là chuỗi không phải số, hoặc rỗng
- **THEN** hệ thống SHALL từ chối và giữ nguyên hạn mức cũ
- **AND** SHALL nói rõ giá trị nào bị từ chối và vì sao

### Requirement: Hạn mức lưu cạnh khoá, không lưu trong bảng riêng

Hạn mức và lịch sử nạp SHALL lưu trong phần ghi chú tự do của chính virtual key mà agent dùng, và
SHALL sửa được bằng lệnh quản lý khoá sẵn có của Gateway. Hệ thống MUST NOT dựng bảng mới trong
database nào cho việc này, và MUST NOT cấp thêm quyền ghi database cho backend.

Lý do: dựng bảng kéo theo migration, một vai database mới, một mục trong danh sách giữ-khi-dựng-lại,
và một kết nối thứ hai cho tiến trình thi hành. Ghi cạnh khoá thì không cần gì trong số đó, và số
đã tiêu cũng đã có sẵn ở đó.

#### Scenario: Đặt hạn mức cho một project
- **WHEN** người quản trị đặt hạn mức
- **THEN** giá trị SHALL nằm trong phần ghi chú của virtual key tương ứng
- **AND** MUST NOT có bảng database nào được tạo hay ghi cho việc đó

#### Scenario: Khoá vẫn hoạt động bình thường sau khi ghi hạn mức
- **WHEN** hạn mức được ghi vào phần ghi chú của khoá
- **THEN** khoá đó SHALL vẫn gọi được như trước
- **AND** tag định danh của nó SHALL vẫn lọc đúng tuyến

#### Scenario: Một project có nhiều hơn một khoá
- **WHEN** một project có từ hai virtual key trở lên
- **THEN** giao diện SHALL nói rõ hạn mức chỉ áp cho từng khoá, không cộng gộp cả project
- **AND** MUST NOT hiển thị một con số gộp như thể nó đang được thi hành

### Requirement: Mỗi lần nạp để lại một dòng lịch sử không bị ghi đè

Mỗi thao tác đặt hoặc nạp thêm hạn mức SHALL ghi một dòng lịch sử gồm: giá trị trước, giá trị sau,
thời điểm, và chứng danh của người thao tác. Thao tác sau MUST NOT xoá hay sửa dòng lịch sử của
thao tác trước.

Lý do: hạn mức chỉ giữ con số **hiện tại**. Sửa 50 thành 80 là đè mất số cũ, và câu hỏi "tháng này
project đó nạp mấy lần" sẽ không ai dựng lại được.

#### Scenario: Nạp thêm cho một project đã hết
- **WHEN** người quản trị nâng hạn mức của một project từ 50 lên 80
- **THEN** SHALL có một dòng lịch sử mới ghi 50 → 80 kèm thời điểm
- **AND** hạn mức hiệu lực SHALL là 80

#### Scenario: Hạ hạn mức xuống dưới mức đã tiêu
- **WHEN** hạn mức mới thấp hơn số project đó đã tiêu
- **THEN** hệ thống SHALL chấp nhận và ghi lịch sử như mọi thao tác khác
- **AND** project đó SHALL rơi ngay vào trạng thái đã vượt

#### Scenario: Xem lại lịch sử nạp
- **WHEN** người quản trị mở lịch sử của một project
- **THEN** SHALL thấy mọi lần nạp theo thứ tự thời gian
- **AND** MUST NOT có lần nạp nào bị thiếu vì đã bị thao tác sau ghi đè

### Requirement: Danh sách project lấy từ database, và nói rõ project nào không thi hành được

Màn hình nhập hạn mức SHALL lấy danh sách project từ database chứ không từ một danh sách viết cứng.
Với project mà hạn mức không thi hành được, màn hình SHALL nói rõ điều đó tại chỗ, chứ MUST NOT chỉ
hiện một ô nhập trông giống hệt các ô khác.

Lý do: Gateway chỉ chặn được lưu lượng đi qua nó. Một ô nhập cho project không đi qua Gateway trông
y hệt ô có tác dụng thật — người nhập sẽ tin là đã chặn, trong khi không có gì chặn cả.

#### Scenario: Có agent mới được thêm vào danh mục
- **WHEN** một dòng agent mới xuất hiện trong danh mục của database
- **THEN** màn hình nhập SHALL có ô cho project đó mà không phải sửa mã nguồn

#### Scenario: Project của agent chưa nối vào Gateway
- **WHEN** project đó chưa có virtual key nào ở Gateway
- **THEN** màn hình SHALL ghi rõ hạn mức này chỉ để cảnh báo, không chặn được
- **AND** MUST NOT hiển thị nó giống hệt một project chặn được

#### Scenario: Project không có nguồn chi phí từ nhà cung cấp
- **WHEN** một agent không có nguồn dữ liệu chi phí từ Google
- **THEN** màn hình SHALL nói rõ số đã tiêu của project đó luôn bằng 0
- **AND** MUST NOT để người dùng tưởng hạn mức đang được theo dõi

### Requirement: Đường ghi hạn mức chỉ sửa được đúng phần hạn mức

Endpoint ghi hạn mức SHALL chỉ thay đổi được hai khoá ghi chú của khoá: hạn mức và lịch sử nạp.
Mọi khoá ghi chú khác, và mọi trường khác của virtual key, MUST NOT thay đổi được qua đường này.
Backend MUST NOT có endpoint nào chuyển tiếp một lệnh tuỳ ý sang Gateway.

Lý do: để sửa được ghi chú của khoá, backend phải giữ master key của Gateway — khoá mở được mọi
thứ. Một endpoint viết lỏng tay sẽ biến khoá dashboard thành quyền quản trị Gateway.

#### Scenario: Gửi kèm một khoá ghi chú lạ
- **WHEN** yêu cầu ghi hạn mức mang thêm những khoá ghi chú ngoài hai khoá cho phép
- **THEN** hệ thống SHALL bỏ qua chúng
- **AND** phần ghi chú của khoá MUST NOT có thêm khoá nào mới

#### Scenario: Tag định danh còn nguyên sau khi sửa hạn mức
- **WHEN** hạn mức của một khoá được sửa
- **THEN** tag định danh trong ghi chú của khoá đó SHALL giữ nguyên

#### Scenario: Master key không được lộ ra ngoài
- **WHEN** bất kỳ endpoint nào trả lời, kể cả khi trả lỗi
- **THEN** câu trả lời MUST NOT chứa master key của Gateway

#### Scenario: Thiếu master key lúc khởi động
- **WHEN** biến môi trường giữ master key không được đặt
- **THEN** backend SHALL từ chối khởi động và nói rõ thiếu biến nào
- **AND** MUST NOT khởi động ở trạng thái sửa hạn mức được mà không xác thực nổi với Gateway
