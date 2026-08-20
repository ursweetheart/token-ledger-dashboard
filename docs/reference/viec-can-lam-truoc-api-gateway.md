# Việc cần làm để sẵn sàng bước vào phát triển API Gateway

*Soạn 20/08/2026. Nguồn: `Master Plan API Gateway.xlsx` (3 sheet), `Tài_liệu_triển_khai_API_Gateway.docx`, `db/01_schema.sql`, `backend/`, `web/js/`, `scripts/`.*

---

## 0. Điều phải nói trước: bỏ cột nguồn đi **ngược** chính Master Plan của anh

Anh đề xuất *"bỏ các cột định nghĩa nguồn dữ liệu, vì sau khi có Gateway thì đó không còn là vấn đề"*. Tôi đã đi tìm bằng chứng cho ý đó trong chính kế hoạch, và tìm thấy điều ngược lại — ở **bốn** chỗ:

| Nơi | Nguyên văn |
|---|---|
| `Kế hoạch` — Giai đoạn 6 | "**Thêm nguồn dữ liệu Gateway vào trong danh sách các nguồn hiện có.** Kiểm tra và báo cáo đối chiếu chênh lệch giữa **bốn nguồn**." |
| `Kế hoạch` — Giai đoạn 7 | "Kỳ chạy **song song** Gateway và **ba nguồn cũ, tối thiểu 2 tuần**. Báo cáo đối chiếu token và chi phí theo ngày × agent × model." |
| `Kế hoạch` — Giai đoạn 8 | "mỗi agent chạy **song song tối thiểu 1 tuần** trước khi cắt đường cũ." |
| `Data Out` — trường #21 | `cost_is_estimated` · bool · **Nguồn: Gateway** · "Phân biệt tiền hoá đơn với tiền suy từ bảng giá" |

Đọc liền bốn dòng đó thì kết luận rõ:

> Cột nguồn **không biến mất**. Nó **đổi từ vựng** — từ `app | billing | monitoring` thành `app | billing | monitoring | gateway`, rồi về sau thành `scrape | gateway`.

Và thời điểm cần nó nhất chính là giai đoạn 6–7–8: lúc có **bốn** bộ đếm cùng lúc, không phải ba. Bỏ cột nguồn hôm nay là tháo đúng cái dụng cụ dùng để nghiệm thu Gateway — mà tháo trước ngày phải dùng nó.

Bản thân `docs/reference/tu-dien-database.md` Phần II (viết 19/08) cũng đã đi tới cùng kết luận, chỉ gọi tên khác:

```
   token_estimated  ──▶  cost_basis     ('gateway_price' | 'provider_invoice')
   token_source     ──▶  data_era       ('scrape' | 'gateway')
```

Vẫn là hai cột, vẫn trả lời đúng câu hỏi cũ: *"con số này ai đếm, và đã ai xác nhận chưa?"*

**Việc đúng cho hôm nay không phải bỏ cột nguồn, mà là làm cho hệ thống nhận thêm được một nguồn thứ tư mà không gãy.** Toàn bộ Nhóm B dưới đây là việc đó.

---

## 1. Hôm nay đang ở đâu

> **Sửa 20/08 sau góp ý của anh.** Bản đầu của mục này viết *"87,4% token không quy
> được về người"*. Con số đó **gộp nhầm hai chuyện**, xem khung ⚠️ ngay dưới sơ đồ.

```
   HÔM NAY — 3 nguồn, không nguồn nào biết đủ
   ┌──────────┐
   │ 8 agent  │──▶ Google (billing CSV + Monitoring)  ──┐
   └──────────┘         không ghi AI GỌI                │
        └──── 2/8 app phơi API riêng ───────────────────┤
                        biết từng người ────────────────┘
                                    │
                        fact_usage_daily (source = app|billing|monitoring)
                                    │
                            usage_resolved  ← COALESCE(billing, monitoring, app)

   SAU GATEWAY — 1 nguồn, biết đủ, NHƯNG chỉ từ ngày bật trở đi
   ┌──────────┐   ┌──────────────────┐
   │ 8 agent  │──▶│ Gateway/LiteLLM  │──▶ provider
   └──────────┘   │ ghi: user, đơn vị │
   gửi kèm:       │ token, cost, model│──▶ fact_usage_daily (data_era='gateway')
   username       └──────────────────┘
   phòng ban
                  ┌────────────────────────────────────────────┐
                  │ Lịch sử 01–08/2026 VĨNH VIỄN ở kỷ nguyên cũ │
                  │ Gateway không dựng lại được. Cửa sổ lưu giữ │
                  │ của Google đã trượt: 06/08 thấy 196 ngày,   │
                  │ 13/08 chỉ còn 112 ngày.                     │
                  └────────────────────────────────────────────┘
```

