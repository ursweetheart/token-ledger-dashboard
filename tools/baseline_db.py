"""Chup bo so bat bien cua database, va so hai ban chup voi nhau.

    python tools/baseline_db.py --save var/baseline-2026-08-24.json
    python tools/baseline_db.py --db postgresql://.../token_ledger_v2 \
                               --compare var/baseline-2026-08-24.json

VI SAO LA MOT CONG CU CHU KHONG PHAI MOT FILE TINH
--------------------------------------------------
Task 1.2 cua change `change-the-schema-without-dropping-it` chi noi "ghi cac con
so vao mot file tam". Nhung task 5.4 phai SO LAI dung nhung con so do tren
database moi, va so bang mat thi de bo sot mot chu so. Cong cu nay chup duoc ca
hai dau roi tu so tung khoa mot.

DOC QUA usage_resolved, KHONG CONG THANG fact_usage_daily
---------------------------------------------------------
`fact_usage_daily` de ba nguon canh nhau (billing 965 / monitoring 539 / app 341
= 1.845 dong cho 1.189 khoa). Cong thang la dem ba lan - da do 20/08: ra 1,27 ty
thay vi 868 trieu, va "phan con lai" ra AM 43,9%. Moi phep do o day di qua view
`usage_resolved` da khu trung lap.

TIEN SO SANH BANG CHUOI, KHONG PHAI BANG FLOAT
-----------------------------------------------
`cost_usd` la NUMERIC(14,6); psycopg2 tra ve Decimal. Doi sang float de so la tu
tao ra sai so o chu so thu 15 - dung loai loi ma `==` tren so thuc sinh ra. Giu
nguyen dang chuoi.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "db"))

import connect  # noqa: E402

# (ten nhom, cau SQL, nhan cho tung cot tra ve)
AGGREGATES = [
    ("usage_resolved",
     "SELECT COUNT(*), SUM(total_tokens), SUM(cost_usd), MIN(day), MAX(day) FROM usage_resolved",
     ["rows", "tokens", "cost_usd", "first_day", "last_day"]),
    ("usage_by_account",
     "SELECT COUNT(*), SUM(total_tokens) FROM usage_by_account",
     ["rows", "tokens"]),
]

ROW_COUNT_TABLES = ["account", "dim_agent", "dim_unit", "fact_usage_daily",
                    "fact_billing_daily", "fact_monitoring", "fact_call",
                    "fact_app_daily", "ref_source"]

GROUPINGS = [
    ("account_by_kind", "SELECT kind, COUNT(*) FROM account GROUP BY kind"),
    ("usage_daily_by_source", "SELECT source, COUNT(*) FROM fact_usage_daily GROUP BY source"),
]


def capture(dsn: str) -> dict:
    """Doc toan bo bo so bat bien tu mot database. Chi doc, khong ghi gi."""
    cn, _ = connect.open_db(dsn)
    cur = cn.cursor()
    snapshot: dict = {}
    try:
        for name, sql, labels in AGGREGATES:
            cur.execute(sql)
            row = cur.fetchone()
            snapshot[name] = {k: (None if v is None else str(v)) for k, v in zip(labels, row)}

        counts = {}
        for table in ROW_COUNT_TABLES:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
        snapshot["row_counts"] = counts

        for name, sql in GROUPINGS:
            cur.execute(sql)
            snapshot[name] = {str(k): v for k, v in cur.fetchall()}
    finally:
        cn.close()
    return snapshot


def _flatten(data: dict, prefix: str = "") -> dict:
    """Trai cay long nhau thanh mot tang, de so tung khoa mot."""
    out = {}
    for key, value in data.items():
        full = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(_flatten(value, full + "."))
        else:
            out[full] = value
    return out


def _num(value) -> str:
    """Dinh dang so nguyen co dau cham ngan. NULL giu nguyen la NULL.

    SUM() tren bang RONG tra ve NULL, khong phai 0 - va do chinh la truong hop
    se gap o task 5.2 (schema vua dung xong, chua nap gi). `int(None)` no ngay
    tai do, tuc cong cu hong dung luc can dung nhat. Va NULL khac 0 that: mot
    cai la "chua do", mot cai la "da do, bang khong".
    """
    if value is None or value == "None":
        return "NULL"
    return f"{int(value):,}".replace(",", ".")


def print_snapshot(snapshot: dict) -> None:
    usage = snapshot["usage_resolved"]
    print(f"  usage_resolved      {usage['rows']:>7} dong · {_num(usage['tokens'])} token"
          f" · ${usage['cost_usd']}")
    print(f"                      ky {usage['first_day']} -> {usage['last_day']}")
    by_account = snapshot["usage_by_account"]
    print(f"  usage_by_account    {by_account['rows']:>7} dong · {_num(by_account['tokens'])} token")
    print()
    for table, count in snapshot["row_counts"].items():
        print(f"    {table:22s} {count:>8,}".replace(",", "."))
    print()
    print("    account by kind        :", dict(sorted(snapshot["account_by_kind"].items())))
    print("    usage_daily by source  :", dict(sorted(snapshot["usage_daily_by_source"].items())))


def compare(base: dict, current: dict) -> int:
    """So hai ban chup. Tra ve so khoa lech, in ten tung khoa lech mot."""
    flat_base, flat_current = _flatten(base), _flatten(current)
    keys = sorted(set(flat_base) | set(flat_current))
    diffs = []
    for key in keys:
        left, right = flat_base.get(key, "(thieu)"), flat_current.get(key, "(thieu)")
        if str(left) != str(right):
            diffs.append((key, left, right))
    print(f"\n  So {len(keys)} khoa: {len(keys) - len(diffs)} khop · {len(diffs)} lech")
    if diffs:
        print()
        for key, left, right in diffs:
            print(f"    LECH  {key}")
            print(f"          moc  : {left}")
            print(f"          nay  : {right}")
    return len(diffs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=connect.DEFAULT_DSN,
                        help="DSN. Mac dinh: connect.DEFAULT_DSN")
    parser.add_argument("--save", help="Ghi ban chup ra file JSON")
    parser.add_argument("--compare", help="So ban chup nay voi mot file JSON da ghi")
    args = parser.parse_args()

    print(f"Database: {connect.mask_dsn(args.db)}\n")
    snapshot = capture(args.db)
    print_snapshot(snapshot)

    if args.save:
        path = Path(args.save)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  Da ghi: {path}")

    if args.compare:
        base = json.loads(Path(args.compare).read_text(encoding="utf-8"))
        n = compare(base, snapshot)
        if n:
            raise SystemExit(f"\n  KHONG DAT: {n} khoa lech. Dung lai, dieu tra - "
                             f"KHONG noi phep so cho vua y.")
        print("\n  DAT: khop tung con so.")


if __name__ == "__main__":
    main()
