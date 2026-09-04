## Context

Hoá đơn Google về dưới dạng 7 file CSV tải tay từ Cloud Console, mỗi project một file. Chúng được gộp thành `data/billing/billing_gop_tru_CTDA.csv` — nhưng **bằng tay**. Dấu vết còn rõ: 7 file có thời điểm sửa đổi 10:28 → 10:36 ngày 05/08, file gộp lúc 10:45.

Đường tự động hoá "đúng bài" là BigQuery billing export, nhưng nó **bị chặn ở quyền**: tài khoản mua qua đại lý Gimasys (`GMSSub` trong tên file = Gimasys), chỉ họ bật được. Đã ghi trong `docs/explore-2026-08-04-nguon-du-lieu-gcp.md` §8.1. Nên chặng "người vào Console tải file" sẽ còn đó, và thiết kế phải chấp nhận điều đó thay vì chờ nó biến mất.

Đối chiếu 7 file thô với file gộp cho thấy phép gộp là **thuần cơ học**: từng project khớp cả số dòng lẫn tổng tiền tới 4 chữ số thập phân, tổng 2.259 dòng / $270,9517. Không dòng nào bị lọc, gộp hay sửa tay. Đây là lý do việc này script hoá được trọn vẹn — và là lý do bản gộp hiện có dùng làm mốc nghiệm thu được.

Pipeline hiện chạy thuần thư viện chuẩn Python (`csv`, `json`, `sqlite3`), toàn bộ 5 loader mất 14,56 giây. `docs/khao-sat-luong-transform-2026-08-10.md` đã kết luận không cần công cụ nặng, và đặc biệt **không dùng pandas** vì ép kiểu ngầm phá quy tắc "thiếu thì NULL, không phải 0".

## Goals / Non-Goals

**Goals:**

- Thay thao tác gộp tay bằng một script chạy lại được, cho ra kết quả giống hệt nhau mỗi lần.
- Chứng minh script đúng bằng cách tái tạo **trùng khít** bản gộp tay hiện có.
- Làm mọi tri thức ẩn trở nên tường minh: ánh xạ project, lựa chọn cột tiền, thứ tự phân loại SKU.
- Biến các giả định về tiền thành bất biến kiểm được mỗi lần chạy.
- Giữ nguyên đường chạy hiện tại: `nap_billing.py` và database không bị đụng ở đợt này.

**Non-Goals:**

- Không thêm cột vào `fact_billing_daily` (4 cột tiền mới) — đợt sau.
- Không thêm cột mốc UTC, không xử lý giờ mùa hè Mỹ, không rải chi phí sang ngày ICT — đợt sau, và còn đang tranh luận nên rải cho `output` thôi hay cả `input`.
- Không chuyển `DELETE` → `UPSERT`, không sửa hai hằng số nghiệm thu ghim cứng trong `nap_billing.py`.
- Không tự động hoá việc tải file từ Console.
- Không xử lý Ralli/CTDA — dự án đó chưa bật billing export, nằm ngoài cả 7 file.

## Decisions

### D1. Giữ file gộp trung gian, không cho `nap_billing.py` đọc thẳng 7 file thô

**Chọn:** hai chặng — `gop_billing.py` sinh file chuẩn hoá, `nap_billing.py` đọc file đó.

**Thay vì:** một chặng, bỏ file trung gian.

**Vì:**
- 11 chỗ trong repo đang đọc file gộp (`test/kiem_tra_du_lieu.py`, `test/soat_ctda.py`, `db/sinh_02_danh_muc.py`, …). Bỏ file trung gian là phải sửa cả 11.
- Bước gộp có đúng tính chất đáng tách ra: nó **thuần và kiểm chứng được**. Chạy script rồi so với file cũ là một bài kiểm tra hồi quy có sẵn. Gộp hai chặng làm một là vứt bài kiểm tra đó đi.
- Khi số sai, mở file trung gian ra soi bằng mắt rẻ hơn nhiều so với gỡ lỗi trong lúc nạp.

