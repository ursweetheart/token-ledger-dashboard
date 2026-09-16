"""Sinh db/02_catalog.sql từ dữ liệu thật - chỉ đọc file, không gọi mạng.

VÌ SAO SINH BẰNG MÁY
--------------------
File danh mục có hơn 40 dòng ánh xạ tên model. Gõ tay thì sai một dòng cũng
không ai phát hiện: tổng tiền vẫn đúng, chỉ tỷ lệ giữa các model là sai. Sinh
bằng máy thì quy tắc nằm trong db/rules.py, đọc lại và kiểm lại được.

Ngày bắt đầu / kết thúc có dữ liệu cũng TÍNH TỪ FILE thay vì gõ tay.

Nhưng `is_running` thì GÕ TAY có chủ đích. Đó là kết luận nghiệp vụ (mục C3:
tools-quizz ngừng từ 30/06, Multi modal AI Invoice từ 25/07), không phải thứ suy
ra được bằng ngưỡng "bao nhiêu ngày không có dữ liệu thì coi là ngừng". Một
ngưỡng như vậy sẽ âm thầm phân loại sai mỗi khi một agent nghỉ lễ dài.

Chạy: python db/gen_catalog.py
"""

from __future__ import annotations

import collections
import csv
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rules import GATEWAY_MODELS, MODEL_ID, MODELS, guess_kind, guess_model  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _latest_dir(parent: Path, prefer_suffix: str = "") -> Path:
    children = sorted(p for p in parent.glob("*") if p.is_dir())
    if not children:
        raise SystemExit(f"no collection folder in {parent}")
    if prefer_suffix:
        match = [p for p in children if p.name.endswith(prefer_suffix)]
        if match:
            return match[-1]
    return children[-1]


def _latest_file(parent: Path, pattern: str) -> Path:
    candidates = sorted(parent.glob(pattern))
    if not candidates:
        raise SystemExit(f"no file matches {parent / pattern}")
    return candidates[-1]


# Ba nguồn cũ đều đã lạc hậu: bản gộp tay bị xoá, đợt kéo Monitoring 06/08 không
# còn phủ hết dải ngày, và data/ctda là bản cào tay 05/08. Nay lấy bản mới nhất.
BILLING = _latest_file(ROOT / "data" / "da_xu_ly" / "billing", "billing_*.csv")
MONITORING = _latest_dir(ROOT / "data" / "da_xu_ly" / "du_lieu_giam_sat", "-gop")
RALLI_DIR = _latest_dir(ROOT / "data" / "raw_web" / "ralli")
TLA_DIR = _latest_dir(ROOT / "data" / "raw_web" / "tla-hd")
RALLI_RAW = RALLI_DIR / "db-token_usage-raw.json"
OUT = ROOT / "db" / "02_catalog.sql"

