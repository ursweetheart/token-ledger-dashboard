"""Keo phan bo do tre (histogram) tu Cloud Monitoring - chi doc.

VI SAO CO SCRIPT NAY
--------------------
`pull_monitoring.py` xin do tre bang ALIGN_PERCENTILE_95/99, tuc ep ca mot
histogram thanh MOT con so cho moi 60 giay. Phan vi cua phan vi khong cong
duoc: trung binh cua p95=2,1s (tren 100 luot) va p95=8,4s (tren 2 luot) ra
5,25s, trong khi p95 that cua ca hai phut khoang 2,3s.

Histogram thi cong duoc. Cong so luot o tung o qua 1.440 phut roi doc moc 95%
se ra p95 CHINH XAC cua ca ngay. Nen script nay xin ALIGN_DELTA va giu nguyen
bucketCounts.

Chi tiet: docs/mui-gio-2026-08-08.md muc M-C.

PHAM VI
-------
Chi mot phep do: serviceruntime.googleapis.com/api/request_latencies
Mac dinh chi service generativelanguage - loc NGAY TREN API, vi rieng
pro-tuner co 137.493 diem cua drive.googleapis.com va do la rac (quy tac 3
trong docs/plan-xay-dung-database-2026-08-07.md muc 4.6).

DINH DANG RA
------------
JSONL, moi dong mot diem. CSV khong chua duoc histogram: mot o mot so.
KHONG tinh san p95 o day. Script nay ghi lai cai Google tra ve, khong hon -
tinh toan thuoc ve tang sau, chay lai duoc vo han, con cao lai thi khong.

AN TOAN
-------
Tu choi ghi vao thu muc da co du lieu. Do la kich ban X2 trong
docs/van-de-xu-ly-du-lieu-2026-08-08.md: cao de len la mat vinh vien, vi
`data/` nam trong .gitignore va Google chi giu 196 ngay.

Auth dung gcloud login san co. Moi loi goi deu la GET. Khong ghi credential.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pull_monitoring import (  # noqa: E402
    API,
    ICT,
    PROJECTS,
    access_token,
    gcloud_path,
    paged,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "raw_google_console" / "do_tre_phan_bo"  # vi-ok: on-disk path

METRIC = "serviceruntime.googleapis.com/api/request_latencies"
GENLANG_SERVICE = "generativelanguage.googleapis.com"

# ALIGN_DELTA giu nguyen histogram. Moi aligner ALIGN_PERCENTILE_* deu lam
# sup no thanh mot so - chinh la thu script nay sinh ra de tranh.
ALIGNER = "ALIGN_DELTA"


def build_filter(service: str) -> str:
    parts = [f'metric.type="{METRIC}"']
    if service:
        parts.append(f'resource.labels.service="{service}"')
    return " AND ".join(parts)


def rows_for(project: str, token: str, start: datetime, end: datetime,
             align: int, service: str) -> list[dict]:
    params = {
        "filter": build_filter(service),
        "interval.startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "interval.endTime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "aggregation.alignmentPeriod": f"{align}s",
        "aggregation.perSeriesAligner": ALIGNER,
        "view": "FULL",
        "pageSize": "10000",
    }
    url = f"{API}/projects/{project}/timeSeries?" + urllib.parse.urlencode(params)

    rows: list[dict] = []
    for series in paged(url, token, "timeSeries"):
        metric_labels = series.get("metric", {}).get("labels", {})
        resource_labels = series.get("resource", {}).get("labels", {})

        for point in series.get("points", []):
            distribution = point.get("value", {}).get("distributionValue")
            # Mot diem khong phai phan bo nghia la gia dinh nen cua script sai.
            # Dung han con hon ghi ra mot file trong ma khong ai nhan ra.
            if distribution is None:
                raise SystemExit(
                    f"a point has no distributionValue in {project}.\n"
                    f"Got: {json.dumps(point.get('value', {}))[:300]}\n"
                    "Check METRIC and ALIGNER before running again."
                )

            stamp = point["interval"]["endTime"].replace("Z", "+00:00")
            moment = datetime.fromisoformat(stamp).astimezone(timezone.utc)

            rows.append({
                "metric_type": METRIC,
                "gcp_project_id": project,
                "ts_utc": moment.strftime("%Y-%m-%d %H:%M:%S"),
                "ts_ict": moment.astimezone(ICT).strftime("%Y-%m-%d %H:%M:%S"),
                "aligner": ALIGNER,
                "res_service": resource_labels.get("service", ""),
                "res_method": resource_labels.get("method", ""),
                "res_location": resource_labels.get("location", ""),
                # BAT BUOC co. Cung mot phut, cung mot method van co NHIEU chuoi
                # so lieu khac nhau neu goi bang nhieu API key. Thieu cot nay thi
                # chung trong nhu ban ghi trung lap, va moi phep doi chieu se
                # lay nham mot chuoi lam dai dien cho ca nhom.
                "res_credential_id": resource_labels.get("credential_id", ""),
                # KHONG co cot response_code. File mo ta cua phep do nay khong
                # he co khoa "labels" - Google khong gan ma tra ve vao do tre.
                # Mot cot luon rong se bi doc nham thanh "khong co loi nao".
                # metric_labels_json ben duoi van giu nguyen su that.
                #
                # Bon truong duoi la CAI CAN GIU. bucketOptions cho biet moi o
                # ung voi khoang giay nao - thieu no thi bucketCounts vo nghia.
                #
                # Mac dinh None chu KHONG phai 0 hay {} - quy tac 5 muc 4.6:
                # thieu thi nap NULL. "0" nghia la do duoc va bang khong.
                "count": distribution.get("count"),
                "mean": distribution.get("mean"),
                "bucketOptions": distribution.get("bucketOptions"),
                "bucketCounts": distribution.get("bucketCounts"),
                "metric_labels_json": json.dumps(metric_labels, ensure_ascii=False,
                                                 sort_keys=True),
                "resource_labels_json": json.dumps(resource_labels, ensure_ascii=False,
                                                   sort_keys=True),
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False)
    parser.add_argument("--projects", default=",".join(PROJECTS),
                        help="Comma-separated project_id list")
    parser.add_argument("--days", type=int, default=196,
                        help="Days to go back (default 196 = the most Google retains)")
    parser.add_argument("--align", type=int, default=60,
                        help="Grain in seconds (default 60 = the finest Google has)")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--all-services", action="store_true",
                        help="Pull every service, not only generativelanguage")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only print what would happen: no network call, no file written")
    parser.add_argument("--gcloud", default="", help="Path to gcloud if it is not on PATH")
    args = parser.parse_args()

    if args.align < 60:
        raise SystemExit(f"--align {args.align} is below 60s. Google only stores 60s resolution.")

    service = "" if args.all_services else GENLANG_SERVICE
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=args.days)

    # Ten thu muc mang CA khoang CA do min. Bo mot trong hai la lap lai X4:
    # thu muc `2026-08-06-1m` bi doc nham thanh "1 thang" suot mot tuan.
    label = f"{args.align // 60}m" if args.align < 3600 else f"{args.align // 3600}h"
    out_dir = Path(args.out) / f"{end:%Y-%m-%d}-{args.days}d-{label}"

    projects = [p.strip() for p in args.projects.split(",") if p.strip()]

    print(f"metric  : {METRIC}")
    print(f"aligner : {ALIGNER}  (histogram kept intact)")
    print(f"service : {service or 'ALL'}")
    print(f"range   : {start:%Y-%m-%d %H:%M} -> {end:%Y-%m-%d %H:%M} UTC ({args.days} days)")
    print(f"grain   : {args.align}s ({label})")
    print(f"writing : {out_dir}")
    print(f"projects: {len(projects)} - {', '.join(projects)}\n")

    if args.dry_run:
        print("--dry-run: stopping here. No network call, no file written.")
        return

    # Chan X2: khong bao gio ghi de len mot ban cao da co.
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(
            f"The folder already holds data: {out_dir}\n"
            "this script never overwrites. Google keeps only 196 days and `data/` is not\n"
            "in git - overwriting loses it forever. Change --out or rename the old folder."
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    gcloud = args.gcloud or gcloud_path()
    total = 0
    for project in projects:
        print(f"[{project}]")
        # Lay lai token moi project: mot vong quet rong co the song lau hon token.
        rows = rows_for(project, access_token(gcloud), start, end, args.align, service)

        target = out_dir / f"{project}.jsonl"
        with target.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

        # r["count"] co the la None (quy tac 5). Dem rieng de biet co bao nhieu
        # diem khong do duoc, thay vi lang le coi chung bang 0.
        measured = [r for r in rows if r["count"] is not None]
        calls = sum(int(r["count"]) for r in measured)
        missing = len(rows) - len(measured)
        print(f"  {len(rows):>7} points | {calls:>9,} calls | {target.name}")
        if missing:
            print(f"          {missing} points have NO count field (written as NULL, not 0)")
        print()
        total += len(rows)

    print(f"done. {total} points, {len(projects)} projects.")
    if total == 0:
        print("\nWARNING: no points at all. Re-check the Monitoring Viewer permission and the time range.")
        sys.exit(1)


if __name__ == "__main__":
    main()
