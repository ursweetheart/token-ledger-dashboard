# Báo cáo: Các chức năng LiteLLM liên quan đến dự án Token Ledger

**Ngày:** 16/08/2026
**Dự án tham chiếu:** Token Ledger — API Gateway nội bộ wrap LiteLLM, định tuyến request từ 8 Agent app tới 3 nhà cung cấp LLM (OpenAI, Anthropic, Google AI Studio), mô hình 1 agent = 1 project GCP = 1 pool quota độc lập.

> Ghi chú phương pháp: mọi URL trong báo cáo này đều đã được mở và đọc trực tiếp (web fetch) từ `docs.litellm.ai`, không suy đoán từ tên gọi hay kết quả tìm kiếm gián tiếp.

---

## 1. Danh sách các chức năng LiteLLM có liên hệ tới dự án

| # | Chức năng | URL đã xác minh | Vai trò trong Token Ledger |
|---|---|---|---|
| 1 | Router — Load Balancing (bao gồm `usage-based-routing`) | https://docs.litellm.ai/docs/routing | Cân bằng tải giữa 8 project GCP theo quota còn lại |
| 2 | Routing & Load Balancing (trang mục lục) | https://docs.litellm.ai/docs/routing-load-balancing | Tổng hợp các trang con: fallback, cooldown, tag routing, budget routing... |
| 3 | Spend Tracking | https://docs.litellm.ai/docs/proxy/cost_tracking | Ghi nhận chi phí từng request, nền tảng cho dashboard chi phí |
| 4 | Budgets, Rate Limits | https://docs.litellm.ai/docs/proxy/users | Giới hạn ngân sách / rpm-tpm theo từng agent (key/team) |
| 5 | Caching | https://docs.litellm.ai/docs/proxy/caching | Giảm số request trùng lặp gửi tới provider, tiết kiệm quota + tiền |
| 6 | Auto Routing | https://docs.litellm.ai/docs/proxy/auto_routing | Định tuyến theo độ khó câu hỏi (tối ưu chi phí, không phải theo quota) |
| 7 | Config.yaml (Overview) | https://docs.litellm.ai/docs/proxy/configs | Nơi khai báo 8 deployment GCP + toàn bộ tham số router/budget/cache |
| 8 | Prometheus metrics | https://docs.litellm.ai/docs/proxy/prometheus | Nguồn dữ liệu real-time cho dashboard giám sát |
| 9 | Billable Request Metering | https://docs.litellm.ai/docs/proxy/billing_metrics | Cơ chế đo lường usage của chính LiteLLM Enterprise (không phải dashboard nội bộ) |

---

## 2. Chức năng phù hợp nhất với Token Ledger

### 2.1. Router — Load Balancing (`usage-based-routing`)
**URL:** https://docs.litellm.ai/docs/routing

**Cách hoạt động dựa trên kiến trúc hiện tại:**
Token Ledger khai báo 8 `deployment` cùng chung một `model_name` (ví dụ `gemini-pro`), mỗi deployment ứng với 1 project GCP. Router theo dõi `rpm`/`tpm` đã dùng của từng deployment theo thời gian thực (qua Redis khi chạy nhiều instance), rồi tự động chọn project nào còn nhiều quota nhất cho request tiếp theo — đúng cơ chế 1-agent-1-project-1-quota-pool mà dự án đang dùng. Kèm theo là cooldown tự động (loại project khỏi vòng chọn 5 giây nếu lỗi liên tục) và fallback (chuyển hẳn sang provider khác nếu tất cả project cùng nhóm đều fail).

**Có mất phí không:** Không. Toàn bộ Router, routing strategies (`usage-based-routing`, `simple-shuffle`, `latency-based-routing`...), cooldown, retry, fallback đều nằm trong bản mã nguồn mở (OSS), không có nhãn Enterprise trong tài liệu.

**Cách tận dụng:** Khai báo `rpm`/`tpm` chính xác cho từng project GCP trong `config.yaml`, bật `routing_strategy: usage-based-routing-v2`, và chạy kèm Redis để router chia sẻ trạng thái quota giữa các instance của gateway — không cần viết thêm logic load-balancing thủ công.

---

### 2.2. Spend Tracking
**URL:** https://docs.litellm.ai/docs/proxy/cost_tracking

**Cách hoạt động dựa trên kiến trúc hiện tại:**
Mỗi request qua gateway tự động được tính cost (dựa vào bảng giá nội bộ của LiteLLM) và ghi vào bảng `LiteLLM_SpendLogs` trong Postgres — không cần code thêm. Nếu Token Ledger gán mỗi Agent app một Virtual Key/Team riêng, Spend Tracking sẽ tự tách chi phí theo từng agent, thay thế cho việc tự viết script `crawl_all_metrics.py` / `export_billing_bigquery_to_csv.py` để lấy dữ liệu billing từ GCP.

**Có mất phí không:** Phần lõi (track theo key/user/team, endpoint `/user/daily/activity` trả breakdown theo model/provider/key) là miễn phí. Riêng **track chi tiêu theo tag tuỳ ý** (`tags` trong metadata request) là tính năng Enterprise.

**Cách tận dụng:** Dùng `/user/daily/activity` để lấy breakdown sẵn theo ngày/model/provider/key — thay thế trực tiếp cho hướng "billing export qua BigQuery" đang thử nghiệm, vì dữ liệu đã có sẵn trong Postgres của chính LiteLLM.

