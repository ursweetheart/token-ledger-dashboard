# Nhật ký sáng 20/08/2026

Đọc trong 2 phút: mục 1 và mục 5. Còn lại là chi tiết khi cần tra.

---

## 1. Tóm tắt một dòng

> Sáng nay chữa **ba con số sai** trên dashboard, và trong lúc chữa thì phát hiện
> **hai chuyện lớn hơn** mà trước đó không ai biết.

**11 commit** (09:48 → 11:28), tất cả phép kiểm xanh, **chưa push**.

---

## 2. Ba con số đã sai, giờ đã đúng

### ① Độ phủ người dùng: **12,4% → 98,5%**

Dashboard báo *"chỉ 12,4% token quy được về tài khoản thật"*. Nghe như 88% dữ liệu bị mù.

**Sự thật:** 6 agent một-người-dùng bị đếm nhầm vào phần "không biết ai dùng" — dù ta biết
chính xác. Lỗ hổng thật chỉ **1,5%**.

Nguyên nhân: cột `account.kind` dùng một nhãn `whole_agent` cho **hai chuyện trái ngược**:

```
  6 agent một-người-dùng   "đúng một tài khoản dịch vụ, biết là ai"   -> quy được
  TLA Hợp Đồng + Ralli     "không biết ai trong 45 / 892 người"       -> KHÔNG quy được
```

Đã tách thành nhãn riêng `service_account`.

### ② Tỷ lệ áp dụng `3/1 · 300%`

Hàng "Chưa quy được" báo *3 trên 1*. Không thể có 3 người trong nhóm 1 người.

Mẫu số đếm *"người được cấp quyền"* (có trong danh bạ), tử số đếm **tất cả** ai có
request — kể cả tài khoản `system`, `admin`, `guest` không có trong danh bạ. Giờ hai vế
đếm cùng một tập, và số người ngoài danh bạ được ghi trong tooltip thay vì cộng bừa.

### ③ Cột tiền `0 ₫` cho phòng ban rõ ràng có tiêu tiền

`Nghiên cứu thị trường`: **49 request · 525,9 nghìn token · 0 ₫**. Ba số không thể cùng đúng.

Tiền chỉ có trên hoá đơn Google, mà hoá đơn tính **theo project**, không ghi ai gọi. Code
tra không ra rồi **trả về 0** — biến *"không đo được"* thành *"bằng không"*.

Giờ tính được thật (xem mục 3), và phòng ban **không có lưu lượng** vẫn giữ `0 ₫` vì ở đó
số 0 là sự thật.

---

## 3. Hai phát hiện lớn hơn cả ba lỗi trên

### 🔴 Phần lớn tiền trên dashboard là **suy ra**, và trước hôm nay không ô nào nói

| Agent | Hoá đơn thật | Suy từ bảng giá | % suy ra |
|---|---:|---:|---:|
| Sale Agent | $16,06 | $0,29 | 2% |
| Chatbot Contact Center | $15,30 | $1,58 | 9% |
| Phân Loại Phản Hồi Tiếp Thị | $6,02 | $2,68 | 31% |
| **Trợ lý ảo Ralli** | **$0,00** | **$2,51** | **100%** |

Trợ lý ảo Ralli chưa nối Google Billing nên **không có hoá đơn nào** — toàn bộ số tiền của
nó là suy ra, mà màn hình im lặng.

Giờ mọi ô có phần suy ra đều mang dấu **`≈`**, và tooltip nói **bao nhiêu phần trăm**.
*"Có một phần suy ra"* và *"không đồng nào từ hoá đơn"* là hai chuyện khác nhau.

**Tin tốt:** phép suy này **không phải phỏng đoán**. Bảng giá lấy thẳng từ Cloud Billing
Catalog của Google. Đối chiếu 965 dòng có cả hai vế:

```
   suy ra   $291,6462
   hoá đơn  $291,9856      lệch tổng −0,1%   lệch trung vị mỗi dòng 0,0%
```

