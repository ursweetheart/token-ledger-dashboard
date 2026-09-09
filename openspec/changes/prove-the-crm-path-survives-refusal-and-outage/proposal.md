# Chứng minh đường CRM qua Gateway chịu được từ chối và mất Gateway

## Why

Change `route-the-crm-agent-through-the-gateway` chứng minh đường đi **thông**. Nó không
chứng minh đường đi **bền**, và có một lý do làm chuyện đó không tự xảy ra:

```
   CRM tu gioi han : ~7,3 luot/phut  (7,5s + jitter, tac gia khuyen nghi)
   Gateway cho     :  15 luot/phut
                      ────────────
   CRM chay o DUOI NUA tran
```

Nên **vận hành bình thường sẽ không bao giờ sinh ra 429**. Nhánh xử lý 429 của CRM — nhánh
nhận lỗi bằng cách **so chuỗi** trong thông báo, thứ dễ hỏng nhất trong cả tích hợp — vì thế
nằm nguyên đó chưa ai chạy qua. Muốn biết nó có chạy hay không thì phải **cố ý ép**.

Cùng lý lẽ đó áp cho hai chuyện khác:

- **Mất Gateway giữa lúc chạy batch.** Kế hoạch tháng 9 xếp "diễn tập đường lui" là rủi ro
  số 1 và tới nay chưa diễn tập lần nào. CRM có điểm lưu (`save_history_db_atomic` sau mỗi
  batch, ghi vào `classified_history_db.json`), nên nó *có thể* chạy lại được — nhưng "có
  thể" là suy luận từ đọc code, chưa phải phép đo.
- **Tải thật.** Đo trong sổ: ngày cao nhất **502 lượt**, giờ cao nhất **365 lượt**. Một lượt
  gọi = 25 dòng CRM. Chưa ai cho đường mới chạy ở khối lượng đó.

Và một câu đáng tiền: **Gateway làm chậm thêm bao nhiêu?** Hôm nay chỉ biết Gateway thêm một
chặng nginx và hai instance LiteLLM. Chưa ai đo độ trễ so với gọi thẳng nhà cung cấp, nên
không trả lời được cho nhóm CRM khi họ hỏi.

## What Changes

- **Ép 429 rồi chứng minh CRM lùi lịch đúng nhánh.** Nhánh "lùi lịch sự" (`10 × attempt`, tối
  đa 120 giây) phải chạy, chứ không phải nhánh chung `4,0 × attempt`.
- **Diễn tập mất Gateway giữa batch**, rồi chứng minh chạy lại không mất dòng và không đếm
  đôi.
- **Chạy một batch cỡ production** và đo: nhịp thực đạt, số 429, độ trễ, chi phí, và **mọi
  lượt gọi có quy được về agent 7 hay không**.
- **Đo chênh lệch độ trễ** giữa đường qua Gateway và đường gọi thẳng, trên cùng đầu vào.
- **Tách harness thành công cụ dùng lại được** cho 6 agent còn lại, thay vì một script chỉ
  dùng một lần cho CRM.

## Capabilities

### New Capabilities
- `agent-gateway-resilience`: khi một agent đã đi qua Gateway, hệ thống phải chứng minh được
  bằng phép đo rằng agent ấy chịu được Gateway từ chối, chịu được Gateway mất hẳn, và chịu
  được khối lượng thật — chứ không chỉ chứng minh một lượt gọi lẻ đi thông.

### Modified Capabilities
<!-- Khong co. `crm-gateway-routing` (change truoc) da neu yeu cau "nhanh qua han muc phai
     duoc coi la CHUA KIEM CHUNG khi tran cao hon nhip tu gioi han". Change nay di KIEM
     CHUNG dung yeu cau do, khong sua no. -->

## Impact

- Công cụ mới trong `tools/` — harness gọi tầng LLM của một agent, dùng lại được cho agent
  khác, không phải script riêng cho CRM
- `docker/gateway/config.gateway.yaml` — **đổi tạm** `rpm` để ép 429, rồi trả lại. Phải có
  bước trả lại tường minh, không dựa vào việc ai đó nhớ
- Tài liệu: nhật ký đo, kèm số

**Không đụng tới**

- Logic phân loại của CRM. Không sửa nhánh `gateway` đã viết ở change trước — nếu phải sửa
  thì đó là **phát hiện** của change này, ghi lại rồi mới sửa
- SharePoint, email, Excel. Mọi phép đo đi qua harness

**Phụ thuộc**

- Change `route-the-crm-agent-through-the-gateway` phải xong trước. Không có đường thông thì
  không có gì để ép hỏng
- Change `let-the-gateway-ledger-arrive-by-itself` — dùng lại dịch vụ tự làm mới và phép kiểm
  độ trễ; cả hai đã xong và đã archive

**Rủi ro đáng nói trước**

- Batch cỡ production nghĩa là gọi Google thật và tiêu credit thật. Phải chốt trần chi tiêu
  trước khi chạy, không phải sau
