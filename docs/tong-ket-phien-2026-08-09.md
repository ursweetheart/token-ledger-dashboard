# Tổng kết phiên — chiều 09/08/2026

> Mục tiêu vào phiên: xác nhận Ngày 1 rồi làm Ngày 2.
> Kết quả: **Ngày 2 xong**, nhưng dọc đường phát hiện hai thứ **lật ngược kế hoạch**
> và một thứ **chặn** quyết định vừa chốt trong chính phiên này.
>
> Mọi con số dưới đây đã được máy tính lại từ dữ liệu gốc, không cộng nhẩm.

---

## 1. Đã làm gì

```
   ①  Xác nhận Ngày 1        đọc hẳn nội dung .sqlite, đối chiếu TỪNG DÒNG với CSV gốc
   ②  Khám phá Ngày 2        tìm ra 3 vấn đề trước khi viết dòng code nào
   ③  Chốt nguồn hiển thị    "mỗi agent một nguồn duy nhất" — ý của anh
   ④  Đo giá của lựa chọn    12,9% · và 91,4% nằm ngoài khoảng đối chứng
   ⑤  Chốt 3 câu hỏi treo    Ralli user · admin 2 khoá · tools-quizz
   ⑥  Soát kế hoạch BẰNG MÁY sửa 6 nhóm lệch giữa kế hoạch và code
   ⑦  Ghi bản quyết định     docs/quyet-dinh-ngay-2-2026-08-09.md
   ⑧  Kiểm users-by-unit.csv cửa chặn trước khi nạp — SẠCH
   ⑨  Dựng Ngày 2            3 bộ nạp mới, dựng lại từ số không chạy sạch
```

## 2. Sáu phát hiện

### ① Chiều "người dùng" của Ralli gần như rỗng — 97%

`fact_call` có 7.924 lời gọi nhưng chỉ **30 `user_id` khác nhau**:

| Ai | Lượt | Token | Tỷ lệ |
|---|---:|---:|---:|
| `system` (nhãn `legacy`) | 6.986 | 40.849.145 | **91,4%** |
| `admin` (2 khoá) | 480 | 1.588.404 | 3,6% |
| `None` / `guest` | 194 | 986.156 | 2,2% |
| **→ "Chưa quy được"** | **7.660** | **43.423.705** | **97,2%** |
| Có đơn vị thật | 264 | 1.268.796 | 2,8% |

**Lật ngược kế hoạch.** Bản 07/08 viết *"Ralli **không cần** dòng Chưa quy được"*. Thực tế
Ralli cần dòng đó **gấp 132 lần** TLA HĐ — 7.660 lượt so với 58. Lý do không phải lệch với
Google, mà là dữ liệu **không gắn được với người nào ngay trong chính nhật ký của nó**.

### ② `user_id` của Ralli là khoá trộn — và đây là phép kiểm mạnh nhất của cả ngày

Phát hiện khi nạp: **bản ghi cũ để `username` trong trường `user_id`, bản ghi mới để
ObjectId.** 13 trong 17 "người lạ" thật ra có trong danh bạ, chỉ khác dạng khoá.

Sau khi gán đơn vị theo tên (vẫn giữ riêng hai dòng theo quyết định **N7**):

```
    215 (khớp ObjectId)  +  49 (khớp username)  =  264
    không quy được:  7.924 − 264               =  7.660
                                                   ↑
                     khớp TUYỆT ĐỐI con số app tự tổng hợp độc lập
```

Hai đường tính hoàn toàn khác nhau ra đúng một số. Không phải trùng hợp được.

### ③ TLA HĐ không có dòng `nguon='app'` nào — chặn quyết định N2

Quyết định **N2** chốt đầu phiên: *TLA HĐ hiển thị theo nguồn app*. Nhưng khi dựng
`fact_usage_daily` mới lộ ra là **không dựng được**:

```
    token-usage-day.json     1 ngày (05/08), toàn số 0
    token-usage-week.json    bucket=day nhưng chỉ 1 điểm
    token-usage-month.json   bucket=day nhưng chỉ 2 điểm (02/08 và 04/08)
    token-usage-year.json    bucket=THÁNG, by_user gộp cả kỳ
```

Không có dữ liệu app mức **ngày × model × người** cho TLA HĐ. Việc cào lại — mà **N5**
hoãn với lý do *"dựng xong rồi nhìn mới biết thiếu gì"* — giờ đã biết: **chuyển từ *để sau*
thành *chặn***. Đúng như N5 dự tính, chỉ là câu trả lời không như mong đợi.

