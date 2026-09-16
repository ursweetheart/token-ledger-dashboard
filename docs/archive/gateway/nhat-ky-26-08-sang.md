# Nhật ký sáng 26/08/2026

Tiếp theo `nhat-ky-22-08-sang.md`. Đọc nhanh: mục 1, mục 5, mục 11.

Buổi sáng có **hai mạch việc song song**: đo bản ghi Gateway, và kiểm lại schema migration
sau khi đồng nghiệp làm tiếp. Cả hai đều kết thúc bằng một kết luận khác với giả định ban đầu.

---

## 1. Tóm tắt

```
   MACH A -- DO BAN GHI GATEWAY
     ① Dung moi truong do tach biet, build fork LiteLLM 1.99.0
     ② A3 -> BAC BO      header tuy y bi vut sach, 0/10 cot
     ③ A5 -> SUA CACH GHI  khong co cot rieng, nhung DAN XUAT duoc
     ④ 3 request that, 0,0023 do

   MACH B -- SCHEMA MIGRATION
     ⑤ Tim ra nhanh dong nghiep: 11 commit, CHUA merge vao dau ca
     ⑥ Soi chat luong: ho sua mot loi PHA HUY that + viet 12 test
     ⑦ Xac minh 2 "lenh mien" ghi trong tasks.md -- 1 dung, 1 SAI
     ⑧ Merge + nghiem thu chang A          -> 8.1-8.5, 8.7 deu xanh
     ⑨ Dien tap doi schema tren du lieu that -> 002/003, 23/23 khop
     ⑩ Chup ban du phong + tu ra soat        -> 40/45, cong cutover 3/4
```

Điểm chung của cả hai mạch: **thứ hỏng im lặng chỉ bắt được bằng đo, không bắt được bằng
đọc.** Sáng nay tôi tự tạo ra **chín** cái hỏng im lặng của riêng mình — ba cái ở mục 13,
sáu cái ở mục 12c. Cái nguy hiểm nhất báo *"0 khác biệt, đạt"* cho một câu lệnh đã chết.

---

# MẠCH A — Đo bản ghi Gateway

## 2. Đo tài nguyên, và một thứ không đi tìm

Câu hỏi ban đầu chỉ là "máy có đủ chỗ để build không". Đủ, và dư nhiều:

```
   Docker 29.4.1 · WSL2 · docker_data.vhdx 62,7 GB tren C:
   C: con 247,1 GB   ·   trong may ao Docker con 893 GB
```

Bài học nhỏ: Docker chạy qua WSL2 nên **không** ăn vào `D:`. Đo `D:` là đo nhầm ổ.

Nhưng `docker ps -a` cho ra một thứ khác: **container postgres của dự án đã bị xoá hẳn**,
chỉ còn 10 container `openwebui-*` exited từ 2 tuần trước. Volume còn nguyên nên dữ liệu
an toàn. Điều này buộc tôi sửa một câu đã nói hôm 24/08 — *"cổng 5432 bị chiếm"* — không
còn đúng. Đến 01:57 UTC nó xuất hiện trở lại, không phải do tôi.

## 3. Bản fork: vỡ một lần

```
   stage builder, buoc 5/16, lenh apk add
   ERROR: keyutils-libs-1.6.3-r39: IO ERROR      <-- 1 goi tren 72
```

71 gói còn lại cài xong, gồm cả `rust-1.97` và `nodejs-26`. Không phải Dockerfile sai,
không thiếu đĩa. Lỗi I/O thoáng qua → chạy lại. **Lần 2 đạt.**

```
   litellm_rang_dong:probe   cc794ac6c222   1,65 GB
   ben trong: litellm 1.99.0 · enterprise 0.1.59 · proxy-extras 0.4.89
   fork commit f005afa146 (22/08), cay lam viec sach
```

## 4. Bố cục: hai file đặt sai chỗ

Câu hỏi *"có nên để fork bên trong thư mục dự án không"* lộ ra lỗi của tôi: tôi đã đặt
`config.probe.yaml` và `docker-compose.probe.yml` **trong thư mục fork**, trong khi chúng
là file của dự án ta.

Đã dời sang `tools/probe-gateway/`, build context trỏ ngược ra `../../../litellm_rang_dong`.
Kết quả: fork **sạch tuyệt đối** (`git status` rỗng hoàn toàn), phép đo tái lập được, và
quy ước ngang hàng trở thành mã.

Không lồng fork vào trong dự án, vì: repo lồng repo, `git clean -xfd` xoá sạch cả fork,
số file nhảy 469 → 10.241, và `enterprise/` mang giấy phép thương mại.

## 5. Hai phán quyết

### A3 — ~~BÁC BỎ~~ → **CHẠY ĐƯỢC** (sửa chiều 26/08, xem mục 16)

> ⚠️ **Phán quyết dưới đây SAI. Giữ nguyên văn để đối chiếu.** Lượt đo 4b chạy với
> `store_prompts_in_spend_logs` **tắt** (mặc định), nên cột `proxy_server_request` luôn
> trả chuỗi rỗng `"{}"` bất kể header gửi gì. Phép đo nhìn đúng chỗ, nhưng chỗ đó đang
> bị khoá. Đo lại lượt 5 với cấu hình đủ: **8/8 header ghi lại nguyên văn.**

