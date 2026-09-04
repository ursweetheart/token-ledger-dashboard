# Việc phải làm

## 1. Chốt ranh giới trước khi chạy gì

- [x] 1.1 Đo endpoint 8 agent thật đang dùng — `SELECT` chỉ-đọc trên `fact_monitoring`.
      Kết quả: `generativelanguage` 120.247 dòng / 7 agent, `aiplatform` 20 dòng
- [x] 1.2 Thử hai khoá trong `.env`. `KEY_GOOGLE_AI_STU` → 200 (50 model);
      `KEY_GOOGLE_CLOUD_CONSOLE` → 403 PERMISSION_DENIED
- [x] 1.3 Đối chiếu `dim_model` với model khoá gọi được, có trọng số theo token thật.
      `gemini-2.5-flash` = 46,2%, phủ 53,2%
- [x] 1.4 Kiểm cổng `4000` / `5433` / `9090` rảnh, `5432` là của dự án
- [x] 1.5 Ghi lại số phiên bản LiteLLM của bản fork và commit hash đang đứng.
      `pyproject.toml` version = **1.99.0**; commit **f005afa146** (2026-08-22,
      "test(exception-mapping): pin the status and error-shape table..."); cây làm việc sạch

## 2. Dựng môi trường đo

- [x] 2.1 Viết `litellm_rang_dong/config.probe.yaml` — một model `gemini/gemini-2.5-flash`,
      `api_key: os.environ/KEY_GOOGLE_AI_STU` (tham chiếu, KHÔNG phải chuỗi)
- [x] 2.2 Viết `litellm_rang_dong/docker-compose.probe.yml` — `name: litellm-probe`,
      db `127.0.0.1:5433`, litellm `127.0.0.1:4000`, volume `litellm_probe_pg`, bỏ prometheus
- [x] 2.3 Kiểm hai file KHÔNG chứa chuỗi khoá: `grep` tìm tiền tố khoá, phải ra rỗng
- [x] 2.4 Kiểm `docker-compose.yml` gốc của fork KHÔNG bị sửa — `git status` trong fork chỉ
      thấy 2 file mới
- [x] 2.5 Build. **Lần 1 vỡ**: `keyutils-libs-1.6.3-r39: IO ERROR` — 1/72 gói hỏng do I/O
      thoáng qua, không phải lỗi cấu hình (máy ảo Docker còn 893 GB). **Lần 2 đạt**:
      `litellm_rang_dong:probe` = `cc794ac6c222`, 1,65 GB, 0 dòng ERROR.
      Kiểm bên trong image: litellm **1.99.0**, litellm-enterprise 0.1.59,
      litellm-proxy-extras 0.4.89 — khớp `pyproject.toml` của fork
- [x] 2.6 `up -d`. db `healthy`, litellm `health/liveliness` → **HTTP 200**
- [x] 2.7 Ranh giới: `:5433` → `current_database()` = **`litellm`**, 75 bảng `LiteLLM_*`.
      `token-ledger-postgres` (tạo lại lúc 01:57 UTC, không phải bởi tôi) `healthy`;
      `token_ledger` **và** `token_ledger_v2` đều có **0** bảng `LiteLLM_*` và vẫn đủ
      **867.657.110** token
- [x] 2.8 `127.0.0.1:4000` và `127.0.0.1:5433`, không cổng nào `0.0.0.0`

## 3. Lượt 3a — `mock_response`, không tốn phí

- [x] 3.1 Mốc trước khi gửi: **0 dòng**
- [x] 3.2 `mock_response` **trong body KHÔNG chặn** cuộc gọi — cả 2 lượt vẫn ra Google.
      Phải khai ở **tầng cấu hình** (`litellm_params.mock_response`) mới ăn → HTTP 200,
      không gọi Google
- [x] 3.3 **4 dòng** — mock CÓ ghi log. Và LiteLLM ghi cả **request thất bại**
      (`status='failure'`, có cả token count), điều không ai giả định trước
