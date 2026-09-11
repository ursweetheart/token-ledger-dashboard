# Việc

Nhật ký đo: `docs/reference/token-suy-nghi-tren-hoa-don-11-09.md`.

## 1. Soát bảng ánh xạ trước, vì nó rẻ nhất

- [x] 1.1 Liệt kê mọi `sku_id` thuộc `kind = 'output'` trong `dim_metric_alias`, tách hai nhóm: tên có chữ `non-thinking` và tên không có
      → **9 SKU output. 2 có chữ `non-thinking`, 7 không.** Hai SKU có:
      `6EDB-2409-6348` (`gemini 2.5 flash`) và `7133-23F2-04B7` (`gemini 2.5 flash lite`).
      Tổng bảng có 31 SKU hoá đơn: 15 input, 9 output, 7 cached.
- [x] 1.2 Tìm SKU nào tên nhắc tới suy nghĩ mà `kind` **khác** `'output'` — có thì đây là lỗi thật, và đóng được câu hỏi ngay tại đây
      → **0 dòng.** Không có lỗi ở đây. Và một phát hiện quan trọng hơn: **0 SKU nào mang chữ
      `thinking` trơn**, chỉ có `non-thinking`. Sau 240 ngày hoá đơn, không có SKU riêng cho
      phần suy nghĩ — đây thành lập luận mạnh nhất của cả change.
- [x] 1.3 Đối chiếu danh sách SKU đã khai với danh sách SKU thực sự xuất hiện trong `fact_billing_daily`: có SKU nào đã khai mà chưa bao giờ về không
      → **Không. 31/31 SKU đã khai đều có dòng thật**, kéo từ 01/01 tới 29/08.
- [x] 1.4 Đọc `db/load_billing.py` để tự xác nhận bộ nạp dừng hẳn khi gặp SKU lạ. **Đừng tin ghi chú này** — ghi chú là thứ dễ cũ đi nhất
      → **Đã đọc `load_billing.py:85-112`, ghi chú đúng.** SKU không tra ra `kind` thì vào
      `no_kind` rồi `continue`; cuối vòng lặp `if no_model or no_kind or no_agent: raise
      SystemExit(...)`. Không có nhánh nào nạp tiếp trong im lặng. Nhờ vậy kết luận 1.2 còn
      đứng được trong tương lai chứ không chỉ đúng với 240 ngày đã có: SKU suy nghĩ mới xuất
      hiện sẽ **làm bộ nạp chết**.

## 2. Ghép số, chỉ khi việc 1 không tìm ra gì

- [x] 2.1 Dựng phép ghép ở mức `ngày × agent × project × model`, **KHÔNG** ghép chỉ theo ngày
      → Ghép ở mức `ngày × project` cho phép so hai SKU, và `ngày × project × model` cho phép
      so theo model. **Bỏ `agent` là có ý**: `project → agent` là một phép tra một-một trong
      `dim_agent`, nên `ngày × project` đã mịn bằng hoặc mịn hơn `ngày × agent × project`.
      Thêm `agent` vào chỉ làm câu SQL dài ra chứ không tách thêm được nhóm nào.
- [x] 2.2 Chạy trên `gemini-2.5-flash` trước: model này có 8.107 dòng bật suy nghĩ và 128 ngày chung với hoá đơn
      → Chạy trước, và **chính model này cho phép kiểm quyết định**: 56 cặp ngày × project mà
      monitoring không có lượt nào bật suy nghĩ thì **cả 56 cặp** có SKU `911A-8880-A243` bằng
      0, tổng đúng 0. Nên `911A` = token ra của lượt BẬT, `6EDB` = lượt TẮT.
- [x] 2.3 Báo cáo bằng **phân bố** phần lệch, không bằng một con số tổng
      → Báo bằng phân bố theo **project** và theo **model**, cộng 20 ngày mẫu. Và chính phân
      bố đó bác bỏ kết luận sai: tổng cho 122,1% trên nhánh bật suy nghĩ, nghe như "hoá đơn
      đếm thêm phần suy nghĩ", nhưng tách theo project thì lệch **hai chiều**, 62,1% tới
      150,8%. **Chưa làm:** phân vị của tỷ lệ theo ngày. Không làm vì phân bố theo project đã
      đủ để bác kết luận sai, thêm phân vị không đổi câu trả lời.
