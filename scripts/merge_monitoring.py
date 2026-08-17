"""Gop nhieu dot keo Cloud Monitoring thanh mot, co khu trung lap.

VI SAO CAN
----------
Cua so luu giu cua Google KHONG on dinh. Do hai lan bang cung mot script:

    keo 06/08  ->  ngay som nhat 2026-01-22   (196 ngay)
    keo 13/08  ->  ngay som nhat 2026-04-23   (112 ngay)

Bay ngay troi qua nhung mep cua so nhay toi 91 ngay. Du lieu 22/01-22/04 gio
CHI con tren dia. Dung mot dot keo duy nhat lam nguon cho dashboard nghia la
moi lan keo lai, dai ngay lai co lai.

KHU TRUNG LAP
-------------
Hai dot chong nhau o khoang 23/04-06/08. Cong thang se NHAN DOI moi diem do
trong khoang do - va tong van trong nhu mot con so hop le, khong ai nhin ra.

Khoa trung lap = TOAN BO cot tru `value`. Cung mot phep do, cung mot moc thoi
gian, cung bo nhan thi phai la mot dong. Dot MOI duoc uu tien; neu dot cu cho
gia tri khac tren cung mot khoa thi day la chuyen dang ke - script dem va bao,
khong lang le chon bua mot ben.

Chi doc thu muc keo tho. Ghi ra mot thu muc moi, KHONG sua thu muc nao dang co.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THO = ROOT / "data" / "raw_google_console" / "du_lieu_giam_sat"
RA = ROOT / "data" / "da_xu_ly" / "du_lieu_giam_sat"

# Cot mang gia tri do duoc. Moi cot con lai la dinh danh cua phep do.
COT_GIA_TRI = "value"


def khoa(dong: dict, cot: list[str]) -> bytes:
    """Bam khoa thay vi giu nguyen chuoi - mot project co toi 456.000 dong."""
    thanh_phan = "\x1f".join(str(dong.get(c, "")) for c in cot if c != COT_GIA_TRI)
    return hashlib.blake2b(thanh_phan.encode("utf-8"), digest_size=16).digest()


def gop_project(ten: str, duong_dan: list[Path], dich: Path) -> dict:
    """Gop cac file cua mot project. duong_dan da sap xep MOI TRUOC CU SAU."""
    # Luu ca GIA TRI lan TEN DOT da cho gia tri do. Chi luu gia tri thi khi bao
    # lech se khong biet ben nao la ben nao - va vi vong lap chay MOI TRUOC CU
    # SAU nen truc giac "cai luu truoc la cai cu" bi nguoc.
    da_thay: dict[bytes, tuple[str, str]] = {}
    thong_ke = {"project": ten, "vao": 0, "ra": 0, "trung": 0, "lech": 0}
    cot: list[str] | None = None
    lech_vi_du: list[tuple] = []

    dich.parent.mkdir(parents=True, exist_ok=True)
    ghi = None
    handle = None

    try:
        for chi_so, p in enumerate(duong_dan):
            # utf-8-sig: chiu duoc ca file co BOM lan khong. Doc bang utf-8 thuan
            # thi BOM se dinh vao ten cot dau tien va moi phep tra cot deu truot.
            with p.open(encoding="utf-8-sig", newline="") as h:
                doc = csv.DictReader(h)
                if cot is None:
                    cot = list(doc.fieldnames or [])
                    handle = dich.open("w", encoding="utf-8", newline="")
                    ghi = csv.DictWriter(handle, fieldnames=cot, quoting=csv.QUOTE_ALL)
                    ghi.writeheader()
                elif list(doc.fieldnames or []) != cot:
                    raise SystemExit(
                        f"DUNG: {p} co bo cot khac cac file truoc.\n"
                        f"  truoc: {cot}\n  file nay: {doc.fieldnames}")

                dot = p.parent.name
                for dong in doc:
                    thong_ke["vao"] += 1
                    k = khoa(dong, cot)
                    da_co = da_thay.get(k)
                    if da_co is not None:
                        gia_tri_cu, dot_cu = da_co
                        thong_ke["trung"] += 1
                        if gia_tri_cu != dong.get(COT_GIA_TRI):
                            thong_ke["lech"] += 1
                            if len(lech_vi_du) < 5:
                                lech_vi_du.append(
                                    (dong.get("metric_alias"), dong.get("ts_utc"),
                                     dot_cu, gia_tri_cu, dot, dong.get(COT_GIA_TRI)))
                        continue
                    da_thay[k] = (dong.get(COT_GIA_TRI), dot)
                    ghi.writerow(dong)
                    thong_ke["ra"] += 1
    finally:
        if handle is not None:
            handle.close()

    thong_ke["lech_vi_du"] = lech_vi_du
    return thong_ke


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dot", default="",
                   help="Danh sach ten thu muc dot keo, ngan cach dau phay. "
                        "De trong = lay tat ca trong data/raw_google_console/du_lieu_giam_sat")
    p.add_argument("--ra", default="", help="Ten thu muc dau ra. Mac dinh <dot moi nhat>-gop")
    p.add_argument("--tho", default=str(THO))
    args = p.parse_args()

    goc = Path(args.tho)
    if args.dot:
        dots = [goc / t.strip() for t in args.dot.split(",") if t.strip()]
    else:
        dots = sorted(d for d in goc.glob("*") if d.is_dir())
    thieu = [d for d in dots if not d.is_dir()]
    if thieu:
        raise SystemExit(f"Khong thay thu muc: {[str(t) for t in thieu]}")
    if not dots:
        raise SystemExit(f"Khong co dot keo nao trong {goc}")

    # MOI TRUOC CU SAU: dot moi la nguon uu tien khi trung khoa.
    dots = sorted(dots, key=lambda d: d.name, reverse=True)
    ten_ra = args.ra or (dots[0].name + "-gop")
    dich = Path(RA) / ten_ra

    print(f"Gop {len(dots)} dot (uu tien tu tren xuong):")
    for d in dots:
        print(f"    {d.name}")
    print(f"Ghi vao: {dich}\n")

    projects: dict[str, list[Path]] = {}
    for d in dots:
        for f in sorted(d.glob("*.csv")):
            if f.name == "_tat-ca.csv":
                continue
            projects.setdefault(f.stem, []).append(f)

    tong = {"vao": 0, "ra": 0, "trung": 0, "lech": 0}
    for ten in sorted(projects):
        tk = gop_project(ten, projects[ten], dich / f"{ten}.csv")
        for k in tong:
            tong[k] += tk[k]
        print(f"  {ten:<28} {tk['vao']:>8,} vao -> {tk['ra']:>8,} ra"
              f" | trung {tk['trung']:>7,} | lech gia tri {tk['lech']:,}")
        for vd in tk["lech_vi_du"]:
            print(f"        LECH {vd[0]} @ {vd[1]}:")
            print(f"             {vd[2]} = {vd[3]}   (dot duoc GIU)")
            print(f"             {vd[4]} = {vd[5]}   (dot bi BO)")

    print(f"\n  TONG {tong['vao']:,} vao -> {tong['ra']:,} ra"
          f" | trung {tong['trung']:,} | lech gia tri {tong['lech']:,}")
    if tong["lech"]:
        print("\n  CANH BAO: co khoa trung nhung gia tri khac nhau giua hai dot keo.")
        print("  Da giu gia tri cua dot MOI. Xem vi du o tren truoc khi tin ket qua.")
    print(f"\nXong. Buoc tiep: db/load_monitoring.py doc {ten_ra} khi dung lai database")


if __name__ == "__main__":
    main()
