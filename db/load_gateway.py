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

NẠP CẢ LƯỢT HỎNG (đổi 31/08/2026)
----------------------------------
Bản đầu chỉ nạp lượt thành công. Nay nạp cả hai, vì Master Plan đòi "bản ghi mỗi
request" và một sổ lặng lẽ bỏ qua lượt hỏng thì không phải sổ đầy đủ - ta chỉ
biết CÓ hỏng mà không biết VÌ SAO, trong khi câu trả lời nằm sẵn trong sổ.

Ba cột đi kèm:

    duration_ms   độ trễ thô. `NULLIF(request_duration_ms, 0)` ngay ở tầng SQL.
    outcome       success / failure. MỌI phép tổng hợp PHẢI lọc cột này.
    error_code    `NULLIF(..., '')`. Đo: 3/5 dòng hỏng mang chuỗi rỗng.

VÌ SAO `duration_ms` PHẢI NULL KHI BẰNG 0 - và lý do KHÔNG phải cái ta tưởng:

    AuthenticationError    độ trễ 0   mã 401   DA GOI GOOGLE, Google từ chối
    ProxyException         độ trễ 0   mã 403   chặn ở Gateway
    ValueError             độ trễ 0   mã rỗng  chặn ở Gateway
    RouterRateLimitError   độ trễ 0   mã rỗng  không tìm được tuyến   x2

Dòng đầu ĐÃ ra tới nhà cung cấp mà độ trễ vẫn 0. Nên lý do thật là **LiteLLM
không ghi độ trễ cho lượt hỏng**, bất kể nó đi được tới đâu - chứ không phải
"chưa chạm provider nên không có gì để đo". Nạp 0 vào là kéo tụt mọi phân vị.

NĂM CÁI BẪY - cả năm đều ĐO ĐƯỢC, không phải phòng xa
------------------------------------------------------
1. `status` KHÔNG BAO GIỜ NULL. Nó nhận đúng hai giá trị `success` / `failure`
   (đo 45/45 dòng, 0 dòng NULL). Lọc `WHERE status IS NULL` trả về 0 dòng và
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
    SELECT outcome, COUNT(*), SUM(total_tokens) FROM fact_call
     WHERE source='gateway' GROUP BY 1;
    SELECT COUNT(*) FROM fact_call WHERE source='gateway' AND duration_ms = 0;
    -- câu trên PHẢI trả về 0: số 0 là "chưa đo", phải nạp thành NULL
    SELECT error_code, COUNT(*) FROM fact_call
     WHERE source='gateway' AND outcome='failure' GROUP BY 1;
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
import logs  # noqa: E402

log = logs.get_logger("load_gateway")

# Lùi lại bao nhiêu so với mốc đã nạp. Sổ ghi bất đồng bộ nên một dòng có thể
# xuất hiện SAU khi bộ nạp đã đi qua mốc thời gian của nó. Một giờ là rộng rãi so
# với độ trễ đo được (~4 giây), và đọc lại vùng chồng lấn không tốn gì: câu truy
# vấn chạy bằng chỉ mục, còn `ON CONFLICT DO NOTHING` lo phần trùng.
OVERLAP = timedelta(hours=1)

# Giờ Việt Nam. Cùng hằng số với load_ralli.py, cùng lý do.
VN_OFFSET = timedelta(hours=7)

SOURCE = "gateway"

