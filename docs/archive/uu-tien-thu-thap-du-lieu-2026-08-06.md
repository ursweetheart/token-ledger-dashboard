# Thu thập dữ liệu Monitoring — nhật ký & việc còn lại (06/08/2026)

> **Trạng thái:** Bước 1 (kéo dữ liệu) **ĐÃ XONG** cho cả 7 project. Bước 2 (gộp về một
> format) chưa bắt đầu — bàn sau khi đã cầm dữ liệu.
>
> Tài liệu này ban đầu viết để chạy đua với giả định "Monitoring chỉ giữ 6 tuần".
> **Giả định đó đã bị bác bỏ ngay trong ngày** (§2). Phần lớn nội dung được viết lại theo
> số liệu thật thay vì ước lượng.

---

## 1. Chiến lược & quy ước đã chốt

```
   BƯỚC 1  KÉO ĐỦ, KHÔNG BIẾN ĐỔI                    ✅ XONG 06/08
           scripts/pull_monitoring.py — 7 project, cửa sổ 240–400 ngày
           mọi nhãn giữ nguyên, ghi vào data/raw/monitoring/2026-08-06/

   BƯỚC 2  TẬP HỢP VỀ MỘT FORMAT                     ⏸ BÀN SAU
           chốt sau khi đã cầm dữ liệu trong tay, không thiết kế trước
```

**Phân vai nguồn — chốt bằng đối chiếu số thật:**

| Cần gì | Nguồn | Vì sao không dùng nguồn kia |
|---|---|---|
| Token + chi phí | **Billing** | Monitoring đếm token lệch tới 4,2× ở một số model (§4 bẫy 4) |
| Request · mã lỗi · độ trễ p95 | **Monitoring** | Billing không có |
| Danh tính user · lịch sử chat | **CSDL agent** (chỉ HĐ + Ralli) | Google vĩnh viễn không biết ai dùng |

**Quy ước token:** `cached` **cộng chung vào input**. Không phải quy ước tự đặt —
**ba nguồn độc lập đều đếm y hệt**:

| Nguồn | Bằng chứng |
|---|---|
| Cloud Monitoring | `input_token_count` khớp `billing input + cached`, không khớp `input` đơn thuần (§4 bẫy 4) |
| CSDL Ralli/CTDA | phải trừ `cached` khỏi `prompt_tokens` mới ra đúng `input_cost` (§3) |
| *(Billing là ngoại lệ)* | tách thành **2 SKU riêng** ⇒ khi nạp phải cộng: `input = SKU_input + SKU_cached` |

**Quy ước "1 user":** áp cho 6 project không có CSDL riêng (tất cả trừ Hợp Đồng và Ralli).
```
   user := tên project
   ⇒ số của project CHÍNH LÀ số của user, không cần phân bổ
   ⇒ quota của project = quota của user, không tính riêng
   ⇒ khoá tự nhiên là (project, thời gian, model) — không cần cột user
```
**Vẫn không có, kể cả với giả định 1 user:** số cuộc chat (`c`).

---

## 2. ⭐ Mốc lưu giữ thật: **196 ngày**, không phải 6 tuần

Đây là phát hiện quan trọng nhất của buổi 06/08, và nó đảo ngược toàn bộ mức khẩn cấp
của tài liệu này.

**Cách chứng minh (3 bước, mỗi bước loại một cách giải thích khác):**

```
 ① Kéo 60 ngày   → cả 3 project lớn đều bắt đầu đúng 07/06
                    = mép cửa sổ của TA, chưa chạm giới hạn của Google
 ② Kéo 240 ngày  → dừng ở 22/01, KHÔNG dừng ở mép cửa sổ (~10/12/2025)
                    hai project dừng đúng cùng một ngày ⇒ dấu hiệu của tường
 ③ Kéo 400 ngày  → kết quả y HỆT bước ②: 8.291 dòng, 25.776 request, vẫn 22/01
                    ⇒ tường xác nhận
```

