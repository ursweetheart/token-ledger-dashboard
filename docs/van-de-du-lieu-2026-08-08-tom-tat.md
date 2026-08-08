# Tóm tắt: Các vấn đề dữ liệu hiện tại

> **Lưu ý:** Đây là bản tóm lược để nắm bắt nhanh tình hình ("nắm được đại khái vấn đề"). Để xem chi tiết bằng chứng và lập luận, vui lòng đọc file gốc: `van-de-du-lieu-2026-08-08.md` — mỗi mục dưới đây đều có mã (A1, B3…) trỏ thẳng tới phần tương ứng trong file đó.

Dữ liệu đang đến từ 3 nguồn: **API ứng dụng** (biết ai dùng), **Google Billing** (chân lý về tiền thật) và **Google Monitoring** (chân lý về lượt gọi, độ trễ). Hầu hết vấn đề sinh ra ở chỗ 3 nguồn này **lệch nhau hoặc bị khuyết**.

Tổng cộng **22 vấn đề**: 4 nghiêm trọng, 8 trung bình, 10 nhẹ.

---

## 🔴 1. Các vấn đề nghiêm trọng (cần ưu tiên xử lý)

* **Dự án Ralli hoàn toàn không có đối chứng — `B1`, `B8`**
  * 44,7 triệu token của Ralli chỉ có số app tự khai, **không có hoá đơn Google nào** để đối chứng. Nếu app ghi thiếu như TLA Hợp đồng đang thiếu 17% thì cũng **không có cách nào phát hiện**.
  * Kéo theo: không có số lỗi, không có độ trễ. Trên dashboard, Ralli phải hiện `—` ở các cột này thay vì `0%` — vì "không đo được" khác hẳn "không có lỗi".
  * **Hành động:** bật xuất billing cho dự án Ralli trên Google.

* **Không biết ai đang dùng — `B3`, `B4`, `A3`**
  * **Ralli:** 88% bản ghi ghi dưới tên `system`, chỉ **3,3% dòng** tra ngược ra được tài khoản có thật. Kéo theo 97% token không biết thuộc phòng nào. Dashboard Ralli **không thể trả lời** câu hỏi "ai dùng nhiều nhất".
  * **TLA Hợp đồng:** 53,6% token rơi vào đúng **2 tài khoản** — `admin` và `Test1`. Đây không phải dữ liệu vô danh, chỉ là 2 tài khoản chưa được gán phòng ban.
  * ⚠️ **Lưu ý quan trọng:** nếu `admin` hoá ra là tài khoản kỹ thuật dùng chung, thì câu trả lời đúng là **loại 53,6% này ra khỏi thống kê người dùng**, chứ không phải phân về phòng nào cả. Tổng chi phí không đổi, nhưng bức tranh "ai đang dùng" đổi hoàn toàn.

* **TLA Hợp đồng lệch hẳn so với Google — `A1`, `A2`**
  * App ghi **thiếu 17%** lượt gọi so với Google. Đáng chú ý: 342 lượt Google ghi nhận **đều trả về mã 200**, nên phần thiếu là lượt gọi **thành công bị bỏ sót**, không phải lỗi.
  * Giai đoạn **tháng 3 đến tháng 6** có lưu lượng trên app nhưng Google không có bản ghi nào — vì dự án Google chỉ được tạo ngày **20/06/2026**. Nếu để nguyên, dashboard sẽ hiện chi phí **gấp 4,4 lần** hoá đơn thật.
  * **Hướng xử lý (đã chốt):** lấy tổng theo Google, chia nhỏ theo app. Bỏ toàn bộ dữ liệu tháng 3–6.

---

## 🟠 2. Các vấn đề trung bình

* **Dữ liệu giám sát đang rụng dần — `D2`**
  * Google chỉ lưu **196 ngày**. Bản dữ liệu hiện có đã kịch trần: sớm nhất là 22/01/2026, và **không có cách nào lấy được gì cũ hơn**.
  * Mỗi ngày trôi qua mất thêm một ngày ở đuôi. Bản đang có là bản đầy đủ nhất sẽ từng có.
  * Riêng độ trễ (p95/p99) chỉ có từ 01/05 — biểu đồ trước mốc đó sẽ trống, đó là giới hạn của nguồn.

