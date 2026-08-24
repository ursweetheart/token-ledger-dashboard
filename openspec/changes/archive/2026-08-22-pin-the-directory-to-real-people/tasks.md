# Tasks

## 1. Mốc đo — ĐÃ CÓ, ghi lại để không phải dựng máy chủ lần nữa

Đo ngày 22/08/2026 bằng uvicorn thật + `app.js` thật, A/B trên đúng một dòng, đã hoàn
nguyên bằng `git checkout -- backend/store.py`.

- [x] 1.1 `SELECT kind, COUNT(*) FROM account GROUP BY kind`:
      `real` **937** · `service_account` **6** · `unattributed` **8** · `whole_agent` **2**
- [x] 1.2 Sáu dòng `service_account` nguyên văn: `unit_id = "__technical_<aid>__"` ·
      `is_shared = 1` · `in_directory = 0` · `is_enabled = NULL` ·
      `full_name = "Cả <tên agent>"` · `username = svc.<dim_agent.code>`
- [x] 1.3 Cả 6 dòng **qua được** `JOIN dim_unit` lẫn `JOIN dim_agent` — bộ lọc `kind` là
      thứ duy nhất chặn ở tầng SQL
- [x] 1.4 A/B qua harness: `REAL_ACCOUNTS` 937 → **943**, `USER_ACCOUNTS` 937 → **943**,
      bị vứt **0**, `svc.*` sống sót **0 → 6**, User hoạt động **26/937 → 26/943**,
      đơn vị kỹ thuật trong `ORG_UNITS` **0** cả hai lần
- [x] 1.5 Cơ chế lọt: `unitById("__technical_1__")` → không có, nhưng
      `unitOf("Đơn vị sử dụng …")` **trả ra** đơn vị `auto:` — tạo mới nếu chưa có, trả bản
      cũ nếu đã có. Ở đây là vế thứ hai (xem 1.6), nên `u.unitId` không bao giờ rỗng và
      `.filter()` không loại được dòng nào
- [x] 1.6 **Đếm lại thì bản đầu SAI.** Bản đầu viết *"bỏ bộ lọc → 6 phòng ban mới mọc ở
      cấp gốc"*. Đo ra: **đơn vị gốc 11 → 11**, trong đó **tự tạo 7 → 7**. Sáu đơn vị
      *"Đơn vị sử dụng …"* cộng *"Chưa quy được"* **đã có sẵn từ trước**, do các dòng
      usage chế ra chứ không phải danh bạ. Change này không thêm phòng nào
- [x] 1.7 `DEPT_PROVISIONED` **101 đơn vị / 3.693 — không đổi**, vì
      `rebuildProvisionedFromDirectory()` lọc `in_directory && !is_shared`
      **trước khi** gọi `unitOf()`
- [x] 1.8 Tử số tỷ lệ áp dụng **26 không đổi** — `is_shared=1` + `in_directory=0` đã đủ
      loại chúng khỏi `eligible = inDirectory && !shared`
- [x] 1.9 Hai tiêu chí phân biệt an toàn: tiền tố `"Cả "` ở `full_name` chỉ có ở
      `service_account` (6) và `whole_agent` (2) — **0 người thật**; tiền tố `svc.` ở
      `username` — **0 người thật**
- [x] 1.10 Harness chưa sửa, chạy 22/08: **exit 0**, in "nạp OK" 2 lần, nhật ký uvicorn
      **0 lần gọi `/api/`**, `conn-text = "Chưa nhập khoá"`, `freshness-text` rỗng
- [x] 1.11 Mốc bộ kiểm hôm nay: `check_api.py` **18/18** · `audit_db.py` **36 phép,
      31 đạt, 5 lưu ý, 0 hỏng** · JS **6 + 11**, 0 fail

