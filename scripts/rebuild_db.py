"""Dung lai toan bo database tu DU LIEU DA THU THAP.

    docker compose up -d                                  # PHAI len truoc
    python scripts/rebuild_db.py                          # dung DEFAULT_DSN
    python scripts/rebuild_db.py --db postgresql://.../token_ledger_v2

DSN la gi
---------
Chuoi ket noi PostgreSQL. SQLite da bi go 24/08/2026 (change
`drop-the-sqlite-escape-hatch`) - dua vao mot duong dan .sqlite thi connect.py
dung ngay voi thong bao noi ro, chu khong im lang tao file.

Mac dinh lay tu connect.DEFAULT_DSN, KHONG khai rieng o day. Truoc 17/08/2026
file nay co hang so DSN cua rieng no, va scripts/update_dashboard.py goi no
khong truyen --db - nen doi connect.py xong ma duong ong van dung lai database
cu, khong loi nao bao ra.

NGUON DU LIEU
-------------
Toan bo lay tu thu muc data/, tuc nhung gi cac script pull_* da thu thap:

    data/da_xu_ly/billing/billing_<ngay>.csv          <- merge_billing.py
    data/da_xu_ly/du_lieu_giam_sat/<ngay>-gop/        <- merge_monitoring.py
    data/raw_web/ralli/<ngay>/                        <- pull_web_apps.py
    data/raw_web/tla-hd/<ngay>/                       <- pull_web_apps.py
    data/raw_web/tla-hd/<ngay>/usage-day-user-model.json  <- pull_hd_usage.py

Hai script pull_* ghi vao CUNG cay tla-hd nhung theo NGAY KEO cua rieng chung,
nen thu muc moi nhat co the chi chua mot file. Cac loader vi vay tim "dot moi
nhat CO DU file can" chu khong lay bua thu muc cuoi - xem `_latest` trong
db/load_org.py.

Moi script nap tu chon ban MOI NHAT, khong ghim ngay. Nhung `data/` KHONG len
git, nen mot ban clone thuan tuy chi dung duoc schema + danh muc (hai file .sql
co trong repo), khong co so lieu. Do la ranh gioi co chu dich: schema va danh
muc la MA, so lieu la DU LIEU.

CANH BAO VE MONITORING
----------------------
Nguon monitoring la thu muc DA GOP. No chi day du khi con giu ca dot keo cu:
cua so luu giu cua Google truot 91 ngay chi trong 7 ngay (do 06/08 thay 196
ngay, do 13/08 con 112). Du lieu 22/01-22/04 gio CHI con tren dia. Xoa thu muc
keo cu la mat vinh vien, khong dung lai duoc tu bat ky dau.

THU TU BAT BUOC
---------------
    1  load_billing --rebuild   migration tai cho, xoa dong, nap danh muc + hoa don
    2  load_org                 dim_unit / account / dim_user / dim_function
    3  load_ralli               fact_call
    4  load_hd                  fact_app_daily
    5  load_monitoring          fact_monitoring
    6  load_gateway             fact_call (nguon 'gateway')
    7  build_usage_daily        fact_usage_daily (bang dan xuat)
    8  build_usage_hourly       fact_usage_hourly (bang dan xuat)
    9  build_performance        fact_perf_daily + fact_latency_daily
   10  check_db_grants          KIEM quyen doc cua vai `api_readonly`

Buoc 1 phai dau vi --rebuild xoa dong moi bang. Buoc 2 truoc buoc 3-4 vi load_org xoa
fact_call, va vi ca hai buoc do deu tra account_id trong bang `account` do
load_org dung len. BA buoc cuoi la bang DAN XUAT: chung doc cac bang tren chu
khong doc file, nen phai chay sau cung.

Buoc 8 doc CUNG mot bo loc voi buoc 7 va tu doi chieu tong cua minh voi tong
theo ngay - no dung han neu hai con so lech. Nen thu tu 7 truoc 8 la bat buoc.

BUOC 10 KHONG NAP GI - NO LA PHEP KIEM, VA NO PHAI DUNG CUOI
------------------------------------------------------------
Truoc 14/09/2026 buoc 1 goi `DROP SCHEMA public CASCADE`, xoa MOI GRANT - ke ca
quyen doc cua vai ma container `api` dung. Do 02/09/2026: sau mot lan dung lai,
`api_readonly` doc duoc 0/20 bang · 0/3 view, va container `api` chay 38 phut tren
mot database no khong doc noi. Khong bo kiem nao bat duoc: audit_db.py chay bang
vai `token` (chu schema), con check_api.py chi thu mot lenh GHI - ma mat quyen doc
thi lenh ghi VAN bi tu choi.

Tu 14/09/2026 buoc 1 chi TRUNCATE nen quyen con nguyen (change
`stop-a-later-pull-from-shrinking-an-earlier-one`). Buoc 10 VAN o lai: quyen con
mat duoc theo duong khac - mot database moi chua chay read-only-api.sql, hay ai
do DROP bang tay - va mot phep kiem thi re.

Buoc nay BAO DONG chu khong tu chua. Van de khong phai quyen bi xoa, ma la khong
ai duoc bao. Chua bang mot lenh:  docker compose up -d api

VI SAO CO RIENG MOT BUOC CHO TLA HD
-----------------------------------
Ralli phoi log TUNG LUOT GOI nen fact_call gop ra ngay nao cung duoc. TLA HD chi
phoi API da tong hop san, muc min nhat lay duoc la (ngay x nguoi x model) - nen
no vao bang rieng fact_app_daily. Hai duong cung do ve fact_usage_daily
source='app'. Chi tiet o db/load_hd.py.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

sys.path.insert(0, str(ROOT / "db"))

import connect  # noqa: E402
import logs  # noqa: E402

log = logs.get_logger("rebuild")

# (nhan, duong dan tuong doi ROOT, tham so rieng)
#
# Mang DUONG DAN chu khong chi ten file (doi 03/09/2026): buoc cuoi nam o
# `scripts/` chu khong o `db/`, va no la phep KIEM chu khong phai buoc NAP.
STEPS = [
    ("Billing",          "db/load_billing.py",      ["--rebuild"]),
    ("Org tree",         "db/load_org.py",          []),
    ("Ralli log",        "db/load_ralli.py",        []),
    ("TLA HD usage",     "db/load_hd.py",           []),
    ("Monitoring",       "db/load_monitoring.py",   []),
    # PHAI dung TRUOC build_usage_daily: buoc do la bang DAN XUAT, no doc
    # fact_call. Va PHAI co mat o day - buoc 1 (`--rebuild`) xoa dong fact_call,
    # nen thieu dong nay thi moi lan cap nhat dashboard la du lieu Gateway bien
    # mat, khong loi nao bao. Bo nap tu do lai tu dau vi moc nap doc chinh
    # fact_call: bang rong -> doc toan bo so.
    ("Gateway ledger",   "db/load_gateway.py",      []),
    # So cua NHA CUNG CAP - y kien thu hai ve cung mot luu luong, KHONG phai
    # nguon thu nam. `usage_resolved` khong doc no.
    #
    # PHAI co mat o day, cung ly le voi hai buoc tren: buoc 1 (`--rebuild`) xoa
    # dong moi bang, nen thieu dong nay thi `fact_provider_daily` rong sau moi lan
    # cap nhat - va phep doi chieu se lang le bao "chua kiem duoc" mai mai.
    #
    # `--tuy-chon`: khong phai ngay nao cung co lan keo nha cung cap, va thieu
    # no KHONG phai loi. Nhung bo nap se noi to rang no thieu, kem hau qua.
    ("Provider ledger",  "db/load_provider.py",     ["--tuy-chon"]),
    ("Usage rollup",     "db/build_usage_daily.py", []),
    # PHAI co mat, cung ly le voi buoc Gateway o tren: buoc 1 (`--rebuild`) xoa
    # dong moi bang, nen thieu dong nay thi moi lan cap nhat dashboard la bang
    # theo gio bien mat - khong loi nao bao, chi la mot bang rong.
    ("Usage hourly",     "db/build_usage_hourly.py", []),
    ("Performance",      "db/build_performance.py", []),
    # BUOC CUOI, va no la mot PHEP KIEM chu khong phai mot buoc nap.
    #
    # Truoc 14/09/2026 buoc 1 (`--rebuild`) goi `DROP SCHEMA public CASCADE`, va
    # lenh do xoa MOI GRANT - ke ca quyen doc cua vai ma container `api` dung.
    # Cho cap lai la docker/read-only-api.sql, chi chay qua `api-db-init`.
    # Nay buoc 1 chi TRUNCATE nen quyen con; buoc kiem nay van giu vi quyen con
    # mat duoc theo duong khac.
    #
    # Do 02/09/2026: sau mot lan dung lai, `api_readonly` doc duoc 0/20 bang va
    # 0/3 view, trong khi CA HAI bo kiem deu bao lanh - audit_db.py chay bang vai
    # `token` (chu schema), con check_api.py chi thu mot lenh GHI, ma mat quyen
    # doc thi lenh ghi VAN bi tu choi.
    #
    # Buoc nay BAO DONG, KHONG tu cap lai - xem docstring cua check_db_grants.py.
    ("Read-role grants", "scripts/check_db_grants.py", []),
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=connect.DEFAULT_DSN,
                   help="Chuoi ket noi PostgreSQL. Mac dinh: connect.DEFAULT_DSN")
    p.add_argument("--from-step", type=int, default=1,
                   help=f"Bat dau tu buoc N (1-{len(STEPS)}). Dung khi mot buoc hong va da sua xong.")
    args = p.parse_args()

    log.info("rebuilding database from collected data -> %s",
             connect.mask_dsn(args.db))
    if args.from_step > 1:
        log.warning("starting at step %d - EARLIER STEPS ARE SKIPPED", args.from_step)
        if "--rebuild" in STEPS[0][2]:
            log.warning("skipping step 1 means migrations are NOT applied and old rows are NOT emptied")

    started = time.time()
    for i, (label, filename, extra_args) in enumerate(STEPS, start=1):
        if i < args.from_step:
            log.info("[%d/%d] %s - skipped", i, len(STEPS), label)
            continue
        log.info("[%d/%d] %s  (%s)", i, len(STEPS), label, filename)
        # Tien trinh con ghi thang ra stdout, con logger o day qua bo dem cua no;
        # khong flush thi loi cua con hien truoc dong danh dau buoc.
        # logging.StreamHandler da tu flush - dong duoi la bao hiem.
        sys.stdout.flush()
        # DSN di qua BIEN MOI TRUONG, khong qua dong lenh: dong lenh cua mot
        # tien trinh nhin thay duoc tu ngoai (ps / Task Manager), nen dat DSN
        # Postgres o day la phoi mat khau ra ca 7 tien trinh con. Truoc
        # 17/08/2026 DSN la duong dan file nen khong co gi de lo.
        #
        # Con doc duoc vi connect.DEFAULT_DSN uu tien TOKEN_LEDGER_DSN, va --db
        # cua moi script nap mac dinh bang connect.DEFAULT_DSN.
        result = subprocess.run([PY, str(ROOT / filename), *extra_args],
                                 cwd=ROOT, env={**os.environ,
                                                "TOKEN_LEDGER_DSN": args.db})
        if result.returncode != 0:
            log.error("STOPPED at step %d (%s), exit code %d",
                      i, filename, result.returncode)
            log.error("after fixing, resume from here:  python scripts/rebuild_db.py"
                      " --db <dsn> --from-step %d", i)
            sys.exit(1)

    log.info("done in %ds - all %d steps passed their acceptance checks",
             time.time() - started, len(STEPS))


if __name__ == "__main__":
    main()
