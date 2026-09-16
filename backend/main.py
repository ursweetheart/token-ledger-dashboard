"""API đọc database, phục vụ dashboard. CHỈ ĐỌC - không có endpoint ghi nào.

    pip install -r backend/requirements.txt
    python -m uvicorn backend.main:app --reload --port 8000

    http://127.0.0.1:8000/docs     tài liệu tự sinh, bấm thử được từng endpoint

Đổi database:
    set TOKEN_LEDGER_DSN=postgresql://token:token_local@127.0.0.1:5432/token_ledger_v2

PHẢI CÓ KHOÁ MỚI CHẠY ĐƯỢC
--------------------------
    python -c "import secrets; print(secrets.token_urlsafe(32))"   # sinh khoá
    DASHBOARD_KEY=<khoá vừa sinh>            # vào .env, HOẶC set/export

Thiếu biến này thì máy chủ KHÔNG khởi động - xem khối `caller()` bên dưới.
Đó là chủ ý: chế độ hỏng phải là "không chạy", tuyệt đối không phải "chạy mở".

TRƯỚC 21/08/2026 chỗ này ghi "VÌ SAO CHỈ CHẠY TRÊN 127.0.0.1" và dựa vào đúng
một dòng cấu hình của uvicorn để giữ 937 họ tên khỏi ra ngoài. Nay đã có một cơ
chế thật, nhưng lời khuyên cũ vẫn đúng và giữ nguyên: database này chứa danh
sách nhân viên kèm phòng ban, `--host 0.0.0.0` là mở ra cả mạng nội bộ, đừng
làm nếu chưa bàn với ai.

VÌ SAO API TRẢ CẢ "SỐ NÀY TỪ ĐÂU RA"
------------------------------------
Mọi endpoint trả số liệu đều kèm cột nguồn (`token_source`, `token_estimated`,
`enough_samples`, `unit_conflict`) và endpoint /api/health trả danh sách cảnh
báo. Đó không phải siêu dữ liệu cho vui: một bảng số chỉ phủ 5,7% người dùng
trông y hệt một bảng số đầy đủ. Nếu frontend không hiện được phần này thì bỏ đi
còn hơn, vì khi đó người xem sẽ tin vào con số nhiều hơn mức nó đáng được.
"""

from __future__ import annotations

import os
import re
import secrets
import sys
from dataclasses import dataclass
from datetime import date, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import store

