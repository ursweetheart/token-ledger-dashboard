# Nhật ký chiều 20/08/2026

Tiếp theo `nhat-ky-20-08-sang.md`. Đọc nhanh: mục 1 và mục 6.

**10 commit** (13:26 → 17:10). Mọi phép kiểm xanh. **Chưa push.**

---

## 1. Tóm tắt

Buổi sáng sửa **ba con số sai** trên màn hình. Buổi chiều làm hai việc khác hẳn:

> **Gỡ nốt phần gõ cứng cuối cùng ra khỏi frontend**, và **trả lời hết các câu hỏi
> đang chặn việc bắt tay vào API Gateway**.

Nhóm A trong `viec-can-lam-truoc-api-gateway.md` — nhóm *"quyết định, chặn mọi thứ phía
sau"* — từ **3 việc đỏ** xuống còn **2 việc nhỏ**.

---

## 2. Việc code

### ① Bỏ 108 đơn vị gõ cứng khỏi `app.js`

Cây phòng ban giờ đọc từ database. `app.js` nhẹ **176 dòng**.

| | Trước | Sau |
|---|---|---|
| Hàng cấp 1 | 21 | **21** |
| Tổng tiền | $88,68 | **$88,68** |
| Đơn vị lệch cha | 0 | **0** |

Không lệch một xu — đúng như phải thế, vì đây là đổi **nguồn**, không đổi **số**.

Ba thứ chuyển từ mã giao diện vào database, mỗi thứ là một sự thật về công ty mà trước đây
chỉ người viết frontend biết:

```
canonical_unit_id     4 cặp phòng ban trùng giữa hai cây tổ chức
is_report_aggregate   2 cấp gom mà báo cáo bắt đầu từ bên dưới
service_account       (làm buổi sáng) 6 agent một-người-dùng
```

### ② Mọi con số tiền nói rõ nó từ đâu ra

**28,2% tiền trên dashboard chưa từng đến từ hoá đơn nào** — $114,41 trên $406,39. Trước
hôm nay không ô nào nói điều đó.

Và nó **không rải đều**:

| Agent | % suy từ bảng giá |
|---|---:|
| **Trợ lý ảo Ralli** | **100,0%** — chưa nối Google Billing |
| **Trợ Lý Ảo Hợp Đồng** | 77,7% |
| Chatbot Contact Center | 2,8% |

Giờ ô có phần suy ra mang dấu **`≈`** và tooltip nói **bao nhiêu phần trăm**, cộng thêm
CSV có cột `Nguồn tiền`. Ngưỡng 2% để dấu hiệu không thành nhiễu — một dấu xuất hiện khắp
nơi thì hết là dấu hiệu.

**Tại sao phải phân biệt hai lý do:** hoá đơn về trễ thì vài ngày tự hết; agent chưa nối
billing thì **không bao giờ**. Gộp chung một nhãn *"ước tính"* là chôn mất một việc cần
người xử lý.

### ③ Bỏ email nhân viên khỏi API

`/api/accounts` từng trả **927 địa chỉ thư** vì frontend dùng email làm khoá ghép. Nhưng
`/api/usage-by-account` đã có `account_id` — ghép bằng khoá số thì **chính xác hơn** và
không phụ thuộc hoa/thường.

Đổi xong cho kết quả **y hệt**: `TTDL&DHS` 2/6, `TT&TMĐT` 1/3, `PBH3` 9/266.

Đây là **phòng thủ theo chiều sâu, không thay cho xác thực** — máy chủ vẫn chưa có xác
thực nào (mục C1 vẫn đỏ).

### ④ Hai ghi chú chống trôi

- **CORS** đọc từ `DASHBOARD_ORIGINS` thay vì `*`. Ghi chú cũ tự biện minh *"chấp nhận được
  vì chỉ lắng nghe trên 127.0.0.1"* — lý do đó hết hiệu lực đúng ngày Gateway lên, mà
  không ai được báo.
- **`gcp_project_id`** được ghi rõ là phép suy `agent_id ← project` **có hạn sử dụng**. Sau
  cân bằng tải, hoá đơn ghi nợ project B cho lưu lượng của Agent A, và dashboard sẽ báo B
  tiêu tiền của A **mà không lỗi nào báo**.

---

## 3. Bốn quyết định anh đã chốt

