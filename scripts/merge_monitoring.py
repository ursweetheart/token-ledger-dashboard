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
gian, cung bo nhan thi phai la mot dong.

HAI DOT CHO GIA TRI KHAC TREN CUNG KHOA: GIU SO LON HON (doi 14/09/2026)
----------------------------------------------------------------------
Truoc 14/09/2026 dot MOI thang. Do tren 6 dot keo 1 phut (06/08 -> 12/09): 14
diem lech, CA 14 deu la dot sau bao NHO hon, va dot sau thieu dong ngay sat
diem do - vung mep cua so bi cut. Luat "dot moi thang" da bo 11.262 token, trong
do 3.462 token ngay 11/06 (tranquil, 00:00 UTC: 4406 o 5 dot, 944 o dot 12/09).
Xem docs/reference/luat-trien-khai-tu-dong-13-09.md muc 2.

"Dot cu thang" cung dung 14/14 tren du lieu da co. "So lon hon" duoc chon vi no
dung them o truong hop da biet ma chua gap: du lieu ve muon lam dot sau LON hon.

Moi ca lech duoc GHI RA TEP `<ten dau ra>.lech.csv` CANH thu muc gop - khong phai
ben trong: db/load_monitoring.py nap MOI *.csv trong thu muc gop. Tep luon co
dong tieu de, ke ca khi khong lech, de phan biet "khong lech" voi "chua chay".

HAI LUOT DOC
------------
Luat "so lon hon" phai doi duoc dong da giu khi gap so lon hon o dot cu hon, nen
khong ghi thang ra tep nhu truoc. Luot 1 chi nho (ma bam, gia tri, dot, so thu tu
dong) cua ben thang; luot 2 doc lai dung thu tu va chi ghi dong thang. Giu nguyen
dong trong bo nho thi pro-tuner (621.612 khoa, hai cot JSON dai) ton vai tram MB.

CHI GOP THU MUC DUNG KHUON TEN (doi 14/09/2026)
----------------------------------------------
Mac dinh chi doc thu muc khop `PULL_DIR` - dung khuon ma scripts/pull_monitoring.py
dat cho lan keo san xuat (do min 1 phut, tai khoan mac dinh). Lan keo 1 gio hay
bang tai khoan khac bi BO QUA va duoc in ten ra. Ngay 12/09 thu muc
`2026-09-04-1h-dinhthinhan18111971` lot vao ban gop, mang theo project la
`project-e62bad30-*`, va phai xoa tay. `--batches` van doc dung danh sach duoc goi
ten, kem canh bao cho ten khong khop khuon.

Chi doc thu muc keo tho. Ghi ra mot thu muc moi - NHUNG neu thu muc dich da co thi
tep cung ten bi ghi de va tep khac ten van nam lai; doi ten thu muc cu truoc.

TEN TREN DIA GIU NGUYEN: hau to thu muc gop `-gop` va tep ca lech `.lech.csv` duoc
db/load_monitoring.py va nguoi van hanh doc lai.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw_google_console" / "du_lieu_giam_sat"  # vi-ok: on-disk path
OUT_ROOT = ROOT / "data" / "da_xu_ly" / "du_lieu_giam_sat"  # vi-ok: on-disk path

# Cot mang gia tri do duoc. Moi cot con lai la dinh danh cua phep do.
VALUE_COL = "value"

# Khuon ten lan keo san xuat: scripts/pull_monitoring.py:309-318 dat
# `<ngay>-<do min>` va KHONG them hau to khi dung tai khoan mac dinh.
PULL_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}-1m$")

CLASH_TAIL = ["pull_a", "value_a", "pull_b", "value_b", "kept", "newest_value"]


def row_key(row: dict, cols: list[str]) -> bytes:
    """Bam khoa thay vi giu nguyen chuoi - mot project co toi 456.000 dong."""
    parts = "\x1f".join(str(row.get(c, "")) for c in cols if c != VALUE_COL)
    return hashlib.blake2b(parts.encode("utf-8"), digest_size=16).digest()


