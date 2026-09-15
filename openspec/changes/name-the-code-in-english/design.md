## Context

Đo ngày 15/09/2026:

```
pham vi quet     backend/ db/ scripts/ tools/ tests/
chuoi co dau     357 dong / 23 tep  -- DEM DU: mau tim bat ca dong dau docstring
                 va comment SQL nam trong chuoi. So that do o task 0.3
comment SQL      37 dong `-- ...co dau` NAM TRONG chuoi SQL, 5 tep (backend/store.py: 25)
co tieng Viet    ~40 co / 13 tep, duoc nhac 110 lan trong 30 tep (docs, spec, archive)
ten tep Viet     20 tep, duoc nhac 83 lan trong 39 tep (phan lon la nhat ky va archive)
import           0 tep import module sap doi ten -> grep theo duong dan tep la du
tests/           CO dinh danh Viet: merge_monitoring.run(ra=, dot=),
                 load_provider.gop_cac_lan_keo, bien loi/ket/_luot_api/_canh_bao
```

**Đường chạy tự động gọi tên sắp đổi** — phải đổi cùng commit, nếu không pipeline gãy:

| Nơi gọi | Gọi gì |
|---|---|
| `scripts/refresh_gateway.py:80` (dịch vụ `ledger-refresh`) | `db/build_performance.py --chi-gateway` |
| `scripts/update_dashboard.py:155` (image `tools`) | `scripts/pull_hd_usage.py` |
| `scripts/rebuild_db.py:118` | `db/load_hd.py` |
| `scripts/update_dashboard.py:139` | `scripts/pull_web_apps.py --chi-kiem-token` (tệp đợt 3) |
| `scripts/rebuild_db.py:135` | `db/load_provider.py --tuy-chon` (tệp đợt 2) |
| `tests/test_load_provider.py`, `tests/test_merge_*.py` | chuỗi `ca lech`, key `summary["lech"]` |

Hai dòng giữa lộ ra lúc apply (15/09/2026): cờ của tệp đợt sau bị tệp đợt 1 gọi. **Đợt 1 đổi luôn phần
khai cờ** của `pull_web_apps.py` và `load_provider.py`; chuỗi và định danh của hai tệp đó vẫn ở đợt của
chúng. Không còn chỗ gọi cờ chéo nào khác (đã tìm mọi chuỗi `"--…"` ngoài `add_argument`).

**Key JSON tiếng Việt ghi xuống đĩa** (`tu_ngay`, `den_ngay`, `keo_luc`, `tong_luot` trong
`usage-day-user-model.json`) giữ nguyên, đánh dấu `vi-ok`: tệp đã kéo về đang mang chúng.

**Mã migration nằm trong database.** `revision = "012_nhip_tim_lam_moi"` được ghi vào bảng
`alembic_version`. Đổi tên thì `alembic upgrade` không còn tìm thấy phiên bản đang đứng.

**Giao diện không so khớp chữ của lỗi API.** Tìm trong `web/`: không có chỗ nào so `Khoa khong dung`,
`Thieu header`… Giao diện chỉ hiện `err.message`. `web/js/app.js` có nhắc `doi_chieu_cay_don_vi.py`
nhưng chỉ trong comment.

## Goals / Non-Goals

**Goals:**

- Người lập trình đọc được mọi tên tệp, cờ, định danh và output mà không cần biết tiếng Việt.
- Không đường chạy tự động nào gãy vì đổi tên.
- Tiếng Việt không quay lại được mà CI không báo.

**Non-Goals:**

- Dịch comment, docstring, `docs/`.
- Đổi nội dung người dùng dashboard đọc.
- Đổi dữ liệu đã ghi xuống đĩa hoặc vào database.
- Giữ bí danh cho tên tệp và cờ cũ. Người chạy tay chỉ có vài người, và bảng tra ở D1, D2 đủ để đổi thói
  quen.

## Decisions

### D1. Bảng đổi tên tệp (20 tệp, dùng `git mv` để giữ lịch sử)

