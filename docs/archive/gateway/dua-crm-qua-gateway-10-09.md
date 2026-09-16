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
  gemini/gemini-2.5-flash`, khoá bằng `api_key: os.environ/KEY_BENCH_CRM_TEST_GG_AIA_STU`, `api_base:
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
- `docker-compose.yml` — truyền `KEY_BENCH_CRM_TEST_GG_AIA_STU` vào khối `x-litellm`
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

## 7. Chín việc đáng báo lại nhóm CRM

1. **`GEMINI_BATCH_SIZE=40` không có tác dụng.** `.env.example` khuyến nghị `40`, nhưng
   `config.py:32` là `min(25, ...)` nên bị cắt xuống 25 **mà không báo**. Ai đọc
   `.env.example` sẽ tin lô là 40
2. **`config.CKPT_JSON` là cấu hình chết, và cả mục cứu hộ dựng trên nó cũng chết.** Khai ở
   `config.py:25` (`llm_fills_checkpoint.json`) nhưng **không nơi nào trong `src/` đọc hay ghi
   nó**. Điểm lưu thật là `save_history_db_atomic` ghi `classified_history_db.json` sau mỗi lô
   (`pipeline.py:688`).

   Đo lại ngày 10/09 thì việc này nặng hơn một dòng cấu hình bỏ quên:

   - **Bảy chỗ trong `tests/test_automation.py` gán `config.CKPT_JSON`** (dòng 120, 202, 310,
     387, 466, 541, 633) và **không chỗ nào đọc lại**. Nên bộ test làm nó *trông như* còn sống:
     ai đọc test sẽ tin đây là đường cứu hộ có người canh
   - **Mục `11.2 Step 3 Bị Crash Giữa Chừng` của `docs/HANDOVER.md` không làm theo được.** Nó
     mở đầu bằng câu **"Không mất dữ liệu! Hệ thống có checkpoint"**, rồi bảo người vận hành
     `type output\llm_fills_checkpoint.json` để xem đã xử lý bao nhiêu, và
     `python run_pipeline.py 3` để chạy tiếp. Cả ba đều không tồn tại: file không ai ghi,
     **`run_pipeline.py` và `step3_call_llm.py` không có trong repo** (`src/` chỉ có
     `pipeline.py`, `classifier.py`, `config.py`, `db_init.py`, `llm.py`, `notification.py`,
     `sharepoint.py`)
   - Cùng cái tên đó còn được dặn ở ba chỗ khác — dòng 360, 584, 800 — trong đó dòng 584 và
     800 bảo `del` file để chạy lại từ đầu. Lệnh đó **không có tác dụng gì**, mà người chạy lại
     tưởng mình đã xoá trạng thái cũ

   Hệ quả thật: pipeline hỏng giữa lô, người vận hành làm đúng tài liệu, và tin là đã dọn sạch
   trong khi trạng thái cũ vẫn nằm nguyên trong `classified_history_db.json`
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

5. **Nhánh 429 ngủ 30 giây cho một lần thử lại không bao giờ xảy ra.** Đây là lỗi lệch giữa
   hai nhánh trong cùng một vòng, `src/llm.py:283-291`:

   ```python
   for attempt in range(1, max_retry + 1):          # max_retry = 3 -> 1, 2, 3
       ...
       if "429" in low or ...:
           wait = min(120, 10 * attempt) + random.random() * 2
           time.sleep(wait)
           continue                                  # <-- KHONG co chot
       if attempt < max_retry:                       # <-- nhanh chung CO chot
           time.sleep(4.0 * attempt)
           continue
       raise RuntimeError(...)
   ```

   Nhánh chung có chốt `if attempt < max_retry` nên tới lượt 3 là ném lỗi ngay, không ngủ.
   Nhánh 429 **không có chốt đó**: lượt 3 vẫn ngủ `30` giây (cộng ≤2s ngẫu nhiên) rồi `continue`,
   `range` hết, và rơi xuống `raise` ở sau vòng. Không có lượt 4 nào để chờ.

   Giá phải trả: **mỗi lần 429 dứt điểm tốn thêm 30-32 giây ngủ vô ích**. Với lô 25 dòng thì
   đây là 30 giây thêm vào trước khi lô đó được báo hỏng. Sửa bằng cách đưa `continue` của
   nhánh 429 vào trong cùng một chốt `attempt < max_retry`.

   Kèm theo, hai nhánh ném ra **hai câu lỗi khác nhau**, và đây là thứ dùng được:

   | nhánh | câu lỗi cuối |
   |---|---|
   | 429 | `Failed calling Gemini API due to exhausted retries.` |
   | chung | `Failed calling Gemini API after 3 retries. Error: ...` |

   Câu lỗi phân biệt được hai nhánh **mà không cần bấm giờ**, nên nó là mốc đối chiếu độc lập
   cho phép đo của change `prove-the-crm-path-survives-refusal-and-outage`

