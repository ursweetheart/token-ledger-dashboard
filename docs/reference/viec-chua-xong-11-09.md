# Việc chưa xong — rà soát 11/09/2026

Chụp lại trạng thái sau khi đóng ô 2.1 của `standardize-kpi-card-insights` và chạy xong change
`settle-what-the-bill-does-with-thinking-tokens`. Rà bốn chỗ: task của OpenSpec, checkbox trong
`docs/`, việc phải bàn giao nhóm CRM, và trạng thái git.

Mục tiêu tuần này theo anh Tuấn: **thông luồng Agent CRM**, **kiểm dữ liệu LiteLLM trả về đầy
đủ**, **hiển thị được lên dashboard**.

---

## 1. Bảng một trang

| # | việc | thuộc | chặn bởi | mục tiêu tuần |
|---|---|---|---|---|
| 1 | Ô 7.6 — so kết quả phân loại hai nhánh CRM | change `route-the-crm-agent-through-the-gateway` | **cần anh Tuấn cho sửa repo CRM** | luồng CRM |
| ~~2~~ | ~~Ô 4.4 — `fact_usage_daily` trộn hai múi giờ~~ **XONG 11/09**, đổi thành phép kiểm | change `settle-what-the-bill-does...` | — | dashboard |
| 2b | Ô 4.5 — `usage_resolved` ghép tiền Pacific với token VN trên cùng một dòng | change `settle-what-the-bill-does...` | không | dashboard |
| ~~3~~ | ~~Ô 4.1 — đổi tên cột `thinking_tokens`~~ **XONG 12/09** → `output_tokens_thinking_on` | change `settle-what-the-bill-does...` | — | dashboard |
| ~~3b~~ | ~~Ô 4.6 — lý do gỡ thẻ "Token suy luận"~~ **XONG 12/09**, sửa lý do, không dựng lại thẻ | change `settle-what-the-bill-does...` | — | dashboard |
| ~~4~~ | ~~Ô 4.3 — lưu `reasoning_tokens`~~ **KHÔNG LÀM 12/09**, token suy luận và token ra là một biến | change `settle-what-the-bill-does...` | — | dashboard |
| 5 | Ô 6.2 — bộ chọn agent cho biểu đồ ngân sách | change `revise-dashboard-ui...` | không | dashboard |
| 6 | Ô 5.3 — xem 8 card ở bề rộng hẹp | change `standardize-kpi-card-insights` | không | dashboard |
| 7 | Ba việc trước khi lên server (gateway fall back) | `docs/decisions/che-do-hong-cua-gateway-2026-09-10.md` | chỉ cần trước khi lên server | — |
| 8 | Chín việc bàn giao nhóm CRM | `docs/reference/dua-crm-qua-gateway-10-09.md` mục 7 | cần gặp nhóm CRM | luồng CRM |
| 9 | Đo tải và độ trễ đường CRM | hoãn có chủ ý 10/09 | cần trần thời gian, không phải trần tiền | luồng CRM |
| ~~10~~ | ~~`no-fake-baseline.test.js` đang hỏng~~ **XONG 11/09**, xem mục 10 | không thuộc change nào | — | dashboard |

Tiến độ change:

```
   route-the-crm-agent-through-the-gateway        54/55
   standardize-kpi-card-insights                  16/17
   revise-dashboard-ui-after-2026-07-25-review    52/53
   settle-what-the-bill-does-with-thinking-tokens 14/17
```

---

## 2. Việc trong OpenSpec — 6 ô

### 2.1 Ô 7.6 `route-the-crm-agent-through-the-gateway` — ô duy nhất còn chặn

So **kết quả phân loại** của nhánh cũ và nhánh gateway trên **cùng** đầu vào, ở
`temperature = 0,0`.

Lý do chặn cũ đã hết. Ghi chú cũ nói *"không có khoá Google nào gọi được `gemini-2.5-flash`"* —
đo lại thì khoá gọi được. Thứ chặn là **địa chỉ**: nhánh cũ mặc định đi AI Studio, khoá đang có
là khoá Vertex.

