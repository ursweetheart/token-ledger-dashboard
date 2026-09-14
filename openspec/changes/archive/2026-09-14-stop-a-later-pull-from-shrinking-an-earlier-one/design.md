## Context

Dữ liệu đi qua ba tầng. Chỉ tầng đầu là đã ghi thêm thật:

```
  Google ──kéo──▶  data/raw_*/<ngày>/       ──gộp──▶   bản gộp            ──nạp──▶   database
                   ✅ mỗi lần kéo 1 thư mục            ❌ lần sau làm co              xoá dòng rồi nạp lại
                      không sửa, không xoá                lần trước                   (vô hại nếu bản gộp đủ)
```

Số đo ngày 14/09/2026, chi tiết ở `docs/reference/luat-trien-khai-tu-dong-13-09.md` mục 2:

| Nguồn | Hiện trạng | Đã mất gì |
|---|---|---|
| Monitoring | `merge_monitoring.py:83-95` cho bản mới thắng | 14 điểm, 11.262 token |
| Histogram độ trễ | `merge_latency_daily.py:185-190` đòi đúng 1 lần kéo | `latency-daily.csv` bắt đầu 09/06, bản sao tay 17/08 bắt đầu 01/05 |
| Nhà cung cấp | `load_provider.py:196-198` đọc lần kéo mới nhất | Chưa mất (mới có 1 lần kéo), sẽ mất ở lần kéo thứ hai |

Hai điều khiến thứ tự làm việc bị ràng buộc, cả hai đã chạy hoặc đọc thật:

- `update_dashboard.py` bước 7 gọi `merge_latency_daily.py` không có `--in`, và thoát 1 trên thư mục có 4 lần kéo. Lỗi này đang chặn đường tới bước 8.
- Bước 8 dẫn tới `connect.rebuild()`, và hàm này gọi `DROP SCHEMA public CASCADE` (`db/connect.py:264`). `docker/read-only-api.sql` cấp quyền cho `api_readonly` bằng `GRANT SELECT ON ALL TABLES IN SCHEMA public` và `ALTER DEFAULT PRIVILEGES ... IN SCHEMA public`. Cả hai gắn với schema, nên mất khi schema bị xoá. Đó là vụ 02/09.

Ràng buộc làm việc: `data/` là thứ duy nhất mất là mất vĩnh viễn. Các bộ `load_*` chỉ đọc file. Không tự ý commit. Mọi thao tác ghi vào database thật phải hỏi trước.

## Goals / Non-Goals

**Goals:**
- Không lần kéo nào làm co được dữ liệu của lần kéo trước, ở cả ba nguồn.
- Mọi ca lệch để lại dấu vết đọc được sau khi lệnh kết thúc.
- `update_dashboard.py` bước 7 chạy được trên thư mục có nhiều lần kéo.
- Dựng lại database không xoá schema, không mất quyền.
- Nghiệm thu bằng số trên dữ liệu thật.

**Non-Goals:**
- **Ghi thêm ở tầng database** (upsert thay cho xoá rồi nạp). Bị chặn bởi ba điều đã đọc được: `fact_monitoring` không có khoá chính (`001_baseline.sql:451-483`); `account_id` được đánh số lại mỗi lần nạp (`load_org.py:509`, `enumerate(sorted(...))`); và chỉ ghi thêm thì dòng sai không bao giờ bị xoá. Chỗ làm mất dữ liệu thật nằm ở tầng gộp, không ở tầng database.
- Giải thích vì sao Google trả thiếu ở mép cửa sổ.
- Gỡ luật cấm dịch vụ `tools` trong lệnh triển khai.
- Rút ngắn khoảng ~78 giây dashboard thấy bảng rỗng trong lúc dựng lại. Khoảng này có từ trước và không đổi.
- Ralli và TLA HD. Mỗi lần kéo đã trả toàn bộ lịch sử: số bản ghi Ralli tăng dần 8.216 → 8.972 qua 5 lần kéo, và TLA HD luôn xin từ 2026-02-01.

### Điều kiện change này KHÔNG lo, và nếu vi phạm thì vẫn mất phần đầu

Change chặn việc lần kéo sau **làm co** lần kéo trước. Nó không sinh ra được dữ liệu mà không lần kéo nào còn giữ. Đo ngày 14/09/2026 trên mọi lần kéo hiện có:

| Họ phép đo | Độ rộng cửa sổ (từ ngày có dữ liệu sớm nhất tới ngày kéo) |
|---|---|
| Token quota | 91–114 ngày |
| `api_request_count` | 91–195 ngày (195 chỉ ở lần kéo 06/08; các lần sau 91–101) |
| Histogram độ trễ | 91–114 ngày |

