"""Lam moi duong Gateway: so LiteLLM -> fact_call -> fact_usage_daily.

    python scripts/refresh_gateway.py
    python scripts/refresh_gateway.py --every 120     # che do vong lap

VI SAO CO FILE NAY

Sau khi mot agent goi qua Gateway, du lieu vao so cua Gateway NGAY (bat dong bo
~4 giay), nhung dashboard thi khong tu doi - phai chay BON lenh, dung thu tu.

BON, KHONG PHAI HAI (doi 03/09/2026)
File nay viet 31/08 khi duong dan Gateway dung la hai buoc. Migration 008 sang
03/09 them HAI BANG DAN XUAT nua ma nguon gateway nuoi - `fact_usage_hourly` va
phan gateway cua `fact_latency_daily` - va file nay khong duoc cap nhat theo.

He qua: `/api/usage-hourly` va `/api/performance` phuc vu SO CU sau moi lan
refresh, IM LANG. `audit_db.py` co bat duoc, nhung chi khi ai do chay no.
Nho mot lenh de hon nho hai, va quen buoc 2 thi so cu nam nguyen tren dashboard
ma khong co dau hieu gi.

Do 03/09/2026: ca chu ky BON buoc mat ~1,8 giay (moc hai buoc la 0,89 giay;
bang theo gio them 921 ms, phan vi chi-Gateway chay tren 41 dong nen tinh bang
mili giay). Voi `--every 120` thi 1,8 tren 120 giay la 1,5% - khong dang ban.

DUNG NGAY NEU BUOC 1 HONG

`build_usage_daily.py` XOA SACH fact_usage_daily roi dung lai. Neu load_gateway
hong (vi du Gateway dang tat) ma van chay buoc 2, ta se dung lai bang tong hop
tu mot fact_call THIEU du lieu Gateway - va ket qua trong y het "chua co luu
luong". Tha dung lai voi so cu con dung.

HANH VI O CHE DO VONG LAP - BIET TRUOC DE KHONG TUONG MINH LAM HONG GI

`db/build_usage_hourly.py` TU DOI CHIEU tong theo gio voi tong theo ngay va
`SystemExit` neu lech. O che do chay tay do la dung thu ta muon. O che do
`--every` no se keu MOI CHU KY cho toi khi co nguoi sua.

Do la hanh vi DUNG - im lang thi te hon nhieu, va chinh khoang lang do la thu
change nay di bit. Nhanh `try/except` quanh `mot_luot()` giu cho vong lap khong
chet vi mot luot hong; no chi keu.

KHONG PHAI BAN THAY THE rebuild_db.py

`rebuild_db.py` dung lai CA database tu file du lieu (78 giay). File nay chi lam
moi duong Gateway tren database dang co (~0,8 giay). Hai viec khac nhau.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "db"))

import connect  # noqa: E402

PY = sys.executable

# (nhan, duong dan tuong doi ROOT, tham so rieng)
#
# MANG DUONG DAN VA THAM SO, khong chi ten file (doi 03/09/2026). Buoc 4 can mot
# co rieng, va ban cu ghep cung `ROOT / "db" / ten` nen khong truyen duoc gi.
# Cung hinh dang ma scripts/rebuild_db.py dang dung.
#
# THU TU LA BAT BUOC, KHONG PHAI TUY
#   3 phai sau 2: build_usage_hourly tu doi chieu tong cua minh voi bang NGAY va
#     SystemExit neu lech. Dao thu tu la so voi bang ngay CU roi bao lech gia.
#   4 dung --chi-gateway: che do day du doc `latency-daily.csv`, mot file CAO TAY,
#     va DUNG HAN neu file vang mat. Mot vong lap `--every 120` ma phu thuoc file
#     phai cao tay la qua bom hen gio. Xem db/build_performance.py:chi_gateway().
STEPS = [
    ("Nap so Gateway",     "db/load_gateway.py",       []),
    ("Tong hop theo ngay", "db/build_usage_daily.py",  []),
    ("Tong hop theo gio",  "db/build_usage_hourly.py", []),
    ("Phan vi Gateway",    "db/build_performance.py",  ["--chi-gateway"]),
]


def dem(dsn: str) -> tuple[int, int, int, int, int]:
    """Dem CA BON bang ma nguon gateway nuoi.

    Ban truoc 03/09 chi dem hai (fact_call, fact_usage_daily) - dung bang hai
    buoc ma no chay. Nen mot bang dan xuat bi bo lai KHONG hien ra o dong tom tat:
    nguoi chay thay `fact_call +1` va tuong ca duong da moi.

    Dem du bon thi bang nao khong nhuc nhich se lo ra ngay tren man hinh.
    """
    cn, _ = connect.open_db(dsn)
    try:
        n, tok = connect.query_one(
            cn, "SELECT COUNT(*), COALESCE(SUM(total_tokens), 0)"
                " FROM fact_call WHERE source = 'gateway'")
        agg = connect.query_one(
            cn, "SELECT COUNT(*) FROM fact_usage_daily WHERE source = 'gateway'")[0]
        gio = connect.query_one(
            cn, "SELECT COUNT(*) FROM fact_usage_hourly WHERE source = 'gateway'")[0]
        lat = connect.query_one(
            cn, "SELECT COUNT(*) FROM fact_latency_daily WHERE source = 'gateway'")[0]
        return int(n), int(tok), int(agg), int(gio), int(lat)
    finally:
        cn.close()


def ghi_nhip_tim(dsn: str, so_dong: int, nhip: int) -> None:
    """Ghi dau moc "luot lam moi nay da chay xong" vao `ref_load_run`.

    VI SAO CAN, va vi sao khong the suy ra tu du lieu (do 09/09/2026)
    ----------------------------------------------------------------
    Nhin vao `fact_call` thi HAI trang thai duoi day trong Y HET NHAU:

        dong gateway moi nhat cach day 3 tieng, vi KHONG AI GOI
        dong gateway moi nhat cach day 3 tieng, vi DUONG NAP DA CHET

    Cai thu nhat binh thuong, cai thu hai la su co. Khong con so nao trong
    `token_ledger_v2` tach duoc chung, vi ca hai deu la "khong co dong moi".
    Nhip tim gia di theo DONG HO, nen no tach duoc: nhip tim tuoi + khong co
    dong moi = khong ai goi; nhip tim cu = duong nap chet.

    CHI GOI KHI CA BON BUOC DA XONG. Ghi som mot buoc la noi doi: nhip tim se
    tuoi trong khi so dang thieu du lieu.

    KHONG DUOC LAM CHET CA LUOT LAM MOI. Nhip tim la thu de CHAN DOAN; hong noi
    nay khong duoc keo do viec nap du lieu that. Nhung cung KHONG duoc nuot lang:
    nhip tim khong ghi duoc ma khong ai biet thi phep kiem do tre se doc mot moc
    cu va bao dong gia.

    `nhip` la so giay giua hai luot cua CHINH tien trinh nay (0 = chay mot lan roi
    thoat). Ghi no vao so chu khong de moi ben doc tu doan: nguong cua phep kiem
    do tre suy TU nhip, va neu moi tien trinh doc mot bien moi truong rieng thi hai
    ben lech nhau -> bao dong gia. Xem migration 012, cot `every_seconds`.
    """
    try:
        cn, _ = connect.open_db(dsn)
    except Exception as e:                        # noqa: BLE001
        print(f"  CANH BAO: khong mo duoc ket noi de ghi nhip tim: {type(e).__name__}")
        return
    try:
        with cn.cursor() as cur:
            # `now() AT TIME ZONE 'Asia/Ho_Chi_Minh'` -- dong ho cua DATABASE, gio
            # VN. KHONG dung datetime.now() cua Python: container nay chay UTC
            # (do 09/09/2026) con `fact_call.ts_local` la gio VN, nen lay dong ho
            # container se lech DUNG 7 GIO va mot nhip tim vua ghi se trong nhu
            # da chet 7 tieng.
            cur.execute("""
                INSERT INTO ref_load_run (source, last_success_at, rows_after,
                                          written_by, every_seconds)
                VALUES ('gateway', now() AT TIME ZONE 'Asia/Ho_Chi_Minh', %s,
                        'scripts/refresh_gateway.py', %s)
                ON CONFLICT (source) DO UPDATE
                   SET last_success_at = EXCLUDED.last_success_at,
                       rows_after      = EXCLUDED.rows_after,
                       written_by      = EXCLUDED.written_by,
                       every_seconds   = EXCLUDED.every_seconds""",
                        (so_dong, nhip or None))
        cn.commit()
    except Exception as e:                        # noqa: BLE001
        print(f"  CANH BAO: khong ghi duoc nhip tim: {type(e).__name__}: {e}")
    finally:
        cn.close()


def mot_luot(dsn: str, im_lang: bool, nhip: int = 0) -> int:
    truoc = dem(dsn)
    for nhan, duong_dan, them in STEPS:
        # encoding PHAI dat tuong minh: mac dinh cua subprocess la codepage cua
        # console (cp1252 tren may nay), ma hai buoc deu in tieng Viet. Thieu no
        # thi luong doc nem UnicodeDecodeError - va mat dung doan chan doan can
        # xem nhat khi co su co.
        r = subprocess.run([PY, str(ROOT / duong_dan), *them],
                           capture_output=im_lang, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(f"FAILED at step '{nhan}' ({duong_dan}), exit code {r.returncode}."
                  f" DUNG LAI - khong tong hop tren du lieu thieu.")
            # In CA hai luong. Traceback nam o stderr; in moi stdout la giau
            # dung thu can xem.
            for luong in (r.stdout, r.stderr):
                if im_lang and luong:
                    print(luong.rstrip())
            return r.returncode
    sau = dem(dsn)
    ghi_nhip_tim(dsn, sau[0], nhip)

    print(f"  fact_call gateway  {truoc[0]:>6} -> {sau[0]:<6} (+{sau[0] - truoc[0]})"
          f"  | token {truoc[1]:,} -> {sau[1]:,}")
    for nhan, i in (("fact_usage_daily", 2), ("fact_usage_hourly", 3),
                    ("fact_latency_daily", 4)):
        print(f"  {nhan:<18} {truoc[i]:>6} -> {sau[i]:<6} gateway rows")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default=connect.DEFAULT_DSN)
    p.add_argument("--every", type=int, default=0,
                   help="Chay lap lai moi N giay. 0 = chay mot lan roi thoat.")
    p.add_argument("--quiet", action="store_true",
                   help="Nuot dau ra cua hai buoc, chi in tom tat")
    args = p.parse_args()

    if not args.every:
        return mot_luot(args.db, args.quiet, 0)

    print(f"Looping every {args.every}s. Ctrl-C to stop.")
    while True:
        # Bat CA loi cua dem(): database co the dang khoi dong lai, va mot vong
        # lap chet vi mot luot hong la mat luon co che tu dong.
        try:
            ma = mot_luot(args.db, True, args.every)
        except Exception as exc:
            print(f"  ERROR: {type(exc).__name__}: "
                  f"{str(exc).strip().splitlines()[0]}")
            ma = 1
        if ma != 0:
            print(f"  (retrying in {args.every}s)")
        time.sleep(args.every)


if __name__ == "__main__":
    raise SystemExit(main())
