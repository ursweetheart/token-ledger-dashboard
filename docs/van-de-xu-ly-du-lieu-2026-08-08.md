# Các vấn đề do quá trình xử lý dữ liệu của ta

> **Phạm vi:** những vấn đề **do script và cách làm việc của đội tạo ra**, không phải khuyết tật của dữ liệu gốc
> **File anh em:** [`van-de-du-lieu-2026-08-08.md`](van-de-du-lieu-2026-08-08.md) — chứa vấn đề của **dữ liệu gốc**

---

## Vì sao tách làm hai file

Vấn đề của dữ liệu và vấn đề của cách ta xử lý dữ liệu **thuộc hai người khác nhau**:

| | Ai chịu trách nhiệm | Sửa bằng cách nào |
|---|---|---|
| Vấn đề **dữ liệu gốc** | Đội phát triển ứng dụng, hoặc Google | Sửa ứng dụng, bật billing, hỏi nghiệp vụ |
| Vấn đề **xử lý** (file này) | Chính đội mình | Sửa script, đổi cách làm |

Trộn chung sẽ dẫn tới hai hiểu nhầm ngược nhau: hoặc đổ lỗi cho ứng dụng về thứ mình tự gây ra, hoặc bỏ qua lỗi của mình vì tưởng là khuyết tật của nguồn.

Có một lý do kỹ thuật nữa, quan trọng hơn:

> **Kết luận về dữ liệu phải rút ra từ dữ liệu thô.** Nếu rút ra từ bảng đã thống kê, ta có nguy cơ **tự tạo ra vấn đề trong lúc thống kê** rồi tưởng đó là vấn đề của dữ liệu.

Điều này đã xảy ra thật một lần — xem **X1**.

---

## Ba tầng dữ liệu, phải phân biệt được

```
   TẦNG 1  ─  THÔ            từng lượt gọi, từng dòng hoá đơn
              db-token_usage-raw.json · billing/*.csv · du_lieu_giam_sat/*.csv
                    │
   TẦNG 2  ─  ỨNG DỤNG CỘNG  ứng dụng tự gom sẵn rồi trả về qua API
              token-usage-year.json → by_unit, by_user, timeline…
                    │
   TẦNG 3  ─  TA NỐI RA      script của mình gom, nối, đổi định dạng
              17 file .csv trong data/ctda/ và data/tla-hd/
```

**Cách nhận ra tầng 3 chỉ trong một giây:** mọi file CSV trong `data/` đều có **cột `agent`** ở vị trí đầu tiên, và **không file JSON nào có**. Ứng dụng không biết khái niệm "agent" — cột đó do script mình thêm vào để gộp hai nguồn lại.

```
   24 file .json   →  ứng dụng trả về nguyên xi        (tầng 1 và 2)
   17 file .csv    →  script mình sinh ra              (tầng 3)
```

Rủi ro tăng dần theo tầng. Tầng 3 là tầng duy nhất mình có thể tự bịa ra số.

---

## Kết quả kiểm tra: tầng 3 sai ở đâu

Đã đối chiếu **từng file CSV** với mảng JSON tương ứng.

**Mười file chỉ đổ phẳng một mảng JSON ra bảng — khớp tuyệt đối:**

| Dự án | File | Kết quả |
|---|---|---|
| TLA HĐ | `by-unit` · `by-user` · `by-function` · `by-model` · `timeline-monthly` | **5/5 khớp** |
| Ralli | `by-unit` · `top-users` · `by-function` · `by-model` · `timeline-monthly` | **5/5 khớp** |

**Ba file không có JSON đối ứng — tức bắt buộc phải NỐI BẢNG mới tạo ra được:**

| File | Dòng | Trạng thái |
|---|---:|---|
| `tla-hd/user-usage-with-unit.csv` | 28 | ❌ **đã sai** — xem **X1** |
| `tla-hd/users-by-unit.csv` | 42 | chưa kiểm |
| `tla-hd/adoption-by-unit.csv` | 7 | chưa kiểm |

