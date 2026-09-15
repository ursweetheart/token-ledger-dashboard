## 1. Đo mốc trước khi đổi

- [x] 1.1 Chạy `tools/scan_secrets.py --root ../litellm_tuan_test` trên fork tại `e3490555c5`, ghi kết quả vào `design.md` (điều kiện của D8). Lưu ý: cờ `--fork` chỉ kiểm `git status` của fork, **không** quét nội dung — 619 khớp, người sở hữu duyệt đạt ngày 15/09/2026. Lý do trong D8
- [x] 1.2 Ghi ID image `litellm_tuan_test:gateway` đang chạy, và kết quả grep `_SENTINEL_IGNORED_CONNECTION_ARGS` bên trong nó, làm mốc so — `21536058b191`, 1,65 GB, bản vá có mặt (3 lần), `.env*` duy nhất là `/app/docker/.env.example`. Xem Context trong `design.md`

## 2. Công việc đóng gói trong CI

- [x] 2.1 Thêm công việc `gateway-image` vào `.github/workflows/ci.yml`: chạy khi đẩy lên `main`/`Tuan-develop` và khi bấm tay, không chạy ở pull request; `permissions: contents: read, packages: write` chỉ ở công việc này
- [x] 2.2 Clone `--depth 1 --branch Tuan-develop` qua HTTPS, đọc commit bằng `git rev-parse HEAD`
- [x] 2.3 Bước canh bản vá Sentinel trước build, thông điệp nêu nhánh, commit, tệp, ký hiệu
- [x] 2.4 Đăng nhập GHCR bằng `GITHUB_TOKEN` qua `--password-stdin`; `docker manifest inspect` nhãn commit, có rồi thì bỏ qua build và đẩy, báo rõ lý do — `denied` cũng tính là "chưa có", xem D4
- [x] 2.5 `docker build` với nhãn OCI `revision` (commit fork), `url` (fork) và `source` (repo dashboard, xem D4), rồi `docker push` đúng một nhãn là commit đầy đủ
- [x] 2.6 Bước cuối: đọc nhãn mặc định của `x-litellm` trong `docker-compose.yml`, `docker manifest inspect` nó, không có thì hỏng. Khi `x-litellm` còn `build:` thì bỏ qua, có thông báo

> 2.1–2.6 kiểm trên máy 15/09/2026: 22/22 phép kiểm chạy nguyên văn các khối `run:` lấy từ `ci.yml`,
> với `docker` giả; `actionlint 1.7.7` (kèm shellcheck) mã thoát 0. Bước clone, đăng nhập, build và
> đẩy thật chỉ kiểm được ở 2.7.
- [x] 2.7 Đẩy lên và đo lần build đầu: thời gian, dung lượng image, đĩa còn trống; ghi vào `proposal.md` phần chi phí vận hành — CI `34916164838`: build 487 giây, image 1,19 GB, đĩa 14 GB → 6,0 GB. Lần đầu `34914702065` hỏng vì glibc, sửa ở fork `4373a32c`

## 3. Làm đỏ có chủ ý

- [x] 3.1 Trên một nhánh tạm, làm phép canh bản vá không tìm thấy ký hiệu; ghi mã lần chạy CI đỏ; xoá nhánh tạm — CI `34917662852` (`tmp/red-sentinel-guard`, đã xoá): đỏ ở `Require the Sentinel patch`, ba bước sau đều skipped, thông điệp nêu ký hiệu, tệp, fork, nhánh và commit `4373a32c`
- [x] 3.2 Chạy lại lần hai trên cùng commit fork; xác nhận bước build bị bỏ qua và ghi thời gian công việc — CI `34917485220` (push `249f384`): `Skipping build: …:4373a32c… is already in the registry`, bước `Build and push` = skipped, công việc `gateway-image` 9 giây (lần build thật 8 phút 45 giây)
- [x] 3.3 Trên một nhánh tạm, ghim compose vào một nhãn không tồn tại; ghi mã lần chạy đỏ; xoá nhánh tạm — CI `34917665176` (`tmp/red-compose-pin`, đã xoá): build skipped vì nhãn `4373a32c` đã có, rồi đỏ ở `Compose must pin a tag that exists` với `pins …:0000…0000, which is not in the registry`

## 4. Kho GHCR

- [x] 4.1 Người sở hữu đặt gói `ursweetheart/litellm_rang_dong` thành công khai (thao tác tay trên GitHub, chỉ sau khi 1.1 đạt) — 15/09/2026, API `visibility=public`. Lần thử đầu không được lưu; gói do workflow đẩy lên sinh ra riêng tư dù repo công khai
- [x] 4.2 `docker logout ghcr.io` rồi `docker pull` nhãn vừa build; xác nhận kéo được mà không đăng nhập — không `logout` (tránh xoá thông tin đăng nhập khác trên máy); chứng minh bằng `curl` ẩn danh: token ẩn danh lấy được, manifest `HTTP 200`, digest `sha256:7e888594…` khớp CI. Trước khi công khai: token 401, manifest 403
- [x] 4.3 `docker inspect` image kéo về: nhãn `revision` đúng commit fork, không có tệp `.env` nào trong image — `revision=4373a32c…`, `url=…/litellm_rang_dong`, `source=…/token-ledger-dashboard`; `.env*` duy nhất là `/app/docker/.env.example`; bản vá Sentinel có 3 lần; `python 3.13.15+`, `import math` chạy được

## 5. Compose

