## 1. Gỡ chỗ chặn — làm trước, mọi việc sau phụ thuộc

- [x] 1.1 Tạo `.env` cho CRM tại `D:\RangDonk\CRM-Classification-Pipeline\.env`, dựa trên
      `.env.example`. **Container hiện không khởi động được** vì `docker-compose.yml:7` khai
      `env_file: .env` mà tệp đó không tồn tại. Nghiệm thu: `docker compose config --quiet` sạch và
      container lên được
- [x] 1.2 Xác nhận tệp `.env` nằm trong `.gitignore` của CRM trước khi điền bất kỳ bí mật nào.
      Nghiệm thu: `git check-ignore .env` trả về đường dẫn, và `git status` không thấy tệp
- [x] 1.3 Ghi vào `.env` project chịu phí của đường dự phòng (`crm-test-508114`) dưới dạng chú
      thích, kèm câu nói rõ nó **khác** `crm-500509` đang khai cho agent 7 trong `dim_agent`. Xem
      Requirement "Project chịu phí của đường dự phòng phải được khai rõ"
- [x] 1.4 Xác nhận `sa-key.json` còn dùng được bằng **một lượt gọi thật**, không bằng việc tệp tồn
      tại. Mốc đã đo 12/09: HTTP 200, 19 token, project `crm-test-508114`

## 2. Đường gửi thư thường

- [x] 2.1 Thêm hàm gửi qua SMTP vào `src/notification.py`, **đứng cạnh** hàm gửi qua Microsoft
      Graph, không thay thế nó. Cấu hình đã kiểm chứng: `smtp.gmail.com:587`, TLS, app password 16
      ký tự
- [x] 2.2 Thêm biến chọn đường gửi vào `src/config.py`, mặc định là đường thư thường. Mật khẩu đọc
      từ biến môi trường, MUST NOT nằm trong tệp theo git
- [x] 2.3 Gửi **một thư thật** và **chờ người nhận xác nhận đã thấy thư trong hộp thư**. Xem
      Requirement "Đường báo động phải được kiểm chứng bằng một thư thật". Thư rời khỏi máy không
      tính là thư đã tới — máy chủ thư có thể xếp vào thư rác
- [x] 2.4 Bọc mọi lời gọi gửi thư trong `try/except`, ghi log rồi chạy tiếp. Mẫu đã có sẵn ở
      `src/pipeline.py:877-879`. Nghiệm thu: cắt mạng rồi chạy một lô, lô vẫn xong

## 3. Máy trạng thái hai nấc

- [x] 3.1 Viết lớp bọc quanh client giữ trạng thái đường đang dùng, để `call_llm_batch()`
      (`src/llm.py:254`) và `src/pipeline.py` **không đổi một dòng nào**. Xem Quyết định 1 của
      design
- [x] 3.2 Viết hàm phân loại lỗi, trả về một trong ba: không kết nối được, quá hạn mức, hoặc lỗi
      yêu cầu. Nguồn phân loại là ba câu lỗi ở `src/llm.py:91-118`
- [x] 3.3 Thêm bộ đếm lỗi **liên tiếp** dưới một `threading.Lock`, và đặt lại về không sau mỗi lượt
      thành công. CRM chạy 3 worker song song dùng chung client (`src/pipeline.py:600,610`); thiếu
      chốt thì ba worker cùng đổi đường và cùng gửi thư
- [x] 3.4 Dựng đường dự phòng bằng nhánh Vertex sẵn có, đọc `sa-key.json`. Đường này MUST NOT đọc
      biến `GEMINI_API_KEY` — khi chạy qua Gateway, biến đó giữ khoá ảo `sk-…`, mang đi gọi thẳng
      Google sẽ hỏng. Xem Quyết định 4
- [x] 3.5 Thêm phép thử định kỳ để quay về Gateway, không thử ở mỗi lượt gọi. Đề nghị bắt đầu bằng
      60 giây, chỉnh sau khi diễn tập ở ô 5.2
- [x] 3.6 Thêm cấu hình bật/tắt tính năng đổi đường, **mặc định tắt**. Thiếu thông tin xác thực cho
      đường dự phòng thì tự tắt, ghi log mức lỗi lúc khởi động, nhưng agent vẫn khởi động được
- [x] 3.7 Ghi lại mọi lượt đi đường thẳng kèm mốc thời gian và lý do đổi đường. Xem Requirement
      "Lượt gọi đi đường thẳng phải đọc lại được"

## 4. Nối báo động vào máy trạng thái

