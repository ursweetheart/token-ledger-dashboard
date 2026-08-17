# Đọc hiểu database (số liệu ngày 14/08/2026)

> Dành cho người mở pgAdmin lên và không biết mình đang nhìn gì.
> 18 bảng + 3 view, 577.819 dòng. **PostgreSQL là mặc định** từ 17/08/2026; SQLite vẫn
> dựng được để đối chiếu.
>
> Muốn biết dữ liệu **đến đây bằng đường nào**: `toan-trinh-du-lieu.md`.
>
> **Chỉ cần đọc một chỗ thì đọc view `usage_resolved`.** Nó đã gộp sẵn ba nguồn
> dữ liệu rời rạc lại thành một con số cho mỗi câu hỏi.

---

## Tên bảng có tiền tố — đây là ý nghĩa của chúng

```
dim_    THỰC THỂ MÔ TẢ    ai / cái gì. Ít dòng, ít đổi. Dùng để JOIN vào.
fact_   SỐ ĐO             chuyện đã xảy ra. Nhiều dòng. Cộng và nhóm được.
ref_    TRA CỨU           cấu hình: giá, tỷ giá, ngân sách.
```

Nhìn tiền tố là biết cách dùng: `dim_` không bao giờ cộng, `fact_` thì cộng thoải mái.

---

## Bản đồ

```
        ┌─────────────┐                     
        │  dim_agent  │ 8 agent — mỗi agent là một phần mềm AI
        └──────┬──────┘   trong đó 7 chạy trên Google Cloud, Ralli thì không
               │
      ┌────────┼──────────────┬────────────────┐
      ▼        ▼              ▼                ▼
 ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
 │dim_unit │ │dim_user  │ │dim_func  │ │ ref_budget   │
 │  130    │ │   957    │ │    8     │ │      7       │
 │phòng ban│ │tài khoản │ │chức năng │ │ ngân sách    │
 └─────────┘ └──────────┘ └──────────┘ └──────────────┘

        ┌─────────────┐        ┌──────────────────┐
        │  dim_model  │        │ dim_metric_alias │ 44 — dịch tên đo
        └──────┬──────┘        │ 13 phép đo + 31  │   của Google sang
               │               │ SKU hoá đơn      │   từ vựng của ta
               │  dim_model_alias (44)  └─────────┘
      ┌────────┼──────────┬──────────────┬──────────────────┐
      ▼        ▼          ▼              ▼                  ▼
┌──────────────┐ ┌───────────┐ ┌──────────────┐ ┌────────────────┐
│fact_billing  │ │ fact_call │ │fact_app_daily│ │fact_monitoring │
│   _daily     │ │           │ │              │ │                │
│   2.377      │ │   8.216   │ │      76      │ │    562.307     │
│ HOÁ ĐƠN thật │ │từng lượt  │ │ ngày×người   │ │ đo từng phút   │
│ có TIỀN      │ │gọi Ralli  │ │ ×model TLA HĐ│ │ có lỗi/độ trễ  │
└──────┬───────┘ └─────┬─────┘ └──────┬───────┘ └────────┬───────┘
       │               │              │                  │
       │               └── nguồn 'app'┘                  │
       └──────────────────────┼──────────────────────────┘
                              ▼
            ┌─────────────────────┐
            │  fact_usage_daily   │  1.715 dòng — bảng ĐỐI CHỨNG
            │  cột `source` giữ    │  để SO ba nguồn với nhau
            │  ba nguồn tách rời  │
            └──────────┬──────────┘
                       ▼
            ┌─────────────────────┐
            │ VIEW usage_resolved   │  1.128 dòng — CỬA CHÍNH
            │ đã CHỌN SẴN nguồn   │  hỏi số liệu thì đọc cái này
            │ 1 câu hỏi = 1 số    │
            └─────────────────────┘

        ┌──────────────┐        ┌──────────────────┐ ┌──────────────────┐
        │   account    │ 948    │ fact_perf_daily  │ │fact_latency_daily │
        │  932 thật    │  MỘT   │   578 dòng       │ │    297 dòng      │
        │  + 16 kỹ thuật│ mã số │ lượt theo mã     │ │ p50/p95/p99      │
        │  + ĐƠN VỊ    │ mỗi   │ trả về           │ │ gộp từ histogram │
        └──────────────┘ người └──────────────────┘ └──────────────────┘
                                 (ngày,agent,        (ngày,agent)
                                  phương thức,mã)     — độ mịn Google cho
```

