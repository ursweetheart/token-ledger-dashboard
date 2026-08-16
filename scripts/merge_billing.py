"""Gop 7 file hoa don tai tay tu Google Cloud Console thanh MOT file chuan hoa.

Thay cho thao tac gop tay da sinh ra data/billing/billing_gop_tru_CTDA.csv
(7 file sua luc 10:28-10:36 ngay 05/08, file gop luc 10:45). Duong "dung bai"
la BigQuery billing export nhung bi chan o quyen: tai khoan mua qua dai ly
Gimasys (GMSSub trong ten file), chi ho bat duoc. Xem
docs/explore-2026-08-04-nguon-du-lieu-gcp.md muc 8.1.

QUY TAC AP DUNG
---------------
Anh xa project  File CSV cua Console KHONG co cot nao dinh danh project. Thong
                tin do chi nam o duoi ten file, va do la TEN HIEN THI chu khong
                phai PROJECT ID. Hai khong gian dinh danh khac nhau
                (AI-sale_agent <-> tranquil-post-471401-c1). Bang anh xa duoi
                day gõ tay, so khop CHINH XAC TUYET DOI. Xem ANH_XA_PROJECT.

Cot tien       chi_phi_usd lay tu "Unrounded subtotal ($)", KHONG phai Cost hay
                Subtotal. Hai cot do lam tron toi xu o muc TUNG DONG, khien
                740/2.259 dong (32,8%) hien $0,00 du mang $0,83 tien that va
                8,06 trieu token. Sai so lech mot chieu (bao thieu) vi dong nho
                chi tron xuong 0 duoc, khong co gi tron len bu.

Phan loai SKU   Goi db/rules.py::guess_kind(). Thu tu BAT BUOC cached -> output
                -> input. SKU 911A-8880-A243 ten day du la "Generate content
                OUTPUT token count ... short INPUT text": kiem sai thu tu thi
                38,9% chi phi nhay nham cot MA TONG VAN DUNG.

Decimal         Moi phep tinh tien dung decimal.Decimal doc thang tu chuoi goc.
                Hai bat bien duoi day la DANG THUC CHINH XAC, khong phai so
                sanh co nguong - float lam chung khong kiem duoc.

NGHIEM THU BA TANG - chay HET roi moi ghi file
----------------------------------------------
tang 1  tung dong    Cost - Savings programs - Other savings == Unrounded
                     round(Unrounded, 2) == Subtotal        (ROUND_HALF_UP)
tang 2  tung project so dong va tong tien == chinh file tho cua project do
tang 3  toan bo      trung khit billing_gop_tru_CTDA.csv (2.259 dong $270,9517)

Tang 1 va 2 luon dung voi MOI ban export nen chay mac dinh. Tang 3 ghim vao mot
anh chup cu the nen la CO TUY CHON --doi-chieu. Day la bai hoc tu nap_billing.py:
no ghim != 2259 va != $270.9517 lam dieu kien dung MAC DINH, nen ban export ngay
mai se lam no dung.

Bat ky phep kiem nao truot -> thoat ma khac 0 va KHONG de lai file nao. Mot file
gop sai nhung ton tai nguy hiem hon khong co file: nap_billing.py se nap no vao
database ma khong biet.

CACH DUNG
---------
    python scripts/gop_billing.py
    python scripts/gop_billing.py --doi-chieu data/billing/billing_gop_tru_CTDA.csv
"""

from __future__ import annotations

import argparse
import collections
import csv
import sqlite3
import sys
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "db"))

from rules import guess_kind  # noqa: E402

THU_MUC_THO = ROOT / "data" / "billing"
MAU_FILE = "*GMSSub*.csv"
THU_MUC_RA = ROOT / "data" / "da_xu_ly" / "billing"
DB_MAC_DINH = ROOT / "var" / "token_ledger.sqlite"

