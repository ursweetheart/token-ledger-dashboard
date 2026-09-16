# Kế hoạch nén — API Gateway về đích 30/09/2026

Soạn 27/08/2026. **Không thay thế** `planning/Master Plan API Gateway.xlsx` — bản kế hoạch gốc giữ
nguyên lịch 20 tuần. File này là phương án nén, để so sánh và để quyết.

- Mốc gốc: **31/12/2026** (20 tuần)
- Mốc nén: **30/09/2026** (5 tuần, 25 ngày làm việc, trừ lễ còn **23**)
- Cắt đi: **13 tuần**

---

## 1. Trả lời trước: được, nhưng biên độ bằng không

Được — với **hai điều kiện bên ngoài**, và nếu thiếu một trong hai thì trượt, không phải
"cố thì kịp". Gate xóa/rename database đã bị rút ngày 27/08; giữ song song hai ledger không
chặn phát triển Gateway.

| | Điều kiện | Ai quyết | Hạn chót |
|---|---|---|---|
| ① | 8 khoá API của 8 project nộp đủ về một chỗ | TTDL&ĐHS (An Thanh) | **28/08** |
| ② | Được quyền đổi `base_url` của Ralli và 7 agent còn lại | TTDL&ĐHS (An Thanh) | **04/09** |

Điều kiện ② **không thay thế được bằng việc viết thêm code**. Chưa có quyền đổi `base_url`
thì chưa agent thật nào đi qua Gateway; xin muộn một ngày là mất một ngày rollout.

---

## 2. Hai thứ không nén được và một invariant phải giữ

**① Hai tuần chạy song song.** Chính Master Plan đặt sàn này (GĐ7 dòng 19), và nó là thứ
duy nhất chứng minh được Gateway không làm lệch số. Nén xuống 1 tuần thì báo cáo đối chiếu
mất một nửa cơ sở. **Giữ nguyên 2 tuần: 14/09 → 25/09.**

**② Nghỉ lễ 02/09.** Thứ Tư, nghỉ 2 ngày theo luật. Tuần 31/08–04/09 chỉ còn **3 ngày**.
Đây là tuần dựng Gateway thật — tuần nặng nhất lại là tuần ngắn nhất.

**③ Cửa sổ đối chiếu hai tuần.** `token_ledger` legacy, `token_ledger_v2` runtime và database
`litellm` được giữ tách biệt. Việc không xóa/rename database loại bỏ một destructive gate,
nhưng không được dùng để rút ngắn cửa sổ đối chiếu Gateway với các nguồn cũ.

---

## 3. Chỗ nén được, và nén bằng cách nào

Lịch gốc xếp GĐ7 (chạy song song 2 tuần) **rồi mới** tới GĐ8 (chuyển 8 agent, mỗi agent
song song ≥1 tuần). Xếp nối tiếp như vậy là 2 + 8 = 10 tuần nếu chuyển từng đợt.

**Hai giai đoạn đó là cùng một cái đồng hồ.** Một agent đã trỏ qua Gateway trong kỳ đối
chiếu thì chính nó *đang* chạy song song. Ba nguồn cũ — `billing`, `monitoring`, `app` —
không hề dừng ghi khi agent đổi `base_url`: `billing` và `monitoring` ghi ở phía Google,
`app` ghi ở phía Ralli. Chuyển agent qua Gateway **không tắt nguồn nào cả**.

Vậy: đưa cả 8 agent vào **đầu** cửa sổ đối chiếu. Mỗi agent nhận đủ 2 tuần song song —
nhiều gấp đôi mức sàn "≥1 tuần" của GĐ8. 10 tuần co còn 2.

**Cái phải trả cho việc đó:** một lỗi của Gateway sẽ đập vào cả 8 agent cùng lúc, thay vì
1 agent. Đổi lại:

- Không mất số. Ba nguồn cũ vẫn ghi suốt — lỗi Gateway làm *gián đoạn dịch vụ*, không làm
  *mất dữ liệu*.
- Đường lùi là một dòng cấu hình: trỏ `base_url` của agent về thẳng nhà cung cấp. Phải đo
  **thời gian lùi thực tế** trong buổi diễn tập tuần 2, không được để tới lúc cần mới thử.

---

## 4. Lịch 5 tuần

### Tuần 0 — 27/08 (Năm) → 28/08 (Sáu) · 2 ngày · *mở khoá, không gõ phím*

