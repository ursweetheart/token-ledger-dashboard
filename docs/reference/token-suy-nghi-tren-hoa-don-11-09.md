# Token suy nghĩ nằm ở đâu trên hoá đơn Google — nhật ký đo 11/09/2026

Câu hỏi mở từ 22/07, ô 2.1 của change `standardize-kpi-card-insights`: **hoá đơn của Google
có tách token suy nghĩ ra khỏi token ra không?** Nếu có, và dashboard không cộng phần đó, thì
tổng token đang thiếu — đúng hạng lỗi cache ngày 15/08 làm rơi 26% token mà không ai thấy.

Change: `settle-what-the-bill-does-with-thinking-tokens`. Nhật ký trước:
`ep-429-va-mat-gateway-10-09.md` mục 2.7 (nửa Gateway), `dua-crm-qua-gateway-10-09.md`.

---

## 1. Kết quả một dòng

**Hoá đơn KHÔNG tách. Token suy nghĩ nằm trong SKU output, và dashboard đã cộng nó rồi.**
Không thiếu token. Không phải sửa công thức `ti + to + cached`.

Và **hai** cái bẫy tìm được trên đường đo, cả hai nguy hiểm hơn câu hỏi gốc:

1. Cột `thinking_tokens` mà dashboard đang có **không phải** token suy nghĩ. Cộng nó vào output
   là đếm hai lần 91% token ra. Xem mục 6.
2. `fact_usage_daily` trộn **ngày US/Pacific** của hoá đơn với **ngày Việt Nam** của ba nguồn
   còn lại vào cùng một cột `day`. Mọi biểu đồ theo ngày có tiền hoá đơn đều lệch một ngày.
   Xem mục 11.

---

## 2. Hoá đơn không có SKU nào cho token suy nghĩ

`dim_metric_alias` khai 31 SKU hoá đơn. Cả 31 đều có dòng thật trong `fact_billing_daily`,
không SKU nào đã khai mà chưa bao giờ về.

```
   billing_sku   input   15
   billing_sku   output   9
   billing_sku   cached   7
```

Trong 9 SKU output, **đúng 2 SKU** mang chữ `non-thinking` trong tên:

```
   6EDB-2409-6348   output   ... gemini 2.5 flash short output text non-thinking
   7133-23F2-04B7   output   ... gemini 2.5 flash lite short output text non-thinking
```

Và **0 SKU** mang chữ `thinking` trơn. Cũng **0 SKU** nào nhắc tới suy nghĩ mà `kind` khác
`output`.

Đây là lập luận mạnh nhất của cả nhật ký này: hoá đơn phủ **240 ngày**. Nếu Google tính tiền
phần suy nghĩ thành một dòng riêng thì sau 240 ngày phải thấy một SKU riêng. Không có.
Nghĩa là phần suy nghĩ được tính **bên trong** SKU output.

---

## 3. Hai SKU output của `gemini 2.5 flash` chính là hai nhãn bật và tắt suy nghĩ

Tên SKU của Google đặt không nhất quán nên đọc tên không đủ. SKU `911A-8880-A243` có
`kind = output` nhưng tên lại là *"output token count gemini 2.5 flash short **input** text"*.
Nên phải đo, không đoán.

Phép đo: lấy những cặp ngày × project mà Cloud Monitoring **không có lượt nào** bật suy nghĩ,
rồi xem SKU `911A` bằng bao nhiêu.

| phép kiểm | số cặp ngày × project |
|---|---|
| monitoring tắt suy nghĩ hết, tức `mon_bat = 0` | 56 |
| trong đó `911A = 0` | **56** |
| tổng token của `911A` trong 56 cặp đó | **0** |

56 trên 56, và tổng đúng bằng 0. Chiều ngược lại kém sạch hơn nhưng cùng hướng: 173 cặp
monitoring bật suy nghĩ hết, 161 cặp có `6EDB = 0`, 12 cặp còn lại tổng 119.145 token — hạng
sai số của lệch ngày, xem mục 7.

**Kết luận mapping:**

