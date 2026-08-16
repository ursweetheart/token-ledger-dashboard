"""Swap the dashboard's seed data and price table for the real ones.

Three edits, all of them to data literals. No function is touched, no markup is
touched, and the row shape is unchanged, so every chart keeps computing exactly
what it computed before -- from real numbers instead of spreadsheet extracts.

  1. basePricing   two wrong rates corrected, four missing models added.
                   Every rate is money-divided-by-tokens straight out of
                   Google's invoice, not a figure copied off a price page.
  2. SEED_DAYS     replaced wholesale by the generated block.
  3. STORE         version bumped, otherwise a returning browser keeps serving
                   the old data out of localStorage and none of this shows up.

buildJuneExcelWeeks() is deliberately left alone. defaultState() merges it
UNDER SEED_DAYS, and all four of its dates now exist in the new data, so every
one of its rows is overwritten. Deleting it would be a code change for no
behavioural gain.

Writes app.js. Keeps a .bak next to it.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "js" / "app.js"
SEED = Path(__file__).parent / "seed-days-that.js"

# Hau to mo ta dot cap nhat nay, gan sau so phien ban trong khoa localStorage.
NHAN_PHIEN_BAN = "du-lieu-13-08"
MO_TA_PHIEN_BAN = ("dữ liệu tới 13/08/2026 "
                   "(billing + monitoring gộp 2 đợt + Ralli/TLA HĐ)")

# USD / 1 trieu token, suy tu hoa don: chi phi thuc chia cho so token thuc.
GIA = """/* ─── Bảng giá (USD / 1 triệu token) ───
   Mọi đơn giá dưới đây suy từ HOÁ ĐƠN Google: lấy số tiền thật chia cho số token
   thật trong data/billing/. Không chép từ trang giá.
   Hai giá đã sửa so với bản cũ:
     Gemini 2.5 Pro   giá ra  3.75 -> 10.00   (hoá đơn: $10.0000/1tr)
     Gemini 3.5 Flash 0/0     -> 1.50 / 9.00  (trước ghi là "chưa dùng", thực tế có dùng)
   Bốn model bổ sung vì có phát sinh thật nhưng chưa được khai báo. ─── */
