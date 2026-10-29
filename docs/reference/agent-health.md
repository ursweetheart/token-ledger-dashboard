# Sức khỏe Agent

Tab **🩺 Sức khỏe Agent** cho biết từng agent còn trả lời được không, và luồng gọi model của nó còn
chạy không. Thiết kế: `openspec/changes/add-agent-health-tab/design.md`.

## Chạy như thế nào

```
service agent-health-watch (vòng 5 giây)
  ① có lần "Chạy ngay" đang chờ?  → chạy
  ② không thì: giờ VN đã qua giờ đặt và hôm nay lịch chưa chạy? → chạy
  mỗi lần chạy: gọi từng phép kiểm trong config/agent-health.yaml, ghi kết quả vào database
```

- **Lịch:** một lần mỗi ngày, vào giờ đặt trên tab (giờ Việt Nam). Container khởi động lại sau khi
  đã chạy thì không chạy lần hai. Container lên trễ (ví dụ đặt 08:00, lên lúc 09:00) thì chạy bù ngay.
- **Chạy ngay:** chạy tất cả phép kiểm ngay lập tức. **Không ảnh hưởng tới lịch**: bấm lúc 07:00 thì
  08:00 lịch vẫn chạy.
- **Một lúc chỉ có một lần chạy.** Bấm khi đang chạy thì nút bị tắt; ai gọi API thẳng thì nhận 409.
  Database giữ luật này (index duy nhất), không phải code.
- Apply và Chạy ngay cần **khoá quản trị kết nối** (giống tab Kết nối agent). Khoá đọc dashboard chỉ
  xem được. Máy không bật `CONNECTIONS_ENABLED=1` thì hai nút trả 503. Khi đó dùng
  `docker compose exec agent-health-watch python3 scripts/watch_agents.py --once`.

## Ba mức kết quả

| Mức | Nghĩa |
|---|---|
| ✅ đạt | mọi điều kiện trong YAML đều đúng |
| ⚠️ cảnh báo | agent trả 429 (bị giới hạn request hoặc hết AI budget, chưa phải chết), hoặc key sắp hết hạn |
| ❌ lỗi | mọi thứ khác: mạng, timeout, mã HTTP sai, điều kiện sai, **thiếu biến key** |

Thiếu biến key thì là ❌, không bị bỏ qua. Bỏ qua thì tab trông như "không có lỗi".

## Thanh tiến độ đứng ở 50% lâu: không phải treo

Thanh đếm **số phép kiểm đã xong**, không đếm thời gian. Trợ lý ảo Ralli có 2 phép kiểm, nên thanh đi
0% → 50% → 100%. Phép kiểm thứ hai gọi LLM và có thể chờ tới 180 giây. Dòng "Đang kiểm: … (N giây)"
cho biết nó vẫn đang chạy.

## Thêm một agent mới

1. Thêm một khối dưới `agents:` trong `config/agent-health.yaml`: `name`, `base_url`,
   `auth: {header, env}`, `checks`. Khuôn và giải thích ở đầu file đó.
2. Mỗi phép kiểm `POST` phải có path trong `allow_post` của agent. **Mỗi POST là một ngoại lệ của luật
   chỉ-đọc: hỏi người phụ trách trước khi thêm.** Thiếu thì service từ chối khởi động.
3. Thêm biến key vào `.env`, vào `.env.example` (để trống), và vào `environment:` của
   `agent-health-watch` trong `docker-compose.yml`.
4. Agent đã đi qua Gateway thì thêm `gateway_tag: <tag>`, để service đối chiếu thêm một bước với sổ
   Gateway (phép kiểm `gateway-log`).
5. Khởi động lại service: `docker compose --profile gateway up -d agent-health-watch`. YAML chỉ được đọc
   lúc khởi động. Đổi `scripts/watch_agents.py` thì phải build lại image `tools`, vì script được chép vào
   image.

Kiểm trước khi bật thật:
`docker compose run --rm agent-health-watch python3 scripts/watch_agents.py --dry-run`. Lệnh này chỉ gọi
`GET`, in kết quả, không ghi gì.

## Những điều phải biết

- **Mỗi lần chạy tốn một lần gọi LLM** (`POST /ctda/v2/analyze` của Ralli). Người dùng duyệt ngày
  29/10/2026: một lần theo lịch, cộng mỗi lần bấm Chạy ngay; dự kiến 1–3 lần mỗi ngày.
- **Token của lần kiểm tính cho tài khoản gắn với key.** Key Ralli hiện gắn tài khoản `admin`, nên
  dashboard sẽ thấy `admin` gọi một câu mỗi ngày.
- **Key Ralli hiện có đủ 11 quyền**, kể cả `chat:ask`, quyền này mở được `DELETE /conversations/{id}`.
  Nên xin quản trị Ralli một key **chỉ có `action:ctda`**, gắn một tài khoản riêng. Đổi key chỉ cần sửa
  `.env`, không sửa code.
- **Câu chào không kiểm được LLM.** Ngày 29/10/2026, `"hello"` trả HTTP 200 và `success` sau 0,19 giây,
  với `data.feature = "clarification"`, mà không đi tới LLM. Vì vậy YAML đòi
  `data.feature != clarification`. Nếu câu hỏi thử hiện tại cũng bị trả lời như vậy, phép kiểm `llm` sẽ
  báo ❌; khi đó đổi câu trong YAML.
- **Chỉ chạy một bản service.** Lúc khởi động, vòng lặp đánh dấu mọi lần chạy dở là `interrupted`, để
  nút Chạy ngay không bị khoá mãi sau khi container chết. Hai bản cùng chạy thì bản sau ngắt nhầm bản
  trước. `container_name` cố định chặn chuyện này trong compose. **Đừng chạy vòng lặp
  `watch_agents.py` ngoài container** khi service đang lên. `--once` và `--dry-run` thì được.
- **Tab báo "hôm nay đã qua giờ chạy nhưng lịch chưa chạy"** nghĩa là service không chạy hoặc không
  tới được database. Xem `docker logs token-ledger-agent-health-watch`.
- **Kết quả nằm ở hai nơi, cùng một tài liệu JSON:** cột `agent_health_run.result` và tệp
  `var/agent-checks/<run_id>/result.json` (chỉ có khi lần chạy xong). Khuôn tài liệu:
  `docs/reference/agent-health-result.md`.
- **Phép kiểm có câu hỏi giữ nguyên câu hỏi và nguyên response của agent** làm bằng chứng (chốt
  29/10/2026). Response có thể chứa dữ liệu nghiệp vụ: tab chỉ hiện mã HTTP, thời gian và lý do;
  `var/agent-checks/` nằm trong `.gitignore`. Phép kiểm health không giữ response.
- Chưa có bước tự xoá `var/agent-checks/` cũ. Mỗi lần chạy một thư mục, vài KB.
