"""dien tap 8.6 - them mot cot nullable vo hai

Revision ID: 002_rehearsal_add
Revises: 001_baseline
Create Date: 2026-08-26

VI SAO MOT MIGRATION KHONG MANG GIA TRI NGHIEP VU LAI NAM TRONG LICH SU

Task 8.6 doi chung minh nang luc "doi schema tai cho, giu nguyen du lieu" tren
database THAT, chu khong phai tren mot ban thu. Cach duy nhat de chung minh la
lam that mot lan, roi do lai 23 con so moc.

Gia phai tra: lich su migration co them hai ban ghi (002 va 003) khong lam gi
cho nghiep vu. Do la gia DUNG - lich su migration von chi duoc them, khong duoc
sua, va hai dong nay la bang chung ngay nang luc do duoc chung minh.

Xem db/migrations/sql/002_rehearsal_add_column.sql de biet vi sao chon
fact_usage_daily va vi sao cot phai nullable khong default.
"""

from pathlib import Path

from alembic import op

revision = "002_rehearsal_add"
down_revision = "001_baseline"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "002_rehearsal_add_column.sql"


def upgrade() -> None:
    raw = op.get_bind().connection          # ket noi DBAPI that (psycopg2)
    with raw.cursor() as cur:
        cur.execute(SQL.read_text(encoding="utf-8"))   # KHONG doi so thu hai


def downgrade() -> None:
    raise NotImplementedError(
        "Change `change-the-schema-without-dropping-it` chon FORWARD-ONLY.\n"
        "Go cot rehearsal_marker bang migration 003, khong bang downgrade."
    )
