# Việc cần làm để sẵn sàng bước vào phát triển API Gateway

*Soạn 20/08/2026. Nguồn: `planning/Master Plan API Gateway.xlsx` (3 sheet), `planning/Tài_liệu_triển_khai_API_Gateway.docx`, `db/migrations/sql/001_baseline.sql`, `backend/`, `web/js/`, `scripts/`.*

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
    db/migrations/sql/001_baseline.sql:759   view usage_by_account
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

#### ✅ A1. CẢ BA CÂU ĐÃ CHỐT — 20/08/2026 (`tu-dien-database.md` §8a–8e)

Ba câu này đổi hình dạng schema nên chặn mọi migration. **Cả ba đã có câu trả lời.**

| # | Câu hỏi | Quyết định |
|---|---|---|
| 1 | Lịch sử cũ đi đâu? | **MỘT database** + cột `data_era`. Và **giữ `fact_monitoring`** (đóng băng, không xoá) — 583.917 dòng đó không dựng lại được |
| 2 | Có ghi `fact_attempt`? | **CÓ.** Dữ liệu retry không dựng lại được về sau |
| 3 | Ngân sách do ai chặn? | **LiteLLM**, `$70` mỗi agent, cảnh báo 50% / 90%, chạm 100% thì chặn. `ref_budget` là bản sao chỉ-đọc + `synced_at` |

Ba việc kéo theo, ghi ở `§8b` và `§8e` — đọc trước khi viết `config.yaml`:

- Dòng `scrape` để **NULL** ở cột mới → truy vấn dùng cột mới sẽ **âm thầm bỏ 8 tháng lịch sử**
- **Cảnh báo Google Cloud phải giữ** — nó là thứ duy nhất bắt được lưu lượng đi vòng qua Gateway
- **Ralli đặt hạn mức theo token**, LiteLLM chặn theo USD → giữ trần token ở tầng app

Bảng gốc để tra lại lập luận:

| # | Câu hỏi | Nếu chọn A | Nếu chọn B |
|---|---|---|---|
| ~~1~~ | ~~Lịch sử cũ đi đâu?~~ | ✅ **CHỐT 20/08:** một database + `data_era`, và **giữ `fact_monitoring`** (đóng băng, không xoá) | |
| 2 | Có ghi `fact_attempt` không? | Có → trả lời được *"bao nhiêu tiền cháy vì retry"*, *"deployment nào hay dính 429"*. Bảng lớn nhất hệ thống | Không → gộp vào `fact_request`, **mất hẳn** hai câu đó |
| 3 | Ngân sách do ai chặn? | LiteLLM chặn, `ref_budget` là bản sao chỉ-đọc + `synced_at` | Ta tự chặn → cần thêm lịch sử thay đổi + nhật ký chặn |

**Đề xuất của tôi:** 1A, 2-Có, 3-LiteLLM. Lý do câu 1: dashboard đọc hai database là chi phí vĩnh viễn trả cho một lần tiện; `data_era` là một cột.

#### ✅ A2. Project ID — ĐÃ CHỐT 20/08/2026: database đúng, tài liệu sai cả hai chỗ

| Tài liệu §1.2 | Database | Kết luận |
|---|---|---|
| `tla-rally` | **`tla-ralli`** | Database ĐÚNG — người dùng xác nhận 20/08 |
| `tools-quiz` | **`tools-quizz`** | Database ĐÚNG — **chứng minh bằng chính dữ liệu Google** |
| 6 dòng còn lại | | khớp |

**Chứng cứ cho `tools-quizz`** mạnh hơn cả ảnh chụp console: cả CSV hoá đơn lẫn Cloud
Monitoring API do Google tự xuất ra đều ghi `tools-quizz`. Nếu database ghi sai thì 2.441
dòng hoá đơn đã không nối được.

**`tla-ralli` thì dữ liệu không phán được** — project này chưa nối Google Billing nên
không xuất hiện ở cả hai nguồn. Chốt bằng mắt người, 20/08/2026.

→ **Việc còn lại: sửa `Tài_liệu_triển_khai_API_Gateway.docx` §1.2**, không sửa database.

Nếu `config.yaml` của LiteLLM lấy theo cách viết trong tài liệu, hai agent đó **không nối được với dữ liệu cũ, và không có lỗi nào báo ra**. Sửa mất 5 phút hôm nay; sau khi có traffic thì là một cuộc điều tra.

Việc: mở `SELECT gcp_project_id FROM dim_agent` trên GCP Console đối chiếu, chốt một cách viết, sửa vào tài liệu (không sửa DB nếu DB đang đúng).

