"""fact_call ghi them ten model goc, khoa da goi va trang thai dem

Revision ID: 007_cot_bo_qua
Revises: 006_do_tre
Create Date: 2026-09-01

Ba cot nay da co san trong so Gateway ma khong dong ma nao doc toi. Hai cot la
truong BAT BUOC cua sheet Data Out; cot thu ba `cache_hit` co the lam phong so
token mot cach im lang khi bat cache.

Xem db/migrations/sql/007_cot_bi_bo_qua.sql de biet HAI CAI BAY nguoc nhau cua
`cache_hit` o hai dau duong nap.
"""

from pathlib import Path

from alembic import op

revision = "007_cot_bo_qua"
down_revision = "006_do_tre"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "007_cot_bi_bo_qua.sql"


def upgrade() -> None:
    raw = op.get_bind().connection          # ket noi DBAPI that (psycopg2)
    with raw.cursor() as cur:
        cur.execute(SQL.read_text(encoding="utf-8"))   # KHONG doi so thu hai


def downgrade() -> None:
    raise NotImplementedError(
        "Change `change-the-schema-without-dropping-it` chon FORWARD-ONLY.\n"
        "Muon go ba cot nay thi viet mot migration TIEN moi."
    )
