## 1. Đo lại nền, trước khi đổi gì

- [x] 1.1 **Đo được 09/09: 2.348 ms** một chu kỳ trên 444 dòng nguồn (số cũ 1,8 giây là của 03/09 khi chỉ có 41 dòng). Đo thời gian một chu kỳ `scripts/refresh_gateway.py` trên dữ liệu **hiện tại**. Con số 1,8 giây là của 03/09 khi mới có 41 dòng gateway; nay 444. Ghi lại số đo được, KHÔNG chép lại số cũ
- [x] 1.2 **Đo được 09/09: trễ 8 ngày 13:38:35** — sổ Gateway 2026-09-08 23:55:37 (đã +7h) so với `fact_call` 2026-08-31 10:17:02; 444 dòng so với 41. Ghi lại độ trễ đang có trước khi sửa: mốc mới nhất của `LiteLLM_SpendLogs` so với mốc mới nhất của `fact_call` phần `source='gateway'`
- [x] 1.3 **Đạt**: mã thoát 0, bốn bước chạy hết, `fact_call` gateway 41 → 364 (+323 = 444 − 80 dòng không tag). Nguồn khác KHÔNG đổi: billing 1012, monitoring 606, app 371. Tổng theo giờ khớp tổng theo ngày. Chạy một lượt `refresh_gateway.py` bằng tay và xác nhận bốn bước đều chạy hết, `fact_call` vượt qua mốc 31/08
- [x] 1.4 **Đạt**: `Phân Loại Dữ Liệu CRM | agent_id 7 | 1 dòng`. Sau lượt 1.3, xác nhận dòng mang tag `crm-feedback` được gán đúng `agent_id = 7`. Đây là phép kiểm đường tag→agent trước khi agent CRM chạy thật

## 2. Cho đường làm mới chạy như một dịch vụ

- [x] 2.1 **Xong**: dịch vụ `ledger-refresh` (container `token-ledger-refresh`). Thêm dịch vụ vào `docker-compose.yml` dùng lại image `token-ledger-tools:local`, chạy `scripts/refresh_gateway.py --every <nhịp>`
- [x] 2.2 **Xong**, kiểm bằng `docker compose config`: nội suy ra `postgres:5432/litellm`, không phải `localhost`. Khai `GATEWAY_DSN` **tường minh** trong dịch vụ ấy. Mặc định dựng từ `PG_HOST` = `localhost`, mà trong container `localhost` là chính container đó
- [x] 2.3 **Xong**: nội suy ra `postgres:5432/token_ledger_v2`. Khai `TOKEN_LEDGER_DSN` tường minh, giống cách dịch vụ `tools` phải khai
- [x] 2.4 **Xong**. Đặt `restart: unless-stopped` và `depends_on: postgres` điều kiện `service_healthy`
- [x] 2.5 **Xong**: profile `refresh`. Đặt dịch vụ dưới một profile riêng, để bật/tắt được mà không đụng các profile khác
- [x] 2.6 **Xong**: `REFRESH_EVERY_SECONDS`, mặc định 120, đã ghi vào `.env.example` kèm căn cứ. Kiểm: đặt 300 thì `command` nội suy ra `"300"`. Đặt nhịp qua biến môi trường có giá trị mặc định, không viết cứng trong `command`
- [x] 2.7 **Đạt**: `config --quiet` sạch; không gọi profile thì danh sách dịch vụ là `api api-db-init pgadmin postgres web` — **không có** `ledger-refresh`; gọi `--profile refresh` thì có. Xác nhận `docker compose config` hợp lệ và dịch vụ KHÔNG khởi động khi không gọi profile

## 3. Phép đo độ trễ — thêm vào nhóm J đang có, không viết mới

Thu hẹp 09/09/2026 sau khi đọc `scripts/audit_db.py`. `group_j_gateway_row_accounting`
(dòng 1348) **đã** mở sổ nguồn qua `connect.GATEWAY_DSN`, đã có ba trạng thái, đã loại trừ
dòng bị bỏ có tên, và đã trả "CHƯA KIỂM ĐƯỢC" thay vì sập khi không mở được sổ nguồn.
Năm task của bản đầu vì thế **bị bỏ, không phải bị quên**:

