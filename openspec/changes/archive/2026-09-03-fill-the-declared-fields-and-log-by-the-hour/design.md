# Thiết kế — điền nốt những trường đã khai, và ghi log theo giờ

Mọi con số đo trên database thật và sổ `LiteLLM_SpendLogs` thật, ngày 02/09/2026.

---

## ① `unit_id`: tra từ tài khoản, KHÔNG tra từ tag

`db/load_ralli.py` đã có sẵn đường đi đúng — tra `dim_user` theo `user_id`. Nhưng nguồn Gateway
khác: nó có `account_id` đã quy được, nên tra thẳng từ đó.

```
   account 949 (svc.dms-feedback)  ->  unit_id = __technical_6__
```

**Cấm suy `unit_id` từ tag của request.** Tag nói agent nào gửi, không nói người gửi thuộc phòng
ban nào. Với agent một-người-dùng thì hai thứ trùng nhau **hôm nay**, và đúng vì thế mà lỗi sẽ
im lặng khi có agent nhiều người dùng đi qua Gateway.

**`__technical_6__` là một đơn vị KỸ THUẬT, không phải phòng ban thật.** Đó là câu trả lời
trung thực cho một tài khoản dịch vụ: nó không thuộc phòng ban nào. Ghi `NULL` thì mất thông
tin (không phân biệt được "chưa nạp" với "không có phòng ban"); bịa một phòng ban thật thì tệ
hơn nhiều.

## ② `cached_tokens`: ĐO, không vá

Đếm trên 42 lượt thành công:

```
   prompt_tokens_details.cached_tokens     0/42   JSON null
   cache_read_input_tokens                 0/42   JSON null
```

LiteLLM có **hai** chỗ riêng để ghi token cache và **cả hai đều rỗng**. Nên đây không phải một
chỗ đọc nhầm — nếu chỉ một chỗ rỗng thì còn nghi ngờ được, hai chỗ thì không.

**Ba khả năng, và chúng đòi ba cách xử lý khác nhau:**

| | Khả năng | Kiểm bằng gì | Nếu đúng thì làm gì |
|---|---|---|---|
| a | Gemini không có context caching cho những lượt này | Hoá đơn Google có SKU cache những ngày đó không | Ghi NULL vĩnh viễn, **đúng nghĩa** |
| b | Gemini có báo, LiteLLM không ánh xạ | Đọc `response` thô của một lượt | Báo lên fork, hoặc tự vá ánh xạ |
| c | Có caching nhưng phải bật tường minh | Tài liệu Gemini + cấu hình tuyến | Là quyết định sản phẩm, không phải lỗi |

**Change này chỉ ĐO và GHI LẠI, không tự chọn.** Lý do: (a) và (b) trông giống hệt nhau ở tầng
database — cả hai đều ra NULL — mà cách xử lý thì ngược nhau hoàn toàn.

**Tuyệt đối không ghi 0.** Cùng lý lẽ đã dùng cho `duration_ms` ở change 006: 0 là *"đo được
bằng không"*, NULL là *"không đo được"*. Ghi 0 vào đây thì mọi phép tính tỷ lệ cache sau này
đều sai mà không ai biết.

## ③ Bảng theo giờ: `billing` KHÔNG có giờ, và phải nói ra ở tầng dữ liệu

```
   fact_call gateway       ts_local  ->  xuong duoc GIO
   fact_call app           ts_local  ->  xuong duoc GIO
   fact_monitoring         ts_local  ->  xuong duoc GIO
   fact_billing_daily      day       ->  KHONG BAO GIO co gio
```

Hoá đơn Google tính theo ngày. Đó là giới hạn của nhà cung cấp, không phải của ta, và **không
có cách nào vượt**.

**Quyết định: bảng theo giờ KHÔNG chứa nguồn `billing`, và cột `source` làm điều đó lộ ra.**

Cách sai mà dễ chọn: chia đều tiền của một ngày cho 24 giờ. Nó cho ra một biểu đồ đẹp và một
con số **bịa** — mỗi giờ mang một phần tiền mà nhà cung cấp chưa bao giờ nói là của giờ đó. Cùng
loại lỗi với việc trung bình các p95 để ra p95 của ngày, đã ghi ở `db/build_performance.py`.

