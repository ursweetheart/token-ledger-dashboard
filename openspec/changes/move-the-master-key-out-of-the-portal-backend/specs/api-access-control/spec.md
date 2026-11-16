## ADDED Requirements

### Requirement: Container `api` không giữ master key của Gateway

Container `api` của portal SHALL khởi động mà không cần và không mang `LITELLM_MASTER_KEY`. Cửa chặn khởi
động của `api` MUST NOT đòi master key của Gateway. Mọi thao tác cần master key (đọc/sửa hạn mức, cấp/thu
hồi khoá) SHALL do worker trên host thực hiện; `api` chỉ nói chuyện với worker, không nói thẳng với API
quản trị của Gateway.

Lý do: master key trong `api` là quyền rộng hơn mức một dashboard chỉ-đọc cần, và là đường rò khoá Google
qua `POST /config/pass_through_endpoint` (đã chứng minh trên máy dev 03/11/2026). Giữ master key ở đúng
một nơi (worker) thu hẹp bề mặt tấn công.

#### Scenario: `api` khởi động không có master key
- **WHEN** container `api` khởi động mà môi trường không đặt `LITELLM_MASTER_KEY`
- **THEN** máy chủ SHALL khởi động bình thường và phục vụ các endpoint như cũ

#### Scenario: Không có master key trong môi trường của `api`
- **WHEN** kiểm biến môi trường của container `api` đang chạy
- **THEN** SHALL không có `LITELLM_MASTER_KEY`

#### Scenario: Hạn mức vẫn tắt được trên máy dev
- **WHEN** đặt `QUOTA_DISABLED=1`
- **THEN** `api` SHALL khởi động và các đường hạn mức trả 503 như trước, không kèm master key
