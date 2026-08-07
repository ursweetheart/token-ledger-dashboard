"""Filter a Monitoring pull and print the numbers that prove it is sound.

Two traps make raw Cloud Monitoring counts wrong by default. Both are documented
in docs/uu-tien-thu-thap-du-lieu-2026-08-06.md section 3; both are fixed here
rather than at pull time, so the raw files stay untouched.

  Trap 1  The GenerateContent quota metric is counted by two limits at once
          (PerDay and PerMinute), each reporting the same number. Summing both
          doubles every request count.
  Trap 2  serviceruntime api/request_count and api/request_latencies cover every
          Google API the project touches. On pro-tuner-454203-v3, 97.4% of that
          total is Google Drive traffic that has nothing to do with Gemini.

Run this right after every pull. If the printed numbers look wrong, the pull is
wrong — that is cheaper to learn now than after seven projects.

Reads a pull directory written by pull_monitoring.py:
  data/raw_google_console/du_lieu_giam_sat/<date>-<do min>/<project>.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
import collections
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEMINI = "generativelanguage.googleapis.com"


def classify(row: dict) -> str:
    """Group a row by what it measures, tolerating renamed metrics.

    The `_limit` split is not cosmetic. Every quota metric ships in a pair:
    `.../usage` (how much was consumed) and `.../limit` (the ceiling). An
    unlimited ceiling reports as int64 max, 9.22e18 — mixing the two turns a
    request count into a meaningless 10^20. Caught on the first real pull.
    """
    metric_type = row.get("metric_type", "") or ""
    alias = row.get("metric_alias") or row.get("metric_name") or ""
    if metric_type.endswith("api/request_count") or alias == "api_request_count":
        return "api_request_count"
    if metric_type.endswith("api/request_latencies") or alias in ("latency_p95_s", "api_request_latencies"):
        return "latency"
    if metric_type.endswith("/limit") or alias.endswith("_limit"):
        return "quota_limit"
    if "output_token" in alias:
        return "output_tokens"
    if "input_token" in alias:
        return "input_tokens"
    if "request" in alias:
        # Embedding calls are requests too, but not the same kind of request.
        # Kept apart so the dashboard's definition stays explicit (trap 3).
        return "embed_requests" if "embed" in alias else "quota_requests"
    return "other"


def stamp(row: dict) -> str:
    """The UTC timestamp, whatever the pull called it.

    Renamed from ts_hour_utc to ts_utc once pulls stopped being hourly. Older
    files on disk still use the old name and must keep working.
    """
    return row.get("ts_utc") or row.get("ts_hour_utc") or ""


def read_rows(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                row["_kind"] = classify(row)
                try:
                    row["_value"] = float(row.get("value") or 0)
                except ValueError:
                    row["_value"] = 0.0
                rows.append(row)
    return rows


def pick_limit(rows: list[dict]) -> tuple[str, str]:
    """Choose one quota limit so trap 1 cannot double-count.

    Returns (chosen limit_name, note). Prefers the per-day limit; falls back to
    the only limit present; reports honestly when it cannot decide.
    """
    limits = sorted({row.get("limit_name", "") for row in rows if row.get("limit_name")})
    if not limits:
        return "", "khong co nhan limit_name — KHONG khu duoc dem dup, kiem tay"
    per_day = [limit for limit in limits if "PerDay" in limit]
    if per_day:
        return per_day[0], f"chon PerDay trong {len(limits)} limit"
    if len(limits) == 1:
        return limits[0], "chi co 1 limit, dung luon"
    return limits[0], f"KHONG thay PerDay; tam dung {limits[0]!r} trong {limits}"


def summarise(rows: list[dict]) -> dict:
    projects: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        projects[row.get("gcp_project_id", "?")].append(row)

    report = {}
    for project, project_rows in sorted(projects.items()):
        quota = [r for r in project_rows if r["_kind"] == "quota_requests"]
        limit, note = pick_limit(quota)
        quota_kept = [r for r in quota if not limit or r.get("limit_name") == limit]

        api = [r for r in project_rows if r["_kind"] == "api_request_count"]
        api_gemini = [r for r in api if r.get("res_service") == GEMINI]
        errors = [r for r in api_gemini if not str(r.get("response_code", "")).startswith("2")]

        latency = [r for r in project_rows
                   if r["_kind"] == "latency" and r.get("res_service") == GEMINI]
        # Files pulled before p99 existed carry neither an `aligner` column nor a
        # suffix, so an unmarked latency row is p95 by history.
        def percentile(rows_in: list[dict], tag: str) -> list[dict]:
            return [r for r in rows_in
                    if tag in (r.get("aligner", "") or "")
                    or (tag == "95" and not r.get("aligner"))]

        stamps = [s for s in (stamp(r) for r in project_rows) if s]
        methods = collections.Counter()
        keys = collections.Counter()
        for row in api_gemini:
            methods[(row.get("res_method", "") or "?").split(".")[-1]] += row["_value"]
            keys[row.get("res_credential_id", "") or "?"] += row["_value"]

        report[project] = {
            "quota_raw": sum(r["_value"] for r in quota),
            "quota": sum(r["_value"] for r in quota_kept),
            "limit": limit,
            "limit_note": note,
            "embed": sum(r["_value"] for r in project_rows if r["_kind"] == "embed_requests"),
            "api_raw": sum(r["_value"] for r in api),
            "api": sum(r["_value"] for r in api_gemini),
            "errors": sum(r["_value"] for r in errors),
            "codes": sorted({r.get("response_code", "") for r in api_gemini if r.get("response_code")}),
            "p95_max": max((r["_value"] for r in percentile(latency, "95")), default=0.0),
            "p99_max": max((r["_value"] for r in percentile(latency, "99")), default=0.0),
            "methods": methods,
            "keys": keys,
            # Distinct buckets with traffic. At 60s alignment these are minutes,
            # not hours -- the column is a liveness signal either way.
            "hours": len({stamp(r) for r in quota_kept or api_gemini}),
            "models": sorted({r.get("model", "") for r in project_rows if r.get("model")}),
            "since": min(stamps, default="-"),
            "until": max(stamps, default="-"),
        }
    return report


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default="", help="Thu muc mot dot keo")
    parser.add_argument("--file", default="", help="Mot file CSV cu the")
    parser.add_argument("--out", default="", help="Neu dat, ghi ban da loc ra CSV nay")
    args = parser.parse_args()

    if args.file:
        paths = [Path(args.file)]
    elif args.dir:
        paths = sorted(Path(args.dir).glob("*.csv"))
    else:
        pulls = sorted((ROOT / "data" / "raw_google_console" / "du_lieu_giam_sat").glob("*/"))
        if not pulls:
            raise SystemExit("Chua co dot keo nao. Chay pull_monitoring.py truoc.")
        paths = sorted(pulls[-1].glob("*.csv"))

    paths = [p for p in paths if p.exists()]
    if not paths:
        raise SystemExit("Khong tim thay file nao. Dung --dir hoac --file.")

    print("Doc:")
    for path in paths:
        print(f"  {path.relative_to(ROOT) if ROOT in path.parents else path}")
    rows = read_rows(paths)
    print(f"  {len(rows)} dong\n")

    report = summarise(rows)

    print("TRUOC KHI LOC  ->  SAU KHI LOC   (chenh lech cang lon, bay cang nguy hiem)")
    print(f"{'project':<26}{'quota req':>22}{'api req':>22}")
    for project, data in report.items():
        quota = f"{data['quota_raw']:,.0f} -> {data['quota']:,.0f}"
        api = f"{data['api_raw']:,.0f} -> {data['api']:,.0f}"
        print(f"{project:<26}{quota:>22}{api:>22}")

    print("\nBANG KIEM CHUNG")
    header = (f"{'project':<26}{'GenContent':>11}{'req(API)':>9}{'loi':>6}"
              f"{'ty le loi':>11}{'p95':>8}{'p99':>8}{'key':>5}{'gio':>6}{'model':>7}  khoang")
    print(header)
    print("-" * len(header))
    for project, data in report.items():
        rate = (data["errors"] / data["api"] * 100) if data["api"] else 0.0
        span = f"{data['since'][:10]} -> {data['until'][:10]}"
        # The agreed definition of "a request": user-facing generation only.
        gen = sum(v for k, v in data["methods"].items() if "GenerateContent" in k)
        print(f"{project:<26}{gen:>11,.0f}{data['api']:>9,.0f}{data['errors']:>6,.0f}"
              f"{rate:>10.2f}%{data['p95_max']:>8.2f}{data['p99_max']:>8.2f}"
              f"{len(data['keys']):>5}{data['hours']:>6}{len(data['models']):>7}  {span}")

    print("\nCHI TIET")
    for project, data in report.items():
        print(f"  {project}")
        print(f"    limit da chon : {data['limit'] or '(khong co)'}  [{data['limit_note']}]")
        print(f"    ma tra ve     : {', '.join(data['codes']) or '-'}")
        print(f"    model         : {', '.join(data['models']) or '-'}")
        print(f"    quota requests: {data['quota']:,.0f}"
              f"  (don vi han muc, KHONG phai luot goi)")
        if data["methods"]:
            top = ", ".join(f"{k}={v:,.0f}" for k, v in data["methods"].most_common(6))
            print(f"    method        : {top}")
        if data["keys"]:
            for key, value in data["keys"].most_common():
                print(f"    key           : {key:<48} {value:>9,.0f}")

    if args.out:
        keep = {"quota_requests", "api_request_count", "latency"}
        filtered = [
            row for row in rows
            if row["_kind"] in keep
            and (row["_kind"] != "api_request_count" or row.get("res_service") == GEMINI)
            and (row["_kind"] != "latency" or row.get("res_service") == GEMINI)
            and (row["_kind"] != "quota_requests"
                 or row.get("limit_name") == report[row.get("gcp_project_id", "?")]["limit"])
        ]
        columns = [c for c in rows[0] if not c.startswith("_")]
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, quoting=csv.QUOTE_ALL,
                                    extrasaction="ignore")
            writer.writeheader()
            writer.writerows(filtered)
        print(f"\nDa ghi ban loc: {out_path}  ({len(filtered)} dong)")


if __name__ == "__main__":
    main()