6. **NẶNG NHẤT — `max_output_tokens = 8192` bị token suy nghĩ ăn hết 96%, và cả lô bị cắt cụt
   trong im lặng.** Đo ngày 10/09 trên **dữ liệu thật**, câu nhắc production đầy đủ, 5 bản ghi
   một lô, đi qua Gateway tới `gemini-2.5-flash`:

   | | |
   |---|---|
   | token vào | 5.189 |
   | token ra | **8.178** trên trần **8.192** — chạm trần, thiếu đúng 14 |
   | trong đó **suy nghĩ** | **7.860, tức 96%** |
   | còn lại cho câu trả lời | **318, tức 4%** |
   | gửi đi | **5** bản ghi |
   | nhận về | **1** bản ghi |
   | có báo lỗi không | **không** |

   Chuỗi che lỗi có **bốn tầng**, mỗi tầng giấu thêm một ít:

   ```
   1. gemini-2.5-flash bat suy nghi MAC DINH, va suy nghi an chung ngan sach
      max_output_tokens voi cau tra loi   ->  JSON bi cat cut giua chung
   2. _parse_llm_json goi json_repair (CO trong image)  ->  va lai duoc 1 object
   3. Va thanh cong nen KHONG ghi failed_llm_response.txt, KHONG canh bao
   4. call_llm_batch tra ve binh thuong, khong nem loi
   ```

   Chỉ vòng thử lại trong `pipeline.py` mới đếm được thiếu item, và nó sẽ **thử lại 4 bản ghi
   kia với cùng ngân sách**, tức nhiều khả năng đâm vào đúng bức tường đó lần nữa. Lô production
   là **25** bản ghi chứ không phải 5, nên tỷ lệ hụt sẽ tệ hơn hẳn.

   **ĐÃ SỬA VÀ ĐÃ CHỨNG MINH — 10/09, sau khi anh Tuấn hỏi lại lead.**

   Trước hết phải đính chính một điều đang được hiểu sai. Câu hỏi đặt ra là *"quota thinking có
   tính chung với input không"*, và câu trả lời nhận được là *"nó tính vào rồi, không phải thêm"*.
   **Vế "không phải thêm" đúng, nhưng nó tính vào OUTPUT chứ không phải input.** Đo ba lượt cùng
   một câu nhắc, khác nhau đúng một tham số:

   | cách gọi | vào | ra | suy nghĩ | chữ |
   |---|---|---|---|---|
   | mặc định | 19 | 296 | 285 | 11 |
   | `reasoning_effort: "disable"` | 19 | **107** | **không có** | 107 |
   | `thinking: {"type":"disabled"}` | 19 | 296 | 285 | 11 |

   Cột **vào đứng yên ở 19 cả ba lượt**. Chỗ này quan trọng vì hai lẽ: token ra **đắt hơn token
   vào khoảng 8 lần**, và nó ăn vào `max_output_tokens` — đúng thứ làm cả lô bị cắt cụt.
   Dòng thứ ba là một cái bẫy phải nhớ: `thinking: {"type":"disabled"}` bị `drop_params: true`
   **bỏ im lặng**, số token y hệt lúc không khai gì. Chỉ `reasoning_effort` mới ăn.

   **Sửa ở TUYẾN GATEWAY, không sửa repo CRM.** Thêm `reasoning_effort: "disable"` vào
   `litellm_params` của tuyến `gemini-2.5-flash`. Cách này không phải đụng code của nhóm khác, và
   nó áp cho mọi lượt gọi của CRM mà agent không cần khai gì.

   **Đo lại đúng phép thử cũ, cùng 5 bản ghi, cùng câu nhắc — `prompt_tokens` bằng nhau tuyệt đối
   ở cả hai lượt nên đây là phép so sạch:**

   | | suy nghĩ BẬT | suy nghĩ TẮT |
   |---|---|---|
   | token vào | 5.189 | 5.189 |
   | token ra | **8.178** (chạm trần 8.192) | **2.031** |
   | trong đó suy nghĩ | 7.860 | **0** |
   | trong đó chữ | 318 | **2.031** |
   | thời gian | 42,6 s | **20,3 s** |
   | tiền một lượt | $0,022002 | **$0,006634** |
   | gửi 5 bản ghi, nhận về | **1** | **5** |
   | số cột LLM điền được | — | **57** |

   Rẻ hơn **3,3 lần**, nhanh hơn **2,1 lần**, và phần chữ thật tăng **6,4 lần**. Số cột mà file có
   còn ta không có tụt từ **26 xuống 7**.

   **Một tác dụng phụ ngoài dự tính, và nó tốt:** hai cột ngày nay ra **đúng** `dd/mm/yyyy` như câu
   nhắc bắt buộc — `01/01/2026`, `01/04/2026`, `15/10/2026` — trong khi giá trị cũ trong file là
   `01/01/26`, `01/04/26`, `15/10/26`. Nên các dòng lệch ở cột ngày là **ta đúng, file sai** (xem
   ý 8). Suy luận bật không làm model tuân thủ định dạng tốt hơn; ở đây nó còn kém hơn.

   **ĐÃ ĐO LÔ 25 — TẮT SUY NGHĨ LÀ CẦN, NHƯNG CHƯA ĐỦ.** Chạy đúng cỡ lô production:

   | lô | vào | ra | suy nghĩ | chữ | gửi → nhận |
   |---|---|---|---|---|---|
   | 5 bản ghi | 5.189 | 2.031 | 0 | 2.031 | 5 → **5** |
   | 25 bản ghi | 10.271 | **8.177** (trần 8.192) | 0 | 8.177 | 25 → **20** |

   Suy nghĩ đã về `0` và toàn bộ ngân sách nay dành cho câu trả lời thật. Nhưng **25 bản ghi cần
   nhiều hơn `8.192` token**, nên nó lại chạm trần và mất 5 bản ghi cuối.

   **Con số dùng được ngay, và hai cách đo độc lập cho ra gần bằng nhau:**

   ```
     lo 5  :  2.031 / 5  = 406,2 token ra moi ban ghi
     lo 25 :  8.177 / 20 = 408,9 token ra moi ban ghi   <- 20 la so ban ghi THUC su tra ve
   ```

   Lấy tròn **~407 token ra cho mỗi bản ghi**. Từ đó:

   ```
     so ban ghi toi da lot vao 8.192 token  =  8.192 / 407  ≈  20,1
   ```

   **Con số `20,1` này giải thích đúng quan sát `20`**, nên đây là mô hình mô tả được thực tế chứ
   không phải trùng hợp.

   **Hai đường sửa, phải chọn một:**

   1. **Nâng `max_output_tokens`.** `call_llm_batch` (`llm.py:274`) ghi cứng `8192`.
      `gemini-2.5-flash` cho tới `65.536` token ra. Đặt `12.000` là đủ chỗ cho lô 25 kèm biên an
      toàn. Đây là cách tốt hơn, nhưng **phải sửa repo CRM** — và đó là chỗ duy nhất đặt giá trị
      này; không có biến môi trường nào chỉnh được.

      > **ĐÃ THỬ ĐƯỜNG TRÁNH VÀ ĐƯỜNG ĐÓ KHÔNG ĐI ĐƯỢC.** Câu hỏi tự nhiên là: có đặt được ở
      > tuyến Gateway để khỏi đụng repo của nhóm khác không, giống cách đã làm với
      > `reasoning_effort`? **Không.**
      > Thêm `max_tokens: 12000` vào `litellm_params` của tuyến rồi chạy lại đúng lô 25:
      >
      > ```
      >   khong khai o tuyen :  ra = 8.177,  25 -> 20 ban ghi
      >   khai 12000 o tuyen :  ra = 8.177,  25 -> 19 ban ghi
      > ```
      >
      > Token ra **y hệt**, vẫn dừng ở trần `8.192`. Tham số client tự khai **thắng** mặc định
      > của tuyến.
      > Lý do khác với `reasoning_effort` nằm ở chỗ: CRM **không bao giờ gửi** `reasoning_effort`,
      > nên tuyến điền vào chỗ trống. Còn `max_tokens` thì CRM **có gửi** — lớp đứng thay Gateway
      > đọc `max_output_tokens` (`llm.py:50`) rồi đặt thẳng vào `body["max_tokens"]`
      > (`llm.py:72-73`) ở mọi lượt gọi.
      > **Quy tắc rút ra, dùng được cho mọi tuyến sau này:** tuyến Gateway chỉ đặt được những tham
      > số mà agent **không** gửi. Tham số agent có gửi thì phải sửa ở agent.

      **ĐÃ THỬ `12000` VÀ NÓ GIẢI QUYẾT ĐƯỢC.** Thử mà **không sửa file trong repo CRM**: chép
      `llm.py` ra ngoài, đổi đúng một dòng ở bản chép, rồi mount đè vào container. File gốc của
      nhóm CRM không bị chạm.

      Ba lượt cùng cỡ lô **25**, cùng `10.271` token vào nên so được trực tiếp:

      | lượt | cấu hình | token ra | gửi → nhận | giây | tiền |
      |---|---|---|---|---|---|
      | 09:20 | `8192`, tuyến không khai | 8.177 (chạm trần) | 25 → **20** | 40,0 | $0,023524 |
      | 09:30 | `8192`, tuyến khai `12000` | 8.192 (chạm trần) | 25 → **19** | 23,5 | $0,023561 |
      | 09:44 | **`12000` trong code CRM** | **11.020** | 25 → **25** | 50,0 | $0,030631 |

      Lượt cuối **không chạm trần** — nó dừng vì viết xong, không phải vì hết chỗ. Đây là lần đầu
      một lô cỡ production trả về đủ.

      **Nhưng biên an toàn mỏng, và phải nói rõ.** Dùng `11.020` trên trần `12.000` chỉ còn **8%**
      chỗ thừa. Đo lại theo lô đủ thì mỗi bản ghi tốn `11.020 / 25 = 440,8` token ra, **cao hơn**
      con số `407` ước từ các lô bị cắt cụt — vì lô cụt không đếm được phần bản ghi dở dang. Lấy
      `440,8` làm chuẩn thì lô 25 cần `11.020`, và chỉ cần vài bản ghi dài hơn trung bình là tràn
      tiếp. **Đề nghị đặt `16.000` chứ không phải `12.000`**; model cho tới `65.536` nên chỗ thừa
      không tốn gì — chỉ token thực sinh mới bị tính tiền.

      **Giá mỗi bản ghi, tính cho đủ:**

      ```
        suy nghi BAT, lo 5  : $0,022002 / 5  = $0,0044   moi ban ghi
        suy nghi TAT, lo 25 : $0,030631 / 25 = $0,001225 moi ban ghi
      ```

      Rẻ hơn **3,6 lần** mỗi bản ghi, và đó là so **sau khi** đã tính cả phần token ra tăng lên do
      nay viết đủ 25 bản ghi thay vì 20.
   2. **Hạ cỡ lô xuống 18.** Không phải sửa code, chỉ đặt `GEMINI_BATCH_SIZE=18` trong `.env`.
      Đổi lại là số lượt gọi tăng, và mỗi lượt vẫn phải trả lại **toàn bộ** câu nhắc `10.181` ký
      tự, nên tổng token vào sẽ tăng theo.

   **Nối với ý 1 của mục này:** ý đó ghi `GEMINI_BATCH_SIZE=40` bị `min(25, ...)` cắt xuống 25 mà
   không báo. Nay biết thêm rằng **chính con số 25 cũng đã quá lớn**. Cái chốt `min(25, ...)` được
   đặt ra để chặn lô quá to, nhưng nó chặn ở một mức vẫn tràn.

   **Và phải biết cái giá của việc tràn:** vòng thử lại trong `pipeline.py` sẽ gọi lại 5 bản ghi
   thiếu, mà mỗi lượt gọi đều phải gửi lại **toàn bộ** câu nhắc. Nên một lô tràn tốn gần gấp đôi
   token vào so với một lô vừa khít.

