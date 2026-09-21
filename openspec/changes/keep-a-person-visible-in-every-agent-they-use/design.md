## Context

### Hai chiều đã cùng tồn tại, và đó là thiết kế đúng

```
   dim_user      PRIMARY KEY (agent_id, user_id)
   ┌──────────────────────────────────────────────┐
   │ (8, u_991)  longnt  → account 500 · PBH1     │   "có mặt ở đâu"
   │ (5, 4412)   longnt  → account 500 · Phòng BH1│
   └───────────────────┬──────────────────────────┘
                       │ account_id
                       ▼
   account       username UNIQUE
   ┌──────────────────────────────────────────────┐
   │ 500  longnt  · PBH1 · unit_agent_id = 8      │   "là ai"
   │              · unit_conflict = 1             │
   └──────────────────────────────────────────────┘
```

Hai bảng trả lời hai câu khác nhau. Không bảng nào thừa.

`fact_usage_daily` và `usage_by_account_resolved` mang **cả** `agent_id` lẫn `account_id` trên mỗi
dòng, nên **lưu lượng chưa bao giờ bị trộn giữa các agent**. Câu hỏi *"ai dùng nhiều nhất trong
agent X"* hôm nay đã trả lời đúng. Việc gộp `account` chỉ gộp **danh tính**, không gộp số.

Điều này quan trọng với phạm vi change: ta không đi sửa số liệu. Ta đi sửa ba chỗ **tra nhầm bảng**.

### Ai đã hỏi đúng, ai đang hỏi sai

| Nơi | Hỏi gì | Đúng? |
|---|---|---|
| `store.py:279` `adoption()` | `dim_user` WHERE `agent_id` = agent | ✅ |
| `load_ralli.py:86` | `dim_user` WHERE `agent_id` = Ralli | ✅ |
| `load_tla_contract.py:96` | `dim_user` WHERE `agent_id` = TLA HĐ | ✅ |
| `load_gateway.py:379` | `account.unit_agent_id` **==** agent | ❌ |
| `store.py:202` `accounts()` | `JOIN dim_agent ON a.unit_agent_id` | ❌ |
| phòng ban hiển thị | `account.unit_id` | ⚠️ có nhãn |

Bốn trên sáu đã đúng. Change này không đặt ra khuôn mới — nó kéo hai chỗ còn lại về khuôn đã có.

## Goals / Non-Goals

**Goals**

- Người có trong danh bạ của agent X thì lưu lượng của họ qua agent X SHALL quy về chính họ.
- Danh bạ lọc theo agent SHALL trả đủ người có mặt ở agent đó.
- Định danh **không** có trong danh bạ agent nào SHALL vẫn bị từ chối, và vẫn được đếm.

**Non-Goals**

- Không bỏ gộp `account`, không bỏ `username UNIQUE`.
- Không đổi phòng ban đang hiển thị.
- Không đổi cách tính tiền, token, hay bất kỳ tổng nào.

## Decisions

### D1 — Tra khoá đôi, KHÔNG phải nới lỏng phép so

Có hai cách làm cho 4 người kia lọt qua. Chỉ một cách đúng.

| | Cách | Kết quả với `longnt` → agent 5 | Kết quả với `admin` → agent 6 |
|---|---|---|---|
| ✅ | tra `(agent_id, username)` trong `dim_user` | có dòng → **nhận** | không có dòng → **từ chối** |
| ❌ | bỏ hẳn phép so `found[1] == agent_id` | nhận | **nhận** ← lỗi cũ quay lại |

Cách thứ hai là chính đường hỏng đã đo ngày 31/08: bảng `account` **có** dòng `admin` (account 1,
"Quản trị viên", thuộc agent 5) và dòng ấy đã mang 480 lượt / 1.588.404 token. Agent khác gửi
`X-User: admin` — tên đăng nhập cục bộ của chính nó — thì lưu lượng trộn vào lịch sử của một người
dùng TLA Hợp Đồng, im lặng, tổng vẫn khớp.

Phép tra khoá đôi **chặt đúng chỗ và lỏng đúng chỗ**: nó chặn `admin` vì `admin` không có trong
danh bạ agent 6, và nó nhận `longnt` vì `longnt` **có** trong danh bạ agent 5. Không cần thêm ngoại
lệ nào.

#### D1b — "Có mặt" nằm ở HAI sổ đăng ký, không phải một

Sửa 21/09, phát hiện lúc bắt tay viết việc 1.1. Bản đầu của D1 chỉ nói *tra `dim_user`*, và làm
đúng như vậy thì **hỏng cả 6 agent một-người-dùng** — đúng thứ việc 2.5 sinh ra để chặn.

Lý do: hai bảng đặt **hai cái tên khác nhau** cho cùng một tài khoản dịch vụ.

```
  load_org.py:405   dim_user:  (agent 6, "__technical_6__")  →  account 949
  load_org.py:609   account:   949, "svc.dms-feedback",
                               kind='service_account', unit_agent_id=6
```

