"""Phép kiểm cho lớp hạn mức. KHÔNG cần Gateway thật chạy.

CA QUAN TRỌNG NHẤT là `test_writing_a_quota_keeps_the_identity_tag`.

Nó khoá lại một cái bẫy đọc được trong mã nguồn LiteLLM
(`key_management_endpoints.py:2010`): `/key/update` **thay thế** cả cục metadata
chứ không gộp. Nên gửi `{"metadata": {"quota_usd": 50}}` sẽ xoá `tags` của khoá.

Hỏng kiểu đó không ném lỗi nào. Tag định danh biến mất, request rơi sang tuyến
khác, tiền ghi sai project - mà mọi lượt gọi vẫn trả 200. Đo ngày 31/08/2026
trên khoá không mang tag: 7/8 lượt thành công, 1/8 lạc tuyến. Tức 12,5%, và
"gọi thử thấy chạy" không phát hiện ra.

Vì vậy phép kiểm này soi ĐÚNG THÂN YÊU CẦU gửi đi, không soi giá trị trả về.
"""
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# CỐ Ý KHÔNG nạp `backend.main`: file đó kéo theo FastAPI, mà bộ kiểm của dự án
# phải chạy được trên một máy sạch không cài thêm gói. Phần logic đáng kiểm đã
# nằm trong `backend/gateway.py`, và những gì còn lại ở `main.py` được kiểm bằng
# cách đọc mã nguồn - xem `RouteTests`.
from backend import gateway  # noqa: E402

TAGGED_KEY = {
    "key_alias": "dms-feedback-tagged",
    "spend": 12.5,
    "metadata": {"tags": ["dms-feedback"], "note": "giu nguyen"},
}


class MergeTests(unittest.TestCase):
    """Phần dựng metadata mới - chỗ duy nhất quyết định cái gì bị mất."""

    def test_writing_a_quota_keeps_the_identity_tag(self):
        merged = gateway._merge(TAGGED_KEY["metadata"], 50.0, "dashboard")
        self.assertEqual(merged["tags"], ["dms-feedback"])
        self.assertEqual(merged[gateway.QUOTA_FIELD], 50.0)

    def test_writing_a_quota_keeps_unrelated_fields(self):
        merged = gateway._merge(TAGGED_KEY["metadata"], 50.0, "dashboard")
        self.assertEqual(merged["note"], "giu nguyen")

    def test_the_source_metadata_is_not_mutated(self):
        before = dict(TAGGED_KEY["metadata"])
        gateway._merge(TAGGED_KEY["metadata"], 50.0, "dashboard")
        self.assertEqual(TAGGED_KEY["metadata"], before)

    def test_each_write_appends_one_log_entry(self):
        first = gateway._merge({}, 50.0, "dashboard")
        second = gateway._merge(first, 80.0, "dashboard")
        self.assertEqual(len(second[gateway.LOG_FIELD]), 2)
        self.assertEqual(second[gateway.LOG_FIELD][-1]["from"], 50.0)
        self.assertEqual(second[gateway.LOG_FIELD][-1]["to"], 80.0)

    def test_history_survives_a_later_write(self):
        first = gateway._merge({}, 50.0, "dashboard")
        stamp = first[gateway.LOG_FIELD][0]["at"]
        second = gateway._merge(first, 80.0, "dashboard")
        self.assertEqual(second[gateway.LOG_FIELD][0]["at"], stamp)


class SetQuotaTests(unittest.TestCase):
    """Soi thân yêu cầu thật sự gửi sang Gateway."""

    def setUp(self):
        gateway.configure("http://gateway.invalid", "sk-master")

    def test_the_request_body_carries_the_whole_metadata(self):
        sent = {}

        def fake_call(path, method, payload=None, query=None):
            if path == gateway._PATH_LIST:
                return {"keys": [TAGGED_KEY], "total_pages": 1}
            sent["payload"] = payload
            return {}

        with mock.patch.object(gateway, "_call", side_effect=fake_call):
            gateway.set_quota("dms-feedback-tagged", 50.0, "dashboard")

        metadata = sent["payload"]["metadata"]
        # Đây là phép kiểm chống đúng cái bẫy ở đầu file.
        self.assertEqual(metadata["tags"], ["dms-feedback"])
        self.assertEqual(metadata[gateway.QUOTA_FIELD], 50.0)
        self.assertEqual(sent["payload"]["key_alias"], "dms-feedback-tagged")

    def test_an_unknown_alias_is_an_error_not_a_silent_create(self):
        with mock.patch.object(gateway, "_call",
                               return_value={"keys": [], "total_pages": 1}):
            with self.assertRaises(gateway.GatewayError):
                gateway.set_quota("khong-ton-tai", 50.0, "dashboard")


class ReadingTests(unittest.TestCase):
    """Đọc hạn mức: giá trị lạ phải thành 'chưa đặt', không thành lỗi."""

    def test_missing_quota_reads_as_none(self):
        self.assertIsNone(gateway.quota_of({"metadata": {}}))

    def test_a_string_quota_reads_as_none(self):
        self.assertIsNone(gateway.quota_of({"metadata": {gateway.QUOTA_FIELD: "50"}}))

    def test_a_boolean_quota_reads_as_none(self):
        # `True` là số nguyên hợp lệ trong Python; không loại tường minh thì
        # `quota_usd: true` thành hạn mức 1 đô.
        self.assertIsNone(gateway.quota_of({"metadata": {gateway.QUOTA_FIELD: True}}))

    def test_a_negative_quota_reads_as_none(self):
        self.assertIsNone(gateway.quota_of({"metadata": {gateway.QUOTA_FIELD: -5}}))

    def test_a_real_quota_reads_back(self):
        self.assertEqual(gateway.quota_of({"metadata": {gateway.QUOTA_FIELD: 50}}), 50.0)

    def test_spend_defaults_to_zero(self):
        self.assertEqual(gateway.spend_of({}), 0.0)

    def test_a_broken_history_reads_as_empty(self):
        self.assertEqual(gateway.log_of({"metadata": {gateway.LOG_FIELD: "hong"}}), [])


