## Context

Sổ Gateway (`LiteLLM_SpendLogs`, database `litellm`) và sổ dashboard (`token_ledger_v2`)
nằm **cùng một instance PostgreSQL** nhưng là hai database. Tách như vậy là quyết định
31/08/2026 và lý do vẫn còn nguyên giá trị: LiteLLM tự chạy migration bằng Prisma, gộp
chung nghĩa là mỗi lần nâng phiên bản nó có quyền `ALTER` ngay trong database chứa dữ liệu
dashboard.

Đường nối hiện tại là `db/load_gateway.py`, mở hai kết nối và ánh xạ ở tầng Python. Nó
được gọi bởi `scripts/refresh_gateway.py` — bốn bước, đúng thứ tự, đo 03/09/2026 mất
**~1,8 giây** một chu kỳ, và **đã có sẵn `--every`** để chạy vòng lặp.

Cái thiếu duy nhất: không dịch vụ nào chạy nó. `grep refresh_gateway docker-compose.yml`
không ra kết quả nào.

### Đo được ngày 08/09/2026

| Đo | Kết quả |
|---|---|
| `LiteLLM_SpendLogs` | 444 dòng, 29/08 → 08/09 |
| `fact_call` phần `source='gateway'` | **41 dòng, toàn bộ ngày 31/08** |
| `fact_call` toàn bảng | 8.672 dòng (8.631 dòng nguồn `app`, tới 30/08) |
| Dòng sổ Gateway không mang tag định danh | 80/444 — bị bỏ **đúng thiết kế** |
| `refresh_gateway.py` trong compose | không có |
| `audit_db.py` có nối sang sổ Gateway | không |

## Goals / Non-Goals

**Goals:**
- Sau khi một agent gọi qua Gateway, dashboard tự thấy số mới trong vòng vài phút, **không
  ai chạy lệnh nào**.
- Độ trễ giữa hai sổ đo được, và phân biệt được với "chưa có lưu lượng".
- Khi đường làm mới chết, chuyện đó **kêu**, không im lặng.

**Non-Goals:**
- Không viết lại `db/load_gateway.py`.
- Không đổi schema, không đổi cách ba nguồn còn lại (hoá đơn, monitoring, app) được nạp —
  chúng là tệp xuất định kỳ và luôn cần một bước nạp.
- Không nhắm độ trễ bằng không. Bảng tổng hợp mịn nhất là **theo ngày**; trễ vài phút
  không đổi bất kỳ con số nào ai đọc.
- Không tự động sửa khi phép kiểm kêu. Kêu là việc của change này; sửa là việc của người.

## Decisions

### Quyết định 1 — Chạy script đã có, thay vì viết cơ chế mới

`scripts/refresh_gateway.py --every N` chạy trong một container dùng lại image
`token-ledger-tools:local`, `restart: unless-stopped`, `depends_on: postgres healthy`.

Lý do chọn: toàn bộ tri thức đã tích luỹ về sổ Gateway nằm trong `db/load_gateway.py` —
`cache_hit` là TEXT ghi chuỗi `'None'` chứ không phải NULL; `request_duration_ms = 0`
phải thành NULL; đọc `completion_tokens_details` chứ **không** phải
`prompt_tokens_details` (đọc nhầm vẫn ra số, chỉ là số của chiều ngược lại); tag định
danh là tag khớp `dim_agent.code` chứ không phải tag đầu tiên. Mỗi luật là một lần đo.
Viết lại là chuyển hết rủi ro đó sang một bản mới chưa ai đo.

### Quyết định 2 — Nhịp 120 giây

1,8 giây trên 120 giây là 1,5% thời gian. Đủ tươi cho một bảng mịn theo ngày, đủ thưa để
không phải nghĩ về tải. Đặt qua biến môi trường để đổi được mà không sửa ảnh.

### Quyết định 3 — Phép kiểm độ trễ so với **sổ Gateway**, không so nội bộ

Phép kiểm mới trong `audit_db.py` mở kết nối thứ hai bằng vai `gateway_readonly` và so
mốc thời gian mới nhất của `LiteLLM_SpendLogs` với mốc mới nhất của phần `source='gateway'`
trong `fact_call`.

