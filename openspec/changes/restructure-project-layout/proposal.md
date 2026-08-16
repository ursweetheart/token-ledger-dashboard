## Why

Gốc repo đang là document root. `docs/toan-trinh-du-lieu.md` (dòng 51 và 317) hướng dẫn
chạy `python -m http.server 8080` ngay tại gốc để phục vụ `index.html`; mà
`SimpleHTTPRequestHandler` phục vụ toàn bộ cwd, đệ quy, không lọc dotfile, và mặc định
bind `0.0.0.0`. Hệ quả: mỗi lần xem dashboard là `.env`, `db/token_ledger.sqlite`
(937 nhân viên kèm email và phòng ban), toàn bộ `data/` và `.git/` đều tải được từ bất
kỳ máy nào trong mạng LAN. Ràng buộc "database không ra mạng" — vốn đã được giữ đúng ở
uvicorn qua việc bind 127.0.0.1 — bị vòng qua bằng cửa sau này.

Chỉ riêng việc dời frontend xuống một thư mục con đã đóng lỗ đó, vì khi ấy `http.server`
chạy trong `web/` và không đi ngược lên được. Nhân dịp phải dời file, gom luôn những chỗ
xếp sai đang làm việc mới dễ lọt: 6 file frontend nằm lẫn với cấu hình và dữ liệu ở gốc,
dữ liệu chạy nằm trong thư mục mã nguồn, và hai script sản xuất nằm nhầm trong `test/`.

## What Changes

**Dời frontend vào `web/` — đây là phần đóng lỗ bảo mật**

- `index.html` → `web/index.html`
- `app.js`, `api.js` → `web/js/`; `app.js.bak` đi kèm `app.js`
- `ralli-users.js` → `web/js/fallback/` (đã hạ xuống vai trò dự phòng)
- `dashboard.css` → `web/css/`
- `chart.umd.min.js` → `web/vendor/` (tách mã đi mượn khỏi mã tự viết)
- `assets/rang-dong-logo.png` → `web/assets/` — đây là ảnh duy nhất `index.html` dùng

Sau khi dời, `index.html` phải sửa **5** trong 6 tham chiếu. Dòng 251
(`assets/rang-dong-logo.png`) giữ nguyên vì `assets/` đi vào `web/` cùng nó.

**Tách dữ liệu chạy khỏi mã nguồn**

- `db/token_ledger.sqlite` → `var/token_ledger.sqlite`; `db/` chỉ còn `.sql` và `.py`

**Sửa chỗ xếp sai đang gây nhầm lẫn**

- `test/sinh_du_lieu_dashboard.py`, `test/va_app_js.py` → `scripts/`. Đây là **bước 10
  của đường ống sản xuất**, không phải test; nằm trong `test/` khiến người đọc
  `update_dashboard.py` tưởng pipeline đang gọi vào bộ kiểm thử.
- `test/` tách ba: 3 mục sản xuất sang `scripts/`; `tests/` giữ 2 thứ phải luôn xanh
  (`date-range-filter.test.js` và fixture JSON); `tools/` nhận 9 script chẩn đoán một
  lần cùng `ket-qua-kiem-tra.csv`, được phép mục theo thời gian.
- **BREAKING** cho thói quen gõ tay: mọi lệnh `python test/<x>.py` đổi thành
  `python tools/<x>.py`. Không script nào trong đường ống bị ảnh hưởng ngoài hai file
  vừa nêu.

**Dọn gốc repo**

- `docs/` chia ba: `reference/` (tra cứu lâu dài), `decisions/` (quyết định còn hiệu
  lực), `archive/` (nhật ký phiên có ngày tháng)
- `planning/` nhận 4 `.xlsx`, 1 `.docx`, ghi chú họp
- **BREAKING** — Xoá `TLA Ralli.xlsx` **và** `scripts/export_ralli_users.py` (chốt
  16/08). Script này hiện luôn sập vì nguồn của nó không tồn tại; xoá nguồn thì phải xoá
  cả script, không để lại file vĩnh viễn không chạy được. Giữ `ralli-users.js` — nó có
  trong git và vẫn là dữ liệu dự phòng ngoại tuyến dùng được. Cái mất đi là khả năng
  *sinh lại* file đó, chấp nhận được vì danh bạ giờ lấy từ database.
  ⚠️ `TLA Ralli.xlsx` **không nằm trong git**, xoá là mất vĩnh viễn
