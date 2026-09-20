## Why

Hôm nay không có gì chặn chi tiêu: Gateway cứ nhận request là chuyển đi, tiền tiêu tới đâu chỉ
biết khi đọc sổ hoặc khi hoá đơn Google về. Ghi chú đo ngày 08/09 trong `config.gateway.yaml` nói
thẳng — cả hai virtual key đều không đặt `tpm/rpm/max_parallel_requests/max_budget`, nên **bỏ giới
hạn không có gì để thi hành**. Một agent hỏng, một vòng lặp thử lại, hay một đợt chạy lô lỡ tay là
đủ đốt hết ngân sách của project mà không ai biết cho tới lúc muộn.

Change này đặt cho mỗi project một hạn mức tiền do người nhập, cảnh báo khi gần hết, và **dừng hẳn
lưu lượng** khi đã hết — cho tới khi có người nạp thêm.

## What Changes

- Hạn mức và lịch sử nạp lưu trong **`metadata` của virtual key**, sửa qua `/key/update` của
  LiteLLM. Không bảng mới, không migration, không đụng schema của ai.
- Hạn mức **không tự reset theo chu kỳ**: hết thì người quản trị nạp thêm, và mỗi lần nạp để lại
  một dòng trong chính metadata đó.
- Thêm tab **Setting** trên dashboard: mỗi project một ô nhập, danh sách project đọc từ database.
- Thêm hai endpoint ghi đầu tiên cho `backend/`: `POST /api/quota` và `POST /api/quota/top-up`.
  Chúng **không ghi database** — chúng gọi tiếp sang LiteLLM. Kỷ luật chỉ-đọc của database giữ
  nguyên, nhưng backend phải cầm master key của Gateway, và đó là một quyền mới.
- Gateway chặn request khi số đã tiêu của khoá đã vượt hạn mức trong metadata của chính khoá đó.
  Hai kiểu trả lời, chọn theo tag agent:
  - agent có người chat → trả **HTTP 200** mang một câu thông báo, đúng hình dạng câu trả lời của
    model (hook trả về một `RejectedRequestError`, LiteLLM dựng câu trả lời từ đó);
  - agent chạy theo lô → trả **429** kèm chuỗi `429`, để app tự lùi thay vì nhận văn xuôi rồi hỏng
    khi phân tích JSON.
- Mỗi lượt bị chặn ghi **một dòng JSON ra log của container**, đủ để truy nguyên: thời điểm, agent,
  project, model, hạn mức, đã tiêu, kiểu trả lời.
- Cảnh báo qua email ở ba bậc 90% / 100% / đã vượt, mỗi bậc gửi đúng một lần khi bậc đổi. Dùng lại
  khuôn của `scripts/watch_gateway.py` (đã có SMTP, đã có file trạng thái, đã chỉ gửi khi đổi trạng
  thái).
- Trang nhập khoá của dashboard đổi từ một khối nhỏ trong luồng trang thành **trang phủ toàn màn
  hình**; chưa nhập khoá thì không thấy gì ngoài ô nhập.

Không làm trong change này: quota theo từng người dùng (đã cân nhắc và bỏ — chỉ quản ở cấp
project), tự động reset theo tháng, bảng lưu lượt bị chặn để báo cáo theo ngày, và mọi thay đổi
trong mã nguồn của các agent hay của LiteLLM.

## Capabilities

### New Capabilities
- `project-quota-budgets`: hạn mức tiền theo project — nơi lưu, cách nhập, cách nạp thêm, lịch sử
  nạp, và đường ghi có kiểm soát từ dashboard xuống Gateway.
- `quota-enforcement`: quyết định cho qua hay chặn ở Gateway, hai kiểu trả lời theo loại agent, và
  bản ghi của mỗi lượt bị chặn.
- `quota-threshold-alerting`: cảnh báo email ở ba bậc, chống gửi lặp, và nội dung thư đủ để người
  nhận biết phải làm gì.
- `dashboard-sign-in-gate`: cổng khoá phủ toàn màn hình trước khi dashboard hiện ra.

### Modified Capabilities
- `api-access-control`: yêu cầu hiện tại chỉ nói về endpoint **đọc**. Nay phải nói rõ endpoint ghi
  cũng đòi chứng danh; ghi lại quyết định đã chốt là dùng **chung một khoá** cho cả đọc lẫn sửa hạn
  mức; và ràng buộc mới quanh việc backend giữ master key của Gateway.

`read-only-api-durability` **không đổi**: database vẫn chỉ-đọc hoàn toàn, không vai mới, không bảng
mới. Đây là kết quả trực tiếp của việc lưu hạn mức trong metadata thay vì trong một bảng riêng.

## Impact

**Mã nguồn**
- `backend/main.py` — hai endpoint ghi đầu tiên, dùng lại `caller()` sẵn có; một client gọi sang
  LiteLLM
- `web/index.html`, `web/js/app.js`, `web/js/api.js` — tab Setting, cổng khoá phủ toàn màn hình
- Một hook của LiteLLM, gắn vào container bằng `volumes` và khai trong
  `docker/gateway/config.gateway.yaml`
- `scripts/` — tiến trình cảnh báo quota, theo khuôn `watch_gateway.py`
- `docker-compose.yml` — một dịch vụ chạy nền cho cảnh báo; gắn file hook; biến môi trường cho
  master key mà backend dùng

Không đụng: `db/migrations/`, `db/connect.py`, `docker/read-only-api.sql`, `backend/store.py`, và
mã nguồn của LiteLLM.

**Phạm vi thi hành có giới hạn, phải nói rõ với người dùng**
Gateway chỉ chặn được thứ đi qua nó. Hôm nay là **Phân Loại Phản Hồi Tiếp Thị** và **Phân Loại Dữ
Liệu CRM**. Sáu agent còn lại vẫn gọi thẳng Google: hạn mức của chúng chỉ là đèn báo và email, không
chặn được gì. Riêng **Phân Loại Dữ Liệu CRM** còn một đường lui đi thẳng Google bằng `sa-key.json`
(change `keep-the-crm-agent-running-when-the-gateway-dies`) — khi nó rơi vào đường đó thì hạn mức
cũng không chặn được.

**Độ chính xác đã chấp nhận**
Chi phí của một request chỉ biết sau khi gọi xong, nên luật thi hành là *đã tiêu ≥ hạn mức thì chặn
lượt kế tiếp*. Cộng thêm: khoá được nhớ đệm 300 giây, nên số đã tiêu mà hook nhìn thấy có thể cũ
tới 5 phút. Hệ quả: luôn vượt một khoản nhỏ. Đã chốt là chấp nhận, không đặt ngưỡng chặn sớm.

**Tiền đề cũ bị đổi**
Ghi chú ở `backend/main.py` (quyết định 21/08/2026) lập luận không cần phân vai vì *"8/8 endpoint là
GET, 0 hành động đặc quyền"*. Change này tạo ra hành động đặc quyền đầu tiên, nên ghi chú đó phải
được sửa lại cho khớp chứ không để nguyên.

**Không dùng tính năng trả phí nào**
Đã kiểm: `auth/auth_checks.py`, `router.py` và `router_strategy/tag_based_routing.py` đều có **0**
chỗ kiểm giấy phép. Chỗ duy nhất liên quan là trường `tags` cấp cao của `/key/generate` và
`/key/update` — dự án không dùng trường đó, tag nằm trong `metadata.tags`, và đường đó đã chạy thật
từ 31/08/2026.
