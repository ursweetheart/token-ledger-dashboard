"""Do xem nginx co TIEP TUC gui luu luong vao instance dang OM khong.

Cau hoi: `config.gateway.yaml` dung nginx ban mo nguon, KHONG co health check chu
dong. No chi dem loi that. Nhung mot instance thieu bo nho KHONG tra loi - no tra
200 sau 24 giay. Vay nginx co nhan ra khong?

TAI SAO BAN VAO `/health/liveliness` CHU KHONG PHAI `/v1/chat/completions`:
Da do 07/09/2026 - `mock_response` dat trong THAN request bi tuyen that BO QUA
(cau hinh that khong khai no trong litellm_params). Nen ban chat/completions vao
cong 4000 la goi Google THAT: ton tien, an vao han muc free tier 15 rpm, va ghi
vao so that. `/health/liveliness` thi di qua upstream y het - chinh nginx.conf ghi
"Muon biet instance con song thi goi /health/liveliness (di qua upstream)" - nen
no do dung quyet dinh dinh tuyen ma khong phai tra dong nao.

Dem phan bo giua hai instance bang log, chay RIENG sau khi script nay xong:
    docker logs token-ledger-litellm-1 --since 30s | grep -c health/liveliness
    docker logs token-ledger-litellm-2 --since 30s | grep -c health/liveliness

Chay:
    python tools/bench/do_dinh_tuyen_khi_om.py <label>
`<label>` chi de in ra cho de doc, vi du "truoc" hoac "sau".
"""

from __future__ import annotations

import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

REQUEST_COUNT = int(os.environ.get("REQUEST_COUNT", "400"))
CONCURRENCY = int(os.environ.get("CONCURRENCY", "40"))
PROBE_URL = "http://127.0.0.1:4000/health/liveliness"


def send_one(_: int) -> tuple[int, float]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(PROBE_URL, timeout=30) as response:
            response.read()
            return response.status, time.perf_counter() - started
    except urllib.error.HTTPError as exc:
        return exc.code, time.perf_counter() - started
    except Exception:
        return -1, time.perf_counter() - started


def main() -> None:
    label = sys.argv[1] if len(sys.argv) > 1 else "(khong nhan)"
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        results = list(pool.map(send_one, range(REQUEST_COUNT)))
    total_seconds = time.perf_counter() - started

    latencies = sorted(seconds for status, seconds in results if status == 200)
    failures = [status for status, _ in results if status != 200]
    print(f"[{label}] {REQUEST_COUNT} luot / {total_seconds:.1f}s = "
          f"{REQUEST_COUNT/total_seconds:.1f} luot/giay")
    print(f"[{label}] dat {len(latencies)}  hong {len(failures)}")
    if latencies:
        print(f"[{label}] p50 {latencies[len(latencies)//2]*1000:.0f}ms  "
              f"p95 {latencies[int(len(latencies)*0.95)-1]*1000:.0f}ms  "
              f"max {latencies[-1]*1000:.0f}ms")


if __name__ == "__main__":
    main()
