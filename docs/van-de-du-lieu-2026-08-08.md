# Các vấn đề của dữ liệu hiện tại

> **Phạm vi:** khuyết tật của **dữ liệu gốc** — thứ ứng dụng và Google trả về
> **Mục đích:** liệt kê đầy đủ vấn đề, kèm bằng chứng, để làm nguyên liệu viết báo cáo

---

## Cách đọc tài liệu này

Mỗi vấn đề gồm bốn phần:

| Phần | Nội dung |
|---|---|
| **Vấn đề** | Mô tả ngắn cái đang sai hoặc đang thiếu |
| **Vì sao** | Nguyên nhân |
| **Bằng chứng** | Số liệu và cách kiểm ra được — phần này để người viết báo cáo tin được |
| **Ảnh hưởng** | Nếu bỏ qua thì dashboard sai ở đâu |

Mức độ chắc chắn được đánh dấu ngay ở phần **Vì sao**:

- ✅ **Chứng minh được** — có số liệu đối chiếu từ hai nguồn độc lập trở lên
- ⚠️ **Suy luận** — hợp lý nhưng chưa kiểm chứng, cần hỏi người biết việc

Phân biệt hai loại này rất quan trọng. Trộn lẫn sẽ khiến người đọc tin nhầm mức độ chắc chắn của kết luận.

---

## Bối cảnh chung: dữ liệu đến từ đâu

Dashboard đang ghép **ba nguồn** khác nhau, mỗi nguồn đo một thứ khác nhau:

| Nguồn | Đo cái gì | Ai tạo ra |
|---|---|---|
| **API của ứng dụng** | Lượt gọi, token, người dùng, phòng ban | Đội phát triển từng ứng dụng tự ghi |
| **Google Billing** | Tiền thật, token thật theo SKU | Google, đây là hoá đơn |
| **Google Monitoring** | Số request, mã lỗi, độ trễ | Google, đo ở tầng hạ tầng |

Nguyên tắc: **Google là chân lý về tiền và lượt gọi, ứng dụng là chân lý về ai dùng.** Gần như mọi vấn đề dưới đây đều sinh ra ở chỗ hai bên không khớp nhau.

Ba nguồn này cũng có **phạm vi thời gian khác nhau**, nên nhiều so sánh chỉ hợp lệ ở phần giao nhau:

```
   API ứng dụng      01/2026 ─────────────────────────► 05/08/2026
   Google Billing    01/2026 ─────────────────────────► 04/08/2026   (khác nhau theo dự án)
   Google Monitoring     22/01/2026 ─────────────────► 06/08/2026   (trần lưu trữ 196 ngày)
```

Riêng Monitoring, phạm vi còn **khác nhau theo từng phép đo** — không phải phép đo nào cũng có đủ từ đầu:

```
   api_request_count            22/01 ─────────────► 06/08     (kịch trần lưu trữ)
   quota / token theo model     24/04 ────────────► 06/08
   độ trễ p95 / p99                  01/05 ───────► 06/08
```

---

# PHẦN A — Dự án TLA Hợp đồng

**Mã dự án Google:** `ai-chatbot-contract`
**Nguồn dữ liệu:** API web của ứng dụng + Google Billing + Google Monitoring
**Đây là dự án duy nhất có đủ cả ba nguồn.**

---

## A1. Ứng dụng ghi thiếu 17% lượt gọi so với Google

> **Nguồn:** `data/tla-hd/token-usage-year.json` → `timeline` (số của ứng dụng)
> `data/raw_google_console/du_lieu_giam_sat/2026-08-06-1m/ai-chatbot-contract.csv` → `api_request_count` (Monitoring)
> `data/billing/… AI-chatbot-contract-hop-dong.csv` (hoá đơn)
> Script đối chiếu: `test/doi_chieu_tla_hd.py` — cột **Chênh** là tự tính, không có sẵn trong file nào.

### Vấn đề

Trong cùng một khoảng thời gian, Google đếm được nhiều lượt gọi hơn ứng dụng.

### Vì sao

⚠️ **Suy luận trên cơ sở chưa có được dữ liệu log ghi lại trên app.** Ứng dụng có một hoặc nhiều đường gọi Gemini **không đi qua chỗ ghi log**. Chưa xác định được đường nào.

Đã loại trừ được giả thuyết "ứng dụng chỉ ghi lượt thành công": trong 342 lượt Google ghi nhận, **toàn bộ đều trả về mã 200**. Nghĩa là phần thiếu không phải lỗi, mà là **lượt gọi thành công bị bỏ sót**.

### Bằng chứng

Đối chiếu tháng, chỉ ở phần hai bên cùng có dữ liệu:

| Tháng | API web | Google Monitoring | Chênh |
|---|---:|---:|---:|
| 2026-07 | 129 | 150 | **−14,0%** |
| 2026-08 | 155 | 192 | **−19,3%** |
| **Tổng** | **284** | **342** | **−17,0%** |

Độ hụt token cũng gần y hệt, tức không phải sai số ngẫu nhiên mà là thiếu hẳn một nhóm lượt gọi:

| Tháng | Token vào (web) | Token vào (Google Billing) | Chênh |
|---|---:|---:|---:|
| 2026-07 | 1.539.425 | 1.799.882 | −14,5% |
| 2026-08 | 2.883.801 | 3.582.370 | −19,5% |

Nguồn thứ ba xác nhận độc lập — Monitoring đo token ra, khớp gần như tuyệt đối với hoá đơn:

```
   Monitoring token ra   gemini-2.5-pro    1.120.936
   Hoá đơn   token ra    gemini-2.5-pro    1.120.936     ← khớp 100%
```

Nghĩa là **Google tự nhất quán**, còn ứng dụng lệch so với cả hai.

### Ảnh hưởng

Mọi con số lượt gọi và token lấy từ API web đều **thấp hơn thực tế khoảng 17%**. Nếu lấy số của ứng dụng để tính chi phí thì báo cáo sẽ thấp hơn hoá đơn thật.

**Đã quyết:** lấy tổng từ Google, lấy phần chia nhỏ (theo phòng, theo người) từ ứng dụng.

---

## A2. Tháng 3 đến tháng 6 có trên ứng dụng nhưng không có trên Google

> **Nguồn:** `data/tla-hd/token-usage-year.json` → `timeline` · `data/billing/… AI-chatbot-contract-hop-dong.csv`
> `data/raw_google_console/du_lieu_giam_sat/2026-08-06-1m/ai-chatbot-contract.csv` → cột `ts_ict`
> Ngày tạo dự án lấy từ `gcloud projects list` và Logs Explorer — **chưa lưu thành file**, cần chạy lại nếu muốn kiểm chứng.

### Vấn đề

Ứng dụng báo cáo lưu lượng từ tháng 3/2026. Google không có bất kỳ bản ghi nào trước tháng 7.

### Vì sao

✅ **Chứng minh được.** Dự án Google `ai-chatbot-contract` **được tạo ngày 20/06/2026 lúc 14:08 (giờ Việt Nam)**, bởi tài khoản Gmail cá nhân `letrunghieu4799@gmail.com`.

Dữ liệu tháng 3–6 trên ứng dụng ⚠️ **suy luận** là giai đoạn chạy thử bằng một dự án Google khác (nhiều khả năng là project cá nhân do AI Studio tự sinh), chưa gắn vào hệ thống thanh toán của công ty.

### Bằng chứng

Ba nguồn độc lập cùng chỉ ra ngày tạo dự án:

1. Nhật ký kiểm toán của Google Cloud
2. Lệnh `gcloud projects list` — cột `createTime`
3. Google Logs Explorer

Đối chiếu số liệu theo tháng:

