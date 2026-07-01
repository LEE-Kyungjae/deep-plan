#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple


SCAFFOLD_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = SCAFFOLD_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deepplan_agents.adapters.deepplan_adapter import DeepPlanAdapter, summarize_cycle_result
from deepplan_agents.runtime.decision_gate import evaluate_cycle_gate, evaluate_snapshot_gate
from deepplan_agents.runtime.host_events import build_error_event, build_success_event, summarize_for_host
from deepplan_agents.runtime.host_step import HostStep, action_contract, required_capabilities_for_action, role_has_action_capabilities
from deepplan_agents.runtime.policies import apply_idempotency_policy, build_idempotency_key, should_retry_stale_conflict
from deepplan_agents.workflows.planner_loop import PlannerLoop
from deepplan_agents.workflows.research_loop import ResearchLoop
from deepplan_agents.workflows.review_loop import ReviewLoop


class FakeDeepPlanClient:
    def __init__(self, *, before_score: float = 0.8, after_score: float = 0.92, health_status: str = "ok", qa_result: str = "PASS") -> None:
        self.calls: List[Tuple[str, Dict[str, Any]]] = []
        self.goal = "initial goal"
        self.before_score = before_score
        self.after_score = after_score
        self.health_status = health_status
        self.qa_result = qa_result

    def get_cycle(self, *, history_limit: int = 10) -> Dict[str, Any]:
        self.calls.append(("get_cycle", {"history_limit": history_limit}))
        return {
            "plan": {"goal": self.goal},
            "qa": {"result": self.qa_result, "score": self.before_score},
            "health": {"status": self.health_status},
            "history_limit": history_limit,
            "fingerprint": "fp-before",
        }

    def apply_and_get_cycle(
        self,
        operation: str,
        payload: Dict[str, Any],
        *,
        history_limit: int = 10,
        expected_fingerprint: str = "",
        require_healthy: bool = False,
    ) -> Dict[str, Any]:
        self.calls.append(
            (
                operation,
                {
                    "payload": dict(payload),
                    "history_limit": history_limit,
                    "expected_fingerprint": expected_fingerprint,
                    "require_healthy": require_healthy,
                },
            )
        )
        if operation == "update_plan":
            self.goal = str(payload.get("goal", self.goal))
        return {
            "operation": operation,
            "changed_fields": sorted(payload.keys()),
            "post_fingerprint": "fp-after",
            "retried": False,
            "post_cycle": {
                "plan": {"goal": self.goal},
                "qa": {"result": self.qa_result, "score": self.after_score},
                "health": {"status": self.health_status},
            },
        }

    def capture_evidence_cycle(
        self,
        evidence_payload: Dict[str, Any],
        *,
        replan_payload=None,
        history_limit: int = 10,
        idempotency_key: str = "",
        expected_fingerprint: str = "",
        allow_retry: bool = False,
        require_healthy: bool = False,
    ) -> Dict[str, Any]:
        payload = dict(evidence_payload)
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        self.calls.append(
            (
                "capture_evidence_cycle",
                {
                    "payload": payload,
                    "replan_payload": dict(replan_payload or {}),
                    "history_limit": history_limit,
                    "expected_fingerprint": expected_fingerprint,
                    "allow_retry": allow_retry,
                    "require_healthy": require_healthy,
                },
            )
        )
        return {
            "operation": "capture_evidence_cycle",
            "changed_fields": ["evidence"],
            "post_fingerprint": "fp-after",
            "retried": False,
            "post_cycle": {
                "plan": {"goal": self.goal},
                "qa": {"result": self.qa_result, "score": self.after_score},
                "health": {"status": self.health_status},
            },
        }

    def preview_restore(self, *, previous: bool = False) -> Dict[str, Any]:
        self.calls.append(("preview_restore", {"previous": previous}))
        return {"selected_via": "previous" if previous else "revision_id"}


