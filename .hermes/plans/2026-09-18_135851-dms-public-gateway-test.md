# DMS Public API Gateway — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task. Nếu skill đó không có, dùng quy trình TDD và review hiện có; không giả định một skill/API chưa được nạp. Chỉ triển khai sau khi người dùng duyệt phạm vi; không tự commit/push/deploy.

**Goal:** Chạy đúng helper và API phân loại của `D:\dms-feedback-classification` qua Gateway public, chứng minh định tuyến, danh tính, hành vi lỗi và usage; không làm ảnh hưởng dữ liệu/SharePoint/Dashboard đang vận hành.

**Architecture:** Giữ `GeminiClient.generate()` / `generate_json()` và hợp đồng `GeminiResponse`; thêm backend `gateway` dùng OpenAI-compatible HTTP. Identity/correlation có scope riêng cho request và worker, không đặt username vào singleton. Gateway-only mặc định fail-closed; không tự chuyển sang Google khi Gateway lỗi.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic Settings, requests, pytest, SQLite; LiteLLM Gateway + Nginx, PostgreSQL SpendLogs và token_ledger_v2 ở hệ thống Gateway. Không cần thêm OpenAI SDK/LiteLLM SDK vào DMS.

---

## 1. Phạm vi và bằng chứng đã kiểm tra

Ngày lập: 2026-09-18. Chỉ đọc source và Git, chưa chạy test, chưa đọc `.env`/credential, chưa gọi inference hoặc thay đổi runtime.

- Target DMS: `D:\dms-feedback-classification`; branch `ChiThanh`; HEAD `63cc633ee185ab8d7fed73fbf9fdf12ebf5150d4`; remote `https://github.com/ThanhDT127/dms-feedback-classification.git`. Git status chỉ thấy `.hermes/` untracked.
- Workspace Gateway: `D:\token-ledger-dashboard`; branch `ChiThanh`; HEAD `e1b402087d8ea12f7bbbf708f96a5e3418328796`; remote `https://github.com/ursweetheart/token-ledger-dashboard.git`. Có WIP đã tồn tại; không ghi đè/cherry-pick/merge.
- URL người dùng cung cấp: `http://apigateway.rangdong.com.vn:50888/`.
- Nội dung trang được đính kèm là `Status unknown / Waiting for first measurement`; không phải bằng chứng inference, readiness database hoặc provider. Chưa xác minh live từ máy này.
- Nhật ký `docs/archive/gateway/dua-dms-qua-gateway-31-08.md` thuộc thử nghiệm DMS trước đây; không chứng minh code hoặc runtime ở target hiện tại đã tích hợp.

### Bảng bằng chứng source hiện tại

Các đường dẫn DMS dưới đây tính từ target repo, các đường dẫn Gateway tính từ workspace Gateway.

