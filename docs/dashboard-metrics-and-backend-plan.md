# Token Ledger Dashboard — Chỉ tiêu & Kế hoạch Backend

> Tài liệu tổng hợp toàn bộ **chỉ tiêu (metrics/KPI)** đang được đo đạc trên dashboard,
> phân loại theo **entity** và **tab**, đồng thời đề xuất **kiến trúc backend** để thay thế
> nhập liệu thủ công bằng pipeline tự động.
>
> Cập nhật lần cuối: 2026-08-03 — bổ sung Phần VI (đối chiếu chỉ tiêu ↔ schema) và
> sửa schema Phần IV theo kết quả đối chiếu.

---

## Phần I — Trạng thái hiện tại của dự án

### Kiến trúc

| Hạng mục | Giá trị |
|---|---|
| **Frontend** | Single-page HTML + vanilla JS (`app.js` ~2.300 dòng), Chart.js offline |
| **Lưu trữ** | `localStorage` trên trình duyệt (key `agent-dash-state-v12-ralli-permissions`) |
| **Nhập dữ liệu** | Thủ công theo ngày: nhập từ file Excel → paste vào form trên dashboard |
| **Tính chi phí** | `(token_in ÷ 1M × giá_in) + (token_out ÷ 1M × giá_out)`, quy VNĐ theo tỷ giá 25.200 |
| **Seed data** | Tháng 6/2026 (4 tuần) + tháng 7/2026 (4 tuần) — hardcode trong `app.js` từ Excel |
| **Cây tổ chức** | Hardcode `ORG_UNITS[]` (>90 đơn vị, 5 cấp) + `UNIT_ALIASES{}` — 887 user phân quyền |
| **Tài khoản user** | Demo — phân bổ (allocated), không phải số đo. Nhãn `Dữ liệu phân bổ (demo)` |

### Các file dữ liệu nguồn (`data/`)

| File | Nội dung | Cách sử dụng hiện tại |
|---|---|---|
| `Bảng tổng hợp chi phí token AI agent tháng 7 (3).xlsx` | 4 sheet tuần (01, 08, 15, 22/07): token in/out, request, error%, latency, user phân quyền theo agent × phòng ban | Đọc thủ công → hardcode thành `SEED_DAYS{}` trong `app.js` |
| `20240806 Chuẩn hóa định dạng dashboard_RD Revised.xlsx` | Danh mục viết tắt chuẩn công ty (BH1→Phòng Bán hàng 1, TMDT→Thương mại điện tử...), cấu trúc phòng ban cấp Kênh/Vùng/Tỉnh | Dùng để xây `UNIT_ALIASES{}` và xác nhận cấp drilldown |

**Vấn đề quan trọng từ dữ liệu:**
- Mỗi agent dùng **quy ước đặt tên phòng ban khác nhau** trong Excel (PBH1 vs Phòng Bán hàng 1, TMĐT vs Thương mại điện tử) → cần `UNIT_ALIASES` để chuẩn hóa
- File usage **không có userId** — mỗi dòng là tổng theo `agent × phòng_ban × model` → không thể quy về từng user thật
- Số user (`u`) là số **ĐÃ CẤP** (snapshot), không phải active → chỉ gắn vào Tuần 1 để tránh cộng trùng
- Cây phân quyền Ralli có **887 user** nhưng các agent khác không có dữ liệu phân quyền chi tiết

### 6 Tab trên dashboard

1. 📊 **Tổng quan** (`overview`)
2. 🏢 **Phòng ban & User** (`departments` — Departments + Users đã gộp)
3. 🤖 **Agents** (`agents`)
4. 🏭 **Provider & Model** (`providers` — hai tab cũ đã gộp, provider là cấp cha của model)
5. 💸 **Chi phí** (`cost`)
6. ⚡ **Hiệu năng** (`performance`)

### Bộ lọc toàn cục

- Khoảng thời gian (Từ → Đến + preset 7/30/90 ngày/Tất cả) — nằm trên toolbar
- 5 bộ lọc trên filter bar: Phòng ban, User, Provider, Model, Agent

### Danh sách Agent hiện tại (7 agents)

| Agent | Phòng ban chính | Model chính | Ngân sách tháng (USD) |
|---|---|---|---|
| Trợ Lý Ảo Hợp Đồng | Cty CPBĐ PN, PBH1–3, C4LED, TT&TMĐT, TTDL&DHS | Gemini 2.5 Flash, 2.5 Pro | 20 |
| Chatbot Contact Center | CSKH, Thương mại điện tử | Gemini 2.5 Flash, 3.0 Flash, 3.1 Flash Lite | 30 |
| Phân Loại Dữ Liệu CRM | P.NCTT, TTDL&ĐHS | Gemini 2.5 Flash | 20 |
| Phân Loại Phản Hồi Tiếp Thị | P.NCTT, TTDL&ĐHS | Gemini 2.5 Flash | 20 |
| Multi modal AI Invoice | — | — | 20 |
| Sale Agent | Anh Em tiếp thị | Gemini 2.5 Flash | 50 |
| Trợ lý ảo Ralli | Toàn công ty (887 user phân quyền) | Gemini 2.5 Flash | — (chưa cấp budget riêng) |

**Tổng ngân sách tháng: 160 USD ≈ 4.032.000 VNĐ** (6 agents có budget; Ralli chưa có)

### Yêu cầu cải tiến từ cuộc họp 25/7/2026

Dựa trên `nội_dung_cuộc_họp_25_7.txt`:

| # | Yêu cầu | Ảnh hưởng tới backend |
|---|---|---|
| 1 | Ghi rõ % tăng giảm là so với kỳ trước (KT) hay cùng kỳ (CK) | API cần trả cả giá trị kỳ trước lẫn cùng kỳ |
| 2 | Cần % hoạt động User (user sử dụng / tổng user) | Cần `userId` thật để tính chính xác |
| 3 | Track số user hoạt động đối với Agent cần đăng nhập | Backend ingestion cần log userId per request |
| 4 | Gộp tab Phòng ban & User, xem user trong phòng ban | API `/departments` trả drilldown tới user |
| 5 | Bộ lọc theo User (toàn dashboard) | API cần filter param `user=` |
| 6 | Cảnh báo chi phí: cao hơn 30% trung bình → cảnh báo | Backend tính trung bình rolling, so sánh |
| 7 | Bảng chi phí theo kỳ muốn xem theo từng agent | API `/cost` cần `groupby=agent` + filter |
| 8 | Vẫn phải nhập số thủ công trên file Excel | Excel Import API là **bắt buộc** ở Phase 1 |

---

## Phần II — Các Entity (thực thể dữ liệu)

Toàn bộ dashboard xoay quanh **6 entity chính**:

```
┌──────────────────────────────────────────────────────────────┐
│                      DATA MODEL HIỆN TẠI                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌───────────┐    ┌───────────┐             │
│  │ Provider │───▶│   Model   │───▶│   Agent   │             │
│  │ suy ra từ│    │(+ pricing)│    │(= project)│             │
│  │ tên model│    └───────────┘    └─────┬─────┘             │
│  └──────────┘                           │                    │
│                                  ┌──────┴───────┐           │
│                                  │  Usage Row   │           │
│                                  │  (per day ×  │           │
│                                  │  agent ×     │           │
│                                  │  dept ×      │           │
│                                  │  model)      │           │
│                                  └──────┬───────┘           │
│                                         │                    │
│                             ┌───────────┴──────────┐        │
│                             │                      │        │
│                       ┌─────┴──────┐       ┌───────┴─────┐  │
│                       │  Phòng ban │       │    User     │  │
│                       │ (ORG_UNIT  │       │  (Account   │  │
│                       │  5 cấp,    │       │   ALLOCATED │  │
│                       │  90+ đơn   │       │   demo)     │  │
│                       │  vị)       │       └─────────────┘  │
│                       └────────────┘                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Row-level data schema (1 dòng nhập liệu gốc)

| Field | Ý nghĩa | Kiểu | Ví dụ |
|---|---|---|---|
| `a` | Tên Agent (= project GCP) | string | `"Sale Agent"` |
| `d` | Phòng ban / Đơn vị (chuỗi tự do) | string | `"PBH1"`, `"Anh Em tiếp thị"` |
| `m` | Model AI đang dùng | string | `"Gemini 2.5 Flash"` |
| `ug` | User group | string | `"Nhóm Kinh doanh"` |
| `u` | Số user ĐÃ CẤP (snapshot, chỉ Tuần 1) | int | `887` |
| `c` | Số cuộc chat | int | `0` |
| `ti` | Token input | bigint | `2214480` |
| `to` | Token output | bigint | `612620` |
| `r` | Số request | int | `610` |
| `er` | Tỷ lệ lỗi (%) | float | `0.0034` |
| `lat` | Latency p95 (giây) | float | `4.5` |
| `cached` | Cached token count | bigint | `0` |
| `think` | Thinking token count | bigint | `0` |

**Provider** (`modelProvider()`) được **suy ra từ tên model**: Gemini → Google AI Studio, GPT/o → OpenAI, Claude → Anthropic, còn lại → Khác. Không có field riêng trong dữ liệu.

---

## Phần III — Chỉ tiêu theo Entity & Tab

### Entity 1: Agent

| # | Chỉ tiêu | Công thức / Định nghĩa | Tab |
|---|---|---|---|
| 1 | Số AI Agent | Đếm agent unique có ≥1 request | Tổng quan |
| 2 | Agent đang hoạt động | Agent có ≥1 request trong kỳ | Agents |
| 3 | Agent không dùng (idle) | Agent 0 request trong kỳ | Agents |
| 4 | Tổng lượt request | Σ request mọi agent | Agents |
| 5 | Chi phí TB / agent | Tổng chi phí ÷ số agent hoạt động | Agents |
| 6 | Mức độ sử dụng (donut) | Request share mỗi agent | Agents |
| 7 | Top agent theo token | Bảng xếp hạng Σ(token_in + token_out) | Agents |
| 8 | Mức sử dụng ngân sách / agent | (chi phí thực ÷ budget_usd) × 100% (bar chart) | Agents |
| 9 | Ma trận Agent × Phòng ban | Heatmap request: hàng=agent, cột=phòng ban, drilldown 3 cấp | Agents |
| 10 | Bảng chi tiết agent | Agent, Phòng ban chính, Model, Users, Requests, Tokens, Error%, p95, Trạng thái | Agents |
| 11 | Top AI Agent theo chi phí | Bar chart: ranking agent theo VNĐ | Tổng quan |
| 12 | Phân bổ chi phí theo AI Agent | Donut: tỷ trọng chi phí | Tổng quan |
| 13 | Tỉ lệ lỗi theo agent | Bar chart: error% mỗi agent | Hiệu năng |
| 14 | Hiệu năng theo agent | Bảng: Agent, Model, Requests, Success%, Error%, p95, p99 | Hiệu năng |

---

### Entity 2: Phòng ban (Department / ORG_UNIT)

| # | Chỉ tiêu | Công thức / Định nghĩa | Tab |
|---|---|---|---|
| 1 | Số phòng ban | Đếm phòng ban có agent phát sinh sử dụng | Tổng quan, Phòng ban |
| 2 | Phòng sử dụng nhiều nhất | Phòng có request hoặc chi phí cao nhất | Phòng ban |
| 3 | Chi phí TB / phòng | Tổng chi phí ÷ số phòng ban | Phòng ban |
| 4 | Mức độ tập trung chi phí | Tỷ trọng chi phí của Top-2 phòng | Phòng ban |
| 5 | Chi phí theo phòng ban (donut) | Phân bổ chi phí theo phòng | Phòng ban |
| 6 | Tỷ lệ sử dụng theo phòng ban (donut) | User hoạt động ÷ user phân quyền | Phòng ban |
| 7 | Bảng chi tiết phòng ban (drilldown) | Phòng ban, Agent, User phân quyền, User hoạt động, Tỷ lệ hoạt động, Token, Request, Tỷ lệ lỗi — accordion 3 cấp (Phòng→Vùng→User) | Phòng ban |
| 8 | Top đơn vị theo chi phí | Bar chart VNĐ | Tổng quan |
| 9 | Heatmap request 7 ngày | Agent × Ngày trong 7 ngày gần nhất | Tổng quan |

---

### Entity 3: User (Tài khoản người dùng)

> **Lưu ý:** Dữ liệu user hiện tại là **phân bổ (allocated/demo)**, không phải số đo thực.
> Nguồn usage không có `userId`, nên tầng user được sinh từ cây `ORG_UNITS` và phân bổ
> số liệu thật của phòng ban xuống theo trọng số (`weight`).

| # | Chỉ tiêu | Công thức / Định nghĩa | Tab |
|---|---|---|---|
| 1 | Tổng số tài khoản | Tổng account đã cấp (provisioned từ cây ORG_UNITS) | Phòng ban & User |
| 2 | Tài khoản hoạt động | Account có ≥1 request được phân bổ trong kỳ | Phòng ban & User, Tổng quan |
| 3 | Tài khoản không hoạt động | Account 0 request trong kỳ | Phòng ban & User |
| 4 | Cấp mới trong kỳ | Account có `created` nằm trong khoảng thời gian đang chọn | Phòng ban & User |
| 5 | Số phòng ban (user) | Phòng ban có tài khoản được cấp | Phòng ban & User |
| 6 | Chi phí / User | Tổng chi phí ÷ số user hoạt động | Tổng quan |
| 7 | % hoạt động User | Số user hoạt động ÷ tổng user phân quyền. ⚠️ Mẫu số thật (`DEPT_PROVISIONED` đếm từ `RALLI_USERS`), **tử số suy ra** từ `weight`/`adoptionRatio` (`app.js:241`) | Phòng ban & User |
| 8 | Bảng danh sách User | #, User, Role, Status, Reqs, Chi phí, Quota kỳ hiện tại. ⚠️ Quota **cả hai vế** đều suy ra: `%` = `12+(hash%80)` (`app.js:339`), hạn mức = suy ngược từ `%` (`app.js:1544`) | Phòng ban & User |
| 9 | DAU (Daily Active Users, 30d) | ⚠️ `total × (0.10 + 0.16 × req/maxReq)` — **chưa có số đo** (`app.js:2599`) | Phòng ban & User |
| 10 | DS tài khoản không hoạt động | User, Phòng ban, Lần cuối dùng. ⚠️ `last` được gán = ngày cuối kỳ (`app.js:337`); cột "Thời gian được cấp" luôn rỗng vì nguồn TLA Ralli chưa xuất | Phòng ban & User |

> **Ghi chú chung Entity User:** mọi số theo tài khoản (req, token, chi phí, active, last)
> là **số phân bổ** từ tổng của phòng ban theo `weight`, không phải số đo — xem
> `applyAccountAllocation()` (`app.js:280-341`). Chỉ **danh tính** (login, tên, phòng ban,
> vai trò, trạng thái) là dữ liệu thật từ TLA Ralli.

---

### Entity 4: Provider

| # | Chỉ tiêu | Công thức / Định nghĩa | Tab |
|---|---|---|---|
| 1 | Số provider | Provider có lưu lượng trong kỳ | Providers |
| 2 | Tỉ trọng provider lớn nhất | % token của provider chiếm nhiều nhất | Providers |
| 3 | Chi phí provider lớn nhất | Chi phí quy đổi từ token theo bảng giá | Providers |
| 4 | Độ trễ trung bình | p95 bình quân theo request | Providers |
| 5 | Phân bổ token theo Provider (donut) | Token share mỗi provider | Providers |
| 6 | Chi phí theo provider (bar) | Ranking chi phí VNĐ | Providers |
| 7 | Bảng chi tiết provider | Provider, Models, Agents, Requests, Tokens, Error%, p95, Trạng thái | Providers |

---

### Entity 5: Model

| # | Chỉ tiêu | Công thức / Định nghĩa | Tab |
|---|---|---|---|
| 1 | Tổng số model | Số model trong bảng giá (`basePricing`) | Model |
| 2 | Model chưa dùng | Model khai báo mà 0 request | Model |
| 3 | Rẻ nhất / token | Model có blended price thấp nhất | Model |
| 4 | Đắt nhất / token | Model có blended price cao nhất | Model |
| 5 | Token suy luận (thinking) | Σ `think` (thoughtsTokenCount) | Model |
| 6 | Token theo model (bar) | Token in + out mỗi model | Model |
| 7 | Chi phí theo model (bar) | Chi phí VNĐ mỗi model | Model |
| 8 | Bảng chi tiết model | Model, Provider, Agents dùng, Token in, Token out, Giá in/out, Error% | Model |

---

### Entity 6: Chi phí (Cost) — chỉ tiêu tổng hợp cross-entity

| # | Chỉ tiêu | Công thức / Định nghĩa | Tab |
|---|---|---|---|
| 1 | Tổng chi phí (VNĐ) | Σ(token × đơn giá) × tỷ giá | Tổng quan, Chi phí |
| 2 | Đã dùng ngân sách | (chi phí thực ÷ ngân sách tháng) × 100% | Chi phí |
| 3 | Mức độ tập trung chi phí | Tỷ trọng chi phí Top-2 agent | Chi phí |
| 4 | Chi phí / 1K request | Tổng chi phí ÷ (tổng request ÷ 1000) | Chi phí |
| 5 | Chi phí theo Agent/Dept/Model (donut) | Tỷ trọng, nhóm theo dropdown | Chi phí |
| 6 | Chi phí theo kỳ vs ngân sách (line) | Thực tế vs đường ngân sách tháng | Chi phí |
| 7 | Bảng chi phí (nhóm theo) | Agent/Dept/Model, Tokens, Requests, Chi phí/1K req, Chi phí VNĐ, Tỷ trọng | Chi phí |
| 8 | Xu hướng chi phí VNĐ (line) | Line chart theo ngày | Tổng quan |

---

### Entity 7: Hiệu năng (Performance) — chỉ tiêu cross-entity

| # | Chỉ tiêu | Công thức / Định nghĩa | Tab |
|---|---|---|---|
| 1 | Tỉ lệ thành công | Request thành công ÷ tổng request | Tổng quan, Hiệu năng |
| 2 | Tỷ lệ lỗi tổng | Request lỗi ÷ tổng request | Tổng quan |
| 3 | Lỗi phía gọi (4xx) | ⚠️ `error_rate × 0.64` — hệ số tạm, **chưa có số đo** (`app.js:2794`) | Hiệu năng |
| 4 | Lỗi phía máy chủ (5xx) | ⚠️ `error_rate × 0.21` — hệ số tạm, **chưa có số đo** (`app.js:2795`) | Hiệu năng |
| 5 | Chạm giới hạn tốc độ (429) | ⚠️ `error_rate × 0.15` — hệ số tạm, **chưa có số đo** (`app.js:2796`) | Hiệu năng |
| 6 | Độ trễ p95 | Mốc trễ 95% request nằm dưới — số đo thật (field `lat`) | Hiệu năng |
| 7 | Độ trễ p99 | ⚠️ `p95 × 2.1` — hệ số tạm, **chưa có số đo** (`app.js:2799`) | Hiệu năng |
| 8 | Tổng lượt request | Σ request mọi agent | Tổng quan, Hiệu năng |
| 9 | Xu hướng Token (line) | Token theo ngày | Tổng quan |
| 10 | Xu hướng Request (line) | Request theo ngày | Tổng quan |
| 11 | Request theo response code (donut) | 2xx / 4xx / 5xx / 429 | Hiệu năng |

---

### Bảng chi tiết sử dụng AI Agent (Tab Tổng quan)

| Cột | Ghi chú |
|---|---|
| AI Agent | Tên agent |
| Đơn vị | Phòng ban chính |
| User | Số user hoạt động |
| Request | Tổng lượt gọi |
| Token | Token in + out |
| Chi phí | Quy VNĐ |
| Tỷ lệ lỗi | Error % |
| Tỉ lệ thành công | 100% − Error% |

### Cảnh báo & sự kiện (Tab Tổng quan)

Logic cảnh báo dựa trên `INSIGHT_THRESHOLDS`:

| Chỉ tiêu cảnh báo | Warning | Critical |
|---|---|---|
| Token/request | > 20K | > 50K |
| Ngân sách pace | vượt 10% | gần 90% |
| Tập trung chi phí | > 50% | > 70% |
| Error rate | > 1% | > 3% |
| Adoption rate | < 60% | < 30% |
| Tài khoản không hoạt động | > 30 ngày | — |

---

## Phần IV — Kế hoạch triển khai Backend

### 1. Bối cảnh & Mục tiêu

**Hiện trạng:**
- Dashboard chạy hoàn toàn offline (HTML + JS + `localStorage`)
- Dữ liệu nhập tay từ Excel → hardcode vào `app.js` hoặc paste vào form
- **Không bền vững** (localStorage mất khi xóa cache), **không chia sẻ** (mỗi máy 1 bản), **không tự động**
- Cây tổ chức 90+ đơn vị và 887 user phân quyền đang hardcode — khó cập nhật
- Dữ liệu Excel đến theo **tuần** (4 sheet/tháng), ai đó phải đọc và nhập thủ công
- Alias phòng ban phải quản lý bằng tay trong code

**Mục tiêu backend:**
- Tự động thu thập dữ liệu token/request/lỗi từ Google Cloud APIs
- Lưu trữ tập trung, bền vững (database)
- Cung cấp REST API cho frontend → nhiều user truy cập đồng thời
- Quản lý cây tổ chức, alias, bảng giá qua giao diện (không sửa code)
- **Giữ nguyên logic tính toán hiện tại** (đã được verify với dữ liệu thật tháng 6-7/2026)

### 2. Kiến trúc đề xuất

```
┌──────────────────────────────────────────────────────────────────────┐
│                        PROPOSED ARCHITECTURE                         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  DATA SOURCES (hiện tại đang đọc thủ công)                          │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────────────┐   │
│  │ Google AI     │  │ Cloud         │  │ BigQuery               │   │
│  │ Studio API    │  │ Monitoring    │  │ Billing Export         │   │
│  │ usageMetadata │  │ error/latency │  │ cost per project       │   │
│  │  per call     │  │  ≈30 phút    │  │  ≈1 ngày              │   │
│  └───────┬───────┘  └───────┬───────┘  └────────────┬───────────┘   │
│          │                  │                        │               │
│          ▼                  ▼                        ▼               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │             DATA INGESTION (Cloud Functions / Cloud Run Jobs) │   │
│  │  • Token:    5 phút  (aggregate usageMetadata)               │   │
│  │  • Error:   30 phút  (Cloud Monitoring API)                  │   │
│  │  • Billing:  1 ngày  (BigQuery scheduled query)              │   │
│  │  • Excel:   import API (upload xlsx → parse → insert)  [NEW] │   │
│  │  • Org:      1 ngày  (sync from HR/IAM source)              │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                        │
│                             ▼                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                      DATABASE LAYER                           │   │
│  │  PostgreSQL (Cloud SQL)                                       │   │
│  │  • usage_daily (dữ liệu chính — thay localStorage)          │   │
│  │  • model_pricing (bảng giá)                                  │   │
│  │  • org_units + unit_aliases (cây tổ chức + alias)            │   │
│  │  • agent_budgets (ngân sách)                                 │   │
│  │  • user_accounts (tài khoản — khi có userId thật)            │   │
│  │  • config (tỷ giá, ngưỡng cảnh báo...)                      │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                        │
│                             ▼                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   BACKEND API (Cloud Run)                     │   │
│  │  Python FastAPI                                               │   │
│  │  • REST: /overview, /departments, /agents, /providers,       │   │
│  │          /models, /cost, /performance                        │   │
│  │  • Admin: /org-tree, /pricing, /aliases, /budgets            │   │
│  │  • Import: /upload-excel (POST multipart)                    │   │
│  │  • Auth: Google IAP                                          │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                        │
│                             ▼                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     FRONTEND (hiện tại)                        │   │
│  │  index.html + app.js (giữ nguyên giao diện)                  │   │
│  │  • Thay localStorage → fetch() gọi API                       │   │
│  │  • Thay hardcode ORG_UNITS → GET /org-tree                   │   │
│  │  • Thêm: nút Upload Excel (gọi POST /upload-excel)          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 3. Database Schema