```
   Gui:  X-User, X-OpenWebUI-User-Email
   Tim trong CA 10 cot co the chua  ->  0/10.  MAT SACH.
   proxy_server_request = {} rong
```

~~**Quy ước A3 sẽ mất danh tính, không một lỗi nào báo.**~~ Hai đường thay thế, cả hai đo được:

| Cách gửi | Cột nhận |
|---|---|
| Trường `"user"` trong **body** | `end_user` ✅ |
| Header **`x-litellm-tags`** | `request_tags` ✅ |
| Header tuỳ ý | ~~❌ mất~~ → ✅ **`proxy_server_request.metadata.headers`** (mục 16) |
| Header khai ở `user_header_name` | → ✅ **`end_user`** (mục 16) |
| `metadata` trong body | ❌ mất |

~~LiteLLM chỉ giữ **header nó biết tên**.~~ → LiteLLM giữ **mọi** header; cột chứa chúng
mặc định bị khoá.

### A5 — SỬA CÁCH GHI

Phép đo có đối chứng — cùng model, cùng câu hỏi, khác đúng một tham số:

```
   tag          reasoning_tokens   completion_tokens   spend
   a5-high                   432                 454   0,00172875
   a5-disable          VANG MAT                    3   0,0000375
```

Khoá **vắng mặt hoàn toàn** khi tắt, không phải bằng `0`.

`thinking_enabled` **dẫn xuất được**, không có sẵn. Sheet `Data Out` phải ghi
**"dẫn xuất từ Gateway"** kèm quy tắc tính. `output_modality` cũng vậy.

Một request đơn lẻ không chứng minh được điều này. Cặp bật/tắt mới chứng minh được.

## 6. Phát hiện nguy hiểm nhất của mạch A

```
   SpendLogs ghi:   model = "gemini/gemini-3.6-flash"
   guess_model()    ->   None
```

Không còn là giả thuyết — đó là chuỗi thật LiteLLM vừa ghi, đưa qua đúng hàm ánh xạ của
dự án. Mẫu `"3 flash"` không khớp `"3.6 flash"`.

Và Google **đã chặn `gemini-2.5-flash` với project mới**, chỉ thẳng sang `gemini-3.6-flash`.
Đó là con đường 8 agent sẽ bị đẩy vào.

### Một nhầm lẫn của tôi, đã sửa

Hôm 24/08 tôi ghi `gemini-3-flash` (32,5% lưu lượng) là *khoá không gọi được*. Sai.
`dim_model` giữ tên suy từ **hoá đơn** (`gemini-3-flash`), Google trả **mã API**
(`gemini-3-flash-preview`). Tôi so khớp chính xác hai chuỗi không cùng hệ quy chiếu.
Độ phủ danh mục: **53,2% → 85,7%**.

## 7. Ba phát hiện phụ

**① `completion_tokens` đã GỒM token suy luận** — `454 = 432 + 22`. Cộng thêm lần nữa khi
đối chiếu hoá đơn là nhân đôi, đúng loại lỗi từng dính với `cached_tokens`.

**② `spend` dựng lại được đến từng chữ số** —
`35×0,00000075 + 432×0,00000375 + 22×0,00000375 = 0,00172875`.

**③ LiteLLM ghi cả request THẤT BẠI** — `status='failure'` kèm token count.
`fact_request` bắt buộc phải có cột `status`.

## 8. Vertex hay AI Studio

Google **có** khác biệt thật: `candidatesTokenCount` **gồm** token suy nghĩ trên Gemini API,
**không gồm** trên Vertex. Nhưng LiteLLM chuẩn hoá bằng phép cộng
(`is_candidate_token_count_inclusive`), phát hiện bằng số học chứ không bằng tên nhà cung cấp
— nên khác biệt bị xoá **trước khi** ghi `SpendLogs`.

Cuối cùng chọn đường rẻ nhất: key AI Studio project mới **không gắn billing**. 0 cột lệch.

---

# MẠCH B — Schema migration

## 9. Nhánh của đồng nghiệp: có, nhưng chưa vào

Anh nói đã pull, nhưng `HEAD` không nhúc nhích. Việc của họ nằm ở một nhánh khác:

```
   ae8d9b3 ══════════════════  HEAD = Tuan-develop = origin/main
      ╲
       ╰─▶ 3fb4a0e … ef17a48   origin/codex/change-schema-without-drop
                                 11 commit · fast-forward sach · CHUA gop
```

`22/44 → 33/44`. Họ làm **toàn bộ phần code và tài liệu**; hai mảng còn lại đều là thao
tác trên database thật.

## 10. Soi chất lượng: cao

