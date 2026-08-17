"""Keo du lieu tu 2 web app noi bo - Ralli (CTDA) va TLA Hop Dong. CHI DOC.

AN TOAN
-------
Ca hai API deu phoi ra endpoint ghi/xoa that (POST /trigger-data-fetch,
POST /logs/cleanup, DELETE /users/{id}, POST /api/ctda/refresh-data...).
Script nay khoa cung DANH SACH TRANG duoi day va dung method="GET" tuong minh.
Khong co duong nao trong code goi ra mot phuong thuc khac.

TOKEN
-----
JWT cua hai app song rat ngan (~6h va ~1 ngay). Thu tu tim token:

    1. Bien moi truong <APP>_JWT      - dan tay, khong luu gi xuong dia
    2. Dang nhap bang <APP>_USER / <APP>_PASS doc tu .env

Duong (2) la NGOAI LE DUY NHAT so voi ky luat chi-GET cua repo nay: POST toi
/auth/login. No khong ghi du lieu nghiep vu, chi doi tai khoan lay token, va
duoc chon co y thuc de chay duoc mot lenh duy nhat. Moi endpoint con lai van
la GET tren danh sach trang.

Token KHONG bao gio duoc in ra man hinh hay ghi xuong dia. .env da nam trong
.gitignore san. Xem .env.example de biet can dien gi.

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
import base64
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "raw_web"

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

SOURCES = {
    "ralli": {
        "goc": "https://ralliai.rangdong.com.vn:9001",
        "bien": "RALLI_JWT", "bien_user": "RALLI_USER", "bien_pass": "RALLI_PASS",
        # openapi noi ro: application/x-www-form-urlencoded, truong username/password
        "dang_nhap": "/auth/login", "kieu_body": "form",
        "diem": RALLI,
    },
    "tla-hd": {
        "goc": "https://chatbothd.rangdong.com.vn:10001",
        "bien": "HD_JWT", "bien_user": "HD_USER", "bien_pass": "HD_PASS",
        # GET tra 405 => duong dan dung, chi nhan POST. App khong phoi openapi
        # nen kieu body chua chac chan; thu json truoc roi form.
        "dang_nhap": "/api/auth/login", "kieu_body": "json",
        "diem": TLA_HD,
    },
}

ENV_FILE = ROOT / ".env"

# Kiem chung chi binh thuong. Trinh duyet mo duoc ca hai site khong canh bao nen
# chung chi hop le; tat xac thuc o day la tu lam yeu ket noi vo co.
CTX = ssl.create_default_context()


class LoiKeo(Exception):
    pass


# ───────────────────────── xac thuc ─────────────────────────

def read_env(path: Path) -> dict:
    """Doc .env dang KEY=VALUE. Tu viet de khong them phu thuoc ngoai."""
    out_path: dict[str, str] = {}
    if not path.exists():
        return out_path
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out_path[key.strip()] = value.strip().strip('"').strip("'")
    return out_path


def expires_in(token: str) -> str:
    """Doc exp trong JWT de bao con bao lau. KHONG in token."""
    try:
        body = token.split(".")[1]
        body += "=" * (-len(body) % 4)
        exp = json.loads(base64.urlsafe_b64decode(body)).get("exp")
        if not exp:
            return "khong co exp"
        remaining = exp - time.time()
        moc = datetime.fromtimestamp(exp).strftime("%H:%M %d/%m")
        return f"het han {moc} (con {remaining / 3600:.1f} gio)" if remaining > 0 else f"DA HET HAN luc {moc}"
    except Exception:
        return "khong doc duoc exp"


def login(config: dict, username: str, password: str) -> str:
    """POST /auth/login lay JWT. Day la POST DUY NHAT trong ca script nay.

    Thu kieu body theo cau hinh truoc, roi thu kieu con lai: TLA HD khong phoi
    openapi nen kieu body la suy doan, va 422 chi co nghia "sai dang", khong co
    nghia "sai mat khau".
    """
    url = config["goc"] + config["dang_nhap"]
    body_order = [config["kieu_body"]] + [k for k in ("json", "form") if k != config["kieu_body"]]
    last_error = ""

    for body_kind in body_order:
        if body_kind == "form":
            du_lieu = urllib.parse.urlencode(
                {"grant_type": "password", "username": username, "password": password}
            ).encode()
            content_type = "application/x-www-form-urlencoded"
        else:
            du_lieu = json.dumps({"username": username, "password": password}).encode()
            content_type = "application/json"

        req = urllib.request.Request(
            url, data=du_lieu, method="POST",
            headers={"Content-Type": content_type, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
                payload = json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read(300).decode("utf-8", "replace")
            # 401/403 = sai tai khoan. Doi kieu body cung vo ich, dung ngay.
            if e.code in (401, 403):
                raise LoiKeo(f"HTTP {e.code} khi dang nhap - sai tai khoan/mat khau") from e
            last_error = f"HTTP {e.code} ({body_kind}): {body[:160]}"
            continue
        except Exception as e:
            raise LoiKeo(f"{type(e).__name__}: {e}") from e

        for key in ("access_token", "token", "accessToken", "jwt"):
            if isinstance(payload.get(key), str):
                return payload[key]
        trong = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        for key in ("access_token", "token", "accessToken"):
            if isinstance(trong.get(key), str):
                return trong[key]
        last_error = f"dang nhap OK ({body_kind}) nhung khong tim thay token; khoa: {list(payload)}"

    raise LoiKeo(last_error or "khong dang nhap duoc")


def get_token(name: str, config: dict, env: dict) -> tuple[str, str]:
    """Tra (token, mo ta nguon). Khong bao gio tra ve chuoi rong."""
    san = env.get(config["bien"], "").strip()
    if san:
        return san, f"{config['bien']} co san"

    username = env.get(config["bien_user"], "").strip()
    password = env.get(config["bien_pass"], "").strip()
    if not (username and password):
        raise SystemExit(
            f"[{name}] khong co token va khong co tai khoan de dang nhap.\n"
            f"  Dat {config['bien']} trong moi truong,\n"
            f"  HOAC dien {config['bien_user']} va {config['bien_pass']} vao {ENV_FILE}.\n"
            f"  Xem .env.example."
        )
    return login(config, username, password), f"dang nhap {config['login']}"


def http_get(base: str, path: str, token: str, attempts: int = 3) -> bytes:
    """GET mot duong dan. Thu lai khi loi mang, KHONG thu lai khi 4xx."""
    url = base + path
    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            method="GET",                 # tuong minh - khong bao gio thanh POST/PUT/DELETE
        )
        try:
            with urllib.request.urlopen(req, timeout=180, context=CTX) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            body = e.read(300).decode("utf-8", "replace")
            # 401/403 = token het han hoac thieu quyen; thu lai vo nghia.
            raise LoiKeo(f"HTTP {e.code} - {body}") from e
        except Exception as e:
            if attempt == attempts:
                raise LoiKeo(f"{type(e).__name__}: {e}") from e
            time.sleep(2 * attempt)
    raise LoiKeo("khong toi day duoc")


def describe(obj: object) -> str:
    """Mo ta ngan gon noi dung, de nhin ra ngay khi mot endpoint tra ve rong."""
    if isinstance(obj, list):
        return f"list[{len(obj)}]"
    if isinstance(obj, dict):
        for key in ("data", "items", "users", "units", "collections", "tree", "sessions"):
            gt = obj.get(key)
            if isinstance(gt, list):
                return f"{key}[{len(gt)}]"
        return "{" + ",".join(list(obj)[:4]) + "}"
    return type(obj).__name__


def pull_one_app(name: str, folder: Path, thin_slice: bool, token: str) -> list[dict]:
    config = SOURCES[name]
    folder.mkdir(parents=True, exist_ok=True)
    result: list[dict] = []

    for filename, path, bat_buoc, nang in config["diem"]:
        if thin_slice and nang:
            result.append({"file": filename, "trang_thai": "BO QUA (lat mong)",
                            "bat_buoc": bat_buoc, "byte": 0, "noi_dung": "-"})
            continue
        try:
            body = http_get(config["goc"], path, token)
        except LoiKeo as e:
            result.append({"file": filename, "trang_thai": f"HONG: {e}",
                            "bat_buoc": bat_buoc, "byte": 0, "noi_dung": "-"})
            print(f"  {'X':<2} {filename:<34} {e}")
            continue

        try:
            obj = json.loads(body)
        except json.JSONDecodeError:
            # Tra ve HTML (thuong la trang SPA) nghia la duong dan khong ton tai
            # that su, du ma tra ve 200. Day la loi, khong duoc luu.
            result.append({"file": filename, "trang_thai": "HONG: khong phai JSON",
                            "bat_buoc": bat_buoc, "byte": len(body), "noi_dung": "-"})
            print(f"  {'X':<2} {filename:<34} tra ve khong phai JSON ({len(body):,} byte)")
            continue

        (folder / filename).write_text(
            json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
        mo_ta = describe(obj)
        result.append({"file": filename, "trang_thai": "OK", "bat_buoc": bat_buoc,
                        "byte": len(body), "noi_dung": mo_ta})
        print(f"  {'v':<2} {filename:<34} {len(body):>10,} byte  {mo_ta}")

    return result


def pull_tla_members(folder: Path, token: str) -> str:
    """Thanh vien tung don vi TLA HD -> units-members.json.

    Phai keo rieng vi duong dan co {unit_id} nen khong nam duoc trong danh sach
    trang tinh. Day la nguon DUY NHAT co email/role/phone cua nguoi dung TLA HD:
    token-usage/filter-options chi co id/username/full_name/unit_id, nap tu do
    se lang le mat email cua toan bo nguoi dung.
    """
    f_units = folder / "units.json"
    if not f_units.exists():
        return "khong co units.json de duyet thanh vien"

    units = json.loads(f_units.read_text(encoding="utf-8"))
    danh_sach = units.get("units") if isinstance(units, dict) else units
    base = SOURCES["tla-hd"]["goc"]
    gom: list[dict] = []
    hong: list[str] = []

    for u in danh_sach:
        try:
            body = http_get(base, f"/api/units/{u['id']}/members", token)
            gom.append(json.loads(body))
        except (LoiKeo, json.JSONDecodeError) as e:
            hong.append(f"{u.get('name')}: {e}")

    (folder / "units-members.json").write_text(
        json.dumps(gom, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(x.get("members") or []) for x in gom)
    print(f"  {'v':<2} {'units-members.json':<34} {len(gom)}/{len(danh_sach)} don vi,"
          f" {total} thanh vien")
    return f"khong keo duoc thanh vien cua {len(hong)} don vi: {hong[:3]}" if hong else ""


def crosscheck_ralli(folder: Path) -> list[str]:
    """So so ban ghi tho voi so ma chinh API tu khai trong /api/database/collections.

    Day la phep kiem quan trong nhat cua Ralli: neu /export im lang cat bot thi
    hai con so nay tach nhau. Khong co no thi mot ban keo thieu 90% van trong
    nhu mot ban keo thanh cong.
    """
    canh_bao: list[str] = []
    f_collections = folder / "db-collections.json"
    f_raw = folder / "db-token_usage-raw.json"
    if not (f_collections.exists() and f_raw.exists()):
        return ["khong du file de kiem cheo so ban ghi token_usage"]

    collections_json = json.loads(f_collections.read_text(encoding="utf-8"))
    khai = None
    for c in collections_json.get("collections", []):
        if c.get("name") == "token_usage":
            khai = c.get("count")
    raw_json = json.loads(f_raw.read_text(encoding="utf-8"))
    that = len(raw_json) if isinstance(raw_json, list) else len(raw_json.get("data", []))

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
    p.add_argument("--ra", dest="out_path", default=str(OUT_DIR))
    p.add_argument("--lat-mong", dest="thin_slice", action="store_true",
                   help="Bo qua cac endpoint nang, de tu soat quay vong nhanh")
    p.add_argument("--chi-kiem-token", action="store_true",
                   help="Chi lay token roi thoat. De goi truoc cac buoc dai.")
    args = p.parse_args()

    day = date.today().isoformat()
    apps = [a.strip() for a in args.app.split(",") if a.strip()]
    unknown = [a for a in apps if a not in SOURCES]
    if unknown:
        raise SystemExit(f"App khong biet: {unknown}. Chi co: {list(SOURCES)}")

    # Bien moi truong thang duoc uu tien hon .env, de dan tay van de.
    env = {**read_env(ENV_FILE), **{k: v for k, v in os.environ.items() if v}}

    # Lay token cho TAT CA app TRUOC khi keo bat cu thu gi: hong xac thuc o app
    # thu hai sau khi da keo xong app thu nhat la kieu that bai ton thoi gian
    # nhat, va o day no hoan toan tranh duoc.
    token_cua: dict[str, str] = {}
    for app in apps:
        tk, source = get_token(app, SOURCES[app], env)
        token_cua[app] = tk
        print(f"[{app}] token: {source} | {expires_in(tk)}")
    if args.chi_kiem_token:
        print("Chi kiem token - dung tai day.")
        return

    tat_ca: dict[str, list[dict]] = {}
    canh_bao: list[str] = []

    for app in apps:
        folder = Path(args.out_path) / app / day
        print(f"\n[{app}] -> {folder}")
        tat_ca[app] = pull_one_app(app, folder, args.thin_slice, token_cua[app])
        if app == "ralli" and not args.thin_slice:
            canh_bao += crosscheck_ralli(folder)
        if app == "tla-hd" and not args.thin_slice:
            errors = pull_tla_members(folder, token_cua[app])
            if errors:
                canh_bao.append(errors)

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