# Ten hien thi (duoi ten file Console) -> project ID (cot `project` cua database).
#
# KHONG duoc doan. Thuat toan so khop gan dung se trung 5/7 - du de TRONG NHU
# DANG CHAY - roi truot dung hai project chiem $219,10/$270,95 = 80,9% so tien:
#
#   AI-chatbot-contact-center  -> pro-tuner-454203-v3       khong co gi chung
#   AI-sale_agent              -> tranquil-post-471401-c1   khong co gi chung
#   Multi-model-invoice        -> multimodal-invoice        gan giong, khac that
#   tool-quiz                  -> tools-quizz               gan giong, khac that
#
# Them mot ly do nua: ten hien thi SUA DUOC bat cu luc nao tren Console ma khong
# anh huong project ID. Ai do doi ten hien thi la anh xa doan truot, IM LANG.
ANH_XA_PROJECT = {
    "AI-chatbot-contact-center": "pro-tuner-454203-v3",
    "AI-chatbot-contract-hop-dong": "ai-chatbot-contract",
    "AI-sale_agent": "tranquil-post-471401-c1",
    "CRM-feedback": "crm-500509",
    "Multi-model-invoice": "multimodal-invoice",
    "feedback-dms-tiep-thi": "feedback-dms-tiep-thi",
    "tool-quiz": "tools-quizz",
}

# ten cot dau ra  <-  ten cot trong file tho
MONEY_COLS = [
    ("cost_usd", "Unrounded subtotal ($)"),          # COT CHUAN, moi KPI lay o day
    ("cost_list_usd", "Cost ($)"),               # truoc giam gia
    ("discount_commit_usd", "Savings programs ($)"),       # CUD
    ("discount_other_usd", "Other savings ($)"),             # credit / khuyen mai
    ("cost_invoiced_usd", "Subtotal ($)"),            # so Gimasys thu tien
]
OUT_COLS = ["day", "project", "service", "sku_id", "sku_name", "kind", "quantity"] \
    + [ten for ten, _ in MONEY_COLS]

MOT_XU = Decimal("0.01")


class LoiNghiemThu(Exception):
    """Moi loi khien script dung. Thong diep phai du de nguoi van hanh hanh dong."""


def dung(*dong: str) -> None:
    raise LoiNghiemThu("\n".join(dong))


def tien(chuoi: str, o_dau: str) -> Decimal:
    """Doc mot cot tien thanh Decimal, THANG tu chuoi goc, khong qua float."""
    s = (chuoi or "").strip().replace(",", "")
    if s == "":
        dung(f"Cot tien rong tai {o_dau}.",
             "  File Console luon dien du 5 cot tien. Rong nghia la file bi cat",
             "  hoac tai thieu. Tai lai file tu Console.")
    try:
        return Decimal(s)
    except InvalidOperation:
        dung(f"Khong doc duoc so tien {chuoi!r} tai {o_dau}.")
        raise  # khong toi day, chi de type checker yen tam


def so_nguyen(chuoi: str, o_dau: str) -> int:
    """Boc dau phay ngan nghin: '21,235' -> 21235."""
    s = (chuoi or "").strip().replace(",", "")
    try:
        d = Decimal(s)
    except InvalidOperation:
        dung(f"Khong doc duoc luong dung {chuoi!r} tai {o_dau}.")
        raise
    if d != d.to_integral_value():
        dung(f"Luong dung {chuoi!r} khong phai so nguyen tai {o_dau}.",
             "  Cot Usage amount cua SKU token luon la so dem. Kiem tra lai file tho.")
    return int(d)


def in_tien(d: Decimal) -> str:
    """Giu nguyen do chinh xac cua nguon: 0.123137 -> '0.123137', 0.00 -> '0.00'."""
    return format(d, "f")


def tim_file(thu_muc: Path) -> list[Path]:
    """Chon file theo MAU, khong ghim ten.

    Ten file Console chua khoang ngay nguoi dung chon ('... 2026-01-01 - 2026-08-31,
    ...') nen doi theo moi lan xuat. Ghim ten se khien ban xuat moi bi bo qua ma
    script VAN BAO THANH CONG.
    """
    if not thu_muc.is_dir():
        dung(f"Khong thay thu muc {thu_muc}.")
    files = sorted(thu_muc.glob(MAU_FILE))
    if not files:
        dung(f"Khong file nao khop mau {MAU_FILE!r} trong {thu_muc}.",
             "  Tai cac ban xuat tu Cloud Console (Billing > Reports > Download CSV)",
             "  va dat vao thu muc tren, giu nguyen ten file.")
    return files


