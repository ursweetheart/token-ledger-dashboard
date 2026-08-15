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
DUONG = "/api/admin/token-usage/stats"
TEN_FILE = "usage-day-user-model.json"

# Ngay dau tien co du lieu, do bang tay 14/08: timeline ca nam bat dau 03/2026.
# Lui them mot thang cho chac - thang rong chi ton mot luot GET.
NGAY_DAU = date(2026, 2, 1)

NGHI = 0.15   # giay giua hai luot GET. Lich su voi may chu noi bo.


class KhongKhop(Exception):
    """Server tra ve khoang ngay khac khoang da xin - tham so bi bo qua."""


def stats(cau_hinh: dict, token: str, tu: str, den: str, them: str = "") -> dict:
    """Mot luot GET period=custom. Kiem luon khoang tra ve co dung khong.

    Kiem o DAY chu khong o cho goi: neu API doi cach nhan tham so thi moi loi
    goi deu hong cung mot kieu, va bat mot cho thi khong the quen cho nao.
    """
    q = f"?period=custom&date_from={tu}&date_to={den}{them}"
    goi = json.loads(P.lay(cau_hinh["goc"], DUONG + q, token))
    time.sleep(NGHI)
    if (goi.get("date_from"), goi.get("date_to")) != (tu, den):
        raise KhongKhop(
            f"xin {tu}..{den} nhung server tra {goi.get('date_from')}.."
            f"{goi.get('date_to')} - tham so bi bo qua, KHONG duoc nap so nay")
    return goi


def by_model(goi: dict) -> list:
    """by_model nam trong `costs`. Doc nham tang tra ve [] mot cach im lang."""
    return (goi.get("costs") or {}).get("by_model") or []


def cac_thang(tu: date, den: date):
    """Sinh (dau_thang, cuoi_thang) cat theo `den`."""
    moc = tu.replace(day=1)
    while moc <= den:
        sau = (moc.replace(day=28) + timedelta(days=4)).replace(day=1)
        yield moc, min(sau - timedelta(days=1), den)
        moc = sau


def ngay_co_luot(cau_hinh: dict, token: str, tu: date, den: date) -> list[str]:
    """Hoi theo THANG de biet ngay nao co luot, thay vi hoi tung ngay mot.

    166 ngay -> 7 luot GET thay vi 166. Timeline cua khoang mot thang co
    bucket='day', da kiem: ca 6 thang deu tra bucket=day.
    """
    ra = []
    for dau, cuoi in cac_thang(tu, den):
        goi = stats(cau_hinh, token, dau.isoformat(), cuoi.isoformat())
        buc = goi.get("bucket")
        if buc != "day":
            raise SystemExit(
                f"Thang {dau:%m/%Y} tra bucket={buc!r}, mong doi 'day'."
                f" Khong suy ra duoc ngay nao co luot - dung lai.")
        co = [t["timestamp"][:10] for t in (goi.get("timeline") or []) if t.get("calls")]
        ra.extend(co)
        print(f"  {dau:%m/%Y}  {goi['totals']['call_count']:>6,} luot"
              f"  {len(co):>3} ngay co du lieu")
    return sorted(set(ra))


def keo(cau_hinh: dict, token: str, ngay: str) -> tuple[list[dict], int]:
    """Mot ngay -> danh sach dong (ngay, nguoi, model). Tra ca tong luot de doi chieu.

    TIET KIEM LUOT GOI: chi hoi rieng tung nguoi khi THAT SU can.
      - ngay chi co 1 nguoi  -> by_model cua ca ngay CHINH LA cua nguoi do
      - ngay chi co 1 model  -> moi nguoi deu dung model do
      - con lai              -> hoi tung nguoi mot
    Hai loi tat tren khong phai uoc luong: chung dung ve mat toan hoc khi mot
    trong hai chieu chi co mot gia tri.
    """
    goi = stats(cau_hinh, token, ngay, ngay)
    tong = goi["totals"]["call_count"]
    nguoi = goi.get("by_user") or []
    models = by_model(goi)
    dong = []

    if len(nguoi) == 1:
        u = nguoi[0]
        for m in models:
            dong.append(_dong(ngay, u, m))
    elif len(models) == 1:
        m0 = models[0]
        for u in nguoi:
            # Chia theo NGUOI, khong theo model: model chi co mot nen moi token
            # cua nguoi nay deu thuoc no. Lay so tu by_user - do la so do that
            # cua chinh nguoi do, khong phai phan bo tu tong.
            dong.append(_dong(ngay, u, {
                "model": m0["model"], "calls": u["calls"],
                "total_tokens": u["total_tokens"],
                "prompt_tokens": u.get("prompt_tokens"),
                "completion_tokens": u.get("completion_tokens")}))
    else:
        for u in nguoi:
            uid = u.get("user_id")
            if not uid:
                # Khong co user_id thi khong loc duoc. Giu nguyen dong nguoi do
                # voi model rong - load_hd.py se doi no thanh tai khoan
                # 'unattributed', chu khong am tham gan bua vao mot model.
                dong.append(_dong(ngay, u, {"model": None, "calls": u["calls"],
                                            "total_tokens": u["total_tokens"],
                                            "prompt_tokens": u.get("prompt_tokens"),
                                            "completion_tokens": u.get("completion_tokens")}))
                continue
            r = stats(cau_hinh, token, ngay, ngay, f"&user_id={uid}")
            for m in by_model(r):
                dong.append(_dong(ngay, u, m))
    return dong, tong


