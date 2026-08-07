"""Extract what the dashboard actually asks for, from index.html and app.js.

Reading 1,100 lines of HTML by eye and then writing a plan from memory is how a
plan ends up describing a dashboard that does not exist. This walks the markup
instead and prints, per tab:

    the metric cards      id, label, the "=" definition, and the source badge
    the charts            id, title, chart type
    the tables            column headers
    the controls          period presets, group-by selectors, filters

The source badge matters more than it looks. Each card already declares where
its number is supposed to come from (src-batch / src-stream / ...), which is a
requirement written by whoever designed the screen -- not a guess by us.

Read only. Writes nothing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "index.html"
APP = ROOT / "app.js"

TAB_NAMES = {
    "overview": "1. Tong quan",
    "departments": "2. Phong ban & User",
    "agents": "3. Agents",
    "providers": "4. Provider & Model",
    "cost": "5. Chi phi",
    "performance": "6. Hieu nang",
}


def strip_tags(text: str) -> str:
    """Markup to plain text, keeping the words in order."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&amp;", "&").replace("&nbsp;", " ").replace("&lt;", "<")
    return " ".join(text.split())


def tab_blocks(html: str) -> list[tuple[str, str]]:
    """Split the document at each tab-content container.

    Splitting on the opening tag rather than parsing nested divs: the closing
    </div> of a tab cannot be found by counting without a real parser, and the
    next tab's opening tag marks the end just as reliably.
    """
    marks = [(m.start(), m.group(1))
             for m in re.finditer(r'<div class="tab-content[^"]*" id="([^"]+)"', html)]
    blocks = []
    for index, (start, tab_id) in enumerate(marks):
        end = marks[index + 1][0] if index + 1 < len(marks) else len(html)
        blocks.append((tab_id, html[start:end]))
    return blocks


def metric_cards(block: str) -> list[dict]:
    """One entry per metric card: its id, its label, its '=' definition, its badge."""
    cards = []
    for match in re.finditer(r'<div class="metric-card[^"]*">(.*?)(?=<div class="metric-card|\Z)',
                             block, re.S):
        chunk = match.group(1)[:900]
        label = re.search(r'class="metric-label"[^>]*>(.*?)</div>', chunk, re.S)
        value = re.search(r'class="metric-value" id="([^"]+)"', chunk)
        define = re.search(r'class="metric-def"[^>]*>(.*?)</div>', chunk, re.S)
        badge = re.search(r'class="src-dot ([^"]+)"[^>]*></span>(.*?)</div>', chunk, re.S)
        if not value:
            continue
        cards.append({
            "id": value.group(1),
            "label": strip_tags(label.group(1)) if label else "",
            "dinh_nghia": strip_tags(define.group(1)) if define else "",
            "nguon": strip_tags(badge.group(2)) if badge else "",
        })
    return cards


def charts(block: str) -> list[dict]:
    out = []
    for match in re.finditer(r'<div class="wf-chart[^"]*">(.*?)(?=<div class="wf-chart|\Z)',
                             block, re.S):
        chunk = match.group(1)[:900]
        canvas = re.search(r'<canvas id="([^"]+)"', chunk)
        title = re.search(r'class="wf-title"[^>]*>(.*?)</div>', chunk, re.S)
        kind = re.search(r'class="wf-type"[^>]*>(.*?)</span>', chunk, re.S)
        if canvas:
            out.append({
                "id": canvas.group(1),
                "tieu_de": strip_tags(title.group(1)) if title else "",
                "loai": strip_tags(kind.group(1)) if kind else "duong/cot",
            })
    # Canvases that live outside a wf-chart wrapper still need reporting.
    wrapped = {c["id"] for c in out}
    for match in re.finditer(r'<canvas id="([^"]+)"', block):
        if match.group(1) not in wrapped:
            out.append({"id": match.group(1), "tieu_de": "(khong co tieu de)", "loai": "?"})
    return out


def tables(block: str) -> list[list[str]]:
    out = []
    for match in re.finditer(r"<thead>(.*?)</thead>", block, re.S):
        cols = [strip_tags(c) for c in re.findall(r"<th[^>]*>(.*?)</th>", match.group(1), re.S)]
        if cols:
            out.append(cols)
    for match in re.finditer(r'<table class="heatmap[^"]*" id="([^"]+)"', block):
        out.append([f"(bang dong - dung JS - id={match.group(1)})"])
    return out