Hiện chưa có khoảng hở: hai lần kéo cách nhau xa nhất là 12 ngày, và mọi cặp lần kéo liền nhau chồng lên nhau ≥ 79 ngày.

1. **Phải kéo đều.** Hai lần kéo cách nhau hơn độ rộng cửa sổ (hôm nay khoảng 91 ngày) thì những ngày ở giữa **mất vĩnh viễn**. Con số 91 là cửa sổ **hôm nay**, và nó từng dao động từ 91 tới 195 ngày, nên đừng chờ tới sát ngưỡng. Change không tự động hoá việc kéo, và lệnh triển khai không kéo (dịch vụ `tools` bị cấm).
2. **Phải sao lưu `data/`.** Thư mục này không nằm trong git, và hôm nay là bản duy nhất. Mất ổ đĩa, hoặc chuyển máy chủ mà không chép các thư mục kéo cũ, là mất mọi ngày đã trượt khỏi cửa sổ. Hiện đó là mọi ngày trước 11/06 với token quota.
3. **Lần kéo đầu tiên trên một máy mới thì không có gì để so.** Nếu nó bị cụt ở mép, luật "số lớn hơn" không có số nào lớn hơn để giữ.
4. **Ralli và TLA HD** chỉ an toàn chừng nào hai app còn giữ toàn bộ lịch sử. Ralli có sẵn API `POST /logs/cleanup`. Nếu app bắt đầu xoá log, bộ nạp chỉ đọc lần kéo mới nhất sẽ mất phần đầu, và change này không chặn được.

## Decisions

### D1. Khi hai lần kéo lệch: giữ số lớn hơn

| Luật | Trên 14 ca đã đo | Trường hợp đã biết mà nó sai |
|---|---|---|
| Bản mới thắng (hiện tại) | 0/14 | Lần kéo mới bị cụt ở mép |
| Bản cũ thắng | 14/14 | Dữ liệu về muộn làm lần kéo sau **lớn** hơn |
| Chốt sau N giờ tính từ mép cửa sổ | Tối đa 11/14 (chưa kiểm từng điểm có đúng ở mép không) | 3 ca tranquil 12/08 chỉ cũ 4 ngày, không nằm ở mép nào. Còn phải tính mép cửa sổ cho từng chuỗi |
| **Số lớn hơn** | **14/14** | Google sửa **giảm** thật (ví dụ khử đếm đôi). Chưa gặp lần nào |

Chọn số lớn hơn. Dữ liệu không phân biệt được nó với "bản cũ thắng", nhưng nó đúng thêm ở một trường hợp đã biết. Khi xảy ra trường hợp nó sai, dấu vết nằm trong tệp ca lệch (D2).

Giới hạn, phải ghi bằng chú thích `ponytail:` ngay trong mã: với phân vị (`ALIGN_PERCENTILE_95/99`), "lớn hơn" không đồng nghĩa "đủ hơn". Nếu một ngày cần luật riêng cho phân vị, cách nâng cấp là lấy giá trị từ lần kéo có `api_request_count` lớn hơn ở cùng phút.

### D2. Tệp ca lệch nằm cạnh kết quả, không nằm trong thư mục mà khâu nạp quét

| Nguồn | Tệp ca lệch | Vì sao đặt ở đó an toàn |
|---|---|---|
| Monitoring | `data/da_xu_ly/du_lieu_giam_sat/<tên đầu ra>.lech.csv` | `load_monitoring.py:57` chỉ lấy **thư mục**, rồi `:90` đọc `*.csv` **bên trong** thư mục đó |
| Histogram | `<--out bỏ đuôi>.lech.csv`, ví dụ `latency-daily.lech.csv` | `build_performance.py:44-45` đọc đúng một đường dẫn cố định. `merge_latency_daily.py` chỉ quét `*.jsonl` và thư mục con |
| Nhà cung cấp | Dòng log, mỗi ca một dòng, cộng một dòng tổng | Bộ `load_*` chỉ đọc file, không ghi vào `data/` |

Cột của tệp: mọi cột khoá, `pull_a`, `value_a`, `pull_b`, `value_b`, `kept`. Tệp luôn có dòng tiêu đề.

### D3. Histogram: khử trùng lặp theo điểm trước, rồi mới cộng theo ngày

Khoá = `(gcp_project_id, ts_utc, res_service, res_method, res_location, res_credential_id)`. Khi trùng khoá, giữ điểm có `count` lớn hơn. Kiểm `bucketOptions` trên **mọi** điểm của mọi lần kéo, giữ nguyên luật dừng khi gặp bộ thứ hai.

