import csv
import tempfile
import unittest
from pathlib import Path

from db import load_provider

COLS = ["metric_alias", "gcp_project_id", "ts_ict", "model", "limit_name", "value"]
ALIAS_IN = "generate_content_paid_tier_input_token_count"
KEY = ("2026-08-30", "proj", "gemini-3-flash", "input_tokens")


def write_pull(root: Path, name: str, rows: list[tuple]) -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    with (folder / "proj.csv").open("w", encoding="utf-8", newline="") as h:
        w = csv.writer(h)
        w.writerow(COLS)
        for ts, value, *limit in rows:
            w.writerow([ALIAS_IN, "proj", ts, "gemini-3-flash", limit[0] if limit else "", value])
    return folder


class ProviderPullsTests(unittest.TestCase):
    """Every provider pull is read; a later pull never shrinks an earlier one."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_day_cut_at_the_edge_of_a_later_pull_keeps_the_full_day(self):
        a = write_pull(self.root, "2026-09-04-1h-acc", [("2026-08-30 10:00:00", "100"),
                                                        ("2026-08-30 11:00:00", "50")])
        b = write_pull(self.root, "2026-09-10-1h-acc", [("2026-08-30 11:00:00", "50")])
        with self.assertLogs("load_provider", level="WARNING") as logs:
            result, _api_requests, _warnings, errors = load_provider.merge_pulls([a, b])
        self.assertEqual(errors, [])
        self.assertEqual(result[KEY], 150)
        self.assertTrue(any("2026-08-30" in m and "150" in m and "50" in m for m in logs.output),
                        logs.output)
        self.assertTrue(any("clashes: 1" in m for m in logs.output), logs.output)

    def test_day_only_in_the_older_pull_survives(self):
        a = write_pull(self.root, "2026-09-04-1h-acc", [("2026-08-20 10:00:00", "7")])
        b = write_pull(self.root, "2026-09-10-1h-acc", [("2026-08-30 10:00:00", "9")])
        result, _, _, _ = load_provider.merge_pulls([a, b])
        self.assertEqual(result[("2026-08-20", "proj", "gemini-3-flash", "input_tokens")], 7)
        self.assertEqual(result[KEY], 9)

    def test_branch_check_still_runs_inside_each_pull(self):
        a = write_pull(self.root, "2026-09-04-1h-acc", [("2026-08-30 10:00:00", "10", "XPerDay"),
                                                        ("2026-08-30 10:00:00", "12", "XPerMinute")])
        _, _, _, errors = load_provider.merge_pulls([a])
        self.assertTrue(errors and "2026-09-04-1h-acc" in errors[0], errors)

    def test_only_account_suffixed_folders_are_provider_pulls(self):
        for name in ("2026-09-12-1m", "2026-09-04-1h", "2026-09-04-1h-acc", "2026-09-10-1m-other"):
            (self.root / name).mkdir()
        chosen = [d.name for d in load_provider.pick_pulls(self.root)]
        self.assertEqual(chosen, ["2026-09-04-1h-acc", "2026-09-10-1m-other"])