---

## Muốn biết X thì đọc bảng nào

| Câu hỏi | Bảng | Ghi chú |
|---|---|---|
| **Số cho biểu đồ, theo ngày** | **view `usage_resolved`** | **đã chọn sẵn nguồn — bắt đầu từ đây** |
| Số theo tài khoản | view `usage_by_account` | chỉ Ralli và TLA HĐ mới biết ai dùng |
| Tỷ lệ tài khoản được cấp có dùng | `GET /api/adoption` | chỉ tiêu **tích luỹ**, không theo kỳ |
| Tốn bao nhiêu tiền? | `fact_billing_daily` | **số thật Google thu**, chi tiết tới từng SKU |
| Gọi bao nhiêu lượt? | `fact_monitoring` | qua view `monitoring_ai` |
| Ai dùng, dùng bao nhiêu? | `fact_call` + `fact_app_daily` | Ralli tới **từng lượt gọi**, TLA HĐ tới **mức ngày** |
| Lỗi và độ trễ? | `fact_monitoring` | cột `response_code`, phép đo `*_latencies_*` |
| Có bao nhiêu tài khoản? | `account` | 932 thật (+16 dòng kỹ thuật) |
| Cây phòng ban? | `dim_unit` | cột `path` cho sẵn đường dẫn đầy đủ |
| Ba nguồn có khớp nhau không? | `fact_usage_daily` | bảng **đối chứng**, nhớ lọc `source` |

---

## Từng bảng một

### `dim_agent` — 8 dòng
Danh sách phần mềm AI đang theo dõi.

| agent_id | name | gcp_project_id | đang chạy |
|---|---|---|---|
| 1 | Chatbot Contact Center | `pro-tuner-454203-v3` | ✓ |
| 2 | Sale Agent | `tranquil-post-471401-c1` | ✓ |
| 3 | Multi modal AI Invoice | `multimodal-invoice` | ✗ |
| 4 | Tools Quizzer | `tools-quizz` | ✗ |
| 5 | Trợ Lý Ảo Hợp Đồng | `ai-chatbot-contract` | ✓ |
| 6 | Phân Loại Phản Hồi Tiếp Thị | `feedback-dms-tiep-thi` | ✓ |
| 7 | Phân Loại Dữ Liệu CRM | `crm-500509` | ✓ |
| 8 | Trợ lý ảo Ralli | `tla-ralli` | ✓ |

**Ralli có project trên GCP nhưng `has_google_source = FALSE`.** Đây là hai chuyện khác nhau và có hai cột riêng:

- `gcp_project_id` — project có tồn tại trên GCP hay không. Ralli **có**: `tla-ralli`.
- `has_google_source` — có số liệu của Google để đối chiếu hay không. Ralli **không**, vì project chưa nối Google Billing.

Nên Ralli không có dòng hoá đơn lẫn monitoring nào; **mọi số của Ralli đến từ dữ liệu cào về từ chính app đó** (`fact_call`). View `usage_resolved` tự rơi về nguồn `app` cho agent này.

*(Trước đây `has_google_source` được **suy ra** bằng `gcp_project_id IS NOT NULL`. Gộp hai chuyện vào một phép suy chính là lý do cột này từng sai.)*

`has_org_tree` = agent này có phân cấp phòng ban hay không. Chỉ Ralli và TLA HĐ có.

### `dim_unit` — 130 dòng
Phòng ban. Tự trỏ vào chính nó qua `parent_id` để thành cây.

- `path` đã dựng sẵn đường dẫn đầy đủ (`Công ty > Vùng 1 > CN Biên Hòa`), khỏi phải đệ quy
- `is_technical = TRUE` là **dòng do pipeline tự tạo**, không phải phòng ban thật: 6 dòng "Đơn vị sử dụng ..." cho 6 agent không có cây tổ chức, và 2 dòng "Chưa quy được"

### `dim_user` — 957 dòng
**Đây là bảng cấp tài khoản, không phải danh sách nhân sự.** Khoá là `(agent_id, user_id)` — một người có tài khoản ở hai app sẽ có hai dòng.

`found_in` cho biết dòng đó từ đâu ra:

| giá trị | số dòng | nghĩa |
|---|---|---|
| `directory` | 934 | lấy từ API danh bạ của app |
| `log` | 17 | chỉ thấy trong log, không có trong danh bạ |
| `technical` | 6 | pipeline tự tạo cho 6 agent không có chiều người dùng |

