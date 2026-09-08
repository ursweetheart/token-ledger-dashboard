# api-access-control Specification

## Purpose
TBD - created by archiving change require-a-key-to-read-the-api. Update Purpose after archive.
## Requirements
### Requirement: Mọi endpoint đòi một chứng danh hợp lệ

Mọi endpoint của `backend/` SHALL từ chối yêu cầu không mang chứng danh hợp lệ, trả HTTP
401. MUST NOT có endpoint nào trả dữ liệu nghiệp vụ mà không kiểm.

Lý do: `/api/accounts` trả **937 tài khoản** kèm họ tên, phòng ban, vai trò. Hôm nay 8/8
endpoint không kiểm gì; an toàn chỉ vì uvicorn gắn `127.0.0.1` — một dòng cấu hình, không
phải một cơ chế.

CORS **không** thay được yêu cầu này: CORS là luật của trình duyệt, còn `curl` không đọc
CORS bao giờ và vẫn nhận đủ dữ liệu.

#### Scenario: Gọi không mang khoá

- **WHEN** một yêu cầu tới bất kỳ endpoint nào mà không có header `Authorization`
- **THEN** máy chủ SHALL trả 401
- **AND** MUST NOT trả bất kỳ dòng dữ liệu nào

#### Scenario: Gọi bằng công cụ ngoài trình duyệt

- **WHEN** `curl` gọi `/api/accounts` không mang khoá
- **THEN** máy chủ SHALL trả 401
- **AND** kết quả MUST NOT phụ thuộc vào cấu hình CORS

#### Scenario: Cần một điểm thăm dò sống-chết

- **WHEN** hệ thống giám sát cần biết máy chủ còn sống
- **THEN** điểm thăm dò SHALL không trả dữ liệu nghiệp vụ nào
- **AND** MUST NOT dùng `/api/health` cho việc này — endpoint đó nói dữ liệu có gì, mới
  đến đâu, thiếu chỗ nào

### Requirement: Thiếu cấu hình thì máy chủ không khởi động

Khi không có khoá được cấu hình, máy chủ SHALL từ chối khởi động và in rõ lý do. MUST NOT
khởi động ở chế độ không xác thực do thiếu cấu hình.

Lý do: chế độ hỏng phải là *"không chạy"*, không được là *"chạy mở"*. Quên đặt biến môi
trường mà máy chủ vẫn chạy bình thường thì ta có đúng lỗ hổng hôm nay, cộng thêm niềm tin
sai rằng đã khoá. Cùng hạng lỗi với mọi thứ sửa ngày 20/08: sai một cách im lặng.

#### Scenario: Triển khai mà quên biến môi trường

- **WHEN** `DASHBOARD_KEY` không được đặt, hoặc đặt bằng chuỗi rỗng
- **THEN** máy chủ SHALL thoát với thông báo nêu tên biến còn thiếu
- **AND** MUST NOT lắng nghe trên cổng nào

#### Scenario: Tắt xác thực lúc phát triển

- **WHEN** người phát triển muốn chạy không cần khoá
- **THEN** họ SHALL phải đặt một biến riêng, tường minh (`DASHBOARD_OPEN=1`)
- **AND** máy chủ SHALL in cảnh báo mỗi lần khởi động ở chế độ đó

### Requirement: Phép kiểm chứng danh trả về một chủ thể, không trả đúng/sai

Hàm kiểm SHALL trả về một đối tượng mô tả **ai đang gọi**. MUST NOT chỉ trả boolean hoặc
chỉ ném lỗi.

Lý do: ngày nâng lên JWT theo người, hàm đó trả `Principal(kind='user', name=..., role=...)`
thay vì `Principal(kind='shared_key', ...)` — và 8 endpoint không phải sửa một chữ. Đây là
khác biệt giữa một bản chắp vá và một nền móng.

#### Scenario: Nâng lên JWT theo người về sau

- **WHEN** cơ chế xác thực đổi từ khoá dùng chung sang JWT
- **THEN** chữ ký của các endpoint SHALL giữ nguyên
- **AND** chỉ hàm kiểm chứng danh SHALL phải sửa

