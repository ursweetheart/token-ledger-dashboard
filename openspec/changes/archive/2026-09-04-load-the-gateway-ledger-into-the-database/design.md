# Thiết kế — nạp sổ Gateway vào database

Mọi con số trong tài liệu này đo trên **39 dòng thật** trong `LiteLLM_SpendLogs` ngày
31/08/2026, không suy từ tài liệu.

---

## ① Nạp vào `fact_call`, không dựng bảng mới

`LiteLLM_SpendLogs` là bảng **một dòng một lượt gọi**. `fact_call` cũng vậy, và đã có sẵn
đúng ba cột cần cho vấn đề múi giờ:

```
   fact_call.ts_raw        chep NGUYEN startTime
   fact_call.tz_confirmed  TRUE khi da chung minh duoc mui gio goc
   fact_call.ts_local      gio Viet Nam
```

`measure-what-the-gateway-records` có nhắc tới một bảng `fact_request` trong tương lai. **Chưa
dựng nó trong change này.** Tài liệu chính của dự án xếp "dựng sẵn `fact_request`" vào mục
việc KHÔNG nên làm khi chưa chốt hình dạng, và hôm nay mới có **một** agent chạy thật — chưa
đủ để chốt.

### Sửa 31/08 khi triển khai: phải thêm HAI cột, không nạp thẳng được

Bản đầu của quyết định này nói *"nạp vào `fact_call`, không dựng bảng mới"* và dừng ở đó.
**Thiếu.** Đo lúc triển khai cho thấy nạp thẳng vào `fact_call` là hỏng ngay:

```
   build_usage_daily.py:212   out = [(*r, None, "app") for r in rows]
                              MOI dong fact_call bi gan cung nguon 'app'
                              -> luu luong gateway se bi dem thanh cua app

   build_usage_daily.py:286   if len(by_source) != 3:
                              phep nghiem thu GHIM CUNG "phai co 3 nguon"
                              -> them nguon thu tu la no BAO LOI

   fact_call                  khong co cot `source`, cung khong co cot tien
```

Nên change này **thêm hai cột** vào `fact_call`:

| Cột | Kiểu | Vì sao |
|---|---|---|
| `source` | `TEXT NOT NULL DEFAULT 'app'` | 8.631 dòng cũ đều là app. Khoá ngoại tới `ref_source` cho khớp cách `fact_usage_daily` đang làm |
| `cost_usd` | `NUMERIC` (cho phép NULL) | Gateway **có** tiền; app thì không. NULL cho dòng app là đúng nghĩa, không phải thiếu dữ liệu |

Cả hai đều là `ADD COLUMN` — từ PostgreSQL 11 thì thêm cột kể cả có `DEFAULT` không viết lại
bảng, chỉ ghi vào siêu dữ liệu. Dự án đã **diễn tập đúng thao tác này** ở migration 002/003.

Kèm một chỉ mục `(source, ts_raw)`: mốc nạp tăng dần hỏi đúng câu
`WHERE source='gateway' ORDER BY ts_raw DESC LIMIT 1`. Với 8.631 dòng thì chưa cần, nhưng
bảng này sẽ lớn nhanh — mỗi lượt phân loại đẻ hai dòng.

Phương án bảng riêng `fact_gateway_call` đã cân nhắc và **loại**: nó tạo hai bảng cùng một độ
mịn, và chính là việc dự án cố ý hoãn (`fact_request`) khi mới có một agent chạy thật.

## ② Lọc `status = 'success'`, đếm riêng `failure` — không im lặng bỏ

```
   SELECT count(*) WHERE status IS NULL   ->  0 / 39
   DISTINCT status                        ->  failure, success
```

Bản đầu của nhật ký 31/08 ghi *"dòng thành công có `status` NULL"* — **sai**, đã sửa. Nếu
loader viết theo bản sai thì nó nạp **0 dòng và không báo lỗi**, dashboard hiện số 0 trông y
hệt "chưa có lưu lượng".

