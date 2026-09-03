# Tasks

Quy ước: mỗi mục đo được thì **ghi số đo ngay tại chỗ**, không ghi "đã kiểm tra".

## 1. Chuẩn bị chiều dữ liệu — làm trước, vì thiếu là rơi 100% dòng

- [x] 1.1 Đo lại `dim_model` xem `gemini-3.5-flash-lite` đã có chưa — **chưa có**; `max(model_id)`
      trước khi thêm là **11**
- [x] 1.2 Thêm `dim_model`: `gemini-3.5-flash-lite`, family `gemini-3`, provider `Google`.
      **`model_id = 12`**. Nguồn chuẩn là `db/rules.py:MODELS`, không sửa tay `02_catalog.sql`
      (file đó do `gen_catalog.py` sinh ra)
- [x] 1.2b **BẪY, đã sập nếu không bắt kịp:** `db/rules.py:MODEL_PATTERNS` có `"3.5 flash"`
      mà chưa có `"3.5 flash lite"`, nên `guess_model("gemini/gemini-3.5-flash-lite")` trả về
      **`gemini-3.5-flash`** — model khác, đơn giá khác, và vẫn báo "có trong dim_model".
      Đã chèn `"3.5 flash lite"` **trước** `"3.5 flash"`. Kiểm 6/6 tên model: sạch
- [x] 1.2c Kiểm sửa `MODEL_PATTERNS` không làm đổi ánh xạ cũ: sinh lại `02_catalog.sql` và so
      với bản trước — **31 SKU billing giữ nguyên toàn bộ**. Hai dòng `data_to` của agent 3 và 4
      có đổi, nhưng do dữ liệu trên đĩa mới hơn lần sinh trước, không phải do sửa này
- [x] 1.3 Thêm `dim_model_alias` nguồn `gateway`, sinh từ `rules.GATEWAY_MODELS`:
      `gemini/gemini-3.6-flash → 11`, `gemini/gemini-3.5-flash-lite → 12`.
      Tổng ánh xạ **44 → 46** (billing 31 · app 4 · monitoring 9 · gateway 2)
- [x] 1.4 Kiểm `dim_agent.code` — có `dms-feedback`, **agent_id 6**, `is_running = true`
- [x] 1.5 Ba tuyến trong `config.gateway.yaml`, đối chiếu xong:

      gemini-flash         gemini/gemini-3.6-flash         -> model 11   OK
      gemini-flash-lite    gemini/gemini-3.5-flash-lite    -> model 12   OK (sau 1.2b)
      gemini-flash-preview gemini/gemini-3-flash-preview   -> CO Y BO

      Tuyến preview bị bỏ có chủ đích: `guess_model` sẽ gộp nó vào `gemini-3-flash`, mà đơn
      giá bản preview so với bản chính thức thì chưa ai kiểm. Để lưu lượng của nó rơi vào mục
      "không nối được model" của bộ nạp — ở đó nó được đếm và in ra

## 2. Kết nối hai database

- [x] 2.1 `connect.open_db()` mở được cả hai. Thêm `connect.GATEWAY_DSN` **trong chính
      `connect.py`** — file đó tự đặt luật "chỗ DUY NHẤT quyết định database mặc định,
      không file nào khác được dựng chuỗi kết nối riêng"
- [x] 2.2 Lập **vai riêng** `gateway_readonly` (`docker/read-only-gateway.sql`), không dùng
      lại `api_readonly`. Ba lý do: (a) `api_readonly` đọc được **0 bảng** trong `litellm`;
      (b) `llmproxy` là chủ sở hữu nên ghi được — đúng thứ task cấm; (c) dùng lại
      `read-only-api.sql` thì kéo theo hàng loạt `REVOKE … FROM PUBLIC` lên database mà
      LiteLLM đang migrate bằng Prisma. File mới **chỉ GRANT, không REVOKE**.
      Nghiệm thu: đọc SpendLogs `true` · ghi SpendLogs `false` ·
      đọc `LiteLLM_VerificationToken` `false` · siêu quyền `false` ·
      thử `CREATE TEMP TABLE` → *cannot execute in a read-only transaction*
