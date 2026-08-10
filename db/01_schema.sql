-- =====================================================================
-- Token Ledger - lop CORE
-- Nguon: docs/plan-xay-dung-database-2026-08-07.md muc 4.2 / 4.3 / 4.5
--        docs/mui-gio-2026-08-08.md (quyet dinh M-A .. M-H)
--
-- 14 bang + 1 view: 6 dim_ + 5 fact_ + 3 ref_
--   Ke hoach goc ghi 12 (5+4+3). Thay doi so voi ke hoach:
--     + dim_model_alias  ba nguon goi ten model theo ba kieu, xem ghi chu o bang
--     + fact_perf_daily  hai cong to cua Google khong giao nhau, xem ghi chu o bang
--
-- LUU Y KHI VIET SCRIPT DOC BANG NAY: ten agent co dau tieng Viet. Console
-- Windows mac dinh cp1252 se NEM UnicodeEncodeError khi in ra. Ghi ra file UTF-8
-- hoac dat PYTHONIOENCODING=utf-8 truoc khi in.
--
-- CHAY DUOC CA PostgreSQL LAN SQLite.
--   Khong dung SERIAL - moi khoa deu gan tuong minh. Ly do khong phai de
--   tuong thich: dim_agent 8 dong va dim_model 10 dong von da go tay, nen
--   khoa tu sinh khong mang lai gi ngoai viec so ID doi moi lan nap lai.
--   Nho vay kiem duoc toan bo khau nap bang SQLite khi Docker chua chay.
-- =====================================================================


-- =====================================================================
-- 1. BANG DANH MUC
-- =====================================================================

CREATE TABLE dim_agent (
    agent_id                 INT PRIMARY KEY,
    ma                       TEXT UNIQUE NOT NULL,
    ten                      TEXT NOT NULL,
    gcp_project_id           TEXT,              -- NULL voi Ralli: khong di qua GCP
    co_cay_to_chuc           BOOLEAN NOT NULL,  -- chi TLA HD va Ralli (quyet dinh A1)
    ngay_tao_project         DATE,
    ngay_bat_dau_co_du_lieu  DATE NOT NULL,
    ngay_ket_thuc_du_lieu    DATE,              -- NULL = con chay
    dang_van_hanh            BOOLEAN NOT NULL,
    -- Quyet dinh M-D: Ralli khong co billing lan monitoring. Cot nay ton tai
    -- de moi view biet luc nao phai tra ve '-' thay vi '0%'. Khong co no thi
    -- "khong do duoc" se hien ra man hinh y het "khong co loi nao".
    co_nguon_doi_chung       BOOLEAN NOT NULL
);

CREATE TABLE dim_unit (
    unit_id    TEXT PRIMARY KEY,
    agent_id   INT NOT NULL REFERENCES dim_agent,
    ten        TEXT NOT NULL,
    parent_id  TEXT REFERENCES dim_unit,
    cap        INT,
    duong_dan  TEXT,
    -- TRUE voi 6 dong 'Don vi su dung <agent>' va dong 'Chua quy duoc'.
    -- Thieu cot nay thi COUNT(*) dem ca dong ky thuat thanh phong ban that.
    la_dong_ky_thuat BOOLEAN NOT NULL
);

CREATE TABLE dim_user (
    user_id         TEXT NOT NULL,
    agent_id        INT NOT NULL REFERENCES dim_agent,
    username        TEXT NOT NULL,
    ho_ten          TEXT,
    email           TEXT,
    unit_id         TEXT REFERENCES dim_unit,
    dang_hoat_dong  BOOLEAN,
    ngay_tao        TIMESTAMP,
    la_dong_ky_thuat BOOLEAN NOT NULL,
    -- 'danh ba' | 'nhat ky' | 'ky thuat'.
    -- Ralli co user_id CHI xuat hien trong nhat ky chu KHONG co trong danh ba
    -- 890 nguoi: 'system' (6.986 luot), 'admin' (2 khoa khac nhau, 480 luot),
    -- 'guest'. Khong the nap dim_user thuan tu danh ba duoc.
    -- 'ky thuat' = 6 dong sinh ra cho 6 agent mot-nguoi-dung (quyet dinh A1).
    nguon_gap       TEXT NOT NULL,
    PRIMARY KEY (agent_id, user_id)
);

CREATE TABLE dim_model (
    model_id  INT PRIMARY KEY,
    ten       TEXT UNIQUE NOT NULL,   -- ten CHUAN, dang gach ngang
    ho        TEXT,
    provider  TEXT NOT NULL
);

