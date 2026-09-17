## ADDED Requirements

### Requirement: Phải có một tiến trình dò Gateway đứng ngoài mọi agent

Hệ thống SHALL có một tiến trình dò tình trạng Gateway theo nhịp, chạy trong một container riêng,
không nằm trong bất kỳ agent nào.

Lý do: thư gửi từ bên trong agent chỉ tồn tại khi agent ấy đang chạy một lô. Gateway chết vào lúc
không agent nào làm việc thì không ai được báo, và sự cố có thể đã qua trước khi có người mở log.
Một chỗ canh đứng ngoài phủ mọi agent, kể cả agent chưa có nhánh dự phòng.

#### Scenario: Gateway chết lúc không agent nào đang chạy

- **WHEN** Gateway không phục vụ được trong khoảng không có agent nào xử lý lô
- **THEN** hệ thống SHALL vẫn gửi thư báo
- **AND** thư SHALL nêu thời điểm phát hiện

#### Scenario: Phép kiểm lúc khởi động

- **WHEN** tiến trình dò vừa khởi động
- **THEN** nhịp dò đầu tiên SHALL chạy ngay, trước khi ngủ lần đầu
- **AND** hệ thống MUST NOT cần một tiến trình riêng chỉ để kiểm lúc khởi động

### Requirement: Ít nhất một phép dò phải đi qua upstream

Trong tập phép dò SHALL có ít nhất một phép đi **qua** các instance LiteLLM. Một endpoint trả mã 200
cố định MUST NOT được dùng làm bằng chứng Gateway phục vụ được, và một endpoint chỉ chứng minh tiến
trình còn sống MUST NOT được dùng làm phép đo chiều sâu.

Lý do: `/lb-health` trả 200 cứng và không chạm upstream. Ngày 17/09/2026, `litellm-1` nhận 0/20 lượt
trong khi `/lb-health` vẫn trả `lb-ok` và cả ba container vẫn `healthy`. `/health/liveliness` thuộc
cùng lớp sai — chính lớp mà `ledger-refresh` đã từ chối bằng chú thích trong `docker-compose.yml`.

#### Scenario: Chọn phép dò chiều sâu

- **WHEN** hệ thống kết luận Gateway phục vụ được
- **THEN** kết luận ấy SHALL dựa trên ít nhất một phép dò đi qua upstream
- **AND** MUST NOT dựa chỉ vào một endpoint trả mã cố định

#### Scenario: Phép dò MUST NOT tốn tiền

- **WHEN** tiến trình dò chạy một nhịp
- **THEN** nó MUST NOT gọi một endpoint sinh ra lượt gọi tính tiền tới nhà cung cấp
- **AND** nó MUST NOT sinh thêm dòng nào trong sổ gọi của Gateway

#### Scenario: Lớp hỏng không được phủ

- **WHEN** một khoá nhà cung cấp hết hạn hoặc hết hạn mức
- **THEN** tập phép dò miễn phí có thể vẫn báo bình thường
- **AND** trần ấy SHALL được ghi trong tài liệu vận hành, MUST NOT để người nhận tự phát hiện

### Requirement: Phải dò cả lớp vỏ theo đường agent đi, tách khỏi phép dò bên trong

Tập phép dò SHALL gồm ít nhất một phép đi theo **đúng đường agent dùng**, và ít nhất một phép đi từ
bên trong. Thư báo SHALL phân biệt được hai nhóm ấy.

Lý do: giữa agent và Gateway còn DNS, TLS và reverse proxy của máy chủ. Báo "khoẻ" theo phép dò bên
trong trong khi agent không kết nối được là đúng loại thư làm người nhận mất lòng tin vào chuông.
Chênh lệch giữa hai nhóm tự nó là chẩn đoán: nó tách "Gateway hỏng" khỏi "đường tới Gateway hỏng",
hai việc cần hai cách sửa khác nhau mà log của agent không phân biệt được.

#### Scenario: Lớp ngoài hỏng mà bên trong khoẻ

- **WHEN** phép dò theo đường agent thất bại còn các phép dò bên trong đều đạt
- **THEN** hệ thống SHALL gửi thư
- **AND** thư SHALL nói rõ rằng Gateway khoẻ và hỏng nằm ở lớp ngoài

#### Scenario: Bên trong hỏng mà lớp vỏ còn đứng

- **WHEN** phép dò theo đường agent đạt còn phép dò bên trong thất bại
- **THEN** thư SHALL nói rõ rằng tiến trình nginx còn sống nhưng lớp phía sau hỏng

### Requirement: Đích dò phải đọc từ cấu hình, không ghim trong mã

Mọi đích dò SHALL đọc từ cấu hình bên ngoài. Mã nguồn MUST NOT chứa một địa chỉ đích cố định nào, và
MUST NOT rẽ nhánh theo nơi nó đang chạy.