**Đánh đổi:** hai bản dữ liệu có thể lệch nhau. Chặn bằng cách file trung gian **luôn được sinh ra, không bao giờ sửa tay**, và đặt ở `data/da_xu_ly/` — thư mục vốn dành cho dữ liệu dẫn xuất — thay vì để lẫn cạnh file thô như hiện nay. Vị trí phát tín hiệu đó.

### D2. Ánh xạ project khai báo tường minh, so khớp chính xác tuyệt đối

**Chọn:** bảng 7 dòng gõ tay, khớp chuỗi chính xác, tên lạ thì dừng.

**Thay vì:** so khớp gần đúng / chuẩn hoá chuỗi rồi đoán.

**Vì:** tên file mang *tên hiển thị*, cột `project` cần *project ID*. Đây là hai không gian định danh khác nhau, và phân bố quan hệ giữa chúng là tệ nhất có thể cho việc đoán:

| Tên hiển thị (trong tên file) | Project ID | Quan hệ |
|---|---|---|
| `AI-chatbot-contact-center` | `pro-tuner-454203-v3` | không có gì chung |
| `AI-sale_agent` | `tranquil-post-471401-c1` | không có gì chung |
| `Multi-model-invoice` | `multimodal-invoice` | gần giống, khác thật |
| `tool-quiz` | `tools-quizz` | gần giống, khác thật |
| `CRM-feedback` | `crm-500509` | chung tiền tố |
| `AI-chatbot-contract-hop-dong` | `ai-chatbot-contract` | chung tiền tố |
| `feedback-dms-tiep-thi` | `feedback-dms-tiep-thi` | trùng khớp |

Thuật toán đoán sẽ trúng 5/7 — đủ để *trông như đang chạy* — rồi trượt đúng hai project chiếm **$219,10 / $270,95 = 80,9% số tiền**.

Thêm một lý do nữa: tên hiển thị **sửa được bất cứ lúc nào** trên Console mà không ảnh hưởng project ID. Ai đó đổi tên hiển thị là ánh xạ đoán trượt, im lặng.

**Kiểm chéo:** cả 7 project ID SHALL đối chiếu với `dim_agent.gcp_project_id`. Bằng chứng chúng là ID thật chứ không phải chuỗi tự đặt: `fact_monitoring` — dữ liệu do Cloud Monitoring phát ra — chứa đúng 7 chuỗi này.

### D3. `Decimal` cho mọi phép tính tiền, không dùng `float`

**Chọn:** `decimal.Decimal` đọc thẳng từ chuỗi gốc.

**Vì:** các bất biến ở `nghiem-thu-gop-billing` là **đẳng thức chính xác**, không phải so sánh có ngưỡng. Chúng không kiểm được nếu giá trị đã đi qua dấu phẩy động. Dùng ngưỡng sai số thay cho `Decimal` là tự bịt mắt đúng chỗ cần nhìn.

Làm tròn dùng `ROUND_HALF_UP` — đã đo khớp `Subtotal` trên 2.259/2.259 dòng.

**Đính chính sau khi đo (phát hiện lúc chạy thật):** bản thiết kế đầu tiên đặt bất biến là `Cost − Savings − Other == Unrounded` ở độ chính xác đầy đủ. Sai. `Cost ($)` **cũng đã làm tròn tới xu**, nên đẳng thức đó chỉ đúng **4/2259 dòng** — trúng ngẫu nhiên ở những dòng `Unrounded` vừa vặn hai chữ số. Bất biến đúng là ở độ chính xác xu:

```
round(Cost − Savings − Other, 2) == Subtotal          2259/2259
Cost == round(Unrounded, 2)   (khi giảm giá = 0)      2259/2259
round(Unrounded, 2) == Subtotal                       2259/2259
```

