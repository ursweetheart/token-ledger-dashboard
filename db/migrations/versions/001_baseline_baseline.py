"""baseline - toan bo schema tai thoi diem 24/08/2026

Revision ID: 001_baseline
Revises:
Create Date: 2026-08-24

Migration nay dung toan bo schema tu db/migrations/sql/001_baseline.sql - ban chep
DONG BANG cua db/01_schema.sql (749 dong, than file trung khit tung byte).

VI SAO SQL NAM O FILE RIENG, KHONG NHET VAO CHUOI PYTHON
---------------------------------------------------------
File .sql do khong chi la DDL. No la TRI NHO THIET KE cua du an: moi cot deu co
ghi chu tieng Viet noi VI SAO no ton tai, cai bay nao da cat, con so nao da do.
Nhet 749 dong do vao mot chuoi Python la bien tai lieu thanh du lieu - khong con
to mau cu phap, khong grep ra duoc, khong ai doc nua.

VI SAO DI THANG XUONG CON TRO DBAPI
------------------------------------
File nay co 11 dau `%` (trong ghi chu tieng Viet: "12,4%", "85,6%"...) va mot
`LIKE '%token_count'`. Hai duong hien nhien deu HONG vi chung, va da do that:

    op.execute(chuoi)              -> qua SQLAlchemy text(); `:ten` thanh tham so
                                      buoc, `%` di qua paramstyle pyformat
    exec_driver_sql(chuoi)         -> TypeError: immutabledict is not a sequence
                                      (van day mot dict rong xuong driver)
    exec_driver_sql(chuoi, ())     -> co tham so = BAT nooi suy `%`, va 11 dau
                                      phan tram kia vo

psycopg2 chi bo qua `%` khi goi execute() KHONG co doi so thu hai. Nen phai lay
ket noi DBAPI that roi goi thang - dung cach `db/connect.py:run_sql_file()` da
lam san, va cung la ly do ham do ton tai.

FORWARD-ONLY
------------
Khong co migration lui. Xem downgrade() ben duoi.
"""

from pathlib import Path

from alembic import op

# revision identifiers, used by Alembic.
revision = "001_baseline"
down_revision = None
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "001_baseline.sql"


def upgrade() -> None:
    bind = op.get_bind()
    sql = SQL.read_text(encoding="utf-8")
    raw = bind.connection          # ket noi DBAPI that: psycopg2 hoac sqlite3

    if bind.dialect.name == "sqlite":
        # sqlite3.execute() chi chay MOT cau lenh; nhieu cau phai dung
        # executescript. Giu nhanh nay vi migration cua du an nay bat buoc
        # trung lap hai he (task 3.5) - duong SQLite chua bi go.
        raw.executescript(sql)
    else:
        with raw.cursor() as cur:
            cur.execute(sql)       # KHONG doi so thu hai - xem ghi chu dau file


def downgrade() -> None:
    raise NotImplementedError(
        "Change `change-the-schema-without-dropping-it` chon FORWARD-ONLY.\n"
        "\n"
        "Migration lui thuong duoc viet ma khong bao gio chay, nen den luc can thi\n"
        "no sai. Voi doi 3 nguoi thi ban luu truoc khi chay re hon va that hon.\n"
        "\n"
        "Muon go mot thay doi schema: THEM mot migration TIEN de go no.\n"
        "Muon quay ve truoc mot moc: dung lai database tu `data/` (nhung nho rang\n"
        "tu ngay Gateway ghi dong dau tien, dong gateway KHONG co ban sao o `data/`)."
    )
