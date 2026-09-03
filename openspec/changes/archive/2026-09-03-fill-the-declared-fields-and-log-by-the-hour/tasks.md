# Tasks

Quy ước: mỗi mục đo được thì **ghi số đo ngay tại chỗ**, không ghi "đã kiểm tra".

## 1. Ghi mốc trước khi đổi

- [x] 1.1 `var/baseline-truoc-008.json` — 24 khoá
- [x] 1.2 Đo: `cached_tokens` **0/41** · `unit_id` **0/41** · `cost_usd` 38/41 · `duration_ms` 38/41 · `model_id` 39/41
- [x] 1.3 app 371 · billing 1.012 · monitoring 606 · gateway 1
- [x] 1.4 Ước lượng số dòng bảng theo giờ. Đếm **ba cách** (khoá thiếu / khoá đủ / khoá đủ kèm
      bộ lọc thật của `build_usage_daily`) ra hệ số **3,8 – 6,9 lần**, tổng **3.000 – 7.700**
      dòng. `fact_call` 298→704 (2,4). **Không cách nào chính xác** — con số thật ở việc 6.5
- [x] 1.5 `fact_latency_daily` 339 dòng/9 cột · `fact_perf_daily` 669 dòng/5 cột — **cả hai không có `source`**

## 2. Mục tiêu 1 — `unit_id`

- [x] 2.1 `connect.account_unit_lookup()` mới; `COLUMNS` thêm `unit_id`. Đối chiếu AST: **21 = 21**, đúng thứ tự
- [x] 2.2 Tra từ `account_id`, **không** từ tag. Thêm bộ đếm `khong_ro_don_vi`
- [x] 2.3 `DO UPDATE` phủ `unit_id` — 41 dòng cũ được ghi đè, không rỗng vĩnh viễn
- [x] 2.4 **0/41 → 41/41**, toàn bộ `__technical_6__`, `unit unknown 0`
- [x] 2.5 **24/24 khoá khớp, 0 lệch**; bốn nguồn không đổi một token

## 3. Mục tiêu 1 — ĐO `cached_tokens`, không vá

- [x] 3.1 `response` thô cũng ghi `cached_tokens: null` — nhưng đó là bản **đã chuẩn hoá** của LiteLLM, không phải phản hồi gốc Gemini, nên **không phân biệt được (a) với (b)**
- [x] 3.2 **Hoá đơn CÓ SKU cache**: 461 dòng / 7 SKU / 252.321.118 token. Riêng agent 6:
      **16/19 ngày có hoá đơn đều có cached** (1.596.241 token) khi gọi THẲNG Google.
      **NHƯNG không so được**: hoá đơn dừng ở **29/08**, lượt gọi Gateway ở **31/08** —
      không giao nhau. Đúng cái bẫy đã mắc ở change 006 với độ trễ, không lặp lại
- [x] 3.3 **Loại trừ được (b)**: fork `litellm_tuan_test` CÓ ánh xạ — `vertex_and_google_ai_studio_gemini.py:1760` đọc `cachedContentTokenCount` → `cached_tokens`. Google báo thì LiteLLM chuyển tiếp
- [x] 3.4 **CHƯA KẾT LUẬN ĐƯỢC — và đó là câu trả lời đúng ở thời điểm này.**
      Loại được (b). Nghiêng về (a) nhưng chưa chứng minh: 7/42 lượt có prompt ≥ 1.024 token
      (đủ ngưỡng cache ngầm) mà vẫn không có cached — hợp lý vì cache ngầm cần **tiền tố lặp
      lại**, còn DMS phân loại các phản hồi khác nhau. Phép thử quyết định là hoá đơn ngày
      31/08, **chưa về**
- [x] 3.5 **Không ghi 0**. Cột giữ NULL
- [x] 3.6 `docs/reference/nhat-ky-03-09-sang.md` **mục 5** ghi đủ kết luận: loại trừ được (b)
      (fork CÓ ánh xạ `cachedContentTokenCount`); **không** loại được (a) khỏi (c) vì `response`
      thô cũng là bản đã chuẩn hoá của LiteLLM; phép thử quyết định là hoá đơn 31/08, **chưa về**.
      Master Plan STT 7 mục tiêu 2 (dòng 20) đã ghi rõ phép kiểm cache **CHƯA THỰC HIỆN ĐƯỢC**,
      kèm lý do đo được: vế Gateway rỗng 0/41 và hoá đơn dừng 29/08 trong khi Gateway ở 31/08

