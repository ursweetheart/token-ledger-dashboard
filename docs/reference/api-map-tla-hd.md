# Bản đồ API — TLA Hợp Đồng

> Dò ngày 05/08/2026 bằng cách đọc network request của chính giao diện admin.
> Cập nhật 16/08/2026 — bốn mục từng ghi "chưa xác minh" nay đã có câu trả lời,
> đánh dấu ✅ bên dưới.
>
> Đây là **1 trong 8 agent**. Tính cả Trợ lý ảo Ralli thì đã biết địa chỉ **2/8**;
> sáu agent còn lại vẫn chưa. Cả hai đều được `scripts/pull_web_apps.py` gọi.

**Gốc:** `https://chatbothd.rangdong.com.vn:10001`

## Xác thực

```
Authorization: Bearer <JWT>
```

Máy chủ **không** chấp nhận cookie — mở thẳng URL API trong trình duyệt đang
đăng nhập trả về `{"detail":"Authentication required"}`.

JWT chứa: `sub`, `role`, `company_id`, `unit_id`, `username`, `exp`.
Token quan sát được có `exp` rất ngắn (~1 ngày).

✅ **Đã giải quyết theo hướng khác, không cần token dài hạn.** Đường ống tự đăng
nhập bằng `POST /auth/login` mỗi lần chạy rồi vứt token đi — xem
[`huong-dan-cap-nhat-dashboard.md`](huong-dan-cap-nhat-dashboard.md#kỷ-luật-chỉ-đọc).
Đây là **ngoại lệ POST duy nhất** được cho phép; mọi endpoint dữ liệu vẫn là GET
trên danh sách trắng khai báo cứng. Token không bao giờ in ra màn hình hay ghi
xuống đĩa.

## Endpoint

| Method | Path | Trả về | Ghi chú |
|---|---|---|---|
| GET | `/api/admin/token-usage/stats?period=` | token · chi phí · lượt gọi · prompt · completion | ⭐ quan trọng nhất. ✅ Đã dò xong tham số — xem bảng ngay dưới |
| GET | `/api/units/tree` | cây tổ chức, 20 đơn vị, 3 cấp | thay `ORG_UNITS` hardcode |
| GET | `/api/units/{uuid}/members` | thành viên của 1 đơn vị | tên · vai trò · email · SĐT |
| GET | `/api/history/sessions` | 181 phiên chat | mỗi phiên có `Người tạo (@username)` |
| GET | `/api/history/sessions/{id}/messages` | tin nhắn trong phiên | chưa xác minh có trường token hay không |
| GET | `/api/dashboard/stats?period=30d` | KPI tổng quan | |
| GET | `/api/projects` | ~100 hợp đồng, trạng thái 🟢/🔴 | |
| GET | `/api/presence/online-count` | số người đang online | |
| POST | `/api/presence/heartbeat` | — | app tự gọi định kỳ, không cần dùng |
| GET | `/api/permissions/me` | quyền của tài khoản hiện tại | kiểm quyền trước khi gọi |
| GET | `/api/notifications?limit=` | thông báo | |
| GET | `/api/notifications/stream?token=<JWT>` | SSE | ⚠️ endpoint duy nhất nhận JWT qua query string |

### Tham số của `/api/admin/token-usage/stats` — đã dò tay 14/08

| Cách gọi | Kết quả |
|---|---|
| `?period=custom&date_from=A&date_to=B` | ✅ **Được.** Trả đúng khoảng xin |
| `?period=day&date=…` | ❌ Bị **bỏ qua im lặng**, trả về hôm nay |
| `?date_from=…&date_to=…` (thiếu `period`) | ❌ Bị bỏ qua, trả về cả tháng |
| `&user_id=<uuid>` | ✅ **Được.** Khớp chính xác `by_user` |

⚠️ **Tham số lạ không báo lỗi — nó bị bỏ qua và máy chủ vẫn trả 200.** Nghĩa là gọi
sai vẫn nhận được số liệu trông hợp lệ nhưng của khoảng khác. `pull_hd_usage.py` vì
thế kiểm lại `date_from`/`date_to` trong phản hồi và ném lỗi nếu không khớp yêu cầu.

Một chi tiết dễ đọc nhầm: **`by_model` nằm trong khối `costs`, không ở gốc phản hồi.**
Đọc sai chỗ sẽ thấy "0 model" ở mọi dòng và tưởng API không hỗ trợ chiều model.

Chi tiết đầy đủ: docstring của `scripts/pull_hd_usage.py`.

## Vai trò

`ADMIN` · `COMPANY_ADMIN` · `UNIT_LEAD` · `MEMBER`
(màn hình Phân quyền còn cột "Thư ký" nhưng chưa ai được gán)

## Số liệu quan sát được (tháng 08/2026)

```
$8,0661   tổng chi phí — "USD theo catalog" (TỰ NHÂN token × giá,
          KHÔNG phải tiền thật của Google, không trừ cached token)
3,44M     tổng token
155       lượt gọi
2,88M     prompt (token vào)
552,47K   completion (token ra)
3.436.267 / 200.000.000 = 1,7% hạn mức token/tháng
```

Token theo phòng ban: **Chưa xác định 2,02M (59%)** · TT C4LED 963K · Phòng BH3 452K
⇒ hơn nửa lưu lượng chưa gán được phòng ban, cần hỏi lại nhà cung cấp.

## Việc cần hỏi đơn vị làm phần mềm

**Còn phải hỏi:**

1. Địa chỉ + tài khoản admin của **6 agent còn lại** (đã có TLA HĐ và Ralli)
2. Vì sao 59% token rơi vào "Chưa xác định"

**Đã tự trả lời được, không cần hỏi nữa:**

3. ✅ ~~Token chỉ-đọc dài hạn~~ — đường ống tự đăng nhập mỗi lần chạy, xem §Xác thực
4. ✅ ~~`stats` có nhận `unit_id`/`user_id`/`from`/`to` không~~ — xem bảng tham số ở trên
5. ✅ ~~Bản ghi user có `created_at` không~~ — **có**. Database hiện có
   `account.created_at`, phủ 891/953 tài khoản; 62 tài khoản còn NULL là nhóm đến từ
   nguồn Ralli, vốn không xuất cột ngày cấp
