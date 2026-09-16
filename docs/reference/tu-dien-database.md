# Từ điển database `token_ledger_v2`

> **File này có HAI PHẦN. Đừng lẫn chúng với nhau.**
>
> | | Nội dung | Trạng thái |
> |---|---|---|
> | **PHẦN I** | 23 bảng + 5 view đang chạy — 747.714 dòng | ✅ **CÓ THẬT.** Mở pgAdmin ra là thấy |
> | **PHẦN II** | Schema đề xuất cho kiến trúc API Gateway | 🟡 **PHẦN LỚN CHƯA TỒN TẠI.** Bản vẽ để bàn — xem đầu Phần II để biết mảnh nào đã thành thật |
>
> Viết truy vấn thì đọc Phần I. Chỉ những gì có ở Phần I mới có trong database.

---

# ✅ PHẦN I — SCHEMA HIỆN TẠI

> Tra cứu từng bảng, từng cột. Số liệu đọc trực tiếp từ PostgreSQL **ngày 14/09/2026**,
> ngay sau lần dựng lại từ `data/` cùng ngày. Schema ở migration `012_nhip_tim_lam_moi`.
> Kết nối: `postgresql://token:***@127.0.0.1:5432/token_ledger_v2` (PostgreSQL 17, docker-compose).
>
> **23 bảng + 5 view — 747.714 dòng** (tổng của 23 bảng, không tính view). **38 khoá ngoại.**
>
> Database cũ `token_ledger` **đã bị xoá ngày 14/09/2026**, sau khi so mọi bảng với v2
> (xem `openspec/specs/schema-migrations/spec.md`). Bản trước của file này đo trên database đó
> ngày 19/08/2026; vài con số lịch sử bên dưới vẫn giữ và **được ghi rõ ngày đo**.
>
> Muốn hiểu *vì sao* database có hình dạng này thì đọc `mo-ta-database.md`.
> Muốn biết dữ liệu *đến đây bằng đường nào* thì đọc `toan-trinh-du-lieu.md`.
> Baseline bất biến kèm ghi chú thiết kế nằm ở `db/migrations/sql/001_baseline.sql`.

---

## Tiền tố tên bảng

| Tiền tố | Nghĩa | Dùng thế nào | Các bảng |
|---|---|---|---|
| `dim_` | **dimension** — thực thể mô tả: *ai / cái gì* | Ít dòng, ít đổi. Chỉ để JOIN vào. **Không bao giờ cộng.** | `dim_agent` `dim_unit` `dim_user` `dim_model` `dim_model_alias` `dim_function` `dim_metric_alias` |
| `fact_` | **fact** — số đo: *chuyện đã xảy ra* | Nhiều dòng. Cộng và nhóm thoải mái — **trừ** `fact_provider_daily`, bảng chỉ để đối chiếu. | `fact_call` `fact_app_daily` `fact_billing_daily` `fact_monitoring` `fact_usage_daily` `fact_usage_hourly` `fact_perf_daily` `fact_latency_daily` `fact_provider_daily` |
| `ref_` | **reference** — quy ước do *người* quyết định, hoặc sổ theo dõi của đường nạp | Bảng giá, tỷ giá, ngân sách, năng lực của nguồn, nhịp tim. Không cộng vào số liệu. | `ref_price` `ref_fx` `ref_budget` `ref_source` `ref_load_run` |
| *(không tiền tố)* | `account` — bảng danh tính hợp nhất | Nằm giữa `dim_` và trục chính. Là khoá CHUNG cho mọi nguồn. | `account` |
| *(không tiền tố)* | `alembic_version` — bảng của công cụ migration | Không phải dữ liệu. Đừng sửa tay. | `alembic_version` |

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
| 8 | `data_to` | `date` | ngày cuối có dữ liệu | `NULL` = **còn chạy**. Chỉ 2/8 có giá trị | `2026-08-26` (invoice), `2026-08-21` (quizzer) |
| 9 | `is_running` | `boolean` | còn hoạt động không | `true` (6), `false` (2 — invoice và tools-quizzer đã dừng) | `true` |
| 10 | `has_google_source` | `boolean` | có nối Google Billing/Monitoring không | **7/8 = `true`.** Ralli `false`: project `tla-ralli` CÓ tồn tại nhưng CHƯA nối billing. Cột này tồn tại để giao diện biết lúc nào phải hiện `-` thay vì `0%` | `false` (chỉ Ralli) |

**Trọn vẹn 8 dòng:**

| id | code | name | gcp_project_id | org_tree | created | from | to | running | google |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `contact-center` | Chatbot Contact Center | `pro-tuner-454203-v3` | ✗ | 2025-03-19 | 2026-01-13 | — | ✓ | ✓ |
| 2 | `sale-agent` | Sale Agent | `tranquil-post-471401-c1` | ✗ | 2025-09-07 | 2026-01-01 | — | ✓ | ✓ |
| 3 | `invoice` | Multi modal AI Invoice | `multimodal-invoice` | ✗ | 2025-09-15 | 2026-01-22 | 2026-08-26 | ✗ | ✓ |
| 4 | `tools-quizzer` | Tools Quizzer | `tools-quizz` | ✗ | 2026-04-10 | 2026-06-17 | 2026-08-21 | ✗ | ✓ |
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
| 7 | `is_technical` | `boolean` | dòng kỹ thuật hay phòng ban thật | **`true` ở 8/130.** Gồm 6 dòng *"Đơn vị sử dụng &lt;agent&gt;"* (`__technical_1__` … `__technical_7__`, trừ 5) và 2 dòng *"Chưa quy được"* (`__unattributed_5__`, `__unattributed_8__`). Không có cột này thì `COUNT(*)` đếm cả dòng kỹ thuật thành phòng ban thật | `false` (122), `true` (8) |
| 8 | `canonical_unit_id` | `text` | **cùng một phòng ban ngoài đời** nằm ở dòng nào của cây kia | Chỉ 4/130 có. Cả 4 là phòng ban của cây TLA HĐ trỏ sang dòng tương ứng ở cây Ralli: `TT C4LED`, `Phòng BH1`, `Phòng BH2`, `Phòng BH3`. Trước 20/08 phép gộp này nằm trong `UNIT_ALIASES` gõ tay ở `web/js/app.js` | `69ee5b13be38bdbf5a8de6a3` |
| 9 | `is_report_aggregate` | `boolean` | **cấp gom thuần tuý**, báo cáo bắt đầu từ bên dưới nó | `true` ở đúng 2 dòng: `Toàn công ty` và `Tổng công ty Rạng Đông`. Mọi phòng ban đều nằm dưới chúng, nên để làm cấp 1 của bảng thì tốn hai lần bung mà không phân biệt được gì. Gốc báo cáo = đơn vị không phải cấp gom, mà cha của nó hoặc không có, hoặc là cấp gom | `false` (128), `true` (2) |

**Dữ liệu mẫu:**

| unit_id | agent | name | parent | level | path | technical |
|---|---|---|---|---|---|---|
| `__unattributed_5__` | 5 | Chưa quy được | — | 0 | `Chưa quy được` | ✓ |
| `__unattributed_8__` | 8 | Chưa quy được | — | 0 | `Chưa quy được` | ✓ |
| `69ee5b13be38bdbf5a8de666` | 8 | Toàn công ty | — | 1 | `Toàn công ty` | ✗ |
| `ceadd40f-1a4f-…` | 5 | TT C4LED | — | 1 | `TT C4LED` | ✗ |

---

## `account` — **Tài khoản** hợp nhất. Một dòng = một tài khoản, KHÔNG phải một con người

954 dòng · Khoá chính `account_id` · `username` là UNIQUE

**Vì sao bảng này tồn tại:** trước đây mỗi nguồn ghi *"ai dùng"* theo kiểu riêng — Ralli ghi ObjectId của Ralli, TLA HĐ ghi id của TLA HĐ, còn Google thì **không ghi người nào cả** (hoá đơn chỉ biết *"cả project này tiêu ngần này"*). Ba quyển sổ, không mã chung. Từ đây mọi nơi đều trỏ về `account_id`.

**Không dùng tên đăng nhập làm khoá ngoại** — tên đăng nhập là chuỗi, đã thấy ba dạng cho cùng một tài khoản (hoa/thường, khoảng trắng thừa, Ralli đôi khi ghi username vào chỗ ObjectId). Cột `username` ở đây đã `LOWER(TRIM())`.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `account_id` | `integer` | mã tài khoản chung | 1–954. Khoá dùng cho MỌI phép tính | `1`, `505`, `950` |
| 2 | `username` | `text` | tên đăng nhập | Đã hạ chữ thường, cắt khoảng trắng | `admin`, `bh1.longnt`, `svc.crm-feedback` |
| 3 | `full_name` | `text` | họ tên | 947/954 có | `Nguyễn Văn Quí`, `Quản trị viên` |
| 4 | `email` | `text` | thư điện tử | 928/954 có | `ct.giangcl@rangdong.com.vn` |
| 5 | `kind` | `text` | **loại tài khoản** | `real` (938) người thật · `service_account` (6) tài khoản dịch vụ của 6 agent một-người-dùng (`svc.contact-center`, `svc.crm-feedback`…): biết chính xác ai gọi, chỉ là "ai" đó không phải một con người · `whole_agent` (2) cả agent, không quy được về ai (ví dụ `__whole_agent_5__`) · `unattributed` (8) có lượt gọi nhưng bản ghi không kèm người | `real` |
| 6 | `unit_id` | `text` | đơn vị của tài khoản | **Đơn vị nằm ở đây, không ở `dim_user`.** Một tài khoản = một đơn vị, đã chọn dứt điểm | `69ee5b13be38bdbf5a8de6c5` |
| 7 | `is_shared` | `integer` | tài khoản dùng chung? | `0`/`1`. `1` = `admin`, tài khoản thử… Vẫn tính đủ token và tiền, nhưng **phải loại khỏi tỷ lệ áp dụng** — `admin` một mình tạo 46,4% lưu lượng TLA HĐ | `0`, `1` |
| 8 | `role` | `text` | vai trò cao nhất trong các app | `MEMBER` (801) · `DT` (63) · `UNIT_LEAD` (45) · `COMPANY_ADMIN` (15) · `ADMIN` (4) · `PKH` (1) · `ASSISTANT` (1) · `NULL` (24) | `MEMBER` |
| 9 | `is_enabled` | `boolean` | tài khoản còn bật? | 892 `true`, 62 `NULL` (`NULL` = app không khai, khác với "bị tắt") | `true` |
| 10 | `created_at` | `timestamp` | ngày được cấp tài khoản | 892/954 có. Từ 02/04/2026 đến 18/08/2026 | `2026-04-26 17:59:49` |
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

965 dòng · Khoá chính `(agent_id, user_id)`

Khác `account` thế nào: **nhiều dòng `dim_user` có thể trỏ vào CÙNG một `account`** — đo 19/08/2026: 13 dòng do Ralli ghi hai dạng khoá, 5 dòng do cùng tên đăng nhập tồn tại ở cả hai app, 1 dòng do hai tài khoản dùng chung email. Đo 14/09: 965 dòng trỏ vào 944 tài khoản khác nhau. Bảng này giữ nguyên hiện trạng từng app; `account` mới là bản đã gộp.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `user_id` | `text` | khoá GỐC của app | ObjectId của Ralli, hoặc id của TLA HĐ | `69ee5296c7fb84b9e507c2f9` |
| 2 | `agent_id` | `integer` | dòng này do app nào khai | 1–8 | `8` |
| 3 | `account_id` | `integer` | trỏ về tài khoản đã hợp nhất | 965/965 đều đã quy được | `472`, `516` |
| 4 | `username` | `text` | tên đăng nhập app khai | Giữ nguyên dạng gốc, chưa chuẩn hoá | `tg.xemdon`, `NCTT.TungTX` |
| 5 | `full_name` | `text` | họ tên | 936/965 có | `Trần Vinh Quy` |
| 6 | `email` | `text` | thư điện tử | 932/965 có | `crm.trangnt@rangdong.com.vn` |
| 7 | `unit_id` | `text` | đơn vị **theo cây của app này** | Đây là chỗ hai app bất đồng nhau | `69ee5b13be38bdbf5a8de6c6` |
| 8 | `is_enabled` | `boolean` | còn bật không | 892 `true`, 73 `NULL` | `true` |
| 9 | `created_at` | `timestamp` | ngày cấp | 892/965 có | `2026-04-02 01:04:35` |
| 10 | `is_technical` | `boolean` | dòng kỹ thuật? | `true` ở 6 dòng — sinh ra cho 6 agent một-người-dùng | `false` (959), `true` (6) |
| 11 | `found_in` | `text` | **tìm thấy ở đâu** | `directory` (936) có trong danh bạ · `log` (23) CHỈ thấy trong nhật ký, không có trong danh bạ (`system`, `admin`, `guest`) · `technical` (6) dòng tự sinh | `directory` |
| 12 | `role` | `text` | vai trò do CHÍNH APP khai | `MEMBER` (801) · `DT` (64) · `UNIT_LEAD` (48) · `COMPANY_ADMIN` (16) · `ADMIN` (4) · `ASSISTANT` · `PKH` · `NULL` (30) | `COMPANY_ADMIN` |

