"""API đọc database, phục vụ dashboard. CHỈ ĐỌC - không có endpoint ghi nào.

    pip install -r backend/requirements.txt
    python -m uvicorn backend.main:app --reload --port 8000

    http://127.0.0.1:8000/docs     tài liệu tự sinh, bấm thử được từng endpoint

Đổi database:
    set TOKEN_LEDGER_DSN=postgresql://token:token_local@127.0.0.1:5432/token_ledger

VÌ SAO CHỈ CHẠY TRÊN 127.0.0.1
------------------------------
Database này chứa danh sách 932 nhân viên kèm email và phòng ban. Nó không được
ra mạng. Uvicorn mặc định gắn 127.0.0.1; dùng `--host 0.0.0.0` là mở ra cả mạng
nội bộ, đừng làm nếu chưa bàn với ai.

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
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import store

app = FastAPI(
    title="Token Ledger API",
    version="1.0",
    description="Doc du lieu chi phi / token / hieu nang cua cac AI agent."
                " Chi doc, khong ghi.",
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
            raise HTTPException(400, f"Ngay phai dang YYYY-MM-DD, nhan duoc {x!r}")
        try:
            date.fromisoformat(x)
        except ValueError:
            raise HTTPException(400, f"Khong phai ngay co that: {x!r}")
    if start > end:
        start, end = end, start
    return start, end


@app.get("/api/health", summary="Du lieu co gi, moi den dau, thieu cho nao")
def health():
    with store.open_db() as (cn, _):
        return store.health(cn)


@app.get("/api/catalog", summary="Agent, model, don vi, ty gia - doi rat it")
def catalog():
    with store.open_db() as (cn, _):
        return {"agents": store.agents(cn), "models": store.models(cn),
                "units": store.units(cn), "fx_rate": store.fx_rate(cn)}


@app.get("/api/usage", summary="Token va chi phi theo ngay/agent/model")
def usage(start: str | None = Query(None, description="YYYY-MM-DD"),
          end: str | None = Query(None, description="YYYY-MM-DD")):
    start, end = date_range(start, end)
    with store.open_db() as (cn, ph):
        rows = store.usage(cn, ph, start, end)
    return {"start": start, "end": end, "count": len(rows), "rows": rows}


@app.get("/api/accounts", summary="Danh ba nhan vien kem don vi")
def accounts():
    with store.open_db() as (cn, _):
        return {"rows": store.accounts(cn)}


@app.get("/api/adoption", summary="Ty le tai khoan duoc cap co phat sinh request")
def adoption():
    """KHONG nhan khoang ngay - day la chi tieu TICH LUY.

    Xem ghi chu o store.adoption(): ep no theo thanh truot ngay thi cung mot
    agent nhay tu 50% xuong 7% chi vi doi ky. Moi dong tra ve kem from_day/
    to_day de noi ro ty le tinh tren khoang nao.
    """
    with store.open_db() as (cn, _):
        return {"rows": store.adoption(cn)}


@app.get("/api/usage-by-account", summary="Su dung quy ve tung nguoi")
def usage_by_account(start: str | None = None, end: str | None = None):
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


@app.get("/api/performance", summary="Ma tra ve va do tre - hai do min khac nhau")
def performance(start: str | None = None, end: str | None = None):
    start, end = date_range(start, end)
    with store.open_db() as (cn, ph):
        result = store.performance(cn, ph, start, end)
    return {"start": start, "end": end, **result}


@app.get("/api/thinking", summary="Token co bat che do thinking (chi Monitoring)")
def thinking(start: str | None = None, end: str | None = None):
    start, end = date_range(start, end)
    with store.open_db() as (cn, ph):
        return {"start": start, "end": end, "rows": store.thinking(cn, ph, start, end)}