Người đọc biết `billing` vắng mặt bằng cách **truy vấn `source`**, không phải bằng một dòng chú
thích trên giao diện. Dữ liệu tự nói, không nhờ tầng hiển thị nói hộ.

## ④ Khoá của bảng theo giờ — đo trước khi chốt

Đếm ba lần, ra **ba con số khác nhau** — và chuyện đó mới là điều đáng ghi:

```
   cach dem                                        ngay      gio    he so
   (1) khoa thieu: (gio, agent) cho monitoring      739    5.129      6,9
   (2) khoa du:    (gio, agent, model)            1.320    7.651      5,8
   (3) khoa du + DUNG BO LOC cua build_usage_daily
       (model_id IS NOT NULL, measures='token')      782    2.946      3,8
```

Cách (3) gần đúng nhất vì nó dùng chính bộ lọc mà tầng tổng hợp sẽ dùng. Nhưng nó **vẫn chỉ là
ước lượng**: nó cho 484 dòng monitoring theo ngày trong khi `fact_usage_daily` đang có **606**.

Lệch vì một chuyện cụ thể, đã kiểm: **`fact_monitoring` không có cột `account_id`**. Nguồn này
chỉ báo tới mức project, nên tầng tổng hợp gán tài khoản neo cho nó. Dựng lại phép gộp bằng tay
mà bỏ chiều `account_id` thì đếm thiếu — và đó đúng là chỗ 484 khác 606.

Khoá thật của `fact_usage_daily` (đã kiểm bằng `pg_index`):

```
   day, agent_id, model_id, account_id, source
```

Bảng theo giờ dùng đúng năm chiều đó, chỉ đổi `day` thành `hour`.

**Kết luận trung thực: vài nghìn dòng, cùng bậc với bảng lớn nhất hiện có
(`fact_billing_daily` 2.575). Con số chính xác chỉ biết sau khi dựng — đó là việc 6.5.**

Điều **chắc chắn** rút ra được, không phụ thuộc cách đếm: hệ số nằm trong khoảng **3,8 – 6,9
lần**, không phải 24 lần. Lưu lượng dồn vào giờ hành chính chứ không rải đều.

Và một điều nữa, đúng ở cả ba cách đếm: bảng theo giờ sẽ **lớn hơn hoặc xấp xỉ bảng tổng hợp
lớn nhất hiện tại**, chứ không nhỏ. Nó cũng là bảng duy nhất **tăng theo lưu lượng** khi 8 agent
cùng đi qua Gateway.

**Nên chọn khoá đầy đủ như bảng ngày**, không rút bớt chiều để tiết kiệm dòng. Rút chiều là mất
khả năng cắt lát, mà cái ta tiết kiệm được thì không đáng gì.

**Bảng riêng, không thêm cột `hour` vào `fact_usage_daily`.** Hai lý do: khoá chính của bảng
ngày đang được 10 chỗ đầu đọc dựa vào, và một bảng mà hai độ mịn nằm chung thì **mọi phép SUM
đều phải nhớ lọc** — đúng hình dạng lỗi `source` hồi 31/08.

## ⑤ `fact_latency_daily` và `fact_perf_daily` phải có cột `source` TRƯỚC

```
   fact_latency_daily   day, agent_id, samples, p50_seconds, p95_seconds,
                        p95_bucket_from, p95_bucket_to, p99_seconds, enough_samples
   fact_perf_daily      day, agent_id, method, response_code, calls
```

Cả hai **không có cột `source`**. Chúng là bảng dẫn xuất của riêng nguồn monitoring, dựng từ
histogram gộp tay.

Đổ phân vị Gateway vào chúng khi chưa có `source` là trộn hai phép đo bản chất khác nhau:

```
   monitoring   p95 NOI SUY trong thung rong 33,55 - 67,11 giay
   gateway      p95 CHINH XAC tu tung gia tri do_tre tho
```

Hai con số cùng tên, cùng cột, khác hẳn độ tin cậy. Không có `source` thì **không ai phân biệt
được**, và người đọc sau sẽ so hai số như thể chúng cùng loại.

