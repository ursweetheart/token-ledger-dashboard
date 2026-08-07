"""Turn a raw Monitoring pull into something a person can open in Excel.

This is the missing middle step. `pull_monitoring.py` talks to Google and writes
data/raw_google_console/ exactly as it arrived; nothing may edit those files
afterwards. This script reads them and writes a readable copy under
data/da_xu_ly/ -- filtered, reordered, and dated the way a person here reads.

The split matters because the two jobs fail differently. Getting data back from
Google costs minutes of network time and can only ever be done for the window
Google still retains. Changing how a date is written costs two seconds and can
be redone forever. Fusing them would mean re-downloading 240 days to fix a
display format -- which is what this file exists to prevent.

What it changes, and nothing else:

  * adds ts_ict_vn, the Vietnam timestamp written dd/mm/yyyy for human eyes
  * sorts rows chronologically (the API returns newest-first, per metric)
  * writes UTF-8 with BOM so Excel shows Vietnamese text correctly on open

Values are never touched. Rows are never dropped unless --loc is passed, and
even then the raw file still holds everything.

Usage
    python scripts/make_readable.py                  # ban keo moi nhat
    python scripts/make_readable.py --dir data/raw_google_console/du_lieu_giam_sat/2026-08-06-1m
    python scripts/make_readable.py --loc            # bo dong rac (xem duoi)
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw_google_console" / "du_lieu_giam_sat"
DA_XU_LY = ROOT / "data" / "da_xu_ly" / "du_lieu_giam_sat"

GEMINI = "generativelanguage.googleapis.com"
VN_COLUMN = "ts_ict_vn"


def utc_of(row: dict) -> str:
    """The UTC timestamp under whichever name this pull used.

    Pulls made before --align existed called it ts_hour_utc. Those files are on
    disk and are the only copy of the oldest data, so both names must work.
    """
    return row.get("ts_utc") or row.get("ts_hour_utc") or ""


def ict_of(row: dict) -> str:
    return row.get("ts_ict") or row.get("ts_hour_ict") or ""


def to_vn(iso: str) -> str:
    """'2026-07-24 20:00:00' -> '24/07/2026 20:00'.

    Written for reading only. A US-locale Excel parses d/m/y inconsistently --
    it leaves 24/07/2026 as text but silently reads 07/02/2026 as 7 February.
    That is survivable precisely because every script reads the ISO columns
    instead, so a misread can reach the eye but never a calculation.
    """
    if not iso:
        return ""
    for shape in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(iso, shape).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue
    return iso


def is_junk(row: dict) -> bool:
    """Rows that are real data but answer no question the dashboard asks.

    Two kinds, both documented as traps in the priority doc:
      * quota `_limit` rows report the ceiling, not the usage. An uncapped
        ceiling reads 9.22e18, so mixing them into a sum is catastrophic.
      * serviceruntime covers every Google API the project touches. On Sale
        Agent, Google Drive traffic outnumbers Gemini traffic.
    """
    alias = row.get("metric_alias", "")
    if alias.endswith("_limit"):
        return True
    service = row.get("res_service", "")
    return bool(service) and service != GEMINI


def read_pull(directory: Path) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    columns: list[str] = []
    for path in sorted(directory.glob("*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = columns or list(reader.fieldnames or [])
            rows.extend(reader)
    return rows, columns


def write(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig: without the BOM, Excel opens the file as the system codepage
    # and Vietnamese diacritics arrive as mojibake.
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, quoting=csv.QUOTE_ALL,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default="",
                        help="Thu muc mot dot keo trong data/raw_google_console")
    parser.add_argument("--out", default="", help="Thu muc ghi ra (mac dinh data/da_xu_ly)")
    parser.add_argument("--loc", action="store_true",
                        help="Bo dong _limit va dich vu khong phai Gemini")
    args = parser.parse_args()

    if args.dir:
        source = Path(args.dir)
    else:
        pulls = sorted(p for p in RAW.glob("*") if p.is_dir())
        if not pulls:
            raise SystemExit(f"Khong thay dot keo nao trong {RAW}")
        source = pulls[-1]

    if not source.is_dir():
        raise SystemExit(f"Khong thay thu muc: {source}")

    rows, columns = read_pull(source)
    if not rows:
        raise SystemExit(f"Khong co dong nao trong {source}")

    print(f"Doc  : {source}   ({len(rows):,} dong)")

    dropped = 0
    if args.loc:
        before = len(rows)
        rows = [r for r in rows if not is_junk(r)]
        dropped = before - len(rows)

    for row in rows:
        row[VN_COLUMN] = to_vn(ict_of(row))

    # Chronological, then project, then metric -- so equal timestamps still land
    # in a stable order and two runs produce identical files.
    rows.sort(key=lambda r: (utc_of(r), r.get("gcp_project_id", ""),
                             r.get("metric_alias", ""), r.get("aligner", "")))

    # The human column goes first. The ISO ones stay, immediately after, because
    # they are what every script reads.
    time_columns = [c for c in columns if c.startswith("ts_")]
    rest = [c for c in columns if not c.startswith("ts_")]
    head = [c for c in ("metric_alias", "metric_type", "gcp_project_id") if c in rest]
    tail = [c for c in rest if c not in head]
    ordered = head + [VN_COLUMN] + time_columns + tail

    target = Path(args.out) if args.out else DA_XU_LY / source.name
    projects = sorted({r.get("gcp_project_id", "?") for r in rows})
    for project in projects:
        subset = [r for r in rows if r.get("gcp_project_id") == project]
        write(target / f"{project}.csv", subset, ordered)

    combined = target / "_tat-ca.csv"
    write(combined, rows, ordered)

    print(f"Ghi  : {target}")
    if dropped:
        print(f"       da bo {dropped:,} dong rac (--loc)")
    print(f"       {len(projects)} file theo project + _tat-ca.csv ({len(rows):,} dong)")
    print(f"Khoang: {to_vn(ict_of(rows[0]))}  ->  {to_vn(ict_of(rows[-1]))}  (gio Viet Nam)")


if __name__ == "__main__":
    main()
