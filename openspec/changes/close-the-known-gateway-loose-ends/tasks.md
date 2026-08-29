## 1. Đổi tên thư mục sao lưu

- [x] 1.1 `grep -r "2026-26-08"` toàn repo — 6 kết quả, không chỗ nào là script sống; 3 là
      artifact của chính change này, 3 là nhật ký/tasks dated ghi lại lịch sử, giữ nguyên
- [x] 1.2 Đổi tên `D:\RangDonk\token-ledger-backup\2026-26-08` → `2026-08-26`
- [x] 1.3 `ls D:\RangDonk\token-ledger-backup` — xác nhận cả ba thư mục đều theo định dạng
      `YYYY-MM-DD` (`2026-08-08`, `2026-08-26`, `2026-08-26-truoc-cutover`)

## 2. Thêm `gemini-3.6-flash` vào danh mục model

- [x] 2.1 Xác nhận lại bằng chứng model đang phục vụ thật (nhật ký 26/08, mục 6 và 16.7 —
      Google trả 404 kèm "use models/gemini-3.6-flash")
- [x] 2.2 Thêm dòng `(11, "gemini-3.6-flash", "gemini-3")` vào `MODELS` trong `db/rules.py`
- [x] 2.3 Thêm mẫu `("3.6 flash", "gemini-3.6-flash")` vào `MODEL_PATTERNS`, đặt trước
      `"3 pro"`/`"3 flash"` theo đúng quy tắc thứ tự có sẵn
- [x] 2.4 Chạy `db/gen_catalog.py`, diff `db/02_catalog.sql` trước/sau — đúng 1 dòng mới
      (`(11, 'gemini-3.6-flash', 'gemini-3', 'Google')`), không dòng nào khác đổi
- [x] 2.5 **Đổi cách làm so với design.md ban đầu.** Không có "đường đã dùng để dựng 10
      dòng hiện có" áp được lên DB sống — hai đường duy nhất là `alembic upgrade head`
      (không đụng catalog) và `rebuild_db.py` (`DROP SCHEMA public CASCADE` trước, chính
      docstring cấm dùng lên "database thật"). Đã chạy `INSERT` đúng 1 dòng, copy nguyên
      văn từ `02_catalog.sql` vừa sinh, thay vì gõ tay hay chạy nguyên file
- [x] 2.6 Xác minh trên database thật: `dim_model` có 11 dòng, `model_id=11` là
      `gemini-3.6-flash`, `GROUP BY model_id HAVING count(*) > 1` → 0 dòng trùng
- [x] 2.7 Không có test riêng cho `db/rules.py`/`guess_model()`. Chạy
      `python -m unittest discover -s tests -p 'test_*.py'` → 11/11 OK, không vỡ gì khác

## 3. Quyết định số phận `docker-packaging` plan

- [x] 3.1 Đọc toàn bộ `docs/superpowers/plans/2026-08-18-docker-packaging.md` (899 dòng)
- [x] 3.2 **Sửa lại giả định sai trong `design.md`.** Plan này KHÔNG liên quan LiteLLM
      Gateway — "gateway" ở đây là Nginx đứng trước chính `token-ledger-dashboard`, mục
      tiêu là đóng gói + deploy dashboard ra `dashboard.rangdong.com.vn:45501`. Kế hoạch
      nén không hề "thay thế" kiến trúc này, chỉ trùng chữ "gateway". Đo được: 0/40
      checkbox đã tick, 0/9 file mô tả trong "File Structure" tồn tại trong repo, 2 tham
      chiếu hỏng (`copy_to_postgres.py` xoá 24/08, `var/token_ledger.sqlite` xoá 17/08)
- [ ] 3.3 **HOÃN — chờ hỏi.** Đây là quyết định phạm vi sản phẩm (còn muốn deploy dashboard
      ra domain thật hay không), không suy ra được từ code. Anh Tuấn chọn "để lại, đi hỏi"
      ngày 29/08/2026. Chưa sửa file `docker-packaging.md`, chưa đánh dấu lỗi thời hay còn
      sống — quay lại task này sau khi có câu trả lời
- [ ] 3.4 (chờ 3.3)
- [ ] 3.5 (chờ 3.3)

## 4. Nghiệm thu

- [x] 4.1 **Sửa lại tiêu chí ban đầu.** "0 kết quả" là sai mục tiêu — nhật ký dated phải
      giữ nguyên để trung thực với lịch sử (xem 1.1). Tiêu chí đúng: vẫn 6 kết quả như lúc
      1.1, không phát sinh thêm, và không có script nào phụ thuộc đường dẫn cũ. Chạy lại
      `grep -r "2026-26-08"` → đúng 6 kết quả cũ, không đổi
- [x] 4.2 `node --test tests/*.test.js` → 18/18 xanh (cộng 11/11 unittest ở 2.7 — đúng bộ
      nghiệm thu 18+11 dự án đang dùng)
- [x] 4.3 Không tự tạo file nhật ký ngày mới — đó là nếp ghi chép riêng của anh Tuấn. Tóm
      tắt 2/3 việc đã đóng (model catalog, đổi tên backup) đưa thẳng vào cuối phiên
      `/opsx:apply` này; việc còn lại (docker-packaging plan) đang hoãn chờ hỏi, chưa đối
      chiếu vào mục 8 `ke-hoach-nen-thang-9-2026.md` được vì chưa có kết luận
