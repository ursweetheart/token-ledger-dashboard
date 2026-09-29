## 0. Đối chứng số đã đo, trước khi sửa một dòng nào

Ba con số của proposal đo lúc database **đang rỗng**, nên chúng đến từ tệp nguồn và từ mã nguồn,
không từ dữ liệu đã nạp. Dựng lại database rồi đối chứng — ra khác thì proposal phải viết lại theo
số thật, không phải ngược lại.

- [x] 0.1 Dựng lại database (`scripts/rebuild_db.py`). **Chặn trước:** đợt 20/09 dừng ở bước 1 vì
      `gemini-3.8-flash` (Ralli, xuất hiện 17/09, 138 lượt / 1.236.777 token) chưa có trong
      `db/rules.py`, và hai SKU `5904-BFA2-5FD5` / `7207-AF1D-C15D` chưa vào `db/02_catalog.sql`.
      Gỡ xong mới chạy được mục 0.

      **Chạy 21/09/2026: 11/11 bước ĐẠT trong 55 giây.** Chỗ chặn đã được gỡ trên `main` bởi
      `d1a6175` — `rules.py` nay có `(13, "gemini-3.8-flash", "gemini-3")` và mẫu `"3.8 flash"`.
      `model not declared 0`. Bước 11 xác nhận `api_readonly` đọc được 28/28 bảng+view.

- [x] 0.2 Đếm người có mặt ở từ hai agent trở lên, đọc từ `dim_user` đã nạp.
      **Kỳ vọng: 5** — `longnt`, `pbh3_tthien`, `quy.tv@rangdong.com.vn`, `tg.namnh`, `tt3.binhtv`.

      ```sql
      SELECT lower(trim(username)) AS ten, count(DISTINCT agent_id) AS so_agent,
             string_agg(DISTINCT agent_id::text, ',' ORDER BY agent_id::text) AS cac_agent
      FROM dim_user WHERE NOT is_technical
      GROUP BY 1 HAVING count(DISTINCT agent_id) > 1 ORDER BY 1;
      ```

      **Đo được 6, không phải 5.** Năm người kỳ vọng đều có mặt. Người thứ sáu là `admin`, vào
      Ralli qua `found_in = 'log'` chứ không qua danh bạ — phép đo đầu tiên đọc tệp danh bạ nên
      không thấy. Mở ra Open Question 4 trong `design.md`.

- [x] 0.3 Đối chứng "ai thắng". So `account.unit_agent_id` thật của 5 người ấy với bảng đã dựng lại
      bằng tay. **Kỳ vọng: Ralli (8) giữ 4, TLA Hợp Đồng (5) giữ 1.** Ra khác thì phép dựng lại
      `unit_priority()` ở design.md sai, và mọi con số 4/5 trong change này phải sửa.

      **ĐÚNG TỪNG NGƯỜI.** longnt · pbh3_tthien · tg.namnh · tt3.binhtv → Ralli (8);
      quy.tv@rangdong.com.vn → TLA Hợp Đồng (5). Đúng cả lý do: `quy.tv` về TLA vì Ralli xếp anh
      ấy vào "Chưa quy được" (tầng 1), không phải vì độ sâu. Tổng theo agent là 4/2 chứ không 4/1,
      vì `admin` cũng thuộc agent 5 — nhưng nó là người thứ sáu, ngoài năm người danh bạ.

- [x] 0.4 Đếm `SELECT COUNT(*) FROM account WHERE unit_conflict = 1`. Con số này phải **≥ 5**; lớn
      hơn là có thêm ca xung đột phòng ban mà tên đăng nhập **không** trùng — ghi lại, nó thuộc Open
      Question 2.

      **Đo được 4, không ≥5 — và kỳ vọng ban đầu SAI chứ không phải dữ liệu.** `admin` và `quy.tv`
      đều có một bên im lặng ("Chưa quy được"), mà lược đồ ghi rõ im lặng *không tính là cãi nhau*.
      Bốn ca còn lại đều là hai bên cùng nêu tên đơn vị và nêu khác nhau. Không có ca nào ngoài sáu
      người trên, nên Open Question 2 chưa có bằng chứng nào.

