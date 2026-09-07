# Tasks

## 1. Ghi lại mốc trước khi sửa

- [x] 1.1 Chạy `tools/do_tien_suy_ra.py`, lưu bộ số mốc: 28,2% cả kỳ · 8 dòng theo agent ·
      22/228 ngày trên 50%
- [x] 1.2 Ghi lại tổng tiền từng tab TRƯỚC khi sửa — change này MUST NOT đổi con số nào,
      chỉ thêm nhãn. Lệch một xu là có lỗi

## 2. `aggregate()` — điểm nghẽn duy nhất

- [x] 2.1 `aggregate()` (`app.js:939`) trả thêm `costEst` (phần suy ra) bên cạnh `cost`
- [x] 2.2 Dùng `costOrNull()` đã có từ commit `0e11c5a` để biết dòng nào suy ra, không
      viết lại phép kiểm
- [x] 2.3 Tách `costEstNoBilling` / `costEstLate`. **Cách đầu tiên SAI**: phân biệt bằng
      `costRowsInv===0` gộp nhầm *"agent này không bao giờ có hoá đơn"* với *"kỳ này chưa
      có hoá đơn nào"* — chọn riêng ngày 17/08 là cả 7 agent đã nối billing đều bị dán
      nhãn "chưa nối". Dấu hiệu đúng là `dim_agent.has_google_source`, api.js phơi thành
      `noBillingAgents`
- [x] 2.4 Xác nhận 7 chỗ gọi `aggregate()` đều nhận được trường mới mà không đổi con số cũ

## 3. Một hàm dựng ô tiền, dùng chung

- [x] 3.1 Gom logic hiển thị vào một chỗ, theo đúng khuôn `deptCostCell()` đã viết ở
      commit `6d6eef8` — đừng để hai cách gắn nhãn cho cùng một khái niệm
- [x] 3.2 Ba trạng thái: toàn bộ hoá đơn · có phần suy ra (nêu %) · toàn bộ suy ra
- [x] 3.3 Ngưỡng "không đáng kể" khai thành hằng số có tên và có ghi chú vì sao chọn số đó
- [x] 3.4 `moneyCell()` (`app.js:520`) chuyển sang dùng hàm mới

## 4. Từng tab

- [x] 4.1 **Tổng quan** — thẻ tổng chi phí nêu tỷ lệ suy ra CỦA KỲ ĐANG CHỌN.
      Cạm bẫy đã mắc 17/08: tính tỷ lệ trên 224 ngày trong khi thẻ tiền chỉ hiện kỳ được
      chọn, báo 28% cạnh một con số mà tỷ lệ thật là 32%
- [x] 4.2 **Agents** — bảng theo agent. Trợ lý ảo Ralli phải nói rõ *"chưa nối billing"*,
      không nói *"hoá đơn chưa về"*
- [x] 4.3 **Provider & Model**
- [x] 4.4 **Chi phí**
- [x] 4.5 **Hiệu năng** — kiểm xem có ô tiền nào không; không có thì ghi rõ là đã kiểm

## 5. Xuất CSV

- [x] 5.1 Thêm cột phân biệt tiền hoá đơn với tiền suy ra
- [x] 5.2 **06/09/2026 — tìm ra và sửa 2 lỗi thật trước khi kịp "kiểm mở bằng Excel".**
      `exportCSV()` (`app.js:3826`) không có BOM UTF-8 và dùng dấu phẩy làm delimiter cố
      định. Máy dev này là `en-US` (`Get-Culture` → decimal `.`, list separator `,`) nên
      không lộ ra ở đây, nhưng theo đúng cơ chế Windows đã ghi chú trong code: Excel mở
      CSV bằng list separator lấy từ Control Panel Regional Settings của máy đang mở, và
      Excel tiếng Việt/vùng miền Việt Nam mặc định lấy dấu phẩy làm phân cách thập phân
      nên list separator đổi thành dấu chấm phẩy — file này không có dấu `;` nào nên sẽ
      gộp hết vào một cột. Sửa bằng 2 fix chuẩn của Excel, không phụ thuộc vùng miền máy
      mở: dòng chỉ thị `sep=,` ở đầu file (Excel mọi vùng miền đọc dòng này để cố định
      delimiter) + BOM UTF-8 (để không vỡ dấu tiếng Việt). Xác minh bằng `xxd` trên file
      mẫu dựng lại đúng cơ chế: byte đầu `ef bb bf` (BOM đúng), dòng 2 `sep=,`, dòng 3 là
      header đủ dấu, dòng dữ liệu có phẩy trong giá trị (`"486,957"`, `"Chăm sóc khách
      hàng, cấp 1"`) được quote đúng. `node --check web/js/app.js` xanh. Đã gửi file mẫu
      cho anh Tuấn mở thử trên Excel thật để xác nhận bằng mắt — chưa tự tay xác nhận
      được bước này vì môi trường không có Excel tiếng Việt để mở

## 6. Nghiệm thu

- [x] 6.1 **Tổng tiền từng tab KHÔNG đổi** so với mốc ở 1.2
- [x] 6.2 Trợ lý ảo Ralli hiện 100% suy ra ở mọi chỗ nó xuất hiện
- [x] 6.3 Chatbot Contact Center (2,8% suy ra) KHÔNG bị gắn dấu ở mức gây nhiễu
- [x] 6.4 Chọn riêng 17/08 → thẻ tiền `≈ 63 nghìn`, *"100% suy từ bảng giá, trong đó
      8,4 nghìn ₫ của agent chưa nối billing, phần còn lại do hoá đơn về trễ"*
- [x] 6.5 Chọn kỳ 01/01–13/08 → tỷ lệ phải thấp hơn hẳn kỳ có ngày mới nhất
- [x] 6.6 `node --check`, hai bộ test JS, `audit_db.py`, `check_api.py` đều xanh
- [x] 6.7 Kiểm trong Chrome bằng `Ctrl+Shift+R`, xác nhận đang xem bản mới bằng
      `fetch("js/app.js?probe="+Date.now())` — 20/08 đã mất một vòng vì bộ đệm

## 7. Việc KHÔNG thuộc change này

- Đụng `backend/`, `db/`, `scripts/`. Dữ liệu đã đủ: `cost_usd` NULL ở đúng những dòng
  chưa có hoá đơn
- Đổi cách TÍNH tiền. Con số giữ nguyên, chỉ thêm phần nói nó từ đâu ra
- Nối Google Billing cho `tla-ralli` — đó là việc hạ tầng, change này chỉ làm nó **nhìn
  thấy được**

---

> **THAY THẾ MỘT PHẦN — 31/08/2026.** Nguồn thứ tư `gateway` **không** áp dụng yêu cầu
> "phân biệt tiền hoá đơn với tiền suy ra" của `specs/visible-data-provenance`. Chủ dự án
> chốt hiển thị thẳng số tiền của LiteLLM, không gắn dấu `≈`. Lý do và số đo:
> `openspec/changes/load-the-gateway-ledger-into-the-database/tasks.md` mục 9, và đầu file
> `db/migrations/sql/005_gateway_cost_vao_view.sql`.
>
> Ba nguồn cũ (`billing`, `monitoring`, `app`) **giữ nguyên** yêu cầu này.