Không cộng thẳng histogram của các lần kéo. Các lần kéo chồng lên nhau phần lớn khoảng ngày (mỗi lần xin 196 ngày; cửa sổ thật của Google chưa đo), nên cộng thẳng là nhân đôi mọi ngày chung.

### D4. Nhà cung cấp: gộp trong từng lần kéo trước, giữ số lớn hơn giữa các lần kéo sau

Giữ nguyên `doc_mot_file` và `chon_nhanh` (đối chiếu PerDay/PerMinute) **trong từng lần kéo**. Sau đó, với mỗi khoá `(ngày, project, model, đại lượng)`, giữ số lớn hơn giữa các lần kéo. Làm theo thứ tự này để phép đối chiếu PerDay/PerMinute không bị lẫn số của hai lần kéo khác nhau.

Giới hạn: một ngày bị cắt ở mép trong **mọi** lần kéo thì vẫn thiếu. Luật này không tự sinh ra dữ liệu.

### D5. Dựng lại: migration tại chỗ, rồi TRUNCATE trong một giao dịch

```
connect.rebuild(dsn):
    kiểm 02_catalog.sql tồn tại            # giữ nguyên: phải trước mọi kết nối
    apply_migrations(dsn)                  # máy trắng: dựng từ 001; máy cũ: không làm gì
    cn = open_db(dsn)
    BEGIN
      bảng = pg_tables WHERE schemaname='public', trừ KEEP_ON_REBUILD (alembic_version, ref_source)
      nếu có bảng: TRUNCATE TABLE <bảng> RESTART IDENTITY CASCADE
      run_sql_file(02_catalog.sql)
    COMMIT
    return cn, "%s"                        # hợp đồng trả về không đổi
```

- **Danh sách bảng đọc từ `pg_tables`, không ghi cứng.** Migration 008, 011, 012 đều thêm bảng. Danh sách ghi cứng sẽ lỗi thời ngay ở migration kế tiếp, và lỗi theo cách im lặng: bảng mới không được xoá dòng, rồi đụng khoá chính khi nạp.
- **`TRUNCATE` thay cho `DELETE`.** Một câu lệnh có `CASCADE` thì không phải xếp thứ tự khoá ngoại, và nhanh hơn. `TRUNCATE` không đụng bảng, view, schema, hay quyền đã cấp.
- **Một giao dịch.** Không có lúc nào danh mục trống một nửa mà vẫn thấy được từ bên ngoài.
- **Giữ bảng mà migration ghi dòng.** Bản đầu của D5 giả định mọi dữ liệu gieo nằm trong `02_catalog.sql`. **Sai.** `001_baseline.sql:364` gieo 4 dòng `ref_source`. Code cũ không gặp lỗi vì `DROP SCHEMA` làm migration chạy lại. Code mới trên một database đã có sẵn thì không chạy lại migration, nên `TRUNCATE` sẽ xoá mất 4 dòng đó mãi mãi. Đo ngày 14/09/2026 lần dựng đầu trên database diễn tập: `load_ralli` chết với `fact_call_source_fkey`. Phép kiểm dùng kết nối giả không bắt được lỗi này; chỉ lần diễn tập trên database thật mới bắt được. Cách sửa: hằng `KEEP_ON_REBUILD`, cộng một phép kiểm quét mọi migration tìm `INSERT INTO` và đòi mỗi bảng tìm thấy phải có trong hằng. `ref_source` không có khoá ngoại trỏ đi (đã truy vấn `pg_constraint`), nên `CASCADE` từ các bảng khác không lan tới nó.
- **Phương án bị loại:** giữ `DROP SCHEMA` rồi chạy lại `docker/read-only-api.sql`. File đó cần 4 biến psql và vai admin, và chỉ chạy qua `api-db-init` trong compose. Ngoài compose sẽ có một khoảng mất quyền.
- **Phương án bị loại:** không xoá gì, chỉ upsert danh mục. Dòng danh mục đã bỏ trong `gen_catalog.py` sẽ nằm lại mãi, còn các bảng fact thì đụng khoá chính khi nạp lại.

Hệ quả phụ, chấp nhận được: `ref_load_run` bị xoá dòng nên nhịp tim về 0. `ledger-refresh` ghi lại ở chu kỳ kế tiếp (mặc định 300 giây).

### D6. Thứ tự: bỏ DROP SCHEMA trước, sửa bước 7 sau cùng

