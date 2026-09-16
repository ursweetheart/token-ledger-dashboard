# Law Insight — audit identity và đường LLM (offline, read-only)

## Kết quả thực thi

- Repo `C:/law_insight`, HEAD `dfd7cdca75fc173e7e0f4ea416b1a6b919b65774`; interpreter `.venv-gateway/Scripts/python.exe`: **Python 3.14.5**.
- Hai bộ test có sẵn: **20 passed, 1 failed** (7/7 gateway; 13/14 token_logger), 7.32s.
- Lần chạy cuối gồm 5 probe bổ sung: **25 passed, 1 failed, 19 warnings**, 8.00s; tổng 26 case được đếm lại từ AST và đối chiếu pytest. 5/5 probe bổ sung PASS nghĩa là tái hiện hành vi, không phải toàn bộ yêu cầu đã đạt.
- FAIL: `backend/tests/test_token_logger.py:250-297`, gọi helper tại `:289` không tạo UsageContext và vẫn kỳ vọng model direct Gemini. Gateway chặn tại `backend/app/services/llm.py:70-72`. Đây là test direct cũ không tương thích môi trường gateway; không sửa/xóa/skip để làm xanh.
- **0 authenticated HTTP-router test được chạy thành công**: import router thật bị `ModuleNotFoundError: fastapi`; probe analyze còn phát hiện thiếu `qdrant_client`. Không cài dependency, không khởi động app.
- Không đọc `.env`; guard đã chặn một lần LiteLLM cố auto-load dotenv ở collection. Sau đó vô hiệu cả python-dotenv và Pydantic dotenv source trong tiến trình test. Guard mạng ban đầu chặn cả Windows asyncio self-pipe (12 pass/9 setup error); đã giới hạn ngoại lệ đúng stdlib `_fallback_socketpair` loopback, không mở egress ứng dụng. Các lỗi chuẩn bị này không tính là lỗi sản phẩm.

## Lệnh tái chạy an toàn

Chạy từ `C:/law_insight` bằng Git Bash:

```bash
LLM_MODE=gateway GEMINI_API_KEY_1='' GEMINI_API_KEY_2='' GEMINI_API_KEY_3='' \
LITELLM_LOCAL_MODEL_COST_MAP=True PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH='C:/token-ledger-dashboard/tools/gateway-smoke/harnesses/identity-audit-support;backend' \
.venv-gateway/Scripts/python.exe -m pytest -p no:cacheprovider \
backend/tests/test_llm_gateway.py backend/tests/test_token_logger.py \
C:/token-ledger-dashboard/tools/gateway-smoke/harnesses/identity-audit-support/test_active_paths.py \
-q --tb=short -rA
```

`PYTHONPATH` giữ `backend`, thêm bootstrap `sitecustomize.py` để chặn dotenv trước import, kể cả subprocess của test import. Bootstrap đặt DB/JWT giả, xóa key provider khỏi môi trường test, chặn DNS/connect/sendto và tắt bytecode/cache pytest. Các probe riêng chỉ đặt key giả tạm thời để kiểm tra nhánh, thay callable provider bằng mock; không gọi SDK/network thật. Không chạy migration hay persistence thật.

## Trace và khoảng trống chính xác

Tất cả đường dẫn sau tương đối với `C:/law_insight`.