class DeepPlanAgentsAdapterTests(unittest.TestCase):
    def test_adapter_snapshot_and_apply_plan_update_delegate_to_client(self):
        client = FakeDeepPlanClient()
        adapter = DeepPlanAdapter(client, history_limit=7, require_healthy_writes=True)

        before = adapter.snapshot()
        result = adapter.apply_plan_update({"goal": "new goal"})

        self.assertEqual(before["plan"]["goal"], "initial goal")
        self.assertEqual(result["post_cycle"]["plan"]["goal"], "new goal")
        self.assertEqual(
            client.calls,
            [
                ("get_cycle", {"history_limit": 7}),
                (
                    "update_plan",
                    {
                        "payload": {"goal": "new goal"},
                        "history_limit": 7,
                        "expected_fingerprint": "",
                        "require_healthy": True,
                    },
                ),
            ],
        )

    def test_adapter_exposes_review_and_restore_operations(self):
        client = FakeDeepPlanClient()
        adapter = DeepPlanAdapter(client, history_limit=3, require_healthy_writes=False)

        adapter.capture_evidence_cycle({"claim": "signal", "source": "call", "confidence": 70})
        adapter.request_review({"scope": "plan", "reason": "Need reviewer"})
        adapter.resolve_review({"request_id": "review-1", "status": "resolved"})
        preview = adapter.preview_restore_previous()
        adapter.restore_previous()

        self.assertEqual(preview["selected_via"], "previous")
        self.assertEqual([item[0] for item in client.calls], ["capture_evidence_cycle", "request_review", "resolve_review", "preview_restore", "restore_revision"])
        self.assertTrue(client.calls[0][1]["allow_retry"])

    def test_summarize_cycle_result_extracts_host_facing_fields(self):
        summary = summarize_cycle_result(
            {
                "operation": "update_plan",
                "post_fingerprint": "fp-after",
                "changed_fields": ["goal"],
                "retried": True,
                "post_cycle": {
                    "qa": {"result": "PASS", "score": 0.9},
                    "health": {"status": "ok"},
                },
            }
        )

        self.assertEqual(summary["operation"], "update_plan")
        self.assertEqual(summary["fingerprint"], "fp-after")
        self.assertEqual(summary["qa_result"], "PASS")
        self.assertEqual(summary["health_status"], "ok")
        self.assertTrue(summary["retried"])


