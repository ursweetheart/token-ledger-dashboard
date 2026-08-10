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
BILLING = ROOT / "data" / "billing" / "billing_gop_tru_CTDA.csv"

TONG_MONG_DOI = 270.9517
DONG_MONG_DOI = 2259


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
        loai = suy_loai(r["sku"])
        if loai is None:
            khong_loai[r["sku_id"]] += 1
            continue
        model_id = tra.get(("billing_sku", r["sku_id"]))
        if model_id is None:
            khong_model[r["sku_id"]] += 1
        ban_ghi.append((r["date"], r["project"], r["sku_id"], r["sku"], model_id,
                        loai, int(float(r["amount"])), float(r["cost"])))

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

    print(f"  {n} dong | ${float(tong):.4f}")
    print(f"  theo loai: {dict(theo_loai)}")

    loi = []
    if n != DONG_MONG_DOI:
        loi.append(f"so dong {n} != {DONG_MONG_DOI}")
    if abs(float(tong) - TONG_MONG_DOI) > 0.0001:
        loi.append(f"tong ${float(tong):.4f} != ${TONG_MONG_DOI}")
    if loi:
        raise SystemExit("NGHIEM THU KHONG DAT: " + " | ".join(loi))
    print("  NGHIEM THU DAT")


if __name__ == "__main__":
    main()
