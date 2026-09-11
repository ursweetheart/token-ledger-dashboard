# gateway-shared-state-continuity

## ADDED Requirements

### Requirement: Trạng thái dùng chung phải sống sót khi một Redis chết

Hệ thống SHALL tự chuyển vai sang bản sao **không cần người can thiệp** khi tiến trình
Redis đang giữ vai master dừng hoạt động mà máy chủ vẫn sống, và các instance LiteLLM
SHALL tự đi theo địa chỉ master mới mà không phải khởi động lại.

Lý do: `docker-compose.yml:365` đang ghi nhận giới hạn *"Primary chết thì replica KHÔNG tự
lên thay - phải đợi tay"*. Kế hoạch GĐ5 dòng 13 yêu cầu có bản sao; phần tự thay thế chưa
làm.

Mức nghiêm trọng đã được đo và là THẤP — tắt hẳn Redis thì Gateway vẫn phục vụ (9/10 lượt
HTTP 200, p50 0,87 s), và toàn bộ dữ liệu trong Redis có hạn sống ≤ 60 giây. Yêu cầu này
tồn tại vì đây là điều khoản chưa hoàn thành của kế hoạch, không vì nó là lỗ hổng nguy
hiểm.

#### Scenario: Master chết đột ngột

- **WHEN** tiến trình Redis đang giữ vai master bị giết cứng
- **THEN** một bản sao SHALL được thăng lên làm master
- **AND** việc thăng cấp SHALL xảy ra không cần lệnh tay nào
- **AND** thời gian từ lúc chết tới lúc có master mới SHALL được ghi lại thành con số

#### Scenario: LiteLLM đi theo master mới

- **WHEN** vai master đã chuyển sang một địa chỉ khác
- **THEN** các instance LiteLLM SHALL nối vào master mới
- **AND** MUST NOT cần khởi động lại instance nào
- **AND** lượt gọi thật sau đó SHALL trả về 200

#### Scenario: Master cũ quay lại không được làm master thứ hai

- **WHEN** tiến trình Redis đã chết được dựng lại
- **THEN** nó SHALL nhận vai bản sao của master hiện hành
- **AND** MUST NOT tiếp tục nhận lệnh ghi như một master độc lập

Lý do: hai Redis cùng nhận ghi thì mỗi instance LiteLLM đếm vào một cái, và hạn mức bị đếm
sai theo cách không phép kiểm nào hiện có phát hiện được. Trạng thái đó **tệ hơn** trạng
thái trước khi làm change này.

### Requirement: Vai trò sau chuyển đổi phải sống sót qua việc dựng lại container

Vai trò master/replica của mỗi Redis SHALL được ghi vào nơi bền vững, sao cho một lần dựng
lại container **không đảo ngược** kết quả chuyển vai.

Lý do: hôm nay cả hai Redis chạy hoàn toàn bằng cờ dòng lệnh, và bản sao mang
`--replicaof redis 6379` ghi cứng (`docker-compose.yml:375-377`). Redis giữ trạng thái
`replicaof` bằng cách ghi lại vào file cấu hình của chính nó — không có file thì không ghi
được. Hệ quả: mọi lần thăng cấp đều bị xoá sạch ở lần `restart` kế tiếp, mà `restart:
unless-stopped` khiến việc đó xảy ra thường xuyên.

Đây là kiểu hỏng im lặng: cơ chế chuyển vai vẫn dựng được, log vẫn sạch, và chỉ vô dụng
đúng lúc cần đến.

#### Scenario: Dựng lại container sau khi đã chuyển vai

- **WHEN** một bản sao đã được thăng lên master
- **AND** container của nó được dựng lại
- **THEN** nó SHALL vẫn giữ vai master
- **AND** MUST NOT quay về làm bản sao của master cũ

#### Scenario: Không còn cờ vai trò nào ghi cứng ở dòng lệnh

- **WHEN** đọc khai báo của cả hai dịch vụ Redis
- **THEN** không dịch vụ nào SHALL mang cờ `--replicaof` ở dòng lệnh
- **AND** tệp cấu hình của chúng SHALL nằm trên một volume ghi được

### Requirement: Nghiệm thu bằng một lần chuyển vai thật

Việc chuyển vai SHALL được nghiệm thu bằng cách **giết master thật** rồi quan sát hệ thống,
MUST NOT nghiệm thu bằng việc các tiến trình giám sát khởi động được.

Lý do: một cụm giám sát cấu hình sai vẫn khởi động sạch, log vẫn đẹp, và truy vấn trạng
thái vẫn trả về đúng. Cùng hạng lỗi với `enable_tag_filtering` phát hiện ngày 30/08 — mặc
định tắt, thiếu thì cấu hình `tags` bị bỏ qua hoàn toàn và im lặng, trong khi mọi dấu hiệu
bên ngoài đều bình thường.

#### Scenario: Phép kiểm chấp nhận được

- **WHEN** chứng minh yêu cầu này đã đạt
- **THEN** bằng chứng SHALL bao gồm một lần giết master và đo thời gian tới khi có master mới
- **AND** SHALL bao gồm lượt gọi thật thành công sau khi chuyển vai
- **AND** SHALL bao gồm một lần dựng lại container chứng minh vai trò không bị đảo ngược

#### Scenario: Bằng chứng không chấp nhận được

- **WHEN** bằng chứng chỉ gồm việc tiến trình giám sát đang chạy, hoặc truy vấn trạng thái
  trả về đúng
- **THEN** yêu cầu này MUST NOT được coi là đã đạt

### Requirement: Nói rõ điều change này KHÔNG bảo vệ

Tài liệu của hệ thống SHALL nêu rõ rằng cơ chế này **không** bảo vệ trước việc mất máy chủ.

Lý do: mọi tiến trình giám sát đều chạy trên cùng một máy với cả hai Redis. Máy chết là
chết tất cả. Một người đọc thấy "đã có cơ chế tự chuyển vai" rất dễ kết luận nhầm rằng
Redis đã có tính sẵn sàng cao, rồi bỏ qua rủi ro lớn hơn nhiều là chỉ có một máy chủ.

#### Scenario: Người đọc tài liệu tra mức bảo vệ

- **WHEN** đọc phần mô tả cơ chế chuyển vai
- **THEN** tài liệu SHALL nêu kịch bản duy nhất được bảo vệ là *tiến trình Redis hỏng vĩnh
  viễn trong khi máy chủ còn sống*
- **AND** SHALL nêu rõ mất máy chủ vẫn là mất toàn bộ
