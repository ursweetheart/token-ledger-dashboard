# Nối một agent mới vào Gateway — bảng việc phải làm

Viết 19/09/2026, soát lại 21/09/2026. Đây là **bảng đầu việc** để dùng khi làm, không phải
tài liệu giải thích. Muốn biết *vì sao* mỗi việc tồn tại, đọc
[`gateway-architecture-and-agent-integration.md`](gateway-architecture-and-agent-integration.md).

Mỗi đầu việc có ba dòng: **Làm gì** · **Xong khi** · **Bỏ qua thì**. Dòng thứ ba quan trọng
nhất: gần như mọi việc trong bảng này, thiếu nó thì hệ thống **vẫn chạy, vẫn trả 200**, chỉ
có số liệu là sai.

> **PHẠM VI — đọc trước khi bắt đầu.** Bảng này chỉ đủ cho agent **một-người-dùng**. Agent
> nhiều người dùng cần thêm một khâu nạp danh bạ mà hôm nay **chưa có đường sẵn** — xem
> mục 8. Đừng chạy theo bảng này rồi mới phát hiện ra điều đó ở việc C3.

---

## 0. Gom đủ 5 thứ trước khi bắt đầu

| Thứ cần | Ví dụ | Lấy ở đâu |
|---|---|---|
| Mã agent (`code`) | `dms-feedback` | Tự đặt, chữ thường, gạch nối. Sẽ dùng làm tag |
| Tên hiển thị | Phân Loại Phản Hồi Tiếp Thị | Tên người đọc được, tiếng Việt có dấu |
| Project GCP | `feedback-dms-tiep-thi` | Bên quản trị Google Cloud |
| Loại người dùng | một-người-dùng **hay** nhiều người dùng | Xem bảng ở việc A5 |
| Khoá Google | dùng chung `KEY_GOOGLE_AI_STU` hay khoá riêng | Có khoá riêng thì hoá đơn mới tách được theo project |

> Chưa có đủ 5 thứ thì **đừng bắt đầu**. Đổi `code` giữa chừng là phải cấp lại khoá và sửa
> lại cả ba nơi.

---

## 1. Việc ở phía AGENT

Bảy đầu việc. Làm trong repo của agent, không đụng gì tới repo này.

### A1 — Tìm chỗ agent gọi nhà cung cấp

- **Làm gì:** tìm **một** hàm duy nhất mà mọi lượt gọi LLM đều đi qua. Gọi rải rác nhiều chỗ
  thì gom lại trước.
- **Xong khi:** chỉ ra được đúng một file, một hàm.
- **Bỏ qua thì:** còn đường gọi thẳng Google mà không ai biết, và sổ thiếu token mãi mãi.

### A2 — Thêm một backend mới, không sửa backend cũ

- **Làm gì:** thêm nhánh `gateway` bên cạnh các nhánh sẵn có. Giữ nguyên đường cũ.
- **Xong khi:** đổi một biến môi trường là quay lại đường cũ được.
- **Bỏ qua thì:** không có đường lùi. Gateway hỏng là agent chết theo.

### A3 — Nới danh sách trắng cấu hình

- **Làm gì:** tìm chỗ app liệt kê các giá trị hợp lệ của biến chọn backend, thêm `gateway`
  vào.
- **Xong khi:** app khởi động được ở chế độ mới.
- **Bỏ qua thì:** app **không khởi động**, và có app còn nuốt lỗi rồi vẫn báo khởi động xong.

### A4 — Gọi bằng hình dạng OpenAI

- **Làm gì:**
  ```
  POST {base_url}/v1/chat/completions
  Authorization: Bearer sk-…
  X-User: <định danh>
  {"model": "<bí danh>", "messages": [...]}
  ```
  Dùng thư viện HTTP **đã có sẵn** trong agent, không thêm phụ thuộc mới.
- **Xong khi:** gọi thử trả về 200 và bóc được nội dung.
- **Bỏ qua thì:** thêm phụ thuộc mới là phải dựng lại image, việc nhỏ thành việc to.

### A5 — Chọn đúng loại định danh cho `X-User`