Cột `account_id` trỏ về bảng `account`. Nhiều dòng `dim_user` có thể trỏ vào **cùng một** tài khoản — đó là chỗ 19 dòng trùng được gộp lại.

Muốn đếm tài khoản thì **đếm bảng `account`** (932 dòng `kind='real'`), đừng đếm bảng này.

### `dim_model` — 10 dòng
10 model Gemini, kèm `family` (`gemini-2.5`, `gemini-3`, `embedding`) và `provider`.

### `dim_model_alias` — 44 dòng
Mỗi nguồn gọi tên model một kiểu; bảng này quy về `model_id` chung.

```
billing_sku  31   mã SKU của Google, ví dụ 911A-8880-A243
monitoring    9   nhãn model trong Cloud Monitoring
app           4   tên model trong log của Ralli/TLA HĐ
```

Thiếu một dòng ở đây là script nạp **dừng hẳn** chứ không nạp với `model_id` rỗng.

### `dim_function` — 8 dòng
Chức năng trong app (`analyze` = Phân tích hợp đồng, `chat` = Hỏi đáp AI...).

### `fact_billing_daily` — 2.377 dòng · 01/01 → 12/08
**Hoá đơn Google. Đây là nguồn tiền duy nhất đáng tin.** Một dòng = một ngày × một project × một SKU.

- `kind` — `input` (1.111 dòng) · `output` (852) · `cached` (414)
- `cost_usd` giữ 6 chữ số thập phân, vì làm tròn tới xu ở mức từng dòng làm **773/2.377 dòng (32,5%) thành $0,00** dù chúng mang $0,89 và 9,3 triệu token
- `quantity` là số token
- `agent_id` là khoá chuẩn; `project` giữ lại chỉ để truy vết về GCP

### `fact_call` — 8.216 dòng · 14/03 → 13/08
Từng lượt gọi của **riêng Ralli**. Ralli phơi log thô nên gộp ra ngày nào cũng được.

Hai cột ghi "ai": `user_id` là khoá **gốc** của app (giữ để truy vết), `account_id` là khoá **chung** (dùng để tính toán). Nhật ký đôi khi ghi `user_id` là tên đăng nhập thay vì ObjectId — cả hai dạng đều trỏ về một `account_id`.

`dinh_dang_ban_ghi` cho biết bản ghi gốc có bao nhiêu trường — **quan trọng khi đọc `cached_tokens`**:

```
1  6.871 dòng   bản ghi 8 trường   KHÔNG CÓ cached_tokens  → cột này NULL
2    542 dòng   14 trường          có, giá trị 0 là SỐ 0 THẬT
3    803 dòng   16 trường          có, thêm actor_type/username
```

⚠ `cached_tokens IS NULL` nghĩa là **không biết**, không phải bằng 0. Lấy trung bình mà coi NULL là 0 thì sai 7,5 lần.

### `fact_app_daily` — 76 dòng · 14/03 → 12/08
Chiều người dùng của **TLA Hợp Đồng**. Cùng vai trò với `fact_call`, nhưng thô hơn một bậc: một dòng cho mỗi **(ngày, người, model)**, không phải mỗi lượt gọi.

Không phải chọn cho gọn — app Hợp Đồng **không phơi log thô**, chỉ phơi API đã tổng hợp sẵn. Mức mịn nhất lấy được đúng là ba chiều này.

```
2.834 lượt · 62.460.256 token · 28 người · 37 ngày có dữ liệu
gemini-2.5-flash  2.337 lượt      gemini-2.5-pro  493 lượt
```

- `raw_model` giữ tên gốc app trả về; `model_id` là tên đã dịch qua `dim_model_alias`
- `model_id IS NULL` ở 2 dòng (4 lượt): một dòng app trả tên `'none'`, một dòng của tài khoản đã bị xoá nên không lọc riêng được. **Hai dòng này không vào `fact_usage_daily`** vì `model_id` nằm trong khoá chính — `load_hd.py` in ra con số đó mỗi lần chạy chứ không nuốt lặng
- khoá chính là `row_id` gán tường minh, không phải bộ khoá tự nhiên: PostgreSQL cấm NULL trong khoá chính còn SQLite thì cho, đúng kiểu khác biệt chỉ lộ ra lúc đổi hệ

⚠ **Đừng cộng `fact_call` với `fact_app_daily` để lấy "tổng lượt gọi".** Chúng đo hai agent khác nhau ở hai độ mịn khác nhau. Muốn một con số thì đọc `fact_usage_daily` lọc `source='app'`, hoặc view `usage_resolved`.

