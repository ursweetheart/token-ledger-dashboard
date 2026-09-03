# Quy ước log — chốt 01/09/2026

Trước hôm nay, `docker compose logs` đổ ra hai phong cách nằm cạnh nhau: bốn thành phần bên thứ
ba viết tiếng Anh có nhãn thời gian và có mức, còn mã của ta viết tiếng Việt không dấu, tự chế
định dạng, không có mức nào.

Change: `speak-one-language-in-the-container-logs`.

---

## 1. Đường kẻ: **ai đọc** quyết định ngôn ngữ, không phải file nào chứa nó

Quy ước cũ nói *"định danh tiếng Anh, ghi chú tiếng Việt"* và *"không dấu chỉ dành cho file cấu
hình"*. Log **không thuộc loại nào** — nó là đầu ra chạy thật.

Chỗ này từng gây nhầm. Cùng một sự việc *"database chưa có dữ liệu"* hiện ở **ba** nơi:

```
   web/js/app.js      man hinh dashboard    NGUOI DUNG CUOI   -> Viet CO DAU, GIU NGUYEN
   web/js/api.js      console trinh duyet   nguoi phat trien  -> Anh
   backend/check_api  terminal / docker     nguoi van hanh    -> Anh
```

**Quy tắc chốt:**

| Ai đọc | Ngôn ngữ | Ví dụ |
|---|---|---|
| Người dùng cuối, trên màn hình | **Tiếng Việt có dấu** | `web/`, ô lỗi trên dashboard |
| Người vận hành, qua `docker logs` | **Tiếng Anh** | `scripts/`, `db/`, `backend/`, `docker/*.sh` |
| Lập trình viên, đọc mã | **Tiếng Việt có dấu** | chú thích trong mã |

Hệ quả: `web/` **không nằm trong phạm vi**, dù nó cũng đầy tiếng Việt. Đã kiểm bằng
`git diff --stat web/` — rỗng.

**Hai thứ KHÔNG phải chữ của log, nên giữ nguyên tiếng Việt:**

- **Dữ liệu.** `agents with an 'app' source: Trợ Lý Ảo Hợp Đồng, Trợ lý ảo Ralli` — tên agent
  lấy từ `dim_agent.name`. Dịch nó là sửa dữ liệu.
- **Giá trị tra cứu.** `could not find the 'Khong xac dinh' entry` — chuỗi đó là khoá có thật
  trong file nguồn của Ralli.

## 2. Nút vặn phải là BIẾN MÔI TRƯỜNG, và có HAI ranh giới khác nhau

Pipeline lồng ba tầng bằng `subprocess`, mỗi tầng một tiến trình riêng. Tham số hàm ở tầng cha
**không** làm tầng cháu im bớt.

```
   may that ──[1]──▶ container ──[2]──▶ tien trinh con ──[2]──▶ tien trinh chau

   [1] KHONG tu dong.  Compose noi suy `.env` cho CHINH FILE compose, khong bom
                       bien vao container. Phai khai TUONG MINH:
                           LOG_LEVEL: ${LOG_LEVEL:-INFO}
                       trong `environment:` cua `tools` va `api`.
   [2] TU DONG.        `subprocess.run()` ke thua `os.environ`.
```

Đây là chỗ dễ tưởng nhầm nhất, và bản đầu của thiết kế đã tưởng nhầm.

Đo thật, ranh giới [2] hoạt động:

```
   LOG_LEVEL=INFO     rebuild_db in 70 dong (ca 8 tien trinh con)
   LOG_LEVEL=WARNING  rebuild_db in 17 dong
```

## 3. Ba loại nội dung, chỉ một loại được cắt

```
   ①  TIEN DO      "[4/9] pull Ralli + TLA HD"                -> cat bot duoc
   ②  SO DO DUOC   "billing 1012 | monitoring 606 | app 371"  -> PHAI GIU o INFO
   ③  PHAT HIEN    "42 checks | 38 passed | 4 notes"          -> PHAI GIU o INFO
```

Loại ② và ③ là **lý do người ta đọc log**. Đẩy chúng xuống `DEBUG` là làm mù chính công cụ
soát của mình. Change này chỉ đổi ngôn ngữ, **giữ nguyên cấu trúc và con số**.

Nghiệm thu bằng cách chụp mốc trước khi sửa (`var/so-do-truoc-khi-doi.txt`, 24 dòng số đo) rồi
đối chiếu: **42 con số riêng biệt, mất 0**.

## 4. LOG khác BÁO CÁO — `audit_db.py` giữ `print`

Phát hiện lúc triển khai, không có trong thiết kế ban đầu.

```
   LOG      dong su kien, co thoi diem, loc duoc theo muc
   BAO CAO  ket qua mot lan chay, doc nhu mot bang
```

Cho khối 42 phép kiểm đi qua logger thì mỗi dòng bảng mang một nhãn thời gian:

```
   2026-09-02 15:54:16  INFO   [  ok  ] Foreign keys (23 relations)
```

