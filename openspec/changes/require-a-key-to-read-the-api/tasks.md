# Tasks

## 1. Ghi mốc trước khi sửa

- [x] 1.1 Xác nhận hiện trạng: `grep -n "Depends|Authorization|api_key" backend/main.py`
      ra rỗng, 8 endpoint đều `GET`
      → **rỗng, exit 1.** 8/8 endpoint không kiểm gì. Tiền đề của change đúng
- [x] 1.2 Ghi lại: `curl` không khoá tới `/api/accounts` trả **937 dòng**. Sau change này
      cùng lệnh đó phải trả **401**
      → đo bằng cách **tái lập** hành vi cũ (`DASHBOARD_OPEN=1`) chứ không nhớ lại:
      **937 dòng, 930 dòng có họ tên thật**, không khoá. Sau change: **401**, thân trả
      lời dưới 300 byte và không chứa `full_name`
- [x] 1.3 `python backend/check_api.py` — 16/16 xanh, để so sau
      → sau change: **18/18** (16 cũ + 2 mới). Không phép kiểm cũ nào phải sửa

## 2. Backend

- [x] 2.1 `Principal` — kiểu dữ liệu nhỏ mô tả ai đang gọi (`kind`, `name`). **Trả đối
      tượng, không trả boolean**: ngày lên JWT chỉ sửa một hàm
- [x] 2.2 `nguoi_goi()` dùng `HTTPBearer`, so bằng `secrets.compare_digest`, sai → 401
      → **`auto_error=False` là bắt buộc**: mặc định `HTTPBearer` trả **403** khi thiếu
      header, không phải 401. Để mặc định thì phép kiểm 4.2 trượt vì một lý do không
      liên quan gì tới xác thực
- [x] 2.3 `Depends(nguoi_goi)` trên cả 8 endpoint. Đếm lại: 8/8, không sót cái nào
      → đếm bằng **bảng route của FastAPI**, không bằng `grep`: bản `grep` đầu tiên báo
      nhầm 2 endpoint vì regex dừng ở dấu `)` của `Query(...)`
- [x] 2.4 **Thiếu `DASHBOARD_KEY` → thoát ngay lúc khởi động**, in tên biến còn thiếu.
      Chuỗi rỗng cũng tính là thiếu
- [x] 2.5 `DASHBOARD_OPEN=1` là cửa thoát duy nhất, và in cảnh báo mỗi lần khởi động
- [x] 2.6 `.env.example` thêm `DASHBOARD_KEY=`, kèm một câu về cách sinh khoá
- [x] 2.7 **(thêm lúc làm)** `_doc_env()` — backend phải ĐỌC ĐƯỢC `.env`.
      Đo ra: **không file Python nào của backend đọc `.env`**, chỉ docker-compose và
      `scripts/pull_web_apps.py` đọc. Không có bước này thì đồng nghiệp làm đúng theo
      `.env.example` vẫn không khởi động được, và thông báo lỗi lại bảo họ dán vào `.env`
- [x] 2.8 **(thêm lúc làm — spec đòi, tasks.md sót)** `/healthz`: điểm thăm dò sống-chết,
      endpoint duy nhất không khoá, KHÔNG trả dữ liệu nghiệp vụ và không chạm database.
      Spec `api-access-control` có kịch bản *"Cần một điểm thăm dò sống-chết"* và cấm dùng
      `/api/health` cho việc đó — không có endpoint này thì kịch bản ấy không ai thoả

## 3. Frontend

- [x] 3.1 `web/js/api.js:62` gắn `Authorization: Bearer` — **điểm `fetch()` duy nhất trong
      toàn bộ `web/`**, xác nhận lại bằng `grep -rn "fetch(" web/js/` phải ra đúng 1
      → **đúng 1**
- [x] 3.2 Đọc khoá từ `localStorage`. **MUST NOT** nhận khoá qua `?key=` — tham số truy
      vấn nằm trong nhật ký máy chủ, lịch sử trình duyệt và header `Referer`
      → thêm một phép kiểm JS đọc thẳng `api.js` để bắt lối tắt này về sau
