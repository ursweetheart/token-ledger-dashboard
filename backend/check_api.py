"""Kiểm API: đối chiếu với database, và đối chiếu SQLite <-> PostgreSQL.

    # mở máy chủ trước, ở một cửa sổ khác:
    python -m uvicorn backend.main:app --port 8000

    python backend/check_api.py
    python backend/check_api.py --compare http://127.0.0.1:8001

NĂM VIỆC NÀY KIỂM
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
5. Endpoint không phơi thứ không được phơi. `/api/accounts` chỉ được trả
   tài khoản là NGƯỜI; 6 tài khoản dịch vụ lọt vào đó sẽ bị đếm như 6 nhân
   viên, và không tầng nào phía sau loại chúng ra.

CẦN KHOÁ ĐỂ CHẠY
----------------
Đặt DASHBOARD_KEY (biến môi trường hoặc .env) giống hệt khoá máy chủ đang dùng.
Thiếu thì script này thoát ngay lúc import - xem ghi chú ở chỗ import.

Với --compare: gọi cả hai máy chủ và so từng byte JSON. Hai hệ quản trị phải trả
về giống hệt nhau, kể cả thứ tự dòng.

LƯU Ý VỀ --compare (sửa 24/08/2026)
-----------------------------------
Trước đây --compare dùng để đối chiếu PostgreSQL với một bản SQLite. SQLite đã bị
gỡ khỏi dự án (change `drop-the-sqlite-escape-hatch`), nên nay nó dùng để so hai
database PostgreSQL - ví dụ bản đang chạy với một bản vừa dựng lại:

    TOKEN_LEDGER_DSN=postgresql://.../token_ledger_v2 \\
        python -m uvicorn backend.main:app --port 8001

Hai chênh lệch KIỂU từng ghi ở đây (Decimal vs int, true vs 1) là chênh lệch giữa
psycopg2 và sqlite3. Chúng không còn xảy ra vì chỉ còn một driver.
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
        raise SystemExit("The database has no usage data yet - run rebuild_db.py first.")
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
]


class Check:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.notes: list[str] = []
        self.passed = 0

    def expect(self, ok: bool, label: str, detail: str = "") -> None:
        if ok:
            self.passed += 1
            print(f"[  ok  ] {label}")
        else:
            self.failures.append(f"{label}: {detail}")
            print(f"[ FAIL ] {label}\n         {detail}")

    def expect_tren(self, quan_sat: int, ok: bool, label: str,
                    detail: str = "") -> None:
        """Như `expect()`, nhưng KHAI CẢ MẪU SỐ - số dòng đã quan sát.

        Cùng lý lẽ với `Audit.check_tren()` ở scripts/audit_db.py: một phép kiểm
        `khong dong nao xau` chạy trên **0 dòng** sẽ báo ĐẠT, và nó không phân biệt
        *"nguồn ghi đúng"* với *"nguồn không ghi gì cả"*.

        BA KẾT CỤC:
            quan sat 0 dong             -> CHUA KIEM DUOC (khong tinh la dat,
                                           va KHONG lam script that bai)
            quan sat n > 0, khong loi   -> DAT, nhan kem "(n rows)"
            quan sat n > 0, co loi      -> HONG

        Không làm script thất bại vì kỳ chưa có lưu lượng của nguồn đó là trạng
        thái HỢP LỆ. Nhưng nó phải HIỆN RA - hôm nay nó vô hình.
        """
        if quan_sat == 0:
            self.notes.append(f"{label}: {detail}")
            print(f"[ note ] {label}\n         CHUA KIEM DUOC - 0 dong de quan sat."
                  f" Day KHONG phai ket qua dat."
                  + (f"\n         {detail}" if detail else ""))
            return
        self.expect(ok, f"{label} ({quan_sat} rows)", detail)


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
        # TIEN CUA VIEW = HOA DON + GATEWAY, khong phai chi hoa don.
        #
        # Phep kiem nay LOI THOI tu 31/08/2026 va den 03/09 moi bi bat. Migration
        # 005 (`gateway_cost_vao_view`) CO Y dao nguoc quyet dinh cua baseline
        # 001 va do them tien cua Gateway vao `usage_resolved.cost_usd`.
        # `scripts/audit_db.py` da duoc sua theo ("Cost: invoice + gateway ==
        # usage_resolved"), file nay thi khong - nen no bao HONG trong khi ca hai
        # ve deu dung:
        #
        #     fact_billing_daily        $307,360850
        #     usage_resolved            $307,382155
        #     gateway trong fact_usage_daily  $0,021305   <- dung bang chenh lech
        #
        # KHONG noi long nguong de no qua. Sua CONG THUC cho dung dinh nghia moi
        # cua view - chinh la truong hop duy nhat duoc phep sua mot phep kiem.
        db_cost = connect.query_one(cn, "SELECT SUM(cost_usd) FROM fact_billing_daily")[0]
        # Chi cong tien Gateway cua nhung khoa KHONG co dong hoa don tuong ung.
        # Cung cong thuc voi audit_db.py - khoa co ca hai thi view lay hoa don,
        # cong ca hai la dem hai lan.
        gw_cost = connect.query_one(cn, """
            SELECT COALESCE(SUM(g.cost_usd), 0) FROM fact_usage_daily g
             WHERE g.source = 'gateway'
               AND NOT EXISTS (SELECT 1 FROM fact_usage_daily b
                                WHERE b.source = 'billing' AND b.day = g.day
                                  AND b.agent_id = g.agent_id
                                  AND b.model_id = g.model_id)""")[0]
        db_cost = float(db_cost or 0) + float(gw_cost or 0)
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
    # Mẫu số lấy từ `kind='real'` - CÙNG điều kiện mà store.accounts() dùng.
    # Nghĩa là phép kiểm này soi gương chính bản cài đặt: sửa cả hai chỗ cho
    # khớp nhau thì nó vẫn xanh. Phép kiểm khẳng định TÍNH CHẤT nằm ở
    # directory_is_people_only() bên dưới, và đó là chỗ nói rõ dòng nào lọt.
    n_api = len(get(base, "/api/accounts")["rows"])
    c.expect(n_api == n_accounts, "Account count matches",
             f"api {n_api} != db {n_accounts} (db dem kind='real')")

    # Cột "số này từ đâu ra" phải có thật, không chỉ có trong tài liệu.
    missing = [k for k in ("token_source", "call_source", "token_estimated")
               if rows and k not in rows[0]]
    c.expect(not missing, "Every usage row carries its source", f"missing: {missing}")

    # Tỷ lệ áp dụng: mỗi agent đúng một dòng, và tỷ lệ phải khớp phép chia của
    # chính nó. Kiểm phép chia nghe thừa, nhưng nó bắt được đúng cái nguy hiểm
    # nhất ở endpoint này - tử số và mẫu số đến từ hai câu SQL khác nhau, sửa
    # một bên mà quên bên kia thì con số vẫn hiện ra bình thường.
    ad = get(base, "/api/adoption")["rows"]
    c.expect(len(ad) == len(cat["agents"]), "Adoption: one row per agent",
             f"{len(ad)} rows / {len(cat['agents'])} agents")
    sai = [r["agent"] for r in ad
           if r["provisioned"] <= 0
           or r["active"] > r["provisioned"]
           or abs(r["rate_pct"] - 100.0 * r["active"] / r["provisioned"]) > 0.06]
    c.expect(not sai, "Ty le ap dung khop tu so / mau so", f"differs at: {sai}")

    h = get(base, "/api/health")
    c.expect(bool(h.get("warnings")), "/api/health co canh bao do phu",
             "no warning at all - the coverage figure is probably wrong")
    acct = get(base, f"/api/usage-by-account?start={START}&end={END}")
    c.expect(any(w["code"] == "user_coverage" for w in acct.get("warnings", [])),
             "The per-account endpoint raises its own coverage warning",
             "no warning - a reader would assume this table is complete")


def bad_params(c: Check, base: str) -> None:
    for junk in ("hom-qua", "2026-13-99", "2026-02-30", "01/01/2026", ""):
        code = status(base, f"/api/usage?start={junk}")
        c.expect(code == 400 or (junk == "" and code == 200),
                 f"Tham so rac bi tu choi: start={junk!r}",
                 f"returned {code}, expected 400")
    d = get(base, "/api/usage?start=2026-08-13&end=2026-08-01")
    c.expect(d["start"] == "2026-08-01" and d["end"] == "2026-08-13",
             "A reversed date range is re-ordered", f"{d['start']} .. {d['end']}")


def theo_gio(c: Check, base: str) -> None:
    """Endpoint theo GIO: bat buoc khoang thoi gian, va KHONG duoc co `billing`.

    Hai loai loi khac han nhau:

      (1) Goi tran phai bi TU CHOI. Cac endpoint theo ngay mac dinh 30 ngay gan
          nhat khi thieu tham so; o day mac dinh nhu vay la keo ve hang nghin
          dong cho mot cau hoi chua ai dat. Neu phep kiem nay hong thi khong ai
          THAY gi ca - API van tra ve so dung, chi la qua nhieu.

      (2) `billing` KHONG duoc xuat hien. Hoa don Google chi tinh theo NGAY, nen
          moi con so tien theo gio deu la bia. Bo dung da chan o tang NAP; phep
          kiem nay chan them o tang DOC, vi hai tang co the lech nhau.
    """
    for thieu in ("", "?start=2026-08-31", "?end=2026-08-31"):
        code = status(base, "/api/usage-hourly" + thieu)
        c.expect(code == 400,
                 f"Endpoint theo gio doi khoang thoi gian: {thieu or '(goi tran)'}",
                 f"returned {code}, expected 400")

    d = get(base, "/api/usage-hourly?start=2026-08-31&end=2026-08-31")
    c.expect("billing" not in (d.get("sources") or {}),
             "Bang theo gio KHONG co nguon `billing`",
             f"sources = {d.get('sources')}")
    c.expect(all(len(r["hour"]) == 19 and r["hour"][13:] == ":00:00"
                 for r in d["rows"]),
             "Moi dong theo gio cat dung ve dau gio",
             f"{[r['hour'] for r in d['rows'][:3]]}")
    # 31/08 la ngay DUY NHAT co Gateway. Phep kiem nay hong nghia la hoac bo
    # dung khong chay, hoac khoang ngay bi hieu lech mot ngay.
    c.expect(d["count"] > 0,
             "Ngay 31/08/2026 co du lieu theo gio",
             f"count = {d['count']}")


def nguon_gateway(c: Check, base: str) -> None:
    """Nguon `gateway` co len toi API khong - HOI QUA ENDPOINT.

    KHONG CHEP CAU SQL CUA audit_db.py SANG DAY
    -------------------------------------------
    `audit_db.py` chay bang vai `token` va soi thang bang. File nay phai soi THU
    API THAT SU TRA RA, qua vai `api_readonly`. Chep cau SQL sang day la tao ban
    sao thu hai cua cung mot phep do, va ban sao SE TROI - dung cai bay da dinh
    ngay 21/08 khi tools/dien_tap_gateway.py tu chep cau SQL cua store.py roi do
    bang logic da bi bo.

    Ba endpoint, ba cau hoi khac nhau:
        /api/usage           so Gateway co len toi cua chinh khong (token_source)
        /api/usage-hourly    nguon gateway co xuong duoc gio khong
        /api/performance     phan vi ngay Gateway phu co ra so THO khong
    """
    P = f"?start={START}&end={END}"

    # (1) /api/usage - dong nao mang token_source = 'gateway'
    rows = get(base, "/api/usage" + P)["rows"]
    gw = [r for r in rows if r.get("token_source") == "gateway"]
    c.expect_tren(len(gw), all((r.get("total_tokens") or 0) > 0 for r in gw),
                  "Nguon gateway len toi /api/usage va mang token",
                  "co dong gateway nhung total_tokens bang 0 hoac rong")

    # (2) /api/usage-hourly - nguon gateway co mat, va KHONG duoc co billing
    d = get(base, "/api/usage-hourly"
            + f"?start={START}&end={END}")
    theo_nguon = d.get("sources") or {}
    c.expect_tren(theo_nguon.get("gateway", 0), True,
                  "Nguon gateway co mat trong bang theo gio")
    c.expect("billing" not in theo_nguon,
             "Bang theo gio van KHONG co nguon `billing`",
             f"sources = {theo_nguon}")

    # (3) /api/performance - ngay Gateway phu phai co phan vi, va la SO THO.
    #
    # So tho khong co sai so noi suy nen HAI cot o histogram phai RONG. Mot dong
    # mang o nghia la ai do da dan sai so cua phep do KHAC len mot con so von
    # khong co - va no trong y nhu that.
    lat = get(base, "/api/performance" + P)["latency"]
    tho = [r for r in lat
           if r.get("p95_bucket_from") is None and r.get("p95_bucket_to") is None]
    c.expect_tren(len(tho),
                  all((r.get("p95_seconds") or 0) > 0 for r in tho),
                  "Phan vi tu so tho len toi /api/performance, khong mang o histogram",
                  "co dong khong mang o nhung p95 rong")


def xac_thuc(c: Check, base: str) -> None:
    """Gọi KHÔNG khoá phải bị từ chối.

    Đây là phép kiểm giữ cho cả bộ này khỏi nói dối. MỌI phép kiểm khác đều
    gửi khoá, nên chúng vẫn xanh y nguyên kể cả khi xác thực bị gỡ khỏi mọi
    endpoint. Không có phép kiểm này thì bộ kiểm báo "đạt" cho một máy chủ
    đang mở toang - đúng loại sai im lặng mà cả change này đi bịt.

    (Tới 22/08/2026 câu trên ghi "16 phép kiểm cũ". Một con số nằm trong văn
    xuôi thì cũ đi mỗi lần thêm một phép kiểm, nên đã bỏ.)
    """
    code = status(base, "/api/accounts", auth=False)
    # Liệt kê CẢ BA nguyên nhân, không đoán lấy một.
    #
    # Bản đầu chọn nguyên nhân theo `DASHBOARD_OPEN` của CHÍNH tiến trình này -
    # nhưng máy chủ có thể đã được khởi động từ một cửa sổ khác với biến môi
    # trường khác. Khi đó thông báo tự tin chỉ sai chỗ, và người đọc đi sửa
    # đúng thứ không hỏng.
    vi_sao = ("Three possibilities: (1) the server started with DASHBOARD_OPEN=1"
              " - authentication is OFF; (2) the endpoint is missing Depends(nguoi_goi);"
              " (3) HTTPBearer has auto_error=True so it returns 403, not 401."
              f" [this process reads DASHBOARD_OPEN={DASHBOARD_OPEN}]")
    c.expect(code == 401, "Calling /api/accounts without a key is refused with 401",
             f"returned {code}. {vi_sao}")

    # Điểm thăm dò PHẢI mở. Nếu ai đó gắn khoá vào /healthz thì giám sát sẽ báo
    # máy chủ chết trong khi nó vẫn sống - và không ai biết vì sao.
    code = status(base, "/healthz", auth=False)
    c.expect(code == 200, "The /healthz probe stays open without a key",
             f"returned {code}, expected 200")


def directory_is_people_only(c: Check, base: str) -> None:
    """Danh bạ chỉ được chứa con người.

    `/api/accounts` là thứ duy nhất nuôi USER_ACCOUNTS ở frontend, và mọi dòng
    lọt vào đó đều được đếm như một con người. Bộ lọc `kind='real'` trong
    store.accounts() là tấm lưới DUY NHẤT - đo A/B ngày 22/08/2026: nới nó ra
    thì danh bạ 937 -> 943, sáu tài khoản dịch vụ `svc.<code>` lên thẳng màn
    hình, và KHÔNG tầng nào phía sau loại chúng (đo được đúng 0 dòng bị vứt).

    Hỏi DỮ LIỆU TRẢ VỀ, không đọc mã nguồn. Phép kiểm đọc mã nguồn sẽ vẫn xanh
    vào ngày ai đó thêm một endpoint thứ hai cũng trả danh bạ - và ngày 21/08 đã
    có một lần grep đếm nhầm `Depends` rồi báo hai endpoint hở trong khi cả tám
    đều kín.
    """
    rows = get(base, "/api/accounts")["rows"]
    la = [r for r in rows if r.get("kind") != "real"]
    # Nói RÕ dòng nào lọt. "unexpected rows" thì người đọc phải tự đi tìm.
    ten = ", ".join(f"{r.get('username')}({r.get('kind')})" for r in la[:5])
    c.expect(not la, "The /api/accounts directory holds only real people",
             f"{len(la)} rows are not kind='real': {ten}"
             + (" ..." if len(la) > 5 else ""))


def con_doc_duoc(c: Check, base: str) -> None:
    """MAY CHU co con doc duoc database khong. Hoi QUA HTTP, khong hoi ket noi cua
    chinh tien trinh nay.

    PHAI HOI MAY CHU - DAY LA CHO BAN DAU TOI LAM SAI (sua 03/09/2026)
    ------------------------------------------------------------------
    Ban dau ham nay thu doc bang `store.open_db()`, tuc ket noi cua CHINH tien
    trinh dang chay phep kiem. Do that ngay 03/09, ngay sau `rebuild_db.py`:

        API that (container)          /api/health -> HTTP 500   MU HOAN TOAN
        phep kiem chay tu shell       "con doc duoc" -> DAT     <- SAI

    Ly do: `backend/store.py` lay DSN tu `TOKEN_LEDGER_DSN`. Trong container do
    la `api_readonly`; chay tu shell thi no la `token` - VAI QUAN TRI, chu schema,
    khong bao gio mat quyen. Nen phep kiem thu mot ket noi HOAN TOAN KHAC voi cai
    ma may chu dung.

    Do dung la cai bay ma ca change nay di bit, va ban dau toi tu dat lai no.

    CACH HOI DUNG: HAI ENDPOINT, HAI CAU HOI
    ----------------------------------------
        /healthz      "tien trinh con tho khong"  -> KHONG cham database
        /api/health   "du lieu co gi"             -> PHAI cham database

    Bon to hop, va chung noi bon chuyen khac han nhau:

        /healthz   /api/health   ket luan
        --------   -----------   -------------------------------------------
          200          200       binh thuong
          200          500       MAY CHU SONG NHUNG KHONG DOC DUOC DATABASE
                                 -> gan nhu chac chan `rebuild_db.py` vua chay
          200          401       khoa sai, khong lien quan quyen doc
          loi          -         may chu chua bat
    """
    label = "The API server can still READ the database"
    ma_healthz = status(base, "/healthz", auth=False)
    if ma_healthz != 200:
        c.expect(False, label,
                 f"/healthz tra {ma_healthz} - may chu chua bat, chua ket luan"
                 f" duoc gi ve quyen doc")
        return

    ma = status(base, "/api/health")
    if ma == 200:
        c.expect(True, label, "")
        return
    if ma == 401:
        c.expect(False, label,
                 "/api/health tra 401 - khoa sai. Day KHONG phai van de quyen doc.")
        return
    c.expect(False, label,
             f"/healthz tra 200 nhung /api/health tra {ma}:"
             f" MAY CHU SONG MA KHONG DOC DUOC DATABASE.\n"
             f"         Vai doc nhieu kha nang da mat quyen. Tu 14/09/2026"
             f" `rebuild_db.py` chi TRUNCATE, KHONG con xoa GRANT -\n"
             f"         nen nghi toi: database moi chua chay read-only-api.sql,"
             f" hoac mot lan DROP bang tay.\n"
             f"         Kiem:  python scripts/check_db_grants.py\n"
             f"         Chua:  docker compose up -d api")


def _ket_noi_cuc_bo_doc_duoc(c: Check) -> None:
    """Ket noi cua CHINH tien trinh nay co doc duoc khong.

    PHEP PHU, KHONG thay the `con_doc_duoc()`.

    No noi ve DSN ma TIEN TRINH NAY dang cam, chu khong phai DSN cua may chu. Do
    03/09: chay tu shell thi `backend/store.py` lay `token` (vai QUAN TRI, chu
    schema) - vai do khong bao gio mat quyen, nen phep nay LUON DAT ke ca luc
    container dang mu. Vi vay no khong thay the duoc phep hoi qua HTTP.

    Giu lai vi no van bat duoc mot truong hop that: chay phep kiem tren mot may
    ma database khong voi toi duoc, hoac DSN cuc bo tro sai cho.

    Nhan cua no NEU RO VAI da thu, de khong ai doc nham "DAT" thanh "may chu doc
    duoc".

    CAU DOC PHAI CHAM MOT BANG THAT
    -------------------------------
    KHONG dung `SELECT 1`: cau do khong can quyen USAGE tren schema nen no chay
    duoc CA KHI quyen da mat sach - tuc phep kiem se mu dung y nhu cai no thay the.
    """
    label = "The local check connection can READ"
    ok, detail = False, ""
    try:
        with store.open_db() as (cn, _):
            cur = cn.cursor()
            # `ref_source` la bang nho nhat co that trong schema (4 dong). Doc no
            # doi CA `USAGE` tren schema LAN `SELECT` tren bang - dung hai quyen
            # ma mot lan DROP SCHEMA xoa mat (rebuild truoc 14/09/2026, hay chay tay).
            cur.execute("SELECT COUNT(*) FROM ref_source")
            n = cur.fetchone()[0]
            vai = connect.query_one(cn, "SELECT current_user")[0]
            ok = True
            # NEU RO VAI: doc "DAT" ma khong biet no thu vai nao la doc nham.
            label = f"{label} (vai `{vai}`, ref_source: {n} rows)"
    except Exception as e:
        detail = (f"CANNOT READ ({type(e).__name__}): {e}\n"
                  f"         Vai doc da mat quyen. Tu 14/09/2026 `rebuild_db.py`"
                  f" chi TRUNCATE, KHONG con xoa GRANT - nen nghi toi: database\n"
                  f"         moi chua chay read-only-api.sql, hoac mot lan DROP"
                  f" bang tay.\n"
                  f"         Chua: `docker compose up -d api` (keo theo"
                  f" api-db-init, cap lai quyen).")
    c.expect(ok, label, detail)


def read_only(c: Check) -> None:
    """Thử GHI thật sự qua chính kết nối của backend. Phải bị từ chối.

    CHI tra loi cau "lenh ghi co bi chan khong". Cau "vai con doc duoc khong"
    nam o `con_doc_duoc()` ngay tren - HAI cau hoi khac nhau, va truoc 03/09
    chung dung chung mot phep kiem nen mot trang thai hong bao DAT.
    """
    label = "The backend connection is read-only"
    ok = False
    result_label = label
    detail = ""
    try:
        with store.open_db() as (cn, _):
            try:
                cur = cn.cursor()
            except Exception as e:
                detail = f"COULD NOT OPEN A CURSOR ({type(e).__name__}): {e}"
            else:
                rejection = None
                try:
                    cur.execute("CREATE TEMP TABLE _write_probe (x INT)")
                except Exception as e:
                    rejection = e

                try:
                    cn.rollback()
                except Exception as e:
                    detail = f"ROLLBACK FAILED ({type(e).__name__}): {e}"
                else:
                    if rejection is None:
                        detail = "THE WRITE SUCCEEDED - the database is not read-only"
                    else:
                        sqlstate = (getattr(rejection, "pgcode", None)
                                    or getattr(rejection, "sqlstate", None))
                        if sqlstate == "25006":
                            ok = True
                            result_label = f"{label} ({type(rejection).__name__})"
                        else:
                            detail = ("THE WRITE FAILED BUT NOT WITH A READ-ONLY ERROR "
                                      f"({type(rejection).__name__}, "
                                      f"SQLSTATE={sqlstate or 'none'}): {rejection}")
    except Exception as e:
        detail = f"COULD NOT OPEN A CONNECTION ({type(e).__name__}): {e}"

    c.expect(ok, result_label, detail)


def compare_engines(c: Check, a: str, b: str) -> None:
    for p in PATHS:
        x, y = get(a, p), get(b, p)
        c.expect(x == y, f"SQLite == PostgreSQL: {p}",
                 "the JSON differs - call both by hand to see which column diverges")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", default="http://127.0.0.1:8000")
    p.add_argument("--compare", default=None,
                   help="URL of the second server (running on a different admin system)")
    args = p.parse_args()

    # THAM DO BANG /healthz, KHONG BANG /api/health (doi 03/09/2026).
    #
    # `/healthz` KHONG cham database, nen no tach duoc hai chuyen tung bi gop:
    #     may chu chua bat            -> khong noi duoc gi ve quyen doc
    #     may chu bat ma khong doc noi -> DUNG cai change nay di bit
    #
    # Tham do bang `/api/health` thi truong hop thu hai thoat ngay o day voi
    # "Cannot reach ... HTTP 500", va phep kiem chan doan ben duoi KHONG kip chay.
    try:
        status_healthz = status(args.base, "/healthz", auth=False)
    except Exception as e:
        raise SystemExit(f"Cannot reach {args.base}: {e}\n"
                         f"  Start the server first:"
                         f"  python -m uvicorn backend.main:app --port 8000")
    if status_healthz != 200:
        raise SystemExit(f"Cannot reach {args.base}: /healthz tra {status_healthz}")

    ma = status(args.base, "/api/health")
    if ma == 401:
        # 401 KHÁC HẲN "chưa bật máy chủ": máy chủ đang chạy và đang trả lời.
        # Gộp hai cái vào một câu là chỉ sai chỗ cho người đọc.
        raise SystemExit(
            f"Server {args.base} returned 401 - wrong key.\n"
            f"  The check key comes from DASHBOARD_KEY (this process's"
            f" hoac .env).\n"
            f"  The server must have been started with THAT SAME key.")
    if ma != 200:
        # KHONG thoat o day. Chay THANG toi nhom "Read-only" de con_doc_duoc()
        # chan doan va bao dung nguyen nhan - do la ly do no ton tai.
        print(f"\n!! /healthz tra 200 nhung /api/health tra {ma}."
              f" May chu SONG ma khong doc duoc database.")
        print("   Bo qua cac phep can du lieu, chay thang phep chan doan.\n")
        c = Check()
        print("Read-only\n" + "─" * 72)
        con_doc_duoc(c, args.base)
        _ket_noi_cuc_bo_doc_duoc(c)
        read_only(c)
        print("\n" + "═" * 72)
        print(f"{c.passed + len(c.failures)} checks | {c.passed} passed"
              f" | {len(c.failures)} failed")
        for f in c.failures:
            print(f"  {f}")
        sys.exit(1)

    c = Check()
    print("Checked against the database\n" + "─" * 72)
    against_database(c, args.base)
    print("\nParameters\n" + "─" * 72)
    bad_params(c, args.base)
    print("\nHourly endpoint\n" + "─" * 72)
    theo_gio(c, args.base)
    print("\nGateway source\n" + "─" * 72)
    nguon_gateway(c, args.base)
    print("\nAuthentication\n" + "─" * 72)
    xac_thuc(c, args.base)
    print("\nExposed data scope\n" + "─" * 72)
    directory_is_people_only(c, args.base)
    print("\nRead-only\n" + "─" * 72)
    # HAI phep, HAI cau hoi. Ca hai dat moi la ky luat chi-doc con nguyen ven -
    # xem docstring cua con_doc_duoc().
    # BA phep, ba cau hoi. Phep DAU la phep THAT - no hoi MAY CHU.
    con_doc_duoc(c, args.base)
    _ket_noi_cuc_bo_doc_duoc(c)
    read_only(c)
    if args.compare:
        print("\nTwo admin systems\n" + "─" * 72)
        compare_engines(c, args.base, args.compare)

    print("\n" + "═" * 72)
    # Dem CA `notes`: mot phep kiem "chua kiem duoc" van la mot phep kiem da chay,
    # va giau no khoi tong so la lam dung cai viec ma no sinh ra de chong.
    tong = c.passed + len(c.notes) + len(c.failures)
    print(f"{tong} checks | {c.passed} passed | {len(c.notes)} notes"
          f" | {len(c.failures)} failed")
    if c.failures:
        sys.exit(1)
    print("API OK.")


if __name__ == "__main__":
    main()
