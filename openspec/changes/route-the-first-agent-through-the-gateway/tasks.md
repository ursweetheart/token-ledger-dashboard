# Thứ tự làm — mỗi bước một phép đo

Nguyên tắc: **không bước nào được kết luận bằng "chạy không báo lỗi"**. Mỗi bước phải kết
thúc bằng một con số hoặc một dòng dữ liệu soi được. Ba lỗi im lặng của ngày 29/08 đều trông
y hệt thành công.

## 1. Dựng lại nền, chưa sửa gì

- [x] 1.1 Bật Docker Desktop. `docker compose --profile gateway up -d`.
      **Hai lần trượt trước khi lên, cả hai đều KHÔNG phải lỗi cấu hình:**
      (a) container cũ từ 31–35h trước còn ghi ID của mạng đã bị xoá →
      `network 2bedb31550a1… not found`; gỡ bằng `--force-recreate` (dựng lại container
      từ image có sẵn, KHÔNG build lại, không đụng named volume).
      (b) `token-ledger-web` không bind được `192.168.20.111:8080` — thuộc tầng dashboard,
      ngoài phạm vi change này, để nguyên. Ghi lại vì nó sẽ còn trượt ở lần dựng sau.
      **Đính chính hiểu nhầm:** `--profile gateway` KHÔNG thay tầng dashboard bằng tầng
      Gateway — dịch vụ không khai `profiles:` thì luôn chạy, nên `api`/`web`/`pgadmin`
      cũng được kéo lên cùng
- [x] 1.2 ĐO: 5 dịch vụ Gateway (`redis`, `redis-replica`, `litellm-1`, `litellm-2`,
      `gateway-lb`) đều `healthy` — **5/5 ĐẠT**. `gateway-lb` phải gọi riêng
      (`up -d gateway-lb`) vì lượt trước đã đứt ở `web` trước khi tới nó
- [x] 1.3 ĐO: database `litellm` có **75** bảng `LiteLLM_*`, `LiteLLM_SpendLogs` tồn tại;
      `token_ledger_v2` có **đúng 0** bảng `LiteLLM_*` → **ranh giới hai sổ còn nguyên**.
      Con số 75 khớp đúng chú thích trong `docker-compose.yml` — một xác nhận độc lập
- [x] 1.4 Mốc `LiteLLM_SpendLogs` = **1 dòng** (của lượt `curl` 29/08). **Không phải 0** —
      mọi phép đếm sau phải trừ mốc này ra

## 2. Chứng minh tuyến `gemini-flash-lite` còn gọi được (chưa đụng DMS)

- [x] 2.1 Gọi `POST /v1/chat/completions` qua `127.0.0.1:4000`, master key,
      `model: gemini-flash-lite` (bí danh), `X-User: tuan.tran`, chuỗi mồi
      `PHEP-DO-31-08-CHUOI-MOI`
- [x] 2.2 ĐO: **HTTP 200**, nội dung trả về `"OK"`, `usage` = 24 + 1 = **25 token**.
      Tuyến `gemini-flash-lite` → `gemini-3.5-flash-lite` **đã chứng minh gọi được thật**,
      không phải suy từ `/health/liveliness`
- [x] 2.3 ĐO: đúng **1 dòng mới** (2 tổng, mốc là 1). `request_id lG-UarHhIYXmosUPv4ihmQ8`
      **khớp đúng `id` trong response curl** — không phải dòng trùng hợp.
      `total_tokens 25` = 24+1 khớp `usage` của API · `spend 9,7e-06` > 0 ·
      `end_user tuan.tran` (từ header `X-User`) · `api_key litellm_proxy_master_key`.
      **`model` = `gemini/gemini-3.5-flash-lite`, KHÔNG phải bí danh** → xác nhận đúng dự
      đoán rút ra khi tự soát (`reconstruct_model_name` ưu tiên `metadata["deployment"]`),
      nên tiêu chí nghiệm thu của 6.6 giữ nguyên
