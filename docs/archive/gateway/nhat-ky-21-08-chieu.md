# Nhật ký chiều 21/08/2026

Tiếp theo `nhat-ky-21-08-sang.md`. Đọc nhanh: mục 1, mục 3 và mục 7.

**Chưa commit.** Mọi phép kiểm xanh.

---

## 1. Tóm tắt

> Chiều nay bịt **việc đỏ cuối cùng** trong repo — API không còn trả 937 họ tên cho bất kỳ
> ai gọi được. Nhưng thứ đáng nhớ hơn nằm ở vòng tự soát **sau khi** code đã chạy đúng:
> nó tìm ra **hai lỗ hổng**, và một trong hai là do chính change này mở ra.

```
   ① Doc lai 4 nhat ky + .docx + .xlsx   -> con gi chua lam
   ② Lam tron change "khoa cho API"      -> 8/8 endpoint doi khoa
   ③ Vong tu soat sau khi da xanh        -> 2 lo hong, 7 loi trong chinh cong cu do
```

Nhóm C trong `viec-can-lam-truoc-api-gateway.md` **hết việc đỏ**. Cả A, B, C đều hết.

---

## 2. Đọc lại tài liệu gốc: ba chỗ giấy tờ đã lệch khỏi hệ thống

Lần đầu đọc trọn `Tài_liệu_triển_khai_API_Gateway.docx` (66 dòng) và cả 3 sheet của
`Master Plan API Gateway.xlsx`. Ba chỗ mâu thuẫn với chính quyết định đã chốt:

| Nơi | Giấy tờ ghi | Thực tế |
|---|---|---|
| `.docx` §1.2 | `tla-rally` · `tools-quiz` | Database đúng: **`tla-ralli`** · **`tools-quizz`**. A2 chốt 20/08, chưa ai sửa file |
| `.docx` §8.1 + `Kế hoạch` GĐ3 | request mang theo **"phòng ban"** | A3 chốt 20/08 đã **bỏ** — tra `account.unit_id`. Giữ nguyên là tạo nguồn sự thật thứ hai |
| Sheet `Database Schema dự kiến` | 3 giá trị `kind` · `token_source` không có `gateway` · không có `ref_source` | Lạc hậu **4 chỗ** so với database sau hai change 20 và 21/08 |

Và một khoảng trống chưa ai đặt tên: **A1-2 chốt "CÓ ghi `fact_attempt`" từ 20/08, nhưng
không bảng nào tồn tại và không change nào nhận việc đó.**

---

## 3. Change `require-a-key-to-read-the-api`

### Trước và sau, đo trên cùng một máy chủ

Không nhớ lại — tái lập hành vi cũ bằng `DASHBOARD_OPEN=1` rồi đo:

| | không khoá (hành vi cũ) | có khoá |
|---|---|---|
| `/api/accounts` | **937 dòng · 930 có họ tên thật** | **401** · thân < 300 byte · không có `full_name` |
| `/api/usage` | 1.189 dòng · 867.657.110 token · $291,985601 | **trùng khít** |

### Chế độ hỏng là "không chạy", không phải "chạy mở"

```
   thieu DASHBOARD_KEY          ->  uvicorn KHONG lang nghe cong nao
   thieu + --reload             ->  van khong
   khoa toan khoang trang       ->  van khong
   DASHBOARD_OPEN=1             ->  chay, IN CANH BAO moi lan khoi dong
```

Đây là task quan trọng nhất của change. Nếu quên đặt biến mà máy chủ vẫn chạy bình thường,
ta có đúng lỗ hổng cũ **cộng thêm** niềm tin sai rằng đã khoá.

### Bốn quyết định đáng ghi

| | |
|---|---|
| `nguoi_goi()` trả **`Principal`**, không trả `True` | Ngày lên JWT chỉ sửa **một hàm**; 8 endpoint không đụng một chữ |
| Header là `Authorization: Bearer`, không phải `X-Dashboard-Key` | Lên JWT thì header **không đổi tên**, chỉ đổi thứ sau chữ `Bearer` |
| `/healthz` là endpoint **duy nhất** không khoá | Giám sát cần biết máy chủ sống. `/api/health` trả lời câu khác hẳn nên vẫn phải có khoá |
| `/docs` · `/openapi.json` **cố ý để mở** | Chúng chỉ mô tả *hình dạng* API; bấm thử không khoá vẫn nhận 401 |

### Ba chỗ đo lại thì khác lúc soạn proposal

