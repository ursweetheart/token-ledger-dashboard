## Context

Ba việc trong proposal đều được phát hiện trong lúc đo Gateway (26–27/08/2026), nhưng
không phụ thuộc lẫn nhau và không đụng vào tầng vận hành Gateway thật. Gói chung vào một
change vì cùng một lý do xuất hiện: "việc còn treo, không nằm trên đường găng" (mục 8, kế
hoạch nén). Không việc nào cần thiết kế kiến trúc mới — design.md này chủ yếu ghi lại các
quyết định kỹ thuật nhỏ để tránh làm ẩu.

Ràng buộc có sẵn cần tôn trọng: `change-the-schema-without-dropping-it` đã thiết lập luật
**migration chỉ tiến, không lùi**, và `db/rules.py` là **một bản duy nhất** dùng ở cả lúc
sinh catalog lẫn lúc nạp hoá đơn (không được sửa một bên).

## Goals / Non-Goals

**Goals:**
- `guess_model()` không còn trả `None` cho model đang thực sự được Google phục vụ
  (`gemini-3.6-flash`, xác nhận sống bằng phép đo 404 redirect chiều 26/08)
- `docs/superpowers/plans/2026-08-18-docker-packaging.md` không còn dẫn người đọc tới một
  script/đường dẫn đã xoá mà không cảnh báo
- Thư mục sao lưu cục bộ dùng đúng một định dạng ngày duy nhất, sắp xếp bảng chữ cái trùng
  sắp xếp thời gian

**Non-Goals:**
- Không sửa lại các dòng hoá đơn ĐÃ nạp trước đây mà đang mang `model_id = NULL` vì thiếu
  mapping — đó là việc backfill riêng, ngoài phạm vi
- Không thêm trước các tên model mà Google **chưa** xác nhận đang phục vụ (chỉ thêm cái đã
  đo được bằng chứng, tránh đoán mò tạo thêm dòng ánh xạ sai)
- Không đụng vào `docker/gateway/`, `.env`, hay bất kỳ thứ gì thuộc việc bật Gateway chạy
  thật — nằm ở change khác

## Decisions

**① Thêm `gemini-3.6-flash` vào `db/rules.py`, không phải chỉ vào `dim_model`.**
`dim_model` được sinh bằng máy từ `MODELS`/`MODEL_PATTERNS` qua `db/gen_catalog.py` — sửa
tay thẳng vào bảng catalog sẽ lệch với lần sinh lại tiếp theo. Sửa đúng chỗ là file quy tắc,
rồi chạy lại `gen_catalog.py`.

Thứ tự trong `MODEL_PATTERNS` phải đặt mẫu mới **trước** mọi mẫu có thể trùng một phần,
đúng quy ước đã ghi sẵn trong file ("mẫu dài hơn phải đứng trước").

**② Áp dụng vào database đang chạy: seed lại qua `gen_catalog.py`, không UPDATE tay.**
`dim_model` là dữ liệu tĩnh sinh từ file quy tắc, không phải thứ đổi cấu trúc — nên không
cần một alembic revision mới, chỉ cần chạy lại đường sinh catalog và nạp dòng mới vào
`token_ledger_v2` đang chạy bằng đúng script đã dùng để dựng những dòng hiện có (không tự
viết `INSERT` tay, tránh lệch với 10 dòng gõ máy ban đầu).

**③ `docker-packaging` plan: đọc hết rồi quyết, không sửa nửa vời.**
Kế hoạch 18/08 tham chiếu `copy_to_postgres.py` (xoá 24/08) và `var/token_ledger.sqlite`
(xoá 17/08) — cả hai chỉ là triệu chứng. Câu hỏi thật là: kiến trúc nó mô tả (theo Master
Plan gốc, có thể gồm 2 server vật lý) có còn khớp với kế hoạch nén 30/09 không (kế hoạch
nén đã tự cắt "2 máy server" xuống "1 máy, 2 instance container" — mục 5). Nếu kiến trúc đã
bị kế hoạch nén thay thế, đánh dấu **lỗi thời**, không xoá (giữ lịch sử như quy ước dự án
đang làm với các nhật ký dated khác), thêm dòng đầu file trỏ sang
`ke-hoach-nen-thang-9-2026.md`.

**④ Đổi tên thư mục backup: `grep` trước, đổi sau.**
Trước khi đổi tên, quét toàn repo (script, doc) tìm chuỗi `2026-26-08` — nếu có chỗ nào
tham chiếu tên cũ thì phải sửa cùng lúc, không để lại đường dẫn chết.

## Risks / Trade-offs

- [Rủi ro] Nạp dòng `dim_model` mới vào `token_ledger_v2` bằng tay, ngoài lịch sử migration
  → **Giảm**: dùng lại đúng script `gen_catalog.py` từng dựng 10 dòng hiện có, không viết
  `INSERT` tay mới; ghi lại trong `tasks.md` chạy lệnh gì, kết quả so sánh trước/sau
- [Rủi ro] Đánh dấu `docker-packaging` lỗi thời trong khi thực ra vẫn còn phần dùng được
  → **Giảm**: đọc hết 899 dòng trước khi quyết, không chỉ nhìn hai chỗ tham chiếu bị hỏng
- [Rủi ro] Đổi tên thư mục sao lưu nhưng bỏ sót một script/doc còn gọi tên cũ
  → **Giảm**: `grep -r "2026-26-08"` trước khi đổi, coi kết quả 0 là điều kiện để tiến hành
- [Đánh đổi] Không backfill các dòng hoá đơn cũ đã mất model — chấp nhận nợ đó lại, vì
  phạm vi hôm nay là chặn mất mát MỚI, không phải sửa mất mát ĐÃ xảy ra

## Migration Plan

1. Đổi tên thư mục backup (không phụ thuộc gì, làm trước, ít rủi ro nhất)
2. Sửa `db/rules.py`, chạy `gen_catalog.py`, so sánh `db/02_catalog.sql` trước/sau bằng
   diff, rồi áp catalog mới vào `token_ledger_v2` đang chạy
3. Đọc và quyết định số phận `docker-packaging` plan, sửa/đánh dấu tương ứng

Không có bước rollback đặc biệt: (1) là đổi tên thuần, lùi được bằng đổi tên ngược; (2) chỉ
thêm dòng vào bảng tĩnh, không xoá gì đang dùng; (3) chỉ sửa văn bản.

## Open Questions

- Ngoài `gemini-3.6-flash`, còn model nào khác đã xác nhận sống mà `MODELS` chưa có không —
  hay phạm vi chỉ dừng ở đúng một model đã có bằng chứng đo (404 redirect, mục 6/16.7 nhật
  ký 26/08)?
- `docker-packaging` plan: quyết định cuối (còn sống / lỗi thời) cần xác nhận từ anh Tuấn
  trước khi sửa file, hay agent tự đọc và tự quyết theo bằng chứng ở bước 3?
