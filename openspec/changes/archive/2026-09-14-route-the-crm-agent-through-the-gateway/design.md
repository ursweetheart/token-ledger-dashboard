## Context

CRM là **pipeline chạy theo lịch**, không phải web service như DMS. Đọc code bản clone
`CRM-Classification-Pipeline` ngày 09/09/2026:

```
  SharePoint (CRM_merge.xlsx)
        │  tai ve -- va XOA file cuc bo truoc khi tai
        ▼
  [1] phan loai bang regex                 <- khong goi LLM
        ▼
  [2] o nao regex khong quyet duoc  -> gom batch 25 dong
        ▼
  [3] Gemini: 1 luot goi = 25 dong CRM     <- CHO DUY NHAT change nay sua
        │  ThreadPoolExecutor(3 worker), nhung wait_for_rate_limit() khoa TOAN CUC
        │  va ngu BEN TRONG khoa -> cac luot goi cach nhau MIN_INTERVAL_S + jitter,
        │  bat ke co bao nhieu worker. CRM KHONG BAO GIO ban don.
        ▼
  [4] ghep -> ghi Excel -> UPLOAD SharePoint -> GUI EMAIL
```

Daemon: chạy **ngay khi khởi động**, rồi mỗi ngày **03:30**
(`pipeline.py:916`, `get_seconds_until_next_run(3, 30)`). Khớp đúng phép đo trong sổ: giờ 3
chiếm 1.146 lượt trên 46 ngày.

### Đo được, dùng làm căn cứ cho thiết kế

| Điều | Giá trị | Nguồn |
|---|---|---|
| model | `gemini-2.5-flash`, **duy nhất** | `fact_usage_daily`, agent 7 |
| khối lượng | 1.888 lượt / 22,6M token / $15,20 | sổ, 06/07 → 29/08 |
| một lượt gọi | **25 dòng CRM** — và **luôn** là 25: `.env.example` khuyến nghị `GEMINI_BATCH_SIZE=40` nhưng code là `min(25, …)` nên 40 bị cắt xuống 25 mà không báo | `config.py:32` |
| nhịp tự giới hạn | mặc định code 3,5s+0,5 → **16 rpm**; `.env.example` 7,5s+1,5 → **7,3 rpm** | `src/config.py` |
| SDK | `google-genai` (bản **mới**) | `requirements.txt`, `src/llm.py` |
| backend mặc định | **Vertex** (`USE_VERTEX=True`) + `sa-key.json` | `src/llm.py:15` |
| định danh dịch vụ | `svc.crm-feedback`, account **951**, đã có | bảng `account` |
| chiều người dùng | `usage_by_account` **0 dòng** | sổ |

### Không có trong tay

`.gitignore` loại `.env` và `sa-key.json`, nên bản clone **không có khoá nào**. Kết luận
ngày 08/09 rằng "khoá của CRM nằm sẵn trong `.env`, không phải đi xin" là **sai**, và đã
rút lại.

## Goals / Non-Goals

**Goals**

- Một lượt gọi LLM thật của CRM đi qua Gateway, tới Google, về, và hiện lên dashboard.
- Lượt gọi đó quy được về **đúng agent 7** trong sổ.
- Giữ **đúng model production đang dùng** — không thay thế model.
- Đường lùi là **một biến môi trường**, không phải sửa code.

**Non-Goals**

- Không sửa logic phân loại của CRM. Không đụng SharePoint, email, Excel.
- Không chạy cả pipeline để nghiệm thu — xem Quyết định 4.
- Không đo tải, không thử 429, không chạy batch thật. Đó là change thứ hai.
- Không nhắm chiều **người dùng**. CRM là việc chạy đêm, `X-User` sẽ là định danh **dịch
  vụ**; không có con người nào để quy, và điền bừa một cái tên còn tệ hơn để trống.

## Decisions

### Quyết định 1 — Cửa vào là `/v1/chat/completions`, không phải `/gemini` passthrough

Passthrough hấp dẫn vì gần như không phải sửa code CRM. **Bị loại**, hai lý do độc lập:

1. Tài liệu DMS 31/08 đã loại nó: `passthrough_endpoint_router.py:72-95` chọn khoá nhà cung
   cấp bằng `next()` trên danh sách deployment, và `_get_region_name_from_api_base()` trả
   `None` cho mọi provider trừ `assemblyai`. Nên **cả 8 tuyến khớp như nhau và luôn lấy dòng
   đầu** → 8 agent dồn vào 1 project → mất nguồn đối chiếu độc lập.
2. Đọc thêm 09/09: `llm_passthrough_endpoints.py:224` lấy khoá từ
   `passthrough_endpoint_router.get_credentials()`, tức là **bỏ qua router hoàn toàn**. Mất
   luôn lọc tag, mất hạn mức rpm, mất bí danh model. Không có tag thì
   `load_gateway.py:238` không quy được dòng về agent nào.

### Quyết định 2 — XOÁ `model_group_alias`, và đây là sửa lỗi

Ngày 08/09 change trước thêm `model_group_alias: {gemini-2.5-flash: gemini-flash}` để CRM
gọi tên cũ mà không phải sửa code. Với tuyến Vertex thật mang **đúng tên đó**, bí danh trở
thành **nguy hiểm**, không phải dư thừa.

`router.py:11011`:

```python
_model_from_alias = self._get_model_from_alias(model=model)
if _model_from_alias is not None:
    model = _model_from_alias
```

Bí danh được giải **trước** khi tra model group thật, và ghi đè `model`. Nên để lại thì:

```
   CRM goi "gemini-2.5-flash"
     -> bi danh ghi de thanh "gemini-flash"
     -> ra gemini/gemini-3.6-flash        <- SAI MODEL
     -> tuyen Vertex moi KHONG BAO GIO duoc goi toi
     -> request van 200, so van co dong, chi cot model la sai
```

Đúng lớp hỏng im lặng của dự án này. Và nó còn kéo theo chi phí: theo `ref_price`,
`gemini-3.6-flash` là $0,75/$3,75 còn `gemini-2.5-flash` là $0,30/$2,50 — với tỷ lệ
vào/ra của CRM (10,0M / 12,2M) thì đắt hơn **1,59 lần**.

### Quyết định 3 — Tuyến Vertex **express mode**, khoá bằng API key qua `api_base`

**Sửa 09/09/2026 sau khi đo.** Bản đầu của quyết định này viết
`model: vertex_ai/gemini-2.5-flash` + `vertex_credentials: /app/vertex-sa.json`. **Không dùng
được** với thứ người dùng có trong tay: `KEY_BENCH_CRM_TEST` là **API key** (dạng `AQ.`, 53 ký
tự) tạo trong Cloud Console, không phải service account JSON.

Đọc fork: `vertex_llm_base.py:703` chỉ nhận API key khi `custom_llm_provider == "gemini"`;
nhánh `vertex_ai` đi đường OAuth/service account. Nên `model: vertex_ai/…` sẽ **không** chạy
với khoá này.

Đường chạy được — đo trực tiếp, có đối chứng:

| Điều kiểm | Kết quả |
|---|---|
| `aiplatform.googleapis.com/v1/publishers/google/models/gemini-2.5-flash:generateContent?key=` | **200** |
| cùng URL, nhưng auth bằng header `x-goog-api-key` (**cái LiteLLM gửi**) | **200** |
| cùng URL, header mang khoá **sai** | **401** — nên auth thật sự được kiểm, không phải endpoint mở |
| `gemini-2.5-flash` | **có** — model production đang dùng, không phải thay thế |
| `gemini-3.6-flash` | có |
| một tên model **bịa ra** (đối chứng) | **không có** — "Publisher model … not found", nên phép đo phân biệt được |

Nên cấu hình là:

```yaml
- model_name: gemini-2.5-flash                 # dung ten CRM dang goi
  litellm_params:
    model: gemini/gemini-2.5-flash             # provider `gemini` -> duong API key
    api_key: os.environ/KEY_BENCH_CRM_TEST
    # `_check_custom_proxy` dung `{api_base}/models/{model}:{endpoint}`, nen api_base
    # PHAI ket thuc o `/publishers/google` -- thieu doan do thi URL sai va ra 404.
    api_base: https://aiplatform.googleapis.com/v1/publishers/google
    tags: ["crm-feedback"]
    rpm: 15
```

**Không** khai `vertex_project` / `vertex_location`: đường express tự suy project từ khoá, và
tự chọn region — thông báo lỗi của đối chứng cho thấy nó chọn `asia-southeast1`, không phải
`us-central1` như bản đầu giả định.

Đổi lại được một thứ **tốt hơn** bản đầu: không có file bí mật nào phải mount, nên không có
đường nào để khoá lọt vào git; chỉ một biến môi trường, giống mọi khoá khác đang có.

**`rpm: 15` giữ nguyên dù Vertex trả tiền có hạn mức cao hơn** — người dùng chốt 09/09: giữ
con số sát production nhất. Nếu production chạy free tier thì đo dưới hạn mức rộng sẽ không
nói được gì về production. Hệ quả cần biết: CRM ở 7,3 rpm nằm **dưới nửa** trần 15, nên
**sẽ không bao giờ thấy 429 trong vận hành bình thường** — nhánh xử lý 429 vì thế không
được thử ở change này. Đó là việc của change thứ hai, và phải **cố ý ép** mới thấy.

### Quyết định 4 — Nghiệm thu bằng **harness chỉ gọi tầng LLM**, không chạy cả pipeline

Chạy cả pipeline để nghiệm thu là sai, vì code **không có cờ dry-run nào**: không
`skip_upload`, không `skip_email`, không `DISABLE_*`. Bật container = tải SharePoint thật +
gọi LLM 5–60 phút + **ghi lại SharePoint thật** + **gửi email cho người thật**.

Thứ change này sửa chỉ là bước [3]. Nên nghiệm thu chỉ bước [3]:

```
   mot script goi init_llm_client() + call_llm_batch()
   voi vai dong lay tu sample_data/CRM_merge_sample.xlsx (6.304 byte, co san trong repo)
   -> KHONG SharePoint, KHONG email, KHONG ghi Excel
   -> ~1 phut thay vi 10-65
   -> van chung minh du: xac thuc, tag, ghi so, dashboard
```

Lưu ý pipeline **xoá file input cục bộ rồi mới tải từ SharePoint** (`pipeline.py:344`), nên
sample không dùng được cho cả pipeline — nhưng dùng cho harness thì được.

### Quyết định 5 — Nhánh mới **dựng** request, không **dịch** request

Không có lớp chuyển đổi nào giữa hai định dạng. `call_llm_batch(client, model_name,
system_prompt, batch)` nhận vào **dữ liệu trung lập**: một chuỗi và một list dict. Lời gọi
Gemini được *dựng* từ đó; lời gọi OpenAI cũng *dựng* từ đúng đó.

```
   system_prompt ─┐
                  ├─▶ GenerateContentConfig + contents=...        (nhanh cu)
   batch ─────────┤
                  └─▶ {"messages":[{system},{user}]}              (nhanh gateway)
```

Nhờ vậy không có bảng ánh xạ nào phải bảo trì, và SDK của Google đổi cũng không ảnh hưởng
nhánh gateway. Chỗ duy nhất phải đổi ở chiều về: đọc `choices[0].message.content` thay cho
`resp.text`.

Dùng `httpx` — đã được `src/llm.py` import sẵn, nên **không thêm phụ thuộc, không build lại
image**. Không dùng `openai` SDK: nó không có trong `requirements.txt`.

## Risks / Trade-offs

