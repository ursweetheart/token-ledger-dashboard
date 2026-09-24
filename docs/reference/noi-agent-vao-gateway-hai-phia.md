# Nối một agent vào Gateway — toàn bộ những thứ phải cấu hình

Viết 23/09/2026. Mọi câu ở đây đã soát lại bằng mã nguồn đang có trong repo, không viết theo
trí nhớ. Chỗ nào chưa kiểm được thì ghi rõ là chưa kiểm.

Tài liệu này cố gắng **liệt kê đủ**: mọi biến, mọi file, mọi thao tác. Muốn biết *vì sao* từng
thứ tồn tại, đọc
[`gateway-architecture-and-agent-integration.md`](gateway-architecture-and-agent-integration.md).
Bảng đầu việc rút gọn nằm ở [`onboard-a-new-agent.md`](onboard-a-new-agent.md).

---

## 1. "Hai chiều" ở đây nghĩa là gì

Gateway **không bao giờ gọi ngược vào agent**. Không webhook, không callback. Hai chiều là hai
đường dữ liệu khác nhau:

```
   CHIEU DI  ── agent goi Gateway ──────────────────────────────────┐
                                                                    │
   agent ──▶ gateway-lb :4000 ──▶ litellm-1 / litellm-2 ──▶ Google  │
     ▲                                     │                        │
     └──── cau tra loi ve ngay ────────────┘                        │
                                           │                        │
                                           ▼                        │
                              LiteLLM_SpendLogs (database litellm)  │
                                           │                        │
   CHIEU VE  ── so lieu ve dashboard ──────┤                        │
                                           ▼                        │
                         ledger-refresh ──▶ fact_call ──▶ dashboard │
                                                                    │
   ─────────────────────────────────────────────────────────────────┘
```

| Chiều | Ai chạy | Cấu hình ở đâu |
|---|---|---|
| **Đi** — agent xin câu trả lời | agent tự gọi | mục 4 (agent) + mục 5 (Gateway) |
| **Về** — token, tiền lên dashboard | dịch vụ `ledger-refresh` tự chạy | mục 6 (dashboard) |

**Chỉ mục 4 và 5 là bắt buộc để nối.** Bỏ hẳn mục 6 thì agent vẫn gọi được, vẫn có câu trả
lời, hạn mức vẫn chặn, sổ LiteLLM vẫn ghi đủ token và tiền — chỉ riêng dashboard là hiện 0.
Khai sau rồi chạy `python db/load_gateway.py --full` là nạp lại được từ đầu, không mất dữ liệu.

---

## 2. Gom đủ 5 thứ trước khi bắt đầu

| Thứ cần | Ví dụ | Lấy ở đâu |
|---|---|---|
| Mã agent (`code`) | `dms-feedback` | Tự đặt. Chữ thường, gạch nối. Sẽ dùng làm **tag** |
| Tên hiển thị | Phân Loại Phản Hồi Tiếp Thị | Tên tiếng Việt có dấu, người đọc được |
| Project GCP | `feedback-dms-tiep-thi` | Bên quản trị Google Cloud |
| Loại người dùng | một-người-dùng **hay** nhiều người dùng | Xem bảng ở mục 4.4 |
| Khoá Google | dùng chung hay khoá riêng | Có khoá riêng thì hoá đơn Google mới tách được theo project |

Đổi mã agent giữa chừng là phải cấp lại khoá ảo và sửa lại cả ba phía. Chốt trước.

---

## 3. Điều kiện nền — Gateway phải chạy được đã

Nếu Gateway đã chạy thì bỏ qua mục này. Dựng mới thì phải điền các biến sau vào `.env` của
repo này.

### 3.1 Biến KHÔNG có giá trị mặc định — thiếu là container dừng hẳn

`docker/gateway/entrypoint.sh` kiểm 6 biến này **trước** khi LiteLLM khởi động. Thiếu một biến
thì nó in `STOP: <tên biến> is missing.` rồi thoát.

| Biến | Là gì | Lấy ở đâu |
|---|---|---|
| `LITELLM_MASTER_KEY` | khoá quản trị Gateway. **Phải bắt đầu bằng `sk-`** | `python -c "import secrets; print('sk-' + secrets.token_urlsafe(32))"` |
| `LITELLM_SALT_KEY` | khoá mã hoá Virtual Key lưu trong database | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `KEY_GOOGLE_AI_STU` | khoá Google AI Studio, dùng cho các tuyến Gemini chung | Google AI Studio |
| `KEY_CRM_FEEDBACK` | khoá Vertex express của agent 7 (tiền tố `AQ.`, 53 ký tự) | Google Cloud Console |
| `DATABASE_URL` | compose tự ghép từ `GATEWAY_PG*` | — |
| `REDIS_PASSWORD` | mật khẩu Redis dùng chung | tự đặt, mặc định `redis_local` |

