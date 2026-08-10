-- ==============================================================
-- SINH TU DONG boi db/sinh_02_danh_muc.py - dung sua tay.
-- Sua quy tac trong db/quy_tac.py hoac trong script do roi chay lai.
-- ==============================================================

-- 8 agent. Khoang ngay TINH TU DU LIEU; dang_van_hanh go tay theo muc C3.
INSERT INTO dim_agent (agent_id, ma, ten, gcp_project_id, co_cay_to_chuc,
                       ngay_tao_project, ngay_bat_dau_co_du_lieu,
                       ngay_ket_thuc_du_lieu, dang_van_hanh, co_nguon_doi_chung) VALUES
  (1, 'contact-center', 'Chatbot Contact Center', 'pro-tuner-454203-v3', FALSE, '2025-03-19', '2026-01-13', NULL, TRUE, TRUE),
  (2, 'sale-agent', 'Sale Agent', 'tranquil-post-471401-c1', FALSE, '2025-09-07', '2026-01-01', NULL, TRUE, TRUE),
  (3, 'invoice', 'Multi modal AI Invoice', 'multimodal-invoice', FALSE, '2025-09-15', '2026-01-22', '2026-07-25', FALSE, TRUE),
  (4, 'tools-quizzer', 'Tools Quizzer', 'tools-quizz', FALSE, '2026-04-10', '2026-06-17', '2026-07-01', FALSE, TRUE),
  (5, 'tla-hd', 'Trợ Lý Ảo Hợp Đồng', 'ai-chatbot-contract', TRUE, '2026-06-20', '2026-07-02', NULL, TRUE, TRUE),
  (6, 'dms-feedback', 'Phân Loại Phản Hồi Tiếp Thị', 'feedback-dms-tiep-thi', FALSE, '2026-06-25', '2026-07-06', NULL, TRUE, TRUE),
  (7, 'crm-feedback', 'Phân Loại Dữ Liệu CRM', 'crm-500509', FALSE, '2026-06-25', '2026-07-06', NULL, TRUE, TRUE),
  (8, 'ralli', 'Trợ lý ảo Ralli', NULL, TRUE, NULL, '2026-03-14', NULL, TRUE, FALSE);

-- 10 model, ten chuan dang gach ngang.
INSERT INTO dim_model (model_id, ten, ho, provider) VALUES
  (1, 'gemini-2.0-flash', 'gemini-2.0', 'Google'),
  (2, 'gemini-2.5-flash', 'gemini-2.5', 'Google'),
  (3, 'gemini-2.5-flash-lite', 'gemini-2.5', 'Google'),
  (4, 'gemini-2.5-pro', 'gemini-2.5', 'Google'),
  (5, 'gemini-3-flash', 'gemini-3', 'Google'),
  (6, 'gemini-3-pro', 'gemini-3', 'Google'),
  (7, 'gemini-3.1-flash-lite', 'gemini-3', 'Google'),
  (8, 'gemini-3.5-flash', 'gemini-3', 'Google'),
  (9, 'gemini-embedding-1.0', 'embedding', 'Google'),
  (10, 'gemini-embedding-2', 'embedding', 'Google');

-- 43 anh xa. Ba nguon goi ten model theo ba kieu khac nhau:
--   billing 'gemini-embedding-001'  <->  monitoring 'gemini-embedding-1.0'
INSERT INTO dim_model_alias (nguon, ten_goc, model_id) VALUES
  ('billing_sku', '07D6-73CA-C859', 5),
  ('billing_sku', '0F51-429B-C2DC', 4),
  ('billing_sku', '13B8-087F-4762', 10),
  ('billing_sku', '1C33-4690-9D67', 2),
  ('billing_sku', '1FD9-C71B-4D32', 4),
  ('billing_sku', '2D1C-F790-3C09', 4),
  ('billing_sku', '2F6F-C249-0F1B', 1),
  ('billing_sku', '399C-32AD-1412', 3),
  ('billing_sku', '43A6-3A69-1E0A', 1),
  ('billing_sku', '4D6D-3A29-44D7', 6),
  ('billing_sku', '5308-F418-CF26', 2),
  ('billing_sku', '530B-F4DF-9814', 6),
  ('billing_sku', '54F8-C433-9340', 7),
  ('billing_sku', '5882-9C22-CC57', 7),
  ('billing_sku', '5CDC-4C82-2AEC', 2),
  ('billing_sku', '63AC-2BA8-3F85', 8),
  ('billing_sku', '68D6-42D9-37E1', 2),
  ('billing_sku', '6EDB-2409-6348', 2),
  ('billing_sku', '7133-23F2-04B7', 3),
  ('billing_sku', '8DCE-878A-487F', 1),
  ('billing_sku', '911A-8880-A243', 2),
  ('billing_sku', '9465-C223-0CE9', 4),
  ('billing_sku', '96EA-8692-BEAE', 1),
  ('billing_sku', '981A-C057-0BF9', 2),
  ('billing_sku', 'ACA6-865B-F153', 5),
  ('billing_sku', 'C2BC-2466-DBDE', 2),
  ('billing_sku', 'E211-E01C-0CB3', 9),
  ('billing_sku', 'EBC7-B1E9-1DA3', 3),
  ('billing_sku', 'F2C1-F842-5D84', 5),
  ('billing_sku', 'F9BE-D8E8-69E9', 8),
  ('billing_sku', 'FB70-0CFB-9533', 6),
  ('app', 'gemini-2.0-flash', 1),
  ('app', 'gemini-2.5-flash', 2),
  ('app', 'gemini-2.5-flash-lite', 3),
  ('app', 'gemini-2.5-pro', 4),
  ('monitoring', 'gemini-2.0-flash', 1),
  ('monitoring', 'gemini-2.5-flash', 2),
  ('monitoring', 'gemini-2.5-pro', 4),
  ('monitoring', 'gemini-3-flash', 5),
  ('monitoring', 'gemini-3.1-flash-lite', 7),
  ('monitoring', 'gemini-3.5-flash', 8),
  ('monitoring', 'gemini-embedding-1.0', 9),
  ('monitoring', 'gemini-embedding-2', 10);

-- Ty gia go cung (quyet dinh M-F). Keo API sau, cau truc khong phai doi.
INSERT INTO ref_fx (ngay, vnd_moi_usd, nguon) VALUES ('2026-08-08', 25200, 'go cung (app.js)');

-- Ralli chan theo TOKEN, sau agent kia theo TIEN. Khong quy doi.
-- Tools Quizzer khong co ngan sach: app.js da loai khoi danh sach.
INSERT INTO ref_budget (agent_id, thang, ngan_sach_usd, ngan_sach_token) VALUES
  (1, '2026-08-01', 30, NULL),
  (2, '2026-08-01', 50, NULL),
  (3, '2026-08-01', 20, NULL),
  (5, '2026-08-01', 20, NULL),
  (6, '2026-08-01', 20, NULL),
  (7, '2026-08-01', 20, NULL),
  (8, '2026-08-01', NULL, 50000000);
