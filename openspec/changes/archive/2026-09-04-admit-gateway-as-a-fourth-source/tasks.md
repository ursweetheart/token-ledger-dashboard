# Tasks

## 1. Chạy kịch bản nghiệm thu TRƯỚC khi sửa gì

Thứ tự này quan trọng. Hôm nay kịch bản sẽ **trượt**, và danh sách chỗ trượt chính là
phạm vi thật của change — thay cho danh sách grep. Ba lần "đo lại thì sai" ngày 20/08 đều
là cùng bài học đó.

- [x] 1.1 Ghi mốc từ `usage_resolved`: **1.189 dòng · 867.657.110 token** · billing
      965/708.868.471 · app 168/104.990.903 · monitoring 46/53.797.736 · NULL 10 dòng ·
      kỳ 01/01→17/08. Ba nhóm độ phủ: người thật **104.990.903** · dịch vụ
      **749.483.267** · không quy được **13.182.940** (cộng đúng tổng)
- [x] 1.2 Ghi mốc `usage_by_account`: **320 dòng / 107.926.810 token**. Tử số tỷ lệ áp
      dụng của Trợ lý ảo Ralli: **24**
- [x] 1.3 Viết `tools/dien_tap_gateway.py` — chèn trong TRANSACTION, `ROLLBACK` ở cuối kể
      cả khi lỗi giữa chừng (`try/finally`). Không dùng `autocommit`
- [x] 1.4 Dòng giả mang username **THẬT** tra từ `account`: `administrator`, `admintest`,
      `app.reviewer` (agent 8) + một dòng trên đúng khoá `usage_resolved` đang chọn
      billing `(2026-08-16, agent 1, model 5)` để kiểm thứ tự ưu tiên.
      **Lỗi bắt được lúc tự soát:** bản đầu tra tài khoản dịch vụ theo `unit_agent_id` của
      khoá billing — nhưng Ralli và Hợp Đồng là `whole_agent`, **không có** tài khoản dịch
      vụ. Khoá billing rơi vào một trong hai thì dòng kiểm ưu tiên không được chèn và kỳ
      vọng trượt vì **lý do khác hẳn cái đang đo** — một phép kiểm nói dối. Đã đổi sang
      lấy `account_id` của chính dòng billing đó
- [x] 1.5 Chạy trên code CHƯA SỬA: **TRƯỢT 8/8**, `ROLLBACK` sạch. Triệu chứng rõ hơn dự
      đoán trong proposal:

      | | trước | sau | |
      |---|---:|---:|---|
      | `usage_by_account` dòng | 320 | 320 | **+0** |
      | tỷ lệ áp dụng agent 8 | 24 | 24 | **+0** |
      | quy về người thật | 104.990.903 | 104.990.903 | **+0** |
      | `usage_resolved` dòng | 1.189 | 1.192 | +3 |
      | `usage_resolved` token | 867.657.110 | 867.657.110 | **+0** |
      | `usage_resolved` dòng KHÔNG có token | 10 | **13** | **+3** |

      Chèn 4.000.000 token mà dashboard đứng im. `usage_resolved` **có** thêm khoá nhưng
      `COALESCE(b, m, a)` không biết `gateway` nên trả `NULL` — dữ liệu nằm trong database
      và **vô hình**. Đây là bản đặc tả của nhóm 3 và nhóm 4

## 2. Bảng `ref_source`, và tên của 6 tài khoản dịch vụ

- [x] 2.1 `ref_source(source, knows_user, has_invoice_cost, era, note)` trong
      `db/01_schema.sql`. **Đặt ở cuối mục 1, không ở mục 3 cùng `ref_price`** — khoá
      ngoại của `fact_usage_daily` trỏ vào nó nên SQL đòi khai trước.
      **Đổi tên cột lúc viết: `has_cost` → `has_invoice_cost`.** LiteLLM *có* trả về một
      con số tiền, nhưng nó tự nhân từ bảng giá. Gọi là `has_cost = TRUE` rồi đổ vào
      `cost_usd` là biến tiền suy ra thành tiền đã xác nhận — đúng thứ cả ngày 20/08 đi bịt
- [x] 2.2 Nạp 4 dòng ngay trong `01_schema.sql`: `app`(T,F,scrape) · `billing`(F,T,scrape)
      · `monitoring`(F,F,scrape) · `gateway`(**T,F**,gateway) — gateway
      `has_invoice_cost = FALSE`, lý do ở 2.1
- [x] 2.3 Ghi chú tại chỗ: vì sao `knows_user` tách khỏi tên nguồn, kèm ngày. Ghi chú tại
      chỗ có giá trị hơn một tài liệu riêng