> **Quy luật rút ra: đổ phẳng thì an toàn, nối bảng thì sinh lỗi.**
>
> Đổ phẳng không có chỗ nào để bịa. Nối bảng thì phải quyết định "khi không khớp thì ghi gì" — và chính quyết định đó là chỗ sinh ra số không có thật.

---

# X1. File dẫn xuất báo sai, thổi phồng phần chưa gán 16,4%

> **Nguồn:** `data/tla-hd/user-usage-with-unit.csv` (tầng 3)
> Đối chiếu với `data/tla-hd/token-usage-year.json` → `by_unit` (tầng 2)

### Vấn đề

File `user-usage-with-unit.csv` gán nhãn `CHUA GAN DON VI` cho **7 tài khoản**. Cộng theo file này ra **1.504 lượt** chưa gán đơn vị, trong khi số thật của ứng dụng là **1.327**.

Sai **177 lượt / 5.503.739 token** — thổi phồng phần "chưa gán" thêm **16,4%**.

### Vì sao

✅ **Chứng minh được.** File này **không phải do ứng dụng trả về**. Script của mình nối `by-user-2026.csv` với bảng nhân sự `users-by-unit.csv` **theo tên đăng nhập**.

Bảy tài khoản không tìm thấy trong bảng nhân sự, nên script gán cho chúng nhãn `CHUA GAN DON VI`. Nhãn đó phản ánh **kết quả phép nối của ta**, không phản ánh cách ứng dụng thực sự quy đơn vị.

Ứng dụng quy 5 trong 7 tài khoản đó về phòng ban có tên — vì nó **đóng dấu đơn vị lên từng lượt gọi**, không tra ngược từ hồ sơ người dùng.

### Bằng chứng

Dấu hiệu nhận ra nằm ngay trong giá trị của ô: `CHUA GAN DON VI` — **viết hoa toàn bộ, không dấu tiếng Việt**. Dữ liệu gốc dùng `Chưa xác định` (có dấu, viết thường). Hai kiểu viết khác nhau vì hai nơi sinh ra khác nhau.

```
   Cộng theo user-usage-with-unit.csv     1.504 lượt   38.979.261 token
   Khối "Chưa xác định" của ứng dụng      1.327 lượt   33.475.522 token
   ─────────────────────────────────────────────────────────────────────
   Chênh                                   +177 lượt   +5.503.739 token
```

Phần chênh đúng bằng 5 tài khoản `test4` + `test1` + `test3` + `test2` + `Nghiệp vụ BH1`.

### Ảnh hưởng

Đây là **bằng chứng cụ thể cho lý do tách hai file này**. Nếu ai đó dùng `user-usage-with-unit.csv` làm căn cứ viết báo cáo, họ sẽ khẳng định một vấn đề **nghiêm trọng hơn thực tế 16,4%** — và vấn đề đó là do mình tạo ra, không phải của ứng dụng.

**Việc cần làm:** hoặc sửa script cho khớp cách ứng dụng quy đơn vị, hoặc bỏ hẳn file này và đọc thẳng từ `token-usage-year.json`.

---

# X2. Script cào ghi đè tại chỗ, không khôi phục được quá khứ

> **Nguồn:** cấu trúc thư mục `data/ctda/` và `data/tla-hd/` — file nằm phẳng, không có thư mục theo ngày
> `.gitignore` dòng `data/`

### Vấn đề

Mỗi lần chạy script cào, file cũ bị thay thế hoàn toàn.

### Vì sao

✅ **Chứng minh được.** Hai yếu tố cộng lại:

1. API bỏ qua tham số `date_from` → **không xin lại dữ liệu cũ được** (đây là vấn đề của ứng dụng, xem **B6** ở file kia)
2. Script ghi đè trực tiếp lên file cùng tên → bản cũ biến mất *(đây là phần của mình)*

Yếu tố 1 không sửa được. Yếu tố 2 sửa được ngay — và chỉ cần sửa một yếu tố là rủi ro biến mất.

