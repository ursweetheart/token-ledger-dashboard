# Tasks

Quy ước: mỗi mục đo được thì **ghi số đo ngay tại chỗ**, không ghi "đã kiểm tra".

Change này **không có phép kiểm tự động nào bảo vệ** — không ai viết test cho câu chữ log. Nên
mục 1 và mục 7 là chỗ duy nhất bắt được lỗi, và không được bỏ.

## 1. Ghi mốc trước khi đổi

- [x] 1.1 `var/log-truoc-khi-doi.txt` — **87 dòng**. CHỈ chụp `load_gateway` + `build_usage_daily` + `audit_db`: các bước kéo dữ liệu gọi `gcloud` và đăng nhập hai web app thật, chạy chúng chỉ để chụp *chữ* là đụng hệ thống thật mà không mua được gì. Mọi dòng số đo đều nằm trong ba script này
- [x] 1.2 87 dòng · kẻ ngang **42** · dòng khung **35** (mốc tĩnh) · **24 dòng mang số đo**
- [x] 1.3 `var/baseline-truoc-log.json` — 24 khoá
- [x] 1.4 `var/so-do-truoc-khi-doi.txt` — **24 dòng**, lưới an toàn của cả change
- [x] 1.5 Mốc **238** `print()` (backend 14 · db 60 · scripts 164)

## 2. `db/logs.py` — logger dùng chung

- [x] 2.1 `db/logs.py` — `get_logger()`, mức từ `LOG_LEVEL`, mặc định `INFO`. **Tên file là `logs.py`** — `db/` nằm đầu `sys.path` nên `logging.py` sẽ che thư viện chuẩn, xem design ②b
- [x] 2.2 Đo: ghi ra **stdout**, không phải stderr — `StreamHandler(sys.stdout)` — **KHÔNG** để mặc định `stderr`, xem design ③
- [x] 2.3 `2026-09-02 15:47:42  INFO   …` — giờ VN ép cứng, vì container chạy UTC còn máy dev chạy giờ VN
- [x] 2.4 **Không màu** — `docker logs` không phải TTY, mã màu sẽ hiện thành rác
- [x] 2.5 Gọi 3 lần → in **đúng 1 lần**. Chặn bằng kiểm `root.handlers` trước khi thêm
- [x] 2.6 Phép thử âm **6/6 đạt**: không đặt·INFO·`debug` thường·rỗng → INFO; `RAC!!!` → cảnh báo stderr rồi về INFO, mã thoát 0; WARNING → 1 dòng

## 3. Hai script in băng-rôn

- [x] 3.1 `update_dashboard.py`: **0 kẻ ngang, 0 `print`**. Mỗi bước 2 dòng (bắt đầu + xong-sau-Ns) thay vì 5 — cần dòng bắt đầu vì bước kéo Monitoring chạy 10–15 phút
- [x] 3.2 `rebuild_db.py`: **0 kẻ ngang, 0 `print`**. Mỗi bước 4 dòng → **1 dòng**
- [x] 3.3 Giữ `sys.stdout.flush()`. Phát hiện: `logging.StreamHandler` **đã tự flush** sau mỗi bản ghi, nên nó là bảo hiểm chứ không bắt buộc — đã ghi rõ trong chú thích
- [x] 3.4 5 dòng hướng dẫn → 2 dòng `DEBUG`
- [x] 3.5 Đo lại: **42 kẻ ngang → 0** · `print()` 238 → 150 (150 còn lại đều là khối BÁO CÁO hoặc đã tiếng Anh)

## 4. Bộ nạp và script còn lại

- [x] 4.1 Đổi hết sang tiếng Anh qua logger chung: 6 bộ nạp `db/` + `build_usage_daily` + `load_gateway` + 12 script `scripts/`+`backend/`
- [x] 4.2 **42/42 con số còn nguyên**, đối chiếu với `var/so-do-truoc-khi-doi.txt`
- [x] 4.3 Cảnh báo dùng `log.warning`, không hạ xuống `INFO`
- [x] 4.4 `backend/check_api.py` đã dịch — 45 chuỗi
- [x] 4.5 `audit_db.py` **giữ `print`** cho khối báo cáo. Phát hiện lúc triển khai: LOG khác BÁO CÁO, đóng dấu thời gian lên từng dòng bảng là kém chuyên nghiệp hơn — xem nhật ký mục 4

## 5. Script shell của Gateway

- [x] 5.1 `entrypoint.sh` — 4 chuỗi, giữ `stderr`
- [x] 5.2 `init-db.sh` — **19/22** `echo` (3 dòng còn lại không mang chữ Việt). Bỏ `== 1/3` → `step 1/3:`
- [x] 5.3 `sh -n` sạch cả hai file; không đổi một lệnh thoát nào

## 6. `backend/main.py` và compose

- [x] 6.1 Đã dịch, **giữ nguyên độ dài** và ba biến thể cmd/PowerShell/bash
- [x] 6.2 Đã dịch, **giữ hai hàng `!` và giữ `stderr`**
- [x] 6.3 `x-logging: &logging` — `max-size: 10m`, `max-file: 3`, gắn cho **13/13** dịch vụ
- [x] 6.3b `LOG_LEVEL: ${LOG_LEVEL:-INFO}` trong `environment:` của `tools` và `api`
- [x] 6.4 Đã áp cho cả 13, kể cả `api-db-init` và `gateway-db-init` (chạy xong là thoát)
- [x] 6.5 `docker compose config` SẠCH · `--profile gateway` SẠCH · sau nội suy: 14 lần `max-size` (13 dịch vụ + 1 định nghĩa neo)

## 7. Nghiệm thu

- [x] 7.1 `var/rebuild-cuoi.txt` + `var/audit-cuoi.txt`, cả hai mã thoát 0
- [x] 7.2 **Mất 0/42 con số**
- [x] 7.3 **24/24 khoá khớp, 0 lệch** — sau khi `rebuild_db.py` xoá sạch và dựng lại từ đầu
- [x] 7.4 `LOG_LEVEL=DEBUG` → 11 dòng · `INFO` → 11 · truyền xuống con: rebuild_db **70 dòng**
- [x] 7.5 `LOG_LEVEL=WARNING` → load_gateway **0 dòng**, rebuild_db **17 dòng**
- [x] 7.6 **Đạt** — ép sai mật khẩu DSN, traceback của tiến trình con nằm ĐÚNG SAU dòng `[1/8] Billing`
- [x] 7.7 **0 dòng tiếng Việt**. Quét cả mã nguồn (chuỗi trốn trong SQL không lộ ở đầu ra) — bắt được `'(khong co ma)'` trong `COALESCE`
- [x] 7.8 `git diff --stat web/` **rỗng**
- [x] 7.9 `docker inspect token-ledger-api` → `json-file max-size=10m max-file=3`

## 8. Tài liệu

- [x] 8.1 `docs/reference/quy-uoc-log-01-09.md` — 10 mục
- [x] 8.2 Nhật ký nằm chung trong file trên
- [x] 8.3 `.env.example` — `LOG_LEVEL` kèm giải thích ba mức và cách đổi cho một lần chạy