> Đổi `LITELLM_SALT_KEY` = **mọi Virtual Key đã cấp đọc không ra nữa**. Sinh một lần rồi giữ
> nguyên.

### 3.2 Biến có mặc định — để trống vẫn chạy

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `GATEWAY_PGDATABASE` | `litellm` | database riêng của Gateway, **tách khỏi** database dashboard |
| `GATEWAY_PGUSER` / `GATEWAY_PGPASSWORD` | `llmproxy` / `llmproxy_local` | tài khoản ghi của Gateway |
| `GATEWAY_READONLY_USER` / `_PASSWORD` | `gateway_readonly` / `gateway_readonly_local` | vai **chỉ-đọc** cho bộ nạp dashboard |
| `REDIS_PORT` | `6379` | |
| `LLM_GATEWAY_DOMAIN` | `apigateway.rangdong.com.vn` | tên miền nginx nhận |
| `LLM_GATEWAY_EDGE_BIND` / `_PORT` | `127.0.0.1` / `8088` | cổng HTTP ra ngoài |
| `LLM_GATEWAY_TLS_BIND` / `_PORT` | `127.0.0.1` / `443` | cổng HTTPS |
| `LLM_GATEWAY_TLS_ALT_BIND` / `_PORT` | `0.0.0.0` / `8443` | cổng HTTPS phụ |
| `LLM_GATEWAY_ADMIN_CIDR` | `127.0.0.1/32` | dải IP được xem trang trạng thái |
| `LLM_GATEWAY_LAN_CIDR` | `127.0.0.1/32` | dải LAN được xem trang trạng thái |

> Trang trạng thái **không có đăng nhập**. Đừng bao giờ đặt hai dải CIDR thành `0.0.0.0/0`.
> Hai đường `/v1/chat/completions` thì không bị hai biến này chi phối — chúng chỉ kiểm khoá.

### 3.3 Bật Gateway

```bash
docker compose --profile gateway up -d
docker compose --profile gateway logs -f litellm-1
```

`docker compose up -d` (không có profile) **không** kéo Gateway lên — nó chỉ dựng dashboard.

---

## 4. Phía AGENT — làm trong repo của agent

### 4.1 Tìm đúng một chỗ gọi LLM

Mọi lượt gọi phải đi qua **một** hàm. Gọi rải rác nhiều chỗ thì gom lại trước, không thì còn
một đường lén gọi thẳng Google mà không ai biết.

### 4.2 Thêm nhánh mới, giữ nguyên nhánh cũ

Thêm backend `gateway` bên cạnh đường cũ, để đổi một biến là lùi lại được. Nhớ nới cả **danh
sách giá trị hợp lệ** của biến chọn backend (`if backend not in {...}`) — quên là app không
khởi động.

### 4.3 Gọi theo hình dạng OpenAI

```bash
curl http://gateway-lb:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-…" \
  -H "X-User: svc.dms-feedback" \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-flash-lite",
       "messages": [{"role": "user", "content": "chao"}]}'
```

| Trường | Phải là gì | Không được là gì |
|---|---|---|
| `Authorization` | **Virtual Key** `sk-…` của Gateway | khoá Google |
| `model` | **bí danh** Gateway khai, ví dụ `gemini-flash-lite` | tên upstream `gemini/gemini-3.5-flash-lite` |
| `X-User` | định danh người dùng (mục 4.4) | bỏ trống — sổ sẽ ghi chuỗi rỗng |

Tên header `X-User` do `general_settings.user_header_name` trong `config.gateway.yaml` quyết
định. **Chỉ một tên header được phép**, đổi là phải sửa cả hai phía.

Dùng thư viện HTTP **đã có sẵn** trong agent. DMS dùng `httpx` vì nó đã là phụ thuộc của tầng
web; chọn `openai` là phải sửa `requirements.txt` và dựng lại image.

**Hai hành vi của Gateway agent phải biết trước:**

