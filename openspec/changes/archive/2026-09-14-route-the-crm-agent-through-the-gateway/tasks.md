## 1. Xin thông tin từ bên ngoài — chặn mọi việc sau

- [x] 1.1 **Xong 10/09 — project id là `crm-test-508114`, và service account JSON đã có.**
      Anh Tuấn tạo project và tải service account về. File nằm ở `D:\RangDonk\CRM-Classification-Pipeline\sa-key.json`, service account là `vertex-express@crm-test-508114.iam.gserviceaccount.com`, quyền **Vertex AI User**. Đã kiểm bằng máy: JSON hợp lệ, đủ 6 trường bắt buộc, khoá riêng đúng định dạng. **Không in giá trị khoá ra bất kỳ đâu.**
      **ĐÃ NGHIỆM THU BẰNG MỘT LƯỢT GỌI THẬT**, qua đúng hàm `init_llm_client()` của CRM: in ra `>>> Using Google Vertex AI client...`, `vertexai=True`, `project=crm-test-508114`, trả về **200** và JSON hợp lệ. Nghĩa là nhánh Vertex của CRM **hết rơi ngược về AI Studio**.
      **HAI ĐIỀU PHẢI GHI KÈM, KHÔNG ĐƯỢC BỎ:**
      · `crm-test-508114` là **project THỬ**, anh Tuấn tạo để chạy thông luồng trên máy local, **không phải** project số `60854134008` ghi trong nhật ký cũ. Anh Tuấn đã chốt: hoá đơn lệch không sao vì đang chạy local. Nhưng khi nào đưa lên chạy thật thì **phải xem lại ô này**, và `dim_agent.gcp_project_id` của agent 7 vẫn giữ `crm-500509` (xem ô 8.3) nên hiện có **ba** project id khác nhau trong cùng câu chuyện. Ai đọc sau phải biết đủ ba.
      · Trước khi có file, mã **âm thầm** rơi về AI Studio: điều kiện là `use_vertex and sa_key_path.exists()`, mà `.env.example` đặt sẵn `USE_VERTEX=True`, nên người đọc cấu hình tưởng đang chạy Vertex trong khi thật ra không. Không có cảnh báo nào. Đã báo lại nhóm CRM ở mục 7
- [x] 1.2 **Không còn chặn gì — nhưng phép đo cũ vẫn đúng, chỉ là đo sai đường.** Hai lý do 403 dưới đây là của `generativelanguage.googleapis.com` (AI Studio). Tuyến thật của CRM đi `aiplatform.googleapis.com` (Vertex express) và **không bị chặn** — xem 1.3. Nên **không cần bật** Gemini API trên project, và không cần gỡ giới hạn API của khoá; để nguyên còn hẹp hơn. Việc còn lại thuộc 1.1 (ghi project id), không thuộc task này. **SỬA MỘT CHỖ GHI SAI (10/09) — khoá này là VERTEX EXPRESS, không phải AI Studio.**
      Bản trước của chính ô này ghi `KEY_BENCH_CRM_TEST` là "khoá AI Studio". Sai, và cái sai đó
      đã đẻ ra một kết luận sai to hơn ở ô 7.6 ("không có khoá nào ở đây gọi được model"). Đo lại
      cho thấy hành vi **ngược hẳn** với một khoá AI Studio:
      · `aiplatform.googleapis.com` (Vertex) → **200**, trả nội dung thật
      · `generativelanguage.googleapis.com` (AI Studio) → **403**
      Khoá AI Studio thì đúng hai chiều ngược lại. Tiền tố cũng khớp: khoá AI Studio dạng `AIza`,
      còn `AQ.` là dạng của Vertex express.
      Nên hai lý do 403 bên dưới đọc lại thành một câu đơn giản: **đang gửi khoá Vertex sang một
      sản phẩm không phải Vertex**, trên project mà sản phẩm đó cũng chưa bật. Không phải "khoá
      hỏng", cũng không phải "project thiếu quyền".
      Hệ quả thực tế: **không có gì phải sửa trong console.** Cả hai chỗ chặn chỉ nằm trên tuyến
      AI Studio, mà production không dùng tuyến đó. Giới hạn API đặt trên khoá là cấu hình ĐÚNG và
      an toàn — không được nới ra chỉ để chạy một phép so.
      Nguyên văn phép đo cũ (giữ lại để đối chiếu, kể cả phần nhãn sai): Bật API trên project đó. **Đo 09/09, chưa bật**: khoá `KEY_BENCH_CRM_TEST` (dạng `AQ.`, 53 ký tự — ~~khoá AI Studio~~ **thật ra là Vertex express**, **không phải** service account) trả 403 cho mọi model trên project `60854134008`, với **hai** lý do khác nhau:
  - `SERVICE_DISABLED` — Gemini API chưa bật trên project, kèm link kích hoạt
  - `API_KEY_SERVICE_BLOCKED` — bản thân khoá có **giới hạn API** chặn `generativelanguage.googleapis.com`
  Hai lý do này **đảo chỗ giữa các lượt chạy cho cùng một model** (`gemini-2.5-flash` ra lý do A ở lượt 1, lý do B ở lượt 2), nên chúng không phải thuộc tính của model — và không thể biết cả hai đều thật hay một cái che cái kia. Phải sửa cả hai rồi đo lại
