## Why

Gateway là dịch vụ duy nhất trong `docker-compose.yml` **không chạy được trên một máy vừa clone repo**.
Khối `x-litellm` build image từ `build.context: ../litellm_tuan_test`, một thư mục ngang hàng repo.
Hệ quả đã ghi ở `docs/reference/luat-trien-khai-tu-dong-13-09.md`: máy nào thiếu thư mục đó thì
compose thoát ngay, nên lệnh triển khai tự động (chặng 3) **không được** gọi profile `gateway`.

Thư mục đó còn phải đứng đúng nhánh. Đo ngày 14/09/2026: bản clone trên máy này đang ở nhánh
`litellm_internal_staging`, nhưng tại commit `e3490555c5` có bản vá Sentinel. Trên kho từ xa,
`litellm_internal_staging` ở `5b13b8361e` và **không** có bản vá. Nhánh có bản vá là `Tuan-develop`.
Clone nhầm nhánh thì Gateway chết lúc khởi động với
`TypeError: Redis.__init__() got multiple values for argument 'host'`.

Và image đang chạy, `litellm_tuan_test:gateway`, được build **trên máy một người**. Không có dấu vết
nào nói nó build từ commit nào.

Lúc cần làm là bây giờ: kế hoạch đưa Gateway sang một máy chủ riêng nghĩa là sẽ có một máy mới. Máy mới
chính là kịch bản cả ba lỗi trên cùng xảy ra.

## What Changes

- **CI đóng gói image LiteLLM và đẩy lên GHCR.** Thêm một công việc vào `.github/workflows/ci.yml`
  của repo này. Nó clone fork công khai `ursweetheart/litellm_rang_dong` ở nhánh `Tuan-develop`,
  build, rồi đẩy lên `ghcr.io/ursweetheart/litellm_rang_dong:<commit của fork>`. Chỉ chạy khi đẩy code
  lên nhánh chính hoặc bấm chạy tay, không chạy ở pull request.
- **Thiếu bản vá Sentinel thì không đóng gói.** Trước khi build, CI tìm
  `_SENTINEL_IGNORED_CONNECTION_ARGS` trong `litellm/_redis.py`. Không thấy thì dừng và báo hỏng.
- **Mỗi commit của fork chỉ đóng gói một lần.** Nhãn đã có trên kho thì bỏ qua bước build. Không có
  nhãn trôi kiểu `latest`.
- **BREAKING (máy phát triển):** `x-litellm` đổi `build:` thành
  `image: ${LITELLM_IMAGE:-ghcr.io/ursweetheart/litellm_rang_dong:<commit>}`. Máy nào đang dựa vào
  `../litellm_tuan_test` để build thì phải đặt `LITELLM_IMAGE` nếu muốn dùng bản build tại chỗ.
  `docker-compose.bench.yml` dùng cùng biến.
- **CI canh để compose không quay lại phụ thuộc thư mục ngang hàng**, và nhãn image mà compose ghim
  phải tồn tại trên kho.
- **Chuyển Gateway trên máy phát triển sang image lấy từ kho**, sau khi so image mới với image cũ.

**Không thuộc phạm vi change này:**

- **Tự động đưa code lên máy chủ.** Đó là chặng 3. Change này chỉ gỡ nút chặn cho nó. Lệnh triển khai
  có gọi profile `gateway` hay không vẫn là quyết định của chặng 3.
- **Đóng gói `api` và `web`.** Hai image đó build từ chính repo này, nên máy nào có repo là build được.
  Chúng không mang nút chặn nào.
- **Đưa `tools` lên kho.** Luật đã chốt: không bao giờ chạy dịch vụ `tools` trong triển khai.
- **`tools/probe-gateway/docker-compose.probe.yml`.** Đây là công cụ dò tay, không phải đường chạy.
  Nó vẫn build từ fork ngang hàng.

## Capabilities

### New Capabilities

- `gateway-image-delivery`: Image Gateway được đóng gói bởi CI từ đúng nhánh có bản vá, gắn nhãn theo
  commit của fork, lấy về được từ kho mà không cần thư mục ngang hàng hay khoá bí mật trên máy chủ, và
  không mang bí mật nào bên trong.

### Modified Capabilities

(không có — `continuous-integration-checks` nói về bộ kiểm chạy trên máy sạch không Docker. Công việc
đóng gói là một công việc riêng, không đổi yêu cầu nào của spec đó.)

## Impact

| Tệp | Việc |
|---|---|
| `.github/workflows/ci.yml` | thêm công việc `gateway-image`; nhóm `guards` thêm một phép canh |
| `docker-compose.yml` | `x-litellm`: `build:` → `image:` đọc từ biến |
| `docker-compose.bench.yml` | `litellm-bench` dùng cùng biến image |
| `.env.example` | khai `LITELLM_IMAGE` và cách build tại chỗ |
| `docs/reference/luat-trien-khai-tu-dong-13-09.md` | mục 5, 6, 7: nút chặn đã gỡ, việc còn lại của chặng 3 |

**Hệ thống bên ngoài:**

- **GHCR** thêm gói `ursweetheart/litellm_rang_dong`. Gói sinh ra **riêng tư**, dù repo này công khai
  (đo qua API 15/09/2026: gói `visibility=private`, repo `private=false` từ 25/07/2026; bản đầu của
  proposal ghi nhầm repo là PRIVATE). Người sở hữu phải **đặt gói thành công khai một lần bằng tay**
  trên giao diện web, vì GitHub không có API đổi chế độ hiển thị của gói, để máy chủ kéo
  được mà không phải giữ khoá. Mã nguồn bên trong đã công khai sẵn ở fork.
- **Gateway trên máy phát triển** là bản local, sẽ được khởi động lại khi đổi image. Không ảnh hưởng
  hệ thống thật.

**Quyền:** công việc mới dùng `GITHUB_TOKEN` với `packages: write`, chỉ ở công việc đó. Không thêm
khoá bí mật nào vào repo. Token `gh` trên máy này không có quyền `read:packages`; điều đó không ảnh
hưởng CI, chỉ ảnh hưởng việc xem gói bằng dòng lệnh.

**Chi phí vận hành, đo ở lần build đầu thành công** (CI `34916164838`, 15/09/2026, fork `4373a32c`):

| Đo | Giá trị |
|---|---|
| Thời gian `docker build` | 487 giây |
| Cả công việc `gateway-image` | 8 phút 45 giây |
| Đĩa trống trên runner | 14 GB trước build → 6,0 GB sau build |
| Dung lượng image (giải nén) | 1,19 GB |
| Digest đã đẩy | `sha256:7e888594ede9dfdfa3cc8e2fd6efef6042d5bc046fe3609d3ea0f08c2e2c4b64` |

Nhờ bỏ qua khi nhãn đã có, chỉ lần đẩy đầu tiên sau mỗi commit mới của fork mới trả chi phí này. Build
dùng hết khoảng 8 GB đĩa, còn dư 6 GB: chưa cần bước dọn đĩa, nhưng nếu Dockerfile của fork nặng thêm
thì đây là giới hạn đầu tiên chạm tới.

Lần chạy trước đó (`34914702065`, fork `e3490555c5`) hỏng ở bước build sau khoảng 1 phút 30 giây, vì gói
apk trôi khỏi base image. Xem Risks trong `design.md`.
