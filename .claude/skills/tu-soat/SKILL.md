---
name: tu-soat
description: Viết xong thì tự soát - chạy - sửa lặp lại cho đến khi sạch lỗi, trước khi báo là xong. Dùng khi tạo hoặc sửa script, hàm xử lý dữ liệu, truy vấn, pipeline - bất cứ thứ gì chạy được và có thể sai một cách âm thầm. Đặc biệt cần khi kết quả là số liệu, vì số sai vẫn trông như số đúng.
metadata:
  author: rangdong
  version: "1.0"
---

Viết xong **không phải là xong**. Xong là khi đã chạy sạch và bạn hiểu vì sao nó sạch.

Kỹ năng này là một vòng lặp. Không thoát ra cho đến khi đạt điều kiện dừng ở cuối tài liệu.

---

## Vòng lặp

```
   ① VIẾT      → ② TỰ ĐỌC LẠI → ③ CHẠY LÁT MỎNG → ④ PHÂN LOẠI → ⑤ SỬA
                       ↑                                              │
                       └──────────────────────────────────────────────┘
                          lặp cho đến khi không còn LỖI SCRIPT
                                        ↓
                               ⑥ CHẠY BẢN ĐẦY ĐỦ
```

### ① Viết

Viết hết, đừng viết một nửa rồi chạy thử. Vòng lặp bên dưới rẻ hơn nhiều so với việc viết dở dang.

### ② Tự đọc lại — trước khi chạy

**Bắt buộc.** Đọc lại toàn bộ code vừa viết và tìm lỗi bằng mắt, không chờ máy báo.

Máy chỉ báo lỗi làm chương trình dừng. Loại lỗi nguy hiểm hơn là loại chạy trót lọt và trả về số sai — bước này là chỗ duy nhất bắt được chúng.

Danh mục soát, theo thứ tự hay gặp:

- **Thứ tự ưu tiên toán tử.** `a + b if c else 0` — điều kiện nuốt cả tổng, không phải chỉ số hạng cuối.
- **Chia cho số có thể bằng 0.**
- **Truy cập khoá có thể không tồn tại.** Dữ liệu thật hiếm khi đồng đều. Dùng `.get()` thay vì `[...]` khi chưa chắc.
- **Biến bị ghi đè.** PowerShell không phân biệt hoa thường: `$d` xoá mất `$D`.
- **Vòng lặp lồng ẩn.** Dựng `set(...)` bên trong một generator = dựng lại ở mỗi vòng.
- **So sánh số thực bằng `==`.** Tiền và số thập phân phải có dung sai.
- **Mã hoá ký tự.** BOM, UTF-8 vs codepage hệ thống, dấu tiếng Việt trong chính file script.
- **Rò rỉ tài nguyên.** Mở file mà không đóng.

Sửa hết những gì tìm được **rồi mới** chạy.

### ③ Chạy lát mỏng nhất trước

Đừng chạy ngay bản đầy đủ. Chạy phần rẻ nhất mà vẫn đi qua được nhiều nhánh code nhất.

Nếu công việc có phần nặng — file lớn, gọi mạng, truy vấn tốn kém — thì ngay từ bước ① phải để sẵn một cờ để bỏ qua phần đó. Vòng lặp cần **quay vòng trong vài giây**, không phải vài phút. Một vòng lặp chậm sẽ khiến bạn bỏ cuộc sớm.

### ④ Phân loại kết quả — bước quan trọng nhất

Mỗi lần chạy thất bại đều thuộc đúng **một** trong hai loại. Nhầm loại là hỏng cả việc.

| | **LỖI SCRIPT** | **PHÁT HIỆN THẬT** |
|---|---|---|
| Nghĩa là | Code tôi viết sai | Code đúng, **dữ liệu** có vấn đề |
| Phải làm | Sửa code | **Giữ nguyên**, ghi lại, báo cáo |
| Dấu hiệu | Crash, kiểu dữ liệu sai, chỉ số vượt biên | Số cộng không khớp, thiếu bản ghi, giá trị vô lý |

**Luật tuyệt đối: không bao giờ nới lỏng phép kiểm để nó qua.**

Nếu một phép kiểm báo lỗi và câu trả lời của bạn là hạ ngưỡng, thêm dung sai, hay bọc `try/except` cho nó im — dừng lại. Bạn vừa định xoá đúng cái thứ mà công cụ này sinh ra để tìm.

Chỉ được sửa phép kiểm khi chứng minh được **bản thân phép kiểm sai**, không phải khi dữ liệu không vừa ý nó.

