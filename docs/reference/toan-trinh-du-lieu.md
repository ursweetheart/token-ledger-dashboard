# Toàn trình dữ liệu — từ Google về tới màn hình

> Đọc file này là đủ để tự chạy lại mọi thứ. Không cần đọc file nào khác trước.
>
> Cập nhật 14/08/2026.

---

## Bức tranh một trang

```
   ①  LẤY                ②  GỘP              ③  NẠP            ④  DỌN
   ──────────           ─────────           ────────          ────────

   Hoá đơn Google   ──►  merge_billing ──┐
   (tải TAY)                             │
                                         │
   Cloud Monitoring ──►  merge_monitor ─┤
   (API, ~12 phút)                       │
                                         ├──►  DATABASE  ──►  BACKEND  ──►  Dashboard
   Histogram độ trễ ──►  merge_latency ──┤     18 bảng        FastAPI       index.html
   (API)                                 │     3 view         chỉ đọc
                                         │
   App Ralli + TLA  ──►  (dùng thẳng)  ──┤
   (đăng nhập, API)                      │
                                         │
   Danh mục SKU     ──►  gen_catalog   ─┘
   (API, 1 lần)          → giá + tên chuẩn
```

**Bốn chặng, bốn thư mục.** Mỗi chặng đọc thư mục của chặng trước, không bao giờ
đọc ngược:

| Chặng | Đọc từ | Ghi vào |
|---|---|---|
| ① Lấy | Internet | `data/billing/`, `data/raw_web/`, `data/raw_google_console/` |
| ② Gộp | `data/` thô | `data/da_xu_ly/` |
| ③ Nạp | `data/da_xu_ly/` + `data/raw_web/` | PostgreSQL (volume `pgdata`) |
| ④ Dọn | database | JSON qua HTTP |

---

## Chạy lại tất cả — một lệnh

Nếu chỉ muốn làm cho nó chạy, đây là toàn bộ. **Không cần gọi tay script gộp
nào** — `update_dashboard.py` chạy đủ 9 bước, gồm cả chặng ② và chặng ③:

```bash
python scripts/update_dashboard.py                # ① + ② + ③  (~15 phút, có 1 bước tay)
python -m uvicorn backend.main:app --port 8000   # ④  (chạy nền)
cd web && python -m http.server 8080 --bind 127.0.0.1   # phục vụ dashboard
```

Rồi mở `index.html`. Xong.

Phần còn lại của tài liệu giải thích từng chặng — đọc khi có gì đó hỏng, hoặc
khi cần sửa.

---

# ① LẤY DỮ LIỆU

## Có năm nguồn, và chúng không giống nhau

| Nguồn | Cho ta cái gì | Lấy bằng gì | Trễ |
|---|---|---|---|
| **Hoá đơn** (Billing Console) | **Tiền** + token theo ngày/model | **Tải tay** | ~1 ngày |
| **Cloud Monitoring** | Token, lượt gọi, mã trả về | API | ~30 phút |
| **Histogram độ trễ** | p50/p95/p99 | API | ~30 phút |
| **App Ralli / TLA HĐ** | **Ai dùng** + danh bạ | API sau đăng nhập | tức thời |
| **Danh mục SKU** | Bảng giá chính chủ | API | đổi rất ít |

**Không nguồn nào đủ một mình.** Đó là lý do có database:

```
             tiền   token   lượt   ai dùng   độ trễ
  hoá đơn     ✓✓✓    ✓✓✓     —        —         —
  monitoring   —      ✓✓     ✓✓✓      —        ✓✓✓
  app          —      ✓       ✓       ✓✓✓       —
```

## Bước phải làm tay: tải hoá đơn

Google Cloud Console không cho tải báo cáo GMSSub qua API với quyền hiện có.

1. Vào **Billing → Reports**
2. Tải về **7 file** (mỗi project một file)
3. Bỏ vào `data/billing/`

`update_dashboard.py` kiểm ngày mới nhất trong các file đó ở **bước 0**. Cũ
hơn hôm qua thì **dừng ngay**, không chạy tiếp — vì nếu chạy tiếp, dashboard sẽ
có lượt gọi của hôm nay nhưng tiền của tuần trước. Sai mà trông như thật.

