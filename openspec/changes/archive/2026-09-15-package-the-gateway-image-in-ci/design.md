## Context

Hiện trạng, đo ngày 14/09/2026:

```
docker-compose.yml   x-litellm.build.context   ../litellm_tuan_test
                     x-litellm.image           litellm_tuan_test:gateway   (build tren may nguoi)
docker-compose.bench.yml  litellm-bench.image  litellm_tuan_test:gateway

fork   github.com/ursweetheart/litellm_rang_dong   PUBLIC, nhanh mac dinh Tuan-develop
       Tuan-develop               e3490555c5   CO  _SENTINEL_IGNORED_CONNECTION_ARGS
       litellm_internal_staging   5b13b8361e   KHONG co ban va
       ban clone tren may nay:    nhanh litellm_internal_staging, commit e3490555c5

repo   github.com/ursweetheart/token-ledger-dashboard   PUBLIC tu 25/07/2026 (ban dau ghi nham PRIVATE)
CI     .github/workflows/ci.yml: guards, test-js, test-py — khong co Docker

image  litellm_tuan_test:gateway   21536058b191   1,65 GB (giai nen)   tao 07/09/2026 17:25 +07
       _SENTINEL_IGNORED_CONNECTION_ARGS trong .venv/.../litellm/_redis.py: 3 lan
       file .env* trong image: chi /app/docker/.env.example
       commit e3490555c5 ngay 08/09/2026 10:28 +07 -> image co truoc commit nay,
       tuc la KHONG build dung tu e3490555c5
```

Image đang chạy tạo **trước** commit mà change này ghim. Nó build từ một cây mã trên máy người, không
biết đúng commit nào. Đây thêm một lý do để không coi nó là mốc so từng byte, mà chỉ so hai điều: có bản
vá, và không có `.env`.

Chặng 1 (`2026-09-13-run-every-check-on-every-push`) đã ghi rõ: *"Chặng 2 gỡ được nút này bằng cách
thay `build:` bằng `image:` trỏ vào kho."* Luật triển khai đã chốt vẫn giữ nguyên: không `down`, không
`--remove-orphans`, không gọi profile `tools`.

Dockerfile của fork gồm 4 tầng: builder giao diện dùng `node:24.19-alpine`, `uv`, builder `wolfi-base`
có Rust, và runtime. Các base image đều ghim theo digest. Dockerfile dùng `RUN --mount=type=cache`, nên
cần BuildKit.

## Goals / Non-Goals

**Goals:**

- Một máy chỉ có repo này, **không có thư mục ngang hàng nào**, vẫn chạy được
  `docker compose --profile gateway pull` và `up -d`.
- Nhìn nhãn image là biết nó build từ commit nào của fork.
- Nhánh mất bản vá Sentinel thì CI đỏ **trước khi** có image hỏng trên kho.
- Máy chủ kéo image mà không phải giữ khoá bí mật nào.

**Non-Goals:**

- Tự động triển khai. Đó là chặng 3.
- Đóng gói `api`, `web`, `tools`.
- Build nhiều kiến trúc. Chỉ build `linux/amd64` — xem Open Questions.
- Cache tầng build giữa các lần chạy. Bỏ qua khi nhãn đã có đã loại gần hết số lần build.

## Decisions

### D1. Build trong CI của repo dashboard, không trong CI của fork

**Chọn:** thêm công việc `gateway-image` vào `.github/workflows/ci.yml` của `token-ledger-dashboard`.

**Phương án bị loại — workflow nằm trong fork.** Fork thừa hưởng **45 workflow** từ upstream LiteLLM.
Bật Actions ở fork là phải soát và tắt từng cái, và mỗi lần merge upstream lại có thể mang về cái mới.
Còn đặt ở repo dashboard thì mọi thứ quyết định việc chạy Gateway nằm chung một chỗ: compose, cấu hình
LiteLLM, và nay là cách đóng gói.

**Cái giá:** repo dashboard không biết khi nào fork có commit mới. D4 lo chuyện đó.

### D2. Clone nhánh `Tuan-develop` qua HTTPS, không cần khoá

```
git clone --depth 1 --branch Tuan-develop https://github.com/ursweetheart/litellm_rang_dong.git
```

Fork công khai, nên clone không cần token. Commit build ra được đọc bằng `git rev-parse HEAD` **sau**
khi clone, không đoán trước.

**Phương án bị loại — ghim commit trong workflow.** Lặp lại cái mà compose đã ghim. Hai chỗ ghim cùng
một sự thật thì trôi khỏi nhau. Nhãn trong compose (D6) đã là chỗ quyết định image nào chạy. CI chỉ lo
**có sẵn** image cho đầu nhánh.