```
   911A-8880-A243   =  token RA cua luot BAT suy nghi
   6EDB-2409-6348   =  token RA cua luot TAT suy nghi   (ten co san chu non-thinking)
```

---

## 4. Đơn giá khớp đúng giá output, không có giá thứ hai

```sql
SELECT sku_id, sum(quantity), sum(cost_usd),
       round((sum(cost_usd)/sum(quantity)*1000000)::numeric, 6) AS usd_tren_1M
  FROM fact_billing_daily GROUP BY 1;
```

| SKU | loại | token | USD | USD / 1 triệu |
|---|---|---|---|---|
| `981A-C057-0BF9` | input | 184.284.509 | 55,2828 | 0,299986 |
| `5CDC-4C82-2AEC` | cached | 88.851.479 | 2,6652 | 0,029996 |
| `911A-8880-A243` | output bật suy nghĩ | 48.159.944 | 120,3987 | **2,499976** |
| `6EDB-2409-6348` | output tắt suy nghĩ | 4.789.764 | 11,9742 | **2,499946** |

Hai SKU output **cùng một giá**: 2,50 đô trên 1 triệu token. Nên `non-thinking` ở đây không
phải một bậc giá rẻ hơn, chỉ là một ngăn ghi sổ.

Và 2,50 đô đúng bằng con số LiteLLM dùng hôm 10/09 khi tính tiền phần suy nghĩ theo giá
token ra: `6/1e6 × 0,30 + 23/1e6 × 2,50 = 0,00005930`, sổ ghi `0,00005930`, khớp tới 8 chữ số
thập phân. Hai nguồn độc lập, cùng một bảng giá.

---

## 5. Cả hai SKU đều đã nằm trong tổng của dashboard

Hai SKU cùng `kind = 'output'`. Đường hoá đơn cộng theo `kind`, không cộng theo `sku_id`. Nên
token ra của lượt bật suy nghĩ **đã vào** `to`, và đã vào tổng `ti + to + cached`.

Không thiếu. Không phải sửa công thức.

---

## 6. Cái bẫy thật: `thinking_tokens` KHÔNG phải token suy nghĩ

`backend/store.py:469` tính:

```sql
SUM(CASE WHEN m.thinking_enabled = 'true' THEN m.value ELSE 0 END) AS thinking_tokens
```

`thinking_enabled` là một **nhãn trên metric**, không phải một metric riêng. Nên phép cộng này
trả về *token ra của những lượt có bật suy nghĩ*, chứ **không** phải *số token đã dùng để suy
nghĩ*. Tên cột nói một chuyện, số nói chuyện khác.

Đo bao nhiêu:

| đo trên monitoring | token |
|---|---|
| `thinking_tokens` như code đang tính | 47.913.327 |
| tổng token ra của monitoring | 52.560.360 |
| tỷ lệ | **91,2%** |

Cộng cột này vào output là đếm hai lần 91% token ra.

**Một nghi ngờ đã kiểm và LOẠI.** Điều kiện `d.measures = 'token'` phủ cả metric input lẫn
output, nên thoạt đọc thì `thinking_tokens` có vẻ trộn cả input vào. Đo lại thì **không**: các
metric input **không mang nhãn** `thinking_enabled` bao giờ, giá trị là NULL, nên nhánh
`CASE WHEN ... = 'true'` cho ra 0 trên mọi dòng input. Thực tế cột này chỉ ăn metric output.

```
   kind     bat_suy_nghi   tat_ca
   input    (NULL)         444.373.433     <- khong dong nao co nhan
   output   47.913.327      52.560.360
```

Monitoring cũng chỉ có **đúng một** metric token ra,
`generativelanguage.googleapis.com/generate_content_usage_output_token_count`. Nên ở tầng
monitoring cũng không có ngăn thứ ba.

---

## 7. Số token suy nghĩ THẬT: chỉ sổ Gateway có, và nó là tập con

LiteLLM ghi `completion_tokens_details.reasoning_tokens` trong `metadata` của
`LiteLLM_SpendLogs`. `db/load_gateway.py:201` chỉ đọc nó để suy ra **cờ** `thinking_enabled`
kiểu boolean. **Con số thì không được lưu thành cột nào.**

