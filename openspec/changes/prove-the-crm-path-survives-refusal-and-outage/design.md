## Context

Đường CRM → Gateway → Google → sổ → dashboard đã thông sau change
`route-the-crm-agent-through-the-gateway`. Change này đi tìm chỗ nó **vỡ**.

### Vì sao ba phép đo này không tự xảy ra

```
   CRM tu gioi han : ~7,3 luot/phut   (7,5s + jitter 1,5 -- con so tac gia khuyen nghi)
   Gateway cho     :  15 luot/phut    (giu nguyen theo chot 09/09: sat production nhat)
                      ─────────────
                      CRM o DUOI NUA tran -> KHONG BAO GIO sinh 429
```

Nên nhánh 429 của CRM chưa ai chạy qua. Và nó là nhánh đáng lo nhất, vì nó nhận lỗi bằng
**so chuỗi**:

```python
if "429" in low or "rate limit" in low or "resource_exhausted" in low:
    wait = min(120, 10 * attempt) + random.random() * 2
    time.sleep(wait)
    continue                          # lui LICH SU -- ngu o MOI lan thu
if attempt < max_retry:
    time.sleep(4.0 * attempt)
    continue                          # lui CHUNG -- ngu o lan 1,2; lan 3 nem loi ngay
raise RuntimeError(...)
```

Đây là **hai câu `if` nối tiếp**, không phải `if/else` — và chốt `attempt < max_retry` ở câu
thứ hai là chi tiết quyết định, xem Quyết định 2.

Sai một chữ trong thông báo lỗi là CRM chuyển từ lùi `10, 20, 30` giây sang lùi `4, 8` giây,
và dập vào một Gateway vừa xin nó chậm lại. Không phép đo nào ngoài việc ép 429 nhìn thấy
được chuyện đó.

### Đo được, làm căn cứ cho thiết kế

| Điều | Giá trị | Nguồn |
|---|---|---|
| tải cao nhất theo ngày | **502 lượt** | `fact_usage_daily`, agent 7 |
| tải cao nhất theo giờ | **365 lượt** (07/07 12:00) | `fact_usage_hourly` |
| một lượt gọi | 25 dòng CRM | `config.BATCH_SIZE` |
| điểm lưu | `save_history_db_atomic` gọi trong worker sau **mỗi** batch, ghi `classified_history_db.json` | `pipeline.py:688` (còn 3 chỗ nữa: 488, 538, 718, nằm ngoài vòng batch) |
| song song | `ThreadPoolExecutor(3)`, nhưng `wait_for_rate_limit()` khoá **toàn cục** và ngủ **trong** khoá | `llm.py` |
| retry của CRM | `max_retry=3`; 429 → ngủ `10, 20, 30`s (trần `min(120, …)` **không bao giờ chạm tới** ở 3 lần thử); lỗi khác → ngủ `4, 8`s rồi lần 3 ném lỗi ngay | `llm.py` |
| retry của Gateway | `num_retries: 3`, `allowed_fails: 3`, `cooldown_time: 30` | `config.gateway.yaml` |
| fallback của Gateway | `gemini-flash → gemini-flash-preview` | `config.gateway.yaml` |

### Một phát hiện phụ khi đọc code

`config.CKPT_JSON` (`llm_fills_checkpoint.json`) **được khai nhưng không nơi nào dùng**.
Điểm lưu thật ghi vào `DB_JSON_PATH` (`classified_history_db.json`). `docs/HANDOVER.md` của
CRM vẫn mô tả `llm_fills_checkpoint.json` là file cho phép chạy lại — nên ai đọc doc rồi đi
xoá/kiểm file đó sẽ nhìn vào chỗ không liên quan. Thêm vào danh sách báo lại nhóm CRM.

## Goals / Non-Goals

**Goals**

- Chứng minh **bằng phép đo** rằng nhánh 429 của CRM chạy đúng nhánh lịch sự.
- Chứng minh mất Gateway giữa batch thì chạy lại **không mất dòng và không đếm đôi**.
- Biết đường mới chịu được khối lượng thật, và biết nó **chậm thêm bao nhiêu**.
- Để lại một công cụ **dùng lại được cho 6 agent còn lại**, không phải script một lần.

**Non-Goals**

- Không sửa nhánh `gateway` đã viết. Nếu phép đo lộ ra nó sai thì đó là **phát hiện**, ghi
  lại trước, sửa sau — có thể ở change khác.
