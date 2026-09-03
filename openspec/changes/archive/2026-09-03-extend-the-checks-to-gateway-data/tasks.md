# Tasks

Quy ước: mỗi mục đo được thì **ghi số đo ngay tại chỗ**, không ghi "đã kiểm tra".

Thứ tự: nhóm **2, 3, 4** độc lập nhau, làm được song song. Nhóm **5** phải sau nhóm 4 —
nó dùng chính cơ chế "chưa kiểm được" mà nhóm 4 dựng. Nhóm **6** sau nhóm 4 cùng lý do.

## 1. Ghi mốc trước khi đổi

- [x] 1.1 `var/baseline-truoc-kiem-gateway.json`. audit **68 · 64 · 4 · 0**, check_api
      **27 · 27 · 0**, kèm **nhãn của cả bốn lưu ý**: *Every usage_resolved row carries
      tokens* · *Latency coverage* · *Coverage of the 'who used it' dimension* ·
      *Accounts whose unit two apps declare differently*
- [x] 1.2 khoá ngoại **thật 36 / khai 23 / thiếu 13**, danh sách 13 quan hệ ghi vào mốc
- [x] 1.3 gateway `cached_tokens` **0/41** · hoá đơn `kind='cached'` **461 dòng ·
      252.321.118 token · 214 ngày · 6 agent · 05/01 → 29/08** ·
      **số ngày giao nhau: 0**
- [x] 1.4 Tìm được **8 cặp (bảng, nguồn) rỗng tự nhiên**, nhiều hơn dự kiến:
      `fact_perf_daily` thiếu cả gateway/app/billing · `fact_latency_daily` thiếu
      app/billing · `fact_call` thiếu billing/monitoring · `fact_usage_hourly` thiếu
      billing. Không phải dựng database giả để nghiệm thu việc 4.5

## 2. Khoá ngoại: hỏi database, không giữ bản chép tay

- [x] 2.1 `doc_khoa_ngoai(cn)` đọc `pg_constraint` (kèm `confkey` để lấy **cột cha**, không
      chỉ bảng cha). Hằng số cũ đổi tên thành `FOREIGN_KEYS_GO_TAY`, giữ để đối chiếu
- [x] 2.2 Ghi trong docstring `doc_khoa_ngoai()`: **CHỈ CHẠY TRÊN POSTGRESQL**, kèm lý do
      (`pg_constraint` là catalog riêng) và mốc dự án đã bỏ SQLite 24/08/2026
- [x] 2.3 Nhãn nay là `Foreign keys (36 relations, read from the database)` — **36**, không
      còn 23
- [x] 2.4 `MOC_KHOA_NGOAI = 36`, phép kiểm `Foreign key count has not dropped (>= 36)` ĐẠT.
      Docstring ghi rõ điểm mù ngược lại mà nó chặn: danh sách tự sinh vẫn xanh khi một
      khoá ngoại **bị xoá**
- [x] 2.5 **36/36 quan hệ được kiểm, 0 quan hệ treo.** Thêm phép mức CẢNH BÁO đo khoảng cách
      giữa hai cách làm: `danh sach go tay cu bo sot 13/36 quan he` — độ trôi nay là một
      **con số**, không phải một lời kể

## 3. Ngày tương lai: mốc là ngày chạy

- [x] 3.1 Bỏ `'2026-12-31'`, thay bằng `CURRENT_DATE`
- [x] 3.2 `> CURRENT_DATE + 1`. Lý do ghi tại chỗ: mọi cột thời gian là giờ VN (chốt 14/08)
      còn `CURRENT_DATE` là ngày của máy chủ database — hai đồng hồ cách nhau tới 7 giờ
- [x] 3.3 Năm bảng: `fact_call.ts_local` · `fact_usage_daily.day` · `fact_usage_hourly.hour`
      · `fact_billing_daily.day` · `fact_monitoring.ts_local`. Đã kiểm cả năm cột **có
      thật** và đúng kiểu trước khi viết
- [x] 3.4 **0 dòng tương lai** trên cả năm bảng. Nhãn nay nói rõ phạm vi:
      `No future-dated rows (5 tables, threshold = today + 1)`

