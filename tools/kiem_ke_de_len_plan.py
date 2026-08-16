"""Inventory every dataset by what a database would need from it.

A plan written from memory of the data is a plan that will not survive contact
with it. This prints the four facts that decide table design, for every file:

    so dong      how big the table is
    khoa         what makes a row unique
    khoang ngay  what period it covers -- decides whether it can be joined
    do min       hour / day / month -- the finest grain, which caps every
                 report built on top of it

Read only. Writes nothing.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


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


def head(title: str) -> None:
    print(f"\n{'=' * 82}\n{title}\n{'=' * 82}")


def span_of(values) -> str:
    good = sorted(v for v in values if v)
    return f"{good[0][:10]} -> {good[-1][:10]}" if good else "khong ro"


def cols_of(rows: list, limit: int = 7) -> str:
    """Column list that survives an empty file instead of raising IndexError."""
    if not rows:
        return "(khong co dong nao)"
    names = list(rows[0].keys())
    return ", ".join(names[:limit]) + (" ..." if len(names) > limit else "")


# ───────────────── 1. hai app: cai gi dung duoc lam bang ─────────────────

def app_tables() -> None:
    head("1. HAI APP - lat cat nao dung duoc lam BANG")

    for agent, folder in (("TLA HD", "tla-hd"), ("CTDA", "ctda")):
        year = read_json(DATA / folder / "token-usage-year.json")
        print(f"\n  ### {agent} ###")
        totals = year["totals"]
        print(f"    tong: {totals['total_tokens']:,} token · {totals['call_count']:,} luot")

        slices = []
        for name in ("by_unit", "by_user", "by_function", "timeline",
                     "breakdown", "top_users", "top_functions"):
            if name in year:
                slices.append((name, year[name]))
        slices.append(("costs.by_model", year["costs"]["by_model"]))

        for name, rows in slices:
            rows = rows or []
            print(f"    {name:<18} {len(rows):>4} dong   cot: {cols_of(rows, 6)}")


def ctda_raw() -> None:
    head("2. CTDA BANG THO - nguon duy nhat co the lam BANG SU KIEN")
    raw = read_json(DATA / "ctda" / "db-token_usage-raw.json")
    print(f"  so dong        {len(raw):,}")
    print(f"  khoa           _id (khong trung)")
    stamps = [str(r.get("timestamp") or "") for r in raw]
    print(f"  khoang         {span_of(stamps)}")
    print(f"  do min         den micro-giay  <= min nhat trong toan bo du lieu")

    print("\n  -- truong nao co o bao nhieu dong (quyet dinh cot NULLABLE) --")
    fields = Counter()
    for row in raw:
        fields.update(row.keys())
    for field, count in sorted(fields.items(), key=lambda kv: (-kv[1], kv[0])):
        flag = "" if count == len(raw) else f"  <= THIEU o {len(raw) - count} dong"
        print(f"     {field:<28} {count:>5}/{len(raw)}{flag}")

    print("\n  -- gia tri thuc te cua cac cot phan loai --")
    for field in ("model", "function", "actor_type", "event_type", "pricing_mode"):
        seen = Counter(str(r.get(field, "(thieu)")) for r in raw)
        print(f"     {field:<14} {len(seen)} gia tri: "
              + ", ".join(f"{k}={v}" for k, v in seen.most_common(4)))


# ───────────────── 3. billing va monitoring ─────────────────

def billing_monitoring() -> None:
    head("3. BILLING + MONITORING - nguon ngoai, doc lap voi app")

    rows = read_csv(DATA / "billing" / "billing_gop_tru_CTDA.csv")
    print(f"\n  BILLING  {len(rows):,} dong   {span_of([r['date'] for r in rows])}")
    print(f"    khoa      (project, date, sku_id)")
    print(f"    do min    NGAY  <= khong the bao cao theo gio tu billing")
    projects = Counter(r["project"] for r in rows)
    print(f"    project   {len(projects)}: " + ", ".join(sorted(projects)))
    kinds = Counter()
    for row in rows:
        low = row["sku"].lower()
        kinds["cached" if "cached" in low else
              "output" if "output token" in low else
              "input" if "input token" in low else "khac"] += 1
    print(f"    loai SKU  {dict(kinds)}  <= PHAI cong cached vao input khi nap")

    folder = DATA / "da_xu_ly" / "du_lieu_giam_sat"
    pulls = sorted(p for p in folder.glob("*") if p.is_dir()) if folder.exists() else []
    if not pulls:
        print("\n  MONITORING  khong thay dot keo nao")
        return
    newest = pulls[-1]
    total = 0
    metrics = Counter()
    stamps = []
    for path in sorted(newest.glob("*.csv")):
        if path.name == "_tat-ca.csv":
            continue
        for row in read_csv(path):
            total += 1
            metrics[row.get("metric_alias", "?")] += 1
            stamps.append(row.get("ts_ict", ""))
    print(f"\n  MONITORING  {total:,} dong (da loc)   {span_of(stamps)}   [{newest.name}]")
    print(f"    khoa      (project, ts, metric, model, response_code)")
    print(f"    do min    1 PHUT  <= min nhat trong cac nguon Google")
    print(f"    phep do   {len(metrics)}:")
    for metric, count in metrics.most_common():
        print(f"       {metric:<52} {count:>7,}")


# ───────────────── 4. danh muc: user, don vi ─────────────────

def dimensions() -> None:
    head("4. BANG DANH MUC - de gan ten cho so lieu")

    users = read_json(DATA / "ctda" / "users-list.json")
    units = read_json(DATA / "ctda" / "units.json")["data"]
    print(f"\n  CTDA users   {len(users):,} dong   cot: {cols_of(users, 20)}")
    active = sum(1 for u in users if u.get("is_active"))
    with_unit = sum(1 for u in users if u.get("unit_id"))
    print(f"     dang hoat dong {active}   co don vi {with_unit}   co created_at "
          f"{sum(1 for u in users if u.get('created_at'))}")
    print(f"  CTDA units   {len(units):,} dong   cot: {cols_of(units, 20)}")

    for name in ("users-by-unit.csv", "user-usage-with-unit.csv", "adoption-by-unit.csv"):
        path = DATA / "tla-hd" / name
        if path.exists():
            rows = read_csv(path)
            print(f"  TLA HD {name:<26} {len(rows):>4} dong   cot: {cols_of(rows)}")


# ───────────────── 5. cai gi CHUA co ─────────────────

def missing() -> None:
    head("5. CAI GI CON THIEU - moi dong la mot cau hoi chua tra loi duoc")
    items = [
        ("URL + tai khoan cua 6 agent con lai", "khong co phong ban / nguoi dung cho 6/8 agent"),
        ("Bang tho cua TLA HD", "khong khoanh duoc 17% luot goi bi thieu"),
        ("Mui gio cua timestamp CTDA", "lech 7 tieng tren moi bieu do theo gio"),
        ("Bang gia chinh thuc theo model", "hien suy nguoc tu chi phi, chua ai xac nhan"),
        ("Ty gia VND", "dang go cung 25.200 trong app.js, khong nguon"),
        ("Ngan sach thang cua Ralli + Tools Quizzer", "mau so cua % ngan sach dang sai"),
        ("Agent nao goi gemini-embedding-001", "41,4 trieu token / $6,39 khong thuoc ai"),
        ("multimodal-invoice con chay khong", "khong co du lieu sau 25/07"),
        ("Luu luong TLA HD thang 3-6 chay o dau", "91,4% token khong co doi chung Google"),
        ("Vi sao app ghi thieu 17% luot goi", "Google do 342, app ghi 284, ca 342 deu ma 200"),
    ]
    for index, (question, why) in enumerate(items, start=1):
        print(f"  {index:>2}. {question}")
        print(f"      -> {why}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    app_tables()
    ctda_raw()
    billing_monitoring()
    dimensions()
    missing()


if __name__ == "__main__":
    main()
