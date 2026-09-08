> **Tên lỗi dùng xuyên suốt:** *lượt hỏng không phải lượt miễn phí* — định danh mã nguồn
> `failed_is_not_free`. Định nghĩa ở `design.md` mục ⑥, chép nguyên văn khi cần trích.

## 1. Chốt mốc trước khi đụng vào gì

- [x] 1.1 Chạy `scripts/audit_db.py` và ghi lại con số, mốc hiện tại là **73 phép / 66 đạt / 7 lưu ý / 0 hỏng**
- [x] 1.2 Chạy `backend/check_api.py` và ghi lại, mốc hiện tại là **31 / 31 / 0 / 0**
- [x] 1.3 Ghi 4 khoá mốc của `usage_resolved` (số dòng · token · calls · tiền) ra `var/` để đối chiếu ở nhóm 7 — change này MUST NOT làm đổi một con số nào trong đó
- [x] 1.4 Ghi mốc ngày 31/08 để tái tạo được: `fact_call` gateway **41 dòng** (38 thành công 45.187 token + 3 hỏng 14 token), `fact_usage_daily` gateway **38 calls / 45.187 token**
- [x] 1.5 Ghi mốc phía nhà cung cấp: **41 request tất cả `response_code=200`**, token vào **47.613**, token ra **3.922**, model `gemini-3.5-flash-lite`, project `project-e62bad30-a591-407b-ba7`, tài khoản `dinhthinhan18111971@gmail.com`
- [x] 1.6 Đo còn bao nhiêu ngày Monitoring giữ được 31/08 — kéo sớm hay muộn phụ thuộc con số này, và cửa sổ đã trượt 196→112 ngày trong một tuần

## 2. Migration: bảng số của nhà cung cấp

- [x] 2.1 Viết `db/migrations/sql/011_so_nha_cung_cap.sql` dựng `fact_provider_daily`, khoá `(day, provider_project, raw_model)` — **không** dùng `model_id` làm khoá vì nó phải NULL được khi chưa ánh xạ, mà cột NULL không làm khoá chính được
- [x] 2.2 Viết `db/migrations/versions/011_so_nha_cung_cap.py`, `downgrade()` ném `NotImplementedError` như **10** migration trước (đo 04/09: `alembic head` = `010_latency_resolved`)
- [x] 2.3 Ghi vào chú thích bảng: `usage_resolved` **KHÔNG** đọc bảng này; nó là ý kiến thứ hai để đối chiếu, không phải nguồn thứ năm để cộng
- [x] 2.4 `provider_project` là mã project dạng text, **không** có khoá ngoại tới `dim_agent` — project của Gateway không thuộc agent nào, và nhét nó vào `dim_agent` sẽ sinh một agent giả hiện lên dashboard
- [x] 2.5 Chạy migration, xác nhận `alembic head` = 011 và 10 bảng fact cũ không đổi một dòng nào

## 3. Mở đường kéo tới tài khoản thứ hai

- [x] 3.1 Thêm `--account` cho `scripts/pull_monitoring.py`; bỏ trống thì dùng tài khoản đang hoạt động của `gcloud`, đúng hành vi hiện tại
- [x] 3.2 Tài khoản được chỉ định mà chưa có khoá truy cập thì DỪNG và nói rõ thiếu tài khoản nào — MUST NOT lặng lẽ lùi về tài khoản mặc định
- [x] 3.3 Đưa tài khoản vào tên thư mục kết quả, vì hai tài khoản kéo cùng ngày cùng độ mịn sẽ ghi đè nhau
- [x] 3.4 Chạy không tham số, xác nhận vẫn kéo đúng 7 project sản xuất và tên thư mục cũ không vỡ
- [x] 3.5 Chạy với `--account dinhthinhan18111971@gmail.com --projects project-e62bad30-a591-407b-ba7`, xác nhận có file kết quả khác rỗng

## 4. Bộ nạp số nhà cung cấp

