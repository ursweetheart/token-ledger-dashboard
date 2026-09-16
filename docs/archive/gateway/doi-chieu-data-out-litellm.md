# Đối chiếu hợp đồng dữ liệu `Data Out` × bản ghi LiteLLM

Thuộc change `measure-what-the-gateway-records`, task 5.1–5.4. Soạn 27/08/2026.

Nguồn số: `tools/probe-gateway/ket-qua/spendlogs-mot-dong-4b-that.json` (request **thật**,
`gemini-3.6-flash`) và `spendlogs-mot-dong-luot5.json` (lượt có đủ 4 khoá cấu hình).
Cách đo và phiên bản ghim: [`do-ban-ghi-litellm-24-08.md`](do-ban-ghi-litellm-24-08.md).

Sheet `Data Out` có **26** trường — không phải 25 như task 5.1 ghi. Lệch 1, đã sửa trong task.

---

## 1. Cách đọc — chỗ nào chứng minh được, chỗ nào chưa

Đây là yêu cầu của task 5.4, và nó là cột quan trọng nhất trong bảng. Trộn hai loại vào
nhau là cách nhanh nhất để một giả định trông giống một phép đo.

| Dấu | Nghĩa |
|---|---|
| ✅ | **Chứng minh được** — có trong dòng đã chép ra, mở file là thấy giá trị |
| 🧩 | **Dẫn xuất được, đã chứng minh** — không có cột riêng, nhưng quy tắc tính đã đo có đối chứng |
| 🏠 | **Không phải việc của Gateway** — hệ thống ta đã có, JOIN vào |
| 🟡 | **Có đường, chưa đo** — biết đi lối nào nhưng lượt đo chưa chạm tới |
| ⚠️ | **Bẫy** — có cột trùng tên nhưng khác nghĩa, hoặc con số dễ bị cộng hai lần |

---

## 2. Chiều xuôi — 26 trường `Data Out` × LiteLLM  *(task 5.1)*

