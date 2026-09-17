## MODIFIED Requirements

### Requirement: Đổi đường vì hạ tầng hỏng phải báo cho người vận hành

Khi hạ tầng Gateway hỏng, hệ thống SHALL báo cho người vận hành bằng thư điện tử. Việc báo SHALL do
một tiến trình canh gác đứng ngoài agent thực hiện, không do chính agent.

**Nghĩa vụ báo động SHALL không còn nằm ở agent.** Việc người vận hành có được báo hay không SHALL
chỉ phụ thuộc vào tiến trình canh gác, và MUST NOT phụ thuộc vào việc agent nào đó có gửi thư hay
không.

Agent SHALL vẫn ghi log mỗi lần đổi đường — đó là chỗ tra số lượt đã đi đường dự phòng. Agent có còn
gửi thư nữa hay không là việc dọn dẹp riêng, làm sau và ngoài phạm vi yêu cầu này.

Một dòng log MUST NOT được coi là đã báo. Sự cố ngày 10/09 đã đi qua hoàn toàn im lặng theo cách
đó: agent bỏ lô, ghi ba dòng log, và không ai biết cho tới khi có người đọc lại nhật ký. Luật ấy
không đổi — chỉ đổi chỗ đặt cái chuông. Log giữ vai **chỗ tra số chi tiết**, thư giữ vai **báo
động**.

#### Scenario: Hạ tầng Gateway không phục vụ được

- **WHEN** Gateway không phục vụ được
- **THEN** hệ thống SHALL gửi một thư báo
- **AND** thư SHALL nói rõ thời điểm phát hiện và lớp nào hỏng

#### Scenario: Gateway phục vụ trở lại

- **WHEN** Gateway phục vụ được trở lại
- **THEN** hệ thống SHALL gửi một thư báo
- **AND** thư SHALL nói rõ sự cố kéo dài bao lâu

#### Scenario: Agent đổi đường

- **WHEN** agent chuyển từ Gateway sang gọi thẳng nhà cung cấp, hoặc quay về
- **THEN** agent SHALL ghi một dòng log nhận ra được, kèm số lượt đã đi đường dự phòng
- **AND** người vận hành SHALL được báo bởi tiến trình canh gác, không phụ thuộc vào agent

#### Scenario: Agent chưa được gỡ mã gửi thư

- **WHEN** một agent vẫn còn mã gửi thư riêng và một sự cố xảy ra
- **THEN** người vận hành có thể nhận hai thư cho cùng một sự cố
- **AND** điều đó MUST NOT được coi là lỗi
- **AND** tài liệu vận hành SHALL nói rõ điều này, để người nhận không hiểu nhầm là chuông gửi trùng
  vì hỏng

### Requirement: Thư gộp theo lần đổi trạng thái, không gộp theo lượt gọi

Mỗi lần trạng thái đổi SHALL sinh ra đúng **một** thư. Hệ thống MUST NOT gửi một thư cho mỗi lượt
gọi hỏng, và MUST NOT gửi một thư cho mỗi nhịp dò hỏng.

Một lô cỡ production có hàng nghìn lượt gọi, và một sự cố dài có hàng trăm nhịp dò. Gửi mỗi lần hỏng
một thư SHALL làm người nhận tắt thông báo, tức phép cảnh báo tự huỷ chính nó.

Trạng thái SHALL có ít nhất ba mức, vì "mất một instance mà vẫn phục vụ được" là tin đáng gửi nhưng
không cùng mức với "hỏng hẳn". Một sự cố hỏng hẳn rồi phục hồi vì vậy sinh hai thư; một sự cố đi qua
mức trung gian sinh nhiều hơn hai, và đó là đúng.

#### Scenario: Sự cố xảy ra giữa một lô lớn

- **WHEN** Gateway chết giữa một lô có hàng nghìn lượt gọi
- **THEN** hệ thống SHALL gửi đúng một thư cho lần hỏng đó
- **AND** MUST NOT gửi thư cho từng lượt gọi hỏng

#### Scenario: Sự cố kéo dài nhiều nhịp dò

- **WHEN** Gateway hỏng suốt nhiều nhịp dò liên tiếp
- **THEN** hệ thống SHALL gửi đúng một thư
- **AND** số thư MUST NOT tỷ lệ với số nhịp dò

