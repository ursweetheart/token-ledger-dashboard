# Thiết kế — Redis replica tự lên thay

## Bối cảnh

Hiện trạng, đo 07/09/2026:

```
   redis            primary, --appendonly yes, maxmemory 256mb, noeviction
   redis-replica    --replicaof redis 6379, --replica-read-only yes
   (không có Sentinel)

   Nội dung Redis:
     <hash>:<model>:rpm:<HH-MM>          TTL 60   ← bộ đếm request theo phút
     <hash>:<model>:tpm:<HH-MM>          TTL 60   ← bộ đếm token theo phút
     deployment:<model_id>:cooldown      TTL 30   ← tuyến đang bị phạt nguội
```

Hai loại đầu **quan sát trực tiếp** được: gọi 2 lượt thì 4 khoá xuất hiện, giá trị `rpm=2`
`tpm=18`, TTL đếm lùi 59 → 53 sau 6 giây. Lúc không có lưu lượng, `dbsize` = **0**.

Loại thứ ba **đọc từ mã nguồn, chưa quan sát được** — trong lúc đo không tuyến nào bị phạt.
Tên khoá lấy ở `litellm/router_utils/cooldown_cache.py:108`
(`"deployment:" + model_id + ":cooldown"`); TTL bằng đúng `cooldown_time` vì
`add_deployment_to_cooldown()` gọi `set_cache(..., ttl=_cooldown_time)`.

## Mục tiêu

Khi tiến trình Redis primary chết vĩnh viễn mà máy còn sống, replica **tự lên thay không
cần người**, và LiteLLM **tự đi theo master mới** — không phải sửa cấu hình, không phải
khởi động lại instance nào.

## Không phải mục tiêu

- Chống máy chết. Ba sentinel cùng một máy thì máy chết là hết. Nói rõ ở đây để không ai
  đọc change này rồi tưởng đã có HA.
- Giảm độ trễ, tăng thông lượng, hay bất cứ chuyện hiệu năng nào.

## Quyết định

### 1. Chuyển Redis sang file cấu hình — điều kiện tiên quyết, không phải tuỳ chọn

Hiện cả hai Redis chạy **hoàn toàn bằng cờ dòng lệnh**, không có file `.conf` nào trong
repo. Replica mang `--replicaof redis 6379` ghi cứng ở `docker-compose.yml:375-377`.

Vì sao điều đó giết Sentinel:

```
   Sentinel thăng replica lên master
        → nó gửi lệnh REPLICAOF NO ONE
        → Redis muốn GHI LẠI trạng thái mới vào file cấu hình của chính nó
        → KHÔNG CÓ FILE NÀO để ghi
        → trạng thái chỉ tồn tại trong bộ nhớ

   container dựng lại (restart: unless-stopped, reboot, compose up)
        → cờ `--replicaof redis 6379` áp lại từ đầu
        → nó tụt về làm replica của master CŨ vừa bị hạ
        → lần thăng cấp coi như chưa từng xảy ra
```

**ĐÃ ĐO 07/09/2026, không phải suy luận.** Chạy thẳng trên `token-ledger-redis-replica`,
giả lập đúng thứ Sentinel sẽ làm:

```
   1. vai trò ban đầu                             role:slave
   2. sau `REPLICAOF NO ONE` (Sentinel thăng cấp) role:master   ← thăng cấp có tác dụng
   3. sau `docker restart` container              role:slave    ← BỊ XOÁ SẠCH
```

Bước 3 là bằng chứng: cờ dòng lệnh thắng, và kết quả thăng cấp biến mất. Replica sau đó
nối lại master bình thường (`master_link_status:up`), nên phép thử này không để lại hậu quả.

Nên bước đầu tiên là đưa cả `redis` lẫn `redis-replica` sang `redis.conf` /
`redis-replica.conf` nằm trên **volume ghi được**, và bỏ hết cờ dòng lệnh tương ứng.

**Đây là chỗ dễ bỏ sót nhất của cả change.** Bỏ qua nó thì mọi thứ còn lại vẫn dựng được,
vẫn chạy được, và vẫn vô dụng — im lặng.

### 2. Ba sentinel, không phải một

Sentinel quyết định thăng cấp bằng **quorum**. Một sentinel thì không có quorum, nó chỉ là
một điểm chết mới. Ba là số lẻ nhỏ nhất cho phép mất một mà vẫn quyết được.

`quorum = 2`: cần hai sentinel cùng đồng ý là primary đã chết mới thăng cấp. Đặt 1 thì một
sentinel bị lỗi mạng thoáng qua có thể tự ý thăng cấp — sinh split-brain.

**Thành thật về giới hạn:** ba sentinel trên cùng một máy chỉ chống được *tiến trình Redis*
chết, không chống được *máy* chết. Đây là điều được chấp nhận có ý thức, không phải sơ suất.

