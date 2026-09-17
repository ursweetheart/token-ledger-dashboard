# Agent CRM tự đổi sang đường thẳng khi Gateway chết — nhật ký 12/09/2026

Ghi trong lúc làm change `keep-the-crm-agent-running-when-the-gateway-dies`. Tách rõ phần
**chứng minh được** khỏi phần **suy luận**, theo khuôn của
[`ep-429-va-mat-gateway-10-09.md`](ep-429-va-mat-gateway-10-09.md).

---

## 1. Kết quả một dòng

`gateway-lb` là điểm hỏng đơn. Agent CRM nay tự chuyển sang gọi thẳng nhà cung cấp sau ba lần mất
kết nối liên tiếp, chạy xong lô đang dở, và gửi đúng hai thư cho mỗi sự cố.

---

## 2. Điều CHỨNG MINH ĐƯỢC — kèm số

### 2.1 Khoá dự phòng ghi phí vào project thử, không phải project của agent

Gọi một lượt thật qua Vertex bằng `sa-key.json` trong repo CRM:

```
   HTTP 200 · 19 token · project crm-test-508114
```

Ba project cùng tồn tại trong câu chuyện này, và ai đọc sau phải biết đủ ba:

| Project | Vai trò |
|---|---|
| `crm-500509` | project **thật** của agent 7, đang ghi trong `dim_agent` |
| `crm-test-508114` | project **thử**, chứa `sa-key.json` — đường dự phòng dùng cái này |
| `60854134008` | project của khoá Vertex express mà Gateway đang dùng |

### 2.2 Đường thư của OpenWebUI dùng được, đường Graph của CRM thì chưa

| | OpenWebUI | CRM trước change |
|---|---|---|
| Cách gửi | SMTP Gmail, cổng 587 | Microsoft Graph |
| Thứ cần có | app password 16 ký tự | tenant, client id, client secret |
| Trạng thái đo 12/09 | đăng nhập được, gửi được thư thật | cả ba biến **trống**, không có tệp `.env` |

App password của Gmail **không** dùng cho Graph được. Hai cơ chế khác nhau hoàn toàn.

Sau change, một thư thật đã gửi thành công **qua chính mã nguồn CRM**, không qua script riêng.

### 2.3 Container CRM trước change không khởi động được

`docker-compose.yml:7` khai `env_file: .env`, mà tệp đó không tồn tại trong repo. Đây là chỗ chặn
mọi việc khác, và nó không liên quan gì tới Gateway.

### 2.4 Khoá `AQ.` là Vertex express, không phải AI Studio

Đã ghi ở `route-the-crm-agent-through-the-gateway/tasks.md` ô 1.2 từ 10/09, nhưng dễ đọc nhầm lần
nữa nên chép lại:

```
   KEY_CRM_FEEDBACK   dạng `AQ.`
        aiplatform.googleapis.com          → 200
        generativelanguage.googleapis.com  → 403
```

> **Tên biến đổi 17/09/2026:** `KEY_BENCH_CRM_TEST_GG_AIA_STU` → `KEY_CRM_FEEDBACK`. Tên cũ nói sai
> ba lần — khoá này không phải `BENCH`, không phải `TEST`, và `GG_AIA_STU` thì ngược hẳn: đúng hai
> dòng đo ngay trên đã chỉ ra nó là Vertex express chứ không phải AI Studio. Tên mới lấy từ
> `dim_agent.code`, trùng với nhãn đang dán trên tuyến. Xem change `name-the-crm-key-after-its-agent`.

Nhánh gọi bằng khoá của CRM dựng `genai.Client(api_key=…)`, mặc định đi AI Studio, tức đi đúng cửa
bị 403. **Đổ khoá này vào biến `KEY_FALLBACK` rồi dùng nhánh đó sẽ hỏng.** Đó là lý do đường dự
phòng dùng tệp service account chứ không dùng biến khoá.

### 2.5 Bảy phép kiểm tự động, chạy trong mili giây

`tests/test_fallback.py` trong repo CRM. Dùng client giả nên không gọi mạng, không tốn tiền:

