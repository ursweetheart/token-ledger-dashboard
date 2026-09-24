"""Phép tra (agent, tên đăng nhập) -> tài khoản, dùng cho chiều người dùng.

Vì sao có tệp này: phép tra cũ khoá bằng tên đăng nhập MỘT MÌNH, nên nó chỉ trả
về được một agent cho mỗi người và bên gọi phải đem đi so sánh. Phép so ấy trượt
với người có mặt ở hai agent - đo 21/09/2026: 5 người, Ralli và TLA Hợp Đồng.

Hỏng kiểu đó không làm sai một con số tổng nào, nên nó phải được khoá lại bằng
phép kiểm chứ không bằng mắt.
"""

import unittest

from db import connect


class FakeCursor:
    """Trả kết quả theo NỘI DUNG câu truy vấn, vì hàm chạy hai câu khác nhau."""

    def __init__(self, directory_rows, service_rows, seen_sql):
        self.directory_rows = directory_rows
        self.service_rows = service_rows
        self.seen_sql = seen_sql
        self._rows = []

    def execute(self, sql, params=None):
        self.seen_sql.append(sql)
        self._rows = self.directory_rows if "dim_user" in sql else self.service_rows

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(self, directory_rows=(), service_rows=()):
        self.seen_sql = []
        self._cursor = FakeCursor(list(directory_rows), list(service_rows),
                                  self.seen_sql)

    def cursor(self):
        return self._cursor