#### Scenario: Gateway chập chờn trong một khoảng ngắn

- **WHEN** Gateway hỏng rồi sống lại rồi lại hỏng trong một khoảng ngắn
- **THEN** mỗi lần đổi trạng thái SHALL sinh đúng một thư
- **AND** số thư SHALL tỷ lệ với số lần đổi trạng thái

#### Scenario: Mất một phần năng lực rồi mới hỏng hẳn

- **WHEN** một instance ngừng phục vụ, rồi sau đó Gateway hỏng hẳn
- **THEN** hệ thống SHALL gửi hai thư, mỗi lần đổi trạng thái một thư
- **AND** tiêu đề hai thư SHALL phân biệt được mức độ

#### Scenario: Sự cố ngắn hơn một nhịp dò

- **WHEN** sự cố bắt đầu và kết thúc trong khoảng ngắn hơn một nhịp dò
- **THEN** hệ thống có thể không gửi thư nào
- **AND** cửa sổ mù ấy SHALL được ghi trong tài liệu vận hành kèm con số, MUST NOT để người nhận
  tự phát hiện

### Requirement: Gửi thư hỏng không được làm hỏng công việc đang chạy

Việc gửi thư SHALL không bao giờ làm lỗi lan ra công việc đang chạy. Gửi hỏng thì hệ thống SHALL ghi
log rồi chạy tiếp.

Sau khi việc gửi thư rời khỏi agent, yêu cầu này đúng theo **cấu trúc**: tiến trình gửi thư không
chạy chung với bất kỳ việc xử lý dữ liệu nào. Yêu cầu vẫn giữ, vì nó còn áp cho chính vòng lặp dò —
gửi hỏng MUST NOT làm dừng việc dò.

#### Scenario: Máy chủ thư không phản hồi

- **WHEN** việc gửi thư thất bại vì bất kỳ lý do gì
- **THEN** tiến trình canh gác SHALL ghi log mức lỗi
- **AND** SHALL chạy tiếp nhịp dò sau
- **AND** lỗi gửi thư MUST NOT làm dừng bất kỳ agent nào

## REMOVED Requirements

### Requirement: Đường gửi thư thường đứng cạnh đường sẵn có, không thay thế

**Reason**: Yêu cầu này ràng buộc kiến trúc gửi thư **của agent CRM** — đường Microsoft Graph sẵn
có ở `src/notification.py` và đường SMTP thêm vào cạnh nó. Sau change này, agent không còn gửi thư
báo động nữa, nên ràng buộc "đứng cạnh, không thay thế" không còn đối tượng để áp.

Nó được thay bằng một ràng buộc hẹp hơn và đúng chỗ hơn, đã nằm trong yêu cầu của
`gateway-liveness-watch`: thông tin đăng nhập của máy chủ thư SHALL đọc từ biến môi trường và MUST
NOT nằm trong tệp nào được git theo dõi.

**Migration**: `src/notification.py` của CRM **giữ nguyên, không xoá** — `pipeline.py` vẫn dùng nó
cho thư lỗi của lô, việc khác hẳn việc báo động hạ tầng. Chỉ hai lệnh gọi `_notify(...)` trong
`src/llm.py` được gỡ. Tiến trình canh gác dùng SMTP qua thư viện chuẩn, không dùng lại mã của CRM.

### Requirement: Đường báo động phải được kiểm chứng bằng một thư thật

**Reason**: Yêu cầu này không mất, nó **chuyển chỗ**. Nó nay là điều kiện nghiệm thu của
`gateway-liveness-watch` và nằm trong `tasks.md` của change này, vì đối tượng nghiệm thu đã đổi từ
đường gửi thư của agent sang đường gửi thư của tiến trình canh gác.

**Migration**: Điều kiện giữ nguyên nội dung, không nới một chữ — thư rời khỏi máy MUST NOT được coi
là thư đã tới; nghiệm thu SHALL dựa trên việc người nhận xác nhận đã thấy thư, kể cả kiểm hộp thư
rác. Áp cho **cả hai** loại thư của tiến trình canh gác: thư sự cố và thư nhịp tim.
