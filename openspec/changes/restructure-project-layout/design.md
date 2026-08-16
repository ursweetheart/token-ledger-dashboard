## Context

Dự án là bốn thứ nằm chung một thư mục: đường ống dữ liệu (15 script `scripts/` +
10 module `db/`), database, backend FastAPI chỉ-đọc, và một dashboard tĩnh. Ba phần đầu
đã có thư mục riêng. Phần thứ tư — 6 file, 948 KB — nằm rải ở gốc repo, biến gốc repo
thành document root và kéo theo lỗ hở mô tả trong `proposal.md`.

Ba ràng buộc định hình toàn bộ thiết kế:

1. **`ROOT = Path(__file__).resolve().parents[1]` xuất hiện ở 36 file Python.** Chừng
   nào mọi thư mục chứa Python còn ở đúng một cấp dưới gốc, không file nào phải sửa
   cách tính ROOT. Đây là lý do thiết kế này *không* gom Python vào `src/token_ledger/`
   ở lần này — làm thế là đụng cả 30 file.
2. **Frontend không có bước build.** `index.html` nạp thẳng 4 thẻ `<script>`, không
   npm, không bundler. Toàn bộ trang chỉ tham chiếu đúng 6 tài nguyên, và **5 trong số
   đó phải sửa đường dẫn** — `assets/rang-dong-logo.png` ở dòng 251 giữ nguyên, vì
   `assets/` đi vào `web/` cùng `index.html` nên đường dẫn tương đối không đổi.
3. **Dashboard phải chạy được cả khi bấm đúp `index.html`** (`api.js` dòng 9). Bản
   offline dùng dữ liệu vá sẵn trong `app.js`. Mọi đường dẫn phải là tương đối, không
   được phụ thuộc máy chủ.

Một chi tiết phát hiện khi soát, không nằm trong phạm vi change này nhưng ảnh hưởng
đến cách viết phép kiểm: `dashboard.css` dòng 3 có
`@import url('https://fonts.googleapis.com/…')`. Mỗi lần mở dashboard là một yêu cầu ra
Internet, và nó **không** phải tài nguyên cùng gốc. Phép kiểm "không yêu cầu nào 404"
vì thế phải giới hạn ở tài nguyên cùng gốc, nếu không nó sẽ đỏ vì máy không có mạng
chứ chẳng liên quan gì tới việc dời thư mục.

Yêu cầu người dùng đặt ra khi giao việc: *"phải đảm bảo mọi thứ hoạt động hoàn hảo như
trước"*. Đó là ràng buộc mạnh hơn "chạy được" — nó đòi **bằng chứng đối chiếu**, không
phải cảm nhận. Phần lớn tài liệu này nói về cách tạo bằng chứng đó.

## Goals / Non-Goals

**Goals:**

- Không nội dung nhạy cảm nào (`.env`, `var/*.sqlite`, `data/`, `.git/`) tiếp cận được
  qua máy chủ tĩnh, và điều đó đúng **theo cấu trúc thư mục** — không phụ thuộc người
  chạy nhớ thêm cờ nào.
- Chứng minh được bằng số rằng hành vi sau khi dời trùng khớp trước khi dời: cùng
  database, cùng JSON của 8 endpoint, cùng 30 phép kiểm, cùng dashboard.
- `git log --follow` còn truy được lịch sử mọi file đã dời.
- Có quy tắc thành văn cho câu hỏi "file mới này để đâu".

**Non-Goals:**

- **Không tách `app.js`.** 488 KB vẫn nguyên 488 KB, chỉ đổi chỗ. Tách file là thay đổi
  hành vi tiềm tàng, phải là một change riêng.
- **Không gom Python vào một gói.** Đó là tầng 2, đụng 30 file, để dành.
- **Không đổi schema, endpoint, giao diện, hay bất kỳ con số nào.**
- **Không quyết chuyện API Gateway cùng repo hay repo riêng.** Cấu trúc này để chỗ
  cho `gateway/` ngang hàng `backend/`, nhưng không giả định gì.
