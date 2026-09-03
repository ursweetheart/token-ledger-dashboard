## Context

Change này nối hai thứ đã chạy độc lập: một Gateway đã chứng minh ghi sổ đúng (bằng `curl`,
29/08) và một agent thật đã chứng minh phân loại đúng (bản clone DMS, 29/08). Cả hai đều
đạt, nhưng chưa nối vào nhau.

Ràng buộc có sẵn phải tôn trọng:

- `config.gateway.yaml` là **nguồn sự thật**, `store_model_in_db: false` — đổi model hay
  khoá là sửa file rồi triển khai lại, có vết trong git.
- Bốn khoá cấu hình ghi sổ đã được đo 26/08 và **không được sửa mà không đo lại**:
  `user_header_name`, `store_prompts_in_spend_logs`, `turn_off_message_logging`,
  `forward_client_headers_to_llm_api`.
- `entrypoint.sh` chặn khởi động khi thiếu khoá — chế độ hỏng là "không chạy", tuyệt đối
  không phải "chạy mở".
- Bản clone DMS đã giữ nguyên tắc **không sửa file của nhóm DMS** từ 29/08. Change này phá
  nguyên tắc đó một cách có chủ ý, nên phải phá ở chỗ hẹp nhất có thể.

## Goals / Non-Goals

**Goals:**
- Một lượt `POST /api/classify/text` của DMS sinh ra một dòng `LiteLLM_SpendLogs` có
  token khác 0, cost khác 0, và nhận diện được là của `dms-feedback`
- Đường đi đó **nhân lên được cho agent thứ 2..8** mà không phải đổi kiến trúc
- Kết quả phân loại DMS trả về **không đổi** so với lượt đo 29/08 (cùng câu vào, cùng ba
  trường ra)

**Non-Goals:**
- Không nạp `LiteLLM_SpendLogs` sang `token_ledger_v2` — change kế tiếp
- Không dựng agent thứ hai — change này chỉ chứng minh đường đi bằng một agent
- Không bật cache trả lời (đã có chú thích trong `config.gateway.yaml`: cache làm
  `spend=0` khi trúng, phá phép đối chiếu với hoá đơn nhà cung cấp)
- Không đụng `watcher` / SharePoint / Teams của DMS

## Decisions

### ① Chọn `/v1/chat/completions`, không chọn `/gemini` passthrough

Lý do chính đã ghi ở proposal (passthrough không tách được 8 project). Ba mất mát còn lại,
để đủ hồ sơ khi có người hỏi lại:

| | `/v1/chat/completions` | `/gemini` passthrough |
|---|---|---|
| Router chọn deployment | có | không — đi thẳng tới Google |
| `rpm: 60` / `tpm: 1.000.000` | có (bộ đếm chung trên Redis) | không |
| `fallbacks` khi provider lỗi | có | không |
| Ghi `LiteLLM_SpendLogs` | có | có (`GeminiPassthroughLoggingHandler`) |
| Chọn khoá theo agent | có (tag) | **không** (`next()` lấy dòng đầu) |

Passthrough vẫn có thể dùng **một lần** để rút ngắn việc chẩn đoán nếu đường chính tắc,
nhưng không được để nó ở lại: nó chỉ trả lời "luồng có thông không", không trả lời "hệ
thống dùng thật được không".

### ② `drop_params: true` có thể nuốt mất chế độ JSON — đây là kiểu hỏng im lặng

`litellm_settings.drop_params: true` bỏ **im lặng** tham số mà tuyến không nhận.
`generate_json()` của DMS phụ thuộc `response_mime_type: "application/json"`. Nếu tham số
tương ứng bị bỏ, Gateway trả văn xuôi thay vì JSON — và `_generate_apikey_json`
(`gemini_client.py:170-193`) chỉ bắt **exception** rồi thử lại, mà ở đây không có exception
nào để bắt.