# id, code, name, project, has_org_tree, project_created_at, is_running,
# has_google_source
# project_created_at lấy từ `gcloud projects list`, ghi trong kế hoạch mục 0.
#
# RALLI CÓ PROJECT NHƯNG KHÔNG CÓ NGUỒN ĐỐI CHỨNG
# -----------------------------------------------
# Trước đây gcp_project_id của Ralli để NULL, và has_google_source được SUY ra
# bằng `project is not None`. Ảnh chụp console 14/08 cho thấy project có thật:
# `tla-ralli`. Nhưng nó CHƯA nối Google Billing, nên vẫn không có dòng hoá đơn
# hay monitoring nào.
#
# Hai chuyện đó giờ tách rời nhau, mỗi cái một cột:
#     gcp_project_id     project tồn tại trên GCP hay không
#     has_google_source  có số liệu của Google để đối chiếu hay không
# Gộp hai chuyện vào một phép suy là lý do cột này từng sai. Ralli lấy số từ dữ
# liệu cào về từ chính app (fact_call).
#
# AGENT 7 (crm-feedback): `crm-500509` LÀ PROJECT CỦA THỜI TRƯỚC GATEWAY
# ----------------------------------------------------------------------
# Quyết định ngày 10/09/2026 (anh Tuấn chọn): GIỮ `crm-500509`, kèm ghi chú này.
#
# Từ khi agent 7 đi qua Gateway, tiền của nó KHÔNG còn rời khỏi `crm-500509`
# nữa — nó rời khỏi project riêng của CRM (project number `60854134008`, id
# dạng chuỗi thì CHƯA BIẾT, xem task 1.1 của change
# `route-the-crm-agent-through-the-gateway`). Nên với dữ liệu SAU ngày chuyển,
# giá trị ở đây không còn trỏ tới nơi phát sinh chi phí.
#
# Vì sao vẫn giữ, chứ không để NULL hay điền project mới:
#   - cột này là khoá JOIN của đường nạp monitoring và hoá đơn Google
#     (`db/connect.py:375` → `agent_lookup`, và `db/load_monitoring.py:118`).
#     Đổi giá trị thì MỌI dòng monitoring/hoá đơn CŨ của agent 7 mất đường quy
#     về agent — mất dữ liệu lịch sử, mà lịch sử ấy có thật.
#   - để NULL thì `agent_lookup` bỏ hẳn agent 7 (`WHERE gcp_project_id IS NOT
#     NULL`), hỏng y như trên.
#   - điền project mới bằng một chuỗi ĐOÁN thì tệ hơn cả hai: nó trông đúng.
#
# Cách đọc cho người sau: cột này trả lời "hoá đơn Google CŨ của agent này nằm
# ở project nào", KHÔNG trả lời "hôm nay tiền của nó ra từ đâu". Với đường
# Gateway, câu sau được trả lời bởi sổ Gateway (`fact_call` → `virtual_key_id`
# / tag `crm-feedback`), không phải bởi cột này. Số cũ và số mới KHÔNG nối
# liền — đã ghi ở `docs/archive/gateway/dua-crm-qua-gateway-10-09.md` mục 9.
AGENTS = [
    (1, "contact-center", "Chatbot Contact Center", "pro-tuner-454203-v3", False, "2025-03-19", True, True),
    (2, "sale-agent", "Sale Agent", "tranquil-post-471401-c1", False, "2025-09-07", True, True),
    (3, "invoice", "Multi modal AI Invoice", "multimodal-invoice", False, "2025-09-15", False, True),
    (4, "tools-quizzer", "Tools Quizzer", "tools-quizz", False, "2026-04-10", False, True),
    (5, "tla-hd", "Trợ Lý Ảo Hợp Đồng", "ai-chatbot-contract", True, "2026-06-20", True, True),
    (6, "dms-feedback", "Phân Loại Phản Hồi Tiếp Thị", "feedback-dms-tiep-thi", False, "2026-06-25", True, True),
    (7, "crm-feedback", "Phân Loại Dữ Liệu CRM", "crm-500509", False, "2026-06-25", True, True),
    (8, "ralli", "Trợ lý ảo Ralli", "tla-ralli", True, None, True, False),
]

# Catalog SKU chính chủ, do scripts/pull_sku_catalog.py kéo về.
SKU_CATALOG = ROOT / "data" / "raw_google_console" / "danh_muc" / "sku-gemini-api.json"
# Thư mục kéo monitoring THÔ - nơi chứa {project}.descriptors.json.
MONITORING_RAW = ROOT / "data" / "raw_google_console" / "du_lieu_giam_sat"

# Hạn mức USD theo cấu hình Google Cloud. ĐÂY là nguồn sự thật: nó vào
# 02_catalog.sql -> ref_budget -> /api/catalog -> dashboard.
#
# Trước 17/08/2026 chú thích ở đây trỏ vào "app.js dòng 15-22", vì lúc đó app.js
# cũng giữ một bản gõ tay. Bản đó đã bỏ - hai nguồn cho một con số thì sớm muộn
# lệch nhau mà không gì báo.
#
# Tools Quizzer không có hạn mức, Ralli đặt theo TOKEN (xem RALLI_BUDGET_TOKENS
# dưới). Cả hai vẫn XUẤT HIỆN đầy đủ trong báo cáo - không có hạn mức USD khác
# với bị loại khỏi báo cáo.
BUDGET_USD = {
    "Trợ Lý Ảo Hợp Đồng": 20, "Chatbot Contact Center": 30, "Phân Loại Dữ Liệu CRM": 20,
    "Phân Loại Phản Hồi Tiếp Thị": 20, "Multi modal AI Invoice": 20, "Sale Agent": 50,
}
VND_RATE = 25200                    # quyet dinh M-F, khong keo tu API
RALLI_BUDGET_TOKENS = 50_000_000    # data/ctda/token-usage-budget.json
BUDGET_MONTH = "2026-08-01"
FX_DAY = "2026-08-08"


