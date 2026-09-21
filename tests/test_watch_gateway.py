"""Phép kiểm cho `decide()` — hàm quyết định có gọi người dậy lúc nửa đêm hay không.

Chỉ kiểm hàm gộp, không kiểm phép dò: phép dò cần mạng, còn chỗ sai nguy hiểm thì nằm ở luật gộp.

Ca quan trọng nhất là `test_status_says_down_but_a_real_call_still_works`. Nó khoá lại một phép đo
ngày 17/09/2026: dừng `litellm-1` thì `/api/status` trả `unavailable` trong khi một lượt gọi thật
qua load balancer **vẫn xong**. Nguyên nhân là `tools/gateway-status/server.js` dò `route` với hạn
2,5 giây, thấp hơn hẳn cửa sổ `proxy_connect_timeout 10s` × `proxy_next_upstream_tries 2` của
nginx — nên phép dò của nó bỏ cuộc trong lúc nginx đang tự chuyển tuyến.

Tin `/api/status` ở ca đó là báo "chết hẳn" cho một sự cố mà agent vẫn gọi được.
"""
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import watch_gateway as watch  # noqa: E402

PASS = {"lb": ""}
FAIL = {"lb": "URLError: timed out"}


class DecideTests(unittest.TestCase):
    def decide(self, http, status, error="", has_status=True):
        return watch.decide(http, status, error, has_status)

    def test_everything_healthy(self):
        self.assertEqual(self.decide(PASS, watch.OK), watch.OK)

    def test_status_reports_a_dead_instance(self):
        self.assertEqual(self.decide(PASS, watch.DEGRADED), watch.DEGRADED)

    def test_status_says_down_but_a_real_call_still_works(self):
        # Đo 17/09/2026. MUST NOT là `unavailable`: agent vẫn gọi được.
        self.assertEqual(self.decide(PASS, watch.DOWN), watch.DEGRADED)

    def test_a_real_call_fails(self):
        # Chỉ có đúng một đường ra `unavailable`: lượt gọi thật qua LB cũng không xong.
        self.assertEqual(self.decide(FAIL, watch.OK), watch.DOWN)

    def test_both_agree_it_is_down(self):
        self.assertEqual(self.decide(FAIL, watch.DOWN), watch.DOWN)

    def test_status_unreadable_while_the_gateway_answers(self):
        # `gateway-status` mang `restart: unless-stopped` nên nó sẽ có lúc dựng lại. Coi việc đó là
        # sự cố Gateway thì mỗi lần dựng lại là một thư báo động giả.
        self.assertEqual(self.decide(PASS, "", "boom"), watch.BLIND)

    def test_status_unreadable_and_the_gateway_is_down(self):
        self.assertEqual(self.decide(FAIL, "", "boom"), watch.DOWN)

    def test_no_http_target_falls_back_to_status(self):
        # Bản chạy trên máy khác chỉ khai `WATCH_STATUS_URL`; lúc ấy không có trọng tài nào.
        self.assertEqual(self.decide({}, watch.DOWN), watch.DOWN)
        self.assertEqual(self.decide({}, watch.DEGRADED), watch.DEGRADED)

    def test_no_status_source_configured(self):
        self.assertEqual(self.decide(PASS, "", "", has_status=False), watch.OK)

    def test_unknown_status_string_is_not_treated_as_down(self):
        # Bản `gateway-status` sau này có thể thêm mức mới. Lượt gọi thật vẫn xong thì MUST NOT
        # nhảy thẳng sang "chết hẳn" chỉ vì gặp một chữ lạ.
        self.assertEqual(self.decide(PASS, "something-new"), watch.DEGRADED)


class ParsePairsTests(unittest.TestCase):
    def test_reads_name_and_url(self):
        self.assertEqual(
            watch.parse_pairs("lb=http://a:1/x public=https://b/y"),
            {"lb": "http://a:1/x", "public": "https://b/y"})

    def test_empty_config_is_not_an_error(self):
        # `WATCH_STATUS_URL` để trống là cách bản ngoài khai "tôi không ở trong mạng đó".
        self.assertEqual(watch.parse_pairs(""), {})

    def test_a_malformed_entry_does_not_discard_the_rest(self):
        # Một dòng cấu hình gõ nhầm MUST NOT làm chỗ canh không khởi động được.
        self.assertEqual(watch.parse_pairs("rac lb=http://a/x"), {"lb": "http://a/x"})


