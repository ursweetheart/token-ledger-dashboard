# Token Ledger — Billing Export & IAM Research Log

**Mục đích:** Ghi lại toàn bộ kiến thức đã tìm hiểu và tiến độ test billing export → BigQuery, phục vụ dự án Token Ledger Dashboard (Rạng Đông).

**Ngày cập nhật:** 04/08/2026

---

## 1. Phân tích bộ quyền IAM (6 role gốc)

Bộ quyền: `Logs Viewer`, `Monitoring Viewer`, `Project Billing Manager`, `Quota Viewer (Beta)`, `Service Usage Viewer`, `Support User`

| Role | Cho phép xem | Giới hạn |
|---|---|---|
| Logs Viewer | Cloud Logging (request/error logs) | Không có Data Access audit logs (cần Private Logs Viewer + bật riêng) |
| Monitoring Viewer | Metrics: `api/request_count`, error rate, latency | **Không có label model** trên metric này |
| Project Billing Manager | Link/unlink billing account vào project | **Không** xem được chi tiết cost — cần role cấp Billing Account (Costs Manager/Administrator) |
| Quota Viewer (Beta) | Quota limit & usage hiện tại | Không phải cost/token data |
| Service Usage Viewer | Danh sách API đang enable | — |
| Support User | Support case | Không liên quan data |

**Kết luận:** Bộ quyền này đủ để giám sát vận hành (logs/metrics/quota), nhưng **không đủ** để lấy cost/token theo model — vẫn cần route Billing Export riêng.

---

## 2. Cấu trúc dữ liệu Cloud Monitoring

- Mỗi metric type = tập hợp nhiều **time series**, mỗi time series ứng với 1 tổ hợp label (`metric.labels` + `resource.labels`) duy nhất.
- JSON trả về gồm: `metric.labels`, `resource.labels`, `metricKind`, `valueType`, `points[]` (mảng timestamp+value).
- **Finding quan trọng:** metric `serviceruntime.googleapis.com/api/request_count` (dùng cho Generative Language API) **không có label `model`** → không tách được token/cost theo từng model qua Monitoring.

### Cách lấy được breakdown theo model
1. **Vertex AI / Agent Platform** (`aiplatform.googleapis.com/publisher/...`) — có model label sẵn, nhưng chỉ khi gọi model **qua Vertex**, không áp dụng cho AI Studio.
2. **Tự log ở tầng app** + tạo Log-based Metric trong Cloud Logging (áp dụng được cho cả AI Studio).
3. Data Access audit logs — có nhưng tốn phí lưu log, cần bật riêng.

---

## 3. Billing Export → BigQuery

### Cách kiểm tra đã bật chưa
- Console: **Billing → Billing export** (cấp Billing Account, cần role Costs Manager/Administrator)
- Hoặc kiểm tra trực tiếp trong BigQuery: tìm bảng `gcp_billing_export_v1_<BILLING_ACCOUNT_ID>` (Standard) hoặc `gcp_billing_export_resource_v1_<ID>` (Detailed)
- **Không có gcloud CLI/API** để check/enable — chỉ làm được qua Console UI

### Nếu đã bật
- Chỉ cần viết script Python (`google-cloud-bigquery`) hoặc dùng `bq` CLI để query trực tiếp bằng SQL — thay thế hoàn toàn bước tải CSV thủ công + `import_manual_billing.py`
- Có thể chạy script trong **Cloud Shell** (đã cài sẵn gcloud, bq, Python, tự động auth) — không cần setup local
- Schema chính: `service.description`, `sku.description`, `project.id`, `cost`, `usage.amount`, `credits`, `labels`, `currency`, `usage_start_time`

### Nếu chưa bật
- Vẫn lấy được: Monitoring metrics, Quota, Service list (độc lập với billing export)
- **Không lấy được** qua API: cost/token-theo-model — Google không có REST API public cho việc này (khác AWS Cost Explorer). File export tự động (CSV/JSON → Cloud Storage) đã bị khai tử từ 15/5/2023. Chỉ còn: BigQuery export (tự động) hoặc tải CSV tay (thủ công, không tự động hoá được).