- [x] 2.3b **BẪY ĐO ĐẠC — ghi lại để không ai vấp lại.** Query ngay sau khi curl trả về thì
      `count(*)` vẫn là **1**: LiteLLM ghi sổ **bất đồng bộ, theo lô**. Dòng xuất hiện sau
      ~4 giây. Một phép đo "gọi xong, đếm ngay" sẽ kết luận **SAI** rằng "Gateway không ghi
      sổ". Mọi phép đếm từ nay phải **theo dõi lặp cho tới khi đổi**, không đếm một lần.
      Cùng họ với kết luận sai sáng 26/08
- [x] 2.4 ĐO: chuỗi mồi `PHEP-DO-31-08-CHUOI-MOI` xuất hiện **0 lần** trên toàn bộ
      `pg_dump` của database `litellm`. Cột `messages` = `{}`. Trong
      `proxy_server_request` (9.221 ký tự): `messages` = `[{"role":"user","content":
      "redacted-by-litellm"}]`, `prompt` = `""`, `input` = `""`, mà `metadata.headers`
      vẫn giữ nguyên `x-user: tuan.tran`.
      → Bốn khoá ghi sổ hoạt động đúng như đo 26/08, trên đúng đường change này dùng
      (quyết định ⑦ **đã kiểm**, không còn là suy luận).
      **Ghi chú tiện thể:** ba khoá bị xoá đúng là `messages` / `prompt` / `input` — đúng ba
      tên mà `perform_redaction` biết. Đây là bằng chứng gián tiếp củng cố lo ngại ở mục 5
      nhật ký 30/08: thân request Gemini nguyên bản dùng `contents`, không nằm trong ba tên
      đó. Chọn phương án B đã tránh luôn lỗ hổng ấy
## 3. Cấp Virtual Key cho `dms-feedback` và gắn `tags`

- [x] 3.1 Thêm `tags: ["dms-feedback"]` vào tuyến `gemini-flash-lite` trong
      `docker/gateway/config.gateway.yaml`, kèm chú thích nêu rõ nó là trục chọn khoá
      project và **vô tác dụng nếu thiếu 3.1b**
- [x] 3.1b Khai `enable_tag_filtering: true` trong `router_settings`. Đã ghi hẳn vào file
      lý do và kiểu hỏng, vì mặc định là `False` (`router.py:430`)
- [x] 3.2 **Sửa lại giả định của tasks.md.** Khoá KHÔNG cần cấp mới từ đầu — đã có sẵn
      `key_alias dms-feedback` cấp 29/08, `models {gemini-flash-lite}`, `spend 1,17e-05`
      khớp đúng dòng SpendLogs 29/08. Nhưng nó **thiếu `tags` trong metadata**, và
      **giá trị `sk-…` gốc không lưu ở đâu** (LiteLLM chỉ giữ hash; đã tìm `.env` của DMS,
      `docs/reference/`, thư mục kết quả đo — không có). Sửa metadata là ngõ cụt vì sửa
      xong vẫn không ai gọi được. → Cấp khoá mới `dms-feedback-tagged` có
      `metadata.tags`, **giữ nguyên khoá cũ** làm hồ sơ phép đo 29/08 (chọn phương án 1,
      không chặn không xoá — thứ mất đi khi xoá là bằng chứng)
- [x] 3.2b Xác minh LiteLLM đọc tag ở ĐÂU: `litellm_pre_call_utils.py:1942`
      `key_metadata = user_api_key_dict.metadata` → đúng là trường `metadata` của khoá.
      Trường `tags` cấp cao trong response `/key/generate` là thứ khác và đang `null`;
      bảng `LiteLLM_VerificationToken` **không có cột `tags`**
