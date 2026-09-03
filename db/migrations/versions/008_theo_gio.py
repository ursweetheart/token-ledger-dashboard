"""do min theo gio, va hai bang phan vi biet minh den tu nguon nao

Revision ID: 008_theo_gio
Revises: 007_cot_bo_qua
Create Date: 2026-09-03

Ba viec, gop chung vi cung phuc vu STT 4 muc tieu 2 cua Master Plan:

  (1) fact_call ghi them output_modality va thinking_enabled - hai truong Data
      Out con thieu, ca hai nam trong CUNG khoi completion_tokens_details.
  (2) fact_latency_daily va fact_perf_daily co cot `source`, vao ca KHOA CHINH.
      Phai lam TRUOC khi do phan vi Gateway vao, neu khong thi hai phep do khac
      han ban chat nam chung mot cot ma khong ai phan biet duoc.
  (3) fact_usage_hourly - bang tong hop theo gio, KHONG co nguon `billing`.

Xem db/migrations/sql/008_theo_gio.sql de biet ly le tung cot.
"""

from pathlib import Path

from alembic import op

revision = "008_theo_gio"
down_revision = "007_cot_bo_qua"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "008_theo_gio.sql"


def upgrade() -> None:
    raw = op.get_bind().connection          # ket noi DBAPI that (psycopg2)
    with raw.cursor() as cur:
        cur.execute(SQL.read_text(encoding="utf-8"))   # KHONG doi so thu hai


def downgrade() -> None:
    raise NotImplementedError(
        "Change `change-the-schema-without-dropping-it` chon FORWARD-ONLY.\n"
        "Muon go nhung thu nay thi viet mot migration TIEN moi."
    )