---

## 4. Google AI Studio vs Vertex AI (nay là "Gemini Enterprise Agent Platform")

| | AI Studio | Vertex AI / Agent Platform |
|---|---|---|
| Endpoint | `generativelanguage.googleapis.com` | `aiplatform.googleapis.com` |
| Auth | API key | IAM / service account |
| $300 Free Trial credit | ❌ **Loại trừ từ 3/2026** | ✅ Vẫn áp dụng bình thường |
| Billing model | **Prepay** (từ 23/3/2026 — phải mua credit tối thiểu $10) | Pay-as-you-go qua billing account |
| Model-level metrics (Monitoring) | Không có | Có sẵn (`aiplatform.googleapis.com/publisher/...`) |
| Billing export (BigQuery) schema | Giống hệt | Giống hệt (chỉ khác giá trị `service.description`, `sku.description`) |

**Lưu ý đặt tên:** Vertex AI đã đổi tên thành **"Gemini Enterprise Agent Platform"** (công bố 22/4/2026). API cần enable trong Console: search **"Agent Platform"** → chọn **"Agent Platform API"** (không tìm bằng từ khóa "vertex" hay "Gemini" vì không ra đúng kết quả). Endpoint kỹ thuật `aiplatform.googleapis.com` không đổi.

**Phân biệt thuật ngữ:** "Provider" = bên tạo ra model (Google, Anthropic, Meta...). "AI Studio"/"Vertex AI" chỉ là **kênh truy cập** (access platform), không phải provider.

---

## 5. Google Cloud Free Trial ($300, 90 ngày)

- Không tự động tính phí thẻ sau khi hết hạn/hết credit — chỉ tính phí nếu **chủ động** bấm Upgrade
- Không cần làm gì để "hủy" — tự động đóng account, có 30 ngày ân hạn trước khi xoá resource
- Điều kiện: chưa từng là khách hàng trả phí GCP/Maps/Firebase, chưa từng đăng ký Free Trial trước đó (gắn với Google Account cá nhân, không phải công ty)
- BigQuery Sandbox: dùng thử BigQuery không cần thẻ, nhưng **không** test được billing export thật (cần billing account thật có usage)

---

## 6. Tiến độ thực hiện test (project `token-ledger-test`)

- [x] Đăng ký Google Cloud Free Trial cá nhân ($300 credit, hết hạn 03/11/2026)
- [x] Khai báo Vietnam tax info (chọn "Business Household or Individual")
- [x] Tạo project `token-ledger-test`
- [x] Enable **Agent Platform API** (tránh nhánh AI Studio bị Prepay)
- [x] Chat thử qua **Agent Studio** (model `gemini-3.6-flash`) — đã sinh ra usage thật (~4,235 tokens ghi nhận)
- [x] Enable **BigQuery API**
- [x] Tạo dataset `billing_export_test` (location: US)
- [x] Bật **Standard usage cost export** → trỏ vào `billing_export_test`
- [x] Bật **Detailed usage cost export** → cùng dataset
- [ ] **Đang chờ**: dữ liệu đổ về BigQuery (dự kiến vài giờ – 24h)
- [ ] Query kiểm tra bảng `gcp_billing_export_v1_<BILLING_ACCOUNT_ID>` đã có data chưa
- [ ] Xác nhận `service.description` thực tế hiện là gì (dự kiến `"Agent Platform"` hoặc `"Vertex AI"`)
- [ ] Thử regex parse SKU → model name, đối chiếu với logic đang dùng trong `import_manual_billing.py`
- [ ] (Tuỳ chọn) Test lại đúng 6 role IAM ban đầu bằng service account riêng trong project test

---

## 7. Query mẫu sẽ dùng khi có data

```sql
-- Kiểm tra bảng đã có + đếm dòng
SELECT COUNT(*)
FROM `token-ledger-test.billing_export_test.gcp_billing_export_v1_<BILLING_ACCOUNT_ID>`;

-- Xem service name thực tế
SELECT DISTINCT service.description
FROM `token-ledger-test.billing_export_test.gcp_billing_export_v1_<BILLING_ACCOUNT_ID>`;

-- Xem chi tiết SKU + cost
SELECT usage_start_time, service.description, sku.description, cost, usage.amount
FROM `token-ledger-test.billing_export_test.gcp_billing_export_v1_<BILLING_ACCOUNT_ID>`
ORDER BY usage_start_time DESC
LIMIT 20;
```