### `fact_monitoring` — 562.307 dòng · 22/01 → 13/08
Số đo thô từ Cloud Monitoring, **từng phút**, giữ nguyên không lọc.

Phép đo nhiều nhất:
```
api_request_count              163.685    số lượt gọi
api_request_latencies_p95      158.956    độ trễ
api_request_latencies_p99      158.956
generate_content_*_requests     26.117
```

Mã trả về: `200` (163.167) · `302` · `503` · `400` · `404` · `499` · `500` · `403`

⚠ **Đừng `SUM(gia_tri)` trên bảng này.** Nó chứa cả dòng hạn mức quota với giá trị `int64 max` ≈ 9,2 × 10¹⁸. Dùng view **`monitoring_ai`** đã lọc sẵn.

Bốn cột **có trong file cào nhưng trước đây bị vứt lúc nạp**, nay đã lấy lại:

| cột | số dòng có giá trị | dùng để làm gì |
|---|---|---|
| `metric_type` | 562.307 | mã API chính thức của Google — nối vào `dim_metric_alias` |
| `thinking_enabled` | 13.130 | **dashboard có cột "think" mà DB trước đây không có nguồn** |
| `output_modality` | 13.130 | text / image / audio |
| `limit_name` | 67.574 | tên hạn mức quota |

Token output tách theo `thinking_enabled`: **43,2 triệu** token có bật thinking, **3,4 triệu** không.

Chuyện đáng nhớ ở đây: `metric_nickname` là biệt danh do chính script cào tự đặt, còn `metric_type` mới là mã Google cam kết ổn định. Bản trước giữ cái tự chế và vứt cái chính chủ.

### `fact_usage_daily` — 1.715 dòng · 01/01 → 13/08
Bảng **đối chứng**, sinh từ ba bảng trên. Dùng để so ba nguồn với nhau. Muốn một con số thì đọc view `usage_resolved`. **Xem cạm bẫy ① bên dưới.**

**Không có cột `unit_id`** — và đó là cố ý (sửa 14/08). Đơn vị là thuộc tính *của tài khoản*, lấy bằng `JOIN account`. Chép thêm một bản sao vào đây thì hai bản có thể lệch nhau; bỏ hẳn cột thì không còn chỗ để lệch.

Ba cột `input_tokens` / `output_tokens` / `cached_tokens` tách theo chiều — **nhưng `cached` không cùng nghĩa ở ba nguồn**, xem cạm bẫy ⑤.

### `fact_perf_daily` — 578 dòng · 22/01 → 13/08
Số lượt gọi theo **mã trả về**, khoá `(ngày, agent, phương thức, mã trả về)`.

| mã | lượt |
|---|---|
| 200 | 43.805 |
| 400 | 36 |
| 503 | 32 |
| 404 | 28 |
| 499 | 14 |
| 500 | 3 |

Tỷ lệ lỗi thật: **0,26%**. Dashboard trước đây suy 4xx/5xx/429 bằng hệ số nhân từ một con số error_rate — nay là số đo.

⚠ **Bẫy khi tự viết truy vấn trên `api/request_count`:** phép đo này đếm **mọi Google API** mà project gọi, không riêng gì AI. Trong 163.685 dòng thô: **147.969 là Google Drive** (90,4%), chỉ 14.179 là `generativelanguage`. Không lọc `dich_vu` thì 90% con số trên biểu đồ "hiệu năng agent" là lưu lượng Drive — và nó trông y như thật.

### `fact_latency_daily` — 297 dòng · 01/05 → 08/08
Độ trễ, khoá `(ngày, agent)` — **không có mã trả về, và không thể có**.

Tách khỏi `fact_perf_daily` ngày 14/08. Bảng cũ gộp cả hai vào khoá `(ngày, agent, phương thức, mã)` và **vì thế nằm rỗng từ đầu**: không có dữ liệu nào ở độ mịn ấy. Phân vị không cộng được, nên con số độ trễ *đúng* chỉ tồn tại ở mức cả ngày cả agent.

Hai cột `p95_o_tu` / `p95_o_den` là **bề rộng ô** chứa phân vị. Histogram gộp lại thì chính xác, nhưng đọc một phân vị ra vẫn phải nội suy trong ô, mà ô rộng gấp đôi sau mỗi bậc. **Dashboard nên hiện khoảng, không phải số lẻ.**