Cách gỡ: trỏ nhánh cũ sang Vertex bằng `vertexai=True` trong cùng SDK, để hai nhánh đi cùng một
địa chỉ. **Đây là sửa mã trong bản clone `CRM-Classification-Pipeline`, mà repo đó không được
commit theo lệnh người dùng.** Phải hỏi trước.

Rủi ro chính đã bị loại bằng phép đo khác: thân yêu cầu gửi Google **khớp từng trường** giữa hai
nhánh — `system_instruction`, một lượt `user`, `temperature: 0.0`, `max_output_tokens: 8192`,
`response_mime_type: application/json`. Việc còn thiếu là so **đầu ra**.

### 2.2 Ô 4.4 — `fact_usage_daily` trộn ngày Pacific với ngày Việt Nam

> **XONG 11/09, và mục này viết sai một chỗ quan trọng.** Đây **không** phải lỗ hổng chưa ai
> biết. Docstring `db/build_usage_daily.py` mục (a) đã ghi và chốt từ **14/08**. Quyết định
> cuối: **không sửa cột `day`** — hoá đơn chỉ có ngày, không có giờ, nên mọi phép quy đều là
> dịch cả ngày và chỉ đúng cho 14/24 lưu lượng, lại phá mất tính chất *tổng cả kỳ đúng tuyệt
> đối*. Thay bằng một phép kiểm thường trực trong `scripts/audit_db.py` nhóm I: quy monitoring
> về ngày Pacific rồi so với hoá đơn, lệch **0,20%** so với **81,3%** nếu để nguyên giờ VN.
> Ba nguồn cũng **không** cộng vào nhau theo ngày, `usage_resolved` chọn một nguồn. Chỗ duy
> nhất múi giờ còn lẫn trên một dòng đã tách thành ô 4.5.

```
   fact_usage_daily.day
     <- load_billing()      ngay US/Pacific   (merge_billing.py:251 lay nguyen tu file hoa don)
     <- load_monitoring()   ngay Viet Nam     (docstring noi ro)
     <- load_app()          ngay Viet Nam
     <- load_gateway()      ngay Viet Nam
```

Bốn bộ nạp, một cột `day`, một nguồn khác múi giờ. Chuỗi theo ngày của riêng nguồn billing
**lệch một ngày**. Tổng cả kỳ đúng, ngày lẻ sai. Đây là mô tả đúng, chỉ có chữ *"phát hiện
mới"* là sai — xem khối trên.

~~Phải quy bằng `America/Los_Angeles`.~~ Quy được cho **monitoring** vì nó có giờ, và phép kiểm
mới làm đúng thế. **Không** quy được cho hoá đơn vì hoá đơn không có giờ. `AT TIME ZONE` hai
lần chứ không bù hằng số: lệch 14 giờ trong PDT nhưng 15 giờ trong PST, nên bù cứng sẽ sai bốn
tháng mỗi năm.

Bằng chứng đầy đủ ở mục 11 của `token-suy-nghi-tren-hoa-don-11-09.md`: xếp monitoring theo ngày
Pacific thì **238/272 cặp ngày × project trùng khít tới từng con số**, và cả 7 project ra
**100,00%**.

### 2.3 Ô 4.1 — cột `thinking_tokens` mang tên sai

`store.py:469` cộng `value` của những dòng có nhãn `thinking_enabled = 'true'`. `thinking_enabled`
là **nhãn trên metric**, không phải metric riêng. Nên cột này đo *token ra của lượt có bật suy
nghĩ*: **47.913.327 trên tổng 52.560.360 token ra, tức 91,2%**.

Ai đọc tên cột rồi cộng nó vào output sẽ đếm hai lần 91% token ra.

