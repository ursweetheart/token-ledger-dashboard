# API phải hỏi một khoá trước khi trả dữ liệu

## Why

`backend/main.py` có **8 endpoint** và **không một dòng nào kiểm danh tính**:

```
$ grep -n "Depends\|Authorization\|api_key" backend/main.py
(khong co ket qua)
```

`/api/accounts` trả về **937 tài khoản** kèm họ tên, phòng ban, đường dẫn đơn vị, vai trò,
ngày tạo. Bất kỳ ai gọi được máy chủ đều lấy được toàn bộ.

Hôm nay an toàn **chỉ vì** uvicorn gắn `127.0.0.1`. Đó là một dòng cấu hình, không phải
một cơ chế. Kiến trúc Gateway có load balancer, 2+ server và Redis — tức là hệ thống
**ra mạng**, và lúc đó dòng cấu hình kia đổi.

### CORS đã siết hôm 20/08 **không** đóng được lỗ này

Đây là chỗ dễ tưởng nhầm là đã xong. Commit `c3d7169` đổi `allow_origins=["*"]` thành đọc
từ `DASHBOARD_ORIGINS`. Việc đó đúng và cần, nhưng:

```
   CORS là luật của TRÌNH DUYỆT, không phải của máy chủ.

   trang web lạ  ──▶  trình duyệt chặn        ✅ CORS bảo vệ được
   curl / script ──▶  KHÔNG đọc CORS bao giờ  ❌ CORS không thấy gì
```

Máy chủ vẫn **trả đủ dữ liệu** trong cả hai trường hợp; CORS chỉ khiến trình duyệt vứt
câu trả lời đi. Một dòng `curl` lấy trọn 937 người, hôm qua cũng như hôm nay.

### Vì sao khoá dùng chung, không phải JWT theo người

Quyết định 21/08. Master Plan giai đoạn 3 yêu cầu *"JWT đăng nhập Dashboard… áp dụng cho
Admin / User xem báo cáo"*. Nhưng:

| | |
|---|---|
| Số endpoint | 8 |
| Số endpoint là `GET` | **8** |
| Hành động đặc quyền (sửa, xoá, đổi hạn mức) | **0** |
| Kho người dùng của dashboard | **không có** — `account` có `username` nhưng **không có cột mật khẩu**, và không có bảng nào khác |

**Không có gì để phân biệt thì phân biệt bây giờ là viết code không dùng tới.** Ngày
dashboard có nút đổi hạn mức thì mới cần phân vai — và thiết kế dưới đây khiến lúc đó chỉ
phải sửa **một hàm**.

Nói thẳng phần khoá dùng chung **không** cho:

| | Khoá dùng chung |
|---|---|
| Chặn người lạ đọc 937 họ tên + phòng ban | ✅ đây là rủi ro thật của C1 |
| Biến "an toàn vì bind 127.0.0.1" thành một cơ chế | ✅ |
| Biết **ai** đã xem gì | ❌ không có nhật ký theo người |
| Thu hồi quyền **một người** | ❌ đổi khoá là đá văng tất cả |
| Phân biệt Admin / User | ❌ |

## What Changes

- **`Depends(nguoi_goi)`** trên cả 8 endpoint. Hàm này trả về một **`Principal`**, không
  trả `True` — ngày lên JWT chỉ sửa hàm đó, 8 endpoint không đụng một chữ
- **Header `Authorization: Bearer <khoá>`** — không đặt tên riêng kiểu `X-Dashboard-Key`,
  vì khi lên JWT header **không đổi tên**, chỉ đổi thứ nằm sau chữ `Bearer`. Frontend viết
  một lần
- **So khoá bằng `secrets.compare_digest`**, không dùng `==`
- **Thiếu cấu hình thì KHÔNG khởi động được.** `DASHBOARD_KEY` chưa đặt → uvicorn từ chối
  chạy, in rõ lý do. Muốn tắt xác thực lúc phát triển thì phải gõ `DASHBOARD_OPEN=1` —
  tức phải **khai ra ý định**, không tắt được bằng cách quên
- **Frontend**: ô nhập khoá, lưu `localStorage`, gắn header ở `web/js/api.js:62` —
  **điểm `fetch()` duy nhất trong toàn bộ `web/`**
- **401 thành một loại lỗi riêng** trong `makeError()`, phân biệt với *"chưa bật backend"*
- **`backend/check_api.py`** gửi kèm khoá, và thêm một phép kiểm: gọi **không** khoá phải
  bị từ chối

**KHÔNG làm trong change này**

- Không dựng JWT theo người, không dựng kho người dùng, không nhật ký truy cập
- Không giới hạn tốc độ gọi
- Không đụng `db/` hay `scripts/` — không rebuild database
- Không đổi CORS. `allow_headers=["*"]` hiện tại đã cho phép header `Authorization` đi qua

## Impact

| | |
|---|---|
| **Specs** | `api-access-control` (mới) |
| **Code** | `backend/main.py` · `backend/check_api.py` · `web/js/api.js` · `web/js/app.js` · `web/index.html` · `tests/load-failure-states.test.js` · `.env.example` · `tools/soat_khoa_api.py` (mới) |
| **Không đụng** | `db/` · `scripts/` · `backend/store.py` — không rebuild |
| **Rủi ro** | **Thấp về dữ liệu, trung bình về vận hành.** Không con số nào đổi. Nhưng làm sai phần cấu hình thì hoặc *không ai vào được*, hoặc tệ hơn: *chạy mở mà tưởng đã khoá* — task 2.4 và 5.2 nhắm đúng vế thứ hai |
| **Đồng nghiệp** | Sau change này họ cần `DASHBOARD_KEY` trong `.env`. Phải ghi vào `.env.example` và tài liệu đồng bộ, nếu không họ pull về và dashboard trắng |
| **Quay lui** | Một commit backend, một commit frontend. Đặt `DASHBOARD_OPEN=1` là trở về hành vi cũ mà không cần quay lui code |

### Cái bẫy chính của change này

Chế độ hỏng phải là **"không khởi động được"**, tuyệt đối không phải **"khởi động ở chế độ
mở"**. Nếu quên đặt biến môi trường mà máy chủ vẫn chạy bình thường, ta có đúng thứ đang
có hôm nay — cộng thêm niềm tin sai rằng đã khoá. Đó cùng một hạng lỗi với mọi thứ đã sửa
ngày 20/08: sai một cách im lặng.