* **TLA Hợp đồng không có dữ liệu từng lượt gọi — `A3`, `A4`**
  * Ứng dụng chỉ trả về bảng đã cộng sẵn, không có endpoint nào cho từng lượt gọi.
  * Hệ quả: hai phát hiện `A3` và `A4` chỉ chứng minh được **ứng dụng tự mâu thuẫn với chính nó**, chưa chứng minh được gì về dữ liệu bên dưới. Vẫn có giá trị, nhưng cần nói rõ mức độ chắc chắn khi đưa vào báo cáo.

* **Hoá đơn TLA Hợp đồng chỉ có 9 ngày — `A5`**
  * Không đủ để dựng xu hướng theo tuần/tháng. Muốn vẽ biểu đồ thời gian thì phải dùng số app — mà app đang thiếu 17%.

* **App tự tính tiền và tính sai — `A6`**
  * App trả về sẵn cột chi phí, nhưng lệch **−10,5% đến −14,6%** so với hoá đơn thật. **Không được dùng cột tiền của app** — phải tính lại từ token nhân bảng giá suy từ hoá đơn.

* **Dữ liệu Ralli có 3 định dạng trong cùng một bảng — `B2`**
  * 6.871 dòng có 8 trường, 542 dòng có 14, 511 dòng có 16. Chỉ **8 trường** chung cho cả ba.
  * Mọi phép tính dùng trường ngoài 8 trường đó **chỉ đúng cho 13% dữ liệu**. Ví dụ cụ thể: lấy trung bình `cached_tokens` trên cả bảng sẽ **sai 7,5 lần**.
  * Khi đổ sang database, các ô này **bắt buộc là `NULL`, không được điền `0`** — vì `0` nghĩa là "đo được và bằng không", còn `NULL` là "không đo".

* **Có 11 dự án Google nhưng chỉ 7 dự án có dữ liệu — `D1`**
  * Hai dự án chưa được tính đến: `tla-ralli` và `gen-lang-client-0247490857` (tên do Google AI Studio tự sinh khi ai đó tạo khoá API nhanh). Có khả năng đang tồn tại lưu lượng **không nằm trong bất kỳ báo cáo nào**.

* **Hai dự án có dấu hiệu đã ngừng — `C3`**
  * `tool-quiz` không phát sinh chi phí từ 30/06 (cả đời chỉ có 8 dòng / 4 ngày). `Multi-model-invoice` dừng từ 25/07.
  * Nếu hiển thị lẫn với dự án đang chạy, người xem sẽ hiểu nhầm là "chi phí giảm mạnh" thay vì "không còn dùng".

---

## 🟡 3. Các vấn đề nhẹ (cần biết để không tính sai)

* **Số request theo model là ước lượng — `D3`.** Google không gắn nhãn model vào phép đo request, nên con số này đúng ở mức tổng nhưng là ước lượng ở mức chia nhỏ. Cần ghi rõ trên dashboard.
* **File mô tả cấu trúc bảng mô tả sai 87% dữ liệu — `D6`.** Nó chỉ quét 100 bản ghi mới nhất rồi suy ngược ra, nên khai 16 trường trong khi phần lớn dữ liệu chỉ có 8. **Không được dùng file này để thiết kế bảng database.**
* **Phạm vi hoá đơn giữa các dự án lệch nhau rất xa — `C2`.** Từ 4 ngày đến 214 ngày. **Không so sánh trực tiếp tổng cả năm giữa các dự án được**, phải quy về cùng kỳ.
* **API bỏ qua tham số truy vấn — `B6`.** Xin 100 bản ghi thì trả về 1.000; lọc theo ngày thì bị bỏ qua. Không thể lấy dữ liệu theo khoảng thời gian, và **quá khứ không lấy lại được**.
* **Kiểu dữ liệu tiền không nhất quán — `D7`.** TLA Hợp đồng lưu tiền kiểu chuỗi, Ralli kiểu số thực. Mọi script phải ép kiểu trước khi tính, nếu quên thì phép cộng cho ra kết quả trông giống số nhưng sai hoàn toàn.
* **Hai khoản lệch token nhỏ — `A4`, `B5`.** TLA Hợp đồng lệch 2.223 token (nhiều khả năng là *thinking token* mà app chưa có cột để lưu); Ralli lệch 162 token do lỗi phiên bản ghi log cũ, đã ngừng từ 23/06. Nhỏ về lượng nhưng chứng minh app đang thiếu một cột mà Google có tính tiền.
* **Thiếu 1 người dùng so với mục lục — `B7`.** Database khai 891 tài khoản, lấy về được 890.
* **6 agent nền chỉ có tiền, không có người dùng — `C1`.** Đã thống nhất chấp nhận: mỗi dự án tính là một agent, không phân cấp bên trong.

