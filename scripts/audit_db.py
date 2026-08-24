"""Soi toàn bộ database một lượt: cấu trúc, số khớp, phân loại, lỗ im lặng.

    python scripts/audit_db.py
    python scripts/audit_db.py --db "postgresql://token:token_local@localhost:5432/token_ledger"

CHỈ ĐỌC. Không ghi, không sửa, không xoá - mở SQLite bằng mode=ro để điều đó
được hệ điều hành bảo đảm chứ không phải bằng lời hứa trong tài liệu.

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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "db"))

import connect  # noqa: E402

OK, WARN, FAIL = "DAT", "CANH BAO", "HONG"


def open_read_only(dsn: str):
    """Như connect.open_db nhưng SQLite mở ở chế độ chỉ đọc thật sự."""
    if connect.is_sqlite(dsn):
        import sqlite3
        p = Path(dsn).resolve().as_posix()
        return sqlite3.connect(f"file:{p}?mode=ro", uri=True), "?"
    return connect.open_db(dsn)


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


# (bảng con, cột con, bảng cha, cột cha)
FOREIGN_KEYS = [
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
    # liet ke o day vi ban SQLite khong bat khoa ngoai, va vi database dung tu
    # schema truoc 21/08/2026 khong co rang buoc nay.
    ("fact_usage_daily", "source", "ref_source", "source"),
    ("fact_usage_daily", "account_id", "account", "account_id"),
    ("fact_usage_daily", "model_id", "dim_model", "model_id"),
    ("fact_usage_daily", "agent_id", "dim_agent", "agent_id"),
    ("fact_perf_daily", "agent_id", "dim_agent", "agent_id"),
    ("fact_latency_daily", "agent_id", "dim_agent", "agent_id"),
]


def group_a_structure(a: Audit) -> None:
    """Khoá ngoại, cây đơn vị, khoá trống."""
    # PRAGMA foreign_key_check chỉ có ở SQLite. LEFT JOIN chạy cả hai hệ và còn
    # nói rõ bảng nào cột nào, thay vì một danh sách rowid.
    dangling = []
    for child, col, parent, key in FOREIGN_KEYS:
        n = a.num(f"""SELECT COUNT(*) FROM {child} c
                      LEFT JOIN {parent} p ON p.{key} = c.{col}
                      WHERE c.{col} IS NOT NULL AND p.{key} IS NULL""")
        if n:
            dangling.append(f"{child}.{col} -> {parent}: {int(n)} dong")
    a.check(not dangling, f"Khoa ngoai ({len(FOREIGN_KEYS)} quan he)",
            "; ".join(dangling))

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
    a.check(not cycles, "Cay don vi khong co vong lap",
            f"{len(cycles)} dong: {cycles[:3]}")
    a.check(not bad_level, "Cot `level` khop do sau that",
            f"{len(bad_level)} dong: {bad_level[:3]}")

    # Một tài khoản một đơn vị - khuyết tật đã sửa 14/08. Đối chiếu ngược: đơn vị
    # được chọn phải là một trong những đơn vị mà chính dim_user của nó khai,
    # không được là đơn vị bịa ra do lấy nhầm chỉ số trong tuple.
    invented = a.num("""SELECT COUNT(*) FROM account x
                        WHERE x.kind = 'real'
                          AND NOT EXISTS (SELECT 1 FROM dim_user u
                                          WHERE u.account_id = x.account_id
                                            AND u.unit_id = x.unit_id)""")
    a.check(invented == 0, "Don vi cua tai khoan do nguon khai",
            f"{int(invented)} tai khoan co don vi khong nguon nao noi")


def group_b_totals(a: Audit) -> None:
    """Tiền và token phải bằng nhau qua mọi tầng tổng hợp."""
    src_cost = a.num("SELECT SUM(cost_usd) FROM fact_billing_daily")
    view_cost = a.num("SELECT SUM(cost_usd) FROM usage_resolved")
    a.check(abs(src_cost - view_cost) < 1e-4, "Tien: hoa don == usage_resolved",
            f"${src_cost:.6f} != ${view_cost:.6f}")

    # Nguồn 'app' có HAI bảng gốc: Ralli qua fact_call (từng lượt gọi), TLA HĐ
    # qua fact_app_daily (app chỉ phơi số đã gộp). Cả hai đều lọc
    # model_id IS NOT NULL cho khớp điều kiện mà build_usage_daily dùng - dòng
    # không biết model không vào được fact_usage_daily vì model_id nằm trong khoá.
    call_tokens = a.num("SELECT SUM(total_tokens) FROM fact_call"
                        " WHERE model_id IS NOT NULL")
    hd_tokens = a.num("SELECT SUM(total_tokens) FROM fact_app_daily"
                      " WHERE model_id IS NOT NULL")
    app_tokens = a.num("SELECT SUM(total_tokens) FROM fact_usage_daily"
                       " WHERE source='app'")
    a.check(call_tokens + hd_tokens == app_tokens,
            "Token app: fact_call + fact_app_daily == fact_usage_daily",
            f"{call_tokens:,.0f} + {hd_tokens:,.0f} != {app_tokens:,.0f}")

    src_tokens = a.num("SELECT SUM(quantity) FROM fact_billing_daily")
    billing_tokens = a.num("SELECT SUM(total_tokens) FROM fact_usage_daily"
                           " WHERE source='billing'")
    a.check(src_tokens == billing_tokens, "Token hoa don: goc == fact_usage_daily",
            f"{src_tokens:,.0f} != {billing_tokens:,.0f}")

    # usage_resolved phải là MỘT dòng cho mỗi (day, agent, model). Nhiều hơn là
    # view đang nhân bản dòng - tức mọi tổng đọc từ nó đều to lên âm thầm.
    n_rows = a.num("SELECT COUNT(*) FROM usage_resolved")
    n_keys = a.num("SELECT COUNT(*) FROM (SELECT DISTINCT day, agent_id, model_id"
                   " FROM usage_resolved) x")
    a.check(n_rows == n_keys, "usage_resolved: mot khoa mot dong",
            f"{int(n_rows)} dong nhung chi {int(n_keys)} khoa")

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
    a.check(double_counted == 0, "usage_resolved lay nguyen so cua nguon da chon",
            f"{int(double_counted)} dong co so khac nguon no khai")


def group_c_classification(a: Audit) -> None:
    """Mọi tên lạ phải có trong bảng alias, không được rơi vào im lặng."""
    unknown_metric = a.num("""SELECT COUNT(DISTINCT m.metric_type) FROM fact_monitoring m
                              LEFT JOIN dim_metric_alias d
                                ON d.source='monitoring' AND d.raw_name = m.metric_type
                              WHERE d.raw_name IS NULL""")
    a.check(unknown_metric == 0, "Moi metric_type co trong dim_metric_alias",
            f"{int(unknown_metric)} phep do la")

    unknown_sku = a.num("""SELECT COUNT(DISTINCT b.sku_id) FROM fact_billing_daily b
                           LEFT JOIN dim_metric_alias d
                             ON d.source='billing_sku' AND d.raw_name = b.sku_id
                           WHERE d.raw_name IS NULL""")
    a.check(unknown_sku == 0, "Moi sku_id co trong dim_metric_alias",
            f"{int(unknown_sku)} SKU la")

    unknown_sku_model = a.num("""SELECT COUNT(DISTINCT b.sku_id) FROM fact_billing_daily b
                                 LEFT JOIN dim_model_alias d
                                   ON d.source='billing_sku' AND d.raw_name = b.sku_id
                                 WHERE d.raw_name IS NULL""")
    a.check(unknown_sku_model == 0, "Moi sku_id co trong dim_model_alias",
            f"{int(unknown_sku_model)} SKU la")

    # `is_quota_limit` là bản sao của dim_metric_alias.measures='quota_limit' nằm
    # trong bảng sự kiện. Bản sao thì có thể lệch - phép kiểm này là lý do duy
    # nhất để còn giữ cả hai.
    mismatch = a.num("""SELECT COUNT(*) FROM fact_monitoring f
                        JOIN dim_metric_alias d
                          ON d.source='monitoring' AND d.raw_name = f.metric_type
                        WHERE (CASE WHEN f.is_quota_limit THEN 1 ELSE 0 END)
                           <> (CASE WHEN d.measures='quota_limit' THEN 1 ELSE 0 END)""")
    a.check(mismatch == 0, "is_quota_limit khop dim_metric_alias",
            f"{int(mismatch)} dong mau thuan")


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
    a.check(not no_denominator, "Moi agent co mau so cho ty le ap dung",
            f"khong xac dinh duoc mau so: {no_denominator}")

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
    a.check(over == 0, "Ty le ap dung khong vuot 100%",
            f"{int(over)} agent co tu so > mau so")

    # fact_app_daily: khoá tự nhiên phải duy nhất. Trùng nghĩa là khâu kéo gộp
    # hụt, và hậu quả là token bị đếm hai lần khi đổ về fact_usage_daily.
    dup = a.num("""SELECT COUNT(*) FROM (
        SELECT day, agent_id, account_id, raw_model, COUNT(*) AS n
        FROM fact_app_daily GROUP BY day, agent_id, account_id, raw_model
        HAVING COUNT(*) > 1) x""")
    a.check(dup == 0, "fact_app_daily: mot (ngay, tai khoan, model) mot dong",
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
    a.check(outside == 0, "Nguoi co dung deu con trong danh ba",
            f"{int(outside)} tai khoan co phat sinh request nhung khong con trong"
            f" danh ba - khong tinh vao tu so", WARN)

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
    a.check(not idle, "Tai khoan co dung deu nhan dang duoc la nguoi",
            f"{len(idle)} tai khoan co request nhung khong ho ten khong email:"
            f" {idle} - kha nang la tai khoan he thong, xem SHARED_EXACT"
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
    a.check(missing_tokens == 0, "Moi dong usage_resolved deu co token",
            f"{int(missing_tokens)}/{int(total_rows)} dong co luot ma KHONG co token"
            f" - SUM(total_tokens) bo qua chung khong bao. Model: {model_names}"
            f" (Monitoring khong co phep do token cho embedding)", WARN)

    for t in ("fact_perf_daily", "fact_latency_daily", "ref_budget", "ref_fx",
              "ref_price"):
        n = connect.count_rows(a.cn, t)
        a.check(n > 0, f"Bang {t} co du lieu", "0 dong", WARN)

    # Phân vị phải xếp đúng thứ tự, và p95 phải nằm trong ô được báo là chứa nó.
    # Cả hai là tính chất của PHÂN VỊ, không phụ thuộc dữ liệu - sai là ánh xạ
    # cột sai lúc nạp, mà lỗi đó không thể thấy bằng mắt.
    bad_pct = a.num("""SELECT COUNT(*) FROM fact_latency_daily
                       WHERE (p50_seconds > p95_seconds)
                          OR (p95_seconds > p99_seconds)
                          OR (p95_seconds < p95_bucket_from)
                          OR (p95_seconds > p95_bucket_to)""")
    a.check(bad_pct == 0, "Do tre: p50<=p95<=p99 va p95 nam trong o cua no",
            f"{int(bad_pct)} dong sai - kha nang anh xa cot CSV nham")

    # Độ phủ độ trễ so với số lượt: hai phép đo này đến từ hai đường khác nhau
    # (histogram vs bộ đếm) nên phủ không bằng nhau là bình thường, nhưng phải
    # biết lệch bao nhiêu trước khi vẽ biểu đồ "độ trễ theo ngày".
    days_calls = a.num("SELECT COUNT(DISTINCT day) FROM fact_perf_daily")
    days_latency = a.num("SELECT COUNT(DISTINCT day) FROM fact_latency_daily")
    a.note(WARN if days_latency < days_calls else OK, "Do phu do tre",
           f"{int(days_latency)} ngay co do tre / {int(days_calls)} ngay co so luot"
           if days_latency < days_calls else "")

    # AGENT KHAI LA DA DUNG NHUNG VAN CO LUU LUONG.
    #
    # `dim_agent.is_running` GO TAY co chu dich - no la ket luan nghiep vu, khong
    # suy ra bang nguong "bao nhieu ngay khong co du lieu thi coi la ngung", vi
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
    a.check(not dung_ma_van_chay, "Agent khai da dung thi khong con luu luong",
            "; ".join(f"{n}: van co du lieu toi {d} - dung ngay moi nhat cua ca"
                      f" database, tong {c:,} luot"
                      for n, d, c in dung_ma_van_chay)
            + ". Hoac agent chay lai, hoac is_running da loi thoi", WARN)

    # Độ phủ chiều NGƯỜI, tách làm BA chứ không hai (sửa 20/08/2026).
    #
    # Bản trước chỉ đo `kind='real'` rồi gọi toàn bộ phần còn lại là "không quy
    # được". Nó gộp 6 agent một-người-dùng - nơi ta BIẾT chính xác ai dùng - vào
    # cùng rổ với phần Google thật sự không biết, làm lỗ hổng trông lớn gấp ~70
    # lần. Xem ghi chú `kind` ở db/01_schema.sql.
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
            "Ba nhom do phu cong dung bang tong",
            f"{real_tokens + svc_tokens + gap:,.0f} != {view_tokens:,.0f}")
    a.note(WARN, "Do phu chieu 'ai dung'",
           f"(a) nguoi that {real_tokens:,.0f} = {pct(real_tokens):.1f}%"
           f" | (b) tai khoan dich vu {svc_tokens:,.0f} = {pct(svc_tokens):.1f}%"
           f" | (c) KHONG quy duoc {gap:,.0f} = {pct(gap):.1f}%"
           f" (hoa don Google chi bao muc project)")

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
    a.check(n_svc == n_no_dir, "Moi agent khong co danh ba co mot tai khoan dich vu",
            f"{int(n_svc)} tai khoan service_account / {int(n_no_dir)} agent"
            f" khong co danh ba - database co the dung tu truoc 20/08/2026,"
            f" chay lai scripts/rebuild_db.py")

    # Ten dang nhap cua tai khoan dich vu phai la svc.<code> (quyet dinh A3,
    # chot 20/08/2026). Day KHONG phai quy uoc dat ten cho dep: ngay Gateway
    # chay, 6 agent mot-nguoi-dung gui len DUNG chuoi nay lam username. Lech mot
    # ky tu la Gateway gui len mot ten khong tra ra tai khoan nao, va dong do roi
    # vao "khong quy duoc" MA KHONG LOI NAO BAO.
    sai_ten = [f"{u} (agent {c})" for u, c in connect.query(a.cn, """
        SELECT c.username, g.code FROM account c
          JOIN dim_agent g ON g.agent_id = c.unit_agent_id
         WHERE c.kind = 'service_account' AND c.username <> 'svc.' || g.code
         ORDER BY c.username""")]
    a.check(not sai_ten, "Tai khoan dich vu dat ten svc.<code>",
            f"lech quy uoc A3: {sai_ten}")

    # LUOI AN TOAN THAY CHO VIEC CHO MOT TOKEN NHAN VIEN THUONG (quyet dinh
    # 21/08/2026). Hinh dang claim JWT do duoc tren tai khoan QUAN TRI: Ralli
    # dat username o claim `sub`, TLA HD dat o claim `username` (khong phai
    # `sub`). Chua chung minh duoc nhan vien thuong cung vay.
    #
    # Thay vi cho, kiem dieu nay: dong ky nguyen GATEWAY khong duoc roi vao cho
    # danh cho "khong biet ai". Roi vao do nghia la khau nap tra username khong
    # ra tai khoan va da lui ve mac dinh. Luoi nay bat duoc ca thu chua nghi ra:
    # agent trich nham claim, app doi claim sau mot lan nang cap, hoac ai do
    # viet `sub` cho ca hai app.
    #
    # LOC THEO era='gateway', KHONG THEO knows_user. Ban dau loc knows_user va
    # phep kiem keu ngay 21 dong - hoa ra dung: nguon 'app' BIET DUOC nguoi dung
    # nhung khong phai luc nao cung biet (nhat ky Ralli co luot khong kem user,
    # khau nap lui ve tai khoan __unattributed__ mot cach co chu y). "Nguon nay
    # co the mang danh tinh" khac "moi dong deu co danh tinh". Chi ky nguyen
    # gateway moi duoc doi ve sau, vi A3 bao dam moi request mang danh tinh.
    lac = a.num("""
        SELECT COUNT(*) FROM fact_usage_daily f
          JOIN account c ON c.account_id = f.account_id
          JOIN ref_source r ON r.source = f.source
         WHERE r.era = 'gateway' AND c.kind IN ('unattributed', 'whole_agent')""")
    a.check(lac == 0, "Dong tu nguon biet nguoi dung deu quy duoc ve tai khoan",
            f"{int(lac)} dong roi vao cho 'khong biet ai' - username gui len"
            f" khong tra ra account_id, xem tu-dien-database.md 8f")

    # Tien cua Gateway KHONG vao cot cost_usd cua usage_resolved: no la so tu
    # nhan tu bang gia, khong phai hoa don. Ai chen dong gateway kem cost_usd se
    # thay so tien do BIEN MAT khoi dashboard ma khong loi nao bao - nen phai keu
    # o day. Xem ghi chu cost_usd trong usage_resolved.
    tien_bo = a.num("""
        SELECT COUNT(*) FROM fact_usage_daily f
          JOIN ref_source r ON r.source = f.source
         WHERE NOT r.has_invoice_cost AND f.cost_usd IS NOT NULL""")
    a.check(tien_bo == 0, "Khong nguon nao mang tien ma view bo qua",
            f"{int(tien_bo)} dong co cost_usd tu nguon khong phai hoa don -"
            f" so tien nay KHONG hien tren dashboard", WARN)

    # Model có lưu lượng mà không có giá thì mọi báo cáo chi phí đều thiếu nó.
    no_price = connect.query(a.cn, """
        SELECT m.name FROM dim_model m
        WHERE EXISTS (SELECT 1 FROM fact_usage_daily f WHERE f.model_id = m.model_id)
          AND NOT EXISTS (SELECT 1 FROM ref_price p WHERE p.model_id = m.model_id)""")
    a.check(not no_price, "Model dang dung deu co gia",
            f"{len(no_price)} model thieu: {[r[0] for r in no_price][:4]}", WARN)

    # Ngày tương lai = đồng hồ sai ở đâu đó trong chuỗi thu thập.
    future = a.num("SELECT COUNT(*) FROM usage_resolved"
                   " WHERE CAST(day AS TEXT) > '2026-12-31'")
    a.check(future == 0, "Khong co ngay tuong lai", f"{int(future)} dong")

    n_conflict = a.num("SELECT COUNT(*) FROM account WHERE unit_conflict = 1")
    if n_conflict:
        a.note(WARN, "Tai khoan co don vi bi hai app khai khac nhau",
               f"{int(n_conflict)} tai khoan - da chon theo quy tac tat dinh,"
               f" xem cot unit_conflict")
    else:
        a.note(OK, "Tai khoan co don vi bi hai app khai khac nhau", "")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=connect.DEFAULT_DSN)
    args = p.parse_args()

    cn, _ = open_read_only(args.db)
    a = Audit(cn)
    for title, fn in (("A. Cau truc", group_a_structure),
                      ("B. So khop", group_b_totals),
                      ("C. Phan loai", group_c_classification),
                      ("D. Lo im lang", group_d_silent_gaps),
                      ("E. Ty le ap dung", group_e_adoption)):
        print(f"\n{title}\n{'─' * 72}")
        start = len(a.results)
        fn(a)
        for level, label, detail in a.results[start:]:
            mark = {OK: "  ok  ", WARN: " luu y", FAIL: " HONG "}[level]
            print(f"[{mark}] {label}")
            if detail:
                print(f"           {detail}")

    failed = [r for r in a.results if r[0] == FAIL]
    warned = [r for r in a.results if r[0] == WARN]
    print(f"\n{'═' * 72}")
    print(f"{len(a.results)} phep kiem | {len(a.results) - len(failed) - len(warned)} dat"
          f" | {len(warned)} luu y | {len(failed)} hong")
    if failed:
        print("KHONG DAT:")
        for _, label, detail in failed:
            print(f"  {label}: {detail}")
        sys.exit(1)
    print("Cau truc SACH. Cac muc 'luu y' la du lieu thieu da biet, khong phai loi.")


if __name__ == "__main__":
    main()
