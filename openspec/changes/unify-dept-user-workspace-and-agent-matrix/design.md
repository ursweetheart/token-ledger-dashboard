## Context

Dashboard là ứng dụng HTML/JS tĩnh, không backend, dữ liệu nằm trong `app.js` và `localStorage`.

Hai nguồn dữ liệu hiện **không có khoá nối**:

```
┌─ SEED_DAYS / state.days (số THẬT tháng 7 từ Excel) ─┐
│ row = {a, d, m, ug, u, ti, to, r, er, lat}          │
│   a  = agent (= project)                            │
│   d  = tên phòng ban dạng chuỗi tự do               │
│   u  = số user ĐƯỢC CẤP (snapshot, không phải active)│
│   ✗ KHÔNG có userId                                 │
└─────────────────────────────────────────────────────┘
                       ✗ không nối được
┌─ USER_ACCOUNTS (186 tài khoản demo) ────────────────┐
│ acct = {user, n, d, a, m, ug, req, ti, to, last,    │
│         active, role, created, disabled, quotaPct}  │
│   ✓ có định danh                                    │
│   ✗ chỉ phủ 4 phòng ban / 13 phòng có usage         │
│   ✗ không có cấp đơn vị con                          │
└─────────────────────────────────────────────────────┘
```

Vì vậy mọi yêu cầu dạng "click phòng ban → xem nhân viên với số liệu tương ứng" đều không thể thực hiện đúng trên dữ liệu hiện tại. Change này giải quyết bằng cách xây một **tầng metadata đơn vị** và một **tầng tài khoản demo phái sinh từ số thật của phòng**, đồng thời nói rõ với người xem rằng tầng user là dữ liệu phân bổ.

## Goals / Non-Goals

**Goals:**

- Người xem biết chính xác baseline của mỗi delta là `KT` hay `CK`.
- Một tab duy nhất đi từ phòng ban xuống tới tài khoản mà không đổi tab.
- Ma trận đọc theo chiều "project dùng ở những phòng nào" và drilldown được xuống đơn vị con rồi tới tài khoản.
- Bảng chi tiết phòng ban trả lời được "cấp bao nhiêu tài khoản, bao nhiêu người thực dùng".
- Chuẩn hoá tên phòng ban để mỗi đơn vị chỉ xuất hiện một lần.
- Tổng của cấp con luôn khớp tổng của cấp cha.

**Non-Goals:**

- Không xây backend, API, database, authentication.
- Không triển khai import Excel.
- Không thay đổi quy ước màu delta (tăng = xanh, giảm = đỏ) của `standardize-kpi-card-insights`.
- Không sửa tab Chi phí, tab Hiệu năng, tab Providers, tab Model.
- Không thay bộ lọc User toàn cục (`state.filters.user` vẫn dùng `ug`) — việc đó thuộc change cũ.

## Decisions

### 1. Định danh phòng ban chuẩn hoá là nền móng của cả change

Thêm bảng đơn vị làm nguồn sự thật duy nhất, thay cho việc dùng chuỗi `r.d` tự do:

Hai file trong `data/` là bằng chứng quyết định, đặc biệt sheet `06.08 DM viết tắt` của
`20240806 Chuẩn hóa định dạng dashboard_RD Revised.xlsx` — đây là **danh mục viết tắt chuẩn của công ty**:

```
Tên đơn vị (trích danh mục chuẩn)        Ý nghĩa
────────────────────────────────────────────────────────────────
BH1                                      Phòng Bán hàng 1
BH2                                      Phòng Bán hàng 2
TMDT                                     Phòng Thương mại điện tử
PXK                                      Phòng Xuất khẩu
TMDT MR / TMDT GT / TMDT TT              TMĐT mở rộng / gián tiếp / trực tiếp
```

Hai dòng khác trong cùng danh mục xác nhận cấp dưới phòng ban là **thật, không phải suy diễn**:

```
r152  "TX theo Kênh/ Vùng / Tỉnh"  — thuộc phòng bán hàng 1
r167  "DT theo tỉnh/ vùng"          — phòng BH1
```

Nghĩa là cây thật bên trong phòng bán hàng là `Phòng BH1 → Kênh / Vùng / Tỉnh`, khớp đúng ảnh yêu cầu
`Phòng BH1 → Vùng 1 → tài khoản`. **Phòng ban là cấp 1, `Vùng` là cấp con bên trong phòng ban** — không phải
`Phòng Bán hàng` làm cha của `Phòng Bán hàng 1`.