- [x] 3.3 Gọi lại bước 2.1 bằng Virtual Key mới → **HTTP 200**, trả `"XONG"`, 22+2=24 token
- [x] 3.4 ĐO: `key_alias = dms-feedback-tagged` · `model gemini/gemini-3.5-flash-lite` ·
      `total_tokens 24` · `spend 1,16e-05` · `end_user tuan.tran`.
      **Lưu ý:** cột `tags` và `routing_decision` trong SpendLogs đều RỖNG → sổ **không**
      chứng minh được tag có lọc hay không. Chỉ phép kiểm âm 3.6–3.7 mới kết luận được
- [x] 3.5 ĐO (kiểm âm model): Virtual Key gọi `gemini-flash` → **HTTP 403**
      `key_model_access_denied`. Giới hạn model là thật
- [x] 3.6 **Sửa lại chính phép đo trước khi chạy.** Bản đầu định kết luận bằng "10/10 lượt
      thành công" — SAI, vì `num_retries: 3` sẽ thử lại qua tuyến đúng và che mất lỗi.
      Phải đo *lượt chạm*, không đo *kết quả cuối*. Đã dựng tuyến mồi: cùng
      `model_name: gemini-flash-lite`, `tags: ["khong-ai-dung"]`, `api_key` cố ý sai
- [x] 3.7 ĐO bằng ba dấu vết độc lập, 10 lượt gọi bằng Virtual Key có tag:
      · **10/10 HTTP 200**
      · **10 dòng SpendLogs mới** (14 − 4), không thừa không thiếu
      · **`attempted_retries = 0` trên cả 10 dòng** → không lần thử lại nào che giấu gì
      · **0 lần chạm tuyến mồi** trong log của cả `litellm-1` lẫn `litellm-2`
      → **Tag lọc ĐÚNG.** Quyết định ⑧ đã kiểm, không còn là suy luận
- [x] 3.8 ĐO hành vi request KHÔNG tag (quyết định ⑨), 8 lượt bằng master key:
      **7/8 thành công, 1/8 TRƯỢT** — và lượt trượt đúng là **chạm tuyến mồi**:
      `400 Bad Request` từ `generativelanguage.googleapis.com` (khoá sai bị Google từ
      chối; lỗi bị `MaskedHTTPStatusError` che nên grep `API key not valid` không bắt
      được), rồi `ValueError: Not allowed to access model due to tags configuration.
      Passed model=gemini-flash-lite and tags=['khong-ai-dung']`.
      → **12,5% request không tag rơi nhầm tuyến.** Quyết định ⑨ đã kiểm.
      Hệ quả phải nhớ: agent lỡ mất `tags` KHÔNG hỏng hẳn — nó hỏng lác đác, khó thấy
- [x] 3.9 Gỡ tuyến mồi (khôi phục từ bản sao lưu), triển khai lại. ĐO lại: đúng
      **1 deployment** `gemini-flash-lite`, `tags ['dms-feedback']`, khoá thật;
      `enable_tag_filtering = True`; một lượt gọi mới → 200, +1 dòng,
      `key_alias dms-feedback-tagged`, `retries 0`
## 4. Nối mạng DMS ↔ Gateway (chưa sửa code DMS)

- [x] 4.1 Thêm khai báo mạng vào `docker-compose.override.yml` của bản clone DMS —
      **chỉ nối thêm vào cuối, không sửa dòng nào đang có**, và vẫn không đụng
      `docker-compose.yml` gốc của nhóm DMS.
      **Bẫy bắt được lúc đọc lại, TRƯỚC khi chạy:** compose gốc của DMS không khai
      `networks:` ở đâu cả → mọi service dùng mạng `default` ngầm định. Nếu chỉ viết
      `networks: [gateway]` thì Compose **bỏ mạng ngầm định đó đi** và `web` rời khỏi mạng
      của chính DMS (nginx sẽ không còn gọi được web). Phải liệt kê **cả hai**:
      `[default, gateway]`
