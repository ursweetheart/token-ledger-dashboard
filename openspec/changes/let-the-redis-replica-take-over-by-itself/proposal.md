# Redis replica phải tự lên thay, không cần người

## Why

`docker-compose.yml:365` ghi thẳng giới hạn:

> `NOI RO GIOI HAN: chua co Sentinel. Primary chet thi replica KHONG tu len thay - phai doi tay.`

Kế hoạch GĐ5 dòng 13 yêu cầu *"Redis 1 primary + 1 replica"*. Bản sao đã có, phần **tự
thay thế** thì chưa.

### Đã đo trước khi quyết, và số liệu nói mức độ nghiêm trọng là THẤP

Ghi lại đây để người sau biết quyết định này được đưa ra với mắt mở, không phải vì tưởng
Redis là điểm chết cứng. Đo ngày 07/09/2026:

| Câu hỏi | Đo được |
|---|---|
| Tắt hẳn Redis thì Gateway còn phục vụ không? | **Còn.** 9/10 lượt HTTP 200, p50 0,87 s |
| Giá phải trả khi mất Redis | **một lần 5,12 s** lúc client phát hiện mất kết nối, sau đó bình thường |
| Bật Redis lại có phải làm gì không? | **Không.** 0 lỗi tồn dư, replica tự nối lại master |
| Redis đang giữ gì | bộ đếm `rpm`/`tpm` — **quan sát được**, TTL 60 s; và tuyến bị phạt nguội — **đọc từ mã nguồn**, TTL 30 s, chưa quan sát được vì lúc đo không tuyến nào bị phạt |
| Khi không có lưu lượng | `dbsize` = **0** — Redis rỗng hoàn toàn |

Tức thứ mất đi khi Redis chết là **nhiều nhất một phút bộ đếm**, và nó tự dựng lại từ lưu
lượng bình thường.

Và cửa sổ mà "không tự thay thế" thật sự có nghĩa cũng hẹp:

| Kịch bản | Replica có cần thăng cấp không |
|---|---|
| Redis chết bình thường | **Không** — `restart: unless-stopped` tự dựng lại |
| Redis hỏng vĩnh viễn **mà máy vẫn sống** | **Có** — đây là kịch bản duy nhất |
| Máy chết | **Không** — replica chết theo |

### Vì sao vẫn làm

Quyết định của anh Trần Xuân Tuấn sau cuộc họp 07/09/2026, khi đã nghe đủ số liệu trên.
Lý do chính đáng dù mức nghiêm trọng thấp:

- **Nó là một điều khoản của kế hoạch chưa hoàn thành.** Để nợ một mục GĐ5 tới lúc nghiệm
  thu là tự tạo việc vào đúng lúc bận nhất.
- **Chi phí sửa thấp hơn chi phí giải thích.** Mỗi lần có người đọc dòng chú thích đó lại
  phải giải thích lại vì sao không đáng lo.
- **Nó là bài tập thật cho một cơ chế sẽ cần lại.** Postgres cũng đang một bản; làm quen
  với failover ở chỗ rẻ trước khi phải làm ở chỗ đắt.

## What Changes

- **Chuyển Redis sang file cấu hình.** Đây là **điều kiện tiên quyết**, không phải chi
  tiết — xem `design.md` §1. Hiện cả hai Redis chạy hoàn toàn bằng cờ dòng lệnh và replica
  mang `--replicaof redis 6379` ghi cứng, nên mọi lần Sentinel thăng cấp đều bị xoá sạch
  khi container dựng lại.
- **Thêm 3 tiến trình Sentinel.** Số lẻ để có quorum.
- **Đổi khai báo Redis trong `config.gateway.yaml`** từ `redis_host`/`redis_port` sang
  `sentinel_nodes` + `service_name`. LiteLLM có hỗ trợ sẵn — `litellm/_redis.py:394` đọc
  `sentinel_nodes`, `:408` đọc `service_name`, `:401` đọc `sentinel_password`.
- **Nghiệm thu bằng một lần giết primary thật**, không phải bằng "Sentinel khởi động được".

**KHÔNG làm trong change này**

- **Không giải quyết chuyện máy chết.** Ba sentinel trên cùng một máy thì máy chết là chết
  cả ba. Change này chỉ chống được kịch bản "Redis hỏng vĩnh viễn mà máy còn sống".
- Không bật cache trả lời (`config.gateway.yaml:91` vẫn comment — lý do ở đó).
- Không đụng Postgres, không đụng `db/`, không đụng dashboard.
- Không đổi `routing_strategy`, không đổi `rpm`/`tpm`.

## Impact

| | |
|---|---|
| **Specs** | `gateway-shared-state-continuity` (mới) |
| **Code** | `docker-compose.yml` · `docker/gateway/config.gateway.yaml` · `docker/gateway/redis/*.conf` (mới) |
| **Không đụng** | `db/` · `backend/` · `web/` · `scripts/` |
| **Rủi ro** | **Trung bình, và cao hơn mức lợi ích.** Sentinel cấu hình sai gây split-brain — hai Redis cùng nhận ghi — tệ hơn hẳn trạng thái hiện tại. Xem `design.md` §5 |
| **Quay lui** | Giữ nguyên khối cấu hình cũ dưới dạng comment; gỡ 3 sentinel và trả `redis_host` về là xong |
| **Thời điểm** | **Phải xong trước 13/09.** Từ 14/09 là cửa sổ đối chiếu, có luật không đổi cấu hình Gateway |

### Cái bẫy chính của change này

Sentinel dựng xong **trông như đang chạy** kể cả khi nó vô dụng: tiến trình lên, log đẹp,
`SENTINEL masters` trả về đúng. Nhưng nếu Redis vẫn chạy bằng cờ dòng lệnh thì lần thăng
cấp đầu tiên sẽ bị xoá lúc container dựng lại, và **không ai biết cho tới khi cần đến nó**.

Cùng một hạng lỗi với `enable_tag_filtering` hôm 30/08: mặc định tắt, thiếu thì `tags` bị
bỏ qua HOÀN TOÀN và IM LẶNG. Nghiệm thu phải là **giết primary thật rồi xem có ai đỡ
không**, không phải xem tiến trình có lên không.