### 3. LiteLLM nói chuyện với Sentinel, không nói thẳng với Redis

`litellm/_redis.py` đã hỗ trợ sẵn, không cần vá gì:

| Tham số | Đọc ở | Từ biến môi trường |
|---|---|---|
| `sentinel_nodes` | `_redis.py:394` | `REDIS_SENTINEL_NODES` |
| `sentinel_password` | `_redis.py:401` | `REDIS_SENTINEL_PASSWORD` |
| `service_name` | `_redis.py:408` | `REDIS_SERVICE_NAME` |

Trong `config.gateway.yaml`, khối `router_settings` đổi từ:

```yaml
  redis_host: redis
  redis_port: 6379
```

sang khai `sentinel_nodes` + `service_name`. Giữ nguyên khối cũ **dưới dạng comment kèm
ngày**, theo đúng thói quen của file này — nó là đường quay lui trong một phút.

### 4. Mật khẩu phải khai ở ba chỗ, thiếu một là hỏng im

Redis đang bật `requirepass`. Khi có Sentinel, mật khẩu phải có mặt ở:

```
   requirepass        trên cả primary lẫn replica   (đã có)
   masterauth         trên replica                  (đã có)
   sentinel auth-pass trong cấu hình sentinel        ← MỚI, thiếu là sentinel
                                                       không giám sát được
```

Và `masterauth` phải có trên **cả hai** Redis, không chỉ replica: sau khi thăng cấp, vai
trò đảo ngược — primary cũ sẽ thành replica và cần `masterauth` để nối vào master mới.
Hiện `redis` (primary) **không có** `masterauth`. Đây là lỗi sẽ chỉ lộ ra ở lần failover
thứ nhất.

### 5. Nghiệm thu phải là giết thật, không phải "tiến trình lên"

Sentinel dựng sai vẫn trông y như dựng đúng: log sạch, `SENTINEL masters` trả về đúng,
`docker ps` xanh cả ba. Nên phép kiểm phải đi qua một lần chuyển vai thật:

```
   1. ghi mốc: ai đang là master (SENTINEL get-master-addr-by-name)
   2. docker kill redis (giết CỨNG, không phải stop — stop là chết có báo trước)
   3. đo bao nhiêu giây thì SENTINEL trỏ sang địa chỉ mới
   4. LiteLLM có tự đi theo không — gọi thật vài lượt, phải 200
   5. dựng lại redis cũ → nó phải vào làm REPLICA, tuyệt đối không phải master thứ hai
   6. restart container replica mới → nó phải VẪN là master   ← đây là phép kiểm của §1
```

Bước 6 là bước duy nhất chứng minh §1 đã làm đúng. Thiếu nó thì change này coi như chưa
nghiệm thu.

## Rủi ro và đánh đổi

**Split-brain — rủi ro thật và tệ hơn hiện trạng.** Hôm nay mất Redis chỉ tốn một lần 5
giây. Sau change này, cấu hình sai có thể cho ra **hai Redis cùng nhận ghi**, mỗi instance
LiteLLM đếm vào một cái. Lúc đó hạn mức bị đếm sai theo cách không ai phát hiện được. Đây
là lý do quorum = 2 và tại sao bước nghiệm thu 5 tồn tại.

**Thêm ba container để chống một sự cố hiếm.** Ba sentinel là ba thứ nữa phải vận hành,
phải cập nhật, phải hiểu khi đọc log. Đổi lại chúng chống được một kịch bản mà đo được là
gần như vô hại. Đánh đổi này **đã được nêu rõ và người quyết đã chấp nhận** — ghi ở
`proposal.md`.

**Cửa sổ thời gian.** Phải xong trước 13/09. Từ 14/09 có luật không đổi cấu hình Gateway
trong hai tuần đối chiếu; đổi giữa kỳ là đồng hồ đếm lại từ đầu.

## Câu còn mở

**Sau khi có Sentinel, `redis-replica` có còn nên `--replica-read-only yes` không?** Có —
nhưng sau khi thăng cấp, Sentinel phải gỡ cờ đó. Nếu nó nằm trong file cấu hình mà Sentinel
không ghi đè được thì master mới sẽ từ chối mọi lệnh ghi, tức failover thành công về hình
thức mà hỏng về thực chất. **Chưa kiểm.** Phải xác nhận trong lúc làm, và nó thuộc cùng họ
với §1.

**Có nên áp cùng cách này cho Postgres không?** Postgres nghiêm trọng hơn Redis nhiều —
LiteLLM tra hash khoá ảo ở đó **mỗi request**, và `token_ledger_v2` cũng nằm cùng máy đó.
Nhưng **chưa ai đo** Postgres chết thì Gateway còn phục vụ được không. Đó là việc riêng,
không kéo vào change này.