### Bằng chứng

Toàn bộ file trong `data/ctda/` và `data/tla-hd/` nằm phẳng, không có thư mục theo ngày.

Nghiêm trọng hơn: thư mục `data/` nằm trong `.gitignore` — **git không theo dõi file nào ở đó**. Không có bản sao nào để phục hồi.

Đối chứng cho thấy cách làm đúng đã tồn tại sẵn trong dự án: thư mục giám sát được đặt tên `du_lieu_giam_sat/2026-08-06-1m/` — **có gắn ngày**. Chỉ hai thư mục ứng dụng là không.

### Ảnh hưởng

**Đây là rủi ro cao nhất về mặt vận hành trong toàn bộ dự án.** Một lần chạy nhầm là mất dữ liệu vĩnh viễn, không có gì cứu được.

**Việc cần làm ngay:** đổi sang cấu trúc có gắn ngày (`data/ctda/2026-08-08/`) **trước khi cào lần tiếp theo**, và bắt đầu chụp ảnh dữ liệu hằng ngày.

---

# X3. Khâu chuyển JSON sang CSV làm rơi mất trường

> **Nguồn:** ba cặp file trong `data/ctda/`: `units.json`↔`units.csv` · `users-list.json`↔`users.csv` · `db-token_usage-raw.json`↔`.csv`

### Vấn đề

Ba file có cả hai định dạng, và bản CSV **mất một số trường** so với bản JSON.

### Vì sao

✅ **Chứng minh được.** CSV là bảng phẳng, không biểu diễn được cấu trúc lồng nhau, nên script chuyển đổi đã lược bớt.

Đây **không phải khuyết tật của ứng dụng** — bản JSON có đủ. Mất mát xảy ra ở khâu mình chuyển đổi.

### Bằng chứng

Số dòng khớp tuyệt đối, nhưng số cột thì không:

| File | JSON | CSV | Trường bị mất |
|---|---:|---:|---|
| `db-token_usage-raw` | 7.924 | 7.924 | *(không mất, nhưng 3 trường lồng bị nén thành chuỗi)* |
| `units` | 108 | 108 | `updated_at` |
| `users-list` → `users` | 890 | 890 | `address`, `company_id`, `require_password_change` |

Điểm tích cực: script ghi **ô rỗng** cho trường thiếu, **không tự điền `0`**. Đó là lựa chọn đúng.

Nhưng cái bẫy nằm ở người đọc tiếp theo: mở bằng Excel hoặc nạp bằng `pandas`, ô rỗng thành `NaN`, rồi rất dễ bị `.fillna(0)` biến tiếp thành `0` — và 6.871 dòng "không đo được" lặng lẽ trở thành "đo được và bằng 0".

### Ảnh hưởng

**Dùng CSV để xem cho dễ, dùng JSON để tính.** Mọi phép tính chính thức phải đọc từ JSON.

---

# X4. Tên thư mục `1m` mô tả sai nội dung bên trong

> **Nguồn:** `data/raw_google_console/du_lieu_giam_sat/2026-08-06-1m/` — tên thư mục so với cột `ts_ict` của bảy file bên trong

### Vấn đề

Hậu tố `1m` khiến người đọc hiểu là bản cào chỉ có 1 tháng. Thực tế nó trải **196 ngày**, từ 22/01 đến 06/08/2026.

### Vì sao

✅ **Chứng minh được.** Đây thuần tuý là **lỗi đặt tên của mình**, dữ liệu bên trong không thiếu gì.

### Bằng chứng

```
   Tên thư mục nói        1 tháng
   api_request_count      22/01/2026 → 06/08/2026     = 196 ngày
```

### Ảnh hưởng

Đã gây ra một kết luận sai thật trong bản đầu của tài liệu dữ liệu: ghi rằng *"Monitoring chỉ có 1 tháng, cần cào lại gấp với cửa sổ rộng hơn"*. Sai hoàn toàn — bản cào đã đầy đủ tối đa, và cào lại hôm nay **còn mất thêm dữ liệu** vì phần đuôi đã rụng.

