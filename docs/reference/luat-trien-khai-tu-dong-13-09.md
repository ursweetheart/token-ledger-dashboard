# Bốn luật cho lệnh triển khai tự động — đo ngày 13/09/2026

Ghi trong lúc làm change `run-every-check-on-every-push`. Change đó **chỉ làm phần CI**; bốn luật
dưới đây thuộc về phần CD sẽ làm sau, và được đo trong lúc khảo sát để không phải đo lại.

Tách rõ phần **chứng minh được** khỏi phần **suy luận**, theo khuôn của
[`ep-429-va-mat-gateway-10-09.md`](ep-429-va-mat-gateway-10-09.md).

---

## 1. Kết quả một dòng

Lệnh triển khai tự động của dự án này chỉ được gồm `docker compose pull` và
`docker compose --profile refresh up -d`. Ba thứ bị cấm: profile `tools`, lệnh `down`, và cờ
`--remove-orphans` — mỗi thứ vì một lý do đã đo được, không phải vì cẩn thận chung chung.

---

## 2. Luật 1 — không bao giờ gọi profile `tools`

**Chứng minh được.** Chuỗi năm bước, mỗi bước đọc được trong repo:

| Bước | Vị trí | Nội dung |
|---|---|---|
| 1 | `docker/tools.Dockerfile:27` | `CMD ["python3", "scripts/update_dashboard.py"]` |
| 2 | `scripts/update_dashboard.py:160` | `[8/9] Dựng lại database → scripts/rebuild_db.py` |
| 3 | `scripts/rebuild_db.py:110` | `("Billing", "db/load_billing.py", ["--rebuild"])` |
| 4 | `scripts/rebuild_db.py:68` | `--rebuild` gọi `DROP SCHEMA public CASCADE`, xoá **mọi GRANT** |
| 5 | `db/connect.py:264` | `cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")` |

Không có bước hỏi xác nhận ở bất kỳ khâu nào — tìm `input()`, `confirm`, `--yes`, `--force` trong
`scripts/rebuild_db.py` đều không có, chỉ có `argparse`.

Dịch vụ `tools` được thiết kế để chạy bằng `docker compose run --rm tools <lệnh cụ thể>`, tức
**người gõ chọn lệnh**. `up -d` bỏ qua đúng phần đó và rơi thẳng vào `CMD` mặc định.

### Hậu quả nặng hơn downtime: mất dữ liệu vĩnh viễn

`rebuild_db.py` xoá rồi **kéo lại** từ Cloud Monitoring, mà cửa sổ lưu giữ của Monitoring trượt
nhanh. Đã đo được một lần mất thật, bằng cách so `token_ledger` (trước migrate) với
`token_ledger_v2`:

```
fact_usage_daily, ngày 11/06/2026
    token_ledger      13.541.550 token
    token_ledger_v2   13.538.088 token
    chênh                  3.462 token   <- mất

fact_monitoring, ngày 11/06/2026
    chỉ số generate_content_paid_tier_3_input_token_count
    token_ledger           4.406
    token_ledger_v2          944
    hiệu     4.406 - 944 =  3.462        <- khớp tuyệt đối
```

Phạm vi đã soát: 129 ngày chung của `fact_monitoring`, băm md5 theo từng ngày. **126 ngày trùng
khít**, 3 ngày lệch (04/06, 11/06, 12/06), tổng cộng 5 dòng. Cả 5 dòng bản cũ đều cao hơn, hai
dòng bản mới về thẳng `0`.

**Suy luận, không phải chứng cứ:** nguyên nhân là cửa sổ Monitoring trượt qua trước khi rebuild
chạy. Giả thuyết đối thủ — "bản mới khử trùng lặp, bản cũ đếm đôi" — bị loại vì khử trùng lặp không
tạo ra giá trị `0`, và tỉ lệ 4.406/944 = 4,67 không chia chẵn. Muốn chứng minh dứt điểm phải hỏi
Cloud Monitoring, mà nó đã trượt qua rồi.

**Điều này nghĩa là:** một lệnh triển khai gọi `--profile tools` không gây một tai nạn, nó gây
**bào mòn đều đặn** — mỗi lần triển khai mất thêm một ít, và nó im lặng, vì số vẫn hiển thị bình
thường, chỉ nhỏ dần.

---

## 3. Luật 2 — không bao giờ `docker compose down`

