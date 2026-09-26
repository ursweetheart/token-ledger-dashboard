## Context

> **Topology update (18/09/2026):** `gateway-status` is no longer a separate
> service. Its existing Node collector runs inside `gateway-lb`; the internal
> watcher target is `http://gateway-lb:8089/api/status`, and port 8089 is not
> published. Historical measurements below retain the old service wording.

Capability `agent-outage-alerting` ra đời ngày 14/09 từ diễn tập 10/09: Gateway mất, agent CRM thử
ba lần trong **21–24 giây** rồi bỏ cả lô, và chỉ để lại ba dòng log giữa hàng trăm dòng khác. Lời
giải lúc ấy đặt việc gửi thư **bên trong agent**, vì lúc ấy chỉ có một agent được sửa.

Ba tháng sau, số liệu đã khác: 8 agent, 1 có mã gửi thư. Change này giữ nguyên chẩn đoán cũ — im
lặng là không chấp nhận được — nhưng đổi chỗ đặt cái chuông.

**Đo 17/09/2026, và phải nói rõ nó đo được tới đâu.** Chỉ 3 trong 8 repo agent có trên máy phát
triển này. Trong ba repo ấy, đúng **một** repo gửi thư khi đổi đường: `CRM-Classification-Pipeline`,
`src/llm.py:263` và `:279`.

`dms-feedback-classification` **có** đường gửi thư nhưng dùng cho việc khác — thư báo lỗi của lô
(`notification.py::_build_error_html`), cùng loại với `pipeline.py` của CRM. Nó không có nhánh đổi
đường; `dms/metrics.py:291` có `_consecutive_failures >= 3` nhưng đếm **tệp xử lý hỏng** và chỉ sinh
chuỗi `health_status`, còn `dms/gemini_client.py:252` ghi rõ nó **cố ý không có fallback**.

Nên con số 1/8 **chưa bị bác, cũng chưa được chứng minh đủ**: 5 repo còn lại phải kiểm trên máy
khác. Nếu con số ấy hoá ra lớn hơn 1, phần Why của proposal phải viết lại theo số đo — nhưng ba lý
do của change thì không đổi, vì chúng không dựa vào việc "chỉ có một agent", mà dựa vào việc chỗ canh
ngoài làm được ba thứ agent không làm được.

**Hình dạng hạ tầng đã đổi ngày 17/09 (`d0d8ff4`), và thiết kế này viết theo bản mới:**

- `gateway-edge` **đã bị xoá**. `docker/gateway/edge.conf.template` không còn. Chỉ còn hai nginx
  trong toàn bộ compose: `token-ledger-web` (dashboard, nginx 1.28) và `token-ledger-gateway-lb`
  (gateway + trang status, nginx 1.27).
- `gateway-status` là dịch vụ mới, và **nó đã dò sẵn** bốn thành phần: `lb`, `proxy1`, `proxy2`,
  `route`. Gộp thành `reachable` / `degraded` / `unavailable`, trả ở `/api/status`.
- `nginx.conf` mới theo lối **cấm hết rồi mở từng đường**: `location / { return 404; }`, cộng
  `default_server` trả 444 cho `Host` lạ, cộng `if ($host = ${LLM_GATEWAY_DOMAIN}) { return 404; }`
  cho `/health/*`, cộng ACL theo IP cho `/api/status`.

**Số đo sẵn có, không phải suy luận:**

- `nginx.conf`, ngày 17/09, ép IP `litellm-1` đổi một bậc:

  ```
  litellm-1    0 / 20 luot      <- bien mat khoi vong chia tai
  litellm-2   20 / 20 luot
  cung luc:   ca ba container `healthy`, /lb-health tra `lb-ok`
  ```

- `docker-compose.yml`, dịch vụ `ledger-refresh`:

  ```
  # CO Y KHONG DAT healthcheck. Healthcheck kieu "tien trinh con song" chinh la
  # phep do sai ... dung lop "song ma hong" da gap o /health/liveliness cua Gateway.
  ```

  Luật ấy áp thẳng cho change này. Nó quyết định D1 và D4.

## Decisions

### D1 — Chỉ dò miễn phí. Không gọi thật, kể cả bằng khoá miễn phí