def merge_project(name: str, paths: list[Path], dest: Path) -> dict:
    """Gop cac file cua mot project. `paths` da sap xep MOI TRUOC CU SAU."""
    # khoa -> (gia tri so, gia tri chuoi, chi so dot, so thu tu dong, gia tri cua dot moi nhat)
    best: dict[bytes, tuple[float, str, int, int, str]] = {}
    stats = {"project": name, "rows_in": 0, "rows_out": 0, "duplicates": 0, "clashes": 0,
             "cols": [], "clash_rows": []}
    cols: list[str] | None = None

    # ---- LUOT 1: chon ben thang cho moi khoa
    for idx, p in enumerate(paths):
        # utf-8-sig: chiu duoc ca file co BOM lan khong. Doc bang utf-8 thuan
        # thi BOM se dinh vao ten cot dau tien va moi phep tra cot deu truot.
        with p.open(encoding="utf-8-sig", newline="") as h:
            reader = csv.DictReader(h)
            if cols is None:
                cols = list(reader.fieldnames or [])
            elif list(reader.fieldnames or []) != cols:
                raise SystemExit(
                    f"STOP: {p} has different columns from the files before it.\n"
                    f"  before:    {cols}\n  this file: {reader.fieldnames}")
            for i, row in enumerate(reader):
                stats["rows_in"] += 1
                k = row_key(row, cols)
                v_str = row.get(VALUE_COL, "")
                cur = best.get(k)
                if cur is None:
                    best[k] = (float(v_str), v_str, idx, i, v_str)
                    continue
                stats["duplicates"] += 1
                if cur[1] == v_str:
                    continue
                v = float(v_str)
                # ponytail: "lon hon" dung cho cong to (ALIGN_SUM) - thieu du lieu chi
                # lam so NHO di. Voi phan vi (ALIGN_PERCENTILE_*) lon hon KHONG dong
                # nghia day du hon; 4/14 ca phan vi hom nay chon dung la do trung hop.
                # Nang cap: lay gia tri tu dot co api_request_count lon hon o cung phut.
                larger = v > cur[0]
                stats["clashes"] += 1
                stats["clash_rows"].append({
                    **{c: row.get(c, "") for c in cols if c != VALUE_COL},
                    "pull_a": paths[cur[2]].parent.name, "value_a": cur[1],
                    "pull_b": p.parent.name, "value_b": v_str,
                    "kept": v_str if larger else cur[1], "newest_value": cur[4],
                })
                if larger:
                    best[k] = (v, v_str, idx, i, cur[4])

    # ---- LUOT 2: doc lai dung thu tu, chi ghi dong thang
    cols = cols or []
    stats["cols"] = cols
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=cols, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for idx, p in enumerate(paths):
            with p.open(encoding="utf-8-sig", newline="") as h:
                for i, row in enumerate(csv.DictReader(h)):
                    won = best.get(row_key(row, cols))
                    if won is not None and won[2] == idx and won[3] == i:
                        writer.writerow(row)
                        stats["rows_out"] += 1
    return stats


def select_batches(base: Path, names: str) -> tuple[list[Path], list[str], list[str]]:
    """(thu muc se doc, ten bi bo qua, ten duoc goi tuong minh ma khong khop khuon)."""
    if names:
        batches = [base / t.strip() for t in names.split(",") if t.strip()]
        return batches, [], [d.name for d in batches if not PULL_DIR.match(d.name)]
    dirs = sorted(d for d in base.glob("*") if d.is_dir())
    return ([d for d in dirs if PULL_DIR.match(d.name)],
            [d.name for d in dirs if not PULL_DIR.match(d.name)], [])


