"""Locate, do not just count, the defects that kiem_tra_du_lieu.py reported.

The main checker answers "is something wrong". This answers "what exactly, and
where". The distinction matters because the fix is different in each case:

  * a gap that is constant per row is an accounting rule
  * a gap that scales with volume is a rounding or a unit error
  * a gap confined to one model is that model's feature
  * a gap spread evenly is a systemic double-count

Only the raw CTDA table can be interrogated this way. TLA HD publishes no raw
table, so the finest available grain there is its own slice lists -- which is
itself a finding, and is reported as one.

Read only. Writes nothing.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def num(value) -> float:
    """TLA HD serialises money as JSON strings, CTDA as JSON numbers."""
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", "")
    if text == "" or text.lower() in ("none", "null", "nan", "-"):
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def when(row: dict) -> datetime | None:
    text = row.get("timestamp")
    if not text:
        return None
    try:
        return datetime.fromisoformat(str(text).replace("Z", ""))
    except ValueError:
        return None


def head(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def profile(label: str, rows: list[dict], fields: tuple[str, ...]) -> None:
    """Value distribution of a group, so it can be told apart from the rest."""
    print(f"\n  -- {label}  ({len(rows)} dong) --")
    for field in fields:
        seen = Counter(str(r.get(field, "(THIEU TRUONG)")) for r in rows)
        shown = "  ".join(f"{value}={count}" for value, count in seen.most_common(4))
        extra = f"  (+{len(seen) - 4} gia tri khac)" if len(seen) > 4 else ""
        print(f"     {field:<18} {shown}{extra}")


# ───────────────────── 1. CTDA: 162 token bien di dau ─────────────────────

def ctda_gap(raw: list[dict]) -> None:
    head("1. CTDA - 162 token lech nam o dau")

    off, fine = [], []
    for row in raw:
        diff = (num(row.get("total_tokens")) - num(row.get("prompt_tokens"))
                - num(row.get("completion_tokens")))
        (off if abs(diff) > 0.5 else fine).append((row, diff))

    # round, not int: int() truncates toward zero, so a gap of -1.9999 would
    # print as -1 and a constant gap would look ragged.
    sizes = Counter(round(diff) for _, diff in off)
    print(f"  so dong lech        {len(off)} / {len(raw)}")
    print(f"  tong token thieu    {sum(round(d) for _, d in off)}")
    print(f"  do lon moi cho lech {dict(sorted(sizes.items()))}   <- (lech: so dong)")
    if len(sizes) == 1:
        size = next(iter(sizes))
        print(f"  ==> LUON dung {size} token moi dong. Khong phai lam tron.")

    fields = ("model", "function", "event_type", "pricing_mode", "actor_type")
    profile("NHOM LECH", [r for r, _ in off], fields)
    profile("NHOM BINH THUONG", [r for r, _ in fine], fields)

    # If the gap is a feature of one function, that function should be rare in
    # the healthy group too -- otherwise the split is caused by something else.
    print("\n  -- ty le lech trong tung nhom function --")
    per_function: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row, diff in off:
        per_function[str(row.get("function"))][0] += 1
    for row, _ in fine:
        per_function[str(row.get("function"))][1] += 1
    for function, (bad, good) in sorted(per_function.items(),
                                        key=lambda kv: -kv[1][0]):
        total = bad + good
        print(f"     {function:<26} lech {bad:>4} / {total:<6} ({100 * bad / total:5.1f}%)")

    stamps = sorted(s for s in (when(r) for r, _ in off) if s)
    if stamps:
        print(f"\n  khoang thoi gian nhom lech   {stamps[0]:%d/%m/%Y} -> {stamps[-1]:%d/%m/%Y}")
    all_stamps = sorted(s for s in (when(r) for r in raw) if s)
    if all_stamps:
        print(f"  khoang thoi gian ca bang     {all_stamps[0]:%d/%m/%Y} -> {all_stamps[-1]:%d/%m/%Y}")

    # A gap that only appears where a field is absent points at the migration,
    # not at the model.
    print("\n  -- nhom lech co truong cached_tokens khong --")
    has = sum(1 for r, _ in off if "cached_tokens" in r)
    print(f"     co truong    {has}/{len(off)}")
    print(f"     thieu truong {len(off) - has}/{len(off)}")


# ──────────────── 2. CTDA: bang tho co may dinh dang ────────────────

def ctda_shapes(raw: list[dict]) -> None:
    head("2. CTDA - bang tho co bao nhieu dinh dang khac nhau")

    shapes: dict[frozenset, list[dict]] = defaultdict(list)
    for row in raw:
        shapes[frozenset(row.keys())].append(row)

    print(f"  so dinh dang khac nhau: {len(shapes)}")
    base = set.intersection(*(set(keys) for keys in shapes)) if shapes else set()

    ordered = sorted(shapes.items(), key=lambda kv: len(kv[1]), reverse=True)
    for index, (keys, rows) in enumerate(ordered, start=1):
        stamps = sorted(s for s in (when(r) for r in rows) if s)
        span = f"{stamps[0]:%d/%m/%Y} -> {stamps[-1]:%d/%m/%Y}" if stamps else "?"
        extra = sorted(set(keys) - base)
        print(f"\n  [dinh dang {index}]  {len(rows):>5} dong   {span}")
        print(f"     so truong    {len(keys)}")
        print(f"     truong rieng {extra if extra else '(khong co - day la nen chung)'}")

    print(f"\n  truong CHUNG cho moi dinh dang ({len(base)}): {sorted(base)}")


# ─────────────── 3. TLA HD: 2.223 token nam o lat cat nao ───────────────

def tla_gap(year: dict) -> None:
    head("3. TLA HD - 2.223 token lech nam o dau")

    totals = year["totals"]
    grand = num(totals["total_tokens"])
    halves = num(totals["prompt_tokens"]) + num(totals["completion_tokens"])
    print(f"  tong khai bao      {grand:>14,.0f}")
    print(f"  prompt+completion  {halves:>14,.0f}")
    print(f"  lech               {grand - halves:>14,.0f}")

    slices = (("costs.by_model", year["costs"]["by_model"], "model"),
              ("by_unit", year["by_unit"], "unit_name"),
              ("by_user", year["by_user"], "username"),
              ("by_function", year["by_function"], "function"),
              ("timeline", year["timeline"], "timestamp"))

    for label, rows, key in slices:
        offenders = []
        for row in rows:
            diff = (num(row.get("total_tokens")) - num(row.get("prompt_tokens"))
                    - num(row.get("completion_tokens")))
            if abs(diff) > 0.5:
                offenders.append((str(row.get(key)), diff))
        slice_gap = sum(diff for _, diff in offenders)
        print(f"\n  -- {label}  ({len(rows)} dong, {len(offenders)} dong lech, "
              f"tong lech {slice_gap:+,.0f}) --")
        for name, diff in sorted(offenders, key=lambda kv: -abs(kv[1]))[:6]:
            print(f"     {name:<34} {diff:+,.0f}")

    # Same question as for CTDA: constant per row, or proportional to volume?
    print("\n  -- lech co ty le voi luu luong khong --")
    for row in year["costs"]["by_model"]:
        diff = (num(row.get("total_tokens")) - num(row.get("prompt_tokens"))
                - num(row.get("completion_tokens")))
        calls = num(row.get("calls"))
        tokens = num(row.get("total_tokens"))
        per_call = diff / calls if calls else 0.0
        share = 100 * diff / tokens if tokens else 0.0
        print(f"     {str(row.get('model')):<22} lech {diff:>+8,.0f}  "
              f"{calls:>5,.0f} luot  {per_call:>7.2f} token/luot  {share:.4f}% tong")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    raw = read_json(DATA / "ctda" / "db-token_usage-raw.json")
    tla_year = read_json(DATA / "tla-hd" / "token-usage-year.json")

    ctda_gap(raw)
    ctda_shapes(raw)
    tla_gap(tla_year)


if __name__ == "__main__":
    main()