> **Hại thật, sau khi trừ đi những gì đo ra là không đổi:** sáu dòng *"Cả &lt;tên
> agent&gt;"* hiện trong bảng danh bạ, và mẫu số thẻ "User hoạt động" 937 → 943
> (2,77% → 2,76%). Change vẫn đúng, nhưng lý do là *"một dòng chịu lực không tên, không
> phép kiểm"*, không phải *"sắp vỡ màn hình"*.

## 2. Ghi chú tại chỗ ở `backend/store.py`

- [x] 2.1 Ngay trên dòng `WHERE a.kind = 'real'` (:207): nói rõ đây là thứ **duy nhất**
      chặn, kèm bảng 937/943 và kèm hai chỗ **không** đỡ (`api.js:216` chặn đơn vị chứ
      không chặn tài khoản; `.filter(u => u.unitId)` bị `unitOf()` vô hiệu hoá)
- [x] 2.2 Ghi cả **lý do không phơi** 6 tài khoản đó lên: chúng sẽ rơi vào sáu đơn vị
      `auto:` không có `parent` và không ai chủ động tạo, nên phải quyết chỗ đứng trong
      cây trước; và hôm nay `adoption()` đã trả lời được câu hỏi mà chúng sinh ra để trả
      lời
- [x] 2.2b Ghi rõ mức độ: ghi chú MUST NOT nói quá thành "sập màn hình". Hại đo được là
      6 dòng trong danh bạ + mẫu số 937→943. Nói quá thì người sau đọc xong sẽ nới bộ lọc
      để "thử xem có sập thật không"
- [x] 2.3 Sửa docstring `accounts()` (:192-194) — bỏ câu *"máy chủ này vẫn chưa có xác
      thực nào"*, thay bằng trạng thái đúng: khoá dùng chung từ 21/08, và việc bớt dữ
      liệu vẫn là phòng thủ theo chiều sâu chứ không thay cho xác thực
- [x] 2.4 Đọc lại bằng mắt trước khi chạy: ghi chú KHÔNG được nhắc số dòng cụ thể của
      `api.js`/`app.js` — số dòng trôi, tên hàm thì không

## 3. Phép kiểm trong `backend/check_api.py`

- [x] 3.1 Thêm phép kiểm: `/api/accounts` không trả dòng nào có `kind <> 'real'`. Kiểm
      bằng **dữ liệu trả về**, không bằng cách đọc mã nguồn
- [x] 3.2 Thông điệp khi hỏng phải nói được **dòng nào** lọt (in `username` + `kind` của
      tối đa 5 dòng đầu), không chỉ nói "có dòng lạ"
- [x] 3.3 Kiểm ngược (negative control): tạm nới bộ lọc, xác nhận phép kiểm **kêu**.
      **KHÔNG dùng `git checkout` để hoàn nguyên** — `store.py` lúc này đã mang ghi chú
      của §2, checkout là xoá mất. Đảo ngược đúng một dòng bằng `sed`.
      Kết quả: exit **1**, phép kiểm mới báo hỏng và in đủ 6 tên
      `svc.*(service_account)`. **19 phép | 17 đạt | 2 hỏng**
- [x] 3.7 **Phát hiện khi kiểm ngược:** cái hỏng thứ hai là phép kiểm CŨ
      `So tai khoan khop` — nó cũng bắt được, nhưng phần chi tiết là **chuỗi rỗng** nên
      in ra một dòng trắng. Đã vá: in `api N != db M (db dem kind='real')`, kèm ghi chú
      nói rõ nó soi gương bản cài đặt nên không thay được phép kiểm tính chất
- [x] 3.4 **KHÔNG có số tổng nào gõ cứng** trong `check_api.py` — nó tính lúc chạy
      (`c.passed + len(c.failures)`, dòng ~286). Việc phải làm là khác: dòng ~201 trong
      docstring của `xac_thuc()` viết *"16 phép kiểm cũ đều gửi khoá"*. Phép kiểm mới
      cũng gửi khoá, nên con số đó phải đo lại rồi sửa, hoặc viết lại cho không phụ thuộc
      số đếm
