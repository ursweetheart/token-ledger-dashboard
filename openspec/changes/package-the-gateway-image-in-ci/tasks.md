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

- [ ] 3.1 Trên một nhánh tạm, làm phép canh bản vá không tìm thấy ký hiệu; ghi mã lần chạy CI đỏ; xoá nhánh tạm
- [ ] 3.2 Chạy lại lần hai trên cùng commit fork; xác nhận bước build bị bỏ qua và ghi thời gian công việc
- [ ] 3.3 Trên một nhánh tạm, ghim compose vào một nhãn không tồn tại; ghi mã lần chạy đỏ; xoá nhánh tạm

## 4. Kho GHCR

- [ ] 4.1 Người sở hữu đặt gói `ursweetheart/litellm_rang_dong` thành công khai (thao tác tay trên GitHub, chỉ sau khi 1.1 đạt)
- [ ] 4.2 `docker logout ghcr.io` rồi `docker pull` nhãn vừa build; xác nhận kéo được mà không đăng nhập
- [ ] 4.3 `docker inspect` image kéo về: nhãn `revision` đúng commit fork, không có tệp `.env` nào trong image

## 5. Compose

- [ ] 5.1 `x-litellm`: bỏ `build:`, thêm `image: ${LITELLM_IMAGE:-ghcr.io/ursweetheart/litellm_rang_dong:<commit>}`, chuyển chú thích bản vá Sentinel lên trên dòng đó
- [ ] 5.2 `docker-compose.bench.yml`: `litellm-bench` dùng cùng biến image
- [ ] 5.3 `.env.example`: khai `LITELLM_IMAGE`, giá trị mặc định, và cách build tại chỗ từ `../litellm_tuan_test`
- [ ] 5.4 Nhóm `guards`: khối `x-litellm` không được có `build:` hay `context:` trỏ ra ngoài repo; làm đỏ có chủ ý một lần
- [ ] 5.5 Trong một bản sao repo không có thư mục ngang hàng, chạy `docker compose --profile gateway config`; xác nhận đạt
- [ ] 5.6 Đo `docker compose pull --dry-run` và `docker compose --profile gateway pull --dry-run`; ghi xem các image `:local` có cần `--ignore-buildable` không

## 6. Chuyển Gateway đang chạy sang image từ kho

> Gateway trên máy phát triển là bản local, tắt bật tự do (chốt 15/09/2026). Không cần làm lần lượt
> từng instance. Cách làm đó để dành cho máy chủ thật ở chặng 3.

- [ ] 6.1 `docker compose --profile gateway pull`; grep `_SENTINEL_IGNORED_CONNECTION_ARGS` bên trong image mới
- [ ] 6.2 `docker compose --profile gateway up -d`, đợi hai instance healthy, gọi thử một lượt qua `gateway-lb`. Không `down`, không `--remove-orphans`
- [ ] 6.3 Xác nhận cả hai instance chạy image từ kho (`docker compose ps` và `docker inspect`)
- [ ] 6.4 Ghi cách quay lui đã kiểm được: `LITELLM_IMAGE=litellm_tuan_test:gateway` trong `.env`, rồi `up -d` lại từng instance

## 7. Tài liệu và nghiệm thu

- [ ] 7.1 `docs/reference/luat-trien-khai-tu-dong-13-09.md`: mục 5 (nút chặn `gateway` đã gỡ, việc gọi profile này thuộc chặng 3), mục 6 (bản clone sai nhánh không còn ảnh hưởng máy chạy), mục 7 (kết quả 5.6)
- [ ] 7.2 `docker/gateway/config.gateway.yaml`: chú thích "kiểm bằng grep trong image" trỏ về bước canh của CI
- [ ] 7.3 `openspec validate package-the-gateway-image-in-ci --strict` đạt
