# Thiết kế — mở rộng bộ kiểm tra tự động sang dữ liệu Gateway

Mọi con số đo trên database thật `token_ledger_v2` ngày **03/09/2026**.

## Context

Hai bộ kiểm hiện có, chạy bằng hai vai khác nhau, và đó là điểm mạnh **lẫn** điểm mù:

```
   scripts/audit_db.py    vai `token` (chu schema)   68 phep · 64 dat · 4 luu y · 0 hong
                          soi CAU TRUC va SO KHOP giua cac bang

   backend/check_api.py   vai `api_readonly` (qua HTTP)  27 phep · 27 dat
                          soi API tra dung so ma database co
```

Ngày 02/09 cả hai cùng báo lành trong khi container `api` chạy 38 phút trên một
database nó không đọc nổi. Nguyên nhân đã bịt ở change trước, nhưng **hình dạng lỗi
thì chưa**: một phép kiểm khẳng định tính chất mà nó chưa thực sự quan sát.

Change này mở rộng cả hai bộ sang nguồn `gateway` — và đồng thời sửa chính hình dạng
lỗi đó, vì mở rộng mà giữ nguyên hình dạng là nhân nó lên.

## Goals / Non-Goals

**Goals:**

- Bộ kiểm phủ **đúng cấu trúc thật** của database, không phủ một bản chép tay đã trôi.
- Phân biệt được **"đã kiểm và đạt"** với **"không có gì để kiểm"** — hai kết quả khác
  nhau, hôm nay in ra cùng một chữ.
- Có phép kiểm đối chiếu token cache Gateway ↔ SKU cache hoá đơn, **và nó nói thẳng khi
  chưa chạy được** thay vì báo đạt trên tập rỗng.
- Ngưỡng chấp nhận sai lệch **ban hành trước** khi có số đầu tiên.

**Non-Goals:**

- **Không** làm cho phép đối chiếu cache *chạy được*. Nó bị chặn bởi dữ liệu (0 ngày
  giao nhau), không bởi mã. Change này viết phép kiểm và làm nó **trung thực**, không
  tạo ra dữ liệu để nó có việc làm.
- **Không** đổi ngưỡng `MIN_SAMPLES`, không đụng `usage_resolved`, không đụng frontend.
- **Không** viết migration nào. Đây là change về **bộ kiểm**, không về schema.
- **Không** sửa nội dung các phép kiểm đang đạt vì lý do thẩm mỹ.

## Decisions

### ① Khoá ngoại: HỎI DATABASE, không giữ bản chép tay

Đo được, và con số tự nói:

```
   khoa ngoai THAT trong database   36
   FOREIGN_KEYS khai trong audit    23
   KHONG DUOC KIEM                  13     (6 trong so do sinh sang nay)
```

Bản chép tay không sai vì ai đó cẩu thả — nó sai vì **cấu trúc đi tiếp còn bản chép thì
đứng lại**. Sáng nay migration 008 thêm 6 khoá, và không có gì nhắc phải sửa danh sách.
Lần sau sẽ y hệt.

**Quyết định: dựng danh sách từ `pg_constraint` lúc chạy.**

```sql
   SELECT conrelid::regclass, a.attname, confrelid::regclass
   FROM pg_constraint c
   JOIN unnest(c.conkey) WITH ORDINALITY k(attnum, ord) ON TRUE
   JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
   WHERE c.contype = 'f' AND c.connamespace = 'public'::regnamespace
```

**Nhưng KHÔNG bỏ hẳn con số mốc.** Một danh sách tự sinh có điểm mù ngược lại: khoá
ngoại **bị xoá** thì danh sách ngắn đi và phép kiểm vẫn xanh — nó chỉ kiểm những gì còn
lại. Nên giữ thêm một khẳng định về **số lượng**:

```
   so quan he doc duoc  >=  MOC (36, do 03/09/2026)
   tut xuong duoi moc  ->  HONG, keu ten quan he da bien mat
```

Hai phép này bắt hai chuyện ngược nhau: bản chép tay hụt so với database, và database
hụt so với hôm qua.

### ② Ngày tương lai: mốc là NGÀY CHẠY, và soi mọi bảng có cột ngày

Phép kiểm hiện tại ghim `'2026-12-31'` và chỉ soi `usage_resolved`. Hai khuyết tật, cả
hai nổ muộn:

```
   ghim 2026     sang 2027 moi dong THAT deu bi coi la tuong lai
                 -> phep kiem chuyen tu im lang sang keu am, khong phai vi he thong hong

   mot bang      fact_call (noi Gateway ghi tung luot) khong duoc soi
                 dong ho sai o khau nap Gateway di thang vao day
```

**Quyết định: ngưỡng là `CURRENT_DATE`, và soi năm bảng có cột thời gian:**

