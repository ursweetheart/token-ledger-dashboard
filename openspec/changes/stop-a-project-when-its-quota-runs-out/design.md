## Context

Hệ thống hôm nay có ba mảnh rời nhau:

```
   agent ──▶ gateway-lb ──▶ litellm-1/2 ──▶ Google
                                 │
                                 ▼
                        database `litellm`
                        LiteLLM_SpendLogs         <- tien Gateway thay
                        LiteLLM_VerificationToken <- khoa ao: spend, metadata
                                 │
                        ledger-refresh (moi 300s)
                                 ▼
                        database `token_ledger_v2`
                        fact_call, fact_usage_daily
                                 │
                        FastAPI (CHI-DOC) ──▶ web/  <- nguoi xem
```

Ba ràng buộc có sẵn, không được phá:

- **API chỉ-đọc là cơ chế, không phải lời hứa.** Vai PostgreSQL của backend mang
  `default_transaction_read_only = on`; `backend/store.py` mở đầu bằng *"nếu ai thêm nhầm thì
  database tự từ chối"*.
- **Hai database tách bạch có chủ ý.** `token_ledger_v2` phải có **đúng 0** bảng `LiteLLM_*`, và
  database `litellm` do Prisma của LiteLLM quản — repo cố ý không trồng bảng vào đó.
- **Cấu hình Gateway là nguồn sự thật, không phải bảng trong DB** (`store_model_in_db: false`).

Lưu lượng hiện tại rất thấp: agent **Phân Loại Dữ Liệu CRM** đo được 1.888 lượt trong gần hai
tháng. Con số này quyết định nhiều lựa chọn kỹ thuật bên dưới — ở mức này, những tối ưu thường phải
làm thì chưa cần làm.

## Goals / Non-Goals

**Goals:**
- Một project hết hạn mức thì lưu lượng của nó dừng lại ở Gateway, trước khi tốn tiền.
- Agent không phải sửa một dòng nào. LiteLLM cũng không.
- Người quản trị nhập và nạp hạn mức từ dashboard, và biết trước khi hết qua email.
- Mọi lượt bị chặn đều truy nguyên được.

**Non-Goals:**
- Hạn mức theo từng người dùng. Đã cân nhắc và bỏ.
- Tự reset theo chu kỳ.
- Đưa nốt sáu agent còn lại qua Gateway. Việc đó độc lập và có đường riêng của nó.
- Làm cho số tiền chính xác hơn số hiện có. Change này dùng số đang có, không cải thiện nó.

## Decisions

### D1 — Hạn mức nằm trong `metadata` của virtual key, không nằm trong bảng nào

Đây là quyết định gốc; các quyết định còn lại đều rơi ra từ nó.

Mỗi khi một request tới, LiteLLM đã đưa sẵn cho hook một gói thông tin về khoá:

```
   user_api_key_dict
     ├── spend        = 38.42     <- LiteLLM tu cong sau moi luot
     ├── max_budget   = None
     ├── metadata     = {...}     <- o ghi chu TU DO, LiteLLM khong dung toi
     └── key_alias    = "crm-feedback-tagged"
```

Ghi hạn mức vào `metadata` (`{"quota_usd": 50, "quota_log": [...]}`) thì:

- **Không bảng mới, không migration, không vai database mới.** Ba thứ này kéo theo cả một chuỗi:
  `KEEP_ON_REBUILD`, phép kiểm phạm vi vai, cấp quyền sau mỗi lần dựng lại database.
- **Không tự `SUM` số đã tiêu.** LiteLLM đã cộng sẵn vào `spend`.
- **Hook không cần kết nối database nào.** Mọi thứ nằm trong tham số nó nhận được.
- **Sửa bằng một lệnh API** (`/key/update`), không đụng schema do Prisma quản.

Vì sao **không** dùng ô `max_budget` chính thức: nó khiến LiteLLM tự chặn ở **cửa xác thực**, tức
là trước khi hook kịp chạy — và nó trả HTTP 400 cho mọi agent, mất hẳn khả năng trả tin nhắn giả.

```
   request ──▶ [cua xac thuc]  max_budget het? ──▶ 400, het chuyen
                     │
                     ▼ chua het
                 [hook]   <- cho duy nhat minh chon duoc cach tra loi
```

| Phương án | Vì sao không chọn |
|---|---|
| `max_budget` trên khoá | LiteLLM tự chặn trước hook → 400 cho mọi agent |
| Ngân sách theo tag | cùng vấn đề, và số nằm ở chỗ người nhập không nhìn thấy |
| Bảng riêng trong `token_ledger_v2` | kéo theo migration, vai DB, `KEEP_ON_REBUILD`, kết nối thứ hai |
| Bảng riêng trong `litellm` | Prisma quản schema đó; repo đã cố ý không đụng |
| Sửa mã nguồn LiteLLM | hook là cửa chính thức, sửa fork ở đây không mua thêm gì mà thêm nợ merge |