Phép dò dùng endpoint health miễn phí. **Không** gửi `POST /v1/chat/completions`.

Phương án "gọi thật mỗi giờ" đã được xét kỹ và **bỏ**. Nó có năm bất cập, và bất cập đầu tiên là
bất cập giết nó:

**(1) Nó chứng minh cho khoá của chính nó, không cho khoá của agent nào.** Lớp hỏng mà cuộc gọi
thật sinh ra để bắt — khoá hết hạn, hết quota, model khai sai — hầu như luôn là riêng từng khoá,
riêng từng model. Chuông gọi bằng khoá riêng trên model rẻ nhất sẽ xanh trong khi khoá của agent 7
đã hết hạn. Tệ hơn: nó tạo **cảm giác đã phủ**.

**(2) Nó làm bẩn sổ.** Mỗi lượt sinh một dòng `LiteLLM_SpendLogs` → `refresh_gateway.py` kéo vào
`fact_call`. Nguồn bẩn là log của LiteLLM, **không phải** hoá đơn — nên đổi khoá nhà cung cấp không
làm dòng ấy biến mất.

**(3) Nó đâm vào ba spec.** Lượt gọi cần danh tính. Khai một agent giả thì vướng
`visible-data-provenance`; để trống thì vướng `call-record-completeness` và
`user-dimension-coverage`. Không có lối thứ ba sạch.

**(4) Một lượt mỗi giờ chỉ chạm một instance.** Round-robin. Instance "sống mà hỏng" có ~50% khả
năng bị bỏ sót mỗi giờ.

**(5) Khuôn khoá ảo của `tools/gateway-smoke/run.py` không chuyển sang được.** Nó dùng
`duration: '1h'` vì nó là phép thử chạy một lần. Chuông chạy mãi, nên khoá của nó phải sống mãi —
tức một bí mật lâu dài, hoặc một việc xoay khoá thủ công không bao giờ hết.

**Ý khoá miễn phí riêng — đã xét, và nó tốt hơn là thoạt nghe.** Nó lật ngược (2): tiền của chuông
không nằm trong hoá đơn công ty, nên lọc bỏ khỏi dashboard làm hai số **khớp** thay vì lệch. Nó
cũng làm (3) nhẹ đi — một điều kiện lọc theo tag ở một chỗ — và gần như xoá (5), vì khoá ảo chỉ gọi
được một model miễn phí với ngân sách nhỏ. Nhưng nó **không chạm được** (1) và (4), và nó thêm một
bất cập mới: free tier không có cam kết dịch vụ, nên khoá bị thu hồi hay đổi chính sách sẽ làm
chuông đỏ trong khi hệ thống công ty hoàn toàn khoẻ.

**Trần đã biết, chấp nhận có ý thức:** lớp "sống mà hỏng" theo từng khoá, từng model **không được
phủ**. `tools/gateway-status/server.js` cũng khai đúng trần ấy:

> `Liveness checks only. Provider access, credentials, database and Redis readiness are not verified.`

**Lối thay thế, rẻ hơn và phủ rộng hơn — đọc kết cục thật thay vì tạo lưu lượng giả.** Gateway đã ghi
kết cục của mọi lượt gọi; spec `gateway-call-outcomes` bắt buộc *"lượt gọi hỏng phải được ghi lại kèm
lý do"*. Hỏi sổ thì biết được tỷ lệ hỏng **theo từng agent, từng model, trên lưu lượng thật**, không
tốn tiền, không giữ khoá, không bẩn sổ.

Nhưng nó là **một chuông khác, trả lời một câu hỏi khác**, và phải để thành change riêng:

```
  Q1  "Duong co thong khong?"     -> duong DUT thi khong ai ghi gi
                                     -> BAT BUOC chu dong go cua  -> change nay
  Q2  "Duong thong, nhung cuoc goi co hong khong?"
                                  -> Gateway VAN GHI, ghi ca ly do
                                     -> chi can DOC  -> change sau
```

Và vì đường đứt thì sổ trống, "sổ trống" không phải tín hiệu dùng được: 0 lượt trong một giờ có thể
là 2 giờ sáng, cũng có thể là Gateway chết từ 1 giờ. Chỉ phép dò chủ động phân biệt được. Hai chuông
bổ sung nhau, không thay nhau.

