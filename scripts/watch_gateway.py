"""Canh Gateway theo nhịp rồi gửi thư khi trạng thái đổi.

    python scripts/watch_gateway.py --once --dry-run
    python scripts/watch_gateway.py --every 60

VÌ SAO CÓ FILE NÀY

Trước 17/09/2026, việc báo động khi Gateway hỏng nằm **bên trong agent**: agent đổi đường thì agent
gửi thư. Đo 17/09: chỉ 1 trong 8 agent có mã ấy. Bảy agent còn lại, Gateway chết là im lặng.

Thư của agent còn một khoảng lặng nữa, không sửa được bằng cách thêm agent: nó chỉ tồn tại khi có
một lô đang chạy. Gateway chết lúc 2 giờ sáng thì không ai biết, và tới 6 giờ sáng lô đã chạy trên
hạ tầng hỏng rồi.

File này đứng ngoài mọi agent, chạy suốt, và phủ cả tám.

NÓ KHÔNG DÒ LẠI THỨ ĐÃ CÓ NGƯỜI DÒ

`tools/gateway-status/server.js` đã dò sẵn bốn thành phần (`lb`, `proxy1`, `proxy2`, `route`) và gộp
thành `reachable` / `degraded` / `unavailable`. File này **đọc** kết quả đó qua `/api/status` chứ
không dựng bộ dò thứ hai — hai chỗ cùng dò một thứ theo hai kiểu là loại lệch không ai nhớ vì sao.

BA ĐÍCH, BA LỚP KHÁC NHAU — xem design.md D3

    (A)  tên miền public /lb-health       DNS + TLS + proxy máy chủ + nginx còn sống
    (B)  /api/status                      instance nào chết, degraded hay unavailable
    (C)  /health/readiness                LiteLLM sẵn sàng + db: connected

Đo 17/09 bằng `docker stop litellm-1`: `/lb-health` trả `lb-ok`, `/health/readiness` trả `healthy`,
**chỉ** `/api/status` trả `degraded`. Tức (C) cũng mù khi mất một instance — vì nó đi qua LB và LB
đẩy sang instance còn sống. Đó là lý do (B) không thừa.

MỌI ĐÍCH ĐỌC TỪ BIẾN, KHÔNG GHIM TRONG MÃ — design.md D11

Cùng một tệp chạy được ở hai chỗ: trong mạng Docker của Gateway (đọc được chiều sâu), và trên một
máy khác (thấy được cả cái chết của chính máy chủ). Hai chỗ khác nhau ở **tập đích**, không khác ở
hành vi — nên không có nhánh `if` nào theo môi trường.

Và mỗi đích phải **bỏ qua được**. Đo 17/09: `apigateway.rangdong.com.vn` chưa tồn tại
(`Non-existent domain`), nên bật (A) trên máy phát triển là tự tạo một đích đỏ mỗi phút trong khi
hệ thống hoàn toàn khoẻ.

THƯ GỘP THEO LẦN ĐỔI TRẠNG THÁI, KHÔNG THEO NHỊP DÒ

Một sự cố dài có hàng trăm nhịp. Gửi mỗi nhịp một thư là làm người nhận tắt thông báo, tức phép báo
động tự huỷ chính nó. Trạng thái ghi ra tệp chứ không giữ trong bộ nhớ, vì container mang
`restart: unless-stopped` và sẽ được dựng lại giữa sự cố.

NGUỒN TÌNH TRẠNG KHÔNG ĐỌC ĐƯỢC CHƯA ĐỦ KẾT LUẬN GATEWAY CHẾT

Collector Node nằm cùng container với Nginx nhưng là một tiến trình và cổng riêng. Nếu phép đọc
collector hỏng mà readiness vẫn trả lời, watcher giữ trạng thái riêng thay vì báo Gateway chết;
các đích HTTP vẫn là trọng tài.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import smtplib
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

LOG = logging.getLogger("gateway-watch")

# Giờ Việt Nam. KHÔNG dùng giờ địa phương của máy: container chạy UTC (đo 09/09/2026), nên mọi mốc
# trong thư sẽ lệch đúng 7 tiếng và một sự cố vừa xảy ra trông như đã qua từ chiều hôm trước.
VN = timezone(timedelta(hours=7))

# Bốn trạng thái, không hai. Ba trạng thái đầu lấy thẳng từ `gateway-status`; trạng thái thứ tư là
# của chính chỗ canh, dành cho ca "không đọc được tình trạng mà Gateway vẫn khoẻ".
OK, DEGRADED, DOWN, BLIND = "reachable", "degraded", "unavailable", "status_unreadable"

SEVERITY = {OK: "OK", DEGRADED: "WARN", BLIND: "WARN", DOWN: "DOWN"}

# Tiêu đề viết thành câu, không ghép máy móc từ tên trạng thái. Người nhận đọc tiêu đề TRƯỚC, và
# `Gateway status_unreadable` đọc lướt thì trông y như Gateway hỏng — đúng kiểu hiểu nhầm làm người
# ta chạy đi sửa nhầm thứ lúc nửa đêm.
SUBJECT = {
    OK: "Gateway da tro lai binh thuong",                           # vi-ok: email subject
    DEGRADED: "Gateway mat mot phan nang luc, VAN dang phuc vu",    # vi-ok: email subject
    DOWN: "GATEWAY HONG",                                           # vi-ok: email subject
    BLIND: "Khong doc duoc trang thai (Gateway van tra loi)",       # vi-ok: email subject
}


# --------------------------------------------------------------------------- cấu hình


def env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def parse_pairs(raw: str) -> dict[str, str]:
    """`"a=1 b=2"` -> `{"a": "1", "b": "2"}`.

    Tách theo khoảng trắng vì URL không chứa khoảng trắng — dấu phẩy thì có thể nằm trong URL.
    Mục nào không có `=` thì bỏ qua, không làm hỏng cả danh sách: một dòng cấu hình gõ nhầm MUST
    NOT làm chỗ canh không khởi động được.
    """
    out: dict[str, str] = {}
    for item in raw.split():
        name, sep, value = item.partition("=")
        if sep and name and value:
            out[name] = value
        elif item:
            LOG.warning("Ignoring malformed entry %r (expected name=value)", item)
    return out


# --------------------------------------------------------------------------- phép dò


def fetch(url: str, timeout: float, host: str = "") -> tuple[int, bytes]:
    """Trả về `(mã, thân)`. Ném ngoại lệ nếu không tới được.

    `timeout` là bắt buộc ở mọi lượt gọi: một tiến trình treo thì không bao giờ báo được gì, mà
    treo lại là chế độ hỏng tệ nhất của chỗ canh — im lặng trông y hệt "mọi thứ bình thường".
    """
    request = urllib.request.Request(url, headers={"Host": host} if host else {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read(65536)


def probe_http(targets: dict[str, str], expect: dict[str, str],
               timeout: float) -> dict[str, str]:
    """Dò từng đích. Trả về `{tên: ""}` nếu đạt, `{tên: "lý do"}` nếu hỏng."""
    result: dict[str, str] = {}
    for name, url in targets.items():
        try:
            status, body = fetch(url, timeout)
            if status != 200:
                result[name] = f"HTTP {status}"
            elif expect.get(name) and expect[name].encode() not in body:
                # 200 chưa chắc là đúng: một reverse proxy cấu hình sai vẫn trả 200 kèm trang
                # đăng nhập, và `/health/readiness` có thể trả 200 mà `db` không connected.
                result[name] = f"body missing {expect[name]!r}"
            else:
                result[name] = ""
        except urllib.error.HTTPError as exc:
            result[name] = f"HTTP {exc.code}"
        except (urllib.error.URLError, socket.timeout, ssl.SSLError,
                ConnectionError, OSError) as exc:
            result[name] = f"{type(exc).__name__}: {exc}"
    return result


def probe_status(url: str, host: str, timeout: float) -> tuple[str, list[dict], str]:
    """Đọc `/api/status`. Trả về `(trạng thái, thành phần, lý do đọc hỏng)`.

    `Host` phải là `localhost`: `tools/gateway-status/server.js` chặn cứng theo header ấy và trả
    403 cho mọi giá trị khác. Đo 17/09: có header thì 200, thiếu header thì `403 Forbidden.`
    """
    try:
        status, body = fetch(url, timeout, host)
        if status != 200:
            return "", [], f"HTTP {status}"
        data = json.loads(body)
        if not isinstance(data, dict):
            return "", [], "response is not an object"
        components = data.get("components")
        return str(data.get("status") or ""), \
            components if isinstance(components, list) else [], ""
    except Exception as exc:                                        # noqa: BLE001
        # Bắt rộng có chủ ý: JSON hỏng, thân rỗng, kiểu sai, mạng hỏng — mọi thứ đều dẫn tới cùng
        # một kết luận "không đọc được tình trạng", và phân biệt chúng không đổi hành động.
        return "", [], f"{type(exc).__name__}: {exc}"


def decide(http: dict[str, str], status: str, status_error: str,
           has_status: bool) -> str:
    """Gộp kết quả dò thành một trạng thái.

    LUẬT: **đích HTTP quyết định có hỏng hay không; `/api/status` chỉ quyết định hỏng tới đâu.**

    Vì sao không để `/api/status` tự quyết, dù nó nhìn được nhiều hơn — đo 17/09/2026, dừng
    `litellm-1` rồi đo cùng lúc:

        (C) /health/readiness qua LB   DAT       <- Gateway VAN phuc vu duoc
        (B) /api/status                unavailable
                route  unreachable  "Liveness check timed out."

    `tools/gateway-status/server.js` dò `route` với hạn **2,5 giây**, và `createMonitor` chặn cứng
    không cho khai quá 2500ms. Mà `nginx.conf` khai `proxy_connect_timeout 10s` với
    `proxy_next_upstream_tries 2`, nên trong lúc nginx đang tự chuyển sang instance còn sống, phép
    dò của nó bỏ cuộc trước — `route` hoá `unreachable` dù Gateway vẫn trả lời bình thường.

    Tin `/api/status` ở đây là báo `unavailable` cho một ca mà agent **vẫn gọi được**. Sai mức độ,
    và sai theo hướng tệ nhất: gọi người dậy lúc nửa đêm cho một sự cố không có thật.

    Nên một lượt gọi THẬT đi xuyên qua load balancer và trả về đúng thân tin cậy hơn một phép dò
    tổng hợp bị bó hạn thời gian. `/api/status` vẫn cần — nó là thứ duy nhất nói được instance nào
    chết (xem D3) — chỉ là nó không được quyền tuyên bố "chết hẳn".
    """
    http_ok = all(not reason for reason in http.values())

    if has_status and status_error:
        # Nguồn tình trạng im. Các đích HTTP làm trọng tài — thiếu bước này thì mỗi lần
        # `gateway-status` dựng lại là một thư báo động giả.
        return BLIND if http_ok else DOWN
    if not http_ok:
        # Một lượt gọi thật qua LB cũng không xong. Đây mới là "hỏng hẳn".
        return DOWN
    if not http:
        # Không có đích HTTP nào để làm trọng tài — bản chạy trên máy khác rơi vào đây nếu chỉ khai
        # `WATCH_STATUS_URL`. Lúc ấy đành theo `/api/status`, kèm đúng cái trần vừa nói ở trên.
        return status if status in (OK, DEGRADED, DOWN) else OK
    if status and status != OK:
        # Lượt gọi thật VẪN xong, nên Gateway còn phục vụ được; `/api/status` chỉ đang nói rằng
        # năng lực đã sứt. `degraded` và `unavailable` của nó gộp về cùng một mức ở đây.
        return DEGRADED
    return OK


# --------------------------------------------------------------------------- trạng thái


def load_state(path: Path) -> dict:
    """Đọc tệp trạng thái. Tệp rỗng hay hỏng thì coi như đang khoẻ rồi chạy tiếp."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        LOG.warning("State file %s is not an object; starting from healthy", path)
    except FileNotFoundError:
        pass
    except Exception as exc:                                        # noqa: BLE001
        LOG.warning("Cannot read state file %s (%s); starting from healthy",
                    path, type(exc).__name__)
    return {}


