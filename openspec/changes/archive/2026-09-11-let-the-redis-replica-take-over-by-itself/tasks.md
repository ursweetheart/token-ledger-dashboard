# Việc phải làm

Phải xong **trước 13/09**. Từ 14/09 là cửa sổ đối chiếu, có luật không đổi cấu hình Gateway.

## 1. Ghi mốc trước khi sửa

- [x] 1.1 `git status` sạch trên `docker/` và `docker-compose.yml` — **ĐO 07/09: sạch.** `git status --porcelain docker/ docker-compose.yml` trả rỗng
- [x] 1.2 Ghi lại hành vi hiện tại để cuối change chứng minh không làm nó tệ đi: tắt Redis
      → gọi thật 10 lượt → ghi tỷ lệ 200 và p50. **Mốc đo 07/09: 9/10 lượt 200, p50
      0,87 s, một lần phạt 5,12 s ở lượt đầu**
      → **DÙNG LẠI mốc đo cùng ngày**, không đo lại: mỗi lần đo tốn 10 lượt gọi Google thật
      và ăn vào hạn mức free tier 15 rpm. Trạng thái hệ không đổi giữa hai thời điểm
- [x] 1.3 Ghi lại `docker inspect` mem/cpu và `dbsize` của cả hai Redis — **ĐO 07/09:** `redis` CPU 4,40% MEM 4,34 MiB `dbsize=0` `role:master` · `redis-replica` CPU 1,02% MEM 3,77 MiB `dbsize=0` `role:slave`. `dbsize=0` là bình thường: mọi khoá có TTL ≤ 60 s nên lúc không lưu lượng Redis rỗng
- [x] 1.4 Sao lưu `docker/gateway/config.gateway.yaml` và `docker-compose.yml` — đã chép `docker-compose.yml` và `config.gateway.yaml` sang thư mục tạm; cả hai cũng đang được git theo dõi (`622b52b`) nên có hai lớp quay lui

## 2. Chuyển Redis sang file cấu hình — LÀM TRƯỚC, đây là điều kiện tiên quyết

Xem `design.md` §1. Bỏ qua nhóm này thì mọi thứ sau vẫn dựng được và vẫn vô dụng.

> **LỆCH SO VỚI THIẾT KẾ, phát hiện lúc bắt tay — 07/09.** Thiết kế nói "tạo
> `redis.conf`". Làm mới lộ ra hai ràng buộc kéo ngược nhau:
>
> 1. Redis **không nội suy biến môi trường** trong file cấu hình. `requirepass
>    ${REDIS_PASSWORD}` đặt mật khẩu thành đúng chuỗi đó.
> 2. Khi Sentinel đổi vai, Redis chạy `CONFIG REWRITE` và **ghi mật khẩu thật vào file**.
>    File nằm trong repo thì bí mật rơi vào git.
>
> Nên thành: repo giữ **bản mẫu** không có bí mật; `entrypoint.sh` sinh file thật **một
> lần** vào `/data` trên volume. Sinh lại mỗi lần khởi động sẽ xoá trạng thái Sentinel
> viết — tức tái lập đúng lỗi change này sinh ra để sửa.

- [x] 2.1 Tạo `docker/gateway/redis/redis.conf` mang đúng các tuỳ chọn đang ở dòng lệnh:
      `requirepass`, `appendonly yes`, `maxmemory 256mb`, `maxmemory-policy noeviction`
      → thành `redis.conf.template` + `entrypoint.sh`, lý do ở khung trên
- [x] 2.2 Tạo `docker/gateway/redis/redis-replica.conf` tương tự, kèm `replicaof redis 6379`
      và `replica-read-only yes`
      → thành `redis-replica.conf.template`
- [x] 2.3 **Thêm `masterauth` vào CẢ HAI file**, không chỉ replica. Sau khi thăng cấp vai
      trò đảo ngược: primary cũ sẽ thành replica và cần `masterauth` để nối vào master mới.
      Hiện `redis` không có — lỗi này chỉ lộ ở lần failover thứ nhất
      → **ĐO trước khi sửa: `redis` trả `masterauth` RỖNG.** Sau khi sửa: cả hai đều có
