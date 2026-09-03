-- 004 - `fact_call` don them nguon thu tu: API Gateway.
--
-- VI SAO PHAI THEM COT, KHONG NAP THANG DUOC
-- ------------------------------------------
-- Truoc migration nay, MOI dong cua fact_call deu duoc coi la cua app:
--
--     build_usage_daily.py:212   out = [(*r, None, "app") for r in rows]
--
-- Do la gan CUNG, khong doc tu du lieu. Nap luu luong Gateway vao bang nay ma
-- khong co cot `source` thi no bi dem thanh luu luong cua app - va khong phep
-- kiem nao bao, vi tong van khop.
--
-- HAI COT
-- -------
-- `source`    8.631 dong dang co deu la app, nen DEFAULT 'app' la dung nghia
--             chu khong phai mot gia tri tam. Khoa ngoai toi ref_source cho khop
--             cach fact_usage_daily dang lam - `gateway` da co san trong bang do.
--
-- `cost_usd`  Gateway CO tien (LiteLLM tinh tu bang gia noi bo cua no), app thi
--             KHONG. NULL o dong app la dung nghia "nguon nay khong co tien",
--             khong phai "thieu du lieu". Nullable, khong DEFAULT.
--
-- TIEN: tu PostgreSQL 11, ADD COLUMN ke ca co DEFAULT khong viet lai bang - gia
-- tri di vao sieu du lieu. Nang luc nay da duoc dien tap o migration 002/003.
--
-- CHI MUC: moc nap tang dan cua db/load_gateway.py hoi dung mot cau
--     SELECT max(ts_raw) FROM fact_call WHERE source = 'gateway'
-- Voi 8.631 dong thi quet bang cung xong, nhung bang nay lon nhanh: MOT luot
-- phan loai cua DMS de ra HAI dong.

ALTER TABLE fact_call
    ADD COLUMN source TEXT NOT NULL DEFAULT 'app';

ALTER TABLE fact_call
    ADD CONSTRAINT fact_call_source_fkey
    FOREIGN KEY (source) REFERENCES ref_source(source);

ALTER TABLE fact_call
    ADD COLUMN cost_usd NUMERIC;

CREATE INDEX fact_call_source_ts_idx ON fact_call (source, ts_raw);

COMMENT ON COLUMN fact_call.source IS
    'Nguon cua dong. Khoa ngoai toi ref_source. Truoc 31/08/2026 bang nay chi co '
    'nguon app nen gia tri do la DEFAULT.';
COMMENT ON COLUMN fact_call.cost_usd IS
    'Tien USD, CHI co o nguon gateway va la so UOC TINH tu bang gia noi bo cua '
    'LiteLLM, khong phai so Google xuat hoa don. NULL o nguon app la dung nghia.';
