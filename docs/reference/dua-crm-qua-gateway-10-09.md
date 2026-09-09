# Đưa CRM Classification Pipeline đi qua API Gateway — nhật ký 09–10/09/2026

Nhật ký của change `route-the-crm-agent-through-the-gateway`. Viết theo khuôn
`dua-dms-qua-gateway-31-08.md`, và **chỉ ghi những gì đo được**. Chỗ nào là suy luận thì nói
rõ là suy luận.

Agent 7 (`crm-feedback`) là agent thứ hai đi qua Gateway, sau DMS Feedback. Điểm khác lớn
nhất so với DMS: CRM **không phải web service**. Nó là một pipeline chạy theo lịch, xử lý
theo lô, và tự tuần tự hoá mọi lời gọi LLM bằng một khoá toàn cục.

---

## 1. Kết quả một dòng

CRM gọi **đúng model production của nó** (`gemini-2.5-flash`) qua Gateway, và mọi lượt gọi
quy được về đúng agent lẫn đúng định danh dịch vụ:

```
   container CRM  ->  gateway-lb:4000  ->  Vertex express  ->  Google
                                             |
                                             v
                            LiteLLM_SpendLogs  ->  fact_call  ->  dashboard
```

Đo được trên một lượt gọi thật, prompt production đầy đủ:

| | |
|---|---|
| prompt | 10.181 ký tự |
| số dòng trong lô | 2 (lấy từ `sample_data/CRM_merge_sample.xlsx`) |
| thời gian | 2,75 giây |
| kết quả | JSON hợp lệ, phân tích được bằng **chính `_parse_llm_json` của CRM** |
| `model_group` trong sổ | `gemini-2.5-flash` |
| `model` trong sổ | `gemini/gemini-2.5-flash` |
| token | 4.009 |
| `end_user` | `svc.crm-feedback` |
| tag | `crm-feedback` |
| chạm SharePoint / email / Excel | **không** |

Cột `end_user` là điều đáng nói nhất. Trước hôm nay, `usage_by_account` có **0 dòng** cho
agent 7 — CRM chỉ có tổng theo project, không có chiều định danh nào. Nay mỗi lượt gọi đều
có tên.

---

## 2. CRM khác DMS ở đâu

Bốn chỗ khác, và cả bốn đều ảnh hưởng tới cách tích hợp:

1. **Pipeline theo lịch, không phải web service.** DMS có tiến trình chạy thường trực, sửa
   xong khởi động lại là xong. CRM chạy một lượt rồi thoát, nên không có "trạng thái đang
   chạy" để quan sát — muốn đo thì phải tự gọi tầng LLM.
2. **SDK mới.** CRM dùng `google-genai` (`client.models.generate_content(...)`), DMS dùng
   `google-generativeai` bản cũ. Hình dạng đối tượng khác nhau, nên lớp đứng thay phải theo
   khuôn của SDK mới.
3. **Backend mặc định là Vertex, không phải khoá API.** DMS đi AI Studio. CRM đi Vertex với
   service account. Đây là lý do phải dựng tuyến **Vertex express mode** thay vì dùng lại
   tuyến AI Studio đang có.
4. **Tự tuần tự hoá lời gọi.** `wait_for_rate_limit()` giữ một khoá toàn cục và ép khoảng
   cách giữa hai lần bắt đầu gọi:

   ```python
   interval = config.MIN_INTERVAL_S + random.random() * config.JITTER_S
   ```

   Nên nhịp tối đa CRM tự cho phép là `60 / (MIN_INTERVAL_S + JITTER_S/2)`:

   | nguồn giá trị | khoảng cách | trung bình | nhịp tối đa |
   |---|---|---|---|
   | `.env.example` khuyến nghị | `7,5s + jitter 1,5s` | 8,25s | **7,3** lượt/phút |
   | mặc định trong code | `3,5s + jitter 0,5s` | 3,75s | **16,0** lượt/phút |

   **Một cái bẫy tôi vừa rơi vào, ghi lại vì nó rất dễ tái diễn.** Hai tham số này lấy giá
   trị từ **hai chỗ khác nhau**, và hai chỗ đó **không khớp nhau**:

   ```
   .env.example  : GEMINI_MIN_INTERVAL_S=7.5   GEMINI_JITTER_S=1.5
   config.py     : mac dinh 3.5                mac dinh 0.5
   ```

   Lấy khoảng cách của `.env.example` ghép với jitter mặc định của code cho ra `7,75s` →
   `7,7` lượt/phút — một con số **không tương ứng với bất kỳ cấu hình thật nào**. Tôi đã
   tính ra đúng con số đó và tưởng là mình đang sửa một lỗi. Phải lấy **cả cặp từ cùng một
   nguồn**.

   Cả hai nhịp đều nằm dưới trần `rpm: 15` của tuyến. Nhịp production thì **chưa biết**, vì
   chưa hỏi được nhóm CRM `.env` thật đặt gì — xem 8.4.

