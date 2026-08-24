"""Nap Cloud Monitoring vao fact_monitoring - chi doc file, khong goi mang.

QUY DINH M-A: NAP DU, LOC O TANG VIEW
------------------------------------
Nap ca 525.639 dong, ke ca luu luong Drive/Sheets/Compute. KHONG loc luc nap.

Ly do: chinh mo luu luong do la BANG CHUNG cho quy tac 3 - `pro-tuner` sai
45,7 lan neu quen loc. Loc ngay luc nap thi sau nay khong chung minh lai duoc,
ma cao lai thi khong the vi Google chi giu 196 ngay.

View `monitoring_ai` la cua duy nhat nen di qua khi tinh toan.

HAI CAI BAY
-----------
Quy tac 9  `dich_vu` KHONG co san tno_model file. Dung cac dong TOKEN cua
           generativelanguage lai co `res_service` RONG - dich vu cua chung nam
           o tien to `metric_type`. Gan thang dich_vu = res_service roi loc se
           tra ve 0 dong token, KHONG bao loi.
Quy tac 2  *_limit la ALIGN_MAX - han muc quota, khong phai so dem. Danh dau
           bang cot `is_quota_limit` de khong ai lo SUM chung vao.

NGHIEM THU
----------
    SELECT COUNT(*) FROM fact_monitoring;                 -- 525639
    SELECT COUNT(DISTINCT project) FROM fact_monitoring;  -- 7
    SELECT COUNT(*) FROM monitoring_ai;                        -- 85166
"""

from __future__ import annotations

import argparse
import collections
import csv
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import connect  # noqa: E402
from rules import guess_service, is_quota_limit  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _latest_monitoring() -> Path:
    """Uu tien thu muc da GOP (scripts/merge_monitoring.py).

    Cua so luu giu cua Google truot rat nhanh - do 06/08 thay 196 ngay, do 13/08
    chi con 112. Mot dot keo don le KHONG con phu het dai ngay, nen nguon dung
    cho nap la ban gop nhieu dot.
    """
    parent_dir = ROOT / "data" / "da_xu_ly" / "du_lieu_giam_sat"
    remaining = sorted(p for p in parent_dir.glob("*") if p.is_dir())
    if not remaining:
        raise SystemExit(f"Khong co thu muc nao tno_model {parent_dir}."
                         f" Chay scripts/merge_monitoring.py truoc.")
    merged = [p for p in remaining if p.name.endswith("-gop")]
    return (merged or remaining)[-1]


MONITORING_DIR = _latest_monitoring()
BATCH_SIZE = 20000