7. **Câu nhắc hứa `allowed` và `locked_labels`, code KHÔNG BAO GIỜ gửi.** Câu nhắc ghi rõ ở mục
   RÀNG BUỘC TAXONOMY: *"Với mỗi cột trong missing_cols, bạn sẽ được cung cấp danh sách
   allowed[cột] trong item."* Đã tìm bằng máy: chuỗi `allowed` và `locked` **không xuất hiện ở
   bất kỳ đâu trong `src/`**. Payload thật (`pipeline.py:582`) chỉ có 5 trường văn bản,
   `row_idx` và `missing_cols`.
   Hệ quả: ràng buộc taxonomy chỉ còn dựa vào **danh sách tĩnh viết trong thân câu nhắc**. Và
   lúc ghép kết quả về (`pipeline.py:670`), code làm `fills[col] = str(val).strip()` — **không
   kiểm giá trị có nằm trong danh sách hợp lệ hay không**.
   **Tin tốt, đã đo:** quét toàn bộ 298 dòng có nội dung, **không có một tag bịa nào** trong 14
   cột phân loại. Chỉ 1 giá trị ngoài danh sách, ở cột hãng đối thủ: `'Kimin'` — nhiều khả năng
   là hãng thật mà bảng từ khoá còn thiếu, không phải model bịa. Nên đây là **rủi ro chưa nổ**,
   không phải thiệt hại đã xảy ra.