**Chứng minh được một nửa.** `docker-compose.yml` khai mạng với dải IP tĩnh, và chú thích trong
khối `networks:` cuối tệp nói rõ: tên mạng `token-ledger-dashboard_default` không được đổi vì ràng
buộc `external` trong compose của DMS trỏ vào đó.

`down` xoá mạng. DMS khai `external: true` nghĩa là nó **mượn** chứ không tạo, nên mạng mất là DMS
không lên lại được.

**Chưa xác minh:** tôi đọc chú thích trong repo này, **chưa mở** compose của DMS để tự nhìn thấy
dòng `external`. Luật vẫn đứng vững vì cái giá của việc tuân theo nó bằng không — `up -d` làm được
mọi việc `down` rồi `up` làm, mà không xoá mạng.

---

## 4. Luật 3 — không bao giờ `--remove-orphans`

**Chứng minh được.** Cờ này xoá container không thuộc tập dịch vụ đang gọi. Lệnh triển khai không
gọi profile `gateway`, nên với cờ này nó sẽ giết cả hai instance LiteLLM, ba sentinel, hai Redis và
nginx đang chạy.

---

## 5. Luật 4 — lệnh triển khai đầy đủ

```bash
docker compose pull
docker compose --profile refresh up -d
```

**Có `refresh`.** Chú thích trong `docker-compose.yml` nói rõ vì sao dịch vụ `ledger-refresh` tồn
tại — một khoảng trống đã đo được:

```
LiteLLM_SpendLogs                 444 dòng, mới nhất 08/09 23:55
fact_call WHERE source='gateway'   41 dòng, mới nhất 31/08 10:17
-> trễ 8 ngày 13 giờ 38 phút, và KHÔNG có dấu hiệu nào báo là đang trễ
```

Kết luận của chú thích đó: *"script đã có sẵn chế độ `--every`; cái thiếu là không ai chạy nó"*.
Một lệnh triển khai tự động chính là người chạy nó.

**Không có `gateway`, và đây là ràng buộc kỹ thuật chứ không phải lựa chọn.** Khối `x-litellm` khai
`build.context: ../litellm_tuan_test` — một thư mục **ngang hàng** repo. Máy nào không có thư mục
đó thì compose thoát ngay, kéo theo `postgres`, `api`, `web` đều không lên. Nút này chỉ gỡ được khi
image LiteLLM được đóng gói sẵn và `build:` đổi thành `image:` trỏ vào kho.

---

## 6. Một việc liên quan, chưa làm

**Chứng minh được.** Bản clone `../litellm_tuan_test` đang ở nhánh `litellm_internal_staging` tại
commit `e3490555c5` — có bản vá Sentinel. Nhưng trên kho từ xa:

| Nhánh | Commit | Bản vá `_SENTINEL_IGNORED_CONNECTION_ARGS` |
|---|---|---|
| `origin/Tuan-develop` | `e3490555c5` | **có** |
| `origin/litellm_internal_staging` | `f005afa146` | **không** |

Và `origin/HEAD` trỏ vào `litellm_internal_staging`. Nghĩa là **một bản clone mới rơi thẳng vào
nhánh không có bản vá**, và Gateway sẽ chết lúc khởi động với
`TypeError: Redis.__init__() got multiple values for argument 'host'`.

Máy hiện tại an toàn: local đi trước remote đúng 1 commit, nên `git pull` không kéo lùi được. Rủi
ro nằm ở **máy mới** — đúng kịch bản đưa Gateway sang server riêng.

Cách chặn rẻ nhất, để dành cho chặng 2: trước khi đóng gói image, `grep` tìm
`_SENTINEL_IGNORED_CONNECTION_ARGS` trong `litellm/_redis.py`; không thấy thì dừng.

---

## 7. Còn chưa chắc

| Điều | Mức |
|---|---|
| Nguyên nhân mất 3.462 token là do cửa sổ Monitoring trượt | **Suy luận mạnh**, đã loại được giả thuyết đối thủ |
| 3.462 ở `fact_monitoring` **gây ra** 3.462 ở `fact_usage_daily` | **Chưa lần theo** đường số liệu; mới thấy hai con số trùng khít |
| Compose của DMS thật sự khai `external` | **Chưa mở** tệp đó ra nhìn |
| `token_ledger` còn giữ gì độc quyền ngoài 5 dòng đã tìm | **Chưa soát hết** — 3 bảng `fact_call`, `fact_latency_daily`, `fact_perf_daily` có cột khác nhau nên không so trực tiếp được |
