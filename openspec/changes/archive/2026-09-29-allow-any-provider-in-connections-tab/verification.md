# Kiểm chứng — 2026-09-28

Áp dụng `.claude/skills/tu-soat`: tự đọc lại trước khi chạy, chạy lát mỏng (unit thuần) trước, rồi bản đầy đủ trên fixture cách ly. Không gọi provider thật, không đụng ledger thật.

## Đã chạy

| Bộ | Kết quả | Ghi chú |
|---|---|---|
| `tests/connection_config_cases.py` (unit thuần) | 18/18 | 8 test mới: danh mục, luật wildcard, mã `catalog`, tuyến wildcard một tag, chọn model thử, mẫu cấu hình |
| Fixture `connection_{config,auth,admin,migration}_cases.py` | **59 passed**, 27 subtests, 0 skip, 150 giây | Trước change: 45. Fixture `gateway-connections-test` chạy trên máy dev (Gateway dev tạm dừng vì trùng cổng 4401/4402, bật lại sau, cả hai healthy) |
| 7 test live liên quan chạy riêng `-v` | 7 PASSED | Xác nhận không bị skip im lặng |
| `probe.py` | PASS | Không đổi |
| Python stdlib `unittest discover -s tests -p "test_*.py"` | 201/201 | Khớp `EXPECTED_PY: "201"` của CI |
| JS `node --test tests/*.test.js` | 117/117 | Khớp `EXPECTED_JS: "117"` |
| `browser_check.py` (Chromium thật, HTTP giả) | PASS | Kiểm thêm: gợi ý model theo provider, không còn chữ "Google" trong form, `test_model` được gửi. Đã xem ảnh chụp màn hình |
| `openspec validate --strict` | đạt cho change này và `configure-agent-gateway-connections-from-ui` | |

## Hành vi image pin — đo lúc chạy (trước đây chỉ đọc mã nguồn)

- Key `models: ["*"]` được phép gọi tên chưa khai (`openai/any-new-model`): `auth_checks.py:3639` đúng như đọc.
- Hai tuyến `openai/*` cùng tên, khác tag: mỗi key luôn trúng đúng tuyến của tag mình (3/3 lượt mỗi key, theo header `x-litellm-model-id`); không lần nào chạm tuyến tag kia.
- Tên không có tuyến khớp tag (`anthropic/not-routed`) bị từ chối, không trả 200.
- `/public/providers`, `/public/litellm_model_cost_map` trả JSON cả khi fixture không có Internet (bảng trong image); danh mục vẫn có `gemini/gemini-2.5-flash`, `anthropic/claude-sonnet-4-5`.

## Lỗi script tự bắt được

1. `verify` so tuyến theo alias của **mục đầu tiên**; với hồ sơ chỉ wildcard, tuyến phục vụ là tuyến `<provider>/*` → sai tuyến mong đợi. Sửa: `verification_model` trả cả alias của tuyến sẽ phục vụ.
2. JS gán thẳng kết quả `/catalog`; nhận `null` thì mọi lần `fill()` sau đó sập. Sửa: kiểm dạng dữ liệu, sai thì dùng danh mục rỗng.
3. Nhãn "Model thử" chứa `<code>` bị vỡ dòng trong ảnh chụp. Sửa: chữ thường.

## Phát hiện thật (ngoài phạm vi, có từ trước)

- `browser_check.py` vẫn bấm tab **⚙ Setting**, trong khi commit `539d106` đã chuyển khung kết nối sang tab **🔗 Kết nối agent**: script hỏng từ commit đó (hết giờ ở lần đăng nhập đầu, dòng 63) và không nằm trong CI nên không ai thấy. Đã sửa trong change này (task 6.4). Vẫn chưa đưa vào CI.
- Đo danh mục trên máy dev: `litellm_provider` không phải tiền tố định tuyến (`vertex_ai-language-models`, `bedrock_converse`; 92 mục có `/` với tiền tố khác nhãn; 11 tiền tố ngoài `/public/providers`). Thiết kế D2 xử lý; ghi lại vì dễ bị hiểu sai lần sau.

