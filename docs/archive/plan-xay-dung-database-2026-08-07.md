# Kế hoạch xây dựng Database + Backend — 07/08/2026

> **Đối tượng đọc:** người mới vào dự án. Mọi thuật ngữ được giải thích ở chỗ dùng lần đầu.
>
> **Bản này thay thế bản trước** sau khi có 3 quyết định về phạm vi và sau khi đọc lại
> toàn bộ `index.html` bằng script trích xuất thay vì đọc bằng mắt.

---

## 0. Ba quyết định đã chốt ngày 07/08

| # | Quyết định | Hệ quả |
|---|---|---|
| **A1** | 6 agent (trừ TLA HĐ và Ralli) — mỗi project tính là **1 agent = 1 user**, không cần phân cấp bên trong | Khoá tự nhiên của 6 agent này là `(agent, ngày, model)`. **Cây tổ chức vẫn giữ** cho TLA HĐ và Ralli |
| **A2** | Bỏ tháng 3–6 của TLA HĐ, bắt đầu dùng dữ liệu từ cuối tháng 6 | Xoá bỏ vấn đề "91,4% token không đối chứng được" |
| **A3** | Chỗ nào Google và app không khớp thì **lấy Google** — ⚠️ **sửa 09/08, xem A3′ bên dưới** | Xoá bỏ vấn đề "app ghi thiếu 17%" |
| **A3′** | *(09/08)* Lấy Google, **trừ chiều người dùng/phòng ban của TLA HĐ và Ralli** | Google dừng ở mức project, **không có nhãn người dùng trong bất kỳ phép đo nào**. Bỏ số app đi thì chiều "người dùng" không phải kém chính xác — nó **không tồn tại**. Chi tiết ở §4.6b |
| **B3** | Phần không quy được về ai → để thành **dòng riêng "Chưa quy được"**, không phân bổ | Trung thực, và bản thân nó là một chỉ tiêu chất lượng dữ liệu |

## 0b. Bốn quyết định bổ sung ngày 08/08

> Căn cứ đầy đủ ở [`mui-gio-2026-08-08.md`](mui-gio-2026-08-08.md) và [`van-de-xu-ly-du-lieu-2026-08-08.md`](van-de-xu-ly-du-lieu-2026-08-08.md).

| # | Quyết định | Hệ quả |
|---|---|---|
| **M-A** | **Nạp đủ 525.639 dòng Monitoring**, không lọc lúc nạp | Đúng quy tắc 3 của §4.6. **Nghiệm thu Ngày 1 sửa từ `85166` thành `525639`** (đã sửa ở §5). Cần thêm view `mon_sach` lọc `dich_vu` và bỏ `*_limit` |
| **M-B** | **Hiển thị ngày theo ICT** | Hoá đơn Google cắt ngày theo **giờ Mỹ**, nên chi phí theo ngày là **kết quả quy đổi**, không lấy thẳng từ hoá đơn. Tổng cả kỳ vẫn phải ra đúng $270,9517 |
| **M-C** | **Cào lại `request_latencies` dạng DISTRIBUTION** | p95/p99 theo ngày thành số chính xác thay vì ước lượng. **Có hạn chót** — Google chỉ giữ 196 ngày, mỗi ngày trôi qua mất thêm một ngày ở đuôi |
| **M-D** | **Bỏ theo đuổi `B1` và `D1`** — Ralli dùng dữ liệu cào từ API (`data/ctda/`) làm nguồn duy nhất | Ralli chỉ bao giờ có `nguon='app'`, không có đối chứng. Cột lỗi và độ trễ của Ralli hiện `—`, **không phải `0%`**. Chi phí Ralli suy từ `ref_price` với `nguon='suy nguoc'`, phải gắn nhãn "ước tính" |

**Bốn quyết định nghiệp vụ, chốt chiều 08/08:**

| # | Quyết định | Hệ quả |
|---|---|---|
| **M-E** | **Mỗi tài khoản là một user.** Không phân biệt tài khoản dùng chung hay cá nhân | Xoá câu hỏi chặn số 1. `admin` và `Test1` của TLA HĐ vẫn tính là user bình thường — nghĩa là **53,6% token dồn vào 2 tài khoản là chuyện có thật về mức độ tập trung sử dụng**, không phải khuyết tật dữ liệu |
| **M-F** | **Tỷ giá VNĐ gõ cứng** theo tỷ giá hiện tại, kéo API sau | `ref_fx` vẫn giữ nguyên cấu trúc (một dòng mỗi ngày) để sau này đổ API vào không phải sửa schema. Hiện nạp một dòng, `nguon = 'go cung'` |
| **M-G** | **Ngân sách Ralli** đọc từ `data/ctda/token-usage-budget.json` | ⚠️ Xem cảnh báo đơn vị bên dưới |
| **M-H** | **Bảng giá model giữ nguyên** như hiện tại. Sếp là người duyệt | Xoá câu hỏi chặn số 4. `ref_price.nguon = 'suy nguoc'` cho tới khi có bảng chính thức |

> ### ⚠️ Ngân sách Ralli KHÁC ĐƠN VỊ với 6 agent kia
>
> ```json
> data/ctda/token-usage-budget.json   →   { "monthly_limit": 50000000, "enabled": true }
> ```
>
> **50 triệu là TOKEN, không phải USD.** Trong khi `app.js` đặt ngân sách 6 agent kia bằng tiền (tổng $160/tháng). Bảng `ref_budget` ở §4.5 chỉ có cột `ngan_sach_usd` — **không chứa được**.
>
> Đề xuất: **thêm cột `ngan_sach_token`**, không quy đổi. Quy ra USD sẽ khiến ngân sách trôi mỗi lần bảng giá đổi, trong khi bản chất Ralli đang bị chặn theo token thật.
>
> Ghi chú: Ralli đã dùng **44,7 / 50 triệu token = 89% hạn mức**.

**Đã kiểm chứng 08/08 — giả định "chi phí project = chi phí agent" đứng vững:**

Đối chiếu màn hình Billing của `pro-tuner-454203-v3` với file CSV đã tải:

```
   Man hinh   $95,78   (01/01 - 31/08/2026)      bang chi tiet chi CO MOT DONG: Gemini API
   File CSV   $93,76   (13/01 - 04/08/2026)      1 dich vu, 18 SKU
   ─────────────────────────────────────────────────────────────────────────────
   Chenh      $ 2,02   =  4,4 ngay x $0,46/ngay  =  dung bang so ngay file con thieu
```

Dự án này có **2 dịch vụ** (`Cloud Logging` và `Gemini API`) nhưng **Cloud Logging tốn $0** — nên nó không có dòng nào trong bảng chi phí, và cũng không có gì để tải về. Đó là lý do bản xuất CSV chỉ có Gemini API: **không phải bị lọc mất, mà là không có dòng nào khác tồn tại.**

Nghĩa là: dù `pro-tuner` có lưu lượng tới 9 dịch vụ Google (Drive, Sheets, Compute, Storage…), **không dịch vụ nào phát sinh tiền** — tất cả nằm trong hạn mức miễn phí. Hoá đơn là 100% chi phí AI.

**Còn treo:** `apikey:UNKNOWN` — chỉ **29/39.943 lượt gọi (0,07%)**, rải trên 6 ngày, 05/05→15/07. Không tra được bằng `gcloud`: chữ `UNKNOWN` nghĩa là chính Google không phân giải được khoá, không có mã để tra. Bỏ qua, không đáng theo đuổi.

**Hai quy tắc nạp bổ sung cho §4.6:**

