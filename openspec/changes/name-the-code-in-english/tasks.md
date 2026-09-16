## 0. Phép canh và mốc đo (chưa bật trong CI)

- [x] 0.1 Viết `tools/check_english_names.py` theo D5: 5 phép (tên tệp, cờ, định danh gồm thuộc tính gán và tham số khi gọi, chuỗi, `allow_abbrev=False`), dấu `# vi-ok: <lý do>` áp cho cả chuỗi nhiều dòng, bỏ comment `--` trong chuỗi SQL, bỏ qua docstring và chuỗi đứng một mình, bỏ qua `db/migrations/`, chỉ thư viện chuẩn, mã thoát 0/1/2
- [x] 0.2 Viết `tests/test_check_english_names.py`: mỗi phép một cặp đạt/hỏng; comment, docstring và chuỗi đứng một mình tiếng Việt đạt; comment SQL có dấu trong chuỗi SQL đạt nhưng phần SQL có chữ Việt vẫn hỏng; `"x -- đạt"` ngoài SQL hỏng; `vi-ok` ở dòng giữa một chuỗi nhiều dòng đạt; `vi-ok` thiếu lý do hỏng; parser thiếu `allow_abbrev=False` hỏng; migration không bị xét tên
- [x] 0.3 Chạy phép canh trên cây hiện tại; ghi mốc số vi phạm theo loại và theo thư mục vào `design.md`; soát báo nhầm và sửa danh sách từ (không dùng `vi-ok` để che báo nhầm)

## 1. Đường chạy tự động (một commit)

- [x] 1.1 `db/build_performance.py`: `--chi-gateway` → `--gateway-only`; sửa `scripts/refresh_gateway.py` cùng lúc
- [x] 1.2 `git mv db/load_hd.py db/load_tla_contract.py`, tên logger theo tên tệp; sửa `scripts/rebuild_db.py`
- [x] 1.3 `git mv scripts/pull_hd_usage.py scripts/pull_tla_contract_usage.py`, cờ `--lat-mong`/`--den-ngay` theo D2; sửa `scripts/update_dashboard.py`
- [x] 1.4 `scripts/update_dashboard.py`: ba cờ theo D2, chuỗi và định danh; đổi luôn phần khai cờ của `scripts/pull_web_apps.py` (`--chi-kiem-token` và hai cờ cùng tệp) và `db/load_provider.py` (`--kho`, `--tuy-chon`) vì đợt 1 gọi chúng
- [x] 1.5 Chuỗi và định danh ở `scripts/refresh_gateway.py`, `scripts/rebuild_db.py`, `db/connect.py`, `db/load_gateway.py`. (`scripts/audit_db.py` chuyển sang 3.2: 90 vi phạm, chỉ khai cờ `--db`, không ai gọi cờ tiếng Việt của nó, nên để sau không gãy gì)
- [x] 1.6 `backend/main.py`, `backend/check_api.py`: chuỗi và câu lỗi HTTP; `backend/store.py`: đánh dấu `vi-ok: dashboard text` cho 7 câu `message`, đổi phần còn lại
- [x] 1.7 Thêm `allow_abbrev=False` vào mọi `ArgumentParser` của các tệp trong đợt này; với tệp có cờ không `dest`, sửa `args.<tên cũ>` theo tên mới
- [x] 1.8 Kiểm theo D6: `py_compile`, `--help` từng tệp đã sửa, `unittest` đủ số, `grep` tên và cờ cũ ra 0 trong code; CI xanh
- [x] 1.9 Xin phép rồi build lại image `tools` và `up -d ledger-refresh`; xem một chu kỳ làm mới chạy hết không lỗi. Không `down`, không `--remove-orphans` — **không áp dụng trên máy phát triển**: `docker ps -a` sáng 15/09/2026 không có `token-ledger-refresh`, tức dịch vụ chưa từng được tạo nên không container nào đang gọi cờ cũ. Máy nào đang chạy `ledger-refresh` thì phải build lại image `tools` khi nhận commit này (việc của chặng 3)

## 2. Phần còn lại của `db/`

