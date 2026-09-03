"""Lam moi duong Gateway: so LiteLLM -> fact_call -> fact_usage_daily.

    python scripts/refresh_gateway.py
    python scripts/refresh_gateway.py --every 120     # che do vong lap

VI SAO CO FILE NAY

Sau khi mot agent goi qua Gateway, du lieu vao so cua Gateway NGAY (bat dong bo
~4 giay), nhung dashboard thi khong tu doi - phai chay hai lenh, dung thu tu.
Nho mot lenh de hon nho hai, va quen buoc 2 thi so cu nam nguyen tren dashboard
ma khong co dau hieu gi.

Do 31/08/2026: ca chu ky mat ~0,8 giay (271 ms + 520 ms). Nen chay dinh ky la
re, khong can toi uu gi them.

DUNG NGAY NEU BUOC 1 HONG

`build_usage_daily.py` XOA SACH fact_usage_daily roi dung lai. Neu load_gateway
hong (vi du Gateway dang tat) ma van chay buoc 2, ta se dung lai bang tong hop
tu mot fact_call THIEU du lieu Gateway - va ket qua trong y het "chua co luu
luong". Tha dung lai voi so cu con dung.

KHONG PHAI BAN THAY THE rebuild_db.py

`rebuild_db.py` dung lai CA database tu file du lieu (78 giay). File nay chi lam
moi duong Gateway tren database dang co (~0,8 giay). Hai viec khac nhau.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "db"))

import connect  # noqa: E402

PY = sys.executable
STEPS = [
    ("Nap so Gateway", "load_gateway.py"),
    ("Tong hop su dung", "build_usage_daily.py"),
]


def dem(dsn: str) -> tuple[int, int, int]:
    """(dong fact_call gateway, token, dong fact_usage_daily gateway)."""
    cn, _ = connect.open_db(dsn)
    try:
        n, tok = connect.query_one(
            cn, "SELECT COUNT(*), COALESCE(SUM(total_tokens), 0)"
                " FROM fact_call WHERE source = 'gateway'")
        agg = connect.query_one(
            cn, "SELECT COUNT(*) FROM fact_usage_daily WHERE source = 'gateway'")[0]
        return int(n), int(tok), int(agg)
    finally:
        cn.close()


def mot_luot(dsn: str, im_lang: bool) -> int:
    truoc = dem(dsn)
    for nhan, ten in STEPS:
        # encoding PHAI dat tuong minh: mac dinh cua subprocess la codepage cua
        # console (cp1252 tren may nay), ma hai buoc deu in tieng Viet. Thieu no
        # thi luong doc nem UnicodeDecodeError - va mat dung doan chan doan can
        # xem nhat khi co su co.
        r = subprocess.run([PY, str(ROOT / "db" / ten)],
                           capture_output=im_lang, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(f"FAILED at step '{nhan}' ({ten}), exit code {r.returncode}."
                  f" DUNG LAI - khong tong hop tren du lieu thieu.")
            # In CA hai luong. Traceback nam o stderr; in moi stdout la giau
            # dung thu can xem.
            for luong in (r.stdout, r.stderr):
                if im_lang and luong:
                    print(luong.rstrip())
            return r.returncode
    sau = dem(dsn)

    print(f"  fact_call gateway  {truoc[0]:>6} -> {sau[0]:<6} (+{sau[0] - truoc[0]})"
          f"  | token {truoc[1]:,} -> {sau[1]:,}")
    print(f"  fact_usage_daily   {truoc[2]:>6} -> {sau[2]:<6} gateway rows")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default=connect.DEFAULT_DSN)
    p.add_argument("--every", type=int, default=0,
                   help="Chay lap lai moi N giay. 0 = chay mot lan roi thoat.")
    p.add_argument("--quiet", action="store_true",
                   help="Nuot dau ra cua hai buoc, chi in tom tat")
    args = p.parse_args()

    if not args.every:
        return mot_luot(args.db, args.quiet)

    print(f"Looping every {args.every}s. Ctrl-C to stop.")
    while True:
        # Bat CA loi cua dem(): database co the dang khoi dong lai, va mot vong
        # lap chet vi mot luot hong la mat luon co che tu dong.
        try:
            ma = mot_luot(args.db, True)
        except Exception as exc:
            print(f"  ERROR: {type(exc).__name__}: "
                  f"{str(exc).strip().splitlines()[0]}")
            ma = 1
        if ma != 0:
            print(f"  (retrying in {args.every}s)")
        time.sleep(args.every)


if __name__ == "__main__":
    raise SystemExit(main())
