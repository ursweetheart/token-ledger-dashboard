# Tasks

Quy ước: mỗi mục đo được thì **ghi số đo ngay tại chỗ**, không ghi "đã kiểm tra".

## 1. Ghi mốc trước khi đổi

- [x] 1.1 `fact_call`: **8.672 dòng / 50.113.744 token / 20 cột** — app 8.631, gateway 41
- [x] 1.2 Bốn nguồn trên `fact_usage_daily`: app 371 · billing 1.012 · monitoring 606 · gateway 1/45.187
- [x] 1.3 Lưu `var/baseline-2026-09-01-truoc-007.json` — so với mốc 31/08: **23/24 khoá khớp**, lệch đúng `fact_call` 8.669→8.672 (3 dòng hỏng change 006 cố ý thêm)
- [x] 1.4 Sổ nguồn 47 dòng. `cache_hit` kiểu **TEXT**: `'None'` **41** · `'False'` **5** · `'True'` **1** — **không một dòng SQL NULL nào**
- [x] 1.5 `api_key`: khoá ảo `8112bd…` 35 · `b3f276…` 1 · **khoá tổng 11/47 = 23,4%**
- [x] 1.6 `model` thô: upstream 44 dòng · bí danh 3 dòng — nhưng chỉ **2** vào được `fact_call`, vì `gemini-flash` không có tag agent
- [x] 1.7 `fact_call` gateway: `model_id = 12` **39 dòng / 45.201 token** · `model_id` NULL **2 dòng / 0 token**
- [x] 1.8 Trong **41 dòng nạp được** (có tag agent): `cache_hit` `'None'` **38**/45.187 · `'False'` **3**/14 · `'True'` **0**. Khoá: DMS **34**/45.117 · **khoá tổng 7/41 = 17,1%**/84 token

## 2. Migration 007

- [x] 2.1 `007_cot_bi_bo_qua` ← `006_do_tre_va_ket_cuc`, forward-only
- [x] 2.2 `raw_model TEXT` nullable, không DEFAULT
- [x] 2.3 `virtual_key_id TEXT` nullable, không DEFAULT
- [x] 2.4 `cache_hit BOOLEAN` nullable, không DEFAULT — **không** đặt DEFAULT false
- [x] 2.5 Cả ba có `COMMENT ON COLUMN`. Riêng `cache_hit` phải ghi **cả hai bẫy**: nguồn là TEXT mang chuỗi `'None'`, đích là BOOLEAN nên phải lọc bằng `IS NOT TRUE`
- [x] 2.6 Nghiệm thu **đạt cả 6/6**: 8.672 dòng · 50.113.744 token · 20 → **23 cột** · head `007_cot_bo_qua` · ba cột mới **0 dòng có giá trị** · app 8.631 / gateway 41 không đổi

## 3. Sửa `db/load_gateway.py`

- [x] 3.1 Lấy thêm `model` (nguyên văn), `api_key`, `cache_hit` ở câu SELECT
- [x] 3.2 `raw_model` nạp nguyên văn — **không** chuẩn hoá, **không** cắt tiền tố `gemini/`
- [x] 3.3 `virtual_key_id` nạp nguyên văn — giữ cả chuỗi `litellm_proxy_master_key`
- [x] 3.4 `cache_hit` dịch bằng `CASE WHEN 'True' … WHEN 'False' … ELSE NULL`. **Cấm `::boolean`**: gặp giá trị thứ tư là câu truy vấn ném lỗi giữa chừng
- [x] 3.5 Đếm và cảnh báo số dòng `cache_hit` mang **giá trị lạ** — cùng cơ chế đã làm cho `outcome`
- [x] 3.6 `ON CONFLICT` mở rộng `DO UPDATE` cho đúng ba cột mới — nếu không, 41 dòng cũ rỗng vĩnh viễn (đúng lỗi đã mắc ở migration 006)
- [x] 3.7 Chạy thật: `di bang KHOA TONG 7/41 | trung cache 0 | mang bi danh 2` — cả ba khớp mốc 1.6/1.8
- [x] 3.8 Đối chiếu khớp: nguồn **47/45.961** = đích **41/45.201** + bỏ qua **6/760**

## 4. Sửa `db/build_usage_daily.py`

- [x] 4.1 Thêm `AND cache_hit IS NOT TRUE` — lọc ở **vế đích** (`fact_call`, kiểu BOOLEAN). Ở vế nguồn câu này **lỗi kiểu**, xem design ②
- [x] 4.2 **Đã chứng minh cả ba chiều** bằng phép thử âm đảo ngược được — đặt `cache_hit=true` lên một dòng có sẵn (6.866 token) rồi khôi phục bằng chính `load_gateway.py`:
      · (ĐÚNG) `IS NOT TRUE` → **38.321** token, loại đúng dòng đó
      · (sai a) bỏ bộ lọc → **45.187** token, **rò 6.866**
      · (sai b) `NOT cache_hit` → **0 dòng / 0 token**, mất sạch 38.321
      Khôi phục xác nhận: `cache_hit` về 38 NULL + 3 false, gateway về 45.187
      *Không dùng cách tạo dòng sổ mang tag agent thật — xem việc 6.*