- **Không đụng `.agent/` và `.codex/`** dù chúng trùng lặp với `.claude/`. Ba bản sao
  của cùng 4 skill là vấn đề thật nhưng thuộc phạm vi khác.

## Decisions

### 1. `web/` là document root, và cách chạy đổi theo

Lệnh trong tài liệu đổi từ:

```
python -m http.server 8080                          # tại gốc repo
```

thành:

```
cd web && python -m http.server 8080 --bind 127.0.0.1
```

Hai vế đều cần thiết và giải hai vấn đề khác nhau:

- `cd web` chặn **cái gì** phục vụ được. Đây là rào chắn theo cấu trúc: kể cả quên
  `--bind`, thứ lộ ra cũng chỉ là dashboard — vốn không có gì bí mật.
- `--bind 127.0.0.1` chặn **ai** truy cập được. Mặc định của `http.server` là
  `--bind ADDRESS (default: all interfaces)`, tức cả mạng LAN công ty.

Cả hai vế đã được **đo trong hộp cát**, không phải suy từ tài liệu. Dựng một cây thư
mục giả có `.env` và `db/token_ledger.sqlite`, chạy `http.server` ở hai vị trí:

| Đường dẫn | Chạy tại gốc | Chạy trong `web/` |
|---|---|---|
| `/.env` | **200** — tải về nguyên nội dung | 404 |
| `/db/token_ledger.sqlite` | **200** | 404 |
| `/.git/config` | **200** — đọc được remote | 404 |
| `/.git/` | **200 — bảng liệt kê thư mục** | 404 |
| `/../.env` | — | 404 |
| `/..%2f.env` | — | 404 |
| `/%2e%2e/.env` | — | 404 |
| `/index.html` | 200 | 200 |

Hai điều đáng chú ý trong bảng này. Thứ nhất, `http.server` **không lọc dotfile lẫn
dot-thư mục** — `.env` và `.git/` đều phục vụ như file thường. Thứ hai, nó **bật liệt
kê thư mục mặc định**, nên người truy cập không cần đoán tên file: mở `/.git/` là thấy
cả cây, mở `/data/` là thấy toàn bộ kho dữ liệu thô.

Ba kiểu mã hoá `..` đều bị chặn khi đã ở trong `web/`, nên không cần thêm lớp nào.

*Đã cân nhắc — `python -m http.server 8080 --directory web` từ gốc repo.* Cờ này có
thật và cho kết quả giống hệt. Vẫn chọn `cd web` vì lý do đã nêu ở Goals: ranh giới
phải nằm ở **vị trí thư mục**, không ở tham số dòng lệnh. Người gõ thiếu `--directory`
sẽ phục vụ nguyên gốc repo mà không nhận ra — trang vẫn không mở được nên họ sẽ thử
`/index.html`, thấy 404, rồi bỏ đi, để lại một máy chủ đang mở `.env` cho cả LAN. Còn
người quên `cd` thì `http.server` không tìm thấy `index.html` ngay từ đầu, sai lầm tự
lộ. Ưu tiên cách sai một cách ồn ào.

*Đã cân nhắc:* để uvicorn phục vụ luôn file tĩnh qua `StaticFiles`, bỏ hẳn máy chủ thứ
hai. Gọn hơn thật, nhưng phá mất yêu cầu "bấm đúp `index.html` vẫn xem được" và biến
backend thành phụ thuộc bắt buộc để nhìn thấy giao diện. Không đáng. Có thể thêm sau
như một tuỳ chọn, không phải bây giờ.

### 2. `var/` cho dữ liệu chạy, chứ không phải `db/`

`db/` đang chứa cả mã (`.sql`, `.py`) lẫn dữ liệu (`token_ledger.sqlite`). Tách ra để
"xoá sạch làm lại" là một thao tác an toàn (`rm -rf var/`) thay vì một thao tác đáng sợ.