| Tháng | API web (lượt) | Google (lượt) |
|---|---:|---:|
| 2026-03 | 260 | **0** |
| 2026-04 | 723 | **0** |
| 2026-05 | 58 | **0** |
| 2026-06 | 1.508 | **0** |
| 2026-07 | 129 | 150 |
| 2026-08 | 155 | 192 |

Tiền cũng vậy — ứng dụng tự tính ra 69,25 USD cả năm, Google chỉ thu 15,87 USD:

| Tháng | Web tự tính | Google thu thật |
|---|---:|---:|
| 03 → 06 | $55,44 | **$0,00** |
| 07 | $5,75 | $6,42 |
| 08 | $8,07 | $9,45 |

**91,4% token và 80,1% chi phí mà ứng dụng báo cáo không có đối ứng nào bên Google.**

### Ảnh hưởng

Nếu để nguyên, dashboard sẽ hiển thị một dự án có chi phí gấp **4,4 lần** hoá đơn thật đã được lưu trên Google Console.

**Đã quyết:** bỏ dữ liệu tháng 3 đến tháng 6, chỉ dùng từ cuối tháng 6 trở đi.

---

## A3. Hơn một nửa token không gắn được vào phòng ban nào

> **Nguồn:** `data/tla-hd/token-usage-year.json` → mảng `by_unit` + `by_user`
> `data/tla-hd/users-by-unit.csv` (bảng nhân sự) · `data/tla-hd/by-user-2026.csv` (mã `user_id` từng tài khoản)
> Cùng số liệu `by_unit` còn nằm ở `data/tla-hd/by-unit-2026.csv`, nhưng file đó **không có `by_user`** nên đọc một mình nó sẽ không phát hiện ra kết luận của mục này.
> Cột **Tỉ lệ** là tự tính (chia cho tổng 62.450.515 token), không có sẵn trong file nào.

### Vấn đề

Bảng thống kê theo đơn vị có một dòng tên **"Chưa xác định"** chiếm **53,6%** toàn bộ token.

### Vì sao

✅ **Chứng minh được — và đây không phải dữ liệu vô danh.**

Khối "Chưa xác định" **không phải một đám đông không rõ danh tính**. Nó là đúng **hai tài khoản**: `admin` và `Test1` (trong file token-usage-year.json của thư mục /data/tla-hd/).

Nên đây không phải lỗi kỹ thuật, mà là **một câu hỏi nghiệp vụ chưa ai trả lời**: `admin` là tài khoản kỹ thuật dùng chung, hay là một người cụ thể đang dùng nó để làm việc thật, tại sao các tài khoản test khác lại không được quy vào trong "chưa xác định", nên xử lí như thế nào với các tài khoản đó?

### Bằng chứng

Thống kê theo đơn vị (cả năm):

| Đơn vị | Request | Token | Tỉ lệ |
|---|---:|---:|---:|
| **Chưa xác định** | **1.327** | **33.475.522** | **53,6%** |
| Công ty CPBĐ PN Rạng Đông | 254 | 8.444.108 | 13,5% |
| Phòng BH1 | 506 | 6.471.853 | 10,4% |
| Phòng BH3 | 122 | 3.666.657 | 5,9% |
| Phòng BH2 | 260 | 3.503.493 | 5,6% |
| TTDL&DHS | 170 | 3.450.588 | 5,5% |
| TT C4LED | 81 | 2.033.867 | 3,3% |
| TT&TMĐT | 113 | 1.404.427 | 2,2% |

Ghép với thống kê theo người dùng, cùng kỳ:

```
   admin      1.315 lượt    33.314.955 token
   Test1         12 lượt       160.567 token
   ──────────────────────────────────────────
   Cộng       1.327 lượt    33.475.522 token
   Khối       1.327 lượt    33.475.522 token     ← khớp cả HAI đại lượng request và token
```

Khớp đồng thời **cả số lượt Request lẫn số token**. Trong 28 tài khoản, không có tổ hợp nào khác cho ra kết quả này — nên đây là chứng minh, không phải phỏng đoán.

**Lưu ý về cách tìm ra:** riêng mảng `by_unit` **không đủ** để phát hiện điều này. Đọc một mình nó thì chỉ thấy "53,6% không rõ phòng nào", và dễ kết luận nhầm là dữ liệu vô danh. Phải đặt `by_user` cạnh `by_unit` — cùng một tập dữ liệu gom theo hai chiều khác nhau — mới lộ ra khối đó có tên.

### Nguyên nhân KHÔNG phải "người dùng chưa được phân quyền"

Đây là giả thuyết tự nhiên nhất, và **dữ liệu bác bỏ nó**.

Có 7 tài khoản dùng ứng dụng nhưng không có mặt trong bảng nhân sự (42 người). Nếu thiếu hồ sơ là nguyên nhân, cả 7 phải rơi vào "Chưa xác định". Thực tế chỉ 2:

| Tài khoản | `user_id` | Lượt | Trong bảng nhân sự | Được quy về đơn vị |
|---|---|---:|---|---|
| `admin` | `user-admin` | 1.315 | không | ❌ **Chưa xác định** |
| `Test1` | *(trống)* | 12 | không | ❌ **Chưa xác định** |
| `test4` | *(trống)* | 91 | không | ✅ có |
| `test1` | *(trống)* | 45 | không | ✅ có |
| `test3` | *(trống)* | 29 | không | ✅ có |
| `test2` | *(trống)* | 10 | không | ✅ có |
| `Nghiệp vụ BH1` | *(trống)* | 2 | không | ✅ có |

Năm tài khoản cuối **cũng không có hồ sơ, cũng không có `user_id`**, nhưng vẫn được quy về phòng ban có tên — tổng 177 lượt / 5.503.739 token.

⚠️ **Suy luận:** đơn vị được **đóng dấu lên từng lượt gọi** tại thời điểm gọi, không phải tra ngược từ hồ sơ người dùng. Nên thiếu hồ sơ không tự động dẫn đến "Chưa xác định", cần được xác minh.

Đối chứng: 21 tài khoản còn lại đều có `user_id` dạng UUID thật, đều có hồ sơ nhân sự, và **21/21 đều được quy về đơn vị**.

⚠️ Một chi tiết chưa giải thích được: `test1` (chữ thường, 45 lượt) có đơn vị, còn `Test1` (chữ hoa, 12 lượt) thì không. Hai tài khoản khác nhau đúng **một chữ hoa** — rất giống tài khoản trùng do gõ nhầm, nhưng chưa kiểm chứng được.

### Ảnh hưởng

Câu trả lời cho câu hỏi về `admin` dẫn tới **hai hướng xử lý ngược nhau**:

| Nếu `admin` là… | Thì 53,6% này… |
|---|---|
| Tài khoản kỹ thuật dùng chung | **không phải người dùng thật** — phải loại khỏi mọi thống kê theo người và theo phòng |
| Một người cụ thể đang làm việc thật | quy được về đúng phòng của người đó |

Đây vẫn là **việc rẻ nhất trong toàn bộ danh sách** — một câu hỏi, không cần cào lại, không cần sửa code. Nhưng cần nói rõ: câu trả lời "kỹ thuật" **không đưa dữ liệu về đúng chỗ**, nó **loại** hơn một nửa lưu lượng ra khỏi thống kê người dùng. Con số tổng của dự án không đổi, nhưng bức tranh "ai đang dùng" thì đổi hoàn toàn.

---

## A4. Lệch 2.223 token giữa tổng và các thành phần

> **Nguồn:** `data/tla-hd/token-usage-year.json` → cả 5 mảng `costs.by_model`, `by_unit`, `by_user`, `by_function`, `timeline`
> Script: `test/chan_doan_loi.py` mục 3 — toàn bộ phép lệch là tự tính.

