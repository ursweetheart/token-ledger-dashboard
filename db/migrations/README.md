# Schema migrations

Alembic là nguồn schema đang sống duy nhất của dự án. Mỗi thay đổi schema phải thêm
một Python revision mới trong `versions/` và một file SQL tương ứng trong `sql/`.
Revision đã áp dụng là bất biến: không bao giờ sửa lại; muốn bỏ một thay đổi thì thêm
một revision tiến mới để thực hiện việc bỏ đó.

Dự án không hỗ trợ `downgrade()`. Hạ schema bằng migration lùi bị từ chối; mọi thao tác
gỡ bỏ đều đi qua một upgrade revision mới để lịch sử trên mọi database đi cùng một chiều.

Không dùng `alembic revision --autogenerate`. Dự án theo hướng SQL-first, và các view
viết tay chứa quy tắc nghiệp vụ mà autogenerate không thể tái tạo đúng. Hãy viết SQL
rõ ràng, review file SQL, rồi để Python revision thực thi đúng file đó.

Khi revision chạy SQL, dùng raw DBAPI cursor và gọi `cursor.execute(sql)` mà không truyền
đối số thứ hai rỗng. Cách này giữ các dấu `%` trong SQL và comment là ký tự nguyên văn;
`cursor.execute(sql, ())` có thể khiến driver hiểu chúng là placeholder.

`db/02_catalog.sql` là seed data được sinh ra, không phải migration. Luồng rebuild chạy
migrations trước rồi mới nạp lại catalog này; đừng đưa dữ liệu sinh tự động đó vào chuỗi
revision.

Hai đường vận hành có mục đích khác nhau:

- `alembic upgrade head` đổi schema tại chỗ và giữ nguyên dữ liệu hiện có.
- `python scripts/rebuild_db.py` cố ý xoá sạch, chạy migrations, rồi nạp catalog và dữ
  liệu từ `data/`.

DSN của Alembic lấy từ `connect.DEFAULT_DSN` (hoặc đường ghi đè runtime đã được hỗ trợ).
Không khôi phục `sqlalchemy.url` trong `alembic.ini`, vì làm vậy sẽ tạo nguồn cấu hình
kết nối thứ hai và có thể đưa migration sang nhầm database.