| Thành phần | Bằng chứng | Hệ quả cho kế hoạch |
|---|---|---|
| Backend DMS | `service/src/dms/settings.py:129-142` chỉ chấp nhận `vertex`, `apikey`; `gemini_client.py:63-111` gọi SDK Google | Chỉ đổi URL/config chưa đủ; cần nhánh Gateway thực sự |
| Product extraction | `pipeline/rag_product.py:190` gọi `generate`; lỗi trả `NONE` | Phải đi qua Gateway và không nuốt lỗi transport/auth thành thành công |
| Issue classification | `pipeline/issue_classifier.py:424` gọi `generate_json`; `:494-588` parse/retry mini-batch và từng hàng | Kiểm tra JSON array, row_index, thiếu/trùng hàng, số attempt thực tế |
| Text API | `web/api/classify.py:43-97` đã có user xác thực nhưng chưa truyền tới LLM; chỉ ghi usage classifier | Scope phải bao cả product extraction và classification; tránh bỏ usage RAG |
| File API + worker | `classify.py` lưu job owner; `classification_worker.py:209-216` chạy pipeline ở thread | Khôi phục identity từ job owner khi thực thi, không dựa vào context của HTTP đã kết thúc |
| Watcher SharePoint | `watcher.py:276` dùng `system_watcher`, `:343` gọi pipeline | Đây là tác vụ hệ thống, không được gán giả thành người tải file; cần chính sách riêng |
| Settings probes | `web/api/settings_api.py:182,307` có generation thủ công và khi lưu settings | Không bỏ sót, không phát sinh paid request chỉ vì lưu Gateway config |
| Local usage | `usage_tracker.py:16-28` chỉ có model/type/job/token/cost; pipeline dùng `_last_usage` và `_current_job_id` mutable | Chưa đủ đối soát từng response/attempt và dễ stale/cross-job khi dùng singleton |
| Error handling | `runner.py:65-88,266-294`, `classify.py:59-66`, classifier/RAG catch rộng | Cần typed Gateway errors xuyên qua các lớp; không báo job completed bằng fallback rỗng khi LB chết |
| Retry | `gemini_client.py` retry mọi exception; `http_client.py:24-28` retry cả POST; worker còn requeue | Không dùng nguyên `create_session()` hiện tại cho paid POST; chặn nhân retry giữa các tầng |
| Timeout | `gemini_client.py:119-125` dùng ThreadPoolExecutor context manager | `future.result(timeout)` chưa đảm bảo thoát nhanh vì executor shutdown có thể đợi; Gateway dùng timeout transport thật |
| Identity | `web/deps.py:115-148` lấy JWT sub và tra user active | Dùng username từ user đã xác thực, không tin `X-User`/username/department của browser |
| Catalog Gateway | `db/02_catalog.sql:15`: agent 6, code `dms-feedback` | Tái sử dụng code; không tạo thêm agent theo tên thư mục |
| Route Gateway | `docker/gateway/nginx.conf:133-139` cho `/gateway/v1/chat/completions` và `/v1/chat/completions` | Base dự kiến là URL public + `/gateway/v1`, không phải trang `/` |
| Model Gateway | `config.gateway.yaml:45-57`: `gemini-flash-lite` → `gemini/gemini-3.5-flash-lite`; DMS default `gemini-2.5-flash-lite` | Khác model; cần duyệt alias/model, không âm thầm đổi để test xanh |
| User Gateway | `config.gateway.yaml:140` nhận `X-User`; `:265` bật tag filtering | Kiểm tra runtime, virtual-key tag và actual model trong SpendLogs, không chỉ tin config local |
| Data/network | `web/app.py:203-210` restore/sync SharePoint và start worker; worker upload output riêng | Không chạy web mặc định trên dữ liệu thật; tắt input upload chưa cô lập hết egress |
| Existing tests | `tests/test_gemini.py` mock Google; `tests/conftest.py` có auth overrides và Settings đọc dotenv mặc định | Chưa phải bằng chứng JWT→Gateway hoặc provider-real; cần isolation fixture trước khi chạy |

Không tìm thấy đường OCR/cloud embeddings trong source runtime đã rà soát. RAG ở đây có extraction LLM + matching local, không mặc định coi là vector embedding service. Không thêm OCR vào phạm vi. Trường department của analytics là đơn vị trong dữ liệu nghiệp vụ, không dùng thay phòng ban của người gọi.

## 2. Contract kết nối đề xuất

Luồng web:

`User → DMS JWT/RBAC → scope(username, operation/job) → RAG + classifier → public LB /gateway/v1/chat/completions → LiteLLM → provider → SpendLogs → ETL → token_ledger_v2`

Cấu hình mới dự kiến trong Settings (tên mới được đề xuất, chưa tồn tại):

| Biến | Quy tắc |
|---|---|
| `GEMINI_BACKEND=gateway` | Opt-in, giữ hai backend cũ; không tự switch sau lỗi |
| `LLM_GATEWAY_BASE_URL` | Dự kiến `http://apigateway.rangdong.com.vn:50888/gateway/v1`; chỉ nối `/chat/completions` một lần; live phải dùng TLS hoặc kênh mạng được bảo vệ |
| `LLM_GATEWAY_API_KEY` | Virtual Key riêng cho test DMS, tag `dms-feedback`, model allowlist, quota/expiry; không dùng master key |
| `LLM_GATEWAY_MODEL` | Alias được duyệt; ứng viên theo config local: `gemini-flash-lite`; giữ nguyên token alias, không normalize như tên Gemini |
| `LLM_GATEWAY_TIMEOUT_SECONDS` | Positive; đặt rõ connect/read timeout và deadline test; không coi requests read timeout là hard wall-clock deadline |
| `LLM_GATEWAY_MAX_OUTPUT_TOKENS` | Positive; giới hạn rõ để tránh chi phí/JSON cắt cụt; không tự bật/tắt reasoning cho model chưa xác minh hỗ trợ |