| # | Câu hỏi | Quyết định |
|---|---|---|
| **A1-1** | Lịch sử cũ đi đâu? | **Một database** + cột `data_era`. Và **giữ `fact_monitoring`** (đóng băng) — 583.917 dòng đó không dựng lại được |
| **A1-2** | Có ghi `fact_attempt`? | **CÓ.** Dữ liệu retry không dựng lại được về sau |
| **A1-3** | Ngân sách do ai chặn? | **LiteLLM**, `$70` mỗi agent, cảnh báo 50% · 90%, chạm 100% thì chặn |
| **A2** | Project ID | **Database đúng cả hai chỗ** — `tla-ralli` và `tools-quizz`. Sửa file `.docx` |
| **A3** | Danh tính người dùng | **Agent tự trích từ JWT** rồi gửi lên Gateway. Sáu agent một-người-dùng dùng tên cố định |

Ba việc kéo theo, đã ghi vào tài liệu để người viết `config.yaml` không phải tự phát hiện:

1. Dòng `scrape` để **NULL** ở cột mới → truy vấn dùng cột mới sẽ **âm thầm bỏ 8 tháng lịch sử**
2. **Cảnh báo Google Cloud phải giữ** — nó là thứ duy nhất bắt được lưu lượng đi vòng qua
   Gateway. Project gắn tài khoản khách hàng nên cảnh báo được nhưng **không chặn được**
3. **Ralli chặn theo token**, LiteLLM chặn theo USD → giữ trần token ở tầng app Ralli

Và **A3 xoá luôn một mục**: có username là tra được `account.unit_id`, nên **agent không
cần gửi phòng ban**. Bắt gửi là tạo nguồn thứ hai cho một sự thật đã có.

---

## 4. Ba lần "đo lại thì sai"

Đây là phần đáng đọc nhất, vì cả ba đều là **lập luận nghe hợp lý** mà nếu không đo thì đã
đi tiếp theo hướng sai.

### ① "Bỏ `dim_function` cho gọn" — RÚT

Nhận định: *8 dòng, `is_user_facing` chưa từng có giá trị, không endpoint nào đọc.*

Đo ra: **`fact_call.function_code` có giá trị ở 8.330/8.330 dòng**, và `Data Out` #10 ghi
`function` sẽ do **Gateway gửi**. Bảng không chết — nó **chưa được phơi lên giao diện**. Bỏ
bây giờ là xoá rồi dựng lại, mất luôn 2 nhãn tiếng Việt đang có.

### ② "Phân biệt hai lý do bằng *không có dòng hoá đơn nào*" — SAI

Đúng với Ralli. Nhưng chọn riêng ngày 17/08 thì **không agent nào có hoá đơn**, và màn hình
dán nhãn *"chưa nối billing"* cho **cả 7 agent đã nối**.

Bắt được vì tôi chọn thử đúng ngày đó và **đọc câu nó nói ra**. Dấu hiệu đúng là
`dim_agent.has_google_source` — database đã tách riêng nó khỏi `gcp_project_id` từ 14/08 vì
đúng lý do này.

### ③ Công cụ đo của tôi dính bẫy `cached`

`tools/do_tien_suy_ra.py` cộng `cached_tokens` ở **mọi** dòng, trong khi chỉ nguồn billing
mới có cached nằm **ngoài** input — của app nó là **tập con** của prompt, cộng vào là đếm
hai lần. May là con số đầu 28,2% không đổi, chỉ lệch chữ số thập phân thứ tư.

Đây là cái bẫy `api.js` đã ghi chú sẵn, và tôi vẫn dính.

---

## 5. Một phát hiện ngoài kế hoạch

Chạy `gen_catalog.py` để kiểm mục D1 thì lộ ra:

> **`Multi modal AI Invoice` bị khai là đã dừng từ 25/07** (`is_running = FALSE`), nhưng có
> **452.096 token / 88 lượt sau ngày đó**, mới nhất **17/08** — đúng ngày mới nhất của cả
> database.

`is_running` **gõ tay có chủ đích** — `gen_catalog.py` giải thích rõ vì sao không suy tự
động: một ngưỡng kiểu *"bao nhiêu ngày không có dữ liệu thì coi là ngừng"* sẽ phân loại sai
mỗi khi agent nghỉ lễ dài. Lập luận đúng. Nhưng **gõ tay thì trôi, và trôi im lặng.**