def q(s) -> str:
    """Bọc nháy đơn cho SQL. None -> NULL."""
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"


def data_range() -> dict[str, tuple[str, str]]:
    days: dict[str, list[str]] = collections.defaultdict(list)
    with open(BILLING, encoding="utf-8-sig") as h:
        for r in csv.DictReader(h):
            days[r["project"]].append(r["day"])
    for f in sorted(glob.glob(str(MONITORING / "*.csv"))):
        with open(f, encoding="utf-8-sig") as h:
            for r in csv.DictReader(h):
                svc = r["res_service"] or r["metric_type"].split("/")[0]
                if svc.startswith("generativelanguage"):
                    days[r["gcp_project_id"]].append(r["ts_ict"][:10])
    with open(RALLI_RAW, encoding="utf-8-sig") as h:
        root = json.load(h)
    raw = root if isinstance(root, list) else list(root.values())[0]
    days["__ralli__"] = [str(r["timestamp"])[:10] for r in raw]
    return {p: (min(v), max(v)) for p, v in days.items()}


def model_aliases() -> list[tuple[str, str, int]]:
    """(source, raw_name, model_id). Dừng hẳn nếu gặp tên không suy được."""
    aliases: list[tuple[str, str, int]] = []
    failed: list[str] = []

    sku: dict[str, str] = {}
    with open(BILLING, encoding="utf-8-sig") as h:
        for r in csv.DictReader(h):
            sku[r["sku_id"]] = r["sku_name"]
    for sid, name in sorted(sku.items()):
        m, k = guess_model(name), guess_kind(name)
        if not m or not k:
            failed.append(f"SKU {sid} '{name}' -> model={m} kind={k}")
        else:
            aliases.append(("billing_sku", sid, MODEL_ID[m]))

    labels: set[tuple[str, str]] = set()
    for f in sorted(glob.glob(str(MONITORING / "*.csv"))):
        with open(f, encoding="utf-8-sig") as h:
            for r in csv.DictReader(h):
                if r["model"]:
                    labels.add(("monitoring", r["model"]))
    # Nguồn cũ là by-model-2026.csv của hai app - file PHÁI SINH, đợt kéo mới
    # không có. `costs.by_model` trong stats cả năm là thứ API trả về trực tiếp
    # và có đúng bộ trường đó.
    for f in (RALLI_DIR / "token-usage-year.json", TLA_DIR / "token-usage-year.json"):
        for r in json.loads(f.read_text(encoding="utf-8-sig"))["costs"].get("by_model") or []:
            # 'none' của TLA HĐ là 2 lượt gọi 0 token, KHÔNG phải một model.
            if r.get("model") and r["model"] != "none":
                labels.add(("app", r["model"]))
    for source, name in sorted(labels):
        if name not in MODEL_ID:
            failed.append(f"label {source} '{name}' is not in the canonical model list")
        else:
            aliases.append((source, name, MODEL_ID[name]))

    # Nguon 'gateway'. KHAC ba nguon tren: ten khong doc tu file du lieu ma khai
    # trong rules.GATEWAY_MODELS, vi Gateway ghi ten upstream cua nha cung cap
    # chu khong ghi bi danh. Tuyen nao chua khai thi luu luong cua no roi vao
    # muc "khong noi duoc model" cua db/load_gateway.py -- duoc dem va in ra,
    # khong bien mat im lang.
    for raw in GATEWAY_MODELS:
        canonical = guess_model(raw)
        if not canonical or canonical not in MODEL_ID:
            failed.append(f"tuyen gateway '{raw}' -> model={canonical}")
        else:
            aliases.append(("gateway", raw, MODEL_ID[canonical]))

    if failed:
        raise SystemExit("CANNOT BE MAPPED - add it to db/rules.py and run again:\n  "
                         + "\n  ".join(failed))
    return aliases


