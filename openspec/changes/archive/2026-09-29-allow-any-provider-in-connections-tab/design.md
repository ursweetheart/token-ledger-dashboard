## Context

Change `configure-agent-gateway-connections-from-ui` (đã code xong, chưa archive) dựng tab Kết nối agent với ba giới hạn cứng quanh model: lưu nháp chỉ nhận upstream `gemini/…` và cấm `*` (`backend/connection_config.py:96-100`); xem trước chỉ nhận upstream đã có trong config đang chạy hoặc tên `google/…` của danh mục OpenRouter (`backend/connection_worker.py:233-241`); key cấp ra mang `models = [alias…]` (`connection_worker.py:540-541`). Kiểm tra Gateway và mẫu cấu hình agent đều lấy alias đầu tiên làm model (`connection_worker.py:653`, `connection_config.py:178`).

Proxy LiteLLM đang pin (`b7657e95b1`, trùng fork `D:\RangDonk\litellm_tuan_test`) có hai API công khai, không cần key: `/public/providers` trả enum `LlmProviders` (152 giá trị) và `/public/litellm_model_cost_map` trả `litellm.model_cost`. Theo `litellm_core_utils/get_model_cost_map.py`, bảng này được tải từ GitHub lúc khởi động, lỗi thì dùng bản trong image; compose, `docker/` và `.env` không đặt `LITELLM_LOCAL_MODEL_COST_MAP` (đã kiểm), nên danh mục có thể đổi mỗi lần tạo lại container.

Số đo trên máy dev 28/09: 4.404 mục, 3.316 mục `mode: chat`. Trường `litellm_provider` **không** phải tiền tố định tuyến: `gemini-2.5-flash` mang `vertex_ai-language-models`; 206 mục không có `/` mang `bedrock_converse`; 92 mục có `/` nhưng tiền tố khác `litellm_provider`; 11 tiền tố (`aihubmix` 72, `qwen_ai_platform` 43, `qwencloud` 41…) không có trong `/public/providers`. Theo luật ở D2 còn 2.853 tên gọi được, 68 provider. Mọi upstream Gemini đang chạy (`gemini/gemini-3.5-flash-lite`, `gemini/gemini-3.6-flash`, `gemini/gemini-3-flash-preview`, `gemini/gemini-2.5-flash`) đều có trong danh mục.

Mã nguồn fork xác nhận key có `"*"` trong `models` được coi là truy cập mọi model (`litellm/proxy/auth/auth_checks.py:3639`); chưa kiểm lúc chạy.

## Goals / Non-Goals

**Goals:**
- Nối agent tới mọi provider mà image đang pin định tuyến được, với tên được kiểm trước khi triển khai.
- Cho phép tuyến wildcard theo provider để model mới của một provider đã nối không cần thao tác thêm.
- Giữ nguyên cô lập theo tag, quản lý secret, xem trước/áp dụng/phục hồi của change gốc.
- Không làm hỏng hồ sơ đã áp dụng khi danh mục LiteLLM đổi.

**Non-Goals:**
- Adapter `openai/` + `api_base` cho provider chưa có trong LiteLLM; form không có ô `api_base`.
- Ghi provider đúng trên dashboard (đọc `model_group` trong bộ nạp ledger) — change riêng.
- Tiếp quản 8 agent legacy; tự tạo khoá ở provider; sửa việc Áp dụng xoá chú thích YAML.
- Chọn/ưu tiên model rẻ; kiểm soát chi phí ngoài hạn mức từng key đã có.

## Decisions

### D1 — Danh mục lấy từ Gateway đang pin, tải mỗi lần cần, không cache

Worker gọi `GET /public/litellm_model_cost_map` và `GET /public/providers` qua `Gateway` của instance đầu tiên (thêm hai đường vào danh sách cho phép của `Gateway.call`), mỗi lần xem trước và mỗi lần UI xin gợi ý. Lỗi mạng, HTTP lỗi hoặc thân không phải object → xem trước thất bại, không đoán.