---

## 3. Đã chứng minh được những gì

### 3.1 Tầng Gateway

- Tuyến Vertex express chạy: `model_name: gemini-2.5-flash` → `model:
  gemini/gemini-2.5-flash`, khoá bằng `api_key: os.environ/KEY_BENCH_CRM_TEST`, `api_base:
  https://aiplatform.googleapis.com/v1/publishers/google`. 200 trong 0,80 giây
- `api_base` **phải** kết thúc ở `/publishers/google`, vì `_check_custom_proxy` nối thêm
  `/models/{model}:{endpoint}`. Không khai `vertex_project` / `vertex_location` — express tự
  suy ra từ khoá
- **Hai cửa xác thực phân biệt được bằng mã trả về**: `403` = danh sách `models` của khoá,
  `401` = lọc tag. Danh sách `models` chạy **trước** và ngắn mạch
- Virtual key `crm-feedback-tagged` cấp qua `/key/generate`, mang **đúng một** tag định danh
- Khớp model theo **tên nhóm**: khai `models` là `gemini-2.5-flash` thì gọi tên đó ra 200,
  gọi `gemini-flash-lite` ra 403 kèm câu `This key can only access models=[...]`

### 3.2 Tầng CRM — luồng end-to-end

Xem bảng ở mục 1. Thêm hai điều:

- **Đường lùi còn nguyên.** Bỏ `GEMINI_BACKEND` ra thì CRM in `>>> Using Google AI Studio
  client...` rồi ném **đúng lỗi cũ** `No GEMINI_API_KEY environment variable found!` tại
  `llm.py:172`. Nhánh mới không chiếm mặc định
- **Sổ tự đến dashboard**, không chạy lệnh nào. Dịch vụ `ledger-refresh` lo phần đó. Đo lại
  sau một lượt tắt máy: `fact_call` đi từ 383 lên 385 dòng trong vòng một chu kỳ 120 giây

**Một chỗ dễ đọc sai, phát hiện khi soát lại các con số trên.** Agent 7 hiện có 9 dòng gắn
`account_id = 951`, nhưng **chỉ 3 dòng** trong đó thật sự có `X-User`:

```
   user_id = svc.crm-feedback   ->  3 dong   (harness + 2 luot do che do JSON)
   user_id = (rong)             ->  6 dong   (curl tay, khong gui X-User)
   ca 9 dong                    ->  account_id = 951
```

Sáu dòng kia rơi vào 951 vì `account_id` **nằm trong khoá chính** của `fact_usage_daily` nên
không được NULL, và bộ nạp neo chúng vào tài khoản của chính agent gửi request
(`__technical_7__`). Việc này **cố ý và có ghi chú**, không phải lỗi — và với agent 7 thì neo
**chính là đáp án đúng**, theo quy ước 20/08 rằng 6/8 agent chỉ có một người dùng là tài khoản
dịch vụ `svc.<code>`.

Nhưng hệ quả về cách đọc số thì thật: **`account_id` không nói được định danh có được gửi hay
không.** Cột nói điều đó là `user_id`, và con số nói điều đó là bộ đếm `end_user empty` của bộ
nạp. Ai dựng một ô "độ phủ định danh" trên `account_id` sẽ báo 100% cho một agent gửi 0 header.
Đây cũng chính là bộ đếm mà mục 5.2 vừa gỡ khỏi thùng rác.

### 3.3 Chế độ JSON có thật tới Google — và cách đo cho đúng

`drop_params: true` bỏ tham số nhà cung cấp không nhận **mà không báo**. `_parse_llm_json`
của CRM lại tự vá được JSON hỏng. Nên "kết quả vẫn đúng" **không** chứng minh gì.

Đo hai tầng:

**Tầng cơ chế** — gọi đúng hàm mà router gọi, không tốn tiền, không ra mạng:

```
   litellm.utils.get_optional_params(custom_llm_provider="gemini", drop_params=True, ...)
     khong khai  ->  {}
     co khai     ->  {"response_mime_type": "application/json"}
```

`response_format` **có** trong danh sách tham số được hỗ trợ, nên `drop_params` không đụng
tới nó, và nó dịch sang đúng trường chế độ JSON của Google. LiteLLM `1.99.0`.

**Tầng đầu-cuối** — hai lượt giống hệt nhau trừ một tham số, cùng `temperature: 0.0`, câu
nhắc chọn sao cho câu trả lời **tự nhiên là văn xuôi**:

