"""Ralli form OCR through the isolated LB/two-Proxy mock stack."""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from types import SimpleNamespace

from PIL import Image

SMOKE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SMOKE_ROOT))
import run as smoke

os.environ.update(
    LLM_BACKEND="gateway",
    LLM_MODE="gateway",
    GATEWAY_FALLBACK_ENABLED="false",
    GEMINI_API="",
    GEMINI_API_KEY_1="",
)
sys.path.insert(0, "D:/rangdong-chatbot")

from src.core import gemini_client, token_tracker
from src.core.llm_provider import GatewayConfig, GatewayProvider, GatewayTransportError
from src.core.token_logger import get_usage_context, token_usage_context
from src.services.assistant.form_service import DAMFormValidationService

BASE = "http://127.0.0.1:4101"
LB = "tla-gateway-smoke-gateway-lb-1"
SECOND = "tla-gateway-smoke-gateway2-1"
DB = "tla-gateway-smoke-db-1"
ROOT = SMOKE_ROOT
ARTIFACTS = ROOT / "artifacts" / "current"


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise RuntimeError("docker command failed: " + " ".join(args[:3]))
    return result.stdout


def http(path: str, key: str | None = None, payload: dict | None = None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    request = urllib.request.Request(
        BASE + path,
        headers=headers,
        data=None if payload is None else json.dumps(payload).encode(),
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw.startswith("{") else raw
    except urllib.error.HTTPError as exc:
        return exc.code, None


async def ready() -> None:
    for _ in range(60):
        try:
            if http("/health/readiness")[0] == 200:
                return
        except Exception:
            pass
        await asyncio.sleep(1)
    raise AssertionError("LB readiness timeout")


def synthetic_image() -> bytes:
    image = Image.new("RGB", (600, 800), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


async def main() -> None:
    run_id = "ralli-ocr-" + secrets.token_hex(6)
    image = synthetic_image()
    report = {
        "run_id": run_id,
        "result": "RUNNING",
        "scope": "actual Ralli DAM form _extract -> nginx LB -> two mock LiteLLM Proxies -> isolated SpendLogs",
        "fixture": {"mime_type": "image/png", "sha256": hashlib.sha256(image).hexdigest(), "synthetic": True},
        "limitations": [
            "mock upstream, not Google",
            "application usage rows captured in memory",
            "not authenticated multipart route in this run; covered separately by ASGI test",
            "no MongoDB/Qdrant persistence or ETL/dashboard",
        ],
        "calls": [],
        "stages": [],
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    destination = ARTIFACTS / f"{run_id}.json"
    master = smoke.state()["SMOKE_MASTER_KEY"]
    key = None
    provider = None
    stopped_proxy = False
    stopped_lb = False
    original_provider = gemini_client._gateway_provider
    original_direct = gemini_client._client
    original_db = token_tracker._sync_db

    def save() -> None:
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")

    rows: list[dict] = []
    token_tracker._sync_db = SimpleNamespace(
        token_budget=SimpleNamespace(find_one=lambda *args, **kwargs: None),
        token_usage=SimpleNamespace(insert_one=lambda row: rows.append(row)),
    )
    gemini_client._client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **kwargs: (_ for _ in ()).throw(
                AssertionError("direct provider forbidden")
            )
        )
    )

    def configure(timeout: float = 10) -> None:
        nonlocal provider
        if provider is not None:
            provider.close()
        provider = GatewayProvider(GatewayConfig.from_mapping({
            "backend": "gateway",
            "base_url": BASE,
            "virtual_key": key,
            "model_aliases": {name: "ralli-ocr-mock" for name in ("text", "json", "structured", "vision")},
            "timeout": timeout,
            "agent_code": "ralli",
        }))
        gemini_client._gateway_provider = provider

    async def call(stage: str, index: int) -> None:
        user = f"{run_id}.{stage}.user-{index}"
        before = len(rows)
        with token_usage_context(
            user_id=f"synthetic-{index}",
            username=user,
            company_id="company-test",
            unit_id="unit-test",
            session_id=f"{stage}-{index}",
            function_name=stage,
        ):
            result = await DAMFormValidationService()._extract(image, "image/png")
        assert result is not None
        assert result.text == "gateway-ralli-ocr-ok"
        assert result.is_dam_rooftop_survey is True
        assert len(rows) == before + 1
        row = rows[-1]
        assert row["username"] == user and row["route"] == "gateway"
        report["calls"].append({
            "user": user,
            "stage": stage,
            "response_id": row["provider_response_id"],
            "prompt_tokens": row["prompt_tokens"],
            "completion_tokens": row["completion_tokens"],
            "total_tokens": row["total_tokens"],
        })
        report["stages"].append({"name": stage, "user": user, "images": 1})
        assert get_usage_context() is None

    try:
        await ready()
        status, created = http("/key/generate", master, {
            "models": ["ralli-ocr-mock"],
            "duration": "1h",
            "key_alias": run_id,
            "metadata": {"tags": ["ralli"]},
            "max_budget": 1,
        })
        assert status == 200 and created.get("key")
        key = created["key"]
        status, info = http("/key/info?key=" + urllib.parse.quote(key, safe=""), master)
        assert status == 200
        assert info["info"]["metadata"]["tags"] == ["ralli"]
        assert info["info"]["models"] == ["ralli-ocr-mock"]
        configure()

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
        await call("proxy_recovery", 4)

        calls_before_outage = len(report["calls"])
        rows_before_outage = len(rows)
        docker("stop", "--time", "2", LB)
        stopped_lb = True
        configure(timeout=3)
        try:
            await call("lb_down", 5)
            raise AssertionError("LB outage accepted Ralli OCR request")
        except GatewayTransportError as exc:
            assert len(report["calls"]) == calls_before_outage
            assert len(rows) == rows_before_outage
            report["lb_outage"] = {
                "result": "fail_closed",
                "error_type": type(exc).__name__,
                "direct_fallback": False,
                "local_ocr_fallback": False,
                "usage_rows_created": 0,
            }
        docker("start", LB)
        stopped_lb = False
        await ready()
        configure()
        await call("lb_recovery", 6)

        ids = {call_row["response_id"] for call_row in report["calls"]}
        sql = f'''SELECT COALESCE(json_agg(t), '[]'::json) FROM (SELECT request_id,end_user,prompt_tokens,completion_tokens,total_tokens,request_tags,model,status FROM "LiteLLM_SpendLogs" WHERE end_user LIKE '{run_id}%') t;'''
        deadline = time.monotonic() + 120
        while True:
            spend_logs = json.loads(docker(
                "exec", DB, "psql", "-U", "smoke", "-d", "litellm_smoke", "-tAc", sql
            ))
            if ids <= {row["request_id"] for row in spend_logs} or time.monotonic() >= deadline:
                break
            await asyncio.sleep(2)
        assert len(spend_logs) == len(report["calls"]) == 5
        by_id = {row["request_id"]: row for row in spend_logs}
        for call_row in report["calls"]:
            spend = by_id[call_row["response_id"]]
            assert spend["end_user"] == call_row["user"]
            assert all(
                spend[field] == call_row[field]
                for field in ("prompt_tokens", "completion_tokens", "total_tokens")
            )
            assert "ralli" in spend["request_tags"]

        trace = [
            json.loads(line)
            for line in docker("exec", LB, "cat", "/var/log/nginx/attribution.jsonl").splitlines()
        ]
        trace = [
            row for row in trace
            if row.get("user", "").startswith(run_id)
            and row.get("path") == "/v1/chat/completions"
        ]
        successful_trace = [row for row in trace if row["status"] == 200]
        assert len(successful_trace) == 5
        upstreams = sorted({row["upstream"].split(", ")[-1] for row in successful_trace})
        assert len(upstreams) == 2
        report.update(
            result="PASS",
            spend_logs=spend_logs,
            lb_trace=trace,
            upstreams=upstreams,
            total_requests=5,
            total_tokens=sum(row["total_tokens"] for row in report["calls"]),
        )
    except Exception as exc:
        report.update(result="FAIL", error_type=type(exc).__name__)
        raise
    finally:
        if stopped_proxy:
            docker("start", SECOND)
        if stopped_lb:
            docker("start", LB)
        if provider is not None:
            provider.close()
        gemini_client._gateway_provider = original_provider
        gemini_client._client = original_direct
        token_tracker._sync_db = original_db
        if key:
            try:
                status, _ = http("/key/delete", master, {"keys": [key]})
                read_status, _ = http(
                    "/key/info?key=" + urllib.parse.quote(key, safe=""), master
                )
                report["key_cleanup"] = {
                    "delete_status": status,
                    "readback_status": read_status,
                }
                if status != 200 or read_status != 404:
                    report["result"] = "DEGRADED"
            except Exception:
                report["key_cleanup"] = "cleanup failed; key expires after 1h"
                report["result"] = "DEGRADED"
        save()
        print(json.dumps({
            name: report[name]
            for name in (
                "result", "run_id", "stages", "lb_outage", "upstreams", "key_cleanup"
            )
            if name in report
        }, indent=2))
        print("Evidence:", destination)


if __name__ == "__main__":
    asyncio.run(main())
