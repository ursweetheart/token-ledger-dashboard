-- ==============================================================
-- SINH TU DONG boi db/gen_catalog.py - dung sua tay.
-- Sua quy tac trong db/rules.py hoac trong script do roi chay lai.
-- ==============================================================

-- 8 agent. Khoang ngay TINH TU DU LIEU; is_running go tay theo muc C3.
INSERT INTO dim_agent (agent_id, code, name, gcp_project_id, has_org_tree,
                       project_created_at, data_from, data_to,
                       is_running, has_google_source) VALUES
  (1, 'contact-center', 'Chatbot Contact Center', 'pro-tuner-454203-v3', FALSE, '2025-03-19', '2026-01-13', NULL, TRUE, TRUE),
  (2, 'sale-agent', 'Sale Agent', 'tranquil-post-471401-c1', FALSE, '2025-09-07', '2026-01-01', NULL, TRUE, TRUE),
  (3, 'invoice', 'Multi modal AI Invoice', 'multimodal-invoice', FALSE, '2025-09-15', '2026-01-22', '2026-08-26', FALSE, TRUE),
  (4, 'tools-quizzer', 'Tools Quizzer', 'tools-quizz', FALSE, '2026-04-10', '2026-06-17', '2026-08-21', FALSE, TRUE),
  (5, 'tla-hd', 'Trợ Lý Ảo Hợp Đồng', 'ai-chatbot-contract', TRUE, '2026-06-20', '2026-07-02', NULL, TRUE, TRUE),
  (6, 'dms-feedback', 'Phân Loại Phản Hồi Tiếp Thị', 'feedback-dms-tiep-thi', FALSE, '2026-06-25', '2026-07-06', NULL, TRUE, TRUE),
  (7, 'crm-feedback', 'Phân Loại Dữ Liệu CRM', 'crm-500509', FALSE, '2026-06-25', '2026-07-06', NULL, TRUE, TRUE),
  (8, 'ralli', 'Trợ lý ảo Ralli', 'tla-ralli', TRUE, NULL, '2026-03-14', NULL, TRUE, FALSE);

-- 12 model, ten chuan dang gach ngang.
INSERT INTO dim_model (model_id, name, family, provider) VALUES
  (1, 'gemini-2.0-flash', 'gemini-2.0', 'Google'),
  (2, 'gemini-2.5-flash', 'gemini-2.5', 'Google'),
  (3, 'gemini-2.5-flash-lite', 'gemini-2.5', 'Google'),
  (4, 'gemini-2.5-pro', 'gemini-2.5', 'Google'),
  (5, 'gemini-3-flash', 'gemini-3', 'Google'),
  (6, 'gemini-3-pro', 'gemini-3', 'Google'),
  (7, 'gemini-3.1-flash-lite', 'gemini-3', 'Google'),
  (8, 'gemini-3.5-flash', 'gemini-3', 'Google'),
  (9, 'gemini-embedding-1.0', 'embedding', 'Google'),
  (10, 'gemini-embedding-2', 'embedding', 'Google'),
  (11, 'gemini-3.6-flash', 'gemini-3', 'Google'),
  (12, 'gemini-3.5-flash-lite', 'gemini-3', 'Google');

-- 49 anh xa. Ba nguon goi ten model theo ba kieu khac nhau:
--   billing 'gemini-embedding-001'  <->  monitoring 'gemini-embedding-1.0'
INSERT INTO dim_model_alias (source, raw_name, model_id) VALUES
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
  ('monitoring', 'gemini-2.5-flash-lite', 3),
  ('monitoring', 'gemini-2.5-pro', 4),
  ('monitoring', 'gemini-3-flash', 5),
  ('monitoring', 'gemini-3.1-flash-lite', 7),
  ('monitoring', 'gemini-3.5-flash', 8),
  ('monitoring', 'gemini-3.5-flash-lite', 12),
  ('monitoring', 'gemini-3.6-flash', 11),
  ('monitoring', 'gemini-embedding-1.0', 9),
  ('monitoring', 'gemini-embedding-2', 10),
  ('gateway', 'gemini/gemini-3.6-flash', 11),
  ('gateway', 'gemini/gemini-3.5-flash-lite', 12),
  ('gateway', 'gemini/gemini-2.5-flash', 2);