- [x] 2.4 `fact_usage_daily.source` thêm `REFERENCES ref_source` — nguồn lạ bị chặn ngay
      lúc ghi, không đợi phép kiểm
- [x] 2.5 **Không phải sửa `rebuild_db.py`**: 4 dòng nạp thẳng trong `01_schema.sql`, mà
      file đó chạy đầu tiên trong `connect.rebuild()`

**Thêm 21/08 — kịch bản nghiệm thu bắt được, tasks.md ban đầu bỏ sót.** Spec đã yêu cầu
username của agent một-người-dùng là `svc.<code>`, nhưng 6 tài khoản dịch vụ hiện vẫn mang
tên tạm của khâu nạp:

```
   938 __whole_agent_1__  ->  svc.contact-center
   940 __whole_agent_2__  ->  svc.sale-agent
   942 __whole_agent_3__  ->  svc.invoice
   944 __whole_agent_4__  ->  svc.tools-quizzer
   948 __whole_agent_6__  ->  svc.dms-feedback
   950 __whole_agent_7__  ->  svc.crm-feedback
```

Không đổi thì ngày Gateway gửi `svc.contact-center`, username **không tra ra tài khoản
nào** — đúng thứ phép kiểm 5.1 sẽ kêu.

- [x] 2.6 `db/load_org.py` đặt `username = f"svc.{agent_code[aid]}"`, suy từ
      `dim_agent.code` chứ không gõ tay 6 lần.
      **Kéo theo một việc mà ghi chú tại chỗ đã cảnh báo trước:** `load_org.py:568` ghi
      *"đừng đổi tên ở đây — `build_usage_daily.py` tra tài khoản này BẰNG TÊN ĐĂNG
      NHẬP"*. Sửa không phải bằng cách đổi chuỗi ở hai nơi, mà **bỏ hẳn phụ thuộc**:
      `anchor_accounts()` giờ tra bằng `(kind, unit_agent_id)` — hỏi đúng câu nó cần
      hỏi — kèm hai phép kiểm thiếu/thừa để hỏng ồn ào
- [x] 2.7 Giữ nguyên tên tạm `__unattributed_<id>__` cho 8 dòng `unattributed` — chúng
      KHÔNG phải tài khoản, không ai gửi tên đó lên Gateway
- [x] 2.8 Phép kiểm: mọi dòng `kind='service_account'` có username khớp
      `svc.` + `dim_agent.code` của chính nó

## 3. `usage_resolved` nhận nguồn thứ tư

- [x] 3.1 Thêm CTE `g` (gateway) vào view, đứng **đầu** `COALESCE(g, b, m, a)`
- [x] 3.2 `token_source` nhận thêm giá trị `'gateway'`
- [x] 3.3 Cập nhật khối ghi chú đầu view — nó đang mô tả 3 nguồn
- [x] 3.4 **Kiểm bất biến**: khi `ref_source` có `gateway` nhưng chưa có bản ghi nào, mọi
      con số ở 1.1 và 1.2 phải giữ nguyên **đến từng token**. Lệch một token là có lỗi

## 4. Tám chỗ đầu đọc

Chỉ đầu đọc. **KHÔNG đụng 14 chỗ đầu ghi** — `load_ralli.py` ghi `source='app'` là mô tả
đúng sự thật.

**Phân loại lại 21/08 thì phạm vi là 8, không phải 10.** Hai chỗ tôi xếp nhầm vào đầu
đọc thực ra là *định nghĩa*, và Gateway lọt vào đó mới là sai:

| Chỗ | Câu nó hỏi | |
|---|---|---|
| `01_schema.sql` CTE `a` | *"gom các dòng CỦA nguồn app"* | **giữ** |
| `audit_db.py:163` | *"khâu nạp app ghi đúng bằng hai bảng app không"* | **giữ** |

- [x] 4.1 ~~`01_schema.sql:600`~~ → **GIỮ NGUYÊN**, đây là CTE `a` của `usage_resolved`,
      tức định nghĩa nguồn app chứ không phải phép đọc
- [x] 4.2 `db/01_schema.sql:648` — `WHERE f.source='app' AND a.kind='real'`. Chú ý: hai
      điều kiện này hỏi **hai câu khác nhau** ("nguồn biết người" và "là con người"), đừng
      gộp làm một khi sửa
- [x] 4.3 `backend/store.py:257, 263` — chỉ tiêu tỷ lệ áp dụng
- [x] 4.4 `backend/store.py:452` — `v.token_source='app'`, chia token về người thật
- [x] 4.5 `scripts/audit_db.py:263, 290, 312, 413` — **4** phép kiểm (giữ `:163`)
- [x] 4.6 `grep` lại: `store.py` còn 0 chỗ lọc, `audit_db.py` còn đúng `:163`, schema còn
      đúng CTE `a`. 14 chỗ đầu ghi nguyên vẹn

