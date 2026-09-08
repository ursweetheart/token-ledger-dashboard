# single-source-dashboard-data Specification

## Purpose
TBD - created by archiving change serve-dashboard-from-database-only. Update Purpose after archive.
## Requirements
### Requirement: Frontend không chứa số liệu

Mã nguồn frontend SHALL không chứa dữ liệu số liệu nào — kể cả làm dữ liệu dự phòng, dữ
liệu mẫu, hay dữ liệu để xem offline. Mọi con số hiện trên dashboard SHALL đến từ database
qua API.

Quy tắc này bao trùm cả những thứ dễ tưởng là "cấu hình" chứ không phải "số liệu": bảng
giá model, hạn mức ngân sách theo agent, danh sách người dùng, **và cây tổ chức đơn vị**.
Cả bốn đều đã có bảng trong database (`ref_price`, `ref_budget`, `dim_user`/`account`,
`dim_unit`), nên giữ bản gõ tay ở frontend là tạo ra nguồn thứ hai cho cùng một sự thật.

**Bổ sung 20/08/2026 — cây tổ chức.** Change `serve-dashboard-from-database-only` bỏ được
`SEED_DAYS`, bảng giá và danh bạ, nhưng bỏ sót cây đơn vị:

| | Gõ cứng trong `web/js/app.js` | Trong database |
|---|---|---|
| Đơn vị | **108** (`ORG_UNITS`, dòng 67–177) | **130** (`dim_unit`) |
| Phân loại kỹ thuật / thật | *(không có)* | `is_technical`: 8 / 122 |
| Bảng đổi tên viết tắt | **33** mục `UNIT_ALIASES` gõ tay | *(không cần)* |

`/api/catalog` đã trả đủ `unit_id`, `agent_id`, `name`, `parent_id`, `level`, `path`,
`is_technical`; `web/js/api.js` chỉ dùng nội bộ để tra đơn vị gốc của agent và không
chuyển ra ngoài.

Hệ quả dây chuyền: không có `unit_id` thì frontend phải ghép usage vào đơn vị bằng **chuỗi
tên hiển thị**. Ghép bằng chuỗi hiển thị sẽ gãy khi ai đó sửa một nhãn tiếng Việt — và gãy
im lặng, vì usage không tìm được đơn vị sẽ rơi vào một đơn vị tự sinh (`app.js:591`) chứ
không báo lỗi.

> ### ⏸️ Các yêu cầu về cây tổ chức đang HOÃN — chưa được thực hiện
>
> Đo ngày 20/08/2026 cho thấy `dim_unit` là **hai cây riêng** — 20 đơn vị với **4 gốc**
> của Trợ Lý Ảo Hợp Đồng, 102 đơn vị với 1 gốc của Trợ lý ảo Ralli — và **8 tên tồn tại
> ở cả hai**. `ORG_UNITS` là một cây đã gộp sẵn bằng tay.
>
> Nên `UNIT_ALIASES` làm **hai** việc: hoà giải viết tắt (`unit_id` thay được) **và gộp
> hai cây thành một cái nhìn công ty** (`unit_id` KHÔNG thay được — hai cây không có khoá
> chung). Thay thẳng sẽ cho ra hai cây rời với 8 nhánh trùng tên.
>
> Việc gộp cây là câu hỏi **nghiệp vụ**, cần người quyết. Xem `design.md` §2.3.

Các scenario dưới đây mô tả trạng thái đích, **chưa phải trạng thái hiện tại**.

#### Scenario: Không còn khối dữ liệu nào trong mã frontend

- **WHEN** tìm trong `web/js/` các định danh `SEED_DAYS`, `buildJuneExcelWeeks`,
  `RALLI_USERS`, `basePricing`, `AGENT_MONTHLY_BUDGETS`, **`ORG_UNITS`**,
  **`UNIT_ALIASES`**
- **THEN** không định danh nào còn mang dữ liệu gán cứng

#### Scenario: Cây đơn vị dựng từ database

- **WHEN** dashboard nạp xong danh mục
- **THEN** cây đơn vị SHALL dựng từ `/api/catalog` field `units`
- **AND** mỗi nút SHALL giữ `unit_id` và `is_technical` nguyên như database trả về
- **AND** số đơn vị hiện ra SHALL khớp số dòng `dim_unit` sau khi trừ các đơn vị bị lọc
  theo quy tắc hiển thị

#### Scenario: Usage ghép vào đơn vị bằng khoá, không bằng tên

- **WHEN** một dòng usage cần được quy về một đơn vị
- **THEN** phép ghép SHALL dùng `unit_id`
- **AND** MUST NOT dùng chuỗi tên hiển thị của phòng ban
- **AND** không cần bảng alias nào để hoà giải **cách viết tắt**