Lý do: cùng một tiến trình phải chạy được ở hai chỗ — trong mạng của Gateway, nơi đọc được chiều
sâu; và trên một máy khác, nơi thấy được cả cái chết của chính máy chủ. Hai chỗ khác nhau ở **tập
đích**, không khác ở hành vi. Ghim địa chỉ trong mã là biến việc triển khai thứ hai thành một lần
viết lại.

#### Scenario: Chạy ở nơi không đọc được phép dò tổng hợp

- **WHEN** cấu hình không khai đích của phép dò tổng hợp
- **THEN** tiến trình SHALL chạy bằng các đích còn lại
- **AND** MUST NOT báo lỗi cấu hình vì thiếu đích ấy

#### Scenario: Hai bản cùng gửi vào một hộp thư

- **WHEN** có nhiều hơn một bản đang chạy
- **THEN** mỗi thư SHALL mang tên của bản đã gửi nó
- **AND** tài liệu vận hành SHALL nói rõ việc nhận thư từ bản nào nghĩa là gì

### Requirement: Tiến trình canh gác MUST NOT mở thêm cổng và MUST NOT đòi nới quyền

Tiến trình canh gác MUST NOT công bố hay mở bất kỳ cổng nào. Việc dựng nó MUST NOT đòi nới một luật
kiểm soát truy cập đang có, MUST NOT đổi địa chỉ bind của dịch vụ nào, và MUST NOT thêm đường đi mới
vào cấu hình của load balancer.

Lý do: canh gác chỉ gửi request, không nhận. Nó không cần ai chuyển tiếp tới nó, nên nó không cần
một cổng. Và nới một biên giới an toàn để phục vụ việc giám sát là đổi một rủi ro thật lấy một tiện
lợi — nhất là khi trang tình trạng nói rõ thành phần nào đang chết và chết vì lý do gì.

#### Scenario: Dựng tiến trình canh gác

- **WHEN** tiến trình canh gác được dựng trong mạng của Gateway
- **THEN** nó SHALL gọi các dịch vụ bằng tên nội bộ, không qua load balancer
- **AND** danh sách địa chỉ được phép truy cập trang tình trạng SHALL giữ nguyên

#### Scenario: Bí mật mà nó giữ

- **WHEN** liệt kê những bí mật tiến trình canh gác nắm giữ
- **THEN** danh sách ấy MUST NOT gồm khoá nhà cung cấp, khoá quản trị của Gateway, hay thông tin
  kết nối cơ sở dữ liệu

### Requirement: Một lần đổi trạng thái sinh đúng một thư, và trạng thái phải sống sót qua việc dựng lại container

Tiến trình dò SHALL gửi thư khi **trạng thái đổi**, không khi mỗi nhịp dò hỏng. Trạng thái SHALL có
ít nhất ba mức, phân biệt được "hỏng hẳn" với "phục vụ được nhưng đã mất một phần năng lực". Trạng
thái SHALL được ghi ra ngoài bộ nhớ tiến trình.

Lý do: một instance chết thì load balancer đẩy hết sang instance kia, nên agent chạy trơn tru và
không báo gì — mất một nửa năng lực xử lý trong im lặng. Đó là tin đáng gửi, nhưng không cùng mức
với việc Gateway chết hẳn. Và container mang `restart: unless-stopped` sẽ được dựng lại; trạng thái
nằm trong bộ nhớ thì mỗi lần dựng lại là thêm một thư cho cùng một sự cố.

#### Scenario: Gateway hỏng kéo dài nhiều nhịp dò

- **WHEN** Gateway hỏng suốt nhiều nhịp dò liên tiếp
- **THEN** hệ thống SHALL gửi đúng **một** thư cho lần hỏng ấy
- **AND** số thư MUST NOT tỷ lệ với số nhịp dò

#### Scenario: Mất một phần năng lực

- **WHEN** một instance ngừng phục vụ trong khi Gateway vẫn đáp ứng được
- **THEN** hệ thống SHALL gửi thư
- **AND** thư SHALL nói rõ Gateway **vẫn đang phục vụ**
- **AND** tiêu đề thư SHALL phân biệt được với thư báo hỏng hẳn

#### Scenario: Container canh gác được dựng lại giữa sự cố

- **WHEN** container canh gác dựng lại trong lúc Gateway vẫn đang hỏng
- **THEN** hệ thống MUST NOT gửi thêm thư cho sự cố đang diễn ra

#### Scenario: Tệp trạng thái rỗng hoặc hỏng

- **WHEN** tệp trạng thái không đọc được
- **THEN** tiến trình SHALL coi như trạng thái "đang khoẻ" và chạy tiếp
- **AND** MUST NOT dừng