### Vấn đề

Tổng số token mà API khai báo **lớn hơn** tổng của token vào cộng token ra.

```
   Tổng khai báo        62.450.515
   Vào + ra              62.448.292
   ─────────────────────────────────
   Lệch                       2.223
```

### Vì sao

⚠️ **Suy luận: đây là token suy nghĩ (thinking tokens).**

Gemini 2.5 Pro có chế độ suy luận nội bộ, sinh ra token không nằm trong câu trả lời hiển thị. Google tính tiền phần này nhưng ứng dụng không có cột riêng để lưu, nên nó chỉ xuất hiện ở tổng.

### Bằng chứng

Cắt dữ liệu theo **năm chiều độc lập**, phần lệch luôn rơi vào đúng một ô:

| Cắt theo | Số dòng | Dòng lệch | Nằm ở |
|---|---:|---:|---|
| Model | 3 | 1 | `gemini-2.5-pro` |
| Đơn vị | 8 | 1 | `Chưa xác định` |
| Người dùng | 28 | 1 | `admin` |
| Chức năng | 2 | 1 | `chat` (Hỏi đáp AI) |
| Thời gian | 6 | 1 | `2026-07` |

Năm cách cắt khác nhau đều hội tụ về **cùng một khối**. Xác suất trùng hợp ngẫu nhiên gần như bằng không.

Kiểm thêm: lệch chỉ xuất hiện ở model có chế độ suy luận.

```
   gemini-2.5-pro      lệch  +2.223    494 lượt   ≈ 4,50 token/lượt
   gemini-2.5-flash    lệch      +0  2.337 lượt        0 token/lượt
```

`gemini-2.5-flash` không bật chế độ suy luận và lệch đúng bằng 0.

### Ảnh hưởng

Nhỏ về lượng (0,0036% tổng token) nhưng **quan trọng về nguyên tắc**: nó chứng minh ứng dụng đang thiếu một cột dữ liệu mà Google có tính tiền. Khi dùng nhiều model Pro hơn, khoảng lệch này sẽ nở ra.

---

## A5. Hoá đơn Google chỉ có 9 ngày

> **Nguồn:** `data/billing/… AI-chatbot-contract-hop-dong.csv` → cột `Date`
> Số ngày là **đếm giá trị khác nhau** của cột đó, không phải một cột có sẵn.

### Vấn đề

File billing của TLA Hợp đồng chỉ chứa **9 ngày**, từ 02/07/2026 đến 04/08/2026 — trong khi tên file ghi phạm vi 01/01 đến 31/08.

### Vì sao

⚠️ **Suy luận.** Dự án mới tạo 20/06, và chỉ những ngày **có phát sinh chi phí** mới xuất hiện trong báo cáo billing. 9 ngày này là 9 ngày thực sự có dùng.

### Bằng chứng

```
   File:  ...AI-chatbot-contract-hop-dong.csv
   31 dòng   |   cột Date: 2026-07-02 → 2026-08-04   |   9 ngày riêng biệt
```

So với dự án lâu đời nhất trong cùng thư mục:

```
   ...AI-sale_agent.csv        864 dòng   2026-01-01 → 2026-08-04   214 ngày
```

### Ảnh hưởng

Không thể tính xu hướng theo tuần/tháng cho dự án này từ hoá đơn. Mọi biểu đồ theo thời gian của TLA Hợp đồng phải dựa vào ứng dụng, và ứng dụng thì đang thiếu 17% (xem **A1**).

---

## A6. Ứng dụng tự tính tiền và có sự chênh lệch so với hoá đơn

> **Nguồn:** `data/tla-hd/token-usage-year.json` → `costs.by_model[].total_cost_usd` (số ứng dụng tự tính)
> `data/billing/… AI-chatbot-contract-hop-dong.csv` (số Google thu thật)
> Script: `test/doi_chieu_tla_hd.py` mục 4 — cột **Chênh** là tự tính.

### Vấn đề

API web trả về sẵn cột `total_cost_usd` — tức ứng dụng **tự nhân giá rồi tự tính tiền**. Con số này không khớp hoá đơn thật.

### Vì sao

⚠️ **Suy luận, dự đoán hai nguyên nhân cộng lại:**

1. Ứng dụng thiếu 17% lượt gọi (**A1**) → tính ra ít hơn
2. Bảng giá ứng dụng dùng có thể khác giá Google thực thu

### Bằng chứng

| Tháng | Web tự tính | Google thu | Chênh |
|---|---:|---:|---:|
| 2026-07 | $5,7460 | $6,4205 | −10,5% |
| 2026-08 | $8,0661 | $9,4461 | −14,6% |

### Ảnh hưởng

**Không được dùng cột tiền của ứng dụng.** Chi phí phải tính lại từ token thật nhân bảng giá suy từ hoá đơn.

---

# PHẦN B — Dự án Trợ lý ảo Ralli (CTDA)

**Thư mục dữ liệu:** `data/ctda/`
**Nguồn dữ liệu:** chỉ có API web của ứng dụng
**Đây là dự án có nhiều vấn đề nhất, vì không có nguồn nào để đối chiếu.**

> **Ghi chú tên gọi:** thư mục tên `ctda`, dữ liệu bên trong ghi `TLA CTDA`, dashboard hiển thị là *Trợ lý ảo Ralli*. Ba tên cho cùng một thứ — bản thân điều này đã gây nhầm lẫn và nên thống nhất lại.

---

## B1. Không có hoá đơn Google nào để đối chiếu

> **Nguồn:** danh sách file trong `data/billing/` (7 file, không có file nào cho Ralli)
> danh sách thư mục trong `data/raw_google_console/du_lieu_giam_sat/2026-08-06-1m/` (7 dự án, không có `tla-ralli`)
> Ngày tạo `tla-ralli` lấy từ `gcloud projects list` — **chưa lưu thành file**.

### Vấn đề

Toàn bộ 44,7 triệu token và 7.924 lượt gọi của dự án này **không có bất kỳ bản ghi Google nào** xác nhận.

### Vì sao

⚠️ **Suy luận.** Trong danh sách dự án Google có một project tên `tla-ralli`, tạo ngày **27/07/2026**, nhưng **chưa được bật xuất dữ liệu thanh toán**. Nhiều khả năng ứng dụng vẫn đang chạy bằng khoá API cá nhân, chưa gắn vào tài khoản thanh toán của công ty.

### Bằng chứng

Thư mục `data/billing/` có **7 file, không có file nào cho Ralli**:

```
   AI-chatbot-contact-center      AI-chatbot-contract-hop-dong
   AI-sale_agent                  CRM-feedback
   Multi-model-invoice            feedback-dms-tiep-thi
   tool-quiz
```

Thư mục `data/raw_google_console/` cũng chỉ có 7 dự án, cùng danh sách trên.

Ngày tạo `tla-ralli` (27/07/2026) trùng khít với ngày ứng dụng CTDA đổi định dạng ghi log (xem **B2**, định dạng 3 bắt đầu 28/07). ⚠️ Trùng hợp đáng chú ý nhưng chưa đủ để kết luận nhân quả.

### Ảnh hưởng

**Đây là vấn đề nghiêm trọng nhất của dự án này.** Mọi con số của Ralli đều là *ứng dụng tự khai*, không ai kiểm chứng được. Nếu ứng dụng ghi thiếu như TLA Hợp đồng đang thiếu 17%, sẽ **không có cách nào phát hiện**.

Trên dashboard, dự án này phải được đánh dấu **độ tin cậy thấp**.

---

## B2. Ba định dạng bản ghi khác nhau trong cùng một bảng