| | Bằng chứng |
|---|---|
| **Sửa một lỗi phá huỷ thật** | `rebuild()` từng `DROP SCHEMA` **rồi mới** kiểm thiếu `02_catalog.sql` — xoá sạch rồi mới báo lỗi. Đã đảo thứ tự |
| **Khoá lỗi đó bằng test** | `test_missing_catalog_fails_before_opening_or_wiping_database` |
| **Chống nhầm hỏng thành đạt** | 5/8 phép trong `test_acceptance_safety.py` khẳng định *phép đo hỏng ≠ chỉ-đọc đạt* |
| **Dọn tham chiếu tỉ mỉ** | Sửa cả số dòng: `001_baseline.sql:161`, `:525` |
| **Ghi sổ trung thực** | *"Do not claim a new deletion"* — không nhận công của commit khác |
| **Siết cổng thay vì nới** | Đổi *"chờ vài ngày"* thành *"phải xong 8.1–8.6 + backup + snapshot + preflight review"* |

## 11. Hai "lệnh miễn" — một đúng, một sai

`tasks.md` ghi hai chỗ *"người dùng đã miễn rõ ràng ngày 24/08/2026"*. Đã hỏi lại anh Tuấn
sáng nay:

**① Miễn khoảng chờ (task 6.3) — ĐÚNG.** Anh xác nhận có nói không cần chờ. Và bản viết
lại của đồng nghiệp thực ra **chặt hơn**: chờ 3 ngày mà không kiểm gì thì vẫn mù như chờ
0 ngày; đổi sang bằng chứng là đúng hướng.

**② Miễn sao lưu `data/` (task 1.1) — SAI.** Task ghi *"không có bản sao lưu nào được tuyên
bố đã thực hiện"*, suy từ việc checkout không chứa `data/`. Đúng với một bản clone sạch —
`data/*` nằm trong `.gitignore` — nhưng **sai với máy đang vận hành**.

**Nói cho rõ, vì câu trên dễ đọc nhầm:** anh Tuấn **có** nếp sao lưu, và có từ trước —
tại `D:\RangDonk\token-ledger-backup\`, mỗi lần một thư mục theo ngày. Vấn đề **không phải
là không có bản nào**, mà là **bản gần nhất đã cũ 18 ngày**. Hai câu đó rất khác nhau và
task 1.1 gộp chúng làm một.

Đo thật: `data/` có **2,3 GB / 192 file**. Bản sao lưu `2026-08-08` chỉ phủ **443 MB /
73 file**; 120 file kéo về ngày 13/08 và 17/08 nằm ngoài nó. Kiểm mtime: không file nào
sinh sau ngày bàn giao — **tất cả là của anh Tuấn**, không phải của đồng nghiệp.

Trong 120 file thiếu:

| Nhóm | File | Dung lượng | Lấy lại được |
|---|---:|---:|---|
| `da_xu_ly/` | 16 | **728 MB** | ✅ dựng lại từ `raw_*` |
| `raw_web/` | 66 | 439 MB | 🟡 ra ảnh chụp khác |
| `raw_google_console/` | 37 | 688 MB | 🔴 **không** — cửa sổ Cloud Monitoring trượt nhanh |

Nhóm nặng nhất lại ít quan trọng nhất.

Anh Tuấn đã chép bổ sung. Kiểm chứng:

```
   D:\RangDonk\token-ledger-backup\2026-26-08\data
     192/192 file · 0 thieu · 0 thua · 0 file lech byte
     raw_google_console (688 MB, phan KHONG lay lai duoc):
       data/  sha256 857550e577817423
       backup sha256 857550e577817423    KHOP TUNG BYTE
```

Task 1.1 đã viết lại theo bằng chứng thật. Điều kiện *backup* của cổng 6.3 nay **đã thoả**.

⚠️ Tên thư mục `2026-26-08` theo `YYYY-DD-MM`, lệch với `2026-08-08` theo `YYYY-MM-DD`.
Lần sau sao lưu ngày 01/09 sẽ ra `2026-01-09` và nhảy lên đầu danh sách, trông như bản cũ
nhất. Nên đổi thành `2026-08-26`.

## 12. Merge và nghiệm thu chặng A

Merge fast-forward, 0 va chạm, **không tạo commit mới**.

```
   8.1  database TRANG -> alembic upgrade head -> rebuild_db.py (43s)
          baseline_db.py --compare : 23 khoa · 23 KHOP · 0 lech
          1.189 dong · 867.657.110 token · $291,985601
   8.2  audit_db.py     36 phep · 31 dat · 5 luu y · 0 HONG
   8.3  check_api.py    19 phep · 19 dat · 0 HONG
   8.4  node --test     18/18   +   unittest 11/11
   8.5  chay_dashboard  exit 0, "DASHBOARD NAP DUOC"
   8.7  bit khe ho nghiem thu (xem duoi)
```

Và chặng B — diễn tập trên **dữ liệu thật**, task 8.6:

```
   truoc 002    23/23 khop    fact_usage_daily  11 cot
   sau  002     23/23 khop    11 -> 12 cot,  3 view nguyen ven
   sau  003     23/23 khop    12 -> 11 cot,  cot dien tap: 0

   chuoi: 001_baseline -> 002_rehearsal_add -> 003_rehearsal_drop
