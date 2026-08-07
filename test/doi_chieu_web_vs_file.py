"""Check the scraped files against what the web UI actually shows.

Every other check in test/ compares our data against itself or against Google.
This one compares it against the vendor's own screen -- the thing a person would
point at and say "but the app says X". It is the only check that can catch a
scrape that pulled the wrong endpoint, read the wrong field, or silently went
stale.

The snapshot in ui-snapshot-*.json was transcribed from the rendered page, not
re-fetched from the API. That is deliberate: re-calling the API would only prove
the API agrees with itself.

Direction matters more than equality. The snapshot is NEWER than the scrape, so
for a running-total figure:

    web == file   the source stopped moving -- must match to the token
    web >  file   normal growth between the two dates
    web <  file   IMPOSSIBLE. A cumulative total cannot shrink. Either the
                  scrape captured something the app has since lost, or one of
                  the two is not what we think it is.

Only the third case is an error, and it is an error for every metric without
needing to know which agent grew. Rows are matched by name, so a renamed or
vanished category is caught too.

Read only. Writes nothing.
"""

from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SNAPSHOT = Path(__file__).parent / "ui-snapshot-2026-08-07.json"

# The UI rounds money to 4-6 places depending on the widget, so cost is compared
# loosely. Tokens and call counts are integers on both sides and compared exact.
USD_TOL = 0.0006

KHOP, TANG, LOI, TIN = "KHOP", "DA TANG", "LOI", "TIN"
_counts = {KHOP: 0, TANG: 0, LOI: 0, TIN: 0}


def say(status: str, label: str, detail: str = "") -> None:
    mark = {KHOP: "  KHOP  ", TANG: "  TANG  ", LOI: "> LOI   ", TIN: "  TIN   "}[status]
    _counts[status] += 1
    print(f"{mark}{label:<46} {detail}")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def num(value) -> float:
    """TLA HD returns money as JSON strings, CTDA as JSON numbers."""
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", "")
    if text == "" or text.lower() in ("none", "null", "nan"):
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


# The screen shows a Vietnamese label where the API returns a code. Discovered
# by this very check reporting four rows as missing on both sides at once --
# which is the signature of a naming mismatch, not of missing data.
LABEL_MAP = {
    "phân tích hợp đồng": "analyze",
    "hỏi đáp ai": "chat",
}


def key_of(name: str) -> str:
    """Match rows across two sources that disagree about spacing and accents.

    The UI writes 'Đội chuyên trách - Vùng 3' and the API 'Đội chuyên trách -
    Vùng 3' with a different dash and a stray double space. NFC first so the
    same letter composed two ways compares equal.
    """
    text = unicodedata.normalize("NFC", str(name or "")).lower()
    for dash in ("–", "—", "−"):
        text = text.replace(dash, "-")
    text = " ".join(text.split())
    return LABEL_MAP.get(text, text)


def shown(value: float, money: bool) -> str:
    """Format without mangling the number.

    Trailing-zero stripping is tempting here and wrong: "20.0000".rstrip("0")
    leaves "2.", and stripping the dot then prints twenty dollars as two.
    """
    if not money:
        return f"{value:,.0f}"
    text = f"{value:,.6f}".rstrip("0")
    return text + "0" if text.endswith(".") else text


def compare(label: str, web, file_value, tol: float = 0.0) -> None:
    """One metric, judged by direction rather than by equality."""
    if web is None:
        say(TIN, label, f"giao dien khong hien so - file co {file_value:,.0f}")
        return
    gap = web - file_value
    if abs(gap) <= tol or (tol == 0.0 and round(gap) == 0):
        say(KHOP, label, shown(web, tol > 0))
    elif gap > 0:
        # shown(), not :,.0f -- rounding money to whole dollars printed every
        # cost drift as "web 5 > file 5 (+0)", which reads as no drift at all.
        say(TANG, label, f"web {shown(web, tol > 0)} > file {shown(file_value, tol > 0)}"
                         f"   (+{shown(gap, tol > 0)})")
    else:
        say(LOI, label, f"web {shown(web, tol > 0)} < file {shown(file_value, tol > 0)}"
                        f"   ({shown(gap, tol > 0)})  <= tong luy ke KHONG the giam")


