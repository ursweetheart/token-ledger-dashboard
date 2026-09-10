"""nhip tim cua duong nap, de phan biet "khong co luu luong" voi "duong nap da chet"

Revision ID: 012_nhip_tim_lam_moi
Revises: 011_so_nha_cung_cap
Create Date: 2026-09-09

Them bang `ref_load_run`. Truoc khi co no, khong cau nao trong `token_ledger_v2`
tra loi duoc "lan cuoi duong nap chay thanh cong la khi nao" -- nen hai trang
thai duoi day trong Y HET NHAU tu phia dashboard: dong gateway moi nhat cach day
3 tieng vi KHONG AI GOI, va dong gateway moi nhat cach day 3 tieng vi DUONG NAP
DA CHET.

Do duoc 09/09/2026 truoc khi co dich vu `ledger-refresh`: so nguon 444 dong (moi
nhat 08/09 23:55) trong khi `fact_call` phan gateway chi 41 dong (moi nhat 31/08
10:17) -- tre 8 ngay 13 gio, khong mot dau hieu nao.

`scripts/audit_db.py` nhom J co bat duoc do tre, nhung chi khi CO NGUOI chay audit
va chi khi so nguon CO DONG MOI. Nhip tim gia di theo dong ho, khong phu thuoc ca
hai dieu kien ay.

BANG NAY KHONG PHAI MOT NGUON DU LIEU. `usage_resolved` KHONG doc no. Xem
db/migrations/sql/012_nhip_tim_lam_moi.sql de biet day du ly le va cai bay mui gio.
"""

from pathlib import Path

from alembic import op

revision = "012_nhip_tim_lam_moi"
down_revision = "011_so_nha_cung_cap"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "012_nhip_tim_lam_moi.sql"


def upgrade() -> None:
    raw = op.get_bind().connection          # ket noi DBAPI that (psycopg2)
    with raw.cursor() as cur:
        cur.execute(SQL.read_text(encoding="utf-8"))   # KHONG doi so thu hai


def downgrade() -> None:
    raise NotImplementedError(
        "Change `change-the-schema-without-dropping-it` chon FORWARD-ONLY.\n"
        "Muon go bang nay thi viet mot migration TIEN moi."
    )