| # | Quy tắc | Vì sao — bằng số |
|---|---|---|
| 8 | **Phân loại SKU theo thứ tự `cached` → `output` → `input`** | SKU `911A-8880-A243` tên là *"Generate content **output** token count gemini 2.5 flash short **input** text"*. Kiểm `input` trước `output` thì **346 dòng / $105,42 = 38,9% chi phí** nhảy sai cột — mà tổng vẫn đúng nên nghiệm thu tổng **vẫn xanh** |
| 9 | **`dich_vu` = `res_service`, rỗng thì lấy tiền tố của `metric_type`** | Đúng các dòng token của `generativelanguage` có `res_service` **rỗng**. Gán thẳng `dich_vu = res_service` rồi lọc sẽ trả về **0 dòng token, không báo lỗi** — đúng dạng lỗi **X7** |

**Múi giờ của từng nguồn** (chi tiết ở `mui-gio-2026-08-08.md`):

```
   Hoá đơn Google (7 project)   Pacific   không ghi nhãn   → phải quy đổi
   Monitoring Google            UTC       có sẵn ts_ict    → dùng thẳng
   Ralli    data/ctda/          UTC       không ghi nhãn   → cộng 7h
   TLA HĐ   data/tla-hd/        ICT       ghi rõ +07:00    → KHÔNG cộng thêm
```

---

## 1. Dashboard đang cần gì — số liệu trích từ `index.html`

Trích bằng `test/trich_yeu_cau_dashboard.py`, không đọc bằng mắt.

| Tab | Thẻ số | Biểu đồ | Bảng | Cộng |
|---|---:|---:|---:|---:|
| 1. Tổng quan | 8 | 6 | 2 | 16 |
| 2. Phòng ban & User | 8 | 5 | 2 | 15 |
| 3. Agents | 4 | 1 | 2 | 7 |
| 4. Provider & Model | 9 | 4 | 1 | 14 |
| 5. Chi phí | 4 | 4 | 1 | 9 |
| 6. Hiệu năng | 7 | 2 | 1 | 10 |
| **Tổng** | **40** | **22** | **9** | **71** |

**Cấu hình hiện tại trong `app.js`:**

```
   RANGE_PRESETS   7 ngày / 30 ngày / 90 ngày / Tất cả      (tính lùi từ hôm nay)
   SEED_DAY        2026-07-01
   VND_RATE        25200                                     <- gõ cứng, không nguồn
   Trường 1 dòng   a, d, m, ug, u, c, ti, to, r, er, lat, cached, think
   Ngân sách       6 agent, tổng $160/tháng                   <- thiếu Ralli, Tools Quizzer
```

**Ba điều đọc được từ chính markup mà trước đó không biết:**

1. **`SEED_DAY = "2026-07-01"`** — prototype đã tự neo dữ liệu mẫu ở mốc 01/07. Việc chốt kỳ
   chuẩn từ 01/07 **không phải thay đổi**, mà là làm đúng cái prototype đã giả định.
2. Thẻ "Tổng chi phí" đã ghi sẵn nguồn: **`BigQuery Billing · ≈1 ngày`**. Người thiết kế màn
   hình đã định lấy tiền từ billing — trùng đúng quyết định A3.
3. Ô chọn model trong bảng giá đang liệt kê **GPT-4o, o3, o4-mini** — sót lại từ mẫu chung.
   Ta chỉ dùng Google, cần thay danh sách.

---

## 2. ⭐ BẢNG XÁC ĐỊNH CHỨC NĂNG → BACKEND → DỮ LIỆU

Đây là bảng được yêu cầu: *xác định chức năng → để làm backend → xác định data nào cần dùng*.

**Cách đọc:** mỗi dòng là **một endpoint backend**. Cột "Phục vụ ô nào" cho biết nó nuôi những
ô nào trên màn hình. Cột "Dữ liệu cần" ghi bảng và cột cụ thể trong database.

### Nhóm 1 — Danh mục (tra cứu, không có số liệu)

| # | Endpoint | Chức năng | Phục vụ ô nào | Dữ liệu cần | Nguồn gốc | TT |
|---|---|---|---|---|---|---|
| 1 | `GET /api/agents` | Danh sách 8 agent + ngày bắt đầu có dữ liệu | `m-ov-agents`, `m-ag-active`, `m-ag-idle` | `dim_agent` toàn bộ | gcloud + khai báo tay | ✅ |
| 2 | `GET /api/units` | Cây tổ chức, dạng cây | `dept-tree-table`, ô lọc phòng ban | `dim_unit(unit_id, ten, parent_id, cap)` | CTDA 108 + TLA HĐ 20 | ✅ |
| 3 | `GET /api/users` | Danh sách tài khoản được cấp | `m-dep-users`, `m-us-total` | `dim_user` toàn bộ | CTDA 890 + TLA HĐ 42 | ✅ |
| 4 | `GET /api/models` | Model + đơn giá đang hiệu lực | `m-md-total`, `m-md-cheap`, `m-md-exp` | `dim_model` ⋈ `ref_price` | suy ngược từ chi phí | ⚠️ giá chưa ai xác nhận |

### Nhóm 2 — Tổng hợp (dùng chung cho nhiều tab)

| # | Endpoint | Chức năng | Phục vụ ô nào | Dữ liệu cần | Nguồn gốc | TT |
|---|---|---|---|---|---|---|
| 5 | `GET /api/summary?from&to&agent&unit` | 8 con số đầu tab Tổng quan | `m-ov-*` (8 ô) | `fact_billing_daily` + `fact_monitoring` + `dim_user` | Google | ✅ |
| 6 | `GET /api/timeseries?metric&bucket&from&to` | Chuỗi thời gian: chi phí / request / token | `c-ov-cost-trend`, `c-ov-request-trend`, `c-ov-token-trend`, `c-co-trend` | `fact_billing_daily` (ngày) · `fact_monitoring` (giờ) | Google | ✅ |
| 7 | `GET /api/heatmap?from&to` | Nhiệt đồ giờ × thứ | `heatmap-ov-week` | `fact_monitoring` gộp theo giờ | Monitoring | ✅ |
| 8 | `GET /api/breakdown?dim=agent\|unit\|model\|user` | Mọi biểu đồ tròn / cột phân bổ | `c-ov-agent-share`, `c-ov-unit-cost`, `c-dep-cost`, `c-ag-usage`, `c-pv-share`, `c-pv-cost`, `c-md-token`, `c-md-cost`, `c-co-dim` | `fact_usage_daily` gộp theo chiều | Google + app | ⚠️ chiều `unit`/`user` chỉ có 2/8 agent |
| 9 | `GET /api/detail?groupby&from&to` | Bảng chi tiết có sắp xếp | bảng tab 1, 3, 5, 6 | như trên | | ⚠️ như trên |
| 10 | `GET /api/matrix?rows&cols&from&to` | Ma trận 2 chiều dạng cây | `dept-tree-table`, `matrix-tree-table`, `pm-tree-table` | `fact_usage_daily` ⋈ `dim_unit` | | ⚠️ như trên |

### Nhóm 3 — Người dùng (tab Phòng ban & User)

| # | Endpoint | Chức năng | Phục vụ ô nào | Dữ liệu cần | Nguồn gốc | TT |
|---|---|---|---|---|---|---|
| 11 | `GET /api/users/adoption` | Được cấp / đã dùng / tỷ lệ | `m-us-adoption`, `c-dep-adopt`, `c-us-adopt-all` | `dim_user` LEFT JOIN `fact_usage_daily` | app | ⚠️ 2/8 |
| 12 | `GET /api/users/inactive` | Tài khoản chưa dùng bao giờ + số ngày im | `m-us-inactive`, `c-us-idle`, bảng tab 2 | `dim_user` LEFT JOIN fact | app | ⚠️ 2/8 |
| 13 | `GET /api/users/daily-active` | Số người hoạt động theo ngày | `c-us-dau` | `fact_call` gộp theo ngày | **chỉ Ralli** có mức lời gọi | ⚠️ 1/8 |
| 14 | `GET /api/users/new` | Tài khoản cấp mới trong kỳ | `m-us-new` | `dim_user.ngay_tao` | CTDA có 890/890 | ◐ TLA HĐ chưa có |
| 15 | `GET /api/units/top` | Phòng năng suất nhất | `m-dep-top`, `m-dep-count`, `m-us-units` | `fact_usage_daily` ⋈ `dim_unit` | | ⚠️ 2/8 |

