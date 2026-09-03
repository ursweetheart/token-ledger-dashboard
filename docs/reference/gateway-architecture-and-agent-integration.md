# API Gateway — cách hoạt động và cách nối một agent vào

Tài liệu này mô tả **hệ thống đang chạy thật ngày 31/08/2026**, không phải thiết kế dự kiến.
Mọi con số đều đo được; chỗ nào chưa chứng minh thì ghi rõ là chưa.

Nhật ký quá trình: `dua-dms-qua-gateway-31-08.md` (nối agent) và
`nap-so-gateway-vao-database-31-08.md` (đưa vào dashboard).

---

## 1. Toàn cảnh

```
   ┌─ mang cua agent ─────────┐   ┌─ mang cua gateway ──────────────────────┐
   │                          │   │                                          │
   │  DMS Feedback            │   │   gateway-lb :4000  (nginx)              │
   │  (FastAPI)               │   │        │                                 │
   │    │ Bearer sk-…         │   │        ├──▶ litellm-1 ─┐                 │
   │    │ X-User: svc.dms-…   │───┼───▶    └──▶ litellm-2 ─┤                 │
   │    │ model: alias        │   │                        │                 │
   │    ▼                     │   │            redis  ◀────┘ han muc dung chung│
   │  POST /v1/chat/          │   │            redis-replica                 │
   │       completions        │   │                        │                 │
   └──────────────────────────┘   │                        ▼                 │
                                  │              Google AI Studio            │
                                  │                        │                 │
                                  │                        ▼                 │
                                  │              LiteLLM_SpendLogs           │
                                  └──────────────────────────────────────────┘
```

Ba điều làm nên kiến trúc này:

**① Agent không giữ khoá của nhà cung cấp.** Nó cầm một *Virtual Key* dạng `sk-…` chỉ dùng
được với Gateway. Khoá thật của Google chỉ nằm trong cấu hình Gateway. Ai lấy được `sk-…` cũng
không gọi thẳng Google được — đi qua Gateway trở thành **bắt buộc về mặt kỹ thuật**, không
phải một thoả thuận.

**② Agent gọi bằng bí danh, không gọi bằng tên model thật.** Agent xin `gemini-flash-lite`;
Gateway mới dịch sang `gemini/gemini-3.5-flash-lite`. Đổi model upstream không phải sửa agent.

**③ Tag của khoá quyết định hoá đơn rơi vào project nào.** Virtual key mang
`metadata.tags = ["dms-feedback"]`; Gateway chỉ chọn tuyến mang đúng tag đó.

> **BẪY CHẾT NGƯỜI:** `enable_tag_filtering` mặc định là **False** (`litellm/router.py:430`).
> Thiếu dòng đó trong `router_settings` thì `tags` bị **bỏ qua hoàn toàn và im lặng** — mọi
> phép kiểm vẫn đạt, câu trả lời vẫn đúng, chỉ có tiền là rơi sai project. Đã đo bằng phép
> kiểm mồi: có tag filtering thì 10/10 đúng tuyến; không có tag thì **12,5% rơi nhầm tuyến**.

---

## 2. Đã sửa gì trong agent DMS

Tổng cộng **2 file sửa (+108 dòng), 1 file thêm mới**. Không đụng vào logic nghiệp vụ, không
đụng vào `requirements.txt`, không phải dựng lại image.

### 2.1 `service/src/dms/gemini_client.py` — +100 dòng

Thêm một **backend thứ ba** bên cạnh `vertex` và `apikey` đã có. Ba phần:

| Thêm gì | Việc |
|---|---|
| `self._gateway_client` trong `__init__` | ô chứa client, khởi tạo lười |
| `_init_gateway()` | dựng `httpx.Client` với `base_url`, `Authorization: Bearer sk-…`, và `X-User` nếu có |
| `_generate_gateway()` | gọi `POST /v1/chat/completions`, bóc `choices[0].message.content` và `usage` |

Cộng **2 dòng rẽ nhánh** trong `generate()` và `generate_json()`:

```python
    if self.settings.gemini_backend == "gateway":
        return self._generate_gateway(prompt, temperature=temperature)
```

Dùng `httpx` chứ không dùng `openai`: `httpx` **đã là phụ thuộc sẵn có** của tầng web, còn
`openai` thì không — chọn `openai` là phải sửa `requirements.txt` và dựng lại image.