```
   "Reply with the single word hello. No punctuation, no explanation, no quotes."
     khong khai  ->  hello        <- json.loads THAT BAI
     co khai     ->  "hello"      <- json.loads THANH CONG
```

Lượt thứ nhất là phép đối chứng. Không có nó thì lượt thứ hai vô nghĩa, vì model vẫn hay tự
trả JSON khi được nhắc.

**Và việc này đã được đo một lần rồi.** Mục 4.4 của nhật ký DMS 31/08 đã kết luận đúng câu
này, bằng **đúng** phương pháp chênh lệch, với câu nhắc `Thu do cua Viet Nam la thanh pho
nao`. Tôi dựng lại phép đo mà không tra nhật ký cũ trước. Phần thật sự mới chỉ có hai điều:
phép đo chạy trên **tuyến Vertex** chứ không phải AI Studio, và tầng cơ chế chỉ ra được *vì
sao* tham số sống sót chứ không chỉ ra rằng nó sống sót.

**Vì sao điều này quan trọng với CRM hơn là với DMS.** Nhánh cũ của CRM đặt chế độ JSON
**trực tiếp** ở tầng nhà cung cấp:

```python
config=types.GenerateContentConfig(
    system_instruction=system_prompt,
    temperature=0.0,
    max_output_tokens=8192,
    response_mime_type="application/json",   # <- dat truc tiep
)
```

Nhánh Gateway không gọi được trường đó, nó chỉ gửi được `response_format` của OpenAI. Nên câu
hỏi thật không phải "chế độ JSON có bật không" mà là **"hai nhánh có đặt cùng một trường ở
tầng nhà cung cấp không"**. Tầng cơ chế trả lời đúng câu đó: `response_format` dịch ra
`response_mime_type: application/json`, **cùng một trường, cùng một giá trị**. Nếu nó bị bỏ
thì nhánh Gateway sẽ chạy ở một chế độ khác nhánh cũ mà không ai thấy — và `_parse_llm_json`
sẽ che đi phần lớn hậu quả.

### 3.4 Cơ chế bí danh che tuyến thật — chứng minh được cả hai chiều

Thêm bí danh tạm `gemini-flash-lite → gemini-flash` trên một tuyến **đã có**, rồi gọi:

```
   HTTP 200
   model_group = gemini-flash-lite       <- trong DUNG
   model       = gemini/gemini-3.6-flash <- BI DANH THANG TUYEN THAT
```

Xoá bí danh, gọi lại → `model = gemini/gemini-3.5-flash-lite`. Cả hai chiều đều đo được, và
`git diff --quiet` xác nhận file cấu hình về đúng bản đã commit.

Điểm đáng nhớ nhất: cột `model_group` **vẫn ghi đúng tên người gọi yêu cầu**. Ai chỉ xem cột
đó sẽ không thấy gì bất thường. Chỉ cột `model` lộ ra.

**Lặp lại trên chính tuyến của CRM (10/09), và kết quả hay hơn dự đoán.** Trên tuyến CRM
hôm nay, bí danh **không** gây hỏng im lặng — nó gây **401**:

```
   Not allowed to access model due to tags configuration.
   Passed model=gemini-flash and tags=['crm-feedback']
```

Câu đó chứng minh hai điều một lúc: bí danh **có** ghi đè (người gọi gửi `gemini-2.5-flash`),
và request bị **chặn** vì tuyến `gemini-flash` nay không mang tag nào nên request có tag không
còn chỗ rơi vào.

Nghĩa là task 2.3 — gỡ tag `crm-feedback` khỏi tuyến `gemini-flash` — có một **lợi ích thứ
hai mà lúc làm không ai tính đến**: nó biến một sai-im-lặng thành một hỏng-to-tiếng.

Nhưng hỏng im lặng vẫn là thật, và đo được bằng cách dựng lại **đúng** cấu hình 08/09 (trả
tag về, giữ bí danh):

| cấu hình | mã | `model_group` | `model` trong sổ | tiền |
|---|---|---|---|---|
| bí danh, tuyến không tag (hôm nay) | **401** | `gemini-2.5-flash` | `gemini-2.5-flash` | 0 |
| bí danh + tag (đúng 08/09) | **200** | `gemini-2.5-flash` | **`gemini/gemini-3.6-flash`** | 5,10e-05 |
| đã trả cấu hình | **200** | `gemini-2.5-flash` | `gemini/gemini-2.5-flash` | 3,06e-05 |