**Loại nốt khả năng "22/01 là ngày bắt đầu chạy":** billing của Sale Agent cho thấy nó chạy
**liên tục 21 ngày** từ 01/01 đến 21/01 (~17 triệu token, ~$3,5), không nghỉ ngày nào —
mà Monitoring không có một dòng nào trong khoảng đó.

```
   06/08/2026 − 22/01/2026 = 196 ngày ≈ 28 tuần ≈ 6,5 tháng
```

### Thiệt hại thật so với ước lượng cũ

| Project | Ngày chạy (billing) | Có monitoring | **Mất** | Doc cũ ước |
|---|---:|---:|---:|---:|
| AI Sale Agent | 214 | 193 | **21** | ~~173~~ |
| Contact Center | 189 | 181 | **8** | ~~149~~ |
| Multimodal Invoice | 88 | 86 | **2** | ~~61~~ |
| CRM Feedback | 29 | 28 | 1\* | ~~0~~ |
| Feedback DMS | 11 | 10 | 1\* | ~~0~~ |
| Contract HĐ | 9 | 9 | 0 | 0 |
| Tools quizz | 4 | 4 | 0 | ~~1~~ |
| **Tổng** | **544** | **511** | **33 (6%)** | ~~384~~ |

\* *Lệch 1 ngày ở CRM và DMS là hiệu ứng biên múi giờ (billing tính theo ngày, monitoring
theo giờ UTC), không phải mất dữ liệu thật.*

**Bài học:** việc này chưa bao giờ gấp như đã tưởng. Nhưng nếu giả định 6 tuần đúng thì bây
giờ đã mất thật — nên chi phí của việc kiểm sớm vẫn thấp hơn rủi ro.

---

## 3. ⛔ Ralli không lấy được gì từ Google Cloud

**Lý do:** phần mềm Ralli không gọi Gemini API qua project `tla-ralli`. Xác nhận bằng số:

```
   Ralli/CTDA tự khai (gemini-2.5-flash-lite)      47.204.454 token
   Cùng model, trong billing CẢ 7 project               363.882 token
                                                   ──────────────────
                                                   lệch 130 lần
```

### Hệ quả

1. **Bác bỏ kết luận "8 project ↔ 8 agent khớp 1-1"** của `docs/explore-2026-08-04` §2.2
   (đang được đánh dấu ✅ *đã chứng minh*).
2. **Mất phép đối chiếu chi phí của Ralli** — không có số của Google để so.
3. **Ẩn số:** Ralli gọi Gemini bằng key của ai, tính tiền vào ví nào? Nếu là ví khác thì công
   ty đang trả tiền ở một chỗ **không ai giám sát**.

### Nhưng bảng giá của Ralli đã kiểm chứng được, và nó ĐÚNG

Không so được *số token*, nhưng so được *bảng giá*. Suy ngược từ chính số của CTDA:

```
   CTDA tự khai                            Suy ngược
   input_cost   = 3.8045973000000077   ←  (40.634.413 − 2.588.440) × 0,100/1M = 3,8045973  ✅
   output_cost  = 1.592640400000009    ←    3.981.601             × 0,400/1M = 1,5926404  ✅
   cached_cost  = 0.025884399999999957 ←    2.588.440             × 0,010/1M = 0,0258844  ✅
```

Và **0,100 / 0,400 / 0,010 đúng bằng giá suy từ billing Google** cho gemini-2.5-flash-lite (§7).

⇒ Rủi ro còn lại của Ralli thu hẹp từ *"giá có đúng không"* (đã trả lời: đúng) xuống còn
*"phần mềm có ghi log đủ mọi lượt gọi không"* — chỉ đơn vị làm phần mềm trả lời được.

---

## 4. ⚠️ Năm cái bẫy trong dữ liệu Monitoring

Cả năm đều đã được xử lý trong `scripts/check_monitoring.py`. Ghi lại để hiểu **vì sao** bộ
lọc phải làm như thế, và để người sau không gỡ nhầm.