-- 48 bi danh do dac: 17 phep do
-- monitoring + 31 SKU hoa don. Thay cho viec doan ten bang
-- regex va LIKE '%token_count'. Nguon: descriptor + Cloud Billing Catalog.
INSERT INTO dim_metric_alias (source, raw_name, label, measures, kind, metric_kind, value_type) VALUES
  ('monitoring', 'generativelanguage.googleapis.com/generate_content_usage_output_token_count', 'Generate content usage output token count.', 'token', 'output', 'DELTA', 'INT64'),
  ('monitoring', 'generativelanguage.googleapis.com/quota/embed_content_paid_tier_3_requests/limit', 'Current limit on quota metric generativelanguage.googleapis.com/embed_content_paid_tier_3_requests.', 'quota_limit', NULL, 'GAUGE', 'INT64'),
  ('monitoring', 'generativelanguage.googleapis.com/quota/embed_content_paid_tier_3_requests/usage', 'Current usage on quota metric generativelanguage.googleapis.com/embed_content_paid_tier_3_requests.', 'calls', NULL, 'DELTA', 'INT64'),
  ('monitoring', 'generativelanguage.googleapis.com/quota/generate_content_free_tier_input_token_count/limit', 'Current limit on quota metric generativelanguage.googleapis.com/generate_content_free_tier_input_token_count.', 'quota_limit', NULL, 'GAUGE', 'INT64'),
  ('monitoring', 'generativelanguage.googleapis.com/quota/generate_content_free_tier_input_token_count/usage', 'Current usage on quota metric generativelanguage.googleapis.com/generate_content_free_tier_input_token_count.', 'token', 'input', 'DELTA', 'INT64'),
  ('monitoring', 'generativelanguage.googleapis.com/quota/generate_content_free_tier_requests/limit', 'Current limit on quota metric generativelanguage.googleapis.com/generate_content_free_tier_requests.', 'quota_limit', NULL, 'GAUGE', 'INT64'),
  ('monitoring', 'generativelanguage.googleapis.com/quota/generate_content_free_tier_requests/usage', 'Current usage on quota metric generativelanguage.googleapis.com/generate_content_free_tier_requests.', 'calls', NULL, 'DELTA', 'INT64'),
  ('monitoring', 'generativelanguage.googleapis.com/quota/generate_content_paid_tier_3_input_token_count/limit', 'Current limit on quota metric generativelanguage.googleapis.com/generate_content_paid_tier_3_input_token_count.', 'quota_limit', NULL, 'GAUGE', 'INT64'),
  ('monitoring', 'generativelanguage.googleapis.com/quota/generate_content_paid_tier_3_input_token_count/usage', 'Current usage on quota metric generativelanguage.googleapis.com/generate_content_paid_tier_3_input_token_count.', 'token', 'input', 'DELTA', 'INT64'),
  ('monitoring', 'generativelanguage.googleapis.com/quota/generate_content_paid_tier_3_requests/limit', 'Current limit on quota metric generativelanguage.googleapis.com/generate_content_paid_tier_3_requests.', 'quota_limit', NULL, 'GAUGE', 'INT64'),
  ('monitoring', 'generativelanguage.googleapis.com/quota/generate_content_paid_tier_3_requests/usage', 'Current usage on quota metric generativelanguage.googleapis.com/generate_content_paid_tier_3_requests.', 'calls', NULL, 'DELTA', 'INT64'),
  ('monitoring', 'generativelanguage.googleapis.com/quota/generate_content_paid_tier_input_token_count/limit', 'Current limit on quota metric generativelanguage.googleapis.com/generate_content_paid_tier_input_token_count.', 'quota_limit', NULL, 'GAUGE', 'INT64'),
  ('monitoring', 'generativelanguage.googleapis.com/quota/generate_content_paid_tier_input_token_count/usage', 'Current usage on quota metric generativelanguage.googleapis.com/generate_content_paid_tier_input_token_count.', 'token', 'input', 'DELTA', 'INT64'),
  ('monitoring', 'generativelanguage.googleapis.com/quota/generate_requests_per_model/limit', 'Current limit on quota metric generativelanguage.googleapis.com/generate_requests_per_model.', 'quota_limit', NULL, 'GAUGE', 'INT64'),
  ('monitoring', 'generativelanguage.googleapis.com/quota/generate_requests_per_model/usage', 'Current usage on quota metric generativelanguage.googleapis.com/generate_requests_per_model.', 'calls', NULL, 'DELTA', 'INT64'),
  ('monitoring', 'serviceruntime.googleapis.com/api/request_count', 'The count of completed requests.', 'calls', NULL, 'DELTA', 'INT64'),
  ('monitoring', 'serviceruntime.googleapis.com/api/request_latencies', 'Distribution of latencies in seconds for non-streaming requests.', 'latency', NULL, 'DELTA', 'DISTRIBUTION'),
  ('billing_sku', '07D6-73CA-C859', 'Generate_content cached text input token count for gemini 3 flash', 'token', 'cached', NULL, NULL),
  ('billing_sku', '0F51-429B-C2DC', 'Generate content output token count Gemini 2.5 Pro short output text', 'token', 'output', NULL, NULL),
  ('billing_sku', '13B8-087F-4762', 'EmbedContent input token count for gemini-embedding-2 text', 'token', 'input', NULL, NULL),
  ('billing_sku', '1C33-4690-9D67', 'Generate content cached input token count gemini 2.5 flash input image', 'token', 'cached', NULL, NULL),
  ('billing_sku', '1FD9-C71B-4D32', 'Generate content input token count Gemini 2.5 Pro input image', 'token', 'input', NULL, NULL),
  ('billing_sku', '2D1C-F790-3C09', 'Generate content input token count Gemini 2.5 Pro short input text', 'token', 'input', NULL, NULL),
  ('billing_sku', '2F6F-C249-0F1B', 'GenerateContent text output token count for Gemini 2.0 Flash', 'token', 'output', NULL, NULL),
  ('billing_sku', '399C-32AD-1412', 'Generate content input token count gemini 2.5 flash lite short input text', 'token', 'input', NULL, NULL),
  ('billing_sku', '43A6-3A69-1E0A', 'GenerateContent image input token count for Gemini 2.0 Flash', 'token', 'input', NULL, NULL),
  ('billing_sku', '4D6D-3A29-44D7', 'Generate_content text cached input token count for gemini 3 pro short', 'token', 'cached', NULL, NULL),
  ('billing_sku', '5308-F418-CF26', 'Generate content input token count gemini 2.5 flash input audio', 'token', 'input', NULL, NULL),
  ('billing_sku', '530B-F4DF-9814', 'Generate_content text output token count for gemini 3 pro short', 'token', 'output', NULL, NULL),
  ('billing_sku', '54F8-C433-9340', 'Generate content input token count gemini 3.1 flash lite preview text', 'token', 'input', NULL, NULL),
  ('billing_sku', '5882-9C22-CC57', 'Generate content output token count gemini 3.1 flash lite preview text', 'token', 'output', NULL, NULL),
  ('billing_sku', '5CDC-4C82-2AEC', 'Generate content cached input token count gemini 2.5 flash input short text', 'token', 'cached', NULL, NULL),
  ('billing_sku', '63AC-2BA8-3F85', 'Generate content input token count gemini 3.5 flash text', 'token', 'input', NULL, NULL),
  ('billing_sku', '68D6-42D9-37E1', 'Generate content input token count gemini 2.5 flash input image', 'token', 'input', NULL, NULL),
  ('billing_sku', '6EDB-2409-6348', 'Generate content output token count gemini 2.5 flash short output text non-thinking', 'token', 'output', NULL, NULL),
  ('billing_sku', '7133-23F2-04B7', 'Generate content output token count gemini 2.5 flash lite short output text non-thinking', 'token', 'output', NULL, NULL),
  ('billing_sku', '8DCE-878A-487F', 'GenerateContent audio input token count for Gemini 2.0 Flash', 'token', 'input', NULL, NULL),
  ('billing_sku', '911A-8880-A243', 'Generate content output token count gemini 2.5 flash short input text', 'token', 'output', NULL, NULL),
  ('billing_sku', '9465-C223-0CE9', 'Generate content cached input token count gemini 2.5 pro short input', 'token', 'cached', NULL, NULL),
  ('billing_sku', '96EA-8692-BEAE', 'GenerateContent text input token count for Gemini 2.0 Flash', 'token', 'input', NULL, NULL),
  ('billing_sku', '981A-C057-0BF9', 'Generate content input token count gemini 2.5 flash short input text', 'token', 'input', NULL, NULL),
  ('billing_sku', 'ACA6-865B-F153', 'Generate_content text output token count for gemini 3 flash', 'token', 'output', NULL, NULL),
  ('billing_sku', 'C2BC-2466-DBDE', 'Generate content cached input token count gemini 2.5 flash input audio', 'token', 'cached', NULL, NULL),
  ('billing_sku', 'E211-E01C-0CB3', 'EmbedContent input token count for gemini-embedding-001', 'token', 'input', NULL, NULL),
  ('billing_sku', 'EBC7-B1E9-1DA3', 'Generate_content text cached input token count for gemini 2.5 Flash Lite', 'token', 'cached', NULL, NULL),
  ('billing_sku', 'F2C1-F842-5D84', 'Generate_content text input token count for gemini 3 flash', 'token', 'input', NULL, NULL),
  ('billing_sku', 'F9BE-D8E8-69E9', 'Generate content output token count gemini 3.5 flash text', 'token', 'output', NULL, NULL),
  ('billing_sku', 'FB70-0CFB-9533', 'Generate_content text input token count for gemini 3 pro short', 'token', 'input', NULL, NULL);

