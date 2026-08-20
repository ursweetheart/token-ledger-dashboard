# Từ điển database `token_ledger`

> **File này có HAI PHẦN. Đừng lẫn chúng với nhau.**
>
> | | Nội dung | Trạng thái |
> |---|---|---|
> | **PHẦN I** | 18 bảng + 3 view đang chạy — 599.686 dòng | ✅ **CÓ THẬT.** Mở pgAdmin ra là thấy |
> | **PHẦN II** | Schema đề xuất cho kiến trúc API Gateway | 🟡 **CHƯA TỒN TẠI.** Bản vẽ để bàn |
>
> Không bảng nào trong Phần II tồn tại trong database. Viết truy vấn thì đọc Phần I.

---

# ✅ PHẦN I — SCHEMA HIỆN TẠI

> Tra cứu từng bảng, từng cột. Số liệu đọc trực tiếp từ PostgreSQL **ngày 19/08/2026**.
> Kết nối: `postgresql://token:***@127.0.0.1:5432/token_ledger` (PostgreSQL 17, docker-compose).
>
> **18 bảng + 3 view — 599.686 dòng.**
>
> Muốn hiểu *vì sao* database có hình dạng này thì đọc `mo-ta-database.md`.
> Muốn biết dữ liệu *đến đây bằng đường nào* thì đọc `toan-trinh-du-lieu.md`.
> Bản khai báo gốc kèm ghi chú thiết kế nằm ở `db/01_schema.sql`.

---

## Tiền tố tên bảng

| Tiền tố | Nghĩa | Dùng thế nào | Các bảng |
|---|---|---|---|
| `dim_` | **dimension** — thực thể mô tả: *ai / cái gì* | Ít dòng, ít đổi. Chỉ để JOIN vào. **Không bao giờ cộng.** | `dim_agent` `dim_unit` `dim_user` `dim_model` `dim_model_alias` `dim_function` `dim_metric_alias` |
| `fact_` | **fact** — số đo: *chuyện đã xảy ra* | Nhiều dòng. Cộng và nhóm thoải mái. | `fact_call` `fact_app_daily` `fact_billing_daily` `fact_monitoring` `fact_usage_daily` `fact_perf_daily` `fact_latency_daily` |
| `ref_` | **reference** — quy ước do *người* quyết định | Bảng giá, tỷ giá, ngân sách. Không đo được, phải khai. | `ref_price` `ref_fx` `ref_budget` |
| *(không tiền tố)* | `account` — bảng danh tính hợp nhất | Nằm giữa `dim_` và trục chính. Là khoá CHUNG cho cả ba nguồn. | `account` |

**Hai quy ước xuyên suốt:**

1. **Mọi cột ngày/giờ đều là GIỜ VIỆT NAM** (chốt 14/08/2026), trừ hai cột ghi rõ `_utc`/`_raw`. Không quy đổi múi giờ ở bất kỳ đâu.
2. **Tên bảng/cột là tiếng Anh, ghi chú là tiếng Việt.** Đây là quy ước đặt tên của dự án.

---

# 1. Bảng danh mục (`dim_`) và danh tính

## `dim_agent` — Danh mục **agent**, tức từng phần mềm AI của công ty

8 dòng · Khoá chính `agent_id` · `code` là UNIQUE

Đây là bảng gốc của cả database: mọi `fact_` đều trỏ về đây bằng `agent_id`.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `agent_id` | `integer` | mã số agent | Số 1–8, gán tay chứ không tự sinh | `1`, `5`, `8` |
| 2 | `code` | `text` | mã chữ, không dấu | Tên ngắn dùng trong URL và mã nguồn | `contact-center`, `tla-hd`, `ralli` |
| 3 | `name` | `text` | tên hiển thị | Tên tiếng Việt đưa ra màn hình | `Trợ Lý Ảo Hợp Đồng`, `Chatbot Contact Center` |
| 4 | `gcp_project_id` | `text` | mã project trên Google Cloud | Cả 8/8 agent đều có. Dùng để nối với `fact_billing_daily.project` | `ai-chatbot-contract`, `pro-tuner-454203-v3` |
| 5 | `has_org_tree` | `boolean` | có cây tổ chức không | `true` ở 2/8 (TLA HĐ và Ralli) — chỉ hai app này khai phòng ban | `true` (2), `false` (6) |
| 6 | `project_created_at` | `date` | ngày lập project trên GCP | 7/8 có. Ralli để trống | `2025-03-19` … `2026-06-25` |
| 7 | `data_from` | `date` | ngày đầu tiên **có dữ liệu** | Khác `project_created_at`: lập project trước, có số liệu sau | `2026-01-01` … `2026-07-06` |
| 8 | `data_to` | `date` | ngày cuối có dữ liệu | `NULL` = **còn chạy**. Chỉ 2/8 có giá trị | `2026-08-13` (invoice), `2026-07-01` (quizzer) |
| 9 | `is_running` | `boolean` | còn hoạt động không | `true` (6), `false` (2 — invoice và tools-quizzer đã dừng) | `true` |
| 10 | `has_google_source` | `boolean` | có nối Google Billing/Monitoring không | **7/8 = `true`.** Ralli `false`: project `tla-ralli` CÓ tồn tại nhưng CHƯA nối billing. Cột này tồn tại để giao diện biết lúc nào phải hiện `-` thay vì `0%` | `false` (chỉ Ralli) |

**Trọn vẹn 8 dòng:**

| id | code | name | gcp_project_id | org_tree | created | from | to | running | google |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `contact-center` | Chatbot Contact Center | `pro-tuner-454203-v3` | ✗ | 2025-03-19 | 2026-01-13 | — | ✓ | ✓ |
| 2 | `sale-agent` | Sale Agent | `tranquil-post-471401-c1` | ✗ | 2025-09-07 | 2026-01-01 | — | ✓ | ✓ |
| 3 | `invoice` | Multi modal AI Invoice | `multimodal-invoice` | ✗ | 2025-09-15 | 2026-01-22 | 2026-08-13 | ✗ | ✓ |
| 4 | `tools-quizzer` | Tools Quizzer | `tools-quizz` | ✗ | 2026-04-10 | 2026-06-17 | 2026-07-01 | ✗ | ✓ |
| 5 | `tla-hd` | Trợ Lý Ảo Hợp Đồng | `ai-chatbot-contract` | ✓ | 2026-06-20 | 2026-07-02 | — | ✓ | ✓ |
| 6 | `dms-feedback` | Phân Loại Phản Hồi Tiếp Thị | `feedback-dms-tiep-thi` | ✗ | 2026-06-25 | 2026-07-06 | — | ✓ | ✓ |
| 7 | `crm-feedback` | Phân Loại Dữ Liệu CRM | `crm-500509` | ✗ | 2026-06-25 | 2026-07-06 | — | ✓ | ✓ |
| 8 | `ralli` | Trợ lý ảo Ralli | `tla-ralli` | ✓ | — | 2026-03-14 | — | ✓ | **✗** |

---

## `dim_unit` — Danh mục **đơn vị**, tức phòng ban / chi nhánh

130 dòng · Khoá chính `unit_id` · Tự trỏ về mình qua `parent_id` (cây phân cấp)

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `unit_id` | `text` | mã đơn vị | Khoá gốc của app: Ralli dùng ObjectId 24 ký tự, TLA HĐ dùng UUID | `69ee5b13be38bdbf5a8de666`, `ceadd40f-1a4f-…` |
| 2 | `agent_id` | `integer` | đơn vị này thuộc cây của app nào | 1–8. **Cùng một phòng ban ngoài đời có thể có 2 dòng ở 2 cây khác nhau** | `5`, `8` |
| 3 | `name` | `text` | tên phòng ban | Tên tiếng Việt có dấu | `Toàn công ty`, `TT C4LED`, `Đội 4 - Thanh Hoá` |
| 4 | `parent_id` | `text` | đơn vị cha | 117/130 có cha. 13 dòng `NULL` = gốc cây | `69ee5b13be38bdbf5a8de670` |
| 5 | `level` | `integer` | độ sâu trong cây | 0–5. `0` dành cho dòng kỹ thuật | `0`, `1`, `3`, `5` |
| 6 | `path` | `text` | đường dẫn đầy đủ từ gốc | Ghép tên các cấp bằng ` > `, để hiện lên màn hình mà không phải đệ quy | `Công ty CPBĐ PN Rạng Đông > Phòng BH3 > …` |
| 7 | `is_technical` | `boolean` | dòng kỹ thuật hay phòng ban thật | **`true` ở 8/130.** Gồm 6 dòng *"Đơn vị sử dụng &lt;agent&gt;"* và các dòng *"Chưa quy được"*. Không có cột này thì `COUNT(*)` đếm cả dòng kỹ thuật thành phòng ban thật | `false` (122), `true` (8) |

**Dữ liệu mẫu:**

| unit_id | agent | name | parent | level | path | technical |
|---|---|---|---|---|---|---|
| `__unattributed_5__` | 5 | Chưa quy được | — | 0 | `Chưa quy được` | ✓ |
| `__unattributed_8__` | 8 | Chưa quy được | — | 0 | `Chưa quy được` | ✓ |
| `69ee5b13be38bdbf5a8de666` | 8 | Toàn công ty | — | 1 | `Toàn công ty` | ✗ |
| `ceadd40f-1a4f-…` | 5 | TT C4LED | — | 1 | `TT C4LED` | ✗ |

---

## `account` — **Tài khoản** hợp nhất. Một dòng = một tài khoản, KHÔNG phải một con người

953 dòng · Khoá chính `account_id` · `username` là UNIQUE

**Vì sao bảng này tồn tại:** trước đây mỗi nguồn ghi *"ai dùng"* theo kiểu riêng — Ralli ghi ObjectId của Ralli, TLA HĐ ghi id của TLA HĐ, còn Google thì **không ghi người nào cả** (hoá đơn chỉ biết *"cả project này tiêu ngần này"*). Ba quyển sổ, không mã chung. Từ đây mọi nơi đều trỏ về `account_id`.

