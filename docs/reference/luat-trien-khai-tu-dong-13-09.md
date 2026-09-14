# Bốn luật cho lệnh triển khai tự động — đo ngày 13/09/2026

Ghi trong lúc làm change `run-every-check-on-every-push`. Change đó **chỉ làm phần CI**; bốn luật
dưới đây thuộc về phần CD sẽ làm sau, và được đo trong lúc khảo sát để không phải đo lại.

> **Sửa 14/09/2026.** Bản 13/09 ghi nguyên nhân mất 3.462 token là "cửa sổ Monitoring trượt", và
> ghi ở mức *suy luận*. Đo lại thì **sai**. Nguyên nhân thật là luật gộp "bản mới thắng" gặp một lần
> kéo bị cụt ở mép cửa sổ. Mục 2 đã viết lại theo số đo mới. Luật 1 vẫn đứng, nhưng giờ đứng vì lý
> do đúng. Mục 2 cũng thêm hai điều bản cũ bỏ sót: bước 0 chặn khi hoá đơn cũ, và việc cấm là cấm
> **dịch vụ** chứ không cấm **image**.

Tách rõ phần **chứng minh được** khỏi phần **suy luận**, theo khuôn của
[`ep-429-va-mat-gateway-10-09.md`](ep-429-va-mat-gateway-10-09.md).

---

## 1. Kết quả một dòng

Lệnh triển khai tự động của dự án này chỉ được gồm `docker compose pull` và
`docker compose --profile refresh up -d`. Ba thứ bị cấm: profile `tools`, lệnh `down`, và cờ
`--remove-orphans` — mỗi thứ vì một lý do đã đo được, không phải vì cẩn thận chung chung.

---

## 2. Luật 1 — không bao giờ gọi profile `tools`

**Chứng minh được.** Chuỗi năm bước, mỗi bước đọc được trong repo:

| Bước | Vị trí | Nội dung |
|---|---|---|
| 1 | `docker/tools.Dockerfile:27` | `CMD ["python3", "scripts/update_dashboard.py"]` |
| 2 | `scripts/update_dashboard.py:160` | `[8/9] Dựng lại database → scripts/rebuild_db.py` |
| 3 | `scripts/rebuild_db.py:110` | `("Billing", "db/load_billing.py", ["--rebuild"])` |
| 4 | `scripts/rebuild_db.py:68` | `--rebuild` gọi `DROP SCHEMA public CASCADE`, xoá **mọi GRANT** |
| 5 | `db/connect.py:264` | `cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")` |

Không có bước hỏi xác nhận ở bất kỳ khâu nào — tìm `input()`, `confirm`, `--yes`, `--force` trong
`scripts/rebuild_db.py` đều không có, chỉ có `argparse`.

Dịch vụ `tools` được thiết kế để chạy bằng `docker compose run --rm tools <lệnh cụ thể>`, tức
**người gõ chọn lệnh**. `up -d` bỏ qua đúng phần đó và rơi thẳng vào `CMD` mặc định.

### Không phải lần nào cũng nổ — và chính điều đó mới nguy hiểm

Trước bước 8 còn **bước 0** (`scripts/update_dashboard.py:104-110`). Nếu ngày mới nhất trong
`data/billing/*GMSSub*.csv` cũ hơn hôm qua, pipeline dừng ngay và không xoá gì.

| Tình huống | Điều xảy ra |
|---|---|
| Ngày thường, hoá đơn chưa tải mới | Dừng ở bước 0 sau vài giây. Không hại gì |
| **Vừa bỏ hoá đơn mới vào** | Chạy đủ 9 bước: đăng nhập hai web app, hơn 100 lượt GET, kéo Monitoring 10–15 phút, gộp, rồi dựng lại database ở bước 8 (xoá dòng mọi bảng, nạp lại khoảng 78 giây) |

**Trước change `stop-a-later-pull-from-shrinking-an-earlier-one`, chuỗi dừng ở bước 7.** Đo ngày 14/09:
`scripts/update_dashboard.py:157-159` gọi `merge_latency_daily.py` mà không truyền `--in`. Script đó
dừng hẳn khi thư mục cha có khác đúng một lần kéo, và `data/raw_google_console/do_tre_phan_bo/` đang có
4 lần kéo. Chạy thật cho ra `ambiguous which folder to take ...` với mã thoát 1. Vậy từ khi có lần kéo độ
trễ thứ hai (29/08), đường này không thể tới bước 8.

