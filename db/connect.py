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
# chua ban chup bo so bat bien cua tools/diagnostics/baseline_db.py.

# Tên biến VÀ giá trị mặc định KHỚP docker-compose.yml, nên `docker compose up -d`
# rồi chạy script là nối được ngay, không phải đặt gì. Đặt tên khác sẽ thành hai
# bộ cấu hình phải giữ khớp bằng tay - đúng loại lỗi im lặng mà file này đang dọn.
PG_HOST = os.environ.get("PGHOST", "127.0.0.1")
PG_PORT = os.environ.get("PGPORT", "5432")
PG_USER = os.environ.get("PGUSER", "token")
PG_PASSWORD = os.environ.get("PGPASSWORD", "token_local")
# Runtime ledger: token_ledger_v2. Giữ nguyên tên `_v2`, không rename (quyết định
# 27/08/2026).
#
# v2 là bản dựng HOÀN TOÀN từ chuỗi migration rồi nạp lại từ data/, và lúc chuyển
# đã khớp 23/23 khoá với bản cũ (867.657.110 token · $291,985601 · audit 36/31/5/0 ·
# check_api 19/19).
#
# `token_ledger` cũ ĐÃ BỊ XOÁ ngày 14/09/2026, sau khi so mọi bảng với v2: 0 khoá mất,
# và v2 không nhỏ hơn bản cũ ở khoá nào. Chỗ khác còn lại là danh bạ cũ (unit_id,
# role của 3 người), mà trạng thái cũ vẫn nằm trong data/raw_web/ralli/2026-08-13 và
# 2026-08-17. KHÔNG còn database nào để quay lui bằng cách đổi PGDATABASE: quay lui
# nghĩa là dựng lại từ data/ bằng scripts/rebuild_db.py.
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
# không cho JOIN xuyên database, nên db/load_gateway.py mở HAI kết nối và ánh xạ
# ở tầng Python.
#
# `postgres_fdw` và `dblink` CHƯA CÀI - nhưng CÓ SẴN trong ảnh postgres, đo
# 09/09/2026 (fdw 1.1, dblink 1.2; `pg_cron` thì không có). Câu cũ ở đây chỉ ghi
# "chưa cài", dễ đọc thành "không có".
#
# Đường fdw đã được ĐO LÀ CHẠY ĐƯỢC rồi VẪN LOẠI - đọc xuyên database qua vai
# `gateway_readonly` được, vai đó chặn ghi thật, và fdw còn đẩy điều kiện lọc
# xuống nguồn. Lý lẽ loại nằm ở
# openspec/changes/let-the-gateway-ledger-arrive-by-itself/design.md; tóm lại:
# nó buộc viết lại bằng SQL toàn bộ tri thức đang nằm trong load_gateway.py, bảng
# ngoại lệch schema thì `count(*)` VẪN chạy sạch nên phép kiểm dễ báo xanh sai, và
# nó không giải được vấn đề thật (là "không ai chạy", chứ không phải "chép chậm").
# Đừng đề xuất lại từ đầu - bắt đầu từ số đo trong design.md ấy.
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
            f"The DSN points at an SQLite file: {dsn}\n"
            "SQLite was removed from the project on 24/08/2026 - see the note at the top of this file.\n"
            "Use a PostgreSQL connection string, for example:\n"
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
                "psycopg2 is needed to reach PostgreSQL:  pip install psycopg2-binary\n"
                "  or:  pip install -r backend/requirements.txt\n"
                "PostgreSQL is the ONLY database engine since 24/08/2026, so this\n"
                "package is required - there is no SQLite fallback any more."
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


# Bảng mà `rebuild()` KHÔNG xoá dòng. Dòng của chúng do MIGRATION ghi, không do data/
# hay 02_catalog.sql. Một database đã có sẵn không bao giờ chạy lại migration, nên xoá
# những dòng này là mất vĩnh viễn.
#   alembic_version  sổ migration. Xoá thì lần upgrade kế tiếp chạy lại 001 lên bảng đang có.
#   ref_source       4 nguồn, gieo ở db/migrations/sql/001_baseline.sql. Đo 14/09/2026 trên
#                    database diễn tập: xoá nó thì load_ralli chết với fact_call_source_fkey.
# Không bảng nào ở đây có khoá ngoại trỏ sang bảng khác, nên TRUNCATE ... CASCADE các bảng
# còn lại không lan tới chúng. tests/test_connect_migrations.py quét mọi migration và ĐỎ nếu
# có migration ghi dòng vào một bảng chưa có tên ở đây.
KEEP_ON_REBUILD = ("alembic_version", "ref_source")


