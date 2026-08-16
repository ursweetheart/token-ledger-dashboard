AGENT ANALYTICS · TOKEN LEDGER — Bảng điều khiển chi phí AI agent
==================================================================

CÁCH MỞ
-------
Bấm đúp vào file  index.html  → mở bằng trình duyệt (Chrome / Edge).
Không cần cài đặt, không cần internet (Chart.js đã đóng gói sẵn trong folder).

FILE TRONG FOLDER
-----------------
  index.html          Giao diện dashboard
  app.js              Toàn bộ logic tính toán (nhập liệu → chỉ số → biểu đồ)
  dashboard.css       Bộ giao diện dùng chung của công ty
  chart.umd.min.js    Thư viện vẽ biểu đồ (bản offline)

NHẬP LIỆU (theo NGÀY)
---------------------
1. Bấm  ✎ Dữ liệu nguồn.
2. Chọn  Ngày nhập liệu  (ô lịch).
3. Nhập token/request... cho từng agent trong ngày đó (bấm "+ Thêm dòng" nếu cần).
4. Bấm  💾 Lưu ngày này.  → dashboard tính lại theo dữ liệu vừa lưu.
5. Muốn xoá dữ liệu 1 ngày: chọn ngày đó rồi bấm  🗑 Xoá ngày.

CẤU HÌNH GIÁ
------------
Bấm  ⚙ Cấu hình giá  → sửa đơn giá input/output theo model → bấm  💾 Lưu bảng giá.

KHOẢNG THỜI GIAN
----------------
Dùng ô "Khoảng thời gian" (Từ → Đến) hoặc nút 7/30/90 ngày.
Dashboard cộng dữ liệu MỌI NGÀY đã lưu nằm trong khoảng đó.

GIAO DIỆN SÁNG / TỐI
--------------------
Bấm nút  ☀️ Sáng / 🌙 Tối  ở thanh công cụ.

LƯU Ý
-----
- Dữ liệu nhập được lưu trong trình duyệt (localStorage) của MÁY đang mở.
  Gửi folder sang máy khác thì máy đó bắt đầu từ dữ liệu Excel tháng 6 và tháng 7.
- Cây phòng ban và số user phân quyền Trợ lý ảo Ralli được chuẩn hóa từ
  data/phong_ban_phan_quyen.xlsx và nhúng trong app.js.
- Cột Users / Chat để 0: Google chỉ nhận diện theo API key, không quy ra
  người dùng thật, nên số này phải nhập tay nếu có nguồn khác.
