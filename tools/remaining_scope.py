"""What is left after the three scope decisions of 07/08.

The decisions:
  A1  the six non-TLA-HD / non-Ralli projects each count as one agent and one
      user. No org hierarchy inside them.
  A2  drop March-June. Reporting starts at the end of June.
  A3  where Google and the app disagree, Google wins.

Each decision removes work, but each also removes data, and the second effect
is the one that gets discovered too late. This prints exactly what survives so
the cut-off date can be chosen on evidence instead of on a round number.

Read only. Writes nothing.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
GEMINI = "generativelanguage.googleapis.com"
ASK = ("GenerativeService.GenerateContent", "GenerativeService.StreamGenerateContent")

# Candidate cut-off dates, and why each one is arguable.
MOC = [
    (date(2026, 6, 1),  "dau thang 6  - giu tron thang 6 cua 3 project cu"),
    (date(2026, 6, 20), "20/06        - ngay tao project TLA HD"),
    (date(2026, 6, 24), "24/06        - dong billing dau tien cua tools-quizz"),
    (date(2026, 7, 1),  "dau thang 7  - moc thang tron, 4/7 project bat dau o day"),
]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def num(value) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", "")
    if text == "" or text.lower() in ("none", "null", "nan"):
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def as_date(text: str) -> date | None:
    try:
        return date.fromisoformat(str(text)[:10])
    except (ValueError, TypeError):
        return None


def head(title: str) -> None:
    print(f"\n{'=' * 80}\n{title}\n{'=' * 80}")


def share(part: float, whole: float) -> str:
    """Percentage that says so when there is nothing to divide by."""
    return f"{100 * part / whole:.1f}%" if whole else "n/a"


def billing_rows() -> list[dict]:
    return read_csv(DATA / "billing" / "billing_gop_tru_CTDA.csv")


def monitoring_rows():
    folder = DATA / "da_xu_ly" / "du_lieu_giam_sat"
    pulls = sorted(p for p in folder.glob("*") if p.is_dir()) if folder.exists() else []
    if not pulls:
        return
    for path in sorted(pulls[-1].glob("*.csv")):
        if path.name == "_tat-ca.csv":
            continue
        yield from read_csv(path)


# ───────────────── 1. moc cat nao thi con bao nhieu ─────────────────

def cut_offs() -> None:
    head("1. CAT TU MOC NAO THI CON LAI BAO NHIEU")
    bills = billing_rows()
    total_cost = sum(num(r["cost"]) for r in bills)
    print(f"  Toan bo billing hien co: ${total_cost:,.4f}  ({len(bills):,} dong)\n")

    print(f"  {'moc cat':<14} {'chi phi giu lai':>16} {'% giu':>7} {'so dong':>9} "
          f"{'so project con so lieu':>24}")
    for moc, note in MOC:
        kept = [r for r in bills if (d := as_date(r["date"])) and d >= moc]
        cost = sum(num(r["cost"]) for r in kept)
        projects = {r["project"] for r in kept}
        print(f"  {moc:%d/%m/%Y}   ${cost:>14,.4f} {share(cost, total_cost):>7} "
              f"{len(kept):>9,} {len(projects):>24}")
    print()
    for moc, note in MOC:
        print(f"    {moc:%d/%m}  {note}")


def per_project_by_month() -> None:
    head("2. TUNG PROJECT CO SO LIEU TU THANG NAO")
    bills = billing_rows()
    grid = defaultdict(lambda: defaultdict(float))
    for row in bills:
        grid[row["project"]][str(row["date"])[:7]] += num(row["cost"])
    months = sorted({str(r["date"])[:7] for r in bills})
    print(f"  {'project':<26}" + "".join(f"{m[5:]:>9}" for m in months))
    for project in sorted(grid):
        cells = "".join(f"{grid[project][m]:>9.2f}" if grid[project].get(m)
                        else f"{'-':>9}" for m in months)
        print(f"  {project:<26}{cells}")
    print("\n  => 4/7 project khong ton tai truoc thang 7. Cat tu 01/07 thi moi agent")
    print("     deu co du lieu tu ngay dau ky, khong agent nao 'bang 0 gia'.")


# ───────────────── 3. A3: Google thay app thi con gi ─────────────────

def google_only() -> None:
    head("3. NEU LAY GOOGLE LAM CHUAN - con thieu gi")
    counts = defaultdict(lambda: {"luot": 0.0, "loi": 0.0})
    for row in monitoring_rows():
        if row.get("metric_alias") != "api_request_count":
            continue
        if row.get("res_service") != GEMINI:
            continue
        if not any(m in (row.get("res_method") or "") for m in ASK):
            continue
        stamp = as_date(row.get("ts_ict", ""))
        if not stamp or stamp < date(2026, 7, 1):
            continue
        entry = counts[row.get("gcp_project_id", "?")]
        entry["luot"] += num(row.get("value"))
        code = str(row.get("response_code", ""))
        if code not in ("499",) and not code.startswith("2") and not code.startswith("3"):
            entry["loi"] += num(row.get("value"))

    print("  Luot goi tu 01/07 theo Google Monitoring (da loc Gemini + 2 phuong thuc hoi):\n")
    print(f"  {'project':<26} {'luot goi':>10} {'loi':>7} {'ty le loi':>10}")
    total = 0.0
    for project, entry in sorted(counts.items(), key=lambda kv: -kv[1]["luot"]):
        rate = 100 * entry["loi"] / entry["luot"] if entry["luot"] else 0.0
        total += entry["luot"]
        print(f"  {project:<26} {entry['luot']:>10,.0f} {entry['loi']:>7,.0f} {rate:>9.2f}%")
    print(f"  {'TONG':<26} {total:>10,.0f}")

    print("\n  -- Ralli / CTDA --")
    print("  KHONG co trong bang tren: Ralli khong di qua GCP truoc 27/07.")
    print("  => A3 'lay Google lam chuan' AP DUNG DUOC cho 7 project, KHONG cho Ralli.")
    print("     Rieng Ralli van phai dung so cua app, khong co hoa don doi chung.")


# ───────────────── 4. TLA HD: tong Google vs chia nho cua app ─────────────────

def tla_reconcile() -> None:
    head("4. TLA HD - lay tong cua Google nhung chia nho theo app thi lech bao nhieu")
    year = read_json(DATA / "tla-hd" / "token-usage-year.json")
    thang_7_8 = [r for r in year["timeline"] if str(r["timestamp"])[:7] in ("2026-07", "2026-08")]
    app_calls = sum(num(r["calls"]) for r in thang_7_8)
    app_tokens = sum(num(r["total_tokens"]) for r in thang_7_8)

    bills = [r for r in billing_rows()
             if r["project"] == "ai-chatbot-contract" and (d := as_date(r["date"])) and d >= date(2026, 7, 1)]
    bill_tokens = sum(num(r["amount"]) for r in bills)
    bill_cost = sum(num(r["cost"]) for r in bills)

    google_calls = 0.0
    for row in monitoring_rows():
        if (row.get("gcp_project_id") == "ai-chatbot-contract"
                and row.get("metric_alias") == "api_request_count"
                and row.get("res_service") == GEMINI
                and any(m in (row.get("res_method") or "") for m in ASK)):
            stamp = as_date(row.get("ts_ict", ""))
            if stamp and stamp >= date(2026, 7, 1):
                google_calls += num(row.get("value"))

    print(f"  {'':<22}{'app noi':>14}{'Google noi':>14}{'app thieu':>12}")
    print(f"  {'luot goi':<22}{app_calls:>14,.0f}{google_calls:>14,.0f}"
          f"{share(google_calls - app_calls, google_calls):>12}")
    print(f"  {'token':<22}{app_tokens:>14,.0f}{bill_tokens:>14,.0f}"
          f"{share(bill_tokens - app_tokens, bill_tokens):>12}")
    print(f"  {'tien':<22}{'(app tu tinh)':>14}{bill_cost:>14,.4f}")

    print("\n  Van de thiet ke chua co loi giai:")
    print("  Tong lay tu Google, nhung chia theo phong ban / nguoi dung chi app moi co -")
    print("  ma tong cua app thi THIEU. Cong cac phong ban lai se KHONG bang tong.")
    print(f"  Phan khong quy duoc ve ai: {bill_tokens - app_tokens:,.0f} token"
          f" ({google_calls - app_calls:,.0f} luot).")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cut_offs()
    per_project_by_month()
    google_only()
    tla_reconcile()


if __name__ == "__main__":
    main()
