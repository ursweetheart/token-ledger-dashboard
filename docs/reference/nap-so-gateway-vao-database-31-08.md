# Nạp sổ Gateway vào database — nhật ký 31/08/2026

Chặng cuối của luồng end-to-end. Trước hôm nay, Gateway đã ghi sổ đúng nhưng dashboard không
thấy một dòng nào; nay `usage_resolved` hiện được lưu lượng của DMS Feedback.

Tài liệu này ghi **những gì đo được**, kèm phân biệt rõ cái nào chứng minh được và cái nào
mới là suy luận. Nhật ký chặng trước: `dua-dms-qua-gateway-31-08.md`.

---

## 1. Phát hiện quan trọng nhất: `guess_model` khớp nhầm Flash Lite thành Flash

Đây là thứ suýt đi vào production mà **không phép kiểm tổng nào bắt được**.

`db/rules.py:30` có sẵn một dòng cảnh báo, viết từ trước, cho đúng tình huống này:

> *"Thứ tự QUAN TRỌNG: mẫu dài hơn phải đứng trước. '2.5 flash lite' phải được thử trước
> '2.5 flash', nếu không Flash Lite bị gán nhầm thành Flash."*

Nhưng bảng mẫu chỉ có `"2.5 flash lite"` và `"3.1 flash lite"`. **Không có `"3.5 flash lite"`.**
Trong khi tuyến `gemini-flash-lite` của Gateway định tuyến tới đúng model đó:

```
   guess_model('gemini/gemini-3.5-flash-lite')  ->  gemini-3.5-flash    ← SAI
   bao cao doi chieu lai ghi                    ->  "CO trong dim_model"
```

Chuỗi ngắn nằm trọn trong chuỗi dài, nên `"3.5 flash"` khớp trước. Hậu quả nếu bỏ lọt:

- Toàn bộ lưu lượng DMS bị quy về **model khác, đơn giá khác**
- Tổng token vẫn đúng, tổng tiền vẫn đúng — chỉ **tỷ lệ giữa các model** là sai
- Không có dòng nào biến mất, nên không phép đếm nào kêu

Sửa: chèn `("3.5 flash lite", "gemini-3.5-flash-lite")` **trước** `("3.5 flash", …)`.

**Kiểm rằng sửa không làm hỏng chỗ khác** — vì `MODEL_PATTERNS` dùng chung cho cả nguồn
billing: sinh lại `02_catalog.sql` rồi so với bản trước. **31 ánh xạ SKU billing giữ nguyên
toàn bộ.** Chỉ có phần model là thêm.

---

## 2. Thiết kế sai ở đâu — bốn chỗ, đều lộ ra lúc triển khai

### 2.1 `fact_call` không có cột `source` — nạp thẳng vào là hỏng

Quyết định ① của `design.md` viết *"nạp vào `fact_call`, không dựng bảng mới"* rồi dừng ở đó.
Đo lúc triển khai:

```
   build_usage_daily.py:212   out = [(*r, None, "app") for r in rows]
                              MOI dong fact_call bi gan cung nguon 'app'

   build_usage_daily.py:286   if len(by_source) != 3:
                              phep nghiem thu GHIM CUNG "phai co 3 nguon"
```

Nạp vào mà không có cột `source` thì lưu lượng Gateway **bị đếm thành của app**, và tổng vẫn
khớp nên không ai biết. Còn phép kiểm ghim cứng số 3 thì báo lỗi ngay khi có nguồn thứ tư —
tức là báo lỗi đúng lúc hệ thống đang đúng.

Đã thêm hai cột qua migration `004`: `source TEXT NOT NULL DEFAULT 'app'` (khoá ngoại tới
`ref_source`) và `cost_usd NUMERIC` (Gateway có tiền, app thì không). Kèm chỉ mục
`(source, ts_raw)` cho mốc nạp tăng dần.

### 2.2 `account_id` không được để NULL

Quyết định ⑩ viết *"để `account_id` NULL"*. Nhưng `account_id` nằm trong **khoá chính** của
`fact_usage_daily` — NULL không vào được.