| Đường | Bằng chứng | Phạm vi xác minh / khoảng trống |
|---|---|---|
| Auth → user server-side | `backend/app/middleware/__init__.py:16-44`: JWT decode, lấy `sub`, lookup User và kiểm tra active; `:47-51` require_auth | Chỉ static: chưa chạy JWT/login/expired/revoked/spoofed-header HTTP vì thiếu FastAPI. Username dự kiến lấy từ User DB, không từ header client. |
| User → UsageContext | `backend/app/services/token_logger.py:21-35,114-135` immutable dataclass + ContextVar set/reset | Test scope/reset PASS; helper test tự dựng identity, không chứng minh authenticated router. |
| Chat → gateway | `backend/app/routers/chat.py:349-378` require_auth + session access; `:463-475` truyền `user.id/user.username/company_id/unit_id`; `backend/app/services/llm.py:202-205,68-98` | `X-User` và `user` đều là **username** tại `llm.py:82`, tạo riêng từng call; 3 user helper chạy song song và outage không fallback PASS (`test_llm_gateway.py:47-66`). Chưa kiểm chứng auth/session ownership/spoofing qua router. |
| Analyze upload → parser | `backend/app/routers/analyze.py:470-475,655-663` tạo context function `ocr`; `_parse_file :220-228` gọi parser theo định dạng | Static cho route; không upload vì có ghi đĩa/DB. Context không tự biến parser thành gateway. |
| Analyze background → fan-out | `backend/app/routers/analyze.py:808-814` truyền username và ID; `:235-251` semaphore; `:307-326` dựng lại snapshot rồi run_pipeline | Probe thực thi nguyên hàm background trích AST, cache giả, pipeline dừng trước persistence: alice/bob/carol giữ đúng context sau async scheduling. DTO RAG được thay SimpleNamespace vì thiếu Qdrant. Không phải route/job E2E hoặc test pipeline thật. |
| Agent/retry/validation calls | `backend/app/services/agents.py:17,786,848,959,1041,1123,1180,1356` đều gọi call_llm; fan-out `:1268` gather | Qua helper ở gateway mode theo static trace. Chưa chạy orchestration thật, retries nghiệp vụ, cancellation/restart, hoặc load authenticated app. |
| KB upload/version/restore → OCR | `backend/app/routers/knowledge_base.py:491-499,664-672,740-748` truyền snapshot; `:178-186` context `kb_ocr`; `:194,202` local fallback | Snapshot có truyền. Nhưng OCR đầu tiên vẫn Google trực tiếp; test token_logger OCR chỉ fake model/record, không phải gateway. |
| Knowledge legacy background | `backend/app/routers/knowledge.py:323-326,491-495` schedule; `:68-79` không nhận username/user_id và gọi parse_pdf ngoài UsageContext | Probe nguyên hàm trích AST chứng minh context **None** tại parser. Nếu OCR direct được chọn, usage có thể thiếu user snapshot. Không chạy DB phía sau. |
| PDF Gemini OCR bypass | `backend/app/services/parser.py:34-45`; `backend/app/services/gemini_ocr.py:48-53,101-111,143-168` configure/generate_content trực tiếp Google, không kiểm tra llm_mode | Probe PASS tái hiện `LLM_MODE=gateway` + key giả vẫn chọn callable OCR direct. Không có X-User gateway. OCR ghi usage sau executor tại `:114-121` nên context coroutine vẫn có thể còn; không nhầm việc này với propagation trong thread. |
| LlamaParse cloud bypass | `backend/app/services/parser.py:48-57,64-98` client cloud + 4 attempts | Probe PASS tái hiện gateway mode vẫn chọn cloud fallback khi có key giả, không yêu cầu identity. Không có gateway header/record_model_call tại boundary này. |
| Marker | KB gọi local tại `knowledge_base.py:198-204`; `backend/app/services/marker_converter.py:78-99` tạo GoogleGeminiService; `:148-174` LLM trong run_in_executor | Local Marker không phải gateway LLM. Toàn backend search `convert_pdf_with_llm` chỉ tìm được definition `:148`: chưa thấy caller active, nên đánh dấu **latent**, không khẳng định nhánh direct đang chạy. Probe mock chứng minh executor của nhánh này mất ContextVar; không có usage boundary riêng. |
| Embedding/reranker | `backend/app/services/vectordb.py:113-122,128,148-157`; sparse `backend/app/services/rag_sparse.py:34-36` | Local SentenceTransformer/CrossEncoder/FastEmbed, ngoài gateway token accounting. Không init/download/Qdrant call trong audit. |
| Accounting | `backend/app/services/llm.py:90-95`; `backend/app/services/token_logger.py:234-261` | Normalize/build-row/fake-session tests PASS; không chứng minh DB durability. Logger trả False khi commit lỗi (`:259-261`), helper không kiểm tra return (`llm.py:93-95`): response có thể thành công mà app ledger thiếu row. Chưa reconcile SpendLogs → ETL → dashboard, retry duplicates/cost/dept mapping. |

## Kết luận

**Chưa đạt “mọi LLM đi qua LB, identity authenticated end-to-end”.** Core chat/agent helper có nhánh gateway fail-closed và `X-User: <username>` đúng ở biên mock. Tuy nhiên PDF OCR/LlamaParse còn nhánh trực tiếp không chịu `LLM_MODE`; knowledge legacy thiếu context; Marker LLM là nhánh latent mất context trong executor.

URL helper được kiểm tra hình thức tại `llm.py:73-79` nhưng không xác nhận đích là LB. Test `test_llm_gateway.py:19-38` chỉ assert kwargs mock, không gửi HTTP tới `127.0.0.1:4100`. Audit này không chứng minh LB traversal, hai Proxy, load capacity hay SpendLogs; các gate đó thuộc harness riêng của tác vụ cha. Không đổi `X-User` sang UUID.

## File và tính toàn vẹn

Tạo chỉ trong thư mục evidence riêng:
- `tools/gateway-smoke/reports/identity-audit.md`
- `tools/gateway-smoke/harnesses/identity-audit-support/sitecustomize.py`
- `tools/gateway-smoke/harnesses/identity-audit-support/test_active_paths.py`

`git status --short` Law Insight trước/sau không thay đổi: hai file đã sửa sẵn `backend/app/config.py`, `backend/app/services/llm.py`; hai untracked sẵn `backend/GATEWAY.md`, `backend/tests/test_llm_gateway.py`. Không sửa app code, không git write, không container change, không provider thật, không DB write.