- [x] 1.3 **Đạt — Vertex CÓ phục vụ `gemini-2.5-flash` với khoá này.** Đo bằng đúng thứ task này yêu cầu: **một lượt `generateContent` thật**, không dùng endpoint metadata. Đi qua tuyến `api_base: https://aiplatform.googleapis.com/v1/publishers/google` (tức `aiplatform`, KHÔNG phải `generativelanguage`) → **200**, nội dung thật, 0,80 giây; và đo lại 10/09 hai lượt nữa, 200 cả hai. Nên câu hỏi của 1.2 và 1.3 tách hẳn nhau: **AI Studio bị chặn, Vertex thì không**. Ghi chú gốc: **CHẶN bởi 1.2** — không đo được gì về model khi mọi lượt gọi bị chặn ở tầng project/khoá. Phép kiểm ngược đã xác nhận điều đó: một tên model **bịa ra** cũng trả đúng cùng loại lỗi, nên phép đo hiện chưa phân biệt được model nào có model nào không. **Đo một lượt `generateContent` thật** để biết Vertex có phục vụ `gemini-2.5-flash` hay không. KHÔNG dùng endpoint metadata: đã thử hai đường (`publishers/google/models` và bản project-scoped), cả hai trả **cùng một mã** cho một tên model bịa ra, nên chúng không phân biệt được gì
- [x] 1.4 **Không phải làm — điều kiện không xảy ra.** 1.3 cho kết quả **CÓ**, nên không có gì phải dừng và không có gì phải xin quyết định. Cái bẫy mà task này dựng ra (âm thầm đổi sang model khác) cũng không có cơ hội xảy ra: model chạy được chính là model production `gemini-2.5-flash`. Nguyên văn: Nếu 1.3 cho kết quả **không có** model đó: **DỪNG LẠI, báo, chờ quyết định**. MUST NOT âm thầm đổi sang model khác — đó đúng là cái bẫy Quyết định 2 vừa gỡ
- [x] 1.5 **ĐÓNG BẰNG NHÁNH DỰ PHÒNG CỦA CHÍNH TASK NÀY, KHÔNG PHẢI BẰNG CÂU TRẢ LỜI.** Giá trị production **vẫn chưa biết** và không được coi là đã biết. Nhánh dự phòng ("không có câu trả lời thì ghi là chưa biết") đã làm xong và ghi thành mục riêng: `docs/archive/gateway/dua-crm-qua-gateway-10-09.md` mục **8.4**, nằm trong phần "những điều KHÔNG chứng minh được" chứ không nằm trong phần kết quả.
      Hai con số có thật đều ghi kèm nguồn: `.env.example` cho `7,5s + 1,5s` → **7,3** lượt/phút; mặc định trong code (`src/config.py:30-31`) cho `3,5s + 0,5s` → **16,0** lượt/phút. Không con số nào được chọn làm "nhịp production".
      Cái bẫy mà task này dựng ra đã bật thật một lần và được ghi lại ở mục 2 nhật ký: ghép khoảng cách của `.env.example` với jitter mặc định của code cho ra `7,7` lượt/phút — con số **không ứng với bất kỳ cấu hình thật nào**. Việc còn phải làm khi nào có người của nhóm CRM: sửa mục 8.4, và sửa cả mục 2 nếu con số production khác cả hai.

## 2. Tuyến Vertex trong Gateway

- [x] 2.1 **KHÔNG CẦN NỮA** — đường express dùng API key trong biến môi trường, không có file bí mật nào phải mount. Xem Quyết định 3 đã sửa. Việc còn lại là truyền `KEY_BENCH_CRM_TEST` vào khối `x-litellm`, làm ở 2.2
- [x] 2.2 **Xong** — đã đo qua Gateway: `model_group = gemini-2.5-flash`, `model = gemini/gemini-2.5-flash` (model production thật, không thay thế), 200 trong 0,80 giây. Khai tuyến `model_name: gemini-2.5-flash` → `model: gemini/gemini-2.5-flash`, `api_key: os.environ/KEY_BENCH_CRM_TEST`, `api_base: https://aiplatform.googleapis.com/v1/publishers/google`. **`api_base` phải kết thúc ở `/publishers/google`** vì `_check_custom_proxy` nối thêm `/models/{model}:{endpoint}`. KHÔNG khai `vertex_project`/`vertex_location` — express tự suy. Truyền `KEY_BENCH_CRM_TEST` vào khối `x-litellm`
- [x] 2.3 **Xong**, và đã sửa thêm một bẫy: tuyến `gemini-flash` vẫn mang `tags: ["crm-feedback"]` từ 08/09 (hồi CRM định đi qua đó bằng bí danh). Nay CRM có tuyến riêng nên giữ tag đó sẽ đóng dấu `crm-feedback` lên **bất kỳ** ai gọi `gemini-flash` — kể cả master key không tag — và quy sai vào agent 7. Đã gỡ; tuyến đó nay không mang tag nào. Đặt `tags: ["crm-feedback"]` — **đúng một** tag định danh. MUST NOT thêm tag agent thứ hai vào cùng tuyến: `router.py:3292` trộn mọi tag của tuyến vào metadata, hai tag định danh thì `load_gateway.py:238` không phân giải được
- [x] 2.4 **Xong**. Đặt `rpm: 15`. Giữ con số này dù Vertex trả tiền cho hạn mức cao hơn — người dùng chốt 09/09: giữ điều kiện sát production nhất
- [x] 2.5 **Xong** — và đúng lúc: sau khi khai tuyến thật, `gemini-2.5-flash` vừa là tên nhóm thật vừa là khoá bí danh, tức đúng điều kiện che đã chứng minh ở 4.0. **XOÁ `model_group_alias`** đã thêm 08/09. Đây là sửa lỗi, không phải dọn dẹp — xem 4.1 để kiểm chứng
- [x] 2.6 **Đạt**: `config --quiet` sạch, cả hai instance `healthy`, log nạp đủ 4 tuyến, biến khoá tới được container (53 ký tự)
- [x] 2.7 **Đạt** — không còn file khoá nào để lọt: đường express dùng biến môi trường. `git diff` không chứa giá trị khoá nào; chỉ `docker-compose.yml` và `config.gateway.yaml` bị sửa. Xác nhận file khoá **không** lọt vào git: `git status` sạch và `git check-ignore` xác nhận

## 3. Virtual key cho CRM