Gateway gửi `X-User: svc.dms-feedback`. Tra `dim_user` theo `(6, "svc.dms-feedback")` ra **rỗng**,
vì trong `dim_user` nó mang tên `__technical_6__`.

Nên phép tra SHALL hợp hai nguồn, cả hai đều khoá theo agent:

| Nguồn | Điều kiện | Khoá |
|---|---|---|
| `dim_user` | `NOT is_technical` | `(agent_id, username)` |
| `account` | `kind = 'service_account'` | `(unit_agent_id, username)` |

`kind = 'whole_agent'` **loại** — Gateway không bao giờ gửi `__whole_agent_5__`, và đó vốn là tài
khoản neo để rơi về. Gộp nó vào là làm đường rơi trở thành đường nhận.

Nguyên tắc không đổi: vẫn là *"người này có mặt ở đâu"*. Chỉ là **"có mặt" được ghi ở hai sổ**, và
sổ thứ hai dùng một quy ước đặt tên khác.

#### D1c — Chuẩn hoá phải làm ở CẢ HAI đầu, không chỉ đầu tra

Thêm 21/09 sau khi soát lại hàm vừa viết. Hàm tra chuẩn hoá khoá bằng
`LOWER(TRIM())`. Nhưng **người gọi thì không**:

```
  load_gateway.py:346   user_id = end_user or None     ← NGUYÊN VĂN
  load_gateway.py:379   accounts.get(user_id)           ← tra bằng chuỗi thô
```

Đây **không phải lỗi mới**: `account.username` vốn đã lưu dạng `LOWER(TRIM())`
(`001_baseline.sql:210`), nên khoảng hở này có từ trước. Nó đang **ngủ**, vì hôm nay chỉ agent
một-người-dùng đi qua Gateway và `svc.<code>` vốn toàn chữ thường.

Nó tỉnh dậy đúng lúc kịch bản của change này xảy ra. Đo trên danh bạ đợt kéo 20/09:

| | |
|---|---|
| Tổng tên đăng nhập | 935 |
| Có **chữ hoa** | **59 = 6,3%** |
| Có khoảng trắng thừa | 0 |

Và trong 5 người mà change này sinh ra để cứu:

| Người | Danh bạ ghi |
|---|---|
| **`Longnt`** | chữ hoa |
| **`PBH3_TTHien`** | chữ hoa |
| `quy.tv@rangdong.com.vn` · `tg.namnh` · `tt3.binhtv` | thường |

**2/5 người vẫn sẽ mất sau khi sửa xong bug chính** — vì một lý do hoàn toàn khác. Triệu chứng
lúc nghiệm thu: `identity_unresolvable` giảm nhưng **không về 0**, và người sửa đi tìm một lỗi
định tuyến không tồn tại.

Nên việc 2.1 SHALL hạ chữ thường và cắt khoảng trắng `end_user` trước khi tra.

**Chưa chứng minh được:** hai app thật sự gửi `X-User` dạng nào — chúng chưa đi qua Gateway lần
nào. Giả định ở đây là chúng gửi đúng chuỗi trong danh bạ của mình. Nhưng chuẩn hoá ở đầu nạp thì
**không mất gì** dù app làm kiểu gì, nên không phải chờ biết mới làm.

### D2 — Khoá tra là `username`, nhưng khoá chính của `dim_user` là `user_id`

**Đây là chỗ dễ vấp nhất của change này.**

```
   dim_user   PRIMARY KEY (agent_id, user_id)      ← user_id, KHÔNG phải username
```

Lược đồ ghi rõ ở `db/migrations/sql/001_baseline.sql:239`: *"13 dòng do Ralli ghi hai dạng khoá"*.
Nghĩa là trong Ralli, một `username` có thể ra **hai dòng** `dim_user`.

Chú thích ở `db/load_ralli.py:83-84` nói rõ thêm: nhật ký Ralli ghi `user_id` theo hai dạng khoá
khác nhau cho cùng một người, và **cả hai dạng đều trỏ về một `account_id`**. Khâu nạp Ralli đã
dựa vào tính chất ấy. Nên kết quả tra vẫn đúng, **với điều kiện phép tra gộp trùng**.

Dựng bảng tra bằng một `dict` gán thẳng thì dòng sau ghi đè dòng trước — vô hại ở đây vì hai dòng
cùng `account_id`, nhưng **chỉ vô hại nhờ một tính chất không ai cưỡng chế**. Phải kiểm tường minh:
nếu một cặp `(agent_id, username)` cho ra **hai `account_id` khác nhau**, đó là dữ liệu hỏng và
phép dựng SHALL dừng, không được im lặng chọn một.

Bỏ qua chi tiết này thì code chạy đúng trên 7 agent và sai trên Ralli — đúng kiểu bẫy của repo này.

### D3 — `identity_unresolvable` giữ nguyên tên và ý nghĩa

Cám dỗ: sau khi sửa, con số này về gần 0, nên dễ nghĩ là bỏ được.

Không bỏ. Nó chuyển từ *"đếm người dùng hai agent"* sang *"đếm định danh lạ"* — và nghĩa thứ hai
mới là nghĩa nó sinh ra để mang. Một agent gửi `X-User` sai quy ước, hoặc gửi tài khoản đã bị xoá
khỏi danh bạ, vẫn phải làm con số này nhảy.

