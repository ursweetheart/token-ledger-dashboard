"""Nap SO CUA NHA CUNG CAP tu mot lan keo Monitoring vao `fact_provider_daily`.

    python db/load_provider.py --dir data/raw_google_console/du_lieu_giam_sat/<lan keo>

BANG NAY KHONG PHAI NGUON THU NAM
---------------------------------
`usage_resolved` KHONG doc `fact_provider_daily`. Cung mot luot goi da nam trong
`fact_call` roi; doc them la dem doi. Bang nay giu cau tra loi cua NHA CUNG CAP
cho cung mot luu luong, de doi chieu voi cau tra loi cua TA.

BA BAY DA DO DUOC, MOI CAI DEU TRA VE SO SAI MA KHONG BAO LOI
------------------------------------------------------------
1. NHAN DOI THEO limit_name. Mot phep do quota tra ve HAI chuoi mang CUNG mot
   luong, tach theo `limit_name` - mot nhanh "PerDay", mot nhanh "PerMinute".
   Do 04/09/2026 tren ngay 31/08:

       GenerateContentInputTokensPerModelPerDay-FreeTier      47.613
       GenerateContentInputTokensPerModelPerMinute-FreeTier   47.613

   Cong ca hai ra 95.226, tuc gap doi, va con so do trong y het mot phep do that.
   Bo nap lay nhanh PerDay VA SO voi nhanh PerMinute; lech thi DUNG. Khong tu
   chon mot ben, vi "hai nhanh luon bang nhau" la gia dinh ve hanh vi cua Google
   chu khong phai su that ta kiem soat.

2. TEM THOI GIAN LA CUOI O, KHONG PHAI DAU O. `pull_monitoring.py:228` lay
   `point.interval.endTime`. Nen o ghi 00:00 thuoc ve NGAY HOM TRUOC. Quy ngay
   bang cach lui mot giay truoc khi cat.

3. *_limit LA HAN MUC, KHONG PHAI SO DEM. Chung la ALIGN_MAX va co gia tri
   55.340.232.221.128.654.848. Cong chung vao la ra mot con so vo nghia ma van
   la mot so. Loc bang rules.is_quota_limit().

VI SAO KHONG DUNG api/request_count CHO SO LUOT
-----------------------------------------------
`serviceruntime/api/request_count` KHONG co nhan `model`, ma khoa cua bang co
`raw_model`. Dung no thi phai gan bua model cho so luot. Metric quota
`generate_content_free_tier_requests` CO nhan model va do duoc la khop chinh
xac: ngay 31/08 ca hai deu ra 41. Nen lay tu metric quota, va DOI CHIEU voi
api_request_count nhu mot phep kiem cheo.

DOC MOI LAN KEO, GIU SO LON HON (doi 14/09/2026)
------------------------------------------------
Truoc 14/09 bo nap chi doc lan keo MOI NHAT. Buoc dung lai xoa sach bang nay, nen
lan keo thu hai se lam mat moi ngay chi lan keo dau con giu - dung loai mat phan
dau ma viec giu lan keo cu tren dia sinh ra de chan.

Nay doc MOI thu muc khop `PULL_FOLDER_PATTERN`. `pick_branch` chay TRONG tung lan
keo, de nhanh PerDay cua lan keo nay khong bi so voi nhanh PerMinute cua lan keo
khac. Giua cac lan keo, cung (ngay, project, model, dai luong) thi giu SO LON HON
va log ca lech: mot ngay bi cat o mep cua lan keo nay van co the day du o lan keo
khac. Xem change `stop-a-later-pull-from-shrinking-an-earlier-one`.
"""

from __future__ import annotations

import argparse
import collections
import csv
import logging
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import connect                                  # noqa: E402
import rules                                    # noqa: E402

log = logging.getLogger("load_provider")

# Bi danh cua ba dai luong ta can. Moi cai mot cach nhan dang rieng vi Google
# dat ten khong theo mot khuon nao.
ALIAS_OUTPUT = "generate_content_usage_output_token_count"