8. **Hai cột ngày sai định dạng ở 100% số ô.** Câu nhắc ghi `FORMAT BẮT BUỘC: dd/mm/yyyy`.
   Thực tế trong file: `01/10/25`, `01/09/25`, `01/04/26`, `15/10/26`… — **9 trên 9 ô** dùng năm
   2 chữ số. Không ô nào đúng định dạng bắt buộc.
   Đáng chú ý là tầng từ khoá **không đụng** hai cột này: `load_and_index_keywords` loại chúng
   vì danh sách từ khoá rỗng, nên chúng **hoàn toàn do LLM sinh ra**. Ai đọc `dd/mm/yy` rồi
   parse bằng `%d/%m/%Y` sẽ hỏng.

9. **Tầng từ khoá gánh ít hơn tên gọi gợi ra rất nhiều.** Câu nhắc mở đầu bằng *"Chỉ xử lý các ô
   keyword đánh dấu mơ hồ hoặc trống"*, nghe như LLM chỉ vá chỗ trống. Đo trên **cả 220 bản ghi
   có dữ liệu**:

   | | |
   |---|---|
   | cột từ khoá tự chốt | 349 |
   | cột phải nhờ LLM | **2.731** |
   | LLM gánh | **88,7%** |
   | trung bình từ khoá chốt được | **1,59 / 14 cột** |
   | bản ghi từ khoá chốt được 0 cột | **63, tức 28,6%** |

   Nên đây **không** phải hệ thống từ khoá có LLM vá lỗ. Đây là hệ thống LLM có vài luật từ khoá
   chặn trước. Điều đó đổi hẳn cách đánh giá rủi ro và cách đọc hoá đơn.

