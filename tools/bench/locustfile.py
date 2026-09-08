"""Do tai instance LiteLLM DUNG RIENG DE BENCH (cong 4003), khong phai ban that.

Chay:
    set LITELLM_MASTER_KEY=sk-...
    locust -f tools/bench/locustfile.py --host http://127.0.0.1:4003

BA DIEU KIEN AN TOAN, kiem lai truoc moi lan chay:
  1. `--host` phai la cong 4003 (instance bench), KHONG phai 4000 (gateway-lb
     that) va KHONG phai 4001/4002 (hai instance that).
  2. Instance 4003 dung `mock_response`, nen khong lan goi nao ra Google.
  3. No ghi vao database `litellm_bench`, khong phai `litellm`.

VI SAO KHONG LAY HTTP 200 LAM BANG CHUNG:
LiteLLM co the tra 200 kem mot than khong phai cau tra loi mong doi. Locust mac
dinh dem 200 la dat, nen mot bai do "10.000/10.000 thanh cong" van co the dang
do mot thu khac han. Moi lan goi o day deu doc than tra ve va doi dung chuoi
mock; sai chuoi thi dem la HONG, du HTTP la 200.
"""

import json
import os

from locust import HttpUser, between, task

# Phai khop `mock_response` trong docker/gateway/config.bench.yaml. Doi mot ben
# ma quen ben kia thi moi luot bi dem la hong - co y de lo ra ngay, khong im.
EXPECTED_MOCK_TEXT = os.environ.get("BENCH_MOCK_TEXT", "BENCH: cau tra loi gia")

# Phai khop `model_name` trong config.bench.yaml.
BENCH_MODEL = os.environ.get("BENCH_MODEL", "bench-mock")

# Dat bien nay de gui `mock_response` NGAY TRONG THAN request, thay vi dua vao
# cau hinh cua tuyen.
#
# CANH BAO da do 07/09/2026: tuyen THAT BO QUA `mock_response` trong than
# request - chi `mock_response` khai trong `litellm_params` cua cau hinh tuyen
# moi an. Nen dat bien nay roi ban vao cong 4000 VAN goi Google that: ton tien,
# an vao han muc free tier 15 rpm, va ghi vao so that. Giu bien nay cho cac
# tuyen co khai mock trong cau hinh.
MOCK_IN_BODY = os.environ.get("BENCH_MOCK_IN_BODY", "").strip()


class GatewayCaller(HttpUser):
    # Khong nghi giua hai luot: dang do tran tai, khong mo phong nguoi dung that.
    wait_time = between(0, 0)

    def on_start(self) -> None:
        key = os.environ.get("LITELLM_MASTER_KEY", "").strip()
        if not key:
            raise RuntimeError(
                "Thieu LITELLM_MASTER_KEY. Bench se do duoc mot bai toan 401 "
                "thay vi do duong dan that - dung han con hon do nham."
            )
        self.client.headers.update({
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        })

    @task
    def chat_completion(self) -> None:
        body = {
            "model": BENCH_MODEL,
            "messages": [{"role": "user", "content": "do tai, khong phai cau hoi that"}],
        }
        if MOCK_IN_BODY:
            body["mock_response"] = MOCK_IN_BODY
        with self.client.post(
            "/v1/chat/completions",
            data=json.dumps(body),
            name="POST /v1/chat/completions [mock]",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}: {response.text[:200]}")
                return
            try:
                content = response.json()["choices"][0]["message"]["content"]
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                response.failure(
                    f"Than tra ve khong dung hinh dang: {type(exc).__name__} "
                    f"{response.text[:200]}"
                )
                return
            if EXPECTED_MOCK_TEXT not in content:
                # Day la truong hop dang lo nhat: 200 nhung KHONG phai mock.
                # Neu thay dong nay, dung bench lai va kiem xem co phai request
                # da di ra Google that khong.
                response.failure(f"200 nhung KHONG phai cau tra loi mock: {content[:120]!r}")
                return
            response.success()