def _dong(ngay: str, u: dict, m: dict) -> dict:
    return {
        "day": ngay,
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
    p.add_argument("--lat-mong", action="store_true",
                   help="Chi keo thang gan nhat. Dung cho vong tu soat.")
    p.add_argument("--den-ngay", default=date.today().isoformat(),
                   help="Ngay cuoi, mac dinh hom nay.")
    args = p.parse_args()

    den = date.fromisoformat(args.den_ngay)
    tu = den.replace(day=1) if args.lat_mong else NGAY_DAU

    cau_hinh = P.NGUON[APP]
    env = {**P.doc_env(P.ENV_FILE), **os.environ}
    token, nguon = P.lay_token(APP, cau_hinh, env)
    print(f"Token: {nguon} - {P.het_han(token)}")
    print(f"Khoang: {tu} -> {den}\n")

    print("Buoc 1/2  Hoi theo thang de biet ngay nao co luot")
    ngay = ngay_co_luot(cau_hinh, token, tu, den)
    print(f"  -> {len(ngay)} ngay co du lieu\n")

    print(f"Buoc 2/2  Keo tung ngay ({len(ngay)} ngay)")
    tat_ca, tong_ngay = [], {}
    for i, d in enumerate(ngay, start=1):
        dong, tong = keo(cau_hinh, token, d)
        tat_ca.extend(dong)
        tong_ngay[d] = tong
        print(f"  [{i:>3}/{len(ngay)}] {d}  {tong:>5,} luot"
              f"  {len(dong):>3} dong (nguoi x model)")

    # ── NGHIEM THU ────────────────────────────────────────────────────
    # Tong cong lai tu cac dong PHAI bang tong server bao cho tung ngay.
    # Khong ghim so cung: doi chieu voi chinh cau tra loi cua server o moi lan
    # chay, nen phep kiem nay khong loi thoi khi co du lieu moi.
    loi = []
    for d, tong in tong_ngay.items():
        co = sum(x["calls"] or 0 for x in tat_ca if x["day"] == d)
        if co != tong:
            loi.append(f"{d}: gop duoc {co} luot != {tong} server bao")

    thieu_model = [x for x in tat_ca if not x["model"]]
    if thieu_model:
        print(f"\n  LUU Y: {len(thieu_model)} dong khong xac dinh duoc model"
              f" ({sum(x['calls'] or 0 for x in thieu_model)} luot).")

    if loi:
        raise SystemExit("NGHIEM THU KHONG DAT - khong ghi file:\n  "
                         + "\n  ".join(loi[:20]))

    thu_muc = ROOT / "data" / "raw_web" / APP / date.today().isoformat()
    thu_muc.mkdir(parents=True, exist_ok=True)
    ra = thu_muc / TEN_FILE
    ra.write_text(json.dumps({
        "keo_luc": datetime.now().isoformat(timespec="seconds"),
        "tu_ngay": tu.isoformat(), "den_ngay": den.isoformat(),
        "tong_luot": sum(tong_ngay.values()),
        "rows": tat_ca,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\nNGHIEM THU DAT - {len(tat_ca)} dong,"
          f" {sum(tong_ngay.values()):,} luot,"
          f" {sum(x['total_tokens'] or 0 for x in tat_ca):,} token")
    print(f"Da ghi: {ra.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