*Thay `<BILLING_ACCOUNT_ID>` bằng tên bảng thật xem trong BigQuery Explorer (dataset `billing_export_test`) sau khi bảng tự sinh ra.*

---

## 8. Bước tiếp theo (sau khi có data)

1. Đối chiếu schema/logic với production (8 project công ty đang dùng AI Studio thật)
2. Viết script `crawl_billing_bigquery.py` thay thế `import_manual_billing.py`, giữ nguyên logic `aggregate_tokens_weekly.py`
3. Đề xuất bật billing export chính thức trên billing account công ty (cần quyền Billing Account Administrator/Costs Manager — khác với Project Billing Manager đang có)
4. Cân nhắc dài hạn: có nên migrate 1 phần calling từ AI Studio sang Vertex/Agent Platform để có model-level metrics tự động (Monitoring) mà không cần tự log

---

## 9. Ket qua kiem thu tich hop 2 agent qua API Gateway (tuan 08-14/09/2026)

> **Nguoi thuc hien:** Tuan (nhanh `Tuan-develop`)
> **Moi truong:** Container Docker ket noi vao Gateway stack that (`gateway-lb:4000`). Co mot so luot goi that toi Google. Khong ghi du lieu san xuat SharePoint hay gui email that trong cac bai kiem harness.
> **Nhat ky day du:** [dua-dms-qua-gateway-31-08.md](./dua-dms-qua-gateway-31-08.md) - [dua-crm-qua-gateway-10-09.md](./dua-crm-qua-gateway-10-09.md) - [fallback-crm-12-09.md](./fallback-crm-12-09.md) - [ep-429-va-mat-gateway-10-09.md](./ep-429-va-mat-gateway-10-09.md)

---

### 9.1 Agent DMS — DMS Feedback Classification

- **App:** `dms-feedback-classification`, commit goc `f875b24`
- **Ngay test:** 29-31/08/2026
- **Model:** `gemini-3.5-flash-lite` (AI Studio, Virtual Key `dms-feedback-tagged`)
- **Agent code:** `dms-feedback` | **Account:** `svc.dms-feedback`

#### Ket luan tong the

**PASS — luong end-to-end da chay that.** Mot luot `POST /api/classify/text` cua DMS di qua Gateway, ra Google, ve lai DMS voi ket qua dung va de lai du dong trong `LiteLLM_SpendLogs`. DMS la **agent dau tien** di qua Gateway trong du an.

#### Nhung gi da chung minh duoc (bang so do)

| Dieu | Bang chung |
|---|---|
| Tuyen `gemini-flash-lite` goi duoc that | HTTP 200, 25 token |
| So ghi dung luot goi | `request_id` trong SpendLogs **khop dung `id`** trong response |
| `X-User` thanh `end_user` | `svc.dms-feedback` xuat hien dung trong cot `end_user` |
| Tag loc dung 10/10 luot | `attempted_retries = 0`, 0 lan cham tuyen moi co khoa sai |
| Che do JSON hoat dong qua Gateway | `json_mode=False` ra van xuoi; `True` ra JSON hop le |
| Phan loai that khop moc cu | `Bao loi = true`, `Bao hanh = true`, `Tieu cuc`, 2 muc |
| Nhanh lui lai duoc | `GEMINI_BACKEND=apikey` -> SpendLogs dung yen; DMS di thang Google, Gateway khong biet |
| Mot luot phan loai = 2 luot goi LLM | `rag_product.py`: 236 token; `issue_classifier.py`: 6.044 token |
| Dashboard nhan duoc luu luong DMS | `fact_call` +2 dong sau lan chay lai nguoi, tre ~2 giay |

#### Phat hien quan trong