> **Nguồn:** `data/ctda/db-token_usage-raw.json` — đếm số khoá của từng bản ghi
> Script: `test/chan_doan_loi.py` mục 2.

### Vấn đề

Bảng `token_usage` chứa ba loại bản ghi với số trường khác nhau: 8, 14 và 16 trường.

### Vì sao

✅ **Chứng minh được.** Ứng dụng được nâng cấp hai lần, mỗi lần thêm trường mới. MongoDB không bắt buộc mọi bản ghi giống nhau, nên **bản ghi cũ không hề biết là có trường mới tồn tại** — chúng đơn giản là thiếu hẳn trường đó, không phải để trống.

Đây là điểm khác biệt căn bản giữa MongoDB và SQL: trong SQL, thêm cột mới thì mọi dòng cũ tự động có cột đó với giá trị `NULL`.

### Bằng chứng

| Định dạng | Số dòng | Khoảng thời gian | Số trường | Trường thêm mới |
|---|---:|---|---:|---|
| 1 | **6.871** (86,7%) | 14/03 → 15/07 | 8 | *(nền chung)* |
| 2 | 542 (6,8%) | 15/07 → 27/07 | 14 | `cached_tokens`, `pricing_mode`, `event_type`, 3 trường modality |
| 3 | 511 (6,5%) | 28/07 → 05/08 | 16 | thêm `actor_type`, `username` |

Chỉ **8 trường** có mặt ở cả ba định dạng:

```
   _id · timestamp · user_id · function · model
   prompt_tokens · completion_tokens · total_tokens
```

### Ảnh hưởng

Bất kỳ phép tính nào dùng trường ngoài 8 trường chung đều **chỉ đúng cho 13,3% dữ liệu**.

Ví dụ cụ thể: lấy trung bình `cached_tokens` trên cả bảng sẽ **sai 7,5 lần**, vì mẫu số tính cả 6.871 dòng vốn không có trường đó.

Khi chuyển sang PostgreSQL, những ô này **bắt buộc phải là `NULL`, không được điền `0`** — vì `0` nghĩa là "đo được và bằng không", còn `NULL` nghĩa là "không đo".

---

## B3. 88% bản ghi không biết ai là người dùng

> **Nguồn:** `data/ctda/db-token_usage-raw.json` → trường `user_id`
> `data/ctda/users.csv` → cột `id` và `username` (bảng tài khoản để tra ngược)
> Bảng phân loại 4 nhóm là **tự dựng**, không có sẵn ở đâu.

### Vấn đề

Trường `user_id` mang giá trị chuỗi `'system'` ở phần lớn bản ghi.

### Vì sao

⚠️ **Suy luận — và có hai cách hiểu trái ngược nhau, chưa ai trả lời được cách nào đúng:**

- **Cách hiểu 1:** đây là tác vụ nền chạy tự động → 91,4% token này **không phải người dùng thật**
- **Cách hiểu 2:** đây là giai đoạn ứng dụng chưa gắn theo dõi người dùng → là người dùng thật nhưng đã mất dấu

Hai cách hiểu dẫn tới hai kết luận hoàn toàn khác nhau về việc dự án này có bao nhiêu người dùng thật.

### Bằng chứng

Phân loại toàn bộ 7.924 bản ghi theo khả năng tra ngược ra tài khoản:

| Loại | Lượt | Tỉ lệ | Token | Tỉ lệ |
|---|---:|---:|---:|---:|
| `user_id = 'system'` | **6.986** | **88,2%** | **40.849.145** | **91,4%** |
| Tra ra được `users.id` | 215 | 2,7% | 1.129.696 | 2,5% |
| Tra ra được `users.username` | 49 | 0,6% | 139.100 | 0,3% |
| Có giá trị nhưng **tra không ra ai** | 674 | 8,5% | 2.574.560 | 5,8% |

Nhóm 674 dòng "tra không ra" tách nhỏ thành 4 nguyên nhân khác nhau:

```
   69b4e9d78bc3012c1cd8cb72     162 lượt    877.077 token   ← mã người đã bị xoá khỏi bảng users
   (null)                       134 lượt    786.851 token   ← có trường, để trống
   admin                        318 lượt    711.327 token   ← lưu tên, không phải mã
   guest                         60 lượt    199.305 token   ← tài khoản khách
```

Chú ý dòng thứ ba: cùng một trường `user_id` nhưng chỗ thì lưu **mã**, chỗ lưu **tên đăng nhập**. Đây là lý do không thể nối bảng bằng một phép so sánh duy nhất.

Bằng chứng phụ trợ — chỉ **511/7.924 bản ghi (6,5%)** có trường `username`, đúng bằng số bản ghi thuộc định dạng 3 (xem **B2**).

### Ảnh hưởng

Kết luận quan trọng: **chỉ 264/7.924 dòng (3,3%) tra ngược ra được một tài khoản có thật.**

Nghĩa là dashboard **không thể trả lời câu hỏi "ai dùng nhiều nhất"** cho dự án này. Mọi thống kê theo người dùng của Ralli đều dựa trên 3,3% dữ liệu.

---

## B4. 97% token không gắn được vào đơn vị nào

> **Nguồn:** `data/ctda/by-unit-2026.csv` → dòng `Không xác định`
> Tỉ lệ % là tự tính (chia cho tổng 44.692.501 token / 7.924 lượt).

### Vấn đề

Thống kê theo đơn vị có dòng **"Không xác định"** chiếm gần như toàn bộ.

### Vì sao

✅ **Chứng minh được** — hệ quả trực tiếp của **B3**. Không biết người thì không biết phòng.

### Bằng chứng

```
   Không xác định     7.660 lượt   43.423.705 token   ← 96,7% lượt / 97,2% token
   TT3                  118 lượt      569.559 token
   … các đơn vị khác
```

### Ảnh hưởng

Biểu đồ phân bổ theo phòng ban của Ralli **không dùng được**. Nếu vẽ ra, người xem sẽ thấy một cột chiếm 97% và các cột còn lại gần như vô hình.

---

## B5. Lệch 162 token — chính xác 81 dòng, mỗi dòng đúng 2 token

> **Nguồn:** `data/ctda/db-token_usage-raw.json` — so `total_tokens` với `prompt_tokens + completion_tokens` từng dòng
> Script: `test/chan_doan_loi.py` mục 1
> Kiểm chứng thêm trên giao diện web ngày 07/08/2026 (`test/ui-snapshot-2026-08-07.json`).

### Vấn đề

Tổng token khai báo lệch 162 so với tổng các thành phần.

### Vì sao

⚠️ **Suy luận: lỗi ở phiên bản ghi log cũ.** Toàn bộ dòng lệch nằm trong định dạng 8 trường, và **ngừng hẳn từ 23/06** — trùng với giai đoạn ứng dụng được nâng cấp.

Con số **đúng 2 token mỗi dòng, không xê dịch** loại trừ khả năng làm tròn. Đây là một hằng số bị bỏ sót, không phải sai số tính toán.

### Bằng chứng

```
   Số dòng lệch        81 / 7.924
   Tổng token thiếu    162
   Phân bố độ lệch     {2 token: 81 dòng}      ← chỉ một giá trị duy nhất
```

Đặc điểm nhóm lệch — rất tập trung:

| Chiều | Kết quả |
|---|---|
| Model | `gemini-2.5-flash-lite` = 81/81 dòng |
| Chức năng | `gemini_structured_call` 68 · `gemini_chat_json_messages` 13 |
| Định dạng bản ghi | 81/81 thiếu trường `cached_tokens` — tức 100% thuộc định dạng cũ |
| Thời gian | 29/03 → 23/06, sau đó **không tái diễn** |

