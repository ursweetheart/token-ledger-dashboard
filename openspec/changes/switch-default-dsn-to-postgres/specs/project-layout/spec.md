## MODIFIED Requirements

### Requirement: Mã nguồn tách khỏi dữ liệu chạy

Thư mục chứa mã SHALL không chứa dữ liệu do chương trình sinh ra khi chạy. Dữ liệu chạy
của database SHALL nằm ngoài cây mã nguồn: với PostgreSQL là volume Docker `pgdata` do
`docker-compose.yml` khai báo, với SQLite (chỉ dùng để đối chiếu bằng tay) là `var/`.

Ranh giới này phân biệt hai thứ có hậu quả khác hẳn nhau khi mất: `data/` là dữ liệu thô
kéo về, mất là mất vĩnh viễn vì cửa sổ lưu giữ ở nguồn trượt nhanh; dữ liệu chạy của
database dựng lại được hoàn toàn từ `data/` bằng `scripts/rebuild_db.py`.

Sau khi PostgreSQL thành mặc định, `var/` KHÔNG còn chứa database của dự án. Nó vẫn là nơi
duy nhất được phép chứa database SQLite nếu ai đó dựng một bản để đối chiếu.

#### Scenario: Xoá dữ liệu chạy là thao tác an toàn

- **WHEN** xoá sạch dữ liệu chạy của database — `docker compose down -v` với PostgreSQL —
  rồi chạy lại lệnh dựng database
- **THEN** database được dựng lại đầy đủ từ `data/`
- **AND** không mã nguồn nào bị mất

#### Scenario: Không còn dữ liệu trong thư mục mã

- **WHEN** liệt kê `db/`
- **THEN** chỉ thấy file `.sql` và `.py`
- **AND** không thấy file `.sqlite` nào

#### Scenario: Thư mục dữ liệu chạy không còn database mặc định

- **WHEN** liệt kê `var/` sau khi đã chuyển sang PostgreSQL
- **THEN** không thấy `token_ledger.sqlite`
- **AND** đường ống vẫn dựng lại được database đầy đủ mà không cần file đó
