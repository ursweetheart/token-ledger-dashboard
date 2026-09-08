# Thiết kế: đo hình dạng bản ghi Gateway

## Context

Bản fork `D:\RangDonk\litellm_rang_dong` (LiteLLM **v1.99.0**, remote
`ursweetheart/litellm_rang_dong`) đã clone về nhưng **chưa khởi động lần nào**. Fork có sẵn
`docker-compose.yml` và `Dockerfile` 4 stage.

Máy đang chạy `token-ledger-postgres` trên `127.0.0.1:5432` chứa **867.657.110 token** của
8 tháng lịch sử. Cổng `4000`, `5433`, `9090` rảnh (đo 24/08/2026).

Khoá nằm ở `.env` của dự án dưới tên `KEY_GOOGLE_AI_STU` — đã kiểm: **HTTP 200**, 50 model.
Khoá thứ hai `KEY_GOOGLE_CLOUD_CONSOLE` trả **403 PERMISSION_DENIED**.

## Goals / Non-Goals

**Goals:**

- Thu được **một dòng `LiteLLM_SpendLogs` thật**, đầy đủ cột, chép ra tra lại được
- Phán quyết A5: `thinking_enabled` / `output_modality` có nguồn Gateway hay không
- Phán quyết A3: header danh tính có sống sót xuống bản ghi không
- Bảng đối chiếu hai chiều với 25 trường sheet `Data Out`
- Xác nhận bản fork build và chạy được

**Non-Goals:**

- **Không** tạo `fact_request` / `fact_attempt`
- **Không** nạp dữ liệu đo vào `token_ledger`
- **Không** wire LiteLLM vào `docker-compose.yml` của dự án — đó là việc C3/D3, tách riêng
- **Không** cấu hình router, budget, caching, Prometheus — 5 chức năng ở báo cáo LiteLLM
  đều để sau
- **Không** sửa code LiteLLM. Fork lần này chỉ đóng vai *bản chạy được*, chưa phải *bản sửa*

## Decisions

### D1. Compose riêng, không sửa compose sẵn có của fork

Tạo `docker-compose.probe.yml` với `name: litellm-probe` — compose project tách hẳn.

Ba sửa đổi bắt buộc so với bản gốc của fork:

```
   db ports        "5432:5432"   ->   "127.0.0.1:5433:5432"    tranh token-ledger-postgres
   litellm ports   "4000:4000"   ->   "127.0.0.1:4000:4000"    khong mo ra LAN
   env_file        - .env        ->   environment: tuong minh  khong chep khoa
```

**Đã cân nhắc:** sửa thẳng `docker-compose.yml` của fork. Bỏ, vì file đó là bản ngược dòng
— sửa nó tạo xung đột mỗi lần `git pull` từ upstream, đúng cái giá của việc fork mà lần
trước đã bàn.

### D2. Bỏ `prometheus` khỏi compose đo

Fork khai ba service. Phép đo chỉ cần `litellm` + `db`. Prometheus là chức năng đáng dùng
về sau (báo cáo LiteLLM §2.5) nhưng không liên quan tới hình dạng bản ghi.

### D3. Khoá chuyển tiếp qua `--env-file`, không chép

```bash
docker compose --env-file "D:\RangDonk\token-ledger-dashboard\.env" \
               -f docker-compose.probe.yml up -d --build
```

`--env-file` chỉ cấp biến cho **phép thế `${...}`** trong compose. Các biến khác trong file
đó (`RALLI_PASS`, `HD_PASS`…) **không** vào container vì `environment:` liệt kê tường minh.

Trong `config.probe.yaml` khoá là **tham chiếu**, không phải chuỗi:

```yaml
api_key: os.environ/KEY_GOOGLE_AI_STU
```

**Đã cân nhắc:** tạo `.env` trong thư mục fork (cách fork tự gợi ý). Bỏ, vì nó nhân bản bí
mật ra chỗ thứ hai, và thư mục fork là repo khác với `.gitignore` khác.

### D4. Hai lượt gửi request, `mock_response` trước

| Lượt | Cần | Trả lời |
|---|---|---|
| **3a** `mock_response` | không key, không tiền | A3 (header), hình dạng bản ghi, fork chạy được |
| **3b** request thật | key, ~$0,0001 | A5 (`thinking` / `modality`), cost thật |

Lượt 3a vẫn đi **trọn đường ống** của LiteLLM và vẫn ghi vào `LiteLLM_SpendLogs` — nên nó
trả lời được 3/4 câu mà không tiêu gì. Nếu đường ống hỏng, nó hỏng lúc chưa tốn.

**Đã cân nhắc:** chỉ chạy request thật cho gọn. Bỏ, vì lỗi cấu hình lúc đó sẽ lẫn với lỗi
mạng/khoá, khó phân loại — đúng cái bẫy mà kỹ năng *"vòng lặp review + sửa"* gọi là chạy
bản đầy đủ trước khi lát mỏng sạch.

