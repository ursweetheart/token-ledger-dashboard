# Hạn mức chi tiêu — cách dùng và cách nó hoạt động

Viết 20/09/2026, cùng change `stop-a-project-when-its-quota-runs-out`.

Mỗi khoá agent có một hạn mức tiền do người nhập. Tiêu hết thì Gateway ngừng
chuyển request đi, cho tới khi có người nạp thêm. **Không tự đặt lại theo tháng.**

---

## 1. Dùng tab Setting

Mở dashboard → tab **⚙ Setting**. Mỗi khoá agent một dòng.

| Cột | Nghĩa |
|---|---|
| Đã tiêu | phần **Gateway nhìn thấy**, không phải tổng chi phí ở các tab khác |
| Hạn mức | số đang hiệu lực, `chưa đặt` nghĩa là không chặn gì |
| Tỷ lệ | đã tiêu / hạn mức |
| Trạng thái | `còn hạn mức` · `sắp hết` (≥90%) · `ĐANG CHẶN` |

Ba nút, mỗi nút **một nghĩa cố định** — kết quả luôn biết trước:

| Nút | Làm gì |
|---|---|
| **Đặt thành** | hạn mức = đúng số vừa gõ. Muốn **giảm** thì gõ số nhỏ hơn |
| **Cộng thêm** | hạn mức = hạn mức hiện tại + số vừa gõ |
| **Chặn** | hạn mức = 0. Nút này **không đọc ô nhập** |

Cả ba đều đợi Gateway trả lời rồi mới đổi số trên màn hình — bấm xong mà báo đỏ
thì tức là **chưa lưu được**, số cũ vẫn nguyên.

> **Vì sao không gộp thành một nút** (đã cân nhắc và bỏ, 20/09/2026): ý tưởng là
> "còn hạn mức thì cộng thêm, hết rồi thì đặt lại". Nhưng ranh giới giữa hai
> nghĩa là lúc *đã tiêu* chạm *hạn mức*, mà con số đó chậm tới 5 phút — người
> dùng nhìn thấy "còn hạn mức", bấm để cộng thêm, và nó vừa hết nên thành đặt
> lại. Cùng một thao tác, hai kết quả, không lỗi nào báo ra. Thêm nữa, ở nhánh
> "cộng thêm" thì gõ `0` nghĩa là `hiện tại + 0`, tức **mất luôn cách chặn**.

Mọi lần đặt và nạp đều để lại một dòng trong bảng **Lịch sử nạp** phía dưới.

> **Số ở tab này chậm tới 5 phút.** Khoá được nhớ đệm 300 giây, nên `đã tiêu` có
> thể là số của 5 phút trước. Đó là độ trễ đã biết và đã chấp nhận: hạ nó xuống
> đồng nghĩa mở lại một vấn đề đã đóng ngày 08/09 (khoá ảo sống sót qua một lần
> Postgres khởi động lại).

---

## 2. Hết hạn mức thì agent nhận được gì

Hai kiểu trả lời, chọn theo tag của agent:

```
   agent CO NGUOI CHAT                agent CHAY THEO LO
   (Contact Center, Ralli,            (Phan Loai Phan Hoi Tiep Thi,
    TLA Hop Dong, Sale Agent)          Phan Loai Du Lieu CRM)
   ──────────────────────             ──────────────────────
   HTTP 200                           HTTP 429
   than tra loi dung hinh dang        thong bao co chuoi `429`
   cua mot cau tra loi model          -> app tu lui roi thu lai
   -> nguoi dung doc duoc cau
      thong bao, hieu ngay
```

Agent chạy lô **không** nhận tin nhắn giả, và đó là chủ ý: chúng đang đợi JSON.
Một câu văn xuôi đi vào đó sẽ hỏng lúc phân tích và báo thành lỗi JSON — người
vận hành đi tìm bệnh ở chỗ phân tích dữ liệu trong khi bệnh là hết tiền.

Khai loại agent ở biến `QUOTA_CHAT_TAGS`. **Tag chưa khai thì mặc định là agent
chạy lô.**

---

## 3. Cảnh báo email

Dịch vụ `quota-watch` gửi thư ở ba bậc, mỗi bậc **một thư khi bậc đổi**:

| Bậc | Nghĩa |
|---|---|
| ≥ 90% | sắp hết, còn kịp nạp |
| ≥ 100% | đã chạm hạn mức, Gateway bắt đầu chặn |
| ≥ 110% | **vượt đáng kể — việc chặn có thể không hoạt động** |

Bậc thứ ba không phải nhắc lại rằng đã hết. Gateway chặn ngay khi chạm 100%, nên
tiêu thêm được hơn 10% nữa nghĩa là lưu lượng đang đi đường khác: agent còn khoá
nhà cung cấp riêng, hoặc hook không được nạp, hoặc `QUOTA_DRY_RUN` còn bằng 1.