### D2 — Nhịp mặc định 60 giây, không 300

Người dùng đề xuất 5 phút. Đặt mặc định 60 giây, để lại biến `WATCH_EVERY_SECONDS`.

Lý do là một phép trừ: phép dò **miễn phí** (D1), nên cửa sổ mù không phải ràng buộc kỹ thuật mà là
thứ ta tự chọn. Mà cửa sổ mù có hậu quả đo được:

```
  t = 0s        Gateway chet
  t = 21-24s    agent CRM chuyen sang goi thang        <- da xay ra roi
  t = 60-180s   canh gac bao (nhip 60s, 2 lan lien tiep)
  t = 300-900s  canh gac bao (nhip 300s, 2 lan lien tiep)
```

Nhịp 60 giây rút lớp vô hình xuống một phần năm, đổi lại là 1.440 lượt `GET` vào endpoint tĩnh —
chi phí thật bằng không. Cửa sổ mù vẫn còn, định lượng ở D9.

### D3 — Ba đích, mỗi đích phủ một lớp; ghép lại thì tự chẩn đoán

```
  (A)  https://<ten mien>/lb-health          DNS + TLS + proxy may chu + nginx song
  (B)  gateway-status:8089/api/status        instance nao chet, degraded / unavailable
  (C)  gateway-lb:4000/health/readiness      LiteLLM san sang + db: connected
```

Vì sao ba chứ không một: chúng đo ba chiều khác nhau, và **chênh lệch giữa chúng chính là chẩn
đoán**:

| (A) | (B) + (C) | Kết luận trong thư |
|---|---|---|
| đạt | đạt | khoẻ |
| **hỏng** | **đạt** | Gateway khoẻ — hỏng ở **DNS / TLS / proxy máy chủ** |
| đạt | hỏng | nginx sống, **LiteLLM hoặc Postgres** hỏng |
| hỏng | hỏng | chết hẳn |

Dòng thứ hai là dòng đáng tiền: nó trả lời tự động câu *"agent đổi đường vì Gateway chết, hay vì
đường tới Gateway chết?"* — hai nguyên nhân, hai cách sửa hoàn toàn khác nhau, mà log của agent chỉ
nói được "không kết nối được".

**(B) không viết lại phép dò.** `tools/gateway-status/server.js` đã dò bốn thành phần rồi. Hai chỗ
cùng dò một thứ theo hai kiểu là đúng loại lệch mà proposal ngày 17/09 đã cảnh báo.

**(C) không phải cho agent, nó cho cái sổ.** Postgres chết thì LiteLLM vẫn trả lời, agent **không**
đổi đường và không biết gì — nhưng spend log không ghi được, và `fact_call` thủng. Với một dự án tên
là token ledger, đó mới là thiệt hại thật.

**(B) KHÔNG thừa so với (C) — đo 17/09/2026, `docker stop litellm-1`:**

```
lb-health        :  lb-ok                                   <- XANH
health/readiness :  {"status":"healthy","db":"connected"}    <- XANH
api/status       :  degraded   (proxy1 unreachable)         <- chi minh no thay
```

Mất một nửa năng lực xử lý thì **(C) cũng mù**, y như `/lb-health` — vì nó đi qua LB, mà LB đẩy
sang instance còn sống. Trước phép đo này, (B) chỉ được biện minh bằng "chiều rộng". Giờ nó có lý do
cứng: bỏ (B) là mất hẳn khả năng thấy `degraded`, đúng cái ca mà agent cũng không bao giờ báo.

**Đo kèm, ảnh hưởng tới `timeout` của watcher:** instance chết làm (B) chậm thêm ~2,5 giây mỗi nhịp,
vì DNS của Docker vẫn trả địa chỉ cũ nên `gateway-status` phải chờ hết hạn chứ không bị từ chối ngay.

**Và (A) hiện chưa dò được gì — tên miền chưa tồn tại:**

```
trong container:  gaierror [Errno -2]
tren may host:    nslookup -> Non-existent domain
```

Khớp với việc không agent nào dùng tên miền (cả CRM lẫn DMS đều gọi `http://gateway-lb:4000`). Nên
(A) là phép dò của **đường sắp tới**, không phải đường đang dùng — và vì vậy nó phải **tuỳ chọn**,
xem D11.

