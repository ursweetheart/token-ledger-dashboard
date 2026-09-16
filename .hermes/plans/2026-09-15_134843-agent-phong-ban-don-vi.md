# Kế hoạch bộ lọc — Bản V1 lưu tham khảo

> **Đã được thay thế về thiết kế bởi [V2 — phân cấp theo Excel](agent-phong-ban-don-vi-v2.md).** V2 tách Đơn vị và Đội thành hai dropdown, dùng Excel làm khung nghiệp vụ nhưng giữ toàn bộ node crawl. Các quy tắc dưới đây (gộp Đội vào Đơn vị, giữ nguyên tên nguồn để hiển thị, suy không có phòng từ việc thiếu cây API) là thiết kế V1, không còn là hướng triển khai. Chỉ mockup/tài liệu được duyệt cập nhật; chưa sửa dashboard thật hoặc quyền truy cập.

**Trạng thái:** Đề xuất để duyệt; chưa triển khai. Việc tạo tài liệu không đồng nghĩa đã duyệt sửa code hoặc database.

**Mục tiêu:** Chọn agent trước, sau đó chỉ chọn được phòng ban và đơn vị thuộc cây của agent đó; không trộn các cây nguồn trong cùng dropdown.

**Kiến trúc:** Tái sử dụng `catalog.units` để dựng lựa chọn theo cây nguồn của từng agent. Giữ nguyên cây canonical cho báo cáo tổng; khi lọc tài khoản/số liệu, đối chiếu phạm vi cây nguồn với ID canonical và điều kiện agent.

**Công nghệ:** JavaScript hiện hữu, HTML select native, kiểm thử `node:test`; không thêm thư viện.

**Bối cảnh:** Repo `D:/token-ledger-dashboard`, nhánh `ChiThanh_Develop`, commit đã kiểm tra `b308a5f`. Cây dưới đây được đối chiếu từ snapshot `2026-09-12`, không phải xác nhận trạng thái database runtime.

---

## 1. Phạm vi bản thử

Thanh lọc đề xuất:

```text
[Agent ▼] → [Phòng ban / Khối ▼] → [Đơn vị ▼] → [User ▼]
```

Provider, Model và khoảng thời gian giữ chức năng hiện hữu. Chỉ thêm một ô Đơn vị; đội con được hiển thị thụt cấp trong ô này, chưa thêm dropdown Đội riêng.

Không sửa raw data, không mở rộng canonical mapping database, không migration/rebuild database, không đổi Docker/network, không commit hoặc push trong phạm vi tạo tài liệu này.

## 2. Quy tắc tương tác

| Trạng thái/thao tác | Hành vi đề xuất |
|---|---|
| Chưa chọn agent hoặc chọn Tất cả agent | Xem tổng dashboard; khóa Phòng ban và Đơn vị, nhắc Chọn agent trước |
| Chọn agent có cây tổ chức | Mở Phòng ban/Khối, chỉ hiện các phạm vi thuộc agent đó |
| Chọn phòng ban | Mở Đơn vị, chỉ hiện đơn vị và đội bên dưới phòng đã chọn |
| Chọn Tất cả đơn vị | Bao gồm tài khoản trực thuộc phòng và mọi đơn vị con |
| Chọn một đơn vị | Bao gồm tài khoản trực thuộc đơn vị đó và cây con của nó |
| Phòng không có đơn vị con | Khóa Đơn vị, ghi Không có đơn vị con; vẫn lọc được user trực thuộc phòng |
| Agent không có cây tổ chức | Khóa Phòng ban và Đơn vị, ghi Agent chưa có cây tổ chức; không lấy tên agent giả làm phòng |
| Đổi agent | Xóa phòng ban, đơn vị, user cũ và trạng thái bung cây không còn hợp lệ |
| Đổi phòng ban | Xóa đơn vị và user cũ |
| Đổi đơn vị | Xóa user cũ |
| Xóa lọc | Xóa cả lựa chọn Đơn vị mới và trở về tổng ban đầu |

