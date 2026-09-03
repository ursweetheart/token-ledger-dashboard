# Tasks

Quy ước: mỗi mục đo được thì **ghi số đo ngay tại chỗ**, không ghi "đã kiểm tra".

Thứ tự: nhóm **1, 2, 3** làm được **ngay** — không phụ thuộc gì và không đụng file nào của
change khác. Nhóm **4, 5** **chặn** cho tới khi việc 5.3 và 7.1–7.5 của
`fill-the-declared-fields-and-log-by-the-hour` xong — xem design ⑨. Nhóm **6** làm sau cùng, vì
việc 6.4 cần số đo thật của nhóm 3 và 5.

Nhóm 2 đứng trước nhóm 3: nó sửa một thứ **đang hỏng**, còn nhóm 3 là thêm năng lực mới.

## 1. Ghi mốc trước khi đổi

- [x] 1.1 `var/baseline-truoc-chieu-account.json` — 7 nhóm khoá. `usage_resolved`
      **token 915.969.971 · calls 122.504 · $307,382155**; account theo `kind`; số dòng 12 bảng;
      `latency_by_source` (monitoring 339 · gateway 1); độ phủ `/api/health`
- [x] 1.2 Đo lại sau khi change trước đã áp: **337 dòng · 2 agent · 53 account · 108.554.843
      token · 14/03 → 29/08** — **không đổi một token nào**. Đây là con số phải vượt qua
- [x] 1.3 Bốn chỗ hiển thị đều ăn từ **cùng một** bộ số, nên chụp chính bộ số đó thay vì chụp
      màn hình. `A.lat` (trung bình có trọng số theo request, `app.js:1155,1172`) = **13,8002 s**.
      p95 từng agent: 1→13,1092 · 2→12,6311 · 3→6,3014 · 4→14,05 · 5→45,6006 · 6→**61,451** ·
      7→49,8854.
      **Ghi nhận quan trọng:** dòng gateway ngày 31/08 hiện **KHÔNG ảnh hưởng** con số nào —
      `fact_perf_daily` không có dòng nào cho (31/08, agent 6) nên trọng số của nó bằng **0**
- [x] 1.4 **CHỨNG MINH ĐƯỢC — không còn là suy luận.** Đo cả hai đầu ngày 03/09:

          truoc `docker compose up -d api`   USAGE = false   doc duoc  0/24
          sau                                USAGE = true    doc duoc 24/24

      (`rebuild_db.py` gây ra trạng thái đầu là lần chạy **02/09**, không phải lần tôi chạy —
      bằng chứng tương đương, và ghi rõ như vậy.) Bảng mới `fact_usage_hourly` cũng tự có
      quyền: `read-only-api.sql` cấp theo `ALL TABLES IN SCHEMA`, không phải khai từng bảng.
      **Nhưng nó KHÔNG làm lỗ hổng biến mất** — đây là cách chữa thủ công *sau khi đã hỏng*,
      và nó đòi có người biết mà chạy. Design ④ cập nhật theo

## 2. Kỷ luật chỉ-đọc sống sót qua `rebuild_db.py`

- [x] 2.1 Tách thành **hai hàm riêng**, không phải hai nhánh trong một hàm:
      `con_doc_duoc()` (mới) và `read_only()` (giữ nguyên chức năng cũ, thu hẹp docstring cho
      đúng câu nó trả lời). Cả hai chạy cạnh nhau ở nhóm "Read-only"
- [x] 2.2 `SELECT COUNT(*) FROM ref_source` — bảng nhỏ nhất có thật (4 dòng). Đọc nó đòi
      **cả** `USAGE` trên schema **lẫn** `SELECT` trên bảng, đúng hai quyền mà `DROP SCHEMA` xoá.
      Chạy: **26 kiểm · 26 đạt · 0 hỏng** (mốc trước 25/25)
- [x] 2.3 **Tái tạo được, và kết quả đúng từng chi tiết.** Chạy `rebuild_db.py` (API mù thật:
      `/healthz` 200 nhưng `/api/health` **500**), rồi `check_api.py`:

          [ FAIL ] The API server can still READ the database      <- phep MOI
          [  ok  ] The local check connection can READ (vai `token`)
          [  ok  ] The backend connection is read-only             <- phep CU, VAN DAT

      Phép cũ báo ĐẠT trong khi API mù hoàn toàn — **chứng minh nó mù**. Phép mới hỏng kèm
      chẩn đoán đúng nguyên nhân và hai lệnh chữa.