| Cũ | Mới | Việc tệp làm |
|---|---|---|
| `tools/chan_doan_loi.py` | `tools/locate_data_defects.py` | chỉ ra chỗ lỗi mà bước kiểm dữ liệu đếm được |
| `tools/doi_chieu_tla_hd.py` | `tools/reconcile_tla_contract.py` | đối chiếu TLA Hợp Đồng với Google |
| `tools/doi_chieu_web_vs_file.py` | `tools/reconcile_web_vs_files.py` | so tệp cào với giao diện web |
| `tools/kiem_ke_de_len_plan.py` | `tools/inventory_datasets.py` | kiểm kê dataset theo nhu cầu database |
| `tools/kiem_tra_du_lieu.py` | `tools/verify_datasets.py` | kiểm mọi dataset trong `data/` |
| `tools/kiem_tu_raw.py` | `tools/recheck_from_raw.py` | tính lại kết luận từ dữ liệu raw |
| `tools/pham_vi_moi.py` | `tools/remaining_scope.py` | phần còn lại sau 3 quyết định phạm vi |
| `tools/soat_ctda.py` | `tools/audit_ctda.py` | mọi lỗi của dataset CTDA (Ralli) |
| `tools/trich_yeu_cau_dashboard.py` | `tools/extract_dashboard_requirements.py` | trích thứ dashboard cần |
| `tools/doi_chieu_cay_don_vi.py` | `tools/reconcile_org_tree.py` | so cây đơn vị cứng với database |
| `tools/do_tien_suy_ra.py` | `tools/measure_derived_cost.py` | đo tỷ lệ tiền suy ra |
| `tools/kiem_so_artifact.py` | `tools/verify_artifact_numbers.py` | kiểm từng con số trong artifact |
| `tools/soat_khoa_api.py` | `tools/audit_api_auth.py` | soát lớp xác thực API |
| `tools/soat_du_lieu_cao.py` | `tools/audit_scraped_files.py` | soát tệp vừa cào |
| `tools/do_duong_llm.py` | `tools/measure_llm_path.py` | đo một đường gọi LLM |
| `tools/dien_tap_gateway.py` | `tools/gateway_drill.py` | diễn tập Gateway |
| `tools/bench/goi_thu_tuyen_that.py` | `tools/bench/probe_live_route.py` | gọi thật để xem hạn mức nào chặn trước |
| `tools/bench/do_dinh_tuyen_khi_om.py` | `tools/bench/measure_routing_when_unhealthy.py` | nginx có gửi vào instance ốm không |
| `db/load_hd.py` | `db/load_tla_contract.py` | nạp số liệu TLA Hợp Đồng |
| `scripts/pull_hd_usage.py` | `scripts/pull_tla_contract_usage.py` | kéo số liệu TLA Hợp Đồng |

`tools/baseline_db.py` vốn đã là tiếng Anh, giữ. Tên logger đi theo tên tệp (`get_logger("load_hd")` →
`"load_tla_contract"`).

### D2. Bảng đổi tên cờ (không giữ cờ cũ)

| Tệp | Cũ → Mới |
|---|---|
| `scripts/update_dashboard.py` | `--hoa-don-cu` → `--allow-stale-billing`; `--bo-monitoring` → `--skip-monitoring`; `--ngay-monitoring` → `--monitoring-days` |
| `scripts/pull_web_apps.py` | `--ra` → `--out`; `--lat-mong` → `--thin-slice`; `--chi-kiem-token` → `--token-only` |
| `scripts/pull_sku_catalog.py` | `--tim-dich-vu` → `--list-services`; `--dich` → `--out` |
| `scripts/pull_tla_contract_usage.py` | `--lat-mong` → `--thin-slice`; `--den-ngay` → `--until` |
| `scripts/make_readable.py` | `--loc` → `--filter` |
| `scripts/merge_monitoring.py` | `--dot` → `--batches`; `--ra` → `--out`; `--tho` → `--raw`; `--dich` → `--out-root` |
| `scripts/merge_latency_daily.py` | `--theo-method` → `--by-method` |
| `scripts/merge_billing.py` | `--thu-muc` → `--folder`; `--ra` → `--out`; `--doi-chieu` → `--reconcile` |
| `tools/verify_datasets.py` | `--bo-qua-monitoring` → `--skip-monitoring`; `--bao-cao` → `--report` |
| `tools/measure_llm_path.py` | `--duong` → `--route` (giá trị `truc-tiep` → `direct`); `--khoa-bien` → `--key-env`; `--so-luot` → `--calls`; `--nguoi-dung` → `--user`; `--cau` → `--prompt`; `--he-thong` → `--system`; `--nhap` → `--prompts-file`; `--nhiet-do` → `--temperature`; `--token-ra-toi-da` → `--max-output-tokens`; `--tat-json` → `--no-json`; `--nghi` → `--pause`; `--rung` → `--jitter`; `--han-giay` → `--timeout`; `--ra` → `--out`; `--thu-kho` → `--dry-run` |
| `db/load_provider.py` | `--kho` → `--dry-run`; `--tuy-chon` → `--optional` |
| `db/build_performance.py` | `--chi-gateway` → `--gateway-only` |