| Cấu hình Gateway | Nghĩa với agent |
|---|---|
| `drop_params: true` | tham số lạ bị **bỏ im lặng**, không báo lỗi. Đừng bọc `try/except` quanh chỗ này — nó sẽ giấu đúng thứ đáng bắt |
| `turn_off_message_logging: true` | agent nhận câu trả lời **đầy đủ**, nhưng sổ chỉ lưu `redacted-by-litellm`. Cố ý |

Và phải kiểm `finish_reason`: `"length"` nghĩa là câu trả lời **bị cắt giữa chừng**, không
phải lỗi phân tích cú pháp. DMS hiện chưa kiểm trường này.

### 4.4 Chọn đúng loại định danh cho `X-User`

| Loại agent | `X-User` gửi | Bên dashboard thành |
|---|---|---|
| **Một-người-dùng** (6 trong 8 agent hôm nay) | `svc.<mã agent>` — chuỗi cố định | `account.kind = 'service_account'` |
| **Nhiều người dùng** (Trợ Lý Ảo Hợp Đồng, Trợ lý ảo Ralli) | tên đăng nhập của người đang dùng | `account.kind = 'real'` |

Gửi tên nhân viên cho một agent một-người-dùng **không** làm dữ liệu chi tiết hơn — nó làm lưu
lượng rơi khỏi chiều người dùng.

> **Agent nhiều người dùng: đọc mục 8 của [`onboard-a-new-agent.md`](onboard-a-new-agent.md)
> trước khi bắt đầu.** Hôm nay chưa có đường sẵn để nạp danh bạ người dùng của một app mới.

### 4.5 Chốt một lớp thử lại duy nhất

Gateway đã tự thử lại 3 lần (`num_retries: 3`). Agent mà cũng có vòng thử lại thì **tắt một
trong hai**. Hai lớp nhân nhau thành 9 lượt gọi thật, hoá đơn nhân theo, không ai thấy gì lạ.

### 4.6 Nối mạng

Agent và Gateway thường ở hai compose project khác nhau. Cho container agent vào mạng của
Gateway:

```yaml
services:
  web:
    networks: [default, gateway]     # PHAI liet ke ca `default`

networks:
  gateway:
    external: true
    name: token-ledger-dashboard_default
```

Viết mỗi `networks: [gateway]` là agent **rơi khỏi mạng của chính nó**, các service của nó gọi
nhau không được nữa.

> Tên mạng `token-ledger-dashboard_default` là **suy ra** theo quy tắc của Compose (tên thư
> mục + `_default`; repo không đặt `COMPOSE_PROJECT_NAME`). Chưa kiểm bằng `docker network ls`
> vì Docker trên máy này đang tắt. Kiểm một lượt trước khi dán vào compose thật.

Không dùng `host.docker.internal`: `gateway-lb` cố ý chỉ bind `127.0.0.1`, và việc container
xuyên được vào cổng chỉ-loopback thì chưa ai chứng minh.

### 4.7 `.env` của agent

Tên biến tuỳ agent. Đây là bộ của DMS, lấy làm mẫu:

```
GEMINI_BACKEND=gateway
GEMINI_MODEL=gemini-flash-lite            <- bi danh, KHONG phai ten upstream
GEMINI_API_KEY=sk-...                     <- Virtual Key, KHONG phai khoa Google
GEMINI_GATEWAY_BASE_URL=http://gateway-lb:4000
GEMINI_GATEWAY_USER=svc.dms-feedback
```

> `env_file` chỉ nạp lúc **tạo** container. Sửa `.env` rồi `restart` là không ăn — phải
> `up -d --force-recreate`.

### 4.8 Gọi từ đâu thì dùng địa chỉ nào

| Agent chạy ở đâu | Địa chỉ |
|---|---|
| Trong mạng Docker của Gateway | `http://gateway-lb:4000` — đường chính, có cân bằng tải |
| Trên chính máy chủ Gateway | `http://127.0.0.1:8088` |
| Ngoài mạng, qua tên miền | `https://apigateway.rangdong.com.vn` (443 hoặc 8443) |

**Cổng ngoài chỉ mở đúng mấy đường này** (`docker/gateway/nginx.conf`):

```
   /v1/chat/completions            mo
   /gateway/v1/chat/completions    mo (cung dich)
   /health/liveliness|readiness    mo, NHUNG tra 404 khi goi bang ten mien
   /lb-health, /edge-health        mo, de kiem nginx con song
   /app.js, /style.css, /api/status  chi cho IP trong ADMIN_CIDR / LAN_CIDR
   moi duong khac                  404
   Host la                         444 (dong ket noi, khong tra loi)
```

