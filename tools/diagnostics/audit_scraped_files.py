"""Soát các file VỪA CÀO trước khi bàn giao cho người khác nạp lên server.

    python tools/diagnostics/audit_scraped_files.py

VÌ SAO CẦN
----------
`scripts/audit_db.py` soi DATABASE. Khi việc chỉ dừng ở "cào rồi gửi file đi",
database không được dựng, nên không phép kiểm nào chạm vào bộ file bàn giao.
Người nhận nạp một bộ file thiếu thì phát hiện ra ở phía họ - muộn, và trên một
máy mà mình không nhìn thấy.

Script này CHỈ ĐỌC file trên đĩa. Không nối database, không gọi mạng.

BỐN PHẦN
--------
1  Hoá đơn thô          7 project, file nào KHÔNG thuộc đợt tải này
2  Bất biến lịch sử     bản gộp mới vs bản gộp trước: CHỈ ngày cuối được đổi
3  Cloud Monitoring     các đợt kéo, dải ngày, độ phủ HỢP NHẤT của mọi đợt
4  Danh mục bàn giao    file nào, bao nhiêu byte, mới tới ngày nào

Mã thoát: 0 nếu không phát hiện gì đáng dừng, 1 nếu có. Phần 2 lệch ở ngày KHÁC
ngày cuối là đáng dừng thật - nó nghĩa là Google viết lại lịch sử, khác hẳn với
việc chốt muộn ngày cuối.
"""

from __future__ import annotations

import collections
import csv
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BILLING_RAW = ROOT / "data" / "billing"
BILLING_MERGED = ROOT / "data" / "da_xu_ly" / "billing"
MONITOR_RAW = ROOT / "data" / "raw_google_console" / "du_lieu_giam_sat"
MONITOR_MERGED = ROOT / "data" / "da_xu_ly" / "du_lieu_giam_sat"
LATENCY = ROOT / "data" / "raw_google_console" / "do_tre_phan_bo"

# Ngưỡng để nói một file KHÔNG thuộc đợt tải này. Bám vào thời điểm tải chứ không
# bám vào ngày cuối của dữ liệu - xem note chú trong part_1_raw_billing().
STALE_AFTER_HOURS = 24        # file tải trước đợt mới nhất quá ngần này giờ = không cùng đợt

findings: list[str] = []


def print_heading(number: int, text: str) -> None:
    print(f"\n{'─' * 76}\n{number}. {text.upper()}\n{'─' * 76}")


def display_name(f: Path) -> str:
    """Phần sau dấu phẩy cuối cùng - cùng quy tắc scripts/merge_billing.py."""
    return f.stem.rsplit(",", 1)[1].strip() if "," in f.stem else f.stem


def collapse_ranges(days: list[date]) -> list[str]:
    """[1,2,3,7] -> ['01/01-03/01', '07/01']. Để in dải ngày cho gọn."""
    if not days:
        return []
    segments, start, prev = [], days[0], days[0]
    for d in days[1:]:
        if (d - prev).days == 1:
            prev = d
            continue
        segments.append((start, prev))
        start = prev = d
    segments.append((start, prev))
    return [f"{a:%d/%m}" if a == b else f"{a:%d/%m}-{b:%d/%m}" for a, b in segments]


def short_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:,.1f} {unit}"
        n /= 1024
    return ""


# ---------------------------------------------------------------- phần 1