- Không đổi `rpm` vĩnh viễn. Mọi lần đổi để ép hỏng đều phải trả lại.
- Không chạy cả pipeline. Mọi phép đo qua harness — pipeline không có cờ dry-run nào và sẽ
  ghi SharePoint thật, gửi email thật.
- Không nhắm tối ưu hiệu năng. Đo để **biết**, không để nhanh hơn.

## Decisions

### Quyết định 1 — Ép 429 bằng cách hạ `rpm`, không bằng cách bắn dồn

Hai cách ép:

| cách | vấn đề |
|---|---|
| bắn nhiều lượt song song | `wait_for_rate_limit()` khoá **toàn cục**, nên harness không bắn dồn được nếu nó đi qua đúng đường CRM đi. Muốn bắn dồn phải **đi vòng** qua chính cơ chế đang muốn thử |
| hạ `rpm` của tuyến xuống 1 | Gateway từ chối ngay ở lượt thứ hai, không cần đụng vào CRM |

Chọn cách thứ hai: nó ép đúng **cửa** ta muốn thử (Gateway từ chối → CRM nhận), và không sửa
gì trong đường của CRM. Cách thứ nhất sẽ đo một đường mà production không bao giờ đi.

Bắt buộc: trả `rpm` về 15 ngay sau đó, và **kiểm bằng phép đo** là đã trả — không dựa vào
việc ai nhớ.

### Quyết định 2 — Phân biệt được nhánh nào chạy, không suy từ "nó vẫn xong"

Cả hai nhánh lùi lịch đều dẫn tới "cuối cùng vẫn xong", nên **kết quả không nói được** nhánh
nào đã chạy. Phải đo bằng **thời gian giữa hai lần thử**:

**Số lần ngủ phân biệt mạnh hơn độ dài** — đọc kỹ `llm.py` mới thấy. Nhánh 429 `continue` ở
**mọi** lần thử nên nó ngủ cả ở lần thứ 3; nhánh chung có chốt `if attempt < max_retry` nên
lần thử thứ 3 **ném lỗi ngay, không ngủ**. Với `max_retry = 3`:

```
   nhanh 429    -> 3 khoang: 10, 20, 30   (>= 60 giay truoc khi bo)
   nhanh chung  -> 2 khoang:  4,  8       (12 giay)
```

Hai dãy không chồng nhau **và** số khoảng cũng khác, nên phân biệt được nhánh **mà không cần
đọc log của CRM**. Đo được 2 khoảng 4 và 8 giây thì `429` không tới được nhánh đúng — đó là
phát hiện thật, không phải lỗi phép đo.

Kèm một hệ quả cho phép đo tải: nhánh 429 ngủ 30 giây ở lần thử cuối rồi **vẫn bỏ**, vì vòng
lặp hết và rơi xuống `raise` phía sau. Một batch bị 429 tới cùng mất **ít nhất 60 giây** trước
khi thất bại; đặt timeout ngắn hơn con số đó rồi kết luận là treo thì sai.

### Quyết định 3 — Diễn tập mất Gateway: dừng `gateway-lb`, không dừng LiteLLM

Dừng `gateway-lb` mô phỏng đúng thứ CRM thấy: **không kết nối được**. Dừng LiteLLM thì nginx
còn sống và trả 502 — một tình huống khác, và nhẹ hơn.

Nghiệm thu là **hai** điều, không phải một:

```
   1. khong MAT dong: moi dong CRM dang xu ly hoac vao so, hoac quay lai hang cho
   2. khong DEM DOI: chay lai KHONG sinh ra dong thu hai cho cung mot dong CRM
```

Điều thứ hai dễ bị bỏ qua và tệ hơn điều thứ nhất: mất dòng thì thấy ngay ở kết quả phân
loại, còn đếm đôi thì làm **tiền và token trong sổ phồng lên** mà kết quả phân loại vẫn
trông đúng.

### Quyết định 4 — Đo độ trễ bằng cặp có kiểm soát, không so hai lần chạy khác nhau

So "batch qua Gateway" với "batch chạy tuần trước" là vô nghĩa: khác đầu vào, khác giờ, khác
tải của Google. Phép đo phải là **cùng đầu vào, hai đường, xen kẽ**:

```
   dong 1..N  ->  Gateway   ┐
   dong 1..N  ->  truc tiep ├─ xen ke, khong chay het duong nay roi moi sang duong kia
   dong 1..N  ->  Gateway   ┘
```

Xen kẽ vì tải của Google trôi theo thời gian; chạy hết một đường rồi mới sang đường kia là
đo cả chuyện đó vào chênh lệch.

Nêu **trung vị và phân vị 95**, không nêu trung bình: một lượt chậm bất thường kéo trung
bình đi và che mất hình dạng.

### Quyết định 5 — Harness là công cụ, không phải script một lần

6 agent còn lại sẽ cần đúng việc này. Nên harness nhận **tham số**: agent nào, khoá nào,
model nào, bao nhiêu lượt, đường nào (gateway hay trực tiếp). Không nhét CRM vào code.

Đặt trong `tools/` cùng chỗ với các công cụ đo đã có, và **không** trong `db/` hay
`scripts/` — hai chỗ đó là đường nạp dữ liệu thật.

## Risks / Trade-offs

**Hạ `rpm` rồi quên trả lại** → tuyến CRM sẽ từ chối gần như mọi lượt gọi, và triệu chứng
trông y như "Google giới hạn ta". Giảm rủi ro: task trả lại là task riêng, và có phép đo xác
nhận `rpm` đã về 15 chứ không chỉ có một dòng ghi "đã trả".

**Batch cỡ production tiêu tiền thật** → 502 lượt × ~12.000 token/lượt. Phải chốt trần chi
tiêu **trước** khi chạy. Và ghi rõ: đây là credit của người dùng, không phải tiền công ty.

**`num_retries` của Gateway che mất 429 khỏi CRM** → Gateway tự thử lại 3 lần trước khi trả
lỗi ra ngoài. Nên khi hạ `rpm` xuống 1, có thể CRM **không bao giờ thấy** 429 vì Gateway đã
tự xoay xong. Phải kiểm chuyện này trước, không thì phép đo sẽ kết luận "CRM không nhận
được 429" trong khi thật ra là "CRM chưa bao giờ được cho xem 429".

**`fallbacks` cũng che** → `gemini-flash → gemini-flash-preview` nghĩa là hết hạn mức ở tuyến
này thì Gateway đổi sang tuyến khác. Tuyến CRM **chưa tồn tại lúc viết tài liệu này**, nên
không thể nói nó có fallback hay không; phải kiểm sau khi change trước khai xong. Nếu có thì phép đo
429 sẽ đo một đường khác hẳn.

**Mất Gateway giữa batch có thể để lại trạng thái nửa vời trên SharePoint** → không, vì mọi
phép đo đi qua harness và harness không ghi SharePoint. Nhưng nếu sau này ai chạy diễn tập
này bằng pipeline thật thì rủi ro đó có thật, và phải ghi vào tài liệu.

**Đo độ trễ đường trực tiếp cần khoá nhà cung cấp** → mà theo thiết kế change trước, CRM
**không còn giữ** khoá nhà cung cấp để nó không đi vòng được. Nên phép đo đường trực tiếp
phải dùng khoá của người vận hành, và phải nói rõ đó là đường **không** tồn tại trong
production nữa — nó chỉ là mốc so.

## Migration Plan

1. Đo mốc nền trước khi đổi gì: nhịp thực đạt, độ trễ, số dòng trong sổ.
2. Ép 429 (hạ `rpm`), đo khoảng cách giữa các lần thử, trả `rpm` về, xác nhận đã trả.
3. Diễn tập mất Gateway giữa batch, chạy lại, đối chiếu không mất và không đôi.
4. Batch cỡ production, trong trần chi tiêu đã chốt.
5. Đo độ trễ xen kẽ hai đường.
6. Không có gì phải hoàn tác ngoài `rpm` — mọi phép đo đọc, không ghi vào dữ liệu nghiệp vụ.

## Open Questions

- `num_retries: 3` của Gateway có che 429 khỏi CRM hay không? Quyết định cả cách ép ở
  Quyết định 1. Phải đo trước, không đoán.
- Trần chi tiêu cho batch cỡ production là bao nhiêu? Người dùng chốt.
- Có nên diễn tập luôn "Gateway chết trong lúc pipeline thật chạy 03:30" hay chỉ diễn tập
  qua harness? Bản đầu chọn harness cho an toàn; nhưng đường lui thật thì chỉ diễn tập trên
  pipeline thật mới chứng minh được.