- [x] 3.4 **34 cột** → `tools/probe-gateway/ket-qua/spendlogs-cot.txt`
- [x] 3.5 → `tools/probe-gateway/ket-qua/spendlogs-mot-dong-3a.json` (248 dòng, đã che khoá)
- [x] 3.6 **A3 TRẢ LỜI: `X-User` KHÔNG sống sót.** 0/10 cột chứa giá trị đó, kể cả
      `proxy_server_request` (rỗng `{}`). Header tuỳ ý bị **vứt bỏ hoàn toàn**.
      🔴 **Quy ước A3 như đã ban hành sẽ mất danh tính, im lặng.**
      Hai đường thay thế ĐO ĐƯỢC: body `user` → cột `end_user` ✅;
      header `x-litellm-tags` → cột `request_tags` ✅

## 4. Lượt 3b — request thật

- [x] 4.1 `gemini-2.5-flash` **404 "no longer available to new users"** → đổi sang
      `gemini-3.6-flash` (Google chỉ định) trên key AI Studio **gói miễn phí, project mới**
- [x] 4.2 → `tools/probe-gateway/ket-qua/spendlogs-mot-dong-4b-that.json`
- [x] 4.3 **A5 TRẢ LỜI: không có cột riêng, nhưng DẪN XUẤT được.**
      Phép đo có đối chứng, cùng model cùng câu hỏi, khác đúng 1 tham số:
      `reasoning_effort:high` → `reasoning_tokens`=**432**;
      `reasoning_effort:disable` → khoá **vắng mặt hoàn toàn** (không phải `0`).
      `output_modality` cũng vậy: `completion_tokens_details.text_tokens` = 22 / 3.
      🔴 Sheet `Data Out` phải ghi **"dẫn xuất từ Gateway"**, KHÔNG phải "Nguồn: Gateway"
- [x] 4.4 `spend` **dựng lại được chính xác** từ token × đơn giá:
      input 35×0,00000075=0,00002625; reasoning 432×0,00000375=0,00162;
      text 22×0,00000375=0,0000825 → total **0,00172875** ✅ khớp tuyệt đối.
      `cost_breakdown` tách sẵn `reasoning_cost`. `service_tier`=`"default"` (không phải
      chỉ Vertex mới có — dự đoán trước đó của tôi sai)
- [x] 4.5 Chỉ có ở request thật: `api_base` (mock để rỗng), `reasoning_cost`,
      `service_tier`, và `completion_tokens_details` có nội dung thật.
      🔴 **`completion_tokens` = 454 = 432 suy luận + 22 văn bản** — đã GỒM token suy luận,
      không được cộng thêm lần nữa khi đối chiếu hoá đơn
- [x] 4.6 `SpendLogs` ghi **CẢ HAI**: `model`=`gemini/gemini-3.6-flash` (tiền tố + mã API),
      `model_group`=`probe-36` (tên ta đặt). Ánh xạ về `dim_model` phải đọc `model`.
      🔴 Kiểm trên chuỗi THẬT: `guess_model("gemini-3.6-flash")` → **`None`**.
      `gemini-3-flash-preview` → `gemini-3-flash` ✅. `gemini-3-flash-preview` **có** trả
      `reasoning_tokens`=176 — báo cáo lỗi trên diễn đàn Google là nhầm phía người dùng

## 5. Đối chiếu với hợp đồng dữ liệu

- [x] 5.1 Lập bảng ~~25~~ **26** trường sheet `Data Out` × LiteLLM: **có** / **không có** / **tên khác**

      Bảng đầy đủ: [`docs/reference/doi-chieu-data-out-litellm.md`](docs/reference/doi-chieu-data-out-litellm.md) §2.
      ⚠️ Sheet có **26** trường, không phải 25 — task ghi sai từ đầu, đã sửa ngay đây.

      ```
         chung minh duoc, co san      10
         dan xuat duoc, da chung minh  4
         cua he thong ta, khong phai Gateway  5
         co duong nhung chua do        7
                                      --
                                      26
      ```

      🔴 Phát hiện đắt nhất của bảng: **ba lần trùng tên khác nghĩa** — `agent_id`,
      `model_id`, và "project" (`user_api_key_project_id` ≠ `gcp_project_id`). LiteLLM có
      cột đúng tên nhưng nghĩa hoàn toàn khác. Loader ánh xạ theo tên sẽ chạy trơn, ra số,
      và sai. Cùng họ với `source='app'` ở change `admit-gateway-as-a-fourth-source`.
