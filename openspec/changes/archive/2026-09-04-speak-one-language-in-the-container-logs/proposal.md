# Nói một thứ tiếng trong log của container

## Why

`docker compose logs` hiện đổ ra hai phong cách nằm cạnh nhau. Bốn thành phần bên thứ ba viết
tiếng Anh có nhãn thời gian và có mức; mã của ta viết tiếng Việt không dấu, tự chế định dạng,
không có mức nào:

```
   BEN THU BA  (chep tu log THAT, quan sat 31/08-01/09)
   litellm    ^[[92m17:15:02 - LiteLLM:WARNING^[[0m: utils.py:2907 - register_model…
   litellm    INFO:     127.0.0.1:47956 - "GET /health/liveliness HTTP/1.1" 200 OK
   gateway-lb 172.20.0.5 - - [31/Aug/2026:18:21:20 +0000] "POST /v1/chat/completions
              HTTP/1.1" 200 2481 "-" "Python-urllib/3.13" "-"

   MA CUA TA  (chep tu MA NGUON, chua chay lai duoc vi Docker dang tat)
   tools      ========================================================================
              CAP NHAT DU LIEU DASHBOARD
              ========================================================================
              ────────────────────────────────────────────────────────────────────────
              [4/9] Keo Ralli + TLA Hop Dong
              ────────────────────────────────────────────────────────────────────────
   gw-db-init == 1/3  role llmproxy
                 da co, khong dung toi (mat khau KHONG duoc dong bo lai -- xem buoc 3)
   api        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                DASHBOARD_OPEN=1 - MAY CHU DANG CHAY KHONG XAC THUC.
```

> Hai mẫu của `postgres` và của `api` chưa quan sát được trực tiếp — Docker tắt trước khi đọc
> kịp. Phần "mã của ta" trích từ mã nguồn nên chính xác từng ký tự; phần bên thứ ba là log
> thật đã đọc trong phiên. **Việc 1.1 phải chụp lại log thật trước khi sửa.**

### Đo được: 42 dòng kẻ ngang, mỗi lần chạy

Container `tools` chạy một pipeline **lồng ba tầng**, mỗi tầng tự in băng-rôn của mình, và mọi
tiến trình con đều ghi thẳng vào cùng luồng đó. Đếm trên mã nguồn — 9 lần gọi `run_step`, 8 mục
trong `STEPS`:

```
                            KE NGANG 72 KY TU     DONG MANG CHU
   update_dashboard.py       2 + 9x2 + 2 = 22     tieu de + 9 nhan + 9 "xong sau" + 5 = 24
     └─ rebuild_db.py        2 + 8x2 + 2 = 20     tieu de + "Dich:" + 8 nhan + 1     = 11
                            ------------------     -------------------------------------
                                          42                                        35
```

**42 dòng kẻ ngang không mang một thông tin nào.** Chúng chỉ là dấu ngăn.

35 dòng còn lại thì **có** mang thông tin (bước nào, mất bao lâu) — chỗ này rút gọn được nhưng
không xoá được. Mỗi bước còn một dòng thay vì bốn.

### Nhưng phần lớn phần còn lại thì PHẢI giữ

238 lệnh `print` trong ba thư mục container chép vào (`scripts/`, `db/`, `backend/`) không cùng
một loại:

```
   ①  TIEN DO      "[4/9] Keo Ralli + TLA Hop Dong"          -> cat bot duoc
   ②  SO DO DUOC   "billing 1012 | monitoring 606 | app 371"
                   "di bang KHOA TONG 7/41 | trung cache 0"   -> PHAI GIU
   ③  PHAT HIEN    "app lech 2.385 token giua total va prompt+completion"
                   "42 phep kiem | 38 dat | 4 luu y | 0 hong" -> PHAI GIU
```

Loại ② và ③ là thứ được xây có chủ ý, theo quy ước *"đo được thì ghi số đo ngay tại chỗ"*. Rút
gọn chúng là làm mù chính công cụ soát của mình. Change này **không đụng** vào chúng, chỉ đổi
ngôn ngữ và bọc chúng trong một định dạng thống nhất.

### Và một chuyện không phải thẩm mỹ

```
   docker-compose.yml   khong co khoi `logging:`   -> json-file, KHONG GIOI HAN kich thuoc
```

Máy chạy 24/7, uvicorn ghi mọi request, không có xoay vòng. File log lớn dần **vô hạn** cho tới
lúc đầy ổ — và ổ đó cũng đang chứa `pgdata`, tức cả `token_ledger_v2` lẫn sổ Gateway.

## What Changes

- **`db/logs.py`** (mới): một hàm dựng logger dùng chung, đọc mức từ biến môi trường `LOG_LEVEL`.
  Biến môi trường là thứ **tự truyền xuống tiến trình con**, nên đây là cách duy nhất một nút
  vặn điều khiển được cả ba tầng pipeline — xem design ②.
- **`scripts/update_dashboard.py`, `scripts/rebuild_db.py`**: bỏ **42 kẻ ngang**, mỗi bước còn
  **một dòng** thay vì bốn. Chi tiết chuyển xuống mức `DEBUG`.
- **Các script và bộ nạp còn lại**: đổi thông báo sang tiếng Anh, đi qua logger chung. Dòng số
  đo **giữ nguyên nội dung**, chỉ đổi ngôn ngữ.
- **`docker/gateway/entrypoint.sh`, `init-db.sh`**: đổi sang tiếng Anh, bỏ `== 1/3` tự chế.
- **`backend/main.py`**: hai thông báo khởi động sang tiếng Anh. Băng-rôn `DASHBOARD_OPEN`
  **giữ nguyên độ dài và độ ồn** — xem design ⑤.
- **`docker-compose.yml`**: thêm khối `logging:` với `max-size` và `max-file`.

**KHÔNG đụng tầng giao diện.** `web/js/app.js` và `web/index.html` viết tiếng Việt **có dấu**
cho người dùng cuối đọc trên màn hình. Đó là đúng, và đổi nó là làm hỏng thứ đang đúng.

## Impact

- Log đọc như **một hệ thống**, không phải hai nửa ghép lại.
- Có nút vặn thật: `LOG_LEVEL=WARNING` để chạy im, `LOG_LEVEL=DEBUG` để lấy lại toàn bộ chi
  tiết của hôm nay. Không mất gì, chỉ là mặc định khác đi.
- Log không còn lớn vô hạn.
- Rủi ro chính: **thứ tự dòng giữa tiến trình cha và con**. Hai chỗ trong mã hiện tại đã ghi
  lại cái bẫy này bằng chú thích và vá bằng `flush()`. Đổi luồng ghi mà quên chuyện đó thì
  thông báo lỗi của tiến trình con hiện **trước** tiêu đề bước, và người đọc quy lỗi nhầm bước
  — xem design ③.
- Rủi ro thứ hai: đây là change đụng **nhiều file nhất từ trước tới nay** mà **không có phép
  kiểm tự động nào** bảo vệ, vì không ai viết test cho câu chữ log. Chống bằng cách chạy lại
  toàn bộ pipeline và đối soát 24 khoá mốc — xem tasks mục 7.