- [x] 4.1 Viết `db/load_provider.py` nạp từ thư mục kéo vào `fact_provider_daily`
- [x] 4.2 Token ra lấy từ `generate_content_usage_output_token_count`
- [x] 4.3 Token vào lấy từ nhánh `...PerDay-FreeTier` của `quota/generate_content_free_tier_input_token_count/usage`
- [x] 4.4 **Bẫy đã đo được 04/09:** phép đo token vào trả về HAI chuỗi mang cùng con số, tách theo `limit_name` (`...PerDay...` và `...PerMinute...`, cả hai = 47.613). Cộng gộp là nhân đôi — đúng cái đã làm phép đo đầu tiên ra "lệch 2,19 lần"
- [x] 4.5 Bộ nạp SO hai nhánh và DỪNG nếu chúng khác nhau — MUST NOT tự chọn một bên. "Hai nhánh luôn bằng nhau" là giả định về hành vi của Google, phải kiểm mỗi lần nạp
- [x] 4.6 Xác nhận điểm dữ liệu là **mức tăng từng giờ**, không phải luỹ kế — đã kiểm 04/09 (dãy 20 · 267 · 23.577 · 5.895 · 5.875 · 11.979 không đơn điệu tăng). Nếu Google đổi sang luỹ kế thì cộng dồn sẽ sai, nên bộ nạp phải phát hiện dãy đơn điệu tăng và cảnh báo
- [x] 4.7 Quy giờ về ngày theo giờ VN, giữ đúng quy ước đang dùng ở 4 nguồn kia
- [x] 4.8 Nạp ngày 31/08 và đối chiếu với mốc 1.5: phải ra đúng 41 · 47.613 · 3.922
- [x] 4.9 Thêm bước vào `scripts/rebuild_db.py` (đang 10 bước) và xác nhận số bước in ra khớp số bước thật
- [x] 4.10 **Phu thuoc phat sinh:** `gemini-3.5-flash-lite` va `gemini-3.6-flash` chua co bi danh cho nguon `monitoring` (chi co cho nguon `gateway`, duoi ten co tien to `gemini/`). Da them 2 dong vao `db/02_catalog.sql` va vao database dang chay. Khong co chung thi `model_id` de NULL va bo nap bao thieu — no KHONG im lang, nhung van la mot lo hong doc so.

## 5. Phép kiểm

- [x] 5.1 Thêm nhóm phép kiểm mới vào `scripts/audit_db.py`, so `fact_call` với `fact_provider_daily` theo ngày
- [x] 5.2 So trên **cả ba trục**: số lượt, token vào, token ra — khớp một trục không đủ để kết luận
- [x] 5.3 So ở mức NGÀY, không mức giờ. Nhà cung cấp gắn nhãn ô theo thời điểm kết thúc, sổ Gateway ghi theo thời điểm bắt đầu; đo được 04/09 là giờ 01h lệch −12 còn giờ 02h lệch +5.864, một phần chỉ là ranh giới ô
- [x] 5.4 HỎNG khi `fact_call` khai nhiều hơn nhà cung cấp ở bất kỳ trục nào — chiều này bất khả, không cần ngưỡng
- [x] 5.5 LƯU Ý kèm con số khi nhà cung cấp nhiều hơn: in chênh lệch tuyệt đối và tỷ lệ. MUST NOT báo hỏng — chiều này là kỳ vọng, báo hỏng thì phép kiểm đỏ vĩnh viễn rồi bị bỏ qua
- [x] 5.6 **KHÔNG** đặt ngưỡng phần trăm cho chiều thiếu hụt. Ta đã biết kết quả 12,21% nên đặt ngưỡng bây giờ là chọn số vừa khít với đáp án — trái kỷ luật "ban hành ngưỡng trước kỳ đo" của `gateway-cache-reconciliation`
- [x] 5.7 0 ngày giao nhau thì báo CHƯA KIỂM ĐƯỢC kèm khoảng ngày của cả hai sổ, dùng `Audit.check_tren` đã có
- [x] 5.8 Có ngày giao nhau thì in số ngày đã đối chiếu làm mẫu số của kết luận
- [x] 5.9 Sửa báo cáo của `db/load_gateway.py`: in số lượt hỏng **kèm tổng token sổ ghi cho chúng**, và nói rõ đó là *điều sổ khai*, không phải *điều đã tiêu*
- [x] 5.10 Tái tạo lỗi để nghiệm thu phép kiểm 5.4: dựng một trường hợp `fact_call` nhiều hơn nhà cung cấp và xác nhận nó HỎNG. Dùng dữ liệu tạm rồi hoàn tác, **không** sửa dữ liệu thật