- ~~3.1 mở kết nối thứ hai~~ — đã có, `audit_db.py:1394`
- ~~3.3 ba trạng thái~~ — đã có, và đã ghi thành tài liệu trong docstring nhóm J
- ~~3.4 nguồn có dòng mà đích rỗng → HỎNG~~ — đã có, suy ra từ logic tập hợp
- ~~3.7 loại trừ dòng bỏ có tên~~ — đã có, hai loại: không tag định danh, bản sao cache-hit
- ~~3.8 mở sổ nguồn thất bại → CHƯA KIỂM ĐƯỢC~~ — đã có, `audit_db.py:1396`

Còn lại đúng ba việc nhóm J chưa làm — nó so theo **tập dòng**, không theo **thời gian**:

- [x] 3.2 **Xong, và định nghĩa đổi sau khi đo.** Không so hiệu hai `max()` — cách đó tương đương hoàn toàn với phép kiểm tập hợp của nhóm J nên **không thêm gì**. Độ trễ = **tuổi của dòng nạp được cũ nhất chưa vào sổ**, tính bằng SQL trên chính kết nối nhóm J đã mở. Múi giờ: `now() AT TIME ZONE 'UTC' - "startTime"`, đã đo là khớp (dòng vừa gọi ra 60s, dòng cách 3 tiếng ra 10.748s). Thêm phép so mốc thời gian: `max("startTime" + 7h)` của sổ nguồn so với `max(ts_local)` của `fact_call` phần `source='gateway'`. **Dùng lại kết nối nhóm J đã mở**, MUST NOT mở thêm kết nối thứ hai
- [x] 3.5 **Xong**: nhãn nhóm J giờ đọc `(364 dong da nap, tre 199s/nguong 420s)`. Báo cáo nêu **độ trễ đo được bằng số**, không chỉ đạt/hỏng. Nhóm J hiện chỉ nêu số dòng
- [x] 3.6 **Xong và kiểm ngược**: `NGUONG_TRE_GIAY = 3 × NHIP + 60`. Đặt nhịp 10s → ngưỡng 90s → dòng 216s tuổi chuyển từ ĐẠT sang **FAIL**, nên ngưỡng thật sự suy từ nhịp. Chuỗi rỗng rơi về 120 (dùng `or`, cùng quy ước `db/connect.py`) chứ không nổ `ValueError`. Ngưỡng tính từ `REFRESH_EVERY_SECONDS` (mặc định 120), theo `3 × nhịp` cộng biên. MUST NOT viết cứng một con số rời khỏi nhịp
- [x] 3.9 **Xong**: độ trễ chỉ tính trên `nen_nap`, không tính trên toàn sổ nguồn — nếu không thì 79 dòng không tag định danh sẽ làm phép kiểm hỏng oan vĩnh viễn. Chỉ so trên tập dòng mà tầng nạp **thực sự nhận**. Dòng mới nhất của nguồn có thể là dòng bị bỏ có tên — so thẳng sẽ báo hỏng oan, và đó là lỗi phép kiểm chứ không phải phát hiện

### Phát hiện thật trong lúc apply (09/09/2026)

Nhóm J **báo động giả** trước khi có thay đổi này. Đo: gọi một lượt thật, chờ 12 giây, chạy
audit → `[ FAIL ] 1 dong nap duoc nhung VANG trong fact_call`, trong khi hệ thống chạy hoàn
hảo và nhịp làm mới là 120 giây. Với dịch vụ chạy **liên tục** thì tình trạng ấy gần như
thường trực — và chính docstring nhóm J đã viết: *"một phép kiểm đỏ vĩnh viễn là một phép
kiểm bị bỏ qua"*.

Đây **không phải** nới lỏng phép kiểm: nó đang gọi "mất" một dòng chưa hề có cơ hội được
nạp. Chia "đang trên đường" khỏi "mất" mới là đo đúng, và dung sai có **trần** suy từ nhịp
nên một dòng mất thật vẫn HỎNG sau vài phút — đã kiểm ngược, xem 3.6.

Hệ quả: task 3.6 không phải "thêm thông tin cho đẹp" mà là thứ **làm nhóm J đúng** dưới chế
độ làm mới liên tục.

