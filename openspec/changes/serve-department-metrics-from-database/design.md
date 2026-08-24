# Thiết kế

## 1. Nguyên tắc chi phối cả ba lỗi

> **Không đo được và bằng không là hai chuyện. Màn hình phải phân biệt được.**

Đây là biến thể thứ ba của cùng một nguyên tắc dự án đã trả giá hai lần:

| Lần | Nơi | Biểu hiện |
|---|---|---|
| 14/08 | `dim_agent.has_google_source` | Ralli không có nguồn đối chứng, view phải trả `-` chứ không phải `0%` |
| 20/08 sáng | `account.kind` | 6 agent một-người-dùng bị đếm vào "không quy được", độ phủ báo 12,4% thay vì 98,5% |
| 20/08 chiều | `cost()` frontend | Phòng ban thật báo `0 ₫` cạnh 525,9 nghìn token |

Và nguyên tắc thứ hai, đã ghi trong `backend/store.py`:

> **KHÔNG TÍNH LẠI CÁI DATABASE ĐÃ TÍNH.**

Frontend đang vi phạm nó ở đúng chỗ backend làm cẩn thận nhất — chỉ tiêu tỷ lệ áp dụng.

## 2. Ba quyết định

### 2.1. `cost()` giữ hợp đồng cũ, thêm `costOrNull()` bên cạnh

**Phương án đã chọn.** `cost()` vẫn trả về số; `costOrNull()` trả `null` khi không tính
được. Chỗ nào cần phân biệt thì gọi hàm sau.

**Vì sao không đổi thẳng `cost()` thành trả `null`:** nó được gọi ở hàng chục chỗ đang
cộng dồn (`a.cost += cost(r)`). Trong JavaScript `0 + null === 0`, nên đổi kiểu trả về sẽ
**không ném lỗi ở đâu cả** — mọi phép cộng vẫn chạy, chỉ âm thầm coi `null` là 0. Đó đúng
là loại hỏng mà change này sinh ra để chống.

### 2.2. Đơn vị không có lưu lượng vẫn hiện `0 ₫`

Không phải mọi `0 ₫` đều sai. Với đơn vị **không có request và không có token**, số 0 là
đáp án đúng — hiện `—` ở đó là đổi một thông tin có thật thành một chỗ trống.

Ranh giới: `costKnown = known > 0 || (requests === 0 && tokens === 0)`.

Kiểm chứng trên trang thật: `Kế hoạch` và `Trung tâm R&D` (0 request) giữ `0 ₫`;
`Nghiên cứu thị trường`, `TTDL&ĐHS`, `TT&TMĐT` (có request) đổi sang `—`.

### 2.3. Cây tổ chức — HOÃN, vì lập luận ban đầu đã bị bác bỏ

> **Bản đầu viết:** *"33 mục `UNIT_ALIASES` tồn tại **chỉ vì** frontend khớp bằng chuỗi
> tên. Có `unit_id` thì chúng không còn việc gì để làm."*
>
> **Sai.** Đo ngày 20/08/2026, trước khi viết một dòng code nào.

`dim_unit` **không phải một cây**. Nó là hai, cộng thêm trùng lặp bên trong một cây:

```
   agent 5  Tro Ly Ao Hop Dong     20 don vi that,  BON goc
            Cong ty CPBD PN Rang Dong · TT C4LED · TT&TMDT · TTDL&DHS

   agent 8  Tro ly ao Ralli       102 don vi that,  mot goc
            Toan cong ty

   TAM ten ton tai o CA HAI cay:
       CN Can Tho · CN Nha Trang · CN Tien Giang · CN Da Nang
       TT3 · Vung 1 · Vung 2 · Vung 3
   Va TT1, TT2 trung NGAY BEN TRONG cay cua Ralli.
```

Còn `ORG_UNITS` (108 đơn vị) là **một cây đã gộp sẵn bằng tay**.