class SanitizeTests(unittest.TestCase):
    def test_only_the_quota_field_survives(self):
        cleaned = gateway.sanitize_incoming(
            {gateway.QUOTA_FIELD: 50, "tags": ["gia-mao"], "spend": 0})
        self.assertEqual(cleaned, {gateway.QUOTA_FIELD: 50})

    def test_none_is_allowed(self):
        self.assertEqual(gateway.sanitize_incoming(None), {})


class MasterKeyTests(unittest.TestCase):
    def test_an_http_error_never_carries_the_master_key(self):
        import urllib.error

        gateway.configure("http://gateway.invalid", "sk-master-secret")
        err = urllib.error.HTTPError("http://gateway.invalid/key/list", 403,
                                     "Forbidden", {}, None)
        with mock.patch.object(gateway.urllib.request, "urlopen", side_effect=err):
            with self.assertRaises(gateway.GatewayError) as caught:
                gateway.list_keys()
        self.assertNotIn("sk-master-secret", str(caught.exception))

    def test_an_unreachable_gateway_never_carries_the_master_key(self):
        import urllib.error

        gateway.configure("http://gateway.invalid", "sk-master-secret")
        with mock.patch.object(gateway.urllib.request, "urlopen",
                               side_effect=urllib.error.URLError("timed out")):
            with self.assertRaises(gateway.GatewayError) as caught:
                gateway.list_keys()
        self.assertNotIn("sk-master-secret", str(caught.exception))


class AmountTests(unittest.TestCase):
    """Giá trị nhập vào bị từ chối kèm lý do, không lặng lẽ thành 0."""

    def reject(self, value):
        with self.assertRaises(ValueError) as caught:
            gateway.parse_amount(value)
        # Lý do phải nói được VÌ SAO, vì nó đi thẳng ra màn hình người dùng.
        self.assertTrue(str(caught.exception).strip())

    def test_negative_is_rejected(self):
        self.reject(-1)

    def test_text_is_rejected(self):
        self.reject("nhieu tien")

    def test_empty_is_rejected(self):
        self.reject("")

    def test_boolean_is_rejected(self):
        self.reject(True)

    def test_infinity_is_rejected(self):
        self.reject(float("inf"))

    def test_a_number_as_text_is_accepted(self):
        # Ô nhập trên web gửi chuỗi. Từ chối "50" là từ chối chính đường dùng thật.
        self.assertEqual(gateway.parse_amount("50"), 50.0)

    def test_zero_is_accepted(self):
        # 0 là cách chặn hẳn một agent, không phải giá trị vô nghĩa.
        self.assertEqual(gateway.parse_amount(0), 0.0)


class RouteTests(unittest.TestCase):
    """Hai endpoint GHI phải đòi khoá y như mọi endpoint đọc.

    Kiểm bằng cách ĐỌC MÃ NGUỒN, không nạp `backend.main`: nạp nó kéo theo
    FastAPI, mà bộ kiểm của dự án phải chạy được trên một máy sạch không cài
    thêm gói. Yếu hơn một phép kiểm hành vi, nhưng nó bắt đúng hồi quy đáng sợ
    nhất ở đây: ai đó thêm một đường ghi mà quên `Depends(caller)`.
    """

    def setUp(self):
        self.src = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")

    def write_routes(self):
        # Mỗi `@app.post(...)` kèm hàm ngay dưới nó, tới hết chữ ký hàm.
        return re.findall(r'@app\.post\(\s*"([^"]+)"[\s\S]*?\ndef \w+\(([\s\S]*?)\)\s*:',
                          self.src)

    def test_every_write_route_asks_for_a_credential(self):
        routes = self.write_routes()
        self.assertTrue(routes, "khong tim thay endpoint ghi nao trong main.py")
        for path, signature in routes:
            self.assertIn("Depends(caller)", signature,
                          f"{path} khong doi chung danh")

    def test_the_only_write_routes_are_the_quota_ones(self):
        # Một endpoint ghi mới xuất hiện mà không ai để ý là chuyện đáng biết:
        # đây là API vốn chỉ-đọc, và mỗi đường ghi là một quyết định.
        self.assertEqual(sorted(p for p, _ in self.write_routes()),
                         ["/api/quota", "/api/quota/top-up"])

    def test_cors_allows_the_post_method(self):
        # Thiếu "POST" ở đây thì trình duyệt chặn ngay bước preflight, và lỗi hiện
        # ra là "CORS" chứ không phải "401" - mất công tìm nhầm chỗ.
        self.assertRegex(self.src, r'allow_methods=\["GET",\s*"POST"\]')

    def test_the_quota_endpoints_go_through_the_gateway_layer(self):
        # Không được gọi thẳng `urllib` từ `main.py`: phạm vi những gì sửa được
        # nằm trong `backend/gateway.py`, và nó chỉ giữ được nếu mọi lượt gọi đi
        # qua đó.
        self.assertNotIn("urllib", self.src)


if __name__ == "__main__":
    unittest.main()