def compare_rows(title: str, web_rows: list[dict], file_rows: list[dict],
                 name_key: str, tok_keys: tuple[str, ...],
                 call_key: str, cost_key: str) -> None:
    print(f"\n  -- {title} --")
    by_name = {key_of(r.get(name_key)): r for r in file_rows}
    if len(by_name) != len(file_rows):
        say(LOI, f"{title}: ten bi trung trong file",
            f"{len(file_rows)} dong -> {len(by_name)} ten")

    seen = set()
    for row in web_rows:
        name = str(row["ten"])
        found = by_name.get(key_of(name))
        if found is None:
            say(LOI, f"  {name[:40]}", "co tren web, KHONG co trong file")
            continue
        seen.add(key_of(name))

        # A model row may publish the two halves instead of a single total.
        got = None
        for candidate in tok_keys:
            if candidate in found:
                got = num(found[candidate])
                break
        if got is None:
            got = num(found.get("prompt_tokens")) + num(found.get("completion_tokens"))

        compare(f"  {name[:40]} · token", row["tokens"], got)
        compare(f"  {name[:40]} · luot", row.get("calls"), num(found.get(call_key)))
        compare(f"  {name[:40]} · tien", row["cost_usd"], num(found.get(cost_key)), USD_TOL)

    for key, row in by_name.items():
        if key not in seen:
            say(LOI, f"  {str(row.get(name_key))[:40]}", "co trong file, KHONG co tren web")


def check_tla(web: dict) -> None:
    print(f"\n{'=' * 84}\nTLA HD  -  web 07/08  vs  file cao 05/08\n{'=' * 84}")
    year = read_json(DATA / "tla-hd" / "token-usage-year.json")
    totals, costs = year["totals"], year["costs"]

    compare("tong token", web["totals"]["total_tokens"], num(totals["total_tokens"]))
    compare("tong luot goi", web["totals"]["call_count"], num(totals["call_count"]))
    compare("tong tien", web["totals"]["total_cost_usd"], num(costs["total_cost_usd"]), USD_TOL)

    month = next((r for r in year["timeline"] if str(r["timestamp"])[:7] == "2026-08"), None)
    if month:
        print("\n  -- rieng thang 08/2026 --")
        compare("  token", web["thang_08_2026"]["total_tokens"], num(month["total_tokens"]))
        compare("  luot goi", web["thang_08_2026"]["call_count"], num(month["calls"]))
        compare("  tien", web["thang_08_2026"]["total_cost_usd"],
                num(month["total_cost_usd"]), USD_TOL)

    compare_rows("theo model", web["by_model"], costs["by_model"], "model",
                 ("total_tokens",), "calls", "total_cost_usd")
    compare_rows("theo phong ban", web["by_unit"], year["by_unit"], "unit_name",
                 ("total_tokens",), "calls", "total_cost_usd")
    compare_rows("theo chuc nang", web["by_function"], year["by_function"], "function",
                 ("total_tokens",), "calls", "total_cost_usd")

    print("\n  -- so dong theo nguoi dung --")
    compare("so nguoi trong bang", web["so_dong_by_user"], len(year["by_user"]))


def check_ctda(web: dict) -> None:
    print(f"\n{'=' * 84}\nCTDA  -  web 07/08  vs  file cao 05/08\n{'=' * 84}")
    year = read_json(DATA / "ctda" / "token-usage-year.json")
    totals, costs = year["totals"], year["costs"]

    compare("tong token", web["totals"]["total_tokens"], num(totals["total_tokens"]))
    compare("tong luot goi", web["totals"]["call_count"], num(totals["call_count"]))
    compare("tong tien", web["totals"]["total_cost_usd"], num(costs["total_cost_usd"]), USD_TOL)

    compare_rows("theo model", web["by_model"], costs["by_model"], "model",
                 ("total_tokens",), "calls", "total_cost_usd")
    compare_rows("theo phong ban", web["by_unit"], year["by_unit"], "unit_name",
                 ("total_tokens",), "calls", "total_cost_usd")


