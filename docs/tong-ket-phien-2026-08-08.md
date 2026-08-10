# Tổng kết phiên làm việc — chiều 08/08/2026

> **Đọc file này để nắm nhanh.** Mỗi mục đều trỏ tới tài liệu gốc có bằng chứng đầy đủ.
>
> Phiên bắt đầu từ câu hỏi *"nhiệm vụ ngày thứ 7 là gì"* và kết thúc với một database chạy được.

---

## 1. Tình hình lúc bắt đầu

Kế hoạch `plan-xay-dung-database-2026-08-07.md` chia 3 ngày: thứ Sáu dựng khung + hai nguồn Google, thứ Bảy nạp dữ liệu app, Chủ nhật dựng view và endpoint.

Thực tế thứ Sáu và sáng thứ Bảy đi làm **kiểm chứng dữ liệu**, không phải dựng database. Không phải đi lạc — chính nhờ đó mới biết `cached_tokens` phải là `NULL` chứ không phải `0`, biết không được dùng cột tiền của app, biết `user-usage-with-unit.csv` thổi phồng 16,4%. Dựng DB trước rồi mới biết thì phải nạp lại từ đầu.

Nhưng hệ quả: chiều 08/08 phải làm **cả Ngày 1**, chưa động tới Ngày 2.

---

## 2. Đã dựng được gì

```
   db/
   ├── quy_tac.py            quy tac dung chung - MOT ban duy nhat
   ├── ket_noi.py            mo ket noi, dung lai schema
   ├── 01_schema.sql         14 bang + 1 view, chay duoc ca Postgres lan SQLite
   ├── sinh_02_danh_muc.py   sinh danh muc TU DU LIEU THAT
   ├── 02_danh_muc.sql       8 agent · 10 model · 43 anh xa · 1 ty gia · 7 ngan sach
   ├── nap_billing.py        -> fact_billing_daily
   ├── nap_monitoring.py     -> fact_monitoring
   └── token_ledger.sqlite   database dang chay

   scripts/
   ├── pull_latency_distribution.py   cao histogram do tre (moi)
   └── gop_do_tre_theo_ngay.py        gop histogram -> p95 theo ngay ICT (moi)
```

### Nghiệm thu, tất cả đã chạy thật

| Phép kiểm | Kỳ vọng | Kết quả |
|---|---:|---|
| `fact_billing_daily` số dòng | 2.259 | ✅ |
| `fact_billing_daily` tổng tiền | $270,951716 | ✅ |
| Phân loại SKU input/output/cached | 1065 / 807 / 387 | ✅ |
| `fact_monitoring` số dòng | 525.639 | ✅ |
| `fact_monitoring` số dự án | 7 | ✅ |
| View `mon_sach` (đã lọc) | 85.166 | ✅ |
| p95 tự tính ↔ p95 của Google | 9.875 phút | ✅ sai số **0,0000%** |
| Lượt gọi ↔ `api_request_count` | 30.601 lượt | ✅ lệch **+0,01%** |

> **Về con số $270,9517.** Tổng thật là **$270,951716**; `270.9517` trong mọi tài liệu trước là bản đã làm tròn 4 chữ số. Không được dùng nó làm phép so bằng chính xác — phép nghiệm thu phải có dung sai (loader đang dùng `0,0001`, rộng hơn sai số làm tròn `1,6e-05`).
>
> Cộng bằng `float` của SQLite ra **đúng bằng** cộng bằng `Decimal`, chênh `0,000e+00`. Nhưng đó là may: SQLite lưu `NUMERIC(14,6)` dưới dạng `real` (dấu phẩy động), còn PostgreSQL lưu đúng kiểu thập phân. Khi số dòng lớn hơn thì hai bên có thể tách ra — thêm một lý do để chuyển sang Postgres.

Chi phí quy về 8 agent, cộng lại vẫn đúng $270,95:

