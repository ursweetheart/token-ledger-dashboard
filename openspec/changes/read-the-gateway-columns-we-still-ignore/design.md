# Thiết kế — đọc nốt những cột sổ Gateway đang bị bỏ qua

Mọi con số đo trên **47 dòng thật** trong `LiteLLM_SpendLogs`, ngày 01/09/2026.

---

## ① Ba cột mới trên `fact_call`

| Cột | Kiểu | Vì sao |
|---|---|---|
| `raw_model` | `TEXT`, cho phép NULL | tên model **đúng như Gateway nhận được**, trước khi ánh xạ |
| `virtual_key_id` | `TEXT`, cho phép NULL | khoá đã gọi lượt này. TEXT chứ không phải mã băm — xem ④ |
| `cache_hit` | `BOOLEAN`, cho phép NULL | ba trạng thái, không phải hai — xem ② |

Cả ba `ADD COLUMN` nullable không `DEFAULT`, nên PostgreSQL chỉ ghi siêu dữ liệu chứ không viết
lại bảng. Cùng đường đã đi ở migration 004 và 006.

**Nguồn `app` để NULL cả ba.** Nhật ký Ralli không ghi tên model gốc, không có khoá ảo, và
không có khái niệm cache. Đặt giá trị cho chúng là **bịa** — cùng lý lẽ với `outcome` ở
migration 006.

## ② `cache_hit` — HAI cái bẫy khác nhau ở hai đầu

Bản đầu của mục này viết *"`cache_hit` có ba giá trị `NULL` / `False` / `True`, phải lọc bằng
`IS NOT TRUE`"*. **Sai ở vế nguồn.** Đo kiểu dữ liệu thật:

```
   information_schema:  cache_hit  data_type = text     <- KHONG phai boolean

   gia tri tho          do dai   so dong
   'True'                    4         1
   'False'                   5         5
   'None'                    4        41   <- CHUOI 4 KY TU, khong phai SQL NULL
```

**Bẫy ở VẾ NGUỒN — chuỗi `'None'`.** Không có một dòng SQL NULL nào trong cột này. Hậu quả:

```sql
   WHERE cache_hit IS NULL      -> 0 dong, du 41/47 dong "khong co thong tin"
   WHERE cache_hit IS NOT TRUE  -> LOI KIEU, khong chay noi
   WHERE NOT cache_hit          -> LOI KIEU, khong chay noi
```

Nên bộ nạp phải dịch tường minh, và **đếm giá trị lạ** thay vì ép kiểu mù:

```sql
   CASE WHEN cache_hit = 'True'  THEN true
        WHEN cache_hit = 'False' THEN false
        ELSE NULL END
```

Không dùng `::boolean`: gặp một giá trị thứ tư là câu truy vấn **ném lỗi giữa chừng**, còn
`CASE` thì quy về NULL và bộ đếm sẽ báo. Cùng cách đã làm với `outcome` ở change trước.

**Bẫy ở VẾ ĐÍCH — logic ba trị.** Sau khi nạp, `fact_call.cache_hit` là `BOOLEAN` thật với NULL
thật. Lúc đó bẫy ba trị mới có hiệu lực:

```sql
   AND NOT cache_hit          -> NOT NULL ra UNKNOWN -> vut sach 41 dong NULL
   AND cache_hit IS NOT TRUE  -> DUNG
```

Hai cái bẫy này **ngược nhau**: ở nguồn thì `IS NOT TRUE` không chạy được, ở đích thì nó là
cách duy nhất đúng. Viết nhầm đầu nào cũng hỏng, và cả hai đều hỏng **im lặng ở mức số liệu**.

## ③ Lượt trúng cache: LƯU vào `fact_call`, KHÔNG cộng vào số liệu sử dụng

Đúng hình dạng quyết định đã chốt cho lượt hỏng ở change trước, và vì cùng một lý do: sổ phải
đầy đủ, còn phép tổng hợp thì phải lọc tường minh.

```
   fact_call          GIU luot trung cache   -> con tra cuu duoc, con dem duoc ty le trung
   fact_usage_daily   BO luot trung cache    -> vi nha cung cap KHONG tinh tien luot do
```

### Lỗ rò CHƯA chứng minh được bằng dữ liệu đang có

Bản đầu viết *"quên bộ lọc thì rò đúng 352 token"*. **Không kiểm chứng được.** Dòng trúng cache
duy nhất trong sổ là do phép nghiệm thu 01/09 tạo ra, và nó mang tag:

```
   ["User-Agent: Python-urllib", "User-Agent: Python-urllib/3.13"]
```

**Không có tag agent**, nên `resolve_agent()` không quy được về agent nào và bộ nạp **bỏ dòng
đó** trước khi nó kịp chạm `fact_call`. Lỗ rò là thật về cơ chế, nhưng con số 352 thì hiện
**không xảy ra**.

