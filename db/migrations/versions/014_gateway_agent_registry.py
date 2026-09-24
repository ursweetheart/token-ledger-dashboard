"""Incremental Gateway agent registration and observed identities."""
from pathlib import Path
from alembic import op

revision = "014_gateway_agent_registry"
down_revision = "013_model_catalog_pricing"
branch_labels = None
depends_on = None


def upgrade():
    sql = Path(__file__).resolve().parents[1] / "sql" / "014_gateway_agent_registry.sql"
    with op.get_bind().connection.cursor() as cur:
        cur.execute(sql.read_text(encoding="utf-8"))


def downgrade():
    raise NotImplementedError("Retain Gateway identities and history; stop the worker instead.")
