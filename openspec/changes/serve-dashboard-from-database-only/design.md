## Context

Dashboard hiện chạy theo lối **vẽ trước, thay sau**. `web/js/app.js:5245` `init()` gọi
`loadState()` rồi `renderAll()` ngay, sau đó `napTuBackend()` mới hỏi API và ghi đè:

```
  init()
    ├─ loadState() ──▶ localStorage  ──(rỗng/lỗi)──▶ defaultState()
    │                                                     │
    │                                    buildJuneExcelWeeks() + SEED_DAYS
    │                                                     │
    ├─ renderAll()  ◀────────────────── VẼ SỐ CŨ RA MÀN HÌNH
    │
    └─ napTuBackend() ──▶ API ──┬─ được  ──▶ ghi đè state ──▶ renderAll()
                                └─ hỏng  ──▶ return null  ──▶ KHÔNG LÀM GÌ
                                                                   │
                                              số cũ ở lại trên màn hình,
                                              chỉ có một dòng console.warn
```

Chính docstring của `napTuBackend()` nói rõ thiết kế này: *"dashboard hiện ra ngay bằng dữ
liệu nhúng, rồi số thật thay vào khi backend trả lời. Không có backend thì không có gì xảy
ra."* Vế cuối là vấn đề: "không có gì xảy ra" nghĩa là số cũ ở lại và trông như số mới.

Số liệu nhúng đã lệch **-15,6%** so với database, chỉ **25/224 ngày** khớp.

**Một phát hiện thêm khi soát.** `napTuBackend()` cố ý không gọi `saveState()`, với lý do
đúng ghi tại dòng 5333: *"Ghi dữ liệu backend vào localStorage sẽ khiến lần mở sau dùng bản
cũ mà tưởng là mới."* Nhưng `saveState()` được gọi từ **9 chỗ khác** — đổi bộ lọc, sửa bảng
giá, bung/thu cây phòng ban — và nó ghi **toàn bộ** `state`, gồm cả `state.days` lúc này đã
chứa dữ liệu backend:

```javascript
function saveState(){ try{ localStorage.setItem(STORE, JSON.stringify(state)); }catch(e){} }
```

Nên ý định ở dòng 5333 bị vô hiệu bởi bất kỳ cú bấm nào của người dùng. Sau một lần lọc,
dữ liệu backend nằm trong `localStorage`; lần mở trang sau, `loadState()` đọc nó ra và vẽ
trước khi hỏi API. Đó là vector dữ liệu cũ thứ hai, và nó không phải hardcode.

**Đã ĐO được trên trình duyệt thật, 17/08/2026** — không còn là suy luận từ đọc mã. Sau một
phiên xem dashboard bình thường, `localStorage` chứa:

```
khoá  agent-dash-state-v19-du-lieu-13-08          345 KB
      224 ngày · 1.154 dòng · 2026-01-01 → 2026-08-13
      input 539.777.683 · output 87.446.579 · cached 224.609.584
```

`cached = 224.609.584` khớp **đúng** con số billing-only mà `api.js:157` chuyển tiếp, nên
đây chắc chắn là dữ liệu backend đã bị ghi xuống, không phải `SEED_DAYS`.

**Và nó là vector thực sự nổ ra.** Trỏ dashboard vào một backend không tồn tại
(`?api=http://127.0.0.1:9999`) rồi so:

| | Nguồn | Tổng token kỳ 01/08→13/08 | Hiện trên màn hình |
|---|---|---|---|
| Database | Postgres | 45.685.588 | **45,7 triệu** |
| `localStorage` | phiên trước | ~45,6 triệu | **45,7 triệu** ← đã hiện cái này |
| `SEED_DAYS` | nhúng trong mã | 50.280.159 | 50,3 triệu |

Với backend chết, màn hình hiện **45,7 triệu** — tức nó lấy `localStorage`, không lấy
`SEED_DAYS`. Nghĩa là **thứ tự ưu tiên của dữ liệu cũ là `localStorage` trước, dữ liệu nhúng
sau**; xoá `SEED_DAYS` mà không sửa `saveState()` sẽ **không** đóng được đường này.

