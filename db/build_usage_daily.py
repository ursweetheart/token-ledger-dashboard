"""Dựng fact_usage_daily từ ba nguồn - bước (7) của Ngày 2.

Không đọc file nào: chỉ gộp lại từ các bảng đã nạp.

CỘT `source` LÀ CỘT QUAN TRỌNG NHẤT
-----------------------------------
Ba nguồn nằm CẠNH NHAU, KHÔNG cộng vào nhau. Cùng một ngày cùng một agent có thể
có ba dòng. Chính tỷ lệ giữa chúng là bộ đo phát hiện app ghi thiếu (12,9% tiền,
17,0% lượt gọi ở TLA HĐ). Xoá một nguồn là xoá luôn bộ đo.

    Hỏi TIỀN          -> đọc source='billing'
    Hỏi AI DÙNG       -> đọc source='app'
    Hỏi LƯỢT/ĐỘ TRỄ   -> đọc source='monitoring' (hoặc fact_perf_daily)

Muốn MỘT con số thì đọc view `usage_resolved` - nó đã chọn sẵn nguồn.

VIỆC CHƯA LÀM ĐƯỢC - PHẢI BIẾT TRƯỚC KHI DÙNG BẢNG NÀY
-------------------------------------------------------
(a) `day` của nguồn 'billing' là ngày theo giờ Mỹ, nhưng ta COI LÀ giờ Việt Nam
    (chốt 14/08). Tổng cả kỳ vẫn đúng tuyệt đối; chỉ CHUỖI THEO NGÀY của riêng
    nguồn billing là lệch tới 15 giờ. Nguồn 'app' và 'monitoring' đều là giờ VN
    thật.
(b) Nguồn 'app' của TLA HĐ mịn đến (ngày x người x model) chứ không đến từng
    lượt gọi - app không phơi log thô. Đủ cho mọi câu hỏi theo ngày, nhưng
    không truy được về một lượt cụ thể như Ralli. Xem chú thích ở `load_app`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import connect  # noqa: E402
import logs  # noqa: E402

log = logs.get_logger("build_usage_daily")

# RALLI/TLA_HD/SINGLE_USER_AGENTS đã bỏ: chúng chỉ phục vụ việc chọn đơn vị kỹ
# thuật trong `anchor_accounts`, mà đơn vị không còn nằm trong bảng này nữa.

# KHÔNG ghim số mong đợi nữa (trước: 270.951716 / 44.692.501). Bảng này là bảng
# DẪN XUẤT: nó phải bằng đúng tổng của fact_billing_daily và fact_call. Số dùng
# để đối chiếu vì vậy lấy THẲNG TỪ HAI BẢNG ĐÓ, ở mỗi lần chạy. Như thế phép
# kiểm vẫn bắt được đúng cái nó sinh ra để bắt - tiền rơi rớt trong khâu tổng
# hợp - mà không lỗi thời mỗi khi có dữ liệu mới.


def anchor_accounts(cn) -> dict[int, int]:
    """agent_id -> account_id kỹ thuật, thay cho NULL ở khoá (§4.2).

    Tra CẢ BẢNG một lần rồi tra cứu trong bộ nhớ. Gọi một câu SELECT cho từng
    dòng thì với vài nghìn dòng là vài nghìn vòng quay - không hỏng, chỉ chậm,
    nên rất dễ bỏ qua.

    KHÔNG trả về unit_id: fact_usage_daily đã bỏ cột đó. Đơn vị là thuộc tính
    của tài khoản, JOIN account là ra - giữ thêm một bản sao trong bảng sự kiện
    chỉ tạo thêm một chỗ để lệch.

    TRA BẰNG (kind, unit_agent_id), KHÔNG BẰNG TÊN ĐĂNG NHẬP. Trước 21/08/2026
    hàm này tra `__whole_agent_<id>__`, tức một chuỗi ký tự do khâu nạp khác đặt
    ra - hai file phải giữ khớp bằng tay, và load_org.py phải mang một ghi chú
    "đừng đổi tên ở đây". Ngày quy ước A3 bắt tài khoản dịch vụ đổi sang
    `svc.<code>`, đúng chỗ đó gãy.

    `kind IN ('service_account','whole_agent')` là CHỖ NGỒI "cả agent" - hai giá
    trị vì 20/08 đã tách "biết chính xác là ai" khỏi "không biết ai trong 892
    người". Cả hai đều là dòng gộp mức agent, nên cùng vào đây.
    """
    rows = connect.query(cn, """
        SELECT unit_agent_id, account_id FROM account
         WHERE kind IN ('service_account', 'whole_agent')""")
    out = {int(a): int(acc) for a, acc in rows}
    missing = [aid for (aid,) in connect.query(cn, "SELECT agent_id FROM dim_agent")
               if aid not in out]
    if missing:
        raise SystemExit(f"agents with no agent-level contribution: {missing}."
                         f" Run db/load_org.py again.")
    if len(out) != len(rows):
        raise SystemExit(f"some agent has more than one agent-level contribution:"
                         f" {len(rows)} rows, {len(out)} agents. Run db/load_org.py again.")
    return out


COLUMNS = ["day", "agent_id", "model_id", "account_id", "calls", "total_tokens",
           "input_tokens", "output_tokens", "cached_tokens", "cost_usd", "source"]


def load_billing(cn, ph, anchor) -> int:
    """Tiền từ hoá đơn.

    JOIN qua gcp_project_id đã BỎ: fact_billing_daily giờ có cột agent_id thật.

    `kind` của hoá đơn ('input'/'output'/'cached') chuyển thẳng thành ba cột.
    SUM(CASE...) chứ không ba truy vấn: một lần quét bảng, và ba con số chắc
    chắn đến từ cùng một bộ dòng.
    """
    rows = connect.query(cn, """
        SELECT day, agent_id, model_id, SUM(quantity), SUM(cost_usd),
               SUM(CASE WHEN kind = 'input'  THEN quantity ELSE 0 END),
               SUM(CASE WHEN kind = 'output' THEN quantity ELSE 0 END),
               SUM(CASE WHEN kind = 'cached' THEN quantity ELSE 0 END)
        FROM fact_billing_daily
        GROUP BY day, agent_id, model_id
    """)
    out = [(day, aid, mid, anchor[aid], None, tokens, tin, tout, tcached, cost, "billing")
           for day, aid, mid, tokens, cost, tin, tout, tcached in rows]
    return connect.insert_many(cn, ph, "fact_usage_daily", COLUMNS, out)


def load_monitoring(cn, ph, anchor) -> int:
    """Token và lượt gọi từ công tơ Google. Ngày giờ Việt Nam thật.

    LẤY NGÀY TỪ CHUỖI, KHÔNG DÙNG HÀM NGÀY THÁNG
    --------------------------------------------
    `substr(CAST(x AS TEXT), 1, 10)` chạy được cả hai hệ. Viết
    `substr(x, 1, 10)` thì SQLite vẫn chạy - vì nó lưu TIMESTAMP như chuỗi -
    nhưng Postgres ném "function substr(timestamp...) does not exist".
    Các hàm riêng từng hệ (`strftime` của SQLite, `to_char` của Postgres) đều
    không dùng được vì chỉ chạy một bên.

    Giả định: Postgres ở DateStyle mặc định (ISO), tức CAST ra text cho dạng
    'YYYY-MM-DD HH:MM:SS'. Container trong docker-compose.yml dùng locale=C nên
    đúng giả định này.

    LỌC BẰNG dim_metric_alias, KHÔNG CÒN LIKE '%token_count'
    -------------------------------------------------------
    Mẫu LIKE phụ thuộc vào cách Google đặt tên biến: đổi tên là truy vấn trả về
    0 dòng, không lỗi nào báo. Bảng biệt danh thì một tên lạ sẽ làm khâu NẠP
    dừng hẳn (xem load_monitoring.py), tức hỏng ở chỗ có người nhìn thấy.

    `api/request_count` vẫn bị loại, nhưng giờ bằng một lý do nói ra được:
    measures='calls' của nó đến từ serviceruntime chứ không từ generativelanguage,
    và nó KHÔNG có nhãn model (13.276/13.276 rỗng) - nó thuộc về fact_perf_daily.
    Điều kiện `model_id IS NOT NULL` đã loại sẵn.
    """
    def group(measures: str, kind: str | None = None) -> dict:
        # `kind` là NULL ở mọi phép đo không phải token, nên không lọc được bằng
        # `d.kind = ?` cho trường hợp tổng. Tách làm hai nhánh cho rõ.
        extra = f" AND d.kind = {ph}" if kind else ""
        params = (measures, kind) if kind else (measures,)
        return {(r[0], r[1], r[2]): r[3] for r in connect.query(cn, f"""
            SELECT substr(CAST(m.ts_local AS TEXT), 1, 10), m.agent_id,
                   m.model_id, SUM(m.value)
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
    # KHÔNG lấy cached: Cloud Monitoring không có phép đo nào cho nó (đã kiểm,
    # 13 phép đo không có cái nào kind='cached'). Để NULL, không để 0 - 0 nghĩa
    # là "đo được và bằng không", NULL nghĩa là "không đo".

    def get(d: dict, k) -> int | None:
        return int(d[k]) if k in d else None

    out = []
    for k in sorted(set(tokens) | set(calls)):
        day, aid, mid = k
        out.append((day, aid, mid, anchor[aid], get(calls, k), get(tokens, k),
                    get(tok_in, k), get(tok_out, k), None, None, "monitoring"))
    return connect.insert_many(cn, ph, "fact_usage_daily", COLUMNS, out)


