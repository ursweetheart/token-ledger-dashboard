# Kiểm chứng — 2026-09-30

Áp dụng `.claude/skills/tu-soat`: tự đọc lại trước khi chạy, chạy test giả (Chromium thật, HTTP giả) trước,
rồi thử đột biến, rồi mới thử trên dashboard local thật.

## 4. Kiểm thử tự động

| Bộ | Kết quả |
|---|---|
| `tests/gateway-connections/browser_check.py` (Chromium thật, HTTP giả; chạy bằng `.local/connections/venv`) | **PASS** — ca 4.1, 4.3–4.9, Enter, và 3.2 |
| `unittest discover -s tests -p "test_*.py"` | 208 OK (mốc `EXPECTED_PY` không đổi) |
| `pytest tests/connection_config_cases.py tests/connection_auth_cases.py` | 26 passed |
| `node --test tests/*.test.js` | 117 pass, 0 fail (mốc `EXPECTED_JS` không đổi) |

Backend không đổi nên các bộ connection trên fixture Docker không chạy lại.

**Thử đột biến** (sửa tạm code rồi khôi phục, mã băm file khớp trước/sau):

| Đột biến | Mô phỏng lỗi | Kết quả |
|---|---|---|
| Bỏ điều kiện `dirty` khi lưu | lỗi A (xem trước bản cũ) | test đỏ ở dòng 118 (bước Enter: không lưu → `saves()` không tăng) |
| "Chấp nhận baseline" bật lại mù | lỗi G | test đỏ ở dòng 158 (`accept.is_disabled()`) |

## 5. Dashboard local thật (container `web` build lại từ working tree)

- **5.3** Chrome đã lưu mật khẩu cho origin này (ngày 29/09 ô khoá bị điền sẵn): mở tab Kết nối → ô
  "Khoá quản trị kết nối" **trống**.
- **5.2** Hồ sơ `dms-tap` (bản nháp 2 = đã áp dụng 2):
  - RPM 15 → 20, không lưu, bấm "4. Xem thay đổi" → "Đã lưu bản nháp (revision 3)", preview `"rpm": 20`,
    tóm tắt đúng một dòng `RPM: 15 → 20`, nút Áp dụng bật. (Ngày 29/09 cùng thao tác cho preview
    revision 2 với `"rpm": 15`.)
  - Sửa RPM về 15 → nút Áp dụng tắt, tóm tắt và JSON cũ biến mất.
  - Nhấn **Enter** trong ô RPM → "Đã lưu bản nháp (revision 4)", preview `"rpm": 15`, tóm tắt "Không có thay
    đổi so với bản đang chạy."
  - Không bấm Áp dụng: trạng thái cuối "Bản nháp: 4 · Đã áp dụng: 2", Gateway không đổi.

## Lỗi tự bắt được trước khi chạy

1. Form không có nút submit thì Enter không gửi form (luật HTML khi form có nhiều ô). Chỉ bỏ nút "Lưu bản
   nháp" thì task 1.5 không chạy. Sửa: "4. Xem thay đổi" là nút `type="submit"`, một đường xử lý duy nhất.
2. Sửa form nhưng tóm tắt/JSON của lần xem trước cũ vẫn trên màn hình: người dùng đọc nhầm, và lệnh chờ
   trong test qua ngay (phép kiểm rỗng). Sửa: hàm `invalidate()` xoá cả hai.
3. Test tìm endpoint bằng `select_option` cùng giá trị có thể không phát sự kiện `change` → dùng nút "Tải lại".

## Phát hiện thật (ngoài phạm vi)

- Luật tên tiếng Anh (`tools/check_english_names.py`) **không chạy trên repo trong CI** (chỉ có unit test của
  chính công cụ). Toàn repo hiện có 80 vi phạm (tests 56, scripts 17, backend 5, db 2). Change này đánh dấu
  `# vi-ok` cho 20 dòng nó thêm vào `browser_check.py`: file đó từ 24 (HEAD) còn 17 vi phạm.
- `browser_check.py` cần `playwright`, chỉ có trong `.local/connections/venv`, không có trong Python chung
  của máy và không nằm trong CI.
- Khoá quản trị kết nối trên máy dev đoán được từ `DASHBOARD_KEY`, mà khoá đó từng nằm trong Master Plan
  có trong lịch sử git. Nên đổi cả hai.
