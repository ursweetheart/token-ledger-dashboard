-- 005 - `usage_resolved.cost_usd` nhan them tien cua Gateway.
--
-- QUYET DINH NAY DAO NGUOC MOT QUYET DINH CU. DOC KY TRUOC KHI SUA TIEP.
--
-- Baseline 001 co y chi lay tien cua hoa don, va ghi ro ly do: giao dien coi
-- `cost_usd IS NULL` la "chua co hoa don" roi gan dau ≈ dua vao do. Do tien
-- Gateway vao day lam no trong nhu tien da duoc hoa don xac nhan.
--
-- Chu du an chot ngay 31/08/2026 rang danh doi do CHAP NHAN DUOC, voi ly do:
--   - Du lieu cua ba nguon cu von da khong dong nhat (keo tay, gioi han cua
--     Google Cloud, khong voi sau duoc vao trong cac app), nen sai so la thu
--     phai song chung.
--   - Do 31/08: Ralli 100% uoc tinh, TLA Hop Dong 78,1%. Viec phan biet
--     hoa-don/uoc-tinh khong doi mot quyet dinh nao trong thuc te dung.
--
-- Quyet dinh nay THAY THE yeu cau sau cua change
-- `label-derived-cost-across-dashboard`, specs/visible-data-provenance:
--     "Moi o, the, bieu do va dong xuat CSV co chua tien SHALL cho biet phan nao
--      den tu hoa don va phan nao suy tu bang gia."
-- Voi nguon `gateway`, yeu cau do khong con hieu luc.
--
-- HE QUA PHAI BIET
--   - app.js:1143 dem tien Gateway vao nhom `costInv` (tien hoa don), khong con
--     gan dau ≈. app.js:3806 ghi nhan nguon la "hoa don".
--   - Phep kiem `Tien: hoa don == usage_resolved` trong scripts/audit_db.py da
--     duoc sua thanh `hoa don + gateway == view` cung ngay. Thieu buoc do thi
--     audit do moi lan chay, va update_dashboard.py that bai o buoc 9/9.
--
-- THU TU UU TIEN: hoa don TRUOC, Gateway SAU. Hoa don la so Google thuc su tru
-- tien; so cua Gateway la LiteLLM tu nhan tu bang gia rieng cua no. Ngay hoa don
-- ve, no thay the so uoc tinh - dung nhu voi ba nguon cu.
--
-- Cot va thu tu cot KHONG DOI nen CREATE OR REPLACE dung duoc. Da kiem 31/08:
-- khong view nao phu thuoc `usage_resolved`.

CREATE OR REPLACE VIEW usage_resolved AS
WITH keys AS (
    SELECT DISTINCT day, agent_id, model_id FROM fact_usage_daily
),
g AS (
    SELECT day, agent_id, model_id,
           SUM(total_tokens) AS tokens, SUM(cost_usd) AS cost, SUM(calls) AS calls,
           SUM(input_tokens) AS tok_in, SUM(output_tokens) AS tok_out,
           SUM(cached_tokens) AS tok_cached
    FROM fact_usage_daily WHERE source = 'gateway'
    GROUP BY day, agent_id, model_id
),
b AS (
    SELECT day, agent_id, model_id,
           SUM(total_tokens) AS tokens, SUM(cost_usd) AS cost, SUM(calls) AS calls,
           SUM(input_tokens) AS tok_in, SUM(output_tokens) AS tok_out,
           SUM(cached_tokens) AS tok_cached
    FROM fact_usage_daily WHERE source = 'billing'
    GROUP BY day, agent_id, model_id
),
m AS (
    SELECT day, agent_id, model_id,
           SUM(total_tokens) AS tokens, SUM(calls) AS calls,
           SUM(input_tokens) AS tok_in, SUM(output_tokens) AS tok_out,
           SUM(cached_tokens) AS tok_cached
    FROM fact_usage_daily WHERE source = 'monitoring'
    GROUP BY day, agent_id, model_id
),
a AS (
    SELECT day, agent_id, model_id,
           SUM(total_tokens) AS tokens, SUM(calls) AS calls,
           SUM(input_tokens) AS tok_in, SUM(output_tokens) AS tok_out,
           SUM(cached_tokens) AS tok_cached
    FROM fact_usage_daily WHERE source = 'app'
    GROUP BY day, agent_id, model_id
)
SELECT k.day,
       k.agent_id,
       k.model_id,
       COALESCE(g.tokens, b.tokens, m.tokens, a.tokens)  AS total_tokens,
       -- Ba cột này lấy từ CÙNG nguồn với total_tokens, không COALESCE riêng
       -- từng cột: trộn input_tokens của hoá đơn với output_tokens của
       -- monitoring sẽ ra một cặp số không kỳ nguồn nào từng báo cáo.
       CASE WHEN g.tokens IS NOT NULL THEN g.tok_in
            WHEN b.tokens IS NOT NULL THEN b.tok_in
            WHEN m.tokens IS NOT NULL THEN m.tok_in
            ELSE a.tok_in     END               AS input_tokens,
       CASE WHEN g.tokens IS NOT NULL THEN g.tok_out
            WHEN b.tokens IS NOT NULL THEN b.tok_out
            WHEN m.tokens IS NOT NULL THEN m.tok_out
            ELSE a.tok_out    END               AS output_tokens,
       CASE WHEN g.tokens IS NOT NULL THEN g.tok_cached
            WHEN b.tokens IS NOT NULL THEN b.tok_cached
            WHEN m.tokens IS NOT NULL THEN m.tok_cached
            ELSE a.tok_cached END               AS cached_tokens,
       -- HOÁ ĐƠN TRƯỚC, GATEWAY SAU. Xem đầu file để biết vì sao quyết định
       -- này đảo ngược baseline 001, và nó thay thế yêu cầu spec nào.
       --
       -- Thứ tự này KHÁC thứ tự của total_tokens (gateway trước): token thì
       -- Gateway đếm chính xác hơn hoá đơn, còn tiền thì hoá đơn là số thật.
       COALESCE(b.cost, g.cost)                 AS cost_usd,
       COALESCE(g.calls, m.calls, a.calls)      AS calls,
       CASE WHEN g.tokens IS NOT NULL THEN 'gateway'
            WHEN b.tokens IS NOT NULL THEN 'billing'
            WHEN m.tokens IS NOT NULL THEN 'monitoring'
            WHEN a.tokens IS NOT NULL THEN 'app'   END AS token_source,
       CASE WHEN g.calls  IS NOT NULL THEN 'gateway'
            WHEN m.calls  IS NOT NULL THEN 'monitoring'
            WHEN a.calls  IS NOT NULL THEN 'app'   END AS call_source,
       -- 1 = TOKEN của dòng này chưa được hoá đơn xác nhận. KHÔNG đổi theo
       -- migration này: nó nói về token, không nói về tiền. Dòng Gateway vẫn
       -- mang cờ 1 dù nay đã có tiền hiển thị.
       CASE WHEN b.tokens IS NULL THEN 1 ELSE 0 END   AS token_estimated
FROM keys k
LEFT JOIN g ON g.day = k.day AND g.agent_id = k.agent_id AND g.model_id = k.model_id
LEFT JOIN b ON b.day = k.day AND b.agent_id = k.agent_id AND b.model_id = k.model_id
LEFT JOIN m ON m.day = k.day AND m.agent_id = k.agent_id AND m.model_id = k.model_id
LEFT JOIN a ON a.day = k.day AND a.agent_id = k.agent_id AND a.model_id = k.model_id;