```
   fact_call           ts_local     <- nguon gateway ghi o day
   fact_usage_daily    day
   fact_usage_hourly   hour
   fact_billing_daily  day
   fact_monitoring     ts_local
```

**Dung sai một ngày, không phải bằng không.** Quy ước dự án là mọi cột ngày theo **giờ
Việt Nam**, mà `CURRENT_DATE` của máy chủ database có thể lệch múi. Một dòng của hôm nay
không được coi là tương lai chỉ vì hai đồng hồ cách nhau 7 giờ. Ngưỡng là
`> CURRENT_DATE + 1`.

### ③ Phân biệt "ĐẠT" với "KHÔNG CÓ GÌ ĐỂ KIỂM" — quyết định trung tâm

Hình dạng hiện tại của mọi phép kiểm theo nguồn:

```python
   n = a.num("SELECT COUNT(*) FROM fact_call"
             " WHERE source='gateway' AND <dieu kien xau>")
   a.check(n == 0, "...", "...")
```

Với **0 dòng gateway**, `n` bằng 0 và phép kiểm báo **ĐẠT**. Nó không phân biệt *"Gateway
ghi đúng"* với *"Gateway không ghi gì"*.

Đây không phải chuyện lý thuyết: bước `load_gateway.py` hỏng im lặng thì `fact_call`
không có dòng gateway nào, mọi phép kiểm gateway vẫn xanh, và dashboard chỉ trông như
*"chưa có lưu lượng"*.

**Quyết định: mỗi phép kiểm theo nguồn phải khai MẪU SỐ, không chỉ TỬ SỐ.**

```
   quan sat 0 dong    ->  CANH BAO "chua kiem duoc"   (KHONG phai DAT)
   quan sat n > 0 dong,  0 dong xau   ->  DAT, kem "n dong da soi"
   quan sat n > 0 dong,  k dong xau   ->  HONG
```

Con số `n` **in ra trong nhãn**. Một phép kiểm nói *"đạt trên 41 dòng"* khác hẳn một
phép kiểm nói *"đạt"* — và khác đúng ở chỗ người đọc cần biết.

**Vì sao CẢNH BÁO chứ không HỎNG:** database mới dựng, hoặc kỳ chưa có lưu lượng
Gateway, là trạng thái **hợp lệ**. Ranh giới CẢNH BÁO/HỎNG của dự án đã chốt ở
`audit_db.py`: *"có sửa được bằng cách nạp lại không"*. Chưa có dữ liệu thì nạp lại
không giúp gì — đó là CẢNH BÁO. Nhưng nó **phải hiện ra**, vì hôm nay nó vô hình.

### ④ Đối chiếu token cache: viết phép kiểm cho một phép đo CHƯA CHẠY ĐƯỢC

Hai vế, đo cả hai:

```
   ve GATEWAY   fact_call source='gateway'          41 dong · cached_tokens 0/41
   ve HOA DON   fact_billing_daily kind='cached'   461 dong · 252.321.118 token
                                                   214 ngay · 6 agent · 05/01 -> 29/08

   so ngay ca hai nguon CUNG co du lieu:  0
       gateway  31/08 -> 31/08     billing  01/01 -> 29/08
```

Vế hoá đơn giàu, vế Gateway rỗng, và hai khoảng ngày **rời nhau hoàn toàn**.

**Quyết định: viết phép kiểm ĐẦY ĐỦ ngay bây giờ, nhưng cho nó ba kết cục rõ ràng.**

```
   khong ngay nao giao nhau        ->  CANH BAO "chua kiem duoc: hai khoang ngay roi nhau"
                                       kem CA HAI khoang, de nguoi doc thay ngay vi sao

   co ngay giao nhau, gateway rong ->  CANH BAO "gateway chua ghi cached_tokens"
                                       (dung hinh dang hom nay: 0/41)

   co ngay giao nhau, ca hai co so ->  so tung (ngay, agent), ap NGUONG o quyet dinh ⑤
```

**Vì sao viết ngay khi chưa chạy được:** ngày hai nguồn giao nhau, phép kiểm phải **đã
sẵn ở đó**. Viết sau nghĩa là ngày đó không ai nhớ, và cửa sổ so sánh trôi qua — đúng
như cửa sổ lưu giữ của Cloud Monitoring đã trôi mất ba tháng dữ liệu.

**Và tuyệt đối không cho nó báo ĐẠT trên tập rỗng.** Đó là cách dễ nhất để tick xanh
một mục Master Plan bằng một phép kiểm chưa từng kiểm gì. Đây là rủi ro ③ của đề xuất,
và quyết định này chính là chỗ làm nó **không thể xảy ra**.

### ⑤ Ngưỡng sai lệch: chốt TRƯỚC khi có số đầu tiên

