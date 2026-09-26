"""Quy định danh người dùng cuối về tài khoản, trong `db/load_gateway.py`.

Tách khỏi phép tra ở `connect.py`: tệp kia kiểm bảng tra dựng ĐÚNG chưa, tệp này
kiểm bộ nạp DÙNG nó đúng chưa. Hai chỗ hỏng khác nhau.

Vì sao phải có: hỏng ở đây KHÔNG làm sai một con số tổng nào. Token đủ, tiền đủ,
HTTP 200, dòng vẫn vào sổ - chỉ chiều người dùng là mất. Mọi phép nghiệm thu bằng
TỔNG đều ĐẠT. Bộ đếm `identity_unresolvable` là thứ duy nhất nói ra.
"""

import unittest
from datetime import datetime

from db import load_gateway as lg

AGENT_BY_CODE = {"tla-hd": 5, "dms-feedback": 6, "ralli": 8}
MODELS = {(lg.SOURCE, "gemini/gemini-3.6-flash"): 11}
# agent_id -> tài khoản neo. Với agent một-người-dùng, neo CHÍNH LÀ tài khoản
# dịch vụ (xem `connect.anchor_account_lookup`), nên "quy đúng" và "rơi về neo"
# đáp xuống cùng một dòng - phép kiểm phải soi bộ đếm, không soi `account_id`.
ANCHORS = {5: 947, 6: 949, 8: 953}
UNITS = {}
TS = datetime(2026, 9, 21, 3, 0, 0)


def ledger_row(call_id, end_user, tags):
    """Một dòng sổ Gateway. 19 trường, đúng thứ tự `build_rows()` bóc ra."""
    return (call_id, TS, "gemini/gemini-3.6-flash", end_user, tags,
            10, 20, 30, None, 0.001, "success", 120, None,
            "vk-test", False, False, "text", False, False)


def load_one(directory, end_user, tag):
    """Trả về (account_id của dòng, số định danh không phân giải được)."""
    rows, stats = lg.build_rows([ledger_row("c1", end_user, [tag])],
                                AGENT_BY_CODE, MODELS, directory, ANCHORS, UNITS)
    assert len(rows) == 1, "dòng phải vào sổ dù định danh có phân giải được hay không"
    return rows[0][6], stats["identity_unresolvable"]


class PersonInTwoAgentsTests(unittest.TestCase):
    """Lõi của change. Đo 21/09/2026: 5 người có mặt ở cả Ralli lẫn TLA Hợp Đồng."""

    # `longnt` có dòng danh bạ ở CẢ hai agent, cùng trỏ về account 348.
    DIRECTORY = {(5, "longnt"): 348, (8, "longnt"): 348}

    def test_resolves_under_the_agent_that_owns_the_account(self):
        acc, unresolved = load_one(self.DIRECTORY, "longnt", "tla-hd")
        self.assertEqual(acc, 348)
        self.assertEqual(unresolved, 0)

    def test_resolves_under_the_OTHER_agent_too(self):
        """Đây là dòng mà phép so cũ làm trượt.

        `account.unit_agent_id` của `longnt` là 8 (Ralli thắng phép chọn vì cây
        đơn vị của nó sâu hơn). Phép so cũ `found[1] == agent_id` vì thế từ chối
        mọi request của anh ấy qua agent 5 - 4/5 người va chạm mất theo cách này.
        """
        acc, unresolved = load_one(self.DIRECTORY, "longnt", "ralli")
        self.assertEqual(acc, 348)
        self.assertEqual(unresolved, 0)


