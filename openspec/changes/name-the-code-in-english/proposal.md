## Why

Quy ước đã chốt từ 14/08 là **định danh tiếng Anh, ghi chú tiếng Việt**, nhưng code chỉ theo được một
nửa. Đếm ngày 15/09/2026 trong `backend/`, `db/`, `scripts/`, `tools/`:

| Loại | Số lượng |
|---|---|
| Dòng có chuỗi chứa chữ có dấu (`print`, lỗi, log; mẫu tìm này **đếm dư** dòng đầu docstring và comment SQL trong chuỗi, số thật đo ở task 0.3) | 357 dòng, 23 tệp |
| Chuỗi không dấu (đếm theo từ khoá, nên thiếu) | ít nhất 125 dòng, 27 tệp |
| Cờ dòng lệnh tiếng Việt (`--ra`, `--lat-mong`, `--hoa-don-cu`, `--chi-gateway`…) | khoảng 40 cờ, 13 tệp |
| Tên tệp tool/script tiếng Việt (`do_duong_llm.py`, `load_hd.py`…) | 20 tệp |

Hệ quả thấy được ngay trong phiên 15/09: cờ `--goc` của `tools/scan_secrets.py` không đoán được nghĩa, và
phần help của cờ `--fork` viết không dấu đã làm người đọc tưởng nó quét nội dung fork. Không có gì chặn
tiếng Việt quay lại, nên sửa tay một lần rồi sẽ trôi.

## What Changes

- **BREAKING (người chạy tay):** đổi tên 20 tệp tool/script sang tiếng Anh. Lệnh cũ như
  `python tools/do_duong_llm.py` không còn chạy.
- **BREAKING (người chạy tay):** đổi khoảng 40 cờ dòng lệnh tiếng Việt sang tiếng Anh. Không giữ bí danh
  cũ.
- Đổi sang tiếng Anh: chuỗi in ra màn hình, log, thông báo lỗi, `help` của argparse, tên hàm, tên biến,
  key trong dict, và câu lỗi HTTP của `backend/main.py`.
- Sửa cùng commit mọi chỗ gọi tên tệp hoặc cờ đã đổi: `scripts/refresh_gateway.py`
  (`--chi-gateway`), `scripts/update_dashboard.py` (`pull_hd_usage.py`), `scripts/rebuild_db.py`
  (`load_hd.py`), và các test đang kiểm chuỗi output.
- Sửa tài liệu **đang dùng** (`docs/reference/` trừ nhật ký, `openspec/specs/`) theo tên mới.
- **Phép canh mới trong nhóm `guards` của CI:** chặn tên tệp, cờ, định danh và chuỗi tiếng Việt quay lại
  code. Comment và docstring được phép.

**Giữ nguyên, có chủ ý:**

- Comment, docstring, `docs/`.
- 7 câu cảnh báo `message` trong `backend/store.py`: chúng hiện lên dashboard cho người dùng Việt, là
  nội dung sản phẩm.
- Tên tệp, thư mục và cột dữ liệu ghi xuống đĩa (`data/raw_web/tla-hd/`, `latency-daily.lech.csv`…):
  script khác đọc lại chúng, và `data/` là dữ liệu không thay thế được.
- Tên migration trong `db/migrations/` và giá trị đã ghi vào database.
- Nhật ký (`docs/reference/nhat-ky-*`), `docs/archive/`, `openspec/changes/archive/`: đó là lịch sử.
- `web/`: quy ước không đụng frontend.

## Capabilities

### New Capabilities

- `english-code-names`: Tên tệp, cờ dòng lệnh, định danh và chuỗi người lập trình đọc trong
  `backend/`, `db/`, `scripts/`, `tools/` là tiếng Anh; ngoại lệ phải được đánh dấu tại chỗ kèm lý do; CI
  chặn vi phạm quay lại.

### Modified Capabilities

(không có — `continuous-integration-checks` nói về bộ kiểm chạy trên máy sạch không cài gói. Phép canh
mới chạy bằng thư viện chuẩn của Python, đúng yêu cầu đó, và không đổi yêu cầu nào của spec ấy.)

## Impact

| Vùng | Việc |
|---|---|
| `tools/` | đổi tên 18 tệp; chuỗi, cờ, định danh |
| `scripts/` | đổi tên `pull_hd_usage.py`; cờ ở 8 tệp; chuỗi |
| `db/` | đổi tên `load_hd.py`; cờ `--chi-gateway`, `--kho`, `--tuy-chon`; chuỗi, định danh |
| `backend/` | câu lỗi HTTP ở `main.py`, chuỗi ở `check_api.py`; `store.py` chỉ đánh dấu ngoại lệ |
| `tests/` | theo chuỗi và key đã đổi |
| `.github/workflows/ci.yml` | bước canh mới trong `guards`; `EXPECTED_PY` tăng theo test của phép canh |
| `docs/reference/`, `openspec/specs/` | tên tệp và cờ mới |

**Hệ thống đang chạy:** dịch vụ `ledger-refresh` chạy `scripts/refresh_gateway.py` trong image `tools`.
Image đó phải build lại sau khi đổi, nếu không container cũ vẫn gọi cờ cũ. Gateway không bị ảnh hưởng.