-- Ba nguon goi ten model theo ba kieu. Khong co bang nay thi phai doan bang
-- chuoi, va 'gemini-embedding-001' voi 'gemini-embedding-1.0' khong co quy tac
-- chuan hoa nao noi duoc voi nhau.
CREATE TABLE dim_model_alias (
    nguon     TEXT NOT NULL,          -- 'billing_sku' | 'monitoring' | 'app'
    ten_goc   TEXT NOT NULL,
    model_id  INT NOT NULL REFERENCES dim_model,
    PRIMARY KEY (nguon, ten_goc)
);

CREATE TABLE dim_function (
    agent_id       INT NOT NULL REFERENCES dim_agent,
    ma             TEXT NOT NULL,
    nhan           TEXT,
    la_nguoi_dung  BOOLEAN,           -- NULL = chua biet, KHONG mac dinh true
    PRIMARY KEY (agent_id, ma)
);


-- =====================================================================
-- 2. BANG SU KIEN
-- Nguyen tac so mot: moi nguon mot bang rieng, khong tron.
-- =====================================================================

-- MOT dong = MOT loi goi API. Chi Ralli co muc nay.
CREATE TABLE fact_call (
    call_id              TEXT PRIMARY KEY,
    agent_id             INT NOT NULL REFERENCES dim_agent,
    thoi_diem_goc        TIMESTAMP NOT NULL,   -- chep nguyen, chua quy doi
    mui_gio_da_xac_nhan  BOOLEAN NOT NULL,     -- TRUE tu 08/08: da chung minh la UTC (M2)
    thoi_diem_ict        TIMESTAMP,
    user_id              TEXT,
    unit_id              TEXT REFERENCES dim_unit,
    model_id             INT REFERENCES dim_model,
    ma_ham               TEXT,
    prompt_tokens        BIGINT,
    completion_tokens    BIGINT,
    total_tokens         BIGINT NOT NULL,      -- cot chuan, KHONG tu cong hai nua (quy tac 6)
    cached_tokens        BIGINT,               -- NULL o 6.871 dong cu, KHONG phai 0 (quy tac 5)
    dinh_dang_ban_ghi    SMALLINT              -- 1 / 2 / 3
);

CREATE TABLE fact_billing_daily (
    ngay         DATE NOT NULL,        -- NGAY THEO GIO MY (Pacific) - xem M1
    project      TEXT NOT NULL,
    sku_id       TEXT NOT NULL,
    sku_ten      TEXT NOT NULL,
    model_id     INT REFERENCES dim_model,
    loai         TEXT NOT NULL,        -- 'input' | 'output' | 'cached'
    so_luong     BIGINT NOT NULL,
    chi_phi_usd  NUMERIC(14,6) NOT NULL,
    PRIMARY KEY (ngay, project, sku_id)
);

CREATE TABLE fact_monitoring (
    thoi_diem_utc  TIMESTAMP NOT NULL,
    thoi_diem_ict  TIMESTAMP NOT NULL,
    project        TEXT NOT NULL,
    phep_do        TEXT NOT NULL,
    -- NULL vi phep do dang request khong co nhan `model`. Ty le PHU THUOC TAP:
    -- 85,6% tren bang tho (450.138/525.639, phan lon la Drive), 39,6% trong
    -- view mon_sach (33.734/85.166). Con so hay duoc trich dan la 39,6%.
    model_id       INT REFERENCES dim_model,
    ma_tra_ve      TEXT,
    dich_vu        TEXT NOT NULL,              -- quy tac 9: res_service, rong thi lay tien to metric_type
    phuong_thuc    TEXT,
    credential_id  TEXT,                       -- cung phut cung method van co nhieu chuoi neu nhieu API key
    la_han_muc     BOOLEAN NOT NULL,           -- TRUE voi *_limit: ALIGN_MAX, KHONG duoc SUM
    gia_tri        DOUBLE PRECISION NOT NULL,
    don_vi         TEXT
);

-- Bang dashboard dung nhieu nhat. Cot `nguon` cho phep cung mot ngay co nhieu
-- con so tu nhieu nguon ma khong de len nhau - chinh la cach phat hien ra app
-- ghi thieu 17%.
-- MOI COT KHOA DEU NOT NULL. Ban dau de unit_id/user_id/model_id nhan NULL, va
-- do la mot cai bay im lang:
--   PostgreSQL  PRIMARY KEY => NOT NULL, se TU CHOI dong billing dau tien
--   SQLite      cho phep NULL trong khoa chinh, va coi NULL != NULL, nen NHAN
--               CA HAI DONG GIONG HET NHAU. Da thu, no nhan that.
-- Cach chua: dung dong ky thuat o dim_unit/dim_user thay cho NULL.
--   model_id KHONG can dong ky thuat - da kiem, ca 3 phep do token deu co nhan
--   model (0/12.534, 0/12.258, 0/14 thieu). Phep do thieu model
--   (api_request_count, latencies) thuoc ve fact_perf_daily chu khong vao day.
CREATE TABLE fact_usage_daily (
    ngay          DATE NOT NULL,      -- NGAY THEO ICT (quyet dinh M-B)
    agent_id      INT NOT NULL REFERENCES dim_agent,
    model_id      INT NOT NULL REFERENCES dim_model,
    unit_id       TEXT NOT NULL REFERENCES dim_unit,
    user_id       TEXT NOT NULL,
    so_luot       INT,
    total_tokens  BIGINT,
    chi_phi_usd   NUMERIC(14,6),
    nguon         TEXT NOT NULL,      -- 'app' | 'billing' | 'monitoring'
    PRIMARY KEY (ngay, agent_id, model_id, unit_id, user_id, nguon)
);