`du_mau = FALSE` (38/297 ngày) nghĩa là dưới 10 lượt — "p95" khi đó chỉ là lượt chậm nhất, đừng vẽ.

### `ref_price` — 10 dòng
Bảng giá model, USD trên 1 triệu token, **giá chính chủ từ Cloud Billing Catalog** (`nguon = 'google'`).

| model | input | output | cached |
|---|---|---|---|
| gemini-2.5-flash | 0,30 | 2,50 | 0,03 |
| gemini-2.5-pro | 1,25 | 10,00 | 0,125 |
| gemini-3-pro | 2,00 | 12,00 | 0,20 |

Đối chiếu ngày 14/08: **29/31 SKU có giá catalog trùng khớp giá suy ngược từ hoá đơn trong vòng 1%** (hai cái lệch đều là SKU $0,00, sai số làm tròn).

⚠ Catalog chỉ trả về **giá hiện hành**, không có lịch sử. Cột `effective_from` nói "giá từ ngày này", không nói được giá hồi tháng 1.

Kéo lại bằng `python scripts/pull_sku_catalog.py`.

### `dim_metric_alias` — 44 dòng
Dịch tên đo của Google sang từ vựng của ta: 13 phép đo monitoring + 31 SKU hoá đơn.

| do_gi | nghĩa | số bí danh |
|---|---|---|
| `token` | đếm token | 3 monitoring + 31 SKU |
| `luot` | đếm lượt gọi | 4 |
| `do_tre` | phân phối độ trễ | 1 |
| `han_muc` | hạn mức quota — **không được SUM** | 5 |

**Vì sao cần bảng này.** Trước đây phân loại bằng cách đoán tên ở hai chỗ khác nhau: regex trên `sku_name`, và `LIKE '%token_count'` trong truy vấn. Google đổi cách đặt tên là cả hai lặng lẽ trả về rỗng, không lỗi nào báo. Thành bảng tra cứu thì tên lạ làm **khâu nạp dừng hẳn**.

Nguồn phân loại:
- `han_muc` ⟺ `metricKind = GAUGE` — **metadata của Google quyết định**
- `do_tre` ⟺ `valueType = DISTRIBUTION` — metadata quyết định
- `token` vs `luot` — metadata **không** phân biệt (cả hai đều `DELTA/INT64`), phải đọc tên. Nhưng đọc từ `metric_type` (mã API chính thức) chứ không từ biệt danh do script tự đặt.
- `input`/`output`/`cached` cho SKU — catalog **không có** trường nào nói điều này (cả 597 SKU đều `resourceGroup=Gemini`, `usageType=OnDemand`), nên vẫn phải regex, nhưng chạy trên `description` chính chủ.

### `account` — 948 dòng
**Một mã số cho mỗi tài khoản.** Một dòng = một tài khoản, **không phải một con người**.

Trước đây mỗi nguồn ghi "ai dùng" theo kiểu riêng — Ralli ghi ObjectId của Ralli, TLA HĐ ghi id của TLA HĐ, Google thì không ghi ai cả. Ba quyển sổ, không mã chung. Bảng này là chỗ quy chúng về một mối; mọi bảng sự kiện đều trỏ về `account_id`.

| loai | số dòng | nghĩa |
|---|---|---|
| `that` | 932 | tài khoản người thật |
| `ca_agent` | 8 | Google chỉ báo được mức project → không quy được về ai |
| `chua_quy_duoc` | 8 | có lượt gọi nhưng bản ghi không kèm người dùng |

Khoá đối chiếu là **tên đăng nhập** đã `LOWER+TRIM`. Không dùng email (890 dòng Ralli không có email), không dùng họ tên (hai người trùng tên là gộp nhầm).

Gộp được 19 dòng trùng: 13 do Ralli ghi hai dạng khoá cho cùng một tài khoản, 5 do cùng tên đăng nhập tồn tại ở cả hai app, 1 do hai tài khoản dùng chung email.

Hai loại sau **không phải dữ liệu thiếu** — Google vốn không biết ai gọi.

#### Đơn vị nằm ở đây, không ở `dim_user` (sửa 14/08)

Trước đây `account` không có cột `unit_id`, nên câu "người này thuộc đơn vị nào" phải vòng qua `dim_user` — mà `dim_user` có **nhiều dòng cho cùng một tài khoản**, mỗi dòng một đơn vị. **5/932 tài khoản có hai đáp án:**

