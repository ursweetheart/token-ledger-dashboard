## 0. Chứng minh khoảng trống có thật, và đo hai thứ có thể lật thiết kế

> **Topology update (18/09/2026):** the completed measurements below used the
> former separate `gateway-status` service. Current runtime bundles that
> collector into `gateway-lb` and uses `gateway-lb:8089` internally.

Không dựng chuông trước rồi tin là đã có chuông.

- [x] 0.1 Đếm chính xác bao nhiêu agent có mã gửi thư khi đổi đường. Tìm theo `_notify`,
      `send_alert`, `NotificationService` trên cả tám repo agent. **Kỳ vọng: 1/8.** Ghi số thật vào
      `design.md` mục Context — ra khác 1 thì phần Why của proposal phải viết lại theo số đo

      **Đo 17/09/2026. Chỉ 3/8 repo có trên máy này**, nên kết quả là **một phần**, không phải toàn bộ.

      | Repo | Có mã gửi thư | Loại | Có đổi đường |
      |---|---|---|---|
      | `CRM-Classification-Pipeline` | có | **thư đổi đường** (`llm.py:263`, `:279`) + thư lỗi lô | có |
      | `dms-feedback-classification` | có | **chỉ thư lỗi lô** (`notification.py::_build_error_html`) | không |
      | `E_Commerce_crawling_analysis` | không | — | không |
      | Ralli, Law Insight, 3 repo còn lại | **chưa kiểm** | — | — |

      **Bẫy đã tránh:** `grep` thô theo `NotificationService`/`smtplib` cho ra "6 tệp" ở **cả** CRM lẫn
      DMS, trông như 2/8. Đếm như vậy là **sai phép đếm**: DMS gửi thư khi *lô hỏng*, không phải khi
      *đổi đường*. Hai việc khác hẳn, và chỉ việc sau là thứ change này chuyển đi.

      **Phát hiện thật:** `dms/metrics.py:291` có `_consecutive_failures >= 3` — nhìn giống ngưỡng
      đổi đường của CRM, nhưng nó đếm **tệp xử lý hỏng**, chỉ sinh chuỗi `health_status`, không gửi
      thư và không đổi đường. `dms/gemini_client.py:252` còn ghi rõ nó **cố ý không có fallback**.

      **Kết luận:** trong phần kiểm được, đúng **1 repo** có thư đổi đường. Con số 1/8 của proposal
      **chưa bị bác**, nhưng cũng **chưa được chứng minh đủ** — còn 5 repo phải kiểm trên máy khác
      trước khi coi là đã đo xong.
- [x] 0.2 **Đo rằng `/lb-health` nói dối.** Ép `litellm-1` ra khỏi vòng chia tải bằng đúng cách task
      0.3 của change `keep-the-load-balancer-pointed-at-live-instances` đã làm. Cùng lúc đó gọi
      `/lb-health`, `/health/readiness`, và `/api/status`. Ghi cả ba câu trả lời

      **Kỳ vọng: cả ba đều xanh.** Đây là bằng chứng cho D4 và cho trần của (B) ở D13. Ra khác kỳ
      vọng là **phát hiện thật** — ghi lại, đừng sửa kỳ vọng cho vừa

      **Đo 17/09/2026 bằng cách RẺ HƠN — `docker stop litellm-1` thay vì ép IP đổi.** Hai cách sinh
      hai chế độ hỏng khác nhau; xem "còn treo" ở cuối mục này.

      ```
      lb-health        :  b'lb-ok\n'                                        <- XANH
      health/readiness :  b'{"status":"healthy","db":"connected"}'          <- XANH
      api/status       :  degraded
                              lb      reachable    Liveness check passed.
                              proxy1  UNREACHABLE  Liveness check timed out.
                              proxy2  reachable    Liveness check passed.
                              route   reachable    Liveness check passed.
      ```

      **Kỳ vọng SAI một nửa, và phát hiện thật nằm ở chỗ đó.** Kỳ vọng ghi "cả ba đều xanh". Thực
      tế **hai** xanh, **một** bắt được.

      | Đích | Một instance chết | Kết luận |
      |---|---|---|
      | `/lb-health` | `lb-ok` — xanh | vô dụng, đúng như D4 nói |
      | `/health/readiness` (C) | `healthy` — **xanh** | nó đi qua LB, LB đẩy sang instance còn sống |
      | `/api/status` (B) | **`degraded`**, chỉ đích danh `proxy1` | **chỉ mình nó thấy** |

      **Hệ quả: (B) KHÔNG thừa so với (C).** Trước phép đo này, D3 biện minh cho (B) bằng lý do
      "chiều rộng". Giờ có bằng chứng cứng hơn: mất một nửa năng lực xử lý thì **(C) cũng mù**, y
      như `/lb-health`. Bỏ (B) đi là mất hẳn khả năng thấy `degraded` — đúng cái ca mà agent cũng
      không bao giờ báo.

      **Quan sát phụ, chưa truy:** `proxy1` báo `Liveness check timed out.` chứ không phải
      `Service name could not be resolved.`. Tức DNS của Docker vẫn trả địa chỉ cũ sau khi container
      dừng, và kết nối treo tới khi hết hạn 2,5 giây. Không ảnh hưởng thiết kế, nhưng nó nghĩa là mỗi
      nhịp dò (B) sẽ **chậm thêm ~2,5 giây** khi có instance chết — cần nhớ khi đặt `timeout` cho
      chính watcher ở task 1.5

      **CÒN TREO, chưa đo:** ca ép IP đổi của 17/09 — `litellm-1` **khoẻ** nhưng LB không gửi lượt
      nào tới. `docker stop` không dựng lại được ca đó. Suy luận ở D13 là `/api/status` sẽ trả
      `reachable` (cả bốn thành phần đều sống), tức **(B) cũng mù ở ca ấy**. Đó là **suy luận, chưa
      chứng minh** — D13 phải ghi đúng như vậy
- [x] 0.3 Xác nhận `/health/readiness` gọi được **không cần khoá** và **không sinh dòng nào** trong
      sổ. Đếm `LiteLLM_SpendLogs` trước và sau 20 lượt dò. **Kỳ vọng: chênh 0.** Lệch khác 0 lật đổ
      D1 — dừng lại, báo, đừng dò tiếp

      **Đo 17/09/2026 — ĐẠT, đúng kỳ vọng.**

      ```
      LiteLLM_SpendLogs truoc :  567
      20 luot GET /health/readiness, KHONG kem Authorization  ->  20/20 tra 200
      LiteLLM_SpendLogs sau   :  567        chenh = 0
      ```

      Hai điều được chứng minh cùng lúc: (C) **không cần khoá**, và (C) **không sinh dòng nào**
      trong sổ. Đây là nền của D1 — nếu lệch khác 0 thì toàn bộ lập luận "dò miễn phí không bẩn sổ"
      sụp, và change phải viết lại
