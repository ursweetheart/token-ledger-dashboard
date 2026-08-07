"""Everything wrong with the CTDA (Ralli) dataset, in one place.

CTDA is the agent this project can check least. It never went through Google
Cloud before 27/07, so there is no invoice and no independent measurement to
compare against -- every number it reports can only be checked against itself.
That makes self-consistency necessary but nowhere near sufficient, and it makes
listing the known weaknesses more important here than anywhere else.

Read only. Writes nothing.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CTDA = ROOT / "data" / "ctda"

NANG, VUA, NHE, TIN = "NANG ", "VUA  ", "NHE  ", "TIN  "
_found: list[tuple[str, str, str]] = []


def note(muc: str, van_de: str, so_lieu: str) -> None:
    _found.append((muc, van_de, so_lieu))
    print(f"  [{muc}] {van_de}")
    print(f"         {so_lieu}")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def when(row: dict):
    try:
        return datetime.fromisoformat(str(row.get("timestamp") or "").replace("Z", ""))
    except ValueError:
        return None


def head(title: str) -> None:
    print(f"\n{'=' * 80}\n{title}\n{'=' * 80}")


def ty_le(phan: float, tong: float) -> str:
    """Percentage that reports an empty denominator instead of raising."""
    return f"{100 * phan / tong:.1f}%" if tong else "n/a"


# ───────────────── 1. khong co nguon ngoai de doi chieu ─────────────────

def khong_doi_chung(raw: list[dict], year: dict) -> None:
    head("1. KHONG CO NGUON NGOAI - diem mu lon nhat")
    billing = ROOT / "data" / "billing" / "billing_gop_tru_CTDA.csv"
    ten_file = billing.name
    note(NANG, "Khong co hoa don Google nao cho CTDA",
         f"File billing ten '{ten_file}' - 'gop TRU CTDA'. 7 project deu khong phai CTDA.")
    note(NANG, "So tien cua CTDA la do APP TU TINH",
         f"${num(year['costs']['total_cost_usd']):.6f} tren {len(raw):,} luot goi. "
         f"Khong ai thu so tien nay, khong co gi doi chieu.")

    tla = read_json(ROOT / "data" / "tla-hd" / "token-usage-year.json")
    note(TIN, "De so sanh: TLA HD co doi chung thi app ghi THIEU 17%",
         "Neu CTDA dung chung thu vien ghi log, kha nang no cung thieu tuong tu - "
         "nhung KHONG CACH NAO chung minh hay bac bo.")
    note(TIN, "Quy mo tuong doi",
         f"CTDA {len(raw):,} luot / {num(year['totals']['total_tokens']):,.0f} token / "
         f"${num(year['costs']['total_cost_usd']):.2f}  |  "
         f"TLA HD {num(tla['totals']['call_count']):,.0f} luot / "
         f"{num(tla['totals']['total_tokens']):,.0f} token / "
         f"${num(tla['costs']['total_cost_usd']):.2f}")


# ───────────────── 2. gan luu luong ve nguoi ─────────────────

def quy_ve_nguoi(raw: list[dict], year: dict) -> None:
    head("2. GAN LUU LUONG VE NGUOI DUNG")
    users = read_json(CTDA / "users-list.json")
    known = {u["id"] for u in users}

    hop_le = [r for r in raw if r.get("user_id") in known]
    co_uid = [r for r in raw if r.get("user_id")]
    tokens = sum(num(r.get("total_tokens")) for r in raw)
    tok_ok = sum(num(r.get("total_tokens")) for r in hop_le)

    note(NANG, "Rat it luu luong quy duoc ve mot tai khoan co that",
         f"{len(hop_le)}/{len(raw)} dong ({ty_le(len(hop_le), len(raw))}) · "
         f"{ty_le(tok_ok, tokens)} token")

    treo = [r for r in co_uid if r.get("user_id") not in known]
    ten_treo = Counter(str(r.get("user_id")) for r in treo)
    note(NANG, "Truong user_id cu chua CHUOI TEN, khong phai ma tai khoan",
         f"{len(treo):,} dong co user_id nhung KHONG tra ra ai. "
         f"Chi {len(ten_treo)} gia tri khac nhau: "
         + ", ".join(f"{k}({v})" for k, v in ten_treo.most_common(5)))

    cuu_duoc = {u["username"] for u in users}
    noi_lai = sum(count for name, count in ten_treo.items() if name in cuu_duoc)
    note(TIN, "Co the cuu duoc bao nhieu bang cach noi user_id -> users.username",
         f"{noi_lai:,}/{len(treo):,} dong noi lai duoc "
         f"({ty_le(noi_lai, len(treo))}) neu chap nhan phep noi thu hai")

    khong_xd = next((u for u in year["by_unit"] if not u.get("unit_id")), None)
    if khong_xd:
        # Hoisted out of the f-string: Python 3.11 cannot nest the same quote
        # character inside an f-string expression.
        tok_kxd = num(khong_xd["total_tokens"])
        note(NANG, "Mot 'don vi' nuot gan het bao cao theo phong ban",
             f"'{khong_xd['unit_name']}' chiem {tok_kxd:,.0f} token "
             f"({ty_le(tok_kxd, tokens)}) · {num(khong_xd['calls']):,.0f} luot")


# ───────────────── 3. bang tho khong dong nhat ─────────────────

def dinh_dang(raw: list[dict]) -> None:
    head("3. BANG THO CO BA DINH DANG KHAC NHAU")
    shapes: dict[frozenset, list[dict]] = defaultdict(list)
    for row in raw:
        shapes[frozenset(row.keys())].append(row)
    base = set.intersection(*(set(k) for k in shapes))

    ordered = sorted(shapes.items(), key=lambda kv: len(kv[1]), reverse=True)
    for index, (keys, rows) in enumerate(ordered, start=1):
        stamps = sorted(s for s in (when(r) for r in rows) if s)
        note(VUA, f"Dinh dang {index}: {len(keys)} truong, {len(rows):,} dong",
             (f"{stamps[0]:%d/%m/%Y} -> {stamps[-1]:%d/%m/%Y}" if stamps else "?")
             + f" · rieng co: {sorted(set(keys) - base) or '(nen chung)'}")
    thieu_cached = sum(len(v) for k, v in shapes.items() if "cached_tokens" not in k)
    note(NANG, "Truong VANG MAT khac han truong bang 0",
         f"Chi {len(base)} truong co o ca ba dinh dang. Rieng cached_tokens vang o "
         f"{thieu_cached:,}/{len(raw):,} dong - lay trung binh tren ca bang la sai "
         f"{len(raw) / (len(raw) - thieu_cached):.1f} lan.")


# ───────────────── 4. cac cho lech so hoc ─────────────────

def lech_so_hoc(raw: list[dict], year: dict) -> None:
    head("4. CAC CHO LECH SO HOC")
    off = [(r, num(r.get("total_tokens")) - num(r.get("prompt_tokens"))
            - num(r.get("completion_tokens"))) for r in raw]
    off = [(r, d) for r, d in off if abs(d) > 0.5]
    if off:
        sizes = Counter(round(d) for _, d in off)
        stamps = sorted(s for s in (when(r) for r, _ in off) if s)
        note(VUA, "total_tokens KHONG bang prompt + completion",
             f"{len(off)}/{len(raw)} dong, thieu {sum(round(d) for _, d in off)} token · "
             f"do lech: {dict(sizes)} · tu {stamps[0]:%d/%m} den {stamps[-1]:%d/%m}, sau do ngung")

    top = year.get("top_users") or []
    trung = Counter(str(u.get("user_id")) for u in top if u.get("user_id"))
    lap = {k: v for k, v in trung.items() if v > 1}
    if lap:
        note(VUA, "Bang top_users co dong TRUNG user_id",
             f"{lap} - cong lai se dem hai lan neu khong khu")

    note(NHE, "top_users chi la TOP-20, khong phai toan bo",
         f"{len(top)} dong / {len(read_json(CTDA / 'users-list.json'))} tai khoan. "
         f"Dung lam mau so la sai.")


# ───────────────── 5. mui gio ─────────────────

def mui_gio(raw: list[dict]) -> None:
    head("5. MUI GIO CHUA XAC NHAN")
    hours = Counter()
    for row in raw:
        stamp = when(row)
        if stamp:
            hours[stamp.hour] += 1
    total = sum(hours.values())
    lam_viec = sum(c for h, c in hours.items() if 8 <= h <= 18)
    neu_utc = sum(c for h, c in hours.items() if 1 <= h <= 11)
    peak = max(hours, key=lambda h: hours[h])
    note(VUA, "Khong ro timestamp la UTC hay gio Viet Nam",
         f"gio ban nhat {peak:02d}h · doc nguyen: {ty_le(lam_viec, total)} trong 8-18h · "
         f"coi la UTC: {ty_le(neu_utc, total)} trong 8-18h ICT")

    stamps = sorted(s for s in (when(r) for r in raw) if s)
    ngay = {s.date() for s in stamps}
    khoang = (stamps[-1].date() - stamps[0].date()).days + 1
    note(TIN, "Do phu theo ngay",
         f"{len(ngay)}/{khoang} ngay co du lieu ({ty_le(len(ngay), khoang)}) · "
         f"{stamps[0]:%d/%m/%Y} -> {stamps[-1]:%d/%m/%Y}")

    trong = []
    moc = stamps[0].date()
    while moc <= stamps[-1].date():
        if moc not in ngay:
            trong.append(moc)
        moc += timedelta(days=1)
    if trong:
        dai = []
        run = [trong[0]]
        for day in trong[1:]:
            if (day - run[-1]).days == 1:
                run.append(day)
            else:
                dai.append(run)
                run = [day]
        dai.append(run)
        dai.sort(key=len, reverse=True)
        note(NHE, "Co nhung ngay khong mot luot goi nao",
             f"{len(trong)} ngay trong · doan dai nhat {len(dai[0])} ngay "
             f"({dai[0][0]:%d/%m} -> {dai[0][-1]:%d/%m})")


# ───────────────── 6. cac han che khac ─────────────────

def han_che_khac(raw: list[dict], year: dict) -> None:
    head("6. CAC HAN CHE KHAC")
    note(VUA, "Khong co truong LOI va DO TRE",
         "Bang tho co 16 truong, khong truong nao ve ma tra ve hay thoi gian phan hoi. "
         "Day la log NGHIEP VU, khong phai log KY THUAT.")

    models = Counter(str(r.get("model")) for r in raw)
    note(TIN, "Chi dung 2 model",
         ", ".join(f"{k}={v:,}" for k, v in models.most_common()))

    logs = read_json(CTDA / "logs-recent-365.json")
    rows = logs.get("data", {}).get("logs") or logs.get("logs") or []
    if rows:
        stamps = sorted(str(r.get("timestamp") or "") for r in rows if r.get("timestamp"))
        note(NHE, "Nhat ky su kien gan nhu vo dung cho lich su",
             f"xin 365 ngay, tra ve {len(rows)} dong, thuc te chi phu "
             f"{stamps[0][:16]} -> {stamps[-1][:16]}")

    note(VUA, "date_from / date_to BI BO QUA",
         "Da chung minh bang thuc nghiem: goi co tham so va khong tham so tra ve tong y het. "
         "=> khong the hoi lai qua khu, phai chup anh hang ngay.")

    funcs = Counter(str(r.get("function")) for r in raw)
    note(VUA, "Chua biet ham nao la NGUOI DUNG THAT, ham nao la MAY CHAY NEN",
         ", ".join(f"{k}={v:,}" for k, v in funcs.most_common()))

    actor = Counter(str(r.get("actor_type", "(thieu)")) for r in raw)
    note(NHE, "actor_type = 'system' chua biet la tac vu gi",
         ", ".join(f"{k}={v:,}" for k, v in actor.most_common()))


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    raw = read_json(CTDA / "db-token_usage-raw.json")
    year = read_json(CTDA / "token-usage-year.json")

    khong_doi_chung(raw, year)
    quy_ve_nguoi(raw, year)
    dinh_dang(raw)
    lech_so_hoc(raw, year)
    mui_gio(raw)
    han_che_khac(raw, year)

    head("TONG KET")
    muc = Counter(m for m, _, _ in _found)
    for level, label in ((NANG, "NANG  - anh huong ket luan"),
                         (VUA, "VUA   - phai xu ly khi nap"),
                         (NHE, "NHE   - can biet, khong chan"),
                         (TIN, "TIN   - so lieu tham khao")):
        print(f"  {label:<28} {muc.get(level, 0)}")
    print(f"\n  Tong: {len(_found)} muc")


if __name__ == "__main__":
    main()
