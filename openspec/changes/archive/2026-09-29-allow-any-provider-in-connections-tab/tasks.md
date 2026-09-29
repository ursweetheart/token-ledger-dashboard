## 1. Kiểm hành vi LiteLLM lúc chạy (trước khi sửa code)

- [x] 1.1 Thêm vào `tests/gateway-connections/config.yaml` hai tuyến `model_name: "openai/*"`, `model: "openai/*"`, `api_base` trỏ provider giả, một tuyến tag `test-wild`, một tuyến tag `wrong-wild` với `model_info.id` khác nhau
- [x] 1.2 Test live: key `models: ["*"]` + tag `test-wild` gọi `openai/bat-ky-ten-nao` → 200 và header `x-litellm-model-id` là id của tuyến `test-wild`; key tag `wrong-wild` → id tuyến `wrong-wild`; không lần nào chạm tuyến của tag kia
- [x] 1.3 Test live: key `models: ["*"]` gọi tên không có tuyến nào khớp tag (ví dụ `anthropic/x`) → lỗi, không 200
- [x] 1.4 Test live: `/public/providers` và `/public/litellm_model_cost_map` của instance fixture trả JSON (fixture không có Internet → bảng từ bản trong image); nếu 1.2–1.4 trái mã nguồn thì dừng và sửa design

## 2. Danh mục từ Gateway

- [x] 2.1 `Gateway.call`: thêm `/public/providers`, `/public/litellm_model_cost_map` vào danh sách đường cho phép, gọi GET không gửi thân
- [x] 2.2 Hàm thuần `routable_catalog(cost_map, providers)` trong `backend/connection_config.py` theo D2: chỉ mục `mode: chat`; key có `/` giữ nguyên, không có `/` ghép `litellm_provider/`; loại provider không có trong `providers`; trả `{providers: [...], models: {provider: [tên…]}}` đã sắp
- [x] 2.3 Unit test `routable_catalog` bằng dữ liệu mẫu: `claude-haiku-4-5`/`anthropic` → `anthropic/claude-haiku-4-5`; `gemini-2.5-flash`/`vertex_ai-language-models` bị loại; `amazon-nova/…` bị loại; mục `mode: embedding` bị loại; thân không phải object → lỗi
- [x] 2.4 `Worker.catalog()` tải hai API từ instance đầu tiên và gọi `routable_catalog`; lỗi mạng/HTTP/dạng dữ liệu → `RuntimeError`, không trả danh mục rỗng

## 3. Kiểm model khi lưu nháp và khi xem trước

- [x] 3.1 `connection_config.validate`: bỏ luật `startswith('gemini/')`; upstream phải là `<provider>/*` hoặc `<provider>/<model>`; cấm `*` trần và `*` ở chỗ khác; wildcard thì alias = upstream; giữ tập ký tự cũ
- [x] 3.2 `validate`: cấm mã agent `catalog` (tránh đè route `GET /{code}`)
- [x] 3.3 Cập nhật `tests/connection_config_cases.py`: nhận `anthropic/*`; từ chối `*`, `gemini/*-flash`, `foo/*`→`anthropic/*`, mã `catalog`; model cụ thể không phải Gemini lưu được
- [x] 3.4 `Worker.preview`: thay đoạn `allowed` (`connection_worker.py:233-241`) bằng kiểm theo danh mục — provider ∈ danh mục; model cụ thể ∈ tên gọi được **hoặc** đã là upstream trong config đang chạy; không còn đọc `ref_model_catalog`
- [x] 3.5 Test xem trước: `antropic/*` bị từ chối; `anthropic/claude-haiku-4-5` được nhận; upstream đã deploy vắng khỏi danh mục vẫn được nhận; danh mục lỗi → xem trước lỗi, không ghi file
- [x] 3.6 Test `render_routes`: mục wildcard sinh tuyến `model_name`/`model` = `anthropic/*`, tag đúng một mã agent, `model_info.id` = `route_id(code, alias)`