## 4. Kiểm ngược — chứng minh phép kiểm thật sự bắt được lỗi

- [x] 4.1 **Đạt**: dịch vụ chưa chạy, dòng `y2egapL4INOMvr0PpbrMkQo` 426s tuổi > ngưỡng 420s → `[ FAIL ] ... tre 438s/nguong 420s`, thông báo nêu đúng dòng và cách suy ngưỡng. Tắt dịch vụ làm mới, gọi một lượt qua Gateway, chờ quá ngưỡng, chạy audit → phải **HỎNG**. Nếu vẫn ĐẠT thì phép kiểm vô dụng
- [x] 4.2 **Đạt**: bật `ledger-refresh`, chu kỳ đầu nạp đúng dòng đang chờ (`fact_call` gateway 364 → 365, cả bốn bảng dẫn xuất theo), audit → `[ ok ] ... tre 0s/nguong 420s`, **0 failed**. Bật lại dịch vụ, chờ một chu kỳ, chạy audit → phải **ĐẠT**
- [x] 4.3 **Đạt**: dựng database `thu_nghiem_rong` với `LiteLLM_SpendLogs` rỗng (đã `DROP` sau khi đo) → `CHUA KIEM DUOC - 0 dong de quan sat. Day KHONG phai ket qua dat.` Kiểm thêm DSN sai mật khẩu → cũng CHƯA KIỂM ĐƯỢC, `OperationalError`, audit **không chết** (mã thoát 0). Dựng tình huống sổ Gateway rỗng → phải ra **CHƯA KIỂM ĐƯỢC**, không phải ĐẠT
- [x] 4.4 **Xong** — số đo nằm ở 4.1/4.2/4.3 trên. Thêm phép nghiệm thu đầu-cuối, là điều change này nhắm tới: gọi một lượt thật qua Gateway lúc 03:02:13, **không chạy bất kỳ lệnh nào**, dòng vào `fact_call` sau **73 giây** (`xmmgapWjKbGi9tMPveq3mA0`, agent Phân Loại Phản Hồi Tiếp Thị, 3 token). Ghi lại số đo của cả ba lượt trên. "Đã thử rồi" không phải là kết quả

## 5. Phơi độ trễ cho người đọc số

- [x] 5.1 **Chọn: nhịp tim ghi vào sổ, API đọc từ đó.** Lý do: `/api/health` là chỗ đúng — docstring của `store.health()` đã phát biểu đúng nguyên tắc này (*"một bảng số đầy đủ trông y hệt một bảng số chỉ phủ 5,7%"*). Nhưng API dùng vai `api_readonly` trên `token_ledger_v2` và **không** với tới database `litellm`, nên nó không tự tính được độ trễ thật. Ba phương án đã cân: (a) cho API nối thêm sổ Gateway — nới phạm vi một dịch vụ đang cố tình chỉ biết MỘT database; (b) chỉ báo tuổi dòng gateway mới nhất — **không phân biệt được** "không ai gọi" với "đường nạp chết"; (c) nhịp tim — phân biệt được, giá là một migration. Chọn (c). Quyết định chỗ phơi: API chỉ-đọc hay ngay trên giao diện. Ghi lại lý do chọn
- [x] 5.2 **Xong**: migration `012_nhip_tim_lam_moi` tạo `ref_load_run`; `scripts/refresh_gateway.py` ghi nhịp tim **chỉ khi cả bốn bước xong**; `store.health()` phát cảnh báo. Quyền: `api_readonly` đọc được (`ALTER DEFAULT PRIVILEGES` tự cấp — đã đo, không đoán), ghi thì không. Múi giờ dùng `now() AT TIME ZONE 'Asia/Ho_Chi_Minh'` cả hai bên, đối chiếu `ts_raw(UTC)=20:02:12` ↔ `ts_local(VN)=03:02:12`. Phơi độ trễ ra chỗ đã chọn, có phân biệt ba trạng thái như mục 3.3
- [x] 5.3 **Kiểm ngược đủ bốn trạng thái qua `/api/health` thật (HTTP 200)**: chưa từng chạy → `gateway_refresh_never_ran` [high]; cũ 1 tiếng → `gateway_stale` value=3600; cũ 8 phút (ngưỡng 7 phút) → **kêu**; cũ 3 phút → **không kêu**. Biên khớp đúng 3×120+60 = 420s. Bật lại dịch vụ → cảnh báo **tự mất**. Xác nhận khi số đang cũ thì người đọc thấy được, không phải tự đi so hai database

