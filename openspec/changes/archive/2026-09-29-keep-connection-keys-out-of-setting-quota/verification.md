# Kiểm chứng

## 2.5 Bộ test (29/09/2026, máy dev, Python 3.12)

| Bộ | Lệnh | Kết quả |
|---|---|---|
| stdlib (giống CI) | `python -m unittest discover -s tests -p "test_*.py"` | **208 test, OK** |
| connection config + auth | `python -m pytest tests/connection_config_cases.py tests/connection_auth_cases.py -q` | **26 passed, 27 subtests** |
| cả 4 bộ connection, fixture Docker cách ly | `CONNECTION_TEST_DSN=… python -m pytest tests/connection_{config,auth,admin,migration}_cases.py -q` | **59 passed, 27 subtests, 0 skipped** (111 s) |

- Mốc trước change: 201 test (ghi chú Master Plan 28/09). Change thêm 7 ca: 4 ở `ManagedKeyTests`,
  3 ở `RouteTests`. 201 + 7 = 208, khớp — tức 7 ca mới đã chạy và đạt. Mốc `EXPECTED_PY` trong
  `.github/workflows/ci.yml` đã nâng 201 → 208; không nâng thì CI đỏ.
- Ca 2.4 (tên key worker cấp mang tiền tố `connection-`) nằm trong
  `test_live_issue_unlimited_and_revocation` của `connection_admin_cases.py`, chạy trên fixture
  `tests/gateway-connections/compose.yaml` (migrate 001→015, `probe.py` PASS).
- Môi trường máy dev phải sửa trước khi chạy được bộ connection: Python312 thiếu `httpx2` (starlette
  1.6.0 đòi) và `PyYAML`. Đã cài `httpx2-2.13.1` và `pip install -r backend/requirements.txt pytest`
  (chỉ thêm `PyYAML-6.0.3`, không gói nào bị nâng).
- CI 28/09 (run 36343225406) dùng starlette **1.7.0** + `httpx` 0.28.1: 18 passed, chỉ cảnh báo
  "Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead". CI chưa hỏng,
  nhưng một bản starlette sau có thể bỏ hẳn `httpx` — khi đó `ci.yml:36` phải đổi sang `httpx2`.
  Ngoài phạm vi change này.

## Bản sạch: HEAD 931a7c8 + chỉ change này (mô phỏng đồng nghiệp pull về)

Working tree đang lẫn việc dở của change khác, nên đo lại trên `git worktree` tại HEAD, áp đúng các đoạn
của change này (7 file, +129/−3). Ba file lẫn việc khác (`tests/connection_admin_cases.py`, hai file
`docs/reference/`) được tách theo từng đoạn bằng danh sách cho phép.

| Bộ | Kết quả |
|---|---|
| `unittest discover -s tests -p "test_*.py"` | **208 OK** = `EXPECTED_PY: "208"` |
| `pytest` config + auth (`ci.yml:37`) | **18 passed, 9 subtests** (khớp CI 28/09) |
| cả 4 bộ connection trên fixture Docker | **45 passed, 9 subtests, 0 skipped** |

Không thêm gói, biến môi trường hay migration. HEAD đã tự đặt tên key `connection-…`
(`connection_worker.py:376, 518`), nên change không phụ thuộc việc dở nào.

Lưu ý khi commit: trong `test_live_issue_unlimited_and_revocation`, assert `key['models']==['*']` của
change `allow-any-provider-in-connections-tab` nằm sát 3 dòng của change này — không `git add` nguyên file.

## 4. Kiểm trên dashboard local (29/09/2026)

API chạy image build lại từ code của change (`python scripts/dashboard.py start`).

**Mức API** (script gọi thẳng, khoá đọc từ `.env`, không in ra):

| Endpoint | key_alias | Kết quả |
|---|---|---|
| `POST /api/quota` | `connection-750ea85b-…` | HTTP 409, `"Key này do tab Kết nối agent quản lý. Sửa hạn mức ở tab đó (cần khoá quản trị)."` |
| `POST /api/quota/top-up` | `connection-750ea85b-…` | HTTP 409, cùng câu |

**Mức giao diện** (Chrome, tab Setting):

- 4.1: key `connection-750ea85b-…` vẫn có trong danh sách (hạn mức 1.00, đã tiêu 0.0000). Bấm "Đặt thành"
  với 1 → dòng đó hiện "Không lưu được: Key này do tab Kết nối agent quản lý. Sửa hạn mức ở tab đó (cần
  khoá quản trị)."; hạn mức giữ 1.00; Lịch sử nạp không có dòng nào cho key này.
- 4.2: key thường `dms-feedback-2809`, bấm "Đặt thành" với đúng số đang có (1) → lưu được; Lịch sử nạp
  thêm đúng một dòng `2026-09-29T16:15:35+00:00  1.00 → 1.00  dashboard`; hạn mức giữ 1.00. Dòng
  `quota_log` này là dấu vết cố ý của phép thử, không xoá được.

Sự cố môi trường trong lúc kiểm (không do code của change): lần bật đầu tranh cổng 4401 với fixture test
còn chạy, để lại `litellm-1`/`litellm-2` không gắn mạng nào → không phân giải được `sentinel-*` → khởi
động lại liên tục. Sửa bằng `up -d --force-recreate litellm-1 litellm-2`.

## 0.1 So hạn mức key `connection-…` trên Gateway với `gateway_connection_key`

29/09/2026, máy dev, hai truy vấn trong phiên `default_transaction_read_only=on`
(database `token_ledger_v2` và `litellm` trong container `token-ledger-postgres`).

Luật so, đặt trước khi xem số (giống worker, `connection_worker.py:412-413`): `finite` thì `quota_usd`
trên Gateway phải bằng `usd`; `unlimited` thì Gateway không được có `quota_usd`; key chỉ có ở một phía
là lệch.

| key_alias | code | Sổ tab Kết nối | Gateway `quota_usd` | spend | `quota_log` |
|---|---|---|---|---|---|
| `connection-750ea85b-231e-4efa-a849-2f577910afda` | `dms-tap` | active, finite 1.0 | 1.0 | 0.0000483 | rỗng |

**Kết quả: 1 key, 0 lệch.** Không key nào chỉ có ở một phía.

`quota_log` rỗng: mỗi lần tab Setting sửa hạn mức đều nối thêm một dòng vào đó (`gateway._merge`).
Vậy tab Setting chưa từng sửa key này — lỗ hổng có thật trong code nhưng chưa bị dùng tới. Không cần
đặt lại hạn mức nào.