- [x] 4.1b **LỖI đã mắc và đã sửa:** lần viết đầu tôi `>>` thêm một khối `services:` thứ
      hai vào cùng file → `yaml: construct errors: mapping key "services" already defined
      at line 14`. Bắt được ngay ở lát mỏng (`docker compose config`) chứ không phải lúc
      chạy. Đã khôi phục từ bản sao lưu và gộp `networks:` vào đúng khối `web` có sẵn
- [x] 4.1c ĐO cấu hình sau khi gộp: `web` → `networks: {default, gateway}`;
      `gateway` → `external: true, name: token-ledger-dashboard_default`;
      mạng riêng của DMS là `service_default` (tên project là `service` vì compose nằm
      trong thư mục đó). `watcher` và `nginx` không bị đụng tới
- [x] 4.2 ĐO **từ bên trong** `dms-feedback-web` (không phải từ host), bằng `urllib`:
      · `GET /lb-health` → **200** `lb-ok`
      · `GET /health/liveliness` → **200**
      · `POST /v1/chat/completions` kèm Virtual Key → **200**, trả `"OK"`
      Container nằm trên đúng hai mạng: `service_default` + `token-ledger-dashboard_default`
- [x] 4.2b ĐO tiếp cho chắc — lượt gọi từ trong container **có vào sổ**:
      `request_id 3n6UarjKM-eN1e8Po6KtqA8` khớp đúng response · `total_tokens 16` ·
      `spend 7e-06` · `key_alias dms-feedback-tagged` · `end_user tuan.tran`.
      → Quyết định ⑥ **đã kiểm**: không cần `host.docker.internal`, và không phụ thuộc
      cổng bind loopback
- [x] 4.2c **Ghi chú cho việc quy trách nhiệm sau này:** `requester_ip_address` = `172.20.0.9`
      — đó là `gateway-lb`, KHÔNG phải container gọi. Nghĩa là không thể dùng IP để biết
      agent nào gọi; danh tính agent **chỉ** đến từ Virtual Key
## 5. Thêm nhánh backend `gateway` vào `gemini_client.py`

- [x] 5.1 **Gộp còn HAI method thay vì ba.** `_generate_gateway(prompt, temperature,
      json_mode=False)` phục vụ cả hai đường; không cần `_generate_gateway_json` riêng vì
      khác biệt duy nhất là một trường trong payload. Đã thêm `_init_gateway` +
      `_generate_gateway`. `_init_vertex`, `_init_apikey`, `_generate_vertex`,
      `_generate_apikey`, `_generate_apikey_json`, `_extract_usage` **không sửa một dòng**
- [x] 5.1b **Quyết định: dùng `httpx`, KHÔNG dùng `openai` SDK.** Đo trong container:
      `openai` KHÔNG có, `httpx 0.28.1` CÓ. Chọn httpx nên **không thêm dòng nào vào
      `requirements.txt` và không phải build lại image** — giảm hẳn phạm vi đụng chạm vào
      repo của nhóm DMS
- [x] 5.1c **Quyết định: đọc cấu hình từ `os.environ`, không thêm trường vào `settings.py`.**
      Nhờ vậy số file của nhóm DMS bị sửa giữ ở đúng **1**. Hợp lệ vì
      `docker-compose.yml:11` cho `web` một `env_file:` (giá trị `.env` vào cả `os.environ`),
      `settings.py:28` để `extra="ignore"`, và **chính `gemini_client.py` đã đọc/ghi
      `os.environ` sẵn** trong `_init_vertex`. Hai biến: `GEMINI_GATEWAY_BASE_URL`
      (mặc định `http://gateway-lb:4000`) và `GEMINI_GATEWAY_USER` (tuỳ chọn)
- [x] 5.2 Thêm nhánh `gateway` vào công tắc của `generate()` và `generate_json()`, đặt
      **giữa** `vertex` và `apikey` để `apikey` vẫn là nhánh mặc định — lùi lại được chỉ
      bằng một biến môi trường
