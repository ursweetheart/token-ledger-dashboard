# Lượt hỏng không phải lượt miễn phí — `failed_is_not_free`

**Đo 04–05/09/2026 · dữ liệu 26/08 → 01/09/2026 · nhánh `Tuan-develop`**

---

## 1. Hình dạng lỗi, nói một lần cho gọn

> Nhà cung cấp **đã phục vụ xong** một request và **đã tính token** cho nó.
> Sau đó proxy hỏng ở khâu của mình, nên sổ ghi lượt đó là **hỏng, 0 token, 0 ms**.
> Bảng tổng hợp loại lượt hỏng ra — **điều đó đúng**.
> Nhưng phần bị loại **không bằng không**, và đó là chỗ sai.

Loại một lượt hỏng khỏi thống kê là quyết định đúng. Coi phần đã loại là số không là một quyết định **khác**, và nó chưa từng được ai quyết — nó chỉ xảy ra vì sổ ghi 0 và không ai hỏi lại.

Tên gọi riêng: **`failed_is_not_free`**. Cần một cái tên vì đây không phải "lỗi của Gateway"; nó là một hình dạng có thể tái diễn ở bất kỳ đường nạp nào phân biệt thành công / thất bại rồi lấy con số của bên thất bại làm 0.

---

## 2. Bằng chứng

Ngày 31/08/2026, giờ Việt Nam, dự án `project-e62bad30-a591-407b-ba7`:

| trục | nhà cung cấp | `fact_call` | lệch |
|---|---:|---:|---:|
| số lượt | 41 | 41 | **0** |
| token vào | 47.613 | 41.679 | +5.934 |
| token ra | 3.922 | 3.522 | +400 |
| **cộng token** | **51.535** | **45.201** | **+6.334 = 12,29%** |

Điều đắt giá nhất nằm ở dòng đầu: **số lượt khớp tuyệt đối**. Nếu chỉ kiểm một trục — và trục số lượt là trục dễ kiểm nhất — thì phép kiểm xanh và lỗi đi qua. Đó là lý do phép đối chiếu phải chạy trên **cả ba trục**.

Nhà cung cấp báo **41 request, `response_code = 200` cho TẤT CẢ**, không một lỗi nào. Sổ LiteLLM cùng ngày ghi **39 thành công + 5 hỏng**.

### 2.1. Chênh lệch nằm gọn ở một giờ

| giờ | ncc vào | `fc` vào | lệch | ncc ra | `fc` ra | lệch | ncc lượt | `fc` lượt | lệch |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 00 | 20 | 0 | +20 | 1 | 0 | +1 | 0 | 0 | 0 |
| 01 | 267 | 265 | +2 | 20 | 20 | 0 | 20 | 19 | **+1** |
| 02 | 23.577 | 17.713 | **+5.864** | 1.669 | 1.270 | **+399** | 13 | 14 | **−1** |
| 07 | 5.895 | 5.895 | **0** | 411 | 411 | **0** | 2 | 2 | 0 |
| 09 | 5.875 | 5.875 | **0** | 404 | 404 | **0** | 2 | 2 | 0 |
| 10 | 11.979 | 11.931 | +48 | 1.417 | 1.417 | 0 | 4 | 4 | 0 |
| **cộng** | **47.613** | **41.679** | **+5.934** | **3.922** | **3.522** | **+400** | **41** | **41** | **0** |

Hai điều đọc ra được:

- **Giờ 07 và 09 khớp tới từng token trên cả ba trục.** Nên cách đếm của ta **không sai một cách hệ thống**. Nếu sai hệ thống thì mọi giờ đều lệch.
- **98,8% chênh lệch token vào và 99,75% token ra dồn vào đúng giờ 02.**

### 2.2. Vì sao phải so ở mức NGÀY chứ không mức giờ

Nhìn cột cuối: giờ 01 lệch **+1** lượt, giờ 02 lệch **−1**, cộng lại bằng 0. Đó không phải hai lỗi triệt tiêu nhau — đó là **một request duy nhất rơi vào hai ô khác nhau** ở hai bên, vì nhà cung cấp gắn nhãn ô theo **thời điểm kết thúc** còn sổ Gateway ghi theo **thời điểm bắt đầu**.

Ở mức giờ, hiệu ứng ranh giới ô lẫn vào chênh lệch thật và không tách ra được. Ở mức ngày nó biến mất, trừ đúng nửa đêm. Nên `scripts/audit_db.py` nhóm I **so ở mức ngày**.

### 2.3. Giả thuyết "hai lượt bị ghi hỏng" — khớp nhưng **chưa chứng minh**