- [x] 0.5 **Chụp ảnh nền trước khi sửa.** Ghi lại, để so sau: tổng token, tổng tiền, số tài khoản
      phân giải được theo từng agent, và `identity_unresolvable` của lượt nạp Gateway. Đây là mốc
      so, không phải số tham khảo.

      **Ảnh nền 21/09/2026, trước khi sửa `load_gateway.py`:**

      | | |
      |---|---|
      | `fact_usage_daily` | 2.336 dòng · 1.579.479.392 token · $366,206928 |
      | `fact_call` nguồn gateway | 500 dòng · 234.420 token · $0,251448 |
      | `identity_unresolvable` | **15** |
      | agent đã qua Gateway | `dms-feedback`, `crm-feedback` — đều một-người-dùng |

      **Và một phát hiện làm đổi cách viết việc 4.1 và 5.3:** với agent một-người-dùng, NEO CHÍNH
      LÀ tài khoản dịch vụ, nên "quy đúng" và "rơi về neo" đáp xuống CÙNG một `account_id`. Không
      phép truy vấn nào theo `account.kind` phân biệt được. Xem D6 trong `design.md`.

## 1. Phép tra khoá đôi

- [x] 1.1 Thêm vào `db/connect.py` một phép tra `(agent_id, username) → account_id`, **hợp hai
      nguồn** theo D1b: `dim_user` cho người thật (`NOT is_technical`) và `account` cho tài khoản
      dịch vụ (`kind = 'service_account'`, khoá theo `unit_agent_id`). Không trả `unit_agent_id` —
      không còn gì để so sánh.

      Nguồn `dim_user` lọc thêm `found_in = 'directory'` theo **D7**: dòng nhật ký KHÔNG tính là
      "có mặt". Đo 21/09: 8/8 định danh chỉ-có-trong-nhật-ký đều mang `is_shared = 1`.

- [x] 1.2 **Dừng khi dữ liệu hỏng, không im lặng chọn một.** Nếu một cặp `(agent_id, username)` cho
      ra hai `account_id` khác nhau thì phép dựng SHALL báo lỗi và dừng. Gộp trùng chỉ được phép khi
      mọi dòng trùng cùng một `account_id` (D2).

- [x] 1.3 Phép kiểm cho riêng 1.2: dựng bảng tra từ dữ liệu giả có đúng ca hỏng đó, khẳng định nó
      **ném lỗi**. Không có phép kiểm này thì 1.2 là một lời hứa.

- [x] 1.4 Kiểm trên dữ liệu thật: 13 dòng Ralli hai dạng khoá phải gộp về đúng một `account_id` mỗi
      người, không ca nào chạm nhánh lỗi.

      **Chạy trên database thật 21/09: 942 khoá dựng xong, không ném lỗi.** Và 6/6 `svc.<code>`
      tra ra ĐÚNG `account_id` mà `account_lookup()` cũ trả về — điều kiện của việc 2.5.

- [x] 1.5 **Phép kiểm cho tài khoản dịch vụ** (D1b). Tra `(agent_id, "svc.<code>")` phải ra đúng
      `account_id` mà `account_lookup()` cũ trả về, cho **cả 6** agent một-người-dùng. Đây là chỗ
      bản đầu của D1 sai, và là phép kiểm duy nhất bắt được nếu ai đó rút gọn phép tra về một nguồn.

- [x] 1.6 **Tài khoản neo MUST NOT tra ra được.** `__whole_agent_5__` và `__unattributed_8__` không
      được xuất hiện trong bảng tra. Chúng là đích rơi về, không phải đích nhận — gộp nhầm là biến
      đường rơi thành đường nhận, im lặng.

- [x] 1.7 **Phép kiểm HAI NGUỒN CÙNG LÚC.** Lỗ hổng phát hiện 21/09 khi soát lại: 11 phép kiểm đầu
      tiên không phép nào đặt cả `dim_user` lẫn `account` trong cùng một lượt — mỗi phép chỉ dùng
      một nguồn. Hành vi hiện tại **đã đúng** (đã đo), nhưng đúng mà không ai canh: ai sửa hàm này
      để nguồn 2 đè nguồn 1 thì cả 11 phép vẫn xanh.

      Dựng một agent có **cả** người thật lẫn tài khoản dịch vụ; cả hai khoá phải còn nguyên.

- [x] 1.8 **Phép kiểm xung đột XUYÊN NGUỒN.** `dim_user` nói `(6,'x') → 100` còn `account` nói
      `(6,'x') → 200` thì phải dừng, y như xung đột trong cùng một nguồn. Việc 1.3 chỉ phủ xung đột
      **nội bộ** `dim_user`.

## 2. Khâu nạp Gateway

- [x] 2.1 `db/load_gateway.py` — thay phép so `found[1] == agent_id` bằng phép tra khoá đôi. Giữ
      nguyên đường rơi về tài khoản neo khi tra không ra: `account_id` nằm trong khoá chính của
      `fact_usage_daily`, không được NULL.

      **Và chuẩn hoá `end_user` trước khi tra** (D1c). Dòng 346 hiện lấy `end_user` nguyên văn,
      trong khi bảng tra khoá bằng `LOWER(TRIM())`. Bỏ qua chỗ này thì **2 trong 5 người** mà
      change này sinh ra để cứu vẫn mất — `Longnt` và `PBH3_TTHien` mang chữ hoa trong danh bạ.