Kéo theo một giới hạn thật, phải nói thẳng: **`Unrounded subtotal` không kiểm chéo được**. Nó là cột duy nhất mang giá trị dưới-xu; ba cột kia đều đã tròn. Ta tin nó vì nó là cột Google tính ra, không phải vì ta chứng minh được nó. Đây chính là lý do nó được chọn làm cột chuẩn ở D6 — không phải vì đáng tin hơn, mà vì nó là cột **duy nhất** còn giữ thông tin.

### D4. Tự nghiệm thu ba tầng, chạy trước khi ghi file

```
tầng 1  từng dòng      Cost − Savings − Other == Unrounded
                       round(Unrounded, 2)    == Subtotal
                              │
tầng 2  từng project   số dòng và tổng tiền == file thô tương ứng
                              │
tầng 3  toàn bộ        trùng khít billing_gop_tru_CTDA.csv
                       (2.259 dòng · $270,9517)
                              │
                              ▼
                        mới được ghi file
```

Ba tầng bắt ba loại lỗi khác nhau: tầng 1 bắt lỗi hiểu sai cột, tầng 2 bắt lỗi mất/nhân đôi/gán nhầm dòng, tầng 3 bắt lỗi đổi ý nghĩa dữ liệu so với bản đã dùng dựng database.

Tầng 3 là **tạm thời theo bản chất** — nó ghim vào một ảnh chụp cụ thể. Khi có bản export mới, tầng 3 không còn áp dụng cho dữ liệu mới, nhưng vẫn chạy được trên bộ file cũ để bắt hồi quy. Vì vậy nó là một **cờ tuỳ chọn** (`--doi-chieu`), không phải phép kiểm mặc định — khác với tầng 1 và 2 vốn luôn đúng với mọi bản export.

Đây chính là bài học từ `nap_billing.py` hiện tại: nó ghim `!= 2259` và `!= $270.9517` làm điều kiện dừng **mặc định**, nên bản export ngày mai sẽ làm nó dừng. Thiết kế này tách hai thứ đó ra.

### D5. Đầu ra có ngày trong tên, sắp xếp ổn định

`data/da_xu_ly/billing/billing_<YYYY-MM-DD>.csv`, sắp theo `(project, ngay, sku_id)`.

**Vì:** ngày trong tên giữ được lịch sử các bản export — thứ mà `data/billing/` hiện không có, và là đúng cái bẫy mà `nap_monitoring.py:44` đã dính (ghim cứng `2026-08-06-1m`, cào mới thì đọc nhầm thư mục cũ và **báo thành công**).

Sắp xếp ổn định để hai lần chạy cho ra file giống nhau tới từng byte — điều kiện để `diff` có ý nghĩa.

### D6. Tên cột đầu ra: giữ `chi_phi_usd`, bốn cột mới có hậu tố rõ nghĩa

```
ngay, project, service, sku_id, sku_ten, loai, so_luong,
chi_phi_usd             ← Unrounded subtotal. CỘT CHUẨN, mọi KPI lấy ở đây
chi_phi_niem_yet_usd    ← Cost, trước giảm giá
giam_cam_ket_usd        ← Savings programs
giam_khac_usd           ← Other savings
chi_phi_hoa_don_usd     ← Subtotal, số Gimasys thu tiền
```

Giữ nguyên tên `chi_phi_usd` là cố ý: 11 chỗ đang đọc nó và nó vẫn đúng nghĩa. Rủi ro thật của việc giữ 5 cột tiền là người viết truy vấn sau này chọn nhầm cột — chặn bằng cách không cột nào mang tên chung chung, mỗi hậu tố nói rõ nó là chặng nào của phép tính.

Đầu ra cũng thêm cột `loai` (`cached`/`output`/`input`) mà bản gộp tay không có, vì `nap_billing.py` vẫn phải tự suy lại. Cột này KHÔNG tham gia phép đối chiếu tầng 3 — bản gộp tay không có nó để so.

### D7. Không dùng pandas, không thêm phụ thuộc

Thuần `csv` + `decimal` + `pathlib` + `sqlite3`. Kế thừa nguyên kết luận của `docs/khao-sat-luong-transform-2026-08-10.md` §3: pandas **có hại ở đây** vì ép kiểu ngầm biến giá trị thiếu thành `NaN` rồi thành float, phá quy tắc 5. Quy mô cũng không đòi hỏi gì: 716 KB, 2.259 dòng.

