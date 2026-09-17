## ADDED Requirements

### Requirement: Load balancer phải theo được instance qua một lần dựng lại container

`gateway-lb` SHALL tiếp tục gửi request tới một instance LiteLLM sau khi container của instance ấy
được **dựng lại**, mà không cần ai khởi động lại `gateway-lb`.

Lý do: biến môi trường chỉ đặt được lúc tạo container, nên thêm một khoá `KEY_*` cho agent mới là
buộc phải dựng lại cả hai instance. Container dựng lại nhận địa chỉ IP mới. Nếu load balancer chỉ
phân giải tên một lần lúc khởi động, nó sẽ giữ địa chỉ cũ mãi mãi và instance khoẻ kia trở thành vô
hình với nó.

#### Scenario: Dựng lại một instance khi load balancer đang chạy
- **WHEN** container của một instance LiteLLM được dựng lại và trở lại trạng thái `healthy`
- **THEN** `gateway-lb` SHALL gửi request tới instance đó trở lại
- **AND** MUST NOT đòi hỏi một lần khởi động lại `gateway-lb`

#### Scenario: Dựng lại cả hai instance lần lượt
- **WHEN** instance thứ nhất được dựng lại và trở lại `healthy`, rồi tới instance thứ hai
- **THEN** cả hai SHALL cùng nhận được request sau khi việc dựng lại xong
- **AND** Gateway MUST NOT có khoảng thời gian nào không phục vụ được, miễn là mỗi lần dựng lại
  chỉ đụng một instance và chờ nó `healthy` trước khi sang instance kia

#### Scenario: Cửa sổ giao thời phải có giới hạn trên
- **WHEN** một instance vừa đổi địa chỉ mà load balancer chưa kịp biết
- **THEN** khoảng thời gian load balancer còn gửi tới địa chỉ cũ SHALL có giới hạn trên do cấu hình
  quyết định
- **AND** MUST NOT kéo dài tới khi có người can thiệp

### Requirement: Hai tệp cấu hình nginx phải khai việc phân giải tên theo cùng một cách

Một tệp cấu hình nginx trong `docker/gateway/` SHALL khai `resolver` khi nó có khối `upstream` trỏ
tới upstream bằng tên; khối `upstream` ấy SHALL nằm trong một `zone`; và mỗi dòng `server` trỏ bằng
tên SHALL được đánh dấu là cần phân giải lại. Một phép canh trong CI SHALL chặn vi phạm quay lại.

Lý do: hai tệp cùng làm một việc mà viết hai kiểu thì chỗ viết thiếu sẽ không ai phát hiện — nó
không báo lỗi, không ghi log, và chỉ lộ ra đúng lúc có người dựng lại container. Ghim luật theo tính
chất, không theo tên tệp, để khối `upstream` thêm sau cũng bị xét.

#### Scenario: Thêm một khối upstream trỏ bằng tên
- **WHEN** một khối `upstream` mới được thêm vào, trỏ tới một dịch vụ bằng tên
- **THEN** phép canh SHALL báo hỏng nếu khối ấy thiếu `zone`, hoặc dòng `server` thiếu dấu hiệu phân
  giải lại, hoặc tệp chứa nó thiếu `resolver`

#### Scenario: Upstream trỏ bằng địa chỉ IP
- **WHEN** một dòng `server` trong khối `upstream` trỏ bằng địa chỉ IP thay vì tên
- **THEN** phép canh MUST NOT đòi dòng ấy phân giải lại

#### Scenario: Một tệp trôi khỏi tệp kia
- **WHEN** dấu hiệu phân giải lại bị gỡ khỏi một trong hai tệp
- **THEN** CI SHALL đỏ

### Requirement: Nghiệm thu phải chứng minh bằng một lần dựng lại thật

Việc nghiệm thu SHALL dựa trên số lượt gọi **đếm được ở từng instance** sau một lần dựng lại thật.
Nó MUST NOT kết luận từ việc request vẫn thành công, từ trạng thái `healthy` của container, hay từ
`/lb-health` và `/health/liveliness`.

Lý do: chế độ hỏng ở đây không làm request thất bại. Một instance biến mất khỏi vòng chia tải thì
instance còn lại nhận hết, và mọi dấu hiệu bề mặt vẫn xanh. Chỉ số lượt đếm theo từng instance mới
phân biệt được "chia đều" với "dồn một chỗ".

#### Scenario: Mọi dấu hiệu bề mặt đều xanh nhưng một nửa năng lực đã mất
- **WHEN** một instance không còn nhận được request vì load balancer giữ địa chỉ cũ
- **THEN** `docker compose ps`, `/lb-health` và `/health/liveliness` của cả hai instance SHALL vẫn
  báo bình thường
- **AND** vì vậy chúng MUST NOT được dùng làm bằng chứng nghiệm thu

#### Scenario: Đếm theo từng instance
- **WHEN** nghiệm thu sau một lần dựng lại
- **THEN** phép đo SHALL gửi nhiều lượt gọi và đếm số lượt vào **từng** instance
- **AND** cả hai instance SHALL có số lượt lớn hơn không

#### Scenario: Đo cả hai chiều
- **WHEN** báo cáo kết quả nghiệm thu
- **THEN** phép đo SHALL được lặp cho cả instance thứ nhất và instance thứ hai
- **AND** MUST NOT kết luận từ một chiều duy nhất