var basePricing = {
  "Gemini 2.5 Flash":       {i:0.30, o:2.50},
  "Gemini 2.5 Flash Lite":  {i:0.10, o:0.40},
  "Gemini 2.5 Pro":         {i:1.25, o:10.00},
  "Gemini 2.0 Flash":       {i:0.10, o:0.40},
  "Gemini 3.0 Flash":       {i:0.50, o:3.00},
  "Gemini 3.1 Flash Lite":  {i:0.25, o:1.50},
  "Gemini 3.5 Flash":       {i:1.50, o:9.00},
  "Gemini 3 Pro":           {i:2.00, o:12.00},
  "Gemini Embedding 001":   {i:0.1510, o:0},
  "GPT-4o mini":            {i:0.15, o:0.60},   // OpenAI — giữ sẵn cho nhập thủ công
  "GPT-4o":                 {i:2.50, o:10.00}   // OpenAI — đã khai báo, chưa dùng
};"""


def thay(text: str, patterns, moi: str, ten: str) -> str:
    """One substitution, and a loud failure if it did not match exactly once.

    Takes a LIST of alternative patterns so the script stays runnable after it
    has already run once: the first pass rewrites the very comment headers the
    patterns anchor on, so a single fixed pattern would match zero times on the
    second pass and the run would abort with nothing done.
    """
    if isinstance(patterns, str):
        patterns = [patterns]
    for pattern in patterns:
        found = re.findall(pattern, text, re.S)
        if len(found) == 1:
            return re.sub(pattern, lambda _: moi, text, count=1, flags=re.S)
        if len(found) > 1:
            raise SystemExit(f"DUNG: mau '{ten}' khop {len(found)} lan, phai dung 1.")
    raise SystemExit(f"DUNG: khong mau nao cua '{ten}' khop. File da bi sua tay?")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not SEED.exists():
        raise SystemExit(f"Chua co {SEED}. Chay test/sinh_du_lieu_dashboard.py truoc.")

    text = APP.read_text(encoding="utf-8")
    truoc = len(text)
    sao_luu = APP.with_suffix(".js.bak")
    if not sao_luu.exists():
        shutil.copy2(APP, sao_luu)

    # 1. bang gia — mau cu (chua va) hoac mau moi (da va lan truoc)
    text = thay(text,
                [r"/\* ─── Bảng giá gốc.*?\nvar basePricing = \{.*?\n\};",
                 r"/\* ─── Bảng giá \(USD.*?\nvar basePricing = \{.*?\n\};"],
                GIA, "basePricing")

    # 2. du lieu seed — mau cu hoac mau da sinh tu dong
    khoi = SEED.read_text(encoding="utf-8").rstrip()
    text = thay(text,
                [r"/\* ─── Dữ liệu THẬT tháng 7/2026.*?\nvar SEED_DAYS = \{.*?\n\};",
                 r"/\* ═+\n   SEED_DAYS — sinh tự động.*?\nvar SEED_DAYS = \{.*?\n\};"],
                khoi, "SEED_DAYS")

    # 3. khoang ngay mac dinh — suy TU DU LIEU, khong ghim ngay chet
    #
    # defaultState() dang ghim range 01/07-31/07. Du lieu chay toi 13/08 nhung
    # nguoi mo dashboard van thay thang 7, tuc phan cap nhat khong nhin thay
    # duoc. Ghim mot ngay moi chi doi cho cu ky han: lay thang cua NGAY CUOI
    # CUNG co du lieu thi lan sinh sau tu dung.
    moc = sorted(re.findall(r'^\s*"(\d{4}-\d{2}-\d{2})":\s*\[', khoi, re.M))
    if not moc:
        raise SystemExit("DUNG: khong doc duoc ngay nao trong khoi seed.")
    cuoi = moc[-1]
    dau_thang = cuoi[:8] + "01"
    so_thay = len(re.findall(r'\{\s*start:"\d{4}-\d{2}-\d{2}",\s*end:"\d{4}-\d{2}-\d{2}"\s*\}', text))
    text = re.sub(r'\{\s*start:"\d{4}-\d{2}-\d{2}",\s*end:"\d{4}-\d{2}-\d{2}"\s*\}',
                  f'{{start:"{dau_thang}",end:"{cuoi}"}}', text)
    if so_thay == 0:
        raise SystemExit("DUNG: khong tim thay range mac dinh nao de sua.")

    # 4. bump phien ban localStorage
    #
    # PHAI tang so, khong duoc ghim cung mot chuoi dich. Ban truoc ghim
    # "...v18-ma-loi-that" trong khi app.js DA la v18, nen phep thay thanh vo
    # hieu: trinh duyet cu tiep tuc doc du lieu cu tu localStorage va toan bo
    # dot cap nhat khong hien ra man hinh - hong mot cach hoan toan im lang.
    cu = re.search(r'var STORE = "([^"]+)"', text)
    if not cu:
        raise SystemExit("DUNG: khong tim thay STORE.")
    so = re.search(r"-v(\d+)-", cu.group(1))
    if not so:
        raise SystemExit(f"DUNG: STORE '{cu.group(1)}' khong co dang -v<so>-.")
    so_moi = int(so.group(1)) + 1
    moi_ten = f"agent-dash-state-v{so_moi}-{NHAN_PHIEN_BAN}"
    # Thay ca dong ke ca chu thich: de nguyen chu thich cu thi dong nay se ghi
    # "v19" o gia tri nhung "v18" o loi giai thich, va nguoi doc sau tin cai sai.
    text = re.sub(r'var STORE = "[^"]+";[^\n]*',
                  f'var STORE = "{moi_ten}"; // v{so_moi}: {MO_TA_PHIEN_BAN}',
                  text, count=1)

    APP.write_text(text, encoding="utf-8")
    print(f"  Sao luu : {APP.with_suffix('.js.bak').name}")
    print(f"  app.js  : {truoc:,} -> {len(text):,} ky tu")
    print(f"  STORE   : {cu.group(1)}  ->  {moi_ten}")


if __name__ == "__main__":
    main()