| # | Phat hien | Muc do |
|---|---|---|
| 1 | `enable_tag_filtering` mac dinh **TAT** — neu bo sot, 8 agent don vao 1 project, hoa don sai ma moi phep do van DAT | Nghiem trong — da sua |
| 2 | `/gemini` passthrough khong dung duoc: `next()` luon lay deployment dau, mat phan biet agent | Loai han |
| 3 | `GEMINI_MODEL_PRICING` thieu `gemini-3.5-flash-lite` -> moi luot tinh chi phi **0** khong bao | Can sua |
| 4 | DMS tra HTTP 200 khi LLM hong (429) — `safe fallback` im lang, nguoi goi khong biet | Can bao nhom DMS |
| 5 | `startTime` trong SpendLogs la UTC tran -> loader phai cong +7 gio | Da xu ly trong loader |
| 6 | Luot goi HONG van sinh dong trong SpendLogs (`status = failure`) -> loader phai loc `WHERE status = success` | Da xu ly |

#### Pham vi chua nghiem thu

- Loc tag khi co nhieu tuyen cung bi danh (chi do tren 1 tuyen).
- Tuyen `gemini-3.6-flash` va `gemini-3-flash-preview` chua co bang chung goi duoc.
- `X-User` hien la dinh danh dich vu co dinh, chua gan voi tung nguoi dung JWT.
- ETL day du sang `token_ledger_v2`, mapping phong ban va giao dien dashboard.

---

### 9.2 Agent CRM — CRM Classification Pipeline

- **App:** `CRM-Classification-Pipeline` (ban clone)
- **Ngay test:** 09-12/09/2026 (routing: 09-10/09; fallback + 429: 12/09)
- **Model:** `gemini-2.5-flash` (Vertex Express, Virtual Key `crm-feedback-tagged`)
- **Agent code:** `crm-feedback` | **Account:** `svc.crm-feedback` | **Agent ID:** 7
- **Dac diem noi bat:** CRM la **pipeline theo lich** (batch), khong phai web service

#### 9.2.1 Ket qua routing qua Gateway (09-10/09)

**PASS.** CRM goi dung model `gemini-2.5-flash` qua Gateway, moi luot ghi dung `end_user` va tag:

| Chi so (luot goi that, prompt production day du) | Gia tri |
|---|---|
| Prompt | 10.181 ky tu |
| So dong trong lo | 2 (`CRM_merge_sample.xlsx`) |
| Thoi gian | 2,75 giay |
| Token | 4.009 |
| `end_user` trong SpendLogs | `svc.crm-feedback` |
| Tag | `crm-feedback` |
| `model_group` | `gemini-2.5-flash` |
| Ket qua | JSON hop le, phan tich duoc bang `_parse_llm_json` cua CRM |
| Cham SharePoint / email / Excel | **khong** |

#### 9.2.2 Ket qua xu ly 429 va fallback khi Gateway chet (10-12/09)

**PASS — 0 lo bi bo trong ca ba bai dien tap:**

| Bai dien tap | Kich ban | Ket qua |
|---|---|---|
| 7 unit test tu dong | Client gia, khong goi mang | **7/7 PASS** trong mili giay |
| Dien tap cat duong | Tro sang cong chet sau lo 3 | **8/8 lo thanh cong**, 5 luot duong thang |
| Dien tap dung container that | Dung `gateway-lb` giua luc chay | **60/60 lo thanh cong**, 8 luot duong thang, tu ve Gateway sau 69 giay |

Ve 429: Gateway hoan loi 123,7 giay (3 lan thu lai noi bo); mot lo hong vi 429 ton 7 phut 14 giay tong, trong do **86% la Gateway, chi 14% la CRM**.

**Quy tac fallback da xac nhan:**
- Chuyen duong sau 3 lan lien tiep loi ket noi/timeout; lo dang chay khong bi bo.
- Nhieu worker cung hong van chi gui 1 email canh bao (khoa toan cuc).
- Tham do dinh ky thanh cong -> tu ve Gateway.
- Rang buoc bat buoc: `FALLBACK_FAIL_THRESHOLD (3) <= call_llm_batch(max_retry=3)`.

