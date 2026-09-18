## Why

Ngày 14/09, `agent-outage-alerting` được đặt ra với **một actor duy nhất: chính agent**. Agent đổi
đường thì agent gửi thư. Đến 17/09, đúng **1 trong 8** agent có mã ấy —
`CRM-Classification-Pipeline/src/llm.py:263` và `:279`. Bảy agent còn lại, Gateway chết là im lặng
hoàn toàn, đúng cái im lặng ngày 10/09 mà capability ấy sinh ra để chấm dứt.

Nhân số ra thì cách cũ đắt: 8 repo phải sửa, 8 nơi cấu hình SMTP, 8 lần nghiệm thu bằng một thư
thật, và 8 chỗ có thể trôi khỏi nhau mà không ai biết.

**Ba điều một chỗ canh ngoài làm được mà agent không làm được:**

1. **Báo cả khi không agent nào đang chạy.** Thư của agent chỉ tồn tại nếu lúc ấy có một lô đang xử
   lý. Gateway chết lúc 2 giờ sáng thì không ai được báo cho tới sáng — và lúc đó nó có thể đã sống
   lại, không để lại dấu vết nào ngoài log. Lô 6 giờ sáng thì đã chạy trên hạ tầng hỏng rồi.
2. **Thấy `degraded` — thứ agent không bao giờ nói.** Một instance chết thì load balancer đẩy hết
   sang instance kia. Agent chạy trơn tru, không đổi đường, không ghi một dòng nào. Mất một nửa năng
   lực xử lý, im lặng tuyệt đối.
3. **Gửi thư hỏng không thể làm hỏng việc chính — theo cấu trúc, không theo mã.** Spec hiện đòi điều
   này và hiện phải dùng `try/except` ở `llm.py:292` để giữ. Đưa việc gửi thư sang một container
   không làm gì khác thì yêu cầu ấy đúng vì **không có việc chính nào ở đó để hỏng**.

**Agent giữ nguyên fallback.** Máy trạng thái hai nấc là thứ giữ cho lô chạy tiếp; nó không đổi. Chỉ
bỏ phần gửi thư.

**Phép dò thì không viết lại.** Commit `d0d8ff4` vừa thêm `gateway-status`, và nó **đã dò sẵn** bốn
thành phần rồi. Change này lấy kết quả ấy và biến nó thành thư — chứ không dựng một bộ dò thứ hai
cạnh bộ đã có.

## What Changes

- **Dịch vụ mới `gateway-watch`** trong `docker-compose.yml`, profile `gateway`, dùng lại image
  `token-ledger-tools:local` và đúng khuôn của `ledger-refresh` — không cron, không Dockerfile mới,
  không gói phụ thuộc mới. **Không `ports`, không `expose`**: nó là khách, không phải máy chủ.
- **`scripts/watch_gateway.py --every N`**: dò, so trạng thái với lần trước, gửi thư khi **đổi trạng
  thái**. Chỉ `urllib` + `smtplib` của thư viện chuẩn.
- **Ba đích dò, mỗi đích phủ một lớp khác nhau** (D3):

  | | Đích | Phủ lớp |
  |---|---|---|
  | (A) | `https://<tên miền>/lb-health` | DNS, TLS, proxy máy chủ, nginx còn sống |
  | (B) | `gateway-status:8089/api/status` | từng instance, `degraded` hay `unavailable` |
  | (C) | `gateway-lb:4000/health/readiness` | LiteLLM sẵn sàng, `db: connected` |

- **Máy trạng thái ba nấc**, không hai: `reachable` / `degraded` / `unavailable` — theo đúng cách
  `gateway-status` đã gộp.
- **Mọi đích đọc từ biến môi trường, không ghim trong mã.** Cùng một tệp chạy được cả bản trong
  container lẫn bản trên máy khác (D11).
- **Nhịp mặc định 60 giây, không 300** (D2). Phép dò miễn phí nên cửa sổ mù là thứ ta tự chọn.
- **Trạng thái ghi ra tệp**, không giữ trong bộ nhớ (D5).
- **Một thư nhịp tim mỗi ngày** (D7). Sau change này, canh gác là nguồn báo động duy nhất.
- **Một ghi chú bàn giao** trong `docs/reference/`: cái gì gỡ khỏi agent, cái gì bắt buộc giữ, và
  điều kiện trước khi gỡ.