- [x] 2.4 Bước **10/10** `scripts/check_db_grants.py`, chạy được cả **độc lập**. Trả `exit 1`
      kèm hướng dẫn `docker compose up -d api`. **KHÔNG tự cấp lại** — có chủ ý
- [x] 2.5 Hỏi thẳng catalog: `has_schema_privilege` + `has_table_privilege` cho **từng** bảng
      và **từng** view (`information_schema.tables`), không thử một bảng. Chạy thử đường lành:
      **24/24 đọc được**.
      Đường hỏng đã thử và sửa một lần: bản đầu gộp *"vai không tồn tại"* với *"vai mất quyền"*
      vào **một** thông điệp nói `DROP SCHEMA` là thủ phạm — **sai**, `DROP SCHEMA` xoá GRANT
      chứ không xoá vai. Nay tách hai nhánh, hai cách chữa khác nhau
- [x] 2.6 **Sửa kỳ vọng: 9 → 10 bước, không phải 8 → 9.** Change trước
      (`fill-the-declared-fields…` việc 6.4) đã thêm `build_usage_hourly` thành bước 8, nên khi
      viết task này con số 8 đã cũ. Docstring liệt kê bước đã cập nhật, kèm đoạn giải thích vì
      sao bước 10 phải đứng cuối và vì sao nó báo động thay vì tự chữa.
      Đổi kèm: `STEPS` nay mang **đường dẫn tương đối ROOT** (`db/…`, `scripts/…`) thay vì chỉ
      tên file — bộ chạy trước đây ghép cứng `ROOT / "db" / filename`, mà bước 10 nằm ở
      `scripts/`
- [x] 2.7 Đo hai đầu, hai lần rebuild đều giống nhau:

          sau rebuild_db.py            USAGE = false   doc duoc  0/26
          sau docker compose up -d api USAGE = true    doc duoc 26/26

      **26 chứ không phải 23** (mốc 02/09 là 20 bảng + 3 view): thêm `fact_usage_hourly` và
      hai view mới. `read-only-api.sql` cấp theo `ALL TABLES IN SCHEMA` nên bảng/view mới tự có
      quyền, không phải khai thêm

## 3. View chiều account cho cả 8 agent

- [x] 3.1 `usage_by_account_resolved`, migration **009** ← `008_theo_gio`. Hai CTE `t` và `c`,
      mỗi nhánh JOIN theo đúng `*_source` của nó
- [x] 3.2 `FULL OUTER JOIN`. Chênh lệch số dòng chứng minh nó cần thiết: JOIN một nhánh cho
      **1.442** dòng, hai nhánh cho **1.453** — đúng **11** dòng chỉ-có-calls
- [x] 3.3 `FULL OUTER JOIN ... ON` bốn chiều, khoá gộp bằng `COALESCE(t.<cột>, c.<cột>)`
- [x] 3.4 Đo trên view thật: **token 915.969.971 = 915.969.971** · **calls 122.504 = 122.504**.
      Cả hai lệch 0. Thành **hai phép kiểm riêng** trong `audit_db.py` nhóm G, không gộp một
- [x] 3.5 **1.453 dòng · 8/8 agent · 60 account.** Từng agent:
      Chatbot Contact Center 1 acc/216 ngày · Sale Agent 1/240 · Multi modal AI Invoice 1/105 ·
      TLA Hợp Đồng **25**/63 · Ralli **31**/148 · CRM 1/53 · DMS 1/25 · Tools Quizzer 1/8
- [x] 3.6 Giữ cả hai. Đo trên view: `whole_agent` 38 dòng / **15.230.908** / **1,7%** ·
      `unattributed` 34 dòng / **4.220.527** / **0,5%**. Thêm phép kiểm mức CẢNH BÁO — mất
      chúng thì độ phủ trông như 100%