Và đo ra một thứ tốt hơn hẳn: quy ước A3 (20/08) đặt tài khoản dịch vụ theo dạng `svc.<code>`,
đúng dạng mà `GEMINI_GATEWAY_USER` đang gửi. Nên `end_user = 'svc.dms-feedback'` khớp **thẳng**
một dòng `account` — id 949, kind `service_account`, `unit_agent_id = 6`. Không phải suy đoán.

### 2.3 Suýt lặp lại một sự cố đã có tài liệu

Bản đầu của bộ nạp tra neo bằng `accounts.get("svc." + code)`. Bắt được ở bước **tự đọc lại
trước khi chạy**, nhờ docstring của `build_usage_daily.anchor_accounts()`:

> *"TRA BẰNG (kind, unit_agent_id), KHÔNG BẰNG TÊN ĐĂNG NHẬP. Trước 21/08/2026 hàm này tra
> `__whole_agent_<id>__`, tức một chuỗi ký tự do khâu nạp khác đặt ra… Ngày quy ước A3 bắt tài
> khoản dịch vụ đổi sang `svc.<code>`, đúng chỗ đó gãy."*

Hai agent mang `kind = 'whole_agent'` và tên của chúng **không** theo dạng `svc.<code>`. Hôm
nay chỉ agent 6 có lưu lượng nên lỗi chưa nổ — nó sẽ nổ vào ngày agent thứ hai chạy.

Đã thêm `connect.anchor_account_lookup()` tra theo `(kind, unit_agent_id)`.

### 2.4 Phép đối chiếu ban đầu sẽ báo lệch giả

Bản đầu so `dst_rows + bỏ_qua != src_rows`, trong đó `bỏ_qua` chỉ đếm **cửa sổ vừa đọc** còn
hai số kia là của **cả sổ**. Lần chạy tăng dần nào cũng kêu lệch. Cũng bắt ở bước tự đọc lại.

---

## 3. Bốn cái bẫy của dữ liệu — khác với bốn lỗi thiết kế ở trên

| | Bẫy | Nếu bỏ lọt |
|---|---|---|
| ① | `status` không bao giờ NULL (`success`/`failure`, 0/39 dòng NULL) | Lọc `IS NULL` → **0 dòng, không lỗi** |
| ② | `end_user` là **chuỗi rỗng**, không phải NULL (11 dòng `''`, 0 dòng NULL) | Kiểm `IS NULL` bắt 0 dòng, tưởng mọi request đều có người |
| ③ | `error_information` **có mặt ở cả dòng thành công**, mang JSON `null` | `metadata->'…' IS NOT NULL` khớp **cả 39 dòng**, vô dụng. Phải dùng `->>` |
| ④ | `request_tags` trộn tag `User-Agent` do LiteLLM tự thêm | **Một** request thành **ba** agent |

Bẫy ③ đáng chú ý vì nó **cùng họ với bẫy ①**: một khoá tồn tại nhưng mang giá trị null của
JSON, khác hẳn với việc khoá vắng mặt.

Về ④: quy tắc đã chốt là **chỉ tag khớp một dòng `dim_agent.code`** mới là tag định danh.
Không lọc bằng cách bỏ tiền tố `User-Agent:` — cách đó vá đúng triệu chứng hôm nay và sẽ hỏng
khi LiteLLM thêm loại tag tự động khác.

### Một ghi chép cũ của tôi sai

`dua-dms-qua-gateway-31-08.md` mục 8.1 ghi dòng hỏng có `total_tokens = 0`. Đo lại:

```
   spend         0  tren ca 5/5 dong          <- dung
   total_tokens  14 tren 2 dong, 0 tren 3     <- SAI, khong phai luon 0
```

Loại dòng hỏng làm **mất 28 token đã thật sự gửi đi**. Số nhỏ, nhưng phải biết là mất bao
nhiêu chứ không được tin là mất 0. Đã sửa trong tài liệu đó.

