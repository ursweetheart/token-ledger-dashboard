# Tasks

Quy ước: mỗi mục đo được thì **ghi số đo ngay tại chỗ**, không ghi "đã kiểm tra".

Thứ tự bắt buộc: nhóm **2** trước nhóm **3** — nhóm 3 gọi cờ mà nhóm 2 tạo ra.
Nhóm **4** sau cùng: phép kiểm phải soi một đường đã sửa xong.

## 1. Ghi mốc trước khi đổi

- [x] 1.1 `var/baseline-truoc-refresh-day-du.json`. `fact_latency_daily` **monitoring 339 ·
      gateway 1** · `fact_usage_hourly` monitoring 2.624 · app 698 · gateway 5 ·
      `fact_perf_daily` **669** (chỉ monitoring) · `fact_usage_daily` 4 nguồn · `fact_call`
      app 8.631 · gateway 41
- [x] 1.2 Đo hai lượt: **1,40 s** (lạnh) và **0,89 s** (ấm). Docstring ghi ~0,8 s — con số ấm
      khớp, con số lạnh thì không. Lấy **0,89 s** làm mốc
- [x] 1.3 Bốn mốc thời gian **đều ra 2026-08-31**: `fact_call` thô · `fact_call` sau bộ lọc ·
      `fact_usage_hourly` · `fact_latency_daily`.
      **Ghi rõ: số liệu hôm nay KHÔNG phân biệt được hai cách cài ở việc 4.2** — 3 lượt hỏng
      nằm lúc 02:27, thành công kéo tới 10:17, nên `MAX` thô và `MAX` đã lọc trùng nhau

## 2. `build_performance.py` nhận chế độ chỉ-Gateway

- [x] 2.1 `--chi-gateway` → `chi_gateway(cn, dc)`: `DELETE FROM fact_latency_daily
      WHERE source = 'gateway'` rồi `load_gateway_latency()`
- [x] 2.2 Gọi lại **chính** `load_gateway_latency()`. Không một dòng percentile nào được chép
      lại — docstring nêu đích danh bẫy 21/08 với `tools/dien_tap_gateway.py`
- [x] 2.3 Đã kiểm: `load_gateway_latency()` nhắc `LATENCY_CSV` **0 lần**; cả 4 chỗ nhắc (dòng
      44 · 100 · 102 · 108) đều ở hằng số module và nhánh `load_latency()`.
      Đo sau khi chạy: `fact_perf_daily` **669** không đụng
- [x] 2.4 `rebuild_db.py --from-step 9` chạy sạch: `fact_perf_daily` **669** ·
      `fact_latency_daily` **340** · *acceptance passed* · **10/10 bước**. Khớp mốc 1.1
- [x] 2.5 `chi_gateway()` **tự đếm mọi nguồn** trước/sau và `rollback` + `SystemExit` nếu nguồn
      khác đổi. Chạy thật: `gateway 1 -> 1 | cac nguon khac KHONG doi (monitoring=339)`.
      Đây là chỗ nguy hiểm nhất: chỉ đếm gateway thì một lệnh `DELETE` quên `WHERE` **vẫn cho
      kết quả đúng**
- [x] 2.6 Đổi tên tạm `latency-daily.csv` rồi chạy cả hai chế độ:

          che do day du   rc=1   (dung han, thong bao ro cach chua)
          --chi-gateway   rc=0   (chay sach)

      CSV đã trả lại nguyên **35.732 byte**

## 3. `refresh_gateway.py` làm mới đủ đường dẫn

- [x] 3.1 `STEPS` **2 → 4 bước**: `db/load_gateway.py` · `db/build_usage_daily.py` ·
      `db/build_usage_hourly.py` · `db/build_performance.py --chi-gateway`
- [x] 3.2 Thứ tự giữ đúng: bước 3 sau bước 2. Lý do ghi thẳng vào chú thích của `STEPS`
- [x] 3.3 `STEPS` nay mang **(nhãn, đường dẫn tương đối ROOT, tham số riêng)** — 3 phần tử thay
      vì 2. Bộ chạy đổi từ `ROOT / "db" / ten` sang `ROOT / duong_dan` kèm `*them`. Cùng hình
      dạng `rebuild_db.py` đang dùng
