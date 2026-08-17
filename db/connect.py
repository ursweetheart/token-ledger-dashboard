"""Mở kết nối và dựng lại database - dùng chung cho mọi script nạp.

HAI HỆ QUẢN TRỊ, MỘT BẢN SCHEMA
-------------------------------
01_schema.sql chạy được cả PostgreSQL lẫn SQLite vì không dùng SERIAL: mọi khoá
đều gán tường minh. Nhờ vậy dựng được một bản SQLite để đối chiếu độc lập, rồi
đổi sang Postgres mà không sửa dòng SQL nào.

Cách chọn: đuôi .sqlite / .db -> SQLite. Còn lại -> chuỗi kết nối PostgreSQL.

MẶC ĐỊNH LÀ POSTGRESQL
----------------------
Trước 17/08/2026 mặc định là một file SQLite trong var/. Đổi vì SQLite là MỘT
FILE: nó không đi qua mạng nên tiến trình trong container khác không đọc được,
và nó không có schema riêng lẫn GRANT theo user nên không chia quyền theo service
được. Cả hai là chặn đường cứng cho việc chạy nhiều bản sau một load balancer.

SQLite vẫn mở được, nhưng phải chỉ định tường minh - nó là đường đối chiếu bằng
tay, không còn là database của dự án.

MỘT NGUỒN SỰ THẬT
-----------------
DEFAULT_DSN dưới đây là chỗ DUY NHẤT quyết định database mặc định. Không file nào
khác được dựng chuỗi kết nối mặc định của riêng nó.

Đã có sự cố đúng hình dạng đó: scripts/rebuild_db.py từng khai
`default=str(ROOT / "var" / "token_ledger.sqlite")` độc lập với hằng số này, và
scripts/update_dashboard.py gọi nó KHÔNG truyền --db. Hệ quả: đổi file này xong
mà đường ống vẫn dựng lại database cũ, không lỗi nào báo ra.

Thứ tự ưu tiên:
    1. TOKEN_LEDGER_DSN        - đổi được TOÀN BỘ hệ thống bằng một biến
    2. PG* dựng thành chuỗi    - khớp tên biến của docker-compose.yml
    3. --db trên dòng lệnh     - ghi đè cho một lần chạy
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "db"                # ma: schema .sql + cac module nap
VAR_DIR = ROOT / "var"              # noi DUY NHAT duoc chua SQLite doi chieu

# Tên biến VÀ giá trị mặc định KHỚP docker-compose.yml, nên `docker compose up -d`
# rồi chạy script là nối được ngay, không phải đặt gì. Đặt tên khác sẽ thành hai
# bộ cấu hình phải giữ khớp bằng tay - đúng loại lỗi im lặng mà file này đang dọn.
PG_HOST = os.environ.get("PGHOST", "127.0.0.1")
PG_PORT = os.environ.get("PGPORT", "5432")
PG_USER = os.environ.get("PGUSER", "token")
PG_PASSWORD = os.environ.get("PGPASSWORD", "token_local")
PG_DATABASE = os.environ.get("PGDATABASE", "token_ledger")

# Dùng `or` chứ không `os.environ.get(k, mac_dinh)`: biến đặt thành chuỗi rỗng
# cũng phải rơi về mặc định, không được thành DSN rỗng.
DEFAULT_DSN = os.environ.get("TOKEN_LEDGER_DSN") or (
    f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}")

# Đường quay về SQLite, để thông báo lỗi và tài liệu trỏ vào một chỗ.
SQLITE_DSN = str(VAR_DIR / "token_ledger.sqlite")


def is_sqlite(dsn: str) -> bool:
    return dsn.endswith(".sqlite") or dsn.endswith(".db")


def mask_dsn(dsn: str) -> str:
    """Giấu mật khẩu khi in DSN ra màn hình hoặc log.

    Nơi nào biết DSN thì nơi đó phải biết cách in DSN an toàn - nên hàm này nằm
    cạnh DEFAULT_DSN chứ không nằm trong script gọi. Hai bản cài đặt của cùng một
    quy tắc bảo mật là một bản sẽ sai.

    Trước 17/08 mặc định là đường dẫn file nên in thẳng vô hại, và
    db/load_billing.py in `args.db` không che. Khi mặc định thành chuỗi Postgres
    có mật khẩu thì chính dòng đó thành chỗ rò.

    DSN là đường dẫn file thì trả về y nguyên, không cắt gì.

    CẮT Ở '@' CUỐI, KHÔNG PHẢI '@' ĐẦU
    ----------------------------------
    Mật khẩu được phép chứa '@'. Với `postgresql://u:p@ss@may/db`, cắt ở '@' đầu
    cho credentials='u:p' và host='ss@may/db' - tức đoạn 'ss' của mật khẩu CHẢY
    SANG vế host rồi được in ra nguyên văn. Phần host của URL thì không bao giờ
    chứa '@', nên cắt ở '@' cuối mới đúng.
    """
    if "://" not in dsn or "@" not in dsn:
        return dsn
    scheme, rest = dsn.split("://", 1)
    credentials, host = rest.rsplit("@", 1)
    # Không có ':' nghĩa là DSN vốn không mang mật khẩu - đừng thêm '***' vào,
    # người đọc log sẽ tưởng có một mật khẩu mà thực ra không có.
    if ":" not in credentials:
        return f"{scheme}://{credentials}@{host}"
    user = credentials.split(":", 1)[0]
    return f"{scheme}://{user}:***@{host}"


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
                "  (từ 17/08/2026 PostgreSQL là mặc định, nên gói này BẮT BUỘC)\n"
                f"Hoặc dựng một bản SQLite để đối chiếu:  --db {SQLITE_DSN}"
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
