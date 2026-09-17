## Context

Đọc ngày 17/09/2026. Hai tệp nginx trong `docker/gateway/`, cùng một việc, viết hai kiểu:

```
edge.conf.template                      nginx.conf
──────────────────────────────────      ──────────────────────────────────
resolver 127.0.0.11 valid=10s           (không có)
    ipv6=off;
upstream gateway_pool {                 upstream litellm_pool {
    zone gateway_pool 64k;                  (không có zone)
    server gateway-lb:4000 resolve;         server litellm-1:4000 max_fails=2 …
}                                           server litellm-2:4000 max_fails=2 …
                                            keepalive 32;
                                        }
```

`127.0.0.11` là DNS nội bộ của Docker, cố định cho mọi mạng bridge do người dùng khai.

**Vì sao `edge` đúng mà `lb` thiếu:** `edge.conf.template` được viết sau, lúc dựng lớp bàn giao cho
reverse proxy. `nginx.conf` có từ 27/08, trước khi ai gặp vấn đề dựng lại container. Không có quyết
định nào chọn hai kiểu khác nhau — chỉ là hai thời điểm.

**Chú thích hiện có ở `nginx.conf:25-30` mô tả đúng hành vi, nhưng rút thiếu một hệ quả:**

| Ghi trong tệp | Thiếu |
|---|---|
| tắt một instance khi nginx **đang chạy** → nginx sống, loại instance đó | |
| khởi động lại nginx khi một instance **đang tắt** → nginx không lên được | |
| | **dựng lại** một instance → IP mới → nginx vẫn gọi IP cũ, im lặng |

## Decisions

### D1 — Dùng `resolve`, không dùng IP tĩnh

IP tĩnh cũng vá được: gán `172.20.250.20/.21` cho hai instance, giống `redis` và `redis-replica`
đang có. Bác bỏ vì ba lẽ:

**① Tiền lệ Redis không áp được sang đây.** IP tĩnh của Redis là cách vá một hạn chế của Sentinel,
ghi rõ trong `sentinel.conf.template`: Sentinel chỉ nhận IP; bật `resolve-hostnames yes` thì lúc
master chết, DNS Docker mất luôn tên đó, sentinel rơi vào `+tilt` và không chuyển vai. nginx **không**
có hạn chế ấy — nó dùng được tên, chỉ cần khai `resolver`.

**② IP tĩnh chặn `--scale`.** Docker không gán được cùng một IP cho nhiều container, nên
`docker compose up -d --scale litellm=4` báo lỗi ngay. Chọn IP tĩnh là khoá luôn đường mở rộng,
trong khi `resolve` để ngỏ.

**③ IP tĩnh phải bảo trì bằng tay.** Mỗi instance thêm vào là một địa chỉ phải tự chọn, cộng thêm
một dòng `server` trong `nginx.conf` và một lần khởi động lại nginx. `resolve` thì không.

### D2 — Giữ hai dịch vụ rời `litellm-1` / `litellm-2`

Cách gọn hơn là một dịch vụ `litellm` rồi `--scale 2`, và `server litellm:4000 resolve` sẽ nhận đủ
N bản ghi A mà Docker DNS trả về. Để ngoài change này vì nó kéo theo:

- bỏ `container_name` cố định (compose từ chối scale dịch vụ có `container_name`);
- sửa `depends_on` của `gateway-lb`, đang liệt kê đích danh hai tên;
- soát `docker-compose.bench.yml` và mọi tài liệu gọi tên `token-ledger-litellm-1`.

Đó là một câu hỏi về mở rộng năng lực. Change này chỉ vá một lỗ hổng đã có. Trộn hai việc thì lúc
hỏng không biết vì cái nào.

### D3 — `nginx -t` trước khi khởi động lại, không sau

Chế độ hỏng của change này là **Gateway đứng**: `resolver` sai cú pháp thì nginx từ chối khởi động,
và `restart: unless-stopped` sẽ quay vòng mãi. Nên thứ tự bắt buộc là kiểm cấu hình **trong
container đang chạy** rồi mới khởi động lại:

```
docker compose --profile gateway exec gateway-lb nginx -t
```

`nginx -t` đọc tệp đã mount, nên nó kiểm đúng nội dung mới trước khi có tiến trình nào phải chết.

Đường lùi: `git checkout docker/gateway/nginx.conf` rồi khởi động lại `gateway-lb`. Cấu hình là
bind mount nên không phải dựng lại image.

### D4 — Phép canh so hai tệp với nhau, không ghim một chuỗi

Phép canh dễ nhất là `grep resolver docker/gateway/nginx.conf`. Không chọn, vì nó không chặn được
việc thêm một khối `upstream` **thứ hai** thiếu `resolve`, và cũng không chặn `edge.conf.template`
trôi theo hướng ngược lại.

Phép canh khai theo tính chất: trong `docker/gateway/*.conf` và `*.conf.template`, mỗi tệp có khối
`upstream` SHALL khai `resolver`; mỗi khối `upstream` SHALL có `zone`; mỗi dòng `server <tên>:<cổng>`
bên trong SHALL mang `resolve`.

