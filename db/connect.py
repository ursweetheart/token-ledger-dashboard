"""Mở kết nối và dựng lại database - dùng chung cho mọi script nạp.

CHỈ POSTGRESQL. SQLITE ĐÃ BỊ GỠ 24/08/2026.
-------------------------------------------
File này TỪNG hứa "hai hệ quản trị, một bản schema". Đừng khôi phục lời hứa đó -
nó đã sai từ 21/08 và không ai biết. Ba điều kiện của một đường quay về, đo ngày
24/08, không điều nào còn đúng:

    có dữ liệu để quay về   var/token_ledger.sqlite bị xoá 17/08, var/ rỗng
    dựng lại được           tệp schema đơn khối cũ HỎNG CÚ PHÁP trên SQLite từ 21/08
    có phép kiểm canh       chưa từng có phép nào chạy trên SQLite

Chỗ hỏng nằm ở `INSERT INTO ref_source`: hai chuỗi viết LIỀN KỀ nhau. PostgreSQL
nối lại theo chuẩn SQL, SQLite báo lỗi cú pháp. Bảng `ref_source` ra đời 21/08,
tức SAU ngày database SQLite biến mất - nên lỗi nằm im ba ngày, không ai chạm tới.

Một đường quay về không dựng được, không có dữ liệu, và không ai kiểm thì không
phải đường quay về. Nó tệ hơn không có gì: nó làm người đọc file này tin rằng có.

VÌ SAO KHÔNG PHẢI SQLITE, GHI LẠI ĐỂ KHÔNG AI QUAY LẠI
------------------------------------------------------
SQLite là MỘT FILE: không đi qua mạng nên tiến trình trong container khác không
đọc được, và không có schema riêng lẫn GRANT theo user nên không chia quyền theo
service được. Cả hai là chặn đường cứng cho việc chạy nhiều bản sau một load
balancer - tức chặn đúng kiến trúc mà Master Plan giai đoạn 5 đang nhắm tới.

MỘT NGUỒN SỰ THẬT
-----------------
DEFAULT_DSN dưới đây là chỗ DUY NHẤT quyết định database mặc định. Không file nào
khác được dựng chuỗi kết nối mặc định của riêng nó.

Đã có sự cố đúng hình dạng đó: scripts/rebuild_db.py từng khai
`default=str(ROOT / "var" / "token_ledger.sqlite")` độc lập với hằng số này, và
scripts/update_dashboard.py gọi nó KHÔNG truyền --db. Hệ quả: đổi file này xong
mà đường ống vẫn dựng lại database cũ, không lỗi nào báo ra.

Thứ tự ưu tiên:
    1. TOKEN_LEDGER_DSN        - đổi được TOÀN BỘ hệ thống bằng một biến
    2. PG* dựng thành chuỗi    - khớp tên biến của docker-compose.yml
    3. --db trên dòng lệnh     - ghi đè cho một lần chạy
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "db"                # ma: migration + danh muc .sql
# VAR_DIR bo 24/08/2026 cung voi SQLite - no chi ton tai de tro toi file .sqlite,
# va sau khi go thi khong file .py nao con dung toi. Thu muc var/ van con, nay
# chua ban chup bo so bat bien cua tools/baseline_db.py.

# Tên biến VÀ giá trị mặc định KHỚP docker-compose.yml, nên `docker compose up -d`
# rồi chạy script là nối được ngay, không phải đặt gì. Đặt tên khác sẽ thành hai
# bộ cấu hình phải giữ khớp bằng tay - đúng loại lỗi im lặng mà file này đang dọn.
PG_HOST = os.environ.get("PGHOST", "127.0.0.1")
PG_PORT = os.environ.get("PGPORT", "5432")
PG_USER = os.environ.get("PGUSER", "token")
PG_PASSWORD = os.environ.get("PGPASSWORD", "token_local")
# Runtime ledger hiện hành: token_ledger_v2. Quyết định giữ song song 27/08/2026:
# không DROP/rename để trả tên; token_ledger cũ là bản legacy đối chiếu/rollback.
#
# v2 là bản dựng HOÀN TOÀN từ chuỗi migration rồi nạp lại từ data/, và đã khớp
# 23/23 khoá với bản cũ (867.657.110 token · $291,985601 · audit 36/31/5/0 ·
# check_api 19/19).
#
# `token_ledger` cũ VẪN CÒN NGUYÊN. Quay lui runtime = đặt PGDATABASE hoặc
# TOKEN_LEDGER_DSN về database đó. Gateway ingestion tương lai chỉ ghi vào v2;
# không ghi cùng một dòng vào cả hai database.
PG_DATABASE = os.environ.get("PGDATABASE", "token_ledger_v2")

# Dùng `or` chứ không `os.environ.get(k, mac_dinh)`: biến đặt thành chuỗi rỗng
# cũng phải rơi về mặc định, không được thành DSN rỗng.
DEFAULT_DSN = os.environ.get("TOKEN_LEDGER_DSN") or (
    f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}")

# Sổ của API Gateway. Database RIÊNG (`litellm`), cùng một instance PostgreSQL.
#
# VÌ SAO KHÔNG GỘP VÀO `token_ledger_v2` (chốt 31/08/2026): LiteLLM tự chạy
# migration bằng Prisma. Gộp nghĩa là mỗi lần nâng phiên bản nó có quyền ALTER
# ngay trong database chứa dữ liệu dashboard. Cái giá phải trả là PostgreSQL
# không cho JOIN xuyên database - `postgres_fdw` và `dblink` đều CHƯA cài - nên
# db/load_gateway.py mở HAI kết nối và ánh xạ ở tầng Python.
#
# Vai `gateway_readonly` chỉ SELECT được đúng một bảng `LiteLLM_SpendLogs`, và
# mang `default_transaction_read_only = on`. Xem docker/read-only-gateway.sql.
# Vai chủ sở hữu `llmproxy` CỐ Ý không dùng ở đây: nó ghi được.
GW_USER = os.environ.get("GATEWAY_READONLY_USER", "gateway_readonly")
GW_PASSWORD = os.environ.get("GATEWAY_READONLY_PASSWORD", "gateway_readonly_local")
GW_DATABASE = os.environ.get("GATEWAY_PGDATABASE", "litellm")

GATEWAY_DSN = os.environ.get("GATEWAY_DSN") or (
    f"postgresql://{GW_USER}:{GW_PASSWORD}@{PG_HOST}:{PG_PORT}/{GW_DATABASE}")

# DSN của lần chạy hiện tại, khi nó KHÁC mặc định.
#
# Vì sao cần thêm biến này (24/08/2026): `DEFAULT_DSN` là hằng số tính MỘT LẦN lúc
# import, nên `rebuild(dsn_khac)` không đổi được nó, và `db/migrations/env.py` -
# chạy trong một ngăn xếp gọi khác - sẽ vẫn thấy database mặc định. Tức là
# `rebuild()` xoá database A rồi bảo Alembic dựng schema lên database B.
#
# `rebuild()` đặt biến này trước khi gọi Alembic và trả về `None` sau đó. env.py
# đọc nó. Thứ tự ưu tiên trong env.py:  -x db=...  >  ACTIVE_DSN  >  DEFAULT_DSN
#
# Vẫn giữ đúng nguyên tắc "một nguồn sự thật": chuỗi kết nối vẫn chỉ được quyết
# định trong file này, không nơi nào khác dựng chuỗi mặc định của riêng nó.
ACTIVE_DSN: str | None = None


def _chan_sqlite(dsn: str) -> None:
    """Dừng ngay nếu DSN trỏ vào một file SQLite.

    HỎNG TO TIẾNG, KHÔNG HỎNG IM LẶNG. Không có hàm này thì `--db du_lieu.sqlite`
    đi thẳng vào psycopg2, và thông báo lỗi sẽ nói về chuỗi kết nối chứ không nói
    về điều người dùng thật sự làm sai. Tệ hơn: nếu mai kia có ai thêm lại một
    nhánh sqlite3 thì nó sẽ lặng lẽ TẠO một file rỗng rồi chạy nửa vời.

    Đây là thứ duy nhất còn sót lại của `is_sqlite()` cũ, và nó tồn tại để nói
    KHÔNG cho rõ ràng.
    """
    if dsn.endswith((".sqlite", ".db")):
        raise SystemExit(
            f"DSN trỏ vào một file SQLite: {dsn}\n"
            "SQLite đã bị gỡ khỏi dự án ngày 24/08/2026 - xem ghi chú đầu file này.\n"
            "Dùng một chuỗi kết nối PostgreSQL, ví dụ:\n"
            f"    {mask_dsn(DEFAULT_DSN)}"
        )


def mask_dsn(dsn: str) -> str:
    """Giấu mật khẩu khi in DSN ra màn hình hoặc log.

    Nơi nào biết DSN thì nơi đó phải biết cách in DSN an toàn - nên hàm này nằm
    cạnh DEFAULT_DSN chứ không nằm trong script gọi. Hai bản cài đặt của cùng một
    quy tắc bảo mật là một bản sẽ sai.

    Trước 17/08 mặc định là đường dẫn file nên in thẳng vô hại, và
    db/load_billing.py in `args.db` không che. Khi mặc định thành chuỗi Postgres
    có mật khẩu thì chính dòng đó thành chỗ rò.

    DSN là đường dẫn file thì trả về y nguyên, không cắt gì.

    CẮT Ở '@' CUỐI, KHÔNG PHẢI '@' ĐẦU
    ----------------------------------
    Mật khẩu được phép chứa '@'. Với `postgresql://u:p@ss@may/db`, cắt ở '@' đầu
    cho credentials='u:p' và host='ss@may/db' - tức đoạn 'ss' của mật khẩu CHẢY
    SANG vế host rồi được in ra nguyên văn. Phần host của URL thì không bao giờ
    chứa '@', nên cắt ở '@' cuối mới đúng.
    """
    if "://" not in dsn or "@" not in dsn:
        return dsn
    scheme, rest = dsn.split("://", 1)
    credentials, host = rest.rsplit("@", 1)
    # Không có ':' nghĩa là DSN vốn không mang mật khẩu - đừng thêm '***' vào,
    # người đọc log sẽ tưởng có một mật khẩu mà thực ra không có.
    if ":" not in credentials:
        return f"{scheme}://{credentials}@{host}"
    user = credentials.split(":", 1)[0]
    return f"{scheme}://{user}:***@{host}"


def open_db(dsn: str):
    """Trả về (connection, placeholder).

    VÌ SAO VẪN TRẢ VỀ `placeholder` KHI CHỈ CÒN MỘT HỆ
    ---------------------------------------------------
    Nó nay là hằng `"%s"`, nên nhìn qua thì thừa. Giữ lại là CÓ CHỦ Ý: gỡ nó đi
    là sửa 34 chỗ - 15 điểm gọi hàm này, cộng 19 chuỗi truy vấn nội suy biến
    placeholder, nằm rải khắp db/, scripts/, backend/. Một diff lớn như vậy mang
    rủi ro thật mà không mua thêm năng lực nào.

    (Cố ý KHÔNG viết literal của biến đó ra đây: phép kiểm 6.2 của change đếm số
    lần nó xuất hiện để chứng minh change không lan vào tầng truy vấn, và một
    dòng ghi chú cũng bị đếm. Bẫy này đã cắn một lần ngày 24/08.)

    Change `drop-the-sqlite-escape-hatch` (24/08/2026) vì thế chỉ gỡ NHÁNH RẼ,
    không chạm tầng truy vấn - và nghiệm thu bằng cách đếm lại đúng hai con số
    15 và 19. Muốn dọn nốt thì làm một change riêng.
    """
    _chan_sqlite(dsn)
    try:
        import psycopg2 as pg
    except ImportError:
        try:
            import psycopg as pg  # type: ignore
        except ImportError:
            raise SystemExit(
                "Cần psycopg2 để nối PostgreSQL:  pip install psycopg2-binary\n"
                "  hoặc:  pip install -r backend/requirements.txt\n"
                "PostgreSQL là hệ quản trị DUY NHẤT từ 24/08/2026, nên gói này\n"
                "bắt buộc - không còn đường quay về SQLite để đỡ."
            )
    return pg.connect(dsn), "%s"


def run_sql_file(cn, placeholder: str, path: Path) -> None:
    # `placeholder` giữ trong chữ ký để 15 chỗ gọi không phải đổi - xem open_db().
    with cn.cursor() as cur:
        cur.execute(path.read_text(encoding="utf-8"))


def apply_migrations(dsn: str) -> None:
    """Dựng schema bằng chuỗi migration trong db/migrations/.

    Thay cho đường nạp tệp schema đơn khối từ 24/08/2026. Từ đó schema chỉ được
    mô tả ở MỘT chỗ - chuỗi migration; baseline nằm ở
    `db/migrations/sql/001_baseline.sql`.

    Gọi Alembic qua API trong tiến trình, không qua `subprocess`: trên máy này
    `python` trên PATH là một shim trỏ đi chỗ khác, nên gọi tiến trình con là mời
    đúng loại lỗi "chạy nhầm trình thông dịch" vào một hàm vốn không có lỗi nào.
    """
    global ACTIVE_DSN
    from alembic import command
    from alembic.config import Config

    ACTIVE_DSN = dsn
    try:
        command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    finally:
        ACTIVE_DSN = None


def rebuild(dsn: str):
    """Xoá sạch rồi dựng lại: migration + 02_catalog.sql.

    CHỈ dùng cho database do script này tạo ra. Không dùng lên database thật.

    BƯỚC XOÁ SẠCH VẪN Ở ĐÂY, VÀ PHẢI Ở ĐÂY.
    ----------------------------------------
    Change `change-the-schema-without-dropping-it` mang cái tên dễ khiến người
    đọc tưởng `DROP SCHEMA` phải biến mất. Không phải. Nó chỉ làm cho việc đổi
    schema KHÔNG CÒN BẮT BUỘC phải xoá - `alembic upgrade head` gọi độc lập sẽ
    sửa tại chỗ, không đi qua hàm này.

    Còn hàm này là đường "dựng lại toàn bộ từ data/", và nó thật sự cần một schema
    trắng: bước ngay sau là nạp `02_catalog.sql`, mà nạp danh mục vào bảng đã có
    dòng là đụng khoá chính ngay.

    Hai đường dùng chung một chuỗi migration:
        rebuild()              xoá sạch  ->  migration  ->  danh mục
        alembic upgrade head   (không xoá gì, database giữ nguyên dữ liệu)
    """
    catalog = DB_DIR / "02_catalog.sql"
    if not catalog.exists():
        raise SystemExit("Chưa có db/02_catalog.sql. Chạy: python db/gen_catalog.py")

    cn, _ = open_db(dsn)
    with cn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    cn.commit()
    # ĐÓNG kết nối này trước khi Alembic mở kết nối của nó. Giữ mở thì lát nữa
    # phải tin rằng một kết nối cũ nhìn thấy bảng do kết nối khác vừa tạo -
    # đúng, nhưng là thứ phải nhớ mỗi lần đọc lại. Mở lại sau rẻ hơn.
    cn.close()

    apply_migrations(dsn)

    cn, placeholder = open_db(dsn)
    run_sql_file(cn, placeholder, catalog)
    cn.commit()
    return cn, placeholder


def query(cn, sql: str, params=()) -> list:
    """Chạy một câu SELECT, trả về toàn bộ kết quả.

    psycopg2 cho `execute()` trả về None, nên `cur.execute(...).fetchall()` hay
    `for r in cur.execute(...)` đều ném AttributeError. Hàm này bịt hẳn lối viết
    tiện tay đó lại.

    (Trước 24/08/2026 ghi chú ở đây nói đó là "bẫy khi đổi hệ": SQLite cho
    execute() trả về chính cursor nên hai lối viết trên chạy được, và chỉ vỡ khi
    sang Postgres. SQLite đã bị gỡ, nhưng cái bẫy vẫn còn - chỉ là nay nó vỡ
    ngay lần chạy đầu thay vì vỡ muộn.)
    """
    cur = cn.cursor()
    # KHÔNG truyền tuple rỗng xuống. psycopg2 chỉ diễn giải '%' khi đối số tham
    # số KHÁC None - đưa () xuống thì câu `LIKE '%token_count'` bị hiểu là dấu
    # định dạng và ném IndexError.
    #
    # BẪY NÀY VẪN CÒN SỐNG, và nó vừa cắn lần nữa ngày 24/08: migration 001 gọi
    # `exec_driver_sql(sql, ())` và 11 dấu '%' trong ghi chú tiếng Việt của
    # baseline vỡ hết. Xem db/migrations/versions/001_baseline_baseline.py.
    if params:
        cur.execute(sql, params)
    else:
        cur.execute(sql)
    return cur.fetchall()


def query_one(cn, sql: str, params=()):
    """Như query() nhưng trả về dòng đầu tiên, hoặc None."""
    rows = query(cn, sql, params)
    return rows[0] if rows else None


def insert_many(cn, placeholder: str, table: str, columns: list[str], rows: list,
                on_conflict: str = "") -> int:
    """Chèn nhiều dòng, ưu tiên đường nhanh của psycopg2.

    executemany của psycopg2 gửi MỘT vòng mạng cho MỖI dòng. Với 562.307 dòng
    của fact_monitoring thì đó là hàng chục phút - và nó không hỏng, chỉ chậm,
    nên rất dễ tưởng là bình thường. execute_values gom nhiều dòng vào một câu
    INSERT, nhanh hơn vài chục lần.

    Nhánh `executemany` cuối hàm KHÔNG phải nhánh cho hệ quản trị khác - nó là
    đường lui khi `psycopg2.extras.execute_values` không import được.

    `on_conflict` nối nguyên văn vào cuối câu, ví dụ "ON CONFLICT DO NOTHING".
    Mặc định rỗng nên 15 chỗ gọi sẵn có KHÔNG đổi hành vi. Thêm vào đây thay vì
    viết INSERT riêng trong load_gateway.py để đường chèn theo lô vẫn chỉ có MỘT
    chỗ - execute_values gộp lô, executemany thì một vòng mạng mỗi dòng.

    CẢNH BÁO: `len(rows)` là số dòng ĐÃ GỬI, không phải số dòng đã chèn. Với
    ON CONFLICT DO NOTHING hai con số đó khác nhau - bên gọi phải tự đếm bằng
    cách so số dòng của bảng trước và sau nếu cần con số thật.
    """
    if not rows:
        return 0
    cur = cn.cursor()
    col_list = ",".join(columns)
    tail = f" {on_conflict}" if on_conflict else ""
    if placeholder == "%s":
        try:
            from psycopg2.extras import execute_values
        except ImportError:
            execute_values = None
        if execute_values is not None:
            execute_values(cur, f"INSERT INTO {table} ({col_list}) VALUES %s{tail}",
                           rows, page_size=1000)
            return len(rows)
    cur.executemany(
        f"INSERT INTO {table} ({col_list})"
        f" VALUES ({','.join([placeholder] * len(columns))}){tail}", rows)
    return len(rows)


def count_rows(cn, table: str) -> int:
    cur = cn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0]


def model_lookup(cn) -> dict[tuple[str, str], int]:
    """(source, raw_name) -> model_id, đọc từ dim_model_alias."""
    cur = cn.cursor()
    cur.execute("SELECT source, raw_name, model_id FROM dim_model_alias")
    return {(s, r): m for s, r, m in cur.fetchall()}


def agent_lookup(cn) -> dict[str, int]:
    """gcp_project_id -> agent_id.

    Trước đây mọi truy vấn trên fact_billing_daily/fact_monitoring phải tự viết
    `JOIN dim_agent ON gcp_project_id = project`. Quên một chỗ là mất dòng,
    không lỗi nào báo. Nay agent_id là cột thật trong hai bảng đó, và hàm này là
    chỗ duy nhất làm phép tra cứu - lúc nạp.
    """
    cur = cn.cursor()
    cur.execute("SELECT gcp_project_id, agent_id FROM dim_agent"
                " WHERE gcp_project_id IS NOT NULL")
    return {p: a for p, a in cur.fetchall()}


def agent_code_lookup(cn) -> dict[str, int]:
    """code -> agent_id.

    KHÁC agent_lookup(): nguồn Gateway không mang `gcp_project_id`. Thứ nó mang
    là tag của virtual key, và tag đó được đặt TRÙNG với `dim_agent.code`
    (`dms-feedback`). Đây là chỗ duy nhất làm phép tra cứu đó.

    Dùng để lọc tag định danh khỏi tag rác: LiteLLM tự chèn thêm
    `"User-Agent: python-httpx"` vào cùng mảng `request_tags`, nên tag nào KHÔNG
    khớp một dòng của bảng này thì không phải tag agent. Lọc bằng cách bỏ tiền tố
    `User-Agent:` là vá triệu chứng - sẽ hỏng khi LiteLLM thêm loại tag khác.
    """
    cur = cn.cursor()
    cur.execute("SELECT code, agent_id FROM dim_agent")
    return {c: a for c, a in cur.fetchall()}


def account_lookup(cn) -> dict[str, int]:
    """username -> account_id.

    Nguồn Gateway gửi định danh người dùng qua header `X-User`, và LiteLLM ghi
    nguyên nó vào cột `end_user`. Quy ước A3 (20/08) đặt tài khoản dịch vụ theo
    dạng `svc.<code>`, nên `svc.dms-feedback` của Gateway khớp THẲNG một dòng
    `account` - không phải suy đoán, đã đo: account_id 949, kind
    `service_account`, unit_agent_id 6.

    `username` duy nhất trên toàn bảng (đo 31/08: 0 trùng lặp), nên dùng làm khoá
    tra cứu được.

    Trả về `username -> (account_id, unit_agent_id)`. Cần CẢ HAI: bên gọi phải
    kiểm định danh có thuộc đúng agent gửi request không, chứ không chỉ có tồn
    tại hay không. Xem load_gateway.build_rows().

    Dòng nào không tra được thì bên gọi phải rơi về tài khoản kỹ thuật mức agent
    - KHÔNG để NULL, vì `account_id` nằm trong khoá chính của fact_usage_daily.
    """
    cur = cn.cursor()
    cur.execute("SELECT username, account_id, unit_agent_id FROM account")
    return {u: (a, g) for u, a, g in cur.fetchall()}


def anchor_account_lookup(cn) -> dict[int, int]:
    """agent_id -> account_id kỹ thuật mức agent, thay cho NULL ở khoá.

    TRA BẰNG (kind, unit_agent_id), KHÔNG BẰNG TÊN ĐĂNG NHẬP. Đây là cùng một
    phép tra mà `build_usage_daily.anchor_accounts()` đang làm, và docstring ở đó
    ghi lại một sự cố có thật: trước 21/08/2026 nó tra theo một chuỗi tên do khâu
    nạp khác đặt ra, rồi quy ước A3 đổi tài khoản dịch vụ sang `svc.<code>` và
    đúng chỗ đó gãy.

    Không phải agent nào cũng có `service_account`: hai agent mang
    `kind = 'whole_agent'`, tên của chúng KHÔNG có dạng `svc.<code>`. Đoán tên
    là lặp lại đúng sự cố cũ.
    """
    cur = cn.cursor()
    cur.execute("SELECT unit_agent_id, account_id FROM account"
                " WHERE kind IN ('service_account', 'whole_agent')")
    return {int(a): int(acc) for a, acc in cur.fetchall()}


def metric_lookup(cn) -> dict[tuple[str, str], tuple]:
    """(source, raw_name) -> (measures, kind), đọc từ dim_metric_alias.

    Thay cho việc đoán tên: regex trên sku_name, và LIKE '%token_count'.
    """
    cur = cn.cursor()
    cur.execute("SELECT source, raw_name, measures, kind FROM dim_metric_alias")
    return {(s, r): (m, k) for s, r, m, k in cur.fetchall()}