`db/01_schema.sql` nói thẳng điều này ngay tại bảng `dim_unit`: *"Cùng một phòng ban ngoài
đời có thể có 2 dòng ở 2 cây khác nhau."* Database **cố ý** giữ chúng riêng.

**Vậy `UNIT_ALIASES` làm hai việc, không phải một:**

| Việc | `unit_id` có thay được không |
|---|---|
| Hoà giải viết tắt: `PBH1` ↔ `Phòng Bán hàng 1` ↔ `Phòng BH1` | ✅ Có |
| **Gộp hai cây tổ chức thành một cái nhìn công ty** | ❌ Không — hai cây không có khoá chung nào |

Thay `ORG_UNITS` bằng `dim_unit` sẽ cho ra **hai cây rời với 8 nhánh trùng tên**, không
phải một cây sạch hơn.

**Một chi tiết làm nhẹ vấn đề:** 892/937 tài khoản nằm ở cây của Trợ lý ảo Ralli, 45 ở cây
Trợ Lý Ảo Hợp Đồng — và trong 8 tên trùng, bản của agent 5 đều có **0 tài khoản**. Nên
phần trùng chủ yếu là trùng *hình dạng cây*, không phải trùng dữ liệu; `account.unit_id`
đã chọn sẵn một bên theo quy tắc tất định từ 14/08.

**Quyết định 20/08/2026: HOÃN việc thay cây.** Câu *"Vùng 1 của Hợp Đồng và Vùng 1 của
Ralli có phải một phòng không"* là câu hỏi **nghiệp vụ**, không phải kỹ thuật. Đoán sai thì
tiền chảy sang nhánh khác — đúng kiểu lệch thứ ba đã cảnh báo ở §3, kiểu không mọc không
mất nên không ai thấy.

Khi làm, hai hướng còn lại:

| | Hướng | Được | Mất |
|---|---|---|---|
| **A** | Đưa bảng ánh xạ **vào database** (cột `canonical_unit_id` hoặc bảng `unit_alias`) | Một nguồn thật; frontend hết gõ cứng | Đụng `db/`; phải có người quyết cặp nào gộp cặp nào |
| **B** | Hiện **hai cây**, ghi rõ cây của app nào | Trung thực với dữ liệu; không cần ánh xạ | Tab Phòng ban đổi nghĩa từ *"công ty"* sang *"theo từng app"* |

**Bài học, giống hệt §5.1:** lập luận nghe hợp lý vẫn phải đo trước khi dùng nó để quyết
phạm vi. Lần này cái sai lộ ra ở bước đầu tiên của việc apply — nếu không dừng lại đo thì
đã viết xong `api.js` và `app.js` rồi mới phát hiện cây không gộp được.

## 3. Chỗ nguy hiểm nhất: 108 ↔ 130 không phải quan hệ con của nhau

Đây là bước bắt buộc **trước** khi xoá `ORG_UNITS`, và là chỗ change này dễ hỏng nhất.

Chênh 22 dòng không nói được điều gì cho tới khi biết chúng nằm ở đâu. Ba khả năng, và
mỗi khả năng đòi một cách xử lý khác nhau:

```
   trong database, KHÔNG có trong ORG_UNITS
     -> đơn vị mới hoặc đơn vị chưa từng hiện. Thay xong sẽ MỌC THÊM hàng.
        Phải xác nhận là mọc đúng, không phải mọc do dòng kỹ thuật lọt vào.

   trong ORG_UNITS, KHÔNG có trong database
     -> hoặc đã giải thể, hoặc tên bị lệch. Thay xong sẽ MẤT hàng, và một số
        usage sẽ không tìm được đơn vị.

   có ở cả hai nhưng KHÁC CHA hoặc KHÁC CẤP
     -> nguy hiểm nhất. Không mọc, không mất, chỉ CỘNG SANG NHÁNH KHÁC.
        Tổng toàn công ty vẫn đúng; số của từng phòng ban đổi mà không ai báo.
```

