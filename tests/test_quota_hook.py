"""Phép kiểm cho phần quyết định của hook chặn hạn mức.

KIỂM CẢ NHÁNH HỎNG, KHÔNG CHỈ NHÁNH CHẠY ĐÚNG. Hook này chạy trên MỌI request
của Gateway, nên một lỗi trong nó là lỗi của toàn bộ Gateway. Ba ca quan trọng
nhất đều là ca "dữ liệu không như mong đợi thì vẫn phải CHO QUA". Chặn nhầm vì
một giá trị gõ sai còn tệ hơn không chặn: nó biến một lỗi gõ tay thành một sự cố
toàn hệ thống.

VÌ SAO KHÔNG KIỂM THẲNG LỚP HOOK: lớp đó kế thừa `CustomLogger` của `litellm`,
mà `litellm` chỉ có bên trong container Gateway. Phép kiểm phụ thuộc nó sẽ bị bỏ
qua ở mọi nơi khác - và một phép kiểm không bao giờ chạy thì không bảo vệ được
gì. Nên `quota_hook.decide_action` được tách ra thành hàm thuần, và đó là chỗ
chứa toàn bộ logic.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docker" / "gateway"))

import quota_hook  # noqa: E402

CHAT = frozenset({"ralli", "tla-hd"})


def act(quota=None, spend=0.0, tags=("dms-feedback",), chat_tags=CHAT):
    metadata = {} if quota is None else {quota_hook.QUOTA_FIELD: quota}
    action, _info = quota_hook.decide_action(metadata, spend, list(tags), chat_tags)
    return action


class PassThroughTests(unittest.TestCase):
    """Mọi thứ không phải 'đã hết hạn mức rõ ràng' đều phải đi tiếp."""

    def test_no_quota_lets_traffic_through(self):
        self.assertEqual(act(quota=None, spend=999), quota_hook.PASS)

    def test_under_quota_lets_traffic_through(self):
        self.assertEqual(act(quota=50, spend=49.99), quota_hook.PASS)

    def test_a_broken_quota_lets_traffic_through(self):
        for bad in ("50", True, -1, None, float("inf"), float("nan"), [], {}):
            with self.subTest(bad=bad):
                self.assertEqual(act(quota=bad, spend=999), quota_hook.PASS)

    def test_a_broken_spend_counts_as_zero(self):
        for bad in ("nhieu", True, None, [], float("nan")):
            with self.subTest(bad=bad):
                self.assertEqual(act(quota=50, spend=bad), quota_hook.PASS)

    def test_metadata_of_the_wrong_shape_lets_traffic_through(self):
        for bad in (None, "khong phai dict", 7, []):
            with self.subTest(bad=bad):
                action, _ = quota_hook.decide_action(bad, 999, ["ralli"], CHAT)
                self.assertEqual(action, quota_hook.PASS)


class BlockingTests(unittest.TestCase):
    def test_a_chat_agent_is_blocked_with_a_message(self):
        self.assertEqual(act(quota=50, spend=50, tags=("ralli",)), quota_hook.BLOCK_CHAT)

    def test_a_batch_agent_is_blocked_with_a_429(self):
        self.assertEqual(act(quota=50, spend=50, tags=("dms-feedback",)),
                         quota_hook.BLOCK_BATCH)

    def test_an_unknown_tag_is_treated_as_a_batch_agent(self):
        # Mặc định an toàn: sai kiểu này chỉ làm agent nghỉ; sai kiểu kia đẩy
        # văn xuôi vào một đường phân tích JSON.
        self.assertEqual(act(quota=50, spend=50, tags=("agent-chua-khai",)),
                         quota_hook.BLOCK_BATCH)

    def test_no_tag_at_all_is_treated_as_a_batch_agent(self):
        self.assertEqual(act(quota=50, spend=50, tags=()), quota_hook.BLOCK_BATCH)

    def test_litellm_own_tags_are_not_mistaken_for_an_agent(self):
        # LiteLLM tự thêm tag `User-Agent: ...`. Lấy "tag đầu tiên" là sai.
        self.assertEqual(act(quota=50, spend=50,
                             tags=("User-Agent: curl/8.0", "ralli")),
                         quota_hook.BLOCK_CHAT)

    def test_spending_far_past_the_quota_still_blocks(self):
        self.assertEqual(act(quota=50, spend=120), quota_hook.BLOCK_BATCH)

    def test_a_zero_quota_blocks_everything(self):
        # 0 là cách chặn hẳn một agent, không phải "chưa đặt".
        self.assertEqual(act(quota=0, spend=0), quota_hook.BLOCK_BATCH)


class ReportedInfoTests(unittest.TestCase):
    """Thông tin đem ghi log phải đủ để truy nguyên một khoảng agent im lặng."""

    def test_the_block_record_carries_the_numbers(self):
        _action, info = quota_hook.decide_action(
            {quota_hook.QUOTA_FIELD: 50}, 50.03, ["dms-feedback"], CHAT)
        self.assertEqual(info["quota"], 50.0)
        self.assertEqual(info["spent"], 50.03)
        self.assertEqual(info["agent"], "dms-feedback")
        self.assertEqual(info["reply"], "429")

    def test_a_pass_reports_nothing(self):
        _action, info = quota_hook.decide_action({}, 0, ["ralli"], CHAT)
        self.assertEqual(info, {})


class LogTests(unittest.TestCase):
    def test_the_log_line_is_machine_readable_json(self):
        import io
        import json
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            quota_hook._log("quota_block", agent="ralli", quota=50.0, spent=51.0)
        row = json.loads(buf.getvalue().strip())
        self.assertEqual(row["event"], "quota_block")
        self.assertEqual(row["agent"], "ralli")
        self.assertIn("at", row)


class ConfigTests(unittest.TestCase):
    def test_chat_tags_come_from_the_environment(self):
        os.environ["QUOTA_CHAT_TAGS"] = "chi-mot-agent"
        self.addCleanup(os.environ.pop, "QUOTA_CHAT_TAGS", None)
        action, _ = quota_hook.decide_action(
            {quota_hook.QUOTA_FIELD: 50}, 50, ["chi-mot-agent"])
        self.assertEqual(action, quota_hook.BLOCK_CHAT)

    def test_an_empty_environment_value_falls_back_to_the_default(self):
        # Compose truyền `${VAR:-}` thành chuỗi RỖNG, không phải vắng mặt. Bản
        # trước dùng tham số mặc định của `os.getenv` nên tin nhắn thành rỗng và
        # người dùng nhận một câu trả lời trắng, không lỗi nào báo ra.
        os.environ["QUOTA_BLOCK_MESSAGE"] = ""
        os.environ["QUOTA_CHAT_TAGS"] = ""
        self.addCleanup(os.environ.pop, "QUOTA_BLOCK_MESSAGE", None)
        self.addCleanup(os.environ.pop, "QUOTA_CHAT_TAGS", None)
        self.assertTrue(quota_hook._message().strip())
        self.assertIn("ralli", quota_hook._chat_tags())

    def test_the_default_message_says_it_is_a_system_notice(self):
        # Người dùng cuối phải phân biệt được "model từ chối" với "hệ thống hết
        # tiền". Câu chữ là thứ duy nhất nói ra điều đó.
        self.assertIn("hệ thống", quota_hook._message().lower())


if __name__ == "__main__":
    unittest.main()