| Loại agent | `X-User` gửi | Bên dashboard |
|---|---|---|
| **Một-người-dùng** (6 trong 8 agent) | `svc.<code>` — chuỗi cố định | `account.kind = 'service_account'` |
| **Nhiều người dùng** (Trợ Lý Ảo Hợp Đồng, Trợ lý ảo Ralli) | tên người đăng nhập | `account.kind = 'real'` |

- **Xong khi:** chuỗi gửi đi khớp đúng một trong hai dạng trên.
- **Bỏ qua thì:** gửi tên nhân viên cho một agent một-người-dùng sẽ làm lưu lượng **rơi khỏi
  chiều người dùng** thay vì gộp vào tài khoản dịch vụ.

### A6 — Chốt một lớp thử lại duy nhất

- **Làm gì:** Gateway đã tự thử lại 3 lần. Nếu agent cũng có vòng thử lại thì **tắt một
  trong hai**.
- **Xong khi:** một request hỏng sinh ra nhiều nhất 3 lượt gọi thật tới Google, không phải 9.
- **Bỏ qua thì:** hai lớp nhân nhau, hoá đơn nhân theo, và không ai thấy gì bất thường.

### A7 — Nối mạng và điền `.env` của agent

- **Làm gì:** cho container của agent vào mạng của Gateway (`networks.external`), và **luôn
  liệt kê cả mạng mặc định của chính nó**. Rồi điền:
  ```
  GEMINI_BACKEND=gateway
  GEMINI_MODEL=<bí danh>                     <- bí danh, KHÔNG phải tên upstream
  GEMINI_API_KEY=sk-…                        <- Virtual Key, KHÔNG phải khoá Google
  GEMINI_GATEWAY_BASE_URL=http://gateway-lb:4000
  GEMINI_GATEWAY_USER=svc.<code>
  ```
- **Xong khi:** từ trong container agent, `curl http://gateway-lb:4000/health/liveliness` trả
  200.
- **Bỏ qua thì:** viết `networks: [gateway]` mà quên `default` là agent **rơi khỏi mạng của
  chính nó** — các service khác của agent gọi nhau không được nữa.

> **Bẫy:** `env_file` chỉ nạp lúc **tạo** container. Sửa `.env` rồi `restart` là không ăn —
> phải `up -d --force-recreate`.

---

## 2. Việc ở phía GATEWAY

Chín đầu việc, trong repo này. B2→B6 là sửa file; B1, B7, B8 là thao tác; B9 là cả hai.

### B1 — Xin khoá Google cho project của agent

- **Làm gì:** tạo khoá API trong project GCP của agent. Đặt tên biến theo mã agent:
  `KEY_<MÃ_AGENT_VIẾT_HOA>`, ví dụ `KEY_CRM_FEEDBACK`.
- **Xong khi:** có chuỗi khoá thật trong tay.
- **Bỏ qua thì:** dùng chung khoá cũ được, nhưng hoá đơn Google **không tách được theo
  project** — mất luôn nguồn đối chiếu độc lập với sổ của Gateway.

### B2 — `.env` và `.env.example`

- **Làm gì:** điền giá trị thật vào `.env`; thêm dòng **rỗng có chú thích** vào `.env.example`.
- **Xong khi:** người khác clone repo là biết phải điền biến nào.
- **Bỏ qua thì:** máy khác dựng lại Gateway sẽ thiếu khoá, và triệu chứng xuất hiện muộn — lúc
  có người gọi thật.

### B3 — `docker-compose.yml`, khối `x-litellm`

- **Làm gì:** thêm một dòng trong `environment:`
  ```yaml
  KEY_<MÃ_AGENT>: ${KEY_<MÃ_AGENT>:-}
  ```
- **Xong khi:** `docker compose --profile gateway config` in ra biến đó.
- **Bỏ qua thì:** file này liệt kê **từng biến một**, không có `env_file`. Thiếu dòng này thì
  container không thấy biến, `os.environ/KEY_…` trong cấu hình ra rỗng, và tuyến **chết im
  lặng** cho tới lượt gọi thật đầu tiên.

### B4 — `docker/gateway/entrypoint.sh`

- **Làm gì:** thêm tên biến vào vòng kiểm biến bắt buộc.
- **Xong khi:** xoá biến đó khỏi `.env` thì container in `STOP: … is missing.` rồi dừng.
- **Bỏ qua thì:** khoá thiếu không làm gì dừng cả. Container lên, `/health/liveliness` trả
  200, Docker báo `healthy` — tuyến chết mà mọi đèn đều xanh. Đúng lỗi đã sập ngày 10/09.

