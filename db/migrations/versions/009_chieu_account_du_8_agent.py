"""chieu account phu du ca 8 agent, khong chi 2

Revision ID: 009_chieu_account
Revises: 008_theo_gio
Create Date: 2026-09-03

Them view `usage_by_account_resolved`. Giu nguyen `usage_by_account` cu - hai
view tra loi HAI cau hoi khac nhau, va hai cong cu o tools/ doc view cu lam moc
lich su.

Do 03/09/2026:
    view cu   337 dong · 2 AGENT · 53 account
    view moi  1.453 dong · 8 AGENT · 60 account
              token 915.969.971 = usage_resolved   DAT
              calls     122.504 = usage_resolved   DAT

Xem db/migrations/sql/009_chieu_account_du_8_agent.sql de biet vi sao KHONG sua
view cu, va vi sao phai JOIN HAI LAN.
"""

from pathlib import Path

from alembic import op

revision = "009_chieu_account"
down_revision = "008_theo_gio"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "009_chieu_account_du_8_agent.sql"


def upgrade() -> None:
    raw = op.get_bind().connection          # ket noi DBAPI that (psycopg2)
    with raw.cursor() as cur:
        cur.execute(SQL.read_text(encoding="utf-8"))   # KHONG doi so thu hai


def downgrade() -> None:
    raise NotImplementedError(
        "Change `change-the-schema-without-dropping-it` chon FORWARD-ONLY.\n"
        "Muon go view nay thi viet mot migration TIEN moi."
    )