| sổ Gateway | giá trị |
|---|---|
| tổng số dòng | 505 |
| dòng có `reasoning_tokens` | 46 |
| tổng `reasoning_tokens` của 46 dòng | 9.554 |
| tổng `completion_tokens` của 46 dòng | 9.968 |
| dòng có `reasoning > completion` | **0** |

95,8% token ra là suy nghĩ, và **không dòng nào** vượt quá `completion_tokens`. Tập con, không
phải ngăn riêng. Đây là bằng chứng trực tiếp nhất cho câu "suy nghĩ nằm trong output".

Muốn hiển thị token suy nghĩ trên dashboard thì đây là nguồn duy nhất đúng, và phải hiển thị
kiểu **chia phần của token ra**, không bao giờ cộng thêm. Cần một cột mới trong `fact_call`.

---

## 8. Bộ nạp hoá đơn dừng hẳn khi gặp SKU lạ — đọc code, không tin ghi chú

Ô task ghi rõ *"đừng tin ghi chú này"*, nên đã đọc `db/load_billing.py:85-112`. Đúng như ghi
chú: SKU không tra ra `kind` thì vào `no_kind` rồi `continue`, và cuối vòng lặp
`if no_model or no_kind or no_agent: raise SystemExit(...)`. Không có nhánh nào nạp tiếp trong
im lặng.

Nghĩa là một SKU suy nghĩ mới xuất hiện trên hoá đơn sẽ **làm bộ nạp chết**, không lặng lẽ rơi.
Kết luận ở mục 2 vì thế còn đứng được trong tương lai, không chỉ đúng với 240 ngày đã có.

---

## 9. Phần lệch 122% — GIỮ NGUYÊN LÀM VẾT, ĐÃ BỊ MỤC 11 BÁC BỎ

> **Đọc mục 11 trước khi tin mục này.** Toàn bộ phần lệch mô tả dưới đây **không tồn tại**. Nó
> là ảo ảnh của việc so ngày giờ Việt Nam với ngày giờ US/Pacific. Khớp đúng múi giờ thì cả
> bảy project đều ra **100,00%**. Giữ lại nguyên văn vì cách tôi suýt kết luận sai ở đây là
> phần đáng học nhất của nhật ký.

Phép so tổng giữa monitoring và hoá đơn trên khoảng 25/04 đến 28/08:

| nhánh | monitoring | hoá đơn | hoá đơn / monitoring |
|---|---|---|---|
| tắt suy nghĩ | 4.522.851 | 4.503.631 | **99,6%** |
| bật suy nghĩ | 29.961.623 | 36.594.384 | **122,1%** |

Thoạt trông thì 122% giống như "hoá đơn đếm thêm phần suy nghĩ mà monitoring không đếm". Tách
theo project thì **lập luận đó sụp**:

| project | bật suy nghĩ, hoá đơn / monitoring |
|---|---|
| `tranquil-post-471401-c1` | 150,8% |
| `ai-chatbot-contract` | 121,0% |
| `multimodal-invoice` | 100,0% |
| `pro-tuner-454203-v3` | 91,9% |
| `feedback-dms-tiep-thi` | 77,2% |
| `crm-500509` | 68,5% |
| `tools-quizz` | 62,1% |

Lệch **hai chiều**, từ 62% tới 151%. Còn nhánh tắt suy nghĩ trên cùng những ngày đó thì ngồi
yên ở 99,1% và 100,4%. Tách theo model cũng vậy: `gemini-2.5-flash` 119,2% nhưng
`gemini-3-flash` — model luôn bật suy nghĩ — chỉ 101,0%.

Nếu 22% là phần suy nghĩ thì `gemini-3-flash` phải lệch tương tự. Nó không. Nên **22% không
phải phần suy nghĩ**, mà là monitoring phủ thiếu theo project. Ghi lại thành việc riêng, không
gộp vào câu hỏi này.

