"""Phép kiểm cho `decide()` — hàm quyết định có gọi người dậy lúc nửa đêm hay không.

Chỉ kiểm hàm gộp, không kiểm phép dò: phép dò cần mạng, còn chỗ sai nguy hiểm thì nằm ở luật gộp.

Ca quan trọng nhất là `test_status_says_down_but_a_real_call_still_works`. Nó khoá lại một phép đo
ngày 17/09/2026: dừng `litellm-1` thì `/api/status` trả `unavailable` trong khi một lượt gọi thật
qua load balancer **vẫn xong**. Nguyên nhân là `tools/gateway-status/server.js` dò `route` với hạn
2,5 giây, thấp hơn hẳn cửa sổ `proxy_connect_timeout 10s` × `proxy_next_upstream_tries 2` của
nginx — nên phép dò của nó bỏ cuộc trong lúc nginx đang tự chuyển tuyến.

Tin `/api/status` ở ca đó là báo "chết hẳn" cho một sự cố mà agent vẫn gọi được.
"""
import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
