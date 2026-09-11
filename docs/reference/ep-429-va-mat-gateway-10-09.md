# Ép 429 và diễn tập mất Gateway — nhật ký đo 10/09/2026

Nhật ký của change `prove-the-crm-path-survives-refusal-and-outage`. Nguyên tắc: **mỗi kết luận
kèm số**. "Đã thử rồi" không phải kết quả.

Mục 2 và mục 3 của tài liệu này tách rõ **điều chứng minh được** khỏi **điều suy luận**. Trộn hai
loại làm người đọc tin nhầm mức độ chắc chắn.

---

## 1. Kết quả một dòng

Nhánh xử lý 429 của CRM **chạy đúng**, và đường CRM **sống sót** khi mất Gateway giữa chừng: không
mất dòng, không đếm đôi. Nhưng cả hai phép đo đều lộ ra thứ không ai đi tìm, và những thứ đó đắt
hơn câu hỏi ban đầu.

| | |
|---|---|
| tổng lượt gọi dùng cho cả change | **32** |
| trần đã chốt ở ô 0.2 | ~50 |
| tiền | **$0,216** |
| lượt đắt nhất | lô 25 dòng, `$0,0257` |
| phát hiện đắt nhất | token suy nghĩ ăn 96% ngân sách đầu ra |

---

## 2. Điều CHỨNG MINH ĐƯỢC — kèm số

### 2.1 Gateway không che 429, nhưng hoãn nó 123,7 giây

`num_retries: 3` khiến Gateway tự thử lại ba lần trước khi chịu trả `429` cho người gọi.

```
   06:42:21  Router: RateLimitError, rpm_limit=1, current_rpm=1.0
   06:43:35  Router: RateLimitError                                   (+74s)
   06:44:35  LiteLLM Retried: 3 times  ->  POST /v1/chat/completions 429   (+60s)
```

Đo từ phía người gọi trên ba lượt liên tiếp: `124` · `123,8` · `123,6` giây. **Lấy con số của người
gọi, không lấy khoảng cách giữa hai dòng log** — con số log (`~60`s) chỉ là một phần cửa sổ.

### 2.2 `rpm: 1` không phải "một lượt mỗi phút" mà là "không lượt nào"

Bộ đếm đọc được `current_rpm: 1.0` ở **cả bảy phút liên tiếp**, từ `06:40` tới `06:46`, không một
lần về 0. Nên mục 2 đo cảnh **tuyến chết hẳn**, không phải cảnh chạm trần thoáng qua. Hệ quả: kết
quả mục 2 là **trường hợp xấu nhất**, không phải trường hợp thường gặp.

### 2.3 Một lô hỏng vì 429 tốn 7 phút 14 giây

```
   3 x 123,7 giay cho Gateway   +   (10,2 + 20,4 + 31,4) giay CRM tu ngu   =   433,99 giay
   ──────────────────────────       ──────────────────────────────────────
   371s  (86%)                      62s  (14%)
```

**86% thời gian là Gateway**, chỉ 14% là phần lùi lịch của CRM mà change này lập ra để đo.

### 2.4 Cách phân loại nhánh mà chính ô task đề ra đã BỊ BÁC BỎ

| đếm cái gì | nhánh 429 | nhánh chung | phân biệt được? |
|---|---|---|---|
| số lượt gọi | 3 | 3 | không |
| **số khoảng giữa hai lượt gọi** | **2** | **2** | **không** |
| số lần ngủ | 3 | 2 | có, nhưng phải đọc log CRM |
| **câu lỗi cuối** | `due to exhausted retries` | `after 3 retries` | **có, không cần log** |

Cả hai nhánh cho **đúng 2 khoảng**, vì vòng lặp chỉ có 3 lượt gọi. Nhánh 429 ngủ lần thứ ba mà không
có lượt gọi nào đi sau, nên lần ngủ đó **không sinh ra khoảng nào đo được**.

Độ dài khoảng cũng vô dụng: đo ra `134,21`s và `144,14`s, không giống `10, 20, 30` mà ô task dự
đoán, cũng không giống `13,5 / 20 / 30` mà phép mô phỏng cho ra — cả hai lần đều bỏ sót `~124` giây
của Gateway.

**Câu lỗi là mốc duy nhất còn đứng được**, và nó chứng tỏ giá trị **hai lần**: mục 2 nhận ra nhánh
429, mục 3 nhận ra nhánh chung, trong khi cả hai cảnh đều cho 2 khoảng.

### 2.5 Nhánh 429 ngủ 30 giây cho một lần thử lại không bao giờ xảy ra

`src/llm.py:283-291`. Nhánh chung có chốt `if attempt < max_retry` nên lượt 3 ném lỗi ngay. Nhánh
429 **không có chốt đó**: lượt 3 vẫn ngủ `31,4` giây rồi `continue`, `range` hết, rơi xuống `raise`.
Đo được chứ không suy: CRM tự in `Sleeping 31.4s` mà sau đó không có lượt gọi nào.