---

## `dim_model` — Danh mục **model** AI

12 dòng · Khoá chính `model_id` · `name` là UNIQUE

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `model_id` | `integer` | mã model | 1–12 | `4` |
| 2 | `name` | `text` | tên **CHUẨN**, dạng gạch ngang | Tên ta chọn làm gốc để mọi nguồn quy về | `gemini-2.5-pro` |
| 3 | `family` | `text` | dòng model | `gemini-3` (6) · `gemini-2.5` (3) · `embedding` (2) · `gemini-2.0` (1) | `gemini-2.5` |
| 4 | `provider` | `text` | nhà cung cấp | Hiện toàn bộ 12/12 là `Google` | `Google` |

**Trọn vẹn 12 dòng — kèm giá từ `ref_price` (USD / 1 triệu token):**

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
| 11 | `gemini-3.6-flash` | gemini-3 | 0,75 | 3,75 | 0,075 |
| 12 | `gemini-3.5-flash-lite` | gemini-3 | 0,30 | 2,50 | 0,03 |

*(Hai model embedding không có giá đầu ra vì phép nhúng không sinh token ra. Model 11 và 12 đến cùng Gateway: hôm nay chỉ `fact_call` nguồn `gateway` và `fact_provider_daily` dùng chúng.)*

---

## `dim_model_alias` — Bảng **dịch tên model**: mỗi nguồn gọi một model theo một kiểu

49 dòng · Khoá chính `(source, raw_name)`

Không có bảng này thì phải đoán bằng chuỗi, mà `gemini-embedding-001` với `gemini-embedding-1.0` thì không quy tắc chuẩn hoá nào nói được với nhau.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `source` | `text` | nguồn gọi tên | `billing_sku` (31) mã SKU hoá đơn · `monitoring` (11) tên trong Cloud Monitoring · `app` (4) tên app tự ghi · `gateway` (3) tên upstream mà LiteLLM ghi | `billing_sku` |
| 2 | `raw_name` | `text` | tên **thô** ở nguồn đó | SKU là mã 3 cụm; monitoring/app là tên chữ; gateway có tiền tố `gemini/` | `07D6-73CA-C859`, `gemini/gemini-2.5-flash` |
| 3 | `model_id` | `integer` | quy về model chuẩn nào | Trỏ sang `dim_model`, 1–12 | `5`, `1` |

**Dữ liệu mẫu — mỗi nguồn một dòng:**

| source | raw_name | → model_id |
|---|---|---|
| `app` | `gemini-2.0-flash` | 1 |
| `monitoring` | `gemini-2.0-flash` | 1 |
| `billing_sku` | `07D6-73CA-C859` | 5 |
| `gateway` | `gemini/gemini-3.5-flash-lite` | 12 |

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

48 dòng · Khoá chính `(source, raw_name)`

Cùng khuôn với `dim_model_alias`, sinh ra để chữa cùng một bệnh. Trước khi có bảng này, phân loại là **đoán tên** ở hai chỗ khác nhau (regex trên `sku_name`, và `LIKE '%token_count'`); Google đổi cách đặt tên thì cả hai trả về **rỗng** chứ không báo lỗi. Đổi thành bảng tra cứu thì tên lạ làm khâu nạp **dừng hẳn** — hỏng ồn ào, không hỏng im lặng.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `source` | `text` | nguồn của tên | `billing_sku` (31) · `monitoring` (17) | `monitoring` |
| 2 | `raw_name` | `text` | mã chính chủ của Google | SKU id, hoặc `metric_type` đầy đủ | `serviceruntime.googleapis.com/api/request_latencies` |
| 3 | `label` | `text` | mô tả chính chủ của Google | 48/48 có. Đây là chỗ regex chạy trên (thay vì trên tên tự chế) | `Distribution of latencies in seconds for non-streaming requests.` |
| 4 | `measures` | `text` | **phép đo này đo cái gì** | `token` (35) · `quota_limit` (7) · `calls` (5) · `latency` (1) | `token` |
| 5 | `kind` | `text` | loại token | `input` (18) · `output` (10) · `cached` (7) · `NULL` (13, khi không phải token) | `cached` |
| 6 | `metric_kind` | `text` | kiểu công tơ (Google khai) | `DELTA` (10) công tơ cộng dồn · `GAUGE` (7) hạn mức. Chỉ nguồn monitoring có | `DELTA` |
| 7 | `value_type` | `text` | kiểu giá trị (Google khai) | `INT64` (16) · `DISTRIBUTION` (1, chính là độ trễ) | `INT64` |

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

## `fact_call` — **Từng lượt gọi API**, mức mịn nhất. Hai nguồn: nhật ký Ralli và Gateway

9.453 dòng · Khoá chính `call_id` · Cột `source` tách hai nguồn:

```
   source = 'app'       8.972 dong   luon agent 8 (Ralli)       14/03 -> 12/09/2026
   source = 'gateway'     481 dong   agent 6 (377) · agent 7 (104)   31/08 -> 12/09/2026
                                     398 thanh cong · 83 hong
```

Cột 1–15 có từ baseline. Cột 16–25 thêm ở migration 004, 006, 007, 008 cho nguồn Gateway — **nguồn `app` để `NULL` cả mười cột**, vì nhật ký Ralli không ghi những thứ đó. Gán giá trị cho chúng là bịa.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `call_id` | `text` | mã lượt gọi | `app`: ObjectId từ nhật ký Ralli · `gateway`: mã do LiteLLM ghi | `69b4ec3d1c64451042f7f58f`, `-0Geasv7DZi6vr0PnoaskAQ` |
| 2 | `agent_id` | `integer` | agent nào | `8` (8.972) · `6` (377) · `7` (104) | `8` |
| 3 | `ts_raw` | `timestamp` | **thời điểm chép nguyên**, chưa quy đổi | Giờ UTC. 14/03 → 12/09/2026 | `2026-03-14 05:03:57.488` |
| 4 | `tz_confirmed` | `boolean` | đã chứng minh múi giờ chưa | `true` cho cả 9.453 dòng — đã chứng minh là UTC | `true` |
| 5 | `ts_local` | `timestamp` | **giờ Việt Nam** (= `ts_raw` + 7h) | Đây là cột dùng để tính | `2026-03-14 12:03:57.488` |
| 6 | `user_id` | `text` | khoá **GỐC** của nguồn, giữ để truy vết | 8.339/9.453 có (`app` 8.209/8.972). `app` trộn hai dạng: username và ObjectId. `gateway` ghi tên tài khoản dịch vụ | `system`, `6a60535b2fb111497fa554c3`, `svc.crm-feedback` |
| 7 | `account_id` | `integer` | khoá **CHUNG**, dùng để tính toán | 9.453/9.453 đã quy được | `505` |
| 8 | `unit_id` | `text` | đơn vị | **8.327/8.972 dòng `app` rơi vào `__unattributed_8__`** — phần lớn lượt gọi là của `system`. Dòng `gateway` rơi vào `__technical_6__` / `__technical_7__` | `__unattributed_8__` |
| 9 | `model_id` | `integer` | model dùng | 9.447/9.453 có. `app` chỉ 1–3 · `gateway` 2, 11, 12. **6 dòng `NULL` đều là lượt Gateway hỏng** trước khi Router chốt tuyến — xem `raw_model` | `3`, `12` |
| 10 | `function_code` | `text` | chức năng nào gọi | Chỉ `app`: `gemini_generate_text` (4.637) · `gemini_structured_call` (3.939) · `gemini_chat_json_messages` (336) · `assistant_extract_image_text` (39) · … `NULL` ở 481 dòng `gateway` | `gemini_generate_text` |
| 11 | `prompt_tokens` | `bigint` | token đầu vào | 0 → 120.614 (`app` từ 20) | `376` |
| 12 | `completion_tokens` | `bigint` | token đầu ra | 0 → 65.536 | `2305` |
| 13 | `total_tokens` | `bigint` | **cột chuẩn** — tổng token | 0 → 155.511. `app` từ 127; số 0 chỉ có ở `gateway`. **KHÔNG tự cộng hai cột trên** (quy tắc 6) | `2681` |
| 14 | `cached_tokens` | `bigint` | token đọc từ bộ nhớ đệm | Chỉ 2.102/9.453 có. **`NULL` ở 6.871 dòng cũ nghĩa là "không biết", KHÔNG phải 0** (quy tắc 5) | `NULL`, `0`, `8625` |
| 15 | `record_format` | `smallint` | định dạng bản ghi | `1` (6.871) · `3` (1.559) · `2` (542) · `NULL` (481, `gateway`). Ralli đổi cấu trúc log 3 lần — đây là dấu vết | `1` |
| 16 | `source` | `text` | **nguồn của dòng** (migration 004) | `app` (8.972) · `gateway` (481). Khoá ngoại tới `ref_source`. `DEFAULT 'app'` là đúng nghĩa: trước 31/08 mọi dòng đều của app | `gateway` |
| 17 | `cost_usd` | `numeric` | tiền USD (migration 004) | Chỉ `gateway`, 398 dòng = đúng số lượt thành công. **Số ƯỚC TÍNH** do LiteLLM tự nhân từ bảng giá của nó, không phải hoá đơn. `NULL` ở `app` = nguồn này không có tiền | `0.0000031` → `0.0306313` |
| 18 | `duration_ms` | `integer` | độ trễ, mili giây (migration 006) | 398 dòng, 254 → 102.366 ms. Gateway ghi `0` cho MỌI lượt hỏng, nên `0` không phải một phép đo — bộ nạp quy về `NULL`. Nạp `0` vào là kéo tụt mọi phân vị | `1002` |
| 19 | `outcome` | `text` | kết cục (migration 006) | `success` (398) · `failure` (83) · `NULL` (8.972 dòng `app` — **không biết, KHÔNG phải thành công**). **Mọi phép tổng hợp lưu lượng và chi phí PHẢI lọc cột này** | `success` |
| 20 | `error_code` | `text` | mã lỗi khi hỏng (migration 006) | 77 dòng: `429` (74) · `500` (2) · `401` (1). 6 lượt hỏng còn lại không có mã (bộ nạp quy chuỗi rỗng về `NULL`). `TEXT` vì không bảo đảm là số | `429` |
| 21 | `raw_model` | `text` | tên model **đúng như Gateway nhận** (migration 007) | 481 dòng `gateway`: `gemini/gemini-3.5-flash-lite` (372) · `gemini/gemini-2.5-flash` (100) · `gemini/gemini-3.6-flash` (3) · và 6 dòng mang **bí danh** (`gemini-flash-lite`, `gemini-flash`…) — chính là 6 dòng `model_id NULL`. Ở dòng đó cột này là bằng chứng duy nhất để biết nên khai thêm tuyến nào | `gemini/gemini-3.5-flash-lite` |
| 22 | `virtual_key_id` | `text` | khoá đã gọi (migration 007) | 481 dòng. **Không chuẩn hoá**: `litellm_proxy_master_key` (303 — khoá tổng) và 5 khoá ảo dạng băm (178). Số dòng đi bằng khoá tổng phải giảm về 0 khi mỗi agent có khoá riêng | `litellm_proxy_master_key` |
| 23 | `cache_hit` | `boolean` | lượt được trả từ bộ nhớ đệm? (migration 007) | Chỉ 83 dòng có giá trị, đều `false`, đều là lượt hỏng. 398 lượt thành công đều `NULL` = không có thông tin. **Bẫy: `NOT cache_hit` vứt sạch dòng `NULL` — lọc bằng `cache_hit IS NOT TRUE`** | `NULL` |
| 24 | `output_modality` | `text` | **nhãn** kiểu phản hồi, không phải số token (migration 008) | `text` (391) · `NULL`. Cùng quy ước với `fact_monitoring.output_modality` | `text` |
| 25 | `thinking_enabled` | `boolean` | lượt có sinh token suy luận? (migration 008) | `true` (16) · `NULL`. **`NULL` = không có thông tin, KHÔNG phải "không bật"**. Khác kiểu với cột cùng tên ở `fact_monitoring` (ở đó là `TEXT`) — so hai bảng phải dịch kiểu tường minh | `true` |

---

## `fact_app_daily` — Mức **ngày × người × model** do app tự tổng hợp (TLA Hợp Đồng)

78 dòng · Khoá chính `row_id` · Toàn bộ `agent_id = 5`