Tỉ lệ lệch theo từng loại chức năng — lộ ra rằng chỉ hai đường code bị dính:

```
   gemini_structured_call        68 / 3.388    ( 2,0%)
   gemini_chat_json_messages     13 /   304    ( 4,3%)
   gemini_generate_text           0 / 4.172    ( 0,0%)   ← đường code này không dính
   assistant_extract_image_text   0 /    39    ( 0,0%)
```

Kiểm chứng thêm: mở giao diện web ngày 07/08/2026, con số vẫn đúng **162** — nghĩa là lỗi nằm ở dữ liệu đã lưu, không phải ở khâu cào.

### Ảnh hưởng

Rất nhỏ về lượng (0,0004%). Giá trị của phát hiện này là ở chỗ khác: nó **chứng minh dữ liệu cũ có lỗi hệ thống**, và cho thấy phương pháp kiểm tra đủ nhạy để bắt được sai lệch cỡ 2 token trong 44 triệu.

---

## B6. API của ứng dụng bỏ qua tham số truy vấn

> **Nguồn:** `data/ctda/logs-recent-365.json` → hai trường `requested_limit` và `fetched_count` nằm ngay trong file
> `data/ctda/db-collections.json` → dòng `assistant_query_logs` (để biết tổng thật là 1.493).

### Vấn đề

Gửi tham số giới hạn hoặc lọc theo ngày, API **không đọc** mà trả về theo mặc định của nó.

### Vì sao

✅ **Chứng minh được** — chính file dữ liệu trả về tự tố cáo.

### Bằng chứng

File `logs-recent-365.json` chứa nguyên văn:

```
   requested_limit  =  100      ← đã xin 100 bản ghi
   fetched_count    = 1000      ← trả về 1000
```

Tham số `date_from` cũng bị bỏ qua tương tự ở cả hai ứng dụng (CTDA và TLA Hợp đồng).

Đối chiếu với mục lục database: bảng `assistant_query_logs` có **1.493 bản ghi**, ta chỉ lấy được **1.000** — bị chặn ở mốc cứng, thiếu 493.

### Ảnh hưởng

**Không thể cào dữ liệu theo khoảng thời gian.** Mỗi lần cào là lấy nguyên khối mới nhất.

Hệ quả nghiêm trọng hơn: **quá khứ không lấy lại được**. Đã lỡ bỏ sót một ngày thì ngày đó mất vĩnh viễn, vì không có cách nào yêu cầu API trả về dữ liệu cũ.

---

## B7. Thiếu 1 người dùng so với mục lục database

> **Nguồn:** `data/ctda/db-collections.json` → dòng `users`, trường `count`
> `data/ctda/users-list.json` → đếm số phần tử.

### Vấn đề

Mục lục ghi bảng `users` có 891 bản ghi. File cào về chỉ có 890.

### Vì sao

⚠️ **Chưa xác định.** Có thể là tài khoản ẩn, tài khoản hệ thống bị API lọc bỏ, hoặc API cắt mất một dòng.

### Bằng chứng

File `db-collections.json` — đây là mục lục do chính database khai báo:

```
   { "name": "users", "count": 891, "size": 475918 }
```

File `users-list.json` cào về: **890 bản ghi**.

Đối chứng: cùng file mục lục ghi `token_usage` = **7.924**, và file cào về đúng **7.924** — khớp tuyệt đối. Nên chênh lệch ở bảng `users` không phải lỗi cào chung chung.

### Ảnh hưởng

Nhỏ, nhưng cần biết: nếu tài khoản thiếu đó chính là chủ của một phần lưu lượng thì sẽ rơi vào nhóm "tra không ra" ở **B3**.

---

---

## B8. Chưa có dữ liệu request, lỗi và độ trễ

> **Nguồn:** `data/raw_google_console/du_lieu_giam_sat/2026-08-06-1m/` — không có thư mục nào cho Ralli
> `test/seed-days-that.js` (sinh bởi `test/sinh_du_lieu_dashboard.py`) → trường `eKnown`
> Con số 40.547 / 48.471 là tự tính khi dựng dữ liệu dashboard.

### Vấn đề

Dự án này **không có** số lượt gọi theo mã trạng thái, không có tỉ lệ lỗi, không có độ trễ.

### Vì sao

✅ **Chứng minh được** — hệ quả trực tiếp của **B1**. Các chỉ số này chỉ Google Monitoring mới đo được, mà dự án chưa gắn Google.

### Bằng chứng

Trong 48.471 lượt gọi toàn hệ thống, chỉ **40.547 lượt (83,7%)** biết được mã trạng thái. Phần thiếu là **7.924 lượt — đúng bằng toàn bộ Ralli**.

### Ảnh hưởng

Trên tab Hiệu năng, Ralli hiện dấu **`—`** ở cả bốn cột và **bị loại khỏi biểu đồ tỉ lệ lỗi**.

Lý do phải làm vậy: trước đây dashboard hiển thị Ralli "100% thành công / 0% lỗi". Đó là một khẳng định **không có gì chứng minh** — vừa nói không đo được mã lỗi, vừa khẳng định không có lỗi nào, là tự mâu thuẫn. Hiện tại 7.924 lượt của Ralli cũng **không nằm trong mẫu số** khi tính tỉ lệ thành công chung.

---

# PHẦN C — Sáu dự án còn lại

**Danh sách:** Sale Agent · Chatbot Contact Center · Phân Loại Dữ Liệu CRM · Phân Loại Phản Hồi Tiếp Thị · Multi modal AI Invoice · Tools Quizzer
**Nguồn dữ liệu:** chỉ có Google Billing và Google Monitoring

---

## C1. Chỉ có tiền, không có người dùng

> **Nguồn:** cấu trúc thư mục `data/` — sáu dự án này chỉ xuất hiện trong `data/billing/` và `data/raw_google_console/du_lieu_giam_sat/2026-08-06-1m/`, không có thư mục dữ liệu ứng dụng nào.

### Vấn đề

Sáu dự án này không có API ứng dụng nào để lấy thông tin người dùng, phòng ban, hay nội dung sử dụng.

### Vì sao

✅ **Chứng minh được.** Đây là các dịch vụ chạy nền hoặc công cụ nội bộ, không có giao diện quản trị riêng có thống kê.

### Bằng chứng

Trong `data/`, sáu dự án này chỉ xuất hiện ở `billing/` và `raw_google_console/`. Không có thư mục dữ liệu ứng dụng nào.

### Ảnh hưởng

Đã thống nhất: **mỗi dự án tính là một agent duy nhất**, không phân cấp người dùng bên trong. Cây tổ chức chỉ áp dụng cho TLA Hợp đồng và Ralli.

---

## C2. Phạm vi hoá đơn giữa các dự án lệch nhau rất xa

> **Nguồn:** bảy file trong `data/billing/` → cột `Date` của từng file
> Số dòng và số ngày đều là **tự đếm**.

### Vấn đề

Có dự án có 214 ngày dữ liệu, có dự án chỉ có 4 ngày.

### Vì sao

⚠️ **Suy luận, hai nguyên nhân:** dự án được tạo ở các thời điểm khác nhau, và chỉ ngày nào có phát sinh chi phí mới xuất hiện trong hoá đơn.

### Bằng chứng

| Dự án | Số dòng | Khoảng thời gian | Số ngày |
|---|---:|---|---:|
| AI-sale_agent | 864 | 01/01 → 04/08 | **214** |
| AI-chatbot-contact-center | 870 | 13/01 → 04/08 | 189 |
| Multi-model-invoice | 383 | 22/01 → **25/07** | 88 |
| CRM-feedback | 73 | 06/07 → 04/08 | 29 |
| feedback-dms-tiep-thi | 30 | 06/07 → **31/07** | 11 |
| AI-chatbot-contract | 31 | 02/07 → 04/08 | **9** |
| tool-quiz | 8 | 24/06 → **30/06** | **4** |