Đó là **kém chuyên nghiệp hơn**, không phải hơn. `pytest`, `eslint`, `terraform plan` đều không
đóng dấu thời gian lên từng dòng báo cáo.

Nên `audit_db.py` giữ `print` cho khối báo cáo, chỉ đổi sang tiếng Anh. Đó là **đầu ra của công
cụ**, không phải log của nó.

## 5. Định dạng: đi theo cái đã có, nhưng KHÔNG có sẵn cái để bắt chước

Bản đầu của thiết kế viết *"bốn thành phần bên thứ ba đều dùng thời gian – mức – nội dung"*.
**Nói quá.** Đo thật:

```
   litellm     17:15:02 - LiteLLM:WARNING - …      co MUC, gio KHONG co ngay
   uvicorn     INFO:     127.0.0.1 - "GET …"       co MUC, KHONG co thoi gian
   nginx       172.20.0.5 - - [31/Aug/2026:…]      co thoi gian, KHONG co muc
```

Chọn dạng đầy đủ nhất, vì nó là thứ **duy nhất đọc được khi ba luồng trộn vào nhau**:

```
   2026-09-02 16:04:58  INFO   [7/8] Usage rollup  (build_usage_daily.py)
```

**Giờ Việt Nam ép cứng**, không dùng giờ cục bộ: container chạy UTC còn máy dev chạy giờ VN, để
mặc định thì cùng một pipeline ghi hai mốc giờ khác nhau tuỳ chạy ở đâu.

**Không màu.** Không phải suy đoán — log LiteLLM đã dẫm phải:

```
   ^[[92m17:15:02 - LiteLLM:WARNING^[[0m: utils.py:2907 - register_model…
   ^^^^^^^                          ^^^^^   ma ANSI lot thang vao docker logs
```

## 6. `db/logs.py` chứ không phải `db/logging.py`

`db/` **không phải package** — không có `__init__.py`. Các script nối vào bằng:

```python
   sys.path.insert(0, str(ROOT / "db"))     # scripts/rebuild_db.py:81
```

`insert(0, …)` đặt `db/` **lên đầu** đường tìm module. Một file tên `db/logging.py` sẽ **che
khuất `logging` của thư viện chuẩn** trong mọi tiến trình nối vào `db/`, và hỏng theo kiểu khó
lần nhất: `import logging` vẫn thành công, chỉ là nhập nhầm file.

**Đây là ràng buộc, không phải sở thích đặt tên.**

## 7. Hai thứ CỐ Ý không làm nhẹ đi

- **Băng-rôn `DASHBOARD_OPEN`** giữ nguyên hai hàng `!` và giữ `stderr`. Nó chỉ in khi máy chủ
  đang chạy **không xác thực**, và khi đó ai gọi `/api/accounts` cũng lấy được 937 họ tên kèm
  phòng ban. Đây là cảnh báo an toàn, không phải log tiến độ.
- **Thông báo thiếu `DASHBOARD_KEY`** giữ nguyên độ dài và ba biến thể lệnh cmd/PowerShell/bash.
  Nó dài vì nó **dạy người đọc cách sửa**, và người gặp nó đang bị chặn.

## 8. Xoay vòng log

```yaml
   x-logging: &logging
     driver: json-file
     options: { max-size: "10m", max-file: "3" }
```

Trước đó **không cấu hình gì**, tức `json-file` **không giới hạn**: file log lớn dần mãi trên ổ
đang chứa `pgdata` — cả `token_ledger_v2` lẫn sổ Gateway.

Đặt ở khối `x-` dùng chung cho **13 dịch vụ**, không chép 13 lần. Có tiền lệ ngay trong file:
`x-litellm: &litellm` ở dòng 36.

---

## 9. Nghiệm thu

```
   print()            238 -> 150   (150 con lai deu la BAO CAO hoac da tieng Anh)
   ke ngang 72 ky tu   42 -> 0
   rebuild_db in ra          70 dong (truoc: 70 dong khung + noi dung)
   dong so do           mat 0/42 con so
   dong tieng Viet      0
   audit               42 checks | 38 passed | 4 notes | 0 failed
   doi soat moc        24/24 khoa KHOP, 0 lech
   web/                KHONG bi dung mot dong nao
   xoay vong           json-file max-size=10m max-file=3 tren container that
```

## 10. Còn chưa chắc

| | Mức |
|---|---|
| Không mất dòng số đo nào | **Chứng minh được** — 42/42 con số còn nguyên |
| Không hồi quy dữ liệu | **Chứng minh được** — 24/24 khoá mốc sau khi dựng lại từ đầu |
| Thứ tự dòng cha/con vẫn đúng | **Chứng minh được** — ép hỏng, traceback nằm đúng sau tiêu đề bước |
| Nút vặn truyền xuống tiến trình con | **Chứng minh được** — 70 dòng ở INFO, 17 ở WARNING |
| Các script `pull_*` in ra đúng | **Chỉ suy luận** — chúng gọi mạng thật, chưa chạy được lần nào |
| `max-size: 10m` có đủ không | **Chỉ ước lượng** — chưa đo `api` ghi bao nhiêu mỗi ngày |