### Nhóm 4 — Chi phí (tab Chi phí)

| # | Endpoint | Chức năng | Phục vụ ô nào | Dữ liệu cần | Nguồn gốc | TT |
|---|---|---|---|---|---|---|
| 16 | `GET /api/cost/summary?from&to` | Tổng chi phí VNĐ, chi phí/1.000 lượt, mức tập trung | `m-co-total`, `m-co-perk`, `m-co-conc`, `m-ov-cost`, `m-ov-costuser`, `m-pv-cost` | `fact_billing_daily` × `ref_fx` | Billing | ⚠️ thiếu tỷ giá |
| 17 | `GET /api/cost/budget?thang` | % ngân sách đã dùng theo agent | `m-co-budget`, `c-co-agent-budget` | `ref_budget` ⋈ `fact_billing_daily` | khai báo tay | ⚠️ thiếu Ralli + Tools Quizzer |
| 18 | `GET /api/cost/by-unit-timeseries` | Chi phí theo thời gian của từng phòng ban | `c-co-dept-trend` | `fact_usage_daily(nguon='app')` | app | ⚠️ 2/8 |

### Nhóm 5 — Hiệu năng (tab Hiệu năng)

| # | Endpoint | Chức năng | Phục vụ ô nào | Dữ liệu cần | Nguồn gốc | TT |
|---|---|---|---|---|---|---|
| 19 | `GET /api/perf/summary?from&to` | Request, tỷ lệ thành công, 4xx, 5xx, 429, p95, p99 | `m-pf-*` (7 ô) | `fact_monitoring` lọc `dich_vu=generativelanguage` | Monitoring | ✅ **số thật** |
| 20 | `GET /api/perf/codes?from&to` | Phân bố mã trả về theo thời gian | `c-pf-code`, `c-ov-success` | `fact_monitoring.ma_tra_ve` | Monitoring | ✅ |
| 21 | `GET /api/perf/by-agent?from&to` | Tỷ lệ lỗi và độ trễ từng agent | `c-pf-err`, `m-ov-error`, `m-pv-latency`, bảng tab 6 | `fact_monitoring` gộp theo project | Monitoring | ✅ |

### Nhóm 6 — Cấu hình (đọc và ghi)

| # | Endpoint | Chức năng | Phục vụ ô nào | Dữ liệu cần | Nguồn gốc | TT |
|---|---|---|---|---|---|---|
| 22 | `GET/PUT /api/config/price` | Bảng giá theo model, có hiệu lực từ ngày | tab Provider & Model | `ref_price` | | ⚠️ |
| 23 | `GET/PUT /api/config/fx` | Tỷ giá VNĐ theo ngày | mọi ô hiển thị VNĐ | `ref_fx` | | ❌ chưa có nguồn |
| 24 | `GET/PUT /api/config/budget` | Ngân sách tháng theo agent | `m-co-budget` | `ref_budget` | | ⚠️ |

### Tổng kết mức sẵn sàng của backend

```
   ✅  làm được ngay, dữ liệu đầy đủ         9 / 24 endpoint   (38%)
   ⚠️  làm được, nhưng dữ liệu thiếu một phần 13 / 24 endpoint  (54%)
   ◐   được một nửa                          1 / 24 endpoint   ( 4%)
   ❌  chưa có nguồn dữ liệu                  1 / 24 endpoint   ( 4%)
```

**Điểm quan trọng:** không endpoint nào bị chặn hoàn toàn trừ `/api/config/fx` — và cái đó
chỉ cần một quyết định nội bộ, không cần chờ ai. 13 endpoint ⚠️ đều **chạy được ngay**, chỉ là
chiều `phòng ban`/`người dùng` sẽ trống với 6 agent — đúng như A1 đã chấp nhận.

### Quy ước bắt buộc cho MỌI phản hồi

```json
{
  "du_lieu":  [ ... ],
  "sieu_du_lieu": {
    "nguon":       "billing",
    "do_tin_cay":  "cao",
    "kem_theo":    ["6 agent khong co chieu phong ban"],
    "khoang_that": { "tu": "2026-07-01", "den": "2026-08-04" }
  }
}
```

Không có khối `sieu_du_lieu` thì người xem không phân biệt được **số đo** với **số ước tính** —
đó chính là lỗi mà dashboard hiện tại đang mắc và phải tự dán nhãn cảnh báo để chữa.

---

## 3. Kỳ báo cáo — có hợp với prototype hiện tại không

**Câu trả lời: có, và không cần thêm nút nào.**

Prototype đã có sẵn `RANGE_PRESETS = 7 / 30 / 90 / Tất cả`, tính lùi từ hôm nay:

| Preset | Lùi tới | Có bao nhiêu agent tồn tại | Dùng được không |
|---|---|---|---|
| 7 ngày | 31/07 | 7/7 | ✅ |
| 30 ngày | 08/07 | 7/7 | ✅ |
| **90 ngày** | **09/05** | **3/7** | ⚠️ so sánh sẽ sai lệch |
| **Tất cả** | 01/01 | **3/7** | ⚠️ như trên |

Nghĩa là hai preset đầu **đã tương đương "kỳ chuẩn"**, hai preset sau **đã tương đương "kỳ đầy đủ"**.
Việc cần làm không phải thêm nút, mà là **thêm cảnh báo**:

> Khi đầu kỳ đang chọn **sớm hơn** ngày agent bắt đầu có dữ liệu, hiện dòng nhắc:
> *"Sale Agent và Contact Center có dữ liệu từ 01/01; 5 agent còn lại chỉ từ tháng 7 —
> so sánh trực tiếp sẽ thiên lệch."*

Để làm được, `dim_agent` phải có cột `ngay_bat_dau_co_du_lieu`, và endpoint số 1 phải trả nó ra.

**Số liệu chứng minh — tại sao không nên cắt cứng ở 01/07:**

```
   project                    01    02    03    04    05    06    07    08
   tranquil-post (Sale)     5.12  4.68 10.85 18.88 20.65 46.56 17.50  1.10
   pro-tuner (Contact)     13.15 12.67  8.25  8.30 13.41 20.72 15.63  1.63
   multimodal-invoice       0.01  0.04  0.69  1.24  1.82  2.02 11.56     -
   ai-chatbot-contract         -     -     -     -     -     -  6.42  9.45
   crm-500509                  -     -     -     -     -     - 11.87  0.53
   feedback-dms                -     -     -     -     -     -  6.16     -
   tools-quizz                 -     -     -     -     -  0.04     -     -
```

Cắt cứng ở 01/07 sẽ vứt **$189,10 hoá đơn thật của Google** (69,8% tổng chi phí) của 3 agent cũ.
Database chứa hết; tầng hiển thị chọn kỳ. Không mất gì mà vẫn tránh được so sánh sai.

---

## 4. Thiết kế Database

### 4.1. Ba lớp

```
   LỚP 1  RAW     chép y nguyên từ nguồn, KHÔNG sửa gì
              ↓
   LỚP 2  CORE    chuẩn hoá về một khung chung
              ↓
   LỚP 3  MART    view dọn sẵn cho từng endpoint ở §2
```

