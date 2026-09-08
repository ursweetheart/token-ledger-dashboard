# Đo xem Gateway thật sự ghi lại những gì

## Why

Dự án sắp thiết kế `fact_request` — bảng trung tâm của kỷ nguyên Gateway. Mọi thứ ta biết
về hình dạng của nó hôm nay đều đến từ **đọc tài liệu rồi suy ra**, chưa một dòng dữ liệu
thật nào được nhìn thấy.

Hai quyết định đã ban hành đang đứng trên giả định chưa kiểm chứng:

| Quyết định | Giả định nằm dưới | Đã đo? |
|---|---|---|
| **A5** — chuyển `thinking_enabled` / `output_modality` sang "Nguồn: Gateway" | LiteLLM có phơi hai trường đó | ❌ |
| **A3** (chốt 20/08) — agent tự giải mã JWT rồi gửi `X-User` | LiteLLM **giữ lại** header đó và ghi xuống | ❌ |

Cả hai đều hỏng **im lặng** nếu sai:

```
   A5 sai  ->  cot "think" tren dashboard TRANG, khong loi nao bao
   A3 sai  ->  quy uoc danh tinh khong thuc hien duoc, phat hien khi 8 agent da code xong
```

`viec-can-lam-truoc-api-gateway.md` §A5 tự nó đã ghi điều kiện: *"xác nhận LiteLLM có phơi
chúng không"*. Câu đó tới nay chưa ai làm.

### Vì sao là bây giờ

Bản fork `litellm_rang_dong` (v1.99.0) đã có trên máy nhưng **chưa khởi động lần nào**. Và
tài liệu chính của dự án xếp *"Dựng sẵn `fact_request` / `fact_attempt`"* vào mục **việc
KHÔNG nên làm** khi chưa chốt hình dạng. Đo trước khi dựng là đúng thứ tự đã tự đặt ra.

Việc này **rẻ**: 3 request tới Google, dưới một xu, trong một project GCP tách rời.

## What Changes

- **Dựng một môi trường đo tách biệt** từ bản fork: `docker-compose.probe.yml` +
  `config.probe.yaml` đặt trong `litellm_rang_dong`, **không** sửa `docker-compose.yml`
  sẵn có của fork, **không** đụng `docker-compose.yml` của dự án.
- **Gửi một request thật** qua LiteLLM tới `gemini/gemini-2.5-flash`, kèm header `X-User`
  và metadata, sau khi đã chạy được lượt `mock_response` không tốn phí.
- **Trích nguyên một dòng** `LiteLLM_SpendLogs` cùng toàn bộ cột của bảng, chép ra làm
  bằng chứng tra lại được.
- **Lập bảng đối chiếu** 25 trường của sheet `Data Out` với những gì LiteLLM thật sự ghi:
  có / không có / tên khác — và cả chiều ngược lại, những trường LiteLLM có mà `Data Out`
  đang bỏ phí.
- **Ghi kết quả** thành tài liệu trong `docs/reference/`, và sửa A5 trong sheet `Data Out`
  dựa trên đo đạc thay vì suy đoán.
- **Không** tạo bảng `fact_request` trong lần này. Không nạp dữ liệu đo vào `token_ledger`.

## Capabilities

### New Capabilities

- `gateway-record-shape`: hình dạng bản ghi mà Gateway sinh ra phải là thứ **đo được**,
  không phải thứ suy từ tài liệu — kèm ràng buộc rằng phép đo không được chạm vào
  database thật hay 8 project thật.

### Modified Capabilities

*(không có — bốn spec đang hoạt động `account-directory-scope`,
`layout-migration-equivalence`, `project-layout`, `static-document-root` đều không đổi
yêu cầu. Việc này thêm bằng chứng, không đổi hành vi hệ thống.)*

## Impact

### Đã đo được trước khi viết proposal này

Bốn phép đo chỉ-đọc đã chạy 24/08/2026, và chúng **thu hẹp phạm vi** so với dự tính ban đầu:

| Đo | Kết quả | Ảnh hưởng |
|---|---|---|
| 8 agent đi endpoint nào | `generativelanguage` **120.247 dòng / 7 agent**; `aiplatform` chỉ **20 dòng**, và cả 20 là công tơ `serviceruntime` chung, gói trong một tuần tháng 6 | Cần **API key**, không cần service account. Khai `gemini/` chứ không `vertex_ai/` |
| Hai key trong `.env` | `KEY_GOOGLE_AI_STU` → **200**, 50 model; `KEY_GOOGLE_CLOUD_CONSOLE` → **403 PERMISSION_DENIED** ("blocked" = API restriction trên key) | Dùng key AI Studio. Key kia không cần sửa |
| Model nào gọi được | `gemini-2.5-flash` **có** — **46,2%** lưu lượng thật (401.227.817 token) | Đo trên model đông nhất hệ thống, không phải model bên lề |
| Độ phủ danh mục (sửa 26/08) | **85,7%** token thật nằm trên model key này gọi được | Sau khi sửa nhầm lẫn về tên, xem mục dưới |

