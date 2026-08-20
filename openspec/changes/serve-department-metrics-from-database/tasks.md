# Tasks

## 1. Không đo được phải hiện khác bằng không — ĐÃ XONG (`0e11c5a`, 20/08/2026)

- [x] 1.1 Thêm `costOrNull()` trả `null` khi không tra được giá; giữ `cost()` trả số để
      mọi phép cộng đang có không đổi hành vi
- [x] 1.2 `deptUnitMetrics()` trả thêm `costKnown`, đếm số tài khoản thật sự cho ra giá trị
- [x] 1.3 Ranh giới: đơn vị **không có lưu lượng** vẫn hiện `0 ₫`; có lưu lượng mà không
      tính được thì hiện `—`
- [x] 1.4 Ô `—` mang tooltip nói rõ lý do. LƯU Ý: câu hiện tại ("tiền chỉ có ở mức
      project") sẽ THÀNH SAI sau nhóm 8 — task 8.5 phải sửa lại nó
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

## 3–7. Cây tổ chức — ⏸️ HOÃN (quyết định 20/08/2026)

Đo trước khi apply thấy `dim_unit` là **hai cây** (Trợ Lý Ảo Hợp Đồng 20 đơn vị / 4 gốc,
Trợ lý ảo Ralli 102 đơn vị / 1 gốc) với **8 tên trùng nhau**, còn `ORG_UNITS` là một cây
đã gộp bằng tay. `unit_id` hoà giải được viết tắt nhưng **không gộp được hai cây** — đó là
câu hỏi nghiệp vụ, cần người quyết. Xem `design.md` §2.3.

Nhóm 8 độc lập hoàn toàn với phần này nên vẫn làm được ngay.

## 3. Đối chiếu 108 ↔ 130 — chưa làm

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

- [ ] 6.1 Xoá `ORG_UNITS` (108 đơn vị, `app.js:67-177`)
- [ ] 6.2 Xoá `UNIT_ALIASES` (33 mục) và nhánh ghép theo tên
- [ ] 6.3 `rebuildRalliProvisioned()` (`app.js:631`) ghép bằng `unit_id` thay vì
      `a.unit_name`. **KHÔNG xoá hàm này** — soát lại 20/08 thấy nó đã dựng từ
      `REAL_ACCOUNTS` (tức `/api/accounts`) chứ không phải từ dữ liệu gõ cứng; chỗ hỏng
      duy nhất là nó tra đơn vị qua `unitOf(a.unit_name)`, tức khớp bằng chuỗi
- [ ] 6.4 Quét lại `web/js/` xác nhận không còn định danh nào mang dữ liệu gán cứng
- [ ] 6.5 Đổi tên `rebuildRalliProvisioned` — nó đếm **mọi** tài khoản chứ không riêng
      Trợ lý ảo Ralli, tên hiện tại nói sai phạm vi

## 7. Nghiệm thu

- [ ] 7.1 Bốn mốc ở 3.5 khớp trước và sau; mọi chênh lệch truy được về một dòng trong bảng
      đối chiếu
- [ ] 7.2 Quét toàn bảng: không ô tỷ lệ áp dụng nào vượt 100%
- [ ] 7.3 Quét cột tiền: không hàng nào vừa có token > 0 vừa hiện `0 ₫`; hàng có số phải
      mang nhãn *"suy từ bảng giá"*; hàng `—` phải nói được lý do
- [ ] 7.4 Kiểm cả hai tab **Phòng ban & User** và **Agents** — chúng dùng chung cây
- [ ] 7.5 `node --check`, hai bộ test JS, `audit_db.py`, `check_api.py` đều xanh
- [ ] 7.6 Kiểm trong Chrome bằng `Ctrl+Shift+R`. Xác nhận đang xem bản mới:
      `fetch("js/app.js?probe="+Date.now())` rồi so nội dung file với hàm có trong trang —
      ngày 20/08 đã mất một vòng vì bộ đệm giữ bản cũ và bảng hiện y hệt trước khi sửa

## 8. Tiền theo phòng ban — suy từ bảng giá — ĐÃ XONG (20/08/2026)

Đưa vào phạm vi sau khi đo bác bỏ lý do loại nó ra. Xem `design.md` §5.

- [x] 8.1 `api.js` giữ `model_id` trên từng dòng `byAccount` — **đã sẵn đúng**:
      `state.byAccount` chuyển thẳng `r[6].rows`, không bỏ trường nào
- [x] 8.2 Dựng bảng tra `model_id` → tên model từ `/api/catalog`, vì `state.pricing` khoá
      theo tên còn API trả id
- [x] 8.3 Tính tiền ở **mức dòng** rồi mới cộng lên tài khoản. MUST NOT nhân token đã cộng
      gộp của tài khoản với một đơn giá — `flash-lite` $0,10 so với `pro` $1,25 chênh 12,5 lần
- [x] 8.4 Dòng có `model_id` không tra được giá thì đơn vị chứa nó rơi về `—`, không tính 0
- [x] 8.5 Ô tiền mang dấu hiệu nói rõ **suy từ bảng giá**, không phải hoá đơn.
      ĐỒNG THỜI sửa tooltip của ô `—` đặt ở task 1.4 — câu *"tiền chỉ có ở mức
      project"* thành SAI khi tiền đã tính được; `—` lúc đó chỉ còn nghĩa
      *"model này không tra được đơn giá"*
- [x] 8.6 Thêm chỗ nói HAI phần chênh: hoá đơn không quy được ($47,5109 = 75,8%) và phần
      suy ra NGOÀI hoá đơn của Trợ lý ảo Ralli ($1,2988 — agent chưa nối Google Billing)
- [x] 8.7 Đối chiếu: tổng tiền suy ra của các phòng ban phải khớp con số đã đo tay
      (414.090 ₫ = $16,43 cho kỳ 19/07–17/08), lệch thì tìm ra dòng nào trước khi đi tiếp
- [x] 8.8 Đối chiếu lại phép suy trên nguồn billing: 965 dòng cho lệch tổng −0,1% và lệch
      trung vị 0,0% — `tools/kiem_so_artifact.py` giữ phép kiểm này
- [x] 8.9 **Phát hiện khi apply:** tiền của hàng đơn vị kỹ thuật đã TRỘN SẴN hoá đơn với
      suy ra từ trước, mà không mang dấu gì — Chatbot Contact Center $15,30 hoá đơn +
      $1,58 suy ra, Trợ lý ảo Ralli $0,00 + $2,51 (toàn bộ suy ra). Dấu `≈` vì vậy phải
      áp cho CẢ hai nhánh, và tooltip nói rõ **bao nhiêu phần trăm** là suy ra: 2% với
      Sale Agent, 9% Chatbot Contact Center, 31% Phân Loại Phản Hồi Tiếp Thị, 100% TTDL&ĐHS

## 9. Việc KHÔNG thuộc change này

- Mọi thay đổi trong `backend/`, `db/`, `scripts/`. Cả ba lỗi đều ở frontend, và phép suy
  tiền cũng làm được hoàn toàn ở frontend: `/api/usage-by-account` đã có `model_id`,
  `/api/catalog` đã có đơn giá