## 4. Phân biệt "ĐẠT" với "KHÔNG CÓ GÌ ĐỂ KIỂM"

- [x] 4.1 `Audit.check_tren(quan_sat, ok, label, ...)`. Ba kết cục đúng như thiết kế
- [x] 4.2 Nhãn kèm `(n rows checked)`. Đo: sáu phép gateway nay hiện **(41 rows checked)** và
      **(1 rows checked)**
- [x] 4.3 Chuyển **6** phép: *Failed calls never reach the rollup* · *Cache hits never reach
      the rollup* · *Every gateway row has raw_model* · *…has virtual_key_id* ·
      *…has unit_id* · *Raw percentiles have no histogram bucket*. Không viết lại phép nào
      — chỉ thêm mẫu số
- [x] 4.4 CẢNH BÁO chứ không HỎNG, lý do ghi trong docstring `check_tren()`, dẫn đúng ranh
      giới đã chốt ở đầu file: *"có sửa được bằng cách nạp lại không"*
- [x] 4.5 Dùng tập rỗng **thật**, không dựng database giả. Thêm phép kiểm
      `Gateway rows in fact_perf_daily carry method and response_code` — bảng đó chỉ có
      monitoring (669 dòng), gateway **0 dòng**. Chạy ra:

          [ note ] Gateway rows in fact_perf_daily carry method and response_code
                   CHUA KIEM DUOC - 0 dong de quan sat. Day KHONG phai ket qua dat.

      Cơ chế hoạt động. Không xoá một dòng dữ liệu nào
- [x] 4.6 Lưu ý **4 → 7**, và cả ba cái mới đều đúng loại:
      *Foreign keys are read from the database…* (độ trôi 13/36) ·
      *Gateway cache tokens match the invoice cache SKU* (chưa kiểm được) ·
      *Gateway rows in fact_perf_daily…* (0 dòng quan sát).
      **Bốn lưu ý cũ giữ nguyên**, không cái nào biến mất. Số hỏng vẫn **0**

## 5. Đối chiếu token cache — CHẶN sau nhóm 4

- [x] 5.1 `group_h_cache_reconciliation()` — nhóm **H. Cache reconciliation**. So theo
      `(ngày × agent)`, `INTERSECT` hai tập ngày trước khi so
- [x] 5.2 Ba kết cục cài đủ: không ngày chung → CẢNH BÁO kèm **cả hai** khoảng; có ngày chung
      nhưng gateway rỗng → CẢNH BÁO nêu vế rỗng; cả hai có số → `FULL OUTER JOIN` theo
      (ngày, agent) rồi áp ngưỡng
- [x] 5.3 Hai nhánh rỗng đều `a.note(WARN, ...)` và **không** đi qua `check()`. Chuỗi
      *"Day KHONG phai ket qua dat"* nằm ngay trong thông điệp
- [x] 5.4 `NGUONG_LECH_CACHE = 0.01`, kèm khối chú thích nêu rõ: chốt trước khi có số, lý do
      chọn 1% chứ không phải 0, và **chưa có cơ sở đo đạc**
- [x] 5.5 Chạy ra đúng như dự kiến:

          [ note ] Gateway cache tokens match the invoice cache SKU
                   CHUA KIEM DUOC - khong ngay nao ca hai nguon cung co du lieu.
                   gateway 2026-08-31 -> 2026-08-31 (1 ngay) ·
                   hoa don 2026-01-05 -> 2026-08-29 (214 ngay).
                   Day KHONG phai ket qua dat.
- [x] 5.6 Nhánh thứ hai đếm `COUNT(cached_tokens)` chứ không `SUM`, nên NULL **không** thành
      0. Thông điệp nói thẳng *"NULL KHONG duoc coi la 0"*

## 6. `check_api.py`: hỏi máy chủ, không chép câu SQL — CHẶN sau nhóm 4

- [x] 6.1 `nguon_gateway(c, base)` — 4 phép qua endpoint: `/api/usage` mang
      `token_source='gateway'` · `/api/usage-hourly` có nguồn gateway · bảng giờ vẫn
      **không** có `billing` · `/api/performance` trả phân vị số thô không mang ô histogram