#### Scenario: Một nhịp dò trượt lẻ

- **WHEN** đúng một nhịp dò thất bại rồi nhịp sau trở lại bình thường
- **THEN** hệ thống MUST NOT gửi thư

### Requirement: Nguồn số liệu tình trạng hỏng MUST NOT bị báo thành Gateway hỏng

Khi tiến trình canh gác không đọc được nguồn số liệu tình trạng, nó SHALL dùng một phép dò khác làm
trọng tài trước khi kết luận, và SHALL phân biệt trong thư giữa "không đọc được tình trạng" và
"Gateway hỏng".

Lý do: nguồn số liệu tình trạng là một dịch vụ riêng, mang `restart: unless-stopped`, nên nó sẽ có
lúc dựng lại trong khi Gateway hoàn toàn khoẻ. Coi việc ấy là sự cố thì mỗi lần dựng lại là một thư
báo động giả, và thư báo động giả làm người nhận tắt thông báo — tức phép cảnh báo tự huỷ chính nó.

#### Scenario: Nguồn tình trạng chết mà Gateway khoẻ

- **WHEN** không đọc được nguồn số liệu tình trạng nhưng phép dò đi qua upstream vẫn đạt
- **THEN** thư SHALL nói rõ đây là sự cố của chỗ canh, không phải của Gateway
- **AND** MUST NOT mang tiêu đề báo Gateway hỏng

#### Scenario: Cả hai cùng im

- **WHEN** không đọc được nguồn tình trạng và phép dò đi qua upstream cũng thất bại
- **THEN** hệ thống SHALL báo Gateway hỏng

### Requirement: Chỗ canh gác phải tự chứng minh nó còn sống

Hệ thống SHALL gửi một thư nhịp tim theo chu kỳ cố định, kể cả khi không có sự cố nào.

Lý do: sau khi việc báo động rời khỏi agent, chỗ canh gác là **nguồn báo động duy nhất**. Nó hỏng
theo kiểu im lặng, mà im lặng lại trùng khít với tín hiệu "mọi thứ bình thường". Không có nhịp tim
thì không phân biệt được hai thứ đó.

#### Scenario: Không có sự cố nào trong ngày

- **WHEN** một chu kỳ nhịp tim trôi qua mà không có sự cố
- **THEN** hệ thống SHALL vẫn gửi một thư
- **AND** thư SHALL nêu số nhịp đã dò và số nhịp hỏng trong chu kỳ ấy

#### Scenario: Chỗ canh gác chết

- **WHEN** tiến trình dò dừng hẳn
- **THEN** việc **vắng** thư nhịp tim SHALL được tài liệu vận hành coi là một tín hiệu
- **AND** MUST NOT để người nhận tự suy ra

### Requirement: Thư báo phải nêu khoảng thời gian đủ để tra lại log của agent

Thư báo khi Gateway trở lại SHALL nêu thời điểm bắt đầu, thời điểm kết thúc và độ dài sự cố, và
SHALL trỏ tới chỗ tra số lượt đã đi đường dự phòng.

Lý do: chỗ canh ngoài không đếm được số lượt agent đã đi thẳng tới nhà cung cấp, cũng không biết
project nào trả tiền cho chúng. Con số ấy chỉ còn trong log của agent. Thư không thay được con số
đó, nhưng thư phải đưa đủ khoảng thời gian để tìm ra nó.

#### Scenario: Gateway trở lại

- **WHEN** Gateway phục vụ được trở lại sau một sự cố
- **THEN** thư SHALL nêu độ dài sự cố
- **AND** thư SHALL nêu chỗ tra số lượt đã đi đường dự phòng

#### Scenario: Độ chính xác của độ dài sự cố

- **WHEN** thư nêu độ dài sự cố
- **THEN** con số ấy SHALL được hiểu là chính xác tới một nhịp dò
- **AND** MUST NOT được trình bày như một phép đo chính xác hơn thế

### Requirement: Việc gửi thư MUST NOT làm dừng vòng lặp dò

Gửi thư thất bại thì tiến trình SHALL ghi log mức lỗi rồi chạy tiếp nhịp sau.

#### Scenario: Máy chủ thư không phản hồi

- **WHEN** việc gửi thư thất bại vì bất kỳ lý do gì
- **THEN** tiến trình SHALL ghi log mức lỗi
- **AND** SHALL chạy tiếp nhịp dò sau
- **AND** MUST NOT thoát

#### Scenario: Phép dò treo

- **WHEN** một lượt dò không nhận được phản hồi
- **THEN** lượt ấy SHALL bị cắt theo một hạn thời gian
- **AND** MUST NOT treo vô hạn, vì một tiến trình treo thì không bao giờ báo được gì