## Risks / Trade-offs

**Bảng ánh xạ 7 dòng sẽ lỗi thời khi có project thứ 8** → script dừng và in tên hiển thị lạ cùng danh sách tên đang khai báo. Hỏng ồn ào, sửa mất một dòng. Đây là đánh đổi cố ý so với ánh xạ tự động vốn hỏng im lặng.

**Hai bản dữ liệu (file gộp cũ và file mới) cùng tồn tại một thời gian** → giai đoạn chuyển tiếp có hai nguồn. Giảm thiểu: đợt này KHÔNG đổi `nap_billing.py` sang đọc file mới. File mới chỉ được sinh ra và đối chiếu. Việc chuyển nguồn là bước riêng, sau khi đã thấy hai file trùng khít.

**Người vận hành chỉ tải 5/7 file** → tầng 2 vẫn đạt (mỗi project tự khớp với file của nó), tầng 3 sẽ trượt vì thiếu dòng. Script phải in rõ danh sách file đã chọn ngay từ đầu để người dùng thấy thiếu — đây là lý do yêu cầu "in ra file đã chọn kèm số dòng" nằm trong spec chứ không phải chuyện tiện ích.

**Ngày cuối của mỗi bản export chưa chốt xong** (billing trễ ~1 ngày; đo được 04/08 lệch >80% so với monitoring ở 2/7 project) → đợt này KHÔNG xử lý, vì file gộp tay cũng chứa ngày đó và tầng 3 cần trùng khít. Ghi nhận để đợt sau.

**Đối chiếu `dim_agent` cần đọc SQLite** → thêm một phụ thuộc vào database cho một script vốn chỉ xử lý file. Chấp nhận vì đó là chỗ duy nhất project ID được khai báo chính thức, và mở ở chế độ chỉ đọc (`mode=ro`). Lưu ý kỹ thuật: URI SQLite coi `\` của Windows là ký tự thoát, phải dùng `Path.as_posix()`.

**Console Windows mặc định cp1252 sẽ ném `UnicodeEncodeError`** khi in tên có dấu tiếng Việt — đã ghi trong `db/01_schema.sql`. Script phải đặt `PYTHONIOENCODING=utf-8` hoặc ghi ra bằng UTF-8 tường minh.

## Migration Plan

1. Thêm `scripts/gop_billing.py` và thư mục `data/da_xu_ly/billing/`. Không sửa file nào đang có.
2. Chạy với `--doi-chieu data/billing/billing_gop_tru_CTDA.csv`. Phải trùng khít.
3. Dừng lại ở đây. `nap_billing.py` vẫn đọc file cũ.
4. *(bước riêng, không thuộc change này)* Sau khi trùng khít được xác nhận, chuyển `nap_billing.py` sang đọc file mới nhất trong `data/da_xu_ly/billing/`.

**Quay lui:** xoá file script và thư mục đầu ra. Không có gì để hoàn tác vì không file nào đang có bị sửa.

## Open Questions

1. **File gộp có nên mang thêm `agent_id` không?** Hiện chỉ có `project`, nên mọi truy vấn theo agent phải join qua `dim_agent.gcp_project_id`. Thêm `agent_id` làm join biến mất, nhưng file trung gian sẽ hết là "bản chuẩn hoá thuần của hoá đơn" mà mang theo tri thức nội bộ. **Đợt này để nguyên** — thêm cột thì tầng 3 vẫn so được (cột thừa bị bỏ qua), nên quyết định sau vẫn rẻ.
2. **Có nên thêm cột nguồn (tên file, thời điểm gộp) vào đầu ra không?** Có ích khi truy vết, nhưng phá tính "hai lần chạy ra file giống hệt nhau". Nghiêng về đưa vào một file `.meta.json` bên cạnh thay vì vào chính CSV.
