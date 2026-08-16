"""Tai tao database SQLite hien co sang PostgreSQL - ban sao 1:1.

    docker compose up -d
    pip install "psycopg[binary]"
    python scripts/tai_tao_postgres.py

VI SAO CHEP BANG, KHONG CHAY LAI CAC SCRIPT NAP
-----------------------------------------------
Chay lai db/load_*.py voi --db <dsn postgres> cung ra database dung, nhung no
dung lai tu DU LIEU NGUON. Neu mai kia thu muc data/ khong con day du thi khong
tai tao duoc nua. Chep thang tu file SQLite cho ra ban sao dung bang cai dang co
o day, va doi chieu duoc tung bang mot.

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
SQLITE_MAC_DINH = ROOT / "var" / "token_ledger.sqlite"

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
KIEU_SO = ("BIGINT", "NUMERIC", "DOUBLE PRECISION", "INTEGER", "INT", "REAL",
           "SMALLINT", "DECIMAL", "FLOAT")


def la_kieu_so(kieu: str) -> bool:
    goc = kieu.split("(", 1)[0].strip().upper()
    return goc in KIEU_SO
LO = 5000


def tach_cau_lenh(sql: str) -> list[str]:
    """Tach file .sql thanh tung cau lenh.

    psycopg2 chay duoc nhieu cau trong mot execute, psycopg3 thi KHONG (no dung
    extended protocol, chi nhan mot cau). Tach san o day thi ca hai thu vien deu
    chay duoc, khong bat nguoi dung phai cai dung ban.

    Tach bang dau ; la an toan voi file nay: 01_schema.sql chi co CREATE TABLE,
    CREATE INDEX va mot CREATE VIEW - khong co ham hay khoi DO $$ ... $$ nao.
    """
    sach: list[str] = []
    for dong in sql.splitlines():
        khong_chu_thich = dong.split("--", 1)[0]
        sach.append(khong_chu_thich)
    return [c.strip() for c in "\n".join(sach).split(";") if c.strip()]


def dsn_mac_dinh() -> str:
    """Khop mac dinh trong docker-compose.yml."""
    return (f"postgresql://{os.environ.get('PGUSER', 'token')}:"
            f"{os.environ.get('PGPASSWORD', 'token_local')}@"
            f"{os.environ.get('PGHOST', '127.0.0.1')}:"
            f"{os.environ.get('PGPORT', '5432')}/"
            f"{os.environ.get('PGDATABASE', 'token_ledger')}")


def noi_postgres(dsn: str, cho_giay: int):
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

    het = time.time() + cho_giay
    loi_cuoi = None
    while time.time() < het:
        try:
            return pg.connect(dsn), execute_values
        except Exception as e:                     # container chua san sang
            loi_cuoi = e
            time.sleep(2)
    raise SystemExit(
        f"Khong noi duoc PostgreSQL sau {cho_giay}s: {loi_cuoi}\n"
        f"  Da chay `docker compose up -d` chua?\n"
        f"  Kiem: docker compose ps")


def cau_truc(cn_lite) -> tuple[list[str], dict, dict]:
    """(thu tu nap, cot moi bang, kieu moi cot)."""
    bang = [r[0] for r in cn_lite.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    cot, kieu, phu = {}, {}, {}
    for b in bang:
        info = list(cn_lite.execute(f"PRAGMA table_info({b})"))
        cot[b] = [r[1] for r in info]
        kieu[b] = {r[1]: (r[2] or "").upper() for r in info}
        phu[b] = {r[2] for r in cn_lite.execute(f"PRAGMA foreign_key_list({b})")}

    xong, thu_tu = set(), []
    while len(thu_tu) < len(bang):
        # `p == b` bo qua tu tham chieu: dim_unit tro vao chinh no, cho no chan
        # chinh no thi vong lap khong bao gio thoat.
        tien = [b for b in bang if b not in xong
                and all(p in xong or p == b for p in phu[b])]
        if not tien:
            raise SystemExit(f"Khoa ngoai co vong lap: {sorted(set(bang) - xong)}")
        for b in tien:
            xong.add(b)
            thu_tu.append(b)
    return thu_tu, cot, kieu


def doc_dong(cn_lite, bang: str, cot: list[str], bool_cot: list[int]):
    # dim_unit tu tro vao chinh no -> cha phai vao truoc con.
    sap = " ORDER BY level" if bang == "dim_unit" else ""
    cau = f"SELECT {','.join(cot)} FROM {bang}{sap}"
    for dong in cn_lite.execute(cau):
        if not bool_cot:
            yield dong
            continue
        d = list(dong)
        for i in bool_cot:
            if d[i] is not None:
                d[i] = bool(d[i])
        yield tuple(d)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--nguon", default=str(SQLITE_MAC_DINH), help="File .sqlite nguon")
    p.add_argument("--dich", default="", help="DSN PostgreSQL (mac dinh: theo docker-compose)")
    p.add_argument("--cho", type=int, default=60, help="So giay doi Postgres san sang")
    args = p.parse_args()

    nguon = Path(args.nguon)
    if not nguon.exists():
        raise SystemExit(f"Khong thay file nguon {nguon}")
    dsn = args.dich or dsn_mac_dinh()

    # CHI DOC - khong co duong nao ghi vao file SQLite.
    cn_lite = sqlite3.connect(f"file:{nguon.resolve().as_posix()}?mode=ro", uri=True)
    thu_tu, cot, kieu = cau_truc(cn_lite)

    print(f"Nguon : {nguon}")
    print(f"Dich  : {dsn.rsplit('@', 1)[-1]}")     # khong in mat khau
    print(f"Bang  : {len(thu_tu)}\n")

    cn_pg, execute_values = noi_postgres(dsn, args.cho)
    cur = cn_pg.cursor()

    print("Dung lai schema tu db/01_schema.sql")
    cur.execute("DROP SCHEMA IF EXISTS public CASCADE")
    cur.execute("CREATE SCHEMA public")
    cau_lenh = tach_cau_lenh(SCHEMA.read_text(encoding="utf-8"))
    for c in cau_lenh:
        cur.execute(c)
    cn_pg.commit()
    print(f"  {len(cau_lenh)} cau lenh DDL")

    tong = 0
    for bang in thu_tu:
        cols = cot[bang]
        bool_cot = [i for i, c in enumerate(cols) if kieu[bang][c] == "BOOLEAN"]
        cau = f'INSERT INTO {bang} ({",".join(cols)}) VALUES %s'
        cau_em = f'INSERT INTO {bang} ({",".join(cols)}) VALUES ({",".join(["%s"] * len(cols))})'

        n, lo = 0, []
        for dong in doc_dong(cn_lite, bang, cols, bool_cot):
            lo.append(dong)
            if len(lo) >= LO:
                if execute_values:
                    execute_values(cur, cau, lo)
                else:
                    cur.executemany(cau_em, lo)
                n += len(lo)
                lo = []
        if lo:
            if execute_values:
                execute_values(cur, cau, lo)
            else:
                cur.executemany(cau_em, lo)
            n += len(lo)
        cn_pg.commit()
        tong += n
        print(f"  {bang:<22} {n:>8,} dong")

    # ── doi chieu tung bang: so dong VA tong moi cot so ──
    print("\nDoi chieu SQLite <-> PostgreSQL")
    lech: list[str] = []
    for bang in thu_tu:
        a = cn_lite.execute(f"SELECT COUNT(*) FROM {bang}").fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {bang}")
        b = cur.fetchone()[0]
        if a != b:
            lech.append(f"{bang}: so dong {a} != {b}")
            continue

        cot_so = [c for c in cot[bang] if la_kieu_so(kieu[bang][c])]
        for c in cot_so:
            # 1) SUM voi sai so TUONG DOI, khong tuyet doi.
            #    fact_monitoring.gia_tri chua han muc quota = int64 max (9,2e18);
            #    tong len toi 8e22, ma o thang do buoc nho nhat cua double da la
            #    16,7 trieu. Hai he cong theo thu tu khac nhau nen chenh vai tram
            #    ULP la BINH THUONG, khong phai mat du lieu. Nguong tuyet doi
            #    1e-6 o day chi tao bao dong gia.
            x = cn_lite.execute(f"SELECT SUM({c}) FROM {bang}").fetchone()[0]
            cur.execute(f"SELECT SUM({c}) FROM {bang}")
            y = cur.fetchone()[0]
            if (x is None) != (y is None):
                lech.append(f"{bang}.{c}: mot ben NULL ({x} / {y})")
            elif x is not None:
                lon = max(abs(float(x)), abs(float(y)), 1.0)
                if abs(float(x) - float(y)) / lon > 1e-9:
                    lech.append(f"{bang}.{c}: tong {x} != {y}")

            # 2) So gia tri KHAC NHAU - khong phu thuoc thu tu cong chut nao.
            #    Bat duoc kieu hong ma SUM co the che giau (vi du hai dong doi
            #    gia tri cho nhau, hoac mot gia tri bi thay bang gia tri khac
            #    cung tong).
            x = cn_lite.execute(f"SELECT COUNT(DISTINCT {c}) FROM {bang}").fetchone()[0]
            cur.execute(f"SELECT COUNT(DISTINCT {c}) FROM {bang}")
            y = cur.fetchone()[0]
            if x != y:
                lech.append(f"{bang}.{c}: so gia tri khac nhau {x} != {y}")
        print(f"  {bang:<22} {a:>8,} dong, {len(cot_so)} cot so - khop")

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
            lech.append(f"view {v}: {a} != {b}")
        print(f"  {v + ' (view)':<22} {b:>8,} dong - {'khop' if a == b else 'LECH'}")

    if lech:
        print("\nKHONG KHOP:")
        for x in lech:
            print(f"  {x}")
        raise SystemExit(1)

    print(f"\nXONG. {tong:,} dong tren {len(thu_tu)} bang, moi bang khop ca so dong lan tong so.")
    print("Mo pgAdmin: http://localhost:5050")


if __name__ == "__main__":
    main()