- [x] 3.3 `makeError()` thêm loại `unauthorized` cho HTTP 401, tách khỏi `endpoint-error`
- [x] 3.4 Ô nhập khoá trong `web/index.html`. Lần đầu vào: hỏi khoá trước khi gọi endpoint
      dữ liệu nào
      → `load()` chặn **trước** `fetch` đầu tiên: chưa có khoá thì không một request nào
      được bắn đi
- [x] 3.5 401 → nói *khoá không đúng*, hỏi lại. **Không dùng chung lời** với "chưa bật
      backend" — hai tình huống, hai hành động
      → ba trạng thái, ba câu: chưa nhập (xanh) · khoá sai (đỏ, xoá khoá hỏng) · chưa bật
      backend (dải `load-note` cũ)

## 4. `check_api.py`

- [x] 4.1 Đọc `DASHBOARD_KEY` và gửi kèm ở cả 16 phép kiểm
      → `from backend.main import DASHBOARD_KEY`, **không đọc lại biến môi trường**: đọc
      lại là tạo bản sao thứ hai của cùng một phép đọc cấu hình, và bản sao sẽ trôi
- [x] 4.2 Phép kiểm **mới**: gọi `/api/accounts` KHÔNG khoá phải nhận 401. Không có phép
      kiểm này thì cả bộ vẫn xanh kể cả khi xác thực bị tắt
      → thêm phép kiểm **thứ hai**: `/healthz` phải VẪN MỞ. Gắn khoá vào nó thì giám sát
      báo máy chủ chết trong khi nó đang sống. **16 → 18 phép kiểm**

## 5. Nghiệm thu

- [x] 5.1 `curl` không khoá → 401. `curl` sai khoá → 401. `curl` đúng khoá → dữ liệu
      → cả ba, trên database thật. Cùng 5 biến thể nữa ở 5b.1: Bearer rỗng · lược đồ
      `Basic` · ký tự ngoài ASCII · tham số rác không khoá · cả 8 endpoint
- [x] 5.2 **Kiểm chế độ hỏng**: bỏ `DASHBOARD_KEY` rồi khởi động — máy chủ phải **không
      chạy**. Đây là task quan trọng nhất của change; hỏng ở đây là có lỗ hổng mà tưởng đã
      khoá
      → **XONG.** uvicorn thật, ba biến thể: thiếu hẳn biến · thiếu biến + `--reload` ·
      khoá toàn khoảng trắng. Cả ba **không lắng nghe cổng nào**, và thông báo nêu đúng
      tên biến còn thiếu. Không cần Docker vì `main.py` chết trước khi chạm database
- [x] 5.3 Mở dashboard bằng khoá đúng: mọi con số **y hệt** trước change. Change này không
      đổi một con số nào
      → so **trước/sau trên cùng một máy chủ**: `/api/usage` 1.189 dòng · 867.657.110
      token · $291,985601 · `/api/accounts` 937 dòng — trùng khít, và khớp bất biến đã
      chốt sáng 21/08. `audit_db.py` vẫn 36 phép / 0 hỏng (change này không đụng `db/`)
- [ ] 5.4 `Ctrl+Shift+R` trước khi kết luận frontend đã đổi — Chrome giữ `app.js` cũ trong
      bộ đệm, bẫy này mất một vòng ngày 20/08
- [x] 5.5 `python backend/check_api.py` — **18/18** (16 cũ + 2 mới ở 4.2)
- [x] 5.6 `node --test tests/` — **6 + 11**
      → cả 4 kịch bản hỏng cũ **trượt** lúc đầu: `localStorage` giả rỗng nên `load()` dừng
      ở ô nhập khoá và không bao giờ chạm tới nhánh chúng đang kiểm. Sửa bằng cách gieo
      khoá vào harness, rồi **thêm 3 phép kiểm**: chưa nhập khoá thì không gọi endpoint
      nào · khoá sai nói riêng và bị xoá · khoá không đi qua URL · khoá của backend này
      không gửi sang backend khác