## 5. Ba phép kiểm mới

Hai trong ba phép kiểm tôi soạn ban đầu **không kêu được**, phải thay bằng phép kiểm khác.
Chi tiết ở từng dòng.

- [x] 5.1 Dòng ký nguyên `gateway` rơi vào tài khoản `unattributed`/`whole_agent` → hỏng.
      **Bản đầu lọc `knows_user` và kêu ngay 21 dòng** — hoá ra nó đúng: nguồn `app`
      *biết được* người dùng nhưng **không phải lúc nào cũng biết** (nhật ký Ralli có lượt
      không kèm user, khâu nạp lùi về `__unattributed__` một cách có chủ ý). *"Nguồn này
      có thể mang danh tính"* khác *"mọi dòng đều có danh tính"*. Chỉ kỷ nguyên gateway
      mới được đòi vế sau, vì A3 bảo đảm mọi request mang danh tính
- [x] 5.2 ~~Phép kiểm riêng cho `source` lạ~~ → **KHÔNG THÊM.** Khoá ngoại ở 2.4 đã chặn
      ngay lúc ghi, nên một phép kiểm riêng sẽ **không bao giờ kêu được** — đúng thứ 5.4
      cấm. Thay bằng: thêm `(fact_usage_daily, source, ref_source, source)` vào bảng
      `FOREIGN_KEYS`, chỗ này *kêu được* với bản SQLite (không bắt khoá ngoại) và với
      database dựng từ schema trước 21/08
- [x] 5.3 ~~Bẫy NULL của cột chỉ Gateway mới có~~ → **CHƯA CÓ CỘT NÀO NHƯ VẬY.** Thay bằng
      một bẫy im lặng THẬT mà chính quyết định ở 3.1 tạo ra: ai chèn dòng `gateway` kèm
      `cost_usd` sẽ thấy số tiền đó **biến mất** khỏi dashboard, vì view chỉ lấy tiền hoá
      đơn. Phép kiểm: nguồn `has_invoice_cost = FALSE` mà có `cost_usd` → CẢNH BÁO
- [x] 5.4 Đã chứng minh **kêu được**: chèn trong `BEGIN … ROLLBACK` một dòng `gateway` trỏ
      vào tài khoản `whole_agent` → 0 thành 1; một dòng `gateway` kèm `cost_usd` → 0
      thành 1. Trên dữ liệu sạch cả hai im lặng. Phép kiểm không thể kêu còn tệ hơn không
      có — bài học `data_to` ngày 20/08

## 6. Chạy lại kịch bản nghiệm thu

- [x] 6.1 Chạy `tools/dien_tap_gateway.py` trên code đã sửa
- [x] 6.2 `usage_by_account` phải có thêm dòng (mốc: 320)
- [x] 6.3 Tỷ lệ quy về người phải tăng khỏi 12,4%
- [x] 6.4 Xác nhận `ROLLBACK` sạch: chạy lại 1.1 và 1.2, số phải về đúng mốc cũ

## 7. Nghiệm thu toàn bộ

- [x] 7.1 `python scripts/rebuild_db.py` — 7/7 bước
- [x] 7.2 `python scripts/audit_db.py` — **36 phép | 31 đạt | 5 lưu ý | 0 hỏng**
- [x] 7.3 `python backend/check_api.py` — **16/16**
- [x] 7.4 `node --test` — **6 + 7**. Chạy `node --test tests/` (chế độ thư mục) báo hỏng
      trên bản Node này kể cả khi hai file đều xanh; phải chạy từng file
- [x] 7.5 So qua API: `/api/usage` cả kỳ trả **1.189 dòng · 867.657.110 token ·
      $291,985601**, `/api/health` trả **104.990.903 / 749.483.267 / 13.182.940**. Khớp
      mốc 1.1 tuyệt đối
- [x] 7.6 Mọi phép đo trong change này đi qua `usage_resolved`, không cộng thẳng
      `fact_usage_daily` — cộng thẳng là đếm hai lần, đã cắn hai lần ngày 20/08

## 8. Tài liệu

- [x] 8.1 `tu-dien-database.md` §7b — `ref_source`, kèm hai chỗ dễ đọc nhầm
- [x] 8.2 `viec-can-lam-truoc-api-gateway.md` — B1 + B2 ✅, kèm bảng trước/sau và bốn
      chỗ "đo lại thì khác với lúc soạn proposal"
- [x] 8.3 `dong-bo-may-dong-nghiep-20-08.md` — mục bổ sung 21/08: phải rebuild lần nữa,
      3 thứ mới, con số phải giữ nguyên, và `tools/dien_tap_gateway.py`