- [x] 0.4 Xác nhận `/api/status` gọi được từ một container khác khi đặt `Host: localhost`, và **bị
      403 khi không đặt**. `server.js` chặn cứng theo `Host`; không biết trước thì sẽ mất buổi để mò

      **Đo 17/09/2026 — ĐẠT, đúng kỳ vọng, cả hai chiều.**

      ```
      CO  Host: localhost  ->  200   status=reachable   components=4
      KHONG dat Host       ->  403   "Forbidden."
      ```

      Gọi thẳng `gateway-status:8089` từ container khác **không cần** đi qua nginx và **không cần**
      nới `LLM_GATEWAY_ADMIN_CIDR` — đúng như D12 khẳng định. Chỉ cần đặt `Host: localhost`, giống
      hệt điều `nginx.conf:135` đang làm (`proxy_set_header Host localhost`).

      Và `components=4` xác nhận (B) trả đủ bốn thành phần `lb` / `proxy1` / `proxy2` / `route`
- [x] 0.5 **Đo hairpin — thứ có thể làm (A) vô dụng.** Từ trong một container trên mạng này, gọi
      `https://${LLM_GATEWAY_DOMAIN}/lb-health`.

      | Kết quả | Nghĩa |
      |---|---|
      | trả `lb-ok` | (A) dùng được như thiết kế |
      | không kết nối / timeout | router không cho vòng lại → **(A) sẽ đỏ mỗi phút dù hệ thống khoẻ** |

      Hỏng thì vá bằng `extra_hosts` trỏ tên miền vào IP LAN của máy chủ, rồi **đo lại**. Vẫn hỏng
      thì (A) chỉ chạy được ở bản ngoài (D11), và phải ghi điều đó vào `design.md` trước khi viết mã

      **Đo 17/09/2026 — kết quả KHÁC hẳn hai khả năng đã lường trước.**

      ```
      trong container:  DNS apigateway.rangdong.com.vn -> gaierror [Errno -2]
      tren may host:    nslookup                       -> Non-existent domain
      .env:             khong khai LLM_GATEWAY_DOMAIN  -> dung mac dinh cua .env.example
      ```

      **Không phải hairpin. Tên miền chưa tồn tại.** Nên (A) hiện **không đo được**, và quan trọng
      hơn: nếu bật (A) trên máy này thì nó sẽ **đỏ mỗi phút** — báo động giả vĩnh viễn.

      Khớp với task 0.6: không agent nào dùng tên miền, cả hai đều gọi `http://gateway-lb:4000`.
      Đường public **chưa dựng**, nó là đường của tương lai.

      **Hệ quả bắt buộc cho thiết kế — (A) phải TUỲ CHỌN, không mặc định:** `WATCH_HTTP` phải chịu
      được việc thiếu hẳn một đích, đúng cách `WATCH_STATUS_URL` chịu được việc để trống. Trên máy
      phát triển, cấu hình mặc định **MUST NOT** chứa (A). Đây là lý do thứ hai cho D11 — trước
      đó D11 chỉ đứng bằng lý do "hai bản triển khai"; giờ nó cần ngay cả khi chỉ có một bản.

      **Vớt lại được phần đo được của (A): luật `Host` của D4, đo trực tiếp bằng cách giả header.**

      | Đường | `Host` = tên miền | `Host` = `gateway-lb` |
      |---|---|---|
      | `/lb-health` | `200  lb-ok` | `200  lb-ok` |
      | `/edge-health` | `200  edge-ok` | `200  edge-ok` |
      | `/health/readiness` | **404** | `200  {"status":"healthy","db":"connected"}` |
      | `/health/liveliness` | **404** | `200  "I'm alive!"` |

      D4 **khớp từng dòng**: qua tên miền chỉ còn hai endpoint `return 200` cứng; chiều sâu bị chặn
      đúng như `if ($host = ${LLM_GATEWAY_DOMAIN}) { return 404; }` khai. Và `readiness` trả đúng
      `db: connected`, **không lộ số phiên bản** — nên (C) không phải một đường rò thông tin
- [x] 0.6 Ghi lại đường agent thật đi sau khi chuyển hết sang tên miền public: có TLS không, qua
      reverse proxy nào, cổng nào. Đọc cấu hình agent thật, không đoán

      **Đo 17/09/2026 — việc chuyển sang tên public CHƯA xảy ra.** Cả hai agent kiểm được đều đang
      gọi bằng **tên container nội bộ**:

      ```
      CRM   .env.example:42       GEMINI_GATEWAY_BASE_URL=http://gateway-lb:4000
      DMS   gemini_client.py:85   default                 http://gateway-lb:4000
      ```

      Không repo agent nào nhắc tới `apigateway.rangdong.com.vn`. Không TLS, không reverse proxy,
      không tên miền — agent nằm **trong cùng mạng Docker** và gọi thẳng.

      **Hệ quả cho D3, phải ghi rõ vì nó đổi trọng tâm hai phép dò:**

      | | Hôm nay | Sau khi chuyển sang tên public |
      |---|---|---|
      | (C) `gateway-lb:4000` | **chính là đường agent đi** | thành phép dò nội bộ |
      | (A) tên miền public | đường của **tương lai**, chưa ai dùng | thành đường agent đi |

      Nên (A) hiện **chưa** phủ đường agent nào — nó phủ đường sắp tới. Vẫn giữ (A) trong change
      này: dựng sẵn thì lúc chuyển đổi không có khoảng mù, và nó là phép dò duy nhất chạy được ở
      bản ngoài (D11). Nhưng MUST NOT mô tả nó như "đang canh đường agent" cho tới khi việc chuyển
      đổi xong — đó là điều tài liệu ở task 8.1 phải nói đúng.

## 1. Viết `scripts/watch_gateway.py`

Viết hết rồi mới chạy. Viết một nửa rồi chạy thử là cách tốn thời gian nhất.

- [x] 1.1 Khung vòng lặp theo khuôn `scripts/refresh_gateway.py`: `--every N`, log qua `logging`
      theo `LOG_LEVEL`, **dò trước ngủ sau** để nhịp đầu tiên chạy ngay lúc container lên (D6)
- [x] 1.2 **Bốn cờ bắt buộc, viết ngay từ đầu.** Không có chúng thì mỗi vòng tự soát mất vài phút và
      sẽ bỏ cuộc giữa chừng:

      | Cờ | Tác dụng |
      |---|---|
      | `--once` | chạy một nhịp rồi thoát |
      | `--dry-run` | in thư ra màn hình, **không gửi** |
      | `--fake-state X` | ép trạng thái `reachable`/`degraded`/`unavailable` |
      | `--fake-status-down` | ép riêng nhánh "không đọc được `/api/status`" |