### ④ Khoá chính có NULL — SQLite nuốt trôi, PostgreSQL từ chối

Nguồn `billing` không có `unit_id` lẫn `user_id`, mà hai cột đó nằm trong khoá chính. Thử
nạp **hai dòng y hệt nhau**:

```
    SQLite nhận 2 dòng giống hệt nhau vào KHÓA CHÍNH
```

SQLite cho phép NULL trong `PRIMARY KEY` và coi `NULL ≠ NULL`. PostgreSQL thì
`PRIMARY KEY ⇒ NOT NULL`, sẽ từ chối dòng billing đầu tiên. Nghĩa là bảng này **hoặc vỡ
ngay trên Postgres, hoặc âm thầm nhân đôi trên SQLite**. Đã bịt, có kiểm chứng:

```
    NULL vào khoá chính  →  NOT NULL constraint failed: fact_usage_daily.unit_id
    Hai dòng y hệt nhau  →  UNIQUE constraint failed: ngay, agent_id, model_id, ...
```

### ⑤ Kế hoạch lệch code ở 6 nhóm — soát bằng mắt sẽ bỏ sót

Viết script trích `CREATE TABLE` từ cả hai bên rồi so tập cột:

| Lệch | Chi tiết |
|---|---|
| 2 bảng thiếu hẳn | `dim_model_alias`, `fact_perf_daily` |
| `dim_agent` | thiếu `ngay_ket_thuc_du_lieu`, `co_nguon_doi_chung` |
| `fact_monitoring` | thiếu `credential_id`, `la_han_muc`, `don_vi` |
| `fact_billing_daily` | thiếu `sku_ten` |
| `ref_budget` | thiếu `ngan_sach_token` |
| 2 chỗ `SERIAL` | không chạy được trên SQLite |

Sau khi sửa: **0 bảng thiếu, 0 cột lệch, 0 `SERIAL`.**

### ⑥ Chi phí thật của việc lấy app làm nguồn hiển thị TLA HĐ

```
   tháng      app $    Google $    chênh        app token
   ────────────────────────────────────────────────────────
   2026-03    14,23       0,00       —          4.639.924   ┐
   2026-04    16,40       0,00       —         21.863.066   │ KHÔNG CÓ
   2026-05     1,19       0,00       —          1.906.917   │ HOÁ ĐƠN NÀO
   2026-06    23,62       0,00       —         28.660.419   ┘
   ────────────────────────────────────────────────────────
   2026-07     5,75       6,42     −10,5%       1.943.922   ┐ đối chứng
   2026-08     8,07       9,45     −14,6%       3.436.267   ┘ được
```

- Trong khoảng đối chứng được: app thấp hơn hoá đơn **12,9%**
- Ngoài khoảng đó: **57.070.326 token / $55,44 không có hoá đơn nào** = **91,4%** toàn bộ
  token app khai — nhiều hơn cả lịch sử Ralli
- Quên chặn ranh giới A2 → tổng TLA HĐ **cao gấp 4,4 lần**

Và con số **17%** hay được trích là của **lượt gọi**, **không phải hằng số** — tháng 7 lệch
−14,0%, tháng 8 lệch −19,3%. Không thể sửa số app bằng cách nhân 1,17.

---

## 3. Mười bảy lỗi script đã sửa — và một cái sai trong tài liệu

Vòng `tu-soat` chạy ở **mọi** bước. Đáng chú ý:

| Lỗi | Nếu để nguyên |
|---|---|
| Phép đối chiếu billing dùng `int(float(amount))` — **y hệt loader** | Loader cắt cụt thì cả hai cùng sai, phép kiểm im lặng. Thêm phép kiểm thẳng trên CSV → 0 dòng có phần lẻ |
| `nap_app` liệt kê **9 cột**, 8 chỗ trống, `SELECT` trả **7 giá trị** | Hỏng ngay — bắt được bằng mắt trước khi chạy |
| Lấy `username` của bản ghi **đầu tiên** cho mỗi user | Bản ghi đầu thường là định dạng 1 (không có `username`) → ghi nhầm `user_id` làm tên người |
| `ten[hien]`, `x['ancestors']` không guard | **6/108** đơn vị Ralli thật sự thiếu `ancestors` |
| Regex tìm `SERIAL` bắt cả chữ trong câu tiếng Việt | Báo động giả mãi, rồi người ta bỏ qua cả báo động thật |
| `cong_don()` quét lại 42 dòng ở **mỗi nút cây** | Đúng mục "vòng lặp lồng ẩn" trong danh mục soát |
| `yield from () or duyet(...)` | Chạy đúng nhưng không ai đọc nổi |