**Cố ý KHÔNG có đường lui im lặng khi `json_mode`.** Gateway chạy với `drop_params: true`, tức
là nó **bỏ tham số lạ mà không báo lỗi**. Một `try/except` ở đây sẽ giấu đúng thứ đáng bắt: yêu
cầu JSON bị trả lời bằng văn xuôi. Đã đo bằng prompt trung tính: `json_mode=False` → văn xuôi,
`json_mode=True` → `{"thu_do": "Hà Nội"}`. Vậy `response_format` **không** bị nuốt.

### 2.2 `service/src/dms/settings.py` — +10 / −2 dòng

Danh sách trắng backend là **vô điều kiện**, nên không thêm `"gateway"` vào đó thì app không
khởi động được:

```python
-  if backend not in {"vertex", "apikey"}:
+  if backend not in {"vertex", "apikey", "gateway"}:
```

Cộng một phép kiểm bắt buộc phải có Virtual Key khi ở chế độ gateway.

### 2.3 `service/docker-compose.override.yml` — file mới

Compose tự nạp file `override`, nên **không phải sửa file gốc của nhóm DMS**. Hai việc: mở cổng
`127.0.0.1:8502` để đo, và nối `web` vào mạng của Gateway.

> **BẪY:** phải liệt kê **cả `default`**. Compose gốc của DMS không khai `networks:` nên mọi
> service dùng mạng ngầm định; chỉ cần viết `networks: [gateway]` là compose bỏ mạng ngầm định
> đi, và `web` **rơi khỏi mạng của chính DMS** — `nginx` sẽ không gọi được `web` nữa.

Không dùng `host.docker.internal`: Gateway cố ý chỉ bind `127.0.0.1`, và việc container xuyên
được vào một cổng chỉ-loopback thì **chưa chứng minh được**. Cách chắc ăn là cho `web` vào
thẳng mạng của Gateway rồi gọi bằng tên service `http://gateway-lb:4000`.

### 2.4 `.env` (không theo git)

```
   GEMINI_BACKEND=gateway
   GEMINI_MODEL=gemini-flash-lite          <- BI DANH, khong phai ten upstream
   GEMINI_API_KEY=sk-…                     <- Virtual Key, khong phai khoa Google
   GEMINI_GATEWAY_BASE_URL=http://gateway-lb:4000
   GEMINI_GATEWAY_USER=svc.dms-feedback
```

> **BẪY:** `env_file` chỉ được nạp lúc **tạo** container. Sửa `.env` rồi `restart` là không ăn
> — phải `up -d --force-recreate`.

---

## 3. Quy tắc chung để nối agent tiếp theo

Suy từ những gì đã làm với DMS. Sáu bước, theo thứ tự.

### Bước 1 — Tìm chỗ agent gọi nhà cung cấp

Tìm **một** hàm duy nhất mà mọi lượt gọi LLM đều đi qua. Ở DMS đó là `GeminiClient`. Agent nào
gọi rải rác nhiều chỗ thì phải gom lại trước — nếu không sẽ có đường đi vòng qua Gateway mà
không ai biết.

### Bước 2 — Thêm backend, KHÔNG sửa backend cũ

Thêm một nhánh mới bên cạnh các nhánh sẵn có. Giữ nguyên đường cũ nguyên vẹn để **lùi lại
được**: đổi một biến môi trường là quay về trạng thái trước.

### Bước 3 — Soát danh sách trắng cấu hình

Hầu hết app đều có một chỗ liệt kê các giá trị hợp lệ của biến cấu hình. Ở DMS là
`settings.py`. **Bỏ sót chỗ này thì app không khởi động** — và ở DMS nó còn tệ hơn: app nuốt
lỗi cấu hình rồi vẫn báo `Application startup complete`, container vẫn `healthy`.

### Bước 4 — Gọi bằng hình dạng OpenAI

```
   POST {base_url}/v1/chat/completions
   Authorization: Bearer sk-…
   X-User: <dinh danh>            (tuy chon)
   {"model": "<bi danh>", "messages": [{"role":"user","content":"…"}]}
```