**Không dùng tên đăng nhập làm khoá ngoại** — tên đăng nhập là chuỗi, đã thấy ba dạng cho cùng một tài khoản (hoa/thường, khoảng trắng thừa, Ralli đôi khi ghi username vào chỗ ObjectId). Cột `username` ở đây đã `LOWER(TRIM())`.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `account_id` | `integer` | mã tài khoản chung | 1–953. Khoá dùng cho MỌI phép tính | `1`, `505`, `950` |
| 2 | `username` | `text` | tên đăng nhập | Đã hạ chữ thường, cắt khoảng trắng | `admin`, `bh1.longnt`, `quy.tv@rangdong.com.vn` |
| 3 | `full_name` | `text` | họ tên | 946/953 có | `Nguyễn Văn Quí`, `Quản trị viên` |
| 4 | `email` | `text` | thư điện tử | 927/953 có | `ct.giangcl@rangdong.com.vn` |
| 5 | `kind` | `text` | **loại tài khoản** | `real` (937) người thật · `whole_agent` (8) Google chỉ báo mức project nên không quy được về ai, một dòng mỗi agent · `unattributed` (8) có lượt gọi nhưng bản ghi không kèm người | `real` |
| 6 | `unit_id` | `text` | đơn vị của tài khoản | **Đơn vị nằm ở đây, không ở `dim_user`.** Một tài khoản = một đơn vị, đã chọn dứt điểm | `69ee5b13be38bdbf5a8de6c5` |
| 7 | `is_shared` | `integer` | tài khoản dùng chung? | `0`/`1`. `1` = `admin`, tài khoản thử… Vẫn tính đủ token và tiền, nhưng **phải loại khỏi tỷ lệ áp dụng** — `admin` một mình tạo 46,4% lưu lượng TLA HĐ | `0`, `1` |
| 8 | `role` | `text` | vai trò cao nhất trong các app | `MEMBER` (803) · `DT` (63) · `UNIT_LEAD` (42) · `COMPANY_ADMIN` (15) · `ADMIN` (4) · `PKH` (1) · `ASSISTANT` (1) · `NULL` (24) | `MEMBER` |
| 9 | `is_enabled` | `boolean` | tài khoản còn bật? | 891 `true`, 62 `NULL` (`NULL` = app không khai, khác với "bị tắt") | `true` |
| 10 | `created_at` | `timestamp` | ngày được cấp tài khoản | 891/953 có. Từ 02/04/2026 đến 12/08/2026 | `2026-04-26 17:59:49` |
| 11 | `unit_agent_id` | `integer` | đơn vị lấy từ cây của app nào | Ghi lại đã chọn cây nào, vì hai app mô hình hoá tổ chức khác nhau | `5`, `8` |
| 12 | `unit_conflict` | `integer` | các nguồn có bất đồng không | `1` = hai app nói hai đơn vị khác nhau, ta đã chọn hộ (lấy đơn vị **sâu nhất**). Giữ lại dấu vết để việc chọn không diễn ra âm thầm | `0`, `1` |

**Dữ liệu mẫu:**

| id | username | full_name | kind | unit_id | shared | role | enabled |
|---|---|---|---|---|---|---|---|
| 1 | `admin` | Quản trị viên | `real` | `__unattributed_5__` | **1** | — | — |
| 2 | `administrator` | Administrator | `real` | `69ee5b13be38bdbf5a8de667` | 0 | `MEMBER` | ✓ |
| 3 | `admintest` | Admin Test | `real` | `69ee5b13be38bdbf5a8de6b3` | 0 | `MEMBER` | ✓ |

---

## `dim_user` — **Bản ghi người dùng theo từng app** (thô, trước khi hợp nhất)

964 dòng · Khoá chính `(agent_id, user_id)`

Khác `account` thế nào: **nhiều dòng `dim_user` có thể trỏ vào CÙNG một `account`** — 13 dòng do Ralli ghi hai dạng khoá, 5 dòng do cùng tên đăng nhập tồn tại ở cả hai app, 1 dòng do hai tài khoản dùng chung email. Bảng này giữ nguyên hiện trạng từng app; `account` mới là bản đã gộp.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `user_id` | `text` | khoá GỐC của app | ObjectId của Ralli, hoặc id của TLA HĐ | `69ee5296c7fb84b9e507c2f9` |
| 2 | `agent_id` | `integer` | dòng này do app nào khai | 1–8 | `8` |
| 3 | `account_id` | `integer` | trỏ về tài khoản đã hợp nhất | 964/964 đều đã quy được | `472`, `516` |
| 4 | `username` | `text` | tên đăng nhập app khai | Giữ nguyên dạng gốc, chưa chuẩn hoá | `tg.xemdon`, `NCTT.TungTX` |
| 5 | `full_name` | `text` | họ tên | 935/964 có | `Trần Vinh Quy` |
| 6 | `email` | `text` | thư điện tử | 931/964 có | `crm.trangnt@rangdong.com.vn` |
| 7 | `unit_id` | `text` | đơn vị **theo cây của app này** | Đây là chỗ hai app bất đồng nhau | `69ee5b13be38bdbf5a8de6c6` |
| 8 | `is_enabled` | `boolean` | còn bật không | 891 `true`, 73 `NULL` | `true` |
| 9 | `created_at` | `timestamp` | ngày cấp | 891/964 có | `2026-04-02 01:04:35` |
| 10 | `is_technical` | `boolean` | dòng kỹ thuật? | `true` ở 6 dòng — sinh ra cho 6 agent một-người-dùng | `false` (958), `true` (6) |
| 11 | `found_in` | `text` | **tìm thấy ở đâu** | `directory` (935) có trong danh bạ · `log` (23) CHỈ thấy trong nhật ký, không có trong danh bạ (`system`, `admin`, `guest`) · `technical` (6) dòng tự sinh | `directory` |
| 12 | `role` | `text` | vai trò do CHÍNH APP khai | `MEMBER` (803) · `DT` (64) · `UNIT_LEAD` (45) · `COMPANY_ADMIN` (16) · `ADMIN` (4) · `ASSISTANT` · `PKH` · `NULL` (30) | `COMPANY_ADMIN` |

---

## `dim_model` — Danh mục **model** AI

10 dòng · Khoá chính `model_id` · `name` là UNIQUE

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `model_id` | `integer` | mã model | 1–10 | `4` |
| 2 | `name` | `text` | tên **CHUẨN**, dạng gạch ngang | Tên ta chọn làm gốc để ba nguồn quy về | `gemini-2.5-pro` |
| 3 | `family` | `text` | dòng model | `gemini-3` (4) · `gemini-2.5` (3) · `embedding` (2) · `gemini-2.0` (1) | `gemini-2.5` |
| 4 | `provider` | `text` | nhà cung cấp | Hiện toàn bộ 10/10 là `Google` | `Google` |

**Trọn vẹn 10 dòng — kèm giá từ `ref_price` (USD / 1 triệu token):**

| id | name | family | giá vào | giá ra | giá cached |
|---|---|---|---|---|---|
| 1 | `gemini-2.0-flash` | gemini-2.0 | 0,10 | 0,40 | — |
| 2 | `gemini-2.5-flash` | gemini-2.5 | 0,30 | 2,50 | 0,03 |
| 3 | `gemini-2.5-flash-lite` | gemini-2.5 | 0,10 | 0,40 | 0,01 |
| 4 | `gemini-2.5-pro` | gemini-2.5 | 1,25 | 10,00 | 0,125 |
| 5 | `gemini-3-flash` | gemini-3 | 0,50 | 3,00 | 0,05 |
| 6 | `gemini-3-pro` | gemini-3 | 2,00 | 12,00 | 0,20 |
| 7 | `gemini-3.1-flash-lite` | gemini-3 | 0,25 | 1,50 | — |
| 8 | `gemini-3.5-flash` | gemini-3 | 1,50 | 9,00 | — |
| 9 | `gemini-embedding-1.0` | embedding | 0,15 | — | — |
| 10 | `gemini-embedding-2` | embedding | 0,20 | — | — |

*(Hai model embedding không có giá đầu ra vì phép nhúng không sinh token ra.)*

---

## `dim_model_alias` — Bảng **dịch tên model**: ba nguồn gọi một model theo ba kiểu

44 dòng · Khoá chính `(source, raw_name)`

Không có bảng này thì phải đoán bằng chuỗi, mà `gemini-embedding-001` với `gemini-embedding-1.0` thì không quy tắc chuẩn hoá nào nói được với nhau.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `source` | `text` | nguồn gọi tên | `billing_sku` (31) mã SKU hoá đơn · `monitoring` (9) tên trong Cloud Monitoring · `app` (4) tên app tự ghi | `billing_sku` |
| 2 | `raw_name` | `text` | tên **thô** ở nguồn đó | SKU là mã 3 cụm; monitoring/app là tên chữ | `07D6-73CA-C859`, `gemini-2.0-flash` |
| 3 | `model_id` | `integer` | quy về model chuẩn nào | Trỏ sang `dim_model` | `5`, `1` |

**Dữ liệu mẫu — mỗi nguồn một dòng:**

| source | raw_name | → model_id |
|---|---|---|
| `app` | `gemini-2.0-flash` | 1 |
| `monitoring` | `gemini-2.0-flash` | 1 |
| `billing_sku` | `07D6-73CA-C859` | 5 |

---

## `dim_function` — Danh mục **chức năng** mà agent gọi

8 dòng · Khoá chính `(agent_id, code)`

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `agent_id` | `integer` | chức năng của agent nào | Hiện chỉ agent 5 và 8 có khai | `8` |
| 2 | `code` | `text` | mã chức năng | Tên hàm mà app gọi | `gemini_generate_text`, `gemini_structured_call` |
| 3 | `label` | `text` | nhãn tiếng Việt | Chỉ 2/8 có; 6 dòng còn lại `NULL` | `Hỏi đáp AI`, `Phân tích hợp đồng` |
| 4 | `is_user_facing` | `boolean` | người dùng gọi trực tiếp hay hệ thống gọi ngầm | **Cả 8/8 đều `NULL` = chưa biết.** Cố ý để `NULL` chứ KHÔNG mặc định `true` | `NULL` |

---

## `dim_metric_alias` — Bảng **dịch tên phép đo** của Google sang từ vựng của ta

44 dòng · Khoá chính `(source, raw_name)`

