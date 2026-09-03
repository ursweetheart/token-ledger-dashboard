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
import logs  # noqa: E402

log = logs.get_logger("build_performance")

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
    rows = connect.query(cn, """
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
    # `source` khai TUONG MINH, khong dua vao DEFAULT cua migration 008. DEFAULT
    # o do la de dap 669 dong LICH SU; moi lan ghi MOI phai tu noi minh la nguon
    # nao, neu khong thi ngay them nguon thu hai se co dong khong ai biet tu dau.
    return connect.insert_many(cn, dc, "fact_perf_daily",
                        ["day", "agent_id", "method", "response_code", "calls",
                         "source"],
                        [(n, a, p, m, int(v), "monitoring")
                         for n, a, p, m, v in rows])


def load_latency(cn, dc) -> tuple[int, list[str]]:
    """Do tre da gop histogram, doc tu CSV. Tra (so dong, project khong biet)."""
    if not LATENCY_CSV.exists():
        raise SystemExit(
            f"{LATENCY_CSV} not found\n"
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
                      "enough_samples", "source"],
                     [(*r, "monitoring") for r in rows])
    return n, sorted(set(unknown))


def load_gateway_latency(cn, dc) -> int:
    """Phan vi CHINH XAC cho nguon gateway, tinh thang tu `duration_ms` tho.

    KHAC HAN load_latency() O BAN CHAT PHEP DO
    ------------------------------------------
        monitoring   histogram da gop -> doc mot moc phan vi ra bang NOI SUY
                     trong mot o. Do 03/09: be rong o trung binh bang 54-67%
                     chinh gia tri p95 cua ba agent cham nhat.
        gateway      tung gia tri duration_ms -> percentile_cont doc thang.
                     KHONG co sai so noi suy nao.

    Nen `p95_bucket_from` / `p95_bucket_to` de NULL. Chung mo ta sai so cua
    histogram, ma so tho khong co sai so do. Ghi 0 la noi "sai so bang khong do
    duoc"; ghi gia tri nao khac la bia. NULL noi dung: khong ap dung.

    MOI NGUON MOT DONG, KHONG GOP TRUNG BINH voi monitoring. Trung binh cua hai
    phan vi la mot con so khong thuoc ve phep do nao - chinh file nay da ghi lai
    phep do chung minh dieu do o docstring dau file.

    BA BO LOC, VA MOT BO LOC CO Y KHONG DAT
    ---------------------------------------
    `duration_ms IS NOT NULL`  phai co phep do. Gateway ghi 0 cho MOI luot hong
                               (ke ca luot da toi nha cung cap), va tang nap da
                               NULLIF(...,0) - nen 0 khong bao gio vao day.

    `cache_hit IS NOT TRUE`    luot trung dem KHONG toi nha cung cap, nen do tre
                               cua no do mot thu khac han. Hom nay khong doi gi
                               (0/38 dong trung dem, p95 bang nhau ca hai cach),
                               nhung se doi ngay cache duoc bat lai.
                               PHAI viet `IS NOT TRUE`, khong duoc `NOT
                               cache_hit` - cot cho phep NULL, cach viet sai vut
                               sach 38/38 dong.

    `outcome = 'success'`      CO Y KHONG DAT, khac voi build_usage_daily.
                               Do tre cua mot luot HONG van la do tre that -
                               nguoi goi van cho ngan ay lau. Loai no ra la lam
                               dep so mot cach im lang. Hom nay cau hoi nay chua
                               co hau qua (3/3 luot hong deu co duration_ms
                               NULL), nhung khi LiteLLM bat dau ghi do tre cho
                               luot hong thi lua chon nay moi la lua chon dung.
    """
    rows = connect.query(cn, f"""
        SELECT CAST(ts_local AS DATE), agent_id, COUNT(*),
               percentile_cont(0.50) WITHIN GROUP (ORDER BY duration_ms) / 1000.0,
               percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) / 1000.0,
               percentile_cont(0.99) WITHIN GROUP (ORDER BY duration_ms) / 1000.0
        FROM fact_call
        WHERE source = 'gateway' AND ts_local IS NOT NULL
          AND duration_ms IS NOT NULL
          AND cache_hit IS NOT TRUE
        GROUP BY 1, 2
    """)
    out = [(day, aid, n, p50, p95, None, None, p99, n >= MIN_SAMPLES, "gateway")
           for day, aid, n, p50, p95, p99 in rows]
    return connect.insert_many(cn, dc, "fact_latency_daily",
                        ["day", "agent_id", "samples", "p50_seconds",
                         "p95_seconds", "p95_bucket_from", "p95_bucket_to",
                         "p99_seconds", "enough_samples", "source"], out)


def chi_gateway(cn, dc) -> None:
    """Dung lai CHI phan `gateway` cua fact_latency_daily. Khong doc CSV.

    VI SAO CO CHE DO NAY (them 03/09/2026)
    --------------------------------------
    `scripts/refresh_gateway.py` la duong lam moi NHANH, chay duoc vong lap
    (`--every 120`). No phai dung lai moi bang dan xuat ma nguon gateway nuoi -
    ke ca fact_latency_daily.

    Nhung `main()` day du KHONG dung duoc o do: `load_latency()` doc
    `latency-daily.csv`, mot file CAO TAY (`pull_latency_distribution.py` +
    `merge_latency_daily.py`), va no DUNG HAN neu file vang mat. Do 03/09: file
    ay cu 4 ngay. Mot vong lap chay ca buoi ma phu thuoc mot file phai cao tay la
    qua bom hen gio dat o noi khong ai nhin.

    `load_gateway_latency()` thi KHONG can CSV - no doc duy nhat
    `fact_call.duration_ms`. Ca 4 cho nhac `LATENCY_CSV` deu nam o nhanh
    `load_latency()`. Nen phan gateway tach ra chay rieng duoc.

    GOI LAI CHINH `load_gateway_latency()`, KHONG CHEP PHEP TINH
    -----------------------------------------------------------
    Chep phep tinh percentile sang day la tao ban sao thu hai cua mot phep do, va
    ban sao SE TROI - dung bay da dinh 21/08 khi tools/dien_tap_gateway.py chep
    cau SQL cua store.py roi do bang logic da bi bo.

    XOA CO DIEU KIEN - CHO NGUY HIEM NHAT CUA HAM NAY
    -------------------------------------------------
    `fact_latency_daily` co 340 dong: monitoring 339, gateway 1. Quen `WHERE` la
    mat 339 dong monitoring, MA CHUNG CHI DUNG LAI DUOC NEU CSV CON - tuc phuc hoi
    phu thuoc dung cai file ma ham nay sinh ra de tranh phu thuoc.
    Ham tu dem CA HAI nguon truoc/sau va dung han neu monitoring doi.
    """
    truoc = {k: v for k, v in connect.query(
        cn, "SELECT source, COUNT(*) FROM fact_latency_daily GROUP BY 1")}

    cur = cn.cursor()
    cur.execute("DELETE FROM fact_latency_daily WHERE source = 'gateway'")
    n_gw = load_gateway_latency(cn, dc)

    sau = {k: v for k, v in connect.query(
        cn, "SELECT source, COUNT(*) FROM fact_latency_daily GROUP BY 1")}

    # Dem MOI nguon, khong chi nguon vua dung lai. Chi dem gateway thi mot lenh
    # DELETE quen WHERE VAN cho ket qua "dung" - gateway van ra dung so dong sau
    # khi nap lai, trong khi monitoring da bien mat.
    khac = {k: (truoc.get(k, 0), sau.get(k, 0))
            for k in set(truoc) | set(sau)
            if k != "gateway" and truoc.get(k, 0) != sau.get(k, 0)}
    if khac:
        cn.rollback()
        raise SystemExit(
            "ACCEPTANCE FAILED - rolled back: che do --chi-gateway da dung vao"
            f" nguon khac: {khac}")

    cn.commit()
    log.info("  --chi-gateway: fact_latency_daily gateway %d -> %d dong"
             " | cac nguon khac KHONG doi (%s)",
             truoc.get("gateway", 0), n_gw,
             ", ".join(f"{k}={v}" for k, v in sorted(sau.items()) if k != "gateway"))
    cn.close()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=connect.DEFAULT_DSN)
    p.add_argument("--chi-gateway", action="store_true",
                   help="CHI dung lai phan `gateway` cua fact_latency_daily."
                        " Khong doc CSV, khong dung fact_perf_daily, khong dung"
                        " dong `monitoring`. Danh cho scripts/refresh_gateway.py.")
    args = p.parse_args()

    cn, dc = connect.open_db(args.db)

    if args.chi_gateway:
        return chi_gateway(cn, dc)

    cur = cn.cursor()
    cur.execute("DELETE FROM fact_perf_daily")
    cur.execute("DELETE FROM fact_latency_daily")

    n_calls = load_call_counts(cn, dc)
    n_latency, unknown_projects = load_latency(cn, dc)
    n_gw = load_gateway_latency(cn, dc)

    total_calls = connect.query_one(cn, "SELECT SUM(calls) FROM fact_perf_daily")[0]
    by_code = dict(connect.query(cn, "SELECT response_code, SUM(calls) FROM fact_perf_daily"
                               " GROUP BY response_code ORDER BY 2 DESC"))
    few_samples = connect.query_one(cn, "SELECT COUNT(*) FROM fact_latency_daily"
                                " WHERE enough_samples = FALSE")[0]
    log.info("  fact_perf_daily    %5d rows | %s calls", n_calls, f"{int(total_calls):,}")
    log.info("  by response code   %s", by_code)
    log.info("  fact_latency_daily %5d rows | %d days without enough samples"
             " (<%d calls)", n_latency + n_gw, few_samples, MIN_SAMPLES)
    log.info("  ... of which  monitoring %d (histogram, co o sai so)"
             " | gateway %d (so tho, o = NULL)", n_latency, n_gw)

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
        errors.append(f"projects missing from dim_agent: {unknown_projects}")
    if n_latency == 0:
        errors.append("no latency row could be loaded")
    # Phan vi tu so THO khong duoc mang o histogram. Mot dong gateway co
    # p95_bucket_* khac NULL nghia la ai do da dan sai so cua phep do KHAC len
    # mot con so von khong co sai so do - va no se trong y nhu that.
    gw_co_o = connect.query_one(cn, """
        SELECT COUNT(*) FROM fact_latency_daily
        WHERE source = 'gateway'
          AND (p95_bucket_from IS NOT NULL OR p95_bucket_to IS NOT NULL)""")[0]
    if gw_co_o:
        errors.append(f"{gw_co_o} gateway rows carry a histogram bucket -"
                      f" raw percentiles have no interpolation error to describe")
    # Moi (ngay, agent, nguon) dung MOT dong. Hai dong nghia la khoa chinh cua
    # migration 008 khong lam viec, va mot trong hai nguon dang bi ghi de.
    trung_khoa = connect.query_one(cn, """
        SELECT COUNT(*) FROM (
            SELECT day, agent_id, source FROM fact_latency_daily
            GROUP BY 1, 2, 3 HAVING COUNT(*) > 1) t""")[0]
    if trung_khoa:
        errors.append(f"{trung_khoa} (day, agent, source) keys appear twice")
    # p95 phai nam trong chinh o chua no. Lech nghia la doc nham cot khi anh xa
    # CSV - loi khong the thay bang mat vi moi so deu trong nhu that.
    outside_bucket = connect.query_one(cn, """
        SELECT COUNT(*) FROM fact_latency_daily
        WHERE p95_seconds IS NOT NULL AND p95_bucket_from IS NOT NULL
          AND (p95_seconds < p95_bucket_from OR p95_seconds > p95_bucket_to)""")[0]
    if outside_bucket:
        errors.append(f"{outside_bucket} rows have a p95 outside their own bucket - wrong column mapping?")
    # p50 <= p95 <= p99 la tinh chat cua phan vi, khong phai cua du lieu.
    wrong_order = connect.query_one(cn, """
        SELECT COUNT(*) FROM fact_latency_daily
        WHERE (p50_seconds IS NOT NULL AND p95_seconds IS NOT NULL AND p50_seconds > p95_seconds)
           OR (p95_seconds IS NOT NULL AND p99_seconds IS NOT NULL AND p95_seconds > p99_seconds)""")[0]
    if wrong_order:
        errors.append(f"{wrong_order} rows have p50>p95 or p95>p99")

    if errors:
        cn.rollback()
        raise SystemExit("ACCEPTANCE FAILED - rolled back:\n  "
                         + "\n  ".join(errors))
    cn.commit()
    log.info("  acceptance passed")


if __name__ == "__main__":
    main()