**Bẫy 1 — quota đếm ĐÚP đúng 2 lần.** Hai hạn mức cùng đếm một lượt gọi:
```
GenerateRequestsPerDayPerProjectPerModel-PaidTier3      ┐ hai dòng
GenerateRequestsPerMinutePerProjectPerModel-PaidTier3   ┘ giá trị BẰNG NHAU
```
Thấy rõ ở mọi project, không sai một số: `684→342 · 1.296→648 · 774→387 · 13.096→6.548 ·
31.956→15.977 · 8.554→4.277 · 38→19`. ⇒ Lọc đúng 1 `limit_name`.

**Bẫy 2 — `api_request_count` / `api_request_latencies` đếm MỌI Google API.**
Trên `pro-tuner-454203-v3`: `233.787 → 4.722` sau khi lọc. **97,4% là Google Drive**, không
liên quan gì tới Gemini. ⇒ Bắt buộc lọc `res_service = generativelanguage.googleapis.com`.

**Bẫy 3 — hai nguồn đếm request lệch nhau.** Hoá ra nhỏ hơn lo ngại, khớp ~99%:

| Project | quota | api | lệch |
|---|---:|---:|---:|
| feedback-dms | 387 | 387 | 0 |
| multimodal-invoice | 7.995 | 7.951 | 44 |
| ai-chatbot-contract | 342 | 345 | 3 |
| tranquil-post | 25.776 | 22.586 | 3.190 |

⇒ Vẫn phải chốt **một** định nghĩa "request" và ghi lên UI.
**Hệ quả không gỡ được:** `model` và `response_code` ở hai phép đo khác họ ⇒ **không thể**
ra chỉ tiêu "tỷ lệ lỗi theo từng model". Đừng hứa cột đó.

**Bẫy 4 — token trong Monitoring KHÔNG khớp billing.** `pro-tuner`, 20/06 → 04/08:
```
model                     MONITORING   billing input   billing cached   input+cached
gemini-3-flash            71.975.957      27.954.994       42.194.315     70.149.309  ✅ 97,4%
gemini-3.1-flash-lite          9.059           9.059                0          9.059  ✅ 100%
gemini-2.5-flash             207.548         881.704                0        881.704  ❌ lệch 4,2×
```
Phép đo là `..._paid_tier_3_...` — chỉ đếm lưu lượng rơi vào hạn mức **Tier 3**.
⇒ **Token luôn lấy từ billing.**

**Bẫy 5 — mỗi quota có CẶP `/usage` và `/limit`.** Phát hiện ngay ở lần kéo thật đầu tiên:
```
   generate_content_paid_tier_3_requests          ← đã dùng bao nhiêu
   generate_content_paid_tier_3_requests_limit    ← HẠN MỨC (9,22×10¹⁸ nếu không giới hạn)
```
Gộp nhầm hai cái ⇒ số request thành **10²⁰**. ⇒ Loại mọi dòng `_limit` khỏi phép cộng.

> 💡 Nhưng **đừng vứt** `_limit` — nó chính là mẫu số cho chỉ tiêu *"đã dùng bao nhiêu %
> hạn mức"*, thứ giao diện TLA HĐ đang hiển thị (1,7% hạn mức token/tháng).

---

## 5. Kết quả kéo — 06/08/2026

`data/raw/monitoring/2026-08-06/` · 7 project × (1 file `.csv` + 1 file `.descriptors.json`)

`request` dưới đây là **định nghĩa đã chốt** (§5b-①): `GenerateContent` + `StreamGenerateContent`.

| Project | request | tổng gọi | lỗi | tỷ lệ lỗi | p95 | p99 | key | giờ | model | khoảng |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| tranquil-post (Sale Agent) | 22.580 | 22.586 | 53 | 0,23% | 154,35 | 479,16 | **3** | 882 | 4 | 22/01 → 06/08 |
| pro-tuner (Contact Center) | 8.525 | 9.509 | 40 | 0,42% | 140,93 | 242,93 | **4** | 557 | 5 | 22/01 → 06/08 |
| multimodal-invoice | 7.925 | 7.951 | 10 | 0,13% | 87,24 | 222,80 | 1 | 203 | 2 | 26/01 → 25/07 |
| crm-500509 | 648 | 657 | 0 | 0,00% | 64,59 | 66,61 | 1 | 35 | 1 | 07/07 → 05/08 |
| feedback-dms-tiep-thi | 387 | 387 | 1 | 0,26% | 65,77 | 112,74 | 1 | 15 | 1 | 07/07 → 04/08 |
| ai-chatbot-contract | 342 | 345 | 0 | 0,00% | 64,59 | 475,13 | 1 | 18 | 2 | 20/06 → 04/08 |
| tools-quizz | 19 | 21 | 5 | **23,81%** | 31,88 | 33,22 | 2 | 7 | 2 | 17/06 → 01/07 |