- [x] 3.4 Giữ nguyên. Thông báo lỗi nay in **đường dẫn** thay vì tên file trần
- [x] 3.5 `dem()` trả **5 giá trị** thay vì 3; dòng tóm tắt in **bốn** bảng. Giá trị của thay
      đổi này thấy ngay ở việc 4.4: khi chữa, màn hình hiện `fact_usage_hourly 0 -> 5` —
      trước đây bảng ấy không có mặt để mà nhúc nhích
- [x] 3.6 Docstring thêm khối **"HANH VI O CHE DO VONG LAP"**: `build_usage_hourly`
      `SystemExit` khi tổng lệch nên ở `--every` nó kêu mỗi chu kỳ; đó là hành vi ĐÚNG, và
      nhánh `try/except` sẵn có giữ vòng lặp không chết
- [x] 3.7 **0,89 s → 1,54 s.** Ước lượng ~1,8 s, đo thật **thấp hơn**. Với `--every 120` là
      1,3% chu kỳ. Docstring đã cập nhật con số

## 4. Phép kiểm canh bảng dẫn xuất cũ

- [x] 4.1 Phép kiểm `Gateway derived tables are as fresh as fact_call`, mức HỎNG, đặt trong
      nhóm F
- [x] 4.2 So trên **bộ lọc riêng của từng bảng**, không dùng chung một câu — hai bảng lọc khác
      nhau:

          build_usage_hourly    outcome='success' · model_id IS NOT NULL · cache_hit IS NOT TRUE
          load_gateway_latency  duration_ms IS NOT NULL · cache_hit IS NOT TRUE

      `load_gateway_latency` **không** lọc `outcome` — có chủ ý. Cảnh báo về việc số liệu hôm
      nay không phân biệt được hai cách cài đã ghi thẳng vào chú thích
- [x] 4.3 Dùng `check_tren(gw_call_dong, ...)` — 0 dòng gateway → CHƯA KIỂM ĐƯỢC. Chạy hôm nay:
      `(41 rows checked)`
- [x] 4.4 **Tái tạo được.** Xoá 5 dòng gateway khỏi `fact_usage_hourly` (giả lập đúng hành vi
      cũ) → phép kiểm **HỎNG**:

          [ FAIL ] Gateway derived tables are as fresh as fact_call (41 rows checked)
                   fact_usage_hourly: moc None nhung fact_call co den 2026-08-31
                   - gan nhu chac chan `refresh_gateway.py` da chay ma bo buoc.

      Chữa bằng chính `refresh_gateway.py` 4 bước → `0 -> 5`, xanh trở lại.
      **Phép so tổng KHÔNG bắt được tình huống này** — hôm nay không có dữ liệu gateway mới
      nên tổng vẫn khớp; mốc thời gian là thứ duy nhất bắt được

## 5. Nghiệm thu

- [x] 5.1 `rc=0`, báo cáo đủ **4 bảng**
- [x] 5.2 **73 · 66 · 7 · 0** (mốc 72 · 65 · 7 · 0). Thêm 1 phép, thêm 1 đạt, **lưu ý không
      tăng**, hỏng vẫn 0
- [x] 5.3 **31 · 31 · 0 · 0** — không đổi
- [x] 5.4 `fact_latency_daily`: monitoring **339** · gateway **1** — không đổi
- [x] 5.5 `rebuild_db.py` vẫn **10 bước**, không đổi một chữ
- [x] 5.6 Chạy hai lần liên tiếp: ảnh chụp 5 bảng **khớp hoàn toàn**
- [x] 5.7 Đối soát mốc 1.1: **khớp hết, 0 chỗ lệch**. Change này chỉ dựng lại bảng dẫn xuất

## 6. Tài liệu

- [x] 6.1 Mục 7 của `gateway-architecture-and-agent-integration.md` viết lại: liệt kê 4 bước,
      nêu vì sao bước 4 dùng `--chi-gateway`, và nêu phép kiểm mới canh khoảng trống này
- [x] 6.2 Nhật ký mục **16–20**. Ghi rõ khoản nợ **có ngày sinh**: `refresh_gateway.py` viết
      31/08 (`44997a8`), migration 008 sáng 03/09 thêm hai bảng mà không ai cập nhật nó theo —
      nợ sinh ra từ chính việc mình vừa làm. Tiêu đề nhật ký sửa thành **bốn** change
