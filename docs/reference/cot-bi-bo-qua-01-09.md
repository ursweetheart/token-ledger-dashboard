# Đọc nốt những cột sổ Gateway đang bị bỏ qua — nhật ký 01/09/2026

Ba cột trong `LiteLLM_SpendLogs` mà **không dòng mã nào của ta đọc tới**. Hai cột là trường
**bắt buộc** của sheet Data Out; cột thứ ba có thể làm sai số liệu một cách im lặng.

Change: `read-the-gateway-columns-we-still-ignore`. Nhật ký trước:
`do-tre-va-ket-cuc-luot-goi-31-08.md`.

---

## 1. Phát hiện mở đầu: một lệnh `grep` trả về rỗng

```
   grep -rn "cache_hit" db/ scripts/ backend/    ->  KHONG CO KET QUA NAO
```

Cột này tồn tại trong sổ từ đầu. Nó không được đọc, không được nhắc trong tài liệu, và tài
liệu kiến trúc còn xếp nó vào mục *"ba cột trông có ích nhưng KHÔNG dùng được"* với ghi chú
sai: *"nói về cache của LiteLLM, không phải cached token"*.

Nó **dùng được**, và bỏ qua nó thì token phồng.

---

## 2. Lỗi nguy hiểm nhất: hai cái bẫy NGƯỢC NHAU ở hai đầu

Bản đầu của thiết kế viết *"`cache_hit` có ba giá trị `NULL` / `False` / `True`, lọc bằng
`IS NOT TRUE`"*. **Sai ở vế nguồn.** Đo kiểu dữ liệu thật:

```
   information_schema:  cache_hit  data_type = text     <- KHONG phai boolean

   gia tri tho     do dai   so dong
   'True'               4         1
   'False'              5         5
   'None'               4        41   <- CHUOI 4 KY TU, khong phai SQL NULL
```

**Không có một dòng SQL NULL nào trong cột này.** Hậu quả ở vế nguồn:

```sql
   WHERE cache_hit IS NULL      -> 0 dong, du 41/47 dong "khong co thong tin"
   WHERE cache_hit IS NOT TRUE  -> LOI KIEU, khong chay noi
   WHERE NOT cache_hit          -> LOI KIEU, khong chay noi
```

Nhưng sau khi nạp, `fact_call.cache_hit` là `BOOLEAN` thật với NULL thật — và ở đó bẫy **đảo
chiều**:

```sql
   AND NOT cache_hit          -> NOT NULL ra UNKNOWN -> vut sach 38/41 dong
   AND cache_hit IS NOT TRUE  -> DUNG
```

Viết nhầm đầu nào cũng hỏng, và cả hai đều hỏng **im lặng ở mức số liệu**.

Bộ nạp dịch bằng `CASE` tường minh chứ **không** `::boolean`: gặp giá trị thứ tư thì ép kiểu
ném lỗi giữa chừng, còn `CASE` quy về NULL và một bộ đếm riêng sẽ kêu. Cùng cách đã làm với
`outcome` ở change trước.

---

## 3. Lỗ rò: chứng minh bằng phép thử âm ĐẢO NGƯỢC ĐƯỢC

Bản đầu của thiết kế viết *"quên bộ lọc thì rò đúng 352 token"*. **Không kiểm chứng được.**
Dòng trúng cache duy nhất trong sổ là do phép nghiệm thu cache tạo ra, và nó mang tag
`["User-Agent: Python-urllib", …]` — **không có tag agent**, nên `resolve_agent()` bỏ nó trước
khi nó kịp chạm `fact_call`.

Cách chứng minh **không** chọn: chế ra một dòng sổ mang tag `dms-feedback` bằng khoá quản trị.
Làm vậy là bịa ra lưu lượng mang tên một agent thật.

Cách đã chọn: đặt cờ trên **một dòng có sẵn**, đo, rồi khôi phục bằng **chính bộ nạp** — vì
`DO UPDATE` chép lại giá trị từ sổ gốc nên khôi phục là tự động và kiểm chứng được.