**Vì sao chuyện đó không làm lung lay kết luận mục 1.** Bốn bằng chứng ở mục 2, 4, 7 và 8 không
dùng tới phép so này: không có SKU suy nghĩ sau 240 ngày, đơn giá bằng đúng giá output, sổ
Gateway cho thấy `reasoning ⊂ completion` với 0 trên 46 dòng vượt, và bộ nạp sẽ chết nếu SKU lạ
xuất hiện. Phép so monitoring chỉ đóng vai phụ, và điều nó nói được là: trên nhánh bật suy
nghĩ, hoá đơn **không bao giờ thấp hơn** monitoring một cách hệ thống. Thiếu token thì phải
thấy chiều ngược lại.

**Điều thành thật là chưa có:** một phép đo trực tiếp cho thấy `quantity` của SKU output **bằng
số** với `token ra + token suy nghĩ` của cùng những lượt gọi đó. Monitoring phủ thiếu nên chưa
làm được từ hai nguồn này. Làm được khi sổ Gateway và hoá đơn có ngày chồng nhau — hiện chưa có,
sổ Gateway bắt đầu từ tháng 9 còn hoá đơn dừng ở 29/08.

---

## 10. Hệ quả, viết thành lệnh

1. **KHÔNG cộng `thinking_tokens` vào output.** Đếm hai lần 91% token ra.
2. **KHÔNG sửa công thức `ti + to + cached`.** Nó đã đúng, cả đường hoá đơn lẫn đường Gateway.
3. Muốn hiện token suy nghĩ thì lấy `reasoning_tokens` từ sổ Gateway, thêm cột vào `fact_call`,
   và trình bày kiểu **trong đó**, không phải **cộng thêm**.
4. Cột `thinking_tokens` nên đổi tên, vì tên hiện tại mô tả sai thứ nó đo. Tên đúng là đại ý
   *token ra của lượt có bật suy nghĩ*.
5. ~~Việc riêng cần mở: monitoring phủ thiếu theo project, lệch 62% tới 151% so với hoá đơn.~~
   **Sai, xem mục 11.** Monitoring không phủ thiếu. Việc thật phải mở là: `fact_usage_daily`
   đang trộn ngày Pacific của hoá đơn với ngày Việt Nam của monitoring vào cùng một cột `day`.

---

## 11. Phần lệch 122% không tồn tại — nó là lệch múi giờ, đo 11/09

Mục 9 kết luận "monitoring phủ thiếu theo project, lệch 62% tới 151%". **Sai.** Không có phần
lệch nào. Cả hai nguồn đếm **đúng một thứ**, chỉ dán nhãn ngày theo hai múi giờ khác nhau.

### 11.1 Dấu hiệu đầu: dịch một ngày thì sai số rơi ba lần

Thay vì ghép `ngày = ngày`, thử ghép `ngày hoá đơn = ngày monitoring + d` với `d` chạy từ −2
tới 2, rồi đo tổng sai số tuyệt đối ở mức ngày:

| `d` | sai số / tổng monitoring |
|---|---|
| −2 | 126,2% |
| **−1** | **31,7%** |
| 0 | 96,2% |
| 1 | 126,8% |
| 2 | 123,8% |

Một cực tiểu rõ rệt ở `d = −1`. Ngày của hoá đơn **lùi một ngày** so với ngày của monitoring.

### 11.2 Nguyên nhân: hoá đơn theo giờ US/Pacific, monitoring theo giờ Việt Nam

`scripts/merge_billing.py:251` lấy `"day": r["Date"]` **nguyên văn** từ file xuất của Cloud
Billing, không đổi múi giờ ở đâu cả. Cloud Billing xuất theo US/Pacific. Còn
`db/build_usage_daily.load_monitoring()` ghi thẳng trong docstring *"Ngày giờ Việt Nam thật"*.

Tháng 4 tới tháng 8 là PDT, tức UTC−7, còn Việt Nam là UTC+7. Lệch 14 giờ. Nên **Pacific 00:00
= Việt Nam 14:00**.

### 11.3 Phép kiểm quyết định: xếp lại monitoring theo ngày Pacific