- [x] 1.3 **Đích dò đọc từ `WATCH_HTTP` và `WATCH_STATUS_URL`** (D11). MUST NOT ghim URL nào trong
      mã. `WATCH_STATUS_URL` trống thì bỏ qua (B), không lỗi — đó là cách bản ngoài chạy
- [x] 1.4 Đọc `/api/status`: đặt `Host: localhost`, phân tích `status` và mảng `components`. Chịu
      được JSON thiếu trường, sai kiểu, hoặc thân rỗng
- [x] 1.5 **Bắt buộc có `timeout` ở mọi lượt gọi.** Một lượt dò treo là một chuông không bao giờ
      kêu được
- [x] 1.6 Máy trạng thái **ba nấc** (D13). Hai nhịp hỏng liên tiếp mới đổi sang xấu; một nhịp tốt là
      phục hồi
- [x] 1.7 **Nhánh riêng cho "không đọc được `/api/status`"** — MUST NOT coi là "Gateway chết". Dùng
      (C) làm trọng tài:

      ```
      (B) im
          ├─ (C) dat   ->  "khong doc duoc trang thai, LB van tra loi"
          └─ (C) hong  ->  "GATEWAY HONG"
      ```

      Thiếu nhánh này thì mỗi lần `gateway-status` dựng lại là một thư báo động giả
- [x] 1.8 Tệp trạng thái JSON trong `var/`. Ghi ra tệp tạm rồi đổi tên. Đọc bằng `.get()`, chịu được
      tệp rỗng và tệp hỏng — coi như "đang khoẻ" rồi chạy tiếp (D5). Thêm vào `.gitignore`
- [x] 1.9 Mẫu thư, tiêu đề mang `WATCH_NAME` và mức độ:
      - `unavailable` — thời điểm, bảng chẩn đoán (A)/(B)+(C) của D3, câu lỗi thật từng đích
      - `degraded` — instance nào chết, và câu nói rõ Gateway **vẫn đang phục vụ**
      - phục hồi — bắt đầu, kết thúc, độ dài, cộng câu trỏ tới log `[FALLBACK]` của agent (D8)

      Thư khai UTF-8. Không khai thì dấu tiếng Việt tới nơi thành ký tự lạ
- [x] 1.10 Thư nhịp tim mỗi ngày, giờ cố định (D7): số nhịp đã dò, số nhịp hỏng
- [x] 1.11 Gửi thư bọc trong `try/except` rộng, log mức lỗi, **không bao giờ thoát**. Mật khẩu SMTP
      đọc từ biến môi trường, MUST NOT in ra log kể cả trong câu ngoại lệ

## 2. Tự soát — trước khi chạy lần đầu

**Bắt buộc.** Đọc lại toàn bộ và tìm lỗi bằng mắt. Máy chỉ báo loại lỗi làm chương trình dừng; loại
nguy hiểm hơn là loại chạy trót lọt rồi im lặng sai.

- [x] 2.1 **Ngoại lệ mạng bắt đủ chưa.** `URLError`, `HTTPError`, `socket.timeout`,
      `ConnectionResetError`, và lỗi TLS của (A). Sót một cái là container chết lặng lẽ — đúng chế
      độ hỏng tệ nhất của change này
- [x] 2.2 **Mọi lượt gọi mạng đều có `timeout`.** Không sót lượt nào
- [x] 2.3 **Phân tích JSON của (B) không được sập** vì thiếu khoá. Dùng `.get()`, không `[...]`
- [x] 2.4 **Phép tính độ dài sự cố.** Không so số thực bằng `==`. Xử được ca mốc bắt đầu không có
      trong tệp trạng thái
- [x] 2.5 **Múi giờ.** Mọi mốc trong thư là giờ Việt Nam và ghi rõ trong thân thư. Container chạy
      UTC là mặc định
- [x] 2.6 **Ghi tệp trạng thái không để lại tệp dở.** Tệp tạm rồi đổi tên
- [x] 2.7 **Không tệp nào mở mà không đóng.** Dùng `with`
- [x] 2.8 **Thông tin đăng nhập không lọt vào log**, kể cả trong câu ngoại lệ khi gửi hỏng

## 3. Chạy lát mỏng — mỗi bước vài giây

Bước 3.3 là bước dễ sai nhất, và đọc mã không bắt được.

- [x] 3.1 `--once --dry-run`, hệ thống khoẻ → **kỳ vọng: im lặng**
- [x] 3.2 `--once --dry-run --fake-state unavailable` → **kỳ vọng: in ra một thư "Gateway hỏng"**
- [x] 3.3 Lặp lại **ngay** lệnh 3.2 → **kỳ vọng: IM LẶNG.** Đã báo rồi thì không báo lại
- [x] 3.4 `--once --dry-run --fake-state degraded` sau khi đang `unavailable` → **kỳ vọng: một thư
      đổi trạng thái**, tiêu đề khác thư 3.2
- [x] 3.5 `--once --dry-run` trở lại khoẻ → **kỳ vọng: thư "phục hồi"** kèm độ dài và câu trỏ tới
      log agent
- [x] 3.6 `--once --dry-run --fake-status-down` khi (C) vẫn đạt → **kỳ vọng: thư nói "không đọc được
      trạng thái", KHÔNG nói "Gateway hỏng"**
- [x] 3.7 Tệp trạng thái rỗng, rồi JSON hỏng → **kỳ vọng: chạy tiếp, không sập**
- [x] 3.8 Xoá tệp trạng thái giữa lúc đang hỏng, chạy lại → **kỳ vọng: không thành vòng gửi lặp**
- [x] 3.9 `WATCH_STATUS_URL` để trống (giả lập bản ngoài) → **kỳ vọng: chạy bằng mỗi `WATCH_HTTP`,
      không lỗi.** Đây là phép kiểm cho D11, và nó phải chạy được **trước** khi có máy thứ hai
- [x] 3.10 Ép một đích trỏ vào cổng đóng → **kỳ vọng: nhận ra là hỏng, không ném ngoại lệ ra ngoài**
- [x] 3.11 Ép máy chủ thư sai, **không** `--dry-run` → **kỳ vọng: log mức lỗi, vòng lặp chạy tiếp**

**Phân loại mỗi lần hỏng, đừng nhầm loại:**

| Triệu chứng | Loại | Làm gì |
|---|---|---|
| Script sập, sai kiểu, `KeyError` | LỖI SCRIPT | sửa mã |
| Một sự cố ra hai thư | LỖI SCRIPT | sửa mã |
| Gửi thư ném ngoại lệ ra ngoài | LỖI SCRIPT | sửa mã, spec cấm |
| Dò thật thấy Gateway đáp chậm bất thường | **PHÁT HIỆN THẬT** | ghi số, **không nới `timeout`** |
| `/health/readiness` sinh dòng trong sổ | **PHÁT HIỆN THẬT** | D1 sai, dừng và báo |
| `/api/status` trả `reachable` khi một instance nhận 0 lượt | **PHÁT HIỆN THẬT** | trần của D13, ghi số |
| (A) đỏ mà (B)(C) xanh | **PHÁT HIỆN THẬT** | hairpin hoặc lớp ngoài — phân biệt bằng task 0.5 |

