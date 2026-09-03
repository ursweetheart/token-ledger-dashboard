-- 009 - CHIEU ACCOUNT phu DU CA 8 AGENT, khong chi 2.
--
-- CAU HOI MA VIEW NAY TRA LOI
-- ---------------------------
--     "Ngay A, agent nay hoat dong the nao, va quy ve TAI KHOAN nao?"
--
-- View cu `usage_by_account` chi tra loi duoc cho 2/8 agent. Do 03/09/2026:
--
--     337 dong · 2 AGENT · 53 account · 108.554.843 token · 14/03 -> 29/08
--
-- VI SAO KHONG SUA VIEW CU (da DO ca hai duong, ca hai deu hong)
-- --------------------------------------------------------------
-- View cu co HAI dieu kien:  source IN (... knows_user)  AND  kind = 'real'
--
--   (1) Noi `kind` -> kind IN ('real','service_account')
--       338 dong · 3 AGENT · 54 account      <- chi THEM MOT agent
--       Vi `knows_user` van chan:
--           service_account · billing     knows_user=f  741.641.736 token  CHAN
--           service_account · monitoring  knows_user=f  485.267.016 token  CHAN
--           service_account · gateway     knows_user=t       45.187 token  lot
--       Chi DMS lot, vi no la agent duy nhat da di qua Gateway.
--
--   (2) Bo LUON `knows_user`
--       1.903 dong · 8 agent · 1.335.508.782 token
--       tong chuan (usage_resolved):           915.969.971
--                                              -> PHONG 145,8%
--       Vi `fact_usage_daily` de BON NGUON CANH NHAU, khong chong len nhau.
--       Mot agent dich vu co token o CA billing LAN monitoring; cong thang la
--       dem hai lan cung mot luu luong qua hai cai cong to.
--       (Bay nay da ghi o backend/store.py:455, kem so do cu: 1.248.600.872 /
--        867.657.110 = 143,9%, va "phan con lai" ra -43,9%.)
--
-- Dieu kien `knows_user` hien tai AN TOAN MOT CACH TINH CO: no loc con dung
-- MOT nguon (`app`) nen khong co gi de dem hai lan. Noi no ra la mat luon su
-- an toan tinh co do.
--
-- CACH DUNG: JOIN VOI NGUON DA DUOC CHON
-- --------------------------------------
-- `usage_resolved` khoa theo (day, agent_id, model_id) va KHONG mang account_id
-- - vi COALESCE dien ra o muc do. Nhung no NOI RA no da chon nguon nao qua hai
-- cot `token_source` / `call_source`. Lay dung nguon ay quay lai
-- `fact_usage_daily` la co chieu account, khong dem hai lan.
--
-- PHAI JOIN HAI LAN, KHONG PHAI MOT
-- ---------------------------------
-- Do that: JOIN chi theo `token_source` cho TOKEN khop TUYET DOI (lech 0) trong
-- khi CALLS hut 77,9% (27.056 / 122.504). Chi nghiem thu token thi mot loi 78%
-- van bao DAT - va do la loi da xay ra that trong luc thiet ke change nay.
--
-- Nguyen nhan: `usage_resolved` chon nguon THEO TUNG CHI TIEU, va `billing`
-- KHONG CO cot `calls`:
--
--     token_source | call_source | dong |    token    | calls
--     -------------+-------------+------+-------------+--------
--     billing      | monitoring  |  524 | 472.161.741 | 93.062   <- lech o day
--     billing      |   (khong)   |  488 | 279.027.663 |      -
--     app          | app         |  181 | 107.125.668 | 11.176
--     monitoring   | monitoring  |   71 |  57.609.712 | 15.842
--       (khong)    | monitoring  |   11 |           - |  2.386   <- CHI co calls
--     gateway      | gateway     |    1 |      45.187 |     38
--
-- VI SAO `FULL OUTER` CHU KHONG `LEFT`
-- ------------------------------------
-- 11 dong o hang ap chot CHI co calls, khong co nhanh token (agent 1, 29/04 ->
-- 28/08, 2.386 luot). `LEFT JOIN` tu phia token vut chung di ma TONG TOKEN VAN
-- KHOP - dung loai loi im lang ma view nay sinh ra de tranh.
--
-- KET QUA DO DUOC (03/09/2026)
-- ----------------------------
--     1.453 dong · 8/8 AGENT · 60 account
--     token   915.969.971 = 915.969.971   DAT
--     calls       122.504 =     122.504   DAT
--
--     service_account  1.046 dong · 6 agent ·  6 account · 793.613.395 · 86,6%
--     real               324 dong · 2 agent · 52 account · 102.905.141 · 11,2%
--     whole_agent         38 dong · 1 agent ·  1 account ·  15.230.908 ·  1,7%
--     unattributed        34 dong · 1 agent ·  1 account ·   4.220.527 ·  0,5%
--
-- GIU CA `whole_agent` VA `unattributed`, KHONG LOC
-- ------------------------------------------------
-- Chung la 2,2% ma ta THAT SU khong quy duoc ve mot account nao. Loc di la noi
-- doi rang do phu bang 100%. Cung ly le da dung cho `unit_conflict`: giu lai dau
-- vet cho ta da chon ho, thay vi de viec chon dien ra am tham.
--
-- View nay KHONG co `cost_usd`, va do la co y: tien chi ton tai o muc
-- (ngay, agent, model) chu khong o muc tai khoan. Them mot cot tien chia deu cho
-- cac tai khoan la bia ra mot con so khong nguon nao tung bao cao.