def part_1_raw_billing() -> None:
    print_heading(1, "Hoá đơn thô — 7 file tải tay")
    files = sorted(BILLING_RAW.glob("*GMSSub*.csv"))
    if not files:
        findings.append(f"Không có file hoá đơn nào trong {BILLING_RAW}")
        print("  KHÔNG CÓ FILE NÀO.")
        return

    table = []
    for f in files:
        days = []
        with f.open(encoding="utf-8-sig", newline="") as h:
            for r in csv.DictReader(h):
                d = (r.get("Date") or "").strip()
                if d:
                    days.append(d)
        table.append((display_name(f), len(days), min(days) if days else "-",
                     max(days) if days else "-",
                     datetime.fromtimestamp(f.stat().st_mtime)))

    # PHÂN BIỆT HAI THỨ HAY BỊ LẪN
    # ----------------------------
    # "ngày cuối" là ngày cuối cùng agent đó CÓ DÙNG. Một agent ngừng dùng từ
    # 20/08 thì file tải hôm nay vẫn kết thúc ở 20/08, và đó là số ĐÚNG.
    # "tải lúc" là thời điểm file rời Console. Đây mới là thứ nói được file có
    # nằm trong đợt tải này hay không.
    #
    # Bản đầu của script này gắn cờ theo `ngày cuối` và đã báo nhầm 2/7 file
    # vừa tải xong là "đứng số". Cờ phải bám vào `tải lúc`.
    newest_download = max(r[4] for r in table)
    print(f"  {'tên hiển thị':30s} {'dòng':>6s}  {'ngày đầu':10s}  {'ngày cuối':10s}  tải lúc")
    for name, row_count, start, end, downloaded_at in sorted(table, key=lambda r: r[4]):
        hours_behind = (newest_download - downloaded_at).total_seconds() / 3600
        is_stale = hours_behind > STALE_AFTER_HOURS
        marker = "!!" if is_stale else "  "
        note = f"cũ hơn đợt này {hours_behind / 24:.0f} ngày" if is_stale else ""
        if is_stale:
            findings.append(
                f"Hoá đơn `{name}` tải lúc {downloaded_at:%d/%m %H:%M}, không thuộc đợt tải này "
                f"(dữ liệu dừng ở {end})")
        print(f"{marker}{name:30s} {row_count:6d}  {start:10s}  {end:10s}  "
              f"{downloaded_at:%d/%m %H:%M}  {note}")
    print(f"\n  Đợt tải mới nhất: {newest_download:%d/%m/%Y %H:%M}. `!!` = file tải trước đó")
    print("  quá 24 giờ, tức KHÔNG được tải lại cùng đợt với các file kia.")
    print("  `ngày cuối` sớm mà `tải lúc` mới thì bình thường: agent đó ngừng dùng.")


# ---------------------------------------------------------------- phần 2


def read_merged(p: Path) -> dict[tuple[str, str, str], dict]:
    with p.open(encoding="utf-8") as h:
        return {(r["day"], r["project"], r["sku_id"]): r for r in csv.DictReader(h)}


def part_2_invariants() -> None:
    print_heading(2, "Bất biến lịch sử — bản gộp mới vs bản gộp trước")
    snapshots = sorted(BILLING_MERGED.glob("billing_*.csv"))
    if len(snapshots) < 2:
        print(f"  Chỉ có {len(snapshots)} bản gộp, chưa number được. Bỏ qua.")
        return

    prev, latest = snapshots[-2], snapshots[-1]
    a, b = read_merged(prev), read_merged(latest)
    shared, missing, added = set(a) & set(b), set(a) - set(b), set(b) - set(a)
    rewritten = [k for k in shared
            if a[k]["quantity"] != b[k]["quantity"] or a[k]["cost_usd"] != b[k]["cost_usd"]]
    prev_last_day = max(k[0] for k in a)

    print(f"  {prev.name}  ->  {latest.name}")
    print(f"  chồng nhau {len(shared):5d} khoá | mất {len(missing)} | thêm mới {len(added)} "
          f"| viết lại {len(rewritten)}")

    rewritten_outside_edge = sorted({k[0] for k in rewritten if k[0] != prev_last_day})
    print(f"  Ngày cuối của bản trước: {prev_last_day} — mọi thay đổi ĐƯỢC PHÉP nằm ở đây.")
    if missing:
        findings.append(f"{len(missing)} dòng biến mất khỏi bản gộp mới")
        print(f"  !! {len(missing)} dòng BIẾN MẤT. Hoá đơn không được phép mất dòng.")
    if rewritten_outside_edge:
        findings.append(f"{len(rewritten_outside_edge)} ngày bị viết lại NGOÀI ngày cuối: "
                         f"{', '.join(rewritten_outside_edge)}")
        print(f"  !! Bị viết lại ở {len(rewritten_outside_edge)} ngày KHÁC ngày cuối: "
              f"{', '.join(rewritten_outside_edge)}")
        print("     Đây KHÁC với việc chốt muộn ngày cuối. Phải xem lại trước khi gửi.")
    elif rewritten:
        print(f"  ĐẠT: {len(rewritten)} dòng viết lại đều nằm đúng ngày cuối, "
              f"{len(shared) - len(rewritten)} dòng khớp tuyệt đối.")
    else:
        print(f"  ĐẠT: không dòng nào bị viết lại.")

    for label, p in (("trước", prev), ("mới  ", latest)):
        rows = read_merged(p).values()
        usd = sum(Decimal(r["cost_usd"]) for r in rows)
        tok = sum(int(r["quantity"]) for r in rows)
        print(f"  {label}: {len(list(rows)):5d} dòng | ${usd:>10,.2f} | {tok:>15,} token")


