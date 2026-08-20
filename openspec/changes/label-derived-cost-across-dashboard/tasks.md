# Tasks

## 1. Ghi lại mốc trước khi sửa

- [ ] 1.1 Chạy `tools/do_tien_suy_ra.py`, lưu bộ số mốc: 28,2% cả kỳ · 8 dòng theo agent ·
      22/228 ngày trên 50%
- [ ] 1.2 Ghi lại tổng tiền từng tab TRƯỚC khi sửa — change này MUST NOT đổi con số nào,
      chỉ thêm nhãn. Lệch một xu là có lỗi

## 2. `aggregate()` — điểm nghẽn duy nhất

- [ ] 2.1 `aggregate()` (`app.js:939`) trả thêm `costEst` (phần suy ra) bên cạnh `cost`
- [ ] 2.2 Dùng `costOrNull()` đã có từ commit `0e11c5a` để biết dòng nào suy ra, không
      viết lại phép kiểm
- [ ] 2.3 Trả thêm `costInvoicedRows` / `costDerivedRows` để phân biệt được **agent chưa
      nối billing** (0 dòng có hoá đơn) với **hoá đơn về trễ** (có cả hai loại)
- [ ] 2.4 Xác nhận 7 chỗ gọi `aggregate()` đều nhận được trường mới mà không đổi con số cũ

## 3. Một hàm dựng ô tiền, dùng chung

- [ ] 3.1 Gom logic hiển thị vào một chỗ, theo đúng khuôn `deptCostCell()` đã viết ở
      commit `6d6eef8` — đừng để hai cách gắn nhãn cho cùng một khái niệm
- [ ] 3.2 Ba trạng thái: toàn bộ hoá đơn · có phần suy ra (nêu %) · toàn bộ suy ra
- [ ] 3.3 Ngưỡng "không đáng kể" khai thành hằng số có tên và có ghi chú vì sao chọn số đó
- [ ] 3.4 `moneyCell()` (`app.js:520`) chuyển sang dùng hàm mới

## 4. Từng tab

- [ ] 4.1 **Tổng quan** — thẻ tổng chi phí nêu tỷ lệ suy ra CỦA KỲ ĐANG CHỌN.
      Cạm bẫy đã mắc 17/08: tính tỷ lệ trên 224 ngày trong khi thẻ tiền chỉ hiện kỳ được
      chọn, báo 28% cạnh một con số mà tỷ lệ thật là 32%
- [ ] 4.2 **Agents** — bảng theo agent. Trợ lý ảo Ralli phải nói rõ *"chưa nối billing"*,
      không nói *"hoá đơn chưa về"*
- [ ] 4.3 **Provider & Model**
- [ ] 4.4 **Chi phí**
- [ ] 4.5 **Hiệu năng** — kiểm xem có ô tiền nào không; không có thì ghi rõ là đã kiểm

## 5. Xuất CSV

- [ ] 5.1 Thêm cột phân biệt tiền hoá đơn với tiền suy ra
- [ ] 5.2 Kiểm mở bằng Excel tiếng Việt, cột không vỡ

## 6. Nghiệm thu

- [ ] 6.1 **Tổng tiền từng tab KHÔNG đổi** so với mốc ở 1.2
- [ ] 6.2 Trợ lý ảo Ralli hiện 100% suy ra ở mọi chỗ nó xuất hiện
- [ ] 6.3 Chatbot Contact Center (2,8% suy ra) KHÔNG bị gắn dấu ở mức gây nhiễu
- [ ] 6.4 Chọn kỳ chỉ có ngày 17/08 → mọi ô tiền phải nói 100% suy ra
- [ ] 6.5 Chọn kỳ 01/01–13/08 → tỷ lệ phải thấp hơn hẳn kỳ có ngày mới nhất
- [ ] 6.6 `node --check`, hai bộ test JS, `audit_db.py`, `check_api.py` đều xanh
- [ ] 6.7 Kiểm trong Chrome bằng `Ctrl+Shift+R`, xác nhận đang xem bản mới bằng
      `fetch("js/app.js?probe="+Date.now())` — 20/08 đã mất một vòng vì bộ đệm

## 7. Việc KHÔNG thuộc change này

- Đụng `backend/`, `db/`, `scripts/`. Dữ liệu đã đủ: `cost_usd` NULL ở đúng những dòng
  chưa có hoá đơn
- Đổi cách TÍNH tiền. Con số giữ nguyên, chỉ thêm phần nói nó từ đâu ra
- Nối Google Billing cho `tla-ralli` — đó là việc hạ tầng, change này chỉ làm nó **nhìn
  thấy được**