| # | Trường `Data Out` | | LiteLLM ghi ở đâu | Ghi chú |
|---|---|---|---|---|
| 1 | `request_id` | ✅ | `request_id` | Cùng tên, cùng nghĩa |
| 2 | `timestamp` | 🟡⚠️ | `startTime` | Kiểu `timestamp without time zone`, giá trị `2026-08-26T03:21:23` cho lượt chạy sáng 26/08 giờ VN → **là UTC**. Hợp đồng đòi giờ VN, phải **cộng 7 giờ**. Một phép đo 1 phút xác nhận được |
| 3 | `date` | 🧩 | suy từ `startTime` | Sau khi đã đổi múi giờ ở dòng trên |
| 4 | `username` | ✅ | `end_user` | Đo được lượt 5: header khai ở `user_header_name` → cột này. Đặt claim `sub` vào, **không** đặt cả chuỗi JWT |
| 5 | `account_id` | 🏠 | — | `dim_account` của ta, JOIN theo `username` |
| 6 | `unit_id` | 🟡 | *(chưa có)* | Hai đường: header riêng → `proxy_server_request.metadata.headers`, hoặc gắn Virtual Key vào team → `team_id`. Lượt đo dùng master key nên `team_id` rỗng |
| 7 | `unit_path` | 🏠 | — | `dim_unit` của ta, suy từ `unit_id` |
| 8 | `agent_id` | 🏠⚠️ | ~~`agent_id`~~ | **Trùng tên, khác nghĩa.** Cột `agent_id` của LiteLLM = `null` trong lượt đo, đó là agent của LiteLLM chứ không phải agent của ta. Đường đúng: mỗi agent một Virtual Key → `api_key` / `metadata.user_api_key_alias` |
| 9 | `gcp_project_id` | 🏠⚠️ | ~~`user_api_key_project_id`~~ | **Trùng tên, khác nghĩa.** "project" của LiteLLM là nhóm khoá, không phải GCP project |
| 10 | `function` | 🟡 | `request_tags` | Đường đã chạy được: header `x-litellm-tags` → `request_tags` (đo được `["a5-high", ...]`). Chưa gửi đúng giá trị `function` |
| 11 | `raw_model` | ✅ | `model` | Đo được `gemini/gemini-3.6-flash` — **có tiền tố provider**, phải cắt trước khi tra `dim_model` |
| 12 | `model_id` | 🏠⚠️ | ~~`model_id`~~ | **Trùng tên, khác nghĩa** — `model_id` của LiteLLM là id deployment trong Router. Xem mục 5 ② |
| 13 | `provider` | ✅ | `custom_llm_provider` | Đo được `gemini` |
| 14 | `thinking_enabled` | 🧩 | `metadata.usage_object.completion_tokens_details.reasoning_tokens` | **Không có cột riêng.** Bật → `432`; tắt → khoá **vắng mặt hoàn toàn**, không phải `=0`. Quy tắc: có khoá ⇒ `true` |
| 15 | `output_modality` | 🧩 | `…completion_tokens_details.{text,audio,image}_tokens` | Cùng cơ chế. Đo được `text_tokens=22` |
| 16 | `input_tokens` | ✅ | `prompt_tokens` | Đo được `35` |
| 17 | `output_tokens` | ✅⚠️ | `completion_tokens` | Đo được `454` = **432 suy luận + 22 văn bản**. Đã GỒM token suy luận — cộng thêm lần nữa là nhân đôi |
| 18 | `cached_tokens` | 🟡⚠️ | `metadata.usage_object.prompt_tokens_details.cached_tokens` | Không có cột riêng. Lượt đo `null` vì không trúng cache. **Chưa đo được** câu quan trọng nhất: `prompt_tokens` đã gồm cached hay chưa. Đúng chỗ từng làm hụt 26% token |
| 19 | `total_tokens` | ✅ | `total_tokens` | Đo được `489` = 35 + 454 |
| 20 | `cost_usd` | ✅ | `spend` | Đo được `0,00172875`, dựng lại được đến từng chữ số từ token × đơn giá |
| 21 | `cost_is_estimated` | 🧩⚠️ | `metadata.model_map_information` | **Luôn `true` với nguồn Gateway.** Xem mục 5 ① |
| 22 | `response_code` | 🟡 | `status` | Chỉ có `"success"` / `"failure"`, không phải mã HTTP. Mã và thông báo thật nằm ở `metadata.error_information` — lượt đo `null` vì không lỗi |
| 23 | `latency_ms` | ✅ | `request_duration_ms` | Đo được `5791` ms |
| 24 | `retry_count` | ✅ | `metadata.attempted_retries` | Đo được `0`, kèm `max_retries=2` |
| 25 | `fallback_used` | 🟡 | `metadata.routing_decision` | `null` trong lượt đo vì không có chuyển tuyến nào xảy ra. Phải dựng kịch bản fallback mới đo được |
| 26 | `virtual_key_id` | 🟡 | `api_key` | Lượt đo ra `"litellm_proxy_master_key"` vì dùng master key. Với Virtual Key thật sẽ là hash; tên đọc được ở `metadata.user_api_key_alias` |

**Cộng lại:** ✅ 10 · 🧩 4 · 🏠 5 · 🟡 7 = **26**.

> **Ba lần trùng tên khác nghĩa** (dòng 8, 9, 12) là loại lỗi im lặng: JOIN vẫn chạy, số vẫn
> ra, chỉ là sai. Cùng họ với `source='app'` trong change `admit-gateway-as-a-fourth-source`.
> Loader Gateway **không được** ánh xạ ba cột này theo tên.

---

## 3. Chiều ngược — LiteLLM ghi mà `Data Out` không có  *(task 5.2)*

Bốn trường dưới đây **nên thêm** vào hợp đồng. Không phải cho đủ, mà vì thiếu chúng thì
một mục của kế hoạch không có số để báo cáo.

| Đề nghị thêm | Lấy từ | Vì sao cần |
|---|---|---|
| `gateway_overhead_ms` | `metadata.litellm_overhead_time_ms` | Đo được **21,344** ms. Đây **chính là** "độ trễ tăng thêm do Gateway" mà GĐ7 dòng 21 phải báo cáo. Không có trường này thì phải đo lại bằng tay |
| `reasoning_tokens` | `…completion_tokens_details.reasoning_tokens` | Đang bị gói kín trong `output_tokens`. Tách ra mới giải thích được vì sao chi phí nhảy |
| `time_to_first_token_ms` | `completionStartTime − startTime` | Chỉ số người dùng cảm nhận được, khác hẳn tổng thời gian |
| `model_group` | `model_group` | Tên tuyến **ta đặt**, khác `model` là tên API. Cần để biết request đi qua tuyến nào |

