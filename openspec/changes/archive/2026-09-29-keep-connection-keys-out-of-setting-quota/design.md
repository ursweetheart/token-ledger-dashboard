## Context

- Hai endpoint ghi hạn mức của dashboard (`POST /api/quota`, `POST /api/quota/top-up`) đều gọi
  `gateway.set_quota` (`backend/gateway.py:225`). Ngoài hai endpoint này, chỉ test gọi hàm đó.
- Worker đặt tên mọi key nó cấp theo mẫu `connection-<mã thao tác>` (`connection_worker.py:392`, và
  thấy trên màn hình: `connection-750ea85b-…`). Metadata của key chỉ có `tags` và `quota_usd`
  (`connection_worker.py:549-551`) — không có dấu "do ai quản lý".
- API dashboard chạy bằng vai chỉ-đọc `api_readonly`; chú thích `main.py:436` chốt "không vai mới,
  không GRANT mới".
- Tab Setting đã xử lý lỗi từ backend: hiện "Không lưu được: <lý do>", giữ nguyên số cũ.

## Goals / Non-Goals

**Goals:**
- Chỉ còn một đường sửa hạn mức cho key do tab Kết nối cấp: đường có khoá quản trị và audit.
- Chặn ở backend — nơi là ranh giới quyền thật.

**Non-Goals:**
- Không ẩn hay tắt nút trong tab Setting (quy ước: không sửa frontend ngoài tab Kết nối).
- Không đổi quyết định "một khoá dùng chung" cho các key khác.
- Không cho tab Kết nối đọc hạn mức từ Gateway (không cần khi chỉ còn một nơi sửa).

## Decisions

**1. Nhận diện key được quản lý bằng tiền tố tên `connection-`.**
Phương án khác và vì sao bỏ:
- *Đọc bảng `gateway_connection_key`*: phải cấp thêm GRANT cho `api_readonly` — trái quy ước.
- *Thêm dấu vào metadata khi cấp key*: key đã cấp (ví dụ key của `dms-tap`) không có dấu, phải chạy
  migrate metadata trên Gateway thật.
- *Theo tag*: tag là agent, không nói ai quản lý key; agent legacy cũng có tag.
Tiền tố do chính worker đặt, không ai nhập tay. Chú thích `main.py:498-505` cảnh báo "tên khoá chỉ là
nhãn người đặt" — đúng cho việc **quy tiền về agent**; ở đây câu hỏi là "key này do ai tạo", và tên do
worker sinh trả lời được câu đó. Sai lệch nếu có là về phía an toàn: ai tự đặt tay một key tên
`connection-x` thì key đó bị khoá ở Setting, không bị mở ra.

**2. Chặn trong `gateway.set_quota`, không chặn trong từng endpoint.**
Một chỗ phủ cả hai endpoint và mọi nơi gọi sau này. Hàm ném một lỗi riêng (không dùng `GatewayError`,
vì lỗi đó đang được đổi thành 502 "Gateway hỏng"); endpoint đổi lỗi riêng thành 409.
Phép kiểm chạy **trước** mọi lệnh gọi Gateway, nên không có đọc-rồi-ghi dở dang.

**3. Mã 409, không phải 403.**
403 nghĩa là "người gọi thiếu quyền" — người gọi có khoá hợp lệ. 409 nghĩa là "trạng thái tài nguyên
không cho thao tác này", đúng với "key này thuộc nơi khác quản lý". Câu lỗi chỉ đường: tab Kết nối agent.

## Risks / Trade-offs

- [Mất nút chặn khẩn cấp không cần khoá quản trị] → Có chủ đích: spec tab Kết nối yêu cầu đúng điều
  này. Ghi vào tài liệu vận hành, kèm cách chặn thay thế (hạn mức 0 hoặc thu hồi ở tab Kết nối).
- [Worker đổi mẫu tên key sau này] → Thêm ca kiểm ở bộ test của worker: key cấp ra phải bắt đầu bằng
  `connection-`. Đổi mẫu tên thì test đỏ, không lặng lẽ mở lại lỗ.
- [Key `connection-…` cấp trước ngày sửa đã bị tab Setting đổi hạn mức] → Số trong
  `gateway_connection_key` có thể đã lệch. Việc kiểm: so hạn mức trên Gateway với bảng cho từng key
  đang hoạt động; lệch thì đặt lại qua tab Kết nối (có audit), không sửa tay database.