### B5 — `docker-compose.bench.yml`

- **Làm gì:** thêm giá trị **cố ý sai** cho đúng biến vừa thêm ở B4.
- **Xong khi:** bench lên được.
- **Bỏ qua thì:** bench dùng chung `entrypoint.sh`, nên thêm biến vào vòng kiểm mà quên bench
  là **bench không lên được nữa**.

### B6 — `docker/gateway/config.gateway.yaml` — khai tuyến

- **Làm gì:** thêm một tuyến:
  ```yaml
  - model_name: <bí danh agent sẽ gọi>
    litellm_params:
      model: <tên upstream thật>
      api_key: os.environ/KEY_<MÃ_AGENT>
      rpm: 15
      tpm: 1000000
      tags: ["<mã agent>"]
  ```
- **Xong khi:** đúng **một** tag định danh trên tuyến.
- **Bỏ qua thì:**
  - Không có tuyến → request không có đường đi.
  - **Hai** tag định danh → bộ nạp không phân giải được agent nào, dòng rơi vào "nhiều tag".
  - Tuyến không tag nhưng agent khác vẫn gọi được tên đó → request đi bằng **khoá của người
    khác**, sai project, mà vẫn trả 200.

> Kiểm lại `enable_tag_filtering: true` còn trong `router_settings`. Mặc định của LiteLLM là
> **tắt**, và khi tắt thì `tags` bị bỏ qua hoàn toàn, im lặng: mọi phép kiểm vẫn đạt, chỉ tiền
> là rơi sai project.

### B7 — Khởi động lại hai instance

- **Làm gì:** `docker compose --profile gateway up -d --force-recreate litellm-1 litellm-2`
- **Xong khi:** cả hai `healthy`, và `/v1/models` liệt kê bí danh mới.
- **Bỏ qua thì:** cấu hình chỉ đọc lúc khởi động (`store_model_in_db: false`). Sửa file mà
  không dựng lại là không có gì đổi.

### B8 — Cấp Virtual Key cho agent

- **Làm gì:** gọi `/key/generate` với:
  - `metadata.tags = ["<mã agent>"]` ← **đúng chỗ này**, không phải trường `tags` cấp cao
  - `models` = danh sách bí danh agent được phép gọi (để trống nếu muốn cho gọi tự do)
  - `key_alias` = `<mã agent>-tagged`
- **Xong khi:** đã **chép chuỗi `sk-…` ra chỗ an toàn** và trao cho agent.
- **Bỏ qua thì:**
  - Tag sai chỗ → không có tác dụng, im lặng. Bảng khoá của LiteLLM **không có cột `tags`**.
  - Không chép chuỗi `sk-…` ngay → mất vĩnh viễn, LiteLLM chỉ lưu hash. Sửa metadata của khoá
    cũ là **ngõ cụt**: sửa xong vẫn không ai biết khoá là gì. Phải cấp khoá mới.

> **`/key/generate` không gọi được từ cổng ngoài.** nginx ở edge chỉ mở
> `/v1/chat/completions` và `/health/*`; mọi đường khác trả 404. Cấp khoá phải làm **từ trong
> mạng Docker** (gọi `http://litellm-1:4000/key/generate`) hoặc bằng `docker exec`.

### B9 — Khai loại agent và đặt hạn mức

- **Làm gì:** khai mã agent vào `QUOTA_CHAT_TAGS` **nếu** đây là agent có người ngồi đọc câu
  trả lời. Rồi mở tab **⚙ Setting** trên dashboard và đặt hạn mức cho khoá vừa cấp.

  **KHÔNG PHẢI "thêm vào", mà là "viết lại cả dòng".** Soát 21/09: `.env` hôm nay **không có
  dòng `QUOTA_CHAT_TAGS` nào** — nó đang ăn giá trị mặc định, và giá trị đó nằm ở **hai chỗ**:

  | Chỗ | Giá trị |
  |---|---|
  | `docker-compose.yml`, khối `x-litellm` | `${QUOTA_CHAT_TAGS:-contact-center,sale-agent,tla-hd,ralli}` |
  | `docker/gateway/quota_hook.py`, `_DEFAULT_CHAT_TAGS` | `contact-center,sale-agent,tla-hd,ralli` |

  Viết một dòng `QUOTA_CHAT_TAGS=` vào `.env` là **đè cả hai**. Nên phải **kê lại đủ bốn mã cũ
  rồi mới thêm mã mới**. Kê thiếu một mã thì agent đó lặng lẽ rơi khỏi nhóm chat.