### 🔴 Cây phòng ban trong dashboard là một bản **chép tay**, và database có **hai cây**

Dashboard dùng danh sách 108 phòng ban **gõ cứng** trong `app.js`, trong khi database có
130. Đây là phần bị bỏ sót của đợt "chỉ đọc từ database" ngày 17/08.

Và database không có **một** cây mà **hai**:

```
   Trợ lý ảo Ralli       102 đơn vị, MỘT gốc "Toàn công ty"     <- 892/937 tài khoản
   Trợ Lý Ảo Hợp Đồng     20 đơn vị, BỐN gốc rời                <-  45/937 tài khoản
```

Hai app mô hình hoá cùng một công ty theo hai kiểu, **không có mã chung nào**. Bảng
`UNIT_ALIASES` gõ tay trong `app.js` chính là thứ đang gộp chúng lại.

---

## 4. Việc anh đã quyết sáng nay

**Xác nhận 4 cặp phòng ban trùng** — và đã đưa vào database (`canonical_unit_id`):

```
   TT C4LED  (Hợp Đồng)  ==  C4LED  (Ralli)
   Phòng BH1 (Hợp Đồng)  ==  PBH1   (Ralli)
   Phòng BH2 (Hợp Đồng)  ==  PBH2   (Ralli)
   Phòng BH3 (Hợp Đồng)  ==  PBH3   (Ralli)
```

Có lúc tưởng phải gộp thêm 8–13 cặp nữa, vì `Phòng BH1/2/3` mỗi cái có 4–5 **con**. Nhưng
đo ra thì **mọi đơn vị con ở cây Hợp Đồng đều 0 tài khoản / 0 token** — toàn bộ dữ liệu ở
cây Ralli, và dashboard tự cắt nhánh rỗng. Nên **4 cặp là đủ**.

**Chọn hướng 2 cho hai cấp gom** — thêm cột `is_report_aggregate` vào database, đánh dấu
`Toàn công ty` và `Tổng công ty Rạng Đông` để báo cáo bắt đầu từ bên dưới chúng. Trước đó
việc này là hai mã gõ cứng trong `app.js`.

---

## 5. Đang ở đâu, chiều làm gì tiếp

### Xong và đã commit

| Giờ | | |
|---|---|---|
| 09:48 | `3dc795b` | Tách `service_account` — độ phủ 12,4% → 98,5% |
| 09:49 | `db6c238` | Code in **tên agent** thay vì `[5, 8]` |
| 09:49 | `790e373` | **Hai tài liệu**: việc cần làm trước API Gateway · đồng bộ máy đồng nghiệp |
| 09:50 | `90571be` | Sửa tài liệu đồng bộ — nó tự mâu thuẫn ngay sau khi commit |
| 10:20 | `0e11c5a` | `0 ₫` → `—` · `3/1 · 300%` → `0/1` |
| 10:26 | `f8c9299` | Proposal OpenSpec gộp cả ba lỗi |
| 10:41 | `047e95b` | Đưa việc suy tiền vào phạm vi sau khi đo bác bỏ lý do loại nó |
| 10:50 | `a07a42f` | Sửa **6 khẳng định sai** trong chính proposal đó |
| 11:05 | `6d6eef8` | Tiền phòng ban suy từ bảng giá, có dấu `≈` và % suy ra |
| 11:16 | `feb0f03` | 4 cặp gộp vào database + công cụ đối chiếu cây |
| 11:28 | `cf1e9ab` | API phơi cây đã gộp + cột `is_report_aggregate` |

Hai tài liệu ở `790e373` đáng đọc riêng:

- **`viec-can-lam-truoc-api-gateway.md`** — việc cần xong trước khi bắt đầu API Gateway,
  chia theo Quyết định / Sửa code / Bịt lỗ hổng / Tái lập được. Phát hiện chính: Master
  Plan yêu cầu đối chiếu **bốn** nguồn và chạy song song 2 tuần, nên cột nguồn cần **hơn**
  sau Gateway chứ không phải bớt.
