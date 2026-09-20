## 1. Dựng chỗ chứa hạn mức, chưa ai đọc

- [x] 1.1 Chốt hình dạng phần ghi chú của khoá: `quota_usd` (số) và `quota_log` (danh sách các lần
      nạp, mỗi lần gồm giá trị trước, giá trị sau, thời điểm, người thao tác)
- [x] 1.2 Đặt thử `quota_usd` vào metadata của **một** khoá bằng tay qua `/key/update`, rồi gọi
      `/key/info` xem lại
- [x] 1.3 Sau bước 1.2, gọi thật một lượt bằng khoá đó và xác nhận **hai** điều: khoá vẫn gọi được,
      và tag định danh vẫn lọc đúng tuyến (metadata bị ghi đè là mất tag, mất luôn việc quy tiền
      theo agent)
- [x] 1.4 Thêm biến môi trường cho master key mà backend dùng, và để backend dừng hẳn khi thiếu
      biến đó — cùng kỷ luật với `DASHBOARD_KEY`

## 2. Đường ghi ở backend

- [x] 2.1 Viết client gọi `/key/update` và `/key/info` của Gateway, dùng master key từ biến môi
      trường. Đường dẫn và phương thức **viết cứng**, không lấy từ yêu cầu của người gọi
- [x] 2.2 Thêm `POST /api/quota` (đặt hạn mức) dùng lại `caller()`, từ chối giá trị âm / không phải
      số / rỗng kèm thông báo nói rõ vì sao
- [x] 2.3 Thêm `POST /api/quota/top-up` (nạp thêm): đọc giá trị hiện tại, ghi giá trị mới, thêm một
      phần tử vào `quota_log`
- [x] 2.4 Mọi thao tác ghi phải theo trình tự **đọc – gộp – ghi lại cả cục**: gọi `/key/info` lấy
      metadata hiện có, gộp thêm `quota_usd`/`quota_log`, rồi gửi lại **toàn bộ** metadata. Gửi
      thiếu là **xoá mất `tags`** của khoá — `key_management_endpoints.py:2010` thay thế chứ không
      gộp, và mất tag nghĩa là tiền ghi sai project mà request vẫn trả 200
- [x] 2.5 Lọc trắng khoá metadata: chỉ `quota_usd` và `quota_log` được nhận từ người gọi; mọi khoá
      khác trong yêu cầu bị bỏ, và những khoá metadata sẵn có được giữ nguyên
- [x] 2.6 Viết phép kiểm cho đúng cái bẫy trên: đặt hạn mức cho một khoá **đang có tag**, rồi khẳng
      định tag còn nguyên sau khi ghi. Phép kiểm này MUST chạy được mà không cần Gateway thật
- [x] 2.7 Thêm `GET /api/quota` trả hạn mức, số đã tiêu, tỉ lệ, và cờ "project này có chặn được
      không"
- [x] 2.8 Phát hiện và báo khi một project có nhiều hơn một virtual key — hạn mức khi đó không còn
      nghĩa "cả project"
- [x] 2.9 Viết phép kiểm: gọi hai endpoint ghi không mang khoá phải nhận 401, và hạn mức **không**
      đổi
- [x] 2.10 Viết phép kiểm: gửi kèm khoá metadata lạ thì chúng bị bỏ, và `tags` của khoá còn nguyên
- [x] 2.11 Viết phép kiểm: master key không xuất hiện trong bất kỳ câu trả lời nào, kể cả khi Gateway
      trả lỗi
- [x] 2.12 Sửa ghi chú lập luận ở phần xác thực của `backend/main.py` cho khớp: nay đã có endpoint
      ghi, khoá dùng chung mở cả hai chiều, và backend giữ master key của Gateway

## 3. Tab Setting trên dashboard

- [x] 3.1 Thêm tab `⚙ Setting` vào thanh tab, đọc danh sách project từ API chứ không viết cứng
- [x] 3.2 Mỗi project một ô nhập hạn mức, hiện kèm số đã tiêu và tỉ lệ — lấy từ **số của Gateway**,
      kèm một dòng nói rõ đây là phần Gateway thấy
- [x] 3.3 Đánh dấu rõ project chưa có khoá ở Gateway ("chỉ cảnh báo, không chặn"), project không có
      nguồn chi phí Google ("số đã tiêu luôn bằng 0"), và project có nhiều hơn một khoá
- [x] 3.4 Bảng lịch sử nạp cho từng project, theo thứ tự thời gian
- [x] 3.5 Bấm Lưu phải gọi API và đợi kết quả; lỗi thì nói rõ và **không** hiện số mới như thể đã
      lưu — đúng bài học của panel bị xoá 17/08/2026
- [x] 3.6 Viết phép kiểm cho lớp gọi API của tab này

