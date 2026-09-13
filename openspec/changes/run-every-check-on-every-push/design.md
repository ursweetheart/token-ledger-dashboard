# Thiết kế

## Vì sao chia ba chặng chứ không làm một lượt

CI/CD thường được nói như một khối. Ở đây nó là ba việc có mức rủi ro khác hẳn nhau, nên tách ra:

```
  CHẶNG 1  chạy phép kiểm        rủi ro 0    ← change này
  CHẶNG 2  đóng gói + đẩy kho    rủi ro 0
  CHẶNG 3  đưa lên máy chủ       rủi ro thật
```

Chặng 1 chạy trên máy ảo của GitHub. Máy ảo đó sinh ra, làm việc, rồi bị xoá. Nó không chạm vào
`192.168.20.111`, không chạm vào PostgreSQL, không chạm vào máy nào của mình. Hỏng thì chỉ hiện ra
một dấu đỏ trên trang web.

Chặng 3 mới là chặng chạm vào máy thật, và nó cần những thứ chặng 1 không cần: một runner nằm trong
mạng nội bộ, quyết định về kho chứa image, và bốn luật an toàn dưới đây. Gộp cả ba vào một change
là buộc phải trả lời mọi câu hỏi trước khi được lợi ích đầu tiên.

## Bốn luật cho chặng 3 — ghi ở đây để không mất

Change này **không** triển khai chặng 3. Nhưng bốn luật dưới đây đã được đo trong lúc khảo sát ngày
13/09, và nếu không ghi lại thì lần sau sẽ phải đo lại từ đầu.

### Luật 1 — lệnh triển khai KHÔNG BAO GIỜ gọi profile `tools`

Đây là luật quan trọng nhất, và nó không hiển nhiên chút nào. Tên profile nghe như "bộ công cụ".
Thực tế:

```
  docker compose --profile tools up -d
       │
       ▼  docker/tools.Dockerfile:27
  CMD ["python3", "scripts/update_dashboard.py"]
       │
       ▼  scripts/update_dashboard.py:160
  [8/9] Dựng lại database → scripts/rebuild_db.py
       │
       ▼  scripts/rebuild_db.py:110
  ("Billing", "db/load_billing.py", ["--rebuild"])
       │
       ▼  db/connect.py:264
  DROP SCHEMA public CASCADE; CREATE SCHEMA public;
```

Không có bước hỏi xác nhận ở bất kỳ khâu nào — tìm `input()`, `confirm`, `--yes`, `--force` trong
`rebuild_db.py` đều không có.

Dịch vụ này được thiết kế để chạy bằng `docker compose run --rm tools <lệnh cụ thể>`, tức người gõ
chọn lệnh. `up -d` bỏ qua đúng phần "người chọn" và rơi thẳng vào `CMD` mặc định.

**Hậu quả nặng hơn là mất dữ liệu vĩnh viễn, không phải downtime.** `rebuild_db.py` xoá rồi kéo lại
từ Cloud Monitoring, mà cửa sổ lưu giữ của Monitoring trượt nhanh. Đã đo được một lần mất thật:

| Ngày | `token_ledger` (trước migrate) | `token_ledger_v2` | Chênh |
|---|---|---|---|
| 11/06 | 13.541.550 token | 13.538.088 token | **mất 3.462** |

Truy ngược tới đúng dòng: `fact_monitoring` ngày 11/06, chỉ số
`generate_content_paid_tier_3_input_token_count` — bản cũ ghi 4.406, bản mới ghi 944. Hiệu số
4.406 − 944 = 3.462, khớp tuyệt đối với chênh lệch ở bảng tổng hợp.

Nếu mỗi lần triển khai đều rebuild thì đây không phải một tai nạn mà là **bào mòn đều đặn**, và nó
im lặng: số vẫn hiển thị bình thường, chỉ nhỏ dần.

### Luật 2 — không bao giờ `docker compose down`

`docker-compose.yml` khai mạng `token-ledger-dashboard_default` với dải IP tĩnh, và chú thích trong
khối `networks:` nói rõ compose của DMS khai mạng này là `external`. `down` xoá mạng, kéo DMS gãy
theo. Một dự án khác hỏng vì một lệnh triển khai của dự án này là loại lỗi rất khó lần ra.