Cùng khuôn với `dim_model_alias`, sinh ra để chữa cùng một bệnh. Trước khi có bảng này, phân loại là **đoán tên** ở hai chỗ khác nhau (regex trên `sku_name`, và `LIKE '%token_count'`); Google đổi cách đặt tên thì cả hai trả về **rỗng** chứ không báo lỗi. Đổi thành bảng tra cứu thì tên lạ làm khâu nạp **dừng hẳn** — hỏng ồn ào, không hỏng im lặng.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `source` | `text` | nguồn của tên | `billing_sku` (31) · `monitoring` (13) | `monitoring` |
| 2 | `raw_name` | `text` | mã chính chủ của Google | SKU id, hoặc `metric_type` đầy đủ | `serviceruntime.googleapis.com/api/request_latencies` |
| 3 | `label` | `text` | mô tả chính chủ của Google | 44/44 có. Đây là chỗ regex chạy trên (thay vì trên tên tự chế) | `Distribution of latencies in seconds for non-streaming requests.` |
| 4 | `measures` | `text` | **phép đo này đo cái gì** | `token` (34) · `quota_limit` (5) · `calls` (4) · `latency` (1) | `token` |
| 5 | `kind` | `text` | loại token | `input` (17) · `output` (10) · `cached` (7) · `NULL` (10, khi không phải token) | `cached` |
| 6 | `metric_kind` | `text` | kiểu công tơ (Google khai) | `DELTA` (8) công tơ cộng dồn · `GAUGE` (5) hạn mức. Chỉ nguồn monitoring có | `DELTA` |
| 7 | `value_type` | `text` | kiểu giá trị (Google khai) | `INT64` (12) · `DISTRIBUTION` (1, chính là độ trễ) | `INT64` |

**Phần nào lấy từ metadata, phần nào vẫn phải đọc tên:**

| Kết luận | Suy ra từ đâu |
|---|---|
| `measures='quota_limit'` | metadata quyết định — `metricKind = GAUGE` |
| `measures='latency'` | metadata quyết định — `valueType = DISTRIBUTION` |
| `measures='token'` vs `'calls'` | metadata **KHÔNG** phân biệt (cả hai đều DELTA/INT64/unit=1) → vẫn phải đọc tên, nhưng đọc từ `raw_name` là mã API chính thức |
| `kind='input'/'output'/'cached'` | catalog SKU không có trường nào (cả 597 SKU đều `resourceGroup='Gemini'`) → regex trên `label` |

**Dữ liệu mẫu — mỗi loại `measures` một dòng:**

| source | raw_name (rút gọn) | measures | kind | metric_kind | value_type |
|---|---|---|---|---|---|
| `monitoring` | `…/quota/embed_content_paid_tier_3_requests/usage` | `calls` | — | DELTA | INT64 |
| `monitoring` | `serviceruntime…/api/request_latencies` | `latency` | — | DELTA | DISTRIBUTION |
| `monitoring` | `…/quota/embed_content_paid_tier_3_requests/limit` | `quota_limit` | — | GAUGE | INT64 |
| `billing_sku` | `07D6-73CA-C859` | `token` | `cached` | — | — |

---

# 2. Bảng sự kiện (`fact_`)

> **Nguyên tắc số một: mỗi nguồn một bảng riêng, không trộn.**

## `fact_call` — **Từng lượt gọi API**, mức mịn nhất. Chỉ Ralli có

8.330 dòng · Khoá chính `call_id` · Toàn bộ `agent_id = 8`

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `call_id` | `text` | mã lượt gọi | ObjectId từ nhật ký Ralli | `69b4ec3d1c64451042f7f58f` |
| 2 | `agent_id` | `integer` | agent nào | Luôn `8` (Ralli) | `8` |
| 3 | `ts_raw` | `timestamp` | **thời điểm chép nguyên**, chưa quy đổi | Giờ UTC. 14/03 → 17/08/2026 | `2026-03-14 05:03:57.488` |
| 4 | `tz_confirmed` | `boolean` | đã chứng minh múi giờ chưa | `true` cho cả 8.330 dòng — đã chứng minh là UTC | `true` |
| 5 | `ts_local` | `timestamp` | **giờ Việt Nam** (= `ts_raw` + 7h) | Đây là cột dùng để tính | `2026-03-14 12:03:57.488` |
| 6 | `user_id` | `text` | khoá **GỐC** của app, giữ để truy vết | 7.976/8.330 có. Trộn hai dạng: username và ObjectId | `system`, `tt3.longnhb`, `6a60535b2fb111497fa554c3` |
| 7 | `account_id` | `integer` | khoá **CHUNG**, dùng để tính toán | 8.330/8.330 đã quy được | `505` |
| 8 | `unit_id` | `text` | đơn vị | **7.887/8.330 rơi vào `__unattributed_8__`** — phần lớn lượt gọi là của `system` | `__unattributed_8__` |
| 9 | `model_id` | `integer` | model dùng | Chỉ 1–3 (2.0-flash, 2.5-flash, 2.5-flash-lite) | `1`, `3` |
| 10 | `function_code` | `text` | chức năng nào gọi | `gemini_generate_text` (4.344) · `gemini_structured_call` (3.607) · `gemini_chat_json_messages` (319) · `assistant_extract_image_text` (39) · … | `gemini_generate_text` |
| 11 | `prompt_tokens` | `bigint` | token đầu vào | 20 → 120.614 | `376` |
| 12 | `completion_tokens` | `bigint` | token đầu ra | 0 → 65.536 | `2305` |
| 13 | `total_tokens` | `bigint` | **cột chuẩn** — tổng token | 127 → 155.511. **KHÔNG tự cộng hai cột trên** (quy tắc 6) | `2681` |
| 14 | `cached_tokens` | `bigint` | token đọc từ bộ nhớ đệm | Chỉ 1.459/8.330 có. **`NULL` ở 6.871 dòng cũ nghĩa là "không biết", KHÔNG phải 0** (quy tắc 5) | `NULL`, `0`, `8625` |
| 15 | `record_format` | `smallint` | định dạng bản ghi | `1` (6.871) · `3` (917) · `2` (542). Ralli đổi cấu trúc log 3 lần — đây là dấu vết | `1` |

---

## `fact_app_daily` — Mức **ngày × người × model** do app tự tổng hợp (TLA Hợp Đồng)

77 dòng · Khoá chính `row_id` · Toàn bộ `agent_id = 5`

**Vì sao cần bảng riêng:** Ralli phơi từng lượt gọi nên vào được `fact_call`. TLA Hợp Đồng **chỉ phơi API đã tổng hợp sẵn**, mức mịn nhất lấy được là (ngày × người × model). Không có bảng này thì hoặc phải bịa ra lượt gọi giả, hoặc phải bỏ hẳn chiều người dùng của TLA HĐ — trước 14/08 là phương án thứ hai, và hậu quả là biểu đồ tỷ lệ áp dụng báo `0/39` trong khi sự thật là *"có người dùng, không nhìn thấy ai"*.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `row_id` | `integer` | số thứ tự | 1–77. Gán tường minh vì `model_id` được phép `NULL`, mà PostgreSQL cấm `NULL` trong khoá chính | `1` |
| 2 | `day` | `date` | ngày (giờ VN) | 14/03 → 15/08/2026 | `2026-03-14` |
| 3 | `agent_id` | `integer` | agent | Luôn `5` (TLA HĐ) | `5` |
| 4 | `account_id` | `integer` | tài khoản | 1–690 | `1` |
| 5 | `model_id` | `integer` | model | 75/77 có. **`NULL` = app không nói model** | `2`, `4`, `NULL` |
| 6 | `raw_model` | `text` | tên model **gốc**, giữ để truy vết | `gemini-2.5-flash` (56) · `gemini-2.5-pro` (19) · `none` (1) · `NULL` (1) | `gemini-2.5-pro` |
| 7 | `calls` | `integer` | số lượt gọi trong ngày | 1 → 230 | `143` |
| 8 | `total_tokens` | `bigint` | tổng token | 0 → 8.126.973 | `3227233` |
| 9 | `prompt_tokens` | `bigint` | token vào | 0 → 6.815.690 | `2532049` |
| 10 | `completion_tokens` | `bigint` | token ra | 0 → 1.311.283 | `695184` |

---

## `fact_billing_daily` — **Hoá đơn Google.** Nguồn DUY NHẤT có TIỀN

2.441 dòng · Khoá chính `(day, project, sku_id)` · 7/8 agent (Ralli không có)

> **Cảnh báo múi giờ:** Google cắt ngày hoá đơn theo giờ Thái Bình Dương; ta coi luôn là giờ VN, không quy đổi. **Tổng cả kỳ vẫn tuyệt đối đúng.** Cái phải biết: **ngày CUỐI CÙNG luôn hụt**, và mỗi ngày lẫn khoảng 15 giờ của ngày kề bên. Đủ để theo xu hướng, không đủ để đối chiếu một ngày lẻ với nguồn khác.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `day` | `date` | ngày hoá đơn | 01/01 → 16/08/2026 | `2026-07-02` |
| 2 | `agent_id` | `integer` | **khoá CHUẨN** | 1–7. Thêm vào để không phải nhớ viết `JOIN … ON gcp_project_id = project` mỗi lần — quên là mất dòng mà không lỗi nào báo | `5` |
| 3 | `project` | `text` | mã project GCP, giữ để truy vết | `pro-tuner-454203-v3` (921) · `tranquil-post-471401-c1` (909) · `multimodal-invoice` (394) · … | `ai-chatbot-contract` |
| 4 | `sku_id` | `text` | mã hàng hoá của Google | Mã 3 cụm. Nối vào `dim_model_alias` và `dim_metric_alias` | `0F51-429B-C2DC` |
| 5 | `sku_name` | `text` | tên hàng hoá | Mô tả dài của Google | `Generate content output token count Gemini 2.5 Pro short output text` |
| 6 | `model_id` | `integer` | model đã quy chuẩn | 2.441/2.441 đều quy được (1–10) | `4` |
| 7 | `kind` | `text` | **loại token** | `input` (1.138) · `output` (873) · `cached` (430) | `output` |
| 8 | `quantity` | `bigint` | **số token** | 5 → 24.990.232 | `15215` |
| 9 | `cost_usd` | `numeric(14,6)` | **tiền thật, USD** | 0 → 25,14 USD một dòng. **Đây là con số duy nhất không phải ước tính** | `0.152150` |

> **Bẫy `cached` ở hoá đơn:** cached là SKU **RIÊNG**, nằm **NGOÀI** input. Cộng cả ba mới ra tổng. Ở nguồn `app` thì ngược lại — cached là một phần **CỦA** `prompt_tokens`, cộng vào là đếm hai lần.

---

## `fact_monitoring` — Số đo **từng phút** từ Google Cloud Monitoring. Bảng lớn nhất

583.917 dòng · **Không có khoá chính** (là bảng thô) · 7/8 agent

