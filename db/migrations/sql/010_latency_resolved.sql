-- 010 - MOT con so do tre cho moi (ngay, agent), CHON chu khong TRUNG BINH.
--
-- CAU HOI MA VIEW NAY TRA LOI
-- ---------------------------
--     "Ngay A, agent nay cham bao nhieu?"  -> MOT con so, khong phai hai.
--
-- Tu migration 008, `fact_latency_daily` co the co HAI dong cho cung mot
-- (ngay, agent): mot cua `monitoring`, mot cua `gateway`. Do la dung o tang du
-- lieu - moi nguon giu phep do cua no. Nhung tang doc thi chua chiu noi:
--
--     web/js/api.js:187   d.lat = x.p95_seconds || 0;   <- GAN DE
--                         khoa la `day|agent_id`, KHONG co `source`
--     backend/store.py    ORDER BY day, agent_id        <- KHONG co tie-break
--
-- Hai dong cho cung mot khoa thi dong den SAU thang, va khong ai biet la dong
-- nao. Khong crash, khong nhan doi - chi la mot con so KHONG XAC DINH.
--
-- TUYET DOI KHONG TRUNG BINH HAI PHAN VI
-- --------------------------------------
-- Phan vi khong cong duoc. Chinh du an nay da do: trung binh cua p95=2,1s (tren
-- 100 luot) va p95=8,4s (tren 2 luot) ra 5,25s, trong khi so that ~2,3s. Xem
-- docstring dau db/build_performance.py.
--
-- Nen view nay CHON MOT NGUON cho moi khoa, va lay TAT CA cot tu dung nguon do -
-- khong COALESCE rieng tung cot. Tron p50 cua nguon nay voi p95 cua nguon kia se
-- ra mot cap so khong nguon nao tung bao cao. Cung ly le voi `usage_resolved`.
--
-- ==========================================================================
-- THU TU UU TIEN: `monitoring` TRUOC `gateway` - VA DAY LA LUA CHON TAM
-- ==========================================================================
--
-- DAY LA DIEU DUY NHAT TRONG CHANGE NAY CHUA CO CO SO DO DAC.
--
-- Do 03/09/2026 tren CUNG agent 6:
--
--     thu cong (histogram Google)   p95 TB 58,206 s   p50 TB 19,66 s   681 mau
--     gateway  (duration_ms tho)    p95     1,822 s   p50     0,788 s    38 mau
--                                         ^ lech 31,9 lan     ^ lech 24,9 lan
--
-- Ba phep do da LOAI TRU cac giai thich de dai:
--   (a) KHONG phai o histogram rong: 38 luot Gateway min 609 ms, max 3.136 ms,
--       tren 10 giay 0 luot, tren 33,55 giay 0 luot.
--   (b) KHONG phai mau it: thu cong TB 45,4 luot/ngay (11-145) vs gateway 38.
--   (c) p50 CUNG lech, ma p50 it chiu sai so o hon nhieu.
--
-- O cuoi CO bao hoa that, nhung chi o vai agent: agent 6 la 86,7% so ngay, agent
-- 7 la 64,0%, nhung agent 1 chi 3,2% va agent 2 la 0,0%. Khong giai thich duoc
-- toan bo.
--
-- Va KHONG NGAY NAO CHONG LAN: thu cong dung 29/08, gateway bat dau 31/08. Nen
-- chua nguon nao kiem chung duoc nguon kia.
--
-- HAI GIA THUYET CON SONG:
--   (i)  hai nguon do hai DIEM khac nhau trong duong goi
--   (ii) 38 luot ngay 31/08 la luu luong THU ngan, khong phai luu luong DMS san xuat
--
-- LY LE CHON `monitoring` TRUOC - ve RUI RO BAT DOI XUNG, khong ve do chinh xac:
--
--     monitoring truoc  ->  dashboard KHONG doi mot con so nao hom nay.
--                           Gateway chi dien vao NGAY ma monitoring khong co.
--                           Sai lam nay khong ai nhin thay.
--
--     gateway truoc     ->  p95 cua DMS roi tu ~58 s xuong ~1,8 s.
--                           Nguoi xem thay he thong nhanh len 31,9 LAN sau mot
--                           dem. Sai lam nay AI CUNG nhin thay, va no trong y
--                           nhu that.
--
-- Chon huong ma sai lam RE HON, cho toi khi co so.
--
-- CHO NAY DI NGUOC `usage_resolved`, VA DO LA CO CHU Y. View kia cho `gateway`
-- dung truoc billing ve TOKEN, vi Gateway la bo dem cua chinh ta va co mat ngay
-- trong ngay. Ly le do dung cho TOKEN - hai nguon dem CUNG mot thu. Voi DO TRE
-- thi chua chung minh duoc la chung do cung mot thu. Cung mot ten "nguon" khong
-- bao dam cung mot phep do.
--
-- PHEP DO SE TRA LOI: mot buoi chay DMS qua Gateway TRONG NGAY ma Cloud
-- Monitoring dang ghi. Khi co ngay giao nhau, doi DUNG MOT DONG `CASE` duoi day.

