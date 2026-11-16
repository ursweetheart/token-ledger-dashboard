## ADDED Requirements

### Requirement: Đọc và ghi hạn mức đi qua worker, không qua master key ở `api`

Mọi đường đọc và ghi hạn mức của dashboard SHALL lấy và sửa dữ liệu khoá thông qua worker trên host, không gọi thẳng API quản trị của Gateway. Điều này áp dụng cho `GET /api/quota`, `POST /api/quota` và `POST /api/quota/top-up`. Backend `api` MUST NOT giữ master key của Gateway và MUST NOT có đường nào gọi `/key/*` hay `/config/*` của Gateway. Chứng danh và hình dạng dữ liệu của các endpoint này SHALL giữ nguyên để frontend không đổi.

Lý do: master key trong container `api` cho phép tạo đường chuyển tiếp rò khoá Google (đã chứng minh trên
máy dev 03/11/2026). Worker vốn đã giữ master key và là nơi duy nhất nên giữ nó.

#### Scenario: Đọc danh sách hạn mức khi worker đang chạy
- **WHEN** người gọi có khoá dashboard hợp lệ đọc `GET /api/quota`
- **THEN** `api` SHALL lấy danh sách khoá qua worker và trả về cùng hình dạng dữ liệu như trước change này

#### Scenario: Đặt hạn mức khi worker đang chạy
- **WHEN** người gọi đặt hạn mức cho một khoá không mang tiền tố `connection-`
- **THEN** `api` SHALL nhờ worker sửa `metadata` của khoá đó và trả về hạn mức cùng nhật ký mới

#### Scenario: Worker không chạy
- **WHEN** worker không với tới được và người gọi đọc hoặc sửa hạn mức
- **THEN** hệ thống SHALL trả 503 với thông báo rõ rằng cần worker

#### Scenario: `api` không có đường tới API quản trị Gateway
- **WHEN** rà toàn bộ mã của `backend/` đang chạy trong container `api`
- **THEN** SHALL không có lệnh gọi nào tới `/key/*` hoặc `/config/*` của Gateway, và không nơi nào đọc `LITELLM_MASTER_KEY`

### Requirement: Bộ canh hạn mức đọc qua worker và báo khi không đọc được

Dịch vụ `quota-watch` (`scripts/watch_quota.py`) SHALL đọc hạn mức và số đã tiêu thông qua RPC `quota-list` của worker, bằng cùng `CONNECTION_WORKER_URL` và `CONNECTION_WORKER_KEY` với container `api`. Nó MUST NOT giữ `LITELLM_MASTER_KEY` và MUST NOT gọi `/key/*` của Gateway. Khi không đọc được hạn mức, nó MUST NOT đoán bậc và MUST NOT gửi thư bậc nào; sau hai nhịp hỏng liên tiếp nó SHALL gửi đúng một thư nói rằng cảnh báo đang mù, và một đợt hỏng mới sau khi đã đọc lại được SHALL được báo lại.

Lý do (chốt 16/11/2026, phương án PA2): việc của bộ canh chỉ là đọc ba con số, còn master key thì tạo được đường chuyển tiếp rò khoá Google. Giữ master key ở đúng một nơi (worker) là mục tiêu của change này. Cái giá là bộ canh phụ thuộc worker, nên sự im lặng lúc worker tắt phải được thay bằng một thư.

#### Scenario: Đọc hạn mức khi worker đang chạy
- **WHEN** `quota-watch` chạy một nhịp và worker trả lời
- **THEN** nó SHALL lấy danh sách khoá bằng RPC `quota-list` và so bậc như trước change này

#### Scenario: Không có master key trong môi trường của `quota-watch`
- **WHEN** kiểm biến môi trường của container `quota-watch` đang chạy
- **THEN** SHALL không có `LITELLM_MASTER_KEY`

#### Scenario: Worker tắt một nhịp
- **WHEN** một nhịp không đọc được hạn mức
- **THEN** bậc đã lưu của mọi khoá SHALL giữ nguyên và không thư nào được gửi

#### Scenario: Worker tắt kéo dài
- **WHEN** hai nhịp liên tiếp không đọc được hạn mức
- **THEN** hệ thống SHALL gửi đúng một thư báo cảnh báo đang mù, và các nhịp hỏng tiếp theo của cùng đợt MUST NOT gửi thêm

## MODIFIED Requirements

### Requirement: Đường ghi hạn mức của dashboard không sửa key do tab Kết nối quản lý

Endpoint ghi hạn mức của dashboard (đặt thành, cộng thêm) MUST NOT thay đổi hạn mức của Virtual Key do
tab Kết nối agent cấp. Key như vậy SHALL được nhận diện bằng tiền tố tên `connection-` do worker đặt.
Phép từ chối SHALL do worker quyết định, xảy ra trước mọi lệnh gọi tới Gateway, và `api` SHALL chuyển mã
409 kèm lời chỉ tới tab Kết nối agent cho người gọi. Danh sách hạn mức SHALL vẫn liệt kê các key này để xem.

Lý do: key do tab Kết nối cấp chỉ được sửa bằng khoá quản trị, có audit, và tab đó lưu hạn mức để hiển
thị. Một đường sửa thứ hai bằng khoá xem dashboard vừa vượt quyền vừa làm số hiển thị sai. Sau khi đường
ghi chuyển qua worker, chính worker là nơi thi hành phép từ chối này.

#### Scenario: Đặt hạn mức cho key do tab Kết nối cấp
- **WHEN** người gọi có khoá dashboard hợp lệ gửi yêu cầu đặt hạn mức cho key `connection-…`
- **THEN** hệ thống SHALL trả 409 và nêu rằng key do tab Kết nối agent quản lý
- **AND** MUST NOT gửi lệnh nào tới Gateway

#### Scenario: Cộng thêm hạn mức cho key do tab Kết nối cấp
- **WHEN** người gọi gửi yêu cầu cộng thêm hạn mức cho key `connection-…`
- **THEN** hệ thống SHALL trả 409 như trên và hạn mức trên Gateway giữ nguyên

#### Scenario: Key khác vẫn sửa được
- **WHEN** người gọi đặt hạn mức cho một key không mang tiền tố `connection-`
- **THEN** hệ thống SHALL sửa như trước change này

#### Scenario: Key do tab Kết nối cấp vẫn hiện trong danh sách
- **WHEN** người gọi đọc danh sách hạn mức
- **THEN** các key `connection-…` SHALL có mặt với hạn mức và số đã tiêu