| Phép kiểm | Khẳng định điều gì |
|---|---|
| phân loại ba câu lỗi | ba loại lỗi vẫn phân biệt được với nhau |
| đổi đường đúng ngưỡng | ba lần liên tiếp mới đổi, và **lượt đó chạy xong** chứ không bị bỏ |
| một lượt hỏng lẻ | lượt thành công đặt bộ đếm về không |
| lỗi 400 | không kích hoạt đổi đường |
| nhiều luồng | ba worker cùng hỏng vẫn chỉ đổi **một** lần, gửi **một** thư |
| thăm dò định kỳ | thăm dò thành công thì quay về, và sự cố sinh **đúng hai** thư |
| thăm dò hỏng | không đổi trạng thái, im lặng dùng tiếp đường thẳng |

---

### 2.6 Diễn tập cắt đường tới Gateway: 8 trên 8 lô chạy xong

Cắt đường tới Gateway ngay sau lô thứ ba, rồi chạy tiếp năm lô nữa:

```
   lo 1-3   OK  (gateway)
   >>> cat duong toi Gateway
   lo 4-8   OK  (THANG)      <- doi duong ngay trong lo 4, khong lo nao bi bo
```

Kết quả: **8/8 thành công, 0 lô bị bỏ**, 5 lượt đi đường thẳng.

Đây là diễn tập bằng cách trỏ sang một cổng không ai nghe, **không** dừng container thật. Hai
cách cho cùng kết quả phân loại, nhưng khác câu lỗi: dừng container cho lỗi phân giải tên, cổng
chết cho lỗi từ chối kết nối. Nhánh phân giải tên **chưa** được diễn tập với thiết kế mới.

### 2.7 Diễn tập dừng container thật: 60 trên 60 lô chạy xong

Anh Tuấn tự dừng `gateway-lb` giữa lúc chạy, rồi bật lại. Đây là kiểu mất Gateway cho lỗi **phân
giải tên**, khác với bài ở 2.6.

```
   lo 1-8     duong THANG     <- doi duong ngay trong lo dau gap su co
   lo 9-60    qua gateway     <- tham do thanh cong, tu quay ve
```

| | |
|---|---|
| Tổng số lô | 60 |
| Bị bỏ | **0** |
| Đi đường thẳng | 8 |
| Gateway mất | 69 giây |
| Trạng thái lúc kết thúc | đã về Gateway |

**Và bài đo này lộ một thiếu sót trong chính mã vừa viết.** Không câu lỗi nào được ghi lại, vì
fallback làm việc quá tốt: không lô nào ném lỗi ra ngoài, nên câu lỗi thật bị nuốt gọn. Diễn tập
chứng minh **hành vi** đúng nhưng không chứng minh được Gateway hỏng **kiểu gì**.

Đã sửa: lúc đổi đường, mã ghi thêm câu lỗi cuối cùng nhận được từ Gateway. Hai kiểu hỏng đòi hai
cách xử khác nhau khi lên server, và không ghi thì không phân biệt được.

### 2.8 Ngưỡng đổi đường phải nhỏ hơn hoặc bằng số lần thử lại trong một lô

Bản đầu của bài diễn tập gọi thẳng tầng client và đo ra **2 lô bị bỏ**. Đọc vội thì đó là lỗi
thiết kế. Thật ra là **bài đo sai tầng**: nó bỏ qua vòng thử lại ba lần nằm bên trong
`call_llm_batch`, tức tầng mà pipeline thật dùng.

Đo lại đúng tầng cho 0 lô bị bỏ. Nhưng phép đo hỏng ấy để lại một ràng buộc thật:

```
   FALLBACK_FAIL_THRESHOLD  <=  call_llm_batch(max_retry)
              3                          3
```

Đặt ngưỡng lớn hơn số lần thử lại thì **lô đầu tiên gặp sự cố vẫn bị bỏ** — đúng cái mà change
này sinh ra để tránh. Ràng buộc này đã ghi cạnh dòng khai báo trong tệp cấu hình của CRM.

---

### 2.9 Bản chạy thử không đụng SharePoint

Pipeline CRM **không có cờ chạy khô**: bật lên là tải SharePoint thật, ghi đè tệp Excel thật, và
gửi thư cho người thật. Nên `tests/run_sample_offline.py` dùng đúng hai thứ mà pipeline dùng, tầng
gọi lô và cơ chế checkpoint, rồi bỏ qua mọi thứ khác.

