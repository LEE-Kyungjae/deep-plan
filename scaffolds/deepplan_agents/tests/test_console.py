#!/usr/bin/env python3
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict


SCAFFOLD_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = SCAFFOLD_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import deepplan
from deepplan_agents.console import main


class DeepPlanStateIsolation:
    def __init__(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.state_dir = self.root / ".deeplan"
        self.originals: Dict[str, Any] = {}

    def __enter__(self):
        self.originals = {
            "ROOT": deepplan.ROOT,
            "STATE_DIR": deepplan.STATE_DIR,
            "PLAN_PATH": deepplan.PLAN_PATH,
            "DECISIONS_PATH": deepplan.DECISIONS_PATH,
            "RISKS_PATH": deepplan.RISKS_PATH,
            "EVENTS_PATH": deepplan.EVENTS_PATH,
            "REVISIONS_PATH": deepplan.REVISIONS_PATH,
            "EVENT_RETENTION_LIMIT": deepplan.EVENT_RETENTION_LIMIT,
            "REVISION_RETENTION_LIMIT": deepplan.REVISION_RETENTION_LIMIT,
        }
        deepplan.ROOT = self.root
        deepplan.STATE_DIR = self.state_dir
        deepplan.PLAN_PATH = self.state_dir / "plan.json"
        deepplan.DECISIONS_PATH = self.state_dir / "decisions.jsonl"
        deepplan.RISKS_PATH = self.state_dir / "risks.jsonl"
        deepplan.EVENTS_PATH = self.state_dir / "events.jsonl"
        deepplan.REVISIONS_PATH = self.state_dir / "revisions.jsonl"
        deepplan._sync_store_paths()
        return self

    def __exit__(self, exc_type, exc, tb):
        deepplan.ROOT = self.originals["ROOT"]
        deepplan.STATE_DIR = self.originals["STATE_DIR"]
        deepplan.PLAN_PATH = self.originals["PLAN_PATH"]
        deepplan.DECISIONS_PATH = self.originals["DECISIONS_PATH"]
        deepplan.RISKS_PATH = self.originals["RISKS_PATH"]
        deepplan.EVENTS_PATH = self.originals["EVENTS_PATH"]
        deepplan.REVISIONS_PATH = self.originals["REVISIONS_PATH"]
        deepplan.EVENT_RETENTION_LIMIT = self.originals["EVENT_RETENTION_LIMIT"]
        deepplan.REVISION_RETENTION_LIMIT = self.originals["REVISION_RETENTION_LIMIT"]
        deepplan._sync_store_paths()
        self.tempdir.cleanup()


def run_console(argv):
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = main(argv)
    return code, json.loads(stdout.getvalue())


class DeepPlanAgentsConsoleTests(unittest.TestCase):
    def test_agents_lists_runnable_roles(self):
        code, payload = run_console(["agents"])

        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        roles = {item["role"]: item for item in payload["roles"]}
        self.assertIn("planner", roles)
        self.assertIn("researcher", roles)
        self.assertIn("reviewer", roles)
        self.assertIn("update_plan", roles["planner"]["allowed_actions"])
        self.assertIn("capture_evidence_cycle", roles["researcher"]["allowed_actions"])

    def test_snapshot_and_planner_run_against_in_process_workspace(self):
        with DeepPlanStateIsolation():
            snapshot_code, snapshot = run_console(["snapshot"])
            run_code, event = run_console(
                [
                    "run",
                    "--role",
                    "planner",
                    "--action",
                    "update_plan",
                    "--payload-json",
                    '{"goal":"console test goal","success_metric":"console test metric","deadline":"2026-05-31"}',
                ]
            )

        self.assertEqual(snapshot_code, 0)
        self.assertEqual(snapshot["type"], "snapshot")
        self.assertEqual(run_code, 0)
        self.assertTrue(event["ok"])
        self.assertEqual(event["type"], "planner_step")
        self.assertEqual(event["summary"]["operation"], "update_plan")
        self.assertIn("goal", event["summary"]["changed_fields"])

    def test_reviewer_cannot_run_planner_write(self):
        with DeepPlanStateIsolation():
            code, event = run_console(
                [
                    "run",
                    "--role",
                    "reviewer",
                    "--action",
                    "update_plan",
                    "--payload-json",
                    '{"goal":"denied"}',
                ]
            )

        self.assertEqual(code, 1)
        self.assertFalse(event["ok"])
        self.assertEqual(event["error"]["type"], "permission_denied")


if __name__ == "__main__":
    unittest.main()
