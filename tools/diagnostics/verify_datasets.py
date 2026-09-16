"""Verify every dataset under data/ -- read only, no network.

Written to answer one question a reviewer will actually ask: "is this data
correct?" That question has five layers, and the ones that matter are not the
ones people usually check.

  A  INTEGRITY     file parses, no mojibake, no placeholder junk
  B  CONSISTENCY   sum of the slices == the stated total, within one source
  C  CROSS-CHECK   raw table vs aggregate API, merged file vs its parts
  D  PLAUSIBILITY  no negatives, no duplicate ids, no impossible timestamps
  E  TIMEZONE      which clock the stored timestamps are on
  F  KNOWN TRAPS   the traps documented in docs/uu-tien-thu-thap-du-lieu

Layers A-C are the ones a normal check stops at, and this dataset passes them.
Layer E is where the real risk is: every number can be individually valid while
the whole report is shifted seven hours. A check that cannot fail on layer E is
not checking the thing that would actually hurt.

Nothing here writes to data/. The only file written is the report next to this tool.

Usage
    python tools/diagnostics/verify_datasets.py
    python tools/diagnostics/verify_datasets.py --skip-monitoring   # skip 335 MB, runs fast
    python tools/diagnostics/verify_datasets.py --report ""         # print to the screen only
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# A 304 MB single-column value would otherwise raise _csv.Error. Nothing here
# is near that, but a truncated pull could produce one and the failure would
# look like corrupt data rather than a size limit.
csv.field_size_limit(10_000_000)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
GEMINI = "generativelanguage.googleapis.com"
ICT_OFFSET = timedelta(hours=7)

# Money is float all the way from the vendor's JSON, so exact equality is the
# wrong test. A cent is far below anything that changes a decision here.
USD_TOL = 0.01


# ───────────────────────────── results ─────────────────────────────

PASS, FAIL, WARN, INFO = "PASS", "FAIL", "WARN", "INFO"


class Report:
    """Collects results so the summary can be printed after everything ran.

    Deliberately does not stop at the first failure: the point of the run is a
    complete list to send back, not a bisect.
    """

    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str, str]] = []
        self.section = ""

    def open(self, title: str) -> None:
        self.section = title
        print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")

    def add(self, status: str, label: str, detail: str = "") -> None:
        mark = {PASS: "  PASS", FAIL: "> FAIL", WARN: "! WARN", INFO: "  INFO"}[status]
        print(f"{mark}  {label:<52} {detail}")
        self.rows.append((self.section, status, label, detail))

    def ok(self, label: str, detail: str = "") -> None:
        self.add(PASS, label, detail)

    def fail(self, label: str, detail: str = "") -> None:
        self.add(FAIL, label, detail)

    def warn(self, label: str, detail: str = "") -> None:
        self.add(WARN, label, detail)

    def info(self, label: str, detail: str = "") -> None:
        self.add(INFO, label, detail)

    def check(self, cond: bool, label: str, detail: str = "") -> bool:
        self.add(PASS if cond else FAIL, label, detail)
        return cond

    def count(self, status: str) -> int:
        return sum(1 for row in self.rows if row[1] == status)


R = Report()


# ───────────────────────────── reading ─────────────────────────────

def read_json(path: Path):
    """utf-8-sig because half these files carry a BOM and half do not.

    The split is not random: anything written by the PowerShell recon scripts
    has one, anything saved straight from the browser does not. Reading with
    plain utf-8 raises on the first group, which is how this was found.
    """
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def num(value) -> float:
    """Tolerant number parse. Billing exports quote thousands separators."""
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", "")
    if text == "" or text.lower() in ("none", "null", "nan", "-"):
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def same(a: float, b: float, tol: float = 0.5) -> bool:
    return abs(a - b) <= tol


def gap(a: float, b: float) -> str:
    if same(a, b):
        return f"{a:,.0f} = {b:,.0f}"
    return f"{a:,.2f} vs {b:,.2f}   off by {a - b:+,.2f}"


def naive(text: str) -> datetime | None:
    """Parse a stored timestamp without inventing a timezone.

    Whether the value means UTC or ICT is exactly what section E is trying to
    decide, so attaching an offset here would assume the answer.
    """
    if not text:
        return None
    body = text.strip().replace("Z", "")
    try:
        parsed = datetime.fromisoformat(body)
    except ValueError:
        for shape in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(body, shape)
                break
            except ValueError:
                continue
        else:
            return None
    return parsed.replace(tzinfo=None)


# ───────────────────────── A. file integrity ─────────────────────────

# Byte pairs that appear when UTF-8 is decoded as cp1252 and re-encoded. Any of
# these in a Vietnamese file means the text was mangled somewhere upstream.
MOJIBAKE = ("Ã¡", "Ã ", "áº", "Ã´", "Ä‘", "â€", "Ã½", "Ãª", "á»")
JUNK = ("System.Object", "[object Object]", "undefined")


def section_a(paths_json: list[Path], paths_csv: list[Path]) -> None:
    R.open("A. FILE INTEGRITY")

    broken = []
    for path in paths_json:
        try:
            read_json(path)
        except Exception as error:  # noqa: BLE001 - reporting, not handling
            broken.append(f"{path.name}: {type(error).__name__}")
    R.check(not broken, "every JSON file parses",
            f"{len(paths_json)} files" if not broken else "; ".join(broken[:3]))

    bad_csv, ragged = [], []
    for path in paths_csv:
        try:
            with path.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                header = next(reader, None)
                if header is None:
                    bad_csv.append(f"{path.name}: empty")
                    continue
                width = len(header)
                for line, row in enumerate(reader, start=2):
                    if row and len(row) != width:
                        ragged.append(f"{path.name}:{line} has {len(row)}/{width} columns")
                        break
        except Exception as error:  # noqa: BLE001
            bad_csv.append(f"{path.name}: {type(error).__name__}")
    R.check(not bad_csv, "every CSV file parses",
            f"{len(paths_csv)} files" if not bad_csv else "; ".join(bad_csv[:3]))
    R.check(not ragged, "every CSV row has all columns",
            "none ragged" if not ragged else "; ".join(ragged[:3]))

    hit_mojibake, hit_junk = [], []
    for path in paths_csv:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        found = [sign for sign in MOJIBAKE if sign in text]
        if found:
            hit_mojibake.append(f"{path.name} ({found[0]!r})")
        found = [sign for sign in JUNK if sign in text]
        if found:
            hit_junk.append(f"{path.name} ({found[0]})")
    R.check(not hit_mojibake, "no file has mojibake",
            "clean" if not hit_mojibake else "; ".join(hit_mojibake[:3]))
    R.check(not hit_junk, "no cell holds a junk value",
            "clean" if not hit_junk else "; ".join(hit_junk[:3]))

    with_bom = sum(1 for p in paths_json if p.read_bytes()[:3] == b"\xef\xbb\xbf")
    R.info("JSON files are inconsistent about BOM",
           f"{with_bom}/{len(paths_json)} have a BOM - reading with utf-8-sig handles it")


# ─────────────────────── B. consistency within one source ───────────────────────

def sum_of(rows, *keys) -> float:
    total = 0.0
    for row in rows:
        for key in keys:
            if key in row and row[key] is not None:
                total += num(row[key])
                break
    return total


def check_costs(agent: str, costs: dict) -> None:
    """The cost block must decompose, whatever JSON type it arrived as.

    CTDA sends these as JSON numbers, TLA HD sends the identical fields as
    JSON strings -- a Decimal serialised straight to text. Adding them without
    coercing concatenates instead of summing, which is a TypeError here but
    would be a silently wrong column in a loader that accepts it.
    """
    kinds = {type(costs[key]).__name__
             for key in ("total_cost_usd", "input_cost_usd", "output_cost_usd",
                         "cached_input_cost_usd", "cache_storage_cost_usd")
             if key in costs}
    R.info(f"{agent}  JSON type of the money fields", ", ".join(sorted(kinds)))

    parts = (num(costs["input_cost_usd"]) + num(costs["output_cost_usd"])
             + num(costs["cached_input_cost_usd"]) + num(costs["cache_storage_cost_usd"]))
    stated = num(costs["total_cost_usd"])
    R.check(same(parts, stated, USD_TOL), f"{agent}  input+output+cached+storage = total cost",
            f"${parts:.6f} vs ${stated:.6f}")

    by_model = sum_of(costs["by_model"], "total_cost_usd")
    R.check(same(by_model, stated, USD_TOL), f"{agent}  sum(by_model.cost) = total cost",
            f"${by_model:.6f} vs ${stated:.6f}")


def section_b_ctda(year: dict) -> None:
    totals = year["totals"]
    grand = totals["total_tokens"]
    calls = totals["call_count"]

    halves = totals["prompt_tokens"] + totals["completion_tokens"]
    R.check(same(halves, grand), "CTDA  prompt + completion = total_tokens",
            gap(halves, grand) + ("" if same(halves, grand)
                                  else "  <= tokens that are neither in nor out"))

    for label, rows, tok_key, call_key, closed in (
        ("by_unit", year["by_unit"], "total_tokens", "calls", True),
        ("breakdown", year["breakdown"], "tokens", "calls", True),
        ("costs.by_model", year["costs"]["by_model"], None, "calls", True),
        ("top_functions", year["top_functions"], "tokens", "calls", False),
        ("top_users", year["top_users"], "tokens", "calls", False),
    ):
        if tok_key is None:  # by_model reports the two halves, not the sum
            got = sum_of(rows, "prompt_tokens") + sum_of(rows, "completion_tokens")
        else:
            got = sum_of(rows, tok_key)
        got_calls = sum_of(rows, call_key)
        if closed:
            R.check(same(got, grand) and same(got_calls, calls),
                    f"CTDA  sum({label}) = total",
                    f"{gap(got, grand)} | calls {gap(got_calls, calls)}")
        else:
            # These two are explicitly top-N, so equality is not expected --
            # but exceeding the total would still be a real error.
            R.check(got <= grand + 0.5 and got_calls <= calls + 0.5,
                    f"CTDA  sum({label}) <= total  (top-N)",
                    f"{got:,.0f} / {grand:,.0f} tokens ({100 * got / grand:.1f}%)")

    check_costs("CTDA", year["costs"])


def section_b_tla(year: dict) -> None:
    totals = year["totals"]
    grand = totals["total_tokens"]
    calls = totals["call_count"]

    halves = totals["prompt_tokens"] + totals["completion_tokens"]
    R.check(same(halves, grand), "TLA HD  prompt + completion = total_tokens",
            gap(halves, grand) + ("" if same(halves, grand)
                                  else "  <= tokens that are neither in nor out"))

    # No raw table exists for this agent, so by_model is the finest grain
    # available for locating the same gap.
    off = [(m["model"], num(m["total_tokens"]) - num(m["prompt_tokens"])
            - num(m["completion_tokens"])) for m in year["costs"]["by_model"]]
    culprits = [f"{model}: {diff:+,.0f}" for model, diff in off if abs(diff) > 0.5]
    if culprits:
        R.info("TLA HD  which model carries the gap", "; ".join(culprits))

    for label, rows in (("by_unit", year["by_unit"]),
                        ("by_user", year["by_user"]),
                        ("by_function", year["by_function"]),
                        ("timeline", year["timeline"]),
                        ("costs.by_model", year["costs"]["by_model"])):
        got = sum_of(rows, "total_tokens")
        got_calls = sum_of(rows, "calls")
        R.check(same(got, grand) and same(got_calls, calls),
                f"TLA HD  sum({label}) = total",
                f"{gap(got, grand)} | calls {gap(got_calls, calls)}")

    check_costs("TLA HD", year["costs"])


# ───────────────────── C. cross-source checks ─────────────────────

def compare_csv_json(label: str, csv_path: Path, rows_json: list[dict],
                     numeric: tuple[str, ...]) -> None:
    """A derived CSV must be a faithful projection of its source JSON.

    Row count alone is not enough: the mojibake bug found earlier kept the row
    count intact while destroying every name, and the System.Object bug kept
    both count and numbers while losing a whole column.
    """
    if not csv_path.exists():
        R.warn(f"{label}: CSV file missing", str(csv_path.relative_to(ROOT)))
        return
    rows_csv = read_csv(csv_path)
    if not R.check(len(rows_csv) == len(rows_json), f"{label}: row count",
                   f"csv {len(rows_csv)} vs json {len(rows_json)}"):
        return
    shared = [key for key in numeric if rows_json and key in rows_json[0]]
    bad = []
    for key in shared:
        a = sum(num(row.get(key)) for row in rows_csv)
        b = sum(num(row.get(key)) for row in rows_json)
        if not same(a, b, USD_TOL if "cost" in key else 0.5):
            bad.append(f"{key}: {a:,.2f} vs {b:,.2f}")
    R.check(not bad, f"{label}: column totals",
            f"{len(shared)} columns match" if not bad else "; ".join(bad[:3]))


def section_c_raw_vs_api(raw: list[dict], year: dict, collections: dict) -> None:
    raw_csv = read_csv(DATA / "ctda" / "db-token_usage-raw.csv")
    R.check(len(raw) == len(raw_csv), "CTDA  raw JSON = raw CSV (row count)",
            f"{len(raw)} = {len(raw_csv)}")
    for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cached_tokens"):
        a = sum(num(r.get(key)) for r in raw)
        b = sum(num(r.get(key)) for r in raw_csv)
        R.check(same(a, b), f"CTDA  raw JSON = raw CSV ({key})", gap(a, b))

    totals = year["totals"]
    cached_api = sum_of(year["costs"]["by_model"], "cached_tokens")
    for label, got, want in (
        ("calls", len(raw), totals["call_count"]),
        ("total_tokens", sum(num(r.get("total_tokens")) for r in raw), totals["total_tokens"]),
        ("prompt_tokens", sum(num(r.get("prompt_tokens")) for r in raw), totals["prompt_tokens"]),
        ("completion_tokens", sum(num(r.get("completion_tokens")) for r in raw), totals["completion_tokens"]),
        ("cached_tokens", sum(num(r.get("cached_tokens")) for r in raw), cached_api),
    ):
        R.check(same(got, want), f"CTDA  raw table = aggregate API: {label}", gap(got, want))

    # Field presence, not just field values. A row missing `cached_tokens`
    # entirely reads as zero in every sum here, so the totals can reconcile
    # perfectly while part of the table has a different shape.
    expected_fields = ("_id", "timestamp", "model", "function", "actor_type", "user_id",
                       "username", "prompt_tokens", "completion_tokens", "total_tokens",
                       "cached_tokens", "pricing_mode", "event_type")
    absent = {field: sum(1 for r in raw if field not in r) for field in expected_fields}
    ragged = {field: count for field, count in absent.items() if count}
    if not ragged:
        R.ok("CTDA  every raw row has every field", f"{len(expected_fields)} fields")
    else:
        R.warn("CTDA  raw rows do not all have the same fields",
               "; ".join(f"{field} missing in {count}/{len(raw)} rows"
                         for field, count in sorted(ragged.items(), key=lambda x: -x[1])[:4]))

    entries = collections.get("collections") or collections.get("data") or []
    found = next((c for c in entries if c.get("name") == "token_usage"), None)
    if found:
        R.check(len(raw) == found["count"], "CTDA  raw = row count the database reports",
                f"{len(raw)} = {found['count']}")
    else:
        R.warn("CTDA  token_usage not found in db-collections", "")


def section_c_billing() -> None:
    merged_path = DATA / "billing" / "billing_gop_tru_CTDA.csv"
    if not merged_path.exists():
        R.warn("billing: merged file missing", str(merged_path.name))
        return
    merged = read_csv(merged_path)
    parts = sorted(p for p in (DATA / "billing").glob("*.csv") if p != merged_path)

    part_rows = 0
    part_cost = 0.0
    part_usage = 0.0
    for path in parts:
        rows = read_csv(path)
        part_rows += len(rows)
        for row in rows:
            # The per-project export offers three cost columns. Subtotal is the
            # one that already has savings applied, and it is what the merged
            # file kept -- picking Cost ($) instead reads 0.00 on small rows
            # because that column is rounded to cents.
            part_cost += num(row.get("Unrounded subtotal ($)") or row.get("Subtotal ($)")
                             or row.get("Cost ($)"))
            part_usage += num(row.get("Usage amount"))

    merged_cost = sum(num(row.get("cost")) for row in merged)
    merged_usage = sum(num(row.get("amount")) for row in merged)

    R.check(len(merged) == part_rows, "billing  merged = sum of the parts (rows)",
            f"{len(merged)} = {part_rows}  ({len(parts)} files)")
    R.check(same(merged_cost, part_cost, 0.05), "billing  merged = sum of the parts (cost)",
            f"${merged_cost:,.4f} vs ${part_cost:,.4f}")
    R.check(same(merged_usage, part_usage, 1.0), "billing  merged = sum of the parts (tokens)",
            f"{merged_usage:,.0f} vs {part_usage:,.0f}")
    R.info("billing  total cost", f"${merged_cost:,.4f} over {len(merged)} rows")


# ───────────────────────── D. plausibility ─────────────────────────

def section_d(raw: list[dict], users: list[dict], units: list[dict],
              ctda_year: dict, tla_year: dict) -> None:
    negatives = []
    for label, rows, keys in (
        ("raw", raw, ("prompt_tokens", "completion_tokens", "total_tokens", "cached_tokens")),
        ("CTDA by_unit", ctda_year["by_unit"], ("total_tokens", "calls", "total_cost_usd")),
        ("CTDA by_model", ctda_year["costs"]["by_model"], ("calls", "total_cost_usd")),
        ("TLA by_unit", tla_year["by_unit"], ("total_tokens", "calls", "total_cost_usd")),
        ("TLA by_user", tla_year["by_user"], ("total_tokens", "calls", "total_cost_usd")),
    ):
        for row in rows:
            for key in keys:
                if key in row and num(row[key]) < 0:
                    negatives.append(f"{label}.{key}")
                    break
    R.check(not negatives, "no negative values",
            "clean" if not negatives else f"{len(negatives)} rows: {negatives[:3]}")

    ids = Counter(row.get("_id") for row in raw)
    dup = [key for key, count in ids.items() if count > 1]
    R.check(not dup, "raw: no duplicate _id", f"{len(raw)} unique ids" if not dup else str(dup[:3]))

    # Where the missing tokens actually live. The year totals are short by 162,
    # so either a few rows carry the whole gap or every row is off by a little;
    # those two have completely different explanations.
    broken_sum = [r for r in raw
                  if not same(num(r.get("prompt_tokens")) + num(r.get("completion_tokens")),
                              num(r.get("total_tokens")))]
    if not broken_sum:
        R.ok("raw: prompt + completion = total on every row", "every row matches")
    else:
        gaps = Counter(int(num(r.get("total_tokens")) - num(r.get("prompt_tokens"))
                           - num(r.get("completion_tokens"))) for r in broken_sum)
        missing = sum(size * count for size, count in gaps.items())
        models = Counter(r.get("model", "?") for r in broken_sum)
        R.fail("raw: prompt + completion = total on every row",
               f"{len(broken_sum)}/{len(raw)} rows off, {missing:,.0f} tokens missing | "
               f"model: {dict(models.most_common(3))}")
        # A constant per-row gap is a fixed accounting overhead; a scattered one
        # is a rounding or a dropped field. They need different questions asked.
        R.info("raw: size of each gap",
               f"{dict(sorted(gaps.items()))} (token gap: rows)"
               + ("  <= ALWAYS the same, a fixed overhead"
                  if len(gaps) == 1 else "  <= uneven"))
        sample = broken_sum[0]
        prompt = sample.get("prompt_tokens")
        completion = sample.get("completion_tokens")
        total = sample.get("total_tokens")
        R.info("raw: one gap row as an example",
               f"prompt {prompt} + completion {completion} != total {total}  "
               f"({sample.get('model')}, {sample.get('function')})")

    over_cache = [r.get("_id") for r in raw if num(r.get("cached_tokens")) > num(r.get("prompt_tokens"))]
    R.check(not over_cache, "raw: cached <= prompt on every row",
            "cached is a subset of prompt" if not over_cache else f"{len(over_cache)} bad rows")

    stamps = [naive(r.get("timestamp")) for r in raw]
    missing = sum(1 for s in stamps if s is None)
    R.check(missing == 0, "raw: every row has a readable timestamp", f"{missing} bad rows")
    good = [s for s in stamps if s]
    if good:
        floor, ceiling = datetime(2026, 1, 1), datetime.now()
        out = [s for s in good if s < floor or s > ceiling]
        R.check(not out, "raw: timestamps within a plausible range",
                f"{min(good)} -> {max(good)}" if not out else f"{len(out)} rows out of range")

    user_ids = Counter(u["id"] for u in users)
    dup_user = [key for key, count in user_ids.items() if count > 1]
    R.check(not dup_user, "users: no duplicate id", f"{len(users)} accounts")

    known_users = set(user_ids)
    unit_ids = {u["id"] for u in units}
    dangling = {u["unit_id"] for u in users if u.get("unit_id") and u["unit_id"] not in unit_ids}
    R.check(not dangling, "users: unit_id points to a real unit",
            f"{len(unit_ids)} units" if not dangling else f"{len(dangling)} dangling unit_id")

    # The vendor's own by_unit says ~97% is unattributed. Confirm that from the
    # raw side so the figure is ours, not theirs. The membership set is built
    # once: inlining it into the generator made this 890x slower for no reason.
    resolvable = sum(1 for r in raw if r.get("user_id") in known_users)
    tok_resolvable = sum(num(r.get("total_tokens")) for r in raw
                         if r.get("user_id") in known_users)
    tok_all = sum(num(r.get("total_tokens")) for r in raw)
    R.info("raw: rows attributable to a real account",
           f"{resolvable}/{len(raw)} rows ({100 * resolvable / len(raw):.1f}%) | "
           f"{100 * tok_resolvable / tok_all:.1f}% tokens")


# ───────────────────────── E. timezone ─────────────────────────

def bucket_raw(raw: list[dict], shift: timedelta, shape: str) -> dict[str, list[float]]:
    out: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for row in raw:
        stamp = naive(row.get("timestamp"))
        if stamp is None:
            continue
        key = (stamp + shift).strftime(shape)
        out[key][0] += num(row.get("total_tokens"))
        out[key][1] += 1
    return out


def test_hypothesis(api_rows: list[dict], raw: list[dict], shift: timedelta,
                    shape: str, bucket_key: str) -> tuple[int, int]:
    """How many API buckets a given clock hypothesis reproduces exactly."""
    mine = bucket_raw(raw, shift, shape)
    hit = 0
    for row in api_rows:
        key = row[bucket_key]
        got = mine.get(key)
        if got and same(got[0], num(row["tokens"])) and same(got[1], num(row["calls"])):
            hit += 1
    return hit, len(api_rows)


def section_e(raw: list[dict], tla_year: dict) -> None:
    # ── E1/E2: does the API bucket the stored value as-is, or shifted? ──
    #
    # Only the hourly file can decide this. Daily buckets cannot: almost all
    # traffic sits in the early hours, so shifting it seven hours moves nothing
    # across a date boundary and both hypotheses reproduce the same days. The
    # coarse files are still run, but a tie there is expected, not a warning.
    decided = False
    for name, filename, shape, bucket_key, decisive in (
        ("by HOUR (token-usage-day)", "token-usage-day.json", "%Y-%m-%dT%H:00", "bucket", True),
        ("by DAY  (token-usage-month)", "token-usage-month.json", "%Y-%m-%d", "bucket", False),
        ("by DAY  (token-usage-week)", "token-usage-week.json", "%Y-%m-%d", "bucket", False),
    ):
        path = DATA / "ctda" / filename
        if not path.exists():
            continue
        api_rows = read_json(path).get("breakdown") or []
        if not api_rows:
            continue
        raw_hit, total = test_hypothesis(api_rows, raw, timedelta(0), shape, bucket_key)
        shift_hit, _ = test_hypothesis(api_rows, raw, ICT_OFFSET, shape, bucket_key)
        score = f"as stored {raw_hit}/{total} | +7h {shift_hit}/{total}"
        if raw_hit == total and shift_hit < total:
            decided = True
            R.ok(f"timezone  API uses the stored value as-is, {name}", score)
        elif shift_hit == total and raw_hit < total:
            decided = True
            R.fail(f"timezone  API ADDS 7h, {name}", score)
        elif decisive:
            R.warn(f"timezone  cannot tell apart, {name}", score)
        else:
            R.info(f"timezone  cannot tell apart, {name}",
                   score + ("  (expected: the hourly check already decided)" if decided
                            else "  (no check has decided yet)"))

    # ── E3: the activity profile is the only evidence about the stored clock ──
    hours = Counter()
    for row in raw:
        stamp = naive(row.get("timestamp"))
        if stamp:
            hours[stamp.hour] += 1
    if hours:
        work_naive = sum(count for hour, count in hours.items() if 8 <= hour <= 18)
        work_plus7 = sum(count for hour, count in hours.items() if 1 <= hour <= 11)
        total = sum(hours.values())
        peak = max(hours, key=lambda h: hours[h])
        R.info("timezone  busiest hour of the raw table",
               f"{peak:02d}h ({hours[peak]} calls) | read as-is: {100 * work_naive / total:.0f}% "
               f"within 8-18h | read as UTC: {100 * work_plus7 / total:.0f}% within 8-18h ICT")
        if work_plus7 > work_naive:
            R.warn("timezone  the CTDA raw table is most likely UTC",
                   "only +7h lands on VN working hours - ASK THE VENDOR to be sure")
        else:
            R.info("timezone  the CTDA raw table looks like VN time already", "")

    # ── E4: newest row vs when the file was pulled ──
    stamps = [s for s in (naive(r.get("timestamp")) for r in raw) if s]
    if stamps:
        pulled = datetime.fromtimestamp((DATA / "ctda" / "db-token_usage-raw.json").stat().st_mtime)
        lag = pulled - max(stamps)
        R.info("timezone  newest row vs when the file was pulled",
               f"newest {max(stamps):%d/%m %H:%M} | pulled {pulled:%d/%m %H:%M} | "
               f"gap {lag.total_seconds() / 3600:.1f}h")

    # ── E5: TLA HD states its offset outright, CTDA does not ──
    timeline = tla_year.get("timeline") or []
    marked = [row.get("timestamp") for row in timeline
              if isinstance(row.get("timestamp"), str)
              and ("+" in row.get("timestamp") or row.get("timestamp").endswith("Z"))]
    if marked:
        R.ok("timezone  TLA HD states its offset explicitly",
             f"{len(marked)}/{len(timeline)} points carry an offset, e.g. {marked[0]}")
    else:
        R.warn("timezone  TLA HD states no offset", "must assume the same as CTDA")


# ─────────────── F. back-derived prices + known traps ───────────────

def section_f_prices(ctda_year: dict, tla_year: dict) -> None:
    """Recover the unit price each app charged, and check it is a real price.

    Both apps bill cached input at one tenth of normal input and subtract the
    cached half out of prompt_tokens first. That gives two independent ways to
    reach the same rate, so a wrong cost column cannot stay hidden: it would
    have to be wrong in both directions by exactly the right amount.
    """
    rows = []
    for agent, models, has_cached_tokens in (
        ("CTDA", ctda_year["costs"]["by_model"], True),
        ("TLA HD", tla_year["costs"]["by_model"], False),
    ):
        for model in models:
            prompt = num(model.get("prompt_tokens"))
            completion = num(model.get("completion_tokens"))
            cost_in = num(model.get("input_cost_usd"))
            cost_out = num(model.get("output_cost_usd"))
            cost_cached = num(model.get("cached_input_cost_usd"))
            if prompt <= 0:
                continue
            # cost_in + 10*cost_cached == prompt/1e6 * rate_in, whether or not
            # the cached token count itself is published. That identity is what
            # lets TLA HD be checked at all: it publishes the cached *cost* but
            # never the cached token count.
            rate_in = (cost_in + 10 * cost_cached) * 1e6 / prompt
            rate_out = (cost_out * 1e6 / completion) if completion else 0.0
            if has_cached_tokens:
                cached = num(model.get("cached_tokens"))
            elif rate_in > 0:
                cached = cost_cached * 1e6 / (rate_in / 10)
            else:
                cached = 0.0
            # Kept as three separate terms on purpose. Folding the output term
            # into a conditional expression makes the ternary swallow the whole
            # sum, which silently zeroed every embedding-only model.
            rebuilt = (prompt - cached) / 1e6 * rate_in
            rebuilt += cached / 1e6 * rate_in / 10
            rebuilt += completion / 1e6 * rate_out
            rows.append((agent, model["model"], rate_in, rate_out,
                         rebuilt, num(model.get("total_cost_usd"))))

    bad = [f"{a} {m}" for a, m, _, _, built, stated in rows
           if not same(built, stated, USD_TOL)]
    R.check(not bad, "price  cost rebuilds from tokens and unit price",
            f"{len(rows)} models match" if not bad else "; ".join(bad[:3]))

    for agent, model, rate_in, rate_out, _, _ in rows:
        R.info(f"price  {agent} {model}",
               f"in ${rate_in:.4f}/1M  out ${rate_out:.4f}/1M  cached ${rate_in / 10:.4f}/1M")


def section_f_billing_models() -> None:
    merged = read_csv(DATA / "billing" / "billing_gop_tru_CTDA.csv")
    by_sku = defaultdict(float)
    cached_sku = set()
    for row in merged:
        sku = row.get("sku", "")
        by_sku[sku] += num(row.get("cost"))
        if "cached" in sku.lower() or "cache" in sku.lower():
            cached_sku.add(sku)
    R.info("billing  distinct SKUs", f"{len(by_sku)} SKUs")
    R.check(bool(cached_sku), "billing  has a separate cached SKU",
            f"{len(cached_sku)} SKUs - MUST be added to input when loading, never dropped")

    embedding = {sku: cost for sku, cost in by_sku.items() if "embed" in sku.lower()}
    if embedding:
        R.warn("billing  has embedding SKUs that belong to no agent",
               f"{len(embedding)} SKU, ${sum(embedding.values()):.4f}")

    per_project = defaultdict(lambda: [0.0, set()])
    for row in merged:
        entry = per_project[row.get("project", "?")]
        entry[0] += num(row.get("cost"))
        entry[1].add(row.get("date", ""))
    for project, (cost, dates) in sorted(per_project.items()):
        span = f"{min(dates)} -> {max(dates)}" if dates else "?"
        R.info(f"billing  {project}", f"${cost:>10,.4f}  {len(dates):>3} days  {span}")


def section_f_monitoring(raw_dir: Path, ready_dir: Path) -> None:
    """One streaming pass. The raw pull is 335 MB and must not be held in memory."""
    per_project = defaultdict(lambda: {
        "rows": 0, "junk": 0, "codes": Counter(), "services": Counter(),
        "tz_bad": 0, "negative": 0, "p95": set(), "ts": [None, None],
    })

    for path in sorted(raw_dir.glob("*.csv")):
        print(f"      {path.name:<36} {path.stat().st_size / 1e6:>7.1f} MB", flush=True)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                entry = per_project[row.get("gcp_project_id", "?")]
                entry["rows"] += 1

                alias = row.get("metric_alias", "")
                service = row.get("res_service", "")
                if alias.endswith("_limit") or (service and service != GEMINI):
                    entry["junk"] += 1

                if alias == "api_request_count":
                    entry["services"][service or "(no label)"] += num(row.get("value"))
                    code = row.get("response_code", "")
                    if code:
                        entry["codes"][code] += num(row.get("value"))

                utc, ict = naive(row.get("ts_utc", "")), naive(row.get("ts_ict", ""))
                if utc and ict and ict - utc != ICT_OFFSET:
                    entry["tz_bad"] += 1
                if utc:
                    span = entry["ts"]
                    if span[0] is None or utc < span[0]:
                        span[0] = utc
                    if span[1] is None or utc > span[1]:
                        span[1] = utc

                if num(row.get("value")) < 0:
                    entry["negative"] += 1
                if row.get("aligner") == "ALIGN_PERCENTILE_95" and service == GEMINI:
                    entry["p95"].add(round(num(row.get("value")), 2))

    total_rows = sum(e["rows"] for e in per_project.values())
    R.info("monitoring  raw rows", f"{total_rows:,} rows, {len(per_project)} projects")

    tz_bad = sum(e["tz_bad"] for e in per_project.values())
    R.check(tz_bad == 0, "monitoring  ts_ict = ts_utc + 7h on every row",
            "all correct" if tz_bad == 0 else f"{tz_bad} rows off")

    negative = sum(e["negative"] for e in per_project.values())
    R.check(negative == 0, "monitoring  no negative values", f"{negative} negative rows")

    # Trap 1: api_request_count counts every Google API the project touches.
    for project, entry in sorted(per_project.items()):
        gemini = entry["services"].get(GEMINI, 0.0)
        everything = sum(entry["services"].values())
        if everything <= 0:
            continue
        share = 100 * gemini / everything
        detail = (f"Gemini {gemini:,.0f} / all {everything:,.0f} ({share:.1f}%)  "
                  f"= {everything / gemini:.1f}x too high if left unfiltered" if gemini
                  else f"all {everything:,.0f}, NO Gemini")
        (R.ok if share > 99 else R.warn)(f"monitoring  {project}: must filter res_service", detail)

    # Trap: 499 is a user cancelling, not a system fault.
    codes = Counter()
    for entry in per_project.values():
        codes.update(entry["codes"])
    if codes:
        shown = "  ".join(f"{code}:{int(count)}" for code, count in sorted(codes.items()))
        R.info("monitoring  response code distribution", shown)
        R.check(codes.get("429", 0) == 0, "monitoring  never rate limited (429)",
                f"429 = {int(codes.get('429', 0))}")
        if codes.get("499"):
            R.warn("monitoring  has 499 - the user cancelled, NOT a system fault",
                   f"{int(codes['499'])} calls - must be split out of the 4xx group")

    # Trap: percentiles come from exponential buckets, so collisions are normal.
    shared = Counter()
    for entry in per_project.values():
        shared.update(set(entry["p95"]))
    collided = [value for value, count in shared.items() if count > 1]
    if collided:
        R.warn("monitoring  p95 values repeat across projects",
               f"{len(collided)} shared values, e.g. {sorted(collided)[:3]} "
               f"- read p95/p99 as a RANGE, not exact seconds")

    for project, entry in sorted(per_project.items()):
        low, high = entry["ts"]
        span = f"{low:%d/%m} -> {high:%d/%m}" if low and high else "no known time range"
        R.info(f"monitoring  {project}",
               f"{entry['rows']:>7,} rows  junk {entry['junk']:>7,}  {span}")

    # The readable copy is the raw pull either filtered (--filter) or not. Both are
    # legitimate outputs of make_readable.py, so the check is "does it equal one
    # of the two", not "does it equal the filtered one" -- otherwise an unfiltered
    # copy would be reported as corruption.
    if ready_dir.exists():
        ready_rows = 0
        for path in sorted(ready_dir.glob("*.csv")):
            if path.name == "_tat-ca.csv":  # vi-ok: on-disk file name written by make_readable.py
                continue
            with path.open(encoding="utf-8-sig", newline="") as handle:
                ready_rows += sum(1 for _ in csv.DictReader(handle))
        junk = sum(e["junk"] for e in per_project.values())
        filtered = total_rows - junk
        if ready_rows == filtered:
            R.ok("monitoring  processed copy = filtered raw pull",
                 f"{ready_rows:,} = {total_rows:,} - {junk:,} junk rows")
        elif ready_rows == total_rows:
            R.warn("monitoring  processed copy is NOT filtered",
                   f"{ready_rows:,} rows, still holding {junk:,} junk rows - rerun with --filter")
        else:
            R.fail("monitoring  processed copy does not match the raw pull",
                   f"{ready_rows:,} vs {filtered:,} (filtered) or {total_rows:,} (unfiltered)")


# ───────────────────────────── run ─────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     allow_abbrev=False)
    parser.add_argument("--skip-monitoring", action="store_true",
                        help="Skip the 335 MB of Monitoring data to run fast")
    parser.add_argument("--report", default=str(Path(__file__).parent / "verify-datasets-report.csv"),
                        help="Report file path (CSV). Leave empty to print to the screen only.")
    args = parser.parse_args()

    # The console here is cp1252; without this every section header raises.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    skip = {"raw_google_console", "da_xu_ly"}
    paths_json = sorted(p for p in DATA.rglob("*.json") if not skip & set(p.parts))
    paths_csv = sorted(p for p in DATA.rglob("*.csv") if not skip & set(p.parts))

    print(f"Data root : {DATA}")
    print(f"Checking  : {len(paths_json)} JSON + {len(paths_csv)} CSV"
          + ("  (Monitoring skipped)" if args.skip_monitoring else "  + Monitoring"))

    section_a(paths_json, paths_csv)

    ctda_year = read_json(DATA / "ctda" / "token-usage-year.json")
    tla_year = read_json(DATA / "tla-hd" / "token-usage-year.json")
    raw = read_json(DATA / "ctda" / "db-token_usage-raw.json")
    users = read_json(DATA / "ctda" / "users-list.json")
    units = read_json(DATA / "ctda" / "units.json")["data"]
    collections = read_json(DATA / "ctda" / "db-collections.json")

    R.open("B. CONSISTENCY WITHIN ONE SOURCE")
    section_b_ctda(ctda_year)
    section_b_tla(tla_year)

    R.open("C. CROSS-SOURCE CHECKS")
    section_c_raw_vs_api(raw, ctda_year, collections)
    compare_csv_json("CTDA by-unit", DATA / "ctda" / "by-unit-2026.csv",
                     ctda_year["by_unit"], ("total_tokens", "calls", "total_cost_usd"))
    compare_csv_json("CTDA by-model", DATA / "ctda" / "by-model-2026.csv",
                     ctda_year["costs"]["by_model"],
                     ("calls", "prompt_tokens", "completion_tokens", "cached_tokens", "total_cost_usd"))
    compare_csv_json("CTDA by-function", DATA / "ctda" / "by-function-2026.csv",
                     ctda_year["top_functions"], ("tokens", "calls"))
    compare_csv_json("CTDA timeline", DATA / "ctda" / "timeline-monthly-2026.csv",
                     ctda_year["breakdown"], ("tokens", "prompt", "completion", "calls"))
    compare_csv_json("CTDA top-users", DATA / "ctda" / "top-users-2026.csv",
                     ctda_year["top_users"], ("tokens", "calls", "total_cost_usd"))
    compare_csv_json("TLA HD by-unit", DATA / "tla-hd" / "by-unit-2026.csv",
                     tla_year["by_unit"], ("calls", "total_tokens", "prompt_tokens",
                                           "completion_tokens", "total_cost_usd"))
    compare_csv_json("TLA HD by-model", DATA / "tla-hd" / "by-model-2026.csv",
                     tla_year["costs"]["by_model"],
                     ("calls", "total_tokens", "prompt_tokens", "completion_tokens", "total_cost_usd"))
    compare_csv_json("TLA HD by-user", DATA / "tla-hd" / "by-user-2026.csv",
                     tla_year["by_user"], ("calls", "total_tokens", "prompt_tokens",
                                           "completion_tokens", "total_cost_usd"))
    compare_csv_json("TLA HD by-function", DATA / "tla-hd" / "by-function-2026.csv",
                     tla_year["by_function"], ("calls", "total_tokens", "total_cost_usd"))
    compare_csv_json("TLA HD timeline", DATA / "tla-hd" / "timeline-monthly-2026.csv",
                     tla_year["timeline"], ("calls", "total_tokens", "prompt_tokens",
                                            "completion_tokens", "total_cost_usd"))
    section_c_billing()

    R.open("D. PLAUSIBILITY")
    section_d(raw, users, units, ctda_year, tla_year)

    R.open("E. TIMEZONE")
    section_e(raw, tla_year)

    R.open("F. BACK-DERIVED PRICES AND KNOWN TRAPS")
    section_f_prices(ctda_year, tla_year)
    section_f_billing_models()
    if not args.skip_monitoring:
        raw_dir = DATA / "raw_google_console" / "du_lieu_giam_sat"  # vi-ok: on-disk path
        pulls = sorted(p for p in raw_dir.glob("*") if p.is_dir())
        if pulls:
            newest = pulls[-1]
            print(f"\n  ... reading {newest.name} (335 MB, takes about 1-2 minutes)")
            section_f_monitoring(newest, DATA / "da_xu_ly" / "du_lieu_giam_sat" / newest.name)  # vi-ok: on-disk path
        else:
            R.warn("monitoring  no pull found", str(raw_dir))

    R.open("SUMMARY")
    print(f"  PASS {R.count(PASS):>3}")
    print(f"  FAIL {R.count(FAIL):>3}")
    print(f"  WARN {R.count(WARN):>3}")
    print(f"  INFO {R.count(INFO):>3}")

    failures = [row for row in R.rows if row[1] == FAIL]
    warnings = [row for row in R.rows if row[1] == WARN]
    if failures:
        print("\n  --- FAILURES TO FIX ---")
        for _, _, label, detail in failures:
            print(f"    {label}  |  {detail}")
    if warnings:
        print("\n  --- WARNINGS TO READ ---")
        for _, _, label, detail in warnings:
            print(f"    {label}  |  {detail}")
    if not failures:
        print("\n  No failures. WARN entries are properties of the data, not technical faults.")

    if args.report:
        target = Path(args.report)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["section", "result", "check", "detail"])
            writer.writerows(R.rows)
        print(f"\nReport: {target}")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
