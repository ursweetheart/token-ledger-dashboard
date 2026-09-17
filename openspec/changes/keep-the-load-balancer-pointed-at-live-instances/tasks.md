## 0. Chứng minh lỗ hổng có thật (chưa sửa gì)

Không sửa trước rồi tin là đã sửa. Phải thấy nó hỏng trước đã.

- [x] 0.1 Bật Gateway trên máy phát triển, đợi cả hai instance `healthy`. Ghi IP hiện tại:
      `docker inspect -f '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' token-ledger-litellm-1 token-ledger-litellm-2`
      — 17/09/2026: `litellm-1` 172.20.0.8, `litellm-2` 172.20.0.4, `gateway-lb` 172.20.0.2
- [x] 0.2 `docker compose --profile gateway exec gateway-lb nginx -t` → phải đạt. Đây là mốc so sánh
      cho task 2.1, và cũng xác nhận `nginx -t` chạy được trong container này — 17/09/2026: đạt,
      `syntax is ok` / `test is successful`
- [x] 0.3 **Đo hành vi hỏng.** `docker compose up -d --force-recreate --no-deps litellm-1`, đợi
      `healthy`, ghi IP mới. Gửi 20 lượt `GET /health/readiness` qua `gateway-lb`, đếm số lượt vào
      từng instance bằng log của chúng. **Kỳ vọng: 0 lượt vào `litellm-1`.** Ghi số đo vào
      `design.md` mục Context. Phương pháp đo: xem D6 — endpoint miễn phí, `--no-deps` bắt buộc

      **Kết quả 17/09/2026 — kỳ vọng SAI, và phát hiện thật nằm ở chỗ đó.** Xem D7.

      | Lần đo | IP `litellm-1` | litellm-1 | litellm-2 |
      |---|---|---|---|
      | mốc chuẩn, chưa đụng gì | .8 | 11 | 9 |
      | sau `--force-recreate` một instance | .8 (**không đổi**) | 11 | 9 |
      | sau `--force-recreate` **cả hai** | .8 và .4 (**không đổi**) | — | — |
      | ép IP đổi bằng cách chiếm chỗ `.8` | **.9** | **0** | **20** |

      Dựng lại container **không tự nó** đổi IP — Docker cấp lại đúng địa chỉ cũ khi nó còn trống.
      Lỗ hổng chỉ kích hoạt khi địa chỉ cũ **bị container khác giành mất** trong lúc dựng lại.
- [x] 0.4 Ghi thêm dấu hiệu bề mặt tại đúng thời điểm đó: `docker compose --profile gateway ps` trạng
      thái cả hai, `/lb-health` trả gì, `/health/liveliness` của `litellm-1` trả gì. Mục đích là ghi
      lại rằng **mọi dấu hiệu đều xanh** trong khi một nửa năng lực đã mất

      **Kết quả 17/09/2026, đo đúng lúc `litellm-1` nhận 0/20 lượt:** `litellm-1` `Up 32 seconds
      (healthy)`, `litellm-2` `Up 2 minutes (healthy)`, `gateway-lb` `Up 5 minutes (healthy)`,
      `/lb-health` trả `lb-ok`. **Không một dấu hiệu nào lệch.**
- [x] 0.5 Khôi phục: khởi động lại `gateway-lb`, đo lại 20 lượt, xác nhận tải chia đều trở lại. Đây
      là cách chữa cũ, và là thứ change này xoá bỏ — 17/09/2026: sau `restart gateway-lb`,
      `litellm-1` 18 lượt / `litellm-2` 2 lượt. Cả hai trở lại vòng chia tải; lệch 18/2 là do vòng
      round-robin bắt đầu lại, không phải do còn sót lỗi

## 1. Vá `nginx.conf`

- [x] 1.1 Thêm `resolver 127.0.0.11 valid=10s ipv6=off;` ở phạm vi `http` của tệp, đặt ngay trên khối
      `upstream`, đúng vị trí `edge.conf.template` đang đặt — tệp này mount vào
      `/etc/nginx/conf.d/default.conf`, tức đã nằm trong khối `http`