Nên change này phải **tự tạo ra bằng chứng**: bật cache rồi gọi hai lượt giống nhau **bằng
chính khoá ảo của DMS**, để dòng trúng cache mang tag `dms-feedback` và đi hết đường nạp. Đó là
việc 6, và việc 4.2 phụ thuộc vào nó.

**Không lọc ở tầng nạp.** Lượt trúng cache là một lượt gọi có thật, agent có nhận được câu trả
lời. Bỏ nó khỏi `fact_call` là làm sổ nói dối về số lượt.

## ④ `virtual_key_id`: cột nguồn TRỘN HAI LOẠI GIÁ TRỊ

```
   8112bdb7eca52b7f...        64 ky tu, bam SHA-256    khoa ao
   b3f2765d1d32ddc7...        64 ky tu, bam SHA-256    khoa ao
   litellm_proxy_master_key   CHUOI THUONG             khoa tong
```

Cột `api_key` **không phải lúc nào cũng là mã băm**. Với khoá tổng, LiteLLM ghi thẳng chuỗi
`litellm_proxy_master_key`.

**Quyết định: nạp nguyên văn, không chuẩn hoá.** Ép nó về một dạng là mất đúng cái phân biệt
đang cần. Thay vào đó bộ nạp **đếm và in riêng** số lượt đi bằng khoá tổng:

```
   ca so       11/47 luot (23,4%) di bang khoa tong
   NAP DUOC     7/41 luot (17,1%),  84 token      <- con so that su lam ban du lieu
```

Hai con số này khác nhau vì 4 lượt khoá tổng không mang tag agent nên bị bỏ ngay ở tầng nạp.
**Con số phải theo dõi là 7/41**, vì đó là phần thực sự nằm lẫn trong lưu lượng của agent.
Nó phải giảm về 0 khi 8 agent đều có khoá riêng. In nó ra mỗi lần chạy để nó không
lặng lẽ nằm đó.

**Không đặt phép kiểm bắt buộc "không dòng nào dùng khoá tổng"** — hôm nay nó sẽ hỏng ngay với
11 dòng, và một phép kiểm luôn đỏ thì chẳng ai nhìn nữa.

## ⑤ `raw_model`: giữ nguyên văn, không chuẩn hoá

```
   gemini/gemini-3.5-flash-lite   42 dong   ten upstream  -> model_id 12
   gemini/gemini-3.6-flash         2 dong   ten upstream  -> model_id 11
   gemini-flash-lite               2 dong   BI DANH       -> model_id NULL
   gemini-flash                    1 dong   BI DANH       -> model_id NULL
```

Bí danh là **`model_name` khai trong `config.gateway.yaml`**; tên upstream là thứ Router điền
vào sau khi đã chốt tuyến. Nên dòng mang bí danh chính là dòng **hỏng trước khi Router chốt
tuyến** — đúng phân biệt đã tách bộ đếm ở change trước.

Giá trị của cột này là ở chỗ: khi `model_id` ra NULL, `raw_model` **là bằng chứng duy nhất còn
lại** để biết nên khai thêm tuyến nào vào `GATEWAY_MODELS`.

## ⑥ CHƯA BIẾT: cache có tách theo khoá ảo không

Nếu khoá cache **không** gồm khoá ảo, thì hai agent hỏi cùng một câu sẽ dùng chung một câu trả
lời. Hậu quả không phải lỗi kỹ thuật mà là **lỗi quy tiền**: lượt của agent B trả về nội dung
đã tính tiền cho agent A, và agent B ghi `spend = 0`.

Change này **không kết luận** chuyện đó. Nó đặt một phép đo:

```
   1. Bat cache
   2. Goi cau X bang khoa ao A   -> ghi so
   3. Goi cau X bang khoa ao B   -> cache_hit TRUE hay NULL ?
   4. Tat cache
```

Kết quả ghi vào tài liệu, **không** biến thành cấu hình cho tới khi có người quyết.

---

## Những gì change này CỐ Ý không làm

- **Không bật cache.** Change này chỉ làm cho việc bật cache **an toàn**, không tự bật. Quyết
  định bật thuộc mục Master Plan Giai đoạn 6 mục 1, sau khi có báo cáo đối chiếu bốn nguồn.
- **Không nạp `messages` và `response`.** `turn_off_message_logging: true` đang xoá chúng có
  chủ ý, vì database chứa 927 email nhân viên thật.
- **Không đụng tầng view và frontend.** Chưa có ô nào cần hiển thị ba cột này.
- **Không suy `provider` từ `raw_model`.** Provider đã tra được qua `dim_model`.
