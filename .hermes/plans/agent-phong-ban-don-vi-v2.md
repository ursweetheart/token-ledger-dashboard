# V2 — Sắp cây nghiệp vụ cho bộ lọc Agent → Phòng ban → Đơn vị → Đội → User

## Phạm vi đã duyệt

Chỉ cập nhật mockup và tài liệu để xem trước. Không sửa dashboard production, database, tài khoản, quyền đăng nhập, dữ liệu crawl, migration hoặc Docker. Không commit/push nếu chưa được yêu cầu riêng.

Đây là phân cấp tổ chức cho trình bày và lọc, không phải triển khai cơ chế cấp quyền truy cập.

## Nguồn và nguyên tắc

- Dữ liệu có mặt theo agent: snapshot `data/raw_web/{ralli,tla-hd}/2026-09-12/units.json`, đại diện dữ liệu crawl dùng trong mockup; chưa truy vấn database runtime.
- Khung nghiệp vụ: `2026.T4.09 DS Đội.xlsx`, sheet `DS đội`, cập nhật 09/04/2026. Có 3 phòng, 11 đơn vị, 67 đội (đối chiếu sheet `Tổng`).
- Excel chỉ dẫn cách phân cấp và đặt tên; không thay thế tập node nguồn. Giữ nguyên ID, tên nguồn, parent nguồn và agent. Mockup bổ sung nhãn hiển thị, cấp và dấu vết đối chiếu.
- Không suy thay đổi tổ chức chỉ từ việc tháng của Excel cũ hơn/mới hơn nguồn. Các trường hợp chưa rõ giữ nguyên và ghi cần đối chiếu.
- Sheet `Cũ-Mới` chứa 74 dòng tên cũ quy về 67 tên V1/V2. V2 mockup dùng tên của sheet `DS đội`, không tự gộp ID nguồn theo bảng tên cũ.

## Bộ lọc mới

```text
Agent → Phòng ban / Khối → Đơn vị → Đội → User
```

- Phòng ban chỉ chứa phòng/khối và phạm vi trực thuộc công ty khi cần.
- Đơn vị chỉ chứa đơn vị con của phòng được chọn; không chứa TEAM.
- Đội chỉ chứa đội của đơn vị được chọn. Loại đội (Truyền thống; Dự án/ Chuyên trách) là thuộc tính, không tạo cấp cha giả.
- Đổi cấp cha xóa tất cả lựa chọn cấp con. Xóa lọc đưa về trạng thái tổng.
- Tất cả đội bao gồm cả tài khoản trực thuộc đơn vị. Tất cả đơn vị bao gồm cả tài khoản trực thuộc phòng.
- Thiếu cây API không chứng minh agent không có phòng sử dụng. Nhãn phân công trong Excel chi phí cần được đối chiếu riêng; ví dụ agent chưa nối cây trong mockup không đại diện mọi agent dịch vụ.
- User chưa nối danh bạ trong mockup, giữ disabled và ghi rõ. Không tạo số tài khoản, token, request hoặc chi phí giả.

## Cây đối chiếu, giữ các node nguồn chưa có trong Excel

```text
Phòng Bán hàng 1
├── Truyền thống Vùng 1
├── Truyền thống Vùng 2
├── Truyền thống Vùng 3
└── Trung tâm 1
    ├── Đội Chuyên trách 1 - Trung tâm 1
    ├── Đội Chuyên trách 2 - Trung tâm 1
    └── TT1 [đội crawl, cần đối chiếu]

Phòng Bán hàng 2
├── CN Đà Nẵng
├── CN Nha Trang
├── CN Tây Nguyên
└── TT2 [đơn vị crawl Ralli, cần đối chiếu]
    └── Giữ đầy đủ các đội nguồn của TT2

Phòng Bán hàng 3
├── CN Hồ Chí Minh
├── CN Biên Hòa
├── CN Cần Thơ
├── CN Tiền Giang
├── TT3 [cần đối chiếu]
└── TT4 [Ralli, cần đối chiếu]
```

Cây trên minh họa Ralli. Với Hợp Đồng chỉ hiển thị node nguồn của Hợp Đồng: Trung tâm 2 và TT3 vẫn giữ, không tự thêm TT4 hoặc các đội nguồn Ralli. Các phòng ngoài ba phòng bán hàng vẫn giữ trong danh mục nguồn, ghi ngoài phạm vi Excel DS đội.

## Nhãn đối chiếu trong bản xem thử

