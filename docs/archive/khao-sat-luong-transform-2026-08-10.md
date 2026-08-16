# Khảo sát luồng transform → nạp database

> **Ngày:** 10/08/2026 · chế độ explore, **chưa viết code**
> **Câu hỏi:** làm sao để chạy **một lệnh** là transform xong dữ liệu và đẩy vào database — và có nên dùng công cụ chuyên dụng (Spark…) không?
> **Cách làm:** áp dụng SKILL `tu-soat` vào chính việc *đánh giá*: đo dữ liệu thật trước, kết luận sau. Toàn bộ phép đo **chỉ đọc**; riêng phép đo thời gian nạp chạy trên **bản sao** DB trong scratchpad, `db/token_ledger.sqlite` không bị đụng tới.

---

## 0. Kết luận một dòng

**Không dùng Spark — lệch 3–4 bậc độ lớn.** Toàn bộ pipeline hiện chạy hết **14,56 giây** trên 337 MB dữ liệu thô, thuần thư viện chuẩn Python. Việc cần làm không phải đổi công cụ, mà là **chuyển từ nạp đè sang nạp chồng** — và để làm được điều đó phải bổ sung hai cột đang thiếu trong `fact_monitoring`.

---

## 1. Số đo nền

### 1.1 Quy mô dữ liệu

| Nhóm | File | Dung lượng |
|---|---:|---:|
| billing (CSV Console) | 8 | 716,5 KB |
| ctda / Ralli | 22 | 5,8 MB |
| tla-hd | 19 | 221,9 KB |
| monitoring (bản cào) | 14 | **334,4 MB** |
| độ trễ (histogram) | 8 | 11,9 MB |
| da_xu_ly | 8 | 100,6 MB |
| **Tổng trên đĩa** | | **453,6 MB** |

Chỉ tính **các file loader thực sự đọc**: **337,3 MB**, trong đó `2026-08-06-1m/*.csv` = 333,4 MB → **98,8%**. Mọi thứ còn lại cộng lại chưa tới 4 MB.

### 1.2 Database hiện tại — 122,6 MB · 538.592 dòng

| Bảng | Dòng | | Bảng | Dòng |
|---|---:|---|---|---:|
| `fact_monitoring` | 525.639 | | `dim_unit` | 136 |
| `fact_call` | 7.924 | | `dim_model_alias` | 43 |
| `fact_billing_daily` | 2.259 | | `dim_model` | 10 |
| `fact_usage_daily` | 1.602 | | `dim_agent` | 8 |
| `dim_user` | 955 | | `dim_function` | 8 |
| `ref_budget` | 7 | | `ref_fx` | 1 |
| `fact_perf_daily` | 0 | | `ref_price` | 0 |

### 1.3 Tốc độ thật

| Phép | Thời gian |
|---|---:|
| `json.loads` nhật ký Ralli (7.924 bản ghi) | 0,048 s |
| `csv.DictReader` toàn bộ monitoring (525.639 dòng) | 5,54 s |
| `GROUP BY` trên `fact_monitoring` | 1,23 s |

**Chạy đủ 5 loader** (trên bản sao DB, đúng thứ tự phụ thuộc):

| Bước | Bảng | Giây |
|---|---|---:|
| `nap_to_chuc` | `dim_unit` + `dim_user` + `dim_function` | 0,42 |
| `nap_ralli` | `fact_call` | 0,33 |
| `nap_billing` | `fact_billing_daily` | 0,25 |
| `nap_monitoring` | `fact_monitoring` ← khối nặng nhất | 13,21 |
| `dung_usage_daily` | `fact_usage_daily` | 0,35 |
| **Tổng** | | **14,56** |

Cả 5 bước chạy sạch, không bước nào hỏng.

### 1.4 Môi trường

Python 3.11.15 · SQLite 3.53.1. **Chưa cài:** `duckdb`, `pandas`, `polars`, `pyarrow`, `sqlalchemy`, `psycopg2/psycopg`, `pyspark`, `dbt`. Chỉ có `requests`.

→ Pipeline hiện chạy **thuần thư viện chuẩn** (`csv`, `json`, `sqlite3`). Đây là *tài sản*, không phải thiếu sót: không có gì để hỏng khi nâng cấp, không có gì ép kiểu sau lưng.

---

## 2. Phát hiện thật

### ① Bản cào bị cắt đúng tại ranh giới lưu trữ — đã hiện hình

```
22/01/2026 ─────────────────────────────── 06/08/2026
           đúng 196 ngày, không hơn một ngày
```