- [x] 2.2b Nối vào compose: service `gateway-readonly-init`, profile `gateway`, chạy sau
      `gateway-db-init`. Chạy lần hai bỏ qua `CREATE ROLE`, thoát mã 0
- [x] 2.2c `connect.insert_many()` thêm tham số `on_conflict` (mặc định rỗng nên 15 chỗ gọi
      cũ không đổi hành vi). Kiểm 3/3: đường cũ vẫn ném `UniqueViolation` khi trùng,
      đường mới không nhân đôi và không ghi đè
- [x] 2.3 Kiểm bằng DSN sai cổng. Bộ nạp in ba dòng rồi **thoát mã 1**:
      `KHONG NOI DUOC SO GATEWAY` · `OperationalError: … Connection refused` ·
      `Gateway dang tat? Chay: docker compose --profile gateway up -d`.
      Không có đường nào nạp 0 dòng rồi báo thành công

## 2b. Thêm hai cột vào `fact_call` — phát sinh khi triển khai, xem design ①

- [x] 2b.1 Migration `004_fact_call_src`, forward-only, uỷ quyền cho `sql/004_fact_call_source_cost.sql`
- [x] 2b.2 `source TEXT NOT NULL DEFAULT 'app'` + `fact_call_source_fkey` → `ref_source`
- [x] 2b.3 `cost_usd NUMERIC` cho phép NULL
- [x] 2b.4 Chỉ mục `fact_call_source_ts_idx (source, ts_raw)`
- [x] 2b.5 Chạy migration. **9/9 mốc khớp**: 8.631 dòng · 50.068.543 token · 45.138.423 prompt · 6.871 cached NULL · 15→17 cột · head `004_fact_call_src` · `source='app'` 8.631 · khác app 0 · `cost_usd` khác NULL 0
- [x] 2b.6 `build_usage_daily.py` lọc `AND source = 'app'` trong `load_app()`
- [x] 2b.7 Bỏ ghim cứng `!= 3`, thay bằng nêu đích danh ba nguồn bắt buộc; `gateway` là tuỳ vì sổ có thể rỗng
- [x] 2b.8 Chạy lại: app **371 dòng / 112.775.370 token — không đổi**, billing và monitoring cũng vậy

## 3. Viết `db/load_gateway.py`

- [x] 3.1 Docstring theo khuôn `load_billing.py`: quy tắc, múi giờ, **năm cái bẫy**, tốc độ, SQL nghiệm thu
- [x] 3.2 Đã ghi rõ, kèm số đo hai lượt gọi
- [x] 3.3 `WHERE status = 'success'`
- [x] 3.4 `ts_raw` nguyên bản · `ts_local = ts_raw + 7h` · `tz_confirmed = TRUE`. Kiểm thật: `02:27:00` UTC → `09:27:00` VN, đồng hồ máy lúc gọi `09:26:58`
- [x] 3.5 `call_id = request_id` + `ON CONFLICT (call_id) DO NOTHING`. `request_id` duy nhất 39/39
- [x] 3.6 `resolve_agent()` chỉ nhận tag khớp `dim_agent.code`. Đối chứng độc lập bằng SQL: **2 dòng** bị bỏ, khớp đúng bộ đếm
- [x] 3.7 Tra `(source='gateway', model)` qua `dim_model_alias`, không dùng `model_group`. Kết quả **0 dòng không nối được**
- [x] 3.8 `metadata->usage_object->prompt_tokens_details->>cached_tokens`, thiếu thì NULL. Đo: 34/34 NULL, giữ NULL suốt tới `fact_usage_daily`
- [x] 3.9 `NULLIF` qua `end_user or None`. Đối chứng SQL: **9 dòng** chuỗi rỗng, khớp bộ đếm
- [x] 3.10 `unit_id`/`function_code`/`record_format` để NULL. `account_id` thì **KHÔNG** — xem 3.10b
- [x] 3.10b **Sửa thiết kế khi triển khai.** design ⑩ viết "để `account_id` NULL". Sai:
      `account_id` nằm trong **khoá chính** của `fact_usage_daily`, NULL không vào được.
      Và đo ra một thứ tốt hơn: quy ước A3 đặt tài khoản dịch vụ dạng `svc.<code>`, nên
      `end_user = 'svc.dms-feedback'` khớp **thẳng** `account` 949 — không phải suy đoán.
      Không tra được thì rơi về neo mức agent