- PBH1/2/3 và Phòng BH1/2/3 → Phòng Bán hàng 1/2/3.
- Vùng 1/2/3 → Truyền thống Vùng 1/2/3.
- TT1 ở cấp đơn vị → Trung tâm 1. Node TEAM tên TT1 giữ riêng, không tự ánh xạ về đơn vị.
- Tây Nguyên → CN Tây Nguyên.
- CN HCM → CN Hồ Chí Minh; CN Biên Hoà → CN Biên Hòa, trong đúng Phòng Bán hàng 3 và đúng agent nguồn.
- Tên đội đối chiếu trong cùng phòng và đơn vị, có xử lý khác biệt khoảng trắng, dấu gạch nối, chữ hoa/thường và biến thể Hòa/Hoà, Hóa/Hoá để tìm ứng viên. Đây là đối chiếu nhãn mockup, không phải luật merge production.
- Hai tên đội rút gọn được dùng làm đề xuất trong mockup: `Đội Chuyên Trách 2` dưới TT1 → `Đội Chuyên trách 2 - Trung tâm 1`; `Đội chuyên trách - Tây Nguyên` → `Đội Chuyên trách - CN Tây Nguyên`. Giữ tên crawl và tọa độ dòng Excel để người dùng kiểm tra trước khi áp dụng thật.

## Kết quả kiểm tra nguồn

- Ralli: giữ đủ 102 ID nguồn, trong đó 66 TEAM tìm được tên tương ứng theo phòng/đơn vị trong Excel.
- Hợp Đồng: giữ đủ 20 ID nguồn, không có TEAM trong snapshot; không tự lấy 67 đội Excel gắn vào agent này.
- Đội Quảng Ngãi: có tại `DS đội!E33`, thuộc Phòng Bán hàng 2 → CN Đà Nẵng; không có trong snapshot Ralli. Hiển thị cảnh báo, không tạo ID crawl hoặc gán user giả.
- Các node Ralli cần đối chiếu: TEAM TT1; đơn vị TT2 và các đội con; TT3, TT4.
- Các đơn vị Hợp Đồng cần đối chiếu: Trung tâm 2, TT3.
- Parent nguồn giữ nguyên ở bản này: các cặp đối chiếu xác định được nằm dưới đúng cha tương ứng; chưa có cơ sở chuyển cha của node chưa khớp.

Bảng kiểm có ID, tên crawl, nhãn mới, parent, loại và dòng Excel: `sketches/reconciliation-v2.json`.

## File xem thử

- Thanh ngang: `sketches/agent-filter-horizontal/v2.html`.
- Bên trái: `sketches/agent-filter-sidebar/v2.html`.
- `index.html` ở hai thư mục là bản V1 để so sánh, không phải bản mới.

## Kiểm tra bắt buộc

Mỗi mockup có `window.runChecks()` chạy trong console trình duyệt:

1. Khóa cấp con trước khi chọn cha.
2. Đơn vị không chứa TEAM, Đội chỉ chứa con của đơn vị.
3. CN Biên Hòa nguồn Ralli có đầy đủ đội nguồn.
4. Trung tâm 1 hiển thị tên Excel nhưng vẫn giữ TEAM TT1 có nhãn cần đối chiếu.
5. Đổi agent/đơn vị reset đầy đủ cấp con.
6. Hợp Đồng không bị thêm đội giả hoặc node Ralli.
7. Giữ đủ ID nguồn của cả hai agent; Đội Quảng Ngãi không bị tự thêm vào tập crawl.
8. Phạm vi trực thuộc công ty không chứa đơn vị/đội con.
9. Kiểm tra giao diện màn hình rộng và nhỏ, không tràn ngang.

## Trước khi triển khai thật

- Người dùng duyệt các nhãn đối chiếu và cách giữ node chưa rõ.
- Đọc lại code nhánh đích; phân tích trước đây chủ yếu ở `ChiThanh_Develop@b308a5f`, không mặc nhiên dùng các số dòng đó cho `ChiThanh`.
- Tái sử dụng canonical và quan hệ nguồn hiện hữu, bổ sung phép lọc theo agent + ID, không ghi đè bản ghi crawl.
- Kiểm tra mọi đường lọc tài khoản và usage, bảo toàn tổng; phân biệt số đo theo tài khoản với số tổng/phân bổ theo agent.
- Thay đổi quyền truy cập/RBAC hoặc dữ liệu database là phạm vi khác, chưa được duyệt.