Ở dòng giữa, **mọi thứ trông đúng**: mã 200, thân phản hồi ghi `model: gemini-2.5-flash`, cột
`model_group` ghi `gemini-2.5-flash`, `end_user` đúng `svc.crm-feedback`. Chỉ **một** cột lộ
ra. Và chênh giá đo được từ chính hai lượt đó: `3,1875e-06` so với `2,1857e-06` USD/token,
tức **đắt hơn 1,46 lần**.

**Cách trả cấu hình phải chứng minh được.** 4.0 dùng `git diff --quiet`. Ở đây **không dùng
được**, vì file cấu hình đang có thay đổi chưa commit hợp lệ. Mốc so phải là **băm**:
`sha256` sau khi trả khớp từng bit với mốc trước phép đo. Rồi vẫn phải gọi thêm một lượt để
xác nhận bằng phép đo, không bằng một dòng ghi chú.

**Hai chuyện phụ, cùng lộ ra trong phép đo này:**

- **Lượt 401 VẪN sinh một dòng trong sổ nguồn**, với `model` = **tên người gọi đã yêu cầu**
  (`gemini-2.5-flash`), không phải tên mà bí danh ghi đè thành. Token 0, tiền 0, nên không có
  gì bị quy sai — nhưng ai đếm dòng mà không đọc token sẽ tưởng lượt đó đã chạy
- **Cấu hình có khai `fallbacks`, và tuyến CRM KHÔNG nằm trong đó.** Chỉ một dòng:
  `- gemini-flash: ["gemini-flash-preview"]`. LiteLLM tự nói lúc chạy: *"No fallback model
  group found for original model_group=gemini-2.5-flash"*. Nên khi hết hạn mức, tuyến CRM
  **trả 429** chứ không lặng lẽ đổi tuyến. Đây là câu trả lời đo được cho một câu hỏi mở của
  change thứ hai

**Phép đo này để lại vết trong sổ, và vết đó KHÔNG được xoá.** Sau 4.1, agent 7 mang:

| model | lượt | token | USD |
|---|---|---|---|
| `gemini-2.5-flash` | 5 | 4.121 | 0,00201290 |
| `gemini-3.6-flash` | **3** | 22 | 0,00006150 |
| chưa nối được model | 4 | 9 | 0,00001590 |

Ba lượt trên `gemini-3.6-flash` là **lượt thí nghiệm**, không phải lưu lượng CRM thật. Ai đọc
bảng model của agent 7 sẽ thấy một model mà CRM không hề dùng. Ghi lại ở đây thay vì xoá dòng,
vì `fact_call` **cố ý không** cho phép viết lại lịch sử im lặng — xem mục 9.

Bốn dòng "chưa nối được model" cũng có lý do, và cũng là cố ý: ba dòng từ 09/09 sinh ra
**trước** khi 8.2 khai `gemini/gemini-2.5-flash`, và upsert của `fact_call` **không** cập nhật
`model_id`, nên chúng giữ nguyên NULL. Dòng thứ tư là lượt **401** ở 4.1: nó mang tên nhóm
trần `gemini-2.5-flash` (không tiền tố), vì request chết **trước** khi Router chốt tuyến.

Bộ nạp tách đúng hai nghĩa đó, và phép đo 4.1 là lần đầu chuyện này được kiểm trên một lượt
401 thật:

```
   failed calls loaded 1 | model not declared 0 | failed before routing 1
   alias model names 1
```

`model not declared` **bằng 0** mới là kết quả đúng: dòng `failure` không nối được model là
chuyện thường, còn dòng `success` không nối được model mới là **việc phải làm**. Gộp hai thứ
vào một bộ đếm là để một con số đang báo động chìm trong tiếng ồn thường ngày — và đó chính là
bộ đếm mà mục 5.2 vừa gỡ khỏi thùng rác, nên nó phải sạch để còn dùng được.

### 3.5 Thân yêu cầu gửi Google khớp **từng trường** với nhánh cũ

3.3 chỉ chứng minh một trường sống sót. Câu hỏi lớn hơn: nhánh gateway dựng
`messages` kiểu OpenAI, còn nhánh cũ đặt thẳng `GenerateContentConfig`. **Hai thứ đó có ra
cùng một thân yêu cầu không?**

Chỗ dễ hỏng nhất không phải các tham số số học mà là **prompt hệ thống**. Nếu message
`system` bị gộp thành một lượt `user` thì cấu trúc prompt khác nhánh cũ — và khác **không ai
thấy**, vì kết quả vẫn là JSON đọc được.

Đo bằng cách gọi thẳng hàm dựng thân yêu cầu của LiteLLM (`_transform_request_body`, provider
`gemini`), không ra mạng:

```json
{
  "contents": [ { "role": "user", "parts": [ { "text": "<dong CRM>" } ] } ],
  "system_instruction": { "parts": [ { "text": "<prompt he thong>" } ] },
  "generationConfig": {
    "temperature": 0.0,
    "max_output_tokens": 8192,
    "response_mime_type": "application/json"
  }
}
```

