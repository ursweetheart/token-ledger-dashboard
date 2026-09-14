## 1. Mốc trước khi đổi (chỉ đọc)

- [x] 1.1 Hỏi người dùng trước. Sau đó chạy `tools/baseline_db.py --save var/baseline-2026-09-14-truoc.json` trên `token_ledger_v2`
- [x] 1.2 Đo thêm bằng truy vấn chỉ-đọc, ghi vào `design.md` (D8): tổng token `fact_monitoring` ngày 04/06, 11/06, 12/06; `MIN(day)` và `COUNT(*)` của `fact_latency_daily`; `COUNT`, `MIN(day)`, `MAX(day)` của `fact_provider_daily`; số bảng và view `api_readonly` đọc được
- [x] 1.3 Chạy `node --test tests/*.test.js` và `python -m unittest discover -s tests -p "test_*.py"`, ghi số phép kiểm hiện có. **Đo 14/09: JS 51/51, Python 11/11**

## 2. Dựng lại không DROP SCHEMA (phải xong trước nhóm 5)

- [x] 2.1 Đọc lại `connect.run_sql_file` và `open_db`, xác nhận vẫn không có commit giữa chừng. Đã soát trước lúc viết change (14/09): `run_sql_file` chỉ `cur.execute` (`db/connect.py:210-213`), `connect.py` không đặt `autocommit`, và `02_catalog.sql` không có `BEGIN`/`COMMIT`. Nếu một trong ba điều này đã đổi thì điều chỉnh D5 trước khi viết mã
- [x] 2.2 Viết lại `tests/test_connect_migrations.py::RebuildTests` theo thứ tự mới: kiểm danh mục → migrate → mở kết nối → TRUNCATE (danh sách đọc từ `pg_tables`, trừ `alembic_version`) → nạp danh mục → commit. Khẳng định không câu lệnh nào chứa `DROP SCHEMA`. Chạy và thấy **đỏ** trên mã cũ
- [x] 2.3 Thêm phép kiểm: database trắng (không bảng nào) thì bỏ qua TRUNCATE, không ném lỗi
- [x] 2.4 Giữ phép kiểm "thiếu danh mục thì dừng trước khi mở kết nối", và nó phải vẫn xanh
- [x] 2.5 Sửa `connect.rebuild()` cho mọi phép kiểm nhóm 2 xanh. Giữ hợp đồng trả về `(connection, "%s")`
- [x] 2.6 Sửa docstring và chú thích cho khớp đường mới: `connect.rebuild()`, `scripts/rebuild_db.py` (đầu tệp và `STEPS`), `db/load_billing.py` (trợ giúp của `--rebuild`), `scripts/check_db_grants.py`

## 3. Gộp Monitoring giữ số lớn hơn

- [x] 3.1 Viết phép kiểm cho `merge_project` với 4 scenario của spec: lần sau nhỏ hơn, lần sau lớn hơn, khoá chỉ ở một lần, trùng khít. Chạy và thấy **đỏ**
- [x] 3.2 Viết phép kiểm cho tệp ca lệch: có ca lệch thì số dòng bằng số in ra; không có ca lệch thì chỉ có dòng tiêu đề; tệp nằm ngoài thư mục gộp. Chạy và thấy **đỏ**
- [x] 3.3 Viết phép kiểm cho khuôn tên thư mục (D9): `2026-09-04-1h` và `2026-09-04-1h-dinhthinhan18111971` bị bỏ qua và có tên trong danh sách in ra; `--dot` với tên không khớp khuôn thì vẫn đọc và in cảnh báo. Chạy và thấy **đỏ**
- [x] 3.4 Sửa `scripts/merge_monitoring.py`: lọc thư mục theo khuôn `^\d{4}-\d{2}-\d{2}-1m$`, giữ số lớn hơn, ghi `<tên đầu ra>.lech.csv` cạnh thư mục gộp, thêm chú thích `ponytail:` về giới hạn với phân vị. Mọi phép kiểm nhóm 3 xanh
- [x] 3.5 Chạy gộp **mặc định** (không `--dot`) vào một thư mục đầu ra **tạm** trong scratchpad. Nghiệm thu: đúng 6 lần kéo được đọc, 2 thư mục bị bỏ qua, không có tệp `project-e62bad30-*`, và 4 con số của spec (14 ca lệch, 14 giảm / 0 tăng, +11.262 token, 4406 ở 11/06 00:00). Không khớp thì dừng và điều tra, không nới phép so. **Đo 14/09: 10/10 đạt. 2.952.954 dòng vào → 726.051 ra; số dòng từng project khớp cả 7 với `2026-09-12-1m-gop` cũ (luật mới chỉ đổi giá trị, không đổi tập khoá); 77,9 giây; bộ nhớ đỉnh 196 MB**
- [x] 3.6 Hỏi người dùng. Đổi tên `data/da_xu_ly/du_lieu_giam_sat/2026-09-12-1m-gop` thành `2026-09-12-1m-gop.luat-ban-moi-thang`, rồi gộp thật vào tên mặc định. **Người dùng đồng ý 14/09. Gộp thật: 6 lần kéo, bỏ qua 2 thư mục, 2.952.954 → 726.051 dòng, 14 ca lệch (pro-tuner 8, tranquil 6), tệp `2026-09-12-1m-gop.lech.csv` nằm cạnh thư mục gộp**
- [x] 3.7 Xác nhận **không cần database**: import `db.load_monitoring` rồi in `MONITORING_DIR` và các tệp `*.csv` trong đó. Phải là `2026-09-12-1m-gop`, đúng 7 tệp, không có tệp ca lệch. **KHÔNG chạy `load_monitoring.py --limit` lên `token_ledger_v2`**: dòng 95 chạy `DELETE FROM fact_monitoring` trước khi nạp, nên "lát mỏng" sẽ xoá gần hết bảng thật (sửa 14/09 sau khi soát lại task)