- **Xong khi:** tab Setting hiện khoá mới với một con số hạn mức, không phải `chưa đặt`.
- **Bỏ qua thì:**
  - Không khai loại → agent bị coi là **chạy theo lô** và khi hết hạn mức sẽ nhận **429** thay vì
    một câu thông báo. Với agent có người dùng thì đó là một lỗi kỹ thuật hiện lên màn hình.
  - Không đặt hạn mức → agent đó **không bị chặn bao giờ**. Không lỗi nào báo ra; nó đơn giản là
    nằm ngoài cơ chế giữ tiền.

> **Đây không còn là chuyện diễn tập.** `.env` hôm nay đặt `QUOTA_DRY_RUN=0`, tức **chặn thật**.
> Bản đầu của trang này viết khi hệ thống còn ở chế độ chỉ-ghi-nhận, nên hai hậu quả trên đọc
> như cảnh báo xa. Nay chúng xảy ra ngay ở lượt gọi vượt hạn mức đầu tiên.

> Chi tiết ở [`quota-han-muc.md`](quota-han-muc.md); bản đồ mã nguồn ở
> [`quota-internals.md`](quota-internals.md). Lưu ý một điều khi sửa khoá bằng tay:
> `/key/update` **thay thế** cả cục `metadata`, nên gửi thiếu là **xoá mất `tags`** của khoá — và
> mất tag thì tiền ghi sai project mà request vẫn trả 200. Luôn đọc metadata hiện có rồi gửi lại
> đầy đủ.

---

## 3. Việc ở phía DASHBOARD

> **Workflow hiện tại cho Gateway-only:** sửa `config/gateway-agents.yaml`,
> dry-run → apply → refresh; xem đầy đủ [runbook](gateway-agent-registration.md).
> Không tải danh bạ/web exports hay billing/monitoring files. Mode multiple
> tạo identity riêng theo agent từ log; không gọi đó là nhân viên đã cấp quyền.
> **C1–C4 và phần 8 dưới đây là ghi chép legacy**, không áp dụng cho agent
> đăng ký bằng YAML. Không chạy generator/load_org/rebuild theo các ví dụ cũ.

**Bốn** đầu việc. Thiếu thì lưu lượng vẫn chạy, chỉ là dashboard không thấy.

### C1 — Thêm agent vào danh mục

- **Làm gì:** thêm một dòng vào bảng `AGENTS` trong `db/gen_catalog.py` (id, code, tên hiển
  thị, project GCP, có cây tổ chức, ngày tạo project, đang chạy, có nguồn Google). Nếu agent
  có hạn mức USD thì thêm một dòng vào `BUDGET_USD` **ngay dưới đó** — dict này khoá bằng
  **tên hiển thị**, không phải mã agent. Rồi chạy `python db/gen_catalog.py` để sinh lại
  `db/02_catalog.sql`.
- **Xong khi:** `SELECT code FROM dim_agent` có mã agent mới.
- **Bỏ qua thì:** bộ nạp tìm tag định danh bằng cách so với `dim_agent.code`. Không có dòng
  nào khớp thì **mọi dòng của agent đó bị bỏ**, đếm vào "không có tag định danh".
- **Bỏ qua `BUDGET_USD` thì:** agent không có hạn mức USD, và **không cách nào phân biệt với
  cố ý**. Tools Quizzer và Ralli hôm nay cũng vắng mặt trong dict đó, và đó là có chủ đích.