Nơi `dest=` đã là tiếng Anh thì giữ `dest`, chỉ đổi chữ cờ. Nơi **không có** `dest` (như `--hoa-don-cu`,
`--chi-gateway`, `--tuy-chon`), argparse lấy tên thuộc tính từ chữ cờ, nên thân hàm đang đọc
`args.hoa_don_cu` phải sửa theo tên mới.

**Tắt viết tắt ở mọi parser: `ArgumentParser(..., allow_abbrev=False)`.** Mặc định argparse nhận cờ viết
tắt, nên một cờ cũ là **tiền tố** của một cờ mới sẽ chạy im lặng với nghĩa khác. Rà cả bảng trên, có đúng
một va chạm: `merge_monitoring.py` cũ `--ra X` (thư mục đầu ra) sẽ được hiểu là `--raw X` (thư mục dữ liệu
thô). Tắt viết tắt thì mọi cờ cũ đều hỏng ồn ào với `unrecognized arguments`, kể cả va chạm chưa ai thấy.

**Giá trị mặc định là dữ liệu thì giữ.** `--user` của `measure_llm_path.py` mặc định
`svc.do-duong-llm`: giá trị này là header `X-User` và đã nằm trong sổ Gateway làm khoá quy người dùng. Đổi
nó là tách một người dùng thành hai trong dữ liệu. Giữ, kèm dấu ngoại lệ (D5).

### D3. Cái gì giữ tiếng Việt, và vì sao

| Giữ | Vì sao |
|---|---|
| comment, docstring, `docs/` | quy ước 14/08 |
| 7 câu `message` trong `backend/store.py` | hiện lên dashboard cho người dùng Việt |
| `db/migrations/` (tên tệp, `revision`, SQL) | mã phiên bản đã ghi trong `alembic_version` |
| tên tệp/thư mục/cột ghi xuống đĩa (`data/raw_web/tla-hd/`, `*.lech.csv`, `ket-qua-kiem-tra.csv`) | script khác đọc lại; `data/` không thay thế được |
| giá trị đã ghi vào dữ liệu (`svc.do-duong-llm`, tên phòng ban…) | đổi là tách một thực thể thành hai |
| nhật ký, `docs/archive/`, `openspec/changes/archive/` | lịch sử; tên cũ tra được qua D1, D2 |
| `web/` | quy ước không đụng frontend |

### D4. Cách đổi chuỗi

- Output, log, lỗi, `help`: tiếng Anh ngắn, **giữ nguyên mọi con số và tên dữ liệu**.
- Câu tiếng Việt đang mang lý do quan trọng thì lý do chuyển lên comment ngay trên dòng, không mất.
- Không đổi ý nghĩa, mức log, mã thoát, hay thứ tự in. Test đang so chuỗi thì sửa test theo đúng chuỗi mới,
  không nới phép so.

### D5. Phép canh: `tools/check_english_names.py`

Chỉ dùng thư viện chuẩn (`ast`, `tokenize`, `pathlib`), chạy trong `guards` như các bước khác, không cài gói.

Quét các tệp `.py` trong `backend/ db/ scripts/ tools/ tests/`, bỏ qua `db/migrations/`. Test JavaScript
(`tests/*.test.js`) đứng ngoài: nó thuộc phía frontend. Năm phép:

1. **Tên tệp** `.py`/`.sh`: tách theo `_ - .`, có mảnh nằm trong danh sách từ tiếng Việt → hỏng.
2. **Cờ dòng lệnh**: chuỗi bắt đầu bằng `--` trong lời gọi `add_argument` → tách mảnh, như trên.
3. **Định danh**: tên hàm, lớp, tham số, biến gán, thuộc tính gán (`self.ra = …`), tên tham số khi gọi
   (`run(ra=…)`) → tách mảnh, như trên.
4. **Chuỗi**: có ký tự có dấu tiếng Việt → hỏng; không dấu mà có **từ 2 mảnh** trở lên trong danh sách từ
   → hỏng. Không xét: docstring, và mọi chuỗi **đứng một mình thành câu lệnh** (dùng như comment).
   **Chuỗi SQL** (có từ khoá `SELECT`/`FROM`/`WITH`/`INSERT`/`UPDATE`/`CREATE` viết hoa) thì bỏ phần từ `--`
   tới hết dòng trước khi xét: đó là comment SQL, đo được 37 dòng như vậy. Chuỗi không phải SQL thì giữ
   nguyên, vì `--` ở đó thường là dấu ngăn trong output (`"0 findings -- pass"`).
5. **Viết tắt cờ**: mọi lời gọi `ArgumentParser(...)` phải có `allow_abbrev=False` (D2).

**Ngoại lệ đánh dấu tại dòng:** `# vi-ok: <lý do>`. Chuỗi trải nhiều dòng thì dấu nằm ở **bất kỳ dòng nào**
trong khoảng dòng của chuỗi đó. Không có lý do thì chính dấu đó hỏng. Không có danh sách tệp miễn trừ: miễn
cả tệp là mở chỗ mù vĩnh viễn (bài học `scan_secrets.py`, 26/08).

**Danh sách từ** chỉ gồm âm tiết tiếng Việt không trùng từ tiếng Anh thông dụng (`khong`, `kiem`, `soat`,
`doi`, `chieu`, `lech`, `gop`, `nap`, `keo`, `ngay`, `nguon`, `thieu`, `dong`, `loi`, `luot`, `canh`,
`bao`, `ra`…). Bỏ những mảnh trùng từ tiếng Anh (`do`, `to`, `ban`, `loc`, `den`, `dot`) hoặc quá ngắn và dễ trùng
viết tắt (`ket`). Vì vậy
`dot=` và `ket` không bị phép canh bắt; đổi tay ở đợt 2–3.
`ponytail:` danh sách từ là heuristic, bắt chuỗi không dấu theo từ khoá nên có thể lọt câu toàn từ lạ; nâng
cấp khi thấy lọt thật bằng cách thêm từ, không đổi sang mô hình nhận dạng ngôn ngữ.

Mã thoát 0 = sạch, 1 = có vi phạm (in `tệp:dòng  [loại]  mảnh bắt được`), 2 = lỗi khi chạy.

**Mốc đo trước khi sửa (task 0.3, 15/09/2026):** 1.222 vi phạm trong 56 tệp.

| Loại | Số | | Thư mục | Số |
|---|---|---|---|---|
| chuỗi (từ không dấu) | 695 | | `tools/` | 652 |
| định danh | 301 | | `scripts/` | 285 |
| chuỗi (có dấu) | 142 | | `db/` | 224 |
| cờ dòng lệnh | 34 | | `backend/` | 54 |
| parser bật viết tắt | 32 | | `tests/` | 7 |
| tên tệp | 18 | | | |

Soát báo nhầm: xem mẫu của 15 mảnh dễ trùng tiếng Anh nhất (`tong`, `gia`, `bao`, `chi`, `sai`, `hai`,
`khi`, `mau`, `dau`, `tang`, `bo`, `cau`, `trong`, `nhu`, `mot`), **mọi dòng mẫu đều là tiếng Việt thật**
(`canh bao`, `truoc khi tuyen`, `chi_tiet`, `gia_tri`). Chưa thấy báo nhầm.

