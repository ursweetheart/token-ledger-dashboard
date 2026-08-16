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
