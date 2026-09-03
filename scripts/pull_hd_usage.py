"""Keo so lieu su dung cua TLA Hop Dong o muc NGAY x NGUOI x MODEL. CHI GET.

    python scripts/pull_hd_usage.py              # keo day du
    python scripts/pull_hd_usage.py --lat-mong   # 1 thang, de thu nhanh

VI SAO CAN SCRIPT RIENG
-----------------------
pull_web_apps.py keo cac trang tong hop san (period=day|week|month|year). Chung
KHONG du de dung fact_usage_daily cho TLA HD:

    token-usage-year.json    by_user la tong CA KY, bucket=thang
    token-usage-month.json   chi thang hien tai

Nghia la khong co chieu NGAY x NGUOI x MODEL - dung khoang trong ma
build_usage_daily.py ghi lai la "quyet dinh N5 hoan lai". Script nay dong no.

Ralli khong can script nay: no phoi log TUNG LUOT GOI, gop ra ngay nao cung duoc.

CACH LAY - da do bang tay truoc khi viet (14/08)
-----------------------------------------------
    ?period=custom&date_from=A&date_to=B      <- DUOC. Tra dung khoang xin.
    ?period=day&date=...                      <- bi BO QUA, tra ve hom nay
    ?date_from=...&date_to=...  (thieu period) <- bi BO QUA, tra ve ca thang
    &user_id=<uuid>                           <- DUOC. Khop chinh xac by_user.

CAI BAY DA GAP, DUNG DAM VAO LAI
--------------------------------
1. `by_model` nam TRONG khoi `costs`, khong o goc phan hoi. Doc nham tang tra
   ve [] mot cach im lang - trong y het "API khong tra model".
2. Tham so la KHONG bi bao loi, chi bi bo qua. Nen moi lan goi deu phai so
   date_from/date_to server tra ve voi khoang minh xin.

AN TOAN
-------
Dung ham lay() cua pull_web_apps: method="GET" tuong minh. POST duy nhat la
/api/auth/login de doi token, dung ngoai le da thong nhat. Token khong bao gio
in ra man hinh hay ghi xuong dia.

DAU RA
------
    data/raw_web/tla-hd/<YYYY-MM-DD>/usage-day-user-model.json

Ghi vao thu muc theo NGAY KEO, giong moi script pull_* khac. File nay doc boi
db/load_hd.py.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pull_web_apps as P  # noqa: E402

APP = "tla-hd"
API_PATH = "/api/admin/token-usage/stats"
OUT_FILE = "usage-day-user-model.json"

# Ngay dau tien co du lieu, do bang tay 14/08: timeline ca nam bat dau 03/2026.
# Lui them mot thang cho chac - thang rong chi ton mot luot GET.
FIRST_DAY = date(2026, 2, 1)

SLEEP_BETWEEN = 0.15   # giay giua hai luot GET. Lich su voi may chu noi bo.


class Mismatch(Exception):
    """Server tra ve khoang ngay khac khoang da xin - tham so bi bo qua."""


def stats(config: dict, token: str, start: str, end: str, extra: str = "") -> dict:
    """Mot luot GET period=custom. Kiem luon khoang tra ve co dung khong.

    Kiem o DAY chu khong o cho goi: neu API doi cach nhan tham so thi moi loi
    goi deu hong cung mot kieu, va bat mot cho thi khong the quen cho nao.
    """
    q = f"?period=custom&date_from={start}&date_to={end}{extra}"
    payload = json.loads(P.http_get(config["goc"], API_PATH + q, token))
    time.sleep(SLEEP_BETWEEN)
    if (payload.get("date_from"), payload.get("date_to")) != (start, end):
        raise Mismatch(
            f"xin {start}..{end} nhung server tra {payload.get('date_from')}.."
            f"{payload.get('date_to')} - tham so bi bo qua, KHONG duoc nap so nay")
    return payload


def by_model(payload: dict) -> list:
    """by_model nam trong `costs`. Doc nham tang tra ve [] mot cach im lang."""
    return (payload.get("costs") or {}).get("by_model") or []


def month_spans(start: date, end: date):
    """Sinh (dau_thang, cuoi_thang) cat theo `den`."""
    cursor = start.replace(day=1)
    while cursor <= end:
        next_month = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
        yield cursor, min(next_month - timedelta(days=1), end)
        cursor = next_month


def days_with_calls(config: dict, token: str, start: date, end: date) -> list[str]:
    """Hoi theo THANG de biet ngay nao co luot, thay vi hoi tung ngay mot.

    166 ngay -> 7 luot GET thay vi 166. Timeline cua khoang mot thang co
    bucket='day', da kiem: ca 6 thang deu tra bucket=day.
    """
    out_path = []
    for marker, span_end in month_spans(start, end):
        payload = stats(config, token, marker.isoformat(), span_end.isoformat())
        buc = payload.get("bucket")
        if buc != "day":
            raise SystemExit(
                f"Thang {marker:%m/%Y} tra bucket={buc!r}, mong doi 'day'."
                f" could not derive which days have calls - stopping.")
        days_present = [t["timestamp"][:10] for t in (payload.get("timeline") or []) if t.get("calls")]
        out_path.extend(days_present)
        print(f"  {marker:%m/%Y}  {payload['totals']['call_count']:>6,} calls"
              f"  {len(days_present):>3} ngay co du lieu")
    return sorted(set(out_path))


def pull_day(config: dict, token: str, day: str) -> tuple[list[dict], int]:
    """Mot ngay -> danh sach dong (ngay, nguoi, model). Tra ca tong luot de doi chieu.

    TIET KIEM LUOT GOI: chi hoi rieng tung nguoi khi THAT SU can.
      - ngay chi co 1 nguoi  -> by_model cua ca ngay CHINH LA cua nguoi do
      - ngay chi co 1 model  -> moi nguoi deu dung model do
      - con lai              -> hoi tung nguoi mot
    Hai loi tat tren khong phai uoc luong: chung dung ve mat toan hoc khi mot
    trong hai chieu chi co mot gia tri.
    """
    payload = stats(config, token, day, day)
    total = payload["totals"]["call_count"]
    by_user = payload.get("by_user") or []
    models = by_model(payload)
    rows = []

    if len(by_user) == 1:
        u = by_user[0]
        for m in models:
            rows.append(_make_row(day, u, m))
    elif len(models) == 1:
        m0 = models[0]
        for u in by_user:
            # Chia theo NGUOI, khong theo model: model chi co mot nen moi token
            # cua nguoi nay deu thuoc no. Lay so tu by_user - do la so do that
            # cua chinh nguoi do, khong phai phan bo tu tong.
            rows.append(_make_row(day, u, {
                "model": m0["model"], "calls": u["calls"],
                "total_tokens": u["total_tokens"],
                "prompt_tokens": u.get("prompt_tokens"),
                "completion_tokens": u.get("completion_tokens")}))
    else:
        for u in by_user:
            uid = u.get("user_id")
            if not uid:
                # Khong co user_id thi khong loc duoc. Giu nguyen dong nguoi do
                # voi model rong - load_hd.py se doi no thanh tai khoan
                # 'unattributed', chu khong am tham gan bua vao mot model.
                rows.append(_make_row(day, u, {"model": None, "calls": u["calls"],
                                            "total_tokens": u["total_tokens"],
                                            "prompt_tokens": u.get("prompt_tokens"),
                                            "completion_tokens": u.get("completion_tokens")}))
                continue
            r = stats(config, token, day, day, f"&user_id={uid}")
            for m in by_model(r):
                rows.append(_make_row(day, u, m))
    return rows, total


def _make_row(day: str, u: dict, m: dict) -> dict:
    return {
        "day": day,
        "user_id": u.get("user_id"),
        "username": u.get("username"),
        "model": m.get("model"),
        "calls": m.get("calls"),
        "total_tokens": m.get("total_tokens"),
        # Quy tac 5: truong vang mat -> None, KHONG phai 0.
        "prompt_tokens": m.get("prompt_tokens"),
        "completion_tokens": m.get("completion_tokens"),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lat-mong", dest="thin_slice", action="store_true",
                   help="Chi keo thang gan nhat. Dung cho vong tu soat.")
    p.add_argument("--den-ngay", default=date.today().isoformat(),
                   help="Ngay cuoi, mac dinh hom nay.")
    args = p.parse_args()

    end = date.fromisoformat(args.den_ngay)
    start = end.replace(day=1) if args.thin_slice else FIRST_DAY

    config = P.SOURCES[APP]
    env = {**P.read_env(P.ENV_FILE), **os.environ}
    token, source = P.get_token(APP, config, env)
    print(f"Token: {source} - {P.expires_in(token)}")
    print(f"range: {start} -> {end}\n")

    print("step 1/2  query by month to find which days have calls")
    day = days_with_calls(config, token, start, end)
    print(f"  -> {len(day)} days with data\n")

    print(f"step 2/2  pull each day ({len(day)} days)")
    all_rows, total_by_day = [], {}
    for i, d in enumerate(day, start=1):
        rows, total = pull_day(config, token, d)
        all_rows.extend(rows)
        total_by_day[d] = total
        print(f"  [{i:>3}/{len(day)}] {d}  {total:>5,} calls"
              f"  {len(rows):>3} dong (nguoi x model)")

    # ── NGHIEM THU ────────────────────────────────────────────────────
    # Tong cong lai tu cac dong PHAI bang tong server bao cho tung ngay.
    # Khong ghim so cung: doi chieu voi chinh cau tra loi cua server o moi lan
    # chay, nen phep kiem nay khong loi thoi khi co du lieu moi.
    errors = []
    for d, total in total_by_day.items():
        days_present = sum(x["calls"] or 0 for x in all_rows if x["day"] == d)
        if days_present != total:
            errors.append(f"{d}: rows sum to {days_present} calls != {total} reported by the server")

    missing_model = [x for x in all_rows if not x["model"]]
    if missing_model:
        print(f"\n  NOTE: {len(missing_model)} rows have no identifiable model"
              f" ({sum(x['calls'] or 0 for x in missing_model)} luot).")

    if errors:
        raise SystemExit("ACCEPTANCE FAILED - no file written:\n  "
                         + "\n  ".join(errors[:20]))

    folder = ROOT / "data" / "raw_web" / APP / date.today().isoformat()
    folder.mkdir(parents=True, exist_ok=True)
    out_path = folder / OUT_FILE
    out_path.write_text(json.dumps({
        "keo_luc": datetime.now().isoformat(timespec="seconds"),
        "tu_ngay": start.isoformat(), "den_ngay": end.isoformat(),
        "tong_luot": sum(total_by_day.values()),
        "rows": all_rows,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\nacceptance passed - {len(all_rows)} rows,"
          f" {sum(total_by_day.values()):,} luot,"
          f" {sum(x['total_tokens'] or 0 for x in all_rows):,} token")
    print(f"wrote: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
