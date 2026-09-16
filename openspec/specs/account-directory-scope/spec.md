# account-directory-scope Specification

## Purpose

Giữ cho `/api/accounts` chỉ trả về tài khoản là **con người**, và giữ điều đó bằng một
cơ chế có tên chứ không bằng một dòng SQL không ai chú thích.

Bảng `account` có bốn loại `kind`: `real` (937), `service_account` (6), `unattributed`
(8), `whole_agent` (2). Chỉ loại đầu là người. Ba loại còn lại là chỗ ngồi kế toán —
chúng cần thiết để token và tiền không hụt, nhưng đếm chúng như nhân viên thì mọi chỉ
tiêu theo người đều sai.

Đo A/B ngày 22/08/2026 cho thấy bộ lọc `kind='real'` trong `store.accounts()` là tấm
lưới **duy nhất**: nới nó ra thì sáu tài khoản dịch vụ đi thẳng lên màn hình và không
tầng nào phía sau loại chúng. Năng lực này vì thế gồm cả phép kiểm khoá tấm lưới đó lại,
chứ không chỉ là bản thân điều kiện lọc.

## Requirements
### Requirement: Danh bạ chỉ trả về tài khoản là con người

`/api/accounts` SHALL chỉ trả về dòng có `account.kind = 'real'`. MUST NOT trả về
`service_account`, `whole_agent` hay `unattributed`.

Lý do: đây là endpoint duy nhất nuôi `USER_ACCOUNTS`, và mọi dòng lọt vào đó được đếm
như một con người.

**Đo được (22/08/2026):** bảng danh bạ có thêm 6 dòng, và mẫu số thẻ "User hoạt động"
937 → 943.

**Suy luận, chưa đo:** hàng của sáu đơn vị `auto:` trong bảng phòng ban sẽ đổi từ *"chưa
có user"* sang *"1 tài khoản"*. Phòng ban thật không đổi — `DEPT_PROVISIONED` đo ra
101 đơn vị / 3.693 ở cả hai vế.

Bốn loại `kind` hôm nay: `real` 937 · `service_account` 6 · `unattributed` 8 ·
`whole_agent` 2.

#### Scenario: Tài khoản dịch vụ không được lọt vào danh bạ

- **WHEN** `account` có dòng `kind = 'service_account'` (`svc.contact-center`,
  `svc.sale-agent`, `svc.invoice`, `svc.tools-quizzer`, `svc.dms-feedback`,
  `svc.crm-feedback`)
- **THEN** `/api/accounts` SHALL trả về **937 dòng**, không phải 943
- **AND** MUST NOT có dòng nào mang `full_name` bắt đầu bằng `"Cả "` — đo 22/08: tiền tố
  này chỉ xuất hiện ở `service_account` (6) và `whole_agent` (2), **0 người thật**
- **AND** MUST NOT có dòng nào mang `username` bắt đầu bằng `svc.` — đo 22/08: **0 người
  thật**

#### Scenario: Bộ lọc bị gỡ

- **WHEN** điều kiện `kind` ở `accounts()` bị nới ra, dù vô tình hay có chủ ý
- **THEN** `backend/check_api.py` SHALL báo hỏng và thoát khác 0
- **AND** thông báo SHALL nêu đích danh dòng nào lọt (`username` + `kind`), MUST NOT chỉ
  nói có chênh lệch

> **Kiểm ngược 22/08/2026 bác bỏ một khẳng định của bản đầu.** Bản đầu viết *"hôm nay
> không có gì kêu lên"*. Chạy thật thì phép kiểm cũ `So tai khoan khop` **có** báo hỏng —
> nó so số dòng API với `SELECT COUNT(*) FROM account WHERE kind='real'`. Nhưng nó yếu ở
> hai chỗ, và đó mới là lý do cần phép kiểm mới:
>
> | | |
> |---|---|
> | Phần chi tiết khi hỏng | **chuỗi rỗng** — in ra một dòng trắng, không nói lệch bao nhiêu hay vì sao |
> | Cách khẳng định | **soi gương bản cài đặt** — mẫu số dùng lại đúng `kind='real'`. Sửa cả hai chỗ cho khớp nhau thì nó xanh trở lại |
>
> Phép kiểm mới khẳng định một **tính chất** (*"không dòng nào có `kind` khác `real`"*)
> chứ không so hai con số, và nó gọi tên dòng lọt.

