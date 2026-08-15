"""Dung fact_perf_daily + fact_latency_daily - buoc (6) cua khau nap.

    python db/build_performance.py

HAI BANG, HAI NGUON, HAI DO MIN - va do la ly do chung khong o chung
--------------------------------------------------------------------
fact_perf_daily    tu fact_monitoring, phep do api/request_count.
                   Co response_code va method, khong co model.
                   -> (day, agent, method, response_code)

fact_latency_daily  tu do-tre-theo-ngay-ict.csv, do scripts/merge_latency_daily.py
                   sinh ra bang cach GOP HISTOGRAM roi moi doc moc phan vi.
                   Khong co response_code, va cung khong the co: phan vi khong cong
                   duoc, nen con so dung chi ton tai o muc ca ngay ca agent.
                   -> (day, agent)

VI SAO KHONG LAY p95 THANG TU fact_monitoring
---------------------------------------------
fact_monitoring CO cot p95 (158.956 dong, hau to `_p95` trong `phep_do`) nhung do
la p95 CUA TUNG PHUT. Trung binh cac p95 khong ra p95 cua ngay: trung binh cua
p95=2,1s tren 100 luot va p95=8,4s tren 2 luot cho 5,25s, trong khi so that
khoang 2,3s. Chinh file CSV kia da do do lech: cot `lech_phan_tram` cho thay
cach trung binh sai toi 19,3% ngay o dong thu hai.

Nen p95 trong fact_monitoring la du lieu THO de tra nguoc, khong phai nguon cua
bang tong hop. Bang tong hop lay tu histogram.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import connect  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LATENCY_CSV = (ROOT / "data" / "raw_google_console" / "do_tre_phan_bo"
               / "latency-daily.csv")

# Duoi nguong nay thi phan vi khong noi len dieu gi - 3 luot goi thi "p95" chi la
# luot cham nhat. Cot `du_mau` de bao cao biet luc nao phai ghi '-' thay vi mot so.
MIN_SAMPLES = 10


def num(x: str):
    """Chuoi -> float, o trong -> None. CSV khong phan biet '' voi 0."""
    x = (x or "").strip()
    return float(x) if x else None


def load_call_counts(cn, dc) -> int:
    """So luot theo ma tra ve, tu chinh fact_monitoring.

    LOC BANG dim_metric_alias chu khong bang LIKE tren ten: doi ten phep do thi
    LIKE tra ve 0 dong lang le, con bang alias thi khau nap fact_monitoring da
    dung tu truoc do (no bat moi ten la).

    PHAI LOC dich_vu - day la cai bay chinh cua bang nay
    ----------------------------------------------------
    serviceruntime/api/request_count dem MOI Google API ma project goi, khong
    rieng gi AI. Trong 163.685 dong:
        drive.googleapis.com                147.969   90,4%
        generativelanguage.googleapis.com    14.179    8,7%
        con lai (apphub, dataform, compute...) 1.537
    Gop het vao mot bang ten la "hieu nang agent" thi 90% con so tren dashboard
    la luu luong Google Drive. Va no se trong y nhu that: cung don vi, cung ma
    tra ve, cung do thi len xuong.
    """
    dong = connect.query(cn, """
        SELECT substr(CAST(m.ts_local AS TEXT), 1, 10), m.agent_id,
               m.method, m.response_code, SUM(m.value)
        FROM fact_monitoring m
        JOIN dim_metric_alias d
          ON d.source = 'monitoring' AND d.raw_name = m.metric_type
        WHERE d.measures = 'calls'
          AND m.service = 'generativelanguage.googleapis.com'
          AND m.method IS NOT NULL AND m.method <> ''
          AND m.response_code IS NOT NULL AND m.response_code <> ''
        GROUP BY 1, 2, 3, 4
    """)
    return connect.insert_many(cn, dc, "fact_perf_daily",
                        ["day", "agent_id", "method", "response_code", "calls"],
                        [(n, a, p, m, int(v)) for n, a, p, m, v in dong])


def load_latency(cn, dc) -> tuple[int, list[str]]:
    """Do tre da gop histogram, doc tu CSV. Tra (so dong, project khong biet)."""
    if not LATENCY_CSV.exists():
        raise SystemExit(
            f"Khong co {LATENCY_CSV}\n"
            f"  Chay truoc: python scripts/pull_latency_distribution.py\n"
            f"              python scripts/merge_latency_daily.py")

    agents = connect.agent_lookup(cn)          # gcp_project_id -> agent_id
    rows, unknown = [], []
    with LATENCY_CSV.open(encoding="utf-8-sig", newline="") as h:
        for r in csv.DictReader(h):
            aid = agents.get(r["project"])
            if aid is None:
                # KHONG bo qua im lang. Mot project la nghia la hoac dim_agent
                # thieu mot dong, hoac ai do doi ten project tren GCP - ca hai
                # deu phai co nguoi nhin thay.
                unknown.append(r["project"])
                continue
            n = int(float(r["samples"]))
            rows.append((r["day"], aid, n,
                         num(r["p50_s"]), num(r["p95_s"]),
                         num(r["p95_bucket_from"]), num(r["p95_bucket_to"]), num(r["p99_s"]),
                         n >= MIN_SAMPLES))
    n = connect.insert_many(cn, dc, "fact_latency_daily",
                     ["day", "agent_id", "samples", "p50_seconds", "p95_seconds",
                      "p95_bucket_from", "p95_bucket_to", "p99_seconds",
                      "enough_samples"], rows)
    return n, sorted(set(unknown))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=connect.DEFAULT_DSN)
    args = p.parse_args()

    cn, dc = connect.open_db(args.db)
    cur = cn.cursor()
    cur.execute("DELETE FROM fact_perf_daily")
    cur.execute("DELETE FROM fact_latency_daily")

    n_calls = load_call_counts(cn, dc)
    n_latency, unknown_projects = load_latency(cn, dc)

    total_calls = connect.query_one(cn, "SELECT SUM(calls) FROM fact_perf_daily")[0]
    by_code = dict(connect.query(cn, "SELECT response_code, SUM(calls) FROM fact_perf_daily"
                               " GROUP BY response_code ORDER BY 2 DESC"))
    few_samples = connect.query_one(cn, "SELECT COUNT(*) FROM fact_latency_daily"
                                " WHERE enough_samples = FALSE")[0]
    print(f"  fact_perf_daily    {n_calls:>5} dong | {int(total_calls):,} luot")
    print(f"  theo ma tra ve     {by_code}")
    print(f"  fact_latency_daily  {n_latency:>5} dong | {few_samples} ngay khong du mau"
          f" (<{MIN_SAMPLES} luot)")

    # ================================================== nghiem thu
    # Doi chieu voi CHINH nguon o moi lan chay, khong ghim so.
    src_calls = connect.query_one(cn, """
        SELECT SUM(m.value) FROM fact_monitoring m
        JOIN dim_metric_alias d ON d.source='monitoring' AND d.raw_name = m.metric_type
        WHERE d.measures='calls' AND m.service = 'generativelanguage.googleapis.com'
          AND m.method IS NOT NULL AND m.method <> ''
          AND m.response_code IS NOT NULL AND m.response_code <> ''""")[0]

    errors = []
    if int(total_calls or 0) != int(src_calls or 0):
        errors.append(f"so luot {int(total_calls or 0):,} != {int(src_calls or 0):,}"
                   f" trong fact_monitoring")
    if unknown_projects:
        errors.append(f"project khong co trong dim_agent: {unknown_projects}")
    if n_latency == 0:
        errors.append("khong nap duoc dong do tre nao")
    # p95 phai nam trong chinh o chua no. Lech nghia la doc nham cot khi anh xa
    # CSV - loi khong the thay bang mat vi moi so deu trong nhu that.
    outside_bucket = connect.query_one(cn, """
        SELECT COUNT(*) FROM fact_latency_daily
        WHERE p95_seconds IS NOT NULL AND p95_bucket_from IS NOT NULL
          AND (p95_seconds < p95_bucket_from OR p95_seconds > p95_bucket_to)""")[0]
    if outside_bucket:
        errors.append(f"{outside_bucket} dong co p95 nam ngoai o chua no - anh xa cot sai")
    # p50 <= p95 <= p99 la tinh chat cua phan vi, khong phai cua du lieu.
    wrong_order = connect.query_one(cn, """
        SELECT COUNT(*) FROM fact_latency_daily
        WHERE (p50_seconds IS NOT NULL AND p95_seconds IS NOT NULL AND p50_seconds > p95_seconds)
           OR (p95_seconds IS NOT NULL AND p99_seconds IS NOT NULL AND p95_seconds > p99_seconds)""")[0]
    if wrong_order:
        errors.append(f"{wrong_order} dong co p50>p95 hoac p95>p99")

    if errors:
        cn.rollback()
        raise SystemExit("NGHIEM THU KHONG DAT - da huy:\n  " + "\n  ".join(loi))
    cn.commit()
    print("  NGHIEM THU DAT")


if __name__ == "__main__":
    main()