**Sửa 17/09/2026 — viết bằng shell nội tuyến, không phải Python.** Bản đầu ghi "viết bằng thư viện
chuẩn của Python". Nhưng cả **ba** phép canh đang có trong nhóm `guards` đều là shell nội tuyến
(`grep`/`awk`) đặt thẳng trong `ci.yml`; không có tệp Python nào trong nhóm ấy. Thêm một script
riêng kèm tệp phép kiểm là nặng hơn nếp đang có, và kéo theo việc phải nâng `EXPECTED_PY`. Theo nếp:
một bước `run:`, `sed` + `awk`, không tệp mới.

**Một bẫy đã sập khi viết, ghi lại để đừng lặp:** `awk` đọc theo dòng, nên khối `upstream p { ... }`
viết gọn **trên một dòng** lọt hoàn toàn qua phép canh — hai ca thử đầu tiên đều không bị bắt. Phải
chuẩn hoá trước khi đọc: bỏ chú thích, tách `{` `}` `;` thành dòng riêng. Không có bước ấy thì phép
canh trông như chạy đúng trong khi có một điểm mù.

### D5 — `zone` là bắt buộc, không phải tuỳ chọn

Tham số `resolve` đòi upstream nằm trong vùng nhớ chung, tức phải có `zone`. Thiếu `zone` thì nginx
báo lỗi cấu hình và không khởi động. `edge.conf.template` đã khai `zone gateway_pool 64k;` — dùng
cùng kích thước cho `litellm_pool`, không có lý do đo lại.

### D6 — Đo phân bố tải bằng endpoint miễn phí, không bằng lượt gọi tính tiền

Bản đầu của `tasks.md` viết "gửi 20 lượt gọi qua `gateway-edge`". Sai hai lần, phát hiện lúc apply
ngày 17/09/2026:

**① Tốn tiền vô ích.** `gateway-edge` chỉ mở `/v1/chat/completions`, tức mỗi lượt đo là một lượt gọi
thật tới Google, có tính tiền. Change này đo **phân bố tải giữa hai instance**, không đo chất lượng
trả lời. Trả tiền cho việc đó là thừa.

**② Không chạy được.** `docker ps -a` ngày 17/09/2026 không có `token-ledger-gateway-edge` — dịch vụ
ấy chưa từng được tạo trên máy phát triển.

Đường đo thay thế, đã thử: `GET /health/readiness` qua `gateway-lb`, gọi từ trong mạng Docker.
Miễn phí, không chạm nhà cung cấp, và **đếm được sạch** vì hai loại lưu lượng phân biệt bằng cả IP
nguồn lẫn đường dẫn:

```
luot qua LB    INFO:  172.20.0.2:44160 - "GET /health/readiness" 200   <- IP cua gateway-lb
healthcheck    INFO:  127.0.0.1:46484  - "GET /health/liveliness" 200  <- container tu goi chinh no
```

`/health/readiness` **không** phải endpoint mà healthcheck dùng, nên đếm nó không lẫn nhiễu.

Kèm một ràng buộc bắt buộc: dựng lại instance phải có `--no-deps`. Thiếu cờ ấy thì
`--force-recreate` lan sang cả `postgres`, `redis` và ba `sentinel` — dựng lại `postgres` là việc
hoàn toàn khác, không nằm trong change này.

### D7 — Điều kiện kích hoạt hẹp hơn bản đầu đã viết

Đo ngày 17/09/2026 trong lúc apply. Bản đầu của `proposal.md` viết "container dựng lại **sẽ** nhận
một địa chỉ IP mới". **Sai.** Số đo:

| Việc làm | IP `litellm-1` | litellm-1 | litellm-2 |
|---|---|---|---|
| mốc chuẩn | .8 | 11 | 9 |
| `--force-recreate --no-deps litellm-1` | .8 — **không đổi** | 11 | 9 |
| `--force-recreate --no-deps litellm-1 litellm-2` | .8 và .4 — **không đổi** | — | — |
| chiếm `.8` bằng container khác rồi dựng lại | **.9** | **0** | **20** |

Docker cấp lại đúng địa chỉ cũ khi nó còn trống.

**BỔ SUNG cùng ngày, và nó nới rộng kết luận trên.** Trong lúc apply change
`name-the-crm-key-after-its-agent` — một lần triển khai **thật**, dựng lại cả hai instance để nạp
biến môi trường mới — `litellm-2` **đã đổi IP** `.9` → `.8`, không cần ai chiếm chỗ. Lý do: dải địa
chỉ đã xê dịch từ các thao tác trước, nên địa chỉ cũ của nó không còn là địa chỉ trống thấp nhất.

Kết quả với bản vá đã có: **10 / 10**, và `gateway-lb` vẫn `Up 20 minutes` — không ai động vào nó.

