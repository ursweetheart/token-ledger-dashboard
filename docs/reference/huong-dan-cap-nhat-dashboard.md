# Hướng dẫn cập nhật dữ liệu dashboard (13/08/2026)

> Dashboard là trang tĩnh: mọi số liệu nằm cứng trong `app.js`, không có `fetch` nào.
> "Cập nhật dashboard" = thu thập lại các nguồn rồi sinh lại khối `SEED_DAYS`.
> Tài liệu này mô tả chuỗi đó và những chỗ nó hay gãy.

---

## Chạy

```bash
python scripts/cap_nhat_dashboard.py
```

Hết. Khoảng 12–17 phút, phần lớn là bước kéo Cloud Monitoring.

### Lần đầu: tạo `.env`

```bash
cp .env.example .env
```

Rồi điền một trong hai:

```bash
# Cách A — script tự đăng nhập, không phải dán gì
RALLI_USER=...
RALLI_PASS=...
HD_USER=...
HD_PASS=...

# Cách B — dán JWT sẵn (ưu tiên hơn A nếu điền cả hai)
RALLI_JWT=eyJ...
HD_JWT=eyJ...
```

`.env` đã nằm trong `.gitignore`. Biến môi trường thật (`export`/`set`) luôn thắng giá trị trong file.

Thử riêng phần xác thực trước khi chạy cả chuỗi:

```bash
python scripts/pull_web_apps.py --chi-kiem-token
```

Nó chỉ lấy token, in hạn dùng rồi dừng. **Không in token ra màn hình.**

---

## Chuỗi 7 bước

```
[0/7]  Kiểm hoá đơn đã mới chưa          vài giây   ← DỪNG nếu cũ
[1/7]  Lấy token 2 web app               vài giây   ← DỪNG nếu hỏng
[2/7]  Kéo Cloud Monitoring              10-15 ph
[3/7]  Gộp các đợt kéo Monitoring        ~30 giây
[4/7]  Kéo Ralli + TLA Hợp Đồng          ~1 phút
[5/7]  Gộp hoá đơn từ 7 file Console     ~1 giây
[6/7]  Sinh khối dữ liệu dashboard       ~4 giây
[7/7]  Vá vào app.js                     ~1 giây
```

Hỏng bước nào là **dừng ngay**. Không bước nào chạy tiếp trên đầu ra dở dang của bước trước.

**Vì sao bước 0 và 1 đứng đầu:** bước 2 mất hơn 10 phút. Phát hiện thiếu file hoá đơn hoặc token hỏng *sau* đó là vứt đi 10 phút vô cớ, trong khi cả hai phép kiểm chỉ mất vài giây. Bước 1 đăng nhập một lần rồi vứt token đi, bước 4 đăng nhập lại — hai lần đăng nhập rẻ hơn nhiều so với một lần kéo Monitoring bị bỏ.

### Cờ dòng lệnh

| Cờ | Dùng khi |
|---|---|
| `--bo-monitoring` | Đã kéo Monitoring hôm nay rồi. Vẫn gộp lại từ các đợt đã có. |
| `--hoa-don-cu` | Cố ý chạy với hoá đơn chưa tải mới. |
| `--ngay-monitoring N` | Đổi cửa sổ kéo (mặc định 196). Google chỉ giữ một phần, xin rộng không hại gì. |

---

## Từng script làm gì

| Script | Vai trò | Chạy riêng được |
|---|---|---|
| `scripts/cap_nhat_dashboard.py` | Điều phối cả 7 bước | — |
| `scripts/pull_monitoring.py` | Kéo time series từ Cloud Monitoring qua `gcloud` | ✓ |
| `scripts/gop_monitoring.py` | Gộp nhiều đợt kéo, khử trùng lặp | ✓ |
| `scripts/pull_web_apps.py` | Kéo Ralli + TLA HĐ qua API của chúng | ✓ |
| `scripts/gop_billing.py` | Gộp 7 CSV Console thành một file chuẩn hoá | ✓ |
| `test/sinh_du_lieu_dashboard.py` | Sinh `test/seed-days-that.js` từ mọi nguồn | ✓ |
| `test/va_app_js.py` | Vá `seed-days-that.js` vào `app.js` | ✓ |

Cả ba script `pull_*` và `gop_*` đều **ghi vào thư mục mới theo ngày, không bao giờ ghi đè đợt cũ**. Xem §"Đừng xoá thư mục kéo cũ" để biết vì sao đó không phải sự cẩn thận thừa.

---

## Việc vẫn phải làm tay: tải hoá đơn

Google Cloud Console không cho tải báo cáo GMSSub qua API với quyền hiện có. Mỗi lần cập nhật:

1. Cloud Console → Billing → Reports
2. Tải 7 file, mỗi project một file
3. Bỏ vào `data/billing/`, giữ nguyên tên `rangdong.com.vn - GMSSub_Reports, <khoảng ngày>,<TÊN HIỂN THỊ>.csv`

Bước 0 đọc cột `Date` trong các file đó. Ngày mới nhất cũ hơn hôm qua ⇒ dừng.

**Không được chạy tiếp với hoá đơn cũ.** Khi đó dashboard sẽ có request của hôm nay nhưng token của tuần trước — sai mà trông như thật.

⚠️ **Tên file mang tên hiển thị, không phải project ID.** `AI-sale_agent` ↔ `tranquil-post-471401-c1`, không chữ nào chung. Bảng ánh xạ 7 dòng khai báo cứng trong `scripts/gop_billing.py`. Tên lạ ⇒ script dừng và in tên đó ra. Đoán gần đúng sẽ trúng 5/7 và trượt đúng 2 project chiếm **81% số tiền**.

---

## Khi hỏng

