## Context

Luồng hiện tại có ba nút: "Lưu bản nháp" → "4. Xem thay đổi" → "5. Áp dụng".

- Lưu: `POST /api/gateway-connections` với nội dung form. Mỗi lần lưu **tăng revision và ghi một dòng
  audit** (`backend/connection_store.py:68-72`), kể cả khi nội dung giống hệt.
- Xem trước: `POST /{code}/preview` chỉ gửi `expected_revision`. Worker đọc bản nháp **đã lưu** và trả
  toàn bộ cấu hình đích, không có phần so sánh.
- Hồ sơ trả về từ `GET /{code}` có cả `draft` lẫn `applied` (bản nháp đã áp dụng lần cuối, ghi ở
  `connection_worker.py:492`).
- `bind()` bọc mọi nút: tắt khi đang chạy, `finally` bật lại (trừ Áp dụng khi chưa có preview).

## Goals / Non-Goals

**Goals:**
- Bản xem trước luôn khớp với nội dung form lúc bấm nút.
- Người dùng đọc được bấm Áp dụng sẽ đổi gì, không phải đọc JSON.
- Không sinh revision/audit thừa khi form không đổi.
- Nút phản ánh đúng trạng thái; mọi thao tác có câu báo kết quả.

**Non-Goals:**
- Không đổi API backend.
- Không so sánh các tuyến của agent khác hay file cấu hình bị sửa tay: việc đó là của "Xem thay đổi
  ngoài UI" (reconcile).
- Không cảnh báo khi đổi hồ sơ trong ô chọn mà form còn thay đổi chưa lưu.

## Decisions

**1. Tự lưu trong nút Xem thay đổi, thay vì khoá nút khi form bẩn.**
Hai cách đều chặn được lỗi A. Tự lưu thì bớt được một nút và một bước bấm; khoá nút thì giữ đủ ba nút
và bắt người dùng nhớ thứ tự. Xem trước không ghi gì lên Gateway, nên gộp lưu vào đó không làm mất khả
năng "lưu nháp mà chưa triển khai".

**2. Chỉ lưu khi form bẩn, dùng một cờ `dirty`.**
Không so nội dung form với bản đã lưu (phải chuẩn hoá kiểu số, ngày, thứ tự model — dễ sai). Cờ bật khi
có sự kiện `input` trong form, khi "Thêm model", "Bỏ model", và khi "Lưu key và lấy tham chiếu" ghi
vào ô `secret_ref` bằng code (ghi bằng code không phát sự kiện `input`). Cờ tắt trong `fill()` và sau
khi lưu thành công. Agent mới (`selected == null`) luôn lưu.

**3. Tự kiểm form trước khi lưu.**
Nút submit cũ nhờ trình duyệt kiểm `required`/`pattern`. Nút "Xem thay đổi" là `type="button"` nên
phải gọi `form.reportValidity()`; không hợp lệ thì dừng, không gửi gì.

**4. Nhấn Enter trong form = bấm Xem thay đổi.**
Bỏ nút submit thì sự kiện `submit` của form chạy cùng luồng lưu-rồi-xem-trước.

**5. Lưu lỗi thì dừng hẳn.**
Lưu lỗi (409 revision đổi, 400 dữ liệu sai) → hiện lỗi, giữ `dirty = true`, không gọi preview, Áp dụng
vẫn tắt. Lưu được mà preview lỗi (worker tắt, drift) → bản nháp đã lưu, `dirty = false`, hiện lỗi
preview, Áp dụng vẫn tắt.

**6. Tóm tắt thay đổi làm ở giao diện, so `preview.profile` với `selected.applied`.**
Không sửa worker: dữ liệu đã có đủ. So từng trường mà người dùng nhập được: tên, đang hoạt động, tham
chiếu khoá, danh sách model (alias → upstream), RPM, TPM, chế độ khi hết hạn mức, ngân sách. Ba kết quả:
`applied == null` → "Chưa áp dụng lần nào — toàn bộ cấu hình trên là mới"; không có trường nào khác →
"Không có thay đổi so với bản đang chạy"; ngược lại → mỗi trường một dòng `Tên: cũ → mới`. Tóm tắt đặt
trên JSON; JSON giữ nguyên để kiểm chi tiết. Giới hạn đã biết: tóm tắt chỉ nói về hồ sơ của agent này,
không nói về thay đổi ngoài UI — ghi rõ câu đó ngay dưới tóm tắt.

Phương án bỏ: cho worker trả `diff`. Đúng hơn về lâu dài (thấy cả tuyến), nhưng phải sửa worker và
test backend cho một thứ giao diện tự làm được.

**7. `bind()` hỏi trạng thái thay vì bật lại mù.**
`finally` đặt `disabled` theo một hàm trạng thái: Áp dụng cần `preview`, Chấp nhận baseline cần
`drift`. Các nút khác bật lại như cũ.

**8. `autocomplete="new-password"` cho ba ô mật khẩu.**
Chrome bỏ qua `off` với ô mật khẩu nhưng tôn trọng `new-password` (không tự điền giá trị đã lưu).
Không thêm thư viện hay mẹo ẩn ô.

## Risks / Trade-offs

- [Người dùng mất cách "lưu mà không xem trước"] → Xem trước không có tác dụng phụ; nếu preview lỗi thì
  bản nháp vẫn đã lưu (quyết định 5).
- [Cờ `dirty` sót một đường ghi form bằng code] → Liệt kê đủ ở quyết định 2; ca kiểm dùng "Lưu key và
  lấy tham chiếu" để bắt chỗ dễ sót nhất.
- [Tóm tắt bỏ sót trường mới thêm vào hồ sơ sau này] → Hàm so sánh duyệt theo danh sách trường có tên;
  thêm ca kiểm "mọi khoá của `draft` đều có trong danh sách" để trường mới làm test đỏ.
- [Chrome vẫn gợi ý mật khẩu đã lưu khi bấm vào ô] → Chấp nhận; mục tiêu là không tự điền sẵn.