- [x] 3.7 **Ba con số khớp tuyệt đối**, và đây là bằng chứng mạnh nhất có được mà không cần
      nguồn thứ ba — `/api/health` đi từ `usage_resolved`, KHÔNG qua `account`:
      people **107.125.668** · service **793.613.395** · opaque **15.230.908**.
      Thành ba phép kiểm trong `audit_db.py` nhóm G
- [x] 3.8 View cũ **nguyên vẹn**. Thêm `COMMENT ON VIEW` cho **cả hai**, nói rõ view nào trả
      lời câu nào, và vì sao view cũ phải giữ (`tools/baseline_db.py`,
      `tools/dien_tap_gateway.py` đọc nó làm mốc lịch sử). Phép kiểm mới canh view cũ vẫn đọc được
- [x] 3.9 Đổi nguồn đọc, giữ tên endpoint. Trả thêm 4 cột: `kind`, `cached_tokens`,
      `token_source`, `call_source`. Đo qua HTTP: **1.453 dòng · 8 agent · 60 account ·
      token 915.969.971 · calls 122.504**
- [x] 3.10 Cả ba đọc bảng `account`, không đọc view, nên không đụng gì. Chạy thật để chắc:
      `anchor_accounts()` trả **8/8 agent**, không raise; hai phép kiểm audit đều ĐẠT
- [x] 3.11 Nhóm **G. Account dimension**, 10 phép: hai phép tổng (token, calls) · độ phủ agent ·
      hai phép `whole_agent`/`unattributed` còn nhìn thấy · ba phép chéo kiểm `/api/health` ·
      một phép canh view cũ còn đọc được · một dòng ghi phân bố theo `kind`.
      Audit đầy đủ: **64 kiểm · 60 đạt · 4 lưu ý · 0 hỏng** (mốc trước 54/50/4/0)
- [x] 3.12 Đo qua HTTP: **98,3% = 11,7% người thật + 86,6% tài khoản dịch vụ**, **1,7%** không
      quy được. **Không dịch một con số nào**
- [x] 3.13 Rà đủ 14 chỗ. **11 chỗ vẫn đúng** (chúng nói về `model_id`, về `cost_usd`, về việc
      là SỐ ĐO — không chỗ nào khẳng định độ phủ). **3 chỗ phải sửa**:

      - `app.js:403` — **nguy hiểm nhất, và không chỉ là chú thích sai.** Nó mô tả một giả định
        mà **chính khối mã ngay dưới đang dựa vào**: *"tài khoản dịch vụ không có dòng nào ở đó
        — vòng lặp trên để chúng bằng 0"*. Nay chúng CÓ 1.057 dòng.
        **Đã đo trước khi kết luận an toàn:** phép gán là `=` chứ không phải `+=` nên nó GHI ĐÈ,
        không cộng dồn → **không đếm hai lần**. Và so hai đường qua HTTP cho cả 8 agent:
        **0/8 lệch** trên `calls`, `input_tokens`, `output_tokens`. Giữ khối mã làm đường lui,
        viết lại chú thích cho đúng sự thật mới.
        **Thứ ĐỔI THẬT:** `costDerived` / `byModel` / `costRows` nay được điền cho tài khoản
        dịch vụ (trước rỗng) — cải thiện, vì sáu agent đó vốn CÓ tiêu tiền mà trước hiện 0.
      - `app.js:1596` — *"chỉ những nguồn biết người dùng (ref_source.knows_user)"*: sai từ 03/09.
      - `app.js:3223` — bổ sung ghi chú **ĐỔI HÀNH VI**: biểu đồ "Người dùng hoạt động theo ngày"
        nay phủ 8/8 agent, đường cong **nhảy lên** vì dữ liệu mới chứ không phải lỗi; và nói rõ
        đây là đếm **TÀI KHOẢN**, không phải đếm người ngoài đời.

      `node --check` sạch cả `app.js` lẫn `api.js`
- [x] 3.14 **Xác nhận bằng đo, không giả định**: gọi HTTP và kiểm khoá của dòng đầu —
      `'cost_usd' in rows[0]` trả **False**. Hai chú thích vẫn đúng, giữ nguyên.
      View cố ý không có cột tiền: tiền chỉ tồn tại ở mức (ngày, agent, model); chia đều cho các
      tài khoản là bịa ra một con số không nguồn nào từng báo cáo — đã ghi vào `COMMENT ON VIEW`