**Luật tuyệt đối:** phép kiểm kêu mà cách xử là nới ngưỡng, thêm dung sai, hay bọc `try/except` cho
nó im — dừng lại. Chỉ sửa phép kiểm khi chứng minh được **phép kiểm sai**.

### Kết quả mục 1–3, đo 17/09/2026

`scripts/watch_gateway.py` — 11 bài lát mỏng chạy trên hệ thống thật (`gateway-lb` và
`gateway-status` đang chạy), gọi qua cổng đã publish `127.0.0.1:8088` / `:8089`.

| Bài | Kỳ vọng | Kết quả |
|---|---|---|
| 3.1 khoẻ | im lặng | ĐẠT (kèm một thư nhịp tim — xem phát hiện 1) |
| 3.2 `unavailable` | một thư, sau **hai** nhịp | ĐẠT: nhịp 1 im, nhịp 2 gửi |
| 3.3 lặp lại | im lặng | ĐẠT |
| 3.4 `degraded` | một thư, tiêu đề khác | ĐẠT: `WARN` thay vì `DOWN` |
| 3.5 phục hồi | một thư, **ngay nhịp đầu** | ĐẠT, kèm độ dài và câu trỏ `[FALLBACK]` |
| 3.6 `--fake-status-down`, (C) đạt | "không đọc được trạng thái" | ĐẠT, nói rõ **không phải** sự cố Gateway |
| 3.7 tệp trạng thái hỏng / rỗng | chạy tiếp | ĐẠT, cảnh báo rồi coi như đang khoẻ |
| 3.8 xoá tệp giữa sự cố | không thành vòng gửi lặp | ĐẠT: 1 → 1 → 0 → 0, hội tụ |
| 3.9 `WATCH_STATUS_URL` trống | chạy bằng mỗi `WATCH_HTTP` | ĐẠT — đây là phép kiểm cho D11 |
| 3.10 cổng đóng | nhận ra hỏng, không ném ngoại lệ | ĐẠT |
| 3.11 máy chủ thư sai | log lỗi, không chết | ĐẠT, mã thoát 0 |

`tools/check_english_names.py scripts/watch_gateway.py` → **0 vi phạm**.
Mật khẩu SMTP xuất hiện trong log: **0 lần**.

**Phát hiện 1 — nhịp tim bắn ngay lúc khởi động, và ĐÓ LÀ ĐÚNG; chữ trong design mới sai.**
Bài 3.1 chạy lúc 22:35 và nhận ngay một thư nhịp tim. Mã đang theo luật "giờ hiện tại ≥
`WATCH_HEARTBEAT_HOUR` và hôm nay chưa gửi", chứ không phải "đúng giờ X".

Đã cân nhắc đổi sang `==` cho khớp chữ "giờ cố định" ở D7, và **từ chối**: nếu chỗ canh được dựng
lại trong đúng giờ ấy thì cả ngày mất thư nhịp tim — mà vắng nhịp tim lại chính là tín hiệu ta bảo
người vận hành hiểu là "chỗ canh đã chết". Tức sửa cho đúng chữ sẽ **tự tạo báo động giả**.

Giữ mã, sửa chữ ở D7. Và gửi ngay lúc khởi động còn có lợi: nó chứng minh đường thư chạy được ngay
sau khi triển khai, không phải chờ tới hôm sau.

**Phát hiện 2 — tiêu đề thư ghép máy móc từ tên trạng thái thì đọc lướt dễ hiểu ngược.**
Bản đầu sinh ra `[trong] WARN - Gateway status_unreadable`, đọc nhanh trông y như Gateway hỏng,
trong khi thân thư nói ngược lại. Người nhận đọc tiêu đề **trước**. Đã thay bằng bảng `SUBJECT`
viết thành câu: `Khong doc duoc trang thai (Gateway van tra loi)`.

**Phát hiện 3 — mất tệp trạng thái thì tốn thêm một thư nhịp tim, không chỉ một thư sự cố.**
Bài 3.8: nhịp 1 gửi nhịp tim (vì `heartbeat_date` mất theo tệp), nhịp 2 gửi thư sự cố, nhịp 3 trở đi
im. Hội tụ, chấp nhận được — nhưng phải ghi ra, vì người nhận sẽ thấy một thư nhịp tim lạc giờ.

**Báo động hụt của chính tôi, ghi lại để không ai lặp:** `check_english_names.py` in
`0 violations in 0 files`, và tôi đọc thành "không quét tệp nào". Đọc mã ở dòng 217 thì con số thứ
hai là **số tệp CÓ vi phạm**, không phải số tệp đã quét. Tức nó đã chạy và đã sạch.

## 4. Dựng dịch vụ

- [x] 4.1 Thêm `gateway-watch` vào `docker-compose.yml`, profile `gateway`, chép khuôn
      `ledger-refresh` (D6): `image: token-ledger-tools:local`, `restart: unless-stopped`,
      `logging: *logging`, `init: true`, `PYTHONIOENCODING=utf-8`
- [x] 4.2 **Không `ports`, không `expose`** (D12). Ghi chú thích nói rõ vì sao, để lần sau không ai
      "sửa thiếu sót" này
- [x] 4.3 Hardening chép từ `gateway-status`: `read_only: true`, `cap_drop: [ALL]`,
      `security_opt: [no-new-privileges:true]`, người dùng không phải root, và **đúng một** volume
      ghi được cho `var/`
- [x] 4.4 **Không đặt `healthcheck`**, cùng lý do `ledger-refresh` không đặt. Ghi chú thích
- [x] 4.5 Khai biến vào `.env.example`: `WATCH_NAME`, `WATCH_EVERY_SECONDS=60`, `WATCH_HTTP`,
      `WATCH_STATUS_URL`, thông tin SMTP, người nhận, giờ nhịp tim. Giá trị thật ở `.env`, và `.env`
      nằm trong `.gitignore`
- [x] 4.6 **Xác nhận không nới gì:** `git diff` phải KHÔNG chạm `LLM_GATEWAY_ADMIN_CIDR`, không đổi
      bind của dịch vụ nào, không thêm dòng `location` nào trong `nginx.conf`. Đây là D12, và nó chỉ
      giữ được nếu có người kiểm
- [x] 4.7 `docker compose config` đạt. Dựng lên, xem log, xác nhận nhịp dò đúng bằng
      `WATCH_EVERY_SECONDS` — bằng dấu thời gian trong log, không bằng suy luận

