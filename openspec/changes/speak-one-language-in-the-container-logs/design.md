# Thiết kế — nói một thứ tiếng trong log của container

Mọi con số đếm trên mã nguồn ngày 01/09/2026.

---

## ① Ranh giới: log cho MÁY, chữ cho NGƯỜI DÙNG

Quy ước đang có nói *"định danh tiếng Anh, ghi chú tiếng Việt"* và *"không dấu chỉ dành cho
file cấu hình"*. Log **không thuộc loại nào** trong hai loại đó — nó là đầu ra chạy thật.

Chỗ này từng gây nhầm, và cần một đường kẻ rõ. Cùng một sự việc "database chưa có dữ liệu" hiện
ở **ba** nơi khác nhau:

```
   web/js/app.js:4077      man hinh dashboard    NGUOI DUNG CUOI    -> Viet CO DAU, GIU NGUYEN
   web/js/api.js:517       console trinh duyet   nguoi phat trien   -> Anh
   backend/check_api.py:88 terminal / docker     nguoi van hanh     -> Anh
```

**Đường kẻ:** ai đọc nó quyết định ngôn ngữ, không phải file nào chứa nó.

```
   NGUOI DUNG CUOI doc   ->  tieng Viet CO DAU     giao dien, o loi tren man hinh
   NGUOI VAN HANH doc    ->  tieng Anh             docker logs, console, cong cu tay
```

Hệ quả: `web/` **không nằm trong phạm vi** change này, dù nó cũng chứa câu tiếng Việt. Còn
`backend/check_api.py` thì có, dù nó thường chạy tay — vì nó là bước 9/9 của pipeline và đầu ra
của nó vào thẳng `docker logs`.

## ② Nút vặn phải là BIẾN MÔI TRƯỜNG, không phải tham số

Đây là quyết định kỹ thuật quan trọng nhất, và nó xuất phát từ hình dạng thật của pipeline:

```
   update_dashboard.py
     └─ subprocess.run  ->  rebuild_db.py
                              └─ subprocess.run  ->  load_gateway.py
```

Ba tiến trình **riêng biệt**. Đặt mức log bằng tham số hàm ở tầng cha **không** làm tầng cháu im
bớt — mỗi tiến trình có không gian biến riêng.

`subprocess.run()` mặc định **kế thừa `os.environ`**. Nên một biến `LOG_LEVEL` đặt một lần ở
ngoài cùng sẽ tự chảy xuống cả ba tầng, không cần truyền tay qua 17 lời gọi:

```
   LOG_LEVEL=WARNING docker compose --profile tools run tools
       -> ca 3 tang deu im, chi con canh bao va so do
```

Đây cũng là cách `PYTHONUNBUFFERED=1` đang làm việc trong `tools.Dockerfile` — cùng cơ chế, đã
chứng minh chạy được trong chính dự án này.

### NHƯNG kế thừa chỉ đúng BÊN TRONG container

Bản đầu của mục này viết *"đặt một lần ở ngoài cùng là tự chảy xuống cả ba tầng"*. **Đúng một
nửa.** Có hai ranh giới, và chúng hoạt động khác nhau:

```
   may that ──[1]──▶ container ──[2]──▶ tien trinh con ──[2]──▶ tien trinh chau

   [1] KHONG tu dong. Compose noi suy `.env` cho CHINH FILE compose, chu khong
       bom bien vao container. Phai khai TUONG MINH trong khoi `environment:`.
   [2] TU DONG. `subprocess.run()` ke thua `os.environ`.
```

Bằng chứng ngay trong file: dịch vụ `api` phải khai từng dòng `TOKEN_LEDGER_DSN:` và
`DASHBOARD_KEY:` mới đưa được chúng vào container — không dòng nào tự vào.

Nên cần **hai** việc, không phải một:

```
   docker-compose.yml   LOG_LEVEL: ${LOG_LEVEL:-INFO}   trong `environment:` cua `tools` va `api`
   db/logs.py           doc os.environ["LOG_LEVEL"]
```

Chỉ có `tools` và `api` cần — `postgres`, `redis`, `nginx` không chạy mã của ta.

Muốn đổi mức cho **một lần chạy** mà không sửa file thì dùng cờ của Docker, không cần cấu hình:

```
   docker compose --profile tools run -e LOG_LEVEL=DEBUG tools
```

## ②b Vì sao tên file là `logs.py` chứ không phải `logging.py`

`db/` **không phải một package** — không có `__init__.py`. Các script nối vào nó bằng:

```python
   sys.path.insert(0, str(ROOT / "db"))     # scripts/rebuild_db.py:81
   import connect                            # scripts/rebuild_db.py:83
```

`insert(0, …)` đặt `db/` **lên đầu** đường tìm module. Nên một file tên `db/logging.py` sẽ
**che khuất `logging` của thư viện chuẩn** trong mọi tiến trình nối vào `db/` — và hỏng theo kiểu
khó lần nhất: `import logging` thành công, chỉ là nhập nhầm file.

Tên `logs.py` không đụng tên nào trong thư viện chuẩn. Đây là ràng buộc bắt buộc, không phải sở
thích đặt tên.

## ③ CÁI BẪY: thứ tự dòng giữa cha và con

Mã hiện tại đã gặp và đã vá cái bẫy này, ghi lại bằng chú thích ở **hai** chỗ:

> `scripts/update_dashboard.py:61` — *"Tiến trình con ghi thẳng ra terminal, còn `print()` ở đây
> đi qua bộ đệm. Không flush thì thông báo lỗi của con HIỆN TRƯỚC tiêu đề bước, và người đọc
> không biết lỗi thuộc về bước nào."*

