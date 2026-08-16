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
│   ├── js/       app.js · api.js · fallback/ralli-users.js
│   ├── css/      dashboard.css
│   ├── vendor/   chart.umd.min.js        ← mã đi mượn, tách khỏi mã tự viết
│   └── assets/   rang-dong-logo.png
│
├── backend/                ③ API chỉ-đọc (FastAPI) — 8 endpoint
│   main.py · store.py (mọi câu SQL) · check_api.py
│
├── scripts/                ① KÉO + ② GỘP + điều phối
│   pull_*.py (6) · merge_*.py (3) · update_dashboard.py (10 bước)
│   rebuild_db.py · audit_db.py (30 phép kiểm) · copy_to_postgres.py
│   sinh_du_lieu_dashboard.py · va_app_js.py    ← bước 10, LÀ script sản xuất
│
├── db/                     ③ SCHEMA + NẠP — chỉ chứa MÃ
│   01_schema.sql · 02_catalog.sql · load_*.py · build_*.py · connect.py · rules.py
│
├── data/                   Kho dữ liệu THÔ — mất là mất vĩnh viễn
├── var/                    Dữ liệu CHẠY — dựng lại được trong 15 giây
│   token_ledger.sqlite
│
├── tests/                  Phải LUÔN xanh
├── tools/                  Chẩn đoán một lần — ĐƯỢC PHÉP mục
├── docs/
│   ├── reference/          Hệ thống ĐANG là gì  ← file này
│   ├── decisions/          Quyết định còn hiệu lực
│   └── archive/            Nhật ký phiên — KHÔNG sửa, kể cả đường dẫn đã cũ
├── planning/               .xlsx · .docx · ghi chú họp
│
├── openspec/  .claude/  .agent/  .codex/       ← công cụ bắt buộc ở gốc
└── docker-compose.yml  .env.example  .gitignore  README.md
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

## Thêm file mới thì để đâu

| File | Đi đâu | Vì sao |
|---|---|---|
| Script kéo dữ liệu mới | `scripts/` | Đường ống sản xuất |
| Script chẩn đoán một lần | `tools/` | Không có nghĩa vụ luôn xanh |
| Test phải luôn xanh | `tests/` | |
| Ảnh, CSS, JS của dashboard | `web/` | Được phục vụ ra mạng |
| Bảng tính, tài liệu Word | `planning/` | Không phải mã, không phải đầu vào |
| Đầu vào của đường ống | `data/` | Kể cả là `.xlsx` |
| Bất cứ thứ gì chương trình sinh ra khi chạy | `var/` | Xoá được, dựng lại được |

Một script được `update_dashboard.py` gọi thì **phải** ở `scripts/`. Đường ống sản xuất
không bao giờ gọi vào `tests/` hay `tools/`.