Dùng thư viện HTTP **đã có sẵn** trong agent. Không thêm phụ thuộc mới nếu tránh được.

### Bước 5 — Nối mạng

Agent và Gateway thường ở hai compose project khác nhau. Cho container của agent vào mạng của
Gateway bằng `networks.external`, và **luôn liệt kê cả mạng mặc định của chính nó**.

### Bước 5b — Chọn ĐÚNG loại định danh cho `X-User`

Quy ước chốt **20/08/2026**: trong 8 agent, **6 agent được coi là chỉ có một người dùng**
(tất cả trừ Trợ Lý Ảo Hợp Đồng và Trợ lý ảo Ralli). Chúng **biết được người dùng** — thứ
duy nhất từng thiếu là một cái tên hợp lý cho "người dùng đặc biệt" đó.

Nên `X-User` gửi gì là tuỳ **loại agent**, không phải tuỳ khẩu vị:

| Loại agent | `X-User` gửi | Bên dashboard |
|---|---|---|
| **Một-người-dùng** (6 agent, có DMS) | `svc.<code>` — một chuỗi cố định | `account.kind = 'service_account'` |
| **Nhiều người dùng** (TLA HĐ, Ralli) | tên người đăng nhập | `account.kind = 'real'` |

Đo 31/08: `kind` đã tách đúng — 6 dòng `service_account` cho agent 1,2,3,4,6,7 và 2 dòng
`whole_agent` cho agent 5,8. `backend/store.py:479` phụ thuộc trực tiếp vào việc tách này.

> **ĐỪNG gửi tên nhân viên cho một agent một-người-dùng.** Nó không làm dữ liệu chi tiết hơn
> mà làm hỏng quy ước: `usage_by_account` lọc `kind='real'`, nên tên lạ sẽ rơi ra ngoài chiều
> người dùng thay vì gộp vào tài khoản dịch vụ của agent. Với DMS, `svc.dms-feedback` khớp
> thẳng `account_id 949` — đó là kết quả ĐÚNG, không phải giải pháp tạm.

### Bước 6 — Khai tuyến ở Gateway và ở dashboard

Ba chỗ, thiếu chỗ nào cũng hỏng im lặng:

| Chỗ | Khai gì | Thiếu thì |
|---|---|---|
| `docker/gateway/config.gateway.yaml` | tuyến + `tags: ["<code-agent>"]` | request không có tuyến để đi |
| Virtual key | `metadata.tags` khớp `dim_agent.code` | bộ nạp bỏ dòng, đếm vào "không có tag định danh" |
| `db/rules.py: GATEWAY_MODELS` | tên upstream của model | dòng vào database với `model_id` NULL |

> **BẪY đã sập một lần:** `db/rules.py:MODEL_PATTERNS` xếp theo thứ tự, **mẫu dài phải đứng
> trước**. Thiếu `"3.5 flash lite"` thì `guess_model("gemini/gemini-3.5-flash-lite")` trả về
> `gemini-3.5-flash` — model khác, đơn giá khác, và **vẫn báo là tìm thấy**.

---

## 4. Một request đi qua những bước nào

```
   ① Agent goi                POST /v1/chat/completions
                              Bearer sk-… · X-User · model = bi danh

   ② gateway-lb              can bang tai sang litellm-1 hoac litellm-2

   ③ Xac thuc khoa           sha256(sk-…) tra LiteLLM_VerificationToken
                             lay ra key_alias + metadata.tags

   ④ Gan tag vao request     key_metadata -> request metadata

   ⑤ Router chon tuyen       loc deployment theo tag
                             (chi chay khi enable_tag_filtering: true)

   ⑥ Dich ten + thay khoa    gemini-flash-lite -> gemini/gemini-3.5-flash-lite
                             api_key <- os.environ/KEY_GOOGLE_AI_STU

   ⑦ Goi Google              kem han muc rpm/tpm dung chung qua Redis

   ⑧ Nhan ket qua            tinh tien tu bang gia noi bo cua LiteLLM

   ⑨ RE HAI NHANH
        │
        ├─▶ tra ve agent   NGAY, noi dung NGUYEN VEN
        │
        └─▶ ghi so         BAT DONG BO ~4 giay, noi dung DA CHE
```