- [x] 5.3 `X-User` gắn qua `GEMINI_GATEWAY_USER`, **chỉ gửi khi biến được đặt**.
      Đã kiểm: `web/api/classify.py:43` `classify_text(body, user: dict = CURRENT_USER_DEP)`
      **có** cầm danh tính, nhưng `GeminiClient.generate()` nằm sâu bên dưới và không nhận
      nó — luồn xuống sẽ phải sửa thêm nhiều file của nhóm DMS, vượt phạm vi.
      Giải pháp trung thực: đặt `svc.dms-feedback` (định danh **dịch vụ**, đã có sẵn trong
      danh mục tài khoản của dự án), không bịa ra một con người. Việc lấy claim `sub` của
      JWT cho từng người dùng là change riêng
- [x] 5.4 ĐO: `usage` trả về đúng ba khoá `prompt_tokens` / `completion_tokens` /
      `total_tokens`. **Không cần dịch**: hình dạng `usage` của OpenAI trùng đúng ba tên mà
      `_extract_usage` đang sinh ra, nên tầng trên không biết đang dùng backend nào
- [x] 5.5 ĐỌC LẠI + kiểm cấu trúc bằng `ast`: `_generate_gateway` nằm **trong** lớp,
      `_extract_usage` vẫn ở **cấp module**; đủ 12 method; `py_compile` đạt.
      Cũng đã kiểm `./src:/app/src` là bind-mount → sửa xong chỉ cần restart, không build lại
- [x] 5.6 CHẠY LÁT MỎNG (chưa đụng `.env`, gọi thẳng nhánh mới trong container):
      · văn xuôi → `'OK'`, usage `13 + 1 = 14`
      · `json_mode=True` → parse được thành `dict`
- [x] 5.7 **Phép đo 5.6 lúc đầu KHÔNG tách được biến — đã làm lại.** Prompt thử nghiệm có
      chữ "trả về JSON", nên kết quả JSON có thể chỉ là model nghe lời prompt, không chứng
      minh được `response_format` có tác dụng. Đo lại bằng **cùng một prompt không hề nhắc
      JSON** (`"Thu do cua Viet Nam la thanh pho nao"`):
      · `json_mode=False` → `"Thủ đô của Việt Nam là **thành phố Hà Nội**."` (văn xuôi)
      · `json_mode=True`  → `{"thu_do": "Hà Nội"}` (JSON hợp lệ)
      → **`drop_params: true` KHÔNG nuốt `response_format`.** Lo ngại ở quyết định ② là
      chính đáng nhưng đã được giải toả bằng phép đo, không phải bằng suy luận.
      **Việc này làm luôn phần cốt lõi của mục 7**
- [x] 5.8 ĐO sổ sau lát mỏng: tổng dòng đi 22 →23 (3.9) →24 (4.2) →26 (lát mỏng)
      →28 (đo tách biến). **Khớp từng lượt, không dòng nào thừa hay thiếu.**
      Cả 5 dòng mới nhất: `key_alias dms-feedback-tagged`, `attempted_retries 0`
## 6. Đổi `.env` của DMS và chạy lát mỏng

- [x] 6.0 **Đã tạo nhánh `Tuan-develop` trong bản clone DMS trước khi đi tiếp.** Trước đó
      working tree nằm trên `main` — nhưng **chưa commit gì**, commit mới nhất `f875b24`
      là của nhóm DMS. `git checkout -b` mang nguyên ba thay đổi chưa commit sang, không
      mất gì và không có nhánh lạ nào phải xoá. `main` vẫn đứng nguyên ở `f875b24`
- [x] 6.1 `.env` DMS: `GEMINI_BACKEND=gateway` · `GEMINI_API_KEY` → Virtual Key `sk-…` ·
      `GEMINI_MODEL` → bí danh `gemini-flash-lite` · thêm `GEMINI_GATEWAY_BASE_URL` và
      `GEMINI_GATEWAY_USER=svc.dms-feedback`. Đã sao lưu `.env` cũ trước khi ghi đè
