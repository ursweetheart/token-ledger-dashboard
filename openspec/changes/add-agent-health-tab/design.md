## Context

- `scripts/watch_gateway.py` đã có sẵn ba thứ cần dùng: múi giờ `VN = timezone(timedelta(hours=7))`
  (dòng 77), mẫu "một lần mỗi ngày sau giờ X" của thư nhịp tim (`heartbeat()`, dòng 486), và vòng lặp
  mà một nhịp lỗi không giết được (dòng 568).
- `backend/connection_api.py` có `authorize()` bằng `CONNECTION_ADMIN_KEY`, và kết nối ghi qua vai
  `connection_admin` (`CONNECTION_ADMIN_DSN`). API chính dùng vai `api_readonly`.
  `docker/read-only-api.sql` cho vai này quyền `SELECT` mặc định trên mọi bảng mới.
- `db/connect.py:251` `rebuild()` xoá dòng của mọi bảng không có trong `KEEP_ON_REBUILD`.
  `tests/test_connect_migrations.py` báo đỏ nếu một migration gieo dòng vào bảng không có trong danh
  sách đó.
- Trợ lý ảo Ralli có Rạng Đông Partner API (`/api/partner/v1`, FastAPI, 50 path, **không có
  `/health`**). Xác thực bằng header `X-API-Key`. Lỗi trả `application/problem+json`. Mọi response có
  `X-Request-ID`. `429` nghĩa là hết hạn mức request hoặc hết AI budget; `503` nghĩa là dịch vụ AI
  không sẵn sàng.
- Response 200 của `/ctda/v2/analyze` có schema `{}`. Thử thật 29/10: `{"status":"success","data":
  {"feature","title","analysis","raw_data"}}`.
- Image `tools` có `psycopg2-binary` và `PyYAML` (`backend/requirements.txt`).

## Goals / Non-Goals

**Goals:**

- Thêm agent bằng một khối YAML, không sửa Python.
- Lịch chạy đúng một lần mỗi ngày vào giờ VN đã đặt. Restart không chạy lần hai. Lỡ giờ thì chạy bù.
- Đổi giờ trên dashboard là có tác dụng ở vòng kế tiếp (≤ 5 giây), không cần restart container.
- Nút "Chạy ngay" bắt đầu trong ≤ 5 giây, hiện tiến độ, và không đụng tới lịch.
- Kết quả mỗi phép kiểm có: đạt / cảnh báo / lỗi, mã HTTP, thời gian (ms), lý do, `X-Request-ID`.

**Non-Goals:**

- Gửi thư, nhiều lịch, cron, biểu đồ.
- Trần số lần bấm "Chạy ngay" mỗi ngày. Người dùng dự kiến 1–3 lần; khoá quản trị và chặn bấm chồng là đủ.
- Thanh tiến độ theo thời gian ước tính.
- Gọi bất kỳ endpoint ghi nào của agent ngoài endpoint đã được khai và được duyệt.
- Kiểm nội dung câu trả lời của LLM có đúng nghiệp vụ hay không.

## Decisions

### D1 — Một service riêng, theo khuôn `gateway-watch`, không gộp vào `gateway-watch`

`gateway-watch` hỏi "Gateway có sống không" mỗi 60 giây, dùng các phép dò miễn phí. Phép kiểm agent
chạy theo lịch mỗi ngày hoặc khi bấm tay, và có tốn phí. Gộp lại thì một lỗi YAML của agent có thể làm hỏng việc canh
Gateway. Script mới **import** `VN` và `parse_since` / `stamp` từ `watch_gateway.py`, như
`watch_quota.py` đang làm, chứ không chép lại.

Đã cân nhắc: cron trong container (cần image mới), APScheduler (phụ thuộc mới). Cả hai đều không đổi
giờ được nếu không restart.

### D2 — Giờ chạy nằm trong DB, service đọc lại mỗi vòng

```
mỗi 5 s:
  ① có run trigger='manual' đang queued? → run(run_id); xong vòng          (D9)
  ② s = SELECT run_at, last_run_date FROM agent_health_setting
     now_vn = now(UTC).astimezone(VN)
     if now_vn.time() >= s.run_at and s.last_run_date != now_vn.date():
         BEGIN
           UPDATE ... SET last_run_date = today WHERE last_run_date IS DISTINCT FROM today  -- giữ chỗ
           if rowcount == 1: INSERT agent_health_run (trigger='schedule', status='running')
         COMMIT        -- INSERT vướng index duy nhất → ROLLBACK cả hai, vòng sau thử lại
         run(run_id)
```

