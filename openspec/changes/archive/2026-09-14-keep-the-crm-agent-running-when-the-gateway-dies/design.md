## Context

Agent CRM gọi model qua Gateway từ 10/09. Đường đi hiện nay:

```
   CRM (3 worker song song)
        │  Bearer sk-…  ·  X-User: svc.crm-feedback
        ▼
   gateway-lb :4000  (nginx, MỘT instance)     ← điểm hỏng đơn
        ├──▶ litellm-1 ─┐
        └──▶ litellm-2 ─┴──▶ Google
```

**Hiện trạng đã đọc từ mã nguồn, không suy đoán:**

`init_llm_client()` (`src/llm.py:127`) chọn đường **một lần** rồi trả về client. Nhánh gateway kiểm
trước và trả về ngay, nên hai nhánh cũ (`vertex`, khoá trực tiếp) không đổi dòng nào.

`call_llm_batch()` (`src/llm.py:254`) thử lại 3 lần, ngủ 4 rồi 8 giây, sau đó ném
`RuntimeError("Failed calling Gemini API after 3 retries")`. Nhánh bắt lỗi ở `src/pipeline.py:664`
ghi log rồi **bỏ lô**, pipeline chạy tiếp lô sau.

`pipeline.py:600` dựng client **một lần**, `pipeline.py:610` chạy **3 worker** song song dùng chung
client đó. Đã có sẵn một `threading.Lock()` cho checkpoint (`pipeline.py:617`).

**Hiện trạng đã đo ngày 12/09, có số:**

| Điều | Kết quả đo |
|---|---|
| `sa-key.json` gọi Vertex | HTTP 200, 19 token, project `crm-test-508114` |
| SMTP Gmail của OpenWebUI | đăng nhập OK, đã gửi một thư thật |
| Ba thông tin Azure của CRM | trống cả ba, và không có tệp `.env` |
| Tệp `.env` mà `docker-compose.yml` khai là bắt buộc | không tồn tại |

## Goals / Non-Goals

**Goals:**

- Lô đang chạy **chạy xong** khi Gateway mất, thay vì bị bỏ và phải chạy lại.
- Người vận hành **biết** chuyện đó đã xảy ra, trong vòng vài phút, không phải bằng cách đọc log.
- Khoảng thời gian chạy đường thẳng **đọc lại được về sau**, không biến mất.
- Chuyển đường **không cần khởi động lại** agent.

**Non-Goals:**

- Không đưa phí của đường dự phòng về đúng project. Mọi khoá dùng được ở local đều trỏ project thử.
  Chốt 12/09: giai đoạn phát triển chấp nhận lệch. Mở lại trước khi lên server.
- Không bỏ `gateway-lb` hay dựng load balancer thứ hai. Đó là đường khác, giải cùng vấn đề, nhưng
  nằm ở repo dashboard chứ không ở agent.
- Không áp change này cho agent DMS. DMS chỉ dùng khi chạy bench.
- Không thay đường Microsoft Graph. Nó được giữ nguyên cho production sau khi có thông tin Azure.

## Decisions

### Quyết định 1 — Máy trạng thái ở tầng client, không ở tầng gọi từng lô

Đặt trạng thái vào một lớp bọc quanh client, để `call_llm_batch()` và `pipeline.py` **không đổi một
dòng nào**. Lớp bọc giữ đường hiện hành và tự đổi khi cần.

*Vì sao không đặt ở `call_llm_batch`:* hàm đó nhận `client` làm tham số và không biết gì về đường
đi. Sửa nó thành biết thì mọi nơi gọi nó đều phải biết theo.

*Vì sao không đặt ở `pipeline.py`:* pipeline đang chạy 3 worker; đặt logic đổi đường ở đó thì ba
worker mỗi con một bản sao trạng thái.

*Đã cân nhắc và loại:* để nguyên hai đường rồi bảo người vận hành đổi biến môi trường và chạy lại.
Rẻ nhất, nhưng đúng bằng hiện trạng — lô vẫn hỏng, chỉ khác là có người biết.

### Quyết định 2 — Đổi đường dựa trên lỗi liên tiếp, đếm dưới một chốt dùng chung

Ngưỡng là **N lần hỏng liên tiếp**, không phải tổng số lần hỏng. Một lượt hỏng lẻ là chuyện thường;
ba lượt liên tiếp mới là tuyến chết.