Nạp **đủ** mọi dòng cào về, kể cả lưu lượng Drive/Sheets/Compute, rồi **lọc ở tầng view** `monitoring_ai`. Giữ dòng rác vì chính nó là bằng chứng: quên lọc thì agent `pro-tuner` sai **45,7 lần**.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `ts_utc` | `timestamp` | mốc thời gian **UTC** | 22/01 → 17/08/2026, từng phút | `2026-08-17 01:59:00` |
| 2 | `ts_local` | `timestamp` | mốc thời gian **giờ VN** | = `ts_utc` + 7h | `2026-08-17 08:59:00` |
| 3 | `agent_id` | `integer` | khoá CHUẨN | 1–7 | `5` |
| 4 | `project` | `text` | mã project, giữ để truy vết | `pro-tuner-454203-v3` chiếm 497.953/583.917 | `ai-chatbot-contract` |
| 5 | `metric_nickname` | `text` | **biệt danh** do script cào tự đặt | 14 giá trị. `api_request_count` (170.180) · `api_request_latencies_p95`/`_p99` (165.362 mỗi loại) · … Tiện đọc, nhưng **không có cam kết ổn định** | `generate_content_usage_output_token_count` |
| 6 | `metric_type` | `text` | **mã CHÍNH CHỦ của Google** | 13 giá trị. Đây mới là thứ nối vào `dim_metric_alias`. Trước đây cột này bị vứt lúc nạp — tức bỏ thứ ổn định, giữ thứ tự chế | `generativelanguage.googleapis.com/generate_content_usage_output_token_count` |
| 7 | `model_id` | `integer` | model | **Chỉ 83.013/583.917 (14,2%) có.** Phép đo dạng request không mang nhãn `model`. Trong view `monitoring_ai` tỷ lệ là 60,3% | `2` |
| 8 | `response_code` | `text` | mã HTTP trả về | Chỉ 170.180 dòng có. `200` (169.654) · `302` (277) · `503` (83) · `400` (58) · `404` (45) · `499` (27) · `500` (23) · `403` (13) | `200` |
| 9 | `service` | `text` | dịch vụ Google nào | **`drive.googleapis.com` (460.003) lấn át `generativelanguage.googleapis.com` (120.247)** — chính là lý do phải lọc | `generativelanguage.googleapis.com` |
| 10 | `method` | `text` | phương thức API | 500.904/583.917 có | `google.ai.generativelanguage.v1beta.GenerativeService.GenerateContent` |
| 11 | `credential_id` | `text` | khoá API nào gọi | Cùng phút cùng method vẫn nhiều dòng nếu nhiều API key. Dạng `oauth2:…` hoặc `apikey:…` | `apikey:536546b1-37fd-…` |
| 12 | `is_quota_limit` | `boolean` | dòng này là **hạn mức** hay số đo thật | `true` (26.370) = ALIGN_MAX, **KHÔNG được SUM**. Mọi hạn mức đều `GAUGE`, mọi công tơ đều `DELTA` | `false` |
| 13 | `thinking_enabled` | `text` | có bật chế độ suy luận không | 13.527 dòng có: `true` (10.568) · `false` (2.959). **Đây là nguồn duy nhất cho cột "think" trên dashboard** | `true` |
| 14 | `output_modality` | `text` | dạng đầu ra | 13.527 dòng có, toàn bộ là `text` | `text` |
| 15 | `limit_name` | `text` | tên hạn mức Google áp | 69.480 dòng có, 8 loại | `GenerateContentPaidTierInputTokensPerModelPerMinute` |
| 16 | `value` | `double precision` | **giá trị đo được** | Ý nghĩa **phụ thuộc `metric_type`**: token, số lượt, giây, hay hạn mức | `145.0` |
| 17 | `unit` | `text` | đơn vị | `s` (330.724) giây · `1` (253.193) đếm | `1` |

---

## `fact_usage_daily` — **Bảng ĐỐI CHỨNG.** Ba nguồn đặt cạnh nhau, chưa chọn

1.845 dòng · Khoá chính `(day, agent_id, model_id, account_id, source)`

> **Đọc bảng này để SO SÁNH ba nguồn, KHÔNG phải để hỏi một con số.** Muốn một con số thì đọc view `usage_resolved`. Vì `source` nằm trong khoá chính nên ai hỏi bảng này cũng phải tự chọn nguồn trước — đó là việc của view, không phải của người hỏi.
>
> **Không có cột `unit_id` — và đó là cố ý.** Đơn vị là thuộc tính CỦA tài khoản, `JOIN account` là ra. Chép thêm bản sao vào đây thì hai bản có thể lệch nhau.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `day` | `date` | ngày (giờ VN) | 01/01 → 17/08/2026 | `2026-07-26` |
| 2 | `agent_id` | `integer` | agent | 1–8 (đủ cả 8) | `7` |
| 3 | `model_id` | `integer` | model | 1–10. **NOT NULL** | `2` |
| 4 | `account_id` | `integer` | tài khoản | 1–953. **NOT NULL** — dùng dòng kỹ thuật (`whole_agent`/`unattributed`) thay cho `NULL` | `950` |
| 5 | `calls` | `integer` | số lượt gọi | 880/1.845 có (nguồn `billing` không đếm lượt) | `NULL`, `11582` |
| 6 | `total_tokens` | `bigint` | tổng token | 1.733/1.845 có. Tới 35.048.214 | `88818` |
| 7 | `input_tokens` | `bigint` | token vào | 1.732/1.845 có | `39649` |
| 8 | `output_tokens` | `bigint` | token ra | 1.727/1.845 có | `49169` |
| 9 | `cached_tokens` | `bigint` | token đệm | 1.063/1.845 có. **`monitoring` không có phép đo cached → luôn `NULL`** | `0` |
| 10 | `cost_usd` | `numeric(14,6)` | tiền | Chỉ 965/1.845 có — đúng bằng số dòng `source='billing'` | `0.134816` |
| 11 | `source` | `text` | **nguồn của dòng này** | `billing` (965) · `monitoring` (539) · `app` (341) | `billing` |

> **`cached` không cùng nghĩa ở ba nguồn** (đã đo, không phải suy): billing coi cached là SKU riêng ngoài input; app coi cached là tập con của `prompt_tokens`; monitoring không đo cached. Vì vậy `total_tokens` **giữ nguyên theo quy ước của nguồn**, và cột `source` cho biết đang đọc quy ước nào.

---

## `fact_perf_daily` — **Số lượt gọi theo mã lỗi**, mức ngày

600 dòng · Khoá chính `(day, agent_id, method, response_code)`

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `day` | `date` | ngày (giờ VN) | 22/01 → 17/08/2026 | `2026-01-22` |
| 2 | `agent_id` | `integer` | agent | 1–7 | `1` |
| 3 | `method` | `text` | phương thức API | 12 giá trị, đều thuộc `generativelanguage` | `google.ai.generativelanguage.v1beta.GenerativeService.EmbedContent` |
| 4 | `response_code` | `text` | **mã HTTP** | `200` (554) · `503` (21) · `400` (11) · `404` (6) · `499` (6) · `500` (2) | `200` |
| 5 | `calls` | `integer` | số lượt | 1 → 5.790 | `51` |

---

## `fact_latency_daily` — **Độ trễ** ở đúng độ mịn Google cho: một số cho mỗi (ngày, agent)

297 dòng · Khoá chính `(day, agent_id)`

**Vì sao tách khỏi `fact_perf_daily`:** hai chỉ tiêu đo ở hai độ mịn khác nhau. Số lượt có `response_code` và `method`; độ trễ thì **không** có `response_code`, và con số đúng chỉ tồn tại ở mức (ngày, agent) — phân vị không cộng được, phải gộp histogram rồi mới đọc mốc. Lấy trung bình các p95 từng phút đã đo thử: **lệch trên 19%**.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `day` | `date` | ngày (giờ VN) | 01/05 → 08/08/2026 | `2026-05-02` |
| 2 | `agent_id` | `integer` | agent | 1–7 | `3` |
| 3 | `samples` | `integer` | số mẫu vào histogram ngày đó | 1 → 5.791 | `15` |
| 4 | `p50_seconds` | `double precision` | **trung vị** — nửa số lượt nhanh hơn mức này | 0,197 → 39,15 giây | `1.7039` |
| 5 | `p95_seconds` | `double precision` | **phân vị 95** — 5% lượt chậm hơn mức này | 0,256 → 382,52 giây | `3.67` |
| 6 | `p95_bucket_from` | `double precision` | **cận dưới** ô histogram chứa p95 | Ô rộng gấp đôi sau mỗi bậc | `2.0972` |
| 7 | `p95_bucket_to` | `double precision` | **cận trên** ô đó | Trung vị bề rộng ô = **57% của chính giá trị p95** → dashboard phải hiện **KHOẢNG**, không phải số lẻ | `4.1943` |
| 8 | `p99_seconds` | `double precision` | phân vị 99 | 0,261 → 506,00 giây | `4.0894` |
| 9 | `enough_samples` | `boolean` | đủ mẫu để phân vị có nghĩa? | `true` (259) · **`false` (38) khi `samples < 10`** | `true` |

---

# 3. Bảng tham chiếu (`ref_`) — quy ước do người quyết định

## `ref_price` — **Bảng giá** model theo thời điểm hiệu lực

10 dòng · Khoá chính `(model_id, effective_from)` · Đơn vị: **USD / 1 triệu token**

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `model_id` | `integer` | model nào | 1–10, đủ cả 10 model | `4` |
| 2 | `effective_from` | `date` | **giá có hiệu lực từ ngày** | Hiện toàn bộ là `2026-08-13` — mới có một mốc giá duy nhất | `2026-08-13` |
| 3 | `price_input` | `numeric(12,8)` | giá token vào | 0,10 → 2,00 USD/1M. 10/10 có | `1.25000000` |
| 4 | `price_output` | `numeric(12,8)` | giá token ra | 0,40 → 12,00 USD/1M. 8/10 có (2 model embedding không sinh token ra) | `10.00000000` |
| 5 | `price_cached` | `numeric(12,8)` | giá token đệm | 0,01 → 0,20 USD/1M. Chỉ 5/10 có | `0.12500000` |
| 6 | `source` | `text` | giá lấy từ đâu | Cả 10/10 là `google`. Ba giá trị hợp lệ: `derived` (suy ra) · `google` · `vendor` | `google` |

> ⚠️ Bảng này là gốc của các con số **ước tính**. Phần tiền hiển thị mà không đến từ `fact_billing_daily` đều tính bằng bảng giá này — giao diện hiện không phân biệt.

## `ref_fx` — **Tỷ giá** quy đổi USD sang VND

1 dòng · Khoá chính `day`

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `day` | `date` | ngày áp dụng | Chỉ có **một** dòng: `2026-08-08` | `2026-08-08` |
| 2 | `vnd_per_usd` | `numeric(12,2)` | bao nhiêu VND cho 1 USD | `25200.00` | `25200.00` |
| 3 | `source` | `text` | tỷ giá lấy từ đâu | `hardcoded (app.js)` — **gõ tay trong mã nguồn**, chưa kéo từ API nào | `hardcoded (app.js)` |

