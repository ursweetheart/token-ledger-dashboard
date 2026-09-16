# Đưa DMS Feedback đi qua API Gateway — nhật ký 31/08/2026

Ghi lại lượt triển khai change `route-the-first-agent-through-the-gateway`. Tiếp nối nhật ký
`thay-doi-ban-clone-dms-29-08.md`, và **đính chính vài chỗ trong đó**.

Trạng thái khi bắt đầu: Gateway đã chứng minh ghi sổ đúng bằng `curl` (29/08), DMS đã chứng
minh phân loại đúng (29/08), nhưng **hai thứ chưa nối vào nhau** — 0 request nào của DMS
từng đi qua Gateway.

**Trạng thái cuối ngày: luồng end-to-end ĐÃ CHẠY.** Một lượt `POST /api/classify/text` của
DMS đi qua Gateway, ra Google, về lại DMS với kết quả đúng, và để lại đủ dòng trong sổ.

---

## 1. Chọn đường: `/v1/chat/completions`, không phải `/gemini` passthrough

Nhật ký 29/08 mục 8 phác sẵn đường passthrough (sửa 2 dòng trong `gemini_client.py`). Đường
đó **bị loại**, vì đọc mã nguồn fork `f005afa146` cho thấy nó không nhân lên được 8 agent.

`passthrough_endpoint_router.py:72-95` chọn khoá nhà cung cấp bằng `next()` trên danh sách
deployment, lọc theo đúng ba điều kiện: `use_in_pass_through is True`, provider khớp, và
`deployment_region == region_name`. Với Google AI Studio,
`_get_region_name_from_api_base():314-327` trả `None` cho mọi provider trừ `assemblyai`.

Nên **cả 8 tuyến project đều khớp như nhau, và `next()` luôn lấy dòng đầu tiên**:

```
   /v1/chat/completions              /gemini passthrough
   ────────────────────              ───────────────────
   sk-dms  -> tag dms  -> KEY_DMS    sk-dms   ┐
   sk-sale -> tag sale -> KEY_SALE   sk-sale  ├─> KEY cua dong dau tien
      …                                 …     ┘
   8 agent -> 8 khoa -> 8 project    8 agent -> 1 khoa -> 1 project
```

Hoá đơn Google sẽ dồn cả 8 agent vào một project → **mất nguồn đối chiếu độc lập của Giai
đoạn 6**, đúng thứ mà điều kiện "8 khoá API của 8 project" sinh ra để giữ.

---

## 2. Phát hiện quan trọng nhất: `enable_tag_filtering` mặc định TẮT

Phát hiện lúc **tự soát lại tài liệu change** (30/08), trước khi chạy một lượt nào.

Kế hoạch dựa vào việc virtual key mang `tags` để chọn đúng khoá project. Nhưng lọc theo tag
không tự chạy: `router.py:430` khai `enable_tag_filtering: bool = False`, và
`tag_based_routing.py:483` thoát sớm:

```python
if request_enable_tag_filtering is not True and chain_default is not True:
    return healthy_deployments        # tra ve NGUYEN danh sach, khong loc gi
```

Kiểu hỏng của nó là kiểu tệ nhất:

```
   Thieu enable_tag_filtering
     -> tra ve CA 8 deployment
     -> usage-based-routing-v2 chon theo han muc con lai
     -> request 200 OK · SpendLogs co dong · token dung · cost dung
     -> CHI RIENG khoa project la chon ngau nhien
     -> hoa don Google rai deu ra 8 project, khong ai keu mot tieng
```

Nếu bỏ sót dòng này, **mọi phép đo trong ngày vẫn ĐẠT hết** — chỉ hoá đơn là sai. Đã khai
tường minh trong `config.gateway.yaml`, kèm chú thích nêu rõ kiểu hỏng.

---

## 3. Đã chứng minh được những gì

Tất cả đều bằng phép đo, không suy luận.

### 3.1 Tầng Gateway

