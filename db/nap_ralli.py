"""Nap nhat ky Ralli vao fact_call - buoc (6) cua Ngay 2. Chi doc file.

QUY TAC AP DUNG
---------------
Quy tac 5  Truong thieu nap NULL, KHONG nap 0. `cached_tokens` vang mat o
           6.871/7.924 dong (dinh dang 1). Nap 0 roi lay trung binh la sai 7,5 lan.
           CHU Y phan biet: dinh dang 2 va 3 CO truong nay va gia tri 0 la SO 0
           THAT. Chi dong nao KHONG CO truong moi thanh NULL.
Quy tac 6  Dung `total_tokens`, khong tu cong prompt + completion. Lech 162.

MUI GIO
-------
`timestamp` khong co nhan mui gio. Da chung minh la UTC (M2, docs/mui-gio-2026-08-08.md)
nen `mui_gio_da_xac_nhan = TRUE` va `thoi_diem_ict = thoi_diem_goc + 7h`.
Cot `thoi_diem_goc` van chep NGUYEN de sau nay con kiem lai duoc.

NGHIEM THU
----------
    SELECT COUNT(*), SUM(total_tokens) FROM fact_call;             -- 7924 | 44692501
    SELECT COUNT(*) FROM fact_call WHERE cached_tokens IS NULL;    -- 6871
    SELECT dinh_dang_ban_ghi, COUNT(*) FROM fact_call GROUP BY 1;  -- 1:6871 2:542 3:511
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ket_noi  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _ralli_moi_nhat() -> Path:
    """Dot keo Ralli moi nhat. Nguon cu data/ctda/ la ban cao tay 05/08."""
    cha = ROOT / "data" / "raw_web" / "ralli"
    con = sorted(p for p in cha.glob("*") if p.is_dir())
    if not con:
        raise SystemExit(f"Khong co dot keo nao trong {cha}."
                         f" Chay scripts/pull_web_apps.py truoc.")
    return con[-1]


RALLI_DIR = _ralli_moi_nhat()
NHAT_KY = RALLI_DIR / "db-token_usage-raw.json"
# Stats ca nam do CHINH APP tong hop - doc lap voi bang tho. Dung lam doi chung
# cho so luot khong quy duoc ve don vi.
STATS_NAM = RALLI_DIR / "token-usage-year.json"

RALLI = 8
DINH_DANG = {8: 1, 14: 2, 16: 3}          # so truong -> ma dinh dang

# KHONG ghim so mong doi nua (truoc: 7924 / 44.692.501 / 6871 / {1:6871,2:542,3:511}
# / 7660). Ca nam so deu dung cho dot du lieu 05/08 va lam script DUNG ngay khi
# co ban ghi moi - tuc chan dung viec chung phai bao ve. Nay:
#   - bon so dau  SUY TU CHINH BANG THO, bat duoc dong roi rot khi nap
#   - so cuoi     lay tu STATS_NAM, van la doi chung DOC LAP nhu y ban dau


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=ket_noi.MAC_DINH)
    args = p.parse_args()

    cn, dc = ket_noi.mo(args.db)
    cur = cn.cursor()

    tra_model = ket_noi.tra_model(cn)
    unit_cua = dict(ket_noi.truy(
        cn, f"SELECT user_id, unit_id FROM dim_user WHERE agent_id = {dc}", (RALLI,)))
    chua_quy = f"__chua_quy_duoc_{RALLI}__"

    calls = json.loads(NHAT_KY.read_text(encoding="utf-8-sig"))

    ban_ghi: list[tuple] = []
    thieu_model: collections.Counter = collections.Counter()
    la_dinh_dang: collections.Counter = collections.Counter()
    for c in calls:
        dd = DINH_DANG.get(len(c))
        if dd is None:
            la_dinh_dang[len(c)] += 1
            continue

        mid = tra_model.get(("app", c["model"]))
        if mid is None:
            thieu_model[c["model"]] += 1

        goc = datetime.fromisoformat(c["timestamp"])
        uid = c.get("user_id")

        ban_ghi.append((
            c["_id"], RALLI,
            goc.isoformat(sep=" "),
            True,
            (goc + timedelta(hours=7)).isoformat(sep=" "),
            uid,
            unit_cua.get(uid, chua_quy),
            mid,
            c.get("function"),
            c.get("prompt_tokens"),
            c.get("completion_tokens"),
            c["total_tokens"],
            # QUY TAC 5: vang mat -> NULL. Co mat va bang 0 -> giu nguyen 0.
            c["cached_tokens"] if "cached_tokens" in c else None,
            dd,
        ))

    if la_dinh_dang or thieu_model:
        raise SystemExit(
            "Du lieu co dang chua biet - dung han, khong nap:\n"
            f"  so truong la : {dict(la_dinh_dang)}\n"
            f"  model chua co: {dict(thieu_model)}")

    cur.execute("DELETE FROM fact_call")
    cur.executemany(
        f"INSERT INTO fact_call (call_id, agent_id, thoi_diem_goc, mui_gio_da_xac_nhan,"
        f" thoi_diem_ict, user_id, unit_id, model_id, ma_ham, prompt_tokens,"
        f" completion_tokens, total_tokens, cached_tokens, dinh_dang_ban_ghi)"
        f" VALUES ({','.join([dc] * 14)})", ban_ghi)

    n, tok = ket_noi.mot(cn, "SELECT COUNT(*), SUM(total_tokens) FROM fact_call")
    thieu = ket_noi.mot(cn, "SELECT COUNT(*) FROM fact_call"
                            " WHERE cached_tokens IS NULL")[0]
    theo_dd = dict(ket_noi.truy(cn, "SELECT dinh_dang_ban_ghi, COUNT(*) FROM fact_call"
                                    " GROUP BY 1 ORDER BY 1"))
    kh_ai = ket_noi.mot(cn, f"SELECT COUNT(*) FROM fact_call WHERE unit_id = {dc}",
                        (chua_quy,))[0]

    print(f"  {n} dong | {tok:,} token | dinh dang {theo_dd}")
    print(f"  cached_tokens NULL {thieu} | khong quy duoc ve don vi {kh_ai}")

    # ── so mong doi suy tu chinh bang tho ──
    dong_nguon = len(ban_ghi)
    token_nguon = sum(c["total_tokens"] for c in calls if DINH_DANG.get(len(c)))
    thieu_nguon = sum(1 for c in calls
                      if DINH_DANG.get(len(c)) and "cached_tokens" not in c)
    dd_nguon = collections.Counter(DINH_DANG[len(c)] for c in calls if DINH_DANG.get(len(c)))

    # ── so doi chung DOC LAP: app tu tong hop ra muc 'Khong xac dinh' ──
    # Ta phai ra dung con so do. Lech nghia la khau gan don vi sai - xem chu
    # thich o nap_to_chuc.py.
    kh_ai_app = None
    for u in json.loads(STATS_NAM.read_text(encoding="utf-8-sig")).get("by_unit", []):
        if str(u.get("unit_name", "")).strip().lower() in ("không xác định", "khong xac dinh"):
            kh_ai_app = u.get("calls")

    loi = []
    if n != dong_nguon:
        loi.append(f"so dong {n} != {dong_nguon} dong dung tu bang tho")
    if tok != token_nguon:
        loi.append(f"token {tok} != {token_nguon} trong bang tho")
    if thieu != thieu_nguon:
        loi.append(f"cached NULL {thieu} != {thieu_nguon} ban ghi thieu truong")
    if theo_dd != dict(dd_nguon):
        loi.append(f"dinh dang {theo_dd} != {dict(dd_nguon)} dem tu bang tho")
    if kh_ai_app is None:
        loi.append(f"khong tim thay muc 'Khong xac dinh' trong {STATS_NAM.name}"
                   f" - mat doi chung doc lap, khong nap mu")
    elif kh_ai != kh_ai_app:
        loi.append(f"khong quy duoc {kh_ai} != {kh_ai_app} (so app tu tinh doc lap)")
    if loi:
        cn.rollback()
        raise SystemExit("NGHIEM THU KHONG DAT - da huy:\n  " + "\n  ".join(loi))
    cn.commit()
    print("  NGHIEM THU DAT")


if __name__ == "__main__":
    main()