- [x] 3.5 Kiểm phần đầu docstring: mục "BỐN VIỆC NÀY KIỂM" có phải thành **NĂM** không.
      Phép kiểm mới hỏi *"endpoint có phơi thứ không được phơi không"* — khác cả bốn mục
      đang có, nên nhiều khả năng là mục thứ năm chứ không nhét vào mục 3
- [x] 3.6 Chạy `python backend/check_api.py` → **19 phép** (hôm nay 18)

## 4. Vá `tools/chay_dashboard_trong_node.js`

- [x] 4.1 Gieo khoá vào `localStorage` giả, lấy từ biến môi trường `DASHBOARD_KEY` —
      KHÔNG gõ cứng một chuỗi vào file
- [x] 4.2 Khoá phải cất đúng tên kho theo địa chỉ: `tokenledger.key:<base>`; sai tên kho
      thì `api.js` vẫn coi như chưa có khoá
- [x] 4.3 Thoát khác 0 khi `REAL_ACCOUNTS` rỗng sau khi chờ, và nói rõ lý do (chưa có
      khoá / máy chủ chưa chạy / máy chủ trả 401)
- [x] 4.4 Chèn được phép đo vào **trong** IIFE của `app.js` nếu cần — biến của nó là
      biến riêng, nối vào sau `})();` là `ReferenceError`. Ghi bẫy này vào đầu file
- [x] 4.5 Chạy thử **không** đặt `DASHBOARD_KEY`: phải thoát khác 0. **KHÔNG** cấm dòng
      "nạp OK" — nó nói về việc nạp tệp `.js`, và việc đó thật sự thành công. Cấm nhầm nó
      là chữa sai triệu chứng
- [x] 4.6 Trước khi sửa, chạy bản hiện tại để tái lập triệu chứng: exit **0**, "nạp OK"
      2 lần, `conn-text = "Chưa nhập khoá"`, và **0 dòng `GET /api/`** trong nhật ký
      uvicorn. Sau khi sửa, cùng lệnh đó phải thoát khác 0

## 5. Viết lại năm chỗ đã lỗi thời trong `viec-can-lam-truoc-api-gateway.md`

- [x] 5.1 Mục **B5** — lý do hoãn ghi 20/08 nhắm sai hàm (ma trận ăn từ `adoption()`, đã
      sửa 21/08). Thay bằng bảng đo 22/08 và kết luận: **giữ bộ lọc**, việc còn lại là
      đặt tên cho nó. Ghi đúng mức hại: 6 dòng danh bạ + mẫu số 937→943, **không** phải
      6 phòng ban mới — sáu phòng đó đã có sẵn
- [x] 5.2 Mục **§5 Nghiệm thu** — còn viết ở thì *"dự đoán hôm nay"*, thực ra đã chạy
      bằng `tools/dien_tap_gateway.py` và ra đúng dự đoán: **0/8 → 7/7**
- [x] 5.3 Mục **B1** — bỏ dòng *"→ Việc: đổi từ liệt kê giá trị sang một khái niệm có
      tên…"* đang nằm **dưới** khung ✅ nói đã làm xong bằng `ref_source`
- [x] 5.4 Mục **D2** — số đã cũ: `audit_db.py` nay **36** phép, `check_api.py` **19**, và
      `tools/soat_khoa_api.py` chạy được **không cần Docker lẫn database**
- [x] 5.5 Mục **D1** — sai chỗ: `gen_catalog.py` dùng `_latest_dir()` → trỏ vào
      `2026-08-17`, nơi `token-usage-year.json` **có mặt** ở cả `ralli/` lẫn `tla-hd/`.
      Thư mục `tla-hd/2026-08-14/` là của `pull_hd_usage.py`, gen_catalog không đọc.
      Việc D1 thật là `data/` nằm trong `.gitignore` nên máy khác không có đầu vào