def _classify_metric(metric_type: str) -> tuple[str, str | None]:
    """(measures, kind) suy từ METRIC_TYPE - mã API chính thức của Google.

    Đọc từ metric_type chứ KHÔNG từ biệt danh `metric_alias`: biệt danh do
    pull_monitoring.py tự chế (nó còn tự thêm hậu tố _p95/_p99), còn metric_type
    là bề mặt API có cam kết ổn định của Google.

    Hai nhánh đầu được metadata xác nhận độc lập (metricKind/valueType) - xem
    kiểm tra trong metric_aliases(). Nhánh token/calls thì metadata KHÔNG phân
    biệt được: cả hai đều DELTA/INT64/unit='1'.
    """
    tail = metric_type.split("/", 1)[1] if "/" in metric_type else metric_type
    if tail.startswith("quota/"):
        quota_tail = tail[len("quota/"):]
        if quota_tail.endswith("/limit"):
            return "quota_limit", None
        tail = quota_tail[: -len("/usage")] if quota_tail.endswith("/usage") else quota_tail
    if tail.endswith("request_latencies"):
        return "latency", None
    if tail.endswith("token_count"):
        return "token", ("output" if "output_token" in tail else
                         "cached" if "cached" in tail else "input")
    if tail.endswith("requests") or tail.endswith("request_count") \
            or tail.endswith("requests_per_model"):
        return "calls", None
    raise SystemExit(f"cannot classify the metric '{metric_type}'.\n"
                     "  Them nhanh moi vao _classify_metric() roi chay lai.")


def _descriptors() -> dict[str, dict]:
    """metric_type -> descriptor, gộp từ MỌI đợt kéo thô.

    Gộp hết các đợt vì cửa sổ lưu giữ của Google trượt: đợt 06/08 còn giữ phép
    đo mà đợt 13/08 không trả về nữa. Bảng biệt danh phải phủ được CẢ dữ liệu cũ
    đang nằm trong database.
    """
    d: dict[str, dict] = {}
    for f in sorted(MONITORING_RAW.glob("*/*.descriptors.json")):
        for x in json.loads(f.read_text(encoding="utf-8")):
            d[x["type"]] = x
    return d


def metric_aliases() -> list[tuple]:
    """dim_metric_alias cho nguồn 'monitoring'.

    Lấy danh sách metric_type từ chính dữ liệu SẼ ĐƯỢC NẠP, không từ descriptor.
    Như vậy mọi dòng fact_monitoring chắc chắn có một dòng biệt danh - nếu lấy
    từ descriptor thì một phép đo cũ (Google đã bỏ khỏi danh sách) sẽ không có
    biệt danh, và khâu nạp sẽ hỏng.
    """
    desc = _descriptors()
    used: set[str] = set()
    for f in sorted(glob.glob(str(MONITORING / "*.csv"))):
        with open(f, encoding="utf-8-sig") as h:
            for r in csv.DictReader(h):
                used.add(r["metric_type"])

    out, mismatch = [], []
    for mt in sorted(used):
        measures, kind = _classify_metric(mt)
        d = desc.get(mt, {})
        metric_kind, value_type = d.get("metricKind"), d.get("valueType")
        # Đối chiếu chéo: metadata phải đồng ý với tên ở hai nhánh nó biết.
        if metric_kind and (metric_kind == "GAUGE") != (measures == "quota_limit"):
            mismatch.append(f"{mt}: ten noi '{measures}' nhung metricKind={metric_kind}")
        if value_type and (value_type == "DISTRIBUTION") != (measures == "latency"):
            mismatch.append(f"{mt}: ten noi '{measures}' nhung valueType={value_type}")
        out.append(("monitoring", mt, (d.get("description") or "").strip() or None,
                    measures, kind, metric_kind, value_type))
    if mismatch:
        raise SystemExit("the metric name and Google's metadata DISAGREE:\n  "
                         + "\n  ".join(mismatch))
    return out