Phép kiểm nghiệm thu vì thế có **hai chiều**, không một:

```
   chiều dương   người CÓ trong danh bạ agent    → identity_unresolvable KHÔNG tăng
   chiều âm      định danh KHÔNG có trong danh bạ → identity_unresolvable CÓ tăng
```

Chỉ đo chiều dương là chứng minh được "không còn từ chối ai" bằng cách **thôi từ chối tất cả**.

### D4 — Danh bạ trả danh sách, không trả agent thắng

`accounts()` nay trả một cột `agent` (tên của `unit_agent_id`). Đổi thành danh sách các agent nơi
người đó có mặt, đọc từ `dim_user`.

Giữ lại `unit_agent_id` và `unit_conflict`: chúng là thứ **giải thích** phòng ban đang hiển thị.
Bỏ đi thì màn hình hiện một phòng ban mà không ai nói được nó đến từ đâu — đúng cái im lặng mà cột
`unit_conflict` sinh ra để chấm dứt.

### D5 — Không bỏ gộp `account`: đã cân nhắc và loại

Phương án thay thế: tách `account` thành một dòng cho mỗi cặp `(agent, người)`.

| | Gộp (giữ) | Tách (loại) |
|---|---|---|
| Ai dùng nhiều nhất theo agent | ✅ đã đúng | ✅ vẫn đúng |
| Tỷ lệ áp dụng theo agent | ✅ đã đúng | ✅ vẫn đúng |
| Gateway nhận định danh | ❌ → **D1 sửa** | ✅ |
| Danh bạ theo agent | ❌ → **D4 sửa** | ✅ |
| "Bao nhiêu con người đang dùng AI" | ✅ | ❌ **đếm đôi 5 người** |
| Cờ hai app xếp khác phòng ban | ✅ | ❌ **mất tín hiệu** |
| Khối lượng sửa | 3 chỗ | lược đồ + mọi chỗ đọc `account` |

Hai cột phải ❌ của phương án tách là hai thứ **không lấy lại được bằng cách khác**, trong khi hai
cột ❌ của phương án giữ đều sửa được bằng ba chỗ tra. Ô KPI tổng người dùng đọc thẳng
`accounts.length` (`web/js/app.js:3568`), nên tách là con số ấy tự tăng 5 mà không ai bấm gì.

Loại phương án tách.

## Risks

| Rủi ro | Vì sao nguy | Chặn bằng |
|---|---|---|
| Sửa xong hoá ra **nhận tất cả** | lỗi `admin` 31/08 quay lại, im lặng, tổng vẫn khớp | phép kiểm chiều âm (D3) |
| Hai dòng `dim_user` cùng `username` khác `account_id` | ghi đè im lặng, sai đúng trên Ralli | dựng bảng tra phải **dừng** khi gặp (D2) |
| 6 agent một-người-dùng đổi kết quả | `svc.<code>` đang chạy đúng, không được động | đối chứng trước/sau, phải **y hệt** |
| Nghiệm thu bằng tổng token | tổng luôn đúng kể cả khi hỏng — đã đo | nghiệm thu bằng **số tài khoản phân giải được**, không bằng tổng |

## Open Questions

1. **Ai nên thắng ở phòng ban khi hai app không đồng ý?** Change này không trả lời — nó giữ nguyên
   luật hiện tại và giữ nguyên cờ. Cần người hiểu cơ cấu tổ chức quyết định, không phải người đọc
   code.
2. **`quy.tv@rangdong.com.vn` dùng email làm tên đăng nhập** trong khi 4 người kia dùng mã nhân
   viên. Có phải quy ước đặt tên giữa hai app đang trôi khỏi nhau không, và còn bao nhiêu trường hợp
   như vậy chưa lộ ra vì tên **không** trùng?
3. Khi agent thứ 9 là agent nhiều người dùng, nó lấy danh bạ từ đâu? Nằm ngoài change này, nhưng
   cùng một gốc — xem `docs/reference/onboard-a-new-agent.md` mục 8.

## Mức chắc chắn của các số trong tài liệu này

| Khẳng định | Trạng thái |
|---|---|
| 5 người có mặt ở cả hai danh bạ, kèm tên | **đo được** từ tệp nguồn đợt kéo 20/09 |
| Ralli giữ 4/5, TLA HĐ giữ 1/5 | **đo được**, nhưng bằng cách **dựng lại** `unit_priority()` — hàm lồng, không gọi từ ngoài được. Phải đối chứng với `account.unit_agent_id` thật |
| Gateway từ chối, dồn về neo, tiền + token vẫn đủ | **đo được** — gọi `build_rows()` thật với dữ liệu giả |
| `dim_user` tách theo agent; 4 chỗ đã dùng đúng khuôn | **đọc mã nguồn**, chưa chạy |
| Danh bạ thiếu đúng 4 người trên màn hình | **suy luận** — database đang rỗng lúc viết |