| Tưởng | Đo ra |
|---|---|
| `HTTPBearer` mặc định là đủ | Nó trả **403** khi thiếu header, không phải 401 — phép kiểm sẽ trượt vì một lý do chẳng liên quan gì tới xác thực |
| Đặt khoá vào `.env` là chạy | **Không file Python nào của backend đọc `.env`.** Đồng nghiệp làm đúng theo `.env.example` sẽ vẫn không khởi động được, và thông báo lỗi lại bảo họ dán vào `.env` |
| Test JS không liên quan | **Cả 4 kịch bản hỏng cũ trượt** — `localStorage` giả rỗng nên `load()` dừng ở ô nhập khoá, không bao giờ chạm tới nhánh chúng đang kiểm |

---

## 4. Vòng tự soát: hai lỗ hổng tìm thấy **sau khi** mọi thứ đã xanh

Đây là phần đáng đọc nhất. Cả 25 task đã xong, mọi phép kiểm đã xanh — rồi mới soát, và
tìm ra hai thứ này.

### ① 500 gọi được **mà không cần biết khoá**

```
   Authorization: Bearer <mot ky tu ngoai ASCII>
        |
        +-> secrets.compare_digest(str, str)
              TypeError: comparing strings with non-ASCII
              characters is not supported
                    |
                    +-> MOI endpoint hong, khong phai 401
```

Người gọi **điều khiển được vế trái** của phép so, nên không cần biết khoá vẫn làm hỏng
được máy chủ. Sửa: so trên `bytes`.

**Kiểm ngược đã làm** — gỡ bản sửa ra thì phép kiểm không chỉ báo hỏng, nó **đứt cả kết
nối**. Một phép kiểm không thể kêu còn tệ hơn không có, nên phải chứng minh nó kêu được.

### ② `?api=` biến thành đường rò khoá — do **chính change này** mở ra

```
   TRUOC: ?api=http://may-khac  ->  doi CHO DOC DU LIEU
   SAU:   ?api=http://host-la   ->  doi CHO GUI BI MAT

   ai gui duoc mot link la lay duoc khoa cua nguoi bam vao,
   khong canh bao nao — vi day van la mot tinh nang co that
```

`?api=` vốn là tính năng có thật, đã tồn tại từ lâu. Nó vô hại **cho tới ngày trình duyệt
bắt đầu giữ một bí mật**. Đây là loại lỗi không nằm trong file nào bị sửa — nó nằm ở chỗ
hai thứ vốn an toàn riêng lẻ gặp nhau.

Sửa: cất khoá **theo từng địa chỉ backend** (`tokenledger.key:<base>`). Địa chỉ lạ đơn giản
là không có khoá nào, người dùng phải tự gõ — tức phải cố ý. Và nó đúng hơn về bản chất:
hai máy chủ khác nhau vốn là hai khoá khác nhau.

**Không phép kiểm nào bị nới lỏng.** Cả hai phát hiện đều được thêm phép kiểm mới, không
phải thêm dung sai.

---

## 5. Bảy lỗi trong **chính công cụ đo**

Mỗi cái đều suýt tạo ra một kết luận sai. Ghi lại vì cùng loại bẫy sẽ quay lại:

| Đo bằng gì | Nó nói dối thế nào |
|---|---|
| `grep` đếm `Depends` | Báo 2 endpoint **không có khoá** — regex `[^)]*` dừng ở dấu `)` của `Query(...)`. Đếm lại bằng **bảng route của FastAPI**: 8/8 |
| Khoá thử `khoá-có-dấu-á` | Chứa `ấ` **ngoài latin-1** → sập chính `urllib`, request không bao giờ rời máy |
| Chuyển pha giữa các máy chủ | Không đợi cổng đóng → máy chủ sót lại trả lời thay, và pha "thiếu khoá" báo *"máy chủ vẫn chạy"* |
| `dict(r.headers)` | Tra `WWW-Authenticate` phân biệt hoa thường |
| Pha chế độ mở | `not song or ...` khiến *"máy chủ không lên được"* **lọt qua như đạt** |
| Cắt khối HTML | Mốc `key-gate-hint` bắt trúng **CSS** đứng trước HTML → lát cắt rỗng |
| `grep "^. (pass\|fail)"` | Hụt vì `ℹ` là ký tự nhiều byte — trông như test không chạy |

> Bài học chung: **công cụ đo cũng là code, và nó không được ai kiểm.** Ba trong bảy lỗi
> trên sẽ tạo ra "phát hiện" về những thứ chưa từng xảy ra.

---

## 6. Đang ở đâu

### Nghiệm thu

```
   tools/soat_khoa_api.py    24 | 24 dat | 0 hong    uvicorn that, KHONG can Docker
   check_api.py              18 | 18 dat | 0 hong    16 cu + 2 moi
   soat truoc/sau            12 | 12 dat | 0 hong
   CORS preflight             8 |  8 dat | 0 hong
   test JS               6 + 11 |  0 fail            7 -> 11
   audit_db.py               36 | 31 dat | 5 luu y | 0 hong
```

