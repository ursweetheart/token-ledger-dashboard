# model-catalog-coverage Specification

## Purpose
TBD - created by archiving change close-the-known-gateway-loose-ends. Update Purpose after archive.
## Requirements
### Requirement: Danh mục model phải nhận diện mọi model đang được phục vụ thật
Cơ chế phân loại model từ tên SKU hoá đơn SHALL (PHẢI) ánh xạ được mọi tên model mà Google
đang thực sự định tuyến lưu lượng sản xuất tới, về một dòng `dim_model` khác NULL. Cơ chế đó gồm
`guess_model()` trong `db/rules.py`, dựa trên `MODELS`/`MODEL_PATTERNS`, và catalog `dim_model`
sinh ra từ đó. Hệ thống MUST NOT (KHÔNG được) để một dòng hoá đơn của model đang phục vụ thật
rơi vào `model_id = NULL` một cách im lặng.

#### Scenario: Google ép chuyển sang một model đã đổi tên

- **WHEN** Google trả về lỗi/thông báo ngừng phục vụ trỏ một model đang dùng sang tên model
  mới (ví dụ `gemini-2.5-flash` bị chặn, chỉ sang dùng `gemini-3.6-flash`), và tên mới đó
  sau đó xuất hiện trong SKU hoá đơn
- **THEN** `guess_model()` PHẢI trả về tên chuẩn hoá của model mới thay vì `None`, và
  `dim_model` PHẢI có sẵn dòng tương ứng cho model đó

#### Scenario: Thêm mẫu mới không được làm sai lệch mẫu cũ

- **WHEN** một mẫu tên model mới được thêm vào `MODEL_PATTERNS` mà chuỗi của nó có thể
  trùng một phần với mẫu của một model khác đã có sẵn
- **THEN** mẫu mới PHẢI được đặt đúng vị trí theo quy tắc "mẫu dài hơn/cụ thể hơn thử
  trước" đã có trong file, để không có SKU nào bị phân loại nhầm sang model khác do thứ tự
  kiểm tra sai