### D4 — Qua tên miền public chỉ đo được lớp vỏ, và đó là đúng thiết kế

Với `Host` là tên miền public, `nginx.conf` chỉ cho qua:

| Đường | Qua tên public | |
|---|---|---|
| `/v1/chat/completions`, `/gateway/v1/...` | ✅ | **tốn tiền** |
| `/lb-health`, `/edge-health` | ✅ 200 | `return 200` cứng |
| `/health/readiness`, `/health/liveliness` | ❌ 404 | `if ($host = ${LLM_GATEWAY_DOMAIN})` |
| `/api/status` | ❌ | ACL theo IP **và** `server.js` đòi `Host: localhost` |
| còn lại | ❌ 404 | `location / { return 404; }` |

Nên (A) chỉ dùng được `/lb-health`, và nó chỉ chứng minh tiến trình nginx còn sống. **Đó là giới hạn
chấp nhận được, vì nhiệm vụ của (A) đúng là đo lớp vỏ** — DNS, TLS, proxy máy chủ. Chiều sâu do (B)
và (C) lo, từ bên trong.

`location / { return 404; }` mới là lớp quan trọng nhất của cấu hình ấy, và nó không liên quan gì
tới health: nó giấu `/key/generate`, `/spend/logs`, `/user/new`, `/model/info` và giao diện quản trị
của LiteLLM khỏi Internet. Health bị 404 chỉ là hệ quả đi kèm.

MUST NOT dùng `/lb-health` **từ bên trong** làm bằng chứng Gateway khoẻ: ngày 17/09 nó trả `lb-ok`
trong khi `litellm-1` nhận 0/20 lượt. MUST NOT dùng `/health/liveliness` làm phép đo chiều sâu —
đúng lớp "sống mà hỏng" mà `ledger-refresh` đã từ chối.

### D5 — Trạng thái ghi ra tệp, không giữ trong bộ nhớ

Một tệp JSON nhỏ trong `var/`, ghi mỗi lần đổi trạng thái.

`restart: unless-stopped` nghĩa là container sẽ dựng lại. Giữ trạng thái trong bộ nhớ thì mỗi lần
dựng lại là thêm một thư cho cùng một sự cố — phá đúng luật gộp theo sự cố. Đọc tệp phải chịu được
tệp rỗng và tệp hỏng: coi như "đang khoẻ" rồi chạy tiếp.

### D6 — Dùng lại khuôn `ledger-refresh`, không cron

`docker-compose.yml` đã có đúng hình dạng này:

```yaml
ledger-refresh:
  image: token-ledger-tools:local
  command: ["python3", "scripts/refresh_gateway.py", "--every", "${REFRESH_EVERY_SECONDS:-300}"]
  restart: unless-stopped
```

| | `cron` thật | Vòng lặp trong container |
|---|---|---|
| Cách chạy | mỗi nhịp đẻ một tiến trình mới | một tiến trình sống suốt, ngủ rồi lặp |
| Cần thêm gì | cài `cron` vào image, dựng lịch, đẩy log ra | không gì cả |
| Chết thì sao | phải tự lo | `restart: unless-stopped` dựng lại |
| Repo đã có | không | **có** |

Container **chính là** cái lịch. Và vòng lặp viết kiểu **dò trước, ngủ sau** thì nhịp đầu tiên xảy
ra ngay lúc container lên — tức phép kiểm lúc khởi động được miễn phí, không cần một job riêng.

**`PYTHONIOENCODING=utf-8` là bắt buộc.** Thiếu nó thì một dòng log tiếng Việt làm script chết giữa
chừng.

**Không đặt `healthcheck`**, cùng lý do `ledger-refresh` không đặt. Phép đo đúng là thư nhịp tim ở
D7.

### D7 — Thư nhịp tim mỗi ngày là bắt buộc, không phải tuỳ chọn

Trước change này, mỗi agent có fallback là một nguồn báo động độc lập. Sau change này chỉ còn **một**
nguồn. Và nó hỏng theo kiểu tệ nhất có thể: **im lặng** — mà im lặng lại trùng khít với tín hiệu
"mọi thứ bình thường".