- **Spec `agent-outage-alerting` đổi actor**, không xoá.

**Giữ nguyên, có chủ ý:**

- **Không gọi thật, kể cả bằng khoá miễn phí.** Năm lý do ở D1. Lý do nặng nhất: nó chứng minh cho
  **khoá của chính nó**, trên một model không agent nào dùng. Lối thay thế — đọc kết cục thật đã có
  trong sổ — là một change riêng.
- **Không nới `LLM_GATEWAY_ADMIN_CIDR`, không đổi bind của bất kỳ dịch vụ nào.** Đặt canh gác trong
  mạng thì câu hỏi ấy không phát sinh (D12).
- **Không đụng `nginx.conf`, không đụng `gateway-status`, không đụng fallback của agent.**
- **Không đụng repo agent nào.** Chốt 17/09: change này chỉ làm phần gửi thư của watcher. Mã gửi thư
  trong agent do **leader** gỡ sau, khi watcher đã chạy và đã được tin. Ở đây chỉ để lại ghi chú bàn
  giao. Trong giai đoạn chuyển tiếp, một sự cố sẽ sinh thư từ **cả hai** nguồn — đó là dự tính, và
  còn có lợi: thư của CRM mang con số watcher không biết được (D8).
- **Chưa canh dashboard.** `token-ledger-web` chạy suốt còn `gateway-lb` chạy theo profile; gộp bây
  giờ thì trên máy phát triển chuông sẽ gào mỗi lần tắt Gateway. Danh sách đích nằm trong biến nên
  thêm sau là sửa `.env`, không sửa mã.
- **Chưa dựng bản trên máy khác.** Hợp đồng biến đã định sẵn cho nó (D11); dựng là một lần triển
  khai nữa, không phải một lần viết lại.

## Capabilities

### New Capabilities

- `gateway-liveness-watch`: Một tiến trình đứng ngoài agent dò Gateway theo nhịp, báo thư khi trạng
  thái đổi chứ không khi mỗi lần dò hỏng, không mở thêm cổng nào, đọc đích dò từ cấu hình để chạy
  được cả trong lẫn ngoài máy chủ, và tự chứng minh nó còn sống.

### Modified Capabilities

- `agent-outage-alerting`: Actor đổi từ **agent** sang **tiến trình canh gác**. Agent vẫn phải ghi
  log mỗi lần đổi đường; nó thôi không còn phải gửi thư.

## Impact

| Vùng | Việc |
|---|---|
| `scripts/watch_gateway.py` | tệp mới |
| `docker-compose.yml` | dịch vụ `gateway-watch`, ~20 dòng theo khuôn `ledger-refresh` |
| `.env.example` | `WATCH_NAME`, `WATCH_EVERY_SECONDS`, `WATCH_HTTP`, `WATCH_STATUS_URL`, SMTP |
| `var/` | tệp trạng thái, phải nằm trong `.gitignore` |
| `docs/reference/` | thư báo gì, **không** báo gì, ba trần đã biết, và ghi chú bàn giao |

**Không đụng tới:** `docker/gateway/nginx.conf`, `tools/gateway-status/`, `backend/store.py`,
`.github/workflows/ci.yml`, mọi bind/ACL đang có, **và mọi repo agent**.

**Một con số sẽ mất, cách xử ở D8.** Thư của agent hiện mang ba thứ chỗ canh ngoài không biết được:
project nào trả tiền, **bao nhiêu lượt** đã đi đường thẳng, và câu lỗi cuối cùng từ Gateway.

**Rủi ro phải đo trước, không đoán:** (A) gọi tên miền public từ **trong** cùng máy chủ. Nhiều router
không cho vòng lại (hairpin NAT). Không quay về được thì (A) đỏ mỗi phút dù hệ thống khoẻ — báo động
giả liên tục. Đo ở `tasks.md` mục 0.