Ví dụ thật, từ chính lần chạy sinh ra tài liệu này:

```
  KeyError: 'cached_tokens'
```

Đọc vội thì đây là lỗi script — thì thêm `.get()` là xong. Nhưng lý do khoá đó vắng mặt là **6.871/7.924 bản ghi thật sự không có trường đó**. Hai việc phải làm, không phải một:

1. Sửa cách đọc để không sập  ← lỗi script
2. **Thêm hẳn một phép kiểm mới** đếm xem trường nào thiếu ở bao nhiêu dòng  ← phát hiện thật

Chỉ làm việc (1) là đã âm thầm giấu đi một phát hiện quan trọng.

Khi gặp phát hiện thật, thường phải **thêm phép kiểm để khoanh vùng nó**: lệch nằm ở đâu, bao nhiêu dòng, mỗi dòng lệch bao nhiêu, phân bố có đều không. "Lệch 162 token" gần như vô dụng. "Đúng 81 dòng, mỗi dòng đúng 2 token, toàn bộ trên một model" thì chỉ ra ngay nguyên nhân.

### ⑤ Sửa rồi quay lại ②

Sau mỗi lần sửa, **đọc lại đoạn vừa sửa**. Sửa cũng sinh lỗi mới.

Cảnh giác nhất với sửa hàng loạt: thay thế theo mẫu trên cả file rất dễ đụng vào chỗ không định đụng. Sau khi thay thế hàng loạt, luôn kiểm cú pháp lại trước khi chạy.

### ⑥ Chỉ khi lát mỏng đã sạch — chạy bản đầy đủ

Phần nặng sẽ lộ ra những thứ mà lát mỏng không có: dữ liệu nhiều dạng hơn, giới hạn bộ nhớ, thời gian chạy. Nếu bản đầy đủ hỏng, quay về ④, không quay về ①.

---

## Điều kiện dừng

Được phép dừng khi **cả ba** cùng đúng:

1. Không còn LỖI SCRIPT
2. Mọi PHÁT HIỆN THẬT đã được ghi lại kèm số liệu định lượng, không phép nào bị nới lỏng
3. Đã chạy bản đầy đủ, không phải chỉ lát mỏng

Phải dừng và hỏi người dùng khi:

- **Cùng một lỗi xuất hiện lần thứ ba.** Vòng lặp không hội tụ. Đang hiểu sai vấn đề, sửa thêm chỉ tốn công.
- **Việc sửa đòi hỏi thay đổi phạm vi.** Ví dụ phải kéo thêm dữ liệu, phải xin thêm quyền.
- **Không phân loại được** một kết quả là lỗi script hay phát hiện thật.

Ba trường hợp này **không phải thất bại**. Dừng đúng lúc tốt hơn nhiều so với lặp mù.

---

## Báo cáo khi xong

Không chỉ nói "đã xong". Nói ba điều:

1. **Đã sửa những lỗi script nào** — ngắn gọn, mỗi lỗi một dòng
2. **Tìm ra những phát hiện thật nào** — đây mới là giá trị của việc làm này
3. **Còn gì chưa chắc chắn** — cái gì chứng minh được, cái gì mới chỉ là suy luận

Phân biệt **chứng minh được** với **suy luận** rất quan trọng. Ví dụ: "API dùng nguyên giá trị lưu" là chứng minh được — khớp 6/6 mốc, giả thuyết kia khớp 0/6. Còn "giá trị lưu là UTC" là suy luận — dựa trên việc không ai dùng chatbot công ty lúc 1 giờ sáng. Cái thứ nhất ghi ĐẠT, cái thứ hai ghi CẢNH BÁO và kèm câu cần hỏi ai.

Trộn hai loại đó với nhau là làm người đọc tin nhầm mức độ chắc chắn.

---

## Ba lỗi thường gặp khi áp dụng

**Bỏ bước ②.** Chạy luôn cho nhanh, để máy báo lỗi. Kết quả là chỉ bắt được lỗi làm chương trình dừng, còn lỗi trả số sai thì lọt hết. Đây là lỗi tốn kém nhất.

**Nới phép kiểm cho qua.** Đã nói ở ④, nhưng nhắc lại vì đây là cám dỗ mạnh nhất khi đã mệt.

**Dừng ở lát mỏng.** "Chạy phần nhẹ ổn rồi, chắc phần nặng cũng ổn." Phần nặng là nơi có dữ liệu bất thường.
