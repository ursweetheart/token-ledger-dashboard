# Khám phá 04/08/2026 — Nguồn dữ liệu GCP cho Token Ledger

> **Mục đích tài liệu:** ghi lại toàn bộ những gì đã xác minh được trong buổi chiều 04/08/2026
> về hạ tầng Google Cloud của 8 AI agent, để lần sau đọc lại không phải dò lại từ đầu.
>
> **Cách đọc:** Phần 1 là tóm tắt. Phần 2–7 là chi tiết kèm bằng chứng. Phần 8 là việc cần làm.
> Phần 9 là phụ lục dữ liệu thô (ID, email, timeline) — tra khi cần.
>
> **Quy ước độ tin cậy:**
> ✅ **Đã chứng minh** (có bằng chứng trực tiếp) · 🟡 **Nhiều khả năng** (suy luận có căn cứ) · ❓ **Chưa biết**

---

## 1. Tóm tắt — đọc phần này là đủ

### 1.1. Ba điều quan trọng nhất tìm ra hôm nay

| # | Phát hiện | Ý nghĩa |
|---|---|---|
| 1 | **"GMSSub" = Gimasys** — công ty mua Google Cloud qua đại lý Gimasys | Người bật được billing export là **Gimasys**, không phải người trong công ty |
| 2 | **Phần mềm agent KHÔNG chạy trên Google Cloud** | Mọi hướng lấy dữ liệu qua Cloud Logging đều **đóng**. Google vĩnh viễn không biết ai đang dùng agent |
| 3 | **Chi phí lệch 2,9 lần** giữa dashboard ($17,67) và Google ($6,16) | Phép đối chiếu đầu tiên trong lịch sử dự án, và nó **trúng ngay** |

### 1.2. Bức tranh ba nguồn dữ liệu

Dashboard cần 3 loại dữ liệu, và mỗi loại nằm ở một nơi khác nhau. **Không nguồn nào thay thế được nguồn nào.**

```
 ┌──────────────────┬──────────────────┬────────────────────────┐
 │ ① GOOGLE BILLING │ ② CLOUD MONITOR  │ ③ CSDL PHẦN MỀM AGENT  │
 ├──────────────────┼──────────────────┼────────────────────────┤
 │ • Tiền thật      │ • Số lượt gọi    │ • Danh tính user  ⭐   │
 │ • Token in/out   │ • Mã lỗi thật    │ • Lịch sử chat         │
 │ • Theo model     │ • Độ trễ thật    │ • Cây phòng ban        │
 │ • Theo agent     │ • Quota          │ • Phân quyền           │
 ├──────────────────┼──────────────────┼────────────────────────┤
 │ Δt: ~giờ/ngày    │ Δt: ~1 PHÚT      │ Δt: từng lượt chat     │
 ├──────────────────┼──────────────────┼────────────────────────┤
 │ ⛔ CHỜ QUYỀN     │ ✅ ĐANG CÓ QUYỀN │ 🟡 CÓ TÀI KHOẢN ADMIN  │
 │    (Gimasys bật) │    CHƯA DÙNG     │    chưa khảo sát       │
 ├──────────────────┼──────────────────┼────────────────────────┤
 │ ❌ không biết ai │ ❌ không biết ai │ ❌ không biết tiền     │
 └──────────────────┴──────────────────┴────────────────────────┘
```

**Điểm mấu chốt:** nguồn ③ là nguồn **duy nhất** biết người dùng là ai. Google về nguyên tắc
không bao giờ biết, vì phần mềm gọi API bằng một API key chung cho cả phòng ban.

### 1.3. Ba việc cần làm ngay

