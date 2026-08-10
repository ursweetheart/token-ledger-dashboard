# Quyết định cho Ngày 2 — 09/08/2026

> Mười quyết định chốt trong phiên 09/08, trong đó **hai cái lật ngược kế hoạch 07/08**.
> Mọi con số trong tài liệu này đã được tính lại bằng máy từ dữ liệu gốc
> (`scratchpad/kiem_so_lieu_plan.py`, 33/33 đạt). Chỗ nào là **suy luận** chứ không phải
> đo được thì có ghi rõ.
>
> Kế hoạch gốc `plan-xay-dung-database-2026-08-07.md` đã được sửa theo tài liệu này.

---

## Mười quyết định

| # | Quyết định | Vì sao |
|---|---|---|
| **N1** | `fact_usage_daily` **lưu cả hai nguồn** cho TLA HĐ, không chọn một | Xoá một nguồn là xoá luôn bộ đo phát hiện chênh lệch |
| **N2** | **Mỗi agent hiển thị một nguồn duy nhất**: 6 project → `billing`, TLA HĐ → `app`, Ralli → `app` | Hai tab lấy hai nguồn khác nhau thì lệch 12,9%, người xem mở cạnh nhau là thấy |
| **N3** | Ranh giới A2 đọc từ `dim_agent.ngay_bat_dau_co_du_lieu`, **không** gõ tay `WHERE` | Gõ tay thì lần nạp sau sẽ quên. Quên = tổng TLA HĐ cao gấp 4,4 lần |
| **N4** | 6 dòng kỹ thuật: `'Đơn vị sử dụng <agent>'` / `'Người dùng sử dụng <agent>'`, kèm cột `la_dong_ky_thuat` | `JOIN` gặp NULL sẽ loại 6 agent khỏi mọi bảng phòng ban, kể cả dòng tổng |
| **N5** | **Chưa cào lại TLA HĐ** | Dựng xong rồi nhìn mới biết thiếu gì. Cào trước khi biết cần gì thì dễ cào sai |
| **N6** | Ralli **nạp đủ 890 user + 108 đơn vị**, thêm dòng `'Chưa quy được'` | ⚠️ **Lật ngược kế hoạch 07/08.** Xem §Bằng chứng 1 |
| **N7** | `admin` của Ralli **để riêng hai dòng**, không gộp | Chép nguyên trạng nguồn, không diễn giải. Cột `nguon_gap` phân biệt danh bạ/nhật ký |
| **N8** | `tools-quizz` **giữ lại**, `dang_van_hanh = FALSE` | Không mất $0,04 và dữ liệu tháng 6 khỏi tổng. View lọc ra khi cần |
| **N9** | Khoá chính `fact_usage_daily` **mọi cột NOT NULL** | Xem §Bằng chứng 3 — SQLite nuốt trôi, PostgreSQL từ chối |
| **N10** | **Giữ tên** `fact_usage_daily` | Đổi một bảng trong khi bốn bảng anh em giữ nguyên thì rối hơn là rõ. Bù bằng khối chú thích ở §4.3 |

---

## Bằng chứng

### 1. Ralli cần dòng "Chưa quy được" gấp 132 lần TLA HĐ

Kế hoạch 07/08 viết: *"Ralli **không cần** dòng này: nó không đi qua GCP nên không có số
Google để mà lệch."*

Câu đó chỉ đúng nếu "chưa quy được" nghĩa là **lệch so với Google**. Nhưng phần lớn lượt gọi
của Ralli không gắn được với người nào **ngay trong chính nhật ký của nó**.

Đo trên `data/ctda/db-token_usage-raw.json` — 7.924 lời gọi, **30 `user_id` khác nhau**:

| Ai | Lượt | Token | Tỷ lệ |
|---|---:|---:|---:|
| `system` (nhãn `legacy`) | 6.986 | 40.849.145 | **91,4%** |
| `admin` (2 khoá) | 480 | 1.588.404 | 3,6% |
| `None` / `guest` | 194 | 986.156 | 2,2% |
| **→ "Chưa quy được"** | **7.660** | **43.423.705** | **97,2%** |
| Có đơn vị thật | 264 | 1.268.796 | 2,8% |
| **Tổng** | **7.924** | **44.692.501** | **100%** |

Số tự tổng hợp của chính app xác nhận độc lập: `by_unit` có
`"Không xác định" = 43.423.705 token / 7.660 lượt`.

**Hệ quả cho dashboard:** tab "người dùng theo phòng ban" của Ralli sẽ là **một cột chiếm 97%**
mang tên *"Tài khoản đã xoá hoặc chưa xác định"*. Đây không phải lỗi nạp — đó là tình trạng
thật, và bản thân con số 97% là chỉ tiêu chất lượng đáng báo cáo lên trên.