- Credential chỉ ở backend. Scope tạo header `X-User` và JSON `user` mỗi request, không mutate session headers dùng chung. Không chuyển JWT của DMS tới Gateway/provider.
- Department do directory/mapping của ledger phân giải. Username DMS có thể chưa có trong directory: đánh dấu unresolved, không tự nhận là đúng phòng ban.
- Không tự gọi `/v1/models`: ingress source hiện chỉ allowlist completion routes, có thể 404 theo thiết kế.
- Root status page chỉ liveness. Kiểm tra public route/model bằng một generation được duyệt riêng.
- `generate_json` hiện cần JSON list; không áp `json_object` một cách máy móc. Characterization với top-level array; chọn response format/schema được Gateway/model hỗ trợ, giữ nguyên contract list. Nếu không hỗ trợ: BLOCKED hoặc xin duyệt phương án tương thích, không đổi classifier thành object âm thầm.
- Tắt redirect ở HTTP transport để tránh chuyển Authorization sang đích khác. TLS verify bật; không dùng `verify=False`.
- Default fail-closed: thiếu identity/key, 400/401/403, policy/model error không retry/fallback. Transport lỗi được phân loại, tối đa retry có kiểm soát ở một tầng. Không tự retry paid POST khi read timeout/mất response sau khi gửi; đó là trạng thái chưa biết đã tính tiền hay chưa.
- Hai backend Google cũ chỉ dùng khi operator chủ động cấu hình lại, không phải automatic fallback.

## 3. Thứ tự triển khai sau khi duyệt

Mọi task thay code: thêm test đỏ → chạy test xác nhận đúng nguyên nhân → sửa tối thiểu → chạy xanh → review diff. Không commit/push trừ khi có yêu cầu riêng.

### Task 1 — Khóa baseline và cô lập test

**Files:** sửa `service/tests/conftest.py`; tạo `service/tests/gateway_support.py` nếu cần tái sử dụng fixture; tham chiếu `service/tests/test_app_lifespan.py`, `test_classify_persistent_jobs.py`, `test_classification_worker.py`.

1. Ghi Git branch/HEAD/status mới, giữ WIP. Đọc repo guidance nếu xuất hiện thêm.
2. Fixture chặn đọc `.env` và auto-dotenv trước import; `_env_file=None` cho Settings test. Không dùng credential/project/user store thật.
3. WORK_DIR/DATA_DIR/LOG_DIR, SQLite, users, input/output/checkpoint đều ở temp. Với file route, xử lý cả `WORK_DIR = SERVICE_DIR / "work"` đang hard-code bằng override test; không vô tình ghi `service/work`.
4. Fake SharePoint/Graph/SMTP/Teams boundary, bao gồm startup restore/sync và output upload. Giữ thực thi worker/pipeline/usage row thực, không thay bằng helper mô phỏng.
5. Offline egress deny; HTTP mock dùng loopback allowlist nếu cần. Không start watcher hoặc compose production.
6. Chạy baseline tập trung rồi full suite trong isolation. Ghi lỗi tồn tại sẵn riêng; không đổi auth/validator hoặc fake model artifacts chỉ để xanh.

### Task 2 — Settings và secret handling

**Modify:** `service/src/dms/settings.py`, `service/src/dms/web/api/settings_api.py`.
**Tests:** `service/tests/test_settings.py`, `test_settings_provider.py`, `test_settings_api.py`.

