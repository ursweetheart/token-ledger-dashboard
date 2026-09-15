## ADDED Requirements

### Requirement: Image Gateway phải do CI đóng gói, không do máy của một người
Image LiteLLM mà Gateway chạy SHALL được CI đóng gói từ nhánh `Tuan-develop` của fork
`ursweetheart/litellm_rang_dong`, rồi đẩy lên GHCR. Image build trên máy một người MUST NOT là image
mà cấu hình theo git trỏ tới.

Lý do: image đang chạy trước change này, `litellm_tuan_test:gateway`, được build trên máy phát triển
từ một thư mục ngang hàng. Không có dấu vết nào nói nó build từ commit nào, hay từ nhánh nào.

#### Scenario: Đẩy code lên nhánh chính khi fork có commit chưa đóng gói
- **WHEN** code được đẩy lên `main` hoặc `Tuan-develop`
- **AND** nhãn ứng với commit đầu nhánh `Tuan-develop` của fork chưa có trên kho
- **THEN** CI SHALL build image từ commit đó và đẩy lên kho với nhãn là commit đó

#### Scenario: Mở pull request
- **WHEN** một pull request được mở hoặc cập nhật
- **THEN** CI MUST NOT đẩy image nào lên kho

### Requirement: Thiếu bản vá Sentinel thì không được đóng gói
CI SHALL kiểm `litellm/_redis.py` của fork có ký hiệu `_SENTINEL_IGNORED_CONNECTION_ARGS` **trước khi
build**. Không có thì kết quả MUST là hỏng và MUST NOT có image nào được đẩy lên kho.

Lý do: thiếu bản vá thì LiteLLM chết lúc khởi động với
`TypeError: Redis.__init__() got multiple values for argument 'host'`. Đo ngày 14/09/2026: nhánh
`litellm_internal_staging` của fork không có bản vá, và bản clone trên máy phát triển đang đứng ở
nhánh đó.

#### Scenario: Nhánh bị merge mất bản vá
- **WHEN** đầu nhánh `Tuan-develop` không còn `_SENTINEL_IGNORED_CONNECTION_ARGS` trong `litellm/_redis.py`
- **THEN** kết quả SHALL là hỏng trước bước build
- **AND** thông điệp SHALL nêu nhánh, commit, tệp và ký hiệu còn thiếu

#### Scenario: Phép canh đã từng đỏ thật
- **WHEN** change này được nghiệm thu
- **THEN** SHALL có ít nhất một lần chạy CI mà phép canh này báo hỏng có chủ ý, kèm mã lần chạy

### Requirement: Nhãn image gắn theo commit của fork và không bị ghi đè
Mỗi image SHALL mang nhãn là mã commit đầy đủ của fork mà nó được build từ đó. Một nhãn đã có trên kho
MUST NOT bị build hay đẩy lại. Kho MUST NOT có nhãn trôi kiểu `latest` do change này sinh ra.

Lý do: cùng nhãn phải luôn là cùng image, thì máy chủ mới quay lui được về một nhãn cũ mà biết chắc
mình nhận được gì. GHCR không tự cấm ghi đè nhãn, nên bước bỏ qua là thứ giữ tính chất này.

#### Scenario: Đẩy code dashboard mà fork không đổi
- **WHEN** CI chạy và nhãn ứng với đầu nhánh fork đã có trên kho
- **THEN** CI SHALL bỏ qua bước build và bước đẩy
- **AND** SHALL báo rõ là bỏ qua vì nhãn đã có, kèm nhãn đó

#### Scenario: Hỏi image được build từ đâu
- **WHEN** chạy `docker inspect` trên image kéo từ kho
- **THEN** nhãn `org.opencontainers.image.revision` SHALL là commit của fork
- **AND** nhãn `org.opencontainers.image.url` SHALL là địa chỉ của fork
- **AND** nhãn `org.opencontainers.image.source` SHALL là địa chỉ của repo chạy workflow, không phải
  của fork, vì GHCR dùng nhãn này để gắn gói vào repo, và `GITHUB_TOKEN` chỉ đẩy được vào gói gắn với
  repo chạy workflow

### Requirement: Compose không được phụ thuộc thư mục ngang hàng repo
`docker-compose.yml` MUST NOT build image Gateway từ một thư mục nằm ngoài repo. Nó SHALL trỏ tới một
nhãn cụ thể trên kho, và nhãn đó SHALL tồn tại trên kho.

Lý do: máy nào thiếu `../litellm_tuan_test` thì compose thoát ngay, kéo theo cả `postgres`, `api`,
`web`. Đây là nút chặn khiến lệnh triển khai tự động không được gọi profile `gateway`.

#### Scenario: Máy vừa clone repo, không có fork nào bên cạnh
- **WHEN** một máy chỉ có repo này chạy `docker compose --profile gateway config`
- **THEN** lệnh SHALL đạt
- **AND** `docker compose --profile gateway pull` SHALL kéo được image Gateway mà không cần đăng nhập kho

#### Scenario: Có người đưa lại `build:` trỏ ra ngoài repo
- **WHEN** khối `x-litellm` có `build:` hoặc `context:` trỏ ra ngoài thư mục repo
- **THEN** nhóm canh cấu hình của CI SHALL báo hỏng

#### Scenario: Compose ghim một nhãn chưa từng được build
- **WHEN** nhãn mặc định của image Gateway trong `docker-compose.yml` không tồn tại trên kho
- **THEN** CI SHALL báo hỏng và nêu nhãn đó

#### Scenario: Người phát triển thử một bản fork đang sửa
- **WHEN** người phát triển đặt biến `LITELLM_IMAGE` trỏ tới một image build tại chỗ
- **THEN** Gateway SHALL chạy bằng image đó
- **AND** MUST NOT phải sửa tệp nào theo git

### Requirement: Image công khai không được mang bí mật
Image Gateway SHALL không chứa khoá, mật khẩu hay tệp `.env` nào. Mọi bí mật SHALL đi vào lúc chạy qua
biến môi trường và volume. Gói trên kho MUST NOT được đặt công khai trước khi fork được quét bí mật đạt.

Lý do: Dockerfile của fork chép toàn bộ cây mã vào tầng build (`COPY . .`). Công khai một image là
không rút lại được, vì ai đã kéo thì đã có.

#### Scenario: Trước khi đặt gói công khai
- **WHEN** người sở hữu chuẩn bị đặt gói thành công khai
- **THEN** `tools/scan_secrets.py` trên fork tại commit được đóng gói SHALL đạt
- **AND** kết quả quét SHALL được ghi lại cùng commit đó

#### Scenario: Khởi động Gateway từ image công khai
- **WHEN** Gateway khởi động từ image kéo về từ kho
- **THEN** master key, salt key và khoá nhà cung cấp SHALL đến từ biến môi trường của máy chạy
- **AND** thiếu bất kỳ khoá bắt buộc nào thì entrypoint SHALL dừng hẳn, như trước change