def load_app(cn, ph) -> int:
    """Chiều người dùng. HAI ĐƯỜNG VÀO, cùng đổ về source='app'.

        Ralli   fact_call        từng lượt gọi  -> gộp ra ngày ở đây
        TLA HĐ  fact_app_daily   đã gộp sẵn     -> chỉ chuyển tiếp

    Trước 14/08 TLA HĐ không có dòng nào ở đây, vì các trang tổng hợp sẵn của
    app (period=day|week|month|year) đều không cho chiều NGÀY x MODEL x NGƯỜI:
    year có by_user nhưng là tổng cả kỳ, month chỉ tháng hiện tại. Đã dò ra
    `?period=custom&date_from=&date_to=` cùng `&user_id=` thì lấy được đủ ba
    chiều; scripts/pull_tla_contract_usage.py kéo về, db/load_tla_contract.py nạp vào fact_app_daily.
    Đó là "quyết định N5 hoãn lại" - nay đã xong.

    Hệ quả phải nhớ: hai đường KHÔNG cùng độ mịn. Ralli truy được về một lượt
    gọi cụ thể, TLA HĐ thì không. Mọi câu hỏi theo NGÀY thì cả hai đều trả lời
    được như nhau.

    GOM THEO account_id, KHÔNG theo user_id
    ---------------------------------------
    Nhật ký Ralli đôi khi ghi user_id là USERNAME thay vì ObjectId, nên cùng một
    tài khoản xuất hiện dưới hai dạng khoá. Trước đây chúng thành HAI dòng riêng;
    gom theo account_id thì chúng gộp lại làm một - đó là kết quả đúng, và cũng
    là lý do bắt buộc phải GROUP BY ở đây chứ không chèn thẳng: hai dạng khoá
    cùng ngày cùng model sẽ đụng khoá chính mới.

    134 lượt gọi không có user_id -> account_id đã được gán thành tài khoản
    'unattributed' ngay từ khâu nạp fact_call, nên ở đây không còn NULL nào.

    Đã BỎ `unit_id` khỏi GROUP BY cùng với việc bỏ cột đó khỏi bảng. Bỏ một cột
    khỏi GROUP BY chỉ có thể GỘP dòng lại chứ không tách ra, và gộp ở đây là
    đúng: hai dòng chỉ khác unit_id vốn là cùng một tài khoản bị hai app xếp vào
    hai phòng ban khác tên.
    """
    rows = connect.query(cn, """
        SELECT substr(CAST(ts_local AS TEXT), 1, 10), agent_id, model_id,
               account_id, COUNT(*), SUM(total_tokens),
               SUM(prompt_tokens), SUM(completion_tokens), SUM(cached_tokens)
        FROM fact_call
        WHERE model_id IS NOT NULL AND source = 'app'
        GROUP BY 1, 2, 3, 4
    """)
    # `source = 'app'` THÊM 31/08/2026. Trước đó fact_call chỉ có một nguồn nên
    # điều kiện này thừa; từ khi Gateway đổ vào cùng bảng thì thiếu nó là lưu
    # lượng Gateway bị đếm thành của app - và tổng vẫn khớp nên không phép kiểm
    # nào bắt được.
    #
    # cost_usd để NULL vì app của Ralli không có tiền đối chứng (quyết định M-D).
    out = [(*r, None, "app") for r in rows]

    # TLA HĐ: đã ở đúng độ mịn, chỉ chuyển tiếp.
    # `model_id IS NOT NULL` cùng lý do với fact_call ngay trên: fact_usage_daily
    # có model_id trong khoá chính nên dòng không biết model không vào được.
    # 4 lượt / 13.201 token bị loại như thế, và load_tla_contract.py in ra con số đó mỗi
    # lần chạy chứ không nuốt lặng.
    # Vẫn GROUP BY dù fact_app_daily đã duy nhất theo (ngày, tài khoản, tên model
    # gốc): hai tên gốc khác nhau có thể trỏ về cùng model_id, và khi đó chèn
    # thẳng sẽ đụng khoá chính.
    rows_hd = connect.query(cn, """
        SELECT day, agent_id, model_id, account_id, SUM(calls), SUM(total_tokens),
               SUM(prompt_tokens), SUM(completion_tokens)
        FROM fact_app_daily
        WHERE model_id IS NOT NULL
        GROUP BY day, agent_id, model_id, account_id
    """)
    # cached_tokens = NULL: API của TLA HĐ không tách token cache ra khỏi prompt.
    # NULL nghĩa là "không đo", 0 nghĩa là "đo được và bằng không" (quy tắc 5).
    out += [(*r, None, None, "app") for r in rows_hd]
    return connect.insert_many(cn, ph, "fact_usage_daily", COLUMNS, out)