```sql
-- ═══════════════════════════════════════════════════════════
-- Bảng chính: dữ liệu usage theo ngày
-- Tương đương state.days[date][rows] trong localStorage
-- ═══════════════════════════════════════════════════════════
CREATE TABLE usage_daily (
    id              SERIAL PRIMARY KEY,
    date            DATE NOT NULL,
    agent_name      VARCHAR(100) NOT NULL,          -- field `a`
    department_raw  VARCHAR(200),                    -- field `d` (chuỗi gốc từ Excel)
    unit_id         VARCHAR(50),                     -- resolved từ department_raw qua alias
    model           VARCHAR(100) NOT NULL,           -- field `m`
    user_group      VARCHAR(100),                    -- field `ug`
    users_provisioned INT DEFAULT 0,                 -- field `u` (snapshot, chỉ tuần 1)
    chats           INT DEFAULT 0,                   -- field `c`
    token_in        BIGINT DEFAULT 0,                -- field `ti`
    token_out       BIGINT DEFAULT 0,                -- field `to`
    requests        INT DEFAULT 0,                   -- field `r`
    error_rate      DECIMAL(8,4) DEFAULT 0,          -- field `er` (%)
    latency_p95     DECIMAL(8,2) DEFAULT 0,          -- field `lat`
    cached_tokens   BIGINT DEFAULT 0,                -- field `cached`
    think_tokens    BIGINT DEFAULT 0,                -- field `think`

    -- ── [BỔ SUNG] Tách mã phản hồi. Tab Hiệu năng có 3 thẻ KPI gắn nhãn "MỚI"
    --    (4xx/5xx/429) + donut mã phản hồi, hiện đều nhân hệ số từ error_rate.
    --    Không có 4 cột này thì backend lên xong 4 chỉ tiêu đó vẫn là số giả.
    req_2xx         INT DEFAULT 0,
    req_4xx         INT DEFAULT 0,
    req_5xx         INT DEFAULT 0,
    req_429         INT DEFAULT 0,
    -- ── [BỔ SUNG] p99 cho thẻ "Trường hợp chậm nhất" + cột cùng tên ở bảng hiệu năng.
    latency_p99     DECIMAL(8,2),

    -- ── [BỔ SUNG] Độ mịn của bucket. Excel về theo TUẦN và pipeline map "Tuần 1 → 01",
    --    "Tuần 2 → 08"… nên một dòng chứa dữ liệu CẢ TUẦN nhưng được dán nhãn và giãn
    --    cách như MỘT NGÀY trên trục thời gian (dayLabel, app.js:547). Hệ quả: preset
    --    "7 ngày" bắt đúng 1 bucket = dữ liệu cả tuần, và khi Phase 2 đổ dữ liệu ngày
    --    thật vào cùng bảng thì một trục sẽ trộn giá trị-ngày với giá trị-tuần mà API
    --    không phân biệt được. `date` = mốc đầu bucket, `period_end` = mốc cuối.
    granularity     VARCHAR(10) NOT NULL DEFAULT 'day',   -- 'day' | 'week'
    period_end      DATE,                                  -- NULL ⇒ = date (bucket 1 ngày)

    source          VARCHAR(20) DEFAULT 'manual',    -- 'manual' | 'api' | 'excel_import'
    source_file     VARCHAR(200),                    -- tên file Excel gốc (traceability)
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    -- [SỬA] Thêm user_group vào khoá. Cột `ug` tồn tại và được bộ lọc User dùng
    -- (fillSelect "f-user", app.js:3006) nhưng nằm ngoài khoá cũ ⇒ hai dòng cùng
    -- ngày/agent/phòng/model khác nhóm user sẽ đè nhau khi UPSERT.
    -- Dữ liệu seed hiện tại KHÔNG va chạm (đã kiểm: 45 dòng SEED_DAYS + 24 dòng tháng 6,
    -- 0 va chạm) — đây là rủi ro tiềm ẩn, không phải lỗi đang xảy ra.
    UNIQUE(date, agent_name, department_raw, model, user_group)
);

CREATE INDEX idx_usage_date ON usage_daily(date);
CREATE INDEX idx_usage_agent ON usage_daily(agent_name);
CREATE INDEX idx_usage_unit ON usage_daily(unit_id);

-- ═══════════════════════════════════════════════════════════
-- Bảng giá model (USD / 1 triệu token)
-- Tương đương basePricing{} trong app.js
-- ═══════════════════════════════════════════════════════════
-- [SỬA] Giá phải có hiệu lực theo thời gian. Bản cũ mỗi model 1 dòng + updated_at:
-- sửa giá hôm nay sẽ TÍNH LẠI TOÀN BỘ chi phí tháng 6 và tháng 7 — trái với mục tiêu
-- "giữ nguyên logic đã verify với dữ liệu thật tháng 6-7/2026" ở mục 1.
CREATE TABLE model_pricing (
    model           VARCHAR(100) NOT NULL,
    provider        VARCHAR(50),                     -- 'Google AI Studio', 'OpenAI', 'Anthropic'
    price_input     DECIMAL(10,4) NOT NULL,           -- USD per 1M token in
    price_output    DECIMAL(10,4) NOT NULL,           -- USD per 1M token out
    effective_from  DATE NOT NULL DEFAULT '2026-01-01',
    effective_to    DATE,                             -- NULL = còn hiệu lực
    is_active       BOOLEAN DEFAULT TRUE,             -- FALSE ⇒ vẫn đếm vào "model đã khai báo"
    updated_at      TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (model, effective_from)
);

-- [BỔ SUNG] Tỷ giá theo ngày. Bản cũ để tỷ giá trong `config` dạng MỘT giá trị
-- (VND_RATE = 25200, app.js:25) nên đổi tỷ giá cũng viết lại lịch sử như trên.
CREATE TABLE fx_rate (
    date            DATE PRIMARY KEY,
    usd_vnd         DECIMAL(12,2) NOT NULL,
    source          VARCHAR(100)                      -- khớp EXCHANGE_RATE_META (app.js:26)
);

-- ═══════════════════════════════════════════════════════════
-- Cây tổ chức (thay thế ORG_UNITS[] hardcode)
-- 5 cấp: Company → Tổng công ty → Phòng → Vùng/CN → Đội
-- ═══════════════════════════════════════════════════════════
CREATE TABLE org_units (
    id              VARCHAR(50) PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    parent_id       VARCHAR(50) REFERENCES org_units(id),
    level           INT NOT NULL,                     -- 1=Company, 2=Corp, 3=Phòng, 4=Vùng/CN, 5=Đội
    provisioned     INT DEFAULT 0,                    -- Số user được cấp quyền (từ Excel phân quyền)
    is_excluded     BOOLEAN DEFAULT FALSE,             -- thay EXCLUDED_DEPARTMENTS
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════
-- Alias phòng ban (thay thế UNIT_ALIASES{} hardcode)
-- Giải quyết: PBH1 = Phòng Bán hàng 1, TMĐT = Thương mại điện tử...
-- ═══════════════════════════════════════════════════════════
CREATE TABLE unit_aliases (
    alias           VARCHAR(200) PRIMARY KEY,
    unit_id         VARCHAR(50) NOT NULL REFERENCES org_units(id),
    source          VARCHAR(50) DEFAULT 'manual',     -- 'manual' | 'danh_muc_chuan' | 'excel_import'
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════
-- Ngân sách agent theo tháng
-- Tương đương AGENT_MONTHLY_BUDGETS[] hardcode
-- ═══════════════════════════════════════════════════════════
CREATE TABLE agent_budgets (
    id              SERIAL PRIMARY KEY,
    agent_name      VARCHAR(100) NOT NULL,
    monthly_usd     DECIMAL(10,2) NOT NULL,
    effective_from  DATE NOT NULL DEFAULT '2026-01-01',
    effective_to    DATE,                              -- NULL = còn hiệu lực
    aliases         TEXT[],                             -- tên thay thế
    UNIQUE(agent_name, effective_from)
);

-- ═══════════════════════════════════════════════════════════
-- Tài khoản user
-- Hiện tại = demo/allocated; khi có userId thật sẽ chuyển sang số đo
-- ═══════════════════════════════════════════════════════════
CREATE TABLE user_accounts (
    id              SERIAL PRIMARY KEY,
    -- [SỬA] Frontend cần BA trường định danh tách bạch, bản cũ chỉ có hai.
    login           VARCHAR(100) NOT NULL,             -- `login` — hiện dưới tên ở mọi bảng user
    full_name       VARCHAR(200),                      -- `n` — họ tên đầy đủ
    email           VARCHAR(200),
    unit_id         VARCHAR(50) REFERENCES org_units(id),
    department_raw  VARCHAR(200),                      -- `d` — chuỗi phòng ban gốc trên tài khoản
    agent_name      VARCHAR(100),
    user_group      VARCHAR(100),                      -- [BỔ SUNG] `ug` — bộ lọc User lọc theo cột này
    role            VARCHAR(50) DEFAULT 'user',
    account_type    VARCHAR(20) DEFAULT 'person',      -- [BỔ SUNG] 'person' | 'service'
                                                       --   app.js:262 đổi nhãn Role theo cột này
    source_status   VARCHAR(50),                       -- [BỔ SUNG] chuỗi trạng thái gốc TLA Ralli
    provisioned_at  DATE,                              -- [BỔ SUNG] "Thời gian được cấp" + thẻ
                                                       --   "Cấp mới trong kỳ". Nguồn hiện chưa xuất
                                                       --   ⇒ cột này đang rỗng trên dashboard
    last_active_at  TIMESTAMP,                         -- [SỬA] DATE quá thô cho DAU và cho mốc
                                                       --   "Bắt đầu không hoạt động"
    disabled        BOOLEAN DEFAULT FALSE,
    is_allocated    BOOLEAN DEFAULT TRUE,              -- TRUE = demo, FALSE = user thật
    UNIQUE(login)
);

-- ═══════════════════════════════════════════════════════════
-- [BỔ SUNG] Đăng ký agent
-- KPI "AI Agent (đang chạy / đã tạo)" cần mẫu số "đã tạo". Hiện allAgents()
-- (app.js:762) suy ra từ chính usage rows ⇒ agent đã tạo mà chưa từng chạy là VÔ HÌNH,
-- đúng nhóm mà thẻ "Agent không được sử dụng" muốn chỉ ra.
-- Bảng này cũng là chỗ đặt mapping agent → GCP project mà mục 5 có nhắc nhưng chưa có bảng.
-- ═══════════════════════════════════════════════════════════
CREATE TABLE agents (
    agent_name      VARCHAR(100) PRIMARY KEY,
    display_name    VARCHAR(200),
    gcp_project_id  VARCHAR(100),
    owner_email     VARCHAR(200),
    primary_unit_id VARCHAR(50) REFERENCES org_units(id),
    created_at      DATE NOT NULL,                     -- mẫu số "đã tạo"
    status          VARCHAR(20) DEFAULT 'active',      -- 'active' | 'archived'
    is_excluded     BOOLEAN DEFAULT FALSE              -- thay bảng excluded_agents
);

-- ═══════════════════════════════════════════════════════════
-- [BỔ SUNG] Chi phí thật từ BigQuery Billing
-- Thẻ "Tổng chi phí" ghi rõ nguồn "BigQuery Billing · ≈1 ngày" và "đã trừ ưu đãi"
-- (index.html:965-966) nhưng schema chỉ tính token × giá. Phase 2 có nhắc
-- "insert billing_daily" mà bảng đó chưa từng được định nghĩa.
-- ═══════════════════════════════════════════════════════════
CREATE TABLE billing_daily (
    date            DATE NOT NULL,
    gcp_project_id  VARCHAR(100) NOT NULL,
    agent_name      VARCHAR(100) REFERENCES agents(agent_name),
    service         VARCHAR(100),
    cost_gross_usd  DECIMAL(14,6),
    credits_usd     DECIMAL(14,6),
    cost_net_usd    DECIMAL(14,6),                     -- số hiển thị trên thẻ
    PRIMARY KEY (date, gcp_project_id, service)
);

-- ═══════════════════════════════════════════════════════════
-- [BỔ SUNG] Quyền sử dụng agent theo user — yêu cầu #2 và #3 cuộc họp 25/7
-- org_units.provisioned chỉ là MỘT số cho mỗi đơn vị, không tách theo agent. Hiện mọi
-- tài khoản Ralli hardcode a:"Trợ lý ảo Ralli" (app.js:259) nên khi lọc theo agent khác,
-- tử số của "tỷ lệ tài khoản được dùng" về 0 còn mẫu số provisionedOf() giữ nguyên
-- ⇒ tỷ lệ sai. Bảng này cho mẫu số đúng theo từng cặp (agent, đơn vị).
-- ═══════════════════════════════════════════════════════════
CREATE TABLE agent_entitlements (
    agent_name      VARCHAR(100) NOT NULL REFERENCES agents(agent_name),
    user_id         INT NOT NULL REFERENCES user_accounts(id),
    unit_id         VARCHAR(50) REFERENCES org_units(id),
    granted_at      DATE NOT NULL,
    revoked_at      DATE,
    PRIMARY KEY (agent_name, user_id)
);

-- ═══════════════════════════════════════════════════════════
-- [BỔ SUNG] Usage theo từng user — bảng gỡ bỏ toàn bộ lớp phân bổ
-- Đây là bảng duy nhất cho phép bỏ nhãn ALLOCATED_DATA_LABEL trên tab Phòng ban & User,
-- và cho DAU là số đo thay vì công thức suy ra.
-- ═══════════════════════════════════════════════════════════
CREATE TABLE usage_daily_user (
    date            DATE NOT NULL,
    user_id         INT NOT NULL REFERENCES user_accounts(id),
    agent_name      VARCHAR(100) NOT NULL,
    model           VARCHAR(100) NOT NULL,
    requests        INT DEFAULT 0,
    token_in        BIGINT DEFAULT 0,
    token_out       BIGINT DEFAULT 0,
    last_active_at  TIMESTAMP,
    PRIMARY KEY (date, user_id, agent_name, model)
);

-- ═══════════════════════════════════════════════════════════
-- [BỔ SUNG] Hạn mức — nuôi gauge quota ở cây phòng ban
-- Hiện % là hash(login) và hạn mức được suy NGƯỢC từ chính % đó (app.js:339, 1544)
-- ⇒ cả hai vế của chuỗi "đã dùng / hạn mức" đều là số giả.
-- Cũng là nguồn của ngưỡng quotaWarning=85 / quotaCritical=100 (app.js:38-39).
-- ═══════════════════════════════════════════════════════════
CREATE TABLE quota_usage (
    date            DATE NOT NULL,
    scope           VARCHAR(20) NOT NULL,              -- 'agent' | 'user' | 'project'
    scope_key       VARCHAR(200) NOT NULL,
    quota_type      VARCHAR(20) NOT NULL,              -- 'RPM' | 'TPM' | 'RPD' | 'USD'
    limit_value     DECIMAL(16,2),
    used_value      DECIMAL(16,2),
    exceeded_count  INT DEFAULT 0,                     -- số lần chạm 429
    PRIMARY KEY (date, scope, scope_key, quota_type)
);

-- ═══════════════════════════════════════════════════════════
-- [BỔ SUNG] Trạng thái các job thu thập
-- import_log chỉ ghi nhận upload Excel, không phủ 5 job tự động của Phase 2.
-- Status bar hiện hardcode "Gateway hoạt động" và "lần cuối 2 phút trước"
-- (index.html:276-277) — hai chỗ này cần số thật. (header-data-date và status-period
-- thì ĐÃ tính thật từ dữ liệu, app.js:2936-2937, không cần đụng tới.)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE ingestion_status (
    source          VARCHAR(50) PRIMARY KEY,           -- 'token' | 'monitoring' | 'quota' | 'billing' | 'org'
    last_run_at     TIMESTAMP,
    last_success_at TIMESTAMP,
    status          VARCHAR(20),                       -- 'ok' | 'degraded' | 'failed'
    rows_written    INT DEFAULT 0,
    error           TEXT
);

-- ═══════════════════════════════════════════════════════════
-- [BỎ] excluded_agents — đã gộp thành cột agents.is_excluded ở trên.
-- Giữ một danh sách agent tách rời khỏi bảng đăng ký agent sẽ tạo hai nguồn sự thật.
-- ═══════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════════
-- Cấu hình hệ thống (thay các hằng số hardcode)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE config (
    key             VARCHAR(50) PRIMARY KEY,
    value           JSONB NOT NULL,
    description     VARCHAR(200),
    updated_at      TIMESTAMP DEFAULT NOW()
);
-- Ví dụ:
-- INSERT INTO config VALUES ('budget_alert_thresholds', '[50,90,100]'::jsonb, 'Mốc cảnh báo ngân sách %', NOW());
-- INSERT INTO config VALUES ('cost_alert_pct', '30'::jsonb, 'Cảnh báo khi chi phí > N% trung bình (theo cuộc họp 25/7)', NOW());
-- INSERT INTO config VALUES ('insight_thresholds', '{...}'::jsonb, 'Toàn bộ INSIGHT_THRESHOLDS (app.js:27-43)', NOW());
-- [SỬA] `vnd_rate` đã chuyển sang bảng fx_rate — tỷ giá phải có lịch sử theo ngày,
--       để trong config dạng một giá trị sẽ viết lại chi phí của mọi kỳ đã chốt.

-- ═══════════════════════════════════════════════════════════
-- Lịch sử import (audit trail)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE import_log (
    id              SERIAL PRIMARY KEY,
    file_name       VARCHAR(300) NOT NULL,
    imported_by     VARCHAR(100),
    rows_imported   INT DEFAULT 0,
    rows_skipped    INT DEFAULT 0,
    errors          JSONB,
    imported_at     TIMESTAMP DEFAULT NOW()
);
```