---

## 4. Tốc độ — đo trước khi tối ưu

```
   proxy_server_request  6.677 byte/dong      <- nang nhat
   metadata              2.775 byte/dong
   response                979 byte/dong
   messages                  5 byte/dong      (da che)
   -----------------------------------------
   SELECT *           ~ 10.400 byte/dong
   chi cot can dung   ~    200 byte/dong      -> nhe hon ~50 lan
```

Chỗ tốn **không phải số dòng** mà là bề rộng dòng. Ba việc:

1. Câu `SELECT` liệt kê cột tường minh và **bóc JSON ngay trong PostgreSQL**, không kéo cả
   `metadata` về Python.
2. Mốc nạp tăng dần dùng chỉ mục `startTime` **có sẵn** trong sổ. Lần chạy thứ hai chỉ đọc
   2 dòng thay vì 34.
3. Chèn theo lô bằng `execute_values` (`connect.insert_many`, page_size 1000).

Ước tính ở quy mô 1.000 lượt phân loại/ngày (730 nghìn dòng/năm): `SELECT *` chuyển ~7,6 GB,
bản hiện tại ~150 MB.

**Đánh đổi có chủ ý:** mốc nạp **lùi lại một giờ** trước khi đọc, vì sổ ghi bất đồng bộ ~4 giây
— một dòng có `startTime` = T có thể chưa tồn tại lúc bộ nạp đi qua T. Đọc chồng lấn không tốn
gì (chạy bằng chỉ mục) và `ON CONFLICT DO NOTHING` lo phần trùng.

---

## 5. Đã chứng minh được gì

### 5.1 Chuỗi đầy đủ, đo bằng một lượt gọi thật

```
   dong ho VN luc goi ......... 09:26:58
   so Gateway ................. 39 -> 41   (+2, dung: 1 luot phan loai = 2 luot goi LLM)
   bo nap ..................... doc 4 dong (2 moi + 2 chong lan), chen them DUNG 2
   fact_call .................. ts_raw 02:27:00 UTC -> ts_local 09:27:00 VN
   fact_usage_daily ........... 2026-08-31 | agent 6 | model 12 | 32 luot | 25.560 token
   usage_resolved ............. Phan Loai Phan Hoi Tiep Thi | gemini-3.5-flash-lite
                                34 luot | 31.839 token | token_source=gateway
                                token_estimated=1
```

`ts_local` lệch đồng hồ máy **2 giây** — đúng bằng thời gian giữa lúc ghi mốc và lúc gọi.

### 5.2 Không nguồn cũ nào bị đụng

Sau khi thêm hai cột và dựng lại toàn bộ `fact_usage_daily`:

```
   app         371 dong / 112.775.370 token   KHONG DOI
   billing   1.012 dong / 751.189.404 token   KHONG DOI
   monitoring  606 dong / 496.933.793 token   KHONG DOI
   gateway       1 dong /      25.560 token   MOI
```

Migration giữ nguyên **8.631 dòng / 50.068.543 token** của `fact_call`, toàn bộ nhận
`source = 'app'`, 6.871 dòng `cached_tokens` NULL vẫn NULL.

### 5.3 Idempotent, và nhánh hỏng báo rõ

Chạy hai lần liên tiếp: lần hai đọc 2 dòng, **chèn thêm 0**. Với DSN sai cổng, bộ nạp in ba
dòng rồi **thoát mã 1** — không có đường nào nạp 0 dòng rồi báo thành công.

### 5.4 Vai chỉ-đọc thật sự chỉ đọc

```
   doc LiteLLM_SpendLogs ............... true
   ghi LiteLLM_SpendLogs ............... false
   doc LiteLLM_VerificationToken ....... false   <- noi chua bam khoa ao
   sieu quyen .......................... false
   thu CREATE TEMP TABLE ............... cannot execute in a read-only transaction
```