def load_gateway(cn, ph) -> int:
    """Lưu lượng qua API Gateway, từ `fact_call` nguồn `gateway`.

    KHÁC nguồn `app` ở đúng một chỗ: nguồn này CÓ TIỀN. Nhưng tiền đó do LiteLLM
    nhân từ bảng giá nội bộ của nó, KHÔNG phải số Google xuất hoá đơn - nên
    `ref_source.has_invoice_cost` của `gateway` là FALSE, và mọi chỗ hiển thị phải
    mang nhãn ước tính.

    `model_id IS NOT NULL` cùng lý do với hai nguồn trên: model_id nằm trong khoá
    chính của fact_usage_daily nên dòng không biết model không vào được. Bộ nạp
    db/load_gateway.py in ra số dòng đó mỗi lần chạy chứ không nuốt lặng.

    `outcome = 'success'` THÊM 31/08/2026, cùng ngày `fact_call` bắt đầu nhận cả
    lượt hỏng. Đã đo lỗ rò trước khi vá: thiếu dòng này thì token gateway ra
    45.201 thay vì 45.187 - **rò đúng 14 token** của một lượt hỏng mang tên model
    dạng upstream. Hai lượt hỏng còn lại mang tên bí danh nên `model_id` NULL và
    đã bị điều kiện trên chặn sẵn.

    Con số nhỏ, nhưng nó rò IM LẶNG, và tỉ lệ sẽ tăng khi có lượt hỏng SAU khi
    Router đã chốt tuyến (timeout, 429, 500).

    `cache_hit IS NOT TRUE` THÊM 01/09/2026. Lượt trúng cache KHÔNG tới nhà cung
    cấp, nên nhà cung cấp không tính tiền nó - nhưng Gateway VẪN ghi đủ token cho
    nó (đo được: một lượt trúng cache ghi `spend = 0` mà `total_tokens = 352`).
    Cộng nó vào lưu lượng là khai khống token.

    PHẢI viết `IS NOT TRUE`, KHÔNG được viết `NOT cache_hit`. Cột này cho phép
    NULL, mà `NOT NULL` ra UNKNOWN và `WHERE` loại mọi dòng không đúng TRUE - nên
    cách viết sai sẽ vứt sạch 38/41 dòng gateway và kéo token về 0. Đo cả hai
    cách viết sai trước khi chốt, xem nhật ký 01/09.

    (Ở VẾ NGUỒN thì ngược lại: `LiteLLM_SpendLogs.cache_hit` là TEXT mang chuỗi
    'None', nên ở đó `IS NOT TRUE` lỗi kiểu. Hai đầu hai bẫy khác nhau.)

    MỘT LƯỢT PHÂN LOẠI ĐẺ HAI DÒNG. Nên `calls` ở đây là số lượt gọi LLM, không
    phải số việc nghiệp vụ.
    """
    rows = connect.query(cn, """
        SELECT substr(CAST(ts_local AS TEXT), 1, 10), agent_id, model_id,
               account_id, COUNT(*), SUM(total_tokens),
               SUM(prompt_tokens), SUM(completion_tokens), SUM(cached_tokens),
               SUM(cost_usd)
        FROM fact_call
        WHERE model_id IS NOT NULL AND source = 'gateway'
          AND outcome = 'success'
          AND cache_hit IS NOT TRUE
        GROUP BY 1, 2, 3, 4
    """)
    out = [(*r, "gateway") for r in rows]
    return connect.insert_many(cn, ph, "fact_usage_daily", COLUMNS, out)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                allow_abbrev=False)
    p.add_argument("--db", default=connect.DEFAULT_DSN)
    args = p.parse_args()

    cn, ph = connect.open_db(args.db)
    cn.cursor().execute("DELETE FROM fact_usage_daily")

    anchor = anchor_accounts(cn)
    n_b = load_billing(cn, ph, anchor)
    n_m = load_monitoring(cn, ph, anchor)
    n_a = load_app(cn, ph)
    n_g = load_gateway(cn, ph)
    log.info("  billing %d | monitoring %d | app %d | gateway %d",
             n_b, n_m, n_a, n_g)

    cost = connect.query_one(cn, "SELECT SUM(cost_usd) FROM fact_usage_daily"
                                 " WHERE source='billing'")[0]
    app_tokens = connect.query_one(cn, "SELECT SUM(total_tokens) FROM fact_usage_daily"
                                       " WHERE source='app'")[0]
    by_source = dict(connect.query(cn, "SELECT source, COUNT(*) FROM fact_usage_daily"
                                       " GROUP BY source"))
    # In TEN agent, khong in agent_id. Doc "[5, 8]" thi phai di tra bang moi biet
    # la ai; doc "Tro Ly Ao Hop Dong, Tro ly ao Ralli" thi hieu ngay. `agent_id`
    # van la khoa dung trong SQL - chi rieng CHU IN RA CHO NGUOI DOC moi dung ten.
    app_agents = [r[0] for r in connect.query(
        cn, "SELECT DISTINCT g.name FROM fact_usage_daily f"
            " JOIN dim_agent g ON g.agent_id = f.agent_id"
            " WHERE f.source='app' ORDER BY g.name")]

    log.info("  by source: %s", by_source)
    log.info("  billing cost $%.6f | app tokens %s",
             float(cost), f"{app_tokens:,}")
    log.info("  agents with an 'app' source: %s", ", ".join(app_agents))

    # Đối chiếu với các bảng gốc, không với số ghim.
    src_cost = connect.query_one(cn, "SELECT SUM(cost_usd) FROM fact_billing_daily")[0]
    # Nguồn 'app' có HAI bảng gốc. Cả hai đều lọc model_id IS NOT NULL cho khớp
    # đúng điều kiện mà load_app() dùng - không lọc ở đây thì phép kiểm sẽ báo
    # thiếu token trong khi thật ra chúng bị loại có chủ đích.
    src_tokens = (
        int(connect.query_one(cn, "SELECT SUM(total_tokens) FROM fact_call"
                                  " WHERE model_id IS NOT NULL"
                                  " AND source = 'app'")[0] or 0)
        + int(connect.query_one(cn, "SELECT SUM(total_tokens) FROM fact_app_daily"
                                    " WHERE model_id IS NOT NULL")[0] or 0))

    errors = []
    if abs(float(cost) - float(src_cost or 0)) > 1e-4:
        errors.append(f"cost {float(cost):.6f} != {float(src_cost or 0):.6f}"
                      f" in fact_billing_daily")
    if app_tokens != src_tokens:
        errors.append(f"app tokens {app_tokens} != {src_tokens} in fact_call")
    # Trước 31/08/2026 chỗ này ghim cứng `!= 3`. Ghim SỐ là sai hướng: thêm nguồn
    # thứ tư là phép kiểm báo lỗi trong khi hệ thống đang đúng. Nay nêu ĐÍCH DANH
    # ba nguồn bắt buộc, còn `gateway` là tuỳ - sổ Gateway có thể rỗng khi chưa
    # agent nào chạy qua, và đó không phải lỗi.
    REQUIRED = {"billing", "monitoring", "app"}
    missing = REQUIRED - set(by_source)
    if missing:
        errors.append(f"missing sources {sorted(missing)}")

    # Nguồn gateway: nếu có dòng thì token phải khớp bảng gốc.
    gw_tokens = connect.query_one(cn, "SELECT SUM(total_tokens) FROM fact_usage_daily"
                                      " WHERE source='gateway'")[0]
    if gw_tokens is not None:
        gw_src = connect.query_one(cn, "SELECT SUM(total_tokens) FROM fact_call"
                                       " WHERE model_id IS NOT NULL"
                                       " AND source='gateway'"
                                       " AND outcome='success'")[0]
        if int(gw_tokens) != int(gw_src or 0):
            errors.append(f"gateway tokens {gw_tokens} != {gw_src} in fact_call")

    # Ba cột tách phải cộng lại ra total_tokens - theo đúng QUY ƯỚC CỦA TỪNG
    # NGUỒN, không phải một công thức chung:
    #   billing    input + output + cached = total   (cached là SKU riêng)
    #   app        input + output          = total   (cached nằm trong input)
    #   monitoring không có cached               -> như app
    # Nguồn 'app' KHÔNG khớp tuyệt đối, và đó là lỗi của chính hai app chứ không
    # phải của khâu nạp:
    #   Ralli   81/8.216 lượt có total != prompt+completion, mỗi dòng lệch đúng 2
    #   TLA HĐ  API trả total lệch với prompt+completion ở mức cả kỳ
    #
    # Trước đây chỗ này ghim cứng dung sai 162. Ghim số là sai hướng: nó biến
    # "app lệch bao nhiêu" thành một hằng số phải sửa tay mỗi lần thêm nguồn -
    # và lần thêm TLA HĐ đã chứng minh đúng như vậy. Nay ĐO THẲNG TỪ BẢNG NGUỒN,
    # gộp y hệt cách load_app() gộp, rồi đòi bảng dẫn xuất lệch ĐÚNG BẰNG THẾ.
    # Dung sai 0. Phép kiểm vẫn bắt đúng cái nó sinh ra để bắt - token rơi rớt
    # trong khâu gộp - mà không lỗi thời khi có dữ liệu mới.
    source_conflict = int(connect.query_one(cn, """
        SELECT SUM(t) - SUM(COALESCE(p, 0)) - SUM(COALESCE(c, 0)) FROM (
            SELECT SUM(total_tokens) AS t, SUM(prompt_tokens) AS p,
                   SUM(completion_tokens) AS c
            FROM fact_call WHERE model_id IS NOT NULL AND source = 'app'
            GROUP BY substr(CAST(ts_local AS TEXT), 1, 10), agent_id, model_id,
                     account_id) x""")[0] or 0)
    source_conflict += int(connect.query_one(cn, """
        SELECT SUM(t) - SUM(COALESCE(p, 0)) - SUM(COALESCE(c, 0)) FROM (
            SELECT SUM(total_tokens) AS t, SUM(prompt_tokens) AS p,
                   SUM(completion_tokens) AS c
            FROM fact_app_daily WHERE model_id IS NOT NULL
            GROUP BY day, agent_id, model_id, account_id) x""")[0] or 0)

    for source, add_cached in (("billing", True), ("monitoring", False), ("app", False)):
        r = connect.query_one(cn, f"""
            SELECT SUM(total_tokens), SUM(COALESCE(input_tokens, 0)),
                   SUM(COALESCE(output_tokens, 0)), SUM(COALESCE(cached_tokens, 0))
            FROM fact_usage_daily WHERE source = {ph}""", (source,))
        total = int(r[0] or 0)
        parts = int(r[1] or 0) + int(r[2] or 0) + (int(r[3] or 0) if add_cached else 0)
        allowed = source_conflict if source == "app" else 0
        if (total - parts) != allowed:
            errors.append(f"source {source}: parts {parts:,} != total {total:,}"
                          f" (gap {total - parts:,}, source-table gap {allowed:,})")
    if source_conflict:
        log.warning("  app: %s token gap between total and prompt+completion"
                    " - the app records it that way, checked against the source"
                    " table", f"{source_conflict:,}")

    if errors:
        cn.rollback()
        raise SystemExit("ACCEPTANCE FAILED - rolled back:\n  "
                         + "\n  ".join(errors))
    cn.commit()
    log.info("  acceptance passed")


if __name__ == "__main__":
    main()