- [x] 3.1 **Xong** — `crm-feedback-tagged`, cấp qua `/key/generate` (không INSERT tay vào bảng). Cấp virtual key mang `tags: ["crm-feedback"]`. Việc này **ghi vào database `litellm`** — phải được người dùng cho phép trước
- [x] 3.2 **Đo được: khớp theo TÊN NHÓM.** `models: ["gemini-2.5-flash"]` → gọi `gemini-2.5-flash` ra 200; gọi `gemini-flash-lite` (ngoài danh sách) ra **403** "This key can only access models=['gemini-2.5-flash']"
- [x] 3.3 **Xong**, theo đúng khuôn khoá DMS: `metadata` mang `tags`, `agent`, `cap_ngay`, `muc_dich`. Đặt `key_alias` và `metadata` theo khuôn khoá `dms-feedback-tagged` đang có
- [x] 3.4 **Giữ** — giá trị khoá chỉ nằm ở scratchpad ngoài repo, chưa từng in đầy đủ ra terminal hay ghi vào file nào trong repo. KHÔNG in giá trị khoá ra log, ra terminal, hay vào bất kỳ file nào trong repo

## 4. Kiểm ngược ở tầng Gateway — trước khi đụng vào CRM

- [x] 4.0 **Chứng minh cơ chế bí danh che tuyến thật — làm sớm 09/09, bằng tuyến ĐÃ CÓ, không cần khoá mới.** `gemini-flash-lite` vốn là tuyến thật trỏ `gemini/gemini-3.5-flash-lite`. Thêm bí danh tạm `gemini-flash-lite → gemini-flash`, khởi động lại, gọi `gemini-flash-lite`:
  - **HTTP 200**, `model_group = gemini-flash-lite` (trông đúng), nhưng `model = gemini/gemini-3.6-flash` — **bí danh thắng tuyến thật**
  - Xoá bí danh tạm, gọi lại → `model = gemini/gemini-3.5-flash-lite`. Cả hai chiều đều đo được
  - `git diff --quiet` xác nhận file cấu hình đã về đúng bản đã commit
  - Nên Quyết định 2 không còn là lời đọc code. Và điểm đáng nhớ nhất: cột `model_group` vẫn ghi đúng tên người gọi yêu cầu, nên ai chỉ xem cột đó sẽ **không thấy gì bất thường** — chỉ cột `model` lộ ra

- [x] 4.1 **Đạt — và kết quả KHÁC dự đoán viết trong task này, theo hướng tốt hơn.** Task giả định lặp lại 4.0 trên tuyến Vertex sẽ cho 200 kèm model sai. Đo thật thì **hai tình huống khác nhau**, và chính chỗ khác nhau đó mới là giá trị:

  | cấu hình | mã | `model_group` | `model` trong sổ | token | tiền |
  |---|---|---|---|---|---|
  | bí danh, tuyến `gemini-flash` **không tag** (hôm nay) | **401** | `gemini-2.5-flash` | `gemini-2.5-flash` (tên đã gọi) | 0 | 0 |
  | bí danh + tag `crm-feedback` trên `gemini-flash` (đúng cấu hình **08/09**) | **200** | `gemini-2.5-flash` | **`gemini/gemini-3.6-flash`** | 16 | 5,10e-05 |
  | đã trả cấu hình | **200** | `gemini-2.5-flash` | `gemini/gemini-2.5-flash` | 14 | 3,06e-05 |

  - **Bí danh CÓ ghi đè, đã chứng minh trực tiếp** — không phải suy từ code. Thông báo lỗi của LiteLLM nói thẳng: `Passed model=gemini-flash and tags=['crm-feedback']`, dù người gọi gửi `gemini-2.5-flash`
  - **Hôm nay bí danh KHÔNG gây hỏng im lặng, nó gây 401.** Vì task 2.3 đã gỡ tag `crm-feedback` khỏi tuyến `gemini-flash`, nên request có tag không còn tuyến nào để rơi vào. Đây là **lợi ích thứ hai của 2.3 mà lúc làm không ai tính đến**: nó biến một sai-im-lặng thành một hỏng-to-tiếng
  - **Và hỏng im lặng là THẬT, đo được, chỉ cần trả tag về.** Dựng lại đúng cấu hình 08/09 thì lượt gọi ra **200**, thân phản hồi ghi `model: gemini-2.5-flash` (trông đúng), cột `model_group` ghi `gemini-2.5-flash` (trông đúng), `end_user` đúng `svc.crm-feedback` — **chỉ duy nhất cột `model`** lộ ra `gemini/gemini-3.6-flash`. Đúng kết luận của 4.0, nay xác nhận trên tuyến của chính CRM
  - **Chênh giá đo được, không phải ước lượng.** Từ hai lượt trên: model sai `3,1875e-06` USD/token, model đúng `2,1857e-06` USD/token → **đắt hơn 1,46 lần**. Con số `1,59` trong design là ước lượng theo tỷ lệ vào/ra thật của CRM; `1,46` là đo trên tỷ lệ của chính hai lượt này. Hai con số không xung đột, chúng đo hai tỷ lệ vào/ra khác nhau
  - **Đã trả cấu hình, và xác nhận bằng BĂM chứ không bằng lời.** `sha256` của `config.gateway.yaml` sau khi trả **khớp từng bit** với mốc trước phép đo (`73f6bd9e…`), 0 dấu vết khối tạm, 0 `model_group_alias` trong code thật. Rồi gọi thêm một lượt để xác nhận bằng **phép đo**: sổ ghi `gemini/gemini-2.5-flash`. Lưu ý `git diff --quiet` **không dùng được** ở đây như 4.0 đã dùng, vì file này đang có thay đổi chưa commit hợp lệ — nên mốc so phải là băm, không phải git
  - Task viết là chờ sổ ghi `vertex_ai/gemini-2.5-flash`. **Chuỗi đó sai**, có từ trước khi Quyết định 3 đổi sang express mode; tuyến thật là `gemini/gemini-2.5-flash`. Nguyên văn: Lặp lại 4.0 **trên chính tuyến Vertex**: khai lại bí danh tạm, gọi `gemini-2.5-flash`, xác nhận sổ ghi `gemini-3.6-flash`; xoá bí danh, gọi lại, xác nhận sổ ghi `vertex_ai/gemini-2.5-flash`. 4.0 đã chứng minh **cơ chế**; bước này chứng minh nó đúng với **tuyến cụ thể** của CRM