```
   Sale Agent                     $125,34      Phân Loại Dữ Liệu CRM         $12,40
   Chatbot Contact Center         $ 93,76      Phân Loại Phản Hồi Tiếp Thị   $ 6,16
   Multi modal AI Invoice         $ 17,38      Tools Quizzer                 $ 0,04
   Trợ Lý Ảo Hợp Đồng             $ 15,87      Trợ lý ảo Ralli               $ 0,00 (không có nguồn)
```

### Ba thay đổi so với kế hoạch gốc

| | Thay đổi | Vì sao |
|---|---|---|
| 1 | Thêm bảng **`dim_model_alias`** | Ba nguồn gọi tên model theo ba kiểu. `gemini-embedding-001` (billing) và `gemini-embedding-1.0` (monitoring) không có quy tắc chuẩn hoá nào nối được — phải có bảng ánh xạ |
| 2 | Thêm bảng **`fact_perf_daily`** | Hai công tơ của Google không giao nhau: phép đo token có `model` nhưng không có mã lỗi; `api_request_count` có mã lỗi nhưng không có model. `fact_usage_daily` không có chỗ cho `ma_tra_ve` — hai endpoint hiệu năng sẽ không có nguồn |
| 3 | Thêm cột **`ref_budget.ngan_sach_token`** | Ralli bị chặn theo **token** (50 triệu/tháng), 6 agent kia theo **tiền**. Quy đổi sẽ khiến ngân sách trôi mỗi lần bảng giá đổi |

---

## 3. Tám phát hiện

### 🔴 3.1. Hoá đơn Google cắt ngày theo **giờ Mỹ**

Cột `date` là chuỗi trần không kèm múi giờ. Thử ba giả định trên cả 7 dự án:

```
   UTC       34 / 294 ngày khớp
   ICT       10 / 292 ngày khớp
   Pacific  284 / 316 ngày khớp   ← đây
```

Các ca lệch đều là **dịch nguyên khối một ngày**, cùng con số y hệt tới từng token. Một "ngày" trên hoá đơn bắt đầu lúc **14–15h giờ Việt Nam hôm trước**.

**Không phải lỗi khi tải** — giao diện xuất báo cáo không có tuỳ chọn múi giờ. → `mui-gio-2026-08-08.md` mục `M1`

### 🔴 3.2. Số độ trễ trên dashboard đang **lạc quan hơn thực tế ~26%**

`pull_monitoring.py` xin p95 bằng `ALIGN_PERCENTILE_95`, tức ép cả một histogram thành một số cho mỗi 60 giây. Phân vị của phân vị không cộng được.

Cào lại dạng `DISTRIBUTION` rồi gộp histogram cả ngày, so trên 289 (ngày, dự án) dùng **số p95 thật của Google** làm chuẩn cách cũ:

```
   thấp hơn thực tế   258 dòng      lệch trung vị  −25,9%      tệ nhất  −71,7%
   xấp xỉ              21 dòng      riêng ngày ≥100 lượt: −25,7%
   cao hơn thực tế     10 dòng
```

Có hệ thống, không phải nhiễu mẫu nhỏ: trung bình kéo số về giữa, còn p95 là câu hỏi về **đuôi**.

⚠️ **Nhưng đừng tin ba chữ số thập phân.** Histogram gộp lại thì chính xác, nhưng đọc phân vị vẫn phải nội suy trong ô, mà ô rộng gấp đôi sau mỗi bậc — **độ rộng ô trung vị bằng 57% của chính giá trị p95**. Dashboard phải hiện **khoảng**, không phải số lẻ.

### 🔴 3.3. Dữ liệu Monitoring đang rụng, **đo được**

So bản cào 06/08 với bản 08/08, cách nhau đúng 2 ngày:

```
   multimodal-invoice · tháng 5     159 → 128 mốc    −19,5%
   tranquil-post      · tháng 5   1.679 → 1.457      −13,2%
   multimodal-invoice · tháng 7     678 → 678          0%
```

Khoảng cách giữa các mốc **vẫn là 60 giây** ở cả hai bản → không phải hạ độ mịn, mà từng mốc biến mất hẳn.