## 6. Bản ghi bộ nạp đánh rơi — phát hiện lúc soát artifact 04/09

> **KẾT QUẢ 05/09** — số dòng bị bỏ là **6, không phải 3**, và nguyên nhân đã
> **chứng minh được** chứ không còn là nghi vấn. Chi tiết ở từng ô dưới.

- [x] 6.1 Tái tạo: đo trên TOÀN sổ chứ không riêng 31/08, ra **6 dòng** có trong
  `LiteLLM_SpendLogs` mà không có trong `fact_call`, mang **760 token** —
  `3GWSavLjDcrp2roPvLj7iAY` (29/08, thành công, 17), `lG-UarHhIYXmosUPv4ihmQ8`
  (31/08, **thành công**, 25), `372eb089-…` (31/08, hỏng, 0), `6ff4a85c-…`
  (31/08, hỏng, 14), `GsaVavubFOD21e8PnvHx2QE` (01/09, thành công, 352), và
  `GsaVavubFOD21e8PnvHx2QE_cache_hit…` (01/09, 352). Con số 3 dòng / 39 token
  trong đề xuất là của riêng ngày 31/08
- [x] 6.2 **Nguyên nhân thật, đã chứng minh:** cả 5 dòng đầu đều **không có tag
  nào khớp `dim_agent.code`**. Nhận định cũ "chỉ 1 trong 3 dòng thiếu tag" là
  SAI — nó đếm *mọi* tag, kể cả `User-Agent:` do LiteLLM tự thêm, trong khi
  `resolve_agent` chỉ tính tag khớp mã agent. Hai nghi can cũ đều **bị bác bỏ**:
  chạy `--full` rút hẳn mốc nước vẫn `inserted 0`, nên không phải mốc nước, cũng
  không phải ranh giới ngày
- [x] 6.3 `db/load_gateway.py` nay in số dòng bỏ **kèm tổng token và mã từng
  dòng, tách theo lý do**. Nói thêm cho đúng: nó đã không hề "rớt trong im lặng"
  — dòng `dropped: no tag %d` và `skipped across the ledger` đã có sẵn; cái
  thiếu là **token theo từng lý do**, và đó là phần được thêm
- [x] 6.4 Phép kiểm mới — nhóm J trong `audit_db.py`, **tự tính lại từ sổ nguồn
  bằng SQL của riêng nó** thay vì tin lời bộ nạp. HỎNG khi một dòng lẽ ra nạp
  được mà vắng mặt, **và cả chiều ngược lại**: dòng có trong `fact_call` mà sổ
  nguồn không còn. Không đòi `COUNT(*)` hai vế bằng nhau — xem ô 6.5 để biết vì
  sao đòi thế là đặt một phép kiểm đỏ vĩnh viễn
- [x] 6.5 Không chèn tay dòng nào. Chạy `--full` thật: `inserted 0` — **cả 3
  dòng vẫn không vào**, đúng như ô này dự phòng. Đó là **phát hiện tiếp theo**:
  `fact_call.agent_id` là `NOT NULL`, nên lưu lượng không quy được về agent nào
  **không thể lưu**, dù nó đã tiêu token thật. Cùng một hình dạng lỗi với
  `failed_is_not_free`, chỉ khác trục — và sửa nó cần một agent "không quy được"
  hoặc `agent_id` cho phép NULL, cả hai đều **ngoài phạm vi change này** (ô 8.6
  chốt `dim_agent` phải giữ đúng 8 dòng)

