-- 008 - DO MIN THEO GIO, va hai bang phan vi biet minh den tu NGUON NAO.
--
-- Migration nay lam BA viec, gop chung vi chung phuc vu cung mot muc tieu cua
-- Master Plan (STT 4 muc tieu 2, "ghi log dang time-series"):
--
--   (1) `fact_call` ghi them output_modality va thinking_enabled
--       -> hai truong Data Out con thieu, va CA HAI nam trong CUNG mot khoi
--          JSON `completion_tokens_details`. Nap mot cai ma bo cai kia la
--          quay lai doc dung khoi do lan thu hai.
--
--   (2) `fact_latency_daily` va `fact_perf_daily` co cot `source`
--       -> PHAI lam TRUOC khi do phan vi Gateway vao. Xem phan (2) o duoi.
--
--   (3) `fact_usage_hourly` - bang tong hop theo GIO
--       -> KHONG co nguon `billing`. Xem phan (3) o duoi.
--
-- FORWARD-ONLY. Khong co downgrade - quyet dinh cua change
-- `change-the-schema-without-dropping-it`.


-- =====================================================================
-- (1) fact_call: output_modality va thinking_enabled
-- =====================================================================
--
-- DOC TU `completion_tokens_details`, KHONG TU `prompt_tokens_details`.
-- Ban dau cua de xuat tro nham khoi; do lai moi ra. Hai khoi deu co
-- `text_tokens` 42/42 nen doc nham khoi VAN ra so, chi la so cua chieu NGUOC
-- lai - dung loai loi khong crash va khong ai thay.
--
--     completion_tokens_details co 7 khoa. Dem tren 42 luot thanh cong:
--         text_tokens        42/42
--         reasoning_tokens    2/42   <- chinh la "thinking"
--         audio/image/video   0/42
--
-- HAI COT, HAI KIEU KHAC NHAU - va do la co y:
--
--   output_modality  TEXT     nhan, khong phai so token. Theo dung quy uoc
--                             `fact_monitoring.output_modality` dang dung:
--                             gia tri 'text' (15.029 dong) hoac NULL (636.624).
--                             Ghi so token vao day la doi nghia cot giua hai
--                             nguon cua cung mot dashboard.
--
--   thinking_enabled BOOLEAN  o `fact_monitoring` cot cung ten la TEXT mang
--                             chuoi 'true'/'false' - vi do la bang HA CANH cua
--                             nhan Google gui sang. `fact_call` la bang cua TA,
--                             nen dung BOOLEAN that voi NULL that.
--                             Cung tien le voi `cache_hit` o migration 007:
--                             nguon LiteLLM la TEXT mang chuoi 'None', bo nap
--                             dich bang CASE tuong minh.
--
-- CA HAI NULLABLE, KHONG DEFAULT. Nguon `app` khong biet gi ve hai truong nay -
-- nhat ky Ralli khong ghi chung. Dat gia tri cho chung la BIA, cung ly le voi
-- `outcome` o 006 va ba cot o 007.

ALTER TABLE fact_call
    ADD COLUMN output_modality TEXT;

ALTER TABLE fact_call
    ADD COLUMN thinking_enabled BOOLEAN;

COMMENT ON COLUMN fact_call.output_modality IS
    'NHAN kieu du lieu cua phan HOI, KHONG phai so token. Theo dung quy uoc cua '
    'fact_monitoring.output_modality: chuoi ''text'', hoac NULL khi khong xac '
    'dinh duoc. Suy tu completion_tokens_details cua LiteLLM - khoi CHIEU RA, '
    'khong phai prompt_tokens_details (chieu VAO). Do 02/09/2026 tren 42 luot '
    'thanh cong: text_tokens 42/42, audio/image/video 0/42. NULL o nguon app: '
    'nhat ky Ralli khong ghi loai phan hoi. Data Out so 15.';

