## ADDED Requirements

### Requirement: Đường làm mới nhanh phải phủ mọi bảng dẫn xuất của nguồn
Khi có đường làm mới nhanh cho một nguồn dữ liệu, đường đó SHALL dựng lại **mọi** bảng dẫn
xuất mà nguồn ấy nuôi. Nó MUST NOT để lại bảng nào mang số cũ.

#### Scenario: Nguồn nhận dữ liệu mới
- **WHEN** đường làm mới nhanh chạy xong cho một nguồn
- **THEN** mọi bảng dẫn xuất mà nguồn đó nuôi SHALL phản ánh dữ liệu mới nhất

#### Scenario: Thêm một bảng dẫn xuất mới
- **WHEN** một bảng dẫn xuất mới được thêm cho nguồn đó
- **THEN** đường làm mới nhanh SHALL dựng lại cả bảng ấy
- **AND** MUST NOT chỉ được cập nhật ở đường dựng lại toàn bộ

#### Scenario: Thứ tự giữa các bước dẫn xuất
- **WHEN** một bước dẫn xuất đối chiếu kết quả của mình với một bảng dẫn xuất khác
- **THEN** bước ấy SHALL chạy sau bảng nó đối chiếu
- **AND** MUST NOT so với một bảng chưa được dựng lại trong cùng lượt

### Requirement: Đường làm mới nhanh MUST NOT phụ thuộc dữ liệu chuẩn bị bằng tay
Đường làm mới nhanh — thứ được thiết kế để chạy lặp — SHALL chỉ đọc những gì đã nằm trong
database. Nó MUST NOT phụ thuộc vào tệp phải chuẩn bị bằng tay.

#### Scenario: Một bước cần dữ liệu ngoài database
- **WHEN** một bước dựng lại cần tệp do người chuẩn bị
- **THEN** bước đó MUST NOT được đưa nguyên vào đường làm mới nhanh
- **AND** phần tính được **chỉ từ database** SHALL tách ra chạy riêng

#### Scenario: Tệp chuẩn bị tay vắng mặt
- **WHEN** tệp chuẩn bị tay không còn ở chỗ cũ
- **THEN** đường làm mới nhanh SHALL vẫn chạy được cho phần không cần tệp ấy

#### Scenario: Chế độ đầy đủ
- **WHEN** đường dựng lại toàn bộ chạy
- **THEN** hành vi của nó SHALL không đổi vì có thêm chế độ chạy riêng

### Requirement: Làm mới một phần MUST NOT xoá phần của nguồn khác
Khi một bước chỉ dựng lại phần của một nguồn, nó SHALL chỉ xoá đúng phần ấy. Dữ liệu của
nguồn khác trong cùng bảng MUST NOT bị đụng tới.

#### Scenario: Dựng lại phần của một nguồn
- **WHEN** một bước dựng lại phần của một nguồn trong bảng dùng chung
- **THEN** số dòng của mọi nguồn khác SHALL không đổi

#### Scenario: Nghiệm thu bước làm mới một phần
- **WHEN** nghiệm thu một bước làm mới một phần
- **THEN** phép kiểm SHALL đếm số dòng của **mọi** nguồn trong bảng, trước và sau
- **AND** MUST NOT chỉ đếm nguồn vừa được dựng lại

#### Scenario: Phần bị xoá nhầm không dựng lại được từ database
- **WHEN** một nguồn trong bảng chỉ dựng lại được từ dữ liệu ngoài database
- **THEN** bước làm mới một phần MUST NOT có đường nào xoá được nguồn ấy

### Requirement: Bảng dẫn xuất cũ phải bị phát hiện trước khi tổng lệch
Hệ thống SHALL phát hiện được một bảng dẫn xuất đã cũ so với bảng nguồn của nó, và phát hiện
bằng dấu hiệu xuất hiện **sớm hơn** chênh lệch tổng.

#### Scenario: Một bảng dẫn xuất bị bỏ lại
- **WHEN** bảng nguồn có dữ liệu mới hơn một bảng dẫn xuất của nó
- **THEN** phép kiểm SHALL báo hỏng
- **AND** SHALL nêu bảng nào đang cũ

#### Scenario: Dữ liệu mới bị tầng tổng hợp lọc bỏ hợp lệ
- **WHEN** dữ liệu mới nhất của bảng nguồn bị tầng tổng hợp loại bỏ theo đúng bộ lọc của nó
- **THEN** phép kiểm MUST NOT báo hỏng
- **AND** phép so SHALL thực hiện trên đúng tập dòng mà tầng tổng hợp nhận

#### Scenario: Nguồn chưa có dòng nào
- **WHEN** nguồn chưa có dòng nào để so
- **THEN** kết quả SHALL là chưa kiểm được, không phải đạt
