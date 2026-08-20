# Tasks

## 1. Không đo được phải hiện khác bằng không — ĐÃ XONG (`0e11c5a`, 20/08/2026)

- [x] 1.1 Thêm `costOrNull()` trả `null` khi không tra được giá; giữ `cost()` trả số để
      mọi phép cộng đang có không đổi hành vi
- [x] 1.2 `deptUnitMetrics()` trả thêm `costKnown`, đếm số tài khoản thật sự cho ra giá trị
- [x] 1.3 Ranh giới: đơn vị **không có lưu lượng** vẫn hiện `0 ₫`; có lưu lượng mà không
      tính được thì hiện `—`
- [x] 1.4 Ô `—` mang tooltip nói rõ tiền chỉ có ở mức project nên không chia được theo người
- [x] 1.5 Kiểm trên Chrome, backend nối PostgreSQL: `Nghiên cứu thị trường` (49 req),
      `TTDL&ĐHS` (46 req), `TT&TMĐT` (19 req) đổi `0 ₫` → `—`; `Kế hoạch`,
      `Trung tâm R&D` (0 req) giữ `0 ₫`

## 2. Tỷ lệ áp dụng không vượt 100% — ĐÃ XONG (`0e11c5a`, 20/08/2026)

- [x] 2.1 Tử số lọc cùng điều kiện với mẫu số: `inDirectory && !shared`
- [x] 2.2 Cấp "Trực thuộc" dùng cùng tập cho mẫu số, không dùng `row.accounts.length` thô
- [x] 2.3 `adoptionCell()` nhận thêm số tài khoản ngoài danh bạ, nêu trong tooltip thay vì
      cộng vào tử số
- [x] 2.4 Kiểm trên Chrome: `Chưa quy được` đổi `3/1 · 300%` → `0/1 · 0%`, tooltip nói
      *"thêm 3 tài khoản có request nhưng không có trong danh bạ"*
- [x] 2.5 `node --check` sạch; `date-range-filter` 6/6 và `load-failure-states` 7/7 xanh;
      `audit_db.py` 32 phép / 0 hỏng; `check_api.py` 16/16

## 3. Đối chiếu 108 ↔ 130 — LÀM TRƯỚC, chưa được xoá gì

- [ ] 3.1 Viết công cụ một lần trong `tools/` sinh bảng đối chiếu `ORG_UNITS` ↔ `dim_unit`
- [ ] 3.2 Tách riêng ba kiểu lệch: chỉ có trong database · chỉ có trong `ORG_UNITS` ·
      có ở cả hai nhưng **khác cha hoặc khác cấp**
- [ ] 3.3 Với mỗi mục thuộc kiểu thứ ba, ghi rõ số token đang bị cộng vào nhánh nào
- [ ] 3.4 Soát 33 mục `UNIT_ALIASES`: alias nào là viết tắt thật, alias nào đang **che một
      lệch** giữa hai cây
- [ ] 3.5 Ghi lại bốn mốc nghiệm thu TRƯỚC khi thay: tổng token · tổng tiền · tổng từng
      phòng ban cấp 1 · số hàng đơn vị và số hàng tài khoản

## 4. `api.js` chuyển cây tổ chức ra ngoài

- [ ] 4.1 Thêm `units` vào state mà `api.js` trả về, giữ nguyên `unit_id`, `agent_id`,
      `name`, `parent_id`, `level`, `path`, `is_technical`
- [ ] 4.2 Giữ nguyên hợp đồng "chỉ bơm dữ liệu, không đụng giao diện" — `api.js` MUST NOT vẽ gì
- [ ] 4.3 Mỗi dòng usage mang thêm `unitId` bên cạnh `d` hiện có, để bước 5 chuyển dần
      chứ không đổi một phát
- [ ] 4.4 Giữ `primaryUnit()` chạy song song cho tới khi bước 5 xong

## 5. `app.js` dựng cây từ database

- [ ] 5.1 Dựng `unitIndex` / `unitChildIndex` từ `units` của API thay vì từ `ORG_UNITS`
- [ ] 5.2 `unitOf()` ghép bằng `unit_id`; giữ nhánh ghép theo tên **tạm thời** và đếm số
      lần nó được dùng — con số đó phải về 0 trước khi xoá
- [ ] 5.3 Đơn vị không ghép được phải có dấu hiệu nhìn thấy, không lặng lẽ tự sinh
- [ ] 5.4 Hàng đơn vị kỹ thuật lấy tỷ lệ áp dụng từ `/api/adoption` theo `agent_id`
- [ ] 5.5 Phòng ban thật vẫn tự tính, nhưng theo đúng quy tắc backend: loại `is_shared`
      khỏi cả tử lẫn mẫu
- [ ] 5.6 Xác nhận `Đơn vị sử dụng Sale Agent` hiện `1/1` thay vì `—`, và 5 đơn vị kỹ
      thuật còn lại hiện đúng `1/1` hoặc `0/1` tuỳ có hoạt động trong kỳ

## 6. Xoá phần gõ cứng — bước cuối, chỉ khi 3–5 đã sạch

- [ ] 6.1 Xoá `ORG_UNITS` (108 đơn vị, `app.js:67-176`)
- [ ] 6.2 Xoá `UNIT_ALIASES` (33 mục) và nhánh ghép theo tên
- [ ] 6.3 Xoá `rebuildRalliProvisioned()` nếu `DEPT_PROVISIONED` đã dựng được từ
      `/api/accounts` và `/api/adoption`
- [ ] 6.4 Quét lại `web/js/` xác nhận không còn định danh nào mang dữ liệu gán cứng

## 7. Nghiệm thu

- [ ] 7.1 Bốn mốc ở 3.5 khớp trước và sau; mọi chênh lệch truy được về một dòng trong bảng
      đối chiếu
- [ ] 7.2 Quét toàn bảng: không ô tỷ lệ áp dụng nào vượt 100%
- [ ] 7.3 Quét toàn bảng: không hàng nào vừa có request > 0 vừa hiện `0 ₫`
- [ ] 7.4 Kiểm cả hai tab **Phòng ban & User** và **Agents** — chúng dùng chung cây
- [ ] 7.5 `node --check`, hai bộ test JS, `audit_db.py`, `check_api.py` đều xanh
- [ ] 7.6 Kiểm trong Chrome bằng `Ctrl+Shift+R`. Xác nhận đang xem bản mới:
      `fetch("js/app.js?probe="+Date.now())` rồi so nội dung file với hàm có trong trang —
      ngày 20/08 đã mất một vòng vì bộ đệm giữ bản cũ và bảng hiện y hệt trước khi sửa

## 8. Việc KHÔNG thuộc change này

- Ước tính tiền theo phòng ban từ `ref_price` — làm được nhưng là **thêm một con số ước
  tính mới**, phải có nhãn riêng và là quyết định riêng
- Mọi thay đổi trong `backend/`, `db/`, `scripts/` — cả ba lỗi đều ở frontend