Dòng `failure` **không nạp vào `fact_call`**, nhưng **phải đếm và in ra**. Số lượt hỏng là
chỉ báo sức khoẻ, vứt đi là mất thông tin.

Đo lại 5 dòng hỏng — và kết quả **bác bỏ** điều tôi tưởng:

```
   spend         0  tren ca 5/5 dong          <- dung nhu tuong
   total_tokens  14 tren 2 dong, 0 tren 3     <- SAI so voi ghi chep cu ("luon = 0")
```

Nghĩa là loại dòng hỏng làm **mất 28 token đã thật sự gửi đi**. Con số nhỏ nhưng phải biết
rõ là mất bao nhiêu, chứ không được tin là mất 0.

### Cái bẫy `error_information` — cùng họ với bẫy `status NULL`

```
   status=failure  -> metadata->>'error_information' CO gia tri that  5/5
   status=success  -> metadata->'error_information' = JSON null      34/34
```

Khoá `error_information` **có mặt ở cả dòng thành công**, chỉ là mang giá trị JSON `null`. Nên
`metadata->'error_information' IS NOT NULL` khớp **cả 39 dòng** — vô dụng. Phải dùng toán tử
`->>` (trả về text) thì JSON null mới thành SQL NULL. Dù vậy vẫn nên lọc bằng `status`: nó
trực tiếp và đã đo.

## ③ Múi giờ: `ts_raw` nguyên bản, `ts_local = ts_raw + 7h`, `tz_confirmed = TRUE`

```
   kieu cot startTime ...... timestamp without time zone   (KHONG mang mui gio)
   TimeZone cua DB ......... UTC
   dong ghi luc 07:56 VN ... luu 00:56
   dong ghi luc 02:33 VN ... luu 30/08 19:33     <-- LECH SANG NGAY HOM TRUOC
```

Đã chứng minh chứ không suy luận: đồng hồ máy 07:56 (+07), đồng hồ container 00:47 UTC, dòng
vừa ghi mang 00:56. `tz_confirmed = TRUE` là chính đáng.

Làm giống hệt `load_ralli.py`, kể cả việc **giữ nguyên `ts_raw`** để sau này còn kiểm lại được.

Nếu bỏ khâu +7h: tổng cả kỳ vẫn đúng, nhưng mọi lượt gọi từ 17:00 tới nửa đêm bị dồn sang
ngày hôm trước. Đây là loại lỗi tổng khớp mà phân bố sai — cùng họ với lỗi múi giờ nguồn Ralli.

## ④ Định danh agent: suy từ tag, sau khi bỏ tag User-Agent

Ba khả năng đều đã đo, hai cái đầu **không dùng được**:

| Nguồn | Đo được | Dùng được? |
|---|---|---|
| Cột `agent_id` của LiteLLM | NULL 39/39 | ✗ |
| `session_id` | 39/39 khác nhau, không gom được 2 lượt của 1 lần phân loại | ✗ |
| `request_tags` | có tag `dms-feedback`, khớp đúng `dim_agent.code` | ✓ |

Nhưng `request_tags` bị trộn:

```
   ["dms-feedback", "User-Agent: python-httpx", "User-Agent: python-httpx/0.28.1"]
```

**Quy tắc:** chỉ tag nào **khớp một dòng trong `dim_agent.code`** mới là tag định danh. Không
lọc bằng cách bỏ tiền tố `User-Agent:` — cách đó vá đúng một triệu chứng hôm nay, và sẽ hỏng
khi LiteLLM thêm loại tag tự động khác.

**Không được nạp** dòng có 0 tag định danh, hoặc có ≥2 tag định danh. Cả hai trường hợp đều
phải đếm riêng và in ra. Đây không chỉ là chính sách — `fact_call.agent_id` là **NOT NULL**,
nên schema cưỡng chế điều đó: không có agent thì không có cách nào nạp vào. Đo 31/08: **4/39** dòng không mang tag `dms-feedback` — ba dòng từ
thời chưa gắn tag, và một dòng của phép kiểm mồi `khong-ai-dung`.