class UnknownIdentityTests(unittest.TestCase):
    """Chiều âm. Nới lỏng phép so là mở lại lỗi đã đo 31/08/2026."""

    def test_local_admin_of_one_agent_is_rejected_by_another(self):
        """`admin` thuộc agent 5 và đã mang 480 lượt / 1.588.404 token.

        Agent 6 gửi `X-User: admin` - tên đăng nhập cục bộ của chính nó - thì
        lưu lượng ấy MUST NOT trộn vào lịch sử admin của TLA Hợp Đồng.
        """
        acc, unresolved = load_one({(5, "admin"): 1}, "admin", "dms-feedback")
        self.assertEqual(acc, ANCHORS[6], "phải rơi về neo của agent 6")
        self.assertEqual(unresolved, 1)

    def test_a_person_name_sent_to_a_single_user_agent_is_rejected(self):
        """Ca THẬT, đo 21/09/2026: `tuan.tran` gửi vào `dms-feedback`, 13 lượt.

        Agent một-người-dùng chỉ có một định danh hợp lệ là `svc.<code>`. Luật A5
        của `docs/reference/onboard-a-new-agent.md` nói đúng chuyện này.
        """
        acc, unresolved = load_one({(6, "svc.dms-feedback"): 949}, "tuan.tran",
                             "dms-feedback")
        self.assertEqual(acc, ANCHORS[6])
        self.assertEqual(unresolved, 1)

    def test_service_account_still_resolves(self):
        """Đối trọng của phép kiểm trên: 6 agent một-người-dùng KHÔNG được đổi."""
        acc, unresolved = load_one({(6, "svc.dms-feedback"): 949}, "svc.dms-feedback",
                             "dms-feedback")
        self.assertEqual(acc, 949)
        self.assertEqual(unresolved, 0)


class IdentityNormalisationTests(unittest.TestCase):
    """Bảng tra khoá bằng LOWER(TRIM()), nên chỗ tra phải chuẩn hoá y hệt.

    Đo 21/09/2026: 59/935 tên đăng nhập (6,3%) có chữ hoa, và HAI trong năm người
    va chạm nằm trong số đó - `Longnt` và `PBH3_TTHien`. Bỏ khâu này thì sửa xong
    vẫn mất 2/5 người, và triệu chứng là `identity_unresolvable` giảm nhưng KHÔNG
    về 0 - đủ để người sửa đi tìm một lỗi định tuyến không tồn tại.
    """

    DIRECTORY = {(8, "longnt"): 348}

    def test_uppercase_as_the_directory_spells_it(self):
        self.assertEqual(load_one(self.DIRECTORY, "Longnt", "ralli"), (348, 0))

    def test_all_uppercase(self):
        self.assertEqual(load_one(self.DIRECTORY, "LONGNT", "ralli"), (348, 0))

    def test_surrounding_whitespace(self):
        self.assertEqual(load_one(self.DIRECTORY, "  longnt  ", "ralli"), (348, 0))


class TotalsMustNotChangeTests(unittest.TestCase):
    """Change này KHÔNG sửa số liệu. Tổng đổi nghĩa là đã làm sai thứ khác."""

    def test_tokens_and_cost_are_complete_even_when_identity_fails(self):
        rows, stats = lg.build_rows(
            [ledger_row("c1", "longnt", ["ralli"]),
             ledger_row("c2", "khong-ai-biet", ["ralli"])],
            AGENT_BY_CODE, MODELS, {(8, "longnt"): 348}, ANCHORS, UNITS)
        self.assertEqual(len(rows), 2)
        self.assertEqual(sum(r[11] for r in rows), 60)
        self.assertAlmostEqual(sum(r[14] for r in rows), 0.002)
        self.assertEqual(stats["identity_unresolvable"], 1)
        # Đúng một dòng rơi về neo - chỗ "không quy được về ai".
        self.assertEqual(sum(1 for r in rows if r[6] == ANCHORS[8]), 1)

    def test_empty_identity_is_not_counted_as_unresolvable(self):
        """`end_user` rỗng là THIẾU TIN, không phải một định danh sai.

        Đo trên sổ thật: 368 dòng như vậy. Đếm chúng vào `identity_unresolvable`
        là nhấn chìm 15 ca thật trong tiếng ồn.
        """
        rows, stats = lg.build_rows([ledger_row("c1", "", ["ralli"])],
                                    AGENT_BY_CODE, MODELS, {}, ANCHORS, UNITS)
        self.assertEqual(stats["identity_unresolvable"], 0)
        self.assertEqual(stats["end_user_empty"], 1)
        self.assertEqual(rows[0][6], ANCHORS[8])


if __name__ == "__main__":
    unittest.main()
