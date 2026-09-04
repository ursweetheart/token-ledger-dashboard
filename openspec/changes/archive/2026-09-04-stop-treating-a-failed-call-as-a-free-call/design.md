## Context

Sổ Gateway trông như tự nó nhất quán: `fact_call` gần trùng `LiteLLM_SpendLogs` — 45.201 so
với 45.240 token ngày 31/08 — và bộ kiểm hiện tại xác nhận điều đó. Chữ "gần" mới là chỗ
đáng ngờ: 39 token chênh lệch ấy là 3 bản ghi bộ nạp đánh rơi mà không ai đếm.

Lỗi lớn hơn chỉ lộ ra khi đặt một nguồn **thứ hai** cạnh nó. Ngày 04/09/2026,
sổ Cloud Monitoring của chính project mà Gateway gọi tới cho thấy nhà cung cấp đã phục vụ
41 request với `response_code = 200` **cho tất cả**, trong khi LiteLLM ghi 5 lượt hỏng —
2 trong số đó thực ra đã được phục vụ xong và đã tiêu token.

Ba ràng buộc định hình thiết kế:

1. **Không được sửa số đã nạp.** Ta biết tổng thiếu bao nhiêu, không biết thiếu ở dòng nào.
2. **Khoá của Gateway là free tier.** Lưu lượng này sẽ không bao giờ lên hoá đơn Google, nên
   đường đối chiếu bắt buộc đi qua Monitoring, không qua `fact_billing_daily`.
3. **Cửa sổ lưu giữ của Monitoring không ổn định.** Đo 04/09 trên `request_count`: mép ở
   22/01/2026, tức 225 ngày, giống nhau trên hai project độc lập. Ghi chú cũ ghi 196 rồi
   112 ngày, nhưng đo trên **họ metric khác** (token, độ mịn 60 giây) nên không so trực
   tiếp được. Chưa họ nào được đo đủ để coi là hằng số ⇒ vẫn phải kéo về đĩa.

## Goals / Non-Goals

**Goals:**

- Đặt tên cho hình dạng lỗi và ghi nó vào spec, để nó không phải được phát hiện lại.
- Có một nguồn đối chứng nằm trong database, cập nhật được bằng đường ống hiện có.
- Một phép kiểm tự động bắt được lỗi này cho **mọi** project Gateway gọi tới, không riêng
  project đang đo.
- Phép kiểm nói thẳng khi chưa kiểm được, thay vì báo đạt trên tập rỗng.

**Non-Goals:**

- **Không** suy đoán, nội suy, hay phân bổ token cho lượt hỏng.
- **Không** sửa LiteLLM. Đây là phần mềm thượng nguồn; ta đo hành vi của nó, không vá nó.
- **Không** đưa số của nhà cung cấp vào `usage_resolved`. Nó là **ý kiến thứ hai**, không
  phải một nguồn để cộng vào tổng.
- **Không** đụng frontend hay backend đọc. Change này dừng ở tầng dữ liệu và tầng kiểm.

## Decisions

### ① Số của nhà cung cấp vào bảng riêng, KHÔNG vào `fact_usage_daily`

Bảng mới `fact_provider_daily`, khoá `(day, provider_project, raw_model)`, giữ
`requests`, `input_tokens`, `output_tokens`.

Khoá dùng `raw_model` — tên model **nguyên gốc** nhà cung cấp báo — chứ không dùng `model_id`.
Lý do là ràng buộc của chính PostgreSQL: `model_id` phải để NULL được cho trường hợp nhà cung
cấp báo một tên ta chưa ánh xạ, mà cột NULL thì không làm khoá chính được. Ép nó NOT NULL sẽ
biến "chưa ánh xạ được" thành "không lưu được", tức mất dữ liệu để giữ một khoá đẹp. Cùng
khuôn với `fact_app_daily.raw_model`.

*Vì sao không dùng lại `fact_monitoring`:* đường nạp monitoring hiện quy project về agent
qua `dim_agent.gcp_project_id`. Project của Gateway **không thuộc agent nào** — nó là điểm
quan sát của chính Gateway. Nhét nó vào `dim_agent` để đường ống chạy được sẽ tạo ra một
"agent" không tồn tại, và agent giả đó sẽ hiện lên dashboard.