### D3. Canh bản vá Sentinel trước khi build

```
grep -q _SENTINEL_IGNORED_CONNECTION_ARGS litellm/_redis.py || fail
```

Đây là cách chặn rẻ nhất mà `luat-trien-khai-tu-dong-13-09.md` mục 6 đã để dành cho chặng này. Nó bắt
đúng lỗi đã xảy ra: nhánh không có bản vá. Thông điệp lỗi phải nêu tên nhánh, commit, tệp và ký hiệu.

**Phải làm đỏ có chủ ý một lần** trước khi coi là xong. Bài học của chặng 1: hai lỗi nặng nhất chỉ lộ
ra khi cố ý làm hỏng.

### D4. Nhãn = commit đầy đủ của fork, bất biến, có thì bỏ qua

```
ghcr.io/ursweetheart/litellm_rang_dong:<40 ky tu hex>
```

Trước khi build: `docker manifest inspect <nhãn>`. Có rồi thì **bỏ qua build và push**. Như vậy:

- đẩy code dashboard mà fork không đổi thì công việc chỉ tốn vài giây;
- một nhãn không bao giờ bị ghi đè, nên cùng nhãn luôn là cùng image.

GHCR không tự cấm ghi đè nhãn. Tính bất biến ở đây do bước bỏ qua giữ.

**GHCR trả lời "chưa có" bằng hai cách** (đo 15/09/2026, không đăng nhập):

| Hỏi | GHCR trả |
|---|---|
| nhãn không có, trên gói đã tồn tại (`ghcr.io/berriai/litellm:does-not-exist-xyz`) | `manifest unknown` |
| gói chưa từng tồn tại (`ghcr.io/ursweetheart/litellm_rang_dong:does-not-exist`) | `denied` |

Bản đầu chỉ nhận `manifest unknown`, nên lần build đầu tiên sẽ đỏ mãi: gói chỉ ra đời sau khi build.
Nay `denied` và `unauthorized` cũng tính là "chưa có". Không ghi đè được nhãn nào vì thế: không đọc được
gói thì `docker push` cũng hỏng. Lỗi khác (mạng, kho quá tải) thì dừng.

**Khi đã đăng nhập bằng `GITHUB_TOKEN`**, gói chưa tồn tại, GHCR trả `manifest unknown` (đo ở lần chạy
CI `34914702065`, 15/09/2026). `denied` chỉ gặp khi không đăng nhập. Vẫn giữ `denied` trong danh sách,
vì lý do không ghi đè ở trên vẫn đúng.

**Không có nhãn trôi `latest`.** Nhãn trôi làm `pull` kéo về một thứ không ai chọn.

Kèm nhãn OCI `org.opencontainers.image.revision` (commit fork) và `org.opencontainers.image.url`
(URL fork), để `docker inspect` trên máy chủ cũng trả lời được câu *"build từ đâu"*.

**`org.opencontainers.image.source` trỏ về repo dashboard, không về fork** (sửa 15/09/2026, lúc
apply). Tài liệu GitHub: nhãn này là *"The URL of the repository associated with the package"*, và
*"The token's permissions are limited to the repository that contains your workflow"*. Để nó trỏ về
fork là có nguy cơ gói bị gắn sang fork, rồi lần đẩy sau `GITHUB_TOKEN` hết quyền ghi.

### D5. Quyền: `GITHUB_TOKEN`, chỉ ở một công việc, không chạy ở pull request

```yaml
gateway-image:
  if: github.event_name != 'pull_request'
  permissions:
    contents: read
    packages: write
```

Ba nhóm kiểm cũ giữ quyền mặc định. Không thêm secret nào vào repo. Đăng nhập bằng
`docker login ghcr.io --password-stdin`, không in token.

**Phương án bị loại — dùng PAT.** Thêm một khoá phải xoay vòng, và khoá đó mạnh hơn cần thiết.

Dùng `docker build` và `docker push` trần, không thêm action bên thứ ba ngoài `actions/checkout`.
Docker trên `ubuntu-latest` mặc định dùng BuildKit.

### D6. Compose ghim nhãn qua biến có giá trị mặc định

```yaml
x-litellm: &litellm
  image: ${LITELLM_IMAGE:-ghcr.io/ursweetheart/litellm_rang_dong:4373a32c2a2608cdbd732ba47ba057615e5e2846}
```

- **Máy chủ** không đặt gì và nhận đúng nhãn ghim trong git. Đổi phiên bản Gateway là một dòng đổi
  trong lịch sử git, nhìn thấy được.
- **Máy phát triển** muốn thử bản fork đang sửa thì chạy
  `docker build -t litellm-local ../litellm_tuan_test` rồi đặt `LITELLM_IMAGE=litellm-local` trong
  `.env`.

