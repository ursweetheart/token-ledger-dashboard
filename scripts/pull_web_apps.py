"""Keo du lieu tu 2 web app noi bo - Ralli (CTDA) va TLA Hop Dong. CHI DOC.

AN TOAN
-------
Ca hai API deu phoi ra endpoint ghi/xoa that (POST /trigger-data-fetch,
POST /logs/cleanup, DELETE /users/{id}, POST /api/ctda/refresh-data...).
Script nay khoa cung DANH SACH TRANG duoi day va dung method="GET" tuong minh.
Khong co duong nao trong code goi ra mot phuong thuc khac.

TOKEN
-----
Doc tu bien moi truong, KHONG ghi ra dia, KHONG in ra man hinh. JWT cua hai app
song rat ngan (~6h va ~1 ngay) nen day la thao tac tay, chua tu dong hoa duoc.

DAU RA
------
Moi lan keo mot thu muc rieng theo ngay, giong pull_monitoring.py:
    data/raw_web/<app>/<YYYY-MM-DD>/
KHONG ghi de data/ctda/ va data/tla-hd/. Ban keo cu la bang chung doc lap - lan
truoc mat data/billing/billing_gop_tru_CTDA.csv vi ghi de, khong lap lai.

PHAN TRANG
----------
/api/database/collections/{ten}/data mac dinh limit=20. Dung no de lay ban ghi
tho se im lang chi tra ve 20/7.924 dong. Phai dung /export/{format}.
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THU_MUC_RA = ROOT / "data" / "raw_web"

# (ten file dau ra, duong dan GET, bat buoc, nang)
# "nang" = bo qua khi chay --lat-mong, de vong lap tu soat quay trong vai giay.
RALLI = [
    ("db-collections.json",          "/api/database/collections",                           True,  False),
    ("db-token_usage-schema.json",   "/api/database/collections/token_usage/schema",        True,  False),
    ("db-conversations-schema.json", "/api/database/collections/conversations/schema",      True,  False),
    ("token-usage-budget.json",      "/api/token-usage/budget",                             True,  False),
    ("token-usage-filter-options.json", "/api/token-usage/filter-options",                  True,  False),
    ("token-usage-day.json",         "/api/token-usage/stats?period=day",                   True,  False),
    ("token-usage-week.json",        "/api/token-usage/stats?period=week",                  True,  False),
    ("token-usage-month.json",       "/api/token-usage/stats?period=month",                 True,  False),
    ("token-usage-year.json",        "/api/token-usage/stats?period=year",                  True,  False),
    ("units.json",                   "/api/units",                                          True,  False),
    ("units-tree.json",              "/api/units/tree",                                     True,  False),
    ("rbac-roles.json",              "/api/rbac/roles",                                     True,  False),
    ("rbac-permissions.json",        "/api/rbac/permissions",                               False, False),
    ("users-list.json",              "/users/list",                                         True,  False),
    ("dashboard-stats.json",         "/api/dashboard/stats",                                False, False),
    ("status.json",                  "/api/status",                                         False, False),
    ("db-token_usage-raw.json",      "/api/database/collections/token_usage/export/json",   True,  True),
    ("logs-recent-365.json",         "/logs/recent?days_back=365&limit=100000",             True,  True),
]

TLA_HD = [
    ("permissions-me.json",          "/api/permissions/me",                                 True,  False),
    ("token-usage-filter-options.json", "/api/admin/token-usage/filter-options",            True,  False),
    ("token-usage-day.json",         "/api/admin/token-usage/stats?period=day",             True,  False),
    ("token-usage-week.json",        "/api/admin/token-usage/stats?period=week",            True,  False),
    ("token-usage-month.json",       "/api/admin/token-usage/stats?period=month",           True,  False),
    ("token-usage-year.json",        "/api/admin/token-usage/stats?period=year",            True,  False),
    ("units.json",                   "/api/units",                                          True,  False),
    ("units-tree.json",              "/api/units/tree",                                     True,  False),
    ("dashboard-stats-30d.json",     "/api/dashboard/stats?period=30d",                     True,  False),
    ("presence-online-count.json",   "/api/presence/online-count",                          False, False),
    # limit toi da la 100 - dat 200 bi tra 422. Do chinh server noi ra, khong doan.
    ("notifications.json",           "/api/notifications?limit=100",                        False, False),
    ("projects.json",                "/api/projects",                                       True,  True),
    ("history-sessions.json",        "/api/history/sessions",                               True,  True),
]

NGUON = {
    "ralli":  {"goc": "https://ralliai.rangdong.com.vn:9001",  "bien": "RALLI_JWT", "diem": RALLI},
    "tla-hd": {"goc": "https://chatbothd.rangdong.com.vn:10001", "bien": "HD_JWT",  "diem": TLA_HD},
}

# Kiem chung chi binh thuong. Trinh duyet mo duoc ca hai site khong canh bao nen
# chung chi hop le; tat xac thuc o day la tu lam yeu ket noi vo co.
CTX = ssl.create_default_context()


class LoiKeo(Exception):
    pass


def lay(goc: str, duong_dan: str, token: str, so_lan: int = 3) -> bytes:
    """GET mot duong dan. Thu lai khi loi mang, KHONG thu lai khi 4xx."""
    url = goc + duong_dan
    for lan in range(1, so_lan + 1):
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            method="GET",                 # tuong minh - khong bao gio thanh POST/PUT/DELETE
        )
        try:
            with urllib.request.urlopen(req, timeout=180, context=CTX) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            than = e.read(300).decode("utf-8", "replace")
            # 401/403 = token het han hoac thieu quyen; thu lai vo nghia.
            raise LoiKeo(f"HTTP {e.code} - {than}") from e
        except Exception as e:
            if lan == so_lan:
                raise LoiKeo(f"{type(e).__name__}: {e}") from e
            time.sleep(2 * lan)
    raise LoiKeo("khong toi day duoc")


def dem(doi_tuong: object) -> str:
    """Mo ta ngan gon noi dung, de nhin ra ngay khi mot endpoint tra ve rong."""
    if isinstance(doi_tuong, list):
        return f"list[{len(doi_tuong)}]"
    if isinstance(doi_tuong, dict):
        for khoa in ("data", "items", "users", "units", "collections", "tree", "sessions"):
            gt = doi_tuong.get(khoa)
            if isinstance(gt, list):
                return f"{khoa}[{len(gt)}]"
        return "{" + ",".join(list(doi_tuong)[:4]) + "}"
    return type(doi_tuong).__name__


def keo_mot_app(ten: str, thu_muc: Path, lat_mong: bool) -> list[dict]:
    cau_hinh = NGUON[ten]
    token = os.environ.get(cau_hinh["bien"], "")
    if not token:
        raise SystemExit(f"Thieu bien moi truong {cau_hinh['bien']} cho app {ten}")

    thu_muc.mkdir(parents=True, exist_ok=True)
    ket_qua: list[dict] = []

    for ten_file, duong_dan, bat_buoc, nang in cau_hinh["diem"]:
        if lat_mong and nang:
            ket_qua.append({"file": ten_file, "trang_thai": "BO QUA (lat mong)",
                            "bat_buoc": bat_buoc, "byte": 0, "noi_dung": "-"})
            continue
        try:
            than = lay(cau_hinh["goc"], duong_dan, token)
        except LoiKeo as e:
            ket_qua.append({"file": ten_file, "trang_thai": f"HONG: {e}",
                            "bat_buoc": bat_buoc, "byte": 0, "noi_dung": "-"})
            print(f"  {'X':<2} {ten_file:<34} {e}")
            continue

        try:
            doi_tuong = json.loads(than)
        except json.JSONDecodeError:
            # Tra ve HTML (thuong la trang SPA) nghia la duong dan khong ton tai
            # that su, du ma tra ve 200. Day la loi, khong duoc luu.
            ket_qua.append({"file": ten_file, "trang_thai": "HONG: khong phai JSON",
                            "bat_buoc": bat_buoc, "byte": len(than), "noi_dung": "-"})
            print(f"  {'X':<2} {ten_file:<34} tra ve khong phai JSON ({len(than):,} byte)")
            continue

        (thu_muc / ten_file).write_text(
            json.dumps(doi_tuong, ensure_ascii=False, indent=1), encoding="utf-8")
        mo_ta = dem(doi_tuong)
        ket_qua.append({"file": ten_file, "trang_thai": "OK", "bat_buoc": bat_buoc,
                        "byte": len(than), "noi_dung": mo_ta})
        print(f"  {'v':<2} {ten_file:<34} {len(than):>10,} byte  {mo_ta}")

    return ket_qua


def kiem_cheo_ralli(thu_muc: Path) -> list[str]:
    """So so ban ghi tho voi so ma chinh API tu khai trong /api/database/collections.

    Day la phep kiem quan trong nhat cua Ralli: neu /export im lang cat bot thi
    hai con so nay tach nhau. Khong co no thi mot ban keo thieu 90% van trong
    nhu mot ban keo thanh cong.
    """
    canh_bao: list[str] = []
    f_bo = thu_muc / "db-collections.json"
    f_tho = thu_muc / "db-token_usage-raw.json"
    if not (f_bo.exists() and f_tho.exists()):
        return ["khong du file de kiem cheo so ban ghi token_usage"]

    bo = json.loads(f_bo.read_text(encoding="utf-8"))
    khai = None
    for c in bo.get("collections", []):
        if c.get("name") == "token_usage":
            khai = c.get("count")
    tho = json.loads(f_tho.read_text(encoding="utf-8"))
    that = len(tho) if isinstance(tho, list) else len(tho.get("data", []))

    if khai is None:
        canh_bao.append("khong tim thay token_usage trong danh sach collection")
    elif khai != that:
        canh_bao.append(f"token_usage: API khai {khai:,} ban ghi nhung export tra ve {that:,}")
    else:
        print(f"  KIEM CHEO DAT: token_usage {that:,} ban ghi, khop so API tu khai")
    return canh_bao


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--app", default="ralli,tla-hd", help="ralli | tla-hd | ca hai")
    p.add_argument("--ra", default=str(THU_MUC_RA))
    p.add_argument("--lat-mong", action="store_true",
                   help="Bo qua cac endpoint nang, de tu soat quay vong nhanh")
    args = p.parse_args()

    ngay = date.today().isoformat()
    apps = [a.strip() for a in args.app.split(",") if a.strip()]
    la = [a for a in apps if a not in NGUON]
    if la:
        raise SystemExit(f"App khong biet: {la}. Chi co: {list(NGUON)}")

    tat_ca: dict[str, list[dict]] = {}
    canh_bao: list[str] = []

    for app in apps:
        thu_muc = Path(args.ra) / app / ngay
        print(f"\n[{app}] -> {thu_muc}")
        tat_ca[app] = keo_mot_app(app, thu_muc, args.lat_mong)
        if app == "ralli" and not args.lat_mong:
            canh_bao += kiem_cheo_ralli(thu_muc)

    print("\n" + "=" * 70)
    hong_bat_buoc = []
    for app, rows in tat_ca.items():
        ok = sum(1 for r in rows if r["trang_thai"] == "OK")
        print(f"{app:<10} {ok}/{len(rows)} endpoint lay duoc")
        # "BO QUA (lat mong)" la lua chon co chu dinh, khong phai that bai.
        hong_bat_buoc += [f"{app}/{r['file']}: {r['trang_thai']}"
                          for r in rows if r["bat_buoc"]
                          and r["trang_thai"] != "OK"
                          and not r["trang_thai"].startswith("BO QUA")]

    for c in canh_bao:
        print(f"CANH BAO: {c}")

    if hong_bat_buoc:
        print("\nENDPOINT BAT BUOC HONG:")
        for h in hong_bat_buoc:
            print(f"  {h}")
        raise SystemExit(1)
    if canh_bao:
        raise SystemExit("Co canh bao kiem cheo - xem o tren, khong coi la dat.")
    print("XONG - moi endpoint bat buoc deu lay duoc")


if __name__ == "__main__":
    main()