**Việc cần làm:** đổi tên thành `2026-08-06-196d`, hoặc bỏ hậu tố và ghi phạm vi vào một file `README` bên trong.

---

# X5. Số request theo model là ước lượng, không phải số đo

> **Nguồn:** `test/sinh_du_lieu_dashboard.py` — cách phân bổ request theo tỉ lệ token

### Vấn đề

Trên dashboard, số request của từng model **không phải số đo được**. Đó là số mình tự chia ra.

### Vì sao

✅ **Chứng minh được.** Phép đo `api_request_count` của Google **không có nhãn `model`** — đây là giới hạn của Google, không phải lỗi của mình *(xem **D3** ở file kia)*.

Nhưng **cách xử lý** thì là của mình: script nối theo `(ngày, dự án)` rồi **chia số request theo tỉ lệ token** của từng model trong ngày đó.

### Bằng chứng

Cột `model` rỗng ở mọi dòng có `metric_alias = api_request_count`.

Cách xử lý này từng suýt gây lỗi nặng: bản đầu của script nối theo `(ngày, dự án, model)`. Vì cột model rỗng nên phép nối không khớp dòng nào, và dashboard sẽ hiển thị **0 request ở mọi nơi**.

### Ảnh hưởng

Con số request theo model **đúng ở mức tổng, ước lượng ở mức chia nhỏ**. Nếu một model có token/request lệch hẳn các model khác (ví dụ một model chuyên xử lý câu dài), phép chia theo tỉ lệ token sẽ sai lệch.

**Việc cần làm:** ghi rõ trên dashboard rằng đây là số ước lượng, đừng để người xem tưởng là số đo.

---

# X6. File dẫn xuất và dữ liệu gốc nằm lẫn nhau, không phân biệt được

> **Nguồn:** danh sách file trong `data/ctda/` (22 file) và `data/tla-hd/` (19 file)

### Vấn đề

Mở thư mục ra thấy 41 file trông như nhau. Không có gì cho biết file nào ứng dụng trả về, file nào script mình nối ra.

### Vì sao

✅ **Chứng minh được.** Chưa bao giờ đặt ra quy ước phân biệt.

### Bằng chứng

Đây chính là cơ chế đã sinh ra **X1**: chọn nhầm một file dẫn xuất làm bằng chứng, ra kết luận sai 16,4%.

Hiện chỉ có một dấu hiệu duy nhất để phân biệt, mà **không ai được cho biết**:

```
   file .csv  →  có cột "agent" ở đầu  →  script mình sinh ra
   file .json →  không có cột đó       →  ứng dụng trả về
```

### Ảnh hưởng

Bất kỳ ai — kể cả chính mình sau vài tuần — đều có thể lặp lại lỗi X1.

**Việc cần làm:** tách file dẫn xuất sang thư mục riêng, ví dụ `data/tla-hd/dan_xuat/`. Hoặc tối thiểu là thêm tiền tố tên file.

---

# X7. Hai ứng dụng đặt tên trường khác nhau, script rất dễ đọc nhầm thành 0

> **Nguồn:** `data/tla-hd/token-usage-year.json` so với `data/ctda/token-usage-year.json`

### Vấn đề

Cùng một khái niệm, hai ứng dụng dùng hai tên trường khác nhau. Script nào hardcode tên trường sẽ đọc ra `0` hoặc `None` **mà không báo lỗi**.

### Vì sao

✅ **Chứng minh được.** Hai đội phát triển khác nhau, không có quy ước chung *(bản thân sự không nhất quán này là vấn đề dữ liệu — xem **D7** ở file kia)*. Nhưng **script đọc mà không phòng bị** là phần của mình.

### Bằng chứng

| Khái niệm | TLA HĐ | Ralli (CTDA) |
|---|---|---|
| Tổng token | `total_tokens` | `tokens` |
| Mốc thời gian | `timestamp` | `bucket` |
| Số tiền | `"38.236653075"` *(chuỗi)* | `5.084503180` *(số thực)* |