- [x] 2.4 Mount file cấu hình lên **volume ghi được**, KHÔNG phải `:ro` — Redis phải tự ghi
      lại được khi đổi vai
      → `/data/redis.conf` trên volume `redisdata`/`redisreplicadata`, xác nhận `test -w`
      cho **GHI ĐƯỢC**. Bản mẫu và entrypoint vẫn `:ro` — chúng không phải thứ Redis ghi lại
- [x] 2.5 Xoá hết cờ dòng lệnh tương ứng khỏi `docker-compose.yml`, đặc biệt `--replicaof`
- [x] 2.6 Dựng lại, xác nhận: cả hai lên khoẻ · `INFO replication` cho `role:master` và
      `role:slave` · `master_link_status:up` · `dbsize` hành xử như cũ
      → cả 4 mục ĐẠT. **Và đã chứng minh nhóm này thật sự sửa được lỗi** bằng đúng phép thử
      đã dùng để phát hiện nó: `REPLICAOF NO ONE` → `docker restart` →
      **trước khi sửa cho `role:slave`, sau khi sửa cho `role:master`**

## 3. Dựng ba Sentinel

- [x] 3.1 Tạo cấu hình sentinel: `sentinel monitor <ten> redis 6379 2` — quorum **2**, xem
      `design.md` §2 vì sao không phải 1
      → `sentinel monitor gateway-redis redis 6379 2` trong `sentinel.conf.template`
- [x] 3.2 Khai `sentinel auth-pass <ten> <mat khau>`. Thiếu dòng này thì sentinel không giám
      sát nổi Redis đang bật `requirepass`, và nó hỏng **im lặng**
- [x] 3.3 Mount cấu hình sentinel lên volume ghi được — sentinel cũng tự viết lại file của
      chính nó khi trạng thái đổi
      → mỗi sentinel một volume **riêng** (`sentinel1data`/`2`/`3`). Dùng chung một volume
      thì ba tiến trình giẫm lên file của nhau
- [x] 3.4 Thêm 3 service sentinel vào `docker-compose.yml`, cùng profile `gateway`
- [x] 3.5 Dựng lên, xác nhận cả ba cùng nhìn thấy một master:
      `SENTINEL get-master-addr-by-name <ten>` trả cùng một địa chỉ ở cả ba
      → **ĐẠT**: cả ba trả `redis:6379`. `SENTINEL master` cho `flags=master`,
      `num-slaves=1`, `num-other-sentinels=2` — mỗi sentinel thấy đủ hai cái kia
- [x] 3.6 **THÊM lúc làm — địa chỉ master phải là IP TĨNH, không phải tên service.**
      Đi hết hai bước mới ra:
      → *Lần 1:* khai tên service → cả ba crash-loop, `FATAL CONFIG FILE ERROR ...
      Can't resolve instance hostname`. Sentinel mặc định **chỉ nhận IP**.
      → *Lần 2:* bật `sentinel resolve-hostnames yes` → dựng lên được, ba sentinel đồng
      thuận. Nhưng **giết master thì vẫn không chuyển vai**: container biến mất thì DNS
      Docker mất luôn tên đó, sentinel báo `Failed to resolve hostname 'redis'` liên tục
      rồi vào **`+tilt`** — chế độ tự khoá, và ở tilt nó KHÔNG thăng cấp. Đo được:
      `flags=s_down,master` mà đứng im.
      → *Cách đúng:* gán **IP tĩnh** cho hai Redis (`172.20.250.10`/`.11`) bằng khối
      `networks:` khai `ipam` với đúng dải Docker đang dùng (`172.20.0.0/16`), và sentinel
      giám sát thẳng IP. IP tĩnh không biến mất cùng container nên hết phụ thuộc DNS.
      **Tên mạng giữ nguyên** `token-ledger-dashboard_default` để ràng buộc `external`
      trong compose của DMS không gãy

## 4. Đổi khai báo của LiteLLM

