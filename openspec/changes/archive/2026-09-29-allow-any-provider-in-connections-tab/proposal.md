## Why

Tab Kết nối agent hiện chỉ nối được agent tới Gemini: luật lưu nháp chặn mọi upstream không bắt đầu bằng `gemini/` và cấm dấu `*` (`backend/connection_config.py:96-100`), còn bước xem trước chỉ nhận model đã có trong config hoặc tên `google/…` của danh mục OpenRouter (`backend/connection_worker.py:236-241`). Người vận hành cất được khoá Anthropic nhưng không dùng được, và mỗi model mới lại phải khai một tuyến. Proxy LiteLLM đang pin đã có sẵn danh mục provider/model chuẩn qua API công khai (`/public/litellm_model_cost_map` + `/public/providers`: 4.404 model, 3.316 model chat, trong đó 2.853 tên gọi được thuộc 68 provider định tuyến được — đo trên máy dev 28/09), nên có thể bỏ luật chỉ-Gemini mà vẫn kiểm được tên trước khi triển khai.

## What Changes

- Worker lấy **danh mục provider/model** từ `/public/litellm_model_cost_map` và `/public/providers` của instance Gateway, chỉ giữ model `mode: chat` có tiền tố định tuyến được. Model đã có trong config đang chạy vẫn được chấp nhận dù danh mục mới không còn liệt kê. Đây trở thành nguồn duy nhất để quyết định provider/model nào hợp lệ; danh mục OpenRouter (`ref_model_catalog`) không còn dùng để chặn/cho phép.
- **BREAKING (so với change `configure-agent-gateway-connections-from-ui` chưa archive):** form nhận **mọi provider có model chat** trong danh mục, không chỉ Gemini.
- **BREAKING:** cho phép **tuyến wildcard theo provider** (`anthropic/*`, `gemini/*`…) ở cả alias và upstream; vẫn cấm `*` đứng một mình và cấm `*` ở giữa tên.
- Model cụ thể được ghép tiền tố provider khi danh mục lưu tên không có tiền tố (ví dụ `claude-haiku-4-5` → `anthropic/claude-haiku-4-5`).
- **BREAKING:** Virtual Key do tab cấp mang `models: ["*"]` thay cho danh sách alias; việc tách agent/tiền dựa vào tag như quy ước vận hành hiện tại. Bản xem trước liệt kê các tuyến **không mang tag** mà key `*` có thể chạm tới.
- Kiểm tra Gateway và mẫu cấu hình agent dùng một **model cụ thể**; khi hồ sơ chỉ có tuyến wildcard, admin phải chọn model thử từ danh mục.
- Giao diện đổi nhãn "Google" thành chung, thêm ô chọn provider và gợi ý model từ danh mục.

## Capabilities

### New Capabilities
- `gateway-connection-providers`: Danh mục provider/model lấy từ LiteLLM, kiểm tra provider/model khi lưu và xem trước, tuyến wildcard theo provider, chính sách model của Virtual Key, chọn model cụ thể cho kiểm tra và mẫu cấu hình.

### Modified Capabilities

Không có trong `openspec/specs/`. Các capability `gateway-connection-*` vẫn nằm trong change `configure-agent-gateway-connections-from-ui` chưa archive; các điều khoản sau của nó bị capability mới thay thế và phải được sửa trước khi archive (xem tasks): "explicit model aliases" trong *Connection profile and wizard* và kịch bản *Invalid or immutable input* coi "wildcard alias" là không hợp lệ; "model-restricted … Virtual Keys" trong *Virtual key lifecycle and quota* (đều ở `gateway-connection-management`). Điều khoản "explicit agent-owned routes" trong *Explicit tagged routing and secure secret references* (`gateway-connection-application`) được giữ, hiểu là tuyến thuộc đúng một agent và mang đúng một tag — tuyến wildcard theo provider vẫn thoả.

## Impact

- Backend: `backend/connection_config.py` (luật model, `integration_template`), `backend/connection_worker.py` (danh mục, xem trước, cấp key, kiểm tra), `Gateway.call` thêm hai đường `GET /public/litellm_model_cost_map`, `GET /public/providers` vào danh sách cho phép.
- UI: `web/index.html`, `web/js/gateway-connections.js` (nhãn, ô provider, gợi ý model, model thử).
- Tests: `tests/connection_config_cases.py`, `tests/connection_admin_cases.py`, fixture `tests/gateway-connections/` (cần một provider thứ hai giả).
- Không đổi schema DB, không migration. Không đổi bộ nạp ledger: model mới vẫn được `auto_register_models` đăng ký, nhưng **provider trên dashboard vẫn đoán từ tiền tố tên** (`db/load_gateway.py:298`) — nếu SpendLogs ghi tên Anthropic không tiền tố (như trong danh mục LiteLLM) thì sẽ ra `unknown`; chưa kiểm vì chưa có request Anthropic nào. Sửa việc đó thuộc một change riêng (đọc `model_group`).
- Rủi ro tiền: key `*` + tuyến wildcard cho phép agent tự chọn model đắt; hạn mức từng key là phanh duy nhất. Key `*` cũng chạm được tuyến legacy không tag (`gemini-flash`, `gemini-flash-preview` dùng `KEY_GOOGLE_AI_STU`).
