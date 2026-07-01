#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path


SCAFFOLD_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = SCAFFOLD_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deepplan_agents.strategy_llm import StaticStrategyProvider, run_strategy_llm


VALID_REPORT = {
    "overall_score": 82,
    "decision": "revise_before_build",
    "axes": {
        "problem_solution": 80,
        "desire_emotion": 90,
        "experience_loop": 75,
        "monetization_trigger": 85,
        "anti_generic": 80,
        "reference_insight": 80,
    },
    "emotion_drivers": ["fear/control", "upside/greed"],
    "risk_boundaries": [],
    "generic_patterns": ["dashboard"],
    "missing_fields": {"reference_insight": []},
    "risks": ["generic_llm_service_pattern"],
    "recommendations": ["Sharpen the wedge before build."],
    "research_questions": ["Which behavior data proves this wedge?"],
    "next_actions": [
        {
            "target_role": "planner",
            "action": "update_plan",
            "priority": "medium",
            "reason": "Sharpen positioning before build.",
            "payload": {"selected_option": "Reframe as pre-build product intelligence."},
        }
    ],
    "positioning_rewrite": "Reframe as pre-build product intelligence.",
    "monetization_moment": "Charge when the user avoids wasted build time.",
}


class DeepPlanStrategyLLMTests(unittest.TestCase):
    def test_run_strategy_llm_validates_provider_report(self):
        result = run_strategy_llm(
            StaticStrategyProvider(VALID_REPORT),
            payload={"idea": "AI planning checkpoint"},
            snapshot={"plan": {"goal": "Improve product strategy"}, "qa": {"result": "PASS"}, "health": {"status": "ok"}},
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["type"], "strategy_llm_report")
        self.assertEqual(result["prompt"]["schema_title"], "DeepPlanStrategyReport")
        self.assertEqual(result["report"]["decision"], "revise_before_build")

    def test_run_strategy_llm_rejects_invalid_provider_report(self):
        with self.assertRaises(ValueError) as ctx:
            run_strategy_llm(
                StaticStrategyProvider({"decision": "continue"}),
                payload={"idea": "weak"},
                snapshot={},
            )

        self.assertIn("invalid strategy report", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