```sql
CASE WHEN extract(hour FROM ts_local) >= 14
     THEN ts_local::date ELSE ts_local::date - 1 END AS pacific_day
```

Xếp lại rồi ghép `pacific_day = pacific_day`, không dịch gì nữa:

| project | ngày | ngày trùng khít từng con số | tổng hoá đơn / monitoring |
|---|---|---|---|
| `tranquil-post-471401-c1` | 120 | 109 | **100,00%** |
| `pro-tuner-454203-v3` | 55 | 53 | **100,00%** |
| `crm-500509` | 40 | **40** | **100,00%** |
| `feedback-dms-tiep-thi` | 18 | 17 | 100,06% |
| `ai-chatbot-contract` | 10 | **10** | **100,00%** |
| `tools-quizz` | 5 | **5** | **100,00%** |
| `multimodal-invoice` | 4 | **4** | **100,00%** |

**238 trên 272 cặp ngày × project trùng khít tới từng con số**, và **cả bảy project đều ra
100,00%**. Không còn 62%, không còn 151%.

### 11.4 Vì sao project của pipeline khớp tuyệt đối mà project web thì không

`crm-500509` khớp **40/40**, `ai-chatbot-contract` **10/10**, còn `tranquil-post` chỉ 109/120 dù
tổng vẫn 100,00%. Đây không phải sai số, mà là hệ quả tự nhiên của biên ngày:

```
   Pacific day D  =  VN 14:00 ngay D  ->  VN 13:59 ngay D+1
```

CRM là pipeline chạy theo lịch, lưu lượng dồn vào một khung giờ hẹp nên nằm gọn trong **một**
ngày Pacific. `tranquil-post` là web service có lưu lượng rải cả ngày, nên nó **bị biên
14:00 cắt đôi**: phần trước 14:00 rơi vào ngày Pacific trước. Ngày lẻ vì thế xê dịch, còn tổng
thì không mất gì.

### 11.5 Hệ quả thật, và nó lớn hơn con số 122%

Con số 122% chỉ nằm trong câu SQL tôi tự viết, **không** hiện ở đâu trên dashboard. Nhưng cùng
một chỗ hỏng đó **có** nằm trong bảng của dashboard:

```
   fact_usage_daily.day
     <- load_billing()      ngay US/Pacific   (lay nguyen tu file hoa don)
     <- load_monitoring()   ngay Viet Nam     (docstring noi ro)
     <- load_app()          ngay Viet Nam
     <- load_gateway()      ngay Viet Nam
```

Bốn bộ nạp, bốn dòng cùng vào một cột `day`, mà **một trong bốn dùng múi giờ khác**. Nên mọi
biểu đồ theo ngày có trộn tiền hoá đơn với token của ba nguồn kia đều bị **lệch một ngày** ở vế
hoá đơn. Tổng cả kỳ thì đúng, ngày lẻ thì sai — đúng hạng lỗi khó thấy nhất.

**Phải xử lý đúng múi giờ, không phải bù một hằng số.** Lệch là 14 giờ trong PDT nhưng **15
giờ** trong PST, tức tháng 11 tới tháng 3 biên rơi vào VN 15:00. Bù cứng `−1 ngày` hay `−14
giờ` sẽ sai trong bốn tháng mỗi năm. Phải quy bằng `America/Los_Angeles`.

### 11.6 Điều này còn siết thêm kết luận về token suy nghĩ

Mục 9 cũ phải để ngỏ câu *"chưa có phép đo trực tiếp cho thấy `quantity` của SKU output bằng số
với token ra của cùng những lượt gọi đó"*. Nay **có**: 238 cặp ngày × project trùng khít **tới
từng con số**, và bảy project đều 100,00%.

Nghĩa là `quantity` của SKU output trên hoá đơn và công tơ monitoring là **cùng một cái công
tơ**. Ghép với mục 7 — sổ Gateway cho `reasoning ⊂ completion`, 0 trên 46 dòng vượt — thì phần
suy nghĩ nằm trong token ra trên **cả ba** đường: hoá đơn, monitoring, và Gateway.
