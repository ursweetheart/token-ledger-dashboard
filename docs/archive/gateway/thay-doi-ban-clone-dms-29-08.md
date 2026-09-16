# Bản clone `dms-feedback-classification` — thay đổi để dựng được, 29/08/2026

Ghi lại mọi thứ đã đụng vào bản clone tại `D:\RangDonk\dms-feedback-classification`,
để (a) dựng lại được, (b) báo lại nhóm phát triển DMS những chỗ đáng sửa.

Mục tiêu của bản clone: đo đường ghi của API Gateway trên một agent thật, thay vì mô
phỏng bằng `curl` như đợt đo 26/08.

---

## 1. Nguyên tắc đã giữ

**Không sửa một dòng nào trong file của nhóm DMS.** Toàn bộ thay đổi là *thêm file mới*,
và mọi file thêm vào đều nằm ngoài git của họ hoặc là file mới không xung đột.

```
   Sua file cua ho          0 file
   Them file moi            4
   Sua logic agent          0 dong
```

---

## 2. Bốn file/thư mục đã thêm

Tất cả nằm trong `dms-feedback-classification/service/`.

| File | Trạng thái git | Vì sao cần |
|---|---|---|
| `.env` | `.gitignore:6` bỏ qua | Không có sẵn, chỉ có `.env.example` |
| `testvertex.json` | `.gitignore:97` bỏ qua | Chép từ `testvertex.json.example` |
| `data/` | thư mục rỗng | `docker-compose.yml:70` mount `./data:/app/data` |
| `docker-compose.override.yml` | **chưa theo dõi** | Mở cổng ra host, thay cho việc sửa compose gốc |

### Vì sao phải có `testvertex.json` dù chế độ `apikey` không đọc tới nó

`docker-compose.yml:29,77` mount `./testvertex.json:/app/data/sa-key.json:ro`. Docker gặp
đường dẫn nguồn không tồn tại sẽ **tạo một thư mục rỗng cùng tên** rồi mount thư mục đó
vào — container vẫn lên, nhưng lỗi về sau rất khó lần. Chép file mẫu vào là xong.

### `docker-compose.override.yml`

Compose tự nạp file này, không cần cờ gì thêm. Nội dung đúng một việc:

```yaml
services:
  web:
    ports:
      - "127.0.0.1:8502:8501"
```

Lý do: `web` trong file gốc chỉ khai `expose: 8501` (mở trong mạng nội bộ, không ra host).
Cửa duy nhất ra ngoài là `nginx` (`8501:443`), mà `nginx.conf:19-20` đòi `fullchain.pem`
+ `privkey.pem` trong `./ssl/` — thứ chưa có. Mở thẳng cổng của `web` rẻ hơn nhiều so với
dựng chứng chỉ tự ký, và phép đo không cần TLS vì mọi thứ đều trên `127.0.0.1`.

Chọn `8502` chứ không phải `8501` để sau này có dùng cả `nginx` thì hai cái không tranh cổng.

---

## 3. Các quyết định cấu hình trong `.env`

Giá trị bí mật **không chép vào tài liệu này** — xem trực tiếp trong `.env` (đã gitignore).

### 3.1 Năm trường Azure/SharePoint: giá trị GIẢ, có chủ ý

`settings.py:115-127` đòi đủ `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`,
`SHAREPOINT_DRIVE_ID`, `SHAREPOINT_ROOT_FOLDER_ID` — **vô điều kiện**. Validator không hề
nhìn `ENABLE_SHAREPOINT_CONFIG_SYNC` hay `UPLOAD_INPUT_TO_SHAREPOINT`. Thiếu một trường là
`ValueError` ngay lúc nạp settings, cả `web` lẫn `watcher` đều không khởi động.

Đặt giá trị giả (`khong-dung-ban-clone-cuc-bo`) là **cố ý**: qua được validator, mà không
thể vô tình ghi lên SharePoint thật. Đường `/api/classify/text` không dùng tới trường nào
trong số này.