# Gia tri GHI VAO `fact_provider_daily.raw_model` khi dong khong mang model. La du
# lieu, nam trong khoa chinh: doi chu o day la tach mot dong thanh hai.
NO_MODEL = "(khong khai)"


def is_input_tokens(alias: str) -> bool:
    return "input_token_count" in alias and not rules.is_quota_limit(alias)


def is_requests(alias: str) -> bool:
    return alias.endswith("_requests") and not rules.is_quota_limit(alias)


def branch_of(limit_name: str) -> str:
    """'PerDay' / 'PerMinute' / '' - hai nhanh cua CUNG mot phep do quota."""
    if "PerDay" in limit_name:
        return "PerDay"
    if "PerMinute" in limit_name:
        return "PerMinute"
    return ""


def vn_day(ts_ict: str) -> str:
    """Tem la CUOI o, nen o 00:00 thuoc ngay hom truoc. Lui mot giay roi cat."""
    t = datetime.strptime(ts_ict, "%Y-%m-%d %H:%M:%S") - timedelta(seconds=1)
    return t.date().isoformat()


def read_one_file(path: Path) -> tuple[dict, dict, list[str]]:
    """-> {(day, project, model, measure, branch): total}, {(day, project): requests}, warnings.

    Dict thu hai la `api_request_count`. KHONG nap vao bang - no khong co nhan
    `model` nen khong co cho trong khoa - ma chi de KIEM CHEO so luot lay tu
    metric quota bang mot phep do doc lap.
    """
    totals: dict[tuple, float] = collections.defaultdict(float)
    api_requests: dict[tuple, float] = collections.defaultdict(float)
    by_time: dict[tuple, list] = collections.defaultdict(list)
    warnings: list[str] = []

    with open(path, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            alias = r["metric_alias"]
            if rules.is_quota_limit(alias):
                continue                        # bay 3
            if alias == "api_request_count":
                try:
                    api_requests[(vn_day(r["ts_ict"]), r["gcp_project_id"])] += float(r["value"])
                except (TypeError, ValueError):
                    pass
                continue
            if alias == ALIAS_OUTPUT:
                measure = "output_tokens"
            elif is_input_tokens(alias):
                measure = "input_tokens"
            elif is_requests(alias):
                measure = "requests"
            else:
                continue

            try:
                v = float(r["value"])
            except (TypeError, ValueError):
                continue
            if not v:
                continue

            key = (vn_day(r["ts_ict"]), r["gcp_project_id"], r["model"],
                   measure, branch_of(r["limit_name"]))
            totals[key] += v
            by_time[key].append((r["ts_ict"], v))

    # bay: neu Google doi sang bao LUY KE thi cong don se sai. Day don dieu
    # khong giam tren >= 4 diem la dau hieu. Chi canh bao, khong tu suy dien.
    for key, points in by_time.items():
        if len(points) < 4:
            continue
        values = [v for _, v in sorted(points)]
        if all(b > a for a, b in zip(values, values[1:])):
            warnings.append(
                "series keeps increasing (%d points) at %s - check whether Google "
                "switched to CUMULATIVE reporting; summing cumulative values gives "
                "wrong numbers" % (len(values), key))
    return totals, api_requests, warnings


def pick_branch(totals: dict) -> tuple[dict, list[str]]:
    """Lay nhanh PerDay, SO voi PerMinute. Lech thi dung - xem bay 1."""
    result: dict[tuple, float] = {}
    errors: list[str] = []
    keys_without_branch = {k for k in totals if k[4] == ""}
    for k in keys_without_branch:
        result[k[:4]] = totals[k]

    bases = {k[:4] for k in totals if k[4]}
    for base in sorted(bases):
        day, project, model, measure = base
        d = totals.get((*base, "PerDay"))
        m = totals.get((*base, "PerMinute"))
        if d is not None and m is not None and d != m:
            errors.append(
                "%s %s %s %s: PerDay branch = %s but PerMinute = %s. Both branches "
                "must report the same quantity; a mismatch means the loader's "
                "assumption is wrong, do NOT pick one side."
                % (day, project, model, measure, f"{d:,.0f}", f"{m:,.0f}"))
            continue
        result[base] = d if d is not None else m
    return result, errors


# `<ngay>-<do min>-<tai khoan>`. Hau to tai khoan la thu phan biet lan keo cua nha
# cung cap voi lan keo san xuat; KHONG dua vao do min, vi do min doi duoc bang --align.
PULL_FOLDER_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-\d+[mh]-.+$")


def pick_pulls(root: Path) -> list[Path]:
    """Moi thu muc keo mang ten tai khoan, CU TRUOC MOI SAU (ten bat dau bang ngay)."""
    return sorted(d for d in root.glob("*") if d.is_dir() and PULL_FOLDER_PATTERN.match(d.name))


def merge_pulls(pulls: list[Path]) -> tuple[dict, dict, list[str], list[str]]:
    """-> (result, api_requests, warnings, errors). Doc tung lan keo, giu so lon hon giua cac lan."""
    result: dict[tuple, float] = {}
    source_of: dict[tuple, str] = {}
    api_requests: dict[tuple, float] = {}
    warnings: list[str] = []
    errors: list[str] = []
    clash_count = 0
    for folder in pulls:
        totals: dict[tuple, float] = collections.defaultdict(float)
        api: dict[tuple, float] = collections.defaultdict(float)
        for f in sorted(folder.glob("*.csv")):
            t, a, w = read_one_file(f)
            for k, v in t.items():
                totals[k] += v
            for k, v in a.items():
                api[k] += v
            warnings += [f"{folder.name}: {x}" for x in w]

        pull_result, pull_errors = pick_branch(totals)
        errors += [f"{folder.name}: {e}" for e in pull_errors]
        for k, v in pull_result.items():
            old = result.get(k)
            if old is None:
                result[k], source_of[k] = v, folder.name
                continue
            if old == v:
                continue
            clash_count += 1
            log.warning("  CLASH %s %s %s %s: pull %s = %s, pull %s = %s -> keep %s",
                        k[0], k[1][:28], k[2], k[3], source_of[k], f"{old:,.0f}",
                        folder.name, f"{v:,.0f}", f"{max(old, v):,.0f}")
            if v > old:
                result[k], source_of[k] = v, folder.name
        for k, v in api.items():
            api_requests[k] = max(api_requests.get(k, 0.0), v)

    if clash_count:
        log.warning("  clashes: %d (kept the larger value in each)", clash_count)
    else:
        log.info("  clashes: 0")
    return result, api_requests, warnings, errors


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                allow_abbrev=False)
    p.add_argument("--db", default=connect.DEFAULT_DSN)
    p.add_argument("--dir", default="", help="Folder of one Monitoring pull. "
                                            "Empty = EVERY pull whose name carries an account.")
    p.add_argument("--account", default="", help="Account used for the pull, recorded only")
    p.add_argument("--dry-run", action="store_true", help="Print only, do not write to the database")
    p.add_argument("--optional", action="store_true",
                   help="With no pull at all, WARN and exit 0 instead of failing. "
                        "For rebuild_db.py: provider data is not there every day, "
                        "and without it the reconciliation reports 'not checked' "
                        "rather than 'pass'.")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    pulls_root = (Path(__file__).resolve().parents[1] / "data" / "raw_google_console"
                  / "du_lieu_giam_sat")  # vi-ok: on-disk path
    pulls = [Path(args.dir)] if args.dir else pick_pulls(pulls_root)
    pulls = [d for d in pulls if d.is_dir() and any(d.glob("*.csv"))]
    if not pulls:
        where = args.dir or pulls_root
        if args.optional:
            # KHONG im lang. Thieu du lieu nha cung cap khong phai loi, nhung
            # no co hau qua doc duoc: phep doi chieu se bao 'chua kiem duoc'.
            log.warning("no provider pull at all (%s)", where)
            log.warning("  -> fact_provider_daily unchanged, the reconciliation will report NOT CHECKED")
            log.warning("  -> to get one: scripts/pull_monitoring.py --account <account> --projects <project>")
            return
        raise SystemExit("no pull has a .csv file (%s)" % where)
    log.info("reading %d pulls: %s", len(pulls), ", ".join(d.name for d in pulls))

    result, api_requests, warnings, errors = merge_pulls(pulls)
    for w in warnings:
        log.warning("  WARNING: %s", w)
    if errors:
        for e in errors:
            log.error("  FAILED: %s", e)
        raise SystemExit("Stopping. The two quota branches disagree - see trap 1 in the docstring.")

    # gop ba dai luong ve mot dong moi (ngay, project, model)
    rows: dict[tuple, dict] = collections.defaultdict(dict)
    for (day, project, model, measure), v in result.items():
        rows[(day, project, model)][measure] = int(round(v))

    if not rows:
        raise SystemExit("no row could be loaded - check the pull folder")

    # KIEM CHEO: so luot lay tu metric quota phai khop `api_request_count`. Hai
    # phep do doc lap nhau, nen khop la bang chung ta doc DUNG nhanh quota.
    # KHONG bao hong khi lech: api_request_count dem MOI phuong thuc API chu
    # khong rieng GenerateContent, nen lech co the la that. Nhung phai NOI RA.
    quota_requests: dict[tuple, float] = collections.defaultdict(float)
    for (day, project, _model), v in rows.items():
        if "requests" in v:
            quota_requests[(day, project)] += v["requests"]
    for k in sorted(set(quota_requests) | set(api_requests)):
        a, b = int(quota_requests.get(k, 0)), int(api_requests.get(k, 0))
        if a != b:
            log.warning("  CROSS-CHECK %s %s: quota says %d requests, api_request_count says %d",
                        k[0], k[1][:28], a, b)
        else:
            log.info("  cross-check %s %s: %d requests, both measures agree", k[0], k[1][:28], a)

    cn, _ = connect.open_db(args.db)
    try:
        cur = cn.cursor()
        cur.execute("SELECT raw_name, model_id FROM dim_model_alias WHERE source = 'monitoring'")
        alias_to_model = dict(cur.fetchall())

        unmapped = collections.Counter()
        records = []
        for (day, project, model), v in sorted(rows.items()):
            mid = alias_to_model.get(model)
            if model and mid is None:
                unmapped[model] += 1
            records.append((day, project, model or NO_MODEL, mid,
                            v.get("requests"), v.get("input_tokens"), v.get("output_tokens"),
                            args.account or None))

        if args.dry_run:
            for b in records:
                log.info("  %s %s %-24s req=%s in=%s out=%s",
                         b[0], b[1][:28], b[2], b[4], b[5], b[6])
        else:
            cur.executemany("""
                INSERT INTO fact_provider_daily
                    (day, provider_project, raw_model, model_id,
                     requests, input_tokens, output_tokens, pulled_account, pulled_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (day, provider_project, raw_model) DO UPDATE SET
                    model_id       = EXCLUDED.model_id,
                    requests       = EXCLUDED.requests,
                    input_tokens   = EXCLUDED.input_tokens,
                    output_tokens  = EXCLUDED.output_tokens,
                    pulled_account = EXCLUDED.pulled_account,
                    pulled_at      = EXCLUDED.pulled_at
            """, records)
            cn.commit()

        log.info("%d rows | %d days | %d project%s",
                 len(records), len({b[0] for b in records}), len({b[1] for b in records}),
                 "  (DRY RUN - nothing written)" if args.dry_run else "")
        if unmapped:
            # KHONG im lang. Model chua anh xa thi model_id de NULL va phai noi ra.
            for m, n in unmapped.most_common():
                log.warning("  model has no alias for source 'monitoring': %s (%d rows)", m, n)
    finally:
        cn.close()


if __name__ == "__main__":
    main()