Cố ý **không** dùng lại `docker/read-only-api.sql`: script đó `REVOKE … FROM PUBLIC` trên cả
schema và mọi bảng. Chạy lên database mà LiteLLM đang migrate bằng Prisma là rủi ro thừa.
`docker/read-only-gateway.sql` **chỉ GRANT, không REVOKE**, và chỉ đúng một bảng.

### 5.5 Bộ đếm của bộ nạp khớp truy vấn độc lập

Không tin bộ đếm của chính mình — đối chứng bằng SQL viết riêng:

```
   bo vi khong co tag dinh danh ....  2  khop
   end_user = 'tuan.tran' .......... 13  khop
   end_user = chuoi rong ...........  9  khop
   token cua 2 dong bi bo ..........  42 khop  (31.839 + 42 = 31.881)
```

---

## 6. Vì sao giữ hai database tách nhau

Đo được: **một** instance PostgreSQL, **một** cổng, **một** ổ đĩa — `litellm` 12 MB (chủ
`llmproxy`) nằm cạnh `token_ledger_v2` 213 MB (chủ `token`). Tách ở mức database, **không**
tách ở mức máy chủ.

Lý do quyết định không phải sự tiện lợi mà là **LiteLLM tự chạy migration bằng Prisma**. Gộp
nghĩa là mỗi lần nâng phiên bản nó có quyền `ALTER` ngay trong database chứa dữ liệu dashboard.

Cái giá: PostgreSQL không cho JOIN xuyên database, `postgres_fdw` và `dblink` đều chưa cài,
nên bộ nạp mở **hai kết nối** và ánh xạ ở tầng Python. Ở quy mô này cái giá đó không đáng kể.

Đường giữa chưa dùng tới: cài `postgres_fdw`, giữ hai database mà vẫn JOIN được bằng SQL.

---

## 7. Đã đụng vào những gì

### Repo `token-ledger-dashboard`, nhánh `Tuan-develop`

| File | Việc |
|---|---|
| `db/rules.py` | Thêm model 12 · **chèn `"3.5 flash lite"` trước `"3.5 flash"`** · thêm `GATEWAY_MODELS` |
| `db/gen_catalog.py` | Sinh ánh xạ nguồn `gateway` (44 → 46 ánh xạ) |
| `db/02_catalog.sql` | Sinh lại |
| `db/connect.py` | `GATEWAY_DSN` · `agent_code_lookup` · `account_lookup` · `anchor_account_lookup` · `insert_many(on_conflict=…)` |
| `db/load_gateway.py` | **Mới** |
| `db/build_usage_daily.py` | `load_app` lọc `source='app'` · thêm `load_gateway()` · bỏ ghim cứng `!= 3` |
| `db/migrations/**/004_*` | **Mới** — hai cột + khoá ngoại + chỉ mục |
| `docker/read-only-gateway.sql` | **Mới** |
| `docker-compose.yml` | Service `gateway-readonly-init` |

`insert_many` thêm tham số **mặc định rỗng**, nên 15 chỗ gọi sẵn có không đổi hành vi — đã
kiểm 3/3: đường cũ vẫn ném `UniqueViolation` khi trùng, đường mới không nhân đôi.

### Không đụng

Sổ `LiteLLM_SpendLogs` (chỉ đọc) · ba loader cũ · cấu hình Gateway · bản clone DMS · tầng view.

---

## 7b. Bẫy tìm ra sau cùng: bộ nạp phải nằm trong `rebuild_db.py`

Tìm ra khi trả lời câu hỏi *"chat xong thì dashboard có dữ liệu mới không"*, tức là **sau khi
change đã xong 55/55**. Suýt bỏ lọt.

`scripts/rebuild_db.py` chạy 7 bước theo thứ tự, và bước 1 là `load_billing --rebuild` —
**xoá sạch**. `load_gateway.py` không có trong danh sách đó. Mà `scripts/update_dashboard.py`
bước 8/9 gọi đúng script này.

Hậu quả nếu bỏ lọt: **lần cập nhật dashboard kế tiếp xoá sạch dữ liệu Gateway và không nạp
lại** — không lỗi nào báo, dashboard chỉ đơn giản mất một nguồn.