## 4. Nạp nhà cung cấp đọc mọi lần kéo

- [x] 4.1 Viết phép kiểm theo spec: ngày D đủ ở lần kéo A và thiếu ở lần kéo B thì giữ số của A; ngày chỉ có ở lần kéo cũ thì vẫn còn; ca lệch hiện trong log. Chạy và thấy **đỏ**
- [x] 4.2 Sửa `db/load_provider.py`: khi không có `--dir`, đọc mọi thư mục khớp khuôn. `chon_nhanh` chạy trong từng lần kéo, rồi giữ số lớn hơn giữa các lần kéo, và log từng ca lệch cộng một dòng tổng. Phép kiểm xanh
- [x] 4.3 Chạy `db/load_provider.py --kho` (chỉ in, không ghi database) trên dữ liệu thật và ghi lại số thư mục đã đọc. **Đo 14/09: đọc 1 lần kéo (`2026-09-04-1h-dinhthinhan18111971`), 0 ca lệch, 5 dòng, 4 ngày, mã thoát 0. Hai dòng `KIEM CHEO` lệch (26/08, 29/08) là cảnh báo có sẵn từ trước, không do change này**

## 5. Gộp histogram đọc mọi lần kéo (tháo chốt bước 7)

- [x] 5.1 **Cổng:** xác nhận nhóm 2 đã xong và mọi phép kiểm nhóm 2 đang xanh. Chưa đạt thì DỪNG, không làm tiếp nhóm này
- [x] 5.2 Viết phép kiểm theo spec: cùng phút có ở hai lần kéo, `count` 4 và 3, thì chỉ cộng điểm 4, một lần; `bucketOptions` thứ hai thì dừng; ca lệch được ghi; thư mục không khớp `^\d{4}-\d{2}-\d{2}-\d+d-1m$` bị bỏ qua và có tên trong danh sách in ra. Chạy và thấy **đỏ**
- [x] 5.3 Sửa `scripts/merge_latency_daily.py`: đọc mọi lần kéo đúng khuôn (D9), khử trùng lặp theo khoá của D3, ghi tệp ca lệch cạnh `--out` (không có `--out` thì in ra `stderr`). Phép kiểm xanh
- [x] 5.4 Chạy đúng như bước 7 nhưng `--out` trỏ vào tệp tạm trong scratchpad. Mã thoát phải là 0, ngày sớm nhất phải không muộn hơn 2026-05-01. Ghi lại thời gian chạy. **Đo 14/09: mã thoát 0, 1 giây, 4 lần kéo, 48.578 điểm (18.353 trùng giữa các lần kéo, 6 lệch `count`). Ra 445 dòng từ 2026-05-01, bản cũ 352 dòng từ 2026-06-09. So với bản cũ: 0 cặp (ngày, project) bị mất, 0 cặp nhỏ hơn, 204 cặp lớn hơn, 93 cặp mới**
- [x] 5.5 Hỏi người dùng. Đổi tên `latency-daily.csv` hiện có thành `latency-daily_ban-luu-2026-09-14.csv`, rồi sinh lại tệp thật. **Người dùng đồng ý 14/09. Sinh lại: 445 dòng từ 2026-05-01, 6 ca lệch ghi ở `latency-daily.lech.csv`**

## 6. Diễn tập và nghiệm thu trên database