Tên `var/` mượn quy ước Unix (`/var` = dữ liệu biến thiên khi chạy). `data/` đã mang
nghĩa khác trong dự án này — kho dữ liệu **thô kéo về**, không tái tạo được nếu mất, vì
cửa sổ lưu giữ của Cloud Monitoring trượt nhanh. `var/` thì ngược lại: **tái tạo được
hoàn toàn** bằng `rebuild_db.py`. Phân biệt "mất là xong" với "dựng lại 15 giây" đáng
được thể hiện bằng hai thư mục.

*Đã cân nhắc:* `db/data/token_ledger.sqlite`. Bị loại vì vẫn nằm trong `db/`, nên
`rm -rf db/` vẫn nguy hiểm — không giải quyết được điều muốn giải quyết.

### 3. Hai script sản xuất rời khỏi `test/`

`update_dashboard.py` dòng 153–154 gọi `test/sinh_du_lieu_dashboard.py` và
`test/va_app_js.py`. Đường ống sản xuất đang gọi vào thư mục test. Đây không phải lỗi
thẩm mỹ: nó khiến `test/` trở thành thư mục **không được phép hỏng**, mà tên nó lại nói
điều ngược lại — thư mục test là nơi người ta thoải mái xoá và viết lại.

Chuyển cả hai sang `scripts/`. `sinh_du_lieu_dashboard.py` không cần sửa nội dung: nó
ghi `seed-days-that.js` bằng `Path(__file__).parent`, và `va_app_js.py` đọc lại cũng
bằng `__file__.parent`, nên đường dẫn tương đối giữa hai file không đổi khi chúng đi
cùng nhau. `seed-days-that.js` đi theo sang `scripts/`.

### 4. `test/` tách thành `tests/` và `tools/`

`test/` có 15 mục. Chín trong số đó là script chẩn đoán một lần (`chan_doan_loi.py`,
`doi_chieu_web_vs_file.py`, `kiem_ke_de_len_plan.py`…) — viết cho một cuộc điều tra cụ
thể, hoàn thành xong thì giá trị còn lại là *ghi chép*, không phải *bảo vệ*. Trộn chúng
với test thật làm mất khả năng trả lời câu hỏi "bộ test có xanh không", vì không ai
biết cái nào đáng lẽ phải xanh.

| Đi đâu | Gì | Số lượng |
|---|---|---|
| `scripts/` | `sinh_du_lieu_dashboard.py`, `va_app_js.py`, `seed-days-that.js` | 3 |
| `tests/` | `date-range-filter.test.js`, `fixtures/ui-snapshot-2026-08-07.json` | 2 |
| `tools/` | 9 script chẩn đoán + `ket-qua-kiem-tra.csv` | 10 |

`ket-qua-kiem-tra.csv` là kết quả một lần chạy chẩn đoán, **không được git theo dõi**
(bị `.gitignore` chặn theo đuôi `*.csv`). Vì thế nó phải dời bằng `mv` thường —
`git mv` sẽ từ chối một file không có trong index.

`ROOT = parents[1]` trong 9 script đó vẫn đúng vì `tools/` cũng ở một cấp dưới gốc.

### 5. `app.js.bak` được giữ và dời theo, không xoá

`va_app_js.py:89` chụp `.bak` **một lần duy nhất** (`if not sao_luu.exists()`). Nghĩa là
file hiện tại là ảnh chụp `app.js` *trước lần vá đầu tiên*, đóng băng từ 02/08 — không
phải bản sao lưu tay, cũng không phải thứ được sinh lại mỗi lần chạy.

Xoá nó là hành động **có hại**: lần chạy kế tiếp `va_app_js.py` sẽ thấy `.bak` không tồn
tại và chụp lại — nhưng chụp bản *đã bị vá*, làm mốc gốc biến mất vĩnh viễn. Vì nó nằm
cạnh `app.js` theo `APP.with_suffix(".js.bak")`, dời `app.js` là nó tự đi theo.

### 6. Bằng chứng tương đương: chụp ảnh chuẩn trước, đối chiếu máy sau