def rebuild(dsn: str):
    """Dựng lại toàn bộ từ data/: migration tại chỗ, xoá dòng, nạp 02_catalog.sql.

    CHỈ dùng khi sắp nạp lại mọi thứ từ data/ (scripts/rebuild_db.py). Mọi dòng
    của mọi bảng dữ liệu sẽ bị xoá.

    KHÔNG CÒN DROP SCHEMA (đổi 14/09/2026)
    ---------------------------------------
    Bản trước bắt đầu bằng `DROP SCHEMA public CASCADE`. Lệnh đó xoá luôn mọi
    GRANT: trên schema, trên từng bảng, và cả `ALTER DEFAULT PRIVILEGES ... IN
    SCHEMA public` của docker/read-only-api.sql. Ngày 02/09/2026, `api_readonly`
    đọc được 0/20 bảng suốt 38 phút sau một lần dựng lại.

    Hàm này cần bảng danh mục TRỐNG, vì nạp 02_catalog.sql vào bảng đã có dòng là
    đụng khoá chính. TRUNCATE cho bảng trống mà vẫn giữ nguyên bảng, view, schema
    và quyền. Xem change `stop-a-later-pull-from-shrinking-an-earlier-one`, D5.

    MỘT GIAO DỊCH: TRUNCATE và nạp danh mục được commit cùng lúc, nên không có
    lúc nào danh mục trống một nửa mà vẫn nhìn thấy được từ ngoài.

    Danh sách bảng đọc từ pg_tables, không ghi cứng: migration 008, 011, 012 đều
    thêm bảng, và một danh sách ghi cứng sẽ bỏ sót bảng mới mà không báo gì.
    Chỉ giữ lại các bảng trong `KEEP_ON_REBUILD`: dòng của chúng do chính migration
    ghi, và database đã có sẵn thì không chạy lại migration.

    Hai đường dùng chung một chuỗi migration:
        rebuild()              migration  ->  xoá dòng  ->  danh mục
        alembic upgrade head   (không xoá gì, database giữ nguyên dữ liệu)
    """
    catalog = DB_DIR / "02_catalog.sql"
    if not catalog.exists():
        raise SystemExit("db/02_catalog.sql does not exist yet. Run: python db/gen_catalog.py")

    # Migration CHẠY TRƯỚC khi mở kết nối của hàm này: Alembic mở kết nối riêng,
    # và bảng nó vừa tạo phải nhìn thấy được khi đọc pg_tables ngay dưới đây.
    apply_migrations(dsn)

    cn, placeholder = open_db(dsn)
    with cn.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
        tables = [name for (name,) in cur.fetchall() if name not in KEEP_ON_REBUILD]
        # TRUNCATE với danh sách rỗng là lỗi cú pháp của PostgreSQL.
        if tables:
            quoted = ", ".join('"' + name.replace('"', '""') + '"' for name in tables)
            cur.execute(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE")
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


def directory_account_lookup(cn) -> dict[tuple[int, str], int]:
    """(agent_id, username) -> account_id. Khoá ĐÔI, không phải khoá đơn.

    VÌ SAO KHÔNG DÙNG `account_lookup()` Ở TRÊN
    --------------------------------------------
    Hàm kia khoá bằng `username` một mình, nên nó chỉ trả về được MỘT agent cho
    mỗi người - `account.unit_agent_id`, tức agent thắng phép chọn ở
    `load_org.py:492`. Bên gọi vì thế phải đem cột đó đi SO SÁNH với agent gửi
    request, và phép so ấy trượt với người dùng nhiều agent.

    Đo 21/09/2026 trên đợt kéo 20/09: 5 người có mặt trong danh bạ của CẢ Ralli
    (892 tên) lẫn TLA Hợp Đồng (44 tên) - `longnt`, `pbh3_tthien`,
    `quy.tv@rangdong.com.vn`, `tg.namnh`, `tt3.binhtv`. Con số 5 khớp chú thích
    đã có ở `db/migrations/sql/001_baseline.sql:239`.

    Hỏng kiểu gì: token đủ, tiền đủ, HTTP 200, dòng vẫn vào sổ - chỉ chiều người
    dùng là mất. Mọi phép nghiệm thu bằng TỔNG đều ĐẠT.

    HAI SỔ ĐĂNG KÝ, KHÔNG PHẢI MỘT
    -------------------------------
    Hai bảng đặt hai cái tên khác nhau cho cùng một tài khoản dịch vụ:

        load_org.py:405   dim_user:  (agent 6, "__technical_6__") -> account 949
        load_org.py:609   account:   949, "svc.dms-feedback"

    Gateway gửi `X-User: svc.dms-feedback`. Tra riêng `dim_user` thì ra RỖNG, và
    cả 6 agent một-người-dùng rơi khỏi chiều người dùng. Nên phải hợp hai nguồn:

        dim_user  NOT is_technical              khoá (agent_id, username)
        account   kind = 'service_account'      khoá (unit_agent_id, username)

    `whole_agent` và `unattributed` CỐ Ý không lấy: chúng là đích RƠI VỀ khi tra
    không ra (xem `anchor_account_lookup`). Gộp chúng vào là biến đường rơi thành
    đường nhận, và bộ đếm `identity_unresolvable` sẽ im lặng về 0 vì không còn gì
    trượt được nữa.

    DỪNG KHI DỮ LIỆU HỎNG, KHÔNG IM LẶNG CHỌN MỘT
    ----------------------------------------------
    `dim_user` khoá chính là `(agent_id, user_id)`, KHÔNG phải `(agent_id,
    username)` - nên một `username` có thể ra nhiều dòng trong cùng một agent.
    Có thật: `001_baseline.sql:239` ghi "13 dòng do Ralli ghi hai dạng khoá".

    Cả 13 dòng đó trỏ về cùng một `account_id`, nên gộp trùng là đúng. Nhưng đó
    là một tính chất KHÔNG ai cưỡng chế bằng ràng buộc, nên không được dựa vào nó
    trong im lặng: nếu một khoá cho ra hai `account_id` khác nhau thì dữ liệu đã
    hỏng, và hàm này dừng hẳn thay vì chọn bừa một cái.

    `username` chuẩn hoá bằng LOWER(TRIM()) ở cả hai nguồn, khớp `load_org.norm()`.
    """
    seen: dict[tuple[int, str], int] = {}
    conflicts: list[str] = []

    def add(agent_id, username, account_id, source: str) -> None:
        if account_id is None:
            return
        key = (int(agent_id), username)
        cu = seen.get(key)
        if cu is not None and cu != int(account_id):
            conflicts.append(f"  {key} -> account {cu} và {account_id} ({source})")
        else:
            seen[key] = int(account_id)

    cur = cn.cursor()
    # Nguồn 1: danh bạ người thật, đã tách sẵn theo agent.
    cur.execute("SELECT agent_id, LOWER(TRIM(username)), account_id"
                " FROM dim_user WHERE NOT is_technical")
    for a, u, acc in cur.fetchall():
        add(a, u, acc, "dim_user")

    # Nguồn 2: tài khoản dịch vụ - tên `svc.<code>` CHỈ tồn tại ở bảng này.
    cur.execute("SELECT unit_agent_id, LOWER(TRIM(username)), account_id"
                " FROM account WHERE kind = 'service_account'")
    for a, u, acc in cur.fetchall():
        add(a, u, acc, "account/service")

    if conflicts:
        raise SystemExit(
            "directory_account_lookup: một cặp (agent, tên đăng nhập) trỏ về hai"
            " tài khoản khác nhau. Dữ liệu danh bạ hỏng, không đoán bừa:\n"
            + "\n".join(sorted(conflicts)))
    return seen


def account_unit_lookup(cn) -> dict[int, str]:
    """account_id -> unit_id.

    Truong "phong ban" cua ban ghi luot goi. Master Plan STT 4 muc tieu 1 doi no,
    va do 02/09/2026 thi cot `fact_call.unit_id` RONG tren ca 41 dong gateway:
    `load_ralli.py` co ghi cot nay, `load_gateway.py` khong khai no trong COLUMNS.

    TRA TU TAI KHOAN, KHONG TU TAG. Tag cua request noi AGENT nao gui, khong noi
    NGUOI GUI thuoc phong ban nao. Voi agent mot-nguoi-dung thi hai thu trung nhau
    HOM NAY - va dung vi the ma loi se im lang khi mot agent nhieu nguoi dung di
    qua Gateway.

    Gia tri co the la don vi KY THUAT (`__technical_6__` cho tai khoan dich vu).
    Do la cau tra loi trung thuc: tai khoan dich vu khong thuoc phong ban that nao.
    De NULL thi mat thong tin - khong phan biet duoc "chua nap" voi "khong co
    phong ban".
    """
    cur = cn.cursor()
    cur.execute("SELECT account_id, unit_id FROM account WHERE unit_id IS NOT NULL")
    return {int(a): u for a, u in cur.fetchall()}


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