1. Test nhánh gateway không cần credential Google, nhưng cần URL/key/alias hợp lệ; thiếu field bị từ chối. Giữ validation SharePoint/JWT hiện tại; fixture dùng placeholder offline, không nới production validation.
2. Test alias không bị lowercase/replace tự động, path không nhân đôi, redirect/TLS policy rõ ràng.
3. Thêm key mới vào masking cho cả lowercase field và uppercase dotenv fallback. Không đưa secret vào repr, exception, API settings response, logs.
4. Pha đầu cấu hình Gateway bằng process environment/ignored local config, chưa làm UI editor/key form. Settings save chỉ validate config trong gateway mode; trả lời đúng là đã lưu, không tuyên bố test kết nối khi chưa gọi.
5. `/test-connection` vẫn explicit generation, dùng danh tính admin xác thực và ghi operation riêng. Không thêm automatic paid probe khi reload/settings save.

### Task 3 — Adapter Gateway nhỏ, không thêm SDK

**Modify:** `service/src/dms/gemini_client.py`, `service/src/dms/exceptions.py`.
**Create test:** `service/tests/test_gateway_client.py`.
**Regression:** `service/tests/test_gemini.py`, `test_http_client.py`.

1. Transport requests riêng với retry adapter mặc định tắt; không dùng factory SharePoint có POST retries.
2. Thêm dispatch gateway ở cả generate/generate_json trước vòng retry legacy, giữ Google code path cũ.
3. Assert tại HTTP wire: exact URL, model, Authorization có mặt nhưng không log, X-User và body user khớp, temperature, output cap, JSON mode; reject thiếu scope trước network.
4. Map response text/usage về GeminiResponse; thêm optional response_id/model/correlation fields tương thích caller cũ nếu cần đối soát. Không bịa usage khi missing; không coi zero là bằng chứng model không tính tiền.
5. Typed sanitized error phân biệt auth/policy/rate-limit/transport/invalid-response. Không lộ response body, request headers hoặc key qua exception chain/log.
6. Test 401/403/400 không retry; 429/5xx theo policy bounded đã chốt; read timeout không tự replay; invalid JSON/finish_reason truncated không thành success.
7. Test gateway mode không khởi tạo Google client dù direct key có trong môi trường.

### Task 4 — Identity/correlation xuyên request và persisted worker

**Create:** `service/src/dms/gateway_context.py` — scope nhỏ bằng ContextVar + immutable context, không tạo framework mới.
**Modify:** `service/src/dms/web/api/classify.py`, `web/api/settings_api.py`, `classification_worker.py`, và `watcher.py` chỉ ở boundary thực thi/policy.
**Create tests:** `service/tests/test_gateway_identity.py`, `service/tests/test_gateway_routes.py`.
**Regression:** `test_web_authz.py`, `test_classify_persistent_jobs.py`, `test_classification_worker.py`, `test_watcher_job_tracking.py`.

1. Scope text route sau `get_current_user`, bao cả RAG và classifier; reset bằng finally.
2. Worker tự tạo scope từ persisted `owner_username` + job_id mỗi lần claim/retry, không lấy header request đã kết thúc. Test hai user chạy đồng thời và job được worker mới nhận sau restart.
3. Test authenticated ASGI với JWT thật ký bằng secret test, user store test, expired JWT/disabled user/spoofed browser X-User. Auth override đơn thuần không đủ.
4. Watcher: mặc định không chạy ở live phase đầu; Gateway mode chặn generation nếu chưa có trusted mapping/policy system actor. Giữ `system_watcher` được phân loại riêng nếu operator duyệt mapping, không thay bằng user đang mở UI.
5. CLI `service/scripts/run_pipeline.py`, `run_and_compare.py`, `test_pipeline.py`, `test_sharepoint.py` là đường gọi ngoài HTTP: pha đầu chưa mở live; thiếu trusted identity phải fail closed. Chỉ thêm explicit operator context khi được duyệt, không hard-code service user vào mọi call.
6. Không dùng ContextVar từ HTTP để giả định tự truyền qua thread mới; khởi tạo lại tại worker. Nếu transport dùng executor, pass immutable request data trước submit hoặc copy context rõ ràng.

### Task 5 — Chặn thành công giả và retry khuếch đại

