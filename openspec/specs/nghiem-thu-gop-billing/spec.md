# nghiem-thu-gop-billing Specification

## Purpose
TBD - created by archiving change transform-billing-tu-console. Update Purpose after archive.
## Requirements
### Requirement: Không ghi file khi có bất kỳ phép kiểm nào thất bại

Script SHALL chạy toàn bộ phép kiểm **trước** khi ghi file đầu ra. Khi có bất kỳ phép kiểm nào thất bại, script SHALL thoát với mã lỗi khác 0 và MUST NOT để lại file đầu ra, kể cả file dở dang.

Một file gộp sai nhưng tồn tại còn nguy hiểm hơn không có file: bước sau (`nap_billing.py`) sẽ nạp nó vào database mà không biết.

#### Scenario: Một phép kiểm thất bại
- **WHEN** bất kỳ bất biến nào không đúng
- **THEN** không có file nào được tạo trong `data/da_xu_ly/billing/`, và tiến trình thoát với mã khác 0

#### Scenario: Toàn bộ phép kiểm đạt
- **WHEN** mọi bất biến đều đúng
- **THEN** file đầu ra được ghi, và script in ra tổng số dòng cùng tổng tiền

### Requirement: Bất biến đẳng thức tiền ở mức từng dòng

Với mỗi dòng, script SHALL kiểm `round(Cost − Savings programs − Other savings, 2) == Subtotal`, so sánh bằng `Decimal` chính xác ở độ chính xác xu, không dùng ngưỡng sai số.

Với những dòng có **cả hai** cột giảm giá bằng `0.00`, script SHALL kiểm thêm `Cost == round(Unrounded subtotal, 2)`.

Đo trên toàn bộ 2.259 dòng của bản export 05/08:

| Đẳng thức | Đúng trên |
|---|---|
| `Cost − Savings − Other == Unrounded subtotal` | **4 / 2259** |
| `round(Cost − Savings − Other, 2) == Subtotal` | 2259 / 2259 |
| `Cost == round(Unrounded subtotal, 2)` | 2259 / 2259 |

`Cost ($)` **cũng đã được làm tròn tới xu** như `Subtotal`, không giữ độ chính xác đầy đủ. Nên đẳng thức ở độ chính xác đầy đủ chỉ đúng trên 4 dòng — đúng ngẫu nhiên, ở những dòng `Unrounded` vừa vặn hai chữ số thập phân. Phép kiểm phải đặt ở độ chính xác xu, là độ chính xác thật mà Google công bố `Cost`.

**Giới hạn phải ghi nhận:** `Unrounded subtotal` là cột duy nhất mang giá trị dưới-xu, không cột nào khác đối chứng được nó ở độ chính xác đó. Script MUST NOT giả vờ kiểm được điều đó.

Đẳng thức thứ nhất mang giá trị ở tương lai: khi Gimasys cấp credit, nó vẫn đúng trong khi đẳng thức thứ hai sẽ tách ra — đó là lúc "giá niêm yết" và "tiền thật" khác nhau.

#### Scenario: Không có khoản giảm giá
- **WHEN** một dòng có `Savings programs = 0.00` và `Other savings = 0.00`
- **THEN** script kiểm cả `round(Cost, 2) == Subtotal` lẫn `Cost == round(Unrounded subtotal, 2)`

#### Scenario: Đẳng thức không đúng
- **WHEN** một dòng có `round(Cost − Savings − Other, 2) != Subtotal`
- **THEN** script dừng và in ra ngày, project, mã SKU cùng cả năm giá trị tiền của dòng đó

#### Scenario: Dòng có giảm giá thì không kiểm đẳng thức thứ hai
- **WHEN** một dòng có `Other savings != 0.00`
- **THEN** script bỏ qua phép kiểm `Cost == round(Unrounded subtotal, 2)` trên dòng đó, vì `Cost` là giá trước giảm còn `Unrounded` là tiền sau giảm

### Requirement: Bất biến làm tròn ở mức từng dòng

Với mỗi dòng, script SHALL kiểm `round(Unrounded subtotal, 2) == Subtotal`, dùng làm tròn nửa-lên (`ROUND_HALF_UP`) trên `Decimal`.

Phép kiểm này phát hiện được ngày Google đổi quy tắc làm tròn — điều mà một cột suy ra được sẽ không bao giờ lộ ra.

#### Scenario: Làm tròn khớp
- **WHEN** dòng có `Unrounded subtotal = 0.053087` và `Subtotal = 0.05`
- **THEN** phép kiểm đạt