*Vì sao không dùng `ref_model_catalog` (OpenRouter):* tiền tố OpenRouter là tên hãng (`google/`, `x-ai/`, `meta-llama/`) chứ không phải tiền tố LiteLLM, và không nói gì về việc LiteLLM gọi được hay không. *Vì sao không cache:* danh mục đổi theo lần khởi động container; một lần tải vài MB trong mạng máy chủ rẻ hơn logic làm mới cache. *Vì sao không đọc file JSON trong fork:* image có thể dùng bản tải về khác bản trong repo.

### D2 — Tên gọi được và provider tính từ tiền tố, lọc bằng `/public/providers`

Với mục chat: key có `/` → tên gọi được là key, provider là phần trước `/` đầu tiên; key không có `/` → tên là `litellm_provider/key`. Loại mục khi provider không có trong `/public/providers`. Tập provider hợp lệ là tập provider còn lại.

*Phương án bị loại:* lấy `litellm_provider` làm provider — sinh ra nhãn không định tuyến được (`vertex_ai-language-models`, `bedrock_converse`). Lấy thẳng 152 giá trị enum — gồm cả thứ không chat (`milvus`, `pg_vector`, `deepgram`).

### D3 — Tách kiểm cú pháp (lưu nháp) và kiểm danh mục (xem trước)

`connection_config.validate` (không mạng) chỉ kiểm dạng: upstream là `<provider>/*` hoặc `<provider>/<model>`, không có `*` ở chỗ khác, không `*` trần, ký tự trong tập cũ, wildcard thì alias = upstream. Bỏ luật `startswith('gemini/')`. Worker khi xem trước kiểm: provider ∈ tập D2; model cụ thể ∈ tên gọi được **hoặc** đã là upstream trong config đang chạy (giữ vế đầu của luật cũ ở dòng 235).

*Vì sao giữ vế "đã deploy":* danh mục có thể bỏ một model sau lần khởi động; hồ sơ đang chạy không được thành không-xem-trước-được.

### D4 — Wildcard: alias bắt buộc bằng upstream

Tuyến `model_name: anthropic/*`, `model: anthropic/*`. Không cho alias khác (`foo/*` → `anthropic/*`): cách LiteLLM ghép phần `*` giữa hai mẫu khác nhau chưa được kiểm trên image pin; bó hẹp thì không cần đo. `route_id(code, alias)` giữ nguyên nên tem sở hữu tuyến vẫn ổn định.

### D5 — Key cấp `models: ["*"]`, cô lập bằng tag, xem trước liệt kê tuyến không tag

Đây là quy ước vận hành đã chốt (key cho agent được gọi mọi model). Tag `metadata.tags = [code]` cùng `enable_tag_filtering` quyết định tuyến và khoá provider. Hệ quả phải hiện ra: key `*` cũng chạm được mọi tuyến **không mang tag** — trong config hiện tại là `gemini-flash` và `gemini-flash-preview` (dùng `KEY_GOOGLE_AI_STU`). Xem trước liệt kê các tuyến đó.

*Phương án bị loại:* giữ `models = [alias…]` — an toàn hơn nhưng trái quy ước và buộc cấp lại key mỗi khi thêm alias. *Không làm:* tự gắn tag cho tuyến legacy — đó là tuyến không thuộc quyền sở hữu của UI.

### D6 — Model cụ thể cho kiểm tra và mẫu cấu hình

Kiểm tra Gateway nhận thêm trường tuỳ chọn `test_model`. Nếu mục đầu tiên là model cụ thể thì dùng alias đó như hiện nay; nếu mọi mục là wildcard thì `test_model` bắt buộc, phải là tên gọi được thuộc provider của một mục wildcard, kiểm trước khi gửi request có phí. Mẫu cấu hình dùng alias cụ thể đầu tiên, hoặc chuỗi `<provider>/<model>` làm chỗ trống khi chỉ có wildcard.