- [x] 4.2 **Đạt**: 200, `request_tags` mang `crm-feedback`. Và **lọc tag đã được kiểm riêng**: master key (không giới hạn `models`, nên không bị ngắn mạch) mang tag `dms-feedback` gọi tuyến CRM → **401** "Not allowed to access model due to tags configuration"; cùng thế với tag đúng → 200. Nên hai cửa phân biệt được bằng mã: **403 = danh sách `models`**, **401 = lọc tag**
- [x] 4.3 **Đạt, nhưng hỏng theo kiểu khác dự đoán — và đó mới là điều đáng ghi.** Khoá DMS gọi `gemini-2.5-flash` bị chặn bằng **403**, không phải 401, và lý do là **danh sách `models` của khoá** (`This key can only access models=['gemini-flash-lite']`), **không** phải lọc tag. Danh sách `models` chạy TRƯỚC và ngắn mạch, nên phép kiểm này **không hề chạm tới** lọc tag. Đối chiếu: cùng khoá gọi tuyến của nó → 200.
  Hệ quả: muốn thật sự kiểm lọc tag thì cần một khoá có `models` **cho phép** `gemini-2.5-flash` nhưng tag **không khớp**. Chưa làm được vì chưa cấp khoá CRM (task 3.1)
- [x] 4.4 **Đạt** — `fact_call` có dòng gán `agent_id = 7`, dịch vụ `ledger-refresh` tự làm, không chạy lệnh nào. Chờ một chu kỳ `ledger-refresh`
- [x] 4.5 **Đạt**: sổ ghi `model_group = gemini-2.5-flash` và `model = gemini/gemini-2.5-flash`. Xác nhận cột model trong sổ ghi **cả** tên nhóm CRM gọi **và** tên model thật đã phục vụ

## 5. Nhánh `gateway` trong bản clone CRM

- [x] 5.1 **Xong, và nhỏ hơn dự tính.** `call_llm_batch` gọi `client.models.generate_content(...)` rồi đọc `resp.text`, nên tôi làm một **lớp đứng thay** có đúng hình dạng đó (`_GatewayClient` / `_GatewayModels` / `_GatewayResponse`) — `call_llm_batch` **không sửa một dòng**, kể cả vòng thử lại. Diff: 133 thêm, **2 xoá**, và 2 dòng xoá đó chỉ là dòng `def` cùng docstring của `init_llm_client` được thay bằng bản mở rộng. Thêm nhánh `gateway` vào `src/llm.py`. **Dựng** request OpenAI từ `system_prompt` + `batch` — MUST NOT viết lớp dịch giữa hai định dạng: hai đầu vào đó đã trung lập
- [x] 5.2 **Xong**, và bọc cả `r.json()`: 200 mà thân không phải JSON thì `r.json()` ném lỗi chẳng trỏ vào đâu. Nội dung rỗng thì **ném lỗi rõ** chứ không trả chuỗi rỗng — chuỗi rỗng sẽ thành "Could not parse valid JSON array", trỏ vào prompt thay vì chỗ sai thật. Chiều về: đọc `choices[0].message.content`. Lưu ý `getattr(resp, "text", "")` hiện có giá trị mặc định, nên sai hình dạng phản hồi sẽ ra chuỗi rỗng rồi `_parse_llm_json("")` ném "Could not parse valid JSON array" — triệu chứng trỏ vào prompt, không trỏ vào chỗ sai thật
- [x] 5.3 **Xong**: `raise RuntimeError("429 qua han muc tu Gateway: ...")`. Chưa ép 429 để xem CRM lùi nhánh nào — đó là change thứ hai. **Lỗi quá hạn mức phải mang chuỗi `429` trong thông báo.** `llm.py` nhận 429 bằng cách so chuỗi (`"429" in low or "rate limit" in low or "resource_exhausted" in low`); thiếu chữ đó thì CRM rơi vào nhánh lùi chung `time.sleep(4.0 * attempt)` — ngắn hơn nhiều — và dập vào một Gateway vừa xin nó chậm lại
- [x] 5.4 **Xong và đã đo**: harness gửi `model_name = gemini-2.5-flash`, không tiền tố, và Gateway nhận. **Cắt tiền tố `models/`** khỏi tên model. `init_llm_client` tự thêm tiền tố cho nhánh AI Studio và README dặn đặt `GEMINI_MODEL=models/gemini-2.5-flash`; tuyến Gateway là `gemini-2.5-flash` không tiền tố
- [x] 5.5 **Xong**: `httpx.Timeout(300.0)`, bằng nhánh cũ. Đặt timeout tương đương 300 giây mà nhánh cũ đang dùng (`client._api_client._httpx_client.timeout`). Một batch 25 dòng với 8192 token ra không nhanh — **và đo 09/09 cho một lý do thứ hai**: đã quan sát **một** lượt qua Gateway mất **81 giây** (gọi thẳng Google cùng lúc: 1,4 giây), ba lượt sau đó 1,1 / 2,3 / 0,86 giây, và sau khi dựng lại container thì lượt đầu chỉ 0,80 giây — nên **không tái hiện được và nguyên nhân chưa biết**. Timeout rộng ở đây là đề phòng, không phải vì đã hiểu nguyên nhân
- [x] 5.6 **Đạt, đo trong sổ**: dòng của harness có `end_user = svc.crm-feedback`. Đây là **lần đầu** CRM có giá trị ở cột đó — trước nay `usage_by_account` có 0 dòng cho agent 7. Gửi header `X-User: svc.crm-feedback` (account 951, đã có sẵn). Định danh **dịch vụ**, MUST NOT bịa ra một con người
- [x] 5.7 **Xong**: dùng `httpx` đã có sẵn, `requirements.txt` **không đổi**, ảnh không phải build lại vì thêm phụ thuộc. Dùng `httpx` — đã được `src/llm.py` import sẵn, nên **không thêm phụ thuộc, không build lại ảnh**. MUST NOT dùng `openai` SDK: nó không có trong `requirements.txt`
- [x] 5.8 **Đạt, đã đo**: bỏ `GEMINI_BACKEND` ra thì harness in `>>> Using Google AI Studio client...` rồi ném đúng lỗi **cũ** `No GEMINI_API_KEY environment variable found!` tại `llm.py:172` — nhánh mới không chiếm mặc định. Hai nhánh `vertex` và `apikey` **không sửa một dòng**, và mặc định vẫn là chúng. Đường lùi là một biến môi trường
- [x] 5.9 **Xong**: `GEMINI_BACKEND`, `GEMINI_GATEWAY_BASE_URL`, `GEMINI_GATEWAY_USER`, đều `os.environ`; `config.py` không thêm trường nào. Đọc cấu hình từ `os.environ`, không thêm trường vào `config.py` — `config.py` đã `load_dotenv` sẵn
- [x] 5.10 **Đạt**: `git diff` chỉ có 2 dòng xoá, cả hai thuộc `init_llm_client`. `0 dòng` logic phân loại bị sửa. Kiểm bằng `git diff --stat` trong bản clone

