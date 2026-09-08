## Context

Dashboard hiển thị tiền từ `usage_resolved.cost_usd`. Cột này NULL ở những dòng chưa có
hoá đơn Google; `web/js/app.js` đã tự bù bằng cách nhân `ref_price` (Cloud Billing
Catalog, `price_source='google'`) để dashboard không bao giờ hiện ô trống. Vấn đề không
phải là phép suy sai — đối chiếu 965 dòng có cả hai vế lệch tổng chỉ 0,1% — mà là **màn
hình không nói khi nào nó đang làm vậy**. Đo 20/08/2026: 28,2% số tiền hiển thị trên toàn
kỳ 01/01→17/08 là suy ra, và tỷ lệ này lệch rất mạnh theo agent (Trợ lý ảo Ralli 100%) và
theo ngày (22/228 ngày trên 50%).

Change `serve-department-metrics-from-database` (commit `6d6eef8`) đã giải quyết việc này
cho một bảng (tab Phòng ban & User, hàm `deptCostCell()`). Change này tổng quát hoá cùng
cơ chế ra 5 tab còn lại: Tổng quan · Agents · Provider & Model · Chi phí · Hiệu năng.

## Goals / Non-Goals

**Goals:**
- Mọi ô/thẻ/biểu đồ/dòng CSV chứa tiền phải tự khai được bao nhiêu % là suy ra, không chỉ
  nói "có suy ra".
- Phân biệt hai nguyên nhân suy ra có hành động xử lý khác nhau: hoá đơn về trễ (tự hết)
  và agent chưa nối Google Billing (không tự hết, cần người nối).
- Giữ nguyên mọi con số tiền đã hiển thị — đây là change thêm nhãn, không phải sửa cách
  tính.

**Non-Goals:**
- Không đụng `backend/`, `db/`, `scripts/` — dữ liệu nguồn (`cost_usd` NULL đúng chỗ,
  `token_estimated`) đã đủ để tầng frontend tự phân loại.
- Không nối Google Billing cho `tla-ralli`. Đó là việc hạ tầng; change này chỉ làm phần
  suy ra **nhìn thấy được**, không loại bỏ nó.
- Không áp yêu cầu này cho nguồn `gateway` (xem Quyết định 5).

## Decisions

**1. Một điểm nghẽn duy nhất: `aggregate()` (`app.js:939`).**
7 chỗ gọi hàm này nuôi mọi con số tiền trên dashboard, nên toàn bộ phần suy ra được tính
một lần ở đây (`costEst` bên cạnh `cost` sẵn có) rồi lan ra 6 tab, thay vì tính lại ở từng
tab. Tái dùng `costOrNull()` (đã có từ commit `0e11c5a`) để xác định dòng nào suy ra thay
vì viết lại phép kiểm.

**2. Tách hai nguyên nhân suy ra bằng `dim_agent.has_google_source`, không phải đếm dòng
hoá đơn trong kỳ.**
Cách đầu tiên thử: coi `costRowsInv === 0` (không dòng nào trong kỳ có hoá đơn) là dấu
hiệu "agent chưa nối billing". Sai — kiểm bằng ngày 17/08 lộ ra cả 7 agent **đã nối
billing thật** cũng bị gộp nhầm vào "chưa nối", vì đúng ngày đó chưa agent nào có hoá đơn
về (hoá đơn Google trễ ~1 ngày). Sửa bằng cờ tĩnh cấp-agent `has_google_source`
(`dim_agent`), phơi ra frontend qua `api.js` thành `noBillingAgents` — độc lập với kỳ đang
xem, nên không còn nhầm "hôm nay chưa có" với "sẽ không bao giờ có".

**3. Một hàm dựng ô tiền dùng chung, theo khuôn `deptCostCell()` có sẵn.**
`moneyCell()` (`app.js:520`) chuyển sang gọi hàm chung này thay vì mỗi tab tự viết cách
gắn nhãn riêng. Ba trạng thái cố định: toàn bộ hoá đơn / có phần suy ra (kèm %) / toàn bộ
suy ra. Ngưỡng "không đáng kể" (không gắn dấu để tránh nhiễu — xem Rủi ro) khai thành hằng
số có tên, có ghi chú lý do chọn số đó, không phải số ma thuật rải trong code.

