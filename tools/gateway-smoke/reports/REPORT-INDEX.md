# Báo cáo kiểm thử các agent qua API Gateway

Mỗi báo cáo dưới đây ghi rõ ranh giới bằng chứng. TLA-HĐ và Ralli có harness mock đối chiếu trực tiếp; Ralli, DMS và CRM có thêm bằng chứng provider-real ở các tầng khác nhau. Không sử dụng dữ liệu hợp đồng thật và không cộng các workload khác môi trường thành benchmark chung.

## Cập nhật mới nhất

- [Law Insight routing/fallback 25/09/2026](./LAW-ROUTING-FALLBACK-20260925.md): **49 stage fault mock PASS**, 30 Gateway responses/SpendLogs khớp; OCR hai trang/hai user, cả hai Proxy/LB down và recovery. Direct là SDK mock; không phải provider-real. [Evidence](../artifacts/current/law-fallback-dd3a479685ff.json).

- [Báo cáo tổng hợp API Gateway cho 4 agent](./FOUR-AGENT-API-GATEWAY-CONSOLIDATED-TEST-REPORT.md): quy trình test, identity, routing, failover/fallback, SpendLogs/ledger/billing, bằng chứng và production gate cho TLA-HĐ, Ralli AI, DMS Feedback và CRM Classification.
- [Báo cáo kỹ thuật chi tiết Ralli](./ralli-request-scope-verification.md): nguyên nhân và diff code cũ–mới, kiến trúc identity/request scope, ma trận test offline/mock/Google-real, ảnh hưởng nhiều agent, rủi ro và điều kiện production.
- [Báo cáo Gateway smoke Ralli](./RALLI-TEST-REPORT.md): fallback 20/20 stage và hồi quy SpendLogs 93/93 request trên môi trường mock.
  - Bằng chứng mock: [fallback](../artifacts/current/ralli-fallback-de282363e783.json), [hồi quy LB](../artifacts/current/ralli-lb-aedefd25d9c6.json).
  - Bằng chứng Google-real: [Gateway/fallback 6 lượt](../artifacts/current/ralli-google-de652caba3.json), [direct fallback bounded](../artifacts/current/ralli-real-fallback-6f2ce026.json).
  - Bổ sung OCR: [5/5 OCR request/SpendLogs + LB-down fail-closed/recovery](../artifacts/current/ralli-ocr-d3b5c0f18909.json), [JUnit focused suite 109/109](../artifacts/current/ralli-ocr-focused-tests-20260916.xml), [JUnit full suite 836 pass/2 thiếu snapshot](../artifacts/current/ralli-full-tests-20260916.xml), [harness OCR LB/hai Proxy](../harnesses/ralli_ocr_lb_test.py). Đây là mock upstream, không phải Google-real.
- [Báo cáo Trợ lý ảo Hợp đồng](./CONTRACT-VIRTUAL-ASSISTANT-TEST-REPORT.md): tổng hợp kết quả test, luồng hoạt động, nơi lưu dữ liệu, fault handling và phạm vi chưa nghiệm thu.
- [Retest fallback 11/09/2026](./FALLBACK-RETEST-REPORT.md): 140 focused tests PASS; fallback 20/20 stage PASS; hồi quy LB 93 request / 93 SpendLogs PASS. Không phải chứng nhận production.
- Bằng chứng mới: [fallback](../artifacts/current/law-fallback-e3cee80a23d0.json), [hồi quy LB](../artifacts/current/law-lb-815c700c6af2.json).
- Bổ sung OCR ngày 16/09/2026: [artifact hiện hành sau review, 5/5 OCR request/SpendLogs + LB-down fail-closed/recovery](../artifacts/current/law-ocr-0bb0c8d15e0c.json), [JUnit focused suite 86/86](../artifacts/current/law-ocr-focused-tests-20260916.xml), [harness OCR LB/hai Proxy](../harnesses/law_ocr_lb_test.py). Đây là mock upstream, không phải Google-real. Các artifact `law-ocr-aa17bd4e467e.json` và `law-ocr-7ca50d40fe27.json` là run lịch sử.
- [Sơ đồ logic Gateway/fallback](./gateway-architecture-diagram.html).

## Báo cáo chính

- [Kết quả kiểm thử qua Load Balancer](./LB-TEST-REPORT.md)
  - Luồng: Law Insight helper → Nginx LB → hai LiteLLM Proxy mock → SpendLogs.
  - Kết quả: 93 request, 8 username giả lập, 93 SpendLogs khớp.
  - Bao gồm kiểm tra `X-User`, failover khi một Proxy dừng và fail-closed khi LB dừng.

- [Audit identity và các đường LLM](./identity-audit.md)
  - Audit lịch sử về nguồn identity, `UsageContext`, `X-User` và các đường chat/analysis/OCR/parser.
  - Trạng thái OCR hiện hành đã được cập nhật trong báo cáo hợp nhất và các artifact ngày 16/09/2026; không dùng audit cũ để kết luận OCR vẫn bypass Gateway.

## Dữ liệu bằng chứng

- [Artifact JSON của lần chạy LB hiện hành (retest)](../artifacts/current/law-lb-815c700c6af2.json)
  - Gồm kết quả 93 request, 8 synthetic users, 93 SpendLogs, LB trace và tài nguyên sau retest 11/09.
- [Artifact JSON của lần chạy LB ban đầu (lịch sử)](../artifacts/history/law-lb-9cc2d0ed8f4f.json)
  - Lượt chạy ban đầu dùng đối soát cấu trúc SpendLogs; dữ liệu hiện hành tham chiếu bản retest ở trên.

## Phạm vi cần lưu ý

Đây không phải nghiệm thu production. TLA-HĐ và Ralli đã có authenticated OCR seam cùng actual helper qua LB/hai Proxy mock; vẫn chưa có Google-real OCR, full business persistence, ETL sang `token_ledger_v2`, dashboard reconciliation hoặc capacity production.