Danh mục tổ chức lấy từ catalog, không suy từ riêng các dòng có usage trong kỳ. Đơn vị chưa phát sinh usage vẫn được chọn; kết quả rỗng phải được trình bày đúng, không tự chuyển sang đơn vị khác.

## 3. Cây Phòng ban → Đơn vị

### 3.1. Trợ lý ảo Ralli

Nguồn: `data/raw_web/ralli/2026-09-12/units.json`.

Cây nguồn có hai tầng tổng hợp `Toàn công ty → Tổng công ty Rạng Đông`. Filter bỏ qua các tầng được đánh dấu tổng hợp để chọn thẳng phòng/khối. Cây dưới đây trình bày đến cấp đơn vị, chưa liệt kê toàn bộ đội.

```text
Trợ lý ảo Ralli
├── PBH1
│   ├── Vùng 1
│   ├── Vùng 2
│   ├── Vùng 3
│   └── TT1
├── PBH2
│   ├── CN Đà Nẵng
│   ├── CN Nha Trang
│   ├── Tây Nguyên
│   └── TT2
├── PBH3
│   ├── CN Hồ Chí Minh
│   ├── CN Biên Hòa
│   ├── CN Cần Thơ
│   ├── CN Tiền Giang
│   ├── TT3
│   └── TT4
├── Xuất khẩu
├── Truyền thông
├── Kế toán
├── TMĐT
├── C4LED
├── Nghiên cứu thị trường
├── Kế hoạch
├── Trung tâm R&D
└── Quản trị hệ thống
```

Ví dụ cây đầy đủ bên dưới CN Biên Hòa:

```text
PBH3
└── CN Biên Hòa
    ├── Đội Bình Dương
    ├── Đội Bình Phước
    ├── Đội Bình Thuận
    ├── Đội Đồng Nai
    ├── Đội Vũng Tàu
    └── Đội chuyên trách - CN Biên Hòa
```

Ví dụ hiển thị trong ô Đơn vị khi chọn PBH3:

```text
Tất cả đơn vị
CN Hồ Chí Minh
    CN Hồ Chí Minh › Đội 1
    CN Hồ Chí Minh › Đội 2
    …
CN Biên Hòa
    CN Biên Hòa › Đội Bình Dương
    CN Biên Hòa › Đội Bình Phước
    CN Biên Hòa › Đội Bình Thuận
    CN Biên Hòa › Đội Đồng Nai
    CN Biên Hòa › Đội Vũng Tàu
    CN Biên Hòa › Đội chuyên trách - CN Biên Hòa
CN Cần Thơ
    …
CN Tiền Giang
    …
TT3
TT4
```

Dấu `…` chỉ rút gọn ví dụ trong tài liệu. Giao diện phải lấy đủ node từ catalog, không gõ cứng danh sách này.

Chọn CN Biên Hòa lấy cả tài khoản trực thuộc chi nhánh và các đội con. Chọn Đội Đồng Nai chỉ lấy phạm vi đội đó.

Ralli có TT1 và TT2 ở cả cấp BRANCH lẫn TEAM. Đây là các node khác nhau, không gộp theo tên; nhãn có thể là `TT1` và `TT1 › TT1 (đội)`. Nếu catalog chưa cung cấp loại đơn vị, dùng đường dẫn cha để phân biệt thay vì đoán loại từ tên.

### 3.2. Trợ Lý Ảo Hợp Đồng

Nguồn: `data/raw_web/tla-hd/2026-09-12/units.json`.

Giữ tên của nguồn Hợp Đồng trong chế độ chọn agent:

```text
Trợ Lý Ảo Hợp Đồng
├── Công ty CPBĐ PN Rạng Đông
│   ├── Phòng BH1
│   │   ├── Trung tâm 1
│   │   ├── Vùng 1
│   │   ├── Vùng 2
│   │   └── Vùng 3
│   ├── Phòng BH2
│   │   ├── CN Đà Nẵng
│   │   ├── CN Nha Trang
│   │   ├── CN Tây Nguyên
│   │   └── Trung tâm 2
│   └── Phòng BH3
│       ├── CN Biên Hoà
│       ├── CN Cần Thơ
│       ├── CN HCM
│       ├── CN Tiền Giang
│       └── TT3
├── TT C4LED
├── TT&TMĐT
└── TTDL&DHS
```