- Vòng 5 giây thay vì 60 giây để nút "Chạy ngay" phản hồi nhanh. Mỗi vòng chỉ có một hai câu `SELECT` nhỏ.
- **Run tay đang chờ được xét trước lịch.** Nếu xét lịch trước, `INSERT` của lịch sẽ vướng index duy nhất
  do run tay đang giữ, mỗi vòng một lần, và run tay không bao giờ được chạy. Lịch chỉ bị lùi nhiều nhất
  một lần chạy.
- **Giữ chỗ và `INSERT` run nằm trong một transaction.** Nếu tách ra, `INSERT` thất bại sẽ để lại
  `last_run_date` đã ghi, và lần chạy theo lịch hôm đó mất luôn.

- `UPDATE ... WHERE` dùng làm khoá: nếu hai bản service chạy cùng lúc, chỉ một bản chạy.
- Đánh dấu **trước** khi chạy: service chết giữa chừng thì lịch hôm đó không tự gọi lại `analyze`.
  Người vận hành bấm "Chạy ngay" nếu cần kết quả.
- `last_run_date` **chỉ** do lịch ghi. Lần chạy tay không đọc, không ghi nó (D9).
- Lỡ giờ (container lên lúc 09:00, giờ đặt 08:00): điều kiện vẫn đúng nên chạy bù ngay. Lên sau nửa
  đêm thì hôm trước bị bỏ qua, có chủ ý.
- Đặt giờ mới **sớm hơn** giờ hiện tại, khi hôm nay chưa chạy: chạy ngay ở vòng kế tiếp. Đặt giờ khi
  hôm nay đã chạy rồi: lần sau là ngày mai.
- `run_at` kiểu `time`, nghĩa là giờ VN. `last_run_date` kiểu `date` theo lịch VN. Không lưu UTC vì
  người vận hành chỉ nghĩ theo giờ VN.

### D3 — Cấu hình phép kiểm: YAML khai báo, ba loại điều kiện

```yaml
agents:
  ralli:
    name: Trợ lý ảo Ralli
    base_url: https://ralliai.rangdong.com.vn:9001/api/partner/v1
    auth: {header: X-API-Key, env: RALLI_PARTNER_KEY}
    # gateway_tag: ralli     # bật khi Ralli đã qua Gateway
    checks:
      - name: capabilities
        method: GET
        path: /capabilities
        expect:
          status: 200
          equals: {"features[id=ctda].enabled": true}
          days_until: {"expires_at": 30}        # dưới 30 ngày → warn
      - name: llm
        method: POST
        path: /ctda/v2/analyze
        body: {query: "Phân tích ngắn tình hình chăm sóc công trình dự án tháng này"}
        timeout: 180
        expect:
          status: 200
          equals: {"status": "success"}
          not_equals: {"data.feature": "clarification"}
```

- Đường dẫn trường kiểu `a.b` và một dạng lọc `list[key=value]`. Chỉ vậy. Không dùng JSONPath (phụ thuộc
  mới), vì hai dạng này đủ cho mọi trường hợp đã thấy.
- `method` chỉ nhận `GET` và `POST`. `POST` phải nằm trong danh sách trắng ghi ở chính file YAML
  (`allow_post: [/ctda/v2/analyze]`), và script từ chối chạy nếu thiếu. Chốt này để nhắc rằng mỗi
  `POST` là một ngoại lệ của luật chỉ-đọc, phải được duyệt.
- Key đọc từ biến môi trường mà YAML chỉ ra. YAML không bao giờ chứa key.
- File nằm trong `config/`, **không** nằm trong `config/gateway-agents.yaml`. File đó do worker xuất lại
  từ DB, sẽ ghi đè mất phần health.

Đã cân nhắc: viết mỗi agent một hàm Python. Như vậy dễ hơn với agent lạ, nhưng mỗi agent mới là một lần
sửa code. Khi gặp agent không vừa khuôn này thì mới thêm một kiểu xác thực hay kiểu điều kiện.