### D2 — Hook trả về một `RejectedRequestError`, không trả về chuỗi

`chat_completion` bắt đúng lớp lỗi đó rồi dựng câu trả lời:

```python
    except RejectedRequestError as e:                    # proxy_server.py:10143
        _chat_response = litellm.ModelResponse()
        _chat_response.choices[0].message.content = e.message
```

HTTP 200, đúng hình dạng thường, chạy cả ở chế độ luồng.

**Trả về chuỗi thì KHÔNG ra kết quả này — đã kiểm bằng mã nguồn.** `process_pre_call_hook_response`
(`proxy/utils.py:1158`) chỉ đổi chuỗi thành `RejectedRequestError` khi
`call_type in ["completion", "text_completion"]`; mọi giá trị khác rơi vào
`raise HTTPException(status_code=400, ...)`. Mà `/v1/chat/completions` truyền
`route_type="acompletion"` (`proxy_server.py:10086`), và `pre_call_hook` chuyển nguyên giá trị đó
xuống hook. Nên một hook trả chuỗi sẽ cho agent **HTTP 400**, đúng thứ change này muốn tránh.

Trả về đối tượng lỗi thì không dính nhánh đó: `process_pre_call_hook_response` kiểm
`isinstance(response, Exception)` **trước tiên** và `raise` thẳng, không xét `call_type`.

**CHẾ ĐỘ LUỒNG ĐÒI MỘT BẢN VÁ TRONG FORK — đo ngày 20/09/2026.**
Nhánh không-luồng chạy đúng ngay, nhưng `stream=True` trả HTTP 500:

```
   AttributeError: 'NoneType' object has no attribute 'model_call_details'
   streaming_handler.py:206
```

`proxy_server.py` lấy `litellm_logging_obj` từ `request_data` của lỗi, mà tại thời điểm
pre-call khoá đó **có mặt nhưng giá trị còn là None** (đã xác nhận bằng một lần in ra các khoá
của `data`). Agent chat thì gần như luôn dùng chế độ luồng, nên không vá là mất hẳn tính năng.

Đã thử đường không-vá và **bỏ**: đặt `data["mock_response"]` chạy đúng ở cả hai chế độ, nhưng lượt
bị chặn đi vào `LiteLLM_SpendLogs` như một lượt **thành công, có token và có tiền** — đo được 79
token / 0,0001799 USD cho một câu thông báo, trong khi không hề gọi Google. Nó làm hỏng đúng thứ
dự án này sinh ra để giữ.

Bản vá `_REJECTED_STREAM_LOGGING_FALLBACK` trong fork làm hai việc, cả hai đều hẹp:

1. thiếu `litellm_logging_obj` thì dựng một `Logging` **thật** (không phải object giả — wrapper
   còn dùng nó ở hơn chục chỗ khác: `call_type`, success handler, caching);
2. đặt mã trả về của nhánh luồng thành **200**, khớp nhánh không-luồng ngay bên dưới nó. Chính
   LiteLLM đang không nhất quán: cùng một lỗi, cùng một câu trả lời, hai mã HTTP khác nhau chỉ vì
   client có bật `stream` hay không. Client nhận 400 phần lớn coi là lỗi và không đọc thân.

Đo sau khi vá: **cả hai chế độ trả 200 với đúng câu thông báo**, và sổ ghi `failure`, spend 0,
token 0 — không làm phồng một con số nào.

Giá phải trả, và nó là giá đã biết trước: mỗi bản vá là một món nợ khi merge upstream. Vì vậy CI
có một bước canh giữ **cả hai** bản vá (`FORK_PATCHES`), và bước đó chạy **trước** khi build, để
không image hỏng nào lên kho. Kiểu hỏng của bản vá này nguy hơn bản vá Sentinel: Sentinel mất thì
LiteLLM chết ngay lúc khởi động, còn cái này mất thì mọi thứ vẫn lên xanh và chỉ lộ ra khi có
người dùng thật gặp đúng lúc hết hạn mức.

### D3 — Loại agent (chat / chạy lô) khai trong cấu hình hook, mặc định là 429

Ánh xạ tag → loại agent là thuộc tính của **agent**, không phải của project. Đặt trong cấu hình
của hook, cạnh `config.gateway.yaml` — nơi các quyết định định tuyến khác đã nằm, và nơi có vết
trong git.

