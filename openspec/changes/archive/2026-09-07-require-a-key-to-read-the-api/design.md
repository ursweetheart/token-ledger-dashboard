# Thiết kế — API phải hỏi một khoá trước khi trả dữ liệu

> Viết lại 07/09/2026, sau khi change đã thực thi xong. Mọi quyết định dưới đây được rút từ
> `proposal.md` và từ dấu vết đo đạc trong `tasks.md`, không có mục nào viết thêm cho đẹp
> hồ sơ. Bốn quyết định đầu chốt lúc thiết kế; hai quyết định cuối (§5, §6) là **kết quả của
> vòng tự soát**, tức lúc bắt đầu không ai biết là cần.

## Bối cảnh

`backend/main.py` có 8 endpoint và không dòng nào kiểm danh tính. `/api/accounts` trả về
937 tài khoản kèm họ tên, phòng ban, đường dẫn đơn vị, vai trò, ngày tạo.

Điều giữ cho nó an toàn tới hôm nay là uvicorn gắn `127.0.0.1` — **một dòng cấu hình, không
phải một cơ chế**. Kiến trúc Gateway sắp tới có load balancer, 2+ máy chủ và Redis, tức hệ
thống ra mạng, và lúc đó dòng cấu hình kia đổi.

Chỗ dễ tưởng nhầm là đã xong: CORS siết hôm 20/08 (`c3d7169`) **không** đóng được lỗ này.

```
   CORS là luật của TRÌNH DUYỆT, không phải của máy chủ.

   trang web lạ  ──▶  trình duyệt chặn        ✅ CORS bảo vệ được
   curl / script ──▶  KHÔNG đọc CORS bao giờ  ❌ CORS không thấy gì
```

Máy chủ vẫn trả đủ dữ liệu trong cả hai trường hợp; CORS chỉ khiến trình duyệt vứt câu trả
lời đi. Một dòng `curl` lấy trọn 937 người.

## Mục tiêu

- Biến "an toàn vì bind `127.0.0.1`" thành một cơ chế thật
- Không con số nào trên dashboard đổi
- Ngày lên JWT theo người chỉ phải sửa **một hàm**, không phải 8 endpoint

## Không làm

JWT theo người · kho người dùng · nhật ký truy cập · giới hạn tốc độ gọi · đụng vào `db/`
hay `scripts/` · đổi CORS.

## Quyết định

### 1. Khoá dùng chung, không phải JWT theo người

Master Plan giai đoạn 3 yêu cầu JWT phân vai Admin/User. Đo lại hiện trạng thì yêu cầu đó
chưa có gì để bám vào:

| | |
|---|---|
| Số endpoint | 8 |
| Số endpoint là `GET` | **8** |
| Hành động đặc quyền (sửa, xoá, đổi hạn mức) | **0** |
| Kho người dùng của dashboard | **không có** — `account` có `username` nhưng **không có cột mật khẩu** |

Không có gì để phân biệt thì phân biệt bây giờ là viết code không dùng tới.

**Nói thẳng phần khoá dùng chung không cho**, để người sau không tưởng đây là đã xong:
không biết *ai* đã xem gì · không thu hồi được quyền của **một** người (đổi khoá là đá văng
tất cả) · không phân vai. Ba dòng này đã ghi vào `viec-can-lam-truoc-api-gateway.md`.

### 2. Hàm phụ thuộc trả `Principal`, không trả `True`

`Depends(nguoi_goi)` trên cả 8 endpoint, và hàm đó trả về một **`Principal`** chứ không trả
giá trị đúng/sai.

Lý do: đây chính là chỗ khiến quyết định ① không thành nợ. Ngày lên JWT, thứ phải sửa là
*ai gọi* — nếu tầng phụ thuộc chỉ trả `True/False` thì 8 endpoint phải sửa lại để biết chủ
thể. Trả sẵn một chủ thể ngay từ hôm nay thì lúc đó chỉ đổi ruột **một hàm**.

### 3. `Authorization: Bearer`, không đặt tên header riêng

Không dùng `X-Dashboard-Key`. Khi lên JWT, header **không đổi tên** — chỉ đổi thứ nằm sau
chữ `Bearer`. Frontend viết một lần, không phải sửa lại lần thứ hai.

### 4. Chế độ hỏng phải là "không khởi động được"

Đây là cái bẫy chính của change. Thiếu `DASHBOARD_KEY` → uvicorn **từ chối chạy** và in rõ
lý do. Muốn tắt xác thực lúc phát triển phải gõ hẳn `DASHBOARD_OPEN=1`.