Cố ý dùng hoá đơn cũ thì thêm `--hoa-don-cu`.

## Các bước tự động

```bash
python scripts/pull_web_apps.py --chi-kiem-token   # kiểm đăng nhập trước
python scripts/pull_monitoring.py --days 196 --align 60
python scripts/pull_web_apps.py
python scripts/pull_hd_usage.py                 # chiều người dùng của TLA HĐ
python scripts/pull_latency_distribution.py
python scripts/pull_sku_catalog.py              # chỉ khi giá đổi
```

**Vì sao kiểm đăng nhập trước khi kéo Monitoring:** bước Monitoring mất hơn 10
phút. Phát hiện token hết hạn *sau* đó là vứt đi 10 phút không vì lý do gì.
Phép kiểm đăng nhập mất vài giây.

> ⚠️ **Cửa sổ lưu giữ của Google trượt rất nhanh.** Đợt 06/08 thấy 196 ngày,
> đợt 13/08 chỉ còn 112. Dữ liệu 22/01–22/04 **giờ chỉ còn trên đĩa của bạn**.
> Xoá thư mục kéo cũ là mất vĩnh viễn, không lấy lại được từ đâu.

---

# ② GỘP DỮ LIỆU

## Bạn KHÔNG cần chạy tay chặng này

`update_dashboard.py` đã gọi cả ba script gộp — bước 3, 6 và 7 trong mười bước
của nó. Chạy `update_dashboard.py` là xong chặng ① lẫn ②.

Chỉ chạy tay khi một script gộp hỏng và bạn muốn chạy lại riêng nó, hoặc khi
bạn vừa tải thêm hoá đơn mà không muốn kéo lại Monitoring (mất 10–15 phút):

```bash
python scripts/merge_billing.py                 # sau khi tải thêm hoá đơn
python scripts/merge_monitoring.py              # sau khi kéo thêm đợt Monitoring
python scripts/merge_latency_daily.py \
  --out data/raw_google_console/do_tre_phan_bo/latency-daily.csv
python scripts/rebuild_db.py                    # rồi nạp lại
```

Thứ tự giữa ba script gộp không quan trọng — chúng đọc ba thư mục khác nhau và
không script nào đọc đầu ra của script kia. Nhưng cả ba đều phải xong **trước**
`rebuild_db.py`.

## Vì sao phải có chặng này

Ba lý do, mỗi lý do một script:

**`merge_billing.py`** — hoá đơn về thành 7 file rời (mỗi project một file), mỗi
lần tải lại là một bộ mới. Script gộp thành một file, khử trùng lặp, ra
`data/da_xu_ly/billing/billing_<ngày>.csv`.

**`merge_monitoring.py`** — mỗi đợt kéo là một thư mục. Vì cửa sổ lưu giữ trượt,
**đợt mới KHÔNG chứa hết đợt cũ**. Phải chồng các đợt lên nhau mới ra chuỗi đầy
đủ. Ra `data/da_xu_ly/du_lieu_giam_sat/<ngày>-gop/`.

**`merge_latency_daily.py`** — đây là script đáng chú ý nhất.

### Vì sao độ trễ phải gộp bằng histogram

**Phân vị không cộng được.** Trung bình của p95=2,1s (trên 100 lượt) và p95=8,4s
(trên 2 lượt) ra **5,25s**, trong khi p95 thật khoảng **2,3s**.

Histogram thì cộng được: cộng số lượt ở **từng ô** qua 1.440 phút của một ngày,
rồi đọc mốc 95% trên histogram tổng. Kết quả là phân bố **thật** của cả ngày.

Script đã đo mức sai của cách trung bình: cột `lech_phan_tram` trong file kết
quả cho thấy có ngày lệch **19,3%**.

Ba cái bẫy script này đã xử:

1. **proto3 cắt bỏ các ô 0 ở cuối.** Độ dài `bucketCounts` thay đổi từ 17 đến 26
   trong khi đủ phải là 31 → cộng thẳng hai mảng khác độ dài sẽ **lệch cột**.
