"""Pull Cloud Monitoring time series for the agent projects — read only.

Design decisions, per docs/uu-tien-thu-thap-du-lieu-2026-08-06.md:

  * Pull complete, transform nothing. Every metric label is kept, including the
    ones that look redundant: `res_service` and `limit_name` are precisely the
    two labels that save us from trap 1 and trap 2 in that document.
  * Metric types are DISCOVERED from the descriptor list rather than hardcoded,
    and the full descriptor list is saved next to the data. Google renames these
    (Vertex AI -> Agent Platform); a hardcoded name fails silently by returning
    an empty series, which is the worst possible failure mode here.
  * One directory per pull date. Raw output is never edited afterwards; the
    filtering lives in check_monitoring.py and reads a copy.

Auth uses the caller's existing gcloud login. No credential is written anywhere.
Every call is a GET against monitoring.googleapis.com.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "raw_google_console" / "du_lieu_giam_sat"

API = "https://monitoring.googleapis.com/v3"
ICT = timezone(timedelta(hours=7))

# The seven projects that bill through rangdong.com.vn - GMSSub and actually
# call the API. `tla-ralli` is deliberately absent: the Ralli software does not
# route through GCP at all (see doc section 1b), so it would return an empty
# series and read as a failed pull.
PROJECTS = [
    "crm-500509",
    "feedback-dms-tiep-thi",
    "ai-chatbot-contract",
    "tools-quizz",
    "tranquil-post-471401-c1",
    "multimodal-invoice",
    "pro-tuner-454203-v3",
]

# Always pulled. These two carry response_code and latency, and they are the
# only source for either.
SERVICERUNTIME = [
    "serviceruntime.googleapis.com/api/request_count",
    "serviceruntime.googleapis.com/api/request_latencies",
]

# Default slice of the generativelanguage family. --all-genlang widens this to
# every descriptor the project exposes.
GENLANG_PREFIX = "generativelanguage.googleapis.com/"
GENLANG_WANTED = ("token_count", "request")

# Labels promoted to their own column because we filter or group on them. The
# untouched originals stay in metric_labels_json / resource_labels_json.
#
# Note the two different `method` labels. The metric one (on quota metrics) is
# almost always empty; the resource one (on consumed_api) carries the full API
# method name and is what defines "a request". They are kept in separate columns
# on purpose — collapsing them would silently lose the useful one.
FLAT_METRIC_LABELS = ["model", "method", "response_code", "thinking_enabled",
                      "output_modality", "limit_name"]
FLAT_RESOURCE_LABELS = {"res_service": "service", "res_location": "location",
                        "res_method": "method", "res_credential_id": "credential_id"}

# Both timestamps stay ISO here. Display formatting and row order are decisions
# about reading, not about recording, and they belong in make_readable.py --
# otherwise changing a date format would mean re-downloading 240 days from
# Google, which is absurd for something already sitting on disk.
COLUMNS = ["metric_alias", "metric_type", "gcp_project_id", "ts_utc", "ts_ict",
           *FLAT_METRIC_LABELS, *FLAT_RESOURCE_LABELS, "aligner", "value", "unit",
           "metric_labels_json", "resource_labels_json"]


def gcloud_path() -> str:
    for name in ("gcloud", "gcloud.cmd", "gcloud.CMD"):
        found = shutil.which(name)
        if found:
            return found
    raise SystemExit(
        "Khong tim thay gcloud trong PATH.\n"
        "Mo terminal moi sau khi cai, hoac chi duong dan bang --gcloud."
    )


def access_token(gcloud: str) -> str:
    result = subprocess.run([gcloud, "auth", "print-access-token"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            "gcloud auth print-access-token that bai:\n"
            f"{result.stderr.strip()}\n"
            "Chay `gcloud auth login` roi thu lai."
        )
    return result.stdout.strip()


def get(url: str, token: str) -> dict:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")[:800]
        raise SystemExit(f"HTTP {error.code} khi goi\n  {url}\n{body}") from error


def paged(url: str, token: str, key: str) -> list[dict]:
    items: list[dict] = []
    page_token = ""
    while True:
        page = get(url + (f"&pageToken={page_token}" if page_token else ""), token)
        items.extend(page.get(key, []))
        page_token = page.get("nextPageToken", "")
        if not page_token:
            return items


def list_descriptors(project: str, token: str) -> list[dict]:
    """Every descriptor from the two families we care about."""
    found: list[dict] = []
    for prefix in (GENLANG_PREFIX, "serviceruntime.googleapis.com/api/"):
        query = urllib.parse.quote(f'metric.type = starts_with("{prefix}")')
        url = f"{API}/projects/{project}/metricDescriptors?pageSize=500&filter={query}"
        found.extend(paged(url, token, "metricDescriptors"))
    return found


def wanted(descriptors: list[dict], all_genlang: bool) -> list[dict]:
    chosen: dict[str, dict] = {}
    for descriptor in descriptors:
        metric_type = descriptor.get("type", "")
        if metric_type in SERVICERUNTIME:
            chosen[metric_type] = descriptor
        elif metric_type.startswith(GENLANG_PREFIX):
            if all_genlang or any(token in metric_type for token in GENLANG_WANTED):
                chosen[metric_type] = descriptor
    return sorted(chosen.values(), key=lambda d: d["type"])


def alias_for(metric_type: str) -> str:
    tail = metric_type.split("/", 1)[1] if "/" in metric_type else metric_type
    if tail.endswith("/usage"):
        tail = tail[: -len("/usage")]
    if tail.startswith("quota/"):
        tail = tail[len("quota/"):]
    return tail.replace("/", "_")


def aligners_for(descriptor: dict) -> list[tuple[str, str]]:
    """Hourly aligners matching the metric's own kind, as (alias suffix, aligner).

    Never a cross-series reduce — reducing across series would collapse the
    labels, which is the one thing this script must not do.

    A distribution is fetched twice. One aligner yields one percentile, and the
    dashboard needs both p95 ("thoi gian phan hoi") and p99 ("truong hop cham
    nhat"), so a single pass cannot serve both.
    """
    if descriptor.get("valueType") == "DISTRIBUTION":
        return [("_p95", "ALIGN_PERCENTILE_95"), ("_p99", "ALIGN_PERCENTILE_99")]
    if descriptor.get("metricKind") in ("DELTA", "CUMULATIVE"):
        return [("", "ALIGN_SUM")]
    return [("", "ALIGN_MAX")]


def point_value(point: dict) -> float | None:
    value = point.get("value", {})
    for field in ("int64Value", "doubleValue"):
        if field in value:
            return float(value[field])
    if "boolValue" in value:
        return 1.0 if value["boolValue"] else 0.0
    return None


def fetch_series(project: str, descriptor: dict, token: str,
                 start: datetime, end: datetime, align: int) -> list[dict]:
    metric_type = descriptor["type"]
    base_alias = alias_for(metric_type)
    unit = descriptor.get("unit", "")
    rows: list[dict] = []

    for suffix, aligner in aligners_for(descriptor):
        params = {
            "filter": f'metric.type="{metric_type}"',
            "interval.startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "interval.endTime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "aggregation.alignmentPeriod": f"{align}s",
            "aggregation.perSeriesAligner": aligner,
            "view": "FULL",
            "pageSize": "10000",
        }
        url = f"{API}/projects/{project}/timeSeries?" + urllib.parse.urlencode(params)

        for one in paged(url, token, "timeSeries"):
            metric_labels = one.get("metric", {}).get("labels", {})
            resource_labels = one.get("resource", {}).get("labels", {})
            for point in one.get("points", []):
                value = point_value(point)
                if value is None:
                    continue
                stamp = point["interval"]["endTime"].replace("Z", "+00:00")
                moment = datetime.fromisoformat(stamp).astimezone(timezone.utc)
                local = moment.astimezone(ICT)
                row = {
                    "metric_alias": base_alias + suffix,
                    "metric_type": metric_type,
                    "gcp_project_id": project,
                    "ts_utc": moment.strftime("%Y-%m-%d %H:%M:%S"),
                    "ts_ict": local.strftime("%Y-%m-%d %H:%M:%S"),
                    "aligner": aligner,
                    "value": value,
                    "unit": unit,
                    "metric_labels_json": json.dumps(metric_labels, ensure_ascii=False,
                                                     sort_keys=True),
                    "resource_labels_json": json.dumps(resource_labels, ensure_ascii=False,
                                                       sort_keys=True),
                }
                for label in FLAT_METRIC_LABELS:
                    row[label] = metric_labels.get(label, "")
                for column, label in FLAT_RESOURCE_LABELS.items():
                    row[column] = resource_labels.get(label, "")
                rows.append(row)
    return rows


def pull_project(project: str, token: str, out_dir: Path,
                 start: datetime, end: datetime, all_genlang: bool, align: int) -> int:
    descriptors = list_descriptors(project, token)
    (out_dir / f"{project}.descriptors.json").write_text(
        json.dumps(descriptors, ensure_ascii=False, indent=2), encoding="utf-8")

    targets = wanted(descriptors, all_genlang)
    print(f"  {len(descriptors)} descriptor, keo {len(targets)} phep do")

    rows: list[dict] = []
    for descriptor in targets:
        got = fetch_series(project, descriptor, token, start, end, align)
        if got:
            print(f"    {alias_for(descriptor['type']):<52} {len(got):>6} diem")
        rows.extend(got)

    target = out_dir / f"{project}.csv"
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--projects", default=",".join(PROJECTS),
                        help="Danh sach project_id, ngan cach bang dau phay")
    parser.add_argument("--days", type=int, default=60,
                        help="So ngay lui ve. De rong hon muc nghi la con giu (mac dinh 60)")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--all-genlang", action="store_true",
                        help="Keo MOI phep do generativelanguage, khong chi token/request")
    parser.add_argument("--align", type=int, default=3600,
                        help="Do min, tinh bang giay. 60 = min nhat Google co (mac dinh 3600)")
    parser.add_argument("--gcloud", default="", help="Duong dan gcloud neu khong co trong PATH")
    args = parser.parse_args()

    if args.align < 60:
        raise SystemExit(
            f"--align {args.align} nho hon 60s.\n"
            "Google chi luu o muc 60s (samplePeriod trong descriptor). Xin min hon\n"
            "khong cho them thong tin, chi lam phong so dong."
        )

    gcloud = args.gcloud or gcloud_path()
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=args.days)

    # Resolution belongs in the folder name. Without it a second pull on the same
    # day silently overwrites the first, and the two are not interchangeable.
    label = f"{args.align // 60}m" if args.align < 3600 else f"{args.align // 3600}h"
    out_dir = Path(args.out) / f"{end:%Y-%m-%d}-{label}"
    out_dir.mkdir(parents=True, exist_ok=True)

    projects = [p.strip() for p in args.projects.split(",") if p.strip()]
    print(f"Khoang: {start:%Y-%m-%d %H:%M} -> {end:%Y-%m-%d %H:%M} UTC ({args.days} ngay)")
    print(f"Do min: {args.align}s ({label})")
    print(f"Ghi vao: {out_dir}\n")

    total = 0
    for project in projects:
        print(f"[{project}]")
        # Refreshed per project: a wide sweep can outlive a single token.
        count = pull_project(project, access_token(gcloud), out_dir, start, end,
                             args.all_genlang, args.align)
        print(f"  -> {count} dong\n")
        total += count

    print(f"Xong. {total} dong, {len(projects)} project.")
    print(f"Buoc tiep: python scripts/check_monitoring.py --dir \"{out_dir}\"")
    if total == 0:
        print("\nCANH BAO: khong co dong nao. Kiem lai quyen Monitoring Viewer va khoang thoi gian.")
        sys.exit(1)


if __name__ == "__main__":
    main()