*Vì sao không tính tại chỗ lúc chạy audit:* `audit_db.py` sẽ phải gọi mạng và cần khoá
Google. Bộ kiểm phải chạy được offline trên database, và đó là kỷ luật đang có.

Bảng này **không** được `usage_resolved` đọc. Ghi rõ điều đó trong chú thích của migration,
vì nó là loại nhầm lẫn dễ xảy ra nhất sáu tháng sau.

### ② Metric token vào trả về hai chuỗi trùng nhau — phải chọn, và phải chứng minh là trùng

Đo được 04/09: `quota/generate_content_free_tier_input_token_count/usage` trả về **hai**
chuỗi cho cùng một lượng token, tách theo `limit_name`:

```
   GenerateContentInputTokensPerModelPerDay-FreeTier      47.613
   GenerateContentInputTokensPerModelPerMinute-FreeTier   47.613
```

Cộng cả hai là nhân đôi — đúng cái bẫy đã làm phép đo đầu tiên ra "lệch 2,19 lần".

Bộ nạp lọc lấy đúng nhánh `...PerDay...`, **và** so nó với nhánh `...PerMinute...`:
lệch quá 0 thì **dừng và báo**, không tự chọn bên nào. Giả định "hai nhánh luôn bằng nhau"
là giả định về hành vi của Google, không phải sự thật ta kiểm soát — nên nó phải được kiểm
mỗi lần nạp, không phải tin một lần rồi thôi.

### ③ So theo NGÀY, không theo giờ

Google gắn nhãn ô theo `endTime`, LiteLLM ghi theo `startTime`. Một lượt bắt đầu 01:59 và
kết thúc 02:00 rơi vào hai giờ khác nhau ở hai sổ. Đo được: giờ 01h Google thấp hơn 12
token, giờ 02h cao hơn 5.864 — một phần của chênh lệch đó chỉ là ranh giới ô.

Ngày là đơn vị nhỏ nhất mà hai sổ so được mà không sinh nhiễu giả. Bảng theo giờ vẫn giữ
nguyên cho mục đích khác; phép kiểm này chỉ đọc mức ngày.

### ④ Ngưỡng một chiều, không phải ngưỡng phần trăm

Kỷ luật của `gateway-cache-reconciliation` là **ban hành ngưỡng trước kỳ đo**. Ở đây ta đã
đo rồi, nên đặt một ngưỡng phần trăm bây giờ là chọn con số vừa khít với kết quả đã biết.

Thay vào đó, phép kiểm dùng **bất biến một chiều** — thứ không cần ngưỡng vì chiều ngược
lại là bất khả:

```
   HONG   provider_requests  <  so dong fact_call        ta ghi nhieu hon nha cung cap phuc vu
   HONG   provider_tokens    <  token fact_call          ta khai nhieu hon nha cung cap ban
   LUU Y  provider_*         >  fact_call *              thieu hut da biet -- IN RA CON SO
   CHUA KIEM DUOC            0 ngay giao nhau
```

Chiều "nhà cung cấp nhiều hơn" là **kỳ vọng**, không phải lỗi — nó đúng bằng phần lượt hỏng
đã tiêu token. In con số ra là mục đích của phép kiểm; báo hỏng vì nó thì phép kiểm sẽ đỏ
vĩnh viễn và bị bỏ qua.

Chiều ngược lại thì không có cách nào đúng được, nên nó hỏng thẳng.

### ⑤ `pull_monitoring.py` nhận `--account`, mặc định không đổi

Thêm tham số `--account`; bỏ trống thì dùng tài khoản đang hoạt động của `gcloud`, đúng như
hành vi hiện tại. Danh sách `PROJECTS` giữ nguyên 7 project sản xuất; project của Gateway
truyền qua `--projects` sẵn có.

Thư mục kết quả phải mang cả tài khoản trong tên, vì hai tài khoản kéo cùng ngày cùng độ mịn
sẽ ghi đè nhau — đúng loại mất dữ liệu mà quy ước "không bao giờ ghi đè thư mục kéo cũ"
sinh ra để chặn.