### D7 — Giao diện: ô provider + `<datalist>` gợi ý, không thêm thư viện

Endpoint mới `GET /api/gateway-connections/catalog` (quyền admin như các đường khác) chuyển tiếp RPC `catalog` của worker, trả `{providers, models}` đã lọc theo D2. Đường này một đoạn nên trùng dạng với `GET /{code}` (`backend/connection_api.py:92`): phải khai **trước** `/{code}`, và `catalog` phải thành mã agent bị cấm trong `validate`, nếu không một agent tên `catalog` sẽ không bao giờ xem được chi tiết. Form có ô chọn provider; ô model dùng `<datalist>` gốc của trình duyệt lọc theo provider, vẫn gõ tự do được (để nhập `<provider>/*`). Nhãn bỏ chữ "Google". Lời nhắc khoá dùng chung đổi thành "dùng chung quota tài khoản provider".

### D8 — Kiểm hành vi lúc chạy bằng tuyến viết tay trong fixture

Tuyến form sinh ra không có `api_base`, nên trong mạng kín của fixture nó không tới được provider nào. Hành vi LiteLLM (key `*` được phép, tuyến `openai/*` có tag chọn đúng deployment, key tag khác bị lọc) được kiểm bằng hai tuyến `openai/*` viết tay trong `tests/gateway-connections/config.yaml` trỏ `api_base` vào provider giả, mang hai tag khác nhau. Tuyến do form sinh ra được kiểm bằng unit test của `render_routes`.

## Risks / Trade-offs

- [Key `*` chạm tuyến legacy không tag → tiền rơi vào `KEY_GOOGLE_AI_STU`] → xem trước liệt kê tuyến không tag; gắn tag cho tuyến legacy là việc riêng.
- [Tuyến wildcard + key `*` cho agent tự chọn model đắt] → hạn mức từng key là phanh duy nhất; form đã bắt chọn hạn mức hữu hạn hoặc xác nhận không giới hạn.
- [Danh mục đổi sau mỗi lần tạo lại container] → vế "đã deploy" ở D3; xem trước luôn tải mới.
- [Loại oan provider có tiền tố ngoài enum (ví dụ `aihubmix`)] → an toàn (không cho chọn thì không gọi nhầm); mở lại khi có nhu cầu thật.
- [Model mới chưa có trong danh mục LiteLLM] → dùng tuyến wildcard của provider thay cho model cụ thể.
- [Provider trên dashboard có thể ra `unknown` cho tên không tiền tố] → ngoài phạm vi, change riêng đọc `model_group`.
- [Giá model mới có thể ghi 0 trong `spend`] → không đổi; ghi nhận trong nghiệm thu.

## Migration Plan

1. Kiểm lúc chạy trên fixture (D8) trước khi sửa code; nếu key `*` hoặc tuyến wildcard có tag không hoạt động như mã nguồn cho thấy thì dừng và sửa thiết kế.
2. Triển khai backend + UI; không migration, không đổi schema.
3. Hồ sơ đã áp dụng (`dms-tap`) phải xem trước lại được mà không đổi gì.
4. Key đã cấp trước change giữ nguyên `models` cũ; chỉ key cấp mới mang `["*"]`.
5. Rollback: revert code. Tuyến wildcard đã áp dụng vẫn là YAML hợp lệ với LiteLLM; worker cũ sẽ từ chối xem trước hồ sơ đó cho tới khi sửa hồ sơ.

## Open Questions

- Có cần mở lại các tiền tố ngoài enum (`aihubmix`, `qwencloud`…) không? Cần một agent thật dùng tới mới quyết.
- LiteLLM ghi `SpendLogs.model` cho tuyến `anthropic/*` là `claude-…` hay `anthropic/claude-…`? Chỉ đo được với khoá Anthropic thật; ảnh hưởng change provider-trên-dashboard.
