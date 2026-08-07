"""Cross-check TLA HD against Google, three ways.

TLA HD is the only agent where all three sources exist for the same traffic:

    web API      what the vendor's own app reports
    billing      what Google charged  (project ai-chatbot-contract)
    monitoring   what Google measured (same project)

Every other agent has at most two. That makes this the one place where the
vendor's numbers can be checked against an outside party rather than against
themselves -- and a self-consistent source can still be uniformly wrong.

Three things must be handled or the comparison is meaningless:

  * cached tokens. Billing splits them into their own SKU; the web API folds
    them into prompt_tokens. Comparing prompt against the plain input SKU
    understates billing by the whole cached volume.
  * quota metrics are not usage metrics. Monitoring only exposes input tokens
    as a *quota* counter (paid_tier_3_input_token_count). Quota counts limit
    units, not tokens, so it is reported separately and never summed with the
    usage counters.
  * coverage. The three sources do not span the same dates. Comparing yearly
    totals across sources with different windows produces a large fake gap,
    so everything below is compared month by month and the windows are printed
    first.

Read only. Writes nothing.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PROJECT = "ai-chatbot-contract"
GEMINI = "generativelanguage.googleapis.com"
# The two methods that mean "a person asked the agent something", per the
# decision recorded in docs/uu-tien-thu-thap-du-lieu section 5b.
ASK_METHODS = ("GenerativeService.GenerateContent",
               "GenerativeService.StreamGenerateContent")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def num(value) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", "")
    if text == "" or text.lower() in ("none", "null", "nan", "-"):
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def head(title: str) -> None:
    print(f"\n{'=' * 84}\n{title}\n{'=' * 84}")


def pct(a: float, b: float) -> str:
    """Relative gap, worded so an empty side cannot read as agreement.

    The zero test uses a tolerance, not ==: these are sums of floats, and a
    denominator of 1e-16 would print a percentage in the billions.
    """
    if abs(b) < 1e-9:
        return "n/a" if abs(a) < 1e-9 else "chi 1 ben co"
    return f"{100 * (a - b) / b:+.1f}%"


def span(days: list[str], label: str) -> str:
    """A source with no rows must say so, not raise IndexError."""
    if not days:
        return f"KHONG CO DU LIEU ({label})"
    return f"{days[0]} -> {days[-1]}"


# ───────────────────── doc va phan loai tung nguon ─────────────────────

def sku_kind(sku: str) -> tuple[str, str]:
    """(model, kind) from a billing SKU description.

    Order matters: 'cached input token' also contains 'input token', so the
    cached test must run first or every cached row lands in plain input.
    """
    low = sku.lower()
    if "2.5 pro" in low:
        model = "gemini-2.5-pro"
    elif "2.5 flash" in low:
        model = "gemini-2.5-flash"
    elif "3 flash" in low or "3.0 flash" in low:
        model = "gemini-3.0-flash"
    elif "embed" in low:
        model = "embedding"
    else:
        model = f"(khong ro) {sku[:40]}"

    if "cached" in low:
        kind = "cached"
    elif "output token" in low:
        kind = "output"
    elif "input token" in low:
        kind = "input"
    else:
        kind = "khac"
    return model, kind


def load_web() -> dict:
    year = read_json(DATA / "tla-hd" / "token-usage-year.json")
    months: dict[str, dict] = {}
    for row in year["timeline"]:
        key = str(row["timestamp"])[:7]
        months[key] = {
            "calls": num(row.get("calls")),
            "prompt": num(row.get("prompt_tokens")),
            "completion": num(row.get("completion_tokens")),
            "total": num(row.get("total_tokens")),
            "cost": num(row.get("total_cost_usd")),
        }
    return {"months": months, "year": year}


def load_billing() -> dict:
    rows = [r for r in read_csv(DATA / "billing" / "billing_gop_tru_CTDA.csv")
            if r.get("project") == PROJECT]
    months: dict[str, dict] = defaultdict(
        lambda: {"input": 0.0, "output": 0.0, "cached": 0.0, "khac": 0.0, "cost": 0.0})
    per_model: dict[str, dict] = defaultdict(
        lambda: {"input": 0.0, "output": 0.0, "cached": 0.0, "khac": 0.0, "cost": 0.0})
    days = set()
    for row in rows:
        month = str(row.get("date"))[:7]
        days.add(str(row.get("date")))
        model, kind = sku_kind(str(row.get("sku")))
        months[month][kind] += num(row.get("amount"))
        months[month]["cost"] += num(row.get("cost"))
        per_model[model][kind] += num(row.get("amount"))
        per_model[model]["cost"] += num(row.get("cost"))
    return {"months": months, "per_model": per_model, "days": sorted(days), "rows": len(rows)}


def load_monitoring() -> dict:
    path = (DATA / "raw_google_console" / "du_lieu_giam_sat" / "2026-08-06-1m"
            / f"{PROJECT}.csv")
    months: dict[str, dict] = defaultdict(
        lambda: {"ask": 0.0, "all_api": 0.0, "output": 0.0, "quota_input": 0.0,
                 "quota_req": 0.0})
    per_model: dict[str, float] = defaultdict(float)
    days = set()
    for row in read_csv(path):
        alias = row.get("metric_alias", "")
        if alias.endswith("_limit"):
            continue  # a ceiling, not a measurement
        stamp = row.get("ts_ict") or ""
        month = stamp[:7]
        value = num(row.get("value"))

        if alias == "api_request_count":
            if row.get("res_service") != GEMINI:
                continue
            months[month]["all_api"] += value
            if any(m in (row.get("res_method") or "") for m in ASK_METHODS):
                months[month]["ask"] += value
                days.add(stamp[:10])
        elif alias == "generate_content_usage_output_token_count":
            months[month]["output"] += value
            per_model[row.get("model") or "?"] += value
        elif "input_token_count" in alias:
            months[month]["quota_input"] += value
        elif alias.endswith("_requests"):
            months[month]["quota_req"] += value
    return {"months": months, "per_model": per_model, "days": sorted(days)}


# ───────────────────────────── doi chieu ─────────────────────────────

def show_coverage(web: dict, bill: dict, mon: dict) -> None:
    head("1. BA NGUON PHU NHUNG KHOANG THOI GIAN NAO")
    web_months = sorted(web["months"])
    print(f"  web API      {span(web_months, 'web')}   "
          f"({len(web_months)} thang co du lieu)")
    print(f"  billing      {span(bill['days'], 'billing')}   "
          f"({len(bill['days'])} NGAY co phat sinh tien, {bill['rows']} dong)")
    print(f"  monitoring   {span(mon['days'], 'monitoring')}   "
          f"({len(mon['days'])} ngay co luot hoi)")
    print("\n  ==> chi so sanh duoc o phan GIAO NHAU. So sanh tong ca nam giua")
    print("      cac nguon co cua so khac nhau se tao ra chenh lech gia.")


def show_requests(web: dict, mon: dict) -> None:
    head("2. SO LUOT GOI  -  web API  vs  Google Monitoring")
    print(f"  {'thang':<9} {'web API':>10} {'Google (hoi)':>14} {'chenh':>10} "
          f"{'Google (moi API)':>18}")
    months = sorted(set(web["months"]) | set(mon["months"]))
    tot_web = tot_ask = 0.0
    for month in months:
        w = web["months"].get(month, {}).get("calls", 0.0)
        m = mon["months"].get(month, {})
        ask, every = m.get("ask", 0.0), m.get("all_api", 0.0)
        tot_web += w
        tot_ask += ask
        print(f"  {month:<9} {w:>10,.0f} {ask:>14,.0f} {pct(w, ask):>10} {every:>18,.0f}")
    print(f"  {'TONG':<9} {tot_web:>10,.0f} {tot_ask:>14,.0f} {pct(tot_web, tot_ask):>10}")


def show_tokens(web: dict, bill: dict, mon: dict) -> None:
    head("3. TOKEN  -  web API  vs  Google Billing")
    print("  Luu y: web API gop cached VAO prompt, billing tach rieng.")
    print("  Nen ve doi chieu:  web prompt  ==  billing (input + cached + khac)\n")
    print(f"  {'thang':<9} {'web prompt':>13} {'bill in+cache':>15} {'chenh':>9}   "
          f"{'web output':>12} {'bill output':>13} {'chenh':>9}")
    months = sorted(set(web["months"]) | set(bill["months"]))
    for month in months:
        w = web["months"].get(month, {})
        b = bill["months"].get(month, {})
        w_in, w_out = w.get("prompt", 0.0), w.get("completion", 0.0)
        b_in = b.get("input", 0.0) + b.get("cached", 0.0) + b.get("khac", 0.0)
        b_out = b.get("output", 0.0)
        print(f"  {month:<9} {w_in:>13,.0f} {b_in:>15,.0f} {pct(w_in, b_in):>9}   "
              f"{w_out:>12,.0f} {b_out:>13,.0f} {pct(w_out, b_out):>9}")

    print("\n  -- Google Monitoring do output token (nguon thu ba, doc lap) --")
    print(f"  {'thang':<9} {'web output':>12} {'monitoring':>12} {'chenh':>9}")
    for month in sorted(set(web["months"]) | set(mon["months"])):
        w_out = web["months"].get(month, {}).get("completion", 0.0)
        m_out = mon["months"].get(month, {}).get("output", 0.0)
        if w_out or m_out:
            print(f"  {month:<9} {w_out:>12,.0f} {m_out:>12,.0f} {pct(w_out, m_out):>9}")

    print("\n  -- phep do QUOTA cua Monitoring (KHONG dem token, dem don vi han muc) --")
    for month in sorted(mon["months"]):
        m = mon["months"][month]
        if m["quota_input"] or m["quota_req"]:
            print(f"  {month:<9} input_token(quota) {m['quota_input']:>13,.0f}   "
                  f"requests(quota) {m['quota_req']:>8,.0f}")


def show_cost(web: dict, bill: dict) -> None:
    head("4. TIEN  -  web API tu tinh  vs  Google Billing thu that")
    print(f"  {'thang':<9} {'web tu tinh':>13} {'Google thu':>12} {'chenh':>9}")
    tot_web = tot_bill = 0.0
    for month in sorted(set(web["months"]) | set(bill["months"])):
        w = web["months"].get(month, {}).get("cost", 0.0)
        b = bill["months"].get(month, {}).get("cost", 0.0)
        tot_web += w
        tot_bill += b
        print(f"  {month:<9} ${w:>12,.4f} ${b:>11,.4f} {pct(w, b):>9}")
    print(f"  {'TONG':<9} ${tot_web:>12,.4f} ${tot_bill:>11,.4f} {pct(tot_web, tot_bill):>9}")


def show_models(web: dict, bill: dict, mon: dict) -> None:
    head("5. THEO MODEL  (web API chi co so ca nam, billing chi co 9 ngay)")
    print("  -- web API, ca nam --")
    for row in web["year"]["costs"]["by_model"]:
        print(f"     {str(row.get('model')):<20} {num(row.get('calls')):>6,.0f} luot  "
              f"prompt {num(row.get('prompt_tokens')):>12,.0f}  "
              f"output {num(row.get('completion_tokens')):>11,.0f}  "
              f"${num(row.get('total_cost_usd')):>8.4f}")
    print("\n  -- billing, 9 ngay --")
    for model, data in sorted(bill["per_model"].items()):
        print(f"     {model:<20} {'':>6}       "
              f"input  {data['input'] + data['khac']:>12,.0f}  "
              f"output {data['output']:>11,.0f}  cached {data['cached']:>11,.0f}  "
              f"${data['cost']:>8.4f}")
    print("\n  -- monitoring, output token theo model --")
    for model, value in sorted(mon["per_model"].items(), key=lambda kv: -kv[1]):
        print(f"     {model:<20} {'':>6}       {'':>19} output {value:>11,.0f}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    web, bill, mon = load_web(), load_billing(), load_monitoring()
    show_coverage(web, bill, mon)
    show_requests(web, mon)
    show_tokens(web, bill, mon)
    show_cost(web, bill)
    show_models(web, bill, mon)


if __name__ == "__main__":
    main()