### Luật 3 — không bao giờ `--remove-orphans`

Cờ này giết container không thuộc tập dịch vụ đang gọi, tức giết cả Gateway đang chạy ở profile
khác.

### Luật 4 — lệnh triển khai chỉ gồm

```
docker compose pull
docker compose --profile refresh up -d
```

Có `refresh`, vì chính chú thích trong `docker-compose.yml` nói dịch vụ `ledger-refresh` sinh ra để
vá một khoảng trống đã đo được: sổ Gateway tự ghi ngay, còn sổ dashboard trễ 8 ngày 13 giờ, "script
đã có sẵn chế độ `--every`; cái thiếu là không ai chạy nó". Một lệnh triển khai tự động chính là
người chạy nó.

Không có `gateway`, vì `x-litellm` khai `build.context: ../litellm_tuan_test` — một thư mục ngang
hàng repo. Máy nào không có thư mục đó thì compose **thoát ngay**, kéo theo cả `postgres`, `api`,
`web` đều không lên. Chặng 2 gỡ được nút này bằng cách thay `build:` bằng `image:` trỏ vào kho.

## Quyết định — canh dòng bind, hay bỏ hẳn dòng bind

Vấn đề gốc: cổng của `web` có một nửa là biến, một nửa ghi cứng.

```yaml
- "127.0.0.1:${WEB_PORT:-8080}:80"
#  └────┬────┘ └──────┬───────┘
#   ghi cứng      đã là biến
```

Vì phần địa chỉ ghi cứng nên phải sửa tay mỗi lần đổi môi trường, nên mới quên được.

**Phương án A — thêm phép kiểm canh dòng đó.** CI đọc `docker-compose.yml`, thấy địa chỉ của máy
phát triển thì báo hỏng.

- Được: không đụng tệp đang chạy.
- Mất: người phát triển vẫn phải sửa tay hai lần mỗi vòng, chỉ khác là bị nhắc khi quên. Và muốn
  chạy thử trên máy mình thì CI sẽ đỏ suốt.

**Phương án B — đưa địa chỉ thành biến.**

```yaml
- "${WEB_BIND:-127.0.0.1}:${WEB_PORT:-8080}:80"
```

Máy phát triển không đặt gì, ra `127.0.0.1`. Máy chủ đặt `WEB_BIND=192.168.20.111` trong `.env` —
tệp đã nằm trong `.gitignore`. Hai máy dùng **chung một tệp compose**, không ai sửa tay lần nào.

- Được: loại lỗi này không còn tồn tại để mà canh. Và đây đúng là thứ chặng 3 cần — một tệp compose
  chạy được trên mọi máy.
- Mất: sửa một tệp đang chạy. Mặc định giữ nguyên hành vi cũ nên rủi ro thấp.

**Chọn B, và vẫn giữ một phép kiểm.** Phép kiểm đổi nội dung: thay vì canh một địa chỉ cụ thể, nó
canh **nguyên tắc** — trong `docker-compose.yml` không được có địa chỉ IP của một môi trường cụ thể
nằm ghi cứng ở phần cổng. Viết như vậy thì phép kiểm còn đúng cả khi sau này có máy thứ ba.

Lý do không chọn A: A để nguyên nguyên nhân và thêm người canh. B bỏ nguyên nhân. Thêm một phép
kiểm để canh một thứ đáng lẽ không nên tồn tại là trả tiền hai lần.

## Quyết định — khẳng định số phép kiểm, hay chỉ xem mã thoát

Bộ kiểm JavaScript được gọi bằng `node --test tests/*.test.js`. Dấu sao do vỏ lệnh nở ra. Nếu vì
một lý do nào đó nó nở hụt — đổi thư mục, đổi vỏ lệnh, đổi cách đặt tên tệp — thì lệnh trả về xanh
mà không chạy phép kiểm nào.

**Đã đo, không phải lo xa.** Chạy 13/09/2026:

```
$ node --test tests/khong-ton-tai-*.test.js
  số phép kiểm chạy :  0
  mã thoát          :  0     <- XANH
```

