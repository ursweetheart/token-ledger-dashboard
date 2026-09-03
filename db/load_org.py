"""Nạp dim_unit, account, dim_user, dim_function - bước (2)(3)(4)(5) của Ngày 2.

Chỉ đọc file, không gọi mạng.

THỨ TỰ BẮT BUỘC (xem docs/quyet-dinh-ngay-2-2026-08-09.md)
---------------------------------------------------------
    (2) dim_unit    Ralli + TLA HĐ + 6 kỹ thuật + 2 'Chưa quy được'
    (3) dim_user    từ danh bạ                         found_in='directory'
    (4) quét nhật ký bổ sung user_id không có trong danh bạ  found_in='log'
   (3b) account     một mã số cho mỗi tài khoản, kèm đơn vị chính thức
    (5) dim_function

Đảo (3)(4) với bước nạp fact_call thì fact_call sẽ có khoá ngoại trỏ vào chỗ
trống.

BA CÁI BẪY
----------
BOM      db-token_usage-raw.json có BOM UTF-8. Mở bằng encoding='utf-8' sẽ ném
         JSONDecodeError. Phải dùng 'utf-8-sig'.
THỨ TỰ   dim_unit.parent_id trỏ vào chính dim_unit. Với PRAGMA foreign_keys=ON,
         nạp con trước cha sẽ HỎNG. Phải nạp theo `level` tăng dần.
THIẾU    6/108 đơn vị Ralli KHÔNG có trường `ancestors`. Dùng x['ancestors'] sẽ
         ném KeyError. Đường dẫn tính bằng cách lần theo parent_id, rồi ĐỐI CHIẾU
         với `ancestors` ở 102 đơn vị còn lại - nếu lệch thì một trong hai sai.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import connect  # noqa: E402
import logs  # noqa: E402

log = logs.get_logger("load_org")

ROOT = Path(__file__).resolve().parents[1]


def _latest(parent: Path, *required: str) -> Path:
    """Đợt thu thập mới nhất CÓ ĐỦ các file cần. Tên thư mục là ngày nên sắp
    xếp chuỗi là đủ.

    KHÔNG lấy thẳng thư mục cuối. Nhiều script pull_* cùng ghi vào cây này,
    mỗi cái theo NGÀY KÉO của riêng nó, nên thư mục mới nhất hoàn toàn có thể
    chỉ chứa đúng một file của một script (pull_hd_usage.py là ví dụ). Lấy bừa
    thư mục đó thì hỏng giữa khâu nạp bằng FileNotFoundError - đúng chỗ khó
    đoán nhất. Đòi đủ file thì nó lùi về đợt kéo đầy đủ gần nhất, và nếu không
    có đợt nào đủ thì nói thẳng thiếu file gì.
    """
    children = sorted((p for p in parent.glob("*") if p.is_dir()), reverse=True)
    if not children:
        raise SystemExit(f"no collection batch in {parent}."
                         f" Chay scripts/pull_web_apps.py truoc.")
    for p in children:
        if all((p / f).exists() for f in required):
            return p
    missing = [f for f in required if not (children[0] / f).exists()]
    raise SystemExit(
        f"no batch in {parent} has every required file."
        f" Dot moi nhat ({children[0].name}) thieu: {', '.join(missing)}."
        f" Chay scripts/pull_web_apps.py truoc.")


# Nguồn cũ là data/ctda và data/tla-hd - bản cào TAY ngày 05/08, không cập nhật
# nữa. Nay đọc đợt kéo mới nhất do scripts/pull_web_apps.py sinh ra.
# Liệt kê tường minh từng file đọc bên dưới: thêm chỗ đọc mới mà quên thêm vào
# đây thì `_latest` không bảo vệ được nữa.
RALLI_DIR = _latest(ROOT / "data" / "raw_web" / "ralli",
                    "units.json", "users-list.json", "db-token_usage-raw.json")
TLA_DIR = _latest(ROOT / "data" / "raw_web" / "tla-hd",
                  "units-tree.json", "units-members.json",
                  "token-usage-year.json", "token-usage-filter-options.json")
# Do scripts/pull_hd_usage.py sinh ra. Nó ghi vào thư mục theo NGÀY KÉO của
# riêng nó, nên thường KHÁC thư mục đợt kéo đầy đủ ở trên - đó là lý do phải
# tra bằng tên file chứ không lấy bừa thư mục mới nhất.
HD_USAGE_DIR = _latest(ROOT / "data" / "raw_web" / "tla-hd",
                       "usage-day-user-model.json")

RALLI, TLA_HD = 8, 5
SINGLE_USER_AGENTS = (1, 2, 3, 4, 6, 7)      # quyết định A1

# Nhãn tiếng Việt đã biết, phát hiện khi đối chiếu giao diện web 07/08
FUNCTION_LABELS = {"analyze": "Phân tích hợp đồng", "chat": "Hỏi đáp AI"}

# ─── Tài khoản DÙNG CHUNG ────────────────────────────────────────────────
# Không đại diện cho một người. Vẫn nạp đủ token và tiền - lưu lượng của chúng
# là lưu lượng thật - nhưng phải loại khỏi chỉ tiêu TỶ LỆ ÁP DỤNG, nơi mỗi dòng
# cần là một người có thể chọn dùng hay không dùng.
#
# Quy tắc để ở KHÂU NẠP chứ không ở tầng API, và kết quả ghi thành cột trong
# database. Nhờ vậy soi lại được bằng một câu SELECT, thay vì phải đọc code của
# một endpoint để biết con số trên màn hình đã loại những ai.
#
# QUY TẮC CHÍNH LÀ SUY RA ĐƯỢC, KHÔNG GÕ TAY.
#
# Một người được tổ chức cấp quyền thì phải có mặt trong DANH BẠ của ít nhất
# một app (`found_in = 'directory'`). Tài khoản chỉ xuất hiện trong nhật ký gọi
# mà chưa từng có trong danh bạ nào thì không phải một nhân viên - nó được tạo
# thẳng trong app, hoặc đã bị xoá khỏi danh bạ.
#
# Đã soát toàn bộ 937 tài khoản ngày 15/08: đúng 7 cái chỉ-trong-log, và cả 7
# đều không phải người - system, test1..test4, guest, 'nghiệp vụ bh1'. KHÔNG có
# ca nào nhận nhầm. Nhờ vậy tài khoản thử tạo thêm sau này tự vào nhóm dùng
# chung mà không ai phải sửa file này.
#
# NGOẠI LỆ dưới đây là phần KHÔNG suy ra được: tài khoản CÓ trong danh bạ thật -
# tức tổ chức đã chính thức cấp - nhưng không đại diện cho một người. Chỉ con
# người biết điều đó, nên nó phải là danh sách, và phải kèm lý do.
# Cách phát hiện thêm: `scripts/audit_db.py` kêu lên khi có tài khoản phát sinh
# request mà không họ tên lẫn email.
SHARED_IN_DIRECTORY = {
    # 1.796 lượt / 34,9 triệu token, dùng cả Ralli lẫn TLA HĐ. Họ tên khai là
    # "Quản trị viên" - một chức danh, không phải tên người. Không có email.
    "admin": "tai khoan quan tri dung chung",
}


# Thứ tự cấp bậc do hai app tự khai. Nhỏ hơn = cao hơn. Dùng để chọn vai trò
# khi một người có vai trò khác nhau ở hai app. Vai trò lạ xuống cuối, không
# làm hỏng phép chọn.
ROLE_RANK = {"ADMIN": 0, "COMPANY_ADMIN": 1, "UNIT_LEAD": 2,
             "DT": 3, "PKH": 4, "MEMBER": 5}


def is_shared(username: str, in_directory: bool) -> int:
    """1 nếu tài khoản không đại diện cho một người cụ thể.

    `username` đã qua norm(). `in_directory` = có mặt trong danh bạ app nào đó.
    """
    if username in SHARED_IN_DIRECTORY:
        return 1
    return 0 if in_directory else 1

# KHÔNG ghim số mong đợi nữa. Trước đây là DV_MONG_DOI=136 / HAM_MONG_DOI=8 -
# đúng cho đợt dữ liệu 05/08 và sai ngay khi tổ chức đổi (Ralli vừa bỏ 6 đơn vị:
# 108 -> 102). Ghim số biến phép nghiệm thu thành cái chặn việc, trong khi thứ
# nó phải bắt là "có dòng nào rơi rớt giữa file nguồn và database không".
# Nay số mong đợi được SUY TỪ CHÍNH FILE NGUỒN ở mỗi lần chạy.


def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def walk_up(nid: str, parent: dict[str, str], name: dict[str, str]) -> list[str]:
    """Lần theo parent_id về tới gốc. Trả danh sách tên TỪ GỐC xuống, chưa kể chính nó."""
    path: list[str] = []
    seen = {nid}
    cur = parent.get(nid) or None
    while cur:
        if cur in seen:                       # vòng lặp trong dữ liệu
            raise SystemExit(f"Cay don vi co vong lap tai {cur}")
        if cur not in name:
            raise SystemExit(f"unit {nid} points at a parent {cur} that does not exist")
        seen.add(cur)
        path.append(name[cur])
        cur = parent.get(cur) or None
    return list(reversed(path))


# Bốn phòng ban mà HAI app gọi bằng hai tên. Trái: tên trong cây Trợ Lý Ảo Hợp
# Đồng. Phải: tên trong cây Trợ lý ảo Ralli, và đó là bản CHUẨN.
#
# Vì sao Ralli làm chuẩn: cây của nó mô hình hoá CẢ công ty - một gốc 'Toàn công
# ty', 102 đơn vị, 892/937 tài khoản. Cây Hợp Đồng chỉ 20 đơn vị với BỐN gốc
# rời, tức một phần chứ không phải một cây đầy đủ.
#
# Danh sách này gõ tay vì không suy ra được: 'Phòng BH1' và 'PBH1' không có quy
# tắc chuẩn hoá nào nối được, cũng như 'TT C4LED' với 'C4LED'. Người dùng xác
# nhận đủ bốn cặp ngày 20/08/2026.
#
# ĐÃ ĐO trước khi chốt - mỗi cặp đều có một bên nhiều tài khoản, bên kia nhiều
# token, nên bỏ gộp là chẻ đôi cả hai chỉ tiêu:
#     TT C4LED  3 tk / 1.222.467 tok   <->  C4LED 13 tk /         0 tok
#     Phòng BH1 7 tk /         0 tok   <->  PBH1  30 tk /   105.187 tok
#     Phòng BH2 9 tk /         0 tok   <->  PBH2  12 tk /    17.718 tok
#     Phòng BH3 9 tk /         0 tok   <->  PBH3   4 tk / 1.138.839 tok
#
# Trước 20/08/2026 phép gộp này nằm trong UNIT_ALIASES ở web/js/app.js - một sự
# thật về tổ chức công ty sống trong mã giao diện.
CANONICAL_UNIT_PAIRS = [
    ("TT C4LED", "C4LED"),
    ("Phòng BH1", "PBH1"),
    ("Phòng BH2", "PBH2"),
    ("Phòng BH3", "PBH3"),
]

# Hai cấp gom thuần tuý trong cây Trợ lý ảo Ralli. Báo cáo bắt đầu từ BÊN DƯỚI
# chúng: mọi phòng ban đều nằm dưới cả hai, nên để chúng làm cấp 1 thì người xem
# phải bung hai lần mới thấy được thứ đầu tiên phân biệt được với nhau.
#
# Đây là QUY ƯỚC TRÌNH BÀY, không phải thuộc tính của tổ chức - xem ghi chú ở
# db/migrations/sql/001_baseline.sql:141. Trước 20/08/2026 nó sống trong
# web/js/app.js dưới dạng hai mã
# gõ cứng `unitChildren("company")` và `unitChildren("rd-corp")`.
#
# `Công ty CPBĐ PN Rạng Đông` (cây Hợp Đồng) KHÔNG nằm trong danh sách này dù tên
# nghe tương tự: nó có 2 tài khoản của riêng mình, tức là một hàng có nội dung
# chứ không phải một cấp gom rỗng.
REPORT_AGGREGATE_UNITS = [
    (RALLI, "Toàn công ty"),
    (RALLI, "Tổng công ty Rạng Đông"),
]


def resolve_canonical(rows: list[tuple]) -> dict[str, str]:
    """Tra bốn cặp trong CANONICAL_UNIT_PAIRS thành {unit_id trùng: unit_id chuẩn}.

    rows: (unit_id, agent_id, name, parent_id, level, path, is_technical)

    HỎNG ỒN ÀO khi một vế không tìm thấy hoặc tìm thấy nhiều hơn một. Tên phòng
    ban do hai app tự khai; app đổi nhãn là phép gộp lặng lẽ mất tác dụng, và
    hậu quả - hai hàng thay vì một, mẫu số tỷ lệ áp dụng chẻ đôi - không có gì
    báo ra. Thà dừng khâu nạp còn hơn.
    """
    def find(agent: int, unit_name: str) -> str:
        hit = [r[0] for r in rows
               if r[1] == agent and r[2].strip() == unit_name and not r[6]]
        if len(hit) != 1:
            raise SystemExit(
                f"CANONICAL_UNIT_PAIRS: tim '{unit_name}' trong cay agent"
                f" {agent} ra {len(hit)} ket qua, phai dung 1."
                f" App co the da doi ten don vi - xem lai cap nay.")
        return hit[0]

    return {find(TLA_HD, hd): find(RALLI, ralli)
            for hd, ralli in CANONICAL_UNIT_PAIRS}


def resolve_report_aggregates(rows: list[tuple]) -> list[str]:
    """Tra REPORT_AGGREGATE_UNITS thành danh sách unit_id. Hỏng ồn ào như trên."""
    out = []
    for agent, unit_name in REPORT_AGGREGATE_UNITS:
        hit = [r[0] for r in rows
               if r[1] == agent and r[2].strip() == unit_name and not r[6]]
        if len(hit) != 1:
            raise SystemExit(
                f"REPORT_AGGREGATE_UNITS: tim '{unit_name}' trong cay agent"
                f" {agent} ra {len(hit)} ket qua, phai dung 1."
                f" App co the da doi ten don vi.")
        out.append(hit[0])
    return out


def collect_units() -> list[tuple]:
    """Trả danh sách dòng dim_unit cho cả Ralli lẫn TLA HĐ."""
    rows: list[tuple] = []

    # --- Ralli: cấu trúc phẳng có parent_id ---
    ru = read_json(RALLI_DIR / "units.json")["data"]
    name = {x["id"]: x["name"] for x in ru}
    parent = {x["id"]: (x.get("parent_id") or "") for x in ru}

    path_mismatch = 0
    for x in ru:
        ancestors_walked = walk_up(x["id"], parent, name)
        # Đối chiếu với `ancestors` ở những đơn vị có trường đó
        anc = x.get("ancestors")
        if anc is not None:
            by_anc = [name[a] for a in anc if a in name]
            if by_anc != ancestors_walked:
                path_mismatch += 1
        rows.append((x["id"], RALLI, x["name"], x.get("parent_id") or None,
                     len(ancestors_walked) + 1,
                     " > ".join(ancestors_walked + [x["name"]]), False))
    if path_mismatch:
        raise SystemExit(
            f"parent_id va ancestors cho ra duong dan KHAC NHAU o {path_mismatch}"
            f" don vi - mot trong hai sai, phai lam ro truoc khi nap")

    # --- TLA HĐ: cây lồng nhau ---
    def descend(nodes: list, depth: int, ancestors: list[str]) -> None:
        for n in nodes:
            rows.append((n["id"], TLA_HD, n["name"], n.get("parent_id") or None,
                         depth, " > ".join(ancestors + [n["name"]]), False))
            descend(n.get("children") or [], depth + 1, ancestors + [n["name"]])

    descend(read_json(TLA_DIR / "units-tree.json")["tree"], 1, [])
    return rows


def main() -> None:
    # BẮT BUỘC từ khi báo cáo xung đột in TÊN đơn vị: tên phòng ban có dấu tiếng
    # Việt, còn console Windows mặc định cp1252 sẽ ném UnicodeEncodeError. Lỗi đó
    # xảy ra ở CUỐI bước, sau khi đã làm hết việc, nên rất khó chịu.
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=connect.DEFAULT_DSN)
    args = p.parse_args()

    cn, ph = connect.open_db(args.db)
    cur = cn.cursor()

    agent_name = dict(connect.query(cn, "SELECT agent_id, name FROM dim_agent"))
    # `code` để dựng username của tài khoản dịch vụ: svc.<code> (quyết định A3,
    # chốt 20/08). SUY TỪ dim_agent chứ không gõ tay 6 lần - gõ tay thì ngày
    # thêm agent thứ 9 sẽ quên một chỗ.
    agent_code = dict(connect.query(cn, "SELECT agent_id, code FROM dim_agent"))

    # ================================================== (2) dim_unit
    unit_rows = collect_units()

    # 6 dòng kỹ thuật + 2 dòng 'Chưa quy được'
    for aid in SINGLE_USER_AGENTS:
        unit_rows.append((f"__technical_{aid}__", aid,
                          f"Đơn vị sử dụng {agent_name[aid]}", None, 1,
                          f"Đơn vị sử dụng {agent_name[aid]}", True))
    for aid in (TLA_HD, RALLI):
        unit_rows.append((f"__unattributed_{aid}__", aid, "Chưa quy được",
                          None, 0, "Chưa quy được", True))

    # Thứ tự xoá ngược với thứ tự khoá ngoại: con trước, cha sau.
    #
    # CHÚ Ý (31/08/2026): `fact_call` nay chứa HAI nguồn - `app` và `gateway`.
    # Câu DELETE dưới đây KHÔNG lọc được theo nguồn: khoá ngoại account_id bắt
    # phải dọn sạch bảng con trước khi dựng lại `account`. Nên chạy file này MỘT
    # MÌNH sẽ xoá cả dữ liệu Gateway, và `load_ralli.py` không nạp lại phần đó.
    #
    # `scripts/rebuild_db.py` đã xếp đúng thứ tự (org ở bước 2, gateway ở bước 6)
    # nên đường chính an toàn. Chạy lẻ thì phải chạy lại `db/load_gateway.py`,
    # hoặc gọn hơn là `scripts/refresh_gateway.py`.
    cur.execute("DELETE FROM fact_usage_daily")
    cur.execute("DELETE FROM fact_call")
    cur.execute("DELETE FROM dim_function")
    cur.execute("DELETE FROM dim_user")
    cur.execute("DELETE FROM account")
    cur.execute("DELETE FROM dim_unit")

    # Nạp theo `level` tăng dần: cha phải có trước con, không thì khoá ngoại hỏng
    unit_rows.sort(key=lambda r: r[4])
    cur.executemany(
        f"INSERT INTO dim_unit (unit_id, agent_id, name, parent_id, level, path,"
        f" is_technical) VALUES ({','.join([ph] * 7)})", unit_rows)

    # canonical_unit_id đặt bằng UPDATE SAU khi chèn xong, không đặt trong INSERT.
    # Nó là khoá ngoại TỰ TRỎ, mà vòng chèn ở trên sắp theo `level` tăng dần để
    # cha có trước con. Bản chuẩn không nhất thiết nông hơn bản trùng - PBH1 ở
    # cây Ralli sâu hơn 'Phòng BH1' ở cây Hợp Đồng - nên chèn thẳng sẽ vấp khoá
    # ngoại tuỳ dữ liệu, tức hỏng theo kiểu chỉ xuất hiện ở một số lần chạy.
    canonical = resolve_canonical(unit_rows)
    cur.executemany(
        f"UPDATE dim_unit SET canonical_unit_id = {ph} WHERE unit_id = {ph}",
        [(v, k) for k, v in canonical.items()])
    aggregates = resolve_report_aggregates(unit_rows)
    cur.executemany(
        f"UPDATE dim_unit SET is_report_aggregate = TRUE WHERE unit_id = {ph}",
        [(x,) for x in aggregates])
    log.info("  merged %d units duplicated across the two org trees"
             " | %d aggregate levels, reporting starts below them",
             len(canonical), len(aggregates))

    # ================================================== (3) dim_user từ danh bạ
    # Tuple: (user_id, agent_id, username, full_name, email, unit_id,
    #         is_enabled, created_at, is_technical, found_in, role)
    user_rows: list[tuple] = []
    known_units = {r[0] for r in connect.query(cn, "SELECT unit_id FROM dim_unit")}

    for x in read_json(RALLI_DIR / "users-list.json"):
        unit = x.get("unit_id") or None
        if unit not in known_units:            # 2 người không có đơn vị
            unit = f"__unattributed_{RALLI}__"
        user_rows.append((x["id"], RALLI, x["username"], x.get("full_name"),
                          x.get("email"), unit, x.get("is_active"),
                          x.get("created_at") or None,
                          False, "directory", x.get("role") or None))

    # Nguồn cũ là users-by-unit.csv - file PHÁI SINH, đợt kéo mới không có.
    # Dùng units-members.json (GET /api/units/{id}/members cho từng đơn vị):
    # đây là nguồn DUY NHẤT có email. token-usage/filter-options tuy cũng liệt kê
    # người dùng nhưng không có email, nạp từ đó là mất trường mà không ai báo.
    for block in read_json(TLA_DIR / "units-members.json"):
        raw_unit = block.get("unit_id")
        unit = raw_unit if raw_unit in known_units else f"__unattributed_{TLA_HD}__"
        for r in block.get("members") or []:
            user_rows.append((r["id"], TLA_HD, r["username"],
                              r.get("full_name") or None, r.get("email") or None,
                              unit, None, None, False, "directory",
                              r.get("role") or None))

    # BỔ SUNG người không thuộc đơn vị nào. units-members.json chỉ liệt kê thành
    # viên CỦA MỘT ĐƠN VỊ, nên `admin` (unit_id = null) không xuất hiện ở bất kỳ
    # khối nào: danh bạ 44 người mà chỉ nạp được 43. Đúng người không được phép
    # thiếu - `admin` tạo 46,4% lưu lượng của agent này (1.316/2.834 lượt).
    #
    # Chỉ dùng filter-options để VÁ chỗ thiếu, không dùng thay: nó không có
    # email, nạp từ đó cho tất cả là mất email của 43 người kia mà không ai báo.
    existing = {d[0] for d in user_rows if d[1] == TLA_HD}
    for r in read_json(TLA_DIR / "token-usage-filter-options.json").get("users") or []:
        if r["id"] in existing:
            continue
        raw_unit = r.get("unit_id")
        unit = raw_unit if raw_unit in known_units else f"__unattributed_{TLA_HD}__"
        user_rows.append((r["id"], TLA_HD, r["username"],
                          r.get("full_name") or None, None,
                          unit, None, None, False, "directory", None))

    for aid in SINGLE_USER_AGENTS:
        user_rows.append((f"__technical_{aid}__", aid,
                          f"Người dùng sử dụng {agent_name[aid]}", None, None,
                          f"__technical_{aid}__", None, None, True, "technical", None))

    # ================================================== (4) bổ sung từ nhật ký
    calls = read_json(RALLI_DIR / "db-token_usage-raw.json")
    already = {(d[1], d[0]) for d in user_rows}    # (agent_id, user_id)
    extra: dict[str, str] = {}
    for c in calls:
        uid = c.get("user_id")
        if uid is None or (RALLI, uid) in already:
            continue
        # Chỉ định dạng 3 mới có `username`. Lấy tên thật nếu BẤT KỲ bản ghi nào
        # của user đó có - không được dừng lại ở bản ghi đầu tiên, vì bản ghi đầu
        # rất có thể là định dạng 1 (không có username) và ta sẽ ghi nhầm uid.
        if c.get("username"):
            extra[uid] = c["username"]
        else:
            extra.setdefault(uid, uid)
    # Trong bản ghi cũ, trường `user_id` chứa USERNAME chứ không phải ObjectId.
    # 13/17 'người lạ' thật ra có trong danh bạ, chỉ khác dạng khoá. Gán đúng đơn
    # vị cho họ - VẪN GIỮ RIÊNG hai dòng theo quyết định N7, chỉ điền thêm thuộc
    # tính đã biết chứ không gộp danh tính.
    # Kiểm chứng: 215 (khớp ObjectId) + 49 (khớp username) = 264, đúng bằng con số
    # app tự tính độc lập (7.924 - 7.660).
    unit_by_name = {d[2]: d[5] for d in user_rows
                    if d[1] == RALLI and d[9] == "directory"}
    for uid, display in extra.items():
        user_rows.append((uid, RALLI, display, None, None,
                          unit_by_name.get(uid) or unit_by_name.get(display)
                          or f"__unattributed_{RALLI}__",
                          None, None, False, "log", None))

    # Người dùng TLA HĐ chỉ thấy trong số liệu sử dụng, không có trong danh bạ.
    # Cùng khuôn với Ralli ngay trên: giữ lại với found_in='log' chứ KHÔNG dồn
    # vào 'unattributed'. Dồn vào đó là vứt đi thông tin đang có - ta BIẾT đây
    # là ai, chỉ là họ không (còn) trong danh bạ.
    # Thực tế 14/08: 6 người - test1..test4, Test1 (tài khoản thử) và
    # 'Nghiệp vụ BH1' (không còn user_id, tức đã bị xoá khỏi danh bạ).
    # Nhờ tách riêng found_in mà chỉ tiêu tỷ lệ áp dụng lọc được họ ra, trong
    # khi tổng token vẫn đủ.
    hd_names = {(d[2] or "").strip().lower() for d in user_rows if d[1] == TLA_HD}
    hd_ids = {d[0] for d in user_rows if d[1] == TLA_HD}
    hd_extra: dict[str, str] = {}
    for r in read_json(HD_USAGE_DIR / "usage-day-user-model.json")["rows"]:
        name = (r.get("username") or "").strip()
        if not name or name.lower() in hd_names:
            continue
        # Không có user_id thì lấy chính username làm khoá - đúng cách Ralli đã
        # xử lý cho các bản ghi cũ ghi username vào ô user_id.
        hd_extra[r.get("user_id") or name] = name
    for uid, display in sorted(hd_extra.items()):
        if uid in hd_ids:
            continue
        user_rows.append((uid, TLA_HD, display, None, None,
                          f"__unattributed_{TLA_HD}__", None, None, False, "log", None))

    # ============================================ (3b) bảng `account`
    # Mỗi nguồn trước đây ghi "ai dùng" theo kiểu riêng: Ralli ghi ObjectId của
    # Ralli, TLA HĐ ghi id của TLA HĐ, Google thì không ghi ai cả. Bảng này là
    # chỗ duy nhất để quy ba kiểu đó về một mã số.
    #
    # KHOÁ ĐỐI CHIẾU LÀ TÊN ĐĂNG NHẬP đã LOWER+TRIM. Dùng email thì mất 890 dòng
    # Ralli (không có email); dùng họ tên thì gộp nhầm hai người trùng tên. Tên
    # đăng nhập là thứ duy nhất cả hai app đều có và đều duy nhất trong phạm vi
    # app của nó.
    #
    # ID GÁN THEO THỨ TỰ CHỮ CÁI, không theo thứ tự gặp. Như vậy dựng lại
    # database hai lần từ cùng dữ liệu sẽ ra cùng bộ mã - cần để audit hai lần
    # rebuild từ cùng `data/` cho kết quả ổn định.
    #
    # ĐƠN VỊ CŨNG NẰM Ở ĐÂY (thêm 14/08, đợt rà soát thứ hai)
    # Trước đây đơn vị chỉ nằm ở dim_user. Mà một tài khoản có NHIỀU dòng
    # dim_user, mỗi dòng một đơn vị, nên "người này thuộc đơn vị nào" có hai đáp
    # án - 5/932 tài khoản vấp phải. Nguyên nhân: cùng một tổ chức được mô hình
    # hoá hai lần, TLA HĐ gọi 'Phòng BH1' còn Ralli gọi 'PBH1'.
    # Quy tắc chọn ở hàm `unit_priority` dưới đây; schema gốc và lý do thiết kế
    # nằm trong db/migrations/sql/001_baseline.sql.
    def norm(u: str) -> str:
        return (u or "").strip().lower()

    unit_level = {r[0]: (r[4] or 0) for r in unit_rows}
    unit_name = {r[0]: r[2] for r in unit_rows}

    def is_unattributed(unit: str) -> bool:
        return unit.startswith("__unattributed_")

    def unit_priority(d: tuple) -> tuple:
        """Thứ tự ưu tiên đơn vị của một dòng dim_user. Nhỏ hơn = được chọn."""
        unit = d[5]
        return (1 if is_unattributed(unit) else 0,  # đơn vị thật đi trước chỗ trống
                -unit_level.get(unit, 0),           # sâu nhất đi trước: cụ thể hơn
                d[1],                               # agent_id nhỏ nhất
                unit)                               # chốt bằng thứ tự chữ cái

    # Gom theo tên đăng nhập MỘT LẦN. Bản trước quét lại cả user_rows cho từng
    # tên (932 tên x 957 dòng x 3 lượt) - không sai, chỉ chậm một cách khó thấy.
    by_username: dict[str, list[tuple]] = {}
    for d in user_rows:
        if not d[8]:
            by_username.setdefault(norm(d[2]), []).append(d)

    accounts: list[tuple] = []
    account_id_of: dict[str, int] = {}
    conflicts: list[str] = []
    for i, u in enumerate(sorted(by_username), start=1):
        account_id_of[u] = i
        group = by_username[u]
        # Dòng nào có họ tên / email thì thắng dòng không có: min() trên chuỗi bỏ
        # qua None nên phải lọc trước.
        names = sorted(d[3] for d in group if d[3])
        emails = sorted(d[4] for d in group if d[4])
        chosen = min(group, key=unit_priority)
        # XUNG ĐỘT = hai nguồn cùng NÓI tên đơn vị và nói khác nhau. Một nguồn im
        # lặng ('Chưa quy được') thì không tính là cãi nhau - đó là thiếu tin,
        # không phải mâu thuẫn.
        named = {d[5] for d in group if not is_unattributed(d[5])}
        conflict = 1 if len(named) > 1 else 0
        if conflict:
            # In TÊN đơn vị kèm tên app đã khai, không in unit_id: một ObjectId
            # như '69ee5b13be38bdbf5a8de668' không cho người đọc quyết định được
            # gì, mà cả mục đích của báo cáo này là để người đọc thấy mà phân xử.
            # Bỏ trùng: một app có thể có nhiều dòng dim_user cho cùng tài khoản.
            claims = sorted({(d[1], d[5]) for d in group if not is_unattributed(d[5])})
            conflicts.append(
                f"{u}  " + " | ".join(f"{agent_name[a]}: {unit_name[v]}"
                                      for a, v in claims)
                + f"  -> chon: {unit_name[chosen[5]]}")
        # d[9] = found_in. Có mặt trong danh bạ của BẤT KỲ app nào là đủ:
        # một người dùng hai app chỉ cần một bên khai là đã được cấp quyền.
        in_directory = any(d[9] == "directory" for d in group)
        # Vai trò CAO NHẤT trong các app. Một người là UNIT_LEAD ở app này và
        # MEMBER ở app kia thì vẫn là trưởng đơn vị - lấy dòng đầu tiên gặp sẽ
        # ra kết quả khác nhau tuỳ thứ tự đọc file.
        roles = [d[10] for d in group if d[10]]
        role = min(roles, key=lambda r: ROLE_RANK.get(r, 99)) if roles else None
        # is_enabled: chỉ Ralli khai. False ở BẤT KỲ app nào là đã bị khoá.
        flags = [d[6] for d in group if d[6] is not None]
        enabled = (all(flags) if flags else None)
        # created_at: lấy ngày SỚM NHẤT - người này được cấp quyền từ lúc đó.
        dates = sorted(d[7] for d in group if d[7])
        accounts.append((i, u, names[0] if names else None,
                         emails[0] if emails else None, "real",
                         chosen[5], is_shared(u, in_directory), role, enabled,
                         dates[0] if dates else None, chosen[1], conflict))

    # Tài khoản KỸ THUẬT. Không phải dữ liệu thiếu - Google vốn chỉ báo được mức
    # project, không bao giờ biết ai gọi. Có dòng này thì khoá của fact_usage_daily
    # không phải nhận NULL (xem ghi chú ở bảng đó).
    #
    # Đơn vị của chúng là đơn vị kỹ thuật của chính agent đó. Mỗi agent phải có
    # ĐÚNG một đơn vị kỹ thuật - kiểm tường minh chứ không để dict âm thầm giữ
    # dòng cuối cùng nếu có hai.
    technical_unit: dict[int, str] = {}
    for r in unit_rows:
        if r[6]:
            if r[1] in technical_unit:
                raise SystemExit(f"agent {r[1]} co >1 don vi ky thuat:"
                                 f" {technical_unit[r[1]]} va {r[0]}")
            technical_unit[r[1]] = r[0]

    i = len(by_username)
    technical_account: dict[tuple[str, int], int] = {}
    for aid in sorted(agent_name):
        for slot in ("whole_agent", "unattributed"):
            i += 1
            technical_account[(slot, aid)] = i
            label = (f"Cả {agent_name[aid]}" if slot == "whole_agent"
                     else "Chưa quy được")
            # `slot` là CHỖ NGỒI trong khoá của fact_usage_daily; `kind` là điều
            # ta NÓI VỚI người đọc về dòng đó. Hai chuyện này chỉ khác nhau ở
            # đúng một trường hợp - agent một-người-dùng:
            #
            #   'whole_agent'     Google chỉ báo mức project, KHÔNG biết ai
            #                     trong 45 / 892 người đã gọi. Không quy được.
            #   'service_account' agent chạy bằng MỘT tài khoản dịch vụ. Biết
            #                     chính xác là ai - chỉ là "ai" đó không phải
            #                     một con người. QUY ĐƯỢC.
            #
            # Trước 20/08/2026 cả hai dùng chung 'whole_agent', nên health() đếm
            # 749 triệu token của 6 agent này vào phần "không quy được về người"
            # và báo độ phủ 12,4% trong khi lỗ hổng thật chỉ 1,2%.
            #
            kind = ("service_account"
                    if slot == "whole_agent" and aid in SINGLE_USER_AGENTS
                    else slot)
            # TÊN ĐĂNG NHẬP CỦA TÀI KHOẢN DỊCH VỤ = `svc.` + dim_agent.code
            # (quyết định A3, chốt 20/08/2026).
            #
            # Đây KHÔNG phải đổi tên cho đẹp. Ngày Gateway chạy, 6 agent
            # một-người-dùng gửi lên đúng chuỗi này làm username, và Gateway tra
            # nó ra account_id. Để tên tạm `__whole_agent_<id>__` thì username
            # Gateway gửi lên KHÔNG TRA RA TÀI KHOẢN NÀO.
            #
            # Hai loại còn lại GIỮ tên tạm, có lý do:
            #   whole_agent   Ralli và Hợp Đồng - Gateway gửi username THẬT của
            #                 người dùng, không ai gửi tên chỗ ngồi này lên
            #   unattributed  không phải tài khoản, chỉ là chỗ dồn phần không
            #                 quy được
            #
            # Trước 21/08 build_usage_daily.py tra tài khoản này BẰNG TÊN ĐĂNG
            # NHẬP, nên đổi tên ở đây là gãy khâu nạp. Đã sửa cùng lúc: nó tra
            # bằng (kind, unit_agent_id) - hỏi đúng câu nó cần hỏi, và không còn
            # phụ thuộc vào một chuỗi ký tự nữa.
            username = (f"svc.{agent_code[aid]}" if kind == "service_account"
                        else f"__{slot}_{aid}__")
            # is_shared = 1: theo đúng định nghĩa, đây không phải tài khoản của
            # một người. Nhờ vậy chỉ tiêu tỷ lệ áp dụng chỉ cần lọc `is_shared`
            # là đủ, không phải liệt kê thêm điều kiện về `kind`.
            accounts.append((i, username, label, None, kind,
                             technical_unit[aid], 1, None, None, None, aid, 0))

    cur.executemany(
        f"INSERT INTO account (account_id, username, full_name, email, kind,"
        f" unit_id, is_shared, role, is_enabled, created_at,"
        f" unit_agent_id, unit_conflict)"
        f" VALUES ({','.join([ph] * 12)})",
        accounts)

    # account_id chèn vào sau agent_id, khớp thứ tự cột của schema.
    user_rows = [(d[0], d[1],
                  technical_account[("whole_agent", d[1])] if d[8]
                  else account_id_of[norm(d[2])],
                  *d[2:]) for d in user_rows]

    cur.executemany(
        f"INSERT INTO dim_user (user_id, agent_id, account_id, username, full_name,"
        f" email, unit_id, is_enabled, created_at, is_technical, found_in, role)"
        f" VALUES ({','.join([ph] * 12)})", user_rows)

    # ================================================== (5) dim_function
    function_rows: list[tuple] = []
    for f in sorted({c.get("function") for c in calls if c.get("function")}):
        function_rows.append((RALLI, f, FUNCTION_LABELS.get(f), None))
    # Nguồn cũ là by-function-2026.csv (phái sinh). Nay lấy từ chính phần
    # `by_function` của stats cả năm, là thứ API trả về trực tiếp.
    for r in read_json(TLA_DIR / "token-usage-year.json").get("by_function") or []:
        function_rows.append((TLA_HD, r["function"],
                              FUNCTION_LABELS.get(r["function"]), None))
    cur.executemany(
        f"INSERT INTO dim_function (agent_id, code, label, is_user_facing)"
        f" VALUES ({','.join([ph] * 4)})", function_rows)

    # ================================================== nghiệm thu
    n_units = connect.query_one(cn, "SELECT COUNT(*) FROM dim_unit")[0]
    n_users = connect.query_one(cn, "SELECT COUNT(*) FROM dim_user")[0]
    n_tech = connect.query_one(cn, "SELECT COUNT(*) FROM dim_user WHERE is_technical")[0]
    n_funcs = connect.query_one(cn, "SELECT COUNT(*) FROM dim_function")[0]
    by_source = dict(connect.query(cn, "SELECT found_in, COUNT(*) FROM dim_user"
                                       " GROUP BY found_in"))

    log.info("  source       %s/%s + %s/%s", RALLI_DIR.parent.name, RALLI_DIR.name,
             TLA_DIR.parent.name, TLA_DIR.name)
    log.info("  dim_unit     %4d  (%d real + 6 technical + 2 unresolved)",
             n_units, len(unit_rows) - 8)
    log.info("  dim_user     %4d  %s", n_users, by_source)
    log.info("  account      %4d  %s",
             connect.query_one(cn, "SELECT COUNT(*) FROM account")[0],
             dict(connect.query(cn, "SELECT kind, COUNT(*) FROM account"
                                    " GROUP BY kind")))
    log.info("  dim_function %4d", n_funcs)

    # Xung đột đơn vị KHÔNG phải lỗi - là PHÁT HIỆN, in ra chứ không chặn việc.
    # Cùng một tổ chức được hai app mô hình hoá khác nhau; ta đã chọn một bên
    # theo quy tắc tất định và đánh dấu lại ở cột unit_conflict.
    if conflicts:
        log.warning("  unit clashes %4d  (resolved by rule, column"
                    " unit_conflict=1)", len(conflicts))
        for c in conflicts:
            log.warning("                 %s", c)

    # Mọi user_id trong nhật ký PHẢI có chỗ trỏ tới - nếu không, fact_call sẽ hỏng
    known_users = {r[0] for r in connect.query(
        cn, f"SELECT user_id FROM dim_user WHERE agent_id = {ph}", (RALLI,))}
    orphans = {c.get("user_id") for c in calls} - known_users - {None}

    # Số mong đợi SUY TỪ NGUỒN, không ghim. Phép kiểm này bắt đúng cái nó sinh ra
    # để bắt: dòng rơi rớt giữa file nguồn và database (khoá trùng, khoá ngoại
    # trượt, executemany nuốt dòng). Nó không còn kêu khi tổ chức thay đổi.
    errors = []
    if n_units != len(unit_rows):
        errors.append(f"dim_unit {n_units} != {len(unit_rows)} dong dung tu nguon")
    if n_users != len(user_rows):
        errors.append(f"dim_user {n_users} != {len(user_rows)} dong dung tu nguon")
    if n_tech != len(SINGLE_USER_AGENTS):
        errors.append(f"dong ky thuat {n_tech} != {len(SINGLE_USER_AGENTS)}")
    if n_funcs != len(function_rows):
        errors.append(f"dim_function {n_funcs} != {len(function_rows)} dong tu nguon")
    if orphans:
        errors.append(f"{len(orphans)} user_id trong nhat ky khong co trong dim_user:"
                      f" {sorted(orphans)[:3]}")
    n_accounts = connect.query_one(cn, "SELECT COUNT(*) FROM account")[0]
    if n_accounts != len(accounts):
        errors.append(f"account {n_accounts} != {len(accounts)} dong dung tu nguon")
    # Không dòng dim_user nào được để trống account_id: để trống là một người dùng
    # biến mất khỏi mọi thống kê theo tài khoản mà không có gì báo.
    dangling = connect.query_one(
        cn, "SELECT COUNT(*) FROM dim_user WHERE account_id IS NULL")[0]
    if dangling:
        errors.append(f"{dangling} dim_user rows have no account_id")
    # Đơn vị của tài khoản phải là MỘT TRONG các đơn vị mà chính dòng dim_user
    # của nó đã khai. Phép kiểm này bắt đúng cái dễ sai nhất khi viết đoạn trên:
    # lấy nhầm chỉ số trong tuple, khiến ta gán cho người ta một phòng ban mà
    # không nguồn nào từng nói. Không bắt được bằng mắt, và số vẫn trông như thật.
    invented = connect.query_one(cn, """
        SELECT COUNT(*) FROM account a
        WHERE a.kind = 'real'
          AND NOT EXISTS (SELECT 1 FROM dim_user u
                          WHERE u.account_id = a.account_id
                            AND u.unit_id = a.unit_id)""")[0]
    if invented:
        errors.append(f"{invented} accounts have a unit no source declares")

    if errors:
        cn.rollback()
        raise SystemExit("ACCEPTANCE FAILED - rolled back, nothing written:\n  "
                         + "\n  ".join(errors))
    cn.commit()
    log.info("  acceptance passed")


if __name__ == "__main__":
    main()