Tách ba lớp vì chúng **hỏng theo ba kiểu khác nhau**: lấy lại RAW tốn hàng phút gọi mạng và chỉ
lấy được trong khoảng Google còn giữ; đổi quy ước ở CORE tốn vài giây và chạy lại được vô hạn.
Gộp chúng nghĩa là sửa một quy ước phải tải lại 240 ngày dữ liệu.

### 4.2. Bảng danh mục

```sql
-- KHÔNG dùng SERIAL ở bất kỳ đâu (sửa 09/08). dim_agent 8 dòng và dim_model 10
-- dòng vốn đã gõ tay, nên khoá tự sinh không mang lại gì ngoài việc số ID đổi mỗi
-- lần nạp lại. Bỏ SERIAL thì cùng một file SQL chạy được cả PostgreSQL lẫn SQLite,
-- nhờ đó kiểm được toàn bộ khâu nạp khi Docker chưa chạy.
CREATE TABLE dim_agent (
    agent_id        INT PRIMARY KEY,
    ma              TEXT UNIQUE NOT NULL,
    ten             TEXT NOT NULL,
    gcp_project_id  TEXT,                 -- NULL với Ralli (không qua GCP)
    co_cay_to_chuc  BOOLEAN NOT NULL,     -- chỉ TLA HĐ và Ralli = true  (A1)
    ngay_tao_project DATE,                -- từ gcloud projects list
    ngay_bat_dau_co_du_lieu DATE NOT NULL,-- dùng cho cảnh báo ở §3
    ngay_ket_thuc_du_lieu   DATE,         -- NULL = còn chạy          (thêm 09/08)
    dang_van_hanh   BOOLEAN NOT NULL,
    -- FALSE với Ralli: không có billing lẫn monitoring để đối chứng. Không có cột
    -- này thì "không đo được" hiện ra màn hình y hệt "không có lỗi nào" (M-D).
    co_nguon_doi_chung BOOLEAN NOT NULL   --                          (thêm 09/08)
);

CREATE TABLE dim_unit (
    unit_id     TEXT PRIMARY KEY,
    agent_id    INT NOT NULL REFERENCES dim_agent,
    ten         TEXT NOT NULL,
    parent_id   TEXT REFERENCES dim_unit,
    cap         INT,
    duong_dan   TEXT,                     -- 'Công ty > Phòng BH1 > Vùng 1'
    -- TRUE với 6 dòng "Đơn vị sử dụng <agent>" và dòng "Chưa quy được".
    -- Thiếu cột này thì COUNT(*) đếm cả dòng kỹ thuật thành phòng ban thật.
    la_dong_ky_thuat BOOLEAN NOT NULL     --                          (thêm 09/08)
);

CREATE TABLE dim_user (
    user_id     TEXT,
    agent_id    INT NOT NULL REFERENCES dim_agent,
    username    TEXT NOT NULL,
    ho_ten      TEXT,
    email       TEXT,
    unit_id     TEXT REFERENCES dim_unit,
    dang_hoat_dong BOOLEAN,
    ngay_tao    TIMESTAMP,
    la_dong_ky_thuat BOOLEAN NOT NULL,    -- như trên               (thêm 09/08)
    -- 'danh ba' | 'nhat ky'. Có user_id chỉ xuất hiện trong nhật ký chứ KHÔNG có
    -- trong danh bạ (Ralli: 'system', 'admin', 'guest'). Xem §4.4b.
    nguon_gap   TEXT NOT NULL,            --                          (thêm 09/08)
    PRIMARY KEY (agent_id, user_id)
);

CREATE TABLE dim_model (
    model_id  INT PRIMARY KEY,
    ten       TEXT UNIQUE NOT NULL,       -- tên CHUẨN, dạng gạch ngang
    ho        TEXT,
    provider  TEXT NOT NULL
);

-- THÊM 08/08. Ba nguồn gọi tên model theo ba kiểu. Không có bảng này thì phải đoán
-- bằng chuỗi, mà 'gemini-embedding-001' với 'gemini-embedding-1.0' không có quy tắc
-- chuẩn hoá nào nối được với nhau. Hiện có 43 ánh xạ: billing_sku 31, monitoring 8, app 4.
CREATE TABLE dim_model_alias (
    nguon     TEXT NOT NULL,              -- 'billing_sku' | 'monitoring' | 'app'
    ten_goc   TEXT NOT NULL,
    model_id  INT NOT NULL REFERENCES dim_model,
    PRIMARY KEY (nguon, ten_goc)
);

-- Mã của app -> nhãn tiếng Việt trên màn hình.
-- Bảng này tồn tại vì hai bên gọi tên khác nhau: 'analyze' = 'Phân tích hợp đồng',
-- 'chat' = 'Hỏi đáp AI'. Phát hiện khi đối chiếu với giao diện web ngày 07/08.
CREATE TABLE dim_function (
    agent_id      INT REFERENCES dim_agent,
    ma            TEXT,
    nhan          TEXT,
    la_nguoi_dung BOOLEAN,                -- máy chạy nền = false; CẦN HỎI, xem §6
    PRIMARY KEY (agent_id, ma)
);
```

**Với 6 agent theo quyết định A1** *(chốt lại 09/08 — trước đó §2 và §4.2 nói ngược nhau,
một bên bảo để trống, một bên bảo tạo dòng giả)*:

Tạo **một** dòng `dim_unit` và **một** dòng `dim_user` cho mỗi agent:

```
    dim_unit.ten  =  'Đơn vị sử dụng '   + tên agent
    dim_user.username = 'Người dùng sử dụng ' + tên agent
    cả hai:  la_dong_ky_thuat = TRUE
```

Ba lý do, không phải một:

1. **Câu SQL dùng chung.** `JOIN dim_unit` gặp `unit_id` NULL sẽ *loại dòng đó ra*, nên
   6 agent sẽ biến mất khỏi mọi bảng phòng ban **kể cả dòng tổng** — sai mà không có gì báo.
2. **Khoá chính `fact_usage_daily` hết NULL.** Xem §4.3, đây là điều kiện để chạy được
   PostgreSQL.
3. `la_dong_ky_thuat` để `COUNT` không đếm 6 dòng này thành người thật — nếu không,
   `COUNT(*) FROM dim_user` trả 938 thay vì 932, và 6/938 trông y hệt sai số làm tròn.

### 4.3. Bảng sự kiện

**Nguyên tắc số một: mỗi nguồn một bảng riêng, không trộn.** Trộn rồi thì khi số sai sẽ không
biết sai từ nguồn nào.

