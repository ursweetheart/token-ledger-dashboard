## Why

Nhật ký đo lường Gateway ngày 26–27/08/2026 để lộ ba lỗ hổng nhỏ, không nằm trên đường
găng của kế hoạch nén 30/09, nhưng mỗi cái có kiểu hỏng riêng nếu bỏ quên: một cái làm mất
model âm thầm trong dữ liệu hoá đơn, một cái là tài liệu hướng dẫn dựng lại database bằng
một script đã xoá, một cái là tên thư mục sao lưu tự phá thứ tự thời gian của chính nó. Ba
việc này gói chung vì cùng một lý do: đều **phát hiện được nhưng chưa đóng lại**, và mỗi
ngày để trôi là một ngày rủi ro tương ứng lớn thêm (hoá đơn Google chuyển hẳn sang
`gemini-3.6-flash`, càng nhiều dòng SpendLogs mất model).

## What Changes

- Thêm các tên model mà Google đang ép chuyển sang (`gemini-3.6-flash`, và mọi biến thể
  cùng họ đã xác nhận) vào `db/rules.py` (`MODELS`, `MODEL_PATTERNS`) và vào catalog
  `dim_model` sinh bởi `db/gen_catalog.py`, để `guess_model()` không còn trả `None` cho
  model đang được phục vụ thật.
- Quyết định và ghi lại số phận của
  `docs/superpowers/plans/2026-08-18-docker-packaging.md`: kế hoạch này còn tham chiếu
  `scripts/copy_to_postgres.py` và `var/token_ledger.sqlite` — cả hai đã bị xoá trong các
  đợt dọn dẹp 17/08 và 24/08. Nếu còn giá trị thì sửa lại theo đường ống hiện tại
  (`alembic upgrade head` / `rebuild_db.py`); nếu không thì đánh dấu lỗi thời để không ai
  làm theo và dựng ra một PostgreSQL rỗng.
- Đổi tên thư mục sao lưu `D:\RangDonk\token-ledger-backup\2026-26-08` thành
  `2026-08-26`, khớp định dạng `YYYY-MM-DD` mà hai thư mục sao lưu còn lại
  (`2026-08-08`, `2026-08-26-truoc-cutover`) đang dùng — định dạng duy nhất khiến sắp xếp
  theo bảng chữ cái trùng với sắp xếp theo thời gian.

## Capabilities

### New Capabilities
- `model-catalog-coverage`: hệ thống phân loại model từ tên SKU hoá đơn
  (`guess_model()` / `MODELS` / `dim_model`) phải nhận diện được mọi model Google đang
  thực sự định tuyến lưu lượng tới, không được âm thầm trả về model rỗng cho một model
  đang phục vụ thật.

### Modified Capabilities
- (không có — hai việc còn lại là quyết định về tài liệu và đổi tên thư mục ngoài repo,
  không làm thay đổi hành vi hệ thống ở mức spec)

## Impact

- **Code**: `db/rules.py` (`MODELS`, `MODEL_PATTERNS`), `db/gen_catalog.py` (seed
  `dim_model`)
- **Dữ liệu**: bảng `dim_model` (thêm dòng), không đổi schema
- **Tài liệu**: `docs/superpowers/plans/2026-08-18-docker-packaging.md`
- **Vận hành, ngoài repo**: `D:\RangDonk\token-ledger-backup\2026-26-08` →
  `2026-08-26` (không ảnh hưởng mã nguồn)
- Không đụng tới tầng vận hành Gateway thật (Docker, khoá, virtual key) — phạm vi đó nằm
  ở một change khác
