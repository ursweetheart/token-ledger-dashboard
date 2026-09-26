"""Append-only catalog pricing; no historical fact rewrites."""
from pathlib import Path
from alembic import op

revision = '013_model_catalog_pricing'
down_revision = '012_nhip_tim_lam_moi'
branch_labels = None
depends_on = None
SQL = Path(__file__).resolve().parents[1] / 'sql' / '013_model_catalog_pricing.sql'


def upgrade():
    with op.get_bind().connection.cursor() as cur:
        cur.execute(SQL.read_text(encoding='utf-8'))


def downgrade():
    raise NotImplementedError('Forward-only: disable pricing, retain history.')