Mỗi ngày một thư: còn sống, đã dò bao nhiêu nhịp, bao nhiêu nhịp hỏng. Vắng thư của ngày hôm đó
**là** tín hiệu, và phải nằm trong tài liệu vận hành chứ không để người nhận tự đoán.

**Luật gửi là "lần dò đầu tiên của ngày sau giờ X", KHÔNG phải "đúng giờ X".** Bản đầu của mục này
ghi "giờ cố định"; đo 17/09 cho thấy chữ ấy sai và mã thì đúng. Nếu đòi đúng giờ X, chỗ canh được
dựng lại trong đúng giờ ấy sẽ mất thư của cả ngày — mà vắng nhịp tim lại chính là tín hiệu ta bảo
người vận hành đọc là "chỗ canh đã chết". Tức làm cho đúng chữ sẽ **tự tạo báo động giả**.

Hệ quả kèm theo, chấp nhận: thư nhịp tim đầu tiên bắn ngay khi dựng dịch vụ, không chờ tới hôm sau.
Đó là điều tốt — nó chứng minh đường thư chạy được ngay sau khi triển khai.

### D8 — Con số "bao nhiêu lượt đi đường thẳng" ở lại trong log, và thư phải trỏ tới nó

Thư của agent hiện mang ba thứ chỗ canh ngoài không biết được: project nào trả tiền
(`VERTEX_PROJECT`), **bao nhiêu lượt** đã đi đường thẳng, và câu lỗi cuối cùng từ Gateway. Con số thứ
hai đáng giá nhất — nó lấp đúng khoảng hụt của `fact_call`.

| | Cách | Đánh giá |
|---|---|---|
| (a) | Chấp nhận chỉ còn log | Chính là sự im lặng ngày 10/09 quay lại |
| (b) | Agent ghi một dòng vào bảng riêng, dashboard đọc | Đúng nhất, nhưng đụng cả 8 agent |
| (c) | **Giữ `log_fallback()` nguyên vẹn; thư của canh gác trỏ tới nó** | Chọn |

Cách (c) là một câu trong thân thư: *"Các lượt đi đường thẳng trong khoảng này nằm ở log của agent,
tìm theo `[FALLBACK]`."* Thư nêu **khoảng thời gian chính xác**, mà đó chính là thứ cần để tra log.

Vì sao chấp nhận được, dù spec viết "một dòng log MUST NOT được coi là đã báo": spec cấm dùng log
**làm cách báo động**. Ở đây báo động là thư — đã tới nơi, đúng lúc. Log chỉ còn là **chỗ tra số chi
tiết** sau khi người ta đã được báo. Hai vai khác nhau.

### D9 — Cửa sổ mù còn lại, viết ra thay vì để người dùng tự phát hiện

Nhịp 60 giây cộng luật "hai nhịp hỏng liên tiếp mới báo", **cộng thời gian chờ hết hạn của chính
phép dò** — đây là phần bản đầu bỏ sót, và nó không nhỏ:

```
  khi moi thu chet that, moi nhip mat ~25 giay cho het han (do 17/09)
  -> thoi gian toi thu dau tien = 2 x (25 + 60) ~ 170 giay
```

- sự cố **dưới ~148 giây**: có thể **không có thư nào**
- sự cố **148–176 giây**: có thể có thư, có thể không, tuỳ rơi vào đâu trong nhịp
- sự cố **trên ~176 giây**: báo đủ, độ dài chính xác tới ±1 nhịp

**ĐÃ ĐO 18/09/2026 — không còn là suy luận.** Cách làm hỏng mới: `docker pause` / `docker unpause`,
đóng băng tức thì cả hai chiều, nên hẹn được giờ sự cố. Đó là thứ lần đo 17/09 thiếu: `docker stop`
rồi `start` cách nhau 4 giây vẫn tạo sự cố thật dài ~30 giây, vì LiteLLM cần thêm thời gian mới
`healthy`.

```
  su co 26 giay,  lot han giua hai nhip   -> 0 nhip hong,  KHONG thu   (08:56:57 - 08:57:23)
  su co 121 giay, trum dung mot nhip      -> 1 nhip hong,  KHONG thu   (08:59:57 - 09:01:58)
```