def check_row_sums(web: dict) -> None:
    """Do the rows on screen add up to the headline on screen?

    Stronger than any row-by-row match, and it needs no second source: a table
    whose rows sum to its own total cannot be missing a category. It also
    recovers a cell the accessibility tree omitted -- the missing count is
    whatever the difference is.
    """
    print(f"\n{'=' * 84}\nTONG CAC DONG TREN WEB = TONG CHUNG TREN WEB\n{'=' * 84}")
    for agent in ("tla-hd", "ctda"):
        snapshot = web[agent]
        for slice_name in ("by_model", "by_unit", "by_function"):
            rows = snapshot.get(slice_name)
            if not rows:
                continue
            tokens = sum(r["tokens"] for r in rows)
            calls = sum(r["calls"] for r in rows if r["calls"] is not None)
            blank = [r["ten"] for r in rows if r["calls"] is None]
            want_tokens = snapshot["totals"]["total_tokens"]
            want_calls = snapshot["totals"]["call_count"]

            note = f"token {tokens:,} / {want_tokens:,}"
            if tokens == want_tokens:
                say(KHOP, f"{agent} {slice_name}: token cong du", note)
            else:
                # by_model on CTDA is prompt+completion, so it is short by the
                # 162 the grand total carries. Named, not silently tolerated.
                say(TIN, f"{agent} {slice_name}: token lech", f"{note}  (thieu {want_tokens - tokens})")

            if blank:
                say(TIN, f"{agent} {slice_name}: suy ra o con thieu",
                    f"{blank[0][:30]} = {want_calls - calls} luot")
            elif calls == want_calls:
                say(KHOP, f"{agent} {slice_name}: luot goi cong du", f"{calls:,} / {want_calls:,}")
            else:
                say(LOI, f"{agent} {slice_name}: luot goi KHONG cong du",
                    f"{calls:,} / {want_calls:,}")


def check_gap_162(web: dict) -> None:
    """The 162-token defect, seen from the outside.

    If the gap on today's screen is still exactly 162, the fault stopped
    producing new bad rows and is confined to the 81 historical ones. If it
    grew, the fault is still live and the fix is urgent rather than cosmetic.
    """
    print(f"\n{'=' * 84}\nCHO LECH 162 TOKEN  -  con dang phat sinh khong\n{'=' * 84}")

    # Only CTDA can be tested this way. Its per-model Token column is
    # prompt+completion, so the declared grand total sits 162 above the sum.
    # TLA HD's per-model column already carries the missing tokens inside it --
    # its rows add up to the grand total exactly -- so the same subtraction
    # there yields 0 and would look like the defect had vanished.
    snapshot = web["ctda"]
    declared = snapshot["totals"]["total_tokens"]
    by_model = sum(row["tokens"] for row in snapshot["by_model"])
    gap = declared - by_model
    if gap == 162:
        say(KHOP, "CTDA: cho lech tren web hom nay",
            f"{gap} token - DUNG bang luc cao, loi da ngung phat sinh")
    elif gap > 162:
        say(LOI, "CTDA: cho lech DANG LON DAN",
            f"{gap} token hom nay vs 162 luc cao (+{gap - 162})")
    else:
        say(TIN, "CTDA: cho lech thay doi", f"{gap} hom nay vs 162 luc cao")

    say(TIN, "TLA HD: khong kiem duoc theo cach nay",
        "cot Token cua by_model da gom san 2.223 token thieu")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    web = read_json(SNAPSHOT)
    print(f"Anh chup giao dien : {web['captured_at']}")
    print(f"File da cao        : {web['scraped_at']}")
    print("Quy tac            : web < file la LOI (tong luy ke khong the giam);")
    print("                     web > file la binh thuong (web moi hon 2 ngay)")

    check_tla(web["tla-hd"])
    check_ctda(web["ctda"])
    check_row_sums(web)
    check_gap_162(web)

    print(f"\n{'=' * 84}\nTONG KET\n{'=' * 84}")
    for status in (KHOP, TANG, TIN, LOI):
        print(f"  {status:<10} {_counts[status]:>4}")
    if _counts[LOI]:
        print("\n  Co LOI - xem cac dong '> LOI' o tren.")
    else:
        print("\n  Khong co muc nao web thap hon file. Du lieu da cao la trung thuc.")
    sys.exit(1 if _counts[LOI] else 0)


if __name__ == "__main__":
    main()
