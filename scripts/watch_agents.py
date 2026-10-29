"""Kiểm sức khỏe agent mỗi ngày theo giờ VN đã đặt, và khi có người bấm "Chạy ngay".

    python scripts/watch_agents.py --dry-run        # chỉ GET, in kết quả, không ghi DB
    python scripts/watch_agents.py --once           # chạy ngay một lần, ghi DB, CÓ gọi POST
    python scripts/watch_agents.py                  # vòng lặp của service agent-health-watch

Thiết kế: openspec/changes/add-agent-health-tab/design.md.

PHÉP KIỂM KHAI Ở config/agent-health.yaml, KHÔNG Ở ĐÂY

Code không biết tên agent nào. Thêm agent = thêm một khối YAML rồi khởi động lại service. Mỗi POST
phải có trong `allow_post` của chính agent đó, nếu không file này từ chối khởi động: mỗi POST là
một ngoại lệ của luật chỉ-đọc, phải có người duyệt.

HAI NGUỒN KÍCH HOẠT, MỘT CÁCH CHẠY — design.md D2, D9

Mỗi vòng 5 giây:
  1. có lần "Chạy ngay" đang chờ thì chạy nó. Xét TRƯỚC lịch: xét lịch trước thì INSERT của lịch
     vướng index duy nhất do lần chạy tay đang giữ, vòng nào cũng vậy, và lần chạy tay kẹt mãi.
  2. không thì xét lịch. Giữ chỗ (`last_run_date`) và tạo lần chạy nằm trong MỘT transaction:
     tách ra thì INSERT hỏng sẽ để lại `last_run_date` đã ghi, và lịch hôm đó mất luôn.

Lần chạy tay không đọc, không ghi `last_run_date`. Bấm lúc 07:00 thì 08:00 lịch vẫn chạy.

CHỈ MỘT BẢN CHẠY VÒNG LẶP

Lúc khởi động, vòng lặp chuyển mọi lần chạy `running` sang `interrupted`, để nút "Chạy ngay" không
bị khoá mãi sau một lần container chết. Hai bản cùng chạy thì bản sau ngắt nhầm việc của bản trước.
`container_name` trong compose chặn việc đó. `--once` và `--dry-run` không làm bước dọn này.

KẾT QUẢ: MỘT TÀI LIỆU JSON, HAI NƠI

Cột `agent_health_run.result` (cập nhật sau mỗi phép kiểm, cho thanh tiến độ) và tệp
`var/agent-checks/<run_id>/result.json` (chỉ khi lần chạy xong, cho module chụp màn hình đọc).
Khuôn tài liệu: docs/reference/agent-health-result.md. Đổi khuôn thì tăng `SCHEMA_VERSION`.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from watch_gateway import VN, env  # noqa: E402

LOG = logging.getLogger("agent-health-watch")

CONFIG = ROOT / "config" / "agent-health.yaml"
SCHEMA_VERSION = 1
OK, WARN, FAIL = "ok", "warn", "fail"
METHODS = ("GET", "POST")
KINDS = ("webapp", "gateway-only")
GATEWAY_CHECK = "gateway-log"
# Lý do hiện trên tab. Response body chỉ được giữ cho phép kiểm có câu hỏi (case), vì đó là câu trả
# lời cần làm bằng chứng; nó có thể chứa dữ liệu nghiệp vụ, nên chỉ đọc được qua khoá dashboard.
REASON_MAX = 500
BODY_MAX = 1 << 20
MISSING = object()
# `features[id=ctda]` -> tên mảng `features`, chọn phần tử đầu tiên có `id == "ctda"`.
SEGMENT = re.compile(r"^([^\[\]]+)\[([^=\]]+)=([^\]]*)\]$")


# --------------------------------------------------------------------------- cấu hình


def load_config(path: Path) -> dict:
    """Đọc và kiểm YAML. Sai thì dừng ngay lúc khởi động, không đợi tới giờ chạy mới biết."""
    # Import trong hàm: bộ test_*.py phải chạy được trên máy sạch, không cài PyYAML (xem ci.yml).
    import yaml
    return check_config(yaml.safe_load(path.read_text(encoding="utf-8")) or {}, path)


def check_config(raw: dict, path) -> dict:
    agents = raw.get("agents") or {}
    if not agents:
        raise SystemExit(f"{path}: no agents configured")
    for code, agent in agents.items():
        for key in ("base_url", "auth", "checks"):
            if not agent.get(key):
                raise SystemExit(f"{path}: agent {code!r} has no {key!r}")
        if not (agent["auth"].get("header") and agent["auth"].get("env")):
            raise SystemExit(f"{path}: agent {code!r} needs auth.header and auth.env")
        # Module chụp màn hình chọn cách chụp theo `kind`: thiếu thì nó phải đoán.
        if agent.get("kind") not in KINDS:
            raise SystemExit(f"{path}: agent {code!r} needs kind: one of {', '.join(KINDS)}")
        if agent["kind"] == "webapp" and not agent.get("app_url"):
            raise SystemExit(f"{path}: agent {code!r} is a webapp and needs app_url")
        allowed = set(agent.get("allow_post") or [])
        for check in agent["checks"]:
            if not check.get("name") or not check.get("path"):
                raise SystemExit(f"{path}: agent {code!r} has a check without name or path")
            if "question" in check and not check.get("question_field"):
                raise SystemExit(f"{path}: agent {code!r} check {check['name']!r} has a question "
                                 f"but no question_field")
            method = str(check.get("method", "GET")).upper()
            if method not in METHODS:
                raise SystemExit(f"{path}: agent {code!r} check {check['name']!r} uses {method}; "
                                 f"only GET and POST are allowed")
            if method == "POST" and check["path"] not in allowed:
                raise SystemExit(f"{path}: agent {code!r} POST {check['path']} is not in allow_post")
    return agents


# --------------------------------------------------------------------------- đánh giá


def field(data, path: str):
    """Đọc `a.b` và `list[key=value].c`. Không có thì trả MISSING, không ném lỗi."""
    for part in path.split("."):
        match = SEGMENT.match(part)
        name = match.group(1) if match else part
        if not isinstance(data, dict) or name not in data:
            return MISSING
        data = data[name]
        if match:
            if not isinstance(data, list):
                return MISSING
            key, want = match.group(2), match.group(3)
            data = next((x for x in data if isinstance(x, dict) and str(x.get(key)) == want), MISSING)
            if data is MISSING:
                return MISSING
    return data


def same(a, b) -> bool:
    # Python coi `1 == True`. JSON `1` không được khớp YAML `true`.
    return isinstance(a, bool) == isinstance(b, bool) and a == b


def show(value) -> str:
    return "missing" if value is MISSING else repr(value)


def clip(text: str) -> str:
    return text[:REASON_MAX]


def parse_moment(value):
    if not isinstance(value, str):
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Ralli trả `2027-10-28T01:29:00`, không múi giờ. Coi là UTC: ngưỡng tính bằng ngày nên lệch 7 giờ
    # không đổi kết luận (design.md, Risks).
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def problem_reason(status: int, body: bytes) -> str:
    """Lý do lỗi: `title` + `detail` của problem+json nếu có, không thì chỉ mã HTTP."""
    try:
        doc = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        doc = None
    if isinstance(doc, dict) and (doc.get("title") or doc.get("detail")):
        text = " - ".join(str(doc[k]) for k in ("title", "detail") if doc.get(k))
        return f"HTTP {status}: {text}"
    return f"HTTP {status}"


def evaluate(check: dict, status: int, body: bytes, now: datetime) -> tuple[str, str]:
    """Ba mức theo design.md D4. Trả về (mức, lý do)."""
    expect = check.get("expect") or {}
    if status == 429:
        # Hết hạn mức request hoặc hết AI budget: agent còn sống, chỉ đang bị giới hạn.
        return WARN, clip(problem_reason(status, body) + " (rate or AI budget limit)")
    want = expect.get("status")
    if want is not None and status != want:
        return FAIL, clip(problem_reason(status, body))
    if not any(expect.get(k) for k in ("equals", "not_equals", "days_until")):
        return OK, ""
    try:
        doc = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return FAIL, "Response body is not JSON"
    for path, value in (expect.get("equals") or {}).items():
        got = field(doc, path)
        if got is MISSING or not same(got, value):
            return FAIL, clip(f"{path} = {show(got)}, expected {value!r}")
    for path, value in (expect.get("not_equals") or {}).items():
        got = field(doc, path)
        if got is not MISSING and same(got, value):
            return FAIL, clip(f"{path} = {value!r}")
    warnings = []
    for path, days in (expect.get("days_until") or {}).items():
        moment = parse_moment(field(doc, path))
        if moment is None:
            return FAIL, clip(f"{path} is missing or not a date")
        left = (moment - now).total_seconds() / 86400
        if left < days:
            warnings.append(f"{path} in {left:.0f} days")
    return (WARN, clip("; ".join(warnings))) if warnings else (OK, "")


# --------------------------------------------------------------------------- gọi agent


def url_of(agent: dict, check: dict) -> str:
    return agent["base_url"].rstrip("/") + check["path"]


def method_of(check: dict) -> str:
    return str(check.get("method", "GET")).upper()


def vn_now() -> str:
    return datetime.now(VN).isoformat(timespec="seconds")


def http_call(agent: dict, check: dict, key: str) -> tuple[int, bytes, str | None, int]:
    """Trả về (mã HTTP, thân, X-Request-ID, ms). Lỗi mạng thì ném ra cho người gọi xếp `fail`."""
    url, method = url_of(agent, check), method_of(check)
    # Accept JSON: agent hỗ trợ cả text/event-stream, không xin thì không nhận.
    headers = {"Accept": "application/json", agent["auth"]["header"]: key}
    data = None
    if method == "POST":
        body = dict(check.get("body") or {})
        if "question" in check:
            body[check["question_field"]] = check["question"]
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=float(check.get("timeout", 30))) as response:
            status, body, rid = response.status, response.read(BODY_MAX), response.headers.get("X-Request-ID")
    except urllib.error.HTTPError as exc:
        status, body, rid = exc.code, exc.read(BODY_MAX), exc.headers.get("X-Request-ID")
    return status, body, rid, int((time.monotonic() - started) * 1000)


def blank(code: str, name: str) -> dict:
    return {"agent_code": code, "check_name": name, "status": FAIL, "reason": "",
            "http_status": None, "latency_ms": None, "request_id": None, "sent_at": None}


def keep_body(raw: bytes):
    """Thân response để làm bằng chứng: JSON thì giữ nguyên cấu trúc, không thì giữ chữ."""
    try:
        return json.loads(raw)
    except ValueError:                                              # gồm cả UnicodeDecodeError
        return raw.decode("utf-8", "replace")


def run_check(code: str, agent: dict, check: dict) -> dict:
    result = {**blank(code, check["name"]), "method": method_of(check), "url": url_of(agent, check)}
    if "question" in check:
        result.update(question=check["question"], expected=check.get("expect") or {},
                      answer=None, body=None)
    key = env(agent["auth"]["env"])
    if not key:
        # Không bỏ qua im lặng: bỏ qua thì tab trông như "không có lỗi".
        return {**result, "reason": f"Environment variable {agent['auth']['env']} is not set"}
    result["sent_at"] = vn_now()
    try:
        status, body, rid, ms = http_call(agent, check, key)
    except Exception as exc:                                        # noqa: BLE001
        # Timeout, DNS, TLS. Thông báo có URL nhưng không bao giờ có key: key chỉ nằm trong header.
        return {**result, "reason": clip(f"{type(exc).__name__}: {exc}")}
    level, reason = evaluate(check, status, body, datetime.now(timezone.utc))
    result.update(status=level, reason=reason, http_status=status, latency_ms=ms, request_id=rid)
    if "question" in check:
        result["body"] = keep_body(body)
        if check.get("answer"):
            got = field(result["body"], check["answer"])
            result["answer"] = None if got is MISSING else got
    return result


def gateway_log_check(code: str, agent: dict, start: datetime, end: datetime,
                      attempts: int = 6, pause: float = 5.0) -> dict:
    """Có dòng `LiteLLM_SpendLogs` mang tag của agent trong khoảng thời gian các phép kiểm không.

    Gateway ghi sổ sau vài giây, nên hỏi lại tối đa `attempts` lần. Lúc có người thật đang dùng
    agent thì một dòng cùng tag chưa chắc là của lần kiểm này (design.md D5).
    """
    result = blank(code, GATEWAY_CHECK)
    dsn = env("GATEWAY_DSN")
    if not dsn:
        return {**result, "reason": "GATEWAY_DSN is not set"}
    import psycopg2
    tag = agent["gateway_tag"]
    found = 0
    try:
        for attempt in range(attempts):
            with closing(psycopg2.connect(dsn, connect_timeout=5)) as cn:
                cn.set_session(readonly=True)
                with cn.cursor() as cur:
                    cur.execute('SELECT count(*) FROM "LiteLLM_SpendLogs" '
                                'WHERE "startTime" BETWEEN %s AND %s AND request_tags::jsonb ? %s',
                                (start - timedelta(seconds=5), end + timedelta(seconds=60), tag))
                    found = cur.fetchone()[0]
            if found or attempt == attempts - 1:
                break
            time.sleep(pause)
    except Exception as exc:                                        # noqa: BLE001
        return {**result, "reason": clip(f"Cannot read Gateway log: {type(exc).__name__}: {exc}")}
    if not found:
        return {**result, "reason": f"No Gateway log row tagged {tag!r} for this run"}
    return {**result, "status": OK, "reason": f"{found} Gateway log row(s) tagged {tag!r}"}


def plan(agents: dict, dry_run: bool = False) -> list[tuple[str, dict, dict | None]]:
    """Danh sách bước của một lần chạy. `None` là bước đối chiếu Gateway. Độ dài = `total`."""
    steps = []
    for code, agent in agents.items():
        for check in agent["checks"]:
            if dry_run and str(check.get("method", "GET")).upper() == "POST":
                LOG.info("Skipping %s %s POST %s (dry run)", code, check["name"], check["path"])
                continue
            steps.append((code, agent, check))
        if agent.get("gateway_tag") and not dry_run:
            steps.append((code, agent, None))
    return steps


def item(r: dict) -> dict:
    x = {"name": r["check_name"], "method": r.get("method"), "url": r.get("url"), "sent_at": r["sent_at"],
         "http_status": r["http_status"], "latency_ms": r["latency_ms"], "request_id": r["request_id"],
         "status": r["status"], "reason": r["reason"]}
    if "question" in r:
        x.update(question=r["question"], expected=r["expected"], answer=r["answer"], body=r["body"])
    return x


def document(meta: dict, agents: dict, results: list[dict]) -> dict:
    """Tài liệu kết quả (khuôn ở docs/reference/agent-health-result.md). Agent chưa tới lượt thì chưa có."""
    out = []
    for code, agent in agents.items():
        mine = [r for r in results if r["agent_code"] == code]
        if not mine:
            continue
        out.append({"agent_code": code, "agent_name": agent.get("name", code), "kind": agent.get("kind"),
                    "app_url": agent.get("app_url"), "test_identity": agent.get("test_identity"),
                    # Mức của agent là mức tệ nhất trong các phép kiểm của nó.
                    "status": max((r["status"] for r in mine), key=(OK, WARN, FAIL).index),
                    "health": [item(r) for r in mine if "question" not in r],
                    "cases": [item(r) for r in mine if "question" in r]})
    return {"schema_version": SCHEMA_VERSION, **meta, "agents": out, "limitations": []}


def dump(doc: dict, **kw) -> str:
    # `default=str`: YAML đọc `2026-10-29` thành `date`, mà `expected` được chép thẳng từ YAML.
    return json.dumps(doc, ensure_ascii=False, default=str, **kw)


def write_result(doc: dict) -> Path:
    folder = Path(env("AGENT_CHECKS_DIR", str(ROOT / "var" / "agent-checks"))) / doc["run_id"]
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / "result.json.tmp"
    tmp.write_text(dump(doc, indent=2), encoding="utf-8")
    # Đổi tên là nguyên tử: module chụp màn hình không bao giờ đọc phải tệp đang viết dở.
    tmp.replace(folder / "result.json")
    return folder / "result.json"


def execute(agents: dict, store, run_id, dry_run: bool = False) -> list[dict]:
    """Chạy mọi bước, ghi tiến độ. Một bước hỏng không dừng các bước sau.

    `store` là None khi chạy thử (`--dry-run`): không ghi DB, không ghi tệp.
    """
    steps = plan(agents, dry_run)
    if store:
        meta = store.begin(run_id, len(steps))
    windows: dict[str, tuple[datetime, datetime]] = {}
    results = []
    for code, agent, check in steps:
        name = check["name"] if check else GATEWAY_CHECK
        if store:
            # Ghi TRƯỚC khi gọi: thanh tiến độ phải nói đang chờ phép nào, kể cả khi phép đó mất 180 giây.
            store.label(run_id, f"{agent.get('name', code)} - {name}")
        try:
            if check is None:
                now = datetime.now(timezone.utc)
                start, end = windows.get(code, (now, now))
                result = gateway_log_check(code, agent, start, end)
            else:
                start = datetime.now(timezone.utc)
                result = run_check(code, agent, check)
                windows[code] = (windows.get(code, (start, start))[0], datetime.now(timezone.utc))
        except Exception as exc:                                    # noqa: BLE001
            result = {**blank(code, name), "reason": clip(f"Unexpected {type(exc).__name__}: {exc}")}
        result["agent_name"] = agent.get("name", code)
        LOG.info("%s %s: %s %s %s", code, name, result["status"], result["http_status"] or "-",
                 result["reason"])
        results.append(result)
        if store:
            store.record(run_id, document(meta, agents, results))
    if store:
        doc = document({**meta, "finished_at": vn_now()}, agents, results)
        try:
            LOG.info("Wrote %s", write_result(doc))
        except OSError as exc:
            # Không để lỗi ghi tệp làm mất kết quả: DB vẫn nhận tài liệu, kèm lý do thiếu tệp.
            doc["limitations"].append(clip(f"result.json was not written: {exc}"))
            LOG.error("Could not write result.json: %s", exc)
        store.finish(run_id, doc)
    return results


# --------------------------------------------------------------------------- lịch


def is_due(now_vn: datetime, run_at, last_run_date) -> bool:
    """Lịch đến giờ chưa. `now_vn` phải là giờ VN: container chạy UTC."""
    return now_vn.time() >= run_at and last_run_date != now_vn.date()


class Store:
    """Mọi câu SQL của service. Chạy bằng vai admin của image tools (TOKEN_LEDGER_DSN)."""

    def __init__(self, dsn: str):
        if not dsn:
            raise SystemExit("TOKEN_LEDGER_DSN is required")
        self.dsn = dsn

    @contextmanager
    def tx(self):
        import psycopg2
        cn = psycopg2.connect(self.dsn, connect_timeout=5)
        try:
            with cn:
                with cn.cursor() as cur:
                    yield cur
        finally:
            cn.close()

    def interrupt_running(self) -> int:
        with self.tx() as cur:
            cur.execute("UPDATE agent_health_run SET status = 'interrupted', finished_at = now() "
                        "WHERE status = 'running'")
            return cur.rowcount

    def interrupt(self, run_id) -> None:
        with self.tx() as cur:
            cur.execute("UPDATE agent_health_run SET status = 'interrupted', finished_at = now() "
                        "WHERE id = %s AND status = 'running'", (str(run_id),))

    def take_manual(self):
        with self.tx() as cur:
            cur.execute("UPDATE agent_health_run SET status = 'running', started_at = now() "
                        "WHERE id = (SELECT id FROM agent_health_run WHERE status = 'queued' "
                        "AND trigger = 'manual' ORDER BY requested_at LIMIT 1 FOR UPDATE SKIP LOCKED) "
                        "RETURNING id")
            row = cur.fetchone()
            return row[0] if row else None

    def claim_schedule(self, now_vn: datetime):
        import psycopg2
        today = now_vn.date()
        try:
            with self.tx() as cur:
                cur.execute("SELECT run_at, last_run_date FROM agent_health_setting WHERE id = 1 FOR UPDATE")
                row = cur.fetchone()
                if row is None or not is_due(now_vn, row[0], row[1]):
                    return None
                cur.execute("UPDATE agent_health_setting SET last_run_date = %s "
                            "WHERE id = 1 AND last_run_date IS DISTINCT FROM %s", (today, today))
                if cur.rowcount != 1:
                    return None
                run_id = str(uuid.uuid4())
                cur.execute("INSERT INTO agent_health_run (id, trigger, status, requested_by, started_at) "
                            "VALUES (%s, 'schedule', 'running', 'schedule', now())", (run_id,))
                return run_id
        except psycopg2.errors.UniqueViolation:
            # Đang có một lần chạy khác. Cả transaction rollback, `last_run_date` KHÔNG bị ghi,
            # nên lịch hôm nay chạy ở vòng sau chứ không mất.
            LOG.info("Another run is active; the scheduled run waits for the next tick")
            return None

    def create_cli_run(self):
        import psycopg2
        run_id = str(uuid.uuid4())
        try:
            with self.tx() as cur:
                cur.execute("INSERT INTO agent_health_run (id, trigger, status, requested_by, started_at) "
                            "VALUES (%s, 'manual', 'running', 'cli', now())", (run_id,))
        except psycopg2.errors.UniqueViolation:
            return None
        return run_id

    def begin(self, run_id, total: int) -> dict:
        """Đặt tổng số bước; trả phần đầu của tài liệu kết quả, lấy từ chính dòng của lần chạy."""
        with self.tx() as cur:
            cur.execute("UPDATE agent_health_run SET total = %s WHERE id = %s "
                        "RETURNING trigger, requested_by, started_at", (total, str(run_id)))
            trigger, requested_by, started_at = cur.fetchone()
        return {"run_id": str(run_id), "trigger": trigger, "requested_by": requested_by,
                "started_at": started_at.astimezone(VN).isoformat(timespec="seconds"), "finished_at": None}

    def label(self, run_id, text: str) -> None:
        with self.tx() as cur:
            cur.execute("UPDATE agent_health_run SET current_label = %s WHERE id = %s", (text, str(run_id)))

    def record(self, run_id, doc: dict) -> None:
        # Tài liệu và `done` trong cùng một câu: thanh tiến độ không bao giờ đi trước kết quả.
        with self.tx() as cur:
            cur.execute("UPDATE agent_health_run SET result = %s::jsonb, done = done + 1 WHERE id = %s",
                        (dump(doc), str(run_id)))

    def finish(self, run_id, doc: dict) -> None:
        with self.tx() as cur:
            cur.execute("UPDATE agent_health_run SET status = 'done', finished_at = now(), "
                        "current_label = NULL, result = %s::jsonb WHERE id = %s",
                        (dump(doc), str(run_id)))


def tick(store, agents: dict, now_vn: datetime):
    """Một vòng. Lần chạy tay đang chờ được xét TRƯỚC lịch (xem docstring đầu tệp)."""
    run_id = store.take_manual()
    if run_id is None:
        run_id = store.claim_schedule(now_vn)
    if run_id is None:
        return None
    try:
        execute(agents, store, run_id)
    except Exception:
        # Lỗi DB giữa chừng: không để lần chạy kẹt ở `running`, vì index duy nhất sẽ khoá nút "Chạy ngay".
        try:
            store.interrupt(run_id)
        except Exception:                                           # noqa: BLE001
            LOG.error("Could not mark run %s interrupted", run_id)
        raise
    return run_id


def print_results(results: list[dict]) -> None:
    for r in results:
        print(f"{r['status']:<4}  {r['agent_code']:<12} {r['check_name']:<14} "
              f"{r['http_status'] or '-':>4} {r['latency_ms'] or '-':>6} ms  {r['reason']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=str(CONFIG), help="checks file")
    parser.add_argument("--every", type=float, default=5.0, help="seconds between ticks")
    parser.add_argument("--once", action="store_true",
                        help="run every check now and record it; DOES call POST checks")
    parser.add_argument("--dry-run", action="store_true",
                        help="run GET checks only, print, write nothing")
    args = parser.parse_args()

    logging.basicConfig(level=env("LOG_LEVEL", "INFO").upper(),
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    agents = load_config(Path(args.config))
    LOG.info("Loaded %d agent(s): %s", len(agents), ", ".join(agents))

    if args.dry_run:
        results = execute(agents, None, None, dry_run=True)
        print_results(results)
        return 1 if any(r["status"] == FAIL for r in results) else 0

    store = Store(env("TOKEN_LEDGER_DSN"))
    if args.once:
        run_id = store.create_cli_run()
        if run_id is None:
            LOG.error("Another run is queued or running; try again when it finishes")
            return 1
        try:
            results = execute(agents, store, run_id)
        except Exception:
            store.interrupt(run_id)
            raise
        print_results(results)
        return 1 if any(r["status"] == FAIL for r in results) else 0

    interrupted = store.interrupt_running()
    if interrupted:
        LOG.warning("Marked %d unfinished run(s) as interrupted", interrupted)
    while True:
        try:
            tick(store, agents, datetime.now(timezone.utc).astimezone(VN))
        except Exception as exc:                                    # noqa: BLE001
            # Một vòng hỏng MUST NOT giết vòng lặp: service chết lặng lẽ trông y hệt "mọi thứ ổn".
            LOG.error("Tick failed (%s: %s); continuing", type(exc).__name__, exc)
        time.sleep(args.every)


if __name__ == "__main__":
    raise SystemExit(main())
