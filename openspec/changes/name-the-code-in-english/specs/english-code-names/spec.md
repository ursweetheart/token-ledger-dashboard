## ADDED Requirements

### Requirement: Tên tệp tool và script phải là tiếng Anh
Mọi tệp `.py` và `.sh` trong `backend/`, `db/`, `scripts/`, `tools/`, `tests/` SHALL có tên tiếng Anh.
Thư mục `db/migrations/` MUST được loại khỏi yêu cầu này.

Lý do: người lập trình phải đoán được việc một tệp làm từ tên của nó. Migration đứng ngoài vì mã phiên bản
chứa trong tên đã được ghi vào bảng `alembic_version` của database.

#### Scenario: Thêm một tool mới đặt tên tiếng Việt
- **WHEN** một tệp như `tools/kiem_tra_moi.py` được thêm vào
- **THEN** phép canh SHALL báo hỏng và nêu tệp cùng mảnh tên bắt được

#### Scenario: Migration mới đặt tên tiếng Việt
- **WHEN** một tệp mới được thêm vào `db/migrations/versions/`
- **THEN** phép canh MUST NOT xét tên tệp đó

### Requirement: Cờ dòng lệnh phải là tiếng Anh
Mọi cờ khai bằng `add_argument` trong phạm vi quét SHALL là tiếng Anh. Khi một cờ đổi tên, mọi chỗ gọi
cờ đó trong code SHALL được sửa cùng commit.

Lý do: ngày 15/09/2026, cờ `--goc` không đoán được nghĩa, và `--chi-gateway` đang được
`scripts/refresh_gateway.py` gọi từ dịch vụ chạy tự động.

#### Scenario: Chạy script bằng cờ cũ
- **WHEN** người dùng chạy một script bằng cờ tiếng Việt đã bị đổi
- **THEN** script SHALL thoát với lỗi `unrecognized arguments`, không chạy tiếp với giá trị mặc định

#### Scenario: Cờ cũ là tiền tố của một cờ mới
- **WHEN** người dùng chạy `scripts/merge_monitoring.py --ra X`, mà `--ra` đã đổi thành `--out` và tệp có
  cờ mới `--raw`
- **THEN** script SHALL thoát với `unrecognized arguments`
- **AND** MUST NOT hiểu `--ra` là viết tắt của `--raw`

#### Scenario: Parser bật viết tắt
- **WHEN** một `ArgumentParser` trong phạm vi quét không có `allow_abbrev=False`
- **THEN** phép canh SHALL báo hỏng

#### Scenario: Dịch vụ tự động gọi cờ đã đổi
- **WHEN** `scripts/refresh_gateway.py` gọi `db/build_performance.py`
- **THEN** nó SHALL dùng tên cờ mới, và `--help` của cả hai tệp SHALL chạy được

### Requirement: Định danh và chuỗi người lập trình đọc phải là tiếng Anh
Tên hàm, lớp, tham số, biến, key trong dict, và chuỗi in ra màn hình, log, thông báo lỗi, `help` SHALL là
tiếng Anh. Comment và docstring MAY là tiếng Việt.

#### Scenario: Comment và docstring tiếng Việt
- **WHEN** một tệp có comment hoặc docstring tiếng Việt có dấu
- **THEN** phép canh MUST NOT báo hỏng

#### Scenario: Comment SQL tiếng Việt bên trong chuỗi SQL
- **WHEN** một chuỗi SQL có dòng `-- chú thích có dấu`
- **THEN** phép canh MUST NOT báo hỏng phần comment đó
- **AND** SHALL vẫn báo hỏng nếu phần SQL còn lại có chữ tiếng Việt

#### Scenario: Thông báo lỗi tiếng Việt
- **WHEN** code có `raise ValueError("Thiếu tệp")` hoặc `print("khong tim thay tep")`
- **THEN** phép canh SHALL báo hỏng và nêu tệp, dòng, loại vi phạm

#### Scenario: Đổi chuỗi không được làm mất số liệu
- **WHEN** một dòng output được dịch sang tiếng Anh
- **THEN** mọi con số và tên dữ liệu trong dòng đó SHALL còn nguyên, và mã thoát SHALL không đổi

### Requirement: Ngoại lệ phải đánh dấu tại dòng, kèm lý do
Chuỗi tiếng Việt được giữ SHALL mang dấu `# vi-ok: <lý do>` trên cùng dòng. Dấu không có lý do MUST bị
coi là vi phạm. Phép canh MUST NOT có danh sách tệp được miễn trừ.

Lý do: có ba loại chuỗi phải giữ — câu hiện lên dashboard cho người dùng Việt, tên tệp/cột dữ liệu trên đĩa,
và giá trị đã ghi vào dữ liệu. Miễn trừ cả tệp là mở chỗ mù vĩnh viễn cho mọi dòng khác trong tệp đó.

#### Scenario: Câu cảnh báo hiện lên dashboard
- **WHEN** `backend/store.py` trả một `message` tiếng Việt cho giao diện
- **AND** dòng đó có `# vi-ok: dashboard text`
- **THEN** phép canh SHALL cho qua dòng đó

#### Scenario: Dấu ngoại lệ không nêu lý do
- **WHEN** một dòng có `# vi-ok:` mà không có chữ nào sau dấu hai chấm
- **THEN** phép canh SHALL báo hỏng

### Requirement: CI phải chặn tiếng Việt quay lại code
Nhóm `guards` SHALL chạy phép canh trên mỗi lần đẩy code, chỉ bằng thư viện chuẩn của Python. Phép canh
SHALL được làm đỏ có chủ ý trên CI ít nhất một lần trước khi coi là xong.

#### Scenario: Đẩy code có cờ tiếng Việt
- **WHEN** một commit thêm `add_argument("--bo-qua")`
- **THEN** nhóm `guards` SHALL đỏ

#### Scenario: Phép canh đã từng đỏ thật
- **WHEN** change này được nghiệm thu
- **THEN** SHALL có mã một lần chạy CI mà phép canh báo hỏng có chủ ý

### Requirement: Đổi tên không được làm gãy đường chạy tự động
Mọi đường chạy tự động (`ledger-refresh`, `scripts/update_dashboard.py`, `scripts/rebuild_db.py`) SHALL
còn chạy được sau khi đổi tên, và SHALL được kiểm mà không ghi database hay gọi API thật.

#### Scenario: Script gọi script khác theo tên tệp
- **WHEN** `scripts/update_dashboard.py` hoặc `scripts/rebuild_db.py` gọi một tệp đã đổi tên
- **THEN** đường dẫn trong lời gọi SHALL là tên mới
- **AND** tìm tên cũ trong code SHALL ra 0 kết quả