Lỗi này đã xảy ra **ba lần liên tiếp** trong một phiên làm việc, và cả ba lần đều **giả dạng phát hiện dữ liệu**:

```
   lần 1   cắt khoá 7 ký tự      → "Đội chuyên trách - Vùng 2" và "Vùng 3" gộp làm một → báo LỆCH
   lần 2   hardcode 'tokens'     → CTDA dùng total_tokens, đọc ra 0                    → báo LỆCH
   lần 3   hardcode 'timestamp'  → CTDA dùng bucket, đọc ra None                       → báo LỆCH
```

Không lần nào là vấn đề dữ liệu. Nếu ghi cả ba vào tài liệu thì đã có thêm ba vấn đề **không tồn tại**.

### Ảnh hưởng

Đây là dạng lỗi nguy hiểm nhất vì **nó không làm chương trình dừng**. Đọc ra `0` rồi tính tiếp, cho ra một con số trông hoàn toàn bình thường.

**Việc cần làm:** mọi script đọc dữ liệu hai ứng dụng phải **tự dò tên trường** thay vì hardcode:

```python
def lay(d, *ten):
    for t in ten:
        if t in d and d[t] is not None:
            return d[t]
    return None

lay(dong, "total_tokens", "tokens")     # thay vì dong["tokens"]
```

---

# X8. Chưa cào hai bảng nặng nhất của Ralli

> **Nguồn:** `data/ctda/db-collections.json` → trường `count` và `size`
> Cột "Đã lấy" là đối chiếu tay với file có thật trong `data/ctda/`

### Vấn đề

Hai bảng chiếm 56% dung lượng database gần như chưa động tới.

### Vì sao

✅ **Chứng minh được.** Đây là **quyết định phạm vi của mình**, không phải khuyết tật dữ liệu — dữ liệu vẫn nằm nguyên đó, chỉ là chưa lấy về.

Lý do: chưa có nhu cầu rõ ràng, và dung lượng lớn nên phải cào có phân trang.

### Bằng chứng

| Bảng | Bản ghi | Dung lượng | Đã lấy |
|---|---:|---:|---|
| `conversations` | 1.464 | **222 MB** | chỉ 100 dòng mẫu |
| `assistant_query_logs` | 1.493 | **191 MB** | 1.000 dòng |
| `token_usage` | 7.924 | 1,7 MB | **đủ 100%** |

Bảng `token_usage` — thứ toàn bộ dashboard đang dựa vào — chỉ chiếm **0,23% dung lượng** database.

### Ảnh hưởng

⚠️ **Suy luận:** bảng `conversations` có thể trả lời được câu hỏi lớn nhất đang treo ở **B3** — 88% bản ghi `user_id='system'` là tác vụ nền hay người dùng thật đã mất dấu. Bảng này có `user_id` là **tên đăng nhập thật** và có mốc thời gian.

Nhưng phải cẩn thận: `conversations` **không có trường token nào**. Nó biết *ai hỏi, hỏi gì, lúc nào* nhưng không biết *tốn bao nhiêu*. Muốn ghép chi phí vào người dùng thì phải nối theo thời gian gần nhau — và theo đúng quy luật ở đầu file này, **nối bảng là chỗ sinh lỗi**. Cách nối đó chưa kiểm chứng được cho tới khi cào thật.

---

# Tổng hợp

## Tám vấn đề, xếp theo mức độ

| # | Vấn đề | Mức độ | Sửa được |
|---|---|---|---|
| **X2** | Script cào ghi đè, mất dữ liệu vĩnh viễn | 🔴 Nặng | ✅ Ngay |
| **X1** | File dẫn xuất báo sai 16,4% | 🟠 Vừa | ✅ Ngay |
| **X6** | File dẫn xuất lẫn dữ liệu gốc | 🟠 Vừa | ✅ Ngay |
| **X7** | Script hardcode tên trường, đọc ra 0 mà không báo | 🟠 Vừa | ✅ Ngay |
| **X4** | Tên thư mục `1m` mô tả sai | 🟡 Nhẹ | ✅ Ngay |
| **X5** | Request theo model là ước lượng | 🟡 Nhẹ | Ghi chú rõ |
| **X3** | CSV rơi trường so với JSON | 🟡 Nhẹ | Dùng JSON |
| **X8** | Chưa cào 2 bảng nặng nhất | ⚪ Cơ hội | Có thể làm |

