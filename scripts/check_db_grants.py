"""Vai doc con doc duoc khong - buoc cuoi cua khau dung lai, va chay tay duoc.

    python scripts/check_db_grants.py [--role api_readonly]

VI SAO CO SCRIPT NAY
--------------------
`scripts/rebuild_db.py` buoc 1 goi `load_billing --rebuild`, ma buoc do goi
`db/connect.py:251`:

    DROP SCHEMA public CASCADE; CREATE SCHEMA public;

Lenh do xoa MOI GRANT - tren schema, tren moi bang, moi view, VA ca cac dong
`ALTER DEFAULT PRIVILEGES ... IN SCHEMA public`. Cho cap lai la
`docker/read-only-api.sql`, ma no CHI chay qua container `api-db-init`
(`restart: "no"`), tuc chi khi ai do goi `docker compose up -d`.

Nen: cu dung lai database la vai doc cua API mat sach quyen.

DO THAT NGAY 02/09/2026
-----------------------
    16:08:31  api-db-init xong        -> quyen duoc cap
    16:14:06  rebuild_db.py xong      -> quyen bi xoa
    16:52:14  container `api` tat     -> 38 phut chay tren DB no khong doc noi

    api_readonly thu GHI  ->  bi tu choi (SQLSTATE 25006)          "DAT"
    api_readonly thu DOC  ->  0/20 bang · 0/3 view
                              has_schema_privilege(...,'USAGE') = False

VA KHONG BO KIEM NAO BAT DUOC
-----------------------------
    scripts/audit_db.py     chay bang vai `token` (chu schema)  -> 42/42 DAT
    backend/check_api.py    read_only() thu mot lenh GHI, cho bi tu choi
                            MAT QUYEN DOC thi lenh ghi VAN bi tu choi
                            -> bao DAT dung luc API mu hoan toan

Lan 02/09 vo hai vi stack tat ngay sau do. Hinh dang nguy hiem la chay
`rebuild_db.py` TRONG LUC stack dang bat: API mu ngay lap tuc, khong ai duoc bao,
va ca hai bo kiem deu bao lanh.

BAO DONG, KHONG TU CHUA
-----------------------
Script nay CO Y khong tu cap lai quyen. Van de khong phai quyen bi xoa - van de
la KHONG AI DUOC BAO. Tu chua se sua cai thu nhat va giu nguyen cai thu hai, roi
lo hong quay lai lan sau o mot dang khac.

Chua bang mot lenh:  docker compose up -d api

KHONG DUNG `SELECT 1` DE KIEM
-----------------------------
Cau do khong can quyen USAGE tren schema nen no chay duoc CA KHI quyen da mat
sach. Script nay hoi thang catalog: `has_schema_privilege` va
`has_table_privilege` cho TUNG bang va TUNG view.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "db"))

import connect  # noqa: E402
import logs  # noqa: E402

log = logs.get_logger("check_grants")

# Vai ma container `api` dung. Khai o docker-compose.yml qua
# `-v api_role=api_readonly` cho docker/read-only-api.sql.
DEFAULT_ROLE = "api_readonly"


def kiem(cn, role: str) -> list[str]:
    """Tra ve danh sach mo ta cac cho THIEU quyen. Rong = day du."""
    thieu: list[str] = []

    co_vai = connect.query_one(
        cn, "SELECT COUNT(*) FROM pg_catalog.pg_roles WHERE rolname = %s",
        (role,))[0]
    if not co_vai:
        # Khong co vai thi moi phep kiem duoi deu vo nghia - dung han o day, dung
        # de nguoi doc phai suy tu 24 dong "thieu SELECT".
        return [f"vai `{role}` KHONG TON TAI trong database"]

    if not connect.query_one(
            cn, "SELECT has_schema_privilege(%s, 'public', 'USAGE')", (role,))[0]:
        thieu.append(f"vai `{role}` khong co USAGE tren schema `public`")

    # TUNG bang va TUNG view, khong phai "thu mot bang". `DROP SCHEMA` xoa tat,
    # nhung mot migration hong nua chung co the de lai quyen KHONG DEU - va do
    # moi la truong hop kho thay nhat.
    doi_tuong = connect.query(cn, """
        SELECT table_name, table_type FROM information_schema.tables
         WHERE table_schema = 'public' ORDER BY table_type, table_name""")
    khong_doc_duoc = [
        (t, k) for t, k in doi_tuong
        if not connect.query_one(
            cn, "SELECT has_table_privilege(%s, %s, 'SELECT')",
            (role, f"public.{t}"))[0]]
    if khong_doc_duoc:
        bang = [t for t, k in khong_doc_duoc if k == "BASE TABLE"]
        view = [t for t, k in khong_doc_duoc if k != "BASE TABLE"]
        thieu.append(
            f"vai `{role}` khong doc duoc {len(khong_doc_duoc)}/{len(doi_tuong)}"
            f" doi tuong ({len(bang)} bang, {len(view)} view):"
            f" {', '.join(t for t, _ in khong_doc_duoc[:8])}"
            + (" ..." if len(khong_doc_duoc) > 8 else ""))
    return thieu


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=connect.DEFAULT_DSN,
                   help="DSN cua vai QUAN TRI (chu schema), khong phai vai doc")
    p.add_argument("--role", default=DEFAULT_ROLE)
    args = p.parse_args()

    cn, _ = connect.open_db(args.db)
    thieu = kiem(cn, args.role)
    tong = connect.query_one(
        cn, "SELECT COUNT(*) FROM information_schema.tables"
            " WHERE table_schema = 'public'")[0]
    cn.close()

    if not thieu:
        log.info("  vai `%s` doc duoc %d/%d bang+view, co USAGE tren schema",
                 args.role, tong, tong)
        return 0

    for d in thieu:
        log.error("  %s", d)
    log.error("  ")
    # HAI NGUYEN NHAN KHAC HAN NHAU, va chung doi hai cach chua khac nhau.
    # Gop chung mot thong diep la chi sai cho cho nguoi doc - `DROP SCHEMA`
    # xoa GRANT chu KHONG xoa vai.
    if any("KHONG TON TAI" in d for d in thieu):
        log.error("  Vai chua duoc tao bao gio, hoac ten vai truyen vao sai.")
        log.error("  `DROP SCHEMA` xoa GRANT chu KHONG xoa vai, nen day KHONG"
                  " phai dau vet cua rebuild_db.py.")
        log.error("  ")
        log.error("  Kiem lai ten:  docker-compose.yml khai `-v"
                  " api_role=api_readonly` cho docker/read-only-api.sql")
    else:
        log.error("  Vai co that nhung da mat quyen. `DROP SCHEMA public"
                  " CASCADE` (db/connect.py:251) xoa moi GRANT,")
        log.error("  va cho cap lai la docker/read-only-api.sql - no CHI chay"
                  " qua container `api-db-init` (`restart: \"no\"`).")
    log.error("  ")
    log.error("  CHUA:  docker compose up -d api")
    log.error("  ")
    log.error("  KHONG tu cap lai o day - CO Y. Van de khong phai quyen bi xoa,"
              " ma la KHONG AI DUOC BAO.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
