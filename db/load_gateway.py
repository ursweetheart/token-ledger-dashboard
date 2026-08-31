"""Nạp sổ API Gateway (`LiteLLM_SpendLogs`) vào `fact_call` - chỉ đọc, không gọi mạng.

HAI DATABASE, HAI KẾT NỐI
-------------------------
Sổ Gateway nằm ở database RIÊNG (`litellm`), cùng một instance PostgreSQL với
`token_ledger_v2`. PostgreSQL không cho JOIN xuyên database, và `postgres_fdw`
lẫn `dblink` đều chưa cài - nên file này mở HAI kết nối và ánh xạ ở tầng Python.

Đọc bằng vai `gateway_readonly`: chỉ SELECT được đúng bảng `LiteLLM_SpendLogs`,
mang `default_transaction_read_only = on`. Sổ gốc là bằng chứng, không được sửa.

QUY TẮC ÁP DỤNG
---------------
Quy tắc 5  Trường thiếu nạp NULL, KHÔNG nạp 0. `cached_tokens` vắng ở 39/39 dòng
           đo được ngày 31/08. Nạp 0 rồi lấy trung bình là sai.
Quy tắc 6  Dùng `total_tokens` của sổ, không tự cộng prompt + completion.

MÚI GIỜ
-------
`startTime` là `timestamp without time zone` và database chạy ở UTC. Đã chứng
minh chứ không suy luận: đồng hồ máy 07:56 (+07), đồng hồ container 00:47 UTC,
dòng vừa ghi mang 00:56. Nên `tz_confirmed = TRUE` và `ts_local = ts_raw + 7h`.
`ts_raw` chép NGUYÊN để sau này còn kiểm lại được.

Bỏ khâu +7h thì tổng cả kỳ vẫn đúng, chỉ có phân bố theo ngày là sai: mọi lượt
gọi từ 17:00 tới nửa đêm bị dồn sang ngày hôm trước.

NĂM CÁI BẪY - cả năm đều ĐO ĐƯỢC, không phải phòng xa
------------------------------------------------------
1. `status` KHÔNG BAO GIỜ NULL. Nó nhận đúng hai giá trị `success` / `failure`
   (đo 39/39 dòng, 0 dòng NULL). Lọc `WHERE status IS NULL` trả về 0 dòng và
   không báo lỗi gì - dashboard hiện số 0 trông y hệt "chưa có lưu lượng".

2. `end_user` là CHUỖI RỖNG, không phải NULL, khi thiếu định danh (11 dòng `''`,
   0 dòng NULL). Kiểm `IS NULL` bắt được 0 dòng và tưởng mọi request đều có người.

3. `request_tags` bị trộn tag tự động:
       ["dms-feedback", "User-Agent: python-httpx", "User-Agent: python-httpx/0.28.1"]
   Coi cả mảng là danh sách agent thì MỘT request thành BA agent. Chỉ tag khớp
   một dòng `dim_agent.code` mới là tag định danh. KHÔNG lọc bằng cách bỏ tiền tố
   `User-Agent:` - cách đó vá triệu chứng, sẽ hỏng khi LiteLLM thêm loại tag khác.

4. Cột `model` mang tên upstream có tiền tố (`gemini/gemini-3.5-flash-lite`),
   KHÔNG phải bí danh. Dạng bí danh chỉ xuất hiện ở dòng `failure` - request hỏng
   trước khi Router chốt tuyến thì không có tên upstream để ghi. Nếu về sau thấy
   dòng `success` mang bí danh, đó là dấu hiệu Router đã đổi gì đó.

5. Sổ ghi BẤT ĐỒNG BỘ (~4 giây). Một dòng có `startTime` = T có thể chưa tồn tại
   lúc bộ nạp chạy ở thời điểm T+1s. Nên mốc nạp tăng dần LÙI LẠI một giờ
   (`OVERLAP`) và dựa vào `ON CONFLICT DO NOTHING` để không nhân đôi.

TỐC ĐỘ
------
Đo kích thước cột ngày 31/08:

    proxy_server_request  6.677 byte/dòng      <- nặng nhất
    metadata              2.775 byte/dòng
    response                979 byte/dòng
    ----------------------------------------
    SELECT *           ~ 10.400 byte/dòng
    chỉ cột cần dùng   ~    200 byte/dòng      <- nhẹ hơn ~50 lần

Nên câu SELECT liệt kê cột tường minh và bóc JSON NGAY TRONG POSTGRES. Sổ đã có
sẵn chỉ mục `(startTime)` và `(startTime, request_id)` nên mốc nạp chạy bằng
index scan. Chèn theo lô bằng `execute_values` (`connect.insert_many`).

MỘT LƯỢT PHÂN LOẠI = HAI DÒNG SỔ
---------------------------------
    pipeline/rag_product.py:190       generate()        243 +   3 =   246 token
    pipeline/issue_classifier.py:424  generate_json()  5.652 + 408 = 6.060 token

Nên `COUNT(*)` ở đây là SỐ LƯỢT GỌI LLM, không phải số việc nghiệp vụ. Ai đọc
dashboard mà hiểu "2 dòng = 2 lần phân loại" là sai gấp đôi.

NGHIỆM THU
----------
    SELECT COUNT(*), SUM(total_tokens) FROM fact_call WHERE source='gateway';
    SELECT COUNT(*) FROM fact_call WHERE source='gateway' AND model_id IS NULL;
    -- chạy hai lần liên tiếp, lần hai phải nạp thêm 0 dòng

Chạy: python db/load_gateway.py [--dry-run] [--full]
"""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import connect  # noqa: E402

