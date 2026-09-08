"""so cua nha cung cap, de doi chieu voi so cua Gateway - KHONG phai nguon thu nam

Revision ID: 011_so_nha_cung_cap
Revises: 010_latency_resolved
Create Date: 2026-09-04

Them bang `fact_provider_daily`. So Gateway tu no nhat quan, nen loi trong no
khong lo ra bang cach nhin vao no. Do duoc 04/09/2026 tren du lieu 31/08/2026:
nha cung cap dem 41 request voi response_code = 200 cho TAT CA, trong khi so
Gateway ghi 5 luot hong - 2 trong so do da duoc phuc vu xong va da tieu token
that. Chenh lech 12,21% token cua ngay do nam o cho nay.

Ten goi cua hinh dang loi: "luot hong khong phai luot mien phi" /
failed_is_not_free. Dinh nghia day du trong openspec design.md muc 6.

BANG NAY KHONG PHAI MOT NGUON DU LIEU. `usage_resolved` KHONG doc no va khong
bao gio duoc doc - cung mot luot goi da nam trong `fact_call` roi, doc them la
dem doi. Xem db/migrations/sql/011_so_nha_cung_cap.sql de biet day du ly le.
"""

from pathlib import Path

from alembic import op

revision = "011_so_nha_cung_cap"
down_revision = "010_latency_resolved"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "011_so_nha_cung_cap.sql"


def upgrade() -> None:
    raw = op.get_bind().connection          # ket noi DBAPI that (psycopg2)
    with raw.cursor() as cur:
        cur.execute(SQL.read_text(encoding="utf-8"))   # KHONG doi so thu hai


def downgrade() -> None:
    raise NotImplementedError(
        "Change `change-the-schema-without-dropping-it` chon FORWARD-ONLY.\n"
        "Muon go bang nay thi viet mot migration TIEN moi."
    )