```sql
-- MỘT dòng = MỘT lời gọi API. Chỉ Ralli có mức này.
CREATE TABLE fact_call (
    call_id         TEXT PRIMARY KEY,
    agent_id        INT  NOT NULL REFERENCES dim_agent,
    thoi_diem_goc   TIMESTAMP NOT NULL,   -- CHÉP NGUYÊN, chưa quy đổi
    mui_gio_da_xac_nhan BOOLEAN NOT NULL DEFAULT FALSE,
    thoi_diem_ict   TIMESTAMP,            -- điền sau khi biết câu trả lời
    user_id         TEXT,
    unit_id         TEXT REFERENCES dim_unit,
    model_id        INT  REFERENCES dim_model,
    ma_ham          TEXT,
    prompt_tokens      BIGINT,
    completion_tokens  BIGINT,
    total_tokens       BIGINT NOT NULL,   -- CỘT CHUẨN, không tự cộng hai nửa
    cached_tokens      BIGINT,            -- NULL ở 6.871 dòng cũ, KHÔNG phải 0
    dinh_dang_ban_ghi  SMALLINT           -- 1 / 2 / 3, xem §4.6
);

CREATE TABLE fact_billing_daily (
    ngay        DATE NOT NULL,            -- NGÀY THEO GIỜ MỸ (Pacific) — xem M1
    project     TEXT NOT NULL,
    sku_id      TEXT NOT NULL,
    sku_ten     TEXT NOT NULL,            -- giữ tên gốc để soát lại   (thêm 08/08)
    model_id    INT REFERENCES dim_model,
    loai        TEXT NOT NULL,            -- 'input' | 'output' | 'cached'
    so_luong    BIGINT NOT NULL,
    chi_phi_usd NUMERIC(14,6) NOT NULL,
    PRIMARY KEY (ngay, project, sku_id)
);

CREATE TABLE fact_monitoring (
    thoi_diem_utc TIMESTAMP NOT NULL,
    thoi_diem_ict TIMESTAMP NOT NULL,     -- = utc + 7h, đã kiểm đúng 525.639/525.639 dòng
    project       TEXT NOT NULL,
    phep_do       TEXT NOT NULL,
    model_id      INT REFERENCES dim_model,
    ma_tra_ve     TEXT,
    dich_vu       TEXT NOT NULL,          -- quy tắc 9: res_service, rỗng thì lấy tiền tố metric_type
    phuong_thuc   TEXT,
    credential_id TEXT,                   -- cùng phút cùng method vẫn có nhiều
                                          -- chuỗi nếu nhiều API key   (thêm 08/08)
    la_han_muc    BOOLEAN NOT NULL,       -- TRUE với *_limit: ALIGN_MAX,
                                          -- KHÔNG được SUM            (thêm 08/08)
    gia_tri       DOUBLE PRECISION NOT NULL,
    don_vi        TEXT                    --                           (thêm 08/08)
);

-- THÊM 08/08. Hai công tơ của Google không giao nhau: phép đo token có nhãn `model`
-- nhưng không có mã trả về; api_request_count có mã trả về nhưng không có model.
-- Nên số liệu hiệu năng KHÔNG nhét vào fact_usage_daily được — khoá của nó không
-- có chỗ cho ma_tra_ve. Thiếu bảng này thì /api/perf/summary và /api/perf/codes
-- không có nguồn.
CREATE TABLE fact_perf_daily (
    ngay        DATE NOT NULL,            -- ICT
    agent_id    INT NOT NULL REFERENCES dim_agent,
    phuong_thuc TEXT NOT NULL,
    ma_tra_ve   TEXT NOT NULL,
    so_luot     INT NOT NULL,
    -- p95/p99 gộp từ histogram, KHÔNG phải trung bình các phân vị từng phút.
    -- Hai cột `_o_tu`/`_o_den` là bề rộng ô chứa phân vị: trung vị bề rộng = 57%
    -- của chính giá trị p95, nên dashboard phải hiện KHOẢNG, không phải số lẻ.
    p95_giay    DOUBLE PRECISION,
    p95_o_tu    DOUBLE PRECISION,
    p95_o_den   DOUBLE PRECISION,
    p99_giay    DOUBLE PRECISION,
    du_mau      BOOLEAN NOT NULL          -- FALSE khi so_luot < 10
);

-- Bảng dashboard dùng nhiều nhất.
-- MỌI CỘT KHOÁ ĐỀU NOT NULL (sửa 09/08). Bản cũ để unit_id/user_id/model_id nhận
-- NULL, và đó là một cái bẫy im lặng: PostgreSQL coi PRIMARY KEY là NOT NULL nên
-- sẽ TỪ CHỐI dòng billing đầu tiên; còn SQLite thì cho phép NULL trong khoá chính
-- và coi NULL ≠ NULL, nên NHẬN CẢ HAI DÒNG GIỐNG HỆT NHAU. Đã thử, nó nhận thật.
-- Cách chữa: dùng dòng kỹ thuật ở dim_unit/dim_user (§4.2) thay cho NULL.
--   model_id  không bao giờ NULL — đã kiểm: cả 3 phép đo token đều có nhãn model,
--             0/12.534 + 0/12.258 + 0/14 thiếu. Phép đo thiếu model (api_request_count,
--             latencies) thuộc về fact_perf_daily chứ không vào bảng này.
CREATE TABLE fact_usage_daily (
    ngay         DATE NOT NULL,           -- NGÀY THEO ICT (M-B)
    agent_id     INT  NOT NULL REFERENCES dim_agent,
    model_id     INT  NOT NULL REFERENCES dim_model,
    unit_id      TEXT NOT NULL REFERENCES dim_unit,
    user_id      TEXT NOT NULL,
    so_luot      INT,
    total_tokens BIGINT,
    chi_phi_usd  NUMERIC(14,6),
    nguon        TEXT NOT NULL,           -- 'app' | 'billing' | 'monitoring'
    PRIMARY KEY (ngay, agent_id, model_id, unit_id, user_id, nguon)
);
```

**Bảng này chứa gì** — hỏi thật nhiều lần nên ghi hẳn ra: một dòng nghĩa là *"trong
ngày ICT 01/08, agent Sale Agent dùng model gemini-2.5-flash hết 1,2 triệu token, tốn
$3,05 — theo nguồn `billing`"*. Nó là bảng **đã cộng sẵn** để dashboard khỏi quét
525.639 dòng monitoring mỗi lần bấm chuột.

```
    fact_monitoring  525.639 dòng, mức PHÚT     ─┐
    fact_billing       2.259 dòng, mức NGÀY-Mỹ  ─┼─►  fact_usage_daily
    fact_call          7.924 dòng, mức LỜI GỌI  ─┘      mức NGÀY-ICT
```

Và một view — quyết định M-A nạp đủ rồi lọc ở tầng view:

```sql
CREATE VIEW mon_sach AS
SELECT * FROM fact_monitoring
WHERE dich_vu = 'generativelanguage.googleapis.com' AND la_han_muc = FALSE;
-- 85.166 dòng trên tổng 525.639
```

Cột **`nguon`** là cột quan trọng nhất của cả thiết kế: nó cho phép cùng một ngày có nhiều con
số từ nhiều nguồn mà không đè lên nhau — chính là cách phát hiện ra app ghi thiếu 17%.

### 4.4. Xử lý phần "Chưa quy được" (quyết định B3)

Với TLA HĐ: tổng lấy từ Google (342 lượt / 6.504.335 token), chia nhỏ lấy từ app (284 lượt /
5.380.189 token). Chênh lệch **58 lượt / 1.124.146 token** không quy được về phòng ban nào.

Cách làm: thêm **một đơn vị đặc biệt** trong `dim_unit`, không phải cột mới:

```sql
INSERT INTO dim_unit (unit_id, agent_id, ten, parent_id, cap, la_dong_ky_thuat)
VALUES ('__chua_quy_duoc__', <agent_id>, 'Chưa quy được', NULL, 0, TRUE);
```

Ưu điểm: mọi truy vấn `GROUP BY unit_id` **tự động cộng ra đúng tổng**, không cần viết ngoại lệ.
Trên màn hình nó hiện thành một dòng riêng, tô màu khác, kèm chú thích *"Google ghi nhận nhưng
ứng dụng không ghi lại được — xem §6"*.