# Chỉ cột cần dùng, và bóc JSON ngay trong PostgreSQL - xem mục TỐC ĐỘ.
# Hậu tố LiteLLM gắn vào `request_id` của dòng trúng cache. Đặt tên MỘT chỗ vì nó
# được dùng ở hai nơi phải khớp nhau tuyệt đối: chỗ bỏ dòng (vòng lặp nạp) và chỗ
# đếm dòng đã bỏ (phép đối chiếu toàn sổ). Hai chỗ lệch nhau là bộ nạp dừng.
HAU_TO_CACHE = "_cache_hit"

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
           (metadata->'cost_breakdown'->>'total_cost')::numeric,
           status,
           NULLIF(request_duration_ms, 0),
           NULLIF(metadata->'error_information'->>'error_code', ''),
           api_key,
           -- BAY 5: `cache_hit` la TEXT, va "khong co thong tin" duoc ghi bang
           -- CHUOI 'None' chu khong phai SQL NULL. Do 01/09: 'None' 41 dong,
           -- 'False' 5, 'True' 1 - khong mot dong NULL nao. Nen o VE NGUON,
           -- `IS NULL` tra 0 dong va `IS NOT TRUE` thi LOI KIEU.
           --
           -- Dich bang CASE chu KHONG dung ::boolean: gap gia tri thu tu thi
           -- ep kieu nem loi giua chung, con CASE quy ve NULL va bo dem duoi
           -- day se keu. Cung cach da lam voi `outcome`.
           CASE WHEN cache_hit = 'True'  THEN true
                WHEN cache_hit = 'False' THEN false
                ELSE NULL END,
           COALESCE(cache_hit, 'None') NOT IN ('True', 'False', 'None'),
           -- BAY 6: DOC `completion_tokens_details`, KHONG `prompt_tokens_details`.
           -- Ban dau cua de xuat tro nham khoi. CA HAI khoi deu co `text_tokens`
           -- day du (42/42), nen doc nham VAN ra so - chi la so cua chieu NGUOC
           -- lai. Khong crash, khong ai thay.
           --
           -- `output_modality` la NHAN, khong phai so token - dung quy uoc cua
           -- fact_monitoring.output_modality ('text' | NULL). Do 03/09 tren 42
           -- luot thanh cong: text_tokens > 0 la 42/42, audio/image/video deu 0.
           -- Gap modality khac thi tra NULL va DEM (cot ke tiep), chu khong dan
           -- nhan 'text' cho mot phan hoi khong phai van ban.
           CASE WHEN COALESCE((metadata->'usage_object'->'completion_tokens_details'->>'audio_tokens')::bigint, 0) > 0
                  OR COALESCE((metadata->'usage_object'->'completion_tokens_details'->>'image_tokens')::bigint, 0) > 0
                  OR COALESCE((metadata->'usage_object'->'completion_tokens_details'->>'video_tokens')::bigint, 0) > 0
                     THEN NULL
                WHEN COALESCE((metadata->'usage_object'->'completion_tokens_details'->>'text_tokens')::bigint, 0) > 0
                     THEN 'text'
                ELSE NULL END,
           -- co modality LA khong (de bo dem keu, thay vi im lang tra NULL)
           COALESCE((metadata->'usage_object'->'completion_tokens_details'->>'audio_tokens')::bigint, 0) > 0
             OR COALESCE((metadata->'usage_object'->'completion_tokens_details'->>'image_tokens')::bigint, 0) > 0
             OR COALESCE((metadata->'usage_object'->'completion_tokens_details'->>'video_tokens')::bigint, 0) > 0,
           -- `thinking_enabled`: CHI khang dinh khi LiteLLM CO bao khoa
           -- `reasoning_tokens`. Khoa VANG MAT -> NULL, khong phai false.
           --
           -- Day la mot SAI KHAC CO Y so voi cong thuc viet trong design ⑧
           -- (`reasoning_tokens IS NOT NULL AND > 0`, tuc ra FALSE khi vang
           -- mat). Ly do: Gemini KHONG gui khoa nay cho model khong suy luan,
           -- nen "vang mat" nghia la nha cung cap khong noi gi - khac han
           -- "da do va bang khong". Ghi false cho 40/42 dong la khang dinh mot
           -- phep do chua ai thuc hien. Cung ky luat da ap cho `duration_ms`
           -- (006), `cached_tokens` (008) va `cache_hit` (007).
           CASE WHEN (metadata->'usage_object'->'completion_tokens_details'->>'reasoning_tokens') IS NULL
                     THEN NULL
                ELSE (metadata->'usage_object'->'completion_tokens_details'->>'reasoning_tokens')::bigint > 0
                END
      FROM "LiteLLM_SpendLogs"
     WHERE status IS NOT NULL
