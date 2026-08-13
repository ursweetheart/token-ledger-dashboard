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


def _monitoring_moi_nhat() -> Path:
    """Uu tien thu muc da GOP (scripts/gop_monitoring.py).

    Cua so luu giu cua Google truot rat nhanh - do 06/08 thay 196 ngay, do 13/08
    chi con 112. Mot dot keo don le KHONG con phu het dai ngay, nen nguon dung
    cho nap la ban gop nhieu dot.
    """
    cha = ROOT / "data" / "da_xu_ly" / "du_lieu_giam_sat"
    con = sorted(p for p in cha.glob("*") if p.is_dir())
    if not con:
        raise SystemExit(f"Khong co thu muc nao trong {cha}."
                         f" Chay scripts/gop_monitoring.py truoc.")
    gop = [p for p in con if p.name.endswith("-gop")]
    return (gop or con)[-1]


MON = _monitoring_moi_nhat()
LO = 20000

# KHONG ghim so mong doi nua (truoc: 525639 / 85166 / 7). Chung dung cho dot keo
# 06/08 va sai ngay khi keo dot moi. Nay so dong va so du an SUY TU CHINH FILE
# NGUON. Rieng mon_sach la VIEW - suy lai so mong doi cua no la chep lai dinh
# nghia view, nen thay bang kiem bien: phai > 0 va < tong. Hai gia tri bien do
# bat dung hai kieu hong that su (bo loc chet, hoac bo loc khong chay).


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

    COT = ["thoi_diem_utc", "thoi_diem_ict", "project", "phep_do", "model_id",
           "ma_tra_ve", "dich_vu", "phuong_thuc", "credential_id", "la_han_muc",
           "gia_tri", "don_vi"]

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
                    tong += ket_noi.chen(cn, dc, "fact_monitoring", COT, lo)
                    lo = []
    if lo:
        tong += ket_noi.chen(cn, dc, "fact_monitoring", COT, lo)

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
    du_an_nguon = len({Path(f).stem for f in files})

    loi = []
    if n != tong:
        loi.append(f"so dong trong DB {n} != {tong} dong da doc tu file nguon")
    if du_an != du_an_nguon:
        loi.append(f"so du an {du_an} != {du_an_nguon} file nguon")
    if sach == 0:
        loi.append("mon_sach = 0 - bo loc dich vu chet, khong con dong nao di qua")
    elif sach >= n:
        loi.append(f"mon_sach {sach} >= tong {n} - bo loc khong chay, "
                   f"luu luong Drive/Sheets dang bi tinh chung")
    if loi:
        raise SystemExit("NGHIEM THU KHONG DAT: " + " | ".join(loi))
    print(f"  NGHIEM THU DAT (nguon: {MON.name})")


if __name__ == "__main__":
    main()
