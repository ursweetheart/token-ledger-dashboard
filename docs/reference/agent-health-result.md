# Kết quả kiểm sức khỏe agent — khuôn đầu vào và đầu ra

> Hợp đồng giữa **Module 1 (API)**, tức service `agent-health-watch`, và **Module 2 (chụp màn hình)**.
> Chốt ngày 29/10/2026, `schema_version: 1`. Bản nháp gốc: `kiem-tra-agent-hang-ngay.md`, mục 6.
> Code: `scripts/watch_agents.py`. Đổi khuôn thì tăng `schema_version` và báo bên đọc.

## 1. Luồng

```
 [lịch hằng ngày, giờ VN đặt trên tab]   [nút "Chạy ngay" trên tab]
                  └───────────────┬───────────────┘
                                  ▼      một lần chạy tại một thời điểm (database chặn)
                  service agent-health-watch (Module 1)
                  đọc config/agent-health.yaml  ──  ĐẦU VÀO
                                  │
                  gọi từng phép kiểm của từng agent
                                  │
          ┌───────────────────────┴───────────────────────┐
          ▼  sau MỖI phép kiểm                            ▼  khi lần chạy XONG
 agent_health_run.result (jsonb)            var/agent-checks/<run_id>/result.json
 cho tab trên dashboard (thanh tiến độ)     cho Module 2 đọc  ──  ĐẦU RA
```

Hai nơi chứa **cùng một tài liệu**. Tệp chỉ xuất hiện khi lần chạy đã xong. Tệp được ghi ra tệp tạm
rồi đổi tên, nên Module 2 không bao giờ đọc phải tệp viết dở.

## 2. Đầu vào: `config/agent-health.yaml`

Code không biết tên agent nào. Thêm agent là thêm một khối YAML, rồi khởi động lại service.

```yaml
version: 1
agents:
  ralli:                                  # agent_code
    name: Trợ lý ảo Ralli                 # agent_name, tên hiển thị
    base_url: https://ralliai.rangdong.com.vn:9001/api/partner/v1
    auth: {header: X-API-Key, env: RALLI_PARTNER_KEY}   # env = TÊN biến chứa key, không phải key
    kind: webapp                          # webapp | gateway-only  (Module 2 chọn cách A hay C)
    app_url: https://ralliai.rangdong.com.vn:9001       # bắt buộc khi kind = webapp
    test_identity: admin                  # tài khoản lần kiểm dùng, có thể bỏ
    allow_post: [/ctda/v2/analyze]        # mỗi POST phải được duyệt và liệt kê ở đây
    # gateway_tag: ralli                  # khi agent đi qua Gateway: thêm phép kiểm gateway-log
    checks:
      - name: capabilities                # phép kiểm HEALTH: không có `question`
        method: GET
        path: /capabilities
        expect:
          status: 200
          equals: {"features[id=ctda].enabled": true}
          days_until: {expires_at: 30}
      - name: llm                         # phép kiểm CASE: có `question`
        method: POST
        path: /ctda/v2/analyze
        question: "Phân tích ngắn tình hình chăm sóc công trình dự án tháng này"
        question_field: query            # câu hỏi được gửi trong trường này của body
        # answer: data.xxx               # đường dẫn tới câu trả lời trong response (chưa biết, xem mục 6)
        timeout: 180
        expect:
          status: 200
          equals: {status: success}
          not_equals: {data.feature: clarification}
```

| Trường | Bắt buộc | Nghĩa |
|---|---|---|
| `kind` | có | `webapp` (có giao diện chat) hoặc `gateway-only` (gọi thẳng Gateway) |
| `app_url` | khi `webapp` | địa chỉ giao diện chat, để Module 2 mở |
| `test_identity` | không | tài khoản dùng khi kiểm, để lọc khỏi số liệu người dùng thật |
| `checks[].question` | không | có thì phép kiểm là **case** (câu hỏi thật); không thì là **health** |
| `checks[].question_field` | khi có `question` | tên trường của body chứa câu hỏi |
| `checks[].answer` | không | đường dẫn tới câu trả lời trong response; dạng `a.b.c` hoặc `list[key=value].c` |
| `checks[].expect` | không | điều kiện đạt: `status`, `equals`, `not_equals`, `days_until` |