2. **Chỉ gộp được các điểm cùng `bucketOptions`.** Khác scale thì các ô không
   ứng nhau. Script dừng hẳn nếu gặp bộ thứ hai.
3. **Ngày tính theo giờ Việt Nam**, không theo UTC.

---

# ③ NẠP VÀO DATABASE

```bash
docker compose up -d                            # PHẢI lên trước
python scripts/rebuild_db.py                    # xoá sạch, tự chạy migrations rồi nạp data/
```

Đích mặc định lấy từ `connect.DEFAULT_DSN` — **một** chỗ duy nhất, dựng từ `PG*` khớp
`docker-compose.yml`, và `TOKEN_LEDGER_DSN` ghi đè được cho cả hệ thống. Trước 17/08/2026
`rebuild_db.py` có hằng số DSN riêng, mà `update_dashboard.py` gọi nó không truyền `--db`
— nên đổi `connect.py` xong đường ống vẫn dựng lại database cũ, không lỗi nào báo.

Đây là đường **dựng lại toàn bộ từ `data/`**: `rebuild_db.py` cố ý xoá schema, tự chạy
chuỗi migration đến `head`, nạp `02_catalog.sql`, rồi mới chạy bảy khâu dữ liệu. Nếu
database đang có dữ liệu cần giữ và chỉ cần nhận schema mới, không chạy rebuild; dùng
`alembic upgrade head` để nâng tại chỗ.

## Bảy bước, và thứ tự là bắt buộc

| # | Script | Dựng bảng | Vì sao ở vị trí này |
|---|---|---|---|
| 1 | `load_billing.py --rebuild` | migrations + danh mục + `fact_billing_daily` | `--rebuild` **xoá sạch**, nên phải đầu tiên |
| 2 | `load_org.py` | `dim_unit`, `dim_user`, `account`, `dim_function` | Xoá `fact_call`; đảo với bước 3 là mất cái vừa nạp |
| 3 | `load_ralli.py` | `fact_call` | Cần `account` của bước 2 |
| 4 | `load_hd.py` | `fact_app_daily` | Cần `account` và `dim_user` của bước 2 |
| 5 | `load_monitoring.py` | `fact_monitoring` | Độc lập |
| 6 | `build_usage_daily.py` | `fact_usage_daily` | **Bảng dẫn xuất** — đọc bước 1+3+4+5 |
| 7 | `build_performance.py` | `fact_perf_daily`, `fact_latency_daily` | **Bảng dẫn xuất** — đọc bước 5 + CSV |

**Vì sao Ralli và TLA HĐ đi hai bước riêng:** Ralli phơi log từng lượt gọi nên
vào `fact_call`; TLA HĐ chỉ phơi API đã tổng hợp sẵn nên vào `fact_app_daily` ở
mức (ngày × người × model). Hai đường cùng đổ về `fact_usage_daily` với
`source='app'`. Gộp chúng làm một bước sẽ phải giả vờ hai nguồn cùng độ mịn.

Hỏng bước nào thì **dừng ngay tại đó**, không bước nào chạy tiếp trên đầu ra dở
dang. Sửa xong chạy lại từ đúng bước đó:

```bash
python scripts/rebuild_db.py --from-step 5
```

## Mỗi bước tự nghiệm thu, và so với NGUỒN chứ không với số ghim

Đây là nguyên tắc quan trọng nhất của khâu nạp. Ví dụ `load_org.py` **không**
ghim "phải có 136 đơn vị". Nó đếm số dòng dựng từ file nguồn rồi so với số dòng
trong database.

Khác biệt: số ghim sẽ kêu sai mỗi khi tổ chức thay đổi (Ralli vừa bỏ 6 đơn vị:
108 → 102), và người ta sẽ quen tay sửa số ghim cho hết kêu. Còn phép kiểm suy
từ nguồn thì **chỉ kêu khi có dòng rơi rớt thật** — đúng cái nó sinh ra để bắt.

## Ba từ điển dịch tên

Ba nguồn gọi cùng một thứ bằng ba tên khác nhau. Ba bảng này là chỗ dịch:

