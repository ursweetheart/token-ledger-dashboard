## Why

Biến `KEY_BENCH_CRM_TEST_GG_AIA_STU` giữ khoá nhà cung cấp của tuyến **production** cho agent Phân
Loại Dữ Liệu CRM (`config.gateway.yaml:86`). Cái tên nói sai ba lần:

| Mảnh tên | Nói là | Thật là |
|---|---|---|
| `BENCH` | dùng cho đo hiệu năng | tuyến production, agent 7 gọi thật hằng ngày |
| `TEST` | khoá thử | khoá thật, có tính tiền |
| `GG_AIA_STU` | khoá Google AI Studio | khoá **Vertex express** — đo 10/09/2026, tiền tố `AQ.`, 53 ký tự |

Chỉ mảnh `CRM` là đúng.

**Cái tên này đã gây một sự cố, không phải một phiền toái.** Ngày 10/09/2026, `.env` đã đổi tên biến
trong khi `docker-compose.yml` và `config.gateway.yaml` vẫn giữ tên cũ `KEY_BENCH_CRM_TEST`. Vì
compose viết `${KEY_BENCH_CRM_TEST:-}`, dấu `:-` biến một biến thiếu thành **chuỗi rỗng** thay vì
báo lỗi. Hệ quả đo được: container lên bình thường, `/health/liveliness` trả `200`, mọi phép kiểm
đạt — và tuyến CRM chỉ chết đúng lúc có người gọi thật, với `HTTP 500 "Missing Gemini API key"`.

Cùng một lỗi nằm ở **ba** chỗ hôm ấy, và chỉ một chỗ được sửa ở lần đầu.

**Một sự cố nữa đã suýt xảy ra trong lúc bàn change này (17/09/2026).** Bản đồ khoá bị đọc ngược —
`KEY_GOOGLE_AI_STU` bị tưởng là của CRM, `KEY_BENCH_CRM_TEST_GG_AIA_STU` bị tưởng là của DMS. Đọc
ngược là hợp lý: tài liệu đã ghi rằng hậu tố tên gây hiểu nhầm, nên người đọc lật cả tên, trong khi
chỉ nửa sau sai. Nếu đổi tên theo bản đồ ngược ấy thì hai khoá hoán vị nhau, hai tuyến **vẫn trả
`200`**, và tiền rơi sai project mà không phép kiểm nào hiện có bắt được.

Tên sai không chỉ khó đọc. Ở đây nó là nguyên liệu để sinh ra một lớp hỏng im lặng.

**Tên mới lấy từ định danh đã có, không bịa mới:** cột `dim_agent.code` — cùng chuỗi đang làm nhãn
trên tuyến (`tags: ["crm-feedback"]`). Nhờ vậy sinh ra được một bất biến kiểm bằng máy, và những
khoá thêm sau này có sẵn tên mà không phải bàn.

## What Changes

- **BREAKING (người vận hành):** `KEY_BENCH_CRM_TEST_GG_AIA_STU` → `KEY_CRM_FEEDBACK`. Không giữ
  tên cũ làm bí danh. Máy nào đang chạy Gateway phải sửa `.env` khi nhận commit này, nếu không
  `docker/gateway/entrypoint.sh` dừng hẳn với `STOP: KEY_CRM_FEEDBACK is missing.`
- Đổi tên trong **một commit** ở cả năm tệp được quản lý phiên bản: `.env.example`,
  `docker-compose.yml`, `docker/gateway/entrypoint.sh`, `docker/gateway/config.gateway.yaml`,
  `docker-compose.bench.yml`.
- Sửa chú thích đi kèm: đoạn ở `docker-compose.yml:121-133` giải thích hậu tố `_GG_AIA_STU` gây hiểu
  nhầm — sau khi đổi tên thì đoạn ấy nói về một cái tên không còn tồn tại. Giữ lại **sự thật đã đo**
  (khoá này là Vertex express, tiền tố `AQ.`) vì nó quyết định tuyến đi đường nào.
- Sửa tài liệu **đang dùng** gọi tên cũ: `docs/reference/fallback-crm-12-09.md`,
  `docs/reference/gateway-architecture-and-agent-integration.md`.