### Kết quả mục 4, đo 17/09/2026

`docker compose --profile gateway config` → **đạt**.

**Task 4.6 — kiểm bằng `git diff` rằng không nới biên giới nào.** Đây là phép kiểm mà D12 chỉ giữ
được nếu có người chạy:

```
tep bi doi          .env.example, docker-compose.yml   (KHONG co nginx.conf)
LLM_GATEWAY_ADMIN_CIDR   khong doi gia tri -- chi mot dong CHU THICH noi ro la khong noi
ports / *_BIND           khong dong nao bi doi
docker/gateway/*         khong cham
```

**Quyết định lúc dựng, ghi lại vì nó là một góc bị cắt có chủ ý:** `gateway-watch` chạy bằng
**root**, theo đúng thiết kế của image `tools`. Đổi UID thì volume `watchstate` do root tạo sẽ không
ghi được, phải thêm bước `chown` lúc khởi tạo. Đã bù bằng `read_only: true`, `cap_drop: [ALL]`,
`no-new-privileges:true`, `tmpfs` cho `/tmp`, và **không cổng nào**. Đã đánh dấu `ponytail:` trong
`docker-compose.yml` kèm đường nâng cấp.

**Phát hiện 4 — gửi thư hỏng thì thư ấy MẤT HẲN, không thử lại.** Lần dựng đầu tiên chưa khai SMTP,
nên log ra đúng dòng này rồi chạy tiếp:

```
2026-09-17 15:52:39  INFO   probe -> reachable (current reachable)
2026-09-17 15:52:39  ERROR  Mail not sent: SMTP_HOST or SMTP_TO is empty
```

Hành vi khớp spec ("gửi hỏng thì ghi log rồi chạy tiếp"), nhưng phải nói rõ hệ quả: `commit()` đổi
trạng thái **dù thư có đi được hay không**, nên thư hỏng là một báo động **biến mất luôn**.

Đã cân nhắc thử lại ở nhịp sau và **từ chối**: mỗi lần thử `smtplib` chờ tới 30 giây, nên máy chủ
thư chết một giờ sẽ làm chính vòng lặp dò đứng — tức mất luôn việc canh để cố cứu việc báo. Đổi một
thứ hỏng lấy hai thứ hỏng.

Cái vá đúng đã có sẵn và không tốn dòng mã nào: **thư nhịp tim**. Đường thư hỏng thì nhịp tim cũng
không tới, và vắng nhịp tim đã được định nghĩa là tín hiệu. Tài liệu ở task 8.2 phải nói cả hai
nghĩa của sự vắng mặt ấy: chỗ canh chết, **hoặc** đường thư chết.

**Ghi kèm — log của container chạy giờ UTC** (`15:52` UTC = `22:52` giờ VN). Đúng như chú thích
trong mã đã lường: mọi mốc **trong thư** đổi sang giờ VN, còn dấu thời gian của `logging` thì giữ
giờ container. Hai chỗ khác nhau là có chủ ý, không phải lệch.

## 5. Nghiệm thu bằng cách phá thật

**Bẫy bắt được ngay bài đầu tiên, 17/09/2026 — và nó đáng ghi hơn cả bài kiểm.**

Từ máy host gửi thư được. Trong container thì `Mail failed (SMTPSenderRefused)`. Env trong container
kiểm ra **đủ cả bảy biến, đúng độ dài**. Triệu chứng trông y hệt sai mật khẩu.

Nguyên nhân thật:

```
trong container:  SMTP_USER      SMTP_STARTTLS     <- doc khong ra -> khong goi server.login()
tren dia:         SMTP_USERNAME  SMTP_USE_TLS      <- da doi ten theo CRM
```

`docker/tools.Dockerfile` **nướng `scripts/` vào image lúc build**. Sửa script mà không build lại
thì container vẫn chạy bản cũ, **im lặng** — không một dòng log nào nói "tôi đang chạy mã cũ". Gmail
từ chối người gửi vì không có bước đăng nhập, và lỗi ấy lại trỏ nhầm hướng sang mật khẩu.

Cùng cái bẫy áp cho `ledger-refresh`, vì nó dùng chung image. Phải ghi vào tài liệu vận hành: **sửa
`scripts/*.py` xong thì `--build`, không thì container chạy bản cũ.**

Cách phát hiện, giữ lại vì nó rẻ và chắc — so mã **bên trong** container với mã trên đĩa:

```bash
docker compose --profile gateway exec -T gateway-watch \
    grep -oE 'SMTP_(USER|USERNAME)' scripts/watch_gateway.py | sort -u
grep -oE 'SMTP_(USER|USERNAME)' scripts/watch_gateway.py | sort -u
```

**Bẫy thứ hai, và đây là LỖI THIẾT KẾ thật, không phải lỗi quy trình.**

Dừng `litellm-1` xong, chỗ canh báo `unavailable` — kỳ vọng là `degraded`. Một nhịp dò mất **12
giây**. Nhưng đo lại ngay sau đó thì (C) trả `healthy` **6/6 trong 0,0 giây** và (B) trả `degraded`,
tức đáp án đúng là `degraded`.

Nguyên nhân: hạn thời gian của chỗ canh đặt **bằng đúng** hạn kết nối của Gateway.

```
nginx.conf   proxy_connect_timeout 10s   proxy_next_upstream_tries 2
             -> mot request co the mat toi 20 giay moi ra ket qua DUNG,
                vi nginx dang tu chuyen sang instance con song
             + max_fails=2 fail_timeout=30s  -> cua so ay keo dai ~30 giay sau khi instance chet

watcher      WATCH_TIMEOUT_SECONDS = 10  -> BO CUOC dung luc nginx dang cuu
```

Hậu quả nếu để nguyên: một instance chết sẽ sinh **hai** thư cho **một** sự cố — `DOWN` trước, rồi
`WARN` sau khi nginx loại xong instance hỏng. Sai mức độ, và đúng loại nhiễu làm người nhận tắt
thông báo.

Sửa: `WATCH_TIMEOUT_SECONDS` mặc định **10 → 25**. Luật là hạn của chỗ canh phải **lớn hơn**
`proxy_connect_timeout × proxy_next_upstream_tries` của Gateway, cộng một khoảng dư. Đã ghi lý do
vào cả `scripts/watch_gateway.py`, `docker-compose.yml` và `.env.example` — con số này trông tuỳ
tiện nếu không có câu giải thích đi kèm.

**Vì sao lát mỏng ở mục 3 không bắt được:** ở đó mọi đích hoặc đạt hẳn, hoặc hỏng hẳn (cổng đóng →
từ chối ngay). Cửa sổ "đang chuyển tiếp, chậm nhưng rồi sẽ đúng" chỉ tồn tại khi phá **thật**. Đây
đúng là thứ mục 5 sinh ra để tìm.

