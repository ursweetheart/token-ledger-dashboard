import unittest

from tools import check_english_names as cen


def kinds(rel: str, source: str) -> list[str]:
    return [kind for _, _, kind, _ in cen.check_source(rel, source)]


class FileNameCase(unittest.TestCase):
    def test_english_name_passes(self):
        self.assertEqual(kinds("tools/diagnostics/verify_datasets.py", "x = 1\n"), [])

    def test_vietnamese_name_fails(self):
        self.assertEqual(kinds("tools/kiem_tra_moi.py", "x = 1\n"), ["file name"])  # vi-ok: fixture

    def test_migration_folder_is_not_scanned(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "db" / "migrations" / "versions").mkdir(parents=True)
            (root / "db" / "migrations" / "versions" / "013_nhip_moi.py").write_text("x = 1\n", encoding="utf-8")
            (root / "db" / "load_ok.py").write_text("x = 1\n", encoding="utf-8")
            self.assertEqual(cen.scan(root, ["db"]), [])


class FlagCase(unittest.TestCase):
    def test_english_flag_passes(self):
        src = "p.add_argument('--skip-monitoring', action='store_true')\n"
        self.assertEqual(kinds("a.py", src), [])

    def test_vietnamese_flag_fails(self):
        src = "p.add_argument('--bo-qua', action='store_true')\n"
        self.assertEqual(kinds("a.py", src), ["cli flag"])

    def test_parser_without_allow_abbrev_fails(self):
        self.assertEqual(kinds("a.py", "import argparse\np = argparse.ArgumentParser()\n"),
                         ["parser allows abbreviations"])

    def test_parser_with_allow_abbrev_false_passes(self):
        src = "import argparse\np = argparse.ArgumentParser(description='x', allow_abbrev=False)\n"
        self.assertEqual(kinds("a.py", src), [])


class IdentifierCase(unittest.TestCase):
    def test_function_name_fails(self):
        self.assertEqual(kinds("a.py", "def gop_cac_lan_keo():\n    pass\n"), ["identifier"])  # vi-ok: fixture

    def test_attribute_and_keyword_fail(self):
        src = "self.ra = 1\nrun(ra=2)\n"  # vi-ok: fixture
        self.assertEqual(kinds("a.py", src), ["identifier", "identifier"])

    def test_english_identifiers_pass(self):
        src = "def merge_pulls(out_root, batches):\n    clash = out_root\n    return clash\n"
        self.assertEqual(kinds("a.py", src), [])


class StringCase(unittest.TestCase):
    def test_accented_error_fails(self):
        self.assertEqual(kinds("a.py", "raise ValueError('Thiếu tệp')\n"),  # vi-ok: fixture
                         ["string (accents)"])

    def test_unaccented_words_fail(self):
        self.assertEqual(kinds("a.py", "print('khong tim thay tep')\n"),  # vi-ok: fixture
                         ["string (words)"])

    def test_single_vietnamese_word_passes(self):
        self.assertEqual(kinds("a.py", "print('gateway ra')\n"), [])

    def test_fstring_is_checked_as_one_text(self):
        src = "print(f'{n} dong bi lech')\n"  # vi-ok: fixture
        self.assertEqual(kinds("a.py", src), ["string (words)"])

    def test_docstring_comment_and_bare_string_pass(self):
        src = (
            '"""Tài liệu tiếng Việt."""\n'  # vi-ok: fixture
            "# chú thích có dấu\n"  # vi-ok: fixture
            "def f():\n"
            '    """Hàm này kiểm dữ liệu."""\n'  # vi-ok: fixture
            '    "chuỗi đứng một mình dùng như comment"\n'  # vi-ok: fixture
            "    return 1\n"
        )
        self.assertEqual(kinds("a.py", src), [])

    def test_sql_comment_inside_sql_passes(self):
        src = 'Q = """\nSELECT a  -- cột này đếm lượt\nFROM t\n"""\n'  # vi-ok: fixture
        self.assertEqual(kinds("a.py", src), [])

    def test_vietnamese_outside_sql_comment_still_fails(self):
        src = "Q = \"SELECT 'Phòng Kế toán' FROM t\"\n"  # vi-ok: fixture
        self.assertEqual(kinds("a.py", src), ["string (accents)"])

    def test_double_dash_outside_sql_is_not_stripped(self):
        self.assertEqual(kinds("a.py", "print('0 findings -- đạt')\n"),  # vi-ok: fixture
                         ["string (accents)"])


class MarkerCase(unittest.TestCase):
    def test_marker_with_reason_passes(self):
        src = "MSG = 'Sổ Gateway chưa được làm mới'  # vi-ok: dashboard text\n"  # vi-ok: fixture
        self.assertEqual(kinds("a.py", src), [])

    def test_marker_inside_multiline_string_passes(self):
        src = (
            "MSG = (\n"
            "    'dòng một '\n"  # vi-ok: fixture
            "    'dòng hai'  # vi-ok: dashboard text\n"  # vi-ok: fixture
            ")\n"
        )
        self.assertEqual(kinds("a.py", src), [])

    def test_marker_without_reason_fails(self):
        src = "MSG = 'Thiếu khoá'  # vi-ok:\n"  # vi-ok: fixture
        self.assertEqual(sorted(kinds("a.py", src)), ["string (accents)", "vi-ok without reason"])


if __name__ == "__main__":
    unittest.main()
