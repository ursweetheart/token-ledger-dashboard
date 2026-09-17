## Context

Đọc ngày 17/09/2026. Hai khoá nhà cung cấp đang dùng, và các tuyến ăn theo chúng:

```
KEY_GOOGLE_AI_STU ─────┬─ gemini-flash          (không nhãn, hôm nay không ai gọi)
                       ├─ gemini-flash-preview  (không nhãn, CHƯA ĐO ai gọi)
                       └─ gemini-flash-lite     tags: ["dms-feedback"]

KEY_BENCH_CRM_TEST_
    GG_AIA_STU ────────── gemini-2.5-flash      tags: ["crm-feedback"]
```

Bảy chỗ nhắc tên biến CRM, chia làm hai loại:

| Tệp | Dòng | Loại |
|---|---|---|
| `.env` | — | máy, không nằm trong kho |
| `.env.example` | 79 | sửa |
| `docker-compose.yml` | 121, 133 | sửa |
| `docker/gateway/entrypoint.sh` | 16 | sửa |
| `docker/gateway/config.gateway.yaml` | 86 | sửa |
| `docker-compose.bench.yml` | 45 | sửa |
| `docs/reference/fallback-crm-12-09.md` | 57 | sửa |
| `docs/reference/gateway-architecture-and-agent-integration.md` | nhiều chỗ | sửa |
| `docs/decisions/che-do-hong-cua-gateway-2026-09-10.md` | 35 | **lịch sử, giữ** |
| `openspec/changes/archive/…` | nhiều chỗ | **lịch sử, giữ** |

## Decisions

### D1 — Tên mới là `KEY_CRM_FEEDBACK`, lấy từ `dim_agent.code`

Ba phương án đã cân:

| Tên | Bỏ vì |
|---|---|
| `KEY_CRM` | ngắn nhưng không khớp định danh nào đang có; "CRM" một mình còn mơ hồ với các hệ thống CRM khác |
| `KEY_VERTEX_CRM` | nhét tên nhà cung cấp vào tên biến — chính là cái đã cắn hôm 10/09. Đổi đường đi từ AI Studio sang Vertex thì tên lại sai lần nữa |
| `KEY_CRM_FEEDBACK` | **chọn** |

`crm-feedback` đã là `dim_agent.code` của agent 7, và đã là nhãn trên tuyến. Lấy nó làm tên biến thì
được ba thứ:

1. Agent thêm sau có sẵn tên, không phải bàn: `contact-center` → `KEY_CONTACT_CENTER`.
2. Tên không mang nhà cung cấp, nên đổi đường đi không phải đổi tên.
3. Sinh ra một bất biến **kiểm được bằng máy**: tuyến mang `tags: ["X"]` thì `api_key` phải là
   `os.environ/KEY_<X viết hoa, gạch ngang thành gạch dưới>`.

Điểm 3 chưa thành phép canh trong change này — xem D4.

### D2 — Đổi cả năm tệp trong MỘT commit, không chia nhỏ

Sự cố 10/09 sinh ra đúng vì việc đổi tên bị chia nhỏ: `.env` đổi trước, hai tệp còn lại đổi sau, và
`${VAR:-}` nuốt mất khoảng trống ở giữa. Chia nhỏ ở đây không phải cách làm thận trọng — nó **là**
cơ chế gây lỗi.

Hai chế độ hỏng không cân nhau, và đó là lý do phải cùng commit:

```
sót .env / docker-compose.yml / entrypoint.sh
    → entrypoint in "STOP: … is missing." → container không lên     KÊU TO

sót config.gateway.yaml
    → container khoẻ, /health/liveliness = 200, mọi phép kiểm đạt
    → chết đúng lúc có người gọi thật: HTTP 500                      IM LẶNG
```

### D3 — Không đụng `KEY_GOOGLE_AI_STU` trong change này

Nó phục vụ ba tuyến, chỉ một tuyến mang nhãn. Đặt tên nó là `KEY_DMS_FEEDBACK` là khẳng định "khoá
này của agent DMS" — đúng hôm nay **nếu** không ai gọi hai tuyến kia, và sai kể từ ngày có người gọi.

Câu phải trả lời trước, bằng một truy vấn chỉ-đọc trên `LiteLLM_SpendLogs`: **`gemini-flash-preview`
có dòng nào không, và mỗi dòng mang nhãn gì?**

| Kết quả | Việc tiếp theo |
|---|---|
| 0 dòng | đổi tên được, kèm một dòng ghi rõ hai tuyến không nhãn đang dùng ké |
| có dòng, nhãn trống | **gấp hơn đổi tên**: tiền đang bị `load_gateway.py` bỏ vào `dropped_no_tag` mỗi đêm |
| có dòng, nhãn của agent khác | khoá dùng chung, không đặt tên theo một agent được |

Ba kết quả dẫn tới ba việc khác nhau. Gộp vào change này là đoán thay cho đo.

#### Đã trả lời 17/09/2026 — và là **trường hợp thứ tư**, không nằm trong bảng trên

Hỏi `LiteLLM_SpendLogs`, miễn phí:

```
model = gemini/gemini-3-flash-preview
   17 dong · 170 token · nhan DINH DANH: khong co
   khoa: MASTER KEY      end_user: trong
   07/09/2026  07:06:48 -> 07:07:51     (63 giay)
```