### 4. API Endpoints

#### 4.1 Dashboard APIs (đọc dữ liệu đã tính toán)

| Method | Endpoint | Mô tả | Tương đương frontend |
|---|---|---|---|
| `GET` | `/api/overview?from=&to=&dept=&agent=&model=&provider=&user=` | Toàn bộ KPI tab Tổng quan | `chartsOverview()` |
| `GET` | `/api/departments?from=&to=&...` | Phòng ban + user metrics + drilldown | `chartsDepartments()` |
| `GET` | `/api/agents?from=&to=&...` | Agents metrics + heatmap + matrix | `chartsAgents()` |
| `GET` | `/api/providers?from=&to=&...` | Provider metrics | `chartsProviders()` |
| `GET` | `/api/models?from=&to=&...` | Model metrics | `chartsModels()` |
| `GET` | `/api/cost?from=&to=&groupby=agent\|dept\|model` | Chi phí + ngân sách | `chartsCost()` |
| `GET` | `/api/performance?from=&to=&...` | Hiệu năng + error breakdown | `chartsPerf()` |
| `GET` | `/api/trends?from=&to=&metric=cost\|token\|request` | Time-series cho biểu đồ | Trend charts |
| `GET` | `/api/filters` | Danh sách giá trị cho 5 bộ lọc | Filter dropdowns |