> **"Chạy lại script" KHÔNG đưa được dòng mới vào database.** Đây là chỗ trang này nói nhẹ hơn
> thực tế, sửa 21/09. `db/02_catalog.sql` chỉ vào database qua **đúng một cửa**:
>
> ```
> gen_catalog.py ──▶ db/02_catalog.sql
>                          │
>                          ▼
>                connect.rebuild()          db/connect.py:252
>                          ├── alembic upgrade
>                          ├── TRUNCATE MỌI bảng dữ liệu     ◀── đây
>                          └── nạp lại 02_catalog.sql
>                          │
>                          ▼
>                scripts/rebuild_db.py — 11 bước, nạp lại tất cả từ data/
> ```
>
> Và dịch vụ `ledger-refresh` **không** đi qua cửa đó: `scripts/refresh_gateway.py` chỉ chạy
> 3 bước (nạp sổ Gateway + 2 bảng dẫn xuất) và không bao giờ nạp lại danh mục.
>
> Nghĩa là thêm một agent = **dựng lại cả database**, không phải chạy một script. Việc này có
> chỗ hỏng riêng của nó (quyền đọc của vai `api_readonly`) — bước 11 của `rebuild_db.py` là
> một **phép kiểm** sinh ra đúng để bắt chuyện đó. Đừng bỏ qua nó.

### C2 — Khai model vào `db/rules.py`

- **Làm gì:** thêm tên upstream thật vào `GATEWAY_MODELS`; kiểm `MODEL_PATTERNS` có nhận ra
  model đó không.
- **Xong khi:** nạp thử không còn in `model not declared`.
- **Bỏ qua thì:** dòng vào `fact_call` với `model_id` NULL → `fact_usage_daily` **không có
  dòng nào** → dashboard hiện 0 cho agent đó, trong khi phép kiểm toàn vẹn vẫn ĐẠT vì dòng
  *đã* vào sổ.
- **Bẫy đã sập một lần:** `MODEL_PATTERNS` xếp theo thứ tự, **mẫu dài phải đứng trước**.
  Thiếu mẫu dài thì model bị gán nhầm sang model khác — khác đơn giá, và **vẫn báo là tìm
  thấy**.

### C3 — Khai loại người dùng trong `db/load_org.py`

**Việc này thiếu hẳn trong bản 19/09.** Thêm 21/09 sau khi soát lại mã nguồn.

- **Làm gì:** mở `db/load_org.py` và thêm `agent_id` mới vào **đúng một** trong hai danh sách
  gõ tay ở đầu tệp:

  ```python
  db/load_org.py:84    RALLI, TLA_CONTRACT = 8, 5
  db/load_org.py:85    SINGLE_USER_AGENTS = (1, 2, 3, 4, 6, 7)      # quyết định A1
  ```

  Agent một-người-dùng → thêm vào `SINGLE_USER_AGENTS`. Agent nhiều người dùng → xem mục 8
  trước, vì thêm vào tuple ở dòng 84 **chưa đủ**.
- **Xong khi:** `SELECT username FROM account WHERE kind = 'service_account'` có đúng một dòng
  `svc.<code>` của agent mới.
- **Bỏ qua thì:** **bước 2 của `rebuild_db.py` chết**, với `KeyError` ở `load_org.py:615`.

  Đường đi của lỗi, soát tĩnh 21/09:

  ```
  load_org.py:301   agent_name  ← SELECT agent_id, name FROM dim_agent   (CÓ agent mới)
  load_org.py:311   __technical_{aid}__      chỉ cho aid trong SINGLE_USER_AGENTS
  load_org.py:315   __unattributed_{aid}__   chỉ cho aid trong (TLA_CONTRACT, RALLI)
          ↓
  load_org.py:564   technical_unit = {1,2,3,4,6,7, 5,8}        ← KHÔNG có agent mới
          ↓
  load_org.py:568   for aid in sorted(agent_name):             ← CÓ agent mới
  load_org.py:615   technical_unit[aid]      →  KeyError  →  BƯỚC 2 DỪNG
  ```

  Đây là một trong số **ít** việc trong trang này hỏng **to** chứ không hỏng im lặng. Vẫn phải
  làm trước, vì nó chặn ngang lượt dựng lại database ở việc C1.

- **Một danh sách, ba chỗ đọc.** `SINGLE_USER_AGENTS` được dùng ở dòng 311, 404 và 587. Chỉ
  sửa **một** chỗ khai ở dòng 85; ba chỗ kia tự theo. Chính tệp này, ở dòng 304, đã ghi:
  *"gõ tay thì ngày thêm agent thứ 9 sẽ quên một chỗ"* — và dòng 85 ngay trên nó là một chỗ
  gõ tay.