Nghĩa là `/key/generate`, `/spend/logs`, `/model/info`, `/v1/models` **không gọi được từ
ngoài**. Muốn gọi thì phải ở trong mạng Docker, hoặc `docker exec`.

**Giới hạn của nginx ở edge**, agent nên biết để đặt timeout cho khớp:

| Thiết lập | Giá trị |
|---|---|
| `client_max_body_size` | 25 MB |
| `proxy_connect_timeout` | 10 giây |
| `proxy_read_timeout` / `proxy_send_timeout` | 600 giây |
| chuyển sang instance kia khi lỗi | `error timeout http_502 http_503 http_504`, tối đa 2 lần |

---

## 5. Phía GATEWAY — làm trong repo này

### G1 — Khoá Google cho project của agent

Tạo khoá API trong project GCP của agent. Đặt tên biến theo mã agent:
`KEY_<MÃ_AGENT_VIẾT_HOA>`, ví dụ `KEY_CRM_FEEDBACK`.

Dùng chung khoá cũ vẫn chạy, nhưng hoá đơn Google **không tách được theo project** — mất luôn
nguồn đối chiếu độc lập với sổ của Gateway.

### G2 — `.env` và `.env.example`

Điền giá trị thật vào `.env`. Thêm một dòng **rỗng, có chú thích** vào `.env.example` để máy
khác clone repo là biết phải điền biến nào.

### G3 — `docker-compose.yml`, khối `x-litellm`

```yaml
KEY_<MÃ_AGENT>: ${KEY_<MÃ_AGENT>:-}
```

Khối này liệt kê **từng biến một**, không có `env_file`. Thiếu dòng này thì container không
thấy biến, `os.environ/KEY_…` ra rỗng, và tuyến chết im lặng cho tới lượt gọi thật đầu tiên.

### G4 — `docker/gateway/entrypoint.sh`

Thêm tên biến vào vòng kiểm (`for v in LITELLM_MASTER_KEY … ; do`).

Khoá thiếu **không** làm LiteLLM dừng: container vẫn lên, `/health/liveliness` vẫn trả 200,
Docker vẫn báo `healthy`, mà tuyến thì chết. Đúng lỗi đã sập ngày 10/09.

### G5 — `docker-compose.bench.yml`

Thêm giá trị **cố ý sai** cho đúng biến vừa thêm ở G4. Bench dùng chung `entrypoint.sh` nhưng
không được phép gọi ra ngoài. Quên bước này là **bench không lên được nữa**.

### G6 — Khai tuyến trong `docker/gateway/config.gateway.yaml`

```yaml
- model_name: <bí danh agent sẽ gọi>
  litellm_params:
    model: <tên upstream thật>
    api_key: os.environ/KEY_<MÃ_AGENT>
    rpm: 15
    tpm: 1000000
    tags: ["<mã agent>"]
```

Các tuyến đang có hôm nay:

| Bí danh agent gọi | Model upstream | Khoá | Tag |
|---|---|---|---|
| `gemini-flash` | `gemini/gemini-3.6-flash` | `KEY_GOOGLE_AI_STU` | *(không tag — không agent nào dùng)* |
| `gemini-flash-preview` | `gemini/gemini-3-flash-preview` | `KEY_GOOGLE_AI_STU` | *(không tag)* |
| `gemini-flash-lite` | `gemini/gemini-3.5-flash-lite` | `KEY_GOOGLE_AI_STU` | `dms-feedback` |
| `gemini-2.5-flash` | `gemini/gemini-2.5-flash` (Vertex express) | `KEY_CRM_FEEDBACK` | `crm-feedback` |

Bốn điều phải nhớ:

- **Đúng một tag định danh** mỗi tuyến. Hai tag thì bộ nạp gặp hai kết quả và không phân giải
  được agent nào — dòng rơi vào "nhiều tag" và **bị bỏ**.
- Tuyến **không agent nào dùng thì để trống tag**. `router.py:3292` trộn tag của *tuyến* vào
  metadata, nên ai gọi trúng tuyến đó cũng bị đóng dấu tag ấy và quy sai agent.
- Kiểm `enable_tag_filtering: true` còn trong `router_settings`. Mặc định của LiteLLM là
  **tắt**; khi tắt thì `tags` bị bỏ qua hoàn toàn, im lặng: request vẫn 200, token vẫn đúng,
  chỉ **khoá project là chọn gần như ngẫu nhiên**.
