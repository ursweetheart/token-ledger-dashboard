-- 007 - `fact_call` ghi them TEN MODEL GOC, KHOA DA GOI va TRANG THAI DEM.
--
-- VI SAO
-- ------
-- Ba cot nay DA CO san trong `LiteLLM_SpendLogs`, khong dong ma nao cua ta doc
-- toi. Do 01/09/2026:
--
--     grep -rn "cache_hit" db/ scripts/ backend/   ->  KHONG CO KET QUA NAO
--
-- Hai trong ba cot la truong BAT BUOC cua sheet Data Out (so 11 `raw_model` va
-- so 26 `virtual_key_id`). Cot thu ba, `cache_hit`, co the lam SAI SO LIEU mot
-- cach im lang - xem phan BAY o duoi.
--
-- BA COT, TAT CA NULLABLE VA KHONG DEFAULT
-- ----------------------------------------
-- Nguon `app` de NULL ca ba: nhat ky Ralli khong ghi ten model goc, khong co
-- khoa ao, va khong co khai niem dem. Dat gia tri cho chung la BIA - cung ly le
-- voi `outcome` o migration 006.
--
-- `cache_hit` KHONG dat DEFAULT false. "Khong biet" khac "khong trung dem".
--
-- Tu PostgreSQL 11, ADD COLUMN nullable khong DEFAULT chi ghi vao sieu du lieu,
-- khong viet lai bang. Nang luc nay da dien tap o migration 002/003.

ALTER TABLE fact_call
    ADD COLUMN raw_model TEXT;

ALTER TABLE fact_call
    ADD COLUMN virtual_key_id TEXT;

ALTER TABLE fact_call
    ADD COLUMN cache_hit BOOLEAN;

COMMENT ON COLUMN fact_call.raw_model IS
    'Ten model DUNG NHU Gateway nhan duoc, nguyen van, truoc khi anh xa sang '
    'model_id. Do 01/09/2026: 44/47 dong mang ten upstream (gemini/gemini-3.5-'
    'flash-lite), 3 dong mang BI DANH khai trong config.gateway.yaml (gemini-'
    'flash-lite, gemini-flash). Dong mang bi danh la dong HONG TRUOC khi Router '
    'chot tuyen, nen model_id ra NULL - va luc do cot nay la BANG CHUNG DUY NHAT '
    'con lai de biet nen khai them tuyen nao vao GATEWAY_MODELS. NULL o nguon '
    'app: nhat ky Ralli khong ghi ten goc.';

COMMENT ON COLUMN fact_call.virtual_key_id IS
    'Khoa da thuc hien luot goi, nguyen van tu cot api_key cua LiteLLM. KHONG '
    'chuan hoa: cot nguon TRON HAI LOAI - bam SHA-256 64 ky tu cho khoa ao, '
    'nhung chuoi thuong "litellm_proxy_master_key" cho khoa tong. Ep ve mot dang '
    'la mat dung cai phan biet dang can. Do 01/09: trong 41 dong nap duoc co '
    '7 dong (17,1%) di bang khoa tong - chung chi quy duoc ve agent nho tag chu '
    'khong nho khoa, va con so nay phai giam ve 0 khi 8 agent deu co khoa rieng.';

COMMENT ON COLUMN fact_call.cache_hit IS
    'true = luot duoc tra tu bo nho dem, KHONG toi nha cung cap. NULL = khong co '
    'thong tin (nguon app, hoac Gateway khong ghi). '
    'HAI CAI BAY NGUOC NHAU O HAI DAU: '
    '(1) VE NGUON `LiteLLM_SpendLogs.cache_hit` la TEXT va ghi CHUOI "None" cho '
    'truong hop khong co thong tin - KHONG phai SQL NULL. Nen `WHERE cache_hit '
    'IS NULL` tra ve 0 dong du 41/47 dong khong co thong tin, con `IS NOT TRUE` '
    'thi LOI KIEU. Bo nap phai dich bang CASE tuong minh, KHONG dung ::boolean '
    '(gia tri thu tu se nem loi giua chung). '
    '(2) VE DICH cot nay la BOOLEAN that voi NULL that, nen `NOT cache_hit` bien '
    'NULL thanh UNKNOWN va vut sach 38/41 dong. MOI phep tong hop PHAI loc bang '
    '`cache_hit IS NOT TRUE`. '
    'Luot trung dem VAN ghi du token (do duoc 352) nhung spend = 0, nen cong no '
    'vao luu luong la khai khong token ma nha cung cap khong he tinh.';
