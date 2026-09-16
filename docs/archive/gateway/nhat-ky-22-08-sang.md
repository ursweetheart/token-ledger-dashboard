# Nhật ký sáng 22/08/2026

Tiếp theo `nhat-ky-21-08-chieu.md`. Đọc nhanh: mục 1, mục 4 và mục 7.

**Đã commit 6 lần** — lần đầu sau hai ngày. Change mới đã lưu trữ. Mọi phép kiểm xanh.

---

## 1. Tóm tắt

> Sáng nay có một bài học lặp lại **bốn lần**: mỗi lần tôi khẳng định một điều bằng cách
> *đọc code*, phép đo lại bác bỏ. Không lần nào là lỗi đánh máy — lần nào cũng là một
> kết luận nghe rất hợp lý, rút ra từ mã nguồn đọc kỹ, và sai.

```
   ① Commit 21/08          6 commit · nhanh Tuan-develop di truoc main 30 commit
   ② Doi chieu tai lieu    3 viec tuong con -> thuc ra 1 con, 1 xong, 1 nho cho
   ③ Do 6 dong svc.*       toi sai 2 lan lien tiep, phep do sua ca hai
   ④ Change moi + luu tru  45/45 task, spec chinh thu 4
```

Việc đỏ trong `viec-can-lam-truoc-api-gateway.md` vẫn hết. Cái sáng nay làm là **siết lại
một dòng chịu lực chưa ai đặt tên cho nó**.

---

## 2. Trước hết: hai ngày làm việc chưa commit dòng nào

Điều lớn nhất phát hiện sáng nay lại **không nằm trong tài liệu nào**:

```
   git log -1     ->  f3cd51a   20/08/2026
   git status     ->  16 file sua  +  8 muc chua theo doi
```

Toàn bộ 21/08 — cả hai change, `tools/dien_tap_gateway.py`, `tools/soat_khoa_api.py`,
hai file nhật ký — **chỉ tồn tại trong thư mục làm việc**. Một lần `git checkout .` gõ
nhầm là mất trọn ngày rưỡi đã nghiệm thu 24/24 + 18/18 + 36 phép kiểm.

Đã commit thành **6 lần**, theo đúng lối 24 commit trước (tiếng Anh, thân bài văn xuôi
ngắt 72 cột, không trailer, tách `docs: propose …` khỏi `feat: …`):

```
   2678f6f  docs: propose admitting the Gateway as a fourth data source
   2b9a842  feat: admit the Gateway as a fourth data source
   46d3e61  docs: propose requiring a key to read the API
   f1f9a87  feat: require a key to read the API
   eb8ad79  docs: settle which claim carries the username, and register the sources
   81bb41c  docs: update the readiness list and the colleague sync note
```

Ba file nhật ký để ngoài theo yêu cầu. Nhánh `Tuan-develop` nay đi trước `main` **30
commit** — vẫn chưa gộp.

---

## 3. Đối chiếu tài liệu với commit: ba việc "còn treo" hoá ra không phải

| Việc | Tài liệu ghi | Đo ra |
|---|---|---|
| **D1** `gen_catalog.py` không chạy lại được | thiếu `tla-hd/**2026-08-14**/token-usage-year.json` | `_latest_dir()` trỏ vào **`2026-08-17`**, nơi file đó **có mặt** ở cả hai app. `2026-08-14` là thư mục một-file của `pull_hd_usage.py`, gen_catalog không đọc |
| **B3** ghi chú hạn dùng của `gcp_project_id` | 🟡 chưa làm | **đã có** ở `db/01_schema.sql:52-59` từ commit `c3d7169` |
| **D2** không có gì chạy trên máy trắng | `audit_db` 30 phép, `check_api` 16 phép | nay **36** và **19**; và `tools/soat_khoa_api.py` chạy **không cần Docker lẫn database** — thứ đầu tiên trong repo làm được thế |

`gen_catalog` còn chỉ lấy `costs.by_model` — **tập tên model**, không lấy số, không lấy
ngày — rồi `raise SystemExit` nếu gặp model lạ. Tức nó hỏng **to tiếng**.

