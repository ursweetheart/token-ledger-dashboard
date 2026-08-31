"""usage_resolved.cost_usd nhan them tien cua Gateway

Revision ID: 005_gateway_cost
Revises: 004_fact_call_src
Create Date: 2026-08-31

Quyet dinh nay DAO NGUOC mot quyet dinh cua baseline 001 va THAY THE mot yeu cau
spec cua change `label-derived-cost-across-dashboard`. Ly do, danh doi va he qua
nam trong db/migrations/sql/005_gateway_cost_vao_view.sql - doc truoc khi sua tiep.
"""

from pathlib import Path

from alembic import op

revision = "005_gateway_cost"
down_revision = "004_fact_call_src"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "005_gateway_cost_vao_view.sql"


def upgrade() -> None:
    raw = op.get_bind().connection          # ket noi DBAPI that (psycopg2)
    with raw.cursor() as cur:
        cur.execute(SQL.read_text(encoding="utf-8"))   # KHONG doi so thu hai


def downgrade() -> None:
    raise NotImplementedError(
        "Change `change-the-schema-without-dropping-it` chon FORWARD-ONLY.\n"
        "Muon quay ve chi lay tien hoa don thi viet mot migration TIEN moi."
    )
