# Bảng phòng ban lấy số từ database, và không bịa số khi không tính được

## Why

Tab **Phòng ban & User** có ba con số sai. Cả ba cùng một gốc: **frontend tự dựng lại
câu trả lời mà backend đã có**, và khi không dựng nổi thì nó trả về `0` hoặc `—` thay vì
đi hỏi.

Đo trên trang thật ngày 20/08/2026, backend nối PostgreSQL:

| # | Hàng | Màn hình nói | Sự thật |
|---|---|---|---|
| 1 | Nghiên cứu thị trường | `0 ₫` cạnh **49 request · 525,9 nghìn token** | Tính được — nhưng mã nguồn đánh rơi model trên đường nên trả về 0 |
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
kỹ thuật của agent**, `api.js:164`), nên `deptUnitMetrics` rơi vào nhánh cộng từ tài
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
| Đơn vị | **108** (`ORG_UNITS`, dòng 67–177, 7.207 ký tự) | **130** (`dim_unit`) |
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

**Tiền theo phòng ban — suy từ bảng giá của Google**

Bản đầu của proposal này loại việc đó ra, với lý do *"thêm một con số ước tính mới vào màn
hình vừa bỏ được thói quen bịa số"*. **Đo xong thì lý do đó sai**, ở cả hai vế:

| Điều đã tưởng | Đo được (20/08/2026) |
|---|---|
| App không phơi model nên không tính được | `/api/usage-by-account`: **66/66** dòng Trợ lý ảo Ralli và **10/10** dòng Trợ Lý Ảo Hợp Đồng đều có `model_id` — phủ 100% |
| Nhân token với bảng giá là phỏng đoán | `ref_price` lấy từ **Cloud Billing Catalog của Google** (`price_source='google'` cho cả 10 model), không gõ tay |
| Sai số không chấp nhận được | Trên **965 dòng** có cả hai vế: tổng ước tính $291,6462 vs hoá đơn $291,9856 = **−0,1%**; lệch **trung vị mỗi dòng 0,0%**; dòng lệch nhiều nhất 6,4% |

Với sai số đó, chữ *"ước tính"* dùng sai. Đúng hơn là **suy từ bảng giá chính thức**, và nó
dựng lại gần đúng chính hoá đơn.

Nghẽn không nằm ở dữ liệu mà ở lắp ráp: `api.js` dựng đối tượng tài khoản với `m: ""` và
**cộng gộp token của mọi model lại một cục**, nên tới lúc tính tiền thì model đã bị đánh
rơi trên đường. Phải tính ở **mức dòng** rồi mới cộng.

Nếu nối lại, những ô đang hiện `—` sẽ có số. Đo thử trên kỳ 19/07–17/08:

| Nhóm cấp 1 | Token | Tiền suy ra |
|---|---:|---:|
| Chưa quy được | 4.731.585 | 164.398 ₫ |
| Toàn công ty | 3.253.324 | 83.853 ₫ |
| TT C4LED | 1.222.467 | 74.907 ₫ |
| TTDL&ĐHS | 1.021.501 | 67.661 ₫ |
| TT&TMĐT | 259.772 | 23.270 ₫ |
| **Tổng** | | **414.090 ₫** = $16,4321 |

**Hai điều kiện bắt buộc đi kèm**

1. Ô phải nói rõ số này **suy từ bảng giá**, không phải lấy từ hoá đơn.
2. Phải nói được phần tiền **không thuộc phòng ban nào** — và nói cho đúng. Ba nhóm, đo
   trên kỳ 19/07–17/08:

| | USD | |
|---|---:|---|
| Hoá đơn của kỳ, **quy được** về một phòng ban | **$15,1333** | **24,2%** — toàn bộ là Trợ Lý Ảo Hợp Đồng |
| Hoá đơn của kỳ, **không quy được** | $47,5109 | 75,8% — đi qua hoá đơn Google, nơi không ghi ai gọi |
| | **$62,6442** | tổng hoá đơn |
| Suy ra cho Trợ lý ảo Ralli | +$1,2988 | **nằm NGOÀI hoá đơn** — `tla-ralli` chưa nối Google Billing nên không có dòng hoá đơn nào |

Cộng mọi phòng ban trên màn hình được **$16,4321**, và con số đó **không so thẳng được**
với $62,6442: $1,2988 trong đó thuộc Trợ lý ảo Ralli, agent không phát sinh hoá đơn.
Đây là lưu lượng thật, chi phí thật, nhưng vô hình với tổng hoá đơn — và phép suy từ bảng
giá là **cách duy nhất** nhìn thấy nó.

*(Bản đầu của proposal ghi "26,2% / 73,8%" bằng cách chia $16,43 cho $62,64. Sai: tử số
chứa một khoản không nằm trong mẫu số — đúng loại lỗi mà change này đang sửa ở tỷ lệ áp
dụng.)*

Cột này vì vậy trả lời câu **hẹp hơn** người ta tưởng: *"phần lưu lượng có ghi được người
dùng của phòng ban này đáng giá bao nhiêu"* — không phải *"phòng ban này tiêu bao nhiêu
của công ty"*.

**KHÔNG làm trong change này**

- Đụng vào `backend/`, `db/`, `scripts/`. Cả ba lỗi đều nằm ở frontend; backend đã đúng ở
  cả ba ca. Phép suy tiền cũng làm được hoàn toàn ở frontend, vì `/api/usage-by-account`
  đã có `model_id` và `/api/catalog` đã có đơn giá.

## Impact

| | |
|---|---|
| **Specs** | `department-metric-provenance` (mới) · `single-source-dashboard-data` (mở rộng sang cây tổ chức) |
| **Code** | `web/js/app.js` · `web/js/api.js` |
| **Không đụng** | `backend/` · `db/` · `scripts/` — không rebuild database |
| **Rủi ro** | Cây tổ chức là lõi hiển thị của **cả hai** tab Phòng ban và Agents. Sai một bước thì mọi hàng đổi cùng lúc |
| **Cách quay lui** | Từng bước một commit; `ORG_UNITS` chỉ bị xoá ở bước cuối, sau khi đối chiếu 108 ↔ 130 đã sạch |