### Ảnh hưởng

**Không so sánh trực tiếp tổng cả năm giữa các dự án được.** Mọi so sánh phải quy về cùng một kỳ.

---

## C3. Hai dự án có dấu hiệu đã ngừng hoạt động

> **Nguồn:** `data/billing/… tool-quiz.csv` và `data/billing/… Multi-model-invoice.csv` → giá trị lớn nhất của cột `Date`
> Đối chứng: các file còn lại đều có dữ liệu đến 04/08/2026.

### Vấn đề

`tool-quiz` và `Multi-model-invoice` không phát sinh chi phí nữa.

### Vì sao

⚠️ **Suy luận.** Có thể đã dừng thật, hoặc đã chuyển sang dự án Google khác, hoặc chỉ tạm ngưng.

### Bằng chứng

```
   tool-quiz             ngày cuối có chi phí   30/06/2026    ← im lặng hơn 5 tuần
   Multi-model-invoice   ngày cuối có chi phí   25/07/2026    ← im lặng gần 2 tuần
```

Các dự án còn đang hoạt động đều có dữ liệu đến 04/08/2026.

`tool-quiz` chỉ có **8 dòng / 4 ngày** trong toàn bộ lịch sử — quá ít để gọi là một dự án đang vận hành.

### Ảnh hưởng

Cần xác nhận trước khi lên báo cáo. Nếu đã dừng thì hiển thị chúng cạnh các dự án đang chạy sẽ gây hiểu nhầm là "chi phí giảm mạnh", trong khi thực tế là "không còn dùng".

**Câu hỏi cần trả lời:** có bỏ `tool-quiz` khỏi danh sách agent chính thức không?

---

# PHẦN D — Vấn đề xuyên suốt nhiều dự án

---

## D1. Có 11 dự án Google, chỉ 7 dự án có dữ liệu

> **Nguồn:** `gcloud projects list` → cột `createTime` — **chưa lưu thành file**, cần chạy lại nếu muốn kiểm chứng
> Đối chiếu với số thư mục có thật trong `data/billing/` và `data/raw_google_console/du_lieu_giam_sat/2026-08-06-1m/` (đều là 7).

### Vấn đề

Danh sách dự án trên Google Cloud nhiều hơn số dự án đang được theo dõi.

### Vì sao

⚠️ **Suy luận.** Các dự án thừa là dự án cá nhân hoặc dự án thử nghiệm, chưa gắn vào tài khoản thanh toán công ty.

### Bằng chứng

Hai dự án chưa được tính đến:

| Dự án | Ngày tạo | Ghi chú |
|---|---|---|
| `tla-ralli` | 27/07/2026 | Nhiều khả năng là dự án của Ralli, chưa bật xuất billing |
| `gen-lang-client-0247490857` | 21/07/2026 | Tên *"Default Gemini Project"* — đây là tên Google AI Studio **tự sinh** khi tạo khoá API nhanh |

**Toàn bộ dự án đều do cùng một tài khoản Gmail cá nhân tạo ra**, không phải tài khoản tổ chức.

### Ảnh hưởng

Có khả năng đang tồn tại lưu lượng **không nằm trong bất kỳ báo cáo nào**. Đặc biệt `gen-lang-client-*` — đây đúng là kiểu dự án sinh ra khi ai đó cần khoá API gấp để thử.

**Câu hỏi cần trả lời:** hai dự án này có đang phục vụ nghiệp vụ thật không?

---

## D2. Bản cào giám sát đã kịch trần lưu trữ — dữ liệu cũ hơn đã mất vĩnh viễn

> **Nguồn:** bảy file `data/raw_google_console/du_lieu_giam_sat/2026-08-06-1m/*.csv` → cột `ts_ict` và `metric_alias`
> Mốc 196 ngày là **tự tính**: lấy ngày cào 06/08/2026 trừ ngày sớm nhất 22/01/2026.

### Vấn đề

Tên thư mục là `2026-08-06-1m` khiến người đọc tưởng chỉ cào 1 tháng. **Không phải.** Bản cào thực tế trải **196 ngày**, từ 22/01 đến 06/08/2026 — đúng bằng toàn bộ những gì Google còn giữ.

Vấn đề thật nằm ở chỗ khác: **đây là trần, không phải lựa chọn.** Dữ liệu trước 22/01/2026 đã bị Google xoá trước cả khi ta cào.

### Vì sao

✅ **Chứng minh được.** Google Cloud Monitoring chỉ lưu khoảng **196 ngày**. Bản cào đã lấy hết phần còn lấy được.

### Bằng chứng

Đây là bằng chứng mạnh nhất — **hai dự án khác nhau bắt đầu đúng cùng một ngày**:

| Dự án | Ngày sớm nhất | Cách ngày cào 06/08 |
|---|---|---:|
| `pro-tuner-454203-v3` | 22/01/2026 | **196 ngày** |
| `tranquil-post-471401-c1` | 22/01/2026 | **196 ngày** |

```
   06/08/2026  −  196 ngày  =  22/01/2026     ← khớp chính xác
```

Hai dự án độc lập không thể ngẫu nhiên cùng phát sinh lưu lượng đầu tiên vào đúng một ngày. Đó là **sàn lưu trữ**, không phải ngày bắt đầu thật.

**Đối chứng quan trọng:** các dự án còn lại có phạm vi ngắn hơn, và đó là ngày bắt đầu **thật** của chúng, không phải giới hạn cào:

| Dự án | Phạm vi | Cách 06/08 | Ý nghĩa |
|---|---|---:|---|
| `multimodal-invoice` | 26/01 → 25/07 | 192 ngày | gần sàn, đã ngừng cuối 07 |
| `tools-quizz` | 17/06 → 01/07 | 50 ngày | dự án mới, dùng rất ít |
| `ai-chatbot-contract` | 20/06 → 04/08 | 47 ngày | **trùng ngày tạo dự án** (xem **A2**) |
| `crm-500509` | 07/07 → 06/08 | 30 ngày | dự án mới |
| `feedback-dms-tiep-thi` | 07/07 → 06/08 | 30 ngày | dự án mới |

Đặc biệt `ai-chatbot-contract` bắt đầu đúng **20/06/2026** — trùng khít ngày tạo dự án đã xác minh ở **A2** bằng ba nguồn khác. Đây là bằng chứng độc lập thứ tư cho cùng một kết luận.

Phạm vi cũng khác nhau **theo từng phép đo**:

| Phép đo | Phạm vi | Số ngày |
|---|---|---:|
| `api_request_count` | 22/01 → 06/08 | 196 |
| Token và hạn mức theo model | 24/04 → 06/08 | 105 |
| Độ trễ p95 / p99 | 01/05 → 06/08 | 98 |

### Ảnh hưởng

Ba điều, và không điều nào giống cái tôi viết ở bản đầu:

**1. Bản chụp ngày 06/08 là bản duy nhất, không tái tạo được.** Cào lại hôm nay (08/08) chỉ lấy được từ **24/01** — đã mất 2 ngày đầu so với bản đang có. Mỗi ngày trôi qua mất thêm một ngày.

**2. Không có cách nào lấy dữ liệu giám sát trước 22/01/2026.** Nếu báo cáo cần cả quý 1, phần trước 22/01 phải chấp nhận là trống vĩnh viễn.

**3. Độ trễ chỉ có từ 01/05.** Mọi biểu đồ p95/p99 trước mốc này sẽ trống — và đó là giới hạn của nguồn, không phải lỗi.