Lưu ý: việc này KHÔNG bỏ được nhu cầu **gộp hai cây tổ chức**. Đó là một ánh xạ riêng,
phải có nguồn riêng — xem khung ⏸️ ở trên.

#### Scenario: Đơn vị trong database mà không ghép được thì phải kêu

- **WHEN** một dòng usage mang `unit_id` không có trong danh mục đơn vị
- **THEN** phải có dấu hiệu nhìn thấy được, không được lặng lẽ gom vào một đơn vị tự sinh

### Requirement: Cache của trình duyệt không được trở thành nguồn số liệu cũ

Dashboard MUST NOT ghi số liệu lấy từ backend vào `localStorage`. `localStorage` SHALL chỉ
giữ lựa chọn của người dùng — tab đang mở, giao diện sáng/tối, khoảng ngày đang chọn.

Đây là vector dữ liệu cũ thứ hai, độc lập với dữ liệu nhúng trong mã. Đường ống cũ đã phải
bump số phiên bản trong khoá `localStorage` mỗi lần cập nhật, với lý do ghi thẳng trong
`scripts/va_app_js.py`: *"otherwise a returning browser keeps serving the old data out of
localStorage"*. Khi số liệu không còn được ghi vào đó, việc bump khoá thôi không còn cần
thiết.

#### Scenario: Trình duyệt đã từng mở dashboard không hiện số cũ

- **WHEN** mở dashboard, để nó nạp xong, rồi tải lại trang với backend đã tắt
- **THEN** dashboard MUST NOT hiện số liệu của lần nạp trước
- **AND** nó báo không nối được backend

#### Scenario: Lựa chọn của người dùng vẫn được giữ

- **WHEN** đổi sang tab khác, đổi giao diện sáng/tối, chọn một khoảng ngày, rồi tải lại
  trang
- **THEN** cả ba lựa chọn được giữ nguyên
- **AND** số liệu được nạp lại từ backend, không lấy từ `localStorage`

### Requirement: Đường ống không còn bước vá dữ liệu vào frontend

Đường ống cập nhật SHALL không có bước nào ghi vào `web/js/`. Sinh dữ liệu dự phòng và vá
nó vào `app.js` SHALL bị bỏ hoàn toàn, cùng các script chỉ tồn tại để làm việc đó.

#### Scenario: Đường ống không ghi vào thư mục frontend

- **WHEN** đọc toàn bộ lời gọi lệnh trong `scripts/update_dashboard.py`
- **THEN** không lời gọi nào sinh hoặc sửa file trong `web/`
- **AND** số bước là 9, và nhãn các bước được đánh số lại liên tục

#### Scenario: Script chỉ phục vụ việc vá đã bị xoá

- **WHEN** liệt kê `scripts/`
- **THEN** không còn `sinh_du_lieu_dashboard.py` và `va_app_js.py`
- **AND** không còn ảnh chụp `web/js/app.js.bak`

#### Scenario: Nạp trọn frontend không còn tham chiếu treo

- **WHEN** chạy `node --test tests/date-range-filter.test.js`
- **THEN** cả 6 phép kiểm đạt
- **AND** việc nạp `app.js` trong `vm` không ném lỗi tham chiếu tới định danh đã xoá

### Requirement: Đối chiếu cây cũ và cây mới trước khi thay

Trước khi bỏ `ORG_UNITS`, SHALL sinh ra bảng đối chiếu giữa 108 đơn vị gõ cứng và 130 dòng
`dim_unit`, và bảng đó SHALL phân loại được ba kiểu lệch.

Lý do: chênh 22 dòng không nói được gì cho tới khi biết chúng nằm ở đâu. Kiểu lệch thứ ba
là kiểu nguy hiểm nhất vì nó không làm mọc thêm hay mất đi hàng nào — nó chỉ chuyển số
sang nhánh khác, nên tổng toàn công ty vẫn đúng trong khi số của từng phòng ban đã đổi.

#### Scenario: Ba kiểu lệch được liệt kê riêng

- **WHEN** chạy đối chiếu
- **THEN** kết quả SHALL tách riêng: đơn vị chỉ có trong database · đơn vị chỉ có trong
  `ORG_UNITS` · đơn vị có ở cả hai nhưng **khác cha hoặc khác cấp**
- **AND** mỗi mục SHALL kèm tên và khoá để tra lại được

#### Scenario: Bốn mốc phải khớp trước và sau khi thay

- **WHEN** đã thay cây tổ chức
- **THEN** tổng token và tiền toàn kỳ SHALL không đổi
- **AND** tổng của từng phòng ban cấp 1 SHALL không đổi, hoặc mọi chênh lệch SHALL truy
  được về một dòng trong bảng đối chiếu
- **AND** số hàng đơn vị và số hàng tài khoản SHALL khớp con số đã ghi trước khi thay
- **AND** không ô tỷ lệ áp dụng nào SHALL vượt 100%