### D5. Model đo: `gemini-2.5-flash`

Chọn theo lưu lượng thật, không tuỳ tiện. Đo trên `usage_resolved` ngày 24/08/2026:

| Tên trong `dim_model` | Token thật | % | Mã API thật | Gọi được |
|---|---:|---:|---|:---:|
| **`gemini-2.5-flash`** | 401.227.817 | **46,2%** | `gemini-2.5-flash` | ✅ |
| `gemini-3-flash` | 281.672.600 | 32,5% | `gemini-3-flash-preview` | ✅ |
| `gemini-2.0-flash` | 82.643.227 | 9,5% | *(không còn)* | ❌ |

`gemini-2.0-flash` — lựa chọn đầu tiên của tôi — **đã rút khỏi API**. Đổi sang
`gemini-2.5-flash` hoá ra lại tốt hơn: nó là model đông nhất hệ thống thật.

**Sửa 26/08:** cột "mã API thật" là thứ lượt đo đầu bỏ sót. `dim_model` giữ tên suy ra từ
hoá đơn, không phải mã nhà cung cấp — nên `config.probe.yaml` khai **hai** model, để chính
phép đo cho thấy LiteLLM ghi tên nào xuống `SpendLogs`: mã API hay `model_name` ta đặt.

### D6. Nhà cung cấp: `gemini/`, không phải `vertex_ai/`

Đo `fact_monitoring`: `generativelanguage.googleapis.com` **120.247 dòng / 7 agent**;
`aiplatform.googleapis.com` **20 dòng**, và cả 20 đều là công tơ `serviceruntime` chung
trong một tuần tháng 6 — không phải phép đo model.

Quyết định này cũng chốt luôn loại credential: **API key**, không phải service account JSON.

### D7. Ranh giới database là ràng buộc cứng

```
   ┌─ token-ledger-postgres :5432 ─┐        ┌─ litellm-probe db :5433 ─┐
   │  token_ledger  867 trieu token│   ✗    │  litellm   rong          │
   │  CHI DOC                      │◀──────▶│  LiteLLM tu tao bang     │
   └───────────────────────────────┘ khong  └──────────────────────────┘
                                      noi
```

LiteLLM **tự chạy migration** trong database nó được trỏ tới. Trỏ nhầm không báo lỗi — nó
ghi. Volume riêng `litellm_probe_pg`, xoá được bằng `docker compose down -v` mà không đụng
`pgdata` của dự án.

## Risks / Trade-offs

| Rủi ro | Giảm thiểu |
|---|---|
| **Build 4 stage (Next.js + Rust) rất lâu hoặc vỡ** | Chạy nền, không chặn. Nếu vỡ ở tầng phụ thuộc và gỡ quá 2 lần, **dừng và hỏi** thay vì đào tiếp — image chính thức cho hình dạng bản ghi như nhau |
| **Trỏ nhầm LiteLLM vào `token_ledger`** | Cổng, database, volume, compose project đều khác tên. Kiểm `current_database()` trước khi đọc |
| **Tranh cổng 5432 làm dừng postgres dự án** | Đã đổi sang 5433; đã đo cổng rảnh trước |
| **Khoá rơi vào log hoặc git** | `config.probe.yaml` chỉ chứa tham chiếu; mọi script in lỗi đều thay khoá bằng `<KEY>`; không ghi khoá vào thư mục fork |
| **`mock_response` không ghi `SpendLogs`** | Nếu vậy, lượt 3a mất giá trị và phải nhảy thẳng 3b. Đây là **giả định chưa kiểm** — xem Open Questions |
| **Ổ đĩa** | Docker đang giữ 54 GB image + 28,5 GB build cache. Build này thêm vài GB |

## Migration Plan

Không có migration. Change này **không đổi trạng thái hệ thống** — nó thêm bằng chứng.

**Đường lui:** `docker compose -f docker-compose.probe.yml down -v` xoá sạch container và
volume của phép đo. Xoá 2 file trong thư mục fork. Không có gì trong `token-ledger-dashboard`
bị đổi ngoài tài liệu.

## Open Questions

| | Câu hỏi | Khi nào biết |
|---|---|---|
| 1 | `mock_response` **có** ghi vào `LiteLLM_SpendLogs` không? Toàn bộ giá trị của lượt 3a đứng trên giả định này | Ngay lượt 3a — nếu bảng rỗng thì biết ngay |
| 2 | LiteLLM ghi header tuỳ ý ở **cột nào**? `metadata`, `request_tags`, hay không ghi | Lượt 3a |
| 3 | `gemini-3-flash` (32,5% lưu lượng) vì sao khoá không gọi được? | **Ngoài phạm vi** change này — điều tra riêng |
| 4 | Sau khi biết hình dạng, `fact_request` khai thế nào? | Change kế tiếp |
