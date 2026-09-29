## Why

Hạn mức của một Virtual Key do tab **Kết nối agent** cấp hiện sửa được ở **hai** nơi, với hai quyền
khác nhau, và hai nơi không biết về nhau.

- Tab **Kết nối agent** sửa qua worker, cần **khoá quản trị** (`CONNECTION_ADMIN_KEY`), ghi audit, và
  lưu số hạn mức vào bảng `gateway_connection_key` để hiển thị.
- Tab **Setting** sửa qua `POST /api/quota` và `/api/quota/top-up`, chỉ cần **DASHBOARD_KEY**, ghi
  thẳng metadata trên Gateway. Danh sách của nó gồm **mọi** key, kể cả key `connection-…`
  (`backend/main.py:494`).

Hệ quả, đã chứng minh bằng code ngày 29/09/2026:

1. **Vi phạm spec của tab Kết nối.** Capability `gateway-connection-management` yêu cầu: "MUST NOT grant
   mutation access through the existing dashboard key". Người chỉ có khoá xem dashboard vẫn đổi được
   hạn mức của key do tab Kết nối quản lý.
2. **Tab Kết nối hiện số sai.** Nó đọc hạn mức từ `gateway_connection_key` (`connection_store.py:134`);
   tab Setting không cập nhật bảng đó.
3. **Làm rối bước phục hồi của worker.** Bước phục hồi so hạn mức trên Gateway với số đã lưu
   (`connection_worker.py:412-413`); một lần sửa chen từ tab Setting làm phép so này sai.

## What Changes

- `gateway.set_quota` — hàm chung của cả hai endpoint ghi hạn mức — **từ chối** key có tên bắt đầu
  bằng `connection-`. Hai endpoint trả **409** kèm câu "Key này do tab Kết nối agent quản lý".
- Tab Setting **không sửa**: nó đã tự hiện "Không lưu được: <lý do>" và giữ số cũ khi backend từ chối
  (`web/js/app.js:4812-4816`). Các key `connection-…` vẫn hiện trong danh sách để **xem** số đã tiêu.
- Cập nhật chú thích lập luận ở `backend/main.py:61-66` và tài liệu vận hành: câu "ai xem được
  dashboard thì cũng sửa được hạn mức của **mọi** project" không còn đúng với key do tab Kết nối cấp.
- **Hệ quả cho vận hành:** nút "Chặn" ở tab Setting không chặn khẩn cấp được key `connection-…` nữa.
  Muốn chặn thì dùng tab Kết nối (đặt hạn mức 0 hoặc thu hồi key), cần khoá quản trị.

## Capabilities

### New Capabilities

(không có)

### Modified Capabilities

- `project-quota-budgets`: thêm yêu cầu "đường ghi hạn mức của dashboard không sửa key do tab Kết nối
  quản lý". Capability này còn nằm trong change chưa archive `stop-a-project-when-its-quota-runs-out`;
  delta ở đây chỉ **thêm** yêu cầu. Yêu cầu "Một khoá dùng chung cho cả đọc lẫn sửa hạn mức"
  (capability `api-access-control`, cùng change đó) vẫn đúng với mọi key khác; phạm vi thu hẹp được
  ghi ở chú thích mã nguồn và tài liệu, đúng như yêu cầu "Ghi chú lập luận trong mã nguồn phải khớp với
  thực tế".

## Impact

- `backend/gateway.py`: một phép kiểm trong `set_quota`, một kiểu lỗi mới.
- `backend/main.py`: hai endpoint đổi kiểu lỗi mới thành 409; sửa chú thích dòng 61-66.
- `tests/test_quota_gateway.py`: ca kiểm từ chối key `connection-…`, và ca kiểm key khác vẫn sửa được.
- `docs/reference/gateway-connection-management.md:3`, `docs/reference/dashboard-setup.md:54`.
- Không đụng frontend, worker, database hay Gateway.