**Sai trong tài liệu, không phải trong code** — nguy hiểm hơn vì không ai chạy lại được:

1. **Bảng tôi viết vào kế hoạch cộng ra 7.875, không phải 7.924** — thiếu 49. Nguyên nhân:
   *"người dùng thật"* có **hai định nghĩa** (264 có đơn vị / 215 trong danh bạ) và tôi trộn
   hai thước đo vào một bảng. Đã sửa, và chính chỗ này dẫn tới phát hiện ②.
2. **Số nghiệm thu `dim_user = 932` sai, đúng là 949** — nó quên chính 17 dòng nhật ký mà
   cùng tài liệu đó mô tả.
3. **Chú thích `39,6%` trong schema là con số của `mon_sach`, không phải bảng thô** (85,6%).

---

## 4. Trạng thái sau phiên

```
   dim_agent          8      dim_unit         136      dim_user        955
   dim_model         10      dim_model_alias   43      dim_function      8
   fact_call      7.924      fact_billing   2.259      fact_monitoring 525.639
   fact_usage_daily 1.602    (billing 898 · monitoring 475 · app 229)
   ref_budget         7      ref_fx             1      ref_price         0
```

Dựng lại **từ số không** chạy hết 5 bước: `integrity_check ok`, **0** vi phạm khoá ngoại,
8/8 phép đối chiếu chéo đạt. Tiền cộng qua mọi đường đều ra `$270,951716`.

**File mới:** `db/nap_to_chuc.py`, `db/nap_ralli.py`, `db/dung_usage_daily.py`,
`docs/quyet-dinh-ngay-2-2026-08-09.md`, tài liệu này.
**File sửa:** `db/01_schema.sql`, `docs/plan-xay-dung-database-2026-08-07.md`.

---

## 5. Còn lại

### Chặn

| # | Việc | Vì sao chặn |
|---|---|---|
| 1 | **Cào lại TLA HĐ theo ngày** | Không có thì quyết định N2 không thực hiện được (phát hiện ③) |
| 2 | **Quy ngày Pacific → ICT cho nguồn billing** | `ngay` của `nguon='billing'` hiện là **giờ Mỹ**. Tổng cả kỳ đúng tuyệt đối, nhưng **chuỗi theo ngày lệch tới 15 giờ**. Quy đổi cần rải lại theo hình dạng phút của monitoring — là **ước lượng** |

### Chưa chắc chắn

- **Đường PostgreSQL chưa thực chứng.** Docker chưa chạy, toàn bộ trên SQLite. Schema viết
  để đổi chỉ bằng `--db`, nhưng đó là **suy luận từ thiết kế, chưa phải bằng chứng**.
- **49 lượt chênh** giữa hai định nghĩa "người dùng thật": *suy luận* là người đã bị xoá
  khỏi danh bạ nhưng nhật ký giữ đơn vị cũ. Chưa chứng minh.
- **Giả định phần bỏ sót của TLA HĐ rải đều giữa các user.** Chưa ai chứng minh. Nếu chỉ
  một luồng gọi mất log và luồng đó của riêng vài người thì mọi tỷ lệ chia theo người sẽ lệch.

### Câu hỏi cho các đội

| # | Câu hỏi | Hỏi ai |
|---|---|---|
| 1 | `system` (6.986 lượt / 91,4% token) là tác vụ nền gì? | Ralli |
| 2 | Đường gọi nào không đi qua chỗ ghi log? | TLA HĐ |
| 3 | Phần bị bỏ sót có rải đều giữa các user không? | TLA HĐ |
| 4 | Job chạy lúc 2–3h sáng ICT (841 lượt) là gì? | Ralli |
| 5 | 6 loại `function` — cái nào người thật hỏi, cái nào máy nền? | Ralli |

### Ngày 3

View lớp MART · chuyển `test/kiem_tra_du_lieu.py` sang chạy trên DB · FastAPI 5 endpoint ·
`db/README.md`.