**Contact Center chạy 80% bằng streaming:** `StreamGenerateContent` 6.822 vs `GenerateContent`
1.703. Dashboard hiện chưa phân biệt hai kiểu gọi này.

### Phân loại lỗi — đủ để lấp 3 ô `[MỚI]` của `index.html`

| Nhóm | Mã | Tổng | Ai |
|---|---|---:|---|
| **Lỗi Client** (`:1072`) | 400, 404 | 63 | tranquil 32 · pro-tuner 26 · tools-quizz 5 |
| **Lỗi Provider** (`:1077`) | 500, 503 | 32 | tranquil 21 · multimodal 10 · pro-tuner 1 |
| **Giới hạn tốc độ** (`:1082`) | 429 | **0** | — chưa project nào từng bị chặn |
| *Người dùng huỷ* | 499 | 14 | pro-tuner 13 · dms 1 |

⚠️ **`499` không phải lỗi hệ thống** — client đóng kết nối, tức người dùng huỷ giữa chừng.
Xếp nó vào "Lỗi Client" là đổ oan cho hệ thống. Phải tách riêng.

### ⚠️ Cách đọc p95 / p99

```
   ai-chatbot-contract   p95 = 64,59   p99 = 475,13   (345 request)
   crm-500509            p95 = 64,59   p99 =  66,61   (657 request)
                               ↑ hai project khác nhau, p95 GIỐNG HỆT
```
`request_latencies` là **distribution**; Google ước lượng phân vị bằng nội suy trên **ô luỹ
thừa**, nên giá trị rơi vào biên ô và hai project khác nhau vẫn có thể ra cùng số.
⇒ **Đọc p95/p99 như "khoảng", không phải giây chính xác.** Và p99 của project chỉ có 345
request thì gần như vô nghĩa — 475 giây nhiều khả năng chỉ là ô cao nhất từng chạm tới.

`data/raw/monitoring-probe/2026-08-06/` là phép thử tường lưu giữ (§2 bước ③), **không phải
dữ liệu chính thức** — xoá được sau khi đọc xong tài liệu này.

### Bốn điều bảng này nói ra

1. **`tools-quizz` lỗi 23,81%** (5/21) — cao gấp ~90 lần mọi project khác, và **cả 5 lỗi đều
   là `404` trên `GenerateContent`** ⇒ nó gọi một **model không tồn tại**. Cộng với việc có lưu
   lượng từ 17/06 mà billing chỉ ghi nhận từ 24/06 (những lần gọi đầu lỗi hết nên không phát
   sinh tiền), đây gần như chắc chắn là **thử nghiệm cấu hình sai rồi bỏ**, không phải agent
   đang vận hành.
   *Cùng bệnh:* `pro-tuner` có **19 lỗi `404` trên `EmbedContent`** — model list cho thấy nó
   dùng cả `gemini-embedding-1.0` lẫn `gemini-embedding-2`, nhiều khả năng một cái đã bị gỡ.
2. **Contact Center đã ổn định dần.** Tỷ lệ lỗi 60 ngày gần đây là 0,04%; tính cả từ tháng 1
   là 0,42% ⇒ giai đoạn đầu năm lỗi nhiều gấp ~10 lần. Dashboard hiện không kể được câu
   chuyện này.
