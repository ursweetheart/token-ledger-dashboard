"""Dung fact_usage_daily tu ba nguon - buoc (7) cua Ngay 2.

Khong doc file nao: chi gop lai tu cac bang da nap.

COT `nguon` LA COT QUAN TRONG NHAT
---------------------------------
Ba nguon nam CANH NHAU, KHONG cong vao nhau. Cung mot ngay cung mot agent co the
co ba dong. Chinh ty le giua chung la bo do phat hien app ghi thieu (12,9% tien,
17,0% luot goi o TLA HD). Xoa mot nguon la xoa luon bo do.

    Hoi TIEN          -> doc nguon='billing'
    Hoi AI DUNG       -> doc nguon='app'
    Hoi LUOT/DO TRE   -> doc nguon='monitoring' (hoac fact_perf_daily)

VIEC CHUA LAM DUOC - PHAI BIET TRUOC KHI DUNG BANG NAY
------------------------------------------------------
(a) `ngay` cua nguon 'billing' la NGAY THEO GIO MY, khong phai ICT.
    Hoa don Google cat ngay theo Pacific. Quy sang ICT can rai lai theo hinh dang
    phut cua monitoring - do la UOC LUONG, chua lam. TONG ca ky van dung tuyet doi
    ($270,951716); chi CHUOI THEO NGAY cua rieng nguon billing la lech toi 15 gio.
    Nguon 'app' va 'monitoring' deu da la ICT that.
(b) TLA HD KHONG co dong nguon='app'. Xem chu thich o ham `nap_app`.

NGHIEM THU
----------
    SUM(chi_phi_usd) WHERE nguon='billing'      -- 270.951716
    SUM(total_tokens) WHERE nguon='app'         -- 44692501  (chi Ralli)
    COUNT(DISTINCT nguon)                       -- 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ket_noi  # noqa: E402

RALLI, TLA_HD = 8, 5
AGENT_MOT_USER = (1, 2, 3, 4, 6, 7)

TIEN_MONG_DOI = 270.951716
TOKEN_APP_MONG_DOI = 44692501


def diem_neo(agent_id: int) -> tuple[str, str]:
    """Dong ky thuat de thay cho NULL o unit_id/user_id (xem §4.2 ke hoach)."""
    if agent_id in AGENT_MOT_USER:
        return f"__ky_thuat_{agent_id}__", f"__ky_thuat_{agent_id}__"
    return f"__chua_quy_duoc_{agent_id}__", f"__chua_quy_duoc_{agent_id}__"


def nap_billing(cur, dc) -> int:
    """Tien tu hoa don. NGAY LA GIO MY - xem canh bao (a) o dau file."""
    hang = cur.execute("""
        SELECT b.ngay, a.agent_id, b.model_id, SUM(b.so_luong), SUM(b.chi_phi_usd)
        FROM fact_billing_daily b
        JOIN dim_agent a ON a.gcp_project_id = b.project
        GROUP BY b.ngay, a.agent_id, b.model_id
    """).fetchall()
    dong = []
    for ngay, aid, mid, tok, tien in hang:
        dv, nd = diem_neo(aid)
        dong.append((ngay, aid, mid, dv, nd, None, tok, tien, "billing"))
    cur.executemany(
        f"INSERT INTO fact_usage_daily (ngay, agent_id, model_id, unit_id, user_id,"
        f" so_luot, total_tokens, chi_phi_usd, nguon) VALUES ({','.join([dc] * 9)})", dong)
    return len(dong)


def nap_monitoring(cur, dc) -> int:
    """Token va luot goi tu cong to Google. Ngay ICT that."""
    # Hai phep do nam o hai nhom khac nhau, phai gop rieng roi khop lai.
    # `api_request_count` bi loai vi KHONG co nhan model (13.276/13.276 rong) -
    # no thuoc ve fact_perf_daily. Mau LIKE '%_requests' da loai san no.
    def gom(dieu_kien: str) -> dict:
        return {(r[0], r[1], r[2]): r[3] for r in cur.execute(f"""
            SELECT substr(m.thoi_diem_ict, 1, 10), a.agent_id, m.model_id, SUM(m.gia_tri)
            FROM mon_sach m
            JOIN dim_agent a ON a.gcp_project_id = m.project
            WHERE m.model_id IS NOT NULL AND {dieu_kien}
            GROUP BY 1, 2, 3
        """).fetchall()}

    tok = gom("m.phep_do LIKE '%token_count'")
    luot = gom("m.phep_do LIKE '%requests'")

    dong = []
    for k in sorted(set(tok) | set(luot)):
        ngay, aid, mid = k
        dv, nd = diem_neo(aid)
        n = luot.get(k)
        dong.append((ngay, aid, mid, dv, nd,
                     int(n) if n is not None else None,
                     int(tok[k]) if k in tok else None,
                     None, "monitoring"))
    cur.executemany(
        f"INSERT INTO fact_usage_daily (ngay, agent_id, model_id, unit_id, user_id,"
        f" so_luot, total_tokens, chi_phi_usd, nguon) VALUES ({','.join([dc] * 9)})", dong)
    return len(dong)


def nap_app(cur, dc) -> int:
    """Chieu nguoi dung. CHI RALLI.

    TLA HD khong co dong nao o day, va do KHONG phai thieu sot khi viet ma la
    thieu du lieu:
        token-usage-day.json    dung 1 ngay (05/08), toan so 0
        token-usage-week.json   bucket=day nhung chi 1 diem
        token-usage-month.json  bucket=day nhung chi 2 diem (02/08 va 04/08)
        token-usage-year.json   bucket=THANG, va by_user la tong CA KY
    Nghia la khong co du lieu app muc NGAY x MODEL x NGUOI cho TLA HD. Muon co
    phai cao lai API cua TLA HD theo tung ngay - viec moi, quyet dinh N5 hoan lai.
    Ralli thi nguoc lai: fact_call la TUNG LOI GOI nen gop ra ngay nao cung duoc.
    """
    # 134 loi goi co user_id = NULL (quy tac 5: thieu thi NULL, dung vay o bang
    # THO). Nhung khoa cua bang TONG HOP khong nhan NULL, nen o day thay bang
    # dong ky thuat. Hai bang noi hai chuyen khac nhau va deu dung.
    chua_quy = f"__chua_quy_duoc_{RALLI}__"
    dong = cur.execute("""
        SELECT substr(thoi_diem_ict, 1, 10), agent_id, model_id, unit_id,
               COALESCE(user_id, ?), COUNT(*), SUM(total_tokens)
        FROM fact_call
        WHERE model_id IS NOT NULL
        GROUP BY 1, 2, 3, 4, 5
    """, (chua_quy,)).fetchall()
    # SELECT tra ve 7 cot; chi_phi_usd de NULL vi app cua Ralli khong co tien
    # doi chung (quyet dinh M-D), va nguon luon la 'app'.
    cur.executemany(
        f"INSERT INTO fact_usage_daily (ngay, agent_id, model_id, unit_id, user_id,"
        f" so_luot, total_tokens, chi_phi_usd, nguon)"
        f" VALUES ({','.join([dc] * 7)}, NULL, 'app')", dong)
    return len(dong)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=ket_noi.MAC_DINH)
    args = p.parse_args()

    cn, dc = ket_noi.mo(args.db)
    cur = cn.cursor()
    cur.execute("DELETE FROM fact_usage_daily")

    n_b = nap_billing(cur, dc)
    n_m = nap_monitoring(cur, dc)
    n_a = nap_app(cur, dc)
    print(f"  billing {n_b} | monitoring {n_m} | app {n_a}")

    tien = cur.execute("SELECT SUM(chi_phi_usd) FROM fact_usage_daily"
                       " WHERE nguon='billing'").fetchone()[0]
    tok_app = cur.execute("SELECT SUM(total_tokens) FROM fact_usage_daily"
                          " WHERE nguon='app'").fetchone()[0]
    nguon = dict(cur.execute("SELECT nguon, COUNT(*) FROM fact_usage_daily"
                             " GROUP BY nguon").fetchall())
    agent_co_app = [r[0] for r in cur.execute(
        "SELECT DISTINCT agent_id FROM fact_usage_daily WHERE nguon='app'")]

    print(f"  theo nguon: {nguon}")
    print(f"  tien billing ${float(tien):.6f} | token app {tok_app:,}")
    print(f"  agent co nguon 'app': {agent_co_app}")

    loi = []
    if abs(float(tien) - TIEN_MONG_DOI) > 1e-4:
        loi.append(f"tien {float(tien):.6f} != {TIEN_MONG_DOI}")
    if tok_app != TOKEN_APP_MONG_DOI:
        loi.append(f"token app {tok_app} != {TOKEN_APP_MONG_DOI}")
    if len(nguon) != 3:
        loi.append(f"chi co {len(nguon)} nguon, phai co 3")
    if loi:
        cn.rollback()
        raise SystemExit("NGHIEM THU KHONG DAT - da huy:\n  " + "\n  ".join(loi))
    cn.commit()
    print("  NGHIEM THU DAT")


if __name__ == "__main__":
    main()