CREATE VIEW latency_resolved AS
WITH keys AS (
    SELECT DISTINCT day, agent_id FROM fact_latency_daily
),
m AS (SELECT * FROM fact_latency_daily WHERE source = 'monitoring'),
g AS (SELECT * FROM fact_latency_daily WHERE source = 'gateway')
SELECT k.day,
       k.agent_id,
       -- ===== MOT DONG DUY NHAT QUYET DINH THU TU UU TIEN =====
       -- Doi `m.day IS NOT NULL` thanh `g.day IS NOT NULL` (va dao hai ve cua
       -- MOI CASE duoi day) la dao chieu uu tien. Khong cho nao khac phai sua.
       CASE WHEN m.day IS NOT NULL THEN 'monitoring' ELSE 'gateway' END
                                                        AS latency_source,
       -- MOI cot lay tu CUNG mot nguon voi `latency_source`. Khong COALESCE
       -- rieng tung cot: tron p50 cua nguon nay voi p95 cua nguon kia se ra mot
       -- cap so khong nguon nao tung bao cao.
       CASE WHEN m.day IS NOT NULL THEN m.samples
            ELSE g.samples         END                   AS samples,
       CASE WHEN m.day IS NOT NULL THEN m.p50_seconds
            ELSE g.p50_seconds     END                   AS p50_seconds,
       CASE WHEN m.day IS NOT NULL THEN m.p95_seconds
            ELSE g.p95_seconds     END                   AS p95_seconds,
       -- Hai cot o histogram VAN CHAY QUA VIEW du man hinh khong dung. Chung mo
       -- ta SAI SO cua phep noi suy, va phep kiem `p95 nam trong chinh o cua no`
       -- (scripts/audit_db.py) doc chung. Cat o day la lam gay mot phep kiem
       -- dang dat. Nguon `gateway` de NULL - so tho khong co sai so noi suy.
       CASE WHEN m.day IS NOT NULL THEN m.p95_bucket_from
            ELSE g.p95_bucket_from END                   AS p95_bucket_from,
       CASE WHEN m.day IS NOT NULL THEN m.p95_bucket_to
            ELSE g.p95_bucket_to   END                   AS p95_bucket_to,
       CASE WHEN m.day IS NOT NULL THEN m.p99_seconds
            ELSE g.p99_seconds     END                   AS p99_seconds,
       CASE WHEN m.day IS NOT NULL THEN m.enough_samples
            ELSE g.enough_samples  END                   AS enough_samples
FROM keys k
LEFT JOIN m ON m.day = k.day AND m.agent_id = k.agent_id
LEFT JOIN g ON g.day = k.day AND g.agent_id = k.agent_id;


COMMENT ON VIEW latency_resolved IS
    'MOT con so do tre cho moi (ngay, agent). CHON mot nguon, KHONG trung binh - '
    'phan vi khong cong duoc, trung binh hai phan vi ra mot con so khong thuoc ve '
    'phep do nao. '
    'DOC VIEW NAY, dung doc thang fact_latency_daily: tu migration 008 bang do co '
    'the co HAI dong cho cung mot khoa, ma tang doc (api.js:187 gan de tren khoa '
    '`day|agent_id`) khong phan biet duoc - dong den sau thang, va khong ai biet la '
    'dong nao. '
    'THU TU UU TIEN HIEN TAI: monitoring truoc gateway, VA DAY LA LUA CHON TAM. '
    'Ly do la RUI RO BAT DOI XUNG chu khong phai do chinh xac: chon monitoring thi '
    'dashboard khong doi con so nao hom nay; chon gateway thi p95 cua DMS roi tu '
    '~58 s xuong ~1,8 s va nguoi xem thay he thong nhanh len 31,9 lan sau mot dem. '
    'Hai nguon lech 31,9 lan tren cung agent 6 va CHUA NGAY NAO CHONG LAN de kiem '
    'chung lan nhau. Phep do se tra loi: mot buoi chay DMS qua Gateway trong ngay '
    'ma Cloud Monitoring dang ghi. '
    'Cot `latency_source` phuc vu PHEP KIEM, khong len toi man hinh - dashboard hien '
    'mot con so tran.';