> ### ⚠️ Sửa 09/08 — Ralli **cần** dòng này, và cần gấp 132 lần TLA HĐ
>
> Bản 07/08 viết ở §5: *"Ralli **không cần** dòng này: nó không đi qua GCP nên không có
> số Google để mà lệch."* **Sai.** Câu đó chỉ đúng nếu "chưa quy được" nghĩa là *lệch so
> với Google*. Nhưng phần lớn lượt gọi của Ralli **không gắn được với người nào ngay
> trong chính nhật ký của nó**, chẳng liên quan gì tới Google.
>
> Đo trên `data/ctda/db-token_usage-raw.json` (7.924 lời gọi, 30 `user_id` khác nhau):
>
> | Ai | Lượt | Token | Tỷ lệ token |
> |---|---:|---:|---:|
> | `system` (nhãn `legacy`) | 6.986 | 40.849.145 | **91,4%** |
> | `admin` (2 khoá, xem §4.4b) | 480 | 1.588.404 | 3,6% |
> | `None` / `guest` | 194 | 986.156 | 2,2% |
> | **→ cộng: "Chưa quy được"** | **7.660** | **43.423.705** | **97,2%** |
> | Có đơn vị thật | 264 | 1.268.796 | 2,8% |
> | **Tổng** | **7.924** | **44.692.501** | **100%** |
>
> Số tự tổng hợp của chính app xác nhận y hệt — `by_unit` của Ralli có
> `"Không xác định" = 43.423.705 token / 7.660 lượt`.
>
> **Cẩn thận: "người dùng thật" có hai định nghĩa, lệch nhau 49 lượt.** Phải nói rõ dùng
> cái nào, không thì hai chỗ trong dashboard sẽ ra hai số:
>
> ```
>     có đơn vị thật                       264 lượt   (7.924 − 7.660)
>     user_id nằm trong danh bạ 890 người  215 lượt
>     ────────────────────────────────────────────────
>     chênh                                 49 lượt
> ```
>
> 49 lượt đó thuộc về một đơn vị có thật nhưng `user_id` **không có trong danh bạ** — nhiều
> khả năng là người đã bị xoá khỏi danh sách nhưng nhật ký vẫn giữ đơn vị cũ. Chốt: đếm theo
> **`unit_id`** (264), vì đó là con số cộng ra đúng tổng; `dim_user.nguon_gap = 'nhat ky'`
> đánh dấu 49 lượt kia.
>
> **Hệ quả:** dòng "Chưa quy được" của Ralli chiếm **7.660 lượt**, so với TLA HĐ **58 lượt**.
> Tab "người dùng theo phòng ban" của Ralli sẽ là một cột chiếm 97% mang tên
> *"Tài khoản đã xoá hoặc chưa xác định"*. Đây **không phải lỗi nạp** — đó là tình trạng
> thật của dữ liệu, và bản thân con số 97% là một chỉ tiêu chất lượng đáng báo cáo.

### 4.4b. `dim_user` không nạp thuần từ danh bạ được (thêm 09/08)

`admin` của Ralli xuất hiện dưới **hai `user_id` khác nhau**: một lần là ObjectId
`69b4e9d78bc3012c1cd8cb72` (162 lượt), một lần là chuỗi `'admin'` (318 lượt). **Cả hai đều
không có trong danh bạ 890 người.** `system` và `guest` cũng vậy.

Đã chốt (09/08): **để riêng hai dòng**, không gộp. Chép nguyên trạng dữ liệu nguồn, không
diễn giải. Cột `dim_user.nguon_gap` phân biệt `'danh ba'` với `'nhat ky'` để sau này ai đọc
cũng biết dòng nào là người có thật trong hệ thống, dòng nào chỉ là một chuỗi trong log.

Vì vậy **thứ tự nạp bắt buộc**:

```
    ①  nạp danh bạ        users-list.json (890) + users-by-unit.csv (42)   nguon_gap='danh ba'
    ②  quét fact_call     bổ sung user_id chỉ có trong nhật ký            nguon_gap='nhat ky'
    ③  rồi mới nạp fact_call — lúc này mọi user_id đều đã có chỗ trỏ tới
```

Đảo thứ tự ①② với ③ thì `fact_call` sẽ có khoá ngoại trỏ vào chỗ trống.

### 4.5. Bảng cấu hình

```sql
CREATE TABLE ref_price (
    model_id    INT NOT NULL REFERENCES dim_model,
    hieu_luc_tu DATE NOT NULL,
    gia_input   NUMERIC(12,8),            -- USD / 1 triệu token
    gia_output  NUMERIC(12,8),
    gia_cached  NUMERIC(12,8),
    nguon       TEXT NOT NULL,            -- 'suy nguoc' | 'google' | 'nha cung cap'
    PRIMARY KEY (model_id, hieu_luc_tu)
);

CREATE TABLE ref_fx (
    ngay        DATE PRIMARY KEY,
    vnd_moi_usd NUMERIC(12,2) NOT NULL,
    nguon       TEXT NOT NULL             -- 'go cung' cho đến khi kéo API (M-F)
);

CREATE TABLE ref_budget (
    agent_id      INT NOT NULL REFERENCES dim_agent,
    thang         DATE NOT NULL,
    ngan_sach_usd NUMERIC(12,2),
    -- Ralli bị chặn theo TOKEN (50.000.000/tháng), 6 agent kia theo TIỀN. Không quy
    -- đổi: quy ra USD thì ngân sách trôi mỗi lần bảng giá đổi, trong khi Ralli đang
    -- bị chặn theo token thật.                                    (thêm 08/08, M-G)
    ngan_sach_token BIGINT,
    PRIMARY KEY (agent_id, thang),
    CHECK (ngan_sach_usd IS NOT NULL OR ngan_sach_token IS NOT NULL)
);
```

Cột `ref_price.nguon` phân biệt giá **suy ngược** (hiện tại) với giá **chính thức**. Không có
cột này thì sau vài tuần không ai nhớ số ở đâu ra. Đổi giá là **thêm dòng mới** theo
`hieu_luc_tu`, không sửa dòng cũ — nhờ vậy tính lại chi phí quá khứ vẫn ra đúng số cũ.

### 4.6. Bảy quy tắc nạp dữ liệu

| # | Quy tắc | Vì sao — bằng số |
|---|---|---|
| 1 | **Token và tiền luôn lấy từ billing** — *trừ ngoại lệ ở §4.6b* | App ghi thiếu **17,0% lượt gọi** và **12,9% tiền** (đo lại 09/08: app $13,81 vs hoá đơn $15,87, kỳ 07–08/2026). Monitoring đếm token lệch tới 4,2× và không tách được cached |
| 2 | **Lượt gọi, mã lỗi, độ trễ luôn lấy từ Monitoring** | Cả billing lẫn CSDL app đều không có ba trường này |
| 3 | **Luôn lọc `dich_vu = generativelanguage`** | `pro-tuner` sai **45,7×** nếu quên (lẫn Google Drive); `feedback-dms` sai 1,9× |
| 4 | **Billing: `input = SKU_input + SKU_cached`** | Billing tách 2 SKU (387 dòng cached); hai nguồn kia đã cộng sẵn |
| 5 | **Trường thiếu nạp `NULL`, không nạp `0`** | `cached_tokens` thiếu ở **6.871/7.924** dòng. Nạp 0 rồi lấy trung bình là sai 7,5 lần |
| 6 | **Dùng `total_tokens`, không tự cộng hai nửa** | Lệch 162 (Ralli) và 2.223 (TLA HĐ) |
| 7 | **Mã `499` không phải lỗi hệ thống** | Người dùng tự huỷ giữa chừng, 14 lượt. Xếp vào 4xx là đổ oan cho hệ thống |

**Ba định dạng bản ghi của Ralli** — lý do cột `dinh_dang_ban_ghi` tồn tại:

| Định dạng | Số trường | Số dòng | Khoảng | Có thêm gì |
|---|---:|---:|---|---|
| 1 | 8 | 6.871 | 14/03 → 15/07 | (nền chung) |
| 2 | 14 | 542 | 15/07 → 27/07 | `cached_tokens`, `event_type`, `pricing_mode`, 3 trường modality |
| 3 | 16 | 511 | 28/07 → 05/08 | thêm `actor_type`, `username` |

*Lưu ý khi đọc file này:* `data/ctda/db-token_usage-raw.json` có **BOM UTF-8**. Mở bằng
`encoding='utf-8'` sẽ ném `JSONDecodeError: Unexpected UTF-8 BOM`. Phải dùng `utf-8-sig`.

