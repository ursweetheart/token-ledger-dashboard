# Đo bản ghi LiteLLM — cách đo, kết quả, và chỗ chưa chắc

Thuộc change `measure-what-the-gateway-records`, task 6.1.

- **Ngày đo:** 26/08/2026 (change soạn 24/08 — tên file giữ theo ngày soạn)
- **Nhật ký chi tiết:** `nhat-ky-26-08-sang.md`, mục 2–8 (lượt 1–4) và **mục 16** (lượt 5)
- **File bằng chứng:** `tools/probe-gateway/ket-qua/`

> ⚠️ **Đọc mục 16 trước mục 5 của nhật ký.** Mục 5 chứa một phán quyết SAI đã bị gạch
> (A3 "bác bỏ"). Lượt đo 4b chạy thiếu điều kiện; lượt 5 đo lại và cho kết quả ngược.

---

## 1. Phiên bản — phép đo chỉ tái lập được khi ba thứ này khớp

```
   fork          litellm_rang_dong   commit f005afa146   cay lam viec SACH (0 file)
   image         litellm_rang_dong:probe
                 sha256:cc794ac6c22212d21ed2999f140378aec8167ffccfff81b56816bb190
   goi ben trong litellm 1.99.0 · enterprise 0.1.59 · proxy-extras 0.4.89
   provider      Google AI Studio (tien to `gemini/`), key project MOI, KHONG gan billing
   database do   postgres:16-alpine, cong 127.0.0.1:5433  (tach khoi token-ledger-postgres)
```

Fork nằm **ngang hàng** dự án (`D:\RangDonk\litellm_rang_dong`), không lồng bên trong.
Lý do: repo lồng repo, `git clean -xfd` sẽ xoá cả fork, số file nhảy 469 → 10.241, và
`enterprise/` mang giấy phép thương mại.

## 2. Cách đo

Cấu hình và compose nằm ở `tools/probe-gateway/` (**của dự án ta**, không phải của fork):

```
   tools/probe-gateway/
     config.probe.yaml          model_list + general_settings + litellm_settings
     docker-compose.probe.yml   build context tro nguoc ra ../../../litellm_rang_dong
     ket-qua/                   dau ra cua tung luot do
```

Dựng và bắn một lượt:

```bash
docker compose -f tools/probe-gateway/docker-compose.probe.yml --env-file .env up -d
curl -s http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-probe-local" \
  -H "Content-Type: application/json" \
  -H "X-User: <chuoi-danh-tinh>" \
  -d '{"model":"probe-mock","messages":[{"role":"user","content":"ping"}]}'
docker exec litellm-probe-db-1 psql -U llmproxy -d litellm -v ON_ERROR_STOP=1 -At \
  -c 'SELECT row_to_json(t) FROM (SELECT * FROM "LiteLLM_SpendLogs"
      ORDER BY "startTime" DESC LIMIT 1) t;'
```

Bốn model khai sẵn: `probe-mock` (không gọi Google, không tốn credit) · `probe-flash` ·
`probe-flash3` · `probe-36`.

### Bốn cái bẫy đã dính, và cách chặn

Phép đo hỏng ở đây **trông y hệt** phép đo đạt. Bốn quy tắc dưới đây đổi bằng lỗi thật:

| Bẫy | Chặn bằng |
|---|---|
| Nối ống dẫn vào lệnh nền → `$?` là của `tail`, không phải của lệnh thật | Không nối ống cho lệnh chạy nền; đo mã thoát của đúng lệnh cần đo |
| Nuốt `stderr`, query chết mà vẫn ra *"lệch 0 — đạt"* | `ON_ERROR_STOP=1` **và** kiểm `returncode` |
| `pg_dump`/`psql` trả mã 0 rồi để lại file rỗng | Phân biệt *file rỗng* với *không có dữ liệu* — kiểm `-s` |
| `grep -c` ra `1` cho một lệnh chưa hề chạy | Mở ra **đọc thân**, đừng tin con số đếm |

## 3. Bốn khoá cấu hình quyết định cột nào có dữ liệu

Đây là kết quả trung tâm. Ba khoá đầu **phải bật** thì bản ghi mới đủ; khoá thứ tư
**phải tắt** ở bản chạy thật.

| Khoá | Tầng | Bản thật | Nó mở/đóng cái gì |
|---|---|---|---|
| `user_header_name: "X-User"` | `general_settings` | ✅ bật | header đã khai tên → cột `end_user` |
| `store_prompts_in_spend_logs: true` | `general_settings` | ✅ bật | mở cột `proxy_server_request` (chứa **mọi** header) |
| `turn_off_message_logging: true` | `litellm_settings` | ✅ bật | xoá nội dung prompt, **giữ** header |
| `forward_client_headers_to_llm_api` | `general_settings` | 🔴 **TẮT** | gửi mọi header `x-*` sang nhà cung cấp |

**Vì sao khoá 4 phải tắt.** Đo được ở lượt 5c, gọi thật ra Google:

```
   curl -X POST https://generativelanguage.googleapis.com/v1beta/models/
                gemini-2.5-flash:generateContent
     -H 'x-user: REDACTED'
     -H 'x-ralli-trace: probe-5c-that'
     -H 'x-openwebui-user-email: tuan.tran@example.invalid'
```