- [x] 2.4 **MUST NOT** kết luận từ việc hai tổng gần nhau. Xem design ①: lệch 0,5% ở tổng mà **0** ngày nào trùng khít
      → **Giữ, và lần này bẫy nằm ở chiều ngược lại.** Hai tổng **không** gần nhau (122,1%), và
      tôi cũng không kết luận từ chỗ đó. Phép kiểm ở mức ngày cho thấy chỉ 24/285 cặp trùng
      khít, đúng như design cảnh báo. Kết luận cuối dựa vào 1.2, 1.4, đơn giá, và sổ Gateway —
      không dựa vào phép so tổng.
- [x] 2.5 Lệch lớn thì nghi phép ghép trước, nghi dữ liệu sau. Hai nguồn này từng khớp 100,4%
      → **Nghi phép ghép trước, và đúng.** Nhánh **tắt** suy nghĩ khớp 99,6% trên cùng những
      ngày đó, còn `gemini-3-flash` — model luôn bật suy nghĩ — chỉ lệch 101,0%. Nếu 22% là
      phần suy nghĩ thì `gemini-3-flash` phải lệch tương tự. Nó không. Nên 22% là **monitoring
      phủ thiếu theo project**, không phải thiếu token suy nghĩ.

## 3. Kết luận

- [x] 3.1 Trả lời dứt khoát: dashboard có đang bỏ sót token suy nghĩ trên đường hoá đơn không
      → **KHÔNG bỏ sót.** Hoá đơn không tách token suy nghĩ ra khỏi token ra, và dashboard đã
      cộng nó rồi.
- [x] 3.2 Nếu KHÔNG thiếu thì nói rõ vì sao, kèm con số làm bằng chứng
      → Bốn bằng chứng, không bằng lập luận:
      **①** 0 SKU mang chữ `thinking` trơn sau 240 ngày hoá đơn, và bộ nạp sẽ chết nếu SKU lạ
      xuất hiện (ô 1.2 + 1.4).
      **②** Hai SKU output của `gemini 2.5 flash` là hai nhãn bật/tắt, chứng minh 56/56 (ô 2.2).
      Cả hai cùng `kind = 'output'`, và đường hoá đơn cộng theo `kind` chứ không theo `sku_id`,
      nên phần suy nghĩ **đã vào** `to`.
      **③** Đơn giá hai SKU output bằng nhau, `2,499976` và `2,499946` USD trên 1 triệu token,
      đúng con số LiteLLM dùng hôm 10/09. `non-thinking` không phải bậc giá rẻ hơn.
      **④** Sổ Gateway cho bằng chứng trực tiếp `reasoning ⊂ completion`: 46 dòng có
      `reasoning_tokens`, tổng 9.554 trên `completion_tokens` 9.968, **0 dòng** vượt.
- [x] 3.3 Nếu CÓ thiếu thì đo phần thiếu rồi báo, **KHÔNG** tự sửa công thức trong change này
      → **Không áp dụng.** Không thiếu, nên không có phần thiếu để đo. Công thức
      `ti + to + cached` giữ nguyên, không sửa gì.
- [x] 3.4 Ghi kết quả vào `docs/reference/`, rồi đóng ô 2.1 của change `standardize-kpi-card-insights` bằng con số
      → **Xong.** `docs/reference/token-suy-nghi-tren-hoa-don-11-09.md`, 10 mục. Ô 2.1 của
      `standardize-kpi-card-insights` đã đóng, kèm cả bốn con số.

## 4. Ngoài phạm vi ban đầu — hai việc sinh ra từ chính lượt đo này