## 6. Nối mạng

- [x] 6.1 **Xong**. Tạo `docker-compose.override.yml` trong bản clone CRM, nối `crm-classifier` vào mạng của Gateway
- [x] 6.2 **Đạt, đã kiểm bằng `docker compose config`**: giữ **cả hai** — `default` → `crm-classification-pipeline_default` (mạng của chính CRM) và `gateway` → `token-ledger-dashboard_default` (external). `docker-compose.yml` của CRM **không khai `networks:`** nên mọi service đang dùng mạng `default` ngầm định. Phải liệt kê **cả hai** mạng, không thì service rời khỏi mạng của chính nó. CRM chỉ có một service nên nhẹ hơn DMS, nhưng luật vẫn thế
- [x] 6.3 **Đạt**: harness chạy trong container CRM, nối `--network token-ledger-dashboard_default`, gọi `http://gateway-lb:4000` thành công trong **2,75 giây**. Xác nhận từ trong container CRM gọi được `gateway-lb:4000`
- [x] 6.4 **Giữ** — dùng tên service trong mạng compose, không dùng `host.docker.internal`. KHÔNG dùng `host.docker.internal`: `gateway-lb` cố ý chỉ bind `127.0.0.1`, và chuyện xuyên được vào cổng loopback từ compose project khác thì **chưa ai kiểm**

## 7. Nghiệm thu bằng harness — không chạy cả pipeline

- [x] 7.1 **Xong** — harness đọc dòng thật từ file mẫu, dựng batch **đúng hình dạng** `pipeline.py` dựng (`row_idx` + 5 cột nguồn + `missing_cols`), rồi gọi `init_llm_client()` + `call_llm_batch()`. Viết harness gọi `init_llm_client()` + `call_llm_batch()` với vài dòng lấy từ `sample_data/CRM_merge_sample.xlsx` (6.304 byte, có sẵn trong repo CRM)
- [x] 7.2 **Giữ**: harness không chạm SharePoint, email, Excel. Harness MUST NOT tải/ghi SharePoint, MUST NOT gửi email, MUST NOT ghi Excel. Lý do phải làm thế: pipeline **không có cờ dry-run nào** — không `skip_upload`, không `skip_email`, không `DISABLE_*` — nên bật container là tải SharePoint thật + gọi LLM 5–60 phút + ghi lại SharePoint thật + gửi email cho người thật
- [x] 7.3 **Đạt** — xem 5.8. Không hoàn tất được một lượt gọi trên nhánh cũ vì không có khoá Google nào ở đây gọi được `gemini-2.5-flash`; nhưng điều cần chứng minh (mặc định không bị chiếm) thì đã chứng minh. Chạy harness với `GEMINI_BACKEND` mặc định (nhánh cũ) → xác nhận vẫn chạy, chứng minh không phá gì. Đặt timeout **trên 90 giây** vì đã quan sát một lượt 81 giây (chưa tái hiện được, chưa rõ nguyên nhân) — đề phòng, không phải đã hiểu
- [x] 7.4 **Đạt**: prompt thật 10.181 ký tự, 2 dòng mẫu, **2,75 giây**, trả về 2 phần tử, JSON phân tích được bằng **chính `_parse_llm_json` của CRM**. Sổ ghi `model = gemini/gemini-2.5-flash`, `model_group = gemini-2.5-flash`, 4.009 token, `end_user = svc.crm-feedback`, tag `crm-feedback`. Chạy harness với nhánh `gateway` → 200, JSON phân tích được, và dòng sổ mang `crm-feedback`
- [x] 7.5 **Đạt — đo hai tầng, cả hai đều dương.** `response_format` có thể bị `drop_params: true` bỏ **mà không báo**; `_parse_llm_json` phòng thủ đủ để vẫn chạy, nên phải kiểm trực tiếp chứ không suy từ "kết quả vẫn đúng".
  - **Tầng cơ chế (không gọi mạng, không tốn tiền).** Gọi đúng hàm mà router gọi, `litellm.utils.get_optional_params`, với `custom_llm_provider="gemini"` và `drop_params=True` — tức đúng cấu hình đang chạy. `response_format` **có** trong danh sách tham số được hỗ trợ, nên `drop_params` không đụng tới nó. Không khai → `{}`; có khai → `{"response_mime_type": "application/json"}`, đúng trường chế độ JSON của Google. LiteLLM `1.99.0`
  - **Tầng đầu-cuối (qua tuyến thật, khoá thật của CRM).** Hai lượt gọi giống hệt nhau trừ `response_format`, cùng `temperature: 0.0`, cùng câu nhắc chọn sao cho câu trả lời **tự nhiên là văn xuôi**: `Reply with the single word hello. No punctuation, no explanation, no quotes, no formatting.`

    | | nội dung trả về | `json.loads` |
    |---|---|---|
    | A. không khai | `hello` | thất bại |
    | B. có khai | `"hello"` | thành công |

    Google **đã ép** thân phản hồi thành JSON hợp lệ. Lượt A là phép đối chứng: cùng câu nhắc, cùng nhiệt độ, cùng tuyến, chỉ khác một tham số — nên chênh lệch này quy được về đúng `response_format`, không quy về tính ngẫu nhiên của model
  - **Việc này ĐÃ ĐƯỢC ĐO MỘT LẦN RỒI, và tôi không tra trước khi đo lại.** `docs/archive/gateway/dua-dms-qua-gateway-31-08.md` mục 4.4 đã kết luận đúng câu này cho DMS — *"`drop_params: true` KHÔNG nuốt `response_format`"* — bằng **đúng** phương pháp chênh lệch trên, với câu nhắc `Thu do cua Viet Nam la thanh pho nao` (tắt → văn xuôi, bật → `{"thu_do": "Ha Noi"}`). Lẽ ra tôi phải đọc nhật ký cũ trước khi dựng phép đo. Phần **thật sự mới** ở đây chỉ có hai điều: phép đo chạy trên **tuyến Vertex express của CRM** chứ không phải tuyến AI Studio của DMS, và **tầng cơ chế** (`get_optional_params`) chỉ ra được *vì sao* tham số sống sót, chứ không chỉ ra rằng nó sống sót
  - **Vì sao phải đo chênh lệch chứ không đo một lượt.** Nếu chỉ chạy lượt B rồi thấy JSON hợp lệ thì không kết luận được gì: model vẫn hay tự trả JSON khi được nhắc, và `_parse_llm_json` còn vá được cả JSON hỏng. Chỉ có lượt A trả `hello` trần mới cho lượt B ý nghĩa