**Hệ quả quan trọng nhất: bản cào 06/08 KHÔNG bị thay thế.** Với tháng 5 nó đầy đủ hơn bản hôm nay. Nếu sáng nay cào đè lên nó thì đã mất vĩnh viễn 13–19% dữ liệu tháng 5 mà không ai biết.

### 🟠 3.4. `timestamp` của Ralli là **UTC**

Lọc riêng 938 lượt gọi có người dùng thật, cộng 7 tiếng:

```
   giờ ICT    7h    8h    9h   10h   11h   12h   13h   14h   15h   16h   17h   18h
   lượt       60   290    35    49    41     8    36    92    62    63     9     2
                    ▲▲▲                       ▲                             ▲
               vào ca                    nghỉ trưa                      tan làm
```

Hình của một ngày công sở Việt Nam. Nếu đã là giờ Việt Nam thì cao điểm rơi vào **1 giờ sáng** — vô lý. → Trả lời xong câu hỏi treo số 10.

### 🟠 3.5. `system` của Ralli **phần lớn là người dùng thật**

| | lượt | trong giờ hành chính | cuối tuần | token |
|---|---:|---:|---:|---:|
| người thật | 938 | 79,6% | 23,8% | 3.843.356 |
| `system` | 6.986 | 69,4% | 38,3% | 40.849.145 |

`system` cao điểm **đúng 8h sáng**, trùng khít người dùng thật → phần lớn là lưu lượng người dùng mà ứng dụng không ghi được danh tính. Nhưng vượt mức cuối tuần và có cụm rõ lúc **2–3h sáng** (841 lượt) → có phần chạy theo lịch.

Đủ để **bác bỏ giả thiết "toàn bộ 88% là máy chạy nền"**. Câu hỏi thu hẹp thành: *"tác vụ nền nào chạy lúc 2–3h sáng?"*

### 🟠 3.6. Hai cái bẫy trong khâu nạp, đều **im lặng**

| | Bẫy | Nếu mắc |
|---|---|---|
| Quy tắc 8 | SKU `911A-8880-A243` tên là *"...**OUTPUT** token count gemini 2.5 flash short **INPUT** text"* | Kiểm `input` trước `output` → **346 dòng / $105,42 = 38,9% chi phí** nhảy sai cột, mà tổng vẫn đúng nên nghiệm thu tổng **vẫn xanh** |
| Quy tắc 9 | `dich_vu` không có sẵn: đúng các dòng token của generativelanguage lại có `res_service` **rỗng** | Gán `dich_vu = res_service` rồi lọc → trả về **0 dòng token**, không báo lỗi |

### 🟡 3.7. Hoá đơn **đúng là 100% Gemini API**

Dự án `pro-tuner` có lưu lượng tới 9 dịch vụ Google (Drive, Sheets, Compute, Storage…) và **2 dịch vụ** trong danh sách Billing. Nhưng bảng chi phí chỉ có **một dòng**: Gemini API $95,78. `Cloud Logging` tốn **$0**.

Chênh $2,02 giữa màn hình ($95,78) và file CSV ($93,76) = **4,4 ngày** file còn thiếu (file dừng 04/08). Không phải dịch vụ bị mất.

→ Giả định "chi phí project = chi phí agent" **đứng vững**.

### 🟡 3.8. `credential_id` — cùng một phút vẫn có nhiều chuỗi số liệu

Gọi bằng nhiều API key thì Google tách thành các chuỗi riêng. `tranquil-post` dùng **2 khoá** (13.699 / 8.776 lượt), `pro-tuner` dùng **3**.

Thiếu trường này thì chúng **trông như bản ghi trùng lặp** — và mọi phép đối chiếu sẽ lấy nhầm một chuỗi làm đại diện cho cả nhóm. Chính lỗ hổng này đã tạo ra "6 phút lệch >10%" trong lần kiểm đầu; thêm `credential_id` vào khoá thì cả 6 biến mất.