class DirectoryAccountLookupTests(unittest.TestCase):

    def test_person_in_two_agents_resolves_under_both(self):
        """Lõi của cả change: một người, hai agent, hai khoá, cùng tài khoản."""
        cn = FakeConnection(directory_rows=[
            (8, "longnt", 500),      # Ralli
            (5, "longnt", 500),      # TLA Hợp Đồng
        ])
        got = connect.directory_account_lookup(cn)
        self.assertEqual(got[(8, "longnt")], 500)
        self.assertEqual(got[(5, "longnt")], 500)

    def test_same_name_different_people_stay_apart(self):
        """Chiều âm: tên trùng nhưng là hai người khác nhau thì KHÔNG được gộp."""
        cn = FakeConnection(directory_rows=[
            (5, "admin", 1),
            (8, "admin", 77),
        ])
        got = connect.directory_account_lookup(cn)
        self.assertEqual(got[(5, "admin")], 1)
        self.assertEqual(got[(8, "admin")], 77)

    def test_identity_absent_from_an_agent_is_not_resolvable_there(self):
        """`admin` của agent 5 MUST NOT tra ra được dưới agent 6.

        Đây là đường hỏng đã đo 31/08/2026: bảng `account` có dòng `admin` thuộc
        agent 5 mang 480 lượt / 1.588.404 token, và một agent khác gửi
        `X-User: admin` thì lưu lượng trộn vào lịch sử của người đó.
        """
        cn = FakeConnection(directory_rows=[(5, "admin", 1)])
        got = connect.directory_account_lookup(cn)
        self.assertIn((5, "admin"), got)
        self.assertNotIn((6, "admin"), got)

    def test_service_account_resolves_under_its_own_agent(self):
        """D1b: `svc.<code>` CHỈ có ở bảng `account`, không có ở `dim_user`.

        Trong `dim_user` tài khoản ấy mang tên `__technical_6__`. Tra riêng
        `dim_user` thì cả 6 agent một-người-dùng rơi khỏi chiều người dùng.
        """
        cn = FakeConnection(
            directory_rows=[],                      # không có dòng nào không-kỹ-thuật
            service_rows=[(6, "svc.dms-feedback", 949)])
        got = connect.directory_account_lookup(cn)
        self.assertEqual(got[(6, "svc.dms-feedback")], 949)

    def test_all_six_single_user_agents_resolve(self):
        """Việc 1.5: cả 6 agent một-người-dùng, không phải chỉ một cái mẫu."""
        ma = {1: "contact-center", 2: "sale-agent", 3: "invoice",
              4: "tools-quizzer", 6: "dms-feedback", 7: "crm-feedback"}
        cn = FakeConnection(
            service_rows=[(aid, f"svc.{code}", 900 + aid)
                          for aid, code in ma.items()])
        got = connect.directory_account_lookup(cn)
        for aid, code in ma.items():
            self.assertEqual(got[(aid, f"svc.{code}")], 900 + aid)

    def test_duplicate_key_same_account_is_merged(self):
        """Ralli ghi 13 dòng bằng hai dạng khoá; cả hai trỏ về một tài khoản."""
        cn = FakeConnection(directory_rows=[
            (8, "tg.namnh", 612),
            (8, "tg.namnh", 612),
        ])
        got = connect.directory_account_lookup(cn)
        self.assertEqual(got[(8, "tg.namnh")], 612)

    def test_duplicate_key_different_accounts_stops(self):
        """Việc 1.2: dữ liệu hỏng thì DỪNG, không im lặng chọn một.

        Gộp trùng chỉ đúng nhờ một tính chất không ràng buộc nào cưỡng chế. Dựa
        vào nó trong im lặng là để một lỗi dữ liệu đi thẳng vào sổ.
        """
        cn = FakeConnection(directory_rows=[
            (8, "tg.namnh", 612),
            (8, "tg.namnh", 777),
        ])
        with self.assertRaises(SystemExit) as stop:
            connect.directory_account_lookup(cn)
        self.assertIn("tg.namnh", str(stop.exception))

    def test_both_sources_coexist_neither_overwrites_the_other(self):
        """Việc 1.7. Lỗ hổng tự bắt được 21/09: 11 phép kiểm đầu tiên không phép
        nào đặt CẢ HAI nguồn trong một lượt, nên nếu nguồn 2 đè nguồn 1 thì
        chúng vẫn xanh hết.
        """
        cn = FakeConnection(
            directory_rows=[(6, "nv_hoa", 301)],
            service_rows=[(6, "svc.dms-feedback", 949)])
        got = connect.directory_account_lookup(cn)
        self.assertEqual(got, {(6, "nv_hoa"): 301, (6, "svc.dms-feedback"): 949})

    def test_conflict_across_the_two_sources_stops(self):
        """Việc 1.8. Việc 1.3 chỉ phủ xung đột NỘI BỘ `dim_user`."""
        cn = FakeConnection(directory_rows=[(6, "x", 100)],
                            service_rows=[(6, "x", 200)])
        with self.assertRaises(SystemExit) as stop:
            connect.directory_account_lookup(cn)
        self.assertIn("(6, 'x')", str(stop.exception))

    def test_null_account_is_skipped_not_stored(self):
        """`dim_user.account_id` cho phép rỗng; rỗng thì không phải một đáp án."""
        cn = FakeConnection(directory_rows=[(8, "chua_co_tai_khoan", None)])
        self.assertEqual(connect.directory_account_lookup(cn), {})

    def test_query_excludes_technical_directory_rows(self):
        """Dòng kỹ thuật mang tên `__technical_<id>__`, không ai gửi tên đó lên."""
        cn = FakeConnection()
        connect.directory_account_lookup(cn)
        dim = [s for s in cn.seen_sql if "dim_user" in s]
        self.assertTrue(any("NOT is_technical" in s for s in dim), cn.seen_sql)

    def test_query_takes_only_service_accounts_never_anchors(self):
        """Việc 1.6: `whole_agent` / `unattributed` là đích RƠI VỀ, không phải đích nhận.

        Gộp chúng vào bảng tra là biến đường rơi thành đường nhận, và bộ đếm
        `identity_unresolvable` sẽ im lặng về 0 vì không còn gì trượt được nữa.
        """
        cn = FakeConnection()
        connect.directory_account_lookup(cn)
        acc = [s for s in cn.seen_sql if "FROM account" in s]
        self.assertEqual(len(acc), 1, cn.seen_sql)
        self.assertIn("kind = 'service_account'", acc[0])
        self.assertNotIn("whole_agent", acc[0])
        self.assertNotIn("unattributed", acc[0])

    def test_query_takes_directory_rows_only_never_log_rows(self):
        """D7: dòng nhật ký KHÔNG tính là "có mặt ở agent đó".

        Đo 21/09/2026: cả 8 định danh chỉ-có-trong-nhật-ký đều mang
        `is_shared = 1` - `admin`, `guest`, `system` của Ralli; `test1`..`test4`
        và `nghiệp vụ bh1` của TLA Hợp Đồng. Không cái nào là một con người.
        """
        cn = FakeConnection()
        connect.directory_account_lookup(cn)
        dim = [s for s in cn.seen_sql if "dim_user" in s]
        self.assertEqual(len(dim), 1, cn.seen_sql)
        self.assertIn("found_in = 'directory'", dim[0])

    def test_same_shared_name_in_two_apps_stays_with_its_own_app(self):
        """Ca `admin` - ca quyết định của D7, và là lỗi cũ nếu làm sai.

        `admin` có ở TLA Hợp Đồng (agent 5) qua DANH BẠ và ở Ralli (agent 8) qua
        NHẬT KÝ. Bảng `account` gộp thành một dòng thuộc agent 5. Nếu phép tra
        nhận cả dòng nhật ký thì Ralli gửi `X-User: admin` sẽ quy vào lịch sử
        admin của TLA Hợp Đồng - đúng đường hỏng đã đo 31/08/2026.

        Ở đây dòng nhật ký của Ralli đã bị câu truy vấn loại, nên bảng tra chỉ
        còn khoá của agent 5.
        """
        cn = FakeConnection(directory_rows=[(5, "admin", 1)])
        got = connect.directory_account_lookup(cn)
        self.assertEqual(got[(5, "admin")], 1)
        self.assertNotIn((8, "admin"), got)

    def test_both_queries_normalise_the_username(self):
        """Khớp `load_org.norm()`: strip().lower(). Hai nguồn phải cùng quy ước."""
        cn = FakeConnection()
        connect.directory_account_lookup(cn)
        self.assertEqual(len([s for s in cn.seen_sql if "LOWER(TRIM(" in s]), 2,
                         cn.seen_sql)


if __name__ == "__main__":
    unittest.main()
