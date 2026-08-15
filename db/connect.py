"""Mở kết nối và dựng lại database - dùng chung cho mọi script nạp.

HAI HỆ QUẢN TRỊ, MỘT BẢN SCHEMA
-------------------------------
01_schema.sql chạy được cả PostgreSQL lẫn SQLite vì không dùng SERIAL: mọi khoá
đều gán tường minh. Nhờ vậy khi Docker chưa chạy vẫn kiểm được toàn bộ khâu nạp
bằng một file SQLite, rồi đổi sang Postgres mà không sửa dòng SQL nào.

Cách chọn: đuôi .sqlite / .db -> SQLite. Còn lại -> chuỗi kết nối PostgreSQL.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "db"
DEFAULT_DSN = str(DB_DIR / "token_ledger.sqlite")


def is_sqlite(dsn: str) -> bool:
    return dsn.endswith(".sqlite") or dsn.endswith(".db")


def open_db(dsn: str):
    """Trả về (connection, placeholder) với placeholder là '?' hoặc '%s'."""
    if is_sqlite(dsn):
        import sqlite3
        cn = sqlite3.connect(dsn)
        # SQLite MẶC ĐỊNH KHÔNG kiểm khoá ngoại. Không bật thì một model_id sai
        # vẫn nạp được, và chỉ lộ ra khi đổi sang Postgres.
        cn.execute("PRAGMA foreign_keys = ON")
        return cn, "?"
    try:
        import psycopg2 as pg
    except ImportError:
        try:
            import psycopg as pg  # type: ignore
        except ImportError:
            raise SystemExit(
                "Cần psycopg2 để nối PostgreSQL:  pip install psycopg2-binary\n"
                f"Hoặc dùng SQLite:  --db {DEFAULT_DSN}"
            )
    return pg.connect(dsn), "%s"


def run_sql_file(cn, placeholder: str, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    if placeholder == "?":
        cn.executescript(sql)
    else:
        with cn.cursor() as cur:
            cur.execute(sql)


def rebuild(dsn: str):
    """Xoá sạch rồi dựng lại từ 01_schema.sql + 02_catalog.sql.

    CHỈ dùng cho database do script này tạo ra. Không dùng lên database thật.
    """
    if is_sqlite(dsn):
        p = Path(dsn)
        if p.exists():
            p.unlink()
        cn, placeholder = open_db(dsn)
    else:
        cn, placeholder = open_db(dsn)
        with cn.cursor() as cur:
            cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        cn.commit()

    run_sql_file(cn, placeholder, DB_DIR / "01_schema.sql")
    catalog = DB_DIR / "02_catalog.sql"
    if not catalog.exists():
        raise SystemExit("Chưa có db/02_catalog.sql. Chạy: python db/gen_catalog.py")
    run_sql_file(cn, placeholder, catalog)
    cn.commit()
    return cn, placeholder


def query(cn, sql: str, params=()) -> list:
    """Chạy một câu SELECT, trả về toàn bộ kết quả. Dùng được cả hai hệ.

    SQLite cho `cur.execute(...)` trả về CHÍNH cursor, nên viết
    `cur.execute(...).fetchall()` hoặc lặp thẳng `for r in cur.execute(...)`
    đều chạy. psycopg2 thì `execute()` trả về None.

    Hai lối viết tiện tay đó là cái bẫy kinh điển: chạy trên SQLite thì ngon,
    đổi sang Postgres mới ném AttributeError - tức lộ ra ở đúng lúc chuyển hệ,
    là lúc ít muốn gặp bất ngờ nhất. Hàm này bịt hẳn nó lại.
    """
    cur = cn.cursor()
    # KHÔNG truyền tuple rỗng xuống. psycopg2 chỉ diễn giải '%' khi đối số tham
    # số KHÁC None - đưa () xuống thì câu `LIKE '%token_count'` bị hiểu là dấu
    # định dạng và ném IndexError. SQLite không có vấn đề này, nên lỗi chỉ lộ ra
    # trên Postgres.
    if params:
        cur.execute(sql, params)
    else:
        cur.execute(sql)
    return cur.fetchall()


def query_one(cn, sql: str, params=()):
    """Như query() nhưng trả về dòng đầu tiên, hoặc None."""
    rows = query(cn, sql, params)
    return rows[0] if rows else None


def insert_many(cn, placeholder: str, table: str, columns: list[str], rows: list) -> int:
    """Chèn nhiều dòng, dùng đường nhanh của từng hệ.

    executemany của psycopg2 gửi MỘT vòng mạng cho MỖI dòng. Với 562.307 dòng
    của fact_monitoring thì đó là hàng chục phút - và nó không hỏng, chỉ chậm,
    nên rất dễ tưởng là bình thường. execute_values gom nhiều dòng vào một câu
    INSERT, nhanh hơn vài chục lần.

    SQLite thì executemany vốn đã nhanh vì không qua mạng.
    """
    if not rows:
        return 0
    cur = cn.cursor()
    col_list = ",".join(columns)
    if placeholder == "%s":
        try:
            from psycopg2.extras import execute_values
        except ImportError:
            execute_values = None
        if execute_values is not None:
            execute_values(cur, f"INSERT INTO {table} ({col_list}) VALUES %s",
                           rows, page_size=1000)
            return len(rows)
    cur.executemany(
        f"INSERT INTO {table} ({col_list})"
        f" VALUES ({','.join([placeholder] * len(columns))})", rows)
    return len(rows)


def count_rows(cn, table: str) -> int:
    cur = cn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0]


def model_lookup(cn) -> dict[tuple[str, str], int]:
    """(source, raw_name) -> model_id, đọc từ dim_model_alias."""
    cur = cn.cursor()
    cur.execute("SELECT source, raw_name, model_id FROM dim_model_alias")
    return {(s, r): m for s, r, m in cur.fetchall()}


def agent_lookup(cn) -> dict[str, int]:
    """gcp_project_id -> agent_id.

    Trước đây mọi truy vấn trên fact_billing_daily/fact_monitoring phải tự viết
    `JOIN dim_agent ON gcp_project_id = project`. Quên một chỗ là mất dòng,
    không lỗi nào báo. Nay agent_id là cột thật trong hai bảng đó, và hàm này là
    chỗ duy nhất làm phép tra cứu - lúc nạp.
    """
    cur = cn.cursor()
    cur.execute("SELECT gcp_project_id, agent_id FROM dim_agent"
                " WHERE gcp_project_id IS NOT NULL")
    return {p: a for p, a in cur.fetchall()}


def metric_lookup(cn) -> dict[tuple[str, str], tuple]:
    """(source, raw_name) -> (measures, kind), đọc từ dim_metric_alias.

    Thay cho việc đoán tên: regex trên sku_name, và LIKE '%token_count'.
    """
    cur = cn.cursor()
    cur.execute("SELECT source, raw_name, measures, kind FROM dim_metric_alias")
    return {(s, r): (m, k) for s, r, m, k in cur.fetchall()}