# ---------------------------------------------------------------- phần 3


def monitoring_day_range(folder: Path) -> tuple[set[date], int]:
    """Tập ngày (giờ VN) và số dòng của một đợt kéo. Đọc cột ts_ict.

    Dùng csv.reader + CHỈ SỐ CỘT chứ không DictReader: mỗi đợt kéo nặng ~340 MB
    và DictReader dựng một dict cho từng dòng - chi phí đó không mua thêm gì khi
    ta chỉ cần đúng một cột. Vẫn phải đi qua csv chứ không cắt chuỗi bằng tay,
    vì hai cột cuối là JSON có chứa dấu phẩy.

    Chỉ số cột đọc TỪ HEADER của chính file, không ghim cứng: thứ tự cột do
    scripts/pull_monitoring.py quyết định và nó có quyền đổi.
    """
    days, row_count = set(), 0
    for f in sorted(folder.glob("*.csv")):
        if f.name.startswith("_"):          # _tat-ca.csv là bản gộp của chính đợt đó
            continue
        with f.open(encoding="utf-8", newline="") as h:
            reader = csv.reader(h)
            try:
                header = next(reader)
            except StopIteration:            # file rỗng - đợt kéo đang chạy dở
                continue
            if "ts_ict" not in header:
                findings.append(f"{f.relative_to(ROOT).as_posix()} không có cột ts_ict")
                continue
            i = header.index("ts_ict")
            for row in reader:
                if len(row) <= i or len(row[i]) < 10:
                    continue
                try:
                    days.add(date.fromisoformat(row[i][:10]))
                except ValueError:
                    # Dòng cụt: đợt kéo đang chạy thì file cuối bị đọc giữa chừng.
                    # Bỏ đúng dòng đó, đừng bỏ cả file.
                    continue
                row_count += 1
    return days, row_count


def part_3_monitoring() -> None:
    print_heading(3, "Cloud Monitoring — các đợt kéo")
    batches = sorted(p for p in MONITOR_RAW.iterdir() if p.is_dir()) if MONITOR_RAW.exists() else []
    if not batches:
        print(f"  Không có đợt kéo nào trong {MONITOR_RAW}.")
        findings.append("Không có đợt kéo Cloud Monitoring nào")
        return

    all_days: set[date] = set()
    print(f"  {'đợt kéo':22s} {'file':>5s} {'dòng':>10s}  dải ngày (giờ VN)")
    for d in batches:
        days, row_count = monitoring_day_range(d)
        all_days |= days
        file_count = len([f for f in d.glob("*.csv") if not f.name.startswith("_")])
        span = f"{min(days):%Y-%m-%d} .. {max(days):%Y-%m-%d}" if days else "(rỗng)"
        print(f"  {d.name:22s} {file_count:5d} {row_count:10,d}  {span}")

    if not all_days:
        return
    start, end = min(all_days), max(all_days)
    missing_days = []
    x = start
    while x <= end:
        if x not in all_days:
            missing_days.append(x)
        x += timedelta(days=1)
    print(f"\n  HỢP NHẤT mọi đợt: {start:%Y-%m-%d} .. {end:%Y-%m-%d} "
          f"({(end - start).days + 1} ngày, có dữ liệu {len(all_days)})")
    if missing_days:
        segments = collapse_ranges(missing_days)
        print(f"  Trống {len(missing_days)} ngày giữa dải: {', '.join(segments[:8])}"
              f"{' …' if len(segments) > 8 else ''}")
        cross_check_billing(missing_days)
    print("\n  Vì sao phải giữ MỌI đợt kéo: cửa sổ lưu giữ của Google trượt nhanh —")
    print("  đo 06/08 được 196 ngày, đo 13/08 chỉ còn 112. Dữ liệu rơi khỏi cửa sổ")
    print("  chỉ còn tồn tại trong đợt kéo cũ trên đĩa. Xoá đợt cũ là mất vĩnh viễn.")


