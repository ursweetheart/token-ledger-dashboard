import csv
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts import merge_monitoring

COLS = ["metric_alias", "gcp_project_id", "ts_utc", "value"]


def write_pull(raw: Path, pull: str, project: str, rows: list[tuple]) -> None:
    folder = raw / pull
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / f"{project}.csv").open("w", encoding="utf-8", newline="") as h:
        w = csv.writer(h)
        w.writerow(COLS)
        for alias, ts, value in rows:
            w.writerow([alias, project, ts, value])


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as h:
        return list(csv.DictReader(h))


class MergeCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.raw = root / "raw"
        self.ra = root / "gop"
        self.raw.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def run_merge(self, dot: str = "", out: str = "out-gop"):
        buf = io.StringIO()
        with redirect_stdout(buf):
            summary = merge_monitoring.run(raw=self.raw, ra=self.ra, dot=dot, out_name=out)
        return summary, buf.getvalue()

    def merged_values(self, project="p", out="out-gop") -> dict:
        return {(r["metric_alias"], r["ts_utc"]): r["value"]
                for r in read_csv(self.ra / out / f"{project}.csv")}


class KeepTheLargerValueTests(MergeCase):
    """A later pull must never shrink an earlier one (spec: pull-merge-completeness)."""

    def test_later_pull_reports_smaller_keeps_the_larger(self):
        write_pull(self.raw, "2026-09-05-1m", "p", [("tok", "2026-06-11 00:00:00", "4406.0")])
        write_pull(self.raw, "2026-09-12-1m", "p", [("tok", "2026-06-11 00:00:00", "944.0")])
        self.run_merge()
        rows = read_csv(self.ra / "out-gop" / "p.csv")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["value"], "4406.0")

    def test_later_pull_reports_larger_keeps_the_larger(self):
        write_pull(self.raw, "2026-09-05-1m", "p", [("req", "2026-08-12 07:06:00", "5.0")])
        write_pull(self.raw, "2026-09-12-1m", "p", [("req", "2026-08-12 07:06:00", "6.0")])
        self.run_merge()
        self.assertEqual(self.merged_values(), {("req", "2026-08-12 07:06:00"): "6.0"})

    def test_key_only_in_the_older_pull_is_kept(self):
        write_pull(self.raw, "2026-08-06-1m", "p", [("tok", "2026-05-01 00:00:00", "7.0")])
        write_pull(self.raw, "2026-09-12-1m", "p", [("tok", "2026-09-01 00:00:00", "3.0")])
        self.run_merge()
        self.assertEqual(self.merged_values(), {("tok", "2026-05-01 00:00:00"): "7.0",
                                                ("tok", "2026-09-01 00:00:00"): "3.0"})

    def test_identical_rows_in_two_pulls_are_written_once(self):
        for pull in ("2026-09-05-1m", "2026-09-12-1m"):
            write_pull(self.raw, pull, "p", [("tok", "2026-06-12 00:00:00", "12.0")])
        summary, _ = self.run_merge()
        self.assertEqual(len(read_csv(self.ra / "out-gop" / "p.csv")), 1)
        self.assertEqual(summary["lech"], 0)


class ClashFileTests(MergeCase):
    """Every clash leaves a readable trace, outside the folder the loader scans."""

    def test_clash_rows_match_the_printed_count(self):
        write_pull(self.raw, "2026-09-05-1m", "p", [("tok", "2026-06-11 00:00:00", "4406.0"),
                                                    ("req", "2026-06-11 00:00:00", "2.0")])
        write_pull(self.raw, "2026-09-12-1m", "p", [("tok", "2026-06-11 00:00:00", "944.0"),
                                                    ("req", "2026-06-11 00:00:00", "1.0")])
        summary, printed = self.run_merge()
        clashes = read_csv(summary["clash_file"])
        self.assertEqual(len(clashes), 2)
        self.assertEqual(summary["lech"], 2)
        self.assertIn("value clash 2", printed)
        tok = next(r for r in clashes if r["metric_alias"] == "tok")
        self.assertEqual((tok["value_a"], tok["value_b"], tok["kept"], tok["newest_value"]),
                         ("944.0", "4406.0", "4406.0", "944.0"))

    def test_no_clash_still_writes_a_header_only_file(self):
        write_pull(self.raw, "2026-09-12-1m", "p", [("tok", "2026-06-12 00:00:00", "12.0")])
        summary, _ = self.run_merge()
        path = Path(summary["clash_file"])
        self.assertTrue(path.exists())
        with path.open(encoding="utf-8", newline="") as h:
            lines = h.read().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn("kept", lines[0])

    def test_clash_file_sits_beside_the_merged_folder_not_inside(self):
        write_pull(self.raw, "2026-09-05-1m", "p", [("tok", "2026-06-11 00:00:00", "4406.0")])
        write_pull(self.raw, "2026-09-12-1m", "p", [("tok", "2026-06-11 00:00:00", "944.0")])
        summary, _ = self.run_merge()
        clash = Path(summary["clash_file"])
        self.assertEqual(clash.parent, self.ra)
        self.assertEqual(sorted(f.name for f in (self.ra / "out-gop").iterdir()), ["p.csv"])


class PullFolderPatternTests(MergeCase):
    """Only production pull folders are merged by default (design D9)."""

    def test_hourly_and_other_account_folders_are_skipped_and_named(self):
        write_pull(self.raw, "2026-09-12-1m", "p", [("tok", "2026-09-01 10:00:00", "3.0")])
        write_pull(self.raw, "2026-09-04-1h", "p", [("tok", "2026-09-01 10:00:00", "180.0")])
        write_pull(self.raw, "2026-09-04-1h-dinhthinhan18111971", "project-e62bad30-a591-407b-ba7",
                   [("tok", "2026-08-31 19:00:00", "99.0")])
        summary, printed = self.run_merge()
        self.assertEqual(summary["batches"], ["2026-09-12-1m"])
        self.assertEqual(summary["skipped"], ["2026-09-04-1h", "2026-09-04-1h-dinhthinhan18111971"])
        self.assertIn("2026-09-04-1h-dinhthinhan18111971", printed)
        self.assertEqual(self.merged_values(), {("tok", "2026-09-01 10:00:00"): "3.0"})
        self.assertFalse((self.ra / "out-gop" / "project-e62bad30-a591-407b-ba7.csv").exists())

    def test_explicit_list_is_honoured_with_a_warning_for_odd_names(self):
        write_pull(self.raw, "2026-09-12-1m", "p", [("tok", "2026-09-01 10:00:00", "3.0")])
        write_pull(self.raw, "2026-09-04-1h", "p", [("tok", "2026-09-02 10:00:00", "180.0")])
        summary, printed = self.run_merge(dot="2026-09-12-1m,2026-09-04-1h")
        self.assertEqual(sorted(summary["batches"]), ["2026-09-04-1h", "2026-09-12-1m"])
        self.assertIn("WARNING", printed)
        self.assertIn("2026-09-04-1h", printed)
        self.assertEqual(len(self.merged_values()), 2)