## `ref_budget` — **Ngân sách** theo agent theo tháng

7 dòng · Khoá chính `(agent_id, month)` · Ràng buộc: `budget_usd` hoặc `budget_tokens` phải có ít nhất một

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `agent_id` | `integer` | agent nào | 7 agent (thiếu agent 4 `tools-quizzer` đã dừng) | `1` |
| 2 | `month` | `date` | tháng, ghi bằng ngày mùng 1 | Hiện chỉ có `2026-08-01` | `2026-08-01` |
| 3 | `budget_usd` | `numeric(12,2)` | ngân sách theo **tiền** | 6/7 agent. 20–50 USD/tháng | `30.00` |
| 4 | `budget_tokens` | `bigint` | ngân sách theo **token** | Chỉ Ralli. **Không quy đổi sang USD**: quy ra USD thì ngân sách trôi mỗi lần bảng giá đổi, trong khi Ralli đang bị chặn theo token thật | `50000000` |

**Trọn vẹn 7 dòng (tháng 08/2026):**

| agent | code | budget_usd | budget_tokens |
|---|---|---|---|
| 1 | contact-center | 30,00 | — |
| 2 | sale-agent | 50,00 | — |
| 3 | invoice | 20,00 | — |
| 5 | tla-hd | 20,00 | — |
| 6 | dms-feedback | 20,00 | — |
| 7 | crm-feedback | 20,00 | — |
| 8 | ralli | — | **50.000.000 token** |

---

# 4. View

## `usage_resolved` — **CỬA CHÍNH để hỏi số liệu.** Đã chọn sẵn nguồn

1.189 dòng · Một dòng cho mỗi `(ngày, agent, model)`

Đây là cái `fact_usage_daily` lẽ ra phải là. Bảng đó đặt ba nguồn cạnh nhau và bắt người hỏi tự chọn; view này **chọn sẵn, và nói rõ nó đã chọn gì**.

**Chọn theo từng chỉ tiêu, không phải theo từng dòng** — mỗi nguồn mạnh một thứ:

| Chỉ tiêu | Thứ tự ưu tiên |
|---|---|
| tiền | **chỉ** `billing` có |
| token | `billing` → thiếu thì `monitoring` → thiếu nữa thì `app` |
| lượt gọi | `monitoring` → thiếu thì `app`. `billing` không có |
| người dùng | **chỉ** `app` có |

**Không cộng ba nguồn lại** — chúng đo CÙNG một lưu lượng bằng ba cái công tơ khác nhau. Cộng lại là đếm ba lần.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `day` | `date` | ngày (giờ VN) | 01/01 → 17/08/2026 | `2026-01-01` |
| 2 | `agent_id` | `integer` | agent | 1–8 | `2` |
| 3 | `model_id` | `integer` | model | 1–10 | `1` |
| 4 | `total_tokens` | `numeric` | tổng token đã chọn nguồn | 1.179/1.189 có. Tới 35.048.214 | `950445` |
| 5 | `input_tokens` | `numeric` | token vào | Lấy từ **CÙNG nguồn** với `total_tokens`, không COALESCE riêng từng cột | `887473` |
| 6 | `output_tokens` | `numeric` | token ra | nt. | `62972` |
| 7 | `cached_tokens` | `numeric` | token đệm | 998/1.189 có | `0` |
| 8 | `cost_usd` | `numeric` | tiền | **Chỉ 965/1.189 (81,2%) có** — phần còn lại không có hoá đơn | `0.113907` |
| 9 | `calls` | `bigint` | số lượt gọi | 707/1.189 có | `NULL` |
| 10 | `token_source` | `text` | **con số token này từ nguồn nào** | `billing` (965) · `app` (168) · `monitoring` (46) · `NULL` (10) | `billing` |
| 11 | `call_source` | `text` | **con số lượt gọi này từ nguồn nào** | `monitoring` (539) · `app` (168) · `NULL` (482) | `NULL` |
| 12 | `token_estimated` | `integer` | **1 = chưa được hoá đơn xác nhận** | `0` (965) · `1` (224) | `0` |

> **Hai cột `*_source` là BẮT BUỘC, không phải trang trí.** Một con số token của hôm nay đến từ `monitoring` (ước tính, hoá đơn chưa về) trông **y hệt** con số tuần trước đến từ hoá đơn. Không có cột này thì không phân biệt được.
>
> Ralli (`agent_id=8`) **luôn** rơi về `app` vì project `tla-ralli` chưa nối billing.

**Tổng quan hiện tại theo nguồn:**

| token_source | số dòng | tổng token | tổng tiền (USD) |
|---|---|---|---|
| `billing` | 965 | 708.868.471 | **291,99** |
| `app` | 168 | 104.990.903 | — |
| `monitoring` | 46 | 53.797.736 | — |
| `NULL` | 10 | — | — |

**Tổng quan theo agent:**

| agent | code | dòng | tổng token | tiền (USD) |
|---|---|---|---|---|
| 1 | contact-center | 470 | 333.221.182 | 100,13 |
| 2 | sale-agent | 350 | 300.806.849 | 131,62 |
| 3 | invoice | 106 | 95.881.301 | 17,44 |
| 4 | tools-quizzer | 7 | 63.304 | 0,04 |
| 5 | tla-hd | 59 | 70.240.065 | 18,65 |
| 6 | dms-feedback | 19 | 8.829.396 | 8,90 |
| 7 | crm-feedback | 43 | 10.681.235 | 15,20 |
| 8 | **ralli** | 135 | 47.933.778 | **— (không có hoá đơn)** |

---

## `usage_by_account` — Cùng số liệu, **nhìn theo tài khoản**

320 dòng · Lọc `source='app'` và `kind='real'`

**Chỉ phủ phần có nguồn `app`** — vì Google không ghi ai gọi. Chỉ agent 5 và 8 xuất hiện.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `day` | `date` | ngày | 14/03 → 17/08/2026 | `2026-07-01` |
| 2 | `agent_id` | `integer` | agent | Chỉ `5` và `8` | `8` |
| 3 | `model_id` | `integer` | model | 1–4 | `3` |
| 4 | `unit_id` | `text` | đơn vị — lấy từ `account`, **không** từ fact | 22 giá trị | `69ee5b13be38bdbf5a8de666` |
| 5 | `unit_path` | `text` | đường dẫn đơn vị | **`Chưa quy được` chiếm 223/320 (69,7%)** | `Toàn công ty` |
| 6 | `unit_conflict` | `integer` | các nguồn có bất đồng đơn vị không | `0`/`1` | `0` |
| 7 | `is_shared` | `integer` | tài khoản dùng chung? | `0`/`1` — nhớ loại `1` khi tính tỷ lệ áp dụng | `1` |
| 8 | `account_id` | `integer` | tài khoản | 1–891 | `505` |
| 9 | `username` | `text` | tên đăng nhập | 320/320 có | `system`, `c4led.anhld`, `admin` |
| 10 | `full_name` | `text` | họ tên | **Chỉ 194/320 (60,6%) có** | `Lê Đức Anh` |
| 11 | `email` | `text` | thư điện tử | **Chỉ 96/320 (30,0%) có** | `c4led.anhld@rangdong.com.vn` |
| 12 | `calls` | `integer` | số lượt gọi | 1 → 663 | `14` |
| 13 | `total_tokens` | `bigint` | tổng token | 350 → 8.126.973 | `75588` |
| 14 | `input_tokens` | `bigint` | token vào | 236 → 6.815.690 | `73500` |
| 15 | `output_tokens` | `bigint` | token ra | 3 → 1.311.283 | `2088` |

---

## `monitoring_ai` — `fact_monitoring` **đã lọc**, dùng khi cần số liệu thô

93.877 dòng (từ 583.917 — **giữ lại 16,1%**)

```sql
CREATE VIEW monitoring_ai AS
SELECT * FROM fact_monitoring
WHERE service = 'generativelanguage.googleapis.com'
  AND is_quota_limit = FALSE;
```

Cột giống hệt `fact_monitoring`. Khác biệt sau khi lọc:

| Cột | Ở bảng thô | Ở view |
|---|---|---|
| `service` | 12 dịch vụ, `drive.googleapis.com` chiếm 78,8% | **1 dịch vụ duy nhất** |
| `is_quota_limit` | 26.370 dòng `true` | **0 dòng** — chỉ còn số đo thật |
| `model_id` có giá trị | 83.013/583.917 = **14,2%** | 56.643/93.877 = **60,3%** |
| `project` lớn nhất | `pro-tuner` (497.953) | `tranquil-post` (51.114) — **thứ hạng đảo hẳn** |
| `value` lớn nhất | 9,22 × 10¹⁸ (giá trị hạn mức "vô hạn") | 3.961.961 |

Dòng cuối của bảng trên là lý do view tồn tại: quên lọc thì giá trị hạn mức giả sẽ trộn vào phép cộng.

---

# Phụ lục: sơ đồ quan hệ

```
                        ┌─────────────┐
                        │  dim_agent  │ 8  ← gốc của mọi thứ
                        └──────┬──────┘
          ┌────────────┬───────┼────────┬─────────────┐
          ▼            ▼       ▼        ▼             ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐
    │ dim_unit │ │ dim_user │ │dim_funct.│ │ ref_budget │
    │   130    │ │   964    │ │    8     │ │     7      │
    └────┬─────┘ └────┬─────┘ └──────────┘ └────────────┘
         │            │
         └──────┬─────┘
                ▼
          ┌───────────┐          ┌───────────┐      ┌───────────┐
          │  account  │ 953      │ dim_model │ 10 ──│ ref_price │ 10
          └─────┬─────┘          └─────┬─────┘      └───────────┘
                │                      │
    ┌───────────┼──────────┬───────────┼────────────┐
    ▼           ▼          ▼           ▼            ▼
┌─────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────┐
│fact_call│ │fact_app_ │ │fact_bill-│ │fact_moni- │ │fact_perf_ /  │
│  8.330  │ │  daily   │ │ing_daily │ │  toring   │ │  latency_    │
│ (Ralli) │ │    77    │ │  2.441   │ │  583.917  │ │  600 / 297   │
│từng lượt│ │(TLA HĐ)  │ │ có TIỀN  │ │ từng phút │ │ lỗi / độ trễ │
└────┬────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘ └──────────────┘
     └───────────┴────────────┼─────────────┘
              nguồn 'app'     │  'billing'   'monitoring'
                              ▼
                  ┌───────────────────────┐
                  │   fact_usage_daily    │ 1.845 — ĐỐI CHỨNG
                  │  (3 nguồn cạnh nhau)  │    chưa chọn nguồn
                  └───────────┬───────────┘
                              ▼
                  ┌───────────────────────┐
                  │    usage_resolved     │ 1.189 — CỬA CHÍNH
                  │  (đã chọn sẵn nguồn)  │    hỏi số liệu ở đây
                  └───────────────────────┘
```