- [x] 5.2 Lập chiều ngược lại: trường LiteLLM ghi mà `Data Out` không có

      [`docs/reference/doi-chieu-data-out-litellm.md`](docs/reference/doi-chieu-data-out-litellm.md) §3. Bốn trường **nên thêm** vào hợp đồng, trong đó một trường là bắt buộc:

      `gateway_overhead_ms` ← `metadata.litellm_overhead_time_ms`, đo được **21,344 ms**.
      Đây **chính là** "độ trễ tăng thêm do Gateway" mà GĐ7 dòng 21 phải báo cáo — không
      có trường này thì tới lúc viết báo cáo phải đi đo lại bằng tay.

      Ba trường còn lại: `reasoning_tokens` (đang bị gói kín trong `output_tokens`),
      `time_to_first_token_ms`, `model_group`.
- [x] 5.3 Đánh dấu trường nào cần `fact_request`, trường nào tổng hợp được về mức ngày

      [`docs/reference/doi-chieu-data-out-litellm.md`](docs/reference/doi-chieu-data-out-litellm.md) §4.

      Ranh giới quyết định: **`latency_ms` không gộp được.** p50/p95/p99 không cộng được —
      trung bình của các trung bình ngày không ra được phân vị. Mất dòng gốc là mất p95
      vĩnh viễn, không dựng lại được.

      Gộp về ngày được: `input/output/cached/total_tokens`, `cost_usd`, số request.
      Chiều gộp: `date × account_id × agent_id × model_id × unit_id`.

      🔴 `status` **bắt buộc** nằm trong `fact_request` *và* trong chiều gộp. LiteLLM ghi
      cả request thất bại kèm token count; gộp mà không tách `status` là cộng token của
      lượt hỏng vào tổng lượt chạy được — và tổng vẫn ra một con số trông bình thường.
- [x] 5.4 Ghi rõ chỗ nào là **chứng minh được**, chỗ nào là **suy luận** — không trộn

      Không viết thành một mục riêng mà làm thành **một cột trong chính bảng** —
      [`docs/reference/doi-chieu-data-out-litellm.md`](docs/reference/doi-chieu-data-out-litellm.md) §1. Tách ra một mục riêng thì người đọc bảng vẫn đọc bảng và bỏ qua mục.

      Năm mức: ✅ chứng minh được · 🧩 dẫn xuất được đã chứng minh · 🏠 không phải việc của
      Gateway · 🟡 có đường chưa đo · ⚠️ bẫy.

      §5 ③ gom **cả 7 trường 🟡 vào một lượt đo duy nhất**: Virtual Key thật gắn team, gửi
      header `unit` + `function`, hỏi lại đúng câu vừa hỏi (ép cache hit), gọi một model
      chết (bắt fallback + lỗi). Không cần bảy lượt.

## 6. Ghi lại và dọn

- [x] 6.1 Viết `docs/reference/do-ban-ghi-litellm-24-08.md`: cách đo, phiên bản, bảng đối
      chiếu, dòng `SpendLogs` nguyên vẹn, và những gì chưa chắc chắn

      Xong 26/08 chiều. Gồm 9 mục: phiên bản ghim (fork `f005afa146`, image
      `sha256:cc794ac6c222`), cách đo tái lập được, **4 khoá cấu hình** quyết định cột nào
      có dữ liệu, bảng đối chiếu cách-gửi × cột-nhận, 34 cột `SpendLogs`, 4 phát hiện về
      số, Vertex-hay-AI-Studio, và mục 8 riêng cho phần **chưa chắc chắn**.
