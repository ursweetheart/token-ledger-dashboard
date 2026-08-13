# Định dạng ngày `dd/mm/yyyy` riêng cho bộ lọc khoảng thời gian

## Mục tiêu

Đổi đúng hai ô nhập ngày bắt đầu và ngày kết thúc trong bộ lọc “Khoảng thời gian” từ `mm/dd/yyyy` sang `dd/mm/yyyy`.

## Phạm vi

- Hai ô văn bản `range-start-text` và `range-end-text` hiển thị ngày theo `dd/mm/yyyy`.
- Hai ô chấp nhận dữ liệu người dùng nhập theo `dd/mm/yyyy` và tiếp tục chấp nhận ISO `yyyy-mm-dd` để tương thích với luồng hiện có.
- Placeholder, nhãn trợ năng, chú thích mã và thông báo ngày không hợp lệ được đổi sang `dd/mm/yyyy`.
- Hai ô lịch ẩn vẫn trao đổi giá trị ISO `yyyy-mm-dd` với trạng thái ứng dụng.

Không đổi định dạng ngày tại tiêu đề dashboard, dòng “Kỳ dữ liệu”, bảng tài khoản hoặc ô “Ngày nhập liệu”. Không đổi cấu trúc dữ liệu, phép lọc, preset khoảng thời gian hay nội dung CSV.

## Thiết kế

Tạo một hàm định dạng dành riêng cho bộ lọc, chuyển `yyyy-mm-dd` thành `dd/mm/yyyy`. `renderRange()` dùng hàm này thay vì hàm định dạng Mỹ dùng chung ở các khu vực khác.

Điều chỉnh `parseTypedDate()` để diễn giải ba thành phần có năm ở cuối theo thứ tự ngày, tháng, năm. Hàm vẫn kiểm tra ngày thực bằng UTC và trả về ISO; vì vậy `31/02/2026` bị từ chối, còn `09/08/2026` trả về `2026-08-09`. Toàn bộ xử lý sau `applyRangeEdge()` được giữ nguyên.

## Xử lý lỗi

Khi người dùng nhập rỗng hoặc ngày không tồn tại, khoảng thời gian hiện tại không thay đổi, hai ô được render lại từ trạng thái hợp lệ và thông báo yêu cầu nhập theo `dd/mm/yyyy` được hiển thị.

## Kiểm thử

- Xác nhận `2026-08-09` hiển thị trong bộ lọc thành `09/08/2026`.
- Xác nhận `09/08/2026` được phân tích thành `2026-08-09`.
- Xác nhận ISO `2026-08-09` vẫn được chấp nhận.
- Xác nhận ngày không tồn tại như `31/02/2026` bị từ chối.
- Xác nhận HTML của hai ô bộ lọc dùng placeholder và nhãn `dd/mm/yyyy`.
- Chạy toàn bộ bộ kiểm thử hiện có để phát hiện hồi quy.