Bảng đối chiếu phải sinh ra **trước**, không phải sau khi thay rồi mới đi tìm hiểu vì sao
số lệch.

## 4. Tỷ lệ áp dụng: dùng lại số của backend ở đâu, tự tính ở đâu

`/api/adoption` trả theo **agent**, bảng lại theo **đơn vị**. Không thay thế thẳng được.

| Loại hàng | Nguồn | Lý do |
|---|---|---|
| Đơn vị **kỹ thuật** (`is_technical`) | `/api/adoption` theo `agent_id` | Quan hệ đơn vị ↔ agent là 1:1. Backend đã trả đúng `1/1` cho agent một-người-dùng |
| Phòng ban **thật** | Tự tính | Tỷ lệ áp dụng theo agent không phân rã được xuống từng phòng ban |

Chỗ tự tính vẫn phải theo **đúng quy tắc backend đang dùng**: loại `is_shared` khỏi cả tử
lẫn mẫu, và tài khoản có request mà không có trong danh bạ thì để riêng chứ không cộng vào
tử số.

## 5. Tiền theo phòng ban: suy từ bảng giá — quyết định đã ĐẢO

### 5.1. Lập luận đầu tiên, và phép đo bác bỏ nó

Bản đầu của tài liệu này loại việc suy tiền ra khỏi phạm vi, với ba lý do. Hai trong ba
lý do đó **sai**, và cái sai chỉ lộ ra khi đi đo thay vì ngồi suy:

| Đã lập luận | Đo được 20/08/2026 |
|---|---|
| *"App không phơi model"* | **66/66** dòng Trợ lý ảo Ralli và **10/10** dòng Trợ Lý Ảo Hợp Đồng trong `/api/usage-by-account` đều có `model_id`. Không sót dòng nào |
| *"Đó là thêm một con số ước tính mới"* | `ref_price` lấy từ Cloud Billing Catalog của Google — `price_source='google'` cho cả 10 model, hiệu lực 2026-08-13. Không phải giá gõ tay |
| *"Sai số làm bẩn màn hình"* | Đối chiếu **965 dòng** có cả hai vế: tổng $291,6462 (suy) vs $291,9856 (hoá đơn) = **−0,1%**. Lệch **trung vị mỗi dòng: 0,0%**. Dòng tệ nhất: 6,4% |

Lý do thứ nhất là một **giả định về dữ liệu chưa kiểm** — và nó sai. Ghi lại ở đây vì đó
là bài học đắt hơn cả quyết định: *lập luận nghe hợp lý vẫn phải đo trước khi dùng nó để
loại một việc ra khỏi phạm vi.*

Với sai số 0,1%, chữ **"ước tính" dùng sai**. Phép nhân này không phỏng đoán gì — nó dựng
lại chính hoá đơn từ cùng bảng giá mà Google dùng để phát hành hoá đơn đó.

### 5.2. Nghẽn thật nằm ở lắp ráp, không ở dữ liệu

```
   /api/usage-by-account       76 dong, MOI dong co model_id + input + output
              │
              ▼
   api.js dung doi tuong tai khoan
       m: ""                    <-- model bi bo
       ti/to cong gop MOI model  <-- mat luon phan tach
              │
              ▼
   cost(u)  ->  state.pricing[""]  ->  undefined  ->  0
```

Nên phép tính **phải làm ở mức dòng rồi mới cộng vào tài khoản**. Không suy được từ
`u.ti`/`u.to` đã gộp, vì một tài khoản dùng nhiều model với đơn giá chênh nhau 12,5 lần
(`flash-lite` $0,10 vs `pro` $1,25 cho mỗi triệu token vào).

Chi tiết còn lại: `state.pricing` khoá theo **tên model**, API trả `model_id` — cần một
bước tra qua `/api/catalog`.

### 5.3. Hai điều kiện, và vì sao điều kiện thứ hai mới là điều kiện khó