| Lần chạy | Kết quả |
|---|---|
| Lần một, Gateway sống | 3 dòng vào sổ, 0 bị bỏ |
| Lần hai, cùng checkpoint | 0 dòng phải làm, **0 dòng ghi hai lần** |
| Lần ba, fallback bật, Gateway không tới được | 3 dòng vào sổ qua đường thẳng, 0 bị bỏ |

Phép đếm đôi đếm **số lần mỗi dòng được ghi**, không đếm số bản ghi trong sổ. Sổ là một `dict` nên
"mỗi khoá một bản ghi" đúng bằng cấu trúc và không chứng minh được gì.

**Điều này KHÔNG đóng được ô "lô cỡ thật".** File mẫu chỉ có ba dòng, ra đúng một lô. Lô cỡ thật là
25 dòng một lô và hàng trăm lô.

---

## 3. Một lỗi mắc phải khi làm, ghi để không lặp

Bản đầu của bộ kiểm **gửi thư thật vào hộp thư người thật** mỗi lần chạy. Hai phép kiểm thay hàm
gửi thư để đếm số thư, nhưng ba phép kiểm còn lại thì không, nên chúng gọi thẳng ra ngoài.

Nhật ký không hiện điều đó vì dòng báo gửi thành công nằm ở mức `INFO`, còn bộ kiểm chạy ở mức
`WARNING`.

Cách sửa: chặn đường gửi thư **một lần cho cả bộ kiểm** trong `main()`, thay vì để từng phép kiểm
tự lo. Bài học chung: một phép kiểm chạm tới thế giới bên ngoài phải bị chặn ở chỗ **không phép
kiểm nào bỏ sót được**, không phải ở chỗ người viết nhớ ra.

---

## 4. Điều SUY LUẬN — chưa chứng minh, đừng đọc thành đã biết

- **Ngưỡng ba lần và chờ 60 giây là con số đề nghị, chưa đo.** Chưa có sự cố thật nào ngoài diễn
  tập 10/09 để hiệu chỉnh.
- **Thư đã rời máy, nhưng chưa ai xác nhận nó vào hộp thư.** Máy chủ thư có thể xếp vào thư rác.
  Một phép báo động không tới nơi thì không khác gì không có.
- **Chưa diễn tập trên đường thật.** Bảy phép kiểm dùng client giả. Việc dừng `gateway-lb` giữa
  lúc chạy chưa làm với thiết kế mới.

---

## 5. Điều phải làm trước khi lên server

- **Xin khoá thuộc `crm-500509`** để phí về đúng project. Hiện phí rơi vào `crm-test-508114`, tức
  ra ngoài mọi con số của dashboard. Chốt 12/09: giai đoạn phát triển chấp nhận lệch.
- **Cân nhắc thông tin Azure sau cuộc họp.** Có thì cả hai agent dùng được đường Graph sẵn có, và
  thư gửi bằng hòm thư công ty thay vì Gmail cá nhân.
- **Đặt lại ngưỡng và khoảng chờ** theo số đo của sự cố thật đầu tiên.

---

## 6. Hai câu hỏi còn treo

**Lỗi quá hạn mức có nên đổi đường không?** Hạn mức ảo của Gateway thì đi thẳng có thể qua, nhưng
hạn mức thật của Google thì không. Từ phía agent chưa phân biệt được hai loại. Change này cố ý
không làm, và giữ nguyên nhánh lùi lịch sẵn có.

**Mã project `60854134008` ứng với project id nào?** Biết mã số từ nhật ký cũ nhưng chưa biết tên.
Thử tra bằng công cụ dòng lệnh thì bị chặn quyền. Không chặn việc gì hiện tại.

---

## 7. Cái giá đã trả, ghi rõ để người sau không tưởng nhầm

Tài liệu kiến trúc gọi việc đi qua Gateway là **bắt buộc về mặt kỹ thuật**, vì agent không giữ khoá
nhà cung cấp nên nó *không thể* đi vòng.

**Câu đó không còn đúng cho agent CRM.** Sau change này agent có `sa-key.json` trong tay và đi thẳng
được. Đổi lại là hệ thống không đứng khi Gateway chết, đúng thứ tự ưu tiên mà lead chốt ngày 10/09:
*"cái việc mình track không được ưu tiên trước hệ thống ổn định"*.