- [x] 6.2 Sửa A5 trong sheet `Data Out` theo kết quả đo. Chép bản có ngày trước khi sửa —
      git không theo dõi `.xlsx`

      Bản lưu: `docs/reference/ban-luu/Master Plan API Gateway 2026-08-27.xlsx`, sha256
      khớp từng byte trước khi sửa.

      ```
         dong 16  thinking_enabled   Nguon: "Gateway" -> "Dan xuat tu Gateway"
         dong 17  output_modality    Nguon: "Gateway" -> "Dan xuat tu Gateway"
      ```

      Cả hai kèm **quy tắc tính** trong cột `Ghi chú`, vì "Nguồn: Gateway" khiến người code
      đi tìm một cột không tồn tại. Ghi chú nói rõ chỗ dễ vỡ nhất: khi tắt suy luận,
      `reasoning_tokens` **vắng mặt hoàn toàn**, không phải `= 0`.
- [x] 6.3 Cập nhật `viec-can-lam-truoc-api-gateway.md` §A5 từ 🟡 sang trạng thái thật

      §A5 🟡 → ✅, kèm bảng "có cột riêng không / dẫn xuất được không" và cảnh báo về ba
      cách viết code đọc `reasoning_tokens` — một đúng, hai sai.

      Làm thêm ngoài phạm vi task, vì phát hiện lúc kiểm: **§A4 cũng đã lỗi thời.** Cả 4
      kiểu dữ liệu §A4 đòi sửa thì sheet **đã sửa rồi** (#6 `text`, #12 `int`, #22 `text`,
      #23 ms mức request), nhưng mục vẫn treo 🟡 và bảng ưu tiên vẫn ghi "30 phút". Đã đổi
      cả hai sang ✅ kèm ngày.
- [x] 6.4 Ghi vào mục còn treo, **không** điều tra trong change này:
      (a) `gemini-3.6-flash` / `gemini-3.7-flash` có trên API nhưng `guess_model()` trả `None`;
      (b) `gemini-2.5-flash-image` bị gộp vào `gemini-2.5-flash`, mất nhánh ảnh;
      (c) `gemini-2.0-flash` (9,5% lưu lượng) đã rút khỏi API

      Cả ba ghi ở `nhat-ky-26-08-sang.md` §15 "Còn treo" và `do-ban-ghi-litellm-24-08.md` §9.
      (a) nay có **xác nhận sống**: Google trả `404` cho `gemini-2.5-flash` kèm câu
      *"no longer available to new users… use gemini-3.6-flash"* — đúng model `guess_model()`
      trả `None`. Thêm một mục 🔴 mới không có trong danh sách gốc:
      `forward_client_headers_to_llm_api` phải TẮT ở bản thật (gửi email nhân viên sang Google).

- [x] 6.5 Ghi quan sát Ralli không có dòng monitoring AI nào, kèm hệ quả cho giai đoạn 7

      Quan sát đã ghi ở §15 "Còn treo". Phần hệ quả viết 27/08 tại
      `do-ban-ghi-litellm-24-08.md` **§10**, sau khi đo lại bằng `SELECT` chỉ-đọc:

      ```
         Tro ly ao Ralli        0 dong monitoring     47.933.778 token nguon 'app'
         Tro Ly Ao Hop Dong     2.304 dong            62.706.827 token nguon 'app'
         6 agent con lai        co monitoring         0 token nguon 'app'
      ```

      🔴 **"Đối chiếu bốn nguồn" chỉ đúng với 1 trên 8 agent.** Ralli có 3 nguồn (thiếu
      `monitoring`), 6 agent còn lại có 3 nguồn (thiếu `app`), chỉ Hợp Đồng đủ 4.

      Ba hệ quả cho GĐ7: (1) báo cáo phải chia theo agent × nguồn, một con số tổng sẽ đúng
      số học và sai ý nghĩa; (2) Ralli mang 47,9M token mà **không có ý kiến thứ ba để phân
      xử** khi Gateway lệch so với `app` — lại đúng là agent ta chưa biết có tiền xử lý
      request hay không; (3) ô không có nguồn phải là `NULL`, `COALESCE(...,0)` sẽ ra chênh
      lệch bằng toàn bộ token của Ralli hoặc bằng 0, cả hai đều vô nghĩa.

- [x] 6.6 `docker compose -f docker-compose.probe.yml down` — giữ volume phòng khi cần đọc lại

      26/08 chiều: 2 container + 1 network đã gỡ, `rc=0`. Volume
      `litellm-probe_litellm_probe_pg` **còn nguyên** (kiểm bằng `docker volume ls`).
      `token-ledger-postgres` vẫn `Up (healthy)`.

- [x] 6.7 Kiểm `.env` không đổi, không file nào trong repo chứa chuỗi khoá

      Quét cả hai khoá Google (mỗi khoá 53 ký tự, **không in giá trị**) trong repo dự án:
      **0 file**, trừ chính `.env`. Fork: `git status --porcelain` = **0 dòng** — không file
      nào thêm hay sửa; quét thêm các file cấu hình ở gốc fork cũng ra 0.

      🔴 **NHƯNG ô này KHÔNG được tick.** Phép kiểm trên chỉ tìm **hai chuỗi đã biết trước**,
      nên nó bỏ lọt một bí mật thuộc loại khác:

      ```
         ?? JWT_test_for_header      153 byte, goc repo, KHONG nam trong .gitignore
            noi dung: "Bearer <JWT>"  -- token THAT, claim {exp, role, sub}
            luc kiem: CON SONG, het han sau ~42 phut
      ```

      Đúng họ với chín lỗi ở `nhat-ky-26-08-sang.md` §12c–13: **phép đo hỏng trông giống
      phép đo đạt.** Nó trả "0 file" và trông như một kết quả đạt, chỉ vì câu hỏi hỏi sai —
      *"có chứa hai chuỗi này không"* thay vì *"có bí mật nào không"*.

      Muốn tick ô này thì phải: (1) xử lý `JWT_test_for_header` — đưa ra ngoài repo, hoặc
      thêm vào `.gitignore`, hoặc xoá; (2) đổi phép kiểm sang quét **hình dạng** bí mật
      (`Bearer `, `eyJ`, `AIza`, `sk-`) chứ không quét danh sách chuỗi đã biết.

      ---

      ✅ **Làm xong 27/08/2026, và phép kiểm mới bắt được thứ phép kiểm cũ không thấy.**

      Cả hai việc trên đã làm: `tools/scan_secrets.py` quét **6 hình dạng** trên 410 file
      văn bản, không quét chuỗi biết trước. `JWT_test_for_header` đã ra khỏi repo
      (`D:\RangDonk\JWT_test_for_header.het-han-2026-08-26`; token hết hạn 26/08 17:49).

      Lần chạy đầu ra **24 phát hiện**, trong đó có một thứ chưa ai biết:

      ```
         tools/probe-gateway/ket-qua/spendlogs-mot-dong-luot5.json   7 x JWT 260 ky tu
         tools/probe-gateway/ket-qua/spendlogs-mot-dong-5b.json      7 x JWT 260 ky tu
      ```

      **Chính hai file bằng chứng của phép đo mang nguyên chuỗi JWT.** Cả hai chưa được
      theo dõi và không nằm trong `.gitignore` — `git add -A` sẽ commit chúng. Đây đúng là
      loại bí mật mà phép quét theo chuỗi-biết-trước không bao giờ thấy, vì nó không phải
      khoá Google.

      10 khớp còn lại là **báo động giả**, đã phân loại từng cái thay vì bỏ qua cả file:
      biến thay thế (`${GATEWAY_PGPASSWORD:-...}`), dấu đã che (`***`), ví dụ văn xuôi
      (`postgresql://u:p@ss@may/db`). Bỏ qua theo *lý do*, không theo *đường dẫn* — bỏ qua
      cả file là mở một chỗ mù vĩnh viễn.

      Cách xử lý hai file bằng chứng: **che chứ không xoá**, giữ được cả hai vế.

      ```
         thay 7/7 chuoi bang   <JWT-DA-CHE len=260 sha256=da5ec4c0>
         ca 7 cho cung mot dau -> van chung minh duoc "ghi nguyen van, giong het nhau"
         JSON van doc duoc · con lai chuoi 'eyJ': 0
         ban goc giu NGOAI repo: D:\RangDonk\ket-qua-goc-chua-che-2026-08-26\
      ```

      Chạy lại: **0 phát hiện nghiêm trọng, `rc=0`**. `.env` nằm trong `.gitignore`, dấu
      vân tay `sha256 f39e5f28ca2ceaece…` — ghi lại để lần quét sau so được là có đổi không.
      Fork: `git status --porcelain` = **0 dòng**.

## 7. Nghiệm thu

- [x] 7.1 Có một dòng `LiteLLM_SpendLogs` thật chép ra được, kèm ngày và phiên bản

      **Bốn** dòng, không phải một, trong `tools/probe-gateway/ket-qua/`:
      `spendlogs-mot-dong-3a.json` · `-4b-that.json` · `-luot5.json` · `-5b.json`.
      34 cột. Phiên bản ghim ở `do-ban-ghi-litellm-24-08.md` §1.

- [x] 7.2 A3 có câu trả lời **đo được** (header sống hay chết), không phải suy đoán

      **Header SỐNG.** Và câu trả lời **ngược** với lượt đo đầu.

      Lượt 4b kết luận *"0/10 cột, mất sạch"* vì `store_prompts_in_spend_logs` mặc định
      **tắt**, khiến `proxy_server_request` luôn trả `"{}"` bất kể gửi gì
      (`spend_tracking_utils.py:1097`). Phép đo nhìn đúng chỗ, nhưng chỗ đó đang khoá.

      Đo lại đủ điều kiện — cùng gateway, cùng header, khác một khoá config:

      ```
                                luot 4b        luot 5
         proxy_server_request   {} 0 khoa      5 khoa
         so header ghi lai      0              8
      ```

      `user_header_name` đẩy header vào `end_user`, kể cả với request **thất bại**.
      `turn_off_message_logging` giữ header mà xoá prompt: chuỗi mồi
      `BI-MAT-KHONG-DUOC-LUU-VAO-DB` xuất hiện **0 lần** trong dòng 19.031 byte, header
      vẫn 8/8. Chi tiết: `nhat-ky-26-08-sang.md` §16.

- [x] 7.3 A5 có câu trả lời **đo được**, và sheet `Data Out` đã sửa theo

      Vế đầu xong 26/08: `reasoning_tokens` vắng mặt hoàn toàn khi tắt (không phải `=0`),
      nên `thinking_enabled` **dẫn xuất được** — đo có đối chứng, cùng model cùng câu hỏi,
      khác đúng một tham số.

      Vế sau xong 27/08 (task 6.2): dòng 16 và 17 của sheet `Data Out` nay ghi
      **"Dẫn xuất từ Gateway"** kèm quy tắc tính. `viec-can-lam-truoc-api-gateway.md` §A5
      cũng đã chuyển 🟡 → ✅ (task 6.3). Cả hai vế **đạt**.

- [x] 7.4 `token-ledger-postgres` vẫn chạy, `token_ledger` không có bảng `LiteLLM_*` nào

      `Up (healthy)`. Số bảng khớp `LiteLLM%` trong `token_ledger`: **0**, `rc=0`.

- [x] 7.5 `SELECT COUNT(*) FROM usage_resolved` trên `token_ledger` vẫn ra 867.657.110 token

      **1.189 dòng · 867.657.110 token**, `rc=0`. Khớp đúng từng chữ số với mốc 8.1.

- [x] 7.6 `git status` trong cả hai repo: không có file nào chứa khoá

      🔴 Ngày 26/08 **không đạt**: `git status` repo dự án có `?? JWT_test_for_header` —
      một Bearer token còn sống, ngoài `.gitignore`, nên `git add -A` sẽ commit nó.

      ✅ **27/08 đạt.** File đã ra khỏi repo, và hai file bằng chứng mang JWT đã che
      (xem 6.7). `tools/scan_secrets.py` chạy trên toàn bộ cây làm việc — kể cả file chưa
      được theo dõi, tức đúng những file `git status` đang liệt kê — ra **0 phát hiện
      nghiêm trọng, `rc=0`**. Fork: `git status --porcelain` = **0 dòng**.

      Phép kiểm này nay **chạy lại được**: `python tools/scan_secrets.py`, mã thoát ≠ 0 là
      có bí mật lọt. Không còn là một lần kiểm bằng mắt.
