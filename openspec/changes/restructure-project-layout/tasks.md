> Chạy trên nhánh riêng. Mỗi nhóm từ 2 đến 6 là **một commit** gồm cả việc dời file
> lẫn việc sửa đường dẫn của chính nó — không tách đôi, vì tách đôi sẽ để lại một commit
> giữa chừng mà repo hỏng.
>
> Đặt thư mục ảnh chụp chuẩn **ngoài repo**:
> `BASE="$TEMP/claude/D--RangDonk-token-ledger-dashboard/784b74bd-af40-4bf9-abba-8e8098876344/scratchpad/baseline"`

## 1. Ảnh chụp chuẩn — làm xong hết trước khi dời bất cứ thứ gì

- [x] 1.1 Tạo nhánh `restructure-layout`; xác nhận `git status` sạch, không còn thay đổi
      dở dang từ phiên trước (hiện đang có 3 file sửa chưa commit — commit hoặc stash trước)
- [x] 1.2 Tạo `$BASE/truoc/` và `$BASE/sau/`
- [x] 1.3 **Hạng mục A** — băm database:
      `sha256sum db/token_ledger.sqlite > $BASE/truoc/db.sha256`
- [x] 1.4 **Hạng mục B** — 30 phép kiểm:
      `python scripts/audit_db.py > $BASE/truoc/audit.txt 2>&1`
- [x] 1.5 Bật backend: `python -m uvicorn backend.main:app --port 8000`
- [x] 1.6 **Hạng mục C** — chụp 8 endpoint ra 8 file riêng trong `$BASE/truoc/api/`.
      Bốn endpoint không nhận tham số (`health`, `catalog`, `accounts`, `adoption`);
      bốn endpoint còn lại (`usage`, `usage-by-account`, `performance`, `thinking`)
      phải **ghi rõ** `?start=2026-05-01&end=2026-08-08` — để mặc định thì
      `date_range()` suy ra theo đồng hồ và diff sẽ lệch vì lý do không liên quan
- [x] 1.7 **Hạng mục D** — hai hệ quản trị: `docker compose up -d`, chạy backend thứ hai
      trỏ PostgreSQL trên cổng 8001, rồi
      `python backend/check_api.py --compare http://127.0.0.1:8001 > $BASE/truoc/check_api.txt 2>&1`
- [x] 1.8 **Hạng mục E** — dashboard: mở qua máy chủ tĩnh, duyệt hết các tab, ghi lại số
      canvas vẽ được, toàn bộ console, và mã HTTP của mọi yêu cầu **cùng gốc** vào
      `$BASE/truoc/ui.txt`. Loại yêu cầu tới `fonts.googleapis.com` — `dashboard.css`
      dòng 3 có `@import` ra Internet, nó đỏ hay xanh tuỳ máy có mạng, không liên quan
      tới việc dời thư mục. Trước khi đọc phải ép trình duyệt lấy bản mới, không đọc bản đệm
- [x] 1.9 **Phép kiểm tiêu cực, lần "trước"** — máy chủ tĩnh chạy **tại gốc repo**, ghi
      mã HTTP của `/.env`, `/db/token_ledger.sqlite`, `/.git/config` vào
      `$BASE/truoc/lo-ho.txt`. **Kỳ vọng 200.** Cơ chế đã được đo trong hộp cát rồi
      (`.env` tải về nguyên nội dung), bước này chỉ để xác nhận trên repo thật.
      **Thêm `--bind 127.0.0.1` dù tài liệu cũ không có** — đo lỗ hở thì không cần thực
      sự mở nó ra cho cả mạng LAN. Tắt máy chủ ngay sau khi đo
- [x] 1.10 Xác nhận `$BASE/truoc/` có đủ 5 hạng mục + file lỗ hở trước khi sang nhóm 2

## 2. Dời frontend vào `web/`

- [x] 2.1 `git mv` vào `web/`: `index.html`; `app.js`, `app.js.bak`, `api.js` →
      `web/js/`; `ralli-users.js` → `web/js/fallback/`; `dashboard.css` → `web/css/`;
      `chart.umd.min.js` → `web/vendor/`; `assets/rang-dong-logo.png` → `web/assets/`
- [x] 2.2 `web/index.html` — sửa **5** tham chiếu: dòng 8 (`dashboard.css` →
      `css/dashboard.css`), dòng 10 (`chart.umd.min.js` → `vendor/chart.umd.min.js`),
      dòng 1139 (`ralli-users.js` → `js/fallback/ralli-users.js`), dòng 1142
      (`api.js` → `js/api.js`), dòng 1143 (`app.js` → `js/app.js`).
      **Dòng 251 KHÔNG sửa** — `assets/rang-dong-logo.png` vẫn đúng vì `assets/` đi vào
      `web/` cùng `index.html`. Sửa dòng này là làm hỏng ảnh logo