Dòng cuối là lý do cột nguồn phải sống tiếp **kể cả sau khi Gateway chạy hoàn hảo**.

### ⚠️ "Không quy được về người" phải tách làm BA, không phải hai

Quy ước của dự án: **6 agent ngoài TLA Hợp Đồng và Ralli được coi như chỉ có một
người dùng.** Vậy chúng **biết được người dùng** — thứ còn thiếu cùng lắm chỉ là một
cái tên hợp lý cho "người dùng đặc biệt" đó.

**Đo thật trên PostgreSQL ngày 20/08/2026, qua view `usage_resolved`** (đã khử trùng
lặp — cộng thẳng `fact_usage_daily` sẽ đếm ba lần và ra 1,27 tỷ thay vì 868 triệu):

| | Phần token | Token | | Thực chất | Gateway chữa được? |
|---|---|---:|---:|---|---|
| **(a)** | Trợ Lý Ảo Hợp Đồng + Trợ lý ảo Ralli, nguồn `app` | 107.926.810 | **12,4%** | Quy được về **người thật** | — đã có |
| **(b)** | 6 agent một-người-dùng | 749.483.267 | **86,4%** | Quy được **theo quy ước**: một tài khoản dịch vụ | Không cần chữa. Chỉ cần **đặt tên** |
| **(c)** | Trợ Lý Ảo Hợp Đồng + Trợ lý ảo Ralli, phần từ hoá đơn Google | 10.247.033 | **1,2%** | **Thật sự không quy được** — Google không nói ai trong 45 / 892 người đã gọi | Có, nhưng chỉ từ ngày bật trở đi |
| | | **867.657.110** | | | |

> ### ❌ Con số "87,4% không quy được về người" là SAI
>
> Nó bằng (b) + (c) cộng lại — gộp 6 agent vốn **biết chính xác ai dùng** vào cùng rổ
> với phần thật sự mù. Lỗ hổng thật chỉ **1,2%**.
>
> Nguồn của nó là `backend/store.py` hàm `health()` (~dòng 405): tử số lọc
> `kind='real'`, mà 6 agent một-người-dùng không có dòng `kind='real'` nào. Cảnh báo
> `user_coverage` trả về từ `/api/health` đang mang con số này.

Hai agent có cây tổ chức thật ra **tự phủ gần hết** phần của mình:

| Agent | Token (`usage_resolved`) | Quy về người thật | Độ phủ |
|---|---:|---:|---:|
| Trợ Lý Ảo Hợp Đồng | 70.240.065 | 62.706.827 | **89,3%** |
| Trợ lý ảo Ralli | 47.933.778 | 45.219.983 | **94,3%** |

Và `kind` hôm nay chỉ có **ba** giá trị — `service_account` chưa tồn tại:

```
real           937 tài khoản   (892 Ralli + 45 Trợ Lý Ảo Hợp Đồng)
whole_agent      8 tài khoản   một dòng cho MỖI agent, kể cả 6 agent một-người-dùng
unattributed     8 tài khoản   một dòng cho mỗi agent — chỉ Ralli có token (2,7 triệu)
```

Chính vì `whole_agent` có mặt ở **cả 8** agent nên nó mang hai nghĩa: với 6 agent
một-người-dùng nó là *"đúng một người dùng dịch vụ"*; với Trợ Lý Ảo Hợp Đồng và
Trợ lý ảo Ralli nó là *"không biết ai trong số 45 / 892 người"*.