- [x] 1.2 Thêm `zone litellm_pool 64k;` làm dòng đầu khối `upstream litellm_pool` (D5)
- [x] 1.3 Thêm tham số `resolve` vào cả hai dòng `server`, giữ nguyên `max_fails=2 fail_timeout=30s`
      và `keepalive 32`
- [x] 1.4 Viết lại chú thích ở `nginx.conf:25-30`: đoạn "nginx phân giải tên upstream MỘT LẦN lúc
      khởi động" mô tả hành vi **trước** change này. Ghi số đo của task 0.3 làm lý do, và giữ lại
      luật vẫn đúng — nginx không khởi động được nếu một tên upstream không phân giải được, nên
      `depends_on` của `gateway-lb` vẫn phải đợi cả hai instance

      **Bản đầu của chú thích SAI, đã sửa sau khi đo ở task 2.7.** Nó khẳng định luật cũ "khởi động
      lại nginx khi một instance đang tắt thì nginx không lên được" **vẫn đúng**. Đo ra là **không
      còn đúng**. Chú thích đã viết lại theo số đo.
- [x] 1.5 KHÔNG đụng `proxy_next_upstream`. Xác nhận bằng `git diff` rằng dòng đó không đổi: thêm
      `non_idempotent` là gửi lại một `POST` đã tính tiền — 17/09/2026: `git diff` chỉ chạm khối
      `upstream` và chú thích trên nó; khối `location /` không đổi một ký tự

## 2. Nghiệm thu

- [x] 2.1 `docker compose --profile gateway exec gateway-lb nginx -t` → đạt. **Chưa khởi động lại
      nếu bước này hỏng** (D3). Hỏng thì `git checkout docker/gateway/nginx.conf` và dừng —
      17/09/2026: đạt. Xác nhận build `nginx:1.27-alpine` bản mã nguồn mở nhận `zone` + `resolve`.
      Tệp thuần ASCII, 0 dòng CR (`.gitattributes` ép `docker/** text eol=lf`)
- [x] 2.2 `docker compose --profile gateway restart gateway-lb`, đợi `healthy`. Cả hai instance phải
      `healthy` trước khi chạy lệnh này — 17/09/2026: lên `healthy`, chia tải ngay 10/10
- [x] 2.3 **Lặp lại đúng phép đo 0.3**, cùng phương pháp D6. Dựng lại `litellm-1`, đợi `healthy`,
      gửi 20 lượt, đếm theo instance. **Kỳ vọng: cả hai instance đều nhận được lượt**, và không ai
      phải động vào `gateway-lb` — 17/09/2026: IP đổi `.9` → `.8`, kết quả **10 / 10**, không ai
      động vào `gateway-lb`. Trước khi vá, cùng phép đo cho **0 / 20**
- [x] 2.4 Đo chiều ngược: dựng lại `litellm-2`, lặp lại. Hai chiều, không chỉ một — 17/09/2026: IP
      đổi `.4` → `.9`. **Lần đo đầu ra 0/20**, ba vòng đo ngay sau đó đều **10/10**. Tức không phải
      bản vá hỏng mà là cửa sổ giao thời; định lượng ở 2.5
- [x] 2.5 Đo lúc giao thời: trong khi `litellm-1` đang dựng lại, gửi liên tục và đếm số lượt hỏng.
      Ghi con số thật. `max_fails=2 fail_timeout=30s` nghĩa là **vẫn có** vài lượt rơi vào địa chỉ
      cũ trước khi nginx loại nó — change này rút cửa sổ ấy từ vĩnh viễn xuống tối đa `valid=10s`,
      chứ không làm nó bằng không

      **Đo 17/09/2026**, ép IP đổi rồi bơm liên tục 75 giây, đọc dấu thời gian trong log:

      ```
      T0 = 02:56:17        ngay sau khi container bao healthy, IP moi = .4
      luot dau tien        02:56:18.168    -> tre ~1,2 giay
      75 giay luu luong    litellm-1  12.700   (49,9%)
                           litellm-2  12.731
      ```

      Cửa sổ thật là **~1,2 giây**, không phải 10 giây như D5 ước lượng theo `valid=10s`.

      **Suy luận, chưa chứng minh:** lần 0/20 ở task 2.4 nhiều khả năng do `max_fails=2
      fail_timeout=30s` loại instance sau hai lượt trượt vào địa chỉ cũ, chứ không do TTL của DNS.
      Hai mươi lượt bắn hết trong chưa tới một giây nên rơi trọn vào cửa sổ loại trừ ấy. Muốn chắc
      thì phải đo riêng — chưa làm, và **không** ghi vào tài liệu như thể đã chứng minh