- [ ] 4.1 Cột `thinking_tokens` ở `store.py:469` **không phải** token suy nghĩ, và tên của nó
      mô tả sai thứ nó đo. `thinking_enabled` là NHÃN trên metric, nên phép cộng đó trả về
      *token ra của lượt có bật suy nghĩ*: **47.913.327 trên tổng 52.560.360 token ra, tức
      91,2%**. Cộng cột này vào output là đếm hai lần 91% token ra. Đổi tên, và ghi rõ cách đọc.
      Một nghi ngờ đã kiểm và **loại**: điều kiện `d.measures = 'token'` phủ cả metric input,
      nhưng metric input **không mang nhãn** này bao giờ (NULL), nên nhánh `CASE WHEN` cho 0
      trên mọi dòng input. Thực tế cột chỉ ăn metric output.
- [x] 4.2 ~~Monitoring phủ thiếu theo project: nhánh bật suy nghĩ lệch 62,1% tới 150,8% so với
      hoá đơn tuỳ project.~~ **SAI, TỰ BẮT VÀ TỰ SỬA TRONG CÙNG NGÀY. Không có phần lệch nào.**
      Ghép `ngày hoá đơn = ngày monitoring + d` cho `d` từ −2 tới 2 thì sai số có **cực tiểu rõ
      rệt ở `d = −1`**: 31,7% so với 96,2% ở `d = 0`. Truy ra:
      `scripts/merge_billing.py:251` lấy `"day": r["Date"]` **nguyên văn** từ file xuất Cloud
      Billing, tức giờ **US/Pacific**, còn `build_usage_daily.load_monitoring()` ghi rõ trong
      docstring *"Ngày giờ Việt Nam thật"*. Tháng 4–8 là PDT nên lệch 14 giờ, tức **Pacific
      00:00 = VN 14:00**.
      Xếp lại monitoring theo ngày Pacific rồi ghép: **238/272 cặp ngày × project trùng khít tới
      từng con số, và cả 7 project đều ra 100,00%**. `crm-500509` 40/40, `ai-chatbot-contract`
      10/10, `tools-quizz` 5/5. Project nào là pipeline theo lịch thì khớp tuyệt đối; project web
      có lưu lượng rải cả ngày thì bị biên 14:00 cắt đôi nên ngày lẻ xê dịch mà tổng vẫn đúng.
      **Bài học phương pháp:** tôi đã báo một "lỗi dữ liệu" mà thực ra là lỗi phép ghép của chính
      tôi — đúng cái ô 2.5 dặn *"lệch lớn thì nghi phép ghép trước"*. Đọc rồi vẫn sa vào.
      Xem mục 11 của nhật ký.
- [ ] 4.3 Số token suy nghĩ **thật** chưa được lưu ở đâu cả. `load_gateway.py:201` đọc
      `completion_tokens_details.reasoning_tokens` chỉ để suy ra **cờ** boolean, con số thì bỏ.
      Muốn hiện token suy nghĩ trên dashboard thì thêm một cột vào `fact_call`, và trình bày
      kiểu **trong đó** chứ không **cộng thêm** — nó là tập con của token ra.
- [ ] 4.4 **Việc thật sinh ra từ 4.2, và nó ở trong bảng của dashboard chứ không ở câu SQL của
      tôi.** `fact_usage_daily.day` nhận dòng từ bốn bộ nạp: `load_billing()` ghi ngày
      **US/Pacific**, còn `load_monitoring()`, `load_app()`, `load_gateway()` ghi ngày **Việt
      Nam**. Bốn nguồn, một cột, một nguồn khác múi giờ. Nên mọi biểu đồ theo ngày có trộn tiền
      hoá đơn đều **lệch một ngày** ở vế hoá đơn: tổng cả kỳ đúng, ngày lẻ sai.
      **Phải quy bằng `America/Los_Angeles`, KHÔNG bù một hằng số.** Lệch là 14 giờ trong PDT
      nhưng 15 giờ trong PST, nên bù cứng `−1 ngày` hay `−14 giờ` sẽ sai bốn tháng mỗi năm.
