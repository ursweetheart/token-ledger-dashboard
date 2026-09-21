## 0. Đối chứng số đã đo, trước khi sửa một dòng nào

Ba con số của proposal đo lúc database **đang rỗng**, nên chúng đến từ tệp nguồn và từ mã nguồn,
không từ dữ liệu đã nạp. Dựng lại database rồi đối chứng — ra khác thì proposal phải viết lại theo
số thật, không phải ngược lại.

- [ ] 0.1 Dựng lại database (`scripts/rebuild_db.py`). **Chặn trước:** đợt 20/09 dừng ở bước 1 vì
      `gemini-3.8-flash` (Ralli, xuất hiện 17/09, 138 lượt / 1.236.777 token) chưa có trong
      `db/rules.py`, và hai SKU `5904-BFA2-5FD5` / `7207-AF1D-C15D` chưa vào `db/02_catalog.sql`.
      Gỡ xong mới chạy được mục 0.

- [ ] 0.2 Đếm người có mặt ở từ hai agent trở lên, đọc từ `dim_user` đã nạp.
      **Kỳ vọng: 5** — `longnt`, `pbh3_tthien`, `quy.tv@rangdong.com.vn`, `tg.namnh`, `tt3.binhtv`.

      ```sql
      SELECT lower(trim(username)) AS ten, count(DISTINCT agent_id) AS so_agent,
             string_agg(DISTINCT agent_id::text, ',' ORDER BY agent_id::text) AS cac_agent
      FROM dim_user WHERE NOT is_technical
      GROUP BY 1 HAVING count(DISTINCT agent_id) > 1 ORDER BY 1;
      ```

- [ ] 0.3 Đối chứng "ai thắng". So `account.unit_agent_id` thật của 5 người ấy với bảng đã dựng lại
      bằng tay. **Kỳ vọng: Ralli (8) giữ 4, TLA Hợp Đồng (5) giữ 1.** Ra khác thì phép dựng lại
      `unit_priority()` ở design.md sai, và mọi con số 4/5 trong change này phải sửa.

- [ ] 0.4 Đếm `SELECT COUNT(*) FROM account WHERE unit_conflict = 1`. Con số này phải **≥ 5**; lớn
      hơn là có thêm ca xung đột phòng ban mà tên đăng nhập **không** trùng — ghi lại, nó thuộc Open
      Question 2.

- [ ] 0.5 **Chụp ảnh nền trước khi sửa.** Ghi lại, để so sau: tổng token, tổng tiền, số tài khoản
      phân giải được theo từng agent, và `identity_unresolvable` của lượt nạp Gateway. Đây là mốc
      so, không phải số tham khảo.

## 1. Phép tra khoá đôi

- [x] 1.1 Thêm vào `db/connect.py` một phép tra `(agent_id, username) → account_id`, **hợp hai
      nguồn** theo D1b: `dim_user` cho người thật (`NOT is_technical`) và `account` cho tài khoản
      dịch vụ (`kind = 'service_account'`, khoá theo `unit_agent_id`). Không trả `unit_agent_id` —
      không còn gì để so sánh.

- [x] 1.2 **Dừng khi dữ liệu hỏng, không im lặng chọn một.** Nếu một cặp `(agent_id, username)` cho
      ra hai `account_id` khác nhau thì phép dựng SHALL báo lỗi và dừng. Gộp trùng chỉ được phép khi
      mọi dòng trùng cùng một `account_id` (D2).

- [x] 1.3 Phép kiểm cho riêng 1.2: dựng bảng tra từ dữ liệu giả có đúng ca hỏng đó, khẳng định nó
      **ném lỗi**. Không có phép kiểm này thì 1.2 là một lời hứa.

- [ ] 1.4 Kiểm trên dữ liệu thật: 13 dòng Ralli hai dạng khoá phải gộp về đúng một `account_id` mỗi
      người, không ca nào chạm nhánh lỗi.

- [x] 1.5 **Phép kiểm cho tài khoản dịch vụ** (D1b). Tra `(agent_id, "svc.<code>")` phải ra đúng
      `account_id` mà `account_lookup()` cũ trả về, cho **cả 6** agent một-người-dùng. Đây là chỗ
      bản đầu của D1 sai, và là phép kiểm duy nhất bắt được nếu ai đó rút gọn phép tra về một nguồn.

- [x] 1.6 **Tài khoản neo MUST NOT tra ra được.** `__whole_agent_5__` và `__unattributed_8__` không
      được xuất hiện trong bảng tra. Chúng là đích rơi về, không phải đích nhận — gộp nhầm là biến
      đường rơi thành đường nhận, im lặng.

- [ ] 1.7 **Phép kiểm HAI NGUỒN CÙNG LÚC.** Lỗ hổng phát hiện 21/09 khi soát lại: 11 phép kiểm đầu
      tiên không phép nào đặt cả `dim_user` lẫn `account` trong cùng một lượt — mỗi phép chỉ dùng
      một nguồn. Hành vi hiện tại **đã đúng** (đã đo), nhưng đúng mà không ai canh: ai sửa hàm này
      để nguồn 2 đè nguồn 1 thì cả 11 phép vẫn xanh.

      Dựng một agent có **cả** người thật lẫn tài khoản dịch vụ; cả hai khoá phải còn nguyên.

