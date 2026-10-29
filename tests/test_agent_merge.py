"""Agent gộp hiển thị: ai-chatbot-contract đọc ra dưới tên và agent_id của tla-hd."""
import unittest
from unittest.mock import patch

from backend import store

AGENTS = [dict(agent_id=5, code="tla-hd", name="Trợ Lý Ảo Hợp Đồng"),
          dict(agent_id=9, code="ai-chatbot-contract", name="TLA-HD"),
          dict(agent_id=8, code="ralli", name="Trợ lý ảo Ralli")]


class AgentMergeTests(unittest.TestCase):
    def test_merge_maps_source_to_target(self):
        with patch.object(store, "_rows", return_value=AGENTS):
            self.assertEqual(store._agent_merge(None), {9: (5, "Trợ Lý Ảo Hợp Đồng")})

    def test_missing_code_means_no_merge(self):
        with patch.object(store, "_rows", return_value=AGENTS[:1]):
            self.assertEqual(store._agent_merge(None), {})

    def test_remap_keeps_both_rows_so_totals_add_up(self):
        rows = [dict(agent_id=5, agent="Trợ Lý Ảo Hợp Đồng", total_tokens=10),
                dict(agent_id=9, agent="TLA-HD", total_tokens=20),
                dict(agent_id=8, agent="Trợ lý ảo Ralli", total_tokens=1)]
        out = store._remap_agents(rows, {9: (5, "Trợ Lý Ảo Hợp Đồng")}, "agent")
        self.assertEqual(len(out), 3)
        tla = [x for x in out if x["agent_id"] == 5]
        self.assertEqual(sum(x["total_tokens"] for x in tla), 30)
        self.assertEqual({x["agent"] for x in tla}, {"Trợ Lý Ảo Hợp Đồng"})

    def test_performance_keeps_one_latency_row_per_day_agent(self):
        codes = [dict(day="2026-10-27", agent_id=5, method="m", response_code=200, calls=3),
                 dict(day="2026-10-27", agent_id=9, method="m", response_code=200, calls=4)]
        lat = [dict(day="2026-10-27", agent_id=5, samples=2, enough_samples=0),
               dict(day="2026-10-27", agent_id=9, samples=50, enough_samples=1)]
        answers = iter([codes, lat, AGENTS])
        with patch.object(store, "_rows", side_effect=lambda *a, **k: next(answers)):
            out = store.performance(None, "%s", "2026-10-27", "2026-10-27")
        self.assertEqual(sum(x["calls"] for x in out["response_codes"] if x["agent_id"] == 5), 7)
        self.assertEqual(len(out["latency"]), 1)
        self.assertEqual(out["latency"][0]["samples"], 50)


if __name__ == "__main__":
    unittest.main()
