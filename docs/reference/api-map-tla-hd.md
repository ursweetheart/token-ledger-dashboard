# Bản đồ API — TLA Hợp Đồng

> Dò ngày 05/08/2026 bằng cách đọc network request của chính giao diện admin.
> Đây là **1 trong 8 agent**. Bảy agent còn lại chưa biết địa chỉ.

**Gốc:** `https://chatbothd.rangdong.com.vn:10001`

## Xác thực

```
Authorization: Bearer <JWT>
```

Máy chủ **không** chấp nhận cookie — mở thẳng URL API trong trình duyệt đang
đăng nhập trả về `{"detail":"Authentication required"}`.

JWT chứa: `sub`, `role`, `company_id`, `unit_id`, `username`, `exp`.
Token quan sát được có `exp` rất ngắn (~1 ngày) ⇒ **không dùng để tự động hoá**,
phải xin token dài hạn từ đơn vị làm phần mềm.

## Endpoint

| Method | Path | Trả về | Ghi chú |
|---|---|---|---|
| GET | `/api/admin/token-usage/stats?period=` | token · chi phí · lượt gọi · prompt · completion | ⭐ quan trọng nhất. `period` = `day`\|`week`\|`month`\|`year`. Giao diện còn lọc theo phòng ban + người dùng ⇒ nhiều khả năng nhận thêm `unit_id`/`user_id`/`from`/`to` (chưa xác minh) |
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

1. Token chỉ-đọc dài hạn cho `/api/admin/token-usage/stats` và `/api/units/tree`
2. Địa chỉ + tài khoản admin của **7 agent còn lại**
3. `/api/admin/token-usage/stats` có nhận `unit_id` / `user_id` / `from` / `to` không
4. Vì sao 59% token rơi vào "Chưa xác định"
5. Bản ghi user có trường `created_at` (thời gian được cấp) không — giao diện không hiện
