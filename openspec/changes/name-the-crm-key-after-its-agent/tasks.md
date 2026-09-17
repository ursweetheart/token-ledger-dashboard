## 0. Xác minh bản đồ khoá bằng đo, trước khi gõ

Ngày 17/09/2026 bản đồ này đã bị đọc ngược một lần trong lúc bàn. Đổi tên theo bản đồ sai thì hai
khoá hoán vị nhau, hai tuyến **vẫn trả `200`**, và tiền rơi sai project. Không phép kiểm nào hiện có
bắt được. Nên mục này đứng trước mọi mục khác.

- [x] 0.1 Đọc **tiền tố và độ dài** của cả hai khoá trong `.env` (chỉ tiền tố, không in giá trị, không
      ghi ra tệp). Xác nhận `KEY_BENCH_CRM_TEST_GG_AIA_STU` là dạng `AQ.` — Vertex express, đúng loại
      tuyến `gemini-2.5-flash` cần

      17/09/2026: cả hai khoá `AQ.` / 53 ký tự → **cùng là Vertex express**. Băm khác nhau
      (`f91680b6` và `73182a0f`) → **hai khoá riêng biệt**, không phải một khoá dán hai tên. Khớp
      phép đo 10/09
- [x] 0.2 Đọc `config.gateway.yaml` và ghi lại bản đồ đang có, dạng bảng `khoá → tuyến → nhãn`. Đối
      chiếu với `dim_agent.code`: nhãn `crm-feedback` là agent 7 "Phân Loại Dữ Liệu CRM"

      ```
      KEY_BENCH_CRM_TEST_GG_AIA_STU -> gemini-2.5-flash  -> ["crm-feedback"] -> agent 7
      KEY_GOOGLE_AI_STU             -> gemini-flash-lite -> ["dms-feedback"] -> agent 6
                                    -> gemini-flash, gemini-flash-preview  (khong nhan)
      ```

      `dim_agent` xác nhận: 7 = `crm-feedback` = "Phân Loại Dữ Liệu CRM", 6 = `dms-feedback` =
      "Phân Loại Phản Hồi Tiếp Thị"
- [x] 0.3 ~~Gọi **một** lượt thật qua tuyến `gemini-2.5-flash` bằng chìa khoá ảo của CRM.~~ Xem dòng
      trong `LiteLLM_SpendLogs` mang nhãn `crm-feedback`. Đây là bằng chứng cuối: khoá sắp đổi tên
      phục vụ đúng agent CRM

      **Không gọi lượt mới — hỏi sổ, miễn phí và bằng chứng mạnh hơn.** Sổ đã ghi mọi lượt gọi
      trong quá khứ:

      ```
      gemini/gemini-2.5-flash + ["crm-feedback"]   100 dong   09/09 -> 12/09
      ```

      100 lượt thật đã đi qua đúng tuyến dùng `KEY_BENCH_CRM_TEST_GG_AIA_STU`. Một trăm điểm dữ liệu
      hơn hẳn một lượt gọi mới, và không tốn đồng nào
- [x] 0.4 Ghi kết quả 0.1–0.3 vào `design.md` mục Context. Bản đồ sai thì **dừng change**, mở lại
      cuộc bàn — đừng sửa tên theo bản đồ chưa xác nhận — **bản đồ ĐÚNG**, change chạy tiếp
- [x] 0.5 **Ngoài phạm vi nhưng trả lời được miễn phí:** câu treo ở D3 — ai gọi
      `gemini-flash-preview`? Đã hỏi sổ. Xem D3, mục "Đã trả lời 17/09/2026"

## 1. Đổi tên — MỘT commit, năm tệp

Chia nhỏ mục này là tái hiện sự cố 10/09 (D2). Cả năm tệp trong cùng một commit.

- [x] 1.1 `.env.example:73-79`: tên mới, và viết lại chú thích. Bỏ đoạn giải thích hậu tố
      `_GG_AIA_STU` gây hiểu nhầm (hậu tố ấy không còn), **giữ** sự thật đã đo: khoá này là Vertex
      express, tiền tố `AQ.`, và tuyến `gemini-2.5-flash` cần đúng loại đó