## 4. Cổng khoá phủ toàn màn hình

- [x] 4.1 Đổi `.key-gate` thành lớp phủ kín khung nhìn, nền đặc, ô nhập ở giữa
- [x] 4.2 Không dựng phần còn lại của trang trước khi có khoá — thanh tab, bảng, biểu đồ đều không
      được hiện phía sau
- [x] 4.3 Giữ nguyên hành vi đã có: khoá sai thì nói rõ và không nhớ lại; khoá đúng thì nhớ cho lần
      sau
- [x] 4.4 Viết phép kiểm: chưa có khoá thì không có yêu cầu mạng nào trả về dữ liệu nghiệp vụ
- [x] 4.5 Viết phép kiểm: khoá không bao giờ xuất hiện trên địa chỉ URL, kể cả sau khi đăng nhập
- [x] 4.6 Đặt `DASHBOARD_KEY=TTDL&DHS2026` trong `.env`, và ghi vào tài liệu rằng gõ bằng `set`
      trong cmd sẽ bị dấu `&` cắt cụt

## 5. Cảnh báo email

- [x] 5.1 Viết `scripts/watch_quota.py` theo khuôn `watch_gateway.py`: đọc tỉ lệ từng project, so
      với bậc lần trước, chỉ gửi thư khi đổi bậc
- [x] 5.2 Ba bậc 90% / 100% / đã vượt; nhảy nhiều bậc trong một nhịp thì gửi thư của bậc cao nhất
- [x] 5.3 Nạp thêm làm tỉ lệ tụt xuống thì đặt lại bậc, để lần vượt sau lại gửi thư
- [x] 5.4 Trạng thái lưu ra file JSON, để khởi động lại không gửi lại thư của bậc đang ở
- [x] 5.5 Nội dung thư: tên hiển thị của agent, project, hạn mức, đã tiêu, tỉ lệ, bậc, việc cần làm.
      Không chứa nội dung câu hỏi hay câu trả lời
- [x] 5.6 Thư cho project không chặn được phải nói rõ là cảnh báo suông
- [x] 5.7 Gửi thư hỏng thì ghi lỗi và đi tiếp, không được ảnh hưởng tới việc chặn; dòng ghi lỗi
      không chứa mật khẩu hay tên đăng nhập máy chủ thư
- [x] 5.8 Thêm dịch vụ chạy nền vào `docker-compose.yml`, dùng lại image `tools`, không thêm phụ
      thuộc mới
- [x] 5.9 Viết phép kiểm cho logic đổi bậc, gồm cả trường hợp nhảy nhiều bậc và trường hợp khởi động
      lại

## 6. Hook chặn ở Gateway — chạy ở chế độ chỉ ghi nhận

- [x] 6.1 Viết hook `async_pre_call_hook`: đọc hạn mức từ `user_api_key_dict.metadata`, số đã tiêu
      từ `user_api_key_dict.spend`, và tag từ `data["metadata"]["tags"]`. Không mở kết nối database
      nào
- [x] 6.2 Khai bảng ánh xạ tag → loại agent (chat / chạy lô) trong cấu hình của hook; tag chưa khai
      thì mặc định là loại chạy lô
- [x] 6.3 Nhánh loại chat: trả về **một đối tượng `RejectedRequestError`**, KHÔNG trả về chuỗi —
      chuỗi sẽ thành HTTP 400 vì `call_type` của đường chat là `acompletion`. Câu chữ phải tự nói rõ
      đây là thông báo của hệ thống quản trị
- [x] 6.4 Nhánh loại chạy lô: trả về một lỗi mang chuỗi `429`
- [x] 6.5 Thiếu hạn mức, hạn mức sai định dạng, hay không đọc được số đã tiêu thì **cho qua** và ghi
      lại sự kiện — không chặn vì một lỗi tra cứu
- [x] 6.6 Ghi một dòng JSON cho mỗi lượt bị chặn, đủ bảy trường, không chứa nội dung người dùng
- [x] 6.7 Thêm cờ chế độ chỉ ghi nhận: tính đủ, ghi dòng "lẽ ra đã chặn", nhưng cho mọi request đi
      qua
- [x] 6.8 Gắn file hook vào container bằng `volumes` trong khối `x-litellm` (image lấy từ GHCR
      không chứa mã của repo này), rồi khai trong `litellm_settings.callbacks` của
      `docker/gateway/config.gateway.yaml`, bật chế độ chỉ ghi nhận
- [x] 6.9 Kiểm một lượt rằng hook thật sự được nạp: gọi thử và xác nhận hook có chạy, chứ không kết
      luận từ việc container lên `healthy` — khai sai tên callback không làm LiteLLM dừng
