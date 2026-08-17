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
RAW_DIR = ROOT / "data" / "raw_google_console" / "du_lieu_giam_sat"
RA = ROOT / "data" / "da_xu_ly" / "du_lieu_giam_sat"

# Cot mang gia tri do duoc. Moi cot con lai la dinh danh cua phep do.
VALUE_COL = "value"


def row_key(row: dict, cols: list[str]) -> bytes:
    """Bam khoa thay vi giu nguyen chuoi - mot project co toi 456.000 dong."""
    parts = "\x1f".join(str(row.get(c, "")) for c in cols if c != VALUE_COL)
    return hashlib.blake2b(parts.encode("utf-8"), digest_size=16).digest()


def merge_project(name: str, paths: list[Path], dest: Path) -> dict:
    """Gop cac file cua mot project. duong_dan da sap xep MOI TRUOC CU SAU."""
    # Luu ca GIA TRI lan TEN DOT da cho gia tri do. Chi luu gia tri thi khi bao
    # lech se khong biet ben nao la ben nao - va vi vong lap chay MOI TRUOC CU
    # SAU nen truc giac "cai luu truoc la cai cu" bi nguoc.
    seen: dict[bytes, tuple[str, str]] = {}
    stats = {"project": name, "vao": 0, "ra": 0, "trung": 0, "lech": 0}
    cols: list[str] | None = None
    diff_example: list[tuple] = []

    dest.parent.mkdir(parents=True, exist_ok=True)
    written = None
    handle = None

    try:
        for metric, p in enumerate(paths):
            # utf-8-sig: chiu duoc ca file co BOM lan khong. Doc bang utf-8 thuan
            # thi BOM se dinh vao ten cot dau tien va moi phep tra cot deu truot.
            with p.open(encoding="utf-8-sig", newline="") as h:
                reader = csv.DictReader(h)
                if cols is None:
                    cols = list(reader.fieldnames or [])
                    handle = dest.open("w", encoding="utf-8", newline="")
                    written = csv.DictWriter(handle, fieldnames=cols, quoting=csv.QUOTE_ALL)
                    written.writeheader()
                elif list(reader.fieldnames or []) != cols:
                    raise SystemExit(
                        f"DUNG: {p} co bo cot khac cac file truoc.\n"
                        f"  truoc: {cols}\n  file nay: {reader.fieldnames}")

                batch = p.parent.name
                for row in reader:
                    stats["vao"] += 1
                    k = row_key(row, cols)
                    existing = seen.get(k)
                    if existing is not None:
                        old_value, old_batch = existing
                        stats["trung"] += 1
                        if old_value != row.get(VALUE_COL):
                            stats["lech"] += 1
                            if len(diff_example) < 5:
                                diff_example.append(
                                    (row.get("metric_alias"), row.get("ts_utc"),
                                     old_batch, old_value, batch, row.get(VALUE_COL)))
                        continue
                    seen[k] = (row.get(VALUE_COL), batch)
                    written.writerow(row)
                    stats["ra"] += 1
    finally:
        if handle is not None:
            handle.close()

    stats["lech_vi_du"] = diff_example
    return stats


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dot", dest="batch", default="",
                   help="Danh sach ten thu muc dot keo, ngan cach dau phay. "
                        "De trong = lay tat ca trong data/raw_google_console/du_lieu_giam_sat")
    p.add_argument("--ra", dest="out_path", default="", help="Ten thu muc dau ra. Mac dinh <dot moi nhat>-gop")
    p.add_argument("--tho", dest="raw", default=str(RAW_DIR))
    args = p.parse_args()

    base = Path(args.raw)
    if args.batch:
        batches = [base / t.strip() for t in args.batch.split(",") if t.strip()]
    else:
        batches = sorted(d for d in base.glob("*") if d.is_dir())
    missing = [d for d in batches if not d.is_dir()]
    if missing:
        raise SystemExit(f"Khong thay thu muc: {[str(t) for t in missing]}")
    if not batches:
        raise SystemExit(f"Khong co dot keo nao trong {base}")

    # MOI TRUOC CU SAU: dot moi la nguon uu tien khi trung khoa.
    batches = sorted(batches, key=lambda d: d.name, reverse=True)
    out_name = args.out_path or (batches[0].name + "-gop")
    dest = Path(RA) / out_name

    print(f"Gop {len(batches)} dot (uu tien tu tren xuong):")
    for d in batches:
        print(f"    {d.name}")
    print(f"Ghi vao: {dest}\n")

    projects: dict[str, list[Path]] = {}
    for d in batches:
        for f in sorted(d.glob("*.csv")):
            if f.name == "_tat-ca.csv":
                continue
            projects.setdefault(f.stem, []).append(f)

    total = {"vao": 0, "ra": 0, "trung": 0, "lech": 0}
    for name in sorted(projects):
        tk = merge_project(name, projects[name], dest / f"{name}.csv")
        for k in total:
            total[k] += tk[k]
        print(f"  {name:<28} {tk['vao']:>8,} vao -> {tk['out_path']:>8,} ra"
              f" | trung {tk['trung']:>7,} | lech gia tri {tk['lech']:,}")
        for example in tk["lech_vi_du"]:
            print(f"        LECH {example[0]} @ {example[1]}:")
            print(f"             {example[2]} = {example[3]}   (dot duoc GIU)")
            print(f"             {example[4]} = {example[5]}   (dot bi BO)")

    print(f"\n  TONG {total['vao']:,} vao -> {total['out_path']:,} ra"
          f" | trung {total['trung']:,} | lech gia tri {total['lech']:,}")
    if total["lech"]:
        print("\n  CANH BAO: co khoa trung nhung gia tri khac nhau giua hai dot keo.")
        print("  Da giu gia tri cua dot MOI. Xem vi du o tren truoc khi tin ket qua.")
    print(f"\nXong. Buoc tiep: db/load_monitoring.py doc {out_name} khi dung lai database")


if __name__ == "__main__":
    main()