**Modify:** `service/src/dms/pipeline/rag_product.py`, `pipeline/issue_classifier.py`, `pipeline/runner.py`, `classification_worker.py`, `web/api/classify.py`, `exceptions.py`.
**Create test:** `service/tests/test_gateway_fail_closed.py`.
**Regression:** `service/tests/test_pipeline.py`, `test_classification_worker.py`, `test_gemini.py`.

1. Characterization trước: Gateway error hiện có thể bị RAG/classifier nuốt, rồi runner tạo kết quả dự phòng. Test phải chứng minh lỗi đi qua actual caller, không chỉ helper.
2. Rethrow Gateway typed errors trước broad catch ở tất cả sibling paths: RAG extraction, runner RAG wrapper, text route inner catch, classifier `_llm_json_call`, mini-batch/single-row retries, runner per-row fallback.
3. Giữ keyword/BM25 matching hợp lệ; giữ business output schema. Gateway transport/auth failure không được ghi labels rỗng rồi báo completed. Semantic JSON thiếu hàng có thể retry có budget riêng, không chuyển thành transport retry vô hạn.
4. Không làm mất error classification khi runner wrap PipelineError; worker nhận nonretryable auth/config thì fail ngay. Transient job retry/checkpoint có giới hạn, ghi rõ attempt; không nhân tầng transport × row × job không kiểm soát.
5. Test cancel/resume, recovery cùng helper, không dùng usage cũ của lần trước, không coi lỗi persistence là lý do gọi model thêm lần nữa.

### Task 6 — Usage đúng từng call, giữ schema tương thích

**Modify:** `service/src/dms/usage_tracker.py`, `gemini_client.py`, `pipeline/runner.py`, `pipeline/rag_product.py`, `pipeline/issue_classifier.py`, `web/api/classify.py`, `web/deps.py` nếu cần wiring sink.
**Tests:** `service/tests/test_usage_tracker.py`, tạo `service/tests/test_gateway_accounting.py`; regression `test_daily_stats.py`, `test_metrics.py`.

1. Characterization chứng minh thiếu usage RAG ở text API, `_last_usage` bị ghi đè khi classifier retry, `_current_job_id` mutable khi shared runner.
2. Gateway mode ghi usage một lần tại response boundary qua request-scoped sink dùng UsageTracker hiện có; không tiếp tục ghi trùng tại các legacy aggregate call sites. Không viết hệ thống ledger mới.
3. Additive SQLite migration (nếu persistence đối soát được duyệt): nullable source/username/response_id/operation_id/attempt_id/requested_model, giữ cột cũ và rows lịch sử; unique theo source+response_id chỉ cho response_id thực sự có mặt. Không sửa/xoá dữ liệu cũ.
4. Failed/unknown-outcome attempts ghi trạng thái audit, không giả lập successful usage; semantic retry là call riêng, không dedupe theo job_id.
5. Không tính alias theo giá model mặc định cũ. Nếu không có giá/model thực được xác nhận, báo estimate unknown/unmapped rõ trong bằng chứng; không gọi 0 USD là miễn phí.
6. Không cộng local usage với SpendLogs thành tổng tiền kép; local là đối chứng, Gateway là nguồn transaction ingest đã có provenance.

### Task 7 — Harness và tài liệu chạy từ đúng repo DMS

**Create:** `service/scripts/test_gateway.py`, `service/tests/test_gateway_harness.py`, `docs/testing/api-gateway.md`.

1. Harness gọi actual GeminiClient/RAG/classifier, authenticated ASGI và real worker pipeline; có mode offline/provider-real riêng, default offline.
2. Live explicit opt-in; chỉ đọc đúng file credential người dùng cho phép hoặc environment process. Không dò secret ở repo khác; không dump config. Không thêm key vào example/template.
3. Synthetic text/Excel, temp DB/users/checkpoint/output; SharePoint/notification boundaries mocked và ghi rõ. Live ASGI không đồng nghĩa test web process/browser production.
4. Run ID và artifact JSON chỉ chứa route host/path, commit, case status, response/attempt IDs, model, username test, token/latency/error class; không chứa prompt thật/key/JWT. Tách report PASS/FAIL/BLOCKED/NOT RUN.
5. CLI dự kiến sau khi tạo: `python scripts/test_gateway.py --mode offline`; live `python scripts/test_gateway.py --mode live --max-model-attempts 12 --deadline-seconds 300 --max-output-tokens 4096`. Harness enforce budget trước mỗi model attempt, không chỉ mỗi API/job; flags là giao diện mới cần test, chưa tồn tại.
6. Đề xuất live phase đầu tối đa 12 model attempts cho toàn lượt, output cap 4096 mỗi attempt, concurrency 1; một text + một Excel tối đa 3 hàng + identity/recovery probes trong budget. Dừng khi đạt cap; không tự tăng để hoàn thành ma trận. Trần USD cần operator duyệt và enforce bằng Virtual Key budget trước run; token cap không thay thế trần chi phí.