- [x] 6.2 `MAX_RETRY=1`. `max_retry` **không có alias** trong `settings.py:61`, nên pydantic
      dùng chính tên trường. Đã ĐO lại thay vì tin suông: `s.max_retry = 1`
- [x] 6.3 ĐO: `.env` của DMS còn **0** chuỗi bắt đầu `AQ.`. Agent không còn đường đi vòng
- [x] 6.3b **PHÁT HIỆN THẬT — quyết định 5.1c KHÔNG đạt được, phải sửa file thứ hai.**
      `settings.py:130` có danh sách trắng **vô điều kiện** `{"vertex", "apikey"}`. Nhánh
      thứ ba không thể tồn tại nếu không nới nó. Đã sửa 2 chỗ, **đều là nới rộng**, không
      đổi hành vi hai nhánh cũ:
      · `{"vertex", "apikey", "gateway"}` + sửa câu thông báo lỗi cho khớp
      · thêm chốt `if backend == "gateway" and not self.gemini_api_key: raise` — giữ đúng
        khuôn hai nhánh cũ, chặn trường hợp bật `gateway` mà quên khoá.
      → Số file của nhóm DMS bị sửa: **2**, không phải 1. Task 5.1c đã ghi sai, sửa ở đây
- [x] 6.3c **PHÁT HIỆN THẬT thứ hai, không nằm trong kế hoạch nào — DMS nuốt lỗi cấu hình.**
      Khi `GEMINI_BACKEND=gateway` còn bị từ chối, log ghi `Khong the tai cau hinh day du`
      **ba lần**, rồi vẫn `Application startup complete` và phục vụ `GET / 200`. Container
      báo `healthy` sau 10 giây. Nếu không đọc log thì tưởng mọi thứ ổn.
      Đây là **ngược hẳn** kỷ luật của chính dự án Gateway (`entrypoint.sh`, `DASHBOARD_KEY`):
      *chế độ hỏng phải là "không chạy", tuyệt đối không phải "chạy khuyết"*.
      → **Việc thứ tư đáng báo lại nhóm DMS**
- [x] 6.3d **Bẫy vận hành:** `GEMINI_GATEWAY_*` đọc qua `os.environ`, mà `env_file` chỉ nạp
      **lúc tạo container**. `docker compose restart` KHÔNG đọc lại — phải
      `up -d --force-recreate`. Quên bước này thì `GEMINI_GATEWAY_USER` rỗng và header
      `X-User` biến mất **im lặng**, cột `end_user` trống mà không có lỗi nào
- [x] 6.4 Đăng nhập `POST /api/auth/login` (`admin`), rồi `POST /api/classify/text` với
      **đúng câu 29/08**
- [x] 6.5 ĐO kết quả — **khớp đúng lượt 29/08**: `Báo lỗi = true` · `Bảo hành = true` ·
      `sentiment = "Tiêu cực"` · `decision_log` **2 mục**, lý do tiếng Việt do LLM sinh.
      Chuyển sang Gateway **không làm đổi kết quả agent trả về**
- [x] 6.6 ĐO sổ: `model gemini/gemini-3.5-flash-lite` · `5.643 + 401 = 6.044 token` ·
      `spend 0,0026954` · **`end_user = svc.dms-feedback`** (header `X-User` đi xuyên từ
      nhánh mới) · `key_alias dms-feedback-tagged` · `attempted_retries 0` ·
      `messages {}` (prompt đã xoá)
- [x] 6.6b **Sổ ra +2 dòng, không phải +1 — đã truy ra nguyên nhân, không bỏ qua.**
      Một lượt phân loại = **hai** lượt gọi LLM, cách nhau ~1 giây:
      · `rag_product.py:190` `generate()` → 233 + 3 = **236 token**
      · `issue_classifier.py:424` `generate_json()` → 5.643 + 401 = **6.044 token**
      Cả hai đều `end_user svc.dms-feedback`, `retries 0`.
      **Hệ quả cho hạn mức:** `rpm: 60` thực chất chỉ đủ **~30 lượt phân loại/phút**.
      Phải nhớ điều này khi tính công suất và khi đối chiếu số lượt gọi với số bản ghi