**Bước ⑨ là chỗ hay bị hiểu nhầm nhất.** Hai nhánh mang **nội dung khác nhau**: agent nhận
câu trả lời đầy đủ, còn sổ chỉ lưu `"redacted-by-litellm"`. Đó là do
`turn_off_message_logging` — cố ý, để nội dung phản hồi của khách hàng không nằm trong sổ kế
toán.

---

## 5. Gateway lấy dữ liệu gì

Bảng `LiteLLM_SpendLogs` có **34 cột**. Những cột thực sự dùng được:

### Lấy từ request

| Cột | Nội dung | Ghi chú |
|---|---|---|
| `request_id` | khoá tự nhiên, duy nhất | đo **45/45** phân biệt — dùng làm khoá idempotent |
| `startTime` / `endTime` | thời điểm | `timestamp` **không có múi giờ**, giá trị là **UTC** |
| `end_user` | header `X-User` chép nguyên | **chuỗi rỗng** khi thiếu, không phải NULL |
| `request_tags` | tag của khoá **+ tag User-Agent tự thêm** | xem bẫy bên dưới |
| `metadata.user_api_key_alias` | tên khoá đã gọi | |
| `api_key` | **băm** của virtual key | không khôi phục được bản gốc |

> **BẪY:** `request_tags` bị trộn:
> `["dms-feedback", "User-Agent: python-httpx", "User-Agent: python-httpx/0.28.1"]`.
> Coi cả mảng là danh sách agent thì **một** request thành **ba** agent. Quy tắc: chỉ tag khớp
> một dòng `dim_agent.code` mới là tag định danh — **không** lọc bằng cách bỏ tiền tố
> `User-Agent:`, cách đó vá triệu chứng và sẽ hỏng khi LiteLLM thêm loại tag khác.

### Lấy từ response

| Cột | Nội dung |
|---|---|
| `model` | tên upstream **có tiền tố**: `gemini/gemini-3.5-flash-lite` |
| `model_group` | bí danh agent đã xin: `gemini-flash-lite` |
| `prompt_tokens` / `completion_tokens` / `total_tokens` | số token |
| `spend` | tiền, LiteLLM **tự nhân từ bảng giá của nó** |
| `status` | `success` hoặc `failure` |
| `metadata.cost_breakdown` | tách `input_cost` / `output_cost` / `total_cost` |
| `metadata.usage_object` | usage chi tiết, có `cached_tokens` |
| `metadata.attempted_retries` | số lần thử lại |
| `request_duration_ms` | **độ trễ**. Xem bẫy bên dưới |
| `metadata.error_information.error_code` | **mã lỗi** khi hỏng |
| `api_key` | **khoá đã gọi**. Xem bẫy bên dưới |
| `cache_hit` | **trả từ bộ nhớ đệm hay không**. Xem bẫy bên dưới |
| `response` | response đầy đủ, **nội dung đã che** |

> **BẪY:** `request_duration_ms` bằng **0 trên MỌI lượt hỏng**, kể cả lượt **đã gọi tới nhà
> cung cấp** và bị từ chối. Nên 0 ở đây không phải một phép đo mà là **sự vắng mặt** của phép
> đo — bộ nạp quy nó về NULL. Nạp 0 vào là kéo tụt mọi phân vị.
>
> Và `error_code` mang **chuỗi rỗng** ở 3/5 dòng hỏng, không phải NULL.

> **BẪY `api_key`:** cột này **trộn hai loại giá trị**. Khoá ảo ghi thành băm SHA-256 64 ký
> tự, nhưng khoá quản trị chung ghi thẳng chuỗi `litellm_proxy_master_key`. Bộ nạp giữ
> **nguyên văn**, không chuẩn hoá — ép về một dạng là mất đúng cái phân biệt đang cần. Đo
> 01/09: **7/41 dòng nạp được (17,1%) đi bằng khoá tổng**, và chúng nằm lẫn trong lưu lượng
> của agent vì vẫn quy được về agent nhờ tag.

