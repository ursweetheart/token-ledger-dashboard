## ADDED Requirements

### Requirement: Nạp agent được đăng ký bằng cấu hình Gateway
Loader SHALL dùng registry đã áp dụng để chọn policy nhận diện, đồng thời giữ legacy lookup cho agent không thuộc registry. Gateway database SHALL luôn chỉ đọc. Registration và ingestion MUST NOT yêu cầu generator, org loader, Google files hoặc app exports.

#### Scenario: Registry đã áp dụng và không có exports
- **WHEN** refresh chạy với registry hợp lệ và kết nối Gateway DB nhưng không có source files
- **THEN** agent mới SHALL có call, identity và các rollup cần thiết trên dashboard

#### Scenario: Không có schema registry ở bản DB cũ
- **WHEN** loader tương thích mới chạy với DB chưa migrate registry
- **THEN** nó SHALL duy trì legacy ingestion, không giả vờ đã áp dụng YAML và không tự migrate

### Requirement: Backfill agent mới không bị global watermark bỏ qua
Agent mới SHALL có trạng thái pending backfill. Refresh SHALL đọc toàn bộ lịch sử còn giữ từ reporting_start_date theo giờ Việt Nam cho agent đó, bất kể global watermark; agent cũ giữ incremental policy. Chỉ hoàn tất pending sau khi load, mọi rollup và heartbeat thành công. Calls trước ngày đã khai SHALL được đếm là ngoài phạm vi, không gán nhầm lý do thiếu tag.

#### Scenario: Agent mới đã có request cũ
- **WHEN** agent được đăng ký sau khi global watermark đã đi qua các calls của nó
- **THEN** initial refresh SHALL vẫn nạp mọi call hợp lệ trong phạm vi còn có ở nguồn

#### Scenario: Rollup lỗi sau khi facts đã commit
- **WHEN** cycle lỗi sau bước load và trước khi hoàn thành rollups
- **THEN** pending SHALL còn, lần thử lại SHALL không nhân đôi accounts/facts và SHALL hoàn tất rollups

#### Scenario: Chỉ có dữ liệu trước ngày bắt đầu
- **WHEN** lịch sử agent chỉ có calls trước reporting_start_date
- **THEN** refresh SHALL ghi rõ số calls ngoài phạm vi và không tạo usage trong phạm vi

#### Scenario: Gateway không kết nối được
- **WHEN** initial backfill không đọc được source DB
- **THEN** refresh SHALL báo lỗi, giữ pending và không báo nạp thành công zero rows

### Requirement: Apply và refresh không chạy chồng gây sai số
Apply và toàn cycle refresh SHALL dùng cơ chế khóa chung trong dashboard DB; direct loader SHALL tham gia cùng cơ chế. Tiến trình thứ hai SHALL chờ có giới hạn hoặc từ chối/skip rõ ràng, không chạy đồng thời hai lần dựng rollup. Replay MUST NOT tự đổi account_id/unit_id của facts lịch sử đã có.

#### Scenario: Chạy manual trong lúc service refresh đang chạy
- **WHEN** operator chạy refresh thủ công hoặc apply khi worker đang giữ khóa
- **THEN** tiến trình mới SHALL không ghi xen vào cycle đó và SHALL báo trạng thái khóa rõ ràng

#### Scenario: Replay không có request mới
- **WHEN** loader chạy lại cùng source logs và registry
- **THEN** account IDs, fact count và tổng token/tiền SHALL không đổi