**Vì sao cần bảng riêng:** Ralli phơi từng lượt gọi nên vào được `fact_call`. TLA Hợp Đồng **chỉ phơi API đã tổng hợp sẵn**, mức mịn nhất lấy được là (ngày × người × model). Không có bảng này thì hoặc phải bịa ra lượt gọi giả, hoặc phải bỏ hẳn chiều người dùng của TLA HĐ — trước 14/08 là phương án thứ hai, và hậu quả là biểu đồ tỷ lệ áp dụng báo `0/39` trong khi sự thật là *"có người dùng, không nhìn thấy ai"*.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `row_id` | `integer` | số thứ tự | 1–78. Gán tường minh vì `model_id` được phép `NULL`, mà PostgreSQL cấm `NULL` trong khoá chính | `1` |
| 2 | `day` | `date` | ngày (giờ VN) | 14/03 → 04/09/2026 | `2026-03-14` |
| 3 | `agent_id` | `integer` | agent | Luôn `5` (TLA HĐ) | `5` |
| 4 | `account_id` | `integer` | tài khoản | 1–691 | `1` |
| 5 | `model_id` | `integer` | model | 76/78 có. **`NULL` = app không nói model** | `2`, `4`, `NULL` |
| 6 | `raw_model` | `text` | tên model **gốc**, giữ để truy vết | `gemini-2.5-flash` (56) · `gemini-2.5-pro` (20) · `none` (1) · `NULL` (1) | `gemini-2.5-pro` |
| 7 | `calls` | `integer` | số lượt gọi trong ngày | 1 → 230 | `143` |
| 8 | `total_tokens` | `bigint` | tổng token | 0 → 8.126.973 | `3227233` |
| 9 | `prompt_tokens` | `bigint` | token vào | 0 → 6.815.690 | `2532049` |
| 10 | `completion_tokens` | `bigint` | token ra | 0 → 1.311.283 | `695184` |

---

## `fact_billing_daily` — **Hoá đơn Google.** Nguồn DUY NHẤT có TIỀN

2.833 dòng · Khoá chính `(day, project, sku_id)` · 7/8 agent (Ralli không có)

> **Cảnh báo múi giờ:** Google cắt ngày hoá đơn theo giờ Thái Bình Dương; ta coi luôn là giờ VN, không quy đổi. **Tổng cả kỳ vẫn tuyệt đối đúng.** Cái phải biết: **ngày CUỐI CÙNG luôn hụt**, và mỗi ngày lẫn khoảng 15 giờ của ngày kề bên. Đủ để theo xu hướng, không đủ để đối chiếu một ngày lẻ với nguồn khác.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `day` | `date` | ngày hoá đơn | 01/01 → 11/09/2026 | `2026-07-02` |
| 2 | `agent_id` | `integer` | **khoá CHUẨN** | 1–7. Thêm vào để không phải nhớ viết `JOIN … ON gcp_project_id = project` mỗi lần — quên là mất dòng mà không lỗi nào báo | `5` |
| 3 | `project` | `text` | mã project GCP, giữ để truy vết | `pro-tuner-454203-v3` (1.033) · `tranquil-post-471401-c1` (1.005) · `multimodal-invoice` (421) · … | `ai-chatbot-contract` |
| 4 | `sku_id` | `text` | mã hàng hoá của Google | Mã 3 cụm, 31 giá trị. Nối vào `dim_model_alias` và `dim_metric_alias` | `0F51-429B-C2DC` |
| 5 | `sku_name` | `text` | tên hàng hoá | Mô tả dài của Google | `Generate content output token count Gemini 2.5 Pro short output text` |
| 6 | `model_id` | `integer` | model đã quy chuẩn | 2.833/2.833 đều quy được (1–10) | `4` |
| 7 | `kind` | `text` | **loại token** | `input` (1.296) · `output` (1.016) · `cached` (521) | `output` |
| 8 | `quantity` | `bigint` | **số token** | 5 → 24.990.232 | `15215` |
| 9 | `cost_usd` | `numeric(14,6)` | **tiền thật, USD** | 0 → 25,14 USD một dòng. **Đây là con số duy nhất không phải ước tính** | `0.152150` |

> **Bẫy `cached` ở hoá đơn:** cached là SKU **RIÊNG**, nằm **NGOÀI** input. Cộng cả ba mới ra tổng. Ở nguồn `app` thì ngược lại — cached là một phần **CỦA** `prompt_tokens`, cộng vào là đếm hai lần.

---

## `fact_monitoring` — Số đo **từng phút** từ Google Cloud Monitoring. Bảng lớn nhất

726.051 dòng · **Không có khoá chính** (là bảng thô) · 7/8 agent

Nạp **đủ** mọi dòng cào về, kể cả lưu lượng Drive/Sheets/Compute, rồi **lọc ở tầng view** `monitoring_ai`. Giữ dòng rác vì chính nó là bằng chứng: quên lọc thì agent `pro-tuner` sai **45,7 lần** (đo 19/08/2026).

Nhiều lần kéo cùng một phút được gộp **trước khi nạp**, giữ số lớn hơn cho mỗi khoá — vì lần kéo sau bị cửa sổ lưu giữ cắt ở mép và báo số nhỏ hơn. Luật gộp nằm ở `docs/reference/toan-trinh-du-lieu.md`.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `ts_utc` | `timestamp` | mốc thời gian **UTC** | 22/01 → 12/09/2026, từng phút | `2026-08-17 01:59:00` |
| 2 | `ts_local` | `timestamp` | mốc thời gian **giờ VN** | = `ts_utc` + 7h | `2026-08-17 08:59:00` |
| 3 | `agent_id` | `integer` | khoá CHUẨN | 1–7 | `5` |
| 4 | `project` | `text` | mã project, giữ để truy vết | `pro-tuner-454203-v3` chiếm 621.612/726.051 | `ai-chatbot-contract` |
| 5 | `metric_nickname` | `text` | **biệt danh** do script cào tự đặt | 14 giá trị. `api_request_count` (212.598) · `api_request_latencies_p95`/`_p99` (206.206 mỗi loại) · … Tiện đọc, nhưng **không có cam kết ổn định** | `generate_content_usage_output_token_count` |
| 6 | `metric_type` | `text` | **mã CHÍNH CHỦ của Google** | 13 giá trị. Đây mới là thứ nối vào `dim_metric_alias`. Trước đây cột này bị vứt lúc nạp — tức bỏ thứ ổn định, giữ thứ tự chế | `generativelanguage.googleapis.com/generate_content_usage_output_token_count` |
| 7 | `model_id` | `integer` | model | **Chỉ 101.041/726.051 (13,9%) có.** Phép đo dạng request không mang nhãn `model`. Trong view `monitoring_ai` tỷ lệ là 60,3% | `2` |
| 8 | `response_code` | `text` | mã HTTP trả về | Chỉ 212.598 dòng có, 8 mã. `200` (211.958) · `302` (349) · `503` (105) · `400` (73) · `404` (50) · `499` (27) · `500` (23) · … | `200` |
| 9 | `service` | `text` | dịch vụ Google nào | **`drive.googleapis.com` (575.797) lấn át `generativelanguage.googleapis.com` (146.587)** — chính là lý do phải lọc | `generativelanguage.googleapis.com` |
| 10 | `method` | `text` | phương thức API | 625.010/726.051 có | `google.ai.generativelanguage.v1beta.GenerativeService.GenerateContent` |
| 11 | `credential_id` | `text` | khoá API nào gọi | Cùng phút cùng method vẫn nhiều dòng nếu nhiều API key. Dạng `oauth2:…` hoặc `apikey:…` | `apikey:536546b1-37fd-…` |
| 12 | `is_quota_limit` | `boolean` | dòng này là **hạn mức** hay số đo thật | `true` (31.930) = ALIGN_MAX, **KHÔNG được SUM**. Mọi hạn mức đều `GAUGE`, mọi công tơ đều `DELTA` | `false` |
| 13 | `thinking_enabled` | `text` | có bật chế độ suy luận không | 16.546 dòng có: `true` (12.698) · `false` (3.848). Đo 19/08/2026: đây là nguồn duy nhất cho cột "think" trên dashboard. Từ migration 008 `fact_call` cũng có cột cùng tên, khác kiểu | `true` |
| 14 | `output_modality` | `text` | dạng đầu ra | 16.546 dòng có, toàn bộ là `text` | `text` |
| 15 | `limit_name` | `text` | tên hạn mức Google áp | 84.489 dòng có, 8 loại | `GenerateContentPaidTierInputTokensPerModelPerMinute` |
| 16 | `value` | `double precision` | **giá trị đo được** | Ý nghĩa **phụ thuộc `metric_type`**: token, số lượt, giây, hay hạn mức | `145.0` |
| 17 | `unit` | `text` | đơn vị | `s` (412.412) giây · `1` (313.639) đếm | `1` |

---

## `fact_usage_daily` — **Bảng ĐỐI CHỨNG.** Bốn nguồn đặt cạnh nhau, chưa chọn

2.203 dòng · Khoá chính `(day, agent_id, model_id, account_id, source)`

> **Đọc bảng này để SO SÁNH các nguồn, KHÔNG phải để hỏi một con số.** Muốn một con số thì đọc view `usage_resolved`. Vì `source` nằm trong khoá chính nên ai hỏi bảng này cũng phải tự chọn nguồn trước — đó là việc của view, không phải của người hỏi.
>
> **Không có cột `unit_id` — và đó là cố ý.** Đơn vị là thuộc tính CỦA tài khoản, `JOIN account` là ra. Chép thêm bản sao vào đây thì hai bản có thể lệch nhau.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `day` | `date` | ngày (giờ VN) | 01/01 → 12/09/2026 | `2026-07-26` |
| 2 | `agent_id` | `integer` | agent | 1–8 (đủ cả 8) | `7` |
| 3 | `model_id` | `integer` | model | 1–12. **NOT NULL** | `2` |
| 4 | `account_id` | `integer` | tài khoản | 1–954. **NOT NULL** — dùng dòng kỹ thuật (`whole_agent`/`unattributed`) thay cho `NULL` | `950` |
| 5 | `calls` | `integer` | số lượt gọi | 1.097/2.203 có (nguồn `billing` không đếm lượt) | `NULL`, `11582` |
| 6 | `total_tokens` | `bigint` | tổng token | 2.070/2.203 có. Tới 36.207.425 | `88818` |
| 7 | `input_tokens` | `bigint` | token vào | 2.069/2.203 có | `39649` |
| 8 | `output_tokens` | `bigint` | token ra | 2.064/2.203 có | `49169` |
| 9 | `cached_tokens` | `bigint` | token đệm | 1.270/2.203 có. **`monitoring` không có phép đo cached → luôn `NULL`** | `0` |
| 10 | `cost_usd` | `numeric(14,6)` | tiền | 1.117/2.203 có = 1.106 dòng `billing` (**tiền hoá đơn**) + 11 dòng `gateway` (**tiền ước tính** của LiteLLM). `app` và `monitoring` luôn `NULL` | `0.134816` |
| 11 | `source` | `text` | **nguồn của dòng này** | `billing` (1.106) · `monitoring` (679) · `app` (407) · `gateway` (11). Khoá ngoại tới `ref_source` | `billing` |

> **`cached` không cùng nghĩa ở ba nguồn** (đã đo, không phải suy): billing coi cached là SKU riêng ngoài input; app coi cached là tập con của `prompt_tokens`; monitoring không đo cached. Vì vậy `total_tokens` **giữ nguyên theo quy ước của nguồn**, và cột `source` cho biết đang đọc quy ước nào.

---

## `fact_perf_daily` — **Số lượt gọi theo mã lỗi**, mức ngày

747 dòng · Khoá chính `(day, agent_id, method, response_code, source)`

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `day` | `date` | ngày (giờ VN) | 22/01 → 12/09/2026 | `2026-01-22` |
| 2 | `agent_id` | `integer` | agent | 1–7 | `1` |
| 3 | `method` | `text` | phương thức API | 13 giá trị, đều thuộc `generativelanguage` | `google.ai.generativelanguage.v1beta.GenerativeService.EmbedContent` |
| 4 | `response_code` | `text` | **mã HTTP** | `200` (696) · `503` (21) · `400` (14) · `404` (8) · `499` (6) · `500` (2) | `200` |
| 5 | `calls` | `integer` | số lượt | 1 → 5.790 | `51` |
| 6 | `source` | `text` | **nguồn của dòng** (migration 008, 03/09) | `monitoring` (747). **Đo 14/09: chưa có dòng `gateway` nào.** Đếm qua `serviceruntime/api/request_count`, đã lọc `service = generativelanguage` | `monitoring` |

**Cột `source` thêm 03/09/2026.** Nó nằm trong **khoá chính**, không phải cột phụ. Hai nguồn đếm **hai thứ khác nhau** dù cùng tên cột: `monitoring` đếm qua công tơ Google, `gateway` sẽ đếm từng lượt trong sổ LiteLLM. Cộng hai nguồn lại là đếm hai lần cùng một lưu lượng.