```
   dat cache_hit=true cho mot dong 6.866 token

   (DUNG)  AND cache_hit IS NOT TRUE : 38.321 token   loai dung dong do
   (sai a) khong co bo loc           : 45.187 token   RO  6.866 token
   (sai b) AND NOT cache_hit         :      0 token   MAT sach 38.321

   khoi phuc: cache_hit ve 38 NULL + 3 false, gateway ve 45.187
```

---

## 4. `api_key` trộn hai loại giá trị

```
   8112bdb7eca52b7f...        64 ky tu, bam SHA-256    khoa ao
   b3f2765d1d32ddc7...        64 ky tu, bam SHA-256    khoa ao
   litellm_proxy_master_key   CHUOI THUONG             khoa quan tri chung
```

**Quyết định: nạp nguyên văn, không chuẩn hoá.** Ép về một dạng là mất đúng cái phân biệt đang
cần.

Và con số phải theo dõi **không phải** con số của cả sổ:

```
   ca so       11/47 luot (23,4%) di bang khoa tong
   NAP DUOC     7/41 luot (17,1%),  84 token    <- con so that su lam ban du lieu
```

Bốn lượt kia không mang tag agent nên bị bỏ ngay ở tầng nạp. **7/41 mới là phần nằm lẫn trong
lưu lượng của agent**, và nó phải giảm về 0 khi 8 agent đều có khoá riêng.

**Cố ý KHÔNG đặt phép kiểm "không dòng nào dùng khoá tổng"**: hôm nay nó đỏ ngay với 7 dòng,
mà một phép kiểm luôn đỏ thì chẳng ai nhìn nữa.

---

## 5. `raw_model`: bí danh xuất hiện đúng ở dòng chết sớm

```
   gemini/gemini-3.5-flash-lite   42 dong   ten upstream
   gemini/gemini-3.6-flash         2 dong   ten upstream
   gemini-flash-lite               2 dong   BI DANH  -> model_id NULL
   gemini-flash                    1 dong   BI DANH  -> model_id NULL
```

Bí danh là `model_name` khai trong `config.gateway.yaml`; tên upstream là thứ Router điền vào
**sau khi đã chốt tuyến**. Nên dòng mang bí danh chính là dòng **hỏng trước khi Router chốt
tuyến**.

Và ở đây có một con số tôi viết sai rồi tự bắt được: sổ có **3** dòng bí danh, nhưng `fact_call`
chỉ có **2** — dòng `gemini-flash` không mang tag agent nên chưa từng được nạp.

---

## 6. Đã đụng vào những gì

| File | Việc |
|---|---|
| `db/migrations/**/007_*` | **Mới** — ba cột `raw_model`, `virtual_key_id`, `cache_hit` |
| `db/load_gateway.py` | Đọc thêm `api_key` và `cache_hit` · dịch bằng `CASE` · `DO UPDATE` sáu cột · ba bộ đếm mới |
| `db/build_usage_daily.py` | `load_gateway()` lọc `cache_hit IS NOT TRUE` |
| `scripts/audit_db.py` | Ba phép kiểm mới — 39 → **42** |
| `docs/reference/gateway-architecture-…md` | Mục 5: hai bẫy mới, `cache_hit` ra khỏi danh sách "không dùng được". Mục 7: bốn → **năm** quy tắc |

---

## 7. Nghiệm thu

```
   migration      8.672 dong · 50.113.744 token · 20 -> 23 cot · head 007_cot_bo_qua
                  ba cot moi NULL toan bo, 0 dong nguon app bi gan gia tri
   bo nap         doc 47 | dung duoc 41 | ghi de 41
                  di bang KHOA TONG 7/41 | trung cache 0 | mang bi danh 2
                  doi chieu: nguon 47/45.961 = dich 41/45.201 + bo qua 6/760
   bon nguon      KHONG doi mot token nao
   audit          42 phep kiem | 38 dat | 4 luu y | 0 hong
   doi soat moc   24/24 khoa KHOP, 0 lech
```

---

## 8. Còn chưa chắc, và một việc BỊ CHẶN

