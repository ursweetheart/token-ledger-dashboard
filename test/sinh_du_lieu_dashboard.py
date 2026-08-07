"""Turn the collected data into the exact shape app.js already expects.

Only data is produced. Nothing here changes how the dashboard computes anything:
the output is a drop-in replacement for the SEED_DAYS literal and for the two
price-table entries that are demonstrably wrong.

The row shape app.js uses, unchanged:

    {a: agent, d: don vi, m: model, ug: nhom, u: so user,
     c: so cuoc chat, ti: token vao, to: token ra, r: luot goi,
     er: ty le loi, lat: do tre p95, cached: token cached, think: thinking}

Where each field comes from, and why:

    ti / to / cached   billing      the only source anyone was actually charged for
    r / er / lat       monitoring   the only source that has these three at all
    Ralli everything   bang tho     Ralli never went through GCP, so its own table
                                    is the only source that exists
    u                  snapshot     provisioned head-count, placed on ONE day only,
                                    exactly as the current seed does, so that a
                                    multi-week range does not add it up repeatedly

Read only with respect to data/. Writes one .js file under test/.
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
OUT = Path(__file__).parent / "seed-days-that.js"

GEMINI = "generativelanguage.googleapis.com"
ASK = ("GenerativeService.GenerateContent", "GenerativeService.StreamGenerateContent")

# project -> (ten agent tren dashboard, don vi mac dinh, nhom)
# Ten don vi giu nguyen ten dashboard dang dung, neu khong cay to chuc se vo hieu.
AGENT = {
    "ai-chatbot-contract":     ("Trợ Lý Ảo Hợp Đồng",          None,                 "Nhóm Kinh doanh"),
    "tranquil-post-471401-c1": ("Sale Agent",                  "Anh Em tiếp thị",    "Nhóm Kinh doanh"),
    "pro-tuner-454203-v3":     ("Chatbot Contact Center",      "Chăm sóc khách hàng", "Nhóm CSKH"),
    "crm-500509":              ("Phân Loại Dữ Liệu CRM",       "P.NCTT , TTDL&ĐHS",  "Nhóm Dữ liệu"),
    "feedback-dms-tiep-thi":   ("Phân Loại Phản Hồi Tiếp Thị", "P.NCTT , TTDL&ĐHS",  "Nhóm Dữ liệu"),
    "multimodal-invoice":      ("Multi modal AI Invoice",      "P.NCTT , TTDL&ĐHS",  "Nhóm Dữ liệu"),
    # Ten nay khop EXCLUDED_AGENTS trong app.js nen tu dong bi loai khoi bao cao.
    "tools-quizz":             ("Tools Quizzer",               "Quản trị hệ thống",  "Nhóm Nội bộ"),
}

RALLI = "Trợ lý ảo Ralli"

# Ten model tren dashboard. Cac ten chua co trong basePricing duoc bao cao rieng
# o cuoi de bo sung, chu khong tu doi ten cho khop.
MODEL = {
    "gemini-2.5-flash":      "Gemini 2.5 Flash",
    "gemini-2.5-pro":        "Gemini 2.5 Pro",
    "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
    "gemini-2.0-flash":      "Gemini 2.0 Flash",
    "gemini-3.0-flash":      "Gemini 3.0 Flash",
    "gemini-3.1-flash-lite": "Gemini 3.1 Flash Lite",
    "gemini-3.5-flash":      "Gemini 3.5 Flash",
    "gemini-3-pro":          "Gemini 3 Pro",
    "gemini-embedding":      "Gemini Embedding 001",
}


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


def as_date(text) -> date | None:
    try:
        return date.fromisoformat(str(text)[:10])
    except (ValueError, TypeError):
        return None


def sku_to_model(sku: str) -> str:
    """Billing SKU text -> dashboard model name.

    '2.5 pro' must be tested before 'pro' and 'cached input' before 'input',
    but here only the model half matters. Order is longest-first so that
    '3.1 flash lite' is not swallowed by '3 flash'.
    """
    low = sku.lower()
    for needle, key in (("2.5 flash lite", "gemini-2.5-flash-lite"),
                        ("2.5-flash-lite", "gemini-2.5-flash-lite"),
                        ("3.1 flash lite", "gemini-3.1-flash-lite"),
                        ("2.5 pro", "gemini-2.5-pro"),
                        ("3 pro", "gemini-3-pro"),
                        ("2.5 flash", "gemini-2.5-flash"),
                        ("2.0 flash", "gemini-2.0-flash"),
                        ("3.5 flash", "gemini-3.5-flash"),
                        ("3 flash", "gemini-3.0-flash"),
                        ("embed", "gemini-embedding")):
        if needle in low:
            return MODEL[key]
    return f"(chua ro) {sku[:40]}"


def sku_kind(sku: str) -> str:
    low = sku.lower()
    if "cached" in low:
        return "cached"
    if "output token" in low:
        return "to"
    if "input token" in low:
        return "ti"
    return "khac"


# ───────────────────────── gom tung nguon ─────────────────────────

def from_billing() -> dict:
    """(ngay, project, model) -> {ti, to, cached}"""
    out: dict = defaultdict(lambda: {"ti": 0.0, "to": 0.0, "cached": 0.0})
    for row in read_csv(DATA / "billing" / "billing_gop_tru_CTDA.csv"):
        day = as_date(row.get("date"))
        if not day:
            continue
        model = sku_to_model(str(row.get("sku")))
        kind = sku_kind(str(row.get("sku")))
        entry = out[(day, row.get("project"), model)]
        if kind == "cached":
            # Billing bills cached separately; the two other sources already
            # fold it into the input side, so it is added to ti AND kept apart.
            entry["cached"] += num(row.get("amount"))
            entry["ti"] += num(row.get("amount"))
        elif kind in ("ti", "to"):
            entry[kind] += num(row.get("amount"))
    return out


def from_monitoring() -> tuple[dict, dict]:
    """(ngay, project) -> {r, loi}   and   (ngay, project) -> p95 trung vi.

    Keyed by project WITHOUT model on purpose. `api_request_count` comes from
    the serviceruntime family, whose rows carry no `model` label at all -- the
    column is empty on every one of them. Keying by model here would send every
    request into a bucket named "" and the join against billing would match
    nothing, silently producing a dashboard with zero requests everywhere.
    """
    folder = DATA / "da_xu_ly" / "du_lieu_giam_sat"
    pulls = sorted(p for p in folder.glob("*") if p.is_dir()) if folder.exists() else []
    calls: dict = defaultdict(lambda: {"r": 0.0, "loi": 0.0,
                                       "e4": 0.0, "e5": 0.0, "e429": 0.0})
    lat: dict = defaultdict(lambda: {"p95": [], "p99": []})
    if not pulls:
        return calls, lat

    for path in sorted(pulls[-1].glob("*.csv")):
        if path.name == "_tat-ca.csv":
            continue
        for row in read_csv(path):
            alias = row.get("metric_alias", "")
            if row.get("res_service") != GEMINI:
                continue
            day = as_date(row.get("ts_ict"))
            if not day:
                continue
            project = row.get("gcp_project_id")

            if alias == "api_request_count":
                if not any(m in (row.get("res_method") or "") for m in ASK):
                    continue
                entry = calls[(day, project)]
                gia_tri = num(row.get("value"))
                entry["r"] += gia_tri
                code = str(row.get("response_code", ""))
                # 429 tested before the generic 4xx branch: it IS a 4xx but the
                # dashboard reports it separately, and 499 is the user hanging
                # up rather than anything the system got wrong.
                if code == "429":
                    entry["e429"] += gia_tri
                    entry["loi"] += gia_tri
                elif code == "499":
                    pass
                elif code.startswith("4"):
                    entry["e4"] += gia_tri
                    entry["loi"] += gia_tri
                elif code.startswith("5"):
                    entry["e5"] += gia_tri
                    entry["loi"] += gia_tri
            elif alias == "api_request_latencies_p95":
                lat[(day, project)]["p95"].append(num(row.get("value")))
            elif alias == "api_request_latencies_p99":
                lat[(day, project)]["p99"].append(num(row.get("value")))
    return calls, lat


def trung_vi(values: list[float]) -> float:
    """Median, not max.

    A p95 sample can reach 154 seconds while the hourly average sits near 1.5.
    Taking the day's maximum would make one stalled call define the whole day.
    """
    if not values:
        return 0.0
    ordered = sorted(values)
    giua = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[giua]
    return (ordered[giua - 1] + ordered[giua]) / 2


def from_ralli() -> dict:
    """(ngay, don vi, model) -> {ti, to, cached, r}

    Ralli has no invoice, so its own raw table is the only source. Unit comes
    from the user's department, resolved through users-list.
    """
    raw = read_json(DATA / "ctda" / "db-token_usage-raw.json")
    users = read_json(DATA / "ctda" / "users-list.json")
    units = {u["id"]: u for u in read_json(DATA / "ctda" / "units.json")["data"]}
    by_user = {u["id"]: u for u in users}

    out: dict = defaultdict(lambda: {"ti": 0.0, "to": 0.0, "cached": 0.0, "r": 0.0})
    for row in raw:
        day = as_date(row.get("timestamp"))
        if not day:
            continue
        user = by_user.get(row.get("user_id"))
        unit = units.get(user.get("unit_id")) if user else None
        ten_unit = unit["name"] if unit else "Chưa xác định"
        model = MODEL.get(row.get("model") or "", str(row.get("model")))
        entry = out[(day, ten_unit, model)]
        entry["ti"] += num(row.get("prompt_tokens"))
        entry["to"] += num(row.get("completion_tokens"))
        entry["cached"] += num(row.get("cached_tokens"))
        entry["r"] += 1
    return out


def tla_unit_share() -> list[tuple[str, float]]:
    """(ten don vi, ty trong) cua TLA HD, lay tu by_unit ca nam.

    Billing gives TLA HD a daily total but no department; the app gives a
    department split but no day. Crossing them needs a proportion, and this is
    the only proportion that exists. Flagged in the generated file so nobody
    later mistakes it for a measurement.
    """
    year = read_json(DATA / "tla-hd" / "token-usage-year.json")
    rows = [(str(u.get("unit_name") or "Chưa xác định"), num(u.get("total_tokens")))
            for u in year["by_unit"]]
    tong = sum(t for _, t in rows)
    return [(ten, t / tong) for ten, t in rows if tong and t > 0]


# ───────────────────────── dung SEED_DAYS ─────────────────────────

def build() -> tuple[dict, list[str]]:
    bill = from_billing()
    calls, lat = from_monitoring()
    ralli = from_ralli()
    shares = tla_unit_share()

    days: dict[str, list[dict]] = defaultdict(list)
    thieu_gia: set[str] = set()

    def add(day: date, agent: str, dept: str, model: str, group: str,
            ti: float, to: float, cached: float, r: float, latency: float,
            users: int = 0, e4: float = 0.0, e5: float = 0.0, e429: float = 0.0,
            e_known: float = 0.0, lat99: float = 0.0) -> None:
        if not (ti or to or r or users):
            return
        if model.startswith("(chua ro)"):
            thieu_gia.add(model)
        # er is DERIVED from the three counts rather than passed in separately.
        # Two independent numbers that must agree will eventually stop agreeing;
        # one number computed from the other cannot.
        er = ((e4 + e5 + e429) / r * 100) if r else 0.0
        days[day.isoformat()].append({
            "a": agent, "d": dept, "m": model, "ug": group,
            "u": users, "c": 0,
            "ti": int(round(ti)), "to": int(round(to)),
            "r": int(round(r)), "er": round(er, 4),
            "lat": round(latency, 2), "cached": int(round(cached)), "think": 0,
            # Số LƯỢT theo nhóm mã, không phải tỷ lệ — cộng được ở mọi mức gộp.
            "e4": int(round(e4)), "e5": int(round(e5)), "e429": int(round(e429)),
            # Số lượt mà ta thực sự biết mã trả về. Ralli = 0 vì không qua GCP.
            "eKnown": int(round(e_known)), "lat99": round(lat99, 2),
        })

    # --- 7 project co billing ---
    #
    # Requests are known per (ngay, project) but tokens per (ngay, project, model).
    # The request count is therefore split across that day's models in proportion
    # to their tokens. Stated here rather than hidden: it is an apportionment,
    # and without it every request would have to be dumped on one arbitrary model.
    tokens_per_day: dict = defaultdict(float)
    for (day, project, _model), tok in bill.items():
        tokens_per_day[(day, project)] += tok["ti"] + tok["to"]

    rong = {"r": 0.0, "loi": 0.0, "e4": 0.0, "e5": 0.0, "e429": 0.0}
    for (day, project, model), tok in sorted(bill.items(), key=lambda kv: str(kv[0])):
        if project not in AGENT:
            continue
        agent, dept, group = AGENT[project]
        got = calls.get((day, project), rong)
        do_tre = lat.get((day, project)) or {"p95": [], "p99": []}
        p95, p99 = trung_vi(do_tre["p95"]), trung_vi(do_tre["p99"])

        tong_ngay = tokens_per_day.get((day, project), 0.0)
        phan_model = ((tok["ti"] + tok["to"]) / tong_ngay) if tong_ngay else 0.0

        def dem(he_so: float) -> dict:
            """Every count scales by the same factor, so er stays consistent."""
            return {"r": got["r"] * he_so, "e4": got["e4"] * he_so,
                    "e5": got["e5"] * he_so, "e429": got["e429"] * he_so,
                    "e_known": got["r"] * he_so}

        if dept is None:                      # TLA HD: chia theo ty trong nam
            for ten_unit, phan in shares:
                so = dem(phan_model * phan)
                add(day, agent, ten_unit, model, group,
                    tok["ti"] * phan, tok["to"] * phan, tok["cached"] * phan,
                    so["r"], p95, 0, so["e4"], so["e5"], so["e429"],
                    so["e_known"], p99)
        else:
            so = dem(phan_model)
            add(day, agent, dept, model, group,
                tok["ti"], tok["to"], tok["cached"], so["r"], p95, 0,
                so["e4"], so["e5"], so["e429"], so["e_known"], p99)

    # --- ngay CO request nhung KHONG phat sinh tien ---
    #
    # 25 cap (ngay, project) roi vao truong hop nay: Google do duoc luot goi
    # nhung hoa don khong co dong nao (mien phi, hoac lam tron ve 0). Bo qua
    # chung se mat 7.528 luot goi - gan 19% tong so. Model lay theo model dung
    # nhieu nhat cua project do, vi api_request_count khong mang nhan model.
    model_chinh: dict = defaultdict(lambda: defaultdict(float))
    for (day, project, model), tok in bill.items():
        model_chinh[project][model] += tok["ti"] + tok["to"]

    co_billing = {(day, project) for (day, project, _m) in bill}
    for (day, project), got in sorted(calls.items(), key=lambda kv: str(kv[0])):
        if project not in AGENT or (day, project) in co_billing or not got["r"]:
            continue
        agent, dept, group = AGENT[project]
        theo_model = model_chinh.get(project) or {}
        model = max(theo_model, key=theo_model.get) if theo_model else "Gemini 2.5 Flash"
        do_tre = lat.get((day, project)) or {"p95": [], "p99": []}
        p95, p99 = trung_vi(do_tre["p95"]), trung_vi(do_tre["p99"])
        if dept is None:
            for ten_unit, phan in shares:
                add(day, agent, ten_unit, model, group, 0, 0, 0,
                    got["r"] * phan, p95, 0, got["e4"] * phan, got["e5"] * phan,
                    got["e429"] * phan, got["r"] * phan, p99)
        else:
            add(day, agent, dept, model, group, 0, 0, 0, got["r"], p95, 0,
                got["e4"], got["e5"], got["e429"], got["r"], p99)

    # --- Ralli: khong co billing, dung bang tho ---
    for (day, unit, model), tok in sorted(ralli.items(), key=lambda kv: str(kv[0])):
        # e_known = 0: Ralli khong di qua GCP nen khong co ma tra ve nao
        # de phan loai. Dat 0 chu KHONG dat bang so luot, de dashboard biet
        # la "chua ro" chu khong phai "khong co loi".
        add(day, RALLI, unit, model, "Nhóm Kinh doanh",
            tok["ti"], tok["to"], tok["cached"], tok["r"], latency=0.0)

    # --- so user duoc cap: snapshot, chi gan vao MOT ngay ---
    #
    # Placed on the LAST day with data, not the first. Head-count is a snapshot,
    # so it may only appear once or a multi-week range would add it up again and
    # again -- but putting it at the start means the "7 ngay" preset reports zero
    # accounts, which is the more visible wrong answer.
    moc = max(days) if days else "2026-01-01"
    users = read_json(DATA / "ctda" / "users-list.json")
    units = {u["id"]: u for u in read_json(DATA / "ctda" / "units.json")["data"]}
    dem: dict[str, int] = defaultdict(int)
    for user in users:
        unit = units.get(user.get("unit_id"))
        dem[unit["name"] if unit else "Chưa xác định"] += 1
    for ten_unit, so in sorted(dem.items()):
        add(date.fromisoformat(moc), RALLI, ten_unit, "Gemini 2.5 Flash Lite",
            "Nhóm Kinh doanh", 0, 0, 0, 0, latency=0.0, users=so)

    tla_users = read_csv(DATA / "tla-hd" / "users-by-unit.csv")
    dem2: dict[str, int] = defaultdict(int)
    for user in tla_users:
        dem2[str(user.get("unit_name") or "Chưa xác định")] += 1
    for ten_unit, so in sorted(dem2.items()):
        add(date.fromisoformat(moc), "Trợ Lý Ảo Hợp Đồng", ten_unit, "Gemini 2.5 Pro",
            "Nhóm Kinh doanh", 0, 0, 0, 0, latency=0.0, users=so)

    return days, sorted(thieu_gia)


def emit(days: dict, thieu_gia: list[str]) -> None:
    lines = [
        "/* ═══════════════════════════════════════════════════════════════════",
        "   SEED_DAYS — sinh tự động từ dữ liệu THẬT đã thu thập.",
        f"   Sinh bởi test/sinh_du_lieu_dashboard.py. KHÔNG sửa tay file này.",
        "",
        "   Nguồn từng cột:",
        "     ti / to / cached   Google Billing   (số tiền thật đã bị thu)",
        "     r / er / lat       Google Monitoring (lọc generativelanguage,",
        "                        chỉ GenerateContent + StreamGenerateContent)",
        "     Ralli toàn bộ      bảng thô token_usage — Ralli không qua GCP",
        "     u                  số tài khoản được cấp, gắn vào MỘT ngày duy nhất",
        "",
        "   ⚠ Đơn vị của Trợ Lý Ảo Hợp Đồng là SỐ PHÂN BỔ: billing cho tổng theo",
        "     ngày nhưng không có phòng ban, app cho phòng ban nhưng không có ngày.",
        "   ═══════════════════════════════════════════════════════════════════ */",
        "var SEED_DAYS = {",
    ]
    keys = sorted(days)
    for index, day in enumerate(keys):
        rows = days[day]
        lines.append(f'  "{day}": [')
        for position, row in enumerate(rows):
            body = ",".join(
                f'{k}:{json.dumps(v, ensure_ascii=False)}' for k, v in row.items())
            lines.append("    {" + body + "}" + ("," if position < len(rows) - 1 else ""))
        lines.append("  ]" + ("," if index < len(keys) - 1 else ""))
    lines.append("};")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    tong_r = sum(r["r"] for rows in days.values() for r in rows)
    tong_ti = sum(r["ti"] for rows in days.values() for r in rows)
    tong_to = sum(r["to"] for rows in days.values() for r in rows)
    print(f"  Ghi     : {OUT}")
    print(f"  So ngay : {len(keys)}   ({keys[0]} -> {keys[-1]})")
    print(f"  So dong : {sum(len(v) for v in days.values()):,}")
    print(f"  Token   : vao {tong_ti:,}  ra {tong_to:,}  = {tong_ti + tong_to:,}")
    print(f"  Luot goi: {tong_r:,}")
    if thieu_gia:
        print(f"  CHUA RO MODEL: {thieu_gia}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    days, thieu_gia = build()
    emit(days, thieu_gia)


if __name__ == "__main__":
    main()
