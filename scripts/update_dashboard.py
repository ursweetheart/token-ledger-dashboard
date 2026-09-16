"""Mot lenh: thu thap moi nguon roi dung lai database cho dashboard.

    python scripts/update_dashboard.py

Chay tuan tu 9 buoc. HONG BUOC NAO LA DUNG NGAY - khong buoc nao chay tiep tren
dau ra dang do cua buoc truoc.

    0  Kiem hoa don da moi chua        (viec TAY duy nhat con lai)
    1  Kiem/lay token 2 web app        (lam TRUOC de hong thi hong som)
    2  Keo Cloud Monitoring            ~10-15 phut
    3  Gop cac dot keo Monitoring
    4  Keo Ralli + TLA Hop Dong
    5  Keo chieu nguoi dung TLA Hop Dong  (~100 luot GET)
    6  Gop hoa don tu 7 file Console
    7  Gop histogram do tre theo ngay
    8  Dung lai database          (schema + 7 khau nap, ~15 giay)
    9  Soi database               (30 phep kiem)

DUONG ONG KHONG GHI VAO web/
----------------------------
Truoc 17/08/2026 con mot buoc thu 10 sinh du lieu roi VA THANG vao web/js/app.js
lam ban du phong ngoai tuyen. Da bo cung hai script sinh_du_lieu_dashboard.py va
va_app_js.py: ban du phong do khong tu biet minh cu, nen khi backend hong thi
dashboard hien so cu ma trong y het so moi. Nay dashboard chi doc database, va
khong nap duoc thi no BAO LOI thay vi hien so cu. Frontend la ma nguon, khong
phai dich den cua du lieu.

VI SAO BUOC 0 VA 1 DUNG DAU
---------------------------
Buoc 2 mat hon 10 phut. Phat hien thieu file hoa don hoac token het han SAU do
la vut di 10 phut khong vi ly do gi. Ca hai phep kiem deu chi mat vai giay.

BILLING VAN PHAI TAI TAY
------------------------
Google Cloud Console khong cho tai bao cao GMSSub bang API voi quyen hien co.
Buoc 0 kiem ngay lon nhat trong data/billing/*.csv; cu hon hom qua thi dung han
va in ra viec can lam. Khong tu chay tiep voi hoa don cu, vi khi do dashboard se
co request cua hom nay nhung token cua tuan truoc - sai ma trong nhu that.
Co y chay voi hoa don cu thi them --allow-stale-billing.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

sys.path.insert(0, str(ROOT / "db"))
import logs  # noqa: E402

log = logs.get_logger("pipeline")


class StepFailed(Exception):
    pass


def run_step(label: str, cmd: list[str]) -> float:
    log.info("%s", label)
    # Tien trinh con ghi thang ra stdout, con dong tren di qua bo dem cua logger.
    # Khong flush thi thong bao loi cua con HIEN TRUOC dong danh dau buoc, va
    # nguoi doc khong biet loi thuoc ve buoc nao.
    #
    # logging.StreamHandler DA tu flush sau moi ban ghi, nen dong duoi la bao
    # hiem chu khong phai bat buoc. Giu lai: no khong ton gi, va la thu duy nhat
    # con dung neu sau nay ai do doi handler.
    sys.stdout.flush()
    started = time.time()
    result = subprocess.run(cmd, cwd=ROOT)
    elapsed = time.time() - started
    if result.returncode != 0:
        raise StepFailed(f"{label} failed (exit {result.returncode}) after {elapsed:.0f}s")
    log.info("%s done in %ds", label, elapsed)
    return elapsed


def check_billing(allow_stale: bool) -> str:
    """Ngay lon nhat trong cac file hoa don tho. Dung neu qua cu."""
    folder = ROOT / "data" / "billing"
    files = sorted(folder.glob("*GMSSub*.csv"))
    if not files:
        raise StepFailed(
            f"No billing file found in {folder}\n"
            f"  Go to Google Cloud Console > Billing > Reports, download the 7 GMSSub files\n"
            f"  (one per project) and put them in the folder above."
        )

    newest = ""
    for f in files:
        with f.open(encoding="utf-8-sig", newline="") as h:
            for lines in csv.DictReader(h):
                day = (lines.get("Date") or "").strip()
                if day > newest:
                    newest = day

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    log.info("%d billing files | newest day: %s", len(files), newest)
    if newest < yesterday:
        if not allow_stale:
            raise StepFailed(
                f"STALE billing: newest day {newest}, expected >= {yesterday}.\n"
                f"  Download the 7 GMSSub files again from Google Cloud Console into {folder}\n"
                f"  and rerun. To use stale billing on purpose, add --allow-stale-billing."
            )
        log.warning("billing data is stale (%s), continuing as requested", newest)
    return newest


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                allow_abbrev=False)
    p.add_argument("--allow-stale-billing", action="store_true",
                   help="Run even if billing was not downloaded again (default: stop)")
    p.add_argument("--skip-monitoring", action="store_true",
                   help="Skip the Monitoring pull (~10-15 min). Existing batches are still merged.")
    p.add_argument("--monitoring-days", type=int, default=196,
                   help="Days to pull. Google keeps only part of them; asking wide does no harm.")
    args = p.parse_args()

    total = time.time()
    log.info("dashboard data refresh started")

    try:
        log.info("[0/9] check billing files")
        check_billing(args.allow_stale_billing)

        # Buoc nay dang nhap mot lan roi vut token di; buoc 4 dang nhap lai.
        # Doi lai la biet ngay tu giay thu 5 rang xac thuc co chay duoc khong,
        # thay vi biet sau 15 phut. Hai lan dang nhap re hon nhieu so voi mot
        # lan keo Monitoring bi vut bo.
        run_step("[1/9] check tokens for the 2 web apps",
             [PY, "scripts/pull_web_apps.py", "--token-only"])

        if args.skip_monitoring:
            log.info("[2/9] pull Cloud Monitoring - SKIPPED as requested")
        else:
            run_step("[2/9] pull Cloud Monitoring",
                 [PY, "scripts/pull_monitoring.py",
                  "--days", str(args.monitoring_days), "--align", "60"])

        run_step("[3/9] merge Monitoring batches", [PY, "scripts/merge_monitoring.py"])
        run_step("[4/9] pull Ralli + TLA Contract", [PY, "scripts/pull_web_apps.py"])
        # pull_web_apps chi lay cac trang tong hop san. Chieu NGAY x NGUOI x MODEL
        # cua TLA Hop Dong phai keo rieng - xem docstring pull_tla_contract_usage.py.
        # Thieu buoc nay thi db/load_org.py dung han vi khong tim thay
        # usage-day-user-model.json, va do la hong DUNG cho: som va on ao.
        run_step("[5/9] pull TLA Contract per-user usage",
             [PY, "scripts/pull_tla_contract_usage.py"])
        run_step("[6/9] merge billing", [PY, "scripts/merge_billing.py"])
        run_step("[7/9] merge daily latency histograms",
             [PY, "scripts/merge_latency_daily.py",
              "--out", "data/raw_google_console/do_tre_phan_bo/latency-daily.csv"])  # vi-ok: on-disk path
        run_step("[8/9] rebuild database", [PY, "scripts/rebuild_db.py"])
        run_step("[9/9] audit database", [PY, "scripts/audit_db.py"])

    except StepFailed as e:
        log.error("STOPPED: %s", e)
        sys.exit(1)

    log.info("dashboard data refresh done in %.1f min", (time.time() - total) / 60)
    # Huong dan cho nguoi chay TAY, khong phai log van hanh. Xuong DEBUG.
    log.debug("open index.html to view; the backend must be running: "
              "python -m uvicorn backend.main:app --port 8000")
    log.debug("if the numbers look unchanged, clear the page localStorage "
              "(F12 > Application > Local Storage): app.js bumps its version "
              "but the browser sometimes keeps the old copy")


if __name__ == "__main__":
    main()