Tag chưa khai thì mặc định **429**. Sai kiểu theo hướng này chỉ làm agent nghỉ; sai theo hướng kia
làm dữ liệu rác đi vào database của một agent phân loại.

Hook lấy tag từ `data["metadata"]["tags"]`, đã được gắn trước khi hook chạy
(`litellm_pre_call_utils.py:1410` chạy ở bước `add_litellm_data_to_request`, dòng 1711; hook chạy ở
dòng 1863).

### D4 — Lượt bị chặn ghi một dòng JSON ra log, chưa dựng bảng

Bảng cho lượt bị chặn sẽ kéo về đúng ba thứ mà D1 vừa bỏ được: migration, vai ghi, và một mục nữa
trong `KEEP_ON_REBUILD`. Đổi lại được gì? Một báo cáo theo ngày mà hôm nay chưa ai hỏi.

Một dòng JSON ra `stdout` là đủ để trả lời câu sẽ có người hỏi — *"sáng nay agent im, hỏng à?"*:

```json
{"event":"quota_block","at":"2026-09-20T14:22:07+07:00","agent":"crm-feedback",
 "project":"crm-500509","model":"gemini-2.5-flash","quota":50.0,"spent":50.03,"reply":"429"}
```

Docker đã xoay vòng log sẵn (10MB × 3 mỗi container), và khi quota hết thì lưu lượng **dừng**, nên
số dòng rất ít — đây không phải nguồn sinh log lớn.

Giới hạn phải biết: log mất khi container bị xoá, và không truy vấn được theo ngày. Nâng cấp khi
cần: đọc các dòng này trong bộ nạp và đổ vào một bảng — việc nhỏ, độc lập, làm sau không phải sửa
gì của change này.

### D5 — Số đã tiêu lấy từ `spend` của khoá, chấp nhận trễ tối đa 5 phút

`user_api_key_cache_ttl: 300` nghĩa là khoá được nhớ đệm 300 giây, nên `spend` hook nhìn thấy có
thể là số của 5 phút trước. Ở 1.888 lượt trong hai tháng, một cửa sổ 5 phút thường không có lượt
gọi nào — khoản vượt thêm vì độ trễ này gần bằng không.

Không hạ TTL để đổi lấy độ chính xác: 300 giây là con số đã đo và đã chọn ngày 08/09 để khoá ảo
sống sót qua một lần Postgres khởi động lại. Đổi nó là mở lại một vấn đề đã đóng.

Ngưỡng phải xem lại: khi lưu lượng vượt khoảng **10 lượt/giây**, hoặc khi khoản vượt vì độ trễ lớn
hơn mức chấp nhận được, thì đọc thẳng `spend` từ database thay vì lấy từ khoá đã nhớ đệm.

### D6 — Đường ghi: hai endpoint gọi sang LiteLLM, database vẫn chỉ-đọc

```
   web  ──POST /api/quota──▶  backend  ──/key/update──▶  LiteLLM
         Bearer <khoa chung>            Bearer <master key>
              │                              │
         caller() san co              metadata cua khoa
```

Backend **không ghi database**. Kỷ luật chỉ-đọc giữ nguyên 100%, không vai mới, không `GRANT` mới,
`read-only-api-durability` không phải sửa một chữ.

Cái giá là backend phải giữ **master key** của Gateway — khoá mở được mọi thứ của LiteLLM. Ba ràng
buộc bắt buộc đi kèm:

1. Backend chỉ được gọi đúng `/key/update`, và chỉ sửa đúng hai khoá metadata (`quota_usd`,
   `quota_log`). Không có endpoint nào chuyển tiếp lệnh tuỳ ý sang Gateway.
2. Master key đọc từ biến môi trường, thiếu thì backend dừng — cùng kỷ luật với `DASHBOARD_KEY`.
3. Master key MUST NOT xuất hiện trong câu trả lời của bất kỳ endpoint nào, kể cả thông báo lỗi.

Không cần chống CSRF: khoá đi trong header `Authorization` lấy từ `localStorage`, không dùng cookie.

**Ghi metadata là THAY THẾ, không phải gộp — đây là chỗ nguy nhất của cả change.**
`prepare_metadata_fields` (`key_management_endpoints.py:2010`) chỉ giữ metadata cũ khi yêu cầu
**không** mang `metadata`:

```python
    if "metadata" not in non_default_values:      # chi khi KHONG gui
        non_default_values["metadata"] = existing_metadata.copy()
```