class PlannerLoopTests(unittest.TestCase):
    def test_runtime_policies_build_idempotency_keys_and_gate_stale_retry(self):
        key = build_idempotency_key(
            session_id="session-42",
            step_id="research-3",
            operation="capture_evidence_cycle",
        )
        payload = apply_idempotency_policy(
            "request_review",
            {"scope": "plan", "reason": "Need owner"},
            session_id="session-42",
            step_id="review-1",
        )

        self.assertEqual(key, "session-42:research-3:evidence-cycle")
        self.assertEqual(payload["idempotency_key"], "session-42:review-1:review-request")
        self.assertTrue(should_retry_stale_conflict(attempt_count=1, max_attempts=2, error_code="plan_fingerprint_mismatch"))
        self.assertFalse(should_retry_stale_conflict(attempt_count=2, max_attempts=2, error_code="plan_fingerprint_mismatch"))

    def test_host_events_wrap_success_and_error_shapes(self):
        outcome = {
            "role": "planner",
            "session": {"profile": "planner_full"},
            "summary": {
                "operation": "update_plan",
                "fingerprint": "fp-after",
                "changed_fields": ["goal"],
                "qa_result": "PASS",
                "qa_score": 0.9,
                "health_status": "ok",
                "retried": False,
            },
            "gate": {"decision": "continue", "reasons": ["qa_score_improved"]},
            "result": {"operation": "update_plan"},
        }
        summary = summarize_for_host(outcome)
        success = build_success_event("planner_step", outcome)
        error = build_error_event(
            "planner_step_failed",
            role="planner",
            error_type="conflict",
            message="plan fingerprint mismatch",
            retryable=True,
            operation="update_plan",
            step="mutation",
        )

        self.assertEqual(summary["profile"], "planner_full")
        self.assertEqual(success["type"], "planner_step")
        self.assertTrue(success["ok"])
        self.assertEqual(success["summary"]["decision"], "continue")
        self.assertFalse(error["ok"])
        self.assertEqual(error["error"]["type"], "conflict")
        self.assertTrue(error["error"]["retryable"])

    def test_host_step_dispatches_actions_and_enforces_role_capabilities(self):
        contract = action_contract("reviewer")
        client = FakeDeepPlanClient()
        adapter = DeepPlanAdapter(client, history_limit=4, require_healthy_writes=True)
        reviewer_step = HostStep(adapter, role="reviewer")
        planner_step = HostStep(adapter, role="planner")

        requested = reviewer_step.run_event(
            {
                "action": "request_review",
                "payload": {"scope": "plan", "reason": "Need reviewer decision"},
                "options": {"session_id": "session-42", "step_id": "review-1"},
            }
        )
        denied = reviewer_step.run_event(
            {
                "action": "update_plan",
                "payload": {"goal": "should not be allowed"},
            }
        )
        planned = planner_step.run_event(
            {
                "action": "update_plan",
                "payload": {"goal": "allowed planner update"},
            }
        )

        self.assertEqual(contract["profile"], "reviewer_restore")
        self.assertEqual(required_capabilities_for_action("reviewer", "resolve_review"), ["review.resolve"])
        self.assertTrue(role_has_action_capabilities("reviewer", "resolve_review"))
        self.assertFalse(role_has_action_capabilities("reviewer", "update_plan"))
        self.assertTrue(requested["ok"])
        self.assertEqual(requested["type"], "review_requested")
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["error"]["type"], "permission_denied")
        self.assertTrue(planned["ok"])
        self.assertEqual(planned["type"], "planner_step")

    def test_decision_gate_blocks_unhealthy_snapshot_and_routes_critical_failure(self):
        snapshot_block = evaluate_snapshot_gate({"health": {"status": "error"}, "qa": {"result": "PASS", "score": 0.8}})
        cycle_review = evaluate_cycle_gate(
            {"qa": {"score": 0.8}, "health": {"status": "ok"}},
            {"post_cycle": {"qa": {"result": "CRITICAL_FAILURE", "score": 0.4}, "health": {"status": "ok"}}},
        )

        self.assertEqual(snapshot_block["decision"], "block")
        self.assertTrue(snapshot_block["should_block_writes"])
        self.assertEqual(cycle_review["decision"], "review")
        self.assertTrue(cycle_review["should_route_to_reviewer"])

    def test_planner_loop_runs_one_update_with_runtime_session(self):
        client = FakeDeepPlanClient()
        adapter = DeepPlanAdapter(client, history_limit=4, require_healthy_writes=True)
        loop = PlannerLoop(adapter)

        outcome = loop.run_once({"goal": "planner loop goal"})
        event = loop.run_event({"goal": "planner loop goal"})

        self.assertEqual(outcome["role"], "planner")
        self.assertEqual(outcome["session"]["profile"], "planner_full")
        self.assertEqual(outcome["before"]["plan"]["goal"], "initial goal")
        self.assertEqual(outcome["after"]["plan"]["goal"], "planner loop goal")
        self.assertEqual(outcome["preflight"]["decision"], "continue")
        self.assertEqual(outcome["gate"]["decision"], "continue")
        self.assertEqual(outcome["summary"]["qa_result"], "PASS")
        self.assertTrue(event["ok"])
        self.assertEqual(event["type"], "planner_step")
        self.assertEqual(event["summary"]["operation"], "update_plan")
        self.assertEqual(
            [item[0] for item in client.calls],
            ["get_cycle", "update_plan", "get_cycle", "update_plan"],
        )

    def test_planner_loop_routes_to_reviewer_when_qa_score_regresses(self):
        client = FakeDeepPlanClient(before_score=0.8, after_score=0.5, health_status="ok", qa_result="PASS")
        adapter = DeepPlanAdapter(client, history_limit=4, require_healthy_writes=True)
        loop = PlannerLoop(adapter)

        outcome = loop.run_once({"goal": "planner loop regression"})

        self.assertEqual(outcome["gate"]["decision"], "review")
        self.assertIn("qa_score_regressed", outcome["gate"]["reasons"])

    def test_research_loop_runs_capture_evidence_cycle_with_runtime_session(self):
        client = FakeDeepPlanClient()
        adapter = DeepPlanAdapter(client, history_limit=4, require_healthy_writes=True)
        loop = ResearchLoop(adapter)

        outcome = loop.run_once(
            {
                "evidence": {"claim": "Found repeated friction", "source": "interview", "confidence": 72},
                "replan": {"plan_task": "Tighten onboarding hypothesis"},
            },
            session_id="session-42",
            step_id="research-3",
        )
        event = loop.run_event(
            {
                "evidence": {"claim": "Found repeated friction", "source": "interview", "confidence": 72},
                "replan": {"plan_task": "Tighten onboarding hypothesis"},
            },
            session_id="session-42",
            step_id="research-3",
        )

        self.assertEqual(outcome["role"], "researcher")
        self.assertEqual(outcome["session"]["profile"], "researcher_capture")
        self.assertEqual(outcome["gate"]["decision"], "continue")
        self.assertEqual(outcome["payload"]["idempotency_key"], "session-42:research-3:evidence-cycle")
        self.assertEqual(client.calls[1][1]["payload"]["idempotency_key"], "session-42:research-3:evidence-cycle")
        self.assertEqual(outcome["summary"]["operation"], "capture_evidence_cycle")
        self.assertTrue(event["ok"])
        self.assertEqual(event["type"], "research_step")
        self.assertEqual(event["summary"]["operation"], "capture_evidence_cycle")
        self.assertEqual(
            [item[0] for item in client.calls],
            ["get_cycle", "capture_evidence_cycle", "get_cycle", "capture_evidence_cycle"],
        )

    def test_review_loop_can_request_and_resolve_with_runtime_session(self):
        client = FakeDeepPlanClient()
        adapter = DeepPlanAdapter(client, history_limit=4, require_healthy_writes=True)
        loop = ReviewLoop(adapter)

        requested = loop.request_once(
            {"scope": "plan", "reason": "Need owner decision"},
            session_id="session-42",
            step_id="review-1",
        )
        resolved = loop.resolve_once(
            {"request_id": "review-1", "status": "resolved"},
            session_id="session-42",
            step_id="review-2",
        )
        requested_event = loop.request_event(
            {"scope": "plan", "reason": "Need owner decision"},
            session_id="session-42",
            step_id="review-1",
        )
        resolved_event = loop.resolve_event(
            {"request_id": "review-1", "status": "resolved"},
            session_id="session-42",
            step_id="review-2",
        )

        self.assertEqual(requested["role"], "reviewer")
        self.assertEqual(requested["session"]["profile"], "reviewer_restore")
        self.assertEqual(requested["gate"]["decision"], "continue")
        self.assertEqual(requested["payload"]["idempotency_key"], "session-42:review-1:review-request")
        self.assertEqual(requested["summary"]["operation"], "request_review")
        self.assertEqual(resolved["payload"]["idempotency_key"], "session-42:review-2:review-resolve")
        self.assertEqual(resolved["summary"]["operation"], "resolve_review")
        self.assertEqual(requested_event["type"], "review_requested")
        self.assertEqual(resolved_event["type"], "review_resolved")
        self.assertEqual(
            [item[0] for item in client.calls],
            [
                "get_cycle",
                "request_review",
                "get_cycle",
                "resolve_review",
                "get_cycle",
                "request_review",
                "get_cycle",
                "resolve_review",
            ],
        )


if __name__ == "__main__":
    unittest.main()
