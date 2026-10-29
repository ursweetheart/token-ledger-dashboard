# Tự nhận diện và đăng ký model từ Gateway

## Mục đích

Gateway ghi tên model theo tên upstream, thường có dạng:

```text
gemini/gemini-3.5-flash-lite
```

Trong khi các nguồn dữ liệu khác có thể chỉ ghi tên chuẩn hoặc tên SKU. Repo dùng
hai lớp xử lý:

1. Ánh xạ model đã được review trước trong `db/rules.py`.
2. Tự đăng ký model Gateway mới khi dữ liệu thực tế xuất hiện.

Mục tiêu của lớp thứ hai là không làm mất model khỏi sổ Gateway chỉ vì model đó
chưa được khai báo thủ công.

## Luồng xử lý

```text
LiteLLM_SpendLogs
        |
        v
db/load_gateway.py: read_ledger()
        |
        v
auto_register_models()
        |
        +-- model đã có alias? ----------> dùng model_id hiện có
        |
        +-- model mới + lượt thành công --> thêm dim_model + alias
        |
        v
build_rows()
        |
        v
fact_call -> build_usage_daily -> dashboard
```

Trình tự chạy này được khai báo trong `scripts/rebuild_db.py`: Gateway ledger
phải chạy trước bước `build_usage_daily`, vì bảng usage là bảng dẫn xuất từ
`fact_call`.

## Vị trí mã nguồn

### 1. Tự đăng ký model mới

Hàm chính nằm tại:

```text
db/load_gateway.py:auto_register_models()
```

Hàm này được gọi trước `build_rows()` trong luồng nạp Gateway.

Nó thực hiện các bước:

1. Lấy các model đã biết từ `dim_model_alias`.
2. Tìm tên model thô xuất hiện trong ledger nhưng chưa có alias.
3. Chỉ tự đăng ký các dòng có `outcome = success`.
4. Tách tên dạng `provider/model`:

   ```text
   raw_name = gemini/gemini-3.8-flash
   provider = gemini
   name     = gemini-3.8-flash
   ```

5. Nếu `name` chưa có trong `dim_model`, thêm một dòng model mới.
6. Thêm ánh xạ `gateway + raw_name -> model_id` vào `dim_model_alias`.
7. Gán `model_id` cho các dòng Gateway để chúng đi tiếp vào bảng tổng hợp.

Các câu lệnh INSERT dùng `ON CONFLICT DO NOTHING`, nên chạy lại không tạo bản
ghi model hoặc alias trùng.

### 2. Danh sách model chuẩn và quy tắc nhận diện

Nằm trong:

```text
db/rules.py
```

Các thành phần quan trọng:

| Thành phần | Vai trò |
|---|---|
| `MODELS` | Danh sách tên chuẩn, `model_id` và family |
| `GATEWAY_MODELS` | Các tuyến Gateway đã được review và muốn đưa vào catalog chuẩn |
| `MODEL_PATTERNS` | Mẫu tên dùng để nhận diện model từ SKU hoặc tên nguồn |
| `guess_model()` | Trả về tên model chuẩn từ một chuỗi tên |

`MODEL_PATTERNS` phải đặt mẫu dài trước mẫu ngắn. Ví dụ `3.5 flash lite` phải
đứng trước `3.5 flash`, nếu không model Lite có thể bị nhận nhầm thành Flash.

### 3. Sinh catalog alias

`db/gen_catalog.py:model_aliases()` sinh các alias cho billing, monitoring,
application và Gateway. Đây là bước kiểm tra chặt:

- Nếu model đã biết và khớp quy tắc: tạo alias.
- Nếu tên không khớp: dừng với thông báo `CANNOT BE MAPPED`.
- `GATEWAY_MODELS` là danh sách khai báo thủ công, không phải toàn bộ dữ liệu
  Gateway thực tế.

Vì vậy, `gen_catalog.py` và `auto_register_models()` có mục đích khác nhau:

| Cơ chế | Mục đích |
|---|---|
| `gen_catalog.py` | Xây catalog chuẩn, có review, và bắt lỗi khai báo thiếu |
| `auto_register_models()` | Không để model Gateway mới làm mất dòng dữ liệu thực tế |

## Giới hạn của tự đăng ký

Tự đăng ký không phải là hiểu ngữ nghĩa đầy đủ của model. Nó chỉ suy ra:

- `provider` từ phần trước dấu `/`;
- `name` từ phần còn lại;
- `family` theo thông tin provider suy ra.

> Nó không tự tạo quy tắc giá chuẩn trong `ref_price`, không tự xác nhận model
> có đúng với model kinh doanh mong muốn và không thay thế bước review trong
> `db/rules.py`.

> Chi phí Gateway của từng lượt vẫn lấy từ metadata `cost_breakdown` của LiteLLM
> trong quá trình nạp ledger; việc tự đăng ký chủ yếu mở khóa việc gom nhóm theo
> `model_id`.

Nếu một model chưa biết xuất hiện ở dòng lỗi hoặc không có model name, dòng đó
có thể vẫn được giữ trong `fact_call` với `model_id = NULL`. Các bảng usage theo
model lọc `model_id IS NOT NULL`, nên dòng này sẽ không được đưa vào rollup theo
model cho tới khi có quy tắc hoặc alias phù hợp.

## Cách bổ sung model chính thức

Khi model mới đã được xác nhận là model cần theo dõi chính thức:

1. Thêm tên chuẩn và `model_id` ổn định vào `MODELS` trong `db/rules.py`.
2. Thêm mẫu vào `MODEL_PATTERNS`; đặt mẫu cụ thể trước mẫu tổng quát.
3. Thêm tên upstream vào `GATEWAY_MODELS` nếu muốn catalog sinh alias cố định.
4. Sinh lại catalog:

   ```bash
   python3 db/gen_catalog.py
   ```

5. Nạp lại dữ liệu:

   ```bash
   python3 scripts/rebuild_db.py
   ```

6. Kiểm tra model và alias:

   ```sql
   SELECT model_id, name, family, provider
   FROM dim_model
   ORDER BY model_id;

   SELECT source, raw_name, model_id
   FROM dim_model_alias
   WHERE source = 'gateway'
   ORDER BY raw_name;
   ```

## Ví dụ

Với raw model mới:

```text
anthropic/claude-4-sonnet
```

`auto_register_models()` sẽ tạo hoặc tìm:

```text
dim_model.name     = claude-4-sonnet
dim_model.provider = anthropic
dim_model.family   = anthropic
alias source       = gateway
alias raw_name     = anthropic/claude-4-sonnet
```

Sau đó cần review và bổ sung vào `db/rules.py` nếu model này phải có tên chuẩn,
family và giá được quản lý chính thức.

## Kiểm tra sau khi thay đổi

Tối thiểu nên chạy:

```bash
node --test tests/api-gateway-domain.test.js
docker compose --profile gateway config --quiet
python3 scripts/rebuild_db.py
```

Sau khi rebuild, kiểm tra log `load_gateway` để xác nhận số model tự đăng ký và
chạy audit database để phát hiện dòng Gateway còn `model_id` rỗng.