def ten_hien_thi(f: Path) -> str:
    """Boc phan sau dau phay CUOI CUNG cua ten file (khong ke duoi .csv).

    'rangdong.com.vn - GMSSub_Reports, 2026-01-01 - 2026-08-31,CRM-feedback.csv'
                                                               ^^^^^^^^^^^^
    """
    if "," not in f.stem:
        dung(f"Ten file khong theo dinh dang Console: {f.name}",
             "  Cho doi dang '... , <khoang ngay>,<ten hien thi>.csv'.")
    return f.stem.rsplit(",", 1)[1].strip()


def tra_project(f: Path) -> str:
    ten = ten_hien_thi(f)
    if ten not in ANH_XA_PROJECT:
        dung(f"Ten hien thi la: {ten!r}",
             f"  File   : {f}",
             "  Dang khai bao trong ANH_XA_PROJECT:",
             *[f"    {k!r} -> {v}" for k, v in sorted(ANH_XA_PROJECT.items())],
             "  KHONG doan project ID tu ten hien thi. Mo Cloud Console, lay dung",
             "  project ID cua project nay roi them mot dong vao ANH_XA_PROJECT.")
    return ANH_XA_PROJECT[ten]


def project_id_trong_dim_agent(db: Path) -> set[str]:
    """Doc dim_agent.gcp_project_id o che do CHI DOC.

    URI SQLite coi '\\' cua Windows la ky tu thoat -> phai dung Path.as_posix().
    """
    if not db.is_file():
        dung(f"Khong thay database {db}.",
             "  Can no de kiem cheo ANH_XA_PROJECT voi dim_agent.gcp_project_id.",
             "  Dung --db de tro toi file khac.")
    cn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        return {r[0] for r in cn.execute(
            "SELECT gcp_project_id FROM dim_agent WHERE gcp_project_id IS NOT NULL")}
    finally:
        cn.close()


def kiem_cheo_dim_agent(db: Path) -> None:
    co = project_id_trong_dim_agent(db)
    thieu = sorted(set(ANH_XA_PROJECT.values()) - co)
    if thieu:
        dung("Project ID trong ANH_XA_PROJECT khong tra duoc trong dim_agent:",
             *[f"    {p}" for p in thieu],
             f"  Database: {db}",
             "  Hoac bang anh xa gõ sai, hoac dim_agent chua co agent nay.",
             "  Doi chieu: SELECT agent_id, ten, gcp_project_id FROM dim_agent;")


def doc_file(f: Path, project: str) -> list[dict]:
    """Doc mot file tho thanh cac dong da chuan hoa. utf-8-sig de nuot BOM."""
    ban_ghi = []
    with open(f, encoding="utf-8-sig", newline="") as h:
        doc = csv.DictReader(h)
        thieu = [c for _, c in MONEY_COLS if c not in (doc.fieldnames or [])]
        if thieu:
            dung(f"File thieu cot: {f.name}",
                 f"  Thieu   : {thieu}",
                 f"  Dang co : {doc.fieldnames}",
                 "  Ban xuat Console phai giu du 5 cot tien. Tai lai file.")
        for i, r in enumerate(doc, start=2):  # dong 1 la header
            o_dau = f"{f.name} dong {i}"
            sku_name = r["SKU description"]
            kind = guess_kind(sku_name)
            if kind is None:
                dung(f"SKU chua phan loai duoc tai {o_dau}:",
                     f"  Ma SKU : {r['SKU ID']}",
                     f"  Ten SKU: {sku_name}",
                     f"  Tien   : ${r['Unrounded subtotal ($)']}",
                     "  guess_kind() trong db/rules.py khong thay tu khoa nao trong",
                     "  cached / output / input. Them quy tac vao do, KHONG viet ban",
                     "  thu hai o day.")
            d = {
                "day": r["Date"],
                "project": project,
                "service": r["Service description"],
                "sku_id": r["SKU ID"],
                "sku_name": sku_name,
                "kind": kind,
                "quantity": so_nguyen(r["Usage amount"], o_dau),
                "_o_dau": o_dau,
            }
            for ten_ra, ten_tho in MONEY_COLS:
                d[ten_ra] = tien(r[ten_tho], f"{o_dau}, cot {ten_tho!r}")
            ban_ghi.append(d)
    return ban_ghi


