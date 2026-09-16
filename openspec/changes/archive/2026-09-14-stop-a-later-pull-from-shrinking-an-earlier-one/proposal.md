## Why

Repo giữ lại mọi lần kéo cũ trên đĩa để chống cửa sổ lưu giữ của Google. Nhưng ở ba chỗ, **một lần kéo sau vẫn làm co được dữ liệu của lần kéo trước**, và cả ba chỗ đều im lặng. Đo ngày 14/09/2026:

- **Monitoring.** `scripts/merge_monitoring.py:83-95` cho *bản mới thắng* khi hai lần kéo lệch giá trị. Quét 6 lần kéo × 7 project (khoảng 2,95 triệu dòng) tìm được **14 điểm lệch, cả 14 đều là lần kéo sau báo nhỏ hơn**. Tổng cộng **11.262 token** đã bị bỏ, trong đó có 3.462 token ngày 11/06. Ở những điểm có nhân chứng độc lập (`api_request_count`, histogram độ trễ), nhân chứng nghiêng về số **cũ**. Lần kéo mới thiếu dòng ngay sát các điểm đó.
- **Độ trễ.** `merge_latency_daily.py:185-190` chỉ đọc đúng **một** lần kéo. `latency-daily.csv` hiện tại bắt đầu từ 09/06, trong khi bản sao tay ngày 17/08 bắt đầu từ 01/05. Lần kéo 08/08 vẫn còn dữ liệu tháng 5 trên đĩa, nhưng không vào được database.
- **Nhà cung cấp.** `load_provider.py:196-198` chỉ đọc lần kéo **mới nhất**. Lần kéo thứ hai sẽ đè mất các ngày cũ ở lần dựng lại kế tiếp.

**Việc sửa bị ràng buộc thứ tự.** `scripts/update_dashboard.py` bước 7 hiện đang **hỏng**: gọi `merge_latency_daily.py` không có `--in` trên thư mục có 4 lần kéo thì thoát 1 (đã chạy thật). Chính lỗi đó đang chặn đường tới bước 8, nơi `connect.rebuild()` gọi `DROP SCHEMA public CASCADE`, lệnh này xoá mọi GRANT (vụ 02/09: `api_readonly` đọc 0/20 bảng suốt 38 phút). Sửa phần gộp độ trễ là **tháo chốt** đường đó. Vì vậy change này phải bỏ `DROP SCHEMA` trước hoặc cùng lúc, không được sau.

## What Changes

- Gộp Monitoring: khi hai lần kéo cho **cùng khoá, khác giá trị**, giữ **số lớn hơn** thay cho "bản mới thắng". Mọi ca lệch được **ghi ra tệp** nằm cạnh bản gộp, thay vì chỉ in ra màn hình.
- Gộp độ trễ: đọc **mọi** lần kéo trong `do_tre_phan_bo/`. Với cùng một phút và cùng một chuỗi, giữ điểm có `count` lớn hơn. Bước 7 của `update_dashboard.py` chạy lại được mà không cần `--in`.
- Gộp Monitoring và gộp độ trễ **chỉ đọc thư mục đúng khuôn tên** của lần kéo sản xuất, và in danh sách bị bỏ qua. Lần kéo 1 giờ và lần kéo bằng tài khoản khác không còn lọt vào. Hôm nay thư mục `2026-09-04-1h-dinhthinhan18111971` sẽ mang 133 dòng, 112.546 token của một project lạ vào bản gộp nếu gộp mặc định.
- Nạp nhà cung cấp: đọc **mọi** lần kéo mang tên tài khoản. Với cùng một ngày, project, model và đại lượng, giữ số lớn hơn và ghi ca lệch.
- Dựng lại database: **bỏ `DROP SCHEMA public CASCADE`**. Thay bằng `alembic upgrade head` để schema lên bản mới nhất tại chỗ, rồi xoá dòng của mọi bảng dữ liệu (không đụng `alembic_version` và `ref_source`, hai bảng mà chính migration ghi dòng) trong **một** giao dịch, rồi mới nạp danh mục. Bảng, view, schema và GRANT còn nguyên. **BREAKING** với ai đang dựa vào việc dựng lại để **gỡ** một bảng không còn trong migration: nay việc đó phải qua migration.
- Không đổi: luật cấm dịch vụ `tools` trong lệnh triển khai (`docs/reference/luat-trien-khai-tu-dong-13-09.md`). Change này làm đường dựng lại **bớt hại**, nhưng không làm nó thành việc của lệnh triển khai.

## Capabilities

### New Capabilities
- `pull-merge-completeness`: Gộp nhiều lần kéo của cùng một nguồn không được để lần kéo sau làm co dữ liệu của lần trước. Áp cho Monitoring, histogram độ trễ, và số của nhà cung cấp. Mọi ca lệch phải để lại dấu vết đọc được.

### Modified Capabilities
- `schema-migrations`: yêu cầu "Đổi schema KHÔNG được đòi xoá dữ liệu" hiện **cho phép** đường dựng lại `DROP SCHEMA`. Nay đường đó MUST NOT xoá schema. Nó chỉ được xoá **dòng**, và phải giữ GRANT.
- `single-database-engine`: scenario "Dựng lại database" hiện khoá `connect.rebuild()` vào đúng một đường là `DROP SCHEMA public CASCADE` rồi chạy migration. Nay đường đó là migration tại chỗ, rồi xoá dòng trong một giao dịch.

## Impact

- **Mã:** `scripts/merge_monitoring.py`, `scripts/merge_latency_daily.py`, `db/load_provider.py`, `db/connect.py` (`rebuild()`), `scripts/update_dashboard.py` (bước 7).
- **Phép kiểm:** `tests/test_connect_migrations.py` đang khoá thứ tự `drop → migrate → seed`, nên phải viết lại theo đường mới. Thêm phép kiểm cho luật gộp. Mốc số phép kiểm Python trong `.github/workflows/ci.yml` (`EXPECTED_PY: "11"`) sẽ phải đổi.
- **Dữ liệu:** không đụng `data/`. Database dựng lại sẽ **khác** bản hiện tại: +11.262 token Monitoring, và thêm các ngày độ trễ trước 09/06 (ít nhất từ 01/05; lần kéo 08/08 còn 173 điểm tháng 5 chỉ riêng `multimodal-invoice`). Đây là thay đổi có chủ đích và phải được đo, không phải lỗi.
- **Tài liệu:** docstring `scripts/rebuild_db.py` và `scripts/check_db_grants.py`, `docs/reference/toan-trinh-du-lieu.md`, `docs/reference/luat-trien-khai-tu-dong-13-09.md`.
- **Không đụng:** frontend, API, compose, lệnh triển khai.