| Bảng | Dịch cái gì | Ví dụ |
|---|---|---|
| `dim_model_alias` | tên model | SKU `0F51-429B-C2DC` → `gemini-2.5-pro` |
| `dim_metric_alias` | tên phép đo | `.../generate_content_.../usage` → "đo token, loại input" |
| `account` | tên người | ObjectId của Ralli + id của TLA HĐ → một `account_id` |

**Vì sao là bảng chứ không phải mã nguồn:** trước đây việc phân loại làm bằng
`LIKE '%token_count'` và regex trên tên SKU. Google đổi tên một cái là truy vấn
trả về 0 dòng, **không lỗi nào báo**. Nay một tên lạ làm khâu nạp **dừng hẳn** —
tức hỏng ở chỗ có người nhìn thấy.

## Soát lại sau khi nạp

```bash
python scripts/audit_db.py
```

30 phép kiểm chia 5 nhóm: **cấu trúc** (khoá ngoại, cây đơn vị), **số khớp**
(tiền và token qua mọi tầng), **phân loại** (mọi tên lạ đều có chỗ), **lỗ im
lặng** (bảng rỗng, độ phủ).

Kết quả có ba mức:

- `ok` — không phải làm gì
- `luu y` — dữ liệu thiếu mà ta **đã biết và chấp nhận**, không chặn việc
- `HONG` — cấu trúc sai, mã thoát khác 0

Ranh giới giữa `luu y` và `HONG`: **có sửa được bằng cách nạp lại không.**
"Google không ghi ai gọi" thì nạp lại bao nhiêu lần cũng thế → `luu y`. "Một
dòng trỏ vào `unit_id` không tồn tại" → `HONG`.

## Cập nhật schema tại chỗ

```bash
alembic upgrade head
```

Lệnh này chạy các revision còn thiếu trên database hiện có và **không xoá dữ liệu**.
Không chạy `rebuild_db.py` ngay sau đó: rebuild tự chạy migrations rồi cố ý xoá và nạp
lại toàn bộ. Luật thêm revision và hai đường vận hành nằm ở `db/migrations/README.md`.

---

# ④ TRIỂN KHAI BACKEND

## Cài và chạy

```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --port 8000
```

Mở **http://127.0.0.1:8000/docs** — tài liệu tự sinh, bấm thử được từng endpoint.

Trỏ backend vào database candidate hiện tại:

```bash
set TOKEN_LEDGER_DSN=postgresql://token:token_local@127.0.0.1:5432/token_ledger_v2
python -m uvicorn backend.main:app --port 8000
```

## Tám endpoint

| Đường | Trả về |
|---|---|
| `GET /api/health` | Dữ liệu có gì, mới đến đâu, **thiếu chỗ nào** |
| `GET /api/catalog` | Agent, model + giá, cây đơn vị, tỷ giá |
| `GET /api/usage?start=&end=` | Token + chi phí theo ngày/agent/model |
| `GET /api/accounts` | Danh bạ 932 nhân viên kèm đơn vị |
| `GET /api/usage-by-account?start=&end=` | Sử dụng quy về từng người |
| `GET /api/performance?start=&end=` | Mã trả về + độ trễ |
| `GET /api/thinking?start=&end=` | Token có bật chế độ thinking |

Không có endpoint ghi nào. Kết nối PostgreSQL mở session `readonly`, nên máy chủ
database thực thi chế độ **chỉ đọc thật sự**; đây không phải lời hứa trong tài liệu.

## Mọi con số đều kèm "số này từ đâu ra"

Đây không phải siêu dữ liệu cho vui:

```json
{ "ngay": "2026-08-13", "agent": "Trợ lý ảo Ralli",
  "total_tokens": 1723298,
  "chi_phi_usd": null,
  "nguon_token": "app",          ← lấy từ app, không phải hoá đơn
  "token_uoc_tinh": true }       ← hoá đơn chưa xác nhận con số này
```

Một con số token của hôm nay lấy từ Monitoring **trông y hệt** con số tuần trước
lấy từ hoá đơn. Không có hai cột này thì không phân biệt được.

## Nối với dashboard