def cross_check_billing(missing_days: list[date]) -> None:
    """Ngày Monitoring trống MÀ hoá đơn có số = mất dữ liệu, không phải nghỉ.

    Đây là phép phân biệt quan trọng nhất của phần 3. Một dải ngày trống trông
    y hệt nhau ở hai nguyên nhân hoàn toàn khác:

        agent không chạy   -> không nguồn nào có số, KHÔNG mất gì
        rơi khỏi cửa sổ    -> hoá đơn VẪN CÓ số, Monitoring thì mất VĨNH VIỄN

    Hoá đơn giữ lịch sử không giới hạn còn Monitoring thì không, nên hoá đơn là
    nhân chứng dùng được. Thiếu phép đối chiếu này thì người nhận nhìn một lỗ
    hổng mà không biết nó có đáng lo hay không.
    """
    snapshots = sorted(BILLING_MERGED.glob("billing_*.csv"))
    if not snapshots:
        return
    missing_set = set(d.isoformat() for d in missing_days)
    rows_by_project = collections.Counter()
    days_with_billing = set()
    with snapshots[-1].open(encoding="utf-8") as h:
        for r in csv.DictReader(h):
            if r["day"] in missing_set:
                rows_by_project[r["project"]] += 1
                days_with_billing.add(r["day"])
    if not days_with_billing:
        print("  Đối chiếu hoá đơn: những ngày đó hoá đơn CŨNG không có số —")
        print("  agent không chạy, không mất gì.")
        return
    findings.append(
        f"Cloud Monitoring mất hẳn {len(days_with_billing)} ngày mà hoá đơn vẫn có số "
        f"({min(days_with_billing)}..{max(days_with_billing)}) — đã rơi khỏi cửa sổ lưu giữ")
    print(f"  !! Đối chiếu hoá đơn: {len(days_with_billing)}/{len(missing_days)} ngày trống đó hoá đơn "
          f"VẪN CÓ số ({sum(rows_by_project.values())} dòng):")
    for p, n in rows_by_project.most_common():
        print(f"       {p:26s} {n:4d} dòng")
    print("     ⇒ Đây là MẤT DỮ LIỆU, không phải agent nghỉ. Monitoring đã rơi khỏi")
    print("       cửa sổ lưu giữ của Google và không kéo lại được nữa. Khoảng này")
    print("       chỉ còn chiều token/tiền của hoá đơn, không còn chiều lượt gọi,")
    print("       mã lỗi và độ trễ.")


# ---------------------------------------------------------------- phần 4


def part_4_catalog() -> None:
    print_heading(4, "Danh mục bàn giao")
    groups = [
        ("hoá đơn thô (7 file tải tay)", sorted(BILLING_RAW.glob("*GMSSub*.csv"))),
        ("hoá đơn đã gộp", sorted(BILLING_MERGED.glob("billing_*.csv"))[-1:]),
        ("Cloud Monitoring thô",
         sorted(p for p in MONITOR_RAW.iterdir() if p.is_dir()) if MONITOR_RAW.exists() else []),
        ("phân bố độ trễ (thô + đã gộp theo ngày)",
         (sorted(p for p in LATENCY.iterdir() if p.is_dir()) if LATENCY.exists() else [])
         + sorted(LATENCY.glob("latency-daily.csv"))),
        ("Cloud Monitoring đã gộp",
         sorted(p for p in MONITOR_MERGED.iterdir() if p.is_dir()) if MONITOR_MERGED.exists() else []),
    ]
    total = 0
    for name, items in groups:
        print(f"\n  {name}")
        if not items:
            print("    (không có)")
            continue
        for p in items:
            if p.is_dir():
                size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                n = len([f for f in p.rglob("*") if f.is_file()])
                print(f"    {p.relative_to(ROOT).as_posix():58s} {short_size(size):>10s}  {n} file")
            else:
                size = p.stat().st_size
                modified = datetime.fromtimestamp(p.stat().st_mtime)
                print(f"    {p.relative_to(ROOT).as_posix():58s} {short_size(size):>10s}  "
                      f"sửa {modified:%d/%m %H:%M}")
            total += size
    print(f"\n  Tổng: {short_size(total)}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 76)
    print(f"SOÁT DỮ LIỆU VỪA CÀO — {date.today():%d/%m/%Y}")
    print("=" * 76)

    part_1_raw_billing()
    part_2_invariants()
    part_3_monitoring()
    part_4_catalog()

    print(f"\n{'=' * 76}")
    if findings:
        print(f"KẾT: {len(findings)} điểm cần biết trước khi gửi đi —")
        for i, v in enumerate(findings, 1):
            print(f"  {i}. {v}")
    else:
        print("KẾT: không phát hiện gì đáng dừng.")
    print("=" * 76)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
