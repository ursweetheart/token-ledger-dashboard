"""Tai tao database SQLite hien co sang PostgreSQL - ban sao 1:1.

CONG CU PHU, KHONG NAM TREN DUONG CHINH
---------------------------------------
Tu 17/08/2026 PostgreSQL la mac dinh, va duong chinh de dung database la:

    docker compose up -d
    python scripts/rebuild_db.py        # nap THANG tu data/ vao PostgreSQL

File nay chi con dung khi muon chep nhanh giua hai database ma KHONG nap lai tu
data/. No doi hoi mot file SQLite lam nguon, nen sau khi var/token_ledger.sqlite
bi xoa thi phai dung mot ban SQLite truoc da.

    docker compose up -d
    pip install "psycopg[binary]"
    python scripts/copy_to_postgres.py

VI SAO CHEP BANG, KHONG CHAY LAI CAC SCRIPT NAP
-----------------------------------------------
(Ly do luc file nay duoc viet - GIO DA HET DUNG, giu lai de biet vi sao no ton tai.)
Chay lai db/load_*.py voi --db <dsn postgres> cung ra database dung, nhung no
dung lai tu DU LIEU NGUON. Neu mai kia thu muc data/ khong con day du thi khong
tai tao duoc nua. Chep thang tu file SQLite cho ra ban sao dung bang cai dang co
o day, va doi chieu duoc tung bang mot.

Da do 17/08/2026: duong nap thang vao PostgreSQL CHAY DUOC - ca 7 buoc dat
nghiem thu trong 56s, va ket qua khop tung dong voi ban sao chep tu SQLite.

Bang tho SQLite chi duoc MO CHE DO CHI DOC. Khong co duong nao trong file nay
ghi vao no.

THU TU NAP
----------
Suy bang topo tu khoa ngoai luc chay, khong go tay: them mot bang moi vao schema
thi script tu xep dung cho. Rieng dim_unit tu tro vao chinh no (parent_id) nen
trong bang do phai nap theo `level` tang dan.

KIEU DU LIEU
------------
SQLite khong co BOOLEAN that - no luu 0/1. Postgres thi co. Khong doi kieu thi
psycopg nem loi kieu ngay dong dau. Danh sach cot BOOLEAN doc tu PRAGMA chu
khong go tay.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "db" / "01_schema.sql"
SQLITE_DEFAULT = ROOT / "var" / "token_ledger.sqlite"

# Kieu duoc coi la so - dung de doi chieu tong sau khi chep.
#
# SO KHOP THEO TIEN TO, KHONG SO BANG TUYET DOI.
# PRAGMA tra ve kieu Y NGUYEN NHU DA KHAI, ke ca phan trong ngoac: schema viet
# `NUMERIC(14,6)` va `INT`, khong phai `NUMERIC` va `INTEGER`. Ban truoc so bang
# `kieu in KIEU_SO` nen bo qua HET:
#     chi_phi_usd  NUMERIC(14,6)   <- cot TIEN, thu quan trong nhat
#     ref_price    ca ba cot gia
#     moi cot INT  agent_id, model_id, so_luot...
# Nghia la phep "doi chieu tong moi cot so" van bao khop trong khi khong he cong
# thu cot nao trong so do. Bao dam gia, dung kieu nguy hiem nhat.
NUMERIC_TYPES = ("BIGINT", "NUMERIC", "DOUBLE PRECISION", "INTEGER", "INT", "REAL",
           "SMALLINT", "DECIMAL", "FLOAT")


def is_numeric_type(sql_type: str) -> bool:
    base = sql_type.split("(", 1)[0].strip().upper()
    return base in NUMERIC_TYPES
WARN = 5000


def split_statements(sql: str) -> list[str]:
    """Tach file .sql thanh tung cau lenh.

    psycopg2 chay duoc nhieu cau trong mot execute, psycopg3 thi KHONG (no dung
    extended protocol, chi nhan mot cau). Tach san o day thi ca hai thu vien deu
    chay duoc, khong bat nguoi dung phai cai dung ban.

    Tach bang dau ; la an toan voi file nay: 01_schema.sql chi co CREATE TABLE,
    CREATE INDEX va mot CREATE VIEW - khong co ham hay khoi DO $$ ... $$ nao.
    """
    clean: list[str] = []
    for rows in sql.splitlines():
        no_comment = rows.split("--", 1)[0]
        clean.append(no_comment)
    return [c.strip() for c in "\n".join(clean).split(";") if c.strip()]


def default_dsn() -> str:
    """Khop mac dinh trong docker-compose.yml."""
    return (f"postgresql://{os.environ.get('PGUSER', 'token')}:"
            f"{os.environ.get('PGPASSWORD', 'token_local')}@"
            f"{os.environ.get('PGHOST', '127.0.0.1')}:"
            f"{os.environ.get('PGPORT', '5432')}/"
            f"{os.environ.get('PGDATABASE', 'token_ledger')}")


def connect_postgres(dsn: str, wait_seconds: int):
    try:
        import psycopg2 as pg
        from psycopg2.extras import execute_values
    except ImportError:
        try:
            import psycopg as pg           # type: ignore
            execute_values = None
        except ImportError:
            raise SystemExit(
                "Chua co thu vien PostgreSQL. Cai mot trong hai:\n"
                "    pip install psycopg2-binary       (khuyen nghi)\n"
                "    pip install \"psycopg[binary]\"")

    done = time.time() + wait_seconds
    last_error = None
    while time.time() < done:
        try:
            return pg.connect(dsn), execute_values
        except Exception as e:                     # container chua san sang
            last_error = e
            time.sleep(2)
    raise SystemExit(
        f"Khong noi duoc PostgreSQL sau {wait_seconds}s: {last_error}\n"
        f"  Da chay `docker compose up -d` chua?\n"
        f"  Kiem: docker compose ps")


def schema_of(cn_lite) -> tuple[list[str], dict, dict]:
    """(thu tu nap, cot moi bang, kieu moi cot)."""
    table = [r[0] for r in cn_lite.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    cols, sql_type, covered = {}, {}, {}
    for b in table:
        info = list(cn_lite.execute(f"PRAGMA table_info({b})"))
        cols[b] = [r[1] for r in info]
        sql_type[b] = {r[1]: (r[2] or "").upper() for r in info}
        covered[b] = {r[2] for r in cn_lite.execute(f"PRAGMA foreign_key_list({b})")}

    finished, order = set(), []
    while len(order) < len(table):
        # `p == b` bo qua tu tham chieu: dim_unit tro vao chinh no, cho no chan
        # chinh no thi vong lap khong bao gio thoat.
        money = [b for b in table if b not in finished
                and all(p in finished or p == b for p in covered[b])]
        if not money:
            raise SystemExit(f"Khoa ngoai co vong lap: {sorted(set(table) - finished)}")
        for b in money:
            finished.add(b)
            order.append(b)
    return order, cols, sql_type


def read_rows(cn_lite, table: str, cols: list[str], bool_cols: list[int]):
    # dim_unit tu tro vao chinh no -> cha phai vao truoc con.
    sorted_tables = " ORDER BY level" if table == "dim_unit" else ""
    stmt = f"SELECT {','.join(cols)} FROM {table}{sorted_tables}"
    for rows in cn_lite.execute(stmt):
        if not bool_cols:
            yield rows
            continue
        d = list(rows)
        for i in bool_cols:
            if d[i] is not None:
                d[i] = bool(d[i])
        yield tuple(d)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--nguon", dest="source", default=str(SQLITE_DEFAULT), help="File .sqlite nguon")
    p.add_argument("--dich", dest="dest", default="", help="DSN PostgreSQL (mac dinh: theo docker-compose)")
    p.add_argument("--cho", dest="wait_seconds", type=int, default=60, help="So giay doi Postgres san sang")
    args = p.parse_args()

    source = Path(args.source)
    if not source.exists():
        raise SystemExit(f"Khong thay file nguon {source}")
    dsn = args.dest or default_dsn()

    # CHI DOC - khong co duong nao ghi vao file SQLite.
    cn_lite = sqlite3.connect(f"file:{source.resolve().as_posix()}?mode=ro", uri=True)
    order, cols, sql_type = schema_of(cn_lite)

    print(f"Nguon : {source}")
    print(f"Dich  : {dsn.rsplit('@', 1)[-1]}")     # khong in mat khau
    print(f"Bang  : {len(order)}\n")

    cn_pg, execute_values = connect_postgres(dsn, args.wait_seconds)
    cur = cn_pg.cursor()

    print("Dung lai schema tu db/01_schema.sql")
    cur.execute("DROP SCHEMA IF EXISTS public CASCADE")
    cur.execute("CREATE SCHEMA public")
    statements = split_statements(SCHEMA.read_text(encoding="utf-8"))
    for c in statements:
        cur.execute(c)
    cn_pg.commit()
    print(f"  {len(statements)} cau lenh DDL")

    total = 0
    for table in order:
        cols = cols[table]
        bool_cols = [i for i, c in enumerate(cols) if sql_type[table][c] == "BOOLEAN"]
        stmt = f'INSERT INTO {table} ({",".join(cols)}) VALUES %s'
        child_stmt = f'INSERT INTO {table} ({",".join(cols)}) VALUES ({",".join(["%s"] * len(cols))})'

        n, warn = 0, []
        for rows in read_rows(cn_lite, table, cols, bool_cols):
            warn.append(rows)
            if len(warn) >= WARN:
                if execute_values:
                    execute_values(cur, stmt, warn)
                else:
                    cur.executemany(child_stmt, warn)
                n += len(warn)
                warn = []
        if warn:
            if execute_values:
                execute_values(cur, stmt, warn)
            else:
                cur.executemany(child_stmt, warn)
            n += len(warn)
        cn_pg.commit()
        total += n
        print(f"  {table:<22} {n:>8,} dong")

    # ── doi chieu tung bang: so dong VA tong moi cot so ──
    print("\nDoi chieu SQLite <-> PostgreSQL")
    diff: list[str] = []
    for table in order:
        a = cn_lite.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        b = cur.fetchone()[0]
        if a != b:
            diff.append(f"{table}: so dong {a} != {b}")
            continue

        numeric_cols = [c for c in cols[table] if is_numeric_type(sql_type[table][c])]
        for c in numeric_cols:
            # 1) SUM voi sai so TUONG DOI, khong tuyet doi.
            #    fact_monitoring.gia_tri chua han muc quota = int64 max (9,2e18);
            #    tong len toi 8e22, ma o thang do buoc nho nhat cua double da la
            #    16,7 trieu. Hai he cong theo thu tu khac nhau nen chenh vai tram
            #    ULP la BINH THUONG, khong phai mat du lieu. Nguong tuyet doi
            #    1e-6 o day chi tao bao dong gia.
            x = cn_lite.execute(f"SELECT SUM({c}) FROM {table}").fetchone()[0]
            cur.execute(f"SELECT SUM({c}) FROM {table}")
            y = cur.fetchone()[0]
            if (x is None) != (y is None):
                diff.append(f"{table}.{c}: mot ben NULL ({x} / {y})")
            elif x is not None:
                big = max(abs(float(x)), abs(float(y)), 1.0)
                if abs(float(x) - float(y)) / big > 1e-9:
                    diff.append(f"{table}.{c}: tong {x} != {y}")

            # 2) So gia tri KHAC NHAU - khong phu thuoc thu tu cong chut nao.
            #    Bat duoc kieu hong ma SUM co the che giau (vi du hai dong doi
            #    gia tri cho nhau, hoac mot gia tri bi thay bang gia tri khac
            #    cung tong).
            x = cn_lite.execute(f"SELECT COUNT(DISTINCT {c}) FROM {table}").fetchone()[0]
            cur.execute(f"SELECT COUNT(DISTINCT {c}) FROM {table}")
            y = cur.fetchone()[0]
            if x != y:
                diff.append(f"{table}.{c}: so gia tri khac nhau {x} != {y}")
        print(f"  {table:<22} {a:>8,} dong, {len(numeric_cols)} cot so - khop")

    # Moi VIEW phai chay duoc tren Postgres, khong chi bang. Danh sach view doc
    # tu chinh schema chu KHONG go tay: ghim ten view thi them view moi la phep
    # doi chieu lang le bo qua no.
    views = [r[0] for r in cn_lite.execute(
        "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")]
    for v in views:
        a = cn_lite.execute(f"SELECT COUNT(*) FROM {v}").fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {v}")
        b = cur.fetchone()[0]
        if a != b:
            diff.append(f"view {v}: {a} != {b}")
        print(f"  {v + ' (view)':<22} {b:>8,} dong - {'khop' if a == b else 'LECH'}")

    if diff:
        print("\nKHONG KHOP:")
        for x in diff:
            print(f"  {x}")
        raise SystemExit(1)

    print(f"\nXONG. {total:,} dong tren {len(order)} bang, moi bang khop ca so dong lan tong so.")
    print("Mo pgAdmin: http://localhost:5050")


if __name__ == "__main__":
    main()
