"""mot con so do tre cho moi (ngay, agent) - chon chu khong trung binh

Revision ID: 010_latency_resolved
Revises: 009_chieu_account
Create Date: 2026-09-03

Them view `latency_resolved`. Tu migration 008, `fact_latency_daily` co the co
HAI dong cho cung mot (ngay, agent) - mot cua monitoring, mot cua gateway. Do la
dung o tang du lieu, nhung tang doc chua chiu noi: api.js:187 GAN DE tren khoa
`day|agent_id` khong co `source`, va store.py sap xep khong co tie-break tren
nguon. Hai dong cho cung khoa thi dong den SAU thang, va khong ai biet la dong nao.

THU TU UU TIEN: monitoring truoc gateway - LUA CHON TAM, nam trong DUNG MOT
`CASE`. Xem db/migrations/sql/010_latency_resolved.sql de biet ly le va phep do
se tra loi cho no.
"""

from pathlib import Path

from alembic import op

revision = "010_latency_resolved"
down_revision = "009_chieu_account"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "010_latency_resolved.sql"


def upgrade() -> None:
    raw = op.get_bind().connection          # ket noi DBAPI that (psycopg2)
    with raw.cursor() as cur:
        cur.execute(SQL.read_text(encoding="utf-8"))   # KHONG doi so thu hai


def downgrade() -> None:
    raise NotImplementedError(
        "Change `change-the-schema-without-dropping-it` chon FORWARD-ONLY.\n"
        "Muon go view nay thi viet mot migration TIEN moi."
    )