- [x] 2.1b **Phép kiểm cho chuẩn hoá.** Gửi `X-User: Longnt`, ` longnt `, `LONGNT` → cả ba phải
      quy về cùng một tài khoản với `longnt`.

      Không có phép kiểm này thì triệu chứng lúc nghiệm thu là `identity_unresolvable` **giảm
      nhưng không về 0**, và người sửa sẽ đi tìm một lỗi định tuyến không tồn tại. Đo 21/09 trên
      danh bạ thật: 59/935 tên = **6,3%** có chữ hoa.

- [x] 2.2 Giữ nguyên tên và nghĩa bộ đếm `identity_unresolvable` (D3).

- [x] 2.3 **Phép kiểm chiều dương** — gọi `build_rows()` với dữ liệu giả: người có trong danh bạ
      agent X, request mang tag agent X → quy về đúng tài khoản người ấy, bộ đếm **không** tăng.

- [x] 2.4 **Phép kiểm chiều âm — bắt buộc, không được bỏ** (D3). Định danh **không** có trong danh
      bạ agent nào → vẫn bị từ chối, bộ đếm **có** tăng, dòng rơi về neo.

      Dựng đúng ca `admin` đã đo 31/08: `admin` có trong danh bạ agent 5 và đã mang 480 lượt /
      1.588.404 token; agent 6 gửi `X-User: admin` → **phải bị từ chối**. Thiếu phép kiểm này thì
      "không còn từ chối ai" có thể đạt được bằng cách thôi từ chối tất cả.

- [x] 2.5 **Đối chứng 6 agent một-người-dùng phải Y HỆT trước khi sửa.** `svc.<code>` mang mã agent
      trong chính tên nó nên không bao giờ va chạm. Lệch một dòng nào ở đây nghĩa là phép tra mới
      làm hỏng đường đang chạy đúng.

      **Đo 21/09 bằng `--dry-run --full` trên sổ thật, so với ảnh nền 0.5:**

      | | ảnh nền | sau khi sửa |
      |---|---|---|
      | dòng vào sổ | 500 | 500 |
      | token | 234.420 | 234.420 |
      | `identity_unresolvable` | 15 | **15** |
      | `end_user empty` | 368 | 368 |
      | `unit unknown` | 0 | 0 |

      15 dòng ấy vẫn đúng ba định danh PHẢI bị từ chối (`tuan.tran` 13 lượt,
      `svc.nghiem-thu-doi-ten-17-09` 2 lượt). Nếu phép tra mới làm hỏng 6 agent
      một-người-dùng thì con số này đã nhảy lên ~117 — `svc.crm-feedback` một mình
      đã 98 lượt.

## 3. Danh bạ

- [x] 3.1 `backend/store.py` `accounts()` — trả **danh sách** agent nơi người đó có mặt (đọc
      `dim_user`), thay cho một agent thắng. Giữ `unit_agent_id` và `unit_conflict` (D4).

      **30/09:** `accounts()` trả thêm cột `agents` (mảng tên agent có mặt, đọc dòng danh bạ `dim_user`), LUÔN gồm agent thắng để không ai biến mất khỏi bộ lọc; giữ `agent`, `unit_agent_id`, `unit_conflict`. `api.js` dịch tên từng phần tử như `agent`.

- [x] 3.2 Màn hình danh bạ đọc danh sách ấy. Lọc theo agent khớp *có mặt ở*, không phải *thuộc về*.

      **30/09 (người dùng cho phép sửa logic lọc trong `app.js`, không đổi hiển thị):**
      `buildAccountCatalogueFromDb` mang theo `agents`; `filterAccounts()` và đường lui ghép
      theo tên (`applyRealAccountUsage`) hỏi "có mặt ở". Giữ nguyên chỗ rải tổng đơn vị và
      chỗ đếm agent trong bảng tổng. Trên dashboard thật (sau tải lại cứng): lọc TLA Hợp Đồng
      45 → **49**, Ralli → 894, không lọc 946 = 946. Lưu ý: JS cũ nằm trong bộ nhớ đệm trình
      duyệt sau khi build lại `web` — phải tải lại cứng mới thấy.

