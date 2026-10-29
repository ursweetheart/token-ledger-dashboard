# Ba nguồn dữ liệu có trùng nhau không — ghi chú trao đổi 21/09/2026

Viết để mang đi trao đổi. Tách rõ phần **xác minh được bằng code** khỏi phần **chưa biết,
phải hỏi dữ liệu**.

Chưa truy cập được database lúc viết, nên mọi con số trong tài liệu này là **hình dạng vấn
đề**, không phải kết quả đo.

---

## 1. Câu hỏi

Dashboard nhận dữ liệu từ bốn nguồn. Ba trong số đó có thể cùng đếm một lưu lượng:

| Nguồn | Lấy về bằng cách nào | Ai đếm |
|---|---|---|
| `billing` | tải thủ công CSV từ Google Console | Google, theo project |
| `monitoring` | `scripts/pull_monitoring.py` | Cloud Monitoring, theo project |
| `gateway` | `db/load_gateway.py` đọc sổ LiteLLM | chính ta |
| `app` | cào từ nhật ký của app | chính app |

Chiều 20/09 khi tải billing của project CRM, nhận ra agent CRM đã thông luồng qua Gateway.
Vậy LiteLLM cũng ghi lưu lượng đó. **Lo: billing và monitoring có cộng chồng lên số Gateway
đã lưu không.**

---

## 2. Xác minh được bằng code — hệ thống CÓ cơ chế chống cộng đôi

Bảng `fact_usage_daily` cố ý để bốn nguồn **nằm cạnh nhau, không cộng vào nhau**. Cùng một
ngày, cùng một agent, cùng một model có thể có tới bốn dòng. Đó là chủ ý, không phải lỗi —
chính tỷ lệ giữa các nguồn là bộ đo phát hiện app ghi thiếu.

Chỗ khử trùng nằm ở view `usage_resolved`:

```
  fact_usage_daily  (mot khoa -> toi da 4 dong)
  ┌──────────┬──────────┬──────────┬──────────┐
  │ billing  │monitoring│   app    │ gateway  │
  └────┬─────┴────┬─────┴────┬─────┴────┬─────┘
       └──────────┴────┬─────┴──────────┘
                       ▼
             usage_resolved   ← COALESCE, CHON mot nguon
                       │
         token:  gateway > billing > monitoring > app
         tien:   billing > gateway
                       ▼
              dashboard doc o day
```

- Định nghĩa view: `db/migrations/sql/005_gateway_cost_vao_view.sql:75` — là `COALESCE`,
  **không phải** `SUM`.
- Phép kiểm canh nó: `scripts/audit_db.py:329` (`double_counted`) bắt view phải chép y nguyên
  con số của nguồn nó khai đã chọn. Thêm `usage_resolved: one row per key` ở dòng 316.
- `scripts/audit_db.py` chạy sẵn ở bước 9/9 của `scripts/update_dashboard.py`.

**Kết luận mục này: ở tầng view, không có cộng đôi. Đã có phép kiểm tự động.**

---

## 3. Nhưng cơ chế đó chỉ chắc khi khoá `(ngày, agent, model)` khớp nhau

### 3.1 Model — KHỚP, đã kiểm

Ba không gian tên khác nhau, bảng bí danh gom hết về cùng một `model_id` (`db/02_catalog.sql`):

| nguồn | tên thô | model_id |
|---|---|---|
| gateway | `gemini/gemini-2.5-flash` | 2 |
| monitoring | `gemini-2.5-flash` | 2 |
| billing | SKU `1C33-4690-9D67`, … | 2 |

Bài học đã ghi trong `db/rules.py:40`: monitoring của project mà Gateway gọi tới báo **tên
trần**, còn nguồn gateway báo tên **có tiền tố nhà cung cấp**. Cùng một model, hai cách viết.
Bảng bí danh xử lý đúng chỗ này.

### 3.2 Ngày — KHÔNG khớp tuyệt đối, và ta chấp nhận

`db/load_billing.py` ghi rõ: cột `day` của hoá đơn là ngày cắt theo **múi Thái Bình Dương**,
nhưng ta **coi luôn là giờ Việt Nam**. Gateway và monitoring là giờ Việt Nam thật. Lệch tới
15 giờ.