def save_state(path: Path, state: dict) -> None:
    """Ghi ra tệp tạm rồi đổi tên: cắt điện giữa chừng MUST NOT để lại tệp dở."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.replace(tmp, path)
    except Exception as exc:                                        # noqa: BLE001
        LOG.error("Cannot write state file %s: %s: %s", path, type(exc).__name__, exc)


# --------------------------------------------------------------------------- thư


def send_mail(subject: str, body: str, dry_run: bool) -> None:
    """Gửi thư. Hỏng thì ghi log rồi trả về — MUST NOT làm dừng vòng lặp dò.

    Báo động là việc phụ; việc chính là tiếp tục canh. Cùng thứ tự ưu tiên mà quyết định ngày
    10/09 đặt ra cho Gateway.
    """
    if dry_run:
        print("=" * 72)
        print("Subject:", subject)
        print(body)
        print("=" * 72)
        return
    recipients = [x for x in env("SMTP_TO").replace(",", " ").split() if x]
    host = env("SMTP_HOST")
    if not host or not recipients:
        LOG.error("Mail not sent: SMTP_HOST or SMTP_TO is empty")
        return
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = env("SMTP_FROM") or env("SMTP_USERNAME")
    message["To"] = ", ".join(recipients)
    # UTF-8 tường minh: thân thư là tiếng Việt có dấu, thiếu khai thì tới nơi thành ký tự lạ.
    message.set_content(body, charset="utf-8")
    try:
        port = int(env("SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=30) as server:
            # So với CẢ MỘT TẬP giá trị tắt, không chỉ `"0"`. CRM ghi `SMTP_USE_TLS=true`, nên
            # phép so `!= "0"` sẽ bật TLS cả khi ai đó ghi `false` — im lặng làm ngược ý.
            if env("SMTP_USE_TLS", "1").lower() not in ("0", "false", "no", "off", ""):
                server.starttls(context=ssl.create_default_context())
            if env("SMTP_USERNAME"):
                server.login(env("SMTP_USERNAME"), env("SMTP_PASSWORD"))
            server.send_message(message)
        LOG.info("Mail sent: %s", subject)
    except Exception as exc:                                        # noqa: BLE001
        # CHỈ tên lớp ngoại lệ, không in `exc`: câu lỗi của smtplib có thể mang theo tên đăng nhập,
        # và `docker logs` thì ai đọc cũng được.
        LOG.error("Mail failed (%s); the watch loop continues", type(exc).__name__)


def stamp(moment: datetime) -> str:
    return moment.astimezone(VN).strftime("%d/%m/%Y %H:%M:%S") + " (gio VN)"


def human_duration(seconds: float) -> str:
    seconds = int(max(seconds, 0))
    if seconds < 60:
        return f"{seconds} giay"                    # vi-ok: email text
    if seconds < 3600:
        return f"{seconds // 60} phut {seconds % 60} giay"          # vi-ok: email text
    return f"{seconds // 3600} gio {seconds % 3600 // 60} phut"     # vi-ok: email text


def parse_since(since: str) -> datetime | None:
    """Đọc mốc bắt đầu từ tệp trạng thái. Hỏng thì trả `None` — thư vẫn phải gửi được."""
    try:
        return datetime.fromisoformat(since) if since else None
    except ValueError:
        LOG.warning("State file has an unreadable start time %r", since)
        return None


def diagnose(components: list[dict]) -> str:
    """Một dòng kết luận từ bảng thành phần của `gateway-status`.

    D3: chênh lệch giữa các lớp CHÍNH LÀ chẩn đoán. Bảng ở cuối thư có đủ dữ kiện, nhưng đọc được
    nó thì phải biết `proxy1` là gì; người bị gọi dậy lúc nửa đêm không nợ ai kiến thức đó.
    """
    state_of = {str(c.get("id")): str(c.get("status"))
                for c in components if isinstance(c, dict)}
    if not state_of:
        return ""
    dead = [name for name in ("proxy1", "proxy2")
            if state_of.get(name, "reachable") != "reachable"]
    if state_of.get("lb", "reachable") != "reachable":
        # nginx im thì mọi thứ sau nó đều đỏ theo, không suy ra được gì thêm.
        return "nginx (gateway-lb) khong tra loi -- hong o lop ngoai cung."   # vi-ok: email text
    if len(dead) == 2:
        return "nginx con song, nhung CA HAI instance LiteLLM deu chet."      # vi-ok: email text
    if dead:
        return f"nginx con song, instance {dead[0]} chet."                    # vi-ok: email text
    return "Cac thanh phan deu bao song -- hong o duong di toi chung."        # vi-ok: email text


def build_body(watch_name: str, new: str, old: str, now: datetime,
               since: str, http: dict[str, str], status: str,
               components: list[dict], status_error: str, every: int) -> str:
    """Dựng thân thư. Tiếng Việt có dấu — người đọc là người vận hành, không phải log."""
    lines = [
        f"Trang thai: {old or '?'}  ->  {new}",                     # vi-ok: email text
        f"Thoi diem:  {stamp(now)}",                                # vi-ok: email text
        "",
    ]
    started = parse_since(since)
    if new == DOWN:
        lines += [
            "Gateway KHONG phuc vu duoc: moi luot goi di qua Gateway deu dang hong.",  # vi-ok: email text
            "Agent nao co duong du phong thi van chay (goi thang nha cung cap); agent khong co thi dung.",  # vi-ok: email text
        ]
        # Chẩn đoán một dòng. Bảng thành phần ở dưới có đủ dữ kiện, nhưng người nhận lúc nửa đêm
        # không phải người biết `proxy1` là gì — bắt họ tự suy ra là bắt họ hỏi lại.
        hint = diagnose(components)
        if hint:
            lines.append(hint)
        if started:
            lines.append(f"Hong tu khoang: {stamp(started)} "                 # vi-ok: email text
                         f"(lan do TOT cuoi cung; su co bat dau sau moc nay)")  # vi-ok: email text
        lines += [
            "",
            "Kiem nhanh:",                                              # vi-ok: email text
            "  docker compose --profile gateway ps",
            "  docker compose --profile gateway logs --tail 50 gateway-lb",
            "",
        ]
    if new == OK and started:
        lines += [
            f"Su co bat dau: {stamp(started)}",                     # vi-ok: email text
            f"Su co ket thuc: {stamp(now)}",                        # vi-ok: email text
            f"Keo dai: {human_duration((now - started).total_seconds())}",  # vi-ok: email text
            f"Moc bat dau la lan do TOT cuoi cung, nen su co that bat dau SAU moc nay, "
            f"trong vong mot nhip ({every} giay). Khoang nay rong hon that mot chut - "
            f"co y, de tra log agent khong bo sot.",                # vi-ok: email text
            "",
            "So luot agent da di THANG toi nha cung cap trong khoang nay khong nam o day.",  # vi-ok: email text
            "Tra trong log cua agent, tim theo dau [FALLBACK].",     # vi-ok: email text
            "",
        ]
    if new == BLIND:
        lines += [
            "KHONG doc duoc trang thai tu gateway-status.",          # vi-ok: email text
            "Cac dich HTTP van tra loi, nen DAY KHONG PHAI su co Gateway.",  # vi-ok: email text
            f"Ly do: {status_error}",                                # vi-ok: email text
            "",
        ]
    if new == DEGRADED:
        lines += [
            "Gateway VAN DANG PHUC VU, nhung da mat mot phan nang luc xu ly.",  # vi-ok: email text
            "",
        ]

    lines.append("Ket qua do tung dich:")                           # vi-ok: email text
    for name, reason in sorted(http.items()):
        lines.append(f"  {name:<10} {'DAT' if not reason else 'HONG  ' + reason}")
    if status:
        lines.append(f"  api/status {status}")
    elif status_error:
        lines.append(f"  api/status HONG  {status_error}")
    for component in components:
        if isinstance(component, dict):
            lines.append(f"      {str(component.get('id')):<8}"
                         f"{str(component.get('status')):<13}"
                         f"{str(component.get('detail'))[:50]}")
    lines += ["", f"-- gateway-watch [{watch_name}]"]
    return "\n".join(lines)


# --------------------------------------------------------------------------- vòng lặp


def tick(cfg: dict, state: dict, args) -> dict:
    """Một nhịp: dò, so với lần trước, gửi thư nếu trạng thái đổi."""
    now = datetime.now(timezone.utc)
    http = probe_http(cfg["targets"], cfg["expect"], cfg["timeout"])

    if args.fake_status_down or not cfg["status_url"]:
        status, components, status_error = "", [], (
            "forced by --fake-status-down" if args.fake_status_down else "")
    else:
        status, components, status_error = probe_status(
            cfg["status_url"], cfg["status_host"], cfg["timeout"])

    observed = args.fake_state or decide(http, status, status_error,
                                         bool(cfg["status_url"]))
    current = state.get("state", OK)
    LOG.info("probe -> %s (current %s)%s", observed, current,
             "" if not status_error else f" [status: {status_error}]")

    state["ticks"] = state.get("ticks", 0) + 1
    if observed != OK:
        state["bad_ticks"] = state.get("bad_ticks", 0) + 1
    else:
        # Mốc "tốt cuối cùng". Thư sự cố lấy mốc này làm lúc bắt đầu — xem `commit()`.
        state["last_ok"] = now.isoformat()

    if observed == current:
        state["pending"], state["pending_count"] = "", 0
    elif observed == OK:
        # Phục hồi tính ngay: một nhịp tốt là đủ. Chờ thêm chỉ làm thư "đã khoẻ lại" tới muộn.
        commit(cfg, state, observed, now, http, status, components, status_error, args)
    else:
        # Đi xuống thì phải xác nhận: một nhịp trượt lẻ không phải sự cố, và thư báo nhầm làm
        # người nhận tắt thông báo.
        state["pending_count"] = (state.get("pending_count", 0) + 1
                                  if state.get("pending") == observed else 1)
        state["pending"] = observed
        if state["pending_count"] >= cfg["fails_before"]:
            commit(cfg, state, observed, now, http, status, components, status_error, args)

    heartbeat(cfg, state, now, args)
    return state


def commit(cfg: dict, state: dict, new: str, now: datetime, http: dict[str, str],
           status: str, components: list[dict], status_error: str, args) -> None:
    old = state.get("state", OK)
    # `since` trống nghĩa là sự cố VỪA bắt đầu — lúc ấy mốc nằm ở `last_ok`. Thiếu dòng này thì thư
    # `DOWN` không nói được hỏng từ bao giờ, mà thư `OK` thì mãi sau mới tới.
    body = build_body(cfg["name"], new, old, now,
                      state.get("since") or state.get("last_ok", ""),
                      http, status, components, status_error, cfg["every"])
    send_mail(f"[{cfg['name']}] {SEVERITY.get(new, '?')} - "
              f"{SUBJECT.get(new, new)}", body, args.dry_run)
    state["state"] = new
    if new == OK:
        state["since"] = ""
    elif old == OK:
        # Mốc bắt đầu là lần dò TỐT cuối cùng, KHÔNG phải nhịp dò làm đủ hai lần hỏng. Lấy nhịp
        # ấy thì khoảng thời gian trong thư hụt mất cả quãng chờ — đo 18/09/2026: sự cố thật
        # 3 phút 31 giây, thư ghi 1 phút 31 giây, mốc bắt đầu muộn 144 giây. Và đúng quãng hụt ấy
        # là lúc agent
        # đi đường thẳng nhiều nhất, tức thứ người ta cần tra nhất (D8) lại rơi ngoài khoảng.
        # Thà rộng hơn thật một nhịp còn hơn hẹp hơn: khoảng rộng chỉ tốn công đọc, khoảng hẹp
        # thì mất số liệu.
        state["since"] = state.get("last_ok") or now.isoformat()
    # Đi xuống sâu hơn (degraded -> unavailable) thì GIỮ mốc cũ: vẫn là một sự cố, không phải hai.
    state["pending"], state["pending_count"] = "", 0
    LOG.warning("State changed: %s -> %s", old, new)


def heartbeat(cfg: dict, state: dict, now: datetime, args) -> None:
    """Một thư mỗi ngày, kể cả khi không có sự cố.

    Sau khi việc báo động rời khỏi agent, đây là nguồn báo động DUY NHẤT. Nó hỏng theo kiểu im
    lặng, mà im lặng lại trùng khít với tín hiệu "mọi thứ bình thường". Vắng thư nhịp tim LÀ một
    tín hiệu, và tài liệu vận hành phải nói điều đó.
    """
    local = now.astimezone(VN)
    today = local.date().isoformat()
    if local.hour < cfg["heartbeat_hour"] or state.get("heartbeat_date") == today:
        return
    ticks, bad = state.get("ticks", 0), state.get("bad_ticks", 0)
    send_mail(
        f"[{cfg['name']}] nhip tim - {today}",                       # vi-ok: email text
        "\n".join([
            f"Cho canh con song. {stamp(now)}",                      # vi-ok: email text
            f"Trang thai hien tai: {state.get('state', OK)}",        # vi-ok: email text
            f"Da do: {ticks} nhip, trong do {bad} nhip hong.",       # vi-ok: email text
            "",
            "Khong nhan duoc thu nay vao ngay hom sau nghia la CHO CANH DA CHET.",  # vi-ok: email text
            "",
            f"-- gateway-watch [{cfg['name']}]",
        ]),
        args.dry_run)
    state["heartbeat_date"] = today
    state["ticks"], state["bad_ticks"] = 0, 0


def build_config(args) -> dict:
    targets = parse_pairs(env("WATCH_HTTP"))
    cfg = {
        "name": env("WATCH_NAME", "watch"),
        "every": args.every or int(env("WATCH_EVERY_SECONDS", "60")),
        # PHẢI lớn hơn hạn kết nối của chính Gateway, nếu không chỗ canh bỏ cuộc đúng lúc nginx
        # đang tự chuyển sang instance còn sống. `nginx.conf` khai `proxy_connect_timeout 10s` và
        # `proxy_next_upstream_tries 2`, tức một request có thể mất tới 20 giây mới ra kết quả
        # đúng. Đo 17/09: để 10 giây thì một instance chết bị báo thành `unavailable` thay vì
        # `degraded` — sai mức độ, và sinh hai thư cho một sự cố.
        "timeout": float(env("WATCH_TIMEOUT_SECONDS", "25")),
        "fails_before": max(1, int(env("WATCH_FAILS_BEFORE", "2"))),
        # `off` tắt hẳn thư nhịp tim. 99 vì `local.hour` không bao giờ tới đó, nên phép so
        # trong `heartbeat()` luôn trả về sớm — tắt mà không thêm một nhánh `if` nào.
        # Tắt là MẤT lớp phủ "chỗ canh chết lặng lẽ": xem D7, và mục 3 tài liệu vận hành.
        "heartbeat_hour": 99 if env("WATCH_HEARTBEAT_HOUR", "8").lower() in (
            "off", "no", "false") else int(env("WATCH_HEARTBEAT_HOUR", "8")),
        "targets": targets,
        "expect": parse_pairs(env("WATCH_EXPECT")),
        "status_url": env("WATCH_STATUS_URL"),
        "status_host": env("WATCH_STATUS_HOST", "localhost"),
        "state_file": Path(env("WATCH_STATE_FILE", "/var/watch/state.json")),
    }
    if not targets and not cfg["status_url"]:
        LOG.error("Nothing to probe: both WATCH_HTTP and WATCH_STATUS_URL are empty")
        raise SystemExit(2)
    LOG.info("Watch %r: %d HTTP target(s)%s, every %ds, timeout %.0fs",
             cfg["name"], len(targets),
             ", plus api/status" if cfg["status_url"] else " (no api/status)",
             cfg["every"], cfg["timeout"])
    return cfg


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--every", type=int, default=0,
                        help="Seconds between probes; 0 = read WATCH_EVERY_SECONDS")
    parser.add_argument("--once", action="store_true",
                        help="Run a single probe and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the mail instead of sending it")
    parser.add_argument("--fake-state", choices=[OK, DEGRADED, DOWN, BLIND],
                        help="Force the observed state; for testing the mail path")
    parser.add_argument("--fake-status-down", action="store_true",
                        help="Pretend api/status cannot be read")
    args = parser.parse_args()

    logging.basicConfig(
        level=env("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s")

    cfg = build_config(args)
    state = load_state(cfg["state_file"])

    while True:
        # Dò TRƯỚC, ngủ SAU: nhịp đầu tiên chạy ngay lúc container lên, nên phép kiểm lúc khởi
        # động có sẵn mà không cần một tiến trình riêng.
        try:
            state = tick(cfg, state, args)
        except Exception as exc:                                    # noqa: BLE001
            # Một nhịp hỏng MUST NOT giết vòng lặp: chỗ canh chết lặng lẽ là chế độ hỏng tệ nhất,
            # vì im lặng trông y hệt "mọi thứ bình thường".
            LOG.error("Tick failed (%s: %s); continuing", type(exc).__name__, exc)
        save_state(cfg["state_file"], state)
        if args.once:
            return 0
        time.sleep(cfg["every"])


if __name__ == "__main__":
    raise SystemExit(main())