**Giá mà LiteLLM tính có thể không khớp hoá đơn Vertex** → đường này khai
`model: gemini/gemini-2.5-flash`, nên LiteLLM tra bảng giá của **Google AI Studio**
($0,30/$2,50 theo `ref_price`) trong khi tiền thật đi qua **Vertex**. Hai bảng giá thường
bằng nhau nhưng **chưa đo**. Cột `cost_usd` của nguồn `gateway` vốn đã là "suy từ bảng giá",
nên đây không phải hỏng mới — nhưng phải đối chiếu với hoá đơn Vertex ở Giai đoạn 6 chứ đừng
coi con số LiteLLM tính là đã xác nhận.

**Đã quan sát MỘT lượt gọi mất 81 giây, và KHÔNG tái hiện được** → 09/09/2026: một lượt qua
Gateway mất 81 giây trong khi gọi **thẳng** Google cùng thời điểm chỉ 1,4 giây. Ba lượt tiếp
theo qua Gateway: 1,1 / 2,3 / 0,86 giây.

**Bản đầu của mục này viết đó là chi phí "khởi động nguội". Rút lại — chưa chứng minh được.**
Sau khi `--force-recreate` cả hai instance, lượt gọi **đầu tiên** chỉ mất 0,80 giây, dù log
cho thấy Prisma vẫn chuẩn bị toolchain ở lần khởi động đó. Nên "lượt đầu sau khởi động thì
chậm" là **sai**; nguyên nhân thật của 81 giây kia **chưa biết**.

Nó hỏng theo kiểu gây hiểu nhầm: `LiteLLM_SpendLogs.startTime` là mốc **bắt đầu** request,
nên dòng sổ trông như đã xong ngay, trong khi client vẫn đang chờ; và nginx ghi **499** —
"client tự ngắt" — làm người đọc tưởng client sai. Tôi đã chẩn đoán nhầm một lượt thành "treo
ở đường trả về" trước khi đối chiếu timestamp trong log LiteLLM.

Hệ quả: mọi timeout ở phía client phải **trên 90 giây**, và một phép kiểm sức khoẻ dùng lượt
gọi thật với timeout ngắn sẽ báo hỏng oan ngay sau mỗi lần khởi động.

**Nhận 429 bằng cách so chuỗi** → `llm.py` quyết định lùi lịch sự hay không bằng cách tìm
chuỗi trong **thông báo lỗi**:

```python
if "429" in low or "rate limit" in low or "resource_exhausted" in low:
    wait = min(120, 10 * attempt) + random.random() * 2      # lui lich su
...
    time.sleep(4.0 * attempt)                                 # lui chung, NGAN hon
```

Nhánh mới ném lỗi httpx trần thì thông báo có thể **không chứa** chữ nào trong ba chữ đó →
CRM rơi vào nhánh lùi chung, ngắn hơn, và **dập vào một Gateway vừa xin nó chậm lại**. Bắt
buộc: lỗi từ nhánh gateway phải mang chuỗi `429` trong thông báo.

**Tiền tố `models/`** → `init_llm_client` **tự thêm** `models/` cho nhánh AI Studio, và
README dặn người dùng đặt `GEMINI_MODEL=models/gemini-2.5-flash`. Bí danh/tuyến Gateway là
`gemini-2.5-flash` **không tiền tố**. Nhánh gateway phải cắt tiền tố, không thì "model not
found".

**Chế độ JSON bị bỏ im lặng** → `response_mime_type: "application/json"` thành
`response_format` ở dạng OpenAI. Cấu hình có `drop_params: true`, nên nếu provider không
nhận thì LiteLLM **bỏ tham số mà không báo**. `_parse_llm_json` có phòng thủ (tìm `[`…`]`,
sửa dấu phẩy thừa, `json_repair` dự phòng) nên có thể vẫn chạy — nhưng "có thể" phải đo một
lần, không được suy.

**`resp.text` vắng mặt hỏng theo kiểu gây hiểu nhầm** → `getattr(resp, "text", "")` có giá
trị mặc định, nên sai hình dạng phản hồi sẽ ra chuỗi rỗng, rồi `_parse_llm_json("")` ném
"Could not parse valid JSON array". Triệu chứng trỏ vào **prompt**, không trỏ vào chỗ sai
thật.