- [x] 1.2 `docker-compose.yml:133`: `KEY_CRM_FEEDBACK: ${KEY_CRM_FEEDBACK:-}`. Giữ `:-`, KHÔNG đổi
      sang `:?` — compose nội suy biến cho cả tệp trước khi lọc profile, nên `:?` làm
      `docker compose up -d` của dashboard gãy theo trên máy không có `.env`
- [x] 1.3 `docker-compose.yml:121-132`: viết lại khối chú thích. Đoạn "TEN BIEN DOI 10/09/2026" kể
      một lần đổi tên trước đó — thay bằng lần này, giữ nguyên bài học: `${...:-}` biến khoá thiếu
      thành chuỗi rỗng và tuyến chết im lặng
- [x] 1.4 `docker/gateway/entrypoint.sh:16`: đổi tên trong vòng `for v in …`. Đếm lại: danh sách
      phải còn đúng 6 biến
- [x] 1.5 `docker/gateway/config.gateway.yaml:86`: `api_key: os.environ/KEY_CRM_FEEDBACK`. **Đây là
      tệp sót thì hỏng im lặng.** Sửa xong `grep` lại toàn tệp, tên cũ phải ra 0
- [x] 1.6 `docker-compose.bench.yml:45`: tên mới, giữ giá trị cố ý sai. Bench dùng chung
      `entrypoint.sh`, nên mọi biến trong vòng kiểm phải có giá trị giả tương ứng ở đây
- [x] 1.7 `grep -rn KEY_BENCH_CRM_TEST` toàn kho, loại trừ `docs/decisions/`, `docs/archive/`,
      `openspec/changes/archive/`. Kết quả phải là 0. Ba thư mục ấy là lịch sử, giữ nguyên
- [x] 1.8 Sửa `.env` trên máy phát triển: đổi tên biến, **giữ nguyên giá trị**

## 2. Nghiệm thu — một lượt gọi thật, không chỉ healthcheck

Chế độ hỏng của mục 1 không làm container chết. Nên `ps` xanh và `/health/liveliness` trả `200`
MUST NOT được coi là bằng chứng.

- [x] 2.1 Dựng lại hai instance LiteLLM (xem mục 3), đợi cả hai `healthy`
- [x] 2.2 Kiểm cửa chặn khởi động còn hoạt động: tạm bỏ trống `KEY_CRM_FEEDBACK` trong `.env`, dựng
      lại một instance, xác nhận nó **không lên** và in `STOP: KEY_CRM_FEEDBACK is missing.`. Trả
      giá trị lại ngay
- [x] 2.3 **Gọi một lượt thật** qua tuyến `gemini-2.5-flash` ~~bằng chìa khoá ảo của CRM~~ → `200`.
      Đây là phép kiểm duy nhất phân biệt được "đổi tên đủ năm chỗ" với "sót `config.gateway.yaml`"

      17/09/2026: **`200`**, trả về `"OK"`, 7 token. Phản hồi mang `vertex_ai_grounding_metadata` và
      `vertex_ai_safety_results` → xác nhận đi đúng đường **Vertex express**, khớp loại khoá đo ở
      0.1. Sót `config.gateway.yaml` thì đây đã là `500 "Missing Gemini API key"`.

      **GIỚI HẠN — dùng MASTER KEY, không phải chìa khoá ảo.** `.env` không có chìa khoá ảo nào, và
      LiteLLM chỉ lưu mã băm nên không lấy lại được chuỗi `sk-…` đã cấp. Nên phép kiểm này **chưa**
      chứng minh đường đi qua chìa khoá ảo của agent. Muốn chứng minh thì phải cấp khoá mới
