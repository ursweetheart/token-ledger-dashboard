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

DOC MOI LAN KEO, KHU TRUNG LAP THEO DIEM (doi 14/09/2026)
--------------------------------------------------------
Truoc 14/09 script doi DUNG MOT lan keo. scripts/update_dashboard.py buoc 7 goi no
khong co --in tren thu muc co 4 lan keo, nen thoat 1 - va latency-daily.csv chi con
tu 09/06 trong khi lan keo 08/08 van giu du lieu thang 5.

Nay doc moi thu muc khop `PULL_DIR` (khuon scripts/pull_latency_distribution.py:171
dat cho lan keo 1 phut), in ten thu muc bi bo qua. Cac lan keo chong nhau phan lon
khoang ngay, nen KHONG cong thang: moi diem (project, phut, metric_type, TOAN BO nhan
goc da chuan hoa - xem POINT_KEY) chi tinh MOT lan; hai lan keo khac `count` thi giu
diem co count LON hon - thieu du lieu chi lam count nho di. Ca lech ghi ra tep canh --out.

Ban dau (14/09) khoa dung cac cot phang res_service/res_method/res_location/
res_credential_id. Sai: lan keo 2026-08-08 khong co cot res_credential_id, nen hai chuoi
khac credential bi gop lam mot va mat 8 mau. Phat hien khi so voi database cu token_ledger.

CANH BAO: sua duoc buoc 7 cung la mo duong toi buoc 8 cua update_dashboard.py.
Change nay chi an toan vi connect.rebuild() da bo DROP SCHEMA cung luc.

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
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "data" / "raw_google_console" / "do_tre_phan_bo"  # vi-ok: on-disk path

PERCENTILES = (0.50, 0.95, 0.99)

# Khuon ten lan keo 1 phut: scripts/pull_latency_distribution.py:170-171 dat
# `<ngay>-<so ngay>d-<do min>`. Lan keo 1 gio ghi tem HH:00, khac khoa voi diem 1
# phut, nen se bi CONG CHONG neu lot vao.
PULL_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}-\d+d-1m$")

# Mot CHUOI do = metric_type + TOAN BO nhan goc cua Google, KHONG phai cac cot phang
# (res_method, res_credential_id...) do script keo tu tach ra. Do 14/09/2026: lan keo
# 2026-08-08 duoc ghi bang ban script cu KHONG co cot res_credential_id, va co 7 cap chuoi
# chi khac nhau o credential_id ben trong resource_labels_json (mot khoa that va
# apikey:UNKNOWN, hoac hai khoa). Khoa dung cot phang coi ca cap la mot chuoi, giu mot, va
# lam mat 8 mau ngay 05/05 cua pro-tuner.
POINT_KEY = ("gcp_project_id", "ts_utc", "metric_type", "resource_labels_json", "metric_labels_json")
LABEL_FIELDS = {"resource_labels_json", "metric_labels_json"}
CLASH_COLS = [*POINT_KEY, "pull_a", "count_a", "pull_b", "count_b", "kept"]


def normalized_labels(raw) -> str:
    """Nhan duoi dang chuoi JSON, CHUAN HOA truoc khi vao khoa.

    Hai lan keo ghi cung mot chuoi do bang chuoi JSON khac cach (thu tu khoa, ma hoa ky tu)
    thi so sanh chuoi tho se tach mot chuoi thanh hai - va moi ngay chung giua hai lan keo bi
    CONG DOI. Doc JSON roi ghi lai co sap xep khoa thi hai cach ghi do ra cung mot khoa.
    """
    if not raw:
        return ""
    try:
        return json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(raw)


def point_key(r: dict) -> tuple:
    return tuple(normalized_labels(r.get(c)) if c in LABEL_FIELDS else r.get(c, "") for c in POINT_KEY)


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
            f"Only exponentialBuckets is supported. Got: {json.dumps(options)[:200]}"
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
        raise SystemExit(f"bucketCounts is {len(out_path)} buckets long, more than the schema's {want}.")
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
    raise SystemExit(f"cannot find percentile {q} on a histogram totalling {total}.")


def select_folders(folder: Path) -> tuple[list[Path], list[str], list[str]]:
    """(lan keo se doc - MOI TRUOC CU SAU, ten bi bo qua, ten chi dinh ma khong khop khuon).

    `folder` chua san .jsonl thi do la MOT lan keo duoc chi dinh tuong minh bang --in:
    doc no, chi canh bao neu ten khong khop khuon.
    """
    if list(folder.glob("*.jsonl")):
        return [folder], [], ([] if PULL_DIR.match(folder.name) else [folder.name])
    children = sorted((p for p in folder.glob("*") if p.is_dir() and list(p.glob("*.jsonl"))),
                      key=lambda p: p.name, reverse=True)
    return ([p for p in children if PULL_DIR.match(p.name)],
            sorted(p.name for p in children if not PULL_DIR.match(p.name)), [])