## 4. `latency_resolved` — CHẶN cho tới khi việc 5.3 + 7.1–7.5 của change kia xong

- [x] 4.1 Điều kiện đủ: change `fill-the-declared-fields…` đã áp xong. Cột `source` có, và
      `fact_latency_daily` có **monitoring 339 · gateway 1**
- [x] 4.2 `latency_resolved`, migration **010** ← `009_chieu_account`. Đo:
      **340 dòng view = 340 khoá riêng = 340 dòng bảng**, khoá trùng **0**
- [x] 4.3 `CASE WHEN m.day IS NOT NULL THEN 'monitoring' ELSE 'gateway' END` — **một dòng
      duy nhất** quyết định thứ tự; đổi nó là đảo chiều, không chỗ nào khác phải sửa. SQL ghi đủ
      ba phép loại trừ, hai giả thuyết còn sống, và phép đo sẽ trả lời.
      **Chứng minh đường lui chạy:** ngày 31/08 monitoring không có dòng nào →
      `latency_source = 'gateway'`, p95 **1,822 s**, ô histogram NULL
- [x] 4.4 Có trong view (`monitoring=339 · gateway=1`), và **KHÔNG** trả ra API — kiểm qua
      HTTP: `'latency_source' in row` là **False**
- [x] 4.5 Hai cột chảy qua view. Đo: **1/340** dòng không có ô — đúng dòng gateway. Phép kiểm
      `Latency: p50<=p95<=p99 and p95 sits inside its own bucket` vẫn ĐẠT
- [x] 4.6 Đổi nguồn đọc, kèm chú thích nêu rõ vì sao (`api.js:187` gán đè, `ORDER BY` không
      có tie-break trên nguồn) và vì sao **không** trả `latency_source` ra API
- [x] 4.7 Thêm **4** phép, không phải một: khoá không trùng · view không mất khoá nào
      (340 = 340) · **mọi cột lấy từ CÙNG một nguồn** (bắt trường hợp trộn p50 nguồn này với p95
      nguồn kia) · một dòng ghi phân bố theo nguồn.
      Audit đầy đủ: **68 kiểm · 64 đạt · 4 lưu ý · 0 hỏng** (mốc trước 64/60/4/0)

## 5. Tầng đọc hết ghi đè — CHẶN cùng nhóm 4

- [x] 5.1 **Xác nhận bằng số qua HTTP**: `/api/performance` trả **340 dòng · 340 khoá riêng ·
      0 khoá xuất hiện quá một lần**. Nên `d.lat = …` không còn ghi đè lên gì.
      **KHÔNG sửa `api.js`** — không cần: sửa ở tầng dữ liệu là đủ, và một dòng JS không sửa là
      một dòng không thể sửa hỏng
- [x] 5.2 Tính lại `A.lat` **đúng cách app.js tính** (gán đè theo khoá rồi trung bình có trọng
      số theo request), lấy dữ liệu qua HTTP: **13,8002** — **khớp tuyệt đối** mốc 1.3.
      p95 từng agent cũng khớp cả bảy: 13,1092 · 12,6311 · 6,3014 · 14,05 · 45,6006 · 61,451 ·
      49,8854. **Không một con số nào đổi** — đúng như thiết kế ưu tiên `monitoring` nhắm tới
- [x] 5.3 Phản hồi `/api/performance` có đúng 9 cột, **không** có `latency_source`. Không thêm
      nhãn, không thêm tooltip, không đụng bốn chỗ hiển thị
- [x] 5.4 `git diff web/js/app.js` không có dòng nào chạm `latW` / `latR` / `a.lat`. Thay đổi
      duy nhất ở `app.js` là **chú thích**
- [x] 5.5 `latencyWarning: null` · `latencyCritical: null` — vẫn tắt. Nên không cảnh báo nào tự
      đổi trạng thái theo con số này. **Phải kiểm lại điều này trước khi đảo chiều ưu tiên nguồn**

## 6. Master Plan và tài liệu