## ⑤ Model: phải thêm dòng vào `dim_model` trước, LEFT JOIN chứ không INNER

```
   dim_model co .......... gemini-3.5-flash · gemini-3.1-flash-lite · gemini-2.5-flash-lite
   dim_model KHONG co .... gemini-3.5-flash-lite
   dim_model_alias ....... khong co bi danh nao khop
```

Nếu dùng INNER JOIN thì **34/34 dòng đáng nạp biến mất, không một lời cảnh báo**. Đây đúng là
hình dạng lỗi mà dự án đã gặp nhiều lần: khâu nối hỏng → 0 dòng → trông như "chưa có dữ liệu".

Ràng buộc của schema đứng về phía quyết định này: `fact_call.model_id` **cho phép NULL** và có
khoá ngoại tới `dim_model`. Nên LEFT JOIN là an toàn, còn INNER JOIN thì không những sai mà
còn giấu luôn cái sai.

Quyết định:

- Thêm `dim_model` một dòng `gemini-3.5-flash-lite`, họ `gemini-3`, nhà cung cấp Google.
- Thêm `dim_model_alias` dòng `source='gateway'`, `raw_name='gemini/gemini-3.5-flash-lite'`.
  Cột `model` của sổ mang **tên upstream có tiền tố nhà cung cấp**, không phải bí danh.
- Loader dùng **LEFT JOIN** và **đếm số dòng không nối được**, in ra. Không bao giờ INNER.

Lấy tên từ cột `model`, không lấy `model_group`. `model_group` là bí danh (`gemini-flash-lite`)
— nó cho biết agent *xin* gì, không cho biết Google *tính tiền* model nào.

**Cột `model` không đồng nhất, và sự không đồng nhất đó lại có ích:**

```
   status=success  ten upstream `gemini/gemini-3.5-flash-lite`  34/34   <- luon co tien to
   status=failure  BI DANH `gemini-flash-lite` / `gemini-flash`  3/5
                   ten upstream                                  2/5
```

Dạng bí danh **chỉ xuất hiện ở dòng hỏng** — hợp lý, vì request hỏng trước khi Router chốt được
tuyến thì không có tên upstream để ghi. Mọi dòng đáng nạp đều mang tên upstream, nên khâu nối
chỉ cần lo một dạng. Ngược lại, nếu sau này thấy **dòng success mang bí danh**, đó là dấu hiệu
có gì đó đổi trong Router — đáng dừng lại xem.

## ⑥ Tiền của LiteLLM là ƯỚC TÍNH — phải mang nhãn

`metadata->cost_breakdown` có sẵn tách input/output:

```json
  {"input_cost": 0.0016956, "output_cost": 0.00102, "total_cost": 0.0027156,
   "original_cost": 0.0027156, "margin_percent": 0.0, "discount_percent": 0.0}
```

Con số này do **bảng giá nội bộ của LiteLLM** nhân ra, không phải số Google xuất hoá đơn. Nó
cùng loại với 32% số tiền đang hiển thị trên dashboard mà giao diện không nói là ước tính —
vấn đề đã ghi nhận, không được làm nó tệ thêm.

Nên: nạp `cost_usd` từ `total_cost`, nhưng **change này không được để nó xuất hiện trên
dashboard mà không có nhãn**. Nhãn đi theo `source='gateway'`, thống nhất với cơ chế của
`label-derived-cost-across-dashboard`.

`margin_percent` và `discount_percent` đều bằng 0 trên **34/34 dòng success** — chưa ai bật,
chưa cần xử.

Nhưng **5 dòng `failure` không có khối `cost_breakdown` nào cả**, không phải có mà bằng 0. Loader
đọc `metadata->cost_breakdown->total_cost` trên dòng hỏng sẽ nhận NULL. Vô hại ở đây vì dòng hỏng
bị loại từ trước, nhưng phải nhớ nếu về sau có ai muốn tính chi phí của cả lượt hỏng.