Đối chiếu với `GenerateContentConfig` mà nhánh cũ dựng:

| nhánh cũ đặt | thân yêu cầu thật có | khớp |
|---|---|---|
| `system_instruction=system_prompt` | `system_instruction.parts[0].text` | có |
| `contents=user_input` | đúng **một** lượt, `role: user` | có |
| `temperature=0.0` | `generationConfig.temperature` | có |
| `max_output_tokens=8192` | `generationConfig.max_output_tokens` | có |
| `response_mime_type="application/json"` | `generationConfig.response_mime_type` | có |

Prompt hệ thống **không** bị nhét vào `contents`. Nó lên đúng chỗ `system_instruction`, nên
cấu trúc prompt giống nhánh cũ chứ không chỉ giống về nội dung.

Hai chi tiết đáng ghi kèm, vì cả hai đều từng làm tôi đọc sai kết quả:

- **LiteLLM trộn hai kiểu tên khoá.** `generationConfig` viết camelCase nhưng các trường bên
  trong lại snake_case (`max_output_tokens`, không phải `maxOutputTokens`). Google nhận cả
  hai. Phép kiểm đầu của tôi chỉ tìm camelCase nên báo **THIẾU** trong khi trường **CÓ** — lỗi
  phép kiểm, không phải lỗi dữ liệu
- **`transform_request` không phải cửa vào.** Gọi nó cho tuyến Vertex thì nó `raise
  NotImplementedError("Vertex AI has a custom implementation")`. Cửa vào đúng là
  `_transform_request_body`

---

## 4. `/gemini` passthrough: loại, hai lý lẽ độc lập

Passthrough hấp dẫn vì gần như không phải sửa code CRM. Vẫn loại:

1. **Chọn khoá bằng `next()`.** `passthrough_endpoint_router.py:72-95` lấy khoá nhà cung cấp
   bằng `next()` trên danh sách deployment, và `_get_region_name_from_api_base()` trả `None`
   cho mọi provider trừ `assemblyai`. Nên **cả 8 tuyến khớp như nhau và luôn lấy dòng đầu** →
   8 agent dồn vào 1 project → mất nguồn đối chiếu độc lập. Đây là kết luận của nhật ký DMS
   31/08
2. **Bỏ qua router hoàn toàn.** `llm_passthrough_endpoints.py:224` lấy khoá từ
   `passthrough_endpoint_router.get_credentials()`, không đi qua router. Mất lọc tag, mất hạn
   mức `rpm`, mất bí danh model. Không có tag thì `load_gateway.py:238` **không quy được dòng
   về agent nào**

Hai lý lẽ này độc lập: sửa được cái thứ nhất thì cái thứ hai vẫn đủ để loại.

---

## 5. Tám cái bẫy đo đạc gặp trong hai ngày

### 5.1 `GATEWAY_MODELS` thiếu model → dòng vào sổ nhưng dashboard hiện 0

Lần kiểm đầu, `/api/usage` **không có** dòng `gemini-2.5-flash` nào cho CRM. Truy ra:
`GATEWAY_MODELS` trong `db/rules.py` thiếu `gemini/gemini-2.5-flash`, nên dòng vào `fact_call`
với `model_id` **NULL**, `fact_usage_daily` không có dòng, dashboard hiện 0.

Cái bẫy nằm ở chỗ **mọi phép kiểm khác đều ĐẠT**: lượt gọi 200, dòng có trong `fact_call`,
nhóm J của `audit_db.py` ĐẠT — vì nhóm J kiểm dòng *có vào sổ hay không*, mà dòng đã vào.

### 5.2 Dịch vụ tự làm mới **nuốt** chẩn đoán của bộ nạp — lỗi của chính tôi

`db/rules.py` cố ý để tuyến chưa khai rơi vào mục "không nối được model", vì ở đó nó *được
đếm và in ra, không biến mất im lặng*. Nhưng `mot_luot()` chạy bộ nạp với
`capture_output=True` và **chỉ in lại khi bước đó THẤT BẠI**. Ở lượt chạy thành công, dòng
đếm bị ném vào thùng.

Đây là hệ quả của change `let-the-gateway-ledger-arrive-by-itself` do tôi làm: tự động hoá
làm dữ liệu tươi hơn nhưng **bịt mắt một chẩn đoán**. Đã sửa bằng
`print_counters_worth_attention()`, và **chỉ in khi con số khác 0** — in cả lúc bằng 0 thì
mỗi 120 giây thêm một dòng vô nghĩa, người đọc sẽ học cách bỏ qua nó, đúng cái hỏng đang đi
sửa. Kiểm ngược đủ ba trạng thái: có bí danh → im lặng; xoá bí danh → in `model not declared
4`; trả bí danh → im lặng lại.