**4. Thẻ Tổng quan tính tỷ lệ suy ra của ĐÚNG kỳ đang chọn, không phải toàn bộ dữ liệu.**
Cạm bẫy đã mắc lúc làm (17/08): tính tỷ lệ trên toàn bộ 224 ngày trong khi thẻ chỉ hiện kỳ
người dùng chọn, ra kết quả sai lệch (báo 28% cạnh một con số mà tỷ lệ thật của kỳ đó là
32%). Sửa: tỷ lệ luôn tính lại theo `dateRange` hiện hành, không cache theo kỳ mặc định.

**5. Nguồn `gateway` không áp dụng requirement này — quyết định của chủ dự án, ghi lại
31/08/2026.**
Ba nguồn cũ (`billing`, `monitoring`, `app`) đều giữ yêu cầu gắn `≈`. Nguồn thứ tư
(`gateway`, thêm sau khi change này đã viết proposal) hiển thị thẳng số tiền LiteLLM,
không gắn dấu suy ra. Lý do và số đo nằm ở
`openspec/changes/load-the-gateway-ledger-into-the-database/tasks.md` mục 9 và đầu file
`db/migrations/sql/005_gateway_cost_vao_view.sql` — không lặp lại ở đây để tránh hai nơi
cùng nói một quyết định rồi lệch nhau khi một bên sửa.

## Risks / Trade-offs

- **[Rủi ro] Gắn `≈` lên quá nhiều ô → người đọc coi là nhiễu và bỏ qua hết, kể cả những
  ô đáng chú ý (100% suy ra).**
  → Giảm bằng ngưỡng "không đáng kể" có tên ở Quyết định 3: ví dụ Chatbot Contact Center
  (2,8% suy ra) không mang dấu, trong khi Trợ lý ảo Ralli (100%) và Trợ Lý Ảo Hợp Đồng
  (77,7%) luôn mang dấu kèm số %. Nghiệm thu 6.3 xác nhận trực tiếp trên hai ca này.
- **[Rủi ro] `ref_price` chỉ có một mốc hiệu lực (2026-08-13) — ngày Google đổi giá, mọi
  số suy ra của quá khứ sẽ nhảy, trong khi hoá đơn thì không đổi.**
  → Không mitigate trong change này (ngoài phạm vi — đụng `db/`), chỉ ghi nhận là lý do
  BẮT BUỘC phải gắn nhãn dù sai số tổng hiện tại rất nhỏ (0,1%).
  Chỗ chưa xử lý: nếu bảng giá đổi, không có cơ chế cảnh báo con số lịch sử đã trôi —
  để lại như một hạn chế đã biết, không phải bug của change này.
- **[Rủi ro] Cache trình duyệt khiến người xem không thấy bản mới.**
  Đã xảy ra thật lúc làm (20/08, mất một vòng vì bộ đệm `app.js`).
  → Nghiệm thu 6.7 dùng `fetch("js/app.js?probe="+Date.now())` để xác nhận đang chạy bản
  mới trước khi kết luận bất kỳ tab nào đã đúng.
- **[Rủi ro đã xác nhận và sửa] Excel tiếng Việt vỡ cột khi mở `exportCSV()` trực tiếp.**
  Windows lấy delimiter CSV từ list separator của Regional Settings máy đang mở, không
  phải từ nội dung file; vùng miền Việt Nam đặt dấu phẩy làm phân cách thập phân nên list
  separator mặc định đổi sang dấu chấm phẩy — file chỉ dùng dấu phẩy sẽ gộp hết vào một
  cột. Máy dev (`en-US`) không lộ lỗi này nên phải suy từ cơ chế Windows, không phải từ
  quan sát trực tiếp trên Excel tiếng Việt.
  → Sửa bằng dòng chỉ thị `sep=,` đầu file (Excel mọi vùng miền đọc dòng này, cố định
  delimiter) và thêm BOM UTF-8 để không vỡ dấu tiếng Việt. Xác minh bằng `xxd` trên file
  mẫu dựng lại đúng cơ chế: BOM `ef bb bf` đúng vị trí, `sep=,` đúng dòng đầu, giá trị có
  dấu phẩy được quote đúng chuẩn CSV.

## Open Questions

- Fix `sep=,` + BOM đã xác minh đúng ở mức byte, nhưng chưa có ai tự tay mở bằng Excel
  tiếng Việt thật để xác nhận bằng mắt — môi trường làm việc không có Excel tiếng Việt.
  Đã gửi file mẫu (`sample_export.csv`) cho Trần Xuân Tuấn; nếu mở thử mà vẫn vỡ, quay lại
  đây trước khi coi requirement `visible-data-provenance` (mục "Số mang ra ngoài không mất
  dấu vết") là đạt.