"""

COLUMNS = ["call_id", "agent_id", "ts_raw", "tz_confirmed", "ts_local",
           "user_id", "account_id", "unit_id", "model_id", "prompt_tokens",
           "completion_tokens", "total_tokens", "cached_tokens",
           "source", "cost_usd", "duration_ms", "outcome", "error_code",
           "raw_model", "virtual_key_id", "cache_hit",
           "output_modality", "thinking_enabled"]

# Khoa quan tri chung. LiteLLM ghi THANG chuoi nay vao `api_key`, khong bam -
# nen cot nguon tron hai loai gia tri. Xem COMMENT cua fact_call.virtual_key_id.
MASTER_KEY = "litellm_proxy_master_key"


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


def build_rows(ledger, agent_by_code, models, accounts, anchors, units):
    """Ánh xạ dòng sổ -> dòng `fact_call`, kèm bộ đếm mọi thứ bị bỏ hoặc hụt."""
    rows = []
    stats = {
        "doc_tu_so": len(ledger),
        "bo_khong_co_tag": 0,
        "bo_nhieu_tag": 0,
        "bo_ban_sao_cache": 0,
        "model_chua_khai": 0,
        "hong_truoc_khi_chot_tuyen": 0,
        "nap_luot_hong": 0,
        "trang_thai_la": 0,
        "duration_null": 0,
        "end_user_rong": 0,
        "danh_tinh_khong_noi_duoc": 0,
        "cached_null": 0,
        "cost_null": 0,
        "khoa_tong": 0,
        "trung_cache": 0,
        "bi_danh": 0,
        "cache_hit_la": 0,
        "khong_ro_don_vi": 0,
        "modality_la": 0,
        "modality_null": 0,
        "thinking_null": 0,
        "co_suy_luan": 0,
    }
    # Token của những dòng BỊ BỎ, tách theo lý do. Đếm số dòng thôi là chưa đủ:
    # "bỏ 6 dòng" nghe như chuyện nhỏ, "bỏ 6 dòng mang 760 token" thì không.
    bo_token = {"bo_khong_co_tag": 0, "bo_nhieu_tag": 0, "bo_ban_sao_cache": 0}
    bo_ma = {"bo_khong_co_tag": [], "bo_nhieu_tag": [], "bo_ban_sao_cache": []}

    def bo(khoa: str, ma: str, tong) -> None:
        stats[khoa] += 1
        bo_token[khoa] += int(tong or 0)
        bo_ma[khoa].append(ma)

    for (call_id, ts_raw, model, end_user, tags,
         prompt_tokens, completion_tokens, total_tokens,
         cached_tokens, cost_usd, outcome, duration_ms, error_code,
         virtual_key_id, cache_hit, cache_hit_la,
         output_modality, modality_la, thinking_enabled) in ledger:

        # BẪY 7: BẢN SAO CỦA CÚ CACHE HIT. Bỏ TRƯỚC mọi bước khác, và bỏ CÓ TÊN.
        #
        # LiteLLM ghi thêm một dòng cho cú cache hit, mang chính `request_id` của
        # dòng gốc cộng hậu tố `_cache_hit<epoch>`, và LẶP LẠI nguyên token của
        # dòng gốc. Đo 05/09/2026 trên toàn sổ: đúng 1 dòng như vậy,
        # `GsaVavubFOD21e8PnvHx2QE_cache_hit1788200480.9219387`, 352 token, và
        # dòng gốc `GsaVavubFOD21e8PnvHx2QE` tồn tại với ĐÚNG 352 token. Nhà cung
        # cấp xác nhận độc lập: ngày 01/09 họ phục vụ 1 lượt, 8 vào + 344 ra.
        # Nạp cả hai là đếm đôi 352 token.
        #
        # VÌ SAO PHẢI BỎ TƯỜNG MINH DÙ HÔM NAY NÓ ĐÃ RỚT SẴN: hôm nay dòng này bị
        # loại vì KHÔNG CÓ TAG ĐỊNH DANH - tức là rớt vì một lý do CHẲNG LIÊN
        # QUAN. Ngày nào khâu định danh được nới ra (và đó là việc phải làm - xem
        # cảnh báo cuối hàm này), bản sao sẽ theo cửa đó mà vào, và không phép
        # kiểm nào hiện có bắt được: tổng token vẫn "khớp sổ nguồn", chỉ có điều
        # sổ nguồn tự nó đã đếm đôi.
        if HAU_TO_CACHE in call_id:
            bo("bo_ban_sao_cache", call_id, total_tokens)
            continue

        agent_id, ly_do = resolve_agent(tags, agent_by_code)
        if agent_id is None:
            # `fact_call.agent_id` là NOT NULL, nên đây không chỉ là chính sách -
            # schema cưỡng chế. Đếm rồi bỏ, không nuốt lặng.
            bo("bo_khong_co_tag" if ly_do == "khong co tag dinh danh"
               else "bo_nhieu_tag", call_id, total_tokens)
            continue

        # BẪY 4: tra theo tên upstream ở cột `model`. Dòng nào chưa khai trong
        # rules.GATEWAY_MODELS sẽ ra None - nạp vào với model_id NULL và ĐẾM,
        # chứ không loại. Mất dòng thì không ai biết; NULL thì đếm được.
        model_id = models.get((SOURCE, model))
        if model_id is None:
            # TACH HAI NGHIA. Dong `success` khong noi duoc model = tuyen chua
            # khai trong rules.GATEWAY_MODELS -> VIEC PHAI LAM. Dong `failure`
            # thi thuong mang ten BI DANH vi request chet TRUOC khi Router chot
            # tuyen -> binh thuong, khong phai loi. Gop hai thu vao mot bo dem la
            # de mot con so dang bao dong chim trong tieng on thuong ngay.
            if outcome == "failure":
                stats["hong_truoc_khi_chot_tuyen"] += 1
            else:
                stats["model_chua_khai"] += 1

        # BẪY 2: chuỗi rỗng, không phải NULL.
        user_id = end_user or None
        if user_id is None:
            stats["end_user_rong"] += 1

        # `account_id` nằm trong khoá chính của fact_usage_daily nên KHÔNG được
        # NULL. Neo tra theo (kind, unit_agent_id) - xem anchor_account_lookup().
        neo = anchors.get(agent_id)

        # ĐỊNH DANH PHẢI THUỘC ĐÚNG AGENT GỬI REQUEST.
        #
        # Trước 31/08 chỗ này tra thẳng `accounts.get(end_user)`, tức là tin bất
        # kỳ chuỗi nào Gateway gửi tới. Đo ra một đường hỏng có thật: bảng
        # `account` CÓ dòng `admin` (account_id 1, "Quản trị viên", thuộc agent 5
        # - TLA Hợp Đồng) và dòng đó ĐÃ mang 480 lượt / 1.588.404 token. Ngày một
        # agent gửi `X-User: admin` - tên đăng nhập cục bộ của chính nó - lưu
        # lượng đó bị trộn vào lịch sử của một người dùng TLA Hợp Đồng. Im lặng,
        # tổng vẫn khớp, không phép kiểm nào bắt được.
        #
        # Bản vá đầu chỉ nhận định danh tra ra ĐÚNG tài khoản neo. Chặn được
        # `admin`, nhưng SAI với agent nhiều người dùng: cả 45 người thật của TLA
        # Hợp Đồng cũng khác neo, nên sẽ bị gộp hết vào một tài khoản.
        #
        # Quy tắc đúng cho CẢ HAI loại agent: định danh hợp lệ khi tài khoản của
        # nó thuộc chính agent đang gửi request.
        #
        #     svc.dms-feedback -> agent 6, request agent 6  ->  NHAN
        #     admin            -> agent 5, request agent 6  ->  TU CHOI
        #     pbh1_ntlong      -> agent 5, request agent 5  ->  NHAN
        #
        # Quy ước 20/08: 6/8 agent được coi là chỉ có MỘT người dùng, và người đó
        # là tài khoản dịch vụ `svc.<code>` (kind='service_account'). Với chúng,
        # neo CHÍNH LÀ đáp án đúng, không phải giải pháp tạm.
        tra_ra = accounts.get(user_id) if user_id else None
        if tra_ra is not None and tra_ra[1] == agent_id:
            account_id = tra_ra[0]
        else:
            if user_id is not None:
                stats["danh_tinh_khong_noi_duoc"] += 1
            account_id = neo

        # PHONG BAN tra tu TAI KHOAN da quy duoc, KHONG tu tag cua request.
        # Tag noi agent nao gui, khong noi nguoi gui thuoc phong ban nao - xem
        # connect.account_unit_lookup(). Dong nao khong tra ra thi de NULL va DEM,
        # chu khong bia mot don vi.
        unit_id = units.get(account_id)
        if unit_id is None:
            stats["khong_ro_don_vi"] += 1

        if cached_tokens is None:
            stats["cached_null"] += 1
        if cost_usd is None:
            stats["cost_null"] += 1
        if outcome == "failure":
            stats["nap_luot_hong"] += 1
        elif outcome != "success":
            # LiteLLM hom nay chi dat hai gia tri. Nhung neu mot ban sau them
            # gia tri thu ba (vi du 'timeout'), dong do se nap vao roi bi bo loc
            # `outcome = 'success'` o tang tong hop loai IM LANG. Dem o day de
            # no keu, thay vi mat du lieu ma khong ai biet.
            stats["trang_thai_la"] += 1
        # `duration_ms` da duoc NULLIF(...,0) o tang SQL: Gateway ghi 0 cho MOI
        # luot hong, ke ca luot DA goi toi nha cung cap va bi tu choi - nen 0 la
        # su vang mat cua phep do, khong phai phep do.
        if duration_ms is None:
            stats["duration_null"] += 1
        if virtual_key_id == MASTER_KEY:
            # Luot di bang khoa quan tri chung. No VAN quy duoc ve agent nho tag,
            # nen no NAM LAN trong luu luong that cua agent - va truoc change nay
            # khong co cach nao tach ra. Con so phai giam ve 0 khi 8 agent deu co
            # khoa rieng.
            stats["khoa_tong"] += 1
        if cache_hit is True:
            stats["trung_cache"] += 1
        if cache_hit_la:
            stats["cache_hit_la"] += 1
        if modality_la:
            # Phan hoi mang token audio/image/video. Hom nay 0/42, nhung ngay no
            # xuat hien thi cot `output_modality` de NULL - va bo dem nay la thu
            # duy nhat noi ra rang co mot loai phan hoi ta chua biet dat ten.
            stats["modality_la"] += 1
        if output_modality is None:
            stats["modality_null"] += 1
        if thinking_enabled is None:
            # LiteLLM khong bao khoa `reasoning_tokens`. KHONG suy ra false -
            # xem ghi chu o BASE_SQL.
            stats["thinking_null"] += 1
        elif thinking_enabled:
            stats["co_suy_luan"] += 1
        if "/" not in (model or ""):
            # Ten KHONG mang tien to nha cung cap = `model_name` khai trong
            # config.gateway.yaml, tuc BI DANH. Router chi thay ten upstream vao
            # sau khi da chot tuyen, nen dong mang bi danh la dong chet TRUOC do.
            stats["bi_danh"] += 1

        rows.append((
            call_id, agent_id, ts_raw, True, ts_raw + VN_OFFSET,
            user_id, account_id, unit_id, model_id, prompt_tokens,
            completion_tokens, total_tokens, cached_tokens,
            SOURCE, cost_usd, duration_ms, outcome, error_code,
            model, virtual_key_id, cache_hit,
            output_modality, thinking_enabled,
        ))
    # Tra ca `bo_token` / `bo_ma`: bao cao phai noi duoc BO BAO NHIEU TOKEN va
    # BO DONG NAO, khong chi bo bao nhieu dong.
    stats["bo_token"] = bo_token
    stats["bo_ma"] = bo_ma
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
        log.error("CANNOT REACH THE GATEWAY LEDGER: %s",
                  connect.mask_dsn(args.gateway_db))
        log.error("  %s: %s", type(exc).__name__,
                  str(exc).strip().splitlines()[0])
        log.error("  gateway down? run: docker compose --profile gateway up -d")
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
        log.error("STOPPED: %d rows carry a non-zero margin/discount", n_margin)
        log.error("  `total_cost` is no longer the provider's own price")
        log.error("  decide which figure to load before running again")
        gw_cn.close()
        cn.close()
        return 1

    since = None if args.full else watermark(cn)
    if since is not None:
        since = since - OVERLAP
    log.info("loading from %s", connect.mask_dsn(args.gateway_db))
    log.info("  watermark: %s (rewound by %s)",
             "ALL" if since is None else since, OVERLAP)

    ledger = read_ledger(gw_cn, since)

    agent_by_code = connect.agent_code_lookup(cn)
    models = connect.model_lookup(cn)
    accounts = connect.account_lookup(cn)
    anchors = connect.anchor_account_lookup(cn)
    units = connect.account_unit_lookup(cn)

    rows, stats = build_rows(ledger, agent_by_code, models, accounts, anchors,
                             units)

    truoc = connect.query_one(
        cn, f"SELECT COUNT(*) FROM fact_call WHERE source = '{SOURCE}'")[0]
    if args.dry_run:
        log.info("  --dry-run: nothing written")
        sau = truoc
    else:
        # DO UPDATE cho BA COT MOI, khong phai DO NOTHING.
        #
        # Bay bat duoc 31/08 khi them ba cot nay: `DO NOTHING` bo qua HOAN TOAN
        # dong da co, nen 38 dong nap tu truoc giu nguyen outcome/duration_ms
        # NULL. Hau qua neu bo lot: (a) them bo loc `outcome='success'` o tang
        # tong hop se lam token gateway ve 0 - hong im lang; (b) muc dich chinh
        # cua change - do tre tho - khong dat duoc dong nao.
        #
        # An toan vi ba cot nay suy tu chinh so goc, ma dong trong so la BAT BIEN
        # sau khi ghi. Chay lai bao nhieu lan cung ra cung mot gia tri.
        #
        # CHI sau cot suy tu so goc. Khong DO UPDATE ca hang: neu mai kia mot khau anh xa
        # doi (vi du dim_model_alias), ta KHONG muon lich su bi viet lai im lang.
        connect.insert_many(
            cn, ph, "fact_call", COLUMNS, rows,
            on_conflict="ON CONFLICT (call_id) DO UPDATE SET"
                        " duration_ms    = EXCLUDED.duration_ms,"
                        " outcome        = EXCLUDED.outcome,"
                        " error_code     = EXCLUDED.error_code,"
                        " raw_model      = EXCLUDED.raw_model,"
                        " virtual_key_id = EXCLUDED.virtual_key_id,"
                        " cache_hit      = EXCLUDED.cache_hit,"
                        " unit_id        = EXCLUDED.unit_id,"
                        # 008: thieu hai dong nay thi 41 dong da nap giu
                        # NULL VINH VIEN, va bang chi day len tu luot goi
                        # MOI - dung cai bay da mac 31/08 voi duration_ms.
                        " output_modality  = EXCLUDED.output_modality,"
                        " thinking_enabled = EXCLUDED.thinking_enabled")
        cn.commit()
        sau = connect.query_one(
            cn, f"SELECT COUNT(*) FROM fact_call WHERE source = '{SOURCE}'")[0]

    gw_cur = gw_cn.cursor()

    # `sau - truoc` la so dong CHEN MOI. Tu khi dung DO UPDATE (31/08), lan chay
    # nao cung ghi de ba cot duration_ms/outcome/error_code len dong da co - nen
    # "chen them 0" KHONG co nghia la "khong lam gi".
    log.info("  read %d rows | usable %d | inserted %d | overwritten %d",
             stats["doc_tu_so"], len(rows), sau - truoc,
             len(rows) - (sau - truoc))
    # BỎ BAO NHIÊU DÒNG là nửa câu trả lời; nửa còn lại là BỎ BAO NHIÊU TOKEN và
    # BỎ DÒNG NÀO. "bỏ 6 dòng" nghe như chuyện nhỏ; "bỏ 6 dòng mang 760 token,
    # trong đó một dòng THÀNH CÔNG 25 token" thì không ai bỏ qua được nữa.
    for khoa, nhan in (("bo_khong_co_tag",  "no identity tag"),
                       ("bo_nhieu_tag",     "several identity tags"),
                       ("bo_ban_sao_cache", "cache-hit duplicate row")):
        n = stats[khoa]
        if not n:
            continue
        ma = stats["bo_ma"][khoa]
        log.info("  dropped %d rows (%s) carrying %s tokens: %s%s",
                 n, nhan, f"{stats['bo_token'][khoa]:,}",
                 ", ".join(m[:28] for m in ma[:5]),
                 f" ... +{len(ma) - 5}" if len(ma) > 5 else "")
    if not any(stats[k] for k in ("bo_khong_co_tag", "bo_nhieu_tag",
                                  "bo_ban_sao_cache")):
        log.info("  dropped: nothing - every source row in range was loaded")
    if stats["trang_thai_la"]:
        log.warning("  %d rows carry a status other than success/failure -"
                    " the rollup would drop them silently",
                    stats["trang_thai_la"])
    log.info("  failed calls loaded %d | model not declared %d"
             " | failed before routing %d",
             stats["nap_luot_hong"], stats["model_chua_khai"],
             stats["hong_truoc_khi_chot_tuyen"])
    log.info("  end_user empty %d | identity unresolvable %d",
             stats["end_user_rong"], stats["danh_tinh_khong_noi_duoc"])
    log.info("  cached_tokens NULL %d | cost_usd NULL %d | duration_ms NULL %d",
             stats["cached_null"], stats["cost_null"], stats["duration_null"])
    log.info("  via MASTER KEY %d/%d | cache hits %d | alias model names %d"
             " | unit unknown %d",
             stats["khoa_tong"], len(rows), stats["trung_cache"],
             stats["bi_danh"], stats["khong_ro_don_vi"])
    if stats["cache_hit_la"]:
        log.warning("  %d rows have a cache_hit outside True/False/None -"
                    " mapped to NULL, check the LiteLLM version",
                    stats["cache_hit_la"])
    log.info("  output_modality NULL %d | thinking reported %d/%d"
             " | reasoning tokens seen %d",
             stats["modality_null"],
             len(rows) - stats["thinking_null"], len(rows),
             stats["co_suy_luan"])
    if stats["modality_la"]:
        log.warning("  %d rows carry audio/image/video tokens - output_modality"
                    " left NULL because we have no label for them yet",
                    stats["modality_la"])

    # Phân bố mã lỗi của những dòng ĐÃ NẠP. Không in ra thì không ai biết Gateway
    # đang hỏng vì cái gì - mà câu trả lời nằm sẵn trong sổ.
    gw_cur.execute(
        '''SELECT COALESCE(
                   NULLIF(metadata->'error_information'->>'error_code', ''),
                   '(no code)') AS ma,
                  COUNT(*)
             FROM "LiteLLM_SpendLogs"
            WHERE status = %s
            GROUP BY 1 ORDER BY 2 DESC''',
        ("failure",))
    phan_bo = ", ".join(f"{m}={n}" for m, n in gw_cur.fetchall())
    log.info("  error codes of failed calls in the ledger: %s",
             phan_bo or "(no failed calls)")

    # SỐ LƯỢT HỎNG KHÔNG ĐỦ - PHẢI IN KÈM TOKEN SỔ GHI CHO CHÚNG
    # ---------------------------------------------------------
    # In riêng số lượt là mời người đọc tự điền vào chỗ trống, và ai cũng điền
    # "hỏng thì chắc chẳng tốn gì". Đo 04/09/2026 trên dữ liệu 31/08/2026 thì điều
    # đó SAI: nhà cung cấp báo 41 lượt với `response_code = 200` cho TẤT CẢ, trong
    # khi sổ này ghi 5 lượt hỏng. Hai lượt đã được phục vụ xong và đã tiêu token
    # thật - 6.334 token, 12,29% của ngày hôm đó - nhưng sổ ghi cho chúng 0.
    #
    # Nên con số dưới đây là ĐIỀU SỔ KHAI, không phải ĐIỀU ĐÃ TIÊU. Hai chuyện đó
    # trùng nhau chỉ khi lượt hỏng thật sự hỏng trước khi nhà cung cấp phục vụ.
    # Câu trả lời thật nằm ở `fact_provider_daily`, và phép kiểm đối chiếu ở
    # scripts/audit_db.py nhóm I là chỗ so hai con số đó.
    #
    # Tên gọi của hình dạng lỗi: `failed_is_not_free`.
    gw_cur.execute(
        '''SELECT COUNT(*),
                  COALESCE(SUM(prompt_tokens), 0),
                  COALESCE(SUM(completion_tokens), 0),
                  COALESCE(SUM(total_tokens), 0),
                  COUNT(*) FILTER (WHERE COALESCE(total_tokens, 0) = 0)
             FROM "LiteLLM_SpendLogs" WHERE status = %s''',
        ("failure",))
    n_hong, h_vao, h_ra, h_tong, h_khong = gw_cur.fetchone()
    log.info("  failed calls in the ledger: %d rows | the ledger DECLARES"
             " %s in + %s out = %s tokens for them (%d of them declare zero)",
             n_hong, f"{h_vao:,}", f"{h_ra:,}", f"{h_tong:,}", h_khong)
    if h_khong:
        log.warning("  %d failed rows declare ZERO tokens - that is what the"
                    " LEDGER SAYS, not what was SPENT. A call the provider"
                    " served and then the proxy lost still burned tokens."
                    " Check scripts/audit_db.py group I against"
                    " fact_provider_daily before believing the zero.",
                    h_khong)

    # Đối chiếu với chính sổ gốc, không với số ghim. So trên TOÀN BỘ sổ chứ không
    # riêng vùng vừa đọc: đó mới là câu hỏi thật - "mọi thứ Gateway ghi đã vào
    # đây chưa".
    #
    # Từ 31/08 nạp CẢ HAI trạng thái, nên vế nguồn không còn lọc `success` nữa.
    gw_cur.execute('SELECT COUNT(*), COALESCE(SUM(total_tokens), 0)'
                   ' FROM "LiteLLM_SpendLogs" WHERE status IS NOT NULL')
    src_rows, src_tokens = gw_cur.fetchone()
    dst_rows, dst_tokens = connect.query_one(
        cn, "SELECT COUNT(*), COALESCE(SUM(total_tokens), 0)"
            f" FROM fact_call WHERE source = '{SOURCE}'")

    log.info("  whole-ledger check: source %d rows/%s tokens"
             " | target %d rows/%s tokens",
             src_rows, f"{src_tokens:,}", dst_rows, f"{dst_tokens:,}")

    # Số dòng bị bỏ phải đếm trên CẢ SỔ, không phải trên cửa sổ vừa đọc: lần
    # chạy tăng dần chỉ đọc vài dòng, còn `src_rows`/`dst_rows` là số của cả sổ.
    # Lấy `bo_qua` của cửa sổ mà so với tổng thì lần nào cũng báo lệch giả.
    # PHẢI đếm CẢ HAI lý do bỏ, theo ĐÚNG thứ tự vòng lặp trên: bản sao cache bị
    # bỏ TRƯỚC (bẫy 7), rồi mới tới chuyện tag định danh.
    #
    # Trước 11/09/2026 câu này chỉ đếm vế tag. Hệ quả đo được hôm đó: bật cache,
    # gọi 3 lượt, sinh 2 dòng `_cache_hit` MANG ĐỦ một tag định danh. Chúng bị bỏ
    # ở dòng 312 nên không vào `fact_call`, mà cũng không lọt vào vế "bỏ qua" này
    # vì có đúng 1 tag. Phép đối chiếu thiếu 2 dòng/40 token, báo MISMATCH, rồi
    # DỪNG HẲN trước bước tổng hợp. Tức là: CHỈ CẦN MỘT dòng trúng cache trong sổ
    # là cả đường nạp đứng, và đứng mãi cho tới khi ai đó gỡ dòng đó ra.
    #
    # Dùng `strpos` chứ KHÔNG dùng `LIKE '%_cache_hit%'`: trong LIKE thì `_` là ký
    # tự đại diện khớp một ký tự bất kỳ, nên mẫu đó còn khớp cả `Xcache_hit`.
    # `strpos` so nguyên văn, đúng thứ `"_cache_hit" in call_id` ở dòng 312 làm.
    gw_cur.execute(
        'SELECT COUNT(*), COALESCE(SUM(total_tokens), 0),'
        '       COUNT(*) FILTER (WHERE strpos(request_id, %s) > 0),'
        '       COALESCE(SUM(total_tokens)'
        '                FILTER (WHERE strpos(request_id, %s) > 0), 0)'
        '  FROM "LiteLLM_SpendLogs" WHERE status IS NOT NULL'
        '   AND (strpos(request_id, %s) > 0'
        '        OR (SELECT COUNT(*)'
        '              FROM jsonb_array_elements_text('
        "                     COALESCE(request_tags, '[]'::jsonb)) AS t"
        '             WHERE t = ANY(%s)) <> 1)',
        (HAU_TO_CACHE, HAU_TO_CACHE, HAU_TO_CACHE, list(agent_by_code)))
    bo_qua_ca_so, token_bo_qua, bo_cache_ca_so, token_bo_cache = gw_cur.fetchone()
    log.info("  skipped across the ledger: %d rows, %d tokens"
             " (of which cache-hit duplicates: %d rows, %d tokens)",
             bo_qua_ca_so, token_bo_qua, bo_cache_ca_so, token_bo_cache)

    # Đối chiếu HAI chiều, không chỉ số dòng. Số dòng khớp mà token lệch nghĩa là
    # ánh xạ cột hỏng - đúng loại lỗi mà phép đếm dòng không thấy.
    errors = []
    if not args.dry_run:
        if dst_rows + bo_qua_ca_so != src_rows:
            errors.append(f"rows: target {dst_rows} + skipped {bo_qua_ca_so}"
                          f" != nguon {src_rows}")
        if int(dst_tokens) + int(token_bo_qua) != int(src_tokens):
            errors.append(f"tokens: target {dst_tokens} + skipped {token_bo_qua}"
                          f" != nguon {src_tokens}")

    gw_cn.close()
    cn.close()
    if errors:
        for e in errors:
            log.error("  MISMATCH: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
