"""Mo ket noi va dung lai database - dung chung cho moi script nap.

HAI HE QUAN TRI, MOT BAN SCHEMA
-------------------------------
01_schema.sql chay duoc ca PostgreSQL lan SQLite vi khong dung SERIAL: moi khoa
deu gan tuong minh. Nho vay khi Docker chua chay van kiem duoc toan bo khau nap
bang mot file SQLite, roi doi sang Postgres ma khong sua dong SQL nao.

Cach chon: duoi .sqlite / .db -> SQLite. Con lai -> chuoi ket noi PostgreSQL.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db"
MAC_DINH = str(DB / "token_ledger.sqlite")


def la_sqlite(dsn: str) -> bool:
    return dsn.endswith(".sqlite") or dsn.endswith(".db")


def mo(dsn: str):
    """Tra ve (connection, dat_cho) voi dat_cho la '?' hoac '%s'."""
    if la_sqlite(dsn):
        import sqlite3
        cn = sqlite3.connect(dsn)
        # SQLite MAC DINH KHONG kiem khoa ngoai. Khong bat thi mot model_id sai
        # van nap duoc, va chi lo ra khi doi sang Postgres.
        cn.execute("PRAGMA foreign_keys = ON")
        return cn, "?"
    try:
        import psycopg2 as pg
    except ImportError:
        try:
            import psycopg as pg  # type: ignore
        except ImportError:
            raise SystemExit(
                "Can psycopg2 de noi PostgreSQL:  pip install psycopg2-binary\n"
                f"Hoac dung SQLite:  --db {MAC_DINH}"
            )
    return pg.connect(dsn), "%s"


def chay_file_sql(cn, dat_cho: str, duong_dan: Path) -> None:
    sql = duong_dan.read_text(encoding="utf-8")
    if dat_cho == "?":
        cn.executescript(sql)
    else:
        with cn.cursor() as cur:
            cur.execute(sql)


def dung_lai(dsn: str):
    """Xoa sach roi dung lai tu 01_schema.sql + 02_danh_muc.sql.

    CHI dung cho database do script nay tao ra. Khong dung len database that.
    """
    if la_sqlite(dsn):
        p = Path(dsn)
        if p.exists():
            p.unlink()
        cn, dat_cho = mo(dsn)
    else:
        cn, dat_cho = mo(dsn)
        with cn.cursor() as cur:
            cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        cn.commit()

    chay_file_sql(cn, dat_cho, DB / "01_schema.sql")
    danh_muc = DB / "02_danh_muc.sql"
    if not danh_muc.exists():
        raise SystemExit("Chua co db/02_danh_muc.sql. Chay: python db/sinh_02_danh_muc.py")
    chay_file_sql(cn, dat_cho, danh_muc)
    cn.commit()
    return cn, dat_cho


def truy(cn, cau: str, tham=()) -> list:
    """Chay mot cau SELECT, tra ve toan bo ket qua. Dung duoc ca hai he.

    SQLite cho `cur.execute(...)` tra ve CHINH cursor, nen viet
    `cur.execute(...).fetchall()` hoac lap thang `for r in cur.execute(...)`
    deu chay. psycopg2 thi `execute()` tra ve None.

    Hai loi viet tien tay do la cai bay kinh dien: chay tren SQLite thi ngon,
    doi sang Postgres moi nem AttributeError - tuc lo ra o dung luc chuyen he,
    la luc it muon gap bat ngo nhat. Ham nay bit han no lai.
    """
    cur = cn.cursor()
    # KHONG truyen tuple rong xuong. psycopg2 chi dien giai '%' khi doi so tham
    # so KHAC None - dua () xuong thi cau `LIKE '%token_count'` bi hieu la dau
    # dinh dang va nem IndexError. SQLite khong co van de nay, nen loi chi lo ra
    # tren Postgres.
    if tham:
        cur.execute(cau, tham)
    else:
        cur.execute(cau)
    return cur.fetchall()


def mot(cn, cau: str, tham=()):
    """Nhu truy() nhung tra ve dong dau tien, hoac None."""
    kq = truy(cn, cau, tham)
    return kq[0] if kq else None


def chen(cn, dc: str, bang: str, cot: list[str], dong: list) -> int:
    """Chen nhieu dong, dung duong nhanh cua tung he.

    executemany cua psycopg2 gui MOT vong mang cho MOI dong. Voi 562.307 dong
    cua fact_monitoring thi do la hang chuc phut - va no khong hong, chi cham,
    nen rat de tuong la binh thuong. execute_values gom nhieu dong vao mot cau
    INSERT, nhanh hon vai chuc lan.

    SQLite thi executemany von da nhanh vi khong qua mang.
    """
    if not dong:
        return 0
    cur = cn.cursor()
    ten_cot = ",".join(cot)
    if dc == "%s":
        try:
            from psycopg2.extras import execute_values
        except ImportError:
            execute_values = None
        if execute_values is not None:
            execute_values(cur, f"INSERT INTO {bang} ({ten_cot}) VALUES %s",
                           dong, page_size=1000)
            return len(dong)
    cur.executemany(
        f"INSERT INTO {bang} ({ten_cot}) VALUES ({','.join([dc] * len(cot))})", dong)
    return len(dong)


def dem(cn, bang: str) -> int:
    cur = cn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {bang}")
    return cur.fetchone()[0]


def tra_model(cn) -> dict[tuple[str, str], int]:
    """(nguon, ten_goc) -> model_id, doc tu dim_model_alias."""
    cur = cn.cursor()
    cur.execute("SELECT nguon, ten_goc, model_id FROM dim_model_alias")
    return {(n, t): m for n, t, m in cur.fetchall()}