| tài khoản | TLA Hợp Đồng nói | Ralli nói |
|---|---|---|
| `longnt` | Phòng BH1 | PBH1 |
| `pbh3_tthien` | Phòng BH3 | PBH3 |
| `tt3.binhtv` | Phòng BH3 | PBH3 |
| `tg.namnh` | CN Tiền Giang | Đội chuyên trách - CN Tiền Giang |
| `quy.tv@rangdong.com.vn` | Công ty CPBĐ PN Rạng Đông | *Chưa quy được* |

Nguyên nhân: **cùng một tổ chức được mô hình hoá hai lần**, hai cây khác gốc khác độ sâu. Có 8 tên đơn vị trùng khớp giữa hai cây.

Quy tắc chọn, **tất định**:
1. Bỏ các dòng trỏ vào "Chưa quy được" — trừ khi không còn dòng nào khác
2. Còn lại thì lấy đơn vị **sâu nhất**. Sâu hơn = cụ thể hơn, và cuộn ngược lên luôn làm được qua `parent_id`; cuộn xuống thì không
3. Hoà thì lấy `agent_id` nhỏ nhất, rồi `unit_id` theo thứ tự chữ cái

Cột `don_vi_xung_dot = 1` **giữ lại dấu vết**: các nguồn đã không đồng ý và ta vừa chọn hộ. 4 tài khoản (không tính `quy.tv` — một nguồn im lặng thì là thiếu tin, không phải mâu thuẫn).

> ⚠️ **Đừng bao giờ JOIN bằng `LOWER(username)`.** Hàm `LOWER()` của SQLite **chỉ xử lý ASCII**: `'TMĐT_KTLoan'` qua `LOWER()` ra `'tmĐt_ktloan'`, không khớp `'tmđt_ktloan'` mà Python đã sinh ra. Mất đúng 3 dòng, không lỗi nào báo. Đã có `account_id` thì dùng nó.

### `ref_fx` — 1 dòng
Tỷ giá USD → VND.

### `ref_budget` — 7 dòng
Ngân sách theo `(agent_id, thang)`. Tools Quizzer và Ralli không có ngân sách.

---

## Ba view

### `usage_resolved` — 1.128 dòng ⭐ CỬA CHÍNH

**Đây là bảng để hỏi số liệu.** Mỗi dòng là một `(ngày, agent, model)` với **một** con số cho mỗi chỉ tiêu — không bắt người hỏi chọn nguồn.

Chọn nguồn theo **từng chỉ tiêu**, không theo từng dòng:

| chỉ tiêu | lấy từ | vì |
|---|---|---|
| tiền | `billing` | nguồn duy nhất có tiền |
| token | `billing`, thiếu thì `monitoring`, thiếu nữa thì `app` | hai nguồn đầu khớp 100,4% |
| lượt gọi | `monitoring`, thiếu thì `app` | billing không có |

Hai cột `token_source` / `call_source` nói rõ con số đến từ đâu, và `token_uoc_tinh = 1` nghĩa là **hoá đơn chưa xác nhận**. Không có hai cột này thì con số ước tính của hôm nay trông y hệt con số đã chốt của tuần trước.

```
nguon_token   ước tính   dòng          token
billing          0        942     695.983.837
monitoring       1         45      51.697.696
app              1        131      47.158.654
(không có)       1         10          — chỉ có lượt gọi
```

Ví dụ — câu hỏi từng không trả lời được:

```sql
SELECT SUM(total_tokens), SUM(chi_phi_usd), SUM(so_luot)
FROM usage_resolved WHERE ngay = '2026-08-13';
--  1.723.298 token | tiền NULL (hoá đơn chưa về) | 394 lượt
```

### `usage_by_account` — 240 dòng
Cùng số liệu nhưng nhìn theo tài khoản, kèm sẵn `username` / `full_name` / `email`.

Chỉ đọc nguồn `app` và **không** COALESCE gì cả — vì chỉ app mới biết ai dùng. 27 tài khoản có số liệu, tất cả thuộc Ralli.

### `monitoring_ai` — 91.191 dòng
`fact_monitoring` đã lọc: chỉ giữ dịch vụ `generativelanguage.googleapis.com` và bỏ dòng hạn mức.

**Luôn dùng view này thay vì bảng thô.** Lý do: trên `pro-tuner-454203-v3`, 97,4% lưu lượng là Google Drive chứ không phải Gemini — quên lọc là sai 45,7 lần.

---

## Năm cạm bẫy

