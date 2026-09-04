## 1. Dựng khung và bảng ánh xạ

- [x] 1.1 Tạo `scripts/gop_billing.py` với docstring nêu rõ: mục đích, quy tắc áp dụng, cách nghiệm thu — theo đúng lối `db/nap_billing.py` đang dùng
- [x] 1.2 Khai báo bảng ánh xạ 7 dòng `tên hiển thị → project ID` như hằng số ở đầu file, kèm ghi chú vì sao không được đoán
- [x] 1.3 Tạo thư mục đầu ra `data/da_xu_ly/billing/` và thêm vào `.gitignore` nếu file dẫn xuất không cần theo dõi
- [x] 1.4 Viết hàm đọc `dim_agent.gcp_project_id` từ `db/token_ledger.sqlite` ở chế độ chỉ đọc (`mode=ro`, dùng `Path.as_posix()`)
- [x] 1.5 Kiểm chéo: mọi project ID trong bảng ánh xạ phải tồn tại trong `dim_agent`, không thì dừng và nêu ID nào không tra được

## 2. Đọc và chuẩn hoá file thô

- [x] 2.1 Tìm file đầu vào bằng glob `data/billing/*GMSSub*.csv`, dừng nếu không thấy file nào (nêu thư mục và mẫu đã dùng)
- [x] 2.2 In danh sách file đã chọn kèm số dòng từng file, trước khi xử lý
- [x] 2.3 Bóc tên hiển thị từ phần sau dấu phẩy cuối cùng của tên file, tra bảng ánh xạ bằng so khớp chính xác; tên lạ thì dừng và in cả danh sách tên đang khai báo
- [x] 2.4 Đọc CSV bằng `encoding="utf-8-sig"`, chuyển 5 cột tiền sang `Decimal` thẳng từ chuỗi gốc (không qua `float`)
- [x] 2.5 Bóc dấu phẩy ngăn nghìn khỏi `Usage amount` rồi chuyển sang `int`
- [x] 2.6 Gọi `db/quy_tac.py::suy_loai()` để gán `loai`; `None` thì dừng và in mã SKU, tên SKU đầy đủ, số dòng và tổng tiền của SKU đó

## 3. Nghiệm thu tầng 1 — từng dòng

- [x] 3.1 Kiểm `round(Cost − Savings programs − Other savings, 2) == Subtotal` bằng `Decimal` chính xác, không ngưỡng sai số; với dòng có giảm giá bằng 0 thì kiểm thêm `Cost == round(Unrounded, 2)`
- [x] 3.2 Kiểm `round(Unrounded, 2) == Subtotal` với `ROUND_HALF_UP`
- [x] 3.3 Khi lệch: dừng và in ngày, project, mã SKU cùng cả 5 giá trị tiền của dòng đó
- [x] 3.4 Đếm số dòng có `Savings programs != 0` hoặc `Other savings != 0`; nếu có thì in cảnh báo nổi bật (số dòng + tổng tiền giảm) nhưng **vẫn tiếp tục**

## 4. Nghiệm thu tầng 2 — từng project

- [x] 4.1 Với mỗi file thô, so số dòng và tổng `Unrounded subtotal` với các dòng mang project tương ứng trong kết quả
- [x] 4.2 Khi lệch: dừng và in tên project, cặp số dòng và cặp tổng tiền của cả hai phía

## 5. Ghi đầu ra

- [x] 5.1 Sắp xếp kết quả theo `(project, ngay, sku_id)` để hai lần chạy cho ra file giống hệt nhau
- [x] 5.2 Ghi ra `data/da_xu_ly/billing/billing_<YYYY-MM-DD>.csv` với 12 cột (7 cột định danh + 5 cột tiền theo tên ở design D6), **chỉ sau khi** mọi phép kiểm tầng 1–2 đạt
- [x] 5.3 Đảm bảo không ghi file dở khi có lỗi: dựng xong toàn bộ nội dung trong bộ nhớ rồi mới mở file để ghi
- [x] 5.4 In tổng kết: số dòng, tổng tiền, phân bố theo `loai`, đường dẫn file đã ghi

## 6. Nghiệm thu tầng 3 — đối chiếu bản gộp tay

- [x] 6.1 Thêm cờ tuỳ chọn `--doi-chieu <đường dẫn>` (mặc định KHÔNG chạy, để bản export tương lai không bị chặn)
- [x] 6.2 So trên tập bộ `(ngay, project, sku_id, so_luong, chi_phi_usd)`; cột `loai` không tham gia vì bản gộp tay không có
- [x] 6.3 Báo đạt chỉ khi trùng khít; khi lệch thì in tối đa 10 ví dụ kèm cả hai phía rồi thoát mã khác 0
- [x] 6.4 Chạy thật: `python scripts/gop_billing.py --doi-chieu data/billing/billing_gop_tru_CTDA.csv` phải ra **2.259 dòng · $270,9517 · trùng khít**

## 7. Tự soát theo SKILL `tu-soat`

- [x] 7.1 Chạy lại hai lần liên tiếp, `diff` hai file đầu ra — phải giống hệt tới từng byte
- [x] 7.2 Kiểm `data/billing/` không bị sửa: so nội dung và thời điểm sửa đổi trước/sau khi chạy
- [x] 7.3 Thử ca hỏng có chủ đích: đổi tên một file thành tên lạ → script phải dừng, không tạo file đầu ra
- [x] 7.4 Thử ca hỏng thứ hai: bỏ bớt một file đầu vào → tầng 2 vẫn đạt, tầng 3 phải trượt và nêu rõ thiếu dòng
- [x] 7.5 Kiểm in ấn không ném `UnicodeEncodeError` trên console Windows (đặt `PYTHONIOENCODING=utf-8` hoặc ghi UTF-8 tường minh)
- [x] 7.6 Xác nhận không thêm phụ thuộc ngoài thư viện chuẩn