Kết quả đo: web khởi động bình thường, chỉ ghi cảnh báo và đi tiếp —

```
   Web server failed to restore state from SharePoint Check_Point/:
     Unable to get authority configuration for
     https://login.microsoftonline.com/khong-dung-ban-clone-cuc-bo
   ...
   [INFO] Application startup complete.
```

### 3.2 `GEMINI_BACKEND=apikey` — trung thành với bản chạy thật, không phải giải pháp tình thế

`.env.example:9` ghi `GEMINI_BACKEND=vertex` từ commit đầu tiên. Nhưng đo từ
`fact_monitoring` trên `token_ledger_v2` ngày 29/08:

```
   agent          dich vu Google                       dong
   dms-feedback   generativelanguage.googleapis.com   2.572     <- AI Studio
   dms-feedback   aiplatform.googleapis.com               0     <- Vertex
```

Và cả 7 agent có dữ liệu đều dùng `generativelanguage.googleapis.com`. Chỉ có 20 dòng
`aiplatform` trong toàn bộ dữ liệu (12 của `sale-agent` ngày 20/06, 8 của `contact-center`
ngày 27/06) — trông như hai lượt thử nghiệm, không phải lưu lượng sản xuất.

Hệ quả cho dự án Gateway: điều kiện ① *"8 khoá API của 8 project"* đặt tên **đúng** (là API
key AI Studio, không phải service-account JSON), và tiền tố `gemini/` trong
`config.gateway.yaml` là **đúng** (nếu agent dùng Vertex thì phải viết lại thành
`vertex_ai/...` kèm `vertex_credentials`).

### 3.3 `GEMINI_MODEL`: `gemini-2.5-flash-lite` → `gemini-3.5-flash-lite`

Bắt buộc đổi. Model mặc định đã chết với khoá đang dùng:

```
   404  "This model models/gemini-2.5-flash-lite is no longer available to new
         users. Please update your code to use models/gemini-3.5-flash-lite"
```

Chi tiết về cái bẫy đo đạc ở mục 5.

### 3.4 Tắt mọi đường ghi ra hệ thống thật

```
   ENABLE_SHAREPOINT_CONFIG_SYNC=false
   UPLOAD_INPUT_TO_SHAREPOINT=false
   ENABLE_RUNTIME_CLEANUP=false
   TEAMS_WEBHOOK_URL=              (trong)
   NOTIFICATION_SENDER_EMAIL=      (trong)
   NOTIFICATION_RECIPIENTS=        (trong)
```

Pha đo này chỉ đo **một** biến: đường gọi Gemini. Bật các công tắc trên sẽ kéo theo ghi
thật lên SharePoint và bắn thông báo Teams — không liên quan phép đo, và không lùi lại được.

### 3.5 `JWT_SECRET_KEY` và `DEFAULT_ADMIN_PASSWORD`

`settings.py:146-149` đòi JWT secret ≥ 32 ký tự, bỏ trống là lỗi. Sinh bằng
`secrets.token_urlsafe(48)`.

`DEFAULT_ADMIN_PASSWORD` đặt sẵn một chuỗi sinh ngẫu nhiên thay vì bỏ trống. Lý do ở
`user_store.py:40-47`: bỏ trống thì nó tự sinh **kèm cờ `must_change_password=True`**, và
lần đăng nhập đầu bị bắt đổi mật khẩu — vướng cho một phép đo tự động. Đặt sẵn thì
`must_change=False`, đăng nhập thẳng được.

---

## 4. Chỉ chạy `web`, bỏ `watcher` và `nginx`

```
   docker compose up -d web
```

| Service | Chạy? | Lý do |
|---|---|---|
| `web` | ✅ | Phục vụ `/api/classify/text` — đường duy nhất gọi Gemini mà **không** chạm SharePoint |
| `watcher` | ❌ | Chỉ poll SharePoint mỗi 300s; với credential giả thì lỗi liên tục, không đo được gì thêm |
| `nginx` | ❌ | Đòi chứng chỉ TLS; né bằng `docker-compose.override.yml` |

