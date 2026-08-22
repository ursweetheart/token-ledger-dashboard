# Hệ thống phải đón được nguồn thứ tư mà không phải sửa một câu SQL nào

## Why

Master Plan yêu cầu Gateway chạy **song song với ba nguồn cũ tối thiểu 2 tuần** (giai đoạn
7) và báo cáo đối chiếu chênh lệch giữa **bốn nguồn** (giai đoạn 6). Ngày Gateway bật,
database sẽ có bốn bộ đếm cùng lúc.

Hôm nay hệ thống **không đón được nguồn thứ tư** — không phải vì thiếu tính năng, mà vì
một chuỗi ký tự mang nghĩa ngầm.

### `'app'` không có nghĩa là "nguồn tên app"

Trong code hôm nay, `source = 'app'` thực ra có nghĩa **"nguồn duy nhất biết ai là người
dùng"**. Hai nghĩa đó trùng nhau — cho tới ngày Gateway xuất hiện, vì Gateway cũng biết
người dùng.

Đếm 21/08/2026: **24 chỗ / 8 file** so sánh với chuỗi `'app'`. Nhưng con số đó gộp hai
loại việc trái ngược, và chỉ một loại là lỗi:

```
   ĐẦU GHI (14 chỗ) — ĐÚNG, GIỮ NGUYÊN     ĐẦU ĐỌC (10 chỗ) — ĐÂY LÀ PHẠM VI
   load_hd.py · load_ralli.py              backend/store.py    :257 :263 :452
   build_usage_daily.py · rebuild_db.py    db/01_schema.sql    :600 :648
   gen_catalog.py                          scripts/audit_db.py :163 :263 :290 :312 :413
        │                                       │
   "dòng này TỪ app" — mô tả đúng          "chỉ lấy dòng của app" — lọc mất Gateway
```

`load_ralli.py` ghi `source='app'` vì nó **đúng là** loader của app. Gateway không đụng
tới. Chỉ 10 chỗ đầu đọc thuộc change này.

### Chuyện sẽ xảy ra nếu không sửa

Gateway ghi dữ liệu vào `source='gateway'` mang đầy đủ username. Đo hiện trạng
21/08/2026 (Postgres, kỳ 2026-01-01 → 2026-08-17):

| | Hôm nay | Sau khi Gateway chạy, nếu KHÔNG sửa |
|---|---:|---|
| `usage_by_account` (`01_schema.sql:648`) | **320 dòng · 107.926.810 token** | **y nguyên 320 dòng** — không một dòng Gateway nào |
| Tỷ lệ quy về người (`store.py:257,263`) | 107,9M / 867,7M = **12,4%** | **đứng im 12,4%** |
| `audit_db.py` | 33 phép / 0 hỏng | **33 phép / 0 hỏng** |

**Không có lỗi nào.** Chỉ là một dashboard đã có dữ liệu tốt mà không chịu hiển thị. Đúng
loại hỏng mà cả ngày 20/08 đi bịt: sai một cách im lặng.

Ba nguồn hiện có, đo trên `fact_usage_daily`:

| `source` | dòng | token |
|---|---:|---:|
| `billing` | 965 | 708.868.471 |
| `monitoring` | 539 | 450.972.068 |
| `app` | 341 | 110.640.605 |

Và sau khi `usage_resolved` khử trùng lặp:

| `token_source` | dòng | token |
|---|---:|---:|
| `billing` | 965 | 708.868.471 |
| `app` | 168 | 104.990.903 |
| `monitoring` | 46 | 53.797.736 |
| *(NULL)* | 10 | — |
| | | **867.657.110** |

### Đo 21/08 vừa gỡ bỏ rủi ro lớn nhất của việc này

Nỗi lo lớn nhất khi thêm nguồn Gateway là *"bài toán hoà giải danh tính không biến mất,
chỉ chui vào trong token"*. Đã đo (`tu-dien-database.md` §8f):

```
   JWT claim                account.username            account_id
   "c4led.lamln"     ───▶   đã LOWER(TRIM())     ───▶   khoá số đang có
        │
   Trợ lý ảo Ralli     -> claim  sub
   Trợ Lý Ảo Hợp Đồng  -> claim  username     (KHÔNG phải sub)
   6 agent một-người-dùng -> hằng số  svc.<code>
```

Hai vế đo riêng, ra cùng một hình dạng:

| | Ralli `/users/list` | `account` (kind='real') |
|---|---:|---:|
| dạng có dấu chấm (`c4led.lamln`) | 814/891 | **814/937** |
| là ObjectId 24 hex | **0**/891 | **0**/937 |