## 5b. Tự soát (skill `tu-soat`, sau khi viết xong)

- [x] 5b.1 Lát mỏng dựng uvicorn thật **không cần Docker** — đo được `backend/main.py`
      import xong mà không chạm database (`store.open_db()` chỉ chạy TRONG thân
      endpoint, còn 401 bị chặn ở tầng phụ thuộc, tức TRƯỚC thân). **24/24**
      → đã đưa vào repo thành **`tools/soat_khoa_api.py`**, không để trong thư mục tạm:
      nó là bằng chứng duy nhất cho task 5.2, và là thứ `check_api.py` **không thể**
      thay được — bộ kiểm gọi một máy chủ ĐANG chạy vẫn xanh khi ai đó gỡ mất cái chặn
- [x] 5b.2 **PHÁT HIỆN THẬT — 500 gọi được mà không cần biết khoá.**
      `secrets.compare_digest` với hai `str` ném `TypeError` khi có ký tự ngoài ASCII, nên
      `Authorization: Bearer á` làm mọi endpoint hỏng. Đã so trên `bytes`, thêm kịch bản
      vào spec, và kiểm ngược: gỡ bản sửa ra thì phép kiểm **đứt cả kết nối**
- [x] 5b.3 **PHÁT HIỆN THẬT — `?api=` biến thành đường rò khoá.**
      Tham số đó vốn chỉ đổi *chỗ đọc dữ liệu*; từ lúc trình duyệt giữ bí mật, nó đổi luôn
      *chỗ gửi bí mật*. Đã cất khoá **theo từng địa chỉ**, thêm phép kiểm, kiểm ngược:
      quay lại một-khoá-dùng-chung thì báo *"khoá đã bị gửi sang địa chỉ lạ"*
- [x] 5b.4 Ba lỗi nhỏ hơn: `.env` hỏng mã ký tự làm chết lúc import (`errors="replace"`) ·
      thông báo thiếu khoá trộn cách viết `.env` với `set` · `check_api` đoán một nguyên
      nhân trong khi có ba
- [x] 5b.5 Bốn lỗi trong **chính kịch bản soát**, sửa trước khi tin kết quả
- [x] 5b.6 **CORS preflight** — rủi ro vận hành do chính change này đẻ ra và không phép
      kiểm nào cũ chạm tới: thêm header `Authorization` biến mọi request thành
      *non-simple*, nên từ giờ Chrome gửi một `OPTIONS` đi trước mỗi lần tải trang.
      Đo tay: **8/8** — preflight qua được từ cả hai origin mặc định, `Authorization`
      được cho đi qua, preflight **không** bị tầng xác thực chặn (trình duyệt không bao
      giờ gắn khoá vào `OPTIONS`), và origin lạ vẫn bị từ chối

## 6. Tài liệu

- [x] 6.1 `viec-can-lam-truoc-api-gateway.md` — C1 và C2 đánh ✅, ghi rõ **phần chưa có**:
      không nhật ký theo người, không thu hồi được một người, không phân vai Admin/User
- [x] 6.2 `dong-bo-may-dong-nghiep-*.md` — đồng nghiệp cần `DASHBOARD_KEY`, nếu không thì
      pull về dashboard trắng
      → kèm bảng **bốn triệu chứng** và cách đọc từng cái
- [x] 6.3 Ghi lại lý do chọn khoá dùng chung: 8/8 endpoint là `GET`, 0 hành động đặc
      quyền, `account` không có cột mật khẩu. Để người sau không tưởng đây là cẩu thả
      → ghi ở **hai chỗ**: khối chú thích đầu `backend/main.py` (người sửa code đọc) và
      mục C1 của `viec-can-lam-truoc-api-gateway.md` (người đọc kế hoạch đọc)
