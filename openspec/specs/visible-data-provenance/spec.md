# visible-data-provenance Specification

## Purpose
TBD - created by archiving change label-derived-cost-across-dashboard. Update Purpose after archive.
## Requirements
### Requirement: Mọi con số tiền tự khai nguồn gốc

Mọi ô, thẻ, biểu đồ và dòng xuất CSV có chứa tiền SHALL cho biết phần nào đến từ **hoá
đơn** và phần nào **suy từ bảng giá**. MUST NOT trình bày hai loại giống hệt nhau.

Lý do: đo 20/08/2026 trên toàn kỳ 01/01–17/08, **28,2% số tiền hiển thị** ($114,4076 trên
$406,3932) không đến từ hoá đơn nào — nó được nhân ra từ `ref_price`. Và nó không rải đều:
Trợ lý ảo Ralli **100%** suy ra, Trợ Lý Ảo Hợp Đồng **77,7%**, trong khi Chatbot Contact
Center chỉ 2,8%.

#### Scenario: Ô tiền có chứa phần suy ra

- **WHEN** một ô tiền gộp từ nhiều dòng và có ít nhất một dòng không có `cost_usd`
- **THEN** ô SHALL mang dấu hiệu nhìn thấy được
- **AND** lời giải thích SHALL nêu **tỷ lệ** phần suy ra, không chỉ nêu là có

#### Scenario: Ô tiền hoàn toàn từ hoá đơn

- **WHEN** mọi dòng gộp vào ô đều có `cost_usd`
- **THEN** ô MUST NOT mang dấu hiệu suy ra

#### Scenario: Số mang ra ngoài không mất dấu vết

- **WHEN** người dùng xuất CSV
- **THEN** file SHALL có cột phân biệt phần tiền từ hoá đơn với phần suy ra

### Requirement: Phân biệt hai lý do khiến tiền phải suy ra

Giao diện SHALL phân biệt **hoá đơn chưa về** với **agent chưa nối Google Billing**. Hai
tình huống này trông giống nhau trên màn hình nhưng đòi hai hành động khác nhau.

| Lý do | Tự hết không | Việc phải làm |
|---|---|---|
| Hoá đơn Google trễ ~1 ngày | **Có** — vài ngày nữa dòng đó sẽ có hoá đơn | Không phải làm gì |
| Agent chưa nối Google Billing | **Không** — suy ra mãi mãi | Nối billing cho project đó |

Lý do: `tla-ralli` có project trên GCP nhưng chưa nối billing, nên **$7,6254 chi phí thật
của Trợ lý ảo Ralli không có dòng hoá đơn nào**. Gộp nó chung với "hoá đơn hôm nay chưa
về" là che mất một việc cần người xử lý.

#### Scenario: Agent không có hoá đơn nào trong cả kỳ

- **WHEN** một agent có lưu lượng nhưng không dòng nào có `cost_usd` trong kỳ đang xem
- **THEN** lời giải thích SHALL nói đây là agent **chưa nối billing**
- **AND** MUST NOT dùng cùng lời với trường hợp hoá đơn về trễ

#### Scenario: Ngày mới nhất luôn chưa có hoá đơn

- **WHEN** ngày mới nhất của kỳ có 100% tiền là suy ra
- **THEN** giải thích SHALL nói hoá đơn về trễ khoảng một ngày
- **AND** MUST NOT khiến người xem tưởng có lỗi dữ liệu

### Requirement: Thẻ tiền nói độ tin của chính kỳ đang xem

Thẻ tổng chi phí SHALL nêu tỷ lệ suy ra **của kỳ người dùng đang chọn**, không phải của
toàn bộ dữ liệu.

Lý do: tỷ lệ suy ra lệch rất mạnh theo ngày — **22/228 ngày có hơn một nửa số tiền là suy
ra**, trong đó 17/08 là 100%, 20/06 là 99,7%, 02/08 là 85,7%. Người chọn *"7 ngày gần
nhất"* dễ rơi trúng vùng đó, và một con số trung bình cả kỳ sẽ nói dối về chính kỳ họ đang
xem. Đây đúng loại lỗi đã mắc ngày 17/08: tỷ lệ ước tính tính trên 224 ngày trong khi thẻ
tiền chỉ hiện kỳ được chọn.

#### Scenario: Người dùng đổi khoảng ngày

- **WHEN** người dùng đổi kỳ
- **THEN** tỷ lệ suy ra SHALL tính lại theo đúng kỳ mới
- **AND** SHALL dùng cùng tập dòng mà con số tiền trên thẻ đang dùng

### Requirement: Không gắn nhãn tới mức thành nhiễu

Dấu hiệu suy ra MUST NOT xuất hiện dày tới mức người đọc bỏ qua nó.

Lý do: 224/1.189 dòng là suy ra, nhưng chúng dồn vào ít agent và ít ngày. Gắn dấu lên mọi
ô gộp có dính một dòng suy ra sẽ làm gần như cả bảng có dấu — và một dấu hiệu xuất hiện ở
khắp nơi thì không còn là dấu hiệu.