Phép đo cũng sửa lại số cũ: nhịp hỏng **đắt hơn** nhịp thường. Nhịp `09:00:54` mất **28 giây** mới
kết luận, nên trong lúc hỏng hai nhịp cách nhau `28 + 60 = 88` giây. Trần im lặng vì thế là
`60 + 88 ≈ 148` giây, và thư đầu tiên tới sau `2 × 88 ≈ 176` giây — không phải 85/170 như bản trước
ước lượng.

Hai số này là **trần trên**, ứng với kiểu hỏng **treo** (tiến trình còn đó mà không trả lời) — đúng
kiểu quan sát được khi mọi thứ chết thật. Cổng bị từ chối ngay thì phép dò hỏng tức thì, trần rút về
`60 + 60 = 120` giây.

Vì sao vẫn cần "hai nhịp liên tiếp": một lần trượt mạng lẻ không phải sự cố, và thư báo nhầm làm
người nhận tắt thông báo — tức phép báo động tự huỷ chính nó. Bài 121 giây ở trên là cái giá phải
trả cho luật ấy, và nó được trả có chủ ý.

### D10 — Máy chủ chết: không còn là trần cứng, mà là việc chưa làm

`gateway-watch` chạy cùng máy chủ với Gateway. Máy chủ chết, mạng đứt, hoặc Docker daemon chết thì
cả hai cùng chết và **không có thư nào**.

Bản đầu của quyết định này ghi đó là trần không vá được ở tầng này. **Không còn đúng sau D11:** một
bản thứ hai của cùng script, chạy trên máy khác, thấy ngay lớp đó — vì (A) của nó đỏ. Nên đây là
**việc chưa làm**, có đường làm rõ ràng, không phải giới hạn của thiết kế.

Trong lúc chưa có máy thứ hai, thư nhịp tim (D7) bắt được lớp này trong vòng tối đa 24 giờ.

### D11 — Một code, hai bản triển khai, khác nhau ở biến môi trường

Điều kiện duy nhất để code linh hoạt: **không ghim URL nào trong mã**. Hợp đồng chỉ cần hai biến:

```
  WATCH_HTTP        danh sach  ten=url ,  dat = HTTP 200 (kem chuoi mong doi neu can)
  WATCH_STATUS_URL  tuy chon. Co thi doc JSON cua gateway-status va bao cao tung component
```

```
  Ban TRONG   WATCH_HTTP="lb=http://gateway-lb:4000/health/readiness"
              WATCH_STATUS_URL="http://gateway-status:8089/api/status"

  Ban NGOAI   WATCH_HTTP="public=https://apigateway.rangdong.com.vn/lb-health"
              WATCH_STATUS_URL=            <- de trong
```

Bản ngoài để trống một biến. **Không nhánh `if` nào theo môi trường.** Đó là chỗ "một lần code" nằm.

**Lý do thứ hai, phát hiện ngày 17/09, và nó cần ngay cả khi chỉ có MỘT bản:** tên miền
`apigateway.rangdong.com.vn` **chưa tồn tại** — `Non-existent domain` cả trong container lẫn trên
máy host. Bật (A) trên máy phát triển là tự tạo một đích **đỏ mỗi phút** trong khi hệ thống hoàn
toàn khoẻ. Nên `WATCH_HTTP` phải chịu được việc **thiếu hẳn một đích**, và cấu hình mặc định của
máy phát triển MUST NOT chứa (A). Trước phát hiện này, D11 chỉ đứng bằng lý do "hai bản triển
khai"; giờ nó là điều kiện để change chạy được ngay hôm nay.

**"Một code" KHÔNG có nghĩa là chung mạng.** Mạng của compose này là `bridge`, và `bridge` có
`scope=local` — nó sống trong nhân của **một** máy, máy khác không tham gia được. Đo 17/09:

```
token-ledger-dashboard_default   driver=bridge   scope=local   attachable=false
```

Nên hai bản chạy ở hai chỗ hoàn toàn tách rời: khác máy, khác compose, khác mạng. Bản ngoài **không
gọi tên container nào** — nó chỉ gọi tên miền công khai, thứ agent cũng gọi được từ bất cứ đâu. Và
`WATCH_STATUS_URL` để trống **chính là** cách khai "tôi không ở trong mạng đó, đừng bắt tôi đọc
chiều sâu".