### 5.3 Chạy nhầm pipeline thật — **ba lần**

Container CRM có entrypoint mặc định là chạy cả pipeline. Quên `--entrypoint python` là chạy
thật. Tôi quên **ba lần**, sau khi **tự tay viết cảnh báo đó** vào `design.md`.

Không gây hại: cả ba lần đều chết ở bước đầu vì không có credential Azure, và đã kiểm sổ sau
mỗi lần — **0 lượt gọi LLM**. Nhưng thứ cứu là credential thiếu, không phải sự cẩn thận.

Pipeline CRM **không có cờ dry-run nào** — không `skip_upload`, không `skip_email`, không
`DISABLE_*`. Bật container lên là tải SharePoint thật + gọi LLM 5–60 phút + ghi lại SharePoint
thật + gửi email cho người thật. Đây là lý do phải nghiệm thu bằng harness.

### 5.4 `env_file` chỉ nạp lúc **tạo** container

`docker compose restart` **không** đọc lại `env_file`. Quên `--force-recreate` thì
`GEMINI_GATEWAY_USER` rỗng, header `X-User` biến mất **im lặng**, cột `end_user` trống mà
không có lỗi nào. Ghi lại từ nhật ký DMS; vẫn đúng với CRM.

### 5.5 `up -d` **không** dựng lại ảnh

`api` và `tools` COPY source vào ảnh. Sửa file trên đĩa rồi `up -d` là chạy code cũ. Đo được:
`grep -c ref_load_run` = 0 trong container, 2 trên đĩa.

### 5.6 Chú thích gõ tay trong file do máy sinh

`db/02_catalog.sql` do `gen_catalog.py` sinh ra, nhưng ngày 04/09 có người gõ tay bốn dòng
chú thích vào đó. Chạy lại là mất sạch. Đã chuyển nội dung về `db/rules.py`, kèm câu nhắc
đừng gõ tay vào file sinh ra.

### 5.7 `count(*)` trên foreign table đã lệch schema vẫn chạy sạch

Phép kiểm lệch schema đầu tiên của tôi dùng `count(*)`, và nó **không chứng minh gì** —
`count(*)` không cần đọc cột nào nên chạy qua cả khi định nghĩa foreign table đã lệch.

### 5.8 Bản tổng kết của `audit_db.py` gộp "chưa kiểm được" vào "khe dữ liệu đã biết"

Lộ ra ở lượt tự soát cuối. Hai dòng cuối của script nói:

```
78 checks | 68 passed | 10 notes | 0 failed
Structure is CLEAN. The 'note' entries are known data gaps, not defects.
```

Trong 10 note đó, **2 note là phép kiểm KHÔNG HỀ CHẠY**:

| | |
|---|---|
| đạt | 68 |
| note là khe dữ liệu thật | 8 |
| note là **phép kiểm không chạy** | **2** |
| hỏng | 0 |

Từng note **có** ghi rõ *"Day KHONG phai ket qua dat"*, nên script trung thực ở tầng từng
dòng. Chỗ hỏng là **dòng tổng kết**: nó khẳng định mọi note đều là khe dữ liệu, không phải
khiếm khuyết. Ai chỉ đọc hai dòng cuối sẽ tin cả 78 phép kiểm đều đã chạy.

Đúng lớp hỏng im lặng mà cả dự án này dựng ra để bắt. Ghi lại, **chưa sửa** — nằm ngoài phạm
vi change này.

**Cùng họ, về cách gọi chứ không về code:** chạy `audit_db.py` **trong container `tools`** thì
nhóm J rơi vào "chưa kiểm được", vì `GATEWAY_DSN` mặc định trỏ `127.0.0.1:5432` — trong
container đó là chính nó. Lần chạy đầu của tôi hôm nay đúng như vậy: `0 failed`, nhưng nhóm J
**không chạy**. Truyền `GATEWAY_DSN` trỏ `postgres:5432` rồi thì nhóm J ĐẠT: *385 dòng đã
nạp, trễ 0s/ngưỡng 420s*, 467 dòng nguồn được soát.

---

## 6. Đã đụng vào những gì

### 6.1 Trong repo `token-ledger-dashboard`

- `docker/gateway/config.gateway.yaml` — thêm tuyến CRM; **xoá** `model_group_alias`; **gỡ**
  tag `crm-feedback` khỏi tuyến `gemini-flash`