### ⚠️ Sửa kết luận sai của lượt đo 24/08

Bản đầu proposal này ghi `gemini-3-flash` (32,5% lưu lượng) là **key không gọi được**. Đo
lại ngày 26/08 cho thấy **kết luận đó sai**, và sai vì một lý do đáng ghi nhớ:

```
   dim_model  ghi   'gemini-3-flash'          <- ten CHUAN cua du an
   Google API tra   'gemini-3-flash-preview'  <- ten THAT cua nha cung cap
```

Tôi đã so **khớp chính xác** hai chuỗi vốn không cùng hệ quy chiếu. Model vẫn gọi được
bình thường; chỉ có phép so của tôi là hỏng.

### 🔴 Phát hiện thật, thay chỗ cho cái vừa bị bác

**Tên trong `dim_model` KHÔNG phải mã model của nhà cung cấp.** Chúng là tên chuẩn suy ra
từ **chữ trên hoá đơn Google** — `db/rules.py` khớp mẫu `"3 flash"`, `"2.5 flash lite"`…
trên tên SKU. Gateway sẽ ghi mã API (`gemini-3-flash-preview`), nên **mọi bản ghi từ
Gateway đều cần một bước ánh xạ** trước khi nối được với `dim_model`.

Đã kiểm `guess_model()` trên 10 mã API thật — nó **đã xử lý đúng** hậu tố `-preview`:

| Mã API của Google | `guess_model()` trả về |
|---|---|
| `gemini-3-flash-preview` | `gemini-3-flash` ✅ |
| `gemini-3.1-flash-lite-preview` | `gemini-3.1-flash-lite` ✅ |
| `gemini-2.5-flash-image` | `gemini-2.5-flash` ⚠️ mất nhánh ảnh |
| **`gemini-3.6-flash`** | **`None`** 🔴 |
| **`gemini-3.7-flash`** | **`None`** 🔴 |

Hai model **đã tồn tại trên API hôm nay** không ánh xạ được: mẫu `"3 flash"` không khớp
`"3.6 flash"`. Ngày một agent chuyển sang chúng, `guess_model()` trả `None` — **im lặng**,
đúng kiểu hỏng mà change này sinh ra để chặn. Ghi lại, không sửa trong change này.

### Một model thật sự không gọi được

```
   gemini-2.0-flash   82.643.227 token   9,5%   <-- KHONG con tren API nay
```

Không có mã API nào bắt đầu bằng `gemini-2.0-flash` trong 50 model key trả về. Đây là
model **đã rút**, không phải model bị chặn — khác hẳn trường hợp trên.

### Một quan sát nữa

`Trợ lý ảo Ralli` **không có dòng monitoring AI nào** — khớp với việc `tla-ralli` chưa nối
Google Billing. Nghĩa là ngày chạy song song 2 tuần (Master Plan giai đoạn 7), Ralli là
agent **duy nhất** không có bộ số Google để đối chiếu.

### Ranh giới an toàn

```
   ┌─ token-ledger-postgres :5432 ─┐        ┌─ litellm-probe db :5433 ─┐
   │  token_ledger                 │        │  litellm                 │
   │  867.657.110 token, 8 thang   │   ✗    │  rong, vut di duoc       │
   │  CHI DOC, khong ghi           │◀──────▶│  LiteLLM tu tao bang     │
   └───────────────────────────────┘ khong  └──────────────────────────┘
                                      noi
```

LiteLLM **tự chạy migration và tự tạo bảng** trong database nó được trỏ vào. Đây là lý do
ranh giới trên là ràng buộc, không phải khuyến nghị.

### Ba sửa đổi bắt buộc so với compose sẵn có của fork

| | Fork đang có | Vì sao phải sửa |
|---|---|---|
| 1 | `db` → `"5432:5432"` | **Đè lên `token-ledger-postgres`** đang chạy |
| 2 | `"4000:4000"` không có tiền tố | Mở ra LAN. Quy ước dự án: chỉ `127.0.0.1` |
| 3 | `env_file: - .env` | Buộc chép key sang thư mục thứ hai |

### Chạm vào

| | |
|---|---|
| **Mã dự án** | Không sửa file mã nào. Chỉ thêm tài liệu vào `docs/reference/` |
| **Bản fork** | Thêm 2 file mới; không sửa file có sẵn |
| **`.env`** | Chỉ **đọc** `KEY_GOOGLE_AI_STU`, chuyển tiếp qua `--env-file`, không chép đi đâu |
| **Master Plan** | Sửa A5 trong sheet `Data Out` sau khi có kết quả |
| **Chi phí** | 3 request, ~$0,0001 |
| **Rủi ro** | Build từ nguồn (4 stage, có Next.js + Rust) có thể vỡ hoặc rất lâu. Có đường lui: image chính thức cho kết quả hình dạng như nhau |
