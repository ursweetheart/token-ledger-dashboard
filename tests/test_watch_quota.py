"""Phép kiểm cho luật đổi bậc của bộ canh hạn mức.

Chỉ kiểm phần quyết định, không kiểm phép đọc qua worker hay phép gửi thư: hai thứ
đó cần mạng, còn chỗ sai nguy hiểm thì nằm ở luật "khi nào gửi thư".

HAI CA ĐÁNG GIÁ NHẤT:

  `test_staying_in_a_band_sends_nothing` - một thư mỗi lần ĐỔI bậc, không phải
  mỗi nhịp kiểm. Sai chỗ này thì hộp thư đầy thư giống hệt nhau và người nhận
  ngừng đọc, đúng lúc thư thật sự quan trọng.

  `test_a_top_up_resets_the_band_without_a_mail` - nạp thêm làm tỉ lệ tụt xuống;
  lần vượt SAU phải báo lại. Không đặt lại bậc thì cảnh báo chỉ hoạt động đúng
  một lần trong đời mỗi khoá.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import watch_quota as wq  # noqa: E402


class LevelTests(unittest.TestCase):
    def test_no_quota_is_ok(self):
        self.assertEqual(wq.level_of(None), wq.OK)

    def test_well_under_is_ok(self):
        self.assertEqual(wq.level_of(0.42), wq.OK)

    def test_just_under_ninety_is_still_ok(self):
        self.assertEqual(wq.level_of(0.8999), wq.OK)

    def test_ninety_is_the_first_band(self):
        self.assertEqual(wq.level_of(0.90), wq.B90)

    def test_one_hundred_is_the_second_band(self):
        self.assertEqual(wq.level_of(1.0), wq.B100)

    def test_a_little_over_is_still_the_second_band(self):
        # Chặn ở đúng 100% nhưng chi phí của lượt cuối chỉ biết sau khi gọi, nên
        # trôi qua vài phần trăm là bình thường - không phải chuyện đáng báo động.
        self.assertEqual(wq.level_of(1.05), wq.B100)

    def test_ten_percent_over_means_blocking_is_not_working(self):
        # Đây mới là tín hiệu đáng gọi người: tiêu thêm được hơn 10% sau khi đã
        # chạm hạn mức nghĩa là lưu lượng đang đi đường khác.
        self.assertEqual(wq.level_of(1.10), wq.OVER)


class LadderTests(unittest.TestCase):
    def test_going_up_one_band_is_a_rise(self):
        self.assertTrue(wq.rose(wq.OK, wq.B90))

    def test_jumping_several_bands_is_a_rise(self):
        self.assertTrue(wq.rose(wq.OK, wq.OVER))

    def test_staying_put_is_not_a_rise(self):
        self.assertFalse(wq.rose(wq.B90, wq.B90))

    def test_going_down_is_not_a_rise(self):
        self.assertFalse(wq.rose(wq.OVER, wq.OK))

    def test_an_unknown_band_does_not_crash(self):
        self.assertFalse(wq.rose("bac-la", "bac-la-khac"))


class TickHarness:
    """Thay phép đọc và phép gửi thư bằng bản giả. Không mang phép kiểm nào."""

    def setUp(self):
        self.sent = []
        self.rows = []
        self._mail = wq.send_mail
        self._rows = wq.rows_from_worker
        wq.send_mail = lambda subject, body, dry: self.sent.append(subject)
        wq.rows_from_worker = lambda: self.rows
        self.addCleanup(self.restore)

    def restore(self):
        wq.send_mail = self._mail
        wq.rows_from_worker = self._rows

    def row(self, ratio, alias="ralli-tagged"):
        return {"alias": alias, "quota": 50.0, "spent": 50.0 * (ratio or 0),
                "ratio": ratio}

    def tick(self, state):
        args = type("A", (), {"dry_run": True})()
        return wq.tick(state, args)


class TickTests(TickHarness, unittest.TestCase):
    """Một nhịp kiểm: ai được gửi thư, ai không."""

    def test_crossing_ninety_sends_one_mail(self):
        self.rows = [self.row(0.91)]
        self.tick({})
        self.assertEqual(len(self.sent), 1)

    def test_staying_in_a_band_sends_nothing(self):
        self.rows = [self.row(0.91)]
        state = self.tick({})
        self.sent.clear()
        self.rows = [self.row(0.95)]
        self.tick(state)
        self.assertEqual(self.sent, [])

    def test_jumping_bands_sends_one_mail_for_the_highest(self):
        self.rows = [self.row(1.30)]
        self.tick({})
        self.assertEqual(len(self.sent), 1)
        self.assertIn("VUOT", self.sent[0])

    def test_a_top_up_resets_the_band_without_a_mail(self):
        self.rows = [self.row(1.20)]
        state = self.tick({})
        self.sent.clear()
        self.rows = [self.row(0.30)]          # vừa nạp thêm
        state = self.tick(state)
        self.assertEqual(self.sent, [], "tut bac thi khong duoc gui thu")
        self.rows = [self.row(0.95)]          # lần vượt sau
        self.tick(state)
        self.assertEqual(len(self.sent), 1, "lan vuot sau phai bao lai")

    def test_restarting_does_not_resend(self):
        self.rows = [self.row(1.0)]
        state = self.tick({})
        self.sent.clear()
        # Khởi động lại = nạp đúng file trạng thái đó rồi chạy tiếp.
        self.tick({"levels": dict(state["levels"])})
        self.assertEqual(self.sent, [])

    def test_a_key_with_no_quota_is_never_mailed(self):
        self.rows = [self.row(None)]
        self.tick({})
        self.assertEqual(self.sent, [])

    def test_each_key_is_tracked_on_its_own(self):
        self.rows = [self.row(1.0, "a"), self.row(0.1, "b")]
        self.tick({})
        self.assertEqual(len(self.sent), 1)


class UnreadableTests(TickHarness, unittest.TestCase):
    """Worker tắt thì bộ canh mù: không đoán bậc, nhưng phải nói ra là đang mù.

    Từ 16/11/2026 bộ canh đọc hạn mức qua worker (không còn giữ master key). Im
    lặng lúc không đọc được trông y hệt "mọi khoá đều ổn" - đúng lúc cần biết nhất.
    """

    def fail(self):
        raise RuntimeError("worker down")

    def test_one_failed_read_sends_nothing(self):
        # Worker vừa khởi động lại là chuyện thường; một nhịp hỏng không đáng một thư.
        wq.rows_from_worker = self.fail
        self.tick({})
        self.assertEqual(self.sent, [])

    def test_repeated_failed_reads_send_exactly_one_mail(self):
        wq.rows_from_worker = self.fail
        state = {}
        for _ in range(wq.UNREADABLE_BEFORE_MAIL + 3):
            state = self.tick(state)
        self.assertEqual(len(self.sent), 1)
        self.assertIn("KHONG DOC DUOC", self.sent[0])

    def test_a_failed_read_keeps_the_bands_and_guesses_nothing(self):
        self.rows = [self.row(1.0)]
        state = self.tick({})
        before = dict(state["levels"])
        self.sent.clear()
        wq.rows_from_worker = self.fail
        state = self.tick(state)
        self.assertEqual(state["levels"], before)

    def test_a_second_outage_is_reported_again(self):
        wq.rows_from_worker = self.fail
        state = {}
        for _ in range(wq.UNREADABLE_BEFORE_MAIL):
            state = self.tick(state)
        wq.rows_from_worker = lambda: []      # đọc lại được
        state = self.tick(state)
        wq.rows_from_worker = self.fail
        for _ in range(wq.UNREADABLE_BEFORE_MAIL):
            state = self.tick(state)
        self.assertEqual(len(self.sent), 2)


class WorkerReadTests(unittest.TestCase):
    """Dữ liệu worker trả về -> dòng đem so bậc. Không có master key ở đâu cả."""

    def setUp(self):
        self._rpc = wq.RPC
        self.addCleanup(lambda: setattr(wq, "RPC", self._rpc))

    def test_rows_come_from_the_quota_list_rpc(self):
        calls = []

        def rpc(action, data):
            calls.append((action, data))
            return {"keys": [
                {"key_alias": "ralli-tagged", "spend": 45.0, "metadata": {"quota_usd": 50}},
                {"key_alias": "no-quota", "spend": 3.0, "metadata": {}},
                {"key_alias": None, "spend": 1.0},            # khoá không tên: bỏ
                "hong",                                       # dòng sai kiểu: bỏ
            ]}

        wq.RPC = rpc
        rows = wq.rows_from_worker()
        self.assertEqual(calls, [("quota-list", {})])
        self.assertEqual([r["alias"] for r in rows], ["ralli-tagged", "no-quota"])
        self.assertAlmostEqual(rows[0]["ratio"], 0.9)
        self.assertIsNone(rows[1]["ratio"])

    def test_the_script_no_longer_reads_the_master_key(self):
        # Soi chuỗi trong MÃ, không soi docstring: docstring kể lại lịch sử nên có nhắc tên.
        import ast
        tree = ast.parse((ROOT / "scripts" / "watch_quota.py").read_text(encoding="utf-8"))
        docstrings = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr)}
        strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
                   and isinstance(n.value, str) and id(n) not in docstrings]
        self.assertFalse([x for x in strings if "LITELLM_MASTER_KEY" in x or "/key/" in x])


class BodyTests(unittest.TestCase):
    def test_the_mail_says_what_to_do_next(self):
        row = {"alias": "ralli-tagged", "quota": 50.0, "spent": 50.0, "ratio": 1.0}
        body = wq.body_for(row, wq.B100, enforceable=True)
        self.assertIn("nap them", body.lower())

    def test_a_key_that_cannot_block_says_so(self):
        row = {"alias": "x", "quota": 50.0, "spent": 45.0, "ratio": 0.9}
        body = wq.body_for(row, wq.B90, enforceable=False)
        self.assertIn("canh bao suong", body.lower())

    def test_the_over_mail_points_at_the_likely_causes(self):
        row = {"alias": "x", "quota": 50.0, "spent": 60.0, "ratio": 1.2}
        body = wq.body_for(row, wq.OVER, enforceable=True)
        self.assertIn("QUOTA_DRY_RUN", body)


if __name__ == "__main__":
    unittest.main()