## 7. Phép kiểm riêng cho chế độ JSON (quyết định ②)

- [x] 7.1 Đã đo **hai lần độc lập**, một tổng hợp và một trong ứng dụng thật:
      · Phép thử tổng hợp ở 5.7 — gọi thẳng `_generate_gateway(json_mode=True)`
      · Ứng dụng thật ở 6.4 — `issue_classifier.py:424` `generate_json()` chạy qua Gateway
- [x] 7.2 ĐO **có tách biến** (bản đầu không tách được, xem 5.7): cùng một prompt **không hề
      nhắc JSON** (`"Thu do cua Viet Nam la thanh pho nao"`):
      · `json_mode=False` → `"Thủ đô của Việt Nam là **thành phố Hà Nội**."` — văn xuôi
      · `json_mode=True`  → `{"thu_do": "Hà Nội"}` — JSON hợp lệ
      Và trong ứng dụng thật, `generate_json` trả về đủ `labels` (21 nhãn), `sentiment`,
      `decision_log` — tức chuỗi trả về parse được thành `dict` thật.
      → **`drop_params: true` KHÔNG nuốt `response_format`.** Kết luận bằng phép đo, không
      phải bằng "không thấy lỗi"
- [x] 7.3 Không phải làm gì. `drop_params` giữ nguyên `true`, không đụng tới
## 8. Phép kiểm số lượt gọi (quyết định ③)

- [x] 8.1 Ép hỏng bằng cách tạm đổi `api_key` của tuyến `gemini-flash-lite` thành chuỗi sai
      (đã sao lưu config trước, khôi phục ngay sau khi đo). Gọi 1 request qua `/api/classify/text`
- [x] 8.2 ĐO — **`MAX_RETRY=1` có tác dụng thật**: log DMS ghi
      `GeminiClient generate_json error (1/1)` — **một** lượt thử, không phải ba.
      Không xảy ra phép nhân 3×3 = 9. Quyết định ③ đã kiểm
- [x] 8.2b ĐO chuỗi sự kiện thật, khác với dự đoán trong design:
      khoá sai → Google trả `400` → LiteLLM đếm đủ `allowed_fails: 3` → **đưa deployment vào
      cooldown 30s** → mọi lượt sau nhận **`429 Too Many Requests` ngay lập tức**,
      `attempted_retries = 0`. Tức cơ chế cooldown tự nó đã chặn phép nhân, trước cả khi
      `num_retries` kịp chạy
- [x] 8.3 **PHÁT HIỆN THẬT nghiêm trọng — DMS trả HTTP 200 khi LLM hỏng.**
      ```
      GeminiClient generate_json error (1/1): 429 Too Many Requests
      Pure-LLM issue classifier fail: 429 Too Many Requests
      classify_batch: unusable LLM JSON response; using safe fallback.
      ```
      Endpoint vẫn trả **200**. Người gọi **không có cách nào biết** rằng lượt phân loại đó
      chưa hề được LLM xử lý. Đây là kiểu hỏng nguy hiểm nhất với một dự án đếm token: công
      việc không xảy ra nhưng trông y hệt đã xảy ra.
      → **Việc thứ năm đáng báo lại nhóm DMS.** Cùng họ với 6.3c (nuốt lỗi cấu hình)
- [x] 8.4 **PHÁT HIỆN THẬT cho change kế tiếp (`db/load_gateway.py`)** — lượt gọi HỎNG
      **vẫn sinh dòng** trong `LiteLLM_SpendLogs`:
      · dòng hỏng: `status = failure`, `spend = 0`, `total_tokens = 0` (một dòng ghi 14),
        có `error_information` kèm traceback
      · dòng thành công: `status` = **NULL**
      → Loader tương lai **PHẢI lọc theo `status`**, nếu không sẽ đếm cả lượt hỏng thành
      lưu lượng thật (với 0 token), và số lượt gọi sẽ cao hơn số việc thật sự làm được