Phải là **ba trạng thái**, không phải hai:

| Trạng thái | Nghĩa |
|---|---|
| ĐẠT | trễ trong ngưỡng |
| HỎNG | sổ Gateway đi trước quá ngưỡng → chưa ai làm mới, hoặc vòng lặp chết |
| CHƯA KIỂM ĐƯỢC | sổ Gateway chưa có dòng nào → **không phải ĐẠT** |

Trạng thái thứ ba là bắt buộc: chính `audit_db.py` đã ghi rằng với 0 dòng gateway thì mọi
phép kiểm gateway đều xanh một cách rỗng tuếch. Lặp lại lỗi đó ở đây thì phép kiểm mới vô
dụng đúng vào lúc cần nó nhất.

### Quyết định 4 — Ngưỡng đặt theo nhịp, và nhịp đọc TỪ SỔ chứ không từ biến môi trường

Ngưỡng = `3 × nhịp` cộng một biên. Đặt cứng một con số thì đổi nhịp sẽ làm phép kiểm sai
mà không ai nhớ ra.

**Sửa 09/09/2026 sau khi tự soát.** Bản đầu đọc nhịp từ biến môi trường
`REFRESH_EVERY_SECONDS`, và điều đó **không đủ**: biến môi trường thì *mỗi tiến trình thấy
một giá trị khác*. Đặt `REFRESH_EVERY_SECONDS=300` trong `.env` thì dịch vụ chạy 300 giây,
nhưng người chạy `python scripts/audit_db.py` trong một shell không có biến đó lấy 120 →
ngưỡng 420s thay vì 960s → **báo động giả mỗi lần chạy**. Đúng loại báo động giả mà chính
change này đi diệt.

Nên dịch vụ **ghi nhịp thật của nó** vào `ref_load_run.every_seconds`, và cả
`scripts/audit_db.py` lẫn `/api/health` đọc nhịp từ đó; biến môi trường chỉ còn là đường
lui khi chưa có nhịp tim. Một nguồn sự thật: nhịp mà tiến trình **thực sự** đang chạy.

Đã kiểm ngược: đặt `every_seconds = 600` trong sổ → ngưỡng thành 1860s ở cả audit lẫn API;
đặt biến môi trường `REFRESH_EVERY_SECONDS=9999` trong khi sổ ghi 600 → ngưỡng **vẫn** 1860s,
tức là sổ thắng.

### Đã cân nhắc và loại: `postgres_fdw` + view

Đây là hướng được đề xuất ban đầu. Nó **đã được đo trên máy thật 08/09/2026**, trong một
database dùng-rồi-bỏ (`thu_nghiem_fdw`, đã `DROP` sau khi đo), không đụng vào
`token_ledger_v2`:

| Điều kiểm | Kết quả |
|---|---|
| `postgres_fdw` có trong image | có (1.1), `dblink` cũng có; `pg_cron` **không** |
| Cài và đọc xuyên database | **chạy** — đọc đủ 444 dòng qua vai `gateway_readonly` |
| Vai chỉ-đọc có chặn ghi không | **có** — `INSERT` và `DELETE` đều bị `cannot execute ... in a read-only transaction` |
| Đẩy điều kiện lọc xuống nguồn | **có** — `Remote SQL` mang cả lọc ngày lẫn lọc `status` |
| Tra tag ra agent bằng SQL | **được**, khớp ngữ nghĩa Python (0 / 1 / nhiều tag) |
| Chi phí trên 444 dòng | 2,4 ms qua fdw so với 0,9 ms bảng cục bộ |

Chạy được, nhưng **vẫn loại**, vì ba lý do:

1. **Nó chép lại tri thức thay vì dùng lại.** Xem Quyết định 1.
2. **Bảng ngoại là ảnh chụp cấu trúc.** Đo được: khai một cột không tồn tại bên nguồn thì
   đọc cột đó ném `column ... does not exist`. Prisma đổi schema là bảng ngoại lệch. Và
   cái bẫy thật nằm ở chỗ này: **`count(*)` trên bảng ngoại đã lệch vẫn chạy sạch** — nên
   một phép kiểm kiểu "truy vấn được là ổn" sẽ báo xanh trong khi cấu trúc đã sai.
