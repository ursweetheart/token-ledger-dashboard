# Bảng phòng ban lấy số từ database, và không bịa số khi không tính được

## Why

Tab **Phòng ban & User** có ba con số sai. Cả ba cùng một gốc: **frontend tự dựng lại
câu trả lời mà backend đã có**, và khi không dựng nổi thì nó trả về `0` hoặc `—` thay vì
đi hỏi.

Đo trên trang thật ngày 20/08/2026, backend nối PostgreSQL:

| # | Hàng | Màn hình nói | Sự thật |
|---|---|---|---|
| 1 | Nghiên cứu thị trường | `0 ₫` cạnh **49 request · 525,9 nghìn token** | Không tính được, không phải bằng không |
| 2 | Chưa quy được | `3/1 · 300%` | Tỷ lệ áp dụng không thể vượt 100% |
| 3 | Đơn vị sử dụng Sale Agent | `—` user, cạnh **14.264 request · 35,7 triệu token** | Đúng 1 tài khoản dịch vụ, đang hoạt động |

Ba con số này khác nhau về mức độ nguy hiểm. **(1) và (2) là khẳng định sai** — màn hình
nói một điều không đúng. **(3) là im lặng** — màn hình nói "tôi không biết", trung thực
nhưng thiếu.

### Vì sao (1) xảy ra

Tiền chỉ tồn tại ở hoá đơn Google, mà hoá đơn **tính theo project và không ghi ai gọi**.
Nên `/api/usage-by-account` không có cột `cost_usd`, và đó là đúng chứ không phải thiếu
sót — cùng một giới hạn đã tạo ra con số 1,5% không quy được về người.

Phòng ban thật không có dòng usage nào (mỗi dòng `/api/usage` nhận phòng ban là **đơn vị
kỹ thuật của agent**, `api.js:163`), nên `deptUnitMetrics` rơi vào nhánh cộng từ tài
khoản. Ở đó `cost(u)` cần `u.cost` (không có) hoặc `state.pricing[u.m]` (`u.m` là chuỗi
rỗng) — không đường nào ra số, và hàm **trả về `0`**.

Phép thử đã chạy: nếu chẩn đoán đúng thì mọi hàng có tiền phải là đơn vị kỹ thuật, mọi
phòng ban thật phải `0 ₫`. Đối chiếu **khớp 9/9 hàng**, không ngoại lệ.

### Vì sao (2) xảy ra

Tử số và mẫu số đếm hai tập khác nhau:

```
mẫu số   DEPT_PROVISIONED   lọc `in_directory && !is_shared`   -> 1
tử số    activeCount        KHÔNG lọc gì                       -> 3     = 300%
```

`backend/store.py` `adoption()` **không mắc lỗi này** — nó tách hẳn `outside_directory`
ra cột riêng thay vì cộng vào tử số. Và `scripts/audit_db.py` có phép kiểm *"Ty le ap
dung khong vuot 100%"* đang **đạt**, vì nó soi database chứ không soi trình duyệt.

### Vì sao (3) xảy ra — và vì sao nó lớn hơn hai cái trên

`/api/adoption` **đã trả về đúng đáp án** cho 6 agent một-người-dùng: `kind='service'`,
`provisioned=1`, `active=1` nếu có chạy. Frontend không dùng con số đó, vì nó không biết
hàng nào là đơn vị kỹ thuật.

Nó không biết vì **cây tổ chức vẫn gõ cứng trong `app.js`**:

| | Gõ cứng trong `web/js/app.js` | Trong database |
|---|---|---|
| Đơn vị | **108** (`ORG_UNITS`, dòng 67–176, 7.207 ký tự) | **130** (`dim_unit`) |
| Phân loại kỹ thuật / thật | *(không có)* | `is_technical`: 8 / 122 |
| Bảng đổi tên viết tắt | **33** mục `UNIT_ALIASES` gõ tay | *(không cần)* |

`/api/catalog` **đã trả đủ** `unit_id`, `agent_id`, `name`, `parent_id`, `level`, `path`,
`is_technical` — nhưng `web/js/api.js` không chuyển ra ngoài, chỉ dùng nội bộ để tra đơn
vị gốc của agent (`primaryUnit`).

Đây là **phần còn sót của change `serve-dashboard-from-database-only`** (17/08). Change đó
bỏ `SEED_DAYS` 268 KB và bảng giá, nhưng bỏ quên cây tổ chức. Hệ quả dây chuyền: vì không
có `unit_id` từ database, frontend phải khớp phòng ban bằng **chuỗi tên**, và 33 alias tồn
tại chỉ để hoà giải việc đó.

## What Changes

**Đã làm — commit `0e11c5a` (20/08/2026)**

- `costOrNull()` phân biệt *"đã đo, bằng 0"* với *"không tính được"*; `cost()` giữ nguyên
  hợp đồng trả số nên mọi phép cộng đang có không đổi hành vi
- Đơn vị **không có lưu lượng** vẫn hiện `0 ₫` — ở đó số 0 là đáp án đúng
- Đơn vị **có lưu lượng mà không tính được tiền** hiện `—` kèm tooltip nói lý do
- Tử số tỷ lệ áp dụng lọc cùng tập với mẫu số; số tài khoản ngoài danh bạ đưa vào tooltip
  thay vì cộng vào tử số

**Còn lại — phạm vi chính của change này**

- `web/js/api.js` chuyển `catalog.units` ra ngoài, giữ nguyên `unit_id` và `is_technical`
- `web/js/app.js` bỏ `ORG_UNITS` (108 dòng gõ cứng) và `UNIT_ALIASES` (33 mục), dựng cây
  từ database
- Ghép usage vào đơn vị bằng `unit_id`, không bằng chuỗi tên
- Hàng đơn vị kỹ thuật lấy tỷ lệ áp dụng từ `/api/adoption` thay vì tự tính
- Đối chiếu 108 ↔ 130 đơn vị trước khi thay: tên nào chỉ có một bên, alias nào đang che
  một lệch thật

**KHÔNG làm trong change này**

- Ước tính tiền theo phòng ban từ bảng giá. Làm được (mỗi dòng `/api/usage-by-account` có
  `model_id`), nhưng đó là **thêm một con số ước tính mới**, phải ghi nhãn, và là quyết
  định riêng — không nên đi kèm một change đang sửa lỗi bịa số.
- Đụng vào `backend/`. Cả ba lỗi đều nằm ở frontend; backend đã đúng ở cả ba ca.

## Impact

| | |
|---|---|
| **Specs** | `department-metric-provenance` (mới) · `single-source-dashboard-data` (mở rộng sang cây tổ chức) |
| **Code** | `web/js/app.js` · `web/js/api.js` |
| **Không đụng** | `backend/` · `db/` · `scripts/` — không rebuild database |
| **Rủi ro** | Cây tổ chức là lõi hiển thị của **cả hai** tab Phòng ban và Agents. Sai một bước thì mọi hàng đổi cùng lúc |
| **Cách quay lui** | Từng bước một commit; `ORG_UNITS` chỉ bị xoá ở bước cuối, sau khi đối chiếu 108 ↔ 130 đã sạch |
