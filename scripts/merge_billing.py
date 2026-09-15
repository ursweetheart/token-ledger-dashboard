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
                day gõ tay, so khop CHINH XAC TUYET DOI. Xem PROJECT_MAP.

Cot tien       cost_usd lay tu "Unrounded subtotal ($)", KHONG phai Cost hay
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
anh chup cu the nen la CO TUY CHON --reconcile. Day la bai hoc tu load_billing.py:
no ghim != 2259 va != $270.9517 lam dieu kien dung MAC DINH, nen ban export ngay
mai se lam no dung.

Bat ky phep kiem nao truot -> thoat ma khac 0 va KHONG de lai file nao. Mot file
gop sai nhung ton tai nguy hiem hon khong co file: load_billing.py se nap no vao
database ma khong biet.

CACH DUNG
---------
    python scripts/merge_billing.py
    python scripts/merge_billing.py --reconcile data/billing/billing_gop_tru_CTDA.csv
"""

from __future__ import annotations

import argparse
import collections
import csv
import sys
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "db"))

import connect  # noqa: E402
from rules import guess_kind  # noqa: E402

RAW_DIR = ROOT / "data" / "billing"
FILE_PATTERN = "*GMSSub*.csv"
OUT_DIR = ROOT / "data" / "da_xu_ly" / "billing"

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
PROJECT_MAP = {
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
    + [name for name, _ in MONEY_COLS]

ONE_CENT = Decimal("0.01")


class CheckFailed(Exception):
    """Moi loi khien script dung. Thong diep phai du de nguoi van hanh hanh dong."""


def fail(*rows: str) -> None:
    raise CheckFailed("\n".join(rows))


def money(text: str, where: str) -> Decimal:
    """Doc mot cot tien thanh Decimal, THANG tu chuoi goc, khong qua float."""
    s = (text or "").strip().replace(",", "")
    if s == "":
        fail(f"Empty money column at {where}.",
             "  A Console file always fills all 5 money columns. Empty means the file",
             "  was cut short or partly downloaded. Download it again from the Console.")
    try:
        return Decimal(s)
    except InvalidOperation:
        fail(f"Cannot read the amount {text!r} at {where}.")
        raise  # khong toi day, chi de type checker yen tam


def to_int(text: str, where: str) -> int:
    """Boc dau phay ngan nghin: '21,235' -> 21235."""
    s = (text or "").strip().replace(",", "")
    try:
        d = Decimal(s)
    except InvalidOperation:
        fail(f"Cannot read the usage amount {text!r} at {where}.")
        raise
    if d != d.to_integral_value():
        fail(f"Usage amount {text!r} is not an integer at {where}.",
             "  The Usage amount of a token SKU is always a count. Check the raw file.")
    return int(d)


def fmt_money(d: Decimal) -> str:
    """Giu nguyen do chinh xac cua nguon: 0.123137 -> '0.123137', 0.00 -> '0.00'."""
    return format(d, "f")


def find_files(folder: Path) -> list[Path]:
    """Chon file theo MAU, khong ghim ten.

    Ten file Console chua khoang ngay nguoi dung chon ('... 2026-01-01 - 2026-08-31,
    ...') nen doi theo moi lan xuat. Ghim ten se khien ban xuat moi bi bo qua ma
    script VAN BAO THANH CONG.
    """
    if not folder.is_dir():
        fail(f"Folder not found: {folder}.")
    files = sorted(folder.glob(FILE_PATTERN))
    if not files:
        fail(f"No file matches {FILE_PATTERN!r} in {folder}.",
             "  Download the exports from Cloud Console (Billing > Reports > Download CSV)",
             "  and put them in the folder above, keeping their file names.")
    return files


def display_name(f: Path) -> str:
    """Boc phan sau dau phay CUOI CUNG cua ten file (khong ke duoi .csv).

    'rangdong.com.vn - GMSSub_Reports, 2026-01-01 - 2026-08-31,CRM-feedback.csv'
                                                               ^^^^^^^^^^^^
    """
    if "," not in f.stem:
        fail(f"File name does not follow the Console format: {f.name}",
             "  Expected '... , <date range>,<display name>.csv'.")
    return f.stem.rsplit(",", 1)[1].strip()


def lookup_project(f: Path) -> str:
    name = display_name(f)
    if name not in PROJECT_MAP:
        fail(f"Unknown display name: {name!r}",
             f"  File   : {f}",
             "  Declared in PROJECT_MAP:",
             *[f"    {k!r} -> {v}" for k, v in sorted(PROJECT_MAP.items())],
             "  Do NOT guess the project ID from the display name. Open Cloud Console, take",
             "  the real project ID of this project and add a line to PROJECT_MAP.")
    return PROJECT_MAP[name]


def project_ids_in_dim_agent(dsn: str) -> set[str]:
    """Doc dim_agent.gcp_project_id o che do CHI DOC.

    Truoc 17/08/2026 ham nay goi sqlite3 THANG va nhan mot Path, nen no ghim
    cung vao SQLite. Sau khi PostgreSQL thanh mac dinh thi no la buoc [6/10] cua
    duong ong se DUNG HAN - loi hien ra la "khong thay database", tuc trong nhu
    loi thieu file chu khong phai loi ghim cung he quan tri.

    Nhanh SQLite go han 24/08/2026 (change `drop-the-sqlite-escape-hatch`). Ghi
    chu tren giu lai vi no ke dung cai bay ma ham nay tung dinh: ghim cung mot he
    quan tri roi hong bang mot thong bao noi ve chuyen khac.
    """
    cn, _ = connect.open_db(dsn)
    # Chi doc o muc MAY CHU, khong phai loi hua trong tai lieu - giong
    # backend/store.py. Script nay chi kiem cheo, khong duoc ghi gi.
    cn.set_session(readonly=True)
    try:
        return {r[0] for r in connect.query(
            cn, "SELECT gcp_project_id FROM dim_agent"
                " WHERE gcp_project_id IS NOT NULL")}
    finally:
        cn.close()


def crosscheck_dim_agent(dsn: str) -> None:
    present = project_ids_in_dim_agent(dsn)
    missing = sorted(set(PROJECT_MAP.values()) - present)
    if missing:
        fail("Project IDs in PROJECT_MAP not found in dim_agent:",
             *[f"    {p}" for p in missing],
             f"  Database: {connect.mask_dsn(dsn)}",
             "  Either the map has a typo, or dim_agent does not have this agent yet.",
             "  Cross-check: SELECT agent_id, name, gcp_project_id FROM dim_agent;")


def read_file(f: Path, project: str) -> list[dict]:
    """Doc mot file tho thanh cac dong da chuan hoa. utf-8-sig de nuot BOM."""
    records = []
    with open(f, encoding="utf-8-sig", newline="") as h:
        reader = csv.DictReader(h)
        missing = [c for _, c in MONEY_COLS if c not in (reader.fieldnames or [])]
        if missing:
            fail(f"File is missing columns: {f.name}",
                 f"  Missing : {missing}",
                 f"  Present : {reader.fieldnames}",
                 "  A Console export must keep all 5 money columns. Download the file again.")
        for i, r in enumerate(reader, start=2):  # dong 1 la header
            where = f"{f.name} row {i}"
            sku_name = r["SKU description"]
            kind = guess_kind(sku_name)
            if kind is None:
                fail(f"Unclassified SKU at {where}:",
                     f"  SKU ID  : {r['SKU ID']}",
                     f"  SKU name: {sku_name}",
                     f"  Cost    : ${r['Unrounded subtotal ($)']}",
                     "  guess_kind() in db/rules.py found none of the keywords",
                     "  cached / output / input. Add the rule there, do NOT write a",
                     "  second copy here.")
            d = {
                "day": r["Date"],
                "project": project,
                "service": r["Service description"],
                "sku_id": r["SKU ID"],
                "sku_name": sku_name,
                "kind": kind,
                "quantity": to_int(r["Usage amount"], where),
                "_where": where,
            }
            for out_name, raw_name in MONEY_COLS:
                d[out_name] = money(r[raw_name], f"{where}, column {raw_name!r}")
            records.append(d)
    return records


def check_tier1(records: list[dict]) -> None:
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
    def detail_lines(d: dict) -> list[str]:
        return [f"  Where  : {d['_where']}",
                f"  Key    : day={d['day']} project={d['project']} sku_id={d['sku_id']}",
                f"  Cost              = {fmt_money(d['cost_list_usd'])}",
                f"  Savings programs  = {fmt_money(d['discount_commit_usd'])}",
                f"  Other savings     = {fmt_money(d['discount_other_usd'])}",
                f"  Unrounded subtotal= {fmt_money(d['cost_usd'])}",
                f"  Subtotal          = {fmt_money(d['cost_invoiced_usd'])}"]

    for d in records:
        remainder = (d["cost_list_usd"] - d["discount_commit_usd"]
                   - d["discount_other_usd"]).quantize(ONE_CENT, rounding=ROUND_HALF_UP)
        if remainder != d["cost_invoiced_usd"]:
            fail("LAYER 1 FAILED - the price identity does not hold:",
                 f"  round(Cost - Savings - Other, 2) = {fmt_money(remainder)}",
                 f"  but Subtotal                     = {fmt_money(d['cost_invoiced_usd'])}",
                 *detail_lines(d),
                 "  Two possibilities: (a) Google changed how the discount columns look - check",
                 "  whether discounts are NEGATIVE or POSITIVE, (b) the file was edited by hand.",
                 "  Compare with the invoice on the Console before editing any row.")

        # Chi kiem khi dong nay khong co giam gia. Co giam gia thi Cost la gia
        # TRUOC giam con Unrounded la tien SAU giam - hai ve tach nhau la DUNG.
        if d["discount_commit_usd"] == 0 and d["discount_other_usd"] == 0:
            if d["cost_list_usd"] != d["cost_usd"].quantize(
                    ONE_CENT, rounding=ROUND_HALF_UP):
                fail("LAYER 1 FAILED - Cost does not match Unrounded (row without discount):",
                     f"  Cost                = {fmt_money(d['cost_list_usd'])}",
                     f"  round(Unrounded, 2) = "
                     f"{fmt_money(d['cost_usd'].quantize(ONE_CENT, rounding=ROUND_HALF_UP))}",
                     *detail_lines(d),
                     "  A row with no discount must have both sides equal. A gap means",
                     "  a discount was NOT recorded in the two savings columns -",
                     "  compare with the Gimasys invoice.")

        if d["cost_usd"].quantize(ONE_CENT, rounding=ROUND_HALF_UP) != d["cost_invoiced_usd"]:
            fail("LAYER 1 FAILED - the rounding identity does not hold:",
                 f"  round(Unrounded, 2) = "
                 f"{fmt_money(d['cost_usd'].quantize(ONE_CENT, rounding=ROUND_HALF_UP))}",
                 f"  but Subtotal        = {fmt_money(d['cost_invoiced_usd'])}",
                 *detail_lines(d),
                 "  Google may have changed its rounding rule (ROUND_HALF_UP is assumed,",
                 "  measured to match 2,259/2,259 rows on the 05/08 export).")


def warn_discount(records: list[dict]) -> None:
    """Khoan giam gia la SU KIEN HOP LE, khong phai loi - canh bao roi di tiep."""
    present = [d for d in records
          if d["discount_commit_usd"] != 0 or d["discount_other_usd"] != 0]
    if not present:
        return
    total_by_project = sum((d["discount_commit_usd"] + d["discount_other_usd"] for d in present), Decimal(0))
    print("")
    print("  " + "!" * 68)
    print(f"  !! A DISCOUNT APPEARS FOR THE FIRST TIME: {len(present)} rows, ${fmt_money(total_by_project)} in total")
    print("  !! From now on cost_usd is the cost AFTER the discount, unlike cost_list_usd.")
    print("  !! Every cost figure downstream changes meaning. Review the existing reports.")
    print("  " + "!" * 68)
    print("")


def check_tier2(by_file: dict[Path, list[dict]], records: list[dict]) -> None:
    """Tung project: so dong va tong tien phai bang dung chinh file tho cua no.

    Mot phep so duy nhat bat duoc ca ba kieu hong cua buoc gop: mat dong, nhan doi
    dong, gan nham project.
    """
    count_by_project = collections.Counter(d["project"] for d in records)
    total_by_project = collections.defaultdict(Decimal)
    for d in records:
        total_by_project[d["project"]] += d["cost_usd"]

    for f, raw_rows in by_file.items():
        project = raw_rows[0]["project"] if raw_rows else lookup_project(f)
        n_raw = len(raw_rows)
        t_raw = sum((d["cost_usd"] for d in raw_rows), Decimal(0))
        if count_by_project[project] != n_raw or total_by_project[project] != t_raw:
            fail("LAYER 2 FAILED - a project does not match its own raw file:",
                 f"  Project  : {project}",
                 f"  Raw file : {f.name}",
                 f"  Rows     : result {count_by_project[project]}  |  raw file {n_raw}",
                 f"  Total    : result ${fmt_money(total_by_project[project])}  |  "
                 f"raw file ${fmt_money(t_raw)}",
                 "  Likely: two files map to the same project ID, or a filter in the",
                 "  read step dropped rows. Check PROJECT_MAP first.")


def recon_key(d: dict) -> tuple:
    """Bo khoa tang 3. KHONG co `loai`: ban gop tay khong co cot do de so."""
    return (d["day"], d["project"], d["sku_id"], d["quantity"], d["cost_usd"])


def fmt_key(k: tuple) -> str:
    return f"{k[0]}  {k[1]:24s}  {k[2]}  {k[3]:>10d} token  ${fmt_money(k[4])}"


def reconcile(records: list[dict], ref_path: Path) -> None:
    """Tang 3: trung khit ban gop tay - khong dong thua, khong thieu, khong lech."""
    if not ref_path.is_file():
        fail(f"Reference file not found: {ref_path}")
    with open(ref_path, encoding="utf-8-sig", newline="") as h:
        old_rows = list(csv.DictReader(h))

    old_side = collections.Counter(
        (r["date"], r["project"], r["sku_id"],
         to_int(r["amount"], f"{ref_path.name} (hand-merged file)"),
         Decimal(r["cost"]))
        for r in old_rows)
    new_side = collections.Counter(recon_key(d) for d in records)

    extra = new_side - old_side
    missing = old_side - new_side
    print(f"  layer 3: the hand-merged file has {len(old_rows)} rows "
          f"${fmt_money(sum((Decimal(r['cost']) for r in old_rows), Decimal(0)))}")
    if not extra and not missing:
        print(f"  layer 3: EXACT MATCH on {len(records)} rows")
        return

    examples = ([f"    EXTRA   {fmt_key(k)}" for k in sorted(extra, key=str)[:5]]
          + [f"    MISSING {fmt_key(k)}" for k in sorted(missing, key=str)[:5]])
    fail("LAYER 3 FAILED - does not match the hand-merged file exactly:",
         f"  Reference   : {ref_path}",
         f"  Extra rows  : {sum(extra.values())}   Missing rows: {sum(missing.values())}",
         "  Up to 10 examples (EXTRA = only in the new result, MISSING = only in the hand-merged file):",
         *examples,
         "  Missing rows but no extra ones: raw files are missing. Compare with the",
         "  list of files chosen at the top of this output.")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows mac dinh cp1252
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False)
    p.add_argument("--folder", dest="folder", default=str(RAW_DIR),
                   help="Folder holding the raw files (default data/billing)")
    p.add_argument("--out", dest="out_path", default=None,
                   help="Output file path (default "
                        "data/da_xu_ly/billing/billing_<today>.csv)")
    p.add_argument("--db", default=connect.DEFAULT_DSN,
                   help="DSN used to cross-check PROJECT_MAP against dim_agent (read-only)")
    p.add_argument("--reconcile", dest="reconcile", default=None, metavar="PATH",
                   help="LAYER 3 (optional): match the hand-merged file exactly")
    args = p.parse_args()

    try:
        crosscheck_dim_agent(args.db)

        files = find_files(Path(args.folder))
        by_file: dict[Path, list[dict]] = {}
        print(f"read {len(files)} files from {args.folder}:")
        for f in files:
            project = lookup_project(f)
            rows = read_file(f, project)
            by_file[f] = rows
            print(f"  {len(rows):5d} rows  {project:26s}  {f.name}")

        records = [d for rows in by_file.values() for d in rows]
        if not records:
            fail("No rows read. Are all the raw files empty?")

        check_tier1(records)
        n_discounted = sum(1 for d in records
                     if d["discount_commit_usd"] != 0 or d["discount_other_usd"] != 0)
        print(f"  layer 1: PASS ({len(records)} rows, {len(records) - n_discounted} rows "
              f"checked on all 3 identities, {n_discounted} discounted rows on 2)")
        warn_discount(records)
        check_tier2(by_file, records)
        print(f"  layer 2: PASS ({len(by_file)} projects)")

        # Sap xep ON DINH -> hai lan chay cho ra file giong het nhau toi tung byte,
        # dieu kien de `diff` co y nghia.
        records.sort(key=lambda d: (d["project"], d["day"], d["sku_id"]))

        if args.reconcile:
            reconcile(records, Path(args.reconcile))

        # Dung XONG toan bo noi dung trong bo nho roi moi mo file: khong bao gio
        # de lai file do dang khi co loi.
        out_rows = [[d["day"], d["project"], d["service"], d["sku_id"], d["sku_name"],
                     d["kind"], str(d["quantity"])]
                    + [fmt_money(d[name]) for name, _ in MONEY_COLS]
                    for d in records]

        out_path = Path(args.out_path) if args.out_path else OUT_DIR / f"billing_{date.today():%Y-%m-%d}.csv"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8", newline="") as h:
            w = csv.writer(h)
            w.writerow(OUT_COLS)
            w.writerows(out_rows)

    except CheckFailed as e:
        sys.stdout.flush()  # de thong diep loi khong nhay len truoc phan da in
        print("")
        print(str(e), file=sys.stderr)
        print("output file NOT written.", file=sys.stderr)
        return 1

    total_by_project = sum((d["cost_usd"] for d in records), Decimal(0))
    rows_by_kind = collections.Counter(d["kind"] for d in records)
    money_by_kind = collections.defaultdict(Decimal)
    for d in records:
        money_by_kind[d["kind"]] += d["cost_usd"]
    print("")
    print(f"  {len(records)} rows | ${fmt_money(total_by_project)}")
    for kind in sorted(rows_by_kind):
        print(f"    {kind:8s} {rows_by_kind[kind]:5d} rows  ${fmt_money(money_by_kind[kind])}")
    print(f"  wrote: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
