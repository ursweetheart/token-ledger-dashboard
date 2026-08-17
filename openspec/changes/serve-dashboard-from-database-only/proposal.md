# Dashboard chỉ hiển thị dữ liệu từ database

## Why

Dashboard hiện có **hai** đáp án cho cùng một câu hỏi, và người xem không phân biệt được
đang xem đáp án nào. Backend chạy thì số đến từ database; backend tắt, lỗi một endpoint,
hoặc database thiếu ngày thì `web/js/api.js:250` bắt lỗi, `return null`, và dashboard
lặng lẽ hiện dữ liệu nhúng cứng trong `app.js`. Dấu hiệu duy nhất là một dòng
`console.warn` — phải mở DevTools mới thấy.

Đã đo mức lệch giữa hai đáp án đó:

| | SEED nhúng cứng | Database | Lệch |
|---|---|---|---|
| Tổng in+out | 743.142.318 | 627.287.566 | **-15,6%** |
| Trợ Lý Ảo Hợp Đồng | 8.392.364 | 66.750.712 | **+695,4%** |
| Chatbot Contact Center | 321.701.509 | 175.069.716 | **-45,6%** |
| Multi modal AI Invoice | 86.555.467 | 39.859.039 | **-53,9%** |
| Số ngày khớp chính xác | | | **25 / 224** |

Khối nhúng cứng là ảnh chụp từ trước đợt làm lại backend (15/08), nên nó không chỉ cũ mà
còn **không tự biết mình cũ**: mỗi lần đường ống được sửa, khoảng cách rộng thêm và không
ai được báo.

Chuyện này vi phạm đúng nguyên tắc đã viết trong `backend/main.py:17-23` — *"nếu frontend
không hiện được phần này thì bỏ đi còn hơn, vì khi đó người xem sẽ tin vào con số nhiều
hơn mức nó đáng được."* Ở đây biến thể của nó là: **một bảng số cũ trông y hệt một bảng số
mới.**

Đã xác minh bỏ đi không mất dữ liệu: database phủ **224/224 ngày** và **8/8 agent** của
khối nhúng cứng, không ngày nào và không agent nào chỉ tồn tại ở phía nhúng cứng.

## Đã soát trên trang thật (17/08/2026) — sáu chỗ nói sai về dữ liệu

Mở dashboard với backend nối Postgres, soát cả 6 tab. Mọi tab đều vẽ đủ và số khớp
database, nhưng phần **nói về** dữ liệu thì sai ở sáu chỗ. Bốn chỗ đầu là chữ **gán cứng
trong `web/index.html`**, không do dữ liệu nào điều khiển:

| # | Nơi | Hiện gì | Vấn đề |
|---|---|---|---|
| 1 | `index.html:276-277` | `"Gateway hoạt động"` · `"Cập nhật realtime · lần cuối 2 phút trước"` | **Nặng nhất.** Chữ tĩnh. Không có gateway nào tồn tại, và `"2 phút trước"` là hằng số — dữ liệu cũ bao lâu nó cũng nói vậy. Đây là một khẳng định về **độ mới** mà không gì kiểm chứng |
| 2 | `index.html:454` | `"= Σ token vào + token ra"` | Số **đúng** (45.685.588 = `ti+to+cached`) nhưng nhãn **thiếu `cached`**. Ai đọc nhãn rồi tự tính lại sẽ ra 35,6 triệu — hụt 22% |
| 3 | `index.html:260` | `"Nhập liệu thủ công theo ngày… Dữ liệu lưu trong trình duyệt"` | Mô tả luồng nhập tay + Excel đã không còn dùng |
| 4 | Thẻ TỔNG CHI PHÍ | `1 triệu ₫ · 39,72 US$`, nhãn `"Σ (token × đơn giá) theo bảng giá"`, nhãn nguồn `BigQuery Billing` | **Là số PHA TRỘN, và không chỗ nào nói ra.** Đo được: hoá đơn 26,94 US$ (66/93 dòng) + ước tính 12,78 US$ (27/93 dòng) = **32,2% số tiền trên màn hình là suy ra từ bảng giá**. Cả kỳ 01/01→13/08: 219/1.161 dòng = 18,9% phải ước tính |

Hai lỗi còn lại là lỗi tính/định dạng ở frontend, **không** thuộc phạm vi change này nhưng
ghi lại để không mất:

| # | Nơi | Hiện gì | Vấn đề |
|---|---|---|---|
| 5 | Tab Phòng ban & User, hàng `Chưa quy được` | `2/1 · 200%` | Tỷ lệ vượt 100%; nhãn hàng ghi 9 tài khoản mà mẫu số là 1. `audit_db.py` có phép kiểm *"Tỷ lệ áp dụng không vượt 100%"* và nó **đạt** → lỗi gộp ở frontend, không phải lỗi dữ liệu |
| 6 | Cột `Thời gian được cấp` | `04/26T17:59:49.958000/2026` | Dấu thời gian ISO lọt qua bộ định dạng ngày |

Bốn chỗ đầu là lý do capability `visible-data-provenance` tồn tại: dashboard đang **nói**
những điều về dữ liệu mà dữ liệu không hề bảo đảm.

## What Changes

Năm khối dữ liệu nhúng, cộng một vector cũ thứ sáu không phải hardcode mà là cache:

- Xoá `SEED_DAYS` (`web/js/app.js:482`) — 267.787 ký tự, tức **58% toàn bộ `app.js`**.
- Xoá `buildJuneExcelWeeks()` (`web/js/app.js:2314`) — 3.634 ký tự. `defaultState()` đang
  trộn nó **dưới** `SEED_DAYS`, nên nó là nguồn cũ thứ hai, độc lập.
- Xoá `web/js/fallback/ralli-users.js` — 121 KB danh sách user Ralli.
- `basePricing` (`web/js/app.js:454`) chỉ còn lấy từ `ref_price` qua `/api/catalog`.
- `AGENT_MONTHLY_BUDGETS` (`web/js/app.js:15`) chỉ còn lấy từ `ref_budget`. Hiện là hằng
  số gõ tay bị ghi đè ở dòng 5357 *nếu* backend trả về — hai nguồn cho một con số.
- Bump khoá `localStorage` (`web/js/app.js:11`, hiện
  `agent-dash-state-v19-du-lieu-13-08`) và **không** ghi số liệu backend vào đó nữa. Đây
  là vector cũ thứ sáu: `scripts/va_app_js.py` đã phải bump khoá mỗi lần cập nhật vì
  *"otherwise a returning browser keeps serving the old data out of localStorage"*.
- `web/js/api.js` khi không nạp được: **báo lên màn hình**, không `return null` im lặng.
  Đây là phần quan trọng nhất của change — bốn khối trên chỉ là hệ quả.
- Đường ống rút từ 10 xuống 9 bước: bước `[10/10] Va du lieu du phong vao app.js` tồn tại
  **chỉ để** sinh và vá `SEED_DAYS`, nên nó biến mất cùng hai script
  `scripts/sinh_du_lieu_dashboard.py`, `scripts/va_app_js.py`, và ảnh chụp
  `web/js/app.js.bak` (194 KB).
- **BREAKING** Mở `web/index.html` bằng cách bấm đúp sẽ **không còn xem được số liệu**.
  Đây là đánh đổi có chủ đích: khả năng xem offline chính là cơ chế đã che mất mọi lỗi
  backend. README hiện quảng cáo tính năng này nên phải sửa.

## Capabilities

### New Capabilities

- `single-source-dashboard-data`: dashboard SHALL lấy mọi con số từ database qua API, và
  MUST NOT chứa dữ liệu số liệu nào trong mã nguồn frontend — kể cả làm dữ liệu dự phòng.
  Bao gồm cả bảng giá, hạn mức, và danh sách người dùng.
- `visible-data-provenance`: khi không nạp được dữ liệu, dashboard SHALL nói ra **trên
  màn hình** thay vì chỉ ghi console; và SHALL hiện được khoảng ngày cùng thời điểm của
  dữ liệu đang xem, để "số cũ" không trông giống "số mới".

### Modified Capabilities

- `project-layout`: scenario *"Bước vá dữ liệu dự phòng vẫn chạy đúng"* mô tả bước cuối
  đường ống sinh file trung gian rồi vá vào `web/js/app.js`, và yêu cầu không ghi đè
  `app.js.bak`. Bước đó bị xoá hoàn toàn, nên scenario này phải được bỏ chứ không sửa.
  Requirement *"Đường ống sản xuất MUST NOT gọi vào `tests/` hay `tools/`"* KHÔNG đổi.

## Impact

| Nơi | Thay đổi |
|---|---|
| `web/js/app.js` | xoá `SEED_DAYS`, `buildJuneExcelWeeks()`; `basePricing` + `AGENT_MONTHLY_BUDGETS` chỉ từ API; bump khoá `localStorage`; `defaultState()` không còn nguồn nhúng để trộn |
| `web/js/api.js` | `catch` không còn `return null` im lặng; báo trạng thái ra giao diện |
| `web/js/fallback/ralli-users.js` | **xoá** (cả thư mục `fallback/` nếu trống) |
| `web/js/app.js.bak` | **xoá** — ảnh chụp 194 KB của phiên bản trước |
| `scripts/sinh_du_lieu_dashboard.py`, `scripts/va_app_js.py` | **xoá** |
| `scripts/update_dashboard.py` | bỏ bước `[10/10]`, đánh số lại `[n/9]` |
| `README.md`, `docs/reference/toan-trinh-du-lieu.md` | bỏ lời hứa "bấm đúp vẫn xem được"; 10 bước → 9 bước |
| `tests/date-range-filter.test.js` | **không sửa.** Đã kiểm: nó tự bơm state qua `setState()` nên không dựa vào nội dung `SEED_DAYS`, và đã stub `window.RALLI_USERS = []`. Nó nạp trọn `app.js` trong `vm`, nên nó chính là phép kiểm bắt tham chiếu treo sau khi xoá — 6/6 phải còn xanh |

**Thứ tự với change `switch-default-dsn-to-postgres`:** không phụ thuộc lẫn nhau, nhưng
nên làm **sau** change đó. Lý do: sau change này dashboard không còn đường dự phòng, nên
nó chỉ hiện số khi backend nối được database — cần database mặc định đã ổn định trước.

**Rủi ro:** đây là change kiểm bằng **mắt**, không kiểm bằng số. Phải mở dashboard và soát
từng tab, vì một khối dữ liệu bị xoá thiếu sẽ không làm gì ném lỗi — nó chỉ làm một biểu
đồ trống hoặc một con số về 0.