# ═══════════════════════════════════════════════════════════════════════════
# XÁC THỰC
#
# Một khoá dùng chung, gửi trong `Authorization: Bearer <khoá>`.
#
# VÌ SAO KHÔNG PHẢI JWT THEO NGƯỜI (quyết định 21/08/2026)
# --------------------------------------------------------
# 8/8 endpoint là GET, 0 hành động đặc quyền, và `account` không có cột mật
# khẩu - không có kho người dùng nào để đăng nhập vào. Không có gì để phân biệt
# thì phân vai bây giờ là viết code không dùng tới.
#
# Nói thẳng phần này KHÔNG cho: không biết AI đã xem gì, không thu hồi được
# quyền của MỘT người, không phân biệt Admin/User. Nó chỉ làm đúng một việc -
# chặn người lạ đọc 937 họ tên kèm phòng ban - và biến "an toàn vì bind
# 127.0.0.1" từ một dòng cấu hình thành một cơ chế.
#
# CORS KHÔNG THAY ĐƯỢC CHỖ NÀY. CORS là luật của trình duyệt; `curl` không đọc
# CORS bao giờ và vẫn nhận đủ dữ liệu.
#
# BA ĐƯỜNG CỐ Ý ĐỂ MỞ - nói ra để không ai tưởng là sót:
#     /healthz                    giám sát cần biết máy chủ sống, KHÔNG trả dữ liệu
#     /docs · /redoc              trang thử API do FastAPI tự sinh
#     /openapi.json               lược đồ API
# Ba đường sau chỉ mô tả HÌNH DẠNG của API, không trả một dòng dữ liệu nào -
# bấm thử từ /docs mà không dán khoá thì vẫn nhận 401. Để mở là có ích: đó là
# chỗ người mới học được cách gửi khoá. Ngày máy chủ ra khỏi 127.0.0.1 thì cân
# nhắc lại, vì khi đó lược đồ là thứ giúp người lạ dò nhanh hơn.
def _read_env(name: str) -> str:
    """Đọc một biến: môi trường thật trước, rồi tới file `.env` ở gốc repo.

    VÌ SAO PHẢI ĐỌC `.env` Ở ĐÂY
    ----------------------------
    Đo ngày 21/08: không file Python nào của backend đọc `.env`. Nó chỉ được
    docker-compose và scripts/pull_web_apps.py đọc. Nếu để nguyên, đồng nghiệp
    làm ĐÚNG theo `.env.example` sẽ dán khoá vào đó rồi máy chủ vẫn từ chối
    khởi động - và thông báo lỗi lại bảo họ dán vào `.env`. Một lời hướng dẫn
    sai còn tệ hơn không có hướng dẫn.

    Thứ tự ưu tiên giống hệt `.env.example` đã ghi từ trước: "Bien moi truong
    that (export/set) luon thang gia tri trong file nay."

    Bản đọc `.env` thứ hai nằm ở scripts/pull_web_apps.py:127 (`read_env`).
    Không dùng chung được vì backend là thứ đem đi triển khai, không được phụ
    thuộc vào scripts/. Cả hai đều chỉ tách `KEY=VALUE` nên khó trôi, nhưng
    sửa một bên thì ngó sang bên kia.
    """
    value = os.environ.get(name, "").strip()
    if value:
        return value
    env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       ".env")
    try:
        with open(env, encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == name:
                    return v.strip().strip('"').strip("'")
    except OSError:
        pass
    # `errors="replace"` chứ không để mặc định: `.env` do người gõ tay trên
    # Windows, một ký tự lưu bằng codepage hệ thống là đủ ném UnicodeDecodeError
    # ngay lúc import - máy chủ chết kèm một vệt traceback không nói được rằng
    # vấn đề nằm ở file `.env`. Khoá vốn nên là ASCII; ký tự hỏng bị thay thế
    # thì khoá không khớp và người dùng nhận 401 - một câu trả lời hiểu được.
    return ""


DASHBOARD_KEY = _read_env("DASHBOARD_KEY")
DASHBOARD_OPEN = _read_env("DASHBOARD_OPEN") == "1"

# Thiếu cấu hình thì KHÔNG khởi động. `raise SystemExit` ở mức module nên uvicorn
# vấp ngay lúc nạp `backend.main:app` - đối tượng `app` chưa kịp tồn tại, không
# cổng nào được mở.
#
# Đây là dòng quan trọng nhất file này. Nếu quên đặt biến mà máy chủ vẫn chạy
# bình thường, ta có đúng lỗ hổng của hôm qua CỘNG THÊM niềm tin sai rằng đã
# khoá - cùng hạng lỗi với mọi thứ sửa ngày 20/08: sai một cách im lặng.
if not DASHBOARD_KEY and not DASHBOARD_OPEN:
    raise SystemExit(
        "\nMISSING ENVIRONMENT VARIABLE: DASHBOARD_KEY\n"
        "  The server refuses to start. No port is opened.\n\n"
        "  Generate a key:\n"
        '    python -c "import secrets; print(secrets.token_urlsafe(32))"\n\n'
        "  Then pick ONE of the two:\n"
        "    a) add a line to the .env file at the repo root  (no 'set' word):\n"
        "         DASHBOARD_KEY=<the key you just generated>\n"
        "    b) set an environment variable for this session:\n"
        "         set DASHBOARD_KEY=<key>      (cmd)\n"
        "         $env:DASHBOARD_KEY=\"<key>\"    (PowerShell)\n"
        "         export DASHBOARD_KEY=<key>   (bash)\n\n"
        "  ONLY in DEVELOPMENT, and only if running unauthenticated is acceptable:\n"
        "    DASHBOARD_OPEN=1\n")

if DASHBOARD_OPEN:
    # In ra stderr MỖI LẦN khởi động. Chế độ mở phải luôn nhìn thấy được - một
    # cảnh báo chỉ hiện một lần rồi thôi là một cảnh báo bị quên.
    print("\n" + "!" * 72
          + "\n  DASHBOARD_OPEN=1 - THE SERVER IS RUNNING UNAUTHENTICATED."
            "\n  Anyone who can reach /api/accounts gets 937 full names"
            " and their departments."
          + ("\n  (DASHBOARD_KEY IS set, but it is BEING IGNORED.)"
             if DASHBOARD_KEY else "")
          + "\n  Remove this variable before the server leaves 127.0.0.1.\n"
          + "!" * 72 + "\n", file=sys.stderr)


@dataclass(frozen=True)
class Principal:
    """AI đang gọi. Trả về ĐỐI TƯỢNG, không trả True/False.

    Hôm nay chỉ có một giá trị thật (`shared_key`), nên nhìn thì thừa. Nó không
    thừa vì ngày lên JWT theo người, `caller()` trả
    `Principal(kind='user', name='bh1.longnt')` và 8 endpoint không phải sửa
    một chữ. Trả boolean thì ngày đó phải mở lại từng endpoint để lấy tên người
    - tức là sửa 8 chỗ thay vì 1.
    """

    kind: str   # 'shared_key' | 'open_mode'  (mai sau: 'user')
    name: str


# auto_error=False là BẮT BUỘC, không phải tuỳ chọn phong cách.
#
# HTTPBearer mặc định (auto_error=True) trả **403** khi thiếu header, không phải
# 401 - và spec đòi 401. Để mặc định thì phép kiểm "gọi không khoá phải nhận
# 401" sẽ trượt vì một lý do chẳng liên quan gì tới xác thực.
_bearer = HTTPBearer(auto_error=False,
                     description="Dashboard key. Paste it into the 'Value' box,"
                                 " without the word 'Bearer'.")


def caller(cred: HTTPAuthorizationCredentials | None
              = Depends(_bearer)) -> Principal:
    """Kiểm chứng danh. Đây là hàm DUY NHẤT phải sửa khi lên JWT."""
    if DASHBOARD_OPEN:
        return Principal(kind="open_mode", name="unchecked")
    if cred is None or not cred.credentials:
        raise HTTPException(401, "Missing header 'Authorization: Bearer <key>'",
                            headers={"WWW-Authenticate": "Bearer"})
    # compare_digest chứ không phải `==`: phép so bằng của Python thoát ra ngay
    # ký tự đầu khác nhau, nên thời gian trả lời rò rỉ số ký tự đầu đã đoán đúng.
    #
    # PHẢI .encode() TRƯỚC. Đo ngày 21/08: compare_digest với hai chuỗi `str`
    # ném `TypeError: comparing strings with non-ASCII characters is not
    # supported`. Người gọi điều khiển được vế trái, nên chỉ cần gửi
    # `Authorization: Bearer á` là mọi endpoint trả 500 thay vì 401 - một đường
    # sập gọi được mà không cần biết khoá. Với `bytes` thì không có giới hạn đó.
    if not secrets.compare_digest(cred.credentials.encode("utf-8"),
                                  DASHBOARD_KEY.encode("utf-8")):
        raise HTTPException(401, "Wrong key",
                            headers={"WWW-Authenticate": "Bearer"})
    return Principal(kind="shared_key", name="dashboard")


app = FastAPI(
    title="Token Ledger API",
    version="1.0",
    description="Reads cost / token / performance data of the AI agents."
                " Read-only, never writes.",
)

# Dashboard mở bằng file:// (origin 'null') hoặc từ một cổng khác.
#
# TRƯỚC 20/08/2026 chỗ này là `allow_origins=["*"]`, và ghi chú tự biện minh:
# "chấp nhận được vì máy chủ chỉ lắng nghe trên 127.0.0.1". Lý do đó hết hiệu lực
# đúng vào ngày Gateway lên - kiến trúc đó có load balancer và nhiều instance,
# tức máy chủ này sẽ ra khỏi 127.0.0.1. Một biện minh gắn với một dòng cấu hình
# thì mất hiệu lực cùng lúc dòng cấu hình đó đổi, mà không ai được báo.
#
# Mặc định vẫn cho `null` (file://) và localhost để không phá cách chạy hiện tại.
# Đặt DASHBOARD_ORIGINS để siết lại, hoặc "*" để quay về hành vi cũ - nhưng khi đó
# là một lựa chọn tường minh, không phải một mặc định bị quên.
DEFAULT_ORIGINS = "null,http://127.0.0.1:8080,http://localhost:8080"
ALLOWED_ORIGINS = [o.strip() for o in
                   os.environ.get("DASHBOARD_ORIGINS", DEFAULT_ORIGINS).split(",")
                   if o.strip()]
app.add_middleware(
    CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["GET"],
    allow_headers=["*"],
)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def date_range(start: str | None, end: str | None) -> tuple[str, str]:
    """Kiểm và chuẩn hoá khoảng ngày.

    Kiểm định dạng tường minh chứ không thả thẳng xuống SQL. Tham số đã đi qua
    đặt chỗ nên không tiêm được, nhưng một chuỗi rác vẫn sẽ trả về bảng rỗng mà
    không ai hiểu tại sao - báo lỗi 400 thì người gọi biết ngay.
    """
    today = date.today()
    start = start or (today - timedelta(days=30)).isoformat()
    end = end or today.isoformat()
    for x in (start, end):
        # PHẢI phân tích thành ngày thật, không chỉ khớp hình dạng. Ban đầu chỉ
        # có regex \d{4}-\d{2}-\d{2} và '2026-13-99' lọt qua hết - trả về bảng
        # rỗng, không lỗi nào. Người gọi sẽ tưởng kỳ đó không có dữ liệu.
        if not DATE_RE.match(x):
            raise HTTPException(400, f"Date must look like YYYY-MM-DD, got {x!r}")
        try:
            date.fromisoformat(x)
        except ValueError:
            raise HTTPException(400, f"Not a real date: {x!r}")
    if start > end:
        start, end = end, start
    return start, end


@app.get("/healthz", summary="Is the server alive - returns NO business data")
def healthz():
    """Điểm thăm dò sống-chết. Endpoint DUY NHẤT không đòi khoá.

    KHÔNG dùng /api/health cho việc này. Tên hai cái giống nhau nhưng chúng trả
    lời hai câu khác hẳn:

        /healthz      "tiến trình này còn thở không"   -> giám sát, không khoá
        /api/health   "dữ liệu có gì, mới đến đâu,
                       thiếu chỗ nào"                  -> nghiệp vụ, PHẢI có khoá

    Nó cố tình KHÔNG chạm database: câu nó trả lời là về tiến trình, không phải
    về dữ liệu. Trả `ok` khi Postgres đã chết là đúng chức năng, không phải lỗi -
    thứ nói về dữ liệu là /api/health, và đó là lý do cái kia có khoá.
    """
    return {"status": "ok"}


@app.get("/api/health", summary="What data there is, how fresh, where the gaps are")
def health(who: Principal = Depends(caller)):
    with store.open_db() as (cn, _):
        return store.health(cn)


@app.get("/api/catalog", summary="Agents, models, units, FX rate - rarely change")
def catalog(who: Principal = Depends(caller)):
    with store.open_db() as (cn, _):
        return {"agents": store.agents(cn), "models": store.models(cn),
                "units": store.units(cn), "fx_rate": store.fx_rate(cn)}


@app.get("/api/usage", summary="Tokens and cost by day/agent/model")
def usage(start: str | None = Query(None, description="YYYY-MM-DD"),
          end: str | None = Query(None, description="YYYY-MM-DD"),
          who: Principal = Depends(caller)):
    start, end = date_range(start, end)
    with store.open_db() as (cn, ph):
        rows = store.usage(cn, ph, start, end)
    return {"start": start, "end": end, "count": len(rows), "rows": rows}


@app.get("/api/usage-hourly", summary="Tokens by HOUR - a date range is required")
def usage_hourly(start: str | None = Query(None, description="YYYY-MM-DD, REQUIRED"),
                 end: str | None = Query(None, description="YYYY-MM-DD, REQUIRED"),
                 who: Principal = Depends(caller)):
    """BAT BUOC co `start` va `end` - khong nhu cac endpoint khac.

    Cac endpoint theo ngay mac dinh 30 ngay gan nhat khi goi tran. O day thi
    KHONG: bang theo gio min gap ~24 lan, nen mot loi goi tran se keo ve hang
    nghin dong cho mot cau hoi ma nguoi goi chua kip nghi. Bat khai khoang la
    bat nguoi goi noi ra minh muon gi.

    BA NGUON, KHONG PHAI BON. `billing` khong co mat va se khong bao gio co -
    hoa don Google chi tinh theo ngay. Doc cot `source` de biet nguon nao co
    mat, dung gia dinh bang nay phu het luu luong.
    """
    missing = [t for t, v in (("start", start), ("end", end)) if not v]
    if missing:
        raise HTTPException(
            400,
            f"The hourly endpoint REQUIRES a time range. Missing: "
            f"{', '.join(missing)}. Example: /api/usage-hourly"
            f"?start=2026-08-31&end=2026-08-31")
    start, end = date_range(start, end)
    with store.open_db() as (cn, ph):
        rows = store.usage_hourly(cn, ph, start, end)
    by_source = {}
    for r in rows:
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1
    return {"start": start, "end": end, "count": len(rows),
            "sources": by_source, "rows": rows}


@app.get("/api/accounts", summary="Staff directory with units")
def accounts(who: Principal = Depends(caller)):
    with store.open_db() as (cn, _):
        return {"rows": store.accounts(cn)}


@app.get("/api/adoption", summary="Share of provisioned accounts that made requests")
def adoption(who: Principal = Depends(caller)):
    """KHONG nhan khoang ngay - day la chi tieu TICH LUY.

    Xem ghi chu o store.adoption(): ep no theo thanh truot ngay thi cung mot
    agent nhay tu 50% xuong 7% chi vi doi ky. Moi dong tra ve kem from_day/
    to_day de noi ro ty le tinh tren khoang nao.
    """
    with store.open_db() as (cn, _):
        return {"rows": store.adoption(cn)}


@app.get("/api/usage-by-account", summary="Usage attributed to each person")
def usage_by_account(start: str | None = None, end: str | None = None,
                     who: Principal = Depends(caller)):
    start, end = date_range(start, end)
    with store.open_db() as (cn, ph):
        rows = store.usage_by_account(cn, ph, start, end)
        h = store.health(cn)
    # Gắn cảnh báo độ phủ VÀO CHÍNH endpoint này, không để người gọi phải nhớ
    # sang hỏi /api/health. Đây là endpoint dễ sai nhất: nó trả về một bảng đầy
    # đủ và không có gì nói rằng nó chỉ thấy 5,7% lưu lượng.
    coverage = [w for w in h["warnings"] if w["code"] == "user_coverage"]
    return {"start": start, "end": end, "count": len(rows), "rows": rows,
            "warnings": coverage}


@app.get("/api/performance", summary="Response codes and latency - two different grains")
def performance(start: str | None = None, end: str | None = None,
                who: Principal = Depends(caller)):
    start, end = date_range(start, end)
    with store.open_db() as (cn, ph):
        result = store.performance(cn, ph, start, end)
    return {"start": start, "end": end, **result}


# `/api/thinking` GỠ 12/09/2026. Token suy luận và token ra là MỘT biến: hoá đơn
# không có SKU riêng cho suy nghĩ, nó nằm trong SKU output và tính theo giá output.
# Endpoint này trả về một lát cắt nằm sẵn trong `output_tokens` và không nơi nào
# đọc ra màn hình. Ghi chú đầy đủ ở `backend/store.py`, chỗ hàm `thinking()` cũ.