## 4. Mục tiêu 1 — `output_modality` và `thinking_enabled`

- [x] 4.1 Nạp từ **`completion_tokens_details`**, không phải `prompt_tokens_details`
      (bản đầu của đề xuất trỏ nhầm khối, đo lại mới ra). Đo sau khi nạp:
      `output_modality` **38/41** (3 lượt hỏng NULL, đúng) · `thinking_enabled` **0/41** —
      xem 4.4
- [x] 4.2 Đo: `text_tokens` **42/42** · `reasoning_tokens` **2/42** · audio/image/video **0/42**.
      `fact_monitoring.output_modality` là **nhãn TEXT** (`'text'`), không phải số token — nguồn
      gateway phải theo cùng quy ước
- [x] 4.3 **Mở rộng phạm vi sau khi đo**: `thinking_enabled` (Data Out 14) nằm cùng khối
      `completion_tokens_details`, đo được **2/42** dòng có `reasoning_tokens` (=342, chính hai
      lượt nghiệm thu cache 01/09). `fact_monitoring` đã có cột BOOLEAN cùng tên. Nạp nó không
      tốn thêm gì -> **Data Out 21/26 → 23/26**, không phải 22/26. Design ⑧ đã cập nhật
- [x] 4.4 **PHÁT HIỆN KHI TRIỂN KHAI — `thinking_enabled` nạp ra 0/41, và đó là ĐÚNG.**
      Hai dòng duy nhất có `reasoning_tokens` (=342, `gemini-3.6-flash`, 31/08 18:21 UTC =
      01/09 01:21 giờ VN) mang `request_tags` chỉ có `User-Agent: Python-urllib` — **không tag
      định danh agent nào**. `resolve_agent()` trả None, mà `fact_call.agent_id` là NOT NULL,
      nên cả hai bị loại ở khâu nạp (nằm trong "dropped: no tag 6"). Một trong hai còn là lượt
      trúng cache (`request_id` hậu tố `_cache_hit…`).
      → Cột **đọc đúng**, nhưng **chưa có dữ liệu**, và sẽ chưa có cho tới khi một agent CÓ TAG
      sinh token suy luận. Đúng hình dạng của `cached_tokens`, và đúng luận điểm ① của chính
      đề xuất này: *"có cột không có nghĩa là có dữ liệu"*.
      → **"Data Out 21/26 → 23/26"** ở việc 4.3 phải đọc là *trường đã có đường nạp*, KHÔNG
      phải *trường đã có số*.
- [x] 4.5 **SỬA MỘT SAI SÓT CỦA DESIGN ⑧ (đo lại 03/09).** Design ⑧ và việc 4.3 viết
      *"`fact_monitoring` đã có cột BOOLEAN cùng tên"*. Đo thật: nó là **TEXT** mang chuỗi
      `'true'` / `'false'`. Ba con số 11.440 / 3.589 / 636.624 thì **khớp**.
      `fact_call.thinking_enabled` vẫn dùng **BOOLEAN** — đúng tiền lệ `cache_hit` ở 007 (nguồn
      TEXT `'None'`, đích BOOLEAN, dịch bằng `CASE`). Khác kiểu đã ghi vào `COMMENT ON COLUMN`
      để không ai so hai bảng mà quên dịch kiểu.
- [x] 4.6 **SAI KHÁC CÓ Ý so với công thức của design ⑧.** Design viết
      `thinking_enabled = (reasoning_tokens IS NOT NULL AND > 0)`, tức ra **false** cho 40/42
      dòng. Bộ nạp làm khác: khoá `reasoning_tokens` **vắng mặt → NULL**, không phải false.
      Gemini không gửi khoá đó cho model không suy luận, nên "vắng mặt" là *nhà cung cấp không
      nói gì* — khác hẳn *đã đo và bằng không*. Ghi false là khẳng định một phép đo chưa ai
      thực hiện. Cùng kỷ luật với `duration_ms` (006) và `cached_tokens` (việc 3.5).