**Quy ước này ĐÃ có trong code — nhưng chỉ ở đúng MỘT chỗ.** `backend/store.py`
hàm `adoption()` dòng ~274 đã áp đúng: `kind='service'`, `provisioned=1`,
`active=1 if any_usage`. Bảy chỗ còn lại vẫn lọc `kind='real'` và đánh rơi 6 agent:

    backend/store.py:189   accounts()   WHERE a.kind = 'real'
    backend/store.py:405   health()     SUM(...) WHERE a.kind = 'real'   ← đẻ ra 87,4%
    db/01_schema.sql:581   view usage_by_account
    scripts/audit_db.py:139, 290, 312, 367

Đây cũng chính là lý do ô ma trận drilldown hiện `—` thay vì `1/1`.

**Câu truy vấn dựng lại bảng trên** — mẫu số phải lấy từ `usage_resolved`, tử số từ
`fact_usage_daily`. Đây là chỗ dễ sai nhất: `fact_usage_daily` để ba nguồn cạnh nhau
nên cộng thẳng là đếm ba lần, mà tổng sai vẫn trông như một con số hợp lệ.

```sql
-- (b) 6 agent mot-nguoi-dung: lay TRON tu usage_resolved
SELECT g.name, g.has_org_tree, SUM(v.total_tokens)
FROM usage_resolved v JOIN dim_agent g ON g.agent_id = v.agent_id
GROUP BY g.name, g.has_org_tree ORDER BY 3 DESC;

-- (a) phan quy duoc ve nguoi that cua 2 agent co cay to chuc
SELECT SUM(f.total_tokens)
FROM fact_usage_daily f JOIN account a ON a.account_id = f.account_id
WHERE f.source = 'app' AND a.kind = 'real';

-- (c) = tong usage_resolved cua 2 agent do  -  (a)
```

---

## 2. Bốn nhóm việc

Đánh dấu: 🔴 chặn việc khác · 🟡 nên xong hôm nay · ⚪ làm được sau

---

### NHÓM A — QUYẾT ĐỊNH. Không viết code, nhưng chặn mọi thứ phía sau

Đây là nhóm đáng làm nhất hôm nay: rẻ về thời gian, đắt nếu quyết muộn.

#### 🔴 A1. Ba câu còn treo ở `tu-dien-database.md` Phần II §8

Ba câu này **đổi hình dạng schema**, nên không viết được migration nào trước khi chốt:

| # | Câu hỏi | Nếu chọn A | Nếu chọn B |
|---|---|---|---|
| 1 | Lịch sử cũ đi đâu? | Chung một database, phân biệt bằng `data_era` | Đóng băng DB hiện tại làm kho lưu trữ, dựng DB mới → dashboard phải đọc **hai** database |
| 2 | Có ghi `fact_attempt` không? | Có → trả lời được *"bao nhiêu tiền cháy vì retry"*, *"deployment nào hay dính 429"*. Bảng lớn nhất hệ thống | Không → gộp vào `fact_request`, **mất hẳn** hai câu đó |
| 3 | Ngân sách do ai chặn? | LiteLLM chặn, `ref_budget` là bản sao chỉ-đọc + `synced_at` | Ta tự chặn → cần thêm lịch sử thay đổi + nhật ký chặn |

**Đề xuất của tôi:** 1A, 2-Có, 3-LiteLLM. Lý do câu 1: dashboard đọc hai database là chi phí vĩnh viễn trả cho một lần tiện; `data_era` là một cột.

#### 🔴 A2. Chốt cách viết Project ID — 2/8 đang lệch

| Tài liệu triển khai §1.2 | Database đang chạy | |
|---|---|---|
| `tla-rally` | `tla-ralli` | ❌ |
| `tools-quiz` | `tools-quizz` | ❌ |
| 6 dòng còn lại | | ✅ |

Nếu `config.yaml` của LiteLLM lấy theo cách viết trong tài liệu, hai agent đó **không nối được với dữ liệu cũ, và không có lỗi nào báo ra**. Sửa mất 5 phút hôm nay; sau khi có traffic thì là một cuộc điều tra.

Việc: mở `SELECT gcp_project_id FROM dim_agent` trên GCP Console đối chiếu, chốt một cách viết, sửa vào tài liệu (không sửa DB nếu DB đang đúng).

#### 🔴 A3. Chốt quy ước `username` cho cả 8 agent — **trước** khi có request đầu tiên