Soát bỏ lọt, so với bảng D1, D2: bản đầu bắt 29/39 cờ; thêm `kho tuy chon theo tat cac tiet trung` thì
bắt **34/39**. Còn lọt, có chủ ý vì trùng tiếng Anh: `--dot`, `--tho`, `--loc`, `--he-thong`, `--rung`.
Tên tệp bắt **18/20**: lọt `db/load_hd.py`, `scripts/pull_hd_usage.py`, vì `hd` trùng viết tắt "HD". Các
chỗ lọt này vẫn được đổi tay theo D1, D2.

Kèm `tests/test_check_english_names.py`: mỗi phép một cặp đạt/hỏng, cộng docstring và comment được phép,
dấu `vi-ok` thiếu lý do thì hỏng. `EXPECTED_PY` tăng đúng số test thêm.

**Phải làm đỏ có chủ ý trên CI một lần**, như mọi phép canh trước.

### D6. Thứ tự làm: rủi ro cao trước, mỗi đợt một commit

| Đợt | Nội dung | Vì sao trước |
|---|---|---|
| 0 | viết phép canh, chạy trên cây hiện tại để có **mốc số vi phạm**; chưa bật trong CI | đo trước khi sửa |
| 1 | đường chạy tự động: `refresh_gateway`, `build_performance`, `update_dashboard`, `rebuild_db`, `load_hd`→`load_tla_contract`, `pull_hd_usage`→`pull_tla_contract_usage`, `connect.py`, `audit_db.py`, `load_gateway.py`, `backend/` | compose và image `tools` chạy chúng |
| 2 | phần còn lại của `db/` | dựng database |
| 3 | phần còn lại của `scripts/` | gọi API thật |
| 4 | `tools/` | chạy tay |
| 5 | tài liệu đang dùng; bật phép canh trong CI; làm đỏ có chủ ý | chỉ bật khi đã về 0 |

**Kiểm mỗi đợt, không chạy script nào ghi database hay gọi API thật:** `py_compile` mọi tệp; `--help`
mọi tệp có argparse; `python -m unittest` đủ số và đạt; số vi phạm của phép canh giảm và không tăng ở tệp
ngoài đợt; `grep` tên tệp và cờ cũ ra 0 trong code và tài liệu đang dùng.

## Risks / Trade-offs

- **[Container `ledger-refresh` đang chạy image `tools` cũ]** Nó vẫn gọi `--chi-gateway` cho tới khi build
  lại; sau khi code đổi thì build lại mới đúng.
  → Build lại và `up -d` dịch vụ đó sau đợt 1, xin phép trước. Không `down`, không `--remove-orphans`.
- **[Có chỗ gọi tên cũ mà grep không thấy]** Ví dụ tên ghép chuỗi lúc chạy.
  → Sau mỗi đợt, `grep` tên cũ trong toàn repo trừ lịch sử, cả `.ps1`, `.sh`, `.md`, `.yml`; chạy `--help`
  của mọi tệp gọi tệp khác.
- **[Phép canh báo nhầm]** Danh sách từ bắt trúng tên tiếng Anh.
  → Mốc đợt 0 cho thấy báo nhầm trước khi bật; sửa danh sách từ, không dùng `vi-ok` để che báo nhầm.
- **[Người quen lệnh cũ]** Lệnh cũ báo `unrecognized arguments` hoặc `No such file`.
  → Hỏng ồn ào, không hỏng im lặng; bảng D1, D2 là chỗ tra.
- **[Chí Thanh đang dùng tên cũ]** `tools/gateway-smoke/` của Chí Thanh có thể gọi tool của repo.
  → `grep` tên cũ trong thư mục đó ở đợt 4; nhắn Chí Thanh khi merge.

## Migration Plan

1. Đợt 0–4 trên `Tuan-develop`, mỗi đợt một commit, CI xanh sau mỗi đợt.
2. Sau đợt 1: build lại image `tools`, `up -d ledger-refresh`, xem một chu kỳ làm mới chạy hết không lỗi.
3. Đợt 5: bật phép canh; làm đỏ có chủ ý trên nhánh tạm; xoá nhánh tạm.

**Quay lui:** `git revert` từng đợt. Không có dữ liệu nào bị đổi, nên revert là đủ.

## Open Questions

- Build lại `ledger-refresh` ngay sau đợt 1, hay đợi lần triển khai kế tiếp? Mặc định: ngay sau đợt 1, xin
  phép trước.