- [x] 4.1 Gửi một thư khi đổi sang đường thẳng, nội dung có thời điểm, lý do, và đường đang dùng
- [x] 4.2 Gửi một thư khi quay về Gateway, nội dung có thời gian sự cố kéo dài bao lâu
- [x] 4.3 Khẳng định đúng **hai** thư cho một sự cố. Phép kiểm phải chạy trên một lô nhiều lượt
      gọi, không phải một lượt: lô ngày 09/09 có 3.422 lượt, và cách "mỗi lỗi một thư" sẽ sinh hàng
      nghìn thư

## 5. Nghiệm thu

- [x] 5.1 Phép kiểm tự động khẳng định ba câu lỗi của client Gateway vẫn phân biệt được với nhau.
      Phép kiểm này tồn tại vì việc phân loại dựa trên nội dung câu lỗi: sửa một câu chữ mà không
      ai báo sẽ làm fallback **im lặng ngừng hoạt động**
- [x] 5.2 Diễn tập mất Gateway: dừng `gateway-lb` giữa lúc chạy, bám vào nhật ký chứ không đếm giờ
      áng chừng — cùng cách làm ngày 10/09. Nghiệm thu: **không lô nào bị bỏ**, và số dòng vào sổ
      đúng bằng số dòng đầu vào
- [x] 5.3 Khẳng định không đếm đôi: đếm số lần **mỗi dòng được ghi sổ** qua cả hai đường. Phép kiểm
      "mỗi dòng có đúng một bản ghi" không chứng minh gì nếu sổ là một `dict`
- [x] 5.4 Đo lỗi 400 không kích hoạt đổi đường: gửi một yêu cầu hỏng có chủ ý, khẳng định agent giữ
      nguyên đường Gateway
- [x] 5.5 Đo nhiều luồng cùng gặp lỗi chỉ đổi đường **một** lần và gửi **một** thư
- [x] 5.6 Chạy một lô cỡ thật ở local với tính năng bật. Chưa đưa lên server.
      **ĐÓNG theo quyết định của anh Tuấn 12/09. Phạm vi thực đã chạy, ghi để không đọc nhầm:**
      `sample_data/CRM_merge_sample.xlsx` chỉ có **3 dòng**, ra đúng **1 lô**. Lô cỡ thật
      là 25 dòng một lô và hàng trăm lô. Cần dữ liệu thật hoặc một file mẫu lớn hơn.

## 6. Ghi lại

- [x] 6.1 Viết nhật ký đo vào `docs/reference/`, theo khuôn của
      `ep-429-va-mat-gateway-10-09.md`: tách rõ phần **chứng minh được** khỏi phần **suy luận**
- [x] 6.2 Ghi vào tài liệu bàn giao rằng agent CRM nay **có giữ khoá nhà cung cấp**, nên tính chất
      "đi qua Gateway là bắt buộc về mặt kỹ thuật" trong
      `gateway-architecture-and-agent-integration.md` mục 1 **không còn đúng** cho agent này
- [x] 6.3 Mở một ô việc cho lúc lên server: xin khoá thuộc `crm-500509` để phí về đúng project.
      Ghi kèm ba project id đang cùng tồn tại trong câu chuyện này
- [x] 6.4 Ghi hai câu hỏi còn treo vào phần "chưa chứng minh được": lỗi quá hạn mức có nên đổi
      đường không, và mã project `60854134008` ứng với project id nào

## 7. Bản chạy thử không đụng SharePoint — mở rộng phạm vi, chốt 12/09

Anh Tuấn chọn hướng này để đóng ô 5.3 và 5.6 mà không phải chạy pipeline thật. Pipeline thật
**không có cờ chạy khô**: bật lên là tải SharePoint thật, ghi đè tệp Excel thật, và gửi thư cho
người thật.

- [x] 7.1 Viết bản chạy thử đọc `sample_data/CRM_merge_sample.xlsx`, đi qua đúng tầng
      `call_llm_batch` và đúng cơ chế checkpoint của pipeline, nhưng **không** chạm SharePoint
      và **không** gửi thư kết quả
- [x] 7.2 Chạy với Gateway sống, ghi lại số dòng vào và số dòng ra làm mốc
- [x] 7.3 Chạy lại lần hai trên cùng checkpoint, khẳng định **không dòng nào được ghi sổ hai
      lần** — đóng ô 5.3. Phép kiểm phải đếm số lần mỗi dòng được GHI, không phải đếm số bản ghi
      trong sổ: sổ là một `dict` nên điều đó đúng bằng cấu trúc
- [x] 7.4 Chạy với fallback bật và Gateway bị cắt giữa chừng, khẳng định không dòng nào mất.
      **Không đóng được ô 5.6** như dự tính ban đầu: file mẫu chỉ có 3 dòng nên đây là một lô,
      không phải lô cỡ thật. Nó chứng minh cơ chế, không chứng minh sức chịu.