#### Scenario: Phần suy ra không đáng kể

- **WHEN** phần suy ra dưới một ngưỡng đã ghi rõ trong mã nguồn
- **THEN** ô SHALL không mang dấu hiệu ở mức nhìn thấy ngay
- **AND** lời giải thích khi trỏ chuột SHALL vẫn nêu đủ con số

### Requirement: Không nạp được dữ liệu thì phải nói ra trên màn hình

Khi không nạp được dữ liệu từ backend, dashboard SHALL hiện tình trạng đó **trên giao
diện**. Ghi `console.warn` là KHÔNG đủ — nó đòi người xem mở DevTools mới thấy.

Thông báo SHALL nói được ba điều: không nối được backend, địa chỉ đã thử, và cách khắc
phục. Dashboard MUST NOT hiện bất kỳ con số nào trong trạng thái này.

Yêu cầu này là phần quan trọng nhất của change; việc xoá dữ liệu nhúng chỉ là hệ quả. Cơ
chế cũ tại `web/js/api.js` bắt mọi lỗi rồi `return null`, nên bốn trường hợp rất khác nhau
— backend tắt, một endpoint lỗi, database thiếu ngày, mạng chặn — đều trông y hệt nhau trên
màn hình: một bảng số đầy đủ và hợp lý.

#### Scenario: Backend tắt

- **WHEN** mở dashboard với backend không chạy
- **THEN** giao diện hiện thông báo không nối được backend, kèm địa chỉ đã thử
- **AND** không vùng nào của trang hiện số liệu

#### Scenario: Một endpoint lỗi

- **WHEN** backend chạy nhưng một endpoint trả về mã lỗi HTTP
- **THEN** giao diện nói rõ endpoint nào lỗi và mã trả về là gì
- **AND** MUST NOT hiện số liệu phần còn lại như thể đầy đủ

#### Scenario: Database chưa có dữ liệu sử dụng

- **WHEN** backend nối được database nhưng `/api/health` không trả về khoảng ngày nào cho
  usage
- **THEN** giao diện nói database chưa có dữ liệu sử dụng
- **AND** phân biệt được trường hợp này với trường hợp không nối được backend

#### Scenario: Mở bằng file:// không còn giả vờ chạy được

- **WHEN** mở `web/index.html` bằng cách bấm đúp
- **THEN** giao diện nói cần chạy backend và máy chủ tĩnh
- **AND** MUST NOT hiện số liệu nào

### Requirement: Dữ liệu đang xem phải tự khai khoảng ngày

Khi nạp được dữ liệu, dashboard SHALL hiện khoảng ngày của dữ liệu đang xem ở nơi thấy
được mà không phải bấm vào đâu.

Mục đích là để "số cũ" không trông giống "số mới": nếu đường ống chưa chạy mấy hôm, người
xem phải thấy được điều đó từ chính màn hình.

#### Scenario: Khoảng ngày hiện cùng số liệu

- **WHEN** dashboard nạp xong từ backend
- **THEN** giao diện hiện ngày đầu và ngày cuối của dữ liệu
- **AND** khoảng đó khớp `ranges.usage` mà `/api/health` trả về

### Requirement: Không khẳng định điều gì về dữ liệu mà dữ liệu không bảo đảm

Giao diện MUST NOT chứa chữ gán cứng khẳng định về **trạng thái** hoặc **độ mới** của dữ
liệu. Mọi phát biểu như vậy SHALL do dữ liệu thật điều khiển, hoặc bị bỏ đi.

Đã soát trên trang thật 17/08/2026 và tìm ba chỗ vi phạm, tất cả là chữ tĩnh trong
`web/index.html`:

- `"Gateway hoạt động"` (`:276`) — không có gateway nào tồn tại trong hệ thống hiện tại
- `"Cập nhật realtime · lần cuối 2 phút trước"` (`:277`) — `"2 phút trước"` là hằng số; dữ
  liệu cũ bao lâu nó cũng nói vậy
- `"Nhập liệu thủ công theo ngày… Dữ liệu lưu trong trình duyệt"` (`:260`) — mô tả luồng
  nhập tay + Excel đã không còn dùng

#### Scenario: Không còn khẳng định trạng thái gán cứng

- **WHEN** tìm trong `web/index.html` các chuỗi `Gateway hoạt động`, `realtime`,
  `lần cuối`, `phút trước`
- **THEN** không chuỗi nào còn là chữ tĩnh khẳng định trạng thái hệ thống
- **AND** phát biểu nào còn lại về độ mới của dữ liệu đều tính từ ngày thật của dữ liệu

#### Scenario: Độ mới của dữ liệu tính từ dữ liệu

