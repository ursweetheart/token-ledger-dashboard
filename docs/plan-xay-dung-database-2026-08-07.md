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
| **A3** | Chỗ nào Google và app không khớp thì **lấy Google** | Xoá bỏ vấn đề "app ghi thiếu 17%" |
| **B3** | Phần không quy được về ai → để thành **dòng riêng "Chưa quy được"**, không phân bổ | Trung thực, và bản thân nó là một chỉ tiêu chất lượng dữ liệu |

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
CREATE TABLE dim_agent (
    agent_id        SERIAL PRIMARY KEY,
    ma              TEXT UNIQUE NOT NULL,
    ten             TEXT NOT NULL,
    gcp_project_id  TEXT,                 -- NULL với Ralli (không qua GCP)
    co_cay_to_chuc  BOOLEAN NOT NULL,     -- chỉ TLA HĐ và Ralli = true  (A1)
    ngay_tao_project DATE,                -- từ gcloud projects list
    ngay_bat_dau_co_du_lieu DATE NOT NULL,-- dùng cho cảnh báo ở §3
    dang_van_hanh   BOOLEAN NOT NULL
);

CREATE TABLE dim_unit (
    unit_id     TEXT PRIMARY KEY,
    agent_id    INT REFERENCES dim_agent,
    ten         TEXT NOT NULL,
    parent_id   TEXT REFERENCES dim_unit,
    cap         INT,
    duong_dan   TEXT                      -- 'Công ty > Phòng BH1 > Vùng 1'
);

CREATE TABLE dim_user (
    user_id     TEXT,
    agent_id    INT REFERENCES dim_agent,
    username    TEXT NOT NULL,
    ho_ten      TEXT,
    email       TEXT,
    unit_id     TEXT REFERENCES dim_unit,
    dang_hoat_dong BOOLEAN,
    ngay_tao    TIMESTAMP,
    PRIMARY KEY (agent_id, user_id)
);

CREATE TABLE dim_model (
    model_id  SERIAL PRIMARY KEY,
    ten       TEXT UNIQUE NOT NULL,
    ho        TEXT,
    provider  TEXT DEFAULT 'Google'
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

**Với 6 agent theo quyết định A1:** vẫn tạo **một** dòng `dim_unit` và **một** dòng `dim_user`
cho mỗi agent, tên đặt bằng tên project. Làm vậy để mọi truy vấn dùng chung một câu SQL,
không phải viết hai nhánh `IF`.

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
    ngay        DATE NOT NULL,
    project     TEXT NOT NULL,
    sku_id      TEXT NOT NULL,
    model_id    INT REFERENCES dim_model,
    loai        TEXT NOT NULL,            -- 'input' | 'output' | 'cached'
    so_luong    BIGINT NOT NULL,
    chi_phi_usd NUMERIC(14,6) NOT NULL,
    PRIMARY KEY (ngay, project, sku_id)
);

CREATE TABLE fact_monitoring (
    thoi_diem_utc TIMESTAMP NOT NULL,
    thoi_diem_ict TIMESTAMP NOT NULL,     -- = utc + 7h, đã kiểm đúng 100% dòng
    project       TEXT NOT NULL,
    phep_do       TEXT NOT NULL,
    model_id      INT REFERENCES dim_model,
    ma_tra_ve     TEXT,
    dich_vu       TEXT NOT NULL,          -- BẮT BUỘC lọc, xem quy tắc 3
    phuong_thuc   TEXT,
    gia_tri       DOUBLE PRECISION NOT NULL
);

