"""Sinh db/02_danh_muc.sql tu du lieu that - chi doc file, khong goi mang.

VI SAO SINH BANG MAY
--------------------
File danh muc co hon 40 dong anh xa ten model. Go tay thi sai mot dong cung
khong ai phat hien: tong tien van dung, chi ty le giua cac model la sai. Sinh
bang may thi quy tac nam trong db/quy_tac.py, doc lai va kiem lai duoc.

Ngay bat dau / ket thuc co du lieu cung TINH TU FILE thay vi go tay.

Nhung `dang_van_hanh` thi GO TAY co chu dich. Do la ket luan nghiep vu (muc C3:
tool-quiz ngung tu 30/06, Multi-model-invoice tu 25/07), khong phai thu suy ra
duoc bang nguong "bao nhieu ngay khong co du lieu thi coi la ngung". Mot nguong
nhu vay se am tham phan loai sai moi khi mot agent nghi le dai.

Chay: python db/sinh_02_danh_muc.py
"""

from __future__ import annotations

import collections
import csv
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from quy_tac import MA_MODEL, MODELS, suy_loai, suy_model  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BILLING = ROOT / "data" / "billing" / "billing_gop_tru_CTDA.csv"
MON = ROOT / "data" / "raw_google_console" / "du_lieu_giam_sat" / "2026-08-06-1m"
RALLI_RAW = ROOT / "data" / "ctda" / "db-token_usage-raw.json"
RA = ROOT / "db" / "02_danh_muc.sql"

# id, ma, ten, project, co_cay_to_chuc, ngay_tao_project, dang_van_hanh
# ngay_tao_project lay tu `gcloud projects list`, ghi trong ke hoach muc 0.
AGENTS = [
    (1, "contact-center", "Chatbot Contact Center", "pro-tuner-454203-v3", False, "2025-03-19", True),
    (2, "sale-agent", "Sale Agent", "tranquil-post-471401-c1", False, "2025-09-07", True),
    (3, "invoice", "Multi modal AI Invoice", "multimodal-invoice", False, "2025-09-15", False),
    (4, "tools-quizzer", "Tools Quizzer", "tools-quizz", False, "2026-04-10", False),
    (5, "tla-hd", "Trợ Lý Ảo Hợp Đồng", "ai-chatbot-contract", True, "2026-06-20", True),
    (6, "dms-feedback", "Phân Loại Phản Hồi Tiếp Thị", "feedback-dms-tiep-thi", False, "2026-06-25", True),
    (7, "crm-feedback", "Phân Loại Dữ Liệu CRM", "crm-500509", False, "2026-06-25", True),
    (8, "ralli", "Trợ lý ảo Ralli", None, True, None, True),
]

# app.js dong 15-22. Tools Quizzer va Ralli KHONG co trong danh sach do.
NGAN_SACH_USD = {
    "Trợ Lý Ảo Hợp Đồng": 20, "Chatbot Contact Center": 30, "Phân Loại Dữ Liệu CRM": 20,
    "Phân Loại Phản Hồi Tiếp Thị": 20, "Multi modal AI Invoice": 20, "Sale Agent": 50,
}
VND_RATE = 25200                      # app.js dong 25
NGAN_SACH_RALLI_TOKEN = 50_000_000    # data/ctda/token-usage-budget.json
THANG = "2026-08-01"
NGAY_FX = "2026-08-08"


def nq(s) -> str:
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"


def khoang_du_lieu() -> dict[str, tuple[str, str]]:
    ngay: dict[str, list[str]] = collections.defaultdict(list)
    with open(BILLING, encoding="utf-8-sig") as h:
        for r in csv.DictReader(h):
            ngay[r["project"]].append(r["date"])
    for f in sorted(glob.glob(str(MON / "*.csv"))):
        with open(f, encoding="utf-8-sig") as h:
            for r in csv.DictReader(h):
                svc = r["res_service"] or r["metric_type"].split("/")[0]
                if svc.startswith("generativelanguage"):
                    ngay[r["gcp_project_id"]].append(r["ts_ict"][:10])
    with open(RALLI_RAW, encoding="utf-8-sig") as h:
        goc = json.load(h)
    raw = goc if isinstance(goc, list) else list(goc.values())[0]
    ngay["__ralli__"] = [str(r["timestamp"])[:10] for r in raw]
    return {p: (min(v), max(v)) for p, v in ngay.items()}