Tuần này không dựng gì. Nó chỉ để gỡ ba thứ chặn đường, vì cả ba đều cần người khác.

```
   [ ] Gui yeu cau thu 8 khoa API cua 8 project           -> dieu kien ①
   [ ] Dat lich soat doc lap cong 6.3 voi Chi Thanh       -> dieu kien ②
   [ ] Xin quyen doi base_url cua Ralli + 7 agent         -> dieu kien ③
   [x] Sinh LITELLM_MASTER_KEY / LITELLM_SALT_KEY, dien .env            -- XONG 29/08
       (sua lai 1 lan: khoa dau tien thieu tien to 'sk-', entrypoint.sh
       tu choi, da sinh lai bang secrets.token_urlsafe(32))
   [x] `docker compose --profile gateway up -d` -- dung thu tren may cuc bo  -- XONG 29/08
       6/6 container gateway Healthy, /health/liveliness qua load balancer -> HTTP 200
   [x] Go JWT_test_for_header khoi goc repo            -- XONG 27/08
   [x] Che JWT trong 2 file bang chung o ket-qua/      -- XONG 27/08
   [x] tools/diagnostics/scan_secrets.py: quet bi mat theo HINH DANG, rc=0
```

**Chốt tuần 0:** Gateway lên được ở máy cục bộ, `/health/liveliness` trả 200 qua load
balancer, và ba yêu cầu ① ② ③ đã gửi đi — *đã gửi*, chưa cần có kết quả.

### Tuần 1 — 31/08 → 04/09 · **3 ngày** (nghỉ 02–03/09) · *dựng bản thật*

```
   [ ] Khai 8 tuyen / 8 project vao config.gateway.yaml, moi tuyen mot khoa rieng
       -- CHUA. config.gateway.yaml hom nay chi 3 tuyen, ca 3 dung CHUNG mot
       khoa KEY_GOOGLE_AI_STU. Cho dieu kien ① (8 khoa API cua 8 project)
   [x] Them gemini-3.6-flash vao db/rules.py + dim_model  (muc 6 ②, viec nho)
       -- XONG 06/09, qua close-the-known-gateway-loose-ends (chua commit)
   [ ] Cap 8 Virtual Key, moi agent mot khoa, thu hoi doc lap tung khoa
       -- 1/8. Chi dms-feedback co Virtual Key that (tag "dms-feedback",
       config.gateway.yaml). 7 agent con lai (Ralli, TLA Hop Dong, CRM,
       Contact Center, Sale Agent, Multi modal AI Invoice, Tools Quizzer)
       van goi thang nha cung cap
   [x] Chot dinh dang danh tinh: end_user = claim `sub`, KHONG phai ca chuoi JWT
       -- XONG. config.gateway.yaml: user_header_name="X-User" nhan claim
       `sub`, co ghi chu "da chot" ngay trong file cau hinh
   [x] Xac nhan ingestion chi ghi token_ledger_v2; token_ledger legacy chi doc
       -- XONG 31/08, qua load-the-gateway-ledger-into-the-database
```

**Chốt tuần 1: ĐẠT 31/08 — nhưng (trên một agent).** Request thật của `dms-feedback` đi
qua Gateway tới Google và về, `LiteLLM_SpendLogs` có `end_user = svc.dms-feedback` đúng
người, `spend 0,0026954` khác 0, prompt đã bị xoá. Đây là mốc tối thiểu của kế hoạch, đã
đạt — nhưng mới đúng cho **một** agent trong 8, không suy rộng ra cả 8 được.

> Ba ngày cho khối này là chặt. Nếu tới hết 04/09 mà chưa có một request thật đi qua
> Gateway thì **dừng lại báo ngay**, đừng bù bằng cách làm đêm.
>
> *(Đã không phải dừng — mốc trên đạt đúng hạn 31/08.)*

### Tuần 2 — 07/09 → 11/09 · 5 ngày · *đường dữ liệu + diễn tập*