- [x] 2.4 Xem dòng mới trong `LiteLLM_SpendLogs`: nhãn `crm-feedback`, `model` là
      `gemini/gemini-2.5-flash`, `attempted_retries = 0`

      ```
      el6raqffH8-pr8kPwNDvwA4 | gemini/gemini-2.5-flash      | ["crm-feedback", "User-Agent: Wget"]
      iV6rauXrEve-1e8P-dzb-Q0 | gemini/gemini-3.5-flash-lite | ["dms-feedback", "User-Agent: Wget"]
      ca hai: status=success, attempted_retries=0, end_user=svc.nghiem-thu-doi-ten-17-09
      ```

      Cột `model` là **tên upstream**, không phải bí danh → tuyến giải đúng. `attempted_retries = 0`
      → không có lớp thử lại nào che mất lỗi định tuyến.

      **Hai dòng test này lẫn vào số liệu thật của agent 6 và 7** (15 token tổng). Tách được bằng
      `end_user = 'svc.nghiem-thu-doi-ten-17-09'` — lưu lượng thật mang `svc.crm-feedback` /
      `svc.dms-feedback`. Đặt `X-User` riêng là có chủ ý, để hai dòng này loại được sau
- [x] 2.5 Không hồi quy tuyến DMS: gọi một lượt qua `gemini-flash-lite` ~~bằng chìa khoá ảo của
      DMS~~ → `200`, nhãn `dms-feedback`. Change này không đụng tới nó, và đây là cách chứng minh —
      17/09/2026: **`200`**, `"OK"`, 8 token, nhãn `dms-feedback`, model giải đúng thành
      `gemini/gemini-3.5-flash-lite`. Cùng giới hạn master key như 2.3
- [x] 2.6 Chạy bộ nạp, xác nhận `dropped_no_tag` và `dropped_many_tags` không tăng

      Chạy `--dry-run` trước, rồi mới chạy thật. Cả hai cho cùng kết luận:

      ```
      dropped: nothing - every source row in range was loaded
      model not declared 0 | failed before routing 0
      inserted 2 | overwritten 60
      ```

      **`dropped_no_tag` và `dropped_many_tags` đều 0.** Nhãn `crm-feedback` / `dms-feedback` quy
      được về agent.

      Đối chiếu toàn sổ khớp chính xác sau khi nạp:

      ```
      nguon  567 dong / 235.984 token
      dich   483 dong / 234.260 token      (truoc khi nap: 481 / 234.245)
      bo qua  84 dong /   1.724 token
      483 + 84 = 567 ✓     +2 dong, +15 token = dung 7 + 8 cua hai luot test ✓
      ```

      **`identity unresolvable 2` — hai dòng test, KHÔNG phải lỗi.** `end_user`
      `svc.nghiem-thu-doi-ten-17-09` không có trong danh bạ, nên `load_gateway.py:383` cho chúng rơi
      về **tài khoản neo** của agent thay vì bịa một tài khoản. Dòng vẫn vào sổ, chỉ không quy được
      về người dùng cụ thể. Đúng như thiết kế
- [x] 2.7 **Hai dòng nghiệm thu: GIỮ NGUYÊN.** Chốt bởi lead 17/09/2026.

      Chúng nằm trong `fact_call`, gắn vào tài khoản neo của agent 6 và 7:

      ```
      el6raqffH8-pr8kPwNDvwA4   agent 7   7 token   2026-09-17 10:28:46
      iV6rauXrEve-1e8P-dzb-Q0   agent 6   8 token   2026-09-17 10:29:11
      ```

      Tổng 15 trên 234.260 token = **0,006%**.

      Hai phương án đã cân và bỏ:

      | Bỏ vì |
      |---|
      | Xoá 2 dòng khỏi `LiteLLM_SpendLogs` rồi nạp lại — **xoá dòng khỏi một sổ kiểm toán** tệ hơn giữ một dòng test tự khai danh |
      | Thêm `svc.nghiem-thu-doi-ten-17-09` vào danh bạ — bịa một tài khoản không có thật, để làm tắt một cảnh báo đang nói đúng |

      **Cách tách chúng khi cần:** `end_user = 'svc.nghiem-thu-doi-ten-17-09'` trong
      `LiteLLM_SpendLogs`, hoặc hai `call_id` ở trên trong `fact_call`. Lưu lượng thật của agent mang
      `svc.crm-feedback` / `svc.dms-feedback`, không trùng