| | Mức |
|---|---|
| Ba cột nạp đúng, không hồi quy | **Chứng minh được** — 24/24 khoá mốc khớp |
| Bộ lọc `IS NOT TRUE` đúng, hai cách viết kia sai | **Chứng minh được** — phép thử âm ba chiều |
| `cache_hit = 'False'` nghĩa là lượt hỏng | **Chỉ tương quan** 5/5 mẫu — thiết kế cấm dựa vào, kết cục đã có cột `outcome` |
| **Cache có tách theo khoá ảo không** | **BỊ CHẶN** — xem dưới |

**Việc bị chặn.** Để biết cache có tách theo khoá ảo không, phải gọi cùng một câu bằng **hai
khoá khác nhau** và xem lượt thứ hai có trúng cache không. Việc này cần khoá ảo dạng thô của
DMS, mà đọc biến môi trường chứa khoá bị chặn — **và đó là chặn đúng**.

Vì sao nó quan trọng: nếu khoá cache **không** gồm khoá ảo, thì agent B hỏi trùng câu của agent
A sẽ nhận lại câu trả lời đã tính tiền cho A, và B ghi `spend = 0`. Đó không phải lỗi kỹ thuật
mà là **lỗi quy tiền**.

Chưa trả lời được câu này thì **chưa được bật cache thật**, dù change này đã làm cho việc bật
cache an toàn về mặt số token.


## 9. Bật cache và đo thật — 11/09/2026

Mục 8 ghi việc 6 là **BỊ CHẶN** vì không đọc được khoá ảo của DMS. Lý do đó sai, và sai ở hai
chỗ. Tag định danh đến từ `request_tags` chứ không từ khoá (`db/load_gateway.py:238`), mà tuyến
`gemini-flash-lite` vốn đã tự mang `tags: ["dms-feedback"]` — nên mọi lượt gọi vào tuyến đó đều
được đóng dấu, ai gọi cũng vậy. Còn khoá ảo mới thì xin được mà không đọc khoá nào: gọi
`/key/generate` từ bên trong container, để `$LITELLM_MASTER_KEY` giãn nở ở đó.

### 9.1 Cache KHÔNG tách theo khoá

Ba lượt, cùng một câu, `temperature: 0.0`.

| lượt | khoá | thời gian | `cache_hit` | `spend` | token vào/ra |
|---|---|---|---|---|---|
| 1 | A | 2,31 s | `None` | 1,26e-05 | 17 / 3 |
| 2 | A | 0,16 s | `True` | 0 | 17 / 3 |
| 3 | **B** | 0,05 s | `True` | 0 | 17 / 3 |

Lượt 3 dùng một khoá ảo **khác**, xin riêng, chưa từng hỏi câu đó. Nó nhận đúng câu trả lời của
khoá A: cùng `id` phản hồi, cùng `x-litellm-cache-key`. Truy vấn trên sổ xác nhận hai dòng trúng
cache mang **hai giá trị `api_key` khác nhau**.

Nên câu trả lời cho phép đo là: **cache dùng chung cho mọi khoá**. Câu trả lời của agent này
phục vụ được cho khoá của agent khác. Đây là số đo, không phải quyết định — bật hay không là
việc của người.

Cũng lưu ý: dòng trúng cache **vẫn ghi đủ token** y hệt dòng gốc, chỉ có `spend = 0`. Ba dòng
cộng lại là 60 token trong sổ, mà nhà cung cấp chỉ phục vụ 20.

### 9.2 Một dòng trúng cache làm ĐỨNG cả đường nạp

Đây là phần quan trọng hơn, và nó không nằm trong dự đoán của ô 7.3.

Bộ nạp loại dòng trúng cache ngay đầu đường (`db/load_gateway.py:311`, bẫy 7) vì `call_id` chứa
`_cache_hit`. Lý do chính đáng: dòng đó **lặp lại nguyên token** của dòng gốc, nạp cả hai là
đếm đôi. Đo lại hôm nay xác nhận đúng như vậy, 17 vào + 3 ra ở cả hai dòng.

Nhưng phép đối chiếu toàn sổ ở cuối hàm (`db/load_gateway.py:690`) cộng
`fact_call + bị bỏ qua` rồi so với sổ nguồn, mà câu truy vấn đếm "bị bỏ qua" (dòng 674) **chỉ
đếm dòng có số tag định danh khác 1**. Loại `bo_ban_sao_cache` không được đếm vào đâu cả.