## 4. Ma trận test / tiêu chí nghiệm thu

| Gate | Test | PASS khi |
|---|---|---|
| Offline transport | generate và generate_json qua HTTP mock | Wire URL/header/body đúng; không Google egress; JSON array contract nguyên vẹn |
| Auth attribution | Text, admin test-connection, queued file, parallel users | JWT user = X-User = body user; worker owner giữ đúng; spoof không thắng |
| Failure policy | Missing identity/key, 400/401/403, 429, 502/503, timeout, redirect | Lỗi đúng lớp, không bypass, attempt bounded, không thành công giả |
| Business quality | RAG extraction, classification, Excel, partial/malformed/truncated JSON | Đúng số dòng và row_index, labels hợp lệ, checkpoint/cancel không hồi quy |
| Accounting | Multiple LLM calls + retries + concurrency | Mỗi response có usage được ghi đúng một lần và đúng user/job, không stale |
| Isolated fault matrix | baseline → 1 Proxy down → all Proxies down → LB down → restore | Chạy riêng cả product extraction và JSON classification; failover trước-send đúng; LB down fail-closed; recovery cùng path |
| Public bounded live | DMS → đúng FQDN/port/path → provider | Result nghiệp vụ hợp lệ, route/actual model xác minh, không gọi Proxy/provider trực tiếp |
| Persisted SpendLogs | Poll read-only theo response ID có deadline | Agent tag dms-feedback, end_user, requested/actual model, tokens và attempts đối chiếu được |
| Ledger/department | Existing ETL + read-only API/UI evidence | Đúng agent/user/department hoặc unresolved minh bạch; không double count lịch sử scrape |
| ETL idempotency | Rerun ở DB test hoặc maintenance scope được duyệt | Không phát sinh fact trùng; chưa được duyệt thì NOT RUN, không tự chạy ETL production |

Không dừng Proxy/LB/Redis/PostgreSQL trên Gateway public để thử lỗi mặc định. Fault injection chạy stack riêng; việc chặn client cục bộ chỉ chứng minh policy khi client mất kết nối, không thay cho one-Proxy failover thật. Muốn fault test trên public topology phải có maintenance window, quyền điều khiển và rollback được duyệt riêng. Giữ Dashboard `web/api/pgadmin`, networks và database volumes nguyên trạng; tuyệt đối không `docker compose down -v`.

Mỗi fault chạy tuần tự: tạo baseline → inject → xác minh fault đang tồn tại → gọi đúng helper → thu bằng chứng → restore trong finally → health + recovery cùng helper. Không chạy recovery song song làm mất cửa sổ lỗi.

## 5. Lệnh verification dự kiến

Chạy từ `D:\dms-feedback-classification\service` trong env test đã cô lập; đây là lệnh cho pha implementation, CHƯA chạy ở lượt lập kế hoạch:

- `.venv/Scripts/python.exe -m pytest tests/test_gateway_client.py tests/test_gateway_identity.py tests/test_gateway_routes.py tests/test_gateway_fail_closed.py tests/test_gateway_accounting.py tests/test_gateway_harness.py -q`
- `.venv/Scripts/python.exe -m pytest tests/test_gemini.py tests/test_settings.py tests/test_settings_provider.py tests/test_settings_api.py tests/test_pipeline.py tests/test_classification_worker.py tests/test_classify_persistent_jobs.py tests/test_usage_tracker.py tests/test_web_authz.py tests/test_watcher_job_tracking.py -q`
- `.venv/Scripts/python.exe -m pytest tests -q`
- `.venv/Scripts/python.exe -m ruff check src tests`
- `.venv/Scripts/python.exe -m ruff format --check src tests`
- `.venv/Scripts/python.exe -m mypy --config-file pyproject.toml src`
- `git diff --check` và `git status --short`.