| Điều | Bằng chứng |
|---|---|
| Tuyến `gemini-flash-lite` gọi được thật | HTTP 200, 24+1 = 25 token |
| Sổ ghi đúng lượt gọi | `request_id` trong SpendLogs **khớp đúng `id`** trong response |
| Cột `model` là model thật | `gemini/gemini-3.5-flash-lite`, **không phải bí danh** |
| `X-User` thành `end_user` | `tuan.tran`, rồi `svc.dms-feedback` |
| Prompt bị xoá | chuỗi mồi **0 lần** trên `pg_dump` toàn bộ database |
| Header còn nguyên | `metadata.headers.x-user` |
| Giới hạn model của virtual key | gọi tuyến khác thì **403** `key_model_access_denied` |
| **Tag lọc đúng** | 10/10 lượt, `attempted_retries = 0`, **0 lần** chạm tuyến mồi |
| Request **không** tag không được bảo vệ | **1/8 lượt (12,5%) rơi nhầm tuyến** |
| Ranh giới hai sổ | `litellm` có 75 bảng `LiteLLM_*`; `token_ledger_v2` có **đúng 0** |

### 3.2 Tầng DMS — luồng end-to-end

| Điều | Bằng chứng |
|---|---|
| Mạng DMS tới Gateway | từ **trong** container: `POST /v1/chat/completions` ra 200 + có dòng sổ |
| Nhánh backend mới chạy | `_generate_gateway` trả `'OK'`, usage đúng ba khoá |
| **Chế độ JSON không bị nuốt** | cùng prompt: `json_mode=False` ra văn xuôi, `True` ra JSON |
| **Phân loại thật, qua Gateway** | `Báo lỗi = true`, `Bảo hành = true`, `Tiêu cực`, 2 mục — **khớp đúng lượt 29/08** |
| Danh tính đi xuyên | `end_user = svc.dms-feedback` trên dòng sổ của lượt phân loại |
| `MAX_RETRY=1` có tác dụng | log DMS: `generate_json error (1/1)` — một lượt, không phải ba |
| **Lùi lại được** | về `apikey` thì kết quả y hệt, và **SpendLogs đứng yên** |

### 3.3 Cách chứng minh "tag lọc đúng" — và vì sao phép đo đầu tiên sẽ nói dối

Bản kế hoạch đầu định kết luận bằng "10/10 lượt thành công". **Sai.** `num_retries: 3` sẽ
thử lại qua tuyến đúng và che mất lỗi.

Phải đo *lượt chạm*, không đo *kết quả cuối*. Dựng một tuyến mồi cùng `model_name` nhưng
`tags: ["khong-ai-dung"]` và khoá cố ý sai, rồi đo ba dấu vết độc lập:

```
   10/10 HTTP 200
   10 dong SpendLogs moi (14 - 4), khong thua khong thieu
   attempted_retries = 0 tren CA 10 dong    <- khong co lan thu lai nao che giau
   0 lan cham tuyen moi trong log litellm-1 VA litellm-2
```

### 3.4 Bằng chứng lùi-lại-được, kiêm minh hoạ sống của vấn đề đi vòng

```
   GEMINI_BACKEND=apikey  ->  phan loai VAN DUNG
                          ->  SpendLogs DUNG YEN o 35 dong
                          ->  tuc la da di THANG Google, Gateway khong he biet
```

Vừa chứng minh nhánh cũ còn nguyên, vừa cho thấy tận mắt: **agent nào còn cầm khoá nhà cung
cấp thì còn đi vòng được, và sổ trở thành sổ tự nguyện.** Đó là toàn bộ lý do dùng Virtual Key.

---

## 4. Năm cái bẫy đo đạc — cùng họ với chín lỗi im lặng ghi ở nhật ký 26/08

### 4.1 LiteLLM ghi sổ **bất đồng bộ**

Query `count(*)` ngay sau khi `curl` trả về thì vẫn thấy số cũ. Dòng xuất hiện sau **~4
giây**. Một phép đo "gọi xong, đếm ngay" sẽ kết luận **SAI** rằng Gateway không ghi sổ.

> Mọi phép đếm phải **theo dõi lặp cho tới khi đổi**, không đếm một lần.

### 4.2 `num_retries` che mất lỗi định tuyến

Xem 3.3. Phép kiểm âm mà bên dưới có cơ chế thử lại thì phải đo *lượt chạm*.

### 4.3 `requester_ip_address` không dùng để quy trách nhiệm được

Nó ghi `172.20.0.9` — đó là **`gateway-lb`**, không phải container gọi. Danh tính agent
**chỉ** đến từ Virtual Key.