> **BẪY `cache_hit` — hai bẫy NGƯỢC NHAU ở hai đầu.** Ở **vế nguồn** cột này là `text` và ghi
> **chuỗi `'None'`** cho trường hợp không có thông tin, không phải SQL NULL (đo 01/09: `'None'`
> 41 · `'False'` 5 · `'True'` 1, **không một dòng NULL nào**). Nên `WHERE cache_hit IS NULL`
> trả về **0 dòng**, còn `IS NOT TRUE` thì **lỗi kiểu**. Bộ nạp phải dịch bằng `CASE` tường
> minh, **không** dùng `::boolean` — gặp giá trị thứ tư là ném lỗi giữa chừng.
>
> Ở **vế đích** `fact_call.cache_hit` là `BOOLEAN` thật với NULL thật, nên `NOT cache_hit`
> biến NULL thành UNKNOWN và **vứt sạch 38/41 dòng**. Ở đó `IS NOT TRUE` mới là cách đúng.
>
> Vì sao phải lọc: lượt trúng đệm **không tới nhà cung cấp** nên không bị tính tiền, nhưng
> Gateway **vẫn ghi đủ token** (đo được một lượt ghi `spend = 0` mà `total_tokens = 352`).

### Hai cột trông có ích nhưng KHÔNG dùng được

```
   agent_id      NULL 45/45       cot san cua LiteLLM, khong duoc dien
   session_id    45/45 khac nhau  khong gom duoc 2 luot goi cua 1 lan phan loai
```

*(01/09: `cache_hit` đã ra khỏi danh sách này — nó dùng được, và bỏ qua nó thì token phồng.)*

### `completion_tokens_details` — khối CHIỀU RA, đọc 03/09/2026

Khối này nằm trong `metadata.usage_object`. **Đọc nhầm sang `prompt_tokens_details` vẫn ra số**
— cả hai khối đều có `text_tokens` đầy đủ 42/42 — chỉ là số của **chiều ngược lại**. Không
crash, không ai thấy. Bản đầu của đề xuất đã trỏ nhầm khối, đo lại mới ra.

Đếm trên 42 lượt thành công:

```
   text_tokens                 42/42  deu > 0
   reasoning_tokens             2/42  = 342, ca hai la gemini-3.6-flash
   audio_tokens                 0/42
   image_tokens                 0/42
   video_tokens                 0/42
   accepted_prediction_tokens   0/42
   rejected_prediction_tokens   0/42
```

| Suy ra cột nào | Quy tắc | Đo được |
|---|---|---|
| `fact_call.output_modality` | `'text'` khi `text_tokens > 0` và không modality nào khác > 0. Gặp modality lạ thì **NULL và ĐẾM**, không dán nhãn `'text'` cho một phản hồi không phải văn bản | **38/41** — 3 dòng rỗng là 3 lượt hỏng, và lượt hỏng không có phản hồi để dán nhãn |
| `fact_call.thinking_enabled` | `reasoning_tokens > 0`. Khoá **vắng mặt → NULL**, KHÔNG phải `false` | **0/41** — xem bẫy dưới |

> **BẪY — `thinking_enabled` nạp ra 0/41, và đó là ĐÚNG.**
> Hai dòng duy nhất có `reasoning_tokens` mang `request_tags` chỉ gồm
> `["User-Agent: Python-urllib", "User-Agent: Python-urllib/3.13"]` — **không tag định danh
> agent nào**. `resolve_agent()` trả `None`, mà `fact_call.agent_id` là `NOT NULL`, nên cả hai
> bị loại ngay ở khâu nạp. Một trong hai còn là lượt trúng cache (`request_id` hậu tố
> `_cache_hit…`).
> Cột **đọc đúng**, nhưng **chưa có dữ liệu** — và sẽ chưa có cho tới khi một agent CÓ TAG sinh
> token suy luận.

> **VÌ SAO NULL CHỨ KHÔNG PHẢI `false`.** Gemini **không gửi** khoá `reasoning_tokens` cho model
> không suy luận. "Vắng mặt" nghĩa là *nhà cung cấp không nói gì* — khác hẳn *đã đo và bằng
> không*. Ghi `false` cho 40/42 dòng là khẳng định một phép đo chưa ai thực hiện. Cùng kỷ luật
> đã áp cho `duration_ms` (migration 006) và `cached_tokens`.

> **KIỂU KHÁC `fact_monitoring`.** Ở bảng đó cột cùng tên là **TEXT** mang chuỗi `'true'` /
> `'false'` (11.440 / 3.589, NULL 636.624) — vì nó là bảng hạ cánh của nhãn Google gửi sang.
> `fact_call` là bảng của ta nên dùng **BOOLEAN** thật. Mọi phép so hai bảng **phải dịch kiểu
> tường minh**.