Nếu venv hiện có thiếu package, inspect trước; chỉ cài dev dependency vào env riêng sau khi được phép. CI dùng `service/requirements.txt` bên cạnh pyproject; tránh thêm dependency không cần thiết và không sửa manifest để che lỗi baseline. Không hứa số test PASS trước thực thi.

## 6. Rủi ro, giới hạn và quyết định cần duyệt

1. **HTTP public:** URL hiện không TLS. Không gửi real Virtual Key hoặc dữ liệu công ty qua Internet plaintext. Cần endpoint HTTPS được xác minh hoặc VPN/tunnel/kênh riêng mã hóa; không tự đổi port 50888 thành 443 hay tuyên bố HTTPS đã hoạt động.
2. **Model:** App default và alias hiện tại khác model. Xác nhận alias và actual upstream tại server; giữ thay đổi ở process test, không tự sửa model production. Danh sách model trả về cũng chưa chứng minh account có quyền inference.
3. **Key:** Cần Virtual Key DMS test, tag/model restriction/expiry/budget; người dùng chỉ định đường dẫn file local được đọc khi chạy, không gửi key trong chat. Việc tạo/xóa key là thao tác server cần duyệt và đọc lại trạng thái.
4. **Identity:** Cần user test tương ứng directory/department ledger. Watcher dùng system actor hay ánh xạ uploader phải chốt riêng; không tự dùng email/đơn vị từ Excel làm người tiêu token.
5. **Accounting access:** Cần quyền read-only hoặc export sanitized SpendLogs và ledger theo response IDs. Không có quyền thì kết luận tối đa app/provider smoke, chưa full accounting.
6. **Isolation:** Native Python/ASGI test là ưu tiên trên Windows; Gunicorn trong compose là Linux runtime. Không chạy compose hiện có để tránh dùng chung volume, auto-sync/worker và credentials.
7. **Privacy:** Config local có `store_prompts_in_spend_logs: true`; cần kiểm tra sanitation runtime trước dữ liệu thật. Chỉ synthetic prompts; không lấy khẳng định privacy từ nhật ký cũ làm bằng chứng hiện tại.
8. **Scope/YAGNI:** Không redesign UI, không thêm SDK/framework, không sửa toàn hệ thống retry legacy, không triển khai lại Gateway. Sửa call boundaries và accounting cần thiết cho test đáng tin cậy; thay đổi SQLite additive phải được đưa rõ trong scope duyệt.

### Các chặng duyệt

- **A — Implementation + offline/mock:** adapter, identity, fail-closed, accounting tests, harness; không paid calls, không runtime production.
- **B — Public provider-real:** chỉ sau A, đường truyền an toàn, alias/virtual key/user mapping và budget đã chốt; synthetic data, không server shutdown.
- **C — Public resilience/ledger đầy đủ:** quyền read-only đối soát và maintenance/fault/ETL approval riêng khi cần. Phần thiếu báo BLOCKED/NOT RUN.

## 7. Deliverable và rollback

- Deliverable hiện tại chỉ là kế hoạch này. Sau triển khai: code DMS + focused/full test outputs + tài liệu/harness và artifact sanitized; báo riêng offline, helper-real, ASGI/app-E2E, SpendLogs, ledger và billing-export (billing-export ngoài phạm vi).
- Thành công không chỉ là HTTP 200: phải chứng minh correct route, identity, valid classification, bounded failure policy và accounting ở mức bằng chứng thực tế có được.
- Rollback chỉ ngừng tiến trình test, bỏ environment override, giữ backend/config production cũ và mọi dữ liệu. Không xóa job/history/SpendLogs production. Ephemeral test key chỉ revoke theo quyền đã cấp và xác minh lại; fault stack phải restore/cleanup đúng tài nguyên test.
- Không commit/push/merge/deploy ở bất kỳ bước nào nếu chưa được yêu cầu riêng.