def kiem_tang_1(ban_ghi: list[dict]) -> None:
    """Tung dong: dang thuc gia va dang thuc lam tron. Decimal chinh xac, khong nguong.

    DAT O DO CHINH XAC XU, khong phai do chinh xac day du. Cot "Cost ($)" CUNG DA
    LAM TRON toi xu nhu Subtotal - do tren 2.259 dong cua ban export 05/08:

        Cost - Savings - Other == Unrounded          4/2259   <- SAI, do ngau nhien
        round(Cost - Savings - Other, 2) == Subtotal 2259/2259
        Cost == round(Unrounded, 2)                  2259/2259
        round(Unrounded, 2) == Subtotal              2259/2259

    Keo theo mot GIOI HAN phai noi thang: Unrounded subtotal KHONG kiem cheo duoc.
    No la cot duy nhat mang gia tri duoi-xu, ba cot kia deu da tron. Ta tin no vi
    no la cot Google tinh ra, khong phai vi ta chung minh duoc no.
    """
    def bay_ra(d: dict) -> list[str]:
        return [f"  Vi tri : {d['_o_dau']}",
                f"  Khoa   : ngay={d['day']} project={d['project']} sku_id={d['sku_id']}",
                f"  Cost              = {in_tien(d['cost_list_usd'])}",
                f"  Savings programs  = {in_tien(d['discount_commit_usd'])}",
                f"  Other savings     = {in_tien(d['discount_other_usd'])}",
                f"  Unrounded subtotal= {in_tien(d['cost_usd'])}",
                f"  Subtotal          = {in_tien(d['cost_invoiced_usd'])}"]

    for d in ban_ghi:
        con_lai = (d["cost_list_usd"] - d["discount_commit_usd"]
                   - d["discount_other_usd"]).quantize(MOT_XU, rounding=ROUND_HALF_UP)
        if con_lai != d["cost_invoiced_usd"]:
            dung("TANG 1 TRUOT - dang thuc gia sai:",
                 f"  round(Cost - Savings - Other, 2) = {in_tien(con_lai)}",
                 f"  nhung Subtotal                   = {in_tien(d['cost_invoiced_usd'])}",
                 *bay_ra(d),
                 "  Hai kha nang: (a) Google doi cach trinh bay cot giam gia - kiem",
                 "  xem khoan giam ghi so AM hay DUONG, (b) file bi sua tay. Doi",
                 "  chieu voi hoa don tren Console truoc khi sua bat ky dong nao.")

        # Chi kiem khi dong nay khong co giam gia. Co giam gia thi Cost la gia
        # TRUOC giam con Unrounded la tien SAU giam - hai ve tach nhau la DUNG.
        if d["discount_commit_usd"] == 0 and d["discount_other_usd"] == 0:
            if d["cost_list_usd"] != d["cost_usd"].quantize(
                    MOT_XU, rounding=ROUND_HALF_UP):
                dung("TANG 1 TRUOT - Cost khong khop Unrounded (dong khong co giam gia):",
                     f"  Cost                = {in_tien(d['cost_list_usd'])}",
                     f"  round(Unrounded, 2) = "
                     f"{in_tien(d['cost_usd'].quantize(MOT_XU, rounding=ROUND_HALF_UP))}",
                     *bay_ra(d),
                     "  Dong khong co khoan giam nao thi hai ve phai bang nhau. Lech",
                     "  nghia la co khoan giam KHONG duoc ghi vao hai cot savings -",
                     "  doi chieu voi hoa don Gimasys.")

        if d["cost_usd"].quantize(MOT_XU, rounding=ROUND_HALF_UP) != d["cost_invoiced_usd"]:
            dung("TANG 1 TRUOT - dang thuc lam tron sai:",
                 f"  round(Unrounded, 2) = "
                 f"{in_tien(d['cost_usd'].quantize(MOT_XU, rounding=ROUND_HALF_UP))}",
                 f"  nhung Subtotal      = {in_tien(d['cost_invoiced_usd'])}",
                 *bay_ra(d),
                 "  Co the Google doi quy tac lam tron (dang gia dinh ROUND_HALF_UP,",
                 "  da do khop 2.259/2.259 dong tren ban export 05/08).")