Việc D1 thật nằm chỗ khác: `data/` trong `.gitignore` nên máy khác có **số không** đầu
vào. Cùng bài toán với D2 và D3.

---

## 4. Bốn lần đọc code ra một đằng, đo ra một nẻo

Đây là phần đáng giữ lại nhất của buổi sáng.

### ① "Sáu dòng `svc.*` bị frontend vứt im lặng" — SAI

Lập luận: `api.js` có `if (u.is_technical) return;`, và
`buildAccountCatalogueFromDb` lọc `u.unitId &&`. Đơn vị của 6 tài khoản dịch vụ là đơn vị
kỹ thuật, không có trong `ORG_UNITS` → `unitId` rỗng → bị vứt. Đọc kỹ, nghe chắc.

**Đo A/B thật:** `USER_ACCOUNTS` **937 → 943**, `svc.*` **0 → 6**, bị vứt **0**.

Chỗ tôi bỏ sót là dòng ngay sau đó:

```js
var unit=unitById(a.unit_id)||unitOf(a.unit_name)||null;
                              ^^^^^^^^^^^^^^^^^^^
```

`unitOf()` **tự chế ra một đơn vị** khi tra không ra. `unitId` không bao giờ rỗng, nên
`.filter()` vô hại.

### ② "Bỏ bộ lọc thì 6 phòng ban mới mọc ở cấp gốc" — CŨNG SAI

Sửa lần một xong, tôi lại suy tiếp từ `unitChildIndex[""].push(unit)`. **Đếm thật:**

```
              don vi GOC   trong do auto:true   DEPT_PROVISIONED
   truoc          11               7            101 don vi / 3.693
   sau            11               7            101 don vi / 3.693
```

Sáu đơn vị *"Đơn vị sử dụng …"* **đã có sẵn từ trước** — `unitOf()` trả về bản cũ chứ
không `push()` bản mới. Change không thêm phòng nào.

> **Phát hiện kèm theo:** hôm nay **7 trong 11 đơn vị ở cấp gốc** của cây tổ chức là do
> máy tự chế — sáu cái *"Đơn vị sử dụng …"* cộng *"Chưa quy được"*. Không parent, không
> mã thật, không ai chủ động tạo. Chúng sinh ra từ các **dòng usage** mang tên phòng ban
> tra không ra. Đây là tình trạng có sẵn, ngoài phạm vi change — nhưng đáng hỏi: cây
> phòng ban trên dashboard có đang hiện 7 phòng không ai tạo ra không?

### ③ "Hôm nay không có gì kêu lên nếu ai đó gỡ bộ lọc" — SAI NỐT

Viết câu này vào proposal. Đến lúc **kiểm ngược** (nới bộ lọc để xem phép kiểm mới có kêu
không) thì ra **2 hỏng**, không phải 1. Phép kiểm cũ `So tai khoan khop` **có** bắt được
— nó so số dòng API với `COUNT(*) WHERE kind='real'`.

Nhưng nó yếu ở hai chỗ, và đó mới là lý do phép kiểm mới đáng có:

| | |
|---|---|
| Chi tiết khi hỏng | **chuỗi rỗng** — in ra đúng một dòng trắng |
| Cách khẳng định | **soi gương bản cài đặt** — sửa cả hai chỗ cho khớp thì nó xanh lại |

Đã vá luôn phần chi tiết rỗng đó.

### ④ Một kết quả sai in thẳng ra màn hình mà tôi đọc lướt qua

Sau khi nghiệm thu xong và báo "tất cả xanh", vòng soát lại phát hiện `main()` của
`check_api.py` bị chèn nhầm chỗ:

```
   TIEU DE IN RA                    PHEP KIEM THUC SU CHAY DUOI DO
   Chi doc                          (khong co gi)
   Pham vi du lieu phoi ra          Danh ba ... + Ket noi backend la CHI DOC  ← sai muc
```