**Change đó sửa bước 7**: chạy lại đúng cách bước 7 gọi cho mã thoát 0. **Cùng lúc**, nó bỏ `DROP SCHEMA`
khỏi bước 8. Đường tới bước 8 giờ đã mở, nhưng bước 8 không còn xoá quyền. Hai việc được làm cùng nhau
có chủ đích: sửa bước 7 trước mà còn giữ `DROP SCHEMA` thì sẽ mở lại đúng vụ 02/09.

`latency-daily.csv` được ghi lúc 12/09 13:53, trùng phút với lúc tạo thư mục `2026-09-12-196d-1m`.
Nhiều khả năng tệp này được sinh bằng tay với `--in` trỏ vào một lần kéo. Đây là **suy luận** từ giờ
sửa tệp.

Nên `tools` vẫn là **quả bom hẹn giờ**. Nó nổ vào ngày người vận hành vừa cập nhật hoá đơn, là ngày họ
ít đề phòng nhất. Thử một lần thấy "không sao" **không** chứng minh được là an toàn.

### Cấm dịch vụ, không cấm image

Chữ "tools" đang chỉ ba thứ khác nhau:

| Thứ | Có bị cấm không |
|---|---|
| Thư mục `tools/` (script chẩn đoán) | Không. Nó cũng không vào image nào, vì `.dockerignore:40` loại nó |
| Image `token-ledger-tools:local` | **Không**, và phải build. `ledger-refresh` dùng chung image này |
| Dịch vụ `tools` (`profile tools`, không khai `command:`) | **Cấm** gọi trong lệnh triển khai |

Build image thì an toàn: các dòng `RUN` chỉ cài gói, còn `CMD` không chạy lúc build.

### Hậu quả nặng hơn downtime: mất dữ liệu vĩnh viễn

`CMD` chạy ba bước liên quan tới Monitoring: kéo (bước 2), **gộp** các lần kéo (bước 3), rồi dựng lại
database từ bản gộp (bước 8). Riêng `rebuild_db.py` thì không kéo gì, nó chỉ đọc `data/`. Đã đo được
một lần mất thật, bằng cách so `token_ledger` (trước migrate) với `token_ledger_v2`:

```
fact_usage_daily, ngày 11/06/2026
    token_ledger      13.541.550 token
    token_ledger_v2   13.538.088 token
    chênh                  3.462 token   <- mất

fact_monitoring, ngày 11/06/2026
    chỉ số generate_content_paid_tier_3_input_token_count
    token_ledger           4.406
    token_ledger_v2          944
    hiệu     4.406 - 944 =  3.462        <- khớp tuyệt đối
```

Phạm vi đã soát: 129 ngày chung của `fact_monitoring`, băm md5 theo từng ngày. **126 ngày trùng
khít**, 3 ngày lệch (04/06, 11/06, 12/06), tổng cộng 5 dòng. Cả 5 dòng bản cũ đều cao hơn, hai
dòng bản mới về thẳng `0`.

**Nguyên nhân: chứng minh được, đo 14/09/2026.** Bản 13/09 đoán là cửa sổ trượt. Sai. Thật ra
là **luật gộp gặp một lần kéo bị cụt ở mép cửa sổ**:

```
tranquil-post-471401-c1 · paid_tier_3_input_token_count · 11/06 00:00 UTC

lần kéo           06/08  13/08  17/08  29/08  05/09  12/09
token              4406   4406   4406   4406   4406    944
lượt (PerDay)         2      2      2      2      2      1

bản gộp 2026-09-05-1m-gop: 4406      bản gộp 2026-09-12-1m-gop: 944
```

1. **Lần kéo 12/09 bị cụt ở đúng chỗ đó.** Nó không có dòng token nào trước 11/06 00:00 UTC. Ở phút
   23:59 ngay trước đó, nó không có dòng token hay quota nào, trong khi cả 5 lần kéo trước đều có
   (866 token). Phút 00:00 là phút đầu tiên còn sót lại của một mép bị cụt.
2. **Luật gộp chọn đúng số thiếu đó.** `scripts/merge_monitoring.py:83-95` cho *bản mới thắng* khi
   cùng khoá mà khác giá trị.

Ngày 11/06 **vẫn nằm trong** cửa sổ của lần kéo 12/09. Google không quên ngày đó, Google trả
**thiếu** ở phút mép. Chỉ có (1) thì không mất, vì bản cũ vẫn còn trên đĩa. Chỉ có (2) thì cũng không
mất, vì không có số nào bị trả thiếu. Phải có cả hai.

