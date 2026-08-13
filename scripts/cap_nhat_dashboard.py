"""Mot lenh: thu thap moi nguon roi cap nhat du lieu hardcode cua dashboard.

    python scripts/cap_nhat_dashboard.py

Chay tuan tu 7 buoc. HONG BUOC NAO LA DUNG NGAY - khong buoc nao chay tiep tren
dau ra dang do cua buoc truoc.

    0  Kiem hoa don da moi chua        (viec TAY duy nhat con lai)
    1  Kiem/lay token 2 web app        (lam TRUOC de hong thi hong som)
    2  Keo Cloud Monitoring            ~10-15 phut
    3  Gop cac dot keo Monitoring
    4  Keo Ralli + TLA Hop Dong
    5  Gop hoa don tu 7 file Console
    6  Sinh khoi du lieu cho dashboard
    7  Va vao app.js

VI SAO BUOC 0 VA 1 DUNG DAU
---------------------------
Buoc 2 mat hon 10 phut. Phat hien thieu file hoa don hoac token het han SAU do
la vut di 10 phut khong vi ly do gi. Ca hai phep kiem deu chi mat vai giay.

BILLING VAN PHAI TAI TAY
------------------------
Google Cloud Console khong cho tai bao cao GMSSub bang API voi quyen hien co.
Buoc 0 kiem ngay lon nhat trong data/billing/*.csv; cu hon hom qua thi dung han
va in ra viec can lam. Khong tu chay tiep voi hoa don cu, vi khi do dashboard se
co request cua hom nay nhung token cua tuan truoc - sai ma trong nhu that.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


class Hong(Exception):
    pass


def chay(nhan: str, lenh: list[str]) -> float:
    print(f"\n{'─' * 72}\n{nhan}\n{'─' * 72}")
    # Tien trinh con ghi thang ra terminal, con print() o day di qua bo dem.
    # Khong flush thi thong bao loi cua con HIEN TRUOC tieu de buoc, va nguoi
    # doc khong biet loi thuoc ve buoc nao.
    sys.stdout.flush()
    bat_dau = time.time()
    ket_qua = subprocess.run(lenh, cwd=ROOT)
    mat = time.time() - bat_dau
    if ket_qua.returncode != 0:
        raise Hong(f"{nhan} that bai (ma thoat {ket_qua.returncode}) sau {mat:.0f}s")
    print(f"  [xong sau {mat:.0f}s]")
    return mat


def kiem_billing(cho_phep_cu: bool) -> str:
    """Ngay lon nhat trong cac file hoa don tho. Dung neu qua cu."""
    thu_muc = ROOT / "data" / "billing"
    files = sorted(thu_muc.glob("*GMSSub*.csv"))
    if not files:
        raise Hong(
            f"Khong tim thay file hoa don nao trong {thu_muc}\n"
            f"  Vao Google Cloud Console > Billing > Reports, tai ve 7 file GMSSub\n"
            f"  (moi project mot file) roi bo vao thu muc tren."
        )

    lon_nhat = ""
    for f in files:
        with f.open(encoding="utf-8-sig", newline="") as h:
            for dong in csv.DictReader(h):
                ngay = (dong.get("Date") or "").strip()
                if ngay > lon_nhat:
                    lon_nhat = ngay

    hom_qua = (date.today() - timedelta(days=1)).isoformat()
    print(f"  {len(files)} file hoa don | ngay moi nhat: {lon_nhat}")
    if lon_nhat < hom_qua:
        if not cho_phep_cu:
            raise Hong(
                f"Hoa don CU: ngay moi nhat {lon_nhat}, dang le phai >= {hom_qua}.\n"
                f"  Tai lai 7 file GMSSub tu Google Cloud Console vao {thu_muc}\n"
                f"  roi chay lai. Neu co y muon dung hoa don cu, them --hoa-don-cu."
            )
        print(f"  CANH BAO: hoa don cu ({lon_nhat}), van chay tiep theo yeu cau.")
    return lon_nhat


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hoa-don-cu", action="store_true",
                   help="Van chay du hoa don chua duoc tai moi (mac dinh: dung)")
    p.add_argument("--bo-monitoring", action="store_true",
                   help="Bo qua buoc keo Monitoring (~10-15 phut). Van gop lai tu cac dot da co.")
    p.add_argument("--ngay-monitoring", type=int, default=196,
                   help="So ngay keo ve. Google chi giu mot phan, keo rong khong hai gi.")
    args = p.parse_args()

    tong = time.time()
    print("=" * 72)
    print("CAP NHAT DU LIEU DASHBOARD")
    print("=" * 72)

    try:
        print("\n[0/7] Kiem hoa don")
        kiem_billing(args.hoa_don_cu)

        # Buoc nay dang nhap mot lan roi vut token di; buoc 4 dang nhap lai.
        # Doi lai la biet ngay tu giay thu 5 rang xac thuc co chay duoc khong,
        # thay vi biet sau 15 phut. Hai lan dang nhap re hon nhieu so voi mot
        # lan keo Monitoring bi vut bo.
        chay("[1/7] Kiem token 2 web app",
             [PY, "scripts/pull_web_apps.py", "--chi-kiem-token"])

        if args.bo_monitoring:
            print("\n[2/7] Keo Monitoring - BO QUA theo yeu cau")
        else:
            chay("[2/7] Keo Cloud Monitoring",
                 [PY, "scripts/pull_monitoring.py",
                  "--days", str(args.ngay_monitoring), "--align", "60"])

        chay("[3/7] Gop cac dot keo Monitoring", [PY, "scripts/gop_monitoring.py"])
        chay("[4/7] Keo Ralli + TLA Hop Dong", [PY, "scripts/pull_web_apps.py"])
        chay("[5/7] Gop hoa don", [PY, "scripts/gop_billing.py"])
        chay("[6/7] Sinh khoi du lieu dashboard", [PY, "test/sinh_du_lieu_dashboard.py"])
        chay("[7/7] Va vao app.js", [PY, "test/va_app_js.py"])

    except Hong as e:
        print(f"\n{'=' * 72}\nDUNG: {e}\n{'=' * 72}")
        sys.exit(1)

    print(f"\n{'=' * 72}")
    print(f"XONG sau {(time.time() - tong) / 60:.1f} phut.")
    print("Mo index.html de xem. Neu so khong doi, xoa localStorage cua trang")
    print("(F12 > Application > Local Storage) - app.js co bump phien ban nhung")
    print("trinh duyet doi khi con giu ban cu.")
    print("=" * 72)


if __name__ == "__main__":
    main()