# Lùi lại bao nhiêu so với mốc đã nạp. Sổ ghi bất đồng bộ nên một dòng có thể
# xuất hiện SAU khi bộ nạp đã đi qua mốc thời gian của nó. Một giờ là rộng rãi so
# với độ trễ đo được (~4 giây), và đọc lại vùng chồng lấn không tốn gì: câu truy
# vấn chạy bằng chỉ mục, còn `ON CONFLICT DO NOTHING` lo phần trùng.
OVERLAP = timedelta(hours=1)

# Giờ Việt Nam. Cùng hằng số với load_ralli.py, cùng lý do.
VN_OFFSET = timedelta(hours=7)

SOURCE = "gateway"

# Chỉ cột cần dùng, và bóc JSON ngay trong PostgreSQL - xem mục TỐC ĐỘ.
BASE_SQL = """
    SELECT request_id,
           "startTime",
           model,
           COALESCE(end_user, '') AS end_user,
           request_tags,
           prompt_tokens,
           completion_tokens,
           total_tokens,
           (metadata->'usage_object'->'prompt_tokens_details'->>'cached_tokens')::bigint,
           (metadata->'cost_breakdown'->>'total_cost')::numeric
      FROM "LiteLLM_SpendLogs"
     WHERE status = 'success'
"""

COLUMNS = ["call_id", "agent_id", "ts_raw", "tz_confirmed", "ts_local",
           "user_id", "account_id", "model_id", "prompt_tokens",
           "completion_tokens", "total_tokens", "cached_tokens",
           "source", "cost_usd"]


def watermark(cn):
    """`ts_raw` lớn nhất ĐÃ nạp cho nguồn này, hoặc None nếu chưa có dòng nào.

    Hỏi theo `source` chứ không theo cả bảng: `fact_call` còn chứa 8.631 dòng của
    nguồn app, mốc của chúng không liên quan gì. Chỉ mục `(source, ts_raw)` dựng ở
    migration 004 phục vụ đúng câu này.
    """
    row = connect.query_one(
        cn, f"SELECT MAX(ts_raw) FROM fact_call WHERE source = '{SOURCE}'")
    return row[0] if row else None


def read_ledger(gw_cn, since):
    """Đọc sổ Gateway. `since` là None thì đọc hết."""
    cur = gw_cn.cursor()
    if since is None:
        cur.execute(BASE_SQL + ' ORDER BY "startTime"')
    else:
        cur.execute(BASE_SQL + ' AND "startTime" > %s ORDER BY "startTime"',
                    (since,))
    return cur.fetchall()