### ⑥ Tên gọi

Hình dạng lỗi được gọi là **"lượt hỏng không phải lượt miễn phí"** trong tài liệu tiếng Việt,
và định danh mã nguồn dùng `failed_is_not_free`. Định nghĩa đầy đủ, dùng nguyên văn ở mọi nơi:

> Nhà cung cấp đã phục vụ xong một request và đã tính token cho nó, nhưng proxy hỏng **sau đó**,
> nên sổ ghi lượt ấy là hỏng với 0 token và 0 mili-giây. Loại nó khỏi bảng tổng hợp là đúng;
> coi phần bị loại bằng không là sai.

## Risks / Trade-offs

- **Cửa sổ Monitoring không ổn định, bằng chứng có thể tự hết hạn** → Kéo về đĩa theo thư mục
  ngày và không bao giờ ghi đè. Đo 04/09: mép ở 22/01/2026 nên 31/08 còn dư ~221 ngày, **không
  gấp**. Nhưng con số đó là của `request_count`; họ metric token chưa đo lại, và ghi chú cũ nói
  nó từng hẹp hơn nhiều.
- **Bộ nạp đánh rơi bản ghi trong im lặng** → Đo được 3 dòng / 39 token ngày 31/08, một trong
  số đó là lượt thành công có tag đầy đủ. Không phép kiểm nào bắt được, vì không ai so số dòng
  sổ nguồn với số dòng đích. Thêm phép đếm ở khâu nạp và một phép kiểm so hai con số đó.
- **Mẫu đo rất nhỏ: 5 dòng hỏng trên toàn sổ, tất cả cùng một ngày** → Không được suy ra tỷ lệ
  từ nó. Change này xây *phép đo*, không kết luận *độ lớn*. Con số 12,21% là của một ngày và
  của một nguyên nhân, phải luôn được nói kèm chữ "ngày 31/08".
- **Chỉ 1 trong 8 agent đi qua Gateway** → Phép kiểm sẽ báo "chưa kiểm được" cho phần lớn
  project trong thời gian dài. Đó là câu trả lời đúng, không phải phép kiểm hỏng.
- **Hai tài khoản Google làm khâu xác thực phức tạp hơn** → Giữ mặc định y nguyên; tài khoản
  thứ hai chỉ được dùng khi gọi tên tường minh.
- **Bảng mới có thể bị hiểu nhầm là nguồn thứ năm** → Chú thích trong migration và trong
  `docs/reference/tu-dien-database.md` phải nói thẳng: nó là ý kiến thứ hai để đối chiếu,
  `usage_resolved` không đọc nó.

## Migration Plan

Migration chỉ tiến, không có đường lùi — theo `schema-migrations` đang có. Bảng mới là bảng
rỗng dựng thêm; không đụng bảng nào đang có, nên không cần bước quay lui dữ liệu.

Thứ tự triển khai: dựng bảng → mở đường kéo → nạp → thêm phép kiểm → chạy lại toàn bộ bộ kiểm
và so với mốc `73 phép / 66 đạt / 7 lưu ý / 0 hỏng`.

## Open Questions

- Vì sao `lG-UarHhIYXmosUPv4ihmQ8` — lượt thành công, có tag, 25 token, lúc `00:59:47` — không
  vào được `fact_call`? Nghi mốc nước của bộ nạp hoặc ranh giới ngày, **chưa chứng minh**. Phải
  trả lời trong change này, vì đây là mất dữ liệu chứ không phải khác biệt cách đếm.
- Còn bao nhiêu ngày nữa Monitoring giữ được 31/08? Chưa đo. Ảnh hưởng tới thứ tự làm việc
  chứ không tới thiết kế.
- Hai lượt bị ghi 0 token là **cùng một request thử lại hai lần** hay **hai request khác
  nhau**? Bằng chứng nghiêng về thử lại (hai dòng hỏng lúc 02:27 nằm giữa hai cặp giống hệt
  nhau), nhưng `LiteLLM_SpendLogs` không giữ trường nào nối một lượt thử lại về lượt gốc.
  Không chặn change này.
