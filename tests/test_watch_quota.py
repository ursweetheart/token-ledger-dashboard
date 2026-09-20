"""Phép kiểm cho luật đổi bậc của bộ canh hạn mức.

Chỉ kiểm phần quyết định, không kiểm phép đọc Gateway hay phép gửi thư: hai thứ
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


class TickTests(unittest.TestCase):
    """Một nhịp kiểm: ai được gửi thư, ai không."""

    def setUp(self):
        self.sent = []
        self.rows = []
        self._mail = wq.send_mail
        self._rows = wq.rows_from_gateway
        wq.send_mail = lambda subject, body, dry: self.sent.append(subject)
        wq.rows_from_gateway = lambda: self.rows
        self.addCleanup(self.restore)

    def restore(self):
        wq.send_mail = self._mail
        wq.rows_from_gateway = self._rows

    def row(self, ratio, alias="ralli-tagged"):
        return {"alias": alias, "quota": 50.0, "spent": 50.0 * (ratio or 0),
                "ratio": ratio}

    def tick(self, state):
        args = type("A", (), {"dry_run": True})()
        return wq.tick(state, args)

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