**Một công cụ mới trong repo:** `tools/soat_khoa_api.py` — tự dựng máy chủ ở 5 cấu hình rồi
tự tắt, **chạy được ngay sau `git clone`**, không cần Docker hay database. Nó bắt được thứ
`check_api.py` không thể thấy: bộ kia gọi một máy chủ **đang** chạy nên vẫn xanh nếu ai đó
lỡ tay gỡ mất phần chặn.

### Một phát hiện ngoài lề, đã tận dụng

Docker CLI không nối được daemon, **nhưng PostgreSQL vẫn sống** — nên phần tưởng phải đợi
đã chạy được hết ngay chiều nay.

### Còn treo

| | |
|---|---|
| **5.4** | Mở Chrome, `Ctrl+Shift+R`, dán khoá. **Chỉ anh làm được** — test JS chạy trên DOM giả nên **bỏ qua CSS hoàn toàn** |
| **Giấy tờ** | Ba chỗ ở mục 2 — nằm trong `.docx`/`.xlsx` nên không ai `git diff` được |
| **`fact_attempt`** | Đã chốt 20/08, chưa có bảng và chưa change nào nhận |
| **`Multi modal AI Invoice`** | Chạy lại thật hay còn tiến trình sót? Chỉ anh trả lời được |
| **D2 · D3** | 0 file test Python (nay đã bớt: `soat_khoa_api.py` chạy không cần gì) · Docker thiếu LiteLLM · Redis · Nginx |
| **Git** | 10 commit trên `Tuan-develop` chưa merge vào `main`; toàn bộ việc hai ngày nay **chưa commit** |

---

## 7. Bốn buổi, mỗi việc một câu

### Sáng 20/08 — chữa ba con số sai trên màn hình

1. Tách `account.kind` thành `service_account` để 6 agent một-người-dùng không bị đếm nhầm vào phần "không biết ai dùng", kéo độ phủ từ 12,4% lên 98,5%.
2. Sửa ô tỷ lệ áp dụng hiện `3/1 · 300%` — một con số không thể có thật — về `0/1`.
3. Đổi cột tiền `0 ₫` của phòng ban rõ ràng có tiêu tiền thành `—`, vì "bằng không" và "không đo được" là hai chuyện.
4. Đo ra rằng **28,2% tiền trên dashboard chưa từng đến từ hoá đơn nào** mà là suy từ bảng giá, và trước hôm đó không ô nào nói.
5. Phát hiện cây phòng ban trong dashboard là một bản **chép tay 108 đơn vị** trong `app.js`, trong khi database có hai cây thật.
6. Đưa 4 cặp phòng ban trùng vào database qua cột `canonical_unit_id` sau khi anh xác nhận từng cặp.
7. Thêm cột `is_report_aggregate` để đánh dấu hai cấp gom, theo hướng anh chọn.
8. Viết hai tài liệu mới: việc cần làm trước API Gateway, và hướng dẫn đồng bộ máy đồng nghiệp.
9. Dựng `tools/doi_chieu_cay_don_vi.py` làm lưới an toàn trước khi thay cây gõ cứng.
10. Sửa **6 khẳng định sai trong chính proposal** của mình sau khi đo lại.

### Chiều 20/08 — bỏ dữ liệu gõ cứng và chốt bốn quyết định

11. Bỏ 108 đơn vị gõ cứng khỏi `app.js`, cây đọc thẳng từ database mà tổng tiền và số hàng cấp 1 không lệch một đồng.
12. Gắn dấu `≈` và phần trăm suy ra vào mọi ô tiền, để người đọc biết ô nào là hoá đơn ô nào là suy.
13. Bỏ email nhân viên khỏi API và siết CORS theo biến môi trường thay vì `*`.
14. Thêm phép kiểm bắt agent khai đã dừng mà vẫn phát sinh dữ liệu.
15. Chốt **A1-1**: một database duy nhất kèm cột `data_era`, và **giữ** `fact_monitoring` vì 583.917 dòng đó không dựng lại được.
16. Chốt **A1-2**: có ghi `fact_attempt`, vì dữ liệu retry không dựng lại được về sau.
17. Chốt **A1-3**: LiteLLM chặn ngân sách $70 mỗi agent, `ref_budget` chỉ là bản sao chỉ-đọc.
18. Chốt **A2**: database đúng cả hai project ID, tài liệu `.docx` mới là bên sai.
19. Chốt **A3**: agent tự giải mã JWT rồi gửi username lên Gateway, và **bỏ** việc gửi phòng ban.
20. Rút lại nhận định "`dim_function` đã chết" sau khi đo thấy 8.330/8.330 dòng đều có mã chức năng.
21. Bắt được công cụ đo của chính mình dính bẫy `cached` và dán nhãn "chưa nối billing" cho 7 agent đã nối.