`MIN(thoi_diem_ict) = 2026-01-22`, `MAX = 2026-08-06`, cách nhau **đúng 196 ngày** — bằng đúng thời gian Cloud Monitoring lưu trữ. Không phải trùng hợp.

**Hệ quả:** mọi loader hiện mở đầu bằng `DELETE FROM …` rồi nạp lại từ bản cào mới nhất. Ghép với việc Google xoá dữ liệu quá 196 ngày:

```
Hôm nay:     DB = [01/01 ─────────────── 10/08]     ✔
Tháng 3/2027: nguồn chỉ còn [~15/09 ──── 27/03]
              DELETE + nạp lại → DB = [15/09 ──── 27/03]
                                       ^^^^^^^^^^^^^^ tháng 1–8/2026 BỐC HƠI
```

Đây là **rủi ro nghiêm trọng nhất**, và nó ẩn: hôm nay không thấy, sang năm mới thấy, lúc đó không cứu được.

### ② 78,7% dòng monitoring là rác `drive.googleapis.com`

| Dịch vụ | Dòng | % |
|---|---:|---:|
| `drive.googleapis.com` | 413.516 | 78,7% |
| `generativelanguage.googleapis.com` | 109.235 | 20,8% |
| `apphub` · `dataform` · `compute` | 2.535 | 0,5% |

| Project | Dòng | % |
|---|---:|---:|
| `pro-tuner-454203-v3` | 448.417 | 85,3% |
| `tranquil-post-471401-c1` | 60.207 | 11,5% |
| còn lại (5 project) | 17.015 | 3,2% |

Đây chính là mớ rác **quy tắc 3** loại ra ở tầng view. Dữ liệu *hữu ích* (`mon_sach`) chỉ **85.166 / 525.639 = 16,2%**.

### ③ `fact_monitoring` không có khoá chính, không ràng buộc duy nhất, không chỉ mục nào

525.639 dòng — bảng lớn nhất — hoàn toàn không có khoá:

| Bảng | Dòng | PRIMARY KEY |
|---|---:|---|
| `fact_billing_daily` | 2.259 | ✅ `(ngay, …)` |
| `fact_call` | 7.924 | ✅ |
| `fact_usage_daily` | 1.602 | ✅ `(ngay, …)` |
| `fact_perf_daily` | 0 | ✅ `(ngay, …)` |
| **`fact_monitoring`** | **525.639** | ❌ **KHÔNG CÓ** |

→ Hôm nay **không thể nạp chồng**. Chạy lại mà không xoá thì nhân đôi dữ liệu, âm thầm.

### ④ Bộ cột hiện tại làm nhoè 5.607 dòng — thiếu `res_location` và `protocol`

Thử tăng dần trên **file thô** (DB không còn cột để thử):

| Bộ cột | Tổ hợp riêng | Dòng trùng | Nhóm có `value` **khác nhau** |
|---|---:|---:|---:|
| Nền (đúng như DB đang có) | 520.032 | **5.607** | **2.964** |
| + `res_location` | 525.298 | 341 | 340 |
| + `metric_type` | 525.298 | 341 | 340 |
| + `method` | 525.298 | 341 | 340 |
| + `thinking_enabled` | 525.637 | 2 | 1 |
| + `output_modality` / `aligner` / `unit` | 525.637 | 2 | 1 |
| + `metric_labels_json` | **525.639** | **0** | **0** |

Truy ra nguyên nhân bằng cách đọc thẳng CSV gốc:

**`res_location` bị loader bỏ mất** — gánh 5.257/5.607 dòng nhoè. Cùng một phút, cùng một method, Google trả về **một chuỗi riêng cho mỗi vùng**: `africa-south1`, `asia-east1`, `asia-east2`, `asia-northeast1`, … Một ví dụ có tới **134 dòng** cùng phút chỉ khác vùng.

**`protocol`** nằm bên trong `metric_labels_json`, chưa tách ra. Hai dòng trùng cuối cùng:

```
ai-chatbot-contract · 2026-08-04 07:22 · GenerateContent · asia-east1
    protocol=grpc   value = 8.0
    protocol=https  value = 1.0     ← hai số đo THẬT, hiện không phân biệt được
```

**Khoá tối thiểu đo được:**

```
gcp_project_id · ts_utc · metric_alias · res_method
· res_credential_id · res_location · protocol
```

Thử bỏ từng cột ra khỏi bộ đầy đủ:

| Bỏ cột | Còn trùng | |
|---|---:|---|
| `ts_utc` | 523.922 | CẦN |
| `metric_alias` | 148.557 | CẦN |
| `res_location` | 5.257 | CẦN |
| `res_method` | 4.611 | CẦN |
| `gcp_project_id` | 1.059 | CẦN |
| `res_credential_id` | 285 | CẦN |
| `metric_labels_json` (→ `protocol`) | 2 | CẦN |
| `res_service` · `model` · `response_code` · `limit_name` · `thinking_enabled` | 0 | thừa *trên tập này* |