- [x] 3.10c **Bắt được lúc tự đọc lại, trước khi chạy.** Bản đầu tra neo bằng
      `accounts.get("svc." + code)`. Docstring của `anchor_accounts()` ghi lại một sự cố
      có thật đúng hình dạng đó: *"TRA BẰNG (kind, unit_agent_id), KHÔNG BẰNG TÊN ĐĂNG
      NHẬP… quy ước A3 bắt tài khoản dịch vụ đổi sang `svc.<code>`, đúng chỗ đó gãy"*.
      Hai agent mang `kind='whole_agent'` và tên **không** theo dạng đó. Đã thêm
      `connect.anchor_account_lookup()` tra theo `(kind, unit_agent_id)`
- [x] 3.11 Dùng `total_tokens` của sổ
- [x] 3.12 `--dry-run` chạy đủ mọi khâu ánh xạ, không ghi gì

## 4. Nghiệm thu ngay trong loader — in ra, không chỉ assert

- [x] 4.1 So **cả hai chiều**: dòng và token. `31.839 + 42 = 31.881` khớp nguồn
- [x] 4.2 In `5 dòng, 28 token`
- [x] 4.3 In `bỏ: không có tag 2 | nhiều tag 0`
- [x] 4.4 In `không nối được model 0`
- [x] 4.5 In `cached_tokens NULL 34`
- [x] 4.6 In `end_user rỗng 9 | end_user là người lạ 13`
- [x] 4.7 Chạy hai lần: lần hai chỉ đọc 2 dòng (nhờ chỉ mục) và **chèn thêm 0**

## 5. Chi phí và tổng hợp ngày

- [x] 5.1 Thêm `load_gateway()` vào `build_usage_daily.py`
- [x] 5.2 `SUM(cost_usd)` từ `fact_call`, gốc là `metadata->cost_breakdown->total_cost`
- [x] 5.3 Chốt chặn trong bộ nạp: margin/discount khác 0 thì **dừng và thoát mã 1**. Đo hiện tại 0/34 dòng
- [x] 5.4 View `usage_resolved` đặt `token_estimated = 1` khi thiếu billing — dòng gateway mang đúng nhãn đó
- [x] 5.5 `fact_usage_daily` có dòng `2026-08-31 | agent 6 | model 12 | 32 lượt | 25.560 token`, **ngày theo giờ VN**

## 6. Kiểm bằng lượt gọi thật

- [x] 6.1 Mốc: sổ 39 dòng, `fact_call` gateway 32 dòng, đồng hồ VN `09:26:58`
- [x] 6.2 `Báo lỗi` + `Bảo hành`, `Tiêu cực`, `decision_log` 2 mục
- [x] 6.3 Poll tới khi **ổn định** ở 41 (tăng 2), rồi mới nạp — thoát ngay lần đầu đổi số là sai, vì dòng thứ hai còn đang ghi
- [x] 6.4 `fact_call` tăng **đúng 2 dòng**; `ts_local` lệch đồng hồ máy 2 giây
- [x] 6.5 Token hai dòng khớp sổ gốc tuyệt đối
- [x] 6.6 `usage_resolved` hiện: `Phân Loại Phản Hồi Tiếp Thị | gemini-3.5-flash-lite | 34 lượt | 31.839 token | token_source=gateway | token_estimated=1`

