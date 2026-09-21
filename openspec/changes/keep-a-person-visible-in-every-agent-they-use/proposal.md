## Why

Một người có thể dùng hai agent. Database **biết** điều đó, nhưng ba chỗ trong mã nguồn lại hỏi
một câu khác — và cả ba nhận về câu trả lời sai theo cùng một kiểu.

Bảng `account` gộp mỗi con người thành **một dòng** (`username` là `UNIQUE`), và dòng ấy mang
**một** `unit_agent_id` — agent thắng phép chọn ở `load_org.py:492`. Ba chỗ dùng cột ấy để trả lời
câu *"người này dùng agent nào"*, trong khi nó sinh ra để trả lời câu *"lấy phòng ban theo cây của
app nào"*. Một cột, hai nghĩa, và nghĩa thứ hai là nghĩa mượn.

**Đo được, không phải lo xa.** Quét danh bạ đợt kéo 20/09/2026:

| | |
|---|---|
| Danh bạ Ralli (agent 8) | 892 tên |
| Danh bạ TLA Hợp Đồng (agent 5) | 44 tên |
| **Có mặt ở cả hai** | **5 người** |

`longnt` · `pbh3_tthien` · `quy.tv@rangdong.com.vn` · `tg.namnh` · `tt3.binhtv`

Con số 5 trùng khít với chú thích có sẵn ở `db/migrations/sql/001_baseline.sql:239-240` — *"5 dòng
do cùng một tên đăng nhập tồn tại ở cả hai app"* — viết bởi người khác, lúc khác, bằng đường khác.
Hai nguồn độc lập cùng ra 5.

Phép chọn cho kết quả: **Ralli giữ 4/5, TLA Hợp Đồng giữ 1/5.** Không phải vì `agent_id` nhỏ hơn —
tiêu chí ấy nằm ở tầng ba và không quyết định ca nào. Quyết định là **độ sâu cây đơn vị**: Ralli
khai `PBH1` sâu 3 trong khi TLA HĐ khai `Phòng BH1` sâu 2. Bên nào mô tả cơ cấu chi tiết hơn thì
bên ấy thắng — nên bên thua là agent **cũ hơn, nhỏ hơn**, không phải agent mới.

## Ba hậu quả, một nguyên nhân

**1. Gateway từ chối chính người của mình — mất dữ liệu, im lặng.**

`db/load_gateway.py:379` chỉ nhận định danh khi `account.unit_agent_id` bằng agent gửi request.
Ngày TLA Hợp Đồng đi qua Gateway, 4/5 người ấy bị từ chối.

Đã **đo trên hàm thật** (`build_rows()`, dữ liệu giả, không chạm database):

```
  X-User = pbh1_ntlong,  tag = agent 9
      → identity_unresolvable = 1
      → account_id dồn về tài khoản neo mức agent
      → dòng VẪN vào sổ, token VẪN đủ (60/60), tiền VẪN đủ (0,002/0,002 USD)
```

Trong lô hai dòng, **50% token rơi khỏi chiều người dùng** mà mọi phép nghiệm thu bằng tổng vẫn
ĐẠT. Chỉ bộ đếm `identity_unresolvable` nói ra — và `scripts/refresh_gateway.py` nuốt đầu ra của
bộ nạp khi lượt chạy thành công.

**Chưa nổ.** Hôm nay chưa agent nhiều người dùng nào đi qua Gateway. Sửa trước thì không ai thấy gì.

**2. Danh bạ thiếu người — hiện sai, im lặng.**

`backend/store.py:202` nối `JOIN dim_agent g ON g.agent_id = a.unit_agent_id`, nên mỗi người chỉ
hiện **một** agent. Hỏi *"danh bạ TLA Hợp Đồng gồm những ai"* thì màn hình trả lời thiếu **4/44 =
9,1%**. Đang xảy ra hôm nay, trên màn hình đang chạy.

**3. Phòng ban mang tên của bên thắng — kém chính xác, nhưng CÓ báo.**