**Bẫy thứ ba — nâng hạn lên 25 giây VẪN ra `unavailable`. Nguyên nhân không ở mã của change này.**

Đo từng đích cùng lúc, bằng chính hàm của watcher:

```
(C) /health/readiness qua LB   ->  DAT
(B) /api/status                ->  unavailable
        lb      reachable    Liveness check passed.
        proxy1  unreachable  Liveness check timed out.
        proxy2  reachable    Liveness check passed.
        route   UNREACHABLE  Liveness check timed out.     <- thu pham
```

`tools/gateway-status/server.js` dò `route` với hạn **2,5 giây**, và `createMonitor` **chặn cứng**
không cho khai quá 2500ms:

```js
if (!Number.isFinite(timeoutMs) || timeoutMs < 1 || timeoutMs > 2500) throw new RangeError(...)
```

Nên nó dính đúng cái bẫy vừa sửa ở watcher, mà lại **không nâng hạn lên được**. Một instance chết
thì `route` chập chờn `unreachable` dù Gateway vẫn trả lời bình thường, và `/api/status` tụt thẳng
xuống `unavailable`.

**Không sửa mã của `gateway-status`** — ngoài phạm vi change này, và đó là mã người khác vừa viết.
Sửa **cách gộp** thay vào đó, và cách gộp mới hoá ra đúng hơn về bản chất:

> **Đích HTTP quyết định có hỏng hay không; `/api/status` chỉ quyết định hỏng tới đâu.**

Một lượt gọi thật đi xuyên qua load balancer và trả về đúng thân thì tin cậy hơn một phép dò tổng
hợp bị bó hạn thời gian. Nên chỉ còn **một** đường dẫn tới `unavailable`: lượt gọi thật cũng không
xong. `/api/status` vẫn cần — nó là thứ duy nhất nói được instance nào chết — chỉ là nó không còn
quyền tuyên bố "chết hẳn".

Nếu giữ nguyên cách gộp cũ thì hậu quả là gọi người dậy lúc nửa đêm cho một sự cố mà agent **vẫn
gọi được**. Sai theo hướng tệ nhất.

**Việc cần báo cho Chí Thanh, ngoài phạm vi change này:** `server.js` báo `unavailable` cho ca "một
instance chết" vì chính hạn 2,5 giây của nó. Trang status vì thế cũng đang hiển thị sai mức độ, độc
lập với watcher.

**Đã để lại phép kiểm:** `tests/test_watch_gateway.py`, 13 ca cho `decide()` và `parse_pairs()`, ca
quan trọng nhất là `test_status_says_down_but_a_real_call_still_works` — nó khoá lại đúng phép đo
trên. Bộ kiểm Python đi từ 58 lên **71**, `EXPECTED_PY` trong `ci.yml` đã sửa theo đúng như thông
báo của CI yêu cầu. `tools/check_english_names.py` → 0 vi phạm.

---

### Kết quả mười bài, đo 17/09/2026 trên hệ thống thật

Chạy với nhịp **10 giây** cho nhanh (biến shell, `.env` không bị sửa), hạn 25 giây. `.env` đã có
SMTP thật nên **mọi thư đều gửi đi thật**.

| Bài | Kỳ vọng | Kết quả |
|---|---|---|
| 5.1 `stop litellm-1` | một thư `degraded` | **ĐẠT** sau đúng 2 nhịp, `WARN - Gateway mat mot phan nang luc, VAN dang phuc vu` |
| 5.2 `stop litellm-2` (cả hai) | một thư `unavailable` | **ĐẠT**, `DOWN - GATEWAY HONG` |
| 5.3 giữ nhiều nhịp | không thêm thư | **ĐẠT** — ~7 nhịp liên tiếp ở `unavailable`, 1 thư |
| 5.4 dựng lại chỗ canh giữa sự cố | không thêm thư | **ĐẠT** — 4 nhịp sau, vẫn đúng 2 thư |
| 5.5 bật lại cả hai | một thư phục hồi | **ĐẠT** ngay nhịp tốt đầu tiên |
| 5.6 `stop gateway-status`, Gateway khoẻ | "không đọc được trạng thái" | **ĐẠT**, `WARN - Khong doc duoc trang thai (Gateway van tra loi)` |
| 5.7 `stop gateway-lb` | một thư, khác 5.2 | **ĐẠT** — thư gửi; thân thư không chụp được (xem ghi chú) |
| 5.8 lớp ngoài hỏng, lớp trong khoẻ | thư nói đúng lớp | **ĐẠT** — xem thân thư dưới |
| 5.9 sự cố ngắn hơn một nhịp | không thư nào | **ĐẠT 18/09** bằng `pause`/`unpause` (17/09: lỗi phép thử) |
| 5.10 nhịp tim | một thư | **ĐẠT** bằng đường khác (xem dưới) |

**Thân thư bài 5.8** — đọc là biết hỏng ở lớp nào, không phải đoán:

```
Subject: [trong] DOWN - GATEWAY HONG
Ket qua do tung dich:
  lb         DAT
  public     HONG  URLError: [Errno 111] Connection refused
  api/status reachable
      lb      reachable     proxy1  reachable
      proxy2  reachable     route   reachable
```

**Bài 5.9 — kỳ vọng không đạt, và nguyên nhân nằm ở PHÉP THỬ, không ở mã.** Tắt `litellm-1` lúc
`16:34:05`, bật lại lúc `16:34:09` — bốn giây. Nhưng chỗ canh vẫn đổi trạng thái hai lần và gửi hai
thư.

Lý do: `docker start` chỉ khởi động **container**, còn LiteLLM mất thêm ~30 giây mới `healthy`. Sự
cố **thật** dài ~30 giây chứ không phải 4 giây, nên chỗ canh bắt được là **đúng**.

Hệ quả cho D9: cửa sổ mù **không đo được bằng `docker stop`/`start`**, vì thời gian một instance
khởi động lại đã lớn hơn một nhịp. Con số ở D9 vẫn là **suy luận từ luật debounce** (2 nhịp liên
tiếp × nhịp dò), **không phải phép đo**. Phải ghi đúng như vậy, đừng nâng nó lên thành ĐẠT.

**ĐO XONG NGÀY 18/09/2026 — bằng `docker pause` / `docker unpause`.** `pause` đóng băng tiến trình
**tức thì cả hai chiều**, nên hẹn được giờ sự cố; đó đúng là thứ `stop`/`start` không làm được.

```
  su co 26 giay,  lot han giua hai nhip  -> 0 nhip hong, KHONG thu   08:56:57 - 08:57:23
  su co 121 giay, trum dung mot nhip     -> 1 nhip hong, KHONG thu   08:59:57 - 09:01:58
  tep trang thai sau ca hai bai: state=reachable, bad_ticks=1, khong dong "State changed"
```