#### Scenario: Tên header không đổi khi nâng cấp

- **WHEN** chứng danh được gửi lên
- **THEN** nó SHALL đi trong `Authorization: Bearer <giá trị>`
- **AND** MUST NOT dùng header đặt tên riêng cho khoá dùng chung

### Requirement: So chứng danh không rò rỉ qua thời gian

Phép so SHALL dùng hàm so sánh thời gian hằng định (`secrets.compare_digest`). MUST NOT
dùng `==`.

#### Scenario: So khoá sai

- **WHEN** một khoá sai được gửi lên
- **THEN** thời gian trả lời MUST NOT phụ thuộc vào số ký tự đầu khớp được

#### Scenario: Chứng danh chứa ký tự ngoài ASCII

- **WHEN** người gọi gửi một chứng danh có ký tự ngoài ASCII
- **THEN** máy chủ SHALL trả 401 như mọi khoá sai khác
- **AND** MUST NOT ném lỗi hay trả 5xx

> Đo 21/08/2026: `secrets.compare_digest` với hai chuỗi `str` ném
> `TypeError: comparing strings with non-ASCII characters is not supported`. Người gọi
> điều khiển được vế trái, nên chỉ cần `Authorization: Bearer á` là mọi endpoint hỏng —
> **một đường sập gọi được mà không cần biết khoá**. Phải so trên `bytes`.

### Requirement: Người xem nhập khoá một lần, và khoá không lọt vào URL

Giao diện SHALL hỏi khoá khi chưa có, ghi nhớ cho các lần sau, và gửi kèm mọi yêu cầu.
Khoá MUST NOT xuất hiện trong URL, tham số truy vấn, hay bất kỳ chỗ nào bị ghi vào nhật ký
máy chủ.

Lý do: `web/js/api.js` đã sẵn cách ghi đè địa chỉ bằng `?api=...`, nên lối "cứ thêm
`?key=...` cho nhanh" rất dễ được chọn. Tham số truy vấn nằm trong nhật ký truy cập, trong
lịch sử trình duyệt, và trong header `Referer` gửi sang bên thứ ba.

#### Scenario: Vào dashboard lần đầu

- **WHEN** chưa có khoá được lưu
- **THEN** giao diện SHALL hỏi khoá trước khi gọi endpoint dữ liệu nào

#### Scenario: Khoá sai hoặc đã bị đổi

- **WHEN** máy chủ trả 401
- **THEN** giao diện SHALL nói *khoá không đúng* và hỏi lại
- **AND** MUST NOT dùng chung lời với *"chưa bật backend"* — hai tình huống này đòi hai
  hành động khác nhau

#### Scenario: Khoá không lọt vào URL

- **WHEN** khoá được gửi lên máy chủ
- **THEN** nó SHALL nằm trong header
- **AND** MUST NOT nằm trong `location.search` hay đường dẫn

#### Scenario: Địa chỉ backend bị đổi bằng tham số truy vấn

- **WHEN** trang được mở với một địa chỉ backend khác địa chỉ đã lưu khoá
- **THEN** giao diện SHALL hỏi khoá mới cho địa chỉ đó
- **AND** MUST NOT gửi khoá đã lưu của địa chỉ khác sang địa chỉ mới

> Phát hiện lúc tự soát 21/08/2026. `web/js/api.js` đã có sẵn `?api=http://may-khac:8000`
> để trỏ sang máy khác. Trước change này tham số đó chỉ quyết định **đọc dữ liệu từ đâu**;
> từ lúc trình duyệt giữ một bí mật, nó quyết định luôn **gửi bí mật đi đâu**. Ai gửi được
> link `dashboard?api=http://host-la` là lấy được khoá của người bấm vào, không cảnh báo
> nào — vì đây vẫn là một tính năng có thật.
>
> Cất khoá **theo từng địa chỉ** đóng hẳn đường đó: địa chỉ lạ đơn giản là không có khoá
> nào, người dùng phải tự gõ, tức phải cố ý. Và nó đúng hơn về bản chất — hai máy chủ khác
> nhau vốn là hai khoá khác nhau.