### 4.6b. Lưu đủ hai nguồn, hiển thị một nguồn (chốt 09/08)

Quy tắc 1 chi phối **cách nạp**. Việc **hiển thị** là quyết định riêng, và hai thứ đó tách
được nhờ cột `nguon`.

```
    BẢNG (lưu đủ)                          VIEW (hiển thị nhất quán)
    ┌──────────────────────────────┐       ┌────────────────────────────┐
    │ tla-hd · 07 · billing · 6,42 │──┐    │  agent    nguồn hiển thị   │
    │ tla-hd · 07 · app     · 5,75 │  ├───►│  6 project   billing       │
    │ tla-hd · 08 · billing · 9,45 │  │    │  TLA HĐ      app           │
    │ tla-hd · 08 · app     · 8,07 │──┘    │  Ralli       app           │
    └──────────────────────────────┘       └────────────────────────────┘
```

**Vì sao mỗi agent chỉ hiển thị một nguồn:** nếu tab Tổng quan lấy Google còn tab Người dùng
lấy app, hai tab sẽ lệch nhau 12,9% và người xem mở cạnh nhau là thấy ngay. Một dashboard tự
mâu thuẫn mất tin cậy nhanh hơn một dashboard sai đều.

**Vì sao vẫn lưu cả hai:** giữ được phép so `app ↔ billing` — chính là bộ đo phát hiện ra
12,9%, và là cách duy nhất trả lời câu *"dashboard có khớp hoá đơn Google không?"*.

**Hai điều bắt buộc kèm theo:**

1. **Ranh giới A2 phải đọc từ `dim_agent.ngay_bat_dau_co_du_lieu`** (`tla-hd = 2026-07-02`),
   **không** gõ tay một câu `WHERE` ở đâu đó. Ngoài khoảng đó, app khai **57.070.326 token /
   $55,44 mà không có hoá đơn nào** — bằng 91,4% toàn bộ token app khai của TLA HĐ, và nhiều
   hơn cả lịch sử Ralli. Quên chặn thì tổng TLA HĐ không phải thấp hơn 12,9% nữa mà **cao gấp
   4,4 lần** ($69,25 vs $15,87).
2. **Giả định chưa chứng minh, phải ghi kèm mọi biểu đồ chia theo người:** phần 17% bị bỏ sót
   được coi là **rải đều giữa các user**. Nếu hoá ra chỉ một luồng gọi mất log và luồng đó của
   riêng vài người thì tỷ lệ sẽ lệch hẳn. Cần hỏi đội TLA HĐ cùng lúc với câu về đường gọi
   không qua log.

---

## 5. Kế hoạch 3 ngày — thứ Sáu 07/08 → Chủ nhật 09/08

> Ba ngày là ngắn. Plan này **chỉ làm database và endpoint**, không nối dashboard.
> Nối dashboard là việc của tuần sau, và nó không chặn ai.

### Ngày 1 — thứ Sáu 07/08: khung + hai nguồn Google

Google là nguồn duy nhất đã sạch hoàn toàn, nên làm trước để cuối ngày có thứ chạy được.

**Sáng (3h)**

- [ ] **Dựng PostgreSQL**
      ```bash
      docker run -d --name token-ledger-db \
        -e POSTGRES_PASSWORD=doi_mat_khau -e POSTGRES_DB=token_ledger \
        -p 5432:5432 -v token_ledger_data:/var/lib/postgresql/data postgres:16
      ```
- [ ] **Viết `db/01_schema.sql`** — chép nguyên §4.2, §4.3, §4.5. Chạy, kiểm bằng `\dt`:
      phải ra đúng **14 bảng + 1 view** (6 `dim_` + 5 `fact_` + 3 `ref_` + view `mon_sach`).
      *Sửa 09/08: bản gốc ghi 12 bảng, chưa tính `dim_model_alias` và `fact_perf_daily`.*
- [ ] **Nạp `dim_agent`** — 8 dòng, gõ tay. Ngày tạo project lấy từ `gcloud projects list`:
      ```
      pro-tuner-454203-v3      19/03/2025    Chatbot Contact Center
      tranquil-post-471401-c1  07/09/2025    Sale Agent
      multimodal-invoice       15/09/2025    Multi modal AI Invoice
      tools-quizz              10/04/2026    Tools Quizzer        (dang_van_hanh = false)
      ai-chatbot-contract      20/06/2026    Trợ Lý Ảo Hợp Đồng   (co_cay_to_chuc = true)
      feedback-dms-tiep-thi    25/06/2026    Phân Loại Phản Hồi Tiếp Thị
      crm-500509               25/06/2026    Phân Loại Dữ Liệu CRM
      (không có project)       —             Trợ lý ảo Ralli      (co_cay_to_chuc = true)
      ```
- [ ] **Nạp `dim_model`** — suy từ `sku` của billing + nhãn `model` của monitoring (~10 dòng)

**Chiều (4h)**

- [ ] **`db/nap_billing.py`** → `fact_billing_daily`. Nhớ **quy tắc 4**: phân loại SKU thành
      `input` / `output` / `cached`, kiểm `cached` TRƯỚC `input` vì chuỗi
      `"cached input token"` chứa cả `"input token"`.
- [ ] **`db/nap_monitoring.py`** → `fact_monitoring`. Nhớ **quy tắc 3**: giữ cột `dich_vu`,
      **không lọc lúc nạp** — lọc ở tầng view. Nạp đủ để sau này còn kiểm chứng được.

**Nghiệm thu bắt buộc trước khi nghỉ:**
```sql
SELECT ROUND(SUM(chi_phi_usd), 4) FROM fact_billing_daily;   -- 270.9517
SELECT COUNT(*) FROM fact_billing_daily;                     -- 2259
SELECT COUNT(*) FROM fact_monitoring;                        -- 525639   (sửa 08/08, xem M-A)
SELECT COUNT(DISTINCT project) FROM fact_monitoring;         -- 7
-- kiểm view đã lọc: generativelanguage, bỏ *_limit
SELECT COUNT(*) FROM mon_sach;                               -- 85166
```
Sai một con số là dừng, tìm nguyên nhân, **không đi tiếp**.

### Ngày 2 — thứ Bảy 08/08: dữ liệu app + bảng tổng hợp

**Sáng (3h)**

- [ ] **Nạp `dim_unit`** — 108 đơn vị Ralli (`units.json`) + 20 đơn vị TLA HĐ
      (`units-tree.json`, cây 3 cấp) + 6 đơn vị giả cho 6 agent (A1)
      + **1** dòng `Chưa quy được` cho TLA HĐ (B3)

      > **Đừng nhầm hai thứ giống tên nhau.** TLA HĐ đã sẵn có một nhóm tên
      > **"Chưa xác định"** (1.327 lượt) — đó là *người dùng thật nhưng chưa gán phòng ban*.
      > Còn **"Chưa quy được"** (58 lượt) là *lời gọi Google ghi nhận mà ứng dụng không
      > ghi lại*. Hai nhóm khác hẳn nhau, phải để riêng.
      >
      > ~~Ralli **không cần** dòng này: nó không đi qua GCP nên không có số Google để mà lệch.~~
      > **SAI — sửa 09/08.** Ralli cần dòng này hơn TLA HĐ **132 lần**: 7.660 lượt so với 58.
      > Lý do không phải lệch với Google, mà là 97% lượt gọi của Ralli **không gắn được với
      > người nào ngay trong chính nhật ký của nó**. Xem §4.4.
- [ ] **Nạp `dim_user`** — 890 Ralli + 42 TLA HĐ + 6 dòng kỹ thuật + **N dòng sinh từ nhật ký**
      (`system`, `admin`×2, `guest`… — không có trong danh bạ). Thứ tự nạp bắt buộc ở §4.4b