-- 12 bang gia CHINH CHU tu Cloud Billing Catalog (USD / 1 trieu token).
-- Truoc day bang nay RONG. Moi model lay gia cua SKU co khoi luong lon nhat
-- trong hoa don. Catalog chi co gia HIEN HANH, khong co lich su.
-- Model CHUA CO HOA DON thi khong co khoi luong de chon -> lay SKU TEXT
-- TIEU CHUAN (khong flex/priority/batch/caching). Xem price_table().
INSERT INTO ref_price (model_id, effective_from, price_input, price_output, price_cached, source) VALUES
  (1, '2026-08-13', 0.10000000, 0.40000000, NULL, 'google'),
  (2, '2026-08-13', 0.30000000, 2.50000000, 0.03000000, 'google'),
  (3, '2026-08-13', 0.10000000, 0.40000000, 0.01000000, 'google'),
  (4, '2026-08-13', 1.25000000, 10.00000000, 0.12500000, 'google'),
  (5, '2026-08-13', 0.50000000, 3.00000000, 0.05000000, 'google'),
  (6, '2026-08-13', 2.00000000, 12.00000000, 0.20000000, 'google'),
  (7, '2026-08-13', 0.25000000, 1.50000000, NULL, 'google'),
  (8, '2026-08-13', 1.50000000, 9.00000000, NULL, 'google'),
  (9, '2026-08-13', 0.15000000, NULL, NULL, 'google'),
  (10, '2026-08-13', 0.20000000, NULL, NULL, 'google'),
  (11, '2026-08-13', 0.75000000, 3.75000000, 0.07500000, 'google'),
  (12, '2026-08-13', 0.30000000, 2.50000000, 0.03000000, 'google');

-- Ty gia go cung (quyet dinh M-F). Keo API sau, cau truc khong phai doi.
INSERT INTO ref_fx (day, vnd_per_usd, source) VALUES ('2026-08-08', 25200, 'hardcoded (app.js)');

-- Ralli chan theo TOKEN, sau agent kia theo TIEN. Khong quy doi.
-- Tools Quizzer khong co ngan sach: app.js da loai khoi danh sach.
INSERT INTO ref_budget (agent_id, month, budget_usd, budget_tokens) VALUES
  (1, '2026-08-01', 30, NULL),
  (2, '2026-08-01', 50, NULL),
  (3, '2026-08-01', 20, NULL),
  (5, '2026-08-01', 20, NULL),
  (6, '2026-08-01', 20, NULL),
  (7, '2026-08-01', 20, NULL),
  (8, '2026-08-01', NULL, 50000000);