Đây là phần trả lời trực tiếp yêu cầu "hoạt động hoàn hảo như trước". Nguyên tắc:
**không mắt người nào được dùng làm căn cứ nghiệm thu.** Mọi phép so là `diff`, và
`diff` khác rỗng nghĩa là hoàn tác.

Trước khi `git mv` bất cứ thứ gì, sinh thư mục `baseline/` (nằm trong scratchpad, không
lên git) gồm năm hạng mục:

| | Ảnh chụp | Cách lấy | Điều nó chứng minh |
|---|---|---|---|
| **A** | SHA-256 của file sqlite | băm file | Dời database không đổi một byte |
| **B** | Kết quả 30 phép kiểm | `scripts/audit_db.py` ra file | Nội dung database không đổi |
| **C** | JSON của 8 endpoint | gọi từng endpoint, ghi từng file | Backend trả về y hệt |
| **D** | Kết quả `check_api.py --compare` | ra file | SQLite và PostgreSQL vẫn khớp nhau |
| **E** | Trạng thái dashboard | Chrome: số canvas vẽ được, log lỗi JS, mã HTTP của mọi asset | Giao diện nạp và vẽ y như cũ |

Sau khi dời xong và sửa hết đường dẫn, chạy lại cả năm và `diff` từng cặp.

**A là hạng mục mạnh nhất và rẻ nhất.** Băm file trước và sau khi `git mv` cho bằng
chứng tuyệt đối rằng database không hề bị đụng vào — mạnh hơn mọi phép kiểm nội dung
cộng lại, và tốn một giây. B tồn tại để bắt trường hợp file đúng nhưng *code đọc nhầm
file khác* (ví dụ sửa `connect.py` sai đường dẫn nên nó lặng lẽ tạo database rỗng mới —
đúng kiểu hỏng âm thầm mà `.sqlite` mới tinh vẫn "chạy được").

**Ba chi tiết quyết định C có dùng được hay không:**

- Gọi endpoint với `start`/`end` **ghi rõ**, không để mặc định. `date_range()` suy ra
  khoảng khi thiếu tham số; nếu baseline chụp hôm nay mà đối chiếu chạy sau nửa đêm thì
  diff sẽ khác rỗng vì lý do không liên quan gì đến việc dời thư mục.
- Cùng một `TOKEN_LEDGER_DSN` cho cả hai lần chụp.
- Ghi từng endpoint ra một file riêng, không gộp. Diff phải chỉ ra được *endpoint nào*
  lệch, chứ không chỉ "có lệch".

**E là hạng mục yếu nhất, và nên thừa nhận thẳng.** Nó chứng minh dashboard *nạp và vẽ*,
không chứng minh mọi con số trên màn hình giống hệt. Bù lại bằng hai điều: (1) `app.js`
và `api.js` không đổi một ký tự nào — chỉ đổi vị trí, nên nguồn duy nhất có thể gây lệch
là asset không nạp được, mà cái đó thì mã HTTP bắt được; (2) thêm một phép kiểm tiêu cực
mà bản chụp cũ không có — xem mục dưới.

### 7. Phép kiểm tiêu cực: lỗ hở phải được chứng minh là đã đóng

Bốn hạng mục trên chứng minh *thứ cần chạy vẫn chạy*. Thiếu vế còn lại: *thứ cần chặn
đã bị chặn*. Đây là mục đích chính của cả change này nên không thể để nó không được đo.

Với máy chủ tĩnh đang chạy trong `web/`, bốn đường dẫn sau phải trả về **404**:

```
/.env
/db/token_ledger.sqlite
/var/token_ledger.sqlite
/.git/config
```

Chạy phép kiểm này **trước** khi dời cũng có giá trị riêng: nó sẽ trả về 200, ghi lại
thành bằng chứng lỗ hở là có thật chứ không phải suy đoán từ việc đọc mã.

## Risks / Trade-offs

**[Sót một đường dẫn → dashboard trắng hoặc pipeline hỏng]** → 9 chỗ đã được định vị
chính xác đến số dòng trong `proposal.md`. Sau khi sửa, quét lại toàn repo tìm chuỗi
đường dẫn cũ còn sót; hạng mục C và E bắt phần còn lại.