> ⚠️ **Số liệu hôm nay KHÔNG sai.** Vì đang `DELETE`+nạp lại toàn bộ nên các dòng đó vẫn nằm đủ trong bảng, `SUM` vẫn đúng. Vấn đề chỉ xuất hiện **khi chuyển sang upsert** — lúc đó sẽ mất số một cách âm thầm.

### ⑤ Cột nullable phá vỡ UNIQUE INDEX — cái bẫy đã ghi trong `01_schema.sql`

| Cột | NULL ở | % |
|---|---:|---:|
| `model_id` | 450.138 | 85,6% |
| `ma_tra_ve` | 372.615 | 70,9% |
| `credential_id` | 77.444 | 14,7% |
| `phuong_thuc` | 75.501 | 14,4% |

SQLite **và** PostgreSQL đều coi `NULL ≠ NULL`, nên `UNIQUE INDEX` trên cột nullable **không chặn được trùng**. Muốn upsert phải thay `NULL` bằng giá trị mờ trước — đúng lối `__chua_quy_duoc_*__` / `__ky_thuat_*__` mà `dim_unit` đang dùng.

### ⑥ `nap_to_chuc.py` xoá sạch `dim_user` mỗi lần chạy

```python
db/nap_to_chuc.py:141-145
cur.execute("DELETE FROM fact_usage_daily")
cur.execute("DELETE FROM fact_call")
cur.execute("DELETE FROM dim_function")
cur.execute("DELETE FROM dim_user")
cur.execute("DELETE FROM dim_unit")
```

Hôm nay an toàn vì nó phá cả `fact_call` trước nên khoá ngoại không kêu. Nhưng dưới mô hình nạp chồng, **một người rời danh bạ sẽ kéo theo toàn bộ lịch sử của họ**. Bảng chiều phải chuyển sang *chỉ thêm/sửa, không bao giờ xoá*.

### ⑦ Loader ghim cứng tên thư mục cào

```python
db/nap_monitoring.py:44
MON = ROOT / "data/raw_google_console/du_lieu_giam_sat/2026-08-06-1m"
                                                        ^^^^^^^^^^ ghim ngày
```

Cào mới → sinh thư mục mới → loader vẫn đọc thư mục cũ → **chạy thành công, số không đổi**. Kiểu hỏng tệ nhất vì không có dấu hiệu nào.

---

## 3. Trả lời: có nên dùng Spark không?

**Không. Lệch 3–4 bậc độ lớn.**

| | Dự án này | Ngưỡng Spark bắt đầu có lý |
|---|---|---|
| Dữ liệu thô đọc mỗi lần | **337 MB** | ~100 GB trở lên |
| Số dòng | **525.639** | hàng trăm triệu → tỷ |
| Toàn bộ 5 loader | **14,56 giây** | hàng giờ |
| Máy | 1 laptop | cụm nhiều máy |

**Câu chốt: JVM của Spark khởi động (10–30 giây) còn lâu hơn cả pipeline chạy xong (14,5 giây).**

### Dự báo phình — nếu nạp chồng, không xoá

Ngày đỉnh 12.096 dòng · trung vị 5.091 dòng · ~245 B/dòng:

| | 1 năm | 3 năm | 5 năm |
|---|---:|---:|---:|
| theo trung vị | 1,9 M dòng · 0,4 GB | 5,6 M · 1,3 GB | 9,3 M · 2,1 GB |
| theo đỉnh | 4,4 M dòng · 1,0 GB | 13,2 M · 3,0 GB | 22,1 M · **5,0 GB** |

Kịch bản xấu nhất sau 5 năm vẫn là **một máy**, vẫn không phải Spark. Và phần *hữu ích* chỉ 16,2% → khoảng 0,8 GB.

*(Dự báo này là **suy luận**, giả định tốc độ không đổi — không phải chứng minh.)*

### Các công cụ khác