---

# Phụ lục: bảng tra nhanh số dòng

| Đối tượng | Loại | Số dòng | Khoá chính |
|---|---|---|---|
| `ref_fx` | bảng | 1 | `day` |
| `ref_budget` | bảng | 7 | `(agent_id, month)` |
| `dim_agent` | bảng | 8 | `agent_id` |
| `dim_function` | bảng | 8 | `(agent_id, code)` |
| `dim_model` | bảng | 10 | `model_id` |
| `ref_price` | bảng | 10 | `(model_id, effective_from)` |
| `dim_model_alias` | bảng | 44 | `(source, raw_name)` |
| `dim_metric_alias` | bảng | 44 | `(source, raw_name)` |
| `fact_app_daily` | bảng | 77 | `row_id` |
| `dim_unit` | bảng | 130 | `unit_id` |
| `fact_latency_daily` | bảng | 297 | `(day, agent_id)` |
| `fact_perf_daily` | bảng | 600 | `(day, agent_id, method, response_code)` |
| `account` | bảng | 953 | `account_id` |
| `dim_user` | bảng | 964 | `(agent_id, user_id)` |
| `fact_usage_daily` | bảng | 1.845 | `(day, agent_id, model_id, account_id, source)` |
| `fact_billing_daily` | bảng | 2.441 | `(day, project, sku_id)` |
| `fact_call` | bảng | 8.330 | `call_id` |
| `fact_monitoring` | bảng | **583.917** | *(không có)* |
| `usage_by_account` | view | 320 | — |
| `usage_resolved` | view | 1.189 | — |
| `monitoring_ai` | view | 93.877 | — |
| **Tổng (18 bảng)** | | **599.686** | |

---
---

# 🟡 PHẦN II — SCHEMA ĐỀ XUẤT CHO KIẾN TRÚC API GATEWAY

> ## ⚠️ KHÔNG BẢNG NÀO DƯỚI ĐÂY TỒN TẠI
>
> Đây là **bản vẽ để bàn**, soạn ngày 19/08/2026. Database đang chạy vẫn là 18 bảng
> ở Phần I. Chạy `SELECT * FROM fact_attempt` sẽ báo lỗi — bảng đó chưa có.
>
> **Ba điểm còn treo** chưa được quyết, xem mục 8 cuối phần này. Chúng đổi được
> hình dạng schema, nên đừng coi bản vẽ này là đã chốt.

**Nguồn của đề xuất:**

| Tài liệu | Vai trò |
|---|---|
| `docs/reference/Tài_liệu_triển_khai_API_Gateway.docx` (12/08/2026) | kiến trúc Gateway, luồng xác thực, định dạng dữ liệu trao đổi |
| `docs/reference/Bao_cao_LiteLLM_Token_Ledger.md` (16/08/2026) | chức năng LiteLLM, phần nào miễn phí phần nào Enterprise |
| Phần I của chính file này | schema hiện tại, và các bài học đã trả giá để có |

---

## 1. Vì sao phải đổi schema

Schema hiện tại được thiết kế để **đi nhặt số từ ba quyển sổ của người khác**. Gateway
làm số liệu trở thành **của chính ta**, ghi tại điểm request đi qua.

```
HÔM NAY — nhặt số từ ba nguồn không đồng ý với nhau
┌──────────┐   ┌──────────────┐   ┌───────────────┐
│ 8 agent  │──▶│  8 project   │──▶│ Google        │
└──────────┘   │     GCP      │   │ billing CSV   │──┐
      │        └──────────────┘   │ + Monitoring  │  │
      │ 2/8 app phơi API riêng    └───────────────┘  │
      └──────────────────────────────────────────────┼──▶ 3 bộ đếm
                        ba tên gọi khác nhau ────────┘    KHÔNG khớp

NGÀY MAI — số liệu do CHÍNH TA ghi
┌──────────┐   ┌─────────────────────┐   ┌──────────────┐
│ 8 agent  │──▶│  API Gateway        │──▶│ OpenAI       │
└──────────┘   │  (LiteLLM engine)   │   │ Anthropic    │
               │                     │   │ Google AI    │
   gửi kèm:    │  ghi lại:           │   └──────────────┘
   • username  │  • token vào/ra     │
   • phòng ban │  • cost             │──▶ MỘT bộ đếm, mức TỪNG REQUEST,
   • API key   │  • provider đã chọn │    CÓ SẴN danh tính người dùng
   • route     │  • thời điểm        │
               └─────────────────────┘
```

Chuyển dịch cốt lõi: **Google không bao giờ biết ai gọi — Gateway thì biết, vì chính
agent khai vào request** (§8.1 tài liệu triển khai).

---

## 2. Bốn thứ ở Phần I tan biến

| Bỏ được | Vì sao |
|---|---|
| `dim_model_alias` (44 dòng) | Ba nguồn gọi model ba kiểu → còn một nguồn, một tên |
| `dim_metric_alias` (44 dòng) | Không cào Cloud Monitoring nữa thì không còn tên đo của Google để dịch |
| `source` trong khoá chính `fact_usage_daily` | Không còn ba bộ đếm để đặt cạnh nhau |
| View `usage_resolved` | Nó tồn tại **chỉ** để chọn giữa ba nguồn. Hết nguồn để chọn |

Và hai bảng sự kiện hợp nhất: `fact_call` (Ralli, từng lượt) với `fact_app_daily`
(TLA HĐ, ngày×người×model) tách nhau **chỉ vì hai app phơi dữ liệu ở hai độ mịn**.
Qua Gateway thì mọi agent đều có mức từng-request.

Kéo theo: bức tường `RALLI, TLA_HD = 8, 5` ở `db/load_org.py:81` biến mất — đó là
giới hạn co giãn nghiêm trọng nhất của kiến trúc hiện tại.

---

## 3. Ba vấn đề MỚI mà Gateway tạo ra

### 3.1. Cân bằng tải **cắt đứt** quan hệ agent ↔ project

Tài liệu triển khai §5.2:

> *"khi deployment của Agent A gần chạm giới hạn, nó sẽ tự động bị loại khỏi danh sách
> ứng viên… request sẽ được chuyển hướng sang deployment của Agent B"*

```
   Agent A gọi  ──▶  Gateway  ──▶  project của Agent B  ──▶  Google
        │                                    │
   ai HỎI                              ai TRẢ TIỀN
        └──────── KHÔNG CÒN LÀ MỘT ─────────┘
```

Schema Phần I **gộp hai chuyện này làm một**: `fact_billing_daily` có cả `agent_id`
lẫn `project`, và `agent_id` được **suy ra TỪ** `project` qua `dim_agent.gcp_project_id`.

**Sau Gateway phép suy đó sai.** Hoá đơn Google ghi nợ project B cho lưu lượng của
Agent A. Giữ nguyên cách nối hiện tại thì dashboard báo Agent B tiêu tiền của Agent A,
**không lỗi nào báo ra** — đúng loại hỏng im lặng mà dự án đã tốn công dọn.

→ Lời giải: tách thành hai chiều độc lập, `dim_agent` (ai hỏi) và `dim_deployment`
(ai trả tiền). Cột `gcp_project_id` **rời khỏi** `dim_agent`.

### 3.2. Một request của agent ≠ một lần gọi provider

Router có cooldown, retry, fallback sang provider khác. Cộng thêm cache (báo cáo
LiteLLM §2.4): **cache hit = agent nhận được trả lời, provider tiêu 0 token, 0 đồng.**

```
   1 request của agent
   ├── cache hit                          → 0 lần gọi provider
   ├── thành công ngay                    → 1 lần gọi
   └── 429 → cooldown → retry → fallback  → 3 lần gọi, 2 lần cháy tiền vô ích
```

Ghi một bảng duy nhất thì phải chọn: hoặc **đếm thiếu tiền** (bỏ qua retry), hoặc
**đếm thừa request** (mỗi lần thử thành một lượt). Không cách nào đúng cả hai.

→ Lời giải: **hai độ mịn** — `fact_request` và `fact_attempt`, quan hệ 1:N với N≥0.

### 3.3. Đa provider làm "cached" **rối hơn** chứ không đỡ đi

Hiện `dim_model.provider` là `Google` 100%. Gateway đi ba nhà, mỗi nhà định nghĩa
token khác nhau:

| Provider | Chỗ lệch |
|---|---|
| Google | `cachedContentTokenCount` là **tập con của** prompt tokens |
| Anthropic | tách `cache_creation` và `cache_read` — **hai mức giá khác nhau** |
| OpenAI | có `reasoning_tokens` nằm trong output, hai nhà kia không có |

Ghi chú trong `db/01_schema.sql` — *"cached KHÔNG cùng nghĩa ở ba nguồn… Ép ba nguồn
về một định nghĩa sẽ làm sai một trong hai đầu, mà không đầu nào kêu"* — **vẫn đúng
nguyên xi**, chỉ đổi "ba nguồn" thành "ba provider".

→ Lời giải: tách hẳn `cached_read_tokens` / `cached_write_tokens` / `reasoning_tokens`
thành cột riêng, không gộp.

---

## 4. Quan hệ với schema của LiteLLM — phải chốt TRƯỚC khi vẽ bảng

LiteLLM **đã có schema riêng**: bảng `LiteLLM_SpendLogs` trong Postgres của nó (báo cáo
§2.2). Câu hỏi thật không phải "thiết kế từ đầu" mà là quan hệ giữa hai bên.

| | Cách làm | Được | Mất |
|---|---|---|---|
| **A** | Đọc thẳng `LiteLLM_SpendLogs` | Không ETL, luôn tươi | Dính chặt schema bên thứ ba, họ đổi phiên bản là gãy. Không thêm được cột của mình |
| **B** ★ | Bảng riêng, ETL từ Postgres của LiteLLM | Tự chủ schema, chèn được `unit_id`, xử lý được 3.2 và 3.3, giữ được lịch sử cũ | Một bước đồng bộ phải nuôi |
| **C** | Gateway bắn event thẳng vào store của mình | Kiểm soát tối đa | Viết nhiều nhất, tự làm lại thứ LiteLLM đã có |