Ba worker cùng chạm vào bộ đếm, nên nó phải nằm dưới một `threading.Lock`. Không có chốt thì ba
worker cùng vượt ngưỡng, cùng dựng client mới và cùng gửi thư — đúng cái bẫy mà thiết kế này sinh
ra để tránh.

*Đã cân nhắc và loại:* mỗi worker tự giữ bộ đếm riêng. Đơn giản hơn, nhưng ngưỡng 3 khi ấy thành
ngưỡng 9 trên thực tế.

### Quyết định 3 — Chỉ lỗi "không kết nối được" mới đổi đường

Client Gateway hiện đã ném ba câu lỗi phân biệt được (`src/llm.py:91–118`):

| Câu lỗi | Nghĩa | Đổi đường? |
|---|---|---|
| `Gateway khong ket noi duoc: …` | hạ tầng chết | **có** |
| `429 qua han muc tu Gateway: …` | hạn mức | không, giữ nhánh lùi lịch sẵn có |
| `Gateway tra <mã ≥ 400>: …` | request sai | **không** |

Lỗi 400 đổi đường cũng sai y như vậy, chỉ tốn thêm một lượt gọi ở nơi khác.

Với 429 thì khó hơn và cố ý **không** làm trong change này: hạn mức ảo của Gateway thì đi thẳng có
thể qua, nhưng hạn mức thật của Google thì không, và hiện chưa phân biệt được hai loại từ phía
agent. Ghi vào Open Questions.

*Bẫy đã biết:* nhận dạng bằng chuỗi ký tự là mong manh. Nhưng chính repo đã đặt cược vào đó từ
trước — ghi chú ở `src/llm.py:21–29` nói rõ câu lỗi **phải** mang chuỗi `429`, nếu không CRM lùi
4–8 giây thay vì lùi đúng nhánh. Change này giữ nguyên giao kèo đó chứ không dựng giao kèo mới.

### Quyết định 4 — Đường dự phòng dùng tệp service account có sẵn, không dùng biến khoá mới

Anh Tuấn đề xuất thêm biến `KEY_FALLBACK`. Ý đó **đúng về nguyên tắc** và giữ lại cho sau, nhưng
không dùng được với khoá đang có:

```
   KEY_BENCH_CRM_TEST_GG_AIA_STU  dạng `AQ.`  = Vertex express
        aiplatform.googleapis.com          → 200
        generativelanguage.googleapis.com  → 403
```

Nhánh gọi bằng khoá của CRM dựng `genai.Client(api_key=…)`, mặc định đi AI Studio, tức đi đúng cửa
bị 403. Dùng khoá này phải **viết thêm** một đường gọi Vertex express.

Trong khi đó nhánh Vertex đã viết sẵn, đọc thẳng `sa-key.json`, và tôi gọi một lượt thật ngày 12/09
cho HTTP 200.

Nhưng biến riêng vẫn cần tồn tại, vì một lý do cụ thể: cả ba đường hiện tranh nhau **một** biến
`GEMINI_API_KEY`. Khi chạy qua Gateway, biến đó giữ khoá ảo `sk-…`. Đường dự phòng mà đọc lại chính
biến ấy sẽ cầm khoá ảo đi gọi thẳng Google. Nên đường dự phòng **không được** đọc `GEMINI_API_KEY`,
dù nó lấy thông tin từ đâu.

### Quyết định 5 — Gửi thư bằng SMTP, giữ nguyên đường Graph

Thêm hàm gửi SMTP **cạnh** hàm Graph, chọn bằng cấu hình. Chốt bởi anh Tuấn ngày 12/09; Azure xem
lại sau cuộc họp.

*Vì sao không thay hẳn Graph:* Graph gửi bằng hòm thư công ty, đúng cho production. Nó chưa chạy
được vì thiếu thông tin đăng nhập, không phải vì sai thiết kế.

*Cấu hình lấy từ đâu:* dùng lại đúng thông số đã kiểm chứng của OpenWebUI — `smtp.gmail.com:587`,
TLS, app password 16 ký tự. Mật khẩu đọc từ biến môi trường, **không** ghi vào tệp cấu hình nào
theo git.

### Quyết định 6 — Thư gộp theo sự cố: đúng hai thư

Một thư khi đổi sang đường thẳng, một thư khi quay về. Không thư nào cho từng lượt hỏng.