Ô Phòng ban/Khối đề xuất có:

- Phòng BH1.
- Phòng BH2.
- Phòng BH3.
- TT C4LED.
- TT&TMĐT.
- TTDL&DHS.
- Trực thuộc Công ty CPBĐ PN Rạng Đông.

Lựa chọn cuối là **phạm vi chỉ tài khoản trực thuộc công ty**, không gồm phòng con. Đây là nhãn lọc, không phải đơn vị mới trong database; giá trị lựa chọn phải biểu diễn rõ chế độ trực thuộc, không dùng cùng phép lấy toàn bộ descendants của công ty. Chọn Tất cả phòng ban vẫn bao gồm cả tài khoản trực thuộc và các phòng.

Không đưa TT4 hoặc các đội chỉ có trong cây Ralli sang cây Hợp Đồng. Không tự gộp TT&TMĐT với Truyền thông/TMĐT khi chưa có xác nhận nghiệp vụ.

### 3.3. Agent không có cây tổ chức

```text
Agent được chọn
├── Phòng ban: không áp dụng
├── Đơn vị: không áp dụng
└── User: giữ cách thể hiện tài khoản dịch vụ/quy ước hiện hữu
```

Phân biệt catalog đang tải/lỗi với agent thực sự không có cây. Không hard-code rằng chỉ hai tên agent trên mới được phép có cây; quyết định theo dữ liệu catalog không kỹ thuật của agent.

## 4. Nguyên nhân cần sửa luồng hiện tại

Các vị trí đã đọc trên nhánh hiện tại:

| Vị trí | Hành vi hiện tại |
|---|---|
| `web/js/app.js:3673` — `buildDepartmentFilterOptions` | Duyệt toàn bộ ORG_UNITS, loại trùng theo tên, chưa chia theo agent/cấp |
| `web/js/api.js:213` — `orgTree` | Gộp cây qua canonical_unit_id và bỏ node alias trước khi giao cho app.js |
| `web/js/api.js:237` | Node giữ agentId của bản canonical, không giữ đầy đủ quan hệ nguồn của alias |
| `web/js/app.js:967` — `applyFilters` | Phòng ban lưu tên, tra đơn vị rồi lấy descendants |
| `web/js/app.js:3110` — `filterAccounts` | Lọc danh bạ theo phòng và agent; cần bổ sung cùng phạm vi Đơn vị |
| `web/js/app.js:3725` — `fillSelect` | Đã có cơ chế chỉ dựng lại option khi danh sách đổi; cần giữ cơ chế này |
| `web/js/app.js:3898` | Xóa lọc hiện chưa có trường Đơn vị |
| `web/index.html:453` | Thanh filter hiện đặt Phòng ban trước Agent, chưa có ô Đơn vị |
| `backend/store.py:166` | Catalog đã có ID nguồn, agent, tên, cha, canonical và cờ tổng hợp |

Không thể chỉ lọc `agentId` trên cây đã gộp: các phòng Hợp Đồng đã map sang Ralli có thể biến mất khỏi lựa chọn Hợp Đồng.

## 5. Thiết kế dữ liệu tối thiểu

1. Giữ nguyên cây canonical phục vụ báo cáo tổng và bảng tra ID nguồn → ID canonical hiện có.
2. Trong lớp dịch `web/js/api.js`, giữ thêm thông tin cây nguồn từ catalog: agent, ID nguồn, tên nguồn, parent nguồn, canonical ID và cờ kỹ thuật/tổng hợp.
3. Dựng dropdown từ cây nguồn của agent đã chọn, trước khi alias bị loại khỏi cây hợp nhất.
4. Option dùng ID, không dùng tên làm định danh. Nếu cần khóa ghép để phân biệt nguồn/phạm vi trực thuộc, dùng khóa tường minh; không sửa ID gốc.
5. Phạm vi lọc được tính trên cây nguồn đã chọn, rồi đối chiếu canonical ID **kèm điều kiện agent**. Không dùng descendants toàn bộ cây hợp nhất để suy phạm vi của một agent.
6. Cùng ID trong cùng phạm vi chỉ tạo một option; khác ID nhưng cùng tên phải giữ và thêm đường dẫn.
7. Dùng chung quy tắc phạm vi cho danh bạ, dropdown User và những đường lọc số liệu liên quan; không vá riêng phần danh sách option.
8. Lựa chọn lưu cũ chỉ chuyển sang ID nếu khớp duy nhất và có đủ ngữ cảnh agent; trường hợp mơ hồ thì xóa lựa chọn an toàn, không đoán.