> **XONG 12/09.** Tên mới là `output_tokens_thinking_on`. Ba chỗ dùng tên cũ, không hơn.
> **Không đụng database, không chạy lại luồng nạp**: tra `information_schema` thì không bảng
> nào có cột `thinking_tokens`, đây là bí danh tính lúc truy vấn. Docstring viết lại kèm bảng
> số, và sửa luôn một câu sai nằm trong đó là *"hoá đơn không tách"*. Mở ô 4.6 cho lý do gỡ
> thẻ "Token suy luận" ghi ở `app.js:3525`, vì tiền đề *"con số luôn bằng 0"* nay đã sai.

### 2.4 Ô 4.3 — số token suy nghĩ thật chưa được lưu ở đâu

`load_gateway.py:201` đọc `completion_tokens_details.reasoning_tokens` **chỉ để suy ra cờ
boolean**, con số thì bỏ. Muốn hiện token suy nghĩ lên dashboard thì thêm một cột vào `fact_call`.

Và phải trình bày kiểu **trong đó** chứ không **cộng thêm**: đo trên 46 dòng sổ Gateway thì
`reasoning` là 9.554 trên `completion` 9.968, **0 dòng** vượt. Tập con, không phải ngăn riêng.

> **KHÔNG LÀM, chốt 12/09 bởi anh Tuấn:** *"tôi muốn coi token suy luận và token output là 1:
> đều là biến token output"*. Quyết định đó đúng theo nghĩa kế toán, vì hoá đơn không có SKU
> nào cho suy nghĩ. Và nó **xoá việc chứ không thêm việc**: cả chuỗi `/api/thinking` đã được gỡ
> — một endpoint, một hàm SQL, một bảng tra ở frontend, và một trường không nơi nào đọc.
> Đường quay lại còn nguyên: `reasoning_tokens` vẫn nằm trong `metadata` của
> `LiteLLM_SpendLogs`. Mở lại ô này khi nào cần trả lời *"tắt suy nghĩ đi thì tiết kiệm bao
> nhiêu"*.

### 2.5 Ô 6.2 `revise-dashboard-ui` — bộ chọn agent cho biểu đồ ngân sách

**Chưa bắt đầu.** Đã tìm: không có phần tử chọn nào cho `c-co-agent-budget` trong `index.html`.

Có việc **chưa commit** trong `web/index.html` và `web/js/app.js` đi cùng hướng nhưng không phải
cùng một việc: nó bỏ agent bị bộ lọc loại ra khỏi biểu đồ và cho mẫu số đi theo tử số. Đoạn đó
cũng bắt được một lỗi cũ — khối `.user-scope-note` đang `hidden` mà vẫn cao 36,6px vì
`display:flex` của tác giả thắng luật `[hidden]` của trình duyệt.

### 2.6 Ô 5.3 `standardize-kpi-card-insights` — xem 8 card ở bề rộng hẹp

Xong một nửa. Hai theme đã xem trên Chrome thật và đạt. **Chưa làm:** các bề rộng màn hình, mới
đo đúng 1536px. Lưới có `@media` trong `dashboard.css` nhưng chưa xem thật ở bề rộng hẹp, mà đây
là chỗ dễ vỡ nhất sau khi nâng cỡ chữ nhãn từ 11px lên 12px và sàn giá trị từ 21px lên 24px.

---

## 3. Việc ngoài OpenSpec, trong repo này — 3 ô

`docs/decisions/che-do-hong-cua-gateway-2026-09-10.md`. Quyết định của lead: **gateway hỏng thì
phải fall back, không được chết.** Nguyên văn: *"cái việc mình track không được ưu tiên trước hệ
thống ổn định"*. Giai đoạn dev giữ cửa chặn cứng, **trước khi lên server phải sửa**:

1. Đổi cửa chặn cứng trong `entrypoint.sh` thành cảnh báo. **Giữ** phần chặn cho
   `LITELLM_MASTER_KEY` — khoá đó rỗng thì cổng 4000 mở cho bất kỳ ai, đó là lỗ hổng bảo mật chứ
   không phải mất số liệu.
