-- 012 - NHIP TIM cua duong nap. De phan biet "khong co luu luong" voi "duong nap
-- da chet". KHONG phai mot nguon du lieu.
--
-- CAU HOI MA BANG NAY TRA LOI
-- ---------------------------
--     "Lan cuoi duong nap cua nguon nay chay THANH CONG la khi nao?"
--
-- Nghe nho, nhung khong cau nao trong `token_ledger_v2` tra loi duoc no truoc khi
-- co bang nay -- va thieu cau tra loi do thi HAI trang thai duoi day trong Y HET
-- NHAU tu phia dashboard:
--
--     dong gateway moi nhat cach day 3 tieng, vi KHONG AI GOI trong 3 tieng
--     dong gateway moi nhat cach day 3 tieng, vi DUONG NAP DA CHET 3 tieng
--
-- Cai thu nhat la binh thuong. Cai thu hai la su co. Doan mo ho nay chinh la thu
-- change `let-the-gateway-ledger-arrive-by-itself` di bit.
--
-- VI SAO CAN, DO DUOC 09/09/2026
-- ------------------------------
-- Truoc khi co dich vu `ledger-refresh`, so dashboard chi doi khi CO NGUOI chay
-- `scripts/refresh_gateway.py`. Do luc do:
--
--     LiteLLM_SpendLogs                 444 dong, moi nhat 08/09 23:55
--     fact_call WHERE source='gateway'   41 dong, moi nhat 31/08 10:17
--     -> tre 8 ngay 13 gio 38 phut, va KHONG mot dau hieu nao bao la dang tre
--
-- `scripts/audit_db.py` nhom J bat duoc chuyen do -- nhung CHI KHI co nguoi chay
-- audit, va CHI KHI so nguon co dong moi. Nhip tim thi khong phu thuoc ca hai
-- dieu kien ay: no gia di theo dong ho, ke ca khi khong ai goi mot luot nao.
--
-- BANG NAY KHONG PHAI MOT NGUON DU LIEU
-- -------------------------------------
-- `usage_resolved` KHONG doc no va khong bao gio duoc doc. No khong mang token,
-- khong mang tien, khong mang mot luot goi nao. Cung y do voi
-- `fact_provider_daily`: mot bang de DOI CHIEU, khong de CONG VAO.

CREATE TABLE IF NOT EXISTS ref_load_run (
    -- Khoa ngoai sang `ref_source` chu khong phai TEXT tu do: nhip tim cua mot
    -- nguon KHONG TON TAI la mot dong rac khong ai phat hien duoc.
    source           TEXT PRIMARY KEY REFERENCES ref_source(source),

    -- GIO VIET NAM, cung quy uoc voi `fact_call.ts_local` va toan bo du an
    -- (chot 14/08/2026: moi ngay la gio VN).
    --
    -- Ben ghi PHAI dung `now() AT TIME ZONE 'Asia/Ho_Chi_Minh'` -- lay dong ho
    -- cua DATABASE, khong lay dong ho cua container. Container co the chay UTC
    -- (postgres o day chay UTC, do 09/09/2026), va neu ben ghi dung gio VN con
    -- ben doc dung gio container thi tuoi nhip tim lech DUNG 7 GIO -- nghia la
    -- mot nhip tim vua ghi trong nhu da chet 7 tieng, hoac nguoc lai.
    last_success_at  TIMESTAMP NOT NULL,

    -- So dong cua nguon nay trong `fact_call` NGAY SAU luot do. Khong dung de
    -- tinh toan gi; de doc log nguoc: "luot 03:02 ket thuc voi 366 dong".
    rows_after       BIGINT,

    -- Ai ghi dong nay. Duong nap nhanh va duong dung lai toan bo la HAI duong
    -- khac nhau, va biet duong nao vua chay la thong tin can khi chan doan.
    written_by       TEXT,

    -- NHIP ma tien trinh ghi dong nay DANG chay, tinh bang giay. NULL neu no
    -- chay mot lan roi thoat (khong phai che do vong lap).
    --
    -- VI SAO NAM O DAY chu khong doc tu bien moi truong: nguong cua phep kiem do
    -- tre duoc suy TU nhip, va bien moi truong thi MOI TIEN TRINH THAY MOT GIA
    -- TRI KHAC. Dat REFRESH_EVERY_SECONDS=300 trong .env thi dich vu chay 300s,
    -- nhung nguoi chay `python scripts/audit_db.py` trong mot shell khong co bien
    -- do se lay mac dinh 120 -> nguong 420s thay vi 960s -> BAO DONG GIA. Dung
    -- loai bao dong gia ma change nay di diet.
    --
    -- Ghi vao day thi chi co MOT nguon su that: nhip ma tien trinh THUC SU dang
    -- chay. Moi ben doc deu suy nguong tu no.
    every_seconds    BIGINT
);

COMMENT ON TABLE ref_load_run IS
    'Nhip tim cua duong nap: lan cuoi mot nguon duoc lam moi THANH CONG. Chi de doi chieu do tre - usage_resolved KHONG doc bang nay.';

COMMENT ON COLUMN ref_load_run.last_success_at IS
    'Gio VIET NAM. Ben ghi phai dung now() AT TIME ZONE ''Asia/Ho_Chi_Minh'' -- dong ho cua database, khong phai cua container.';