- [x] 3.3 Kiểm bằng số: lọc danh bạ theo TLA Hợp Đồng phải ra **44**, không phải 40.

      **Đo 30/09 trên database thật:** danh bạ TLA Hợp Đồng (`found_in='directory'`) = **44**; lọc theo cột mới gồm đủ 44/44 (cũ 40/44). Màn hình đếm 49 thay vì 44 vì có thêm 5 tài khoản chỉ-có-trong-nhật-ký thắng về TLA (`test1`–`test4`, `nghiệp vụ bh1`) — cũ 45 → mới 49, tăng đúng 4. Ralli 893 → 894 (`quy.tv`). Đúng 5 người có ≥2 agent. 0 người mất khỏi agent của mình.

- [x] 3.4 **Ô KPI tổng người dùng MUST NOT đổi.** `web/js/app.js:3568` đọc `accounts.length`; change
      này không tách `account` nên con số ấy phải y nguyên. Đổi nghĩa là đã vô tình tách.

      **30/09:** số dòng `accounts()` vẫn 938 (cột mới không nhân bản dòng); `accounts.length` không đổi.

## 4. Phép canh tự động

- [x] 4.1 Thêm vào `scripts/audit_db.py` phép kiểm: **không người nào có trong danh bạ của một agent
      mà lưu lượng của họ qua agent ấy lại rơi vào tài khoản neo.** Đây là phép canh duy nhất bắt
      được lỗi này quay lại — mọi phép kiểm bằng tổng đều ĐẠT khi nó hỏng.

      **30/09:** nhóm G, `check_observed` (khai mẫu số). Thử bằng 3 dòng `fact_call` giả trên danh bạ/tài khoản THẬT, phiên chỉ đọc: mẫu số 2 (`LongNT ` khớp sau chuẩn hoá, định danh lạ bị loại), lỗi 1 (dòng rơi về neo). Trên dữ liệu thật hôm nay: *chưa kiểm được* (0 dòng) vì chưa agent nhiều người dùng nào qua Gateway.

- [x] 4.2 `scripts/audit_db.py` chạy sẵn ở bước 9/9 của `scripts/update_dashboard.py`, nên không
      phải dựng gì mới. Kiểm rằng phép mới có chạy ở đó thật, đừng suy từ việc đã thêm hàm.

      **30/09:** chạy `scripts/audit_db.py` thật → phép mới có trong kết quả (`[ note ] Gateway calls by people in an agent's directory keep their own account`).

## 5. Nghiệm thu

- [x] 5.1 So với mốc 0.5: **tổng token và tổng tiền MUST NOT đổi.** Change này không sửa số liệu;
      tổng đổi nghĩa là đã làm sai thứ khác.

      **30/09:** phần sửa hôm nay chỉ ĐỌC (`store.accounts`, `audit_db.py`), không đường ghi nào đổi. Phần có ghi (khâu nạp Gateway) đã đo ở 2.5: 500 dòng / 234.420 token trước = sau.

- [x] 5.2 Số tài khoản phân giải được: **tăng**, và tăng đúng ở những agent có người dùng chung.

      **30/09:** chiều danh bạ tăng đúng ở hai agent có người dùng chung: TLA Hợp Đồng +4, Ralli +1. Chiều Gateway: logic chứng minh ở 2.3; chưa quan sát trên dữ liệu thật vì chưa agent nhiều người dùng nào qua Gateway.

- [x] 5.3 `identity_unresolvable` ở lượt nạp Gateway: **giảm về 0** cho người có trong danh bạ.
      Không được đạt bằng cách bộ đếm thôi hoạt động — 2.4 là thứ chứng minh điều đó.

      **30/09:** phép canh 4.1 quan sát 0 dòng Gateway nào mang X-User có trong danh bạ; 15 dòng `identity_unresolvable` (2.5) đều là định danh phải từ chối. Bộ đếm vẫn hoạt động (2.4).

- [x] 5.4 Chạy lại toàn bộ `scripts/audit_db.py`. Không nhóm nào đỏ thêm so với mốc 0.5.

      **30/09:** bản HEAD của `audit_db.py` trên cùng database: 79 phép / 67 đạt / 11 lưu ý / 1 hỏng. Bản có phép mới: 80 / 67 / **12** / 1 — đúng +1 lưu ý. Phép hỏng (đối chiếu token cache nhóm H, gateway 0 vs hoá đơn) có sẵn từ trước, ngoài phạm vi change.

- [x] 5.5 Cập nhật `docs/reference/onboard-a-new-agent.md` mục 8: chỗ đang viết *"quy tắc
      `found[1] == agent_id` chưa từng gặp trường hợp này"* nay đã gặp và đã sửa. Ghi lại số đo, đừng
      để tài liệu nói theo trạng thái cũ.

      **30/09:** `docs/reference/onboard-a-new-agent.md` mục 8 ghi đã sửa, kèm số đo; mục "Nguồn danh bạ" vẫn mở.
