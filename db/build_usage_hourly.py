"""Dựng fact_usage_hourly - cùng năm chiều khoá như bảng ngày, chỉ mịn hơn.

Không đọc file nào: chỉ gộp lại từ các bảng đã nạp.

BA NGUỒN, KHÔNG PHẢI BỐN - VÀ NGUỒN VẮNG MẶT LÀ MỘT THÔNG TIN
-------------------------------------------------------------
    app          fact_call.ts_local        -> xuống được giờ
    gateway      fact_call.ts_local        -> xuống được giờ
    monitoring   fact_monitoring.ts_local  -> xuống được giờ
    billing      fact_billing_daily.day    -> KHÔNG BAO GIỜ có giờ

Hoá đơn Google tính theo NGÀY. Đó là giới hạn của nhà cung cấp, không phải của
ta, và không có cách nào vượt.

Cách sai mà dễ chọn: chia đều tiền của một ngày cho 24 giờ. Nó cho ra một biểu
đồ đẹp và một con số BỊA - mỗi giờ mang một phần tiền mà nhà cung cấp chưa bao
giờ nói là của giờ đó. Cùng loại lỗi với việc trung bình các p95 để ra p95 của
ngày, đã ghi ở db/build_performance.py.

Người đọc biết `billing` vắng mặt bằng cách TRUY VẤN cột `source`. Dữ liệu tự
nói, không nhờ tầng hiển thị nói hộ.

CÙNG BỘ LỌC VỚI BẢNG NGÀY, KHÔNG ĐƯỢC KHÁC MỘT ĐIỀU KIỆN NÀO
-------------------------------------------------------------
Bảng này phải cộng lại đúng bằng bảng ngày cho cùng một nguồn - đó là phép kiểm
duy nhất chứng minh nó không lệch. Nên MỌI điều kiện lọc phải sao y
`db/build_usage_daily.py`:

    model_id IS NOT NULL       cả ba nguồn  (model_id nằm trong khoá chính)
    source = '<nguồn>'         app / gateway tách nhau trong cùng fact_call
    outcome = 'success'        chỉ gateway  (rò 14 token khi thiếu, đo 31/08)
    cache_hit IS NOT TRUE      chỉ gateway  (lượt trúng cache vẫn ghi đủ token
                               nhưng nhà cung cấp không tính tiền)

Đổi một điều kiện ở đây mà quên đổi ở kia thì tổng hai bảng lệch, và phép kiểm
`Hourly totals match daily totals` của scripts/audit_db.py sẽ kêu. Đó là chỗ
duy nhất bắt được, nên đừng nới nó.

`cache_hit IS NOT TRUE` chứ KHÔNG phải `NOT cache_hit`: cột cho phép NULL, mà
`NOT NULL` ra UNKNOWN và WHERE loại mọi dòng không đúng TRUE - cách viết sai vứt
sạch 38/41 dòng gateway và kéo token về 0.

Chạy: python db/build_usage_hourly.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_usage_daily  # noqa: E402  - dùng lại anchor_accounts(), không chép
import connect  # noqa: E402
import logs  # noqa: E402

log = logs.get_logger("build_usage_hourly")

COLUMNS = ["hour", "agent_id", "model_id", "account_id", "calls",
           "total_tokens", "input_tokens", "output_tokens", "cached_tokens",
           "cost_usd", "source"]

# Ba nguồn xuống được giờ. `billing` KHÔNG có mặt, và sự vắng mặt đó là có chủ ý
# - xem docstring. Đọc bảng này để biết nguồn nào phải có, thay vì đếm số 3.
NGUON_THEO_GIO = ("app", "gateway", "monitoring")


def _bo_dong_khong_co_gio(cn, source: str) -> int:
    """Đếm dòng `fact_call` của nguồn này KHÔNG có `ts_local`.

    `hour` là NOT NULL và nằm trong khoá chính, nên dòng thiếu `ts_local` không
    vào được bảng. Đếm rồi báo, chứ không để nó biến mất lặng lẽ: bảng ngày dùng
    `substr(CAST(ts_local AS TEXT), 1, 10)` nên cũng vứt đúng những dòng đó, và
    nếu con số này khác 0 thì CẢ HAI bảng đang thiếu cùng một chỗ.
    """
    return int(connect.query_one(cn, f"""
        SELECT COUNT(*) FROM fact_call
         WHERE source = '{source}' AND model_id IS NOT NULL
           AND ts_local IS NULL""")[0] or 0)


def load_app(cn, ph) -> int:
    """Nguồn `app` theo giờ. CHỈ Ralli xuống được giờ.

    TLA Hợp Đồng nằm ở `fact_app_daily`, mà bảng đó gộp sẵn theo NGÀY - app
    không phơi log thô. Nên nguồn `app` của bảng theo giờ chỉ có Ralli, và tổng
    theo giờ của nguồn này sẽ NHỎ HƠN tổng theo ngày.

    Đó là lý do phép kiểm ở audit_db.py phải so THEO TỪNG NGUỒN và phải biết
    trước chuyện này, chứ không so tổng tất cả.
    """
    rows = connect.query(cn, """
        SELECT date_trunc('hour', ts_local), agent_id, model_id, account_id,
               COUNT(*), SUM(total_tokens),
               SUM(prompt_tokens), SUM(completion_tokens), SUM(cached_tokens)
        FROM fact_call
        WHERE model_id IS NOT NULL AND source = 'app' AND ts_local IS NOT NULL
        GROUP BY 1, 2, 3, 4
    """)
    out = [(*r, None, "app") for r in rows]
    return connect.insert_many(cn, ph, "fact_usage_hourly", COLUMNS, out)


def load_gateway(cn, ph) -> int:
    """Nguồn `gateway` theo giờ. Cùng ba bộ lọc với bảng ngày, không thiếu cái nào."""
    rows = connect.query(cn, """
        SELECT date_trunc('hour', ts_local), agent_id, model_id, account_id,
               COUNT(*), SUM(total_tokens),
               SUM(prompt_tokens), SUM(completion_tokens), SUM(cached_tokens),
               SUM(cost_usd)
        FROM fact_call
        WHERE model_id IS NOT NULL AND source = 'gateway' AND ts_local IS NOT NULL
          AND outcome = 'success'
          AND cache_hit IS NOT TRUE
        GROUP BY 1, 2, 3, 4
    """)
    out = [(*r, "gateway") for r in rows]
    return connect.insert_many(cn, ph, "fact_usage_hourly", COLUMNS, out)


def load_monitoring(cn, ph, anchor) -> int:
    """Nguồn `monitoring` theo giờ.

    `fact_monitoring` KHÔNG có `account_id` - Google chỉ báo tới mức project.
    Nên dùng tài khoản neo của agent, đúng như bảng ngày làm.

    Đây cũng là chỗ ước lượng số dòng ở mốc 1.4 đếm hụt: dựng lại phép gộp bằng
    tay mà bỏ chiều `account_id` cho 484 dòng/ngày trong khi bảng thật có 606.
    """
    def group(measures: str, kind: str | None = None) -> dict:
        extra = f" AND d.kind = {ph}" if kind else ""
        params = (measures, kind) if kind else (measures,)
        return {(r[0], r[1], r[2]): r[3] for r in connect.query(cn, f"""
            SELECT date_trunc('hour', m.ts_local), m.agent_id, m.model_id,
                   SUM(m.value)
            FROM monitoring_ai m
            JOIN dim_metric_alias d
              ON d.source = 'monitoring' AND d.raw_name = m.metric_type
            WHERE m.model_id IS NOT NULL AND d.measures = {ph}{extra}
            GROUP BY 1, 2, 3
        """, params)}

    tokens = group("token")
    calls = group("calls")
    tok_in = group("token", "input")
    tok_out = group("token", "output")
    # KHÔNG lấy cached: Cloud Monitoring không có phép đo nào cho nó. NULL, không
    # phải 0 - 0 nghĩa là "đo được và bằng không".

    def get(d: dict, k) -> int | None:
        # `int()` CẮT chứ không làm tròn, và ở đây nó cắt tại mức GIỜ trong khi
        # bảng ngày cắt tại mức NGÀY. Nếu `value` có phần lẻ thì cộng 24 lần số
        # đã cắt sẽ KHÁC số cắt một lần - lệch âm thầm, mỗi giờ một chút.
        #
        # Đo 03/09: 0/62.785 dòng monitoring có phần lẻ, nên hôm nay không lệch.
        # Không dựa vào đó: `doi_chieu_voi_bang_ngay()` so đúng hai con số này và
        # DỪNG HẲN nếu chúng khác nhau. Đó mới là thứ giữ cho phép cắt an toàn.
        return int(d[k]) if k in d else None

    out = []
    for k in sorted(set(tokens) | set(calls)):
        hour, aid, mid = k
        out.append((hour, aid, mid, anchor[aid], get(calls, k), get(tokens, k),
                    get(tok_in, k), get(tok_out, k), None, None, "monitoring"))
    return connect.insert_many(cn, ph, "fact_usage_hourly", COLUMNS, out)


def doi_chieu_voi_bang_ngay(cn) -> list[str]:
    """Tổng theo giờ phải bằng tổng theo ngày, CHO TỪNG NGUỒN.

    Trả về danh sách mô tả các chỗ lệch. Rỗng nghĩa là khớp.

    So theo từng nguồn chứ không so tổng: nguồn `app` có hai bảng gốc và chỉ một
    trong hai xuống được giờ, nên tổng chung CHẮC CHẮN lệch mà không có gì sai.
    Gộp lại thành một con số là biến một sự thật đã biết thành một báo động giả,
    rồi người ta sẽ tắt phép kiểm đi.
    """
    lech = []
    for src in NGUON_THEO_GIO:
        gio = connect.query_one(cn, f"""
            SELECT COALESCE(SUM(total_tokens), 0), COALESCE(SUM(calls), 0)
            FROM fact_usage_hourly WHERE source = '{src}'""")
        ngay = connect.query_one(cn, f"""
            SELECT COALESCE(SUM(total_tokens), 0), COALESCE(SUM(calls), 0)
            FROM fact_usage_daily WHERE source = '{src}'""")
        if src == "app":
            # Chỉ Ralli xuống được giờ. So với phần fact_call của nguồn app, chứ
            # không với cả nguồn - fact_app_daily (TLA HĐ) không có giờ.
            ngay = connect.query_one(cn, """
                SELECT COALESCE(SUM(total_tokens), 0), COALESCE(SUM(calls), 0)
                FROM (SELECT SUM(total_tokens) AS total_tokens,
                             COUNT(*) AS calls
                        FROM fact_call
                       WHERE source = 'app' AND model_id IS NOT NULL
                         AND ts_local IS NOT NULL) t""")
        if int(gio[0]) != int(ngay[0]):
            lech.append(f"{src}: token theo gio {int(gio[0]):,}"
                        f" != {int(ngay[0]):,} theo ngay")
        if int(gio[1]) != int(ngay[1]):
            lech.append(f"{src}: calls theo gio {int(gio[1]):,}"
                        f" != {int(ngay[1]):,} theo ngay")
    return lech


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=connect.DEFAULT_DSN)
    args = p.parse_args()

    cn, ph = connect.open_db(args.db)
    cn.cursor().execute("DELETE FROM fact_usage_hourly")

    for src in ("app", "gateway"):
        n = _bo_dong_khong_co_gio(cn, src)
        if n:
            log.warning("  %s: %d rows have no ts_local - they are missing from"
                        " the daily table too, not just this one", src, n)

    anchor = build_usage_daily.anchor_accounts(cn)
    n_a = load_app(cn, ph)
    n_g = load_gateway(cn, ph)
    n_m = load_monitoring(cn, ph, anchor)
    cn.commit()

    tong = connect.query_one(cn, "SELECT COUNT(*) FROM fact_usage_hourly")[0]
    log.info("  app %d | gateway %d | monitoring %d  ->  %d rows",
             n_a, n_g, n_m, tong)

    by_source = dict(connect.query(cn, "SELECT source, COUNT(*)"
                                       " FROM fact_usage_hourly GROUP BY source"))
    log.info("  by source: %s", by_source)

    # `billing` KHÔNG được có mặt. Nếu ai đó thêm nó vào thì phép kiểm này kêu
    # ngay tại chỗ, chứ không đợi tới lúc có người đọc một con số tiền theo giờ.
    if "billing" in by_source:
        raise SystemExit("fact_usage_hourly co nguon 'billing' - hoa don Google"
                         " chi tinh theo NGAY, moi con so tien theo gio deu la"
                         " bia. Xem docstring cua db/build_usage_hourly.py")

    gio_rieng = connect.query_one(
        cn, "SELECT COUNT(DISTINCT hour) FROM fact_usage_hourly")[0]
    ngay_rieng = connect.query_one(
        cn, "SELECT COUNT(DISTINCT CAST(hour AS DATE)) FROM fact_usage_hourly")[0]
    log.info("  %d distinct hours across %d days", gio_rieng, ngay_rieng)

    lech = doi_chieu_voi_bang_ngay(cn)
    if lech:
        for d in lech:
            log.error("  %s", d)
        raise SystemExit("tong theo gio KHONG bang tong theo ngay - xem tren")
    log.info("  hourly totals match daily totals for all %d sources",
             len(NGUON_THEO_GIO))

    cn.close()


if __name__ == "__main__":
    main()