-- Bảng dashboard dùng nhiều nhất.
CREATE TABLE fact_usage_daily (
    ngay         DATE NOT NULL,
    agent_id     INT  NOT NULL REFERENCES dim_agent,
    model_id     INT  REFERENCES dim_model,
    unit_id      TEXT REFERENCES dim_unit,
    user_id      TEXT,
    so_luot      INT,
    total_tokens BIGINT,
    chi_phi_usd  NUMERIC(14,6),
    nguon        TEXT NOT NULL,           -- 'app' | 'billing' | 'monitoring'
    PRIMARY KEY (ngay, agent_id, model_id, unit_id, user_id, nguon)
);
```

Cột **`nguon`** là cột quan trọng nhất của cả thiết kế: nó cho phép cùng một ngày có nhiều con
số từ nhiều nguồn mà không đè lên nhau — chính là cách phát hiện ra app ghi thiếu 17%.

### 4.4. Xử lý phần "Chưa quy được" (quyết định B3)

Với TLA HĐ: tổng lấy từ Google (342 lượt / 6.504.335 token), chia nhỏ lấy từ app (284 lượt /
5.380.189 token). Chênh lệch **58 lượt / 1.124.146 token** không quy được về phòng ban nào.

Cách làm: thêm **một đơn vị đặc biệt** trong `dim_unit`, không phải cột mới:

```sql
INSERT INTO dim_unit (unit_id, agent_id, ten, parent_id, cap)
VALUES ('__chua_quy_duoc__', <tla_hd>, 'Chưa quy được', NULL, 0);
```

Ưu điểm: mọi truy vấn `GROUP BY unit_id` **tự động cộng ra đúng tổng**, không cần viết ngoại lệ.
Trên màn hình nó hiện thành một dòng riêng, tô màu khác, kèm chú thích *"Google ghi nhận nhưng
ứng dụng không ghi lại được — xem §6"*.

### 4.5. Bảng cấu hình

```sql
CREATE TABLE ref_price (
    model_id    INT REFERENCES dim_model,
    hieu_luc_tu DATE NOT NULL,
    gia_input   NUMERIC(10,6),            -- USD / 1 triệu token
    gia_output  NUMERIC(10,6),
    gia_cached  NUMERIC(10,6),
    nguon       TEXT,                     -- 'suy nguoc' | 'google' | 'nha cung cap'
    PRIMARY KEY (model_id, hieu_luc_tu)
);

CREATE TABLE ref_fx (
    ngay        DATE PRIMARY KEY,
    vnd_moi_usd NUMERIC(10,2) NOT NULL,
    nguon       TEXT
);

CREATE TABLE ref_budget (
    agent_id      INT REFERENCES dim_agent,
    thang         DATE NOT NULL,
    ngan_sach_usd NUMERIC(10,2) NOT NULL,
    PRIMARY KEY (agent_id, thang)
);
```

Cột `ref_price.nguon` phân biệt giá **suy ngược** (hiện tại) với giá **chính thức**. Không có
cột này thì sau vài tuần không ai nhớ số ở đâu ra. Đổi giá là **thêm dòng mới** theo
`hieu_luc_tu`, không sửa dòng cũ — nhờ vậy tính lại chi phí quá khứ vẫn ra đúng số cũ.

### 4.6. Bảy quy tắc nạp dữ liệu

| # | Quy tắc | Vì sao — bằng số |
|---|---|---|
| 1 | **Token và tiền luôn lấy từ billing** | App ghi thiếu 17,3%; Monitoring đếm token lệch tới 4,2× và không tách được cached |
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
      phải ra đúng **12 bảng** (5 `dim_` + 4 `fact_` + 3 `ref_`).
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
SELECT COUNT(*) FROM fact_monitoring;                        -- 85166
SELECT COUNT(DISTINCT project) FROM fact_monitoring;         -- 7
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
      > Ralli **không cần** dòng này: nó không đi qua GCP nên không có số Google để mà lệch.
- [ ] **Nạp `dim_user`** — 890 Ralli + 42 TLA HĐ + 6 user giả cho 6 agent
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

### Cần trả lời trước khi nối dashboard

| # | Câu hỏi | Chặn cái gì |
|---|---|---|
| 1 | **Tỷ giá VNĐ** lấy từ đâu, cập nhật thế nào? | Mọi ô hiển thị VNĐ — hiện gõ cứng 25.200 |
| 2 | **Ngân sách tháng của Ralli** là bao nhiêu? | `m-co-budget` đang tính trên mẫu số sai |
| 3 | **Bảng giá theo model** — ai xác nhận? | Hiện suy ngược từ chi phí, ra số tròn đẹp nhưng chưa ai duyệt |
| 4 | **`tools-quizz`** — bỏ hẳn khỏi danh sách agent? | Từ 01/07 chỉ còn 3 lượt gọi; để lại làm méo tỷ lệ lỗi toàn hệ thống |
| 5 | **Danh sách 8 agent chính thức** + project nào ứng với agent nào | Hiện suy từ tên file billing, chưa ai xác nhận |

### Chưa chặn, hỏi khi tiện

| # | Câu hỏi | Vì sao muốn biết |
|---|---|---|
| 6 | Ralli có 6 loại `function` — cái nào là **người dùng thật hỏi**, cái nào **máy chạy nền**? | Không phân biệt được thì không đếm đúng "số lượt sử dụng". Điền vào `dim_function.la_nguoi_dung` |
| 7 | `actor_type = 'system'` (134 dòng) là tác vụ nền gì? | Có nên tính vào lưu lượng người dùng không |
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