- [x] 5.1 `x-litellm`: bỏ `build:`, thêm `image: ${LITELLM_IMAGE:-ghcr.io/ursweetheart/litellm_rang_dong:<commit>}`, chuyển chú thích bản vá Sentinel lên trên dòng đó — nhãn `4373a32c…`
- [x] 5.2 `docker-compose.bench.yml`: `litellm-bench` dùng cùng biến image — cùng nguyên văn dòng `image:`; phép canh 5.4 kiểm hai dòng giống hệt nhau, vì neo YAML không đi qua được hai tệp
- [x] 5.3 `.env.example`: khai `LITELLM_IMAGE`, giá trị mặc định, và cách build tại chỗ từ `../litellm_tuan_test`
- [x] 5.4 Nhóm `guards`: khối `x-litellm` không được có `build:` hay `context:` trỏ ra ngoài repo; làm đỏ có chủ ý một lần — phép canh đã viết (cấm mọi `build:`/`context:` trong `x-litellm`, và bench phải ghim cùng image); 11 phép kiểm trên máy đạt, trong đó có trường hợp khối bench đọc lan sang khoá cấp cao nhất. Xanh trên CI `34919978157` (`be71c41`). Đỏ có chủ ý: CI `34920093402` (`tmp/red-compose-build`, đã xoá), `Canh cấu hình` hỏng ở đúng bước này, chỉ ra hai dòng `build:`/`context: ../litellm_tuan_test`; ba nhóm khác đạt
- [x] 5.5 Trong một bản sao repo không có thư mục ngang hàng, chạy `docker compose --profile gateway config`; xác nhận đạt — compose mới: `config` đạt, image duy nhất của Gateway là `ghcr.io/…:4373a32c…`, bench cũng vậy. Đối chứng compose cũ (`249f384`): `config` **cũng đạt**; nút chặn chỉ lộ ra ở bước build: `unable to prepare context: path ".../litellm_tuan_test" not found`, rc=1, tái hiện với một nhãn chưa từng build để giống máy mới. `--dry-run` không tái hiện được vì nó bỏ qua bước build
- [x] 5.6 Đo `docker compose pull --dry-run` và `docker compose --profile gateway pull --dry-run`; ghi xem các image `:local` có cần `--ignore-buildable` không — **CẦN**. Không có cờ: rc=1 cả hai trường hợp, `token-ledger-api:local` và `token-ledger-web:local` báo `authorization failed`. Có `--ignore-buildable`: rc=0, hai image đó `Skipped Image can be built`, image Gateway kéo được

## 6. Chuyển Gateway đang chạy sang image từ kho

> Gateway trên máy phát triển là bản local, tắt bật tự do (chốt 15/09/2026). Không cần làm lần lượt
> từng instance. Cách làm đó để dành cho máy chủ thật ở chặng 3.

- [x] 6.1 `docker compose --profile gateway pull`; grep `_SENTINEL_IGNORED_CONNECTION_ARGS` bên trong image mới — image đã kéo ở 4.3; grep trong CẢ HAI container đang chạy: 3 lần mỗi cái
- [x] 6.2 `docker compose --profile gateway up -d`, đợi hai instance healthy, gọi thử một lượt qua `gateway-lb`. Không `down`, không `--remove-orphans` — 15/09/2026 chạy `up -d litellm-1 litellm-2 gateway-lb` (không bật `api`/`web`/`pgadmin`); hai instance healthy sau khoảng 33 giây; `/health/liveliness` HTTP 200 qua `gateway-lb` (4000), `litellm-1` (4001), `litellm-2` (4002); log 3 phút đầu không có error/traceback. Không gọi model thật để không tốn tiền
- [x] 6.3 Xác nhận cả hai instance chạy image từ kho (`docker compose ps` và `docker inspect`) — cả hai: `ghcr.io/…:4373a32c…`, digest `sha256:7e888594…`, `revision=4373a32c…`
- [x] 6.4 Ghi cách quay lui đã kiểm được: `LITELLM_IMAGE=litellm_tuan_test:gateway` trong `.env`, rồi `up -d` lại từng instance — kiểm thật 15/09/2026 lúc 09:14, biến đặt trên dòng lệnh thay vì `.env` (compose đọc như nhau, không để lại gì):
  - **Quay lui:** `LITELLM_IMAGE=litellm_tuan_test:gateway docker compose --profile gateway up -d --wait litellm-1 litellm-2` → 43 giây, cả hai `image=litellm_tuan_test:gateway` (id `21536058b191`), healthy, `/health/liveliness` 200 qua `gateway-lb`, `litellm-1`, `litellm-2`; log không có traceback
  - **Trở lại:** `docker compose --profile gateway up -d --wait litellm-1 litellm-2` → 36 giây, cả hai digest `sha256:7e888594…`, healthy, 200 cả ba cổng
  - Redis, Sentinel, Postgres, `gateway-lb` không bị tạo lại. Không cần revert commit nào

## 7. Tài liệu và nghiệm thu

- [x] 7.1 `docs/reference/luat-trien-khai-tu-dong-13-09.md`: mục 5 (nút chặn `gateway` đã gỡ, việc gọi profile này thuộc chặng 3), mục 6 (bản clone sai nhánh không còn ảnh hưởng máy chạy), mục 7 (kết quả 5.6) — thêm: Luật 4 sửa thành `docker compose pull --ignore-buildable`, vì lệnh cũ thoát mã 1; nút chặn cũ lộ ở bước build chứ không ở `config`
- [x] 7.2 `docker/gateway/config.gateway.yaml`: chú thích "kiểm bằng grep trong image" trỏ về bước canh của CI
- [x] 7.3 `openspec validate package-the-gateway-image-in-ci --strict` đạt — 15/09/2026