- Đặt `rpm` / `tpm` cho tuyến mới. Hạn mức này dùng chung qua Redis nên hai instance đếm chung.

> **Muốn agent gọi bằng một tên model cũ thì khai TUYẾN THẬT mang tên đó, đừng dùng
> `model_group_alias`.** Bí danh nhóm được giải **trước** và ghi đè `model`, nên tuyến thật sẽ
> không bao giờ được gọi tới — mà cột `model_group` trong sổ vẫn ghi đúng tên người gọi xin,
> nên nhìn sổ không thấy gì bất thường. Đã đo cả hai chiều ngày 09/09.

### G7 — Dựng lại hai instance

```bash
docker compose --profile gateway up -d --force-recreate litellm-1 litellm-2
```

Cấu hình chỉ đọc lúc khởi động (`store_model_in_db: false`). Sửa file mà không dựng lại là
không có gì đổi.

Xong thì cả hai phải `healthy`, và `/v1/models` phải liệt kê bí danh mới — nhớ gọi **từ trong
mạng Docker** (`http://litellm-1:4000/v1/models`), vì cổng ngoài chặn đường này.

### G8 — Cấp Virtual Key

Gọi `/key/generate` **từ trong mạng Docker** hoặc bằng `docker exec`, kèm master key:

Gọi từ bên trong container để `$LITELLM_MASTER_KEY` giãn nở ở đó — không phải chép khoá quản
trị ra ngoài. Dùng `python` chứ không `curl`: healthcheck của chính container đã chứng minh
`python` có sẵn, còn `curl` thì chưa ai kiểm.

```bash
docker exec token-ledger-litellm-1 python -c "
import json, os, urllib.request
body = json.dumps({'key_alias': '<mã agent>-tagged',
                   'models': ['<bí danh>'],
                   'metadata': {'tags': ['<mã agent>']}}).encode()
req = urllib.request.Request('http://127.0.0.1:4000/key/generate', data=body,
        headers={'Authorization': 'Bearer ' + os.environ['LITELLM_MASTER_KEY'],
                 'Content-Type': 'application/json'})
print(urllib.request.urlopen(req, timeout=10).read().decode())
"
```

| Trường | Giá trị | Ghi chú |
|---|---|---|
| `metadata.tags` | `["<mã agent>"]` | **đúng chỗ này**, không phải trường `tags` cấp cao |
| `models` | danh sách bí danh được phép gọi | để trống là cho gọi tự do |
| `key_alias` | `<mã agent>-tagged` | tên để tra trong sổ |

Ba cái bẫy, cả ba đều im lặng:

- **Tag phải nằm trong `metadata`.** Bảng khoá của LiteLLM **không có cột `tags`**; khai nhầm
  chỗ thì không có tác dụng và không ai báo.
- **Chép ngay chuỗi `sk-…` ra chỗ an toàn.** LiteLLM chỉ lưu hash. Quên chép là mất vĩnh viễn
  — sửa metadata của khoá đó cũng vô nghĩa vì không ai còn biết khoá là gì. Phải cấp khoá mới.
- Sửa khoá sau này bằng `/key/update` thì **đọc metadata hiện có rồi gửi lại đầy đủ**: lệnh đó
  **thay thế** cả cục `metadata`, gửi thiếu là xoá mất `tags`.

### G9 — Hạn mức

Toàn bộ biến hạn mức, tất cả đều trong `.env` của repo này:

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `QUOTA_DRY_RUN` | `1` trong `.env.example`, **`0` trong `.env` hôm nay** | `1` = chỉ ghi nhận, cho mọi request đi qua. `0` = **chặn thật** |
| `QUOTA_CHAT_TAGS` | `contact-center,sale-agent,tla-hd,ralli` | danh sách agent **có người ngồi đọc** |
| `QUOTA_BLOCK_MESSAGE` | câu mặc định trong `quota_hook.py` | câu người dùng cuối đọc khi bị chặn |
| `QUOTA_WATCH_EVERY_SECONDS` | `300` | nhịp kiểm của dịch vụ `quota-watch` |
| `QUOTA_DISABLED` | rỗng | `1` = tắt hẳn hai endpoint hạn mức của backend |
| `GATEWAY_BASE_URL` | `http://litellm-1:4000` | địa chỉ backend gọi để sửa hạn mức. **Thẳng vào litellm**, không qua `gateway-lb` |
| `LITELLM_MASTER_KEY` | — | backend cần để ghi `metadata` của khoá. Thiếu thì **backend không khởi động**, trừ khi `QUOTA_DISABLED=1` |

