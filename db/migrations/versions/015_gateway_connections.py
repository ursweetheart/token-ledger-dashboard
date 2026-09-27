"""Additive connection administration state, separate from ledger facts."""
from pathlib import Path
from alembic import op

revision = '015_gateway_connections'
down_revision = '014_gateway_agent_registry'
branch_labels = None
depends_on = None


def upgrade():
    sql = Path(__file__).resolve().parents[1] / 'sql' / '015_gateway_connections.sql'
    with op.get_bind().connection.cursor() as cur:
        cur.execute(sql.read_text(encoding='utf-8'))


def downgrade():
    raise NotImplementedError('Disable connection administration; retain audit and history.')