`Data Out` #4 ghi: *"Hiện chỉ 2/8 agent đang có, 6 Agent 1 user còn lại đang được để mặc định."*

Bệnh cũ của dự án là ba nguồn ghi danh tính ba kiểu, phải hoà giải bằng bảng `account`. Gateway **không tự chữa** bệnh đó — nó chỉ dời chỗ: từ *"hai app ghi khoá khác nhau"* thành *"8 agent có gửi username theo cùng một quy ước không?"*.

Nếu agent A gửi `LongNT` còn agent B gửi `longnt@rangdong.com.vn`, ta có lại đúng bệnh cũ, chỉ muộn hơn và tốn hơn.

**Cần ban hành trước khi agent đầu tiên gửi request:**
- Dạng chuẩn: `LOWER(TRIM())`, có/không đuôi tên miền — chọn một
- **Tên của 6 "người dùng đặc biệt"** — xem khung ⚠️ ở mục 1. Đây không phải chỗ
  trống chờ dữ liệu, mà là **một quyết định đặt tên**. Gợi ý ba lối:

  | Lối | Ví dụ | Được | Mất |
  |---|---|---|---|
  | Tài khoản dịch vụ | `svc.dms-feedback` | Nhìn là biết không phải người | Cần quy ước tiền tố, phải nhớ |
  | Theo tên agent | `phan-loai-phan-hoi-tiep-thi` | Đọc lên hiểu ngay, trùng `dim_agent.code` | Dễ nhầm agent với người dùng |
  | Người phụ trách thật | `tuannx` | Có người chịu trách nhiệm chi phí | Sai lệch khi người đó đổi việc |

  **Đề xuất: lối 1**, tiền tố `svc.` + `dim_agent.code`. Suy ra được từ dữ liệu đã
  có, không phải gõ tay 6 lần, và tiền tố khiến mọi truy vấn lọc ra được dễ dàng.
- Phòng ban gửi `unit_id` hay gửi tên — nếu gửi tên thì ai giữ bảng dịch

#### 🟡 A4. Sửa 3 kiểu dữ liệu sai trong sheet `Data Out`

Sheet này là **hợp đồng** giữa Gateway và dashboard. Ai code theo nó sẽ code sai ở 3 trường:

| # | Trường | `Data Out` ghi | Database thật | Hậu quả |
|---|---|---|---|---|
| 6 | `unit_id` | `int` | `TEXT` (ObjectId 24 ký tự / UUID) | JOIN gãy ngay |
| 12 | `model_id` | `text` | `INT` | JOIN gãy ngay |
| 22 | `response_code` | `int` | `TEXT` | So sánh sai |
| 23 | `latency_ms` | `int` ms, nguồn "Hiện có" | DB có `p50_seconds`/`p95_seconds` **theo giây**, ở mức `(ngày, agent)` — không phải mức request | "Hiện có" là sai: cả đơn vị lẫn độ mịn đều khác |

#### 🟡 A5. Hai cột dashboard sắp mất nguồn mà sheet không nói

`Data Out` đánh dấu hai trường này là nguồn **"Hiện có"**:

| # | Trường | Nguồn DUY NHẤT hôm nay |
|---|---|---|
| 14 | `thinking_enabled` | `fact_monitoring.thinking_enabled` |
| 15 | `output_modality` | `fact_monitoring.output_modality` |

Nhưng kiến trúc đích **bỏ hẳn `fact_monitoring`** (Phần II §7: "❌ bỏ — Gateway thay thế hoàn toàn"). Nếu Gateway không tự bắn hai trường này ra, cột **"think"** trên dashboard sẽ trắng — **không lỗi nào báo**.

→ Chuyển hai trường này sang nhóm "Nguồn: Gateway" trong sheet, và xác nhận LiteLLM có phơi chúng không.

#### 🟡 A6. Chốt độ mịn thời gian

`Data Out` #2 yêu cầu `timestamp` mức **giờ** ("Biểu đồ theo giờ"). Hôm nay mọi thứ dashboard đọc đều ở mức **ngày** (`usage_resolved`, `fact_perf_daily`, `fact_latency_daily`). Chỉ `fact_call` và `fact_monitoring` mịn hơn ngày.