| Công cụ | Đánh giá |
|---|---|
| **pandas** | ❌ **có hại ở đây.** Ép kiểu ngầm: thiếu số nguyên → `NaN` → float. **Quy tắc 5** ("thiếu thì NULL, không phải 0") gần như không giữ được. Đúng loại lỗi im lặng đã mất 3 ngày để truy |
| **Polars** | 🟡 nghiêm về kiểu hơn pandas, nhưng giải bài toán tốc độ mà ta **không có** |
| **DuckDB** | 🟡 thật sự hay — đọc thẳng CSV/JSON bằng SQL, cài một dòng, không server. Nhưng thêm **phương ngữ SQL thứ ba** vào kỷ luật SQLite↔Postgres đang giữ. Để dành, cân nhắc lại nếu dữ liệu thô ×10 |
| **dbt / SQLMesh** | 🟡 **đúng hạng mục** cho tầng transform — nhưng nhu cầu đó là **view MART của Ngày 3**, chưa phải bây giờ. Và dbt trên SQLite là công dân hạng hai |
| **Airflow / Dagster / Prefect** | ❌ điều phối 5 bước × 14 giây. Task Scheduler + một script là đủ |

### Mượn *ý tưởng*, đừng mượn framework

```
① watermark      bảng ghi lần nạp: nguồn nào, đến ngày nào, kết quả gì   (từ Airflow)
② incremental    upsert theo khoá tự nhiên, thay DELETE-tất-cả            (từ dbt)
③ test-as-code   đã có sẵn qua tu-soat — chỉ cần đổi từ "bằng đúng
                 525639" sang "không giảm, khớp chéo, trong biên"
```

---

## 4. Hình dạng luồng đề xuất

```
data/…/2026-08-06-1m/          ← vùng đáp, giữ nguyên, có ngày trong tên
        │
        │  ① CHỌN bản cào MỚI NHẤT tự động — không ghim tên trong code
        ▼
   ĐỌC + BIẾN ĐỔI              ← giữ nguyên 5 loader hiện có, chúng đúng rồi
        │
        │  ② UPSERT theo khoá tự nhiên (thay DELETE FROM)
        ▼
db/token_ledger.sqlite         ← tích luỹ, sống lâu hơn cửa sổ 196 ngày
        │
        │  ③ ghi vào bảng lan_nap: nguồn · thư mục · thêm/sửa bao nhiêu
        ▼
   view mon_sach + MART         ← Ngày 3
```

**Một lệnh:** `python db/lam_moi.py`, thêm được `--tu 2026-08-01`, `--chi monitoring`.

### Chiến lược nạp KHÔNG giống nhau giữa các bảng

| Bảng | Cách nạp | Khoá | Độ khó |
|---|---|---|---|
| `fact_call` | upsert | `call_id` (ObjectId Mongo) | 🟢 dễ nhất, khoá có sẵn |
| `fact_billing_daily` | upsert | đã có PK — Google **có sửa lại ngày cũ** nên upsert là bắt buộc | 🟢 |
| `dim_*` | **chỉ thêm/sửa, không xoá** | đã có PK | 🟡 phải bỏ `DELETE FROM dim_user` |
| `fact_monitoring` | upsert | **phải thêm `res_location` + `protocol` trước** | 🔴 việc thật |
| `fact_usage_daily` | dựng lại toàn bộ | bảng dẫn xuất — dựng lại mới đúng | 🟢 |

### Danh sách việc, theo thứ tự phụ thuộc

```
1  bỏ ghim "2026-08-06-1m" → chọn thư mục mới nhất, IN RA tên đã chọn
2  thêm cột res_location + protocol vào fact_monitoring, nạp lại (14 giây)
3  UNIQUE index trên khoá tự nhiên + INSERT…ON CONFLICT DO UPDATE
   ⚠ phải thay NULL bằng giá trị mờ trước — xem phát hiện ⑤
4  bảng lan_nap (watermark)
5  đổi nghiệm thu: giá trị ghim cứng → bất biến
6  lam_moi.py gói tất cả, báo độ cũ từng nguồn
```

Bước 1 · 4 · 6 nhẹ. **Bước 2–3 là phần thật.**

### Về bước 5 — nghiệm thu hiện đang ghim cứng ở cả 5 loader

```
nap_monitoring    != 525639 → dừng
nap_billing       != 2259 · != $270.9517 → dừng
nap_ralli         != 7924 · != 44.692.501 → dừng
nap_to_chuc       != 136 đơn vị → dừng
dung_usage_daily  != $270.951716 → dừng
```

Thiết kế này **đúng cho giai đoạn dựng** (chốt số để bắt hồi quy) và **sai hoàn toàn cho vận hành**: ngày mai dữ liệu nhiều hơn → cả 5 script cùng dừng. Phải đổi từ *kiểm tra giá trị* sang *kiểm tra bất biến*.

### Đầu ra mong muốn của `lam_moi.py`