> **Sửa lỗi:** bản đầu của tài liệu này ghi Monitoring "chỉ có 1 tháng, cần cào lại gấp với cửa sổ rộng hơn". Sai — chỉ nhìn tên thư mục `1m` mà không mở file ra kiểm. Bản cào đã đầy đủ tối đa. Việc gấp không phải cào rộng hơn, mà là **giữ cho kỹ bản đã có** và **chụp đều đặn từ nay**, vì phần đuôi đang rụng dần mỗi ngày.

---

## D3. Phép đo số request không có nhãn model

> **Nguồn:** bảy file `data/raw_google_console/du_lieu_giam_sat/2026-08-06-1m/*.csv` → cột `model` ở các dòng có `metric_alias = api_request_count` (rỗng ở mọi dòng)
> Cách xử lý thay thế nằm trong `test/sinh_du_lieu_dashboard.py`.

### Vấn đề

Không thể biết một request cụ thể gọi model nào.

### Vì sao

✅ **Chứng minh được.** Phép đo `serviceruntime.googleapis.com/api/request_count` **không có nhãn `model`** — nhãn này chỉ tồn tại ở nhóm phép đo token của `generativelanguage`.

### Bằng chứng

Kiểm tra toàn bộ dữ liệu giám sát: ở mọi dòng có `metric_alias = api_request_count`, cột `model` **rỗng**.

Đối chứng cho thấy đây là đặc điểm của nhóm phép đo chứ không phải lỗi ghi nhận: các phép đo token của `generativelanguage` **có** nhãn model đầy đủ, trong cùng bộ dữ liệu, cùng khoảng thời gian.

### Ảnh hưởng

Không có cách nào biết một request cụ thể gọi model nào. Muốn có số request theo model thì **bắt buộc phải ước lượng** — con số đó sẽ đúng ở mức tổng nhưng không phải số đo ở mức chia nhỏ.

Nếu một model có tỉ lệ token trên mỗi request lệch hẳn các model khác — ví dụ một model chuyên xử lý câu dài — thì mọi cách ước lượng dựa trên token đều sai lệch.

---

## D6. File mô tả cấu trúc chỉ lấy mẫu 100 dòng nên mô tả sai phần lớn dữ liệu

> **Nguồn:** `data/ctda/db-token_usage-schema.json` và `db-conversations-schema.json` → trường `sample_count` nằm ngay trong file
> `data/ctda/db-token_usage-raw.json` — để đếm số trường thật của từng bản ghi.

### Vấn đề

Hai file schema khai báo cấu trúc bảng, nhưng cấu trúc đó chỉ đúng cho một phần nhỏ dữ liệu.

### Vì sao

✅ **Chứng minh được.** MongoDB không có schema bắt buộc, nên công cụ phải **quét thử 100 bản ghi rồi suy ngược ra**. Trường nào chỉ có ở bản ghi cũ hoặc hiếm thì không xuất hiện.

Và 100 bản ghi được quét là **100 bản ghi mới nhất** — tức toàn bộ thuộc định dạng mới.

### Bằng chứng

`db-token_usage-schema.json` khai **16 trường**. Dữ liệu thật:

```
   6.871 dòng  →   8 trường   (86,7%)     ← schema mô tả SAI cho nhóm này
     542 dòng  →  14 trường   ( 6,8%)
     511 dòng  →  16 trường   ( 6,5%)     ← schema chỉ đúng cho nhóm này
```

Cả hai file schema đều ghi `"sample_count": 100`.

### Ảnh hưởng

⚠️ **Suy luận:** `db-conversations-schema.json` nhiều khả năng cũng vậy — 9 trường nó liệt kê là 9 trường của 100 hội thoại gần nhất, còn 1.464 bản ghi thật có thể có định dạng cũ khác hẳn. Chưa cào thì chưa biết, nhưng đã có tiền lệ nên không nên tin.

**Không được dùng file schema để thiết kế bảng PostgreSQL.** Phải quét toàn bộ dữ liệu thật.

---

## D7. Kiểu dữ liệu tiền không nhất quán giữa hai ứng dụng

> **Nguồn:** `data/tla-hd/token-usage-year.json` → `by_user[].total_cost_usd` (kiểu chuỗi)
> `data/ctda/token-usage-year.json` → `top_users[].total_cost_usd` (kiểu số thực)
> Hai file cùng tên, cùng vai trò, khác kiểu dữ liệu.

### Vấn đề

Cùng một loại giá trị, hai ứng dụng trả về hai kiểu khác nhau.

### Vì sao

⚠️ **Suy luận.** Hai đội phát triển khác nhau, không có quy ước chung.

### Bằng chứng

```
   TLA Hợp đồng    total_cost_usd = "27.3504"     ← chuỗi
   Ralli (CTDA)    total_cost_usd =  5.4231       ← số thực
```

Điều này đã gây ra lỗi thật lúc kiểm tra: `TypeError: unsupported operand type(s) for -: 'str' and 'str'`.

### Ảnh hưởng

Mọi script đọc dữ liệu phải ép kiểu trước khi tính. Nếu quên, hoặc là chương trình dừng, hoặc tệ hơn — phép cộng chuỗi cho ra kết quả trông giống số nhưng hoàn toàn sai.

---

# PHẦN E — Tổng hợp

## Xếp theo mức độ nghiêm trọng

| # | Vấn đề | Dự án | Mức độ | Sửa được không |
|---|---|---|---|---|
| **B1** | Không có hoá đơn Google để đối chiếu | Ralli | 🔴 Nặng | Cần bật billing |
| **B3** | 88% không biết người dùng | Ralli | 🔴 Nặng | ❌ Không |
| **A1** | Ứng dụng ghi thiếu 17% lượt gọi | TLA HĐ | 🔴 Nặng | Dùng số Google |
| **A2** | Tháng 3–6 không có đối ứng Google | TLA HĐ | 🔴 Nặng | ✅ Đã quyết bỏ |
| **B2** | Ba định dạng bản ghi | Ralli | 🟠 Vừa | Xử lý khi nạp |
| **D2** | Giám sát kịch trần 196 ngày, đuôi rụng dần | Tất cả | 🟠 Vừa | ⏰ Giữ bản đã có |
| **A3** | 53,6% chưa gắn đơn vị — thực ra là `admin` + `Test1` | TLA HĐ | 🟠 Vừa | ✅ Hỏi là xong |
| **B4** | 97% chưa gắn đơn vị | Ralli | 🟠 Vừa | ❌ Không |
| **D1** | 11 dự án Google, 7 có dữ liệu | Tất cả | 🟠 Vừa | Cần xác nhận |
| **B8** | Không có dữ liệu lỗi và độ trễ | Ralli | 🟠 Vừa | Cần bật billing |
| **A6** | Ứng dụng tự tính tiền sai | TLA HĐ | 🟠 Vừa | ✅ Tính lại |
| **A5** | Hoá đơn chỉ có 9 ngày, không dựng được xu hướng | TLA HĐ | 🟠 Vừa | ❌ Không |
| **C3** | Hai dự án có vẻ đã dừng | 6 agent | 🟡 Nhẹ | Cần xác nhận |
| **D6** | Schema mô tả sai 87% dữ liệu | Ralli | 🟡 Nhẹ | Quét lại toàn bộ |
| **C2** | Phạm vi hoá đơn lệch nhau | 6 agent | 🟡 Nhẹ | Quy về cùng kỳ |
| **B6** | API bỏ qua tham số | Cả hai app | 🟡 Nhẹ | ❌ Không |
| **D3** | Request không có nhãn model | Tất cả | 🟡 Nhẹ | Ước lượng |
| **D7** | Kiểu dữ liệu tiền không nhất quán | Cả hai app | 🟡 Nhẹ | Ép kiểu |
| **A4** | Lệch 2.223 token | TLA HĐ | 🟡 Nhẹ | Thêm cột |
| **B5** | Lệch 162 token | Ralli | 🟡 Nhẹ | Đã ngừng |
| **B7** | Thiếu 1 người dùng | Ralli | 🟡 Nhẹ | Cần kiểm |
| **C1** | Chỉ có tiền, không có người | 6 agent | ⚪ Đã chấp nhận | Theo thiết kế |