**Quy mô.** Đã quét cả 6 lần kéo 1 phút × 7 project, khoảng 2,95 triệu dòng, với khoá giống hệt
bước gộp. Có **14 điểm** bị đổi giá trị. **Cả 14 đều giảm**, không điểm nào tăng. Tổng token mà luật gộp
đã bỏ trên toàn lịch sử là **11.262** (3.462 ngày 11/06, cộng 7.800 ngày 12/08).

**Số cũ hay số mới đúng.** Kiểm bằng nhân chứng không đi qua bước gộp: `api_request_count` (họ
`serviceruntime`), và tổng số lượt trong histogram độ trễ (một lần kéo riêng):

| Nhóm | Điểm | Bằng chứng |
|---|---|---|
| Cộng nhiều phút liền nhau, so với nguồn khác | 5 | Số **cũ** khớp hoặc gần khớp nhân chứng, số mới hụt rõ. Ví dụ 12/08 07:04–07:07: api 9, histogram 9, PerDay 9, PerMinute bản cũ 9, bản mới 8. Còn 11/06 23:59–00:01: histogram 8, api bản cũ 7, bản mới 3 |
| Số mới bằng 0 giữa một chuỗi đều khoảng 4 lượt/phút | 4 | Số mới trái với các phút bên cạnh |
| Không có nhân chứng trực tiếp (4 phân vị độ trễ, 1 phút token) | 5 | Chỉ chứng minh được là lần kéo mới **thiếu dòng** ở sát đó |

Hoá đơn **không** phân xử được. Nếu tính 4406 thì ngày 10/06 (giờ Thái Bình Dương) là 100,69% hoá
đơn, còn tính 944 thì là 100,20%. Nhiễu giữa các ngày đã là 100,03–104,62%, lớn hơn 3.462 token.

Giả thuyết đối thủ "bản mới khử trùng lặp, bản cũ đếm đôi" bị loại theo hai hướng. Ở cả 5 điểm có
nhân chứng đếm lượt, nhân chứng nghiêng về số **cũ**. Và lần kéo mới thiếu cả những dòng lẽ ra không
liên quan tới khử trùng lặp, như phút 23:59.

**Khớp với 5 dòng lệch trong database.** Bản quét tìm ra đúng 5 điểm lệch trên ba ngày 04/06, 11/06,
12/06: `api_request_count` 04/06 00:00 về 0, ba dòng 11/06 00:00, và `api_request_count` 12/06 02:26
về 0. Chúng trùng với 5 dòng lệch đo ở trên về ngày, về số dòng, và về hai dòng về `0`. Tôi **chưa**
đối từng khoá với database.

**Còn chưa rõ:** vì sao Google trả thiếu ở mép. Và ở 5 điểm nhóm cuối, mới biết là thiếu dòng chứ
chưa biết giá trị đúng.

**Điều này nghĩa là:** mỗi lần `CMD` chạy với một lần kéo mới là một lần gộp lại theo luật "bản
mới thắng". Số liệu vì vậy **bào mòn đều đặn và im lặng**: số vẫn hiện bình thường, chỉ nhỏ dần.
Sửa luật gộp thì hết bào mòn.

Luật 1 **vẫn đứng** sau change `stop-a-later-pull-from-shrinking-an-earlier-one`, dù change đó đã sửa
luật gộp và bỏ `DROP SCHEMA`. `CMD` không còn xoá quyền, nhưng vẫn làm ba việc:
- xoá dòng mọi bảng rồi nạp lại, nên dashboard thấy bảng rỗng khoảng 78 giây;
- đăng nhập hai web app;
- kéo Monitoring 10–15 phút.

Không việc nào trong số đó thuộc về một lệnh triển khai.

---

## 3. Luật 2 — không bao giờ `docker compose down`

**Chứng minh được (xác minh 14/09/2026).** `docker-compose.yml` khai mạng với dải IP tĩnh, và chú
thích trong khối `networks:` cuối tệp nói rõ: tên mạng `token-ledger-dashboard_default` không được
đổi vì ràng buộc `external` bên DMS trỏ vào đó.

Đã mở tệp bên DMS ra đọc. Ràng buộc nằm ở
`D:\RangDonk\dms-feedback-classification\service\docker-compose.override.yml:36-41`:

```yaml
networks:
  gateway:
    external: true
    name: token-ledger-dashboard_default
```

Một chi tiết mà bản trước nói chưa đúng: khai báo này nằm trong **tệp override cục bộ** mà ta tự thêm
vào bản clone DMS ngày 31/08. `docker-compose.yml` gốc của nhóm DMS **không** có dòng `networks` nào.
Kết luận của luật thì không đổi.

`down` xoá mạng. DMS khai `external: true` nghĩa là nó **mượn** chứ không tạo, nên mạng mất là DMS
không lên lại được.