### ① `fact_usage_daily` có ba nguồn nằm CẠNH nhau, không cộng vào nhau

```sql
SELECT nguon, COUNT(*), SUM(so_luot), SUM(total_tokens), SUM(chi_phi_usd)
FROM fact_usage_daily GROUP BY nguon;
```

```
nguon        dòng   lượt gọi     token      tiền
billing       942       —      696 triệu   $285,18
monitoring    516     99.012   439 triệu      —
app           257      8.216    47 triệu      —
```

Ba con số token **không cộng được** — chúng là ba cái công tơ khác nhau đo cùng một luồng. Cộng lại là đếm ba lần. Cột `source` sinh ra chính để giữ chúng tách biệt.

> **Bảng này là bảng ĐỐI CHỨNG, không phải bảng để hỏi số liệu.** Vì `source` nằm trong khoá chính,
> ai hỏi nó cũng phải tự chọn nguồn trước. Việc chọn thuộc về view `usage_resolved` chứ không thuộc
> về người hỏi. Dùng bảng thô này khi bạn muốn **so ba nguồn với nhau**.

> **Nhưng đừng vội kết luận billing và monitoring mâu thuẫn nhau.** Chênh lệch ở trên phần lớn
> là do **khoảng ngày khác nhau**: hoá đơn phủ 223 ngày, monitoring chỉ phủ ~112 ngày gần nhất.
> Cắt về cùng khoảng ngày (24/04–13/08) thì hai nguồn **khớp trong 0,4%** — đo ngày 13/08/2026,
> kiểm cả ở mức từng model. Luôn `WHERE ngay BETWEEN ...` trước khi so hai nguồn.

```
             tiền   lượt gọi   token   người dùng
billing       ✓        ✗        ✓         ✗
monitoring    ✗        ✓        ✓         ✗
app           ✗        ✓        ✓         ✓
```

**Không nguồn nào có đủ** — đó chính là việc view `usage_resolved` giải quyết.

### ② Mọi cột ngày đều coi là GIỜ VIỆT NAM

Quyết định ngày 14/08: **không quy đổi múi giờ nữa**, mọi cột ngày trong database là giờ Việt Nam.

Chỗ phải biết: Google cắt ngày hoá đơn theo **múi Thái Bình Dương** (đã chứng minh — 284/316 ngày khớp monitoring khi giả định Pacific, so với 34/294 nếu giả định UTC). Coi luôn là giờ VN nghĩa là chấp nhận:

- tổng cả kỳ **vẫn đúng tuyệt đối**
- ngày cuối cùng luôn hụt
- mỗi ngày lẫn khoảng 15 giờ của ngày kề bên

Đủ để theo xu hướng. **Không** đủ để đối chiếu một ngày lẻ giữa hai nguồn.

### ③ Ngày cuối cùng luôn chưa đủ

Hoá đơn mới có tới **12/08** còn Ralli/monitoring đã có **13/08**. Nên ngày cuối trên biểu đồ trông như có lưu lượng mà gần như không tốn tiền — đó là thiếu nguồn, không phải tiết kiệm.

Thêm nữa: **ngày cuối của mỗi bản export hoá đơn là số tạm**, Google viết lại sau. Đo thật: một SKU tăng **118 lần** khi tải lại 8 ngày sau.

### ④ Chiều người dùng mỏng hơn bạn tưởng

```
tài khoản thật trong bảng account     932
tài khoản thật sự có số liệu           27     ← 2,9%
```

Và cả 27 đều thuộc Ralli. Sáu agent kia Google không cấp nhãn người dùng nào, nên mọi chỉ tiêu theo người dùng hiện chỉ nói về Ralli.

*(Con số 27 thấp hơn 32 của bản trước vì các dòng trùng đã được gộp lại: `admin` từng là hai khoá riêng, nay là một tài khoản.)*

Trong `fact_usage_daily`, **86% số dòng có `account_id` là tài khoản kỹ thuật** — đó là phần của Google, không phải mất dữ liệu.

### ⑤ `cached` không cùng nghĩa ở ba nguồn

Đây là chỗ dễ so nhầm nhất. Ba nguồn dùng cùng một chữ cho ba thứ khác nhau — đã đo, không phải suy:

| nguồn | `cached` là gì | có nằm trong `total_tokens` không |
|---|---|---|
| **hoá đơn** | SKU **riêng**, nằm **ngoài** input | **có** — cộng cả ba mới ra tổng |
| **app** (Ralli) | một phần **của** `prompt_tokens` | **không** — tổng chỉ là prompt+completion |
| **monitoring** | **không có phép đo nào** | luôn `NULL` |