Bài 121 giây mới là bài đáng tiền: Gateway **thật sự** không phục vụ được suốt hai phút mà chuông
vẫn im — đúng như luật hai nhịp đã hứa, không phải lỗi.

**Phép đo sửa lại chính con số của D9.** Nhịp `09:00:54` mất **28 giây** mới kết luận hỏng, nên
trong lúc hỏng hai nhịp cách nhau `28 + 60 = 88` giây. Trần im lặng là `60 + 88 ≈ 148` giây, thư đầu
tiên tới sau `2 × 88 ≈ 176` giây — chứ không phải 85/170. Đã sửa trong `design.md` D9 và mục 5.2 của
`docs/reference/canh-gateway-va-gui-thu-17-09.md`.

**Trần trên, không phải trần duy nhất:** số này ứng với kiểu hỏng **treo** (`pause` dựng lại đúng
kiểu ấy, và 17/09 cũng thấy vậy khi mọi thứ chết thật). Cổng bị từ chối ngay thì phép dò hỏng tức
thì và trần rút về `60 + 60 = 120` giây.

**Quan sát kèm, không phải bài thi:** lúc bật cụm lên lúc `08:53:50`, nhịp đầu rơi vào đúng lúc
`gateway-lb` còn đang khởi động → một nhịp `unavailable`, nhịp sau xanh lại, **không thư**. Luật hai
nhịp chặn luôn cả báo động giả lúc khởi động.

**Bài 5.10 — đạt bằng đường khác.** Không đổi đồng hồ container. Thư nhịp tim đã gửi **thật** ba
lần trong quá trình làm: `23:09:03` qua SMTP từ máy host, và hai lần nữa khi chỗ canh khởi động với
tệp trạng thái mới. Nội dung đúng khuôn, có số nhịp đã dò và số nhịp hỏng.

**Bài 5.7 — thân thư không chụp được.** Lần chạy khô để lấy thân thư dùng tệp trạng thái mới, nên
nhịp đầu chưa qua ngưỡng hai nhịp và không in gì. `gateway-lb` đã khôi phục trước khi thử lại. Hành
vi máy trạng thái thì **đã chứng minh** qua log; riêng việc so nội dung với bài 5.2 thì **chưa**.

**Ghi chú về phép thử, không phải về sản phẩm:** hai lần vòng chờ của tôi chụp mốc "số lần đổi trạng
thái" **sau** khi trạng thái đã đổi, nên nó đợi một lần đổi không bao giờ tới. Đúng loại lỗi tranh
chấp thời điểm. Cách đúng: chụp mốc **trước** khi phá.

**Hệ quả đo được của bản sửa hạn 25 giây:** khi mọi thứ chết thật, mỗi nhịp mất ~25 giây thay vì
tức thì. Ở nhịp production 60 giây, thời gian tới thư đầu tiên là `2 × (25 + 60) ≈ 170 giây` (đo
18/09 cho số sát hơn: nhịp hỏng mất 28 giây, tức `≈ 176 giây`), chứ
không phải ~120 giây như D9 ước lượng ban đầu. Phải sửa con số trong D9 theo phép đo này.


Lát mỏng sạch **không** có nghĩa là xong.

- [x] 5.1 `docker stop litellm-1` → **kỳ vọng: một thư `degraded`**, nói rõ Gateway vẫn phục vụ.
      Đây là ca agent không bao giờ báo
- [x] 5.2 `docker stop litellm-2` (cả hai tắt) → **kỳ vọng: một thư `unavailable`** trong vòng hai
      nhịp. Ghi độ trễ thật
- [x] 5.3 Giữ nguyên trạng thái hỏng qua **ít nhất mười nhịp** → **kỳ vọng: không thêm thư nào**
- [x] 5.4 `docker restart token-ledger-gateway-watch` **trong lúc vẫn đang hỏng** → **kỳ vọng: không
      thêm thư nào.** Đây là D5, và chỉ lộ ra ở bài này
- [x] 5.5 Bật hai instance lại → **kỳ vọng: một thư phục hồi**, độ dài khớp đồng hồ thật trong ±1
      nhịp. So bằng số, không bằng cảm giác
- [x] 5.6 `docker stop gateway-status` (Gateway vẫn khoẻ) → **kỳ vọng: thư "không đọc được trạng
      thái", KHÔNG phải "Gateway hỏng"**. Bài này chặn cả một lớp báo động giả
- [x] 5.7 `docker stop gateway-lb` → **kỳ vọng: một thư, nội dung khác bài 5.2**, và (A) cũng đỏ
- [x] 5.8 Chặn riêng (A) trong khi (B)(C) vẫn xanh → **kỳ vọng: thư nói lớp ngoài hỏng**, theo đúng
      bảng chẩn đoán D3
- [x] 5.9 **Đo cửa sổ mù của D9.** Tắt rồi bật trong khoảng ngắn hơn một nhịp → **kỳ vọng: không thư
      nào.** Ghi con số thật vào tài liệu vận hành

      **Đạt 18/09/2026** bằng `docker pause`/`unpause`: sự cố 26 giây (lọt giữa hai nhịp) và sự cố
      121 giây (trùm một nhịp) đều **không sinh thư nào**. Trần im lặng đo được: **~148 giây**. Số
      đã ghi vào `docs/reference/canh-gateway-va-gui-thu-17-09.md` mục 5.2 — xem ghi chú ở trên
- [x] 5.10 Chỉnh đồng hồ tới sát giờ nhịp tim → **kỳ vọng: một thư nhịp tim**, số nhịp khớp log

## 6. Điều kiện dừng — thư phải TỚI NƠI

**Đường thư đã cấu hình xong 17/09/2026.** Giá trị chép từ `.env` của
`CRM-Classification-Pipeline` — cùng một tài khoản gửi, App Password 16 ký tự. `.env` của repo này
đã nằm trong `.gitignore` (`git check-ignore` xác nhận), và **không giá trị nào bị in ra màn hình**
trong suốt quá trình chép.

**Ba thư đã RỜI MÁY, log xác nhận `Mail sent`:**

```
23:09:03   [trong] nhip tim - 2026-09-17
23:09:09   [trong] DOWN - GATEWAY HONG
23:09:16   [trong] OK - Gateway da tro lai binh thuong
```

**Nhưng ba ô dưới đây VẪN CHƯA ĐƯỢC ĐÁNH DẤU**, và đó là điểm mấu chốt của cả mục này: spec viết
*"thư rời khỏi máy MUST NOT được coi là thư đã tới"*. Gmail có thể xếp chúng vào thư rác, hoặc chặn
hẳn. Chỉ người nhận mở hộp thư ra và nói "thấy rồi" mới đóng được mục này.