Chênh lệch giờ 02 (5.864 vào / 399 ra) có kích thước của **một cặp lượt gọi** như cặp đã quan sát được ở nơi khác trong sổ (233 + 5.643 vào / 3 + 400 ra), và trong sổ có hai lượt hỏng ở `02:27`, nằm đúng giữa cặp `02:24` và `02:29`.

Nhưng **cộng không khít**: dư **−12 token vào và −4 token ra**. Nên đây là **suy luận có cơ sở, không phải điều đã chứng minh**. Đừng viết con số này ra ngoài như một kết luận.

---

## 3. ⚠ Mẫu đo rất nhỏ — đọc con số 12,21% cho đúng

**Toàn sổ chỉ có 5 dòng hỏng, và cả 5 đều cùng một ngày.**

Con số **12,21%** là:

- của **riêng ngày 31/08/2026**, không phải của một kỳ;
- của **riêng nguyên nhân này** (LiteLLM so với Google), không phải toàn bộ chênh lệch;
- đo trên **một** dự án, **một** ngày có lưu lượng thật.

Phân rã đủ của 12,29% tổng:

```
   51.535  nha cung cap
 − 45.240  so LiteLLM (39 thanh cong + 5 hong)     -> 6.295 = 12,21%   failed_is_not_free
 − 45.201  fact_call                               ->    39            bo nap danh roi
   ------
    6.334  = 12,29%
```

**MUST NOT** nói "Gateway thiếu 12%" trống không. Một ngày không phải một tỷ lệ. Ngưỡng cảnh báo **chưa được ban hành**, và đó là chủ ý — xem mục 6.

---

## 4. Khoá của Gateway là **free tier**, nên lưu lượng này không bao giờ lên hoá đơn

Bằng chứng nằm ngay trong tên phép đo mà Cloud Monitoring trả về:

```
generativelanguage.googleapis.com/quota/generate_content_free_tier_input_token_count/usage
                                        ^^^^^^^^^
limit_name = GenerateContentInputTokensPerModelPerDay-FreeTier
                                                     ^^^^^^^^
```

Hệ quả, và nó đảo ngược một dòng trong Master Plan:

- Đường đối chiếu **bắt buộc đi qua Monitoring**, không qua `fact_billing_daily`.
- Phép kiểm cache của nhóm H (so `cached_tokens` với SKU cache trên hoá đơn) **sẽ không bao giờ chạy được cho lưu lượng Gateway**, dù chờ bao lâu. Nó vẫn đúng cho lưu lượng agent trả tiền.
- Master Plan STT 7 viết *"phép thử quyết định là hoá đơn 31/08"* — **phép thử đó không thắng được**. Lưu lượng free tier không xuất hiện trên hoá đơn nào cả.

---

## 5. Hai lỗi tôi đã mắc trong lúc đo — ghi lại vì cả hai đều **trông như kết quả đúng**

### 5.1. Cộng trùng hai nhánh hạn mức → con số "lệch 2,19 lần" hoàn toàn giả

Metric quota trả về **hai chuỗi giá trị y hệt nhau**, tách theo nhãn `limit_name`:

```
   GenerateContentInputTokensPerModelPerDay-FreeTier      47.613
   GenerateContentInputTokensPerModelPerMinute-FreeTier   47.613
   ------------------------------------------------------------
   cong ca hai                                            95.226   <- SAI
```

Cộng cả hai ra 95.226, và 95.226 / 43.500 ≈ **2,19**. Con số đó tôi đã báo ra như một phát hiện. Nó không tồn tại.

Không có gì báo lỗi: hai chuỗi cùng tên metric, cùng đơn vị, cùng mốc thời gian, chỉ khác một nhãn. Chỉ lộ ra khi soi nhãn của **từng chuỗi** thay vì tổng.

**Cách chặn hiện tại:** `db/load_provider.py` lấy nhánh `PerDay` **và so với nhánh `PerMinute`**; lệch thì dừng hẳn với `SystemExit`. Nó không lặng lẽ chọn một bên.

Lưu ý kèm: các metric `*_limit` là **hạn mức** đo bằng `ALIGN_MAX`, không phải số đếm — tổng của chúng ra `9.223.372.036.854.775.808` (đúng bằng trần `int64`). Đừng cộng.

### 5.2. `gcloud` cắt project ID ở 30 ký tự → sót 3 dự án, kết luận ngược

Tôi chạy `gcloud projects list --format=table` rồi kết luận **"20 project trên 2 tài khoản, không project nào ghi lưu lượng Gateway"**. Kết luận đó **sai**.

Hai lỗi chồng lên nhau:

1. `--format=table` **cắt project ID ở 30 ký tự**, làm ba mục "My First Project" khác nhau trông y hệt nhau.
2. Tôi chỉ truy vấn 9 trong 12 dự án.

Chạy lại với `--format=value(projectId)` tìm ra ngay `project-e62bad30-a591-407b-ba7`, **41 request ngày 31/08**, trong tài khoản `dinhthinhan18111971@gmail.com`. Đúng như người dùng đã nói ngay từ đầu.

**Bài học đủ hẹp để dùng lại:** khi câu trả lời là *"không tìm thấy gì"*, phải kiểm định dạng đầu ra trước khi tin — `table` là để người đọc, `value(...)` mới là để máy đọc.

### 5.3. Một phép đo phụ cũng từng sai, ghi luôn cho đủ

Metric `generativelanguage.googleapis.com/generate_content_usage_input_token_count` **không tồn tại**; nó trả HTTP 404 ở mọi project, và 404 trông y hệt lỗi phân quyền. Token vào chỉ có trong nhánh **quota**. Token **ra** thì ngược lại — nằm ở `generate_content_usage_output_token_count`, **ngoài** nhánh quota, và không bị tách đôi theo `limit_name`.

---

## 6. Vì sao **chưa** đặt ngưỡng phần trăm

Ta **đã biết** đáp án là 12,21% trước khi viết phép kiểm. Đặt ngưỡng bây giờ là chọn con số vừa khít với đáp án đã biết, tức là ngưỡng sẽ không bao giờ kêu vì nó được cắt theo đúng hình dạng của dữ liệu duy nhất từng thấy. Trái đúng kỷ luật **"ban hành ngưỡng trước kỳ đo"** mà spec `gateway-cache-reconciliation` đã chốt.

Nên nhóm I hiện **in con số ra và không phán xét** ở chiều thiếu hụt:

| chiều | xử lý | vì sao |
|---|---|---|
| nhà cung cấp **>** `fact_call` | **LƯU Ý** kèm tuyệt đối và tỷ lệ | Đây là chiều **kỳ vọng**. Báo hỏng thì phép kiểm đỏ vĩnh viễn rồi bị bỏ qua |
| `fact_call` **>** nhà cung cấp | **HỎNG**, không ngưỡng | Ta không thể tiêu thứ họ không phục vụ |

Chiều HỎNG **đã được nghiệm thu bằng cách tái tạo lỗi**: hạ vế nhà cung cấp xuống dưới `fact_call`, audit đỏ đúng cả ba trục và thoát mã 1; khôi phục bằng cách nạp lại từ đợt kéo, audit xanh trở lại, dữ liệu về nguyên trạng từng byte.

---

## 7. Cách tái tạo phép đo

```bash
docker compose up -d

# 1. Keo so cua nha cung cap (can mang + gcloud da dang nhap dung tai khoan)
python scripts/pull_monitoring.py --account dinhthinhan18111971@gmail.com \
                                  --projects project-e62bad30-a591-407b-ba7

# 2. Nap vao bang doi chieu
python db/load_provider.py

# 3. Doc ket qua - nhom I la phep doi chieu, nhom J la ke toan tung dong
python scripts/audit_db.py
```

Không có mạng thì bỏ bước 1: đợt kéo ngày 04/09 đã nằm trên đĩa ở `data/raw_google_console/du_lieu_giam_sat/2026-09-04-1h-dinhthinhan18111971/`, và bước 2–3 chạy **hoàn toàn ngoại tuyến**.

⚠ **Cửa sổ lưu giữ của Cloud Monitoring trượt.** Đo 04/09/2026 trên hai dự án có lịch sử dài thì mép dữ liệu ở **22/01/2026**, tức **225 ngày**. Con số "196 → 112 ngày" trong ghi chú cũ đo trên **một họ metric khác**, nên **không so sánh được** với con số này. Xoá thư mục kéo cũ là mất vĩnh viễn.

---

## 8. Câu hỏi còn treo

**Hai lượt bị ghi 0 token là một request thử lại hai lần, hay hai request khác nhau?**

`LiteLLM_SpendLogs` **không có trường nào nối một lượt thử lại về lượt gốc** — không `parent_request_id`, không `retry_of`, không nhóm. Nên câu hỏi này không trả lời được bằng dữ liệu đang có.

Vì sao nó quan trọng chứ không phải chi tiết học thuật: nếu là **một** request thử lại hai lần thì số lượt nghiệp vụ thật là 40 chứ không phải 41, và mọi con số "trên mỗi lượt" đang chia sai mẫu số. Nếu là **hai** request khác nhau thì 41 đúng.