669 dòng cũ nhận `DEFAULT 'monitoring'` — **đúng nghĩa**, chúng thật sự dựng từ `fact_monitoring`.

---

## `fact_latency_daily` — **Độ trễ** ở đúng độ mịn Google cho: một số cho mỗi (ngày, agent)

454 dòng · Khoá chính `(day, agent_id, source)`

**Vì sao tách khỏi `fact_perf_daily`:** hai chỉ tiêu đo ở hai độ mịn khác nhau. Số lượt có `response_code` và `method`; độ trễ thì **không** có `response_code`, và con số đúng chỉ tồn tại ở mức (ngày, agent) — phân vị không cộng được, phải gộp histogram rồi mới đọc mốc. Lấy trung bình các p95 từng phút đã đo thử: **lệch trên 19%**.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `day` | `date` | ngày (giờ VN) | 01/05 → 12/09/2026 | `2026-05-02` |
| 2 | `agent_id` | `integer` | agent | 1–7 | `3` |
| 3 | `samples` | `integer` | số mẫu vào histogram ngày đó (`gateway`: số lượt thành công có độ trễ) | 1 → 5.791. Tổng `monitoring` 53.038 mẫu · `gateway` 398 | `15` |
| 4 | `p50_seconds` | `double precision` | **trung vị** — nửa số lượt nhanh hơn mức này | 0,034 → 39,15 giây | `1.7039` |
| 5 | `p95_seconds` | `double precision` | **phân vị 95** — 5% lượt chậm hơn mức này | 0,256 → 382,52 giây | `3.67` |
| 6 | `p95_bucket_from` | `double precision` | **cận dưới** ô histogram chứa p95 | Ô rộng gấp đôi sau mỗi bậc | `2.0972` |
| 7 | `p95_bucket_to` | `double precision` | **cận trên** ô đó | Trung vị bề rộng ô = **57% của chính giá trị p95** → dashboard phải hiện **KHOẢNG**, không phải số lẻ | `4.1943` |
| 8 | `p99_seconds` | `double precision` | phân vị 99 | 0,261 → 506,00 giây | `4.0894` |
| 9 | `enough_samples` | `boolean` | đủ mẫu để phân vị có nghĩa? | `true` (394) · **`false` (60) khi `samples < 10`** | `true` |
| 10 | `source` | `text` | **nguồn của phân vị** (migration 008, 03/09) | `monitoring` (445) · `gateway` (9) | `gateway` |

### Cột `source` và hai cách tính phân vị hoàn toàn khác nhau (03/09/2026)

`source` nằm trong **khoá chính** `(day, agent_id, source)`. Thiếu nó thì dòng Gateway đụng khoá với dòng monitoring của cùng một ngày — hoặc `INSERT` hỏng, hoặc tệ hơn, `DO UPDATE` ghi đè và mất một nguồn mà tổng vẫn "khớp".

**ĐỌC `source` CÙNG `p95_bucket_*` ĐỂ BIẾT ĐỘ TIN CẬY — hai cột đó là thước đo sai số:**

```
   source = 'monitoring'   p95 NOI SUY trong mot o histogram
                           p95_bucket_from/to CO gia tri
                           do 03/09: be rong o = 54-67% chinh gia tri p95
                           (agent 6: p95 58,206 s, o rong 31,318 s)

   source = 'gateway'      p95 tinh THANG tu tung gia tri duration_ms
                           p95_bucket_from/to = NULL  <- KHONG AP DUNG
                           khong co sai so noi suy nao
```

`NULL` ở hai cột ô nghĩa là *"không áp dụng"*, **không** phải *"chưa nạp"*. Ghi `0` vào đó là nói "sai số bằng không đo được" — sai hẳn nghĩa.

**MỖI NGUỒN MỘT DÒNG, KHÔNG GỘP TRUNG BÌNH.** Trung bình hai phân vị cho ra một con số không thuộc về phép đo nào. Muốn **một** con số duy nhất thì phải **CHỌN** một nguồn — và hôm nay chưa view nào làm việc đó.

**Chưa giải thích được, ghi lại để đừng ai kết luận vội (đo 03/09/2026):** hai nguồn lệch **31,9 lần** cho cùng agent 6 — thủ công p95 TB **58,206 s** vs gateway **1,822 s**; p50 lệch 24,9 lần (19,66 s vs 0,788 s). Ba phép đo đã loại trừ các giải thích dễ dãi: 0/38 lượt Gateway vượt 33,55 s; số lượt/ngày tương đương (45,4 vs 38); p50 cũng lệch, mà p50 ít chịu sai số ô hơn nhiều. Lúc đó chưa ngày nào hai nguồn cùng có số.

**Đo 14/09/2026: đã có 5 cặp (ngày, agent) hai nguồn cùng có số.** Chúng **chưa** trả lời được câu hỏi trên, vì lệch không cùng chiều:

```
   ngay    agent   monitoring           gateway            p95 mon / gw
                   mau    p95 (s)       mau    p95 (s)
   07/09     6      17    63,034        202     1,361        46,3 lan
   08/09     7      17    52,848          1    38,238         1,4    <- gateway 1 mau
   09/09     6   1.713    32,010         12    90,564         0,4    <- NGUOC chieu
   09/09     7      17    63,544          6    11,834         5,4    <- gateway < 10 mau
   12/09     7      44    48,654         60     0,953        51,1 lan
```

Ba cặp đủ mẫu ở cả hai phía: hai cặp monitoring chậm hơn ~50 lần, một cặp gateway chậm hơn. Hai nguồn có thể đo hai tập lượt gọi khác nhau trong cùng ngày (lượt không qua Gateway vẫn vào Monitoring) — **chưa kiểm**. `latency_resolved` chọn `monitoring` cho cả 5 cặp.

---

## `fact_provider_daily` — **Sổ của NHÀ CUNG CẤP.** Ý kiến thứ hai, KHÔNG phải nguồn thứ năm

5 dòng · Khoá chính `(day, provider_project, raw_model)` · migration 011, 04/09/2026

### ⚠ `usage_resolved` KHÔNG đọc bảng này, và không bao giờ được đọc

Bảng này trả lời câu **"ngày A, nhà cung cấp nói họ đã phục vụ bao nhiêu lượt và bao nhiêu token?"** — một câu khác hẳn *"sổ của ta ghi bao nhiêu"*. Cùng những lượt gọi đó **đã nằm trong `fact_call` rồi**, nên cộng bảng này vào tổng lưu lượng là **đếm đôi**. Nếu về sau có ai muốn "gộp thêm nguồn provider cho đầy đủ" — đó chính là nhầm lẫn mà dòng này sinh ra để chặn.

Chỉ đúng **một** chỗ được đọc nó: nhóm I của `scripts/audit_db.py`.

### Vì sao cần một bảng riêng thay vì dùng `fact_monitoring`

Đường nạp monitoring quy project về agent qua `dim_agent.gcp_project_id`. Nhưng project mà Gateway gọi tới **không thuộc agent nào** — nó là điểm quan sát của chính Gateway. Nhét nó vào `dim_agent` để đường ống chạy được sẽ tạo ra một "agent" không tồn tại, và agent giả đó sẽ hiện lên dashboard. Nên `provider_project` ở đây là **`TEXT` trần, KHÔNG có khoá ngoại** tới `dim_agent`.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `day` | `date` | ngày (giờ VN) | 26/08 → 01/09/2026 | `2026-08-31` |
| 2 | `provider_project` | `text` | mã project bên nhà cung cấp | 1 project · **không FK** — xem trên | `project-e62bad30-a591-407b-ba7` |
| 3 | `raw_model` | `text` | tên model **nguyên gốc** họ báo | Nằm trong khoá chính **thay cho `model_id`**, vì `model_id` có thể NULL mà cột NULL thì không làm khoá chính được | `gemini-3.5-flash-lite` |
| 4 | `model_id` | `integer` | model đã chuẩn hoá | **NULL khi chưa ánh xạ được** — để rỗng chứ không gán bừa | `12` |
| 5 | `requests` | `bigint` | số lượt **họ** nói họ đã phục vụ | NULL = không đo được, **khác hẳn 0** | `41` |
| 6 | `input_tokens` | `bigint` | token vào theo số của họ | Lấy từ nhánh **quota**, không phải metric `generate_content_usage_*` (metric đó **không tồn tại**) | `47613` |
| 7 | `output_tokens` | `bigint` | token ra theo số của họ | | `3922` |
| 8 | `pulled_account` | `text` | tài khoản Google dùng để kéo | Giữ lại vì **hai tài khoản cho ra hai thế giới khác nhau**, và sau này không ai nhớ project nào thuộc tài khoản nào. **Đo 14/09: 0/5 dòng có** sau lần dựng lại từ `data/` | `NULL` |
| 9 | `pulled_at` | `timestamp` | thời điểm nạp | **Đo 14/09: cả 5 dòng mang cùng giờ của lần dựng lại** (`2026-09-14 03:05`), không phải giờ kéo thật | `2026-09-14 03:05` |

### Ba cái bẫy khi đọc số của nhà cung cấp — cả ba đều **đo được**, không phải phòng xa

1. **Tem thời gian là CUỐI ô, không phải đầu ô.** Nên số ở `00:00` thuộc về **ngày hôm trước**. Bộ nạp lùi một giây rồi mới cắt ngày.
2. **Metric hạn mức trả về HAI chuỗi y hệt nhau**, tách theo nhãn `limit_name` (`PerDay` / `PerMinute`). Cộng cả hai là **nhân đôi** — đây chính là lỗi đã sinh ra con số "lệch 2,19 lần" hoàn toàn giả trong lần đo đầu. Bộ nạp lấy nhánh `PerDay` **và so với nhánh `PerMinute`**, lệch thì dừng, không lặng lẽ chọn một bên.
3. **`api_request_count` đếm MỌI phương thức API**, còn metric quota chỉ đếm `GenerateContent` theo model. Ngày chạy thật hai phép đo trùng khít (31/08: 41 = 41); ngày thử nghiệm thì lệch (29/08: 3 vs 20). Lệch ở đây là **lưu ý, không phải hỏng**.

Ghi chú: `*_limit` là hạn mức theo `ALIGN_MAX`, **không phải số đếm** — đừng cộng.

---

## `fact_usage_hourly` — **Lưu lượng theo GIỜ.** Cùng năm chiều khoá như bảng ngày

3.691 dòng · Khoá chính `(hour, agent_id, model_id, account_id, source)` · migration 008, 03/09/2026

**BA nguồn, không phải bốn — và nguồn vắng mặt là một thông tin.**

```
   app          fact_call.ts_local          738 dong    -> xuong duoc gio
   gateway      fact_call.ts_local           32 dong    -> xuong duoc gio
   monitoring   fact_monitoring.ts_local  2.921 dong    -> xuong duoc gio
   billing      fact_billing_daily.day    KHONG CO      -> KHONG BAO GIO co gio
```

Hoá đơn Google tính theo **ngày**. Đó là giới hạn của nhà cung cấp, không phải của ta. Chia đều tiền một ngày cho 24 giờ sẽ cho ra một biểu đồ đẹp và một con số **bịa**. Người đọc biết `billing` vắng mặt bằng cách **truy vấn cột `source`**, không phải bằng một dòng chú thích trên giao diện.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `hour` | `timestamp` | **đầu giờ**, giờ VN | 1.924 giờ riêng biệt trên 165 ngày, 14/03 → 12/09/2026 | `2026-08-31 18:00:00` |
| 2 | `agent_id` | `integer` | agent | 1–8 | `6` |
| 3 | `model_id` | `integer` | model | 1–12 | `3` |
| 4 | `account_id` | `integer` | tài khoản. Nguồn `monitoring` dùng **tài khoản neo** vì Google chỉ báo mức project | | `949` |
| 5 | `calls` | `integer` | số lượt | | `38` |
| 6 | `total_tokens` | `bigint` | tổng token | | `45187` |
| 7 | `input_tokens` | `bigint` | token vào | | |
| 8 | `output_tokens` | `bigint` | token ra | | |
| 9 | `cached_tokens` | `bigint` | token cache. **NULL ở `monitoring`** — Cloud Monitoring không có phép đo nào cho nó | | |
| 10 | `cost_usd` | `numeric(14,6)` | tiền. **CHỈ `gateway` có** (32/3.691 dòng), và đó là số LiteLLM tự nhân từ bảng giá — không phải hoá đơn | | `0.021305` |
| 11 | `source` | `text` | nguồn | `monitoring` (2.921) · `app` (738) · `gateway` (32). **Không bao giờ có `billing`** | `gateway` |

**TỔNG THEO GIỜ PHẢI BẰNG TỔNG THEO NGÀY — nhưng CHO TỪNG NGUỒN, không phải tổng chung.** Đo 14/09/2026:

```
   gateway          233.084 = 233.084        calls     398 = 398        DAT
   monitoring   560.901.702 = 560.901.702    calls 142.163 = 142.163    DAT
   app           52.591.837  <- so voi PHAN fact_call cua nguon app
                 (52.591.837, khop). Bang ngay ghi 115.837.209, vi TLA Hop
                 Dong nam o fact_app_daily (gop san theo ngay, KHONG co gio)
```

So tổng chung là biến một sự thật đã biết thành một báo động giả — rồi người ta sẽ tắt phép kiểm đi. `scripts/audit_db.py` nhóm F kiểm theo từng nguồn.

**Vì sao bảng riêng, không thêm cột `hour` vào `fact_usage_daily`:** khoá chính của bảng ngày đang được 10 chỗ đầu đọc dựa vào; và một bảng mà hai độ mịn nằm chung thì **mọi phép SUM đều phải nhớ lọc** — đúng hình dạng lỗi `source` hồi 31/08.

**Đọc qua API:** `GET /api/usage-hourly?start=…&end=…`. Endpoint này **bắt buộc** có khoảng thời gian, khác 9 endpoint kia (chúng mặc định 30 ngày gần nhất).

---

# 3. Bảng tham chiếu (`ref_`) — quy ước do người quyết định

## `ref_price` — **Bảng giá** model theo thời điểm hiệu lực

12 dòng · Khoá chính `(model_id, effective_from)` · Đơn vị: **USD / 1 triệu token**

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `model_id` | `integer` | model nào | 1–12, đủ cả 12 model | `4` |
| 2 | `effective_from` | `date` | **giá có hiệu lực từ ngày** | Hiện toàn bộ là `2026-08-13` — mới có một mốc giá duy nhất | `2026-08-13` |
| 3 | `price_input` | `numeric(12,8)` | giá token vào | 0,10 → 2,00 USD/1M. 12/12 có | `1.25000000` |
| 4 | `price_output` | `numeric(12,8)` | giá token ra | 0,40 → 12,00 USD/1M. 10/12 có (2 model embedding không sinh token ra) | `10.00000000` |
| 5 | `price_cached` | `numeric(12,8)` | giá token đệm | 0,01 → 0,20 USD/1M. Chỉ 7/12 có | `0.12500000` |
| 6 | `source` | `text` | giá lấy từ đâu | Cả 12/12 là `google`. Ba giá trị hợp lệ: `derived` (suy ra) · `google` · `vendor` | `google` |

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

## `ref_source` — **Nguồn tự khai năng lực** của nó

4 dòng · Khoá chính `source` · Dòng do **migration 001 gieo**, nên `connect.rebuild()` **không xoá** bảng này (`KEEP_ON_REBUILD`)

Khoá ngoại từ 6 bảng trỏ vào đây: `fact_call`, `fact_usage_daily`, `fact_usage_hourly`, `fact_perf_daily`, `fact_latency_daily`, `ref_load_run` — một nguồn không có tên ở đây thì không nạp được dòng nào.

**Vì sao tồn tại:** chuỗi `source = 'app'` từng mang nghĩa ngầm *"nguồn duy nhất biết người dùng"*. Ngày Gateway ghi dữ liệu có username, mọi câu hỏi viết bằng tên nguồn sẽ trả sai mà không báo lỗi. **Hỏi cột năng lực, đừng liệt kê tên nguồn.** Lý lẽ đầy đủ ở Phần II §7b.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `source` | `text` | tên nguồn | `app` · `billing` · `gateway` · `monitoring` | `gateway` |
| 2 | `knows_user` | `boolean` | nguồn **có thể** nói ai gọi không | `true` ở `app` và `gateway`. Có thể ≠ mọi dòng đều có — xem §7b | `true` |
| 3 | `has_invoice_cost` | `boolean` | nguồn có mang tiền **hoá đơn** không | Chỉ `billing`. Tên cột là `has_invoice_cost`, **không phải** `has_cost`: Gateway có tiền, nhưng là tiền suy từ bảng giá | `false` |
| 4 | `era` | `text` | kỷ nguyên | `scrape` (đi cào số của người khác: `app`, `billing`, `monitoring`) · `gateway` (ta tự đếm) | `scrape` |
| 5 | `note` | `text` | ghi chú | 4/4 có | `Hoá đơn Google. Tính theo project nên không biết ai gọi. Về trễ ~1 ngày.` |

## `ref_load_run` — **Nhịp tim** của đường nạp. KHÔNG phải một nguồn dữ liệu

0 dòng · Khoá chính `source` (khoá ngoại tới `ref_source`) · migration 012, 09/09/2026

Trả lời đúng một câu: *"Lần cuối đường nạp của nguồn này chạy THÀNH CÔNG là khi nào?"* Thiếu câu trả lời đó thì hai trạng thái trông y hệt nhau từ phía dashboard: *dòng gateway mới nhất cách đây 3 tiếng vì không ai gọi* — bình thường; và *vì đường nạp đã chết 3 tiếng* — sự cố.

**`usage_resolved` KHÔNG đọc bảng này**, và không bao giờ được đọc. Nó không mang token, tiền hay lượt gọi nào. Người đọc nó: `scripts/audit_db.py` và `/api/health`.

**Đo 14/09/2026: 0 dòng.** Lần dựng lại cùng ngày xoá dòng mọi bảng dữ liệu, kể cả bảng này, và dịch vụ `ledger-refresh` (profile `refresh`) chưa chạy lại trên database. 0 dòng nghĩa là **chưa có nhịp tim nào được ghi** — không tự nói lên đường nạp sống hay chết.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `source` | `text` | nguồn nào | Khoá ngoại tới `ref_source`: nhịp tim của một nguồn không tồn tại là dòng rác không ai phát hiện | `gateway` |
| 2 | `last_success_at` | `timestamp` | lần cuối chạy thành công | **Giờ Việt Nam**, NOT NULL. Bên ghi PHẢI dùng `now() AT TIME ZONE 'Asia/Ho_Chi_Minh'` — đồng hồ của database, không phải của container. Postgres ở đây chạy UTC; lẫn hai đồng hồ là tuổi nhịp tim lệch đúng 7 giờ | — |
| 3 | `rows_after` | `bigint` | số dòng của nguồn trong `fact_call` ngay sau lượt đó | Không để tính toán, để đọc log ngược: *"lượt 03:02 kết thúc với 366 dòng"* | — |
| 4 | `written_by` | `text` | đường nào ghi | Đường nạp nhanh và đường dựng lại toàn bộ là hai đường khác nhau | |
| 5 | `every_seconds` | `bigint` | nhịp mà tiến trình ghi **đang** chạy, giây | `NULL` nếu chạy một lần rồi thoát. Ngưỡng của phép kiểm độ trễ suy từ đây chứ không từ biến môi trường — vì mỗi tiến trình thấy một giá trị `REFRESH_EVERY_SECONDS` khác nhau, và đó là nguồn báo động giả | `300` |

---

# 4. View

## `usage_resolved` — **CỬA CHÍNH để hỏi số liệu.** Đã chọn sẵn nguồn

1.385 dòng · Một dòng cho mỗi `(ngày, agent, model)`

Đây là cái `fact_usage_daily` lẽ ra phải là. Bảng đó đặt các nguồn cạnh nhau và bắt người hỏi tự chọn; view này **chọn sẵn, và nói rõ nó đã chọn gì**.

**Chọn theo từng chỉ tiêu, không phải theo từng dòng** — mỗi nguồn mạnh một thứ:

| Chỉ tiêu | Thứ tự ưu tiên |
|---|---|
| tiền | `billing` → thiếu thì `gateway` (**từ migration 005, 31/08/2026**). Trước đó chỉ `billing` |
| token | `gateway` → thiếu thì `billing` → `monitoring` → `app` |
| lượt gọi | `gateway` → thiếu thì `monitoring` → `app`. `billing` không có |
| người dùng | nguồn có `ref_source.knows_user` (`app`, `gateway`) |

**Hai thứ tự khác nhau là có chủ ý.** Về token, Gateway là bộ đếm của chính ta và có mặt ngay trong ngày. Về tiền, hoá đơn là số Google thật sự trừ; số của Gateway là LiteLLM tự nhân từ bảng giá. Ngày hoá đơn về, nó thay số ước tính.

> ⚠ **Migration 005 đảo ngược một quyết định của baseline.** Trước đó `cost_usd IS NULL` nghĩa là *"chưa có hoá đơn"*, và giao diện gắn dấu `≈`. Nay tiền Gateway nằm trong cột này và **trông như tiền hoá đơn**. Chủ dự án chốt đánh đổi đó ngày 31/08/2026. Muốn biết một con số tiền có phải hoá đơn không: `token_source = 'billing'`.

**Không cộng các nguồn lại** — chúng đo CÙNG một lưu lượng bằng những cái công tơ khác nhau. Cộng lại là đếm nhiều lần.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `day` | `date` | ngày (giờ VN) | 01/01 → 12/09/2026 | `2026-01-01` |
| 2 | `agent_id` | `integer` | agent | 1–8 | `2` |
| 3 | `model_id` | `integer` | model | 1–12 | `1` |
| 4 | `total_tokens` | `numeric` | tổng token đã chọn nguồn | 1.372/1.385 có. Tới 35.467.506 | `950445` |
| 5 | `input_tokens` | `numeric` | token vào | Lấy từ **CÙNG nguồn** với `total_tokens`, không COALESCE riêng từng cột | `887473` |
| 6 | `output_tokens` | `numeric` | token ra | nt. | `62972` |
| 7 | `cached_tokens` | `numeric` | token đệm | 1.166/1.385 có | `0` |
| 8 | `cost_usd` | `numeric` | tiền | **1.117/1.385 (80,6%) có** = 1.106 dòng tiền hoá đơn + 11 dòng tiền ước tính của Gateway. Phần còn lại không có tiền | `0.113907` |
| 9 | `calls` | `bigint` | số lượt gọi | 882/1.385 có | `NULL` |
| 10 | `token_source` | `text` | **con số token này từ nguồn nào** | `billing` (1.106) · `app` (194) · `monitoring` (61) · `gateway` (11) · `NULL` (13) | `billing` |
| 11 | `call_source` | `text` | **con số lượt gọi này từ nguồn nào** | `monitoring` (677) · `app` (194) · `gateway` (11) · `NULL` (503) | `NULL` |
| 12 | `token_estimated` | `integer` | **1 = TOKEN chưa được hoá đơn xác nhận** | `0` (1.106) · `1` (279). Nói về token, không nói về tiền: dòng Gateway vẫn mang cờ `1` dù có tiền | `0` |

> **Hai cột `*_source` là BẮT BUỘC, không phải trang trí.** Một con số token của hôm nay đến từ `monitoring` (ước tính, hoá đơn chưa về) trông **y hệt** con số tuần trước đến từ hoá đơn. Không có cột này thì không phân biệt được.
>
> Ralli (`agent_id=8`) **luôn** rơi về `app` (161/161 dòng) vì project `tla-ralli` chưa nối billing.

**Tổng quan theo nguồn (đo 14/09/2026):**

| token_source | số dòng | tổng token | tổng tiền (USD) |
|---|---|---|---|
| `billing` | 1.106 | 818.408.100 | **347,72** |
| `app` | 194 | 109.648.962 | — |
| `monitoring` | 61 | 56.878.640 | — |
| `gateway` | 11 | 233.084 | 0,25 *(ước tính)* |
| `NULL` | 13 | — | — |
| **Tổng** | **1.385** | **985.168.786** | **347,97** |

**Tổng quan theo agent:**

| agent | code | dòng | tổng token | tiền (USD) |
|---|---|---|---|---|
| 1 | contact-center | 534 | 360.640.136 | 111,09 |
| 2 | sale-agent | 376 | 317.103.358 | 140,69 |
| 3 | invoice | 112 | 114.031.474 | 20,94 |
| 4 | tools-quizzer | 9 | 79.915 | 0,06 |
| 5 | tla-hd | 87 | 75.793.066 | 23,55 |
| 6 | dms-feedback | 35 | 49.795.155 | 30,32 |
| 7 | crm-feedback | 71 | 15.133.845 | 21,31 |
| 8 | **ralli** | 161 | 52.591.837 | **— (không có hoá đơn)** |

---

## `usage_by_account` — Cùng số liệu, **nhìn theo tài khoản**

> ⚠ **Từ 03/09/2026, hỏi `usage_by_account_resolved` (mục ngay dưới) thay cho view này.**
> View này chỉ phủ **2/8 agent**. Nó trả lời câu *"quy về một CON NGƯỜI"*; câu dashboard cần
> là *"quy về một TÀI KHOẢN"*. Giữ lại vì `tools/diagnostics/baseline_db.py` và
> `tools/diagnostics/dien_tap_gateway.py` đọc nó làm mốc lịch sử — đổi nó là mọi số mốc cũ không so lại
> được.

360 dòng · Lọc nguồn có `ref_source.knows_user` và `kind='real'`