→ Quyết: dashboard có thật sự cần biểu đồ theo giờ ở giai đoạn 1 không? Nếu có thì `fact_usage_daily` không đủ, phải đọc thẳng `fact_request`.

---

### NHÓM B — SỬA CODE để đón được nguồn thứ tư

Đây là phần trả lời trực tiếp mong muốn ban đầu của anh, nhưng theo chiều ngược lại: không phải bỏ cột nguồn, mà là **làm cho việc thêm nguồn không còn đau**.

#### 🔴 B1. `'app'` đang là chuỗi CHỊU LỰC ở 8 chỗ — và nó có nghĩa ngầm

Trong code hôm nay, `source = 'app'` không có nghĩa là *"nguồn tên app"*. Nó có nghĩa là **"nguồn duy nhất biết ai là người dùng"**. Hai nghĩa đó trùng nhau — cho tới ngày Gateway xuất hiện.

| File | Dòng | Câu |
|---|---|---|
| `db/01_schema.sql` | 581 | `WHERE f.source = 'app'` — view `usage_by_account` |
| `backend/store.py` | 239, 245 | `AND f.source = 'app'` — chỉ tiêu **tỷ lệ áp dụng** |
| `scripts/audit_db.py` | 163, 263, 290, 312 | 4 phép kiểm |
| `db/build_usage_daily.py` | 193, 212, 235, 239 | khâu nạp |

**Chuyện sẽ xảy ra nếu không sửa:** Gateway ghi dữ liệu vào `source='gateway'`, mang theo đầy đủ username và phòng ban. Nhưng:
- `usage_by_account` trả về **y nguyên như cũ** — không thấy một dòng Gateway nào
- Tỷ lệ áp dụng **đứng im** ở 12,6%
- `audit_db.py` báo **30/30 đạt**

Không có lỗi nào. Chỉ là một dashboard đã có dữ liệu tốt mà không chịu hiển thị.

→ Việc: đổi từ liệt kê giá trị sang **một khái niệm có tên**, ví dụ một bảng nhỏ `ref_source(source, knows_user BOOLEAN, has_cost BOOLEAN)` hoặc tối thiểu một hằng số dùng chung. Thêm nguồn thứ tư khi đó là thêm **một dòng dữ liệu**, không phải sửa 8 câu SQL nằm rải ở 4 file.

#### 🟡 B2. `usage_resolved` phải nhận được nguồn thứ tư

View hiện có 3 CTE `b`/`m`/`a` và `COALESCE(b, m, a)`. Thêm Gateway = thêm CTE thứ tư **đứng đầu** thứ tự ưu tiên:

```sql
COALESCE(g.tokens, b.tokens, m.tokens, a.tokens)
--       ▲ gateway đứng trước billing: Gateway là bộ đếm của chính ta,
--         và nó có mặt ngay trong ngày, không đợi hoá đơn ~1 ngày
```

Kèm `token_source` nhận thêm giá trị `'gateway'`.

Việc nhỏ và gọn — **nhưng nên làm hôm nay để chứng minh nó nhỏ và gọn.** Cách nghiệm thu: chèn vài dòng giả `source='gateway'` vào một database thử, chạy `audit_db.py` + `check_api.py`, xem có bao nhiêu chỗ vỡ. Con số đó chính là câu trả lời thật cho "hệ thống đã sẵn sàng đón Gateway chưa".

#### 🟡 B3. Chuẩn bị cho việc `agent_id` **tách khỏi** `project`

Đây là hệ quả ít ai để ý của cân bằng tải. Tài liệu triển khai §5.2 nói Router sẽ chuyển request của Agent A sang deployment của Agent B khi A gần chạm hạn mức.

```
   Agent A gọi  ──▶  Gateway  ──▶  project của Agent B  ──▶  Google
        │                                    │
     ai HỎI                            ai TRẢ TIỀN
        └────── KHÔNG CÒN LÀ MỘT ───────────┘
```

Schema hôm nay **gộp hai chuyện làm một**: `fact_billing_daily` có cả `agent_id` lẫn `project`, và `agent_id` được **suy ra TỪ** `project` qua `dim_agent.gcp_project_id`. Sau Gateway phép suy đó sai — hoá đơn ghi nợ project B cho lưu lượng của Agent A, dashboard báo B tiêu tiền của A, **không lỗi nào báo**.

