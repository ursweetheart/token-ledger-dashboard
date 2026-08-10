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
NHAT_KY = ROOT / "data" / "ctda" / "db-token_usage-raw.json"

RALLI = 8
DONG_MONG_DOI = 7924
TOKEN_MONG_DOI = 44692501
THIEU_CACHED_MONG_DOI = 6871
DINH_DANG = {8: 1, 14: 2, 16: 3}          # so truong -> ma dinh dang


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=ket_noi.MAC_DINH)
    args = p.parse_args()

    cn, dc = ket_noi.mo(args.db)
    cur = cn.cursor()

    tra_model = ket_noi.tra_model(cn)
    unit_cua = dict(cur.execute(
        "SELECT user_id, unit_id FROM dim_user WHERE agent_id = ?", (RALLI,)).fetchall())
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

    n, tok = cur.execute("SELECT COUNT(*), SUM(total_tokens) FROM fact_call").fetchone()
    thieu = cur.execute("SELECT COUNT(*) FROM fact_call"
                        " WHERE cached_tokens IS NULL").fetchone()[0]
    theo_dd = dict(cur.execute("SELECT dinh_dang_ban_ghi, COUNT(*) FROM fact_call"
                               " GROUP BY 1 ORDER BY 1").fetchall())
    kh_ai = cur.execute("SELECT COUNT(*) FROM fact_call WHERE unit_id = ?",
                        (chua_quy,)).fetchone()[0]

    print(f"  {n} dong | {tok:,} token | dinh dang {theo_dd}")
    print(f"  cached_tokens NULL {thieu} | khong quy duoc ve don vi {kh_ai}")

    loi = []
    if n != DONG_MONG_DOI:
        loi.append(f"so dong {n} != {DONG_MONG_DOI}")
    if tok != TOKEN_MONG_DOI:
        loi.append(f"token {tok} != {TOKEN_MONG_DOI}")
    if thieu != THIEU_CACHED_MONG_DOI:
        loi.append(f"cached NULL {thieu} != {THIEU_CACHED_MONG_DOI}")
    if theo_dd != {1: 6871, 2: 542, 3: 511}:
        loi.append(f"dinh dang {theo_dd} != {{1: 6871, 2: 542, 3: 511}}")
    # So doc lap: app tu tong hop ra 'Khong xac dinh' = 7.660 luot. Ta phai ra dung
    # con so do. Lech nghia la khau gan don vi sai - xem chu thich o nap_to_chuc.py.
    if kh_ai != 7660:
        loi.append(f"khong quy duoc {kh_ai} != 7660 (so app tu tinh doc lap)")
    if loi:
        cn.rollback()
        raise SystemExit("NGHIEM THU KHONG DAT - da huy:\n  " + "\n  ".join(loi))
    cn.commit()
    print("  NGHIEM THU DAT")


if __name__ == "__main__":
    main()