def anh_xa_model() -> list[tuple[str, str, int]]:
    """(nguon, ten_goc, model_id). Dung han neu gap ten khong suy duoc."""
    alias: list[tuple[str, str, int]] = []
    hong: list[str] = []

    sku: dict[str, str] = {}
    with open(BILLING, encoding="utf-8-sig") as h:
        for r in csv.DictReader(h):
            sku[r["sku_id"]] = r["sku"]
    for sid, ten in sorted(sku.items()):
        m, l = suy_model(ten), suy_loai(ten)
        if not m or not l:
            hong.append(f"SKU {sid} '{ten}' -> model={m} loai={l}")
        else:
            alias.append(("billing_sku", sid, MA_MODEL[m]))

    nhan: set[tuple[str, str]] = set()
    for f in sorted(glob.glob(str(MON / "*.csv"))):
        with open(f, encoding="utf-8-sig") as h:
            for r in csv.DictReader(h):
                if r["model"]:
                    nhan.add(("monitoring", r["model"]))
    for f in (ROOT / "data/ctda/by-model-2026.csv", ROOT / "data/tla-hd/by-model-2026.csv"):
        with open(f, encoding="utf-8-sig") as h:
            for r in csv.DictReader(h):
                # 'none' cua TLA HD la 2 luot goi 0 token, KHONG phai mot model.
                if r["model"] and r["model"] != "none":
                    nhan.add(("app", r["model"]))
    for nguon, ten in sorted(nhan):
        if ten not in MA_MODEL:
            hong.append(f"nhan {nguon} '{ten}' khong co trong danh sach model chuan")
        else:
            alias.append((nguon, ten, MA_MODEL[ten]))

    if hong:
        raise SystemExit("KHONG ANH XA DUOC - them vao db/quy_tac.py roi chay lai:\n  "
                         + "\n  ".join(hong))
    return alias


def main() -> None:
    khoang = khoang_du_lieu()
    alias = anh_xa_model()

    ra: list[str] = []
    A = ra.append
    A("-- ==============================================================")
    A("-- SINH TU DONG boi db/sinh_02_danh_muc.py - dung sua tay.")
    A("-- Sua quy tac trong db/quy_tac.py hoac trong script do roi chay lai.")
    A("-- ==============================================================")
    A("")
    A("-- 8 agent. Khoang ngay TINH TU DU LIEU; dang_van_hanh go tay theo muc C3.")
    A("INSERT INTO dim_agent (agent_id, ma, ten, gcp_project_id, co_cay_to_chuc,")
    A("                       ngay_tao_project, ngay_bat_dau_co_du_lieu,")
    A("                       ngay_ket_thuc_du_lieu, dang_van_hanh, co_nguon_doi_chung) VALUES")
    dong = []
    for aid, ma, ten, proj, cay, tao, chay in AGENTS:
        dau, cuoi = khoang["__ralli__"] if proj is None else khoang[proj]
        dong.append(f"  ({aid}, {nq(ma)}, {nq(ten)}, {nq(proj)}, {str(cay).upper()}, "
                    f"{nq(tao)}, {nq(dau)}, {'NULL' if chay else nq(cuoi)}, "
                    f"{str(chay).upper()}, {str(proj is not None).upper()})")
    A(",\n".join(dong) + ";")
    A("")
    A(f"-- {len(MODELS)} model, ten chuan dang gach ngang.")
    A("INSERT INTO dim_model (model_id, ten, ho, provider) VALUES")
    A(",\n".join(f"  ({i}, {nq(t)}, {nq(h)}, 'Google')" for i, t, h in MODELS) + ";")
    A("")
    A(f"-- {len(alias)} anh xa. Ba nguon goi ten model theo ba kieu khac nhau:")
    A("--   billing 'gemini-embedding-001'  <->  monitoring 'gemini-embedding-1.0'")
    A("INSERT INTO dim_model_alias (nguon, ten_goc, model_id) VALUES")
    A(",\n".join(f"  ({nq(n)}, {nq(t)}, {m})" for n, t, m in alias) + ";")
    A("")
    A("-- Ty gia go cung (quyet dinh M-F). Keo API sau, cau truc khong phai doi.")
    A(f"INSERT INTO ref_fx (ngay, vnd_moi_usd, nguon) VALUES "
      f"({nq(NGAY_FX)}, {VND_RATE}, 'go cung (app.js)');")
    A("")
    A("-- Ralli chan theo TOKEN, sau agent kia theo TIEN. Khong quy doi.")
    A("-- Tools Quizzer khong co ngan sach: app.js da loai khoi danh sach.")
    A("INSERT INTO ref_budget (agent_id, thang, ngan_sach_usd, ngan_sach_token) VALUES")
    ns = []
    for aid, ma, ten, proj, cay, tao, chay in AGENTS:
        if ten in NGAN_SACH_USD:
            ns.append(f"  ({aid}, {nq(THANG)}, {NGAN_SACH_USD[ten]}, NULL)")
        elif ma == "ralli":
            ns.append(f"  ({aid}, {nq(THANG)}, NULL, {NGAN_SACH_RALLI_TOKEN})")
    A(",\n".join(ns) + ";")
    A("")

    RA.write_text("\n".join(ra), encoding="utf-8")
    n = collections.Counter(x[0] for x in alias)
    print(f"Ghi {RA}")
    print(f"  {len(AGENTS)} agent | {len(MODELS)} model | {len(alias)} anh xa {dict(n)} "
          f"| 1 ty gia | {len(ns)} ngan sach")


if __name__ == "__main__":
    main()