- **Phép canh mới trong nhóm `guards` của CI:** mọi biến `os.environ/KEY_*` mà
  `config.gateway.yaml` tham chiếu SHALL có mặt ở cả ba nơi — vòng kiểm bắt buộc của
  `entrypoint.sh`, khối `x-litellm` của `docker-compose.yml`, và `docker-compose.bench.yml`. Đây là
  phép canh bắt được đúng sự cố 10/09.

**Giữ nguyên, có chủ ý:**

- **`KEY_GOOGLE_AI_STU` KHÔNG đổi tên trong change này.** Nó phục vụ **ba** tuyến
  (`gemini-flash`, `gemini-flash-preview`, `gemini-flash-lite`), trong đó chỉ một tuyến mang nhãn
  `dms-feedback`. Đặt tên nó theo một agent là hẹp hơn sự thật. Trả lời được câu "ai đang gọi
  `gemini-flash-preview`" rồi mới đổi — xem `design.md` D3.
- **Giá trị khoá.** Change này đổi **tên biến**, không đổi khoá, không cấp khoá mới, không đụng
  `.env` trong kho (`.env` nằm trong `.gitignore`).
- **Nhãn `tags: ["crm-feedback"]`.** Đã đúng và đã khớp `dim_agent.code`.
- **Lịch sử.** `docs/decisions/che-do-hong-cua-gateway-2026-09-10.md`,
  `docs/archive/`, `openspec/changes/archive/`: đó là biên bản của việc đã xảy ra, sửa vào là làm
  hỏng bằng chứng.

## Capabilities

### New Capabilities

- `provider-key-naming`: Tên biến môi trường giữ khoá nhà cung cấp phải suy ra được agent dùng nó,
  và phải khớp định danh agent đã có trong danh mục; việc đổi tên một biến như thế phải đáp xuống
  mọi tệp tham chiếu trong cùng một commit; và CI chặn trường hợp một tuyến tham chiếu biến mà vòng
  kiểm khởi động không biết tới.

### Modified Capabilities

(không có — `crm-gateway-routing` có yêu cầu "Bí mật xác thực MUST NOT nằm trong mã nguồn", nói về
**nơi cất** giá trị bí mật. Change này đổi **tên tham chiếu**; giá trị vẫn nằm ngoài kho, tệp cấu
hình vẫn chỉ chứa tham chiếu. Không yêu cầu nào của spec ấy đổi.)

## Impact

| Vùng | Việc |
|---|---|
| `.env.example` | tên mới, chú thích viết lại |
| `docker-compose.yml` | biến trong `x-litellm`; chú thích dòng 121-133 |
| `docker/gateway/entrypoint.sh` | tên trong vòng kiểm bắt buộc |
| `docker/gateway/config.gateway.yaml` | `api_key: os.environ/…` của tuyến `gemini-2.5-flash` |
| `docker-compose.bench.yml` | giá trị cố ý sai, tên mới |
| `.github/workflows/ci.yml` | phép canh mới trong nhóm `guards`; `EXPECTED_PY` tăng |
| `docs/reference/` | hai tài liệu đang dùng |

**Hệ thống đang chạy:** đổi tên biến môi trường buộc phải **dựng lại** container LiteLLM, không phải
`restart` — biến môi trường chỉ đặt được lúc tạo container. Việc dựng lại đổi địa chỉ IP của
container, mà `docker/gateway/nginx.conf` hiện phân giải tên upstream một lần lúc khởi động, nên
**phải khởi động lại `gateway-lb` sau cùng**, với cả hai instance đang `healthy`.

Change `keep-the-load-balancer-pointed-at-live-instances` xoá bỏ ràng buộc ấy. Hai change độc lập
với nhau; làm change kia trước thì mục 3 của `tasks.md` ngắn đi một bước.

**Chế độ hỏng nếu sót một tệp:** sót `.env`, `docker-compose.yml` hay `entrypoint.sh` thì **kêu to** —
entrypoint dừng, container không lên. Sót `config.gateway.yaml` thì **im lặng** — container khoẻ,
`/health/liveliness` trả `200`, tuyến chỉ chết khi có người gọi thật. Đó là lý do mục 2 của
`tasks.md` bắt buộc một lượt gọi thật, và lý do phép canh ở mục 4 tồn tại.