## 4. Key `*` và tuyến không tag

- [x] 4.1 `Worker.issue`: cấp key với `models: ["*"]` thay cho danh sách alias; giữ `metadata.tags = [code]`
- [x] 4.2 `Worker.preview`: thêm vào kết quả danh sách `untagged_routes` — tên các tuyến trong config đang chạy không có `tags`
- [x] 4.3 Test: key cấp ra có `models == ["*"]` và tag đúng; xem trước với config fixture chứa tuyến không tag liệt kê đúng tên đó

## 5. Model cụ thể cho kiểm tra và mẫu cấu hình

- [x] 5.1 Hàm thuần chọn model thử: mục đầu là model cụ thể → alias đó; chỉ có wildcard → bắt buộc `test_model`, phải là tên gọi được thuộc provider của một mục wildcard
- [x] 5.2 API `POST /{code}/verify` nhận trường tuỳ chọn `test_model` và chuyển qua RPC `verify` (hiện RPC chỉ nhận đúng `{operation_id, virtual_key}`, `connection_worker.py:825` — phải mở thêm trường này); worker kiểm theo 5.1 **trước** khi gửi request có phí; sai → lỗi 422, không có request tới Gateway
- [x] 5.3 `integration_template`: dùng alias cụ thể đầu tiên; chỉ có wildcard → `GATEWAY_MODEL=<provider>/<model>`
- [x] 5.4 Test: hồ sơ chỉ `anthropic/*` không có `test_model` → từ chối, `gateway.call` không được gọi; `test_model` thuộc provider khác → từ chối; mẫu cấu hình không chứa `*`

## 6. API và giao diện

- [x] 6.1 `GET /api/gateway-connections/catalog` khai trước `GET /{code}`, quyền admin, chuyển tiếp RPC `catalog`; worker lỗi → 503 kèm thông báo
- [x] 6.2 `web/index.html`: đổi nhãn "Tham chiếu Google key", "Google API key mới", "Model Google" thành nhãn chung; thêm ô chọn provider; ô model dùng `<datalist>`; thêm ô "Model thử" cạnh nút Kiểm tra Gateway
- [x] 6.3 `web/js/gateway-connections.js`: tải danh mục sau khi mở quản trị; lọc gợi ý theo provider; gửi `test_model` khi có; lời nhắc khoá dùng chung đổi thành "tài khoản provider"; hiện `untagged_routes` trong bản xem trước
- [x] 6.4 Cập nhật `tests/gateway-connections/browser_check.py` cho nhãn và ô mới; chạy lại

## 7. Nghiệm thu và tài liệu

- [x] 7.1 Chạy bộ Python stdlib, bộ JS, bộ fixture `connection_*_cases.py`; ghi số đạt vào `verification.md` của change này
- [x] 7.2 Máy dev: xem trước lại hồ sơ `dms-tap` không đổi gì (hồ sơ đã áp dụng không bị danh mục mới làm hỏng)
- [x] 7.3 Máy dev: tạo hồ sơ tập dùng `gemini/*`, áp dụng, cấp key, Kiểm tra Gateway với `test_model` Gemini cụ thể → verified; ghi token/chi phí
- [x] 7.4 Sửa spec của change `configure-agent-gateway-connections-from-ui` trước khi archive: bỏ "explicit model aliases", kịch bản "wildcard alias" bị từ chối, "model-restricted … Virtual Keys" trong `gateway-connection-management`, trỏ sang `gateway-connection-providers`
- [x] 7.5 Cập nhật `docs/reference/gateway-connection-management.md` và `dashboard-setup.md`: provider bất kỳ, tuyến wildcard, key `*` chạm tuyến không tag, hạn mức là phanh duy nhất
- [x] 7.6 `openspec validate allow-any-provider-in-connections-tab --strict` đạt
