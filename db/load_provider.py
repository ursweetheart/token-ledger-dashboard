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


def la_token_vao(alias: str) -> bool:
    return "input_token_count" in alias and not rules.is_quota_limit(alias)


def la_so_luot(alias: str) -> bool:
    return alias.endswith("_requests") and not rules.is_quota_limit(alias)


def nhanh(limit_name: str) -> str:
    """'PerDay' / 'PerMinute' / '' - hai nhanh cua CUNG mot phep do quota."""
    if "PerDay" in limit_name:
        return "PerDay"
    if "PerMinute" in limit_name:
        return "PerMinute"
    return ""


def ngay_vn(ts_ict: str) -> str:
    """Tem la CUOI o, nen o 00:00 thuoc ngay hom truoc. Lui mot giay roi cat."""
    t = datetime.strptime(ts_ict, "%Y-%m-%d %H:%M:%S") - timedelta(seconds=1)
    return t.date().isoformat()


def doc_mot_file(path: Path) -> tuple[dict, dict, list[str]]:
    """-> {(day, project, model, dai_luong, nhanh): tong}, {(day, project): luot}, canh bao.

    Dict thu hai la `api_request_count`. KHONG nap vao bang - no khong co nhan
    `model` nen khong co cho trong khoa - ma chi de KIEM CHEO so luot lay tu
    metric quota bang mot phep do doc lap.
    """
    tong: dict[tuple, float] = collections.defaultdict(float)
    luot_api: dict[tuple, float] = collections.defaultdict(float)
    theo_gio: dict[tuple, list] = collections.defaultdict(list)
    canh_bao: list[str] = []

    with open(path, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            alias = r["metric_alias"]
            if rules.is_quota_limit(alias):
                continue                        # bay 3
            if alias == "api_request_count":
                try:
                    luot_api[(ngay_vn(r["ts_ict"]), r["gcp_project_id"])] += float(r["value"])
                except (TypeError, ValueError):
                    pass
                continue
            if alias == ALIAS_OUTPUT:
                dai_luong = "output_tokens"
            elif la_token_vao(alias):
                dai_luong = "input_tokens"
            elif la_so_luot(alias):
                dai_luong = "requests"
            else:
                continue

            try:
                v = float(r["value"])
            except (TypeError, ValueError):
                continue
            if not v:
                continue

            khoa = (ngay_vn(r["ts_ict"]), r["gcp_project_id"], r["model"],
                    dai_luong, nhanh(r["limit_name"]))
            tong[khoa] += v
            theo_gio[khoa].append((r["ts_ict"], v))

    # bay: neu Google doi sang bao LUY KE thi cong don se sai. Day don dieu
    # khong giam tren >= 4 diem la dau hieu. Chi canh bao, khong tu suy dien.
    for khoa, diem in theo_gio.items():
        if len(diem) < 4:
            continue
        gt = [v for _, v in sorted(diem)]
        if all(b > a for a, b in zip(gt, gt[1:])):
            canh_bao.append(
                "day don dieu khong giam (%d diem) o %s - kiem xem Google co doi "
                "sang bao LUY KE khong; cong don luy ke se ra so sai" % (len(gt), khoa))
    return tong, luot_api, canh_bao


def chon_nhanh(tong: dict) -> tuple[dict, list[str]]:
    """Lay nhanh PerDay, SO voi PerMinute. Lech thi dung - xem bay 1."""
    ket: dict[tuple, float] = {}
    loi: list[str] = []
    khoa_khong_nhanh = {k for k in tong if k[4] == ""}
    for k in khoa_khong_nhanh:
        ket[k[:4]] = tong[k]

    goc = {k[:4] for k in tong if k[4]}
    for g in sorted(goc):
        ngay_, du_an, model, dai_luong = g
        d = tong.get((*g, "PerDay"))
        m = tong.get((*g, "PerMinute"))
        if d is not None and m is not None and d != m:
            loi.append(
                "%s %s %s %s: nhanh PerDay = %s nhung PerMinute = %s. Hai nhanh "
                "phai bao cung mot luong; lech nghia la gia dinh cua bo nap sai, "
                "KHONG duoc tu chon mot ben."
                % (ngay_, du_an, model, dai_luong, f"{d:,.0f}", f"{m:,.0f}"))
            continue
        ket[g] = d if d is not None else m
    return ket, loi


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=connect.DEFAULT_DSN)
    p.add_argument("--dir", default="", help="Thu muc mot lan keo Monitoring. "
                                            "De rong = lan keo MOI NHAT co ten mang tai khoan.")
    p.add_argument("--account", default="", help="Tai khoan da dung de keo, chi de ghi lai")
    p.add_argument("--kho", action="store_true", help="Chi in, khong ghi database")
    p.add_argument("--tuy-chon", action="store_true",
                   help="Chua co lan keo nao thi CANH BAO roi thoat 0, thay vi hong. "
                        "Dung cho rebuild_db.py: khong phai ngay nao cung co du lieu "
                        "nha cung cap, nhung thieu no thi phep doi chieu se bao "
                        "'chua kiem duoc' chu khong bao dat.")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.dir:
        thu_muc = Path(args.dir)
    else:
        # Lan keo cua nha cung cap mang ten tai khoan o duoi ten thu muc, nen
        # phan biet duoc voi lan keo san xuat. Lay lan MOI NHAT theo ten (ten
        # bat dau bang ngay nen sap xep chu = sap xep thoi gian).
        goc = Path(__file__).resolve().parents[1] / "data" / "raw_google_console" / "du_lieu_giam_sat"
        # `<ngay>-<do min>-<tai khoan>`. Hau to tai khoan la thu phan biet lan keo
        # cua nha cung cap voi lan keo san xuat; KHONG dua vao do min, vi do min
        # doi duoc bang --align. Ten bat dau bang ngay nen sap chu = sap thoi gian.
        khuon = re.compile(r"^\d{4}-\d{2}-\d{2}-\d+[mh]-.+$")
        ung_vien = sorted(d for d in goc.glob("*") if d.is_dir() and khuon.match(d.name))
        thu_muc = ung_vien[-1] if ung_vien else goc / "(khong co lan keo nao mang ten tai khoan)"

    files = sorted(f for f in thu_muc.glob("*.csv")) if thu_muc.is_dir() else []
    if not files:
        if args.tuy_chon:
            # KHONG im lang. Thieu du lieu nha cung cap khong phai loi, nhung
            # no co hau qua doc duoc: phep doi chieu se bao 'chua kiem duoc'.
            log.warning("khong co lan keo nha cung cap nao (%s)", thu_muc)
            log.warning("  -> fact_provider_daily giu nguyen, phep doi chieu se bao CHUA KIEM DUOC")
            log.warning("  -> muon co: scripts/pull_monitoring.py --account <tai khoan> --projects <project>")
            return
        raise SystemExit("khong co file .csv nao trong %s" % thu_muc)
    log.info("doc %s", thu_muc.name)

    tong: dict[tuple, float] = collections.defaultdict(float)
    luot_api: dict[tuple, float] = collections.defaultdict(float)
    canh_bao: list[str] = []
    for f in files:
        t, la, c = doc_mot_file(f)
        for k, v in t.items():
            tong[k] += v
        for k, v in la.items():
            luot_api[k] += v
        canh_bao += c

    ket, loi = chon_nhanh(tong)
    for c in canh_bao:
        log.warning("  CANH BAO: %s", c)
    if loi:
        for e in loi:
            log.error("  HONG: %s", e)
        raise SystemExit("Dung. Hai nhanh han muc khong khop - xem bay 1 trong docstring.")

    # gop ba dai luong ve mot dong moi (ngay, project, model)
    dong: dict[tuple, dict] = collections.defaultdict(dict)
    for (ngay_, du_an, model, dai_luong), v in ket.items():
        dong[(ngay_, du_an, model)][dai_luong] = int(round(v))

    if not dong:
        raise SystemExit("khong nap duoc dong nao - kiem lai thu muc keo")

    # KIEM CHEO: so luot lay tu metric quota phai khop `api_request_count`. Hai
    # phep do doc lap nhau, nen khop la bang chung ta doc DUNG nhanh quota.
    # KHONG bao hong khi lech: api_request_count dem MOI phuong thuc API chu
    # khong rieng GenerateContent, nen lech co the la that. Nhung phai NOI RA.
    luot_quota: dict[tuple, float] = collections.defaultdict(float)
    for (ngay_, du_an, _model), v in dong.items():
        if "requests" in v:
            luot_quota[(ngay_, du_an)] += v["requests"]
    for k in sorted(set(luot_quota) | set(luot_api)):
        a, b = int(luot_quota.get(k, 0)), int(luot_api.get(k, 0))
        if a != b:
            log.warning("  KIEM CHEO %s %s: quota bao %d luot, api_request_count bao %d",
                        k[0], k[1][:28], a, b)
        else:
            log.info("  kiem cheo %s %s: %d luot, hai phep do khop", k[0], k[1][:28], a)

    cn, _ = connect.open_db(args.db)
    try:
        cur = cn.cursor()
        cur.execute("SELECT raw_name, model_id FROM dim_model_alias WHERE source = 'monitoring'")
        anh_xa = dict(cur.fetchall())

        thieu = collections.Counter()
        ban = []
        for (ngay_, du_an, model), v in sorted(dong.items()):
            mid = anh_xa.get(model)
            if model and mid is None:
                thieu[model] += 1
            ban.append((ngay_, du_an, model or "(khong khai)", mid,
                        v.get("requests"), v.get("input_tokens"), v.get("output_tokens"),
                        args.account or None))

        if args.kho:
            for b in ban:
                log.info("  %s %s %-24s req=%s vao=%s ra=%s",
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
            """, ban)
            cn.commit()

        log.info("%d dong | %d ngay | %d project%s",
                 len(ban), len({b[0] for b in ban}), len({b[1] for b in ban}),
                 "  (KHO - khong ghi)" if args.kho else "")
        if thieu:
            # KHONG im lang. Model chua anh xa thi model_id de NULL va phai noi ra.
            for m, n in thieu.most_common():
                log.warning("  model chua co bi danh cho nguon 'monitoring': %s (%d dong)", m, n)
    finally:
        cn.close()


if __name__ == "__main__":
    main()