### 4.4 Phép thử JSON đầu tiên không tách được biến

Lần đầu tôi thử `json_mode=True` bằng một prompt **có chữ "trả về JSON"**. Kết quả ra JSON —
nhưng điều đó không chứng minh gì, vì model có thể chỉ đang nghe lời prompt. Đo lại bằng
**cùng một prompt không hề nhắc JSON**:

```
   "Thu do cua Viet Nam la thanh pho nao"
     json_mode=False  ->  "Thu do cua Viet Nam la **thanh pho Ha Noi**."   (van xuoi)
     json_mode=True   ->  {"thu_do": "Ha Noi"}                            (JSON hop le)
```

Kết luận: **`drop_params: true` KHÔNG nuốt `response_format`.**

### 4.5 `env_file` chỉ nạp lúc **tạo** container

`GEMINI_GATEWAY_*` đọc qua `os.environ`. `docker compose restart` **không** đọc lại
`env_file` — phải `up -d --force-recreate`. Quên bước này thì `GEMINI_GATEWAY_USER` rỗng,
header `X-User` biến mất **im lặng**, cột `end_user` trống mà không có lỗi nào.

---

### 4.6 `up --profile gateway` thoát giữa chừng, `gateway-lb` không lên

Gặp lúc dựng lại ngày 31/08. `docker-compose.yml:199` ghi cứng IP của máy server:

```yaml
      - "192.168.20.111:${WEB_PORT:-8080}:80"
```

Trên máy dev không có IP đó nên `web` không bind được, và **compose thoát ngay tại đó** —
`gateway-lb` đứng sau trong thứ tự dựng nên không bao giờ được tạo:

```
   redis, redis-replica, litellm-1, litellm-2   ✓ len het, healthy
   web                                          ✗ khong bind duoc
        └──▶ compose thoat
   gateway-lb                                   -- khong duoc dung toi
```

Bẫy nằm ở chỗ `docker ps` sau đó cho thấy hai bản LiteLLM đều `healthy`, trông rất giống
đã dựng xong — trong khi **cửa vào cổng 4000 thì không tồn tại**. Mọi lượt gọi từ DMS sẽ
hỏng ở tầng mạng, và DMS thì trả HTTP 200 kèm "safe fallback" (mục 7).

Chữa tại chỗ: `docker compose --profile gateway up -d gateway-lb`.
Chữa gốc: đưa địa chỉ bind thành tham số, `"${WEB_BIND_HOST:-127.0.0.1}:${WEB_PORT:-8080}:80"`,
để server đặt IP thật trong `.env` còn máy dev dùng mặc định. Chưa sửa — đó là dòng do
người khác cố ý đặt, cần hỏi trước.

---

## 5. Bốn chỗ kế hoạch sai so với thực tế

| | Kế hoạch viết | Thực tế |
|---|---|---|
| ① | "Cấp Virtual Key qua `/key/generate`" | Khoá **đã có sẵn từ 29/08** (`key_alias dms-feedback`, `spend 1,17e-05` khớp đúng dòng SpendLogs 29/08) |
| ② | — | Khoá cũ **thiếu `tags`**, và **giá trị `sk-…` gốc không lưu ở đâu**. LiteLLM chỉ giữ hash |
| ③ | "10/10 lượt thành công là đạt" | Sẽ cho kết quả **giả đạt**, xem 4.2 |
| ④ | "chỉ sửa 1 file của nhóm DMS" | **Phải sửa 2.** `settings.py:130` có danh sách trắng vô điều kiện `{"vertex", "apikey"}` — nhánh thứ ba không thể tồn tại nếu không nới nó |

Với ②, sửa metadata khoá cũ là **ngõ cụt**: sửa xong vẫn không ai gọi được. Đã cấp khoá mới
`dms-feedback-tagged` có `metadata.tags`, và **giữ nguyên khoá cũ** làm hồ sơ phép đo 29/08.

Cũng đã xác minh LiteLLM đọc tag ở đâu: `litellm_pre_call_utils.py:1942`
`key_metadata = user_api_key_dict.metadata`. Trường `tags` cấp cao trong response
`/key/generate` là thứ khác và đang `null`; bảng `LiteLLM_VerificationToken` **không có cột
`tags`**.

