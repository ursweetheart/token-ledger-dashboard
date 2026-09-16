"""Doi chieu cay don vi GO CUNG trong app.js voi cay dung tu database.

    python tools/diagnostics/reconcile_org_tree.py

VI SAO CAN CONG CU NAY
----------------------
Truoc khi bo ORG_UNITS (108 don vi go cung trong web/js/app.js) phai biet cay
dung tu dim_unit co ra dung cay do khong. Chenh 22 dong khong noi duoc gi cho
toi khi biet chung nam o dau, va co BA kieu lech - kieu thu ba nguy hiem nhat:

    chi co trong database        -> thay xong MOC THEM hang, nhin la biet
    chi co trong ORG_UNITS       -> thay xong MAT hang, nhin la biet
    co ca hai nhung KHAC CHA     -> khong moc khong mat, chi CONG SANG NHANH
                                    KHAC. Tong toan cong ty van dung; so cua
                                    tung phong ban doi ma khong ai bao.

CAY GOP LA GI
-------------
dim_unit chua HAI cay: Tro ly ao Ralli 102 don vi mot goc, Tro Ly Ao Hop Dong
20 don vi BON goc. Cot canonical_unit_id (them 20/08/2026) noi 4 cap trung nhau.
Cong cu nay ap phep gop do roi moi so sanh - dung nhu frontend se lam.

CHI DOC. Khong ghi gi vao database lan vao ma nguon.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = "http://127.0.0.1:8000"


def doc_org_units() -> dict[str, dict]:
    """Rut mang ORG_UNITS tu app.js. Tra {id: {name, parent, level}}."""
    src = (ROOT / "web" / "js" / "app.js").read_text(encoding="utf-8")
    i = src.index("var ORG_UNITS")
    # Dem ngoac de tim cuoi mang, khong dung regex tham lam
    depth, j = 0, i
    for j in range(i, len(src)):
        if src[j] == "[":
            depth += 1
        elif src[j] == "]":
            depth -= 1
            if depth == 0:
                break
    out = {}
    for m in re.finditer(
            r'\{id:"([^"]+)",name:"([^"]+)",parent:(null|"[^"]*"),level:(\d+)',
            src[i:j]):
        uid, name, parent, level = m.groups()
        out[uid] = {"name": name,
                    "parent": None if parent == "null" else parent.strip('"'),
                    "level": int(level)}
    return out


def doc_dim_unit() -> list[dict]:
    with urllib.request.urlopen(BASE + "/api/catalog") as r:
        return json.load(r)["units"]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    org = doc_org_units()
    try:
        db = doc_dim_unit()
    except Exception as e:
        raise SystemExit(f"Khong goi duoc {BASE}: {e}\n"
                         f"  Mo may chu truoc:"
                         f"  python -m uvicorn backend.main:app --port 8000")

    print(f"ORG_UNITS go cung : {len(org)} don vi")
    print(f"dim_unit          : {len(db)} dong"
          f" ({sum(1 for x in db if not x['is_technical'])} that,"
          f" {sum(1 for x in db if x['is_technical'])} ky thuat)")

    # --- ap phep gop, dung nhu frontend se lam ---
    by_id = {x["unit_id"]: x for x in db}

    def chuan(uid: str) -> str:
        """Theo canonical_unit_id ve ban chuan. Co chan vong lap."""
        seen = set()
        while uid and by_id.get(uid, {}).get("canonical_unit_id"):
            if uid in seen:
                raise SystemExit(f"canonical_unit_id tao VONG LAP tai {uid}")
            seen.add(uid)
            uid = by_id[uid]["canonical_unit_id"]
        return uid

    that = [x for x in db if not x["is_technical"]]
    gop = {}
    for x in that:
        cid = chuan(x["unit_id"])
        if cid == x["unit_id"]:
            gop[cid] = x
    n_trung = len(that) - len(gop)
    print(f"cay GOP tu database: {len(gop)} don vi"
          f" (da gop {n_trung} ban trung qua canonical_unit_id)")
    print()

    # --- so sanh theo TEN, vi hai ben khong co khoa chung ---
    ten_org = {v["name"].strip(): k for k, v in org.items()}
    ten_db = {v["name"].strip(): k for k, v in gop.items()}

    chi_db = sorted(set(ten_db) - set(ten_org))
    chi_org = sorted(set(ten_org) - set(ten_db))
    chung = sorted(set(ten_db) & set(ten_org))

    # KHAC NHAU CHI O DAU - tach thanh nhom rieng, KHONG gop im lang.
    # 'TTDL&DHS' (database) va 'TTDL&ĐHS' (ORG_UNITS) la mot phong, khac dung mot
    # chu D. Bao chung nhu hai don vi khac nhau la keu nham; nhung tu dong coi la
    # mot cung sai - hai phong ban that su co the chi khac nhau o dau. Neu ra rieng
    # de nguoi doc quyet.
    def bo_dau(s: str) -> str:
        b = "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
        a = "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd"
        return "".join(a[b.index(c)] if c in b else c for c in s.lower())

    khong_dau_db = {}
    for t in chi_db:
        khong_dau_db.setdefault(bo_dau(t), []).append(t)
    gan_giong = []
    for t in list(chi_org):
        k = bo_dau(t)
        if k in khong_dau_db:
            gan_giong.append((khong_dau_db[k][0], t))
            chi_db = [x for x in chi_db if x != khong_dau_db[k][0]]
            chi_org = [x for x in chi_org if x != t]

    def cha_org(uid: str) -> str | None:
        p = org[uid]["parent"]
        return org[p]["name"].strip() if p and p in org else None

    def cha_db(uid: str) -> str | None:
        p = gop[uid].get("parent_id")
        if not p:
            return None
        p = chuan(p)
        return by_id[p]["name"].strip() if p in by_id else None

    khac_cha = []
    for ten in chung:
        a, b = cha_org(ten_org[ten]), cha_db(ten_db[ten])
        if (a or "") != (b or ""):
            khac_cha.append((ten, a, b))

    print(f"[1] Chi co trong DATABASE  : {len(chi_db)}"
          f"   -> thay xong se MOC THEM hang")
    for t in chi_db[:15]:
        print(f"      {t}")
    if len(chi_db) > 15:
        print(f"      ... con {len(chi_db) - 15}")
    print()
    print(f"[2] Chi co trong ORG_UNITS : {len(chi_org)}"
          f"   -> thay xong se MAT hang")
    for t in chi_org[:15]:
        print(f"      {t}")
    if len(chi_org) > 15:
        print(f"      ... con {len(chi_org) - 15}")
    print()
    print(f"[3] Co ca hai nhung KHAC CHA: {len(khac_cha)}"
          f"   -> so CHAY SANG NHANH KHAC, khong ai thay")
    for ten, a, b in khac_cha[:20]:
        print(f"      {ten:30} ORG_UNITS: {a!s:24} database: {b!s}")
    if len(khac_cha) > 20:
        print(f"      ... con {len(khac_cha) - 20}")
    print()
    print(f"[4] Khac nhau CHI O DAU     : {len(gan_giong)}"
          f"   -> gan chac la mot phong, nguoi doc quyet")
    for a, b in gan_giong:
        print(f"      database: {a:22} ORG_UNITS: {b}")
    print()
    print(f"    Trung ten VA trung cha: {len(chung) - len(khac_cha)}/{len(chung)}")

    if khac_cha:
        print()
        print("  Nhom [3] phai lam ro TUNG DONG truoc khi bo ORG_UNITS.")
    sys.exit(1 if (chi_db or chi_org or khac_cha) else 0)


if __name__ == "__main__":
    main()