**[Sửa `connect.py` sai đường dẫn → SQLite lặng lẽ tạo database rỗng]** → Đây là kiểu
hỏng nguy hiểm nhất trong cả change này, vì mọi lệnh vẫn chạy, chỉ có số là rỗng. Đã đo
thật trong hộp cát:

```
sqlite3.connect(duong_dan_sai)                 -> DA TAO FILE RONG (0 byte), khong bao gi
sqlite3.connect('file:...?mode=ro', uri=True)  -> OperationalError: unable to open
                                                  database file, KHONG tao file
```

Backend miễn nhiễm sẵn nhờ hai lớp: `store.py:47` kiểm `p.exists()` và ném
`FileNotFoundError` kèm câu gợi ý, rồi mới mở `mode=ro` ở dòng 50. Bốn chỗ ghi
(`connect.py`, `rebuild_db.py`, `merge_billing.py`, `copy_to_postgres.py`) không có lớp
nào — chúng đúng là nơi rơi vào nhánh "tạo file rỗng 0 byte" ở trên, và là chỗ hạng mục
A với B phải canh.

**[`git mv` trên Windows và chuyện hoa/thường]** → Không có file nào chỉ khác nhau ở
hoa/thường trong lần dời này, nên không gặp. Nhưng phải dùng `git mv` chứ không phải
Explorer, để git ghi nhận là *đổi tên* — kéo thả trong Explorer thì git thấy thành
"xoá 1 file, thêm 1 file" và `--follow` mất dấu.

**[Đồng nghiệp đang có việc dở dang bị xung đột merge]** → Đây là change dời gần như
mọi file ở gốc, nên nó xung đột với mọi nhánh đang mở. Phải làm khi không ai có việc
dở, hoặc báo trước. Đổi lại, chi phí này chỉ tăng theo thời gian nếu trì hoãn.

**[Tài liệu nói đường dẫn cũ]** → 16 file `.md` trong `docs/` nhắc `app.js`,
`db/…sqlite`, `test/…`. Không sửa hết được, và **không nên sửa hết**: `docs/archive/` là nhật ký
phiên có ngày tháng, viết lại chúng là làm sai lịch sử. Chỉ sửa `docs/reference/` —
những file mô tả hệ thống *đang* là gì. `archive/` giữ nguyên, và chính việc nó nằm
trong thư mục tên `archive` đã nói cho người đọc biết nội dung có thể đã cũ.

**[Đánh đổi: không tách `app.js` lần này]** → Sau change này `web/js/app.js` vẫn là một
file 488 KB, tức vấn đề lớn nhất về mã nguồn chưa được giải. Chấp nhận có chủ đích: gộp
việc dời file với việc tách file làm mất khả năng chứng minh tương đương, vì lúc đó
diff khác rỗng sẽ không phân biệt được do dời hay do tách.

## Migration Plan

Làm trên nhánh `restructure-layout`, chia sáu nhóm. **Mỗi nhóm là một commit dời file
cùng với các sửa đường dẫn của chính nó** — không tách "dời" và "sửa đường dẫn" thành
hai commit, vì như thế repo sẽ hỏng ở commit giữa.

Số nhóm dưới đây khớp đúng số nhóm trong `tasks.md`.

```
1. Ảnh chuẩn A–E + phép kiểm tiêu cực (kỳ vọng 200 — ghi lại lỗ hở)   [không commit]
   │
2. web/           8 mục + 5 dòng index.html + va_app_js.py
   │              └─ kiểm E + phép kiểm tiêu cực (kỳ vọng 404)
3. var/           sqlite + 4 chỗ đường dẫn
   │              └─ kiểm A, B, C, D
4. scripts/       3 mục sản xuất rời test/ + update_dashboard.py
   │              └─ update_dashboard.py --help; chạy thử bước 10
5. tests/ tools/  2 + 10 mục; gỡ __pycache__ khỏi git index
   │              └─ chạy tests/
6. docs/ planning/  16 md chia ba + gom 5 xlsx, 1 docx
   │              └─ sửa 2 dòng lệnh + 1 dòng đường dẫn sqlite
7. Nghiệm thu toàn phần: chạy lại A–E, diff tất cả
   │
8. Đóng change
```