- [x] 2.6 Xác nhận không hồi quy: `/lb-health` trả `lb-ok`, và một lượt `/health/readiness` qua
      `gateway-lb` trả `200`. **`gateway-edge` không nằm trong phạm vi đo** — dịch vụ ấy chưa từng
      được tạo trên máy này (`docker ps -a` ngày 17/09/2026 không có `token-ledger-gateway-edge`),
      và change này không đụng `edge.conf.template` — 17/09/2026: `lb-ok`, `{"status":"healthy",
      "db":"connected"}`, ba container `healthy`, chia tải 10/10
- [x] 2.7 **Đo lời khẳng định còn treo ở task 1.4.** Tắt một instance, khởi động lại `gateway-lb`,
      xem nó lên được hay không. `resolve` phân giải lúc chạy nên nginx CÓ THỂ lên được — nếu vậy
      thì luật cũ đã đổi, và cả chú thích trong `nginx.conf` lẫn ràng buộc `depends_on` của
      `gateway-lb` đều phải viết lại theo. Khôi phục instance ngay sau khi đo

      **Kết quả 17/09/2026: luật cũ ĐÃ ĐỔI.** Tắt `litellm-2` rồi `restart gateway-lb` →
      `gateway-lb` **lên bình thường**, worker khởi động sạch, `/health/readiness` vẫn trả
      `{"status":"healthy","db":"connected"}` qua instance còn lại. Trước khi vá, cùng thao tác ấy
      làm nginx không lên được.

      Đây là một **bẫy bị gỡ bỏ**, không phải rủi ro mới — và nó **không nằm trong mục What Changes
      của proposal**. Xem D8.

      `depends_on` của `gateway-lb` **giữ nguyên**: đợi cả hai instance khoẻ vẫn là khởi động sạch
      sẽ, chỉ không còn là điều kiện bắt buộc để nginx lên được. Đổi `depends_on` là mở rộng phạm
      vi, để ngoài change này.

      Khôi phục: `litellm-2` lên lại, chia tải 10/10

## 3. Phép canh trong CI

- [x] 3.1 Viết phép canh theo D4: quét `docker/gateway/*.conf` và `*.conf.template`; tệp có khối
      `upstream` phải khai `resolver`; mỗi khối `upstream` phải có `zone`; mỗi dòng
      `server <tên>:<cổng>` trong khối phải mang `resolve`. ~~Chỉ thư viện chuẩn của Python~~,
      mã thoát 0/1

      **Đổi cách làm, 17/09/2026:** cả ba phép canh đang có trong nhóm `guards` đều là **shell nội
      tuyến** (`grep`/`awk`), không tệp Python nào. Viết một script Python riêng kèm tệp phép kiểm
      là nặng hơn nếp đang có. Theo nếp: một bước `run:` trong `ci.yml`, `sed` + `awk`, không tệp
      mới, không phải nâng `EXPECTED_PY`. D4 đã sửa theo