Chỉ xem mã thoát thì CI báo đạt trong khi nó chưa kiểm gì. Phép đếm bắt được đúng trường hợp này;
`unittest` cũng cho ra 0 phép theo cách tương tự khi mẫu tên tệp không khớp.

Đây không phải chuyện tưởng tượng. Repo này đã gặp đúng dạng đó ở tầng dữ liệu và đã viết thành
nguyên tắc trong `automated-check-coverage`: *"Phép kiểm phải phân biệt đã kiểm và đạt với không có
gì để kiểm"*, và *"chạy trên tập rỗng, phép kiểm MUST NOT báo đạt"*.

Change này áp cùng nguyên tắc cho bộ kiểm mã. CI phải đọc số phép kiểm đã chạy và so với mốc đã
chốt — **51** cho JavaScript, **11** cho Python (đo 13/09).

Đổi lại là mỗi lần thêm phép kiểm mới phải sửa con số. Đó là cái giá chấp nhận được, và thật ra nó
còn tốt: con số thay đổi làm cho việc thêm phép kiểm trở nên nhìn thấy được trong lịch sử.

## Quyết định — chạy trên máy ảo GitHub, không dùng `act`

Có công cụ tên `act` cho phép chạy GitHub Actions ngay trên máy mình. Không dùng, vì hai lý do:

1. Nó phải tải image runner nặng vài GB.
2. Nó không giống hệt bản thật. Xanh trên `act` mà đỏ trên GitHub là chuyện thường, và lúc đó phải
   sửa hai lần.

Đường ngắn hơn: đẩy lên một nhánh và để GitHub chạy bản thật. Vòng lặp khoảng một phút, không cài
gì, không tốn đĩa. Chặng 1 vốn không đụng máy nào nên chẳng có gì để phải thử trước ở local.

## Điều kiện đã đo, để lần sau khỏi đo lại

| Điều | Giá trị | Đo bằng |
|---|---|---|
| Số phép kiểm JavaScript | 51, exit 0, 9,2 giây | `node --test tests/*.test.js` |
| Số phép kiểm Python | 11, exit 0, 0,005 giây | `python -m unittest discover -s tests -p "test_*.py"` |
| Node trên máy phát triển | v24.15.0 | `node --version` |
| Tệp khai phụ thuộc | **không có tệp nào** | `package.json`, `pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini`, `Makefile` đều vắng |
| `psycopg2` nạp ở đâu | trong hàm, `db/connect.py:196` | đầu tệp chỉ có `os` và `pathlib` |
| Bộ kiểm Python trên máy trắng | 11/11 đạt, **không cài gói nào** | `docker run --rm python:3.12-slim python -m unittest discover -s tests -p "test_*.py"` |
| Bộ kiểm JavaScript trên máy trắng | 51/51 đạt, **không `npm install`** | `docker run --rm node:24-alpine node --test tests/*.test.js` |
| Ba `Dockerfile` | sạch, không cảnh báo | `docker build --check` từng tệp |
| Kho mã | `github.com/ursweetheart/token-ledger-dashboard` | `git remote -v` |

Hai dòng "máy trắng" là phép đo quan trọng nhất bảng này. Trước khi có chúng, tính chất "chạy được
mà không cài gì" mới chỉ là **suy luận** từ vị trí lời `import`. Chạy trong container sạch biến nó
thành **chứng cứ**, và đó cũng chính là môi trường mà máy ảo GitHub sẽ dựng lại.

## Rủi ro

| Rủi ro | Mức | Xử lý |
|---|---|---|
| Bộ kiểm đạt ở máy này, đỏ trên máy ảo GitHub | **Thấp** | Đã hạ từ "trung bình" sau khi chạy cả hai bộ kiểm trong container sạch — xem hai dòng "máy trắng" ở bảng trên. Rủi ro còn lại chỉ là khác biệt giữa container và máy ảo GitHub |
| Người phát triển bị chặn merge vì một phép kiểm hỏng sẵn | Thấp | Cả 62 phép đều đang đạt, đo 13/09 |
| Số phép kiểm khai trong CI trôi khỏi số thật | Trung bình | Thông điệp lỗi phải nói rõ số mong đợi, số thật, và sửa ở đâu |
