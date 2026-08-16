"""Tính lại các kết luận trong van-de-du-lieu.md TỪ DỮ LIỆU RAW.

Lý do tồn tại: nhiều mục trong tài liệu trích số từ file thống kê — hoặc do ứng
dụng cộng sẵn, hoặc do chính script của ta nối ra. Cả hai đều có thể tự sinh ra
vấn đề không có thật (mục A7 là ví dụ đã xảy ra).

Script này bỏ qua mọi file thống kê, chỉ đọc:

  data/ctda/db-token_usage-raw.json     7.924 bản ghi gốc, từng lượt gọi
  data/ctda/users-list.json             890 tài khoản (JSON, KHÔNG dùng users.csv)
  data/ctda/units.json                  108 đơn vị
  data/ctda/db-collections.json         mục lục database

rồi so kết quả với con số tài liệu đang khai. Mỗi phép kiểm in ra một trong ba:

  ĐỨNG VỮNG   raw cho ra đúng con số tài liệu khai  -> giữ trong van-de-du-lieu
  LỆCH        raw cho ra số khác                    -> phải sửa tài liệu
  KHÔNG KIỂM  raw không có đủ dữ liệu để tính lại   -> ghi rõ giới hạn này

Chỉ đọc, không ghi gì vào data/.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# Con so tai lieu dang khai, de doi chieu. Sua o day neu tai lieu doi.
KHAI = {
    "B2_dinh_dang": {8: 6871, 14: 542, 16: 511},
    "B3_system_luot": 6986,
    "B3_system_token": 40849145,
    "B3_tra_ra_id": 215,
    "B3_tra_ra_name": 49,
    "B3_khong_tra_ra": 674,
    "B4_khong_xac_dinh_luot": 7660,
    "B4_khong_xac_dinh_token": 43423705,
    "B5_so_dong_lech": 81,
    "B5_tong_lech": 162,
    "B7_catalog_users": 891,
    "B7_file_users": 890,
    "tong_luot": 7924,
    "tong_token": 44692501,
}

ket_qua: list[tuple[str, str, str]] = []


def doc(ten: str):
    """utf-8-sig vi mot nua so file mang BOM, mot nua khong."""
    return json.loads((DATA / ten).read_text(encoding="utf-8-sig"))


def ghi(ma: str, trang_thai: str, chi_tiet: str) -> None:
    ket_qua.append((ma, trang_thai, chi_tiet))
    print(f"  [{trang_thai:11}] {ma:28} {chi_tiet}")


def so(x) -> float:
    """TLA HĐ lưu tiền kiểu chuỗi, CTDA kiểu số thực. Ép về một kiểu."""
    if x is None or x == "":
        return 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    raw = doc("ctda/db-token_usage-raw.json")
    users = doc("ctda/users-list.json")
    units = {u["id"]: u for u in doc("ctda/units.json")["data"]}
    catalog = {c["name"]: c for c in doc("ctda/db-collections.json")["collections"]}

    tong_token = sum(so(r.get("total_tokens")) for r in raw)

    print("=" * 78)
    print("KIEM LAI TU RAW  —  CTDA (Tro ly ao Ralli)")
    print("=" * 78)
    print(f"  Doc: {len(raw):,} ban ghi tho / {len(users):,} tai khoan / {len(units):,} don vi")
    print()

    # ---- tong ----
    ghi("tong_luot",
        "DUNG VUNG" if len(raw) == KHAI["tong_luot"] else "LECH",
        f"raw={len(raw):,}  tai lieu={KHAI['tong_luot']:,}")
    ghi("tong_token",
        "DUNG VUNG" if tong_token == KHAI["tong_token"] else "LECH",
        f"raw={tong_token:,.0f}  tai lieu={KHAI['tong_token']:,}")

    # ---- B2: ba dinh dang ban ghi ----
    dd = Counter(len(r) for r in raw)
    ghi("B2_dinh_dang",
        "DUNG VUNG" if dict(dd) == KHAI["B2_dinh_dang"] else "LECH",
        f"raw={dict(sorted(dd.items()))}  tai lieu={KHAI['B2_dinh_dang']}")

    # ---- B3: phan loai user_id, doi chieu voi users-list.json (KHONG dung users.csv) ----
    theo_id = {u["id"] for u in users}
    theo_ten = {u["username"] for u in users}
    nhom: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for r in raw:
        uid = r.get("user_id")
        key = str(uid) if uid is not None else "(null)"
        if key == "system":
            lab = "system"
        elif key in theo_id:
            lab = "tra_ra_id"
        elif key in theo_ten:
            lab = "tra_ra_name"
        else:
            lab = "khong_tra_ra"
        nhom[lab][0] += 1
        nhom[lab][1] += so(r.get("total_tokens"))

    for lab, ma in [("system", "B3_system_luot"), ("tra_ra_id", "B3_tra_ra_id"),
                    ("tra_ra_name", "B3_tra_ra_name"), ("khong_tra_ra", "B3_khong_tra_ra")]:
        thuc = int(nhom[lab][0])
        ghi(ma, "DUNG VUNG" if thuc == KHAI[ma] else "LECH",
            f"raw={thuc:,}  tai lieu={KHAI[ma]:,}")
    ghi("B3_system_token",
        "DUNG VUNG" if int(nhom["system"][1]) == KHAI["B3_system_token"] else "LECH",
        f"raw={nhom['system'][1]:,.0f}  tai lieu={KHAI['B3_system_token']:,}")

    # ---- B4: quy don vi TU RAW, khong dung by-unit-2026.csv ----
    # Duong noi: raw.user_id -> users-list.id -> unit / unit_id -> units.json
    u_theo_id = {u["id"]: u for u in users}
    u_theo_ten = {u["username"]: u for u in users}
    co_dv = [0, 0.0]
    khong_dv = [0, 0.0]
    ly_do: Counter = Counter()
    for r in raw:
        uid = r.get("user_id")
        key = str(uid) if uid is not None else ""
        nd = u_theo_id.get(key) or u_theo_ten.get(key)
        tok = so(r.get("total_tokens"))
        if nd is None:
            khong_dv[0] += 1
            khong_dv[1] += tok
            ly_do["khong tim thay tai khoan"] += 1
            continue
        # unit_id co the rong, con truong 'unit' luu TEN don vi
        dv = (nd.get("unit_id") or "").strip()
        ten_dv = (nd.get("unit") or "").strip()
        if dv in units or ten_dv:
            co_dv[0] += 1
            co_dv[1] += tok
        else:
            khong_dv[0] += 1
            khong_dv[1] += tok
            ly_do["tai khoan khong gan don vi"] += 1

    ghi("B4_khong_xac_dinh_luot",
        "DUNG VUNG" if khong_dv[0] == KHAI["B4_khong_xac_dinh_luot"] else "LECH",
        f"raw={khong_dv[0]:,}  tai lieu={KHAI['B4_khong_xac_dinh_luot']:,}")
    ghi("B4_khong_xac_dinh_token",
        "DUNG VUNG" if int(khong_dv[1]) == KHAI["B4_khong_xac_dinh_token"] else "LECH",
        f"raw={khong_dv[1]:,.0f}  tai lieu={KHAI['B4_khong_xac_dinh_token']:,}")
    print(f"       ly do khong quy duoc: {dict(ly_do)}")
    print(f"       quy duoc: {co_dv[0]:,} luot / {co_dv[1]:,.0f} token")

    # ---- B5: lech 162 token ----
    dong_lech = [r for r in raw
                 if so(r.get("total_tokens"))
                 != so(r.get("prompt_tokens")) + so(r.get("completion_tokens"))]
    tong_lech = sum(so(r.get("total_tokens"))
                    - so(r.get("prompt_tokens")) - so(r.get("completion_tokens"))
                    for r in dong_lech)
    ghi("B5_so_dong_lech",
        "DUNG VUNG" if len(dong_lech) == KHAI["B5_so_dong_lech"] else "LECH",
        f"raw={len(dong_lech)}  tai lieu={KHAI['B5_so_dong_lech']}")
    ghi("B5_tong_lech",
        "DUNG VUNG" if int(tong_lech) == KHAI["B5_tong_lech"] else "LECH",
        f"raw={tong_lech:,.0f}  tai lieu={KHAI['B5_tong_lech']}")

    # ---- B7: thieu 1 nguoi dung ----
    ghi("B7_catalog_users",
        "DUNG VUNG" if catalog["users"]["count"] == KHAI["B7_catalog_users"] else "LECH",
        f"catalog={catalog['users']['count']:,}  file={len(users):,}  "
        f"thieu={catalog['users']['count'] - len(users)}")

    # ---- TLA HD: co raw khong? ----
    print()
    print("=" * 78)
    print("TLA HOP DONG")
    print("=" * 78)
    co_raw = sorted(p.name for p in (DATA / "tla-hd").glob("*.json"))
    print(f"  File JSON co: {', '.join(co_raw)}")
    print("  -> KHONG co file nao chua tung luot goi. Moi so deu la thong ke ung dung cong san.")
    ghi("A3_A4_A6_tu_raw", "KHONG KIEM", "TLA HD khong co du lieu tung luot goi")

    # ---- tong ket ----
    print()
    print("=" * 78)
    dem = Counter(t for _, t, _ in ket_qua)
    print(f"TONG KET: {dict(dem)}")
    lech = [m for m, t, _ in ket_qua if t == "LECH"]
    if lech:
        print(f"  CAN SUA TAI LIEU: {', '.join(lech)}")
    else:
        print("  Moi phep kiem tinh lai duoc tu raw deu khop.")


if __name__ == "__main__":
    main()