Dòng `[ ok ] Ket noi cua backend la chi doc` đã in ra dưới tiêu đề *"Phạm vi dữ liệu phơi
ra"* ngay trong lần chạy nghiệm thu, và tôi không nhận ra.

**Điểm chung của cả bốn:** không cái nào làm chương trình dừng. Loại lỗi này chỉ bắt được
bằng cách **đọc lại bằng mắt trước khi chạy**, hoặc bằng cách đo thay vì suy.

---

## 5. Change `pin-the-directory-to-real-people`

Sau khi đo xong, việc đúng hoá ra **không phải** việc đã ghi trong tài liệu.

`viec-can-lam-truoc-api-gateway.md` mục B5 ghi *"hoãn, đi cùng B1"* với lý do: ô ma trận
sẽ đổi từ `—` thành `0/1`. **Lý do đó nhắm sai hàm** — ma trận ăn từ `adoption()`, đã sửa
xong 21/08. Hai hàm không dính nhau.

Hại thật, sau khi trừ đi mọi thứ đo ra là không đổi, chỉ còn **hai chỗ**:

1. Sáu dòng *"Cả &lt;tên agent&gt;"* hiện trong bảng danh bạ như sáu con người
2. Mẫu số thẻ "User hoạt động" 937 → 943 (2,77% → 2,76%)

Nên chọn **giữ nguyên hành vi, và đặt tên cho nó**:

| | |
|---|---|
| `store.py` | Ghi chú tại chỗ: đây là **tấm lưới duy nhất**, kèm bảng đo, kèm hai chỗ *trông như đỡ mà không đỡ*. Và một dặn dò: **đừng viết quá lên** — nói "sập màn hình" thì người sau sẽ nới ra để thử |
| `check_api.py` | Phép kiểm mới hỏi **dữ liệu trả về**, không đọc mã nguồn. 18 → **19 phép** |
| `tools/` | Vá harness (mục 6) |
| tài liệu | Viết lại **5 chỗ** đã lỗi thời |

Ghi chú nhắc **người đọc code**; phép kiểm bắt **người sửa code mà không đọc**.

**Kiểm ngược:** nới bộ lọc → exit 1, và gọi đúng tên từng dòng:

```
[ HONG ] Danh ba /api/accounts chi co tai khoan la nguoi
         6 dong khong phai kind='real': svc.contact-center(service_account),
         svc.crm-feedback(service_account), ...
```

---

## 6. Chỗ thứ năm dính bẫy khoá: một công cụ hỏng từ hôm qua

`tools/chay_dashboard_trong_node.js` có `localStorage` giả **rỗng**. Từ 21/08 nó dừng ở ô
nhập khoá và **không gọi một endpoint nào** — trong khi vẫn in "nạp OK" và **thoát 0**.

Đo ngày 22/08 trên chính file chưa sửa:

```
   exit code                 0
   in "nap OK"               2 lan
   nhat ky uvicorn           0 dong GET /api/
   conn-text                 "Chua nhap khoa"   <- co dau vet, nhung o cuoi bang
                                                   do DOM, khong ai doc
```

Đây đúng cái bẫy đã bắt được ở **bốn kịch bản test JS** hôm 21/08 — chỉ khác là `tools/`
không nằm trong bộ kiểm nên không ai chạy, không ai thấy. Chỗ thứ **năm**.

Và khi vá, lại vấp thêm một lỗi cùng họ: bản vá đầu **đoán một con số giây** (PROBE chốt
3400ms, bảng báo cáo đọc 4000ms). Backend thật có lúc chậm hơn thế — bộ test JS mất 9
giây. Khi đó harness sẽ báo *"không nạp được"* trong khi nó chỉ **chưa xong**: một phép
kiểm hỏng vì lý do sai, còn tệ hơn không có phép kiểm.

Đổi sang vòng chờ. **Phụ thu: harness nay xong trong 1 giây thay vì 4**, vì nó thôi chờ
ngay khi có dữ liệu.

Ba nhánh hỏng nay phân biệt được, cả ba đều exit 1:

```
   chua co khoa   ->  conn-text = "Chua nhap khoa"
   khoa sai       ->  conn-text = "Khoa khong dung"
   may chu tat    ->  conn-text = "Khong co du lieu"
```

---

## 7. Đang ở đâu

### Nghiệm thu

```
   check_api.py    19 phep | 19 dat | 0 hong        (18 -> 19)
   audit_db.py     36 phep | 31 dat | 5 luu y | 0 hong
   test JS         6 + 11, 0 fail
   harness         exit 0 · 937/937 · svc.* 0 · 26/937 · goc 11 (tu tao 7) · 1 giay
   bat bien        1.189 dong · 867.657.110 token · $291,985601   khong lech mot token
```

Change đã lưu trữ thành `2026-08-22-pin-the-directory-to-real-people`. `openspec/specs/`
nay có **4 spec chính** — `account-directory-scope` là cái mới, và là cái duy nhất có
phần `## Purpose` được điền (ba cái kia còn `TBD` từ đợt 16/08).

### Ba quyết định anh chốt sáng nay

| | |
|---|---|
| **A6 độ mịn thời gian** | **Mức ngày** — nhưng Gateway sẽ có request thời gian thực rồi ta **tổng hợp** theo ngày. Nên việc đúng không phải hạ `Data Out` #2 xuống mức ngày, mà là ghi rõ **ranh giới**: nguồn giữ mức request, dashboard đọc bản tổng hợp |
| **`cost_is_estimated`** | Mức quan trọng **trung bình** — gộp vào cùng lượt sửa xlsx, không tách riêng |
| **6 dòng `svc.*`** | **Lối 2** — giữ nguyên hành vi, đặt tên cho nó, khoá bằng phép kiểm |

### Còn treo

| | Việc |
|---|---|
| 🔴 | **Chép bản có ngày của `.xlsx` và `.docx` trước khi sửa.** Git **không theo dõi một file xlsx/docx nào** — `*.xlsx` nằm trong `.gitignore`, `.docx` chưa ai `git add`. Master Plan không có lịch sử phiên bản nào cả |
| 🔴 | **Đo tỷ lệ lỗi + p95/p99** để chốt bộ số nền. Token/tiền/độ phủ đã có; hai chỉ số này lấy từ `/api/performance` là xong — và **phải lấy sớm**, cửa sổ Google trượt 196→112 ngày trong một tuần |
| 🟡 | **A4 + A5 + hai chỗ trong Master Plan** — 4 kiểu dữ liệu sai, `thinking_enabled`/`output_modality` còn ghi nguồn "Hiện có", mục tiêu *"Đo hiện trạng làm mốc"* bị đánh rơi khỏi bản chính, `cost_is_estimated` bị hạ xuống không bắt buộc |
| 🟡 | **A2 dư** — sửa `.docx` §1.2: `tla-rally`→`tla-ralli`, `tools-quiz`→`tools-quizz` |
| 🟡 | **Task 5.4 của change hôm qua** — mở Chrome, `Ctrl+Shift+R`, dán khoá. Test JS dùng DOM giả bỏ qua CSS hoàn toàn, nên **chưa gì chứng minh ô nhập khoá hiện đúng** |
| ⚪ | C3 + D3 chung một việc: thêm Nginx/LiteLLM/Redis vào `docker-compose.yml` |
| ⚪ | D1 thật + D2: chạy được trên máy trắng, có CI. `tools/soat_khoa_api.py` đã là mẫu |
| ⚪ | 7 đơn vị `auto:` ở cấp gốc cây tổ chức — hỏi anh: dashboard có đang hiện chúng không? |
| ⚪ | 30 commit trên `Tuan-develop` chưa gộp vào `main` |

### Chưa commit

Bốn file của change sáng nay (`store.py` · `check_api.py` · `chay_dashboard_trong_node.js`
· `viec-can-lam-truoc-api-gateway.md`), thư mục archive, spec mới, và 6 file chưa theo dõi:
4 nhật ký (kể cả file này), `.docx`, và báo cáo LiteLLM.