---

## 6. Đã đụng vào những gì

> **Mọi thay đổi đều nằm trên nhánh `Tuan-develop` của cả hai repo, chưa commit gì.**
> Bản clone DMS trước đó ở `main` nhưng **chưa có commit nào của mình** (commit mới nhất
> `f875b24` là của nhóm DMS), nên `git checkout -b` mang nguyên thay đổi sang, không mất gì
> và không có nhánh lạ nào phải xoá. `main` vẫn đứng nguyên.

### 6.1 Trong repo `token-ledger-dashboard`

`docker/gateway/config.gateway.yaml` — hai chỗ, đều là **thêm**:
- `tags: ["dms-feedback"]` trên tuyến `gemini-flash-lite`
- `enable_tag_filtering: true` trong `router_settings`, kèm chú thích nêu rõ kiểu hỏng

### 6.2 Trong bản clone `dms-feedback-classification`

```
   File cua nhom DMS bi sua        2     (gemini_client.py, settings.py)
   File moi cua minh               1     (docker-compose.override.yml, da co tu 29/08)
   Logic phan loai bi sua          0 dong
```

**`gemini_client.py`** — chỉ *thêm*, không sửa dòng nào của hai nhánh cũ:
- `_init_gateway()` + `_generate_gateway(prompt, temperature, json_mode)`
- nhánh `gateway` trong công tắc của `generate()` và `generate_json()`, đặt **giữa** `vertex`
  và `apikey` để `apikey` vẫn là mặc định

Gộp còn **hai** method thay vì ba: `_generate_gateway_json` không cần tồn tại vì khác biệt
duy nhất là một trường trong payload.

**`settings.py`** — hai chỗ, đều là nới rộng:
- `{"vertex", "apikey"}` → `{"vertex", "apikey", "gateway"}`
- thêm chốt `if backend == "gateway" and not self.gemini_api_key: raise`, giữ đúng khuôn hai
  nhánh cũ

**`docker-compose.override.yml`** — nối `web` vào mạng của Gateway.

### 6.3 Hai quyết định giữ cho phạm vi nhỏ

**Dùng `httpx`, không dùng `openai` SDK.** Đo trong container: `openai` KHÔNG có,
`httpx 0.28.1` CÓ. Chọn httpx nên **không thêm dòng nào vào `requirements.txt` và không phải
build lại image**.

**Đọc cấu hình từ `os.environ`, không thêm trường vào `settings.py`.** Hợp lệ vì
`docker-compose.yml:11` cho `web` một `env_file:`, `settings.py:28` để `extra="ignore"`, và
**chính `gemini_client.py` đã đọc/ghi `os.environ` sẵn** trong `_init_vertex`. Hai biến:
`GEMINI_GATEWAY_BASE_URL` (mặc định `http://gateway-lb:4000`) và `GEMINI_GATEWAY_USER`.

### 6.4 Vì sao không dùng `host.docker.internal`

`gateway-lb` mở cổng trên `127.0.0.1:4000` — cố ý, để Gateway không ra mạng. Từ container
thuộc compose project khác, `host.docker.internal` có xuyên được vào cổng chỉ bind loopback
hay không thì **vẫn chưa biết**. Ta đã **đi vòng qua** câu hỏi đó, chứ không trả lời nó.

**Bẫy bắt được lúc đọc lại, trước khi viết:** compose gốc của DMS **không khai `networks:`**
→ mọi service dùng mạng `default` ngầm định. Nếu chỉ viết `networks: [gateway]` thì Compose
**bỏ mạng ngầm định đó đi** và `web` rời khỏi mạng của chính DMS. Phải liệt kê **cả hai**.

### 6.5 `X-User`: đặt định danh dịch vụ, không bịa ra con người

`web/api/classify.py:43` `classify_text(body, user: dict = CURRENT_USER_DEP)` **có** cầm danh
tính, nhưng `GeminiClient.generate()` nằm sâu bên dưới và không nhận nó — luồn xuống phải sửa
thêm nhiều file của nhóm DMS.

