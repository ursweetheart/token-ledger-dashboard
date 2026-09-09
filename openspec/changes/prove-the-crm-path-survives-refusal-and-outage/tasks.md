## 0. Chặn — phải xong trước

- [ ] 0.1 Change `route-the-crm-agent-through-the-gateway` đã apply xong. Không có đường thông thì không có gì để ép hỏng
- [ ] 0.2 Chốt **trần chi tiêu** cho batch cỡ production. Đây là credit của người dùng, không phải tiền công ty — phải hỏi, không tự quyết
- [ ] 0.3 **Đo trước** xem `num_retries: 3` của Gateway có che 429 khỏi CRM hay không. Nếu Gateway tự xoay xong thì CRM không bao giờ thấy 429, và cả nhóm 2 sẽ đo một thứ khác. MUST NOT giả định
- [x] 0.4 **Đã xác nhận bằng đo, 10/09 — tuyến CRM KHÔNG có fallback.** Lộ ra khi làm task 4.1 của change trước. Cấu hình chỉ khai đúng một dòng fallback, và nó **không** thuộc tuyến CRM:

  ```yaml
  fallbacks:
    - gemini-flash: ["gemini-flash-preview"]
  ```

  Và LiteLLM tự nói ra lúc chạy, chứ không phải tôi suy từ file: `No fallback model group found for original model_group=gemini-2.5-flash. Fallbacks=[{'gemini-flash': ['gemini-flash-preview']}]`. Nên khi hết hạn mức, tuyến CRM sẽ **trả 429** chứ không lặng lẽ đổi tuyến, và phép đo 429 của nhóm 2 đo đúng đường cần đo. Nguyên văn: Xác nhận tuyến CRM **không** khai `fallbacks`. Có fallback thì hết hạn mức sẽ đổi tuyến chứ không trả 429, và phép đo 429 đo một đường khác hẳn

## 1. Harness thành công cụ dùng lại được

- [ ] 1.1 Đặt trong `tools/`, **không** trong `db/` hay `scripts/` — hai chỗ đó là đường nạp dữ liệu thật
- [ ] 1.2 Nhận tham số: agent nào, khoá nào, model nào, bao nhiêu lượt, đường nào (gateway / trực tiếp). MUST NOT nhét CRM vào code
- [ ] 1.3 Ghi ra từng lượt: mốc thời gian bắt đầu, mã trả về, độ trễ, token vào/ra, `request_id`. Đủ để tính lại mọi con số sau này mà không phải chạy lại
- [ ] 1.4 MUST NOT tải/ghi SharePoint, MUST NOT gửi email, MUST NOT ghi Excel
- [ ] 1.5 Chạy thử với 2 lượt để bắt lỗi công cụ trước khi tin số nó in ra

## 2. Ép 429 và xem CRM lùi lịch nhánh nào

- [ ] 2.1 Ghi mốc nền: nhịp thực đạt, độ trễ trung vị, số dòng trong sổ
- [ ] 2.2 Hạ `rpm` của tuyến CRM xuống 1. Ép ở **cửa Gateway từ chối**, không bắn dồn — `wait_for_rate_limit()` khoá toàn cục nên bắn dồn phải đi vòng qua chính cơ chế đang muốn thử, tức là đo một đường production không bao giờ đi
- [ ] 2.3 Chạy harness, **đo khoảng thời gian giữa các lần thử lại**
- [ ] 2.4 Phân loại theo **số khoảng** trước, rồi mới theo độ dài. Lùi lịch sự: **3 khoảng** `10, 20, 30`s (+ ≤2s ngẫu nhiên). Lùi chung: **2 khoảng** `4, 8`s — lần thử thứ 3 ném lỗi ngay không ngủ, vì có chốt `if attempt < max_retry`. Số khoảng phân biệt mạnh hơn độ dài, và phân biệt được **mà không cần đọc log của CRM**
- [ ] 2.5 Đo được 2 khoảng `4` và `8`s → `429` **không tới được nhánh đúng**. Đó là **phát hiện thật**, ghi lại; MUST NOT sửa ngay rồi đo lại rồi báo là đạt
- [ ] 2.6 **Trả `rpm` về 15**, và **xác nhận bằng phép đo** là đã trả — gọi một lượt và kiểm nó không bị từ chối. MUST NOT chỉ ghi "đã trả"
- [ ] 2.7 Ghi lại: cả hai nhánh đều dẫn tới "cuối cùng vẫn xong", nên kết quả **không nói được** nhánh nào chạy. Đây là lý do 2.4 phải đo thời gian

## 3. Diễn tập mất Gateway giữa batch