```

Hai lần đổi schema **tại chỗ trên 867 triệu token**, không suy suyển một đơn vị. Gỡ bằng
bước **TIẾN**, không dùng `downgrade` — đúng luật forward-only của task 3.4. Chuỗi ba
migration cũng chạy sạch từ một database trắng và dừng đúng ở 11 cột.

Đây là năng lực mà trước migration dự án **không có**: đổi schema nghĩa là sửa
`01_schema.sql` rồi dựng lại từ đầu. Giá phải trả là hai bản ghi không mang giá trị nghiệp
vụ nằm vĩnh viễn trong lịch sử — giá đúng, vì chúng là bằng chứng ngày năng lực này được
chứng minh.

**8.1 là con số đáng nhớ nhất của cả change**: toàn bộ database dựng lại được từ số không,
chỉ bằng chuỗi migration và `data/`, ra đúng từng chữ số, trong 43 giây. Đó là năng lực mà
trước migration dự án không có.

### Khe hở nghiệm thu đã bịt (task 8.7 mới thêm)

11 phép kiểm Python mới (`test_acceptance_safety.py` 8 phép, `test_connect_migrations.py`
3 phép) **không nằm trong bất kỳ task nghiệm thu nào** — 8.4 chỉ gọi `node --test`. Nay
8.4 gọi cả hai lệnh. Repo vẫn **không có CI**, nên hai bộ test chỉ chạy khi có người nhớ gõ.

## 12b. Bản chụp trước cutover

Sau diễn tập, dựng nốt điều kiện thứ ba của cổng 6.3.

```
   D:\RangDonk\token-ledger-backup\2026-08-26-truoc-cutover\
     token_ledger_v2-2026-08-26.dump   4.544.548 byte   (pg_dump -Fc)
     sha256.txt                        be9488260c4ff36d...
```

Kiểm ba lớp, vì `pg_dump` là loại lệnh **trả mã 0 rồi để lại file rỗng** nếu chuyển hướng
nhị phân sai — tôi đã dính đúng bẫy đó ở lần thử đầu:

```
   sha256 trong container == sha256 tren dia   -> chep ra khong hong mot byte
   pg_restore --list doc duoc: 97 muc, du TABLE DATA
   ma bam ghi canh file de doi chieu ve sau
```

### Nó chứa gì, và vì sao điều đó quyết định chỗ lưu

```
   19 bang + alembic_version · 3 view · 18 PK · 29 FK · 21 chi muc
   fact_monitoring  583.917 dong (180 MB truoc khi nen)

   946 ho ten day du
   927 dia chi email
   937 tai khoan la NGUOI THAT
   130 don vi / phong ban
```

Nén xuống còn **4,3 MB** — nhỏ đến mức gửi qua chat cũng lọt. Rủi ro của file này **không
phải dung lượng, mà là ai chạm được vào nó**. Chính `backend/main.py` đã cảnh báo:
*"database này chứa danh sách nhân viên kèm phòng ban... đừng làm nếu chưa bàn với ai."*
Bản dump là cùng nội dung đó, dạng một file mang đi được.

Để ngoài repo (`git clean -xfd` sẽ xoá, và 927 email không nên nằm cạnh mã nguồn), không
đẩy lên dịch vụ đám mây nào chưa cân nhắc.

### Đã có `data/` rồi, vì sao vẫn cần dump

Ba lý do, lý do thứ ba là của chính dự án:

1. **Tốc độ đúng lúc cần tốc độ** — cutover hỏng lúc 5 giờ chiều thì `pg_restore` mất vài
   giây; chạy lại đường ống từ `data/` mất 43 giây cộng thời gian nhớ ra phải gõ lệnh nào
2. **Chụp đúng khoảnh khắc** — dựng từ `data/` cho ra database *như hôm nay dựng được*;
   dump giữ đúng trạng thái ngay trước khi xoá
3. **Đường lui bằng `data/` sắp hết hạn.** `001_baseline_baseline.py` ghi rõ: *"từ ngày
   Gateway ghi dòng đầu tiên, dòng gateway KHÔNG có bản sao ở `data/`"*. Từ đó trở đi
   `pg_dump` là đường lui **duy nhất** — tập thói quen bây giờ là đúng lúc

## 12c. Tự rà soát trước cutover — và vì sao nó không đủ

Anh Tuấn yêu cầu tôi tự rà bằng kỹ năng *vòng lặp review + sửa*, thay cho điều kiện
"independent preflight review" của cổng 6.3. Đã làm. Kết quả: **thêm bằng chứng, không
thoả điều kiện.**

### Sáu lỗi script tôi tự tạo ra trong chính lượt rà soát

| | Lỗi | Nó che giấu điều gì |
|---|---|---|
| 1 | `\|\| echo` sau `head` không bao giờ chạy | Không phân biệt được *"không có match"* với *"grep hỏng"* |
| 2 | Nháy lồng làm vỡ `awk` trong `docker exec` | Lệnh chết ngay dòng đầu |
| 3 | Dùng `"x"` trong SQL — đó là **tên cột**, không phải chuỗi | Ba query trả lỗi thay vì số |
| 4 | `$?` đo `head` chứ không đo `pg_restore` | Báo "mã thoát 0" cho một lệnh chưa được đo |
| 5 | `tail -2` cắt mất danh sách database | Nhìn thấy 2/4 — **suýt tưởng `token_ledger` đã biến mất** |
| 6 | Regex đẩy task **8.6 xuống sau 8.7** | Tài liệu sai thứ tự |

Cái số 5 đáng sợ nhất: đầu ra trông hoàn toàn bình thường, chỉ thiếu hai dòng. Tôi bắt được
vì con số vô lý, **không vì cẩn thận**. Cộng ba lỗi ở mục 13 thì đây là lần thứ tư, thứ năm,
thứ sáu... trong một buổi sáng một phép đo hỏng đội lốt một phép đo đạt.

### Năm bằng chứng mới thu được

**① Bản dự phòng khôi phục được thật.** Trước đó chỉ mới chứng minh nó *đọc được*:

```
   pg_restore -> database moi -> 20 bang · 3 view · alembic 003 · 11 cot
   23/23 con so KHOP