```js
var ORG_UNITS = [
  // level 1 — phòng ban (đúng cấp mà dữ liệu usage đang gắn vào)
  {id:"pbh1",  name:"Phòng Bán hàng 1",   parent:null, level:1},
  {id:"pbh2",  name:"Phòng Bán hàng 2",   parent:null, level:1},
  {id:"pbh3",  name:"Phòng Bán hàng 3",   parent:null, level:1},
  {id:"ecom",  name:"Thương mại điện tử", parent:null, level:1},
  {id:"nctt",  name:"P.NCTT , TTDL&ĐHS",  parent:null, level:1},
  ...
  // level 2 — Vùng: cấp THẬT theo danh mục chuẩn, nhưng danh sách vùng cụ thể
  //           không có trong bất kỳ file nào ⇒ tên vùng là metadata demo.
  {id:"pbh1-v1", name:"Vùng 1", parent:"pbh1", level:2},
  {id:"pbh1-v2", name:"Vùng 2", parent:"pbh1", level:2},
  ...
];
```

Chỉ sinh `Vùng` cho phòng ban đủ lớn để chia vùng có nghĩa (ngưỡng theo số tài khoản được cấp);
phòng nhỏ giữ một cấp và mở trực tiếp ra tài khoản. Cấp `Tỉnh` (cấp 4 theo danh mục chuẩn) không
triển khai trong change này.

Bảng alias chỉ gom những cặp có **bằng chứng**. Cấu trúc file tháng 6 cho thấy mỗi agent là một khối
riêng và mỗi khối dùng một quy ước đặt tên khác nhau (khối `Trợ Lý Ảo Hợp Đồng` dùng tên đầy đủ,
khối `Trợ lý ảo Ralli` dùng viết tắt):

```js
var UNIT_ALIASES = {
  // danh mục chuẩn: BH1 = Phòng Bán hàng 1, BH2 = Phòng Bán hàng 2
  "PBH1":"pbh1", "Phòng Bán hàng 1":"pbh1",
  "PBH2":"pbh2", "Phòng Bán hàng 2":"pbh2",
  "PBH3":"pbh3", "Phòng Bán hàng 3":"pbh3",
  // danh mục chuẩn: TMDT = Phòng Thương mại điện tử
  "TMĐT":"ecom", "Thương mại điện tử":"ecom",
  "TT C4LED":"c4led", "C4LED":"c4led",
  "Cty CPBĐ PN Rạng Đông":"cpbd", "Công ty CPBĐ PN Rạng Đông":"cpbd",
  "P.NCTT , TTDL&ĐHS":"nctt", "P.NCTT, TTDL&ĐHS":"nctt"   // chỉ khác dấu cách
};
```

Hai tên **giữ đứng riêng** vì chưa có bằng chứng đủ mạnh:

- `TT&TMĐT` — danh mục chuẩn cho thấy TMĐT có cấp con thật (`TMDT TT/GT/MR`) và `TT` là hậu tố kênh
  (`ĐH TT` = đơn hàng trực tiếp), nên `TT&TMĐT` **có thể** là đơn vị con của TMĐT. Chưa xác nhận ⇒ đứng riêng.
  Nếu xác nhận, chỉ cần đổi thành `{id:"ecom-tt", parent:"ecom", level:2}`.
- `TTDL&DHS` so với `P.NCTT , TTDL&ĐHS` — đứng riêng theo quyết định của người dùng.

Chuỗi không có alias không bị loại: `unitOf` tự sinh một unit level-1 để không mất dữ liệu.

`DEPT_PROVISIONED` chuyển sang khoá theo `unitId`, xoá hẳn nguy cơ lệch chuỗi.

### 2. Tầng tài khoản demo phái sinh từ số thật của phòng, tính theo kỳ

Tách làm hai phần, vì nếu nướng số liệu vào danh sách tài khoản thì `Σ user = Σ phòng` chỉ đúng
cho một kỳ duy nhất và sẽ vỡ ngay khi người dùng đổi khoảng thời gian hoặc bộ lọc.

**(a) Danh mục tài khoản — tĩnh.** `buildAccountCatalogue()` sinh danh tính, không sinh số liệu:

```
Với mỗi đơn vị LÁ có số cấp khai báo:
  sinh `provisionedOf(leaf)` tài khoản
  mỗi tài khoản: {user, n, unitId, a, m, ug, role, created, disabled, weight}
  weight > 0 cho phần tài khoản "có khả năng hoạt động" (tỷ lệ cố định theo unitId)
  weight = 0 cho phần còn lại  => luôn là tài khoản chưa dùng
  agent/model gán vòng tròn theo đúng các agent phục vụ đơn vị đó trong dữ liệu usage
```

**(b) Phân bổ theo kỳ — động.** `applyAccountAllocation(rows)` chạy đầu mỗi lượt render:

```
totals[unit] = tổng {r, ti, to} của các usage row có unitOf(row.d) === unit
với mỗi unit có usage:
  accounts = mọi tài khoản thuộc cây con của unit, weight > 0
  mỗi tài khoản nhận floor(total * weight / tổng weight)
  phần dư dồn vào tài khoản đầu tiên  => tổng khớp CHÍNH XÁC ở mọi cấp
unit không có usage trong kỳ => mọi tài khoản của nó về 0 => adoption 0%
```

`active` không còn là cờ tĩnh: tài khoản hoạt động khi và chỉ khi request được phân bổ trong kỳ
lớn hơn 0. Nhờ vậy `Users active` là số đếm theo kỳ đúng như yêu cầu, thay cho snapshot `u` của nguồn.

Weight lấy từ hàm băm tiền định trên `user` nên mọi lần render cho cùng kết quả; không dùng
`Math.random`, không phụ thuộc thời điểm chạy.

Hệ quả có chủ đích: mọi phòng có usage đều drilldown được, và **tổng cấp con luôn khớp cấp cha ở
mọi cấp và ở mọi kỳ**. Đánh đổi: số của từng tài khoản là số phân bổ, không phải số đo.

Ràng buộc bắt buộc để bù đánh đổi này: mọi khối UI hiển thị số theo tài khoản phải có nhãn
`Dữ liệu phân bổ (demo)` kèm tooltip giải thích. Không được để người xem hiểu đây là số đo
theo tài khoản thật.

Đơn vị không có số cấp khai báo trong nguồn (ví dụ `Chăm sóc khách hàng`, có request thật nhưng
`u = 0`) được suy ra một số cấp demo theo khối lượng request và phải hiển thị kèm chỉ dấu rằng
mẫu số là số suy ra.

### 3. Delta gọi tên baseline bằng KT / CK

```js
var DELTA_BASIS = {
  KT: {abbr:"KT", full:"kỳ trước"},
  CK: {abbr:"CK", full:"cùng kỳ năm trước"}
};
```

`deltaLine(basis, cur, b, fmtFn)` nhận `basis` thay cho chuỗi nhãn tự do. Kết quả render:

```
┌──────────────────────────────┐   ┌──────────────────────────────┐
│ ▲ 50%  so với KT · 4         │   │ ▲ 50%  so với KT · 4         │
│                              │   │ → 0%   so với CK · 6         │
│ tooltip: so với kỳ trước     │   │  (card dùng cả hai baseline) │
│          (tháng 6/2026): 4   │   └──────────────────────────────┘
└──────────────────────────────┘
```

- `renderSingleDelta` → luôn `basis = KT`.
- `renderDelta` → dòng 1 `KT`, dòng 2 `CK`.
- Không có dữ liệu nền → `so với KT: chưa có dữ liệu`, không dựng baseline giả.
- Vì `KT`/`CK` là viết tắt không tự giải thích, thêm một dòng chú giải cạnh dải tab: `KT = kỳ trước · CK = cùng kỳ năm trước`. Đây là điều kiện để việc viết tắt không làm mất thông tin.
- Kỳ cụ thể (`tháng 6/2026`) chuyển vào `title` để giữ scorecard gọn nhưng vẫn truy vết được.

### 4. Tab hợp nhất `Phòng ban & User` với drilldown 3 cấp

Điều hướng: nút tab `👥 User` bị xoá, tab `🏢 Phòng ban` đổi nhãn thành `🏢 Phòng ban & User`. Toàn bộ nội dung `div#users` chuyển vào `div#departments`; `div#users` bị xoá cùng nhánh `case "users"` trong bộ điều phối chart.

Bảng chi tiết trở thành accordion, mỗi cấp thụt lề và giữ đúng bộ cột:

