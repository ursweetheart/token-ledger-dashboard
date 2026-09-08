# project-layout

## MODIFIED Requirements

### Requirement: Mã nguồn tách khỏi dữ liệu chạy

Thư mục chứa mã SHALL không chứa dữ liệu do chương trình sinh ra khi chạy.

Ranh giới này phân biệt hai thứ có hậu quả khác hẳn nhau khi mất: `data/` là dữ liệu
thô kéo về, mất là mất vĩnh viễn vì cửa sổ lưu giữ ở nguồn trượt nhanh; `var/` dựng lại
được hoàn toàn từ `data/`.

**Sửa 24/08/2026.** Bản trước ra lệnh *"Database SQLite SHALL nằm trong `var/`, tách khỏi
`db/`"*. Câu đó nay không còn đối tượng: SQLite đã bị gỡ khỏi dự án, và database sống trong
volume Docker `pgdata` chứ không nằm trong cây thư mục repo. Yêu cầu **tách mã khỏi dữ liệu
chạy vẫn giữ nguyên** — chỉ đổi cái ví dụ minh hoạ, vì `var/` nay chứa bản chụp bộ số bất
biến của `tools/baseline_db.py` thay vì một file database.

#### Scenario: Xoá dữ liệu chạy là thao tác an toàn

- **WHEN** xoá toàn bộ `var/` rồi chạy lại lệnh dựng database
- **THEN** database được dựng lại đầy đủ từ `data/`
- **AND** không mã nguồn nào bị mất

#### Scenario: Không còn dữ liệu trong thư mục mã

- **WHEN** liệt kê `db/`
- **THEN** chỉ thấy file `.sql`, `.py` và thư mục `migrations/`
- **AND** MUST NOT thấy file database nào
