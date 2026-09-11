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

- [x] 4.1 **XONG 12/09. Đổi tên `thinking_tokens` → `output_tokens_thinking_on`, và viết lại
      docstring.** Ba chỗ dùng tên đó, không hơn: bí danh SQL và khoá dict ở `store.py`, chỗ đọc
      ở `api.js:199`.
      **KHÔNG đụng database, KHÔNG chạy lại luồng nạp.** Tra `information_schema` thì không bảng
      nào có cột `thinking_tokens` — chỉ có `thinking_enabled`, mà cột đó tên đúng. Đây là bí
      danh tính lúc truy vấn, nên đổi tên là đổi chữ trong câu SQL, dữ liệu không liên quan.
      Bảng ghi vào docstring để người sau khỏi đo lại:

      | nhãn trên lượt gọi | dòng | token ra |
      |---|---|---|
      | bật suy nghĩ | 11.440 | 47.913.327 |
      | tắt suy nghĩ | 3.589 | 4.647.033 |
      | không có nhãn | 6 | 0 |
      | **tổng token ra** | **15.035** | **52.560.360** |

      Cộng khít, không nhóm nào rơi ra ngoài. Cột này là 91,2% token ra và nằm SẴN trong token
      ra. Cũng ghi rõ `monitoring_tokens` là tổng CẢ vào lẫn ra (496,9 triệu), nên chia cột trên
      cho nó ra một con số không nghĩa lý gì.
      **Và sửa một câu SAI trong docstring cũ:** nó viết *"hoá đơn không tách"*. Hoá đơn **có**
      tách, thành hai SKU output cho `gemini 2.5 flash`, một mang chữ `non-thinking`. Đã bác bỏ
      bằng phép đo 11/09, xem ô 3.2.
      Kiểm: gọi thẳng `store.thinking()` trên database thật, 136 dòng, tên cột mới đúng, tổng
      10.609.201. `node --test` 51/51, `pytest` 11 đạt.
- [x] 4.6 **XONG 12/09 — sửa lý do, và KHÔNG dựng lại thẻ.** Chốt bởi anh Tuấn cùng ngày: *"tôi
      muốn coi token suy luận và token output là 1: đều là biến token output"*. Quyết định đó
      đúng và nó **xoá việc chứ không thêm việc** — xem 4.7.
      Lý do cũ ghi trong mã là *"con số luôn bằng 0"*, và nó sai: con số là 47.913.327 trên
      11.440 dòng. Đã thay bằng lý do đúng: token suy luận **không phải một loại token riêng**,
      nên vẽ nó thành một thẻ cạnh thẻ token là mời người xem cộng hai số đã chồng nhau.
      → Nguyên văn ô lúc mở, giữ làm vết: **Tiền đề của việc gỡ thẻ "Token suy luận" nay đã SAI.** `app.js:3525` ghi lý do gỡ là
      *"chưa xác nhận được agent nào thực sự bật suy luận mở rộng, nên con số luôn bằng 0 và chỉ
      gây hiểu nhầm"*. Số không bằng 0: nó là 47.913.327, tức 91,2% token ra, trên 11.440 dòng.
      Trường `A.think` vẫn được `aggregate()` tính nên dựng lại thẻ không phải sửa gì thêm.
      Quyết định dựng lại hay không thuộc về người dùng, không phải việc của change này — nhưng
      cái lý do ghi trong mã thì phải sửa, vì nó đang nói sai về dữ liệu.
      → Nguyên văn ô 4.1 lúc mở, giữ làm vết: Cột `thinking_tokens` ở `store.py:469` **không
      phải** token suy nghĩ, và tên của nó
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
- [x] 4.3 **KHÔNG LÀM, CÓ LÝ DO — và đây là kết cục tốt hơn việc làm nó.** Chốt 12/09: token suy
      luận và token ra là **một biến**. Nên không cần cột `reasoning_tokens` trong `fact_call`,
      và không cần chỗ nào hiển thị nó.
      **Đường quay lại vẫn còn nguyên:** `reasoning_tokens` nằm trong `metadata` của
      `LiteLLM_SpendLogs`, không ai xoá. Ngày nào cần trả lời câu *"tắt suy nghĩ đi thì tiết
      kiệm bao nhiêu"* thì mở lại ô này. Hôm nay chưa ai hỏi.
      → Nguyên văn ô lúc mở, giữ làm vết: Số token suy nghĩ **thật** chưa được lưu ở đâu cả. `load_gateway.py:201` đọc
      `completion_tokens_details.reasoning_tokens` chỉ để suy ra **cờ** boolean, con số thì bỏ.
      Muốn hiện token suy nghĩ trên dashboard thì thêm một cột vào `fact_call`, và trình bày
      kiểu **trong đó** chứ không **cộng thêm** — nó là tập con của token ra.