- [ ] 7.6 **CHƯA LÀM — người dùng chốt 14/09/2026: ghi lại là chưa làm, chuyển sang một change riêng, rồi archive change này.** Phép so đầu ra của hai nhánh trên cùng đầu vào **chưa từng chạy**. Đừng đọc việc change đã archive thành "hai nhánh cho cùng kết quả". Điều đã đo được chỉ là thân yêu cầu gửi Google khớp từng trường (xem ghi chú gốc dưới). Muốn làm thì phải trỏ tạm nhánh cũ của CRM sang Vertex (sửa code repo CRM, repo đó không được commit), bật stack Gateway, và gọi LLM thật trên `crm-test-508114`.
      **HẾT CHẶN (10/09) — câu "vẫn chặn" bên dưới DỰA TRÊN MỘT NHÃN SAI, xem ô 1.2.**
      Lý do chặn cũ ghi là "không có khoá Google nào ở đây gọi được `gemini-2.5-flash` trên nhánh
      cũ". Đo lại thì **khoá gọi được model đó**, 200, nội dung thật. Thứ chặn không phải khoá và
      cũng không phải model, mà là **địa chỉ**: nhánh cũ mặc định đi AI Studio, còn khoá này là
      khoá Vertex.
      **Cách gỡ, không cần đụng console:** trỏ nhánh cũ sang Vertex bằng chính khoá đang có
      (`vertexai=True` trong cùng SDK). Khi đó **hai nhánh đi cùng một địa chỉ**, nên phép so tách
      được đúng thứ ô này hỏi — đường đi của mã có làm đổi kết quả phân loại không — thay vì trộn
      lẫn với chuyện đổi địa chỉ. Đây là việc sửa mã trong repo CRM, mà repo đó **không được commit**
      theo lệnh của người dùng, nên phải hỏi trước khi động vào.
      **Rủi ro chính đã bị loại bằng phép đo khác — xem mục 3.5 nhật ký.** Ghi chú gốc: Chưa chạy được vì không có khoá Google nào ở đây gọi được `gemini-2.5-flash` trên nhánh cũ. Tuy nhiên điều task này thật sự đề phòng là **hai nhánh cấu hình model khác nhau một cách im lặng**, và điều đó nay đã đo được: thân yêu cầu gửi Google **khớp từng trường** — `system_instruction` (không bị nhét vào `contents`), một lượt `user`, `temperature: 0.0`, `max_output_tokens: 8192`, `response_mime_type: application/json`. Việc còn thiếu là so **đầu ra** trên cùng đầu vào; ở `temperature: 0,0` thì phép so đó vẫn có nghĩa và **không được** bỏ qua bằng câu "LLM vốn không tất định". Nguyên văn: Đối chiếu kết quả phân loại của hai nhánh trên **cùng** đầu vào. Khác nhau thì ghi lại khác ở đâu — MUST NOT bỏ qua vì "LLM vốn không tất định": temperature là 0,0

## 8. Sổ sách và dashboard

