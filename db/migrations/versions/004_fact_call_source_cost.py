"""fact_call don nguon thu tu: them cot source va cost_usd

Revision ID: 004_fact_call_src
Revises: 003_rehearsal_drop
Create Date: 2026-08-31

MIGRATION DAU TIEN MANG GIA TRI NGHIEP VU

002 va 003 la dien tap. Day la lan dau nang luc "doi schema tai cho" duoc dung
that: change `load-the-gateway-ledger-into-the-database` can fact_call phan biet
duoc dong nao cua app, dong nao cua Gateway.

Xem db/migrations/sql/004_fact_call_source_cost.sql de biet vi sao khong nap
thang duoc, va vi sao `source` co DEFAULT con `cost_usd` thi khong.
"""

from pathlib import Path

from alembic import op

revision = "004_fact_call_src"
down_revision = "003_rehearsal_drop"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "004_fact_call_source_cost.sql"


def upgrade() -> None:
    raw = op.get_bind().connection          # ket noi DBAPI that (psycopg2)
    with raw.cursor() as cur:
        cur.execute(SQL.read_text(encoding="utf-8"))   # KHONG doi so thu hai


def downgrade() -> None:
    raise NotImplementedError(
        "Change `change-the-schema-without-dropping-it` chon FORWARD-ONLY.\n"
        "Muon go hai cot nay thi viet mot migration TIEN moi, khong dung downgrade."
    )