### Phát hiện phụ, không có trong kế hoạch: bản sao của cú cache hit

LiteLLM ghi **thêm** một dòng cho cú cache hit, mang chính `request_id` của dòng
gốc cộng hậu tố `_cache_hit<epoch>`, **lặp lại nguyên token**. Toàn sổ có đúng 1
dòng như vậy (352 token) và dòng gốc tồn tại với đúng 352 token; nhà cung cấp xác
nhận độc lập ngày 01/09 họ phục vụ **1 lượt**. Hôm nay nó rớt vì *không có tag
định danh* — một lý do **chẳng liên quan**. Ngày nào khâu định danh được nới ra
để cứu 5 dòng kia, bản sao sẽ theo cùng cửa đó mà vào và **đếm đôi 352 token**,
không phép kiểm nào hiện có bắt được. Nên `load_gateway.py` nay loại nó **tường
minh, có tên**, trước mọi bước khác.

## 7. Tài liệu

- [x] 7.1 Thêm `fact_provider_daily` vào `docs/reference/tu-dien-database.md`, nói thẳng `usage_resolved` không đọc nó
- [x] 7.2 Viết `docs/reference/luot-hong-khong-mien-phi-04-09.md`: bằng chứng, cách tái tạo phép đo, và cả hai lỗi tôi đã mắc trong lúc đo (cộng trùng hai nhánh hạn mức; `gcloud` cắt project ID ở 30 ký tự làm sót 3 dự án)
- [x] 7.3 Ghi vào tài liệu: khoá của Gateway là **free tier**, nên lưu lượng này sẽ không bao giờ lên hoá đơn — đường đối chiếu bắt buộc qua Monitoring, không qua `fact_billing_daily`
- [x] 7.4 Ghi rõ mẫu đo rất nhỏ: **5 dòng hỏng trên toàn sổ, tất cả cùng một ngày**. Con số **12,21%** là của riêng ngày 31/08 và của riêng nguyên nhân này, MUST NOT được nói trống như một tỷ lệ chung
- [x] 7.5 Cập nhật Master Plan STT 7 dòng 20 và STT 4 dòng 11, sao lưu bản cũ vào `docs/reference/ban-luu/` theo ngày
- [x] 7.6 Ghi câu hỏi còn treo: hai lượt bị ghi 0 token là một request thử lại hai lần hay hai request khác nhau — `LiteLLM_SpendLogs` không có trường nối lượt thử lại về lượt gốc

## 8. Nghiệm thu

- [x] 8.1 `usage_resolved` khớp 4/4 khoá mốc của 1.3 — change này MUST NOT đụng một dòng dữ liệu lưu lượng nào
- [x] 8.2 `scripts/audit_db.py` chạy sạch, số phép tăng đúng bằng số phép thêm vào, 0 hỏng
- [x] 8.3 `backend/check_api.py` giữ nguyên 31/31 — change này không đụng tầng API
- [x] 8.4 Chạy audit hai lần liên tiếp, mọi con số không đổi
- [x] 8.5 Kiểm `git status` trên `web/`: không file nào bị đường ống sửa
- [x] 8.6 Xác nhận `dim_agent` vẫn đúng 8 dòng — không có agent giả nào sinh ra từ project của Gateway
- [x] 8.7 Chạy `tools/scan_secrets.py`, rc = 0 — phần này đụng tới hai tài khoản Google
- [x] 8.8 Bind IP của `web` đang là `192.168.20.111` — **không cần trả lại**, change này không đụng tới nó (chính vì thế container `web` không lên được trên máy dev, và đó là trạng thái đúng để push)