### Sáng 21/08 — mở đường cho nguồn thứ tư

22. Đăng nhập cả hai app rồi giải mã JWT, phát hiện **Ralli dùng claim `sub` còn Hợp Đồng dùng `username`** — viết gọn thành "lấy `sub`" là Hợp Đồng gửi lên một chuỗi không có trong bảng `account`.
23. Phát hiện claim `unit_id` của Hợp Đồng **tồn tại nhưng rỗng**, tức quyết định tra `account.unit_id` hôm trước đã tránh đúng một cái bẫy đang nằm sẵn.
24. Đo hai đầu độc lập ra cùng hình dạng (814 dạng có dấu chấm, 0 ObjectId), chứng minh dòng Gateway nối thẳng vào `account_id` đang có.
25. Chạy diễn tập **trước khi sửa** và thấy dashboard đứng im trước 4 triệu token — dữ liệu nằm trong database mà vô hình, trượt 8/8.
26. Thêm bảng `ref_source(source, knows_user, has_invoice_cost, era, note)` để nguồn tự khai năng lực thay cho một chuỗi mang nghĩa ngầm.
27. Cho `usage_resolved` nhận nguồn thứ tư với Gateway đứng **đầu** thứ tự ưu tiên, trước cả hoá đơn.
28. Đổi tên 6 tài khoản dịch vụ sang `svc.<code>` — chính chuỗi mà 6 agent sẽ gửi lên ngày Gateway chạy.
29. Nhận ra `has_cost` cho gateway phải là **FALSE** vì LiteLLM tự nhân từ bảng giá, và đổi tên cột thành `has_invoice_cost` để không ai đọc nhầm.
30. Bỏ một phép kiểm **không thể kêu** (khoá ngoại đã chặn từ lúc ghi) và thay bằng một dòng trong `FOREIGN_KEYS`.
31. Bắt được kịch bản diễn tập của chính mình **tự chép lại câu SQL của `store.py`** và đang đo bằng đúng logic vừa bị bỏ.
32. Soạn hai proposal OpenSpec, làm trọn cái thứ nhất 40/40, giữ bất biến 867.657.110 token không lệch một token.

### Chiều 21/08 — bịt lỗ hổng cuối, rồi soát lại chính nó

33. Đọc trọn `.docx` và cả 3 sheet `.xlsx` lần đầu, tìm ra ba chỗ giấy tờ đã lệch khỏi hệ thống mà không ai `git diff` được.
34. Phát hiện quyết định "có ghi `fact_attempt`" đang treo giữa hai chỗ: đã chốt nhưng chưa vào lịch của ai.
35. Gắn `Depends(nguoi_goi)` lên cả 8 endpoint, đếm lại bằng **bảng route của FastAPI** sau khi bản `grep` báo nhầm 2 chỗ.
36. Làm `nguoi_goi()` trả về một `Principal` thay vì `True`, để ngày lên JWT chỉ phải sửa một hàm.
37. Bắt máy chủ **từ chối khởi động** khi thiếu `DASHBOARD_KEY`, và chứng minh trên uvicorn thật ở ba biến thể.
38. Thêm `/healthz` làm điểm thăm dò duy nhất không khoá, vì spec cấm dùng `/api/health` cho việc đó.
39. Phát hiện **không file Python nào của backend đọc `.env`**, nên thông báo lỗi bảo đồng nghiệp dán khoá vào `.env` là một lời hướng dẫn sai.
40. Thêm ô nhập khoá vào dashboard với ba trạng thái nói ba câu khác nhau: chưa nhập · khoá sai · chưa bật backend.
41. Sửa 4 kịch bản test JS đang **trượt âm thầm** vì `localStorage` giả rỗng khiến chúng dừng ở ô nhập khoá.
42. Tìm ra `secrets.compare_digest` ném `TypeError` với ký tự ngoài ASCII — **một đường sập gọi được mà không cần biết khoá**.
43. Tìm ra `?api=` đã biến thành đường rò khoá, và sửa bằng cách cất khoá theo từng địa chỉ backend.
44. Kiểm ngược cả hai bản sửa bằng cách gỡ chúng ra và xác nhận phép kiểm thật sự kêu.
45. Sửa **bảy lỗi trong chính công cụ đo**, ba trong số đó sẽ tạo ra "phát hiện" về những thứ chưa từng xảy ra.
46. Đưa `tools/soat_khoa_api.py` vào repo — 24 phép kiểm chạy được ngay sau `git clone`, không cần Docker hay database.
47. Đo trước/sau trên cùng một máy chủ và xác nhận change không đổi **một con số nào**: 937 dòng danh bạ, 867.657.110 token, $291,985601.
