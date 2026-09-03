-- 006 - `fact_call` ghi them DO TRE, KET CUC va MA LOI cua tung luot goi.
--
-- VI SAO
-- ------
-- Master Plan muc "Ghi du truong can cho dashboard ngay tai thoi diem goi"
-- (moc 21/09/2026) doi ban ghi moi request gom 12 truong. Dem tren fact_call
-- ngay 31/08: co 10, thieu DO TRE va MA TRA VE.
--
-- Ca hai deu DA CO trong so Gateway, chi thieu duong nap:
--     request_duration_ms                     45/45 dong co gia tri
--     metadata.error_information.error_code    5/5 dong hong co truong
--
-- DO TRE DANG GIA HON VE NGOAI
-- ----------------------------
-- db/build_performance.py ghi lai mot gioi han VE MAT CAU TRUC cua nguon
-- monitoring: "fact_monitoring CO cot p95 nhung do la p95 CUA TUNG PHUT. Trung
-- binh cac p95 khong ra p95 cua ngay". Dashboard hien phai lay phan vi tu mot
-- file histogram gop tay.
--
-- Gateway co do tre THO cua tung luot goi, nen tinh duoc phan vi CHINH XAC.
-- Do 31/08 tren 40 luot thanh cong: 609 - 3.136 ms, trung binh 1.002, p95 1.805.
--
-- BA COT, TAT CA NULLABLE VA KHONG DEFAULT
-- ----------------------------------------
-- `outcome` KHONG dat DEFAULT 'success' cho 8.631 dong cu cua Ralli: nhat ky cua
-- app KHONG ghi ket cuc, nen gan 'success' la BIA. Khac voi `source` o migration
-- 004, noi DEFAULT 'app' la dung nghia vi moi dong cu that su la cua app.
--
-- Tu PostgreSQL 11, ADD COLUMN nullable khong DEFAULT chi ghi vao sieu du lieu,
-- khong viet lai bang. Nang luc nay da dien tap o migration 002/003.
--
-- `error_code` la TEXT chu khong phai INTEGER: do 5 dong hong thay ba dong mang
-- CHUOI RONG, khong ep sang so duoc. Va LiteLLM dat truong nay tu nhieu nguon
-- khac nhau (ProxyException, loi cua nha cung cap, loi mang) nen khong co gi bao
-- dam no luon la so.

ALTER TABLE fact_call
    ADD COLUMN duration_ms INTEGER;

ALTER TABLE fact_call
    ADD COLUMN outcome TEXT;

ALTER TABLE fact_call
    ADD COLUMN error_code TEXT;

COMMENT ON COLUMN fact_call.duration_ms IS
    'Do tre cua luot goi, mili giay, so THO tu Gateway. NULL = khong do duoc. '
    'Do 31/08/2026: Gateway ghi 0 cho MOI luot hong, KE CA luot da goi toi nha '
    'cung cap va bi tu choi - nen 0 khong phai mot phep do, va bo nap quy no ve '
    'NULL. Nap 0 vao la keo tut moi phan vi.';
COMMENT ON COLUMN fact_call.outcome IS
    'success / failure, chep tu `status` cua LiteLLM_SpendLogs. NULL o nguon app '
    'vi nhat ky Ralli KHONG ghi ket cuc - khong biet, chu khong phai thanh cong. '
    'MOI phep tong hop luu luong va chi phi PHAI loc cot nay.';
COMMENT ON COLUMN fact_call.error_code IS
    'Ma loi khi hong, tu metadata.error_information.error_code. TEXT vi gia tri '
    'khong bao dam la so. Chuoi rong quy ve NULL. NULL cung co nghia la luot goi '
    'thanh cong.';