Kiểm chứng bằng chính số liệu:

```
hoá đơn     413.450.261 + 57.923.992 + 224.609.584 = 695.983.837  ✓ = tổng
app          42.813.945 +  4.344.547               =  47.158.492  ✓ ≈ tổng
             (cached 3.069.513 nằm TRONG 42.813.945, cộng vào là đếm hai lần)
monitoring  392.479.531 + 46.605.731               = 439.085.262  ✓ = tổng
```

Vì vậy `total_tokens` **giữ theo quy ước của nguồn**, và cột `token_source` cho biết đang đọc quy ước nào. Ép ba nguồn về một định nghĩa sẽ làm sai một trong hai đầu mà không đầu nào kêu.

Muốn "tổng token vào kể cả cache" từ hoá đơn:

```sql
SELECT SUM(so_luong) FROM fact_billing_daily WHERE loai IN ('input','cached');
```

*(Lệch nhỏ ở nguồn app: 162 token trên 47,1 triệu — 81 lượt gọi của Ralli có `total ≠ prompt+completion`, mỗi dòng lệch đúng 2. Là lỗi của app Ralli, khâu nạp giữ nguyên chứ không nuốt.)*

---

## Dựng lại database

```bash
docker compose up -d                                          # PHẢI lên trước
python scripts/rebuild_db.py                                  # PostgreSQL, ~56 giây
python scripts/rebuild_db.py --db var/token_ledger.sqlite      # SQLite,     ~14 giây
```

Cả 7 khâu nạp chạy được trên **cả hai** hệ mà không sửa dòng SQL nào — đã đo 17/08/2026:
dựng thẳng từ `data/` vào PostgreSQL cho ra database khớp từng dòng với bản sao từ SQLite,
và `audit_db.py` trên hai bên cho đầu ra giống nhau từng byte.

### Hai chênh lệch KIỂU giữa hai hệ quản trị

Cùng một cột trả về kiểu Python khác nhau. Đã đo, cả hai vô hại tới màn hình — nhưng ghi
lại vì loại lỗi này không ném exception, nó chỉ trả số sai:

| Cột | PostgreSQL | SQLite | JSON frontend nhận |
|---|---|---|---|
| `total/input/output/cached_tokens` | `Decimal` | `int` | **số, giống nhau** |
| `dim_unit.is_technical` | `True` | `1` | `true` vs `1` |

**`Decimal` là chỗ nguy hiểm nhất, và đã kiểm tận nơi:** `jsonable_encoder` của FastAPI đổi
`Decimal` có phần thập phân bằng 0 thành `int`, nên JSON ra số nguyên ở cả hai bên. Nếu nó
ra **chuỗi** thì `ti + to + cached` trong `web/js/app.js` sẽ thành **nối chuỗi** thay vì
phép cộng — số sai mà không lỗi nào báo.

**`is_technical`:** SQLite không có BOOLEAN thật, nó lưu 0/1 (`scripts/copy_to_postgres.py`
phải chuyển kiểu vì thế). Hiện không thành phần nào trong `web/` đọc cột này.
⚠ Nếu sau này có phần hiển thị đọc nó thì **đừng so bằng `=== true`** — dùng phép kiểm
đúng/sai thông thường, không thì nó chạy trên hệ này và vỡ trên hệ kia.

Nguồn là thư mục `data/` — thứ các script `pull_*` thu thập về. `data/` **không lên git**, nên bản clone thuần chỉ dựng được schema rỗng kèm danh mục.

## Soát lại sau khi dựng

```bash
python scripts/audit_db.py
```

30 phép kiểm: khoá ngoại, cây đơn vị, tiền/token khớp qua mọi tầng, mọi tên lạ đều có chỗ trong bảng alias, và các lỗ im lặng. Ba mức: `ok` / `luu y` (dữ liệu thiếu đã biết) / `HONG` (cấu trúc sai, mã thoát ≠ 0).

## Đọc thêm

| File | Nội dung |
|---|---|
| `toan-trinh-du-lieu.md` | **Lấy → gộp → nạp → backend.** Đọc cái này nếu muốn tự chạy lại |
| `db/01_schema.sql` | Schema — mỗi quyết định đều có ghi chú lý do |
| `backend/store.py` | Mọi câu SQL của backend |