**Vertex có thể không phục vụ `gemini-2.5-flash`** → chưa biết. Hai endpoint metadata đã thử
đều trả cùng mã cho một tên model bịa ra, nên không trả lời được. Cần một lượt
`generateContent` thật. Nếu không có model đó thì **dừng lại quyết định**, đừng lặng lẽ đổi
sang model khác — đó chính là cái bẫy Quyết định 2 vừa gỡ.

**Project mới là "new user" của Google** → không ảnh hưởng nếu đi Vertex, nhưng nếu phải lùi
về AI Studio thì khoá của project mới gần như chắc chắn bị chặn `gemini-2.5-flash`, y như
`KEY_GOOGLE_AI_STU`.

**Hoá đơn chuyển project** → tiền của CRM sẽ rời `crm-500509` sang project mới.
`dim_agent.gcp_project_id` của agent 7 đang ghi `crm-500509` nên thành sai. Khả năng tách
hoá đơn theo agent **vẫn giữ** vì project mới là project riêng của CRM, nhưng con số cũ và
mới không nối liền được.

**Mạng: compose của CRM không khai `networks:`** → thêm mạng vào mà không liệt kê lại mạng
ngầm định sẽ đẩy service ra khỏi mạng của chính nó. CRM chỉ có **một** service nên nhẹ hơn
DMS, nhưng vẫn phải liệt kê cả hai.

**`docs/HANDOVER.md` của CRM lệch code trên mọi con số** → nó nói `step1..step4_*.py` riêng
lẻ (code là `pipeline.py` một khối 922 dòng), `google-generativeai` (code dùng
`google-genai`), `gemini-2.0-flash` (code `gemini-2.5-flash`), 2,5s (3,5s), 5 retry (3), 20
dòng/batch (25). Ai đọc doc để làm sẽ đi sai. Đáng báo lại nhóm CRM, không thuộc phạm vi
change này.

## Migration Plan

1. Xin project mới + service account JSON. Chạy **một** lượt `generateContent` thật để biết
   Vertex có `gemini-2.5-flash` hay không → quyết định trước khi khai tuyến.
2. Khai tuyến Vertex, **xoá bí danh**, mount file khoá, cấp virtual key.
3. Chứng minh bằng harness — chưa đụng vào container CRM.
4. Thêm nhánh `gateway` + override mạng trong bản clone CRM, mặc định **vẫn** là nhánh cũ.
5. Bật `GEMINI_BACKEND=gateway`, chạy harness lần nữa qua đúng đường CRM sẽ đi.
6. Quay lui = đổi một biến môi trường về `vertex`. Không có thay đổi schema nào phải hoàn
   tác.

## Open Questions

- Vertex có phục vụ `gemini-2.5-flash` không? Quyết định cả tuyến phụ thuộc câu này.
- `.env` thật của production đặt `GEMINI_MIN_INTERVAL_S` bao nhiêu? Người dùng chốt dùng con
  số tác giả khuyến nghị (7,5s) cho phép thử, nhưng con số production vẫn chưa biết — và nó
  quyết định liệu production có đụng trần 15 rpm hay không.
- `dim_agent.gcp_project_id` của agent 7: ghi lại thành project mới, hay giữ `crm-500509` và
  ghi chú? Chưa quyết.


## Cách chạy ô 7.6 — soạn 11/09/2026

### Lý do chặn cũ đã hết, và nó chưa bao giờ cần sửa mã

Ghi chú trong ô 7.6 nói phải sửa `src/llm.py` của repo CRM để trỏ nhánh cũ sang Vertex. Đọc lại
mã thì không phải: `init_llm_client()` chọn nhánh **chỉ bằng biến môi trường**.

```
   GEMINI_BACKEND = gateway ? ───── có ──> NHÁNH MỚI, đi Gateway
            │ không
   USE_VERTEX=True VÀ có sa-key.json ? ── có ──> NHÁNH CŨ, đi Vertex
            │ không
                             NHÁNH CŨ, đi AI Studio
```