---

## 6. Cấu trúc response trả về agent

Hình dạng OpenAI chat-completions. Đây là trường thật, lấy từ sổ:

```json
{
  "id": "MfKUas30GNK_vr0P-sW9kQ8",
  "object": "chat.completion",
  "model": "gemini-3.5-flash-lite",
  "created": 1788146222,
  "service_tier": "default",
  "choices": [{
    "index": 0,
    "finish_reason": "stop",
    "message": { "role": "assistant", "content": "…" }
  }],
  "usage": {
    "prompt_tokens": 5630,
    "completion_tokens": 329,
    "total_tokens": 5959,
    "prompt_tokens_details": {
      "text_tokens": 5630, "audio_tokens": null,
      "image_tokens": null, "video_tokens": null, "cached_tokens": null
    },
    "completion_tokens_details": { "text_tokens": 329 },
    "cache_read_input_tokens": null
  }
}
```

| Trường | Nghĩa |
|---|---|
| `id` | định danh lượt gọi phía nhà cung cấp |
| `object` | luôn là `chat.completion` |
| `model` | model **thực sự** trả lời — **không có tiền tố** ở đây, khác cột `model` trong sổ |
| `created` | dấu thời gian Unix |
| `service_tier` | bậc dịch vụ: `default` / `flex` / `priority` / `batch`. **Quyết định đơn giá** |
| `finish_reason` | `stop` = trả lời xong. `length` = **bị cắt vì chạm giới hạn** |
| `message.content` | câu trả lời. Agent chỉ cần trường này |
| `usage.*_tokens` | số token — dùng `total_tokens`, **không tự cộng** hai số kia |
| `prompt_tokens_details` | tách theo kiểu dữ liệu; `cached_tokens` là phần đọc từ bộ nhớ đệm |

Còn 4 trường `vertex_ai_*` (citation, grounding, safety, url_context) — luôn có mặt, hiện luôn
rỗng vì đi qua AI Studio chứ không qua Vertex.

**`finish_reason` đáng chú ý:** `"length"` nghĩa là câu trả lời **bị cắt giữa chừng**. Agent
không kiểm trường này sẽ nhận một JSON vỡ mà tưởng là lỗi phân tích cú pháp. Hiện DMS **chưa
kiểm** — xem mục 9.

---

## 7. Dữ liệu vào database và lên dashboard thế nào

```
   LiteLLM_SpendLogs  (database `litellm`, vai gateway_readonly chi-doc 1 bang)
        │
        │  db/load_gateway.py
        │    loc status='success'          (KHONG phai IS NULL)
        │    ts_local = ts_raw + 7h        (so goc giu nguyen)
        │    agent tu tag khop dim_agent.code
        │    model tu dim_model_alias source='gateway'
        │    ON CONFLICT (call_id) DO NOTHING
        ▼
   fact_call  source='gateway'   ← tung luot goi, CO tien tung luot
        │
        │  db/build_usage_daily.py
        ▼
   fact_usage_daily  source='gateway'   ← gop theo (ngay, agent, model, tai khoan)
        │
        │  view usage_resolved
        ▼
   Dashboard
```

### Hai database, hai kết nối

Sổ Gateway nằm ở database **riêng** (`litellm`), cùng một instance PostgreSQL. Giữ tách vì
**LiteLLM tự chạy migration bằng Prisma** — gộp nghĩa là mỗi lần nâng phiên bản nó có quyền
`ALTER` trong database chứa dữ liệu dashboard.

Cái giá: PostgreSQL không cho JOIN xuyên database (`postgres_fdw` và `dblink` đều chưa cài),
nên bộ nạp mở **hai kết nối** và ánh xạ ở tầng Python.

### Thứ tự ưu tiên trong `usage_resolved`

```
   TOKEN   gateway > billing > monitoring > app
           Gateway thang vi no dem TUNG luot goi mot

   TIEN    hoa don > gateway
           hoa don la so Google THUC SU tru tien
```

Hai cột ưu tiên **ngược nhau**, và đó là cố ý. Ngày hoá đơn về, nó thay thế số ước tính của
Gateway.