Điều khiến cùng một tệp chạy được cả hai nơi: script không biết Docker là gì, nó chỉ nhận một danh
sách URL. Với `urllib`, `http://gateway-status:8089/...` và `https://apigateway.../lb-health` là hai
chuỗi như nhau; khác nhau ở chỗ nào phân giải được, mà đó là chuyện của mạng, không phải của mã.

| | Bản trong | Bản ngoài |
|---|---|---|
| Thấy | instance nào chết, `degraded`, `db` | DNS, TLS, proxy, **và cả máy chết** |
| Mù | DNS, TLS, proxy, máy chết | bên trong Gateway |

Bản ngoài **không cần repo này** — nó cần một tệp `.py` và Python. Script chỉ dùng thư viện chuẩn,
không có gì phải cài; chạy bằng container hay `systemd` đều được.

**Mỗi bản phải tự xưng tên** qua `WATCH_NAME`, vì hai bản cùng gửi vào một hộp thư:

```
  nhan CA HAI thu   ->  hong that, hong sau
  chi ban NGOAI     ->  lop vo hong, hoac CA MAY CHET
  chi ban TRONG     ->  hong ben trong, lop vo van dung
```

Ba tình huống, đọc tiêu đề là biết. Không cần thêm mã — chỉ cần một biến tên.

**Vì sao bản ngoài CỐ Ý nông.** Có ba lối để nó đọc được chiều sâu, và cả ba đều đắt hơn việc chạy
hai bản nhìn hai hướng:

| Lối | Giá phải trả |
|---|---|
| Đổi mạng sang `overlay` + Docker Swarm | dựng lại toàn bộ hạ tầng, chỉ để phục vụ giám sát |
| Đổi bind `127.0.0.1` sang IP LAN, cộng nới `LLM_GATEWAY_ADMIN_CIDR` | mở trang "instance nào đang chết, chết vì sao" ra mạng công ty |
| Dựng VPN hoặc tunnel giữa hai máy | thêm một hạ tầng nữa, mà nó hỏng thì chuông báo giả |

Từ chối cả ba. Bản ngoài có đúng **một** việc mà bản trong không bao giờ làm được — biết khi cả máy
chủ chết — và việc ấy chỉ cần một lượt `GET` vào đường vốn đã công khai.

### D12 — Không mở cổng nào, và đặt trong mạng để không phải nới luật nào

Mọi dịch vụ khác đều mở cửa ra host: `web` 8080, `gateway-lb` 8088, `gateway-status` 8089, `api`
8000, `postgres` 5432, `redis` 6379, `pgadmin` 5050. `litellm-1/2` chỉ `expose`, không ra host.

`gateway-watch` đi xa hơn một bậc: **không `ports`, không cả `expose`**. Nó chỉ gõ cửa người khác;
không ai gọi vào nó. Bề mặt tấn công nó thêm vào là **không**.

"Không được nginx bọc" không phải thiếu sót. Nginx bọc thứ **nhận** request; muốn được bọc thì phải
mở một cổng trước đã — tức tự tạo ra một cửa rồi thuê người canh cái cửa vừa tạo.

Đặt trong mạng Docker thì (B) và (C) gọi thẳng tên container, **không qua nginx**, nên:

- `LLM_GATEWAY_ADMIN_CIDR` giữ nguyên `127.0.0.1/32`
- không thêm một dòng `location` nào
- không đổi bind của dịch vụ nào

Hardening chép khuôn `gateway-status`: `read_only: true`, `cap_drop: [ALL]`,
`no-new-privileges:true`, người dùng không phải root, `init: true`. `read_only` vẫn ghi được tệp
trạng thái nhờ **đúng một** volume ghi được.

Bí mật duy nhất nó giữ là mật khẩu SMTP. Không khoá nhà cung cấp, không master key, không salt key,
không chạm Postgres. Mất nó thì kẻ lấy được... gửi thư.

### D13 — Ba trạng thái, không hai

`gateway-status` đã gộp sẵn thành ba, và luật gộp của nó là:

```
  reachable     ca 4 thanh phan dat
  degraded      lb + route dat, VA it nhat mot proxy dat
  unavailable   con lai
```

