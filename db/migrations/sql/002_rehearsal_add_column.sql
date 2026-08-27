-- 002 - DIEN TAP, khong mang gia tri nghiep vu.
--
-- Task 8.6 cua change `change-the-schema-without-dropping-it` doi mot bang chung
-- rang schema doi duoc TAI CHO tren database dang co du lieu that, ma khong mat
-- mot token nao. Truoc migration, du an KHONG lam duoc dieu do: doi schema nghia
-- la sua 01_schema.sql roi dung lai tu dau.
--
-- Chon `fact_usage_daily` chu khong phai mot bang nho ben le, vi day la bang su
-- kien trung tam - 1.845 dong, nguon cua view `usage_resolved`. Neu ALTER lam
-- hong cai gi thi no hong o day.
--
-- Cot NULLABLE va KHONG co DEFAULT: PostgreSQL 11+ ghi vao sieu du lieu, khong
-- viet lai bang. Voi 583.917 dong o fact_monitoring thi khac biet do la giay so
-- voi phut - nhung o day chon bang 1.845 dong nen dieu do khong quyet dinh.
--
-- Ba view deu liet ke cot tuong minh, khong dung SELECT *, nen them cot khong
-- lam doi dinh nghia view. Da kiem truoc khi viet file nay.
--
-- Migration 003 go cot nay ra bang mot buoc TIEN. Khong co downgrade.

ALTER TABLE fact_usage_daily
    ADD COLUMN rehearsal_marker TEXT;

COMMENT ON COLUMN fact_usage_daily.rehearsal_marker IS
    'Dien tap task 8.6 ngay 26/08/2026. Go ra o migration 003. Khong dung vao viec gi.';
