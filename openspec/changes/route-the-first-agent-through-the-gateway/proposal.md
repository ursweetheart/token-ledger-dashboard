# Cho agent thật đầu tiên đi qua Gateway, bằng đường còn dùng được với cả 8 agent

## Why

Tính tới 30/08/2026, Gateway đã chứng minh được **đường ghi sổ** — một lượt `curl` ngày
29/08 để lại một dòng `LiteLLM_SpendLogs` đủ cột (`spend 1,17e-05`, `total_tokens 17`,
`end_user tuan.tran`, `messages {}`, chuỗi câu hỏi gốc 0 lần trong toàn database).

Nhưng **chưa một agent thật nào gửi qua Gateway một request nào.** Đo 30/08:

```
   dms-feedback-classification/service/.env   GEMINI_API_KEY = AQ.…  (khoa Google THAT)
   src/dms/gemini_client.py:59                genai_legacy.configure(api_key=…)
                                              khong co client_options / transport
   git status ban clone                       chi 1 file untracked (docker-compose.override.yml)
                                              -> chua sua dong nao cua nhom DMS
```

Chừng nào điều đó còn đúng, sổ của Gateway vẫn là **sổ trống**, và toàn bộ con số trên
dashboard vẫn đến từ ba nguồn cũ — ba nguồn mà chính dự án này đã đo được là thiếu và phải
suy ra (32% số tiền hiển thị là suy từ bảng giá; dashboard từng hụt 26% token).

### Vì sao là đường `/v1/chat/completions` chứ không phải `/gemini` passthrough

Có hai đường đưa DMS qua Gateway. Đường passthrough rẻ hơn nhiều về công sửa (2 dòng trong
`gemini_client.py`), và nhật ký 29/08 mục 8 đã phác sẵn nó. Change này **không chọn** đường
đó, vì đọc mã nguồn fork `f005afa146` cho thấy nó không nhân lên được 8 agent:

`passthrough_endpoint_router.py:72-95` chọn khoá nhà cung cấp bằng `next()` trên danh sách
deployment, lọc theo đúng ba điều kiện — `use_in_pass_through is True`, provider khớp, và
`deployment_region == region_name`. Với Google AI Studio, `_get_region_name_from_api_base()`
(`:314-327`) trả `None` cho mọi provider trừ `assemblyai`. Nên **cả 8 tuyến project đều
khớp như nhau, và `next()` luôn lấy dòng đầu tiên**:

```
   /v1/chat/completions              /gemini passthrough
   ────────────────────              ───────────────────
   sk-dms  -> tag dms  -> KEY_DMS    sk-dms   ┐
   sk-sale -> tag sale -> KEY_SALE   sk-sale  ├─> KEY cua dong dau tien
      …                                 …     ┘
   8 agent -> 8 khoa -> 8 project    8 agent -> 1 khoa -> 1 project
```

Hệ quả: hoá đơn Google dồn cả 8 agent vào một project, và **nguồn đối chiếu độc lập của
Giai đoạn 6 biến mất** — đúng thứ mà điều kiện "8 khoá API của 8 project" sinh ra để giữ.
Đây là kết luận **đọc được từ mã nguồn**, chưa đo bằng lượt gọi thật; ba điều kiện lọc và
`next()` không có nhánh nào khác để hiểu.

## What Changes

- **Thêm một nhánh backend thứ ba** (`gateway`) vào `GeminiClient` của DMS, bên cạnh hai
  nhánh `vertex` / `apikey` đang có. Không viết lại: file đã có sẵn công tắc chọn backend,
  và cả dự án DMS chỉ nhìn thấy `generate()` / `generate_json()` trả về
  `GeminiResponse(text, usage)`.
- **`.env` của DMS**: `GEMINI_BACKEND=gateway`, `GEMINI_API_KEY` đổi từ khoá Google sang
  Virtual Key `sk-…`, `GEMINI_MODEL` đổi từ tên thật sang **bí danh** khai trong
  `config.gateway.yaml`, thêm địa chỉ Gateway.
- **`docker/gateway/config.gateway.yaml`**: thêm `tags` cho tuyến VÀ khai `enable_tag_filtering: true` trong `router_settings` (mặc định `False`), để việc chọn khoá
  project đi qua virtual key thay vì đi qua thứ tự dòng.
- **`docker-compose.override.yml` của bản clone DMS**: nối container DMS vào mạng của
  Gateway (file mới của ta, không phải file của nhóm DMS).
- **Không đụng**: logic phân loại, `app.py`, `classify.py`, `watcher`, SharePoint, Teams.

Đây là lần đầu phải sửa file của nhóm DMS. Nguyên tắc "0 dòng sửa" giữ từ 29/08 chấm dứt ở
change này, có chủ ý và ghi rõ.

## Capabilities

### New Capabilities
- `agent-gateway-routing`: lưu lượng LLM của một agent phải đi tới nhà cung cấp **chỉ qua**
  Gateway, và mỗi request phải được tính vào **đúng khoá project của agent đó** — không
  được rơi vào một khoá dùng chung chọn theo thứ tự dòng, và không được im lặng mất chế độ
  JSON hay nhân đôi số lượt thử lại.

## Impact

- **Code ngoài repo này**: `dms-feedback-classification/service/src/dms/gemini_client.py`
  (thêm nhánh, không sửa nhánh cũ)
- **Cấu hình ngoài repo này**: `.env` và `docker-compose.override.yml` của bản clone DMS
- **Code trong repo**: `docker/gateway/config.gateway.yaml` (thêm `tags`)
- **Vận hành**: cấp 1 Virtual Key cho `dms-feedback`; Gateway phải đang chạy
- **Không đụng**: schema database, `db/`, `backend/`, `web/`
- **Chưa thuộc phạm vi**: nạp `LiteLLM_SpendLogs` sang `token_ledger_v2` (chưa có
  `db/load_gateway.py`, và cả repo không grep ra chuỗi `SpendLogs`) — dashboard vẫn chưa
  hiển thị được token của DMS sau change này. Đó là change kế tiếp.