Nhóm 2 và 3 độc lập nhau — nhóm 2 không đụng gì tới database, nhóm 3 không đụng gì tới
frontend. Nếu phải dừng giữa chừng, dừng sau bất kỳ nhóm nào cũng để lại repo chạy được.

Một ngoại lệ có chủ ý: nhóm 2 sửa `test/va_app_js.py:30` dù file đó mãi nhóm 4 mới dời.
Nếu để dành, repo sẽ hỏng ở khoảng giữa hai commit — `va_app_js.py` trỏ vào `app.js` đã
không còn ở gốc nữa.

**Hoàn tác:** `git reset --hard` về commit trước nhóm đang làm. Vì database chỉ *dời*
chứ không *biến đổi*, hoàn tác không mất dữ liệu. Nếu đã lỡ chạy `rebuild_db.py` với
đường dẫn sai và sinh ra file rỗng ở chỗ lạ, xoá file đó rồi chạy lại từ `data/` —
`data/` không bị change này đụng tới ở bất kỳ nhóm nào.

## Open Questions

1. **Hai file không ai gọi tới — nhưng một trong hai lại gọi đi.** Đo được:

   - `header-with-logo.png` (122 KB, 23/07) — không tham chiếu vào, không tham chiếu
     ra. `index.html` chỉ dùng `assets/rang-dong-logo.png`. File chết hoàn toàn.
   - `matrix-drilldown-demo.html` (32 KB) — không ai gọi nó, **nhưng dòng 167 của nó
     gọi `<script src="ralli-users.js">`**. Lần soát trước tôi chỉ quét chiều vào và
     bỏ sót chiều ra.

   Lịch sử git cho câu trả lời rõ hơn mọi suy đoán: commit cuối chạm vào file này là
   `28/07 — "Replace agent matrix with department-project accordion tree"`, tức chính
   thay đổi đã **thay thế** thứ mà bản demo trình bày. Nó cũng được nhắc trong change
   `unify-dept-user-workspace-and-agent-matrix`. Đây là bản mẫu thiết kế đã hoàn thành
   nhiệm vụ.

   Cả hai **không thuộc `web/`** — `web/` là thứ được phục vụ ra mạng, chứa file chết
   ở đó chỉ làm tăng bề mặt lộ. Mặc định của kế hoạch: chuyển cả hai vào `docs/archive/`.
   Hệ quả phải chấp nhận: bản demo sẽ mất liên kết tới `ralli-users.js` (file này đi
   `web/js/fallback/`) nên mở ra sẽ hiển thị không có dữ liệu người dùng. Với một bản
   mẫu đã lưu trữ thì chấp nhận được, và git vẫn giữ bản chạy được. **Cần bạn chốt:**
   lưu trữ dạng hỏng liên kết, hay xoá hẳn?
2. **`data/` có nên vào `var/` không?** Lập luận ở Quyết định 2 nói không — `data/` mất
   là mất vĩnh viễn, `var/` dựng lại được. Nhưng cả hai đều là "không phải mã nguồn", và
   có người sẽ thấy hai thư mục là thừa.