**Đề xuất: phương án B.** Lý do quyết định: `LiteLLM_SpendLogs` **không biết phòng ban**
— cây tổ chức 130 đơn vị là tài sản riêng của Token Ledger. Thêm nữa §4 tài liệu triển
khai nói ba service Usage / Report / Alert đọc chung một database, nên kho phải là của
ta. Bảng của LiteLLM là **nguồn**, không phải **kho**.

---

## 5. Schema đề xuất

### 5.1. Bảng danh mục

```sql
-- ai HỎI. Bỏ gcp_project_id: agent không còn sở hữu project nào (xem 3.1)
CREATE TABLE dim_agent (
    agent_id     INT PRIMARY KEY,
    code         TEXT UNIQUE NOT NULL,
    name         TEXT NOT NULL,
    is_running   BOOLEAN NOT NULL,
    data_from    DATE NOT NULL,
    data_to      DATE                    -- NULL = còn chạy
);

-- ★MỚI. 3 dòng: openai | anthropic | google
CREATE TABLE dim_provider (
    provider_id  INT PRIMARY KEY,
    code         TEXT UNIQUE NOT NULL,
    name         TEXT NOT NULL
);

-- ★MỚI. ai TRẢ TIỀN. Một dòng = một deployment trong config.yaml của LiteLLM.
-- ĐÂY là chỗ ở mới của gcp_project_id: nó là thuộc tính của ĐÍCH ĐẾN,
-- không còn là thuộc tính của agent.
CREATE TABLE dim_deployment (
    deployment_id  INT PRIMARY KEY,
    provider_id    INT NOT NULL REFERENCES dim_provider,
    model_id       INT NOT NULL REFERENCES dim_model,
    credential_ref TEXT NOT NULL,   -- project GCP / tổ chức OpenAI / workspace Anthropic
    rpm_limit      INT,             -- để đối chiếu lỗi 429 với hạn mức thật
    tpm_limit      BIGINT,
    is_active      BOOLEAN NOT NULL
);

-- ★MỚI. Đơn vị xác thực VÀ đơn vị tính ngân sách của LiteLLM (§7.1 tài liệu).
-- Cầu nối agent <-> chi tiêu.
CREATE TABLE dim_virtual_key (
    key_id      INT PRIMARY KEY,
    key_hash    TEXT UNIQUE NOT NULL,   -- KHÔNG lưu khoá thô
    agent_id    INT NOT NULL REFERENCES dim_agent,
    alias       TEXT,
    created_at  TIMESTAMP NOT NULL,
    revoked_at  TIMESTAMP               -- NULL = còn hiệu lực
);

CREATE TABLE dim_model (
    model_id     INT PRIMARY KEY,
    name         TEXT NOT NULL,          -- tên chuẩn
    provider_id  INT NOT NULL REFERENCES dim_provider,
    family       TEXT,
    UNIQUE (provider_id, name)
);

-- GIỮ NGUYÊN từ Phần I. 130 phòng ban, cây phân cấp, is_technical.
CREATE TABLE dim_unit (...);

-- GIỮ, nhưng ĐƠN GIẢN HƠN NHIỀU — xem 6.1
CREATE TABLE account (
    account_id  INT PRIMARY KEY,
    username    TEXT UNIQUE NOT NULL,    -- vẫn LOWER(TRIM()) — xem 6.1
    full_name   TEXT,
    email       TEXT,
    unit_id     TEXT NOT NULL REFERENCES dim_unit,
    is_shared   BOOLEAN NOT NULL,        -- vẫn cần: loại khỏi tỷ lệ áp dụng
    is_enabled  BOOLEAN,
    created_at  TIMESTAMP
);
```

### 5.2. Bảng sự kiện — hai độ mịn, đây là chỗ then chốt

```sql
-- 1 dòng = 1 REQUEST agent gửi vào Gateway. Kể cả cache hit và bị chặn ngân sách.
CREATE TABLE fact_request (
    request_id         TEXT PRIMARY KEY,
    ts_utc             TIMESTAMP NOT NULL,
    ts_local           TIMESTAMP NOT NULL,   -- giờ VN, như mọi cột ngày khác
    agent_id           INT  NOT NULL REFERENCES dim_agent,
    key_id             INT  NOT NULL REFERENCES dim_virtual_key,
    account_id         INT  NOT NULL REFERENCES account,
    unit_id            TEXT NOT NULL REFERENCES dim_unit,
    requested_model_id INT  REFERENCES dim_model,   -- model agent XIN
    -- 'ok' | 'cache_hit' | 'failed' | 'blocked_budget'
    outcome            TEXT NOT NULL,
    attempts           SMALLINT NOT NULL,   -- 0 khi cache hit, N khi phải thử lại
    latency_ms         INT,                 -- đo từ phía CLIENT, GỒM cả retry
    total_tokens       BIGINT,              -- cộng từ các attempt
    total_cost_usd     NUMERIC(14,6)
);

-- 1 dòng = 1 lần THẬT SỰ gọi provider.  ★ giải bài 3.2
CREATE TABLE fact_attempt (
    attempt_id          BIGINT PRIMARY KEY,
    request_id          TEXT NOT NULL REFERENCES fact_request,
    attempt_no          SMALLINT NOT NULL,
    deployment_id       INT NOT NULL REFERENCES dim_deployment,  -- ★ quota của AI bị trừ
    served_model_id     INT REFERENCES dim_model,   -- model THẬT chạy; fallback đổi được
    status_code         TEXT,
    error_class         TEXT,                       -- '429' | 'timeout' | '5xx' | NULL
    input_tokens        BIGINT,
    output_tokens       BIGINT,
    cached_read_tokens  BIGINT,     -- ★ giải bài 3.3: tách hẳn, KHÔNG gộp
    cached_write_tokens BIGINT,
    reasoning_tokens    BIGINT,
    cost_usd            NUMERIC(14,6),
    -- 'gateway_price' = LiteLLM tự tính | 'provider_invoice' = đã đối chiếu hoá đơn
    cost_basis          TEXT NOT NULL,
    latency_ms          INT,
    UNIQUE (request_id, attempt_no)
);

-- Bảng CUỘN cho dashboard. Đọc từ hai bảng trên, không đọc file.
CREATE TABLE fact_usage_daily (
    day            DATE NOT NULL,
    agent_id       INT  NOT NULL REFERENCES dim_agent,
    unit_id        TEXT NOT NULL REFERENCES dim_unit,
    account_id     INT  NOT NULL REFERENCES account,
    model_id       INT  NOT NULL REFERENCES dim_model,
    provider_id    INT  NOT NULL REFERENCES dim_provider,
    requests       INT NOT NULL,
    cache_hits     INT NOT NULL,
    attempts       INT NOT NULL,
    errors_429     INT NOT NULL,
    errors_5xx     INT NOT NULL,
    input_tokens   BIGINT,
    output_tokens  BIGINT,
    cached_tokens  BIGINT,
    cost_usd       NUMERIC(14,6),
    data_era       TEXT NOT NULL,       -- ★ 'scrape' | 'gateway' — xem 6.2
    PRIMARY KEY (day, agent_id, account_id, model_id, provider_id, data_era)
);

-- Hoá đơn NHÀ CUNG CẤP, giữ lại để ĐỐI CHIẾU.  ★ giải bài 3.1
-- Khoá theo credential_ref chứ KHÔNG theo agent_id: hoá đơn ghi nợ theo project,
-- mà project giờ không thuộc về agent nào.
CREATE TABLE fact_invoice_daily (
    day            DATE NOT NULL,
    provider_id    INT  NOT NULL REFERENCES dim_provider,
    credential_ref TEXT NOT NULL,
    model_id       INT  REFERENCES dim_model,
    kind           TEXT NOT NULL,       -- 'input' | 'output' | 'cached'
    quantity       BIGINT NOT NULL,
    cost_usd       NUMERIC(14,6) NOT NULL,
    PRIMARY KEY (day, provider_id, credential_ref, model_id, kind)
);
```

### 5.3. Bảng tham chiếu

```sql
-- Giá THEO PROVIDER. Cần giữ dù LiteLLM tự tính cost, vì bảng giá nội bộ của
-- LiteLLM đổi theo phiên bản của họ — muốn tính lại lịch sử thì phải có bản của mình.
CREATE TABLE ref_price (
    provider_id       INT NOT NULL REFERENCES dim_provider,
    model_id          INT NOT NULL REFERENCES dim_model,
    effective_from    DATE NOT NULL,
    price_input       NUMERIC(12,8),
    price_output      NUMERIC(12,8),
    price_cache_read  NUMERIC(12,8),
    price_cache_write NUMERIC(12,8),
    source            TEXT NOT NULL,   -- 'provider' | 'litellm' | 'derived'
    PRIMARY KEY (provider_id, model_id, effective_from)
);

-- BẢN SAO ngân sách mà LiteLLM đang thực thi. Xem cảnh báo ở 6.3.
CREATE TABLE ref_budget (
    agent_id      INT NOT NULL REFERENCES dim_agent,
    key_id        INT REFERENCES dim_virtual_key,
    period_start  DATE NOT NULL,
    budget_usd    NUMERIC(12,2),
    budget_tokens BIGINT,
    synced_at     TIMESTAMP NOT NULL,   -- ★ lần cuối đối chiếu với LiteLLM
    PRIMARY KEY (agent_id, period_start),
    CHECK (budget_usd IS NOT NULL OR budget_tokens IS NOT NULL)
);

CREATE TABLE ref_fx (   -- giữ nguyên từ Phần I
    day         DATE PRIMARY KEY,
    vnd_per_usd NUMERIC(12,2) NOT NULL,
    source      TEXT NOT NULL
);
```

### 5.4. Sơ đồ

```
   ai HỎI                                      ai TRẢ TIỀN
   ┌──────────────┐                        ┌──────────────────┐
   │  dim_agent   │                        │  dim_provider    │ 3
   └──────┬───────┘                        └────────┬─────────┘
          │                                          │
   ┌──────▼──────────┐   ┌───────────┐    ┌─────────▼─────────┐
   │ dim_virtual_key │   │ dim_model │◀───│  dim_deployment   │
   └──────┬──────────┘   └─────┬─────┘    │  credential_ref   │
          │                    │          │  rpm/tpm_limit    │
   ┌──────▼──────┐             │          └─────────┬─────────┘
   │   account   │             │                    │
   │  + dim_unit │             │                    │
   └──────┬──────┘             │                    │
          │                    │                    │
   ┌──────▼────────────────────▼──┐                 │
   │       fact_request           │  1 request      │
   │   outcome, attempts, latency │                 │
   └──────┬───────────────────────┘                 │
          │ 1 : N   (N = 0 khi cache hit)           │
   ┌──────▼───────────────────────────────────────▼─┐
   │              fact_attempt                       │
   │  deployment_id ← quota của AI thật sự bị trừ    │
   └──────┬──────────────────────────────────────────┘
          │  cuộn theo ngày
   ┌──────▼───────────┐        ┌──────────────────────┐
   │ fact_usage_daily │◀─ đối ─│  fact_invoice_daily  │
   │  data_era        │  chiếu │  theo credential_ref │
   └──────────────────┘        └──────────────────────┘
```