```bash
cd web && python -m http.server 8080 --bind 127.0.0.1   # phục vụ dashboard
```

Hai vế của lệnh này giải hai vấn đề khác nhau, thiếu vế nào cũng hở:

- **`cd web`** chặn *cái gì* phục vụ được. Trước 24/08/2026, khi file SQLite còn tồn
  tại, chạy tại gốc repo từng phơi `.env`, đường `var/token_ledger.sqlite`, `data/` và
  `.git/` — đã đo, các đường dẫn trả 200. File và đường SQLite đó không còn tồn tại;
  bài học còn hiệu lực là chạy trong `web/` để không có đường đi ngược lên, kể cả
  `..%2f` hay `%2e%2e/`.
- **`--bind 127.0.0.1`** chặn *ai* truy cập được. Mặc định của `http.server` là
  *all interfaces*, tức cả mạng LAN công ty.

```bash
```

`api.js` (nạp trước `app.js`) tự gọi backend và thay dữ liệu vào. **Không chạy
backend thì nó im lặng rút lui** và dashboard chạy bằng dữ liệu nhúng như cũ —
bấm đúp `index.html` vẫn xem được.

Backend ở máy khác: `index.html?api=http://may-khac:8000`

### Chỗ dịch từ vựng

Database nói `agent_id`, `total_tokens`, `token_source`. `app.js` nói `a`, `ti`,
`to` — từ vựng cũ thời nhập Excel. Chỗ dịch nằm **gọn trong `api.js`**, để
`app.js` không phải sửa và database không phải bóp méo theo màn hình.

Ba trường không có nguồn nào cho và **để 0 chứ không bịa**: `ug` (nhóm người
dùng), `u` (số user được cấp), `c` (số cuộc chat). Trước đây dashboard suy chúng
ra bằng hệ số — số suy ra trông y hệt số đo.

## Kiểm backend

```bash
python backend/check_api.py                                   # 16 phép kiểm
python backend/check_api.py --compare http://127.0.0.1:8001   # 24, so hai PostgreSQL
```

**16 phép kiểm**: số khớp database, tham số rác bị từ chối bằng 400 (**không** âm
thầm trả bảng rỗng), và **thử ghi thật** qua chính kết nối của backend để chắc
là nó bị từ chối.

Thêm `--compare` thì thành **24**: 8 phép so nữa, đối chiếu **từng byte JSON** giữa
hai backend PostgreSQL trên cả 8 endpoint — ví dụ database đang chạy với candidate
`token_ledger_v2` vừa dựng. Cờ là `--compare`, không phải `--doi-chieu`.

---

# Phải biết trước khi tin vào số

Năm điều dưới đây không phải lỗi. Chúng là giới hạn của nguồn, và đã được đo.

### 1. Chỉ 12,6% token quy được về người thật

Google chỉ báo được mức project, **không ghi ai gọi**. Chỉ hai app tự ghi danh
tính: Ralli (tới từng lượt gọi) và TLA Hợp Đồng (tới mức ngày). Sáu agent còn
lại chạy bằng tài khoản dịch vụ và vĩnh viễn không có chiều người dùng.

Nên mọi báo cáo theo **người** chỉ phủ 107,4 triệu trên 851,9 triệu token.

> Con số này từng là **5,7%**. Ngày 14/08 nạp thêm chiều người dùng của TLA HĐ
> (62,4 triệu token) thì lên 12,6%. Phần còn lại không phải việc chưa làm — sáu
> agent kia không có gì để nạp.

`/api/usage-by-account` **tự kèm cảnh báo này** vào mỗi lần trả lời, để người
đọc không tưởng bảng đó đầy đủ.

### 1b. Tỷ lệ áp dụng là chỉ tiêu TÍCH LUỸ, không theo kỳ

`/api/adoption` **không nhận khoảng ngày**. "Đã từng dùng chưa" là câu hỏi tích
luỹ; ép vào thanh trượt thì cùng một agent nhảy từ 49% xuống 7% chỉ vì đổi kỳ,
mà con số nào cũng trông như một phép đo. Đã đo thật trên TLA HĐ: 22/44 tính cả
kỳ, 3/44 nếu chỉ tháng 8 — **lệch 7 lần**.

