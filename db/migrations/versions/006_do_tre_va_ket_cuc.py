"""fact_call ghi them do tre, ket cuc va ma loi cua tung luot goi

Revision ID: 006_do_tre
Revises: 005_gateway_cost
Create Date: 2026-08-31

Dong muc Master Plan "Ghi du truong can cho dashboard ngay tai thoi diem goi"
(moc 21/09/2026): ban ghi moi request doi 12 truong, fact_call dang co 10.

Xem db/migrations/sql/006_do_tre_va_ket_cuc.sql de biet vi sao ba cot deu
nullable khong DEFAULT, va vi sao `outcome` KHONG duoc dat 'success' cho du
lieu cu.
"""

from pathlib import Path

from alembic import op

revision = "006_do_tre"
down_revision = "005_gateway_cost"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "006_do_tre_va_ket_cuc.sql"


def upgrade() -> None:
    raw = op.get_bind().connection          # ket noi DBAPI that (psycopg2)
    with raw.cursor() as cur:
        cur.execute(SQL.read_text(encoding="utf-8"))   # KHONG doi so thu hai


def downgrade() -> None:
    raise NotImplementedError(
        "Change `change-the-schema-without-dropping-it` chon FORWARD-ONLY.\n"
        "Muon go ba cot nay thi viet mot migration TIEN moi."
    )
