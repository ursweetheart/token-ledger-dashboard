## Why

`docker/gateway/nginx.conf` phân giải tên upstream **một lần** lúc khởi động. Chú thích ở chính
tệp đó (dòng 25) đã ghi điều này, nhưng chỉ rút ra một hệ quả — "khởi động lại nginx khi một
instance đang tắt thì nginx không lên được". Hệ quả thứ hai chưa ai ghi, và nó nguy hiểm hơn:

> Nếu một instance đổi địa chỉ IP, `gateway-lb` vẫn gửi request tới địa chỉ cũ. Instance đó chết
> đối với load balancer, dù bản thân nó khoẻ.

**Đo ngày 17/09/2026, ép IP đổi một bậc (`.8` → `.9`):**

```
litellm-1    0 / 20 lượt      ← biến mất khỏi vòng chia tải
litellm-2   20 / 20 lượt

cùng lúc đó:  cả ba container `healthy` · /lb-health trả `lb-ok` · request vẫn thành công
```

Mất một nửa năng lực xử lý, **không một dấu hiệu bề mặt nào lệch**. Instance thứ hai cũng đổi địa
chỉ thì Gateway đứng hẳn.

**Điều kiện kích hoạt hẹp hơn thoạt nhìn, và phải nói rõ.** Dựng lại container **không tự nó** đổi
IP: đo được ba lần, Docker cấp lại đúng địa chỉ cũ khi nó còn trống — kể cả khi dựng lại cả hai
instance cùng lúc. Lỗ hổng chỉ kích hoạt khi địa chỉ cũ **bị container khác giành mất** trong lúc
dựng lại. Chi tiết và số đo ở `design.md` D7.

Đường xảy ra thật thì có: `docker-compose.yml:670` ghi rằng compose của DMS trỏ vào chính mạng
`token-ledger-dashboard_default` bằng ràng buộc `external`, nên container của project khác cùng
giành địa chỉ trong dải này. Lúc đo, các container DMS đang tắt.

**Nên đây là bảo hiểm rẻ, không phải vá một đám cháy.** Ba dòng, chặn hẳn một chế độ hỏng mất một
nửa năng lực mà không có tín hiệu nào. Tần suất thật **chưa đo** — xem câu còn treo ở `design.md` D7.

**Lời giải đã có sẵn trong repo.** `docker/gateway/edge.conf.template` giải đúng bài toán này,
bằng ba dòng, trên cùng image `nginx:1.27-alpine`, và đang chạy thật:

```nginx
resolver 127.0.0.11 valid=10s ipv6=off;

upstream gateway_pool {
    zone gateway_pool 64k;
    server gateway-lb:4000 resolve;
}
```

Hai tệp nginx cùng làm một việc mà viết hai kiểu. Chính đó là loại lệch mà mấy tháng sau không ai
nhớ vì sao.

## What Changes

- `docker/gateway/nginx.conf`: thêm `resolver`, thêm `zone` vào khối `upstream litellm_pool`, thêm
  tham số `resolve` vào hai dòng `server`.
- Viết lại chú thích ở `nginx.conf` cho đúng: đoạn "phân giải một lần lúc khởi động" mô tả hành vi
  **trước** change này, và sau change thì không còn đúng.
- **Phép canh mới trong nhóm `guards` của CI:** mọi khối `upstream` trong `docker/gateway/*.conf*`
  phải khai `zone` và mọi dòng `server <tên>:<cổng>` trong đó phải mang `resolve`; tệp chứa khối ấy
  phải khai `resolver`.
- Ghi quy trình dựng lại vào `docs/reference/`: sau change này, không còn phải `restart gateway-lb`
  theo sau mỗi lần dựng lại instance.

**Giữ nguyên, có chủ ý:**

- **Hai dịch vụ rời `litellm-1` và `litellm-2`.** Không gộp thành một dịch vụ `litellm` chạy
  `--scale`. Việc đó đổi `container_name`, đổi `depends_on` của `gateway-lb`, và đụng
  `docker-compose.bench.yml` — một câu hỏi riêng, đo riêng. Change này chỉ vá lỗ hổng đã có.
- **`max_fails` / `fail_timeout` / `proxy_next_upstream`.** Cơ chế loại instance hỏng bằng cách đếm
  lỗi thật không đổi. Riêng `proxy_next_upstream` MUST NOT được thêm `non_idempotent`: gửi lại một
  `POST /v1/chat/completions` là trả tiền hai lần cho một câu hỏi.
- **IP tĩnh cho hai Redis.** Đó là cách vá một hạn chế của Sentinel, không phải phong cách chung —
  xem `design.md` D1.
- **`edge.conf.template`.** Đã đúng, không đụng.

## Capabilities

### New Capabilities

- `gateway-instance-discovery`: Load balancer của Gateway theo được các instance LiteLLM qua một
  lần dựng lại container, không cần ai khởi động lại nó; hai tệp cấu hình nginx khai việc phân giải
  tên theo cùng một cách; và việc nghiệm thu phải chứng minh bằng một lần dựng lại thật.

### Modified Capabilities

(không có — `gateway-shared-state-continuity` nói về vai trò master/replica của Redis sống sót qua
việc dựng lại container. Cùng một tình huống kích hoạt, nhưng khác hẳn thành phần và khác cơ chế;
không yêu cầu nào của spec ấy đổi.)

## Impact

| Vùng | Việc |
|---|---|
| `docker/gateway/nginx.conf` | 3 dòng thêm, chú thích viết lại |
| `.github/workflows/ci.yml` | một bước grep trong nhóm `guards` |
| `docs/reference/` | quy trình dựng lại instance; bỏ bước "restart `gateway-lb` sau cùng" |

**Hệ thống đang chạy:** `gateway-lb` phải được khởi động lại **một lần** để nhận cấu hình mới. Đây
là lần cuối cùng phải làm việc đó. Cả hai instance LiteLLM phải `healthy` trước khi khởi động lại
nó, vì luật cũ vẫn áp cho chính lần này: nginx từ chối khởi động nếu một tên upstream không phân
giải được.

**Rủi ro cần chặn trước:** cấu hình `resolver` sai thì nginx **không khởi động**, tức Gateway đứng.
Bắt buộc chạy `nginx -t` trong container trước khi khởi động lại — xem `tasks.md` mục 2.
