# Cây thư mục

Tài liệu này trả lời một câu hỏi: **file mới này để đâu?**

## Quy tắc gốc repo

Thư mục gốc chỉ nhận **ba loại**:

1. Thư mục do công cụ bên ngoài bắt buộc đặt ở gốc
2. Đúng một thư mục cho mỗi thành phần của hệ thống
3. File cấu hình cấp dự án

Không thuộc ba loại nào thì không được ở gốc. Trước khi có quy tắc này, gốc repo là
nơi mọi thứ không biết để đâu thì rơi vào — 6 file frontend, 5 bảng tính, một file
nhật ký kiểm toán chứa email người thật, và một bản demo đã bị thay thế từ tháng 7.

## Cây hiện tại

```
token-ledger-dashboard/
│
├── web/                    ④ FRONTEND — DOCUMENT ROOT
│   │                          Máy chủ tĩnh chạy TRONG đây. Không gì bên ngoài
│   │                          ra được mạng. Xem "Ranh giới phục vụ" bên dưới.
│   ├── index.html
│   ├── js/       app.js · api.js          KHÔNG chứa dữ liệu số liệu
│   ├── css/      dashboard.css
│   ├── vendor/   chart.umd.min.js        ← mã đi mượn, tách khỏi mã tự viết
│   └── assets/   rang-dong-logo.png
│
├── backend/                ③ API chỉ-đọc (FastAPI) — 8 endpoint
│   main.py · store.py (mọi câu SQL) · check_api.py
│
├── scripts/                ① KÉO + ② GỘP + điều phối
│   pull_*.py (6) · merge_*.py (3) · update_dashboard.py (9 bước)
│   rebuild_db.py · audit_db.py (30 phép kiểm)
│
├── db/                     ③ SCHEMA + NẠP — chỉ chứa MÃ
│   ├── migrations/         Chuỗi schema Alembic — nguồn schema đang sống duy nhất
│   │   ├── README.md
│   │   ├── sql/            001_baseline.sql
│   │   └── versions/       001_baseline_baseline.py
│   └── 02_catalog.sql · load_*.py · build_*.py · connect.py · rules.py
│
├── data/                   Kho dữ liệu THÔ — mất là mất vĩnh viễn
├── var/                    Artifact cục bộ dựng lại được
│   ├── baselines/          Mốc đối chiếu dữ liệu/database
│   └── snapshots/          Dấu vết chẩn đoán không phải baseline JSON
│
├── tests/                  Phải LUÔN xanh
├── tools/
│   ├── diagnostics/        Chẩn đoán một lần — ĐƯỢC PHÉP mục
│   ├── bench/              Load/routing probes có chủ đích
│   ├── probes/             Môi trường đo cô lập + kết quả gốc
│   └── gateway-smoke/      runtime · harnesses · reports · artifacts
├── docs/
│   ├── reference/          Hệ thống ĐANG là gì  ← file này
│   ├── decisions/          Quyết định còn hiệu lực
│   └── archive/            Nhật ký/diễn tập/bản lưu — KHÔNG sửa nội dung lịch sử
├── planning/               .xlsx · .docx · ghi chú họp · sketches/
│
├── openspec/  .claude/  .agent/  .codex/       ← công cụ bắt buộc ở gốc
└── alembic.ini  docker-compose.yml  .env.example  .gitignore  README.md
```

## Hai ranh giới quan trọng

### `data/` với `var/` — vì sao là hai thư mục

| | `data/` | `var/` |
|---|---|---|
| Mất thì sao | **Vĩnh viễn** — cửa sổ lưu giữ Cloud Monitoring trượt nhanh | Dựng lại 15 giây bằng `rebuild_db.py` |
| Sinh ra từ | Kéo về từ nguồn ngoài | Từ `data/` |
| Xoá được không | Tuyệt đối không | `rm -rf var/` là thao tác an toàn |

Chính vì thế `db/` không được chứa database: để `rm -rf db/` không bao giờ là thứ đáng
sợ, còn `rm -rf var/` thì luôn an toàn.

### Ranh giới phục vụ — chỉ `web/` ra được mạng

```bash
cd web && python -m http.server 8080 --bind 127.0.0.1
```

Hai vế, hai vấn đề khác nhau:

- **`cd web`** chặn *cái gì* lộ ra. `http.server` không phục vụ được gì ngoài thư mục
  nó đang đứng, và từ chối cả `..`, `..%2f`, `%2e%2e/`.
- **`--bind 127.0.0.1`** chặn *ai* vào được. Mặc định là *all interfaces* — cả LAN.