**① Ô phải nói rõ số này suy từ bảng giá, không lấy từ hoá đơn.** Dễ — thêm nhãn.

**② Phải nói được rằng phần lớn tiền KHÔNG thuộc phòng ban nào — và nói cho đúng.**

Bản đầu của mục này viết *"$16,43 / $62,64 = 26,2%"*. **Sai**, và sai đúng kiểu mà change
này đang đi sửa: tử số chứa một khoản không nằm trong mẫu số.

```
   HOA DON cua ky                             $62,6442   100%
   ├── quy duoc ve mot phong ban              $15,1333    24,2%  <- toan bo la
   │                                                              Tro Ly Ao Hop Dong
   └── KHONG quy duoc                         $47,5109    75,8%  <- di qua hoa don Google,
                                                                    noi khong ghi ai goi

   NGOAI hoa don, chi thay duoc bang phep suy:
       Tro ly ao Ralli                        $ 1,2988   <- project tla-ralli CHUA NOI
                                                            Google Billing: hoa don $0,00

   Cong moi phong ban tren man hinh  =  $15,1333 + $1,2988  =  $16,4321
```

Hai điều rút ra, và điều thứ hai dễ bị bỏ qua:

1. **Phần không quy được là 75,8%**, không phải 73,8%. Nó không có chiều người dùng để mà
   chia — cùng đúng giới hạn đã tạo ra ba nhóm độ phủ (a)/(b)/(c) trong `health()`.
2. **$1,2988 của Trợ lý ảo Ralli nằm NGOÀI hoá đơn.** Lưu lượng thật, chi phí thật, nhưng
   `tla-ralli` chưa nối Google Billing nên tổng hoá đơn không thấy nó. Phép suy từ bảng
   giá là **cách duy nhất** nhìn thấy khoản này — tức cột tiền theo phòng ban không chỉ
   chia nhỏ cái đã biết, nó còn phơi ra một khoản chi mà hoá đơn không có.

Hệ quả với người đọc: cộng mọi phòng ban lại **sẽ không ra tổng hoá đơn**, theo cả hai
chiều — thiếu phần không quy được, và thừa phần Ralli. Nếu màn hình không nói trước, người
xem sẽ đi tìm một lỗi không tồn tại, hoặc tin rằng công ty chỉ tiêu $16,43.

Vì vậy cột này trả lời một câu **hẹp hơn tên cột gợi ra**:

> *"Phần lưu lượng **có ghi được người dùng** của phòng ban này đáng giá bao nhiêu."*

Không phải *"phòng ban này tiêu bao nhiêu của công ty"*.

## 6. Nghiệm thu

Không tin vào việc "trang vẫn vẽ ra". Bốn mốc phải khớp **trước và sau**:

| Mốc | Cách lấy |
|---|---|
| Tổng token và tiền toàn kỳ | Thẻ Tổng quan, so với `/api/usage` |
| Số hàng đơn vị và số hàng tài khoản | Dòng chân bảng *"Đang hiện N hàng đơn vị và M hàng tài khoản"* |
| Tổng theo từng phòng ban cấp 1 | Cộng tay từ bảng, so với trước khi thay |
| Không hàng nào có tỷ lệ áp dụng > 100% | Quét toàn bảng |

Và **bắt buộc `Ctrl+Shift+R`** khi kiểm trong trình duyệt. Ngày 20/08 đã mất một vòng vì
Chrome giữ `app.js` cũ: file trên đĩa có hàm mới, trang đang chạy thì không, và bảng hiện
y hệt như trước khi sửa. Cách kiểm chắc chắn:

```js
fetch("js/app.js?probe=" + Date.now()).then(r => r.text())
  .then(s => console.log(s.includes("<tên hàm mới>"), typeof <tên hàm mới>));
```

Lệch nhau giữa hai vế nghĩa là đang xem bản cũ.