### D4 — Ba mức kết quả

| Mức | Khi nào |
|---|---|
| `ok` | mọi điều kiện đạt |
| `warn` | HTTP 429 (bị giới hạn, chưa phải chết), hoặc `days_until` dưới ngưỡng |
| `fail` | mọi lỗi khác: mạng, timeout, HTTP khác, điều kiện không đạt, thiếu biến key |

Thiếu biến key thì ghi `fail` với lý do rõ ràng, **không** bỏ qua im lặng: bỏ qua thì tab sẽ trông như
"không có lỗi".

Lý do lỗi lấy `title` + `detail` của `problem+json` nếu có, cắt còn 500 ký tự.

Phép kiểm có `question` trong YAML là một **case**: câu hỏi được gửi trong trường `question_field` của
body, và **nguyên response** được giữ trong kết quả, cùng câu trả lời lấy theo đường dẫn `answer`. Phép
kiểm health thì không giữ response. (Bản đầu không giữ response nào; đổi ngày 29/10/2026 vì module chụp
màn hình cần câu hỏi nguyên văn và câu trả lời để đối chiếu với giao diện, mục 5.2 của
`kiem-tra-agent-hang-ngay.md`.) Response có thể chứa dữ liệu nghiệp vụ, nên chỉ đọc được qua backend có
khoá dashboard, và `var/agent-checks/` nằm trong `.gitignore`.

### D5 — Đối chiếu Gateway là tuỳ chọn

Khi agent có `gateway_tag`, sau phép kiểm `llm` service tìm `LiteLLM_SpendLogs` có tag đó trong khoảng
[bắt đầu − 5 s, kết thúc + 60 s], qua vai chỉ-đọc `GATEWAY_DSN` (đã có ở `ledger-refresh`). Không có dòng
nào thì phép kiểm `gateway-log` là `fail`. Ralli chưa đi qua Gateway nên không khai. Không đọc được
`GATEWAY_DSN` thì phép kiểm này là `fail`, không phải `ok`.

Trần đã biết: lúc có người thật đang dùng thì một dòng cùng tag chưa chắc là của lần kiểm. Lọc thêm theo
user khi biết agent chuyển user nào sang Gateway.

### D6 — Lưu trữ

```sql
agent_health_setting (id smallint PK CHECK (id = 1), run_at time NOT NULL DEFAULT '08:00',
                      last_run_date date, updated_at timestamptz, updated_by text)
agent_health_run     (id uuid PK, trigger text CHECK (trigger IN ('schedule','manual')),
                      status text CHECK (status IN ('queued','running','done','interrupted')),
                      total int, done int NOT NULL DEFAULT 0, current_label text,
                      requested_by text, requested_at timestamptz NOT NULL DEFAULT now(),
                      started_at timestamptz, finished_at timestamptz,
                      result jsonb)      -- tài liệu kết quả, khuôn ở docs/reference/agent-health-result.md
CREATE UNIQUE INDEX ... ON agent_health_run ((true)) WHERE status IN ('queued','running')
```

**Một tài liệu JSON, hai nơi** (chốt 29/10/2026, thay bảng `agent_health_result` của bản đầu):

- Cột `result`: service ghi lại **cả tài liệu** sau mỗi phép kiểm, cùng câu với `done = done + 1`, nên
  thanh tiến độ không đi trước kết quả, và lần chạy bị ngắt vẫn giữ phần đã xong.
- Tệp `var/agent-checks/<run_id>/result.json`: chỉ ghi khi lần chạy xong, ghi ra tệp tạm rồi đổi tên
  (nguyên tử), để module chụp màn hình không đọc phải tệp viết dở. Không ghi được tệp thì DB vẫn nhận
  tài liệu, kèm lý do trong `limitations`.
- API dàn phẳng tài liệu thành `results` cho tab, và không trả nguyên tài liệu: trình duyệt hỏi mỗi giây
  lúc đang chạy, còn tài liệu chứa cả response của agent.

- Index duy nhất có điều kiện: tại một thời điểm chỉ có **một** run đang chờ hoặc đang chạy. Database
  bảo đảm điều này, không phải code. Đây là chốt chặn bấm chồng (D9).
