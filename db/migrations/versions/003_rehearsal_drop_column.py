"""dien tap 8.6 - go cot vua them, bang mot buoc TIEN

Revision ID: 003_rehearsal_drop
Revises: 002_rehearsal_add
Create Date: 2026-08-26

Cap 002/003 la bang chung cua task 8.6: schema doi duoc TAI CHO tren database
dang co du lieu that, ca chieu them lan chieu go, ma 23 con so moc khong suy
suyen mot token.

Do lan luot ngay 26/08/2026 tren token_ledger_v2 (867.657.110 token):
    truoc 002   23/23 khop
    sau  002    23/23 khop, fact_usage_daily 11 -> 12 cot
    sau  003    23/23 khop, fact_usage_daily 12 -> 11 cot

Khong co downgrade. Xem db/migrations/sql/003_rehearsal_drop_column.sql.
"""

from pathlib import Path

from alembic import op

revision = "003_rehearsal_drop"
down_revision = "002_rehearsal_add"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "003_rehearsal_drop_column.sql"


def upgrade() -> None:
    raw = op.get_bind().connection          # ket noi DBAPI that (psycopg2)
    with raw.cursor() as cur:
        cur.execute(SQL.read_text(encoding="utf-8"))   # KHONG doi so thu hai


def downgrade() -> None:
    raise NotImplementedError(
        "Change `change-the-schema-without-dropping-it` chon FORWARD-ONLY.\n"
        "Muon co lai cot rehearsal_marker: them mot migration TIEN moi."
    )