### Phát hiện thật thứ hai (09/09/2026): `docker compose up -d` KHÔNG build lại

Hai lần trong lúc apply, tôi kết luận sai là "code không chạy": cảnh báo `gateway_stale`
không kêu ở **cả bốn** trạng thái, và nhịp tim không được ghi. Nguyên nhân cùng một chỗ:
`docker/api.Dockerfile` và `docker/tools.Dockerfile` **COPY** mã nguồn vào ảnh, không mount.
`docker compose up -d <dịch vụ>` khởi động lại container nhưng **giữ ảnh cũ**, nên container
chạy code trước khi sửa.

Đo: `docker exec token-ledger-api grep -c ref_load_run /app/backend/store.py` → **0**, trong
khi file trên máy có 2. Sau `up -d --build` → 2.

Bài học vận hành: **sửa mã Python của `backend/` hay `scripts/` thì phải `--build`**, không
thì thay đổi không tới container và triệu chứng là "code mới không có tác dụng" — im lặng,
không lỗi. Nếu không kiểm ngược thì tôi đã báo cáo 5.2 là xong trong khi cảnh báo chưa bao
giờ kêu.

### Vòng tự soát sau khi apply (09/09/2026) — ba lỗi tìm được, đã sửa

**① Thông báo tự mâu thuẫn** (lỗi thật, bắt bằng mắt trước khi chạy). Dòng "đang trên
đường" dùng `do_tre` — tuổi cũ nhất trong **cả** tập chưa nạp, kể cả dòng đã mất. Có đồng
thời một dòng mất 130s và một dòng đang bay 18s thì nó in `cu nhat 130s <= nguong 90s`, sai
ngay trên mặt chữ. Sửa: lấy tuổi cũ nhất **của chính nhóm đang bay**. Kiểm ngược bằng cách
dựng đúng tình huống đó → nay in `cu nhat 18s <= nguong 90s`, và dòng 130s vẫn HỎNG riêng.

**② Ngưỡng lệch nhịp thật.** Xem Quyết định 4 ở `design.md`. Dịch vụ nay ghi nhịp của
chính nó vào `ref_load_run.every_seconds`; audit và API đọc từ đó. Kiểm ngược: sổ ghi 600 →
ngưỡng 1860s ở cả hai bên; biến môi trường 9999 **không** thắng được sổ.

**③ `/api/health` trả HTTP 500 trên database chưa migrate.** Đo bằng cách đổi tên bảng để
giả lập. Endpoint báo-có-gì-sai mà sập thì che mất **mọi** cảnh báo khác. Sửa: `try/except`
+ `rollback()`, phát `gateway_heartbeat_unreadable` nêu đúng `UndefinedTable` và migration
012. Kiểm ngược ba trạng thái, đều HTTP 200: thiếu bảng → cảnh báo A; có bảng chưa có dòng
→ cảnh báo B; bình thường → không cảnh báo.

**Sửa kèm:** thông báo cũ in `{tuoi // 60}` làm tròn xuống, nên 430 giây hiện "7 phút" bên
cạnh "ngưỡng 7 phút" — đọc như chưa quá ngưỡng đúng lúc nó vừa quá. Nay in cả giây.

**Đã đo và KHÔNG cần sửa:** `startTime` là `NOT NULL` trong schema sổ nguồn (446/446 dòng
không NULL), nên `int(tuoi)` không thể gặp `None`.

## 6. Chạy thật một đêm rồi đo

Đổi 09/09/2026: chạy **2 tiếng** thay vì qua đêm, theo yêu cầu. Xem "Điều 2 tiếng KHÔNG
phủ được" ở cuối nhóm — đừng đọc nhóm này như thể đã chạy cả đêm.