- `status` của run nói **lần chạy** đã xong hay chưa. Khoẻ hay không thì xem `result`.
- Ghi run bằng vai admin của image `tools` (`TOKEN_LEDGER_DSN`), giống `ledger-refresh`.
- `connection_admin` được `SELECT, UPDATE` trên `agent_health_setting` và `SELECT, INSERT` trên
  `agent_health_run`, và chỉ vậy.
- `api_readonly` tự có `SELECT` qua default privileges.
- Cả hai bảng vào `KEEP_ON_REBUILD`. Bảng setting có một dòng được gieo trong migration, nên thiếu bước
  này thì test migration báo đỏ, và mỗi lần rebuild sẽ mất giờ đã đặt.
- `agent_code` là chuỗi trong YAML, không phải khoá ngoại tới `dim_agent`. Agent có thể được kiểm trước
  khi được đăng ký, và rebuild không được kéo bảng này theo.

### D7 — API

- `GET /api/agent-health` (`main.py` + `store.py`, chứng danh dashboard): trả setting, run mới nhất đã
  xong cùng các dòng result của nó, và run đang chờ/chạy nếu có.
- `GET /api/agent-health/runs/{id}` (chứng danh dashboard): `status`, `done`, `total`, `current_label`,
  `started_at`, cùng các dòng result đã có. Trình duyệt hỏi mỗi giây trong lúc chạy.
- `PUT /api/agent-health/schedule` `{run_at: "HH:MM"}`: thêm vào `connection_api.py` dưới một
  `APIRouter` thứ hai, để dùng chung `authorize()` và `store`. Kiểm `^([01]\d|2[0-3]):[0-5]\d$`, sai thì
  trả 422. Ghi `updated_by = 'connection-admin'`. Tắt quản trị thì trả 503, như mọi mutation khác.
- `POST /api/agent-health/run` (khoá quản trị, body rỗng): `INSERT` một run `manual`, `queued`. Vướng
  index duy nhất thì trả **409** kèm `id` của run đang chạy, để trình duyệt theo dõi luôn run đó thay vì
  báo lỗi suông. Thành công thì trả 202 kèm `id`.

Đã cân nhắc: dùng khoá dashboard cho PUT. Bị loại vì spec `api-access-control` và design của tab Kết nối
đều nói khoá dashboard không cấp quyền ghi.

### D8 — Giao diện

`web/js/agent-health.js`, theo khuôn `gateway-identities.js`. Gọi `TokenLedgerAPI.agentHealth()` để
hiện bảng. Nút Apply và Chạy ngay cần khoá quản trị: dùng `<input type="time">` của trình duyệt (không
thư viện), và một ô khoá quản trị chỉ giữ trong bộ nhớ, như tab Kết nối. Biểu tượng ✅/⚠️/❌ giống tab Kết
nối, ⏳ cho phép kiểm chưa tới lượt. Agent hiện bằng `name` trong YAML, không hiện mã.

```
[08:00] [Apply]                                  [▶ Chạy ngay]
████████████████░░░░░░░░░░░░░░░░  50%  (1/2)        ← <progress value=done max=total>
Đang kiểm: Trợ lý ảo Ralli — llm  (12 giây)          ← current_label + đồng hồ phía trình duyệt
```

- Thanh tiến độ là thẻ `<progress>` có sẵn. Khi đang chạy, nút Chạy ngay bị tắt.
- Mở tab khi đang có run chạy dở (kể cả do người khác bấm, hoặc do lịch) thì thanh hiện ngay và theo dõi
  run đó.
- Run xong thì ngừng hỏi, tải lại bảng.

### D9 — "Chạy ngay" độc lập với lịch

Người dùng chốt 29/10/2026: bấm là gọi ngay, không ảnh hưởng lịch, cho phép thêm `POST /ctda/v2/analyze`
mỗi lần bấm.

- **Độc lập:** run `manual` không đọc, không ghi `last_run_date`. Bấm lúc 07:00 thì 08:00 lịch vẫn chạy.
- **Ai chạy:** service, không phải API. API chạy bằng vai chỉ-đọc, không giữ key agent, và một lần gọi
  LLM có thể mất 180 giây, quá lâu để giữ một request HTTP. Tab Kết nối đã làm theo cách này: API xếp
  việc, worker làm, trình duyệt hỏi lại.