Còn ghi được nhưng chưa cần đưa vào hợp đồng: `api_base`, `cache_hit`, `cache_key`,
`session_id`, `requester_ip_address`, `call_type`, `organization_id`,
`mcp_namespaced_tool_name`, `metadata.cost_breakdown` (tách input/output/reasoning cost),
`metadata.model_map_information` (bảng giá đã dùng), `proxy_server_request` (toàn bộ header
— vết truy JWT).

---

## 4. Trường nào cần `fact_request`, trường nào gộp về ngày được  *(task 5.3)*

### Bắt buộc ở mức từng request — không gộp được

| Trường | Vì sao không gộp được |
|---|---|
| `request_id` | Định danh từng lượt |
| `timestamp` | Biểu đồ theo giờ cần độ phân giải dưới ngày |
| `latency_ms` | **p50 / p95 / p99 không cộng được.** Trung bình của các trung bình ngày không ra được phân vị. Mất dòng gốc là mất luôn p95 |
| `response_code` | Tỷ lệ lỗi cần đếm theo từng lượt |
| `retry_count`, `fallback_used` | Sự kiện rời rạc |
| `thinking_enabled`, `output_modality` | Thuộc tính của từng lượt, không phải của ngày |
| `virtual_key_id` | Đối soát khoá theo từng lượt gọi |

### Gộp về mức ngày được — cộng đơn thuần

`input_tokens` · `output_tokens` · `cached_tokens` · `total_tokens` · `cost_usd` · số request

Chiều gộp: `date × account_id × agent_id × model_id × unit_id`.

> 🔴 **Cột `status` là bắt buộc trong `fact_request`, và bắt buộc nằm trong chiều gộp.**
> Đo được 26/08: LiteLLM ghi cả request **thất bại**, kèm token count. Gộp mà không tách
> `status` là cộng token của lượt hỏng vào tổng lượt chạy được — tổng vẫn ra một con số
> trông bình thường.

---

## 5. Ba đính chính rút ra từ bảng này

### ① Mọi `cost_usd` từ Gateway đều là tiền **ước tính**

`metadata.model_map_information` cho thấy `spend` được dựng từ bảng giá của LiteLLM
(`input_cost_per_token = 7,5e-07`, `output_cost_per_token = 3,75e-06`,
`output_cost_per_reasoning_token = 3,75e-06`) — đúng ba con số dựng lại `0,00172875`.

Nghĩa là Gateway **không bao giờ** biết tiền hoá đơn. Trường `cost_is_estimated` với nguồn
`gateway` luôn `true`. Chỉ nguồn `billing` mới mang tiền thật.

Đây là cùng bài học với `chi-phi-uoc-tinh-khong-ghi-nhan`: giao diện phải nói ra chỗ nào
là suy từ bảng giá.

### ② `guess_model()` — tôi đã xếp sai mức nguy hiểm trong kế hoạch nén

Kế hoạch nén tháng 9 xếp "vá bảng giá `gemini-3.6-flash`" là rủi ro số một, với lý do
LiteLLM không tra được đơn giá. **Sai.** Đo lại hôm nay:

```
   LiteLLM   model_map_key = "gemini/gemini-3.6-flash"   CO DAY DU DON GIA
             spend dung lai duoc den tung chu so          -> KHONG phai van de

   Du an ta  db/rules.py:46  guess_model()                THIEU "3.6 flash"
             MODELS co 10 model, khong co gemini-3.6-flash
```

`guess_model()` là hàm **của ta**, ánh xạ **tên SKU hoá đơn** sang `dim_model`. Nó trả
`None` nghĩa là khi hoá đơn Google bắt đầu có dòng "gemini 3.6 flash", những dòng đó **mất
model** — và Gateway cũng không JOIN được về `model_id`.

Vẫn phải sửa, nhưng nó là **hai dòng trong `db/rules.py` cộng một dòng `dim_model`**, không
phải một việc nghiên cứu đơn giá. Đổi mức: 🔴 → 🟡. *(Ngoài phạm vi change này — task 6.4
ghi rõ "không điều tra trong change này".)*

### ③ Bảy trường chưa đo được đều gom vào một lượt đo duy nhất

`timestamp` (múi giờ) · `unit_id` · `function` · `cached_tokens` · `response_code`
(chi tiết lỗi) · `fallback_used` · `virtual_key_id`.

Cả bảy đều đo xong trong **một** lượt nếu lượt đó: dùng Virtual Key thật gắn team, gửi
header `unit` và `function`, hỏi lại đúng câu hỏi vừa hỏi (ép cache hit), và cố tình gọi
một model chết để bắt fallback + lỗi. Không cần bảy lượt.
