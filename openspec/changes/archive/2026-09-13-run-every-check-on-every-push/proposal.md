## Why

Repo có **62 phép kiểm tự động** và tất cả đều đạt — nhưng chúng chỉ chạy khi có người nhớ gõ lệnh.
Không có thư mục `.github/`, không có tệp cấu hình nào bảo máy chạy chúng. Đo ngày 13/09:

```
node --test tests/*.test.js                        51/51 đạt, exit 0, 9,2 giây
python -m unittest discover -s tests -p "test_*.py"  11/11 đạt, exit 0, 0,005 giây
```

Cùng lúc đó, `docker-compose.yml` trong cây làm việc đang mang dòng bind của **máy phát triển**
(`127.0.0.1`) thay vì của máy chủ (`192.168.20.111`), và chưa được commit. Ngay phía trên dòng đó
đã có chú thích in hoa "TRẢ LẠI DÒNG NÀY TRƯỚC KHI PUSH".

Chú thích đó đúng, và nó không chặn được ai. Đấy là toàn bộ lý do của change này: điều gì phải đúng
trước khi code rời khỏi máy thì phải có máy canh, không giao cho trí nhớ.

Chuyện này sắp nặng hơn chứ không nhẹ đi. Kế hoạch đưa Gateway sang một máy chủ riêng nghĩa là sẽ có
**hai** máy cùng chạy repo này. Một lần quên bind sai hôm nay là mất đường vào dashboard; cũng lỗi
đó trên hai máy thì mất thêm cả thời gian tìm xem máy nào sai.

## What Changes

- **Mỗi lần đẩy code lên đều chạy đủ 62 phép kiểm, không cần ai nhớ.** Ba nhóm chạy song song vì
  chúng độc lập: nhóm canh cấu hình, nhóm kiểm JavaScript, nhóm kiểm Python. Hỏng nhóm nào biết ngay
  nhóm đó, không phải đợi nhau.

- **Thêm một nhóm kiểm mới: canh cấu hình môi trường.** Hiện không có phép kiểm nào soi
  `docker-compose.yml`. Nhóm này bắt đúng loại lỗi mà chú thích đang phải canh bằng tay.

- **Bộ kiểm phải báo đã chạy bao nhiêu phép, không chỉ báo đạt.** Một lệnh chạy 0 phép kiểm cũng trả
  về exit 0. Đây không phải lo xa: `node --test tests/*.test.js` dựa vào việc vỏ lệnh nở được dấu
  sao; nở hụt thì lệnh vẫn xanh mà chẳng kiểm gì. Repo này đã có sẵn nguyên tắc đó trong
  `automated-check-coverage` cho bộ kiểm dữ liệu — change này áp cùng nguyên tắc cho bộ kiểm mã.

- **Giữ nguyên tính chất "chạy được mà không cài thêm gói".** Đây là một tài sản có thật, đo được:
  repo **không có** `package.json`, `pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini` hay
  `Makefile`. Phần JavaScript dùng bộ chạy kiểm có sẵn của Node. Phần Python nạp `psycopg2` **bên
  trong hàm** (`db/connect.py:196`) chứ không ở đầu tệp, nên bộ kiểm chạy được mà không cần
  PostgreSQL lẫn trình điều khiển. Tài sản này dễ mất mà không ai nhận ra — chỉ cần một người đưa
  `import psycopg2` lên đầu tệp. Change này biến nó thành một yêu cầu được canh.

**Không thuộc phạm vi change này:**

- **Đóng gói image và đẩy lên kho.** Đó là chặng 2, cần quyết định về kho chứa và về repo fork
  `litellm_tuan_test`.
- **Tự động đưa code lên máy chủ.** Đó là chặng 3, cần một runner nằm trong mạng nội bộ và cần bốn
  luật an toàn đã ghi trong `design.md`. Trong đó có một luật không được quên: **lệnh triển khai
  không bao giờ được gọi profile `tools`.**
- **Dọn `token_ledger` cũ.** Đã đo 13/09: nó giữ 5 dòng dữ liệu mà `token_ledger_v2` không có. Việc
  riêng, không dính CI.

## Capabilities

### New Capabilities

- `continuous-integration-checks`: Mỗi lần code được đẩy lên kho chung, máy phải chạy đủ bộ kiểm
  hiện có và báo rõ đã chạy bao nhiêu phép; cấu hình dành riêng cho máy phát triển không được đi
  lên nhánh chính.

## Impact

**Tệp thêm mới** — không sửa tệp nào đang có:

| Tệp | Việc |
|---|---|
| `.github/workflows/ci.yml` | tệp mới, ba công việc chạy song song |

**Tệp có thể phải sửa, tuỳ cách chọn ở `design.md`:**

| Tệp | Việc |
|---|---|
| `docker-compose.yml` | đưa địa chỉ bind của `web` thành biến, để bỏ hẳn loại lỗi này |
| `.env.example` | khai biến mới kèm chú thích |

**Không đụng tới:** `backend/`, `db/`, `scripts/`, `web/`, `tests/`. Change này chỉ thêm một lớp
canh bên ngoài; nó không đổi hành vi của hệ thống, và nếu gỡ nó đi thì mọi thứ vẫn chạy y như cũ.

**Chi phí vận hành: 19 giây** mỗi lần đẩy code, đo trên lần chạy CI #1 (commit `7d875d1`,
13/09/2026): canh cấu hình 5 giây, JavaScript 15 giây, Python 5 giây, ba nhóm song song.

Kho mã nằm ở `github.com/ursweetheart/token-ledger-dashboard`.

**Điều kiện đã xác minh 13/09:** kho là **PRIVATE** (`gh repo view --json visibility`). Điều này gỡ
nút cho chặng 3 — runner nội bộ trên một kho công khai là lỗ hổng, vì người lạ mở pull request là
chạy được mã tuỳ ý trên máy trong mạng; kho riêng tư thì không ai ngoài tổ chức làm được việc đó.