- [x] 4.4 **ĐÃ ĐỌC KỸ RỒI QUYẾT ĐỊNH KHÔNG SỬA CỘT `day`. Thay bằng một phép kiểm thường trực.**
      **Đính chính trước đã: đây KHÔNG phải phát hiện mới, và tôi đã viết sai chỗ đó.** Docstring
      của `db/build_usage_daily.py` mục (a) đã ghi và **chốt từ 14/08**: *"`day` của nguồn
      'billing' là ngày theo giờ Mỹ, nhưng ta COI LÀ giờ Việt Nam. Tổng cả kỳ vẫn đúng tuyệt đối;
      chỉ CHUỖI THEO NGÀY của riêng nguồn billing là lệch tới 15 giờ."* Tôi đã báo một hạn chế
      có chủ ý thành một lỗ hổng chưa ai biết.
      **Vì sao không sửa được cho đúng:** hoá đơn chỉ có **ngày**, không có giờ. Một ngày Pacific
      trải trên hai ngày VN (10 giờ ngày này, 14 giờ ngày kia), nên không có cách nào chia tổng
      ngày của hoá đơn về hai ngày VN. Dịch cả ngày thì đúng cho 14/24 lưu lượng và **phá mất**
      tính chất *"tổng cả kỳ đúng tuyệt đối"* ở hai đầu kỳ. Đổi một hạn chế đã biết lấy một sai
      số mới không đo được là lỗ.
      **Và ba nguồn KHÔNG cộng vào nhau theo ngày**, nên không có chuyện đếm đôi: `usage_resolved`
      chọn một nguồn cho token theo thứ tự gateway → billing → monitoring → app.
      **Việc đã làm thay:** thêm phép kiểm `_hoa_don_cung_mui_gio_voi_cong_to` vào nhóm I của
      `scripts/audit_db.py`. Nó quy monitoring về ngày Pacific bằng `AT TIME ZONE` hai lần rồi so
      với hoá đơn. Đo 11/09:

      | giả thuyết | cặp | trùng khít | lệch / token |
      |---|---|---|---|
      | quy về Pacific | 397 | 356 (90%) | **0,20%** |
      | để nguyên giờ VN | 365 | 13 (4%) | **81,3%** |

      **Không đặt ngưỡng**, đúng kỷ luật nhóm I: đã biết đáp án là 0,20% thì đặt ngưỡng bây giờ
      là chọn số vừa khít với đáp án. Phép kiểm hỏi một câu nhị phân — quy về Pacific có lệch ít
      hơn để nguyên giờ VN không. Hôm nay chênh 313 lần nên câu hỏi dư sức sống sót dao động dữ
      liệu, và chỉ đỏ khi quan hệ múi giờ thật sự đổi. Bỏ ngày đầu và ngày cuối của monitoring vì
      cửa sổ lưu giữ trượt làm hai ngày biên luôn khuyết.
      `audit_db.py`: **79 phép kiểm, 69 đạt, 10 lưu ý, 0 hỏng.**
- [ ] 4.5 **Chỗ duy nhất múi giờ còn lẫn trên MỘT DÒNG, sinh ra từ 4.4.** `usage_resolved` lấy
      `total_tokens` theo thứ tự gateway → billing → monitoring → app, nhưng `cost_usd` theo thứ
      tự **billing → gateway**. Nên một dòng có cả hai thì **token là cửa sổ giờ VN còn tiền là
      cửa sổ giờ Pacific** — hai khoảng 24 giờ lệch nhau 14 tới 15 giờ, nằm cạnh nhau trên cùng
      một dòng và trông hoàn toàn khớp. Nằm trong hạn chế đã chốt 14/08 nên không phải lỗi mới,
      nhưng đáng gọi tên riêng vì nó không lộ ra như một chuỗi bị dịch. Ảnh hưởng: chỉ số nào
      chia tiền cho token theo NGÀY. Tổng cả kỳ không ảnh hưởng.
- [x] 4.7 **XONG 12/09 — gỡ cả chuỗi `/api/thinking`, vì mô hình một biến làm nó thành thừa.**
      Tra ra trước khi cắt: trường `think` được `aggregate()` cộng dồn rồi **không nơi nào đọc**.
      Mỗi lần mở trang là thêm một request HTTP và một câu SQL quét `fact_monitoring` cho một con
      số không ai thấy.

      | gỡ ở đâu | gỡ cái gì |
      |---|---|
      | `backend/main.py` | endpoint `/api/thinking` |
      | `backend/store.py` | hàm `thinking()` |
      | `backend/check_api.py` | URL trong danh sách endpoint |
      | `web/js/api.js` | `thinkingByKey()`, tham số của `buildState()`, trường `think`, lời gọi fetch |
      | `web/js/app.js` | `think` trong `aggregate()` và phép cộng dồn |

      **Một cái bẫy suýt dính, và nó là phần đáng giá nhất của ô này.** Danh sách `Promise.all`
      được đọc lại bằng **chỉ số** — `r[0]` tới `r[6]`. Bỏ một lời gọi ở giữa làm lệch mọi chỉ số
      phía sau, và kiểu lỗi đó **không ném exception**: nó chỉ đưa bảng `adoption` vào chỗ
      `catalog`. Đã đổi sang đọc theo **tên** ngay tại chỗ nhận, đúng nguyên tắc mà
      `backend/store.py::_rows` đã ghi sẵn cho việc đọc cột — *"đọc theo tên thì thêm cột không
      làm gì hỏng"*. Giờ thêm hay bớt endpoint không còn đụng tới chỗ nào khác.

      Ba chỗ để lại ghi chú tại chỗ thay vì xoá trắng: `store.py` và `main.py` chỗ hàm cũ, và
      `app.js` chỗ thẻ đã gỡ — để người sau không dựng lại vì tưởng bị bỏ quên.

      **Kiểm bằng máy chủ thật**, không suy từ việc đọc mã: dựng uvicorn trên cổng 8077, gọi cả
      bảy đường.

      ```
      200  /api/usage            200  /api/accounts
      200  /api/performance      200  /api/usage-by-account
      200  /api/catalog          404  /api/thinking     <- dung nhu mong doi
      200  /api/adoption
      ```

      `backend/check_api.py` 31/31 đạt · `node --test` 51/51 · `pytest` 11 đạt ·
      `audit_db.py` 79 phép kiểm, 69 đạt, 0 hỏng.
