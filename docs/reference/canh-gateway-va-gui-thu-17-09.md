# Canh Gateway và gửi thư — `gateway-watch`

Viết ngày 17/09/2026, cùng change `move-the-outage-alarm-out-of-the-agents`.

Tách rõ phần **chứng minh được** khỏi phần **suy luận**, theo khuôn của
[`ep-429-va-mat-gateway-10-09.md`](ep-429-va-mat-gateway-10-09.md).

---

## 1. Kết quả một dòng

`gateway-status` **đo** nhưng không báo — nó là một trang web, phải có người mở ra xem.
`gateway-watch` biến trang đó thành **thư**.

---

## 2. Anh sẽ nhận những thư nào

| Tiêu đề | Khi nào | Phải làm gì |
|---|---|---|
| `DOWN - GATEWAY HONG` | Gateway không phục vụ được | xử ngay |
| `WARN - Gateway mat mot phan nang luc, VAN dang phuc vu` | một instance chết, LB đẩy hết sang instance kia | xử trong giờ làm việc |
| `WARN - Khong doc duoc trang thai (Gateway van tra loi)` | `gateway-status` chết, Gateway thì không | **không phải sự cố Gateway** |
| `OK - Gateway da tro lai binh thuong` | phục hồi | đọc độ dài sự cố |
| `nhip tim - <ngày>` | mỗi ngày một lần | không phải làm gì |

**Một lần đổi trạng thái sinh đúng một thư.** Sự cố kéo dài hàng trăm nhịp dò vẫn chỉ một thư. Đi
qua nhiều mức thì nhiều thư — `degraded` rồi `unavailable` là hai lần đổi, tức hai thư, và đó là
đúng.

Hai nhịp hỏng **liên tiếp** mới báo, nhưng **một** nhịp tốt là đủ để báo phục hồi. Lệch nhau có chủ
ý: báo nhầm thì mất lòng tin, còn báo phục hồi muộn thì làm người ta lo thừa.

---

## 3. Vắng thư nhịp tim LÀ một tín hiệu — và nó có hai nghĩa

Không nhận được thư nhịp tim của một ngày nghĩa là **một trong hai**:

```
  cho canh da chet          container dung, hoac may chu chet
  duong thu da chet         SMTP hong, mat khau het han, bi chan spam
```

Cả hai đều dẫn tới cùng một hậu quả: **từ lúc đó trở đi, sự cố sẽ đi qua trong im lặng.**

Kiểm khi thấy vắng:

```bash
docker compose --profile gateway ps gateway-watch
docker compose --profile gateway logs --tail 50 gateway-watch
```

Log ghi `Mail failed (...)` hoặc `Mail not sent: ...` thì đường thư hỏng, không phải Gateway hỏng.

**Vì sao cần điều này:** sau change này, `gateway-watch` là **nguồn báo động duy nhất**. Nó hỏng theo
kiểu im lặng, mà im lặng lại trùng khít với tín hiệu "mọi thứ bình thường". Nhịp tim là thứ duy nhất
phân biệt được hai cái đó.

**Thư gửi hỏng thì MẤT HẲN, không thử lại.** Cố ý: mỗi lần thử `smtplib` chờ tới 30 giây, nên máy
chủ thư chết một giờ sẽ làm chính vòng lặp dò đứng — tức mất luôn việc canh để cố cứu việc báo.
Nhịp tim là cái vá cho chuyện đó.

---

## 4. Nó dò gì — ba đích, ba lớp

```
 (A)  https://<ten mien>/lb-health       DNS + TLS + proxy may chu + nginx con song
 (B)  gateway-status:8089/api/status     instance nao chet, degraded hay unavailable
 (C)  gateway-lb:4000/health/readiness   LiteLLM san sang + db: connected
```

Chênh lệch giữa chúng chính là chẩn đoán, và thân thư in ra kết quả từng đích:

| (A) | (B)+(C) | Nghĩa |
|---|---|---|
| đạt | đạt | khoẻ |
| **hỏng** | **đạt** | Gateway khoẻ — hỏng ở DNS / TLS / proxy máy chủ |
| đạt | hỏng | nginx sống, LiteLLM hoặc Postgres hỏng |
| hỏng | hỏng | chết hẳn |

**(A) hiện CHƯA bật.** Đo 17/09/2026: `apigateway.rangdong.com.vn` trả `Non-existent domain` cả
trong container lẫn trên máy host, và không agent nào dùng nó — cả CRM lẫn DMS đều gọi
`http://gateway-lb:4000`. Bật bây giờ là tự tạo một đích **đỏ mỗi phút**. Cách bật khi tên miền đã
dựng xong nằm trong `.env.example`.

---

## 5. Ba thứ nó KHÔNG canh — chứng minh được

**5.1. Khoá hết hạn, hết hạn mức, model khai sai.** Mọi phép dò đều miễn phí, nên không lượt nào đi
qua đường tính tiền. `tools/gateway-status/server.js` cũng khai đúng trần này:

> `Liveness checks only. Provider access, credentials, database and Redis readiness are not verified.`

Triệu chứng: agent nhận 403/429 hàng loạt, chuông vẫn xanh. Lối vá về sau là đọc cột kết cục của
lượt gọi **thật** trong sổ, không phải tự gọi thử — một chuông khác, một câu hỏi khác.

**5.2. Sự cố ngắn hơn một nhịp dò.** Nhịp 60 giây cộng luật "hai nhịp liên tiếp":

