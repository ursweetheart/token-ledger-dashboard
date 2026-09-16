# agent-gateway-resilience Specification

## Purpose
TBD - created by archiving change prove-the-crm-path-survives-refusal-and-outage. Update Purpose after archive.
## Requirements
### Requirement: Nhánh xử lý quá hạn mức phải được kiểm chứng bằng cách ép, không bằng cách chờ
Hệ thống SHALL kiểm chứng nhánh xử lý quá hạn mức bằng cách **ép** lỗi ấy xảy ra. Khi hạn
mức của Gateway cao hơn nhịp mà agent tự giới hạn, vận hành bình thường sẽ không sinh ra lỗi
quá hạn mức, và việc vắng lỗi đó MUST NOT được coi là bằng chứng nhánh ấy hoạt động.

#### Scenario: Ép lỗi quá hạn mức
- **WHEN** hạn mức được hạ tạm để Gateway phải từ chối
- **THEN** agent SHALL đi vào nhánh lùi lịch dành cho quá hạn mức
- **AND** hạn mức SHALL được trả về giá trị cũ, và việc đã trả SHALL được xác nhận bằng phép
  đo chứ không bằng một dòng ghi chú

#### Scenario: Phân biệt nhánh nào đã chạy
- **WHEN** cần biết agent đã đi vào nhánh lùi lịch nào
- **THEN** phép đo SHALL dựa trên **dấu hiệu do vị trí trong mã nguồn quyết định**, ví dụ câu
  lỗi cuối cùng mà mỗi nhánh ném ra
- **AND** MUST NOT suy ra từ việc lượt gọi cuối cùng vẫn thành công, vì cả hai nhánh đều dẫn
  tới thành công
- **AND** MUST NOT dựa **chỉ** vào số khoảng hay độ dài khoảng giữa các lần thử lại: hai nhánh
  có thể cho **cùng một số khoảng** khi lần ngủ cuối không có lượt gọi nào đi sau, và độ dài
  khoảng còn bị nhịp tự giới hạn của agent lẫn thời gian Gateway tự thử lại cộng vào

#### Scenario: Gateway tự thử lại và che mất lỗi
- **WHEN** Gateway tự thử lại hoặc tự chuyển tuyến trước khi trả lỗi ra ngoài
- **THEN** điều đó SHALL được xác định trước khi kết luận về nhánh của agent
- **AND** kết quả MUST NOT ghi là "agent không nhận được lỗi" khi thực tế là "agent chưa bao
  giờ được cho thấy lỗi"

### Requirement: Mất Gateway giữa lúc chạy phải không mất dòng và không đếm đôi
Khi Gateway biến mất giữa lúc agent đang xử lý, lần chạy sau SHALL vừa không bỏ sót dòng, vừa
không tạo bản ghi thứ hai cho cùng một dòng.

#### Scenario: Gateway mất giữa lúc chạy
- **WHEN** Gateway không còn kết nối được trong khi agent đang xử lý
- **THEN** mọi dòng đang xử lý SHALL hoặc vào sổ, hoặc quay lại hàng chờ
- **AND** MUST NOT biến mất mà không có dấu hiệu

#### Scenario: Chạy lại sau khi Gateway trở lại
- **WHEN** agent chạy lại sau khi Gateway đã trở lại
- **THEN** mỗi dòng SHALL có đúng **một** bản ghi trong sổ
- **AND** token cùng chi phí trong sổ MUST NOT phồng lên vì đếm lại phần đã xử lý

#### Scenario: Phân biệt hai kiểu hỏng
- **WHEN** báo cáo kết quả diễn tập
- **THEN** mất dòng và đếm đôi SHALL được nêu tách nhau
- **AND** MUST NOT gộp thành một kết luận "chạy lại được", vì đếm đôi để lại kết quả nghiệp
  vụ trông đúng trong khi số tiền thì sai