def read_batch(folders: list[Path], by_method: bool):
    """Khu trung lap THEO DIEM giua cac lan keo, roi moi cong histogram theo ngay.

    Tra ve (gop, cach_cu, schema, so_diem, so_diem_rong, ca_lech, so_diem_trung).
    `folders` da sap MOI TRUOC CU SAU: hai lan keo cung count thi diem cua lan moi duoc giu.
    """
    schema = None
    schema_json = ""
    want = 0
    n_points = n_empty = n_dup = 0
    # khoa diem -> (count, ban ghi, ten lan keo). Ca 4 lan keo chi co vai chuc nghin
    # diem co histogram, nen giu ban ghi trong bo nho duoc - khong can doc hai luot.
    best: dict[tuple, tuple[int, dict, str]] = {}
    clashes: list[dict] = []

    for folder in folders:
        files = sorted(glob.glob(str(folder / "*.jsonl")))
        if not files:
            raise SystemExit(f"no .jsonl file in {folder}")
        for f in files:
            # Dong file ngay khi doc xong - khong giu handle mo.
            with open(f, encoding="utf-8") as handle:
                for line in handle:
                    r = json.loads(line)
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
                    elif json.dumps(opts, sort_keys=True) != schema_json:
                        raise SystemExit(
                            "a second bucketOptions appeared - the buckets do not line up, cannot merge.\n"
                            f"  in use: {json.dumps(schema)}\n"
                            f"  found : {json.dumps(opts)}\n"
                            f"  at    : {folder.name} {r['gcp_project_id']} {r['ts_utc']}"
                        )

                    k = point_key(r)
                    n = int(r["count"])
                    cur = best.get(k)
                    if cur is None:
                        best[k] = (n, r, folder.name)
                        continue
                    n_dup += 1
                    if cur[0] == n:
                        continue
                    clashes.append({**dict(zip(POINT_KEY, k)), "pull_a": cur[2], "count_a": cur[0],
                                    "pull_b": folder.name, "count_b": n, "kept": max(cur[0], n)})
                    if n > cur[0]:
                        best[k] = (n, r, folder.name)

    merged: dict[tuple, list[int]] = {}
    # Cach cu, de doi chung: p95 cua TUNG phut roi lay trung binh.
    old_way: dict[tuple, list[float]] = defaultdict(list)
    bounds = bucket_bounds(schema) if schema is not None else []
    for _n, r, _pull in best.values():
        key = (r["ts_ict"][:10], r["gcp_project_id"])
        if by_method:
            key = key + (r["res_method"],)
        o = pad_zeros(r["bucketCounts"], want)
        merged[key] = [a + b for a, b in zip(merged[key], o)] if key in merged else o
        approx, _, _ = percentile_from_histogram(o, bounds, 0.95)
        if approx is not None:
            old_way[key].append(approx)

    return merged, old_way, schema, n_points, n_empty, clashes, n_dup


def run(in_path: Path, out: str = "", by_method: bool = False) -> dict:
    folder = Path(in_path)
    folders, skipped, odd = select_folders(folder)
    if not folders:
        raise SystemExit(f"no pull folder matching {PULL_DIR.pattern} with .jsonl files in {folder}")

    print(f"read {len(folders)} pulls (newest first; on a clash the point with the LARGER count is kept):",
          file=sys.stderr)
    for p in folders:
        print(f"    {p.name}", file=sys.stderr)
    if skipped:
        print(f"skipped {len(skipped)} folders (name does not match {PULL_DIR.pattern}):", file=sys.stderr)
        for n in skipped:
            print(f"    {n}", file=sys.stderr)
    for n in odd:
        print(f"  WARNING: {n} does not match {PULL_DIR.pattern} - read anyway because --in named it",
              file=sys.stderr)

    merged, old_way, schema, n_points, n_empty, clashes, n_dup = read_batch(folders, by_method)
    if schema is None:
        raise SystemExit(
            f"read {n_points} points but NONE carries a histogram.\n"
            "They are all minutes with no calls. Re-check the input folder."
        )
    bounds = bucket_bounds(schema)

    print(f"  {n_points} points, of which {n_empty} minutes had no calls", file=sys.stderr)
    print(f"  {n_dup} points repeated across pulls, {len(clashes)} of them with a different count",
          file=sys.stderr)
    print(f"  bucketOptions: {json.dumps(schema)}", file=sys.stderr)
    print(f"  the last bucket starts at {bounds[-1]:.1f}s", file=sys.stderr)
    print(f"  -> {len(merged)} result rows", file=sys.stderr)

    cols = ["day", "project"] + (["res_method"] if by_method else []) + [
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
    print(f"  total calls: {total_calls:,}", file=sys.stderr)

    clash_file = None
    if out:
        with open(out, "w", encoding="utf-8", newline="") as h:
            w = csv.DictWriter(h, fieldnames=cols, quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(row)
        print(f"wrote: {out}", file=sys.stderr)
        # Luon ghi, ke ca khi rong: chi co dong tieu de nghia la DA CHAY va KHONG lech.
        # Nam CANH --out, khong phai trong thu muc lan keo nao.
        clash_file = Path(out).with_name(Path(out).stem + ".lech.csv")
        with clash_file.open("w", encoding="utf-8", newline="") as h:
            w = csv.DictWriter(h, fieldnames=CLASH_COLS, quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(clashes)
        print(f"clash file: {clash_file} ({len(clashes)} rows)", file=sys.stderr)
    else:
        w = csv.DictWriter(sys.stdout, fieldnames=cols)
        w.writeheader()
        w.writerows(row)
        for c in clashes:
            print(f"  CLASH {c['gcp_project_id']} {c['ts_utc']} {c['resource_labels_json']}:"
                  f" {c['pull_a']}={c['count_a']}  {c['pull_b']}={c['count_b']}  -> kept {c['kept']}",
                  file=sys.stderr)

    return {"folders": [p.name for p in folders], "skipped": skipped, "odd": odd,
            "rows": row, "clashes": len(clashes), "clash_file": clash_file}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False)
    parser.add_argument("--in", dest="in_path", default=str(DEFAULT_IN),
                        help="One pull folder, or the parent folder (reads EVERY pull matching the pattern)")
    parser.add_argument("--out", default="", help="Output CSV file (default: print to the screen)")
    parser.add_argument("--by-method", dest="by_method", action="store_true",
                        help="Also split by res_method instead of merging the whole project")
    args = parser.parse_args()
    run(Path(args.in_path), args.out, args.by_method)


if __name__ == "__main__":
    main()