- [x] 6.1 **Xong**: chạy liên tục 03:45:05 → 05:45:53 giờ VN, **60 chu kỳ** (đúng 7200/120). Lấy mẫu mỗi 60 giây, **119 mẫu, 0 mẫu đọc lỗi**; log và số chu kỳ đều tăng đơn điệu — nên "không có báo động" là im lặng thật, không phải dụng cụ đo hỏng
- [x] 6.2 **Đo được**: tuổi nhịp tim lớn nhất **121 giây** so với nhịp 120 giây → **chưa bao giờ bỏ một chu kỳ nào**. **0 chu kỳ hỏng**. Đếm trên toàn bộ log 69 chu kỳ: `SystemExit` 0, `Traceback` 0, `ERROR` 0, `FAILED` 0, `CANH BAO` 0, `retrying` 0
- [x] 6.3 **Đo được**: **222 byte/chu kỳ** → 156 KB/ngày. Đầy một file `10m` sau **66 ngày**; với `max-file: 3` thì giữ được **~197 ngày** log. Xoay vòng log không phải vấn đề, không cần đụng `x-logging`
- [x] 6.4 **`build_usage_hourly.py` KHÔNG kêu lệch lần nào.** Nhưng 2 tiếng đầu **không có lưu lượng mới** (`fact_call` giữ nguyên 368), nên mốc sang giờ chưa bị thử. Đã thử riêng lúc 05:57: gọi một lượt thật để tạo **khung giờ mới** `05:00` (khung cũ là `03:00`) → `fact_usage_hourly` 18 → 19 dòng, dòng vào sổ sau 31 giây, **0 dấu hiệu lỗi**. Mốc sang giờ nay là số ĐO, không phải suy luận

### Điều 2 tiếng KHÔNG phủ được — xếp vào "chưa chứng minh"

- **Mốc nửa đêm.** Cửa sổ quan sát là 03:45 → 05:45 giờ VN, nên không qua 00:00 — lúc `ts_local`
  sang ngày mới và tổng theo ngày mở khung mới. Mốc sang **giờ** đã đo (task 6.4); mốc sang
  **ngày** thì chưa. Rẻ để kiểm sau: một lượt gọi ngay sau nửa đêm rồi xem
  `build_usage_hourly` có kêu không.
- **Hành vi dưới tải kéo dài.** 60 chu kỳ đó đều chạy với **0 dòng mới**, nên chúng chứng minh
  dịch vụ *sống và đúng nhịp*, chứ không chứng minh đường nạp chịu được lưu lượng liên tục
  nhiều giờ. Đường nạp có dữ liệu mới thì đã đo riêng: 73 giây và 31 giây trên hai lượt.

## 7. Tài liệu và dọn dẹp

- [x] 7.1 **Xong**, `docs/reference/gateway-architecture-and-agent-integration.md`. Ghi thêm bẫy `--build` đã vấp hai lần. Ghi vào tài liệu vận hành: **không chạy tay trong lúc dịch vụ đang chạy**. `build_usage_daily.py` xoá sạch `fact_usage_daily` rồi dựng lại, hai lượt chồng nhau thì nguy hiểm
- [x] 7.2 **Xong**: nhịp 120s, ngưỡng 7 phút (`3 × nhịp + 60s`), căn cứ 2.348 ms/chu kỳ đo 09/09. Ghi cả ở `.env.example`. Nêu rõ hai con số cũ (0,9s của 31/08 và 1,8s của 03/09) để không ai chép lại. Ghi lại nhịp đã chọn và ngưỡng suy ra từ nó, kèm số đo ở mục 1.1 làm căn cứ
- [x] 7.3 **Xong**: bảng sáu điều kiểm trong tài liệu kiến trúc, chi tiết ở `design.md`. Ghi lại rằng hướng `postgres_fdw` đã được đo là chạy được nhưng bị loại, kèm lý do — để lần sau ai đề xuất lại thì bắt đầu từ số đo. Chi tiết ở `design.md`
- [x] 7.4 **Xong**: chú thích giờ nói rõ "chưa cài nhưng CÓ SẴN trong ảnh", kèm lý lẽ loại và lời nhắc đừng đề xuất lại từ đầu. Cập nhật chú thích ở `db/connect.py` nói `postgres_fdw` và `dblink` "CHƯA cài": đúng là chưa cài, nhưng **có sẵn trong image** — đo 08/09/2026. Câu hiện tại dễ đọc thành "không có"