## 7.2 Xem trước lại hồ sơ `dms-tap` trên máy dev — 2026-09-30

`GET /api/gateway-connections/dms-tap` rồi `POST /dms-tap/preview` (worker mở DB readonly, không ghi file,
không gọi provider). Luật "không đổi gì" đặt trước khi chạy:

| Điều kiện | Kết quả |
|---|---|
| `draft` == `applied` (revision 2, applied_revision 2) | đạt |
| tuyến preview sinh ra == `docker/gateway/config.gateway.yaml` hiện tại | đạt |
| registry preview sinh ra == `config/gateway-agents.yaml` hiện tại | đạt |

`untagged_routes` = `gemini-flash`, `gemini-flash-preview` — đúng hai tuyến không tag đã ghi trong tài liệu.

Môi trường: sau khi máy khởi động lại, `dashboard.py start` bật worker trước Postgres nên worker hết giờ
chờ (`OperationalError` mỗi vòng). Bật `token-ledger-postgres` trước rồi chạy lại thì lên.

## 7.3 Hồ sơ `gemini/*` thật trên máy dev — 2026-09-30

Hồ sơ `test-gemini-wild` (user mode single, một mục `gemini/*` → `gemini/*`, dùng lại tham chiếu khoá của
`dms-tap`). Luồng qua API tab Kết nối: lưu → xem trước (đúng 1 tuyến `gemini/*` gắn tag
`test-gemini-wild`) → áp dụng (`applied`, làm mới ledger `refresh-complete`) → cấp key `models: ["*"]`,
hạn mức 0,05 USD → Kiểm tra Gateway → thu hồi key.

| Lượt | test_model | Kết quả | Token vào/ra/tổng | Chi phí (SpendLogs) |
|---|---|---|---|---|
| 1 | `gemini/gemini-2.5-flash` | failed — Gateway HTTP 404 | 14 / 0 / 14 | 0 (failure) |
| 2 | `gemini/gemini-3.8-flash` | **verified** — "Gateway log and ledger usage match", route `connection-d6ffb71c9bede71053e7a242` | 4 / 4 / 8 | 0,000018 USD |

Cả hai key thử đã thu hồi.

Chứng minh được: key `*` + tag đi qua tuyến wildcard **do form sinh ra** (không `api_base`) tới Google
thật bằng khoá của hồ sơ — điều trước đây chỉ kiểm bằng unit `render_routes` và fixture giả.

Phát hiện thật: lượt 1 tới được Google, Google trả 404 "This model models/gemini-2.5-flash is no longer
available to new users … use models/gemini-3.8-flash" (log `token-ledger-litellm-1`). Danh mục
`/public/litellm_model_cost_map` vẫn liệt kê `gemini/gemini-2.5-flash`: danh mục không phản ánh quyền của
từng tài khoản provider, nên gợi ý model trong form có thể chọn ra model gọi không được. Chưa sửa.

Lỗi script tự bắt: chờ `status == applied` là chưa đủ — worker ghi `applied` trước khi làm mới ledger
(`reporting: awaiting-refresh`) và vẫn giữ khoá, cấp key lúc đó bị 409. Phải chờ `reporting` khác
`awaiting-refresh`.

Còn lại trên máy dev: hồ sơ và agent `test-gemini-wild` (active) trong DB, trong
`docker/gateway/config.gateway.yaml` và `config/gateway-agents.yaml`.

## Chưa chứng minh

- Tuyến wildcard do **form** sinh ra (không `api_base`) đã chạy thật với **Gemini** (xem 7.3). Với Anthropic/OpenAI vẫn chỉ kiểm bằng unit `render_routes` và tuyến viết tay có `api_base` — gọi thật cần khoá thật.
- `SpendLogs.model` cho tuyến `anthropic/*` ghi có tiền tố hay không — cần khoá Anthropic thật; ảnh hưởng change "provider trên dashboard".