Mỗi dòng trả về kèm `from_day`/`to_day` để nói rõ tỷ lệ tính trên khoảng nào.
Tài khoản dùng chung (`admin`) và tài khoản thử (`test*`) bị loại khỏi **cả** tử
số lẫn mẫu số qua cột `account.is_shared` — chúng vẫn nằm đủ trong mọi con số
token và tiền, chỉ riêng chỉ tiêu này cần mỗi dòng là một người có thể chọn dùng
hay không. Số bị loại trả về ở cột `shared_excluded` để chuyện đó nhìn thấy được.

### 2. Mọi cột ngày là giờ Việt Nam

Google cắt ngày hoá đơn theo giờ Thái Bình Dương, nhưng ta **coi luôn là giờ
VN** (quyết định 14/08). Hệ quả đã chấp nhận: tổng cả kỳ vẫn đúng tuyệt đối,
nhưng **ngày cuối luôn hụt** và mỗi ngày lẫn ~15 giờ của ngày kề bên.

### 3. Ralli không có số của Google

Project `tla-ralli` **có** trên GCP nhưng **chưa nối Billing**, nên không có
dòng hoá đơn hay monitoring nào. Số của Ralli lấy từ nhật ký app.

Cột `has_google_source = FALSE` tồn tại để màn hình biết lúc nào phải hiện `–`
thay vì `0%`. Không có nó thì "không đo được" hiện ra y hệt "không có lỗi nào".

### 4. `cached` không cùng nghĩa ở ba nguồn

| Nguồn | `cached` là gì |
|---|---|
| hoá đơn | SKU **riêng**, nằm **ngoài** input. Cộng cả ba mới ra tổng |
| app | một phần **của** `prompt_tokens`. Cộng vào là đếm hai lần |
| monitoring | **không có** phép đo nào → luôn NULL |

Vì vậy `total_tokens` giữ theo **quy ước của nguồn**, và cột `token_source` cho
biết đang đọc quy ước nào.

### 5. Mười dòng có lượt mà không có token

Đều là model **embedding**. Cloud Monitoring có phép đo lượt cho embedding
(`quota/embed_content_.../usage`) nhưng **không có phép đo token nào** cho nó,
trong khi hoá đơn thì có. Ngày nào hoá đơn chưa kịp về, khoá đó chỉ còn lượt.

---

# Khi hỏng thì làm gì

| Triệu chứng | Nguyên nhân thường gặp | Cách xử |
|---|---|---|
| `Hoa don CU: ngay moi nhat ...` | Chưa tải lại 7 file GMSSub | Tải lại, hoặc `--hoa-don-cu` nếu cố ý |
| `Khong tim thay gcloud` | Trên Windows là `gcloud.cmd`, không phải `.exe` | Cài Google Cloud SDK |
| `NGHIEM THU KHONG DAT` ở bước nạp | Nguồn thiếu dòng, hoặc tên lạ chưa có trong bảng alias | Đọc thông báo — nó nói rõ lệch bao nhiêu ở đâu |
| Backend: `column ... does not exist` | Postgres còn là bản cũ | Chạy lại `tai_tao_postgres.py` |
| Dashboard không đổi số | Trình duyệt còn giữ `localStorage` cũ | F12 → Application → Local Storage → xoá |
| `[TokenLedgerAPI] khong nap duoc` | Backend chưa chạy | `uvicorn backend.main:app --port 8000` |
| `UnicodeEncodeError` khi in | Console Windows mặc định cp1252 | `set PYTHONIOENCODING=utf-8` |

---

# Đọc thêm

| File | Nội dung |
|---|---|
| `mo-ta-database.md` | Từng bảng, từng cột, và các bẫy khi truy vấn |
| `db/migrations/sql/001_baseline.sql` | Baseline schema bất biến — mỗi quyết định đều có ghi chú lý do |
| `../decisions/mui-gio-2026-08-08.md` | Các quyết định về múi giờ |
| `backend/store.py` | Mọi câu SQL của backend nằm gọn ở đây |