→ Hôm nay chưa cần tách bảng. Nhưng cần **ghi rõ** vào `db/01_schema.sql` ngay tại chỗ khai `gcp_project_id` rằng phép suy này có hạn sử dụng, kèm ngày. Ghi chú tại chỗ có giá trị hơn một tài liệu riêng.

#### ✅ B5. Tách `account.kind` — nửa `health()` ĐÃ XONG 20/08/2026

*(Thêm 20/08 sau góp ý về 6 agent một-người-dùng.)*

> | Nửa | Trạng thái |
> |---|---|
> | `health()` + phép kiểm độ phủ | ✅ **Xong 20/08.** `kind` nay có `service_account`; `/api/health` báo 98,5% quy được thay vì 12,4% |
> | `accounts()` → 6 tài khoản hiện trên ma trận | ⏸️ **Hoãn, đi cùng B1.** Làm riêng thì ô ma trận đổi từ `—` ("chưa biết") thành `0/1` ("đã đo, bằng 0") cho **Chatbot Contact Center** — agent tiêu nhiều nhất, 333 triệu token. Đó là lời khẳng định sai, tệ hơn `—` |
>
> **Đã sửa:** `db/load_org.py` `db/01_schema.sql` `backend/store.py` `scripts/audit_db.py`
> **Nghiệm thu:** rebuild 7/7 · `audit_db.py` 32 phép / 0 hỏng · `check_api.py` 16/16 · test JS 6 + 7
> **Số đo lại (trên `usage_resolved`, đã khử trùng lặp):** (a) người thật 12,1% ·
> (b) tài khoản dịch vụ 86,4% · (c) không quy được **1,5%** — cộng đúng 867.657.110
>
> Hai lỗi bắt được lúc tự soát, ghi lại vì cùng một bẫy sẽ quay lại ở B1:
> 1. Cộng từ `fact_usage_daily` là **đếm hai lần** — tài khoản dịch vụ có token ở cả
>    billing lẫn monitoring. Đo thử: 143,9%, và "phần còn lại" ra −43,9%.
> 2. Cộng riêng `source='app'` **vẫn lệch** — gồm cả những ngày `usage_resolved` đã chọn
>    billing thay cho app (107,9 triệu thay vì 105,0 triệu).

`account.kind='whole_agent'` đang mang **hai nghĩa khác hẳn nhau**:

```
   kind = 'whole_agent'   (8 dòng — một dòng cho MỖI agent)
   ├── 6 agent một-người-dùng: Chatbot Contact Center, Sale Agent,
   │   Multi modal AI Invoice, Tools Quizzer, Phân Loại Phản Hồi Tiếp Thị,
   │   Phân Loại Dữ Liệu CRM
   │      "một tài khoản dịch vụ, biết CHÍNH XÁC là ai"      ← quy được   86,4%
   └── Trợ Lý Ảo Hợp Đồng và Trợ lý ảo Ralli
          "Google chỉ báo mức project, không biết ai
           trong số 45 / 892 người đã gọi"                    ← KHÔNG quy được  1,2%
```

Gộp hai nghĩa vào một giá trị chính là chỗ đẻ ra con số 87,4% sai, và là lý do ô ma
trận hiện `—`.

→ Tách thành `kind = 'real' | 'service_account' | 'whole_agent' | 'unattributed'`,
rồi sửa 7 chỗ đang lọc `kind='real'` thành lọc **"quy được về ai đó"**
(`kind IN ('real','service_account')`) hay **"là một con người"** (`kind='real'`)
— tuỳ từng chỗ đang hỏi câu nào. Hai câu hỏi đó khác nhau, và hôm nay chúng dùng
chung một điều kiện.

Ba điều làm việc này đáng ưu tiên:
1. **Nó chữa một con số đang sai trên màn hình**, không chỉ dọn dẹp.
2. **Nó trả lời câu hỏi ô `—` đang treo** — không phải giải thích dấu gạch, mà là
   cho 6 đơn vị đó một tài khoản có tên, rồi ô đó tự hiện `1/1` hoặc `0/1`.
