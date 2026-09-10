# Báo cáo kiểm thử Law Insight qua API Gateway

Các báo cáo dưới đây được thực hiện trên môi trường mock cô lập, không gọi Google thật và không sử dụng dữ liệu hợp đồng thật.

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