CREATE VIEW usage_by_account_resolved AS
WITH t AS (
    -- Nhanh TOKEN: lay dung nguon ma usage_resolved da chon cho token.
    SELECT f.day, f.agent_id, f.model_id, f.account_id,
           f.total_tokens, f.input_tokens, f.output_tokens, f.cached_tokens,
           f.source AS token_source
    FROM fact_usage_daily f
    JOIN usage_resolved v
      ON v.day = f.day AND v.agent_id = f.agent_id AND v.model_id = f.model_id
     AND f.source = v.token_source
),
c AS (
    -- Nhanh CALLS: nguon KHAC, vi billing khong co cot calls.
    SELECT f.day, f.agent_id, f.model_id, f.account_id,
           f.calls, f.source AS call_source
    FROM fact_usage_daily f
    JOIN usage_resolved v
      ON v.day = f.day AND v.agent_id = f.agent_id AND v.model_id = f.model_id
     AND f.source = v.call_source
),
gop AS (
    SELECT COALESCE(t.day, c.day)               AS day,
           COALESCE(t.agent_id, c.agent_id)     AS agent_id,
           COALESCE(t.model_id, c.model_id)     AS model_id,
           COALESCE(t.account_id, c.account_id) AS account_id,
           c.calls,
           t.total_tokens, t.input_tokens, t.output_tokens, t.cached_tokens,
           t.token_source, c.call_source
    FROM t
    FULL OUTER JOIN c
      ON c.day = t.day AND c.agent_id = t.agent_id
     AND c.model_id = t.model_id AND c.account_id = t.account_id
)
SELECT g.day, g.agent_id, g.model_id, g.account_id,
       a.username, a.full_name, a.email,
       a.kind,                      -- 'real' | 'service_account'
                                    -- 'whole_agent' | 'unattributed'
       a.unit_id, u.path AS unit_path, a.unit_conflict, a.is_shared,
       g.calls, g.total_tokens, g.input_tokens, g.output_tokens, g.cached_tokens,
       g.token_source, g.call_source
FROM gop g
JOIN account a  ON a.account_id = g.account_id
JOIN dim_unit u ON u.unit_id = a.unit_id;


COMMENT ON VIEW usage_by_account_resolved IS
    'Chieu TAI KHOAN cho CA 8 AGENT. Dung view nay, khong dung `usage_by_account`. '
    'Dung tren `usage_resolved` nen KHONG dem hai lan; JOIN HAI LAN vi '
    '`usage_resolved` chon nguon theo TUNG CHI TIEU va `billing` khong co cot '
    '`calls` - JOIN mot lan theo token_source lam CALLS hut 77,9% trong khi TOKEN '
    'khop tuyet doi. '
    'NGHIEM THU PHAI LA HAI CON SO: SUM(total_tokens) va SUM(calls) deu phai bang '
    '`usage_resolved`. Kiem mot con so thi mot loi 78% van bao DAT. '
    'GIU ca kind=''whole_agent'' va kind=''unattributed'' (2,2% luu luong) - do la '
    'phan THAT SU khong quy duoc ve tai khoan nao, loc di la noi doi rang do phu '
    'bang 100%. '
    'KHONG co `cost_usd`: tien chi ton tai o muc (ngay, agent, model). Chia deu cho '
    'cac tai khoan la bia ra mot con so khong nguon nao tung bao cao.';


COMMENT ON VIEW usage_by_account IS
    'BANG NGUOI DUNG - chi phu 2/8 agent (337 dong · 53 account, do 03/09/2026). '
    'Dieu kien `kind = ''real''` tra loi cau "co phai mot CON NGUOI khong"; dieu '
    'kien `source IN (... knows_user)` loc con dung nguon `app`. '
    'DUNG VIEW NAY khi cau hoi la ve NGUOI THAT. '
    'HOI `usage_by_account_resolved` khi cau hoi la "quy ve TAI KHOAN nao" - no phu '
    'ca 8 agent, ke ca 6 agent chay bang mot tai khoan dich vu. '
    'GIU LAI view nay: tools/baseline_db.py va tools/dien_tap_gateway.py doc no lam '
    'moc lich su, doi no la moi so mo cu khong so lai duoc.';