`apikey:UNKNOWN` chỉ **29/39.943 lượt (0,07%)** — bỏ qua. Không tra được bằng `gcloud`: chữ `UNKNOWN` nghĩa là chính Google không phân giải được khoá.

---

## 4. Quyết định đã chốt

| # | Quyết định |
|---|---|
| **M-A** | Nạp **đủ 525.639 dòng** Monitoring, lọc ở tầng view (`mon_sach`) |
| **M-B** | Hiển thị ngày theo **ICT** — chi phí theo ngày là kết quả quy đổi, phải ghi rõ |
| **M-C** | Cào lại độ trễ dạng **DISTRIBUTION** — ✅ **đã làm xong** |
| **M-D** | Bỏ theo đuổi `B1`/`D1`. Ralli dùng dữ liệu API trong `data/ctda/` làm nguồn duy nhất |
| **M-E** | **Mỗi tài khoản là một user.** Không phân biệt dùng chung hay cá nhân |
| **M-F** | Tỷ giá VNĐ **gõ cứng** 25.200, kéo API sau |
| **M-G** | Ngân sách Ralli = **50 triệu token/tháng** (đã dùng 89%) |
| **M-H** | Bảng giá model **giữ nguyên**, sếp duyệt |

**Hệ quả đáng chú ý của M-E:** vì mỗi tài khoản tính là một user, **53,6% token dồn vào 2 tài khoản `admin` + `Test1` trở thành phát hiện thật về mức độ tập trung sử dụng**, không còn là "dữ liệu chưa gán được". Báo cáo phải trình bày theo hướng đó.

---

## 5. Sửa lại ba kết luận cũ

| Ở đâu | Sai | Đúng |
|---|---|---|
| `X4` | Đổi tên thư mục thành `2026-08-06-196d` | `1m` nghĩa là **độ mịn 1 phút** (`pull_monitoring.py:291`), không phải khoảng thời gian. Tên đúng: `2026-08-06-196d-1m` |
| Nghiệm thu Ngày 1 | `COUNT(*) FROM fact_monitoring = 85166` | Mâu thuẫn với quy tắc 3. Đúng là **525639**; 85166 là số của view `mon_sach` |
| Câu hỏi treo 10 | "Chưa biết Ralli là UTC hay ICT" | **Là UTC** — xem 3.4 |

---

## 6. Còn lại

### Chặn tiến độ — chỉ còn 1 câu

**Chốt danh sách 8 agent chính thức** — có bỏ `tools-quizz` không? *(`app.js` đã loại nó khỏi danh sách ngân sách, nhưng chưa có quyết định chính thức)*

### Không chặn, hỏi khi tiện

1. Tác vụ nền nào của Ralli chạy lúc **2–3h sáng**? → tách người dùng thật khỏi máy
2. `apikey:UNKNOWN` là khoá của ai? → chỉ 0,07%, gần như không đáng

### Việc còn dở

```
   ĐÃ XONG   01_schema.sql · 02_danh_muc.sql · fact_billing_daily · fact_monitoring
             pull_latency_distribution.py · gop_do_tre_theo_ngay.py

   CHƯA LÀM  dim_unit · dim_user · dim_function        <- Ngày 2
             fact_call (7.924 dòng Ralli)              <- Ngày 2
             fact_usage_daily · fact_perf_daily        <- Ngày 2
             view lớp MART · FastAPI                   <- Ngày 3
```

Còn một việc chưa làm trong nhóm `X`: **tách file dẫn xuất sang `dan_xuat/`** (`X6`) và kiểm nốt `users-by-unit.csv` — file này là nguồn của `dim_user` cho TLA HĐ, mà nó nằm cùng nhóm với file đã sai 16,4%. Nên kiểm trước khi làm Ngày 2.

### Một việc chưa quyết

Database hiện đang chạy trên **SQLite** vì Docker Desktop chưa bật. `01_schema.sql` viết để chạy được cả hai (không dùng `SERIAL`, mọi khoá gán tường minh), nên chuyển sang PostgreSQL chỉ là đổi tham số `--db` — không sửa dòng SQL nào.