3. **Nó là bước dọn đường cho Gateway**: `svc.<code>` chốt ở A3 chính là
   `username` của các dòng `service_account` này. Làm hôm nay thì ngày Gateway bắn
   request đầu tiên, khoá đã có sẵn để nối.

Đây đúng là loại "sửa schema cho thuận với Gateway" mà anh muốn — khác với việc bỏ
cột nguồn ở chỗ: nó **thêm khả năng phân biệt**, không **bỏ đi** khả năng đó.

#### ⚪ B4. Dọn cái thật sự chết

`dim_function` — 8 dòng, cột `is_user_facing` **chưa từng có giá trị nào khác NULL**, không endpoint nào đọc. Phần II đã xếp nó vào nhóm bỏ. Đây mới đúng là thứ "bỏ đi cho gọn" — khác hẳn cột nguồn.

---

### NHÓM C — LỖ HỔNG phải bịt trước khi hệ thống ra khỏi `127.0.0.1`

Hôm nay cả hệ thống sống trên máy anh. Gateway có load balancer, 2+ server, Redis — tức là nó **ra mạng**. Ba thứ dưới đây hôm nay vô hại, ngày mai thì không.

#### 🔴 C1. Backend **không có xác thực nào**

`backend/main.py`: 8 endpoint, không một dòng nào kiểm danh tính. `/api/accounts` trả về **953 tài khoản kèm họ tên, email, phòng ban**.

Master Plan giai đoạn 3 yêu cầu: *"JWT đăng nhập Dashboard do Backend phát hành và kiểm tra, áp dụng cho Admin / User xem báo cáo."* Chưa có gì.

Hiện tại an toàn **chỉ vì** uvicorn gắn `127.0.0.1`. Đó là một dòng cấu hình, không phải một cơ chế.

#### 🟡 C2. `CORS allow_origins=["*"]`

`main.py:47`. Ghi chú trong file tự biện minh: *"chấp nhận được vì máy chủ chỉ lắng nghe trên 127.0.0.1"*. Lý do đó hết hiệu lực đúng vào ngày Gateway lên. Nên gắn kèm C1 thành một việc.

#### ⚪ C3. Base URL của frontend

`web/js/api.js:40` — `DEFAULT_BASE = "http://127.0.0.1:8000"`, đã có cách ghi đè bằng `?api=...`. Đủ dùng cho hôm nay. Nhưng kiến trúc §4 của tài liệu có **ba service** (Usage / Report / Alert) → frontend sẽ cần ba base URL, hoặc một reverse proxy đứng trước. Nên quyết sớm là *proxy*, để frontend không phải biết có mấy service.

---

### NHÓM D — TÁI LẬP ĐƯỢC, để người thứ hai vào làm được

Master Plan ghi 3 người: An Thanh (chủ trì), Chí Thanh, Tuấn (CTV). Hôm nay dự án dựng lại được **chỉ trên máy anh**.

#### 🟡 D1. `db/gen_catalog.py` không chạy lại được

Thiếu `data/raw_web/tla-hd/2026-08-14/token-usage-year.json` → không sinh lại được `db/02_catalog.sql` → **không kiểm được** catalog trong repo có còn khớp thực tế không. `data/` nằm trong `.gitignore`, nên người khác clone về sẽ vấp đúng chỗ này.

#### 🟡 D2. Không có test Python nào

`tests/` chỉ có 2 file `.js`. Bộ kiểm thật của dự án là `audit_db.py` (30 phép) và `check_api.py` (16 phép) — nhưng cả hai đều cần **database sống + máy chủ đang chạy**. Không có gì chạy được trên một máy trắng, và không có gì chạy được trong CI.

Master Plan giai đoạn 7 yêu cầu *"Phép kiểm mới trong `scripts/audit_db.py` và `backend/check_api.py` cho nguồn gateway"* — tức chính hai file này sẽ là nơi nghiệm thu Gateway. Chúng cần chạy được trên máy người khác **trước** ngày đó.

#### ⚪ D3. `docker-compose.yml` mới có Postgres + pgAdmin