- [x] 2.3 **Không sửa `scripts/export_ralli_users.py`** — nhóm 6 xoá hẳn file này (đã
      chốt 16/08). Sửa đường dẫn `OUTPUT` rồi xoá là công cốc
- [x] 2.4 `test/va_app_js.py:30` — `APP` → `ROOT / "web" / "js" / "app.js"`.
      (File sẽ chuyển sang `scripts/` ở nhóm 4; sửa ở đây để repo không hỏng giữa chừng)
- [x] 2.5 `matrix-drilldown-demo.html` và `header-with-logo.png` → `docs/archive/`,
      **không** vào `web/`. Không file nào gọi tới chúng; nhưng `matrix-drilldown-demo`
      dòng 167 **gọi đi** `<script src="ralli-users.js">`, nên sau khi dời nó sẽ mất
      liên kết đó. Chấp nhận được với một bản mẫu đã lưu trữ *(xem Open Question 1 —
      cần bạn chốt lưu trữ hay xoá hẳn)*
- [x] 2.6 Quét cả repo tìm chuỗi đường dẫn cũ còn sót ngoài `docs/archive/`.
      **Bắt được 2 lỗ hổng của chính kế hoạch này**, cả hai đọc `index.html` ở gốc mà
      không nhóm nào định sửa: `test/date-range-filter.test.js` dòng 8 và 102 (bộ test
      PHẢI luôn xanh) và `test/trich_yeu_cau_dashboard.py` dòng 26–27. Đã sửa cả 4.
      Bài học: mẫu quét đầu tiên viết theo cú pháp Python (`ROOT / "x"`) nên sót cách
      viết JavaScript (`path.join(ROOT, "x")`) — phải quét bằng tên file, không bằng
      hình dạng biểu thức
- [x] 2.7 Kiểm: `cd web && python -m http.server 8080 --bind 127.0.0.1`, mở trang, xác
      nhận 6 tài nguyên cùng gốc đều 200 và không có lỗi JS
- [x] 2.8 Kiểm bản offline: mở `web/index.html` bằng `file://`, xác nhận vẫn vẽ được
- [x] 2.9 **Phép kiểm tiêu cực, lần "sau"** — cùng 3 đường dẫn ở 1.9 phải trả **404**
- [x] 2.10 Commit

## 3. Dời database sang `var/`

- [x] 3.1 `mkdir var && mv db/token_ledger.sqlite var/` — dùng **`mv` thường**, không
      `git mv`. Đã chạy khô: `git mv` trả `fatal: not under version control` với mọi
      file bị ignore, và `.gitignore:44 *.sqlite` chặn file này
- [x] 3.2 **Băm ngay sau khi dời** và so với `$BASE/truoc/db.sha256`. Phải trùng. Không
      trùng thì dừng lại tại đây
- [x] 3.3 `db/connect.py:18` — `DEFAULT_DSN = str(ROOT / "var" / "token_ledger.sqlite")`
      (chú ý: hiện dùng `DB_DIR`, phải đổi cả cách tính, không chỉ tên file)
- [x] 3.4 `scripts/rebuild_db.py:99` — mặc định `--db` → `ROOT / "var" / …`
- [x] 3.5 `scripts/merge_billing.py:73` — `DB_MAC_DINH` → `ROOT / "var" / …`
- [x] 3.6 `scripts/copy_to_postgres.py:41` — `SQLITE_MAC_DINH` → `ROOT / "var" / …`
- [x] 3.7 Xác nhận lại bằng `git check-ignore -v var/token_ledger.sqlite` — đã đo trước
      và ra `.gitignore:44 *.sqlite`, tức quy tắc theo đuôi đã phủ. Kiểm lại sau khi dời
      để chắc, **bằng lệnh chứ không bằng suy đoán**
- [x] 3.8 Kiểm A: băm lại, so với ảnh chụp chuẩn
- [x] 3.9 Kiểm B: chạy lại `audit_db.py`, diff với `$BASE/truoc/audit.txt` — phải rỗng
- [x] 3.10 Kiểm C: bật lại backend, chụp lại 8 endpoint vào `$BASE/sau/api/`, diff từng
      cặp một — cả 8 phải rỗng
- [x] 3.11 Kiểm D: chạy lại `check_api.py --compare`, so số phép kiểm đạt
- [x] 3.12 Kiểm chống hỏng-âm-thầm: xác nhận **không có** file `.sqlite` nào mới xuất
      hiện ở `db/` hay gốc repo. Có nghĩa là còn chỗ nào đó trỏ sai và vừa tạo database rỗng
- [x] 3.13 Commit

## 4. Hai script sản xuất rời `test/`

