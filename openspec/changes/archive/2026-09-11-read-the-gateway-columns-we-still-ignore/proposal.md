# Đọc nốt những cột sổ Gateway đang bị bỏ qua

## Why

Ba cột trong `LiteLLM_SpendLogs` mà **không dòng mã nào của ta đọc tới**. Hai cột là trường
**bắt buộc** của sheet Data Out; cột thứ ba có thể **làm sai số liệu một cách im lặng**.

```
   grep -rn "cache_hit" db/ scripts/ backend/    ->  KHONG CO KET QUA NAO
```

### ① `cache_hit` — nguy hiểm nhất, và không ai biết nó tồn tại

Ngày 01/09/2026 nghiệm thu cache Redis dùng chung: hai request giống hệt nhau qua load
balancer rơi vào **hai instance khác nhau**, lượt thứ hai trúng cache trên instance chưa từng
ghi cache — 4.222 ms xuống 261 ms, cùng một `id` phản hồi.

Phép đo đó lộ ra một chuyện mà chú thích trong `docker/gateway/config.gateway.yaml` **nói
thiếu một nửa**. Chú thích chỉ cảnh báo *"trúng cache ghi `spend=0`"*. Đo thật:

```
   cache_hit = TRUE  ->  spend = 0   NHUNG  total_tokens = 352 (ghi DU)
```

`db/build_usage_daily.load_gateway()` cộng `total_tokens` với điều kiện `outcome = 'success'`.
Lượt trúng cache **có** `outcome = 'success'`, nên một lượt trúng cache **của agent thật** sẽ
lọt qua và cộng token mà nhà cung cấp **không hề tính**.

Hôm nay chưa rò, vì hai lý do — và **cả hai đều mong manh**: cache đang tắt bằng một dấu `#`
trong file cấu hình, và dòng trúng cache duy nhất đang có là của phép nghiệm thu nên **không
mang tag agent**, bị bộ nạp bỏ trước khi kịp vào bảng. Đổi một trong hai điều đó là rò.

Và cột này còn một bẫy nữa: nó là **`text`**, chứa chuỗi `'None'` chứ không phải SQL NULL — nên
`WHERE cache_hit IS NULL` trả về **0 dòng** dù 41/47 dòng không có thông tin. Xem design ②.

### ② `virtual_key_id` — trường Bắt buộc số 26 của Data Out

Đo 01/09 trên 47 dòng sổ:

```
   8112bdb7ec...              35 dong  45.117 token   khoa ao cua DMS
   b3f2765d1d...               1 dong      17 token   khoa ao thu hai
   litellm_proxy_master_key   11 dong     827 token   KHOA TONG, khong phai khoa agent
```

**11/47 lượt đi bằng khoá tổng.** Chúng chỉ quy được về agent nhờ tag, không nhờ khoá — và
hiện **không có cách nào tách chúng ra** khỏi lưu lượng thật của agent.

### ③ `raw_model` — trường Bắt buộc số 11 của Data Out

Bộ nạp đọc cột `model`, ánh xạ sang `model_id`, rồi **vứt tên gốc đi**. Đo 01/09:

```
   gemini/gemini-3.5-flash-lite   42 dong   ten upstream
   gemini/gemini-3.6-flash         2 dong   ten upstream
   gemini-flash-lite               2 dong   BI DANH  <- model_id ra NULL
   gemini-flash                    1 dong   BI DANH  <- model_id ra NULL
```

3/47 dòng mang **bí danh** nên `model_id` ra NULL. Khi đó ta mất luôn bằng chứng tên model là
gì — trong khi đó chính là thứ cần để biết nên khai thêm tuyến nào.

## What Changes

- **Migration 007**: `fact_call` thêm `raw_model`, `virtual_key_id`, `cache_hit`.
- **`db/load_gateway.py`**: nạp ba cột đó từ `model`, `api_key`, `cache_hit`.
- **`db/build_usage_daily.py`**: loại lượt trúng cache khỏi số token và tiền.
- **`scripts/audit_db.py`**: phép kiểm chặn lượt trúng cache lọt vào bảng tổng hợp, và phép
  kiểm mọi dòng gateway đều có `raw_model`.
- **Đo** cache có tách theo khoá ảo không — hiện **chưa biết**, và nếu không tách thì một agent
  có thể nhận câu trả lời đã tính tiền cho agent khác.

Không đụng: sổ `LiteLLM_SpendLogs` (chỉ đọc), ba nguồn cũ, tầng view, tầng frontend.

## Impact

- Đóng **hai trường bắt buộc cuối cùng** của sheet Data Out → mục Master Plan *"Ghi đủ trường
  cần cho dashboard ngay tại thời điểm gọi"* (mốc 21/09) đạt 21/26 trường, 0 trường bắt buộc
  còn thiếu.
- Gỡ điều kiện chặn việc bật cache Redis: sau change này, bật cache không còn làm phồng token.
- Tách được lưu lượng đi bằng khoá tổng khỏi lưu lượng thật của agent.
- Rủi ro chính: `cache_hit` có **hai cái bẫy ngược nhau ở hai đầu**. Ở nguồn nó là `text` mang
  chuỗi `'None'`, nên `IS NULL` và `IS NOT TRUE` đều vô dụng. Ở đích nó là `boolean` thật, nên
  `NOT cache_hit` sẽ vứt mất **38/41 dòng** nạp được và kéo token gateway về **0**. Chống bằng
  `CASE` tường minh ở vế nạp, `IS NOT TRUE` ở vế tổng hợp, và bằng việc **chạy thử cả hai cách
  viết sai** rồi ghi số đo — xem design ② và việc 4.2.
