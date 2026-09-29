## Why

Rà tab **Kết nối agent** ngày 29/09/2026 tìm ra năm lỗi, đều nằm ở giao diện (`web/index.html`,
`web/js/gateway-connections.js`). Lỗi nặng nhất làm người dùng áp dụng nhầm cấu hình cũ; lỗi thứ hai
làm họ không biết bấm Áp dụng sẽ đổi gì.

- **A — Xem trước bản đã lưu, không phải form.** Nút "4. Xem thay đổi" gửi `selected.revision`
  (`gateway-connections.js:208`), nên worker xem trước bản nháp **đã lưu**. Sửa form mà quên lưu thì
  bản xem trước vẫn là bản cũ và nút "5. Áp dụng" vẫn sáng.
  **Đã chứng minh trên trình duyệt thật:** hồ sơ `dms-tap`, form RPM = 20 (chưa lưu), bản xem trước
  trả `"rpm": 15` (revision 2), nút Áp dụng bật.
- **F — "Xem thay đổi" không cho thấy thay đổi.** Kết quả là toàn bộ cấu hình đích (~200 dòng JSON:
  mọi tuyến, general/router settings), không so với bản đang chạy (`connection_worker.py:263-270`).
  Với `dms-tap` (nháp = đã áp dụng = revision 2) màn hình không nói được câu "không có thay đổi".
  API đã trả sẵn bản đã áp dụng trong cột `applied` (`connection_store.py:37`,
  `connection_worker.py:492`), nên so sánh làm được ở giao diện.
- **G — Nút "Chấp nhận baseline đã xem" tự bật lại** sau khi dùng: khối `finally` của `bind()`
  (`gateway-connections.js:87`) bật lại mọi nút trừ Áp dụng. Bấm lần nữa ra lỗi.
- **H — "Thu hồi key đã chọn" không báo gì khi xong**, trong khi "Thu hồi tất cả" có câu báo.
- **D — Chrome lưu và tự điền khoá quản trị.** Ô khoá dùng `autocomplete="off"` (`index.html:1368`),
  Chrome bỏ qua giá trị này với ô mật khẩu. Đã thấy trên màn hình: ô khoá được điền sẵn khi mở tab.

## What Changes

- "4. Xem thay đổi" **tự lưu trước** khi form có thay đổi chưa lưu (hoặc là agent mới), rồi mới xem
  trước bản vừa lưu. Form không đổi thì không lưu thêm. Lưu lỗi thì dừng, không xem trước.
- **Bỏ nút "Lưu bản nháp"** (23 → 22 nút). Xem trước không ghi gì lên Gateway nên nó là điểm lưu.
- Trên kết quả xem trước, thêm **tóm tắt thay đổi so với bản đã áp dụng** của agent này (ví dụ
  `RPM: 15 → 20`), hoặc "Không có thay đổi", hoặc "Chưa áp dụng lần nào". JSON đầy đủ vẫn giữ bên dưới.
- Nút "Chấp nhận baseline đã xem" chỉ bật khi đang có bản review chưa chấp nhận.
- "Thu hồi key đã chọn" báo kết quả như "Thu hồi tất cả".
- Ba ô mật khẩu của tab (khoá quản trị, khoá provider, Virtual Key thử) dùng
  `autocomplete="new-password"`.
- Backend không đổi.

## Capabilities

### New Capabilities

(không có)

### Modified Capabilities

- `gateway-connection-management`: thêm yêu cầu về bản xem trước (khớp form, tóm tắt thay đổi), phản
  hồi của nút, và ô nhập khoá. Capability này còn nằm trong change chưa archive
  `configure-agent-gateway-connections-from-ui` (và được `allow-any-provider-in-connections-tab` sửa
  tiếp). Delta ở đây chỉ **thêm** yêu cầu. Archive theo thứ tự: `configure-…` → `allow-any-provider-…`
  → change này.

## Impact

- `web/index.html`: bỏ nút `Lưu bản nháp`; đổi `autocomplete` của ba ô mật khẩu; thêm chỗ hiện tóm tắt.
- `web/js/gateway-connections.js`: cờ `dirty`, luồng lưu-rồi-xem-trước, hàm so sánh bản nháp với bản
  đã áp dụng, sửa `bind()`, câu báo thu hồi.
- `tests/gateway-connections/browser_check.py`: bỏ các lần bấm "Lưu bản nháp", thêm ca kiểm.
- `docs/reference/dashboard-setup.md:56`: luồng thao tác bỏ bước "Lưu bản nháp".
- Không đụng backend, database, worker hay Gateway.

**Ngoài phạm vi** (ghi lại khi rà ngày 29/09):
- Hai tab cùng sửa hạn mức key → change riêng `keep-connection-keys-out-of-setting-quota`.
- `scripts/dashboard.py start` không bật postgres trước worker (chỉ hỏng khi postgres bị tắt bằng tay).
- Gộp hai nút "Hướng dẫn host/Docker".
- DASHBOARD_KEY bị ghi trong Master Plan và một file đã commit; Master Plan lệch với code ở 3 chỗ.