```
   Ky vong : JSON  -> parse dat  -> phan loai dung
   That te : van xuoi -> parse hong -> loi o TANG TREN, xa cho gay that
             ...hoac te hon: parse "gan dung" -> phan loai SAI ma khong ai keu
```

Quyết định: **phải đo riêng chế độ JSON**, không suy ra từ việc `generate()` thường chạy
được. Phép đo là một lượt `generate_json` và kiểm chuỗi trả về parse được thành `dict`.
Nếu bị nuốt, xử lý bằng cách khai tường minh chứ **không** bằng cách tắt `drop_params`
(tắt nó đổi hành vi của mọi tuyến, vượt phạm vi change này).

### ③ Hai lớp thử lại nhân với nhau, không cộng

```
   DMS   settings.max_retry           (mac dinh 3, xem gemini_client.py:68,91)
     ×
   Gateway  router_settings.num_retries: 3
     =
   toi 9 luot goi Google cho MOT request hong  --  trong khi rpm: 60
```

Một sự cố ngắn bên Google có thể tự đốt hết hạn mức, rồi hạn mức cạn lại sinh thêm lỗi.

Quyết định: **Gateway chịu trách nhiệm thử lại**, phía DMS hạ `max_retry` xuống `1`. Lý do
chọn hướng này chứ không phải hướng ngược: Gateway là chỗ duy nhất **nhìn thấy bộ đếm hạn
mức trên Redis**, nên nó biết khi nào thử lại là vô ích; DMS thì không.

Đây là một thay đổi hành vi của agent — phải ghi rõ khi báo lại nhóm DMS.

### ④ `GEMINI_MODEL` phải đổi từ tên thật sang bí danh

```
   Hom nay   gemini-3.5-flash-lite   <- ten that Google
   Qua B     gemini-flash-lite       <- model_name trong config.gateway.yaml
```

Gửi tên thật lên Gateway thì không tìm thấy tuyến — lỗi này **kêu ngay**, không nguy hiểm.
Nguy hiểm là chiều ngược lại: đặt trùng một bí danh khác thì chạy êm trên **sai model**.
Nên phép kiểm không phải "có chạy không" mà là "dòng `LiteLLM_SpendLogs` ghi đúng model
`gemini/gemini-3.5-flash-lite` không".

### ⑤ Chỗ duy nhất để cài `X-User` vào sổ

`user_header_name: "X-User"` đã bật sẵn, và `get_end_user_id_from_request_body()` được gọi
ngay trong `user_api_key_auth` — nghĩa là Gateway **đã sẵn sàng đọc** header đó. Thứ còn
thiếu là phía DMS chưa gửi.

Nhánh backend mới là chỗ duy nhất trong toàn bộ DMS để gắn header này. Bỏ lỡ bây giờ thì
sau phải mở lại đúng file đó lần nữa.

Luật đã chốt, nhắc lại để không làm sai: cho vào header là **claim `sub` của JWT**, KHÔNG
phải cả chuỗi JWT — token đổi mỗi lần đăng nhập thì một người sẽ đếm thành nhiều `end_user`.

Nếu đường `/api/classify/text` không cầm được danh tính người dùng ở tầng đó, **để trống
còn hơn điền bừa**: một `end_user` sai làm hỏng chiều người dùng của cả dashboard.

### ⑥ Nối mạng: cho DMS vào mạng của Gateway, không đi qua `host.docker.internal`

`gateway-lb` mở cổng trên `127.0.0.1:4000` — cố ý, để Gateway không ra mạng. Từ trong một
container thuộc compose project khác, `host.docker.internal` có xuyên được vào một cổng chỉ
bind loopback hay không là **chưa chứng minh** trên máy này.

Quyết định: nối container `web` của DMS vào mạng của compose Gateway qua chính
`docker-compose.override.yml` (file mới của ta), rồi gọi `http://gateway-lb:4000`. Đường
này không phụ thuộc hành vi của Docker Desktop, và giữ nguyên tính chất "Gateway không ra
mạng".

### ⑦ Không đo lại bốn khoá ghi sổ — nhưng phải đo lại **cột** một lần