## 7. Tài liệu

- [x] 7.1 `docs/reference/nap-so-gateway-vao-database-31-08.md` — 8 mục: phát hiện
      `guess_model` khớp nhầm · bốn chỗ thiết kế sai · bốn bẫy dữ liệu · số đo tốc độ ·
      đã chứng minh được gì · vì sao tách database · đã đụng vào những gì · việc còn lại
- [x] 7.2 Đã gỡ khỏi mục 9 của nhật ký chặng trước, thay bằng kết quả đo được và trỏ sang
      nhật ký mới
- [x] 7.3 Bảng "chưa chứng minh" ở mục 8: bí danh-chỉ-ở-dòng-hỏng mới là **suy luận**; neo
      mức agent cho 7 agent còn lại **chưa đo**; `GATEWAY_MODELS` **chưa có kiểm tự động**;
      hành vi ở quy mô lớn **chưa đo** (mới 34 dòng)

## 8. Vá sau khi hoàn thành — siết điều kiện nối `account_id`

Phát sinh khi bàn về việc ghi lại người dùng. Không phải task dự kiến; là **lỗ hổng trong
chính code của change này**, tìm ra trước khi nó gây hại.

- [x] 8.1 Đo ra đường hỏng: bảng `account` **có** dòng `admin` — `account_id 1`,
      "Quản trị viên", `unit_agent_id 5` (TLA Hợp Đồng) — và dòng đó **đã mang 480 lượt /
      1.588.404 token**. Bộ nạp bản đầu tra thẳng `accounts.get(end_user)`, nên ngày DMS gửi
      `X-User: admin` (tên đăng nhập cục bộ của nó) lưu lượng DMS sẽ bị **trộn vào lịch sử của
      một người dùng TLA Hợp Đồng** — im lặng, tổng vẫn khớp
- [x] 8.2 Đo thêm: `username` không trùng lặp (0), nhưng **`email` trùng 2** — cùng một người
      có hai tài khoản ở hai agent (`long.nt@`, `phuong.nt@`). Nên email **cũng không phải**
      khoá nối an toàn. Điều tôi khẳng định trước đó là sai
- [x] 8.3 Đo quyết định: **agent 6 (DMS) không có tài khoản người thật nào.** Chỉ agent 5
      (45 dòng) và agent 8 (893 dòng) có — đúng hai app đã được cào. Kể cả khi DMS gửi tên
      chuẩn, hiện chưa có dòng nào để nối tới
- [x] 8.4 Sửa: định danh **chỉ được chấp nhận khi nó tra ra đúng tài khoản neo của chính
      agent đó**. `svc.dms-feedback → 949` = neo của agent 6, nhận. `admin → 1 ≠ 949`, từ chối.
      Không cần đoán tiền tố, không cần danh sách trắng
- [x] 8.5 Phép kiểm **âm**, 5/5 đạt — chứng minh nó *từ chối* chứ không chỉ *chấp nhận*:

      svc.dms-feedback -> 949   nhan
      admin            -> 949   TU CHOI (khong phai 1)
      administrator    -> 949   tu choi
      (rong)           -> 949   neo
      nguoi.la         -> 949   neo

- [x] 8.6 Không hồi quy: 38 dòng đang có **đều mang `account_id 949`**, chạy lại bộ nạp chèn
      thêm 0 dòng. Đối soát 24 khoá lệch đúng 2 khoá, và cả hai giải thích được đến từng token
      (`fact_call` +4 dòng, `usage_resolved` +13.348 token = lưu lượng thật phát sinh sau khi
      chụp mốc lúc 09:44)
- [x] 8.7 Đổi tên bộ đếm `end_user_la_nguoi_la` → `danh_tinh_khong_noi_duoc` cho đúng nghĩa.
      Tới ngày DMS gửi tên người thật, chúng sẽ rơi vào bộ đếm này — **ồn ào, đúng như mong
      muốn** — cho tới khi chiều người dùng của DMS được dựng