### Requirement: Phản hồi thành công nhưng chưa viết xong MUST NOT được coi là đầy đủ
Lớp gọi SHALL nhận ra khi nhà cung cấp trả mã thành công nhưng cắt phản hồi giữa chừng vì
chạm trần token đầu ra, và SHALL báo lỗi. Nó MUST NOT trả phần đã nhận được như thể đó là kết
quả trọn vẹn.

#### Scenario: Phản hồi bị cắt vì chạm trần token đầu ra
- **WHEN** phản hồi mang mã thành công nhưng trường báo lý do kết thúc cho biết nó bị cắt vì
  hết chỗ
- **THEN** lớp gọi SHALL báo lỗi kèm số token đã dùng và trần đang đặt
- **AND** MUST NOT trả nội dung nhận được ra cho tầng trên như một kết quả bình thường

#### Scenario: Có công cụ tự vá dữ liệu hỏng ở tầng dưới
- **WHEN** tầng phân tích dữ liệu có khả năng tự vá một cấu trúc bị cắt cụt
- **THEN** việc vá được SHALL được ghi lại hoặc cảnh báo
- **AND** MUST NOT im lặng, vì kết quả vá được có thể **trông hoàn chỉnh** — thiếu bản ghi mà
  không để lại dấu hiệu nào trên phần còn lại

#### Scenario: Ngân sách token đầu ra dùng chung với phần suy luận của model
- **WHEN** model có chế độ suy luận và phần suy luận tính vào ngân sách token đầu ra
- **THEN** trần token đầu ra SHALL được đặt theo số đo thực tế cho mỗi đơn vị công việc
- **AND** MUST NOT giữ nguyên một trần được chọn từ trước khi bật chế độ suy luận

### Requirement: Chi phí của phép đo phải có trần chốt trước
Phép đo nào gọi nhà cung cấp thật SHALL có trần chi tiêu được chốt **trước** khi chạy.

#### Scenario: Chạy phép đo ở khối lượng thật
- **WHEN** một phép đo dự kiến gọi nhà cung cấp ở khối lượng cỡ production
- **THEN** trần chi tiêu SHALL được chốt trước
- **AND** chi phí thực tế SHALL được ghi lại và đối chiếu với trần ấy

### Requirement: So sánh hai đường phải xen kẽ trên cùng đầu vào
Khi so một đường mới với một đường cũ, phép đo SHALL dùng **cùng** đầu vào và **xen kẽ** hai
đường. Nó MUST NOT chạy hết đường này rồi mới sang đường kia.

#### Scenario: Đo chênh lệch độ trễ
- **WHEN** đo độ trễ của đường qua Gateway so với đường gọi thẳng
- **THEN** hai đường SHALL chạy xen kẽ trên cùng tập đầu vào
- **AND** kết quả SHALL nêu trung vị và phân vị cao, MUST NOT chỉ nêu trung bình

#### Scenario: Đường so sánh không còn tồn tại trong production
- **WHEN** đường gọi thẳng đã bị bỏ khỏi production
- **THEN** báo cáo SHALL nói rõ đó chỉ là mốc so
- **AND** MUST NOT trình bày như thể production còn hai đường để chọn

### Requirement: Công cụ đo phải dùng lại được cho agent khác
Công cụ dựng ra để đo một agent SHALL nhận agent, thông tin xác thực, model, số lượt và đường
đi làm **tham số**.

#### Scenario: Đo agent thứ hai
- **WHEN** cần đo cùng những điều đó cho một agent khác
- **THEN** công cụ SHALL dùng lại được bằng cách đổi tham số
- **AND** MUST NOT phải sửa mã nguồn của công cụ

#### Scenario: Chỗ đặt công cụ
- **WHEN** công cụ được thêm vào repo
- **THEN** nó SHALL nằm tách khỏi đường nạp dữ liệu thật
- **AND** MUST NOT nằm lẫn với các script chạy trong đường nạp