- **WHEN** dữ liệu mới nhất trong database là ngày `D` và hôm nay là `D + 4`
- **THEN** giao diện nói được rằng dữ liệu cũ 4 ngày
- **AND** MUST NOT hiện bất kỳ chữ nào ngụ ý dữ liệu vừa được cập nhật

### Requirement: Nhãn của một con số phải nói đúng con số đó gồm những gì

Nhãn giải thích công thức của một chỉ số SHALL liệt kê đủ mọi thành phần thực sự được cộng
vào. Nhãn thiếu thành phần khiến người đọc tự tính lại và ra số khác — mà không biết mình
sai ở đâu.

Đã đo hai chỗ sai trên trang thật:

- Thẻ **TỔNG TOKEN** ghi `"= Σ token vào + token ra"` (`index.html:454`) nhưng con số hiện
  ra (45.685.588 cho kỳ 01/08→13/08) thực tế là `input + output + cached`. Tự tính theo
  nhãn sẽ ra 35.614.156 — **hụt 22%**. Con số đúng, nhãn sai.
- Thẻ **TỔNG CHI PHÍ** ghi `"= Σ (token × đơn giá) theo bảng giá"` và dán nhãn nguồn
  `BigQuery Billing`, nhưng nó là số **pha trộn**: xem requirement dưới.

#### Scenario: Nhãn tổng token kể đủ ba thành phần

- **WHEN** đọc nhãn công thức của thẻ tổng token
- **THEN** nhãn nêu cả token vào, token ra, **và** token cache
- **AND** tự tính theo nhãn ra đúng con số đang hiện

### Requirement: Số tiền pha trộn phải tách rõ phần hoá đơn và phần ước tính

Khi một con số tiền gồm cả tiền lấy từ hoá đơn và tiền suy ra từ bảng giá, giao diện SHALL
nói rõ tỷ lệ hai phần. MUST NOT dán một nhãn nguồn duy nhất cho cả con số.

Đo được ngày 17/08/2026, kỳ 01/08 → 13/08:

| Thành phần | Số dòng | Tiền | Tỷ lệ |
|---|---|---|---|
| Từ hoá đơn (`cost_usd` có giá trị) | 66 / 93 | 26,94 US$ | 67,8% |
| Ước tính từ bảng giá (`cost_usd` NULL) | 27 / 93 | 12,78 US$ | **32,2%** |
| Hiện trên màn hình | 93 | **39,72 US$** | dán nhãn `BigQuery Billing` |

Cả kỳ 01/01 → 13/08: 219 / 1.161 dòng = **18,9%** phải ước tính. Backend đã đánh dấu sẵn
từng dòng bằng `token_estimated`; tầng hiển thị đang bỏ cờ đó đi.

Ngày càng gần hôm nay thì tỷ lệ ước tính càng cao, vì hoá đơn về sau ~1 ngày — nên con số
của kỳ ngắn gần đây là con số **kém tin nhất**, mà hiện nó lại trông giống nhất với một con
số đã chốt.

#### Scenario: Tỷ lệ ước tính hiện cùng số tiền

- **WHEN** một kỳ có ít nhất một dòng `cost_usd` NULL
- **THEN** giao diện nói rõ bao nhiêu phần trăm số tiền là ước tính từ bảng giá
- **AND** MUST NOT dán nhãn nguồn `BigQuery Billing` cho toàn bộ con số

#### Scenario: Kỳ toàn hoá đơn không bị dán nhãn ước tính

- **WHEN** mọi dòng trong kỳ đều có `cost_usd` từ hoá đơn
- **THEN** giao diện nói số tiền hoàn toàn từ hoá đơn
- **AND** không hiện cảnh báo ước tính nào

### Requirement: Cảnh báo độ phủ và nguồn số liệu phải đi cùng số

Dashboard SHALL chuyển tiếp các cảnh báo mà backend đã sinh ra, thay vì bỏ chúng đi. Tối
thiểu SHALL hiện được: cảnh báo độ phủ từ `/api/health`, và dấu hiệu dòng nào là số ước
tính (`token_estimated`) chứ không phải số đo.

Backend đã tính sẵn những thứ này và đã gắn cảnh báo độ phủ trực tiếp vào
`/api/usage-by-account` để người gọi không phải nhớ đi hỏi `/api/health`. Bỏ chúng ở tầng
hiển thị là làm mất công đó, và làm người xem tin con số hơn mức nó đáng được.

#### Scenario: Bảng theo người dùng nói rõ độ phủ

- **WHEN** xem phần số liệu quy về từng người
- **THEN** giao diện hiện cảnh báo độ phủ mà `/api/usage-by-account` trả kèm
- **AND** MUST NOT hiện bảng đó như thể phủ toàn bộ lưu lượng

#### Scenario: Số ước tính phân biệt được với số đo

- **WHEN** một dòng có `token_estimated` là đúng
- **THEN** giao diện đánh dấu dòng đó là số ước tính
- **AND** người xem phân biệt được nó với dòng lấy từ hoá đơn