```
   [x] Migration 004: bang fact_request. BAT BUOC co cot `status`
       (do duoc 26/08: LiteLLM ghi ca request THAT BAI kem token count)
       -- XONG, nhung KHAC TEN: khong dung bang `fact_request` moi, ma mo rong
       `fact_call` co san (migration 004_fact_call_source_cost + sau do
       006_do_tre_va_ket_cuc them duration_ms/outcome/error_code). Yeu cau goc
       -- co cot trang thai, ghi duoc luot HONG kem token -- da dat
   [x] Loader Gateway -> fact_usage_daily, source='gateway'
       -- XONG 31/08, qua load-the-gateway-ledger-into-the-database
   [x] Doi chieu 26 truong Data Out x 34 cot SpendLogs   -- XONG 27/08
       -> docs/archive/gateway/doi-chieu-data-out-litellm.md
   [x] Mo rong audit_db.py + check_api.py cho nguon gateway
       -- XONG 03-05/09, qua extend-the-checks-to-gateway-data +
       refresh-every-table-the-gateway-touches + stop-treating-a-failed-call-
       as-a-free-call. Moc cuoi: audit_db.py 78 phep / 68 dat / 10 luu y /
       0 hong; check_api.py 31/31
   [ ] DIEN TAP: tat litellm-2, do thoi gian phuc hoi; roi do THOI GIAN LUI
       (tro base_url mot agent ve thang nha cung cap, bam gio)
       -- CHUA THAY BANG CHUNG DA LAM. Day la rui ro so 1 cua tuan nay, xem
       §6③ -- duong lui chua duoc do, "danh sach dep" nhung chua thu that
   [x] Chuyen agent DAU TIEN qua Gateway -- chon agent it luu luong nhat
       -- XONG 31/08, chon dms-feedback. (trên một agent — day dung la
       "AGENT DAU TIEN" theo dung pham vi cua dong nay, KHONG phai ca 8)
```

**Chốt tuần 2 (đến hết 07/09): một nửa.** Đường dữ liệu XONG cả — agent thật vào
`fact_usage_daily` với `source='gateway'`, `audit_db.py` xanh (78/68/10/0). Nhưng
**thời gian lùi CHƯA có con số** — vế diễn tập của mốc này chưa đạt, và đây là việc còn
lại nặng nhất trước khi bước vào cửa sổ đối chiếu 14/09.

### Tuần 3 + 4 — 14/09 → 25/09 · 10 ngày · *cửa sổ đối chiếu, không đụng vào*

```
   14/09  chuyen 7 agent con lai. Ca 8 agent chay qua Gateway tu day.
   moi ngay  doi chieu 4 nguon: gateway / billing / monitoring / app
             ghi lai do lech theo NGAY, khong doi toi cuoi ky moi cong
   song song (khong cham vao cua so tren):
   [ ] Backend: truy van + endpoint moi cho chi tieu tu Gateway
   [ ] Dashboard: ba bieu do chieu nguoi dung, du ca 8 agent
   [ ] Do throughput va do tre TANG THEM do Gateway
   [ ] Tai lieu van hanh: cap/thu hoi khoa, them agent, xu ly su co
```

**Quy tắc của cửa sổ này: không đổi cấu hình Gateway.** Đổi một khoá giữa kỳ là 2 tuần đối
chiếu biến thành hai mẩu 1 tuần, và mức sàn của GĐ7 hỏng. Nếu buộc phải đổi thì **đồng hồ
đếm lại từ đầu** — phải nói ra ngay lúc đổi, không phải lúc viết báo cáo.

### Tuần 5 — 28/09 → 30/09 · 3 ngày · *chốt sổ*

```
   [ ] Bao cao doi chieu 4 nguon, 2 tuan, do lech theo ngay
   [ ] Cat: ngung doi chieu, Gateway thanh duong chinh
   [ ] Ban giao + dao tao van hanh
```

---

## 5. Cắt gì so với Master Plan

Nén 13 tuần không phải bằng cách làm nhanh hơn, mà bằng cách **làm ít hơn**. Đây là danh
sách những gì bỏ. Mỗi dòng cần một cái gật.