# KHONG ghim so mong doi nua (truoc: 525639 / 85166 / 7). Chung dung cho dot keo
# 06/08 va sai ngay khi keo dot moi. Nay so dong va so du an SUY TU CHINH FILE
# NGUON. Rieng monitoring_ai la VIEW - suy lai so mong doi cua no la chep lai dinh
# nghia view, nen thay bang kiem bien: phai > 0 va < tong. Hai gia tri bien do
# bat dung hai kieu hong that su (bo loc chet, hoac bo loc khong chay).


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=connect.DEFAULT_DSN)
    p.add_argument("--dir", default=str(MONITORING_DIR))
    p.add_argument("--limit", type=int, default=0,
                   help="Chi nap N dong dau moi file - de chay lat mong cho nhanh")
    args = p.parse_args()

    cn, dc = connect.open_db(args.db)
    models = connect.model_lookup(cn)
    agents = connect.agent_lookup(cn)
    metrics = connect.metric_lookup(cn)

    files = sorted(glob.glob(str(Path(args.dir) / "*.csv")))
    if not files:
        raise SystemExit(f"Khong co file .csv nao tno_model {args.dir}")

    cur = cn.cursor()
    cur.execute("DELETE FROM fact_monitoring")

    COLUMNS = ["ts_utc", "ts_local", "agent_id", "project", "metric_nickname",
           "metric_type", "model_id", "response_code", "service", "method",
           "credential_id", "is_quota_limit", "thinking_enabled", "output_modality",
           "limit_name", "value", "unit"]

    written = 0
    missing_model = collections.Counter()
    missing_agent = collections.Counter()
    missing_metric = collections.Counter()
    quota_mismatch = collections.Counter()
    batch: list[tuple] = []
    for f in files:
        with open(f, encoding="utf-8-sig") as h:
            for i, r in enumerate(csv.DictReader(h)):
                if args.limit and i >= args.limit:
                    break
                model_id = None
                if r["model"]:
                    model_id = models.get(("monitoring", r["model"]))
                    if model_id is None:
                        missing_model[r["model"]] += 1
                agent_id = agents.get(r["gcp_project_id"])
                if agent_id is None:
                    missing_agent[r["gcp_project_id"]] += 1

                # `is_quota_limit` gio tra tu dim_metric_alias (measures='quota_limit'),
                # khong con suy tu hau to '_limit' cua bi danh. Van goi ham cu de
                # DOI CHIEU: hai cach phai ra cung ket qua, lech la co chuyen.
                measures, _ = metrics.get(("monitoring", r["metric_type"]), (None, None))
                if measures is None:
                    missing_metric[r["metric_type"]] += 1
                is_limit = measures == "quota_limit"
                if measures is not None and is_limit != is_quota_limit(r["metric_alias"]):
                    quota_mismatch[r["metric_type"]] += 1

                batch.append((
                    r["ts_utc"], r["ts_ict"], agent_id, r["gcp_project_id"],
                    r["metric_alias"], r["metric_type"],
                    model_id,
                    r["response_code"] or None,
                    guess_service(r["res_service"], r["metric_type"]),
                    r["res_method"] or None,
                    r["res_credential_id"] or None,
                    is_limit,
                    r["thinking_enabled"] or None,
                    r["output_modality"] or None,
                    r["limit_name"] or None,
                    float(r["value"]),
                    r["unit"] or None,
                ))
                if len(batch) >= BATCH_SIZE:
                    written += connect.insert_many(cn, dc, "fact_monitoring", COLUMNS, batch)
                    batch = []
    if batch:
        written += connect.insert_many(cn, dc, "fact_monitoring", COLUMNS, batch)

    # Kiem TRUOC commit. Neu de sau thi du lieu sai da kip ghi xuong dia, va
    # nguoi chay se co mot database tno_model nhu binh thuong nhung thieu model.
    fatal = []
    if missing_model:
        fatal.append(f"nhan model chua co tno_model danh muc: {dict(missing_model)}")
    if missing_agent:
        fatal.append(f"project khong co tno_model dim_agent: {dict(missing_agent)}")
    if missing_metric:
        fatal.append(f"phep do chua co bi danh: {dict(missing_metric)}")
    if quota_mismatch:
        fatal.append(f"bang bi danh va hau to '_limit' KHONG dong y: {dict(quota_mismatch)}")
    if fatal:
        cn.rollback()
        raise SystemExit(
            "Da huy, khong ghi gi. Chay lai db/gen_catalog.py roi nap lai:\n  "
            + "\n  ".join(hong))
    cn.commit()

    cur.execute("SELECT COUNT(*) FROM fact_monitoring")
    n = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT project) FROM fact_monitoring")
    projects = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM monitoring_ai")
    clean = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM fact_monitoring WHERE model_id IS NULL")
    no_model = cur.fetchone()[0]

    print(f"  {n} dong | {projects} du an | monitoring_ai {clean} | model_id NULL {no_model}")

    if args.limit:
        print("  (lat mong - bo qua nghiem thu)")
        return
    src_projects = len({Path(f).stem for f in files})

    errors = []
    if n != written:
        errors.append(f"so dong tno_model DB {n} != {written} dong da doc tu file nguon")
    if projects != src_projects:
        errors.append(f"so du an {projects} != {src_projects} file nguon")
    if clean == 0:
        errors.append("monitoring_ai = 0 - bo loc dich vu chet, khong con dong nao di qua")
    elif clean >= n:
        errors.append(f"monitoring_ai {clean} >= tong {n} - bo loc khong chay, "
                   f"luu luong Drive/Sheets dang bi tinh chung")
    if errors:
        raise SystemExit("NGHIEM THU KHONG DAT: " + " | ".join(errors))
    print(f"  NGHIEM THU DAT (nguon: {MONITORING_DIR.name})")


if __name__ == "__main__":
    main()
