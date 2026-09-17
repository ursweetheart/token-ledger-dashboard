## ADDED Requirements

### Requirement: Tên biến giữ khoá nhà cung cấp phải suy ra được agent dùng nó

Mỗi biến môi trường giữ khoá của nhà cung cấp cho một tuyến Gateway SHALL mang tên suy ra được từ
định danh agent dùng tuyến ấy, và định danh đó SHALL là một giá trị đã có trong danh mục agent
(`dim_agent.code`). Tên biến MUST NOT mang tên nhà cung cấp, tên đường đi, hay chữ chỉ mục đích thử
nghiệm.

Lý do: tên mang nhà cung cấp sẽ sai khi đường đi đổi, và đã sai thật — một khoá tên
`..._GG_AIA_STU` là khoá Vertex express chứ không phải AI Studio, đo ngày 10/09/2026 bằng tiền tố
`AQ.`. Tên mang chữ `BENCH` và `TEST` cho một khoá production thì người đọc sau sẽ tưởng xoá đi
không sao. Lấy định danh đã có trong danh mục thì khoá thêm sau này có sẵn tên, và tên khớp với nhãn
đang dán trên tuyến.

#### Scenario: Thêm khoá cho một agent mới
- **WHEN** một tuyến mới cần khoá nhà cung cấp cho một agent
- **THEN** tên biến SHALL suy ra được từ `dim_agent.code` của agent ấy
- **AND** MUST NOT phải đặt ra một quy ước tên mới

#### Scenario: Đường đi tới nhà cung cấp đổi
- **WHEN** một tuyến chuyển từ đường đi này sang đường đi khác của cùng nhà cung cấp
- **THEN** tên biến giữ khoá MUST NOT phải đổi theo

#### Scenario: Một khoá phục vụ nhiều agent
- **WHEN** một khoá nhà cung cấp được nhiều hơn một agent dùng
- **THEN** nó MUST NOT được đặt tên theo một agent trong số đó
- **AND** tình trạng dùng chung ấy SHALL được ghi tại chỗ khai báo

### Requirement: Đổi tên một biến khoá phải đáp xuống mọi tệp tham chiếu trong cùng một commit

Mọi tệp được quản lý phiên bản có tham chiếu tên một biến giữ khoá nhà cung cấp SHALL được sửa trong
**cùng một commit** khi tên ấy đổi. Hệ thống MUST NOT giữ bí danh cho tên cũ.

Lý do: ngày 10/09/2026 việc đổi tên bị chia nhỏ — tệp môi trường đổi trước, tệp cấu hình và tệp
compose đổi sau. Vì compose viết `${VAR:-}`, một biến thiếu thành **chuỗi rỗng** thay vì một lỗi.
Container lên bình thường, kiểm tra sức khoẻ trả về bình thường, và tuyến chỉ chết đúng lúc có người
gọi thật. Chia nhỏ ở đây không phải cách làm thận trọng; nó là cơ chế gây lỗi.

#### Scenario: Sót tệp cấu hình tuyến
- **WHEN** tên biến đã đổi ở tệp môi trường nhưng tệp cấu hình tuyến vẫn tham chiếu tên cũ
- **THEN** CI SHALL đỏ trước khi thay đổi ấy tới được máy chủ

#### Scenario: Thiếu khoá lúc khởi động
- **WHEN** một biến khoá bắt buộc trống hoặc không tồn tại
- **THEN** tiến trình Gateway SHALL dừng trước khi phục vụ, với thông báo nêu đúng tên biến
- **AND** MUST NOT khởi động rồi để tuyến ấy hỏng khi có người gọi

#### Scenario: Máy khác nhận commit đổi tên
- **WHEN** một máy đang chạy Gateway nhận commit đổi tên mà tệp môi trường của nó chưa sửa
- **THEN** Gateway ở đó SHALL không khởi động
- **AND** MUST NOT chạy tiếp bằng một giá trị rỗng

### Requirement: Mọi biến khoá mà tuyến tham chiếu phải được vòng kiểm khởi động biết tới

Mỗi biến `KEY_*` mà tệp cấu hình tuyến tham chiếu SHALL có mặt trong danh sách biến bắt buộc của
cửa chặn khởi động, trong khai báo môi trường của dịch vụ Gateway, và trong tệp compose dùng cho đo
hiệu năng. Một phép canh trong CI SHALL chặn trường hợp thiếu bất kỳ nơi nào.

Lý do: cửa chặn khởi động chỉ bảo vệ được những biến nó biết tên. Ngày 10/09/2026 danh sách ấy thiếu
đúng khoá của tuyến CRM, trong khi chú thích ở tệp compose **đã ghi là có** — nên không ai soát lại.
Tệp compose dùng cho đo hiệu năng phải có mặt trong luật này vì nó dùng chung cửa chặn ấy: thêm một
biến vào vòng kiểm mà không cấp giá trị tương ứng ở đó thì phần đo không khởi động được.

#### Scenario: Tuyến tham chiếu biến mà cửa chặn không biết
- **WHEN** tệp cấu hình tuyến tham chiếu một biến `KEY_*` không có trong danh sách bắt buộc của cửa
  chặn khởi động
- **THEN** phép canh SHALL báo hỏng

#### Scenario: Thêm biến vào cửa chặn mà quên phần đo hiệu năng
- **WHEN** một biến được thêm vào danh sách bắt buộc nhưng tệp compose dùng cho đo hiệu năng không
  có giá trị tương ứng
- **THEN** phép canh SHALL báo hỏng

#### Scenario: Khoá ghi thẳng vào tệp cấu hình
- **WHEN** một tuyến khai khoá bằng giá trị ghi thẳng thay vì một tham chiếu tới biến môi trường
- **THEN** phép canh SHALL báo hỏng

### Requirement: Nghiệm thu việc đổi tên phải bằng một lượt gọi thật

Việc nghiệm thu SHALL gồm một lượt gọi thật đi qua tuyến bị ảnh hưởng, và SHALL kiểm dòng sổ mà lượt
gọi ấy sinh ra. Nó MUST NOT kết luận từ trạng thái container hay từ điểm kiểm tra sức khoẻ.

Lý do: sót tệp cấu hình tuyến không làm container chết. Tiến trình lên bình thường, điểm kiểm tra
sức khoẻ trả về bình thường, và lỗi chỉ lộ ra khi có người gọi thật.

#### Scenario: Container khoẻ nhưng tuyến hỏng
- **WHEN** tệp cấu hình tuyến còn tham chiếu một tên biến không còn tồn tại
- **THEN** container SHALL vẫn ở trạng thái khoẻ và điểm kiểm tra sức khoẻ SHALL vẫn trả về thành công
- **AND** vì vậy hai dấu hiệu ấy MUST NOT được dùng làm bằng chứng nghiệm thu

#### Scenario: Lượt gọi thật sau khi đổi tên
- **WHEN** nghiệm thu việc đổi tên
- **THEN** một lượt gọi thật qua tuyến bị ảnh hưởng SHALL thành công
- **AND** dòng sổ sinh ra SHALL mang đúng nhãn định danh của agent và đúng tên model được khai

#### Scenario: Tuyến không bị đụng tới
- **WHEN** một tuyến khác không nằm trong phạm vi đổi tên
- **THEN** nghiệm thu SHALL gồm một lượt gọi qua tuyến ấy để chứng minh nó không hồi quy
