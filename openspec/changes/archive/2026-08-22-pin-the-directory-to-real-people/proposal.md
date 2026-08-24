# Danh bạ chỉ chứa con người — và điều đó phải là một cơ chế, không phải một dòng may

## Why

`backend/store.py:207` có đúng một dòng:

```sql
WHERE a.kind = 'real'
```

Không ghi chú nào nói dòng đó đang chặn cái gì. **Đo A/B ngày 22/08/2026** trên backend
thật và `app.js` thật (uvicorn + `tools/chay_dashboard_trong_node.js` đã gieo khoá), đổi
đúng một dòng đó rồi hoàn nguyên:

| | hôm nay | nếu bỏ lọc |
|---|---:|---:|
| `/api/accounts` trả về | 937 | **943** |
| `USER_ACCOUNTS` sau khi `app.js` lọc | 937 | **943** |
| bị vứt ở `buildAccountCatalogueFromDb` | 0 | **0** |
| dòng `svc.*` hiện lên màn hình | 0 | **6** |
| thẻ **User hoạt động** (`app.js:1331`) | 26/937 | **26/943** |

Sáu dòng đó là tài khoản dịch vụ của 6 agent một-người-dùng: `svc.contact-center`,
`svc.sale-agent`, `svc.invoice`, `svc.tools-quizzer`, `svc.dms-feedback`,
`svc.crm-feedback`, mỗi dòng mang `full_name = "Cả <tên agent>"`.

### Hai thứ trông như lưới đỡ, đo ra thì không phải

```
   accounts()  ──JOIN dim_unit──▶ QUA   unit_id = "__technical_<aid>__" CO that
               ──JOIN dim_agent─▶ QUA   unit_agent_id CO that
                     │
                     ▼   6 dong di qua API, len tan trinh duyet
   api.js:216   if (u.is_technical) return;      <- chan DON VI, khong chan TAI KHOAN
                     │
                     ▼
   app.js:177   var unit=unitById(a.unit_id)||unitOf(a.unit_name)||null;
                                              ^^^^^^^^^^^^^^^^^^^
   app.js:588   unitOf() tra ra don vi "auto:<ten>" - tao moi neu chua co,
                tra ve ban da co neu roi. O day la truong hop THU HAI:
                sau don vi do DA TON TAI san (xem bang duoi).
                => u.unitId khong bao gio rong => .filter() vo hai
```

Nên `.filter(u => u.unitId && …)` ở cuối `buildAccountCatalogueFromDb` **không loại được
dòng nào**: `unitOf()` luôn trả ra một `unitId` trước khi tới đó — ở đây là sáu đơn vị
`auto:` đã tồn tại sẵn. Đo ra đúng **0 dòng bị vứt** ở cả hai vế.

Cái fallback `unitOf()` không phải lỗi — nó có chủ ý, để tài khoản mang phòng ban lạ vẫn
hiện ra thay vì biến mất. Nhưng nó **vô hiệu hoá** tấm lưới người ta tưởng đang đỡ.

### Hậu quả dừng lại ở đâu — đo, không đoán

Bản đầu của mục này viết *"6 phòng ban mới mọc ở cấp gốc"*. **Đếm lại thì sai:** sáu đơn
vị *"Đơn vị sử dụng &lt;tên agent&gt;"* **đã có sẵn ở cấp gốc từ hôm nay**, do `unitOf()`
chế ra từ các dòng usage chứ không phải từ danh bạ. Bỏ bộ lọc không thêm phòng nào.

| | trước | sau |
|---|---:|---:|
| đơn vị ở cấp gốc (`unitChildIndex[""]`) | 11 | **11** |
| trong đó tự tạo (`auto:true`) | 7 | **7** |
| `DEPT_PROVISIONED` — mẫu số theo phòng | 101 đơn vị / **3.693** | 101 đơn vị / **3.693** |
| tử số tỷ lệ áp dụng | 26 | **26** |

`DEPT_PROVISIONED` đứng im vì `rebuildProvisionedFromDirectory()` lọc
`a.in_directory && !a.is_shared` **trước khi** gọi `unitOf()`, mà 6 dòng này có
`in_directory = 0` và `is_shared = 1`. Tỷ lệ áp dụng cũng vậy
(`eligible = inDirectory && !shared`).

**Vậy hại thật chỉ còn hai chỗ**, và cả hai đều nhỏ hơn bản đầu mô tả:

1. Sáu dòng mang tên *"Cả &lt;tên agent&gt;"* hiện trong bảng danh bạ như sáu con người
2. Mẫu số thẻ "User hoạt động" phình từ 937 lên 943 — tỷ lệ hiển thị 2,77% → 2,76%

Change này vì thế **ít khẩn hơn** bản đầu ngụ ý. Nó vẫn đúng, nhưng lý do là *"một dòng
chịu lực không có tên và không có phép kiểm"*, không phải *"sắp vỡ màn hình"*.

### Lý do hoãn ghi ngày 20/08 nhắm sai hàm