3. **~~`embed` của Contact Center không cộng khớp~~ — ĐÃ GIẢI, xem §5b.** Quota đếm *đơn vị
   hạn mức*, `api_request_count` đếm *lượt gọi HTTP*. `BatchEmbedContents` gộp ~68 đoạn văn
   bản trong một lượt gọi: `(8.332 − 804) ÷ 111 ≈ 68`. Không cái nào sai.
4. **`p95 max` tới 140–154 giây** trong khi trung bình theo giờ chỉ ~1,5 s ⇒ dùng **trung vị
   hoặc cắt đuôi** cho chỉ tiêu "thời gian phản hồi", đừng lấy max.

---

## 5b. Hai nhãn ẩn trong `resource_labels_json`

Cột này được giữ lại "cho chắc" khi kéo. Hoá ra nó chứa hai nhãn **không có trong bất kỳ cột
phẳng nào, và cũng không có trong 152 descriptor** — vì chúng là nhãn của *tài nguyên*, không
phải của *phép đo*. File `.descriptors.json` chỉ liệt kê nhãn phép đo.

| Họ phép đo | Loại tài nguyên | Nhãn tài nguyên |
|---|---|---|
| 146 phép đo `generativelanguage` | `…/Location` | chỉ `location`, `project_id` — nghèo |
| 6 phép đo `serviceruntime` | `consumed_api` | `service`, **`method`**, **`credential_id`**, `version`, `location`, `project_id` |

### ① `method` — chốt được định nghĩa "request"

```
   GenerativeService.GenerateContent          33.565  ┐
   GenerativeService.StreamGenerateContent     6.859  ┘ 40.424 — NGƯỜI DÙNG HỎI AGENT
   GenerativeService.EmbedContent                804  ┐
   GenerativeService.BatchEmbedContents          111  ┘    915 — máy tự index tài liệu
   ModelService.ListModels · FileService.CreateFile
   DatasetService.* · PresetService.*                      115 — việc vặt hệ thống
```

**✅ QUYẾT ĐỊNH:** chỉ tiêu "request" trên dashboard =
`api_request_count`, lọc `res_service = generativelanguage`, chỉ lấy
**`GenerateContent` + `StreamGenerateContent`**. Các phép đo quota **không** dùng cho việc này
— chúng đếm đơn vị hạn mức, để dành cho chỉ tiêu "đã dùng bao nhiêu % hạn mức".

*Ghi chú:* 17% lưu lượng là `StreamGenerateContent` — dashboard hiện chưa phân biệt.

### ② `credential_id` — Google BIẾT lời gọi đến từ API key nào

Sửa lại kết luận *"Google không bao giờ biết ai đang dùng"* (doc 04/08 §6.3): đúng ở mức **con
người**, sai ở mức **khoá**.

```
  ai-chatbot-contract    1 khoá        345
  crm-500509             1 khoá        657
  feedback-dms           1 khoá        387
  multimodal-invoice     1 khoá      7.951
  pro-tuner              1 khoá chính 9.477  (+3 khoá lẻ 18/6/6 — có vẻ gọi thử)
  tools-quizz            1 khoá         20   (+1 khoá lẻ)
  ─────────────────────────────────────────────────────────
  tranquil-post          HAI khoá   14.275 / 8.288   ⚠️ 63% / 37%
```

**Ý nghĩa với quy ước `user := tên project`:**
- **5/7 project đúng là một điểm tích hợp duy nhất** ⇒ giả định "1 user" giờ có bằng chứng
- **Sale Agent thì KHÔNG** — hai khoá chạy song song, lưu lượng đáng kể cả hai. Gọi nó "1 user"
  là gộp hai thứ khác nhau. Tra tên khoá trong Console (APIs & Services → Credentials) để biết
  chúng là gì

Giới hạn phải nói rõ: `credential_id` là **khoá**, không phải **người**. Một khoá vẫn có thể
dùng chung cho cả phòng ban ⇒ không thay được CSDL agent. Nhưng nó là chiều **mịn hơn project**,
mà trước giờ ta tưởng không tồn tại.

### ③ Toàn bộ nhãn tồn tại trong 152 descriptor — chỉ có 9