- [x] 4.1 `git mv test/sinh_du_lieu_dashboard.py test/va_app_js.py
      test/seed-days-that.js scripts/` — cả ba đi cùng nhau vì hai script đầu trỏ tới
      file thứ ba bằng `Path(__file__).parent`
- [x] 4.2 `scripts/update_dashboard.py:153-154` — hai lệnh bước 10 đổi từ `test/…` sang
      `scripts/…`
- [x] 4.3 Kiểm: `python scripts/update_dashboard.py --help` hiện đủ 10 bước
- [x] 4.4 Chạy riêng bước 10 (`sinh_du_lieu_dashboard.py` rồi `va_app_js.py`), xác nhận
      nó vá được vào `web/js/app.js`
- [x] 4.5 Xác nhận `web/js/app.js.bak` **vẫn mang dấu thời gian 02/08**, không bị ghi đè
      — nếu nó thành hôm nay thì mốc gốc đã mất, phải khôi phục từ git
- [x] 4.6 Mở lại dashboard, xác nhận vẫn vẽ được sau khi vá
- [x] 4.7 Commit

## 5. Tách `test/` thành `tests/` và `tools/`

- [x] 5.1 `git rm -r --cached test/__pycache__` — gỡ 10 file `.pyc` khỏi git index
      (`.gitignore` không có tác dụng với file đã được add)
- [x] 5.2 `git mv` phần test thật sang `tests/`: `date-range-filter.test.js`, và
      `ui-snapshot-2026-08-07.json` → `tests/fixtures/`
- [x] 5.3 `git mv` 9 script chẩn đoán còn lại sang `tools/`: `chan_doan_loi.py`,
      `doi_chieu_tla_hd.py`, `doi_chieu_web_vs_file.py`, `kiem_ke_de_len_plan.py`,
      `kiem_tra_du_lieu.py`, `kiem_tu_raw.py`, `pham_vi_moi.py`, `soat_ctda.py`,
      `trich_yeu_cau_dashboard.py`
- [x] 5.4 `mv test/ket-qua-kiem-tra.csv tools/` — dùng `mv` **thường**, không `git mv`:
      file này bị `.gitignore` chặn theo đuôi `*.csv` nên không có trong git index
- [x] 5.5 Xoá thư mục `test/` rỗng
- [x] 5.6 Xác nhận `ROOT = parents[1]` trong 9 script vẫn đúng — `tools/` cũng ở một
      cấp dưới gốc, nên không file nào phải sửa
- [x] 5.7 Chạy `tests/date-range-filter.test.js`, xác nhận vẫn đạt
- [x] 5.8 Chạy thử 3 script trong `tools/` để xác nhận đường dẫn `ROOT` còn đúng.
      `soat_ctda.py` và `trich_yeu_cau_dashboard.py` chạy bình thường.
      `pham_vi_moi.py` báo `FileNotFoundError` cho
      `data/billing/billing_gop_tru_CTDA.csv` — **hỏng sẵn từ trước, không do dời**:
      file nằm dưới `data/`, thư mục change này không đụng tới, và `ROOT/"data"` giải
      ra y hệt trước lẫn sau. Đúng minh hoạ cho lý do tách `tools/`: script chẩn đoán
      được phép mục, `tests/` thì không
- [x] 5.9 `git ls-files | grep __pycache__` phải không ra dòng nào
- [x] 5.10 Commit

## 6. Dọn gốc repo

- [ ] 6.1 `docs/` chia ba — **16 file `.md`, phải xếp hết, không sót cái nào**:
      `reference/` nhận 4 (`toan-trinh-du-lieu.md`, `mo-ta-database.md`,
      `api-map-tla-hd.md`, `huong-dan-cap-nhat-dashboard.md`);
      `decisions/` nhận 2 (`mui-gio-2026-08-08.md`, `quyet-dinh-ngay-2-2026-08-09.md`);
      `archive/` nhận 10 — 9 nhật ký phiên có ngày tháng **cộng
      `dashboard-metrics-and-backend-plan.md`**, tài liệu mô tả kiến trúc từ trước khi
      có backend nên phần lớn nội dung đã lỗi thời — cùng thư mục `superpowers/`.
      Kiểm bằng phép cộng: 4 + 2 + 10 = 16
- [ ] 6.2 Tạo `planning/`, chuyển vào đó **4** file `.xlsx` (`2026.T4.09 DS Đội`,
      `Master Plan AI Radar`, `Master Plan - API Gateway`,
      `Master Plan - Token Ledger Dashboard`), `Tài_liệu_triển_khai_API_Gateway.docx`,
      `nội_dung_cuộc_họp_25_7.txt`, `token-ledger-billing-export-test-log.md`.
      Dùng **`mv` thường** cho các `.xlsx`: đã chạy khô và `git mv` trả về
      `fatal: not under version control` vì `.gitignore:18 *.xlsx` chặn chúng
