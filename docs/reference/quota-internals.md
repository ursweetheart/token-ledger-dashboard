# Hạn mức — bản đồ mã nguồn và các quyết định đã chốt

Viết 20/09/2026. Đây là tài liệu **tham chiếu**: sửa gì thì mở file nào, vì sao
nó được làm như thế, và những chỗ đã sập một lần.

Cần biết **cách dùng** thì đọc [`quota-han-muc.md`](quota-han-muc.md). Cần biết
**lập luận đầy đủ** thì đọc `openspec/changes/stop-a-project-when-its-quota-runs-out/design.md`.

---

## 1. Một câu

Mỗi virtual key mang một hạn mức tiền trong `metadata` của chính nó; một hook
trong LiteLLM đọc hạn mức đó cùng `spend` của khoá, và từ chối request khi đã
tiêu hết.

```
   dashboard (tab Setting)
        │  POST /api/quota
        ▼
   backend  ──/key/update──▶  virtual key
   (KHONG ghi database)        metadata: {tags, quota_usd, quota_log}
                                          spend  <- LiteLLM tu cong
                                            │
   agent ──request──▶ litellm ──▶ [hook] ───┘
                                    │
                        spend >= quota_usd ?
                          │              │
                       chua het        da het
                          │              │
                      goi Google    tra loi ngay, KHONG goi Google
```

---

## 2. Sửa gì thì mở file nào

| Việc | File |
|---|---|
| Cách đọc/ghi hạn mức, gọi Gateway | `backend/gateway.py` |
| Ba endpoint `/api/quota*` | `backend/main.py` |
| Quyết định chặn, hai kiểu trả lời | `docker/gateway/quota_hook.py` |
| Nạp hook vào Gateway | `docker/gateway/config.gateway.yaml` → `litellm_settings.callbacks` |
| Gắn file hook vào container, biến `QUOTA_*` | `docker-compose.yml` → khối `x-litellm` |
| Backend lấy master key ở đâu | `docker-compose.yml` → dịch vụ `api` |
| Cảnh báo email ba bậc | `scripts/watch_quota.py`, dịch vụ `quota-watch` |
| Bảng, ba nút, lịch sử nạp | `web/js/app.js` (`renderQuota`, `quotaEditor`) |
| Lớp gọi API của frontend | `web/js/api.js` (`quotaCall`, `quotaSet`, `quotaTopUp`) |
| Tab và CSS | `web/index.html` |
| Đếm lượt chi phí 0 | `db/load_gateway.py` (`cost_zero_with_tokens`) |
| Canh bản vá fork | `.github/workflows/ci.yml` → `FORK_PATCHES` |
| Bản vá trong fork | `litellm/proxy/proxy_server.py` → `_REJECTED_STREAM_LOGGING_FALLBACK` |

Phép kiểm: `tests/test_quota_gateway.py`, `tests/test_quota_hook.py`,
`tests/test_watch_quota.py`, `tests/quota-api-calls.test.js`,
`tests/key-gate-overlay.test.js`.

---

## 3. Bảy quyết định, và cái giá của mỗi cái

**① Hạn mức nằm trong `metadata` của khoá, không nằm trong bảng riêng.**
Đổi lại: không migration, không vai database mới, không mục trong
`KEEP_ON_REBUILD`, không kết nối thứ hai cho hook, và `spend` đã được LiteLLM
cộng sẵn. Database vẫn **chỉ-đọc hoàn toàn**.

**② Không dùng `max_budget` của LiteLLM.** Nó chặn ở cửa xác thực, **trước** khi
hook chạy, và trả 400 cho mọi agent — mất khả năng trả tin nhắn giả.
Cái giá: việc chặn chỉ hoạt động khi hook được nạp. Nếu ai khai sai tên callback
thì **không gì bị chặn** mà container vẫn xanh.

**③ Hook trả về đối tượng lỗi, không trả về chuỗi.** `proxy/utils.py:1158` chỉ
đổi chuỗi thành `RejectedRequestError` khi `call_type in ["completion",
"text_completion"]`, mà đường chat truyền `"acompletion"` — trả chuỗi sẽ ra
HTTP 400.

**④ Hai kiểu trả lời, chọn theo tag.** Agent có người chat nhận 200 kèm câu
thông báo; agent chạy lô nhận 429. Tag chưa khai thì **mặc định 429** — sai kiểu
đó chỉ làm agent nghỉ, sai kiểu kia đẩy văn xuôi vào một đường phân tích JSON.

**⑤ Không dùng `mock_response`.** Nó chạy đúng ở cả hai chế độ, nhưng lượt bị
chặn vào `LiteLLM_SpendLogs` như một lượt **thành công, có token và có tiền**
(đo được: 79 token / 0,0001799 USD cho một câu thông báo, không hề gọi Google).
Đường hiện tại ghi `failure`, spend 0, token 0.

**⑥ Ba nút, mỗi nút một nghĩa cố định.** Đã cân nhắc một nút đổi nghĩa theo
trạng thái và bỏ: ranh giới giữa "cộng thêm" và "đặt lại" là lúc spend chạm
quota, mà số đó chậm tới 5 phút — cùng một thao tác cho hai kết quả, không lỗi
nào báo ra. Và ở nhánh cộng thêm, gõ `0` nghĩa là `hiện tại + 0`, tức mất luôn
cách chặn.

**⑦ Gom khoá theo TAG, không theo tên.** Tên khoá là nhãn người đặt; tag mới
quyết định tuyến và project. Bản đầu gom theo tiền tố tên và sai cả hai chiều
trên dữ liệu thật — xem mục 4.