Gửi `{"metadata": {"quota_usd": 50}}` sẽ **xoá `tags`** của khoá. Hậu quả không phải là quota hỏng —
mà là **tag định danh biến mất**, request rơi ngẫu nhiên vào tuyến khác, và tiền ghi sai project.
Đo ngày 31/08 trên khoá không mang tag: 7/8 lượt vẫn thành công, 1/8 lạc tuyến. Tức là hỏng **12,5%**,
im lặng, và mọi lượt gọi thử đều trông như bình thường.

Nên đường ghi bắt buộc là **đọc – gộp – ghi lại cả cục**:

```
   /key/info  ──▶  metadata hien co
                        │  gop them quota_usd, quota_log
                        ▼
   /key/update ──▶  metadata DAY DU (con nguyen tags)
```

Giới hạn đã biết: hai người sửa cùng lúc thì người ghi sau đè mất thay đổi của người trước. Với một
người quản trị thì chưa thành vấn đề; nếu sau này có nhiều người, phải kiểm lại giá trị cũ trước khi
ghi.

### D7 — Số hiển thị trên tab Setting phải là chính số dùng để chặn

Hai nguồn tiền không bằng nhau: `spend` của khoá chỉ thấy lưu lượng qua Gateway; dashboard thấy cả
nguồn Google. Nếu tab Setting hiện số của dashboard mà hook chặn theo `spend` của khoá thì người
nhập sẽ thấy *"38/50"* trong khi agent đã bị chặn — không cách nào giải thích được.

Nên tab Setting đọc hạn mức và số đã tiêu **từ chính khoá** (qua `/key/info`), kèm một dòng nói rõ
đây là phần Gateway thấy. Tổng chi phí mọi nguồn vẫn xem ở các tab cũ, không đổi gì.

### D8 — Cảnh báo là một tiến trình riêng, theo khuôn `watch_gateway.py`

`scripts/watch_gateway.py` đã có đủ: gửi SMTP, lưu trạng thái ra file JSON, và **chỉ gửi thư khi
trạng thái đổi**. Quota watcher chỉ đổi thứ đem so — từ "Gateway sống hay chết" thành "đang ở bậc
nào". Một dịch vụ compose nữa, cùng image `tools`, không thêm phụ thuộc.

Cấu hình SMTP giữ nguyên ở `.env`, **không** đưa lên tab Setting: đưa lên nghĩa là mật khẩu máy chủ
thư nằm trong database và hiện trên trang web, đổi lấy một tiện lợi dùng đúng một lần.

### D9 — Cổng khoá: đổi CSS và thứ tự dựng trang, không thêm thư viện

Markup và logic đã có (`#key-gate`, `showKeyGate()`, `hideKeyGate()`). Việc cần làm là cho nó
`position: fixed; inset: 0`, nền đặc, và không dựng phần còn lại của trang trước khi có khoá.

### D10 — File hook gắn vào container, vì image không chứa mã của ta

Image LiteLLM do CI đóng gói từ fork và tải về từ GHCR — trong đó **không có** file nào của repo
này. Cấu hình và `entrypoint.sh` hiện đã đi vào container bằng cách gắn thẳng từ máy:

```yaml
    volumes:
      - ./docker/gateway/config.gateway.yaml:/app/config.yaml:ro
      - ./docker/gateway/entrypoint.sh:/gateway-entrypoint.sh:ro
```

File hook đi cùng đường đó, gắn chỉ-đọc, và khai trong `litellm_settings.callbacks`. Không dựng lại
image, không đổi nhãn image, không đụng CI, fork vẫn sạch.

## Risks / Trade-offs

**[Chỉ chặn được 2/8 agent]** → Nói thẳng trên giao diện, ngay cạnh ô nhập của từng project. Tab
Setting phải phân biệt rõ "hạn mức này chặn được" với "hạn mức này chỉ để cảnh báo".

**[Phân Loại Dữ Liệu CRM có đường lui đi thẳng Google]** → Khi nó rơi vào `sa-key.json`, hạn mức
không chặn được. Mâu thuẫn với chính change đã cho nó đường lui đó; không giải trong change này.

**[Backend giữ master key của Gateway]** → Ai có khoá dashboard thì gián tiếp gọi được một đường
hẹp sang Gateway. Giảm thiểu bằng ba ràng buộc ở D6, nhưng rủi ro không biến mất: nếu endpoint viết
lỏng tay, nó thành đường chuyển tiếp lệnh tuỳ ý. Phép kiểm phải thử gửi các khoá metadata lạ và
khẳng định chúng bị bỏ.

**[Hạn mức gắn với KHOÁ, không gắn với project]** → Hôm nay một agent = một khoá = một project nên
khớp. Ngày nào một project có hai khoá thì số bị tách đôi và hạn mức mất nghĩa. Tab Setting phải
phát hiện và nói ra khi một project có nhiều hơn một khoá.