Nghĩa là dòng Gateway nối thẳng vào `account_id` đang có: **không phải mở rộng bảng
`account`, không phải thêm một chiều hoà giải nào.** Trước 21/08 đây là giả định; giờ là
số đo.

### Vì sao đây KHÔNG phải "bỏ cột nguồn"

Đề xuất ban đầu là bỏ các cột định nghĩa nguồn. Master Plan nói ngược lại ở bốn chỗ (giai
đoạn 6, 7, 8, và `Data Out` #21). Change này **giữ nguyên** cột nguồn và làm cho việc
**thêm** một giá trị vào nó không còn đau: thêm nguồn thứ tư phải là **thêm một dòng dữ
liệu**, không phải sửa 10 câu SQL nằm rải ở 3 file.

## What Changes

- **Bảng `ref_source(source, knows_user, has_cost, era, ghi_chu)`** — nguồn tự khai năng
  lực của mình. Đây thành chỗ **duy nhất** biết `'app'` và `'gateway'` cùng biết người dùng
- **10 chỗ đầu đọc** chuyển từ so tên nguồn sang hỏi năng lực (`knows_user`)
- **`usage_resolved`** thêm CTE thứ tư đứng **đầu** thứ tự ưu tiên `COALESCE(g, b, m, a)`
  — Gateway là bộ đếm của chính ta và có mặt ngay trong ngày, không đợi hoá đơn ~1 ngày.
  `token_source` nhận thêm giá trị `'gateway'`
- **Hai phép kiểm mới** trong `audit_db.py`:
  - dòng `gateway` mang username **không tra ra `account_id`** → kêu. Đây là lưới an toàn
    thay cho việc chờ một token nhân viên thường (quyết định 21/08)
  - `source` có trong dữ liệu mà **không có dòng trong `ref_source`** → kêu
- **Kịch bản nghiệm thu** `tools/dien_tap_gateway.py` — chèn dòng giả mang username THẬT
  lấy từ `account`, chạy toàn bộ phép kiểm, so số trước/sau, rồi **`ROLLBACK`**

**KHÔNG làm trong change này**

- Không đụng 14 chỗ đầu ghi. `load_ralli.py` ghi `source='app'` là mô tả đúng sự thật
- Không dựng `fact_request` / `fact_attempt` — chúng thuộc kiến trúc đích, không thuộc
  việc đón nguồn thứ tư
- Không bỏ `token_source` / `token_estimated` — giai đoạn 6–8 cần chúng
- Không dựng LiteLLM thật. Đây là nghiệm thu **hình dạng dữ liệu**, không phải nghiệm thu
  **đường truyền**. Cái đó là D3, và nó cần `config.yaml`, mà `config.yaml` cần A4 xong

## Impact

| | |
|---|---|
| **Specs** | `data-source-registry` (mới) |
| **Code** | `db/01_schema.sql` · `backend/store.py` · `scripts/audit_db.py` · `tools/dien_tap_gateway.py` (mới) |
| **Rebuild** | **Có** — thêm bảng và sửa view, phải chạy lại `scripts/rebuild_db.py` |
| **Đồng nghiệp** | Phải bổ sung `dong-bo-may-dong-nghiep-*.md` |
| **Không đụng** | `web/` — frontend đọc qua API, không biết tên nguồn |
| **Rủi ro** | **Trung bình.** `usage_resolved` là *cửa chính để hỏi số liệu*; sửa sai là mọi con số trên dashboard sai theo. Lưới: task 1 ghi mốc trước, task 7 so từng con số sau |
| **Quay lui** | Mỗi nhóm task một commit. Nhóm 2 (`ref_source`) độc lập với nhóm 3 (`usage_resolved`) |

### Ba cái bẫy đã biết trước

1. **Dòng `scrape` để NULL ở cột mới.** Truy vấn dùng cột mới mà không xử lý NULL sẽ **âm
   thầm bỏ 8 tháng lịch sử** (`tu-dien-database.md` §8b). Task 5.3 kiểm điều này.
2. **Cộng thẳng `fact_usage_daily` là đếm hai lần.** Bẫy này đã cắn hai lần trong ngày
   20/08 — đo thử ra 143,9% và "phần còn lại" âm 43,9%. Mọi phép đo trong change này phải
   đi qua `usage_resolved`.
3. **`cached` có ba nghĩa.** Chỉ nguồn billing mới có cached nằm ngoài input; của app nó
   là tập con của prompt. `tools/do_tien_suy_ra.py` đã dính bẫy này ngày 20/08.