Bật nó nghĩa là **mỗi request gửi email nhân viên và token đăng nhập sang Google**. Ba khoá
trên đã đủ để ghi sổ; khoá này không mua thêm gì cho việc ghi.

**Vì sao khoá 2 nguy hiểm nếu thiếu khoá 3.** `store_prompts_in_spend_logs` một mình sẽ lưu
**nội dung câu hỏi** vào database — nơi đã có 927 email nhân viên thật. Khoá 3 gỡ đúng chỗ
đó: đo được bằng cách gửi chuỗi mồi `BI-MAT-KHONG-DUOC-LUU-VAO-DB` rồi tìm trong cả dòng
19.031 byte → **0 lần**, trong khi 8/8 header còn nguyên.

## 4. Bảng đối chiếu — gửi thế nào thì vào cột nào

| Cách gửi danh tính | Cột nhận | Điều kiện |
|---|---|---|
| Trường `"user"` trong **body** | `end_user` | không cần gì thêm |
| Header khai ở `user_header_name` | `end_user` | cần khoá 1 |
| Header `x-litellm-tags` | `request_tags` | không cần gì thêm |
| **Header bất kỳ** (kể cả tự đặt tên) | `proxy_server_request.metadata.headers` | cần khoá 2 |
| `metadata` trong body | ❌ không vào đâu cả | — |

Ví dụ đo được, 8/8 header vào sổ nguyên văn:

```
   host  accept  user-agent  content-type  content-length
   x-user                   eyJhbGciOiJIUzI1NiIs...   (JWT 260 ky tu, DAY DU)
   x-ralli-trace            probe-jwt-01               (header tu dat)
   x-openwebui-user-email   tuan.tran@example.invalid
```

`end_user` được ghi **kể cả khi request thất bại** — lượt 404 vẫn có `status=failure` kèm
`end_user` đầy đủ.

## 5. 34 cột `LiteLLM_SpendLogs`

```
   agent_id            api_base            api_key             cache_hit
   cache_key           call_type           completionStartTime completion_tokens
   created_at          custom_llm_provider endTime             end_user
   mcp_namespaced_tool_name  messages      metadata            model
   model_group         model_id            organization_id     prompt_tokens
   proxy_server_request  request_duration_ms  request_id       request_tags
   requester_ip_address  response          session_id          spend
   startTime           status              team_id             total_tokens
   updated_at          user
```

Dòng nguyên vẹn đã chép ra:

| File | Lượt | Cấu hình |
|---|---|---|
| `spendlogs-mot-dong-3a.json` | 3a | mock khai ở tầng config |
| `spendlogs-mot-dong-4b-that.json` | 4b | **thiếu** 3 khoá → `proxy_server_request = {}` |
| `spendlogs-mot-dong-luot5.json` | 5 | đủ khoá → 8 header |
| `spendlogs-mot-dong-5b.json` | 5b | đủ khoá + redaction → 8 header, 0 prompt |

## 6. Bốn phát hiện về con số

**① `completion_tokens` đã GỒM token suy luận.** `454 = 432 + 22`. Cộng thêm lần nữa khi
đối chiếu hoá đơn là nhân đôi — đúng loại lỗi từng dính với `cached_tokens`.

**② `spend` dựng lại được đến từng chữ số.**
`35×0,00000075 + 432×0,00000375 + 22×0,00000375 = 0,00172875`.

**③ LiteLLM ghi cả request THẤT BẠI**, kèm token count. `fact_request` **bắt buộc** phải
có cột `status`.

**④ `thinking_enabled` không có cột riêng, nhưng DẪN XUẤT được.** Khoá `reasoning_tokens`
**vắng mặt hoàn toàn** khi tắt suy luận — không phải bằng `0`. Sheet `Data Out` phải ghi
**"dẫn xuất từ Gateway"** kèm quy tắc tính, không ghi "Nguồn". `output_modality` cũng vậy.

Một request đơn lẻ không chứng minh được ④. Cặp bật/tắt cùng model, cùng câu hỏi, khác đúng
một tham số mới chứng minh được.

## 7. Vertex hay AI Studio — khác biệt bị xoá trước khi ghi

Google **có** khác biệt thật: `candidatesTokenCount` **gồm** token suy nghĩ trên Gemini API,
**không gồm** trên Vertex. Nhưng LiteLLM chuẩn hoá bằng phép cộng
(`is_candidate_token_count_inclusive`), phát hiện bằng **số học** chứ không bằng tên nhà
cung cấp — nên khác biệt bị xoá **trước khi** ghi `SpendLogs`. Kết luận: chọn đường rẻ nhất,
key AI Studio project mới không gắn billing. **0 cột lệch.**

## 8. Chưa chắc chắn — không trộn vào phần trên

