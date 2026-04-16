#!/usr/bin/env python3
import io
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import deepplan
from deepplan_host_contract import host_action_contract, required_capabilities_for_action, role_has_action_capabilities
from deepplan_sdk import DeepPlanClient as PackagedDeepPlanClient
from deepplan_client import DeepPlanClient, DeepPlanClientError, DeepPlanClientOperationError, DeepPlanConflictError, DeepPlanHealthGateError
from deepplan_server import DeepPlanHandler


EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))
_PLANNER_HOST_SPEC = importlib.util.spec_from_file_location("deepplan_planner_host_example", EXAMPLES_DIR / "deepplan_planner_host.py")
assert _PLANNER_HOST_SPEC and _PLANNER_HOST_SPEC.loader
_PLANNER_HOST_MODULE = importlib.util.module_from_spec(_PLANNER_HOST_SPEC)
_PLANNER_HOST_SPEC.loader.exec_module(_PLANNER_HOST_MODULE)
PlannerHostStep = _PLANNER_HOST_MODULE.PlannerHostStep


class DeepPlanStateIsolation:
    def __init__(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.state_dir = self.root / ".deeplan"
        self.originals = {}

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
        self.tempdir.cleanup()


def build_handler(method: str, path: str, body: bytes = b"", headers=None) -> DeepPlanHandler:
    handler = DeepPlanHandler.__new__(DeepPlanHandler)
    handler.command = method
    handler.path = path
    handler.headers = {"Content-Length": str(len(body)), **(headers or {})}
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()
    handler._status = None
    handler._sent_headers = {}
    handler.send_response = lambda status, message=None: setattr(handler, "_status", status)
    handler.send_header = lambda key, value: handler._sent_headers.__setitem__(key, value)
    handler.end_headers = lambda: None
    return handler


def handler_transport(method: str, path: str, body=None, headers=None):
    raw_body = json.dumps(body).encode("utf-8") if body is not None else b""
    handler = build_handler(method, path, body=raw_body, headers=headers)
    if method == "GET":
        handler.do_GET()
    else:
        handler.do_POST()
    payload = json.loads(handler.wfile.getvalue().decode("utf-8"))
    return handler._status, payload, handler._sent_headers


class DeepPlanClientTests(unittest.TestCase):
    def test_deepplan_sdk_package_exports_client_surface(self):
        self.assertIs(PackagedDeepPlanClient, DeepPlanClient)

    def test_get_plan_tracks_fingerprint(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            result = client.get_plan()

        self.assertTrue(result["ok"])
        self.assertEqual(client.tracked_fingerprint, result["fingerprint"])

    def test_get_cycle_returns_integrated_snapshot_and_tracks_fingerprint(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            seed = deepplan.mutate_plan_state(
                lambda plan: plan.update(
                    {
                        "goal": "client cycle",
                        "success_metric": "Reach 2 pilots",
                        "deadline": "2026-04-03",
                    }
                ),
                revision_source="test_client_cycle",
            )
            client = DeepPlanClient(transport=handler_transport)
            result = client.get_cycle(history_limit=1)

        self.assertEqual(result["result_type"], "cycle")
        self.assertEqual(result["plan"]["goal"], "client cycle")
        self.assertIn("score", result["qa"])
        self.assertIn("status", result["health"])
        self.assertEqual(result["history_limit"], 1)
        self.assertEqual(len(result["history"]), 1)
        self.assertEqual(client.tracked_fingerprint, deepplan.plan_fingerprint(seed))

    def test_get_host_action_contract_returns_shared_contract(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            result = client.get_host_action_contract(role="researcher")

        self.assertEqual(result["role"], "researcher")
        self.assertEqual(result["profile"], "researcher_capture")
        self.assertEqual(result["allowed_actions"], host_action_contract("researcher")["allowed_actions"])
        self.assertEqual(result["capabilities"], host_action_contract("researcher")["capabilities"])
        self.assertEqual(result["actions"], host_action_contract("researcher")["actions"])
        self.assertIn("contract_path", result)
        action_map = {item["action"]: item for item in result["actions"]}
        self.assertEqual(action_map["capture_evidence_cycle"]["required_capabilities"], ["evidence.append_and_replan"])

    def test_host_contract_capability_helpers_reflect_role_permissions(self):
        self.assertEqual(required_capabilities_for_action("planner", "update_plan"), ["plan.write"])
        self.assertTrue(role_has_action_capabilities("planner", "update_plan"))
        self.assertFalse(role_has_action_capabilities("reviewer", "update_plan"))
        self.assertTrue(role_has_action_capabilities("reviewer", "preview_restore_previous"))

    def test_get_contracts_returns_catalog(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            result = client.get_contracts()

        self.assertTrue(result["ok"])
        self.assertEqual(result["result_type"], "contracts")
        self.assertEqual(result["contract_version"], deepplan.CONTRACT_VERSION)
        self.assertIn("stability_levels", result)
        self.assertIn("summary", result)
        self.assertGreaterEqual(result["summary"]["experimental_contract_count"], 1)
        self.assertIn("http_api", result["contracts"])
        self.assertIn("profile_summary", result["contracts"]["host_action_contract"])
        self.assertIn("conformance_manifest", result["contracts"])

    def test_get_doctor_returns_readiness_report(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            result = client.get_doctor()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["contract_version"], deepplan.CONTRACT_VERSION)
        self.assertIn("checks", result)
        self.assertIn("check_summary", result)
        self.assertEqual(result["check_summary"]["fail"], 0)
        self.assertGreaterEqual(result["check_summary"]["warn"], 1)
        self.assertIn("schema_drift", result)
        self.assertIn("tool_schema", result)
        self.assertIn("host_action_contract", result)

    def test_update_plan_uses_tracked_fingerprint(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            client.get_plan()
            result = client.update_plan(
                {
                    "goal": "client update",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                }
            )

        self.assertEqual(result["plan"]["goal"], "client update")
        self.assertEqual(client.tracked_fingerprint, result["fingerprint"])

    def test_restore_previous_works_through_client(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            first = client.update_plan(
                {
                    "goal": "client previous first",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                }
            )
            second = client.update_plan({"goal": "client previous second"})
            preview = client.preview_restore(previous=True)
            restored = client.restore_revision(previous=True, expected_fingerprint=second["fingerprint"])

        self.assertEqual(preview["selected_via"], "previous")
        self.assertEqual(preview["metadata"]["goal"], "client previous first")
        self.assertEqual(restored["plan"]["goal"], "client previous first")
        self.assertNotEqual(first["fingerprint"], second["fingerprint"])

    def test_capture_evidence_cycle_returns_typed_multi_step_result(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            client.update_plan(
                {
                    "goal": "client evidence cycle",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                }
            )
            result = client.capture_evidence_cycle(
                {
                    "claim": "Repeated pilot friction",
                    "source": "pilot-call",
                    "confidence": 74,
                    "axis": "market",
                },
                replan_payload={"plan_task": "Tighten onboarding loop"},
                history_limit=2,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["operation"], "capture_evidence_cycle")
        self.assertEqual(result["result_type"], "planning_cycle")
        self.assertNotEqual(result["pre_fingerprint"], result["post_fingerprint"])
        self.assertIn("evidence", result["changed_fields"])
        self.assertIn("plan_tasks", result["changed_fields"])
        self.assertEqual(result["evidence_result"]["plan"]["evidence"][-1]["claim"], "Repeated pilot friction")
        self.assertEqual(result["replan_result"]["plan"]["plan_tasks"][-1], "Tighten onboarding loop")
        self.assertEqual(result["post_cycle"]["plan"]["evidence"][-1]["source"], "pilot-call")
        self.assertEqual(result["post_cycle"]["history_limit"], 2)
        self.assertEqual(client.tracked_fingerprint, result["post_fingerprint"])
        self.assertIn("add_evidence", result["step_results"])
        self.assertIn("replan", result["step_results"])

    def test_capture_evidence_cycle_reuses_idempotency_key_without_duplicate_steps(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            client.update_plan(
                {
                    "goal": "idempotent capture evidence cycle",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                }
            )
            first = client.capture_evidence_cycle(
                {
                    "claim": "Repeated onboarding dropoff",
                    "source": "pilot-call",
                    "confidence": 76,
                    "axis": "market",
                },
                replan_payload={"plan_task": "Tighten onboarding loop"},
                history_limit=2,
                idempotency_key="capture-1",
            )
            second = client.capture_evidence_cycle(
                {
                    "claim": "Repeated onboarding dropoff",
                    "source": "pilot-call",
                    "confidence": 76,
                    "axis": "market",
                },
                replan_payload={"plan_task": "Tighten onboarding loop"},
                history_limit=2,
                idempotency_key="capture-1",
            )

        self.assertEqual(first["idempotency_key"], "capture-1")
        self.assertEqual(second["idempotency_key"], "capture-1")
        self.assertFalse(first["evidence_result"]["idempotency_replayed"])
        self.assertFalse(first["replan_result"]["idempotency_replayed"])
        self.assertTrue(second["evidence_result"]["idempotency_replayed"])
        self.assertTrue(second["replan_result"]["idempotency_replayed"])
        self.assertEqual(first["post_fingerprint"], second["post_fingerprint"])
        evidence_claims = [item["claim"] for item in second["post_cycle"]["plan"]["evidence"] if item.get("claim") == "Repeated onboarding dropoff"]
        self.assertEqual(len(evidence_claims), 1)
        self.assertEqual(second["post_cycle"]["plan"]["plan_tasks"].count("Tighten onboarding loop"), 1)

    def test_apply_and_get_cycle_wraps_update_plan_with_post_cycle_snapshot(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            result = client.apply_and_get_cycle(
                "update_plan",
                {
                    "goal": "wrapped update",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                },
                history_limit=1,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["operation"], "update_plan")
        self.assertEqual(result["mutation_result"]["plan"]["goal"], "wrapped update")
        self.assertEqual(result["post_cycle"]["plan"]["goal"], "wrapped update")
        self.assertEqual(result["post_cycle"]["history_limit"], 1)
        self.assertEqual(client.tracked_fingerprint, result["post_fingerprint"])

    def test_apply_and_get_cycle_wraps_restore_revision_with_post_cycle_snapshot(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            first = client.update_plan(
                {
                    "goal": "wrapped restore first",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                }
            )
            second = client.update_plan({"goal": "wrapped restore second"})
            result = client.apply_and_get_cycle(
                "restore_revision",
                {"previous": True},
                expected_fingerprint=second["fingerprint"],
                history_limit=1,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["operation"], "restore_revision")
        self.assertEqual(result["mutation_result"]["plan"]["goal"], "wrapped restore first")
        self.assertEqual(result["post_cycle"]["plan"]["goal"], "wrapped restore first")
        self.assertEqual(result["post_cycle"]["history_limit"], 1)
        self.assertEqual(client.tracked_fingerprint, result["post_fingerprint"])
        self.assertNotEqual(first["fingerprint"], second["fingerprint"])

    def test_apply_and_get_cycle_surfaces_typed_operation_error(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            with self.assertRaises(DeepPlanClientOperationError) as ctx:
                client.apply_and_get_cycle("add_evidence", {"claim": " "})

        self.assertEqual(ctx.exception.operation, "add_evidence")
        self.assertEqual(ctx.exception.step, "mutation")
        self.assertEqual(ctx.exception.status, 400)
        self.assertEqual(ctx.exception.payload["error"], "claim is required")
        self.assertEqual(ctx.exception.payload["error_code"], "invalid_request")
        self.assertFalse(ctx.exception.cause.retryable)

    def test_stale_fingerprint_raises_typed_conflict_error(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            first = client.get_plan()
            client.update_plan(
                {
                    "goal": "fresh write",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                }
            )
            with self.assertRaises(DeepPlanConflictError) as ctx:
                client.update_plan({"goal": "stale write"}, expected_fingerprint=first["fingerprint"])

        self.assertEqual(ctx.exception.status, 412)
        self.assertEqual(ctx.exception.payload["error"], "plan fingerprint mismatch")
        self.assertEqual(ctx.exception.error_code, "plan_fingerprint_mismatch")
        self.assertEqual(ctx.exception.expected_fingerprint, first["fingerprint"])
        self.assertTrue(ctx.exception.current_fingerprint)
        self.assertTrue(ctx.exception.can_refresh)

    def test_apply_and_get_cycle_surfaces_typed_conflict_error_with_operation_context(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            initial = client.get_plan()
            client.update_plan(
                {
                    "goal": "conflict baseline",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                }
            )
            with self.assertRaises(DeepPlanConflictError) as ctx:
                client.apply_and_get_cycle(
                    "update_plan",
                    {"goal": "stale wrapped update"},
                    expected_fingerprint=initial["fingerprint"],
                )

        self.assertEqual(ctx.exception.operation, "update_plan")
        self.assertEqual(ctx.exception.step, "mutation")
        self.assertEqual(ctx.exception.status, 412)
        self.assertEqual(ctx.exception.error_code, "plan_fingerprint_mismatch")
        self.assertEqual(ctx.exception.expected_fingerprint, initial["fingerprint"])
        self.assertTrue(ctx.exception.current_fingerprint)

    def test_apply_and_get_cycle_with_retry_recovers_from_stale_fingerprint_once(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            initial = client.get_plan()
            client.update_plan(
                {
                    "goal": "retry baseline",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                }
            )
            result = client.apply_and_get_cycle_with_retry(
                "update_plan",
                {"goal": "retry recovered"},
                expected_fingerprint=initial["fingerprint"],
                history_limit=1,
            )

        self.assertTrue(result["ok"])
        self.assertTrue(result["retried"])
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["operation"], "update_plan")
        self.assertEqual(result["post_cycle"]["plan"]["goal"], "retry recovered")
        self.assertEqual(result["retry_from_fingerprint"], initial["fingerprint"])
        self.assertTrue(result["retry_to_fingerprint"])
        self.assertEqual(client.tracked_fingerprint, result["post_fingerprint"])

    def test_apply_and_get_cycle_with_retry_recovers_restore_revision_once(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            initial = client.get_plan()
            client.update_plan(
                {
                    "goal": "retry restore first",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                }
            )
            latest = client.update_plan({"goal": "retry restore second"})
            result = client.apply_and_get_cycle_with_retry(
                "restore_revision",
                {"previous": True},
                expected_fingerprint=initial["fingerprint"],
                history_limit=1,
            )

        self.assertTrue(result["ok"])
        self.assertTrue(result["retried"])
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["operation"], "restore_revision")
        self.assertEqual(result["post_cycle"]["plan"]["goal"], "retry restore first")
        self.assertEqual(result["retry_from_fingerprint"], initial["fingerprint"])
        self.assertTrue(result["retry_to_fingerprint"])
        self.assertNotEqual(latest["fingerprint"], result["post_fingerprint"])

    def test_apply_and_get_cycle_with_retry_does_not_retry_validation_error(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            with self.assertRaises(DeepPlanClientOperationError) as ctx:
                client.apply_and_get_cycle_with_retry("add_evidence", {"claim": " "})

        self.assertEqual(ctx.exception.operation, "add_evidence")
        self.assertEqual(ctx.exception.step, "mutation")
        self.assertEqual(ctx.exception.status, 400)

    def test_apply_and_get_cycle_with_retry_does_not_retry_add_evidence_by_default(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            initial = client.get_plan()
            client.update_plan(
                {
                    "goal": "retry add evidence baseline",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                }
            )
            with self.assertRaises(DeepPlanConflictError) as ctx:
                client.apply_and_get_cycle_with_retry(
                    "add_evidence",
                    {"claim": "Pilot friction repeated", "source": "pilot-call", "confidence": 74},
                    expected_fingerprint=initial["fingerprint"],
                )

        self.assertEqual(ctx.exception.operation, "add_evidence")
        self.assertEqual(ctx.exception.step, "mutation")
        self.assertEqual(ctx.exception.expected_fingerprint, initial["fingerprint"])

    def test_apply_and_get_cycle_with_retry_can_opt_in_for_add_evidence(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            initial = client.get_plan()
            client.update_plan(
                {
                    "goal": "retry add evidence opt-in",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                }
            )
            result = client.apply_and_get_cycle_with_retry(
                "add_evidence",
                {"claim": "Opt-in retry evidence", "source": "pilot-call", "confidence": 74},
                expected_fingerprint=initial["fingerprint"],
                allow_non_idempotent_retry=True,
            )

        self.assertTrue(result["ok"])
        self.assertTrue(result["retried"])
        self.assertEqual(result["operation"], "add_evidence")
        self.assertEqual(result["post_cycle"]["plan"]["evidence"][-1]["claim"], "Opt-in retry evidence")
        self.assertTrue(result["mutation_result"]["idempotency_key"].startswith("add_evidence_"))

    def test_add_evidence_idempotency_key_replays_without_duplicate_write(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            first = client.add_evidence(
                {"claim": "Idempotent evidence", "source": "pilot-call", "confidence": 71},
                idempotency_key="client-evidence-1",
            )
            second = client.add_evidence(
                {"claim": "Idempotent evidence", "source": "pilot-call", "confidence": 71},
                idempotency_key="client-evidence-1",
            )

        self.assertFalse(first["idempotency_replayed"])
        self.assertTrue(second["idempotency_replayed"])
        self.assertEqual(len(second["plan"]["evidence"]), 1)
        self.assertEqual(first["fingerprint"], second["fingerprint"])

    def test_apply_and_get_cycle_with_retry_injects_idempotency_key_for_add_evidence_opt_in(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client = DeepPlanClient(transport=handler_transport)
            initial = client.update_plan(
                {
                    "goal": "auto key evidence retry",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                }
            )
            deepplan.mutate_plan_state(
                lambda plan: plan.update({"review_cadence": "weekly"}),
                expected_fingerprint=initial["fingerprint"],
                revision_source="test_auto_key_conflict",
            )
            result = client.apply_and_get_cycle_with_retry(
                "add_evidence",
                {"claim": "Auto-key evidence", "source": "pilot-call", "confidence": 70},
                expected_fingerprint=initial["fingerprint"],
                allow_non_idempotent_retry=True,
            )

        self.assertTrue(result["retried"])
        self.assertTrue(result["mutation_result"]["idempotency_key"].startswith("add_evidence_"))
        matching_claims = [item for item in result["post_cycle"]["plan"]["evidence"] if item.get("claim") == "Auto-key evidence"]
        self.assertEqual(len(matching_claims), 1)

    def test_apply_and_get_cycle_can_block_on_degraded_health(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            deepplan.EVENTS_PATH.write_text('{"type":"ok"}\nnot-json\n', encoding="utf-8")
            client = DeepPlanClient(transport=handler_transport)
            with self.assertRaises(DeepPlanHealthGateError) as ctx:
                client.apply_and_get_cycle(
                    "update_plan",
                    {
                        "goal": "blocked by health",
                        "success_metric": "Reach 2 pilots",
                        "deadline": "2026-04-03",
                    },
                    require_healthy=True,
                )
            plan = deepplan.load_plan()

        self.assertEqual(ctx.exception.operation, "update_plan")
        self.assertEqual(ctx.exception.step, "preflight")
        self.assertEqual(ctx.exception.status, "degraded")
        self.assertEqual(plan["goal"], "")

    def test_apply_and_get_cycle_allows_write_when_health_gate_disabled(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            deepplan.EVENTS_PATH.write_text('{"type":"ok"}\nnot-json\n', encoding="utf-8")
            client = DeepPlanClient(transport=handler_transport)
            result = client.apply_and_get_cycle(
                "update_plan",
                {
                    "goal": "allowed on degraded health",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                },
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["post_cycle"]["plan"]["goal"], "allowed on degraded health")

    def test_capture_evidence_cycle_with_retry_recovers_multi_agent_conflict(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            writer = DeepPlanClient(transport=handler_transport)
            stale_actor = DeepPlanClient(transport=handler_transport)
            initial = stale_actor.update_plan(
                {
                    "goal": "multi-agent cycle baseline",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                }
            )
            writer.update_plan({"review_cadence": "weekly"})
            result = stale_actor.capture_evidence_cycle(
                {
                    "claim": "Shared customer blocker",
                    "source": "pilot-call",
                    "confidence": 75,
                },
                replan_payload={"plan_task": "Revisit onboarding path"},
                expected_fingerprint=initial["fingerprint"],
                allow_retry=True,
            )

        self.assertTrue(result["ok"])
        self.assertTrue(result["retried"])
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["retry_from_fingerprint"], initial["fingerprint"])
        self.assertTrue(result["retry_to_fingerprint"])
        self.assertEqual(result["post_cycle"]["plan"]["evidence"][-1]["claim"], "Shared customer blocker")
        self.assertEqual(result["post_cycle"]["plan"]["plan_tasks"][-1], "Revisit onboarding path")
        self.assertEqual(stale_actor.tracked_fingerprint, result["post_fingerprint"])

    def test_planner_host_exposes_action_contract(self):
        host = PlannerHostStep(adapter=None)  # type: ignore[arg-type]

        contract = host.action_contract()

        self.assertEqual(contract["version"], "v1")
        self.assertEqual(contract["role"], "planner")
        self.assertEqual(contract["profile"], "planner_full")
        self.assertIn("input_schema", contract)
        self.assertIn("allowed_actions", contract)
        self.assertIn("capabilities", contract)
        action_names = [item["action"] for item in contract["actions"]]
        self.assertIn("update_plan", action_names)
        self.assertIn("capture_evidence_cycle", action_names)
        self.assertIn("restore_previous", action_names)
        self.assertIn("update_plan", contract["allowed_actions"])
        self.assertIn("plan.write", contract["capabilities"])

    def test_planner_host_update_plan_action_can_retry_stale_conflict(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            client_a = DeepPlanClient(transport=handler_transport)
            client_b = DeepPlanClient(transport=handler_transport)
            host = PlannerHostStep(adapter=_PLANNER_HOST_MODULE.DeepPlanKernelAdapter(client_b))
            initial = client_a.get_plan()
            client_a.update_plan(
                {
                    "goal": "fresh host baseline",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                }
            )
            event = host.run(
                {
                    "action": "update_plan",
                    "payload": {"goal": "host recovered update"},
                    "options": {
                        "expected_fingerprint": initial["fingerprint"],
                        "allow_retry": True,
                        "history_limit": 1,
                    },
                }
            )

        self.assertEqual(event["type"], "plan_update_applied")
        self.assertEqual(event["action"], "update_plan")
        self.assertTrue(event["result"]["retried"])
        self.assertEqual(event["result"]["post_cycle"]["plan"]["goal"], "host recovered update")
        self.assertEqual(event["summary"]["retried"], True)

    def test_planner_host_capture_evidence_cycle_can_retry_stale_conflict(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            writer = DeepPlanClient(transport=handler_transport)
            actor = DeepPlanClient(transport=handler_transport)
            host = PlannerHostStep(adapter=_PLANNER_HOST_MODULE.DeepPlanKernelAdapter(actor))
            initial = actor.update_plan(
                {
                    "goal": "host cycle baseline",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                }
            )
            writer.update_plan({"review_cadence": "weekly"})
            event = host.run(
                {
                    "action": "capture_evidence_cycle",
                    "payload": {
                        "evidence": {
                            "claim": "Planner host recovered evidence",
                            "source": "pilot-call",
                            "confidence": 74,
                        },
                        "replan": {"plan_task": "Retune follow-up flow"},
                    },
                    "options": {
                        "expected_fingerprint": initial["fingerprint"],
                        "allow_retry": True,
                        "history_limit": 1,
                    },
                }
            )

        self.assertEqual(event["type"], "evidence_cycle_applied")
        self.assertEqual(event["action"], "capture_evidence_cycle")
        self.assertTrue(event["result"]["retried"])
        self.assertEqual(event["result"]["post_cycle"]["plan"]["evidence"][-1]["claim"], "Planner host recovered evidence")
        self.assertEqual(event["result"]["post_cycle"]["plan"]["plan_tasks"][-1], "Retune follow-up flow")

    def test_planner_host_run_event_returns_invalid_action_taxonomy(self):
        host = PlannerHostStep(adapter=_PLANNER_HOST_MODULE.DeepPlanKernelAdapter(DeepPlanClient(transport=handler_transport)))

        event = host.run_event({"action": "unknown_action"})

        self.assertFalse(event["ok"])
        self.assertEqual(event["type"], "invalid_action")
        self.assertEqual(event["action"], "unknown_action")
        self.assertEqual(event["error"]["type"], "invalid_action")
        self.assertEqual(event["error"]["error_code"], "invalid_action")
        self.assertFalse(event["error"]["retryable"])

    def test_planner_host_run_event_returns_permission_denied_taxonomy(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            host = PlannerHostStep(
                adapter=_PLANNER_HOST_MODULE.DeepPlanKernelAdapter(DeepPlanClient(transport=handler_transport)),
                role="researcher",
            )
            event = host.run_event(
                {
                    "action": "restore_previous",
                    "options": {"history_limit": 1},
                }
            )

        self.assertFalse(event["ok"])
        self.assertEqual(event["type"], "permission_denied")
        self.assertEqual(event["action"], "restore_previous")
        self.assertEqual(event["error"]["type"], "permission_denied")
        self.assertEqual(event["error"]["error_code"], "permission_denied")
        self.assertFalse(event["error"]["retryable"])
        self.assertIn("needs plan.restore", event["error"]["message"])

    def test_planner_host_run_event_returns_health_gate_taxonomy(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            deepplan.EVENTS_PATH.write_text('{"type":"ok"}\nnot-json\n', encoding="utf-8")
            host = PlannerHostStep(adapter=_PLANNER_HOST_MODULE.DeepPlanKernelAdapter(DeepPlanClient(transport=handler_transport)))
            event = host.run_event(
                {
                    "action": "update_plan",
                    "payload": {
                        "goal": "blocked host update",
                        "success_metric": "Reach 2 pilots",
                        "deadline": "2026-04-03",
                    },
                    "options": {"require_healthy": True},
                }
            )

        self.assertFalse(event["ok"])
        self.assertEqual(event["type"], "health_gate")
        self.assertEqual(event["error"]["type"], "health_gate")
        self.assertEqual(event["error"]["error_code"], "health_gate_blocked")
        self.assertFalse(event["error"]["retryable"])
        self.assertEqual(event["error"]["operation"], "update_plan")

    def test_planner_host_run_event_returns_conflict_taxonomy(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            writer = DeepPlanClient(transport=handler_transport)
            actor = DeepPlanClient(transport=handler_transport)
            host = PlannerHostStep(adapter=_PLANNER_HOST_MODULE.DeepPlanKernelAdapter(actor))
            initial = actor.update_plan(
                {
                    "goal": "host conflict baseline",
                    "success_metric": "Reach 2 pilots",
                    "deadline": "2026-04-03",
                }
            )
            writer.update_plan({"review_cadence": "weekly"})
            event = host.run_event(
                {
                    "action": "capture_evidence_cycle",
                    "payload": {
                        "evidence": {
                            "claim": "stale host evidence",
                            "source": "pilot-call",
                            "confidence": 72,
                        },
                        "replan": {"plan_task": "stale host follow-up"},
                    },
                    "options": {"expected_fingerprint": initial["fingerprint"]},
                }
            )

        self.assertFalse(event["ok"])
        self.assertEqual(event["type"], "conflict")
        self.assertEqual(event["error"]["type"], "conflict")
        self.assertEqual(event["error"]["error_code"], "plan_fingerprint_mismatch")
        self.assertTrue(event["error"]["retryable"])
        self.assertEqual(event["error"]["operation"], "capture_evidence_cycle")
        self.assertEqual(event["error"]["step"], "add_evidence")
        self.assertEqual(event["error"]["expected_fingerprint"], initial["fingerprint"])
        self.assertTrue(event["error"]["current_fingerprint"])

    def test_planner_host_multi_role_sequence_preserves_shared_plan_state(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            planner = PlannerHostStep(adapter=_PLANNER_HOST_MODULE.DeepPlanKernelAdapter(DeepPlanClient(transport=handler_transport)), role="planner")
            researcher = PlannerHostStep(adapter=_PLANNER_HOST_MODULE.DeepPlanKernelAdapter(DeepPlanClient(transport=handler_transport)), role="researcher")
            reviewer = PlannerHostStep(adapter=_PLANNER_HOST_MODULE.DeepPlanKernelAdapter(DeepPlanClient(transport=handler_transport)), role="reviewer")

            plan_event = planner.run_event(
                {
                    "action": "update_plan",
                    "payload": {
                        "goal": "Narrow onboarding bottleneck",
                        "success_metric": "Reach 3 retained pilots",
                        "deadline": "2026-04-30",
                    },
                }
            )
            evidence_event = researcher.run_event(
                {
                    "action": "capture_evidence_cycle",
                    "payload": {
                        "evidence": {
                            "claim": "Pilot calls show the same activation blocker",
                            "source": "pilot-call",
                            "confidence": 78,
                        },
                        "replan": {
                            "plan_task": "Test a tighter activation walkthrough",
                        },
                        "idempotency_key": "sequence-1",
                    },
                    "options": {
                        "expected_fingerprint": plan_event["result"]["post_fingerprint"],
                        "allow_retry": True,
                        "history_limit": 2,
                    },
                }
            )
            preview_event = reviewer.run_event({"action": "preview_restore_previous"})

        self.assertTrue(plan_event["ok"])
        self.assertEqual(plan_event["type"], "plan_update_applied")
        self.assertTrue(evidence_event["ok"])
        self.assertEqual(evidence_event["type"], "evidence_cycle_applied")
        self.assertEqual(evidence_event["result"]["post_cycle"]["plan"]["evidence"][-1]["claim"], "Pilot calls show the same activation blocker")
        self.assertIn("Test a tighter activation walkthrough", evidence_event["result"]["post_cycle"]["plan"]["plan_tasks"])
        self.assertTrue(preview_event["ok"])
        self.assertEqual(preview_event["type"], "restore_preview")
        self.assertIn("changed_fields", preview_event["preview"])

    def test_reviewer_role_cannot_update_plan(self):
        with DeepPlanStateIsolation():
            deepplan.ensure_state()
            reviewer = PlannerHostStep(
                adapter=_PLANNER_HOST_MODULE.DeepPlanKernelAdapter(DeepPlanClient(transport=handler_transport)),
                role="reviewer",
            )
            event = reviewer.run_event(
                {
                    "action": "update_plan",
                    "payload": {
                        "goal": "reviewer should not write plan",
                    },
                }
            )

        self.assertFalse(event["ok"])
        self.assertEqual(event["type"], "permission_denied")
        self.assertEqual(event["error"]["type"], "permission_denied")
        self.assertIn("needs plan.write", event["error"]["message"])


if __name__ == "__main__":
    unittest.main()