**Quyết định 21/09: giữ nguyên quy ước này.** Đổi nghĩa là nạp lại toàn bộ lịch sử hoá đơn,
không đáng, và về sau khi mọi agent đi qua Gateway thì vấn đề tự hết.

Đánh đổi đã biết trước: **tổng cả kỳ đúng tuyệt đối, chỉ từng ngày lẻ là lệch.**

Luật đi kèm, phải nhớ khi đối chiếu:

```
  so theo NGAY:   billing 10/09 = 2,1tr   gateway 10/09 = 1,9tr
                  → lech 0,2tr  ← VO NGHIA, chi la mui gio

  so theo KY:     billing 01→20/09 = 31,4tr   gateway 01→20/09 = 30,8tr
                  → lech 0,6tr  ← CO nghia
```

*(số trong khung là ví dụ minh hoạ, không phải số đo)*

---

## 4. Riêng CRM: ba project, và ta chỉ giữ một

Từ `docs/archive/gateway/fallback-crm-12-09.md` mục 2.1:

| Project | Vai trò | Quyết định 21/09 |
|---|---|---|
| `crm-500509` | project **thật** của agent 7, đang ghi trong `dim_agent` | **giữ, nạp bình thường** |
| `60854134008` | project của khoá Vertex express mà **Gateway** dùng | kệ, không nạp |
| `crm-test-508114` | project **thử**, đường dự phòng khi Gateway chết | kệ, không nạp |

Hiện trạng code khớp với quyết định này:

- `scripts/pull_monitoring.py:45` chỉ kéo 7 project cũ — không có hai project kia.
- `scripts/merge_billing.py:90` chỉ map `"CRM-feedback" → crm-500509`.
- Nếu ai nạp billing của project lạ, `db/load_billing.py` **dừng hẳn** với `unknown project`.
  Nó không nuốt lặng.

### 4.1 Hệ quả: mối lo đổi chiều

Vì bỏ project khoá Vertex, billing/monitoring của agent 7 và sổ gateway của agent 7
**không còn đo cùng một luồng**:

```
  agent 7 (CRM)
    ├── luu luong di THANG  ──► project crm-500509  ──► billing + monitoring  ✅ nap
    └── luu luong qua GATEWAY ─► project 60854134008 ─► (ke no)               ❌ khong nap
                               └► so LiteLLM         ──► source 'gateway'      ✅ nap
```

Hai nguồn này là **hai mảnh rời** của cùng một agent, không phải hai cách đo một thứ.

Nhưng `usage_resolved` không biết thế. Nó chỉ thấy cùng khoá `(ngày, agent 7, model 2)` có
hai nguồn, rồi áp luật `COALESCE(gateway, billing, …)` — **chọn gateway, vứt billing**.

**Bệnh không phải cộng đôi. Bệnh là nuốt mất.**

### 4.2 Chưa biết — phải hỏi dữ liệu

Bệnh trên chỉ có thật nếu `crm-500509` **vẫn còn phát sinh** sau ngày chuyển (~10/09/2026).
Nếu CRM đã chuyển sạch và project cũ về 0, thì không có gì để nuốt, và không phải làm gì cả.

**Không đoán được. Phải đo.**

---

## 5. Cách dò: đo phần view đã vứt đi

Một truy vấn trả lời được cả hai bệnh cùng lúc.

```
  voi moi khoa co >1 nguon:
      token_duoc_chon  = con so view bao cao
      token_bi_vut     = con so cua nguon con lai

  ty le  bi_vut / duoc_chon:
     ~100%    → hai cong to do CUNG luu luong  → COALESCE dung, yen tam
     ~0-20%   → hai LUONG KHAC nhau bi ep chung khoa → dang nuot so
     >150%    → dang chon nham nguon
```

Truy vấn **chỉ đọc**, chạy trên PostgreSQL `token_ledger_v2`:

```sql
WITH k AS (
  SELECT day, agent_id, model_id, source, SUM(total_tokens) AS t
  FROM fact_usage_daily
  WHERE total_tokens IS NOT NULL
  GROUP BY day, agent_id, model_id, source
)
SELECT g.name AS agent,
       v.token_source AS nguon_duoc_chon,
       k.source       AS nguon_bi_vut,
       COUNT(*)            AS so_khoa,
       MIN(v.day)          AS tu_ngay,
       MAX(v.day)          AS den_ngay,
       SUM(v.total_tokens) AS token_duoc_chon,
       SUM(k.t)            AS token_bi_vut,
       ROUND(100.0 * SUM(k.t) / NULLIF(SUM(v.total_tokens), 0), 1) AS ty_le_pct
FROM usage_resolved v
JOIN k ON k.day = v.day AND k.agent_id = v.agent_id
      AND k.model_id = v.model_id AND k.source <> v.token_source
JOIN dim_agent g ON g.agent_id = v.agent_id
GROUP BY g.name, v.token_source, k.source
ORDER BY token_bi_vut DESC;
```

Nó gom theo **cặp nguồn** và theo **cả kỳ**, đúng luật ở mục 3.2 — nên lệch múi giờ không
làm nhiễu kết quả.

### Cách đọc bảng trả về

| Thấy gì | Nghĩa là | Làm gì |
|---|---|---|
| dòng `gateway / monitoring` tỷ lệ ~100% | đúng thiết kế, hai công tơ đo cùng thứ | không làm gì |
| dòng `gateway / billing` của CRM, tỷ lệ thấp | đúng bệnh mục 4.1, đang nuốt số | xem mục 6 |
| **không có dòng CRM nào** | project cũ đã về 0 | xong chuyện |

### Truy vấn phụ, nếu cần nhìn riêng agent 7

```sql
SELECT source, MIN(day) AS tu_ngay, MAX(day) AS den_ngay, COUNT(*) AS so_dong,
       SUM(total_tokens) AS token, SUM(cost_usd) AS tien
FROM fact_usage_daily WHERE agent_id = 7
GROUP BY source ORDER BY source;
```

Nhìn thẳng: `billing` và `gateway` của agent 7 có **chồng khoảng ngày** không.

---

## 6. Ba đường xử lý, nếu đo ra có bệnh

| Cách | Việc phải làm | Chọn khi |
|---|---|---|
| **Không làm gì** | chỉ ghi lại con số đã đo vào nhật ký | project cũ ≈ 0, hoặc lệch dưới 1% |
| **Thêm phép kiểm cảnh báo** | đưa truy vấn mục 5 vào `scripts/audit_db.py` nhóm D (khe dữ liệu im lặng), cảnh báo khi vượt ngưỡng | có lệch, nhưng chưa muốn đụng view |
| **Sửa view** | đổi luật chọn nguồn cho riêng agent 7 | lệch lớn và kéo dài |

**Nghiêng về cách 2.** Sửa `usage_resolved` là đụng vào con số mà cả dashboard đọc. Thêm một
phép kiểm thì không đổi số nào, chỉ làm cái đang im lặng kêu lên — và `audit_db.py` đã chạy
sẵn trong đường ống rồi, không phải dựng gì mới.

---

## 7. Cần đồng nghiệp trả lời

1. Sau ngày chuyển (~10/09), project `crm-500509` **còn phát sinh lưu lượng không**, hay CRM
   đã đi 100% qua Gateway?
2. Đường **dự phòng** (Gateway chết → CRM gọi thẳng, phí ra `crm-test-508114`) đã chạy thật
   lần nào chưa? Nếu có, phần đó hiện **không nguồn nào ghi** — mất hẳn, không phải trùng.
3. Có kế hoạch đưa nốt các agent còn lại qua Gateway không, và bao giờ? Nếu sớm thì cách 1
   (không làm gì) càng hợp lý — vấn đề sẽ tự hết.

---

## 8. Điều chưa chứng minh — đừng đọc thành đã biết

- **Chưa chạy truy vấn nào.** Toàn bộ tài liệu này đọc từ code, không từ dữ liệu.
- Chưa xác minh khoá `KEY_GOOGLE_AI_STU` (tuyến DMS) thuộc project nào. `db/rules.py:40` ngụ ý
  project đích của Gateway **có** được kéo monitoring, nhưng đó là suy từ một ghi chú, chưa đo.
  Nếu đúng thì DMS và CRM có hình dạng **khác nhau**: DMS chồng thật (COALESCE đúng), CRM
  không chồng (COALESCE nuốt số).
- Chưa biết tỷ lệ lệch thật là bao nhiêu, nên chưa chọn được cách nào ở mục 6.