**Chỉ phủ tài khoản là CON NGƯỜI, ở nguồn biết người dùng.** Hôm nay chỉ agent 5 (76 dòng) và 8 (284 dòng) xuất hiện: dòng Gateway thuộc tài khoản dịch vụ nên bị `kind='real'` loại.

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `day` | `date` | ngày | 14/03 → 12/09/2026 | `2026-07-01` |
| 2 | `agent_id` | `integer` | agent | Chỉ `5` và `8` | `8` |
| 3 | `model_id` | `integer` | model | 1–4 | `3` |
| 4 | `unit_id` | `text` | đơn vị — lấy từ `account`, **không** từ fact | 26 giá trị | `69ee5b13be38bdbf5a8de666` |
| 5 | `unit_path` | `text` | đường dẫn đơn vị | **`Chưa quy được` chiếm 227/360 (63,1%)** | `Toàn công ty` |
| 6 | `unit_conflict` | `integer` | các nguồn có bất đồng đơn vị không | `0`/`1` | `0` |
| 7 | `is_shared` | `integer` | tài khoản dùng chung? | `0`/`1` — nhớ loại `1` khi tính tỷ lệ áp dụng | `1` |
| 8 | `account_id` | `integer` | tài khoản | 56 tài khoản, 1–892 | `505` |
| 9 | `username` | `text` | tên đăng nhập | 360/360 có | `system`, `c4led.anhld`, `admin` |
| 10 | `full_name` | `text` | họ tên | **Chỉ 234/360 (65,0%) có** | `Lê Đức Anh` |
| 11 | `email` | `text` | thư điện tử | **Chỉ 132/360 (36,7%) có** | `c4led.anhld@rangdong.com.vn` |
| 12 | `calls` | `integer` | số lượt gọi | 1 → 663 | `14` |
| 13 | `total_tokens` | `bigint` | tổng token | 350 → 8.126.973 | `75588` |
| 14 | `input_tokens` | `bigint` | token vào | 236 → 6.815.690 | `73500` |
| 15 | `output_tokens` | `bigint` | token ra | 3 → 1.311.283 | `2088` |

---

## `usage_by_account_resolved` — **Chiều tài khoản cho CẢ 8 AGENT.** Dùng view này

1.584 dòng · 8 agent · 63 tài khoản · migration 009, 03/09/2026

**Dùng view này, không dùng `usage_by_account`.** Hai view trả lời hai câu khác nhau (đo 14/09/2026):

```
   usage_by_account            "quy ve mot CON NGUOI"    ->  2/8 agent · 56 account
   usage_by_account_resolved   "quy ve mot TAI KHOAN"    ->  8/8 agent · 63 account
```

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `day` | `date` | ngày (giờ VN) | 01/01 → 12/09/2026 | `2026-07-01` |
| 2 | `agent_id` | `integer` | agent | 1–8, đủ cả 8 | `1` |
| 3 | `model_id` | `integer` | model | 1–12 | `2` |
| 4 | `account_id` | `integer` | tài khoản | 63 tài khoản, 1–954 | `950` |
| 5 | `username` | `text` | tên đăng nhập | 1.584/1.584 có | `svc.contact-center`, `admin`, `__unattributed_8__` |
| 6 | `full_name` | `text` | họ tên | 1.458/1.584 có. Tài khoản dịch vụ mang tên `Cả <agent>` | `Cả Sale Agent`, `Quản trị viên` |
| 7 | `email` | `text` | thư điện tử | Chỉ 125/1.584 có — tài khoản dịch vụ không có email | `tt3.khaitq@rangdong.com.vn` |
| 8 | `kind` | `text` | **loại tài khoản** — cột view cũ không có | `service_account` (1.137) · `real` (346) · `whole_agent` (54) · `unattributed` (47) | `service_account` |
| 9 | `unit_id` | `text` | đơn vị, lấy từ `account` | 32 giá trị. Tài khoản dịch vụ rơi vào `__technical_<agent>__` | `__technical_1__` |
| 10 | `unit_path` | `text` | đường dẫn đơn vị | `Chưa quy được` 321/1.584 | `Đơn vị sử dụng Chatbot Contact Center` |
| 11 | `unit_conflict` | `integer` | các nguồn có bất đồng đơn vị không | `0` (1.566) · `1` (18) | `0` |
| 12 | `is_shared` | `integer` | tài khoản dùng chung? | `1` (1.458) · `0` (126) | `1` |
| 13 | `calls` | `integer` | số lượt gọi, từ `call_source` | 1.081/1.584 có | `21082` |
| 14 | `total_tokens` | `bigint` | tổng token, từ `token_source` | 1.571/1.584 có. Tới 35.467.506 | `950445` |
| 15 | `input_tokens` | `bigint` | token vào | cùng nguồn với `total_tokens` | |
| 16 | `output_tokens` | `bigint` | token ra | cùng nguồn với `total_tokens` | |
| 17 | `cached_tokens` | `bigint` | token đệm — cột view cũ không có | 1.270/1.584 có | `0` |
| 18 | `token_source` | `text` | nguồn của token — cột view cũ không có | `billing` (1.106) · `app` (393) · `monitoring` (61) · `gateway` (11) · `NULL` (13) | `billing` |
| 19 | `call_source` | `text` | nguồn của lượt gọi — cột view cũ không có | `monitoring` (677) · `app` (393) · `gateway` (11) · `NULL` (503) | `monitoring` |

**Nghiệm thu đo 14/09:** `SUM(total_tokens)` = 985.168.786 và `SUM(calls)` = 153.956 — **cả hai** bằng `usage_resolved`.

Sáu agent chạy bằng **một** tài khoản dịch vụ: ta biết chính xác ai gọi, chỉ là "ai" đó không phải một con người — `001_baseline.sql:176-186` đã tách hai câu hỏi đó từ 20/08.

### Vì sao KHÔNG sửa view cũ (đã đo cả hai đường, cả hai hỏng)

```
   noi `kind` IN ('real','service_account')   338 dong · 3 AGENT   <- chi THEM MOT
       vi `knows_user` van chan: service_account co token o billing (741.641.736)
       va monitoring (485.267.016), ca hai deu knows_user = false

   bo LUON `knows_user`                       1.903 dong · 1.335.508.782 token
       tong chuan 915.969.971                 -> PHONG 145,8%
       vi fact_usage_daily de BON NGUON CANH NHAU, khong chong len nhau
```

### Cách dựng: JOIN với nguồn ĐÃ ĐƯỢC CHỌN, và phải JOIN **HAI LẦN**

`usage_resolved` không mang `account_id`, nhưng nó **nói ra** nó đã chọn nguồn nào. Lấy đúng nguồn ấy quay lại `fact_usage_daily` là có chiều tài khoản mà không đếm hai lần.

**Một lần là không đủ.** Đo 03/09/2026: JOIN chỉ theo `token_source` cho **token lệch 0** trong khi **calls hụt 77,9%** (27.056/122.504) — vì `usage_resolved` chọn nguồn theo **từng chỉ tiêu**, và `billing` **không có** cột `calls`:

```
   token_source | call_source | dong |    token    | calls
   -------------+-------------+------+-------------+--------
   billing      | monitoring  |  524 | 472.161.741 | 93.062   <- lech o day
   billing      |   (khong)   |  488 | 279.027.663 |      -
     (khong)    | monitoring  |   11 |           - |  2.386   <- CHI co calls
```

11 dòng chỉ-có-calls là lý do phải `FULL OUTER JOIN`: `LEFT JOIN` từ phía token vứt chúng đi mà **tổng token vẫn khớp**.

> **NGHIỆM THU PHẢI LÀ HAI CON SỐ.** `SUM(total_tokens)` **và** `SUM(calls)` đều phải bằng `usage_resolved`. Kiểm một con số thì một lỗi 78% vẫn báo ĐẠT — đã xảy ra thật.

### Phân bố, và vì sao GIỮ phần không quy được

```
   do 14/09/2026
   service_account  1.137 dong · 6 agent ·  6 account · 856.783.883 · 87,0%
   real               346 dong · 2 agent · 55 account · 103.783.862 · 10,5%
   whole_agent         54 dong · 1 agent ·  1 account ·  18.735.941 ·  1,9%
   unattributed        47 dong · 1 agent ·  1 account ·   5.865.100 ·  0,6%
```

`whole_agent` + `unattributed` = **2,5%** ta THẬT SỰ không quy được về tài khoản nào. Lọc chúng đi là nói dối rằng độ phủ bằng 100%.

**Chéo kiểm với `/api/health`** — một đường tính hoàn toàn khác (đi từ `usage_resolved`, không qua `account`) — ngày 03/09/2026 khớp cả ba: people 107.125.668 · service 793.613.395 · opaque 15.230.908.

**KHÔNG có `cost_usd`, và đó là có chủ ý:** tiền chỉ tồn tại ở mức (ngày, agent, model). Chia đều cho các tài khoản là bịa ra một con số không nguồn nào từng báo cáo.

Cột riêng so với view cũ: `kind` · `cached_tokens` · `token_source` · `call_source`.

---

## `latency_resolved` — **MỘT con số độ trễ** cho mỗi (ngày, agent). Chọn, không trung bình

449 dòng · migration 010, 03/09/2026 · 454 dòng của `fact_latency_daily` trừ 5 cặp (ngày, agent) có cả hai nguồn

| # | Cột | Kiểu | Nghĩa tên cột | Chứa dữ liệu gì | Dữ liệu mẫu |
|---|---|---|---|---|---|
| 1 | `day` | `date` | ngày (giờ VN) | 01/05 → 12/09/2026 | `2026-05-02` |
| 2 | `agent_id` | `integer` | agent | 1–7 | `6` |
| 3 | `latency_source` | `text` | nguồn đã được chọn | `monitoring` (445) · `gateway` (4). Xem mục dưới | `monitoring` |
| 4 | `samples` | `integer` | số mẫu | 1 → 5.791 | `17` |
| 5 | `p50_seconds` | `double precision` | trung vị | cùng nguồn với mọi cột khác | `14.98` |
| 6 | `p95_seconds` | `double precision` | phân vị 95 | 0,256 → 382,52 giây | `63.034` |
| 7 | `p95_bucket_from` | `double precision` | cận dưới ô chứa p95 | 445/449 có — `NULL` đúng ở 4 dòng `gateway` | |
| 8 | `p95_bucket_to` | `double precision` | cận trên ô chứa p95 | như trên | |
| 9 | `p99_seconds` | `double precision` | phân vị 99 | | |
| 10 | `enough_samples` | `boolean` | đủ mẫu? | `true` (391) · `false` (58) | `true` |

Từ migration 008, `fact_latency_daily` **có thể có hai dòng** cho cùng một `(day, agent_id)`. Đó là đúng ở tầng dữ liệu — mỗi nguồn giữ phép đo của nó. Nhưng tầng đọc chưa chịu nổi:

```
   web/js/api.js:187   d.lat = x.p95_seconds || 0;   <- GAN DE
                       khoa la `day|agent_id`, KHONG co `source`
   backend/store.py    ORDER BY day, agent_id        <- KHONG co tie-break
```

Hai dòng cho cùng khoá thì dòng đến **sau** thắng, và không ai biết là dòng nào. Không crash, không nhân đôi — chỉ là một con số **không xác định**.

**TUYỆT ĐỐI KHÔNG trung bình hai phân vị.** Phân vị không cộng được: trung bình của p95=2,1 s (trên 100 lượt) và p95=8,4 s (trên 2 lượt) ra 5,25 s trong khi số thật ~2,3 s.

View lấy **tất cả** cột từ **cùng** nguồn đã chọn — không COALESCE riêng từng cột, vì trộn p50 nguồn này với p95 nguồn kia ra một cặp số không nguồn nào từng báo cáo.

### `latency_source` — cột phục vụ PHÉP KIỂM, không lên màn hình

```
   do 14/09/2026
   monitoring  445 dong    p95 NOI SUY, p95_bucket_* CO gia tri
   gateway       4 dong    p95 tu SO THO, p95_bucket_* = NULL
```

Dashboard hiện **một con số trần**. `/api/performance` **không** trả cột này — kiểm qua HTTP: `'latency_source' in row` là `False`.

### ⚠ Thứ tự ưu tiên hiện tại là LỰA CHỌN TẠM

`monitoring` trước `gateway`. Lý lẽ là **rủi ro bất đối xứng**, không phải độ chính xác:

```
   monitoring truoc  ->  dashboard KHONG doi con so nao hom nay (do: A.lat 13,8002
                         truoc = 13,8002 sau). Sai lam nay khong ai nhin thay.
   gateway truoc     ->  p95 cua DMS roi tu ~58 s xuong ~1,8 s. Nguoi xem thay
                         he thong nhanh len 31,9 LAN sau mot dem, va no trong y
                         nhu that.
```

