"""Kiểm API: đối chiếu với database, và đối chiếu SQLite <-> PostgreSQL.

    # mở máy chủ trước, ở một cửa sổ khác:
    python -m uvicorn backend.main:app --port 8000

    python backend/check_api.py
    python backend/check_api.py --compare http://127.0.0.1:8001

BỐN VIỆC NÀY KIỂM
-----------------
1. API trả đúng số mà database có. Không phải "trả về 200 là xong" - một
   endpoint trả bảng rỗng cũng trả về 200.
2. Tham số rác bị từ chối bằng 400, không âm thầm trả bảng rỗng. Bảng rỗng là
   cách nguy hiểm nhất để báo lỗi, vì nó trông y hệt "kỳ này không có dữ liệu".
3. Xác thực THẬT SỰ bật. Gọi không khoá phải nhận 401. Mọi phép kiểm khác đều
   GỬI khoá, nên chúng vẫn xanh y nguyên nếu xác thực bị gỡ - phép kiểm này là
   thứ duy nhất bắt được chuyện đó.
4. Máy chủ THẬT SỰ chỉ đọc. Thử ghi qua chính kết nối của backend và đợi bị từ
   chối - không tin vào việc "không có endpoint ghi nào".

CẦN KHOÁ ĐỂ CHẠY
----------------
Đặt DASHBOARD_KEY (biến môi trường hoặc .env) giống hệt khoá máy chủ đang dùng.
Thiếu thì script này thoát ngay lúc import - xem ghi chú ở chỗ import.

Với --compare: gọi cả hai máy chủ và so từng byte JSON. Hai hệ quản trị phải trả
về giống hệt nhau, kể cả thứ tự dòng.

LƯU Ý VỀ --compare (từ 17/08/2026)
----------------------------------
PostgreSQL là mặc định và var/token_ledger.sqlite đã bị xoá, nên --compare cần
DỰNG một bản SQLite trước:

    python scripts/rebuild_db.py --db var/token_ledger.sqlite
    TOKEN_LEDGER_DSN=var/token_ledger.sqlite \\
        python -m uvicorn backend.main:app --port 8001

Hai chênh lệch KIỂU đã biết giữa hai hệ, cả hai vô hại tới JSON - xem
docs/reference/mo-ta-database.md:
    token       Decimal (pg) vs int (sqlite) -> jsonable_encoder cho ra so nguyen
    is_technical  true (pg) vs 1 (sqlite)    -> khong thanh phan nao doc cot nay
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "db"))
sys.path.insert(0, str(ROOT))

import connect  # noqa: E402
from backend import store  # noqa: E402

# Lấy khoá TỪ CHÍNH backend, không đọc lại biến môi trường ở đây.
#
# Đọc lại là tạo bản sao thứ hai của cùng một phép đọc cấu hình, và bản sao sẽ
# trôi: đúng cái bẫy đã dính ngày 21/08 khi tools/dien_tap_gateway.py tự chép
# câu SQL của store.py rồi đo bằng logic đã bị bỏ. Import thế này thì khoá mà
# phép kiểm gửi đi LUÔN bằng khoá mà máy chủ kiểm - không có đường nào lệch.
#
# Hệ quả có chủ ý: chưa cấu hình DASHBOARD_KEY thì dòng import này thoát ngay,
# kèm đúng thông báo mà máy chủ sẽ in. Không kiểm được một API chưa cấu hình nổi.
from backend.main import DASHBOARD_KEY, DASHBOARD_OPEN  # noqa: E402

def _data_range() -> tuple[str, str]:
    """Khoảng ngày lấy TỪ DATABASE, không ghim trong file này.

    Trước 17/08/2026 chỗ này là `START, END = "2026-01-01", "2026-08-13"`. Ngày
    ghim đó lỗi thời ngay lần nạp dữ liệu kế tiếp: sau khi đường ống kéo thêm
    14→17/08, phép kiểm hỏi API đến 13/08 rồi so với tổng của TOÀN BỘ database —
    lệch 11,9 triệu token và $4,41, trong khi cả hai vế đều đúng.

    Nó hỏng thành tiếng nên không âm thầm, nhưng vẫn trái với chính lời hàm
    against_database() tự nói: "So với chính database, không với số ghim trong
    file này."
    """
    with store.open_db() as (cn, _):
        lo, hi = connect.query_one(
            cn, "SELECT MIN(day), MAX(day) FROM usage_resolved")
    if lo is None:
        raise SystemExit("Database chua co du lieu su dung - chay rebuild_db.py truoc.")
    return str(lo)[:10], str(hi)[:10]


START, END = _data_range()
PATHS = [
    "/api/health",
    "/api/catalog",
    "/api/accounts",
    "/api/adoption",
    f"/api/usage?start={START}&end={END}",
    f"/api/usage-by-account?start={START}&end={END}",
    f"/api/performance?start={START}&end={END}",
    f"/api/thinking?start={START}&end={END}",
]


class Check:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passed = 0

    def expect(self, ok: bool, label: str, detail: str = "") -> None:
        if ok:
            self.passed += 1
            print(f"[  ok  ] {label}")
        else:
            self.failures.append(f"{label}: {detail}")
            print(f"[ HONG ] {label}\n         {detail}")


def _headers(auth: bool) -> dict:
    return {"Authorization": "Bearer " + DASHBOARD_KEY} if auth and DASHBOARD_KEY else {}


def get(base: str, path: str, auth: bool = True):
    req = urllib.request.Request(base + path, headers=_headers(auth))
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def status(base: str, path: str, auth: bool = True) -> int:
    try:
        urllib.request.urlopen(
            urllib.request.Request(base + path, headers=_headers(auth)), timeout=30)
        return 200
    except urllib.error.HTTPError as e:
        return e.code


def against_database(c: Check, base: str) -> None:
    """So với chính database, không với số ghim trong file này."""
    with store.open_db() as (cn, _):
        db_cost = connect.query_one(cn, "SELECT SUM(cost_usd) FROM fact_billing_daily")[0]
        db_tokens = connect.query_one(cn, "SELECT SUM(total_tokens) FROM usage_resolved")[0]
        n_accounts = connect.query_one(
            cn, "SELECT COUNT(*) FROM account WHERE kind='real'")[0]
        n_units = connect.count_rows(cn, "dim_unit")

    rows = get(base, f"/api/usage?start={START}&end={END}")["rows"]
    api_cost = sum(x["cost_usd"] or 0 for x in rows)
    api_tokens = sum(x["total_tokens"] or 0 for x in rows)
    c.expect(abs(float(db_cost) - api_cost) < 1e-4, "Tien API == database",
             f"api ${api_cost:.6f} != db ${float(db_cost):.6f}")
    c.expect(int(db_tokens) == api_tokens, "Token API == database",
             f"api {api_tokens:,} != db {int(db_tokens):,}")

    cat = get(base, "/api/catalog")
    c.expect(len(cat["units"]) == n_units, "So don vi khop",
             f"{len(cat['units'])} != {n_units}")
    c.expect(len(get(base, "/api/accounts")["rows"]) == n_accounts,
             "So tai khoan khop", "")

    # Cột "số này từ đâu ra" phải có thật, không chỉ có trong tài liệu.
    missing = [k for k in ("token_source", "call_source", "token_estimated")
               if rows and k not in rows[0]]
    c.expect(not missing, "Moi dong su dung deu kem nguon goc", f"thieu: {missing}")

    # Tỷ lệ áp dụng: mỗi agent đúng một dòng, và tỷ lệ phải khớp phép chia của
    # chính nó. Kiểm phép chia nghe thừa, nhưng nó bắt được đúng cái nguy hiểm
    # nhất ở endpoint này - tử số và mẫu số đến từ hai câu SQL khác nhau, sửa
    # một bên mà quên bên kia thì con số vẫn hiện ra bình thường.
    ad = get(base, "/api/adoption")["rows"]
    c.expect(len(ad) == len(cat["agents"]), "Ty le ap dung: mot dong moi agent",
             f"{len(ad)} dong / {len(cat['agents'])} agent")
    sai = [r["agent"] for r in ad
           if r["provisioned"] <= 0
           or r["active"] > r["provisioned"]
           or abs(r["rate_pct"] - 100.0 * r["active"] / r["provisioned"]) > 0.06]
    c.expect(not sai, "Ty le ap dung khop tu so / mau so", f"lech o: {sai}")

    h = get(base, "/api/health")
    c.expect(bool(h.get("warnings")), "/api/health co canh bao do phu",
             "khong co canh bao nao - kha nang tinh sai do phu")
    acct = get(base, f"/api/usage-by-account?start={START}&end={END}")
    c.expect(any(w["code"] == "user_coverage" for w in acct.get("warnings", [])),
             "Endpoint theo tai khoan tu keo canh bao do phu",
             "thieu canh bao - nguoi doc se tuong bang nay day du")


def bad_params(c: Check, base: str) -> None:
    for junk in ("hom-qua", "2026-13-99", "2026-02-30", "01/01/2026", ""):
        code = status(base, f"/api/usage?start={junk}")
        c.expect(code == 400 or (junk == "" and code == 200),
                 f"Tham so rac bi tu choi: start={junk!r}",
                 f"tra ve {code}, dang le 400")
    d = get(base, "/api/usage?start=2026-08-13&end=2026-08-01")
    c.expect(d["start"] == "2026-08-01" and d["end"] == "2026-08-13",
             "Khoang ngay dao nguoc duoc tu sap lai", f"{d['start']} .. {d['end']}")


def xac_thuc(c: Check, base: str) -> None:
    """Gọi KHÔNG khoá phải bị từ chối.

    Đây là phép kiểm giữ cho cả bộ này khỏi nói dối. 16 phép kiểm cũ đều gửi
    khoá, nên chúng vẫn xanh y nguyên kể cả khi xác thực bị gỡ khỏi mọi
    endpoint. Không có phép kiểm này thì bộ kiểm báo "đạt" cho một máy chủ đang
    mở toang - đúng loại sai im lặng mà cả change này đi bịt.
    """
    code = status(base, "/api/accounts", auth=False)
    # Liệt kê CẢ BA nguyên nhân, không đoán lấy một.
    #
    # Bản đầu chọn nguyên nhân theo `DASHBOARD_OPEN` của CHÍNH tiến trình này -
    # nhưng máy chủ có thể đã được khởi động từ một cửa sổ khác với biến môi
    # trường khác. Khi đó thông báo tự tin chỉ sai chỗ, và người đọc đi sửa
    # đúng thứ không hỏng.
    vi_sao = ("Ba kha nang: (1) may chu khoi dong voi DASHBOARD_OPEN=1"
              " - xac thuc DANG TAT; (2) endpoint thieu Depends(nguoi_goi);"
              " (3) HTTPBearer dang auto_error=True nen tra 403 chu khong 401."
              f" [tien trinh nay doc duoc DASHBOARD_OPEN={DASHBOARD_OPEN}]")
    c.expect(code == 401, "Goi /api/accounts khong khoa bi tu choi 401",
             f"tra ve {code}. {vi_sao}")

    # Điểm thăm dò PHẢI mở. Nếu ai đó gắn khoá vào /healthz thì giám sát sẽ báo
    # máy chủ chết trong khi nó vẫn sống - và không ai biết vì sao.
    code = status(base, "/healthz", auth=False)
    c.expect(code == 200, "Diem tham do /healthz van mo khong can khoa",
             f"tra ve {code}, dang le 200")


def read_only(c: Check) -> None:
    """Thử GHI thật sự qua chính kết nối của backend. Phải bị từ chối."""
    try:
        with store.open_db() as (cn, _):
            cn.cursor().execute("CREATE TABLE _write_probe_delete_me (x INT)")
            cn.commit()
        c.expect(False, "Ket noi cua backend la chi doc",
                 "GHI DUOC - database khong o che do chi doc")
    except Exception as e:
        c.expect(True, f"Ket noi cua backend la chi doc ({type(e).__name__})")


def compare_engines(c: Check, a: str, b: str) -> None:
    for p in PATHS:
        x, y = get(a, p), get(b, p)
        c.expect(x == y, f"SQLite == PostgreSQL: {p}",
                 "JSON khac nhau - xem cot nao lech bang cach goi tay hai ben")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", default="http://127.0.0.1:8000")
    p.add_argument("--compare", default=None,
                   help="URL may chu thu hai (chay tren he quan tri khac)")
    args = p.parse_args()

    try:
        get(args.base, "/api/health")
    except urllib.error.HTTPError as e:
        # 401 KHÁC HẲN "chưa bật máy chủ": máy chủ đang chạy và đang trả lời.
        # Gộp hai cái vào một câu là chỉ sai chỗ cho người đọc.
        if e.code == 401:
            raise SystemExit(
                f"May chu {args.base} tra 401 - khoa khong dung.\n"
                f"  Khoa phep kiem dang dung lay tu DASHBOARD_KEY (moi truong"
                f" hoac .env).\n"
                f"  May chu phai duoc khoi dong voi DUNG khoa do.")
        raise SystemExit(f"Khong goi duoc {args.base}: HTTP {e.code}")
    except Exception as e:
        raise SystemExit(f"Khong goi duoc {args.base}: {e}\n"
                         f"  Mo may chu truoc:"
                         f"  python -m uvicorn backend.main:app --port 8000")

    c = Check()
    print("Doi chieu voi database\n" + "─" * 72)
    against_database(c, args.base)
    print("\nTham so\n" + "─" * 72)
    bad_params(c, args.base)
    print("\nXac thuc\n" + "─" * 72)
    xac_thuc(c, args.base)
    print("\nChi doc\n" + "─" * 72)
    read_only(c)
    if args.compare:
        print("\nHai he quan tri\n" + "─" * 72)
        compare_engines(c, args.base, args.compare)

    print("\n" + "═" * 72)
    print(f"{c.passed + len(c.failures)} phep kiem | {c.passed} dat"
          f" | {len(c.failures)} hong")
    if c.failures:
        sys.exit(1)
    print("API DAT.")


if __name__ == "__main__":
    main()
