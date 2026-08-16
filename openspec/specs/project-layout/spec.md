# project-layout Specification

## Purpose
TBD - created by archiving change restructure-project-layout. Update Purpose after archive.
## Requirements
### Requirement: Gốc repo chỉ nhận ba loại mục

Thư mục gốc SHALL chỉ chứa: (a) thư mục do công cụ bên ngoài bắt buộc đặt ở gốc, (b)
đúng một thư mục cho mỗi thành phần của hệ thống, (c) file cấu hình cấp dự án. Bất kỳ
file nào không thuộc ba loại này MUST NOT nằm ở gốc.

Quy tắc này tồn tại để câu hỏi "file mới để đâu" có câu trả lời tra được, thay vì mặc
định rơi vào gốc như trước.

#### Scenario: Thành phần hệ thống có thư mục riêng

- **WHEN** kiểm kê thư mục gốc
- **THEN** frontend nằm trọn trong `web/`, backend trong `backend/`, đường ống kéo và
  gộp trong `scripts/`, schema và nạp trong `db/`
- **AND** không file `.html`, `.js`, hay `.css` nào của dashboard còn ở gốc

#### Scenario: Tài liệu và kế hoạch không nằm ở gốc

- **WHEN** kiểm kê thư mục gốc
- **THEN** không còn file `.xlsx`, `.docx`, hay ghi chú cuộc họp nào ở đó
- **AND** chúng nằm trong `planning/`

#### Scenario: Thư mục công cụ giữ nguyên vị trí

- **WHEN** chạy `openspec list` sau khi dời
- **THEN** lệnh tìm thấy `openspec/config.yaml` và liệt kê đúng các change như trước
- **AND** `openspec/`, `.claude/`, `.agent/`, `.codex/` vẫn ở gốc

### Requirement: Mã nguồn tách khỏi dữ liệu chạy

Thư mục chứa mã SHALL không chứa dữ liệu do chương trình sinh ra khi chạy. Database
SQLite SHALL nằm trong `var/`, tách khỏi `db/` — nơi chỉ còn giữ schema và module nạp.

Ranh giới này phân biệt hai thứ có hậu quả khác hẳn nhau khi mất: `data/` là dữ liệu
thô kéo về, mất là mất vĩnh viễn vì cửa sổ lưu giữ ở nguồn trượt nhanh; `var/` dựng lại
được hoàn toàn từ `data/`.

#### Scenario: Xoá dữ liệu chạy là thao tác an toàn

- **WHEN** xoá toàn bộ `var/` rồi chạy lại lệnh dựng database
- **THEN** database được dựng lại đầy đủ từ `data/`
- **AND** không mã nguồn nào bị mất

#### Scenario: Không còn dữ liệu trong thư mục mã

- **WHEN** liệt kê `db/`
- **THEN** chỉ thấy file `.sql` và `.py`
- **AND** không thấy file `.sqlite` nào

### Requirement: Thư mục kiểm thử phân biệt theo nghĩa vụ

Thư mục `tests/` SHALL chỉ chứa những phép kiểm được kỳ vọng luôn đạt. Script chẩn đoán
một lần — viết cho một cuộc điều tra cụ thể và hết giá trị bảo vệ sau đó — SHALL nằm
trong `tools/`.

Đường ống sản xuất MUST NOT gọi vào `tests/` hay `tools/`. Script nào được
`update_dashboard.py` gọi thì SHALL nằm trong `scripts/`.

#### Scenario: Đường ống không gọi ra ngoài thư mục sản xuất

- **WHEN** đọc toàn bộ lời gọi lệnh trong `scripts/update_dashboard.py`
- **THEN** mọi script được gọi đều nằm trong `scripts/` hoặc `db/`
- **AND** không lời gọi nào trỏ tới `tests/` hoặc `tools/`

#### Scenario: Bước vá dữ liệu dự phòng vẫn chạy đúng

- **WHEN** chạy bước cuối của đường ống sau khi hai script sản xuất đã chuyển sang
  `scripts/`
- **THEN** nó sinh được file dữ liệu trung gian và vá thành công vào `web/js/app.js`
- **AND** ảnh chụp gốc `app.js.bak` từ 02/08 không bị ghi đè

#### Scenario: File biên dịch không bị git theo dõi

- **WHEN** chạy `git ls-files` và lọc theo `__pycache__`
- **THEN** không dòng nào khớp

### Requirement: Tài liệu phân tầng theo tuổi thọ

`docs/` SHALL chia theo tuổi thọ của nội dung: `reference/` mô tả hệ thống đang là gì,
`decisions/` giữ quyết định còn hiệu lực, `archive/` giữ nhật ký phiên có ngày tháng.

Chỉ `docs/reference/` SHALL được cập nhật theo cấu trúc thư mục mới. `docs/archive/`
MUST NOT bị sửa đường dẫn — nó ghi lại điều đã đúng tại thời điểm viết, và sửa nó là
làm sai lịch sử.

#### Scenario: Tài liệu tra cứu nói đúng cách chạy hiện tại

- **WHEN** làm theo đúng chữ trong `docs/reference/toan-trinh-du-lieu.md` để khởi động
  dashboard
- **THEN** lệnh chạy được và trang mở đúng
- **AND** lệnh đó khởi động máy chủ tĩnh từ trong `web/`, ràng buộc về loopback

#### Scenario: Nhật ký phiên giữ nguyên chữ cũ

- **WHEN** so `docs/archive/` trước và sau khi dời
- **THEN** nội dung mọi file y hệt, chỉ vị trí thư mục thay đổi

