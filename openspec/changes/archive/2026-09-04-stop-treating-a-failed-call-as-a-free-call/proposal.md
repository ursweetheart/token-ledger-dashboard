## Why

Bảng tổng hợp loại lượt gọi hỏng ra khỏi số liệu sử dụng — `fact_usage_daily` ngày 31/08
ghi `gateway 45.187 token / 38 calls` trong khi `fact_call` có 41 dòng. Loại ra là đúng,
nhưng đi kèm nó là một giả định chưa ai nói thành lời: **lượt hỏng không tiêu gì**. Đối
chiếu với sổ của chính nhà cung cấp ngày 04/09/2026 cho thấy giả định đó sai: **12,21%**
token của ngày đo nằm ở chỗ này.

Hiện chỉ một agent đi qua Gateway. Khi cả 8 agent đi qua, giả định này áp cho mọi agent
và mọi project — nên phải đặt tên và bắt được nó trước lúc đó, không phải sau.

## What Changes

**Bằng chứng đã đo (04/09/2026, ngày dữ liệu 31/08/2026)**

| | Google | LiteLLM | `fact_call` |
|---|---|---|---|
| số request | 41 — **tất cả `response_code=200`** | 44 (39 thành công + 5 hỏng) | 41 |
| token vào | 47.613 | 41.717 | 41.679 |
| token ra | 3.922 | 3.523 | 3.522 |

- Google **không thấy một lỗi nào**. Vậy 2 trong 41 lượt Google phục vụ thành công đã bị
  LiteLLM ghi là hỏng với 0 token.
- Giờ 07h và 09h khớp **đến từng token** (`5.895/411` và `5.875/404`), nên cách đếm không
  sai hệ thống. Toàn bộ lệch dồn vào giờ 02h.
- Lệch của riêng giờ 02h là `+5.864` vào và `+399` ra. Một cặp gọi `233 + 5.643 / 3 + 400`
  cộng ra `5.876 / 403` — **xấp xỉ**, dư 12 token vào và 4 token ra, không khớp tuyệt đối.
  Hai dòng hỏng lúc `02:27` nằm chen giữa cặp `02:24` và cặp `02:29`, dạng của một lần thử
  lại. Đây là bằng chứng **nghiêng về** một cặp bị ghi 0, không phải phép chứng minh.
- Cả 5 dòng hỏng đều ghi `duration_ms = 0`, kể cả hai dòng đã tiêu token thật.

**Phát hiện thứ hai, tìm được lúc soát lại artifact 04/09:** bộ nạp của ta cũng đánh rơi bản
ghi trong im lặng. Ba dòng có trong `LiteLLM_SpendLogs` mà không có trong `fact_call` — trong
đó `lG-UarHhIYXmosUPv4ihmQ8` là một lượt **thành công, có tag định danh đầy đủ, mang 25 token
thật**. Chỉ 1 trong 3 dòng thiếu tag, nên lời giải thích "rớt vì thiếu định danh agent" không
đúng cho hai dòng còn lại. Tổng **39 token** biến mất ở khâu nạp và không phép kiểm nào đếm
chúng. Cùng *hình dạng* mất mát im lặng, nhưng **nguyên nhân khác** với lỗi đặt tên ở trên.

**Thay đổi**

- Đặt tên và ghi lại hình dạng lỗi: **lượt hỏng không phải lượt miễn phí**. Loại lượt hỏng
  khỏi bảng tổng hợp vẫn giữ nguyên, nhưng từ nay nó tạo ra một khoản **thiếu hụt đã biết**
  phải đo, không phải một khoảng trống được coi bằng không.
- Mở `scripts/pull_monitoring.py` cho nguồn đối chứng: thêm tham số chọn tài khoản Google
  và cho phép khai project ngoài danh sách 7 project sản xuất. Project của Gateway
  (`project-e62bad30-a591-407b-ba7`) nằm trên tài khoản thứ hai, script hiện không với tới.
- Thêm phép kiểm trong `scripts/audit_db.py` so `fact_call` với sổ nhà cung cấp theo ngày,
  trên **cả ba trục**: số lượt, token vào, token ra. Khai rõ mẫu số và báo *chưa kiểm được*
  khi không có ngày giao nhau, theo đúng kỷ luật đã dùng ở `gateway-cache-reconciliation`.
- Bộ nạp Gateway phải **đếm và in ra** số bản ghi nó không nạp được cùng tổng token của chúng,
  và một phép kiểm mới so số dòng sổ nguồn với số dòng `fact_call` theo ngày.
- **KHÔNG** suy đoán token cho lượt hỏng và **KHÔNG** sửa số đã nạp. Ta biết tổng thiếu bao
  nhiêu, nhưng không biết thiếu ở dòng nào — gán số cho từng dòng là bịa.

## Capabilities

### New Capabilities

- `provider-ledger-reconciliation`: Đối chiếu sổ Gateway với sổ của chính nhà cung cấp theo
  ngày trên ba trục (số lượt, token vào, token ra), quy tắc khai mẫu số, và cách báo khi
  chưa có ngày giao nhau.
- `provider-source-reach`: `pull_monitoring.py` phải với được tới project nằm ngoài danh
  sách sản xuất và trên tài khoản Google khác, mà không làm hỏng lần kéo mặc định.

### Modified Capabilities

- `gateway-call-outcomes`: yêu cầu *"Lượt gọi hỏng MUST NOT lọt vào số liệu sử dụng"* được
  bổ sung: việc loại ra tạo ra một khoản thiếu hụt đã biết, và khoản đó phải đo được chứ
  không được ngầm hiểu bằng không.
- `gateway-ledger-loading`: yêu cầu *"Lượt gọi hỏng phải bị loại nhưng vẫn được đếm"* được
  **sửa cho khớp hành vi thật** — spec đang viết bộ nạp *chỉ* nạp lượt thành công, nhưng đo
  được `fact_call` có chứa 3 dòng hỏng của ngày 31/08; câu đó đã lạc hậu từ migration 006.
  Bổ sung thêm: đếm số dòng là chưa đủ, và bản ghi không nạp được phải được đếm.

## Impact

- `scripts/pull_monitoring.py` — thêm tham số tài khoản và project, giữ nguyên hành vi mặc định.
- `scripts/audit_db.py` — nhóm phép kiểm mới đối chiếu với nhà cung cấp.
- `db/` — bảng lưu số của nhà cung cấp theo ngày để phép kiểm có thứ để so; migration chỉ tiến.
- `docs/reference/` — ghi lại hình dạng lỗi và cách tái tạo phép đo.
- `Master Plan API Gateway.xlsx` — STT 7 dòng 20 (bộ kiểm tự động) và STT 4 dòng 11 (ghi đủ trường).
- **Không đụng** `web/`, không đụng backend đọc, không sửa dữ liệu đã nạp.