- [x] 3.2 Phép kiểm cho phép canh: một cặp đạt/hỏng cho mỗi trong ba điều kiện; và một ca `server`
      trỏ bằng **địa chỉ IP** thay vì tên thì MUST NOT bị đòi `resolve`

      Năm ca thử dựng trong thư mục nháp, chạy bằng chính script **trích ra từ `ci.yml`**:

      | Ca | Kỳ vọng | Kết quả |
      |---|---|---|
      | `nginx.conf` trước khi vá (lấy từ `git show HEAD:`) | bắt cả 3 lỗi | ✅ bắt đủ 3 |
      | thiếu `resolver` | bắt | ✅ |
      | thiếu `zone` | bắt | ✅ |
      | một dòng `server` thiếu `resolve` | bắt | ✅ |
      | `server` trỏ bằng **IP** | **bỏ qua** | ✅ không báo |

      **Lỗi script đã bắt được ở vòng đầu:** hai ca `thiếu resolver` và `thiếu zone` **lọt**, vì
      chúng viết khối `upstream` gọn trên một dòng còn `awk` thì `next` ngay sau `{`. Sửa bằng bước
      chuẩn hoá (bỏ chú thích, tách `{ } ;` ra dòng riêng) — **không** sửa ca thử cho vừa phép canh.
      Cùng lúc sửa một lỗi nữa thấy khi đọc lại: biến đếm chỉ lấy khối `upstream` cuối cùng thay vì
      cộng dồn, nên tệp có từ hai khối trở lên sẽ đếm thiếu
- [x] 3.3 Chạy phép canh trên cây đã vá → 0 vi phạm. Chạy trên cây trước khi vá → phải bắt được
      `nginx.conf`. Không có bước này thì không biết phép canh có bắt được gì không — 17/09/2026:
      cây thật mã thoát `0`, cây trước khi vá mã thoát `1` kèm đủ ba dòng lỗi
- [x] 3.4 Thêm bước vào nhóm `guards` của `.github/workflows/ci.yml`; ~~tăng `EXPECTED_PY`~~ —
      không có phép kiểm Python nào thêm nên `EXPECTED_PY` giữ nguyên.

      **Đã kiểm bản trích từ YAML, không chỉ bản nháp:** trích khối `run:` ra tệp rồi chạy lại cả
      hai chiều → cây thật `0`, ca thử `1`, kết quả trùng khít bản nháp. Khối không chứa ký tự tab
- [ ] 3.5 Làm đỏ có chủ ý trên nhánh tạm: gỡ `resolve` khỏi một dòng `server`, xác nhận CI đỏ, ghi
      mã lần chạy, xoá nhánh tạm

      **Chưa làm — cần đẩy code lên GitHub, phải hỏi trước.** Kèm luật trước khi đẩy: trả địa chỉ
      bind của `web` về `192.168.20.111`

## 4. Tài liệu

- [x] 4.1 Ghi quy trình dựng lại instance vào `docs/reference/`, kèm bảng "trước / sau" ở
      `design.md` mục Migration. Nêu rõ: `restart` giữ IP, `up -d` dựng lại thì đổi IP, và sau change
      này cả hai đều an toàn — `docs/reference/dung-lai-instance-gateway.md`, thêm một dòng vào mục
      Tài liệu của `README.md`.

      **Sửa một câu sai trong chính task này:** "`up -d` dựng lại thì đổi IP" **không đúng** — đo ba
      lần, IP giữ nguyên. Tài liệu viết theo số đo, không theo câu này
- [x] 4.2 Ghi số đo của task 0.3 và 2.3 vào tài liệu đó, dạng "hỏng thế nào / đã sửa ra sao". Đây là
      bằng chứng, không phải lời kể — mục 5 của tài liệu là phần **chứng minh được**, mục 6 là phần
      **suy luận** tách riêng, theo khuôn `ep-429-va-mat-gateway-10-09.md`
- [ ] 4.3 `openspec validate keep-the-load-balancer-pointed-at-live-instances --strict` đạt

## Ghi chú vận hành

Gateway trên **máy phát triển** bật tắt tự do, không phải xin phép. Mọi phép đo ở trên chạy ở đó.

Máy chủ thật thì khác: chỉ khởi động lại `gateway-lb` một lần, sau khi đã xác nhận `nginx -t` đạt,
và cả hai instance đang `healthy`. Không `down`, không `--remove-orphans` — theo
`docs/reference/luat-trien-khai-tu-dong-13-09.md`.