```

**② Hai lệnh không quay lại được đã diễn tập** trên database nháp. `DROP DATABASE` và
`ALTER DATABASE ... RENAME TO` đều chạy trơn; bản đổi tên vẫn đủ 23/23 con số.

**③ `token_ledger_v2` không có kết nối nào đang giữ** → lệnh `RENAME` ở 6.5 sẽ không treo.
Chính task 6.5 cảnh báo *"còn kết nối thì lệnh treo chứ không báo lỗi rõ"*.

**④ `downgrade()` của cả ba revision đều ném `NotImplementedError`** — kiểm bằng cách **gọi
thật**, không phải bằng cách đọc.

**⑤ Diễn tập 8.6 an toàn về cấu trúc, không nhờ may.** `insert_many()` nhận danh sách cột
do **người gọi truyền vào**, không nội suy từ bảng. Đối chứng dương: 16 dòng `INSERT INTO`
tồn tại, **0 dòng** thiếu danh sách cột, **0 dòng** `SELECT *` lấy theo vị trí.

Kèm theo: danh sách **9 chỗ còn chữ `_v2`** phải sửa ở bước 6.6 — chỉ `db/connect.py:75` có
hiệu lực chạy, 8 chỗ còn lại là ví dụ trong tài liệu (để lại thì lần sau có người chép
nguyên câu lệnh và trỏ vào một database không tồn tại).

### Chứng minh được, và suy luận — không trộn

**Chứng minh được:** bản dự phòng ra 23/23; `DROP` và `RENAME` chạy được; `downgrade()`
chặn thật; thêm cột nullable không vỡ loader nào; `token_ledger` bản cũ vẫn nguyên 22 bảng
· 867.657.110 token.

**Suy luận, chưa chứng minh:** *"cutover thật sẽ trơn như diễn tập"* — nháp có kích thước
bằng thật, nhưng thật thì không có lần hai. *"9 chỗ `_v2` là đủ"* — dựa trên `grep` những
đuôi file đã liệt kê; file không có đuôi đó thì lọt.

### Vì sao ô đó vẫn để trống

**Tôi vừa rà soát chính công việc của mình — hai vai không thể do một người giữ.**

Bằng chứng nằm ngay trong báo cáo: **6 lỗi script, tất cả đều của tôi**, trong một lượt rà
soát mà mục đích là tìm lỗi. Nếu tôi tự chứng nhận được cho mình thì cái ô đó đã không cần
tồn tại.

```
   [ ] independent preflight   VAN CHUA co
       Tu ra soat 26/08 -- THEM bang chung, KHONG thoa dieu kien
```

Cổng vẫn **3/4**. Tôi không tự mở nó.

Nếu công ty thật sự không có ai khác đủ ngữ cảnh, có đường thay thế trung thực — anh Tuấn
tự đọc `tasks.md` rồi chạy lại ba lệnh nghiệm thu, hoặc nhờ chính đồng nghiệp làm nhánh
`codex/` đọc chéo. **Nhưng phải ghi rõ đã chọn cách nào**, chứ không lặng lẽ đánh dấu xong.

## 13. Ba lỗi im lặng đầu tiên

Đáng ghi vì cả buổi tôi đi tìm loại lỗi này ở chỗ khác. Sáu cái nữa ở mục 12c —
**tổng chín cái trong một buổi sáng.**

**① `exit code 0` cho một lần build thất bại.** Tôi nối lệnh nền qua `| tail -60`, nên mã
thoát ghi nhận là của `tail`. Tin con số đó là báo "build xong" cho một thứ đang hỏng.
→ Không nối ống dẫn cho lệnh chạy nền.

**② Nuốt `stderr` trong phép so ràng buộc.** Query báo
`ERROR: operator is not unique: text || "char"`, nhưng script chỉ đọc `stdout` và không
kiểm mã thoát → ra *"0 ràng buộc ở cả hai bên, lệch 0"*, **trông y hệt một kết quả đạt**.
Chỉ bắt được vì con số 0 vô lý: 19 bảng mà không có khoá chính nào là điều không thể.
→ Thêm `ON_ERROR_STOP=1` và kiểm `returncode`. Số thật là **51 = 51**.

**③ `LIMIT 1` đặt sai chỗ** khiến `jsonb_object_keys(metadata)` trả **một khoá** thay vì
một dòng — suýt báo `metadata` chỉ có 1 trường trong khi nó có **32**.

Cả ba đều cùng một họ với thứ mạch A đi tìm: **một phép đo hỏng trông giống một phép đo đạt.**

## 14. Vết nứt giữa hai luồng việc

Không thuộc nhánh migration, nhưng phát hiện trong lúc kiểm:

```
   docs/superpowers/plans/2026-08-18-docker-packaging.md   899 dong
     dong 236  COPY scripts/copy_to_postgres.py       <-- DA XOA (commit aa5f7d0)
     dong 506  command: copy_to_postgres.py --nguon /import/token_ledger.sqlite
     dong 509  source: ./var/token_ledger.sqlite      <-- DA XOA 17/08