### "Hoa don CU: ngay moi nhat 2026-08-XX"
Tải lại 7 file GMSSub. Xem mục trên.

### "khong co token va khong co tai khoan de dang nhap"
Chưa có `.env`, hoặc chưa điền. `cp .env.example .env` rồi điền.

### "HTTP 401/403 khi dang nhap - sai tai khoan/mat khau"
Sai user/pass. Script không thử lại vì đổi kiểu body cũng vô ích.

### "dang nhap OK nhung khong tim thay token; khoa: [...]"
Đăng nhập được nhưng tên trường chứa token khác dự kiến. Script đã thử `access_token`, `token`, `accessToken`, `jwt`, và cả `data.<...>`. Xem danh sách khoá nó in ra rồi bổ sung vào `dang_nhap()` trong `scripts/pull_web_apps.py`.

### "HTTP 422" khi đăng nhập TLA HĐ
TLA HĐ không phơi `openapi.json` nên kiểu body là **suy đoán**. Script tự thử JSON rồi form-encoded. Hỏng cả hai thì mở DevTools → Network, đăng nhập tay một lần, xem request thật gửi gì.

### Dashboard mở lên vẫn hiện số cũ
`app.js` lưu state trong `localStorage`. `va_app_js.py` có tăng số phiên bản khoá mỗi lần chạy, nhưng nếu bạn chạy nó nhiều lần rồi khôi phục file thì hai lần chạy khác nhau có thể trùng số. Mở F12 → Application → Local Storage → xoá các khoá `agent-dash-state-*` rồi tải lại.

### `gop_monitoring.py` báo "lech gia tri"
Cùng một phép đo, cùng mốc thời gian, hai đợt kéo cho số khác nhau. Script giữ giá trị của **đợt mới** và in ví dụ ra. Đo ngày 13/08: 3 khoá lệch trên 500.879 khoá chồng nhau (0,0006%), và đợt mới đều cho số **nhỏ hơn** — dấu hiệu Google hạ độ phân giải dữ liệu cũ theo thời gian. Số ít thì bỏ qua được; nhiều lên thì phải xem lại quy tắc ưu tiên.

---

## Ba cái bẫy đã biết

### 1. Đừng xoá thư mục kéo Monitoring cũ

Cửa sổ lưu giữ của Google **không có độ rộng cố định**. Đo hai lần bằng cùng script:

| Ngày kéo | Ngày sớm nhất trả về | Độ rộng |
|---|---|---|
| 06/08/2026 | 22/01/2026 | 196 ngày |
| 13/08/2026 | **23/04/2026** | **112 ngày** |

Bảy ngày trôi qua, mép cửa sổ nhảy **91 ngày**. Dữ liệu 22/01–22/04 giờ chỉ còn tồn tại trên đĩa ở `data/raw_google_console/du_lieu_giam_sat/2026-08-06-1m/`.

⇒ Một đợt kéo đơn lẻ **không còn phủ hết dải ngày**. Phải gộp. Xoá thư mục cũ là mất vĩnh viễn.

### 2. Ngày cuối của mỗi bản export hoá đơn là số TẠM

Đối chiếu bản export 05/08 với bản 13/08: 0 dòng biến mất, nhưng **8 dòng bị viết lại — toàn bộ nằm trên ngày cuối cùng** của bản cũ. Mức lệch không nhỏ:

```
SKU 07D6-73CA-C859    22.326  ->  2.646.520 token   (118 lần)
SKU F2C1-F842-5D84    55.829  ->  1.606.920 token   ( 29 lần)
```

Nguyên nhân: hoá đơn tính theo **giờ Pacific**. Tải lúc 10h sáng giờ Việt Nam là ngày Google mới chạy được ~20 tiếng.

⇒ Lịch sử bất biến từ ngày kề-cuối trở về trước (2.251/2.259 dòng khớp tuyệt đối), nhưng **ngày cuối luôn phải coi là chưa chốt**.

### 3. Ngày cuối cùng trên dashboard thiếu tiền

Monitoring và Ralli có dữ liệu tới hôm nay; hoá đơn chỉ tới hôm qua. Nên ngày cuối trên dashboard hiện **có request nhưng gần như không có token từ billing** — trông như ngày dùng nhiều mà không tốn tiền. Đó là thiếu nguồn, không phải tiết kiệm.

---

## Kỷ luật chỉ-đọc

Mọi endpoint dữ liệu của `pull_web_apps.py` là `GET` trên **danh sách trắng khai báo cứng**. Không phải sự cẩn thận thừa: hai API này còn phơi ra

```
POST   /trigger-data-fetch          POST   /logs/cleanup
POST   /api/ctda/refresh-data       DELETE /users/{id}
POST   /upload-product-excel        PUT    /api/units/{id}
```

Ngoại lệ **duy nhất** là `POST /auth/login` để lấy token — được chọn có ý thức ngày 13/08/2026 để chạy được một lệnh. Token không bao giờ được in ra màn hình hay ghi xuống đĩa.

---

## Sau khi chạy

Bước 7 chỉ đổi **3 loại literal** trong `app.js`: khối `SEED_DAYS`, hằng `STORE`, và khoảng ngày mặc định. Không hàm nào, không thẻ HTML nào bị đụng. Kiểm nhanh:

```bash
node --check app.js
git diff --stat app.js
```

Khoảng ngày mặc định được **suy từ ngày cuối cùng có dữ liệu**, không ghim cứng — nên dashboard mở ra luôn ở tháng hiện tại mà không cần sửa gì thêm.

Chạy hai lần liên tiếp phải cho `app.js` giống hệt nhau về nội dung (chỉ khác `STORE`). Nếu khác, có nguồn nào đó không xác định — dừng lại tìm hiểu trước khi tin kết quả.
