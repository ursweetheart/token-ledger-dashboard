## ADDED Requirements

### Requirement: Frontend không chứa số liệu

Mã nguồn frontend SHALL không chứa dữ liệu số liệu nào — kể cả làm dữ liệu dự phòng, dữ
liệu mẫu, hay dữ liệu để xem offline. Mọi con số hiện trên dashboard SHALL đến từ database
qua API.

Quy tắc này bao trùm cả những thứ dễ tưởng là "cấu hình" chứ không phải "số liệu": bảng
giá model, hạn mức ngân sách theo agent, và danh sách người dùng. Cả ba đều đã có bảng
trong database (`ref_price`, `ref_budget`, `dim_user`/`account`), nên giữ bản gõ tay ở
frontend là tạo ra nguồn thứ hai cho cùng một con số.

Lý do: khối nhúng cứng không tự biết mình cũ. Đã đo trước khi bỏ — khối `SEED_DAYS` lệch
**-15,6%** so với database, chỉ **25/224 ngày** khớp chính xác, và một agent lệch
**+695,4%**. Mỗi lần đường ống được sửa, khoảng cách rộng thêm mà không ai được báo.

#### Scenario: Không còn khối dữ liệu nào trong mã frontend

- **WHEN** tìm trong `web/js/` các định danh `SEED_DAYS`, `buildJuneExcelWeeks`,
  `RALLI_USERS`, `basePricing`, `AGENT_MONTHLY_BUDGETS`
- **THEN** không định danh nào còn mang dữ liệu gán cứng
- **AND** không file nào trong `web/js/` vượt quá kích thước của mã điều khiển thuần

#### Scenario: Bảng giá và hạn mức lấy từ database

- **WHEN** dashboard nạp xong từ backend
- **THEN** bảng giá đến từ `ref_price` và hạn mức đến từ `ref_budget` qua `/api/catalog`
- **AND** không con số nào trong hai thứ đó có bản gõ tay trong `web/js/app.js`

#### Scenario: Ba trạng thái hạn mức phân biệt được với nhau

Dữ liệu thật có **ba** nhóm, không phải hai — đã đối chiếu `dim_agent` (8) với `ref_budget`
(7 dòng · 6 có `budget_usd` · 1 có `budget_tokens`):

- **WHEN** một agent có `budget_usd` trong `ref_budget` (6 agent)
- **THEN** dashboard hiện hạn mức USD đó và tính vào tổng ngân sách

- **WHEN** một agent có dòng `ref_budget` nhưng chỉ có `budget_tokens`, không có
  `budget_usd` (`Trợ lý ảo Ralli`, 50.000.000 token)
- **THEN** dashboard hiện đây là hạn mức **theo token**, không phải USD
- **AND** MUST NOT hiện agent này là "chưa đặt hạn mức" — nó đã đặt, chỉ bằng đơn vị khác
- **AND** MUST NOT cộng nó vào tổng ngân sách USD

- **WHEN** một agent không có dòng nào trong `ref_budget` (`Tools Quizzer`)
- **THEN** dashboard hiện agent đó là **chưa đặt hạn mức**
- **AND** MUST NOT hiện 0 — vì 0 nghĩa là "hết hạn mức", khác hẳn "chưa đặt"

### Requirement: Cache của trình duyệt không được trở thành nguồn số liệu cũ

Dashboard MUST NOT ghi số liệu lấy từ backend vào `localStorage`. `localStorage` SHALL chỉ
giữ lựa chọn của người dùng — tab đang mở, giao diện sáng/tối, khoảng ngày đang chọn.

Đây là vector dữ liệu cũ thứ hai, độc lập với dữ liệu nhúng trong mã. Đường ống cũ đã phải
bump số phiên bản trong khoá `localStorage` mỗi lần cập nhật, với lý do ghi thẳng trong
`scripts/va_app_js.py`: *"otherwise a returning browser keeps serving the old data out of
localStorage"*. Khi số liệu không còn được ghi vào đó, việc bump khoá thôi không còn cần
thiết.

#### Scenario: Trình duyệt đã từng mở dashboard không hiện số cũ

- **WHEN** mở dashboard, để nó nạp xong, rồi tải lại trang với backend đã tắt
- **THEN** dashboard MUST NOT hiện số liệu của lần nạp trước
- **AND** nó báo không nối được backend

#### Scenario: Lựa chọn của người dùng vẫn được giữ

- **WHEN** đổi sang tab khác, đổi giao diện sáng/tối, chọn một khoảng ngày, rồi tải lại
  trang
- **THEN** cả ba lựa chọn được giữ nguyên
- **AND** số liệu được nạp lại từ backend, không lấy từ `localStorage`

### Requirement: Đường ống không còn bước vá dữ liệu vào frontend

Đường ống cập nhật SHALL không có bước nào ghi vào `web/js/`. Sinh dữ liệu dự phòng và vá
nó vào `app.js` SHALL bị bỏ hoàn toàn, cùng các script chỉ tồn tại để làm việc đó.

#### Scenario: Đường ống không ghi vào thư mục frontend

- **WHEN** đọc toàn bộ lời gọi lệnh trong `scripts/update_dashboard.py`
- **THEN** không lời gọi nào sinh hoặc sửa file trong `web/`
- **AND** số bước là 9, và nhãn các bước được đánh số lại liên tục

#### Scenario: Script chỉ phục vụ việc vá đã bị xoá

- **WHEN** liệt kê `scripts/`
- **THEN** không còn `sinh_du_lieu_dashboard.py` và `va_app_js.py`
- **AND** không còn ảnh chụp `web/js/app.js.bak`

#### Scenario: Nạp trọn frontend không còn tham chiếu treo

- **WHEN** chạy `node --test tests/date-range-filter.test.js`
- **THEN** cả 6 phép kiểm đạt
- **AND** việc nạp `app.js` trong `vm` không ném lỗi tham chiếu tới định danh đã xoá
