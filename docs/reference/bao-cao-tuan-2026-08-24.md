# Báo cáo tuần — 24/08 → 27/08/2026

**Dự án:** API Gateway & Token Ledger Dashboard
**Người thực hiện:** CTV (Tuấn)
**Số ngày làm việc trong kỳ:** 3 (24/08, 26/08, 27/08)

---

## Đã làm được

### 1. Hoàn tất chuyển schema database sang cơ chế migration — 24/08

- Đưa Alembic vào quản schema, đóng băng schema hiện tại thành migration gốc
- Dựng lại database v2 từ migration, đối chiếu khớp **đến từng token** với bản cũ
- Gỡ hẳn đường thoát SQLite — PostgreSQL là engine duy nhất (hoàn thành 32/32 việc)
- Rà và sửa tài liệu cho khớp database thật: hợp đồng dữ liệu, tài liệu triển khai,
  danh sách việc cần làm trước

*27 commit trong ngày.*

### 2. Đo thực nghiệm khả năng ghi nhận của LiteLLM Gateway — 26/08

- Dựng môi trường đo tách biệt (LiteLLM bản fork + database riêng), chạy 5 lượt đo
- **Kết quả quan trọng:** bác bỏ kết luận sai của buổi sáng — Gateway **không** vứt
  header danh tính; cột chứa chúng chỉ bị tắt theo mặc định
- Chốt được bộ 4 khoá cấu hình an toàn cho bản chạy thật (3 bật, 1 tắt — vì bật là mỗi
  request gửi email nhân viên sang nhà cung cấp)
- Chứng minh được cơ chế che nội dung câu hỏi vẫn giữ nguyên header
- Nghiệm thu: database thật không bị đụng tới, bộ số nền giữ nguyên
  **1.189 dòng / 867.657.110 token**
- Viết tài liệu tham chiếu về cách đo và kết quả đo

### 3. Dựng khung hạ tầng Gateway và lên kế hoạch — 27/08

- Thêm Redis (primary + replica), 2 instance LiteLLM chạy stateless, nginx cân bằng tải
  và database riêng cho Gateway vào Docker Compose — đã kiểm cấu hình, **chưa chạy thật**
- Điền lưới tiến độ 5 tháng vào Master Plan theo tiến độ thực tế
- Lập phương án nén tiến độ về đích **30/09** thay vì 31/12

### 4. Đóng trọn mạch đo Gateway — 27/08

- Lập bảng đối chiếu **26 trường hợp đồng dữ liệu × 34 cột Gateway ghi được**, tách rõ chỗ
  nào chứng minh được với chỗ nào mới là suy luận
- Sửa hợp đồng dữ liệu theo kết quả đo: hai trường `thinking_enabled` / `output_modality`
  đổi từ "Nguồn: Gateway" sang **"Dẫn xuất từ Gateway"** kèm quy tắc tính — ghi sai chỗ này
  thì người viết code đi tìm một cột không tồn tại
- Viết công cụ **quét bí mật theo hình dạng** (`tools/scan_secrets.py`). Phép kiểm cũ chỉ
  tìm hai chuỗi đã biết trước nên trả "0 file" và trông như đạt; phép kiểm mới ngay lần
  chạy đầu phát hiện **hai file bằng chứng chứa nguyên chuỗi token đăng nhập**, chưa được
  theo dõi và sẽ bị commit. Đã che, giữ nguyên giá trị làm bằng chứng
- Đo lại vùng phủ nguồn theo từng agent, phát hiện **"đối chiếu bốn nguồn" chỉ đúng với
  1 trên 8 agent** — điều này đổi cách phải làm báo cáo nghiệm thu ở giai đoạn 7

*Mạch đo Gateway hoàn tất **42/42 đầu việc**.*

---

## Chưa làm được / còn treo

- **Cổng chuyển đổi schema v2 chưa mở** — cần một người khác soát độc lập, không tự soát
  bản của mình được. 5 việc cuối của mạch này đang chờ ở đây
- **Gateway mới có khung, chưa chạy thật** — chưa khai đủ 8 tuyến cho 8 project, chưa cấp
  khoá cho agent nào, chưa có request thật nào đi qua
- **Chưa biết Ralli có tiền xử lý request ở server không** — cần quyền đổi cấu hình phía
  Ralli mới trả lời dứt điểm. Đây nay là **rủi ro lớn nhất** của kế hoạch: Ralli mang gần
  48 triệu token nhưng lại là agent duy nhất không có nguồn đối chứng thứ ba
- **Chưa bổ sung `gemini-3.6-flash` vào danh mục model** — bảng ánh xạ tên hoá đơn sang
  danh mục của ta còn thiếu model mà Google đang ép chuyển sang *(việc nhỏ; xem đính chính
  bên dưới)*
- Toàn bộ công việc từ 26/08 **chưa commit**

---

## Cần hỗ trợ

| Việc | Cần ai | Hạn |
|---|---|---|
| Soát độc lập cổng chuyển schema | Đồng nghiệp trong nhóm | 31/08 |
| Thu 8 khoá API của 8 project | Quản lý dự án | 28/08 |
| Quyền đổi cấu hình Ralli + 7 agent | Quản lý dự án | 04/09 |

---

## Tài liệu sinh ra trong tuần

| File | Nội dung |
|---|---|
| `docs/reference/do-ban-ghi-litellm-24-08.md` | Cách đo, phiên bản ghim, kết quả đo Gateway |
| `docs/reference/nhat-ky-26-08-sang.md` | Nhật ký chi tiết ngày đo |
| `docs/reference/ke-hoach-nen-thang-9-2026.md` | Phương án nén tiến độ về 30/09 |
| `docs/reference/doi-chieu-data-out-litellm.md` | Đối chiếu 26 trường hợp đồng × 34 cột Gateway |
| `docs/reference/bao-cao-tuan-2026-08-24.md` | Báo cáo này |
| `tools/scan_secrets.py` | Quét bí mật lọt repo, chạy lại được, mã thoát ≠ 0 là có lọt |
| `docker/gateway/` | Cấu hình Gateway, load balancer, khởi tạo database |
| `Master Plan API Gateway.xlsx` | Lưới tiến độ + hợp đồng dữ liệu đã sửa (bản lưu: `docs/reference/ban-luu/`) |

---

## Một đính chính

Trong tuần tôi từng xếp *"chưa tra được đơn giá `gemini-3.6-flash`"* là rủi ro số một, với
lý do Gateway sẽ tính sai chi phí cho gần một nửa lưu lượng. **Đo lại thì ngược lại**:
Gateway tra đơn giá đầy đủ và dựng lại được chi phí đến từng chữ số. Thiếu sót nằm ở bảng
danh mục model của chúng ta, không phải ở Gateway — và đó là việc vài dòng chứ không phải
việc nghiên cứu. Rủi ro số một thật sự là Ralli.