Service từ chối khởi động nếu: thiếu `kind`, `webapp` mà thiếu `app_url`, có `question` mà thiếu
`question_field`, hoặc có `POST` không nằm trong `allow_post`. Chỉ cho phép `GET` và `POST`.

## 3. Đầu ra: `var/agent-checks/<run_id>/result.json`

Ví dụ dưới là lần chạy bằng nút "Chạy ngay" ngày 29/10/2026 lúc 10:24 (số thật). `body` là chỗ giữ
nguyên response, rút gọn ở đây.

```json
{
  "schema_version": 1,
  "run_id": "9b7ca4c4-8b80-413f-b0b0-67d5f9af53c3",
  "trigger": "manual",
  "requested_by": "connection-admin",
  "started_at": "2026-10-29T10:24:37+07:00",
  "finished_at": "2026-10-29T10:24:53+07:00",
  "agents": [
    {
      "agent_code": "ralli",
      "agent_name": "Trợ lý ảo Ralli",
      "kind": "webapp",
      "app_url": "https://ralliai.rangdong.com.vn:9001",
      "test_identity": "admin",
      "status": "ok",
      "health": [
        {
          "name": "capabilities",
          "method": "GET",
          "url": "https://ralliai.rangdong.com.vn:9001/api/partner/v1/capabilities",
          "sent_at": "2026-10-29T10:24:37+07:00",
          "http_status": 200,
          "latency_ms": 124,
          "request_id": "2a69307c-6512-4350-b176-529fa0213b1b",
          "status": "ok",
          "reason": ""
        }
      ],
      "cases": [
        {
          "name": "llm",
          "method": "POST",
          "url": "https://ralliai.rangdong.com.vn:9001/api/partner/v1/ctda/v2/analyze",
          "sent_at": "2026-10-29T10:24:37+07:00",
          "http_status": 200,
          "latency_ms": 15959,
          "request_id": "9eb7161a-147b-486f-939f-32a29774a27e",
          "status": "ok",
          "reason": "",
          "question": "Phân tích ngắn tình hình chăm sóc công trình dự án tháng này",
          "expected": {"status": 200, "equals": {"status": "success"},
                       "not_equals": {"data.feature": "clarification"}},
          "answer": null,
          "body": {"status": "success", "data": {"feature": "…", "…": "…"}}
        }
      ]
    }
  ],
  "limitations": []
}
```

### Cấp lần chạy

| Trường | Kiểu | Nghĩa |
|---|---|---|
| `schema_version` | số | hiện là `1` |
| `run_id` | chuỗi UUID | cũng là tên thư mục, và là `id` trong bảng `agent_health_run` |
| `trigger` | `schedule` \| `manual` | theo lịch, hay chạy tay (nút trên tab hoặc dòng lệnh) |
| `requested_by` | chuỗi | `schedule`, `connection-admin` (nút trên tab), hoặc `cli` (dòng lệnh `--once`) |
| `started_at`, `finished_at` | ISO 8601, giờ VN `+07:00` | lúc bắt đầu, lúc xong |
| `agents` | mảng | mỗi agent một phần tử, theo thứ tự trong YAML |
| `limitations` | mảng chuỗi | điều tài liệu này không chứng minh được, ví dụ không ghi được tệp |

### Cấp agent

| Trường | Nghĩa |
|---|---|
| `agent_code`, `agent_name` | mã và tên hiển thị, chép từ YAML |
| `kind`, `app_url`, `test_identity` | chép từ YAML (mục 2) |
| `status` | mức **tệ nhất** trong các phép kiểm của agent: `fail` > `warn` > `ok` |
| `health` | các phép kiểm không có câu hỏi; **không** giữ response |
| `cases` | các phép kiểm có câu hỏi; giữ câu hỏi và nguyên response |

