# Mọi con số tiền phải nói rõ nó đến từ hoá đơn hay suy từ bảng giá

## Why

**28,2% số tiền hiển thị trên dashboard không đến từ hoá đơn nào.** Nó được nhân ra từ
bảng giá, và không một ô nào nói điều đó.

Đo ngày 20/08/2026 trên toàn kỳ 01/01 → 17/08, qua `usage_resolved` (1.189 dòng):

| | USD | |
|---|---:|---:|
| Từ **hoá đơn** Google | $291,9856 | 71,8% · 965 dòng |
| **Suy** từ bảng giá | **$114,4076** | **28,2%** · 224 dòng |
| | **$406,3932** | |

Và nó **không rải đều**. Có agent gần như toàn bộ là suy ra:

| Agent | Hoá đơn | Suy ra | % suy ra |
|---|---:|---:|---:|
| **Trợ lý ảo Ralli** | $0,0000 | $7,6254 | **100,0%** |
| **Trợ Lý Ảo Hợp Đồng** | $18,6497 | $64,9857 | **77,7%** |
| Phân Loại Phản Hồi Tiếp Thị | $8,8990 | $3,9255 | 30,6% |
| Sale Agent | $131,6163 | $31,5010 | 19,3% |
| Multi modal AI Invoice | $17,4434 | $2,9274 | 14,4% |
| Tools Quizzer | $0,0443 | $0,0017 | 3,7% |
| Phân Loại Dữ Liệu CRM | $15,2038 | $0,5184 | 3,3% |
| Chatbot Contact Center | $100,1290 | $2,9224 | 2,8% |

Theo NGÀY còn lệch hơn — **22/228 ngày có hơn một nửa số tiền là suy ra**:

```
   2026-08-17   100,0% suy ra      2026-06-20    99,7%
   2026-03-14    98,4%             2026-04-06    96,4%
   2026-06-17    92,8%             2026-08-02    85,7%
```

Nghĩa là người xem chọn kỳ *"7 ngày gần nhất"* rất dễ rơi đúng vào vùng mà **phần lớn tiền
chưa được hoá đơn nào xác nhận** — và màn hình trình bày nó y hệt tiền đã xác nhận.

### Vì sao có phần suy ra, và vì sao nó không biến mất

Hai nguyên nhân khác hẳn nhau, và người xem cần phân biệt được:

| | Nguyên nhân | Tự hết chưa? |
|---|---|---|
| **Hoá đơn chưa về** | Google phát hành hoá đơn trễ ~1 ngày. Ngày mới nhất luôn 100% suy ra | Có — sau vài ngày dòng đó sẽ có hoá đơn |
| **Agent chưa nối Google Billing** | `tla-ralli` có project trên GCP nhưng **chưa nối billing** | **Không.** Sẽ suy ra mãi cho tới khi ai đó nối |

Trợ lý ảo Ralli thuộc loại thứ hai: $7,6254 chi phí thật, **không hoá đơn nào ghi**. Đó là
chi tiêu vô hình với tổng hoá đơn, và phép suy từ bảng giá là cách duy nhất nhìn thấy nó.

### Việc này đã làm xong cho MỘT bảng

Change `serve-department-metrics-from-database` (commit `6d6eef8`) đã gắn dấu `≈` và tỷ lệ
suy ra cho cột tiền của tab **Phòng ban & User**. Change này **tổng quát hoá** ra 5 tab còn
lại: Tổng quan · Agents · Provider & Model · Chi phí · Hiệu năng.

### Vì sao phép suy đáng tin, và vì sao vẫn phải ghi nhãn

`ref_price` lấy thẳng từ **Cloud Billing Catalog của Google** (`price_source='google'` cho
cả 10 model), không gõ tay. Đối chiếu 965 dòng có cả hai vế: lệch tổng **−0,1%**, lệch
**trung vị mỗi dòng 0,0%**, dòng tệ nhất 6,4%.

Sát đến vậy vẫn **không phải hoá đơn**. Ba lý do phải ghi nhãn dù sai số nhỏ:

1. **Bảng giá đổi thì lịch sử đổi theo.** `ref_price` hiện chỉ có một mốc hiệu lực
   (2026-08-13). Ngày Google đổi giá, mọi con số suy ra của quá khứ sẽ nhảy — còn hoá đơn
   thì không.
2. **Sai số 0,1% là của TỔNG, không phải của từng dòng.** Dòng tệ nhất lệch 6,4%.
3. **Có agent không có hoá đơn để mà lệch.** Với Trợ lý ảo Ralli không tồn tại con số nào
   để đối chiếu — sai số chưa từng được đo.

## What Changes

- `aggregate()` (`web/js/app.js:939`) trả thêm phần tiền suy ra. Đây là **điểm nghẽn duy
  nhất**: 7 chỗ gọi nó nuôi mọi con số tiền trên dashboard, nên sửa một chỗ là phủ cả 6 tab
- Thẻ tiền ở tab Tổng quan nói tỷ lệ suy ra của kỳ đang xem
- Bảng theo agent / model / ngày: ô có phần suy ra mang dấu `≈`, tooltip nói **bao nhiêu
  phần trăm** — không chỉ nói "có"
- Phân biệt **hai lý do**: *"hoá đơn chưa về"* (tự hết) với *"agent chưa nối billing"*
  (không tự hết)
- Xuất CSV kèm cột nguồn tiền, để số mang ra ngoài không mất dấu vết

**KHÔNG làm trong change này**

- Đụng `backend/`, `db/`, `scripts/`. Dữ liệu đã đủ: `usage_resolved.cost_usd` là NULL ở
  đúng những dòng chưa có hoá đơn, và `token_estimated` đã nói dòng nào là ước tính
- Đổi cách TÍNH tiền. Con số giữ nguyên, chỉ thêm phần nói nó từ đâu ra

## Impact

| | |
|---|---|
| **Specs** | `visible-data-provenance` (mở rộng sang chiều TIỀN) |
| **Code** | `web/js/app.js` · có thể `web/index.html` cho thẻ Tổng quan |
| **Không đụng** | `backend/` · `db/` · `scripts/` — không rebuild database |
| **Rủi ro** | Thấp. Không đổi con số nào, chỉ thêm nhãn. Rủi ro thật là **thẩm mỹ**: gắn `≈` lên quá nhiều ô sẽ thành nhiễu và người đọc bỏ qua hết |
| **Quay lui** | Từng tab một commit |