```

Kế hoạch viết 18/08, thứ nó dựa vào bị xoá 24/08, không ai quay lại sửa. Ai làm theo sẽ
dựng lên một PostgreSQL **rỗng** — dashboard chạy nhưng không có số. Cần quyết: kế hoạch
đó còn sống hay đã lỗi thời.

## 15. Đang ở đâu

```
   change measure-what-the-gateway-records    42/42   XONG
     25/42 sang 26/08 · +7 chieu 26/08 · +10 ngay 27/08
     27/08 dong not: nhom 5 (doi chieu 26 truong Data Out) · 6.2 sheet
                     6.3 §A5 · 6.5 he qua GD7 · 6.7+7.6 quet bi mat · 7.3

   change change-the-schema-without-dropping-it   40/45
     con 5 task:  6.3 cong · 6.4-6.7 cutover
```

Cổng 6.3 nay **3/4 điều kiện đã thoả**:

```
   [x] 8.1-8.6 hoan tat
   [x] backup data/          192/192 file, 0 lech byte, sha256 khop
   [x] live snapshot         4.544.548 byte, sha256 khop, pg_restore doc duoc
   [ ] independent preflight -- can MOT NGUOI KHAC
```

Thứ còn thiếu không phải việc gõ phím.

Ba database hiện giống hệt nhau về số:

```
   token_ledger        193 MB   ban cu, cho xoa
   token_ledger_v2     192 MB   DANG CHAY (connect.PG_DATABASE tro vao day)
   token_ledger_acc81  192 MB   ban nghiem thu 8.1
```

### Còn treo

| | Việc |
|---|---|
| ~~🔴~~ 🟡 | `guess_model()` trả `None` cho `gemini-3.6-flash` / `3.7-flash` — Google đang ép chuyển sang chính model này. **Xác nhận sống chiều 26/08**: Google trả `404` cho `gemini-2.5-flash` kèm câu *"no longer available to new users… use gemini-3.6-flash"*.<br>**Hạ mức 27/08:** LiteLLM **có** đủ đơn giá cho `gemini/gemini-3.6-flash` (`model_map_information`), `spend` dựng lại được đến từng chữ số. Thiếu sót nằm ở `db/rules.py` của **ta**, không phải ở LiteLLM — hai dòng, không phải một việc nghiên cứu |
| 🔴 | `forward_client_headers_to_llm_api` **phải TẮT** ở bản thật — đo được chiều 26/08: nó gửi email nhân viên và JWT sang Google (mục 16) |
| 🔴 | Kế hoạch `docker-packaging` dựa trên hai thứ đã xoá |
| 🟡 | Quy ước A3 viết lại theo mục 16: header **dùng được**, cần 3 khoá config. Bản cũ ở mục 5 đã gạch |
| ~~🟡~~ ✅ | ~~Sửa A5 trong sheet `Data Out`~~ — xong 27/08: dòng 16 và 17 nay ghi "Dẫn xuất từ Gateway" kèm quy tắc tính |
| 🟡 | Đổi tên `2026-26-08` → `2026-08-26` |
| 🟡 | Repo không có CI — hai bộ test chỉ chạy khi có người nhớ |
| ⚪ | `gemini-2.5-flash-image` gộp mất nhánh ảnh; `gemini-2.0-flash` đã rút khỏi API |
| ~~⚪~~ ✅ | ~~Ralli không có dòng monitoring AI nào~~ — đo lại 27/08: **0 dòng monitoring, 47.933.778 token nguồn `app`**. Hệ quả cho GĐ7 viết ở `do-ban-ghi-litellm-24-08.md` §10: "đối chiếu bốn nguồn" chỉ đúng với **1 trên 8 agent** |

### Cần anh Tuấn quyết

1. Independent preflight review — **ai làm**. Đây là điều kiện cuối cùng.
   Tự rà soát ngày 26/08 (mục 12c) thêm được 5 bằng chứng nhưng **không thay thế** được nó
2. Kế hoạch `docker-packaging` (mục 14) — **còn sống hay đã lỗi thời**. Nó dựa vào hai thứ
   đã bị xoá; ai làm theo sẽ dựng lên một PostgreSQL rỗng

Sau hai câu đó là cutover: `DROP` bản cũ, đổi tên `_v2`, sửa cấu hình. Khoảng 15 phút,
không quay lại được.

### Chưa commit

```
   M  openspec/changes/change-the-schema-without-dropping-it/tasks.md
   ?? db/migrations/sql/002_rehearsal_add_column.sql
   ?? db/migrations/sql/003_rehearsal_drop_column.sql
   ?? db/migrations/versions/002_rehearsal_add_column.py
   ?? db/migrations/versions/003_rehearsal_drop_column.py
   ?? docs/reference/do-ban-ghi-litellm-24-08.md
   ?? docs/reference/nhat-ky-26-08-sang.md
   ?? openspec/changes/measure-what-the-gateway-records/
   ?? tools/probe-gateway/
