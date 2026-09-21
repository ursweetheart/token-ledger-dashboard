## MODIFIED Requirements

### Requirement: Mọi endpoint đòi một chứng danh hợp lệ

Mọi endpoint của `backend/` SHALL từ chối yêu cầu không mang chứng danh hợp lệ, trả HTTP
401. MUST NOT có endpoint nào trả dữ liệu nghiệp vụ **hoặc thay đổi dữ liệu** mà không kiểm.

Lý do: `/api/accounts` trả **937 tài khoản** kèm họ tên, phòng ban, vai trò. Hôm nay 8/8
endpoint không kiểm gì; an toàn chỉ vì uvicorn gắn `127.0.0.1` — một dòng cấu hình, không
phải một cơ chế.

Từ khi có endpoint ghi hạn mức, yêu cầu này phủ cả hai chiều: đọc dữ liệu và thay đổi dữ liệu. Một
endpoint ghi không kiểm chứng danh còn nguy hơn một endpoint đọc, vì nó để lại hậu quả sau khi kẻ
gọi đã đi khỏi.

CORS **không** thay được yêu cầu này: CORS là luật của trình duyệt, còn `curl` không đọc
CORS bao giờ và vẫn nhận đủ dữ liệu.

#### Scenario: Gọi không mang khoá

- **WHEN** một yêu cầu tới bất kỳ endpoint nào mà không có header `Authorization`
- **THEN** máy chủ SHALL trả 401
- **AND** MUST NOT trả bất kỳ dòng dữ liệu nào

#### Scenario: Gọi endpoint ghi mà không mang khoá

- **WHEN** một yêu cầu ghi hạn mức tới mà không có chứng danh hợp lệ
- **THEN** máy chủ SHALL trả 401
- **AND** MUST NOT thay đổi hạn mức, và MUST NOT ghi dòng lịch sử nào

#### Scenario: Gọi bằng công cụ ngoài trình duyệt

- **WHEN** `curl` gọi `/api/accounts` không mang khoá
- **THEN** máy chủ SHALL trả 401
- **AND** kết quả MUST NOT phụ thuộc vào cấu hình CORS

#### Scenario: Cần một điểm thăm dò sống-chết

- **WHEN** hệ thống giám sát cần biết máy chủ còn sống
- **THEN** điểm thăm dò SHALL không trả dữ liệu nghiệp vụ nào
- **AND** MUST NOT dùng `/api/health` cho việc này — endpoint đó nói dữ liệu có gì, mới
  đến đâu, thiếu chỗ nào

## ADDED Requirements

### Requirement: Backend giữ master key của Gateway thì phải giữ trong phạm vi hẹp nhất

Khi backend giữ master key của Gateway để sửa hạn mức, nó SHALL chỉ dùng khoá đó cho đúng thao tác
sửa hạn mức. Backend MUST NOT có endpoint nào nhận đường dẫn, phương thức hay thân yêu cầu từ người
gọi rồi chuyển tiếp sang Gateway.

Lý do: master key mở được mọi thứ của Gateway — cấp khoá, xoá khoá, đọc sổ. Một endpoint chuyển
tiếp sẽ biến khoá dashboard thành quyền quản trị Gateway, và không ai nhận ra cho tới khi có người
thử.

#### Scenario: Người gọi cố điều khiển đích đến

- **WHEN** yêu cầu gửi lên mang theo một đường dẫn hay phương thức của Gateway
- **THEN** backend SHALL bỏ qua giá trị đó
- **AND** MUST NOT gọi sang Gateway ở bất kỳ đường nào ngoài đường sửa hạn mức

#### Scenario: Thiếu master key lúc khởi động

- **WHEN** biến môi trường giữ master key không được đặt
- **THEN** backend SHALL từ chối khởi động và nói rõ thiếu biến nào

#### Scenario: Gateway trả lỗi

- **WHEN** Gateway trả lỗi cho lệnh sửa hạn mức
- **THEN** backend SHALL báo lỗi đó cho người dùng theo cách hiểu được
- **AND** câu trả lời MUST NOT chứa master key, kể cả trong nguyên văn lỗi

### Requirement: Một khoá dùng chung cho cả đọc lẫn sửa hạn mức

Hệ thống SHALL dùng **một** khoá dùng chung cho cả endpoint đọc lẫn endpoint ghi hạn mức. Hệ quả
SHALL được ghi rõ trong tài liệu: ai xem được dashboard thì cũng sửa được hạn mức của mọi project.

Đây là một quyết định đã chốt, không phải một thiếu sót còn lại. Ghi nó thành yêu cầu để ngày nào
cần tách vai thì người sau biết đang đổi cái gì, chứ không tưởng là đang vá một lỗ hổng bị bỏ quên.

#### Scenario: Người chỉ cần xem dashboard

- **WHEN** một người được trao khoá để xem số liệu
- **THEN** người đó cũng gọi được endpoint sửa hạn mức
- **AND** tài liệu SHALL nói rõ điều này trước khi khoá được trao

#### Scenario: Ngày tách vai đọc và vai quản trị

- **WHEN** hệ thống cần phân biệt người xem với người sửa hạn mức
- **THEN** thay đổi SHALL nằm trong hàm kiểm chứng danh đã có
- **AND** chữ ký của các endpoint MUST NOT phải đổi theo

### Requirement: Ghi chú lập luận trong mã nguồn phải khớp với thực tế sau change này

Ghi chú lập luận trong mã nguồn SHALL khớp với thực tế sau change này, và MUST NOT để lại một lập
luận mà tiền đề của nó đã không còn đúng. Cụ thể: ghi chú tại `backend/main.py` lập luận không cần
phân vai vì *"8/8 endpoint là GET, 0 hành động đặc quyền"*, nên khi endpoint ghi đầu tiên tồn tại,
ghi chú đó phải được sửa lại.

Lý do: ghi chú sai còn tệ hơn không có ghi chú — người sau đọc và tin.

#### Scenario: Đọc lại lập luận sau khi có endpoint ghi

- **WHEN** một người đọc phần xác thực của `backend/main.py`
- **THEN** ghi chú SHALL phản ánh đúng số endpoint ghi đang có
- **AND** SHALL nêu quyết định dùng chung khoá và hệ quả của nó