## 3. Triển khai

- [x] 3.1 **Dựng lại, không `restart`.** Biến môi trường chỉ đặt được lúc tạo container:
      `docker compose --profile gateway up -d litellm-1`, đợi `healthy`, rồi `litellm-2`
- [x] 3.2 Không `down`, không `--remove-orphans` — theo
      `docs/reference/luat-trien-khai-tu-dong-13-09.md`
- [x] 3.3 ~~`docker compose --profile gateway restart gateway-lb` sau cùng~~ — **ĐÃ BỎ**, vì
      `keep-the-load-balancer-pointed-at-live-instances` đã xong trước.

      Và lần triển khai này là bằng chứng thật cho change ấy: `litellm-2` **đã đổi IP** `.9` → `.8`
      khi dựng lại — không ai chiếm chỗ, chỉ vì dải địa chỉ đã xê dịch. Kết quả: chia tải **10/10**,
      `gateway-lb` vẫn `Up 20 minutes`, không ai động vào nó.

      Số đo này đã được ghi ngược lại vào `design.md` D7 của change kia, vì nó **sửa một kết luận
      sai** ở đó: "dựng lại container không đổi IP" chỉ đúng khi địa chỉ cũ còn trống
- [x] 3.4 Bench: ~~`docker compose -f docker-compose.bench.yml` lên được~~, xác nhận 1.6 không sót

      **Chỉ kiểm nội suy cấu hình, KHÔNG khởi động bench.** `docker compose -f docker-compose.yml -f
      docker-compose.bench.yml --profile bench config` nội suy sạch, và `litellm-bench` nhận
      `KEY_CRM_FEEDBACK: KHONG-PHAI-KHOA-THAT-bench-khong-duoc-goi-ra-ngoai`. Đủ để chứng minh 1.6
      không sót; **chưa** chứng minh bench chạy được đầu-cuối.

      Ghi thêm một điều tự lộ ra: bench **không chạy một mình được** — `litellm-bench` phụ thuộc
      `postgres` định nghĩa ở tệp compose chính, nên phải nạp **cả hai tệp**. Chạy
      `-f docker-compose.bench.yml` một mình thì báo `depends on undefined service "postgres"`

## 4. Phép canh trong CI

- [x] 4.1 Viết phép canh theo D4: mọi `os.environ/KEY_*` trong `config.gateway.yaml` phải có mặt ở cả
      ba nơi — vòng kiểm của `entrypoint.sh`, khối `x-litellm` của `docker-compose.yml`, và
      `docker-compose.bench.yml`. ~~Chỉ thư viện chuẩn của Python~~, mã thoát 0/1

      **Shell nội tuyến, không phải Python** — cùng lý do như change
      `keep-the-load-balancer-pointed-at-live-instances`: cả nhóm `guards` là `grep`/`sed` đặt thẳng
      trong `ci.yml`, không tệp Python nào
- [x] 4.2 Phép kiểm cho phép canh: một cặp đạt/hỏng cho mỗi trong ba nơi; và một ca `api_key` là
      chuỗi ghi thẳng (không có tiền tố `os.environ/`) phải **báo hỏng** — bí mật không được nằm
      trong tệp cấu hình

      Bốn ca, dựng từ bản sao cây thật rồi làm hỏng từng chỗ một:

      | Ca | Kết quả |
      |---|---|
      | `su-co-10-09` — config đổi tên, ba tệp kia giữ tên cũ | ✅ báo **cả ba** chỗ thiếu |
      | thiếu ở `docker-compose.yml` | ✅ báo đúng một chỗ |
      | thiếu ở `docker-compose.bench.yml` | ✅ báo đúng một chỗ |
      | `api_key` ghi thẳng khoá vào config | ✅ báo, kèm số dòng |