---

## 7b. Rà soát lại chính code ta sắp bàn giao — 10/09

Mục 7 nói về code **của nhóm CRM**. Mục này soi **code của chính ta**: 133 dòng thêm vào
`src/llm.py` (`_GatewayResponse`, `_GatewayModels`, `_GatewayClient`, `init_llm_client` viết lại).
Đây là thứ sắp giao cho người khác nên không được để lỗi ẩn.

### Ba nghi ngờ đọc bằng mắt, cả ba đều LOẠI được bằng máy

| Nghi ngờ | Kiểm | Kết quả |
|---|---|---|
| `httpx`, `os` chưa import | đọc `llm.py:1-9` | có ở đầu file, **không phải lỗi** |
| `config.API_KEY` lấy từ biến khác → gửi nhầm khoá Google làm Bearer | `config.py:28` | `API_KEY = os.getenv("GEMINI_API_KEY")`, **cùng một biến**, không có rủi ro |
| Có bí mật lọt vào file thay đổi | quét 5 mẫu khoá trên `llm.py` và `docker-compose.override.yml` | **0 kết quả**; `.env` và `sa-key.json` đều bị `.gitignore` chặn |

### LỖI THẬT tìm được: không kiểm `finish_reason`

`_GatewayModels.generate_content` đọc `d["choices"][0]["message"]["content"]` rồi trả về ngay. Nó
**vứt bỏ `finish_reason`** — đúng cái trường nói rằng phản hồi chưa viết xong. Bản gốc có **0** lần
nhắc tới `finish_reason`.

