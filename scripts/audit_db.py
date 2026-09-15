"""Soi toàn bộ database một lượt: cấu trúc, số khớp, phân loại, lỗ im lặng.

    python scripts/audit_db.py
    python scripts/audit_db.py --db "postgresql://token:token_local@localhost:5432/token_ledger_v2"

CHỈ ĐỌC. Không ghi, không sửa, không xoá: kết nối PostgreSQL đặt session
`readonly`, nên máy chủ database thực thi giới hạn này.

VÌ SAO CẦN FILE NÀY
-------------------
Mỗi khâu nạp đều có nghiệm thu riêng, nhưng chúng chỉ kiểm PHẦN CỦA MÌNH:
load_billing đếm dòng hoá đơn, load_ralli đếm dòng nhật ký. Không ai kiểm cái
nằm GIỮA các bảng - và đó là chỗ hỏng đắt nhất, vì một bảng lẻ khớp tuyệt đối
với nguồn của nó vẫn có thể trỏ vào một dòng đã biến mất ở bảng khác.

BA MỨC KẾT QUẢ, KHÁC NHAU VỀ HÀNH ĐỘNG
--------------------------------------
    DAT       không phải làm gì
    CANH BAO  dữ liệu thiếu mà ta ĐÃ BIẾT và đã chấp nhận. In ra kèm số lượng
              để con số đó không âm thầm to lên. KHÔNG làm script thất bại.
    HONG      cấu trúc sai. Mã thoát khác 0.

Ranh giới giữa CANH BAO và HONG là: có sửa được bằng cách nạp lại không. "Google
không ghi ai gọi" thì nạp lại bao nhiêu lần cũng thế - đó là CANH BAO. Còn "một
dòng trỏ vào unit_id không tồn tại" là HONG.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "db"))

import connect  # noqa: E402

OK, WARN, FAIL = "DAT", "CANH BAO", "HONG"


def open_read_only(dsn: str):
    """Mở kết nối PostgreSQL và đặt session chỉ-đọc ở mức máy chủ."""
    cn, placeholder = connect.open_db(dsn)
    cn.set_session(readonly=True)
    return cn, placeholder


class Audit:
    def __init__(self, cn):
        self.cn = cn
        self.results: list[tuple[str, str, str]] = []

    def num(self, sql: str, params=()) -> float:
        """Một con số từ một câu SELECT. NULL -> 0."""
        r = connect.query_one(self.cn, sql, params)
        return float(r[0]) if r and r[0] is not None else 0.0

    def note(self, level: str, label: str, detail: str = "") -> None:
        self.results.append((level, label, detail))

    def check(self, ok: bool, label: str, detail_if_bad: str,
              level_if_bad: str = FAIL) -> None:
        self.note(OK if ok else level_if_bad, label, "" if ok else detail_if_bad)

    def check_tren(self, quan_sat: float, ok: bool, label: str,
                   detail_if_bad: str, level_if_bad: str = FAIL) -> None:
        """Như `check()`, nhưng KHAI CẢ MẪU SỐ - số dòng phép kiểm đã quan sát.

        VÌ SAO CẦN (thêm 03/09/2026)
        ----------------------------
        Mọi phép kiểm theo nguồn đang mang hình dạng:

            n = COUNT(*) WHERE source='gateway' AND <dieu kien xau>
            check(n == 0, ...)

        Với **0 dòng gateway**, `n` bằng 0 và phép kiểm báo ĐẠT. Nó không phân
        biệt *"Gateway ghi đúng"* với *"Gateway không ghi gì cả"*.

        Đây không phải chuyện lý thuyết. Bước `load_gateway.py` hỏng im lặng thì
        `fact_call` không có dòng gateway nào, MỌI phép kiểm gateway vẫn xanh, và
        dashboard chỉ trông như "chưa có lưu lượng". Cùng hình dạng lỗi đã để API
        mù 38 phút ngày 02/09: một phép kiểm khẳng định tính chất mà nó chưa thực
        sự quan sát.

        BA KẾT CỤC, KHÔNG PHẢI HAI
        --------------------------
            quan sat 0 dong             -> CANH BAO "chua kiem duoc"
            quan sat n > 0, khong loi   -> DAT, nhan kem "(n rows checked)"
            quan sat n > 0, co loi      -> HONG

        CẢNH BÁO chứ không HỎNG: database mới dựng, hoặc kỳ chưa có lưu lượng của
        nguồn đó, là trạng thái HỢP LỆ. Ranh giới của file này đã chốt ở docstring
        đầu - *"có sửa được bằng cách nạp lại không"*. Chưa có dữ liệu thì nạp lại
        không giúp gì. Nhưng nó PHẢI HIỆN RA, vì hôm nay nó vô hình.

        Con số `n` in ra trong nhãn: *"đạt trên 41 dòng"* khác hẳn *"đạt"*, và
        khác đúng ở chỗ người đọc cần biết.
        """
        if quan_sat == 0:
            self.note(WARN, label,
                      "CHUA KIEM DUOC - 0 dong de quan sat."
                      " Day KHONG phai ket qua dat.")
            return
        self.note(OK if ok else level_if_bad,
                  f"{label} ({int(quan_sat)} rows checked)",
                  "" if ok else detail_if_bad)


# Số quan hệ khoá ngoại ĐỌC ĐƯỢC ngày 03/09/2026. Danh sách nay tự sinh từ
# `pg_constraint`, nên nó tự phủ mọi bảng mới - nhưng đúng vì thế mà nó có ĐIỂM MÙ
# NGƯỢC LẠI: xoá một khoá ngoại thì danh sách ngắn đi và phép kiểm VẪN XANH, vì nó
# chỉ kiểm những gì còn lại.
#
# Con số này là chốt chặn cho điểm mù đó. Tụt xuống dưới là HỎNG.
# Thêm bảng mới thì con số thật tăng lên - đó là bình thường, và phép kiểm không
# kêu. Chỉ cần cập nhật mốc này khi muốn nâng sàn.
MOC_KHOA_NGOAI = 36


def doc_khoa_ngoai(cn) -> list[tuple[str, str, str, str]]:
    """(bảng con, cột con, bảng cha, cột cha) - đọc TỪ DATABASE, không chép tay.

    VÌ SAO KHÔNG GIỮ DANH SÁCH GÕ TAY (đổi 03/09/2026)
    ---------------------------------------------------
    Bản trước là hằng số `FOREIGN_KEYS` 23 dòng. Đo ngày 03/09: database có **36**
    quan hệ, tức **13 quan hệ không ai canh**. Danh sách không sai vì ai đó cẩu
    thả - nó sai vì CẤU TRÚC ĐI TIẾP CÒN BẢN CHÉP THÌ ĐỨNG LẠI:

        6/13 quan he thieu do chinh migration 008 tao ra SANG NAY
             (fact_usage_hourly 4 khoa, fact_latency_daily.source,
              fact_perf_daily.source)

    Và nó tụt trong im lặng: nhãn vẫn báo `Foreign keys (23 relations)` ĐẠT, mà 23
    là số quan hệ ĐƯỢC KHAI chứ không phải số quan hệ CÓ THẬT.

    CHỈ CHẠY TRÊN POSTGRESQL. `pg_constraint` là catalog riêng của PostgreSQL.
    Dự án đã bỏ SQLite từ change `drop-the-sqlite-escape-hatch` (24/08/2026) nên
    đây không phải mất mát mới - nhưng đừng để ai tưởng file này còn chạy đa hệ.
    """
    return [(r[0], r[1], r[2], r[3]) for r in connect.query(cn, """
        SELECT c.conrelid::regclass::text  AS bang_con,
               ac.attname                  AS cot_con,
               c.confrelid::regclass::text AS bang_cha,
               ap.attname                  AS cot_cha
        FROM pg_constraint c
        JOIN unnest(c.conkey)  WITH ORDINALITY kc(attnum, ord) ON TRUE
        JOIN unnest(c.confkey) WITH ORDINALITY kp(attnum, ord) ON kp.ord = kc.ord
        JOIN pg_attribute ac ON ac.attrelid = c.conrelid  AND ac.attnum = kc.attnum
        JOIN pg_attribute ap ON ap.attrelid = c.confrelid AND ap.attnum = kp.attnum
        WHERE c.contype = 'f' AND c.connamespace = 'public'::regnamespace
        ORDER BY 1, 2""")]


# GIỮ LẠI để đối chiếu: đây là danh sách gõ tay của bản trước 03/09/2026. Nó KHÔNG
# còn được dùng để kiểm - `doc_khoa_ngoai()` thay chỗ đó - nhưng phép kiểm
# `Foreign keys are read from the database, not from a hand-written list` so hai
# con số để chuyện "bản chép tay tụt lại" hiện ra thành một số, chứ không phải một
# lời kể.
#
# (bảng con, cột con, bảng cha, cột cha)
FOREIGN_KEYS_GO_TAY = [
    ("dim_unit", "agent_id", "dim_agent", "agent_id"),
    ("dim_unit", "parent_id", "dim_unit", "unit_id"),
    ("account", "unit_id", "dim_unit", "unit_id"),
    ("account", "unit_agent_id", "dim_agent", "agent_id"),
    ("dim_user", "account_id", "account", "account_id"),
    ("dim_user", "unit_id", "dim_unit", "unit_id"),
    ("dim_user", "agent_id", "dim_agent", "agent_id"),
    ("fact_call", "account_id", "account", "account_id"),
    ("fact_call", "model_id", "dim_model", "model_id"),
    ("fact_call", "agent_id", "dim_agent", "agent_id"),
    ("fact_app_daily", "account_id", "account", "account_id"),
    ("fact_app_daily", "model_id", "dim_model", "model_id"),
    ("fact_app_daily", "agent_id", "dim_agent", "agent_id"),
    ("fact_billing_daily", "agent_id", "dim_agent", "agent_id"),
    ("fact_billing_daily", "model_id", "dim_model", "model_id"),
    ("fact_monitoring", "agent_id", "dim_agent", "agent_id"),
    ("fact_monitoring", "model_id", "dim_model", "model_id"),
    # Nguon la ang la bi chan ngay luc GHI, khong doi phep kiem chay sau. Van
    # liet ke o day de audit database dung tu schema truoc 21/08/2026, khi rang
    # buoc nay chua ton tai.
    ("fact_usage_daily", "source", "ref_source", "source"),
    ("fact_usage_daily", "account_id", "account", "account_id"),
    ("fact_usage_daily", "model_id", "dim_model", "model_id"),
    ("fact_usage_daily", "agent_id", "dim_agent", "agent_id"),
    ("fact_perf_daily", "agent_id", "dim_agent", "agent_id"),
    ("fact_latency_daily", "agent_id", "dim_agent", "agent_id"),
]


def group_a_structure(a: Audit) -> None:
    """Khoá ngoại, cây đơn vị, khoá trống."""
    # LEFT JOIN nói rõ bảng/cột nào bị treo thay vì trả một danh sách rowid mơ hồ,
    # và chạy trực tiếp trên PostgreSQL hiện tại.
    quan_he = doc_khoa_ngoai(a.cn)
    dangling = []
    for child, col, parent, key in quan_he:
        n = a.num(f"""SELECT COUNT(*) FROM {child} c
                      LEFT JOIN {parent} p ON p.{key} = c.{col}
                      WHERE c.{col} IS NOT NULL AND p.{key} IS NULL""")
        if n:
            dangling.append(f"{child}.{col} -> {parent}: {int(n)} rows")
    # Con so trong nhan la so quan he CO THAT, khong phai so quan he duoc khai.
    a.check(not dangling, f"Foreign keys ({len(quan_he)} relations, read from the database)",
            "; ".join(dangling))

    # DIEM MU NGUOC LAI cua danh sach tu sinh: xoa mot khoa ngoai thi danh sach
    # ngan di va phep kiem tren VAN XANH - no chi kiem nhung gi con lai. Moc so
    # luong la cho chan chuyen do.
    a.check(len(quan_he) >= MOC_KHOA_NGOAI,
            f"Foreign key count has not dropped (>= {MOC_KHOA_NGOAI})",
            f"chi con {len(quan_he)} quan he, moc la {MOC_KHOA_NGOAI}"
            f" - mot khoa ngoai da bien mat khoi database")

    # Bang chep tay cu tut lai bao nhieu. KHONG phai phep kiem ve du lieu - no do
    # KHOANG CACH giua cach lam cu va cach lam moi, va no la ly do change nay ton
    # tai. Muc CANH BAO: bang cu khong con duoc dung, nen lech khong lam hong gi.
    khai_tay = {(b, c) for b, c, _, _ in FOREIGN_KEYS_GO_TAY}
    that = {(b, c) for b, c, _, _ in quan_he}
    tut = sorted(that - khai_tay)
    a.check(not tut,
            "Foreign keys are read from the database, not from a hand-written list",
            f"danh sach go tay cu bo sot {len(tut)}/{len(that)} quan he:"
            f" {', '.join(f'{b}.{c}' for b, c in tut[:6])}"
            + (" ..." if len(tut) > 6 else ""), WARN)

    # Cây đơn vị: level phải bằng độ sâu thật. Lệch nghĩa là `path` đã sai theo,
    # và mọi báo cáo gom theo cấp đều gom nhầm.
    parent_of = {r[0]: r[1] for r in connect.query(
        a.cn, "SELECT unit_id, parent_id FROM dim_unit")}
    level_of = {r[0]: r[1] for r in connect.query(
        a.cn, "SELECT unit_id, level FROM dim_unit")}
    cycles, bad_level = [], []
    for u in parent_of:
        seen, cur, depth = {u}, parent_of.get(u), 1
        while cur:
            if cur in seen:
                cycles.append(u)
                break
            seen.add(cur)
            depth += 1
            cur = parent_of.get(cur)
        else:
            # Dòng kỹ thuật 'Chưa quy được' có level=0 có ý - không phải một cấp
            # thật trong cây, mà là chỗ để những gì không quy được.
            if level_of[u] not in (0, depth):
                bad_level.append(f"{u}: level={level_of[u]} nhung sau={depth}")
    a.check(not cycles, "Unit tree has no cycle",
            f"{len(cycles)} rows: {cycles[:3]}")
    a.check(not bad_level, "Column `level` matches the real depth",
            f"{len(bad_level)} rows: {bad_level[:3]}")

    # Một tài khoản một đơn vị - khuyết tật đã sửa 14/08. Đối chiếu ngược: đơn vị
    # được chọn phải là một trong những đơn vị mà chính dim_user của nó khai,
    # không được là đơn vị bịa ra do lấy nhầm chỉ số trong tuple.
    invented = a.num("""SELECT COUNT(*) FROM account x
                        WHERE x.kind = 'real'
                          AND NOT EXISTS (SELECT 1 FROM dim_user u
                                          WHERE u.account_id = x.account_id
                                            AND u.unit_id = x.unit_id)""")
    a.check(invented == 0, "Account unit comes from the source",
            f"{int(invented)} accounts have a unit no source declares")


def group_b_totals(a: Audit) -> None:
    """Tiền và token phải bằng nhau qua mọi tầng tổng hợp."""
    # Migration 005 (31/08/2026) cho `usage_resolved.cost_usd` nhan them tien cua
    # Gateway khi dong do CHUA co hoa don. Nen ve trai khong con la mot minh
    # fact_billing_daily nua.
    #
    # BAY: KHONG duoc cong thang `hoa don + toan bo gateway`. View uu tien hoa
    # don, nen dong nao co CA HAI thi tien gateway bi BO. Ngay hoa don cho ngay
    # 31/08 ve la hai nguon trung khoa, va phep cong thang se tinh doi.
    # Dieu kien NOT EXISTS duoi day lay dung phan gateway ma view thuc su dung.
    src_cost = a.num("SELECT SUM(cost_usd) FROM fact_billing_daily")
    gw_cost = a.num("""
        SELECT COALESCE(SUM(g.cost_usd), 0) FROM fact_usage_daily g
         WHERE g.source = 'gateway'
           AND NOT EXISTS (SELECT 1 FROM fact_usage_daily b
                            WHERE b.source = 'billing' AND b.day = g.day
                              AND b.agent_id = g.agent_id
                              AND b.model_id = g.model_id)""")
    view_cost = a.num("SELECT SUM(cost_usd) FROM usage_resolved")
    a.check(abs(src_cost + gw_cost - view_cost) < 1e-4,
            "Cost: invoice + gateway == usage_resolved",
            f"${src_cost:.6f} + ${gw_cost:.6f} != ${view_cost:.6f}")

    # Nguồn 'app' có HAI bảng gốc: Ralli qua fact_call (từng lượt gọi), TLA HĐ
    # qua fact_app_daily (app chỉ phơi số đã gộp). Cả hai đều lọc
    # model_id IS NOT NULL cho khớp điều kiện mà build_usage_daily dùng - dòng
    # không biết model không vào được fact_usage_daily vì model_id nằm trong khoá.
    # `source='app'` THEM 31/08/2026, cung ly do voi build_usage_daily.load_app():
    # tu khi Gateway do vao cung bang fact_call, khong loc thi ve trai cong ca
    # token cua Gateway trong khi ve phai chi dem nguon 'app'. Do luc do: lech
    # dung 45.187 token - bang het luu luong Gateway.
    call_tokens = a.num("SELECT SUM(total_tokens) FROM fact_call"
                        " WHERE model_id IS NOT NULL AND source = 'app'")
    hd_tokens = a.num("SELECT SUM(total_tokens) FROM fact_app_daily"
                      " WHERE model_id IS NOT NULL")
    app_tokens = a.num("SELECT SUM(total_tokens) FROM fact_usage_daily"
                       " WHERE source='app'")
    a.check(call_tokens + hd_tokens == app_tokens,
            "App tokens: fact_call + fact_app_daily == fact_usage_daily",
            f"{call_tokens:,.0f} + {hd_tokens:,.0f} != {app_tokens:,.0f}")

    src_tokens = a.num("SELECT SUM(quantity) FROM fact_billing_daily")
    billing_tokens = a.num("SELECT SUM(total_tokens) FROM fact_usage_daily"
                           " WHERE source='billing'")
    a.check(src_tokens == billing_tokens, "Invoice tokens: source == fact_usage_daily",
            f"{src_tokens:,.0f} != {billing_tokens:,.0f}")

    # usage_resolved phải là MỘT dòng cho mỗi (day, agent, model). Nhiều hơn là
    # view đang nhân bản dòng - tức mọi tổng đọc từ nó đều to lên âm thầm.
    n_rows = a.num("SELECT COUNT(*) FROM usage_resolved")
    n_keys = a.num("SELECT COUNT(*) FROM (SELECT DISTINCT day, agent_id, model_id"
                   " FROM usage_resolved) x")
    a.check(n_rows == n_keys, "usage_resolved: one row per key",
            f"{int(n_rows)} rows but only {int(n_keys)} keys")

    # View KHÔNG được cộng ba nguồn lại - chúng đo CÙNG một lưu lượng bằng ba
    # cái công tơ khác nhau, cộng lại là đếm ba lần.
    #
    # KHÔNG kiểm bằng "tổng view <= tổng nguồn lớn nhất". Đã viết như thế một lần
    # và nó báo hỏng oan: ba nguồn phủ ba tập khoá KHÁC NHAU (hoá đơn không có
    # Ralli, app chỉ có Ralli), nên tổng view là HỢP CỦA BA, đúng lý khi lớn hơn
    # bất kỳ nguồn nào. Phép kiểm đúng phải xét TỪNG KHOÁ: con số view báo cho
    # một khoá phải bằng y nguyên con số của nguồn mà nó khai là đã chọn.
    double_counted = a.num("""
        SELECT COUNT(*) FROM usage_resolved v
        JOIN (SELECT day, agent_id, model_id, source, SUM(total_tokens) AS t
              FROM fact_usage_daily GROUP BY day, agent_id, model_id, source) f
          ON f.day = v.day AND f.agent_id = v.agent_id
         AND f.model_id = v.model_id AND f.source = v.token_source
        WHERE v.total_tokens <> f.t""")
    a.check(double_counted == 0, "usage_resolved keeps the chosen source's figure verbatim",
            f"{int(double_counted)} rows differ from the source they name")


def group_c_classification(a: Audit) -> None:
    """Mọi tên lạ phải có trong bảng alias, không được rơi vào im lặng."""
    unknown_metric = a.num("""SELECT COUNT(DISTINCT m.metric_type) FROM fact_monitoring m
                              LEFT JOIN dim_metric_alias d
                                ON d.source='monitoring' AND d.raw_name = m.metric_type
                              WHERE d.raw_name IS NULL""")
    a.check(unknown_metric == 0, "Every metric_type is in dim_metric_alias",
            f"{int(unknown_metric)} unknown metrics")

    unknown_sku = a.num("""SELECT COUNT(DISTINCT b.sku_id) FROM fact_billing_daily b
                           LEFT JOIN dim_metric_alias d
                             ON d.source='billing_sku' AND d.raw_name = b.sku_id
                           WHERE d.raw_name IS NULL""")
    a.check(unknown_sku == 0, "Every sku_id is in dim_metric_alias",
            f"{int(unknown_sku)} SKU la")

    unknown_sku_model = a.num("""SELECT COUNT(DISTINCT b.sku_id) FROM fact_billing_daily b
                                 LEFT JOIN dim_model_alias d
                                   ON d.source='billing_sku' AND d.raw_name = b.sku_id
                                 WHERE d.raw_name IS NULL""")
    a.check(unknown_sku_model == 0, "Every sku_id is in dim_model_alias",
            f"{int(unknown_sku_model)} SKU la")

    # `is_quota_limit` là bản sao của dim_metric_alias.measures='quota_limit' nằm
    # trong bảng sự kiện. Bản sao thì có thể lệch - phép kiểm này là lý do duy
    # nhất để còn giữ cả hai.
    mismatch = a.num("""SELECT COUNT(*) FROM fact_monitoring f
                        JOIN dim_metric_alias d
                          ON d.source='monitoring' AND d.raw_name = f.metric_type
                        WHERE (CASE WHEN f.is_quota_limit THEN 1 ELSE 0 END)
                           <> (CASE WHEN d.measures='quota_limit' THEN 1 ELSE 0 END)""")
    a.check(mismatch == 0, "is_quota_limit matches dim_metric_alias",
            f"{int(mismatch)} contradicting rows")


def group_e_adoption(a: Audit) -> None:
    """Chỉ tiêu tỷ lệ áp dụng - mẫu số và tử số phải nhất quán.

    Biểu đồ này từng trắng trơn suốt một thời gian dài mà không ai biết vì sao,
    nên nó cần phép kiểm riêng chứ không dựa vào việc nhìn màn hình.
    """
    # Mỗi agent phải có ĐÚNG MỘT cách xác định mẫu số: hoặc có danh bạ người
    # dùng, hoặc có tài khoản dịch vụ đại diện. Không có cái nào thì biểu đồ
    # không vẽ được dòng đó, và đó là thứ phải lộ ra ở đây.
    no_denominator = [r[0] for r in connect.query(a.cn, """
        SELECT g.name FROM dim_agent g
        WHERE NOT EXISTS (SELECT 1 FROM dim_user d
                           WHERE d.agent_id = g.agent_id AND d.found_in = 'directory')
          AND NOT EXISTS (SELECT 1 FROM account c
                           WHERE c.unit_agent_id = g.agent_id
                             AND c.kind IN ('service_account', 'whole_agent'))
        ORDER BY g.name""")]
    a.check(not no_denominator, "Every agent has a denominator for the adoption rate",
            f"denominator undetermined: {no_denominator}")

    # Tử số không được vượt mẫu số. Vượt nghĩa là đang đếm người có dùng mà
    # KHÔNG nằm trong danh bạ - phải rơi vào cột outside_directory, không được
    # cộng vào tử số, vì cộng thì tỷ lệ ra trên 100%.
    over = a.num("""
        SELECT COUNT(*) FROM dim_agent g WHERE
          (SELECT COUNT(DISTINCT f.account_id) FROM fact_usage_daily f
             JOIN account c ON c.account_id = f.account_id
            WHERE f.agent_id = g.agent_id AND c.is_shared = 0
              AND f.source IN (SELECT source FROM ref_source WHERE knows_user)
              AND f.account_id IN (SELECT d.account_id FROM dim_user d
                                    WHERE d.agent_id = g.agent_id
                                      AND d.found_in = 'directory'))
          >
          (SELECT COUNT(DISTINCT d.account_id) FROM dim_user d
             JOIN account c ON c.account_id = d.account_id
            WHERE d.agent_id = g.agent_id AND d.found_in = 'directory'
              AND c.is_shared = 0)""")
    a.check(over == 0, "Adoption rate never exceeds 100%",
            f"{int(over)} agents have numerator > denominator")

    # fact_app_daily: khoá tự nhiên phải duy nhất. Trùng nghĩa là khâu kéo gộp
    # hụt, và hậu quả là token bị đếm hai lần khi đổ về fact_usage_daily.
    dup = a.num("""SELECT COUNT(*) FROM (
        SELECT day, agent_id, account_id, raw_model, COUNT(*) AS n
        FROM fact_app_daily GROUP BY day, agent_id, account_id, raw_model
        HAVING COUNT(*) > 1) x""")
    a.check(dup == 0, "fact_app_daily: one row per (day, account, model)",
            f"{int(dup)} bo bi trung")

    # Người CÓ dùng nhưng KHÔNG còn trong danh bạ. Không phải lỗi - tài khoản bị
    # xoá là chuyện bình thường - nhưng con số này lớn dần nghĩa là danh bạ và
    # số liệu sử dụng đang trôi ra xa nhau, và đó là thứ cần biết sớm.
    outside = a.num("""
        SELECT COUNT(DISTINCT f.account_id) FROM fact_usage_daily f
        JOIN account c ON c.account_id = f.account_id
        WHERE f.source IN (SELECT source FROM ref_source WHERE knows_user)
          AND c.kind = 'real' AND c.is_shared = 0
          AND NOT EXISTS (SELECT 1 FROM dim_user d
                           WHERE d.account_id = f.account_id
                             AND d.agent_id = f.agent_id
                             AND d.found_in = 'directory')""")
    a.check(outside == 0, "Every person with usage is still in the directory",
            f"{int(outside)} accounts made requests but are no longer in the"
            f" directory - not counted in the numerator", WARN)

    # LƯỚI AN TOÀN cho danh sách tài khoản dùng chung trong load_org.py.
    #
    # Danh sách đó gõ tay, nên nó chỉ đúng cho tới khi app sinh thêm một tài
    # khoản hệ thống mới. Đã xảy ra: `system` (6.986 lượt, 40,8 triệu token -
    # lớn nhất toàn Ralli) và `guest` bị đếm như nhân viên suốt một thời gian,
    # và chỉ lộ ra khi có người ngồi đọc bảng bằng mắt.
    #
    # Dấu hiệu máy đọc được: có phát sinh request mà KHÔNG có họ tên lẫn email.
    # Một nhân viên thật luôn có ít nhất một trong hai. Không tự đánh dấu - việc
    # phân loại vẫn là quyết định của con người - nhưng phải kêu lên.
    idle = [r[0] for r in connect.query(a.cn, """
        SELECT DISTINCT c.username FROM fact_usage_daily f
        JOIN account c ON c.account_id = f.account_id
        WHERE f.source IN (SELECT source FROM ref_source WHERE knows_user)
          AND c.kind = 'real' AND c.is_shared = 0
          AND (c.full_name IS NULL OR c.full_name = '')
          AND (c.email IS NULL OR c.email = '')
        ORDER BY c.username""")]
    a.check(not idle, "Every account with usage is identifiable as a person",
            f"{len(idle)} accounts have requests but no name and no email:"
            f" {idle} - likely system accounts, see SHARED_EXACT"
            f" trong db/load_org.py", WARN)


def group_d_silent_gaps(a: Audit) -> None:
    """Những chỗ dữ liệu thiếu mà không có gì báo. Đều là CANH BAO."""
    # Nguyên nhân đã truy ra 14/08: các dòng này đều là model EMBEDDING. Cloud
    # Monitoring có phép đo lượt cho embedding (quota/embed_content_.../usage)
    # nhưng KHÔNG có phép đo token nào cho nó - trong khi hoá đơn thì có. Ngày
    # nào hoá đơn chưa kịp về, khoá đó chỉ còn lượt.
    missing_tokens = a.num("SELECT COUNT(*) FROM usage_resolved WHERE total_tokens IS NULL")
    total_rows = a.num("SELECT COUNT(*) FROM usage_resolved")
    model_names = [r[0] for r in connect.query(a.cn, """
        SELECT DISTINCT m.name FROM usage_resolved v JOIN dim_model m
          ON m.model_id = v.model_id WHERE v.total_tokens IS NULL""")]
    a.check(missing_tokens == 0, "Every usage_resolved row carries tokens",
            f"{int(missing_tokens)}/{int(total_rows)} rows have calls but NO tokens"
            f" - SUM(total_tokens) drops them without warning. Models: {model_names}"
            f" (Monitoring has no token metric for embeddings)", WARN)

    for t in ("fact_perf_daily", "fact_latency_daily", "ref_budget", "ref_fx",
              "ref_price"):
        n = connect.count_rows(a.cn, t)
        a.check(n > 0, f"Table {t} has data", "0 dong", WARN)

    # Phân vị phải xếp đúng thứ tự, và p95 phải nằm trong ô được báo là chứa nó.
    # Cả hai là tính chất của PHÂN VỊ, không phụ thuộc dữ liệu - sai là ánh xạ
    # cột sai lúc nạp, mà lỗi đó không thể thấy bằng mắt.
    bad_pct = a.num("""SELECT COUNT(*) FROM fact_latency_daily
                       WHERE (p50_seconds > p95_seconds)
                          OR (p95_seconds > p99_seconds)
                          OR (p95_seconds < p95_bucket_from)
                          OR (p95_seconds > p95_bucket_to)""")
    a.check(bad_pct == 0, "Latency: p50<=p95<=p99 and p95 sits inside its own bucket",
            f"{int(bad_pct)} bad rows - the CSV column mapping is probably wrong")

    # Độ phủ độ trễ so với số lượt: hai phép đo này đến từ hai đường khác nhau
    # (histogram vs bộ đếm) nên phủ không bằng nhau là bình thường, nhưng phải
    # biết lệch bao nhiêu trước khi vẽ biểu đồ "daily latency".
    days_calls = a.num("SELECT COUNT(DISTINCT day) FROM fact_perf_daily")
    days_latency = a.num("SELECT COUNT(DISTINCT day) FROM fact_latency_daily")
    a.note(WARN if days_latency < days_calls else OK, "Latency coverage",
           f"{int(days_latency)} days with latency / {int(days_calls)} days with calls"
           if days_latency < days_calls else "")

    # AGENT KHAI LA DA DUNG NHUNG VAN CO LUU LUONG.
    #
    # `dim_agent.is_running` GO TAY co chu dich - no la ket luan nghiep vu, khong
    # suy ra bang nguong "how many days without data counts as stopped", vi
    # nguong nhu vay se phan loai sai moi khi mot agent nghi le dai (xem ghi chu
    # dau db/gen_catalog.py).
    #
    # Nhung go tay thi TROI, va troi im lang. Do 20/08/2026: Multi modal AI
    # Invoice duoc khai ngung tu 25/07, ma sau ngay do van co 452.096 token / 88
    # luot trai tren 6 ngay, ngay cuoi 17/08 - tuc ngay MOI NHAT cua ca database.
    #
    # Phep kiem nay khong tu sua co; no chi bat co va du lieu phai NOI CHUYEN voi
    # nhau. Ai doc con phai quyet: agent chay lai that, hay con mot tien trinh sot.
    # KHONG so voi `data_to`: cot do SUY TU CHINH DU LIEU, nen sau moi lan sinh
    # lai catalog no luon bang ngay cuoi, va dieu kien `v.day > data_to` thanh
    # vinh vien rong - mot phep kiem khong bao gio keu thi te hon la khong co,
    # vi no tao cam giac da duoc kiem.
    #
    # So voi NGAY CUOI CUA CA DATABASE. Mot agent ngung that thi du lieu cua no
    # phai dung TRUOC nhung agent khac; con dung dung ngay moi nhat thi co nghia
    # no van dang chay.
    dung_ma_van_chay = [(r[0], str(r[1])[:10], int(r[2] or 0)) for r in connect.query(a.cn, """
        SELECT g.name, MAX(v.day), SUM(v.calls)
        FROM dim_agent g JOIN usage_resolved v ON v.agent_id = g.agent_id
        WHERE g.is_running = FALSE
        GROUP BY g.name
        HAVING MAX(v.day) >= (SELECT MAX(day) FROM usage_resolved)
        ORDER BY g.name""")]
    a.check(not dung_ma_van_chay, "An agent marked stopped carries no more traffic",
            "; ".join(f"{n}: still has data up to {d} - use the newest day of the whole"
                      f" database, {c:,} calls in total"
                      for n, d, c in dung_ma_van_chay)
            + ". Hoac agent chay lai, hoac is_running da loi thoi", WARN)

    # Độ phủ chiều NGƯỜI, tách làm BA chứ không hai (sửa 20/08/2026).
    #
    # Bản trước chỉ đo `kind='real'` rồi gọi toàn bộ phần còn lại là "không quy
    # được". Nó gộp 6 agent một-người-dùng - nơi ta BIẾT chính xác ai dùng - vào
    # cùng rổ với phần Google thật sự không biết, làm lỗ hổng trông lớn gấp ~70
    # lần. Xem ghi chú `kind` ở db/migrations/sql/001_baseline.sql:166.
    #
    # Con số phải theo dõi là (c), và nó chỉ được TỐT LÊN, không được xấu đi.
    #
    # ĐẾM TRÊN usage_resolved, KHÔNG trên fact_usage_daily. Bảng đối chứng để ba
    # nguồn cạnh nhau, và tài khoản dịch vụ có token ở CẢ billing lẫn monitoring
    # nên cộng thẳng là đếm hai lần: đo 20/08/2026 ra 1.248.600.872/867.657.110
    # = 143,9%. Cộng riêng source='app' cũng vẫn lệch, vì gồm cả những ngày mà
    # view đã chọn billing thay cho app.
    cov = connect.query_one(a.cn, """
        SELECT
          SUM(CASE WHEN s.agent_id IS NULL AND v.token_source IN
                    (SELECT source FROM ref_source WHERE knows_user)
                   THEN v.total_tokens ELSE 0 END),
          SUM(CASE WHEN s.agent_id IS NOT NULL
                   THEN v.total_tokens ELSE 0 END),
          SUM(CASE WHEN s.agent_id IS NULL
                    AND COALESCE(v.token_source, '') <> 'app'
                   THEN v.total_tokens ELSE 0 END)
        FROM usage_resolved v
        LEFT JOIN (SELECT DISTINCT unit_agent_id AS agent_id FROM account
                    WHERE kind = 'service_account') s
               ON s.agent_id = v.agent_id""")
    real_tokens, svc_tokens, gap = (float(x or 0) for x in cov)
    view_tokens = a.num("SELECT SUM(total_tokens) FROM usage_resolved")
    pct = lambda v: 100.0 * v / view_tokens if view_tokens else 0.0

    # Ba nhóm PHẢI cộng đúng bằng tổng của view. Lệch nghĩa là câu trên hụt một
    # trường hợp - và nếu chỉ in ba tỷ lệ thì cái hụt đó không lộ ra.
    a.check(abs(real_tokens + svc_tokens + gap - view_tokens) < 1,
            "The three coverage groups add up to the total",
            f"{real_tokens + svc_tokens + gap:,.0f} != {view_tokens:,.0f}")
    a.note(WARN, "Coverage of the 'who used it' dimension",
           f"(a) real people {real_tokens:,.0f} = {pct(real_tokens):.1f}%"
           f" | (b) service accounts {svc_tokens:,.0f} = {pct(svc_tokens):.1f}%"
           f" | (c) UNATTRIBUTABLE {gap:,.0f} = {pct(gap):.1f}%"
           f" (the Google invoice only reports at project level)")

    # Số tài khoản dịch vụ phải bằng số agent KHÔNG có danh bạ người dùng. Suy ra
    # từ dữ liệu, KHÔNG ghim con số 6: thêm agent thứ 9 chỉ là thêm một dòng.
    #
    # Phép kiểm này còn một việc thứ hai: nó là thứ hỏng ỒN ÀO khi ai đó chạy
    # backend sau 20/08/2026 trên database dựng trước đó. Không có nó thì
    # health() lặng lẽ trả về con số độ phủ cũ, và con số cũ trông y như thật.
    n_svc = a.num("SELECT COUNT(*) FROM account WHERE kind = 'service_account'")
    n_no_dir = a.num("""SELECT COUNT(*) FROM dim_agent g
                        WHERE NOT EXISTS (SELECT 1 FROM dim_user d
                                          WHERE d.agent_id = g.agent_id
                                            AND d.found_in = 'directory')""")
    a.check(n_svc == n_no_dir, "Every agent without a directory has one service account",
            f"{int(n_svc)} service_account rows / {int(n_no_dir)} agents"
            f" khong co danh ba - database co the dung tu truoc 20/08/2026,"
            f" chay lai scripts/rebuild_db.py")

    # Ten dang nhap cua tai khoan dich vu phai la svc.<code> (quyet dinh A3,
    # chot 20/08/2026). Day KHONG phai quy uoc dat ten cho dep: ngay Gateway
    # chay, 6 agent mot-nguoi-dung gui len DUNG chuoi nay lam username. Lech mot
    # ky tu la Gateway gui len mot ten khong tra ra tai khoan nao, va dong do roi
    # vao "unattributable" MA KHONG LOI NAO BAO.
    sai_ten = [f"{u} (agent {c})" for u, c in connect.query(a.cn, """
        SELECT c.username, g.code FROM account c
          JOIN dim_agent g ON g.agent_id = c.unit_agent_id
         WHERE c.kind = 'service_account' AND c.username <> 'svc.' || g.code
         ORDER BY c.username""")]
    a.check(not sai_ten, "Service accounts are named svc.<code>",
            f"breaks convention A3: {sai_ten}")

    # LUOI AN TOAN THAY CHO VIEC CHO MOT TOKEN NHAN VIEN THUONG (quyet dinh
    # 21/08/2026). Hinh dang claim JWT do duoc tren tai khoan QUAN TRI: Ralli
    # dat username o claim `sub`, TLA HD dat o claim `username` (khong phai
    # `sub`). Chua chung minh duoc nhan vien thuong cung vay.
    #
    # Thay vi cho, kiem dieu nay: dong ky nguyen GATEWAY khong duoc roi vao cho
    # danh cho "unknown person". Roi vao do nghia la khau nap tra username khong
    # ra tai khoan va da lui ve mac dinh. Luoi nay bat duoc ca thu chua nghi ra:
    # agent trich nham claim, app doi claim sau mot lan nang cap, hoac ai do
    # viet `sub` cho ca hai app.
    #
    # LOC THEO era='gateway', KHONG THEO knows_user. Ban dau loc knows_user va
    # phep kiem keu ngay 21 dong - hoa ra dung: nguon 'app' BIET DUOC nguoi dung
    # nhung khong phai luc nao cung biet (nhat ky Ralli co luot khong kem user,
    # khau nap lui ve tai khoan __unattributed__ mot cach co chu y). "Nguon nay
    # co the mang danh tinh" khac "every row carries an identity". Chi ky nguyen
    # gateway moi duoc doi ve sau, vi A3 bao dam moi request mang danh tinh.
    lac = a.num("""
        SELECT COUNT(*) FROM fact_usage_daily f
          JOIN account c ON c.account_id = f.account_id
          JOIN ref_source r ON r.source = f.source
         WHERE r.era = 'gateway' AND c.kind IN ('unattributed', 'whole_agent')""")
    a.check(lac == 0, "Rows from a user-aware source all resolve to an account",
            f"{int(lac)} rows fell into 'unknown person' - the username sent"
            f" does not resolve to an account_id, see tu-dien-database.md 8f")

    # Tien cua Gateway KHONG vao cot cost_usd cua usage_resolved: no la so tu
    # nhan tu bang gia, khong phai hoa don. Xem ghi chu cost_usd trong
    # usage_resolved.
    #
    # PHEP KIEM NAY DA DOI NGHIA (31/08/2026). Ban dau no keu bat cu khi nao mot
    # nguon khong-hoa-don mang cost_usd, vi khi do so tien BIEN MAT khoi dashboard.
    # Tu khi Gateway chay that, dieu kien do dung MOI LAN CHAY - mot canh bao keu
    # mai mai la mot canh bao khong ai doc nua.
    #
    # Nhung tien khong con bien mat: dashboard tu nhan lai tu ref_price. Do
    # 31/08 tren luu luong Gateway that: dashboard suy ra $0,0213045, LiteLLM tu
    # tinh $0,0213050 - lech 5 phan trieu do, thuan lam tron.
    #
    # Nen doi thanh phep kiem MANH HON: hai bang gia doc lap co con khop khong.
    # No bat duoc hai hong that ma ban cu khong bat duoc:
    #   - model co tien luu ma KHONG co gia  -> tien that su bien mat
    #   - ref_price cu di so voi bang gia cua LiteLLM, hoac nguoc lai
    lech_gia = connect.query(a.cn, """
        SELECT f.source, m.name,
               SUM(f.cost_usd)                                              AS luu,
               SUM(f.input_tokens/1e6*p.price_input
                 + f.output_tokens/1e6*p.price_output)                      AS suy_ra
          FROM fact_usage_daily f
          JOIN ref_source r ON r.source = f.source
          JOIN dim_model  m ON m.model_id = f.model_id
          LEFT JOIN ref_price p ON p.model_id = f.model_id
         WHERE NOT r.has_invoice_cost AND f.cost_usd IS NOT NULL
         GROUP BY 1, 2
        HAVING SUM(f.input_tokens/1e6*p.price_input
                 + f.output_tokens/1e6*p.price_output) IS NULL
            OR ABS(SUM(f.cost_usd)
                 - SUM(f.input_tokens/1e6*p.price_input
                     + f.output_tokens/1e6*p.price_output))
               > GREATEST(SUM(f.cost_usd) * 0.01, 0.000001)""")
    a.check(not lech_gia, "Non-invoice cost is reproducible from ref_price",
            f"{len(lech_gia)} (source, model) pairs differ by >1% or lack a price: "
            f"{[(r[0], r[1]) for r in lech_gia][:4]}", WARN)

    # THEM 31/08/2026, cung ngay fact_call bat dau nhan ca luot HONG.
    #
    # Luot hong khong duoc dong gop token vao bang tong hop. Da do lo ro truoc khi
    # va: thieu bo loc `outcome` trong build_usage_daily thi token gateway ra
    # 45.201 thay vi 45.187 - ro dung 14 token cua mot luot hong.
    # MAU SO cho moi phep kiem gateway o duoi. Xem Audit.check_tren(): mot phep
    # kiem `COUNT(dong xau) == 0` tren 0 dong gateway se bao DAT, va no khong phan
    # biet "Gateway ghi dung" voi "Gateway khong ghi gi ca".
    gw_dong = a.num("SELECT COUNT(*) FROM fact_call WHERE source = 'gateway'")

    gw_agg = a.num("SELECT COALESCE(SUM(total_tokens), 0) FROM fact_usage_daily"
                   " WHERE source = 'gateway'")
    gw_ok = a.num("SELECT COALESCE(SUM(total_tokens), 0) FROM fact_call"
                  " WHERE source = 'gateway' AND outcome = 'success'"
                  "   AND model_id IS NOT NULL")
    a.check_tren(gw_dong, gw_agg == gw_ok, "Failed calls never reach the rollup",
            f"{int(gw_agg)} != {int(gw_ok)} - chenh {int(gw_agg - gw_ok)} token"
            f" tokens from failed calls reached fact_usage_daily")

    # Gia tri `outcome` la khac success/failure se bi build_usage_daily loai im
    # lang (no loc `= 'success'`). Bat o day de mat du lieu thanh mot phep kiem
    # do, thay vi mot con so tu nhien nho di ma khong ai giai thich duoc.
    outcome_la = a.num("SELECT COUNT(*) FROM fact_call"
                       " WHERE outcome IS NOT NULL"
                       "   AND outcome NOT IN ('success', 'failure')")
    a.check(outcome_la == 0, "No unknown outcome value",
            f"{int(outcome_la)} rows carry an outcome outside success/failure -"
            f" the rollup drops them without warning")

    # Luot TRUNG CACHE khong toi nha cung cap nen nha cung cap khong tinh tien
    # no - nhung Gateway VAN ghi du token (do 01/09: mot luot trung cache ghi
    # spend = 0 ma total_tokens = 352). Cong no vao luu luong la khai khong.
    #
    # So sanh nay cung bat luon CACH VIET SAI o build_usage_daily: neu ai do doi
    # `IS NOT TRUE` thanh `NOT cache_hit` thi 38/41 dong NULL bi vut va ve trai
    # tut xuong 0, phep kiem do.
    gw_cache = a.num("SELECT COALESCE(SUM(total_tokens),0) FROM fact_call"
                     " WHERE source='gateway' AND outcome='success'"
                     "   AND model_id IS NOT NULL AND cache_hit IS NOT TRUE")
    gw_bang = a.num("SELECT COALESCE(SUM(total_tokens),0) FROM fact_usage_daily"
                    " WHERE source='gateway'")
    a.check_tren(gw_dong, gw_cache == gw_bang, "Cache hits never reach the rollup",
            f"{int(gw_bang)} != {int(gw_cache)} - off by"
            f" {int(gw_bang - gw_cache)} token")

    # `raw_model` la BANG CHUNG DUY NHAT con lai khi `model_id` ra NULL. Thieu no
    # thi mot tuyen chua khai bien thanh mot dong trong ma khong tra nguoc duoc.
    thieu_raw = a.num("SELECT COUNT(*) FROM fact_call"
                      " WHERE source='gateway' AND raw_model IS NULL")
    a.check_tren(gw_dong, thieu_raw == 0, "Every gateway row has raw_model",
            f"{int(thieu_raw)} rows are missing the original model name")

    # Khoa la thu duy nhat tach duoc luu luong cua agent khoi luot di bang khoa
    # quan tri chung. Dong thieu khoa thi khong tach duoc bang gi.
    thieu_key = a.num("SELECT COUNT(*) FROM fact_call"
                      " WHERE source='gateway' AND virtual_key_id IS NULL")
    a.check_tren(gw_dong, thieu_key == 0, "Every gateway row has virtual_key_id",
            f"{int(thieu_key)} rows are missing the key identifier")

    # `duration_ms = 0` la "chua do", KHONG phai "do duoc 0 mili giay". Gateway
    # ghi 0 cho MOI luot hong, ke ca luot da goi toi nha cung cap va bi tu choi -
    # nen bo nap phai quy no ve NULL. Nap 0 vao la keo tut moi phan vi.
    do_tre_khong = a.num("SELECT COUNT(*) FROM fact_call WHERE duration_ms = 0")
    a.check(do_tre_khong == 0, "No row has duration_ms = 0",
            f"{int(do_tre_khong)} rows carry a 0 - must be NULL")

    # Model có lưu lượng mà không có giá thì mọi báo cáo chi phí đều thiếu nó.
    no_price = connect.query(a.cn, """
        SELECT m.name FROM dim_model m
        WHERE EXISTS (SELECT 1 FROM fact_usage_daily f WHERE f.model_id = m.model_id)
          AND NOT EXISTS (SELECT 1 FROM ref_price p WHERE p.model_id = m.model_id)""")
    a.check(not no_price, "Every model in use has a price",
            f"{len(no_price)} models missing: {[r[0] for r in no_price][:4]}", WARN)

    # Ngày tương lai = đồng hồ sai ở đâu đó trong chuỗi thu thập.
    #
    # HAI KHUYẾT TẬT ĐÃ SỬA 03/09/2026, cả hai đều nổ MUỘN
    # -----------------------------------------------------
    # (1) Bản cũ ghim ngưỡng `'2026-12-31'`. Sang 2027 thì mọi dòng dữ liệu THẬT
    #     đều bị coi là ngày tương lai - phép kiểm chuyển từ im lặng sang kêu ầm,
    #     không phải vì hệ thống hỏng. Nay lấy mốc từ CHÍNH NGÀY CHẠY.
    #
    # (2) Bản cũ chỉ soi `usage_resolved`. `fact_call` - nơi Gateway ghi TỪNG LƯỢT
    #     - không được soi, nên đồng hồ sai ở khâu nạp Gateway đi thẳng vào
    #     database mà không ai chặn.
    #
    # DUNG SAI MỘT NGÀY, KHÔNG PHẢI BẰNG KHÔNG. Quy ước dự án là mọi cột thời gian
    # theo GIỜ VIỆT NAM (chốt 14/08), mà `CURRENT_DATE` là ngày của máy chủ
    # database - hai đồng hồ có thể cách nhau tới 7 giờ. Một dòng của hôm nay
    # không được coi là tương lai chỉ vì lệch múi.
    BANG_CO_THOI_GIAN = [
        ("fact_call",          "ts_local"),   # tung luot goi - app va gateway
        ("fact_usage_daily",   "day"),
        ("fact_usage_hourly",  "hour"),
        ("fact_billing_daily", "day"),
        ("fact_monitoring",    "ts_local"),
    ]
    tuong_lai = []
    for bang, cot in BANG_CO_THOI_GIAN:
        n = a.num(f"SELECT COUNT(*) FROM {bang}"
                  f" WHERE {cot} IS NOT NULL"
                  f"   AND CAST({cot} AS DATE) > CURRENT_DATE + 1")
        if n:
            tuong_lai.append(f"{bang}.{cot}: {int(n)} rows")
    a.check(not tuong_lai,
            f"No future-dated rows ({len(BANG_CO_THOI_GIAN)} tables, threshold ="
            f" today + 1)",
            "; ".join(tuong_lai))

    n_conflict = a.num("SELECT COUNT(*) FROM account WHERE unit_conflict = 1")
    if n_conflict:
        a.note(WARN, "Accounts whose unit two apps declare differently",
               f"{int(n_conflict)} accounts - resolved by a deterministic rule,"
               f" see the unit_conflict column")
    else:
        a.note(OK, "Accounts whose unit two apps declare differently", "")


def group_f_hourly(a: Audit) -> None:
    """Bang theo gio va hai bang phan vi da co cot `source` (migration 008)."""

    # 9.1 Tong theo GIO phai bang tong theo NGAY - CHO TUNG NGUON.
    #
    # So theo tung nguon chu KHONG so tong: nguon `app` co HAI bang goc va chi
    # mot trong hai xuong duoc gio (Ralli o fact_call co ts_local; TLA Hop Dong
    # o fact_app_daily gop san theo ngay). Gop lai thanh mot con so la bien mot
    # su that da biet thanh mot bao dong gia - roi nguoi ta se tat phep kiem di.
    for src in ("gateway", "monitoring"):
        gio_tok = a.num("SELECT SUM(total_tokens) FROM fact_usage_hourly"
                        " WHERE source = %s", (src,))
        ngay_tok = a.num("SELECT SUM(total_tokens) FROM fact_usage_daily"
                         " WHERE source = %s", (src,))
        gio_calls = a.num("SELECT SUM(calls) FROM fact_usage_hourly"
                          " WHERE source = %s", (src,))
        ngay_calls = a.num("SELECT SUM(calls) FROM fact_usage_daily"
                           " WHERE source = %s", (src,))
        a.check(gio_tok == ngay_tok and gio_calls == ngay_calls,
                f"Hourly totals match daily totals ({src})",
                f"token {gio_tok:,.0f} vs {ngay_tok:,.0f} |"
                f" calls {gio_calls:,.0f} vs {ngay_calls:,.0f}")

    # Nguon `app`: chi phan fact_call xuong duoc gio. So voi CHINH phan do.
    gio_app = a.num("SELECT SUM(total_tokens) FROM fact_usage_hourly"
                    " WHERE source = 'app'")
    goc_app = a.num("SELECT SUM(total_tokens) FROM fact_call"
                    " WHERE source = 'app' AND model_id IS NOT NULL"
                    "   AND ts_local IS NOT NULL")
    a.check(gio_app == goc_app,
            "Hourly totals match the hour-capable part of `app`",
            f"{gio_app:,.0f} vs {goc_app:,.0f} in fact_call")

    # 9.2 `billing` KHONG duoc co mat. Hoa don Google chi tinh theo NGAY, nen
    # moi con so tien theo gio deu la bia - xem db/build_usage_hourly.py.
    n_bill = a.num("SELECT COUNT(*) FROM fact_usage_hourly"
                   " WHERE source = 'billing'")
    a.check(n_bill == 0, "No billing rows in the hourly table",
            f"{int(n_bill)} rows - Google chi xuat hoa don theo NGAY")

    # Moi gio phai cat dung ve dau gio. Mot dong 18:21:00 nghia la phep cat da
    # hong, va tong van khop nen khong phep kiem nao khac bat duoc.
    le_gio = a.num("SELECT COUNT(*) FROM fact_usage_hourly"
                   " WHERE EXTRACT(MINUTE FROM hour) <> 0"
                   "    OR EXTRACT(SECOND FROM hour) <> 0")
    a.check(le_gio == 0, "Every hourly row is truncated to the hour",
            f"{int(le_gio)} rows carry minutes or seconds")

    # 9.3 Moi dong gateway phai co `unit_id`. Cot nay la truong BAT BUOC cua
    # sheet Data Out, va no tung rong 0/41 truoc migration 007.
    gw_dong_f = a.num("SELECT COUNT(*) FROM fact_call WHERE source = 'gateway'")
    gw_thieu_unit = a.num("SELECT COUNT(*) FROM fact_call"
                          " WHERE source = 'gateway' AND unit_id IS NULL")
    a.check_tren(gw_dong_f, gw_thieu_unit == 0, "Every gateway row has unit_id",
            f"{int(gw_thieu_unit)} rows have no unit")

    # 9.4 Phan vi tinh tu SO THO khong duoc mang o histogram.
    #
    # Hai cot `p95_bucket_*` mo ta sai so cua phep NOI SUY trong mot o. So tho
    # khong co sai so do. Mot dong gateway mang o nghia la ai do da dan sai so
    # cua phep do KHAC len mot con so von khong co - va no trong y nhu that.
    gw_lat_dong = a.num("SELECT COUNT(*) FROM fact_latency_daily"
                        " WHERE source = 'gateway'")
    gw_co_o = a.num("SELECT COUNT(*) FROM fact_latency_daily"
                    " WHERE source = 'gateway'"
                    "   AND (p95_bucket_from IS NOT NULL"
                    "     OR p95_bucket_to IS NOT NULL)")
    a.check_tren(gw_lat_dong, gw_co_o == 0, "Raw percentiles have no histogram bucket",
            f"{int(gw_co_o)} gateway rows carry a bucket")

    # Nguoc lai: dong monitoring PHAI co o. Thieu o nghia la khau doc CSV da
    # tha mat cot, va p95 se trong nhu mot so chinh xac trong khi no khong phai.
    mon_thieu_o = a.num("SELECT COUNT(*) FROM fact_latency_daily"
                        " WHERE source = 'monitoring' AND p95_seconds IS NOT NULL"
                        "   AND p95_bucket_from IS NULL")
    a.check(mon_thieu_o == 0, "Interpolated percentiles keep their bucket",
            f"{int(mon_thieu_o)} monitoring rows lost their bucket")

    # Moi (ngay, agent, nguon) dung MOT dong. Hai dong nghia la khoa chinh cua
    # 008 khong lam viec va mot trong hai nguon dang bi ghi de im lang.
    trung = a.num("SELECT COUNT(*) FROM (SELECT day, agent_id, source"
                  " FROM fact_latency_daily GROUP BY 1,2,3 HAVING COUNT(*) > 1) t")
    a.check(trung == 0, "One latency row per (day, agent, source)",
            f"{int(trung)} keys appear twice")

    # `source` cua ca hai bang phai nam trong ref_source. Khoa ngoai da cuong
    # che, nhung phep kiem nay noi ra GIA TRI NAO dang co - de doc bao cao la
    # biet nguon nao da vao duoc, khong phai di truy van rieng.
    for bang in ("fact_latency_daily", "fact_perf_daily", "fact_usage_hourly"):
        co = ", ".join(f"{r[0]}={r[1]}" for r in connect.query(
            a.cn, f"SELECT source, COUNT(*) FROM {bang} GROUP BY 1 ORDER BY 1"))
        a.note(OK, f"{bang} by source", co)


def group_g_account_dimension(a: Audit) -> None:
    """Chieu tai khoan phu du 8 agent, va khong dem hai lan."""

    # HAI CON SO, KHONG PHAI MOT. Do 03/09: cach JOIN chi theo `token_source` cho
    # TOKEN khop TUYET DOI (lech 0) trong khi CALLS hut 77,9% (27.056/122.504).
    # Chi kiem token thi mot loi 78% van bao DAT - da xay ra that.
    for cot in ("total_tokens", "calls"):
        view = a.num(f"SELECT SUM({cot}) FROM usage_by_account_resolved")
        chuan = a.num(f"SELECT SUM({cot}) FROM usage_resolved")
        a.check(view == chuan, f"Account dimension totals match usage_resolved ({cot})",
                f"{view:,.0f} != {chuan:,.0f}")

    # Phu DU 8 agent. Duoi 8 nghia la mot dieu kien loc nao do da quay lai.
    n_agent = a.num("SELECT COUNT(DISTINCT agent_id) FROM usage_by_account_resolved")
    tong_agent = a.num("SELECT COUNT(*) FROM dim_agent WHERE agent_id IN"
                       " (SELECT DISTINCT agent_id FROM usage_resolved)")
    a.check(n_agent == tong_agent,
            "Account dimension covers every agent that has usage",
            f"{int(n_agent)}/{int(tong_agent)} agents")

    # `whole_agent` va `unattributed` PHAI con - chung la phan ta THAT SU khong
    # quy duoc ve tai khoan nao. Loc di la noi doi rang do phu bang 100%.
    for kind in ("whole_agent", "unattributed"):
        n = a.num("SELECT COUNT(*) FROM usage_by_account_resolved WHERE kind = %s",
                  (kind,))
        a.check(n > 0, f"Unattributable traffic stays visible ({kind})",
                f"0 rows - da bi loc mat, do phu se trong nhu 100%", WARN)

    # Moi dong phai quy ve MOT tai khoan co that trong bang `account`. View da
    # JOIN nen dieu nay duoc cuong che, nhung phep kiem noi ra CON SO - de doc
    # bao cao la biet, khong phai di truy van rieng.
    co = ", ".join(f"{r[0]}={r[1]:,}" for r in connect.query(a.cn, """
        SELECT kind, COUNT(*) FROM usage_by_account_resolved GROUP BY 1
         ORDER BY 2 DESC"""))
    a.note(OK, "Account dimension by kind", co)

    # CHEO KIEM voi cong thuc cua /api/health - mot duong tinh HOAN TOAN KHAC
    # (no di tu usage_resolved chu khong qua account). Hai duong doc lap ra cung
    # mot bo so la bang chung manh nhat co duoc ma khong can nguon thu ba.
    cap = [("real,unattributed", "people"), ("service_account", "service"),
           ("whole_agent", "opaque")]
    health = connect.query_one(a.cn, """
        SELECT SUM(CASE WHEN s.agent_id IS NOT NULL THEN v.total_tokens ELSE 0 END),
               SUM(CASE WHEN s.agent_id IS NULL AND v.token_source IN
                    (SELECT source FROM ref_source WHERE knows_user)
                   THEN v.total_tokens ELSE 0 END),
               SUM(CASE WHEN s.agent_id IS NULL AND COALESCE(v.token_source,'') NOT IN
                    (SELECT source FROM ref_source WHERE knows_user)
                   THEN v.total_tokens ELSE 0 END)
        FROM usage_resolved v
        LEFT JOIN (SELECT DISTINCT unit_agent_id AS agent_id FROM account
                    WHERE kind = 'service_account') s ON s.agent_id = v.agent_id""")
    health_map = {"service": float(health[0] or 0), "people": float(health[1] or 0),
                  "opaque": float(health[2] or 0)}
    for kinds, ten in cap:
        ds = ",".join(f"'{k}'" for k in kinds.split(","))
        v = a.num(f"SELECT SUM(total_tokens) FROM usage_by_account_resolved"
                  f" WHERE kind IN ({ds})")
        a.check(v == health_map[ten],
                f"Account dimension agrees with /api/health ({ten})",
                f"{v:,.0f} != {health_map[ten]:,.0f}")

    # View CU phai con nguyen: tools/baseline_db.py va tools/dien_tap_gateway.py
    # doc no lam moc lich su. Doi no la moi so mo cu khong so lai duoc.
    cu = a.num("SELECT COUNT(*) FROM usage_by_account")
    a.check(cu > 0, "The old per-person view is still readable",
            "usage_by_account tra 0 dong - hai cong cu o tools/ se gay")

    # ============ do tre: MOT dong cho moi (ngay, agent) ============
    #
    # `fact_latency_daily` co the co HAI dong cho cung mot khoa tu migration 008.
    # `latency_resolved` chon mot. Hai dong lot qua nghia la view chon hut, va
    # tang doc (api.js:187 gan de tren khoa khong co `source`) se hien mot con so
    # KHONG XAC DINH - dong den sau thang.
    trung_lat = a.num("""
        SELECT COUNT(*) FROM (SELECT day, agent_id FROM latency_resolved
                               GROUP BY 1, 2 HAVING COUNT(*) > 1) t""")
    a.check(trung_lat == 0, "One resolved latency row per (day, agent)",
            f"{int(trung_lat)} keys appear twice - view chon hut")

    # Khong duoc mat khoa nao: moi (ngay, agent) co trong bang phai co trong view.
    khoa_bang = a.num("SELECT COUNT(*) FROM (SELECT DISTINCT day, agent_id"
                      " FROM fact_latency_daily) t")
    khoa_view = a.num("SELECT COUNT(*) FROM latency_resolved")
    a.check(khoa_bang == khoa_view, "Resolved latency keeps every (day, agent)",
            f"view {int(khoa_view)} != bang {int(khoa_bang)}")

    # Nguon da chon phai tra ve mot bo so DAY DU - khong duoc tron p50 cua nguon
    # nay voi p95 cua nguon kia. Neu tron thi se co dong co p95 ma khong co p50.
    nua_voi = a.num("""
        SELECT COUNT(*) FROM latency_resolved
         WHERE (p95_seconds IS NULL) <> (p50_seconds IS NULL)""")
    a.check(nua_voi == 0, "Resolved latency takes every column from one source",
            f"{int(nua_voi)} rows have p95 without p50 (or the reverse)")

    co_lat = ", ".join(f"{r[0]}={r[1]}" for r in connect.query(
        a.cn, "SELECT latency_source, COUNT(*) FROM latency_resolved"
              " GROUP BY 1 ORDER BY 2 DESC"))
    a.note(OK, "Resolved latency by source", co_lat)

    # ====== BANG DAN XUAT CO BI BO LAI KHONG ======
    #
    # `scripts/refresh_gateway.py` la duong lam moi NHANH cho nguon gateway. Truoc
    # 03/09 no chi chay 2/4 buoc, nen `fact_usage_hourly` va phan gateway cua
    # `fact_latency_daily` cu di IM LANG sau moi lan refresh.
    #
    # Phep kiem "Hourly totals match daily totals" o tren BAT DUOC chuyen do,
    # nhung bat MUON: chi khi tong da lech, tuc da co du lieu moi bi bo lai. Moc
    # THOI GIAN lech som hon - ngay o luot goi dau tien cua mot ngay moi.
    #
    # PHAI SO TREN TAP DONG MA TANG TONG HOP NHAN, KHONG SO `MAX` THO
    # ---------------------------------------------------------------
    # Neu ngay moi nhat cua fact_call chi co luot HONG thi `MAX` tho lech mot cach
    # HOP LE, va ta vua them mot bao dong gia - ma bao dong gia thi se bi tat.
    #
    # VA HAI BANG DUNG HAI BO LOC KHAC NHAU, khong duoc dung chung mot cau:
    #     build_usage_hourly    outcome='success' · model_id IS NOT NULL · cache_hit IS NOT TRUE
    #     load_gateway_latency  duration_ms IS NOT NULL · cache_hit IS NOT TRUE
    #                           (KHONG loc outcome - co y, xem build_performance.py)
    #
    # CANH BAO cho nguoi sua sau: do 03/09, ca `MAX` tho lan hai `MAX` da loc deu
    # ra 2026-08-31 (3 luot hong nam luc 02:27, thanh cong keo toi 10:17). Nen SO
    # LIEU HOM NAY KHONG PHAN BIET DUOC hai cach cai. Doc bo loc, dung thu chay.
    gw_call_dong = a.num("SELECT COUNT(*) FROM fact_call WHERE source = 'gateway'")
    cu_hon = []
    for bang, cot, loc in (
        ("fact_usage_hourly", "CAST(hour AS DATE)",
         "outcome = 'success' AND model_id IS NOT NULL AND cache_hit IS NOT TRUE"),
        ("fact_latency_daily", "day",
         "duration_ms IS NOT NULL AND cache_hit IS NOT TRUE"),
    ):
        nguon = connect.query_one(a.cn, f"""
            SELECT MAX(CAST(ts_local AS DATE)) FROM fact_call
             WHERE source = 'gateway' AND ts_local IS NOT NULL AND {loc}""")[0]
        dan_xuat = connect.query_one(
            a.cn, f"SELECT MAX({cot}) FROM {bang} WHERE source = 'gateway'")[0]
        if nguon is not None and dan_xuat != nguon:
            cu_hon.append(f"{bang}: moc {dan_xuat} nhung fact_call co den {nguon}")
    a.check_tren(gw_call_dong, not cu_hon,
                 "Gateway derived tables are as fresh as fact_call",
                 "; ".join(cu_hon)
                 + " - gan nhu chac chan `refresh_gateway.py` da chay ma bo buoc."
                   " Chua: python scripts/refresh_gateway.py")

    # ====== so luot theo ma tra ve, nguon gateway ======
    #
    # Hom nay `fact_perf_daily` CHI co monitoring (669 dong); gateway, app va
    # billing deu 0 dong. Nen phep kiem nay chay tren mot TAP RONG - va no phai
    # noi ra dieu do thay vi bao DAT.
    #
    # Do cung la phep NGHIEM THU cua ca co che `check_tren()`: neu no bao DAT o
    # day thi co che khong lam viec, va moi phep kiem gateway khac deu dang noi
    # doi theo cung mot cach.
    gw_perf_dong = a.num("SELECT COUNT(*) FROM fact_perf_daily"
                         " WHERE source = 'gateway'")
    gw_perf_xau = a.num("""
        SELECT COUNT(*) FROM fact_perf_daily
         WHERE source = 'gateway'
           AND (method IS NULL OR method = ''
             OR response_code IS NULL OR response_code = '')""")
    a.check_tren(gw_perf_dong, gw_perf_xau == 0,
                 "Gateway rows in fact_perf_daily carry method and response_code",
                 f"{int(gw_perf_xau)} rows are missing method or response_code")


# Ngưỡng chấp nhận sai lệch khi đối chiếu token cache Gateway <-> hoá đơn Google.
#
# CHỐT TRƯỚC KHI CÓ SỐ ĐẦU TIÊN, và ghi rõ như vậy. Kỷ luật này do chính Master Plan
# đặt ra ở STT 7 dòng 19: *"ngưỡng chấp nhận sai lệch và quy trình xử lý khi vượt
# ngưỡng, BAN HÀNH TRƯỚC KỲ ĐO"*. Chốt sau khi thấy số là tự vẽ đích quanh mũi tên.
#
# VÌ SAO 1% CHỨ KHÔNG PHẢI 0: hai nguồn đếm ở hai thời điểm khác nhau trong đường
# gọi, và hoá đơn Google gộp theo ngày phía Mỹ trong khi ta coi mọi ngày là giờ Việt
# Nam. Đòi khớp tuyệt đối là đòi một thứ không nguồn nào hứa.
#
# CON SỐ NÀY CHƯA CÓ CƠ SỞ ĐO ĐẠC - chưa ngày nào hai nguồn cùng có dữ liệu để hiệu
# chỉnh. Nếu nó sai thì sẽ hỏng thành tiếng ở lần đo thật, và lúc đó sửa nó là một
# quyết định CÓ BẰNG CHỨNG. Nới nó trong im lặng thì không.
NGUONG_LECH_CACHE = 0.01


def group_h_cache_reconciliation(a: Audit) -> None:
    """Đối chiếu token cache của Gateway với SKU cache trên hoá đơn Google.

    STT 7 mục tiêu 2 của Master Plan đòi phép kiểm này. Đo 03/09/2026 thì nó CHƯA
    CHẠY ĐƯỢC, và lý do là dữ liệu chứ không phải công sức:

        ve GATEWAY   fact_call source='gateway'         41 dong · cached_tokens 0/41
        ve HOA DON   fact_billing_daily kind='cached'  461 dong · 252.321.118 token
                                                       214 ngay · 6 agent
        so ngay ca hai nguon CUNG co du lieu:  0
            gateway  31/08 -> 31/08     billing  01/01 -> 29/08

    VIẾT PHÉP KIỂM NGAY BÂY GIỜ DÙ CHƯA CHẠY ĐƯỢC. Ngày hai nguồn giao nhau, nó phải
    ĐÃ SẴN Ở ĐÓ - viết sau nghĩa là ngày đó không ai nhớ, và cửa sổ so sánh trôi qua.
    Đúng như cửa sổ lưu giữ của Cloud Monitoring đã trôi mất ba tháng dữ liệu.

    VÀ TUYỆT ĐỐI KHÔNG BÁO ĐẠT TRÊN TẬP RỖNG. Đó là cách dễ nhất để tick xanh một mục
    Master Plan bằng một phép kiểm chưa từng kiểm gì.
    """
    gw_ngay = connect.query_one(a.cn, """
        SELECT MIN(ts_local)::date, MAX(ts_local)::date, COUNT(DISTINCT ts_local::date)
        FROM fact_call WHERE source = 'gateway'""")
    bl_ngay = connect.query_one(a.cn, """
        SELECT MIN(day), MAX(day), COUNT(DISTINCT day)
        FROM fact_billing_daily WHERE kind = 'cached'""")

    # Ngay CA HAI nguon cung co du lieu. Chi so tren dung nhung ngay nay - so hai
    # khoang thoi gian khac nhau roi ket luan la cai bay da mac hai lan (change 006
    # voi do tre, va chinh muc nay voi cached_tokens).
    chung = connect.query(a.cn, """
        SELECT ts_local::date AS ngay FROM fact_call WHERE source = 'gateway'
        INTERSECT
        SELECT day FROM fact_billing_daily WHERE kind = 'cached'
        ORDER BY 1""")

    if not chung:
        a.note(WARN, "Gateway cache tokens match the invoice cache SKU",
               f"CHUA KIEM DUOC - khong ngay nao ca hai nguon cung co du lieu."
               f" gateway {gw_ngay[0]} -> {gw_ngay[1]} ({gw_ngay[2]} ngay) ·"
               f" hoa don {bl_ngay[0]} -> {bl_ngay[1]} ({bl_ngay[2]} ngay)."
               f" Day KHONG phai ket qua dat.")
        return

    ds = ", ".join(f"'{r[0]}'" for r in chung)
    gw_co = a.num(f"""
        SELECT COUNT(cached_tokens) FROM fact_call
         WHERE source = 'gateway' AND ts_local::date IN ({ds})""")
    if gw_co == 0:
        a.note(WARN, "Gateway cache tokens match the invoice cache SKU",
               f"CHUA KIEM DUOC - co {len(chung)} ngay chung, nhung ve GATEWAY rong:"
               f" 0 dong co cached_tokens. NULL KHONG duoc coi la 0."
               f" Day KHONG phai ket qua dat.")
        return

    # Ca hai ve co so -> so tung (ngay, agent), ap nguong.
    lech = connect.query(a.cn, f"""
        WITH g AS (SELECT ts_local::date AS ngay, agent_id,
                          COALESCE(SUM(cached_tokens), 0) AS tok
                     FROM fact_call
                    WHERE source = 'gateway' AND ts_local::date IN ({ds})
                    GROUP BY 1, 2),
             b AS (SELECT day AS ngay, agent_id, COALESCE(SUM(quantity), 0) AS tok
                     FROM fact_billing_daily
                    WHERE kind = 'cached' AND day IN ({ds})
                    GROUP BY 1, 2)
        SELECT COALESCE(g.ngay, b.ngay), COALESCE(g.agent_id, b.agent_id),
               COALESCE(g.tok, 0), COALESCE(b.tok, 0)
        FROM g FULL OUTER JOIN b ON b.ngay = g.ngay AND b.agent_id = g.agent_id
        ORDER BY 1, 2""")
    xau = []
    for ngay, aid, gtok, btok in lech:
        mau = max(float(gtok), float(btok))
        if mau == 0:
            continue
        ty_le = abs(float(gtok) - float(btok)) / mau
        if ty_le > NGUONG_LECH_CACHE:
            xau.append(f"{ngay} agent {aid}: gateway {int(gtok):,}"
                       f" vs hoa don {int(btok):,} ({ty_le:.1%})")
    a.check_tren(len(lech), not xau,
                 f"Gateway cache tokens match the invoice cache SKU"
                 f" (nguong {NGUONG_LECH_CACHE:.0%}, {len(chung)} ngay chung)",
                 "; ".join(xau[:5]) + (" ..." if len(xau) > 5 else ""))


def group_i_provider_reconciliation(a: Audit) -> None:
    """Đối chiếu sổ Gateway với sổ NHÀ CUNG CẤP, theo ngày, trên cả ba trục.

    VÌ SAO CẦN
    ----------
    Sổ Gateway tự nó nhất quán: tổng khớp tổng, giờ khớp ngày, không phép kiểm nội
    bộ nào đỏ. Nên lỗi NẰM TRONG nó không lộ ra bằng cách nhìn vào nó - chỉ ý kiến
    thứ hai mới thấy. Đo 04/09/2026 trên dữ liệu 31/08/2026:

        truc          nha cung cap   fact_call    lech
        so luot             41            41          0
        token vao       47.613        41.679      5.934
        token ra         3.922         3.522        400
                                                 ------
                                                  6.334   = 12,29%

    Nhà cung cấp báo 41 lượt, `response_code = 200` cho TẤT CẢ, không một lỗi nào.
    Sổ Gateway ghi 5 lượt hỏng. Hai trong số đó đã được phục vụ xong và đã tiêu
    token thật. Ta loại lượt hỏng khỏi bảng tổng hợp - điều đó đúng - nhưng phần bị
    loại KHÔNG bằng không. Tên gọi của hình dạng lỗi: `failed_is_not_free`.

    VÌ SAO SO Ở MỨC NGÀY, KHÔNG MỨC GIỜ
    -----------------------------------
    Nhà cung cấp gắn nhãn ô theo THỜI ĐIỂM KẾT THÚC, sổ Gateway ghi theo THỜI ĐIỂM
    BẮT ĐẦU. Đo 04/09 thì giờ 01h lệch −12 còn giờ 02h lệch +5.864 - một phần của
    con số đó chỉ là ranh giới ô chứ không phải lỗi. Ở mức ngày ranh giới ô biến
    mất, trừ đúng nửa đêm.

    HAI CHIỀU LỆCH KHÔNG CÙNG MỘT NGHĨA
    -----------------------------------
        nha cung cap > fact_call   -> LƯU Ý kèm số. Đây là chiều KỲ VỌNG: sổ ta bỏ
                                      sót thì bỏ sót về phía thiếu. Báo hỏng chiều
                                      này thì phép kiểm đỏ vĩnh viễn rồi bị bỏ qua.
        fact_call > nha cung cap   -> HỎNG. Ta không thể tiêu thứ họ không phục vụ.

    KHÔNG CÓ NGƯỠNG PHẦN TRĂM CHO CHIỀU THIẾU HỤT, VÀ ĐÓ LÀ CHỦ Ý. Ta ĐÃ BIẾT kết
    quả là 12,21%, nên đặt ngưỡng bây giờ là chọn con số vừa khít với đáp án - trái
    đúng kỷ luật "ban hành ngưỡng trước kỳ đo" mà `gateway-cache-reconciliation` đã
    chốt. Phép kiểm in con số ra; ngưỡng để sau, khi có nhiều hơn một ngày.

    NẾU CHIỀU HỎNG NỔ Ở TRỤC SỐ LƯỢT
    --------------------------------
    Giả thuyết đầu tiên phải thử: một lượt bị proxy từ chối TRƯỚC khi tới nhà cung
    cấp (sai khoá, quá hạn mức) vẫn là một dòng trong `fact_call` mà nhà cung cấp
    không hề thấy. Đó là lời GIẢI THÍCH, không phải cái cớ để nới phép kiểm - ghi
    bằng chứng lại, đừng hạ ngưỡng.
    """
    NHAN = "Gateway ledger agrees with the provider's own count"

    # Project nào là điểm quan sát của Gateway? Project đó KHÔNG THUỘC AGENT NÀO -
    # đúng lý lẽ ở migration 011 khi để `provider_project` là TEXT trần.
    #
    # Lọc là BẮT BUỘC chứ không phải phòng xa: `scripts/pull_monitoring.py` mặc
    # định kéo cả 7 project sản xuất, và `db/load_provider.py` nạp mọi thứ có
    # trong đợt kéo. Cộng gộp tất cả rồi so với riêng lưu lượng Gateway là so hai
    # tập khác nhau - và lệch ra sẽ trông y hệt một phát hiện thật.
    #
    # `IS NOT NULL` trong truy vấn con không thừa: `NOT IN` gặp một NULL là cả vị
    # từ thành NULL, danh sách rỗng, và phép kiểm im lặng bỏ qua mọi thứ.
    du_an = [r[0] for r in connect.query(a.cn, """
        SELECT DISTINCT provider_project
          FROM fact_provider_daily
         WHERE provider_project NOT IN (SELECT gcp_project_id FROM dim_agent
                                         WHERE gcp_project_id IS NOT NULL)
         ORDER BY 1""")]
    if not du_an:
        tong_dong = a.num("SELECT COUNT(*) FROM fact_provider_daily")
        a.note(WARN, NHAN,
               f"CHUA KIEM DUOC - so nha cung cap co {int(tong_dong)} dong nhung"
               f" khong project nao nam ngoai dim_agent, tuc chua co dot keo nao"
               f" cho project cua Gateway. Day KHONG phai ket qua dat.")
        return

    ngay_gw = connect.query_one(a.cn, """
        SELECT MIN(ts_local)::date, MAX(ts_local)::date,
               COUNT(DISTINCT ts_local::date)
          FROM fact_call WHERE source = 'gateway'""")
    ngay_ncc = connect.query_one(a.cn, """
        SELECT MIN(day), MAX(day), COUNT(DISTINCT day)
          FROM fact_provider_daily WHERE provider_project = ANY(%s)""", (du_an,))

    # Ngày CẢ HAI sổ cùng có dữ liệu. So hai khoảng thời gian khác nhau rồi kết
    # luận là cái bẫy dự án này đã mắc hai lần: change 006 với độ trễ, và mục
    # cache với `cached_tokens`.
    chung = [r[0] for r in connect.query(a.cn, """
        SELECT ts_local::date FROM fact_call WHERE source = 'gateway'
        INTERSECT
        SELECT day FROM fact_provider_daily WHERE provider_project = ANY(%s)
        ORDER BY 1""", (du_an,))]
    if not chung:
        a.note(WARN, NHAN,
               f"CHUA KIEM DUOC - khong ngay nao ca hai so cung co du lieu."
               f" gateway {ngay_gw[0]} -> {ngay_gw[1]} ({int(ngay_gw[2] or 0)} ngay) ·"
               f" nha cung cap {ngay_ncc[0]} -> {ngay_ncc[1]}"
               f" ({int(ngay_ncc[2] or 0)} ngay, {len(du_an)} project)."
               f" Day KHONG phai ket qua dat.")
        return

    # NULL = CHƯA ĐO, khác hẳn 0 = ĐÃ ĐO VÀ BẰNG KHÔNG. `SUM()` bỏ qua NULL, nên
    # một trục chưa đo được sẽ lặng lẽ cộng ra con số NHỎ HƠN sự thật - và nhỏ hơn
    # ở vế nhà cung cấp thì đẩy thẳng phép kiểm sang chiều HỎNG. Loại trục đó ra,
    # và NÓI RA là đã loại.
    #
    # Khoá theo TÊN TRỤC chứ không so chuỗi mô tả: bản đầu tiên viết
    # `m.startswith(ten)` trên câu mô tả, và cách đó chỉ đúng chừng nào không tên
    # trục nào là tiền tố của tên trục khác - một điều kiện không ai bảo đảm cho
    # lần thêm trục sau.
    khong_do: dict = {}          # ngay -> {ten truc: [ly do]}
    for ngay, r0, i0, o0 in connect.query(a.cn, """
        SELECT day,
               COUNT(*) FILTER (WHERE requests      IS NULL),
               COUNT(*) FILTER (WHERE input_tokens  IS NULL),
               COUNT(*) FILTER (WHERE output_tokens IS NULL)
          FROM fact_provider_daily
         WHERE provider_project = ANY(%s) AND day = ANY(%s)
         GROUP BY 1""", (du_an, chung)):
        for ten, n in (("so luot", r0), ("token vao", i0), ("token ra", o0)):
            if n:
                khong_do.setdefault(ngay, {}).setdefault(ten, []).append(
                    f"nha cung cap {n} dong NULL")
    for ngay, p0, c0 in connect.query(a.cn, """
        SELECT ts_local::date,
               COUNT(*) FILTER (WHERE prompt_tokens     IS NULL),
               COUNT(*) FILTER (WHERE completion_tokens IS NULL)
          FROM fact_call
         WHERE source = 'gateway' AND ts_local::date = ANY(%s)
         GROUP BY 1""", (chung,)):
        for ten, n in (("token vao", p0), ("token ra", c0)):
            if n:
                khong_do.setdefault(ngay, {}).setdefault(ten, []).append(
                    f"gateway {n} dong NULL")

    doi = connect.query(a.cn, """
        WITH g AS (
            SELECT ts_local::date AS ngay, COUNT(*)::bigint AS luot,
                   COALESCE(SUM(prompt_tokens), 0)     AS tok_vao,
                   COALESCE(SUM(completion_tokens), 0) AS tok_ra
              FROM fact_call
             WHERE source = 'gateway' AND ts_local::date = ANY(%s)
             GROUP BY 1),
             p AS (
            SELECT day AS ngay,
                   COALESCE(SUM(requests), 0)      AS luot,
                   COALESCE(SUM(input_tokens), 0)  AS tok_vao,
                   COALESCE(SUM(output_tokens), 0) AS tok_ra
              FROM fact_provider_daily
             WHERE provider_project = ANY(%s) AND day = ANY(%s)
             GROUP BY 1)
        SELECT g.ngay, g.luot, g.tok_vao, g.tok_ra, p.luot, p.tok_vao, p.tok_ra
          FROM g JOIN p ON p.ngay = g.ngay
         ORDER BY 1""", (chung, du_an, chung))

    # (ten truc, chi so ve GATEWAY, chi so ve NHA CUNG CAP) trong mỗi dòng trên.
    # BA trục chứ không một: khớp số lượt mà lệch token là đúng hình dạng lỗi
    # `failed_is_not_free` - 31/08 khớp 41/41 lượt trong khi lệch 6.334 token. Chỉ
    # kiểm một trục là bỏ lọt chính cái lỗi sinh ra phép kiểm này.
    TRUC = (("so luot", 1, 4), ("token vao", 2, 5), ("token ra", 3, 6))

    hong, thieu_hut, da_so = [], [], 0
    for dong in doi:
        ngay = dong[0]
        bo_qua = khong_do.get(ngay, {})
        for ten, ig, ip in TRUC:
            if ten in bo_qua:
                continue
            gw, ncc = float(dong[ig]), float(dong[ip])
            da_so += 1
            if gw > ncc:
                hong.append(f"{ngay} {ten}: fact_call {int(gw):,}"
                            f" > nha cung cap {int(ncc):,}"
                            f" (thua {int(gw - ncc):,})")
            elif ncc > gw:
                ty_le = (ncc - gw) / ncc if ncc else 0.0
                thieu_hut.append(f"{ngay} {ten}: nha cung cap {int(ncc):,}"
                                 f" vs fact_call {int(gw):,}"
                                 f" (thieu {int(ncc - gw):,} = {ty_le:.2%})")

    a.check_tren(da_so, not hong,
                 f"{NHAN} ({len(chung)} ngay, {len(du_an)} project)",
                 "; ".join(hong[:8])
                 + (f" ... con {len(hong) - 8} truc-ngay nua" if len(hong) > 8 else ""))

    # KHÔNG ngưỡng, và KHÔNG bao giờ HỎNG - xem docstring. In con số ra để người
    # đọc tự thấy độ lớn; ngưỡng chỉ được ban hành khi có nhiều hơn một ngày.
    if thieu_hut:
        a.note(WARN, f"Provider counts more than the gateway ledger"
                     f" ({len(thieu_hut)}/{da_so} truc-ngay tren {len(chung)} ngay)",
               "; ".join(thieu_hut[:6]) + (" ..." if len(thieu_hut) > 6 else ""))

    if khong_do:
        a.note(WARN, f"Provider reconciliation skipped unmeasured axes"
                     f" ({len(khong_do)} ngay)",
               "; ".join(f"{ngay}: " + ", ".join(f"{ten} ({'/'.join(ly_do)})"
                                                 for ten, ly_do in sorted(m.items()))
                         for ngay, m in sorted(khong_do.items())))

    _hoa_don_cung_mui_gio_voi_cong_to(a)


def _hoa_don_cung_mui_gio_voi_cong_to(a: Audit) -> None:
    """Hoá đơn Google và công tơ Google phải khớp - SAU KHI quy về cùng múi giờ.

    VÌ SAO CẦN
    ----------
    `fact_billing_daily.day` là ngày theo giờ **US/Pacific**: `merge_billing.py:251`
    lấy nguyên cột `Date` của file xuất Cloud Billing, không đổi múi giờ ở đâu cả.
    `fact_monitoring.ts_local` là giờ **Việt Nam** thật. Chốt 14/08 là COI ngày hoá
    đơn như ngày VN, và chấp nhận chuỗi theo ngày của riêng nguồn billing lệch tới
    15 giờ - xem docstring `db/build_usage_daily.py` mục (a).

    Quy đúng múi giờ rồi thì hai nguồn là CÙNG MỘT CÔNG TƠ. Đo 11/09/2026:

        gia thuyet          cap   trung khit      lech / token
        quy ve Pacific      397      356 (90%)          0,20%
        de nguyen gio VN    365       13 ( 4%)         81,3%

    GIỜ BIÊN LÀ ĐO ĐƯỢC, KHÔNG PHẢI ĐOÁN
    ------------------------------------
    Quét cả 24 giờ biên khả dĩ (12/09/2026), giờ 14 thắng áp đảo và không mập mờ:

        gio bien   trung khit / cap   lech
            14        358 / 401       0,24%
            13        173 / 395       9,27%
            15        167 / 396      13,73%
            12        148 / 395      16,93%

    VN là UTC+7, biên ngày ở VN 14:00 nghĩa là ngày hoá đơn bắt đầu lúc **UTC−7**.

    Tên *"Pacific"* thì là SUY RA, từ hai chỗ khớp nhau: UTC−7 trong tháng 4 tới 8
    đúng là PDT, và file hoá đơn là bản xuất tay từ **Google Cloud Console** (xem
    `scripts/merge_billing.py` docstring - BigQuery export bị chặn ở quyền), mà
    Console báo cáo theo giờ Thái Bình Dương.

    CHỖ CHƯA ĐO ĐƯỢC, VÀ PHÉP KIỂM NÀY SẼ TỰ HỎI VÀO THÁNG 11
    ---------------------------------------------------------
    Dữ liệu token của monitoring chỉ có từ 24/04/2026, tức **toàn mùa PDT**: 0 dòng
    trước 08/03. Nên chưa phân biệt được hai khả năng cho ra cùng kết quả mùa hè:

        America/Los_Angeles   UTC-7 mua he, UTC-8 mua dong  -> bien doi sang VN 15:00
        mot do lech CO DINH   UTC-7 quanh nam               -> bien van o VN 14:00

    Truy vấn dưới dùng `America/Los_Angeles`, nên nó CHỌN khả năng thứ nhất. Nếu
    thật ra là độ lệch cố định thì phép kiểm sẽ **đỏ vào tháng 11** - và đó là kết
    cục đúng, không phải phiền toái: nó hỏi hộ ta một câu chưa ai trả lời được, vào
    đúng lúc dữ liệu trả lời được. Ai thấy nó đỏ tháng 11 thì thử lại biên VN 14:00
    trước khi nghi dữ liệu.

    KHÔNG ĐẶT NGƯỠNG, SO HAI GIẢ THUYẾT
    -----------------------------------
    Cùng kỷ luật với phần trên: ta ĐÃ BIẾT đáp án là 0,20%, nên đặt ngưỡng bây giờ
    là chọn con số vừa khít với đáp án. Thay vào đó phép kiểm hỏi một câu nhị phân
    **không cần ngưỡng**: quy về Pacific có lệch ít hơn để nguyên giờ VN không?
    Hôm nay chênh nhau 313 lần, nên câu hỏi này dư sức sống sót mọi dao động dữ
    liệu - nó chỉ đỏ khi quan hệ múi giờ thật sự đổi.

    NÓ ĐỎ KHI NÀO
    -------------
    Google đổi múi giờ file xuất hoá đơn · ai đó dịch cột `day` · một trong hai
    nguồn mất dữ liệu diện rộng. Cả ba đều là thứ phải biết ngay, và cả ba đều
    không lộ ra bằng cách nhìn vào riêng một nguồn.

    `AT TIME ZONE` hai lần chứ không trừ một hằng số: lệch là 14 giờ trong PDT
    nhưng 15 giờ trong PST, nên bù cứng sẽ sai bốn tháng mỗi năm.

    Bỏ ngày ĐẦU và ngày CUỐI của monitoring: cửa sổ lưu giữ của Cloud Monitoring
    trượt nên hai ngày biên luôn khuyết, và một phép kiểm đỏ vĩnh viễn thì bị bỏ
    qua - đúng cái bẫy docstring nhóm này đã cảnh báo.
    """
    NHAN = "Billing and the provider meter agree once the timezone is undone"
    r = connect.query_one(a.cn, """
        WITH mon AS (
            SELECT (m.ts_local AT TIME ZONE 'Asia/Ho_Chi_Minh'
                               AT TIME ZONE 'America/Los_Angeles')::date AS ngay_pac,
                   m.ts_local::date AS ngay_vn, m.project, m.value
              FROM fact_monitoring m
              JOIN dim_metric_alias d
                ON d.source = 'monitoring' AND d.raw_name = m.metric_type
             WHERE d.measures = 'token' AND d.kind = 'output'
               AND m.model_id IS NOT NULL
        ), bien AS (SELECT MIN(ngay_pac) AS d1, MAX(ngay_pac) AS d2 FROM mon),
        pac AS (SELECT ngay_pac AS ngay, project, SUM(value) AS token
                  FROM mon, bien WHERE ngay_pac > d1 AND ngay_pac < d2 GROUP BY 1, 2),
        vn  AS (SELECT ngay_vn  AS ngay, project, SUM(value) AS token
                  FROM mon, bien WHERE ngay_vn  > d1 AND ngay_vn  < d2 GROUP BY 1, 2),
        bil AS (SELECT day AS ngay, project, SUM(quantity) AS token
                  FROM fact_billing_daily WHERE kind = 'output' GROUP BY 1, 2)
        SELECT (SELECT COUNT(*) FROM pac p JOIN bil b USING (ngay, project)),
               (SELECT COUNT(*) FILTER (WHERE b.token = p.token)
                  FROM pac p JOIN bil b USING (ngay, project)),
               (SELECT SUM(ABS(b.token - p.token))
                  FROM pac p JOIN bil b USING (ngay, project)),
               (SELECT SUM(ABS(b.token - v.token))
                  FROM vn  v JOIN bil b USING (ngay, project)),
               (SELECT SUM(p.token) FROM pac p JOIN bil b USING (ngay, project))
    """)
    cap, khit, lech_pac, lech_vn, tong = [float(x or 0) for x in (r or (0,) * 5)]

    # `tong` có thể bằng 0 khi database mới dựng: chia cho 0 thì phép kiểm chết
    # thay vì báo "chưa kiểm được", mà `check_tren` sinh ra chính để tránh thế.
    ty_le = (lech_pac / tong) if tong else 0.0
    a.check_tren(cap, lech_pac < lech_vn,
                 f"{NHAN} ({int(cap)} cap ngay-project, {int(khit)} trung khit,"
                 f" lech {ty_le:.2%})",
                 f"quy ve Pacific lech {int(lech_pac):,} token,"
                 f" de nguyen gio VN lech {int(lech_vn):,} - quan he mui gio da doi")


# Nhip mac dinh, chi dung khi KHONG doc duoc nhip that. Xem `read_refresh_interval()`.
DEFAULT_INTERVAL_SECONDS = 300   # khop .env.example va docker-compose.yml, doi 12/09/2026


def read_refresh_interval(cn) -> tuple[int, int, str]:
    """Tra (interval_seconds, stale_threshold, nguon_cua_con_so).

    NGUONG = 3 x nhip + 60 giay bien. Ba chu ky de mot lan lam moi hong khong lam
    do ngay; bien 60 giay cho thoi gian chinh mot chu ky chay (do 09/09/2026:
    2.348 ms tren 444 dong nguon, nhung no tang theo so dong).

    NHIP DOC TU `ref_load_run.every_seconds` TRUOC, bien moi truong chi la duong
    lui. Vi sao thu tu do quan trong: bien moi truong thi MOI TIEN TRINH THAY MOT
    GIA TRI KHAC. Dat REFRESH_EVERY_SECONDS=300 trong `.env` thi dich vu chay
    300s, nhung nguoi chay `python scripts/audit_db.py` trong mot shell khong co
    bien do se lay 120 -> nguong 420s thay vi 960s -> BAO DONG GIA moi lan chay.
    `every_seconds` la nhip ma tien trinh THUC SU dang chay, nen khong lech duoc.

    Duong lui dung `or` chu khong `os.environ.get(k, mac_dinh)`: bien dat thanh
    CHUOI RONG cung phai roi ve mac dinh -- cung quy uoc voi db/connect.py.
    `int("")` nem ValueError.

    Bang co the chua ton tai (database dung truoc migration 012), nen bat
    Exception: thieu nhip tim KHONG duoc lam ca luot audit chet.
    """
    try:
        r = connect.query_one(
            cn, "SELECT every_seconds FROM ref_load_run WHERE source = 'gateway'")
    except Exception:                             # noqa: BLE001
        r = None
    if r and r[0]:
        interval = int(r[0])
        source = "ref_load_run.every_seconds"
    else:
        interval = int(os.environ.get("REFRESH_EVERY_SECONDS") or DEFAULT_INTERVAL_SECONDS)
        source = "bien moi truong / mac dinh"
    return interval, 3 * interval + 60, source


def group_j_gateway_row_accounting(a: Audit) -> None:
    """Mọi dòng sổ nguồn phải VÀO ĐƯỢC `fact_call`, hoặc bị bỏ CÓ TÊN.

    VÌ SAO CẦN
    ----------
    `db/load_gateway.py` báo "read 47 rows | usable 41". Sáu dòng chênh kia đi
    đâu là câu hỏi mà chính bộ nạp trả lời - nên nếu chỉ tin bộ nạp, ta đang lấy
    lời khai của bị cáo làm bằng chứng. Nhóm này TỰ TÍNH LẠI từ sổ nguồn, bằng
    câu SQL của riêng nó, rồi so với `fact_call`.

    BA KẾT CỤC, KHÔNG PHẢI HAI
    --------------------------
        dong co dung mot tag dinh danh, DA co trong fact_call   -> dat
        dong bi bo VI MOT LY DO GOI TEN DUOC                    -> LƯU Ý kem so
        dong khong vao, cung khong co ly do nao                 -> HONG

    Chỉ kết cục thứ ba mới là HỎNG, và đó KHÔNG phải nới lỏng: nó nhắm đúng thứ
    cần bắt - dòng biến mất mà không ai giải thích được. Đòi `COUNT(*)` hai vế
    bằng nhau thì phép kiểm đỏ vĩnh viễn vì một lý do đã biết trước
    (`fact_call.agent_id` là NOT NULL, dòng không có tag định danh KHÔNG THỂ lưu),
    và một phép kiểm đỏ vĩnh viễn là một phép kiểm bị bỏ qua.

    ĐO 05/09/2026 TRÊN TOÀN SỔ
    --------------------------
        doc tu so                          47 dong
        vao duoc fact_call                 41 dong
        bo - khong co tag dinh danh         5 dong ·   408 token
        bo - ban sao cua cu cache hit       1 dong ·   352 token
                                          ----------------------
        khong giai thich duoc               0 dong

    NĂM DÒNG KIA LÀ MỘT KHOẢN NỢ, KHÔNG PHẢI MỘT KẾT LUẬN. Trong đó có
    `lG-UarHhIYXmosUPv4ihmQ8` - một lượt THÀNH CÔNG, 25 token, người dùng
    `tuan.tran`, mà sổ ta không giữ được vì tag của nó chỉ có `User-Agent:`.
    Lưu lượng không quy được về ai cũng không phải lưu lượng miễn phí - cùng đúng
    một hình dạng lỗi với `failed_is_not_free`, chỉ khác trục.
    """
    NHAN = "Every source row is either loaded or dropped for a named reason"

    interval_seconds, stale_threshold, interval_source = read_refresh_interval(a.cn)
    ma_agent = [r[0] for r in connect.query(a.cn, "SELECT code FROM dim_agent")]
    da_nap = {r[0] for r in connect.query(a.cn, """
        SELECT call_id FROM fact_call WHERE source = 'gateway'""")}

    # Sổ nguồn là database KHÁC. Không với tới được thì đó là "chưa kiểm được",
    # KHÔNG phải "đạt" - và cũng không phải cớ để audit sập.
    try:
        gw, _ = connect.open_db(connect.GATEWAY_DSN)
    except Exception as e:                        # noqa: BLE001
        a.note(WARN, NHAN,
               f"CHUA KIEM DUOC - khong mo duoc so nguon"
               f" ({connect.mask_dsn(connect.GATEWAY_DSN)}): {type(e).__name__}."
               f" Day KHONG phai ket qua dat.")
        return

    try:
        # `request_tags` là **jsonb**, không phải `text[]` - nên `unnest()` sẽ
        # lỗi kiểu ở đây. Phải đi qua `jsonb_array_elements_text`, và phải chặn
        # trường hợp cột NULL hoặc không phải mảng, nếu không cả dòng biến mất
        # khỏi kết quả mà không báo gì.
        #
        # Tag định danh = tag KHỚP MỘT DÒNG `dim_agent.code`. Không phải "tag đầu
        # tiên", cũng không phải "tag không bắt đầu bằng User-Agent:" - xem BẪY 3
        # ở db/load_gateway.py.
        nguon = connect.query(gw, """
            SELECT request_id,
                   ("startTime" + interval '7 hours')::date AS ngay,
                   COALESCE(total_tokens, 0) AS tok,
                   request_id LIKE %s AS ban_sao,
                   (SELECT COUNT(*)
                      FROM jsonb_array_elements_text(
                             CASE WHEN jsonb_typeof(request_tags) = 'array'
                                  THEN request_tags ELSE '[]'::jsonb END) AS t
                     WHERE t = ANY(%s)) AS so_tag,
                   -- Tuoi cua dong, tinh bang giay. `startTime` la `timestamp
                   -- without time zone` va database chay o UTC (da chung minh o
                   -- db/load_gateway.py muc MUI GIO), nen phai ep `now()` ve UTC
                   -- truoc khi tru -- khong thi lech 7 gio va MOI dong trong nhu
                   -- vua moi ghi. Do 09/09/2026: dong vua goi ra 60 giay, dong
                   -- cach do 3 tieng ra 10.748 giay.
                   EXTRACT(EPOCH FROM (now() AT TIME ZONE 'UTC'
                                       - "startTime"))::bigint AS tuoi_giay
              FROM "LiteLLM_SpendLogs"
             WHERE status IS NOT NULL
             ORDER BY "startTime" """, (r"%\_cache\_hit%", ma_agent))
    finally:
        gw.close()

    nen_nap, bo_khong_tag, bo_nhieu_tag, bo_ban_sao = [], [], [], []
    age_by_id = {}
    for rid, ngay, tok, ban_sao, so_tag, age in nguon:
        age_by_id[rid] = int(age)
        if ban_sao:
            bo_ban_sao.append((rid, ngay, int(tok)))
        elif so_tag == 1:
            nen_nap.append((rid, ngay, int(tok)))
        elif so_tag == 0:
            bo_khong_tag.append((rid, ngay, int(tok)))
        else:
            bo_nhieu_tag.append((rid, ngay, int(tok)))

    # HỎNG: dòng lẽ ra nạp được mà không có trong `fact_call`. Không lý do nào.
    #
    # NHƯNG PHẢI TRỪ ĐI NHỮNG DÒNG CHƯA ĐẾN LƯỢT (thêm 09/09/2026)
    # ------------------------------------------------------------
    # Đường làm mới chạy theo nhịp, nên giữa hai lượt LUÔN có dòng vừa ghi mà
    # chưa kịp nạp. Dòng ấy KHÔNG mất - nó đang trên đường.
    #
    # Đo được 09/09/2026, trước khi có đoạn này: gọi một lượt thật rồi chạy audit
    # sau 12 giây -> `[ FAIL ] 1 dong nap duoc nhung VANG trong fact_call`, trong
    # khi hệ thống chạy hoàn hảo và nhịp làm mới là 120 giây. Với dịch vụ chạy
    # liên tục thì tình trạng ấy gần như THƯỜNG TRỰC, và chính docstring trên đã
    # nói: *một phép kiểm đỏ vĩnh viễn là một phép kiểm bị bỏ qua*.
    #
    # Đây KHÔNG phải nới lỏng phép kiểm. Phép kiểm cũ đo sai thứ: nó gọi "mất"
    # một dòng chưa hề có cơ hội được nạp. Chia hai mới là đo đúng - và dung sai
    # có TRẦN, suy từ nhịp, nên một dòng mất thật vẫn HỎNG sau vài phút.
    not_loaded = [x for x in nen_nap if x[0] not in da_nap]
    in_flight = [x for x in not_loaded if age_by_id[x[0]] <= stale_threshold]
    mat = [x for x in not_loaded if age_by_id[x[0]] > stale_threshold]

    # ĐỘ TRỄ = tuổi của dòng NẠP ĐƯỢC cũ nhất chưa vào sổ. Không đo bằng hiệu hai
    # mốc `max()`: mốc mới nhất của sổ nguồn có thể là một dòng BỊ BỎ CÓ TÊN
    # (không tag định danh, hoặc bản sao cache-hit), và so với nó thì phép kiểm
    # báo hỏng oan mãi mãi. Chỉ so trên `nen_nap` - đúng tập dòng mà bộ nạp nhận.
    lag_seconds = max((age_by_id[x[0]] for x in not_loaded), default=0)
    # Và chiều ngược lại cũng phải kiểm: dòng có trong `fact_call` mà sổ nguồn
    # không còn - nghĩa là ta đang giữ một bản ghi không ai xác nhận được nữa.
    thua = sorted(da_nap - {x[0] for x in nen_nap})

    loi = []
    if mat:
        loi.append(f"{len(mat)} dong nap duoc, qua nguong {stale_threshold}s"
                   f" (= 3 x nhip {interval_seconds}s + 60s bien, nhip doc tu"
                   f" {interval_source}),"
                   f" ma VANG trong fact_call: "
                   + ", ".join(f"{r[0][:24]} ({r[1]}, {r[2]} token)"
                               for r in mat[:5])
                   + (f" ... +{len(mat) - 5}" if len(mat) > 5 else ""))
    if thua:
        loi.append(f"{len(thua)} dong co trong fact_call ma so nguon khong con: "
                   + ", ".join(t[:24] for t in thua[:5])
                   + (f" ... +{len(thua) - 5}" if len(thua) > 5 else ""))

    a.check_tren(len(nguon), not loi,
                 f"{NHAN} ({len(da_nap)} dong da nap, tre {lag_seconds}s"
                 f"/nguong {stale_threshold}s)",
                 " · ".join(loi))

    # Dòng đang trên đường: hiện ra kèm SỐ, nhưng không phải hỏng. Im lặng ở đây
    # thì không ai phân biệt được "đường làm mới đang chạy, hơi trễ" với "đường
    # làm mới đã chết mà chưa quá ngưỡng".
    if in_flight:
        tok = sum(x[2] for x in in_flight)
        # `lag_seconds` la tuoi cua dong cu nhat trong CA `not_loaded` - ke ca dong da
        # MAT. Dung no o day thi thong bao TU MAU THUAN: co mot dong mat 500s va
        # mot dong dang bay 30s thi no in "cu nhat 500s <= nguong 420s", sai ngay
        # tren mat chu. Phai lay tuoi cu nhat CUA CHINH nhom dang bay.
        oldest_in_flight = max(age_by_id[x[0]] for x in in_flight)
        a.note(WARN, f"Source rows still in flight"
                     f" ({len(in_flight)} dong, {tok:,} token,"
                     f" cu nhat {oldest_in_flight}s <= nguong {stale_threshold}s)",
               ", ".join(f"{r[0][:24]} ({r[1]}, {age_by_id[r[0]]}s)"
                         for r in in_flight[:6])
               + (f" ... +{len(in_flight) - 6}" if len(in_flight) > 6 else ""))

    # Phần bị bỏ CÓ LÝ DO: không phải hỏng, nhưng phải hiện ra kèm token. Đếm số
    # dòng thôi là mời người đọc tự điền "chắc chẳng đáng bao nhiêu".
    for nhom, ten in ((bo_khong_tag,  "no identity tag"),
                      (bo_nhieu_tag,  "several identity tags"),
                      (bo_ban_sao,    "cache-hit duplicate row")):
        if not nhom:
            continue
        tok = sum(x[2] for x in nhom)
        a.note(WARN, f"Source rows dropped: {ten}"
                     f" ({len(nhom)} dong, {tok:,} token)",
               ", ".join(f"{r[0][:24]} ({r[1]}, {r[2]} token)" for r in nhom[:6])
               + (f" ... +{len(nhom) - 6}" if len(nhom) > 6 else ""))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=connect.DEFAULT_DSN)
    args = p.parse_args()

    cn, _ = open_read_only(args.db)
    a = Audit(cn)
    for title, fn in (("A. Structure", group_a_structure),
                      ("B. Totals", group_b_totals),
                      ("C. Classification", group_c_classification),
                      ("D. Silent gaps", group_d_silent_gaps),
                      ("E. Adoption", group_e_adoption),
                      ("F. Hourly and source", group_f_hourly),
                      ("G. Account dimension", group_g_account_dimension),
                      ("H. Cache reconciliation", group_h_cache_reconciliation),
                      ("I. Provider reconciliation",
                       group_i_provider_reconciliation),
                      ("J. Gateway row accounting",
                       group_j_gateway_row_accounting)):
        print(f"\n{title}\n{'─' * 72}")
        start = len(a.results)
        fn(a)
        for level, label, detail in a.results[start:]:
            mark = {OK: "  ok  ", WARN: " note ", FAIL: " FAIL "}[level]
            print(f"[{mark}] {label}")
            if detail:
                print(f"           {detail}")

    failed = [r for r in a.results if r[0] == FAIL]
    warned = [r for r in a.results if r[0] == WARN]
    print(f"\n{'═' * 72}")
    print(f"{len(a.results)} checks | {len(a.results) - len(failed) - len(warned)} passed"
          f" | {len(warned)} notes | {len(failed)} failed")
    if failed:
        print("FAILED:")
        for _, label, detail in failed:
            print(f"  {label}: {detail}")
        sys.exit(1)
    print("Structure is CLEAN. The 'note' entries are known data gaps, not defects.")


if __name__ == "__main__":
    main()
