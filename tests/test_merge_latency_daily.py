import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts import merge_latency_daily as mld

OPTS = {"exponentialBuckets": {"numFiniteBuckets": 3, "growthFactor": 2, "scale": 1}}


def point(ts, count, buckets, opts=OPTS, method="GenerateContent"):
    return {"metric_type": "serviceruntime.googleapis.com/api/request_latencies",
            "gcp_project_id": "proj", "ts_utc": ts, "ts_ict": ts, "aligner": "ALIGN_DELTA",
            "res_service": "generativelanguage.googleapis.com", "res_method": method,
            "res_location": "global", "res_credential_id": "apikey:x",
            "count": str(count), "mean": 1.0, "bucketOptions": opts,
            "bucketCounts": [str(b) for b in buckets]}


def write_pull(root: Path, name: str, points: list[dict]) -> None:
    folder = root / name
    folder.mkdir(parents=True)
    with (folder / "proj.jsonl").open("w", encoding="utf-8") as h:
        for p in points:
            h.write(json.dumps(p) + "\n")


def read_csv(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8", newline="") as h:
        return list(csv.DictReader(h))


class LatencyPullsTests(unittest.TestCase):
    """Every production latency pull is read, and each point counts once."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "do_tre_phan_bo"
        self.root.mkdir()
        self.out = self.root / "latency-daily.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def run_merge(self, out=True):
        err, std = io.StringIO(), io.StringIO()
        with redirect_stderr(err), redirect_stdout(std):
            summary = mld.run(self.root, str(self.out) if out else "", by_method=False)
        return summary, err.getvalue()

    def test_several_pulls_are_no_longer_ambiguous_and_old_days_survive(self):
        write_pull(self.root, "2026-08-08-196d-1m", [point("2026-05-01 10:00:00", 2, [0, 2])])
        write_pull(self.root, "2026-09-12-196d-1m", [point("2026-06-01 10:00:00", 1, [0, 1])])
        summary, _ = self.run_merge()
        self.assertEqual(summary["folders"], ["2026-09-12-196d-1m", "2026-08-08-196d-1m"])
        self.assertEqual(sorted(r["day"] for r in read_csv(self.out)), ["2026-05-01", "2026-06-01"])

    def test_same_minute_in_two_pulls_counts_the_larger_once(self):
        write_pull(self.root, "2026-09-05-196d-1m", [point("2026-06-01 10:00:00", 4, [0, 4])])
        write_pull(self.root, "2026-09-12-196d-1m", [point("2026-06-01 10:00:00", 3, [0, 3])])
        summary, _ = self.run_merge()
        rows = read_csv(self.out)
        self.assertEqual([(r["day"], r["samples"]) for r in rows], [("2026-06-01", "4")])
        clashes = read_csv(summary["clash_file"])
        self.assertEqual(len(clashes), 1)
        self.assertEqual((clashes[0]["count_a"], clashes[0]["count_b"], clashes[0]["kept"]), ("3", "4", "4"))

    def test_identical_point_in_two_pulls_is_not_doubled(self):
        for name in ("2026-09-05-196d-1m", "2026-09-12-196d-1m"):
            write_pull(self.root, name, [point("2026-06-01 10:00:00", 5, [0, 5])])
        summary, _ = self.run_merge()
        self.assertEqual([r["samples"] for r in read_csv(self.out)], ["5"])
        self.assertEqual(read_csv(summary["clash_file"]), [])

    def test_clash_file_beside_out_always_has_a_header(self):
        write_pull(self.root, "2026-09-12-196d-1m", [point("2026-06-01 10:00:00", 1, [0, 1])])
        summary, _ = self.run_merge()
        clash = Path(summary["clash_file"])
        self.assertEqual(clash.parent, self.out.parent)
        self.assertEqual(clash.name, "latency-daily.lech.csv")
        self.assertIn("kept", clash.read_text(encoding="utf-8").splitlines()[0])

    def test_without_out_clashes_go_to_stderr(self):
        write_pull(self.root, "2026-09-05-196d-1m", [point("2026-06-01 10:00:00", 4, [0, 4])])
        write_pull(self.root, "2026-09-12-196d-1m", [point("2026-06-01 10:00:00", 3, [0, 3])])
        summary, err = self.run_merge(out=False)
        self.assertIsNone(summary["clash_file"])
        self.assertIn("CLASH", err)

    def test_second_bucket_options_still_stops(self):
        other = {"exponentialBuckets": {"numFiniteBuckets": 3, "growthFactor": 2, "scale": 2}}
        write_pull(self.root, "2026-09-12-196d-1m", [point("2026-06-01 10:00:00", 1, [0, 1]),
                                                      point("2026-06-01 10:01:00", 1, [0, 1], opts=other)])
        with self.assertRaises(SystemExit):
            self.run_merge()

    def test_folder_not_matching_the_pattern_is_skipped_and_named(self):
        write_pull(self.root, "2026-09-12-196d-1m", [point("2026-06-01 10:00:00", 1, [0, 1])])
        write_pull(self.root, "2026-09-04-60d-1h", [point("2026-06-01 10:00:00", 60, [0, 60])])
        summary, err = self.run_merge()
        self.assertEqual(summary["skipped"], ["2026-09-04-60d-1h"])
        self.assertIn("2026-09-04-60d-1h", err)
        self.assertEqual([r["samples"] for r in read_csv(self.out)], ["1"])