```

~~🔴 `JWT_test_for_header` là một Bearer token THẬT, còn sống.~~ **Xử lý xong 27/08.**
Token đã hết hạn `26/08 17:49`; file đưa ra ngoài repo (`D:\RangDonk\`).

Đáng ghi vì cách nó bị bỏ lọt: phép kiểm 6.7 quét **hai chuỗi khoá đã biết trước** và trả
"0 file" — trông y hệt một kết quả đạt. Câu hỏi sai, không phải phép đo sai.

Phép quét mới `tools/scan_secrets.py` tìm theo **hình dạng** (6 loại), và ngay lần chạy đầu
nó bắt được thứ mà cả hai phép kiểm trước không thấy:

```
   ket-qua/spendlogs-mot-dong-luot5.json    7 x JWT 260 ky tu
   ket-qua/spendlogs-mot-dong-5b.json       7 x JWT 260 ky tu
```

**Chính hai file bằng chứng của phép đo mang nguyên chuỗi JWT** — chưa theo dõi, ngoài
`.gitignore`. Đã che bằng dấu `<JWT-DA-CHE len=260 sha256=da5ec4c0>`: cùng một dấu ở cả 7
chỗ nên vẫn chứng minh được "ghi nguyên văn, giống hệt nhau", JSON vẫn đọc được, bản gốc
giữ ngoài repo. Chạy lại: **0 phát hiện, `rc=0`**.

Môi trường đo `litellm-probe` **đã `down`** chiều 26/08 — 2 container + 1 network gỡ sạch,
volume `litellm-probe_litellm_probe_pg` giữ lại để đọc lại được.

---

# 16. Phụ lục chiều 26/08 — đo lại A3, và một kết luận sáng nay bị lật

Anh Tuấn đề xuất gửi JWT nguyên vẹn trong header, "bê nguyên" như cách Ralli CTDA gửi.
Để kiểm, phải bật những khoá mà lượt 4b **không** bật. Kết quả lật mục 5.

## 16.1 Vì sao lượt sáng ra kết luận sai

Không phải LiteLLM vứt header. Cột chứa header **mặc định bị khoá**:

```python
# spend_tracking_utils.py:1097
if _should_store_prompts_and_responses_in_spend_logs():   # mac dinh FALSE
    ...                                                    # dung noi dung
return "{}"                                                # <-- di thang xuong day
```

Lượt 4b đọc `proxy_server_request` thấy `{}` và kết luận *"header mất sạch"*. Phép đo
**nhìn đúng chỗ, nhưng chỗ đó đang tắt**. Cùng họ với chín lỗi ở mục 12c và 13: một phép
đo hỏng trông y hệt một phép đo đạt — đây là cái **thứ mười**, và tốn nhất, vì nó làm bác
bỏ một quy ước vốn chạy được.

## 16.2 Đối chứng hai lượt

Cùng gateway, cùng hai header, khác đúng một khoá config:

```
                          luot 4b (sang)      luot 5 (chieu)
   proxy_server_request   {} -- 0 khoa        5 khoa
   so header ghi lai      0                   8
   x-openwebui-user-email khong thay          co, nguyen van
```

8/8 header vào được sổ, nguyên văn:

```
   host  accept  user-agent  content-type  content-length
   x-user                   eyJhbGciOiJIUzI1NiIs...  (JWT 260 ky tu, day du)
   x-ralli-trace            probe-jwt-01              <-- header TU DAT
   x-openwebui-user-email   tuan.tran@example.invalid <-- cai sang bao "MAT"
```

Và `user_header_name` đẩy header thẳng vào cột `end_user` — kể cả với request **thất bại**
(lượt 404 vẫn ghi `status=failure` kèm `end_user` đầy đủ).

## 16.3 Cấu hình chốt — bốn khoá, khoá thứ tư phải TẮT

| Khoá | Tầng | Bản thật | Lý do |
|---|---|---|---|
| `user_header_name: "X-User"` | `general_settings` | ✅ bật | header → cột `end_user` |
| `store_prompts_in_spend_logs: true` | `general_settings` | ✅ bật | mở cột `proxy_server_request` |
| `turn_off_message_logging: true` | `litellm_settings` | ✅ bật | bỏ nội dung prompt, **giữ** header |
| `forward_client_headers_to_llm_api` | `general_settings` | 🔴 **TẮT** | xem 16.5 |

## 16.4 Giữ header mà bỏ nội dung câu hỏi — đo được (lượt 5b)

Gửi prompt là chuỗi mồi `BI-MAT-KHONG-DUOC-LUU-VAO-DB`, rồi tìm nó trong cả dòng SpendLogs
19.031 byte:

```
   chuoi moi xuat hien:  0 lan
   messages           :  [{'role':'user','content':'redacted-by-litellm'}]
   headers            :  8/8 CON NGUYEN
   end_user           :  JWT day du