Bản thử theo agent sẽ không hiển thị đồng thời CN Biên Hòa của Ralli và CN Biên Hoà của Hợp Đồng trong cùng dropdown. Điều này **không đồng nghĩa** đã giải quyết hợp nhất hai đơn vị trong chế độ báo cáo toàn công ty; mở rộng canonical mapping là công việc riêng nếu được yêu cầu.

## 6. Kế hoạch thực hiện sau khi được duyệt

### Bước 1 — Khóa hành vi bằng test

- Đọc lại trạng thái branch và các hàm liên quan trước khi sửa.
- Mở rộng `tests/department-filter-options.test.js` với fixture hai agent, một phòng đã canonicalize và các node con khác nhau.
- Test chọn Hợp Đồng phải còn Phòng BH1/BH2/BH3 và TT C4LED nhưng không được lẫn TT4/đội chỉ có ở Ralli.
- Test hai cấp TT1 không bị gộp theo tên.
- Chạy kiểm thử, xác nhận test mới thất bại đúng vì chưa có lọc phụ thuộc; không dùng lỗi cú pháp/import làm bằng chứng tái hiện.

### Bước 2 — Giữ cây nguồn cho dropdown

- Sửa `web/js/api.js` để truyền thông tin cây nguồn đã có trong catalog.
- Giữ hành vi cây canonical và bảng tra ID hiện hữu.
- Thêm kiểm tra trong bộ test phù hợp để bảo đảm alias Hợp Đồng vẫn xuất hiện trong danh mục của Hợp Đồng.

### Bước 3 — Thêm dropdown phụ thuộc

- Sửa `web/index.html`: Agent trước Phòng ban/Khối, thêm Đơn vị trước User; label liên kết đúng với select.
- Sửa `web/js/app.js`: state Đơn vị, option có ID/nhãn, trạng thái disabled và reset dây chuyền.
- Tái sử dụng cơ chế chữ ký option và gắn change handler một lần của `fillSelect`; giữ tương thích các dropdown Provider/Model/User hiện hữu.
- Chỉ tạo một điểm xử lý phạm vi để hai đường `applyFilters` và `filterAccounts` không lệch nhau.
- Kiểm tra các chỗ đọc/lưu/xóa `state.filters` và trạng thái bung cây, không chỉ nơi render dropdown.

### Bước 4 — Kiểm thử hồi quy

Chạy từ repo:

```bash
node --test tests/department-filter-options.test.js tests/filter-select-refresh.test.js
```

Kỳ vọng sau triển khai: toàn bộ test cũ còn phù hợp và test mới đều pass. Đây là tiêu chí tương lai, không phải kết quả đã chạy cho tính năng mới.

### Bước 5 — Kiểm tra runtime

- Khi dashboard/API đã chạy được trong môi trường được phép, đối chiếu dropdown với response catalog thực tế.
- Chạy các ca ở mục 7; kiểm tra DOM option, kết quả bảng và lỗi trình duyệt.
- So sánh số liệu trước/sau khi không áp filter và sau khi xóa filter.
- Nếu bị chặn vì Docker/network/database, báo blocker; không tự sửa stack khác hoặc rebuild database để vượt qua.

## 7. Tiêu chí nghiệm thu