#### Scenario: Làm tròn lệch
- **WHEN** `round(Unrounded, 2)` khác `Subtotal` ở bất kỳ dòng nào
- **THEN** script dừng và in ra dòng đó cùng cả hai giá trị

### Requirement: Cảnh báo khi xuất hiện khoản giảm giá

Khi bất kỳ dòng nào có `Savings programs != 0.00` hoặc `Other savings != 0.00`, script SHALL in cảnh báo nổi bật nêu số dòng liên quan và tổng số tiền được giảm, nhưng SHALL vẫn tiếp tục xử lý nếu các bất biến khác đều đúng.

Đây là sự kiện hợp lệ, không phải lỗi — nhưng nó đổi ý nghĩa của mọi con số chi phí phía sau (`chi_phi_usd` trở thành tiền **sau** giảm giá, khác `chi_phi_niem_yet_usd`), nên người vận hành phải biết.

#### Scenario: Xuất hiện credit lần đầu
- **WHEN** có dòng mang `Other savings = -1.50`
- **THEN** script in cảnh báo nêu số dòng có giảm giá và tổng tiền giảm, rồi tiếp tục và ghi file bình thường

### Requirement: Đối chiếu tổng từng project với file thô

Với mỗi file đầu vào, script SHALL kiểm rằng số dòng và tổng `Unrounded subtotal` của các dòng mang project tương ứng trong đầu ra **bằng đúng** số dòng và tổng của chính file thô đó.

Phép kiểm này bắt được mọi kiểu hỏng của bước gộp — mất dòng, nhân đôi dòng, gán nhầm project — bằng một phép so sánh duy nhất.

#### Scenario: Gộp đúng
- **WHEN** file `AI-sale_agent` có 864 dòng và tổng `Unrounded subtotal` là $125,3368
- **THEN** đầu ra có đúng 864 dòng mang `project = tranquil-post-471401-c1`, tổng đúng $125,3368

#### Scenario: Lệch số dòng hoặc lệch tiền
- **WHEN** số dòng hoặc tổng tiền của một project không khớp file thô tương ứng
- **THEN** script dừng và in ra tên project, cặp số dòng và cặp tổng tiền của cả hai phía

### Requirement: Đối chiếu với bản gộp tay hiện có

Script SHALL cung cấp một chế độ đối chiếu (ví dụ `--doi-chieu <đường dẫn>`) so kết quả với `data/billing/billing_gop_tru_CTDA.csv`.

Phép so SHALL thực hiện trên tập các bộ `(ngay, project, sku_id, so_luong, chi_phi_usd)` và SHALL báo đạt chỉ khi hai tập **trùng khít** — không dòng thừa, không dòng thiếu, không giá trị lệch.

Đây là bài kiểm tra hồi quy có sẵn và miễn phí: bản gộp tay hiện tại đã được dùng để dựng toàn bộ database, nên tái tạo đúng nó là bằng chứng script không làm thay đổi ý nghĩa dữ liệu.

#### Scenario: Trùng khít bản gộp tay
- **WHEN** chạy chế độ đối chiếu trên bộ 7 file thô hiện có
- **THEN** kết quả có đúng 2.259 dòng, tổng $270,9517, và không có dòng nào lệch so với `billing_gop_tru_CTDA.csv`

#### Scenario: Có dòng lệch
- **WHEN** phép đối chiếu tìm thấy dòng thừa, thiếu, hoặc lệch giá trị
- **THEN** script in ra tối đa 10 ví dụ cụ thể kèm cả hai phía, và thoát với mã khác 0

### Requirement: Thông điệp lỗi phải hành động được

Mọi thông điệp lỗi khiến script dừng SHALL nêu đủ: chuyện gì sai, ở dòng/file nào, giá trị thực tế so với giá trị mong đợi, và bước tiếp theo người vận hành cần làm.

Script MUST NOT dừng bằng thông điệp chỉ có mã định danh mà không có ngữ cảnh (ví dụ chỉ in mã SKU mà không in tên SKU và số tiền liên quan).

#### Scenario: Gặp SKU chưa phân loại được
- **WHEN** `suy_loai()` trả về `None` cho một SKU
- **THEN** thông điệp lỗi chứa mã SKU, tên SKU đầy đủ, số dòng và tổng tiền của SKU đó, kèm gợi ý cập nhật `db/quy_tac.py`

#### Scenario: Gặp tên hiển thị lạ
- **WHEN** phần cuối tên file không có trong bảng ánh xạ
- **THEN** thông điệp lỗi chứa tên hiển thị lạ, đường dẫn file, và danh sách các tên hiển thị đang được khai báo

