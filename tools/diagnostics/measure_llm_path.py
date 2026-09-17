"""Đo một đường gọi LLM, từng lượt một, rồi ghi lại đủ để tính lại về sau.

    # xem trước, không gọi mạng, không tốn gì
    python tools/diagnostics/measure_llm_path.py --route gateway --key-env CRM_VIRTUAL_KEY --dry-run

    # hai lượt để bắt lỗi công cụ TRƯỚC khi tin số nó in ra (ô 1.5)
    python tools/diagnostics/measure_llm_path.py --route gateway --key-env CRM_VIRTUAL_KEY \
        --model gemini-2.5-flash --calls 2 --agent crm-feedback

    # đường gọi thẳng nhà cung cấp, để so với đường qua Gateway
    python tools/diagnostics/measure_llm_path.py --route direct --key-env KEY_CRM_FEEDBACK \
        --model gemini-2.5-flash --calls 2 --agent crm-feedback


VÌ SAO FILE NÀY TỒN TẠI
-----------------------
Change `prove-the-crm-path-survives-refusal-and-outage` phải trả lời ba câu:
Gateway từ chối thì client lùi lịch nhánh nào, mất Gateway giữa chừng thì có mất
dòng không, và Gateway làm chậm thêm bao nhiêu. Cả ba đều cần **gọi thật nhiều
lượt và đo từng lượt**.

Chạy thẳng pipeline của agent để lấy mấy con số đó là sai, và sai theo cách đắt:
pipeline của CRM **tải file từ SharePoint, ghi ngược lên SharePoint, rồi gửi
email** (`src/pipeline.py` dòng 350, 743, 849). Ba việc đó không liên quan gì tới
câu hỏi, mà đều chạm vào hệ thống thật của công ty. File này tách phần cần đo ra
khỏi phần không cần đo.

KHÔNG NHÉT MỘT AGENT NÀO VÀO CODE (ô 1.2)
------------------------------------------
Không có chữ "crm" nào trong phần logic. Agent, model, khoá, số lượt, đường đi —
tất cả là tham số. CRM chỉ là agent ĐẦU TIÊN được đo bằng nó, không phải agent
duy nhất. Đo agent khác thì đổi tham số, không đổi file.

KHOÁ TRUYỀN BẰNG TÊN BIẾN, KHÔNG TRUYỀN BẰNG GIÁ TRỊ
-----------------------------------------------------
`--key-env` nhận TÊN của biến môi trường, không nhận khoá. Truyền thẳng khoá
vào dòng lệnh thì nó nằm lại ba chỗ không xoá được: lịch sử shell, danh sách tiến
trình (`ps` của mọi user trên máy), và nhật ký nếu ai đó bật log lệnh.
File này cũng KHÔNG BAO GIỜ in khoá ra, kể cả khi báo lỗi — chỉ in tên biến và độ
dài.

NHỮNG VIỆC FILE NÀY KHÔNG LÀM (ô 1.4)
--------------------------------------
Không tải và không ghi SharePoint. Không gửi email. Không ghi Excel. Không đụng
vào database. Nó chỉ gọi HTTP rồi ghi một file JSONL. Cố ý không `import` bất kỳ
module nào của agent, để một lần sửa nhầm bên đó không kéo theo tác dụng phụ ở
đây.

VÌ SAO DÙNG HTTP TRẦN, KHÔNG DÙNG SDK
--------------------------------------
Hai lý do. Một là SDK của Google **không có** trong môi trường chạy dashboard,
nên thêm nó vào chỉ để đo là thêm một thứ phải bảo trì. Hai là SDK **giấu mất**
đúng thứ cần đo: mã HTTP thật, header, và `request_id`. Gọi trần thì cái gì
Google trả về là cái đó vào sổ.

GHI RA JSONL, MỖI LƯỢT MỘT DÒNG (ô 1.3)
----------------------------------------
Mỗi dòng đủ để tính lại mọi con số sau này mà không phải gọi lại: mốc bắt đầu,
mã trả về, độ trễ, token vào/ra/suy nghĩ/tổng, `request_id`, và cả nội dung trả
về. Có nội dung mới so được kết quả hai đường trên cùng đầu vào — đó là việc 7.6
của change trước, và nếu chỉ ghi con số thì phải gọi lại lần nữa mới so được.

Từ 15/09/2026 các khoá JSONL là tiếng Anh (`started_utc`, `latency_ms`, `status`,
`tokens_in`...). Sổ đo cũ `var/do-duong-llm-20260910-112104.jsonl` giữ khoá tiếng
Việt; không code nào đọc nó.

TOKEN SUY NGHĨ ĐƯỢC GHI RIÊNG
------------------------------
Đo 10/09: `gemini-2.5-flash` trả `vào 13 · ra 10 · tổng 53`. Chênh 30 token là
`thoughtsTokenCount`, một NGĂN THỨ BA nằm ngoài vào và ra. Cộng vào/ra rồi coi là
tổng sẽ hụt đúng phần đó. Nên ở đây bốn con số được ghi TÁCH NHAU, và phần chênh
không giải thích được cũng được ghi ra thay vì làm tròn cho khớp.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Địa chỉ Vertex express. Trùng với `api_base` của các tuyến gemini trong
# `docker/gateway/config.gateway.yaml`, nên đường "trực tiếp" và đường "gateway"
# cuối cùng gõ vào CÙNG MỘT CỬA của Google. Khác nhau chỉ ở chặng ở giữa, và đó
# đúng là thứ cần đo.
VERTEX_BASE = "https://aiplatform.googleapis.com/v1/publishers/google/models"

# Câu nhắc mặc định. Cố tình tầm thường và ngắn: file này đo ĐƯỜNG ĐI, không đo
# chất lượng phân loại. Câu càng ngắn thì token càng ít và tiền càng nhỏ.
DEFAULT_PROMPT = 'Trả về đúng JSON này, không thêm gì: {"trang_thai":"ok"}'  # vi-ok: prompt sent to the model, kept so runs stay comparable
DEFAULT_SYSTEM = "Bạn là bộ phân loại. Chỉ trả về JSON hợp lệ."  # vi-ok: prompt sent to the model, kept so runs stay comparable


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def read_key(env_name: str) -> str:
    """Đọc khoá từ biến môi trường. Không in giá trị ra, kể cả khi hỏng."""
    value = os.environ.get(env_name, "")
    if not value:
        raise SystemExit(
            "Missing key: environment variable `%s` is empty or unset.\n"
            "Set it and run again. Do NOT pass the key on the command line." % env_name
        )
    return value


def request_body(route: str, model: str, system: str, prompt: str,
                 temperature: float, max_output_tokens: int, json_mode: bool) -> dict:
    """Dựng thân yêu cầu cho từng đường.

    Hai đường có hình dạng khác nhau, và đó là chuyện có thật chứ không phải
    tuỳ tiện: Gateway nói tiếng OpenAI, còn Vertex nói tiếng Google. Chỗ dễ sai
    nhất là prompt hệ thống — OpenAI đặt nó thành một `message`, còn Google đặt
    nó ra NGOÀI `contents`. Nhét nhầm vào `contents` thì cấu trúc prompt khác đi
    mà kết quả vẫn ra JSON, nên nhìn không biết.
    """
    if route == "gateway":
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        return body

    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    return body


def parse_result(route: str, body: dict) -> dict:
    """Bóc bốn con số token và nội dung ra khỏi hình dạng riêng của từng đường."""
    if route == "gateway":
        usage = body.get("usage") or {}
        choice = (body.get("choices") or [{}])[0]
        content = ((choice.get("message") or {}).get("content")) or ""
        # LiteLLM chuyển tiếp token suy nghĩ trong `completion_tokens_details`
        # khi nhà cung cấp có báo. Không có thì để None, KHÔNG để 0 — "không báo"
        # khác "báo là 0".
        details = usage.get("completion_tokens_details") or {}
        return {
            "content": content,
            "tokens_in": usage.get("prompt_tokens"),
            "tokens_out": usage.get("completion_tokens"),
            "tokens_thinking": details.get("reasoning_tokens"),
            "tokens_total": usage.get("total_tokens"),
            "request_id": body.get("id"),
        }

    usage = body.get("usageMetadata") or {}
    candidate = (body.get("candidates") or [{}])[0]
    parts = ((candidate.get("content") or {}).get("parts")) or []
    content = "".join(p.get("text", "") for p in parts)
    return {
        "content": content,
        "tokens_in": usage.get("promptTokenCount"),
        "tokens_out": usage.get("candidatesTokenCount"),
        "tokens_thinking": usage.get("thoughtsTokenCount"),
        "tokens_total": usage.get("totalTokenCount"),
        "request_id": body.get("responseId"),
    }


def call_once(route: str, model: str, key: str, base_url: str, user: str,
              body: dict, timeout: float) -> dict:
    """Gọi đúng một lượt. Mọi lỗi đều thành một dòng sổ, không ném ra ngoài.

    Một lượt hỏng cũng là một phép đo — nhất là ở change này, nơi câu hỏi chính
    là "bị từ chối thì chuyện gì xảy ra". Ném ngoại lệ ra ngoài sẽ làm mất đúng
    dòng đáng giá nhất.
    """
    if route == "gateway":
        url = base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "X-User": user,
        }
    else:
        # Khoá đi trong query string là do Google quy định cho express key.
        # Nó KHÔNG được ghi vào sổ đo ở dưới — xem `logged_url`.
        url = "%s/%s:generateContent?key=%s" % (VERTEX_BASE, model, key)
        headers = {"Content-Type": "application/json"}

    logged_url = url.split("?")[0] if route != "gateway" else url

    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    started = now_utc()
    clock = time.perf_counter()
    row = {"started_utc": started, "route": route, "model": model, "url": logged_url}

    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", "replace")
            row["latency_ms"] = round((time.perf_counter() - clock) * 1000, 1)
            row["status"] = resp.status
            # `x-request-id` của LiteLLM và `x-guploader-uploadid` của Google đều
            # là đường lần ngược khi phải hỏi nhà cung cấp về một lượt cụ thể.
            row["header_id"] = (resp.headers.get("x-request-id")
                                or resp.headers.get("x-litellm-call-id") or None)
            try:
                row.update(parse_result(route, json.loads(text)))
            except json.JSONDecodeError:
                row["error"] = "returned 200 but the body is not JSON"
                row["raw_body"] = text[:800]
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")
        row["latency_ms"] = round((time.perf_counter() - clock) * 1000, 1)
        row["status"] = e.code
        row["header_id"] = e.headers.get("x-request-id") if e.headers else None
        # Giữ NGUYÊN VĂN thân lỗi. Đây là chỗ phân biệt 429 của nhà cung cấp với
        # 429 do chính Gateway sinh ra, và hai cái đó dẫn tới hai kết luận khác
        # hẳn nhau ở mục 2 của change.
        row["error_body"] = text[:1200]
    except Exception as e:                                    # noqa: BLE001
        row["latency_ms"] = round((time.perf_counter() - clock) * 1000, 1)
        row["status"] = None
        row["error"] = type(e).__name__ + ": " + str(e)[:300]

    return row


def check_token_sum(row: dict) -> str | None:
    """Bốn con số token có khớp nhau không.

    vào + ra + suy nghĩ có bằng tổng không. Lệch thì GHI RA, không làm tròn cho
    khớp: phần lệch chính là ngăn token mà ta chưa biết tên.
    """
    t_in, t_out, t_think, total = (row.get("tokens_in"), row.get("tokens_out"),
                                   row.get("tokens_thinking"), row.get("tokens_total"))
    if t_in is None or t_out is None or total is None:
        return None
    added = t_in + t_out + (t_think or 0)
    if added == total:
        return None
    return "off by %+d tokens (in %s + out %s + thinking %s = %s, but total says %s)" % (
        total - added, t_in, t_out, t_think if t_think is not None else "not reported",
        added, total)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Measure one LLM call path, one call at a time. No SharePoint, "
                    "no email, no Excel, no database.",
        allow_abbrev=False)
    p.add_argument("--route", required=True, choices=["gateway", "direct"],
                   help="gateway = through the internal Gateway; direct = straight to the provider")
    p.add_argument("--key-env", required=True,
                   help="NAME of the environment variable holding the key. NOT the key itself")
    p.add_argument("--model", default="gemini-2.5-flash")
    p.add_argument("--agent", default="unknown",
                   help="Agent label, only written to the log. Does not change the call")
    p.add_argument("--calls", type=int, default=2)
    p.add_argument("--base-url", default="http://127.0.0.1:4000",
                   help="Only used with --route gateway")
    p.add_argument("--user", default="svc.do-duong-llm",  # vi-ok: X-User value already stored in the Gateway ledger
                   help="X-User header value, so the Gateway ledger can attribute the call")
    p.add_argument("--prompt", default=DEFAULT_PROMPT)
    p.add_argument("--system", default=DEFAULT_SYSTEM)
    p.add_argument("--prompts-file", type=Path,
                   help="Text file, one prompt per line. When given, --prompt is ignored")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--max-output-tokens", type=int, default=8192)
    p.add_argument("--no-json", action="store_true",
                   help="Turn JSON mode off, to measure the difference that setting alone makes")
    p.add_argument("--pause", type=float, default=0.0,
                   help="Seconds to wait between two calls")
    p.add_argument("--jitter", type=float, default=0.0,
                   help="Add a random 0..JITTER seconds, the way agents spread their calls")
    p.add_argument("--timeout", type=float, default=300.0)
    p.add_argument("--out", type=Path,
                   help="JSONL file to write. Default var/llm-path-<timestamp>.jsonl")
    p.add_argument("--dry-run", action="store_true",
                   help="Print what WOULD be sent and stop. No network call, no cost")
    a = p.parse_args()

    if a.calls < 1:
        raise SystemExit("--calls must be >= 1")

    prompts = [a.prompt]
    if a.prompts_file:
        prompts = [line.strip() for line in a.prompts_file.read_text(encoding="utf-8").splitlines()
                   if line.strip()]
        if not prompts:
            raise SystemExit("--prompts-file has no usable line")

    json_mode = not a.no_json
    sample = request_body(a.route, a.model, a.system, prompts[0],
                          a.temperature, a.max_output_tokens, json_mode)

    print("=" * 72)
    print("MEASURE AN LLM CALL PATH")
    print("=" * 72)
    print("  route        :", a.route, "" if a.route == "gateway" else "(straight to the provider)")
    print("  model        :", a.model)
    print("  agent (label):", a.agent)
    print("  calls        :", a.calls)
    print("  JSON mode    :", "ON" if json_mode else "OFF")
    print("  target       :", a.base_url if a.route == "gateway" else VERTEX_BASE)
    print("  key          : read from `%s`, NOT printed" % a.key_env)
    print("  prompts      :", len(prompts))
    print()
    print("Does NOT touch: SharePoint · email · Excel · database")
    print()

    if a.dry_run:
        print("--dry-run: this is the request body that WOULD be sent; no network call.")
        print(json.dumps(sample, indent=2, ensure_ascii=False))
        return 0

    key = read_key(a.key_env)

    out = a.out or (ROOT / "var" /
                    ("llm-path-%s.jsonl" % datetime.now().strftime("%Y%m%d-%H%M%S")))
    out.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    with out.open("w", encoding="utf-8") as f:
        for i in range(a.calls):
            prompt = prompts[i % len(prompts)]
            body = request_body(a.route, a.model, a.system, prompt,
                                a.temperature, a.max_output_tokens, json_mode)
            row = call_once(a.route, a.model, key, a.base_url, a.user, body, a.timeout)
            row["seq"] = i + 1
            row["agent"] = a.agent
            row["prompt"] = prompt
            mismatch = check_token_sum(row)
            if mismatch:
                row["token_warning"] = mismatch

            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()          # ghi ngay từng dòng: dừng giữa chừng vẫn còn sổ
            rows.append(row)

            status = row.get("status")
            print("  call %-3d %-5s %8.1f ms  in/out/think/total %s/%s/%s/%s  %s" % (
                i + 1, status if status is not None else "ERR", row.get("latency_ms", 0),
                row.get("tokens_in"), row.get("tokens_out"),
                row.get("tokens_thinking"), row.get("tokens_total"),
                (row.get("error") or "")[:40]))
            if mismatch:
                print("        ! " + mismatch)

            if i + 1 < a.calls and (a.pause or a.jitter):
                time.sleep(a.pause + random.random() * a.jitter)

    ok = [r for r in rows if r.get("status") == 200]
    latencies = sorted(r["latency_ms"] for r in ok) if ok else []
    print()
    print("-" * 72)
    print("  %d calls · %d succeeded · %d failed" % (len(rows), len(ok), len(rows) - len(ok)))
    if latencies:
        print("  median latency  : %.1f ms" % latencies[len(latencies) // 2])
        print("  min/max latency : %.1f / %.1f ms" % (latencies[0], latencies[-1]))
    total = sum(r.get("tokens_total") or 0 for r in ok)
    thinking = sum(r.get("tokens_thinking") or 0 for r in ok)
    print("  total tokens    : %d (of which thinking %d)" % (total, thinking))
    other_codes = sorted({str(r.get("status")) for r in rows if r.get("status") != 200})
    if other_codes:
        print("  non-200 codes   :", ", ".join(other_codes))
    print("  log             :", out)
    print("-" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