**"Người dùng thật" có hai định nghĩa, lệch nhau 49 lượt** — phải nói rõ dùng cái nào:

```
    có đơn vị thật                        264 lượt   (7.924 − 7.660)
    user_id nằm trong danh bạ 890 người   215 lượt
    ─────────────────────────────────────────────────
    chênh                                  49 lượt
```

Chốt: đếm theo **`unit_id`** (264), vì đó là con số cộng ra đúng tổng.
⚠️ *Suy luận, chưa chứng minh:* 49 lượt đó nhiều khả năng là người đã bị xoá khỏi danh bạ
nhưng nhật ký vẫn giữ đơn vị cũ.

### 2. TLA HĐ — cái giá của việc lấy app làm nguồn hiển thị

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

- **Trong khoảng đối chứng được:** app thấp hơn hoá đơn **12,9%** (`$13,81` vs `$15,87`)
- **Ngoài khoảng đó:** app khai **57.070.326 token / $55,44 không có hoá đơn nào**
  = **91,4%** toàn bộ token app khai của TLA HĐ, nhiều hơn cả lịch sử Ralli (44,7 triệu)
- **Quên chặn ranh giới A2** → tổng TLA HĐ **cao gấp 4,4 lần** ($69,25 vs $15,87)

Lưu ý: con số **17%** hay được trích là của **lượt gọi**, và nó **không phải hằng số** —
tháng 7 lệch −14,0%, tháng 8 lệch −19,3%. Không thể sửa số app bằng cách nhân 1,17.

⚠️ **Giả định chưa chứng minh, phải ghi kèm mọi biểu đồ chia theo người:** phần bị bỏ sót
được coi là **rải đều giữa các user**. Nếu chỉ một luồng gọi mất log và luồng đó của riêng
vài người thì tỷ lệ sẽ lệch hẳn. → Câu hỏi cho đội TLA HĐ.

### 3. Khoá chính có NULL — SQLite nuốt trôi, PostgreSQL từ chối

Nguồn `billing` không có `unit_id` lẫn `user_id`. Hai cột đó nằm trong khoá chính. Thử nạp
**hai dòng y hệt nhau** vào `fact_usage_daily` bản cũ:

```
    SQLite nhận 2 dòng giống hệt nhau vào KHÓA CHÍNH
```

SQLite cho phép NULL trong `PRIMARY KEY` và coi `NULL ≠ NULL`, nên khoá không chặn gì.
PostgreSQL thì `PRIMARY KEY ⇒ NOT NULL`, sẽ **từ chối dòng billing đầu tiên**.

Nghĩa là bảng này **hoặc vỡ ngay trên Postgres, hoặc âm thầm nhân đôi trên SQLite**.

**Cách chữa:** dùng dòng kỹ thuật (N4) và `'Chưa quy được'` (N6) thay cho NULL.

`model_id` thì **không cần** dòng kỹ thuật — đã kiểm, cả ba phép đo token đều có nhãn model:

```
    generate_content_paid_tier_3_input_token_count   12.534 dòng, thiếu model 0
    generate_content_usage_output_token_count        12.258 dòng, thiếu model 0
    generate_content_paid_tier_input_token_count         14 dòng, thiếu model 0
```

Phép đo thiếu model (`api_request_count`, `latencies`) thuộc về `fact_perf_daily`.

### 4. Google không biết ai là ai

Lý do N2 lấy app cho TLA HĐ và Ralli, dù app kém chính xác hơn: **billing và monitoring đều
dừng ở mức project**. Không có nhãn người dùng trong bất kỳ phép đo nào — thứ gần nhất là
`credential_id`, mà một API key thì cả app dùng chung.

Bỏ số app đi thì chiều "người dùng" không phải **kém chính xác** — nó **không tồn tại**.

---

## Thứ tự thực hiện Ngày 2

Thứ tự này **bắt buộc**, không đảo được:

```
   ⓪  Kiểm data/tla-hd/users-by-unit.csv          ← cùng nhóm với file đã sai 16,4%
   ─────────────────────────────────────────────────────────────────────
   ①  Sửa 01_schema.sql                          la_dong_ky_thuat ×2, nguon_gap,
                                                  fact_usage_daily NOT NULL
   ②  dim_unit    108 Ralli + 20 TLA HĐ + 6 kỹ thuật + 2 "Chưa quy được"
   ③  dim_user    890 + 42 + 6 kỹ thuật          nguon_gap = 'danh ba'
   ④  quét fact_call bổ sung user_id chỉ có trong nhật ký   nguon_gap = 'nhat ky'
   ⑤  dim_function
   ⑥  fact_call   7.924 dòng
   ⑦  fact_usage_daily  từ ba nguồn
```