- [x] 4.3 Bốn nguồn khớp mốc 1.2 **tuyệt đối**: app 371/112.775.370 · billing 1.012/751.189.404 · monitoring 606/496.933.793 · gateway 1/45.187

## 5. Sửa `scripts/audit_db.py`

- [x] 5.1 Phép kiểm `Luot trung cache khong lot vao bang tong hop` — **đạt**
- [x] 5.2 Phép kiểm `Moi dong gateway deu co raw_model` — **đạt**
- [x] 5.3 Phép kiểm `Moi dong gateway deu co virtual_key_id` — **đạt**
- [x] 5.4 **Không** thêm phép kiểm "không dòng nào dùng khoá tổng" — hôm nay sẽ đỏ ngay với 11 dòng, xem design ④
- [x] 5.5 Chạy đầy đủ: **42 phép kiểm · 38 đạt · 4 lưu ý · 0 hỏng** (39→42). Bốn lưu ý đều là thiếu dữ liệu đã biết từ trước, không phải mới

## 6. Tự tạo bằng chứng: một lượt trúng cache CÓ tag agent

Dòng trúng cache đang có mang tag `User-Agent:` nên bộ nạp bỏ nó. Không có dòng nào chứng minh
được lỗ rò — phải tự tạo.

- [ ] 6.1 Lấy khoá ảo của DMS (không in ra ngoài), sao lưu `config.gateway.yaml`
      → **BỊ CHẶN** — đọc biến môi trường chứa khoá bị phân loại là truy cập bí mật và bị từ chối. Đây là chặn đúng, không tìm cách lách
- [ ] 6.2 Bật cache, khởi động lại hai instance, xác nhận `Setting Cache on Proxy`
      → (chờ 6.1)
- [ ] 6.3 Gọi cùng một câu **hai lần bằng khoá ảo DMS** → sinh ra dòng `cache_hit='True'` mang tag `dms-feedback`
      → (chờ 6.1)
- [ ] 6.4 Gọi **đúng câu đó bằng khoá ảo thứ hai** → ghi lại `cache_hit` ra `'True'` hay `'None'`. Đây là phép đo *cache có tách theo khoá không*
      → (chờ 6.1)
- [x] 6.5 Cache đang tắt, `git diff docker/gateway/config.gateway.yaml` **rỗng** (đã tắt lại từ phép nghiệm thu 01/09)
- [ ] 6.6 Ghi kết quả 6.4 vào tài liệu. **KHÔNG** đổi cấu hình theo kết quả — đó là quyết định của người, không phải của change này
      → (chờ 6.4)

## 7. Nghiệm thu bằng dữ liệu thật

- [x] 7.1 Đạt: 41/41 dòng có `raw_model`. `gemini/gemini-3.5-flash-lite`→model_id 12 (39 dòng) · `gemini-flash-lite`→model_id NULL (**2** dòng, giữ nguyên bí danh)
- [x] 7.2 Khớp mốc 1.8 tuyệt đối: **34** dòng khoá DMS/45.117 token · **7** dòng khoá tổng/84 token
- [ ] 7.3 Dòng `cache_hit = true` có mặt trong `fact_call` nhưng **không** có mặt trong `fact_usage_daily`
      → **chờ việc 6**. Cơ chế đã chứng minh bằng phép thử âm ở 4.2, nhưng chưa có dòng trúng cache THẬT mang tag agent
- [x] 7.4 Hai lần liên tiếp giống hệt: `dung duoc 6 | chen moi 0 | ghi de 6`
- [x] 7.5 **24/24 khoá khớp, 0 lệch** so với `baseline-2026-09-01-truoc-007.json`

## 8. Tài liệu

- [x] 8.1 Mục 5: thêm `api_key`+`cache_hit` vào bảng, thêm **hai bẫy**, và `cache_hit` **ra khỏi** danh sách "không dùng được" (3→2 cột — ghi chú cũ nói sai). Mục 7: **bốn → năm** quy tắc bộ nạp
- [x] 8.2 `docs/reference/cot-bi-bo-qua-01-09.md` — 8 mục, 177 dòng
- [x] 8.3 Master Plan ô J11 (STT 4 mục tiêu 1): **19/26 → 21/26**, **0 trường bắt buộc còn thiếu**. Vẫn để VÀNG, không tự chuyển xanh