STT 7 dòng 19 đã đặt kỷ luật này cho báo cáo đối chiếu: *"ngưỡng chấp nhận sai lệch và
quy trình xử lý khi vượt ngưỡng, **ban hành trước kỳ đo**"*. Áp đúng nó ở đây.

```
   lech <= 1%   trên tổng token cache của (ngày × agent)  ->  DAT
   1% < lech    ->  HONG, in ra tung (ngay, agent) lech va so token lech
```

**Vì sao 1% chứ không phải 0:** hai nguồn đếm ở hai thời điểm khác nhau trong đường gọi
và hoá đơn Google gộp theo ngày phía Mỹ. Đòi khớp tuyệt đối là đòi một thứ không nguồn
nào hứa.

**Vì sao chốt bây giờ:** chốt sau khi thấy số là tự vẽ đích quanh mũi tên. Con số 1%
này có thể **sai** — nhưng nếu sai thì nó sẽ hỏng thành tiếng ở lần đo thật, và lúc đó
sửa nó là một quyết định có bằng chứng, không phải một lần nới cho vừa.

### ⑥ `check_api.py`: kiểm ở tầng HTTP, KHÔNG chép lại câu SQL của audit

`audit_db.py` chạy bằng vai `token` và soi thẳng bảng. `check_api.py` phải soi **thứ
API thật sự trả ra**, qua vai `api_readonly`. Chép câu SQL của audit sang đây là tạo
bản sao thứ hai của cùng một phép đo, và bản sao sẽ trôi — đúng cái bẫy đã dính ngày
21/08 khi `tools/dien_tap_gateway.py` tự chép câu SQL của `store.py` rồi đo bằng logic
đã bị bỏ.

**Quyết định: phép kiểm gateway ở `check_api.py` hỏi qua endpoint.**

```
   /api/usage           co dong nao mang token_source = 'gateway' khong
   /api/usage-hourly    nguon gateway co mat khong, va gio co cat dung dau gio khong
   /api/performance     phan vi cua ngay Gateway phu co ra dung so tho khong
```

Cùng kỷ luật đã áp cho `con_doc_duoc()` ở change trước: **hỏi máy chủ, đừng hỏi kết nối
của chính mình**.

### ⑦ Bốn phép kiểm mà sản phẩm liệt kê — chỗ nào đã có, chỗ nào chưa

Đối chiếu từng chữ của cột Sản phẩm với thứ đang chạy:

| Sản phẩm đòi | Hiện trạng đo được | Việc phải làm |
|---|---|---|
| khoá ngoại | 23/36 quan hệ được kiểm | dựng từ `pg_constraint` — quyết định ① |
| số khớp với hoá đơn | `Cost: invoice + gateway == usage_resolved` **đã có và đạt** | thêm vế **token**, và nó rơi vào bẫy 0 ngày giao nhau — xem ④ |
| không có tài khoản lạ | `Rows from a user-aware source all resolve to an account` **đã có**, lọc `era='gateway'` | thêm mẫu số quan sát — quyết định ③ |
| không có ngày tương lai | có, nhưng ghim `2026` và chỉ soi `usage_resolved` | quyết định ② |

Hai trong bốn đã có phần lõi. **Không viết lại chúng** — thêm cái thiếu, và sửa cái ghim
cứng.

## Risks / Trade-offs

**Số lưu ý của audit SẼ TĂNG, và đó là kết quả đúng.** Mốc hiện tại 68/64/4/0. Quyết
định ③ biến những phép kiểm đang báo ĐẠT-trên-tập-rỗng thành CẢNH BÁO. Phải **đo và ghi
con số mới**, tuyệt đối không hạ tiêu chuẩn để giữ màu cũ — đó chính là thứ change này
đi bịt.

**Đọc `pg_constraint` gắn `audit_db.py` vào PostgreSQL.** Dự án đã bỏ SQLite từ change
`drop-the-sqlite-escape-hatch` (24/08) nên không mất gì mới, nhưng phải ghi ngay tại chỗ
đọc — không để người sau tưởng file này còn chạy đa hệ.

**Phép kiểm tự sinh khó đọc hơn danh sách gõ tay.** Danh sách 23 dòng nói ngay nó kiểm
gì; một câu truy vấn catalog thì không. Bù lại bằng cách **in ra số quan hệ đã kiểm**
trong nhãn, và giữ mốc số lượng ở quyết định ①.

**Ngưỡng 1% ở quyết định ⑤ chưa có cơ sở đo đạc** — chưa có ngày nào giao nhau để hiệu
chỉnh. Nó là một con số **chốt trước**, và phải được ghi rõ là như vậy, kèm câu hỏi nó
đang thay mặt trả lời. Ngày có số thật, nếu nó sai thì sửa **kèm bằng chứng**, không nới
im lặng.
