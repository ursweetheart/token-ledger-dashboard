"""Agent health schedule, and runs with their JSON result document."""
from pathlib import Path
from alembic import op

revision = '016_agent_health'
down_revision = '015_gateway_connections'
branch_labels = None
depends_on = None


def upgrade():
    sql = Path(__file__).resolve().parents[1] / 'sql' / '016_agent_health.sql'
    with op.get_bind().connection.cursor() as cur:
        cur.execute(sql.read_text(encoding='utf-8'))


def downgrade():
    raise NotImplementedError('Stop agent-health-watch; retain schedule and result history.')