```
▼ Phòng Bán hàng            6  34   21   62%   1,2tr   1.240   0.4
  ▼ Vùng 1                  3  12    9   75%     680k    720   0.3
      ● user.003@corp.vn    1   –    –     –     210k    198   0.2
      ● user.009@corp.vn    1   –    –     –     180k    164   0.5
      ● user.017@corp.vn    1   –    –     –     290k    358   0.3
  ▶ Vùng 2                  2   8    5   63%     340k    360   0.6
  ▶ Vùng 3                  1   5    2   40%     180k    160   0.2
▶ P.NCTT, TTDL&ĐHS          3  30   24   80%   2,3tr     417   0.0
```

- Cấp 1/2 hiển thị đầy đủ cột. Cấp 3 (tài khoản) để `–` ở cột Agents/Tổng Users/Tỷ lệ vì không có nghĩa ở cấp tài khoản.
- Đơn vị chỉ có 1 cấp → không có mũi tên ở cấp 2, mở trực tiếp ra danh sách tài khoản.
- Trạng thái mở/đóng lưu trong `state.deptExpanded = {unitId: true}` để giữ nguyên qua các lần `renderAll()` do đổi bộ lọc.
- Mọi số ở cấp tài khoản chịu nhãn `Dữ liệu phân bổ (demo)` của quyết định 2.
- KPI user, biểu đồ DAU và danh sách tài khoản không hoạt động đặt **dưới** bảng drilldown, ăn theo phòng ban đang chọn ở bộ lọc toàn cục.

Chọn accordion thay vì master-detail hai cột vì nó giữ được so sánh ngang giữa các phòng trong khi vẫn đi sâu được — mất so sánh là điểm yếu chính của master-detail.

### 5. Ma trận Project × Phòng ban với drilldown trên trục ngang

Lật trục so với hiện trạng: **hàng = project (agent), cột = phòng ban**.

```
Ma trận Project × Phòng ban
Tất cả phòng ban  ›  Phòng Bán hàng  ›  Vùng 1        ← breadcrumb, click để lên cấp

CẤP 1 — cột là phòng ban gốc (click header để xuống cấp)
                    │ Anh Em │ TMĐT  │ Phòng Bán hàng │ P.NCTT
────────────────────┼────────┼───────┼────────────────┼────────
Chatbot Contact Ctr │   ·    │ 4,8ng │       ·        │   ·
Phân Loại DL CRM    │   ·    │   ·   │       ·        │ 2,6ng
Sale Agent          │ 2,9ng  │   ·   │       ·        │   ·
Trợ Lý Ảo Hợp Đồng  │   ·    │   ·   │     1,2ng ⌄    │   ·

CẤP 2 — sau khi click "Phòng Bán hàng": cột là các Vùng
                    │ Vùng 1 │ Vùng 2 │ Vùng 3
────────────────────┼────────┼────────┼────────
Trợ lý ảo Ralli     │  720   │  360   │  160  ⌄

CẤP 3 — sau khi click "Vùng 1": cột là tài khoản
                    │ minh.ho │ trang.le │ hai.tran
────────────────────┼─────────┼──────────┼──────────
Trợ lý ảo Ralli     │   198   │   164    │   358
```

- Drilldown đi theo **trục ngang** vì đó là trục phòng ban, khớp đúng yêu cầu `Phòng BH1 → Vùng 1 → tài khoản`.
- Chọn breadcrumb + thay cột thay vì lồng cột (nested column expansion) vì lồng cột làm bảng phình ngang vô hạn trên màn hình đã phải cuộn ngang.
- Header cột có cấp con hiển thị chỉ dấu `⌄` và con trỏ pointer; không có cấp con thì không click được.
- `state.matrixPath = []` → `["pbh"]` → `["pbh","pbh-v1"]`. Reset về `[]` khi đổi bộ lọc phòng ban toàn cục.
- Cột phòng ban/tài khoản chỉ hiện khi có ít nhất một ô > 0, trừ khi đang lọc user cụ thể.
- Cấp 3 hiển thị `user` kèm nhãn dữ liệu phân bổ.
- Bộ lọc `matrix-user-filter` hiện có được giữ nguyên; khi chọn một user, breadcrumb tự nhảy tới đơn vị của user đó.
- Trục hàng (project) sticky bên trái ở mọi cấp.

### 6. Biểu đồ mức độ sử dụng agent chuyển sang tròn

`chartsAgents` đổi `mkBar("c-ag-usage", ..., {horizontal:true})` thành `mkDonut("c-ag-usage", labels, values, "lg-ag-usage", fmt)`.