Lưu lượng TLA Hợp Đồng của 4 người ấy được xếp vào `PBH1`, tên theo cây Ralli. Dữ liệu đúng đã nằm
sẵn trong `dim_user.unit_id` (mỗi agent một dòng, mỗi dòng đơn vị của chính app đó) — chỉ là không
ai đọc.

Khác hai lỗi trên ở chỗ **hệ thống có ghi nhãn**: `account.unit_conflict = 1`, và lược đồ nói thẳng
lý do — *"1 = các nguồn đã KHÔNG đồng ý, ta vừa chọn hộ. Không có cột này thì việc chọn diễn ra âm
thầm."* Đây là đánh đổi **có ý thức**, không phải sơ suất.

## Cách sửa đã có sẵn trong repo, không phải nghĩ mới

Bảng đúng đã tồn tại. `dim_user` có `PRIMARY KEY (agent_id, user_id)` — khoá **đã gồm agent** — và
giữ `username`, `account_id`, `unit_id` riêng cho từng agent:

```
  (agent 8, longnt) → account 500, đơn vị PBH1
  (agent 5, longnt) → account 500, đơn vị Phòng BH1
```

Và khuôn mẫu ấy **đã được dùng ở nơi khác trong chính repo này**: `backend/store.py:279`
(`adoption()`) tra `dim_user` lọc theo `agent_id`, nên tỷ lệ áp dụng theo agent hôm nay đã đúng.
Hai khâu nạp app (`load_ralli.py:86`, `load_tla_contract.py:96`) cũng làm đúng như vậy.

Nên change này **không đổi lược đồ, không bỏ việc gộp `account`, không thêm bảng**. Nó chỉ bắt ba
chỗ còn lại hỏi đúng câu mà bốn chỗ kia đã hỏi đúng:

> Đừng hỏi *"người này **thuộc về** ai"*. Hỏi *"người này **có mặt ở** đâu"*.

## What Changes

- **`db/connect.py`** — thêm một phép tra khoá đôi `(agent_id, username) → account_id` đọc từ
  `dim_user`. `account_lookup()` hiện tại trả `username → (account_id, unit_agent_id)`; phép tra
  mới không cần trả `unit_agent_id` nữa, vì không còn gì để đem đi so sánh.
- **`db/load_gateway.py`** — bỏ phép so `found[1] == agent_id`, thay bằng tra khoá đôi. Bộ đếm
  `identity_unresolvable` **giữ nguyên tên và ý nghĩa**; nó phải về 0 cho người có trong danh bạ,
  và phải **vẫn tăng** cho định danh lạ.
- **`backend/store.py`** — `accounts()` trả **danh sách** agent nơi người đó có mặt, thay cho một
  agent thắng. Cột `unit_agent_id` vẫn trả về, vì nó là thứ giải thích phòng ban đang hiển thị.
- **`web/js/`** — màn hình danh bạ đọc danh sách ấy. Lọc theo agent phải khớp *có mặt ở*, không
  phải *thuộc về*.
- **Phép kiểm âm bắt buộc** trong `scripts/audit_db.py`: không người nào có trong danh bạ một agent
  mà lại rơi vào tài khoản neo của agent ấy.

## Không làm trong change này

- **Không bỏ việc gộp `account`.** Đã cân nhắc và loại — xem `design.md`. Gộp là thứ duy nhất trả
  lời được *"bao nhiêu con người thật đang dùng AI"*, và ô KPI tổng người dùng (`web/js/app.js:3568`)
  đọc thẳng `accounts.length`. Tách ra là con số ấy tự tăng 5 mà không ai bấm gì.
- **Không bỏ `account.username UNIQUE`.** Ràng buộc ấy là thứ giữ cho việc gộp không trôi.
- **Không đổi phòng ban đang hiển thị (lỗi 3).** `unit_conflict` đã ghi nhãn, nên đây là lựa chọn
  chứ không phải nghĩa vụ. Tách ra thành việc riêng, làm sau, khi có người thật sự cần đọc phòng ban
  theo từng agent.
- **Không đụng 6 agent một-người-dùng.** `svc.<code>` mang mã agent trong chính tên nó nên không bao
  giờ va chạm; phép tra khoá đôi phải cho chúng kết quả y hệt hôm nay.