Đã chèn `("So Gateway", "load_gateway.py", [])` vào **trước** `build_usage_daily` (bảng dẫn
xuất, đọc `fact_call`). Bộ nạp tự dựng lại từ đầu sau khi xoá vì mốc nạp đọc chính `fact_call`:
bảng rỗng → đọc toàn bộ sổ.

**Hệ quả phải biết:** từ nay `rebuild_db.py` **cần Gateway đang chạy**. Gateway tắt thì bước
này thoát mã 1 và cả chuỗi dừng. Đó là hành vi ĐÚNG — sau khi bước 1 đã xoá sạch, lựa chọn
còn lại là một dashboard âm thầm thiếu một nguồn.

---

## 7c. Lỗ hổng danh tính — vá sau khi change đã xong

Tìm ra khi bàn tiếp về việc *"ghi lại ai là người nêu phản hồi"*. Đây là lỗ hổng trong chính
bộ nạp của change này, và nó **chưa gây hại chỉ vì DMS đang gửi định danh dịch vụ**.

Bộ nạp bản đầu tra thẳng `accounts.get(end_user)` — tức là tin bất kỳ chuỗi nào Gateway gửi
tới. Đo ra đường hỏng có thật:

```
   account_id 1 | "admin" | "Quan tri vien" | kind=real | unit_agent_id=5 (TLA Hop Dong)
                | DA MANG 480 luot / 1.588.404 token
```

Ngày DMS gửi `X-User: admin` — tên đăng nhập cục bộ của chính nó — lưu lượng DMS sẽ bị trộn
vào lịch sử của một người dùng TLA Hợp Đồng. Im lặng, tổng vẫn khớp, không phép kiểm nào bắt.

### Hai điều đo được làm đổi cả cách nghĩ

**Email cũng không phải khoá an toàn.** Tôi từng khẳng định là có. Sai:

```
   username trung lap ... 0
   email trung lap ...... 2     long.nt@  -> longnt (agent 8) + pbh1_ntlong (agent 5)
                                phuong.nt@ -> phuong.nt (agent 8) + phuong.nt@... (agent 5)
```

Cùng một người có hai tài khoản ở hai agent. Bảng `account` mịn theo **(người, agent)**, nên
email định danh được *người* nhưng không định danh được *dòng*.

**Agent 6 không có tài khoản `kind='real'` nào — và đó là ĐÚNG QUY ƯỚC, không phải thiếu:**

Quy ước chốt 20/08/2026: 6/8 agent được coi là chỉ có một người dùng, và người đó là tài
khoản dịch vụ `svc.<code>`. DMS nằm trong sáu agent đó. Nên `svc.dms-feedback → account 949`
là **kết quả đúng**, không phải giải pháp tạm.

```
   agent 5  real 45     TLA Hop Dong
   agent 8  real 893    Ralli
   agent 6  real 0      DMS      <- khong co gi de noi toi
```

Kể cả khi DMS gửi tên chuẩn, hiện chưa có dòng nào để nối. Chiều người dùng của DMS chưa tồn tại.

### Cách vá

Không đoán tiền tố, không cần danh sách trắng. Định danh **chỉ được chấp nhận khi nó tra ra
đúng tài khoản neo của chính agent đó**:

```
   svc.dms-feedback -> 949 = neo cua agent 6   ->  NHAN
   admin            -> 1  != 949               ->  TU CHOI, ve neo, va DEM
```

Phép kiểm **âm** 5/5 đạt — chứng minh nó *từ chối* chứ không chỉ *chấp nhận*. Không hồi quy:
38 dòng đang có đều mang `account_id 949`, chạy lại chèn thêm 0 dòng.

Tới ngày DMS gửi tên người thật, chúng sẽ rơi vào bộ đếm `danh tinh khong noi duoc` — **ồn ào,
đúng như mong muốn** — thay vì âm thầm nối nhầm.

---