Đã thêm phép kiểm vào `audit_db.py`. Nó **không tự sửa** — *agent chạy lại thật hay còn
tiến trình sót* là câu hỏi nghiệp vụ, cần người trả lời. Nó chỉ không cho cờ và dữ liệu
mâu thuẫn trong im lặng.

**Phiên bản đầu của phép kiểm đó không bao giờ kêu được:** nó so với `data_to`, mà cột này
suy từ chính dữ liệu nên luôn bằng ngày cuối. Một phép kiểm không thể kêu còn tệ hơn không
có — nó tạo cảm giác đã được kiểm. Đã đổi sang so với ngày cuối của cả database: agent ngừng
thật thì dữ liệu phải dừng **trước** những agent khác.

---

## 6. Đang ở đâu, mai làm gì

### Xong chiều nay

| Giờ | | |
|---|---|---|
| 13:26 | `0ae235f` | Proposal: ghi nhãn tiền suy ra trên toàn dashboard |
| 13:33 | `bd0e442` | Bỏ 108 đơn vị gõ cứng, cây đọc từ database |
| 13:48 | `9b4dcdb` | Mọi ô tiền nói rõ hoá đơn hay suy ra |
| 13:54 | `85b719e` | Bắt agent khai đã dừng mà vẫn chạy |
| 14:48 | `111faaa` | Chốt câu 1: một database + giữ `fact_monitoring` |
| 16:06 | `eef023f` | Chốt câu 2 và 3: có ghi `fact_attempt`, LiteLLM chặn $70/agent |
| 16:21 | `30858df` | Chốt A3: agent tự trích JWT |
| 16:32 | `5253c90` | Chốt A2: database đúng cả hai project ID |
| 17:10 | `c3d7169` | Bỏ email khỏi API, CORS theo biến môi trường, ghi chú `gcp_project_id` |
| 17:10 | `f3cd51a` | Rút B4 |

```
audit_db 33 phép / 0 hỏng   ·   check_api 16/16
test JS 6 + 7               ·   kiem_so_artifact 23/23
```

Hai change OpenSpec: `serve-department-metrics-from-database` **49/49 xong**,
`label-derived-cost-across-dashboard` **23/24**.

### Việc còn treo, xếp theo mức khẩn

**🔴 C1 — backend không có xác thực nào.** `/api/accounts` vẫn trả 937 người kèm họ tên và
phòng ban (đã bỏ email). An toàn hiện tại **chỉ vì** uvicorn gắn `127.0.0.1` — một dòng cấu
hình, không phải một cơ chế. Ý đề xuất: một khoá dùng chung kiểm bằng một dependency
(~20 dòng, làm ngay), rồi JWT đầy đủ theo Master Plan giai đoạn 3.

**🔴 Hai việc chỉ anh làm được:**
- Claim nào trong JWT là username, và **hai app có dùng cùng một claim không**.
  `01_schema.sql` ghi *"Ralli đôi khi ghi username vào chỗ ObjectId"* — nếu `sub` của Ralli
  là ObjectId thì hướng A3 phải điều chỉnh. Đo mất 2 phút.
- **`Multi modal AI Invoice` chạy lại thật, hay còn tiến trình sót?**

**🟡 Còn lại:**

| | |
|---|---|
| A4 · A5 · A6 | Sửa 3 kiểu sai trong sheet `Data Out` · hai cột `think`/`output_modality` sau Gateway không có dòng mới · độ mịn thời gian |
| B1 + B2 | `source='app'` còn 22 chỗ · `usage_resolved` chưa nhận nguồn thứ tư. **Nên gộp một change** — làm riêng thì sửa hai lần cùng những câu SQL |
| D2 | Vẫn **0 file test Python** |
| D3 | Docker thiếu LiteLLM · Redis · Nginx |
| CSV | Chưa ai mở bằng Excel tiếng Việt xem cột có vỡ không |

### Phép nghiệm thu cho câu "đã sẵn sàng chưa"

Vẫn là phép thử đề xuất từ đầu, và giờ làm được trong một buổi:

> Chèn vài chục dòng giả `source='gateway'` vào database thử, chạy `audit_db.py` +
> `check_api.py`.
>
> **Nếu mọi phép kiểm xanh mà dashboard không đổi một con số nào** — đó chính là câu trả
> lời: 22 chỗ hardcode `source='app'` đã lặng lẽ lọc hết dữ liệu Gateway ra ngoài.
