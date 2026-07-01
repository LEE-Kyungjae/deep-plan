#!/usr/bin/env python3
import importlib.util
import sys
import unittest
from pathlib import Path


SCAFFOLD_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = SCAFFOLD_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deepplan_agents.skills import registry


class DeepPlanAgentsScaffoldTests(unittest.TestCase):
    def test_load_skill_manifests_contains_expected_examples(self):
        manifests = registry.load_skill_manifests()

        self.assertIn("plan-framing", manifests)
        self.assertIn("review-triage", manifests)
        self.assertEqual(manifests["review-triage"]["role"], "reviewer")

    def test_resolve_profile_uses_local_host_action_contract(self):
        profile = registry.resolve_profile("planner")

        self.assertEqual(profile["profile"], "planner_full")
        self.assertIn("plan.write", profile["capabilities"])
        self.assertIn("update_plan", profile["allowed_actions"])

    def test_resolve_skill_assignment_uses_profile_defaults(self):
        assignment = registry.resolve_skill_assignment("reviewer")

        self.assertEqual(assignment["desired_skills"], ["review-triage", "restore-safety", "decision-closure"])
        self.assertEqual(assignment["actual_skills"], ["review-triage", "restore-safety", "decision-closure"])
        self.assertEqual(assignment["disabled_skills"], [])

    def test_resolve_skill_assignment_reports_disabled_and_missing_capability(self):
        assignment = registry.resolve_skill_assignment(
            "researcher",
            desired_skills=["evidence-capture", "restore-safety", "boundary-awareness"],
            disabled_skills=["boundary-awareness"],
        )

        self.assertEqual(assignment["actual_skills"], ["evidence-capture"])
        self.assertEqual(
            assignment["disabled_skills"],
            [
                {"name": "restore-safety", "reason": "missing_capability"},
                {"name": "boundary-awareness", "reason": "disabled_by_runtime"},
            ],
        )

    def test_build_runtime_session_returns_desired_vs_actual_shape(self):
        session = registry.build_runtime_session(
            "reviewer",
            desired_skills=["review-triage", "restore-safety"],
            disabled_skills=["restore-safety"],
        )

        self.assertEqual(session["role"], "reviewer")
        self.assertEqual(session["profile"], "reviewer_restore")
        self.assertEqual(session["desired_skills"], ["review-triage", "restore-safety"])
        self.assertEqual(session["actual_skills"], ["review-triage"])
        self.assertEqual(session["disabled_skills"], [{"name": "restore-safety", "reason": "disabled_by_runtime"}])


if __name__ == "__main__":
    unittest.main()