- [x] 6.1 Hỏi người dùng: dựng vào một database diễn tập riêng, hay dựng thẳng `token_ledger_v2` sau khi đã có mốc 1.1. **Người dùng chọn database diễn tập riêng `token_ledger_rehearsal` (14/09)**
- [x] 6.2 Chạy `scripts/rebuild_db.py`. Bước `check_db_grants.py` phải đạt. `api_readonly` phải đọc được mọi bảng và view mà **không** chạy lại `docker/read-only-api.sql`. Đo thời gian giữ khoá của giao dịch TRUNCATE. **Đo 14/09 trên `token_ledger_rehearsal`. Lần dựng đầu LỘ LỖI: `TRUNCATE` xoá cả `ref_source` (do migration 001 gieo), `load_ralli` chết với `fact_call_source_fkey` → sửa bằng `KEEP_ON_REBUILD` + phép kiểm quét migration, xoá và tạo lại DB diễn tập. Sau khi sửa: lần 1 đạt 10/11, bước quyền trượt đúng dự kiến (DB mới chưa cấp quyền) → cấp quyền bằng `read-only-api.sql` → `check_db_grants` 28/28 → lần 2 đạt 11/11 trong 64 giây, `api_readonly` vẫn 28/28 mà không chạy lại SQL, `ref_source` còn 4 dòng. Bước 1 (migration + TRUNCATE + danh mục + hoá đơn) mất 3 giây, là giới hạn trên của thời gian giữ khoá. Vai `api_readonly` thật vẫn đăng nhập được `token_ledger_v2`**
- [x] 6.3 Chạy `tools/baseline_db.py --compare var/baseline-2026-09-14-truoc.json`, cộng các số của 1.2. Mỗi khoá lệch phải giải thích được bằng luật mới. Không nới phép so. **Đo 14/09: 19/24 khớp, 5 lệch, và cả 5 đã giải thích được bằng từng dòng. Lưu ý: 4 khoá được giải thích bằng sổ Gateway MỚI HƠN chứ không bằng luật mới, nên khác lời tiêu chí gốc. (a) `fact_call` +60, `fact_usage_daily` +1, nguồn gateway +1, `cost_usd` +0,004165: nguồn `app` giống hệt (8.972); nguồn `gateway` 421 → 481, dòng mới nhất 11/09 13:30 → 12/09 17:18. `audit_db` trên v2 tự báo đúng 60 dòng này vắng, vì `ledger-refresh` không chạy. (b) `usage_resolved.tokens` −563.512: so từng dòng thì chỉ 3 dòng khác. 11/06 và 12/08 (Sale Agent) có `calls` +1, do luật mới. 12/09 (CRM Feedback) đổi `token_source` monitoring 568.060 → gateway 4.548, và 568.060 − 4.548 = 563.512. Thêm số D8: token Monitoring +11.262 (11/06 +3.462), độ trễ Monitoring 352 → 445 dòng từ 01/05, nhà cung cấp và quyền không đổi**
- [x] 6.4 So các dòng `fact_monitoring` ngày 04/06, 11/06, 12/06 với `token_ledger`. Ghi kết quả vào Open Questions của `design.md`. **Đo 14/09: 17.762 dòng mỗi bên; `token_ledger` với v2 lệch đúng 5 dòng, với database diễn tập lệch 0 dòng**
- [x] 6.5 Chạy `scripts/audit_db.py`, mọi phép kiểm phải đạt. **Tiêu chí đổi ngày 14/09 theo quyết định của người dùng (phương án a): "không có FAIL MỚI so với `token_ledger_v2` trước change". Lý do: FAIL còn lại có sẵn từ trước và nằm ngoài phạm vi change. Theo tiêu chí gốc thì chưa đạt (đo 14/09).** Trên database diễn tập: 1 FAIL, "Gateway cache tokens match the invoice cache SKU" (vd 07/09 agent 1: gateway 0, hoá đơn 83.215). FAIL này **có sẵn trên `token_ledger_v2`** (chạy cùng lệnh). FAIL thứ hai của v2, "60 dòng Gateway vắng trong fact_call", không còn trên database diễn tập. Change không tạo ra FAIL mới, nhưng không đánh dấu xong vì làm vậy là nới phép kiểm. Chờ người dùng quyết

## 7. Tài liệu, CI, và đóng change

- [x] 7.1 Cập nhật `EXPECTED_PY` trong `.github/workflows/ci.yml` bằng số đếm thật ở máy, kèm ngày đo
- [x] 7.2 `docs/reference/toan-trinh-du-lieu.md`: bước 1 không còn xoá schema. Thêm hai điều kiện change không lo được, kèm số đo cửa sổ 14/09: phải kéo Monitoring và độ trễ đều (hôm nay cửa sổ khoảng 91 ngày, hai lần kéo xa nhất đang cách 12 ngày), và phải sao lưu `data/`
- [x] 7.3 `docs/reference/luat-trien-khai-tu-dong-13-09.md`: bước 7 đã sửa, nên đường tới bước 8 đã mở. Luật cấm dịch vụ `tools` vẫn giữ, và nêu lại vì sao
- [x] 7.4 Chạy lại cả hai bộ phép kiểm, số khớp mốc mới. **Đo 14/09: JS 51/51, Python 35/35 (thêm phép kiểm quét migration sau lỗi `ref_source`), khớp `EXPECTED_JS` 51 và `EXPECTED_PY` 35. Container `python:3.12-slim` trắng, không có `psycopg2`: 35/35**
- [x] 7.5 `openspec validate stop-a-later-pull-from-shrinking-an-earlier-one --strict`