### C4 — Kiểm tài khoản dịch vụ

- **Làm gì:** với agent một-người-dùng, kiểm `svc.<code>` có ra một dòng trong bảng tài khoản
  sau lượt nạp đầu tiên.
- **Xong khi:** thấy đúng một dòng `kind = 'service_account'`.
- **Bỏ qua thì:** `X-User` gửi một chuỗi không khớp quy ước thì `load_gateway.py:378` **từ
  chối** định danh đó, cộng vào bộ đếm `identity_unresolvable`, và dồn lưu lượng về tài khoản
  neo mức agent. Tổng token vẫn đúng; chỉ riêng chiều người dùng lệch — đúng kiểu hỏng đã làm
  độ phủ báo 12,4% trong khi lỗ hổng thật là 1,2%.

> Không phải chạy lệnh nạp bằng tay: dịch vụ `ledger-refresh` tự nạp theo chu kỳ. Nhưng nó
> chạy bộ nạp với đầu ra bị nuốt khi thành công — nên dòng `model not declared` **sẽ không ai
> thấy**. Lần đầu phải chạy tay một lượt để đọc được các bộ đếm.

---

## 4. Nghiệm thu — bốn phép đo, theo thứ tự

| # | Đo gì | Đạt là |
|---|---|---|
| D1 | Gọi 10 lượt thật từ agent | 10/10 HTTP 200 |
| D2 | Đếm dòng mới trong sổ Gateway | đúng 10 dòng, `total_tokens > 0`, `spend > 0`, số lần thử lại = 0 |
| D3 | **Phép kiểm âm** cho tag | dựng một tuyến mồi cùng bí danh, mang `tags: ["khong-ai-dung"]` và khoá cố ý sai → **0 lần chạm** tuyến mồi. Xong thì **gỡ tuyến mồi và dựng lại** |
| D4 | Chạy bộ nạp một lượt bằng tay | không có dòng bị bỏ, không có `model not declared`, dashboard hiện số |

> **Đừng lấy "gọi thử thấy chạy" làm bằng chứng.** Đo ngày 31/08 trên 8 lượt gọi thiếu tag:
> **7/8 thành công, 1/8 trượt**. Hỏng lác đác 12,5% là kiểu hỏng qua được mọi lần thử tay.
> D3 là phép đo duy nhất chứng minh được tag lọc đúng, vì sổ **không** ghi lại quyết định định
> tuyến — cột tag và cột quyết định trong sổ đều rỗng.

---

## 5. Lùi lại

| Muốn | Làm |
|---|---|
| Tạm ngắt agent khỏi Gateway | đổi biến backend trong `.env` của agent, `up -d --force-recreate` |
| Thu hồi quyền gọi | xoá Virtual Key. Lưu ý khoá đã dùng thành công còn sống thêm **tối đa 5 phút** nếu xoá thẳng bằng SQL; thu hồi qua API của proxy thì mất hiệu lực ngay |
| Gỡ tuyến | xoá khối tuyến trong `config.gateway.yaml`, dựng lại hai instance |
| Gỡ khỏi dashboard | **không gỡ.** Số cũ phải giữ. Đặt agent thành không còn chạy thay vì xoá dòng |

---

## 6. Bảng tra — một agent mới chạm vào những file nào

| Nơi | File | Việc |
|---|---|---|
| Repo agent | chỗ gọi LLM | A1, A2 |
| Repo agent | chỗ khai giá trị cấu hình hợp lệ | A3 |
| Repo agent | compose / override | A7 |
| Repo agent | `.env` | A7 |
| Repo này | `.env`, `.env.example` | B2 |
| Repo này | `docker-compose.yml` (khối `x-litellm`) | B3 |
| Repo này | `docker/gateway/entrypoint.sh` | B4 |
| Repo này | `docker-compose.bench.yml` | B5 |
| Repo này | `docker/gateway/config.gateway.yaml` | B6 |
| Repo này | `db/gen_catalog.py` (bảng `AGENTS`) | C1 |
| Repo này | `db/gen_catalog.py` (dict `BUDGET_USD`) | C1 |
| Repo này | `db/rules.py` (`GATEWAY_MODELS`, `MODEL_PATTERNS`) | C2 |
| Repo này | `db/load_org.py` (`SINGLE_USER_AGENTS`, dòng 85) | C3 |
| Repo này | `.env` (`QUOTA_CHAT_TAGS`) | B9 |
| Không phải file | `/key/generate` | B8 |
| Không phải file | tab ⚙ Setting trên dashboard | B9 |
| Không phải file | chạy `scripts/rebuild_db.py` một lượt | C1 |