> ## ✅ ĐÃ GỠ CHẶN — vá fork LiteLLM (hướng A, anh Tuấn chọn 07/09)
>
> Ban đầu nhóm này **bế tắc**: `litellm_tuan_test` (fork `f005afa146`) có hai ràng buộc
> loại trừ nhau — Router chỉ bật Redis khi có `redis_host`+`redis_port` (`router.py:565`),
> mà chính `redis_host` đó bị `_get_redis_sentinel_connection_kwargs` copy sang
> `sentinel_kwargs` (`_redis.py:522`), khiến `redis.Sentinel` gọi
> `Redis(hostname, port, **sentinel_kwargs)` với `host` hai lần.
>
> **Bản vá:** thêm `_SENTINEL_IGNORED_CONNECTION_ARGS = frozenset({"host", "port"})` và
> loại hai khoá đó khỏi kwargs. **Một dòng logic**, còn lại là ghi chú. Phủ cả nhánh đồng
> bộ (`:552`) lẫn bất đồng bộ (`:586`) vì cả hai dùng chung helper.
>
> Bốn cấu hình đã thử trước khi vá, ghi lại để không ai thử lại từ đầu:
>
> | Thử | Kết quả |
> |---|---|
> | `sentinel_nodes` trong `router_settings` | cảnh báo *"not a valid argument… Ignoring"* rồi chạy tiếp, **không dùng Redis** |
> | biến môi trường + giữ `redis_host` | `litellm-2` crash-loop, request **502** |
> | biến môi trường + bỏ `redis_host` | khởi động sạch, `dbsize` đứng **0** |
> | `redis_url` thay host/port | nhánh `url` xử lý trước nhánh sentinel (`_redis.py:623` vs `:633`) |

- [x] 4.1 Trong `router_settings`, thay `redis_host`/`redis_port` bằng `sentinel_nodes` +
      `service_name`. Tham số LiteLLM đọc: `_redis.py:394`, `:401`, `:408`
      → làm được **sau khi vá fork**. Khai qua biến môi trường `REDIS_SENTINEL_NODES` +
      `REDIS_SERVICE_NAME` trong `docker-compose.yml`; `redis_host`/`redis_port` vẫn giữ vì
      Router cần chúng để quyết định dùng Redis
- [x] 4.2 Giữ khối cũ dưới dạng comment kèm ngày, theo thói quen của file này — đó là đường
      quay lui trong một phút
      → đã dùng đường quay lui đó thật một lần lúc còn bế tắc, rồi khôi phục
- [x] 4.3 Khai `sentinel_password` nếu sentinel có đặt mật khẩu riêng
      → không cần: sentinel không đặt mật khẩu riêng cho cổng 26379, và cổng đó không mở
      ra host
- [x] 4.4 Dựng lại hai instance LiteLLM, xác nhận `/health/liveliness` 200 ở cả hai
      → 200 ở cả 4001 và 4002 sau khi trả về kết nối thẳng
- [x] 4.5 Gọi thật vài lượt, xác nhận khoá `rpm`/`tpm` vẫn xuất hiện trong Redis — chứng tỏ
      LiteLLM thật sự nối được qua sentinel, không phải đang chạy mù
      → **CHÍNH MỤC NÀY BẮT ĐƯỢC BẾ TẮC.** Cấu hình sentinel làm LiteLLM khởi động sạch,
      log không một lỗi, request trả 200 — nhưng `dbsize` đứng ở 0. Không có phép kiểm này
      thì change coi như "xong" trong khi Redis đã bị bỏ ra ngoài hoàn toàn.
      **Sau khi vá: `dbsize` 0 → 4**, khoá `rpm`/`tpm` xuất hiện, 0 lỗi trong log

## 5. Nghiệm thu — giết thật, không phải xem tiến trình có lên không

Xem `design.md` §5. Thiếu bước 5.6 thì change này coi như chưa nghiệm thu.

- [x] 5.1 Ghi mốc: ai đang là master
      → `172.20.250.10:6379`, cả ba sentinel đồng thuận
- [x] 5.2 `docker kill token-ledger-redis` — giết **cứng**, không `stop`. `stop` là chết có
      báo trước, không mô phỏng được sự cố thật
- [x] 5.3 ĐO: bao nhiêu giây thì `SENTINEL get-master-addr-by-name` trỏ sang địa chỉ mới
      → **6 giây**, sang `172.20.250.11:6379`
