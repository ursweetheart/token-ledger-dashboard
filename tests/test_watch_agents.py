"""Phép kiểm cho service sức khỏe agent: đánh giá kết quả, cấu hình, lịch, thứ tự trong một vòng.

Không gọi mạng, không cần database. Phần transaction thật (giữ chỗ + INSERT cùng rollback) chỉ
chứng minh được trên PostgreSQL thật, nên nằm ở verification.md của change, không ở đây.

CA ĐÁNG GIÁ NHẤT

  `test_greeting_answer_is_a_failure` - ngày 29/10/2026, "hello" trả HTTP 200 + `success` sau
  0,19 giây mà không đi tới LLM. Chỉ kiểm HTTP thì phép kiểm báo khỏe mỗi ngày kể cả khi LLM chết.

  `test_queued_manual_run_goes_before_the_schedule` - xét lịch trước thì INSERT của lịch vướng index
  duy nhất do lần chạy tay đang giữ, vòng nào cũng vậy, và lần chạy tay kẹt mãi.
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import watch_agents as wa  # noqa: E402

NOW = datetime(2026, 10, 29, 1, 0, tzinfo=timezone.utc)

CAPABILITIES = {"expect": {"status": 200, "equals": {"features[id=ctda].enabled": True},
                           "days_until": {"expires_at": 30}}}
ANALYZE = {"expect": {"status": 200, "equals": {"status": "success"},
                      "not_equals": {"data.feature": "clarification"}}}


def capabilities_body(enabled=True, expires="2027-10-28T01:29:00"):
    return json.dumps({"username": "admin", "expires_at": expires,
                       "features": [{"id": "crm", "enabled": True}, {"id": "ctda", "enabled": enabled}]}).encode()


class FieldTests(unittest.TestCase):
    def test_dotted_path(self):
        self.assertEqual(wa.field({"data": {"feature": "x"}}, "data.feature"), "x")

    def test_list_filter_picks_the_matching_item(self):
        doc = json.loads(capabilities_body(enabled=False))
        self.assertIs(wa.field(doc, "features[id=ctda].enabled"), False)

    def test_missing_is_not_an_error(self):
        self.assertIs(wa.field({"a": 1}, "a.b"), wa.MISSING)
        self.assertIs(wa.field({"features": []}, "features[id=ctda].enabled"), wa.MISSING)

    def test_one_does_not_match_true(self):
        self.assertFalse(wa.same(1, True))
        self.assertTrue(wa.same(True, True))


class EvaluateTests(unittest.TestCase):
    def test_healthy_capabilities(self):
        self.assertEqual(wa.evaluate(CAPABILITIES, 200, capabilities_body(), NOW), (wa.OK, ""))

    def test_disabled_feature_fails(self):
        level, reason = wa.evaluate(CAPABILITIES, 200, capabilities_body(enabled=False), NOW)
        self.assertEqual(level, wa.FAIL)
        self.assertIn("features[id=ctda].enabled", reason)

    def test_key_expiring_soon_warns_with_days_left(self):
        soon = (NOW + timedelta(days=10)).replace(tzinfo=None).isoformat()
        level, reason = wa.evaluate(CAPABILITIES, 200, capabilities_body(expires=soon), NOW)
        self.assertEqual(level, wa.WARN)
        self.assertIn("10 days", reason)

    def test_missing_expiry_fails(self):
        body = json.dumps({"features": [{"id": "ctda", "enabled": True}]}).encode()
        self.assertEqual(wa.evaluate(CAPABILITIES, 200, body, NOW)[0], wa.FAIL)

    def test_real_analysis_passes(self):
        body = json.dumps({"status": "success", "data": {"feature": "ctda_analysis"}}).encode()
        self.assertEqual(wa.evaluate(ANALYZE, 200, body, NOW), (wa.OK, ""))

    def test_greeting_answer_is_a_failure(self):
        body = json.dumps({"status": "success", "data": {"feature": "clarification", "raw_data": {}}}).encode()
        level, reason = wa.evaluate(ANALYZE, 200, body, NOW)
        self.assertEqual(level, wa.FAIL)
        self.assertIn("clarification", reason)

    def test_rate_limit_warns(self):
        self.assertEqual(wa.evaluate(ANALYZE, 429, b"", NOW)[0], wa.WARN)

    def test_problem_details_become_the_reason_and_are_clipped(self):
        body = json.dumps({"title": "Service Unavailable", "detail": "x" * 900}).encode()
        level, reason = wa.evaluate(ANALYZE, 503, body, NOW)
        self.assertEqual(level, wa.FAIL)
        self.assertTrue(reason.startswith("HTTP 503: Service Unavailable - x"))
        self.assertEqual(len(reason), wa.REASON_MAX)

    def test_non_json_body_fails(self):
        self.assertEqual(wa.evaluate(ANALYZE, 200, b"<html>", NOW)[0], wa.FAIL)


class RunCheckTests(unittest.TestCase):
    def test_missing_key_fails_and_names_the_variable(self):
        agent = {"base_url": "https://never.invalid", "auth": {"header": "X-API-Key", "env": "TEST_ABSENT_KEY"}}
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TEST_ABSENT_KEY", None)
            with mock.patch.object(wa, "http_call") as call:
                result = wa.run_check("x", agent, {"name": "capabilities", "path": "/c"})
        call.assert_not_called()
        self.assertEqual(result["status"], wa.FAIL)
        self.assertIn("TEST_ABSENT_KEY", result["reason"])

    def test_case_keeps_question_answer_and_body(self):
        agent = {"base_url": "https://never.invalid", "auth": {"header": "X-API-Key", "env": "TEST_KEY"}}
        check = {"name": "llm", "method": "POST", "path": "/ask", "question": "Q?", "question_field": "query",
                 "answer": "data.text", **ANALYZE}
        body = json.dumps({"status": "success", "data": {"feature": "ctda_analysis", "text": "A."}}).encode()
        with mock.patch.dict(os.environ, {"TEST_KEY": "k"}), \
                mock.patch.object(wa, "http_call", return_value=(200, body, "rid", 15)):
            result = wa.run_check("x", agent, check)
        self.assertEqual((result["status"], result["question"], result["answer"]), (wa.OK, "Q?", "A."))
        self.assertEqual(result["body"]["data"]["feature"], "ctda_analysis")
        self.assertTrue(result["sent_at"].endswith("+07:00"))

    def test_health_check_does_not_keep_the_body(self):
        agent = {"base_url": "https://never.invalid", "auth": {"header": "X-API-Key", "env": "TEST_KEY"}}
        with mock.patch.dict(os.environ, {"TEST_KEY": "k"}), \
                mock.patch.object(wa, "http_call", return_value=(200, capabilities_body(), "rid", 5)):
            result = wa.run_check("x", agent, {"name": "capabilities", "path": "/c", **CAPABILITIES})
        self.assertNotIn("body", result)
        self.assertNotIn("body", wa.item(result))

    def test_question_goes_into_the_named_body_field(self):
        seen = {}

        class Response:
            status, headers = 200, {"X-Request-ID": "r"}

            def read(self, limit):
                return b"{}"

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def fake_urlopen(request, timeout):
            seen["body"] = json.loads(request.data)
            return Response()

        check = {"name": "llm", "method": "POST", "path": "/ask", "body": {"lang": "vi"},
                 "question": "Q?", "question_field": "query"}
        with mock.patch.object(wa.urllib.request, "urlopen", fake_urlopen):
            wa.http_call({"base_url": "https://x", "auth": {"header": "H", "env": "K"}}, check, "k")
        self.assertEqual(seen["body"], {"lang": "vi", "query": "Q?"})


class ConfigTests(unittest.TestCase):
    # Dict thay cho YAML: máy sạch không có PyYAML. Tệp YAML thật được kiểm ở connection_auth_cases.py.
    def agent(self, check, allow=(), **extra):
        return {"agents": {"a": {"base_url": "https://x", "auth": {"header": "X-API-Key", "env": "K"},
                                 "kind": "gateway-only", "allow_post": list(allow), "checks": [check],
                                 **extra}}}

    def test_kind_is_required(self):
        raw = self.agent({"name": "c", "path": "/c"})
        del raw["agents"]["a"]["kind"]
        with self.assertRaises(SystemExit):
            wa.check_config(raw, "t")

    def test_webapp_needs_app_url(self):
        with self.assertRaises(SystemExit):
            wa.check_config(self.agent({"name": "c", "path": "/c"}, kind="webapp"), "t")

    def test_question_needs_question_field(self):
        raw = self.agent({"name": "llm", "method": "POST", "path": "/ask", "question": "Q?"}, ["/ask"])
        with self.assertRaises(SystemExit):
            wa.check_config(raw, "t")

    def test_post_outside_allow_list_is_refused(self):
        with self.assertRaises(SystemExit) as caught:
            wa.check_config(self.agent({"name": "llm", "method": "POST", "path": "/ask"}), "t")
        self.assertIn("/ask", str(caught.exception))

    def test_post_inside_allow_list_loads(self):
        raw = self.agent({"name": "llm", "method": "POST", "path": "/ask"}, ["/ask"])
        self.assertIn("a", wa.check_config(raw, "t"))

    def test_delete_is_refused_even_when_listed(self):
        with self.assertRaises(SystemExit):
            wa.check_config(self.agent({"name": "x", "method": "DELETE", "path": "/ask"}, ["/ask"]), "t")


class ScheduleTests(unittest.TestCase):
    def test_utc_one_oclock_is_eight_in_vietnam(self):
        self.assertTrue(wa.is_due(NOW.astimezone(wa.VN), time(8, 0), None))

    def test_not_due_before_the_hour(self):
        self.assertFalse(wa.is_due(datetime(2026, 10, 29, 7, 59, tzinfo=wa.VN), time(8, 0), None))

    def test_restart_after_todays_run_does_not_run_again(self):
        self.assertFalse(wa.is_due(datetime(2026, 10, 29, 8, 5, tzinfo=wa.VN), time(8, 0), date(2026, 10, 29)))

    def test_late_start_catches_up(self):
        self.assertTrue(wa.is_due(datetime(2026, 10, 29, 9, 0, tzinfo=wa.VN), time(8, 0), date(2026, 10, 28)))


class FakeStore:
    def __init__(self, manual=None, scheduled=None):
        self.manual, self.scheduled, self.calls = manual, scheduled, []

    def take_manual(self):
        self.calls.append("take_manual")
        return self.manual

    def claim_schedule(self, now_vn):
        self.calls.append("claim_schedule")
        return self.scheduled

    def begin(self, run_id, total):
        self.calls.append(("begin", total))
        return {"run_id": run_id, "trigger": "manual", "requested_by": "test",
                "started_at": "2026-10-29T08:00:00+07:00", "finished_at": None}

    def label(self, run_id, text):
        self.calls.append(("label", text))

    def record(self, run_id, doc):
        # Phép kiểm vừa xong là phần tử cuối: AGENTS chỉ có phép kiểm health.
        latest = doc["agents"][-1]["health"][-1]
        self.calls.append(("record", latest["name"], latest["status"]))

    def finish(self, run_id, doc):
        self.calls.append("finish")
        self.doc = doc

    def interrupt(self, run_id):
        self.calls.append("interrupt")


AGENTS = {"a": {"name": "Agent A", "kind": "gateway-only", "base_url": "https://x",
                "auth": {"header": "H", "env": "K"},
                "checks": [{"name": "one", "path": "/1"},
                           {"name": "two", "method": "POST", "path": "/2"}]}}


class TickTests(unittest.TestCase):
    def setUp(self):
        # Không bao giờ ghi vào var/agent-checks thật của repo.
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.out = Path(folder.name)
        patcher = mock.patch.dict(os.environ, {"AGENT_CHECKS_DIR": str(self.out)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def ok(self, code, agent, check):
        return {**wa.blank(code, check["name"]), "status": wa.OK}

    def test_result_file_is_the_same_document_as_the_database_copy(self):
        store = FakeStore(manual="m1")
        with mock.patch.object(wa, "run_check", self.ok):
            wa.tick(store, AGENTS, NOW.astimezone(wa.VN))
        on_disk = json.loads((self.out / "m1" / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(on_disk, store.doc)
        self.assertEqual((on_disk["schema_version"], on_disk["run_id"]), (1, "m1"))
        self.assertTrue(on_disk["finished_at"])
        self.assertEqual([x["name"] for x in on_disk["agents"][0]["health"]], ["one", "two"])
        self.assertFalse((self.out / "m1" / "result.json.tmp").exists())

    def test_agent_status_is_the_worst_check(self):
        def warn_then_fail(code, agent, check):
            return {**wa.blank(code, check["name"]), "status": wa.WARN if check["name"] == "one" else wa.FAIL}
        store = FakeStore(manual="m1")
        with mock.patch.object(wa, "run_check", warn_then_fail):
            wa.tick(store, AGENTS, NOW.astimezone(wa.VN))
        self.assertEqual(store.doc["agents"][0]["status"], wa.FAIL)

    def test_unwritable_folder_keeps_the_run_and_says_why(self):
        blocker = self.out / "not-a-folder"
        blocker.write_text("x", encoding="utf-8")
        store = FakeStore(manual="m1")
        with mock.patch.dict(os.environ, {"AGENT_CHECKS_DIR": str(blocker)}), \
                mock.patch.object(wa, "run_check", self.ok):
            wa.tick(store, AGENTS, NOW.astimezone(wa.VN))
        self.assertIn("finish", store.calls)
        self.assertIn("result.json was not written", store.doc["limitations"][0])

    def test_queued_manual_run_goes_before_the_schedule(self):
        store = FakeStore(manual="m1", scheduled="s1")
        with mock.patch.object(wa, "run_check", self.ok):
            self.assertEqual(wa.tick(store, AGENTS, NOW.astimezone(wa.VN)), "m1")
        self.assertNotIn("claim_schedule", store.calls)

    def test_schedule_runs_when_nothing_is_queued(self):
        store = FakeStore(scheduled="s1")
        with mock.patch.object(wa, "run_check", self.ok):
            self.assertEqual(wa.tick(store, AGENTS, NOW.astimezone(wa.VN)), "s1")
        self.assertEqual(store.calls[:2], ["take_manual", "claim_schedule"])

    def test_nothing_due_runs_nothing(self):
        store = FakeStore()
        self.assertIsNone(wa.tick(store, AGENTS, NOW.astimezone(wa.VN)))
        self.assertNotIn("finish", store.calls)

    def test_progress_label_before_and_result_after_each_check(self):
        store = FakeStore(manual="m1")
        with mock.patch.object(wa, "run_check", self.ok):
            wa.tick(store, AGENTS, NOW.astimezone(wa.VN))
        self.assertEqual(store.calls[1:], [("begin", 2),
                                           ("label", "Agent A - one"), ("record", "one", wa.OK),
                                           ("label", "Agent A - two"), ("record", "two", wa.OK),
                                           "finish"])

    def test_one_broken_check_does_not_stop_the_next(self):
        def broken_then_ok(code, agent, check):
            if check["name"] == "one":
                raise RuntimeError("boom")
            return self.ok(code, agent, check)
        store = FakeStore(manual="m1")
        with mock.patch.object(wa, "run_check", broken_then_ok):
            wa.tick(store, AGENTS, NOW.astimezone(wa.VN))
        self.assertIn(("record", "one", wa.FAIL), store.calls)
        self.assertIn(("record", "two", wa.OK), store.calls)

    def test_database_error_marks_the_run_interrupted(self):
        store = FakeStore(manual="m1")
        store.record = mock.Mock(side_effect=RuntimeError("db gone"))
        with mock.patch.object(wa, "run_check", self.ok):
            with self.assertRaises(RuntimeError):
                wa.tick(store, AGENTS, NOW.astimezone(wa.VN))
        self.assertIn("interrupt", store.calls)


class PlanTests(unittest.TestCase):
    def test_dry_run_skips_post_and_gateway(self):
        agents = {"a": {**AGENTS["a"], "gateway_tag": "a"}}
        self.assertEqual([c["name"] for _, _, c in wa.plan(agents, dry_run=True)], ["one"])

    def test_gateway_step_follows_the_agent_checks(self):
        agents = {"a": {**AGENTS["a"], "gateway_tag": "a"}}
        steps = wa.plan(agents)
        self.assertEqual(len(steps), 3)
        self.assertIsNone(steps[-1][2])

    def test_no_gateway_step_without_a_tag(self):
        self.assertEqual(len(wa.plan(AGENTS)), 2)


if __name__ == "__main__":
    unittest.main()