**Mười sáu chỗ** cho một agent mới một-người-dùng.

Bỏ sót **phần lớn** những chỗ này thì hệ thống vẫn chạy, vẫn trả 200, chỉ số liệu là sai. Dễ
nhớ hơn nếu học theo chiều ngược lại — đây là **toàn bộ** các chỗ bỏ sót sẽ báo lỗi to, đọc
ra từ chính dòng "Bỏ qua thì" của từng việc:

| Việc | Triệu chứng khi bỏ sót |
|---|---|
| A3 — danh sách cấu hình hợp lệ | app của agent không khởi động |
| B5 — `docker-compose.bench.yml` | bench không lên được |
| B8 — `/key/generate` | không có khoá thì không gọi được |
| C3 — `SINGLE_USER_AGENTS` | `KeyError`, bước 2 của `rebuild_db.py` dừng |

**Mọi chỗ còn lại đều hỏng im lặng.** Nếu đang làm mà thấy một lỗi báo ra, nhiều khả năng nó
là một trong bốn dòng trên; không thấy lỗi nào **không** có nghĩa là đã làm đủ.

> Bản 19/09 đếm mười ba. Ba chỗ thêm vào ngày 21/09 — `BUDGET_USD`, `load_org.py` và lượt
> dựng lại database — đều tìm ra bằng cách đọc mã nguồn, không phải bằng cách nối thử một
> agent. Nên **con số này vẫn có thể còn thiếu.** Lần nối agent thứ 9 thật, hãy ghi lại mọi
> chỗ phải chạm và sửa bảng này.

---

## 7. Tuỳ chọn đang cân nhắc — một tuyến `*` cho mỗi agent

**Chưa bật.** Ghi ở đây vì nó xoá được phần nặng nhất của bảng trên: hiện nay **mỗi model**
phải khai một tuyến; đổi sang cách này thì **mỗi agent** khai một tuyến, rồi agent gọi model
nào cũng được.

```yaml
- model_name: "*"
  litellm_params:
    model: "gemini/*"
    api_key: os.environ/KEY_<MÃ_AGENT>
    tags: ["<mã agent>"]
```

LiteLLM có sẵn cơ chế này, không phải sửa dòng code nào. Tên model người gọi gửi lên được
ghép thẳng vào chỗ `*`, còn khoá và tag của tuyến giữ nguyên — nên việc tách hoá đơn theo
agent vẫn chạy như cũ.

Ba điều phải xử lý trước khi bật:

1. **Tuyến khai tên thật luôn thắng tuyến `*`.** LiteLLM chỉ tìm tới tuyến `*` khi không có
   tuyến nào mang đúng tên được gọi. Nên các tuyến hiện có phải gỡ đi, hoặc phải mang tag —
   nếu không, agent mới gọi trúng một bí danh cũ sẽ đi bằng khoá của tuyến cũ.
2. **Tiền có thể về 0.** Model lạ chưa có trong bảng giá của LiteLLM thì token vẫn ghi đủ
   nhưng chi phí ghi 0. Và `GATEWAY_MODELS` chưa khai thì `model_id` NULL (việc C2 ở trên).
   Tự do gọi model đổi lấy việc sổ tiền không còn tự đúng.
3. **Khoá quản trị vẫn nguy như cũ.** Request không mang tag thì bộ lọc trả về **tất cả**
   tuyến và khoá được chọn gần như ngẫu nhiên.

Việc 1 và 3 phải làm dù có bật hay không. Việc 2 là đánh đổi phải chốt trước.

---

## 8. Ghi chép legacy: agent nhiều người dùng dựa trên danh bạ