- **Tiến độ:** `total` = tổng số phép kiểm của mọi agent, tính lúc bắt đầu. Service cập nhật
  `current_label` **trước** mỗi phép kiểm và `done` **sau** mỗi phép kiểm. Với Ralli, thanh đi 0 → 50 →
  100% và có thể đứng ở 50% tới 180 giây trong lúc chờ LLM. Đây là sự thật, không phải lỗi;
  `current_label` và đồng hồ cho biết nó vẫn đang chạy.
- **Chặn bấm chồng:** index duy nhất có điều kiện ở D6. Lịch đến giờ đúng lúc đang có một run tay thì
  transaction của lịch rollback, và lịch chạy ở vòng ngay sau run tay. `last_run_date` chưa ghi nên lần
  chạy theo lịch không bị mất.
- **Run bị ngắt:** lúc khởi động, service chuyển mọi run `running` sang `interrupted`. Nếu không làm vậy,
  index duy nhất sẽ khoá nút Chạy ngay mãi mãi sau một lần container chết. Run `queued` thì giữ nguyên để
  chạy tiếp.
- **Chỉ một bản service.** Bước dọn lúc khởi động sẽ ngắt nhầm run của một bản service khác nếu có hai bản
  cùng chạy. `container_name` cố định trong compose đã chặn việc có hai bản. Ghi rõ điều này trong tài liệu
  vận hành: không chạy `watch_agents.py` vòng lặp ngoài container khi service đang lên. `--once` thì được,
  vì nó không dọn.

Đã cân nhắc: API gọi thẳng agent rồi trả kết quả qua SSE. Bị loại vì API phải giữ key agent và kết nối
mở 180 giây. Phải tách ra service riêng thì mới đúng ranh giới chỉ-đọc hiện có.

## Risks / Trade-offs

- [Key partner gắn `admin`, có đủ 11 quyền] → Rò key là rò quyền xoá hội thoại. Tạm chấp nhận cho
  baseline. Xin key chỉ có `action:ctda`; đổi key chỉ cần sửa `.env`.
- [Token của lần kiểm tính cho `admin` trên dashboard] → Ghi rõ trong tài liệu vận hành. Xin tài khoản
  riêng cùng lúc với key mới.
- [Câu hỏi thử chưa từng được chạy] → Lần chạy đầu là lần thử. Nếu ra `clarification` thì điều kiện
  `not_equals` sẽ báo `fail`; khi đó đổi câu trong YAML.
- [`expires_at` không có múi giờ] → Ngưỡng 30 ngày nên lệch 7 giờ không ảnh hưởng. Coi như UTC.
- [Giữ chỗ trước khi chạy] → Service chết giữa lần chạy thì hôm đó thiếu kết quả. Tab phải hiện "lần
  chạy gần nhất" kèm ngày, để thấy được ngày bị thiếu.
- [Apply và Chạy ngay phụ thuộc quản trị kết nối] → Máy không bật `CONNECTIONS_ENABLED` vẫn xem được
  kết quả, chỉ không đổi được giờ và không bấm chạy được. Khi đó dùng SQL hoặc `watch_agents.py --once`.
- [Không có trần số lần bấm] → Mỗi lần bấm tốn AI budget và gọi vào hệ thống của đội khác. Chặn bằng khoá
  quản trị và chặn bấm chồng. `requested_by` ghi lại mỗi lần bấm để xem lại được.
- [Thanh đứng ở 50% lâu] → Người xem có thể nghĩ là treo. `current_label` + đồng hồ giây làm rõ.
- [Run kẹt ở `running` sau khi service chết] → Service dọn lúc khởi động (D9). Nếu service không lên lại
  thì nút vẫn bị khoá. Đó là tín hiệu đúng, vì không còn ai để chạy.

## Migration Plan

1. Migration 016 + `KEEP_ON_REBUILD`, chạy `tests/test_connect_migrations.py`.
2. Script với `--once --dry-run` (in kết quả, không ghi DB, không gọi `POST`), rồi `--once` thật.
3. Service trong compose, API, tab.
4. Gỡ: dừng service; bảng giữ lại (migration không xoá dữ liệu, theo `schema-migrations`).

## Open Questions

- Agent tiếp theo có dùng chung chuẩn Partner API (`X-API-Key`, `/capabilities`) không? Nếu có thì D3
  đủ dùng mà không phải sửa.