**Không agent nào dùng tuyến này.** Mười bảy dòng ấy là một đợt **gọi thử bằng master key**, 10
token mỗi lượt, gói trong 63 giây của một ngày duy nhất cách đây mười ngày. Không có `end_user`,
không có khoá ảo, không lặp lại ngày nào khác.

Nên không rơi vào ô "tiền đang bị bỏ mỗi đêm": 170 token là lượng không đáng kể, và nguồn đã dừng.

**Hệ quả:** rào chắn cho việc đổi tên `KEY_GOOGLE_AI_STU` đã được gỡ — hôm nay chỉ DMS dùng khoá ấy
cho lưu lượng agent thật. Nhưng việc đổi tên đó **vẫn nằm ngoài change này**: nó cần xử lý luôn hai
tuyến không nhãn và ràng buộc đơn giá bản preview. Mở change riêng.

**Vẫn còn đúng và vẫn phải làm trước:** `gemini/gemini-3-flash-preview` **cố ý** không có trong
`rules.GATEWAY_MODELS`, vì `guess_model` sẽ gộp bản preview vào bản chính thức trong khi đơn giá hai
bản chưa ai kiểm. Có agent nào định dùng tuyến ấy thật thì phải chốt đơn giá trước.

Kèm một ràng buộc đã ghi sẵn, đúng cho cả ba trường hợp: `gemini/gemini-3-flash-preview` **cố ý**
không có trong `rules.GATEWAY_MODELS`, vì `guess_model` sẽ gộp bản preview vào bản chính thức trong
khi đơn giá hai bản chưa ai kiểm. Nên trước khi có agent nào dùng tuyến ấy thật, phải chốt đơn giá.

### D4 — Phép canh kiểm "có mặt đủ ba nơi", chưa kiểm "khớp nhãn"

Bất biến ở D1 điểm 3 (nhãn ↔ tên khoá) chặt hơn, nhưng hôm nay **chưa đúng trên cây**:
`KEY_GOOGLE_AI_STU` phục vụ tuyến mang nhãn `dms-feedback`. Bật phép canh ấy là CI đỏ ngay, và cách
chữa lại nằm ở D3 — thứ change này cố ý để ngoài.

Nên phép canh trong change này kiểm điều yếu hơn nhưng **đúng ngay hôm nay và bắt đúng sự cố 10/09**:

> Mọi biến `os.environ/KEY_*` mà `config.gateway.yaml` tham chiếu phải có mặt ở cả ba nơi — vòng
> kiểm bắt buộc của `entrypoint.sh`, khối `x-litellm` của `docker-compose.yml`, và
> `docker-compose.bench.yml`.

Thử ngược lại trên cây của 10/09: `config.gateway.yaml` tham chiếu `KEY_BENCH_CRM_TEST`, biến ấy
không có trong `entrypoint.sh` → phép canh đỏ. Bắt được.

Bất biến nhãn ↔ tên khoá là việc của change đổi tên `KEY_GOOGLE_AI_STU`, sau khi D3 được trả lời.

### D5 — Không giữ bí danh cho tên cũ

Compose có thể viết `${KEY_CRM_FEEDBACK:-${KEY_BENCH_CRM_TEST_GG_AIA_STU:-}}` để `.env` cũ vẫn chạy.
Bỏ, vì nó giữ lại đúng cơ chế đã gây sự cố: một chuỗi `:-` lồng nhau vẫn quy về chuỗi rỗng khi cả
hai tên đều thiếu, và người vận hành không biết mình đang chạy bằng tên nào.

Chế độ hỏng phải là **không chạy**. `entrypoint.sh` dừng hẳn với thông báo nêu đúng tên biến và bảo
xem `.env.example` — đó là cách báo đúng.

## Risks / Trade-offs

| Rủi ro | Mức | Chặn bằng |
|---|---|---|
| Sót `config.gateway.yaml` → tuyến CRM chết im lặng | cao | D2 một commit; task 2.3 bắt buộc một lượt gọi thật; phép canh D4 |
| Máy khác đang chạy Gateway nhận commit mà chưa sửa `.env` | trung bình | Chế độ hỏng là "không chạy" và thông báo nêu đúng tên biến. Ghi vào phần bàn giao của task 5.2 |
| Dựng lại container làm `gateway-lb` giữ IP cũ | trung bình | Task 3.3 khởi động lại `gateway-lb` sau cùng. Change `keep-the-load-balancer-pointed-at-live-instances` xoá bước này |
| `docker-compose.bench.yml` sót → bench không lên | thấp | Kêu to, không im lặng. Vẫn nằm trong danh sách một commit |
| Đổi nhầm sang tên của agent khác | **đã suýt xảy ra** | Task 0.1 xác minh bản đồ khoá bằng đo, trước khi gõ một ký tự nào |

## Migration

Không có dữ liệu để chuyển. Trên mỗi máy đang chạy Gateway:

```
1. sửa .env:  KEY_BENCH_CRM_TEST_GG_AIA_STU=…  →  KEY_CRM_FEEDBACK=…   (giữ nguyên giá trị)
2. docker compose --profile gateway up -d litellm-1   (dựng lại, không phải restart)
      đợi healthy
3. docker compose --profile gateway up -d litellm-2
      đợi healthy
4. docker compose --profile gateway restart gateway-lb
5. một lượt gọi thật qua tuyến CRM → 200
```

Bước 4 bỏ được sau change `keep-the-load-balancer-pointed-at-live-instances`.