### Cấp phép kiểm (cả `health` và `cases`)

| Trường | Nghĩa |
|---|---|
| `name` | tên phép kiểm trong YAML |
| `method`, `url` | đã gọi gì (không bao giờ có key hay header) |
| `sent_at` | lúc gửi, giờ VN, chính xác tới giây; `null` nếu chưa gửi được (ví dụ thiếu key) |
| `http_status` | mã HTTP; `null` khi lỗi mạng hoặc timeout |
| `latency_ms` | thời gian chờ response |
| `request_id` | header `X-Request-ID` của agent, để tra cứu bên agent |
| `status` | `ok` \| `warn` \| `fail` (mục 4) |
| `reason` | lý do khi không `ok`, tối đa 500 ký tự |

Riêng `cases` có thêm:

| Trường | Nghĩa |
|---|---|
| `question` | câu hỏi nguyên văn đã gửi |
| `expected` | điều kiện đạt, chép từ `expect` trong YAML |
| `answer` | câu trả lời lấy theo đường dẫn `answer` trong YAML; `null` nếu chưa khai đường dẫn |
| `body` | nguyên response: JSON thì giữ cấu trúc, không phải JSON thì giữ dạng chữ; `null` nếu không gọi được |

Agent có `gateway_tag` thì có thêm một phần tử `health` tên `gateway-log`, với `method` và `url` là `null`.

## 4. Ba mức

| `status` | Khi nào | Gợi ý hiện trên ảnh |
|---|---|---|
| `ok` | mọi điều kiện trong `expect` đều đạt | PASS |
| `warn` | HTTP 429 (bị giới hạn request hoặc hết AI budget), hoặc ngày trong `days_until` sắp tới | CẢNH BÁO |
| `fail` | mọi thứ khác: mạng, timeout, mã HTTP sai, điều kiện sai, **thiếu biến key** | FAIL |

## 5. Quy tắc cho bên đọc (Module 2)

1. **Chỉ đọc khi tệp đã có.** Thư mục `<run_id>` mà chưa có `result.json` nghĩa là lần chạy chưa xong
   hoặc bị ngắt. Đừng đọc `result.json.tmp`.
2. **Lần chạy bị ngắt** (container chết giữa chừng) **không có tệp**. Phần đã chạy vẫn còn trong cột
   `agent_health_run.result`, với `status = interrupted`.
3. **Chọn cách chụp theo `kind`:** `webapp` → cách A, mở `app_url`; `gateway-only` → cách C.
4. **Dùng `sent_at` của case** để biết phải chờ dashboard ghi sổ tới đâu (cách C).
5. **Kết luận của Module 1 độc lập với ảnh.** Giữ nguyên `status` ở đây; kết quả chụp ghi riêng vào
   `manifest.json` của Module 2, không sửa `result.json`.
6. **Tài liệu không chứa key, JWT hay header.** Nhưng `body` là câu trả lời thật của agent, có thể là
   dữ liệu nghiệp vụ. Đừng đưa thư mục này lên git (đã có trong `.gitignore`), và đừng phục vụ nó qua
   `web/`.

## 6. Còn mở

| Việc | Ghi chú |
|---|---|
| Đường dẫn `answer` của Ralli | Tài liệu Partner API không mô tả response 200. Sẽ điền sau lần chạy đầu tiên có giữ `body`. Tới lúc đó `answer` là `null`; câu trả lời vẫn nằm trong `body`. |
| Ralli gọi qua Partner API, không qua web app | Chốt 29/10/2026. Nếu Module 2 cũng gửi câu hỏi qua giao diện (cách A) thì mỗi lần chạy có **hai** câu hỏi tới LLM. Cần thống nhất (mục 5.2.6 của bản nháp). |
| `test_identity` của Ralli là `admin` | Key hiện gắn tài khoản `admin`. Nên xin một key riêng cho lần kiểm. |
| Số token | Partner API không trả số token, nên tài liệu chưa có trường `tokens`. |
| Giữ bao nhiêu ngày | Chưa có bước tự xoá thư mục cũ. |
