## MODIFIED Requirements

### Requirement: Thư mục kiểm thử phân biệt theo nghĩa vụ

Thư mục `tests/` SHALL chỉ chứa những phép kiểm được kỳ vọng luôn đạt. Script chẩn đoán
một lần — viết cho một cuộc điều tra cụ thể và hết giá trị bảo vệ sau đó — SHALL nằm
trong `tools/`.

Đường ống sản xuất MUST NOT gọi vào `tests/` hay `tools/`. Script nào được
`update_dashboard.py` gọi thì SHALL nằm trong `scripts/`.

Đường ống sản xuất cũng MUST NOT ghi vào `web/`. Frontend là mã nguồn, không phải đích đến
của dữ liệu — xem capability `single-source-dashboard-data`.

#### Scenario: Đường ống không gọi ra ngoài thư mục sản xuất

- **WHEN** đọc toàn bộ lời gọi lệnh trong `scripts/update_dashboard.py`
- **THEN** mọi script được gọi đều nằm trong `scripts/` hoặc `db/`
- **AND** không lời gọi nào trỏ tới `tests/` hoặc `tools/`

#### Scenario: Đường ống không ghi vào thư mục frontend

- **WHEN** chạy trọn đường ống rồi kiểm `git status` trên `web/`
- **THEN** không file nào trong `web/` bị đường ống sửa
- **AND** `web/js/app.js` giữ nguyên như trong git

#### Scenario: File biên dịch không bị git theo dõi

- **WHEN** chạy `git ls-files` và lọc theo `__pycache__`
- **THEN** không dòng nào khớp

## REMOVED Requirements

### Requirement: Bước vá dữ liệu dự phòng vẫn chạy đúng

**Reason**: Bước cuối của đường ống (`[10/10] Va du lieu du phong vao app.js`) bị xoá hoàn
toàn, cùng hai script duy nhất tồn tại để phục vụ nó —
`scripts/sinh_du_lieu_dashboard.py` và `scripts/va_app_js.py` — và ảnh chụp
`web/js/app.js.bak`. Không còn dữ liệu dự phòng nào để vá, nên scenario này không còn đối
tượng để kiểm.

Đây vốn là một scenario nằm trong requirement *"Thư mục kiểm thử phân biệt theo nghĩa vụ"*
ở trên; nó được nêu riêng ở đây để việc bỏ nó là tường minh, chứ không lặng lẽ mất khi
requirement kia được cập nhật.

**Migration**: Thay bằng scenario *"Đường ống không ghi vào thư mục frontend"* trong
requirement đã sửa ở trên — phát biểu ngược lại: trước đây đường ống PHẢI vá được vào
`app.js`, giờ nó MUST NOT chạm vào `web/`. Dữ liệu dự phòng không có thứ thay thế: khi
không nạp được, dashboard báo lỗi thay vì hiện số cũ (capability
`visible-data-provenance`).