- [x] 6.10 Viết phép kiểm cho các nhánh hỏng của hook, không chỉ nhánh chạy đúng — một lỗi trong
      hook là lỗi của toàn bộ Gateway
- [ ] 6.11 Đo thực tế: chế độ chỉ ghi nhận chạy đủ lâu, đối chiếu số dòng "lẽ ra đã chặn" với số
      hiển thị trên tab Setting

## 7. Bật chặn thật và nghiệm thu

- [ ] 7.1 Tắt chế độ chỉ ghi nhận, dựng lại hai instance LiteLLM.
      **9.6 ĐÃ XONG** (image `b7657e95b1…` đã phát hành và đã kéo về máy này). Mã nguồn hook đã dùng `RejectedRequestError`, nhưng image
      đang chạy vẫn là bản chưa vá — bật chặn thật lúc này thì agent chat dùng chế độ luồng
      nhận HTTP 500 thay vì câu thông báo.
- [x] 7.2 Đo một agent loại chat: hạ hạn mức xuống dưới số đã tiêu, gọi thật → nhận HTTP 200, thân
      trả lời đúng hình dạng, nội dung là câu thông báo
- [x] 7.3 Đo cùng tình huống ở chế độ luồng → câu trả lời vẫn về đúng dạng luồng, agent không treo
- [x] 7.4 Đo một agent loại chạy lô → nhận 429, thông báo chứa chuỗi `429`, và app tự lùi
- [x] 7.5 Đo nạp thêm: nâng hạn mức lên trên số đã tiêu → request đi qua được trong khoảng trễ đã
      nêu, không khởi động lại dịch vụ nào
- [x] 7.6 Đo rằng lượt bị chặn **không** làm đổi số lượt gọi và token của các phép thống kê hiện có
- [x] 7.7 Đo rằng project không đặt hạn mức thì không bị chặn
- [x] 7.8 Đo lại lần nữa rằng tag vẫn lọc đúng tuyến sau khi mọi khoá đã mang `quota_usd` trong
      metadata
- [x] 7.9 Nâng `EXPECTED_PY` và `EXPECTED_JS` trong `.github/workflows/ci.yml` cho khớp số phép kiểm
      mới — quên bước này đã từng làm `main` đỏ

## 9. Bản vá fork (phát sinh 20/09 từ phép đo chế độ luồng)

- [x] 9.1 Vá `_REJECTED_STREAM_LOGGING_FALLBACK` trong fork: dựng `Logging` thật khi
      `litellm_logging_obj` là None, và cho mã trả về của nhánh luồng khớp nhánh không-luồng (200)
- [x] 9.2 Thêm bản vá vào vòng canh của CI (`FORK_PATCHES`), chạy trước khi build
- [x] 9.3 Đo bản vá bằng cách gắn file đã vá vào container đang chạy: cả hai chế độ trả 200 đúng
      câu, sổ ghi `failure` spend 0 token 0
- [x] 9.4 Commit bản vá trên nhánh `Tuan-develop` của fork (`b7657e95b1`), chưa đẩy
- [x] 9.5 Đẩy lên fork
- [x] 9.6 Đợi CI dựng image, rồi đổi nhãn `image:` trong `docker-compose.yml` **và**
      `docker-compose.bench.yml` — CI đỏ nếu hai chỗ lệch nhau
- [x] 9.7 Dựng lại `litellm-1`, `litellm-2` bằng nhãn mới rồi đo lại chế độ luồng một lượt

## 8. Tài liệu

- [x] 8.1 Viết mục hướng dẫn dùng tab Setting: nhập, nạp thêm, đọc cảnh báo, và ý nghĩa của các dấu
      "chỉ cảnh báo"
- [x] 8.2 Ghi vào tài liệu giới hạn thi hành: hôm nay chỉ chặn được hai agent đã qua Gateway, và
      **Phân Loại Dữ Liệu CRM** còn đường lui đi thẳng Google
- [x] 8.3 Ghi ngưỡng ở design D5 (khi nào phải đọc thẳng `spend` thay vì lấy từ khoá đã nhớ đệm) vào
      chú thích ngay trong mã hook
- [x] 8.4 Ghi rủi ro đường `metadata`: trường `tags` cấp cao là tính năng trả phí, `metadata.tags`
      hôm nay đi lọt; dấu hiệu bị siết là `/key/update` trả 403 hoặc khoá mất tag sau khi nâng cấp
- [x] 8.5 Bổ sung vào `docs/reference/onboard-a-new-agent.md` một đầu việc: agent mới cần khai loại
      (chat / chạy lô) và cần đặt hạn mức cho khoá của nó
- [x] 8.6 Thêm bộ đếm số lượt có chi phí bằng 0 và cảnh báo khi nó tăng — model chưa có trong bảng
      giá là một lối đi vòng qua hạn mức