```

`perform_redaction()` chỉ chạm `messages`/`input`/`prompt`; `metadata.headers` nằm ngoài
tầm nên còn lại. Đây là cấu hình **dùng được ở bản thật** — ghi được danh tính mà không
nuốt nội dung hội thoại vào database vốn đã có 927 email nhân viên.

## 16.5 Khoá thứ tư: nó chạy, và chính vì chạy nên không được dùng (lượt 5c)

Lượt gọi **thật** ra Google, đọc từ log `DEBUG`:

```
   curl -X POST https://generativelanguage.googleapis.com/v1beta/models/
                gemini-2.5-flash:generateContent
     -H 'x-user: REDACTED'                                     <-- Google nhan duoc
     -H 'x-ralli-trace: probe-5c-that'                         <-- Google nhan duoc
     -H 'x-openwebui-user-email: tuan.tran@example.invalid'    <-- Google nhan duoc
```

`forward_client_headers_to_llm_api: true` chuyển **mọi** header `x-*` (trừ `x-stainless`)
sang nhà cung cấp. Bật ở bản thật nghĩa là mỗi request gửi **email nhân viên và token đăng
nhập** sang Google. Ba khoá ở 16.3 đã đủ để ghi sổ; khoá này không mua thêm gì.

⚠️ **Suýt báo nhầm.** `grep -c "POST Request Sent from LiteLLM"` ở lượt 5 (mock) trả `1` —
trông y hệt *"đã gửi đi"*. Mở ra đọc thì thân rỗng (`-d '{}'`) và `RAW RESPONSE:
my-original-response` là chuỗi giữ chỗ của mock: **không có lượt HTTP nào**. Chỉ lượt 5c
bỏ mock mới thật sự trả lời được.

## 16.6 JWT không phải danh tính ổn định

Phép đo không đổi được điều này. `end_user` giờ chứa cả token; token thật của Ralli còn dài
hơn và **đổi mỗi lần đăng nhập**:

```
   09:00 dang nhap -> end_user = eyJ...aaa  ┐
   14:00 dang nhap -> end_user = eyJ...bbb  ├─ CUNG MOT NGUOI, 3 danh tinh
   hom sau         -> end_user = eyJ...ccc  ┘
```

Đếm người dùng theo cột này sẽ lạm phát. Nhưng không phải chọn một trong hai — có cả hai:

| Chỗ | Đựng gì | Dùng để |
|---|---|---|
| `end_user` | claim **`sub`** (`tuan.tran`) | đếm, gộp, truy vấn — ổn định |
| `proxy_server_request.metadata.headers` | **JWT + mọi header**, nguyên văn | đối chiếu, truy vết |

## 16.7 Xác nhận sống: Google đã chặn `gemini-2.5-flash`

Lượt 5c bắn vào `probe-flash`, Google trả thẳng:

```
   404  "This model models/gemini-2.5-flash is no longer available to new users.
         Please update your code to use models/gemini-3.6-flash"
```

Đúng model mà `guess_model()` trả `None`. Việc 🔴 đó nay có bằng chứng đóng dấu thời gian,
không còn là suy đoán từ tài liệu.

## 16.8 Câu Ralli tiền xử lý — **chưa** trả lời được

Lượt 5 dùng `curl` **giả lập** Ralli theo hiểu biết hiện tại. Nó không chứng minh Ralli gửi
đúng như vậy. Cách trả lời dứt điểm: trỏ `base_url` của Ralli vào `http://127.0.0.1:4000`
— cái gì đáp xuống gateway thì **chính là** cái Ralli thật sự gửi, sau mọi tiền xử lý.
Không cần đọc mã Ralli, không cần hỏi ai.

## 16.9 Chứng minh được, và chưa — không trộn

**Chứng minh được:** header tuỳ ý vào được `proxy_server_request` (8/8); `user_header_name`
đẩy header vào `end_user`, kể cả khi request thất bại; `turn_off_message_logging` giữ header
mà xoá prompt (chuỗi mồi 0 lần); `forward_client_headers_to_llm_api` gửi header sang Google;
Google chặn `gemini-2.5-flash` với project mới.

**Chưa chứng minh:** Ralli gửi đúng hình dạng ta giả lập (16.8); cột `end_user` chịu được
JWT dài bao nhiêu — bản đo dùng token 260 ký tự, chưa thử token thật.

**File bằng chứng** trong `tools/probe-gateway/ket-qua/`:
`spendlogs-mot-dong-luot5.json` · `spendlogs-mot-dong-5b.json` · `raw-luot5.log` ·
`raw-5c.log` · `phan-hoi-5c.json`