def _catalog() -> dict[str, dict]:
    if not SKU_CATALOG.exists():
        raise SystemExit(f"Chua co {SKU_CATALOG.relative_to(ROOT)}.\n"
                         "  Chay: python scripts/pull_sku_catalog.py")
    return {s["skuId"]: s for s in json.loads(SKU_CATALOG.read_text(encoding="utf-8"))}


def sku_aliases(cat: dict[str, dict]) -> list[tuple]:
    """dim_metric_alias cho nguồn 'billing_sku'.

    Catalog KHÔNG có trường nào nói input/output/cached - cả 597 SKU đều
    resourceGroup='Gemini', usageType='OnDemand'. Nên vẫn phải đọc mô tả, nhưng
    đọc `description` của catalog (Google sở hữu) thay vì `sku_name` trong CSV
    xuất ra.
    """
    sku: dict[str, str] = {}
    with open(BILLING, encoding="utf-8-sig") as h:
        for r in csv.DictReader(h):
            sku[r["sku_id"]] = r["sku_name"]

    out, failed = [], []
    for sid, csv_name in sorted(sku.items()):
        s = cat.get(sid)
        if not s:
            failed.append(f"SKU {sid} '{csv_name[:60]}' is not in the catalog")
            continue
        description = s.get("description", "")
        kind = guess_kind(description)
        if not kind:
            failed.append(f"SKU {sid} '{description[:60]}' -> cannot infer a kind")
            continue
        out.append(("billing_sku", sid, description, "token", kind, None, None))
    if failed:
        raise SystemExit("SKUs that cannot be looked up:\n  " + "\n  ".join(failed))
    return out