2. Thêm cửa kiểm sức khoẻ soi được **từng tuyến**, không chỉ soi tiến trình.
3. Bỏ `:-` ở những biến mà rỗng đồng nghĩa với hỏng, hoặc giữ `:-` nhưng bắt buộc kèm cảnh báo.

Chỉ cần trước khi lên server, không chặn tuần này.

---

## 4. Chín việc phải bàn giao nhóm CRM

Chi tiết ở mục 7 và 7b của `docs/reference/dua-crm-qua-gateway-10-09.md`. Hai việc nặng nhất:

- **Nâng `max_output_tokens` từ `8192` lên `16000`** (`src/llm.py:274`). Token suy nghĩ ăn 96%
  hạn mức, và cả lô bị cắt cụt. Đây là chỗ **duy nhất** đặt giá trị đó, và **không đặt được ở
  tuyến Gateway** — đã thử, tham số client tự khai thắng mặc định tuyến.
- **Thêm kiểm `finish_reason == "length"`.** Bản gốc có **0** lần nhắc tới trường này, nên cắt
  cụt đi qua hoàn toàn im lặng.

Bảy việc còn lại, đều là lệch giữa tài liệu và code:

| # | việc |
|---|---|
| 1 | `GEMINI_BATCH_SIZE=40` không có tác dụng — `config.py:32` cắt xuống 25 mà không báo |
| 2 | `config.CKPT_JSON` là cấu hình chết, và cả mục cứu hộ trong `HANDOVER.md` dựng trên nó cũng chết |
| 3 | `docs/HANDOVER.md` lệch code trên **mọi** con số |
| 4 | Không có cờ dry-run nào — bật container là tải SharePoint thật và gửi email cho người thật |
| 5 | Nhánh 429 ngủ 30 giây cho một lần thử lại **không bao giờ xảy ra** |
| 7 | Câu nhắc hứa `allowed` và `locked_labels`, code **không bao giờ gửi** |
| 8 | Hai cột ngày sai định dạng ở **100%** số ô, dù câu nhắc ghi `FORMAT BẮT BUỘC: dd/mm/yyyy` |
| 9 | Tầng từ khoá gánh ít hơn tên gọi gợi ra rất nhiều |

---

## 5. Hoãn có chủ ý — đừng đọc thành bỏ quên

Chốt bởi anh Tuấn ngày 10/09: archive change
`prove-the-crm-path-survives-refusal-and-outage` ngay, tách phần đo tải thành việc riêng khi nào
thật sự cần. Ba ô còn lại cần tải thật: **nhịp thực đạt**, **độ trễ phân vị**, **chi phí thực
tế**.

Cái giá thật của phép đo đó, tính từ số đo 10/09:

| cỡ lô | thời gian mỗi lượt | tiền mỗi lượt | 502 lượt tốn |
|---|---|---|---|
| 25 dòng | 39,4 s | $0,0257 | **5,5 tiếng**, $12,90 |
| 5 dòng | 16,2 s | $0,0071 | **2,3 tiếng**, $3,57 |

Trần của phép đo này phải là **trần thời gian**, không phải trần tiền.

---

## 6. Điều chưa chứng minh — đừng đọc thành đã biết

Từ mục 8 của `dua-crm-qua-gateway-10-09.md`:

- **8.1** Nhánh xử lý 429 của CRM chưa được kiểm chứng.
- **8.2** Một lượt gọi 81 giây, không tái hiện được, chưa rõ nguyên nhân.
- **8.3** Chưa đối chiếu kết quả phân loại hai nhánh — chính là ô 7.6 ở trên.
- **8.4** `MIN_INTERVAL_S` trên production là bao nhiêu, chưa biết.
- **8.5** Lệch 4 dòng `dim_metric_alias`, có từ trước, cố ý để đó.

---

## 7. Trạng thái git

```
   47 file thay doi        19 file chua duoc theo doi
```

Đáng để ý:

- `web/index.html` và `web/js/app.js` có việc chưa commit, xem mục 2.5.
- `.env.example`, `docker-compose.yml`, `docker/gateway/config.gateway.yaml`,
  `docker/gateway/entrypoint.sh`, `db/load_gateway.py` đều có sửa chưa commit.
- Ba thư mục change đã archive nhưng bản gốc còn nằm ở `openspec/changes/` dưới dạng đã xoá,
  chưa commit.
- Tám file đo trong `var/` chưa được theo dõi: `audit-cuoi.txt`, `audit-sau.txt`,
  `do-duong-llm-20260910-112104.jsonl`, `log-truoc-khi-doi.txt`, `log-sau-khi-doi.txt`,
  `rebuild-cuoi.txt`, `rebuild-sau.txt`, `so-do-truoc-khi-doi.txt`. Quyết định commit hay xoá.

**Đã kiểm và KHÔNG phải việc còn lại:** bind IP của web. `docker-compose.yml:313` đang là
`192.168.20.111:${WEB_PORT:-8080}:80`, dòng `127.0.0.1` bị chú thích ở 312. Tức đã ở trạng thái
sẵn sàng push.

---

## 8. Cái trông như việc còn lại mà KHÔNG phải

Lệnh `grep` tìm checkbox mở trong `docs/` trả về **hơn 100 dòng**. Gần hết là **rác lịch sử**,
không phải backlog:

| chỗ | số ô mở | thực chất |
|---|---|---|
| `docs/archive/plan-xay-dung-database-2026-08-07.md` | 16 | plan dựng database, **đã xong** — repo có Postgres, migrations, `db/` đầy đủ |
| `docs/superpowers/plans/2026-08-18-docker-packaging.md` | 40 | đã xong — `docker-compose.yml` đang chạy 9 container |
| `docs/superpowers/plans/2026-08-24-complete-schema-migration-change.md` | 45 | đã xong — database đang ở v2 |
| `docs/archive/superpowers/plans/2026-08-13-date-range-filter-ddmmyyyy.md` | 10 | đã xong |

Cộng đúng khít: `docs/` có **114** ô mở, bằng `16 + 40 + 45 + 10 = 111` ô rác cộng **3** ô thật
của quyết định gateway. Không còn ô nào lọt ngoài bảng này.

Đây là plan kiểu superpowers, viết theo từng bước rồi không ai tích lại sau khi làm. **Ai rà
backlog bằng `grep "\[ \]"` trên cả `docs/` sẽ đọc ra hơn 100 việc tồn, trong khi số thật là 6
ô OpenSpec cộng 3 ô quyết định gateway.** Đáng cân nhắc: chuyển ba file plan còn ở
`docs/superpowers/plans/` sang `docs/archive/`, cho cùng chỗ với cái đã archive.

**Và code sạch:** `grep` `TODO`, `FIXME`, `ponytail:` trên `.py`, `.js`, `.yaml`, `.sh` trả về
**0 dòng**.

---

## 9. Thứ tự đề nghị, theo mục tiêu tuần

```
   THONG LUONG CRM
     1. Hoi anh Tuan: cho sua ban clone CRM khong?  -> mo duoc o 7.6
     2. Hen nhom CRM, ban giao 9 viec (2 viec nang: max_output_tokens + finish_reason)

   KIEM LITELLM TRA VE DAY DU
     DA XONG. Cot so Gateway archive 11/09; token suy nghi dong 11/09.

   HIEN LEN DASHBOARD
     3. O 4.4  mui gio trong fact_usage_daily   <- nang nhat, dang sai that
     4. O 4.1  doi ten thinking_tokens          <- re, chan duoc mot loi tuong lai
     5. O 4.3  luu reasoning_tokens             <- moi hien duoc token suy nghi
     6. O 6.2  bo chon agent bieu do ngan sach
     7. O 5.3  xem 8 card o be rong hep
```