Muốn trả lời cần bật ghi log ở tầng router của LiteLLM, hoặc so dấu vân tay nội dung prompt — cả hai đều ngoài phạm vi lần đo này.

---

## 9. Phát hiện phụ, không nằm trong kế hoạch

### 9.1. Sáu dòng sổ nguồn không vào được `fact_call`

| dòng | ngày | trạng thái | token | lý do |
|---|---|---|---:|---|
| `3GWSavLjDcrp2roPvLj7iAY` | 29/08 | thành công | 17 | không có tag định danh |
| `lG-UarHhIYXmosUPv4ihmQ8` | 31/08 | **thành công** | 25 | không có tag định danh |
| `372eb089-…` | 31/08 | hỏng | 0 | không có tag định danh |
| `6ff4a85c-…` | 31/08 | hỏng | 14 | không có tag định danh |
| `GsaVavubFOD21e8PnvHx2QE` | 01/09 | thành công | 352 | không có tag định danh |
| `GsaVavubFOD21e8PnvHx2QE_cache_hit…` | 01/09 | thành công | 352 | **bản sao cú cache hit** |

**Nguyên nhân đã chứng minh, không còn là nghi vấn.** Nhận định trước đó — *"chỉ 1 trong 3 dòng thiếu tag, nên lời giải thích sai cho hai dòng kia"* — là **sai**: nó đếm *mọi* tag, kể cả `User-Agent:` do LiteLLM tự thêm, trong khi tag định danh chỉ là tag **khớp một dòng `dim_agent.code`**. Chạy `db/load_gateway.py --full` rút hẳn mốc nước vẫn cho `inserted 0`, nên hai nghi can cũ (**mốc nước**, **ranh giới ngày**) đều **bị bác bỏ**.

`fact_call.agent_id` là `NOT NULL`, nên lưu lượng không quy được về agent nào **không thể lưu**. Đó là **cùng một hình dạng lỗi với `failed_is_not_free`, chỉ khác trục**: lưu lượng không quy được về ai cũng không phải lưu lượng miễn phí. Sửa được nó cần một agent "không quy được" hoặc `agent_id` cho phép NULL — **ngoài phạm vi change này**, ghi lại thành khoản nợ.

### 9.2. Bản sao của cú cache hit — quả mìn hẹn giờ

LiteLLM ghi **thêm** một dòng cho cú cache hit, mang chính `request_id` của dòng gốc cộng hậu tố `_cache_hit<epoch>`, và **lặp lại nguyên token**. Toàn sổ có đúng 1 dòng như vậy (352 token); dòng gốc tồn tại với đúng 352 token; và **nhà cung cấp xác nhận độc lập** ngày 01/09 họ phục vụ **1 lượt**, 8 vào + 344 ra.

Hôm nay dòng này rớt vì *không có tag định danh* — một lý do **chẳng liên quan gì**. Ngày nào khâu định danh được nới ra để cứu 5 dòng ở mục 9.1, bản sao sẽ theo **cùng cái cửa đó** mà vào và đếm đôi 352 token, và **không phép kiểm nào hiện có bắt được**: tổng vẫn "khớp sổ nguồn", chỉ có điều sổ nguồn tự nó đã đếm đôi.

Nên `db/load_gateway.py` nay loại nó **tường minh, có tên, trước mọi bước khác**.

---

## 10. Đã đổi những gì

| tệp | đổi gì |
|---|---|
| `db/migrations/…/011_so_nha_cung_cap.*` | Bảng `fact_provider_daily`. **`usage_resolved` không đọc nó** |
| `db/load_provider.py` | Nạp một đợt kéo Monitoring vào bảng đó; ba cái bẫy ở mục 5 được chặn bằng mã, không bằng ghi chú |
| `scripts/pull_monitoring.py` | Thêm `--account`; xác thực **trước** khi tạo thư mục kết quả |
| `scripts/audit_db.py` | **Nhóm I** — đối chiếu ba trục, mức ngày. **Nhóm J** — kế toán từng dòng sổ nguồn |
| `db/load_gateway.py` | In token của lượt hỏng kèm chữ *"điều sổ khai"*; đếm dòng bị bỏ **kèm token theo từng lý do**; loại bản sao cache hit tường minh |
| `scripts/rebuild_db.py` | Thêm bước `Provider ledger` — bước 1 xoá sạch schema nên thiếu nó là bảng rỗng vĩnh viễn |
| `db/02_catalog.sql` | Hai bí danh model cho nguồn `monitoring` |

**Không một dòng dữ liệu lưu lượng nào bị đụng.** `usage_resolved` giữ nguyên `1.276 dòng | 915.969.971 token | 122.504` trước và sau.
