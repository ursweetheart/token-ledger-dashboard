# single-source-dashboard-data

## MODIFIED Requirements

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
tên hiển thị**, và 33 alias tồn tại chỉ để hoà giải việc đó. Ghép bằng chuỗi hiển thị sẽ
gãy khi ai đó sửa một nhãn tiếng Việt — và gãy im lặng, vì usage không tìm được đơn vị sẽ
rơi vào một đơn vị tự sinh chứ không báo lỗi.

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
- **AND** không cần bảng alias nào để hoà giải cách viết tắt

#### Scenario: Đơn vị trong database mà không ghép được thì phải kêu

- **WHEN** một dòng usage mang `unit_id` không có trong danh mục đơn vị
- **THEN** phải có dấu hiệu nhìn thấy được, không được lặng lẽ gom vào một đơn vị tự sinh

## ADDED Requirements

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