`USE_VERTEX` mặc định đã là `True`, và `sa-key.json` **đã có trong repo CRM từ 10/09**. Nên
nhánh cũ hiện đi thẳng Vertex. Không phải sửa dòng nào.

Một lo ngại khác cũng đã tự hết: ngày 08/09 có bí danh đẩy `gemini-2.5-flash` sang
`gemini-3.6-flash`, nhưng bí danh đó **đã gỡ** và CRM nay có tuyến thật mang đúng tên. Hai nhánh
chạy **cùng một model trên cùng một nền Vertex**, chỉ khác kiểu xác thực.

### Khác biệt còn lại LỚN HƠN thứ ô này định đo

Tuyến CRM mang `reasoning_effort: "disable"` (thêm 10/09). Nhánh cũ thì không ai tắt nghĩ. Nên
hai nhánh khác nhau ở **hai** biến, không phải một.

Nhìn theo hướng khác thì đây là cơ hội. Chú thích trong `config.gateway.yaml` viết *"tắt suy
nghĩ không làm giảm chất lượng"*. Câu đó là **lập luận, chưa từng đo**. Ô 7.6 là phép đo duy
nhất đang có kế hoạch mà kiểm được nó.

```
                    NGHĨ BẬT          NGHĨ TẮT
   nhánh cũ           A0          [cần sửa mã CRM, không làm]
   nhánh gateway      C                  B

   A0 với C  ->  tách riêng ảnh hưởng của ĐƯỜNG ĐI
   C  với B  ->  tách riêng ảnh hưởng của CHUYỆN NGHĨ
```

Ô C chạy được **chỉ sau khi** nâng `max_output_tokens` trong repo CRM: đi gateway mà bật nghĩ
chính là cấu hình đã hỏng ngày 10/09 (phần nghĩ ăn 96% hạn mức, gửi 5 nhận 1). Tuyến gateway
KHÔNG nâng đè được, vì `max_tokens` do client gửi thì thắng.

### Thứ tự chạy, và điều kiện dừng sớm

```
   Bước 1  CỘT MỐC: nhánh cũ chạy HAI LẦN cùng một đầu vào
           -> tỷ lệ model tự mâu thuẫn với chính nó
           thiếu bước này thì mọi so sánh sau đều không đọc được

   Bước 2  A0 với B
              │
      lệch TRONG mức cột mốc ──> XONG, không cần ô C, không cần sửa mã ai
      lệch VƯỢT mức cột mốc  ──> cần ô C, tức cần việc bàn giao CRM trước
```

### Ba luật của phép đo

1. **Cột mốc là bắt buộc.** `temperature = 0` không bảo đảm hai lượt giống nhau. Nhánh cũ tự
   lệch 3% mà hai nhánh lệch 2% thì kết luận đúng là *"không thấy khác biệt"*.
2. **Cửa chặn số bản ghi.** Lượt gọi nào trả về thiếu bản ghi thì bỏ cả lô, không đem so.
   Thiếu do cắt cụt trông y hệt thiếu do model đổi ý.
3. **Chỉ so ô do LLM điền.** Ô do tầng từ khoá chốt thì hai nhánh giống nhau theo cấu tạo; đem
   vào chỉ làm loãng con số.

### Một điểm không hiển nhiên

Cùng đặt `max_output_tokens = 8192` nhưng con số đó **nghĩa khác nhau ở hai nhánh**. Đi thẳng
Vertex thì phần nghĩ nằm ở ngăn riêng (`thoughts_token_count`), nên 8192 là 8192 dành cho câu
trả lời. Qua Gateway thì phần nghĩ nằm chung ngăn với câu trả lời.

Nhờ vậy A0 và B — dù một bên nghĩ một bên không — **đều có đủ 8192 cho câu trả lời**, nên so
được sòng phẳng. Chỉ ô C mới vướng.

### Hai chỗ phải nhớ khi đọc số

- Nhánh cũ đi thẳng Google nên **lượt gọi của nó không vào sổ Gateway**.
- Phải chạy bằng `--entrypoint python`; thiếu là container chạy pipeline thật, tải SharePoint
  và gửi email.
