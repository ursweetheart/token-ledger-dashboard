## MODIFIED Requirements

### Requirement: Lượt gọi hỏng phải bị loại nhưng vẫn được đếm
Bộ nạp SHALL nạp mọi lượt gọi của sổ nguồn kèm kết cục của chúng, và lượt hỏng MUST NOT đóng
góp vào lưu lượng thật ở bảng tổng hợp theo ngày. Câu cũ *"chỉ nạp lượt gọi có trạng thái
thành công"* đã lạc hậu từ migration 006 — đo được 04/09/2026: `fact_call` nguồn gateway ngày
31/08 chứa **3 dòng hỏng** bên cạnh 38 dòng thành công, và `fact_usage_daily` ghi 38 calls.

Đếm **số lượng** lượt hỏng là chưa đủ. Một dòng hỏng có thể mang token thật mà sổ ghi bằng 0,
nên số lượt hỏng không nói được gì về lượng token đã mất. Báo cáo của lần chạy SHALL nêu số
lượt hỏng **kèm số token mà sổ ghi cho chúng**, và SHALL nói rõ rằng con số ấy là *điều sổ
khai*, không phải *điều đã tiêu*.

Bộ nạp SHALL đếm và in ra **số bản ghi của sổ nguồn mà nó không nạp được**, kèm tổng token của
chúng và lý do từng nhóm. Bản ghi rơi mất trong im lặng MUST NOT được chấp nhận: đo được
05/09/2026 trên **toàn sổ** có **6 bản ghi** không vào được `fact_call`, mang tổng **760
token** — trong đó một bản ghi là lượt **thành công mang 25 token** — và trước change này
không phép kiểm nào phát hiện ra. Riêng ngày 31/08 phần đó là 3 bản ghi / 39 token.

Nguyên nhân **đã chứng minh, không phải suy đoán**: cả 6 bản ghi đều **không có tag nào khớp
`dim_agent.code`**, và `fact_call.agent_id` là `NOT NULL`. Nhận định trước đó — *"một bản ghi
là lượt thành công **có tag định danh đầy đủ**"* — là **SAI**: nó đếm mọi tag, kể cả
`User-Agent:` do LiteLLM tự thêm. Chạy lại với mốc nạp rút hẳn (`--full`) vẫn cho `inserted 0`,
nên hai giả thuyết *mốc nước* và *ranh giới ngày* đều **bị bác bỏ**.

Đây là một **khoản nợ đã biết, chưa trả**: lưu lượng không quy được về agent nào cũng không
phải lưu lượng miễn phí — cùng hình dạng lỗi với `failed_is_not_free`, chỉ khác trục. Sửa được
nó cần một agent "không quy được" hoặc `agent_id` cho phép NULL, cả hai đều ngoài phạm vi
change này. Cho tới lúc đó, bộ nạp SHALL nêu khoản nợ ấy ra ở mọi lần chạy.

Bộ nạp SHALL loại **tường minh** những bản ghi mà sổ nguồn tự nhân đôi. Đo được: LiteLLM ghi
thêm một dòng cho cú cache hit, mang chính `request_id` của dòng gốc cộng hậu tố
`_cache_hit<epoch>` và **lặp lại nguyên token** (1 dòng, 352 token, dòng gốc tồn tại với đúng
352 token; nhà cung cấp xác nhận độc lập rằng ngày đó họ phục vụ 1 lượt). Bản sao ấy MUST NOT
được loại nhờ một điều kiện chẳng liên quan — hôm nay nó rớt vì thiếu tag định danh, nên ngày
nào khâu định danh được nới ra thì nó sẽ theo cùng cửa đó mà vào và đếm đôi, trong khi tổng
vẫn "khớp sổ nguồn" vì chính sổ nguồn đã đếm đôi.

#### Scenario: Sổ có lẫn lượt gọi hỏng
- **WHEN** sổ chứa cả lượt gọi thành công và lượt gọi hỏng
- **THEN** cả hai SHALL vào bảng lượt gọi kèm kết cục, chỉ lượt thành công SHALL đóng góp vào
  bảng tổng hợp theo ngày, và báo cáo của lần chạy SHALL nêu số lượt hỏng

#### Scenario: Bản ghi nguồn không nạp được
- **WHEN** một bản ghi của sổ nguồn không vào được bảng lượt gọi vì bất kỳ lý do gì
- **THEN** báo cáo của lần chạy SHALL nêu số bản ghi đó, tổng token của chúng và lý do, và
  MUST NOT bỏ qua trong im lặng

#### Scenario: Điều kiện lọc dựa trên giá trị đo được
- **WHEN** bộ nạp xác định một dòng là thành công
- **THEN** nó SHALL so trạng thái với giá trị thật mà sổ ghi, và MUST NOT giả định trạng thái
  thành công được biểu diễn bằng giá trị rỗng

#### Scenario: Báo cáo nêu cả token của lượt hỏng
- **WHEN** lần chạy loại ra một số lượt hỏng
- **THEN** báo cáo SHALL in cả số lượt lẫn tổng token mà sổ ghi cho những lượt đó

#### Scenario: Lượt hỏng ghi 0 token và 0 mili-giây
- **WHEN** một lượt hỏng mang 0 token và 0 mili-giây trong sổ
- **THEN** bộ nạp MUST NOT kết luận rằng lượt đó chưa tới nhà cung cấp, vì hai giá trị ấy là
  điều sổ khai chứ không phải điều đã đo

#### Scenario: Bản ghi bị sổ nguồn nhân đôi
- **WHEN** sổ nguồn chứa hai bản ghi cho cùng một lượt gọi, bản thứ hai mang `request_id` của
  bản gốc kèm hậu tố và lặp lại nguyên token
- **THEN** bộ nạp SHALL loại bản sao đó **theo đúng lý do là bản sao**, đếm nó riêng, và MUST
  NOT dựa vào một điều kiện lọc khác tình cờ cũng loại nó

#### Scenario: Lưu lượng không quy được về agent nào
- **WHEN** một bản ghi thành công mang token thật nhưng không có tag nào khớp một agent
- **THEN** bộ nạp SHALL nêu nó ra kèm token, và MUST NOT để lần chạy trông như đã nạp trọn vẹn