## ⑦ `cached_tokens`: có đường lấy, hiện toàn NULL — nạp NULL, không nạp 0

Không có cột riêng. Đường lấy là:

```
   metadata -> usage_object -> prompt_tokens_details -> cached_tokens
```

Đo 39/39 dòng: **toàn bộ NULL**. Áp quy tắc 5 của dự án — trường thiếu nạp NULL, KHÔNG nạp 0.
Nạp 0 rồi lấy trung bình từng sai 7,5 lần ở nguồn Ralli; và chính chiều cached từng làm
dashboard hụt 26% token.

Cột `cache_hit` của sổ mang chuỗi `'None'` (chuỗi, không phải NULL) ở phần lớn dòng — **không
dùng cột đó**, nó nói về cache của LiteLLM chứ không phải cached token của Google.

## ⑧ Idempotent theo `request_id`

`request_id` là khoá tự nhiên, một dòng một lượt gọi. Đã đo chứ không giả định:

```
   tong dong ................ 39
   request_id phan biet ..... 39
   trung lap ................  0
   fact_call.call_id ........ PRIMARY KEY   <- ON CONFLICT dung duoc ngay
```

Dùng nó làm `fact_call.call_id` với `ON CONFLICT DO NOTHING`, để chạy lại loader nhiều lần
không nhân đôi dữ liệu.

Không dùng cửa sổ thời gian làm mốc nạp tăng dần: sổ ghi **bất đồng bộ ~4 giây**, nên một lượt
nạp ngay sát mốc sẽ bỏ sót đúng những dòng vừa sinh. Khoá tự nhiên miễn nhiễm với chuyện này.

## ⑨ Một lượt phân loại = HAI dòng sổ

```
   pipeline/rag_product.py:190       generate()        243 +   3 =   246 token
   pipeline/issue_classifier.py:424  generate_json()  5.652 + 408 = 6.060 token
```

`fact_call.calls` sau khi tổng hợp là **số lượt gọi LLM**, không phải số việc nghiệp vụ. Ai
đọc dashboard mà hiểu "39 dòng = 39 lần phân loại" là sai gấp đôi. Phải ghi rõ trong docstring
của loader, vì đây là thứ không ai đoán ra khi nhìn bảng.

## ⑩ Người dùng: `end_user` rỗng thì nạp NULL

```
   svc.dms-feedback ... 13 dong     (dinh danh dich vu, khong phai nguoi)
   tuan.tran .......... 15 dong     (nguoi that, tu cac luot curl tay)
   CHUOI RONG ......... 11 dong
   THUC SU NULL ....... 0 dong      <-- luu y
```

`svc.dms-feedback` là **định danh dịch vụ**, cố ý đặt vậy để không bịa ra một con người chịu
trách nhiệm cho request do máy sinh. Nó không nối với `dim_user` được và **không nên** nối.

**Cái bẫy:** khi không có định danh, sổ ghi **chuỗi rỗng**, không phải NULL. Đo 39 dòng: 11
dòng mang `''`, **0 dòng NULL**. Loader kiểm `end_user IS NULL` sẽ bắt được **0 dòng** và
tưởng mọi request đều có người. Phải dùng `NULLIF(end_user, '')`.

Sau khi quy đổi, `end_user` rỗng nạp NULL vào `fact_call`. Không thay bằng chuỗi
`'Không xác định'` ở tầng nạp — việc gán nhãn đó là của tầng view, giống cách ba nguồn cũ.

## ⑪ Giữ hai database tách nhau — không gộp

Đo 31/08 trước khi quyết:

```
   MOT container postgres, MOT instance, MOT cong 5432, MOT o dia
      litellm ........... 12 MB    chu so huu llmproxy    <- LiteLLM ghi
      token_ledger_v2 ... 213 MB   chu so huu token       <- dashboard doc
      token_ledger ...... 193 MB   chu so huu token       (ban cu)
```

