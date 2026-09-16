"""Soat lop xac thuc cua API. KHONG CAN DATABASE, KHONG CAN DOCKER.

    python tools/diagnostics/audit_api_auth.py        # ky vong: 24/24

VI SAO KHONG CAN DATABASE
-------------------------
Da do 21/08/2026: backend/main.py import xong ma khong cham database -
store.open_db() chi chay TRONG than endpoint. Con 401 bi chan o tang phu
thuoc, tuc TRUOC than. Nen toan bo duong tu choi kiem duoc tren mot may
trang: khong Postgres, khong du lieu.

Khac voi backend/check_api.py: file kia doi chieu SO LIEU nen phai co database
that. File nay chi hoi mot cau - "co ai vao duoc ma khong co khoa khong" - va
cau do tra loi duoc o bat cu dau.

VI SAO NO PHAI TON TAI
----------------------
Che do hong cua lop xac thuc phai la "may chu KHONG CHAY", tuyet doi khong
phai "may chu chay mo". Mot bo kiem chi goi API DANG chay se van xanh khi ai
do lo tay bo mat cai chan do - vi luc ay may chu van tra loi binh thuong.
File nay tu DUNG may chu len o nhieu cau hinh, ke ca cau hinh thieu bien, nen
no bat duoc dung cai ma bo kiem kia khong the thay.

Hai bay da bat duoc that (21/08/2026):
  - secrets.compare_digest voi hai `str` nem TypeError khi co ky tu ngoai
    ASCII, nen `Authorization: Bearer <chuoi co dau>` lam MOI endpoint tra 500
    thay vi 401. Nguoi goi dieu khien duoc ve trai nen khong can biet khoa.
  - HTTPBearer mac dinh (auto_error=True) tra 403 chu khong phai 401.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve()
while ROOT.parent != ROOT and not (ROOT / "backend" / "main.py").exists():
    ROOT = ROOT.parent
if not (ROOT / "backend" / "main.py").exists():
    raise SystemExit("Khong tim thay goc repo")

PY = sys.executable
# Cong RIENG, khong dung 8000: chay duoc ca khi may chu that dang mo.
PORT = 8123
BASE = f"http://127.0.0.1:{PORT}"
# Khoa CHI song trong tien trinh nay: khong doc .env, khong ghi ra dau.
KHOA = "khoa-chi-dung-de-soat-abc123"

dat = 0
hong: list[str] = []


def ky_vong(ok: bool, nhan: str, chi_tiet: str = "") -> None:
    global dat
    if ok:
        dat += 1
        print(f"[  ok  ] {nhan}")
    else:
        hong.append(f"{nhan}: {chi_tiet}")
        print(f"[ HONG ] {nhan}\n         {chi_tiet}")


def goi(path: str, khoa: str | None = None, method: str = "GET"):
    """Tra ve (ma_http, than, cac_header). Khong nem ngoai le vi ma loi."""
    req = urllib.request.Request(BASE + path, method=method)
    if khoa is not None:
        req.add_header("Authorization", "Bearer " + khoa)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read()[:400], r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400], e.headers


def mo_may_chu(env_them: dict, reload_: bool = False):
    env = {k: v for k, v in os.environ.items()
           if k not in ("DASHBOARD_KEY", "DASHBOARD_OPEN")}
    env.update(env_them)
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [PY, "-m", "uvicorn", "backend.main:app", "--port", str(PORT),
           "--host", "127.0.0.1"]
    if reload_:
        cmd.append("--reload")
    return subprocess.Popen(cmd, cwd=str(ROOT), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")


def doi_song(giay: float = 20.0) -> bool:
    het = time.time() + giay
    while time.time() < het:
        try:
            urllib.request.urlopen(BASE + "/healthz", timeout=2)
            return True
        except urllib.error.HTTPError:
            return True          # co tra loi = da lang nghe
        except Exception:
            time.sleep(0.3)
    return False


def doi_chet(giay: float = 15.0) -> bool:
    """Doi cho cong thuc su khong con ai lang nghe.

    Thieu buoc nay thi mot may chu sot lai tu pha truoc se tra loi thay, va
    pha B bao "may chu van chay" - mot phat hien gia do chinh kich ban de ra.
    """
    het = time.time() + giay
    while time.time() < het:
        try:
            urllib.request.urlopen(BASE + "/healthz", timeout=2)
            time.sleep(0.3)
        except urllib.error.HTTPError:
            time.sleep(0.3)
        except Exception:
            return True
    return False


def dong(p) -> str:
    try:
        p.terminate()
        out, _ = p.communicate(timeout=10)
    except Exception:
        p.kill()
        out, _ = p.communicate(timeout=10)
    return out or ""


# ──────────────────────────── A. May chu CO khoa ────────────────────────────
print("A. May chu chay voi DASHBOARD_KEY\n" + "-" * 70)
p = mo_may_chu({"DASHBOARD_KEY": KHOA})
if not doi_song():
    print(dong(p))
    raise SystemExit("May chu khong len duoc - dung soat.")

try:
    ma, than, hd = goi("/api/accounts")
    ky_vong(ma == 401, "Goi /api/accounts KHONG khoa -> 401", f"nhan {ma}")
    ky_vong(hd.get("WWW-Authenticate") == "Bearer",
            "401 kem header WWW-Authenticate: Bearer",
            f"nhan {hd.get('WWW-Authenticate')!r}")
    ky_vong(b"937" not in than and b"full_name" not in than,
            "Than 401 KHONG chua du lieu nghiep vu", than[:120].decode("utf-8", "replace"))

    ma, _, _ = goi("/api/accounts", khoa="khoa-sai-hoan-toan")
    ky_vong(ma == 401, "Goi voi khoa SAI -> 401", f"nhan {ma}")

    # Day la cho da bat duoc loi that: compare_digest voi str ngoai ASCII nem
    # TypeError -> 500. Nguoi goi dieu khien duoc ve trai, khong can biet khoa.
    # "ấ" (U+1EA5) ngoai latin-1 se lam sap chinh urllib truoc khi gui di -
    # do la LOI KICH BAN, khong phai phat hien. Dung ky tu latin-1 duoc.
    ma, _, _ = goi("/api/accounts", khoa="khoa-á-ñ")
    ky_vong(ma == 401, "Khoa co ky tu NGOAI ASCII -> 401 (khong phai 500)",
            f"nhan {ma} - compare_digest dang so bang str chu khong phai bytes")

    ma, _, _ = goi("/api/accounts", khoa="")
    ky_vong(ma == 401, "Bearer rong -> 401", f"nhan {ma}")

    # Sai luoc do (Basic thay vi Bearer): HTTPBearer(auto_error=False) tra None
    req = urllib.request.Request(BASE + "/api/accounts")
    req.add_header("Authorization", "Basic " + KHOA)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            ma = r.status
    except urllib.error.HTTPError as e:
        ma = e.code
    ky_vong(ma == 401, "Luoc do 'Basic' thay vi 'Bearer' -> 401", f"nhan {ma}")

    # Khoa DUNG: khong duoc la 401. Se la 500 vi khong co database - dieu do
    # CHUNG MINH da qua duoc tang xac thuc va di vao than endpoint.
    ma, _, _ = goi("/api/accounts", khoa=KHOA)
    ky_vong(ma != 401, "Khoa DUNG -> qua duoc tang xac thuc (khong 401)",
            f"nhan 401 - khoa dung ma van bi tu choi")
    ky_vong(ma in (200, 500), "Khoa dung -> vao than endpoint",
            f"nhan {ma}")

    # Diem tham do phai MO, va khong duoc tra du lieu nghiep vu.
    ma, than, _ = goi("/healthz")
    ky_vong(ma == 200, "/healthz khong khoa -> 200", f"nhan {ma}")
    try:
        body = json.loads(than)
    except Exception:
        body = {}
    ky_vong(set(body) == {"status"}, "/healthz chi tra {status}", f"nhan {body}")

    # /api/health PHAI khoa - hai cai ten giong nhau, tra loi hai cau khac han.
    ma, _, _ = goi("/api/health")
    ky_vong(ma == 401, "/api/health VAN doi khoa (khac /healthz)", f"nhan {ma}")

    # Ca 8 endpoint, khong sot cai nao.
    tat_ca = ["/api/health", "/api/catalog", "/api/usage", "/api/accounts",
              "/api/adoption", "/api/usage-by-account", "/api/performance",
              "/api/thinking"]
    lot = [p_ for p_ in tat_ca if goi(p_)[0] != 401]
    ky_vong(not lot, "Ca 8 endpoint deu tra 401 khi khong co khoa",
            f"lot luoi: {lot}")

    # Tham so rac + khong khoa: 401 phai THANG 400. Kiem chua danh tinh phai
    # chay TRUOC moi phep kiem tham so, neu khong thi nguoi la do duoc endpoint
    # nao ton tai bang cach doc ma tra ve.
    ma, _, _ = goi("/api/usage?start=rac-hoan-toan")
    ky_vong(ma == 401, "Tham so rac + khong khoa -> 401 chu khong phai 400",
            f"nhan {ma} - endpoint lo ra thong tin truoc khi kiem khoa")

    # /docs va /openapi.json: co y de mo, nhung PHAI khong chua du lieu.
    ma, than, _ = goi("/openapi.json")
    ky_vong(ma == 200, "/openapi.json mo (co y)", f"nhan {ma}")
finally:
    log_a = dong(p)
    doi_chet()

ky_vong("DASHBOARD_OPEN" not in log_a,
        "Chay co khoa thi KHONG in canh bao che do mo", log_a[-300:])

# ─────────────────── B. May chu THIEU khoa -> khong duoc chay ───────────────
print("\nB. Thieu DASHBOARD_KEY (task 5.2 - quan trong nhat)\n" + "-" * 70)
p = mo_may_chu({})
song = doi_song(giay=8.0)
log_b = dong(p)
doi_chet()
ky_vong(not song, "Thieu khoa -> may chu KHONG lang nghe cong nao",
        "May chu VAN CHAY - day dung la lo hong ma change nay di bit")
ky_vong("THIEU BIEN MOI TRUONG: DASHBOARD_KEY" in log_b,
        "Thong bao neu dung ten bien con thieu", log_b[-300:])
ky_vong("DASHBOARD_KEY=<khoa vua sinh>" in log_b,
        "Thong bao chi ro cach dat vao .env", log_b[-300:])

# ─────────── B2. Cung the nhung voi --reload (cach tai lieu ghi) ────────────
print("\nB2. Thieu khoa + --reload\n" + "-" * 70)
p = mo_may_chu({}, reload_=True)
song = doi_song(giay=8.0)
log_b2 = dong(p)
doi_chet()
ky_vong(not song, "Thieu khoa + --reload -> van KHONG lang nghe",
        "uvicorn --reload van mo cong du app khong nap duoc")

# ─────────────────── C. Chuoi rong cung tinh la thieu ───────────────────────
print("\nC. DASHBOARD_KEY chi co khoang trang\n" + "-" * 70)
p = mo_may_chu({"DASHBOARD_KEY": "    "})
song = doi_song(giay=8.0)
log_c = dong(p)
doi_chet()
ky_vong(not song, "Khoa toan khoang trang -> khong lang nghe", "van chay")

# ─────────────────── D. Che do mo phai luon nhin thay duoc ──────────────────
print("\nD. DASHBOARD_OPEN=1\n" + "-" * 70)
p = mo_may_chu({"DASHBOARD_OPEN": "1"})
song = doi_song()
if song:
    ma, _, _ = goi("/api/accounts")
    ky_vong(ma != 401, "Che do mo -> khong doi khoa", f"nhan {ma}")
log_d = dong(p)
ky_vong(song, "Che do mo -> may chu chay duoc", "khong len duoc")
ky_vong("KHONG XAC THUC" in log_d,
        "Che do mo IN CANH BAO moi lan khoi dong", log_d[-300:])

print("\n" + "=" * 70)
print(f"{dat + len(hong)} ky vong | {dat} dat | {len(hong)} hong")
if hong:
    for h in hong:
        print("  - " + h)
    sys.exit(1)
print("SOAT KHOA: DAT.")