Đây là lý do phải cẩn thận: **`logging` mặc định ghi ra `stderr`, còn `print` ghi ra `stdout`.**
Nếu đổi tầng cha sang `logging` mà tầng con vẫn `print`, ta tạo lại đúng lỗi đã vá — nhưng lần
này tệ hơn, vì hai luồng khác nhau thì `flush()` của luồng này không giúp gì cho luồng kia.

**Quyết định: mọi thứ ghi ra một luồng duy nhất, và là `stdout`.**

```
   logging.StreamHandler(sys.stdout)     <- KHONG de mac dinh (stderr)
   giu nguyen sys.stdout.flush() truoc moi subprocess.run
```

Vì sao chọn `stdout` chứ không phải `stderr`: Docker gộp cả hai vào `docker logs`, nhưng
`docker compose logs` có thể tách; và các tiến trình con hôm nay đang ghi `stdout`. Đổi cha
theo con rẻ hơn đổi 238 chỗ theo cha.

**Ngoại lệ có chủ ý:** hai thông báo ở `backend/main.py` và `entrypoint.sh` giữ nguyên `stderr`.
Chúng là lỗi chặn khởi động, và `stderr` là chỗ đúng cho chúng.

## ④ Định dạng: bám theo cái đã có, không phát minh

Các thành phần bên thứ ba **không** thống nhất một dạng — nói chúng đều theo *thời gian – mức –
nội dung* là nói quá:

```
   litellm     17:15:02 - LiteLLM:WARNING - …      co MUC, gio KHONG co ngay
   uvicorn     INFO:     127.0.0.1 - "GET …"       co MUC, KHONG co thoi gian
   nginx       172.20.0.5 - - [31/Aug/2026:…]      co thoi gian, KHONG co muc
```

Nên không có sẵn một dạng để bắt chước. Chọn dạng đầy đủ nhất trong ba, vì nó là thứ **duy nhất
đọc được khi ba luồng trộn vào nhau** — thiếu ngày thì không biết dòng thuộc lần chạy nào:

```
   2026-09-01 17:14:32  INFO   step 4/9  pull_web_apps
   2026-09-01 17:14:51  INFO   step 4/9  done in 19s
   2026-09-01 17:15:03  WARN   app: 2,385 token gap between total and prompt+completion
```

**Không dùng JSON.** Nó hợp cho máy gom log, mà dự án chưa có máy gom nào — người đọc là người,
đọc bằng `docker logs`. Thêm JSON bây giờ là trả giá mà chưa mua được gì.

**Không dùng màu.** `docker logs` không phải TTY, mã màu sẽ hiện thành rác `\x1b[32m`.

## ⑤ Băng-rôn `DASHBOARD_OPEN` GIỮ NGUYÊN độ ồn

Chú thích tại chỗ (`backend/main.py:146`) giải thích vì sao nó to:

> *"In ra stderr MỖI LẦN khởi động. Chế độ mở phải luôn nhìn thấy được — một cảnh báo chỉ hiện
> một lần rồi thôi là một cảnh báo bị quên."*

Nó chỉ in khi máy chủ **đang chạy không xác thực**, và khi đó ai gọi `/api/accounts` cũng lấy
được 937 họ tên kèm phòng ban. Đây không phải log tiến độ — đây là cảnh báo an toàn.

**Chỉ đổi ngôn ngữ, giữ nguyên hai hàng `!` và giữ nguyên `stderr`.** Làm nó gọn lại là đổi an
toàn lấy thẩm mỹ, và đó là một cuộc đổi chác tồi.

Cùng lý lẽ cho `SystemExit` khi thiếu `DASHBOARD_KEY`: nó dài vì nó **dạy người đọc cách sửa**,
kèm ba biến thể lệnh cho cmd/PowerShell/bash. Người gặp nó đang bị chặn và cần đúng những dòng
đó.

## ⑥ Xoay vòng log: 4 dòng, và một con số phải chọn

```yaml
   logging:
     driver: json-file
     options:
       max-size: "10m"
       max-file: "3"
```

30 MB mỗi container. Với `api` ghi mọi request thì đó là khoảng vài tuần; với `tools` chạy theo
đợt thì lâu hơn nhiều.

**Đặt ở khối `x-` dùng chung**, không chép vào từng dịch vụ: **13 dịch vụ** mà chép 13 lần thì
lần sau đổi sẽ sót.

Cách này **đã có tiền lệ trong chính file**: `x-litellm: &litellm` ở dòng 36 đang dùng đúng cơ
chế neo YAML đó cho hai instance LiteLLM. Nên đây không phải một lối viết mới, chỉ là dùng lại
lối đã chọn.

---

## Những gì change này CỐ Ý không làm

- **Không đụng `web/`** — tiếng Việt có dấu ở đó là cho người dùng cuối, và nó đang đúng.
- **Không đổi nội dung các dòng số đo.** `billing 1012 | monitoring 606 | app 371 | gateway 1`
  đổi sang tiếng Anh nhưng **giữ nguyên cấu trúc và con số**. Đây là thứ có giá trị nhất trong
  cả luồng log.
- **Không tắt log truy cập của uvicorn.** Nó là bản ghi ai gọi gì, và nó đã đúng định dạng.
  Muốn tắt thì đó là quyết định vận hành, không phải dọn dẹp.
- **Không gom log ra ngoài** (Loki, ELK…). Chưa có nhu cầu, và thêm một hệ thống nữa để đọc log
  của một máy là quá tay.
- **Không đổi `db/migrations/env.py`** — alembic tự sinh, và nó đã dùng `logging` sẵn.