- [x] 8.5 Khôi phục config, triển khai lại, ĐO: 3 tuyến đều dùng `os.environ/KEY_GOOGLE_AI_STU`;
      một lượt `/api/classify/text` mới → `Báo lỗi = true`, `Bảo hành = true`,
      `sentiment = "Tiêu cực"`, `decision_log` 2 mục. Hệ thống về đúng trạng thái tốt

## 9. Kiểm tra lùi lại được

- [x] 9.1 Khôi phục `.env` của DMS từ bản sao lưu 31/08 (về `GEMINI_BACKEND=apikey`,
      `GEMINI_MODEL=gemini-3.5-flash-lite`, khoá Google `AQ.…`), `up -d --force-recreate web`
- [x] 9.2 ĐO: `Báo lỗi = true` · `Bảo hành = true` · `sentiment = "Tiêu cực"` · 2 mục —
      **giống hệt trước change**. Nhánh `apikey` không bị nhánh mới đụng tới
- [x] 9.2b ĐO cứng hơn: `LiteLLM_SpendLogs` **đứng yên ở 35 dòng** trong suốt lượt đó.
      Tức DMS đã đi **thẳng** tới Google, Gateway không hề biết.
      Đây vừa là bằng chứng lùi-lại-được, vừa là **minh hoạ sống** của chính vấn đề khiến
      ta chọn Virtual Key: agent nào còn cầm khoá nhà cung cấp thì còn đi vòng được, và sổ
      trở thành **sổ tự nguyện**
- [x] 9.3 Trả `.env` về chế độ gateway, `--force-recreate`, ĐO: `GEMINI_BACKEND=gateway`,
      `GEMINI_MODEL=gemini-flash-lite`, **0** chuỗi `AQ.` trong `.env`
## 10. Ghi lại

- [x] 10.1 Đã viết `docs/reference/dua-dms-qua-gateway-31-08.md` theo khuôn
      `thay-doi-ban-clone-dms-29-08.md`: chọn đường và vì sao, những gì chứng minh được,
      **năm cái bẫy đo đạc**, bốn chỗ kế hoạch sai, đã đụng vào gì, và mục riêng
      "còn chưa chắc — đừng đọc thành đã biết"
- [x] 10.2 Danh sách báo lại nhóm DMS nay có **năm** việc, không phải ba. Hai việc mới phát
      hiện hôm nay (④ nuốt lỗi cấu hình vẫn khởi động, ⑤ trả HTTP 200 khi LLM hỏng) cùng một
      họ và ngược hẳn kỷ luật "hỏng thì không chạy" của dự án Gateway.
      Việc ③ (`GEMINI_MODEL_PRICING` thiếu `gemini-3.5-flash-lite`) đã tự kiểm chứng lại
      thay vì chép từ nhật ký 29/08: bảng giá có đúng 5 model, không có model đang dùng
- [x] 10.3 Đã ghi rõ trong nhật ký, mục 9: **chưa có `db/load_gateway.py`**, dashboard vẫn
      chưa hiển thị được token của DMS; mới chứng minh trên **một** agent; và mọi thay đổi
      còn nằm trên nhánh `Tuan-develop`, **chưa commit**
- [x] 10.4 Thêm mục 8 của nhật ký — **hai điều phải biết trước khi viết `db/load_gateway.py`**:
      lượt gọi hỏng vẫn sinh dòng (`status = 'failure'`, phải lọc), và một lượt phân loại
      bằng **hai** lượt gọi LLM (`rpm: 60` chỉ đủ ~30 lượt phân loại/phút)
      hiển thị được token của DMS. Đừng để ai đọc nhầm change này là "đã xong đường ống"