- **`dong-bo-may-dong-nghiep-20-08.md`** — 5 bước để đồng nghiệp pull code về chạy được.
  `origin/main` đang ở 16/08 nên họ thiếu **cả đợt chuyển sang PostgreSQL**.

```
audit_db 32 phép / 0 hỏng   ·   check_api 16/16
test JS 6 + 7               ·   kiem_so_artifact 24/24
```

### Còn lại — bước cuối, và nó **đã được dọn đường**

Bỏ 108 đơn vị gõ cứng trong `app.js`, đọc từ API.

**Lưới an toàn đã dựng và đã chạy** (`tools/doi_chieu_cay_don_vi.py`):

| Kiểu lệch | Số | Nghĩa |
|---|---|---|
| Có ở cả hai nhưng **khác cha** | **0** | ✅ Nhóm nguy hiểm nhất — số chảy sang nhánh khác mà không ai thấy — **rỗng** |
| Chỉ có trong database | 5 | Đều **0 tài khoản / 0 token**, vô hại |
| Chỉ có trong `ORG_UNITS` | 3 | Tên cũ thời Excel, không có dòng trong database |
| Khác nhau **một chữ `Đ`** | 1 | `TTDL&DHS` ↔ `TTDL&ĐHS` — cần anh chốt cách viết |

Và **gốc báo cáo suy từ database ra đúng 15 đơn vị**, trùng khít 15 hàng cấp 1 mà bản gõ
cứng đang cho.

Nói cách khác: đã chứng minh cây mới cho ra cùng kết quả **trước khi** thay. Việc còn lại
là đổi nguồn, không phải viết lại phép gộp.

### Ba việc nhỏ đang chờ anh

1. **Chốt cách viết `TTDL&DHS` hay `TTDL&ĐHS`** — một chữ, nhưng để lệch thì sau này lại
   phải nuôi thêm một alias.
2. **11 commit chưa push.**
3. **Ba tài liệu chưa theo dõi** — `tu-dien-database.md` đang bị một file đã commit trỏ
   tới ở 3 chỗ, nên đồng nghiệp pull về sẽ gặp tham chiếu gãy.

---

## 6. Bài học ghi lại, vì nó lặp lại 3 lần trong buổi sáng

> **Lập luận nghe hợp lý vẫn phải đo trước khi dùng nó để quyết.**

Ba lần trong một buổi:

| Tôi đã tin | Đo ra |
|---|---|
| *"App Ralli không phơi model nên không tính được tiền"* | **66/66 dòng đều có `model_id`.** Dữ liệu đủ từ đầu |
| *"Có `unit_id` thì bỏ được cả 33 alias"* | Chỉ bỏ được phần viết tắt. **Còn 4 cặp gộp hai cây thì `unit_id` không thay được** |
| *"Phải gộp thêm 8–13 cặp con"* | **Con ở cây Hợp Đồng rỗng hết.** 4 cặp là đủ |

Lần thứ nhất suýt loại một việc có giá trị ra khỏi phạm vi. Lần thứ hai suýt viết xong cả
`api.js` lẫn `app.js` rồi mới phát hiện cây không gộp được.

Và một bẫy kỹ thuật đã mất một vòng: **Chrome giữ `app.js` cũ trong bộ đệm**. File trên đĩa
có hàm mới, trang đang chạy thì không, và bảng hiện y hệt như chưa sửa. Cách kiểm chắc:

```js
fetch("js/app.js?probe=" + Date.now()).then(r => r.text())
  .then(s => console.log(s.includes("<tên hàm mới>"), typeof <tên hàm mới>));
```

Hai vế khác nhau nghĩa là đang xem bản cũ. Luôn `Ctrl+Shift+R`.