### Requirement: Phép đo MUST NOT gây tác dụng phụ nghiệp vụ
Mọi phép đo trong nhóm này SHALL đi qua lớp gọi LLM, không qua toàn bộ tiến trình nghiệp vụ
của agent.

#### Scenario: Đo trên một agent không có chế độ chạy thử
- **WHEN** agent không có cờ tắt được việc ghi ra hệ thống ngoài và gửi thông báo
- **THEN** phép đo SHALL gọi trực tiếp lớp gọi LLM
- **AND** MUST NOT ghi dữ liệu nghiệp vụ thật, MUST NOT gửi thông báo cho người thật

#### Scenario: Diễn tập bằng tiến trình nghiệp vụ thật
- **WHEN** một diễn tập chỉ chứng minh được nếu chạy tiến trình nghiệp vụ thật
- **THEN** tác dụng phụ của nó SHALL được nêu trước trong tài liệu
- **AND** MUST NOT chạy chỉ vì nó tiện hơn

### Requirement: Mất Gateway phải chuyển sang nhà cung cấp, không bỏ lô

Khi Gateway không còn kết nối được, agent SHALL tự chuyển sang gọi thẳng nhà cung cấp và **chạy
xong** lô đang xử lý. Việc bỏ lô rồi chờ lần chạy sau MUST NOT còn là hành vi mặc định.

Chuyển đường SHALL xảy ra **trong cùng một lần chạy**, không đòi khởi động lại agent và không đòi
người vận hành sửa cấu hình.

#### Scenario: Gateway mất giữa lúc chạy

- **WHEN** Gateway không còn kết nối được trong khi agent đang xử lý các lô
- **THEN** agent SHALL chuyển sang đường gọi thẳng nhà cung cấp
- **AND** lô đang xử lý SHALL được xử lý xong, không bị bỏ
- **AND** các lô còn lại SHALL đi tiếp trên đường thẳng cho tới khi Gateway sống lại

#### Scenario: Gateway sống lại

- **WHEN** Gateway kết nối lại được
- **THEN** agent SHALL quay về gọi qua Gateway
- **AND** việc quay về SHALL dựa trên một phép thử định kỳ, MUST NOT thử lại Gateway ở mỗi lượt gọi

### Requirement: Chỉ lỗi hạ tầng mới được đổi đường

Agent SHALL chỉ đổi đường khi lỗi cho thấy **không kết nối được** tới Gateway. Các loại lỗi khác
MUST NOT kích hoạt đổi đường.

Lỗi mã từ 400 trở lên là lỗi của chính yêu cầu gửi đi; gửi lại yêu cầu đó qua đường khác SHALL cho
cùng kết quả sai, và chỉ tốn thêm một lượt gọi.

Lỗi quá hạn mức SHALL tiếp tục đi vào nhánh lùi lịch sẵn có. Việc đổi đường khi quá hạn mức nằm
ngoài phạm vi, vì hạn mức của Gateway và hạn mức của nhà cung cấp chưa phân biệt được từ phía agent.

#### Scenario: Gateway trả mã lỗi từ 400 trở lên

- **WHEN** Gateway trả về một mã lỗi từ 400 trở lên
- **THEN** agent MUST NOT đổi đường
- **AND** lỗi SHALL đi theo đường xử lý lỗi sẵn có

#### Scenario: Gateway trả lỗi quá hạn mức

- **WHEN** Gateway trả về lỗi quá hạn mức
- **THEN** agent MUST NOT đổi đường
- **AND** agent SHALL đi vào nhánh lùi lịch dành cho quá hạn mức

#### Scenario: Ba câu lỗi phải phân biệt được bằng phép kiểm tự động

- **WHEN** bộ kiểm tự động chạy
- **THEN** nó SHALL khẳng định ba loại lỗi của client Gateway vẫn phân biệt được với nhau
- **AND** phép kiểm này tồn tại vì việc phân loại dựa trên nội dung câu lỗi: sửa một câu chữ mà
  không ai báo sẽ làm việc đổi đường **im lặng ngừng hoạt động**