## 7d. Cho tiền Gateway hiện lên dashboard — và bốn lỗi lộ ra trên đường

Đề xuất ban đầu là *"cho view lấy tiền từ `fact_usage_daily`"*. **Không làm thế**, vì schema
đã quyết định ngược lại và ghi rõ lý do ngay tại dòng `cost_usd` trong `001_baseline.sql`:

> *"CHỈ LẤY TIỀN CỦA HOÁ ĐƠN, KỂ CẢ KHI GATEWAY CÓ SỐ TIỀN CỦA NÓ… Đổ vào đây là biến tiền
> suy ra thành tiền đã xác nhận: giao diện coi `cost_usd IS NULL` là 'chưa có hoá đơn' và gắn
> dấu ≈ dựa vào đó. Để NULL thì dòng Gateway **tự động được tính lại từ `ref_price` VÀ được ghi
> nhãn suy ra**."*

Cơ chế đã có sẵn và đúng. Nó không chạy chỉ vì **`ref_price` thiếu dòng cho model 12**.

Và hệ thống **tự chẩn đoán ra điều đó** — `audit_db.py` kêu đúng hai cảnh báo đã viết sẵn:

```
   [luu y] Khong nguon nao mang tien ma view bo qua ... 1 dong
   [luu y] Model dang dung deu co gia ................ 1 model thieu: gemini-3.5-flash-lite
```

### Giá lấy từ đâu — không bịa, không chờ hoá đơn

`price_table()` chọn SKU **có khối lượng lớn nhất trong hoá đơn**. Model mới chạy qua Gateway
thì chưa có hoá đơn, nên không có khối lượng để chọn. Nhưng catalog **đã có sẵn giá**: 66 SKU
cho hai model 11 và 12.

Vấn đề là riêng model 12 có **24 SKU đầu vào** (text/ảnh/âm thanh/video × thường/flex/priority/
batch/caching). Chọn SKU **text tiêu chuẩn**, rồi đối chiếu với một nguồn hoàn toàn độc lập:

```
   Google Cloud Billing Catalog       vao $0,30 / ra $2,50 / cached $0,03
   Suy nguoc tu 40/40 dong LiteLLM    vao $0,30 / ra $2,50
```

Hai nguồn không liên quan gì nhau, khớp đến từng xu. Sau khi nạp, đối chiếu trên lưu lượng thật:

```
   dashboard suy ra   $0,0213045
   LiteLLM tu tinh    $0,0213050
   chenh lech        -$0,0000005     <- lam tron
```

### Bốn lỗi lộ ra trên đường

**① Bản vá đầu tiên rộng quá tay.** Điều kiện `if k in best` vá theo **từng loại giá**, nên nó
lặng lẽ điền `price_cached` cho model 1, 7, 8 — ba model **đã có hoá đơn**, chỉ thiếu khối
lượng cho SKU cached. Bắt được bằng `diff` trước khi nạp. Đã siết thành *"chỉ model không có
một dòng giá nào"*.

**② Một cảnh báo sắp kêu mãi mãi.** `Khong nguon nao mang tien ma view bo qua` đúng khi viết,
nhưng từ khi Gateway chạy thật thì điều kiện của nó đúng **mọi lần chạy** — mà cảnh báo kêu mãi
là cảnh báo không ai đọc. Không tắt nó (kỹ năng soát cấm nới phép kiểm cho vừa ý), mà **đổi
thành phép kiểm mạnh hơn**: hai bảng giá độc lập có còn khớp trong 1% không. Nó bắt được hai
hỏng thật mà bản cũ không bắt được — model có tiền mà thiếu giá, và `ref_price` lệch khỏi bảng
giá của LiteLLM. Kiểm âm: hạ dung sai xuống 1e-9 thì nó kêu, chứng tỏ nó biết kêu.

**③ `audit_db.py` cộng `fact_call` mà không lọc nguồn — ĐANG HỎNG.**

```
   50.113.730 + 62.706.827 = 112.820.557
   fact_usage_daily (app)  = 112.775.370
   lech                    =      45.187   <- DUNG BANG token Gateway
```