**Khai agent vào `QUOTA_CHAT_TAGS` hay không quyết định nó nhận gì khi hết tiền:**

| Loại | Khi hết hạn mức, agent nhận |
|---|---|
| có người ngồi đọc (mã agent **có** trong danh sách) | HTTP 200 kèm **một câu thông báo** thay cho câu trả lời |
| chạy theo lô (**không** có trong danh sách) | lỗi mang mã **429**, app tự lùi |

Hai agent phân loại đang đợi JSON — một câu văn xuôi đi vào đó sẽ vỡ lúc phân tích và báo
thành lỗi JSON, người vận hành đi tìm bệnh sai chỗ.

> **Viết lại cả dòng, không phải thêm vào.** Hôm nay `.env` **không có dòng `QUOTA_CHAT_TAGS`
> nào** — nó đang ăn giá trị mặc định, khai ở hai chỗ (`docker-compose.yml` khối `x-litellm`,
> và `_DEFAULT_CHAT_TAGS` trong `quota_hook.py`). Viết một dòng `QUOTA_CHAT_TAGS=` vào `.env`
> là **đè cả hai**, nên phải kê lại đủ bốn mã cũ rồi mới thêm mã mới.

**Đặt hạn mức USD cho khoá vừa cấp** ở tab **⚙ Setting** trên dashboard. Backend ghi con số đó
vào `metadata.quota_usd` của chính virtual key. Không đặt thì agent đó **không bao giờ bị
chặn** — không lỗi nào báo, nó chỉ nằm ngoài cơ chế giữ tiền.

---

## 6. Phía DASHBOARD — để chiều về nhìn thấy agent

> **Cập nhật Gateway-only:** agent mới chỉ sửa `config/gateway-agents.yaml`,
> chạy dry-run → apply → refresh theo [runbook](gateway-agent-registration.md).
> Không cần crawl/export users, billing hay monitoring. Không chạy generator,
> `load_org.py` hay rebuild cho workflow này. `multiple` tự nhận identity từ log,
> `single` dùng `svc.<code>`. YAML chỉ tác động dashboard, không cấp Gateway key.
>
> **D1–D5 bên dưới là ghi chép legacy**, không phải lệnh onboarding Gateway-only
> hiện tại. Đặc biệt các lệnh rebuild không còn an toàn với pricing/registry.

Không bắt buộc để nối (xem mục 1). Nhưng thiếu thì dashboard hiện 0.

### D1 — Thêm agent vào danh mục — **chỗ duy nhất thật sự bắt buộc**

Thêm một dòng vào `AGENTS` trong `db/gen_catalog.py`. Tám trường, đúng thứ tự:

```python
(9, "ma-agent", "Tên Hiển Thị", "project-gcp", False, "2026-09-23", True, True)
#  │      │            │              │           │         │          │     │
#  │      │            │              │           │         │          │     └─ co so tu Google Cloud
#  │      │            │              │           │         │          └─ dang chay
#  │      │            │              │           │         └─ ngay tao project
#  │      │            │              │           └─ co cay to chuc (danh ba nguoi dung)
#  │      │            │              └─ project GCP
#  │      │            └─ ten hien thi, tieng Viet co dau
#  │      └─ ma agent = TAG
#  └─ agent_id
```

Có hạn mức USD thì thêm một dòng vào `BUDGET_USD` ngay dưới — dict này khoá bằng **tên hiển
thị**, không phải mã agent. Rồi chạy `python db/gen_catalog.py` để sinh lại `db/02_catalog.sql`.

Vì sao bắt buộc: `db/load_gateway.py:390` tra tag của request ra agent bằng cách so với
`dim_agent.code`. Không khớp dòng nào thì `resolve_agent()` trả `None`, và vì `fact_call.agent_id`
là `NOT NULL` nên **dòng bị bỏ** (đếm vào `dropped_no_tag`).

> **Chạy lại script KHÔNG đưa được dòng mới vào database.** `db/02_catalog.sql` chỉ vào
> database qua `connect.rebuild()`, mà bước đó `TRUNCATE` mọi bảng dữ liệu rồi nạp lại. Nghĩa
> là thêm một agent = chạy `scripts/rebuild_db.py`, **dựng lại cả database**. Dịch vụ
> `ledger-refresh` không đi qua cửa đó.