Giải pháp: `GEMINI_GATEWAY_USER=svc.dms-feedback` — định danh **dịch vụ**, đã có sẵn trong
danh mục tài khoản của dự án. Không bịa ra một con người: một `end_user` sai làm hỏng chiều
người dùng của cả dashboard, để trống còn hơn điền bừa. Lấy claim `sub` của JWT cho từng
người dùng là change riêng.

---

## 7. Năm việc đáng báo lại nhóm DMS

Ba việc đầu ghi ở nhật ký 29/08, hai việc sau phát hiện hôm nay.

| | Chỗ | Vấn đề |
|---|---|---|
| ① | `settings.py:115-127` | Năm trường Azure/SharePoint bị kiểm **vô điều kiện** |
| ② | `.env.example:9` | Mặc định `GEMINI_BACKEND=vertex` trong khi bản chạy thật dùng `apikey` |
| ③ | `settings.py:39` | `GEMINI_MODEL_PRICING` thiếu `gemini-3.5-flash-lite`. **Đã tự kiểm lại 30/08**: bảng giá có đúng 5 model và không có model đó, nên mọi lượt gọi tính chi phí **0** mà không báo gì |
| ④ | khởi động app | **Nuốt lỗi cấu hình.** Khi `GEMINI_BACKEND` không hợp lệ, log ghi `Khong the tai cau hinh day du` ba lần rồi vẫn `Application startup complete` và phục vụ `GET / 200`. Container báo `healthy` sau 10 giây |
| ⑤ | `classify_batch` | **Trả HTTP 200 khi LLM hỏng.** Log: `Pure-LLM issue classifier fail: 429` → `using safe fallback`. Người gọi không có cách nào biết lượt phân loại đó chưa hề được LLM xử lý |

④ và ⑤ cùng một họ, và **ngược hẳn** kỷ luật của chính dự án Gateway (`entrypoint.sh`,
`DASHBOARD_KEY`): *chế độ hỏng phải là "không chạy", tuyệt đối không phải "chạy khuyết"*.

Với một dự án đếm token thì ⑤ đặc biệt nguy: **công việc không xảy ra nhưng trông y hệt đã
xảy ra**.

---

## 8. Ba điều phải biết trước khi viết `db/load_gateway.py`

### 8.1 Lượt gọi HỎNG vẫn sinh dòng trong `LiteLLM_SpendLogs`

```
   dong hong        status = 'failure'   spend = 0
                    total_tokens = 14 tren 2/5 dong, = 0 tren 3/5 dong
                    metadata->>'error_information' co gia tri that
   dong thanh cong  status = 'success'
```

Loader **phải lọc theo `status`**, nếu không sẽ đếm cả lượt hỏng thành lưu lượng thật.
Điều kiện đúng là `WHERE status = 'success'`.

> **Sửa lỗi 31/08, đo lại lúc 07:5x.** Bản đầu của mục này ghi dòng thành công có
> `status = NULL`. **Sai.** Đo trên 39/39 dòng: không có dòng nào NULL, cột chỉ nhận
> đúng hai giá trị `success` và `failure`.
>
> ```
>    SELECT count(*) ... WHERE status IS NULL   ->  0
>    string_agg(DISTINCT status, ', ')          ->  failure, success
> ```
>
> Nếu loader viết theo bản sai (`WHERE status IS NULL`) thì nó trả về **0 dòng và
> không báo lỗi gì** — dashboard sẽ hiện số 0 trông y như "chưa có lưu lượng".

### 8.2 Một lượt phân loại = **hai** lượt gọi LLM

```
   pipeline/rag_product.py:190       generate()        233 +   3 =   236 token
   pipeline/issue_classifier.py:424  generate_json()  5.643 + 401 = 6.044 token
```

Hệ quả: `rpm: 60` thực chất chỉ đủ **~30 lượt phân loại/phút**. Phải nhớ khi tính công suất
và khi đối chiếu số lượt gọi với số bản ghi nghiệp vụ.

### 8.3 `startTime` là UTC trần — phải cộng 7 giờ

Đo 31/08:

```
   kieu cot startTime ...... timestamp without time zone   (KHONG co mui gio)
   TimeZone cua DB ......... UTC
   dong ghi luc 07:56 VN ... luu thanh 00:56
   dong ghi luc 02:33 VN ... luu thanh 30/08 19:33   <-- LECH SANG NGAY HOM TRUOC
```

