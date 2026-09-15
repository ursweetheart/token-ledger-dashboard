## Why

Load balancer của Gateway là **điểm hỏng đơn**: hai instance LiteLLM có dự phòng cho nhau, nhưng
`gateway-lb` chỉ có một. Diễn tập 10/09 đã đo: khi nó mất, agent CRM thử ba lần trong khoảng 21–24
giây rồi **bỏ cả lô**, và không ai được báo — chỉ một dòng log giữa hàng trăm dòng khác.

Lead đã chốt hướng ngày 10/09: *"cái việc mình track không được ưu tiên trước hệ thống ổn định"*.
Change này thực hiện đúng câu đó cho agent CRM, và bịt luôn khoảng lặng đi kèm: hệ thống chạy tiếp,
mà người vận hành vẫn biết có thứ đang hỏng.

## What Changes

- **Đường gọi LLM của CRM đổi từ lựa chọn cố định thành máy trạng thái hai nấc.** Hiện
  `init_llm_client()` chọn một lần lúc khởi tạo rồi giữ nguyên suốt lần chạy. Sau change, khi
  Gateway không kết nối được N lần liên tiếp, agent tự chuyển sang gọi thẳng nhà cung cấp và chạy
  tiếp; Gateway sống lại thì tự quay về.
- **Chỉ lỗi hạ tầng mới kích hoạt chuyển đường.** Client Gateway hiện đã phân biệt được ba loại
  lỗi: không kết nối được, quá hạn mức, và mã ≥ 400. Chỉ loại đầu được chuyển. Lỗi 400 là request
  sai, đổi đường cũng sai y như vậy.
- **Thêm đường gửi thư thường qua SMTP** bên cạnh đường Microsoft Graph sẵn có, **không thay thế
  nó**. Đo 12/09: cả ba thông tin Azure của CRM đều trống và repo không có tệp `.env`, nên đường
  Graph hiện **chưa từng gửi được thư nào**. Đường SMTP đã được kiểm chứng bằng một thư thật.
- **Thư gộp theo sự cố, không gộp theo lượt gọi.** Đúng hai thư cho một sự cố: lúc chuyển sang
  đường thẳng, và lúc quay về. Một lô cỡ 09/09 có 3.422 lượt; gửi mỗi lỗi một thư là chôn hộp thư
  người nhận.
- **Tạo tệp cấu hình cho CRM.** `docker-compose.yml` của CRM khai `env_file: .env` mà tệp đó không
  tồn tại, nên container hiện **không khởi động được**. Việc này chặn mọi việc còn lại.
- **Ghi lại mọi lượt đi đường thẳng.** Lúc ấy Gateway không ghi sổ; nếu agent cũng không ghi thì
  khoảng thời gian đó chỉ còn biết qua hoá đơn, chậm một ngày và không biết ai gọi.

**Không thuộc phạm vi change này:** đưa phí của đường dự phòng về đúng project. Khoá dùng được ở
local đều trỏ project thử (xem Impact), và anh Tuấn đã chốt 12/09 rằng giai đoạn phát triển lệch
chút không sao. Phải mở lại trước khi lên server.

## Capabilities

### New Capabilities
- `agent-outage-alerting`: Người vận hành phải được báo khi agent đổi đường gọi vì hạ tầng hỏng,
  và thư báo phải gộp theo sự cố chứ không theo lượt gọi.

### Modified Capabilities
- `agent-gateway-resilience`: Thêm yêu cầu agent **tự chuyển sang nhà cung cấp** khi mất Gateway.
  Capability này hiện chỉ đòi "không mất dòng, không đếm đôi" khi Gateway mất — tức chấp nhận lô
  bị bỏ và chạy lại sau. Yêu cầu mới mạnh hơn: lô đó phải **chạy xong ngay**, không chờ lần sau.

## Impact

**Mã nguồn** — bản clone `D:\RangDonk\CRM-Classification-Pipeline`, được anh Tuấn cho phép sửa
ngày 12/09 (trước đó bị cấm):

| Tệp | Việc |
|---|---|
| `src/llm.py` | máy trạng thái hai nấc, lọc loại lỗi, ghi lượt đi đường thẳng |
| `src/notification.py` | thêm đường gửi SMTP cạnh đường Graph |
| `src/config.py` | khai các biến mới |
| `.env` | tệp mới, hiện chưa tồn tại |

**Ba project trong cùng một câu chuyện**, đã đo ngày 12/09 và phải ghi đủ cả ba:

```
   crm-500509        project THẬT của agent 7, đang ghi trong dim_agent
   crm-test-508114   project THỬ, chứa sa-key.json — gọi thật trả 200
   60854134008       project của khoá Vertex express đang dùng ở Gateway
```

**Bẫy đã đo:** khoá `KEY_BENCH_CRM_TEST_GG_AIA_STU` dạng `AQ.` là khoá **Vertex express**, không
phải AI Studio. Nó trả 200 trên `aiplatform.googleapis.com` và **403** trên
`generativelanguage.googleapis.com`. Nhánh gọi bằng khoá của CRM dựng client mặc định đi AI Studio,
nên đổ khoá này vào đó sẽ hỏng.

**Dashboard:** lượt gọi đi đường thẳng không vào sổ Gateway, nên `fact_call` sẽ thiếu chúng. Chúng
vẫn về qua hoá đơn nếu khoá thuộc một project đã khai trong `dim_agent` — điều hiện **chưa** đúng.

**Không đụng tới:** repo `token-ledger-dashboard`, cấu hình Gateway, và agent DMS.