#### ✅ A3. Quy ước `username` — ĐÃ CHỐT 20/08, ĐÃ ĐO XONG 21/08

`Data Out` #4 ghi: *"Hiện chỉ 2/8 agent đang có, 6 Agent 1 user còn lại đang được để mặc định."*

Bệnh cũ của dự án là ba nguồn ghi danh tính ba kiểu, phải hoà giải bằng bảng `account`. Gateway **không tự chữa** bệnh đó — nó chỉ dời chỗ: từ *"hai app ghi khoá khác nhau"* thành *"8 agent có gửi username theo cùng một quy ước không?"*.

Nếu agent A gửi `LongNT` còn agent B gửi `longnt@rangdong.com.vn`, ta có lại đúng bệnh cũ, chỉ muộn hơn và tốn hơn.

> ### ✅ Chốt 20/08/2026 — danh tính lấy từ JWT, agent tự trích
>
> Ralli và Trợ Lý Ảo Hợp Đồng đều dùng JWT. **Agent tự giải mã token ở phía mình**, trích
> ra người dùng rồi gửi lên Gateway trong một header (ví dụ `X-User`). Sáu agent còn lại
> là một-người-dùng nên chỉ cần một tên cố định.
>
> **Ba điều việc này giải quyết:**
>
> | | |
> |---|---|
> | Danh tính từ **token** thay vì từ client tự khai | 8 chỗ có thể lệch → còn 2, và 6 chỗ **không thể** lệch vì là hằng số |
> | Gateway **không cầm** JWT phiên | JWT phiên là chứng chỉ bearer — ai cầm được thì gọi API của app với tư cách người dùng đó. Agent trích rồi gửi giá trị đã tách thì Gateway không giữ thứ phát lại được |
> | App đổi claim thì sửa **một chỗ** | Sửa trong agent, không đụng Gateway |
>
> **Và nó XOÁ luôn việc gửi phòng ban.** Có username là tra được `account.unit_id` — bảng
> `account` vốn đã là nguồn duy nhất cho *"một tài khoản một đơn vị"* (chốt 14/08, quy tắc
> chọn tất định). Bắt agent gửi phòng ban là tạo **nguồn thứ hai** cho một sự thật đã có.
>
> ### ✅ Đã đo 21/08/2026 — hai app KHÔNG dùng cùng claim
>
> Đăng nhập cả hai app, giải mã payload. Chi tiết đầy đủ: `tu-dien-database.md` §8f.
>
> | | Trợ lý ảo Ralli | Trợ Lý Ảo Hợp Đồng |
> |---|---|---|
> | `sub` | `"admin"` — **là username** | `"user-admin"` — **KHÔNG phải username** |
> | `username` | *(không có claim này)* | `"admin"` — **username ở đây** |
> | `unit_id` | — | `""` **rỗng** |
> | Ký / sống | HS256 · ~2 giờ | HS256 · ~8 giờ |
>
> ```
>    Trợ lý ảo Ralli        ->  claim  sub
>    Trợ Lý Ảo Hợp Đồng     ->  claim  username        (KHÔNG phải sub)
>    6 agent một-người-dùng ->  hằng số  svc.<code>
> ```
>
> **Quy ước không được rút gọn thành "lấy `sub`".** Viết vậy thì agent Hợp Đồng gửi lên
> `user-admin` — chuỗi hợp lệ, không có trong bảng `account`, JOIN ra rỗng, **không lỗi
> nào báo**.
>
> **Bẫy thứ hai:** claim `unit_id` của Hợp Đồng *tồn tại* nên trông như lối tắt cho phòng
> ban, nhưng nó **rỗng** — và Ralli không có claim đơn vị nào. Quyết định "tra
> `account.unit_id`" vì thế tránh đúng một cái bẫy đang nằm sẵn.
>
> **Nỗi lo "Ralli trả ObjectId" nhắm sai chỗ** — cảnh báo ở
> `db/migrations/sql/001_baseline.sql:163` nói về bản
> ghi sử dụng, không phải JWT. Trong 891 tài khoản Ralli: `username` là ObjectId **0/891**,
> có dấu chấm 814/891.
>
> **Chưa chứng minh được:** tài khoản `.env` là ADMIN ở cả hai app, không nằm trong danh bạ
> 891 dòng. Quyết định 21/08: **không đợi token nhân viên thường**. Thay bằng một phép kiểm
> trong `audit_db.py` kêu khi có dòng `gateway` mang username không tra ra `account_id`.