- `docker-compose.yml` — truyền `KEY_BENCH_CRM_TEST` vào khối `x-litellm`
- `db/rules.py` — thêm `gemini/gemini-2.5-flash` vào `GATEWAY_MODELS`; cứu 4 dòng chú thích
- `db/02_catalog.sql` — sinh lại
- `scripts/refresh_gateway.py` — in lại bộ đếm đáng chú ý
- `scripts/audit_db.py`, `backend/store.py` — thuộc change trước, xem nhật ký của nó

Hai chỗ **gỡ tag** và **xoá bí danh** là **sửa lỗi**, không phải dọn dẹp. Giữ tag
`crm-feedback` trên tuyến `gemini-flash` sẽ đóng dấu CRM lên **bất kỳ** ai gọi tuyến đó — kể
cả master key không tag — và quy sai vào agent 7.

### 6.2 Trong bản clone `CRM-Classification-Pipeline`

`git diff --stat`: **133 thêm, 2 xoá**. Hai dòng xoá là dòng `def init_llm_client` và
docstring của nó, được thay bằng bản mở rộng. **0 dòng** logic phân loại bị sửa.

`call_llm_batch` gọi `client.models.generate_content(...)` rồi đọc `resp.text`. Nên thay vì
viết lớp dịch giữa hai định dạng, tôi làm một **lớp đứng thay** có đúng hình dạng đó
(`_GatewayClient` / `_GatewayModels` / `_GatewayResponse`). `call_llm_batch` không sửa một
dòng, kể cả vòng thử lại.

Thêm `docker-compose.override.yml` nối container CRM vào mạng Gateway. Phải liệt kê **cả
hai** mạng: `docker-compose.yml` của CRM **không khai `networks:`** nên mọi service đang dùng
mạng `default` ngầm định — liệt kê một mạng là đẩy service ra khỏi mạng của chính nó.

### 6.3 Ba quyết định giữ cho phạm vi nhỏ

- **Dùng `httpx`**, đã được `src/llm.py` import sẵn → `requirements.txt` không đổi, ảnh không
  phải dựng lại. Không dùng `openai` SDK: nó không có trong `requirements.txt`
- **Đọc cấu hình từ `os.environ`**, không thêm trường vào `config.py` — `config.py` đã
  `load_dotenv` sẵn
- **Lỗi quá hạn mức phải mang chuỗi `429`.** `llm.py` nhận 429 bằng cách **so chuỗi** trên
  thông báo lỗi. Thiếu chữ đó thì CRM rơi vào nhánh lùi chung `sleep(4.0 * attempt)` — ngắn
  hơn nhiều — và dập vào một Gateway vừa xin nó chậm lại

### 6.4 Vì sao không dùng `host.docker.internal`

`gateway-lb` cố ý chỉ bind `127.0.0.1`. Chuyện xuyên được vào cổng loopback từ một compose
project khác thì **chưa ai kiểm**. Dùng tên service trong mạng compose.

### 6.5 `X-User`: đặt định danh **dịch vụ**, không bịa ra con người

`svc.crm-feedback`, account 951, đã có sẵn. CRM là pipeline theo lịch, không có người dùng
nào đứng sau một lượt gọi. Bịa một cái tên người vào đó sẽ làm chiều người dùng nói dối.

---

## 7. Bốn việc đáng báo lại nhóm CRM

1. **`GEMINI_BATCH_SIZE=40` không có tác dụng.** `.env.example` khuyến nghị `40`, nhưng
   `config.py:32` là `min(25, ...)` nên bị cắt xuống 25 **mà không báo**. Ai đọc
   `.env.example` sẽ tin lô là 40
2. **`config.CKPT_JSON` là cấu hình chết.** Khai ở `config.py:25`
   (`llm_fills_checkpoint.json`) nhưng **không nơi nào dùng**. `docs/HANDOVER.md` vẫn mô tả nó
   là file cho phép chạy lại. Điểm lưu thật là `save_history_db_atomic` ghi
   `classified_history_db.json` sau mỗi lô (`pipeline.py:688`)
3. **`docs/HANDOVER.md` lệch code trên mọi con số.** Không phải một chỗ — mọi chỗ:

   | HANDOVER.md nói | code thật là | ở đâu |
   |---|---|---|
   | `step1..step4_*.py` riêng lẻ | `pipeline.py`, một khối 922 dòng | dòng 176-179 |
   | `google-generativeai` | `google-genai` | dòng 58, 452 |
   | `gemini-2.0-flash` | `gemini-2.5-flash` | dòng 59, 613 |
   | 2,5s giữa hai lượt | 3,5s | dòng 381 |
   | 5 lần thử lại | 3 | dòng 385 |
   | 20 dòng một lô | 25 | dòng 464, 817 |
   | lùi lịch 429: `15s → 120s` | `10, 20, 30`s (`10 × attempt`, chặn trên 120) | dòng 138, 877 |
   | lùi lịch chung: `2^attempt` | `4,0 × attempt`, tức tuyến tính | dòng 384 |

   Hai dòng cuối là hai dòng đáng lo nhất: ai đọc tài liệu rồi đi đo sẽ **kết luận sai về
   nhánh nào đã chạy**, vì họ đang so với những con số không tồn tại trong code