Bốn khoá được đo 26/08 trên đúng đường `/v1/chat/completions`, tức đúng đường change này
dùng. Không có lý do đo lại toàn bộ.

Nhưng thân request lần này do **openai SDK** sinh ra, không phải `curl` gõ tay — nên vẫn
phải soi một lần cột `proxy_server_request` để chắc `turn_off_message_logging` xoá đúng chỗ
và header còn nguyên. Một lượt, không phải cả bộ.

### ⑧ `enable_tag_filtering` mặc định TẮT — thiếu nó thì cả quyết định ① vô nghĩa

Phát hiện khi tự soát lại change này (30/08), **sau** khi design.md bản đầu đã viết xong.

Quyết định ① dựa vào việc virtual key mang `tags` để chọn đúng khoá project. Nhưng lọc theo
tag **không tự chạy**. `router.py:430` khai `enable_tag_filtering: bool = False`, và
`tag_based_routing.py:483-484` thoát sớm:

```python
if request_enable_tag_filtering is not True and chain_default is not True:
    return healthy_deployments        # tra ve NGUYEN danh sach, khong loc gi
```

Kiểu hỏng của nó là kiểu tệ nhất trong dự án này:

```
   Thieu enable_tag_filtering
     -> get_deployments_for_tag() tra ve CA 8 deployment
     -> usage-based-routing-v2 chon theo han muc con lai
     -> request 200 OK · SpendLogs co dong · token dung · cost dung
     -> chi rieng KHOA PROJECT la chon ngau nhien
     -> hoa don Google rai deu ra 8 project, khong ai keu mot tieng
```

Nghĩa là nó **tái tạo đúng cái lỗi mà quyết định ① sinh ra để tránh**, chỉ khác là lỗi của
passthrough thì cố định vào một khoá (dễ thấy), còn lỗi này thì rải ngẫu nhiên (khó thấy hơn
nhiều).

Quyết định: `router_settings` phải khai tường minh `enable_tag_filtering: true`, và phép
kiểm nghiệm thu **không được** là "request có chạy không" — phải là một phép kiểm âm.

### ⑨ Request không mang tag thì rơi vào đâu

`_default_tagged_pool()` (`tag_based_routing.py:218-222`): nếu không deployment nào mang tag
`"default"` thì nó trả về **toàn bộ** deployment. Tức một request không tag không bị chặn —
nó đi vào bất kỳ tuyến nào.

Hệ quả phải biết trước: một agent lỡ mất `tags` trong virtual key sẽ **không báo lỗi**, chỉ
âm thầm tính vào project của người khác. Phải đo hành vi này một lần và ghi lại, chứ không
suy ra.

## Risks / Trade-offs

- **Sửa file của nhóm DMS.** Giảm thiểu bằng cách chỉ *thêm* nhánh, không đụng hai nhánh
  cũ — `GEMINI_BACKEND=apikey` vẫn phải chạy y như trước để lùi lại được trong một biến.
- **Hai phép đo dễ nhầm là một.** "DMS trả kết quả đúng" và "Gateway ghi được một dòng" là
  hai phép đo tách rời. Đạt cái này không suy ra cái kia — 29/08 đã đạt cả hai một cách
  **độc lập** mà vẫn không có luồng end-to-end nào.
- **Bảng giá của DMS thiếu `gemini-3.5-flash-lite`** (`settings.py:39`
  `GEMINI_MODEL_PRICING`) — mọi lượt gọi sẽ ra chi phí `0` ở phía DMS mà không báo gì. Nằm
  ngoài phạm vi change này, nhưng nếu ai đó đối chiếu "tiền DMS ghi" với "tiền Gateway ghi"
  thì sẽ thấy lệch và tưởng Gateway sai.
- **Chỉ chứng minh trên một agent.** Việc "8 khoá / 8 project" chỉ được *thiết kế cho*,
  chưa được *đo*, cho tới khi có agent thứ hai với khoá project riêng.