Nạp thêm làm tỉ lệ tụt xuống thì bậc được đặt lại trong im lặng; lần vượt sau lại
báo. Cấu hình SMTP dùng chung với `gateway-watch`, trong `.env`.

---

## 4. Giới hạn thi hành — đọc trước khi tin vào con số

**Chỉ chặn được thứ đi qua Gateway.** Hôm nay là **Phân Loại Phản Hồi Tiếp Thị**
và **Phân Loại Dữ Liệu CRM**. Sáu agent còn lại vẫn gọi thẳng Google: hạn mức của
chúng chỉ là đèn báo, không chặn được gì.

**Phân Loại Dữ Liệu CRM có đường lui đi thẳng Google** bằng `sa-key.json` (change
`keep-the-crm-agent-running-when-the-gateway-dies`). Khi nó rơi vào đường đó, hạn
mức không chặn được. Đây là một lỗ thủng **có tên**, chưa ai quyết bỏ hay giữ.

**Luôn vượt một khoản nhỏ.** Chi phí của một request chỉ biết sau khi gọi xong,
nên luật là *đã tiêu ≥ hạn mức thì chặn lượt kế tiếp*. Cộng với độ trễ 5 phút ở
mục 1.

**Tiền là số ước tính.** LiteLLM tính từ bảng giá nội bộ của nó, không phải hoá
đơn Google. Model chưa có trong bảng giá thì chi phí ghi **0** — và một model như
vậy sẽ **không bao giờ làm hết hạn mức**. Điều này nối thẳng với ý định mở tuyến
`*` cho agent tự chọn model: mở tuyến đó mà không chốt giá trước là mở một lối đi
vòng qua hạn mức.

---

## 5. Triển khai lần đầu

1. Điền `LITELLM_MASTER_KEY` trong `.env` (backend cần nó để sửa hạn mức). Thiếu
   thì backend **không khởi động** — hoặc đặt `QUOTA_DISABLED=1` trên máy không
   có Gateway.
2. Giữ `QUOTA_DRY_RUN=1`. Dựng lại `litellm-1` và `litellm-2`.
3. **Xác nhận hook thật sự được nạp**: gọi một lượt thật rồi tìm dòng
   `quota_block_would_have` trong `docker compose logs litellm-1`.
   **Không kết luận từ việc container lên `healthy`** — khai sai tên callback
   không làm LiteLLM dừng, mọi đèn vẫn xanh và hạn mức lặng lẽ không chặn gì.
4. Nhập hạn mức ở tab Setting, đối chiếu số với các tab khác.
5. Đặt `QUOTA_DRY_RUN=0`, dựng lại hai instance. Từ đây chặn thật.

Lùi lại: gỡ dòng `callbacks` trong `docker/gateway/config.gateway.yaml` rồi dựng
lại hai instance. Hạn mức còn nằm trong metadata của khoá cũng không gây hại —
không ai đọc thì không ai bị chặn.

---

## 6. Hạn mức nằm ở đâu, và một rủi ro dài hạn

Hạn mức **không có bảng riêng**. Nó nằm trong `metadata` của chính virtual key:

```json
{"tags": ["dms-feedback"], "quota_usd": 50, "quota_log": [...]}
```

Nhờ vậy không có migration, không có vai database mới, và `spend` thì LiteLLM đã
cộng sẵn. Backend sửa nó qua `/key/update`, nên **database vẫn chỉ-đọc hoàn toàn**.

> **BẪY, và nó đã được khoá bằng một phép kiểm.** `/key/update` **thay thế** cả
> cục `metadata` chứ không gộp (`key_management_endpoints.py:2010`). Gửi thiếu là
> **xoá mất `tags`** — và mất tag thì request rơi sang tuyến khác, tiền ghi sai
> project, trong khi mọi lượt gọi vẫn trả 200. Đo 31/08 trên khoá không tag: 7/8
> thành công, 1/8 lạc tuyến. Vì vậy `backend/gateway.py` luôn **đọc – gộp – ghi
> lại cả cục**, và `tests/test_quota_gateway.py` soi đúng thân yêu cầu gửi đi.

**Rủi ro dài hạn.** Trường `tags` **cấp cao** của `/key/generate` và `/key/update`
là tính năng trả phí của LiteLLM (`LiteLLM_ManagementEndpoint_MetadataFields_Premium`).
Vòng kiểm giấy phép chỉ soi **tên trường của request**, nên `metadata.tags` đi
lọt — và dự án đã chạy bằng đường đó từ 31/08/2026.

Nếu bản LiteLLM mới soi cả bên trong `metadata` thì gãy **không chỉ quota** mà
gãy luôn việc quy tiền theo agent.

Dấu hiệu nhận biết: sau khi nâng cấp, `/key/update` trả **403**, hoặc virtual key
bỗng mất tag. Khi đó fork là đường chữa — gỡ đúng vòng kiểm ấy và thêm một bước CI
canh giữ, như bản vá Sentinel đã làm.
