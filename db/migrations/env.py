"""Cau hinh Alembic cho Token Ledger.

DSN LAY TU connect.py, KHONG LAY TU alembic.ini
------------------------------------------------
`db/connect.py` tu nhan la "cho DUY NHAT quyet dinh database mac dinh", va no ghi
lai mot su co dung hinh dang nay: `scripts/rebuild_db.py` tung khai DSN mac dinh
rieng, con `scripts/update_dashboard.py` goi no khong truyen `--db`. He qua la doi
connect.py xong ma duong ong van dung lai database cu - KHONG LOI NAO BAO RA.

Vi vay `sqlalchemy.url` da bi go khoi `alembic.ini`. De no o do la tao lai dung
cai bay tren, lan nay giua Alembic va phan con lai cua he thong.

Ghi de cho MOT lan chay (vi du dung database v2 o nhom 5):

    alembic -x db=postgresql://.../token_ledger_v2 upgrade head
    TOKEN_LEDGER_DSN=... alembic upgrade head        # connect.py doc bien nay

KHONG DUNG --autogenerate
-------------------------
`target_metadata = None` la CO Y, khong phai chua lam xong.

Du an nay khong co ORM: schema viet bang SQL thuan, moi cau truy van trong
backend/store.py la SQL tho. Va quan trong hon: Alembic KHONG QUAN LY VIEW, ma
`usage_resolved` moi la thu 01_schema.sql goi la "CUA CHINH de hoi so lieu".
Autogenerate se im lang bo qua ca ba view roi bao "khong co gi thay doi".

Migration o day viet bang SQL thuan, doc tu db/migrations/sql/*.sql qua
op.execute(). Xem db/migrations/README.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "db"))

import connect  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# CO Y de None - xem ghi chu "KHONG DUNG --autogenerate" o dau file.
target_metadata = None


def _dsn() -> str:
    """DSN cho lan chay nay, theo thu tu uu tien:

        1. -x db=...             ghi de tren dong lenh, manh nhat
        2. connect.ACTIVE_DSN    khi Alembic duoc goi TU connect.rebuild()
        3. connect.DEFAULT_DSN   mac dinh

    Buoc 2 la bat buoc, khong phai cho tien: `DEFAULT_DSN` la hang so tinh mot lan
    luc import, nen `rebuild(dsn_khac)` khong doi duoc no. Thieu buoc nay thi
    rebuild() xoa database A roi bao Alembic dung schema len database B - va
    KHONG LOI NAO BAO RA cho toi luc ai do doc so lieu.
    """
    overrides = context.get_x_argument(as_dictionary=True)
    return overrides.get("db") or connect.ACTIVE_DSN or connect.DEFAULT_DSN


def run_migrations_offline() -> None:
    """Sinh SQL ra man hinh, khong noi vao database."""
    context.configure(
        url=_dsn(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    dsn = _dsn()
    # In ra database dang bi tac dong. Da che mat khau bang connect.mask_dsn -
    # `alembic upgrade` la lenh SUA schema, nen nham database la chuyen dat gia.
    print(f"alembic -> {connect.mask_dsn(dsn)}")
    # DSN cua du an dung nguyen lam URL SQLAlchemy vi chi con PostgreSQL, va chuoi
    # `postgresql://...` von da la URL hop le. Truoc 24/08 o day co mot ham doi
    # duong dan SQLite tran thanh `sqlite:///...`; no di cung nhanh SQLite.
    engine = create_engine(dsn, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