Quy ước dữ liệu chốt 14/08 là **mọi ngày tính theo giờ VN**. Cột này không mang múi giờ nên
Postgres sẽ không tự quy đổi giúp — loader phải tự cộng:

```sql
   "startTime" + interval '7 hour'
```

Đây là loại lỗi **tổng vẫn khớp, phân bố theo ngày thì sai**: mọi lượt gọi từ 17:00 tới nửa
đêm giờ VN sẽ bị dồn sang ngày hôm trước. Cùng họ với lỗi múi giờ đã gặp ở nguồn Ralli.

---

## 9. Trạng thái và việc còn lại

### Đã xong — change 64/64 task

Mục 1 (dựng nền) · 2 (chứng minh tuyến) · 3 (virtual key + tag) · 4 (nối mạng) ·
5 (nhánh backend) · 6 (`.env` + luồng thật) · 7 (chế độ JSON) · 8 (số lượt gọi) ·
9 (lùi lại được). `openspec validate`: hợp lệ.

### Đo lại 31/08 lúc 07:56 — sau một lượt tắt máy

Dựng lại từ máy nguội và gọi thật một lượt nữa. Sổ đi từ 37 lên 39 dòng sau ~2 giây:

```
  31/08 07:56:41  success  gemini/gemini-3.5-flash-lite  svc.dms-feedback
                  dms-feedback-tagged     243 +   3 =   246 tok   0,0000804
  31/08 07:56:42  success  gemini/gemini-3.5-flash-lite  svc.dms-feedback
                  dms-feedback-tagged   5.652 + 408 = 6.060 tok   0,0027156
```

Kết quả phân loại khớp mốc 29/08: `Báo lỗi` = true, `Bảo hành` = true, `Tiêu cực`,
`decision_log` 2 mục. Cấu hình trong container khớp đĩa (md5 `44c841f7…` cả hai bên),
`enable_tag_filtering: true` đã được nạp.

Mỗi cột bác bỏ được đúng một cách hỏng: `key_alias` loại khả năng DMS đi vòng qua gateway ·
`end_user` loại khả năng mất `X-User` · `model` là tên upstream nên bí danh đã được dịch ·
`messages {}` chứng tỏ che nội dung còn chạy · `status = success` loại khả năng
"có dòng nhưng lượt gọi hỏng".

### Việc còn lại

- ~~Chưa có `db/load_gateway.py`~~ — **XONG 31/08**, change
  `load-the-gateway-ledger-into-the-database`. Dashboard đã hiện được lưu lượng DMS:
  `usage_resolved` trả về `Phân Loại Phản Hồi Tiếp Thị | gemini-3.5-flash-lite | 34 lượt |
  31.839 token | token_source=gateway`. Nhật ký: `nap-so-gateway-vao-database-31-08.md`.
  Việc phải thêm hai cột `source` và `cost_usd` vào `fact_call` là phát sinh khi triển khai,
  không nằm trong dự kiến ban đầu — chi tiết ở nhật ký đó mục 2.1.
- Mới chứng minh trên **một** agent. Việc "8 khoá / 8 project" mới chỉ được *thiết kế cho*,
  chưa được *đo*, cho tới khi có agent thứ hai với khoá project riêng.
- Chưa commit gì. Mọi thay đổi nằm trên nhánh `Tuan-develop` của cả hai repo.

### Còn chưa chắc — đừng đọc thành đã biết

- `host.docker.internal` có xuyên được cổng bind loopback hay không: **đã né, chưa trả lời**
- Tuyến `gemini-3.6-flash` và `gemini-3-flash-preview`: **vẫn chưa chứng minh gọi được**
  (nguyên trạng từ 29/08). Chỉ `gemini-3.5-flash-lite` có bằng chứng
- Cách `fallbacks` cư xử khi có đủ 8 tuyến dùng chung một hạn mức: chưa đo
- Lọc theo tag khi có **nhiều** tuyến cùng bí danh: cơ chế đã chứng minh bằng phép kiểm mồi,
  nhưng cấu hình 8 tuyến thật thì **chưa từng đo**. Hiện chỉ có một tuyến `gemini-flash-lite`,
  nên tag chưa phải chọn giữa cái gì — đừng đọc lượt đo 31/08 thành bằng chứng cho việc đó