---

## Bốn loại "không quy được về ai"

Đây là chỗ hay bị gộp nhầm. Có **bốn loại khác hẳn nhau**, mỗi loại sửa bằng một cách khác:

| Loại | Dự án | Số liệu | Bản chất | Sửa được |
|---|---|---:|---|---|
| **1** | TLA HĐ | 1.327 lượt / **33,5 tr token (53,6%)** | Biết chính xác là ai — `admin` + `Test1` | ✅ Hỏi một câu |
| **2** | Ralli | 6.986 lượt / **40,8 tr token (91,4%)** | App không ghi người | ❌ Mất vĩnh viễn |
| **3** | Ralli | 674 lượt / 2,6 tr token (5,8%) | Có mã nhưng tra không ra | ◐ Một phần |
| **4** | TLA HĐ | 58 lượt / 1,1 tr token | Không có bản ghi nào | ❌ Không thể |

Chỉ **loại 4** mới thực sự là "không quy được" theo nghĩa đen. Ba loại trên là *chưa quy*, loại 4 là *không thể quy*.

Riêng loại 1 cần nói thêm cho đúng: **"chưa quy" không có nghĩa là sẽ quy được.** Đã biết chính xác đó là `admin` và `Test1`. Nếu `admin` hoá ra là tài khoản kỹ thuật, thì câu trả lời đúng là **loại 53,6% này ra khỏi thống kê người dùng**, chứ không phải phân về phòng nào cả.

> **Lưu ý về phạm vi:** con số 58 lượt lấy từ cửa sổ đối chiếu từ tháng 7 trở đi, còn 53,6% và 91,4% tính cả năm từ tháng 3. **Hai nhóm số này không cộng chung được.** Sau khi cắt về kỳ đã thống nhất, tỉ lệ sẽ thay đổi — nhiều khả năng tỉ lệ `system` của Ralli sẽ giảm mạnh vì bản ghi định dạng cũ tập trung ở giai đoạn đầu.

---

## Những gì đã được kiểm chứng là ĐÚNG

Để cân bằng, đây là những phần đã đối chiếu và khớp hoàn toàn:

| Phép kiểm | Kết quả |
|---|---|
| Dữ liệu thô Ralli ↔ thống kê ứng dụng cộng sẵn | **Khớp tuyệt đối** (7.924 lượt · 44.692.501 token) |
| Hoá đơn gộp ↔ 7 file thành phần | **Khớp tuyệt đối** ($270,9517 · 670.884.864 token) |
| Giao diện web ↔ dữ liệu đã lấy về | **84 điểm khớp, 0 lỗi** |
| Monitoring token ra ↔ hoá đơn token ra | **Khớp tuyệt đối** (1.120.936 và 1.147) |
| Mục lục database ↔ bảng `token_usage` | **Khớp tuyệt đối** (7.924) |

Riêng **B4** đáng nói thêm. Con số 97% có thể tính ra bằng **hai đường độc lập**: đọc thẳng bảng thống kê của ứng dụng, hoặc đi từ 7.924 bản ghi thô qua `users-list.json` rồi `units.json`. Hai đường cho cùng một kết quả:

```
   7.660 lượt  /  43.423.705 token        ← khớp tuyệt đối
```

Nghĩa là con số này **có thật trong dữ liệu thô**, không phải hệ quả của cách gom nhóm.

### Giới hạn: TLA Hợp đồng không có dữ liệu từng lượt gọi

Ứng dụng TLA Hợp đồng **không cung cấp endpoint nào trả về từng lượt gọi**. Mọi thứ lấy được đều là bảng ứng dụng đã tự cộng sẵn.

Đây tự nó là một khuyết tật của nguồn, và nó quyết định mức độ chắc chắn của các mục trong Phần A:

| Mục | Đối chiếu được với nguồn độc lập không |
|---|---|
| **A1**, **A2**, **A5**, **A6** | ✅ có — so với **hoá đơn và giám sát của Google** |
| **A3**, **A4** | ❌ **không** — chỉ so các bảng thống kê của ứng dụng với nhau |

A3 và A4 vẫn là phát hiện có giá trị, nhưng phải nói rõ giới hạn: chúng chứng minh **ứng dụng tự mâu thuẫn với chính nó**, chứ chưa chứng minh được điều gì về dữ liệu bên dưới.

---

## Câu hỏi cần người khác trả lời

**Chặn tiến độ — chưa có câu trả lời thì chưa làm tiếp được:**

1. Tài khoản `admin` của TLA Hợp đồng là tài khoản kỹ thuật dùng chung hay một người cụ thể? *(quyết định 53,6% dữ liệu — xem **A3**)*
2. Tỷ giá VNĐ lấy theo nguồn nào, cập nhật khi nào?
3. Ngân sách tháng của Ralli là bao nhiêu?
4. Ai duyệt bảng giá model?
5. Có bỏ `tool-quiz` khỏi danh sách agent chính thức không?
6. Danh sách 8 agent chính thức và ánh xạ sang dự án Google?

**Không chặn nhưng cần biết:**

7. `user_id = 'system'` của Ralli là tác vụ nền hay giai đoạn chưa gắn theo dõi? *(quyết định 88% dữ liệu có được tính là lưu lượng người dùng không)*
8. Hai dự án `tla-ralli` và `gen-lang-client-0247490857` có phục vụ nghiệp vụ thật không?
9. `Multi-model-invoice` đã dừng hẳn sau 25/07 chưa?
10. Trường `timestamp` của Ralli là giờ UTC hay giờ Việt Nam?
11. Agent nào đang gọi `gemini-embedding-001`?
12. Trong các giá trị `function` của Ralli, cái nào là người dùng thật, cái nào là tác vụ nền?
13. `test1` và `Test1` (khác nhau đúng một chữ hoa) là hai tài khoản thật hay một tài khoản bị tạo trùng do gõ nhầm? *(xem **A3**)*
14. Năm tài khoản `test1`–`test4` và `Nghiệp vụ BH1` không có hồ sơ nhân sự nhưng vẫn phát sinh lưu lượng thật — có phải tài khoản chạy thử không? Nếu phải thì có loại khỏi thống kê không?

---

## Việc cần làm ngay, xếp theo thứ tự

| Thứ tự | Việc | Lý do gấp |
|---|---|---|
| 1 | Sao lưu dữ liệu giám sát hiện có ra nơi an toàn | Bản duy nhất, đuôi rụng dần mỗi ngày (**D2**) |
| 2 | Hỏi về tài khoản `admin` | Quyết định 53,6% dữ liệu chỉ bằng một câu hỏi (**A3**) |
| 3 | Bật xuất billing cho dự án Ralli | Không có thì mọi số của Ralli không kiểm chứng được (**B1**) |
| 4 | Xác nhận `tool-quiz` và `Multi-model-invoice` đã dừng chưa | Hiển thị lẫn với dự án đang chạy sẽ gây hiểu nhầm (**C3**) |
| 5 | Xác nhận hai dự án `tla-ralli` và `gen-lang-client-*` | Có thể đang có lưu lượng ngoài mọi báo cáo (**D1**) |