**[Luôn vượt một khoản nhỏ]** → Đã chốt chấp nhận. Chi phí một request chỉ biết sau khi gọi xong,
cộng thêm độ trễ 5 phút của bộ nhớ đệm khoá.

**[Tiền của LiteLLM là ước tính từ bảng giá nội bộ]** → Model chưa có trong bảng giá thì chi phí ghi
**0**, nên project đó không bao giờ hết hạn mức. Việc này nối thẳng với ý định mở tuyến `*` cho
agent tự chọn model: mở tuyến đó mà không chốt giá trước là mở một lối đi vòng qua hạn mức. Phải
đếm số lượt có chi phí bằng 0 và cảnh báo khi nó tăng.

**[Tin nhắn giả trông như model nói]** → Đó là mục đích, nhưng người dùng cuối không phân biệt được
"model từ chối" với "hệ thống hết tiền". Câu thông báo phải tự nó nói rõ là thông báo của hệ thống.

**[Hook chạy trên mọi request]** → Một lỗi trong hook là lỗi của toàn bộ Gateway. Mọi nhánh phải có
đường thoát về "cho qua", và phải có phép kiểm cho nhánh hỏng, không chỉ nhánh chạy đúng.

**[Hook có thể không chạy mà mọi đèn vẫn xanh]** → Khai sai tên callback không làm LiteLLM dừng:
container lên, `/health/liveliness` trả 200, Docker báo `healthy`, và quota không chặn gì. Không
được suy ra từ trạng thái container; phải gọi thật một lượt và xác nhận hook có chạy.

**[Đường `metadata` phụ thuộc chỗ LiteLLM chưa siết]** → Trường `tags` cấp cao của `/key/generate`
và `/key/update` là tính năng trả phí (`LiteLLM_ManagementEndpoint_MetadataFields_Premium`), nhưng
vòng kiểm chỉ soi **tên trường của request**, nên `metadata.tags` đi lọt — và dự án đã chạy bằng
đường đó từ 31/08/2026. Nếu bản LiteLLM mới soi cả bên trong `metadata` thì gãy **không chỉ quota**
mà gãy luôn việc quy tiền theo agent.
Dấu hiệu nhận biết: nâng cấp xong thì `/key/update` trả **403**, hoặc virtual key bỗng mất tag.
Khi đó fork là đường chữa: gỡ đúng vòng kiểm ấy, thêm một bước CI canh giữ như bản vá Sentinel đã
làm.

## Migration Plan

Thứ tự này chọn để mỗi bước đều **lùi lại được** và không bước nào bật chặn trước khi số đã đúng:

1. Đặt `quota_usd` vào metadata của một khoá bằng tay, qua `/key/update`. Chưa ai đọc nó. Xác nhận
   khoá vẫn gọi được bình thường và tag vẫn lọc đúng tuyến.
2. Hai endpoint ghi + tab Setting. Nhập được hạn mức, chưa có gì chặn. Số đã tiêu hiện lên để đối
   chiếu bằng mắt với các tab cũ.
3. Cổng khoá phủ toàn màn hình. Độc lập với phần còn lại.
4. Tiến trình cảnh báo email. Vẫn chưa chặn — chạy ở chế độ chỉ báo để xem ngưỡng và thư có đúng
   không.
5. Nạp hook ở **chế độ chỉ ghi nhận**: tính đủ, ghi dòng "lẽ ra đã chặn", nhưng cho mọi request đi
   qua. Chạy tới khi thấy số khớp.
6. Bật chặn thật.

Lùi lại: gỡ hook khỏi cấu hình Gateway rồi dựng lại hai instance — hệ thống về đúng trạng thái
trước change. Metadata còn sót lại trên khoá không gây hại: không ai đọc thì không ai bị chặn.

## Open Questions

- **Đường lui của Phân Loại Dữ Liệu CRM.** Hết hạn mức mà nó tự đi thẳng Google thì hạn mức là hình
  thức. Bỏ đường lui, hay chấp nhận một lỗ thủng có tên? Cần lead quyết.
- **Ngưỡng cảnh báo có cần bậc thứ tư không** (ví dụ 50%) cho project tiêu nhanh? Chưa có dữ liệu
  để biết ba bậc là đủ hay thiếu; để sau một tháng chạy thật rồi xem.
- **`quota_log` trong metadata phình tới đâu thì phải cắt?** Mỗi lần nạp thêm một phần tử. Vài chục
  lần thì không sao; nếu một ngày nó dài bất thường thì phải giữ N lần gần nhất và đẩy phần cũ đi
  đâu đó.