- [ ] Chọn Ralli chỉ thấy phòng/khối thuộc Ralli.
- [ ] Chọn Hợp Đồng vẫn thấy các phòng đã canonicalize, không lẫn đơn vị chỉ có ở Ralli.
- [ ] PBH3 → Đơn vị của Ralli có CN Biên Hòa, không có CN Biên Hoà của nguồn Hợp Đồng.
- [ ] Phòng BH3 → Đơn vị của Hợp Đồng có CN Biên Hoà/CN HCM theo tên nguồn.
- [ ] Chọn phòng không có con vẫn giữ được user trực thuộc phòng.
- [ ] Tất cả đơn vị bao gồm cả user trực thuộc phòng và các đơn vị con.
- [ ] Phạm vi Trực thuộc Công ty CPBĐ PN Rạng Đông không kéo theo user ở phòng con.
- [ ] Chọn chi nhánh lấy đúng chi nhánh và đội con; chọn đội không lấy nhánh anh em.
- [ ] TT1/TT2 khác cấp có option riêng và nhãn phân biệt.
- [ ] Đơn vị không có usage trong kỳ vẫn còn trong danh mục.
- [ ] Agent không có cây không bị gán phòng giả trong các dropdown mới.
- [ ] Đổi agent/phòng/đơn vị nhiều lần vẫn cập nhật, không giữ lựa chọn con ngoài phạm vi.
- [ ] Xóa lọc hoặc mở lại từ localStorage cũ không giữ ID không hợp lệ.
- [ ] Provider/Model và các danh sách người dùng hiện hữu không bị thay đổi ngoài phạm vi.
- [ ] Tổng request/token/chi phí khi không lọc không đổi; không nhân đôi dữ liệu do nối canonical.
- [ ] Raw data, database và cấu hình Docker không bị sửa trong bản thử frontend.

## 8. Giới hạn số liệu và rủi ro

- `web/js/api.js:325` xử lý các dòng `/api/usage` ở mức agent/model/ngày, gắn đơn vị đại diện. Thêm dropdown không tự tạo được token/chi phí đo riêng cho từng đơn vị.
- Khi test phải phân biệt số đo theo tài khoản, số tổng theo agent và số phân bổ. Chưa có dữ liệu đủ chi tiết phải hiển thị đúng giới hạn, không báo 0 như một số đo chắc chắn hoặc tuyên bố lọc số liệu chính xác chỉ vì option đúng.
- Tài khoản trực thuộc cấp công ty không được bỏ mất khi bỏ qua các tầng tổng hợp.
- Quan hệ parent và level khác nhau giữa nguồn; không suy cấp chỉ bằng con số level hoặc tên.
- Hợp nhất theo canonical không được làm mất dấu agent nguồn.
- Giữ hai biểu diễn cây là để phục vụ hai cách nhìn trên cùng catalog, không phải thêm một nguồn dữ liệu gõ cứng.

## 9. Các file dự kiến thay đổi khi triển khai

- `web/js/api.js` — giữ cây nguồn phục vụ danh mục theo agent.
- `web/js/app.js` — options, state, reset và phạm vi lọc dùng chung.
- `web/index.html` — sắp xếp thanh filter và thêm select Đơn vị.
- `tests/department-filter-options.test.js` — kiểm tra cây và phạm vi lựa chọn.
- `tests/filter-select-refresh.test.js` — kiểm tra thay đổi lựa chọn liên tiếp và reset dây chuyền khi cần.

Không dự kiến thay `db/load_org.py` hoặc schema trong bản thử này. Nếu kiểm chứng cho thấy thiếu dữ liệu/backend contract, phải trình bày phạm vi bổ sung trước khi sửa.

## 10. Điểm cần duyệt

1. Chọn một agent mới được dùng Phòng ban/Đơn vị; chế độ Tất cả agent chỉ xem tổng.
2. Giữ tên riêng của từng nguồn trong dropdown, không ép tên Hợp Đồng thành tên Ralli.
3. Đội nằm thụt cấp trong ô Đơn vị, chưa tạo ô Đội riêng.
4. Có phạm vi Trực thuộc công ty để giữ tài khoản ở cấp gốc.

**Chỉ bắt đầu triển khai sau khi người dùng duyệt thiết kế.**