def controls(block: str) -> list[str]:
    out = []
    for match in re.finditer(r'<select id="([^"]+)"(.*?)</select>', block, re.S):
        options = re.findall(r"<option[^>]*>(.*?)</option>", match.group(2), re.S)
        out.append(f"{match.group(1)}: " + " | ".join(strip_tags(o) for o in options[:6]))
    return out


def dashboard() -> None:
    html = HTML.read_text(encoding="utf-8")
    first = html.find('<div class="tab-content')
    header = html[:first] if first > 0 else ""
    print(f"{'=' * 84}\nDIEU KHIEN CHUNG (nam NGOAI cac tab)\n{'=' * 84}")
    for found in re.finditer(r'id="(range[^"]*|[^"]*period[^"]*|[^"]*date[^"]*)"', header):
        print(f"  id = {found.group(1)}")
    for control in controls(header):
        print(f"  loc: {control[:110]}")
    for found in re.finditer(r'<button[^>]*class="[^"]*range[^"]*"[^>]*>(.*?)</button>',
                             header, re.S):
        print(f"  nut: {strip_tags(found.group(1))}")

    tong = {"the": 0, "bieu_do": 0, "bang": 0}

    for tab_id, block in tab_blocks(html):
        name = TAB_NAMES.get(tab_id, tab_id)
        cards, chart_list, table_list, control_list = (
            metric_cards(block), charts(block), tables(block), controls(block))
        tong["the"] += len(cards)
        tong["bieu_do"] += len(chart_list)
        tong["bang"] += len(table_list)

        print(f"\n{'=' * 84}\n{name}   "
              f"({len(cards)} the so · {len(chart_list)} bieu do · {len(table_list)} bang)"
              f"\n{'=' * 84}")

        for card in cards:
            print(f"  [{card['id']:<14}] {card['label']}")
            if card["dinh_nghia"]:
                print(f"       dinh nghia: {card['dinh_nghia'][:110]}")
            if card["nguon"]:
                print(f"       nguon ghi tren the: {card['nguon']}")
        for chart in chart_list:
            print(f"  <{chart['id']:<14}> {chart['loai']:<10} {chart['tieu_de'][:70]}")
        for cols in table_list:
            print(f"  bang: {' | '.join(cols)[:110]}")
        for control in control_list:
            print(f"  loc : {control[:110]}")

    print(f"\n{'=' * 84}\nTONG: {tong['the']} the so · {tong['bieu_do']} bieu do · "
          f"{tong['bang']} bang  =  {sum(tong.values())} o can du lieu\n{'=' * 84}")


def app_config() -> None:
    """The constants that decide what a period means and what a row contains."""
    print(f"\n{'=' * 84}\nCAU HINH TRONG app.js\n{'=' * 84}")
    text = APP.read_text(encoding="utf-8")

    presets = re.search(r"var RANGE_PRESETS\s*=\s*(\[.*?\]);", text, re.S)
    if presets:
        print(f"  Khoang thoi gian chon duoc: {' '.join(presets.group(1).split())}")

    schema = re.search(r"\{a:\"[^\"]+\",d:\"[^\"]+\".*?\}", text)
    if schema:
        keys = re.findall(r"([a-z_]+):", schema.group(0))
        print(f"  Cac truong cua MOT dong du lieu: {', '.join(dict.fromkeys(keys))}")

    for name in ("VND_RATE", "MONTHLY_BUDGET", "SEED_DAY", "STORE"):
        found = re.search(rf"var {name}\s*=\s*([^;]{{0,80}});", text)
        if found:
            print(f"  {name:<16} = {' '.join(found.group(1).split())}")

    budgets = re.search(r"var AGENT_MONTHLY_BUDGETS\s*=\s*\[(.*?)\];", text, re.S)
    if budgets:
        names = re.findall(r'agent:"([^"]+)",usd:(\d+)', budgets.group(1))
        print(f"  Ngan sach thang ({len(names)} agent):")
        for agent, usd in names:
            print(f"       {agent:<34} ${usd}")

    print("\n  -- cong thuc BIA ra so, phai thay bang so that --")
    for match in re.finditer(r"^\s*(\w+)\s*[:=]\s*([^;,\n]*\b(?:0\.64|0\.21|0\.15|2\.1)\b[^;,\n]*)",
                             text, re.M):
        print(f"       {match.group(1)} = {match.group(2).strip()}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    dashboard()
    app_config()


if __name__ == "__main__":
    main()