| Điều | Vì sao chưa chắc |
|---|---|
| **Ralli gửi đúng hình dạng ta giả lập** | Lượt 5 dùng `curl` mô phỏng theo hiểu biết hiện tại. Chưa biết Ralli có tiền xử lý ở server không. Cách trả lời dứt điểm: trỏ `base_url` của Ralli vào `http://127.0.0.1:4000` — cái gì đáp xuống chính là cái Ralli thật sự gửi |
| **`end_user` chịu được JWT dài bao nhiêu** | Bản đo dùng token 260 ký tự. Token thật của Ralli dài hơn. Chưa thử ngưỡng cắt |
| **JWT làm danh tính** | Token đổi mỗi lần đăng nhập → cùng một người thành nhiều `end_user`. Nên đặt claim **`sub`** vào `end_user`, để JWT nguyên vẹn nằm ở `proxy_server_request` làm vết truy |
| **Bảng giá tự dựng** | `gemini-2.5-flash` báo *"model isn't mapped yet"* trong log nhưng vẫn ra `response_cost`. Chưa truy nguồn con số đó |

## 9. Việc mở ra từ phép đo này

| | Việc | Ghi ở |
|---|---|---|
| 🔴 | `guess_model()` trả `None` cho `gemini-3.6-flash`. **Xác nhận sống:** Google trả `404` cho `gemini-2.5-flash` kèm *"no longer available to new users… use gemini-3.6-flash"* | task 6.4(a) |
| 🔴 | `forward_client_headers_to_llm_api` phải TẮT ở bản thật | mục 3 trên |
| 🟡 | `gemini-2.5-flash-image` bị gộp vào `gemini-2.5-flash`, mất nhánh ảnh | task 6.4(b) |
| 🟡 | `gemini-2.0-flash` (9,5% lưu lượng) đã rút khỏi API | task 6.4(c) |
| 🟡 | Sheet `Data Out` §A5: đổi "Nguồn" thành "dẫn xuất" | task 6.2 |

## 10. Hệ quả cho giai đoạn 7 — "bốn nguồn" chỉ đúng với 1 trên 8 agent

Task 6.5. Quan sát gốc: **Trợ lý ảo Ralli không có dòng monitoring nào.** Đo lại
27/08/2026 trên `token_ledger`, chỉ-đọc:

```
   agent                          dong monitoring    token nguon 'app'
   Chatbot Contact Center                 497.953                    0
   Sale Agent                              66.345                    0
   Multi modal AI Invoice                  11.674                    0
   Phan Loai Phan Hoi Tiep Thi              3.304                    0
   Tro Ly Ao Hop Dong                       2.304           62.706.827
   Phan Loai Du Lieu CRM                    2.142                    0
   Tools Quizzer                              195                    0
   Tro ly ao Ralli                              0           47.933.778   <--
```

Giai đoạn 7 yêu cầu *"báo cáo đối chiếu chênh lệch giữa **bốn** nguồn"*. Bảng trên nói
rằng bốn nguồn **không tồn tại đồng thời ở agent nào ngoài một**:

| Agent | Nguồn thật sự có (sau khi Gateway chạy) | Số nguồn |
|---|---|---|
| Trợ Lý Ảo Hợp Đồng | `billing` · `monitoring` · `app` · `gateway` | **4** |
| Trợ lý ảo Ralli | `billing` · `app` · `gateway` — **không có `monitoring`** | 3 |
| 6 agent còn lại | `billing` · `monitoring` · `gateway` — **không có `app`** | 3 |

### Ba hệ quả phải xử lý trước khi mở cửa sổ đối chiếu

**① Báo cáo phải chia theo agent × nguồn, không được có một con số tổng.**
Một dòng *"bốn nguồn khớp 99%"* sẽ đúng về số học và sai về ý nghĩa: nó gộp một agent có
bốn nguồn với bảy agent chỉ có ba, và giấu mất chuyện Ralli chưa từng có nguồn thứ ba nào
để đối chứng.

**② Ralli là agent có ít đối chứng nhất, lại đúng là agent bất định nhất.**
Ralli mang **47.933.778 token** ở nguồn `app` — nguồn cấp người dùng lớn thứ hai. Nếu số
Gateway của Ralli lệch so với `app`, **không có ý kiến thứ ba để phân xử**: `billing` chỉ
có tổng theo project, không tách được về người. Với Hợp Đồng thì có `monitoring` đứng giữa.

Trùng hợp bất lợi: Ralli cũng chính là agent mà ta **chưa biết** có tiền xử lý request ở
server hay không (mục 8). Chỗ mù lớn nhất rơi đúng vào chỗ ít đối chứng nhất.

→ Vì vậy việc *trỏ `base_url` của Ralli vào Gateway để xem nó thật sự gửi gì* không phải
việc làm cho đủ, nó là việc **bù lại nguồn đối chứng đang thiếu**.

**③ Không được coi "thiếu monitoring" là "lệch 0%".**
Phép đối chiếu nào chạy `COALESCE(monitoring, 0)` cho Ralli sẽ ra chênh lệch bằng đúng
toàn bộ lượng token của Ralli, hoặc bằng 0 — tuỳ chiều trừ — và cả hai đều là con số vô
nghĩa. Ô không có nguồn phải là **NULL** và phải được báo cáo là *"không đối chiếu được"*,
tách khỏi *"đối chiếu được và khớp"*.
