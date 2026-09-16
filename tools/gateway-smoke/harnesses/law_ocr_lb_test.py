"""TLA-HĐ scanned-PDF OCR through the isolated LB/two-Proxy mock stack."""
import asyncio
import json
from pathlib import Path
import secrets
import sys
import time
import urllib.parse

import fitz

SMOKE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SMOKE_ROOT))
import run as smoke
from law_lb_test import BASE, LB, SECOND, docker, http, ready

sys.path.insert(0, "D:/law_insight/backend")
from app.config import Settings
from app.services import gemini_ocr, llm
from app.services.token_logger import build_token_usage_log, get_usage_context, token_usage_context

ROOT = SMOKE_ROOT
ARTIFACTS = ROOT / "artifacts" / "current"


def scanned_pdf(canary: str) -> bytes:
    source = fitz.open()
    page = source.new_page(width=600, height=800)
    page.insert_text((72, 100), canary, fontsize=18)
    png = page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes("png")
    source.close()
    result = fitz.open()
    page = result.new_page(width=600, height=800)
    page.insert_image(page.rect, stream=png)
    payload = result.tobytes()
    result.close()
    check = fitz.open(stream=payload, filetype="pdf")
    assert check[0].get_text().strip() == ""
    check.close()
    return payload


async def main():
    run_id = "law-ocr-" + secrets.token_hex(6)
    report = {
        "run_id": run_id,
        "result": "RUNNING",
        "scope": "actual TLA-HD scanned-PDF OCR helper -> nginx LB -> two mock LiteLLM Proxies -> isolated SpendLogs",
        "limitations": ["mock upstream, not Google", "application usage rows captured in memory", "no ETL/dashboard"],
        "calls": [],
        "stages": [],
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    destination = ARTIFACTS / f"{run_id}.json"
    master = smoke.state()["SMOKE_MASTER_KEY"]
    key = None
    stopped_proxy = False
    stopped_lb = False
    original_settings = llm.settings
    original_recorder = llm.record_model_call

    def save():
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")

    async def capture(**kwargs):
        context = get_usage_context()
        row = build_token_usage_log(context=context, **kwargs)
        report["calls"].append({
            "user": context.username,
            "stage": context.function_name,
            "response_id": row.call_id,
            "prompt_tokens": row.prompt_tokens,
            "completion_tokens": row.completion_tokens,
            "total_tokens": row.total_tokens,
        })
        return True

    async def call(stage: str, index: int):
        user = f"{run_id}.{stage}.user-{index}"
        canary = f"CANARY-{run_id}-{stage}-{index}"
        with token_usage_context(
            user_id=f"synthetic-{index}", username=user, company_id="company-test",
            unit_id="unit-test", session_id=f"{stage}-{index}", function_name=stage,
        ):
            markdown, pages = await gemini_ocr.ocr_pdf_with_gemini(scanned_pdf(canary), f"{stage}.pdf")
        assert pages == 1 and "gateway-smoke-ok" in markdown
        report["stages"].append({"name": stage, "user": user, "pages": pages})

    try:
        await ready()
        status, created = http("/key/generate", master, {
            "models": ["tla-hd-mock"], "duration": "1h", "key_alias": run_id,
            "metadata": {"tags": ["tla-hd"]}, "max_budget": 1,
        })
        assert status == 200 and created.get("key")
        key = created["key"]
        status, info = http("/key/info?key=" + urllib.parse.quote(key, safe=""), master)
        assert status == 200 and info["info"]["metadata"]["tags"] == ["tla-hd"]
        llm.settings = Settings(
            _env_file=None, llm_mode="gateway", gateway_base_url=BASE + "/v1",
            gateway_virtual_key=key, gateway_model="tla-hd-mock", gateway_timeout_seconds=10,
        )
        llm.record_model_call = capture

        await call("baseline", 1)
        await call("baseline", 2)

        docker("stop", "--time", "2", SECOND)
        stopped_proxy = True
        await call("one_proxy_down", 3)
        docker("start", SECOND)
        stopped_proxy = False
        for _ in range(120):
            if docker("inspect", SECOND, "--format", "{{.State.Health.Status}}").strip() == "healthy":
                break
            await asyncio.sleep(1)
        else:
            raise AssertionError("second Proxy did not recover")
        docker("exec", LB, "nginx", "-s", "reload")
        await ready()
        await call("recovery", 4)

        calls_before_outage = len(report["calls"])
        docker("stop", "--time", "2", LB)
        stopped_lb = True
        llm.settings.gateway_timeout_seconds = 3
        try:
            await call("lb_down", 5)
            raise AssertionError("LB outage accepted OCR request")
        except Exception as exc:
            assert len(report["calls"]) == calls_before_outage
            report["lb_outage"] = {
                "result": "fail_closed",
                "error_type": type(exc).__name__,
                "direct_fallback": False,
            }
        docker("start", LB)
        stopped_lb = False
        await ready()
        llm.settings.gateway_timeout_seconds = 10
        await call("lb_recovery", 6)

        ids = {call["response_id"] for call in report["calls"]}
        sql = f'''SELECT COALESCE(json_agg(t), '[]'::json) FROM (SELECT request_id,end_user,prompt_tokens,completion_tokens,total_tokens,request_tags,model,status FROM "LiteLLM_SpendLogs" WHERE end_user LIKE '{run_id}%') t;'''
        deadline = time.monotonic() + 120
        while True:
            rows = json.loads(docker("exec", "tla-gateway-smoke-db-1", "psql", "-U", "smoke", "-d", "litellm_smoke", "-tAc", sql))
            if ids <= {row["request_id"] for row in rows} or time.monotonic() >= deadline:
                break
            await asyncio.sleep(2)
        assert len(rows) == len(report["calls"]) == 5
        by_id = {row["request_id"]: row for row in rows}
        for call_row in report["calls"]:
            spend = by_id[call_row["response_id"]]
            assert spend["end_user"] == call_row["user"]
            assert all(spend[field] == call_row[field] for field in ("prompt_tokens", "completion_tokens", "total_tokens"))
            assert "tla-hd" in spend["request_tags"]

        trace = [json.loads(line) for line in docker("exec", LB, "cat", "/var/log/nginx/attribution.jsonl").splitlines()]
        trace = [row for row in trace if row.get("user", "").startswith(run_id) and row.get("path") == "/v1/chat/completions"]
        success = [row for row in trace if row["status"] == 200]
        assert len(success) == 5
        upstreams = sorted({row["upstream"].split(", ")[-1] for row in success})
        assert len(upstreams) == 2
        report.update(result="PASS", spend_logs=rows, lb_trace=trace, upstreams=upstreams,
                      total_requests=5, total_tokens=sum(row["total_tokens"] for row in report["calls"]))
    except Exception as exc:
        report.update(result="FAIL", error_type=type(exc).__name__)
        raise
    finally:
        if stopped_proxy:
            docker("start", SECOND)
        if stopped_lb:
            docker("start", LB)
        llm.settings = original_settings
        llm.record_model_call = original_recorder
        if key:
            try:
                status, _ = http("/key/delete", master, {"keys": [key]})
                read_status, _ = http("/key/info?key=" + urllib.parse.quote(key, safe=""), master)
                report["key_cleanup"] = {"delete_status": status, "readback_status": read_status}
                if status != 200 or read_status != 404:
                    report["result"] = "DEGRADED"
            except Exception:
                report["key_cleanup"] = "cleanup failed; key expires after 1h"
                report["result"] = "DEGRADED"
        save()
        print(json.dumps({key: report[key] for key in ("result", "run_id", "stages", "upstreams", "key_cleanup") if key in report}, indent=2))
        print("Evidence:", destination)


if __name__ == "__main__":
    asyncio.run(main())