Cùng một lỗi tôi đã sửa trong `build_usage_daily.load_app()` nhưng bỏ sót ở đây. Nó hỏng từ lúc
nạp dòng gateway đầu tiên; tôi chỉ chưa xem đầu ra đầy đủ của audit. **Bài học: chạy audit đầy
đủ sau mỗi lần đổi bảng dùng chung, đừng grep vài dòng.**

Quét tiếp thì ra chỗ thứ tư cùng họ: `build_usage_daily.py:360` tính dung sai từ `fact_call`
không lọc nguồn. Hiện chưa sai số vì dòng Gateway luôn có `total = prompt + completion` (đóng
góp 0) — nhưng đó là đúng-do-may, đã sửa.

**④ `load_org.py:317` `DELETE FROM fact_call` không lọc được.** Khoá ngoại `account_id` bắt phải
dọn sạch bảng con trước khi dựng lại `account`. `rebuild_db.py` xếp đúng thứ tự (org bước 2,
gateway bước 6) nên đường chính an toàn; chạy lẻ `load_org.py` thì mất dữ liệu Gateway. Không
sửa được câu lệnh — đã ghi cảnh báo tại chỗ.

### Kết quả

```
   36 phep kiem | 32 dat | 4 luu y | 0 hong
   ba nguon cu KHONG DOI: app 371/112.775.370 · billing 1.012 · monitoring 606
```

---

## 7e. Tiền Gateway lên dashboard — và một quyết định bị đảo ngược

Chốt 31/08: **hiển thị thẳng số tiền của LiteLLM**, không gắn cờ ước tính. Đây là quyết định
của chủ dự án, và nó **đảo ngược** một quyết định của baseline 001.

### Tiền đề được đo, không được gật

Lý do đưa ra là *"dữ liệu vốn đã không đồng nhất, con nào có billing chuẩn đâu"*. Đo lại:

```
   Tro ly ao Ralli ............... 100,0% uoc tinh   <- dung
   Tro Ly Ao Hop Dong .............  78,1%           <- dung
   Phan Loai Phan Hoi Tiep Thi ....  33,8%
   Tools Quizzer ..................  19,6%
   Phan Loai Du Lieu CRM ..........  18,7%
   Sale Agent .....................  18,6%
   Multi modal AI Invoice .........  13,1%
   Chatbot Contact Center .........   2,1%           <- gan nhu toan hoa don that
```

Đúng với **2/8 agent**. Sáu agent còn lại phần lớn là hoá đơn thật — tổng 71,7% tiền trên
dashboard đến từ hoá đơn. Đã trình bày số này trước khi làm; chủ dự án giữ quyết định.

### Làm gì

Migration `005`: `cost_usd = COALESCE(b.cost, g.cost)` — **hoá đơn trước, gateway sau**.

Thứ tự này **khác** thứ tự của token (gateway trước), và đó là cố ý: token thì Gateway đếm
chính xác hơn hoá đơn; còn tiền thì hoá đơn là số Google thực sự trừ.

`token_estimated` **giữ nguyên** — nó nói về token, không nói về tiền.

### Hai cái bẫy trên đường

**① Audit sẽ đỏ mỗi ngày.** Phép kiểm `Tien: hoa don == usage_resolved` so tiền view với
`fact_billing_daily`. Thêm tiền gateway vào view là nó lệch $0,021305 — vượt dung sai $0,0001.
Và `audit_db.py` thoát mã 1, còn `update_dashboard.py` chạy nó ở **bước 9/9**, nên mỗi lần cập
nhật dashboard sẽ thất bại. Hại thật không phải dòng chữ đỏ mà là: hỏng mỗi ngày vì lý do đã
biết thì vài hôm sau không ai đọc nữa.

