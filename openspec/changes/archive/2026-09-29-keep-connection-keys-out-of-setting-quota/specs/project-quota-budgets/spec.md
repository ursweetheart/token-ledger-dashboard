## ADDED Requirements

### Requirement: Đường ghi hạn mức của dashboard không sửa key do tab Kết nối quản lý

Endpoint ghi hạn mức của dashboard (đặt thành, cộng thêm) MUST NOT thay đổi hạn mức của Virtual Key do
tab Kết nối agent cấp. Key như vậy SHALL được nhận diện bằng tiền tố tên `connection-` do worker đặt.
Phép từ chối SHALL xảy ra trước mọi lệnh gọi tới Gateway và trả mã 409 kèm lời chỉ tới tab Kết nối
agent. Danh sách hạn mức SHALL vẫn liệt kê các key này để xem.

Lý do: key do tab Kết nối cấp chỉ được sửa bằng khoá quản trị, có audit, và tab đó lưu hạn mức để hiển
thị. Một đường sửa thứ hai bằng khoá xem dashboard vừa vượt quyền vừa làm số hiển thị sai.

#### Scenario: Đặt hạn mức cho key do tab Kết nối cấp
- **WHEN** người gọi có khoá dashboard hợp lệ gửi yêu cầu đặt hạn mức cho key `connection-…`
- **THEN** hệ thống SHALL trả 409 và nêu rằng key do tab Kết nối agent quản lý
- **AND** MUST NOT gửi lệnh nào tới Gateway

#### Scenario: Cộng thêm hạn mức cho key do tab Kết nối cấp
- **WHEN** người gọi gửi yêu cầu cộng thêm hạn mức cho key `connection-…`
- **THEN** hệ thống SHALL trả 409 như trên và hạn mức trên Gateway giữ nguyên

#### Scenario: Key khác vẫn sửa được
- **WHEN** người gọi đặt hạn mức cho một key không mang tiền tố `connection-`
- **THEN** hệ thống SHALL sửa như trước change này

#### Scenario: Key do tab Kết nối cấp vẫn hiện trong danh sách
- **WHEN** người gọi đọc danh sách hạn mức
- **THEN** các key `connection-…` SHALL có mặt với hạn mức và số đã tiêu