Hai nguồn lệch **31,9 lần** trên cùng agent 6 (p95 58,206 s vs 1,822 s; p50 lệch 24,9 lần; đo 03/09/2026). **Đo 14/09 đã có 5 ngày chồng lấn, nhưng lệch không cùng chiều** (0,4 lần tới 51,1 lần) — bảng số ở mục `fact_latency_daily`. Chưa đủ để đổi thứ tự. Ba phép đo đã loại trừ giải thích dễ dãi: 0/38 lượt Gateway vượt 33,55 s; số lượt/ngày tương đương (45,4 vs 38); p50 cũng lệch mà p50 ít chịu sai số ô hơn.

**Đổi chiều = sửa đúng MỘT dòng `CASE`** trong SQL của view. Phép đo sẽ trả lời: một buổi chạy DMS qua Gateway **trong ngày** mà Cloud Monitoring đang ghi.

**Chỗ này đi ngược `usage_resolved`, và đó là có chủ ý.** View kia cho `gateway` đứng trước billing về **token** vì hai nguồn đếm **cùng một thứ**. Với **độ trễ** thì chưa chứng minh được điều đó — cùng một tên "nguồn" không bảo đảm cùng một phép đo.

---

## `monitoring_ai` — `fact_monitoring` **đã lọc**, dùng khi cần số liệu thô

114.657 dòng (từ 726.051 — **giữ lại 15,8%**)

```sql
CREATE VIEW monitoring_ai AS
SELECT * FROM fact_monitoring
WHERE service = 'generativelanguage.googleapis.com'
  AND is_quota_limit = FALSE;
```

**Cột giống hệt `fact_monitoring`, cùng thứ tự, cùng kiểu** — 17 cột: `ts_utc` `ts_local` `agent_id` `project` `metric_nickname` `metric_type` `model_id` `response_code` `service` `method` `credential_id` `is_quota_limit` `thinking_enabled` `output_modality` `limit_name` `value` `unit`. Nghĩa từng cột xem bảng cột của `fact_monitoring`. Khác biệt sau khi lọc (đo 14/09/2026):

| Cột | Ở bảng thô | Ở view |
|---|---|---|
| `service` | 12 dịch vụ, `drive.googleapis.com` chiếm 79,3% | **1 dịch vụ duy nhất** |
| `is_quota_limit` | 31.930 dòng `true` | **0 dòng** — chỉ còn số đo thật |
| `model_id` có giá trị | 101.041/726.051 = **13,9%** | 69.111/114.657 = **60,3%** |
| `project` lớn nhất | `pro-tuner` (621.612) | `tranquil-post` (61.187) — **thứ hạng đảo hẳn** |
| `value` lớn nhất | 9,22 × 10¹⁸ (giá trị hạn mức "vô hạn") | 3.961.961 |

Dòng cuối của bảng trên là lý do view tồn tại: quên lọc thì giá trị hạn mức giả sẽ trộn vào phép cộng.

---

# Phụ lục: sơ đồ quan hệ

Số dòng đo 14/09/2026. Sơ đồ chỉ vẽ trục chính — 38 khoá ngoại thật đọc từ `pg_constraint`.

```
                        ┌─────────────┐
                        │  dim_agent  │ 8  ← gốc của mọi thứ
                        └──────┬──────┘
          ┌────────────┬───────┼────────┬─────────────┐
          ▼            ▼       ▼        ▼             ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐
    │ dim_unit │ │ dim_user │ │dim_funct.│ │ ref_budget │
    │   130    │ │   965    │ │    8     │ │     7      │
    └────┬─────┘ └────┬─────┘ └──────────┘ └────────────┘
         │            │
         └──────┬─────┘
                ▼
          ┌───────────┐          ┌───────────┐      ┌───────────┐
          │  account  │ 954      │ dim_model │ 12 ──│ ref_price │ 12
          └─────┬─────┘          └─────┬─────┘      └───────────┘
                │                      │
    ┌───────────┼──────────┬───────────┼────────────┐
    ▼           ▼          ▼           ▼            ▼
┌─────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────┐
│fact_call│ │fact_app_ │ │fact_bill-│ │fact_moni- │ │fact_perf_ /  │
│  9.453  │ │  daily   │ │ing_daily │ │  toring   │ │  latency_    │
│Ralli +  │ │    78    │ │  2.833   │ │  726.051  │ │  747 / 454   │
│Gateway  │ │(TLA HĐ)  │ │ có TIỀN  │ │ từng phút │ │ lỗi / độ trễ │
└────┬────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘ └──────────────┘
     └───────────┴────────────┼─────────────┘
     'app' + 'gateway'        │  'billing'   'monitoring'
                              ▼
                  ┌───────────────────────┐        ┌───────────────────┐
                  │   fact_usage_daily    │ 2.203  │ fact_usage_hourly │ 3.691
                  │  (4 nguồn cạnh nhau)  │        │ (không có billing)│
                  └───────────┬───────────┘        └───────────────────┘
                              ▼
                  ┌───────────────────────┐
                  │    usage_resolved     │ 1.385 — CỬA CHÍNH
                  │  (đã chọn sẵn nguồn)  │    hỏi số liệu ở đây
                  └───────────────────────┘

   ĐỨNG NGOÀI trục cộng — chỉ để đối chiếu, KHÔNG BAO GIỜ cộng vào:
     fact_provider_daily 5 (sổ nhà cung cấp) · ref_load_run 0 (nhịp tim)

   ref_source 4 — mọi cột `source` của 5 bảng fact trỏ vào đây
```

---

# Phụ lục: cách đọc kết quả `scripts/audit_db.py`

Từ **03/09/2026** báo cáo audit có ba mức thay vì hai, và nhãn của mỗi phép kiểm nói thêm một chuyện: **nó đã soi bao nhiêu dòng**.

```
   [  ok  ] Every gateway row has raw_model (41 rows checked)
                                            ^^^^^^^^^^^^^^^^
   [ note ] Gateway rows in fact_perf_daily carry method and response_code
            CHUA KIEM DUOC - 0 dong de quan sat. Day KHONG phai ket qua dat.
```

**Vì sao cần con số đó.** Mọi phép kiểm theo nguồn đều mang hình dạng *"đếm dòng xấu, đòi bằng 0"*. Chạy trên **0 dòng** thì nó trả 0 và báo ĐẠT — nó **không phân biệt** *"nguồn ghi đúng"* với *"nguồn không ghi gì cả"*.

Đây không phải chuyện lý thuyết. Bước `load_gateway.py` hỏng im lặng thì `fact_call` không có dòng gateway nào, **mọi** phép kiểm gateway vẫn xanh, và dashboard chỉ trông như *"chưa có lưu lượng"*. Cùng hình dạng lỗi đã để container `api` chạy 38 phút trên một database nó không đọc nổi ngày 02/09.

| Mức | Nghĩa | Có làm script thất bại không |
|---|---|---|
| `ok` | đã soi **n > 0** dòng, không dòng nào vi phạm | không |
| `note` | **0 dòng để soi** — chưa kiểm được, hoặc một khoảng trống dữ liệu đã biết | không |
| `FAIL` | đã soi n > 0 dòng, có dòng vi phạm | có |

**`note` KHÔNG phải một dạng ĐẠT nhẹ hơn.** Nó nói rằng phép kiểm ấy **chưa khẳng định được gì**. Số `note` tăng lên sau một lần sửa thường là dấu hiệu **tốt**: những chỗ trước nay báo đạt mà chưa quan sát gì đang lộ ra.

Mốc 03/09/2026 sau khi áp cơ chế: **72 phép · 65 đạt · 7 lưu ý · 0 hỏng** (trước đó 68 · 64 · 4 · 0).

**Khoá ngoại nay đọc từ `pg_constraint`,** không từ danh sách gõ tay. Đo ngày 03/09: danh sách cũ đã trôi mất **13/36** quan hệ, trong đó 6 do migration 008 tạo ra cùng sáng hôm đó. Nhãn `Foreign keys (36 relations, read from the database)` in ra số quan hệ **có thật**. Kèm một mốc số lượng (`>= 36`) để bắt chiều ngược lại: xoá một khoá ngoại thì danh sách tự sinh vẫn xanh, vì nó chỉ kiểm những gì còn lại. Đo 14/09/2026: database có **38** khoá ngoại, trong đó `ref_load_run → ref_source` do migration 012 thêm sau mốc 03/09.

---

# Phụ lục: bảng tra nhanh số dòng

Đo 14/09/2026 trên `token_ledger_v2`.

| Đối tượng | Loại | Số dòng | Khoá chính |
|---|---|---|---|
| `ref_load_run` | bảng | 0 | `source` |
| `alembic_version` | bảng | 1 | `version_num` |
| `ref_fx` | bảng | 1 | `day` |
| `ref_source` | bảng | 4 | `source` |
| `fact_provider_daily` | bảng | 5 | `(day, provider_project, raw_model)` |
| `ref_budget` | bảng | 7 | `(agent_id, month)` |
| `dim_agent` | bảng | 8 | `agent_id` |
| `dim_function` | bảng | 8 | `(agent_id, code)` |
| `dim_model` | bảng | 12 | `model_id` |
| `ref_price` | bảng | 12 | `(model_id, effective_from)` |
| `dim_metric_alias` | bảng | 48 | `(source, raw_name)` |
| `dim_model_alias` | bảng | 49 | `(source, raw_name)` |
| `fact_app_daily` | bảng | 78 | `row_id` |
| `dim_unit` | bảng | 130 | `unit_id` |
| `fact_latency_daily` | bảng | 454 | `(day, agent_id, source)` |
| `fact_perf_daily` | bảng | 747 | `(day, agent_id, method, response_code, source)` |
| `account` | bảng | 954 | `account_id` |
| `dim_user` | bảng | 965 | `(agent_id, user_id)` |
| `fact_usage_daily` | bảng | 2.203 | `(day, agent_id, model_id, account_id, source)` |
| `fact_billing_daily` | bảng | 2.833 | `(day, project, sku_id)` |
| `fact_usage_hourly` | bảng | 3.691 | `(hour, agent_id, model_id, account_id, source)` |
| `fact_call` | bảng | 9.453 | `call_id` |
| `fact_monitoring` | bảng | **726.051** | *(không có)* |
| `usage_by_account` | view | 360 | — |
| `latency_resolved` | view | 449 | — |
| `usage_resolved` | view | 1.385 | — |
| `usage_by_account_resolved` | view | 1.584 | — |
| `monitoring_ai` | view | 114.657 | — |
| **Tổng (23 bảng)** | | **747.714** | |

## `alembic_version` — bảng của công cụ migration

1 dòng · Khoá chính `version_num` · giá trị đo 14/09/2026: `012_nhip_tim_lam_moi`

Alembic ghi vào đây migration cuối cùng đã áp. **Không phải dữ liệu, đừng sửa tay** — sửa là Alembic tin một schema không có thật. `connect.rebuild()` giữ nguyên bảng này khi xoá dòng (`KEEP_ON_REBUILD`), vì database có sẵn không chạy lại migration.

---
---

# 🟡 PHẦN II — SCHEMA ĐỀ XUẤT CHO KIẾN TRÚC API GATEWAY

> ## ⚠️ PHẦN LỚN CÁC BẢNG DƯỚI ĐÂY KHÔNG TỒN TẠI
>
> Đây là **bản vẽ để bàn**, soạn ngày 19/08/2026. Database đang chạy là 23 bảng ở Phần I.
> Chạy `SELECT * FROM fact_attempt` sẽ báo lỗi — bảng đó chưa có.
>
> **Đo 14/09/2026 — mảnh nào đã thành thật, và thành thật bằng hình dạng nào:**
>
> | Đề xuất ở đây | Thực tế ở Phần I |
> |---|---|
> | `ref_source` (§7b) | ✅ có, đúng 5 cột, 4 dòng |
> | Gateway ghi mức từng request vào `fact_request` | 🔀 **khác hình dạng:** lượt Gateway vào `fact_call` với `source = 'gateway'` (migration 004–008), không có bảng `fact_request` |
> | `fact_latency_daily` → `fact_request.latency_ms` | 🔀 **khác hình dạng:** `fact_call.duration_ms` + dòng `source = 'gateway'` trong `fact_latency_daily`, chọn qua view `latency_resolved` |
> | Bỏ `source` khỏi khoá chính, bỏ `usage_resolved` | ❌ **ngược lại:** `source` nay nằm trong khoá của 4 bảng fact, và có thêm `usage_by_account_resolved`, `latency_resolved` |
> | `fact_attempt`, `dim_provider`, `dim_deployment`, `dim_virtual_key`, `fact_invoice_daily` | ❌ chưa có bảng nào. Khoá ảo hiện chỉ là cột `fact_call.virtual_key_id` |
> | *(không có trong bản vẽ)* | ➕ `fact_usage_hourly`, `fact_provider_daily`, `ref_load_run` |
>
> **Ba điểm còn treo** chưa được quyết, xem mục 8 cuối phần này. Chúng đổi được
> hình dạng schema, nên đừng coi bản vẽ này là đã chốt.