3. **Nó giải sai bài toán.** Vấn đề không phải "chép chậm", mà là "**không ai chạy**".
   fdw bỏ được bước chép nhưng vẫn phải dựng lại `fact_usage_daily`, `fact_usage_hourly`
   và phần gateway của `fact_latency_daily` — tức là vẫn cần một thứ chạy định kỳ. Đổi
   kiến trúc mà vẫn còn nguyên vấn đề.

Ghi lại đầy đủ ở đây vì hướng này **sẽ được đề xuất lại**, và lần sau nên bắt đầu từ số
đo chứ không phải từ đầu.

## Risks / Trade-offs

**Vòng lặp chết lặng lẽ** → `restart: unless-stopped` lo phần tiến trình chết. Phần nguy
hiểm hơn là tiến trình **còn sống mà không làm gì** — đúng lớp "sống mà hỏng" đã gặp ở
`/health/liveliness` của Gateway. Phép kiểm độ trễ ở Quyết định 3 là thứ bắt được nó, và
nó phải đo **kết quả** (sổ có tươi không) chứ không đo **tiến trình** (container có chạy
không).

**`build_usage_hourly.py` `SystemExit` khi tổng theo giờ lệch tổng theo ngày** → ở chế độ
vòng lặp nó sẽ kêu **mỗi chu kỳ** cho tới khi có người sửa. Đó là hành vi **đúng** và đã
được ghi trong chính script. Rủi ro thật là người ta quen với tiếng kêu rồi bỏ qua. Không
bịt bằng cách hạ mức log.

**Nhịp 120 giây nhân với lỗi** → mỗi chu kỳ hỏng ghi một khối log. Log đã xoay vòng
10m × 3 ở `x-logging`, nhưng nếu một lỗi lặp vô hạn thì log hữu ích bị đẩy ra ngoài. Cần
đo dung lượng log sau một đêm chạy.

**`GATEWAY_DSN` trỏ nhầm `localhost`** → trong container thì `localhost` là chính nó, và
triệu chứng sẽ là "không kết nối được", kêu ngay chứ không im. Nhưng phải khai tường minh
trong compose, không trông vào mặc định.

**Đường làm mới chạy đè lên chính nó** → 1,8 giây trên 120 giây thì không xảy ra hôm nay.
Nhưng `build_usage_daily.py` **xoá sạch `fact_usage_daily` rồi dựng lại**, nên hai lượt
chồng nhau sẽ nguy hiểm. `--every` là ngủ giữa hai lượt của cùng một tiến trình nên tự nó
không chồng; rủi ro thật là **chạy tay trong lúc dịch vụ đang chạy**. Phải ghi rõ điều
này ở tài liệu vận hành.

**Số liệu 1,8 giây là của 03/09** → lúc đó chỉ có 41 dòng gateway. Nay 444. Phải đo lại
trước khi chốt nhịp, đừng chép lại con số cũ. (Đo 09/09: **2.348 ms**.)

**Backend mới chạy trên database chưa migrate** → đo 09/09: `/api/health` trả **HTTP 500**,
không phải một cảnh báo. Đó là kết cục tệ nhất: `/api/health` chính là chỗ báo có gì sai,
nên nó sập kéo theo **mọi** cảnh báo khác. Đã sửa: bọc `try/except` kèm `rollback()`
(psycopg2 không autocommit ở đây, một câu lỗi làm hỏng cả giao dịch), và phát cảnh báo
`gateway_heartbeat_unreadable` nêu đúng tên migration còn thiếu.

## Migration Plan

1. Đo lại thời gian một chu kỳ trên dữ liệu hiện tại.
2. Thêm dịch vụ, chạy dưới profile riêng để bật/tắt được mà không đụng các profile khác.
3. Chạy một đêm, sáng hôm sau đo: độ trễ lớn nhất quan sát được, dung lượng log, số chu
   kỳ hỏng.
4. Quay lui = tắt dịch vụ. Không có thay đổi schema nào phải hoàn tác.