Cái giá của việc tuân theo luật này bằng không: `up -d` làm được mọi việc `down` rồi `up` làm, mà
không xoá mạng.

---

## 4. Luật 3 — không bao giờ `--remove-orphans`

**Chứng minh được.** Cờ này xoá container không thuộc tập dịch vụ đang gọi. Lệnh triển khai không
gọi profile `gateway`, nên với cờ này nó sẽ giết cả hai instance LiteLLM, ba sentinel, hai Redis và
nginx đang chạy.

---

## 5. Luật 4 — lệnh triển khai đầy đủ

```bash
docker compose pull
docker compose --profile refresh up -d
```

**Có `refresh`.** Chú thích trong `docker-compose.yml` nói rõ vì sao dịch vụ `ledger-refresh` tồn
tại — một khoảng trống đã đo được:

```
LiteLLM_SpendLogs                 444 dòng, mới nhất 08/09 23:55
fact_call WHERE source='gateway'   41 dòng, mới nhất 31/08 10:17
-> trễ 8 ngày 13 giờ 38 phút, và KHÔNG có dấu hiệu nào báo là đang trễ
```

Kết luận của chú thích đó: *"script đã có sẵn chế độ `--every`; cái thiếu là không ai chạy nó"*.
Một lệnh triển khai tự động chính là người chạy nó.

**Không có `gateway`, và đây là ràng buộc kỹ thuật chứ không phải lựa chọn.** Khối `x-litellm` khai
`build.context: ../litellm_tuan_test` — một thư mục **ngang hàng** repo. Máy nào không có thư mục
đó thì compose thoát ngay, kéo theo `postgres`, `api`, `web` đều không lên. Nút này chỉ gỡ được khi
image LiteLLM được đóng gói sẵn và `build:` đổi thành `image:` trỏ vào kho.

---

## 6. Một việc liên quan, chưa làm

**Chứng minh được.** Bản clone `../litellm_tuan_test` đang ở nhánh `litellm_internal_staging` tại
commit `e3490555c5` — có bản vá Sentinel. Nhưng trên kho từ xa:

| Nhánh | Commit | Bản vá `_SENTINEL_IGNORED_CONNECTION_ARGS` |
|---|---|---|
| `origin/Tuan-develop` | `e3490555c5` | **có** |
| `origin/litellm_internal_staging` | `f005afa146` | **không** |

Và `origin/HEAD` trỏ vào `litellm_internal_staging`. Nghĩa là **một bản clone mới rơi thẳng vào
nhánh không có bản vá**, và Gateway sẽ chết lúc khởi động với
`TypeError: Redis.__init__() got multiple values for argument 'host'`.

Máy hiện tại an toàn: local đi trước remote đúng 1 commit, nên `git pull` không kéo lùi được. Rủi
ro nằm ở **máy mới** — đúng kịch bản đưa Gateway sang server riêng.

Cách chặn rẻ nhất, để dành cho chặng 2: trước khi đóng gói image, `grep` tìm
`_SENTINEL_IGNORED_CONNECTION_ARGS` trong `litellm/_redis.py`; không thấy thì dừng.

---

## 7. Còn chưa chắc

| Điều | Mức |
|---|---|
| Nguyên nhân mất 3.462 token | **Chứng minh được** (14/09): lần kéo cụt ở mép, cộng luật gộp "bản mới thắng". Xem mục 2. Bản 13/09 ghi "cửa sổ trượt" là **sai** |
| Vì sao Google trả thiếu ở phút mép cửa sổ | **Chưa rõ.** Đã thấy nó xảy ra ở 14 điểm, chưa biết cơ chế bên Google |
| `docker compose pull` chạy êm khi `api`, `web`, `tools` mang tên `:local` không có trên kho nào | **Chưa kiểm.** Có thể cần cờ `--ignore-buildable`; kiểm bằng `docker compose pull --dry-run` |
| 3.462 ở `fact_monitoring` **gây ra** 3.462 ở `fact_usage_daily` | **Chưa lần theo** đường số liệu; mới thấy hai con số trùng khít |
| Compose của DMS thật sự khai `external` | **Đã xác minh** (14/09): `service/docker-compose.override.yml:36-41` trong bản clone DMS. Tệp gốc của nhóm DMS không khai |
| `token_ledger` còn giữ gì độc quyền ngoài 5 dòng đã tìm | **Chưa soát hết** — 3 bảng `fact_call`, `fact_latency_daily`, `fact_perf_daily` có cột khác nhau nên không so trực tiếp được |
