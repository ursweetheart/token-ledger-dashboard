## ADDED Requirements

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