- [x] 5.4 ĐO: gọi thật 10 lượt ngay sau đó — bao nhiêu lượt 200, p50 bao nhiêu. So với mốc
      1.2. **KHÔNG được tệ hơn**
      → **10/10 lượt 200, p50 0,99 s, p95 1,24 s.** Mốc 1.2 là 9/10 và p50 0,87 s — tức
      **tốt hơn về tỷ lệ thành công**, chậm hơn 0,12 s. Và LiteLLM đã ghi 4 khoá `rpm`/`tpm`
      vào **master MỚI**, chứng tỏ nó tự đi theo mà không cần khởi động lại
- [x] 5.5 Dựng lại Redis cũ → xác nhận nó vào làm **replica**, tuyệt đối không phải master
      thứ hai. Đây là phép kiểm chống split-brain
      → `redis` về làm `role:slave` với `master_link_status:up`. **ĐẠT**
- [x] 5.6 **Restart container của master mới → nó phải VẪN là master.** Đây là bước duy
      nhất chứng minh nhóm 2 đã làm đúng
      → `docker restart token-ledger-redis-replica` → vẫn `role:master`. **ĐẠT.** Đây là
      chỗ mà nếu bỏ qua nhóm 2 thì sẽ hỏng
- [x] 5.7 Lặp lại 5.1–5.6 lần thứ hai theo chiều ngược lại, để chắc không phải ăn may
      → giết `redis-replica` (đang là master) → sentinel chuyển ngược về `172.20.250.10`
      sau **7 giây**. Dựng lại → `redis-replica` về làm slave, link up. **Hai chiều đều
      chạy, không phải ăn may**

## 6. Kiểm phần đã cảnh báo trong design

- [x] 6.1 `replica-read-only` sau khi thăng cấp: xác nhận master mới **ghi được**. Nếu cờ đó
      còn hiệu lực thì failover thành công về hình thức mà hỏng về thực chất — xem `design.md`
      "Câu còn mở"
      → **KHÔNG phải vấn đề.** `CONFIG GET replica-read-only` vẫn trả `yes` sau khi thăng
      cấp, nhưng `SET`/`GET`/`DEL` đều `OK` — cờ đó chỉ có hiệu lực khi instance **đang là**
      replica. Lên master thì nó vô hiệu. Câu còn mở của design đã có đáp án
- [x] 6.2 Xác nhận không có lúc nào hai Redis cùng báo `role:master`
      → kiểm sau mỗi lần chuyển vai ở cả hai chiều: luôn đúng một master, một slave

## 7. Tài liệu

- [x] 7.1 Sửa chú thích ở `docker-compose.yml:365` — hiện nó nói *"chưa có Sentinel"*
      → đã viết lại: nay nói đã có Sentinel, kèm con số đo được
- [x] 7.2 Ghi rõ **điều này KHÔNG bảo vệ**: ba sentinel cùng một máy, máy chết là chết tất
      cả. Không để ai đọc xong tưởng Redis đã có tính sẵn sàng cao
      → ghi ở hai chỗ: chú thích `redis-replica` trong `docker-compose.yml` và khối
      `x-sentinel`
- [x] 7.3 Ghi con số đo được ở 5.3 (thời gian chuyển vai) vào tài liệu vận hành
      → **6 giây** (chiều thuận) và **7 giây** (chiều ngược), ghi vào chú thích compose
- [x] 7.4 Ghi lại rằng mức nghiêm trọng của vấn đề gốc là THẤP và số liệu chứng minh điều
      đó — để người sau không dùng change này làm tiền lệ cho những việc tương tự
      → ghi thẳng vào chú thích `redis-replica`: tắt hẳn Redis thì Gateway vẫn phục vụ
      9/10 lượt, p50 0,87 s, vì mọi thứ Redis giữ đều có TTL ≤ 60 giây
- [x] 7.5 **THÊM: ghi lại bản vá fork.** Bản vá `litellm/_redis.py` nằm ở repo KHÁC
      (`../litellm_tuan_test`) nên rất dễ mất khi merge upstream hoặc clone lại. Đã ghi
      tham chiếu `_SENTINEL_IGNORED_CONNECTION_ARGS` vào `docker-compose.yml` khối
      `x-litellm` và vào `config.gateway.yaml`, để người đọc cấu hình biết có bản vá tồn tại