**② Suýt tính đôi.** Bản sửa hiển nhiên là `hoá đơn + toàn bộ gateway`. **Sai.** View ưu tiên
hoá đơn, nên dòng nào có CẢ HAI thì tiền gateway bị bỏ. Hôm nay chưa trùng (gateway 31/08,
hoá đơn của agent 6 dừng ở 27/08) — nhưng **ngày mai hoá đơn 31/08 về là trùng ngay**. Đã dùng
`NOT EXISTS` lấy đúng phần gateway mà view thực sự dùng, và kiểm bằng phép thử âm giả lập:

```
   gia lap 31/08 DA co hoa don  ->  gw duoc tinh = $0,500000
                                    (KHONG phai $0,521305)
```

### Đã thay thế một yêu cầu spec — ghi rõ để không ai tưởng là quên

`label-derived-cost-across-dashboard`, `specs/visible-data-provenance`:

> *"Mọi ô, thẻ, biểu đồ và dòng xuất CSV có chứa tiền SHALL cho biết phần nào đến từ hoá đơn
> và phần nào suy từ bảng giá. MUST NOT trình bày hai loại giống hệt nhau."*

Với nguồn `gateway`, yêu cầu này **không còn hiệu lực**. Ba nguồn cũ giữ nguyên. Lý do ghi ở
đầu `db/migrations/sql/005_gateway_cost_vao_view.sql` và ở tasks mục 9.

### Kết quả

```
   head 005_gateway_cost | view 1.276 dong / 12 cot KHONG DOI
   tong tien  307,382155 = 307,360850 + 0,021305
   audit      36 phep kiem | 32 dat | 4 luu y | 0 hong

   Man hinh:  hoa don $307,3822 / 1.013 dong
              uoc tinh ≈ $121,2823 / 263 dong
```

---

## 8. Việc còn lại, và những gì CHƯA chứng minh

### Còn lại

- **Tiền của Gateway lưu được nhưng chưa hiện.** View `usage_resolved` lấy `cost_usd` **chỉ từ
  billing** — quyết định có sẵn từ change `admit-gateway-as-a-fourth-source`. Dòng gateway hiện
  ra với `cost_usd` rỗng và `token_estimated = 1`. Số tiền vẫn nằm trong `fact_usage_daily`,
  chờ một change riêng ở tầng view quyết định có phơi ra hay không.
- **Chưa gọi được API của dashboard**: `.env` không có khoá, API bị chặn bởi change
  `require-a-key-to-read-the-api`. Đường dữ liệu tới `usage_resolved` thì đã chứng minh xong.
- **Tuyến `gemini-3-flash-preview` cố ý bỏ khỏi `GATEWAY_MODELS`.** `guess_model` sẽ gộp nó vào
  `gemini-3-flash`, mà đơn giá bản preview so với bản chính thức thì chưa ai kiểm. Để lưu lượng
  của nó rơi vào mục "không nối được model" — ở đó nó được **đếm và in ra**.
- `data_to` của agent 3 và 4 đổi khi sinh lại catalog (17/08 → 26/08, 01/07 → 21/08). Không do
  change này: catalog cũ hơn dữ liệu trên đĩa. Nhưng cả hai agent đang `is_running = FALSE` mà
  vẫn có dữ liệu tới cuối tháng 8 — **đáng xem lại**, có thể `ranges` đếm cả lưu lượng ngoài AI.

### Chưa chứng minh — đừng đọc thành đã biết

| | Mức |
|---|---|
| Luồng nạp, múi giờ, idempotent, đối chiếu | **Chứng minh được** — đo nhiều lần, có đối chứng độc lập |
| Bí danh chỉ xuất hiện ở dòng hỏng | **Suy luận** — đúng trên 41 dòng, lý do suy từ cơ chế Router chứ chưa đọc mã |
| Neo mức agent cho 7 agent còn lại | **Chưa đo** — mới agent 6 có lưu lượng |
| `GATEWAY_MODELS` không lệch khỏi config | **Chưa có kiểm tự động** — cơ chế phát hiện là bộ đếm "không nối được model" |
| Hành vi ở quy mô hàng trăm nghìn dòng | **Chưa đo** — mới 34 dòng |