- [x] 5.6 Ghi thêm một dòng vào bảng "tưởng / đo ra" của change `require-a-key-to-read-
      the-api`: harness `tools/chay_dashboard_trong_node.js` cũng dính bẫy khoá, và nó
      là chỗ thứ năm — bốn chỗ kia là bốn kịch bản test JS

## 6. Nghiệm thu

- [x] 6.1 `python backend/check_api.py` → **19/19**
- [x] 6.2 `node tests/date-range-filter.test.js` và `node tests/load-failure-states.test.js`
      → **6 + 11**, không đổi
- [x] 6.3 `python scripts/audit_db.py` → **36 phép · 31 đạt · 5 lưu ý · 0 hỏng** (đúng
      như hôm nay), các con số bất biến giữ nguyên: 1.189 dòng · 867.657.110 token ·
      $291,985601
- [x] 6.4 Chạy harness đã vá → `REAL_ACCOUNTS` **937**, `USER_ACCOUNTS` **937**,
      `svc.*` **0**, User hoạt động **26/937**, đơn vị gốc **11** (tự tạo **7**),
      `DEPT_PROVISIONED` **101 / 3.693** — đúng như trước change
- [x] 6.5 `git status` sạch ngoài các file trong phạm vi; `backend/store.py` không còn
      dấu vết của phép đo A/B

## 7. Vòng soát lại sau khi triển khai (22/08/2026)

Đọc lại toàn bộ diff **bằng mắt trước khi chạy** — đúng bước ② của `tu-soat`. Ba lỗi,
không cái nào làm chương trình dừng, nên chạy suông sẽ không bắt được cái nào.

- [x] 7.1 **Chèn nhầm chỗ trong `main()` của `check_api.py`.** Neo thay thế là dòng
      *gọi* `read_only(c)` chứ không phải dòng *in tiêu đề*, nên tiêu đề "Chi doc" đứng
      trơ không có phép kiểm nào bên dưới, còn phép kiểm chỉ-đọc lại in ra dưới tiêu đề
      "Pham vi du lieu phoi ra". **Kết quả sai này đã in ra màn hình ở lần chạy nghiệm
      thu và tôi không nhận ra.** Đã đưa khối mới lên trước tiêu đề "Chi doc"
- [x] 7.2 **Harness đoán một con số giây thay vì chờ.** PROBE chốt lúc 3400ms, bảng báo
      cáo đọc lúc 4000ms — cách nhau 600ms. Backend thật có lúc chậm hơn thế
      (`load-failure-states.test.js` mất 9 giây), và khi đó harness báo *"không nạp
      được"* rồi thoát 1 trong khi nó chỉ **chưa xong**. Một phép kiểm hỏng vì lý do sai
      còn tệ hơn không có phép kiểm. Đổi sang vòng chờ 200ms × 75 (PROBE) và × 100 (bảng
      báo cáo). **Phụ thu: harness nay xong trong 1 giây thay vì 4**, vì nó thôi chờ ngay
      khi có dữ liệu
- [x] 7.3 Một dòng docstring dài 120 ký tự sau khi thay thế — đã ngắt lại theo bề rộng
      của file
- [x] 7.4 Chạy lại bản đầy đủ: `check_api.py` **19/19** (tiêu đề nay đúng mục) ·
      `audit_db.py` **36 phép · 31 đạt · 5 lưu ý · 0 hỏng** · JS **6 + 11** · harness
      **exit 0**, `937 / 937 / svc.* 0`, `26/937`, gốc `11` (tự tạo `7`)
- [x] 7.5 Ba nhánh hỏng của harness đều nói đúng nguyên nhân, phân biệt bằng `conn-text`:
      chưa có khoá → `"Chưa nhập khoá"` · khoá sai → `"Khoá không đúng"` · máy chủ tắt →
      `"Không có dữ liệu"`. Cả ba **exit 1**