| vế | dòng | token |
|---|---|---|
| sổ nguồn | 505 | 231.421 |
| `fact_call` | 421 | 229.697 |
| bị bỏ qua (đếm được) | 82 | 1.684 |
| **thiếu** | **2** | **40** |

Bộ nạp báo `MISMATCH`, thoát mã 1, kèm câu *"DUNG LAI - khong tong hop tren du lieu thieu"*.
`fact_usage_daily` vì thế không được tổng hợp. Nghĩa là **chỉ cần một dòng trúng cache trong sổ
là cả đường nạp đứng, và đứng mãi** — không phải chỉ lệch một con số.

### 9.2b Đã sửa, cùng ngày

Sửa ở `db/load_gateway.py`: vế "bị bỏ qua" của phép đối chiếu nay đếm cả bản sao cache. Hậu tố
`_cache_hit` đặt thành hằng `HAU_TO_CACHE`, dùng chung cho chỗ bỏ dòng và chỗ đếm dòng đã bỏ —
hai chỗ lệch nhau là bộ nạp dừng, nên không để mỗi chỗ viết một bản. Câu SQL dùng `strpos` chứ
không dùng `LIKE '%_cache_hit%'`: trong LIKE thì `_` là ký tự đại diện khớp một ký tự bất kỳ,
nên mẫu đó còn khớp cả `Xcache_hit`.

| | trước khi sửa | sau khi sửa |
|---|---|---|
| bỏ qua toàn sổ | 82 dòng / 1.684 token | **84 dòng / 1.724 token** |
| riêng bản sao cache | không được đếm | **3 dòng / 392 token** |
| mã thoát | 1, `MISMATCH` | **0, `acceptance passed`** |
| `fact_usage_daily` | không tổng hợp | 1.998 → **1.999** dòng |

Ba dòng bản sao cache gồm 2 dòng của phép đo này (40 token) và 1 dòng có sẵn từ 01/09
(352 token). Dòng cũ trước đây vẫn được đếm, nhưng nhờ nó KHÔNG có tag định danh — tức đúng số
vì một lý do chẳng liên quan, đúng loại may mắn mà bẫy 7 đã cảnh báo.

`scripts/audit_db.py` chạy lại sau khi sửa: **78 phép kiểm · 68 đạt · 10 lưu ý · 0 hỏng**.

Nhờ vậy **không phải xoá dòng nào trong sổ gốc**. Hai dòng thử cứ để nguyên; sổ gốc là bằng
chứng, và nay bộ nạp đếm được chúng.

### 9.3 Mã đúng, `design.md` sai

`design.md` mục ③ của change `read-the-gateway-columns-we-still-ignore` viết *"fact_call GIU
luot trung cache"* và *"Không lọc ở tầng nạp"*. Mã đang làm ngược lại, và **phép đo cho thấy mã
đúng**: giữ dòng trúng cache trong `fact_call` là đếm đôi token thật, đúng lỗi mà bẫy 7 dựng ra
để chặn. Phải sửa design trước khi archive change đó, cùng hạng việc với lần sửa spec 10/09.

### 9.4 Còn lại gì

Hai việc nêu ra lúc đầu đều đã xong: phép đối chiếu nay đếm bản sao cache, và vì thế không phải
động vào sổ gốc.

Còn hai chuyện **chưa làm, và cố ý không làm ở đây**:

1. **Khối cache soạn sẵn trỏ thẳng `host: redis`**, trong khi phần còn lại của cấu hình đã đi
   qua Sentinel. Khối đó viết trước change Sentinel. Ai bật cache thật phải đổi sang dạng
   Sentinel, không thì mất master là cache trỏ vào chỗ chết.
2. **Có bật cache hay không.** Phép đo chỉ nói cache dùng chung mọi khoá và dòng trúng cache
   lặp token. Quyết định là của người, không phải của change này.

Cấu hình đã trả về nguyên trạng: cache tắt, `diff` với bản sao lưu rỗng, hai instance khởi động
lại và không còn dòng `Setting Cache on Proxy`.