Có `python -m http.server --directory web` cho kết quả giống hệt. **Vẫn nên dùng
`cd web`**: quên `--directory` thì máy chủ lặng lẽ phơi cả repo trong khi trang vẫn có
vẻ "chỉ bị 404"; quên `cd` thì `http.server` không tìm thấy `index.html` ngay lập tức.
Ưu tiên cách sai một cách ồn ào.

Đo trước và sau khi dời frontend vào `web/`:

| | Chạy tại gốc repo | Chạy trong `web/` |
|---|---|---|
| `/.env` | **200 — tải về nguyên nội dung** | 404 |
| `/db/token_ledger.sqlite` | **200** | 404 |
| `/.git/config` · `/.git/` | **200 — kèm liệt kê thư mục** | 404 |
| `/data/` | **200** | 404 |
| 7 tài nguyên của dashboard | 200 | 200 |

## Quy ước đặt tên: định danh tiếng Anh, ghi chú tiếng Việt

**Định danh viết tiếng Anh. Ghi chú và mọi chữ người dùng đọc viết tiếng Việt.**

Trước 17/08/2026 quy ước này chỉ tồn tại như một thói quen — chưa được ghi ở đâu — nên
`backend/` và `db/connect.py` theo được, còn `scripts/` thì trôi hẳn: `chay()`, `dung()`,
`tien()`, `ANH_XA_PROJECT`, `THU_MUC_THO`, `o_dau`, `ban_ghi`. Tiếng Việt **không dấu** là
tệ nhất trong ba lựa chọn: nó không đọc được như tiếng nào, và nó đụng vào từ tiếng Anh.

| Đổi sang tiếng Anh | Giữ tiếng Việt |
|---|---|
| Tên hàm, biến, tham số, hằng số, class | **Ghi chú** — mọi comment và docstring |
| | **Chữ người dùng đọc** — thông báo lỗi, nhãn giao diện, tên cột báo cáo |
| | **Cờ dòng lệnh** — `--thu-muc`, `--ra`, `--dot`, `--doi-chieu` |
| | **Khoá chuỗi trong dict cấu hình** — ví dụ `SOURCES[...]["bien"]` |
| | **Tên file** — chúng nằm trong tài liệu và spec đã archive |
| | `tools/` — chẩn đoán một lần, được phép mục |

### Gọi agent bằng TÊN, không bằng `agent_id` (thêm 20/08/2026)

`agent_id` là khoá đúng **trong SQL và trong biến**. Nhưng ở mọi chỗ **con người đọc** —
chữ in ra terminal, ghi chú, nhãn giao diện, báo cáo — phải viết **tên agent**.

```python
# SAI — người đọc phải đi tra bảng mới biết [5, 8] là ai
print(f"  agent co nguon 'app': {app_agents}")        #  [5, 8]

# ĐÚNG — JOIN dim_agent lấy `name`
print(f"  agent co nguon 'app': {', '.join(app_agents)}")
#  Tro Ly Ao Hop Dong, Tro ly ao Ralli
```

Áp cho cả **ghi chú**: viết *"Trợ lý ảo Ralli luôn rơi về 'app'"* chứ không phải
*"Ralli (agent_id=8) luôn rơi về 'app'"*. Cần chính xác kỹ thuật thì viết tên trước, mã
trong ngoặc: `Trợ Lý Ảo Hợp Đồng (tla-hd)`.

Bảng tra, để không phải mở database mỗi lần:

| `agent_id` | `code` | Tên |
|---|---|---|
| 1 | `contact-center` | Chatbot Contact Center |
| 2 | `sale-agent` | Sale Agent |
| 3 | `invoice` | Multi modal AI Invoice |
| 4 | `tools-quizzer` | Tools Quizzer |
| 5 | `tla-hd` | Trợ Lý Ảo Hợp Đồng |
| 6 | `dms-feedback` | Phân Loại Phản Hồi Tiếp Thị |
| 7 | `crm-feedback` | Phân Loại Dữ Liệu CRM |
| 8 | `ralli` | Trợ lý ảo Ralli |

**Vì sao thành quy ước:** một con số ID chỉ máy đọc được. Người đọc bản in *"agent co
nguon 'app': [5, 8]"* không có cách nào biết đó là hai agent nào mà không tra bảng — và
trong lúc soát số liệu thì mỗi lần phải tra là một lần dễ tra nhầm.

### Hai cái bẫy khi đổi tên hàng loạt

**① Tìm-thay thông thường sẽ phá code.** Định danh tiếng Việt không dấu **cũng là từ
tiếng Việt** trong ghi chú và chuỗi in ra: `dung` là tên hàm, đồng thời là từ trong
*"dung lai database"*, *"su dung"*, *"khong dung duoc"*. `\b` của regex không cứu được —
đó thật sự là một từ trọn vẹn. Phải phân biệt ở mức **token**:

```python
# tokenize thấy NAME khác STRING và COMMENT — chỉ sửa NAME
for tok in tokenize.generate_tokens(io.StringIO(src).readline):
    if tok.type == tokenize.NAME and tok.string in anh_xa: ...
```

Nhưng `tokenize` **chưa đủ**: trên Python 3.11 một f-string là **một token STRING duy
nhất**, nên mã trong `{...}` vô hình với nó. Đã đo lúc dính: 310 chỗ còn sót trên 20 file,
và **không chỗ nào lộ ra ở `--help`**. Trọng tài phải là `ast` — nó *có* phân tích nội
dung f-string. Và khi sửa trong f-string thì phải bỏ qua **chuỗi hằng nằm trong biểu
thức**, vì chúng thường là khoá dict: `f"{config['bien']}"`.

**② `argparse` suy tên thuộc tính từ CHUỖI cờ.** `--thu-muc` cho ra `args.thu_muc` bất kể
biến tên gì. Đổi biến mà không khai `dest=` là `AttributeError` lúc chạy — và `--help`
không bắt được vì argparse thoát trước đó. Cờ giữ nguyên cho người dùng, thuộc tính theo
tiếng Anh:

```python
p.add_argument("--thu-muc", dest="folder", default=str(RAW_DIR), ...)
```

Phép kiểm tĩnh cho cái bẫy này: với mỗi file có `add_argument`, mọi `args.<x>` phải khớp
một `dest` — soi bằng `ast`, không cần chạy.

### Nghiệm thu một đợt đổi tên

Đổi tên **không được** làm đổi hành vi, nên phép kiểm rẻ nhất và chắc nhất là **đầu ra
phải trùng khớp từng byte**:

```bash
python scripts/merge_billing.py --ra /tmp/x.csv        # so md5 với file trong data/da_xu_ly/
python scripts/merge_latency_daily.py --out /tmp/y.csv
PGDATABASE=<db tạm> python scripts/rebuild_db.py       # so 18 bảng + 8 mốc với database thật
python scripts/audit_db.py && python backend/check_api.py
node --test tests/load-failure-states.test.js          # bắt tham chiếu treo trong app.js
```

Số dòng thêm/xoá của một đợt đổi tên thuần phải **cân bằng** — thêm bao nhiêu thì xoá bấy
nhiêu. Lệch nghĩa là có logic bị thay đổi kèm.

## Thêm file mới thì để đâu

| File | Đi đâu | Vì sao |
|---|---|---|
| Script kéo dữ liệu mới | `scripts/` | Đường ống sản xuất |
| Script chẩn đoán một lần | `tools/diagnostics/` | Không có nghĩa vụ luôn xanh |
| Test phải luôn xanh | `tests/` | |
| Ảnh, CSS, JS của dashboard | `web/` | Được phục vụ ra mạng |
| Bảng tính, tài liệu Word, sketch | `planning/` | Không phải mã, không phải đầu vào |
| Đầu vào của đường ống | `data/` | Kể cả là `.xlsx` |
| Bất cứ thứ gì chương trình sinh ra khi chạy | `var/` | Xoá được, dựng lại được |

Một script được `update_dashboard.py` gọi thì **phải** ở `scripts/`. Đường ống sản xuất
không bao giờ gọi vào `tests/` hay `tools/`.

Ba loại kế hoạch không gộp vào nhau: `.hermes/plans/` là WIP của Hermes,
`docs/superpowers/plans/` là implementation plan đã publish theo workflow, còn
`planning/` chứa tài liệu nghiệp vụ và bản phác thảo cho con người.

⚠️ **`scripts/` chỉ chứa `.py`.** Một file dữ liệu do script sinh ra KHÔNG được nằm cạnh
script sinh ra nó. Đã dính: `scripts/seed-days-that.js` — 281 KB số liệu nhúng, sinh bởi
`sinh_du_lieu_dashboard.py` và đọc bởi `va_app_js.py`. Khi cả hai script bị xoá
(17/08/2026) thì nó ở lại, mồ côi hoàn toàn, và không phép kiểm nào phát hiện — vì nó nằm
đúng chỗ mà quy ước không nói tới. File dữ liệu trung gian thuộc `var/`.

⚠️ **`web/` cũng chỉ chứa mã.** Đường ống MUST NOT ghi vào `web/`; chạy trọn xong thì
`git status web/` phải trống. Trước 17/08/2026 có một bước vá số liệu thẳng vào
`web/js/app.js` — đó là lý do dashboard từng hiện số cũ mà trông y hệt số mới.