`viec-can-lam-truoc-api-gateway.md` mục B5 ghi: *"Làm riêng thì ô ma trận đổi từ `—`
thành `0/1` cho Chatbot Contact Center — đó là lời khẳng định sai, tệ hơn `—`."*

Ma trận và ô `—` ăn từ **`adoption()`**, không phải `accounts()`. `adoption()` đã sửa
xong 21/08 và nay không còn phân nhánh theo loại agent. Hai hàm không dính nhau. Lý do
thật để không gỡ bộ lọc là bảng đo ở trên, không phải ô ma trận.

### Vì sao không phơi 6 tài khoản đó lên (chưa)

Muốn hiện chúng tử tế thì phải quyết chúng nằm ở đâu trong cây. Hôm nay chúng sẽ rơi vào
sáu đơn vị `auto:` mà `unitOf()` đã chế sẵn — những đơn vị không có `parent`, không có
mã thật, và không ai chủ động tạo ra. Đó là việc đụng vào cây đơn vị, không phải thêm một
nhãn. Và hôm nay **chưa ai cần nhìn chúng** — `adoption()` đã trả lời được câu *"agent
này có chạy không"* mà không cần chúng có mặt trong danh bạ.

## What Changes

- **Giữ nguyên hành vi.** `/api/accounts` vẫn chỉ trả `kind='real'`
- **Ghi chú tại chỗ** ở `store.py:207` nói rõ: đây là thứ **duy nhất** chặn, kèm bảng đo
  22/08 và kèm lý do `api.js:216` cùng `.filter(u => u.unitId)` **không** đỡ
- **Một phép kiểm mới** trong `backend/check_api.py`: `/api/accounts` MUST NOT trả dòng
  nào có `kind <> 'real'`. 18 → **19 phép**
- **Sửa docstring đã sai** ở `store.py:192-194` — nó còn viết *"máy chủ này vẫn chưa có
  xác thực nào"*, sai từ 21/08
- **Vá `tools/chay_dashboard_trong_node.js`** — `localStorage` giả rỗng nên từ 21/08 nó
  dừng ở ô nhập khoá. Chạy thử 22/08: **exit code 0**, in "nạp OK" hai lần, và nhật ký
  uvicorn ghi nhận **0 lần gọi `/api/`**. Nó *có* để lại dấu vết — `conn-text` bằng
  *"Chưa nhập khoá"* — nhưng dấu vết đó nằm trong bảng đổ DOM ở cuối, không ai đọc. Gieo
  khoá từ `DASHBOARD_KEY`, và thoát khác 0 khi không nạp được dữ liệu
- **Viết lại năm chỗ đã lỗi thời** trong `viec-can-lam-truoc-api-gateway.md`: mục B5
  (lý do hoãn sai hàm), §5 Nghiệm thu (còn viết ở thì dự đoán, thực ra đã chạy 0/8→7/7),
  B1 (còn dòng "→ Việc:" nằm dưới khung ✅), D2 (số phép kiểm đã cũ), D1 (chỉ nhầm thư
  mục — `gen_catalog.py` dùng `_latest_dir()`)

**KHÔNG làm trong change này**

- Không phơi tài khoản dịch vụ lên giao diện
- Không đụng `unitOf()` hay cây đơn vị
- Không đụng `adoption()`, `usage_by_account`, `health()`
- Không đụng `db/` hay `scripts/` — không rebuild database

## Impact

| | |
|---|---|
| **Specs** | `account-directory-scope` (mới) |
| **Code** | `backend/store.py` · `backend/check_api.py` · `tools/chay_dashboard_trong_node.js` |
| **Tài liệu** | `docs/reference/viec-can-lam-truoc-api-gateway.md` |
| **Không đụng** | `db/` · `scripts/` · `web/` — không rebuild, không đổi một pixel |
| **Rủi ro** | **Rất thấp.** Không con số nào trên màn hình đổi. Change này biến một dòng đang đỡ *tình cờ* thành một dòng đỡ *có tên và có phép kiểm* |
| **Quay lui** | Một commit. Không có bước dữ liệu nào để hoàn tác |

### Cái bẫy chính của change này

Dễ làm thành "thêm một dòng chú thích rồi tick xong". Phép kiểm mới là phần đáng giá:
ghi chú nhắc **người đọc code**, còn phép kiểm bắt được **người sửa code mà không đọc**.

**Đính chính sau khi kiểm ngược 22/08:** bản đầu của mục này viết *"gỡ bộ lọc thì không
gì kêu lên"*. Sai — phép kiểm cũ `So tai khoan khop` **có** kêu, vì nó so số dòng API với
`COUNT(*) WHERE kind='real'`. Cái nó không làm được là nói **cái gì** đã lọt: phần chi
tiết của nó là một chuỗi rỗng, in ra đúng một dòng trắng. Và vì mẫu số của nó dùng lại
chính điều kiện của bản cài đặt, người sửa cả hai chỗ cho khớp sẽ thấy nó xanh trở lại.

Nên giá trị của phép kiểm mới không phải *"có cái để kêu"* mà là *"kêu ra được tên"*, và
khẳng định một tính chất thay vì so hai con số cùng nguồn.