Chọn `mkDonut` thay vì pie đặc để nhất quán với `Phân bổ chi phí theo AI Agent` và `Chi phí theo phòng ban` đang dùng trong dashboard. Thêm `div#lg-ag-usage` cho legend, đổi badge `wf-type` từ `Bar` sang `Tròn`.

Gộp phần đuôi thành `Agent khác` khi số agent > 6 để lát bánh không vụn — cùng quy tắc đang dùng ở `chartsDepartments`.

### 7. Hai cột mới của bảng chi tiết phòng ban

```
Phòng ban │ Agents │ Tổng Users │ Users active │ Tỷ lệ active/tổng │ Tokens │ Requests │ Error %
                     ↑ MỚI                       ↑ MỚI
```

- `Tổng Users` = `provisionedOf(unitId)`, cộng dồn từ các đơn vị con.
- `Tỷ lệ active/tổng` = `activeUsers / provisioned`, hiển thị `9/12 · 75%`.
- Tô màu theo `thresholds` đã có trong `app.js`: `< adoptionCritical (30)` → đỏ, `< adoptionWarning (60)` → cam, còn lại → xanh. Dùng ngưỡng có sẵn thay vì đặt ngưỡng mới.
- `provisioned = 0` → hiển thị `—`, không chia cho 0, không suy ra 100%.
- Cột `Users active` giữ nguyên vị trí ngữ nghĩa nhưng nay là số đếm tài khoản có request, không còn là `g.u` (snapshot số cấp) như hiện tại. Đây là sửa lỗi ngữ nghĩa kèm theo.

## Risks / Trade-offs

| Rủi ro | Ảnh hưởng | Giảm thiểu |
|---|---|---|
| Số theo tài khoản là số phân bổ, không phải số đo | Người xem có thể tưởng là số thật | Nhãn `Dữ liệu phân bổ (demo)` bắt buộc trên mọi khối cấp tài khoản; ghi trong tooltip và trong banner tab |
| Cây đơn vị demo không khớp cây tổ chức thật | Phải sửa lại khi có cây thật | Tách cây vào `ORG_UNITS`/`UNIT_ALIASES` một chỗ duy nhất; mọi renderer đi qua `unitOf()` |
| Alias gom sai hai phòng khác nhau về một unit | Số bị cộng dồn sai | Liệt kê alias tường minh, không gom bằng heuristic chuỗi; chuỗi lạ tự sinh unit riêng thay vì đoán |
| Xung đột với change `revise-dashboard-ui-after-2026-07-25-review` trên cùng file | Làm hai lần hoặc ghi đè lẫn nhau | Proposal liệt kê rõ các task bị thay thế; task 5.1 phải đảo chiều |
| Ma trận 3 cấp trên mobile | Không đọc được | Breadcrumb thu gọn, sticky cột project, cuộn ngang trong container riêng |

## Migration Plan

1. Tầng dữ liệu trước: `ORG_UNITS`, `UNIT_ALIASES`, `unitOf()`, `DEPT_PROVISIONED` theo `unitId`, `buildDemoUserAccounts()` mới.
2. Chuyển từng renderer sang `unitOf()`, kiểm tra tổng không đổi sau khi gom alias.
3. Delta `KT`/`CK` (độc lập, làm được song song).
4. Gộp tab và bảng drilldown.
5. Ma trận lật trục và drilldown.
6. Biểu đồ tròn agent, hai cột mới, dọn CSS/DOM/chart instance của `div#users`.

`state.deptExpanded` và `state.matrixPath` là state mới; adapter đọc `localStorage` cũ phải bỏ qua khoá lạ mà không lỗi.

## Open Questions

- Danh sách `Vùng` cụ thể của từng phòng bán hàng (tên vùng, tài khoản nào thuộc vùng nào). Cấp `Vùng` đã xác nhận là thật qua danh mục viết tắt chuẩn, nhưng không file nào chứa danh sách vùng ⇒ tên vùng hiện là metadata demo.
- `TT&TMĐT` có phải đơn vị con của `Thương mại điện tử` (dạng `TMDT TT` trong danh mục chuẩn)? Hiện để đứng riêng.
- Cấp `Tỉnh` (`Phòng BH1 → Kênh → Vùng → Tỉnh` theo danh mục chuẩn) có cần đưa vào drilldown không? Change này dừng ở 3 cấp.
- `Chăm sóc khách hàng` (771 request thật) không có số tài khoản được cấp trong nguồn ⇒ mẫu số đang suy ra từ lượng request và được dán nhãn là số demo. Số cấp thật là bao nhiêu?