Chú thích dài về bản vá Sentinel đang nằm dưới `build:` được giữ lại, chuyển lên trên dòng `image:`.

### D7. Hai phép canh compose

1. **Nhóm `guards`** (không cần mạng): khối `x-litellm` không được có `build:` hay `context: ../`.
2. **Công việc `gateway-image`**, bước cuối: nhãn mặc định mà `docker-compose.yml` ghim phải tồn tại
   trên kho (`docker manifest inspect`).

Thứ tự đổi phiên bản vì thế luôn xanh: đẩy commit fork → CI build nhãn mới → commit sửa nhãn trong
compose. Ghim một nhãn chưa từng build thì đỏ ngay, trước khi máy chủ nào thử kéo nó.

### D8. Gói công khai, đặt bằng tay một lần

Gói do workflow đẩy lên lần đầu thì riêng tư, **kể cả khi repo công khai** (đo 15/09/2026: repo
`private=false`, gói `visibility=private`). Có hai cách để máy chủ kéo được:

| | Công khai gói | `docker login` trên máy chủ |
|---|---|---|
| Khoá trên máy chủ | không | PAT `read:packages`, phải xoay vòng |
| Lộ gì | image của một fork **vốn đã công khai** | không |
| Máy mới | kéo được ngay | phải cấp khoá trước |

**Chọn công khai**, với điều kiện đã kiểm: image không chứa bí mật. Cấu hình LiteLLM, khoá nhà cung
cấp và master key đều đi vào **lúc chạy**, qua volume và biến môi trường (`x-litellm.volumes`,
`x-litellm.environment`).

**Cái gì thật sự vào image.** `COPY . .` chỉ nằm ở tầng `builder`, và tầng đó không được đẩy lên kho.
Tầng `runtime` chỉ chép `.venv` (gói `litellm` đã cài), `docker/`, `enterprise/`, `litellm-proxy-extras/`,
`schema.prisma`, `prisma_migration.py` và `/opt/prisma`. `.dockerignore` của fork loại thêm `.env`,
`.env.local`, `tests`, `docs`, `.git`, `.github`, `.circleci`, `cookbook`. Vẫn phải quét, vì `litellm/`
và bản build giao diện nằm trong `.venv`.

**Cách quét:** `tools/scan_secrets.py --root ../litellm_tuan_test`. Cờ `--fork` chỉ kiểm `git status`
của fork, không quét nội dung.

**Kết quả quét, 15/09/2026, fork tại `e3490555c5`, `git status` sạch:** 9.432 tệp văn bản, 619 khớp
nghiêm trọng. Script thoát mã 1.

| Thư mục | Khớp | Vào image? |
|---|---|---|
| `tests/` | 525 | không — `.dockerignore` |
| `ui/` | 46 | không. Tệp nguồn và tệp test giao diện, chỉ bản build `out/` vào image |
| `.circleci/`, `.github/`, `cookbook/`, `ci_cd/`, `scripts/`, `db_scripts/`, gốc repo | 32 | không |
| `litellm/` | 13 | **có** — ví dụ `sk-...` trong docstring, và dòng mở đầu `-----BEGIN PRIVATE KEY-----` làm chữ gợi ý trong ô nhập |
| `litellm-rust/` | 3 | tệp `tests.rs` |

**Người sở hữu duyệt ĐẠT ngày 15/09/2026, dù script không ra 0.** Lý do: CI build từ một bản clone
mới của fork, và fork **đã công khai**. Mọi thứ đi vào image vốn đã công khai trên GitHub hoặc PyPI.
Image chỉ lộ thêm được thứ gì đó khi build từ một cây mã có tệp nằm ngoài git, và CI không làm vậy.
Đây là **suy luận** dựa trên cách CI build, không phải phép kiểm từng dòng trong 13 khớp ở `litellm/`.

## Risks / Trade-offs

- **[Lần build đầu quá lâu hoặc hết đĩa trên runner]** Runner `ubuntu-latest` có khoảng 14 GB trống.
  Build giao diện Node cộng Rust cộng uv chưa từng được đo trên đó.
  → Đo ở lần chạy đầu và ghi lại con số. Nếu hết đĩa, thêm bước dọn công cụ có sẵn của runner trước
  khi build. Không tối ưu trước khi đo.
- **[Base image ghim digest trên `cgr.dev` bị gỡ]** Build hỏng dù mã không đổi.
  → Hỏng ồn ào, không hỏng im lặng. Image đã có trên GHCR vẫn kéo được, nên máy đang chạy không bị ảnh
  hưởng.