## 9. Cho tiền Gateway hiện lên dashboard (phương án B, chốt 31/08)

Chủ dự án chọn **hiển thị thẳng số tiền của LiteLLM**, không thêm cờ phân biệt
hoá-đơn/ước-tính. Lý do: dữ liệu ba nguồn cũ vốn đã không đồng nhất (kéo tay, giới hạn của
Google Cloud, không với sâu được vào trong các app) nên sai số là thứ phải sống chung; và đo
được Ralli 100% ước tính, TLA Hợp Đồng 78,1% — việc phân biệt không đổi một quyết định thực tế nào.

- [x] 9.1 Đo tiền đề trước khi làm. Chủ dự án nói *"con nào có billing chuẩn đâu"* — **đúng
      với 2/8 agent**, sai với 6 agent còn lại: Contact Center 2,1% ước tính · Multi modal
      13,1% · Sale Agent 18,6% · CRM 18,7% · Tools Quizzer 19,6%. Tổng 71,7% tiền là hoá đơn thật
- [x] 9.2 Migration `005_gateway_cost`: `cost_usd = COALESCE(b.cost, g.cost)` — **hoá đơn
      trước, gateway sau**. Thứ tự này KHÁC thứ tự của token (gateway trước): token thì Gateway
      đếm chính xác hơn, còn tiền thì hoá đơn là số thật
- [x] 9.3 Cột và thứ tự cột không đổi (12 cột) nên `CREATE OR REPLACE VIEW` dùng được.
      Đã kiểm: **0 view phụ thuộc** `usage_resolved`
- [x] 9.4 `token_estimated` **giữ nguyên** — nó nói về token, không nói về tiền. Dòng Gateway
      vẫn mang cờ 1 dù nay đã hiện tiền
- [x] 9.5 Sửa phép kiểm audit thành `hoá đơn + gateway == view`. **Thiếu bước này thì audit
      đỏ mỗi lần chạy**, và `update_dashboard.py` thất bại ở bước 9/9 vì `audit_db.py` thoát mã 1
- [x] 9.6 **Bẫy tính đôi, suýt mắc.** Không được cộng thẳng `hoá đơn + toàn bộ gateway`: view
      ưu tiên hoá đơn, nên dòng nào có CẢ HAI thì tiền gateway bị bỏ. Ngày hoá đơn 31/08 về là
      hai nguồn trùng khoá. Đã thêm `NOT EXISTS` lấy đúng phần gateway mà view thực sự dùng
- [x] 9.7 Phép thử âm cho 9.6: giả lập ngày 31/08 đã có hoá đơn → tiền gateway ngày đó **bị
      loại đúng**, kết quả `0,500000` chứ không phải `0,521305`
- [x] 9.8 Nghiệm thu: head `005_gateway_cost` · view 1.276 dòng / 12 cột **không đổi** ·
      tổng tiền `307,382155` = `307,360850 + 0,021305` · audit **36 phép kiểm, 0 hỏng**
- [x] 9.9 **THAY THẾ một yêu cầu spec.** `label-derived-cost-across-dashboard`,
      `specs/visible-data-provenance` yêu cầu *"Mọi ô… có chứa tiền SHALL cho biết phần nào đến
      từ hoá đơn và phần nào suy từ bảng giá"*. Với nguồn `gateway`, yêu cầu đó **không còn
      hiệu lực**. Đã ghi lý do ở đầu `db/migrations/sql/005_gateway_cost_vao_view.sql`
- [x] 9.10 Hệ quả phải biết: `app.js:1143` đếm tiền Gateway vào nhóm `costInv` (không còn dấu
      `≈`), `app.js:3806` ghi nguồn là "hoá đơn". Số trên màn hình:
      **hoá đơn $307,3822 / 1.013 dòng · ước tính $121,2823 / 263 dòng**
