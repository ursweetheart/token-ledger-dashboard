# department-metric-provenance

## ADDED Requirements

### Requirement: Không đo được phải hiện khác bằng không

Mọi ô số trên bảng phòng ban SHALL phân biệt được hai trạng thái: **đã đo và bằng không**,
với **không có cách nào tính ra**. Ô không tính được SHALL hiện dấu `—` kèm lời giải thích
truy cập được, và MUST NOT hiện `0`.

Lý do: tiền chỉ tồn tại ở hoá đơn Google, mà hoá đơn tính theo project và không ghi ai
gọi — nên `/api/usage-by-account` không có cột `cost_usd`. Trước 20/08/2026 hàm `cost()`
trả về `0` cho cả hai trạng thái, nên phòng ban `Nghiên cứu thị trường` hiện `0 ₫` ngay
cạnh **49 request và 525,9 nghìn token**. Đã đối chiếu toàn bảng: 9/9 hàng khớp quy luật
"chỉ đơn vị kỹ thuật mới có tiền", không ngoại lệ — tức con số `0 ₫` ở phòng ban thật là
bịa ra chứ không phải đo được.

#### Scenario: Phòng ban có lưu lượng nhưng không tính được tiền

- **WHEN** một đơn vị có request hoặc token lớn hơn 0
- **AND** không tài khoản nào của nó cho ra được giá trị tiền
- **THEN** ô tiền SHALL hiện `—`
- **AND** ô đó SHALL mang lời giải thích nói rõ **vì sao lần này không tính được**

Lời giải thích SHALL bám theo lý do thật tại thời điểm đó, không được ghi cứng một câu:

| Giai đoạn | Lý do `—` xuất hiện |
|---|---|
| Sau nhóm 1 (`0e11c5a`) | Chưa nối được model với đơn giá — tiền chỉ có ở mức project |
| Sau nhóm 8 | Chỉ còn khi một `model_id` không tra được trong `ref_price` |

Sau nhóm 8, câu *"tiền chỉ có ở mức project nên không chia được theo người dùng"* **thành
sai** — lúc đó tiền chia được. Đây là chỗ hai nhóm task của cùng change này mâu thuẫn
nhau nếu quên sửa lời giải thích.

#### Scenario: Phòng ban không có lưu lượng nào

- **WHEN** một đơn vị có 0 request và 0 token
- **THEN** ô tiền SHALL hiện `0`
- **AND** MUST NOT hiện `—`, vì ở đây số 0 là đáp án đúng chứ không phải chỗ trống

#### Scenario: Hàm tính tiền không âm thầm coi "không biết" là 0

- **WHEN** mã nguồn cần biết một dòng có tính được tiền hay không
- **THEN** phải có một hàm trả về `null` cho trường hợp không tính được
- **AND** hàm trả về số SHALL vẫn tồn tại để mọi phép cộng đang có giữ nguyên hành vi,
  vì trong JavaScript `0 + null === 0` nên đổi kiểu trả về sẽ không ném lỗi ở đâu cả

### Requirement: Tử số và mẫu số của tỷ lệ áp dụng đếm cùng một tập

Mọi tỷ lệ áp dụng hiện trên giao diện SHALL có tử số và mẫu số lọc theo **cùng một điều
kiện**. Tỷ lệ áp dụng MUST NOT vượt quá 100%.

Tài khoản có phát sinh request nhưng không nằm trong danh bạ SHALL không được cộng vào tử
số, và SHALL được nêu riêng để người đọc biết chúng tồn tại.

Lý do: mẫu số lấy từ `DEPT_PROVISIONED` lọc `in_directory && !is_shared`, trong khi tử số
trước 20/08/2026 không lọc gì. Hàng `Chưa quy được` vì thế hiện `3/1 · 300%`.
`backend/store.py` `adoption()` không mắc lỗi này — nó giữ `outside_directory` thành cột
riêng — và `scripts/audit_db.py` vẫn báo đạt, vì phép kiểm đó soi database chứ không soi
trình duyệt.

#### Scenario: Tài khoản có request nhưng không có trong danh bạ

- **WHEN** một đơn vị có tài khoản phát sinh request mà không có mục trong danh bạ
- **THEN** tài khoản đó MUST NOT được tính vào tử số
- **AND** số lượng tài khoản như vậy SHALL được nêu trong lời giải thích của ô
- **AND** tỷ lệ hiện ra SHALL nhỏ hơn hoặc bằng 100%

#### Scenario: Không hàng nào vượt 100%

- **WHEN** quét toàn bộ bảng phòng ban ở bất kỳ khoảng ngày nào
- **THEN** không ô tỷ lệ áp dụng nào SHALL lớn hơn 100%

### Requirement: Tiền theo phòng ban suy từ bảng giá, và tự khai là suy

Ô tiền của một đơn vị SHALL được tính bằng cách nhân token với `ref_price`, thực hiện ở
**mức từng dòng** `/api/usage-by-account` rồi mới cộng lên. MUST NOT tính từ token đã cộng
gộp của một tài khoản.

Ô đó SHALL nói rõ con số **suy từ bảng giá**, không phải lấy từ hoá đơn.

Lý do phải tính ở mức dòng: một tài khoản dùng nhiều model, và đơn giá chênh nhau tới 12
lần (`gemini-2.5-flash-lite` $0,1 so với `gemini-2.5-pro` $1,25 cho mỗi triệu token vào).
Nhân tổng token đã gộp với bất kỳ đơn giá nào cũng ra một con số không model nào có.

