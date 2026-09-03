"""Nap nhat ky Ralli vao fact_call - buoc (6) cua Ngay 2. Chi doc file.

QUY TAC AP DUNG
---------------
Quy tac 5  Truong thieu nap NULL, KHONG nap 0. `cached_tokens` vang mat o
           6.871/7.924 dong (dinh dang 1). Nap 0 roi lay trung binh la sai 7,5 lan.
           CHU Y phan biet: dinh dang 2 va 3 CO truong nay va gia tri 0 la SO 0
           THAT. Chi dong nao KHONG CO truong moi thanh NULL.
Quy tac 6  Dung `total_tokens`, khong tu cong prompt + completion. Lech 162.

MUI GIO
-------
`timestamp` khong co nhan mui gio. Da chung minh la UTC (M2, docs/mui-gio-2026-08-08.md)
nen `tz_confirmed = TRUE` va `ts_local = ts_raw + 7h`.
Cot `ts_raw` van chep NGUYEN de sau nay con kiem lai duoc.

NGHIEM THU
----------
    SELECT COUNT(*), SUM(total_tokens) FROM fact_call;             -- 7924 | 44692501
    SELECT COUNT(*) FROM fact_call WHERE cached_tokens IS NULL;    -- 6871
    SELECT record_format, COUNT(*) FROM fact_call GROUP BY 1;  -- 1:6871 2:542 3:511
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import connect  # noqa: E402
import logs  # noqa: E402

log = logs.get_logger("load_ralli")

ROOT = Path(__file__).resolve().parents[1]


def _latest_ralli() -> Path:
    """Dot keo Ralli moi nhat. Nguon cu data/ctda/ la ban cao tay 05/08."""
    parent_dir = ROOT / "data" / "raw_web" / "ralli"
    remaining = sorted(p for p in parent_dir.glob("*") if p.is_dir())
    if not remaining:
        raise SystemExit(f"no pull batch in {parent_dir}."
                         f" Chay scripts/pull_web_apps.py truoc.")
    return remaining[-1]


RALLI_DIR = _latest_ralli()
LOG_FILE = RALLI_DIR / "db-token_usage-raw.json"
# Stats ca nam do CHINH APP tong hop - doc lap voi bang tho. Dung lam doi chung
# cho so luot khong quy duoc ve don vi.
YEAR_STATS = RALLI_DIR / "token-usage-year.json"

RALLI = 8
RECORD_FORMATS = {8: 1, 14: 2, 16: 3}          # so truong -> ma dinh dang

# KHONG ghim so mong doi nua (truoc: 7924 / 44.692.501 / 6871 / {1:6871,2:542,3:511}
# / 7660). Ca nam so deu dung cho dot du lieu 05/08 va lam script DUNG ngay khi
# co ban ghi moi - tuc chan dung viec chung phai bao ve. Nay:
#   - bon so dau  SUY TU CHINH BANG THO, bat duoc dong roi rot khi nap
#   - so cuoi     lay tu YEAR_STATS, van la doi chung DOC LAP nhu y ban dau


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=connect.DEFAULT_DSN)
    args = p.parse_args()

    cn, dc = connect.open_db(args.db)
    cur = cn.cursor()

    models = connect.model_lookup(cn)
    unit_of = dict(connect.query(
        cn, f"SELECT user_id, unit_id FROM dim_user WHERE agent_id = {dc}", (RALLI,)))
    # user_id cua Ralli -> account_id. Nhat ky ghi user_id theo hai dang khoa
    # khac nhau cho cung mot nguoi; ca hai dang deu tro ve MOT account_id.
    account_of = dict(connect.query(
        cn, f"SELECT user_id, account_id FROM dim_user WHERE agent_id = {dc}", (RALLI,)))
    unattributed_account = connect.query_one(
        cn, f"SELECT account_id FROM account WHERE username = {dc}",
        (f"__unattributed_{RALLI}__",))[0]
    unattributed_unit = f"__unattributed_{RALLI}__"

    calls = json.loads(LOG_FILE.read_text(encoding="utf-8-sig"))

    records: list[tuple] = []
    missing_model: collections.Counter = collections.Counter()
    unknown_format: collections.Counter = collections.Counter()
    for c in calls:
        fmt = RECORD_FORMATS.get(len(c))
        if fmt is None:
            unknown_format[len(c)] += 1
            continue

        mid = models.get(("app", c["model"]))
        if mid is None:
            missing_model[c["model"]] += 1

        raw_ts = datetime.fromisoformat(c["timestamp"])
        uid = c.get("user_id")

        records.append((
            c["_id"], RALLI,
            raw_ts.isoformat(sep=" "),
            True,
            (raw_ts + timedelta(hours=7)).isoformat(sep=" "),
            uid,
            account_of.get(uid, unattributed_account),
            unit_of.get(uid, unattributed_unit),
            mid,
            c.get("function"),
            c.get("prompt_tokens"),
            c.get("completion_tokens"),
            c["total_tokens"],
            # QUY TAC 5: vang mat -> NULL. Co mat va bang 0 -> giu nguyen 0.
            c["cached_tokens"] if "cached_tokens" in c else None,
            fmt,
        ))

    if unknown_format or missing_model:
        raise SystemExit(
            "the data has an unknown shape - stopping, nothing loaded:\n"
            f"  so truong la : {dict(unknown_format)}\n"
            f"  model chua co: {dict(missing_model)}")

    cur.execute("DELETE FROM fact_call")
    cur.executemany(
        f"INSERT INTO fact_call (call_id, agent_id, ts_raw, tz_confirmed,"
        f" ts_local, user_id, account_id, unit_id, model_id, function_code, prompt_tokens,"
        f" completion_tokens, total_tokens, cached_tokens, record_format)"
        f" VALUES ({','.join([dc] * 15)})", records)

    n, tok = connect.query_one(cn, "SELECT COUNT(*), SUM(total_tokens) FROM fact_call")
    missing_cached = connect.query_one(
        cn, "SELECT COUNT(*) FROM fact_call WHERE cached_tokens IS NULL")[0]
    by_format = dict(connect.query(cn, "SELECT record_format, COUNT(*) FROM fact_call"
                                    " GROUP BY 1 ORDER BY 1"))
    unattributed_calls = connect.query_one(
        cn, f"SELECT COUNT(*) FROM fact_call WHERE unit_id = {dc}",
        (unattributed_unit,))[0]

    log.info("  %d rows | %s tokens | record format %s", n, f"{tok:,}", by_format)
    log.info("  cached_tokens NULL %d | not resolvable to a unit %d",
             missing_cached, unattributed_calls)

    # ── so mong doi suy tu chinh bang tho ──
    src_rows = len(records)
    src_tokens = sum(c["total_tokens"] for c in calls if RECORD_FORMATS.get(len(c)))
    src_missing_cached = sum(1 for c in calls
                      if RECORD_FORMATS.get(len(c)) and "cached_tokens" not in c)
    src_by_format = collections.Counter(RECORD_FORMATS[len(c)] for c in calls if RECORD_FORMATS.get(len(c)))

    # ── so doi chung DOC LAP: app tu tong hop ra muc 'Khong xac dinh' ──
    # Ta phai ra dung con so do. Lech nghia la khau gan don vi sai - xem chu
    # thich o load_org.py.
    unattributed_app = None
    for u in json.loads(YEAR_STATS.read_text(encoding="utf-8-sig")).get("by_unit", []):
        if str(u.get("unit_name", "")).strip().lower() in ("không xác định", "khong xac dinh"):
            unattributed_app = u.get("calls")

    errors = []
    if n != src_rows:
        errors.append(f"row count {n} != {src_rows} counted from the raw table")
    if tok != src_tokens:
        errors.append(f"token {tok} != {src_tokens} trong bang tho")
    if missing_cached != src_missing_cached:
        errors.append(f"cached NULL {missing_cached} != {src_missing_cached} records missing the field")
    if by_format != dict(src_by_format):
        errors.append(f"dinh dang {by_format} != {dict(src_by_format)} dem tu bang tho")
    if unattributed_app is None:
        errors.append(f"could not find the 'Khong xac dinh' entry in {YEAR_STATS.name}"
                   f" - the independent cross-check is gone, refusing to load blind")
    elif unattributed_calls != unattributed_app:
        errors.append(f"khong quy duoc {unattributed_calls} != {unattributed_app} (so app tu tinh doc lap)")
    if errors:
        cn.rollback()
        raise SystemExit("ACCEPTANCE FAILED - rolled back:\n  "
                         + "\n  ".join(errors))
    cn.commit()
    log.info("  acceptance passed")


if __name__ == "__main__":
    main()
