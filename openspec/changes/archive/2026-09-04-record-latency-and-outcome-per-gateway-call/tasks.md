# Tasks

Quy ước: mỗi mục đo được thì **ghi số đo ngay tại chỗ**, không ghi "đã kiểm tra".

## 1. Ghi mốc trước khi đổi

- [x] 1.1 `fact_call` **8.669 dòng / 50.113.730 token / 17 cột** — app 8.631, gateway 38
- [x] 1.2 app 371/112.775.370 · billing 1.012/751.189.404 · monitoring 606/496.933.793 · gateway 1/45.187
- [x] 1.3 `var/baseline-2026-08-31-truoc-006.json`
- [x] 1.4 success **40 dòng** (38 có tag, 45.229 token) · failure **5 dòng** (3 có tag, 28 token)

## 2. Migration 006

- [x] 2.1 `006_do_tre` ← `005_gateway_cost`, forward-only
- [x] 2.2 `duration_ms INTEGER` nullable, không DEFAULT
- [x] 2.3 `outcome TEXT` nullable, không DEFAULT — 8.631 dòng app giữ NULL
- [x] 2.4 `error_code TEXT` nullable
- [x] 2.5 Cả ba có `COMMENT ON COLUMN`, nêu rõ NULL nghĩa là gì
- [x] 2.6 **9/9 mốc khớp**: 8.669 dòng · 50.113.730 token · app 8.631 · gateway 38 · 17→**20 cột** · head `006_do_tre` · ba cột mới NULL toàn bộ

## 3. Sửa `db/load_gateway.py`

- [x] 3.1 `WHERE status IS NOT NULL` thay cho `= 'success'`
- [x] 3.2 Lấy thêm `status`, `request_duration_ms`, `error_information.error_code`
- [x] 3.3 `NULLIF(request_duration_ms, 0)` ngay ở tầng SQL
- [x] 3.4 `NULLIF(…, '')` — đo: **3/5** dòng hỏng mang chuỗi rỗng
- [x] 3.5 `outcome` chép nguyên `status`
- [x] 3.6 4 dòng không có tag vẫn bị bỏ và vẫn được đếm
- [x] 3.7 Vế nguồn bỏ lọc `success`. Đối chiếu: nguồn **45 dòng/45.257 token** = đích **41/45.201** + bỏ qua **4/56**
- [x] 3.8 In thêm: nạp lượt hỏng · model chưa khai · hỏng trước khi chốt tuyến · `duration_ms` NULL · **phân bố mã lỗi**

## 4. Sửa `db/build_usage_daily.py`

- [x] 4.1 Thêm `AND outcome = 'success'`. **Lỗ rò đã chứng minh TRƯỚC khi vá**: chạy không có bộ lọc ra **45.201** thay vì 45.187 — rò đúng **14 token**
- [x] 4.1b Tách thành `model_chua_khai` và `hong_truoc_khi_chot_tuyen`. Chạy thật: **0** và **2** — đúng phân biệt việc-phải-làm với chuyện-bình-thường
- [x] 4.2 Phép kiểm token gateway trong nghiệm thu cũng lọc `outcome`
- [x] 4.3 **Bốn nguồn khớp mốc 1.2 tuyệt đối**, không đổi một token nào

## 5. Sửa `scripts/audit_db.py`

- [x] 5.1 Đã kiểm — **không phải sửa**. Nó đọc `fact_usage_daily`, bảng đó đã được lọc từ 4.1
- [x] 5.2 Thêm `Luot hong khong lot vao bang tong hop` — so `fact_usage_daily` gateway với `fact_call` gateway `outcome='success'`
- [x] 5.3 Thêm `Khong dong nao co duration_ms = 0`
- [x] 5.4 Chạy đầy đủ, đọc hết đầu ra: **38 phép kiểm · 34 đạt · 4 lưu ý · 0 hỏng**

## 6. Nghiệm thu bằng dữ liệu thật

- [x] 6.1 gateway **38 → 41**, đúng bằng 3 dòng hỏng có tag
- [x] 6.2 Dải **609 – 3.136 ms**, và **38/38** dòng thành công đều có độ trễ
- [x] 6.3 3 dòng hỏng: `duration_ms` **NULL toàn bộ**, không có số 0 nào
- [x] 6.4 **một `401` (14 token) và hai NULL (0 token)** — đúng dự đoán
- [x] 6.5 41 → 41 → 41, không đổi
- [x] 6.6 Lệch **đúng 1 khoá**: `fact_call` 8.669→8.672 = +3 dòng hỏng cố ý thêm. `usage_resolved` **không đổi** — chứng minh bộ lọc `outcome` hoạt động
- [x] 6.7 Gateway **p95 = 1,822 s** (chính xác, 38 giá trị thô) · monitoring **p95 = 63,6 s** nội suy trong **thùng 33,55–67,11 s**. **Thùng rộng 33,6 giây** → mọi p95 rút từ nó sai số hàng chục giây. Nhưng hai số này **chưa so được**: monitoring dừng ở 28/08, gateway chỉ có 31/08 — khác giai đoạn, có thể khác cả phép đo. **Không kết luận bên nào đúng**

## 7. Tài liệu

- [x] 7.1 Mục 5 (thêm độ trễ + mã lỗi, kèm bẫy `0` và chuỗi rỗng) · mục 7 (ba → **bốn** quy tắc, thêm quy tắc `DO UPDATE`) · mục 9 (thêm điều chưa chắc về so sánh độ trễ)
- [x] 7.2 `docs/reference/do-tre-va-ket-cuc-luot-goi-31-08.md` — 8 mục
- [x] 7.3 Ghi ở nhật ký mục 6 và ở `docs/reference/gateway-architecture-and-agent-integration.md` mục 7