### 2.6 Mất Gateway: không mất dòng, không đếm đôi

Diễn tập 20 dòng, 5 lô. Dừng `gateway-lb` ngay sau khi lô 2 ghi sổ, bằng vòng chờ bám vào nhật ký
chứ không đếm giờ áng chừng.

| | |
|---|---|
| lỗi CRM nhận được | `ConnectError: [Errno -5] No address associated with hostname` |
| thời gian tới lúc bỏ mỗi lô hỏng | `21,48` · `24,10` · `24,05` giây |
| câu lỗi cuối | `Failed calling Gemini API after 3 retries` → **nhánh chung** |
| dòng vào sổ trước sự cố | 8 |
| **không mất dòng** | mong đợi 20, trong sổ 20, thiếu `0`, thừa `0` |
| **không đếm đôi** | `0` dòng được ghi sổ hai lần |
| sổ Gateway, chênh khi chạy lại | **+3 lượt**, đúng số lô còn thiếu; chạy lại mù sẽ là +5 |

Hai điều đó **đo tách nhau**, không gộp. Trong phép "không đếm đôi" còn tách thêm một tầng: phép
kiểm "mỗi ActivityId có đúng một bản ghi" **không chứng minh gì**, vì sổ là `dict` nên điều đó đúng
bằng cấu trúc. Phép kiểm có giá trị là đếm số lần mỗi dòng được **ghi sổ** qua cả hai lần chạy.

Lỗi CRM nhận được là **lỗi phân giải tên**, không phải từ chối kết nối, vì Docker gỡ luôn bản ghi
DNS khi container dừng. **Kiểu dừng quyết định thông báo lỗi** — đừng đọc thành "mọi kiểu mất Gateway
đều cho lỗi DNS".

### 2.7 Token suy nghĩ nằm trong output, và bị tính tiền theo giá output

| cách gọi | vào | ra | suy nghĩ | chữ |
|---|---|---|---|---|
| mặc định | 19 | 296 | 285 | 11 |
| `reasoning_effort: "disable"` | 19 | **107** | **không có** | 107 |
| `thinking: {"type":"disabled"}` | 19 | 296 | 285 | 11 |

Cột **vào đứng yên ở 19 cả ba lượt**. Số học tiền khớp tới 8 chữ số thập phân, 2/2 dòng:
`6/1e6 × 0,30 + 23/1e6 × 2,50 = 0,00005930`, sổ ghi `0,00005930`.

Dòng thứ ba là bẫy phải nhớ: `drop_params: true` **bỏ im lặng** tham số nó không nhận, nên số token
y hệt lúc không khai gì.

### 2.8 Lô cỡ production bị cắt cụt trong im lặng

| cấu hình | token ra | gửi → nhận |
|---|---|---|
| suy nghĩ BẬT, trần `8192` | 8.178 (7.860 suy nghĩ) | 5 → **1** |
| suy nghĩ TẮT, trần `8192` | 8.177 | 25 → **20** |
| suy nghĩ TẮT, trần `12000` | 11.020 | 25 → **25** |
| suy nghĩ TẮT, trần `16000` | 10.534 | 25 → **25** |

`~440` token ra cho mỗi bản ghi. `8.192 / 440 ≈ 18,6`, khớp quan sát `19-20`.

Bốn tầng che lỗi nối nhau: suy nghĩ ăn ngân sách → JSON cụt → `json_repair` vá được mảng ngắn hơn →
vá thành công nên **không** ghi log → `call_llm_batch` trả về bình thường. Bản ghi cuối trong phần vá
được còn có **13 fills**, cao hơn trung bình **11,4**, nên nhìn kết quả **không có dấu hiệu nào** cho
thấy vừa mất 6 dòng.

### 2.9 Mọi lượt gọi quy đúng về agent 7

`fact_call` nguồn gateway `388 → 420` (**+32**), sổ LiteLLM hôm nay **32**. `32 = 32`, không dòng nào
mất khỏi chiều agent. `audit_db.py` nhóm J: **không mục nào FAIL**; hai mục `note` đều là dòng lịch
sử từ `29/08` tới `07/09`.

Việc phụ đã mở khoá: `thinking_enabled` nay có **7 dòng TRUE**, lần đầu cột này có dữ liệu.

---

## 3. Điều SUY LUẬN — chưa chứng minh, đừng đọc thành đã biết

| điều | dựa trên | cần gì để chứng minh |
|---|---|---|
| Lô 25 với trần `16000` an toàn lâu dài | **một** lượt đo `10.534` token ra | chạy nhiều lô có nội dung dài hơn trung bình |
| Tắt suy nghĩ không giảm chất lượng phân loại | tác vụ là trích xuất theo danh sách tag đóng | so kết quả có/không suy nghĩ trên cùng tập, có người chấm |
| Nhịp thực đạt của production | chưa đo | **mục 4, chưa chạy** |
| Gateway làm chậm thêm bao nhiêu | chưa đo | **mục 5, chưa chạy** |
| `max_tokens` áp cho tổng suy nghĩ cộng chữ | `text_tokens = 0` khi trần 16 | giải thích vì sao lượt đó dừng ở 12 chứ không phải 16 |