Đo cho thấy trường này phân biệt sạch:

```
   max_tokens du   ->  finish_reason = "stop"
   max_tokens thieu ->  finish_reason = "length"
```

Hậu quả **đo được trên lô 25 thật**, không phải suy luận:

```
   gui 25 dong  ->  cham tran 8.192 token ra
                ->  JSON cut, nhung van con mot ']' o cuoi (vi tri 23.046/23.079)
                ->  _parse_llm_json goi json_repair, va lai duoc mot mang NGAN HON
                ->  tra ve 19 dong, KHONG loi, KHONG log
```

**Một chi tiết làm nó khó phát hiện hơn nữa:** bản ghi cuối trong 19 dòng đó có **13 fills**, cao
hơn mức trung bình **11,4** của các bản ghi trước. Nghĩa là `json_repair` cắt **gọn ở ranh giới
object**, không để lại bản ghi dở dang. Nên nhìn kết quả thì **không có dấu hiệu nào** cho thấy vừa
mất 6 dòng.

Kèm theo, quét 83 ô có giá trị trong 19 bản ghi đó: **2 ô (2,4%) nằm ngoài danh sách tag hợp lệ** —
`[Kế Hoạch] Kế hoạch lần tới` nhận `'Sản phẩm'` (tag của cột khác), và `[AETT] Đối tượng` nhận
`'chủ nhà'` viết thường trong khi danh sách ghi `'Chủ nhà'` và câu nhắc bắt buộc phân biệt hoa
thường. Nối với ý 7 mục 7: không gửi `allowed`, và lúc ghép cũng không kiểm.

### Bản vá đề nghị, đã thử cả hai chiều

Thêm vào ngay trước `return _GatewayResponse(content)`:

```python
if finish_reason == "length":
    usage = (d.get("usage") or {})
    raise RuntimeError(
        "Gateway tra 200 nhung phan hoi BI CAT CUT (finish_reason=length): "
        "da dung " + str(usage.get("completion_tokens")) + " token ra tren tran "
        + str(max_output_tokens) + ". Ket qua se THIEU dong. "
        "Tang max_output_tokens hoac giam GEMINI_BATCH_SIZE.")
```

Câu lỗi **cố ý không chứa chuỗi `429`**, để nó rơi vào nhánh lùi lịch chung chứ không bị nhận nhầm
là quá hạn mức.