### Requirement: Cái chặn phải nằm ở máy chủ, không dựa vào tầng hiển thị

Điều kiện lọc SHALL nằm ở `backend/store.py`. MUST NOT dựa vào việc `web/js/` sẽ lọc
giúp, và MUST NOT dựa vào việc đơn vị kỹ thuật không có trong cây.

Lý do: đo A/B ngày 22/08/2026 cho thấy hai thứ trông như lưới đỡ **không đỡ**. `api.js`
dòng 216 (`if (u.is_technical) return;`) chặn *đơn vị*, không chặn *tài khoản*. Và
`.filter(u => u.unitId && ...)` ở `buildAccountCatalogueFromDb` **không loại được dòng
nào** — đo ra đúng 0 ở cả hai vế — vì `unitOf()` luôn trả ra một đơn vị `auto:` (tạo mới
nếu chưa có, trả bản cũ nếu đã có), nên `u.unitId` không bao giờ rỗng.

Đo ra rằng **cây đơn vị không đổi**: đơn vị ở cấp gốc 11 → 11, trong đó tự tạo 7 → 7,
`DEPT_PROVISIONED` 101 đơn vị / 3.693 → không đổi. Sáu đơn vị *"Đơn vị sử dụng &lt;tên
agent&gt;"* **đã có sẵn từ trước**, do các dòng usage chế ra. Hại thật vì thế gói gọn ở
hai chỗ: sáu dòng *"Cả &lt;tên agent&gt;"* nằm trong bảng danh bạ, và mẫu số thẻ "User
hoạt động" 937 → 943.

#### Scenario: Frontend đổi cách lọc

- **WHEN** `buildAccountCatalogueFromDb` hay `unitOf()` được sửa
- **THEN** danh bạ SHALL vẫn không chứa tài khoản dịch vụ
- **AND** không phép kiểm nào của change này SHALL phụ thuộc vào mã JavaScript

#### Scenario: Tài khoản mang đơn vị không có trong cây

- **WHEN** một dòng danh bạ mang `unit_id` không tra ra đơn vị nào trong `ORG_UNITS`
- **THEN** hành vi tự tạo đơn vị của `unitOf()` SHALL được giữ nguyên — nó phục vụ tài
  khoản người thật có phòng ban lạ
- **AND** MUST NOT được dùng làm lý do để nới bộ lọc ở máy chủ

### Requirement: Công cụ chạy dashboard phải hỏng to tiếng khi không lấy được dữ liệu

`tools/diagnostics/chay_dashboard_trong_node.js` SHALL thoát khác 0 khi `napTuBackend()` không nạp
được dữ liệu.

Lý do, đo ngày 22/08/2026 bằng chính file chưa sửa: `localStorage` giả rỗng nên `api.js`
dừng ở ô nhập khoá, nhật ký uvicorn ghi nhận **0 lần gọi `/api/`**, mà harness **thoát 0**
và in "nạp OK" hai lần. Nó *có* để lại dấu vết — `conn-text` bằng *"Chưa nhập khoá"*,
`freshness-text` và `status-period` rỗng — nhưng dấu vết nằm trong bảng đổ DOM ở cuối và
không có gì đọc nó. Đây đúng bẫy đã bắt được ở bốn kịch bản test JS hôm 21/08, chỉ khác
là `tools/` không nằm trong bộ kiểm nên không ai thấy.

Ghi rõ **không** cấm dòng "nạp OK": nó nói về việc *nạp tệp JavaScript*, và việc đó thật
sự thành công. Cấm nhầm nó là chữa triệu chứng sai.

#### Scenario: Chạy harness khi chưa có khoá

- **WHEN** `localStorage` giả không có khoá cho địa chỉ backend đang dùng
- **THEN** harness SHALL nói rõ là chưa có khoá và thoát khác 0
- **AND** MUST NOT kết thúc với mã thoát 0

#### Scenario: Chạy harness khi có khoá đúng

- **WHEN** harness được gieo khoá khớp với `DASHBOARD_KEY` của máy chủ
- **THEN** nó SHALL nạp được và in `REAL_ACCOUNTS` = **937**, `USER_ACCOUNTS` = **937**

