"""Nạp hoá đơn Google vào fact_billing_daily - chỉ đọc file, không gọi mạng.

QUY TẮC ÁP DỤNG (docs/plan-xay-dung-database-2026-08-07.md mục 4.6)
-------------------------------------------------------------------
Quy tắc 1  Token và tiền luôn lấy từ billing. Đây là nguồn chân lý về tiền.
Quy tắc 4  Billing tách 2 SKU: input riêng, cached riêng. Không cộng sẵn.
Quy tắc 8  Thứ tự phân loại BẮT BUỘC: cached -> output -> input.

NGÀY: COI LÀ GIỜ VIỆT NAM (chốt 14/08)
--------------------------------------
Cột `day` chép NGUYÊN cột `Date` của Google. Google cắt ngày theo múi Thái Bình
Dương (đã chứng minh: 284/316 ngày khớp monitoring khi giả định Pacific, so với
34/294 nếu giả định UTC - docs/mui-gio-2026-08-08.md mục M1).

Quyết định là KHÔNG quy đổi: coi luôn là giờ Việt Nam, giống mọi cột ngày khác
trong database. Cái phải biết khi đọc: tổng cả kỳ tuyệt đối đúng, nhưng ngày
CUỐI CÙNG luôn hụt và mỗi ngày lẫn khoảng 15 giờ của ngày kề bên. Đủ để theo xu
hướng, không đủ để đối chiếu một ngày lẻ với nguồn khác.
"""

from __future__ import annotations

import argparse
import collections
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import connect  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _latest_billing() -> Path:
    """File gộp mới nhất do scripts/merge_billing.py sinh ra."""
    folder = ROOT / "data" / "da_xu_ly" / "billing"
    candidates = sorted(folder.glob("billing_*.csv"))
    if not candidates:
        raise SystemExit(f"Khong co file gop nao trong {folder}."
                         f" Chay scripts/merge_billing.py truoc.")
    return candidates[-1]


BILLING = _latest_billing()

# KHÔNG còn số mong đợi ghim cứng (270.9517 / 2259). Hai số đó đúng cho đợt dữ
# liệu 05/08 và làm script DỪNG mỗi khi có hoá đơn mới - tức nó chặn đúng việc
# nó phải bảo vệ. Nay số mong đợi lấy từ CHÍNH FILE NGUỒN, nên phép kiểm vẫn bắt
# được dòng rơi rớt giữa file và database mà không lỗi thời.


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=connect.DEFAULT_DSN,
                   help="Duong dan .sqlite, hoac chuoi ket noi PostgreSQL")
    p.add_argument("--file", default=str(BILLING))
    p.add_argument("--rebuild", action="store_true",
                   help="Xoa sach va dung lai schema + danh muc truoc khi nap")
    args = p.parse_args()

    if args.rebuild:
        cn, ph = connect.rebuild(args.db)
        print(f"Da dung lai schema + danh muc tren {args.db}")
    else:
        cn, ph = connect.open_db(args.db)

    models = connect.model_lookup(cn)
    agents = connect.agent_lookup(cn)
    metrics = connect.metric_lookup(cn)

    with open(args.file, encoding="utf-8-sig") as h:
        rows = list(csv.DictReader(h))

    records = []
    no_model = collections.Counter()
    no_kind = collections.Counter()
    no_agent = collections.Counter()
    for r in rows:
        # `kind` giờ tra từ dim_metric_alias thay vì regex trên sku_name. Bảng đó
        # phân loại theo `description` chính chủ của Cloud Billing Catalog, nên
        # một SKU lạ sẽ DỪNG HẲN ở đây chứ không âm thầm rơi ra ngoài.
        _, kind = metrics.get(("billing_sku", r["sku_id"]), (None, None))
        if kind is None:
            no_kind[r["sku_id"]] += 1
            continue
        model_id = models.get(("billing_sku", r["sku_id"]))
        if model_id is None:
            no_model[r["sku_id"]] += 1
        agent_id = agents.get(r["project"])
        if agent_id is None:
            no_agent[r["project"]] += 1
        records.append((r["day"], agent_id, r["project"], r["sku_id"], r["sku_name"],
                        model_id, kind, int(float(r["quantity"])),
                        float(r["cost_usd"])))

    # Một SKU không tra ra model nghĩa là danh mục đã cũ so với hoá đơn. Dừng
    # hẳn: nạp tiếp sẽ cho ra một bảng có dòng model_id NULL trong im lặng, và
    # mọi biểu đồ "chi phí theo model" sau đó đều thiếu tiền mà không báo gì.
    if no_model or no_kind or no_agent:
        raise SystemExit(
            "Chua co trong danh muc - chay lai python db/gen_catalog.py:\n"
            f"  khong ra model: {dict(no_model)}\n"
            f"  khong ra kind : {dict(no_kind)}\n"
            f"  project la    : {dict(no_agent)}"
        )

    cur = cn.cursor()
    cur.execute("DELETE FROM fact_billing_daily")
    cur.executemany(
        f"INSERT INTO fact_billing_daily (day, agent_id, project, sku_id, sku_name,"
        f" model_id, kind, quantity, cost_usd) VALUES ({','.join([ph] * 9)})",
        records)
    cn.commit()

    cur.execute("SELECT COUNT(*), SUM(cost_usd) FROM fact_billing_daily")
    n, total = cur.fetchone()
    cur.execute("SELECT kind, COUNT(*) FROM fact_billing_daily GROUP BY kind ORDER BY kind")
    by_kind = cur.fetchall()

    print(f"  nguon: {Path(args.file).name}")
    print(f"  {n} dong | ${float(total):.4f}")
    print(f"  theo kind: {dict(by_kind)}")

    # Số mong đợi SUY TỪ FILE NGUỒN ở mỗi lần chạy, không ghim.
    src_rows = len(records)
    src_total = sum(float(r["cost_usd"]) for r in rows)

    errors = []
    if n != src_rows:
        errors.append(f"so dong {n} != {src_rows} dong dung tu file nguon")
    if abs(float(total) - src_total) > 0.0001:
        errors.append(f"tong ${float(total):.6f} != ${src_total:.6f} trong file nguon")
    if errors:
        raise SystemExit("NGHIEM THU KHONG DAT: " + " | ".join(errors))
    print("  NGHIEM THU DAT (doi chieu voi chinh file nguon)")


if __name__ == "__main__":
    main()