def price_table(cat: dict[str, dict]) -> list[tuple]:
    """ref_price từ giá CHÍNH CHỦ của catalog - bảng này trước đây 0 dòng.

    Một model có nhiều SKU cùng loại (ngữ cảnh ngắn/dài, text/ảnh/âm thanh) với
    giá khác nhau. Chọn SKU CÓ KHỐI LƯỢNG LỚN NHẤT trong hoá đơn của ta: đó là
    giá thực sự chi phối tiền, và là giá hợp lý nhất để ước tính cho Ralli - nơi
    không có hoá đơn.

    `effective_from` lấy từ effectiveTime của Google. Lưu ý catalog chỉ trả về
    giá HIỆN HÀNH, không có lịch sử, nên bảng này nói 'giá từ ngày X' chứ không
    nói được giá hồi tháng 1. Đối chiếu 14/08: 29/31 SKU có giá catalog trùng
    khớp giá suy ngược từ hoá đơn trong vòng 1% (hai cái lệch đều là SKU $0,00).
    """
    volume: dict[str, int] = collections.defaultdict(int)
    with open(BILLING, encoding="utf-8-sig") as h:
        for r in csv.DictReader(h):
            volume[r["sku_id"]] += int(float(r["quantity"] or 0))

    # (model_id, kind) -> (khối lượng, giá, ngày hiệu lực, sku)
    best: dict[tuple[int, str], tuple] = {}
    for sid, vol in volume.items():
        s = cat.get(sid)
        if not s:
            continue
        description = s.get("description", "")
        model, kind = guess_model(description), guess_kind(description)
        if not model or not kind:
            continue
        pi = (s.get("pricingInfo") or [{}])[0]
        tiers = pi.get("pricingExpression", {}).get("tieredRates") or []
        if not tiers:
            continue
        u = tiers[-1]["unitPrice"]
        # Giá tính trên MỘT token (usageUnitDescription='count'); đổi ra 1 triệu.
        price = (int(u.get("units", 0)) + u.get("nanos", 0) / 1e9) * 1e6
        day = (pi.get("effectiveTime") or "")[:10] or "1970-01-01"
        k = (MODEL_ID[model], kind)
        if k not in best or vol > best[k][0]:
            best[k] = (vol, price, day, sid)

    # DU PHONG cho model CHUA CO HOA DON.
    #
    # Quy tac "SKU co khoi luong lon nhat" o tren doi ta da tung bi tinh tien cho
    # model do. Model moi bat qua Gateway thi chua - va cho hoa don ve nghia la
    # dashboard hien dau gach ngang thay vi tien, du catalog DA CO gia.
    #
    # Do 31/08/2026: `gemini-3.5-flash-lite` co 24 SKU dau vao trong catalog
    # (text/anh/am thanh/video x thuong/flex/priority/batch/caching). Khong co
    # khoi luong thi khong biet cai nao chi phoi -> chon SKU TEXT TIEU CHUAN,
    # tuc la khong mang bat ky bien the nao. Do la thu mot luot goi API binh
    # thuong dung toi.
    #
    # DA DOI CHIEU DOC LAP: gia catalog cho model do la $0,30 vao / $2,50 ra, va
    # don gia suy nguoc tu 40/40 dong that cua LiteLLM cung ra dung hai so do.
    # Hai nguon khong lien quan gi nhau, khop den tung xu.
    BIEN_THE = ("flex", "priority", "batch", "caching", "storage")
    # CHI ap dung cho model KHONG CO MOT DONG GIA NAO tu hoa don.
    #
    # Ban dau dieu kien la `if k in best` - tuc la vá theo TUNG LOAI gia. Sai:
    # model 1, 7, 8 co hoa don cho input/output nhung khong co khoi luong cho SKU
    # cached, va cach do lang le dien `price_cached` cho ca ba. Chung DA CO hoa
    # don; dien them gia cached la mot quyet dinh khac, phai lam co chu dich chu
    # khong phai roi ra tu day.
    da_co_hoa_don = {mid for (mid, _kind) in best}
    for sid, s_ in cat.items():
        description = s_.get("description", "")
        model, kind = guess_model(description), guess_kind(description)
        if not model or not kind:
            continue
        mid = MODEL_ID[model]
        if mid in da_co_hoa_don:
            continue
        k = (mid, kind)
        if k in best:
            continue
        t = description.lower()
        if " text" not in t or any(v in t for v in BIEN_THE):
            continue
        pi = (s_.get("pricingInfo") or [{}])[0]
        tiers = pi.get("pricingExpression", {}).get("tieredRates") or []
        if not tiers:
            continue
        u = tiers[-1]["unitPrice"]
        best[k] = (0,                        # khoi luong 0 = chon theo du phong
                   (int(u.get("units", 0)) + u.get("nanos", 0) / 1e9) * 1e6,
                   (pi.get("effectiveTime") or "")[:10] or "1970-01-01", sid)

    grouped: dict[tuple[int, str], dict] = collections.defaultdict(dict)
    for (mid, kind), (_, price, day, _sid) in best.items():
        grouped[(mid, day)][kind] = price
    return [(mid, day, g.get("input"), g.get("output"), g.get("cached"))
            for (mid, day), g in sorted(grouped.items())]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ranges = data_range()
    aliases = model_aliases()
    cat = _catalog()
    metrics = metric_aliases()
    skus = sku_aliases(cat)
    prices = price_table(cat)

    out: list[str] = []
    A = out.append
    A("-- ==============================================================")
    A("-- SINH TU DONG boi db/gen_catalog.py - dung sua tay.")
    A("-- Sua quy tac trong db/rules.py hoac trong script do roi chay lai.")
    A("-- ==============================================================")
    A("")
    A("-- 8 agent. Khoang ngay TINH TU DU LIEU; is_running go tay theo muc C3.")
    A("INSERT INTO dim_agent (agent_id, code, name, gcp_project_id, has_org_tree,")
    A("                       project_created_at, data_from, data_to,")
    A("                       is_running, has_google_source) VALUES")
    rows = []
    for aid, code, name, proj, tree, created, running, google in AGENTS:
        # Khoảng ngày lấy theo NƠI CÓ SỐ LIỆU, không theo project: Ralli có
        # project `tla-ralli` nhưng số liệu nằm ở dữ liệu cào từ app.
        first, last = ranges[proj] if google else ranges["__ralli__"]
        rows.append(f"  ({aid}, {q(code)}, {q(name)}, {q(proj)}, {str(tree).upper()}, "
                    f"{q(created)}, {q(first)}, {'NULL' if running else q(last)}, "
                    f"{str(running).upper()}, {str(google).upper()})")
    A(",\n".join(rows) + ";")
    A("")
    A(f"-- {len(MODELS)} model, ten chuan dang gach ngang.")
    A("INSERT INTO dim_model (model_id, name, family, provider) VALUES")
    A(",\n".join(f"  ({i}, {q(t)}, {q(f)}, 'Google')" for i, t, f in MODELS) + ";")
    A("")
    A(f"-- {len(aliases)} anh xa. Ba nguon goi ten model theo ba kieu khac nhau:")
    A("--   billing 'gemini-embedding-001'  <->  monitoring 'gemini-embedding-1.0'")
    A("INSERT INTO dim_model_alias (source, raw_name, model_id) VALUES")
    A(",\n".join(f"  ({q(s)}, {q(t)}, {m})" for s, t, m in aliases) + ";")
    A("")
    A(f"-- {len(metrics) + len(skus)} bi danh do dac: {len(metrics)} phep do")
    A(f"-- monitoring + {len(skus)} SKU hoa don. Thay cho viec doan ten bang")
    A("-- regex va LIKE '%token_count'. Nguon: descriptor + Cloud Billing Catalog.")
    A("INSERT INTO dim_metric_alias (source, raw_name, label, measures, kind,"
      " metric_kind, value_type) VALUES")
    A(",\n".join(f"  ({q(s)}, {q(t)}, {q(lb)}, {q(me)}, {q(k)}, {q(mk)}, {q(vt)})"
                 for s, t, lb, me, k, mk, vt in metrics + skus) + ";")
    A("")
    A(f"-- {len(prices)} bang gia CHINH CHU tu Cloud Billing Catalog (USD / 1 trieu token).")
    A("-- Truoc day bang nay RONG. Moi model lay gia cua SKU co khoi luong lon nhat")
    A("-- trong hoa don. Catalog chi co gia HIEN HANH, khong co lich su.")
    A("-- Model CHUA CO HOA DON thi khong co khoi luong de chon -> lay SKU TEXT")
    A("-- TIEU CHUAN (khong flex/priority/batch/caching). Xem price_table().")
    A("INSERT INTO ref_price (model_id, effective_from, price_input, price_output,"
      " price_cached, source) VALUES")
    A(",\n".join(f"  ({m}, {q(d)}, {'NULL' if i is None else f'{i:.8f}'},"
                 f" {'NULL' if o is None else f'{o:.8f}'},"
                 f" {'NULL' if c is None else f'{c:.8f}'}, 'google')"
                 for m, d, i, o, c in prices) + ";")
    A("")
    A("-- Ty gia go cung (quyet dinh M-F). Keo API sau, cau truc khong phai doi.")
    A(f"INSERT INTO ref_fx (day, vnd_per_usd, source) VALUES "
      f"({q(FX_DAY)}, {VND_RATE}, 'hardcoded (app.js)');")
    A("")
    A("-- Ralli chan theo TOKEN, sau agent kia theo TIEN. Khong quy doi.")
    A("-- Tools Quizzer khong co ngan sach: app.js da loai khoi danh sach.")
    A("INSERT INTO ref_budget (agent_id, month, budget_usd, budget_tokens) VALUES")
    budgets = []
    for aid, code, name, proj, tree, created, running, google in AGENTS:
        if name in BUDGET_USD:
            budgets.append(f"  ({aid}, {q(BUDGET_MONTH)}, {BUDGET_USD[name]}, NULL)")
        elif code == "ralli":
            budgets.append(f"  ({aid}, {q(BUDGET_MONTH)}, NULL, {RALLI_BUDGET_TOKENS})")
    A(",\n".join(budgets) + ";")
    A("")

    OUT.write_text("\n".join(out), encoding="utf-8")
    n = collections.Counter(x[0] for x in aliases)
    print(f"wrote {OUT}")
    print(f"  {len(AGENTS)} agents | {len(MODELS)} models | {len(aliases)} aliases {dict(n)} "
          f"| 1 ty gia | {len(budgets)} ngan sach")
    nm = collections.Counter(x[3] for x in metrics)
    print(f"  {len(metrics)} metric aliases {dict(nm)} | {len(skus)} SKU aliases"
          f" | {len(prices)} dong bang gia")


if __name__ == "__main__":
    main()
