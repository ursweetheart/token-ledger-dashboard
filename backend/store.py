"""Tầng truy vấn - mọi câu SQL của backend nằm ở đây, không ở chỗ nào khác.

BA NGUYÊN TẮC
-------------
1. CHỈ ĐỌC. SQLite mở bằng mode=ro, PostgreSQL đặt session readonly. Đây là hệ
   điều hành và máy chủ database bảo đảm, không phải lời hứa trong tài liệu.
   Backend này không có endpoint ghi nào, và nếu ai thêm nhầm thì database tự
   từ chối.

2. KHÔNG NỐI CHUỖI với giá trị người dùng gửi lên. Mọi tham số đi qua đặt chỗ
   ('?' hoặc '%s'). Tên bảng/cột thì cố định trong mã nguồn, không bao giờ lấy
   từ tham số URL.

3. KHÔNG TÍNH LẠI CÁI DATABASE ĐÃ TÍNH. Tiền lấy từ hoá đơn, không nhân lại
   token với đơn giá. Database đã chọn nguồn và đã ghi lại chọn gì - việc của
   tầng này chỉ là chuyển tiếp, kể cả chuyển tiếp các cột "số này từ đâu ra".

MỖI KẾT NỐI MỘT YÊU CẦU
-----------------------
Đối tượng kết nối SQLite không dùng chung được giữa các luồng. FastAPI chạy đa
luồng, nên dùng chung sẽ ném "SQLite objects created in a thread can only be
used in that same thread" - và chỉ ném khi có hai người vào cùng lúc, tức lúc
khó tái hiện nhất.
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "db"))

import connect  # noqa: E402

DSN = os.environ.get("TOKEN_LEDGER_DSN", connect.DEFAULT_DSN)


@contextmanager
def open_db():
    """Kết nối CHỈ ĐỌC, tự động đóng lại.

    Nhánh SQLite (mở bằng `?mode=ro`) gỡ ngày 24/08/2026 - xem change
    `drop-the-sqlite-escape-hatch`. `set_session(readonly=True)` bên dưới là thứ
    duy nhất còn giữ kỷ luật chỉ-đọc của backend, và `check_api.py` có một phép
    kiểm khẳng định nó (`ReadOnlySqlTransaction`). Đừng gỡ dòng đó.
    """
    cn, ph = connect.open_db(DSN)
    # Postgres tự chặn mọi lệnh ghi ở mức máy chủ, không phụ thuộc mã nguồn.
    cn.set_session(readonly=True)
    try:
        yield cn, ph
    finally:
        cn.close()


def _rows(cn, sql: str, params=()) -> list[dict]:
    """Chạy SELECT, trả về danh sách dict theo tên cột.

    Đọc theo TÊN thay vì theo chỉ số: thêm một cột vào giữa câu SELECT sẽ làm
    lệch hết mọi r[3] phía sau, mà kiểu lỗi đó không ném exception - nó chỉ trả
    về số sai. Đọc theo tên thì thêm cột không làm gì hỏng.
    """
    cur = cn.cursor()
    cur.execute(sql, params) if params else cur.execute(sql)
    names = [m[0] for m in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def _f(x):
    """Decimal/None -> float/None. json không biết mã hoá Decimal của psycopg2."""
    return None if x is None else float(x)


def _money(x):
    """Tiền -> float làm tròn 6 chữ số, đúng thang schema khai NUMERIC(14,6).

    PHẢI làm tròn, không được trả thẳng. SQLite bỏ qua khai báo NUMERIC và cộng
    dồn bằng số thực, nên SUM ra 0.017360999999999998; PostgreSQL cộng bằng
    NUMERIC thật và ra 0.017361. Cùng một database, cùng một câu hỏi, hai chuỗi
    JSON khác nhau - và cái lệch đó lan ra mọi thứ so sánh phía sau (bộ nhớ đệm,
    chữ ký số, đối chiếu hai hệ).

    Làm tròn về 6 chữ số KHÔNG giấu đi chênh lệch thật: một cent là 0,01, còn
    đây là sai số ở chữ số thứ 15.
    """
    return None if x is None else round(float(x), 6)


def _day(x) -> str:
    """date của Postgres hoặc chuỗi của SQLite -> 'YYYY-MM-DD'."""
    return x if isinstance(x, str) else x.isoformat()


# =====================================================================
# Danh mục - đổi khi tổ chức đổi, không đổi khi người dùng bấm nút
# =====================================================================

def agents(cn) -> list[dict]:
    # ref_budget có cột `month`, một agent nhiều dòng. LEFT JOIN thẳng tay sẽ
    # NHÂN BẢN dòng agent ngay khi có tháng thứ hai - lỗi không lộ ra hôm nay,
    # chỉ lộ ra khi ai đó thêm ngân sách tháng sau. Lấy đúng tháng mới nhất.
    r = _rows(cn, """
        SELECT a.agent_id, a.code, a.name, a.gcp_project_id, a.is_running,
               a.has_google_source, a.data_from,
               b.budget_usd, b.budget_tokens, b.month AS budget_month
        FROM dim_agent a
        LEFT JOIN ref_budget b
          ON b.agent_id = a.agent_id
         AND b.month = (SELECT MAX(b2.month) FROM ref_budget b2
                        WHERE b2.agent_id = a.agent_id)
        ORDER BY a.agent_id""")
    for x in r:
        x["budget_usd"] = _money(x["budget_usd"])
        x["is_running"] = bool(x["is_running"])
        # Cột này là lý do view trả về '-' thay vì '0%' cho Ralli. Frontend phải
        # thấy được nó, nếu không "không đo được" sẽ hiện y hệt "không có lỗi".
        x["has_google_source"] = bool(x["has_google_source"])
        x["data_from"] = _day(x["data_from"])
        if x["budget_month"] is not None:
            x["budget_month"] = _day(x["budget_month"])
    return r


def models(cn) -> list[dict]:
    """Model kèm bảng giá. Giá là USD trên MỘT TRIỆU token; source='google' nghĩa
    là lấy từ Cloud Billing Catalog chứ không phải gõ tay."""
    r = _rows(cn, """
        SELECT m.model_id, m.name, m.family, m.provider,
               p.price_input, p.price_output, p.price_cached,
               p.source AS price_source, p.effective_from
        FROM dim_model m
        LEFT JOIN ref_price p
          ON p.model_id = m.model_id
         AND p.effective_from = (SELECT MAX(p2.effective_from) FROM ref_price p2
                                 WHERE p2.model_id = m.model_id)
        ORDER BY m.model_id""")
    for x in r:
        for k in ("price_input", "price_output", "price_cached"):
            x[k] = _money(x[k])
        if x["effective_from"] is not None:
            x["effective_from"] = _day(x["effective_from"])
    return r


def fx_rate(cn) -> dict | None:
    """Tỷ giá mới nhất. Frontend đang gõ cứng 25.200 trong app.js - lấy từ đây
    thì đổi tỷ giá không phải sửa mã nguồn."""
    r = _rows(cn, "SELECT day, vnd_per_usd, source FROM ref_fx ORDER BY day DESC")
    if not r:
        return None
    x = r[0]
    x["day"] = _day(x["day"])
    x["vnd_per_usd"] = _money(x["vnd_per_usd"])
    return x


def units(cn) -> list[dict]:
    # ORDER BY phải là MỘT THỨ TỰ TOÀN PHẦN, không được để hai dòng hoà nhau.
    # `ORDER BY level, name` đã từng đủ: hai dòng 'Chưa quy được' (của Trợ Lý Ảo
    # Hợp Đồng và Trợ lý ảo Ralli)
    # level bằng nhau tên bằng nhau, và SQLite với PostgreSQL trả về ngược thứ tự
    # nhau. Kết quả: cùng một API cho hai kết quả khác nhau tuỳ database, mà
    # không ai báo gì. Thêm khoá chính vào cuối là hết.
    # `canonical_unit_id` NULL = dòng này LÀ bản chuẩn; có giá trị = bản trùng ở
    # cây tổ chức của app kia. Frontend cần cột này để gộp hai cây thành một cái
    # nhìn công ty - trước 20/08/2026 phép gộp đó nằm trong UNIT_ALIASES gõ tay
    # ở web/js/app.js, tức database không biết gì về nó.
    r = _rows(cn, """
        SELECT unit_id, agent_id, name, parent_id, level, path, is_technical,
               canonical_unit_id, is_report_aggregate
        FROM dim_unit ORDER BY level, name, unit_id""")
    for x in r:
        x["is_report_aggregate"] = bool(x["is_report_aggregate"])
    return r


def accounts(cn) -> list[dict]:
    """Danh bạ. `unit_conflict`=1 nghĩa là hai app xếp người này vào hai phòng ban
    khác nhau và database đã chọn một - màn hình nên cho thấy dấu vết đó.

    KHÔNG TRẢ `email` (bỏ 20/08/2026). Frontend từng dùng email làm khoá ghép,
    nhưng `/api/usage-by-account` đã trả `account_id` - ghép bằng khoá số thì
    chính xác hơn và không phụ thuộc hoa/thường. Bỏ đi thì endpoint này thôi phơi
    927 địa chỉ thư của nhân viên ra mọi nơi gọi được nó.

    Đây là phòng thủ theo chiều sâu, KHÔNG thay cho xác thực. Từ 21/08/2026 máy
    chủ đã đòi `Authorization: Bearer <DASHBOARD_KEY>` trên cả 8 endpoint, nên
    mục C1 của docs/reference/viec-can-lam-truoc-api-gateway.md đã đóng - câu
    "máy chủ này chưa có xác thực nào" đứng ở đây tới 22/08/2026 và đã sai.

    Hai lớp vẫn cần cả hai: xác thực chặn người ngoài, còn bớt dữ liệu chặn cả
    sự cố lẫn sơ ý. Và khoá hiện tại là khoá DÙNG CHUNG - nó không biết ai đang
    đọc, nên "đã có xác thực" không có nghĩa là "đã biết ai xem gì"."""
    r = _rows(cn, """
        SELECT a.account_id, a.username, a.full_name, a.kind,
               a.unit_id, u.name AS unit_name, u.path AS unit_path,
               a.unit_conflict, a.is_shared, a.role, a.is_enabled, a.created_at,
               g.name AS agent,
               CASE WHEN EXISTS (SELECT 1 FROM dim_user d
                                  WHERE d.account_id = a.account_id
                                    AND d.found_in = 'directory')
                    THEN 1 ELSE 0 END AS in_directory
        FROM account a
        JOIN dim_unit u ON u.unit_id = a.unit_id
        JOIN dim_agent g ON g.agent_id = a.unit_agent_id
        -- ═══════ DÒNG DUY NHẤT giữ danh bạ chỉ có con người ═══════
        -- Nới điều kiện này ra là 6 tài khoản dịch vụ (`svc.<code>` của 6 agent
        -- một-người-dùng) đi thẳng lên màn hình. Đo A/B ngày 22/08/2026 trên
        -- backend thật và app.js thật, đổi đúng dòng này rồi hoàn nguyên:
        --
        --     /api/accounts          937  ->  943
        --     USER_ACCOUNTS          937  ->  943    (KHÔNG dòng nào bị vứt)
        --     thẻ "User hoạt động"  26/937 -> 26/943
        --
        -- KHÔNG có tấm lưới thứ hai. Hai chỗ trông như đỡ mà đo ra là không:
        --   - api.js loại đơn vị `is_technical` khỏi cây tổ chức, nhưng đó là
        --     chặn ĐƠN VỊ, không chặn TÀI KHOẢN
        --   - buildAccountCatalogueFromDb lọc `u.unitId &&`, nhưng unitOf() luôn
        --     trả ra một đơn vị `auto:` nên unitId không bao giờ rỗng - đo ra
        --     đúng 0 dòng bị loại ở cả hai vế
        --
        -- NÓI ĐÚNG MỨC: hại đo được dừng ở 6 dòng thừa trong bảng danh bạ và
        -- mẫu số 937->943. Cây phòng ban KHÔNG đổi - đơn vị gốc 11->11,
        -- DEPT_PROVISIONED 101 đơn vị / 3.693 không đổi, vì
        -- rebuildProvisionedFromDirectory lọc `in_directory && !is_shared` từ
        -- trước. Đây không phải "sập màn hình". Viết quá lên thì người đọc sau
        -- sẽ nới ra để thử xem có sập thật không.
        --
        -- VÌ SAO CHƯA PHƠI 6 tài khoản đó: chúng sẽ rơi vào 6 đơn vị `auto:` mà
        -- unitOf() chế sẵn - không parent, không mã thật, không ai chủ động tạo
        -- ra. Phải quyết chỗ đứng của chúng trong cây trước. Và hôm nay
        -- adoption() đã trả lời được câu "agent này có chạy không" mà không cần
        -- chúng có mặt ở đây.
        --
        -- backend/check_api.py có một phép kiểm khoá dòng này lại. Ghi chú nhắc
        -- người ĐỌC code; phép kiểm bắt người SỬA code mà không đọc.
        WHERE a.kind = 'real'
        ORDER BY a.username""")
    for x in r:
        x["is_shared"] = bool(x["is_shared"])
        x["in_directory"] = bool(x["in_directory"])
        if x["is_enabled"] is not None:
            x["is_enabled"] = bool(x["is_enabled"])
        if x["created_at"]:
            x["created_at"] = _day(x["created_at"])
    return r


def adoption(cn) -> list[dict]:
    """Tỷ lệ tài khoản được cấp có phát sinh request, theo AGENT.

    KHÔNG THEO KHOẢNG NGÀY, và đó là chủ ý chứ không phải chưa làm.
    "Đã từng dùng chưa" là câu hỏi TÍCH LUỸ. Ép nó vào thanh trượt ngày thì
    cùng một agent nhảy từ 50% xuống 7% chỉ vì người xem đổi kỳ, mà con số nào
    cũng trông như một phép đo. Đã đo thật trên TLA Hợp Đồng: 22/44 tính cả kỳ,
    3/44 nếu chỉ tháng 8 - lệch 7 lần. Hai cột `from_day`/`to_day` nói rõ tỷ lệ
    này tính trên khoảng nào.

    MỘT CÔNG THỨC CHO MỌI AGENT
    ---------------------------
        mẫu số = số tài khoản agent này CÓ
        tử số  = trong đó bao nhiêu tài khoản đã phát sinh request

    Agent cấp cho người thì mẫu số là danh bạ (Ralli 891, TLA HĐ 44). Agent
    chạy bằng một tài khoản dịch vụ thì mẫu số là 1, và tử số là 1 nếu nó có
    chạy. Không phân nhánh theo loại agent - thêm agent thứ 9 chỉ là thêm một
    dòng, không phải thêm một nhánh `if`.

    LOẠI TÀI KHOẢN DÙNG CHUNG khỏi CẢ tử số lẫn mẫu số (`is_shared`). Chúng vẫn
    nằm đủ trong mọi con số token và tiền; chỉ riêng chỉ tiêu này cần mỗi dòng
    là một người có thể chọn dùng hay không. Cột `shared_excluded` trả về số
    lượng bị loại, để chuyện đó nhìn thấy được chứ không nằm im trong code.

    `outside_directory` là người CÓ dùng nhưng KHÔNG có trong danh bạ - tài
    khoản đã bị xoá, hoặc app ghi tên khác. Không cộng vào tử số (mẫu số không
    chứa họ, cộng vào thì tỷ lệ vượt 100%), nhưng phải trả về: nó là dấu hiệu
    danh bạ và số liệu sử dụng đang trôi ra xa nhau.
    """
    r = _rows(cn, """
        SELECT g.agent_id, g.name AS agent,
          (SELECT COUNT(DISTINCT d.account_id)
             FROM dim_user d JOIN account c ON c.account_id = d.account_id
            WHERE d.agent_id = g.agent_id AND d.found_in = 'directory'
              AND c.is_shared = 0) AS provisioned,
          (SELECT COUNT(DISTINCT f.account_id)
             FROM fact_usage_daily f JOIN account c ON c.account_id = f.account_id
            WHERE f.agent_id = g.agent_id AND c.is_shared = 0
              AND f.source IN (SELECT source FROM ref_source WHERE knows_user)
              AND f.account_id IN (SELECT d.account_id FROM dim_user d
                                    WHERE d.agent_id = g.agent_id
                                      AND d.found_in = 'directory')) AS active,
          (SELECT COUNT(DISTINCT f.account_id)
             FROM fact_usage_daily f JOIN account c ON c.account_id = f.account_id
            WHERE f.agent_id = g.agent_id AND c.is_shared = 0
              AND f.source IN (SELECT source FROM ref_source WHERE knows_user)
              AND c.kind = 'real'
              AND f.account_id NOT IN (SELECT d.account_id FROM dim_user d
                                        WHERE d.agent_id = g.agent_id
                                          AND d.found_in = 'directory'))
              AS outside_directory,
          (SELECT COUNT(DISTINCT d.account_id)
             FROM dim_user d JOIN account c ON c.account_id = d.account_id
            WHERE d.agent_id = g.agent_id AND d.found_in = 'directory'
              AND c.is_shared = 1) AS shared_excluded,
          (SELECT COUNT(*) FROM fact_usage_daily f
            WHERE f.agent_id = g.agent_id) AS any_usage,
          (SELECT MIN(f.day) FROM fact_usage_daily f
            WHERE f.agent_id = g.agent_id) AS from_day,
          (SELECT MAX(f.day) FROM fact_usage_daily f
            WHERE f.agent_id = g.agent_id) AS to_day
        FROM dim_agent g
        ORDER BY g.name, g.agent_id""")

    for x in r:
        x["from_day"] = _day(x["from_day"]) if x["from_day"] else None
        x["to_day"] = _day(x["to_day"]) if x["to_day"] else None
        if x["provisioned"]:
            # Agent cấp cho người. Mẫu số là danh bạ.
            x["kind"] = "people"
        else:
            # Agent chạy bằng một tài khoản dịch vụ: mẫu số 1, tử số 1 nếu có
            # chạy trong kỳ. Không có danh bạ nào để đếm, và đó không phải
            # thiếu dữ liệu - agent loại này vốn không cấp quyền cho ai.
            x["kind"] = "service"
            x["provisioned"] = 1
            x["active"] = 1 if x["any_usage"] else 0
        x.pop("any_usage")
        x["rate_pct"] = round(100.0 * x["active"] / x["provisioned"], 1)
    return r


# =====================================================================
# Số liệu theo khoảng ngày
# =====================================================================

def usage(cn, ph, start: str, end: str) -> list[dict]:
    """Một dòng cho mỗi (day, agent, model). Nguồn đã được CHỌN sẵn.

    Ba cột `token_source` / `call_source` / `token_estimated` KHÔNG phải trang
    trí. Con số token của hôm nay đến từ monitoring (hoá đơn chưa về) trông y hệt
    con số tuần trước đến từ hoá đơn. Màn hình phải phân biệt được.
    """
    r = _rows(cn, f"""
        SELECT v.day, v.agent_id, a.name AS agent, v.model_id, m.name AS model,
               m.provider, v.total_tokens, v.input_tokens, v.output_tokens,
               v.cached_tokens, v.cost_usd, v.calls,
               v.token_source, v.call_source, v.token_estimated
        FROM usage_resolved v
        JOIN dim_agent a ON a.agent_id = v.agent_id
        JOIN dim_model m ON m.model_id = v.model_id
        WHERE v.day >= {ph} AND v.day <= {ph}
        ORDER BY v.day, v.agent_id, v.model_id""", (start, end))
    for x in r:
        x["day"] = _day(x["day"])
        x["cost_usd"] = _money(x["cost_usd"])
        x["token_estimated"] = bool(x["token_estimated"])
    return r


def usage_by_account(cn, ph, start: str, end: str) -> list[dict]:
    """Sử dụng quy về từng người. CHỈ phủ phần đến từ nguồn BIẾT NGƯỜI DÙNG
    (ref_source.knows_user) - xem `health`."""
    r = _rows(cn, f"""
        SELECT v.day, v.agent_id, g.name AS agent, v.model_id, v.account_id,
               v.username, v.full_name, v.unit_id, v.unit_path, v.unit_conflict,
               v.is_shared, v.calls, v.total_tokens, v.input_tokens, v.output_tokens
        FROM usage_by_account v
        JOIN dim_agent g ON g.agent_id = v.agent_id
        WHERE v.day >= {ph} AND v.day <= {ph}
        ORDER BY v.day, v.account_id, v.agent_id, v.model_id""", (start, end))
    for x in r:
        x["day"] = _day(x["day"])
    return r


def performance(cn, ph, start: str, end: str) -> dict:
    """Hai bộ số ở HAI ĐỘ MỊN khác nhau - trả riêng, không trộn.

    response_codes  (day, agent, method, response_code)
    latency         (day, agent)     phân vị không cộng được, xem 01_schema.sql
    """
    codes = _rows(cn, f"""
        SELECT day, agent_id, method, response_code, calls
        FROM fact_perf_daily
        WHERE day >= {ph} AND day <= {ph}
        ORDER BY day, agent_id, method, response_code""", (start, end))
    latency = _rows(cn, f"""
        SELECT day, agent_id, samples, p50_seconds, p95_seconds, p95_bucket_from,
               p95_bucket_to, p99_seconds, enough_samples
        FROM fact_latency_daily
        WHERE day >= {ph} AND day <= {ph}
        ORDER BY day, agent_id""", (start, end))
    for x in codes:
        x["day"] = _day(x["day"])
    for x in latency:
        x["day"] = _day(x["day"])
        x["enough_samples"] = bool(x["enough_samples"])
    return {"response_codes": codes, "latency": latency}


def thinking(cn, ph, start: str, end: str) -> list[dict]:
    """Token có bật chế độ suy luận (thinking), theo day/agent/model.

    Chỉ Cloud Monitoring có nhãn này - hoá đơn không tách, app không ghi. Nên
    đây là con số của RIÊNG nguồn monitoring, không phải của tổng.
    """
    r = _rows(cn, f"""
        SELECT substr(CAST(m.ts_local AS TEXT), 1, 10) AS day,
               m.agent_id, m.model_id,
               SUM(CASE WHEN m.thinking_enabled = 'true' THEN m.value ELSE 0 END)
                   AS thinking_tokens,
               SUM(m.value) AS monitoring_tokens
        FROM monitoring_ai m
        JOIN dim_metric_alias d
          ON d.source = 'monitoring' AND d.raw_name = m.metric_type
        WHERE d.measures = 'token' AND m.model_id IS NOT NULL
          AND substr(CAST(m.ts_local AS TEXT), 1, 10) >= {ph}
          AND substr(CAST(m.ts_local AS TEXT), 1, 10) <= {ph}
        GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3""", (start, end))
    for x in r:
        x["thinking_tokens"] = int(x["thinking_tokens"] or 0)
        x["monitoring_tokens"] = int(x["monitoring_tokens"] or 0)
    return r


# =====================================================================
# Sức khoẻ - cái này quan trọng ngang số liệu
# =====================================================================

def health(cn) -> dict:
    """Dữ liệu có gì, mới đến đâu, thiếu chỗ nào.

    Màn hình nào cũng phải hiện được phần `warnings`. Một bảng số đầy đủ trông y
    hệt một bảng số chỉ phủ 5,7% - đó là cách sai lầm đắt nhất xảy ra.
    """
    def one(sql: str):
        cur = cn.cursor()
        cur.execute(sql)
        r = cur.fetchone()
        return r[0] if r else None

    ranges = {}
    for label, table in (("usage", "usage_resolved"),
                         ("response_codes", "fact_perf_daily"),
                         ("latency", "fact_latency_daily")):
        cur = cn.cursor()
        cur.execute(f"SELECT MIN(day), MAX(day), COUNT(*) FROM {table}")
        lo, hi, n = cur.fetchone()
        ranges[label] = {"from": _day(lo) if lo else None,
                         "to": _day(hi) if hi else None, "rows": n}

    total = one("SELECT SUM(total_tokens) FROM usage_resolved") or 0

    # ĐỘ PHỦ CHIỀU NGƯỜI - đếm trên `usage_resolved`, KHÔNG trên fact_usage_daily.
    #
    # HAI CÁI BẪY đã vấp, ghi lại cả hai (20/08/2026):
    #
    # (1) Cộng từ fact_usage_daily là ĐẾM NHIỀU LẦN. Bảng đó để ba nguồn cạnh
    #     nhau, và tài khoản dịch vụ có token ở CẢ billing lẫn monitoring:
    #     Chatbot Contact Center 329.110.605 + 176.980.622 = 506.091.227, trong
    #     khi view chỉ nhận 333.221.182. Đo thử cách cộng đó: 1.248.600.872 /
    #     867.657.110 = 143,9%, và "phần còn lại" ra -43,9%.
    #     Bản trước 20/08 chỉ lọc kind='real' nên an toàn một cách TÌNH CỜ -
    #     token của người thật chỉ tồn tại ở source='app', tức một nguồn duy nhất.
    #
    # (2) Cộng token source='app' từ fact_usage_daily cũng vẫn LỆCH, vì nó gồm
    #     những ngày mà usage_resolved đã CHỌN billing thay cho app. Đo được:
    #     107.926.810 thay vì 104.990.903 - thừa 2,9 triệu view không dùng.
    #
    # Câu hỏi đúng là: "con số dashboard ĐANG HIỆN có chia được theo người
    # không?" - và nó được trả lời ở mức TỪNG KHOÁ (ngày, agent, model):
    #     agent một-người-dùng   -> chia được, về đúng một tài khoản dịch vụ
    #     nguồn knows_user       -> chia được, về người thật (app, gateway)
    #     billing / monitoring   -> KHÔNG, Google chỉ báo mức project
    #
    # HỎI ref_source.knows_user, KHÔNG so với chuỗi 'app' (đổi 21/08/2026).
    # Chuỗi 'app' mang nghĩa ngầm "nguồn duy nhất biết người dùng"; Gateway
    # cũng biết người dùng, nên hai nghĩa đó tách nhau ra.
    #
    # PHỤ THUỘC: câu này cần kind='service_account' đã có trong database. Với
    # database dựng trước 20/08 nó không sập, chỉ trả về con số cũ - nên
    # scripts/audit_db.py có phép kiểm đếm số dòng service_account, để việc chạy
    # backend mới trên database cũ hỏng ỒN ÀO chứ không âm thầm.
    cov = _rows(cn, """
        SELECT
          SUM(CASE WHEN s.agent_id IS NOT NULL
                   THEN v.total_tokens ELSE 0 END) AS service_tokens,
          SUM(CASE WHEN s.agent_id IS NULL AND v.token_source IN
                    (SELECT source FROM ref_source WHERE knows_user)
                   THEN v.total_tokens ELSE 0 END) AS people_tokens,
          SUM(CASE WHEN s.agent_id IS NULL
                    AND COALESCE(v.token_source, '') NOT IN
                        (SELECT source FROM ref_source WHERE knows_user)
                   THEN v.total_tokens ELSE 0 END) AS opaque_tokens
        FROM usage_resolved v
        LEFT JOIN (SELECT DISTINCT unit_agent_id AS agent_id FROM account
                    WHERE kind = 'service_account') s
               ON s.agent_id = v.agent_id""")[0]
    real = int(cov["people_tokens"] or 0)        # quy về một CON NGƯỜI
    service = int(cov["service_tokens"] or 0)    # quy về một tài khoản dịch vụ
    opaque = int(cov["opaque_tokens"] or 0)      # không quy được về ai
    attributed = real + service
    missing_tokens = one("SELECT COUNT(*) FROM usage_resolved WHERE total_tokens IS NULL")
    estimated = one("SELECT COUNT(*) FROM usage_resolved WHERE token_estimated = 1")
    conflicts = one("SELECT COUNT(*) FROM account WHERE unit_conflict = 1")

    warnings = []
    if total:
        pct = 100.0 * attributed / float(total)
        pct_people = 100.0 * real / float(total)
        # Lấy `opaque` ĐO ĐƯỢC chứ không lấy `100 - pct`. Ba nhóm cộng đúng bằng
        # tổng, nên nếu chúng KHÔNG cộng đủ thì đó là dấu hiệu truy vấn trên hụt
        # một trường hợp - và `100 - pct` sẽ che mất đúng dấu hiệu đó.
        pct_opaque = 100.0 * opaque / float(total)
        pct_service = 100.0 * service / float(total)
        warnings.append({
            "code": "user_coverage",
            "level": "medium",
            "value": round(pct, 1),
            "value_people": round(pct_people, 1),
            "value_service": round(pct_service, 1),
            "value_opaque": round(pct_opaque, 1),
            # `message` HIỆN RA TRƯỚC MẶT NGƯỜI DÙNG, nên viết tiếng Việt CÓ DẤU.
            # Trước 17/08/2026 bốn chuỗi này viết không dấu vì chỉ dùng để đọc trong
            # terminal; frontend chuyển tiếp nguyên văn nên chúng đi thẳng lên màn
            # hình. Chữ người dùng đọc thì phải có dấu - xem quy ước ở
            # docs/reference/cay-thu-muc.md.
            #
            # NÓI ĐỦ BA CON SỐ, không gộp (sửa 20/08/2026). Bản trước chỉ nói
            # `real` và gọi phần còn lại là "không quy được" - gộp 6 agent
            # một-người-dùng vào cùng rổ với phần Google thật sự không biết, làm
            # lỗ hổng trông lớn gấp ~70 lần thực tế.
            # Nêu ĐỦ BA tỷ lệ thay vì "phần còn lại". Khi service = 0 - đúng cái
            # xảy ra nếu chạy trên database dựng trước 20/08/2026 - câu "phần còn
            # lại là tài khoản dịch vụ" nói về một thứ không tồn tại. Nêu cả ba
            # thì câu đúng ở MỌI trạng thái, và người đọc cộng kiểm được.
            "message": f"{pct:.1f}% token quy được về một danh tính"
                       f" ({pct_people:.1f}% người thật"
                       f" + {pct_service:.1f}% tài khoản dịch vụ của các agent"
                       f" một-người-dùng)."
                       f" {pct_opaque:.1f}% không quy được: phần này chỉ có hoá đơn"
                       f" Google, nơi ghi được mức project chứ không ghi ai gọi —"
                       f" riêng nó không chia được theo NGƯỜI hay PHÒNG BAN."})
    if estimated:
        warnings.append({
            "code": "estimated_tokens", "level": "medium", "value": estimated,
            "message": f"{estimated} dòng có token chưa được hoá đơn xác nhận, lấy từ"
                       f" Cloud Monitoring hoặc từ chính ứng dụng."})
    if missing_tokens:
        warnings.append({
            "code": "missing_tokens", "level": "low", "value": missing_tokens,
            "message": f"{missing_tokens} dòng có số lượt nhưng không có token —"
                       f" model embedding, Cloud Monitoring không đo token cho chúng."})
    if conflicts:
        warnings.append({
            "code": "unit_conflict", "level": "low", "value": conflicts,
            "message": f"{conflicts} tài khoản được hai ứng dụng xếp vào hai phòng ban"
                       f" khác nhau; database đã chọn một theo quy tắc tất định."})

    # Ba con số dưới đây PHẢI cộng đúng bằng total_tokens. Trả cả ba ra ngoài để
    # người đọc kiểm được phép cộng, thay vì phải tin một tỷ lệ phần trăm.
    return {"ranges": ranges,
            "total_tokens": int(total),
            "tokens_attributed_to_people": real,
            "tokens_attributed_to_service": service,
            "tokens_not_attributable": opaque,
            "tokens_attributed": attributed,
            "warnings": warnings}