Đảo ③④ với ⑥ thì `fact_call` có khoá ngoại trỏ vào chỗ trống.

**Cái bẫy khi đọc file:** `data/ctda/db-token_usage-raw.json` có **BOM UTF-8**. Mở bằng
`encoding='utf-8'` sẽ ném `JSONDecodeError: Unexpected UTF-8 BOM`. Phải dùng `utf-8-sig`.

## Nghiệm thu

```sql
SELECT COUNT(*), SUM(total_tokens) FROM fact_call;               -- 7924 | 44692501
SELECT COUNT(*) FROM fact_call WHERE cached_tokens IS NULL;      -- 6871  (KHÔNG phải 0)
SELECT dinh_dang_ban_ghi, COUNT(*) FROM fact_call GROUP BY 1;    -- 1:6871 · 2:542 · 3:511
SELECT COUNT(*) FROM dim_user WHERE la_dong_ky_thuat = FALSE;    -- 949
SELECT nguon_gap, COUNT(*) FROM dim_user GROUP BY 1;
--   danh ba 932 · nhat ky 17 · ky thuat 6   = 955
SELECT nguon, COUNT(*) FROM fact_usage_daily GROUP BY 1;         -- đủ 3 nguồn
-- Ralli: dòng "Chưa quy được" phải chiếm đúng 7.660 lượt
```

> **Sửa 09/08 sau khi chạy thật:** bản đầu ghi `932, KHÔNG phải 938`. Sai — nó quên
> chính 17 dòng sinh từ nhật ký mà mục §4.4b của kế hoạch mô tả. Đúng là **949**
> (932 danh bạ + 17 nhật ký), và 955 nếu tính cả 6 dòng kỹ thuật.

## Kết quả chạy thật (09/08)

```
   dim_unit         136     108 Ralli + 20 TLA HĐ + 6 kỹ thuật + 2 "Chưa quy được"
   dim_user         955     932 danh bạ + 17 nhật ký + 6 kỹ thuật
   dim_function       8     6 Ralli + 2 TLA HĐ
   fact_call      7.924     44.692.501 token · định dạng 1:6871 2:542 3:511
   fact_usage_daily 1.602   billing 898 · monitoring 475 · app 229
```

**`user_id` của Ralli là khoá trộn** — phát hiện khi nạp. Bản ghi cũ để **username**
trong trường `user_id`, bản ghi mới để **ObjectId**. 13/17 "người lạ" thật ra có trong
danh bạ, chỉ khác dạng khoá. Sau khi gán đơn vị theo tên (vẫn giữ riêng hai dòng theo
**N7**): `215 + 49 = 264`, và số lượt không quy được ra đúng **7.660** — **khớp tuyệt đối
với con số app tự tổng hợp độc lập**. Đây là phép kiểm chứng mạnh nhất của cả Ngày 2.

⚠️ **TLA HĐ không có dòng `nguon='app'` nào.** Chỉ Ralli có. Dữ liệu app mức
ngày × model × người của TLA HĐ **không tồn tại** — file ngày chỉ có 2 điểm, file năm
gộp theo tháng. Nghĩa là **quyết định N2 hiện chưa thực hiện được cho TLA HĐ**, và việc
cào lại (N5 hoãn) chuyển từ *"để sau"* thành **chặn**.

## Còn treo

| # | Câu hỏi | Hỏi ai |
|---|---|---|
| 1 | `system` của Ralli (6.986 lượt / 91,4% token) là tác vụ nền gì? | Đội Ralli |
| 2 | Đường gọi nào của TLA HĐ không đi qua chỗ ghi log? | Đội TLA HĐ |
| 3 | Phần bị bỏ sót có rải đều giữa các user không? | Đội TLA HĐ |
| 4 | Ralli có job chạy lúc 2–3h sáng ICT (841 lượt) — là gì? | Đội Ralli |
| 5 | 6 loại `function` của Ralli — cái nào người thật hỏi, cái nào máy nền? | Đội Ralli |

**Chưa thực chứng:** đường PostgreSQL. Docker Desktop chưa chạy, toàn bộ đang trên SQLite.
`01_schema.sql` viết để không phải sửa dòng SQL nào khi đổi (`--db "postgresql://..."`),
nhưng đó là **suy luận từ thiết kế, chưa phải bằng chứng**.