---

## 4. Sáu cái bẫy đã sập, đừng sập lại

**`/key/update` THAY THẾ cả cục `metadata`, không gộp.**
`key_management_endpoints.py:2010` chỉ giữ metadata cũ khi yêu cầu **không**
mang `metadata`. Gửi `{"metadata": {"quota_usd": 50}}` là **xoá `tags`** — và
mất tag thì request rơi sang tuyến khác, tiền ghi sai project, mà mọi lượt gọi
vẫn trả 200. Đo 31/08 trên khoá không tag: 7/8 thành công, 1/8 lạc tuyến.
→ Mọi thao tác ghi phải **đọc – gộp – ghi lại cả cục**. Khoá lại bằng
`test_quota_gateway.py::test_the_request_body_carries_the_whole_metadata`.

**Compose truyền `${VAR:-}` thành chuỗi RỖNG, không phải vắng mặt.**
`os.getenv(name, default)` sẽ trả `""` và mặc định không bao giờ chạy. Bản đầu
của hook vì thế trả một tin nhắn **rỗng** cho người dùng. → Dùng `or`, không
dùng tham số mặc định của `getenv`.

**`RejectedRequestError` tự thêm tiền tố vào `.message`.**
`exceptions.py:556` đặt `self.message = f"litellm.RejectedRequestError: {message}"`,
mà proxy lấy đúng thuộc tính đó làm nội dung câu trả lời. Không gán lại thì
người dùng cuối đọc được tên lớp lỗi của LiteLLM.

**Ba image chép mã lúc build**: `api`, `web`, `tools`. Thêm file mới mà không
`docker compose build` thì server chạy bản cũ — tab Setting 404, watcher không
tìm thấy script.

**`/key/list` và `/key/update` KHÔNG đi qua `gateway-lb`.** nginx ở edge chỉ mở
`/v1/chat/completions` và `/health/*`; mọi đường khác trả 404. Mọi lượt gọi quản
lý khoá phải trỏ thẳng `http://litellm-1:4000`, và địa chỉ đó chỉ phân giải được
**bên trong mạng Docker**.

**Gom khoá theo tên là sai.** Trên dữ liệu thật ngày 20/09: gom `dms-feedback`
với `dms-feedback-tagged` (khoá trước không mang tag nào), và bỏ sót ba khoá
cùng tag `crm-feedback` mang ba cái tên khác nhau — tức đúng nhóm mà cảnh báo
sinh ra để chỉ.

---

## 5. Kiểm nhanh

```bash
# hook co duoc nap khong  -- KHONG ket luan tu trang thai container
docker compose logs litellm-1 | grep quota_

# nhung luot LE RA da bi chan (che do QUOTA_DRY_RUN=1)
docker compose logs litellm-1 | grep quota_block_would_have

# han muc va spend cua tung khoa
curl -s -H "Authorization: Bearer $DASHBOARD_KEY" http://127.0.0.1:8000/api/quota

# luot bi chan co lam ban so khong -- phai la failure / 0 token / 0 tien
docker compose exec -T postgres psql -U llmproxy -d litellm -c \
  'SELECT model, spend, total_tokens, status FROM "LiteLLM_SpendLogs" ORDER BY "startTime" DESC LIMIT 5;'
```

---

## 6. Ba chỗ cơ chế này KHÔNG với tới

1. **Agent chưa qua Gateway.** Hôm nay chỉ hai agent đi qua; sáu agent còn lại
   gọi thẳng Google, hạn mức của chúng chỉ là đèn báo.
2. **Đường lui của Phân Loại Dữ Liệu CRM.** Nó có `sa-key.json` để đi thẳng
   Google khi Gateway chết (change `keep-the-crm-agent-running-when-the-gateway-dies`).
   Rơi vào đường đó thì hạn mức không chạm tới được. Chưa ai quyết bỏ hay giữ.
3. **Model không có trong bảng giá của LiteLLM.** Chi phí ghi 0, nên hạn mức
   tính bằng tiền không bao giờ hết. Nối thẳng với ý định mở tuyến `*` cho agent
   tự chọn model: mở tuyến đó mà không chốt giá trước là mở một lối đi vòng.
   `db/load_gateway.py` đếm và cảnh báo số lượt như vậy.

---

## 7. Nếu bạn là agent đang sửa phần này

Bốn điều đã cân nhắc kỹ và **bỏ**. Đề xuất lại chúng là quay về một vấn đề đã
giải, nên nếu định làm thì phải có lý do mới:

- gộp ba nút thành một nút đổi nghĩa theo trạng thái → mục 3⑥
- dùng `mock_response` cho nhánh chat → mục 3⑤
- dùng `max_budget` của LiteLLM → mục 3②
- gom khoá theo tên thay vì theo tag → mục 3⑦

Hai điều **không được làm**:

- gửi `metadata` thiếu trường khi gọi `/key/update` → mục 4, bẫy thứ nhất
- kết luận hook đang chạy từ việc container `healthy` → mục 5, lệnh đầu tiên

Và một điều phải nhớ khi chạm vào fork: mỗi bản vá cần một dòng trong
`FORK_PATCHES` của CI. Bản vá `_REJECTED_STREAM_LOGGING_FALLBACK` hỏng **im
lặng** — mất nó thì container vẫn xanh, chỉ những request `stream=True` bị hạn
mức chặn mới trả HTTP 500, và chỉ người dùng thật mới gặp.
