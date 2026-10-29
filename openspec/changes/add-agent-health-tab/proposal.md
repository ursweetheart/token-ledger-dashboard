## Why

Hiện không có gì kiểm mỗi ngày xem **agent** còn trả lời được không. `gateway-watch` chỉ canh Gateway.
Nếu Trợ lý ảo Ralli chết, hoặc key partner hết hạn, hoặc luồng gọi model hỏng, thì chỉ biết khi người
dùng kêu. Cần một phép kiểm tự động, chạy vào giờ người vận hành chọn (giờ VN), và kết quả nằm trên
dashboard.

Làm Ralli trước để có baseline. Tài liệu API của các agent khác sẽ có sau, nên **thêm agent phải là
thêm cấu hình, không phải viết code**.

## What Changes

- **Service mới `agent-health-watch`** (profile `gateway`, image `token-ledger-tools:local`, theo khuôn
  `gateway-watch`). Vòng lặp 5 giây. Mỗi vòng đọc giờ chạy từ DB. Nếu giờ VN đã qua giờ chạy mà hôm
  nay chưa chạy thì chạy một lần, kể cả chạy bù khi container lên trễ. Mỗi vòng cũng nhận các lần
  "Chạy ngay" đang chờ.
- **Nút "Chạy ngay"**: gọi ngay mọi phép kiểm, độc lập với lịch. Lần chạy tay không làm mất lần chạy
  theo lịch của ngày hôm đó. Một thanh ngang hiện % số phép kiểm đã xong và phép kiểm đang chạy. Cần
  khoá quản trị. Trong lúc đang có một lần chạy thì không bấm chồng được.
- **File `config/agent-health.yaml`**: mỗi agent khai `base_url`, tên biến chứa key, và danh sách phép
  kiểm HTTP (method, path, body, điều kiện đạt). Code không biết tên agent nào.
- **Baseline Trợ lý ảo Ralli** (Rạng Đông Partner API, xác thực `X-API-Key`, biến `RALLI_PARTNER_KEY`):
  - `GET /capabilities`: HTTP 200, feature `ctda` có `enabled: true`, `expires_at` còn hơn 30 ngày.
  - `POST /ctda/v2/analyze`: một lần trong mỗi lần chạy, câu "Phân tích ngắn tình hình chăm sóc công trình dự án
    tháng này". Đạt khi HTTP 200 và `status == "success"`. Có thêm điều kiện tuỳ chọn
    `data.feature != "clarification"`.
- **Đối chiếu log Gateway là tuỳ chọn theo agent** (`gateway_tag`). Ralli chưa đi qua Gateway nên tắt.
- **Migration `016_agent_health.sql`**: `agent_health_setting` (một dòng: giờ chạy, ngày chạy theo lịch
  gần nhất) và `agent_health_run` (mỗi lần chạy: theo lịch hay chạy tay, trạng thái, tiến độ, và cột
  `result jsonb` chứa tài liệu kết quả). Hai bảng vào `KEEP_ON_REBUILD`.
- **Tệp `var/agent-checks/<run_id>/result.json`**: cùng tài liệu đó, ghi khi lần chạy xong, cho module
  chụp màn hình (`kiem-tra-agent-hang-ngay.md`, Module 2) đọc. Khuôn ở
  `docs/reference/agent-health-result.md`. Người dùng chốt 29/10/2026: lưu cả DB lẫn tệp, giữ câu hỏi
  và nguyên response của câu hỏi làm bằng chứng.
- **API**: `GET /api/agent-health` và `GET /api/agent-health/runs/{id}` (chứng danh dashboard, chỉ đọc);
  `PUT /api/agent-health/schedule` và `POST /api/agent-health/run` (khoá quản trị kết nối, ghi qua vai
  `connection_admin`).
- **Tab mới "🩺 Sức khỏe Agent"**: ô giờ, nút Apply, nút Chạy ngay, thanh tiến độ, bảng kết quả lần
  chạy gần nhất. Người dùng đã cho phép thêm tab này ngày 29/10/2026.

**Đã thử với hệ thống thật ngày 29/10/2026** (không phải giả định):

| Gọi | Kết quả |
|---|---|
| `GET /capabilities` | 200; tài khoản `admin`; có `action:ctda`; feature `ctda` bật; hết hạn 2027-10-28 |
| `POST /ctda/v2/analyze` với `"hello"` | 200 sau 0,19 s, `data.feature = "clarification"`, nên câu chào không đi tới LLM |

**Không làm, có chủ ý:**

- Không có `/health` ở Ralli: đã đếm 50 path trong `openapi.json` gốc. `/capabilities` thay vào chỗ đó.
- Không gửi thư khi lỗi. Thêm sau bằng `send_mail` của `scripts/watch_gateway.py` khi có yêu cầu.
- Không có cú pháp cron, không nhiều lịch chạy, không biểu đồ lịch sử. Bảng kết quả giữ đủ lịch sử để
  vẽ sau.
- Không gọi endpoint ghi nào khác của Ralli. Ngoại lệ chỉ áp cho `POST /ctda/v2/analyze`: một lần theo
  lịch mỗi ngày, cộng một lần cho mỗi lần bấm "Chạy ngay". Người dùng chốt 29/10/2026, dự kiến 1–3 lần
  mỗi ngày (lịch, khi có lỗi, sau khi sửa lỗi). Không đặt trần số lần bấm. Khoá quản trị và chặn bấm
  chồng là đủ.
- Thanh tiến độ không chạy đều giả theo thời gian. Nó đếm số phép kiểm đã xong.

## Capabilities

### New Capabilities

- `agent-health-monitoring`: Phép kiểm sức khỏe agent khai bằng cấu hình, chạy mỗi ngày đúng giờ VN
  do người vận hành đặt trên dashboard, lưu kết quả từng phép kiểm và hiển thị trong tab riêng.

### Modified Capabilities

(không có — endpoint mới tuân theo `api-access-control` hiện có, không đổi yêu cầu nào)

## Impact

| Vùng | Việc |
|---|---|
| `scripts/watch_agents.py` | tệp mới, chỉ dùng thư viện chuẩn + `psycopg2` + `yaml` đã có trong image |
| `config/agent-health.yaml` | tệp mới, có khối Ralli |
| `db/migrations/sql/016_agent_health.sql` | ba bảng, gieo một dòng setting, GRANT cho `connection_admin` |
| `db/connect.py` | thêm ba bảng vào `KEEP_ON_REBUILD` |
| `backend/store.py`, `backend/main.py` | `GET /api/agent-health`, `GET /api/agent-health/runs/{id}` |
| `backend/connection_api.py` | `PUT /api/agent-health/schedule`, `POST /api/agent-health/run`, dùng chung `authorize()` |
| `docker-compose.yml` | service `agent-health-watch` |
| `.env.example` | `RALLI_PARTNER_KEY=` |
| `web/index.html`, `web/js/api.js`, `web/js/agent-health.js` | tab mới |

**Phụ thuộc:** nút Apply và Chạy ngay chỉ chạy khi quản trị kết nối đã bật (`CONNECTIONS_ENABLED=1`). Tắt
thì tab vẫn hiện kết quả, hai nút báo 503.

**Rủi ro đã biết:** key partner hiện gắn tài khoản `admin` và có đủ 11 quyền, kể cả `chat:ask` (mở được
`DELETE /conversations/{id}`). Token của lần kiểm hằng ngày sẽ tính cho `admin`. Nên xin một key chỉ
có `action:ctda`; khi đó chỉ đổi `.env`.