def resolve_agent(tags, agent_by_code):
    """Trả về (agent_id, lý_do_bỏ). Chỉ một trong hai khác None.

    BẪY 3: `request_tags` chứa cả tag do LiteLLM tự thêm. Tag định danh là tag
    khớp một dòng `dim_agent.code` - không phải "tag đầu tiên", cũng không phải
    "tag không bắt đầu bằng User-Agent:".
    """
    hits = [t for t in (tags or []) if t in agent_by_code]
    if len(hits) == 1:
        return agent_by_code[hits[0]], None
    if not hits:
        return None, "khong co tag dinh danh"
    return None, "nhieu tag dinh danh"


def build_rows(ledger, agent_by_code, models, accounts, anchors):
    """Ánh xạ dòng sổ -> dòng `fact_call`, kèm bộ đếm mọi thứ bị bỏ hoặc hụt."""
    rows = []
    stats = {
        "doc_tu_so": len(ledger),
        "bo_khong_co_tag": 0,
        "bo_nhieu_tag": 0,
        "khong_noi_duoc_model": 0,
        "end_user_rong": 0,
        "danh_tinh_khong_noi_duoc": 0,
        "cached_null": 0,
        "cost_null": 0,
    }
    for (call_id, ts_raw, model, end_user, tags,
         prompt_tokens, completion_tokens, total_tokens,
         cached_tokens, cost_usd) in ledger:

        agent_id, ly_do = resolve_agent(tags, agent_by_code)
        if agent_id is None:
            # `fact_call.agent_id` là NOT NULL, nên đây không chỉ là chính sách -
            # schema cưỡng chế. Đếm rồi bỏ, không nuốt lặng.
            stats["bo_khong_co_tag" if ly_do == "khong co tag dinh danh"
                  else "bo_nhieu_tag"] += 1
            continue

        # BẪY 4: tra theo tên upstream ở cột `model`. Dòng nào chưa khai trong
        # rules.GATEWAY_MODELS sẽ ra None - nạp vào với model_id NULL và ĐẾM,
        # chứ không loại. Mất dòng thì không ai biết; NULL thì đếm được.
        model_id = models.get((SOURCE, model))
        if model_id is None:
            stats["khong_noi_duoc_model"] += 1

        # BẪY 2: chuỗi rỗng, không phải NULL.
        user_id = end_user or None
        if user_id is None:
            stats["end_user_rong"] += 1

        # `account_id` nằm trong khoá chính của fact_usage_daily nên KHÔNG được
        # NULL. Neo tra theo (kind, unit_agent_id) - xem anchor_account_lookup().
        neo = anchors.get(agent_id)

        # CHỈ NỐI ĐỊNH DANH DO CHÍNH TA ĐẶT RA.
        #
        # Trước 31/08 chỗ này tra thẳng `accounts.get(end_user)`, tức là tin bất
        # kỳ chuỗi nào Gateway gửi tới. Đo ra một đường hỏng có thật: bảng
        # `account` CÓ dòng `admin` (account_id 1, "Quản trị viên", agent 5 - TLA
        # Hợp Đồng) và dòng đó ĐÃ mang 480 lượt / 1.588.404 token. Ngày DMS gửi
        # `X-User: admin` - tên đăng nhập cục bộ của chính nó - lưu lượng DMS sẽ
        # bị trộn vào lịch sử của một người dùng TLA Hợp Đồng. Im lặng, tổng vẫn
        # khớp, không phép kiểm nào bắt được.
        #
        # Phép thử an toàn, không cần đoán tiền tố: định danh chỉ được chấp nhận
        # khi nó tra ra ĐÚNG tài khoản neo của chính agent đó. `svc.dms-feedback`
        # -> 949 = neo của agent 6, hợp lệ. `admin` -> 1 != 949, từ chối.
        #
        # Đo 31/08: agent 6 KHÔNG có tài khoản người thật nào (chỉ agent 5 và 8
        # có, 45 và 893 dòng). Nên tới ngày DMS gửi tên người thật, chúng sẽ rơi
        # vào bộ đếm dưới đây - ồn ào, đúng như mong muốn - cho tới khi chiều
        # người dùng của DMS được dựng.
        tra_ra = accounts.get(user_id) if user_id else None
        if tra_ra is not None and tra_ra == neo:
            account_id = tra_ra
        else:
            if user_id is not None:
                stats["danh_tinh_khong_noi_duoc"] += 1
            account_id = neo

        if cached_tokens is None:
            stats["cached_null"] += 1
        if cost_usd is None:
            stats["cost_null"] += 1

        rows.append((
            call_id, agent_id, ts_raw, True, ts_raw + VN_OFFSET,
            user_id, account_id, model_id, prompt_tokens,
            completion_tokens, total_tokens, cached_tokens,
            SOURCE, cost_usd,
        ))
    return rows, stats


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default=connect.DEFAULT_DSN,
                   help="Chuoi ket noi dashboard. Mac dinh: connect.DEFAULT_DSN")
    p.add_argument("--gateway-db", default=connect.GATEWAY_DSN,
                   help="Chuoi ket noi so Gateway. Mac dinh: connect.GATEWAY_DSN")
    p.add_argument("--full", action="store_true",
                   help="Bo qua moc nap, doc lai toan bo so")
    p.add_argument("--dry-run", action="store_true",
                   help="In ra so se nap, khong ghi gi")
    args = p.parse_args()

    cn, ph = connect.open_db(args.db)

    # Nối sổ Gateway. Hỏng ở đây phải BÁO RÕ rồi dừng - tuyệt đối không được
    # nuốt lỗi rồi nạp 0 dòng và báo thành công, vì "0 dòng" trông y hệt
    # "chưa có lưu lượng".
    try:
        gw_cn, _ = connect.open_db(args.gateway_db)
    except Exception as exc:
        print(f"KHONG NOI DUOC SO GATEWAY: {connect.mask_dsn(args.gateway_db)}")
        print(f"  {type(exc).__name__}: {str(exc).strip().splitlines()[0]}")
        print("  Gateway dang tat? Chay: docker compose --profile gateway up -d")
        return 1

    # CHOT CHAN: `total_cost` chi la gia goc cua nha cung cap KHI margin va
    # discount deu bang 0. Do 31/08: 0/34 dong khac 0 - chua ai bat. Neu mot ngay
    # nao do co ai bat, con so nap vao dashboard khong con cung nghia nua, nen
    # DUNG HAN thay vi nap tiep mot cach im lang.
    gw_check = gw_cn.cursor()
    gw_check.execute(
        'SELECT COUNT(*) FROM "LiteLLM_SpendLogs" WHERE status = %s AND ('
        "   COALESCE((metadata->'cost_breakdown'->>'margin_percent')::float, 0) <> 0"
        "   OR COALESCE((metadata->'cost_breakdown'->>'discount_percent')::float, 0) <> 0)",
        ("success",))
    n_margin = gw_check.fetchone()[0]
    if n_margin:
        print(f"DUNG: {n_margin} dong co margin/discount khac 0.")
        print("  `total_cost` khong con la gia goc cua nha cung cap.")
        print("  Phai quyet dinh nap so nao truoc khi chay tiep.")
        gw_cn.close()
        cn.close()
        return 1

    since = None if args.full else watermark(cn)
    if since is not None:
        since = since - OVERLAP
    print(f"Nap tu {connect.mask_dsn(args.gateway_db)}")
    print(f"  moc nap: {'TOAN BO' if since is None else since} "
          f"(da lui lai {OVERLAP})")

    ledger = read_ledger(gw_cn, since)

    agent_by_code = connect.agent_code_lookup(cn)
    models = connect.model_lookup(cn)
    accounts = connect.account_lookup(cn)
    anchors = connect.anchor_account_lookup(cn)

    rows, stats = build_rows(ledger, agent_by_code, models, accounts, anchors)

    truoc = connect.query_one(
        cn, f"SELECT COUNT(*) FROM fact_call WHERE source = '{SOURCE}'")[0]
    if args.dry_run:
        print("  --dry-run: KHONG ghi gi")
        sau = truoc
    else:
        connect.insert_many(cn, ph, "fact_call", COLUMNS, rows,
                            on_conflict="ON CONFLICT (call_id) DO NOTHING")
        cn.commit()
        sau = connect.query_one(
            cn, f"SELECT COUNT(*) FROM fact_call WHERE source = '{SOURCE}'")[0]

    # Lượt hỏng: KHÔNG nạp, nhưng phải đếm. Số lượt hỏng là chỉ báo sức khoẻ của
    # Gateway - vứt đi là mất thông tin. Đo 31/08: 2/5 dòng hỏng vẫn mang 14
    # token đã thật sự gửi đi, nên đây không phải "mất 0".
    gw_cur = gw_cn.cursor()
    gw_cur.execute('SELECT COUNT(*), COALESCE(SUM(total_tokens), 0)'
                   ' FROM "LiteLLM_SpendLogs" WHERE status = %s', ("failure",))
    n_hong, token_hong = gw_cur.fetchone()

    print(f"  doc {stats['doc_tu_so']} dong thanh cong tu so"
          f" | dung duoc {len(rows)} | chen them {sau - truoc}")
    print(f"  bo: khong co tag {stats['bo_khong_co_tag']}"
          f" | nhieu tag {stats['bo_nhieu_tag']}")
    print(f"  khong noi duoc model {stats['khong_noi_duoc_model']}"
          f" | end_user rong {stats['end_user_rong']}"
          f" | danh tinh khong noi duoc {stats['danh_tinh_khong_noi_duoc']}")
    print(f"  cached_tokens NULL {stats['cached_null']}"
          f" | cost_usd NULL {stats['cost_null']}")
    print(f"  luot HONG trong so (khong nap): {n_hong} dong, {token_hong} token")

    # Đối chiếu với chính sổ gốc, không với số ghim. So trên TOÀN BỘ sổ chứ không
    # riêng vùng vừa đọc: đó mới là câu hỏi thật - "mọi thứ Gateway ghi đã vào
    # đây chưa".
    gw_cur.execute('SELECT COUNT(*), COALESCE(SUM(total_tokens), 0)'
                   ' FROM "LiteLLM_SpendLogs" WHERE status = %s', ("success",))
    src_rows, src_tokens = gw_cur.fetchone()
    dst_rows, dst_tokens = connect.query_one(
        cn, "SELECT COUNT(*), COALESCE(SUM(total_tokens), 0)"
            f" FROM fact_call WHERE source = '{SOURCE}'")

    print(f"  doi chieu ca so: nguon {src_rows} dong/{src_tokens:,} token"
          f" | dich {dst_rows} dong/{dst_tokens:,} token")

    # Số dòng bị bỏ phải đếm trên CẢ SỔ, không phải trên cửa sổ vừa đọc: lần
    # chạy tăng dần chỉ đọc vài dòng, còn `src_rows`/`dst_rows` là số của cả sổ.
    # Lấy `bo_qua` của cửa sổ mà so với tổng thì lần nào cũng báo lệch giả.
    gw_cur.execute(
        'SELECT COUNT(*), COALESCE(SUM(total_tokens), 0)'
        '  FROM "LiteLLM_SpendLogs" WHERE status = %s'
        '   AND (SELECT COUNT(*)'
        '          FROM jsonb_array_elements_text('
        "                 COALESCE(request_tags, '[]'::jsonb)) AS t"
        '         WHERE t = ANY(%s)) <> 1',
        ("success", list(agent_by_code)))
    bo_qua_ca_so, token_bo_qua = gw_cur.fetchone()
    print(f"  bo qua tren ca so: {bo_qua_ca_so} dong, {token_bo_qua} token")

    # Đối chiếu HAI chiều, không chỉ số dòng. Số dòng khớp mà token lệch nghĩa là
    # ánh xạ cột hỏng - đúng loại lỗi mà phép đếm dòng không thấy.
    errors = []
    if not args.dry_run:
        if dst_rows + bo_qua_ca_so != src_rows:
            errors.append(f"so dong: dich {dst_rows} + bo qua {bo_qua_ca_so}"
                          f" != nguon {src_rows}")
        if int(dst_tokens) + int(token_bo_qua) != int(src_tokens):
            errors.append(f"token: dich {dst_tokens} + bo qua {token_bo_qua}"
                          f" != nguon {src_tokens}")

    gw_cn.close()
    cn.close()
    if errors:
        for e in errors:
            print(f"  LECH: {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