- [ ] 3.1 Chạy harness với đủ số lượt để nó còn đang chạy khi ta can thiệp. Timeout mỗi lượt phải **trên 60 giây**: nhánh 429 ngủ 10+20+30 rồi mới bỏ, nên timeout ngắn hơn sẽ bị đọc thành treo
- [ ] 3.2 **Dừng `gateway-lb`** giữa lúc chạy — mô phỏng đúng thứ CRM thấy: không kết nối được. MUST NOT dừng LiteLLM: nginx còn sống sẽ trả 502, một tình huống khác và nhẹ hơn
- [ ] 3.3 Ghi lại CRM làm gì: lỗi gì, thử lại mấy lần, có bỏ dở giữa batch hay không
- [ ] 3.4 Bật lại `gateway-lb`, chạy lại, rồi đối chiếu **hai** điều tách nhau:
  - [ ] 3.4.1 **không mất dòng** — mọi dòng hoặc vào sổ, hoặc quay lại hàng chờ
  - [ ] 3.4.2 **không đếm đôi** — mỗi dòng CRM có đúng một bản ghi; token và tiền trong sổ không phồng lên
- [ ] 3.5 Nêu hai điều đó **tách nhau** trong báo cáo. Gộp thành "chạy lại được" là che mất chuyện đếm đôi — mà đếm đôi tệ hơn: kết quả phân loại vẫn trông đúng trong khi số tiền thì sai
- [ ] 3.6 Đối chiếu với điểm lưu thật: `save_history_db_atomic` ghi `classified_history_db.json` sau **mỗi** batch (`pipeline.py:688`; còn 3 chỗ nữa ở 488, 538, 718 nằm ngoài vòng batch). Lưu ý `config.CKPT_JSON` (`llm_fills_checkpoint.json`) **được khai mà không nơi nào dùng** — đừng kiểm file đó, nó không phải nơi giữ trạng thái
- [ ] 3.7 Ghi rõ: diễn tập này đi qua harness nên không đụng SharePoint. Nếu sau này ai diễn tập bằng pipeline thật thì rủi ro để lại trạng thái nửa vời trên SharePoint là **có thật**

## 4. Batch cỡ production

- [ ] 4.1 Chạy trong **trần chi tiêu đã chốt ở 0.2**. Dừng khi tới trần, không chạy tiếp rồi xin lỗi sau
- [ ] 4.2 Số lượt lấy theo tải thật đã đo: ngày cao nhất **502 lượt**, giờ cao nhất **365 lượt**
- [ ] 4.3 Đo: nhịp thực đạt (lượt/phút), số 429, độ trễ trung vị và phân vị 95, token, chi phí
- [ ] 4.4 Đối chiếu nhịp thực đạt với hai con số đã biết: `7,3` (tác giả khuyến nghị) và `16` (mặc định trong code). Con số nào đúng thì nói lên `.env` production đang đặt gì
- [ ] 4.5 Kiểm **mọi** lượt gọi quy được về `agent_id = 7`. Một dòng vào `bo_khong_tag` là một dòng mất khỏi chiều agent
- [ ] 4.6 Chạy `scripts/audit_db.py`, nhóm J phải ĐẠT
- [ ] 4.7 Ghi lại chi phí thực tế và đối chiếu với trần

## 5. Gateway làm chậm thêm bao nhiêu

- [ ] 5.1 Chạy **xen kẽ** hai đường trên **cùng** tập đầu vào. MUST NOT chạy hết đường này rồi mới sang đường kia — tải của Google trôi theo thời gian, làm vậy là đo cả chuyện đó vào chênh lệch
- [ ] 5.2 Nêu **trung vị và phân vị 95**, không nêu trung bình: một lượt chậm bất thường kéo trung bình đi và che mất hình dạng
- [ ] 5.3 Đường gọi thẳng cần khoá nhà cung cấp, mà theo thiết kế change trước CRM **không còn giữ** khoá đó (để nó không đi vòng được). Nên phải dùng khoá của người vận hành, và ghi rõ đây là **mốc so**, không phải một đường production còn có thể chọn
- [ ] 5.4 Tách chênh lệch thành hai phần nếu đo được: chặng nginx, và chặng LiteLLM

## 6. Tài liệu

- [ ] 6.1 Nhật ký đo, mỗi kết luận kèm số. "Đã thử rồi" không phải kết quả
- [ ] 6.2 Ghi rõ điều nào **chứng minh được** và điều nào **suy luận** — trộn hai loại làm người đọc tin nhầm mức độ chắc chắn
- [ ] 6.3 Bổ sung vào danh sách báo lại nhóm CRM: `config.CKPT_JSON` là cấu hình chết, và `docs/HANDOVER.md` vẫn mô tả nó là file cho phép chạy lại
- [ ] 6.4 Nếu 2.5 cho ra phát hiện thật (429 không tới nhánh đúng) thì ghi thành việc riêng, đừng sửa lẫn vào change này