3. **`downloaded-logs-20260804-165359.json` — đã mở ra xem, và nó không phải câu hỏi
   xếp thư mục nữa.** Đo được:

   - 43 bản ghi **Cloud Audit Log** của dự án `ai-chatbot-contract`, tháng 6/2026
   - chứa **3 địa chỉ email người thật** (2 Gmail cá nhân, 1 tên miền nhà cung cấp
     ngoài) + 1 tài khoản dịch vụ + 3 địa chỉ IP người gọi
   - **đang được git theo dõi** — `.gitignore` không chặn `.json` ở gốc
   - nằm ở gốc repo, tức nằm trong tầm phục vụ của máy chủ tĩnh hiện tại

   Nó là ví dụ thứ hai của đúng lỗ hở mà change này sinh ra để đóng, và là ví dụ nặng
   hơn `.env`: `.env` chứa mật khẩu có thể đổi, còn đây là dữ liệu cá nhân của người
   thật, không đổi được.

   Xếp vào `data/` là đúng — nhưng phải kèm `git rm --cached`, vì `data/` bị gitignore
   nên nếu không gỡ khỏi index thì git vẫn theo dõi nó ở vị trí mới. **Phải nói thẳng
   giới hạn:** việc này chỉ chặn từ nay về sau. Lịch sử git đã có nó và sẽ vẫn có, trừ
   khi viết lại lịch sử — nằm ngoài phạm vi change này, và là quyết định của bạn.
4. **`gateway/` sẽ ở đâu?** Không chặn change này, nhưng trả lời sớm thì đỡ phải dời
   lần nữa.
5. **`scripts/export_ralli_users.py` đang HỎNG, và việc xếp thư mục chạm thẳng vào nó.**

   Lượt soát trước tôi ghi "`TLA Ralli.xlsx` có hai bản" — **sai**. Chạy `find` toàn
   repo: chỉ có **một** bản, ở gốc. `data/TLA Ralli.xlsx` không tồn tại. Mà
   `export_ralli_users.py:16` lại đọc đúng đường dẫn đó:

   ```
   $ python scripts/export_ralli_users.py
   FileNotFoundError: [Errno 2] No such file or directory:
     'D:\RangDonk\token-ledger-dashboard\data\TLA Ralli.xlsx'
   ```

   Đây là hỏng **có sẵn từ trước**, không do change này gây ra. Nhưng không thể lờ đi,
   vì kế hoạch cũ của tôi chuyển file ấy vào `planning/` — làm thế là khoá chặt cái
   hỏng lại.

   Theo đúng quy tắc bố trí thì `planning/` sai ngay từ đầu: đây không phải bảng kế
   hoạch như mấy file Master Plan, mà là **đầu vào của đường ống**. Chỗ của nó là
   `data/` — cũng đúng chỗ mã nguồn đang tìm.

   **ĐÃ CHỐT (16/08): xoá cả chuỗi.** Người dùng quyết bỏ hẳn `TLA Ralli.xlsx`. Kèm
   theo phải bỏ `scripts/export_ralli_users.py` — giữ script mà xoá nguồn của nó thì để
   lại một file vĩnh viễn không chạy được, đúng thứ change này đang dọn.

   Ba điều đã đo, quyết định dựa trên chúng:

   - `TLA Ralli.xlsx` **không nằm trong git** (`.gitignore:18 *.xlsx`) → xoá là mất
     vĩnh viễn, không khôi phục được
   - `ralli-users.js` — bản sinh ra từ nó, 121 KB — **có trong git** → dữ liệu vẫn còn
   - `RALLI_USERS` chỉ dùng ở nhánh dự phòng: `app.js:297` là
     `if(REAL_ACCOUNTS.length) return buildAccountCatalogueFromDb();`, và `app.js:2555`
     là nhánh sai của một toán tử ba ngôi cùng điều kiện. Backend chạy thì không chạm tới

   Cái mất đi: khả năng **sinh lại** `ralli-users.js` nếu danh bạ Ralli thay đổi. Chấp
   nhận được vì danh bạ giờ lấy từ database (937 tài khoản qua `/api/accounts`);
   `ralli-users.js` chỉ còn là ảnh chụp đông cứng cho chế độ ngoại tuyến.

   **Trước khi xoá phải hỏi lại một lần nữa** — file không có trong git, và người quyết
   xoá đã nói nó "không liên quan đến code", trong khi thực tế nó là đầu vào của một
   script và một file JS đang được `index.html` nạp. Quyết định vẫn hợp lý, nhưng nó
   hợp lý vì *chuỗi này đã bị database thay thế*, không phải vì *không liên quan*.
