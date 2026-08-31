"""Dung lai toan bo database tu DU LIEU DA THU THAP.

    docker compose up -d                                  # PHAI len truoc
    python scripts/rebuild_db.py                          # dung DEFAULT_DSN
    python scripts/rebuild_db.py --db postgresql://.../token_ledger_v2

DSN la gi
---------
Chuoi ket noi PostgreSQL. SQLite da bi go 24/08/2026 (change
`drop-the-sqlite-escape-hatch`) - dua vao mot duong dan .sqlite thi connect.py
dung ngay voi thong bao noi ro, chu khong im lang tao file.

Mac dinh lay tu connect.DEFAULT_DSN, KHONG khai rieng o day. Truoc 17/08/2026
file nay co hang so DSN cua rieng no, va scripts/update_dashboard.py goi no
khong truyen --db - nen doi connect.py xong ma duong ong van dung lai database
cu, khong loi nao bao ra.

NGUON DU LIEU
-------------
Toan bo lay tu thu muc data/, tuc nhung gi cac script pull_* da thu thap:

    data/da_xu_ly/billing/billing_<ngay>.csv          <- merge_billing.py
    data/da_xu_ly/du_lieu_giam_sat/<ngay>-gop/        <- merge_monitoring.py
    data/raw_web/ralli/<ngay>/                        <- pull_web_apps.py
    data/raw_web/tla-hd/<ngay>/                       <- pull_web_apps.py
    data/raw_web/tla-hd/<ngay>/usage-day-user-model.json  <- pull_hd_usage.py

Hai script pull_* ghi vao CUNG cay tla-hd nhung theo NGAY KEO cua rieng chung,
nen thu muc moi nhat co the chi chua mot file. Cac loader vi vay tim "dot moi
nhat CO DU file can" chu khong lay bua thu muc cuoi - xem `_latest` trong
db/load_org.py.

Moi script nap tu chon ban MOI NHAT, khong ghim ngay. Nhung `data/` KHONG len
git, nen mot ban clone thuan tuy chi dung duoc schema + danh muc (hai file .sql
co trong repo), khong co so lieu. Do la ranh gioi co chu dich: schema va danh
muc la MA, so lieu la DU LIEU.

CANH BAO VE MONITORING
----------------------
Nguon monitoring la thu muc DA GOP. No chi day du khi con giu ca dot keo cu:
cua so luu giu cua Google truot 91 ngay chi trong 7 ngay (do 06/08 thay 196
ngay, do 13/08 con 112). Du lieu 22/01-22/04 gio CHI con tren dia. Xoa thu muc
keo cu la mat vinh vien, khong dung lai duoc tu bat ky dau.

THU TU BAT BUOC
---------------
    1  load_billing --rebuild   xoa sach, dung schema + danh muc, nap hoa don
    2  load_org                 dim_unit / account / dim_user / dim_function
    3  load_ralli               fact_call
    4  load_hd                  fact_app_daily
    5  load_monitoring          fact_monitoring
    6  load_gateway             fact_call (nguon 'gateway')
    7  build_usage_daily        fact_usage_daily (bang dan xuat)
    8  build_performance        fact_perf_daily + fact_latency_daily

Buoc 1 phai dau vi --rebuild xoa sach. Buoc 2 truoc buoc 3-4 vi load_org xoa
fact_call, va vi ca hai buoc do deu tra account_id trong bang `account` do
load_org dung len. Hai buoc cuoi la bang DAN XUAT: chung doc cac bang tren chu
khong doc file, nen phai chay sau cung.

VI SAO CO RIENG MOT BUOC CHO TLA HD
-----------------------------------
Ralli phoi log TUNG LUOT GOI nen fact_call gop ra ngay nao cung duoc. TLA HD chi
phoi API da tong hop san, muc min nhat lay duoc la (ngay x nguoi x model) - nen
no vao bang rieng fact_app_daily. Hai duong cung do ve fact_usage_daily
source='app'. Chi tiet o db/load_hd.py.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

sys.path.insert(0, str(ROOT / "db"))

import connect  # noqa: E402

# (nhan, ten file, tham so rieng)
STEPS = [
    ("Hoa don",          "load_billing.py",      ["--rebuild"]),
    ("To chuc",          "load_org.py",          []),
    ("Nhat ky Ralli",    "load_ralli.py",        []),
    ("Su dung TLA HD",   "load_hd.py",           []),
    ("Monitoring",       "load_monitoring.py",   []),
    # PHAI dung TRUOC build_usage_daily: buoc do la bang DAN XUAT, no doc
    # fact_call. Va PHAI co mat o day - buoc 1 (`--rebuild`) xoa sach fact_call,
    # nen thieu dong nay thi moi lan cap nhat dashboard la du lieu Gateway bien
    # mat, khong loi nao bao. Bo nap tu do lai tu dau vi moc nap doc chinh
    # fact_call: bang rong -> doc toan bo so.
    ("So Gateway",       "load_gateway.py",      []),
    ("Tong hop su dung", "build_usage_daily.py", []),
    ("Hieu nang",        "build_performance.py", []),
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=connect.DEFAULT_DSN,
                   help="Chuoi ket noi PostgreSQL. Mac dinh: connect.DEFAULT_DSN")
    p.add_argument("--from-step", type=int, default=1,
                   help=f"Bat dau tu buoc N (1-{len(STEPS)}). Dung khi mot buoc hong va da sua xong.")
    args = p.parse_args()

    print("=" * 72)
    print("DUNG LAI DATABASE TU DU LIEU DA THU THAP")
    print("=" * 72)
    print(f"Dich: {connect.mask_dsn(args.db)}")
    if args.from_step > 1:
        print(f"Bat dau tu buoc {args.from_step} - CAC BUOC TRUOC BI BO QUA.")
        if args.from_step > 1 and "--rebuild" in STEPS[0][2]:
            print("Luu y: bo qua buoc 1 nghia la KHONG dung lai schema.")

    started = time.time()
    for i, (label, filename, extra_args) in enumerate(STEPS, start=1):
        if i < args.from_step:
            print(f"\n[{i}/{len(STEPS)}] {label} - bo qua")
            continue
        print(f"\n{'─' * 72}\n[{i}/{len(STEPS)}] {label}  ({filename})\n{'─' * 72}")
        # Tien trinh con ghi thang ra terminal con print() o day qua bo dem;
        # khong flush thi loi cua con hien truoc tieu de buoc.
        sys.stdout.flush()
        # DSN di qua BIEN MOI TRUONG, khong qua dong lenh: dong lenh cua mot
        # tien trinh nhin thay duoc tu ngoai (ps / Task Manager), nen dat DSN
        # Postgres o day la phoi mat khau ra ca 7 tien trinh con. Truoc
        # 17/08/2026 DSN la duong dan file nen khong co gi de lo.
        #
        # Con doc duoc vi connect.DEFAULT_DSN uu tien TOKEN_LEDGER_DSN, va --db
        # cua moi script nap mac dinh bang connect.DEFAULT_DSN.
        result = subprocess.run([PY, str(ROOT / "db" / filename), *extra_args],
                                 cwd=ROOT, env={**os.environ,
                                                "TOKEN_LEDGER_DSN": args.db})
        if result.returncode != 0:
            print(f"\n{'=' * 72}")
            print(f"DUNG o buoc {i} ({filename}), ma thoat {result.returncode}.")
            print(f"Sua xong chay lai tu day:  python scripts/rebuild_db.py "
                  f"--db <dsn> --from-step {i}")
            print("=" * 72)
            sys.exit(1)

    print(f"\n{'=' * 72}")
    print(f"XONG sau {time.time() - started:.0f}s."
          f" Ca {len(STEPS)} buoc deu dat nghiem thu.")
    print("=" * 72)


if __name__ == "__main__":
    main()