---

### 2.3. Budgets, Rate Limits
**URL:** https://docs.litellm.ai/docs/proxy/users

**Cách hoạt động dựa trên kiến trúc hiện tại:**
Set `max_budget` + `budget_duration` theo từng Virtual Key (= từng Agent app), hoặc theo Team. Khi 1 agent vượt ngân sách, request tự động bị chặn — giúp tránh trường hợp 1 agent lỗi vòng lặp làm cháy quota của cả 8 project.

**Có mất phí không:** Phần lõi (budget theo key/team/user, nhiều cửa sổ ngân sách cùng lúc) miễn phí. Riêng **ngân sách khác nhau cho từng model trên cùng 1 key** (ví dụ agent A chỉ được chi $10 cho GPT-4o nhưng $100 cho GPT-4o-mini) là tính năng Enterprise.

**Cách tận dụng:** Gán `rpm_limit`/`tpm_limit`/`max_budget` cho từng Virtual Key theo đúng 8 Agent app hiện có — biến mỗi agent thành 1 đơn vị quản lý ngân sách độc lập ngay trong LiteLLM, không cần tự xây cơ chế giới hạn riêng.

---

### 2.4. Caching
**URL:** https://docs.litellm.ai/docs/proxy/caching

**Cách hoạt động dựa trên kiến trúc hiện tại:**
Nếu nhiều Agent app gửi câu hỏi giống hệt hoặc gần giống nhau (cùng prompt template), cache Redis (exact-match) hoặc semantic cache sẽ trả lại response cũ thay vì gọi LLM lại — giảm trực tiếp số request tính vào quota của 8 project.

**Có mất phí không:** Miễn phí hoàn toàn (Redis/S3/GCS/Semantic cache tự host), không có nhãn Enterprise nào trong tài liệu.

**Cách tận dụng:** Bật cache Redis loại exact-match (`type: redis`) cho các agent có prompt lặp lại nhiều; **tránh dùng semantic cache cho agent nào chạy hội thoại nhiều lượt hoặc gọi tool liên tục**, vì tài liệu cảnh báo rõ nó dễ trả nhầm response cũ trong luồng hội thoại/agent.

---

### 2.5. Prometheus metrics
**URL:** https://docs.litellm.ai/docs/proxy/prometheus

**Cách hoạt động dựa trên kiến trúc hiện tại:**
Gateway tự expose endpoint `/metrics` (định dạng Prometheus) khi bật `callbacks: [prometheus]` trong config. Đây là nguồn dữ liệu real-time cho Token Ledger Dashboard — thay vì tự viết script query Postgres định kỳ, dashboard có thể scrape trực tiếp `/metrics` để lấy token consumption, request count, budget còn lại theo từng model/team.

**Có mất phí không:** Miễn phí, có sẵn trong Docker image chính thức của LiteLLM (thư viện `prometheus_client` đã cài sẵn).

**Cách tận dụng:** Bật callback `prometheus` trong `config.yaml`, trỏ Grafana (hoặc dashboard tự viết bằng Chart.js đang dùng cho `token-ledger-dashboard`) vào endpoint `/metrics` để có view real-time song song với báo cáo định kỳ từ Spend Tracking.

---

## 3. Chức năng cần lưu ý — không phù hợp / không cần thiết cho giai đoạn hiện tại

**Billable Request Metering** — https://docs.litellm.ai/docs/proxy/billing_metrics

Đây **không phải** chức năng dashboard nội bộ. Theo nội dung đọc trực tiếp từ trang: đây là cơ chế để bản thân LiteLLM Enterprise đo lường usage của khách hàng nhằm tính phí license (mô hình pricing usage-based của LiteLLM Enterprise), yêu cầu bắt buộc phải có `LITELLM_LICENSE` và bộ chứng chỉ mTLS cấp riêng. Nếu Token Ledger chỉ cần theo dõi chi phí nội bộ cho Rạng Đông, chức năng này **không cần thiết** — Spend Tracking (mục 2.2) đã đáp ứng đủ nhu cầu mà không tốn phí.

---

## 4. Tổng kết: Free vs Trả phí

| Chức năng | Free (OSS) | Cần Enterprise |
|---|---|---|
| Load balancing, usage-based-routing, fallback, cooldown | ✅ | |
| Spend tracking theo key/user/team, endpoint `/user/daily/activity` | ✅ | |
| Spend tracking theo **tag tuỳ ý** | | ✅ |
| Budget theo key/team/user, nhiều cửa sổ ngân sách | ✅ | |
| Budget **riêng theo từng model trên 1 key** | | ✅ |
| Caching (Redis/S3/GCS/Semantic) | ✅ | |
| Prometheus metrics (`/metrics`) | ✅ | |
| Billable Request Metering | | ✅ (bắt buộc có license) |

**Kết luận:** Với thiết kế hiện tại của Token Ledger (8 Agent app, giám sát quota + chi phí nội bộ), toàn bộ 5 chức năng cốt lõi ở mục 2 đều nằm trong bản mã nguồn mở, không phát sinh chi phí license. Chỉ cần cân nhắc Enterprise nếu sau này Token Ledger cần: (a) phân tách chi phí theo tag tuỳ ý chi tiết hơn key/team, hoặc (b) giới hạn ngân sách khác nhau cho từng model trên cùng 1 agent.
