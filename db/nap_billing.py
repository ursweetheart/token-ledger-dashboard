"""Nap hoa don Google vao fact_billing_daily - chi doc file, khong goi mang.

QUY TAC AP DUNG (docs/plan-xay-dung-database-2026-08-07.md muc 4.6)
------------------------------------------------------------------
Quy tac 1  Token va tien luon lay tu billing. Day la nguon chan ly ve tien.
Quy tac 4  Billing tach 2 SKU: input rieng, cached rieng. Khong cong san.
Quy tac 8  Thu tu phan loai BAT BUOC: cached -> output -> input.

NGAY O DAY LA GIO MY, KHONG PHAI GIO VIET NAM
---------------------------------------------
Cot `ngay` chep NGUYEN cot `date` cua Google, tuc ngay theo mui gio Thai Binh
Duong. Da chung minh: 284/316 ngay khop tuyet doi voi monitoring khi gia dinh
Pacific, so voi 34/294 neu gia dinh UTC. Xem docs/mui-gio-2026-08-08.md muc M1.

KHONG quy doi o day. Quy doi sang ngay ICT la viec cua tang sau, va no can
monitoring muc phut de rai lai - thu ma bang nay khong co.

NGHIEM THU
----------
    SELECT ROUND(SUM(chi_phi_usd), 4) FROM fact_billing_daily;   -- 270.9517
    SELECT COUNT(*) FROM fact_billing_daily;                     -- 2259
"""

from __future__ import annotations

import argparse
import collections
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ket_noi  # noqa: E402
from quy_tac import suy_loai  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _billing_moi_nhat() -> Path:
    """File gop moi nhat do scripts/gop_billing.py sinh ra.

    Nguon cu la data/billing/billing_gop_tru_CTDA.csv - ban gop TAY, khong con
    ton tai. File moi mang cung du lieu nhung KHAC TEN COT:
        date -> ngay | sku -> sku_ten | amount -> so_luong | cost -> chi_phi_usd
    """
    thu_muc = ROOT / "data" / "da_xu_ly" / "billing"
    ung_vien = sorted(thu_muc.glob("billing_*.csv"))
    if not ung_vien:
        raise SystemExit(f"Khong co file gop nao trong {thu_muc}."
                         f" Chay scripts/gop_billing.py truoc.")
    return ung_vien[-1]


BILLING = _billing_moi_nhat()

# KHONG con TONG_MONG_DOI/DONG_MONG_DOI ghim cung (270.9517 / 2259). Hai so do
# dung cho dot du lieu 05/08 va lam script DUNG moi khi co hoa don moi - tuc no
# chan dung viec no phai bao ve. Nay so mong doi lay tu CHINH FILE NGUON, nen
# phep kiem van bat duoc dong roi rot giua file va database ma khong lo thoi.


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=ket_noi.MAC_DINH,
                   help="Duong dan .sqlite, hoac chuoi ket noi PostgreSQL")
    p.add_argument("--file", default=str(BILLING))
    p.add_argument("--dung-lai", action="store_true",
                   help="Xoa sach va dung lai schema + danh muc truoc khi nap")
    args = p.parse_args()

    if args.dung_lai:
        cn, dc = ket_noi.dung_lai(args.db)
        print(f"Da dung lai schema + danh muc tren {args.db}")
    else:
        cn, dc = ket_noi.mo(args.db)

    tra = ket_noi.tra_model(cn)

    with open(args.file, encoding="utf-8-sig") as h:
        rows = list(csv.DictReader(h))

    ban_ghi = []
    khong_model = collections.Counter()
    khong_loai = collections.Counter()
    for r in rows:
        loai = suy_loai(r["sku_ten"])
        if loai is None:
            khong_loai[r["sku_id"]] += 1
            continue
        model_id = tra.get(("billing_sku", r["sku_id"]))
        if model_id is None:
            khong_model[r["sku_id"]] += 1
        ban_ghi.append((r["ngay"], r["project"], r["sku_id"], r["sku_ten"], model_id,
                        loai, int(float(r["so_luong"])), float(r["chi_phi_usd"])))

    # Mot SKU khong tra ra model nghia la danh muc da cu so voi hoa don. Dung han:
    # nap tiep se cho ra mot bang co dong model_id NULL trong im lang, va moi bieu
    # do "chi phi theo model" sau do deu thieu tien ma khong bao gi.
    if khong_model or khong_loai:
        raise SystemExit(
            "SKU chua co trong danh muc - chay lai python db/sinh_02_danh_muc.py:\n"
            f"  khong ra model: {dict(khong_model)}\n"
            f"  khong ra loai : {dict(khong_loai)}"
        )

    cur = cn.cursor()
    cur.execute("DELETE FROM fact_billing_daily")
    cur.executemany(
        f"INSERT INTO fact_billing_daily (ngay, project, sku_id, sku_ten, model_id,"
        f" loai, so_luong, chi_phi_usd) VALUES ({','.join([dc] * 8)})", ban_ghi)
    cn.commit()

    cur.execute("SELECT COUNT(*), SUM(chi_phi_usd) FROM fact_billing_daily")
    n, tong = cur.fetchone()
    cur.execute("SELECT loai, COUNT(*) FROM fact_billing_daily GROUP BY loai ORDER BY loai")
    theo_loai = cur.fetchall()

    print(f"  nguon: {Path(args.file).name}")
    print(f"  {n} dong | ${float(tong):.4f}")
    print(f"  theo loai: {dict(theo_loai)}")

    # So mong doi SUY TU FILE NGUON o moi lan chay, khong ghim.
    dong_nguon = len(ban_ghi)
    tien_nguon = sum(float(r["chi_phi_usd"]) for r in rows)

    loi = []
    if n != dong_nguon:
        loi.append(f"so dong {n} != {dong_nguon} dong dung tu file nguon")
    if abs(float(tong) - tien_nguon) > 0.0001:
        loi.append(f"tong ${float(tong):.6f} != ${tien_nguon:.6f} trong file nguon")
    if loi:
        raise SystemExit("NGHIEM THU KHONG DAT: " + " | ".join(loi))
    print("  NGHIEM THU DAT (doi chieu voi chinh file nguon)")


if __name__ == "__main__":
    main()