### Đường dẫn API — tiền tố `/api` dễ bỏ sót

Router khai `prefix="/api/auth"` (`auth_api.py:141`) và `prefix="/api/classify"`
(`classify.py:28`), nhưng `app.py:233-238` gọi `include_router()` **không truyền prefix
thêm**. Gọi `POST /auth/login` trả `404 Not Found` — đường đúng là `POST /api/auth/login`.

---

## 5. Cái bẫy đo đạc quan trọng nhất: `ListModels` nói dối

Trước khi dựng DMS, đã kiểm `gemini-2.5-flash-lite` bằng `GET /v1beta/models` (read-only)
trên đúng khoá sẽ dùng. Kết quả:

```
   gemini-2.5-flash-lite   supportedGenerationMethods: [... generateContent ...]
                           inputTokenLimit 1.048.576 / outputTokenLimit 65.536
   -> ket luan luc do: "model con song, Pha 0 an toan"
```

Gọi thật thì **404**. `ListModels` liệt kê cả model mà khoá này **không gọi được**.

> **`ListModels` không phải phép đo khả dụng.** Chỉ một lượt `generateContent` thật mới kết
> luận được. Cùng họ với chín lỗi im lặng ghi ở nhật ký 26/08 mục 12c và 13: một phép đo
> hỏng trông y hệt một phép đo đạt.

### Hệ quả phải sửa lại: "gemini-2.5-flash còn sống" — nhiều khả năng SAI

Cùng lượt `ListModels` đó cũng liệt kê `gemini-2.5-flash` kèm `generateContent`, và đã dẫn
tới một kết luận tạm thời rằng khoá này gọi được model chiếm **46,2% lưu lượng**, tức
`config.gateway.yaml` đang thiếu một tuyến quan trọng.

Kết luận đó **rút lại**. `KEY_GOOGLE_AI_STU` giờ đã lộ ra là một khoá *"new user"* (bằng
chứng: nó bị chặn `gemini-2.5-flash-lite` với đúng lý do đó). Phán quyết gốc ngày 26/08 —
Google chặn `gemini-2.5-flash` với project mới — nhiều khả năng vẫn đúng.

Chưa kiểm dứt điểm: cần một lượt `generateContent` thật vào `gemini-2.5-flash`.

### Cùng loại, chưa kiểm: tuyến của chính Gateway

`/health/liveliness` trả 200 chỉ nói tiến trình còn sống, **không** nói `gemini-3.6-flash`
bắn ra Google có về hay không. Tuyến `gemini-3.6-flash` và `gemini-3-flash-preview` vẫn
thuộc diện **chưa chứng minh**. (Tuyến `gemini-flash-lite` thì đã chứng minh — mục 7.)

---

## 6. Ba việc đáng báo lại nhóm phát triển DMS

| | Chỗ | Vấn đề |
|---|---|---|
| ① | `settings.py:115-127` | Năm trường Azure/SharePoint bị kiểm **vô điều kiện**. Tắt `ENABLE_SHAREPOINT_CONFIG_SYNC` / `UPLOAD_INPUT_TO_SHAREPOINT` rồi vẫn không khởi động được nếu bỏ trống. Người muốn chạy bản cục bộ không có credential Azure sẽ bị chặn ngay bước đầu |
| ② | `.env.example:9` | Mặc định `GEMINI_BACKEND=vertex` từ commit đầu tiên, trong khi bản chạy thật dùng AI Studio (`apikey`). Ai đọc file mẫu sẽ đi nhầm đường và đi tìm service-account JSON không tồn tại |
| ③ | `settings.py:39` `GEMINI_MODEL_PRICING` | Bảng giá gán cứng 5 model, **không có `gemini-3.5-flash-lite`** — chính model Google vừa ép chuyển sang. Mọi lượt gọi từ giờ sẽ tính ra chi phí **0** mà không báo gì |