4. **Không có cờ dry-run.** Xem 5.3. Bất kỳ ai muốn thử pipeline sẽ tải SharePoint thật và
   gửi email thật. Một cờ tắt tác dụng phụ sẽ đáng giá hơn mọi tài liệu

---

## 8. Điều chưa chứng minh — đừng đọc thành đã biết

### 8.1 Nhánh xử lý 429 của CRM **chưa được kiểm chứng**

CRM tự giới hạn ở ~7,3 lượt/phút (hoặc 16,0 nếu production dùng mặc định trong code). Trần
tuyến là `rpm: 15`. Nên **vận hành bình thường sẽ không sinh ra 429**, và nhánh xử lý 429 —
nhánh nhận lỗi bằng **so chuỗi**, thứ dễ hỏng nhất trong cả tích hợp — nằm nguyên đó chưa ai
chạy qua.

Việc ép nó thuộc change `prove-the-crm-path-survives-refusal-and-outage`. Ở change này thì
đây là **lỗ hổng đã biết**, không phải việc đã xong.

### 8.2 Một lượt gọi 81 giây, không tái hiện được

Ngày 09/09 quan sát **một** lượt qua Gateway mất **81 giây** (gọi thẳng Google cùng lúc: 1,4
giây). Ba lượt sau đó 1,1 / 2,3 / 0,86 giây. Sau khi dựng lại container thì lượt đầu chỉ 0,80
giây. **Không tái hiện được, nguyên nhân chưa biết.**

Tôi từng viết là "khởi động lạnh sau khi restart Gateway tốn ~80 giây". **Câu đó sai** và đã
rút lại — phép đo sau `--force-recreate` cho 0,80 giây. Timeout 300 giây đặt trong nhánh mới
là **đề phòng**, không phải vì đã hiểu nguyên nhân.

### 8.3 Chưa đối chiếu kết quả phân loại của hai nhánh

Không có khoá Google nào ở đây gọi được `gemini-2.5-flash` trên nhánh cũ, nên chưa chạy được
cùng một đầu vào qua hai đường để so kết quả. `temperature` là `0,0` nên phép so này **có
nghĩa** — không thể bỏ qua bằng câu "LLM vốn không tất định".

### 8.4 `MIN_INTERVAL_S` production là bao nhiêu — chưa biết

Chưa hỏi được nhóm CRM. `.env.example` ghi `7.5`, code mặc định `3.5`. **Không** điền con số
của `.env.example` rồi coi như đã biết.

### 8.5 Lệch 4 dòng `dim_metric_alias` — có từ trước, để đó

Chạy `gen_catalog.py` kéo theo 4 dòng `dim_metric_alias` không liên quan
(`generate_content_free_tier_*`), sinh ra từ dữ liệu trong `data/` đã mới hơn lần sinh danh
mục trước. Chúng **có trong file, KHÔNG có trong database đang chạy**, vì `02_catalog.sql` chỉ
được áp khi dựng lại toàn bộ (`connect.py:239`). Lệch này có từ trước; chạy lại chỉ làm nó
hiện ra. Người dùng chốt: để đó.

---

## 9. Hoá đơn: tách được, nhưng số cũ và số mới không nối liền

Tiền của CRM sẽ rời khỏi project cũ và sang project riêng mới. Khả năng **tách hoá đơn theo
agent vẫn giữ** — project mới là project riêng của CRM, nên vẫn có nguồn đối chiếu độc lập
với sổ Gateway.

Nhưng **số cũ và số mới không nối liền**: đổi project là đổi đơn vị tính hoá đơn, nên chuỗi
thời gian của agent 7 sẽ có một điểm gãy tại ngày chuyển. `dim_agent.gcp_project_id` của agent
7 hôm nay ghi `crm-500509`, và giá trị đó thành **sai** kể từ ngày chuyển.

Đáng nói thêm: `fact_call` **cố ý không** cập nhật cả hàng khi upsert, và không đưa `model_id`
vào phần cập nhật. Lý do ghi trong `db/rules.py`: nếu mai kia một khâu ánh xạ đổi thì **không
muốn lịch sử bị viết lại im lặng**. Cùng tinh thần đó, đổi `gcp_project_id` là việc phải quyết
tường minh, không phải sửa lặng.
