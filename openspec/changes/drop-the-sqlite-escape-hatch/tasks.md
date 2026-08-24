# Tasks

Quy ước đặt tên: **định danh tiếng Anh, ghi chú tiếng Việt** (chốt 14/08).

## 1. Ghi mốc trước khi gỡ

- [ ] 1.1 `python tools/baseline_db.py --compare var/baseline-2026-08-24.json` → phải
      **23/23 khớp**. Change này không đụng dữ liệu, nên con số phải y nguyên ở cuối
- [ ] 1.2 Ghi mốc bộ kiểm: `audit_db.py` **36 · 31 đạt · 5 lưu ý · 0 hỏng**,
      `check_api.py` **19 · 19 đạt · 0 hỏng**
- [ ] 1.3 Ghi lại số chỗ **không được đụng**, để cuối change đếm lại:
      **14** chỗ gọi `open_db()`/`rebuild()`, **21** chỗ nối chuỗi `{ph}`

## 2. `db/connect.py` — gỡ nhánh, giữ hình dạng hàm

- [ ] 2.1 Sửa docstring đầu file: bỏ lời hứa *"HAI HỆ QUẢN TRỊ, MỘT BẢN SCHEMA"*. Thay bằng
      ghi chú nói **vì sao** SQLite bị gỡ, kèm ngày và ba điều kiện đã hỏng — để ba tháng
      nữa không ai "khôi phục cho đủ"
- [ ] 2.2 Xoá `SQLITE_DSN` và `is_sqlite()`
- [ ] 2.3 `open_db()`: bỏ nhánh `sqlite3`, giữ nguyên **trả về `(cn, "%s")`**
- [ ] 2.4 ⚠️ Giữ `placeholder` như một **hằng số**, kèm ghi chú tại chỗ nói vì sao nó còn
      sống dù chỉ còn một hệ: gỡ nó là sửa **35 chỗ** (14 điểm gọi + 21 chuỗi `{ph}`), một
      diff lớn không mua thêm gì. Dọn được sau bằng một change riêng
- [ ] 2.5 `run_sql_file()`: bỏ nhánh `executescript`
- [ ] 2.6 `rebuild()`: bỏ nhánh `p.unlink()`, chỉ còn `DROP SCHEMA public CASCADE`
- [ ] 2.7 Sửa thông báo lỗi thiếu `psycopg2` — nó đang mách *"hoặc dựng một bản SQLite"*,
      lời khuyên đó nay dẫn vào ngõ cụt

## 3. Các chỗ đọc còn lại

- [ ] 3.1 `backend/store.py:44-50` — bỏ nhánh SQLite. ⚠️ **Giữ nguyên tính chỉ-đọc của
      nhánh PostgreSQL**: `check_api.py` có phép kiểm *"Kết nối của backend là chỉ đọc
      (ReadOnlySqlTransaction)"*, và nó phải còn xanh
- [ ] 3.2 `scripts/audit_db.py:43-46` — bỏ nhánh
- [ ] 3.3 `scripts/merge_billing.py:203-209` — bỏ nhánh. Đọc kỹ ghi chú dòng 196: hàm này
      **từng** ghim cứng vào SQLite và đã được sửa ngày 17/08; đừng làm ngược lại
- [ ] 3.4 **Xoá `scripts/copy_to_postgres.py`.** Docstring của chính nó ghi *"CONG CU PHU…
      GIO DA HET DUNG"* và nó đòi một file SQLite làm nguồn — thứ đã bị xoá từ 17/08

## 4. Gỡ phí mà change `change-the-schema-without-dropping-it` đang gánh

- [ ] 4.1 `db/migrations/env.py`: xoá `_sqlalchemy_url()`, dùng thẳng DSN. Cập nhật docstring
- [ ] 4.2 `db/migrations/versions/001_baseline_baseline.py`: bỏ nhánh `executescript`, chỉ
      còn con trỏ DBAPI. ⚠️ **Giữ nguyên lời gọi không đối số thứ hai** — 11 dấu `%` trong
      ghi chú vẫn ở đó, và psycopg2 chỉ bỏ qua chúng khi gọi không tham số
- [ ] 4.3 ⚠️ `001_baseline.sql` **chưa được áp lên database thật nào** (mới chỉ chạy trên
      các database rác đã xoá), nên sửa được. Sau nhóm 5 của change kia thì không
- [ ] 4.4 Sang `openspec/changes/change-the-schema-without-dropping-it/tasks.md` gỡ task
      **3.5** và mọi ràng buộc "trung lập hai hệ" — chúng không còn đối tượng

## 5. Trợ giúp dòng lệnh và tài liệu

- [ ] 5.1 `scripts/rebuild_db.py`: bỏ dòng ví dụ `--db var/token_ledger.sqlite`, sửa trợ
      giúp của `--db`
- [ ] 5.2 `db/load_billing.py:59`: sửa trợ giúp *"Duong dan .sqlite, hoac chuoi ket noi
      PostgreSQL"*
- [ ] 5.3 `backend/requirements.txt`: sửa ghi chú nói *"Chay tren SQLite van duoc"*
- [ ] 5.4 `backend/check_api.py:34-38`: sửa phần docstring nói về `--compare` với SQLite
- [ ] 5.5 `docs/reference/dong-bo-may-dong-nghiep-*.md`: ghi rằng `--db <file>.sqlite` không
      còn nhận
- [ ] 5.6 `grep -rn "sqlite" --include=*.py --include=*.md .` — rà chỗ còn sót. Tài liệu
      trong `docs/archive/` **giữ nguyên**: chúng là biên bản lịch sử, sửa là làm sai sử

## 6. Nghiệm thu

- [ ] 6.1 `grep -rn "is_sqlite\|sqlite3\|SQLITE_DSN\|executescript" --include=*.py db/ scripts/ backend/`
      → **0 kết quả** (trừ `tools/` là công cụ điều tra một lần)
- [ ] 6.2 Đếm lại hai con số của task 1.3: vẫn **14** chỗ gọi và **21** chuỗi `{ph}` —
      chứng minh change chỉ gỡ nhánh, không lan vào tầng truy vấn
- [ ] 6.3 `tools/baseline_db.py --compare` → **23/23 khớp**
- [ ] 6.4 `audit_db.py` → không có phép hỏng mới so với mốc 1.2
- [ ] 6.5 `check_api.py` → **19/19**, và phép *"Kết nối của backend là chỉ đọc"* phải nằm
      trong số đạt
- [ ] 6.6 `node --test tests/*.test.js` vẫn xanh
- [ ] 6.7 Dựng lại toàn bộ trên một database rác qua `connect.rebuild()` → vẫn ra 19 bảng,
      3 view, `alembic_version = 001_baseline`, danh mục đủ 8 agent
- [ ] 6.8 Thử `--db var/gi_do.sqlite` → phải **hỏng to tiếng** với thông báo nói rõ SQLite
      không còn được đỡ, **không** được im lặng tạo một file rồi chạy nửa vời