```
   model (146) · limit_name (145) · method (41, loại metric, phần lớn rỗng)
   output_modality · thinking_enabled · protocol
   response_code · response_code_class · grpc_status_code
```

Ngoài 9 nhãn này, Monitoring **không biết gì thêm**. Đáng chú ý: **không có phép đo nào tên
chứa "cache"** ⇒ Monitoring về nguyên tắc không tách được token cached, trong khi cached chiếm
48–66% token vào của hai project lớn nhất. Đây là lý do thứ hai (chắc chắn hơn lý do lệch
4,2×) để **token luôn lấy từ billing**.

---

## 5c. Ba nguồn lấp được gì — đối chiếu với 13 trường dashboard cần

| Trường | 6 project 1 user | HĐ + Ralli | Nguồn |
|---|---|---|---|
| agent · phòng ban · model | tên project · khai báo tĩnh · billing | có sẵn | billing + khai báo |
| số user | = 1 | `users.csv` | — |
| token vào/ra/cached | billing | `db-token_usage-raw` | **billing** |
| tiền | billing (tiền thật) | tự tính — đã kiểm, đúng | **billing** |
| **request** | ✅ | ✅ | **Monitoring** — billing KHÔNG có cột lượt gọi |
| **tỷ lệ lỗi + mã lỗi** | ✅ | ✅ | **Monitoring** — app-DB cũng không có |
| **độ trễ** | ✅ | ✅ | **Monitoring** — app-DB cũng không có |
| số cuộc chat | ⛔ **BỎ** | có sẵn | *(xem dưới)* |

**✅ QUYẾT ĐỊNH (06/08):** **bỏ chỉ tiêu "số cuộc chat"**, tạm thời không đưa vào dashboard.
Lý do vẫn đúng về nghiệp vụ: Multimodal Invoice hay CRM Feedback là agent phân loại chạy nền,
chúng **không có "cuộc hội thoại"** để mà đếm. Ép số vào ô đó là quay lại đúng thói quen cũ.

**Đã soi hết cột của 8 file CTDA + 9 file TLA HĐ: không file nào có trường lỗi hay độ trễ.**
Chúng là log *nghiệp vụ* (ai gọi, tiêu bao nhiêu token), không phải log *kỹ thuật*.
⇒ Monitoring không thừa: nó là nguồn **duy nhất** cho 3 trong 13 trường, và gần trọn một tab
của `index.html` (`:1052` — "Tỷ lệ request thành công · nguồn gốc lỗi · thời gian chờ kết quả")
phụ thuộc hoàn toàn vào nó.

Mã lỗi thật đã đủ để tách 3 ô `[MỚI]`: `4xx = lỗi Client · 5xx = lỗi Provider · 429 = giới hạn
tốc độ`. Dữ liệu có `200 · 302 · 400 · 403 · 404 · 503` — **chưa gặp 429 lần nào**, bản thân
đó là một thông tin tốt.

---

## 6. Việc còn lại

### 6.1. Hỏi người khác (lead-time dài nhất)

| # | Câu hỏi | Gửi ai | ☐ |
|---|---|---|:-:|
| 1 | **Ralli gọi Gemini bằng key của ai, tính tiền vào ví nào?** | `letrunghieu4799@gmail.com` | ☐ |
| 2 | **Phần mềm Ralli/HĐ có ghi log ĐỦ mọi lượt gọi không?** | nt — sau §3, đây là rủi ro duy nhất còn lại của số liệu Ralli | ☐ |
| 3 | **`tools-quizz` còn dùng không, hay là thử nghiệm bỏ dở?** | quyết định nó có nằm trong dashboard hay không (§5-1) | ☐ |

### 6.2. Tự làm được

