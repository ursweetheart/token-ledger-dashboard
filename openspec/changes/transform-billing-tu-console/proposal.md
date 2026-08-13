## Why

Chuỗi xử lý hoá đơn Google hiện **đứt ở khúc đầu**: 7 file CSV tải tay từ Cloud Console được gộp thành `data/billing/billing_gop_tru_CTDA.csv` bằng tay, không script nào trong repo sinh ra file đó (grep cả repo: 11 chỗ *đọc*, 0 chỗ *sinh*). Nửa sau (`db/nap_billing.py`) đã chạy sạch, có nghiệm thu — chỉ nửa đầu là thao tác người, không lặp lại được, không kiểm được.

Việc này chặn mọi thứ phía sau: mỗi lần có bản export mới lại phải ngồi gộp tay, và không ai chứng minh được bản gộp lần này giống bản gộp lần trước về cách làm. Đây cũng là thời điểm rẻ nhất để làm, vì **bản gộp hiện có đóng vai bài kiểm tra hồi quy miễn phí**: script mới phải tái tạo đúng nó — 2.259 dòng, $270,9517 — thì mới coi là đúng.

## What Changes

- **Thêm `scripts/gop_billing.py`**: đọc 7 file `data/billing/*GMSSub*.csv`, xuất một file chuẩn hoá vào `data/da_xu_ly/billing/billing_<ngày>.csv`. Một lệnh, không tham số bắt buộc.
- **Ánh xạ project bằng khai báo, không đoán.** File Console không có cột project; thông tin đó chỉ nằm ở tên file, và tên file mang *tên hiển thị* chứ không phải *project ID* (`AI-sale_agent` ↔ `tranquil-post-471401-c1` — không chữ nào chung). Bảng ánh xạ 7 dòng được khai báo tường minh; tên file lạ ⇒ dừng, in ra tên đó. Đoán gần đúng sẽ trúng 5/7 và trượt đúng 2 project chiếm **81% số tiền**.
- **Giữ cả 5 cột tiền của Google** (`Cost`, `Savings programs`, `Other savings`, `Unrounded subtotal`, `Subtotal`) thay vì chỉ `Unrounded` như bản gộp tay. Mục đích không phải lưu thêm dữ liệu mà là **biến một giả định không kiểm được thành bất biến kiểm được**: hôm nay `Savings = 0` trên 2.259/2.259 dòng nên `Cost == round(Unrounded, 2)`; ngày Gimasys cấp credit, hai vế đó tách nhau và phép kiểm sẽ kêu thay vì tiền lặng lẽ sai. *(Bất biến này đặt ở độ chính xác xu, không phải độ chính xác đầy đủ — `Cost` cũng đã làm tròn tới xu; xem `design.md` D3.)*
- **`Unrounded subtotal` là cột tiền chuẩn.** `Cost`/`Subtotal` làm tròn tới xu ở mức từng dòng, khiến **740/2.259 dòng (32,8%) hiện $0,00** dù mang $0,83 tiền thật và 8,06 triệu token. Sai số này lệch một chiều (báo thiếu) vì dòng nhỏ chỉ tròn xuống 0 được, không có gì tròn lên bù.
- **Dùng lại `db/quy_tac.py`** cho phân loại `cached → output → input`, không viết bản thứ hai. Thứ tự này bắt buộc: SKU `911A-8880-A243` tên đầy đủ là *"Generate content **OUTPUT** token count … short **INPUT** text"*, kiểm sai thứ tự thì 38,9% chi phí nhảy nhầm cột **mà tổng vẫn đúng**.
- **Xử lý đúng định dạng thô**: dấu phẩy ngăn nghìn (`"21,235"`), BOM UTF-8, tên file chứa dấu gạch dài `—` và khoảng ngày thay đổi theo mỗi lần export (khớp theo mẫu, không ghim tên).
- **Không đụng tới**: `db/01_schema.sql`, `db/nap_billing.py`, `db/token_ledger.sqlite`, và `data/billing/billing_gop_tru_CTDA.csv` (giữ nguyên làm mốc đối chiếu).

**Ngoài phạm vi, để đợt sau:** thêm 4 cột tiền vào `fact_billing_daily`; thêm cột mốc UTC + luật giờ mùa hè; rải chi phí sang ngày ICT; chuyển `DELETE` → `UPSERT`; bỏ hai hằng số nghiệm thu ghim cứng trong `nap_billing.py`.

## Capabilities

### New Capabilities

- `gop-billing-console`: chuẩn hoá và gộp các bản xuất hoá đơn từ Google Cloud Console thành một file duy nhất — ánh xạ project theo khai báo, đọc đúng định dạng thô, chọn cột tiền chuẩn, giữ đủ cột kiểm chứng, phân loại SKU, ghi đầu ra có ngày trong tên.
- `nghiem-thu-gop-billing`: các bất biến phải đúng trước khi công nhận đầu ra, và hành vi **từ chối** khi sai — dừng hẳn, không ghi file dở, in ra đủ thông tin để sửa.

### Modified Capabilities

*(không có — `openspec/specs/` hiện trống, đây là spec đầu tiên của repo)*

## Impact

**Thêm mới**
- `scripts/gop_billing.py`
- `data/da_xu_ly/billing/` (thư mục đầu ra)

**Đọc, không sửa**
- `data/billing/*GMSSub*.csv` — 7 file thô
- `data/billing/billing_gop_tru_CTDA.csv` — mốc đối chiếu
- `db/quy_tac.py` — `suy_loai()`
- `db/token_ledger.sqlite` — chỉ đọc `dim_agent` để lấy `gcp_project_id`

**Phụ thuộc**: không thêm gói ngoài. Thuần thư viện chuẩn (`csv`, `decimal`, `pathlib`, `sqlite3`) — giữ đúng kỷ luật hiện có của pipeline, và `decimal` là bắt buộc chứ không phải tuỳ chọn: `float` không kiểm được đẳng thức tiền tệ.

**Rủi ro đã biết**
- Bảng ánh xạ 7 dòng gõ tay sẽ lỗi thời khi có project thứ 8. Chấp nhận được vì lúc đó script **dừng và báo tên lạ**, không nạp im lặng.
- Ralli/CTDA không có billing export nên nằm ngoài cả 7 file (đúng như tên `_tru_CTDA`). Không thay đổi gì ở đợt này.