- [x] 4.7 **`DO UPDATE` KHÔNG ĐỦ — phải chạy `--full`.** Chạy `load_gateway.py` trần chỉ nạp
      **6/41** dòng vì mốc nạp chỉ lùi 1 giờ; 35 dòng cũ giữ NULL. Phải `--full` mới đọc lại cả
      sổ và ghi đè đủ **41/41**.
      → Mọi lần thêm cột vào `fact_call` sau này đều phải `--full`, nếu không thì cột mới chỉ
      đầy dần từ lượt gọi MỚI. Bẫy này chưa được ghi ở đâu trước hôm nay.

## 5. Migration 008

- [x] 5.1 `008_theo_gio` ← `007_cot_bo_qua`, forward-only. `downgrade()` ném NotImplementedError
- [x] 5.2 Bảng theo giờ: khoá `(hour, agent_id, model_id, account_id, source)` — **đủ chiều như
      bảng ngày**, không rút bớt. Đã kiểm `\d`: 5 chiều, 4 khoá ngoại
- [x] 5.3 Cột `source` cho `fact_latency_daily` và `fact_perf_daily` — **phải làm TRƯỚC** khi
      đổ số Gateway vào, xem design ⑤. `source` vào **cả hai khoá chính**:
      `(day, agent_id, source)` và `(day, agent_id, method, response_code, source)`
- [x] 5.4 Dòng cũ của hai bảng đó nhận `DEFAULT 'monitoring'` — đúng nghĩa, vì chúng thật sự là
      của monitoring (khác `outcome` ở 006, nơi DEFAULT sẽ là bịa). 339 + 669 dòng nhận đúng.
      Hai bộ nạp nay khai `source` **tường minh**, không dựa vào DEFAULT — DEFAULT chỉ để đắp
      dòng lịch sử
- [x] 5.5 `COMMENT ON COLUMN` cho mọi cột mới, nêu rõ NULL nghĩa là gì — 6 COMMENT + 1 COMMENT ON TABLE
- [x] 5.6 Nghiệm thu: **24/24 khoá khớp, 0 lệch**; head = `008_theo_gio`

## 6. `db/build_usage_hourly.py`

- [x] 6.1 Dựng từ `fact_call` (app + gateway) và `fact_monitoring`. `db/build_usage_hourly.py`
- [x] 6.2 **KHÔNG có nguồn `billing`** — hoá đơn Google chỉ tính theo ngày, xem design ③.
      Bộ nạp `SystemExit` ngay nếu `billing` xuất hiện, không đợi ai đọc số tiền theo giờ
- [x] 6.3 Lọc `outcome = 'success'` và `cache_hit IS NOT TRUE`, đúng như `build_usage_daily`
- [x] 6.4 Thêm vào `scripts/rebuild_db.py` — **8 → 9 bước**. Thiếu bước này thì mỗi lần cập nhật
      dashboard là bảng theo giờ biến mất (bẫy đã ghi ở `rebuild_db.py` mục "So Gateway").
      Docstring liệt kê bước cũng đã cập nhật
- [x] 6.5 **3.327 dòng** — monitoring 2.624 · app 698 · gateway 5, trên **1.751 giờ / 153 ngày**.
      Nằm TRONG khoảng ước lượng 3.000–7.700, gần cận dưới. Hệ số so bảng ngày:
      3.327/1.990 = **1,67 lần** — THẤP HƠN cả ba cách đếm ở mốc 1.4 (3,8–6,9), vì ước lượng
      đó đếm trên `fact_monitoring` thô còn bảng thật gộp theo `account_id` neo

## 7. Phân vị chính xác cho Gateway

- [x] 7.1 `db/build_performance.py` tính p50/p95/p99 từ `duration_ms` thô —
      `load_gateway_latency()`, dùng `percentile_cont`
- [x] 7.2 `p95_bucket_from` / `p95_bucket_to` **để NULL** cho nguồn gateway. Đo: gateway
      **0/1** dòng có ô, monitoring **339/339** có ô. Nghiệm thu trong chính bộ dựng sẽ
      rollback nếu dòng gateway mang ô
- [x] 7.3 Giữ `MIN_SAMPLES = 10`, không đổi. Dòng gateway 38 mẫu → `enough_samples = true`
- [x] 7.4 Mỗi nguồn một dòng. Thêm phép kiểm mới: `(day, agent_id, source)` không được
      trùng — 0 khoá trùng