def canh_bao_giam_gia(ban_ghi: list[dict]) -> None:
    """Khoan giam gia la SU KIEN HOP LE, khong phai loi - canh bao roi di tiep."""
    co = [d for d in ban_ghi
          if d["discount_commit_usd"] != 0 or d["discount_other_usd"] != 0]
    if not co:
        return
    tong = sum((d["discount_commit_usd"] + d["discount_other_usd"] for d in co), Decimal(0))
    print("")
    print("  " + "!" * 68)
    print(f"  !! LAN DAU XUAT HIEN KHOAN GIAM GIA: {len(co)} dong, tong ${in_tien(tong)}")
    print("  !! Tu day chi_phi_usd la tien SAU giam gia, khac chi_phi_niem_yet_usd.")
    print("  !! Moi con so chi phi phia sau doi nghia. Xem lai cac bao cao dang co.")
    print("  " + "!" * 68)
    print("")


def kiem_tang_2(theo_file: dict[Path, list[dict]], ban_ghi: list[dict]) -> None:
    """Tung project: so dong va tong tien phai bang dung chinh file tho cua no.

    Mot phep so duy nhat bat duoc ca ba kieu hong cua buoc gop: mat dong, nhan doi
    dong, gan nham project.
    """
    dem = collections.Counter(d["project"] for d in ban_ghi)
    tong = collections.defaultdict(Decimal)
    for d in ban_ghi:
        tong[d["project"]] += d["cost_usd"]

    for f, dong_tho in theo_file.items():
        project = dong_tho[0]["project"] if dong_tho else tra_project(f)
        n_tho = len(dong_tho)
        t_tho = sum((d["cost_usd"] for d in dong_tho), Decimal(0))
        if dem[project] != n_tho or tong[project] != t_tho:
            dung("TANG 2 TRUOT - project khong khop file tho cua no:",
                 f"  Project  : {project}",
                 f"  File tho : {f.name}",
                 f"  So dong  : ket qua {dem[project]}  |  file tho {n_tho}",
                 f"  Tong tien: ket qua ${in_tien(tong[project])}  |  "
                 f"file tho ${in_tien(t_tho)}",
                 "  Kha nang: hai file cung anh xa ve mot project ID, hoac bo loc",
                 "  o buoc doc da bo dong. Kiem ANH_XA_PROJECT truoc.")


def khoa_doi_chieu(d: dict) -> tuple:
    """Bo khoa tang 3. KHONG co `loai`: ban gop tay khong co cot do de so."""
    return (d["day"], d["project"], d["sku_id"], d["quantity"], d["cost_usd"])


def in_khoa(k: tuple) -> str:
    return f"{k[0]}  {k[1]:24s}  {k[2]}  {k[3]:>10d} token  ${in_tien(k[4])}"