```
  su co duoi ~60 giay    agent co fallback da doi duong roi quay ve, KHONG co thu
  su co 60-180 giay      co thu, moc bat dau lech toi da mot nhip
  su co tren 180 giay    bao du, do dai chinh xac toi +/- mot nhip
```

**5.3. Máy chủ chết.** `gateway-watch` chạy cùng máy với Gateway. Máy chết thì cả hai cùng chết và
không có thư nào — nhịp tim bắt được lớp này, nhưng chậm tối đa 24 giờ. Vá thật là dựng **bản thứ
hai trên máy khác**; cùng một tệp `.py`, chỉ đổi biến môi trường, xem `.env.example`.

---

## 5b. Khi có hai bản — đọc tiêu đề là biết hỏng ở lớp nào

**Hai máy KHÔNG dùng chung mạng Docker được.** Mạng của compose này là `bridge`, mà `bridge` có
`scope=local` — nó sống trong nhân của một máy. Nên bản ngoài không gọi được `gateway-status:8089`
hay `gateway-lb:4000`; nó chỉ gọi tên miền công khai, và bỏ trống `WATCH_STATUS_URL`.

Mỗi bản mang tên riêng qua `WATCH_NAME`, và tên ấy nằm trong tiêu đề thư:

| Nhận thư từ | Nghĩa |
|---|---|
| **cả hai bản** | hỏng thật, hỏng sâu |
| **chỉ bản `ngoai`** | lớp vỏ hỏng — DNS, TLS, proxy máy chủ — **hoặc cả máy chủ đã chết** |
| **chỉ bản `trong`** | hỏng bên trong Gateway, lớp vỏ vẫn đứng |

Bảng này viết sẵn trước khi dựng bản ngoài, để lúc dựng xong đọc là hiểu ngay.

**Cố ý KHÔNG mở bind để bản ngoài đọc được chiều sâu.** Ba lối đều đắt hơn việc chạy hai bản: đổi
mạng sang `overlay` + Swarm (dựng lại cả hạ tầng), đổi bind `127.0.0.1` sang IP LAN kèm nới
`LLM_GATEWAY_ADMIN_CIDR` (mở trang "instance nào đang chết" ra mạng công ty), hoặc dựng VPN (thêm
một hạ tầng nữa, mà nó hỏng thì chuông báo giả).

---

## 6. Suy luận, CHƯA chứng minh

**`/api/status` có thể mù ở ca "instance khoẻ mà LB không gọi tới".** Ngày 17/09, ép IP đổi một bậc
thì `litellm-1` nhận 0/20 lượt trong khi cả ba container `healthy`. Ở ca ấy cả bốn thành phần của
`gateway-status` đều sống, nên **nhiều khả năng** nó vẫn trả `reachable`.

Chưa đo. Phép đo ngày 17/09 dùng `docker stop`, làm instance chết hẳn — chế độ hỏng khác, và ở đó
`/api/status` **bắt được** (`degraded`). Bản vá `resolve` đã chặn nguyên nhân, nên đây là trần của
phép đo chứ không phải lỗ hổng đang mở.

---

## 7. Tra số lượt agent đã đi đường thẳng

Thư "đã trở lại bình thường" nêu mốc bắt đầu và mốc kết thúc, nhưng **không** có số lượt agent đã
gọi thẳng nhà cung cấp trong khoảng đó — chỗ canh đứng ngoài, nó không biết được.

Con số ấy nằm trong log của agent:

```bash
docker logs <container-cua-agent> 2>&1 | grep '\[FALLBACK\]'
```

Nó quan trọng vì lượt đi đường thẳng **không vào sổ Gateway**, nên `fact_call` sẽ thiếu chúng.

---

## 8. Trong giai đoạn chuyển tiếp: một sự cố có thể sinh HAI thư

Agent CRM hiện vẫn còn mã gửi thư riêng (`src/llm.py:263` và `:279`). Chưa gỡ, nên một sự cố sẽ sinh
thư từ **cả hai** nguồn.

**Đó không phải lỗi.** Và trong giai đoạn này nó còn có lợi: thư của CRM mang đúng con số ở mục 7,
cộng project nào trả tiền cho các lượt ấy.

---

## 9. Bàn giao — gỡ mã gửi thư khỏi agent

**Người gỡ: leader.** Việc này nằm **ngoài** change dựng `gateway-watch`.

**Điều kiện trước khi gỡ:** người nhận đã xác nhận thấy **cả** thư sự cố **lẫn** thư nhịp tim trong
hộp thư thật, kể cả kiểm thư rác. Gỡ trước là tự tạo một khoảng không có chuông nào.

| | Việc | Vì sao |
|---|---|---|
| Gỡ | hai lệnh `_notify(...)` ở `CRM-Classification-Pipeline/src/llm.py:263` và `:279` | `gateway-watch` đã lo |
| Gỡ | hàm `_notify` ở `llm.py:292`, **nếu** sau đó không còn ai gọi — kiểm bằng `grep`, không bằng trí nhớ | dọn mã chết |
| **GIỮ** | `log_fallback()`, máy trạng thái hai nấc, dòng ghi câu lỗi cuối từ Gateway | agent vẫn phải **chạy tiếp** khi Gateway chết, và log là chỗ tra số ở mục 7 |
| **GIỮ** | `src/notification.py` | `pipeline.py:28` và `:879` vẫn dùng nó cho **thư lỗi của lô** — việc khác hẳn. Xoá là làm hỏng một đường thư đang chạy |

**Nghiệm thu sau khi gỡ:** chạy lại diễn tập fallback của CRM → lô vẫn chạy xong, log `[FALLBACK]`
vẫn đầy đủ, không thư nào từ agent.