### D2 — Khai loại người dùng trong `db/load_org.py`

Thêm `agent_id` mới vào `SINGLE_USER_AGENTS` (dòng 85) nếu là agent một-người-dùng.

Đây là một trong số **ít** việc hỏng **to**: thiếu nó thì bước 2 của `rebuild_db.py` chết với
`KeyError` ở `load_org.py:615`. Nên nó chặn ngang D1.

### D3 — Model: nay **tự khai**, không phải sửa tay nữa

Từ 19/09/2026, `auto_register_models()` trong `db/load_gateway.py` tự thêm model upstream lạ
vào `dim_model` + `dim_model_alias` khi nó xuất hiện trong sổ với lượt gọi thành công.

Nghĩa là **bỏ bước này vẫn chạy được**. Nhưng:

- `family` / `provider` của model tự khai chỉ là **suy đoán từ tiền tố** nhà cung cấp, chưa ai
  review. Muốn tên chuẩn thì khai tay vào `rules.GATEWAY_MODELS` rồi chạy `gen_catalog.py`.
- Khai tay thì để ý `MODEL_PATTERNS` xếp **mẫu dài trước**. Thiếu mẫu dài thì model bị gán
  nhầm sang model khác — khác đơn giá, và **vẫn báo là tìm thấy**.
- `cost_usd` không phụ thuộc bước này: tiền lấy thẳng từ `metadata.cost_breakdown` của LiteLLM.

### D4 — Kiểm tài khoản dịch vụ

Sau lượt nạp đầu, với agent một-người-dùng, `svc.<mã agent>` phải ra **đúng một** dòng
`kind = 'service_account'`.

`X-User` gửi chuỗi không khớp quy ước thì bộ nạp **từ chối** định danh đó, cộng vào bộ đếm
`identity_unresolvable`, rồi dồn lưu lượng về tài khoản neo mức agent. Tổng token vẫn đúng;
chỉ riêng chiều người dùng lệch.

> **Luật tra định danh vừa đổi, và bản đổi CHƯA commit** (nhánh `Tuan-develop`, 21/09/2026).
> Luật cũ hỏi *"tài khoản này thuộc về agent nào"* rồi đem so — người dùng hai agent chỉ thuộc
> về một bên nên mọi request qua bên kia đều trượt. Luật mới hỏi *"định danh này có mặt trong
> danh bạ của agent đang gửi không"*, tra bằng khoá đôi `(agent_id, tên đăng nhập)` và chuẩn
> hoá `LOWER(TRIM())` ở cả hai đầu. **Chỉ ảnh hưởng agent nhiều người dùng.**

### D5 — Bật dịch vụ tự nạp

```bash
docker compose --profile refresh up -d
```

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `REFRESH_EVERY_SECONDS` | `300` | nhịp chạy lại bộ nạp |
| `GATEWAY_DSN` | dựng từ `GATEWAY_READONLY_*` | kết nối **chỉ-đọc** sang database `litellm` |

Không bật thì dashboard **không tự cập nhật**, và không có dấu hiệu nào báo là đang cũ. Chạy
tay một lượt: `python scripts/refresh_gateway.py`.

> **Đừng chạy tay trong lúc dịch vụ đang chạy.** `build_usage_daily.py` xoá sạch bảng rồi dựng
> lại; hai lượt chồng nhau là nguy hiểm. Muốn chạy tay thì `docker stop token-ledger-refresh`
> trước.

---

## 7. Những thứ KHÔNG phải cấu hình cho mỗi agent

Dựng một lần, dùng chung cho mọi agent. Nối agent mới **không** phải đụng vào:

| Thành phần | Vai trò |
|---|---|
| Redis primary + replica + 3 Sentinel | giữ bộ đếm `rpm`/`tpm` dùng chung và cache khoá cho cả hai instance |
| `gateway-lb` (nginx) | cân bằng tải, chặn đường, kết thúc TLS |
| Chứng chỉ TLS trong `docker/gateway/tls/` | `.crt`/`.key` **không lên git**, xem README trong thư mục đó |
| `gateway-db-init`, `gateway-readonly-init` | tạo database `litellm` và vai chỉ-đọc |
| `gateway-status`, `gateway-watch` | trang trạng thái và gửi thư khi Gateway đổi trạng thái |
| `quota_hook.py` | hook hạn mức, chạy cho **mọi** agent |