- [x] 7.5 **p95 = 1,822 s** — KHỚP ĐÚNG con số change 006 tính tay.
      Kèm p50 **0,788 s** · p99 **2,702 s** · 38 mẫu · ô histogram NULL

## 8. Endpoint đọc theo giờ

- [x] 8.1 `store.usage_hourly()` + `GET /api/usage-hourly`. Trả thêm `sources` (đếm dòng theo nguồn) để người gọi thấy ngay nguồn nào có mặt
- [x] 8.2 Thiếu `start` **hoặc** `end` đều trả **400**, thông báo nêu đích danh tham số thiếu kèm một ví dụ gọi đúng
- [x] 8.3 Dùng `store.open_db()` như 9 endpoint kia — không mở đường kết nối riêng nào
- [x] 8.4 `theo_gio()` — 6 phép: ba lời gọi thiếu tham số đều phải **400**, không có nguồn
      `billing`, mọi giờ cắt đúng đầu giờ, ngày 31/08 có dữ liệu.
      Chạy đầy đủ: **25 kiểm · 25 đạt · 0 hỏng**
- [x] 8.6 **PHÁT HIỆN — `check_api.py` mang một phép kiểm LỖI THỜI từ 31/08, hôm nay mới bắt.**
      `against_database()` so tiền của API với **riêng** `fact_billing_daily`, trong khi
      migration 005 (`gateway_cost_vao_view`, 31/08) đã **cố ý** đổ tiền Gateway vào
      `usage_resolved.cost_usd`:

          fact_billing_daily              $307,360850
          usage_resolved                  $307,382155
          gateway trong fact_usage_daily    $0,021305   <- ĐÚNG BẰNG chênh lệch

      `scripts/audit_db.py` đã được sửa theo từ 31/08 (*"Cost: invoice + gateway =="*), file
      này thì không — nên nó báo HỎNG trong khi **cả hai vế đều đúng**.
      **Không nới ngưỡng.** Sửa CÔNG THỨC cho khớp định nghĩa mới của view, dùng đúng phép của
      `audit_db.py` (chỉ cộng tiền Gateway của khoá **không** có dòng hoá đơn tương ứng, nếu
      không là đếm hai lần). Đây là trường hợp duy nhất được phép sửa một phép kiểm: chứng minh
      được **bản thân phép kiểm sai**, không phải dữ liệu không vừa ý nó.
      → Đóng luôn một mục Master Plan STT 7 đang treo: *"Còn: backend/check_api.py"*
- [x] 8.5 `git diff --stat web/` **rỗng**

## 9. `scripts/audit_db.py`

- [x] 9.1 `Hourly totals match daily totals` cho **từng nguồn**: gateway ĐẠT · monitoring ĐẠT ·
      app so với **chính phần xuống được giờ** của nó (`fact_call`), vì TLA Hợp Đồng nằm ở
      `fact_app_daily` gộp sẵn theo ngày. Gộp chung thành một con số là biến một sự thật đã
      biết thành báo động giả
- [x] 9.2 `No billing rows in the hourly table` — chặn ở **cả hai tầng**: bộ dựng `SystemExit`, audit kiểm lại
- [x] 9.3 `Every gateway row has unit_id` — 41/41
- [x] 9.4 `Raw percentiles have no histogram bucket` — gateway 0/1 mang ô. Thêm phép **ngược
      lại**: `Interpolated percentiles keep their bucket` (monitoring 339/339 giữ ô) — thiếu ô
      thì p95 nội suy trông y như một số chính xác
- [x] 9.5 **54 kiểm · 50 đạt · 4 lưu ý · 0 hỏng** (mốc trước: 42 · 38 · 4 · 0).
      Thêm 12 phép, tất cả ĐẠT; **4 lưu ý giữ nguyên** — đúng bốn khoảng trống dữ liệu đã biết,
      không phát sinh cái mới

## 10. Nghiệm thu

- [x] 10.1 **Sửa kỳ vọng: 10/10 bước**, không phải 9/9. Change
      `answer-what-each-agent-did-on-a-day` (việc 2.4) thêm bước kiểm quyền vai đọc thành bước
      10. Chín bước nạp đều ĐẠT nghiệm thu riêng; bước 10 **CỐ Ý hỏng** ở lần chạy đầu (xem
      10.2) — sau `docker compose up -d api` thì `--from-step 10` cho
      *"all 10 steps passed their acceptance checks"*
