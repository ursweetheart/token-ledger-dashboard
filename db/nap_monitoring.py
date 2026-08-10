"""Nap Cloud Monitoring vao fact_monitoring - chi doc file, khong goi mang.

QUY DINH M-A: NAP DU, LOC O TANG VIEW
------------------------------------
Nap ca 525.639 dong, ke ca luu luong Drive/Sheets/Compute. KHONG loc luc nap.

Ly do: chinh mo luu luong do la BANG CHUNG cho quy tac 3 - `pro-tuner` sai
45,7 lan neu quen loc. Loc ngay luc nap thi sau nay khong chung minh lai duoc,
ma cao lai thi khong the vi Google chi giu 196 ngay.

View `mon_sach` la cua duy nhat nen di qua khi tinh toan.

HAI CAI BAY
-----------
Quy tac 9  `dich_vu` KHONG co san trong file. Dung cac dong TOKEN cua
           generativelanguage lai co `res_service` RONG - dich vu cua chung nam
           o tien to `metric_type`. Gan thang dich_vu = res_service roi loc se
           tra ve 0 dong token, KHONG bao loi.
Quy tac 2  *_limit la ALIGN_MAX - han muc quota, khong phai so dem. Danh dau
           bang cot `la_han_muc` de khong ai lo SUM chung vao.

NGHIEM THU
----------
    SELECT COUNT(*) FROM fact_monitoring;                 -- 525639
    SELECT COUNT(DISTINCT project) FROM fact_monitoring;  -- 7
    SELECT COUNT(*) FROM mon_sach;                        -- 85166
"""

from __future__ import annotations

import argparse
import collections
import csv
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ket_noi  # noqa: E402
from quy_tac import la_han_muc, suy_dich_vu  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MON = ROOT / "data" / "raw_google_console" / "du_lieu_giam_sat" / "2026-08-06-1m"

DONG_MONG_DOI = 525639
SACH_MONG_DOI = 85166
PROJECT_MONG_DOI = 7
LO = 20000


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=ket_noi.MAC_DINH)
    p.add_argument("--dir", default=str(MON))
    p.add_argument("--gioi-han", type=int, default=0,
                   help="Chi nap N dong dau moi file - de chay lat mong cho nhanh")
    args = p.parse_args()

    cn, dc = ket_noi.mo(args.db)
    tra = ket_noi.tra_model(cn)

    files = sorted(glob.glob(str(Path(args.dir) / "*.csv")))
    if not files:
        raise SystemExit(f"Khong co file .csv nao trong {args.dir}")

    cur = cn.cursor()
    cur.execute("DELETE FROM fact_monitoring")

    cau = (f"INSERT INTO fact_monitoring (thoi_diem_utc, thoi_diem_ict, project, phep_do,"
           f" model_id, ma_tra_ve, dich_vu, phuong_thuc, credential_id, la_han_muc,"
           f" gia_tri, don_vi) VALUES ({','.join([dc] * 12)})")

    tong = 0
    thieu_model = collections.Counter()
    lo: list[tuple] = []
    for f in files:
        with open(f, encoding="utf-8-sig") as h:
            for i, r in enumerate(csv.DictReader(h)):
                if args.gioi_han and i >= args.gioi_han:
                    break
                model_id = None
                if r["model"]:
                    model_id = tra.get(("monitoring", r["model"]))
                    if model_id is None:
                        thieu_model[r["model"]] += 1
                lo.append((
                    r["ts_utc"], r["ts_ict"], r["gcp_project_id"], r["metric_alias"],
                    model_id,
                    r["response_code"] or None,
                    suy_dich_vu(r["res_service"], r["metric_type"]),
                    r["res_method"] or None,
                    r["res_credential_id"] or None,
                    la_han_muc(r["metric_alias"]),
                    float(r["value"]),
                    r["unit"] or None,
                ))
                if len(lo) >= LO:
                    cur.executemany(cau, lo)
                    tong += len(lo)
                    lo = []
    if lo:
        cur.executemany(cau, lo)
        tong += len(lo)

    # Kiem TRUOC commit. Neu de sau thi du lieu sai da kip ghi xuong dia, va
    # nguoi chay se co mot database trong nhu binh thuong nhung thieu model.
    if thieu_model:
        cn.rollback()
        raise SystemExit(
            "Nhan model chua co trong danh muc - da huy, khong ghi gi.\n"
            "Chay lai db/sinh_02_danh_muc.py roi nap lai:\n"
            f"  {dict(thieu_model)}")
    cn.commit()

    cur.execute("SELECT COUNT(*) FROM fact_monitoring")
    n = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT project) FROM fact_monitoring")
    du_an = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM mon_sach")
    sach = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM fact_monitoring WHERE model_id IS NULL")
    rong = cur.fetchone()[0]

    print(f"  {n} dong | {du_an} du an | mon_sach {sach} | model_id NULL {rong}")

    if args.gioi_han:
        print("  (lat mong - bo qua nghiem thu)")
        return
    loi = []
    if n != DONG_MONG_DOI:
        loi.append(f"so dong {n} != {DONG_MONG_DOI}")
    if du_an != PROJECT_MONG_DOI:
        loi.append(f"so du an {du_an} != {PROJECT_MONG_DOI}")
    if sach != SACH_MONG_DOI:
        loi.append(f"mon_sach {sach} != {SACH_MONG_DOI}")
    if loi:
        raise SystemExit("NGHIEM THU KHONG DAT: " + " | ".join(loi))
    print("  NGHIEM THU DAT")


if __name__ == "__main__":
    main()