Việc ③ là **lỗ hổng thứ ba cùng kiểu trong ngày 29/08**, sau `db/rules.py` và `dim_model`
của dự án này. Ba bảng giá/danh mục độc lập, cùng thiếu model mà nhà cung cấp đang phục vụ.

---

## 7. Trạng thái tính tới cuối ngày 29/08

### Đã chứng minh

**DMS chạy thật, phân loại đúng** (`POST /api/classify/text`):

```
   vao : "Den LED cua Rang Dong dung mot thang thi bi nhap nhay,
          dai ly khong nhan bao hanh"
   ra  : Bao loi = true · Bao hanh = true · sentiment = "Tieu cuc"
         decision_log 2 muc, ly do tieng Viet do LLM sinh
```

**Gateway ghi sổ đúng** — nhưng chứng minh bằng `curl`, **không** phải bằng DMS:

```
   model             gemini/gemini-3.5-flash-lite
   spend             1,17e-05          (khac 0)
   total_tokens      17  = 14 + 3
   end_user          tuan.tran         (tu header X-User)
   status            success
   messages          {}                (2 byte — prompt DA XOA)
   chuoi cau hoi goc 0 lan trong toan bo database
   header x-user     con nguyen trong proxy_server_request.metadata.headers
```

### CHƯA làm — đừng đọc nhầm

**DMS vẫn gọi thẳng Google, chưa đi qua Gateway một request nào.**

```
   GEMINI_API_KEY trong .env cua DMS  =  khoa Google AI Studio (bat dau "AQ.")
   Virtual Key (alias "dms-feedback")  =  da cap, MOI CHI thu bang curl
                                          gia tri: xem LiteLLM_VerificationToken
                                          hoac cap lai bang /key/generate
```

Hai khoá khác vai, không được lẫn:

| Khoá | Ai cầm | Việc |
|---|---|---|
| `KEY_GOOGLE_AI_STU` (`AQ.…`) | **Gateway**, trong `.env` của dashboard | Gateway dùng để gọi ra Google |
| Virtual Key (`sk-…`) | **Agent**, trong `.env` của DMS | Agent dùng để tự xưng danh với Gateway |

---

## 8. Pha 1 — việc còn lại để DMS tự đi qua Gateway

Hai thay đổi, và **đây là lần đầu phải chạm vào code của nhóm DMS**:

**① `src/dms/gemini_client.py:59`** — hiện gọi:

```python
genai_legacy.configure(api_key=self.settings.gemini_api_key)
```

Cần thêm `client_options` + `transport`:

```python
genai_legacy.configure(
    api_key=self.settings.gemini_api_key,          # -> Virtual Key
    client_options={"api_endpoint": "http://host.docker.internal:4000/gemini"},
    transport="rest",                               # bat buoc: mac dinh la gRPC
)
```

`transport="rest"` là bắt buộc — SDK này mặc định ưu tiên gRPC, gọi gRPC vào một
nginx/LiteLLM REST sẽ không kết nối được.

Địa chỉ dùng `host.docker.internal` chứ không phải `127.0.0.1`: từ trong container DMS,
`127.0.0.1` trỏ vào chính nó, không phải máy host.

**② `.env` của DMS** — đổi `GEMINI_API_KEY` từ khoá Google sang Virtual Key.

### Chưa trả lời được

Đường `/gemini` passthrough của LiteLLM đọc khoá nhà cung cấp từ biến `GEMINI_API_KEY` ở
phía **server**, khác tên với `KEY_GOOGLE_AI_STU` đang khai trong `config.gateway.yaml`.
Chưa xác minh nó có tự lấy khoá theo `model_list` hay đòi biến riêng. Cách rẻ nhất để biết:
một lượt `curl` qua `http://127.0.0.1:4000/gemini/v1beta/models/...:generateContent`
trước khi sửa `gemini_client.py`.