| Master Plan | Bản nén | Vì sao chấp nhận được |
|---|---|---|
| 3 môi trường dev / staging / production (GĐ2 d.7) | **1** môi trường chạy thật + môi trường đo đã có | Dựng 3 môi trường trong 5 tuần là tiêu tiền vào hạ tầng chứ không vào số liệu |
| 2 máy server vật lý (GĐ5 d.13) | 1 máy, 2 instance container | Chống được lỗi tiến trình, **không** chống được lỗi máy. Ghi rõ đây là nợ |
| Phương án thay thế Kubernetes k3s (GĐ5 d.13) | Bỏ | Docker Compose đã đủ cho 2 instance |
| Cache trả lời trên Redis (GĐ2 d.8) | Bỏ khỏi phạm vi | Một lần trúng cache ghi `cache_hit=true`, `spend=0` — tổng token qua Gateway không còn bằng tổng token nhà cung cấp tính tiền. Bật nó là tự phá GĐ7 |
| Redis Sentinel / tự chuyển primary | Bỏ | Primary chết thì đổi tay. Có replica giữ bản sao là đủ cho 5 tuần |
| 3 kịch bản sự cố (GĐ7 d.21) | **1** kịch bản: tắt 1 instance | Kịch bản đó đã bao trùm đường lùi quan trọng nhất |
| Chuyển 8 agent theo **đợt** (GĐ8 d.22) | Chuyển **cùng lúc** vào 14/09 | Xem mục 3. Đổi lấy 8 tuần |

---

## 6. Ba thứ có thể làm trượt lịch — và dấu hiệu nhận biết sớm

> **Đính chính 27/08.** Bản đầu của file này xếp "vá bảng giá `gemini-3.6-flash`" là rủi
> ro số một. **Sai, và đã đổi thứ tự.** Lý do ở ② bên dưới. Rủi ro số một thật sự là Ralli.

### ① Ralli: chỗ mù lớn nhất rơi đúng vào chỗ ít đối chứng nhất

Hai chuyện riêng lẻ, cộng lại thành rủi ro lớn nhất của kế hoạch.

**Chuyện thứ nhất — chưa ai biết Ralli gửi gì.** Cả phép đo 26/08 dùng `curl` mô phỏng
theo hiểu biết hiện tại. Nếu Ralli sửa request ở server trước khi gửi, hình dạng header
thật khác cái đã đo, và `end_user` có thể **rỗng cho toàn bộ lưu lượng Ralli**.

**Chuyện thứ hai — Ralli không có nguồn đối chứng thứ ba.** Đo 27/08 trên `token_ledger`:

```
   Tro ly ao Ralli        0 dong monitoring        47.933.778 token nguon 'app'
   Tro Ly Ao Hop Dong     2.304 dong monitoring    62.706.827 token nguon 'app'
```

Số Gateway của Ralli lệch so với `app` thì **không có ý kiến thứ ba để phân xử** —
`billing` chỉ có tổng theo project, không tách được về người. Hợp Đồng thì có `monitoring`
đứng giữa. Chi tiết và hai hệ quả khác: [`do-ban-ghi-litellm-24-08.md`](../archive/gateway/do-ban-ghi-litellm-24-08.md) §10.

**Cách gỡ, làm trong tuần 0–1:** trỏ `base_url` của Ralli vào `http://127.0.0.1:4000` rồi
đọc `proxy_server_request.metadata.headers`. Cái gì đáp xuống chính là cái Ralli thật sự
gửi. Một buổi chiều, không phải một tuần — và nó vừa trả lời chuyện thứ nhất vừa bù lại
nguồn đối chứng đang thiếu.

**Dấu hiệu sớm:** hết 04/09 chưa có quyền đổi `base_url` của Ralli → điều kiện ③ hỏng →
lịch trượt ít nhất 1 tuần.

### ② `dim_model` thiếu `gemini-3.6-flash` — nhỏ hơn tôi tưởng, nhưng vẫn phải làm

Bản đầu viết: *"LiteLLM không tra được đơn giá, `spend` sai cho gần một nửa lưu lượng"*.
Đo lại 27/08 từ chính dòng đã chép ra thì **ngược lại**:

```
   LiteLLM   metadata.model_map_information.model_map_key = "gemini/gemini-3.6-flash"
             input_cost_per_token             7,5e-07
             output_cost_per_token            3,75e-06
             output_cost_per_reasoning_token  3,75e-06
             -> dung ba so nay dung lai duoc spend = 0,00172875 den tung chu so
             -> LiteLLM KHONG co van de gi ve gia
```

`guess_model()` là hàm **của ta** (`db/rules.py:46`), ánh xạ **tên SKU hoá đơn** sang
`dim_model`. Danh sách `MODELS` có 10 model, không có `gemini-3.6-flash`. Nó trả `None`
nghĩa là khi hoá đơn Google bắt đầu có dòng "gemini 3.6 flash", **những dòng đó mất model**
— và Gateway cũng không JOIN được về `model_id`.