class OutageStartTests(unittest.TestCase):
    """Mốc bắt đầu sự cố trong thư phải là lần dò TỐT cuối cùng, không phải lúc gửi thư.

    Khoá lại phép đo 18/09/2026: sự cố thật `16:36:43 → 16:40:14` (3 phút 31 giây), nhưng thư ghi
    bắt đầu `16:39:07` và kéo dài 1 phút 31 giây — mốc muộn 144 giây. Mục 7 tài liệu vận hành bảo
    lấy khoảng ấy đi tra `[FALLBACK]` trong log agent, nên khoảng hụt là mất số liệu thật.
    """

    LAST_OK = "2026-09-18T09:36:40+00:00"
    MAIL_AT = datetime(2026, 9, 18, 9, 39, 7, tzinfo=timezone.utc)

    def commit(self, state, new):
        with mock.patch.object(watch, "send_mail"):
            watch.commit({"name": "t", "every": 60}, state, new, self.MAIL_AT,
                         {}, "", [], "", SimpleNamespace(dry_run=True))
        return state

    def test_start_is_the_last_good_probe(self):
        state = self.commit({"state": watch.OK, "last_ok": self.LAST_OK}, watch.DOWN)
        self.assertEqual(state["since"], self.LAST_OK)

    def test_going_deeper_keeps_the_first_start(self):
        # degraded -> unavailable là MỘT sự cố đi sâu thêm, không phải sự cố thứ hai.
        state = self.commit({"state": watch.DEGRADED, "since": self.LAST_OK,
                             "last_ok": "2026-09-18T09:39:00+00:00"}, watch.DOWN)
        self.assertEqual(state["since"], self.LAST_OK)

    def test_recovery_clears_the_start(self):
        state = self.commit({"state": watch.DOWN, "since": self.LAST_OK}, watch.OK)
        self.assertEqual(state["since"], "")

    def test_no_last_ok_falls_back_to_now(self):
        # Chỗ canh dựng lại giữa sự cố thì chưa có nhịp tốt nào; MUST NOT vì thế mà chết.
        state = self.commit({"state": watch.OK}, watch.DOWN)
        self.assertEqual(state["since"], self.MAIL_AT.isoformat())


class DownMailTests(unittest.TestCase):
    """Thư `DOWN` phải đọc được mà không cần hỏi lại — tiêu chí 6.3 của change.

    Ngày 18/09/2026 người nhận đọc thư `DOWN` thật rồi vẫn phải hỏi "cái này đúng không, nghĩa là
    gì". Bảng thành phần có đủ dữ kiện nhưng không có kết luận, và không có mốc bắt đầu.
    """

    COMPONENTS = [{"id": "lb", "status": "reachable", "detail": "Liveness check passed."},
                  {"id": "proxy1", "status": "unreachable", "detail": "timed out"},
                  {"id": "proxy2", "status": "unreachable", "detail": "timed out"},
                  {"id": "route", "status": "unreachable", "detail": "timed out"}]

    def body(self, since=""):
        return watch.build_body("trong", watch.DOWN, watch.OK,
                                datetime(2026, 9, 18, 9, 58, tzinfo=timezone.utc), since,
                                {"lb": "TimeoutError"}, "unavailable", self.COMPONENTS, "", 60)

    def test_says_what_broke_without_reading_the_table(self):
        self.assertIn("CA HAI instance LiteLLM", self.body())

    def test_says_when_it_started(self):
        # Mốc bắt đầu phải có NGAY trong thư DOWN; thư OK tới sau, lúc hết cần.
        self.assertIn("18/09/2026 16:55:24", self.body("2026-09-18T09:55:24+00:00"))

    def test_says_what_to_run(self):
        self.assertIn("docker compose --profile gateway ps", self.body())

    def test_a_broken_start_stamp_still_sends_the_mail(self):
        self.assertIn("GATEWAY", self.body("rac").upper())


class DiagnoseTests(unittest.TestCase):
    def test_outer_layer(self):
        self.assertIn("nginx", watch.diagnose([{"id": "lb", "status": "unreachable"}]))

    def test_one_instance_down_names_it(self):
        line = watch.diagnose([{"id": "lb", "status": "reachable"},
                               {"id": "proxy2", "status": "unreachable"}])
        self.assertIn("proxy2", line)

    def test_no_components_says_nothing(self):
        # Không đọc được tình trạng thì im, MUST NOT đoán bừa.
        self.assertEqual(watch.diagnose([]), "")


class HeartbeatSwitchTests(unittest.TestCase):
    """`WATCH_HEARTBEAT_HOUR=off` phải TẮT thư nhịp tim, không phải gửi lúc 0 giờ.

    Chốt 18/09/2026: chỉ muốn thư khi có sự cố. Chỗ dễ sai là đọc `off` thành số 0 — lúc ấy mọi
    nhịp sau nửa đêm đều qua ngưỡng và thư nhịp tim vẫn gửi, tức làm ngược hẳn ý người dùng.
    """

    def hour(self, value: str) -> int:
        args = SimpleNamespace(every=60)
        with mock.patch.dict(os.environ, {"WATCH_HEARTBEAT_HOUR": value,
                                          "WATCH_HTTP": "lb=http://a/x"}):
            return watch.build_config(args)["heartbeat_hour"]

    def test_off_is_above_every_possible_hour(self):
        self.assertGreater(self.hour("off"), 23)

    def test_a_number_still_works(self):
        self.assertEqual(self.hour("8"), 8)

    def test_no_mail_and_no_counter_reset_when_off(self):
        cfg = {"name": "test", "heartbeat_hour": self.hour("off")}
        state = {"ticks": 9, "bad_ticks": 1}
        watch.heartbeat(cfg, state, datetime(2026, 9, 18, 3, 0, tzinfo=timezone.utc),
                        SimpleNamespace(dry_run=False))
        # Không gửi, và MUST NOT dọn bộ đếm: dọn là mất số liệu mà chẳng báo cho ai.
        self.assertNotIn("heartbeat_date", state)
        self.assertEqual(state["ticks"], 9)


if __name__ == "__main__":
    unittest.main()