#### 4.2 Admin APIs (quản lý cấu hình)

| Method | Endpoint | Mô tả |
|---|---|---|
| `GET/PUT` | `/api/org-tree` | Đọc/cập nhật cây tổ chức |
| `GET/POST/DELETE` | `/api/aliases` | Quản lý alias phòng ban |
| `GET/PUT` | `/api/pricing` | Đọc/cập nhật bảng giá model |
| `GET/PUT` | `/api/budgets` | Đọc/cập nhật ngân sách agent |
| `GET/PUT` | `/api/config/:key` | Đọc/cập nhật cấu hình (tỷ giá, ngưỡng...) |
| `GET` | `/api/import-log` | Lịch sử import |

#### 4.3 Import APIs

| Method | Endpoint | Mô tả |
|---|---|---|
| `POST` | `/api/upload-excel` | Upload file Excel → parse → insert usage_daily |
| `POST` | `/api/usage` | Nhập dữ liệu thủ công 1 ngày (giữ tương thích) |
| `DELETE` | `/api/usage/:date` | Xóa dữ liệu 1 ngày |

### 5. Data Ingestion (thu thập tự động)

| Job | Nguồn GCP | Tần suất | Dữ liệu | Ghi chú |
|---|---|---|---|---|
| **Token Counter** | `usageMetadata` per API call | 5 phút (aggregate) | `token_in`, `token_out`, `cached`, `think`, `requests` | Mỗi agent = 1 GCP project → 1 API key → aggregate per project |
| **Error & Latency** | Cloud Monitoring API (`request_count`, `latency`) | 30 phút | `error_rate` (2xx/4xx/5xx), `latency_p95` | Metric: `serviceruntime.googleapis.com/api/request_count` |
| **Rate Limit** | Cloud Quotas API | 30 phút | RPM/TPM/RPD, lỗi 429 | Tách riêng 429 khỏi 4xx theo yêu cầu cuộc họp 25/7 |
| **Billing** | BigQuery Billing Export | 1 ngày | Chi phí net (sau credits), quy VND | Mỗi agent = 1 project → filter by `project.id` |
| **User Sync** | Internal IAM / Ralli | 1 ngày | Danh sách user, phòng ban, trạng thái | Khi có nguồn thật → chuyển `is_allocated=FALSE` |
| **Excel Import** | Upload thủ công | On-demand | Toàn bộ fields | Giữ song song với API tự động — `source='excel_import'` |

