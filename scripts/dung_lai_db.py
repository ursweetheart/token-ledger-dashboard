"""Dung lai toan bo database tu DU LIEU DA THU THAP, cho SQLite hoac PostgreSQL.

    python scripts/dung_lai_db.py                          # SQLite mac dinh
    python scripts/dung_lai_db.py --db "postgresql://token:token_local@127.0.0.1:5432/token_ledger"

DSN la gi
---------
Chuoi ket noi. ket_noi.py phan biet bang duoi file: `.sqlite`/`.db` thi mo
SQLite, con lai coi la chuoi PostgreSQL. Nho vay cung mot bo script nap chay
duoc ca hai he ma khong sua dong SQL nao.

NGUON DU LIEU
-------------
Toan bo lay tu thu muc data/, tuc nhung gi cac script pull_* da thu thap:

    data/da_xu_ly/billing/billing_<ngay>.csv          <- gop_billing.py
    data/da_xu_ly/du_lieu_giam_sat/<ngay>-gop/        <- gop_monitoring.py
    data/raw_web/ralli/<ngay>/                        <- pull_web_apps.py
    data/raw_web/tla-hd/<ngay>/                       <- pull_web_apps.py

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
    1  nap_billing --dung-lai   xoa sach, dung schema + danh muc, nap hoa don
    2  nap_to_chuc              dim_unit / dim_user / dim_function
    3  nap_ralli                fact_call
    4  nap_monitoring           fact_monitoring
    5  dung_usage_daily         fact_usage_daily (bang dan xuat, chay cuoi)

Buoc 1 phai dau vi --dung-lai xoa sach. Buoc 2 truoc buoc 3 vi nap_to_chuc xoa
fact_call, dao lai la mat dung cai vua nap. Buoc 5 cuoi vi no doc hai bang kia.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

# (nhan, ten file, tham so rieng)
BUOC = [
    ("Hoa don",          "nap_billing.py",      ["--dung-lai"]),
    ("To chuc",          "nap_to_chuc.py",      []),
    ("Nhat ky Ralli",    "nap_ralli.py",        []),
    ("Monitoring",       "nap_monitoring.py",   []),
    ("Tong hop su dung", "dung_usage_daily.py", []),
]


def che(dsn: str) -> str:
    """Giau mat khau khi in DSN ra man hinh."""
    if "://" not in dsn or "@" not in dsn:
        return dsn
    dau, sau = dsn.split("://", 1)
    thong_tin, may = sau.split("@", 1)
    nguoi = thong_tin.split(":", 1)[0]
    return f"{dau}://{nguoi}:***@{may}"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=str(ROOT / "db" / "token_ledger.sqlite"),
                   help="DSN. Duoi .sqlite/.db -> SQLite, con lai -> PostgreSQL")
    p.add_argument("--tu-buoc", type=int, default=1,
                   help="Bat dau tu buoc N (1-5). Dung khi mot buoc hong va da sua xong.")
    args = p.parse_args()

    print("=" * 72)
    print("DUNG LAI DATABASE TU DU LIEU DA THU THAP")
    print("=" * 72)
    print(f"Dich: {che(args.db)}")
    if args.tu_buoc > 1:
        print(f"Bat dau tu buoc {args.tu_buoc} - CAC BUOC TRUOC BI BO QUA.")
        if args.tu_buoc > 1 and "--dung-lai" in BUOC[0][2]:
            print("Luu y: bo qua buoc 1 nghia la KHONG dung lai schema.")

    bat_dau = time.time()
    for i, (nhan, ten_file, rieng) in enumerate(BUOC, start=1):
        if i < args.tu_buoc:
            print(f"\n[{i}/5] {nhan} - bo qua")
            continue
        print(f"\n{'─' * 72}\n[{i}/5] {nhan}  ({ten_file})\n{'─' * 72}")
        # Tien trinh con ghi thang ra terminal con print() o day qua bo dem;
        # khong flush thi loi cua con hien truoc tieu de buoc.
        sys.stdout.flush()
        ket_qua = subprocess.run([PY, str(ROOT / "db" / ten_file), "--db", args.db,
                                  *rieng], cwd=ROOT)
        if ket_qua.returncode != 0:
            print(f"\n{'=' * 72}")
            print(f"DUNG o buoc {i} ({ten_file}), ma thoat {ket_qua.returncode}.")
            print(f"Sua xong chay lai tu day:  python scripts/dung_lai_db.py "
                  f"--db <dsn> --tu-buoc {i}")
            print("=" * 72)
            sys.exit(1)

    print(f"\n{'=' * 72}")
    print(f"XONG sau {time.time() - bat_dau:.0f}s. Ca 5 buoc deu dat nghiem thu.")
    print("=" * 72)


if __name__ == "__main__":
    main()