- [ ] 6.3 **Xoá `TLA Ralli.xlsx`** — đã chốt 16/08. ⚠️ File **không nằm trong git**
      (`.gitignore:18 *.xlsx`), xoá là mất vĩnh viễn. Hỏi lại người quyết một lần nữa
      ngay trước khi xoá; nếu còn phân vân thì chuyển ra ngoài repo thay vì xoá
- [ ] 6.4 **Xoá `scripts/export_ralli_users.py`** cùng lúc — nguồn của nó vừa mất nên
      nó không bao giờ chạy được nữa. Xoá một mà giữ một là để lại rác
- [ ] 6.5 **Giữ `ralli-users.js`** — nó có trong git và vẫn là dữ liệu dự phòng ngoại
      tuyến thật sự dùng được. Nó chỉ mất khả năng *sinh lại*, không mất tác dụng
- [ ] 6.6 Sau khi xoá, xác nhận không còn tham chiếu treo: grep `export_ralli_users`
      và `TLA Ralli` trên toàn repo (trừ `docs/archive/`) phải sạch
- [ ] 6.7 `downloaded-logs-20260804-165359.json` → `data/` **kèm `git rm --cached`**.
      File chứa 43 bản ghi Cloud Audit Log với **3 email người thật** và 3 địa chỉ IP,
      hiện đang được git theo dõi và nằm trong tầm phục vụ của máy chủ tĩnh. Không gỡ
      khỏi index thì git vẫn theo dõi ở vị trí mới, vì `data/` chỉ bị `.gitignore` chặn
      với file chưa được add
- [ ] 6.8 Xác nhận `git status` không còn thấy file đó, và `git ls-files | grep
      downloaded-logs` không ra dòng nào
- [ ] 6.9 `git mv README.txt README.md`
- [ ] 6.10 Xoá `.agents/` (rỗng)
- [ ] 6.11 `docs/reference/toan-trinh-du-lieu.md` dòng 51 và 317 — đổi lệnh máy chủ tĩnh
      thành `cd web && python -m http.server 8080 --bind 127.0.0.1`, và giải thích ngắn
      **vì sao** hai vế đều cần: `cd web` chặn *cái gì* lộ, `--bind` chặn *ai* vào được
- [ ] 6.12 `docs/reference/toan-trinh-du-lieu.md` dòng 38 và mọi chỗ trong
      `docs/reference/` nhắc `db/token_ledger.sqlite` → `var/token_ledger.sqlite`
- [ ] 6.13 **Không sửa `docs/archive/`** — nội dung phải y nguyên, chỉ đổi vị trí
- [ ] 6.14 Thêm vào `docs/reference/` phần mô tả cây thư mục mới kèm quy tắc "gốc repo
      chỉ nhận ba loại mục"
- [ ] 6.15 Commit

## 7. Nghiệm thu toàn phần

- [ ] 7.1 Chạy lại cả 5 hạng mục vào `$BASE/sau/`
- [ ] 7.2 Diff A — mã băm database phải trùng
- [ ] 7.3 Diff B — 30 phép kiểm, diff rỗng, vẫn đúng số đạt và số cảnh báo
- [ ] 7.4 Diff C — cả 8 endpoint, từng file một, tất cả rỗng
- [ ] 7.5 Diff D — số phép kiểm đạt của `check_api --compare` không đổi
- [ ] 7.6 So E — số canvas bằng nhau, không lỗi JS mới, không yêu cầu nào 404
- [ ] 7.7 Phép kiểm tiêu cực lần cuối — 4 đường dẫn nhạy cảm đều 404, đối chiếu với
      `$BASE/truoc/lo-ho.txt` để thấy rõ 200 → 404
- [ ] 7.8 `git log --follow web/js/app.js` — lịch sử phải xuyên qua chỗ dời
- [ ] 7.9 `git status` sạch; `git ls-files` không còn `.pyc`, không còn file frontend ở gốc
- [ ] 7.10 **Nếu bất kỳ diff nào khác rỗng**: ghi lại nguyên nhân. Chỉ bỏ qua khi giải
      thích được là vô hại; không giải thích được thì hoàn tác về commit trước

## 8. Đóng change

- [ ] 8.1 Rà lại `proposal.md` — có mục nào làm khác kế hoạch thì ghi rõ
- [ ] 8.2 Trả lời 4 Open Question trong `design.md`, hoặc chuyển sang change khác
- [ ] 8.3 Merge vào `main`
- [ ] 8.4 Báo đồng nghiệp: mọi nhánh đang mở sẽ xung đột, và lệnh chạy dashboard đã đổi
- [ ] 8.5 `openspec archive restructure-project-layout`