Ô 4.1 nên làm sớm dù nhỏ: tên cột hiện tại **mời người ta cộng sai**, và anh Tuấn đã định cộng
nó vào output đúng một lần rồi.

---

## 10. Một test đang hỏng, và nó không thuộc change nào — thêm 11/09

Chạy bộ test thì ra:

```
   node --test tests/*.test.js     50 phep kiem, 49 dat, 1 HONG
   pytest tests/                   11 dat, 2 subtest dat, 0 hong
```

Phép kiểm hỏng là `tests/no-fake-baseline.test.js:29`, tên
*"không có kỳ gốc thật thì trả 0, không dựng bằng hệ số"*.

```
   Expected values to be strictly equal:   null !== 0
```

**Không phải lỗi mới. Test đang khoá hợp đồng CŨ.** Ô 1.3 của
`standardize-kpi-card-insights` cố ý đổi `deltaBaseline`: trước đây nó ép **cả hai** trạng thái
*"không có kỳ so sánh"* và *"kỳ trước đo được 0"* về cùng giá trị `0`, nên màn hình nói *"chưa
có dữ liệu"* cho một phép đo thật và là tin tốt. Nay `app.js:1163` trả
`{v: null, has: false}` khi không có kỳ nền, và `{v: 0, has: true}` khi kỳ nền thật sự bằng 0.

Ba trong bốn dòng khẳng định của test vì thế sai theo thiết kế mới:

| dòng | test đòi | code trả | đúng theo hợp đồng mới |
|---|---|---|---|
| `deltaBaseline(null).v` | `0` | `null` | `null`, và `has = false` |
| `deltaBaseline(0).v` | `0` | `0` | `0`, và `has = true` |
| `deltaBaseline(-5).v` | `0` | `null` | `null` |
| `deltaBaseline(undefined).v` | `0` | `null` | `null` |

**Việc cần làm:** sửa test cho khớp hợp đồng mới, và kiểm cả `has` chứ không chỉ `v` — vì `has`
mới là thứ tách được hai trạng thái mà ô 1.3 sinh ra để tách. Mục đích gốc của file test vẫn
còn nguyên giá trị và vẫn đang được hai phép kiểm còn lại canh: không ai nhét lại hệ số
`0,88 / 0,57` để dựng kỳ nền giả.

**Đáng lưu ý về quy trình:** ô 1.3 được đánh dấu xong mà bộ test không được chạy lại. Một thay
đổi hợp đồng có chủ ý đã để lại một phép kiểm đỏ trong repo, và không ô task nào ghi nhận.

### Đã sửa cùng ngày — 51/51 xanh

Hai phép kiểm thay cho một, vì hợp đồng mới có **hai** trạng thái chứ không phải một:

```
   khong co ky goc  (null, undefined, -5)  ->  { v: null, has: false }
   ky goc do duoc 0                        ->  { v: 0,    has: true  }
```

Kiểm cả `has` chứ không chỉ `v`, vì `has` mới là thứ ô 1.3 sinh ra để tách hai trạng thái.

**Một cái bẫy gặp khi sửa, ghi lại để lần sau không mất mười phút.** Bản đầu dùng
`assert.deepEqual(deltaBaseline(x), {...})` và **vẫn đỏ**, với thông báo lạ:

```
   Values have same structure but are not reference-equal
```

Nội dung khớp nhưng object do `vm.runInContext` dựng mang `Object.prototype` của **sandbox**,
không phải của realm chạy test, nên `deepStrictEqual` so prototype rồi trượt. Cách gỡ là trải
phẳng về realm này: `{ ...deltaBaseline(x) }`. Mọi file test trong `tests/` đều nạp `app.js`
bằng `vm`, nên cái bẫy này chờ sẵn ở mọi chỗ so cả object thay vì so từng trường.

Hai phép kiểm còn lại của file không đụng tới, và mục đích gốc vẫn nguyên: không ai nhét lại
hệ số `0,88 / 0,57` để dựng kỳ nền giả.