**Nguồn của đề xuất:**

| Tài liệu | Vai trò |
|---|---|
| `planning/Tài_liệu_triển_khai_API_Gateway.docx` (12/08/2026) | kiến trúc Gateway, luồng xác thực, định dạng dữ liệu trao đổi |
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

Ghi chú trong `db/migrations/sql/001_baseline.sql:523` — *"cached KHÔNG cùng nghĩa ở ba nguồn… Ép ba nguồn
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
| 2 | ~~**Có ghi `fact_attempt` không?**~~ | ✅ **ĐÃ CHỐT 20/08/2026 — CÓ GHI.** Xem mục 8c | |
| 3 | ~~**Ngân sách do ai chặn?**~~ | ✅ **ĐÃ CHỐT 20/08/2026.** Xem mục 8d | |

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

### 8c. ✅ Câu 2 đã chốt — CÓ ghi `fact_attempt`

Ghi mức từng lần gọi provider, dù đó sẽ là bảng lớn nhất hệ thống.

*Lý do:* đây là loại dữ liệu **không dựng lại được về sau**. Quyết định "thôi không ghi"
hôm nay là quyết định vĩnh viễn không trả lời được hai câu *"bao nhiêu tiền cháy vì
retry"* và *"deployment nào hay dính 429"*.

Số hiện tại **không** dùng để bác việc này được: `fact_perf_daily` đang có **0 lượt mã
429** và tổng lỗi 113/44.912 = 0,25%. Nhưng đó là số của kiến trúc **hiện tại**, nơi mỗi
agent gọi thẳng project riêng. Gateway **tạo ra** 429 bằng chính cơ chế của nó — cân bằng
tải dồn nhiều agent qua chung một tuyến, rồi retry và fallback.

### 8d. ✅ Câu 3 đã chốt — LiteLLM chặn, $70 mỗi agent, cảnh báo 3 mức

**Nơi thực thi: LiteLLM.** `max_budget` + `budget_duration` theo từng Virtual Key, vượt là
chặn request. Báo cáo LiteLLM mục 2.3 xác nhận tính năng này **miễn phí**; chỉ "ngân sách
khác nhau cho từng model trên cùng một key" mới là Enterprise, mà ta không cần.

**Hạn mức: $70 cho MỖI agent** — không phải trần chung. Trần riêng khoanh vùng thiệt hại:
một agent lỗi vòng lặp chỉ tự chặn mình, không kéo theo 7 agent kia. Đó đúng là lý do
LiteLLM đặt budget theo key.

**Ba mức, khớp đúng ngưỡng dashboard đang dùng sẵn (`web/js/app.js`):**

| Mức | USD | Hành động |
|---|---|---|
| 50% | $35 | cảnh báo |
| 90% | $63 | cảnh báo |
| 100% trở lên | $70 | **chặn request** |

Đối chiếu với chi tiêu thật — chỉ **Sale Agent** từng vượt mức cảnh báo đầu:

| Agent | Đỉnh tháng | % của $70 |
|---|---:|---:|
| Sale Agent | $46,56 (06/26) | **66,5%** |
| Chatbot Contact Center | $20,72 | 29,6% |
| Trợ Lý Ảo Hợp Đồng | $12,23 | 17,5% |
| Phân Loại Dữ Liệu CRM | $11,87 | 17,0% |
| Multi modal AI Invoice | $11,56 | 16,5% |
| Phân Loại Phản Hồi Tiếp Thị | $6,16 | 8,8% |
| Tools Quizzer | $0,04 | 0,1% |

Chưa agent nào từng chạm 90%.

**`ref_budget` là BẢN SAO CHỈ-ĐỌC**, bắt buộc có `synced_at`. Nơi thực thi là LiteLLM;
database chỉ để hiển thị và đối chiếu. Không có `synced_at` thì không ai biết bản sao đã
cũ bao lâu — đúng bệnh `db/gen_catalog.py` đã ghi: *"hai nguồn cho một con số thì sớm muộn
lệch nhau mà không gì báo."*

### 8e. ⚠️ Ba việc câu 3 kéo theo

**① Cảnh báo Google Cloud PHẢI giữ, và không phải để dự phòng.**
Project GCP gắn tài khoản khách hàng nên **cảnh báo được nhưng không chặn được**. Sau khi
Gateway chạy, hai cơ chế trả lời hai câu khác nhau:

| | LiteLLM `max_budget` | Cảnh báo Google |
|---|---|---|
| Trả lời | *"Agent này tiêu quá mức, DỪNG"* | *"Có ai đó đang tiêu mà KHÔNG qua Gateway"* |
| Phạm vi | chỉ lưu lượng qua Gateway | **toàn bộ project**, kể cả đường vòng |

Agent gọi thẳng Google (cấu hình sót, quay lui, hoặc còn API key cũ) thì LiteLLM **không
thấy gì**, hạn mức không bao giờ chạm, mà hoá đơn vẫn tăng. Cảnh báo Google là thứ **duy
nhất** bắt được rò rỉ đó — và trong giai đoạn 6–8 (chạy song song, chuyển từng agent) thì
phần lớn lưu lượng vẫn đi đường cũ.

**② Trợ lý ảo Ralli đặt hạn mức theo TOKEN, LiteLLM chặn theo USD.**
50.000.000 token/tháng không quy được sang `max_budget`: quy ra USD thì trần **trôi** mỗi
lần bảng giá đổi, còn `tpm_limit` là tốc độ mỗi phút chứ không phải trần tháng.
→ Giữ hạn mức token ở tầng app Ralli (đã có sẵn); LiteLLM chặn $70 như trần thứ hai. Hai
chỗ chặn nhưng **khác đơn vị nên không mâu thuẫn**.

**③ Không còn trần chung.** 8 agent × $70 = **$560** trên lý thuyết, trong khi đỉnh thật
của cả 8 cộng lại mới **$69,35** (06/26). Chưa cần trần chung, nhưng nếu sau này muốn thì
đó là quyết định riêng.

---

### 7b. ✅ `ref_source` — nguồn tự khai năng lực (thêm 21/08/2026)

Bảng mới, 5 cột, 4 dòng. Nó tồn tại vì `source = 'app'` từng mang **nghĩa ngầm**.

| cột | |
|---|---|
| `source` | khoá chính. `fact_usage_daily.source` có khoá ngoại trỏ vào đây |
| `knows_user` | nguồn này **có thể** nói ai gọi không |
| `has_invoice_cost` | nguồn này có mang tiền **hoá đơn** không |
| `era` | `'scrape'` (đi cào số của người khác) hoặc `'gateway'` (ta tự đếm) |
| `note` | |

```
   source      knows_user  has_invoice_cost  era
   app            TRUE          FALSE       scrape
   billing        FALSE         TRUE        scrape
   monitoring     FALSE         FALSE       scrape
   gateway        TRUE          FALSE       gateway
```

**Hai chỗ dễ đọc nhầm:**

**① `gateway.has_invoice_cost = FALSE` không có nghĩa Gateway không biết tiền.** LiteLLM
*có* trả về một con số tiền — nhưng nó tự nhân từ bảng giá, y như `ref_price`. Cột này hỏi
*"đã có hoá đơn nào xác nhận chưa"*, và câu trả lời là chưa. ~~Vì vậy `usage_resolved.cost_usd`
vẫn **chỉ** lấy của `billing`: để NULL thì tiền Gateway tự động được tính lại từ `ref_price`
**và** được gắn dấu `≈` — đúng bản chất của nó cho tới ngày hoá đơn về.~~

> **Đã đảo ngược ngày 31/08/2026 (migration 005).** `usage_resolved.cost_usd` nay là
> `COALESCE(billing, gateway)`: tiền Gateway hiện lên màn hình **không** có dấu `≈`. Chủ dự án
> chấp nhận đánh đổi đó. Cột `has_invoice_cost` vẫn đúng nghĩa — chỉ là view không còn dùng nó
> để quyết định. Xem mục `usage_resolved` ở Phần I.

**② `knows_user = TRUE` không có nghĩa mọi dòng đều quy được.** Nguồn `app` khai TRUE nhưng
21 dòng của nó rơi vào tài khoản `__unattributed__` — nhật ký Ralli có lượt không kèm user,
khâu nạp lùi về mặc định một cách có chủ ý. *"Nguồn này có thể mang danh tính"* khác *"mọi
dòng đều có danh tính"*. Chỉ `era='gateway'` mới đòi được vế sau, vì A3 bảo đảm mọi request
mang danh tính — và đó là điều kiện của phép kiểm trong `audit_db.py`.

**Thứ tự ưu tiên trong `usage_resolved` giờ là `COALESCE(g, b, m, a)`** — Gateway đứng
trước billing về TOKEN vì nó là bộ đếm của chính ta và có mặt ngay trong ngày, trong khi
hoá đơn về trễ ~1 ngày. Đứng trước về token **không** kéo theo đứng trước về tiền.

---

### 8f. ✅ A3 — ĐO XONG 21/08/2026: claim nào mang username

Hướng đã chốt 20/08 là *"agent tự giải mã JWT rồi gửi username lên Gateway"*. Câu đó còn
một chữ chưa xác định: **trích claim nào**. Đã đăng nhập cả hai app và giải mã payload.

**Kết quả — hai app KHÔNG dùng cùng claim:**

| | Trợ lý ảo Ralli | Trợ Lý Ảo Hợp Đồng |
|---|---|---|
| Thuật toán ký | HS256 | HS256 |
| Token sống | ~2 giờ | ~8 giờ |
| Số claim | 3 | 6 |
| `sub` | `"admin"` — **là username** | `"user-admin"` — **KHÔNG phải username** |
| `username` | *(không có claim này)* | `"admin"` — **username ở đây** |
| `role` | `"ADMIN"` | `"ADMIN"` |
| `company_id` | — | `"cty-rangdong"` |
| `unit_id` | — | `""` **rỗng** |
| `exp` | có | có |

**→ Quy ước phải nói rõ từng agent, không được rút gọn thành "lấy `sub`":**

```
   Trợ lý ảo Ralli        ->  claim  sub
   Trợ Lý Ảo Hợp Đồng     ->  claim  username        (KHÔNG phải sub)
   6 agent một-người-dùng ->  hằng số  svc.<code>
```

Viết *"agent trích `sub`"* — cách viết tự nhiên nhất — thì agent Hợp Đồng gửi lên
`user-admin`, một chuỗi hợp lệ nhưng **không tồn tại trong bảng `account`**. Gateway nhận
bình thường, JOIN ra rỗng, **không lỗi nào báo**.

**Cái bẫy thứ hai: claim `unit_id` của Hợp Đồng là RỖNG.**
Nó tồn tại, nên trông như một lối tắt cho phòng ban. Nhưng nó rỗng, và Ralli không có
claim đơn vị nào cả. Quyết định 20/08 *"agent không cần gửi phòng ban, tra
`account.unit_id`"* vì thế không chỉ tránh nguồn-sự-thật-thứ-hai — nó tránh một cái bẫy
đang nằm sẵn trong token.

**Nỗi lo "Ralli trả ObjectId" nhắm sai chỗ.** Cảnh báo ở
`db/migrations/sql/001_baseline.sql:163` nói về **bản
ghi sử dụng**, không phải JWT. Đối chiếu 891 tài khoản Ralli đã kéo về:

| | |
|---|---|
| `id` là ObjectId 24 hex | 891/891 — khoá nội bộ, tách bạch |
| `username` là ObjectId | **0/891** — không bao giờ |
| `username` có dấu chấm (`c4led.lamln`) | 814/891 |

Hai trường tách sạch, và `sub` của Ralli trả dạng username chứ không phải 24 ký tự hex.

**Điều KHÔNG chứng minh được, và lưới an toàn thay cho nó.** Tài khoản trong `.env` là
**ADMIN** ở cả hai app và không nằm trong 891 dòng danh bạ — tức đã đo hình dạng token của
một tài khoản quản trị, không phải của nhân viên thường. Quyết định 21/08: **không đợi**.
Thay vào đó, khi Gateway chạy, một phép kiểm trong `audit_db.py` phải kêu nếu có dòng
`gateway` mang username **không tra ra `account_id`** — rẻ hơn việc chờ, và bắt được cả
những sai lệch khác chưa nghĩ ra.

**Hệ quả cho C1:** cả hai app ký **HS256** (khoá đối xứng). Muốn Gateway tự kiểm chữ ký thì
phải chia sẻ khoá bí mật của app — một lý do kỹ thuật nữa cho việc *agent trích, Gateway
không cầm token*. Và JWT của hai app **không dùng lại được** để đăng nhập dashboard:
dashboard phải tự phát hành token của nó, đúng như Master Plan giai đoạn 3 nói.

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