Đã thử bằng cách chép `llm.py` ra ngoài rồi mount đè vào container — **file trong repo CRM không bị
chạm một dòng nào**:

| phép thử | kết quả |
|---|---|
| lô 25, trần `8192` (ép cắt cụt) | ném đúng lỗi: `da dung 8177 token ra tren tran 8192` |
| lô 25, trần `16000` (đủ chỗ) | **25/25 dòng**, không lỗi, `10.534` token ra, 49,3 giây |

Chiều thành công **không** bị bản vá làm hỏng. Hai việc cần giao cho nhóm CRM gộp lại thành một
lần sửa `src/llm.py`: **nâng `max_output_tokens` lên `16000`** và **thêm khối kiểm trên**.

### Hai điều ghi nhận, chưa đủ mức gọi là lỗi

- **`usage` bị vứt bỏ.** Lớp đứng thay không đọc `usage` từ phản hồi, nên CRM không tự ghi được
  token nó tiêu. Không sai, nhưng nghĩa là mọi số liệu chỉ tồn tại ở phía Gateway
- **`httpx.Timeout(300.0)` áp cho cả bốn loại timeout, kể cả `connect`. TÔI ĐÃ LO SAI — đã đo và
  RÚT LẠI.** Câu cũ tôi viết là *"nếu gói tin bị rơi im lặng thì một lượt gọi có thể treo tới 300
  giây"*. Đo bằng chính lớp `_GatewayModels`, bốn kiểu hỏng mạng, không tốn lượt gọi nào:

  | kiểu hỏng | `Timeout(300.0)` | `Timeout(300, connect=5)` | lỗi hệ thống |
  |---|---|---|---|
  | cổng đóng, host còn sống | **0,04**s | — | `ECONNREFUSED` |
  | tên miền không phân giải | **0,09**s | — | DNS |
  | IP `192.0.2.1` (TEST-NET-1) | **21,07**s | 5,01s | `ECONNREFUSED` |
  | IP trong mạng Docker, không ai đáp ARP | **3,11**s | 3,07s | `EHOSTUNREACH` |

  **Lâu nhất đo được là `21,07` giây, không phải 300.** Nhân đây cũng ghi lại một lỗi phương pháp
  của chính tôi: lần thử đầu tôi dùng `192.0.2.1` và gọi nó là "gói tin rơi im lặng", nhưng lỗi trả
  về là `Connection refused` — tức **có thứ gì đó đã trả lời**, nên phép thử đó không dựng đúng
  cảnh cần dựng. Phải đổi sang một địa chỉ nằm trong dải Docker mà không container nào giữ, để ARP
  không ai đáp, mới là im lặng thật. Và cảnh đó lại hỏng **nhanh hơn** (`3,11`s).

  Lý do: hạt nhân hệ điều hành **tự bỏ cuộc trước** trong mọi kiểu hỏng dựng được, nên trần 300 giây
  không bao giờ tới lượt. Tách `connect` xuống 5 giây chỉ ăn thua ở đúng một ô của bảng, và ăn có
  `16` giây. **Không đáng sửa.**

  **Nhưng phần `read` thì khác, và nó vẫn đúng như tác giả đặt:** nếu Gateway nhận kết nối rồi im,
  client sẽ chờ đủ 300 giây. Đó là **cố ý** — một lô 25 dòng mất 40 tới 50 giây, và đã quan sát một
  lượt 81 giây chưa giải thích được (mục 8.2). Không được hạ con số này.

  **Ích lợi mang sang mục 3 của change `prove-the-crm-path-survives-refusal-and-outage`:** khi diễn
  tập dừng `gateway-lb`, CRM sẽ thấy `ECONNREFUSED` trong **0,04 giây**, không phải treo. Nên nhánh
  chạy sẽ là lùi lịch chung `4, 8` giây, KHÔNG phải nhánh 429. Ô 3.1 lo timeout ngắn bị đọc nhầm
  thành treo — theo phép đo này thì lo đó không xảy ra với kiểu hỏng "dừng container"

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