def doi_chieu(ban_ghi: list[dict], moc: Path) -> None:
    """Tang 3: trung khit ban gop tay - khong dong thua, khong thieu, khong lech."""
    if not moc.is_file():
        dung(f"Khong thay file moc doi chieu: {moc}")
    with open(moc, encoding="utf-8-sig", newline="") as h:
        cu = list(csv.DictReader(h))

    ben_cu = collections.Counter(
        (r["date"], r["project"], r["sku_id"],
         so_nguyen(r["amount"], f"{moc.name} (ban gop tay)"),
         Decimal(r["cost"]))
        for r in cu)
    ben_moi = collections.Counter(khoa_doi_chieu(d) for d in ban_ghi)

    thua = ben_moi - ben_cu
    thieu = ben_cu - ben_moi
    print(f"  tang 3: ban gop tay {len(cu)} dong "
          f"${in_tien(sum((Decimal(r['cost']) for r in cu), Decimal(0)))}")
    if not thua and not thieu:
        print(f"  tang 3: TRUNG KHIT {len(ban_ghi)} dong")
        return

    vd = ([f"    THUA  {in_khoa(k)}" for k in sorted(thua, key=str)[:5]]
          + [f"    THIEU {in_khoa(k)}" for k in sorted(thieu, key=str)[:5]])
    dung("TANG 3 TRUOT - khong trung khit ban gop tay:",
         f"  Moc      : {moc}",
         f"  Dong thua: {sum(thua.values())}   Dong thieu: {sum(thieu.values())}",
         "  Toi da 10 vi du (THUA = chi co o ket qua moi, THIEU = chi co o ban gop tay):",
         *vd,
         "  Neu chi thieu ma khong thua: dang tai thieu file tho. Doi chieu danh",
         "  sach file da chon o dau ban in nay.")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows mac dinh cp1252
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--thu-muc", default=str(THU_MUC_THO),
                   help="Thu muc chua file tho (mac dinh data/billing)")
    p.add_argument("--ra", default=None,
                   help="Duong dan file dau ra (mac dinh "
                        "data/da_xu_ly/billing/billing_<hom-nay>.csv)")
    p.add_argument("--db", default=str(DB_MAC_DINH),
                   help="SQLite de kiem cheo ANH_XA_PROJECT voi dim_agent (chi doc)")
    p.add_argument("--doi-chieu", default=None, metavar="DUONG_DAN",
                   help="TANG 3 (tuy chon): so trung khit voi ban gop tay")
    args = p.parse_args()

    try:
        kiem_cheo_dim_agent(Path(args.db))

        files = tim_file(Path(args.thu_muc))
        theo_file: dict[Path, list[dict]] = {}
        print(f"Doc {len(files)} file tu {args.thu_muc}:")
        for f in files:
            project = tra_project(f)
            dong = doc_file(f, project)
            theo_file[f] = dong
            print(f"  {len(dong):5d} dong  {project:26s}  {f.name}")

        ban_ghi = [d for dong in theo_file.values() for d in dong]
        if not ban_ghi:
            dung("Khong doc duoc dong nao. Cac file tho deu rong?")

        kiem_tang_1(ban_ghi)
        n_giam = sum(1 for d in ban_ghi
                     if d["discount_commit_usd"] != 0 or d["discount_other_usd"] != 0)
        print(f"  tang 1: DAT ({len(ban_ghi)} dong, {len(ban_ghi) - n_giam} dong "
              f"kiem du 3 dang thuc, {n_giam} dong co giam gia kiem 2)")
        canh_bao_giam_gia(ban_ghi)
        kiem_tang_2(theo_file, ban_ghi)
        print(f"  tang 2: DAT ({len(theo_file)} project)")

        # Sap xep ON DINH -> hai lan chay cho ra file giong het nhau toi tung byte,
        # dieu kien de `diff` co y nghia.
        ban_ghi.sort(key=lambda d: (d["project"], d["day"], d["sku_id"]))

        if args.doi_chieu:
            doi_chieu(ban_ghi, Path(args.doi_chieu))

        # Dung XONG toan bo noi dung trong bo nho roi moi mo file: khong bao gio
        # de lai file do dang khi co loi.
        noi_dung = [[d["day"], d["project"], d["service"], d["sku_id"], d["sku_name"],
                     d["kind"], str(d["quantity"])]
                    + [in_tien(d[ten]) for ten, _ in MONEY_COLS]
                    for d in ban_ghi]

        ra = Path(args.ra) if args.ra else THU_MUC_RA / f"billing_{date.today():%Y-%m-%d}.csv"
        ra.parent.mkdir(parents=True, exist_ok=True)
        with open(ra, "w", encoding="utf-8", newline="") as h:
            w = csv.writer(h)
            w.writerow(OUT_COLS)
            w.writerows(noi_dung)

    except LoiNghiemThu as e:
        sys.stdout.flush()  # de thong diep loi khong nhay len truoc phan da in
        print("")
        print(str(e), file=sys.stderr)
        print("KHONG ghi file dau ra.", file=sys.stderr)
        return 1

    tong = sum((d["cost_usd"] for d in ban_ghi), Decimal(0))
    theo_loai = collections.Counter(d["kind"] for d in ban_ghi)
    tien_loai = collections.defaultdict(Decimal)
    for d in ban_ghi:
        tien_loai[d["kind"]] += d["cost_usd"]
    print("")
    print(f"  {len(ban_ghi)} dong | ${in_tien(tong)}")
    for loai in sorted(theo_loai):
        print(f"    {loai:8s} {theo_loai[loai]:5d} dong  ${in_tien(tien_loai[loai])}")
    print(f"  Da ghi: {ra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