#### 9.2.3 Phat hien quan trong

| # | Phat hien | Muc do |
|---|---|---|
| 1 | **Token suy nghi an 96% ngan sach dau ra** — lo 5 dong nhan ve chi **1 dong**, khong bao loi (4 tang che gon) | Nghiem trong |
| 2 | Sua bang `reasoning_effort: disable` o tuyen Gateway -> tiet kiem **3,3x tien**, nhanh **2,1x**, chu that tang **6,4x** | Da sua o Gateway |
| 3 | `max_output_tokens=8192` cung trong code CRM van cat lo 25 dong (nhan ve 20) du da tat suy nghi -> can nang len 16.000 trong repo CRM | Can bao nhom CRM |
| 4 | Bi danh model che tuyen that — `model_group` trong dung nhung `model` trong so lo model that; gay **1,46x dat hon** ma khong ai thay | Da sua (xoa bi danh) |
| 5 | `docs/HANDOVER.md` cua CRM lech code tren **moi con so** (model, batch size, retry, backoff) | Can bao nhom CRM |
| 6 | Cau nhac hua `allowed` + `locked_labels` nhung code khong bao gio gui — taxonomy chi dua vao danh sach tinh | Rui ro chua no |
| 7 | `GEMINI_BATCH_SIZE=40` trong `.env.example` bi `min(25, ...)` cat xuong 25 khong bao; va 25 van qua lon | Can bao nhom CRM |
| 8 | Khoa du phong `sa-key.json` ghi phi vao `crm-test-508114`, khong phai `crm-500509` (project that agent 7) | Chap nhan giai doan phat trien |

#### 9.2.4 Pham vi chua nghiem thu

- Lo 25 dong voi `max_output_tokens=16.000` (chi da thu voi file mount de, chua sua repo CRM).
- Khoa `sa-key.json` thuoc dung `crm-500509` truoc khi len server.
- Email Graph (Microsoft) — chua co credential Azure.
- Nhip thuc dat va do tre hai duong (da hoan co chu y, tach thanh viec rieng).
- ETL `LiteLLM_SpendLogs -> token_ledger_v2`, mapping user/phong ban va giao dien dashboard.

---

### 9.3 So sanh hai agent

| Tieu chi | DMS Feedback | CRM Classification |
|---|---|---|
| Kieu app | Web service (thuong tru) | Pipeline theo lich (batch) |
| SDK Google | `google-generativeai` (cu) | `google-genai` (moi) |
| Backend mac dinh | AI Studio (API key) | Vertex Express (service account) |
| Tu tuan tu hoa loi goi | Khong | Co (`wait_for_rate_limit()`, khoa toan cuc) |
| Thu tu dua vao Gateway | **Dau tien** (31/08) | **Thu hai** (10/09) |
| Fallback tu chuyen duong | Khong co (fail-closed) | Co — `sa-key.json` Vertex direct |
| Phat hien nghiem trong nhat | Tag loc mac dinh TAT | Token suy nghi an 96% ngan sach |
| Cach sua phat hien nghiem trong | Khai `enable_tag_filtering: true` o Gateway | Them `reasoning_effort: disable` o tuyen Gateway |

### 9.4 Hanh dong tiep theo

1. **Bao nhom CRM:** nang `max_output_tokens` `8192 -> 16000` trong `src/llm.py:274`; them kiem `finish_reason == length`; sua nhanh 429 ngu vo ich o luot cuoi.
2. **Xin khoa `crm-500509`:** de phi ghi ve dung project agent 7 truoc khi len server.
3. **Can nhac Azure Graph sau cuoc hop:** neu co credential, CRM va cac agent khac dung duoc hom thu cong ty thay Gmail ca nhan.
4. **Nghiem thu ETL pipeline:** noi `LiteLLM_SpendLogs -> token_ledger_v2 -> dashboard` cho ca DMS va CRM.
5. **Dua them agent vao Gateway:** DMS va CRM moi la 2/8 agent — can routing cho 6 agent con lai.
6. **Dat lai nguong va khoang cho fallback** theo so do su co that dau tien (hien dung con so de nghi chua hieu chinh).