- [x] 6.1 Cột **Sản phẩm** dòng 16 sửa thành *"Phép kiểm đối chiếu nguồn, chạy trong quá
      trình phát triển để kiểm soát logic và thuật toán. KHÔNG phải báo cáo giao nộp."*
      Lý do đo được ghi ở cột Kết quả: **0 ngày** có đủ bốn nguồn — ngày duy nhất có Gateway
      (31/08) thì billing và monitoring dừng ở 29/08, app ở 30/08
- [x] 6.2 Ghi thẳng vào cột Kết quả dòng 16: ràng buộc đó **gỡ khỏi đường găng của STT 6**,
      vẫn là sản phẩm của **STT 7 dòng 19**. **Không** đụng dòng 19 — kiểm lại sau khi ghi,
      ô (19,5) còn nguyên *"Kỳ chạy song song Gateway và ba nguồn cũ, tối thiểu 2 tuần."*
- [x] 6.3 Cột **Sản phẩm** dòng 18: *"tỷ lệ áp dụng theo phòng ban"* → *"theo agent"*.
      Đổi **đúng một chữ**, không đụng hai biểu đồ còn lại
- [x] 6.4 Ba ô cột Kết quả. Dòng 17 trước đây **để trống**, nay ghi **XONG 03/09/2026, sớm 34
      ngày** (cả hai vế: endpoint mới, và lỗ hổng chỉ-đọc đã bịt + tái tạo được).
      Dòng 18 ghi **2/3 biểu đồ** — **KHÔNG ghi "Xong"**: biểu đồ chi phí vẫn khoá theo
      `primaryUnit()` nên 130 đơn vị chỉ ra 8 lát, không lát nào là một phòng ban.
      Bản lưu `docs/reference/ban-luu/Master Plan API Gateway 2026-09-03-truoc-stt6.xlsx`.
      Kiểm sau khi ghi: 3 sheet nguyên, `dims A1:AD27` không đổi, `wrap_text` đúng, các ô
      khác còn nguyên. **Không** đổi cột `Mốc hoàn thành` (xoá mốc 07/10 là mất bằng chứng
      "sớm 34 ngày"), **không** tô ô Gantt
- [x] 6.5 Ghi ở **hai chỗ**, phục vụ hai loại người đọc:
      `docs/reference/nhat-ky-03-09-sang.md` **mục 4** (mạch câu chuyện, đủ ba phép loại trừ,
      bảng bão hoà ô cuối theo từng agent) và `docs/reference/tu-dien-database.md` mục
      `latency_resolved` (chỗ người tra bảng sẽ nhìn vào). Cả hai ghi rõ **chưa kết luận được**
      và nêu phép đo sẽ trả lời
- [x] 6.6 Thêm `usage_by_account_resolved` (vì sao không sửa view cũ · bảng
      `token_source × call_source` giải thích JOIN hai lần · phân bố theo `kind` · chéo kiểm
      `/api/health` · vì sao không có `cost_usd`) và `latency_resolved` (bẫy gán đè ở
      `api.js:187` · ý nghĩa `latency_source` · **cảnh báo ưu tiên nguồn là lựa chọn tạm**).
      Thêm khối ⚠ ở đầu mục `usage_by_account` cũ trỏ sang view mới

## 7. Nghiệm thu cuối

- [x] 7.1 **KHỚP 37 khoá, LỆCH 0** — kể cả sau hai lần dựng lại toàn bộ database
- [x] 7.2 **68 phép · 64 đạt · 4 lưu ý · 0 hỏng.** Mốc đầu buổi là 42/38/4/0 — thêm **26 phép**
      qua hai change, tất cả ĐẠT, và **4 lưu ý giữ nguyên**: không phát sinh khoảng trống mới
- [x] 7.3 **27 phép · 27 đạt · 0 hỏng.** Và ngay sau `rebuild_db.py` nó **HỎNG ĐÚNG CHỖ** —
      đó mới là điều cần chứng minh, không phải luôn xanh
- [x] 7.4 **1.453 dòng · 8/8 agent · 60 account · token 915.969.971 · calls 122.504** —
      đo lại sau khi dựng lại database từ đầu
- [x] 7.5 `A.lat` **13,8002 = 13,8002**; p95 từng agent **lệch 0/7**.
      Không một con số nào đổi — đúng như thiết kế ưu tiên `monitoring` nhắm tới