### Ba lần trong một ngày, suy đoán bị chính số đo bác bỏ

Ghi lại vì đây là bài học lặp, không phải ba sự cố rời rạc:

1. Hậu tố `_GG_AIA_STU` nghe như khoá AI Studio → đo tiền tố, nó là `AQ.`, tức Vertex express
2. `KEY_GOOGLE_AI_STU` cũng `AQ.` nên tuyến DMS chắc hỏng → hỏi sổ, **404 lượt thành công**
3. `Timeout(300.0)` có thể treo 300 giây → đo bốn kiểu hỏng mạng, lâu nhất **21,07 giây**

Cả ba đều là suy luận từ **tên gọi hoặc đọc code**, và cả ba đều sai. Cách rẻ hơn luôn có sẵn: hỏi
sổ trước khi gọi thử, đo trước khi kết luận.

### Một lỗi phương pháp, ghi để không lặp

Lúc đo timeout, lần thử đầu dùng IP `192.0.2.1` và gọi đó là "gói tin rơi im lặng". Nhưng lỗi trả về
là `Connection refused`, tức **có thứ gì đó đã trả lời** — phép thử không dựng đúng cảnh cần dựng.
Phải đổi sang địa chỉ trong dải Docker mà không container nào giữ, để ARP không ai đáp. Và cảnh đó
lại hỏng **nhanh hơn** (`3,11`s).

Tương tự, lúc thử `json_repair`, bốn chuỗi cắt cụt tự dựng đều **không có ký tự `]`**, nên
`_parse_llm_json` thoát ở nhánh "không tìm thấy mảng" và chưa hề chạm tới `json_repair`. Phải lấy
phản hồi cắt cụt **thật** mới thấy nó có `]` ở vị trí `23.046/23.079` và đi đúng vào nhánh vá.

---

## 4. Điều CHƯA LÀM và vì sao

**Mục 4 (batch cỡ production) và mục 5 (so độ trễ hai đường) HOÃN CÓ CHỦ Ý — chốt bởi anh Tuấn,
10/09.** Ô 0.2 chốt trần khoảng 50 lượt cho mục 1 tới 3, và ghi rõ mục 4, 5 nằm ngoài trần, phải hỏi
lại trước khi chạy. Đã hỏi, và quyết định là **archive change này ngay**, tách phần đo tải thành việc
riêng khi nào thật sự cần.

Lý do quyết định đó đứng vững: **câu hỏi cốt lõi của change đã trả lời xong**. Change tên là "chứng
minh đường CRM sống sót khi bị từ chối và khi mất Gateway" — cả hai vế đều có số ở mục 2 trên. Mục 4
và 5 hỏi thêm về *tải* và *độ trễ*, là câu hỏi khác và đắt hơn nhiều.

Số đo hôm nay cho biết cái giá thật của mục 4:

| cỡ lô | thời gian mỗi lượt | tiền mỗi lượt | 502 lượt tốn |
|---|---|---|---|
| 25 dòng | 39,4 s | $0,0257 | **5,5 tiếng**, $12,90 |
| 5 dòng | 16,2 s | $0,0071 | **2,3 tiếng**, $3,57 |

Ô 0.2 đã đoán đúng từ đầu: **trần của mục 4 phải là trần THỜI GIAN**, không phải trần tiền.

Hai ô của mục 4 **không phụ thuộc cỡ tải** nên đã làm xong: 4.5 (quy về agent 7) và 4.6 (audit nhóm
J). Ba ô còn lại — nhịp thực đạt, độ trễ phân vị, chi phí thực tế — bắt buộc phải có tải thật.

**Ô 0.1 còn chặn:** change `route-the-crm-agent-through-the-gateway` còn ô 7.6 chưa xong.

---

## 5. Việc phải báo lại nhóm CRM

Chi tiết ở mục 7 và 7b của `docs/reference/dua-crm-qua-gateway-10-09.md`. Tóm tắt phần sinh ra từ
change này:

1. **Nâng `max_output_tokens` `8192` → `16000`** (`src/llm.py:274`). Đây là chỗ duy nhất đặt giá trị
   đó, và **không đặt được ở tuyến Gateway** — đã thử, tham số client tự khai thắng mặc định tuyến
2. **Thêm kiểm `finish_reason == "length"`** trong lớp đứng thay Gateway. Bản gốc có **0** lần nhắc
   tới trường này, nên cắt cụt hiện đi qua hoàn toàn im lặng
3. **Nhánh 429 ngủ 30 giây vô ích** ở lượt thử cuối, do thiếu chốt `attempt < max_retry`
