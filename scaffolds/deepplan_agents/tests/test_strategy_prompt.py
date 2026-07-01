#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path


SCAFFOLD_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = SCAFFOLD_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deepplan_agents.strategy_prompt import build_strategy_prompt_bundle, compact_strategy_snapshot, load_strategy_report_schema, load_strategy_system_prompt


class DeepPlanStrategyPromptTests(unittest.TestCase):
    def test_strategy_prompt_assets_load_and_include_output_contract(self):
        prompt = load_strategy_system_prompt()
        schema = load_strategy_report_schema()
        bundle = build_strategy_prompt_bundle(
            {"idea": "AI productivity dashboard", "target_user": "solo builder"},
            {"plan": {"goal": "Evaluate ideas"}, "qa": {"result": "PASS"}, "health": {"status": "ok"}, "fingerprint": "fp"},
        )

        self.assertIn("attack an idea before execution starts", prompt)
        self.assertEqual(schema["title"], "DeepPlanStrategyReport")
        self.assertEqual(bundle["messages"][0]["role"], "system")
        self.assertIn("idea_payload", bundle["messages"][1]["content"])
        self.assertIn("required_output_schema", bundle["messages"][1]["content"])

    def test_compact_strategy_snapshot_removes_verbose_health_logs(self):
        compact = compact_strategy_snapshot(
            {
                "fingerprint": "fp",
                "plan": {"goal": "Goal", "evidence": [1, 2, 3, 4, 5, 6], "execution_tasks": ["omit"]},
                "qa": {
                    "result": "PASS",
                    "score": 10,
                    "threshold": 8,
                    "checks": [
                        {"name": "ok", "passed": True, "detail": "ok"},
                        {"name": "bad", "passed": False, "detail": "needs work", "critical": True},
                    ],
                },
                "health": {"status": "ok", "issues": [], "logs": {"too": "verbose"}},
            }
        )

        self.assertEqual(compact["fingerprint"], "fp")
        self.assertEqual(compact["plan"]["evidence"], [1, 2, 3, 4, 5])
        self.assertNotIn("execution_tasks", compact["plan"])
        self.assertEqual(compact["qa"]["failed_checks"][0]["name"], "bad")
        self.assertNotIn("logs", compact["health"])


if __name__ == "__main__":
    unittest.main()
