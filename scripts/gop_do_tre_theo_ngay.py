"""Gop histogram do tre theo ngay ICT roi doc ra p50/p95/p99 - chi doc file.

VI SAO
------
Phan vi cua phan vi khong cong duoc. Trung binh cua p95=2,1s (tren 100 luot)
va p95=8,4s (tren 2 luot) ra 5,25s, trong khi p95 that khoang 2,3s.

Histogram thi cong duoc: cong so luot o TUNG O qua 1.440 phut cua ngay, roi
doc moc 95% tren histogram tong. Ket qua khong con la uoc luong theo trong so
ma la phan bo THAT cua ca ngay.

Doc tu: scripts/pull_latency_distribution.py (JSONL)
Chi tiet: docs/mui-gio-2026-08-08.md muc M-C.

BA DIEU PHAI CAN THAN
---------------------
1. proto3 CAT BO cac o 0 o duoi. Do dai bucketCounts thay doi tu 17 den 26 o
   trong khi du phai la 31. Cong thang hai mang khac do dai se LECH COT.
   -> chen 0 cho du truoc khi cong.

2. Chi gop duoc cac diem co CUNG bucketOptions. Khac scale hoac growthFactor
   thi cac o khong ung nhau. Script dung han neu gap bucketOptions thu hai.

3. Ngay tinh theo ICT (quyet dinh M-B). Cot ts_ict da co san trong JSONL.

DO CHINH XAC
------------
Histogram gop lai la CHINH XAC. Nhung doc mot phan vi tu histogram van phai
NOI SUY trong o chua no, va o thi rong dan theo cap so nhan (growthFactor 2).
Nen script xuat CA khoang o chua phan vi, khong chi mot so - de nguoi doc
biet do rong cua sai so thay vi tin vao ba chu so thap phan.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "data" / "raw_google_console" / "do_tre_phan_bo"

PHAN_VI = (0.50, 0.95, 0.99)


def bien_o(options: dict) -> list[float]:
    """Cac moc chia giua cac o, tinh bang giay.

    Google: exponentialBuckets voi N o huu han -> N+2 o tat ca.
      o 0        (-vo cuc, scale)                 duoi nguong
      o i (1..N) [scale*g^(i-1), scale*g^i)
      o N+1      [scale*g^N, +vo cuc)             tren nguong
    Tra ve N+1 moc: scale*g^0 ... scale*g^N.
    """
    mu = options.get("exponentialBuckets")
    if not mu:
        raise SystemExit(
            f"Chi ho tro exponentialBuckets. Nhan duoc: {json.dumps(options)[:200]}"
        )
    scale = float(mu["scale"])
    g = float(mu["growthFactor"])
    n = int(mu["numFiniteBuckets"])
    return [scale * g ** i for i in range(n + 1)]


def so_o(options: dict) -> int:
    return int(options["exponentialBuckets"]["numFiniteBuckets"]) + 2


def chen_0(counts: list, day_du: int) -> list[int]:
    """proto3 cat o 0 o duoi -> chen lai cho du truoc khi cong."""
    ra = [int(x) for x in counts]
    if len(ra) > day_du:
        raise SystemExit(f"bucketCounts dai {len(ra)} o, vuot qua {day_du} o cua schema.")
    return ra + [0] * (day_du - len(ra))


def phan_vi_tu_histogram(counts: list[int], bien: list[float], q: float):
    """Tra ve (uoc_luong, o_duoi, o_tren). o_tren = None neu roi vao o tren nguong."""
    tong = sum(counts)
    if tong == 0:
        return None, None, None

    muc_tieu = q * tong
    truoc = 0
    for i, c in enumerate(counts):
        if c == 0:
            continue
        if truoc + c >= muc_tieu:
            # o 0 la duoi nguong: (0, bien[0]). o cuoi la tren nguong: [bien[-1], vo cuc).
            if i == 0:
                lo, hi = 0.0, bien[0]
            elif i >= len(bien):
                return bien[-1], bien[-1], None
            else:
                lo, hi = bien[i - 1], bien[i]
            trong_o = (muc_tieu - truoc) / c
            return lo + (hi - lo) * trong_o, lo, hi
        truoc += c

    # Chi den day neu tong > 0 nhung vong lap khong bat duoc muc tieu -> loi logic,
    # khong phai du lieu la. Dung han thay vi tra ve mot so trong.
    raise SystemExit(f"Khong tim duoc phan vi {q} tren histogram co tong {tong}.")


def doc(thu_muc: Path, theo_method: bool):
    """Gop histogram theo khoa. Tra ve (gop, schema, so_diem, so_diem_rong)."""
    gop: dict[tuple, list[int]] = {}
    # Cach cu, de doi chung: p95 cua TUNG phut roi lay trung binh.
    cach_cu: dict[tuple, list[float]] = defaultdict(list)
    schema = None
    schema_json = ""
    bien: list[float] = []
    day_du = 0
    so_diem = so_rong = 0

    files = sorted(glob.glob(str(thu_muc / "*.jsonl")))
    if not files:
        raise SystemExit(f"Khong co file .jsonl nao trong {thu_muc}")

    def tung_dong():
        """Doc lan luot, dong file ngay khi doc xong - khong giu handle mo."""
        for f in files:
            with open(f, encoding="utf-8") as handle:
                yield from handle

    for dong in tung_dong():
            r = json.loads(dong)
            so_diem += 1

            # Diem khong co count la phut khong co luot goi nao (proto3 luoc bo
            # gia tri 0). Dong gop 0 vao histogram - bo qua, khong coi la loi.
            if r["count"] is None or r["bucketCounts"] is None:
                so_rong += 1
                continue

            opts = r["bucketOptions"]
            if schema is None:
                # Tinh MOT lan. Dat trong vong lap thi 12.473 lan dung 30 so mu.
                schema = opts
                schema_json = json.dumps(opts, sort_keys=True)
                day_du = so_o(opts)
                bien = bien_o(opts)
            elif json.dumps(opts, sort_keys=True) != schema_json:
                raise SystemExit(
                    "Gap bucketOptions thu hai - cac o khong ung nhau, khong gop duoc.\n"
                    f"  dang dung: {json.dumps(schema)}\n"
                    f"  gap phai : {json.dumps(opts)}\n"
                    f"  tai      : {r['gcp_project_id']} {r['ts_utc']}"
                )

            khoa = (r["ts_ict"][:10], r["gcp_project_id"])
            if theo_method:
                khoa = khoa + (r["res_method"],)

            o = chen_0(r["bucketCounts"], day_du)
            if khoa in gop:
                gop[khoa] = [a + b for a, b in zip(gop[khoa], o)]
            else:
                gop[khoa] = o

            uoc, _, _ = phan_vi_tu_histogram(o, bien, 0.95)
            if uoc is not None:
                cach_cu[khoa].append(uoc)

    return gop, cach_cu, schema, so_diem, so_rong


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="vao", default=str(DEFAULT_IN),
                        help="Thu muc chua ban cao, hoac thu muc cha")
    parser.add_argument("--out", default="", help="File CSV ra (mac dinh: in ra man hinh)")
    parser.add_argument("--theo-method", action="store_true",
                        help="Tach them theo res_method thay vi gop ca du an")
    args = parser.parse_args()

    thu_muc = Path(args.vao)
    if not list(thu_muc.glob("*.jsonl")):
        con = sorted(p for p in thu_muc.glob("*") if p.is_dir() and list(p.glob("*.jsonl")))
        if len(con) != 1:
            raise SystemExit(
                f"Khong ro lay thu muc nao trong {thu_muc}. Tim thay: {[p.name for p in con]}\n"
                "Chi ro bang --in."
            )
        thu_muc = con[0]

    print(f"Doc: {thu_muc}", file=sys.stderr)
    gop, cach_cu, schema, so_diem, so_rong = doc(thu_muc, args.theo_method)
    if schema is None:
        raise SystemExit(
            f"Doc {so_diem} diem nhung KHONG diem nao co histogram.\n"
            "Tat ca deu la phut khong co luot goi. Kiem lai thu muc dau vao."
        )
    bien = bien_o(schema)

    print(f"  {so_diem} diem, trong do {so_rong} phut khong co luot goi", file=sys.stderr)
    print(f"  bucketOptions: {json.dumps(schema)}", file=sys.stderr)
    print(f"  o cuoi cung bat dau tu {bien[-1]:.1f}s", file=sys.stderr)
    print(f"  -> {len(gop)} dong ket qua", file=sys.stderr)

    cot = ["ngay_ict", "project"] + (["res_method"] if args.theo_method else []) + [
        "so_luot", "p50_s", "p95_s", "p99_s", "p95_o_tu", "p95_o_den",
        "p95_cach_cu_trung_binh", "lech_phan_tram"]

    dong = []
    for khoa in sorted(gop):
        counts = gop[khoa]
        tong = sum(counts)
        gia_tri = {}
        for q in PHAN_VI:
            uoc, lo, hi = phan_vi_tu_histogram(counts, bien, q)
            gia_tri[q] = (uoc, lo, hi)

        p95, lo95, hi95 = gia_tri[0.95]
        cu = cach_cu.get(khoa, [])
        tb_cu = sum(cu) / len(cu) if cu else None
        lech = ((tb_cu - p95) / p95 * 100) if (tb_cu is not None and p95) else None

        dong.append(dict(zip(cot, list(khoa) + [
            tong,
            round(gia_tri[0.50][0], 4) if gia_tri[0.50][0] is not None else "",
            round(p95, 4) if p95 is not None else "",
            round(gia_tri[0.99][0], 4) if gia_tri[0.99][0] is not None else "",
            round(lo95, 4) if lo95 is not None else "",
            round(hi95, 4) if hi95 is not None else "",
            round(tb_cu, 4) if tb_cu is not None else "",
            round(lech, 1) if lech is not None else "",
        ])))

    tong_luot = sum(d["so_luot"] for d in dong)
    print(f"  tong so luot goi: {tong_luot:,}", file=sys.stderr)

    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="") as h:
            w = csv.DictWriter(h, fieldnames=cot, quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(dong)
        print(f"Ghi: {args.out}", file=sys.stderr)
    else:
        w = csv.DictWriter(sys.stdout, fieldnames=cot)
        w.writeheader()
        w.writerows(dong)


if __name__ == "__main__":
    main()