Lý do tin được phép suy này: `ref_price` lấy từ Cloud Billing Catalog của Google
(`price_source='google'` cho cả 10 model), không gõ tay. Đối chiếu 965 dòng có cả hai vế:
tổng suy $291,6462 so với hoá đơn $291,9856 — lệch **−0,1%**, lệch **trung vị mỗi dòng
0,0%**, dòng lệch nhiều nhất 6,4%.

#### Scenario: Mỗi dòng usage được áp đúng đơn giá của model nó

- **WHEN** tính tiền cho một đơn vị
- **THEN** mỗi dòng `/api/usage-by-account` SHALL được nhân với đơn giá của chính
  `model_id` của nó
- **AND** kết quả mới được cộng lên mức tài khoản rồi mức đơn vị

#### Scenario: Con số tự khai là suy chứ không phải hoá đơn

- **WHEN** ô tiền của một đơn vị hiện ra một con số
- **THEN** phải có dấu hiệu nhìn thấy được nói con số này suy từ bảng giá
- **AND** MUST NOT trình bày như thể lấy trực tiếp từ hoá đơn

#### Scenario: Model không tra được đơn giá

- **WHEN** một dòng mang `model_id` không có trong `ref_price`
- **THEN** dòng đó MUST NOT được tính là 0 đồng
- **AND** đơn vị chứa nó SHALL rơi về trạng thái không tính được, theo requirement
  *"Không đo được phải hiện khác bằng không"*

### Requirement: Nói rõ phần tiền không thuộc phòng ban nào

Màn hình có cột tiền theo phòng ban SHALL nêu được tỷ lệ tiền **không quy được về phòng
ban nào**, và SHALL không để người đọc tưởng tổng các phòng ban bằng tổng chi phí.

Màn hình SHALL đồng thời nêu được phần tiền **suy ra mà không có dòng hoá đơn nào**.

Lý do, đo ngày 20/08/2026 trên kỳ 19/07–17/08:

| | USD | |
|---|---:|---|
| Hoá đơn, **quy được** về một phòng ban | $15,1333 | **24,2%** |
| Hoá đơn, **không quy được** | $47,5109 | **75,8%** |
| | **$62,6442** | tổng hoá đơn |
| Suy ra cho Trợ lý ảo Ralli | +$1,2988 | **ngoài hoá đơn** — `tla-ralli` chưa nối Google Billing |

Phần không quy được đi qua hoá đơn Google, nơi tính theo project và không ghi ai gọi, nên
**không có chiều người dùng để mà chia** — giới hạn của nguồn, không phải thiếu sót của
phép tính.

Phần của Trợ lý ảo Ralli là chuyện ngược lại: lưu lượng thật, chi phí thật, nhưng **không
hoá đơn nào ghi nó**. Phép suy từ bảng giá là cách duy nhất nhìn thấy khoản này.

Vì vậy tổng các phòng ban lệch khỏi tổng hoá đơn theo **cả hai chiều** — thiếu phần không
quy được, thừa phần Ralli. Không nói ra thì người xem đi tìm một lỗi không tồn tại, hoặc
tin rằng công ty chỉ tiêu $16,43.

#### Scenario: Người đọc cộng các phòng ban lại

- **WHEN** cộng tiền của mọi phòng ban trong kỳ
- **THEN** kết quả SHALL không được trình bày như thể bằng tổng chi phí của kỳ
- **AND** màn hình SHALL nêu được **hai** phần chênh: phần hoá đơn không quy được về phòng
  ban nào, và phần suy ra cho agent không có hoá đơn

#### Scenario: Agent không có hoá đơn vẫn phải nhìn thấy được

- **WHEN** một agent có lưu lượng nhưng không có dòng hoá đơn nào
- **THEN** tiền suy ra của nó SHALL vẫn hiện trên bảng phòng ban
- **AND** SHALL không bị trình bày như một phần của tổng hoá đơn

#### Scenario: Nhãn cột không hứa nhiều hơn số liệu trả lời được

- **WHEN** đặt tên hoặc mô tả cột tiền theo phòng ban
- **THEN** mô tả SHALL nói phạm vi là phần lưu lượng **có ghi được người dùng**
- **AND** MUST NOT trình bày như thể đó là toàn bộ chi phí của phòng ban

### Requirement: Đơn vị kỹ thuật lấy tỷ lệ áp dụng từ backend

Hàng của đơn vị kỹ thuật SHALL lấy số tài khoản hoạt động và số tài khoản được cấp từ
`/api/adoption`, không tự tính lại.

Lý do: `/api/adoption` đã trả đúng đáp án cho agent một-người-dùng — `kind='service'`,
`provisioned=1`, `active=1` nếu có phát sinh. Frontend tự tính sẽ ra `—`, vì tài khoản
dịch vụ mang `is_shared=1` và không có trong danh bạ nên rơi khỏi `DEPT_PROVISIONED`.
Hàng `Đơn vị sử dụng Sale Agent` vì thế hiện `—` ngay cạnh **14.264 request**.

#### Scenario: Agent một-người-dùng đang hoạt động trong kỳ

- **WHEN** một đơn vị kỹ thuật thuộc agent chạy bằng một tài khoản dịch vụ
- **AND** agent đó có phát sinh request
- **THEN** ô tỷ lệ áp dụng SHALL hiện `1/1`
- **AND** MUST NOT hiện `—` hay `0/1`

#### Scenario: Hàng không được vừa nói có lưu lượng vừa nói không ai dùng

- **WHEN** một hàng hiện số request lớn hơn 0
- **THEN** ô tỷ lệ áp dụng của chính hàng đó MUST NOT hiện 0 tài khoản hoạt động, trừ khi
  lời giải thích nêu rõ lưu lượng đó đến từ tài khoản ngoài danh bạ
