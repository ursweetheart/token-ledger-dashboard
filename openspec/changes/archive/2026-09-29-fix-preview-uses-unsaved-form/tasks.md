## 1. Xem trước khớp với form (A)

- [x] 1.1 `web/index.html`: bỏ nút `Lưu bản nháp` (submit) trong `#connection-form`
- [x] 1.2 `web/js/gateway-connections.js`: thêm cờ `dirty`; bật khi form có `input`, khi "Thêm model", "Bỏ model" và "Lưu key và lấy tham chiếu"; tắt trong `fill()` và sau khi lưu thành công
- [x] 1.3 Tách phần thân của handler `submit` hiện tại thành hàm lưu dùng chung (gom model phụ + `request('', …)`)
- [x] 1.4 Handler "4. Xem thay đổi": `reportValidity()` → nếu `dirty` hoặc agent mới thì lưu → rồi preview; lưu lỗi thì dừng, Áp dụng vẫn tắt
- [x] 1.5 Sự kiện `submit` của form (nhấn Enter) chạy cùng luồng với nút Xem thay đổi
- [x] 1.6 Đổi câu báo sau "Lưu key và lấy tham chiếu": bỏ "lưu lại bản nháp", thay bằng "bấm Xem thay đổi để lưu và xem trước"

## 2. Tóm tắt thay đổi (F)

- [x] 2.1 Hàm so `preview.profile` với `selected.applied` theo danh sách trường có tên (tên, đang hoạt động, tham chiếu khoá, model, RPM, TPM, chế độ hết hạn mức, ngân sách); model so theo cặp alias → upstream
- [x] 2.2 Hiện tóm tắt trên JSON: "Chưa áp dụng lần nào…", "Không có thay đổi so với bản đang chạy", hoặc mỗi trường một dòng `Tên: cũ → mới`; kèm câu "thay đổi ngoài UI xem bằng nút Xem thay đổi ngoài UI"
- [x] 2.3 `web/index.html`: chỗ hiện tóm tắt (có `role="status"` hoặc nằm trong vùng đã có `aria-live`)

## 3. Nút và câu báo (G, H, D)

- [x] 3.1 `bind()`: `finally` đặt `disabled` theo trạng thái — Áp dụng cần `preview`, Chấp nhận baseline cần `drift`
- [x] 3.2 "Thu hồi key đã chọn": câu báo nêu tên key đã thu hồi
- [x] 3.3 `web/index.html`: ô khoá quản trị, ô khoá provider, ô Virtual Key thử dùng `autocomplete="new-password"`

## 4. Kiểm thử

- [x] 4.1 `tests/gateway-connections/browser_check.py`: bỏ các lần bấm "Lưu bản nháp" (dòng 82, 93), đổi chờ câu báo cho khớp
- [x] 4.2 Cho mock `/preview` trả lại bản nháp đã lưu, và mock hồ sơ có `applied`, để phép kiểm phân biệt được bản cũ và bản mới
- [x] 4.3 Ca kiểm: sửa RPM không lưu → Xem thay đổi → preview hiện RPM mới, revision tăng 1, tóm tắt có dòng RPM
- [x] 4.4 Ca kiểm: không sửa gì trên hồ sơ đã áp dụng → Xem thay đổi → revision không đổi, tóm tắt "Không có thay đổi"
- [x] 4.5 Ca kiểm: mock lưu trả 409 → không có request `/preview`, Áp dụng vẫn tắt
- [x] 4.6 Ca kiểm: sau preview, bấm "Lưu key và lấy tham chiếu" → Áp dụng tắt, lần Xem thay đổi sau có lưu
- [x] 4.7 Ca kiểm: sau khi chấp nhận baseline, nút Chấp nhận vẫn tắt
- [x] 4.8 Ca kiểm: mọi khoá của `draft` trong mock đều nằm trong danh sách trường của hàm so sánh (trường mới làm test đỏ)
- [x] 4.9 Ca kiểm: ba ô mật khẩu có `autocomplete="new-password"`
- [x] 4.10 Chạy `browser_check.py` và bộ `tests/connection_*_cases.py`, ghi kết quả

## 5. Tài liệu và kiểm trên dashboard local

- [x] 5.1 `docs/reference/dashboard-setup.md:56`: bỏ bước "Lưu bản nháp" khỏi luồng thao tác
- [x] 5.2 Lặp lại phép thử ngày 29/09 trên hồ sơ `dms-tap`: RPM 15 → 20, không lưu, Xem thay đổi → preview hiện 20, tóm tắt `RPM: 15 → 20` (không bấm Áp dụng; sau đó trả RPM về 15 và xem trước lại để bản nháp khớp bản đang chạy)
- [x] 5.3 Mở tab trong Chrome đã lưu mật khẩu: ô khoá quản trị trống