- [ ] **Nạp `dim_function`** — kèm nhãn tiếng Việt đã biết: `analyze` = "Phân tích hợp đồng",
      `chat` = "Hỏi đáp AI". Cột `la_nguoi_dung` để `NULL` cho đến khi có câu trả lời.

**Chiều (4h)**

- [ ] **`db/nap_ralli_raw.py`** → `fact_call`, 7.924 dòng. Nhớ **quy tắc 5 và 6**.
      Điền `dinh_dang_ban_ghi` bằng cách đếm số trường của từng bản ghi.
- [ ] **`db/dung_usage_daily.sql`** — sinh `fact_usage_daily` từ ba nguồn:
      ```sql
      -- nguon='billing'  : từ fact_billing_daily, gộp theo (ngay, project, model)
      -- nguon='monitoring': từ fact_monitoring,   gộp theo (ngay, project, model)
      -- nguon='app'      : từ fact_call (Ralli) và từ file tổng hợp (TLA HĐ)
      ```

**Nghiệm thu:**
```sql
SELECT COUNT(*), SUM(total_tokens) FROM fact_call;              -- 7924 | 44692501
SELECT COUNT(*) FROM fact_call WHERE cached_tokens IS NULL;     -- 6871  (KHÔNG phải 0)
SELECT dinh_dang_ban_ghi, COUNT(*) FROM fact_call GROUP BY 1;   -- 1:6871 · 2:542 · 3:511
SELECT nguon, COUNT(*) FROM fact_usage_daily GROUP BY 1;        -- có đủ 3 nguồn
```

### Ngày 3 — Chủ nhật 09/08: view + kiểm tra + endpoint đầu tiên

**Sáng (3h)**

- [ ] **Dựng view lớp MART** cho 5 endpoint dễ nhất và có giá trị nhất:
      `/api/agents`, `/api/summary`, `/api/timeseries`, `/api/perf/summary`, `/api/perf/codes`
- [ ] **Chuyển `test/kiem_tra_du_lieu.py` sang chạy trên database.**
      Kết quả phải **y hệt** lúc chạy trên file — đây là phép kiểm mạnh nhất cho khâu nạp.
      Nếu lệch thì lệch nằm ở bước nạp, không phải ở dữ liệu.

**Chiều (4h)**

- [ ] **Dựng FastAPI**, mở 5 endpoint trên. Mỗi phản hồi kèm khối `sieu_du_lieu` như §2.
- [ ] **Thêm phép kiểm mới:** so `nguon='app'` với `nguon='billing'` cùng ngày cùng agent
      → tự động phát hiện lại khoảng chênh 17% mỗi lần nạp
- [ ] **Viết `db/README.md`** — cách dựng lại từ số không trong 10 phút

**Nghiệm thu cuối tuần:**
```bash
curl 'localhost:8000/api/perf/summary?from=2026-07-01&to=2026-08-04'
# phải trả 17.375 request, tỷ lệ lỗi < 0,2%, và khối sieu_du_lieu đầy đủ
```

### Nếu chậm tiến độ — thứ tự hy sinh

```
   1. Bỏ FastAPI, chỉ để lại view SQL      -> dashboard vẫn đọc được qua psql
   2. Bỏ fact_call của Ralli               -> mất tab Người dùng theo ngày
   3. Bỏ fact_usage_daily nguồn 'app'      -> mất chiều phòng ban, giữ được tổng
   TUYỆT ĐỐI KHÔNG bỏ: fact_billing_daily + fact_monitoring
```

Hai bảng cuối là nền của 9/24 endpoint đã sẵn sàng — bỏ chúng là mất tất cả.

---

## 6. Vấn đề còn treo

### ~~Cần trả lời trước khi nối dashboard~~ — ĐÃ TRẢ LỜI HẾT (09/08)

| # | Câu hỏi | Trả lời |
|---|---|---|
| 1 | **Tỷ giá VNĐ** lấy từ đâu? | ✅ **M-F** — gõ cứng 25.200, `ref_fx.nguon = 'go cung'`, kéo API sau |
| 2 | **Ngân sách tháng của Ralli**? | ✅ **M-G** — 50.000.000 **token**/tháng, đọc từ `token-usage-budget.json`. Chặn theo token chứ không theo tiền |
| 3 | **Bảng giá theo model** — ai xác nhận? | ✅ **M-H** — giữ nguyên bảng hiện tại, sếp duyệt. `ref_price.nguon = 'suy nguoc'` |
| 4 | **`tools-quizz`** — bỏ khỏi danh sách agent? | ✅ **09/08 — GIỮ**, đánh dấu `dang_van_hanh = FALSE`. Nạp đủ dữ liệu lịch sử, view lọc ra. Không mất $0,04 và dữ liệu tháng 6 khỏi tổng |
| 5 | **Danh sách 8 agent chính thức** | ✅ **09/08 — chốt 8 agent** đúng như `dim_agent` đang có. Xem `db/02_danh_muc.sql` |

### Chưa chặn, hỏi khi tiện

| # | Câu hỏi | Vì sao muốn biết |
|---|---|---|
| 6 | Ralli có 6 loại `function` — cái nào là **người dùng thật hỏi**, cái nào **máy chạy nền**? | Không phân biệt được thì không đếm đúng "số lượt sử dụng". Điền vào `dim_function.la_nguoi_dung` |
| 7 | ⬆️ **NÂNG THÀNH CHẶN (09/08).** `system` của Ralli là tác vụ nền gì? | Bản 07/08 ghi *"134 dòng"* — **đếm thiếu 52 lần**. Đó chỉ là số dòng có `actor_type='system'`. Tính cả `username='system'` (nhãn `legacy`) thì là **6.986 lượt / 40.849.145 token = 91,4% toàn bộ Ralli**. Không biết nó là gì thì tab người dùng của Ralli vô nghĩa |
| 8 | TLA HĐ có 53% lưu lượng thuộc "Chưa xác định" (1.327/2.833 lượt) — là ai? | Đây là nhóm lớn nhất, chưa biết nó là người hay là máy |
| 9 | `multimodal-invoice` không có dữ liệu sau 25/07 — dừng hẳn hay tạm nghỉ? | Quyết định `dang_van_hanh` |
| 10 | Agent nào gọi `gemini-embedding-001` ($6,39)? | Đang không thuộc agent nào |
| 11 | `timestamp` của Ralli là UTC hay giờ VN? | Lệch 7 tiếng. Đã có cột `mui_gio_da_xac_nhan` để chờ, không chặn việc nạp |

### Rủi ro

| Rủi ro | Khả năng | Cách phòng |
|---|---|---|
| Cào lại đè mất ảnh chụp cũ | **Cao** | Đổi `data/ctda/` và `data/tla-hd/` sang thư mục có ngày, giống Monitoring đã làm. `date_from` bị cả 2 app bỏ qua nên quá khứ không lấy lại được |
| Múi giờ Ralli sai | Trung bình | Lưu `thoi_diem_goc` nguyên trạng + cờ. Có câu trả lời thì chạy một câu `UPDATE`, không nạp lại |
| Giá suy ngược sai | Thấp | `ref_price.nguon = 'suy nguoc'`; đổi giá là thêm dòng theo `hieu_luc_tu` |
| 3 ngày không đủ | **Cao** | Đã có thứ tự hy sinh ở §5 |

---

*Số liệu về dashboard trích từ `test/trich_yeu_cau_dashboard.py`. Số liệu về dữ liệu trích từ
`test/kiem_ke_de_len_plan.py` và `test/pham_vi_moi.py`. Kết luận về độ chính xác từ
`test/kiem_tra_du_lieu.py`, `test/chan_doan_loi.py`, `test/doi_chieu_tla_hd.py`,
`test/doi_chieu_web_vs_file.py`. Tất cả chỉ đọc, chạy lại được.*