Thiếu LiteLLM, Redis, Nginx. Chưa cần hôm nay, nhưng khi thêm thì `docker compose up -d` phải vẫn là một lệnh duy nhất — đó là thứ khiến người thứ hai vào được.

---

## 3. Nếu chỉ có một ngày, tôi làm theo thứ tự này

| | Việc | Thời gian | Vì sao trước |
|---|---|---|---|
| 1 | **A1** chốt 3 câu treo | 1h họp | Mọi thứ khác phụ thuộc |
| 2 | **A2** chốt project ID | 15 phút | Rẻ nhất, hỏng im lặng nhất |
| 3 | **A3** ban hành quy ước username | 1h | Phải xong **trước** request đầu tiên, không sửa lại được |
| 4 | **A4 + A5** sửa sheet `Data Out` | 30 phút | Nó là hợp đồng; sai hợp đồng thì code sai theo |
| 5 | ~~**B5** tách `account.kind`~~ | ✅ xong 20/08 | Nửa `health()` đã chữa con số sai; nửa `accounts()` gộp vào B1 |
| 6 | **B1** gỡ `'app'` khỏi 8 chỗ | 2–3h | Việc code lớn nhất, và là việc trả lời đúng ý ban đầu của anh |
| 7 | **B2** thêm nguồn thứ tư vào `usage_resolved` + chạy thử bằng dữ liệu giả | 1–2h | Đây là **phép đo** cho câu "đã sẵn sàng chưa" |
| 8 | **C1 + C2** JWT cho backend | 2–3h | Có thể lùi nếu 1–7 chưa xong |

B5 đứng trước B1 vì cả hai đều đụng cùng những câu SQL ở `store.py` và
`audit_db.py`. Làm B5 trước rồi B1 thì sửa mỗi câu một lần; làm ngược lại thì sửa
hai lần.

1–4 là quyết định, không phải code, và chúng chiếm chưa tới 3 tiếng. Nếu hôm nay chỉ xong 1–4 thì dự án đã sẵn sàng hơn nhiều so với xong 5–7 mà chưa quyết.

---

## 4. Việc **không** nên làm hôm nay

| Việc | Vì sao không |
|---|---|
| Bỏ `token_source` / `token_estimated` | Giai đoạn 6–7–8 cần chúng để đối chiếu **bốn** nguồn và chạy song song 2 tuần |
| Bỏ `fact_monitoring` | Là nguồn duy nhất của `thinking_enabled`, `output_modality`, và của lịch sử 01–04/2026 không dựng lại được |
| Bỏ bảng `account` / gộp vào `fact_request` | Bài toán hoà giải danh tính **dời chỗ chứ không biến mất** — xem A3 |
| Dựng sẵn `fact_request` / `fact_attempt` | Chưa chốt A1 câu 2 thì có thể phải xoá đi làm lại |
| Đổi `dim_agent` bỏ `gcp_project_id` | Khâu nạp hiện tại đang dựa vào nó; đổi bây giờ là phá cái đang chạy để phục vụ cái chưa có |

Điểm chung: **mọi việc "bỏ đi cho gọn" đều nên đứng sau ngày Gateway ghi được dòng dữ liệu đầu tiên**, không đứng trước.

---

## 5. Nghiệm thu: làm sao biết "đã sẵn sàng"?

Một phép thử duy nhất, làm được trong ngày:

> Tạo một database thử, chèn vài chục dòng giả `source='gateway'` có đủ `account_id` + `unit_id`, rồi chạy:
> ```
> python scripts/audit_db.py
> python backend/check_api.py
> node tests/*.test.js
> ```

**Kết quả mong đợi khi ĐÃ sẵn sàng:** token và tiền của dòng giả **hiện lên** dashboard, tỷ lệ áp dụng **nhúc nhích**, `usage_by_account` **có thêm dòng**, và mọi phép kiểm vẫn xanh.

**Kết quả nếu CHƯA sẵn sàng (dự đoán hôm nay):** mọi phép kiểm vẫn xanh, nhưng dashboard **không đổi một con số nào** — vì 8 chỗ hardcode `source='app'` đã lặng lẽ lọc hết dữ liệu Gateway ra ngoài.

Chính sự im lặng đó là thứ cần loại bỏ trước khi bước vào giai đoạn 6.
