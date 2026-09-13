## 1. Dọn chỗ — làm trước, vì CI mới sẽ đỏ ngay nếu bỏ qua

- [x] 1.1 Quyết định giữa phương án A và B ở `design.md` mục "canh dòng bind, hay bỏ hẳn dòng bind".
      Đề xuất là **B**. Mọi việc ở mục 4 phụ thuộc quyết định này
- [x] 1.2 Nếu chọn B: đổi khai báo cổng của `web` trong `docker-compose.yml` thành
      `"${WEB_BIND:-127.0.0.1}:${WEB_PORT:-8080}:80"`, và **xoá khối chú thích nhắc sửa tay** — chú
      thích đó chỉ còn nghĩa khi việc sửa tay còn tồn tại. Nghiệm thu: `docker compose config` in ra
      `127.0.0.1:8080` khi `.env` không đặt gì, và in ra `192.168.20.111:8080` khi đặt
      `WEB_BIND=192.168.20.111`
- [x] 1.3 Khai `WEB_BIND` trong `.env.example` kèm chú thích nói rõ để trống là máy phát triển, đặt
      IP nội bộ là máy chủ. Nghiệm thu: `.env.example` theo git, `.env` vẫn bị `.gitignore` bỏ qua
- [x] 1.4 Xoá thư mục rác `docker/gateway/config.gateway.yaml;C`. Nó rỗng, không nằm trong
      `git ls-files`, tạo ngày 08/09, và đang lọt vào build context. Nghiệm thu: `ls docker/gateway/`
      không còn mục đó

## 2. Nhóm kiểm JavaScript

- [x] 2.1 Thêm công việc chạy `node --test tests/*.test.js`. **Không** thêm bước cài gói — repo
      không có `package.json`, và việc không cần cài chính là tính chất được canh. Nghiệm thu: chạy
      xanh trên máy ảo sạch, không có bước `npm install` nào
- [x] 2.2 Đọc số phép kiểm từ kết xuất và so với mốc **51**. Xem Requirement "Bộ kiểm phải báo số
      phép đã chạy, không chỉ báo đạt". Nghiệm thu: thử sửa mốc thành 52 thì công việc phải đỏ, và
      thông điệp phải nói cả số mong đợi lẫn số thật
- [x] 2.3 Kiểm rằng mẫu tên tệp nở hụt thì công việc đỏ, không xanh. Nghiệm thu: chạy thử với một
      mẫu cố ý sai, kết quả phải là hỏng

## 3. Nhóm kiểm Python

- [x] 3.1 Thêm công việc chạy `python -m unittest discover -s tests -p "test_*.py"`. **Không** thêm
      bước `pip install` — `psycopg2` được nạp trong hàm ở `db/connect.py:196`, nên bộ kiểm không
      cần nó. Nghiệm thu: xanh trên máy ảo sạch không cài gói nào
- [x] 3.2 Nếu bước 3.1 đỏ vì thiếu gói, **dừng lại và ghi lại đó là phát hiện**, đừng vá bằng cách
      thêm `pip install`. Nó có nghĩa là tính chất "chạy được mà không cài gì" đã mất, và cần biết
      tệp nào làm mất. Xem Requirement "Bộ kiểm phải chạy được trên một máy sạch"
- [x] 3.3 Đọc số phép kiểm và so với mốc **11**. Nghiệm thu: giống 2.2
- [x] 3.4 Đặt `PYTHONIOENCODING=utf-8` cho công việc này. Kết xuất phép kiểm có tiếng Việt có dấu;
      thiếu biến này thì tiến trình chết giữa chừng ở một số môi trường. Nghiệm thu: kết xuất hiện
      đúng dấu tiếng Việt trong nhật ký chạy

## 4. Nhóm canh cấu hình

- [x] 4.1 Thêm công việc kiểm rằng không tệp cấu hình theo git nào ghim địa chỉ IP của một môi
      trường cụ thể ở phần khai cổng. Viết theo **nguyên tắc**, không ghim một địa chỉ cụ thể vào
      phép kiểm. Xem Requirement "Cấu hình dành riêng cho một môi trường MUST NOT đi lên nhánh chính"
- [x] 4.2 Kiểm ngược: cố ý đặt lại một địa chỉ ghi cứng rồi chạy, phép kiểm phải đỏ. Một phép kiểm
      chưa từng đỏ là một phép kiểm chưa biết có chạy hay không
- [x] 4.3 Nghiệm thu: thông điệp lỗi nêu đủ tệp, dòng, và tên biến nên dùng thay

## 5. Ghép ba nhóm

- [x] 5.1 Cho ba nhóm chạy **song song**, không phụ thuộc nhau. Nghiệm thu: một nhóm đỏ thì hai nhóm
      kia vẫn báo kết quả riêng của chúng
- [x] 5.2 Kích hoạt cả khi đẩy code lên nhánh `Tuan-develop` lẫn khi mở pull request về `main`
- [ ] 5.3 Đo thời gian chờ thật và **ghi con số đó vào `design.md`**. Ước lượng hiện tại là 30–45
      giây, dựng từ phần đã đo (9,5 giây JavaScript, dưới 1 giây Python, đo trong container sạch)
      cộng phần chưa đo là máy ảo khởi động và lấy mã nguồn. Nếu vượt quá hai phút thì ghi cả nguyên
      nhân, đừng chỉ ghi con số

## 6. Kiểm chứng bằng một vòng thật

- [ ] 6.1 Đẩy một commit cố ý làm hỏng một phép kiểm JavaScript, xác nhận CI **đỏ**, rồi hoàn tác.
      Một hệ thống canh chưa từng bắt được gì thì chưa chứng minh được nó có canh
- [ ] 6.2 Làm lại điều đó với một phép kiểm Python
- [ ] 6.3 Làm lại với nhóm canh cấu hình, bằng cách đặt lại một địa chỉ ghi cứng
- [ ] 6.4 Xác nhận commit sạch thì CI **xanh** cả ba nhóm, và số phép kiểm báo đúng 51 và 11

## 7. Ghi lại

- [x] 7.1 Thêm một mục ngắn vào `README.md` nói CI chạy gì, và cách chạy đúng ba lệnh đó ở máy mình.
      Không chép lại tệp workflow vào tài liệu — hai bản sao sẽ trôi khỏi nhau
- [x] 7.2 Ghi vào tài liệu tham khảo bốn luật cho chặng 3 ở `design.md`, đặc biệt luật cấm profile
      `tools`. Chúng được đo trong change này nhưng sẽ dùng ở change sau

## Không làm trong change này

- Đóng gói image, đẩy lên kho — chặng 2
- Tự động đưa code lên máy chủ, runner nội bộ — chặng 3
- Dọn database `token_ledger` cũ — việc riêng, xem `design.md` để biết vì sao chưa xoá được ngay