### Năm quy tắc bộ nạp phải giữ

```
   Truong thieu -> NULL, KHONG phai 0      (cached_tokens vang 45/45; duration 0 -> NULL)
   Dung total_tokens cua so                 (khong tu cong prompt + completion)
   Luot HONG CO nap, kem ma loi             (doi 31/08 - xem duoi)
   MOI phep tong hop PHAI loc `outcome`     (thieu la ro token cua luot hong)
   MOI phep tong hop PHAI loc `cache_hit`   (them 01/09 - IS NOT TRUE, KHONG phai NOT)
```

**Đổi 31/08:** bản đầu **không nạp** lượt hỏng. Nay nạp, vì Master Plan đòi *"bản ghi mỗi
request"* — trước đó ta chỉ biết CÓ hỏng mà không biết VÌ SAO, trong khi mã lỗi nằm sẵn trong
sổ. Đổi lại, mọi chỗ tổng hợp **bắt buộc** phải lọc `outcome = 'success'`; đã đo lỗ rò trước
khi vá: thiếu bộ lọc thì token gateway ra **45.201 thay vì 45.187**.

**Đổi 01/09:** nạp thêm `raw_model`, `virtual_key_id`, `cache_hit` — ba cột sổ đã ghi sẵn mà
không dòng mã nào đọc tới. Đo lỗ rò bằng phép thử âm đảo ngược được: đặt `cache_hit=true` lên
một dòng 6.866 token thì bỏ bộ lọc **rò đúng 6.866**, còn viết nhầm `NOT cache_hit` thì
**mất sạch 38.321** token.

**Và:** thêm cột vào bảng đã có dữ liệu thì bộ nạp phải **`ON CONFLICT … DO UPDATE`** cho đúng
các cột mới. `DO NOTHING` bỏ qua hoàn toàn dòng cũ, nên cột mới sẽ rỗng vĩnh viễn — đã suýt
làm token gateway về 0.

### Một lượt phân loại KHÔNG bằng một lượt gọi LLM

Đo được, và tỉ lệ **không cố định**:

```
   duong "Doan van ban"   1 dong phan hoi  ->  2 luot goi LLM
   duong "Mot file"       3 dong phan hoi  ->  2 luot goi LLM
```

Nên cột `calls` trên dashboard là **số lượt gọi LLM**, tuyệt đối không đọc thành khối lượng
công việc.

### Chạy tay sau mỗi lượt đo

Sổ Gateway tự động có dữ liệu; dashboard thì không. Một lệnh:

```bash
   python scripts/refresh_gateway.py        # ~0,9 giay
```

Nó chạy `load_gateway.py` rồi `build_usage_daily.py`, **dừng ngay nếu bước đầu hỏng** — vì
`build_usage_daily` xoá sạch rồi dựng lại, chạy nó trên dữ liệu thiếu sẽ cho ra một dashboard
trông y hệt "chưa có lưu lượng".

`scripts/rebuild_db.py` đã có bước `load_gateway.py` ở vị trí **6/9**. **Bỏ bước đó thì mỗi lần
cập nhật dashboard sẽ xoá sạch dữ liệu Gateway và không nạp lại** — không lỗi nào báo.

### Hai nhánh mới, thêm 03/09/2026 (migration 008)

```
   fact_call  source='gateway'
        │
        ├─ db/build_usage_hourly.py    (buoc 8/9)
        │      date_trunc('hour', ts_local), CUNG bo loc voi bang ngay
        │      tu doi chieu tong gio == tong ngay, DUNG HAN neu lech
        ▼
   fact_usage_hourly  source='gateway'   -> GET /api/usage-hourly
        (KHONG BAO GIO co source='billing' - hoa don chi tinh theo NGAY)

   fact_call  source='gateway'  (duration_ms tho)
        │
        ├─ db/build_performance.py     (buoc 9/9)
        │      percentile_cont doc THANG tu tung gia tri
        │      p95_bucket_from/to = NULL  <- so tho khong co sai so noi suy
        ▼
   fact_latency_daily  source='gateway'   -> GET /api/performance
        (moi nguon MOT dong, KHONG gop trung binh voi monitoring)
```