- [x] 4.3 Chạy phép canh trên cây đã sửa → 0 vi phạm. Dựng lại tình huống 10/09 ~~trên nhánh tạm~~
      (đổi `config.gateway.yaml` sang một tên không có trong `entrypoint.sh`) → phép canh phải đỏ.
      Không có bước này thì không biết phép canh bắt được gì

      Dựng lại trong **thư mục nháp**, không đụng cây thật, không cần nhánh tạm. Cây thật mã thoát
      `0`; ca `su-co-10-09` mã thoát `1`
- [x] 4.4 Thêm bước vào nhóm `guards` của `.github/workflows/ci.yml`; ~~tăng `EXPECTED_PY`~~ — không
      có phép kiểm Python nào thêm nên giữ nguyên.

      **Đã kiểm bản trích ngược từ YAML**, không chỉ bản nháp: trích khối `run:` ra tệp rồi chạy lại
      cả năm hướng → cây thật `0`, bốn ca thử `1`, trùng khít bản nháp
- [x] 4.5 Ghi mã lần chạy CI đỏ có chủ ý ở 4.3, xoá nhánh tạm

      17/09/2026, nhánh `ci-red-check`, PR nháp #18 vào `main`:

      ```
      lan chay 35180755339      Canh cau hinh:       failure
                                buoc do: "Every provider key the gateway config
                                          uses must be declared everywhere"
                                Gateway image:        skipped
      ```

      Dựng lại đúng hình dạng sự cố 10/09: `config.gateway.yaml` tham chiếu `KEY_BENCH_CRM_TEST`,
      biến không có ở cả ba nơi. CI in đủ **ba** câu `::error::`, mỗi nơi một câu.

      **Phải hai lần chạy**, vì hai phép canh nằm cùng job `guards`: cái đầu đỏ thì job dừng, cái
      sau không tới lượt. Lần chạy của phép canh kia là `35180632930` — xem
      `keep-the-load-balancer-pointed-at-live-instances` ô 3.5.

      PR đóng, nhánh xoá cả local lẫn remote, `git fetch --prune` xác nhận sạch

## 5. Tài liệu và bàn giao

- [x] 5.1 Sửa tên trong tài liệu đang dùng: `docs/reference/fallback-crm-12-09.md`,
      ~~`docs/reference/gateway-architecture-and-agent-integration.md`~~. Không sửa
      `docs/decisions/`, `docs/archive/`, `openspec/changes/archive/`

      `fallback-crm-12-09.md`: đổi tên, kèm một khối trích dẫn nói rõ vì sao — hai dòng đo ngay trên
      đó (`aiplatform` → 200, `generativelanguage` → 403) chính là bằng chứng hậu tố cũ nói ngược.

      `gateway-architecture-and-agent-integration.md`: **không phải sửa.** Nó chỉ nhắc
      `KEY_GOOGLE_AI_STU` (dòng 295), biến không nằm trong phạm vi change này. Bản `tasks.md` liệt kê
      nó là **thừa** — viết lúc chưa `grep`
- [x] 5.2 Ghi một dòng bàn giao: máy nào đang chạy Gateway phải sửa `.env` khi nhận commit này; chế
      độ hỏng là "không chạy", thông báo nêu đúng tên biến — mục 7 của
      `docs/reference/dung-lai-instance-gateway.md`, kèm bảng tên cũ → tên mới và nguyên văn câu
      `STOP:` sẽ thấy
- [x] 5.3 Ghi lại câu hỏi còn treo cho `KEY_GOOGLE_AI_STU` (D3): `gemini-flash-preview` có ai gọi
      không, nhãn gì. Kèm luôn ràng buộc đơn giá bản preview chưa chốt

      **Câu hỏi đã có đáp án, không còn treo** — xem D3 mục "Đã trả lời 17/09/2026". 17 dòng, 170
      token, master key, 63 giây của một ngày, không agent nào dùng. Ràng buộc đơn giá bản preview
      **vẫn còn** và vẫn phải chốt trước khi có agent dùng thật
- [x] 5.4 `openspec validate name-the-crm-key-after-its-agent --strict` đạt
