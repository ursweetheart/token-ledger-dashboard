# Dựng lại instance Gateway — quy trình và số đo

Áp dụng cho `litellm-1` và `litellm-2`. Viết ngày 17/09/2026, sau change
`keep-the-load-balancer-pointed-at-live-instances`.

Tách rõ phần **chứng minh được** khỏi phần **suy luận**, theo khuôn của
[`ep-429-va-mat-gateway-10-09.md`](ep-429-va-mat-gateway-10-09.md).

---

## 1. Kết quả một dòng

Dựng lại từng instance một, đợi `healthy` trước khi sang instance kia. **Không** phải khởi động lại
`gateway-lb` nữa.

---

## 2. `restart` hay `up -d` — chọn đúng cái

| Việc cần làm | Lệnh | Vì sao |
|---|---|---|
| Đổi `config.gateway.yaml` | `docker compose --profile gateway restart litellm-1` | tệp là bind mount, tiến trình chỉ cần đọc lại |
| Đổi biến môi trường (`KEY_*`…) | `docker compose --profile gateway up -d --no-deps litellm-1` | biến môi trường **chỉ đặt được lúc tạo container** |

`--no-deps` **bắt buộc** ở cột thứ hai. Thiếu nó thì `up -d` lan sang `postgres`, `redis` và ba
`sentinel` — dựng lại `postgres` là việc hoàn toàn khác.

Thêm `--wait --wait-timeout 200` để lệnh tự đợi `healthy` thay vì phải ngồi đếm.

## 3. Quy trình

```bash
# 1. instance thứ nhất
docker compose --profile gateway up -d --no-deps --wait --wait-timeout 200 litellm-1

# 2. đợi lệnh trên trả về (nó tự đợi `healthy`), rồi mới sang instance thứ hai
docker compose --profile gateway up -d --no-deps --wait --wait-timeout 200 litellm-2

# 3. kiểm tải chia đều
docker compose --profile gateway exec -T gateway-lb \
  wget -q -O- http://127.0.0.1:4000/health/readiness
```

**Không** có bước khởi động lại `gateway-lb`. Trước 17/09/2026 thì có, và nó bắt buộc.

## 4. Đếm tải chia về đâu — không tốn tiền

Muốn biết hai instance có cùng nhận request không, **đừng** gọi `/v1/chat/completions`: mỗi lượt là
một lượt gọi thật tới Google, có tính tiền.

Dùng `/health/readiness`. Nó miễn phí, và đếm sạch vì phân biệt được với healthcheck bằng **cả** IP
nguồn **lẫn** đường dẫn:

```
luot qua LB    INFO:  172.20.0.2:44160 - "GET /health/readiness" 200   <- IP cua gateway-lb
healthcheck    INFO:  127.0.0.1:46484  - "GET /health/liveliness" 200  <- container tu goi chinh no
```

```bash
b1=$(docker logs token-ledger-litellm-1 2>&1 | grep -c "GET /health/readiness")
b2=$(docker logs token-ledger-litellm-2 2>&1 | grep -c "GET /health/readiness")
docker compose --profile gateway exec -T gateway-lb sh -c \
  'i=1; while [ $i -le 20 ]; do wget -q -O /dev/null http://127.0.0.1:4000/health/readiness; i=$((i+1)); done'
a1=$(docker logs token-ledger-litellm-1 2>&1 | grep -c "GET /health/readiness")
a2=$(docker logs token-ledger-litellm-2 2>&1 | grep -c "GET /health/readiness")
echo "litellm-1: $((a1-b1))   litellm-2: $((a2-b2))"
```

Bình thường ra `10 / 10`.

> `docker logs --since "02:56:17"` **không** lọc được như mong đợi — chuỗi giờ trần bị hiểu sai và
> trả về rỗng. Dùng `docker logs -t` rồi đọc dấu thời gian, hoặc đếm trước/sau như trên.

## 5. Chứng minh được — vì sao bỏ được bước khởi động lại `gateway-lb`

Đo ngày 17/09/2026 trên máy phát triển.

**Trước khi vá**, ép IP của `litellm-1` đổi một bậc (`.8` → `.9`):

```
litellm-1    0 / 20 luot      <- bien mat han khoi vong chia tai
litellm-2   20 / 20 luot

cung luc do:  ca ba container `healthy`
              /lb-health tra `lb-ok`
              request van thanh cong
```

Mất một nửa năng lực xử lý, **không một dấu hiệu bề mặt nào lệch**. Chỉ khởi động lại `gateway-lb`
mới chữa được.

**Sau khi vá** (`resolver` + `zone` + `resolve` trong `docker/gateway/nginx.conf`), cùng phép đo:

```
IP doi .9 -> .8      litellm-1  10 / 10 luot      khong ai dong vao gateway-lb
IP doi .4 -> .9      chieu nguoc, cung ket qua
```

Trễ bắt kịp, đo bằng dấu thời gian trong log:

```
T0 = 02:56:17            ngay sau khi container bao healthy, IP moi
luot dau tien            02:56:18.168      -> tre ~1,2 giay
bom lien tuc 75 giay     litellm-1  12.700   (49,9%)
                         litellm-2  12.731
```

**Một luật cũ đã hết hiệu lực.** `nginx.conf` từng ghi: *"khởi động lại nginx khi một instance đang
tắt thì nginx KHÔNG lên được"*. Đo lại sau khi vá:

```
tat litellm-2  ->  restart gateway-lb  ->  gateway-lb LEN BINH THUONG
                                           van phuc vu qua instance con lai
```

`resolve` chuyển việc phân giải sang lúc chạy, nên nginx không còn đòi mọi tên phải ra địa chỉ ngay
lúc khởi động. Ai đang cầm luật "không được restart `gateway-lb` khi một instance đang tắt" thì
luật ấy đã bỏ — nhưng chỉ trên máy đã nhận commit này.

`depends_on` của `gateway-lb` **giữ nguyên**: đợi cả hai instance khoẻ vẫn là khởi động sạch sẽ, chỉ
không còn là điều kiện bắt buộc.

## 6. Suy luận — chưa chứng minh, đừng ghi thành kết luận

**Dựng lại container, tự nó, KHÔNG đổi IP.** Đo ba lần: `--force-recreate` một instance, rồi cả hai
instance cùng lúc — Docker cấp lại đúng địa chỉ cũ mỗi lần, vì nó còn trống. Phải **chiếm chỗ địa
chỉ cũ bằng một container khác** mới ép được IP đổi.

Nên lỗ hổng ở mục 5 chỉ kích hoạt khi địa chỉ cũ bị giành mất. Đường xảy ra thật thì có:
`docker-compose.yml:670` ghi rằng compose của DMS trỏ vào chính mạng
`token-ledger-dashboard_default` bằng ràng buộc `external`, nên container của project khác cùng
giành địa chỉ trong dải này. Lúc đo, các container DMS đang tắt.

**Tần suất thật: chưa biết.** Cần biết các container DMS bật tắt thế nào trên máy chủ thật. Chưa đo,
và không nên đoán.

**Lần đo chiều ngược ra 0/20 rồi ba vòng ngay sau đều 10/10.** Nhiều khả năng do
`max_fails=2 fail_timeout=30s` loại instance sau hai lượt trượt vào địa chỉ cũ, chứ không do TTL của
DNS — hai mươi lượt bắn hết trong chưa tới một giây nên rơi trọn vào cửa sổ loại trừ ấy. **Chưa đo
riêng**, ghi là suy luận.

## 7. Khi nhận một commit đổi tên biến khoá

**Máy nào đang chạy Gateway thì phải sửa `.env` trước khi dựng lại.** Đổi tên biến là thay đổi
**BREAKING** với người vận hành: `.env` nằm trong `.gitignore` nên commit không mang nó theo.

Chế độ hỏng là **"không chạy"**, không phải "chạy mở" — `docker/gateway/entrypoint.sh` dừng hẳn và
in đúng tên biến còn thiếu:

```
STOP: KEY_CRM_FEEDBACK is missing. Fill it in .env and run again. See .env.example.
```

Cách xử: mở `.env`, đổi **tên** biến, **giữ nguyên giá trị**, rồi dựng lại theo mục 3.

Đã đổi tên một lần ngày 17/09/2026:

| Tên cũ | Tên mới |
|---|---|
| `KEY_BENCH_CRM_TEST_GG_AIA_STU` | `KEY_CRM_FEEDBACK` |

Từ 17/09/2026 có một phép canh trong nhóm `guards` của CI chặn kiểu lỗi đã xảy ra hôm 10/09: mọi
biến `KEY_*` mà `config.gateway.yaml` tham chiếu phải có mặt đủ ở **ba** nơi — vòng kiểm của
`entrypoint.sh`, khối `x-litellm` của `docker-compose.yml`, và `docker-compose.bench.yml`. Sót một
nơi thì CI đỏ trước khi thay đổi tới được máy chủ.

## 8. Nếu phải lùi

Cấu hình là bind mount, không nằm trong image:

```bash
git checkout docker/gateway/nginx.conf
docker compose --profile gateway exec -T gateway-lb nginx -t   # phải đạt TRƯỚC
docker compose --profile gateway restart gateway-lb
```

`nginx -t` phải chạy **trước** khi khởi động lại. Cấu hình sai thì nginx từ chối khởi động, và
`restart: unless-stopped` sẽ quay vòng mãi — tức Gateway đứng.