- [x] 8.1 **Đạt**: 79 phép kiểm, 68 ĐẠT, **0 hỏng**. Nhóm J ĐẠT, và cơ chế "đang trên đường" của change trước hoạt động đúng trong tình huống thật: 3 dòng đang bay, cũ nhất 67s ≤ ngưỡng 420s, nên không báo hỏng oan. Chạy `scripts/audit_db.py` và **không** có dòng nào vào `bo_khong_tag` do lượt gọi của CRM
- [x] 8.2 **Đạt, nhưng chỉ sau khi sửa một lỗ hổng — và lỗ hổng đó mới là giá trị của task này.** Lần kiểm đầu, `/api/usage` KHÔNG có dòng `gemini-2.5-flash` nào cho CRM. Truy ra: `GATEWAY_MODELS` trong `db/rules.py` thiếu `gemini/gemini-2.5-flash`, nên dòng vào `fact_call` với `model_id` **NULL**, `fact_usage_daily` không có dòng, dashboard hiện 0. Lượt gọi vẫn 200, nhóm J vẫn ĐẠT (nó kiểm dòng có vào sổ hay không, mà dòng ĐÃ vào). Đã thêm vào `rules.py`, chạy `gen_catalog.py`, áp một dòng `dim_model_alias` khớp đúng file sinh ra. Xác nhận sau khi sửa: lượt gọi mới giải ra `gemini-2.5-flash`, `fact_usage_daily` +1 dòng, `/api/usage` hiện đủ. Xác nhận số của CRM hiện trên dashboard **mà không chạy lệnh nào** — dịch vụ `ledger-refresh` lo phần đó
- [x] 8.3 **ĐÃ CHỌN (anh Tuấn, 10/09): giữ `crm-500509` kèm ghi chú.** Ghi chú nằm ở `db/gen_catalog.py` ngay trên danh sách `AGENTS`, tức ở NGUỒN SỰ THẬT chứ không ở file sinh ra (`db/02_catalog.sql` ghi rõ "dung sua tay"). Giá trị **không đổi** nên không phải sinh lại catalog và không đụng database.
      Lý do chọn giữ, đo được chứ không phải cho tiện: cột này là khoá JOIN của đường nạp monitoring và hoá đơn Google — `db/connect.py:375` lọc `WHERE gcp_project_id IS NOT NULL`, `db/load_monitoring.py:118` quy project về agent bằng đúng cột này. Đổi giá trị hay để NULL thì mọi dòng monitoring/hoá đơn **cũ** của agent 7 mất đường quy về agent. Điền project mới bằng chuỗi đoán thì tệ hơn cả hai vì nó trông đúng.
      Ghi chú nói rõ cách đọc cột: nó trả lời "hoá đơn Google CŨ nằm ở project nào", KHÔNG trả lời "hôm nay tiền ra từ đâu". Câu sau do sổ Gateway trả lời. **Vẫn còn lửng đúng một thứ và nó thuộc 1.1**: project id dạng chuỗi của project mới.
- [x] 8.4 **Xong** — mục 9 của `docs/archive/gateway/dua-crm-qua-gateway-10-09.md`. Ghi lại rằng khả năng tách hoá đơn theo agent **vẫn giữ** (project mới là project riêng của CRM), nhưng số cũ và số mới **không nối liền** vì đổi project

## 9. Tài liệu

- [x] 9.1 **Xong** — `docs/archive/gateway/dua-crm-qua-gateway-10-09.md`, 9 mục, theo khuôn `docs/archive/gateway/dua-dms-qua-gateway-31-08.md`. Mọi con số trong đó đã soát lại bằng phép đo hoặc bằng đọc code tại đúng dòng, không lấy từ ghi chú cũ
- [x] 9.2 **Xong** — mục 2, bốn chỗ khác. **Và một phép tính sai của tôi, đã tự bắt và tự sửa trong cùng lượt soát:** tôi tưởng `7,3` lượt/phút là con số ghi sai và đã đổi thành `7,7`. `7,3` MỚI ĐÚNG. Sai vì tôi ghép `MIN_INTERVAL_S` của `.env.example` (`7,5`) với `JITTER_S` **mặc định trong code** (`0,5`) — hai chỗ khác nhau. `.env.example` đặt `GEMINI_JITTER_S=1.5`, nên trung bình là `7,5 + 0,75 = 8,25`s → `60/8,25 = 7,27` ≈ **7,3**. Cả hai con số trong proposal/design đều đúng và **không phải sửa gì**. Đã ghi cái bẫy này vào mục 2 của nhật ký, vì lấy hai tham số từ hai nguồn khác nhau cho ra một con số không ứng với cấu hình thật nào. Ghi rõ **CRM khác DMS ở đâu**: pipeline theo lịch chứ không phải web service; SDK mới `google-genai` chứ không phải bản cũ; backend mặc định là Vertex chứ không phải khoá API; tự tuần tự hoá lời gọi bằng khoá toàn cục
- [x] 9.3 **Xong** — mục 4, và nêu rõ hai lý lẽ **độc lập**: sửa được cái thứ nhất thì cái thứ hai vẫn đủ để loại. Ghi lại kết luận về `/gemini` passthrough kèm **hai** lý lẽ độc lập: `next()` trên danh sách deployment (tài liệu DMS), và việc nó bỏ qua router hoàn toàn (`llm_passthrough_endpoints.py:224`)
- [x] 9.4 **Xong, và thành BỐN chuyện chứ không phải hai** — mục 7. Soát lại `docs/HANDOVER.md` bằng cách đối chiếu từng dòng thì ra **8** chỗ lệch, không phải 6: thêm `lùi lịch 429: 15s → 120s` (code là `10, 20, 30`s) và `lùi lịch chung: 2^attempt` (code là `4,0 × attempt`, tuyến tính). Hai chỗ này đáng lo nhất vì ai đọc tài liệu rồi đi đo sẽ **kết luận sai về nhánh nào đã chạy**. Việc thứ tư thêm vào: pipeline **không có cờ tắt tác dụng phụ** nào. Báo lại nhóm CRM hai chuyện. **Một:** `.env.example` khuyến nghị `GEMINI_BATCH_SIZE=40` nhưng `config.py:32` là `min(25, …)` nên 40 bị cắt xuống 25 **mà không báo** — con số khuyến nghị không có tác dụng. **Hai:** `docs/HANDOVER.md` lệch code trên mọi con số — `step1..step4_*.py` riêng lẻ (code là `pipeline.py` một khối 922 dòng), `google-generativeai` (code dùng `google-genai`), `gemini-2.0-flash` (code `gemini-2.5-flash`), 2,5s (3,5s), 5 retry (3), 20 dòng/batch (25)
- [x] 9.5 **Xong** — mục 8.1, đặt trong một mục riêng tên *"Điều chưa chứng minh — đừng đọc thành đã biết"* cùng bốn điều khác (lượt 81 giây không tái hiện được, chưa đối chiếu kết quả hai nhánh, `MIN_INTERVAL_S` production chưa biết, lệch `dim_metric_alias`). Ghi lại rằng nhánh xử lý 429 **chưa được kiểm chứng** ở change này: CRM ở ~7,3 rpm nằm dưới nửa trần 15 nên vận hành bình thường không bao giờ sinh 429. Việc ép nó thuộc change thứ hai