Máy trạng thái phải theo ba nấc đó. Hệ quả: luật cũ "đúng hai thư một sự cố" viết lại thành **một
thư cho mỗi lần đổi trạng thái**. `degraded` là tin đáng gửi — một instance chết mà agent không bao
giờ báo — nhưng ở mức nhẹ hơn `unavailable`, và tiêu đề thư phải phân biệt.

**Trần của (B) — SUY LUẬN, chưa chứng minh.** `gateway-status` dùng `/health/liveliness`, nên ở ca
ép IP đổi ngày 17/09 — `litellm-1` khoẻ khi gọi thẳng nhưng LB không gửi lượt nào tới — cả bốn thành
phần đều sống, và `/api/status` **nhiều khả năng** vẫn trả `reachable`.

Phép đo ngày 17/09 dùng `docker stop`, không dựng lại được ca ấy: `docker stop` làm instance **chết
hẳn**, nên (B) bắt được và trả `degraded`. Hai chế độ hỏng khác nhau.

Nên câu này ghi là **CẢNH BÁO, không phải ĐẠT**: trần ấy chưa đo. Muốn chứng minh thì phải ép IP đổi
đúng cách task 0.3 của change `keep-the-load-balancer-pointed-at-live-instances` đã làm. Bản vá
`resolve` đã chặn nguyên nhân, nên đây là trần của phép đo chứ không phải lỗ hổng đang mở.

## Risks / Trade-offs

| Rủi ro | Xử |
|---|---|
| Lớp "sống mà hỏng" theo từng khoá không được phủ | Trần đã biết, D1; lối đi là chuông thứ hai đọc kết cục thật |
| Canh gác là điểm hỏng đơn cho mọi báo động | Thư nhịp tim, D7 |
| Máy chủ chết thì im lặng | Bản ngoài, D11; trong lúc chưa có thì nhịp tim bắt trong 24 giờ |
| Sự cố ngắn không được báo | Định lượng ở D9 |
| Mất con số "bao nhiêu lượt đi đường thẳng" | Log giữ nguyên, thư trỏ tới, D8 |
| **(A) không vòng lại được (hairpin NAT)** | **Phải đo trước**, task 0.5; vá bằng `extra_hosts` |
| `gateway-status` dựng lại → báo động giả | (C) làm trọng tài, D3; tách hẳn hai loại thư |
| Thư rơi vào thư rác | Nghiệm thu đòi người nhận xác nhận |

## Migration

| | Trước | Sau |
|---|---|---|
| Ai gửi thư | agent CRM, chỉ khi đang chạy lô | `gateway-watch`, mọi lúc |
| Phủ được mấy agent | 1 / 8 | 8 / 8 |
| Gateway chết lúc 2 giờ sáng | không ai biết | có thư |
| Một instance chết | **không ai biết** | `degraded`, có thư |
| Agent đổi đường | thư + log | log; thư nói khoảng thời gian (D8) |
| Gửi thư hỏng | `try/except` trong `llm.py` | không có việc chính nào để hỏng |
| Lớp "sống mà hỏng" | không phủ | vẫn không phủ |

**Việc gỡ thư khỏi agent nằm NGOÀI change này.** Chốt 17/09: change này chỉ làm phần gửi thư của
watcher; **leader** gỡ mã gửi thư trong agent sau, khi watcher đã chạy và đã được tin. Ở đây chỉ để
lại ghi chú bàn giao (`tasks.md` mục 7).

Thứ tự vẫn giữ nguyên và phải nói rõ với người gỡ: dựng `gateway-watch` và nghiệm thu **xong** — tức
người nhận đã xác nhận thấy cả thư sự cố lẫn thư nhịp tim — rồi mới gỡ. Gỡ trước là tự tạo một
khoảng không có chuông nào.

**Giai đoạn chuyển tiếp: một sự cố sinh thư từ cả hai nguồn.** Đó là dự tính, không phải hỏng, và
trong giai đoạn ấy nó còn có lợi — thư của CRM mang con số **bao nhiêu lượt đã đi đường thẳng**, thứ
D8 nói watcher không biết được. Nghĩa là cách xử (c) của D8 chỉ thực sự cần từ lúc leader gỡ xong;
trước đó con số ấy vẫn tới thẳng hộp thư. Tài liệu phải nói điều này để người nhận không tưởng chuông
đang gửi trùng vì lỗi.