Nên câu đúng không phải "dựng lại thì an toàn" mà là: **dựng lại giữ nguyên IP chỉ khi địa chỉ cũ
còn trống, và điều đó không phải lúc nào cũng đúng.** Một lần triển khai bình thường đã làm nó sai.
Giá trị của change này cao hơn ước lượng ở đoạn trên.

**Cơ chế hỏng thì có thật**, và dòng cuối bảng chứng minh dứt khoát: IP đổi một bậc là instance ấy
biến mất hoàn toàn khỏi vòng chia tải — 0/20 — trong khi cả ba container báo `healthy` và
`/lb-health` trả `lb-ok`. Không một dấu hiệu bề mặt nào lệch.

**Điều kiện kích hoạt: địa chỉ cũ bị giành mất trong lúc dựng lại.** Trên máy này điều đó **có
đường xảy ra thật**, không phải giả định: `docker-compose.yml:670` ghi rằng compose của DMS trỏ vào
chính mạng `token-ledger-dashboard_default` bằng ràng buộc `external`. Container của project khác
cùng giành địa chỉ trong dải này. Lúc đo, các container DMS đang tắt — nên địa chỉ trống và được cấp
lại y cũ. Chúng chạy thì giả định "cấp lại y cũ" không còn đứng.

**Hệ quả cho giá trị của change:** thấp hơn bản đầu ước lượng, nhưng không bằng không. Đây là bảo
hiểm rẻ — ba dòng — cho một chế độ hỏng mất một nửa năng lực mà không có tín hiệu nào. Chưa đo được
tần suất thật, và **không nên đoán**: cần biết các container DMS bật tắt thế nào trên máy chủ thật.
Ghi là câu còn treo, không ghi là lý do.

### D8 — `resolve` còn gỡ bỏ một bẫy khác, ngoài dự kiến

Đo ngày 17/09/2026, sau khi vá. Chú thích cũ ở `nginx.conf` ghi hai hệ quả của việc phân giải một
lần. Hệ quả thứ hai — *"khởi động lại nginx khi một instance đang tắt thì nginx KHÔNG lên được"* —
**không còn đúng** sau khi thêm `resolve`:

```
tat litellm-2  ->  restart gateway-lb
   truoc khi va:  nginx KHONG len duoc      ("host not found in upstream")
   sau khi va:    nginx LEN BINH THUONG, van phuc vu qua instance con lai
                  /health/readiness tra {"status":"healthy","db":"connected"}
```

`resolve` chuyển việc phân giải sang lúc chạy, nên nginx không còn đòi mọi tên phải ra địa chỉ ngay
lúc khởi động.

**Đây là lợi ích, không phải rủi ro.** Luật cũ là một bẫy vận hành thật: khởi động lại load balancer
trong lúc một instance đang bảo trì thì mất luôn cả Gateway. Change này gỡ bỏ nó — nhưng gỡ **ngoài
dự kiến**, không có trong mục What Changes của proposal lúc viết.

**`depends_on` giữ nguyên.** Đợi cả hai instance khoẻ vẫn là cách khởi động sạch sẽ; nó chỉ không
còn là **điều kiện bắt buộc** để nginx lên được. Nới `depends_on` là mở rộng phạm vi, để ngoài
change này.

**Ghi lại vì nó đổi một luật vận hành đã thành nếp:** ai đang cầm luật "không được restart
`gateway-lb` khi một instance đang tắt" cần biết luật ấy đã hết hiệu lực — nhưng chỉ sau khi commit
này tới được máy đó.

## Risks / Trade-offs

| Rủi ro | Mức | Chặn bằng |
|---|---|---|
| `resolver` sai cú pháp → nginx không lên → Gateway đứng | cao | D3: `nginx -t` trước, đường lùi bằng `git checkout` |
| `resolve` không có trong nginx bản mã nguồn mở | thấp | `edge.conf.template` đang dùng chính tham số này, cùng image `nginx:1.27-alpine`, và lưu lượng thật đi qua nó. Task 0.2 xác nhận lại bằng `nginx -t` |
| `valid=10s` làm nginx hỏi DNS thường xuyên hơn | rất thấp | DNS của Docker nằm cùng máy; `edge` đã chạy với đúng giá trị này |
| Giữa lúc IP đổi, vài request rơi vào địa chỉ cũ | thấp | Đã có sẵn `max_fails=2 fail_timeout=30s`. Change này rút ngắn cửa sổ ấy từ **vĩnh viễn** xuống còn tối đa `valid=10s` |

## Migration

Không có dữ liệu để chuyển. Một lần khởi động lại `gateway-lb`, với cả hai instance đang `healthy`.

Sau change này, quy trình dựng lại instance bỏ được bước cuối:

```
TRƯỚC                                   SAU
docker compose up -d litellm-1          docker compose up -d litellm-1
   đợi healthy                             đợi healthy
docker compose up -d litellm-2          docker compose up -d litellm-2
   đợi healthy                             đợi healthy
docker compose restart gateway-lb   ←   (bỏ)
```