- [x] 10.2 Đối soát **37 khoá** với mốc chụp trước khi đổi: **KHỚP 37, LỆCH 0**.
      `usage_resolved` giữ nguyên **915.969.971 token · 122.504 calls · $307,382155**.
      Bước 10 hỏng đúng như thiết kế: `api_readonly` mất **26/26** bảng+view và mất `USAGE`
      trên schema — chính là lỗ hổng mà bước đó sinh ra để bắt
- [x] 10.3 Chạy **hai lần liên tiếp**, so 7 khoá: **KHỚP 7/7, LỆCH 0**.
      `fact_usage_daily` 1.990 · `fact_usage_hourly` 3.327 · `fact_call` 8.672 ·
      `fact_latency_daily` 340 · `fact_perf_daily` 669 · token 915.969.971 · calls 122.504.
      Lần hai cũng dừng ở bước 10 — **tái lập được**, không phải chuyện ngẫu nhiên một lần
- [x] 10.4 Bộ dựng tự đối chiếu mỗi lần chạy và **dừng hẳn nếu lệch** — cả hai lần rebuild đều
      in *"hourly totals match daily totals for all 3 sources"*. `audit_db.py` nhóm F kiểm lại
      độc lập ở tầng khác, cũng ĐẠT cả ba
- [x] 10.5 Đo thật trên 41 dòng gateway:

          unit_id           41/41   ĐẠT
          output_modality   38/41   ĐÚNG, KHÔNG phải 41/41 như việc này viết —
                                    3 dòng rỗng là 3 LƯỢT HỎNG, và lượt hỏng
                                    không có phản hồi nên không có modality nào
                                    để dán nhãn. Ghi 'text' cho chúng là bịa.
          thinking_enabled   0/41   ĐÚNG như vậy — xem việc 4.4
          cached_tokens      0/41   ĐÚNG như vậy — xem việc 3.4

      Kỳ vọng "41/41" của việc này được viết TRƯỚC khi biết 3 lượt hỏng cũng nằm trong
      `fact_call`. Sửa kỳ vọng, **không** sửa dữ liệu.

## 11. Tài liệu

- [x] 11.1 `docs/reference/nhat-ky-03-09-sang.md` — 9 mục. Gồm kết luận việc 3 (mục 5), bốn
      phát hiện ngoài dự tính (mục 6), và một phép đo ngoài lề trả lời được câu đang treo của
      change kế tiếp (mục 8)
- [x] 11.2 **Mục 5** thêm khối `completion_tokens_details` — 7 khoá kèm số đo, bảng suy ra hai
      cột, và ba cảnh báo (0/41 là ĐÚNG · vì sao NULL chứ không `false` · khác kiểu với
      `fact_monitoring`). **Mục 7** thêm hai nhánh mới, sửa `6/8` → `6/9`, và ghi hai bẫy:
      `refresh_gateway.py` **chưa** gọi hai bước mới nên cũ đi một nhịp; thêm cột vào `fact_call`
      thì phải `--full`
- [x] 11.3 Ba ô cột `Kết quả`: dòng 11 (STT 4 mt1, nối thêm) · dòng 12 (STT 4 mt2,
      **"Chưa làm" → "Xong 03/09/2026, sớm 27 ngày so với mốc"**) · dòng 20 (STT 7 mt2).
      Bản lưu `docs/reference/ban-luu/Master Plan API Gateway 2026-09-03.xlsx` trước khi sửa.
      Mở **không** `data_only=True` (bật là mất công thức vĩnh viễn). KHÔNG đổi cột `Mốc hoàn
      thành` — xoá mốc kế hoạch là mất bằng chứng về đích sớm; KHÔNG tô ô Gantt.
      **KHÔNG ghi `thinking_enabled` là "đã xong"**: nó có đường nạp nhưng 0/41 số
- [x] 11.4 Thêm mục `fact_usage_hourly` (11 cột, bảng đối chiếu giờ↔ngày, vì sao bảng riêng),
      cột `source` cho `fact_perf_daily` và `fact_latency_daily` kèm khối *"hai cách tính phân vị
      hoàn toàn khác nhau"* — đọc `source` cùng `p95_bucket_*` để biết độ tin cậy, và ghi lại
      chênh lệch 31,9 lần **chưa giải thích được**