**Mapping Agent → GCP Project:**
Hiện mỗi agent tương ứng 1 project trên Google Cloud. Backend cần bảng mapping:
```
Sale Agent          → project-sale-agent
Chatbot Contact Center → project-contact-center
...
```

### 6. Xử lý dữ liệu Excel (Excel Import Pipeline)

Dựa trên cấu trúc file `Bảng tổng hợp chi phí token AI agent tháng 7 (3).xlsx`:

```
┌─────────────────────────────────────────────────────────────┐
│                   EXCEL IMPORT FLOW                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. User upload .xlsx via POST /upload-excel                │
│     ↓                                                        │
│  2. Parse: detect 4 sheets (Tuần 1/2/3/4)                  │
│     ↓                                                        │
│  3. Mỗi sheet → map sang date:                              │
│     Sheet "Tuần 1" → ngày đầu tháng (01)                   │
│     Sheet "Tuần 2" → ngày 08                                │
│     Sheet "Tuần 3" → ngày 15                                │
│     Sheet "Tuần 4" → ngày 22                                │
│     ↓                                                        │
│  4. Mỗi dòng Excel → 1 row usage_daily:                    │
│     Cột: Agent, Phòng ban, Model, Users, Token in/out,      │
│          Request, Error%, Latency                            │
│     ↓                                                        │
│  5. Resolve phòng ban: department_raw → unit_id via alias   │
│     (chuỗi không có alias → tự sinh unit mới, log warning)  │
│     ↓                                                        │
│  6. field `u` (users) chỉ lấy ở Tuần 1, bỏ qua tuần 2-4   │
│     ↓                                                        │
│  7. Loại agent có agents.is_excluded = TRUE                 │
│     ↓                                                        │
│  8. UPSERT vào usage_daily (ON CONFLICT UPDATE)             │
│     ↓                                                        │
│  9. Log vào import_log (file_name, rows, errors)            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 7. Phân kỳ triển khai

#### Phase 1 — MVP Database + API (2-3 tuần)

| Task | Chi tiết |
|---|---|
| Setup Cloud SQL | PostgreSQL instance, schema migration |
| Seed database | Script migrate `SEED_DAYS{}` + `buildJuneExcelWeeks()` → `usage_daily` |
| Migrate `ORG_UNITS[]` | → `org_units` + `unit_aliases` |
| Migrate `basePricing{}` | → `model_pricing` |
| Migrate `AGENT_MONTHLY_BUDGETS[]` | → `agent_budgets` |
| Seed `agents` | Danh sách agent đã tạo + `created_at` + mapping GCP project. Không lấy từ usage rows — xem Phần VI.2 |
| Seed `fx_rate` | Ít nhất 1 dòng cho mỗi tháng đã có dữ liệu (6/2026, 7/2026) ở tỷ giá 25.200 |
| Khai báo trước các cột Phase 2/4 | `req_2xx/4xx/5xx/429`, `latency_p99`, `provisioned_at`… tạo ngay ở Phase 1 (để NULL) để frontend không phải sửa hai lần |
| Backend API (FastAPI) | 7 dashboard endpoints + CRUD admin endpoints |
| Excel Import API | `POST /upload-excel` với parser theo cấu trúc hiện tại |
| Frontend migration | `app.js`: thay `localStorage` → `fetch()`, thay hardcode ORG_UNITS → API |
| Deploy Cloud Run | Container image, IAP auth |

#### Phase 2 — Auto Ingestion (2-3 tuần)

| Task | Chi tiết |
|---|---|
| Token Counter job | Cloud Function poll `usageMetadata`, aggregate per 5 min |
| Error & Latency job | Cloud Function query Cloud Monitoring API, mỗi 30 phút |
| Rate Limit tracking | Cloud Quotas API → tách 429 riêng |
| Billing sync | BigQuery scheduled query → insert billing_daily |
| Source indicator | Dashboard hiển thị `source` mỗi dòng (manual / api / excel) |

#### Phase 3 — Enhancement (1-2 tuần)

| Task | Chi tiết |
|---|---|
| Alias management UI | CRUD alias trên dashboard, thay vì sửa code |
| Org tree management | Thêm/sửa/xóa đơn vị, cập nhật provisioned |
| Alert system | Email hoặc Slack khi vượt ngân sách, error spike |
| Export PDF/Excel | Xuất báo cáo theo kỳ |
| Audit log | Ai thay đổi gì, lúc nào |

#### Phase 4 — Analytics & Real User (tùy nhu cầu)

| Task | Chi tiết |
|---|---|
| Real userId | Khi nguồn cung cấp userId → thay `is_allocated=TRUE` bằng số đo thật |
| Forecasting | Dự báo chi phí tháng tới dựa trên trend |
| Anomaly detection | Phát hiện bất thường (chi phí đột biến, error spike) |
| MoM / WoW comparison | So sánh kỳ liên tục tự động |
| Per-department dashboard | Dashboard tùy chỉnh cho từng phòng ban |
| WebSocket real-time | Push update khi có dữ liệu mới |

### 8. Công nghệ đề xuất

| Layer | Lựa chọn | Lý do |
|---|---|---|
| **Backend** | Python FastAPI | Type-safe, async, auto-docs (Swagger/OpenAPI), GCP SDK Python mature |
| **Database** | PostgreSQL 15 (Cloud SQL) | ACID, JSONB support, mature, phù hợp workload OLTP + light analytics |
| **Excel parser** | `openpyxl` (Python) | Đọc .xlsx native, không cần Excel installed |
| **Ingestion** | Cloud Functions gen2 (Python) | Serverless, auto-scale, tích hợp GCP native, cron via Cloud Scheduler |
| **Hosting** | Cloud Run | Container-based, auto-scale to zero, giá hợp lý |
| **Auth** | Google IAP | Đã có GCP ecosystem, zero-code SSO cho domain công ty |
| **CI/CD** | Cloud Build + Artifact Registry | Native GCP, trigger từ Git push |
| **Monitoring** | Cloud Monitoring + Cloud Logging | Tái sử dụng cùng hạ tầng đang dùng cho agent |

### 9. Rủi ro & Giải pháp

| Rủi ro | Mức độ | Giải pháp |
|---|---|---|
| Dữ liệu localStorage mất khi chuyển backend | Cao | Script migrate 1 lần + giữ backup JSON trước khi chuyển |
| Google AI Studio không có API aggregate sẵn | Trung bình | Middleware log mỗi call → aggregate theo batch; hoặc dùng Cloud Monitoring metrics |
| Tên phòng ban không thống nhất giữa các source | Cao | Giữ `unit_aliases` làm mapping layer + UI quản lý alias + log warning khi gặp tên mới |
| User không muốn thay đổi flow nhập liệu | Trung bình | Giữ form nhập tay song song, thêm nút Upload Excel → `source='excel_import'` |
| Tỷ giá USD/VND thay đổi | Thấp | Bảng `config` lưu tỷ giá + timestamp áp dụng, cho phép chỉnh qua API |
| File Excel thay đổi cấu trúc | Trung bình | Parser có validation + mapping config, log lỗi chi tiết, cho phép retry |
| User data chuyển từ allocated → real | Trung bình | Column `is_allocated` phân biệt rõ, migration dần dần per-agent |
| Mỗi agent dùng quy ước đặt tên phòng ban khác nhau | Cao | Chuẩn hóa tại ingestion: `department_raw` + resolved `unit_id` lưu song song |

---

## Phần V — Tổng kết

### Ma trận chỉ tiêu

Đếm trực tiếp từ `index.html` ngày 2026-08-03 (số cũ đã lệch sau khi gộp tab Provider + Model):

| Tab | KPI cards | Canvas | Heatmap / cây | Tổng biểu đồ |
|---|---|---|---|---|
| 📊 Tổng quan | 8 | 6 | 1 | 7 |
| 🏢 Phòng ban & User | 8 | 5 | 1 | 6 |
| 🤖 Agents | 4 | 1 | 1 | 2 |
| 🏭 Provider & Model | 9 | 4 | 1 | 5 |
| 💸 Chi phí | 4 | 4 | 0 | 4 |
| ⚡ Hiệu năng | 7 | 2 | 0 | 2 |
| **Tổng cộng** | **40** | **22** | **4** | **26** |

### Ưu tiên backend

```
Phase 1 (MVP)           ██████████████████████  Nền tảng — Database + API + Excel Import
Phase 2 (Automation)    ████████████████        Giá trị — Tự động thu thập, bỏ nhập tay
Phase 3 (Enhancement)   ██████████              Tiện ích — Quản lý, cảnh báo, export
Phase 4 (Analytics)     ██████                  Nâng cao — Dự báo, anomaly, real user
```

---

## Phần VI — Đối chiếu chỉ tiêu ↔ schema (kiểm ngày 2026-08-03)

Đọc toàn bộ `index.html` (1141 dòng, 6 tab) và truy ngược cách `app.js` tính từng chỉ tiêu.

### 1. Chỉ tiêu đang là số suy ra, schema chưa có chỗ chứa số thật

| Chỉ tiêu (id trên `index.html`) | Đang tính thế nào | Đã bổ sung vào schema |
|---|---|---|
| Lỗi phía Client `m-pf-4xx` | `error_rate × 0.64` (`app.js:2794`) | `usage_daily.req_4xx` |
| Lỗi phía Provider `m-pf-5xx` | `error_rate × 0.21` (`app.js:2795`) | `usage_daily.req_5xx` |
| Lỗi giới hạn tốc độ `m-pf-429` | `error_rate × 0.15` (`app.js:2796`) | `usage_daily.req_429` |
| Donut mã phản hồi `c-pf-code` | cùng 3 hệ số trên (`app.js:2821`) | `req_2xx` + 3 cột trên |
| Trường hợp chậm nhất `m-pf-p99` | `p95 × 2.1` (`app.js:2799`, `2808`) | `usage_daily.latency_p99` |
| Gauge quota (cây phòng ban) | `%` = `12+(hash(login)%80)` (`app.js:339`); hạn mức suy **ngược** từ `%` (`app.js:1544`) | `quota_usage` |
| Người dùng hoạt động theo ngày `c-us-dau` | `total × (0.10 + 0.16 × req/maxReq)` (`app.js:2599`) | `usage_daily_user` |
| Tài khoản không sử dụng theo ngày `c-us-idle` | `total − DAU` — kế thừa lỗi trên | `usage_daily_user` |
| Mọi số theo tài khoản (req/token/chi phí/active/last) | phân bổ theo `weight` (`app.js:280-341`) | `usage_daily_user` |
| "Bắt đầu không hoạt động" | `u.last` gán = ngày cuối kỳ (`app.js:337`) | `user_accounts.last_active_at` |
| "Thời gian được cấp" | luôn rỗng — nguồn TLA Ralli chưa có cột (`app.js:268`) | `user_accounts.provisioned_at` |
| Status bar "Gateway hoạt động", "lần cuối 2 phút trước" | hardcode trong `index.html:276-277` | `ingestion_status` |

**Nửa thật nửa suy ra** — `c-dep-adopt` (tỷ lệ tài khoản được dùng theo phòng): mẫu số
`provisionedOf()` là số **đếm thật** từ `RALLI_USERS` (`app.js:641-646`, `653`), nhưng tử số
`u.active` phụ thuộc `weight` mà `adoptionRatio()` (`app.js:241`) đặt bằng 0 cho các tài khoản
ngoài ngưỡng `eligible`. Chỉ `usage_daily_user` mới làm tử số thành số đo.

### 2. Chỉ tiêu có chỗ chứa nhưng mẫu số sai

| Chỉ tiêu | Vấn đề | Đã bổ sung |
|---|---|---|
| "AI Agent (đang chạy / đã tạo)" `m-ov-agents`, `m-ag-active` | `allAgents()` (`app.js:762`) dựng danh sách từ chính usage rows của **mọi ngày** (`allDayRows()`, `app.js:729`). Mẫu số vì thế là "agent từng phát sinh dữ liệu ở bất kỳ đâu trong lịch sử", không phải "agent đã tạo": agent tạo ra mà **chưa từng chạy lần nào** biến mất khỏi cả tử lẫn mẫu, còn agent đã archive thì vẫn được đếm mãi | `agents.created_at`, `agents.status` |
| "Agent không được sử dụng" `m-ag-idle` | `allAgents().length − active.length` (`app.js:1802`). Bắt được agent im lặng **trong kỳ đang chọn** (vì mẫu số trải toàn lịch sử), nhưng **bỏ sót** đúng nhóm đáng lo nhất: agent tạo ra chưa từng chạy | `agents.created_at` |
| Tỷ lệ tài khoản được dùng, khi lọc theo agent | mọi tài khoản Ralli hardcode `a:"Trợ lý ảo Ralli"` (`app.js:259`); lọc agent khác ⇒ tử số về 0, mẫu số `provisionedOf()` không đổi | `agent_entitlements` |
| Tổng chi phí `m-co-total` | thẻ ghi nguồn "BigQuery Billing" và "đã trừ ưu đãi" (`index.html:965-966`) nhưng số tính từ `token × giá`, chưa trừ credit | `billing_daily` |

### 3. Lỗi thiết kế trong schema Phần IV (đã sửa tại chỗ)

| # | Vấn đề | Xử lý |
|---|---|---|
| 1 | `UNIQUE(date, agent_name, department_raw, model)` bỏ sót `user_group` dù cột đó tồn tại và bộ lọc User dùng tới. **Đã kiểm: 0 va chạm** trên 45 dòng `SEED_DAYS` + 24 dòng tháng 6 ⇒ rủi ro tiềm ẩn, chưa phải lỗi đang xảy ra | thêm `user_group` vào khoá |
| 2 | Dữ liệu **tuần** nằm trong cột `DATE` và được vẽ như **ngày**. `trendSeries()` (`app.js:1410`) chỉ lấy ngày có dữ liệu nên đồ thị không bị gai, nhưng một bucket cả tuần vẫn bị dán nhãn một ngày ⇒ preset "7 ngày" bắt trọn dữ liệu một tuần, và Phase 2 sẽ trộn giá trị-ngày với giá trị-tuần trên cùng một trục | `granularity` + `period_end` |
| 3 | `model_pricing` và tỷ giá không có phiên bản ⇒ sửa giá hôm nay viết lại chi phí tháng 6-7 đã verify | `effective_from/to` + bảng `fx_rate` |
| 4 | `user_accounts` chỉ có `user_name` + `email`, thiếu `login`, `account_type`, `source_status`, `user_group` — đúng những trường `app.js:255-270` đang dùng | đã bổ sung 6 cột |
| 5 | `excluded_agents` tách rời khỏi bảng đăng ký agent ⇒ hai nguồn sự thật | gộp vào `agents.is_excluded` |

### 4. Phần plan không cần đụng tới

`org_units` + `unit_aliases` đủ cho drilldown 5 cấp và toàn bộ vấn đề đặt tên phòng ban lệch
nhau giữa các agent · `agent_budgets` đủ cho `c-co-agent-budget` và `BUDGET_ALERT_THRESHOLDS`
· `config` đủ cho `INSIGHT_THRESHOLDS` · `cached_tokens` / `think_tokens` / `chats` đủ dùng ·
`import_log` đủ cho luồng Excel.

Hai hằng `MODALITY` và `USER_HEAT` (`app.js:188-193`) khai báo nhưng **không còn khối UI nào
dùng** — không cần cột modality TEXT/IMG/AUDIO/VIDEO trong schema, dù panel nguồn dữ liệu
(`index.html:267`) vẫn nhắc tới chúng.

### 5. Ràng buộc vận hành kéo theo

So sánh **CK = cùng kỳ năm trước** (`DELTA_BASIS`, `app.js:841`) không cần thêm trường nào,
nhưng buộc phải **giữ tối thiểu 13 tháng dữ liệu**. Với dữ liệu bắt đầu từ 6/2026, mọi thẻ CK
sẽ hiển thị "chưa có dữ liệu" cho tới giữa 2027 — cần thống nhất trước với người dùng thay vì
để họ tưởng dashboard lỗi.

### 6. Ảnh hưởng tới phân kỳ

| Hạng mục bổ sung | Thuộc phase |
|---|---|
| `agents`, `fx_rate`, `model_pricing` versioning, sửa khoá `UNIQUE`, `granularity`/`period_end` | **Phase 1** — là schema nền, sửa sau tốn migration |
| `req_2xx/4xx/5xx/429`, `latency_p99`, `quota_usage`, `billing_daily`, `ingestion_status` | **Phase 2** — đi kèm đúng các job Cloud Monitoring / Cloud Quotas / BigQuery đã liệt kê |
| `usage_daily_user`, `agent_entitlements`, `user_accounts.provisioned_at` | **Phase 4** — phụ thuộc nguồn cấp `userId`, nhưng **cột phải khai báo từ Phase 1** để frontend không phải sửa lần hai |