Thêm cột `source` là **việc phải làm trước**, không phải việc kèm theo.

## ⑥ Phân vị: tính chính xác, và KHÔNG gộp với monitoring

Change 006 để lại hai câu hỏi. Nay trả lời cả hai:

**Ngưỡng số mẫu.** Giữ nguyên `MIN_SAMPLES = 10` và cột `enough_samples` đang có. Đổi ngưỡng
trong cùng một change với việc thêm nguồn là trộn hai thay đổi — không phân biệt được số đổi vì
nguồn mới hay vì ngưỡng mới.

**Gộp hay để cạnh nhau: ĐỂ CẠNH NHAU**, đúng như bốn nguồn token đang làm. Mỗi nguồn một dòng,
`usage_resolved` chọn một khi cần một con số duy nhất. Gộp trung bình hai phân vị là tạo ra một
con số **không thuộc về phép đo nào**.

Với Gateway, `p95_bucket_from` và `p95_bucket_to` **để NULL** — chúng mô tả sai số của histogram,
mà số thô thì không có sai số đó. NULL ở đây nghĩa là *"không áp dụng"*, và đó là một thông tin
thật.

## ⑦ Endpoint theo giờ: chỉ-đọc, và bắt buộc có khoảng thời gian

Endpoint theo giờ **phải đòi khoảng bắt đầu/kết thúc**, không cho gọi trần. Bảng ngày trả 1.990
dòng thì còn chấp nhận được; bảng giờ mà không giới hạn sẽ trả hàng nghìn dòng cho một câu hỏi
mà người gọi chưa kịp nghĩ.

Giữ nguyên kỷ luật: mọi câu SQL trong `backend/store.py`, `api.js` là lớp dịch duy nhất, kết nối
là `api_readonly`.

---

## Những gì change này CỐ Ý không làm

- **Không tự bật context caching**, và không kết luận vì sao `cached_tokens` rỗng. Đo và ghi.
- **Không đổi `MIN_SAMPLES`** — xem ⑥.
- **Không chia tiền hoá đơn ra theo giờ** — xem ③.
- **Không đụng frontend.** Có endpoint theo giờ không có nghĩa là dashboard phải vẽ ngay; đó là
  mục "Cập nhật dashboard cho chiều người dùng đầy đủ" (STT 6 mục tiêu 3, mốc 21/10).
- **Không nạp `retry_count`, `fallback_used`** (Data Out 24, 25). Cả hai **không bắt buộc**, và
  `metadata.attempted_retries` cần đo riêng xem nó có ý nghĩa gì khi Router chuyển tuyến.

## ⑧ `thinking_enabled` — ĐƯA VÀO PHẠM VI sau khi đo (sửa 02/09)

Bản đầu của mục này loại `thinking_enabled` (Data Out 14) với lý do *"không bắt buộc, cần đo
riêng"*. **Đã đo, và lý do đó không còn đúng** — nó nằm ngay trong khối vừa mở ra cho
`output_modality`:

```
   completion_tokens_details co 7 khoa. Dem tren 42 luot thanh cong:
      text_tokens        42/42
      reasoning_tokens    2/42   <- CHINH LA "thinking"
      audio/image/video   0/42
```

Hai dòng mang `reasoning_tokens = 342` là `gemini-3.6-flash` — **chính hai lượt nghiệm thu cache
tối 01/09**. Nên con số này không phải lý thuyết.

Và `fact_monitoring` đã có sẵn cột `thinking_enabled` kiểu BOOLEAN với `true / false / NULL`
(11.440 / 3.589 / 636.624). Nguồn Gateway suy được bằng đúng quy ước đó:

```
   thinking_enabled = (reasoning_tokens IS NOT NULL AND reasoning_tokens > 0)
```

Nạp nó **không tốn thêm gì**: cùng khối JSON, cùng lần sửa bộ nạp, cùng migration. Loại nó ra
lúc này là bỏ một trường Data Out chỉ vì kế hoạch cũ nói vậy.

**Data Out: 21/26 → 23/26** (không phải 22/26 như bản đầu tính).