1. **Nhắn Gimasys** (`tdbao@gimasys.com`) xin bật billing export → xem [§8.1](#81-hai-tin-nhắn-gửi-ngay)
2. **Nhắn `letrunghieu4799@gmail.com`** hỏi phần mềm agent có lưu token không → xem [§8.1](#81-hai-tin-nhắn-gửi-ngay)
3. **Đối chiếu tháng 7** cho 1 project để làm rõ độ lệch chi phí → xem [§7](#7-️-phát-hiện-độ-lệch-chi-phí-29-lần)

---

## 2. Bản đồ tổ chức Google Cloud

### 2.1. Cấu trúc tổng thể ✅

```
   GIMASYS  (đại lý Google Cloud)
      │  ví mẹ
      ▼
   ┌─────────────────────────────────────────────────┐
   │  VÍ TIỀN CÔNG TY (ví con / subaccount)          │
   │  Tên: rangdong.com.vn - GMSSub                  │
   │  ID:  011F53-FB4D9A-9E5452                      │
   │  Enabled Google service: Google Cloud Platform  │
   └────────────────────┬────────────────────────────┘
                        │  cả 8 project chung 1 ví
   ┌────────────────────┼────────────────────┬─────────────┐
   ▼                    ▼                    ▼             ▼
 8 PROJECT AGENT   + Default Gemini    (không thuộc tổ chức nào —
 (xem bảng 2.2)      Project            "No organization")
```

**Bằng chứng "GMSSub = Gimasys":** trong audit log ngày 22/06/2026, tài khoản
`tdbao@gimasys.com` thực hiện `AssignResourceToBillingAccount` gắn project vào ví
`011F53-FB4D9A-9E5452`, được Google chấp thuận với quyền `billing.resourceAssociations.create`
(quyền cấp quản trị trên ví tiền).

### 2.2. 8 project ↔ 8 agent — khớp 1-1 ✅

Đây là bảng ánh xạ quan trọng, dùng được cho cả dashboard lẫn backend sau này.

| Project (GCP) | Project ID | Agent trong `app.js` | Alias trong code |
|---|---|---|---|
| AI Chatbot Contact Center | `pro-tuner-454203-v3` | Chatbot Contact Center | `Contact Center` |
| AI Chatbot Contract hop dong | `ai-chatbot-contract` | Trợ Lý Ảo Hợp Đồng | `Chatbot hợp đồng` |
| AI Sale Agent | `tranquil-post-471401-c1` | Sale Agent | `Sale agent` |
| CRM Feedback | `crm-500509` | Phân Loại Dữ Liệu CRM | `CRM Feedback` |
| Feedback DMS tiep thi | `feedback-dms-tiep-thi` | Phân Loại Phản Hồi Tiếp Thị | `DMS Feedback` |
| Multimodal Invoice | `multimodal-invoice` | Multi modal AI Invoice | `Multi Modal` |
| TLA Ralli AI | `tla-ralli` | Trợ lý ảo Ralli | (TLA = Trợ Lý Ảo) |
| Tools quizz | `tools-quizz` | *(nằm trong `EXCLUDED_AGENTS`)* | — |
| Default Gemini Project | `gen-lang-client-0247490857` | *(project AI Studio tự tạo)* | — |
| token-ledger-test | `token-ledger-test` | *(project test cá nhân)* | — |

**Hệ quả quan trọng:** danh sách `aliases` trong `app.js:15-22` hóa ra chính là **tên project GCP**.
Người viết code trước đã lấy tên project làm alias nhưng không ghi lại lý do.

**Hệ quả thứ hai — sửa được một lỗi thật:** hiện `allAgents()` (`app.js:762`) dựng danh sách agent
từ chính dữ liệu usage. Nên **agent tạo ra mà chưa từng chạy sẽ biến mất khỏi cả tử số lẫn mẫu số**.
Ví dụ cụ thể: project **Multimodal Invoice tồn tại thật, có ngân sách 20 USD/tháng trong code, nhưng
không có dòng dữ liệu nào** → không ai biết đang trả tiền cho một agent bỏ xó.
→ **Danh sách project chính là danh sách agent đã tạo.** Lấy từ đây là sửa được.

### 2.3. Ai giữ quyền gì ✅

Trích từ lần `SetIamPolicy` cuối cùng (22/07/2026) trên project `ai-chatbot-contract`:

```
 ┌──────────────────────────────────────────────────────────┐
 │  roles/OWNER  — toàn quyền                               │
 │    • letrunghieu4799@gmail.com   ← người TẠO ra tất cả   │
 │    • rangdongai@gmail.com        ← tài khoản công ty     │
 ├──────────────────────────────────────────────────────────┤
 │  6 role CHỈ ĐỌC                                          │
 │    • nct18082004@gmail.com                               │
 │    • tranxuantuan1522005@gmail.com  ← TÔI                │
 │                                                          │
 │    billing.projectManager    · iam.supportUser           │
 │    logging.viewer            · monitoring.viewer         │
 │    servicemanagement.quotaViewer                         │
 │    serviceusage.serviceUsageViewer                       │
 └──────────────────────────────────────────────────────────┘
```

**Không có quyền ẩn nào.** Giả thuyết trước đó (*"có thể tôi đang có sẵn quyền billing mà không biết"*)
đã bị **bác bỏ** — 6 role trên là tất cả.

### 2.4. Ai cần hỏi việc gì

```
   Muốn BẬT BILLING EXPORT
        └─► GIMASYS (tdbao@gimasys.com)     ✅ đã chứng minh có quyền
            → owner project KHÔNG tự động có quyền trên ví tiền
            → rangdongai@ / letrunghieu4799@ là người ĐẶT YÊU CẦU

   Muốn LẤY DỮ LIỆU USER (chat, phòng ban, token/lượt)
        └─► letrunghieu4799@gmail.com       🟡 người dựng toàn bộ hệ thống
            → tạo project, tạo API key, cấp quyền cho mọi người
            → gần như chắc chắn cũng là người làm phần mềm TLA HĐ / Ralli
```

### 2.5. ⚠️ Rủi ro vận hành ghi nhận được

Toàn bộ hệ thống đứng trên **tài khoản Gmail cá nhân**, không có tài khoản `@rangdong.com.vn` nào,
và project không thuộc tổ chức nào ("No organization").

→ Nếu `letrunghieu4799@gmail.com` ngừng hợp tác, công ty **mất quyền sở hữu 8 project**.

Đây là vấn đề độc lập với dashboard nhưng đáng đưa vào báo cáo.

---

## 3. Quyền của tôi — chính xác đến đâu

### 3.1. Về billing: chỉ xem được **từng project một** ✅

Đây là điều bị hiểu nhầm nhiều nhất trong buổi hôm nay.

```
 ┌─────────────────────────────────────────────────────┐
 │  TẦNG TRÊN — VÍ TIỀN (billing account)              │
 │  Có bộ quyền RIÊNG:                                 │
 │    Billing Account Viewer / Costs Manager / Admin   │
 │  ❌ TÔI KHÔNG CÓ CÁI NÀO                            │
 └──────────────────────┬──────────────────────────────┘
                        │
      ┌─────────────────┼─────────────────┐
      ▼                 ▼                 ▼
  project 1         project 2   ...   project 8
  ✅ Project        ✅ Project         ✅ Project
     Billing           Billing            Billing
     Manager           Manager            Manager
```

Google hiển thị đúng dòng này khi mở trang billing:

> *"For billing account 'rangdong.com.vn - GMSSub', you have **limited access** to view
> billing data for the **project listed below**."*

Và địa chỉ trang bị ghim vào một project:
`console.cloud.google.com/billing/011F53-FB4D9A-9E5452/manage?project=<PROJECT_ID>`

**Cách chuyển project:** đổi tham số `project=` trong địa chỉ.

**Hệ quả thực tế:**
- ✅ Có role trên cả 8 project ⇒ **ghép tay vẫn ra bức tranh đầy đủ**
- ❌ Không thấy được báo cáo hợp nhất
- ❌ Không thấy được ai giữ quyền trên ví tiền
- ❌ Không thấy mục "Billing export" (menu bị ẩn theo quyền)

→ **Billing export là để KHỎI LÀM 8 LẦN, không phải để CÓ dữ liệu.**
Không bị tắc, chỉ bị chậm. Điều này hạ mức khẩn cấp của việc xin quyền.

### 3.2. Bảng khả thi thu thập dữ liệu tự động

```
 🟢 làm được NGAY   🟡 phải kiểm tra   🔴 đang bị chặn
```

| Muốn lấy | Nguồn | Δt nhỏ nhất | Quyền cần | Trạng thái |
|---|---|---|---|---|
| Số lượt gọi | Cloud Monitoring | **~1 phút** | Monitoring Viewer ✅ | 🟢 |
| Tỷ lệ lỗi + mã lỗi (400/503/429) | Cloud Monitoring | **~1 phút** | Monitoring Viewer ✅ | 🟢 |
| Độ trễ p50/p95/p99 | Cloud Monitoring | **~1 phút** | Monitoring Viewer ✅ | 🟢 |
| Quota: hạn mức + đã dùng | Quota API + Monitoring | vài phút | Quota Viewer ✅ | 🟢 |
| Danh sách agent (kể cả chưa chạy) | Danh sách project | — | Service Usage Viewer ✅ | 🟢 |
| Token + chi phí theo model | Billing export | ~giờ | **cần Gimasys bật** | 🔴 |
| Token + chi phí (thủ công) | Billing Reports / CSV | ngày | đang có, **8 lần** | 🟡 tay |
| **Danh tính user, lịch sử chat** | **CSDL phần mềm agent** | **từng lượt** | tài khoản admin ✅ | 🟡 chưa khảo sát |
| Token qua log ứng dụng | Cloud Logging | — | — | ⛔ **KHÔNG TỒN TẠI** |

**Đọc bảng:** khoảng **60–70%** những gì dashboard cần là lấy tự động được **ngay hôm nay**,
bằng quyền đang có. Phần token + tiền thì đang chờ, nhưng vẫn có đường tay để không tắc.

---

## 4. Cấu trúc SKU — cách Google tính tiền

### 4.1. SKU là gì

```
   QUÁN CÀ PHÊ                  GOOGLE CLOUD
   ───────────                  ────────────
   Quán "Highlands"      ≈      SERVICE      ("Gemini API")
   Món trong menu        ≈      SKU          (một dòng bảng giá)
   Số ly đã gọi          ≈      usage.amount (số token)
   Tiền phải trả         ≈      cost
```

### 4.2. Bốn SKU quan sát được ✅

Kiểm trên 2 project (`feedback-dms-tiep-thi`, `crm-500509`), khoảng thời gian **01/01 → 03/08/2026**:

| # | SKU | Service ID | SKU ID |
|---|---|---|---|
| 1 | Generate content **cached input** token count gemini 2.5 flash input short text | `AEFD-7695-64FA` | `5CDC-4C82-2AEC` |
| 2 | Generate content **input** token count gemini 2.5 flash short input text | `AEFD-7695-64FA` | `981A-C057-0BF9` |
| 3 | Generate content **output** token count gemini 2.5 flash short input text | `AEFD-7695-64FA` | `911A-8880-A243` |
| 4 | Log Storage cost | `5490-F7B7-8DF6` | `143F-A1B0-E0BE` |

**Cách đọc một SKU:**

```
   Generate content │ output token count │ gemini 2.5 flash │ short input text
   ─────────────────┼────────────────────┼──────────────────┼──────────────────
   THAO TÁC         │  ĐẾM CÁI GÌ        │  MODEL           │  BẬC GIÁ
```

Và `usage.amount` của dòng này = **số token**. Đúng con số dashboard cần.

### 4.3. Kết luận về bảng giá

| Lo ngại | Kết quả |
|---|---|
| Có bậc "**long** input text" không? | ✅ **KHÔNG** — chỉ thấy "short". Mô hình `{giá vào, giá ra}` của dashboard là **đủ** |
| Có SKU riêng cho **cached input** không? | ✅ **CÓ** — Google tính giá riêng, rẻ hơn |

**Về quyết định gộp cached input vào input:** đây là **yêu cầu nghiệp vụ có chủ đích**, không phải sót.
Cần tách bạch hai chuyện:

```
 ┌──────────────────────────────────────────────────────────┐
 │  ĐẾM TOKEN                                  ✅ GỘP ĐƯỢC  │
 │  "agent dùng 5 triệu token đầu vào" — hợp lý, dễ hiểu    │
 ├──────────────────────────────────────────────────────────┤
 │  TÍNH TIỀN                                  ❌ KHÔNG GỘP │
 │  cached input RẺ HƠN input thường                        │
 │  (input + cached) × giá_cao ⇒ TÍNH ĐẮT HƠN THỰC TẾ       │
 └──────────────────────────────────────────────────────────┘
```

**Cách xử lý đã thống nhất:** giữ nguyên việc gộp khi hiển thị số token, nhưng
**khi có billing thì lấy thẳng số tiền của Google thay vì tự nhân token × giá**.
Google đã tính đúng mọi bậc, mọi loại token, đã trừ khuyến mãi. Không thể lệch.

> Đây là một **quyết định thiết kế** cần đưa vào `design.md` khi làm backend:
> `cost` lấy từ billing (authoritative), không tính lại từ `token × pricing`.

### 4.4. Còn chưa kiểm

Mới kiểm **2/8 project**, mà là 2 project **nhỏ nhất** (cả hai chỉ dùng Gemini 2.5 Flash).

Chưa kiểm những project dùng model khác và nhiều token nhất:
- `pro-tuner-454203-v3` (Contact Center) — dùng **Gemini 3.0 Flash**, ~7,9 triệu token/tuần
- `ai-chatbot-contract` (Hợp Đồng) — dùng **Gemini 2.5 Pro**
- `tranquil-post-471401-c1` (Sale Agent), `tla-ralli` (Ralli)

→ Việc cần làm, mỗi project ~1 phút. Xem [§8.2](#82-tự-làm-được-hôm-nay).

---

## 5. Vì sao Cloud Logging không có dữ liệu hoạt động — ĐÓNG HẲN

Đây là hướng đã tốn nhiều thời gian nhất và giờ đã **loại bỏ dứt điểm**.

### 5.1. Ba lý do, cả ba đều đóng chặt ✅

**Lý do 1 — Project chỉ mới tồn tại từ 20/06/2026**

```
   Khoảng thời gian đã tra:  01/01/2026 ──────────────► 04/08/2026
   Project thực sự tồn tại:              20/06 ───────► 04/08

   ⇒ Trước 20/06 KHÔNG CÓ GÌ để mà log.
     Không phải thiếu quyền. Không phải hết hạn lưu.
     Project chưa ra đời.
```

Dòng đầu tiên trong file log tải về là `CreateProject` lúc `2026-06-20T07:08:30.268781Z`.

**Lý do 2 — Không có gì chạy trên Google để mà ghi log**

Project chỉ bật **3 API**, và chỉ 1 cái có ý nghĩa:

```
   ✅ cloudapis.googleapis.com                (gói mặc định, không làm gì)
   ✅ generativelanguage.googleapis.com       (Gemini API)
   ✅ privilegedaccessmanager.googleapis.com  (quản lý quyền tạm thời)

   ❌ KHÔNG Cloud Run · Compute Engine · App Engine
   ❌ KHÔNG GKE · Cloud Functions · Cloud SQL
```

Hóa đơn cũng xác nhận: chỉ 4 SKU (3 token + 1 lưu log), **không có SKU máy chủ/lưu trữ/mạng nào**.

**Lý do 3 — Loại log ghi hoạt động thì mặc định tắt, mà bật cũng không xem được**

| Loại log | Ghi gì | Trạng thái |
|---|---|---|
| ① Admin Activity audit | ai **đổi cấu hình** gì | ✅ luôn bật — **đây là thứ đang thấy** |
| ② Data Access audit | ai **gọi API** gì | ❌ mặc định tắt; bật thì tốn tiền; xem cần `Private Logs Viewer` (không có) |
| ③ App log | phần mềm tự ghi | ❌ không tồn tại (xem lý do 2) |

### 5.2. Bức tranh thật của hệ thống

```
 ┌─────────────────────────────────────────────────────┐
 │  MÁY CHỦ Ở ĐÂU ĐÓ                                   │
 │  (nội bộ công ty / VPS / hạ tầng nhà thầu)          │
 │                                                     │
 │  • Phần mềm agent (TLA HĐ, Ralli…)                  │
 │  • CSDL riêng: user, chat, phòng ban, phân quyền    │
 │  • Log của phần mềm  ← NẰM Ở ĐÂY                    │
 └────────────────────────┬────────────────────────────┘
                          │ gọi qua internet, bằng API key
                          ▼
 ┌─────────────────────────────────────────────────────┐
 │  GOOGLE CLOUD PROJECT                               │
 │  Thực chất chỉ là:                                  │
 │    • một cái API key                                │
 │    • một dòng hóa đơn                               │
 │    • một bộ đếm (Monitoring)                        │
 │                                                     │
 │  Google KHÔNG BIẾT ai đang dùng, phòng ban nào —    │
 │  chỉ biết "có người gọi API"                        │
 └─────────────────────────────────────────────────────┘
```

**Ví dụ để nhớ:** lắp đồng hồ điện cho một căn nhà rồi đi tìm *nhật ký sinh hoạt của gia đình*
trong đồng hồ điện. Đồng hồ chỉ đếm kWh — nó không biết ai bật đèn, lúc nào, làm gì.

### 5.3. Hệ quả

```
 ⛔ ĐÓNG: Lấy token qua Cloud Logging
          → sẽ KHÔNG BAO GIỜ có. Đừng thử lại.

 ⛔ ĐÓNG: "Tự ghi log ở tầng app"
          → phải sửa code phần mềm agent, không nằm trong tay mình
          → nhưng CÓ THỂ ĐỀ NGHỊ với letrunghieu4799@ (xem §6)
```

---

## 6. ⭐ Nguồn thứ ba: CSDL của chính phần mềm agent

Đây là phát hiện có giá trị cao nhất, và **chưa ai khảo sát**.

### 6.1. Bằng chứng

Màn hình quản trị của **TLA HĐ** (Trợ Lý Ảo Hợp Đồng), đăng nhập với vai trò **ADMIN**:

```
 ┌──────────────────────────────────────────────────────┐
 │  TLA HĐ — Tổng quan hệ thống                         │
 ├──────────────────────────────────────────────────────┤
 │   Dashboard                                          │
 │   Đang online          ← ai đang dùng ngay bây giờ ⭐ │
 │   Lịch sử Chat         ← TỪNG CUỘC, TỪNG NGƯỜI  ⭐⭐⭐ │
 │   Kho Tri Thức                                       │
 │   Lịch sử tài liệu                                   │
 │  ── QUẢN TRỊ ──                                      │
 │   Cây tổ chức          ← phòng ban THẬT         ⭐⭐  │
 │   Phân quyền           ← ai được cấp quyền      ⭐⭐  │
 │   Cấu hình hệ thống                                  │
 └──────────────────────────────────────────────────────┘
```

### 6.2. Nó giải quyết được 7 chỗ dashboard đang bịa

Đối chiếu với `docs/dashboard-metrics-and-backend-plan.md` Phần VI §1:

| Chỉ tiêu đang bịa | Đang tính thế nào | Phần mềm agent có sẵn? |
|---|---|---|
| Số liệu theo từng tài khoản | chia đều theo trọng số bịa (`app.js:280-341`) | ✅ Lịch sử Chat |
| Người dùng hoạt động theo ngày | `tổng × (0,10 + 0,16 × req/maxReq)` (`app.js:2599`) | ✅ Đang online + Lịch sử Chat |
| Tài khoản không hoạt động theo ngày | `tổng − DAU` — kế thừa lỗi trên | ✅ |
| "Bắt đầu không hoạt động" | gán = ngày cuối kỳ (`app.js:337`) | ✅ Lịch sử Chat |
| Cây phòng ban | chép tay từ Excel vào `ORG_UNITS` | ✅ Cây tổ chức |
| Số tài khoản được cấp | chép tay từ Excel | ✅ Phân quyền |
| Số cuộc chat (`c`) | **luôn = 0** trong mọi bản ghi | ✅ Lịch sử Chat |

### 6.3. Vì sao đây là nguồn **duy nhất** có userId

```
   Phần mềm agent gọi Gemini API bằng MỘT API key
   dùng chung cho cả phòng ban.
                    ↓
   Google chỉ thấy "API key này gọi 500 lần"
   KHÔNG thấy 500 lần đó là của bao nhiêu người.
                    ↓
   ⇒ Dù có billing export hoàn hảo,
     dù có Monitoring đầy đủ,
     DANH TÍNH NGƯỜI DÙNG SẼ MÃI MÃI KHÔNG CÓ Ở PHÍA GOOGLE.
```

### 6.4. Câu hỏi cần hỏi

Gửi cho `letrunghieu4799@gmail.com` (hoặc đơn vị làm phần mềm):

1. Lịch sử chat có lưu **số token mỗi lượt** không?
   *(Gemini trả về sẵn `usageMetadata` mỗi lần gọi: promptTokenCount, candidatesTokenCount, cachedContentTokenCount)*
2. Có **API** để lấy dữ liệu ra không? (lịch sử chat, danh sách user, cây tổ chức)
3. Nếu không có API, cho **quyền đọc CSDL (read-only)** được không?
4. Có **xuất Excel/CSV** được không? *(giải pháp tạm, không cần lập trình)*

**Câu 1 là quan trọng nhất.** Nếu có → có token + user + phòng ban + thời gian,
chính xác tới từng giây, **không cần chờ Google**.

---

## 7. ⚠️ Phát hiện: độ lệch chi phí 2,9 lần

### 7.1. Con số

Từ Billing Reports, project `feedback-dms-tiep-thi`, khoảng 01/01 → 03/08/2026:

> *"You spent **$6.16** between Jan – Aug 2026"*

Tính từ dữ liệu trong `app.js` cho đúng agent đó (Phân Loại Phản Hồi Tiếp Thị):

| Mốc trong dashboard | token vào | token ra | Chi phí (dashboard tự tính) |
|---|---|---|---|
| 01/06 | 2.559.100 | 1.206.600 | $3,78 |
| 08/06 | 1.559.100 | 1.066.000 | $3,13 |
| 15/06 | 1.339.100 | 1.006.600 | $2,92 |
| 22/06 | 2.059.133 | 1.306.621 | $3,88 |
| 01/07 | 60.523 | 578.430 | $1,46 |
| 15/07 | 751.650 | 902.779 | $2,48 |
| **Tổng** | **8.328.606** | **6.067.030** | **$17,67** |

```
   Google nói:      $6,16
   Dashboard nói:  $17,67       ⇒  LỆCH 2,9 LẦN
```

### 7.2. Phân rã độ lệch — hai vấn đề riêng biệt

Nhớ project được tạo **20/06** và gắn vào ví tiền **22/06**:

```
 ┌──────────────────────────────────────────────────────────┐
 │  $17,67  ← dashboard, toàn bộ                            │
 │     │                                                    │
 │     │  ‼️ VẤN ĐỀ A: ~$9,8 gán cho khoảng thời gian mà    │
 │     │     PROJECT CHƯA TỒN TẠI (01/06, 08/06, 15/06)     │
 │     ▼                                                    │
 │   $7,82  ← chỉ phần sau khi project ra đời               │
 │     │                                                    │
 │     │  🟡 VẤN ĐỀ B: ~27% — nhiều khả năng là             │
 │     │     CACHED INPUT TOKEN (rẻ hơn, nhưng dashboard    │
 │     │     tính giá đầy đủ)                               │
 │     ▼                                                    │
 │   $6,16  ← Google                                        │
 └──────────────────────────────────────────────────────────┘
```

**Vấn đề A — nghiêm trọng hơn.** Dữ liệu tháng 6 (tuần 1–3) không thể đến từ project này.
Nó chạy ở đâu? Khả năng: "Default Gemini Project", một project cũ, hoặc **file Excel gán sai kỳ**.
Nếu là gán sai kỳ thì **mọi so sánh "kỳ này vs kỳ trước" trong dashboard đều sai**.

**Vấn đề B — khớp với giả thuyết cached token.** Đây là bằng chứng thực nghiệm cho kết luận ở §4.3:
tự nhân `token × giá` làm chi phí bị tính đắt lên.

### 7.3. ⚠️ Ba chỗ tôi có thể sai — cần kiểm trước khi kết luận

```
   ① Bảng giá trong app.js:345 có thể lỗi thời
      (0,30 / 2,50 USD mỗi triệu token — ai nhập? khi nào?)

   ② $6,16 đọc từ dòng tóm tắt AI trên màn hình,
      không phải từ bảng số liệu gốc

   ③ Phạm vi báo cáo có thể không trùng khít
      (project vs agent, múi giờ, ngày ghi nhận)
```

### 7.4. Cách kiểm cho chắc (10 phút)

Trong Billing Reports, đặt khoảng đúng **01/07 → 31/07**, nhóm theo SKU, rồi so **3 con số**
với dashboard: **token vào · token ra · chi phí**. Một tháng, một project, ba con số.
Khớp hay không sẽ rõ ngay.

> Đây là phép đối chiếu đầu tiên trong lịch sử dự án giữa dữ liệu Excel và một nguồn độc lập.
> Nó **trúng ngay lần đầu**. Đáng làm đầy đủ cho cả 8 project.

---

## 8. Việc cần làm

### 8.1. Hai tin nhắn — gửi ngay (lead-time dài nhất)

**① Gửi Gimasys** (`tdbao@gimasys.com` hoặc người phụ trách tài khoản Rạng Đông)

> Anh/chị cho em hỏi về ví tiền **rangdong.com.vn - GMSSub** (ID `011F53-FB4D9A-9E5452`):
> 1. Mình đã bật **BigQuery billing export** chưa ạ? Nếu rồi thì đang đổ vào project/dataset nào?
> 2. Nếu chưa, nhờ anh/chị **bật giúp**, đổ vào dataset em chỉ định.
> 3. Cấp cho em **quyền ĐỌC đúng dataset đó** (không cần quyền xem toàn bộ chi phí công ty).
>
> Mục đích: thay việc tải tay 8 file CSV mỗi tuần bằng script tự động, phục vụ dashboard chi phí AI.

*Vì sao cách này dễ được duyệt:* không xin quyền cao, chỉ xin **một cái ngăn tủ**.
Và với đại lý, đây là yêu cầu hỗ trợ khách hàng thông thường.

**② Gửi `letrunghieu4799@gmail.com`** — nội dung 4 câu hỏi ở [§6.4](#64-câu-hỏi-cần-hỏi)

*Kỳ vọng của tin nhắn ② cao hơn ①, và có lẽ dễ được đáp ứng hơn.*

### 8.2. Tự làm được, hôm nay

| # | Việc | Thời gian | Mục tiêu |
|---|---|---|---|
| 3 | **Khảo sát phần mềm TLA HĐ** — mở Lịch sử Chat / Cây tổ chức / Phân quyền / Đang online, xem có cột token không, xuất file được không | ~1h | Nguồn duy nhất có userId. Trúng ⇒ giải quyết **7 chỗ bịa** cùng lúc |
| 4 | **Đối chiếu tháng 7** cho 1 project (§7.4) | 10 phút | Xác nhận/bác bỏ độ lệch 2,9 lần |
| 5 | **Kiểm SKU 6 project còn lại** — ưu tiên Contact Center (3.0 Flash) và Contract hop dong (2.5 Pro) | 1 phút/project | Chốt bảng giá dashboard có đủ chiều chưa |
| 6 | **Truy: dữ liệu tháng 6 tuần 1–3 từ đâu?** Project ra đời 20/06 mà dashboard có dữ liệu từ 01/06 | ~30 phút | Nếu Excel gán sai kỳ ⇒ mọi so sánh kỳ đều sai |
| 7 | **Xin "menu" phép đo Cloud Monitoring** — liệt kê metric descriptor thay vì đoán tên | ~1h | Nguồn tự động **duy nhất đang mở sẵn**, Δt 1 phút → request, mã lỗi thật, độ trễ thật, quota |
| 8 | **Lấy danh sách project làm danh sách agent** | 10 phút | Sửa lỗi Multimodal Invoice biến mất (§2.2) |

### 8.3. Đóng lại — không làm nữa

```
 ✖️  Lấy token qua Cloud Logging       — đã chứng minh không tồn tại (§5)
 ✖️  Suy đoán cấu trúc ví tiền          — đã rõ: Gimasys (§2.1)
 ✖️  Tìm quyền billing ẩn của mình      — đã rõ: không có (§2.3)
 ✖️  Xem chi phí công ty qua AI Studio  — Cloud Console cho nhiều hơn (§3.1)
```

---

## 9. Phụ lục

### 9.1. Những giả thuyết đã bị bác bỏ hoặc sửa

Ghi lại để **không lặp lại** ở lần khám phá sau.

| Giả thuyết | Kết luận | Bằng chứng |
|---|---|---|
| "Prepay có thể làm billing export vô dụng" | ❌ **Bác bỏ** | Đã tải được CSV có token theo model từ Cloud Console → dữ liệu billing có đủ chiều |
| "Cần tách theo API key để phân biệt agent" | ❌ **Thừa** | 1 project = 1 agent, khớp 8/8 |
| "Có thể tôi đang có quyền billing mà không biết" | ❌ **Bác bỏ** | `SetIamPolicy` cuối cho thấy đúng 6 role, không hơn |
| "Không thấy dataset ⇒ export chưa bật" | ❌ **Không kết luận được** | Export tạo **1 dataset ở 1 project** do người cấu hình chọn, có thể ở nơi không nhìn thấy |
| "AI Studio không có breakdown theo model" | 🟡 **Sửa lại** | Giao diện AI Studio **CÓ** (Input/Output Tokens per model). Kết luận cũ chỉ đúng với nhóm metric `serviceruntime`, chưa kiểm `generativelanguage` |
| "Công ty mua GCP qua bên thứ ba" | ✅ **Xác nhận** | `tdbao@gimasys.com` thực hiện `AssignResourceToBillingAccount` |
| "Phần mềm agent không chạy trên GCP" | ✅ **Xác nhận** | Chỉ 3 API bật, không có SKU máy chủ nào |
| "Bảng giá thiếu bậc long input text" | ✅ **Gỡ bỏ** (cho 2 project đã kiểm) | Chỉ thấy "short input text" trong khoảng 01/01–03/08 |

### 9.2. Định danh cần nhớ

| Hạng mục | Giá trị |
|---|---|
| Ví tiền **công ty** | `rangdong.com.vn - GMSSub` · ID `011F53-FB4D9A-9E5452` |
| Ví tiền **cá nhân** (không liên quan) | `My Billing Account` · ID `010187-B08D86-6E81CF` · Cloud Prepay · 2 project |
| Đại lý | **Gimasys** — `tdbao@gimasys.com` |
| Owner project | `letrunghieu4799@gmail.com` · `rangdongai@gmail.com` |
| Người dùng chỉ đọc | `nct18082004@gmail.com` · `tranxuantuan1522005@gmail.com` |
| Service ID — Gemini API | `AEFD-7695-64FA` |
| Service ID — Cloud Logging | `5490-F7B7-8DF6` |
| Đường dẫn billing theo project | `console.cloud.google.com/billing/011F53-FB4D9A-9E5452/manage?project=<PROJECT_ID>` |

### 9.3. Timeline dựng hệ thống — project `ai-chatbot-contract`

Trích từ 43 dòng Admin Activity audit log (`downloaded-logs-20260804-165359.json`).

```
 20/06/2026  07:08  │ letrunghieu4799@ TẠO project "AI chatbot contract"
                    │ projectNumber 779509080458
            07:08   │ bật cloudapis.googleapis.com
            07:16   │ bật generativelanguage.googleapis.com        ← Gemini API
            07:16   │ tạo service account "Gemini API Key"
                    │   ais-gemini-key-4a877251605946b@779509080458.iam.gserviceaccount.com
            07:16   │ tạo API KEY (annotation generative-language: enabled)
            07:18   │ bật privilegedaccessmanager.googleapis.com
            07:25   │ đổi tên → "AI Chatbot Contract hop dong"
 ───────────────────┼────────────────────────────────────────────────────
 22/06  01:53       │ tdbao@gimasys.com nhận quyền sở hữu
        02:15       │ tdbao@gimasys.com GẮN VÀO VÍ TIỀN CÔNG TY      ⭐
        03:14       │ gỡ quyền owner của Gimasys (bàn giao xong)
 ───────────────────┼────────────────────────────────────────────────────
 25/06  09:26       │ rangdongai@gmail.com nhận quyền sở hữu
        09:37       │ (thử nhận lại → lỗi, vì đã nhận rồi)
 ───────────────────┼────────────────────────────────────────────────────
 28/06 → 30/06      │ cấp 6 role chỉ đọc cho nct18082004@gmail.com
 21/07 → 22/07      │ cấp 6 role chỉ đọc cho tranxuantuan1522005@gmail.com
```

### 9.4. Ẩn số còn lại

| # | Câu hỏi | Ai/việc nào trả lời | Mức quan trọng |
|---|---|---|---|
| 1 | Phần mềm agent có lưu **số token mỗi lượt chat** không? | Việc 3 + tin nhắn ② | ⭐⭐⭐ cao nhất |
| 2 | Độ lệch **$17,67 vs $6,16** do đâu? | Việc 4 | ⭐⭐⭐ |
| 3 | Dữ liệu **tháng 6 tuần 1–3** chạy ở project nào? | Việc 6 | ⭐⭐ |
| 4 | Số liệu theo model của AI Studio có **lấy được bằng máy** không? | Việc 7 | ⭐⭐ |
| 5 | Cloud Monitoring **lưu quá khứ bao lâu**? (quyết định có backfill T6/T7 được không) | Việc 7 | ⭐⭐ |
| 6 | Ví tiền công ty **đã bật billing export chưa**? | Tin nhắn ① — **không tự tra được** | ⭐⭐ |
| 7 | 8 project có phải **cùng một nhà thầu** dựng không? | Tin nhắn ② | ⭐ |

### 9.5. Tài liệu liên quan

| File | Nội dung | Trạng thái so với tài liệu này |
|---|---|---|
| `token-ledger-billing-export-test-log.md` | Nhật ký nghiên cứu billing export + IAM | ⚠️ **Đã lệch** — xem §9.6 |
| `docs/dashboard-metrics-and-backend-plan.md` | Chỉ tiêu theo entity/tab + kế hoạch backend | Vẫn đúng phần lớn; Phần VI §1 được củng cố bởi §6.2 tài liệu này |

### 9.6. Những chỗ cần sửa trong `token-ledger-billing-export-test-log.md`

Chưa sửa — ghi lại để làm sau:

- **§1** — quyền thật là **xem chi phí từng project một** trên cả 8 project; không có quyền cấp ví tiền; không có quyền ẩn nào
- **§2 mục 30** — kết luận *"không có label model"* chỉ đúng với nhóm metric `serviceruntime`,
  **chưa kiểm** `generativelanguage`; và mâu thuẫn với việc giao diện AI Studio hiện được breakdown theo model
- **§2 cách 2 ("tự log ở tầng app")** — bổ sung: app **không chạy trên GCP**, nên đây là đề nghị
  gửi cho đơn vị làm phần mềm, không phải việc tự làm được
- **§4** — hạ rủi ro Prepay, ghi đúng lý do (CSV tay đã có token theo model), không phải vì ảnh nào
- **§6** — đánh dấu *"kiểm tra export đã bật chưa"* là **không tự làm được**, phải hỏi Gimasys
- **Bổ sung mục mới**: Bản đồ tổ chức GCP · Cấu trúc SKU · Nguồn thứ ba (CSDL agent) · Độ lệch chi phí

---

*Ghi ngày 04/08/2026. Nguồn: khảo sát trực tiếp Google Cloud Console, Google AI Studio,
dashboard TLA HĐ, và 43 dòng Admin Activity audit log của project `ai-chatbot-contract`
(`downloaded-logs-20260804-165359.json`).*