---

## 8. Nghiệm thu — bốn phép đo, theo thứ tự

| # | Đo gì | Đạt là |
|---|---|---|
| 1 | Gọi 10 lượt thật từ agent | 10/10 HTTP 200 |
| 2 | Đếm dòng mới trong sổ Gateway | đúng 10 dòng, `total_tokens > 0`, `spend > 0`, số lần thử lại = 0 |
| 3 | **Phép kiểm âm** cho tag | dựng một tuyến mồi cùng bí danh, mang `tags: ["khong-ai-dung"]` và khoá cố ý sai → **0 lần chạm** tuyến mồi. Xong thì **gỡ tuyến mồi và dựng lại** |
| 4 | Chạy bộ nạp một lượt bằng tay | không dòng nào bị bỏ, dashboard hiện số |

**Đừng lấy "gọi thử thấy chạy" làm bằng chứng.** Đo ngày 31/08 trên 8 lượt gọi thiếu tag:
**7/8 thành công, 1/8 trượt**. Hỏng lác đác 12,5% qua được mọi lần thử tay. Phép đo 3 là phép
duy nhất chứng minh được tag lọc đúng, vì sổ **không** ghi lại quyết định định tuyến.

Và nhớ: `ledger-refresh` chạy bộ nạp với đầu ra bị nuốt khi thành công. Lần đầu **phải chạy
tay một lượt** mới đọc được các bộ đếm.

---

## 9. Lùi lại

| Muốn | Làm |
|---|---|
| Tạm ngắt agent khỏi Gateway | đổi biến backend trong `.env` của agent, `up -d --force-recreate` |
| Thu hồi quyền gọi | xoá Virtual Key **qua API của proxy** — mất hiệu lực ngay. Xoá thẳng bằng SQL thì khoá còn sống thêm tối đa 5 phút (`user_api_key_cache_ttl: 300`) |
| Gỡ tuyến | xoá khối tuyến trong `config.gateway.yaml`, dựng lại hai instance |
| Gỡ khỏi dashboard | **không gỡ.** Số cũ phải giữ. Đặt agent thành không còn chạy, đừng xoá dòng |

---

## 10. Bảng tra tổng — mọi chỗ phải chạm

| Phía | Chỗ | Mục | Bắt buộc? |
|---|---|---|---|
| Agent | chỗ gọi LLM | 4.1–4.3 | có |
| Agent | danh sách giá trị cấu hình hợp lệ | 4.2 | có |
| Agent | compose / override — nối mạng | 4.6 | có |
| Agent | `.env` | 4.7 | có |
| Gateway | `.env`, `.env.example` | G2 | có |
| Gateway | `docker-compose.yml` (khối `x-litellm`) | G3 | có nếu dùng khoá riêng |
| Gateway | `docker/gateway/entrypoint.sh` | G4 | có nếu dùng khoá riêng |
| Gateway | `docker-compose.bench.yml` | G5 | có nếu đã sửa G4 |
| Gateway | `docker/gateway/config.gateway.yaml` | G6 | có |
| Gateway | `/key/generate` (không phải file) | G8 | có |
| Gateway | `.env` — `QUOTA_CHAT_TAGS` | G9 | nên |
| Gateway | tab ⚙ Setting trên dashboard | G9 | nên |
| Dashboard | `db/gen_catalog.py` — `AGENTS`, `BUDGET_USD` | D1 | có, để thấy số |
| Dashboard | `db/load_org.py` — `SINGLE_USER_AGENTS` | D2 | có, nếu đã làm D1 |
| Dashboard | `db/rules.py` | D3 | tuỳ chọn từ 19/09 |
| Dashboard | chạy `scripts/rebuild_db.py` một lượt | D1 | có, nếu đã làm D1 |
| Dashboard | `docker compose --profile refresh up -d` | D5 | nên |

**Bốn chỗ bỏ sót sẽ báo lỗi to**, còn lại **hỏng im lặng**:

| Bỏ sót | Triệu chứng |
|---|---|
| danh sách cấu hình hợp lệ của agent | app của agent không khởi động |
| `docker-compose.bench.yml` (G5) | bench không lên được |
| Virtual Key (G8) | không có khoá thì không gọi được |
| `SINGLE_USER_AGENTS` (D2) | `KeyError`, bước 2 của `rebuild_db.py` dừng |

Không thấy lỗi nào **không** có nghĩa là đã làm đủ.
