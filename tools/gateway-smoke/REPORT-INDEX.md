# Báo cáo kiểm thử Law Insight qua API Gateway

Các báo cáo dưới đây được thực hiện trên môi trường mock cô lập, không gọi Google thật và không sử dụng dữ liệu hợp đồng thật.

## Cập nhật mới nhất

- [Báo cáo kỹ thuật chi tiết Ralli](./ralli-request-scope-verification.md): nguyên nhân và diff code cũ–mới, kiến trúc identity/request scope, ma trận test offline/mock/Google-real, ảnh hưởng nhiều agent, rủi ro và điều kiện production.
- [Báo cáo Gateway smoke Ralli](./RALLI-TEST-REPORT.md): fallback 20/20 stage và hồi quy SpendLogs 93/93 request trên môi trường mock.
  - Bằng chứng mock: [fallback](./ralli-fallback-de282363e783.json), [hồi quy LB](./ralli-lb-aedefd25d9c6.json).
  - Bằng chứng Google-real: [Gateway/fallback 6 lượt](./ralli-google-de652caba3.json), [direct fallback bounded](./ralli-real-fallback-6f2ce026.json).
- [Báo cáo Trợ lý ảo Hợp đồng](./CONTRACT-VIRTUAL-ASSISTANT-TEST-REPORT.md): tổng hợp kết quả test, luồng hoạt động, nơi lưu dữ liệu, fault handling và phạm vi chưa nghiệm thu.
- [Retest fallback 11/09/2026](./FALLBACK-RETEST-REPORT.md): 140 focused tests PASS; fallback 20/20 stage PASS; hồi quy LB 93 request / 93 SpendLogs PASS. Không phải chứng nhận production.
- Bằng chứng mới: [fallback](./law-fallback-e3cee80a23d0.json), [hồi quy LB](./law-lb-815c700c6af2.json).
- [Sơ đồ logic Gateway/fallback](./gateway-architecture-diagram.html).

## Báo cáo chính

- [Kết quả kiểm thử qua Load Balancer](./LB-TEST-REPORT.md)
  - Luồng: Law Insight helper → Nginx LB → hai LiteLLM Proxy mock → SpendLogs.
  - Kết quả: 93 request, 8 username giả lập, 93 SpendLogs khớp.
  - Bao gồm kiểm tra `X-User`, failover khi một Proxy dừng và fail-closed khi LB dừng.

- [Audit identity và các đường LLM](./identity-audit.md)
  - Kiểm tra nguồn identity, `UsageContext`, `X-User` và các đường chat/analysis/OCR/parser.
  - Nêu rõ các phần đã đạt và các đường OCR/LlamaParse chưa chuyển qua Gateway.

## Dữ liệu bằng chứng

- [Artifact JSON của lần chạy LB](./law-lb-9cc2d0ed8f4f.json)
  - Gồm kết quả từng request, response ID, token, SpendLogs, LB trace và chỉ số tải thăm dò.
  - Chỉ chứa username/token mock và dữ liệu synthetic; không chứa API key hay credential.

## Phạm vi cần lưu ý

Đây là bằng chứng kiểm thử tích hợp Gateway mock, không phải nghiệm thu production. Chưa bao gồm provider Google thật, authenticated HTTP-router E2E, ETL sang `token_ledger_v2`, mapping phòng ban trên dashboard, OCR/Marker/LlamaParse đầy đủ hoặc capacity production.