## 10. Bốn việc phát sinh khi apply

Hai việc này **không thuộc phạm vi change ban đầu**. Chúng lộ ra khi làm task 8.2, và người
dùng chốt 09/09: sửa việc thứ nhất, việc thứ hai thì ghi lại chứ không dọn.

- [x] 10.1 **Bịt chỗ dịch vụ `ledger-refresh` nuốt cảnh báo của bộ nạp.** `db/rules.py` cố ý để tuyến chưa khai rơi vào mục "không nối được model", vì ở đó nó *"được ĐẾM và IN RA, không biến mất im lặng"*. Nhưng `mot_luot()` chạy bộ nạp với `capture_output=True` và **chỉ in lại khi bước đó THẤT BẠI** — nên ở lượt chạy thành công, dòng đếm bị ném vào thùng. Đây là hệ quả của change `let-the-gateway-ledger-arrive-by-itself` (đã archive), tức là **lỗi của chính tôi**: tự động hoá làm dữ liệu tươi hơn nhưng bịt mắt một chẩn đoán.
  Sửa: thêm `in_bo_dem_dang_chu_y()` in lại những dòng đếm báo "dữ liệu đến mà không nối được" — hiện có `model not declared` và `identity unresolvable`. **Chỉ in khi con số khác 0**: in cả lúc bằng 0 thì mỗi 120 giây thêm một dòng vô nghĩa, và người đọc sẽ học cách bỏ qua nó, đúng cái hỏng đang đi sửa.
  **Kiểm ngược đủ ba trạng thái**: bí danh CÓ → im lặng; xoá bí danh → `CHU Y [Nap so Gateway]: ... model not declared 4`; trả bí danh → im lặng lại.
- [x] 10.2 **Ghi lại, không dọn**: chạy `db/gen_catalog.py` để lan `rules.py` xuống `db/02_catalog.sql` kéo theo **4 dòng `dim_metric_alias` không liên quan** (`generate_content_free_tier_*`), sinh ra từ dữ liệu trong `data/` đã mới hơn lần sinh danh mục trước. Chúng **có trong file, KHÔNG có trong database đang chạy**, vì `02_catalog.sql` chỉ được áp khi dựng lại toàn bộ (`connect.py:239`). Lệch này **có từ trước**, chạy lại chỉ làm nó hiện ra. Người dùng chốt: để đó.
- [x] 10.3 **Cứu tri thức khỏi một file được sinh ra.** `db/02_catalog.sql` là file do máy sinh, nhưng ngày 04/09 có người gõ tay bốn dòng chú thích vào nó — chạy lại `gen_catalog.py` là mất sạch. Đã chuyển nội dung đó về `db/rules.py`, kèm câu nhắc đừng gõ tay vào file sinh ra.

- [x] 10.4 **GHI LẠI, CHƯA SỬA — `audit_db.py` gộp "chưa kiểm được" vào "khe dữ liệu đã biết".** Lộ ra khi chạy bản đầy đủ trong lượt tự soát 10/09.

  Dòng tổng kết cuối script là:

  ```
  78 checks | 68 passed | 10 notes | 0 failed
  Structure is CLEAN. The 'note' entries are known data gaps, not defects.
  ```

  Nhưng trong **10** note đó có **2** note là *"CHUA KIEM DUOC"* — tức phép kiểm **không hề chạy**, chứ không phải chạy rồi thấy dữ liệu thiếu:

  | | |
  |---|---|
  | đạt | 68 |
  | note là khe dữ liệu thật | 8 |
  | note là **phép kiểm không chạy** | **2** |
  | hỏng | 0 |

  Hai phép không chạy: `Gateway rows in fact_perf_daily carry method and response_code` và `Gateway cache tokens match the invoice cache SKU`.

  Bản thân từng note **có** ghi rõ câu *"Day KHONG phai ket qua dat"* — script trung thực ở tầng từng dòng. Chỗ hỏng nằm ở **dòng tổng kết**: nó khẳng định mọi note đều là "khe dữ liệu đã biết, không phải khiếm khuyết". Ai chỉ đọc hai dòng cuối sẽ tin 78 phép kiểm đều đã chạy.

  Đây đúng lớp hỏng im lặng mà cả dự án này dựng ra để bắt: một phép kiểm lặng lẽ không chạy, và bản tổng kết đọc như đã đạt. **Sửa thì rất nhỏ** (đếm riêng hai loại note ở dòng tổng kết), nhưng nó nằm **ngoài phạm vi** change này, nên ghi lại chứ không sửa lẫn vào đây — cùng cách xử lý như 10.2.

  Và một chuyện nữa cùng họ, về **cách gọi** chứ không về code: chạy `audit_db.py` **trong container `tools`** thì nhóm J rơi vào "chưa kiểm được", vì `GATEWAY_DSN` mặc định trỏ `127.0.0.1:5432` — trong container đó là chính nó. Phải truyền `GATEWAY_DSN` trỏ `postgres:5432`. Lần chạy đầu của tôi hôm nay đúng như thế: `0 failed`, nhưng nhóm J **không chạy**. Truyền DSN vào rồi thì nhóm J ĐẠT: `385 dòng đã nạp, trễ 0s/ngưỡng 420s`, 467 dòng nguồn được soát.
