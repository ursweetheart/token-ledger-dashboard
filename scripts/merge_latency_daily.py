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

PERCENTILES = (0.50, 0.95, 0.99)


def bucket_bounds(options: dict) -> list[float]:
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


def bucket_count(options: dict) -> int:
    return int(options["exponentialBuckets"]["numFiniteBuckets"]) + 2


def pad_zeros(counts: list, want: int) -> list[int]:
    """proto3 cat o 0 o duoi -> chen lai cho du truoc khi cong."""
    out_path = [int(x) for x in counts]
    if len(out_path) > want:
        raise SystemExit(f"bucketCounts dai {len(out_path)} o, vuot qua {want} o cua schema.")
    return out_path + [0] * (want - len(out_path))


def percentile_from_histogram(counts: list[int], bounds: list[float], q: float):
    """Tra ve (uoc_luong, o_duoi, o_tren). o_tren = None neu roi vao o tren nguong."""
    total = sum(counts)
    if total == 0:
        return None, None, None

    target = q * total
    prev = 0
    for i, c in enumerate(counts):
        if c == 0:
            continue
        if prev + c >= target:
            # o 0 la duoi nguong: (0, bien[0]). o cuoi la tren nguong: [bien[-1], vo cuc).
            if i == 0:
                warn, hi = 0.0, bounds[0]
            elif i >= len(bounds):
                return bounds[-1], bounds[-1], None
            else:
                warn, hi = bounds[i - 1], bounds[i]
            in_bucket = (target - prev) / c
            return warn + (hi - warn) * in_bucket, warn, hi
        prev += c

    # Chi den day neu tong > 0 nhung vong lap khong bat duoc muc tieu -> loi logic,
    # khong phai du lieu la. Dung han thay vi tra ve mot so trong.
    raise SystemExit(f"Khong tim duoc phan vi {q} tren histogram co tong {total}.")


def read_batch(folder: Path, by_method: bool):
    """Gop histogram theo khoa. Tra ve (gop, schema, so_diem, so_diem_rong)."""
    merged: dict[tuple, list[int]] = {}
    # Cach cu, de doi chung: p95 cua TUNG phut roi lay trung binh.
    old_way: dict[tuple, list[float]] = defaultdict(list)
    schema = None
    schema_json = ""
    bounds: list[float] = []
    want = 0
    n_points = n_empty = 0

    files = sorted(glob.glob(str(folder / "*.jsonl")))
    if not files:
        raise SystemExit(f"Khong co file .jsonl nao trong {folder}")

    def per_row():
        """Doc lan luot, dong file ngay khi doc xong - khong giu handle mo."""
        for f in files:
            with open(f, encoding="utf-8") as handle:
                yield from handle

    for row in per_row():
            r = json.loads(row)
            n_points += 1

            # Diem khong co count la phut khong co luot goi nao (proto3 luoc bo
            # gia tri 0). Dong gop 0 vao histogram - bo qua, khong coi la loi.
            if r["count"] is None or r["bucketCounts"] is None:
                n_empty += 1
                continue

            opts = r["bucketOptions"]
            if schema is None:
                # Tinh MOT lan. Dat trong vong lap thi 12.473 lan dung 30 so mu.
                schema = opts
                schema_json = json.dumps(opts, sort_keys=True)
                want = bucket_count(opts)
                bounds = bucket_bounds(opts)
            elif json.dumps(opts, sort_keys=True) != schema_json:
                raise SystemExit(
                    "Gap bucketOptions thu hai - cac o khong ung nhau, khong gop duoc.\n"
                    f"  dang dung: {json.dumps(schema)}\n"
                    f"  gap phai : {json.dumps(opts)}\n"
                    f"  tai      : {r['gcp_project_id']} {r['ts_utc']}"
                )

            key = (r["ts_ict"][:10], r["gcp_project_id"])
            if by_method:
                key = key + (r["res_method"],)

            o = pad_zeros(r["bucketCounts"], want)
            if key in merged:
                merged[key] = [a + b for a, b in zip(merged[key], o)]
            else:
                merged[key] = o

            approx, _, _ = percentile_from_histogram(o, bounds, 0.95)
            if approx is not None:
                old_way[key].append(approx)

    return merged, old_way, schema, n_points, n_empty


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="vao", default=str(DEFAULT_IN),
                        help="Thu muc chua ban cao, hoac thu muc cha")
    parser.add_argument("--out", default="", help="File CSV ra (mac dinh: in ra man hinh)")
    parser.add_argument("--theo-method", dest="by_method", action="store_true",
                        help="Tach them theo res_method thay vi gop ca du an")
    args = parser.parse_args()

    folder = Path(args.vao)
    if not list(folder.glob("*.jsonl")):
        remaining = sorted(p for p in folder.glob("*") if p.is_dir() and list(p.glob("*.jsonl")))
        if len(remaining) != 1:
            raise SystemExit(
                f"Khong ro lay thu muc nao trong {folder}. Tim thay: {[p.name for p in remaining]}\n"
                "Chi ro bang --in."
            )
        folder = remaining[0]

    print(f"Doc: {folder}", file=sys.stderr)
    merged, old_way, schema, n_points, n_empty = read_batch(folder, args.by_method)
    if schema is None:
        raise SystemExit(
            f"Doc {n_points} diem nhung KHONG diem nao co histogram.\n"
            "Tat ca deu la phut khong co luot goi. Kiem lai thu muc dau vao."
        )
    bounds = bucket_bounds(schema)

    print(f"  {n_points} diem, trong do {n_empty} phut khong co luot goi", file=sys.stderr)
    print(f"  bucketOptions: {json.dumps(schema)}", file=sys.stderr)
    print(f"  o cuoi cung bat dau tu {bounds[-1]:.1f}s", file=sys.stderr)
    print(f"  -> {len(merged)} dong ket qua", file=sys.stderr)

    cols = ["day", "project"] + (["res_method"] if args.by_method else []) + [
        "samples", "p50_s", "p95_s", "p99_s", "p95_bucket_from",
        "p95_bucket_to", "p95_old_method_avg", "diff_percent"]

    row = []
    for key in sorted(merged):
        counts = merged[key]
        total = sum(counts)
        value = {}
        for q in PERCENTILES:
            approx, warn, hi = percentile_from_histogram(counts, bounds, q)
            value[q] = (approx, warn, hi)

        p95, lo95, hi95 = value[0.95]
        old_rows = old_way.get(key, [])
        old_avg = sum(old_rows) / len(old_rows) if old_rows else None
        diff = ((old_avg - p95) / p95 * 100) if (old_avg is not None and p95) else None

        row.append(dict(zip(cols, list(key) + [
            total,
            round(value[0.50][0], 4) if value[0.50][0] is not None else "",
            round(p95, 4) if p95 is not None else "",
            round(value[0.99][0], 4) if value[0.99][0] is not None else "",
            round(lo95, 4) if lo95 is not None else "",
            round(hi95, 4) if hi95 is not None else "",
            round(old_avg, 4) if old_avg is not None else "",
            round(diff, 1) if diff is not None else "",
        ])))

    total_calls = sum(d["samples"] for d in row)
    print(f"  tong so luot goi: {total_calls:,}", file=sys.stderr)

    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="") as h:
            w = csv.DictWriter(h, fieldnames=cols, quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(row)
        print(f"Ghi: {args.out}", file=sys.stderr)
    else:
        w = csv.DictWriter(sys.stdout, fieldnames=cols)
        w.writeheader()
        w.writerows(row)


if __name__ == "__main__":
    main()
