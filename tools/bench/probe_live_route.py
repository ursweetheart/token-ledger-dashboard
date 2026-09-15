"""Goi THAT qua tuyen that de xem HAN MUC NAO can truoc: `rpm: 60` cua LiteLLM
hay quota cua Google.

KHAC HAN locustfile.py o thu muc nay:
  - locustfile.py  -> cong 4003, mock, khong ton tien, chay bao lau cung duoc
  - file nay       -> cong 4000, GOI GOOGLE THAT, ton tien, ghi vao SO THAT

Vi vay so luot bi CHOT CUNG bang mot hang so, khong phai bang thoi luong. Locust
chay theo `--run-time` nen mot lan go nham don vi la ban thua vai nghin luot ra
ngoai that. O day muon ban them thi phai sua so, tuc phai co y.

Chay:
    set LITELLM_MASTER_KEY=sk-...
    python tools/bench/goi_thu_tuyen_that.py

DOC KET QUA:
  - Neu thay 429 kem chu "rate limit" tu LiteLLM  -> `rpm: 60` can truoc.
    Nang con so do trong config.gateway.yaml se co tac dung.
  - Neu thay 429/RESOURCE_EXHAUSTED tu Google      -> quota Google can truoc.
    Nang `rpm: 60` VO ICH, phai xin quota hoac doi sang Vertex.
  - Neu 100/100 dat va thoi gian ~ 100s            -> `rpm: 60` dang tiet che
    (60/phut), khong ai bi tu choi, chi bi lam cho cham lai.
  - Neu 100/100 dat va thoi gian vai giay          -> KHONG han muc nao can ca.

DA DO 07/09/2026: quota Google can truoc.
    quotaId GenerateRequestsPerMinutePerProjectPerModel-FreeTier, limit 15.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

# CHOT CUNG bang hang so, khong bang thoi luong. Doi qua bien moi truong thi van
# phai go ra mot con so cu the - khong co duong nao "chay them ti nua" trong vo y.
REQUEST_COUNT = int(os.environ.get("REQUEST_COUNT", "100"))
CONCURRENCY = int(os.environ.get("CONCURRENCY", "10"))
BASE_URL = "http://127.0.0.1:4000"
MODEL = os.environ.get("TEST_MODEL", "gemini-flash-lite")   # tuyen re nhat dang co khoa


def send_one(index: int, key: str) -> dict:
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": "tra loi dung mot tu: ok"}],
        # Chan chi phi o dau ra. Dau vao da ngan san.
        "max_tokens": 5,
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=60.0) as response:
            response.read()
            return {"index": index, "status": response.status,
                    "seconds": time.perf_counter() - started, "error": ""}
    except urllib.error.HTTPError as exc:
        # PHAI doc than cua loi: ma 429 khong noi duoc no den tu LiteLLM hay tu
        # Google, chinh cau chu ben trong moi noi. Do la ca muc dich bai nay.
        error_body = exc.read().decode("utf-8", "replace")[:300].replace("\n", " ")
        return {"index": index, "status": exc.code,
                "seconds": time.perf_counter() - started, "error": error_body}
    except Exception as exc:  # loi mang, timeout...
        return {"index": index, "status": -1,
                "seconds": time.perf_counter() - started,
                "error": f"{type(exc).__name__}: {exc}"[:300]}


def main() -> None:
    key = os.environ.get("LITELLM_MASTER_KEY", "").strip()
    if not key:
        raise SystemExit("Thieu LITELLM_MASTER_KEY.")

    print(f"Ban {REQUEST_COUNT} luot THAT toi {BASE_URL} model={MODEL}, "
          f"song song {CONCURRENCY}")
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        results = list(pool.map(lambda i: send_one(i, key), range(REQUEST_COUNT)))
    total_seconds = time.perf_counter() - started

    by_status = Counter(item["status"] for item in results)
    print(f"\nTong thoi gian: {total_seconds:.1f}s  ->  "
          f"{REQUEST_COUNT / total_seconds:.2f} luot/giay")
    print("Ma tra ve:")
    for status, count in sorted(by_status.items()):
        print(f"   {status}: {count}")

    latencies = sorted(item["seconds"] for item in results if item["status"] == 200)
    if latencies:
        print(f"Do tre luot dat: p50 {latencies[len(latencies)//2]:.2f}s  "
              f"p95 {latencies[int(len(latencies)*0.95)-1]:.2f}s  max {latencies[-1]:.2f}s")

    failures = [item for item in results if item["status"] != 200]
    if failures:
        print(f"\n{len(failures)} luot khong phai 200. Ba loi dau, NGUYEN VAN:")
        for item in failures[:3]:
            print(f"   [{item['status']}] {item['error']}")
    else:
        print("\nKhong luot nao bi tu choi.")


if __name__ == "__main__":
    main()