COMMENT ON COLUMN fact_call.thinking_enabled IS
    'true = luot goi nay co sinh token suy luan (reasoning). Suy tu '
    'completion_tokens_details.reasoning_tokens > 0. Do 02/09/2026: 2/42 luot, '
    'ca hai la gemini-3.6-flash voi reasoning_tokens = 342 - chinh hai luot '
    'nghiem thu cache toi 01/09. '
    'KIEU KHAC fact_monitoring: o do cot cung ten la TEXT (chuoi ''true''/'
    '''false'', 11.440/3.589, NULL 636.624) vi do la bang ha canh cua nhan '
    'Google gui sang. Bang nay la cua TA nen dung BOOLEAN that. Moi phep so '
    'sanh giua hai bang PHAI dich kieu tuong minh. '
    'NULL = khong co thong tin, KHONG phai "khong bat thinking" - nguon app luon '
    'NULL. Data Out so 14.';


-- =====================================================================
-- (2) fact_latency_daily + fact_perf_daily: cot `source`
-- =====================================================================
--
-- VI SAO PHAI LAM TRUOC KHI DO SO GATEWAY VAO
-- -------------------------------------------
-- Hai bang nay dung sinh ra cho RIENG nguon monitoring:
--     fact_perf_daily     tu fact_monitoring, phep do api/request_count
--     fact_latency_daily  tu histogram Cloud Monitoring, gop tay boi
--                         scripts/merge_latency_daily.py
--
-- Hai phep do KHAC HAN BAN CHAT:
--     monitoring   p95 NOI SUY trong o rong 33,55 - 67,11 giay
--     gateway      p95 CHINH XAC tu tung gia tri duration_ms tho
--
-- Hai con so cung ten, cung cot, khac han do tin cay. Khong co `source` thi
-- khong ai phan biet duoc, va nguoi doc sau se so chung nhu the cung loai.
--
-- DEFAULT 'monitoring' LA DUNG NGHIA, KHONG PHAI BIA
-- --------------------------------------------------
-- Khac han `outcome` o migration 006, noi mot DEFAULT se la bia dat. O day
-- 339 dong fact_latency_daily va 669 dong fact_perf_daily hien co THAT SU den
-- tu monitoring - do la toan bo noi dung hai bang cho toi hom nay.
--
-- `source` VAO KHOA CHINH, khong chi la mot cot them. Thieu no thi dong gateway
-- dung khoa voi dong monitoring cua cung mot ngay: hoac INSERT hong, hoac -
-- te hon - `DO UPDATE` ghi de len nhau va mat mot nguon ma tong van "khop".

ALTER TABLE fact_latency_daily
    ADD COLUMN source TEXT NOT NULL DEFAULT 'monitoring';

ALTER TABLE fact_latency_daily
    DROP CONSTRAINT fact_latency_daily_pkey;

ALTER TABLE fact_latency_daily
    ADD PRIMARY KEY (day, agent_id, source);

ALTER TABLE fact_latency_daily
    ADD CONSTRAINT fact_latency_daily_source_fkey
    FOREIGN KEY (source) REFERENCES ref_source(source);

COMMENT ON COLUMN fact_latency_daily.source IS
    'Nguon cua phan vi tren dong nay. DEFAULT ''monitoring'' cho 339 dong cu, '
    'va do la dung nghia chu khong phai bia: toan bo noi dung bang nay truoc '
    '008 deu dung tu histogram Cloud Monitoring. '
    'DOC CUNG p95_bucket_from/to DE BIET DO TIN CAY: nguon co hai cot do la '
    'phan vi NOI SUY trong mot o histogram (do 03/09: be rong o trung binh bang '
    '54-67% chinh gia tri p95); nguon de chung NULL la phan vi tinh THANG tu '
    'gia tri tho, khong co sai so noi suy nao. '
    'MOI NGUON MOT DONG. Muon MOT con so duy nhat thi phai CHON, khong duoc '
    'trung binh - trung binh cua hai phan vi la mot con so khong thuoc ve phep '
    'do nao.';

ALTER TABLE fact_perf_daily
    ADD COLUMN source TEXT NOT NULL DEFAULT 'monitoring';

ALTER TABLE fact_perf_daily
    DROP CONSTRAINT fact_perf_daily_pkey;

ALTER TABLE fact_perf_daily
    ADD PRIMARY KEY (day, agent_id, method, response_code, source);

ALTER TABLE fact_perf_daily
    ADD CONSTRAINT fact_perf_daily_source_fkey
    FOREIGN KEY (source) REFERENCES ref_source(source);

COMMENT ON COLUMN fact_perf_daily.source IS
    'Nguon cua so luot theo ma tra ve tren dong nay. DEFAULT ''monitoring'' cho '
    '669 dong cu - dung nghia, chung dung tu fact_monitoring. '
    'Hai nguon dem HAI THU khac nhau du cung ten cot: monitoring dem qua '
    'serviceruntime/api/request_count (da loc service = generativelanguage), '
    'gateway dem tung luot trong so LiteLLM. Cong hai nguon lai la dem hai lan '
    'cung mot luu luong.';


-- =====================================================================
-- (3) fact_usage_hourly - bang tong hop theo GIO
-- =====================================================================
--
-- BANG RIENG, KHONG THEM COT `hour` VAO fact_usage_daily
-- ------------------------------------------------------
-- Hai ly do. Mot: khoa chinh cua bang ngay dang duoc 10 cho dau doc dua vao.
-- Hai: mot bang ma hai do min nam chung thi MOI phep SUM deu phai nho loc - dung
-- hinh dang loi `source` hoi 31/08, noi thieu mot dieu kien WHERE lam luu luong
-- Gateway bi dem thanh cua app ma tong van khop.
--
-- KHOA DU NAM CHIEU NHU BANG NGAY, chi doi `day` -> `hour`. KHONG rut bot chieu
-- de tiet kiem dong: rut chieu la mat kha nang cat lat, ma cai tiet kiem duoc
-- thi khong dang. Do uoc luong 02/09 cho he so 3,8-6,9 lan so voi bang ngay,
-- tuc vai nghin dong - cung bac voi fact_billing_daily (2.575), la bang tong
-- hop lon nhat hien co.
--
-- KHONG CO NGUON `billing` - VA DO LA GIOI HAN CUA NHA CUNG CAP
-- -------------------------------------------------------------
-- Hoa don Google tinh theo NGAY. Khong co cach nao vuot.
--
-- Cach sai ma de chon: chia deu tien cua mot ngay cho 24 gio. No cho ra mot bieu
-- do dep va mot con so BIA - moi gio mang mot phan tien ma nha cung cap chua bao
-- gio noi la cua gio do. Cung loai loi voi viec trung binh cac p95 de ra p95 cua
-- ngay, da ghi o db/build_performance.py.
--
-- Nguoi doc biet `billing` vang mat bang cach TRUY VAN cot `source`, khong phai
-- bang mot dong chu thich tren giao dien. Du lieu tu noi.
--
-- `hour` LA TIMESTAMP DA CAT VE DAU GIO, GIO VIET NAM
-- ---------------------------------------------------
-- Dung TIMESTAMP chu khong phai (date, int): mot cot thi moi phep so sanh
-- khoang thoi gian la mot phep so sanh, khong phai hai. Quy uoc gio Viet Nam
-- giu nguyen nhu moi cot ngay khac (chot 14/08).

CREATE TABLE fact_usage_hourly (
    hour          TIMESTAMP NOT NULL,   -- da cat ve dau gio, GIO VIET NAM
    agent_id      INT NOT NULL REFERENCES dim_agent,
    model_id      INT NOT NULL REFERENCES dim_model,
    account_id    INT NOT NULL REFERENCES account,
    calls         INT,
    total_tokens  BIGINT,
    input_tokens  BIGINT,
    output_tokens BIGINT,
    cached_tokens BIGINT,
    cost_usd      NUMERIC(14,6),
    source        TEXT NOT NULL REFERENCES ref_source,
    PRIMARY KEY (hour, agent_id, model_id, account_id, source)
);

COMMENT ON TABLE fact_usage_hourly IS
    'Luu luong tong hop theo GIO. Cung nam chieu khoa nhu fact_usage_daily, chi '
    'doi `day` thanh `hour`. '
    'CHI CHUA CAC NGUON GHI DUOC THOI DIEM TUNG LUOT: app va gateway (qua '
    'fact_call.ts_local), monitoring (qua fact_monitoring.ts_local). '
    'KHONG CO `billing`, va do KHONG phai thieu sot: hoa don Google chi tinh '
    'theo ngay, nen moi con so tien theo gio deu la bia. Hoi cot `source` de '
    'biet nguon nao co mat, dung gia dinh bang nay phu het luu luong. '
    'TONG THEO GIO CUA MOT NGAY PHAI BANG TONG THEO NGAY cua CUNG mot nguon - '
    'scripts/audit_db.py co phep kiem cho dieu do.';

COMMENT ON COLUMN fact_usage_hourly.hour IS
    'Dau gio, GIO VIET NAM (quy uoc 14/08: moi cot thoi gian la gio VN, khong '
    'quy doi mui gio o bat ky dau). Vi du 2026-08-31 18:00:00 gom moi luot tu '
    '18:00:00 den 18:59:59.';

COMMENT ON COLUMN fact_usage_hourly.cost_usd IS
    'Tien theo gio. CHI nguon `gateway` co gia tri o day, va do la tien LiteLLM '
    'TU NHAN tu bang gia noi bo - khong phai hoa don. Nguon app va monitoring '
    'luon NULL. Vi `billing` khong co mat trong bang nay, cot nay KHONG BAO GIO '
    'chua tien da xac nhan - dung cong no len va goi la chi phi.';

COMMENT ON COLUMN fact_usage_hourly.cached_tokens IS
    'NULL o nguon monitoring: Cloud Monitoring khong co phep do nao cho token '
    'cache (da kiem, 13 phep do khong cai nao kind=''cached''). NULL nghia la '
    'KHONG DO, khac han 0 nghia la do duoc va bang khong.';
