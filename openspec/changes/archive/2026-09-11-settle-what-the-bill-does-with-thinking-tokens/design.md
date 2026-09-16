# Đối chiếu token suy nghĩ với hoá đơn

## ① Phép ghép hiển nhiên KHÔNG chạy — đã thử ngày 11/09

Đây là phần quan trọng nhất của tài liệu này, vì nó chặn người sau đi lại đúng con đường đó.

Bước đầu trông rất thuyết phục:

| nguồn | token |
|---|---|
| `fact_monitoring`, các dòng `thinking_enabled = true` | 47.913.327 |
| hoá đơn, SKU output của 2.5 flash **không** mang chữ `non-thinking` | 48.159.944 |

Lệch 0,5%. Nhìn là muốn kết luận ngay: SKU kia chính là phần suy nghĩ.

**Ghép theo từng ngày thì sập.**

| phép ghép theo ngày, riêng `gemini-2.5-flash` | kết quả |
|---|---|
| số ngày chung | 128 |
| ngày trùng khít | **0** |
| ngày lệch dưới 2% | 7 |
| tổng bên giám sát | 43.873.227 |
| tổng bên hoá đơn | 42.406.135 |

Hai con số tổng gần nhau chỉ vì **cùng quy mô**, không vì cùng một thứ. Đây đúng hạng bẫy đã làm rút lại ba kết luận trong hai ngày 10 và 11/09: một con số tổng hợp trông như bằng chứng.

**Hệ quả cho thiết kế:** không được đóng ô này bằng một câu truy vấn gộp. Phải ghép ở mức chi tiết hơn, và phải giải thích được phần lệch.

## ② Ba giả thuyết, và chỉ một trong ba là nguy hiểm

```
   H1  Hoá đơn KHÔNG tách:  token suy nghĩ nằm chung SKU output
       -> dashboard không thiếu gì, đóng ô 2.1, không phải sửa gì

   H2  Hoá đơn CÓ tách:     suy nghĩ là một SKU output RIÊNG
       -> van la kind='output', dashboard van cong du, dong o 2.1

   H3  Hoá đơn có tách NHƯNG SKU đó bị xếp sai kind, hoặc chưa từng về
       -> dashboard đang THIẾU. Chỉ trường hợp này mới phải báo động
```

Điểm mấu chốt: **H1 và H2 đều dẫn tới "không thiếu"**, vì `fact_billing_daily.kind` chỉ có ba giá trị và cả hai loại SKU output đều vào `output`.

Nên câu hỏi thật không phải *"hoá đơn có tách không"* mà là *"có SKU nào đang bị xếp sai chỗ, hoặc đáng lẽ phải về mà chưa về không"*.

## ③ Một lớp bảo vệ đã có sẵn, và nó hạ hẳn mức rủi ro

`db/load_billing.py:106` **dừng hẳn** khi gặp một `sku_id` chưa có trong `dim_metric_alias`. Nó không bỏ qua, không đoán, không gán mặc định.

```
   SKU lạ xuất hiện  ->  bộ nạp DỪNG  ->  có người phải ánh xạ nó
```

Nghĩa là vế "chưa từng về" của H3 **không thể xảy ra một cách im lặng**. Một SKU suy nghĩ mới sẽ làm đứng đường nạp hoá đơn, y như cách một dòng trúng cache làm đứng đường nạp Gateway (phát hiện 11/09).

Nhưng điều này **không đóng được ô 2.1**: vẫn còn vế kia của H3, là SKU đã về từ lâu, đã được ánh xạ, và đang bị xếp nhầm `kind`. Lớp bảo vệ trên không bắt được chuyện đó.

Nên việc đầu tiên là soát bảng ánh xạ, chứ không phải chạy phép ghép.

## ④ Thứ tự làm, rẻ trước đắt sau

```
   1. Soát dim_metric_alias: mọi SKU output đã ánh xạ, cái nào có/không có
      chữ non-thinking, và cái nào rơi vào kind khác 'output'
      -> thấy một SKU suy nghĩ bị xếp sai kind thì XONG LUÔN, khỏi ghép

   2. Chỉ khi bước 1 sạch mới ghép số, và ghép theo
      ngày x agent x project x model, không chỉ theo ngày

   3. Giải thích phần lệch còn lại, hoặc nói rõ là không giải thích được
```

Bước 1 là một câu truy vấn, không tốn gì. Bước 2 mới là việc thật.

## ⑤ Cái bẫy về ý nghĩa con số giám sát

`fact_monitoring.value` với `metric_nickname = generate_content_usage_output_token_count` là số do Cloud Monitoring báo. Ghi nhớ `gcp-monitoring-recon-context` nói cửa sổ lưu giữ của nó trượt nhanh, và token của nó từng khớp hoá đơn **100,4%** khi so đúng khoảng ngày.

Con số 100,4% đó là bằng chứng quan trọng: hai nguồn ĐÃ từng khớp gần như tuyệt đối. Nếu phép ghép mới cho ra lệch lớn thì nghi ngờ đầu tiên phải là **cách ghép sai**, không phải dữ liệu sai. Soát lại phép ghép trước khi kết luận về dữ liệu.

## ⑥ Điều KHÔNG làm trong change này

Không đổi công thức của dashboard. Change này chỉ trả lời câu hỏi. Nếu câu trả lời là "đang thiếu" thì việc sửa là của change sau, và lúc đó phải bàn cả chuyện nói cho người xem biết con số đã đổi — vì một con số tổng tự nhiên nhảy lên mà không ai giải thích cũng là một kiểu nói dối.