**Cần ban hành trước khi agent đầu tiên gửi request:**
- Dạng chuẩn: `LOWER(TRIM())`, có/không đuôi tên miền — chọn một.
  **Đề xuất giữ dạng hiện tại**: đo 937 tài khoản thật thấy 821 đã dùng dạng có dấu chấm
  (`bh1.longnt`), 113 dạng một từ, 3 có đuôi tên miền
- **Tên của 6 "người dùng đặc biệt"** — xem khung ⚠️ ở mục 1. Đây không phải chỗ
  trống chờ dữ liệu, mà là **một quyết định đặt tên**. Gợi ý ba lối:

  | Lối | Ví dụ | Được | Mất |
  |---|---|---|---|
  | Tài khoản dịch vụ | `svc.dms-feedback` | Nhìn là biết không phải người | Cần quy ước tiền tố, phải nhớ |
  | Theo tên agent | `phan-loai-phan-hoi-tiep-thi` | Đọc lên hiểu ngay, trùng `dim_agent.code` | Dễ nhầm agent với người dùng |
  | Người phụ trách thật | `tuannx` | Có người chịu trách nhiệm chi phí | Sai lệch khi người đó đổi việc |

  **Đề xuất: lối 1**, tiền tố `svc.` + `dim_agent.code`. Suy ra được từ dữ liệu đã
  có, không phải gõ tay 6 lần, và tiền tố khiến mọi truy vấn lọc ra được dễ dàng.
- ~~Phòng ban gửi `unit_id` hay gửi tên~~ → **BỎ**, tra từ `account.unit_id`

#### ✅ A4. Sửa 3 kiểu dữ liệu sai trong sheet `Data Out` — **sheet đã sửa**

Kiểm lại sheet ngày 27/08/2026: **cả bốn dòng dưới đây đã được sửa**, mục này treo 🟡 quá hạn. Giá trị trong sheet hôm nay: #6 `text` · #12 `int` · #22 `text` · #23 `int` ms với nguồn `Gateway` kèm ghi chú về độ mịn. Giữ bảng lại làm vết, không phải việc còn phải làm.

Sheet này là **hợp đồng** giữa Gateway và dashboard. Ai code theo bản cũ sẽ code sai ở 3 trường:

| # | Trường | `Data Out` ghi | Database thật | Hậu quả |
|---|---|---|---|---|
| 6 | `unit_id` | `int` | `TEXT` (ObjectId 24 ký tự / UUID) | JOIN gãy ngay |
| 12 | `model_id` | `text` | `INT` | JOIN gãy ngay |
| 22 | `response_code` | `int` | `TEXT` | So sánh sai |
| 23 | `latency_ms` | `int` ms, nguồn "Hiện có" | DB có `p50_seconds`/`p95_seconds` **theo giây**, ở mức `(ngày, agent)` — không phải mức request | "Hiện có" là sai: cả đơn vị lẫn độ mịn đều khác |

#### ✅ A5. Hai cột dashboard sắp mất nguồn — **đã đo, đã sửa sheet** (27/08/2026)