Con số biện minh: lô ngày 09/09 có 3.422 lượt gọi. Nếu Gateway chết giữa lô đó, cách "mỗi lỗi một
thư" sinh ra hàng nghìn thư và người nhận sẽ tắt thông báo — tức phép cảnh báo tự huỷ chính nó.

Gửi thư **không được** làm hỏng lô: bọc trong `try/except`, hỏng thì ghi log và chạy tiếp. Mẫu này
đã có sẵn ở `src/pipeline.py:877–879`.

### Quyết định 7 — Quay về Gateway bằng phép thử định kỳ, không bằng mỗi lượt gọi

Ở trạng thái đường thẳng, thử lại Gateway sau mỗi khoảng thời gian cố định. Thử mỗi lượt thì mỗi
lượt phải trả giá một lần chờ hết thời gian kết nối.

## Risks / Trade-offs

**Agent lại cầm khoá nhà cung cấp** → Đây là đúng thứ Gateway sinh ra để bỏ: tài liệu kiến trúc gọi
việc đi qua Gateway là *"bắt buộc về mặt kỹ thuật"*. Change này gỡ cái chốt đó. Không có cách giảm
nhẹ nào thật sự; đổi lại là hệ thống không đứng, và lead đã chốt hướng ưu tiên. Phải ghi rõ trong
tài liệu bàn giao để người sau không tưởng tính chất cũ còn nguyên.

**Phí rơi vào project thử** → Chấp nhận có ý thức ở giai đoạn phát triển. Giảm nhẹ: ghi project id
ngay cạnh dòng khai báo, và mở lại ô này trước khi lên server. Tiền lệ đã có: sáng 12/09 một project
lạ lọt vào khâu nạp làm cả đường ống dừng.

**Chập chờn qua lại khi Gateway lúc sống lúc chết** → Giảm nhẹ bằng ngưỡng lỗi liên tiếp và khoảng
chờ trước khi thử lại. Ghi nhận: chưa đo được ngưỡng nào là đủ, vì chưa có sự cố thật nào ngoài
diễn tập.

**Nhận dạng lỗi bằng chuỗi ký tự sẽ vỡ nếu ai đó sửa câu lỗi** → Giảm nhẹ bằng một phép kiểm tự
động khẳng định ba câu lỗi vẫn phân biệt được. Nếu không có phép kiểm đó, thay đổi một câu chữ sẽ
làm fallback im lặng ngừng hoạt động.

**Lượt đi đường thẳng không vào sổ Gateway** → Dashboard sẽ thiếu chúng trong `fact_call`. Giảm nhẹ
bằng cách ghi lại phía agent. Chưa giảm nhẹ được phần hoá đơn, vì khoá không thuộc project đã khai.

**Gmail có thể chặn hoặc xếp thư vào thư rác** → Chưa xác nhận được thư đã vào hộp thư, mới xác nhận
nó rời máy. Phải kiểm trước khi tin vào đường báo động này.

## Migration Plan

1. Tạo `.env` cho CRM — chặn mọi việc khác, vì container hiện không khởi động được.
2. Thêm đường SMTP, kiểm bằng một thư thật trước khi nối vào luồng hỏng.
3. Thêm máy trạng thái, mặc định **tắt**. Bật bằng cấu hình.
4. Diễn tập: dừng `gateway-lb` giữa lúc chạy, giống cách làm ngày 10/09.
5. Bật ở local. Không đưa lên server cho tới khi có khoá thuộc project thật.

**Đường lui:** tắt cấu hình bật fallback, agent trở về hành vi hiện nay. Không có thay đổi dữ liệu
nào phải hoàn tác.

## Open Questions

- **Lỗi 429 có nên đổi đường không?** Hiện chưa phân biệt được hạn mức ảo của Gateway với hạn mức
  thật của Google từ phía agent. Change này cố ý không làm.
- **Ngưỡng bao nhiêu lần liên tiếp, và chờ bao lâu trước khi thử về?** Chưa có sự cố thật để đo.
  Đề nghị bắt đầu bằng 3 lần và 60 giây, rồi chỉnh sau khi diễn tập.
- **Thư có vào được hộp thư không?** Đã gửi một thư thật ngày 12/09 nhưng chưa ai xác nhận nhận được.
- **`60854134008` ứng với project id nào?** Biết mã số nhưng chưa biết tên. Không chặn change này.
