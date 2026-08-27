-- 003 - GO cot dien tap ra, bang mot buoc TIEN.
--
-- Day moi la nua sau cua bang chung task 8.6. Migration 002 chung minh THEM duoc;
-- file nay chung minh GO duoc - va quan trong hon, go bang cach di TOI chu khong
-- di lui.
--
-- VI SAO KHONG DUNG `alembic downgrade`
-- Task 3.4 da chot forward-only, va `downgrade()` cua moi revision trong du an nay
-- deu nem NotImplementedError. Ly do ghi o 001_baseline_baseline.py: migration lui
-- thuong duoc viet ma khong bao gio chay, nen den luc can thi no sai. Voi doi ba
-- nguoi thi ban luu truoc khi chay re hon va that hon.
--
-- He qua: moi database trong du an - may anh Tuan, may dong nghiep, may chu sau
-- nay - deu di qua dung mot chuoi 001 -> 002 -> 003. Khong ban nao lui, nen khong
-- ban nao lech.
--
-- Sau file nay, `fact_usage_daily` tro lai dung 11 cot nhu truoc 26/08/2026.

ALTER TABLE fact_usage_daily
    DROP COLUMN rehearsal_marker;