---

## ✅ 4. Những phần đã kiểm chứng là ĐÚNG

Để cân bằng — không phải mọi thứ đều có vấn đề:

| Phép kiểm | Kết quả |
|---|---|
| Dữ liệu thô Ralli ↔ thống kê ứng dụng | Khớp tuyệt đối (7.924 lượt · 44,7 triệu token) |
| Hoá đơn gộp ↔ 7 file thành phần | Khớp tuyệt đối ($270,95) |
| Giao diện web ↔ dữ liệu đã lấy về | 84 điểm khớp, 0 lỗi |
| Monitoring token ra ↔ hoá đơn token ra | Khớp tuyệt đối |

Con số 97% "không rõ phòng ban" của Ralli còn tính được bằng **hai đường độc lập** — đọc thẳng bảng thống kê, hoặc đi từ 7.924 bản ghi thô — và cho cùng kết quả. Nghĩa là nó **có thật trong dữ liệu thô**, không phải hệ quả của cách gom nhóm.

**Điểm cần nêu rõ trong báo cáo:** vấn đề nằm ở chỗ dữ liệu gốc vốn đã thiếu, không phải ở khâu lấy dữ liệu về.

---

## 📌 5. Câu hỏi cần trả lời ngay (chặn tiến độ)

1. Tài khoản `admin` của TLA Hợp đồng là tài khoản kỹ thuật dùng chung hay của một người cụ thể? *(quyết định 53,6% dữ liệu — xem lưu ý ở mục 🔴)*
2. Tỷ giá VNĐ lấy theo nguồn nào, cập nhật khi nào?
3. Ngân sách tháng của Ralli là bao nhiêu?
4. Ai chốt/duyệt bảng giá model?
5. Chốt danh sách 8 agent chính thức và project Google tương ứng — có bỏ `tool-quiz` không?

**Không chặn tiến độ nhưng cần biết:**

6. `user_id = 'system'` của Ralli là tác vụ nền hay giai đoạn chưa gắn theo dõi? *(quyết định 88% dữ liệu có được tính là lưu lượng người dùng thật không)*
7. Hai dự án `tla-ralli` và `gen-lang-client-*` có phục vụ nghiệp vụ thật không?
8. `test1` và `Test1` (khác đúng một chữ hoa) là hai tài khoản thật hay một tài khoản bị tạo trùng?
9. Năm tài khoản `test1`–`test4` và `Nghiệp vụ BH1` có phải tài khoản chạy thử không? Nếu phải thì có loại khỏi thống kê không?
10. Trường thời gian của Ralli là giờ UTC hay giờ Việt Nam?

---

## 🛠 6. Việc cần làm ngay

| # | Việc | Vì sao gấp |
|---|---|---|
| 1 | Sao lưu dữ liệu giám sát hiện có ra nơi an toàn | Bản duy nhất, đuôi rụng dần mỗi ngày (`D2`) |
| 2 | Hỏi về tài khoản `admin` | Quyết định 53,6% dữ liệu chỉ bằng một câu hỏi (`A3`) |
| 3 | Bật xuất billing cho dự án Ralli | Không có thì mọi số của Ralli không kiểm chứng được (`B1`) |
| 4 | Xác nhận `tool-quiz` và `Multi-model-invoice` đã dừng chưa | Tránh hiểu nhầm "chi phí giảm" (`C3`) |
| 5 | Xác nhận hai dự án Google chưa rõ | Có thể có lưu lượng ngoài mọi báo cáo (`D1`) |

> Ngoài ra còn một nhóm vấn đề **thuộc về script và cách làm việc của đội** (không phải khuyết tật dữ liệu) được ghi riêng ở `van-de-xu-ly-du-lieu-2026-08-08.md`. Nhóm đó đội **tự sửa được ngay**, không phải chờ ai trả lời — trong đó có một việc gấp hơn tất cả những việc trên vì liên quan đến nguy cơ mất dữ liệu vĩnh viễn.
