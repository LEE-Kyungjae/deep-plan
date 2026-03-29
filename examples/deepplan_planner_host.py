#!/usr/bin/env python3
from dataclasses import dataclass
from typing import Any, Dict

from deepplan_sdk import DeepPlanClient

from deepplan_kernel_adapter import DeepPlanKernelAdapter, summarize_for_host


@dataclass
class PlannerHostStep:
    adapter: DeepPlanKernelAdapter

    def run(self, planner_output: Dict[str, Any]) -> Dict[str, Any]:
        action = str(planner_output.get("action", "")).strip()
        payload = dict(planner_output.get("payload", {}) or {})

        if action == "update_plan":
            result = self.adapter.apply_plan_update(payload)
            return {"type": "plan_update_applied", "summary": summarize_for_host(result), "result": result}

        if action == "capture_evidence_cycle":
            result = self.adapter.client.capture_evidence_cycle(
                dict(payload.get("evidence", {}) or {}),
                replan_payload=dict(payload.get("replan", {}) or {}),
                history_limit=self.adapter.history_limit,
                idempotency_key=str(payload.get("idempotency_key", "")).strip(),
            )
            return {"type": "evidence_cycle_applied", "summary": summarize_for_host(result), "result": result}

        if action == "preview_restore_previous":
            preview = self.adapter.preview_restore_previous()
            return {"type": "restore_preview", "preview": preview}

        if action == "restore_previous":
            result = self.adapter.restore_previous()
            return {"type": "restore_applied", "summary": summarize_for_host(result), "result": result}

        raise ValueError(f"unsupported planner action: {action}")


def example_planner_host() -> None:
    adapter = DeepPlanKernelAdapter(DeepPlanClient.from_http("127.0.0.1", 8787))
    host = PlannerHostStep(adapter)
    event = host.run(
        {
            "action": "update_plan",
            "payload": {
                "goal": "Narrow to a retained pilot segment",
                "success_metric": "Reach 5 retained pilots",
                "deadline": "2026-04-30",
            },
        }
    )
    print(event["type"])
    print(event["summary"])


if __name__ == "__main__":
    example_planner_host()