Nhóm việc về histogram (tháo chốt bước 7) chỉ được bắt đầu khi nhóm dựng lại đã xong và phép kiểm đã xanh. Tasks có một bước kiểm điều kiện này; điều kiện không đạt thì dừng.

### D7. Không ghi đè bản gộp cũ

Bước gộp đặt tên đầu ra là `<lần kéo mới nhất>-gop`. Tên `2026-09-12-1m-gop` **đã tồn tại**, và bước gộp không dọn thư mục đích. Trước khi gộp thật, đổi tên bản cũ thành `2026-09-12-1m-gop.luat-ban-moi-thang`. Tên này không kết thúc bằng `-gop`, nên `load_monitoring.py:61` không chọn nhầm. Bản cũ vẫn còn để đối chứng.

`latency-daily.csv` cũng được giữ lại thành `latency-daily_ban-luu-<ngày>.csv` trước khi sinh lại.

### D9. Chỉ gộp thư mục đúng khuôn tên

| Nguồn | Khuôn | Loại ra |
|---|---|---|
| Monitoring | `^\d{4}-\d{2}-\d{2}-1m$` | Lần kéo 1 giờ; lần kéo mang tên tài khoản |
| Histogram | `^\d{4}-\d{2}-\d{2}-\d+d-1m$` | Lần kéo 1 giờ |

Khuôn lấy từ chính chỗ sinh ra tên thư mục (`pull_monitoring.py:309-318`, `pull_latency_distribution.py:170-171`), không suy từ các tên đang có trên đĩa.

**Phương án bị loại:** thêm độ mịn vào khoá gộp. Làm vậy thì lần kéo 1 giờ không còn đụng khoá nữa, nhưng lại bị **cộng chồng** lên dữ liệu 1 phút ở tầng nạp và tầng tổng hợp. Lỗi chỉ đổi chỗ, không mất đi.

**Phương án bị loại:** giữ cách quét mọi thư mục, rồi dặn người vận hành dùng `--dot`. Cách này đã hỏng một lần ngày 12/09: phải chạy lại hai vòng mới ra, và phải xoá tệp bằng tay.

Danh sách tường minh (`--dot`, `--in`) vẫn được tôn trọng, kèm cảnh báo cho mỗi tên không khớp khuôn. Người vận hành vẫn gộp được lần kéo đặc biệt khi họ biết mình đang làm gì.

Phải xong **trước** lần gộp thật ở task 3.6. Không thì lần gộp đó sẽ kéo lại `project-e62bad30-*`.

### D8. Nghiệm thu

`tools/baseline_db.py --save` trước, `--compare` sau. Công cụ này không chụp độ trễ, nhà cung cấp, hay quyền, nên đo thêm bằng truy vấn chỉ-đọc:

- tổng `value` token của `fact_monitoring` theo ngày 04/06, 11/06, 12/06;
- `MIN(day)` và `COUNT(*)` của `fact_latency_daily`;
- `COUNT(*)`, `MIN(day)`, `MAX(day)` của `fact_provider_daily`;
- số bảng và view mà `api_readonly` đọc được, qua `has_table_privilege`.

Mỗi khoá lệch trong `--compare` phải giải thích được bằng luật mới. Không nới phép so.

**Mốc đo ngày 14/09/2026 trên `token_ledger_v2`, trước change** (task 1.1 và 1.2). Tệp mốc nằm ở `var/baseline-2026-09-14-truoc.json`.

| Phép đo | Giá trị |
|---|---|
| `usage_resolved` | 1.385 dòng · 985.732.298 token · $347,962155 · 2026-01-01 → 2026-09-12 |
| `usage_by_account` | 360 dòng · 109.972.109 token |
| Số dòng | `account` 954 · `dim_agent` 8 · `dim_unit` 130 · `fact_usage_daily` 2.202 · `fact_billing_daily` 2.833 · `fact_monitoring` 726.051 · `fact_call` 9.393 · `fact_app_daily` 78 · `ref_source` 4 |
| `fact_usage_daily` theo nguồn | billing 1.106 · monitoring 679 · app 407 · gateway 10 |
| Token `fact_monitoring` | tổng 560.890.440 · 04/06: 8.726.974 · 11/06: 6.484.596 · 12/06: 3.948.791 |
| `fact_latency_daily` | monitoring 352 dòng, 2026-06-09 → 2026-09-12 · gateway 8 dòng, 2026-08-31 → 2026-09-11 |
| `fact_provider_daily` | 5 dòng, 2026-08-26 → 2026-09-01 |
| `api_readonly` | có `USAGE` trên `public`; đọc được 28/28 bảng và view |