def write_clash_file(path: Path, clashes: list[dict], key_cols: list[str]) -> None:
    """Luon ghi, ke ca khi rong: chi co dong tieu de nghia la DA CHAY va KHONG lech."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=["project", *key_cols, *CLASH_TAIL],
                                quoting=csv.QUOTE_ALL, restval="")
        writer.writeheader()
        writer.writerows(clashes)


def run(raw: Path, out_root: Path, batches: str = "", out_name: str = "") -> dict:
    base = Path(raw)
    selected, skipped, odd = select_batches(base, batches)
    missing = [d for d in selected if not d.is_dir()]
    if missing:
        raise SystemExit(f"Folders not found: {[str(t) for t in missing]}")
    if not selected:
        raise SystemExit(f"no pull batch matching {PULL_DIR.pattern} in {base}")

    # MOI TRUOC CU SAU: khi hai dot BANG nhau thi dong cua dot moi duoc ghi.
    selected = sorted(selected, key=lambda d: d.name, reverse=True)
    out_name = out_name or (selected[0].name + "-gop")
    dest = Path(out_root) / out_name
    clash_file = Path(out_root) / f"{out_name}.lech.csv"

    print(f"merging {len(selected)} batches (newest first; on a value clash the LARGER value is kept):")
    for d in selected:
        print(f"    {d.name}")
    if skipped:
        print(f"skipped {len(skipped)} folders (name does not match {PULL_DIR.pattern}):")
        for n in skipped:
            print(f"    {n}")
    for n in odd:
        print(f"  WARNING: {n} does not match {PULL_DIR.pattern} - merged anyway because --batches listed it")
    print(f"writing to: {dest}\n")

    projects: dict[str, list[Path]] = {}
    for d in selected:
        for f in sorted(d.glob("*.csv")):
            if f.name == "_tat-ca.csv":
                continue
            projects.setdefault(f.stem, []).append(f)

    total = {"rows_in": 0, "rows_out": 0, "duplicates": 0, "clashes": 0}
    clashes: list[dict] = []
    key_cols: list[str] = []
    for name in sorted(projects):
        tk = merge_project(name, projects[name], dest / f"{name}.csv")
        for k in total:
            total[k] += tk[k]
        for c in tk["cols"]:
            if c != VALUE_COL and c not in key_cols:
                key_cols.append(c)
        clashes.extend({"project": name, **row} for row in tk["clash_rows"])
        print(f"  {name:<28} {tk['rows_in']:>8,} in -> {tk['rows_out']:>8,} out"
              f" | dup {tk['duplicates']:>7,} | value clash {tk['clashes']:,}")
        for example in tk["clash_rows"][:5]:
            print(f"        MISMATCH {example.get('metric_alias', '')} @ {example.get('ts_utc', '')}:"
                  f" {example['pull_a']}={example['value_a']}  {example['pull_b']}={example['value_b']}"
                  f"  -> kept {example['kept']}")

    write_clash_file(clash_file, clashes, key_cols)

    print(f"\n  TOTAL {total['rows_in']:,} in -> {total['rows_out']:,} out"
          f" | dup {total['duplicates']:,} | value clash {total['clashes']:,}")
    if total["clashes"]:
        print("\n  WARNING: some keys repeat with different values across pull batches.")
        print("  Kept the LARGER value. Every case is listed in the clash file below.")
    print(f"  clash file: {clash_file}")
    print(f"\ndone. Next: db/load_monitoring.py reads {out_name} when rebuilding the database")
    return {"batches": [d.name for d in selected], "skipped": skipped, "odd": odd,
            "dest": dest, "clash_file": clash_file, **total}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                allow_abbrev=False)
    p.add_argument("--batches", dest="batch", default="",
                   help="Comma-separated pull batch folder names. Empty = every folder"
                        " matching the production pull pattern in data/raw_google_console/du_lieu_giam_sat")  # vi-ok: on-disk path
    p.add_argument("--out", dest="out_path", default="",
                   help="Output folder name. Default <newest batch>-gop")
    p.add_argument("--raw", dest="raw", default=str(RAW_DIR))
    p.add_argument("--out-root", dest="out_root", default=str(OUT_ROOT),
                   help="Parent folder of the merged batch and the clash file"
                        " (default data/da_xu_ly/du_lieu_giam_sat)")  # vi-ok: on-disk path
    args = p.parse_args()
    run(raw=Path(args.raw), out_root=Path(args.out_root), batches=args.batch, out_name=args.out_path)


if __name__ == "__main__":
    main()
