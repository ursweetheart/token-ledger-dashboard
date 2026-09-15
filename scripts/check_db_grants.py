"""Vai doc con doc duoc khong - buoc cuoi cua khau dung lai, va chay tay duoc.

    python scripts/check_db_grants.py [--role api_readonly]

VI SAO CO SCRIPT NAY
--------------------
Truoc 14/09/2026, `scripts/rebuild_db.py` buoc 1 goi `load_billing --rebuild`, ma
buoc do goi:

    DROP SCHEMA public CASCADE; CREATE SCHEMA public;

Lenh do xoa MOI GRANT - tren schema, tren moi bang, moi view, VA ca cac dong
`ALTER DEFAULT PRIVILEGES ... IN SCHEMA public`. Cho cap lai la
`docker/read-only-api.sql`, ma no CHI chay qua container `api-db-init`
(`restart: "no"`), tuc chi khi ai do goi `docker compose up -d`.

Nen: cu dung lai database la vai doc cua API mat sach quyen.

Tu 14/09/2026 `connect.rebuild()` chi TRUNCATE, nen duong dung lai KHONG con xoa
quyen (change `stop-a-later-pull-from-shrinking-an-earlier-one`). Script nay VAN
o lai: quyen con mat duoc theo duong khac - mot database moi chua chay
`read-only-api.sql`, hay ai do DROP bang tay - va bao dong thi re.

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

# Chu danh dau mot vai khong ton tai. main() tim dung chuoi nay de tach hai nguyen
# nhan, nen hai cho phai dung CHUNG hang so.
ROLE_MISSING = "DOES NOT EXIST"


def check_grants(cn, role: str) -> list[str]:
    """Tra ve danh sach mo ta cac cho THIEU quyen. Rong = day du."""
    missing: list[str] = []

    role_exists = connect.query_one(
        cn, "SELECT COUNT(*) FROM pg_catalog.pg_roles WHERE rolname = %s",
        (role,))[0]
    if not role_exists:
        # Khong co vai thi moi phep kiem duoi deu vo nghia - dung han o day, dung
        # de nguoi doc phai suy tu 24 dong "thieu SELECT".
        return [f"role `{role}` {ROLE_MISSING} in the database"]

    if not connect.query_one(
            cn, "SELECT has_schema_privilege(%s, 'public', 'USAGE')", (role,))[0]:
        missing.append(f"role `{role}` has no USAGE on schema `public`")

    # TUNG bang va TUNG view, khong phai "thu mot bang". Mot lan `DROP SCHEMA` xoa tat,
    # nhung mot migration hong nua chung co the de lai quyen KHONG DEU - va do
    # moi la truong hop kho thay nhat.
    objects = connect.query(cn, """
        SELECT table_name, table_type FROM information_schema.tables
         WHERE table_schema = 'public' ORDER BY table_type, table_name""")
    unreadable = [
        (t, k) for t, k in objects
        if not connect.query_one(
            cn, "SELECT has_table_privilege(%s, %s, 'SELECT')",
            (role, f"public.{t}"))[0]]
    if unreadable:
        tables = [t for t, k in unreadable if k == "BASE TABLE"]
        views = [t for t, k in unreadable if k != "BASE TABLE"]
        missing.append(
            f"role `{role}` cannot read {len(unreadable)}/{len(objects)}"
            f" objects ({len(tables)} tables, {len(views)} views):"
            f" {', '.join(t for t, _ in unreadable[:8])}"
            + (" ..." if len(unreadable) > 8 else ""))
    return missing


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False)
    p.add_argument("--db", default=connect.DEFAULT_DSN,
                   help="DSN of the ADMIN role (schema owner), not the read role")
    p.add_argument("--role", default=DEFAULT_ROLE)
    args = p.parse_args()

    cn, _ = connect.open_db(args.db)
    missing = check_grants(cn, args.role)
    total = connect.query_one(
        cn, "SELECT COUNT(*) FROM information_schema.tables"
            " WHERE table_schema = 'public'")[0]
    cn.close()

    if not missing:
        log.info("  role `%s` can read %d/%d tables+views, has USAGE on the schema",
                 args.role, total, total)
        return 0

    for d in missing:
        log.error("  %s", d)
    log.error("  ")
    # HAI NGUYEN NHAN KHAC HAN NHAU, va chung doi hai cach chua khac nhau.
    # Gop chung mot thong diep la chi sai cho cho nguoi doc - `DROP SCHEMA`
    # xoa GRANT chu KHONG xoa vai.
    if any(ROLE_MISSING in d for d in missing):
        log.error("  The role was never created, or the role name passed in is wrong.")
        log.error("  `DROP SCHEMA` removes GRANTs but NOT roles, so this is NOT"
                  " the trace of a DROP SCHEMA.")
        log.error("  ")
        log.error("  Check the name:  docker-compose.yml passes `-v"
                  " api_role=api_readonly` to docker/read-only-api.sql")
    else:
        log.error("  The role exists but has lost its grants. Since 14/09/2026 rebuild_db.py"
                  " only TRUNCATEs and does NOT drop GRANTs - so suspect a new database")
        log.error("  that never ran read-only-api.sql, or a manual DROP SCHEMA,")
        log.error("  and grants come back only from docker/read-only-api.sql, which runs"
                  " ONLY through the `api-db-init` container (`restart: \"no\"`).")
    log.error("  ")
    log.error("  FIX:  docker compose up -d api")
    log.error("  ")
    log.error("  Grants are NOT restored here - ON PURPOSE. The problem is not that grants"
              " were removed, it is that NOBODY WAS TOLD.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