- `downloaded-logs-20260804-165359.json` → `data/` **kèm `git rm --cached`**. File này
  chứa 43 bản ghi Cloud Audit Log với 3 email người thật và 3 địa chỉ IP, đang được git
  theo dõi và nằm trong tầm phục vụ của máy chủ tĩnh
- `README.txt` → `README.md`
- Gỡ theo dõi 10 file `test/__pycache__/*.pyc` đang nằm trong git index
- Xoá `.agents/` (thư mục rỗng)
- `matrix-drilldown-demo.html` và `header-with-logo.png` → `docs/archive/`. Đã quét
  toàn repo: không file nào gọi tới cả hai. Chúng không thuộc `web/` vì `web/` là thứ
  được phục vụ ra mạng, không phải kho chứa file chết. Lưu ý: bản demo có gọi *đi*
  `ralli-users.js` ở dòng 167 nên sau khi dời sẽ mất liên kết đó.

**Không đụng tới**

- **36 file Python** tính `ROOT = Path(__file__).resolve().parents[1]`. `scripts/`,
  `db/`, `backend/`, `tools/`, `tests/` đều ở đúng một cấp dưới gốc trước và sau, nên
  `parents[1]` giữ nguyên nghĩa. Không file nào phải sửa cách tính ROOT.
- `openspec/`, `.claude/`, `.agent/`, `.codex/` giữ nguyên ở gốc — công cụ tìm chúng
  từ thư mục gốc dự án.
- Nội dung của bất kỳ file nào, ngoài các dòng đường dẫn được liệt kê trong
  `tasks.md`. Đây là refactor thuần vị trí.

## Capabilities

### New Capabilities

- `project-layout`: quy tắc quyết định mỗi loại file thuộc thư mục nào, và tiêu chí
  cho phép/không cho phép một file nằm ở gốc repo — để lần thêm file mới không phải đoán.
- `static-document-root`: ranh giới phục vụ HTTP. Chỉ nội dung `web/` được ra mạng;
  bí mật, database và dữ liệu thô nằm ngoài tầm với của máy chủ tĩnh theo cấu trúc thư
  mục, không phụ thuộc cấu hình.
- `layout-migration-equivalence`: hợp đồng chứng minh hành vi không đổi. Chụp ảnh
  chuẩn trước khi dời, đối chiếu từng byte sau khi dời; lệch ở đâu thì hoàn tác.

### Modified Capabilities

*(Không có — `openspec/specs/` hiện rỗng, chưa năng lực nào được chốt.)*

## Impact

**Mã phải sửa đường dẫn — 9 chỗ, đã định vị chính xác**

| File | Dòng | Đổi thành |
|---|---|---|
| `db/connect.py` | 18 | `DEFAULT_DSN` → `var/token_ledger.sqlite` |
| `scripts/rebuild_db.py` | 99 | mặc định `--db` → `var/` |
| `scripts/merge_billing.py` | 73 | `DB_MAC_DINH` → `var/` |
| `scripts/copy_to_postgres.py` | 41 | `SQLITE_MAC_DINH` → `var/` |
| `scripts/export_ralli_users.py` | — | **xoá cả file** (nguồn của nó bị xoá) |
| `scripts/update_dashboard.py` | 153–154 | hai lệnh bước 10 → `scripts/` |
| `test/va_app_js.py` | 30 | `APP` → `ROOT / "web" / "js" / "app.js"` — sửa ở nhóm 2, khi file vẫn còn trong `test/`; nhóm 4 mới dời nó sang `scripts/` |
| `web/index.html` | 8, 10, 1139, 1142, 1143 | 5 thẻ `href`/`src`; dòng 251 giữ nguyên |
| `docs/reference/toan-trinh-du-lieu.md` | 51, 317 | `cd web && python -m http.server 8080 --bind 127.0.0.1` |

`sinh_du_lieu_dashboard.py` không phải sửa dòng nào: nó ghi `seed-days-that.js` bằng
`Path(__file__).parent`, và `va_app_js.py` đọc lại cũng bằng `__file__.parent` — hai
file đi cùng nhau nên đường dẫn tương đối giữa chúng không đổi.

**Không đổi giao diện, không đổi API, không đổi schema.** 8 endpoint, 18 bảng, 30 phép
kiểm giữ nguyên tên và nguyên kết quả — đó chính là điều kiện nghiệm thu.