Lý do: nếu quên đặt biến mà máy chủ vẫn chạy bình thường, ta có đúng thứ đang có hôm nay —
cộng thêm niềm tin sai rằng đã khoá. **Tắt được bằng cách quên là chế độ hỏng tệ nhất; tắt
phải là một hành động khai ra ý định.**

### 5. So chứng danh trên `bytes`, không phải trên `str`

Bản đầu dùng `secrets.compare_digest` với hai chuỗi `str`. Vòng tự soát bắt được:
**`compare_digest` ném `TypeError` khi chuỗi có ký tự ngoài ASCII**, nên một header
`Authorization: Bearer á` làm **mọi endpoint trả 500** — tức gọi được máy chủ vào trạng thái
hỏng mà không cần biết khoá.

Đã đổi sang so trên `bytes`, thêm kịch bản vào spec, và **kiểm ngược**: gỡ bản sửa ra thì
phép kiểm đứt cả kết nối. Đây là quyết định không ai nghĩ ra lúc thiết kế — nó đến từ việc
chạy thử với dữ liệu xấu.

### 6. Khoá cất theo từng địa chỉ, không dùng chung một ô

Tham số `?api=` vốn vô hại: nó chỉ đổi *chỗ đọc dữ liệu*. Nhưng từ lúc trình duyệt bắt đầu
giữ một bí mật, chính nó đổi luôn *chỗ gửi bí mật* — ai dụ được người dùng mở dashboard với
`?api=<địa chỉ lạ>` là lấy được khoá.

Đã cất khoá **theo từng địa chỉ** (`localStorage` khoá theo origin đích), thêm phép kiểm, và
kiểm ngược: quay lại một-khoá-dùng-chung thì phép kiểm báo *"khoá đã bị gửi sang địa chỉ
lạ"*.

Hệ quả kèm theo, có chủ ý: **khoá không bao giờ đi qua URL**. `api.js` cố ý không có dòng
nào đọc `?key=` — khoá vào URL là khoá nằm trong log máy chủ, xoá không lại được.

## Rủi ro và đánh đổi

**CORS preflight — rủi ro do chính change này đẻ ra.** Thêm header `Authorization` biến mọi
request thành *non-simple*, nên từ nay Chrome gửi một `OPTIONS` đi trước mỗi lần tải trang.
Không phép kiểm cũ nào chạm tới việc này. Đã đo tay **8/8**: preflight qua được từ cả hai
origin mặc định · `Authorization` được cho đi qua · preflight **không** bị tầng xác thực
chặn (trình duyệt không bao giờ gắn khoá vào `OPTIONS`) · origin lạ vẫn bị từ chối.

**Đồng nghiệp pull về sẽ thấy dashboard trắng** nếu không có `DASHBOARD_KEY` trong `.env`.
Đã ghi vào `.env.example` và `dong-bo-may-dong-nghiep-*.md`, kèm bảng bốn triệu chứng.

**Bộ kiểm gọi máy chủ đang chạy không thay được bộ kiểm tĩnh.** `check_api.py` vẫn xanh nếu
ai đó gỡ mất cái chặn rồi khởi động lại ở chế độ mở. Nên `tools/soat_khoa_api.py` được đưa
hẳn vào repo chứ không để ở thư mục tạm: nó dựng uvicorn thật **không cần Docker** và đo
được rằng `main.py` import xong mà chưa chạm database (`store.open_db()` chỉ chạy trong
thân endpoint, còn 401 chặn ở tầng phụ thuộc — tức TRƯỚC thân). **24/24.**

**Rủi ro vận hành ở mức trung bình, rủi ro dữ liệu ở mức thấp.** Không con số nào đổi. Nhưng
làm sai phần cấu hình thì hoặc *không ai vào được*, hoặc tệ hơn — *chạy mở mà tưởng đã khoá*.

## Câu còn mở

Không còn. Mục cuối cùng (5.4 — xác nhận frontend đã đổi, không phải bản trong bộ đệm) đã
đo trên Chrome thật ngày 07/09/2026: nạp lại cứng, **13 request và không request nào đi tới
backend khi chưa nhập khoá**; `/api/usage`, `/api/accounts`, `/api/catalog` đều trả **401**
khi gọi không mang khoá.

Ba thứ change này **cố ý không làm** — nhật ký theo người, thu hồi quyền một người, phân vai
Admin/User — không phải câu hỏi mở mà là phạm vi đã chốt ở quyết định ①. Chúng chỉ trở thành
việc khi dashboard có hành động đặc quyền đầu tiên.
