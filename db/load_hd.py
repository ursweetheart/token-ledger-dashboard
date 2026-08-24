"""Nap so lieu su dung TLA Hop Dong vao fact_app_daily. Chi doc file.

Nguon: data/raw_web/tla-hd/<ngay>/usage-day-user-model.json
       do scripts/pull_hd_usage.py sinh ra.

VI SAO KHONG VAO fact_call
--------------------------
fact_call la TUNG LUOT GOI. Du lieu cua TLA HD la so DA TONG HOP theo
(ngay x nguoi x model) - app khong phoi log tho. Nhet no vao fact_call thi phai
bia ra 2.834 luot gia voi moc thoi gian gia. Bang rieng noi dung su that: day la
so da gop san, va gop den muc nao.

QUY TAC AP DUNG
---------------
Quy tac 5  Truong thieu nap NULL, KHONG nap 0.
Quy tac 6  Dung `total_tokens` cua API, khong tu cong prompt + completion.

BA CACH MAP, THEO THU TU
------------------------
1. user_id (UUID cua app) -> dim_user.user_id       <- duong chinh
2. username                -> account.username       <- cho ban ghi khong co UUID
3. khong khop              -> tai khoan 'unattributed' cua agent, VA DEM LAI

Buoc 3 khong duoc im lang. Neu no lon dan qua thoi gian nghia la danh ba va so
lieu su dung dang troi ra xa nhau, va do la thu can biet som.

TEN MODEL KHONG UNG VOI MODEL NAO
---------------------------------
API tra ve 'none' cho vai luot khong ghi duoc model (2 luot, 0 token - trung voi
`legacy_calls: 2` trong khoi costs). Day KHONG phai model. No nam trong
KHONG_PHAI_MODEL duoi day, tuc bo mot cach CO GHI CHEP: so luot bi bo duoc in ra
moi lan chay. Ten la khong nam trong danh sach do thi khau nap DUNG HAN - dung
tinh than cua dim_model_alias, hong on ao chu khong tra ve rong.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import connect  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TLA_HD = 5
SRC_FILE = "usage-day-user-model.json"

# Ten API tra ve nhung KHONG phai model. Bo, nhung bo co ghi chep.
NOT_A_MODEL = {
    "none": "app khong ghi duoc model cho luot goi nay (trung legacy_calls)",
}

COLUMNS = ["row_id", "day", "agent_id", "account_id", "model_id", "raw_model",
           "calls", "total_tokens", "prompt_tokens", "completion_tokens"]


def _latest(parent: Path, filename: str) -> Path:
    """Dot keo moi nhat CO file can. Xem ghi chu cung ten trong load_org.py."""
    remaining = sorted((p for p in parent.glob("*") if p.is_dir()), reverse=True)
    for p in remaining:
        if (p / filename).exists():
            return p
    raise SystemExit(
        f"Khong dot nao trong {parent} co {filename}."
        f" Chay scripts/pull_hd_usage.py truoc.")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=connect.DEFAULT_DSN)
    args = p.parse_args()

    folder = _latest(ROOT / "data" / "raw_web" / "tla-hd", SRC_FILE)
    payload = json.loads((folder / SRC_FILE).read_text(encoding="utf-8"))
    rows = payload["rows"]
    print(f"  Nguon: {folder.name}/{SRC_FILE}"
          f" ({payload['tu_ngay']} -> {payload['den_ngay']}, keo luc {payload['keo_luc']})")

    cn, ph = connect.open_db(args.db)
    cn.cursor().execute("DELETE FROM fact_app_daily")

    # ── ba bang tra cuu ───────────────────────────────────────────────
    by_uid = dict(connect.query(
        cn, f"SELECT user_id, account_id FROM dim_user WHERE agent_id = {ph}",
        (TLA_HD,)))
    by_name = {(u or "").strip().lower(): a for u, a in connect.query(
        cn, "SELECT username, account_id FROM account")}
    model_of = dict(connect.query(
        cn, "SELECT raw_name, model_id FROM dim_model_alias WHERE source = 'app'"))
    unmapped = connect.query_one(
        cn, f"SELECT account_id FROM account WHERE username = {ph}",
        (f"__unattributed_{TLA_HD}__",))[0]

    # ── kiem TEN MODEL truoc khi nap dong nao ────────────────────────
    # `model` = None nghia la app khong noi model - da biet va chap nhan duoc,
    # khac han voi mot TEN LA chua ai thay bao gio. Chi ten la moi dung khau nap.
    unknown_models = sorted({r["model"] for r in rows
                 if r.get("model")
                 and r["model"] not in model_of
                 and r["model"] not in NOT_A_MODEL})
    if unknown_models:
        raise SystemExit(
            f"Ten model la, chua co trong dim_model_alias (source='app'): {unknown_models}\n"
            f"  Them vao db/gen_catalog.py neu day la model that,\n"
            f"  hoac them vao KHONG_PHAI_MODEL trong file nay neu khong phai.")

    # ── dung dong ────────────────────────────────────────────────────
    # Sap xep TRUOC roi danh so: row_id phai giong nhau giua SQLite va Postgres,
    # nen khong duoc phu thuoc thu tu doc file.
    rows = sorted(rows, key=lambda r: (r["day"], (r.get("username") or "").lower(),
                                       r.get("model") or ""))
    out_rows, unmappable, skipped = [], {}, {}
    for i, r in enumerate(rows, start=1):
        name = (r.get("username") or "").strip()
        acc = by_uid.get(r.get("user_id")) or by_name.get(name.lower())
        if acc is None:
            acc = unmapped
            unmappable[name or "(khong ten)"] = \
                unmappable.get(name or "(khong ten)", 0) + (r["calls"] or 0)

        raw = r.get("model")
        if raw in NOT_A_MODEL:
            skipped[raw] = skipped.get(raw, 0) + (r["calls"] or 0)
            mid = None
        else:
            mid = model_of.get(raw)          # None khi app khong noi model

        out_rows.append((i, r["day"], TLA_HD, acc, mid, raw, r["calls"],
                   r["total_tokens"], r.get("prompt_tokens"),
                   r.get("completion_tokens")))

    n = connect.insert_many(cn, ph, "fact_app_daily", COLUMNS, out_rows)

    # ── NGHIEM THU ───────────────────────────────────────────────────
    # Doi chieu voi CHINH FILE NGUON o moi lan chay, khong ghim so cung.
    errors = []
    want_calls = sum(r["calls"] or 0 for r in rows)
    want_tokens = sum(r["total_tokens"] or 0 for r in rows)
    actual = connect.query_one(cn, "SELECT COUNT(*), SUM(calls), SUM(total_tokens)"
                               " FROM fact_app_daily")
    if actual[0] != len(rows):
        errors.append(f"nap {actual[0]} dong != {len(rows)} dong trong file")
    if int(actual[1] or 0) != want_calls:
        errors.append(f"luot {actual[1]} != {want_calls} trong file")
    if int(actual[2] or 0) != want_tokens:
        errors.append(f"token {actual[2]} != {want_tokens} trong file")
    if want_calls != payload["tong_luot"]:
        errors.append(f"file tu mau thuan: cong dong ra {want_calls}"
                   f" != tong_luot {payload['tong_luot']}")

    # Khoa tu nhien phai duy nhat, du khoa chinh la so thu tu. Trung o day nghia
    # la mot nguoi co hai dong cung ngay cung model - tuc da gop hut o khau keo.
    dupes = connect.query_one(cn, """
        SELECT COUNT(*) FROM (
            SELECT day, account_id, raw_model, COUNT(*) AS n
            FROM fact_app_daily GROUP BY day, account_id, raw_model
            HAVING COUNT(*) > 1) t""")[0]
    if dupes:
        errors.append(f"{dupes} bo (ngay, tai khoan, model) bi trung - keo hut")

    print(f"  fact_app_daily: {n} dong, {int(actual[1] or 0):,} luot,"
          f" {int(actual[2] or 0):,} token")
    if skipped:
        for name, calls in sorted(skipped.items()):
            print(f"  BO ({calls} luot): model {name!r} - {NOT_A_MODEL[name]}")
    missing_model = connect.query_one(
        cn, "SELECT COUNT(*), SUM(calls) FROM fact_app_daily WHERE model_id IS NULL")
    if missing_model[0]:
        print(f"  {missing_model[0]} dong khong co model_id"
              f" ({int(missing_model[1] or 0)} luot) - khong vao fact_usage_daily")
    if unmappable:
        total = sum(unmappable.values())
        print(f"  {len(unmappable)} nguoi khong quy duoc ve tai khoan"
              f" ({total} luot): {sorted(unmappable)}")

    if errors:
        cn.rollback()
        raise SystemExit("NGHIEM THU KHONG DAT - da huy:\n  " + "\n  ".join(errors))
    cn.commit()
    print("  NGHIEM THU DAT")


if __name__ == "__main__":
    main()
