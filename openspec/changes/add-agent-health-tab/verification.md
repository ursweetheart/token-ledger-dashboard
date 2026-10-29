# Biên bản kiểm thử — add-agent-health-tab

Ngày 29/10/2026, trên máy dev. Giờ là giờ Việt Nam.

## Test tự động

| Bộ | Kết quả |
|---|---|
| `unittest discover -s tests -p "test_*.py"` (máy thường) | 244 test, OK |
| như trên, giả lập máy sạch (`python -S`, chỉ thư viện chuẩn) | 244 test, OK |
| `pytest` connection_config/auth/rollout_cases | 41 passed, 27 subtests |
| `node --check` agent-health.js, api.js | OK |

Lỗi tìm được và đã sửa: `watch_agents.py` từng `import yaml` ở đầu tệp, nên trên máy sạch cả tệp
`test_watch_agents` không nạp được (215 test, 1 lỗi; CI sẽ đỏ). Nay yaml chỉ được import trong
`load_config`; phần kiểm cấu hình tách thành `check_config` và test bằng dict. Phép kiểm "tệp YAML
thật đọc được" chuyển sang `tests/connection_auth_cases.py` (job CI có cài gói).

## Database dev (PostgreSQL 17, `token_ledger_v2`)

Migration `015_gateway_connections` → `016_agent_health`. Script kiểm: 16/16 PASS, dọn sạch dòng thử.

- `api_readonly` đọc được 3 bảng.
- Lần chạy thứ hai bị database từ chối (index duy nhất).
- Lịch gặp lần chạy tay đang chờ thì đợi, không ghi `last_run_date`; lần chạy tay không đổi `last_run_date`.
- Lịch chỉ nhận một lần mỗi ngày; khởi động lại chuyển lần chạy dở sang `interrupted`.
- Vai `connection_admin` (nút Apply, Chạy ngay) `UPDATE` được `agent_health_setting` và `INSERT` được
  `agent_health_run`. Kiểm trong transaction rồi `ROLLBACK`.

## Trợ lý ảo Ralli (ralli) — gọi thật

**`--once --dry-run`** (10:16:05): `capabilities` ok, HTTP 200, 172 ms. Bỏ qua `POST`. Không ghi DB.

**`--once`** (10:16:46), lần gọi LLM đã được người dùng duyệt:

| Phép kiểm | Kết quả | HTTP | Thời gian | `X-Request-ID` |
|---|---|---|---|---|
| capabilities | ok | 200 | 78 ms | `3ec5333c-af3f-4bf8-89dd-b6e4d3ca5d57` |
| llm (`POST /ctda/v2/analyze`) | ok | 200 | 15.155 ms | `17549353-b4a6-45ae-b84e-38c4c4ddd065` |

- Câu hỏi: "Phân tích ngắn tình hình chăm sóc công trình dự án tháng này".
- `data.feature` khác `clarification`, và thời gian 15,2 giây (câu chào ngày 29/10 chỉ 0,19 giây):
  câu hỏi đã đi tới LLM, không bị trả câu soạn sẵn.
- Lần chạy: `4b9c5fd6-361e-4ca5-839a-05036afed93e`, `trigger = manual`, `requested_by = cli`,
  `done 2/2`, 15,5 giây. `last_run_date` vẫn trống sau lần chạy tay.
- Dòng kết quả được giữ lại trong DB dev để kiểm tab trên dashboard.

## Dashboard thật (container `api`, `web`, `agent-health-watch`)

Trước khi bật service, `last_run_date` được đặt bằng hôm nay để service không chạy bù lịch 08:00
(người dùng chọn, tránh thêm một câu LLM). Log service: `Loaded 1 agent(s): ralli`, không chạy bù.

Bấm "Chạy ngay" trên tab (10:24:36), câu LLM thứ hai trong ngày:

| Phép kiểm | Kết quả | HTTP | Thời gian | `X-Request-ID` |
|---|---|---|---|---|
| capabilities | ok | 200 | 124 ms | `2a69307c-6512-4350-b176-529fa0213b1b` |
| llm | ok | 200 | 15.959 ms | `9eb7161a-147b-486f-939f-32a29774a27e` |

- `POST /api/agent-health/run` → 202. Service nhận việc sau 0,9 giây, chạy 16,2 giây.
- `requested_by = connection-admin`. `last_run_date` không đổi sau lần chạy tay.
- Trình duyệt hỏi `GET /api/agent-health/runs/{id}` khoảng mỗi giây (22 lần), rồi tải lại tab khi xong.

### Nút Apply — lỗi tìm được và đã sửa

- Lần Apply đầu (10:25:28) trả 200, nhưng gửi lên 08:00 chứ không phải giờ người dùng đã gõ (API trả
  `{"run_at":"08:00",…}`). Nguyên nhân trong `agent-health.js`: tab tải lại sau mỗi lần chạy xong và
  ghi đè ô giờ bằng giờ trong DB, trừ khi con trỏ đang ở trong ô. Gõ giờ → bấm Chạy ngay → chạy xong →
  ô quay về 08:00 → Apply gửi 08:00. (Thứ tự thao tác là suy luận khớp log; lỗi ghi đè thì chắc chắn.)
- Sửa: chỉ ghi đè khi ô trống hoặc vẫn bằng giờ đang hiện từ DB.
- Sau khi sửa (10:29:18): `PUT` 200, `run_at = 22:00`, `updated_by = connection-admin`. Không lần chạy
  nào bắt đầu (`last_run_date` đã là hôm nay). Trước đó có 2 lần `PUT` trả 401 (10:28:51, 10:28:54):
  khoá nhập sai (khoá dashboard thì là 403; ô trống thì trình duyệt không gửi).

## Đổi sang tài liệu JSON ở DB và tệp (29/10/2026, sau buổi thử trên)

- Test: unittest 253 (máy thường và máy sạch `-S`), pytest 41 passed, `node --test` 117/117.
- DB dev: tắt service, xoá ba bảng cũ, lùi `alembic_version` về 015, áp lại 016. Script kiểm 18/18 PASS:
  bảng `agent_health_result` không còn; `begin` trả phần đầu tài liệu theo giờ VN (`+07:00`); cột
  `result` giữ đúng tiếng Việt qua jsonb. Vai `connection_admin` vẫn `UPDATE` setting và `INSERT` run
  được (đã `ROLLBACK`). Hai lần chạy thử ở trên bị xoá cùng bảng cũ; số liệu của chúng còn ở biên bản này.
- Đặt lại giờ 22:00 và `last_run_date` = 29/10 để service không chạy bù (không tốn LLM).
- Container: service đọc YAML mới (`kind`, `question_field` qua kiểm), không chạy bù; ghi được vào
  `/app/var/agent-checks` (tạo rồi xoá một tệp thử). `git check-ignore` xác nhận `var/agent-checks/` bị bỏ qua.

## Chưa kiểm

- Một lần chạy thật với khuôn mới: `result.json` trên đĩa, `body` của câu hỏi Ralli, đường dẫn `answer`.
- Tải lại trang (F5) giữa lúc đang chạy: log không có request tải lại trang trong 18 giây chạy.
- Lịch chạy trong container (đã chặn chạy bù hôm nay).
