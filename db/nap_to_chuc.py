"""Nap dim_unit, dim_user, dim_function - buoc (2)(3)(4)(5) cua Ngay 2.

Chi doc file, khong goi mang.

THU TU BAT BUOC (xem docs/quyet-dinh-ngay-2-2026-08-09.md)
---------------------------------------------------------
    (2) dim_unit    108 Ralli + 20 TLA HD + 6 ky thuat + 2 'Chua quy duoc'
    (3) dim_user    890 + 42 + 6 ky thuat                   nguon_gap='danh ba'
    (4) quet nhat ky bo sung user_id khong co trong danh ba nguon_gap='nhat ky'
    (5) dim_function

Dao (3)(4) voi buoc nap fact_call thi fact_call se co khoa ngoai tro vao cho trong.

BA CAI BAY
----------
BOM      db-token_usage-raw.json co BOM UTF-8. Mo bang encoding='utf-8' se nem
         JSONDecodeError. Phai dung 'utf-8-sig'.
THU TU   dim_unit.parent_id tro vao chinh dim_unit. Voi PRAGMA foreign_keys=ON,
         nap con truoc cha se HONG. Phai nap theo `cap` tang dan.
THIEU    6/108 don vi Ralli KHONG co truong `ancestors`. Dung x['ancestors'] se
         nem KeyError. Duong dan tinh bang cach lan theo parent_id, roi DOI CHIEU
         voi `ancestors` o 102 don vi con lai - neu lech thi mot trong hai sai.

NGHIEM THU
----------
    dim_unit      136 = 108 + 20 + 6 + 2
    dim_user      938 + N dong sinh tu nhat ky
    dim_function    8 = 6 (Ralli) + 2 (TLA HD)
    moi user_id trong nhat ky Ralli deu co cho tro toi
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ket_noi  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CTDA = ROOT / "data" / "ctda"
TLA = ROOT / "data" / "tla-hd"

RALLI, TLA_HD = 8, 5
AGENT_MOT_USER = (1, 2, 3, 4, 6, 7)          # quyet dinh A1

# Nhan tieng Viet da biet, phat hien khi doi chieu giao dien web 07/08
NHAN_HAM = {"analyze": "Phân tích hợp đồng", "chat": "Hỏi đáp AI"}

DV_MONG_DOI = 136
HAM_MONG_DOI = 8


def doc_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def doc_csv(p: Path) -> list[dict]:
    with open(p, encoding="utf-8-sig") as h:
        return list(csv.DictReader(h))


def lan_len(nid: str, cha: dict[str, str], ten: dict[str, str]) -> list[str]:
    """Lan theo parent_id ve toi goc. Tra danh sach ten TU GOC xuong, chua ke chinh no."""
    duong: list[str] = []
    da_qua = {nid}
    hien = cha.get(nid) or None
    while hien:
        if hien in da_qua:                    # vong lap trong du lieu
            raise SystemExit(f"Cay don vi co vong lap tai {hien}")
        if hien not in ten:
            raise SystemExit(f"Don vi {nid} tro vao cha {hien} khong ton tai")
        da_qua.add(hien)
        duong.append(ten[hien])
        hien = cha.get(hien) or None
    return list(reversed(duong))


def gom_don_vi() -> list[tuple]:
    """Tra danh sach dong dim_unit cho ca Ralli lan TLA HD."""
    dong: list[tuple] = []

    # --- Ralli: 108 don vi, cau truc phang co parent_id ---
    ru = doc_json(CTDA / "units.json")["data"]
    ten = {x["id"]: x["name"] for x in ru}
    cha = {x["id"]: (x.get("parent_id") or "") for x in ru}

    lech_duong_dan = 0
    for x in ru:
        to_tien = lan_len(x["id"], cha, ten)
        # Doi chieu voi `ancestors` o nhung don vi co truong do
        anc = x.get("ancestors")
        if anc is not None:
            theo_anc = [ten[a] for a in anc if a in ten]
            if theo_anc != to_tien:
                lech_duong_dan += 1
        dong.append((x["id"], RALLI, x["name"], x.get("parent_id") or None,
                     len(to_tien) + 1, " > ".join(to_tien + [x["name"]]), False))
    if lech_duong_dan:
        raise SystemExit(
            f"parent_id va ancestors cho ra duong dan KHAC NHAU o {lech_duong_dan} don vi "
            f"- mot trong hai sai, phai lam ro truoc khi nap")

    # --- TLA HD: cay long nhau ---
    def duyet(nut: list, sau: int, to_tien: list[str]) -> None:
        for n in nut:
            dong.append((n["id"], TLA_HD, n["name"], n.get("parent_id") or None,
                         sau, " > ".join(to_tien + [n["name"]]), False))
            duyet(n.get("children") or [], sau + 1, to_tien + [n["name"]])

    duyet(doc_json(TLA / "units-tree.json")["tree"], 1, [])
    return dong


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=ket_noi.MAC_DINH)
    args = p.parse_args()

    cn, dc = ket_noi.mo(args.db)
    cur = cn.cursor()

    ten_agent = dict(cur.execute("SELECT agent_id, ten FROM dim_agent").fetchall())

    # ================================================== (2) dim_unit
    dong_dv = gom_don_vi()

    # 6 dong ky thuat + 2 dong 'Chua quy duoc'
    for aid in AGENT_MOT_USER:
        dong_dv.append((f"__ky_thuat_{aid}__", aid, f"Đơn vị sử dụng {ten_agent[aid]}",
                        None, 1, f"Đơn vị sử dụng {ten_agent[aid]}", True))
    for aid in (TLA_HD, RALLI):
        dong_dv.append((f"__chua_quy_duoc_{aid}__", aid, "Chưa quy được",
                        None, 0, "Chưa quy được", True))

    cur.execute("DELETE FROM fact_usage_daily")
    cur.execute("DELETE FROM fact_call")
    cur.execute("DELETE FROM dim_function")
    cur.execute("DELETE FROM dim_user")
    cur.execute("DELETE FROM dim_unit")

    # Nap theo `cap` tang dan: cha phai co truoc con, khong thi khoa ngoai hong
    dong_dv.sort(key=lambda r: r[4])
    cur.executemany(
        f"INSERT INTO dim_unit (unit_id, agent_id, ten, parent_id, cap, duong_dan,"
        f" la_dong_ky_thuat) VALUES ({','.join([dc] * 7)})", dong_dv)

    # ================================================== (3) dim_user tu danh ba
    dong_nd: list[tuple] = []
    co_dv = {r[0] for r in cur.execute("SELECT unit_id FROM dim_unit")}

    for x in doc_json(CTDA / "users-list.json"):
        dv = x.get("unit_id") or None
        if dv not in co_dv:                    # 2 nguoi khong co don vi
            dv = f"__chua_quy_duoc_{RALLI}__"
        dong_nd.append((x["id"], RALLI, x["username"], x.get("full_name"),
                        x.get("email"), dv, x.get("is_active"), None, False, "danh ba"))

    for r in doc_csv(TLA / "users-by-unit.csv"):
        dv = r["unit_id"] if r["unit_id"] in co_dv else f"__chua_quy_duoc_{TLA_HD}__"
        dong_nd.append((r["user_id"], TLA_HD, r["username"], r.get("full_name") or None,
                        r.get("email") or None, dv, None, None, False, "danh ba"))

    for aid in AGENT_MOT_USER:
        dong_nd.append((f"__ky_thuat_{aid}__", aid, f"Người dùng sử dụng {ten_agent[aid]}",
                        None, None, f"__ky_thuat_{aid}__", None, None, True, "ky thuat"))

    # ================================================== (4) bo sung tu nhat ky
    calls = doc_json(CTDA / "db-token_usage-raw.json")
    da_co = {(d[1], d[0]) for d in dong_nd}    # (agent_id, user_id)
    them: dict[str, str] = {}
    for c in calls:
        uid = c.get("user_id")
        if uid is None or (RALLI, uid) in da_co:
            continue
        # Chi dinh dang 3 moi co `username`. Lay ten that neu BAT KY ban ghi nao
        # cua user do co - khong duoc dung lai o ban ghi dau tien, vi ban ghi dau
        # rat co the la dinh dang 1 (khong co username) va ta se ghi nham uid.
        if c.get("username"):
            them[uid] = c["username"]
        else:
            them.setdefault(uid, uid)
    # Trong ban ghi cu, truong `user_id` chua USERNAME chu khong phai ObjectId.
    # 13/17 'nguoi la' that ra co trong danh ba, chi khac dang khoa. Gan dung don
    # vi cho ho - VAN GIU RIENG hai dong theo quyet dinh N7, chi dien them thuoc
    # tinh da biet chu khong gop danh tinh.
    # Kiem chung: 215 (khop ObjectId) + 49 (khop username) = 264, dung bang con so
    # app tu tinh doc lap (7.924 - 7.660).
    dv_theo_ten = {d[2]: d[5] for d in dong_nd if d[1] == RALLI and d[9] == "danh ba"}
    for uid, tenhien in them.items():
        dong_nd.append((uid, RALLI, tenhien, None, None,
                        dv_theo_ten.get(uid) or dv_theo_ten.get(tenhien)
                        or f"__chua_quy_duoc_{RALLI}__",
                        None, None, False, "nhat ky"))

    cur.executemany(
        f"INSERT INTO dim_user (user_id, agent_id, username, ho_ten, email, unit_id,"
        f" dang_hoat_dong, ngay_tao, la_dong_ky_thuat, nguon_gap)"
        f" VALUES ({','.join([dc] * 10)})", dong_nd)

    # ================================================== (5) dim_function
    dong_ham: list[tuple] = []
    for f in sorted({c.get("function") for c in calls if c.get("function")}):
        dong_ham.append((RALLI, f, NHAN_HAM.get(f), None))
    for r in doc_csv(TLA / "by-function-2026.csv"):
        dong_ham.append((TLA_HD, r["function"], NHAN_HAM.get(r["function"]), None))
    cur.executemany(
        f"INSERT INTO dim_function (agent_id, ma, nhan, la_nguoi_dung)"
        f" VALUES ({','.join([dc] * 4)})", dong_ham)

    # ================================================== nghiem thu
    n_dv = cur.execute("SELECT COUNT(*) FROM dim_unit").fetchone()[0]
    n_nd = cur.execute("SELECT COUNT(*) FROM dim_user").fetchone()[0]
    n_ky = cur.execute("SELECT COUNT(*) FROM dim_user WHERE la_dong_ky_thuat").fetchone()[0]
    n_ham = cur.execute("SELECT COUNT(*) FROM dim_function").fetchone()[0]
    theo_nguon = dict(cur.execute("SELECT nguon_gap, COUNT(*) FROM dim_user"
                                  " GROUP BY nguon_gap").fetchall())

    print(f"  dim_unit     {n_dv:>4}  ({len(dong_dv) - 8} that + 6 ky thuat + 2 chua quy duoc)")
    print(f"  dim_user     {n_nd:>4}  {theo_nguon}")
    print(f"  dim_function {n_ham:>4}")

    # Moi user_id trong nhat ky PHAI co cho tro toi - neu khong, fact_call se hong
    co_nd = {r[0] for r in cur.execute("SELECT user_id FROM dim_user WHERE agent_id = ?",
                                       (RALLI,))}
    mo_coi = {c.get("user_id") for c in calls} - co_nd - {None}

    loi = []
    if n_dv != DV_MONG_DOI:
        loi.append(f"dim_unit {n_dv} != {DV_MONG_DOI}")
    if n_ky != len(AGENT_MOT_USER):
        loi.append(f"dong ky thuat {n_ky} != {len(AGENT_MOT_USER)}")
    if n_ham != HAM_MONG_DOI:
        loi.append(f"dim_function {n_ham} != {HAM_MONG_DOI}")
    if mo_coi:
        loi.append(f"{len(mo_coi)} user_id trong nhat ky khong co trong dim_user: "
                   f"{sorted(mo_coi)[:3]}")
    if loi:
        cn.rollback()
        raise SystemExit("NGHIEM THU KHONG DAT - da huy, khong ghi gi:\n  "
                         + "\n  ".join(loi))
    cn.commit()
    print("  NGHIEM THU DAT")


if __name__ == "__main__":
    main()