Nghĩa là **tách ở mức database, không tách ở mức máy chủ**: cùng tiến trình, cùng ổ đĩa, chết
cùng nhau nếu container chết. Cái "độc lập" hôm nay mỏng hơn nghe tưởng.

**Quyết định: giữ tách.** Lý do quyết định không phải sự tiện lợi mà là **LiteLLM tự chạy
migration bằng Prisma**. Gộp nghĩa là mỗi lần nâng phiên bản LiteLLM, nó có quyền `ALTER`
ngay trong database chứa 213 MB dữ liệu dashboard. Bản fork đang ghim ở commit `f005afa146`,
nhưng ghim không phải là không bao giờ nâng.

Phương án bị loại và cái giá của việc loại nó:

| | Giữ tách (chọn) | Gộp một database (loại) |
|---|---|---|
| Viết loader | 2 kết nối, ánh xạ ở Python | 1 câu `INSERT … SELECT … JOIN` |
| LiteLLM nâng cấp | migration chỉ chạm 12 MB của nó | migration chạy trong DB 213 MB của dashboard |
| Sổ gốc làm bằng chứng | ranh giới rõ | một lệnh admin nhầm là chạm được |
| Tách máy chủ về sau | đổi chuỗi kết nối | phải gỡ ra |

**Hệ quả bắt buộc phải chấp nhận:** Postgres không cho truy vấn xuyên database, và cả
`postgres_fdw` lẫn `dblink` đều **chưa cài**. Nên loader **buộc phải mở hai kết nối** và ánh
xạ agent/model ở tầng Python — không viết được `INSERT … SELECT … JOIN dim_agent`.

Cái giá đó nhỏ ở quy mô hiện tại: 2 dòng sổ mỗi lượt phân loại, cỡ 730 nghìn dòng/năm nếu
chạy 1.000 lượt/ngày. Nếu về sau ánh xạ Python cồng kềnh thật thì còn **đường giữa chưa dùng
tới**: cài `postgres_fdw`, giữ hai database mà vẫn JOIN được bằng SQL — có cái lợi của gộp
mà không mở cửa cho migration của LiteLLM. Không làm trong change này.

### Phát hiện kèm theo: ranh giới hiện chỉ là danh nghĩa, không phải quyền

```
   CONNECT toi database         SELECT bang trong litellm
   llmproxy     -> v2 :  CO
   token        -> litellm :  CO      (sieu quyen, thay tat ca)
   api_readonly -> litellm :  CO      api_readonly doc duoc  0 / N bang
```

Ranh giới **có** được cưỡng chế, nhưng ở tầng bảng chứ không phải tầng database: `CONNECT` vẫn
mở cho `PUBLIC` theo mặc định của Postgres, còn quyền `SELECT` thì không được cấp — đo được
`api_readonly` đọc được **0 bảng** trong `litellm`.

Nên phát biểu đúng là: *vào được cửa, nhưng không mở được tủ nào*. Đủ an toàn để không phải xử
trong change này, nhưng **có hệ quả trực tiếp**: loader không dùng lại được vai `api_readonly`,
phải cấp `SELECT` trên `LiteLLM_SpendLogs` cho một vai chỉ-đọc. Xem task 2.2.

---

## Những gì change này CỐ Ý không làm

- **Không dựng `fact_request` / `fact_attempt`.** Mới một agent chạy thật, chưa đủ chốt hình dạng.
- **Không sửa ba loader cũ.** Đối chiếu bốn nguồn là việc của change sau.
- **Không đụng `LiteLLM_SpendLogs`.** Loader chỉ đọc. Sổ Gateway là bằng chứng gốc.
- **Không tự suy ra `unit_id` / `account_id`** cho dòng gateway. Chưa có đường nối đã chứng
  minh được từ định danh dịch vụ về đơn vị; bịa ra thì hỏng chiều phòng ban của cả dashboard.