Ba con số headline (request · token · tiền) trùng nhau ở độ chính xác hiển thị, nên mắt
không bắt được. Nhưng chiều người dùng thì lệch rõ và vẫn không có cảnh báo nào:

| Thẻ | Backend chạy | Backend chết |
|---|---|---|
| AI AGENT | 7/8 | 7/**7** |
| USER HOẠT ĐỘNG | **15** | **0** |
| MỨC ĐỘ SỬ DỤNG TB/USER | 66,7 nghìn | **0** |
| Tài khoản không hoạt động | 922 | **622** |

## Goals / Non-Goals

**Goals:**

- Mọi con số trên dashboard đến từ database. Không nguồn thứ hai nào, kể cả dự phòng.
- Không nạp được thì **nói ra trên màn hình**, và không hiện con số nào.
- Bốn trường hợp lỗi phân biệt được với nhau: backend tắt · endpoint lỗi · database chưa có
  dữ liệu · mở bằng `file://`.
- `localStorage` chỉ giữ lựa chọn của người dùng, không giữ số liệu.
- Đường ống không còn bước nào ghi vào `web/`.

**Non-Goals:**

- Không thiết kế lại giao diện. Đây là change về **nguồn dữ liệu**, không phải về trình bày.
  Bố cục, màu, biểu đồ giữ nguyên.
- Không đổi hình dạng dữ liệu mà `api.js` dịch ra (`a`, `m`, `ti`, `to`…). Lớp dịch đó là
  chỗ giữ cho `app.js` không phải sửa; đụng vào là mở rộng phạm vi vô ích.
- Không thêm cơ chế xem offline kiểu khác (service worker, cache API). Xem offline chính là
  cái đang che lỗi.
- Không sửa cách backend chọn nguồn hay tính số.
- Không tối ưu kích thước `app.js`. Nó nhỏ đi 390 KB, nhưng đó là hệ quả, không phải mục
  tiêu.

## Decisions

### 1. Đảo luồng: **nạp trước, vẽ sau**

Đây là quyết định gốc; bốn quyết định sau đều là hệ quả.

```
  init()
    ├─ loadPrefs()  ──▶ localStorage: CHỈ tab, giao diện, khoảng ngày
    ├─ renderShell()  ──▶ khung + trạng thái "đang nạp…", KHÔNG số nào
    │
    └─ napTuBackend() ──▶ API ──┬─ được ──▶ state = dữ liệu ──▶ renderAll()
                                └─ hỏng ──▶ renderError(lý do) ──▶ DỪNG
```

`defaultState()` không còn dựng dữ liệu — nó trả về state rỗng kèm lựa chọn người dùng.
`renderAll()` chỉ được gọi khi đã có dữ liệu thật.

*Đã cân nhắc:* giữ lối vẽ-trước và chỉ thêm một dải cảnh báo khi hỏng. Bị loại: nó vẫn hiện
số cũ bên dưới dải cảnh báo, và kinh nghiệm trong chính dự án này là người xem tin bảng số
hơn dòng chữ cạnh nó. `backend/main.py:17-23` đã chốt nguyên tắc: *"nếu frontend không hiện
được phần này thì bỏ đi còn hơn."*

*Đã cân nhắc:* để `api.js` tự vẽ lỗi. Bị loại: `api.js` có hợp đồng rõ là **chỉ bơm dữ
liệu, không đụng giao diện** (ghi ở đầu file). Giữ hợp đồng đó — `api.js` trả về *lý do
hỏng* dưới dạng dữ liệu, `app.js` quyết định vẽ thế nào.

### 2. `api.js` trả về kết quả có phân biệt, thay cho `null`

Hiện `catch` gộp mọi thất bại thành `null`. Đổi thành trả về một đối tượng nói rõ loại lỗi
— đủ để `app.js` phân biệt bốn trường hợp trong spec, kèm địa chỉ đã thử và endpoint nào
hỏng.

Vẫn **không** `reject`: backend chưa chạy là chuyện thường, không phải ngoại lệ chương
trình. Chỉ đổi từ "im lặng" sang "nói rõ".

*Đã cân nhắc:* để `load()` reject và bắt ở `app.js`. Bị loại: mọi chỗ gọi phải bọc
`try/catch`, và một lần quên là quay lại đúng chỗ cũ — thất bại im lặng.

### 3. Tách `localStorage` làm hai: lựa chọn và dữ liệu

`saveState()` hiện ghi cả `state`. Đổi để nó **chỉ** ghi các khoá lựa chọn (tab, giao diện,
khoảng ngày, trạng thái bung/thu cây, bộ lọc). `state.days`, `state.dayOrder`,
`state.pricing`, và các bảng dẫn xuất MUST NOT được ghi.

Cách này sửa được cái mà ghi chú ở dòng 5333 chỉ *mong* làm được: nó không phụ thuộc vào
việc mọi chỗ gọi `saveState()` phải nhớ điều gì. Danh sách khoá được ghi là **danh sách
cho phép**, không phải danh sách loại trừ — thêm một trường dữ liệu mới về sau sẽ không tự
động bị ghi.

Đổi tên khoá `STORE` một lần để bỏ state cũ trên máy đang dùng. Sau change này việc bump
khoá theo mỗi lần cập nhật dữ liệu không còn cần — vì không còn dữ liệu trong đó.

*Đã cân nhắc:* xoá `localStorage` hoàn toàn. Bị loại: người dùng mất tab đang xem, giao
diện tối, và khoảng ngày mỗi lần tải trang. Đó là mất mát thật, không đổi lấy gì.

### 4. Bảng giá và hạn mức: chỉ một nguồn, và "chưa có" khác "bằng 0"

`basePricing` và `AGENT_MONTHLY_BUDGETS` bỏ giá trị gõ tay, khai rỗng và chỉ nhận từ
`/api/catalog`.

Phải giữ đúng một sự phân biệt mà `api.js:207-215` đã cẩn thận làm: agent **chưa đặt** hạn
mức thì không suy ra 0, vì 0 nghĩa là *hết* hạn mức. Ralli đặt hạn mức theo token chứ
không theo USD, nên nó thuộc nhóm "chưa đặt". Sau khi bỏ hằng số gõ tay, `MONTHLY_BUDGET`
(tổng) phải tính từ những agent **có** hạn mức, và giao diện phải nói được "chưa đặt".

Cấu hình `aliases` trong `AGENT_MONTHLY_BUDGETS` hiện dùng để khớp tên cũ **trong dữ liệu
nhúng**. Dữ liệu nhúng biến mất, nên phải kiểm xem `aliases` còn tác dụng gì với tên từ
database không; nếu không thì bỏ luôn thay vì để lại cấu hình chết.

### 5. Thứ tự xoá: đi từ lá vào gốc, test xanh sau mỗi bước

`tests/date-range-filter.test.js` nạp trọn `app.js` trong `vm`, nên nó bắt được **tham chiếu
treo** — gọi một định danh đã xoá. Đó là phép kiểm rẻ nhất đang có, và nó chỉ hữu ích nếu
chạy sau *từng* bước:

```
  1. api.js: trả kết quả có phân biệt        → test xanh (chưa ai xoá gì)
  2. app.js: đảo luồng, renderShell/Error    → test xanh
  3. app.js: tách saveState                  → test xanh
  4. app.js: basePricing + BUDGETS rỗng      → test xanh
  5. xoá SEED_DAYS + buildJuneExcelWeeks     → test bắt tham chiếu treo nếu sót
  6. xoá fallback/ralli-users.js + app.js.bak
  7. update_dashboard.py: 10 → 9 bước; xoá 2 script
  8. README + docs/reference
```

Bước 5 sau bước 2 là có chủ ý: đảo luồng trước thì lúc xoá dữ liệu không còn chỗ nào cần
nó. Làm ngược lại sẽ có một quãng dashboard vỡ mà không biết vì thiếu dữ liệu hay vì luồng
sai.

*Đã cân nhắc:* xoá hết rồi sửa. Bị loại: 390 KB biến mất một lúc thì lỗi đầu tiên che mất
mọi lỗi sau, và không biết cái nào gây cái nào.

### 6. Nghiệm thu bằng mắt, có danh sách

Change này không kiểm được bằng số như change Postgres. Một khối bị xoá thiếu **không ném
lỗi** — nó làm một biểu đồ trống hoặc một con số về 0, và trông hoàn toàn hợp lý.

Nên nghiệm thu là: mở dashboard với backend chạy, soát **từng tab**, đối chiếu với con số
đã chốt (851.897.312 token · 285,18 USD · 8 agent · khoảng 2026-01-01 → 2026-08-13). Rồi
tắt backend, tải lại, và xác nhận **không con số nào** hiện ra.

## Risks / Trade-offs

**Mất khả năng xem offline.** README đang quảng cáo "bấm đúp `index.html` vẫn xem được" →
Đánh đổi có chủ đích, là mục tiêu chứ không phải tác dụng phụ: chính cơ chế đó đã che mọi
lỗi backend. Sửa README nói rõ cần chạy backend.

**Xoá thiếu một khối là lỗi im lặng.** Biểu đồ trống trông giống "kỳ này không có dữ liệu"
→ Chặn bằng ba lớp: test bắt tham chiếu treo sau mỗi bước; soát từng tab; đối chiếu tổng với
con số đã chốt.

**`app.js` là một file 458 KB, sửa luồng khởi động là chạm vào chỗ mọi thứ đi qua.** →
Giữ `git` sạch trước khi bắt đầu để quay lui được từng bước. Không gộp với việc sửa giao
diện.

**Người dùng đang có state cũ trong `localStorage`.** Đổi khoá sẽ làm họ mất bộ lọc và cây
đang bung → Chấp nhận: một lần, và đó là cái giá của việc bỏ số liệu cũ khỏi cache.

**`aliases` có thể còn cần cho tên agent từ database.** Bỏ sớm thì một agent mất hạn mức
mà không ai thấy → Kiểm bằng cách đối chiếu 8 tên agent trong `dim_agent` với khoá của
`ref_budget` (7 dòng) trước khi bỏ.

## Migration Plan

**Triển khai:** 8 bước ở Decision 5, `node --test tests/date-range-filter.test.js` phải
xanh (6/6) sau mỗi bước.

**Quay lui:** `git checkout web/js/ scripts/ README.md`. Không có bước nào không hoàn
nguyên — khác hẳn change Postgres, ở đây không xoá dữ liệu nào, chỉ xoá mã và ảnh chụp còn
trong git.

**Thứ tự với change `switch-default-dsn-to-postgres`:** làm **sau**. Sau change này dashboard
không còn đường dự phòng, nên nó chỉ hiện số khi backend nối được database — cần database
mặc định ổn định trước, không thì lỗi hai bên trộn vào nhau.

## Open Questions

- Dải thông báo lỗi đặt ở đâu trong `web/index.html`? Cần một điểm neo thấy được ngay không
  phải cuộn, và không phá bố cục khi ẩn. Chọn lúc thực thi sau khi xem `index.html`.
- Trong lúc đang nạp thì vẽ gì? Nghiêng về khung tĩnh kèm chữ "đang nạp…", **không** vẽ
  biểu đồ rỗng — biểu đồ rỗng trông giống "không có dữ liệu", tức đúng loại nhập nhằng
  change này đang đi dọn.
- `tests/fixtures/ui-snapshot-2026-08-07.json` dùng cho việc gì? Không thấy
  `date-range-filter.test.js` đọc nó. Nếu là ảnh chụp giao diện của một cuộc điều tra cũ thì
  theo quy ước layout nó thuộc `tools/`, không phải `tests/fixtures/`. Kiểm khi thực thi.