---

## 6. Bốn bài học từ Phần I phải mang sang

Đây là phần dễ bị bỏ qua nhất khi làm lại từ đầu — và cũng là phần đã trả giá để có.

### 6.1. Bài toán danh tính **DI CHUYỂN**, không biến mất

`account` đơn giản hẳn: Gateway nhận thẳng username + phòng ban trong request (§8.1),
nên không còn phải hoà giải hai cây tổ chức. Bỏ được `unit_conflict`, `unit_agent_id`,
`kind='whole_agent'`, và cả bảng `dim_user`.

**Nhưng câu hỏi cũ chỉ đổi chỗ**: từ *"hai app ghi khoá khác nhau"* thành *"8 agent có
gửi username theo cùng một quy ước không?"*. Nếu agent A gửi `LongNT` còn agent B gửi
`longnt@rangdong.com.vn` thì ta có lại đúng bệnh cũ, chỉ muộn hơn.

→ **Giữ `username` đã `LOWER(TRIM())` và giữ `account_id` làm khoá số.** Đây là lý do
`account` vẫn còn trong đề xuất chứ không bị thay bằng cột chuỗi trong `fact_request`.

### 6.2. Lịch sử cũ **không dựng lại được**

Cửa sổ lưu giữ của Google trượt rất nhanh: đo 06/08 thấy 196 ngày, đo 13/08 còn 112
ngày. Dữ liệu monitoring tháng 1–4/2026 **giờ chỉ còn trên đĩa máy cục bộ**, xoá là
mất vĩnh viễn (cảnh báo trong `scripts/rebuild_db.py`).

→ `fact_usage_daily` phải chứa **cả hai kỷ nguyên**, và phải nói rõ dòng nào thuộc kỷ
nguyên nào. Cột `data_era` đóng đúng vai trò mà `token_source` đang đóng ở Phần I: một
con số của tháng 3 (cào về, ước tính) trông y hệt con số của tháng 10 (Gateway ghi).

### 6.3. Ngân sách ở HAI chỗ thì sớm muộn lệch nhau

LiteLLM chặn được ngân sách ngay ở key (báo cáo §2.3). Nếu `ref_budget` của ta cũng
giữ một bản thì có **hai nguồn cho một con số** — đúng cái bệnh mà `db/gen_catalog.py`
đã ghi chú: *"hai nguồn cho một con số thì sớm muộn lệch nhau mà không gì báo."*

→ `ref_budget` là **bản sao chỉ-đọc**, và cột `synced_at` bắt buộc phải có để biết bản
sao đã cũ bao lâu. Nơi thực thi là LiteLLM, không phải database này.

### 6.4. Con số ước tính phải **tự khai** là ước tính

Đừng tưởng Gateway làm tiền hết ước tính: LiteLLM tính cost bằng **bảng giá nội bộ của
nó**, không phải hoá đơn thật. Sai lệch vẫn còn, chỉ giảm từ ba nguồn xuống hai.

→ Cột `cost_basis` giữ đúng tinh thần của `token_estimated` ở Phần I.

---

## 7. Bảng đối chiếu: Phần I → Phần II

| Phần I (đang chạy) | Phần II (đề xuất) | |
|---|---|---|
| `dim_agent` | `dim_agent` | ✂️ bỏ `gcp_project_id`, `has_org_tree`, `has_google_source` |
| — | `dim_provider` | ➕ mới |
| — | `dim_deployment` | ➕ mới — nơi ở mới của `gcp_project_id` |
| — | `dim_virtual_key` | ➕ mới |
| `dim_model` | `dim_model` | ✏️ `provider` chuỗi → `provider_id` khoá ngoại |
| `dim_model_alias` | — | ❌ bỏ |
| `dim_metric_alias` | — | ❌ bỏ |
| `dim_function` | — | ❌ bỏ (8 dòng, `is_user_facing` chưa từng có giá trị) |
| `dim_unit` | `dim_unit` | ✅ giữ nguyên |
| `dim_user` | — | ❌ bỏ — không còn hai cây tổ chức để hoà giải |
| `account` | `account` | ✂️ bỏ `kind`, `unit_conflict`, `unit_agent_id`, `role` |
| `fact_call` | `fact_request` | 🔀 gộp |
| `fact_app_daily` | `fact_request` | 🔀 gộp |
| — | `fact_attempt` | ➕ mới — độ mịn thứ hai |
| `fact_monitoring` | `fact_monitoring` | ✅ **GIỮ, đóng băng** (chốt 20/08 — xem 8a). Bản trước ghi "❌ bỏ", trái với chính mục 6.2 |
| `fact_perf_daily` | `fact_attempt` | 🔀 `error_class` + cuộn ra `fact_usage_daily` |
| `fact_latency_daily` | `fact_request.latency_ms` | 🔀 đo trực tiếp, không còn gộp histogram |
| `fact_billing_daily` | `fact_invoice_daily` | ✏️ khoá đổi sang `credential_ref` |
| `fact_usage_daily` | `fact_usage_daily` | ✏️ `source` → `data_era`, thêm `unit_id`/`provider_id` |
| `usage_resolved` | — | ❌ bỏ |
| `usage_by_account` | view trên `fact_usage_daily` | ✏️ không còn giới hạn ở nguồn `app` |
| `monitoring_ai` | — | ❌ bỏ |
| `ref_price` | `ref_price` | ✏️ thêm `provider_id`, tách giá cache đọc/ghi |
| `ref_budget` | `ref_budget` | ✏️ thêm `key_id`, `synced_at` |
| `ref_fx` | `ref_fx` | ✅ giữ nguyên |

**18 bảng + 3 view → 13 bảng.**

---

## 8. ⚠️ Ba điểm CÒN TREO — chưa quyết

Ba câu này đổi được hình dạng schema. Bản vẽ trên đã tạm chọn một hướng để có cái mà
bàn, **giả định được ghi rõ dưới đây** — không phải đã chốt.

| # | Câu hỏi | Giả định tạm dùng ở trên | Nếu chọn khác thì đổi gì |
|---|---|---|---|
| 1 | ~~**Lịch sử cũ đi đâu?**~~ | ✅ **ĐÃ CHỐT 20/08/2026** — xem mục 8a ngay dưới bảng | |
| 2 | **Có ghi `fact_attempt` không?** Nó sẽ là bảng lớn nhất, và chỉ đáng nếu thật sự cần trả lời *"bao nhiêu tiền cháy vì retry"* và *"deployment nào hay dính 429"* | Có ghi | Không ghi thì gộp vào `fact_request` và **mất hẳn** khả năng trả lời hai câu đó |
| 3 | **Ngân sách do ai chặn?** | LiteLLM chặn, `ref_budget` chỉ là bản sao | Nếu ta tự chặn thì `ref_budget` thành bảng thực thi, cần thêm lịch sử thay đổi và nhật ký chặn |

### 8a. ✅ Câu 1 đã chốt — 20/08/2026

Câu này hoá ra là **hai câu**, và người dùng trả lời cả hai:

**1a. MỘT database, phân biệt bằng `data_era`.**
Dòng cũ mang `'scrape'`, dòng Gateway mang `'gateway'`. Không đóng băng, không dựng
database thứ hai.

*Lý do:* dashboard đọc hai database là chi phí trả **mãi mãi** cho một lần tiện lúc
thiết kế. Một cột rẻ hơn nhiều.

**1b. GIỮ `fact_monitoring` — bảng này KHÔNG bỏ.**
Đóng băng nó: sau ngày Gateway chạy thì không nạp thêm dòng nào, nhưng cũng không xoá.

*Lý do:* mục 6.2 nói *"lịch sử cũ không dựng lại được"*, mà mục 7 lại xếp
`fact_monitoring` vào nhóm ❌ bỏ — **hai câu đó không thể cùng đúng**. Cửa sổ lưu giữ của
Google trượt rất nhanh (đo 06/08: 196 ngày; đo 13/08: 112 ngày), nên **583.917 dòng** này
giờ chỉ còn trên đĩa máy cục bộ. Bảng cuộn `fact_usage_daily` không thay thế được, vì nó
không giữ ba thứ:

| Mất nếu bỏ `fact_monitoring` | Hậu quả |
|---|---|
| `thinking_enabled` | Nguồn **duy nhất** của cột "think" trên dashboard |
| `output_modality` | Không còn phân loại text / image / audio |
| Chi tiết từng phút, histogram độ trễ | Không dựng lại được phân vị |

### 8b. ⚠️ Việc kéo theo mà câu 1 vừa tạo ra

Hai kỷ nguyên **khác hình dạng**, không chỉ khác nhãn:

```
   'scrape'    (ngay, agent, model, account, nguon)
               KHONG co: provider, retry, do tre tung request, virtual_key
   'gateway'   tung request, co du
```

Nên dòng cũ để **NULL** ở các cột mới. Truy vấn nào dùng cột mới sẽ **âm thầm bỏ hết dòng
cũ** — biểu đồ vẫn vẽ ra, chỉ là mất 8 tháng lịch sử mà không báo gì. Mỗi truy vấn phải
quyết tường minh: lọc theo kỳ nguyên, hay chấp nhận NULL. Đây là chỗ tốn công nhất của
phương án "giữ chung", không phải cột `data_era`.

---

## 9. Một chi tiết nhỏ nhưng sẽ cắn

Project ID trong tài liệu triển khai §1.2 **không khớp** database ở 2/8 dòng:

| Tài liệu §1.2 | Database (Phần I) | |
|---|---|---|
| `tla-rally` | `tla-ralli` | ❌ lệch |
| `tools-quiz` | `tools-quizz` | ❌ lệch |
| 6 dòng còn lại | | ✅ khớp |

Nếu `config.yaml` của Gateway lấy theo cách viết trong tài liệu thì hai agent đó sẽ
không nối được với dữ liệu cũ, và **không có lỗi nào báo ra**. Chốt một cách viết
trước khi viết config.