Vẫn phải sửa, vì `dim_model` là chỗ ba nguồn gặp nhau. Nhưng đó là **hai dòng trong
`db/rules.py` cộng một dòng `dim_model`**, không phải một việc nghiên cứu đơn giá.
Mức: 🔴 → 🟡.

> Còn một câu chưa trả lời: hôm 26/08 `gemini-2.5-flash` vẫn ra `response_cost` dù log báo
> *"model isn't mapped yet"*. Chưa truy được con số đó ở đâu ra.

### ③ Cửa sổ đối chiếu không còn slack

14/09 → 25/09 là **đúng** 2 tuần, không dư một ngày. Mọi chậm trễ ở tuần 0–2 ăn thẳng vào
cửa sổ này, tức ăn thẳng vào cơ sở chứng minh Gateway không làm lệch số.

**Dấu hiệu sớm:** nếu tới hết 11/09 chưa có **một** agent chạy thật qua Gateway với số vào
được `fact_usage_daily`, thì mốc 30/09 đã trượt — nhận ngay lúc đó, đừng nhận vào 25/09.

---

## 7. Cách biết kế hoạch này đang trượt

Bốn con số, xem hằng ngày, không đợi tới mốc:

```
   1.  So agent da chay that qua Gateway              muc tieu: 1 vao 11/09, 8 vao 14/09
   2.  So dong fact_usage_daily co source='gateway'   phai TANG moi ngay tu 11/09
   3.  Do lech gateway vs billing theo NGAY           ghi tung ngay, khong cong don ky
   4.  audit_db.py                                    phai luon xanh, khong duoc "xanh tru mot phep"
```

Con số 3 là con số quan trọng nhất và cũng là con số dễ tự lừa nhất: cộng dồn cả kỳ thì
một ngày lệch +8% và một ngày lệch −8% triệt tiêu nhau thành "0% — đạt". **Ghi theo ngày.**

---

## 8. Việc còn treo, không nằm trong đường găng nhưng đừng quên

| | Việc | Ghi ở |
|---|---|---|
| 🔴 | `JWT_test_for_header` — token thật, gốc repo, ngoài `.gitignore` | nhật ký 26/08 §15 |
| 🟡 | `gemini-2.5-flash-image` bị gộp vào `gemini-2.5-flash`, mất nhánh ảnh | task 6.4(b) |
| 🟡 | `gemini-2.0-flash` (9,5% lưu lượng cũ) đã rút khỏi API | task 6.4(c) |
| 🟡 | Sheet `Data Out` §A5: đổi "Nguồn" thành "dẫn xuất" | task 6.2 |
| ✅ | Kế hoạch đóng gói Docker viết 18/08 dựa vào file đã xoá 24/08 — **đã đóng 06/09**: dashboard đã lên server thật, plan đã hoàn thành mục tiêu, không lỗi thời | `close-the-known-gateway-loose-ends/tasks.md` §3 |
| ✅ | Thư mục sao lưu đặt tên `2026-26-08`, phải là `2026-08-26` — **đã đổi tên** | `close-the-known-gateway-loose-ends/tasks.md` §1 |

---

## 9. Đối chiếu nhanh với bản gốc

| | Master Plan | Bản nén |
|---|---|---|
| GĐ1 Mục tiêu & phạm vi | T8w2–w4 | **xong rồi** |
| GĐ2 Hạ tầng | T8w3 → T9w2 | T8w4 → T9w1 |
| GĐ3 Xác thực | T9w1 → w3 | T9w1 |
| GĐ4 Ghi nhận & lưu trữ | T9w1 → w4 | T9w2 |
| GĐ5 Cân bằng tải & fallback | T9w1 → T10w2 | T9w2, **thu hẹp** (1 máy, 1 kịch bản) |
| GĐ6 Tích hợp FE/BE/DB | T8w3 → T10w3 | T9w2 → w4, chạy song song cửa sổ đối chiếu |
| GĐ7 Kiểm thử & nghiệm thu | T9w4 → T11w2 | T9w3 → w4, **giữ nguyên 2 tuần** |
| GĐ8 Go-Live | T11w3 → T12w4 | T9w3 (chuyển) + T9w5 (bàn giao) |
| **Về đích** | 31/12/2026 | **30/09/2026** |