### Requirement: Ngưỡng đổi đường đếm lỗi liên tiếp, dưới một chốt dùng chung

Agent SHALL đổi đường sau một số lần hỏng **liên tiếp**, MUST NOT đếm tổng số lần hỏng. Một lượt
hỏng lẻ không phải dấu hiệu tuyến chết.

Khi agent chạy nhiều luồng song song, bộ đếm và việc đổi đường SHALL nằm dưới một chốt dùng chung.

#### Scenario: Nhiều luồng cùng gặp lỗi

- **WHEN** nhiều luồng cùng gặp lỗi không kết nối được trong cùng một sự cố
- **THEN** việc đổi đường SHALL xảy ra đúng **một** lần
- **AND** MUST NOT dựng nhiều client cho cùng một lần đổi

#### Scenario: Một lượt hỏng lẻ giữa các lượt thành công

- **WHEN** một lượt hỏng vì không kết nối được, nhưng lượt sau đó thành công
- **THEN** bộ đếm SHALL trở về không
- **AND** agent MUST NOT đổi đường

### Requirement: Lượt gọi đi đường thẳng phải đọc lại được

Mọi lượt gọi đi đường thẳng SHALL được agent ghi lại, kèm mốc thời gian và lý do đổi đường.

Trong khoảng thời gian ấy Gateway không ghi sổ. Nếu agent cũng không ghi, khoảng thời gian đó SHALL
chỉ còn biết qua hoá đơn — chậm một ngày và không có chiều người dùng.

#### Scenario: Đọc lại một sự cố đã qua

- **WHEN** cần biết agent đã chạy đường thẳng trong khoảng nào
- **THEN** thông tin đó SHALL lấy được từ ghi chép của agent
- **AND** MUST NOT phải suy ra từ chỗ trống trong sổ Gateway

### Requirement: Đường dự phòng không được dùng chung biến khoá với Gateway

Đường dự phòng MUST NOT đọc biến khoá mà đường Gateway đang dùng.

Khi chạy qua Gateway, biến ấy giữ **khoá ảo** của Gateway, không phải khoá của nhà cung cấp. Đường
dự phòng đọc lại chính biến đó SHALL cầm khoá ảo đi gọi thẳng nhà cung cấp và hỏng.

#### Scenario: Đang chạy qua Gateway thì đổi đường

- **WHEN** agent đang chạy qua Gateway và phải đổi sang đường thẳng
- **THEN** đường thẳng SHALL lấy thông tin xác thực từ nguồn riêng của nó
- **AND** MUST NOT đọc biến khoá của Gateway

#### Scenario: Không có thông tin xác thực cho đường dự phòng

- **WHEN** agent khởi động mà đường dự phòng thiếu thông tin xác thực
- **THEN** tính năng đổi đường SHALL bị tắt
- **AND** agent SHALL ghi log ở mức lỗi lúc khởi động, MUST NOT chỉ ghi ở mức cảnh báo
- **AND** agent SHALL vẫn khởi động được, vì thiếu đường dự phòng không phải lý do chặn hệ thống

### Requirement: Project chịu phí của đường dự phòng phải được khai rõ

Nơi khai thông tin xác thực của đường dự phòng SHALL ghi rõ project nào chịu phí cho các lượt gọi
ấy.

Yêu cầu này tồn tại vì một project không được khai trong danh mục agent SHALL làm khâu nạp dữ liệu
dừng lại, hoặc làm số liệu biến mất khỏi dashboard mà không ai báo.

#### Scenario: Đọc cấu hình để biết tiền rơi vào đâu

- **WHEN** người vận hành đọc cấu hình của đường dự phòng
- **THEN** project chịu phí SHALL đọc được ngay tại đó
- **AND** nếu project đó khác project đang khai cho agent trong danh mục, sự khác biệt SHALL được
  ghi thành chú thích chứ không để người đọc tự phát hiện