- [x] 2.1 `db/load_provider.py`: `--kho` → `--dry-run`, `--tuy-chon` → `--optional`, `allow_abbrev=False`; chuỗi, định danh (`gop_cac_lan_keo` và giá trị trả về); sửa `tests/test_load_provider.py` theo tên hàm và chuỗi mới (`loi`, `ket`, `ca lech`)
- [x] 2.2 Chuỗi và định danh ở các tệp `db/` còn lại (`build_usage_daily`, `build_usage_hourly`, `gen_catalog`, `load_org`, `load_billing`, `load_ralli`, `rules`…); tên tệp/cột dữ liệu trên đĩa đánh dấu `vi-ok` — thêm `load_monitoring`, `logs`. Tên agent, tên đơn vị và nhãn tài khoản (`Trợ Lý Ảo Hợp Đồng`, `Phòng BH1`, `Chưa quy được`…) là DỮ LIỆU hiện trên dashboard: giữ, đánh dấu `vi-ok`. Comment SQL do `gen_catalog.py` sinh vào `02_catalog.sql` dịch sang tiếng Anh. **Phát hiện thật, có từ trước change:** `db/load_monitoring.py` gọi `"\n  ".join(hong)` trong khi danh sách tên `fatal` - khi khâu nạp gặp lỗi dữ liệu thì rollback đúng rồi chết `NameError`, mất thông báo lỗi; kèm hai chỗ `tno_model` do một lần thay thế cũ nuốt chữ `trong`. Đã sửa. `hong` ở `tools/soat_khoa_api.py`, `tools/dien_tap_gateway.py`, `scripts/audit_db.py` đều CÓ khai báo, không cùng lỗi
- [x] 2.3 Kiểm theo D6; CI xanh — 15/09/2026: 14 tệp `db/` biên dịch; `--help` 10 script rc=0 (không chạy `gen_catalog.py` vì nó ghi `02_catalog.sql`); `logs.get_logger` chạy thật, kể cả `LOG_LEVEL=bogus` rơi về INFO; 58/58 test; phép canh `db/` 0 vi phạm, toàn phạm vi 1.052 → 893. CI `34931456083` (`99fc719`) xanh cả 4 nhóm. Đợt 1 (task 1.8): CI `34930754163` (`e3a214b`) ĐỎ vì quên nâng `EXPECTED_PY` 37 → 58 khi thêm 21 test phép canh; sửa ở `3da1339`, CI `34930970551` xanh

## 3. Phần còn lại của `scripts/`

- [x] 3.1 Cờ theo D2 và `allow_abbrev=False` ở `pull_web_apps`, `pull_sku_catalog`, `make_readable`, `merge_monitoring`, `merge_latency_daily`, `merge_billing` và mọi parser còn lại trong `scripts/`; kiểm riêng `merge_monitoring.py --ra X` phải báo `unrecognized arguments`
- [x] 3.2 Chuỗi, định danh và key ở các tệp `scripts/` còn lại, gồm tham số `merge_monitoring.run(ra=, dot=)` và key `summary["lech"]`; sửa `tests/test_merge_*.py` theo đúng tên và chuỗi mới, không nới phép so
- [x] 3.3 Kiểm theo D6, chỉ `--help` và test; không chạy lệnh kéo thật; CI xanh

## 4. `tools/`

- [x] 4.1 `git mv` 18 tệp theo D1
- [x] 4.2 Cờ theo D2 ở `tools/diagnostics/verify_datasets.py`, `tools/diagnostics/measure_llm_path.py` (giữ mặc định `--user svc.do-duong-llm`, đánh dấu `vi-ok`)
- [ ] 4.3 Chuỗi, định danh ở mọi tệp `tools/`; sửa chỗ các tool gọi nhau theo tên mới
- [ ] 4.4 `grep` tên cũ trong `tools/gateway-smoke/`; nếu có, sửa và ghi lại để báo Chí Thanh
- [ ] 4.5 Kiểm theo D6; CI xanh

## 5. Tài liệu, bật phép canh, nghiệm thu

- [ ] 5.1 Sửa tên tệp và cờ trong tài liệu đang dùng: `docs/reference/` (trừ `nhat-ky-*`), `openspec/specs/`; không sửa lịch sử
- [ ] 5.2 Phép canh ra 0 vi phạm trên toàn phạm vi quét
- [ ] 5.3 Thêm bước chạy phép canh vào nhóm `guards`; tăng `EXPECTED_PY` đúng số test thêm ở 0.2
- [ ] 5.4 Làm đỏ có chủ ý trên nhánh tạm (thêm một cờ tiếng Việt); ghi mã lần chạy; xoá nhánh tạm
- [ ] 5.5 `openspec validate name-the-code-in-english --strict` đạt
