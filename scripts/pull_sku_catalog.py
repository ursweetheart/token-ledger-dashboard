"""Keo metadata CHINH CHU cua Google ve dia - chi doc, chi GET.

    python scripts/pull_sku_catalog.py
    python scripts/pull_sku_catalog.py --list-services

Lay hai thu, luu vao data/raw_google_console/danh_muc/:
    sku-gemini-api.json   597 SKU cua dich vu "Gemini API", KEM GIA chinh thuc
    (descriptor phep do thi da co san trong moi lan keo monitoring)

VI SAO PHAI CO FILE NAY
-----------------------
Truoc day database phan loai SKU va phep do bang cach DOAN TEN:
    quy_tac.suy_loai()          regex tren sku_ten
    "LIKE '%token_count'"       trong dung_usage_daily.py
Google doi cach dat ten la ca hai im lang tra ve sai, khong loi nao bao.

File nay bien viec do thanh DU LIEU tra cuu duoc. Chay lai khi Google them SKU.

VI SAO LUU XUONG DIA MA KHONG GOI TRUC TIEP LUC KHOI TAO DATABASE
-----------------------------------------------------------------
db/sinh_02_danh_muc.py phai chay duoc khi khong co mang va khong co quyen GCP -
dong nghiep pull repo ve, chay dung_lai_db.py la xong. Neu no goi API thi ai
khong co tai khoan GCP se khong dung lai duoc database.

CHI DOC
-------
Chi mot phuong thuc duy nhat: GET. Cloud Billing Catalog API khong co endpoint
ghi nao duoc goi o day. Token lay qua `gcloud auth print-access-token`, dung
trong bo nho, KHONG in ra va KHONG ghi xuong dia.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "raw_google_console" / "danh_muc"

CATALOG = "https://cloudbilling.googleapis.com/v1"
# Ma dich vu "Gemini API" trong Cloud Billing Catalog. Tim bang cach duyet
# /v1/services va loc displayName - xem --list-services.
GEMINI_SERVICE = "AEFD-7695-64FA"


def find_gcloud() -> str:
    """Duong dan gcloud.

    Tren Windows gcloud la `gcloud.cmd`, khong phai file .exe. subprocess.run
    voi danh sach doi so KHONG tra qua PATHEXT nen goi thang "gcloud" se nem
    FileNotFoundError du go trong terminal van chay. shutil.which thi co tra.
    """
    for name in ("gcloud", "gcloud.cmd", "gcloud.CMD"):
        d = shutil.which(name)
        if d:
            return d
    raise SystemExit("gcloud not found. Install the Google Cloud SDK first.")


def token() -> str:
    """Access token tu gcloud. KHONG in ra, KHONG ghi xuong dia."""
    try:
        r = subprocess.run([find_gcloud(), "auth", "print-access-token"],
                           capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise SystemExit("gcloud not found. Install the Google Cloud SDK first.")
    if r.returncode != 0:
        raise SystemExit("gcloud could not issue a token. Run `gcloud auth login` first.\n"
                         f"  {r.stderr.strip()[:200]}")
    return r.stdout.strip()


def get(url: str, tok: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"},
                                 method="GET")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} on GET {url.split('?')[0]}\n"
                         f"  {e.read()[:300].decode('utf-8', 'replace')}")


def paged_get(url: str, key: str, tok: str) -> list[dict]:
    """Duyet het cac trang cua mot endpoint danh sach."""
    out_path: list[dict] = []
    page = ""
    while True:
        d = get(url + (f"&pageToken={page}" if page else ""), tok)
        out_path += d.get(key, [])
        page = d.get("nextPageToken") or ""
        if not page:
            return out_path


def find_service(tok: str) -> None:
    """In ra cac dich vu co ten nghe giong AI - de doi chieu DICH_VU_GEMINI."""
    svc = paged_get(f"{CATALOG}/services?pageSize=5000", "services", tok)
    print(f"{len(svc)} services in the catalog. Ids that look AI-related:")
    for s in svc:
        name = s.get("displayName", "")
        if any(k in name.lower() for k in ("generative", "gemini", "vertex")):
            marker = "  <-- in use" if s["serviceId"] == GEMINI_SERVICE else ""
            print(f"  {s['serviceId']:<24} {name}{marker}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                allow_abbrev=False)
    p.add_argument("--list-services", dest="find_service", action="store_true",
                   help="Only list the service ids and exit, write no file")
    p.add_argument("--out", dest="dest", default=str(OUT_DIR))
    args = p.parse_args()

    tok = token()
    if args.find_service:
        find_service(tok)
        return

    skus = paged_get(f"{CATALOG}/services/{GEMINI_SERVICE}/skus?pageSize=5000", "skus", tok)
    if not skus:
        raise SystemExit(f"The catalog returned 0 SKUs for service {GEMINI_SERVICE}."
                         " Is the service id still correct? Run --list-services.")

    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    f = dest / "sku-gemini-api.json"
    f.write_text(json.dumps(skus, ensure_ascii=False, indent=1), encoding="utf-8")

    with_price = sum(1 for s in skus if (s.get("pricingInfo") or [{}])[0]
                 .get("pricingExpression", {}).get("tieredRates"))
    print(f"service {GEMINI_SERVICE} (Gemini API)")
    print(f"  {len(skus):,} SKUs, {with_price:,} with a price")
    print(f"  -> {f.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