Lo ngại ban đầu: kiến trúc đích **bỏ hẳn `fact_monitoring`** (Phần II §7), mà đó là nguồn duy nhất hôm nay của `thinking_enabled` (#14) và `output_modality` (#15). Gateway không bắn ra thì cột **"think"** trên dashboard trắng — **không lỗi nào báo**.

**Đo 26/08/2026, có đối chứng — cùng model, cùng câu hỏi, khác đúng một tham số:**

| Trường | LiteLLM có cột riêng? | Dẫn xuất được? |
|---|---|---|
| `thinking_enabled` | ❌ không | ✅ `…completion_tokens_details.reasoning_tokens` **có khoá** ⇒ `true` |
| `output_modality` | ❌ không | ✅ `…completion_tokens_details.{text,audio,image}_tokens` — khoá nào có giá trị thì đó là dạng đầu ra |

🔴 **Chỗ dễ đọc nhầm nhất:** khi tắt suy luận, khoá `reasoning_tokens` **vắng mặt hoàn toàn** — *không* phải bằng `0`. Code đọc `usage.get("reasoning_tokens", 0) > 0` thì đúng; code đọc `usage["reasoning_tokens"] is not None` thì vỡ; code chỉ kiểm `!= 0` mà không kiểm sự tồn tại thì **mọi request đều thành "có suy luận"**.

**Sheet đã sửa 27/08/2026:** cột `Nguồn` của cả hai trường đổi từ `Gateway` sang **`Dẫn xuất từ Gateway`**, kèm quy tắc tính trong `Ghi chú`. Ghi "Nguồn: Gateway" là sai — ai code theo sẽ đi tìm một cột không tồn tại.

Chi tiết: [`doi-chieu-data-out-litellm.md`](../archive/gateway/doi-chieu-data-out-litellm.md) và [`do-ban-ghi-litellm-24-08.md`](../archive/gateway/do-ban-ghi-litellm-24-08.md) §6 ④.

#### 🟡 A6. Chốt độ mịn thời gian

`Data Out` #2 yêu cầu `timestamp` mức **giờ** ("Biểu đồ theo giờ"). Hôm nay mọi thứ dashboard đọc đều ở mức **ngày** (`usage_resolved`, `fact_perf_daily`, `fact_latency_daily`). Chỉ `fact_call` và `fact_monitoring` mịn hơn ngày.

→ Quyết: dashboard có thật sự cần biểu đồ theo giờ ở giai đoạn 1 không? Nếu có thì `fact_usage_daily` không đủ, phải đọc thẳng `fact_request`.

---

### NHÓM B — SỬA CODE để đón được nguồn thứ tư

Đây là phần trả lời trực tiếp mong muốn ban đầu của anh, nhưng theo chiều ngược lại: không phải bỏ cột nguồn, mà là **làm cho việc thêm nguồn không còn đau**.

#### ✅ B1 + B2. XONG 21/08/2026 — `'app'` không còn là chuỗi chịu lực

Trong code hôm nay, `source = 'app'` không có nghĩa là *"nguồn tên app"*. Nó có nghĩa là **"nguồn duy nhất biết ai là người dùng"**. Hai nghĩa đó trùng nhau — cho tới ngày Gateway xuất hiện.

**Đếm lại 21/08: 24 chỗ / 8 file.** Nhưng con số đó chưa dùng được, vì nó gộp hai loại
việc trái ngược — và chỉ một loại là việc phải làm:

```
   ĐẦU GHI (14 chỗ) — GIỮ NGUYÊN        ĐẦU ĐỌC (10 chỗ) — ĐÂY LÀ B1
   load_hd · load_ralli                 backend/store.py   :257 :263 :452
   build_usage_daily · rebuild_db       db/migrations/sql/001_baseline.sql :700 :751
   gen_catalog                          scripts/audit_db.py :163 :263 :290 :312 :413
        │                                    │
   "dòng này TỪ app" — đúng             "chỉ lấy dòng của app" — lọc mất Gateway
```

| File | Dòng | Câu |
|---|---|---|
| `backend/store.py` | 257, 263 | `AND f.source = 'app'` — chỉ tiêu **tỷ lệ áp dụng** |
| `backend/store.py` | 452 | `v.token_source = 'app'` — chia token về người thật |
| `db/migrations/sql/001_baseline.sql` | 700 | `WHERE source = 'app'` — view đối chiếu nguồn |
| `db/migrations/sql/001_baseline.sql` | 751 | `WHERE f.source = 'app'` — locator lịch sử trước khi view hỏi `ref_source.knows_user` |
| `scripts/audit_db.py` | 163, 263, 290, 312, 413 | 5 phép kiểm |

**Chuyện sẽ xảy ra nếu không sửa:** Gateway ghi dữ liệu vào `source='gateway'`, mang theo đầy đủ username và phòng ban. Nhưng:
- `usage_by_account` trả về **y nguyên như cũ** — không thấy một dòng Gateway nào
- Tỷ lệ áp dụng **đứng im** ở 12,6%
- `audit_db.py` báo **30/30 đạt**

Không có lỗi nào. Chỉ là một dashboard đã có dữ liệu tốt mà không chịu hiển thị.

Việc đúng — và **đã làm xong 21/08**, xem khung ngay dưới: đổi từ liệt kê giá trị sang một khái niệm có tên. Thêm nguồn thứ năm nay là thêm **một dòng dữ liệu** vào `ref_source`, không phải sửa 8 câu SQL nằm rải ở 4 file.

> ### ✅ Làm xong 21/08/2026 — change `admit-gateway-as-a-fourth-source`
>
> **Nghiệm thu bằng một phép đo, không bằng lời:** `tools/diagnostics/dien_tap_gateway.py` chèn dòng
> `source='gateway'` mang username THẬT, chạy toàn bộ phép kiểm, so số trước/sau, rồi
> `ROLLBACK`.
>
> | | trước khi sửa | sau khi sửa |
> |---|---|---|
> | `usage_by_account` | +0 dòng | **+3 dòng / +3.000.000 token** |
> | tỷ lệ áp dụng | +0 | **+3** |
> | quy về người thật | +0 | **+3.000.000** |
> | gateway ưu tiên trước billing | không | **có** |
> | kỳ vọng đạt | **0/8** | **7/7** |
>
> Chạy trước khi sửa, dashboard **đứng im** trước 4 triệu token: `usage_resolved` có thêm
> khoá nhưng `COALESCE(b,m,a)` không biết `gateway` nên trả `NULL`. Dữ liệu nằm trong
> database và **vô hình** — đúng dự đoán, và rõ hơn dự đoán.
>
> **Đã sửa:** bảng `ref_source(source, knows_user, has_invoice_cost, era, note)` ·
> `usage_resolved` thêm CTE `g` đứng đầu `COALESCE` · 8 chỗ đầu đọc hỏi `knows_user` thay
> vì so tên nguồn · 6 tài khoản dịch vụ đổi sang `svc.<code>` · 3 phép kiểm mới.
>
> **Bất biến giữ nguyên tuyệt đối:** 1.189 dòng · 867.657.110 token · $291,985601 · độ phủ
> 104.990.903 / 749.483.267 / 13.182.940. Không lệch một token.
>
> **Nghiệm thu:** rebuild 7/7 · `audit_db.py` 36 phép / 0 hỏng · `check_api.py` 16/16 ·
> test JS 6 + 7 · diễn tập 7/7.
>
> **Bốn chỗ đo lại thì khác với lúc soạn proposal** — ghi lại vì cùng loại bẫy sẽ quay lại:
>
> | Tưởng | Đo ra |
> |---|---|
> | 10 chỗ đầu đọc | **8.** Hai chỗ là *định nghĩa nguồn app*; Gateway lọt vào đó mới sai |
> | `has_cost` cho gateway = TRUE | **FALSE.** LiteLLM có số tiền nhưng tự nhân từ bảng giá — đổ vào `cost_usd` là biến tiền suy ra thành tiền đã xác nhận |
> | Phép kiểm "nguồn lạ" | **Không kêu được** — khoá ngoại đã chặn ngay lúc ghi. Bỏ, thay bằng một dòng trong `FOREIGN_KEYS` |
> | Phép kiểm "mọi dòng biết người đều quy được" | Kêu ngay **21 dòng**, và nó đúng: `app` *biết được* người dùng nhưng không phải lúc nào cũng biết. Chỉ ký nguyên gateway mới đòi được vế đó |

#### ✅ B2. `usage_resolved` đã nhận nguồn thứ tư — chi tiết ở khung trên

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

→ Hôm nay chưa cần tách bảng. Nhưng cần **ghi rõ** tại
`db/migrations/sql/001_baseline.sql:73`, ngay chỗ khai `gcp_project_id`, rằng phép suy này
có hạn sử dụng, kèm ngày. Ghi chú tại chỗ có giá trị hơn một tài liệu riêng.

#### ✅ B5. Tách `account.kind` — nửa `health()` ĐÃ XONG 20/08/2026

*(Thêm 20/08 sau góp ý về 6 agent một-người-dùng.)*

> | Nửa | Trạng thái |
> |---|---|
> | `health()` + phép kiểm độ phủ | ✅ **Xong 20/08.** `kind` nay có `service_account`; `/api/health` báo 98,5% quy được thay vì 12,4% |
> | `accounts()` → 6 tài khoản hiện trên ma trận | ✅ **Đóng lại 22/08 — quyết định GIỮ NGUYÊN.** Lý do hoãn ghi 20/08 nhắm sai hàm; xem khung dưới |
>
> ### ⚠️ Lý do hoãn ghi 20/08 nhắm sai hàm — đính chính 22/08/2026
>
> Ghi chú cũ: *"Làm riêng thì ô ma trận đổi từ `—` thành `0/1` cho Chatbot Contact
> Center — lời khẳng định sai, tệ hơn `—`."* **Ma trận ăn từ `adoption()`, không phải
> `accounts()`.** `adoption()` đã sửa xong 21/08 và nay không phân nhánh theo loại agent,
> nên hai hàm không dính nhau.
>
> Đo A/B thật ngày 22/08 (uvicorn thật + `app.js` thật, đổi đúng một dòng rồi hoàn nguyên):
>
> | | trước | sau |
> |---|---:|---:|
> | `/api/accounts` · `USER_ACCOUNTS` | 937 · 937 | **943 · 943** |
> | dòng `svc.*` lên màn hình | 0 | **6** |
> | thẻ "User hoạt động" | 26/937 | **26/943** |
> | đơn vị gốc · trong đó tự tạo | 11 · 7 | **11 · 7** |
> | `DEPT_PROVISIONED` | 101 / 3.693 | **101 / 3.693** |
>
> **Hại thật gói gọn ở hai chỗ:** 6 dòng *"Cả &lt;tên agent&gt;"* trong bảng danh bạ, và
> mẫu số thẻ "User hoạt động" 937→943. Cây phòng ban **không đổi** — sáu đơn vị *"Đơn vị
> sử dụng …"* đã có sẵn ở cấp gốc từ trước, do các dòng usage chế ra qua `unitOf()`.
>
> Việc đúng vì thế **không phải gỡ bộ lọc** mà là đặt tên cho nó: `store.accounts()` giữ
> `kind='real'`, có ghi chú tại chỗ nói đây là tấm lưới duy nhất, và `check_api.py` có
> phép kiểm khoá lại — change `pin-the-directory-to-real-people`, 22/08/2026.
>
> **Đã sửa:** `db/load_org.py` `db/migrations/sql/001_baseline.sql` `backend/store.py` `scripts/audit_db.py`
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

#### ❌ B4. ĐÃ RÚT — `dim_function` KHÔNG chết (đo lại 20/08/2026)

Nhận định ban đầu: *"8 dòng, `is_user_facing` chưa từng có giá trị, không endpoint nào
đọc — thứ bỏ đi cho gọn."* **Đo lại thì sai:**

| | |
|---|---|
| `fact_call.function_code` | **8.330/8.330 dòng có giá trị** — mọi lượt gọi Ralli đều mang mã chức năng |
| `Data Out` trường #10 | `function` · text · **Nguồn: Gateway** — Gateway sẽ nạp lại chiều này |

Bảng không chết, nó chỉ **chưa được phơi lên giao diện**. Bỏ bây giờ là xoá rồi dựng lại,
và mất luôn 2 nhãn tiếng Việt đang có (`Phân tích hợp đồng`, `Hỏi đáp AI`).

**Giữ.** Việc đúng là phơi chiều này lên dashboard, không phải xoá bảng.

---

### NHÓM C — LỖ HỔNG phải bịt trước khi hệ thống ra khỏi `127.0.0.1`

Hôm nay cả hệ thống sống trên máy anh. Gateway có load balancer, 2+ server, Redis — tức là nó **ra mạng**. Ba thứ dưới đây hôm nay vô hại, ngày mai thì không.

#### ✅ C1 + C2. XONG 21/08/2026 — change `require-a-key-to-read-the-api`

`backend/main.py`: 8 endpoint, không một dòng nào kiểm danh tính. `/api/accounts` trả về **937 tài khoản kèm họ tên, phòng ban**.

Master Plan giai đoạn 3 yêu cầu: *"JWT đăng nhập Dashboard do Backend phát hành và kiểm tra, áp dụng cho Admin / User xem báo cáo."*

Hiện tại an toàn **chỉ vì** uvicorn gắn `127.0.0.1`. Đó là một dòng cấu hình, không phải một cơ chế.

> ### ✅ Đã bịt — nhưng bịt bằng **khoá dùng chung**, không phải JWT theo người
>
> ```
>    Authorization: Bearer <DASHBOARD_KEY>   ->  8/8 endpoint
>    thieu DASHBOARD_KEY                     ->  MAY CHU KHONG KHOI DONG
>    /healthz                                ->  diem tham do duy nhat, khong khoa
> ```
>
> **Vì sao lệch khỏi Master Plan giai đoạn 3** — ghi ra đây để ba tháng nữa mở kế
> hoạch ra không tưởng là chưa làm:
>
> | | |
> |---|---:|
> | Số endpoint | 8 |
> | Trong đó là `GET` | **8** |
> | Hành động đặc quyền (sửa / xoá / đổi hạn mức) | **0** |
> | Kho người dùng của dashboard | **không có** — `account` không có cột mật khẩu |
>
> Không có gì để phân vai thì phân vai bây giờ là viết code không dùng tới. Hàm
> `nguoi_goi()` trả về một **`Principal`** chứ không trả `True`, nên ngày lên JWT
> chỉ phải sửa **một hàm** — 8 endpoint không đụng một chữ.
>
> **Nói thẳng phần CHƯA có**, để không ai tưởng C1 đã đóng trọn:
>
> | | |
> |---|---|
> | Chặn người lạ đọc 937 họ tên kèm phòng ban | ✅ đây là rủi ro thật của C1 |
> | Biết **ai** đã xem gì | ❌ không có nhật ký theo người |
> | Thu hồi quyền của **một người** | ❌ đổi khoá là đá văng tất cả |
> | Phân biệt Admin / User | ❌ |
>
> **C2 (CORS) đã xong từ 20/08** (`c3d7169`, đọc `DASHBOARD_ORIGINS`) — nhưng nó
> **không** đóng được C1 và đây là chỗ dễ tưởng nhầm nhất:
>
> ```
>    CORS la luat cua TRINH DUYET, khong phai cua may chu.
>    trang web la  -> trinh duyet vut cau tra loi di   ✅ CORS chan duoc
>    curl / script -> KHONG doc CORS bao gio           ❌ CORS khong thay gi
> ```
>
> Máy chủ vẫn **trả đủ dữ liệu** trong cả hai trường hợp. Một dòng `curl` lấy trọn
> 937 người, hôm qua cũng như hôm nay — cho tới change này.
>
> **Nghiệm thu:** `check_api.py` 18 phép (thêm *"gọi không khoá phải nhận 401"* và
> *"`/healthz` vẫn mở"*) · test JS **6 + 11** · một lát mỏng riêng dựng uvicorn thật
> **không cần Docker** (`soat_khoa.py`, **24/24**) — đo được rằng `main.py` import xong
> mà không chạm database, nên mọi đường 401 kiểm được ngay.
>
> **Năm chỗ đo lại thì khác lúc soạn proposal** — ghi vì cùng loại bẫy sẽ quay lại.
> (Tới 22/08 dòng này ghi "Ba chỗ" trong khi bảng có năm hàng — đếm lại rồi sửa.)
>
> | Tưởng | Đo ra |
> |---|---|
> | Khoá sai chỉ dẫn tới 401 | **`Bearer á` làm mọi endpoint hỏng.** `secrets.compare_digest` với hai `str` ném `TypeError` khi có ký tự ngoài ASCII — một đường sập gọi được **mà không cần biết khoá**. Phải so trên `bytes` |
> | `?api=` chỉ đổi chỗ đọc dữ liệu | Từ lúc trình duyệt giữ một bí mật, nó đổi luôn **chỗ gửi bí mật**: link `?api=http://host-la` lấy được khoá của người bấm. Đã cất khoá **theo từng địa chỉ** |
> | `HTTPBearer` mặc định là đủ | Nó trả **403** khi thiếu header, không phải 401. Phải `auto_error=False` rồi tự ném 401 |
> | Đặt khoá vào `.env` là chạy | **Không file Python nào của backend đọc `.env`** — chỉ docker-compose và `pull_web_apps.py` đọc. Đồng nghiệp làm đúng theo `.env.example` sẽ vẫn không khởi động được |
> | Test JS không liên quan | Cả **4 kịch bản** hỏng cũ dừng ở ô nhập khoá và không chạm tới nhánh chúng đang kiểm. Phải gieo khoá vào `localStorage` giả |
> | Chỉ `tests/` dính bẫy khoá | **Chỗ thứ năm: `tools/diagnostics/chay_dashboard_trong_node.js`.** Đo 22/08: exit **0**, in "nạp OK" hai lần, nhật ký uvicorn **0 lần gọi `/api/`**. Nằm ở `tools/` nên không ai chạy, không ai thấy. Đã vá cùng change `pin-the-directory-to-real-people` |

#### ⚪ C3. Base URL của frontend

`web/js/api.js:40` — `DEFAULT_BASE = "http://127.0.0.1:8000"`, đã có cách ghi đè bằng `?api=...`. Đủ dùng cho hôm nay. Nhưng kiến trúc §4 của tài liệu có **ba service** (Usage / Report / Alert) → frontend sẽ cần ba base URL, hoặc một reverse proxy đứng trước. Nên quyết sớm là *proxy*, để frontend không phải biết có mấy service.

---

### NHÓM D — TÁI LẬP ĐƯỢC, để người thứ hai vào làm được

Master Plan ghi 3 người: An Thanh (chủ trì), Chí Thanh, Tuấn (CTV). Hôm nay dự án dựng lại được **chỉ trên máy anh**.

#### 🟡 D1. `db/gen_catalog.py` không chạy lại được

> **Đính chính 22/08/2026 — bản đầu chỉ nhầm thư mục.** `db/gen_catalog.py:57-58` không
> ghim ngày, nó gọi `_latest_dir()`, và thư mục mới nhất là `2026-08-17` — nơi
> `token-usage-year.json` **có mặt** ở cả `ralli/` lẫn `tla-hd/`. Thư mục
> `tla-hd/2026-08-14/` là của `pull_hd_usage.py` (chỉ chứa `usage-day-user-model.json`),
> `gen_catalog` không bao giờ đọc tới đó. Và nó chỉ lấy `costs.by_model` — **tập tên
> model**, không lấy số, không lấy ngày — rồi `raise SystemExit` nếu gặp model lạ. Tức
> là nó hỏng **to tiếng**, không hỏng im lặng.

Việc D1 thật nằm chỗ khác: `data/` nằm trong `.gitignore`, nên người khác clone về có
**số không** đầu vào — không sinh lại được `db/02_catalog.sql` để đối chiếu với bản trong
repo. Đây cùng một bài toán với D2 và D3, không phải một file thiếu.

#### 🟡 D2. Không có test Python nào

`tests/` chỉ có 2 file `.js`. Bộ kiểm thật của dự án là `audit_db.py` (**36 phép**, đo
22/08) và `check_api.py` (**19 phép**) — cả hai đều cần **database sống + máy chủ đang
chạy**.

**Tiền đề này đã nhỏ đi một nửa từ 21/08:** `tools/diagnostics/soat_khoa_api.py` dựng uvicorn thật và
khẳng định 24 kỳ vọng **không cần Docker, không cần database** — nó chạy được vì
`backend/main.py` import xong mà chưa chạm PostgreSQL. Đó là thứ đầu tiên trong repo chạy
được trên một máy trắng, và là mẫu để nhân bản. Vẫn chưa có pytest và chưa có CI.

Master Plan giai đoạn 7 yêu cầu *"Phép kiểm mới trong `scripts/audit_db.py` và `backend/check_api.py` cho nguồn gateway"* — tức chính hai file này sẽ là nơi nghiệm thu Gateway. Chúng cần chạy được trên máy người khác **trước** ngày đó.

#### ⚪ D3. `docker-compose.yml` mới có Postgres + pgAdmin

Thiếu LiteLLM, Redis, Nginx. Chưa cần hôm nay, nhưng khi thêm thì `docker compose up -d` phải vẫn là một lệnh duy nhất — đó là thứ khiến người thứ hai vào được.

---

## 3. Nếu chỉ có một ngày, tôi làm theo thứ tự này

| | Việc | Thời gian | Vì sao trước |
|---|---|---|---|
| 1 | **A1** chốt 3 câu treo | 1h họp | Mọi thứ khác phụ thuộc |
| 2 | **A2** chốt project ID | 15 phút | Rẻ nhất, hỏng im lặng nhất |
| 3 | ~~**A3** ban hành quy ước username~~ | ✅ chốt 20/08, đo claim xong 21/08 | Ralli dùng `sub`, Hợp Đồng dùng `username` — xem §8f |
| 4 | ~~**A4 + A5** sửa sheet `Data Out`~~ | ✅ xong 27/08 | A4: 4 kiểu dữ liệu đã đúng. A5: đổi sang "Dẫn xuất từ Gateway" kèm quy tắc tính |
| 5 | ~~**B5** tách `account.kind`~~ | ✅ xong 20/08 | Nửa `health()` đã chữa con số sai; nửa `accounts()` gộp vào B1 |
| 6 | ~~**B1** gỡ `'app'` khỏi 8 chỗ đầu đọc~~ | ✅ xong 21/08 | Diễn tập 0/8 → 7/7 |
| 7 | ~~**B2** nguồn thứ tư vào `usage_resolved`~~ | ✅ xong 21/08 | Gộp cùng B1, đúng như khuyến nghị |
| 8 | ~~**C1 + C2** xác thực cho backend~~ | ✅ xong 21/08 | Khoá dùng chung, không phải JWT theo người — lý do ở mục C1 |

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

> ### ✅ Phép thử này ĐÃ CHẠY — 21/08/2026, `tools/diagnostics/dien_tap_gateway.py`
>
> Mục này viết ở thì *"dự đoán"* cho tới 22/08. Nó đã được chạy thật, và dự đoán đúng
> từng chữ.
>
> **Chạy trên code CHƯA sửa:** mọi phép kiểm vẫn xanh, dashboard **đứng im** trước 4
> triệu token — `usage_resolved` có thêm khoá nhưng `COALESCE(b,m,a)` không biết
> `gateway` nên trả `NULL`. Kỳ vọng đạt **0/8**.
>
> **Chạy trên code đã sửa:** `usage_by_account` **+3 dòng / +3.000.000 token**, tỷ lệ áp
> dụng **+3**, quy về người thật **+3.000.000**, gateway thắng billing. Kỳ vọng **7/7**.
>
> Dòng giả chèn trong TRANSACTION và `ROLLBACK` ở cuối, kể cả khi lỗi giữa chừng.

Chính sự im lặng đó là thứ đã được loại bỏ trước khi bước vào giai đoạn 6.