| # | Việc | Chi tiết | ☐ |
|---|---|---|:-:|
| ~~1~~ | ~~Chốt định nghĩa "request"~~ | ✅ **ĐÃ CHỐT** — `api_request_count` + `method`, xem §5b-① | ✅ |
| ~~2~~ | ~~Tách `method` và `credential_id` thành cột riêng~~ | ✅ **XONG** — cột `res_method`, `res_credential_id` | ✅ |
| ~~3~~ | ~~Kéo thêm `p99`~~ | ✅ **XONG** — cột `aligner` ghi rõ `ALIGN_PERCENTILE_95` / `_99` | ✅ |
| 3' | **Tách `499` khỏi nhóm "Lỗi Client"** | client huỷ, không phải lỗi hệ thống (§5) | ☐ |
| 4 | **Gộp về một format** | bước 2 — bàn sau khi đọc kỹ dữ liệu vừa kéo | ☐ |
| 5 | Kéo lại billing với khoảng **rộng hơn 01/01/2026** | Sale Agent có dòng ngay 01/01 ⇒ lịch sử có thể bị cắt cụt ở đầu | ☐ |
| 6 | Xoá `data/raw/monitoring-probe/` | phép thử đã xong nhiệm vụ | ☐ |
| 7 | **Tra tên 2 API key của Sale Agent** | Console → APIs & Services → Credentials. Quyết định nó là "1 user" hay "2 user" (§5b-②) | ☐ |

### 6.3. Sửa những chỗ đã biết là sai trong dashboard

| # | Việc | Chi tiết | ☐ |
|---|---|---|:-:|
| 1 | **`cost()` đang bỏ qua cached** | `app.js:548` = `ti×i + to×o`. Với quy ước "cached ⊂ input" thì công thức này tính cached ở **giá input đầy đủ**, trong khi giá thật chỉ bằng **1/10**. Contact Center: báo cáo phồng ~+69% | ☐ |
| 2 | **Nạp lại bảng giá — dùng số suy từ billing** | Panel ⚙ đã cho tự cấu hình giá (`app.js:3018`). Không cần đoán — xem §7 | ☐ |
| 3 | **Đưa `tools-quizz` vào diện giám sát** | Gỡ khỏi `EXCLUDED_AGENTS` (`app.js:45`) + thêm dòng ngân sách (`app.js:15`). Nhưng chờ câu trả lời §6.1-3 trước | ☐ |
| 4 | **Danh sách agent lấy từ danh sách project** | `allAgents()` (`app.js:762`) dựng từ Excel ⇒ Multimodal Invoice biến mất dù nó chạy **86 ngày, 7.995 request, $17,38** | ☐ |
| 5 | **Truy dữ liệu tháng 6 của DMS Tiếp Thị** | Billing: DMS chỉ có usage **06/07 → 31/07**, tổng đúng $6,16. Dashboard gán cho nó dữ liệu từ 01/06 ⇒ mọi so sánh "kỳ này vs kỳ trước" đang sai nền | ☐ |
| 6 | **Sửa hằng số error rate** | `app.js` để `er: 0.0034` cho mọi agent. Số đo thật rất khác nhau: 0,00% (CRM, HĐ) · 0,13% · 0,23% · 0,42% · **23,81%** (tools-quizz) | ☐ |
| 7 | **Chỉ tiêu độ trễ dùng trung vị, không dùng max** | §5-4 | ☐ |

### 6.4. Chống lặp lại công sức

| # | Việc | Trạng thái |
|---|---|:-:|
| 1 | Script kéo + lọc lưu trong `scripts/` | ✅ `pull_monitoring.py` · `check_monitoring.py` |
| 2 | Ghi **định nghĩa "request"** đã chọn vào `design.md` khi làm backend | ☐ |
| 3 | Chốt quy ước **`actor_type`** cho project 1-user | ☐ — Contact Center là "1 user" nhưng 158 triệu token; lọt vào KPI "chi phí / người dùng" chung với user thật của Ralli là méo. CSDL CTDA đã có sẵn trường `actor_type`, mượn đúng quy ước đó |

---

## 7. Bảng giá suy từ billing (USD / 1 triệu token)

Lấy `cost ÷ amount` từng SKU. Mọi giá trị rơi đúng số tròn ⇒ phép suy chính xác.

