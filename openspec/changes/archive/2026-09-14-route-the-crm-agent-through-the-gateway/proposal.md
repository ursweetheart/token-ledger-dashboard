# Đưa agent Phân Loại Dữ Liệu CRM đi qua Gateway

## Why

`dms-feedback` là agent duy nhất trong 8 agent đi qua Gateway. Bảy agent còn lại vẫn gọi
thẳng nhà cung cấp, nên với chúng Gateway không ghi được một dòng nào. Change này đưa agent
thứ hai — `crm-feedback`, agent 7 — qua Gateway.

CRM được chọn vì đo trong sổ thấy nó **đơn giản nhất**: đúng **một** model
(`gemini-2.5-flash`, 1.888 lượt / 22,6 triệu token / 06/07 → 29/08), không có cây phòng ban,
không có nguồn `app`. Ít chỗ sai nhất trong 7 agent còn lại.

Và với CRM, Gateway là **nguồn đầu tiên biết từng request**. Hôm nay mọi thứ ta biết về CRM
đều ở mức project + ngày, vì nó chỉ có `billing` và `monitoring`; `usage_by_account` có **0
dòng** cho agent 7. Nên đây không chỉ là chuyển tuyến — nó mở ra dữ liệu chưa từng có.

## What Changes

- **Khai một tuyến Vertex thật** mang tên `gemini-2.5-flash`, chạy trên project mới có credit
  của người dùng, dùng service account của chính project đó. Giữ **đúng model production
  đang dùng**, không thay thế.
- **BREAKING — xoá `model_group_alias`** đã thêm ngày 08/09. Không phải dọn dẹp mà là sửa
  lỗi: `router.py:11011` giải bí danh **trước** khi tra model group thật và ghi đè `model`,
  nên để bí danh lại thì tuyến Vertex mới **không bao giờ được gọi tới** và mọi request rơi
  vào `gemini-3.6-flash` — im lặng, request vẫn 200, chỉ có cột model trong sổ là sai.
- **Cấp virtual key** cho `crm-feedback`, mang tag định danh, giới hạn `models`.
- **Thêm một nhánh `gateway`** vào `src/llm.py` của bản clone CRM, đặt cạnh hai nhánh
  `vertex` và `apikey` đang có. Hai nhánh cũ **không đổi một dòng**, và mặc định vẫn là
  chúng — lùi lại là đổi một biến môi trường.
- **Nối container CRM vào mạng Gateway** bằng `docker-compose.override.yml`.

## Capabilities

### New Capabilities
- `crm-gateway-routing`: agent CRM phải gọi được LLM qua Gateway thay vì gọi thẳng nhà cung
  cấp, mà không sửa logic phân loại, không mất đường lùi, và mỗi lượt gọi phải quy được về
  đúng agent trong sổ.

### Modified Capabilities
<!-- Khong co. `agent-gateway-routing` quy dinh Gateway phai dinh tuyen duoc theo tag va
     tach duoc project; change nay ap dung dung nhung yeu cau do cho mot agent thu hai,
     khong doi mot yeu cau nao. -->

## Impact

**Trong repo này**

- `docker/gateway/config.gateway.yaml` — thêm tuyến Vertex, **xoá** `model_group_alias`
- `docker-compose.yml` — mount file service account vào hai instance LiteLLM
- database `litellm` — thêm một dòng `LiteLLM_VerificationToken` (virtual key)
- `dim_agent.gcp_project_id` của agent 7 đang ghi `crm-500509`; tiền sẽ chuyển sang project
  mới, nên giá trị đó thành sai. Cần quyết định ghi lại hay ghi chú.

**Trong bản clone `CRM-Classification-Pipeline`** (code của nhóm khác, cùng khuôn DMS đã làm)

- `src/llm.py` — thêm nhánh `gateway`, không sửa hai nhánh cũ
- `docker-compose.override.yml` — file mới, nối vào mạng Gateway
- `0 dòng` logic phân loại bị sửa

**Không đụng tới**

- `db/load_gateway.py`, schema, đường nạp sổ — đã xong ở change
  `let-the-gateway-ledger-arrive-by-itself`, chỉ dùng lại
- Hai nhánh `vertex` / `apikey` của CRM, và toàn bộ SharePoint / email / Excel

**Phụ thuộc bên ngoài, chưa có trong tay**

- project Google mới + service account JSON của nó
- **chưa biết Vertex có phục vụ `gemini-2.5-flash` hay không.** Hai endpoint metadata đã thử
  đều trả cùng một mã cho một tên model bịa ra, nên chúng không trả lời được; phải một lượt
  `generateContent` thật. Nếu Vertex không có model đó thì phải quyết định lại, và change
  này có task riêng cho chỗ đó chứ không giả định.