- [ ] 1.8 **Phép kiểm xung đột XUYÊN NGUỒN.** `dim_user` nói `(6,'x') → 100` còn `account` nói
      `(6,'x') → 200` thì phải dừng, y như xung đột trong cùng một nguồn. Việc 1.3 chỉ phủ xung đột
      **nội bộ** `dim_user`.

## 2. Khâu nạp Gateway

- [ ] 2.1 `db/load_gateway.py` — thay phép so `found[1] == agent_id` bằng phép tra khoá đôi. Giữ
      nguyên đường rơi về tài khoản neo khi tra không ra: `account_id` nằm trong khoá chính của
      `fact_usage_daily`, không được NULL.

      **Và chuẩn hoá `end_user` trước khi tra** (D1c). Dòng 346 hiện lấy `end_user` nguyên văn,
      trong khi bảng tra khoá bằng `LOWER(TRIM())`. Bỏ qua chỗ này thì **2 trong 5 người** mà
      change này sinh ra để cứu vẫn mất — `Longnt` và `PBH3_TTHien` mang chữ hoa trong danh bạ.

- [ ] 2.1b **Phép kiểm cho chuẩn hoá.** Gửi `X-User: Longnt`, ` longnt `, `LONGNT` → cả ba phải
      quy về cùng một tài khoản với `longnt`.

      Không có phép kiểm này thì triệu chứng lúc nghiệm thu là `identity_unresolvable` **giảm
      nhưng không về 0**, và người sửa sẽ đi tìm một lỗi định tuyến không tồn tại. Đo 21/09 trên
      danh bạ thật: 59/935 tên = **6,3%** có chữ hoa.

- [ ] 2.2 Giữ nguyên tên và nghĩa bộ đếm `identity_unresolvable` (D3).

- [ ] 2.3 **Phép kiểm chiều dương** — gọi `build_rows()` với dữ liệu giả: người có trong danh bạ
      agent X, request mang tag agent X → quy về đúng tài khoản người ấy, bộ đếm **không** tăng.

- [ ] 2.4 **Phép kiểm chiều âm — bắt buộc, không được bỏ** (D3). Định danh **không** có trong danh
      bạ agent nào → vẫn bị từ chối, bộ đếm **có** tăng, dòng rơi về neo.

      Dựng đúng ca `admin` đã đo 31/08: `admin` có trong danh bạ agent 5 và đã mang 480 lượt /
      1.588.404 token; agent 6 gửi `X-User: admin` → **phải bị từ chối**. Thiếu phép kiểm này thì
      "không còn từ chối ai" có thể đạt được bằng cách thôi từ chối tất cả.

- [ ] 2.5 **Đối chứng 6 agent một-người-dùng phải Y HỆT trước khi sửa.** `svc.<code>` mang mã agent
      trong chính tên nó nên không bao giờ va chạm. Lệch một dòng nào ở đây nghĩa là phép tra mới
      làm hỏng đường đang chạy đúng.

## 3. Danh bạ

- [ ] 3.1 `backend/store.py` `accounts()` — trả **danh sách** agent nơi người đó có mặt (đọc
      `dim_user`), thay cho một agent thắng. Giữ `unit_agent_id` và `unit_conflict` (D4).

- [ ] 3.2 Màn hình danh bạ đọc danh sách ấy. Lọc theo agent khớp *có mặt ở*, không phải *thuộc về*.

- [ ] 3.3 Kiểm bằng số: lọc danh bạ theo TLA Hợp Đồng phải ra **44**, không phải 40.

- [ ] 3.4 **Ô KPI tổng người dùng MUST NOT đổi.** `web/js/app.js:3568` đọc `accounts.length`; change
      này không tách `account` nên con số ấy phải y nguyên. Đổi nghĩa là đã vô tình tách.

## 4. Phép canh tự động

- [ ] 4.1 Thêm vào `scripts/audit_db.py` phép kiểm: **không người nào có trong danh bạ của một agent
      mà lưu lượng của họ qua agent ấy lại rơi vào tài khoản neo.** Đây là phép canh duy nhất bắt
      được lỗi này quay lại — mọi phép kiểm bằng tổng đều ĐẠT khi nó hỏng.

- [ ] 4.2 `scripts/audit_db.py` chạy sẵn ở bước 9/9 của `scripts/update_dashboard.py`, nên không
      phải dựng gì mới. Kiểm rằng phép mới có chạy ở đó thật, đừng suy từ việc đã thêm hàm.

## 5. Nghiệm thu

- [ ] 5.1 So với mốc 0.5: **tổng token và tổng tiền MUST NOT đổi.** Change này không sửa số liệu;
      tổng đổi nghĩa là đã làm sai thứ khác.

- [ ] 5.2 Số tài khoản phân giải được: **tăng**, và tăng đúng ở những agent có người dùng chung.

- [ ] 5.3 `identity_unresolvable` ở lượt nạp Gateway: **giảm về 0** cho người có trong danh bạ.
      Không được đạt bằng cách bộ đếm thôi hoạt động — 2.4 là thứ chứng minh điều đó.

- [ ] 5.4 Chạy lại toàn bộ `scripts/audit_db.py`. Không nhóm nào đỏ thêm so với mốc 0.5.

- [ ] 5.5 Cập nhật `docs/reference/onboard-a-new-agent.md` mục 8: chỗ đang viết *"quy tắc
      `found[1] == agent_id` chưa từng gặp trường hợp này"* nay đã gặp và đã sửa. Ghi lại số đo, đừng
      để tài liệu nói theo trạng thái cũ.