`usage_resolved` chỉ chọn Monitoring cho những ngày không có hoá đơn. Ngày 11/06 có hoá đơn, nên +11.262 token **có thể không** hiện ở `usage_resolved`. Đây là dự đoán, phải đo rồi mới được kết luận.

## Risks / Trade-offs

- [Google sửa giảm thật, luật số lớn hơn giữ số phồng] → Tệp ca lệch luôn được ghi. Mỗi lần gộp in số ca lệch ra màn hình.
- [Phân vị: lớn hơn không có nghĩa là đủ hơn] → Chú thích `ponytail:` trong mã, và ghi trong spec.
- [TRUNCATE giữ khoá `ACCESS EXCLUSIVE` tới khi commit, `api` phải chờ] → Giao dịch chỉ gồm TRUNCATE và nạp danh mục, dưới vài giây. Phải đo trong lúc diễn tập.
- [Dựng lại vẫn xoá dòng. Máy chủ có `data/` ít hơn database sẽ mất dữ liệu] → Change này **không** chặn được. Ghi ở Open Questions.
- [Sửa bước 7 làm `CMD` của `tools` tới được bước 8] → D6. Và luật cấm dịch vụ `tools` vẫn giữ.
- [Hai phép kiểm Python cũ đang khoá `drop`] → Viết lại trong cùng nhóm việc. Mốc `EXPECTED_PY` trong CI đổi theo số đếm thật.
- [Gộp histogram trên 4 lần kéo tốn bộ nhớ] → Đo thời gian và bộ nhớ ở lần chạy thật đầu tiên.

## Migration Plan

1. Chụp mốc chỉ-đọc (D8).
2. Sửa mã theo thứ tự D6, mỗi nhóm có phép kiểm đỏ trước, xanh sau.
3. Sinh lại bản gộp theo D7, không ghi đè bản cũ.
4. Diễn tập dựng lại. Hỏi người dùng: dùng database riêng, hay dựng thẳng `token_ledger_v2` sau khi chụp mốc.
5. Nghiệm thu D8.

**Đã thực hiện ngày 14/09/2026:**

1. Sao lưu `token_ledger_v2` bằng `pg_dump -Fc` (5,7 MB, 23 mục dữ liệu bảng, đọc lại được bằng `pg_restore -l`).
2. Dựng lại `token_ledger_v2` bằng code mới: 11/11 bước đạt trong 50 giây, `api_readonly` vẫn đọc được 28/28 bảng và view, `ref_source` còn 4 dòng.
3. So với database diễn tập: `baseline_db` 24/24 khoá khớp, số D8 7/7 giống nhau. `audit_db` chỉ còn 1 FAIL có sẵn từ trước (cache token Gateway), không có FAIL mới. Vai `api_readonly` thật đọc được `usage_resolved`: 1.385 dòng, 985.168.786 token.
4. Xoá database diễn tập `token_ledger_rehearsal`.

**Quay lui nếu cần:** khôi phục bản `pg_dump` ở trên. Hoặc trả code cũ, đổi tên `2026-09-12-1m-gop.luat-ban-moi-thang` và `latency-daily_ban-luu-2026-09-14.csv` về tên cũ, rồi dựng lại.

**Quay lui:** `data/raw_*` không bị đụng tới. Trả mã cũ, đổi tên bản gộp cũ về như trước, rồi dựng lại, là ra đúng database cũ. `token_ledger` (bản legacy) vẫn giữ nguyên.

## Open Questions

- Có nên chặn việc dựng lại khi `data/` cho khoảng ngày **ngắn hơn** database hiện có không? Đây là rủi ro thật khi đưa lên máy chủ, nhưng chưa xảy ra lần nào.
- Vì sao Google trả thiếu ở phút mép cửa sổ?
- ~~Sau khi dựng lại, 5 dòng lệch giữa `token_ledger` và `token_ledger_v2` (04/06, 11/06, 12/06) có khớp lại không?~~ **Đã trả lời 14/09/2026 (task 6.4): CÓ.** So 17.762 dòng `fact_monitoring` của ba ngày đó trên 12 cột tự nhiên: `token_ledger` với `token_ledger_v2` lệch đúng 5 dòng (`api_request_count` 04/06 00:00 là 4 → 0; tranquil 11/06 00:00 có `api_request_count` 2 → 1, token 4406 → 944, `requests` 2 → 1; `api_request_count` 12/06 02:26 là 3 → 0). `token_ledger` với database dựng bằng luật mới lệch **0 dòng**. Vậy việc trích 5 dòng từ `token_ledger` trước khi xoá database cũ **không còn cần**, sau khi `token_ledger_v2` được dựng lại bằng luật mới.