```
$ python db/lam_moi.py

  ① monitoring     bản cào 2026-08-10-1m · +4 ngày · 531.204 dòng   MỚI
  ② billing        file mới nhất 04/08 · CŨ 6 NGÀY                  ⚠
  ③ ralli          nhật ký 07/08 · CŨ 3 NGÀY                        ⚠
  ④ tla-hd         units 08/08 · CŨ 2 NGÀY                          ⚠
  ⑤ usage_daily    dựng lại · 1.602 → 1.874 dòng                    OK
```

Dashboard im lặng vẽ số cũ **tệ hơn** dashboard nói thẳng "hoá đơn cũ 6 ngày".

---

## 5. Mức độ chắc chắn

| Khẳng định | Mức |
|---|---|
| Khoá tự nhiên nêu ở ④ là **đủ** | ✅ **chứng minh** — 0 trùng trên 525.639 dòng |
| `res_location` gánh 5.257/5.607 dòng nhoè | ✅ **chứng minh** — bỏ ra thì trùng tăng đúng bằng số đó |
| Bản cào bị cắt đúng 196 ngày | ✅ **chứng minh** — 22/01 → 06/08 |
| Toàn bộ pipeline 14,56 giây | ✅ **chứng minh** — đo trên bản sao thật |
| `res_service`·`model`·`response_code`·`limit_name` là "thừa" | ⚠️ **chỉ đúng trên tập này.** Về ngữ nghĩa chúng là danh tính chuỗi → **nên giữ trong khoá** cho an toàn với dữ liệu tương lai |
| Dự báo phình 1/3/5 năm | ⚠️ **suy luận** — giả định tốc độ không đổi |
| Đường PostgreSQL vẫn chạy sau khi đổi schema | ❌ **chưa kiểm** — Docker chưa xác nhận chạy |
| DuckDB có nhanh hơn đáng kể không | ❌ **chưa đo** — chưa cài, cài là thêm dependency |

---

## 6. Quyết định cần chốt

Bước 2–3 đổi schema → phải nạp lại toàn bộ. Rẻ (14 giây) nhưng là thay đổi thật.

**(a) Làm đủ 1→6.** Xong là có luồng nạp chồng thật sự, chống được bào mòn 196 ngày. Tốn hơn, và bước 3 là chỗ dễ sai nhất.

**(b) Làm 1 · 4 · 6 trước.** Có ngay `lam_moi.py` chạy được và biết tự khai nguồn nào cũ. Vẫn `DELETE`+nạp lại, tạm an toàn vì dữ liệu còn nằm trong cửa sổ 196 ngày. Để 2–3 sang buổi khác.

**Nghiêng về (a)**: mỗi ngày trôi mà `fact_monitoring` chưa có `res_location` là một ngày bản cào mới lại nhoè thêm — và bản cào cũ thì **không cào lại được**.

---

## 7. Cách tái lập các con số

Script đo nằm trong scratchpad của phiên (tạm thời, sẽ mất). Các phép chính:

```sql
-- ① ranh giới 196 ngày
SELECT MIN(substr(thoi_diem_ict,1,10)), MAX(substr(thoi_diem_ict,1,10)),
       COUNT(DISTINCT substr(thoi_diem_ict,1,10)), COUNT(*) FROM fact_monitoring;

-- ② tỷ lệ rác
SELECT dich_vu, COUNT(*) FROM fact_monitoring GROUP BY 1 ORDER BY 2 DESC;

-- ③ bảng nào có khoá
SELECT name, sql FROM sqlite_master WHERE type='table' AND name LIKE 'fact%';

-- ⑤ cột nullable
SELECT COUNT(*) FROM fact_monitoring WHERE model_id IS NULL;   -- lặp cho từng cột
```

```python
# ④ đếm trùng theo bộ cột, đọc thẳng CSV gốc
# lưu ý: dùng giá trị mờ cho ô trống, KHÔNG dùng \x00 (SQLite cắt chuỗi tại NUL)
MO = "\x01RONG"
c = Counter(tuple((r.get(x) or MO) for x in COT) for r in rows)
print(len(rows) - len(c), "dòng trùng")
```

**An toàn:** mọi truy vấn mở DB bằng `sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)`
(`as_posix()` bắt buộc — URI SQLite coi `\` của Windows là ký tự thoát).
Phép đo thời gian nạp chạy trên **bản sao**, không đụng DB thật.

---

## Liên quan

- `docs/plan-xay-dung-database-2026-08-07.md` — kế hoạch tổng thể
- `docs/quyet-dinh-ngay-2-2026-08-09.md` — 10 quyết định N1–N10
- `docs/tong-ket-phien-2026-08-09.md` — tổng kết phiên Ngày 2
- `docs/mui-gio-2026-08-08.md` — M1–M4, trong đó M4 giải thích vì sao monitoring mức phút là điều may
