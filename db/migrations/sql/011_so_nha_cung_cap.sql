-- 011 - So cua NHA CUNG CAP, de doi chieu voi so cua Gateway. KHONG phai nguon thu nam.
--
-- CAU HOI MA BANG NAY TRA LOI
-- ---------------------------
--     "Ngay A, nha cung cap noi ho da phuc vu bao nhieu luot va bao nhieu token?"
--
-- Do la mot cau hoi KHAC voi "so cua ta ghi bao nhieu". Bang nay giu cau tra loi
-- cua HO, de doi chieu voi cau tra loi cua TA trong `fact_call`.
--
-- VI SAO CAN
-- ----------
-- So Gateway tu no nhat quan, nen loi trong no khong lo ra bang cach nhin vao no.
-- Do duoc 04/09/2026 tren du lieu 31/08/2026:
--
--     nha cung cap   41 request, TAT CA response_code = 200, khong mot loi nao
--                    47.613 token vao + 3.922 token ra = 51.535
--     LiteLLM        44 dong = 39 thanh cong + 5 HONG
--                    41.717 + 3.523 = 45.240
--     fact_call      41 dong, 45.201
--
-- Nha cung cap KHONG thay loi nao. Vay 2 trong 41 luot ho phuc vu THANH CONG da
-- bi so Gateway ghi la hong voi 0 token. Ta loai luot hong khoi bang tong hop -
-- dieu do dung - nhung phan bi loai KHONG bang khong. 12,21% token cua ngay do
-- nam o cho nay.
--
-- Ten goi cua hinh dang loi: "luot hong khong phai luot mien phi" / failed_is_not_free.
--
-- ==========================================================================
-- BANG NAY KHONG PHAI MOT NGUON DU LIEU
-- ==========================================================================
-- `usage_resolved` KHONG doc bang nay, va KHONG BAO GIO duoc doc.
--
-- Doc no vao tong lưu luong la DEM DOI: cung mot luot goi da nam trong
-- `fact_call` roi. Bang nay la Y KIEN THU HAI ve cung mot luu luong, khong phai
-- luu luong moi. Neu sau nay ai do muon "gop them nguon provider cho day du" -
-- do chinh la nham lan ma dong nay sinh ra de chan.
--
-- Bang nay chi duoc doc boi phep kiem doi chieu trong scripts/audit_db.py.
--
-- ==========================================================================
-- VI SAO KHONG DUNG LAI fact_monitoring
-- ==========================================================================
-- Duong nap monitoring quy project ve agent qua `dim_agent.gcp_project_id`.
-- Project ma Gateway goi toi KHONG THUOC AGENT NAO - no la diem quan sat cua
-- chinh Gateway. Nhet no vao `dim_agent` de duong ong chay duoc se tao ra mot
-- "agent" khong ton tai, va agent gia do se hien len dashboard.
--
-- Nen `provider_project` o day la TEXT tran, KHONG co khoa ngoai toi dim_agent.
-- ==========================================================================

CREATE TABLE IF NOT EXISTS fact_provider_daily (
    day              DATE   NOT NULL,

    -- Ma project cua nha cung cap. TEXT tran, khong FK - xem ly le o tren.
    -- Vi du: 'project-e62bad30-a591-407b-ba7'
    provider_project TEXT   NOT NULL,

    -- Ten model NGUYEN GOC nha cung cap bao. Nam trong khoa chinh chu KHONG
    -- phai model_id: model_id co the NULL khi chua anh xa duoc, ma cot NULL
    -- thi khong lam khoa chinh duoc. Cung khuon voi fact_app_daily.raw_model.
    raw_model        TEXT   NOT NULL,

    -- Model chuan hoa. NULL khi nha cung cap bao mot ten ta chua anh xa duoc -
    -- de rong chu KHONG gan bua vao mot model nao.
    model_id         INT    REFERENCES dim_model(model_id),

    -- So luot nha cung cap noi ho da phuc vu. NULL = khong do duoc, khac han 0.
    requests         BIGINT,
    input_tokens     BIGINT,
    output_tokens    BIGINT,

    -- Tai khoan Google dung de keo. Giu lai vi hai tai khoan cho ra hai the
    -- gioi khac nhau, va sau nay khong ai nho project nao thuoc tai khoan nao.
    pulled_account   TEXT,
    pulled_at        TIMESTAMP,

    PRIMARY KEY (day, provider_project, raw_model)
);

COMMENT ON TABLE fact_provider_daily IS
    'So cua nha cung cap, chi de DOI CHIEU voi fact_call. usage_resolved KHONG doc bang nay - doc vao la dem doi.';

CREATE INDEX IF NOT EXISTS ix_provider_daily_day ON fact_provider_daily (day);