-- BANG THU 13, ke hoach goc khong co.
-- Ly do: hai cong to cua Google khong giao nhau. Phep do token co nhan `model`
-- nhung khong co ma tra ve; api_request_count co ma tra ve nhung khong co model
-- (39,6% dong co o model rong). Nen so lieu hieu nang KHONG nhet vao
-- fact_usage_daily duoc - khoa cua no khong co cho cho ma_tra_ve.
-- Thieu bang nay thi /api/perf/summary va /api/perf/codes khong co nguon.
CREATE TABLE fact_perf_daily (
    ngay        DATE NOT NULL,        -- ICT
    agent_id    INT NOT NULL REFERENCES dim_agent,
    phuong_thuc TEXT NOT NULL,
    ma_tra_ve   TEXT NOT NULL,
    so_luot     INT NOT NULL,
    -- p95/p99 gop tu histogram, KHONG phai trung binh cac phan vi tung phut.
    -- Hai cot `_o_tu`/`_o_den` la be rong o chua phan vi: histogram gop lai thi
    -- chinh xac, nhung doc mot phan vi ra van phai noi suy trong o, ma o rong
    -- gap doi sau moi bac. Trung vi be rong = 57% cua chinh gia tri p95.
    -- Dashboard phai hien KHOANG, khong phai so le.
    p95_giay     DOUBLE PRECISION,
    p95_o_tu     DOUBLE PRECISION,
    p95_o_den    DOUBLE PRECISION,
    p99_giay     DOUBLE PRECISION,
    du_mau       BOOLEAN NOT NULL,    -- FALSE khi so_luot < 10: phan vi khong co y nghia
    PRIMARY KEY (ngay, agent_id, phuong_thuc, ma_tra_ve)
);


-- =====================================================================
-- 3. BANG THAM CHIEU (quy uoc do NGUOI quyet dinh, khong phai do do duoc)
-- =====================================================================

CREATE TABLE ref_price (
    model_id     INT NOT NULL REFERENCES dim_model,
    hieu_luc_tu  DATE NOT NULL,
    gia_input    NUMERIC(12,8),       -- USD / 1 trieu token
    gia_output   NUMERIC(12,8),
    gia_cached   NUMERIC(12,8),
    nguon        TEXT NOT NULL,       -- 'suy nguoc' | 'google' | 'nha cung cap'
    PRIMARY KEY (model_id, hieu_luc_tu)
);

CREATE TABLE ref_fx (
    ngay         DATE PRIMARY KEY,
    vnd_moi_usd  NUMERIC(12,2) NOT NULL,
    nguon        TEXT NOT NULL        -- 'go cung' cho den khi keo API (M-F)
);

CREATE TABLE ref_budget (
    agent_id       INT NOT NULL REFERENCES dim_agent,
    thang          DATE NOT NULL,
    ngan_sach_usd  NUMERIC(12,2),
    -- Ralli bi chan theo TOKEN (50.000.000/thang), 6 agent kia theo TIEN.
    -- Khong quy doi: quy ra USD thi ngan sach troi moi lan bang gia doi, trong
    -- khi Ralli dang bi chan theo token that.
    ngan_sach_token BIGINT,
    PRIMARY KEY (agent_id, thang),
    CHECK (ngan_sach_usd IS NOT NULL OR ngan_sach_token IS NOT NULL)
);


-- =====================================================================
-- 4. VIEW
-- =====================================================================

-- Quyet dinh M-A: nap DU 525.639 dong, loc o tang view.
-- Bang tho giu ca luu luong Drive/Sheets/Compute vi chinh no la bang chung cho
-- quy tac 3 (pro-tuner sai 45,7 lan neu quen loc). View nay la cua duy nhat
-- nen di qua khi tinh toan.
CREATE VIEW mon_sach AS
SELECT *
FROM fact_monitoring
WHERE dich_vu = 'generativelanguage.googleapis.com'
  AND la_han_muc = FALSE;