| Model | Vào | Ra | Cached | `basePricing` (`app.js:345`) |
|---|---:|---:|---:|---|
| Gemini 2.5 Flash | 0,300 | 2,500 | 0,030 | ✅ đúng |
| Gemini 3 Flash | 0,500 | 3,000 | 0,050 | ✅ đúng |
| Gemini 3.1 Flash Lite | 0,250 | 1,500 | — | ✅ đúng |
| **Gemini 2.5 Pro** | 1,250 | **10,000** | 0,125 | ❌ đang để **3,75** — thiếu 2,7× |
| **Gemini 3.5 Flash** | 1,500 | 9,000 | — | ❌ đang để **0 / 0** |
| **Gemini 3 Pro** | 2,000 | 12,000 | 0,200 | ❌ chưa có |
| **Gemini 2.0 Flash** | 0,100 | 0,400 | — | ❌ chưa có |
| **Gemini 2.5 Flash Lite** | 0,100 | 0,400 | 0,010 | ❌ chưa có |
| **gemini-embedding-001** | 0,150 | — | — | ❌ chưa có |
| **gemini-embedding-2** | 0,200 | — | — | ❌ chưa có |

**Quy luật rút ra:**
- `cached = input ÷ 10`, đúng với **mọi** model (0,300→0,030 · 0,500→0,050 · 1,250→0,125 · 2,000→0,200)
- **Đã kiểm chéo độc lập:** dòng Gemini 2.5 Flash Lite (0,100 / 0,400 / 0,010) trùng khít với bảng
  giá phần mềm Ralli/CTDA đang dùng, khớp tới từng chữ số thập phân (§3) ⇒ cách suy giá từ
  `cost ÷ amount` là đáng tin
- **`thinking` KHÔNG phải chiều giá** — SKU "non-thinking" cùng giá với thường (2,500 = 2,500;
  0,400 = 0,400). Nó chỉ là nhãn thống kê ⇒ bảng giá cần **4 chiều**, không phải 5
- **Modality chỉ audio mới lệch:** 2.5 Flash text 0,300 vs **audio 1,000**; 2.0 Flash 0,100 vs
  **audio 0,700**. Image ≈ text (0,299 vs 0,300) ⇒ bỏ qua được.
  Xử lý gọn: thêm dòng model `"Gemini 2.5 Flash (audio)"` ngay trong panel ⚙, không sửa cấu trúc

> ⏸ **Đang chờ xác nhận:** cách xử lý cost tổng thể (tự tính vs lấy thẳng từ billing).

---

## 8. Cách chạy lại

```bash
# Kéo (chỉ GET, không ghi gì phía Google). Mặc định 7 project, cửa sổ 60 ngày.
python scripts/pull_monitoring.py --days 240

# Kiểm ngay sau khi kéo — tự tìm thư mục mới nhất
python scripts/check_monitoring.py

# Kiểm một file cụ thể (đọc được cả định dạng dump cũ 05/08)
python scripts/check_monitoring.py --file data/monitoring/01-timeseries-hourly.csv
```

Điều kiện: đã cài gcloud và `gcloud auth login` bằng tài khoản có `Monitoring Viewer`
(`tranxuantuan1522005@gmail.com` đủ quyền trên cả 7 project).

**Bảng "TRƯỚC KHI LỌC → SAU KHI LỌC" của `check_monitoring.py` là thứ phải nhìn đầu tiên
sau mỗi lần kéo.** Chênh lệch càng lớn nghĩa là bẫy càng nguy hiểm nếu quên lọc — và nó
chính là cách bẫy 5 bị phát hiện ngay lần kéo thật đầu tiên.

---

*Số liệu: `data/raw/monitoring/2026-08-06/` (7 project, kéo 06/08) ·
`data/billing/billing_gop_tru_CTDA.csv` (7 project, 01/01→04/08/2026).
Bối cảnh nền: `docs/explore-2026-08-04-nguon-du-lieu-gcp.md` — lưu ý doc đó vẫn ghi
"Multimodal Invoice không có dữ liệu", "bảng giá {vào, ra} là đủ" và "8 project ↔ 8 agent
khớp 1-1"; cả ba đã bị bác bỏ.*