**`rebuild_db.py` nay là 9 bước, không phải 8.** Bước 8 (`build_usage_hourly`) cũng bị `--rebuild`
xoá sạch như mọi bảng khác — thiếu nó trong `STEPS` thì bảng theo giờ biến mất sau mỗi lần cập
nhật, và không lỗi nào báo: nó chỉ là một bảng rỗng.

**`scripts/refresh_gateway.py` CHƯA gọi hai bước mới.** Nó vẫn chỉ chạy `load_gateway.py` +
`build_usage_daily.py`, nên sau khi refresh thì bảng theo giờ và phân vị Gateway **cũ đi một
nhịp**. Chưa sửa vì nằm ngoài phạm vi change này — ghi lại để không ai tưởng nó đã đủ.

**Và khi thêm cột mới vào `fact_call`, phải chạy `load_gateway.py --full`.** `DO UPDATE` chỉ ghi
đè những dòng bộ nạp **đọc tới**, mà mốc nạp (`watermark`) chỉ lùi 1 giờ. Đo 03/09: chạy trần nạp
được **6/41** dòng, 35 dòng còn lại giữ `NULL`; `--full` mới đủ 41/41.

---

## 8. Trạng thái đo được ngày 31/08/2026

```
   So Gateway          45 luot goi   (38 dung duoc, 5 hong, 2 khong co tag)
   fact_call           38 dong, moi dong CO tien rieng
   fact_usage_daily    1 dong: 2026-08-31 | agent 6 | model 12 | 45.187 token
   usage_resolved      Phan Loai Phan Hoi Tiep Thi | gemini-3.5-flash-lite
                       38 luot | 45.187 token | $0,021305
   audit_db.py         36 phep kiem | 32 dat | 4 luu y | 0 hong
```

Đối chiếu chéo hai bảng giá độc lập, trên lưu lượng thật:

```
   dashboard nhan token x ref_price (bang gia Google)   $0,0213045
   LiteLLM tu tinh bang bang gia rieng                  $0,0213050
   lech                                                -$0,0000005
```

---

## 9. Những gì CHƯA làm được

| Việc | Trạng thái |
|---|---|
| Danh tính từng nhân viên **cho agent nhiều người dùng** | `X-User` bị nướng cứng vào `httpx.Client` lúc khởi tạo, và `GeminiClient` là singleton — nên chưa gửi được định danh theo từng request. **KHÔNG áp dụng cho DMS**: DMS là agent một-người-dùng, `svc.dms-feedback` đã là đáp án đúng. Việc này chỉ cần khi nối TLA Hợp Đồng hoặc Ralli |
| Agent thứ hai | mới chứng minh trên **một** agent; thiết kế "8 khoá / 8 project" chưa được đo |
| `finish_reason == "length"` | DMS **không kiểm** — câu trả lời bị cắt sẽ trông như lỗi phân tích cú pháp |
| Tuyến `gemini-3-flash-preview` | cố ý bỏ khỏi `GATEWAY_MODELS`: đơn giá bản preview chưa ai kiểm |
| Hoá đơn cho `gemini-3.5-flash-lite` | **chưa từng tồn tại** — lưu lượng mới bắt đầu 31/08, Google xuất hoá đơn trễ ~1 ngày |
| Hành vi ở quy mô lớn | mới 45 lượt gọi |
| So sánh độ trễ với monitoring | Gateway `p95 = 1,822 s` (chính xác, 38 giá trị thô) so với monitoring `p95 = 63,6 s` nội suy trong **thùng rộng 33,6 giây**. Chênh 35 lần — **chưa kết luận được** bên nào đúng, vì hai bên đo hai giai đoạn khác nhau |

### Bốn điều đáng báo lại nhóm DMS

1. `classify_batch` trả **HTTP 200 kèm "safe fallback"** khi LLM hỏng — việc không xảy ra mà
   trông y hệt đã xảy ra.
2. App **nuốt lỗi cấu hình** rồi vẫn `Application startup complete`, container vẫn `healthy`.
3. Không kiểm `finish_reason`.
4. `GeminiClient` là singleton và `X-User` nướng cứng vào client — không gửi được danh tính
   theo từng request. Với DMS thì **không sao** (agent một-người-dùng), nhưng cần biết nếu
   nhóm DMS muốn tách theo người.