**Rủi ro**

- Sót một đường dẫn khiến dashboard trắng hoặc một bước pipeline hỏng. Chống bằng
  `layout-migration-equivalence`: chụp ảnh chuẩn trước, đối chiếu sau.
- Dùng `git mv` chứ không phải xoá-rồi-tạo, để `git log --follow` còn truy được lịch sử.
- `.gitignore` phải được cập nhật **cùng lúc** với việc dời: `var/` là thư mục mới chứa
  database, mà quy tắc hiện tại chặn `*.sqlite` theo đuôi file nên vẫn có tác dụng —
  cần xác nhận lại chứ không giả định.

---

## Đã thực thi ngày 16/08 — những chỗ làm khác kế hoạch

Tám chỗ. Không chỗ nào thu hẹp phạm vi; sáu chỗ là kế hoạch thiếu, hai chỗ là quyết
định của người dùng.

**1. Bung stash sớm, không phải ở cuối.** Người dùng chọn "stash rồi bung sau", nhưng
bung ở cuối sẽ xung đột chắc chắn — nhóm 6 dời chính hai file `docs/` đó và nhóm 4 sửa
chính `update_dashboard.py`. Đã bung ngay sau khi chụp ảnh chuẩn, trước lệnh `git mv`
đầu tiên, rồi commit làm nền. Không xung đột.

**2. Phép quét ở task 2.6 bắt được hai lỗ hổng của chính kế hoạch này.**
`tests/date-range-filter.test.js` dòng 8 và 102 — **bộ test phải luôn xanh** — cùng
`tools/trich_yeu_cau_dashboard.py` dòng 26–27 đều đọc `index.html` ở gốc, mà không nhóm
nào định sửa. Nguyên nhân: mẫu quét đầu viết theo cú pháp Python (`ROOT / "x"`) nên sót
cách viết JavaScript (`path.join(ROOT, "x")`). **Phải quét bằng tên file, không bằng
hình dạng biểu thức.**

**3. Hạng mục E là bản thay thế tự động, không phải chụp Chrome.** Extension không kết
nối. Đã đo: 7/7 tài nguyên HTTP 200, 22 canvas, 22 id giống hệt, `node tests/` 6 đạt.
Còn thiếu: bằng chứng biểu đồ vẽ ra đúng và console không lỗi. Rủi ro thấp vì `app.js`
và `api.js` không đổi một ký tự, nhưng **chưa được chứng minh**.

**4. Chạy thử `va_app_js.py` rồi hoàn tác `app.js`.** Script bump phiên bản STORE
v19→v20 — hành vi bình thường của đường ống, nhưng làm nhiễu bằng chứng tương đương.
Đã `git checkout` về đúng băm cũ. Điều cần chứng minh là *script tìm đúng file*, không
phải *dữ liệu mới*.

**5. Xoá thêm hai thư mục rỗng** không có trong kế hoạch: `assets/` (còn lại sau khi
ảnh logo đi vào `web/assets/`) và `.agents/`.

**6. `tools/pham_vi_moi.py` hỏng — nhưng hỏng sẵn từ trước.** Nó tìm
`data/billing/billing_gop_tru_CTDA.csv`, file không tồn tại. Nằm dưới `data/`, thư mục
change này không đụng tới, và `ROOT/"data"` giải ra y hệt trước lẫn sau.

**7–8. Hai quyết định của người dùng** (16/08): xoá hẳn `matrix-drilldown-demo.html`
thay vì lưu trữ; xoá hẳn `TLA Ralli.xlsx` dù đã được cảnh báo nó không nằm trong git.
`header-with-logo.png` vẫn theo kế hoạch cũ — vào `docs/archive/`.

### Còn nợ

- Hạng mục E chưa có bản chụp Chrome thật (mục 3 ở trên).
- Lịch sử git vẫn chứa `downloaded-logs-*.json` với 3 email người thật. Việc gỡ khỏi
  index chỉ chặn từ nay về sau. Viết lại lịch sử nằm ngoài phạm vi change này.
- Open Question 2 (`data/` có nên vào `var/`) và 4 (`gateway/` ở đâu) chưa trả lời —
  không chặn gì, nhưng câu 4 nên chốt trước khi bắt đầu API Gateway.
