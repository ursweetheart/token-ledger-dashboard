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

    def test_two_series_in_one_pull_that_differ_only_in_resource_labels_both_count(self):
        """Measured 14/09/2026: pull 2026-08-08 was written by an older pull script that did
        not flatten res_credential_id (the field is absent), and held 7 pairs of series whose
        resource_labels_json differed only in credential_id (a real key vs apikey:UNKNOWN,
        or two keys). A key built from the flat columns saw both as the same series, kept
        one of each pair, and dropped 8 samples on 2026-05-05 for pro-tuner."""
        a = point("2026-05-05 03:30:00", 1, [0, 1])
        b = point("2026-05-05 03:30:00", 7, [0, 7])
        del a["res_credential_id"], b["res_credential_id"]
        a["resource_labels_json"] = '{"credential_id": "apikey:2f5fc44d", "method": "GenerateContent"}'
        b["resource_labels_json"] = '{"credential_id": "apikey:UNKNOWN", "method": "GenerateContent"}'
        write_pull(self.root, "2026-08-08-196d-1m", [a, b])
        summary, _ = self.run_merge()
        self.assertEqual([r["samples"] for r in read_csv(self.out)], ["8"])
        self.assertEqual(read_csv(summary["clash_file"]), [])

    def test_same_series_with_label_keys_in_another_order_is_counted_once(self):
        """The key now holds the raw label JSON. Without normalising it, two pulls that write
        the same labels in a different key order would double every day they share."""
        a = point("2026-06-01 10:00:00", 5, [0, 5])
        b = point("2026-06-01 10:00:00", 5, [0, 5])
        a["resource_labels_json"] = '{"credential_id": "apikey:1", "method": "GenerateContent"}'
        b["resource_labels_json"] = '{"method": "GenerateContent", "credential_id": "apikey:1"}'
        write_pull(self.root, "2026-09-05-196d-1m", [a])
        write_pull(self.root, "2026-09-12-196d-1m", [b])
        summary, _ = self.run_merge()
        self.assertEqual([r["samples"] for r in read_csv(self.out)], ["5"])
        self.assertEqual(read_csv(summary["clash_file"]), [])

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
