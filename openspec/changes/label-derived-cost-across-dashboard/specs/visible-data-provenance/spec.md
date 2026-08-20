# visible-data-provenance

## ADDED Requirements

### Requirement: Mọi con số tiền tự khai nguồn gốc

Mọi ô, thẻ, biểu đồ và dòng xuất CSV có chứa tiền SHALL cho biết phần nào đến từ **hoá
đơn** và phần nào **suy từ bảng giá**. MUST NOT trình bày hai loại giống hệt nhau.

Lý do: đo 20/08/2026 trên toàn kỳ 01/01–17/08, **28,2% số tiền hiển thị** ($114,4465 trên
$406,4321) không đến từ hoá đơn nào — nó được nhân ra từ `ref_price`. Và nó không rải đều:
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

Lý do: `tla-ralli` có project trên GCP nhưng chưa nối billing, nên **$7,6643 chi phí thật
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