- [x] 6.2 Docstring nêu thẳng: **không chép câu SQL của `audit_db.py`**, kèm bẫy 21/08 khi
      `tools/dien_tap_gateway.py` chép câu SQL của `store.py` rồi đo bằng logic đã bỏ
- [x] 6.3 `Check.expect_tren()` — cùng ba kết cục. Thêm `Check.notes`, và dòng tổng kết nay
      đếm cả `notes`: giấu chúng khỏi tổng số là làm đúng cái việc mà cơ chế này đi chống
- [x] 6.4 **31 kiểm · 31 đạt · 0 lưu ý · 0 hỏng** (mốc 27/27). Bốn phép mới đều ĐẠT kèm mẫu
      số: `(1 rows)` · `(5 rows)` · `(1 rows)`

## 7. Master Plan và tài liệu

- [x] 7.1 Cột Kết quả dòng 20 ghi **XONG cả hai vế — nhưng vế 2 XONG theo nghĩa PHÉP KIỂM
      ĐÃ CÓ VÀ NÓ NÓI THẲNG LÀ CHƯA KIỂM ĐƯỢC**, không phải theo nghĩa đã đối chiếu xong.
      Nêu đủ bốn phép của vế 1 kèm số đo (13/36 khoá ngoại · ngưỡng ngày · 5 bảng), và
      cả hình dạng lỗi đã sửa. Bản lưu
      `docs/reference/ban-luu/Master Plan API Gateway 2026-09-03-truoc-stt7.xlsx`.
      **Không** đổi cột Mốc, **không** tô ô Gantt
- [x] 7.2 Ghi thẳng trong ô: `ĐIỀU KIỆN ĐỂ NÓ CHẠY: một ngày mà Gateway và hoá đơn Google
      cùng có dữ liệu — hoá đơn về trễ ~1 ngày nên chỉ cần Gateway chạy thêm vài ngày
      liên tục là đủ`, kèm hai khoảng ngày rời nhau làm bằng chứng
- [x] 7.3 Thêm phụ lục **"Cách đọc kết quả `scripts/audit_db.py`"** — bảng ba mức
      (`ok` / `note` / `FAIL`), giải thích vì sao nhãn nay kèm số dòng đã soi, và câu
      quan trọng nhất: **`note` KHÔNG phải một dạng ĐẠT nhẹ hơn** — số `note` tăng sau
      một lần sửa thường là dấu hiệu **tốt**
- [x] 7.4 Nối **phiên chiều** vào `docs/reference/nhat-ky-03-09-sang.md` (mục 10–15): ba thứ
      đo được trước khi viết mã · cơ chế mẫu số · đối chiếu cache chưa chạy được · bốn
      phép đổi màu · nghiệm thu · và lỗi bind IP bắt được ngoài phạm vi.
      Sửa tiêu đề file cho đúng phạm vi thật (ba change trong một ngày)

## 8. Nghiệm thu

- [x] 8.1 **72 kiểm · 65 đạt · 7 lưu ý · 0 hỏng** (mốc 68 · 64 · 4 · 0). Lưu ý tăng 4 → 7 là
      **đúng** — xem 4.6. **Hỏng vẫn 0**
- [x] 8.2 **31 kiểm · 31 đạt · 0 lưu ý · 0 hỏng** (mốc 27 · 27 · 0)
- [x] 8.3 **36/36** quan hệ được kiểm, **0** quan hệ treo
- [x] 8.4 **0 dòng** tương lai trên cả năm bảng
- [x] 8.5 Ra đúng CẢNH BÁO *"chưa kiểm được"*, kèm cả hai khoảng ngày — xem 5.5
- [x] 8.6 Chạy **hai lần liên tiếp**: `(72, 65, 7, 0)` và `(72, 65, 7, 0)` — **khớp**
- [x] 8.7 `usage_resolved` **khớp 4/4 khoá, lệch 0** (rows · tokens · calls · cost_usd).
      Change này không đụng dữ liệu, và số liệu chứng minh điều đó