**Toàn bộ tám vấn đề đều sửa được bằng nội lực**, không cần chờ ai trả lời, không cần quyền truy cập mới. Khác hẳn file dữ liệu — ở đó quá nửa phải chờ câu trả lời từ bên ngoài.

---

## Việc cần làm, xếp theo thứ tự

| Thứ tự | Việc | Vấn đề |
|---|---|---|
| 1 | Đổi cấu trúc thư mục cào sang có gắn ngày | **X2** |
| 2 | Sao lưu bản cào giám sát 06/08 ra nơi an toàn | **X2** |
| 3 | Tách file dẫn xuất sang `dan_xuat/` | **X6**, **X1** |
| 4 | Sửa hoặc bỏ `user-usage-with-unit.csv` | **X1** |
| 5 | Kiểm nốt `users-by-unit.csv` và `adoption-by-unit.csv` | mục đầu file |
| 6 | Đổi tên `2026-08-06-1m` thành `2026-08-06-196d` | **X4** |
| 7 | Thay hardcode tên trường bằng hàm tự dò | **X7** |

---

## Điều đã kiểm và thấy KHÔNG có vấn đề

Để cân bằng — phần lớn công việc xử lý là đáng tin:

| Phép kiểm | Kết quả |
|---|---|
| 10 file CSV đổ phẳng ↔ mảng JSON tương ứng | **10/10 khớp tuyệt đối** |
| 13 kết luận về Ralli tính lại **từ dữ liệu thô** | **13/13 đứng vững** |
| Dữ liệu thô Ralli ↔ API tổng hợp | 5/5 khớp (7.924 lượt · 44.692.501 token) |
| Hoá đơn gộp ↔ 7 file thành phần | Khớp tuyệt đối ($270,9517) |
| Giao diện web ↔ file đã cào | 84 điểm khớp, 0 lỗi |

Phép kiểm quan trọng nhất là dòng thứ hai. Script `test/kiem_tu_raw.py` **bỏ qua mọi file thống kê**, tính lại từ `db-token_usage-raw.json` rồi so với con số tài liệu đang khai.

Đáng chú ý nhất là **B4**: tính lại bằng đường hoàn toàn khác — `raw.user_id` → `users-list.json` → `units.json` — vẫn ra đúng **7.660 lượt / 43.423.705 token**, khớp tuyệt đối với số ứng dụng cộng sẵn.

Nghĩa là các kết luận về Ralli **không phải sản phẩm của khâu thống kê**. Chúng có thật trong dữ liệu thô.

---

## Giới hạn: TLA Hợp đồng không kiểm lại được từ thô

Thư mục `data/tla-hd/` có 10 file JSON, và **không file nào chứa từng lượt gọi**. Toàn bộ là thống kê ứng dụng cộng sẵn.

Hệ quả cho các mục ở file dữ liệu:

| Mục | Kiểm lại từ thô được không |
|---|---|
| **A1**, **A2**, **A5**, **A6** | ✅ được — đối chiếu với **hoá đơn và giám sát của Google**, đó là thô |
| **A3**, **A4** | ❌ **không** — chỉ so các bảng thống kê của ứng dụng với nhau |

A3 và A4 vẫn là phát hiện có giá trị, nhưng phải nói rõ giới hạn: chúng chứng minh **ứng dụng tự mâu thuẫn với chính nó**, chứ chưa chứng minh được điều gì về dữ liệu bên dưới.

Muốn kiểm lại thật thì cần một endpoint trả về từng lượt gọi của TLA Hợp đồng — hiện chưa tìm thấy.