- **[Gói apk trôi khỏi base image — ĐÃ XẢY RA ở lần chạy CI đầu, `34914702065`, 15/09/2026]**
  Digest ghim chỉ cố định base image, còn `apk add python3` luôn lấy gói mới nhất. Gói
  `python-3.13 3.13.15_git20260912` cần glibc 2.44; base `a31344ab…` có glibc 2.43. `import math` hỏng,
  uv bỏ `/usr/bin/python3` **không báo gì** (chỉ thấy khi `-v`), tải CPython 3.14, và `uvloop 0.21.0`
  không có wheel 3.14 nên build hỏng. Tầng runtime cài cùng gói, nên dù build qua được, Gateway cũng
  chết lúc chạy. Bản build tay ngày 07/09 không gặp vì gói mới chưa ra.
  → Fork commit `4373a32c`: cả hai tầng lên base `9a8d954d…` (glibc 2.44), thêm
  `UV_PYTHON_DOWNLOADS=never` để lần lệch sau hỏng ngay ở `uv sync`. Kiểm bằng Dockerfile dò: uv chọn
  `/usr/bin/python3` 3.13.15, `.venv` có `home = /usr/bin`. **Sẽ lặp lại** khi Wolfi ra gói mới hơn
  base; cách chữa vẫn là nâng digest. Commit này chỉ đổi 3 dòng trong `Dockerfile`, không đổi kết quả
  quét bí mật ở 1.1.
- **[Merge upstream vào `Tuan-develop` làm mất bản vá]**
  → D3 chặn trước khi build. Image cũ trên kho vẫn còn.
- **[Image từ kho khác image đang chạy dù cùng commit]** Image hiện tại build trên máy người, không có
  dấu vết về cờ build.
  → Trước khi chuyển: kéo image mới, grep bản vá bên trong, rồi mới khởi động lại. Giữ nguyên image cũ
  trên máy để quay lui.
- **[Khởi động lại Gateway]** Gateway trên máy phát triển là bản local, tắt bật tự do (chốt 15/09/2026).
  → Không cần làm lần lượt từng instance ở change này. Máy chủ thật ở chặng 3 mới cần: đợi healthy từng
  cái, `gateway-lb` chuyển lưu lượng sang instance còn sống, như đã diễn tập trong
  `2026-09-14-keep-the-crm-agent-running-when-the-gateway-dies`.
- **[Công khai gói là không rút lại được hoàn toàn]** Ai đã kéo thì đã có.
  → Quét bí mật trước (D8). Mọi bí mật đều đi vào lúc chạy, không nằm trong image.
- **[Người phát triển quen build tại chỗ]** `docker compose --profile gateway up -d --build` không còn
  build từ fork nữa.
  → Ghi cách dùng `LITELLM_IMAGE` trong `.env.example` và ngay trên dòng `image:`.

## Migration Plan

1. Hợp nhất workflow và để CI build nhãn cho `4373a32c…`. Compose **chưa** đổi. (Bản đầu ghi
   `e3490555c5…`; commit đó không build được, xem Risks "gói apk trôi khỏi base image".)
2. Người sở hữu đặt gói công khai. Kéo thử **không đăng nhập** từ một máy.
3. Commit đổi `x-litellm` sang `image:` với nhãn vừa build. CI đỏ nếu nhãn không có.
4. Trên máy phát triển: `docker compose --profile gateway pull`, grep bản vá trong image, rồi
   `docker compose --profile gateway up -d`. **Không** `down`, **không** `--remove-orphans`.
5. Gọi thử một lượt qua `gateway-lb` và kiểm `/health/liveliness` của cả hai instance.

**Quay lui:** đặt `LITELLM_IMAGE=litellm_tuan_test:gateway` trong `.env` (image cũ vẫn nằm trên máy),
rồi `up -d` lại từng instance. Không cần revert commit.

## Open Questions

- **Kiến trúc máy chủ Gateway mới.** Change này giả định `linux/amd64`, giống máy hiện tại. Máy mới là
  ARM thì phải build thêm một kiến trúc. Hỏi trước khi mua hoặc cấp máy.
- ~~**`docker compose pull` với các image `:local`** (`api`, `web`, `tools`) không có trên kho nào: chạy
  êm, hay cần `--ignore-buildable`?~~ **Đã đo 15/09/2026 (task 5.6): CẦN `--ignore-buildable`.**
  Không có cờ thì `pull` thoát mã 1 vì `token-ledger-api:local`/`token-ledger-web:local` báo
  `authorization failed`, có hay không `--profile gateway`. Có cờ thì mã 0. Lệnh triển khai của chặng 3
  phải là `docker compose [--profile gateway] pull --ignore-buildable`.
- **Ai đặt gói công khai.** Thao tác trên giao diện GitHub, chỉ người sở hữu tài khoản làm được.
