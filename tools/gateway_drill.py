"""Dien tap Gateway: chen du lieu gia mang username THAT, do xem dashboard co
nhuc nhich khong, roi HOAN TAC.

    python tools/dien_tap_gateway.py
    python tools/dien_tap_gateway.py --db "postgresql://token:token_local@127.0.0.1:5432/token_ledger_v2"

VI SAO FILE NAY TON TAI
-----------------------
Cau hoi "he thong da san sang don Gateway chua" hom nay la mot Y KIEN. File nay
bien no thanh mot con so: chen vai chuc dong `source='gateway'` roi dem xem co
bao nhieu cho tren dashboard KHONG nhuc nhich.

Chay TRUOC khi sua code thi no phai TRUOT - va danh sach cho truot chinh la
pham vi that cua change `admit-gateway-as-a-fourth-source`. Chay SAU khi sua thi
phai DAT het.

DUNG USERNAME THAT, KHONG BIA account_id
----------------------------------------
Bia mot account_id chi chung minh "cau SQL chay duoc". Tra username that ra
account_id moi chung minh "Gateway noi duoc vao du lieu dang co" - va do la
duong ma Gateway se di:

    JWT claim  ->  username  ->  account.username  ->  account_id
    (Ralli: sub · TLA HD: username · 6 agent mot-nguoi-dung: svc.<code>)

Do 21/08/2026: account (kind='real') co 814/937 username dang co dau cham va
0/937 dang ObjectId; Ralli /users/list co 814/891 va 0/891. Hai dau trung khit.

AN TOAN
-------
Moi thao tac nam trong MOT transaction va ket thuc bang ROLLBACK trong `finally`
- ke ca khi loi giua chung. Khong dung autocommit. Sau khi hoan tac, script DO
LAI mot lan nua de chung minh database da ve dung trang thai cu.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "db"))
sys.path.insert(0, str(ROOT))

import connect  # noqa: E402
from backend import store  # noqa: E402

DAT, TRUOT = "DAT  ", "TRUOT"

# Ngay chen phai NGOAI khoang du lieu that, de khong dung khoa chinh voi dong
# nao dang co va de nhin ra ngay dong nao la cua dien tap.
NGAY_MOI = "2026-08-18"

# Moi dong gia mang tung nay token. So tron de nhin ra ngay trong bao cao.
TOKEN_MOI_DONG = 1_000_000


def mot(cn, sql, params=()):
    r = connect.query_one(cn, sql, params)
    return r[0] if r else None


def do(cn) -> dict:
    """Bay con so ma Gateway PHAI lam thay doi. Moi con so tra loi mot cau.

    GOI THANG backend/store.py, KHONG CHEP LAI CAU SQL CUA NO.

    Ban dau ham nay chep cau truy van do phu cua store.health() vao day. Chay
    thu lan hai thi hai ky vong TRUOT - va hoa ra khong phai code sai, ma la ban
    chep con giu `token_source = 'app'`, tuc dang do bang DUNG cai logic ma
    change nay vua bo di. Mot phep kiem do ban sao cua thu no phai kiem thi no
    dang kiem chinh no.

    Do la cung mot cai bay mà ca change nay di bit, chi khac cho: mot khai niem
    duoc cai dat hai lan thi mot ban se troi.
    """
    ubk = connect.query_one(cn, """
        SELECT COUNT(*), COALESCE(SUM(total_tokens), 0) FROM usage_by_account""")
    ur = connect.query_one(cn, """
        SELECT COUNT(*), COALESCE(SUM(total_tokens), 0) FROM usage_resolved""")
    h = store.health(cn)

    return {
        "ubk_dong":     int(ubk[0]),
        "ubk_token":    int(ubk[1]),
        "ur_dong":      int(ur[0]),
        "ur_token":     int(ur[1]),
        "ur_gateway":   int(mot(cn, "SELECT COUNT(*) FROM usage_resolved"
                                    " WHERE token_source = 'gateway'")),
        "ur_null":      int(mot(cn, "SELECT COUNT(*) FROM usage_resolved"
                                    " WHERE total_tokens IS NULL")),
        "dich_vu":      int(h["tokens_attributed_to_service"]),
        "nguoi_that":   int(h["tokens_attributed_to_people"]),
        "khong_quy":    int(h["tokens_not_attributable"]),
    }


def dem_ap_dung(cn, agent_id: int) -> int:
    """Tu so cua chi tieu TY LE AP DUNG - lay tu store.adoption(), khong chep."""
    for r in store.adoption(cn):
        if r["agent_id"] == agent_id:
            return int(r["active"])
    raise SystemExit(f"khong thay agent {agent_id} trong store.adoption()")


def chon_nguoi_that(cn, agent_id: int, so_luong: int) -> list[tuple[int, str]]:
    """Tai khoan THAT trong danh ba cua agent, chua co luu luong nao.

    Chua co luu luong la co y: neu ho da co dong `source='app'` thi khong phan
    biet duoc "Gateway lam ho hien ra" voi "ho von da hien ra".
    """
    return [(int(a), u) for a, u in connect.query(cn, """
        SELECT c.account_id, c.username
          FROM account c
          JOIN dim_user d ON d.account_id = c.account_id
                         AND d.agent_id = %s AND d.found_in = 'directory'
         WHERE c.is_shared = 0 AND c.kind = 'real'
           AND c.account_id NOT IN (SELECT account_id FROM fact_usage_daily
                                     WHERE agent_id = %s)
         ORDER BY c.username
         LIMIT %s""", (agent_id, agent_id, so_luong))]


def chon_khoa_billing(cn):
    """Mot (ngay, agent, model, account_id) ma usage_resolved DANG chon billing.

    Dung de kiem THU TU UU TIEN: chen mot dong gateway len dung khoa do thi sau
    khi sua, token_source phai doi thanh 'gateway'.

    LAY LUON account_id CUA DONG BILLING DO, khong tra rieng tai khoan dich vu:
    hai agent Ralli va Hop Dong la 'whole_agent', KHONG co tai khoan dich vu.
    Neu khoa billing roi vao mot trong hai thi tra rieng se ra None, dong kiem
    uu tien khong duoc chen, va ky vong truot vi mot ly do KHAC han cai dang do
    - tuc mot phep kiem noi doi.
    """
    return connect.query_one(cn, """
        SELECT v.day, v.agent_id, v.model_id, f.account_id
          FROM usage_resolved v
          JOIN fact_usage_daily f ON f.day = v.day AND f.agent_id = v.agent_id
                                 AND f.model_id = v.model_id
                                 AND f.source = 'billing'
         WHERE v.token_source = 'billing'
         ORDER BY v.day DESC, v.total_tokens DESC LIMIT 1""")


def in_bang(truoc: dict, sau: dict, khoa: list[tuple[str, str]]) -> None:
    print(f"  {'':<38} {'truoc':>16} {'sau':>16} {'lech':>14}")
    for k, nhan in khoa:
        lech = sau[k] - truoc[k]
        dau = f"{lech:+,}" if lech else "0"
        print(f"  {nhan:<38} {truoc[k]:>16,} {sau[k]:>16,} {dau:>14}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=connect.DEFAULT_DSN)
    args = ap.parse_args()

    cn, ph = connect.open_db(args.db)
    if ph != "%s":
        print("Chi chay tren PostgreSQL - SQLite khong phai database cua du an.")
        return 2
    print(f"database: {connect.mask_dsn(args.db)}\n")

    ky_vong: list[tuple[str, bool, str]] = []

    try:
        # ---------------------------------------------------------------- moc
        truoc = do(cn)
        ap_dung_truoc = dem_ap_dung(cn, 8)
        khoa_bl = chon_khoa_billing(cn)
        if khoa_bl is None:
            print("Khong tim duoc khoa billing nao de kiem thu tu uu tien.")
            return 2
        bl_ngay, bl_agent, bl_model, bl_account = khoa_bl

        # -------------------------------------------------- chon nguoi dung that
        nguoi = chon_nguoi_that(cn, 8, 3)
        if len(nguoi) < 3:
            print(f"Chi tim duoc {len(nguoi)} tai khoan that phu hop, can 3.")
            return 2

        # Mot tai khoan dich vu bat ky, chi de kiem QUY UOC DAT TEN svc.<code>.
        # Khong dinh vao khoa billing o tren - xem ghi chu o chon_khoa_billing.
        dich_vu = connect.query_one(cn, """
            SELECT account_id, username FROM account
             WHERE kind = 'service_account' ORDER BY account_id LIMIT 1""")

        print("Tai khoan THAT duoc dung (tra tu username, khong bia account_id):")
        for aid, u in nguoi:
            print(f"  agent 8 · account_id={aid:<5} username={u}")
        print(f"  kiem uu tien · khoa ({bl_ngay}, agent {bl_agent},"
              f" model {bl_model}, account_id {bl_account})")
        print()

        # ------------------------------------------------------------- chen gia
        cot = ["day", "agent_id", "model_id", "account_id", "calls",
               "total_tokens", "input_tokens", "output_tokens", "cached_tokens",
               "cost_usd", "source"]
        dong = []
        for i, (aid, _u) in enumerate(nguoi):
            dong.append((NGAY_MOI, 8, i + 1, aid, 10, TOKEN_MOI_DONG,
                         700_000, 300_000, 0, 0.5, "gateway"))
        # Dung DUNG khoa ma usage_resolved dang chon billing -> kiem uu tien
        dong.append((bl_ngay, bl_agent, bl_model, bl_account, 5,
                     TOKEN_MOI_DONG, 700_000, 300_000, 0, 0.5, "gateway"))

        so_chen = connect.insert_many(cn, ph, "fact_usage_daily", cot, dong)
        print(f"Da chen {so_chen} dong source='gateway' (chua commit).\n")

        # ---------------------------------------------------------------- do lai
        sau = do(cn)
        ap_dung_sau = dem_ap_dung(cn, 8)
        uu_tien = mot(cn, """
            SELECT token_source FROM usage_resolved
             WHERE day = %s AND agent_id = %s AND model_id = %s""",
            (bl_ngay, bl_agent, bl_model))

        print("SO DO")
        in_bang(truoc, sau, [
            ("ubk_dong",   "usage_by_account · dong"),
            ("ubk_token",  "usage_by_account · token"),
            ("ur_dong",    "usage_resolved · dong"),
            ("ur_token",   "usage_resolved · token"),
            ("ur_gateway", "usage_resolved · dong nguon gateway"),
            ("ur_null",    "usage_resolved · dong KHONG co token"),
            ("nguoi_that", "quy ve NGUOI THAT · token"),
            ("dich_vu",    "quy ve tai khoan dich vu · token"),
            ("khong_quy",  "KHONG quy duoc · token"),
        ])
        print(f"  {'ty le ap dung agent 8 · tu so':<38}"
              f" {ap_dung_truoc:>16,} {ap_dung_sau:>16,}"
              f" {ap_dung_sau - ap_dung_truoc:>+14,}")
        print()

        # ------------------------------------------------------------- ky vong
        ky_vong = [
            ("usage_by_account nhan them dong",
             sau["ubk_dong"] == truoc["ubk_dong"] + 3,
             f"+{sau['ubk_dong'] - truoc['ubk_dong']}, can +3"),

            ("usage_by_account nhan them token",
             sau["ubk_token"] == truoc["ubk_token"] + 3 * TOKEN_MOI_DONG,
             f"+{sau['ubk_token'] - truoc['ubk_token']:,},"
             f" can +{3 * TOKEN_MOI_DONG:,}"),

            ("ty le ap dung nhuc nhich",
             ap_dung_sau == ap_dung_truoc + 3,
             f"+{ap_dung_sau - ap_dung_truoc}, can +3"),

            ("token quy ve NGUOI THAT tang",
             sau["nguoi_that"] > truoc["nguoi_that"],
             f"+{sau['nguoi_that'] - truoc['nguoi_that']:,}"),

            ("usage_resolved nhan dien nguon gateway",
             sau["ur_gateway"] > 0,
             f"{sau['ur_gateway']} dong"),

            ("gateway duoc uu tien TRUOC billing",
             uu_tien == "gateway",
             f"khoa ({bl_ngay}, agent {bl_agent}, model {bl_model})"
             f" van la '{uu_tien}'"),

            ("khong sinh dong RONG trong usage_resolved",
             sau["ur_null"] == truoc["ur_null"],
             f"+{sau['ur_null'] - truoc['ur_null']} dong khong co token"),
        ]

        if dich_vu and not str(dich_vu[1]).startswith("svc."):
            ky_vong.append((
                "tai khoan dich vu dung ten svc.<code>",
                False,
                f"dang la '{dich_vu[1]}' - quy uoc A3 chot 20/08 la svc.<code>"))

        print("KY VONG")
        for nhan, dat, chi_tiet in ky_vong:
            print(f"  [{DAT if dat else TRUOT}] {nhan:<45} {chi_tiet}")
        print()

    finally:
        cn.rollback()

    # ------------------------------------------------------ chung minh da sach
    lai = do(cn)
    sach = lai == truoc
    print(f"HOAN TAC: [{DAT if sach else TRUOT}] database ve dung trang thai cu")
    if not sach:
        for k in truoc:
            if truoc[k] != lai[k]:
                print(f"    {k}: {truoc[k]:,} -> {lai[k]:,}")
    print()

    hong = [n for n, dat, _ in ky_vong if not dat]
    if hong or not sach:
        print(f"TRUOT {len(hong)}/{len(ky_vong)} ky vong.")
        print("Neu day la lan chay TRUOC khi sua code thi dung nhu du doan:")
        print("danh sach tren la pham vi that cua change.")
        return 1
    print(f"DAT {len(ky_vong)}/{len(ky_vong)} ky vong.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