Với agent Gateway-only mới, dùng `user_mode: multiple` theo runbook trên;
những yêu cầu import danh bạ dưới đây chỉ dành cho luồng legacy.

**Soát 21/09/2026.** Cả bảng việc ở trên ngầm giả định agent mới là loại một-người-dùng. Với
agent nhiều người dùng, việc C3 không có đáp án, và lý do nằm sâu hơn một dòng cấu hình.

### Người dùng thật đến từ đâu

Không có danh bạ chung của công ty. Bảng `account` chỉ có hai nguồn, và cả hai là **bản xuất
của chính ứng dụng đó**:

```
data/raw_web/ralli/users-list.json        ──▶  người của Trợ lý ảo Ralli   (agent 8)
data/raw_web/tla-hd/units-members.json    ──▶  người của TLA Hợp Đồng      (agent 5)
        + token-usage-filter-options.json      (vá người không thuộc đơn vị nào)
```

Một agent nhiều người dùng **mới** không có bản xuất nào như vậy. Người của nó chỉ xuất hiện
qua header `X-User` lúc gọi — mà `load_gateway.py` thì **tra** bảng `account`, nó không tạo
dòng mới. Nên phải **viết thêm một khâu nạp danh bạ** trong `db/load_org.py`, có nguồn dữ
liệu riêng. Đó là code thật, không phải một dòng cấu hình.

### Bẫy thứ hai, nặng hơn: một người chỉ thuộc về MỘT agent

Đây là chỗ đáng đọc kỹ, vì nó chưa bao giờ bị thử.

`load_org.py:505` gom tài khoản theo **tên đăng nhập**, gộp chung mọi agent — một người là
một dòng, dù họ dùng mấy app. Rồi `unit_priority` (dòng 492) chọn **một** agent chủ cho dòng
đó, và tiêu chí thứ ba là **`agent_id` nhỏ nhất**.

Trong khi đó `load_gateway.py:378` chỉ nhận định danh khi tài khoản thuộc **chính agent đang
gửi request**:

```
       account.unit_agent_id      request mang tag của       kết quả
       ─────────────────────      ────────────────────       ───────
  svc.dms-feedback →  agent 6         agent 6                NHẬN
  admin            →  agent 5         agent 6                TỪ CHỐI
  pbh1_ntlong      →  agent 5         agent 5                NHẬN
  pbh1_ntlong      →  agent 5         agent 9   ◀── mới      TỪ CHỐI
```

Dòng cuối là vấn đề. Một người đã có mặt ở TLA Hợp Đồng (agent 5) mà cũng dùng agent 9 thì
`unit_agent_id` của họ là **5**, vì 5 < 9. Mọi lượt gọi của họ qua agent 9 bị từ chối định
danh, cộng vào `identity_unresolvable`, và dồn về tài khoản neo.

Hỏng **im lặng**: tổng token đúng, tổng tiền đúng, HTTP 200 hết. Chỉ chiều người dùng của
agent 9 là rỗng.

Hôm nay chuyện này chưa xảy ra, vì hai agent nhiều người dùng duy nhất (5 và 8) **chưa cái
nào đi qua Gateway**. Quy tắc `found[1] == agent_id` được viết để phục vụ đúng trường hợp
này, và nó chưa từng gặp trường hợp này.

### Phải chốt gì trước khi nối agent nhiều người dùng đầu tiên

1. **Nguồn danh bạ** — lấy người của agent mới từ đâu, ai kéo, kéo bao lâu một lần.
2. **Một người ở nhiều agent** — giữ nguyên "một dòng một người" rồi sửa phép tra định danh
   thành *"tài khoản này có mặt ở agent đó không"*, hay tách dòng theo từng agent. Hai hướng
   này khác nhau ở chiều phòng ban và ở chỉ tiêu tỷ lệ áp dụng, không chỉ ở một câu `WHERE`.
3. **Phép kiểm âm** — `identity_unresolvable` phải bằng 0 sau lượt nạp đầu. Con số này đang
   được đếm sẵn; đừng nghiệm thu bằng tổng token, vì tổng token vẫn đúng khi chuyện này hỏng.

Chưa chốt xong ba điều trên thì **chưa nối được** agent nhiều người dùng, dù phía Gateway
(mục 2) có làm đủ cả chín việc.