**Lỗi script bắt được ngay khi cấu hình:** CRM ghi `SMTP_USE_TLS=true`, còn mã thì so `!= "0"` —
tức ai đó ghi `false` sẽ **bật** TLS chứ không tắt, im lặng làm ngược ý. Đã sửa thành so với cả tập
`0/false/no/off/rỗng`. Không tự lộ ra nếu chỉ thử bằng giá trị `1`.


- [x] 6.1 **Người nhận xác nhận đã thấy thư sự cố** trong hộp thư. Kiểm cả thư rác. Lệnh gửi không
      báo lỗi MUST NOT được coi là đã báo

      **Xác nhận 18/09/2026.** Người nhận mở Gmail, thấy trong **Inbox** cặp thư của sự cố tối
      17/09: `[trong] WARN - Gateway mat mot phan nang luc, VAN dang phuc vu` (`23:34:21`) rồi
      `[trong] OK - Gateway da tro lai binh thuong` (`23:34:35`). Không rơi vào thư rác.

      **Sửa một con số ghi thiếu:** mục 6 trên kia chép ba thư lúc `23:09`. Hộp thư cho thấy còn
      cặp `23:34` nữa, tức **ít nhất 6 thư** đã gửi thật, không phải 3
- [x] 6.2 **Người nhận xác nhận đã thấy thư nhịp tim.** Hai loại thư, hai lần xác nhận — nhịp tim
      rất dễ bị bộ lọc coi là thư rác vì nó lặp lại và giống nhau

      **Xác nhận 18/09/2026:** người nhận mở Gmail, thấy `[trong] nhip tim - 2026-09-18` **trong
      Inbox**, không phải thư rác. Mốc trong thư `15:53:39 (gio VN)` khớp log container
      `08:53:39` UTC — đúng 7 tiếng, tức phần đổi múi giờ chạy đúng
- [ ] 6.3 Người nhận đọc thư mà **không cần hỏi lại** đang xảy ra chuyện gì và phải làm gì. Không
      đạt thì sửa mẫu thư, không phải giải thích miệng

## 7. Bàn giao việc gỡ thư khỏi agent — NGOÀI phạm vi change này

**Chốt 17/09/2026: change này chỉ làm phần gửi thư của watcher.** Mã gửi thư trong các agent do
**leader** gỡ sau, khi watcher đã chạy và đã được tin. Không đụng repo agent nào ở đây.

- [x] 7.1 Viết ghi chú bàn giao vào `docs/reference/`, nêu đúng bốn điều dưới đây, để người gỡ không
      phải đọc lại toàn bộ change

**Nội dung bàn giao — cái gì gỡ, cái gì phải giữ:**

| | Việc | Vì sao |
|---|---|---|
| Gỡ | hai lệnh `_notify(...)` ở `CRM-Classification-Pipeline/src/llm.py:263` và `:279` | watcher đã lo |
| Gỡ | hàm `_notify` ở `llm.py:292`, **nếu** sau đó không còn ai gọi — kiểm bằng `grep`, không bằng trí nhớ | dọn mã chết |
| **GIỮ** | `log_fallback()`, máy trạng thái hai nấc, dòng ghi câu lỗi cuối từ Gateway | agent vẫn phải **chạy tiếp** khi Gateway chết, và log là chỗ tra số lượt đi thẳng (D8) |
| **GIỮ** | `src/notification.py` | `pipeline.py:28` và `:879` vẫn dùng nó cho **thư lỗi của lô** — việc khác hẳn. Xoá nó là làm hỏng một đường thư đang chạy |

**Điều kiện trước khi gỡ:** mục 6 của change này phải đạt — người nhận đã xác nhận thấy cả thư sự cố
lẫn thư nhịp tim. Gỡ trước là tự tạo một khoảng không có chuông nào.

**Nghiệm thu sau khi gỡ** (người gỡ làm, không phải change này): chạy lại diễn tập fallback của CRM
→ lô vẫn chạy xong, log `[FALLBACK]` vẫn đầy đủ, không thư nào từ agent.

**Trong lúc chưa gỡ — một sự cố sinh ra thư từ CẢ HAI nguồn.** Đó không phải lỗi, và trong giai đoạn
chuyển tiếp nó còn có lợi: thư của CRM mang con số **bao nhiêu lượt đã đi đường thẳng**, thứ watcher
không biết được (D8). Tài liệu ở task 8.1 phải nói rõ điều này, để người nhận không tưởng chuông
đang gửi trùng vì hỏng.

## 8. Tài liệu

- [x] 8.1 Ghi vào `docs/reference/`: thư báo gì, **không** báo gì, và ba trần đã biết — lớp "sống mà
      hỏng" theo từng khoá không phủ (D1), sự cố ngắn hơn một nhịp không phủ (D9), máy chủ chết thì
      im lặng cho tới khi có bản ngoài (D10/D11)
- [x] 8.2 Ghi rõ: **vắng thư nhịp tim là một tín hiệu.** Không có câu này thì D7 vô nghĩa
- [x] 8.3 Ghi cách tra số lượt đi đường thẳng từ log agent theo khoảng thời gian trong thư (D8)
- [x] 8.4 Ghi bảng ba tình huống của D11 — nhận thư từ bản nào nghĩa là gì — kể cả khi bản ngoài
      chưa dựng. Dựng sau thì đọc là hiểu ngay
- [x] 8.5 `openspec validate move-the-outage-alarm-out-of-the-agents --strict` đạt — chạy 18/09/2026
      (openspec 1.3.1): `Change 'move-the-outage-alarm-out-of-the-agents' is valid`

## Ghi chú vận hành

**Nhịp tim TẮT từ 18/09/2026, theo yêu cầu của người nhận chuông:** chỉ gửi thư khi trạng thái đổi.
Bật/tắt bằng `WATCH_HEARTBEAT_HOUR` (`off` để tắt, một con số giờ để bật). Spec đã sửa cho khớp:
nhịp tim phải **có** và phải **tắt được bằng cấu hình**, chứ không bắt buộc bật. Cái giá — chỗ canh
chết lặng lẽ thì không còn tín hiệu nào — ghi ở mục 3 tài liệu vận hành.

Gateway trên **máy phát triển** bật tắt tự do. Mọi bài phá ở mục 5 chạy ở đó, không chạy trên máy
chủ thật.

Mục 7 đụng repo `CRM-Classification-Pipeline`, nằm ngoài repo này. Xin xác nhận trước khi sửa.

**Ngoài phạm vi, đã quyết định, đừng làm lẫn vào đây:**

- Gọi thật mỗi giờ — bỏ, năm lý do ở D1
- Đọc kết cục thật từ sổ để bắt khoá hết hạn — change riêng, câu hỏi khác
- Canh `token-ledger-web` — thêm sau bằng một dòng trong `WATCH_HTTP`
- Dựng bản ngoài trên máy khác — một lần triển khai nữa, không phải một lần viết lại
