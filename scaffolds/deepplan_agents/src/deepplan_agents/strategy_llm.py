#!/usr/bin/env python3
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Protocol

from deepplan_agents.strategy_prompt import build_strategy_prompt_bundle
from deepplan_agents.workflows.strategy_loop import validate_strategy_report_shape


class StrategyLLMProvider(Protocol):
    def complete_json(self, *, messages: List[Dict[str, str]], schema: Dict[str, Any]) -> Dict[str, Any]:
        ...


@dataclass
class StaticStrategyProvider:
    report: Dict[str, Any]

    def complete_json(self, *, messages: List[Dict[str, str]], schema: Dict[str, Any]) -> Dict[str, Any]:
        return dict(self.report)


def run_strategy_llm(
    provider: StrategyLLMProvider,
    *,
    payload: Dict[str, Any],
    snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    bundle = build_strategy_prompt_bundle(payload, snapshot)
    report = provider.complete_json(messages=bundle["messages"], schema=bundle["schema"])
    if not isinstance(report, dict):
        raise ValueError("strategy provider must return a JSON object")
    errors = validate_strategy_report_shape(report)
    if errors:
        raise ValueError("invalid strategy report: " + "; ".join(errors))
    return {
        "ok": True,
        "type": "strategy_llm_report",
        "provider": provider.__class__.__name__,
        "report": report,
        "prompt": {
            "message_count": len(bundle["messages"]),
            "schema_title": str(bundle["schema"].get("title", "")).strip(),
        },
    }


def static_provider_from_json(raw_json: str) -> StaticStrategyProvider:
    payload = json.loads(raw_json)
    if not isinstance(payload, dict):
        raise ValueError("static strategy report must be a JSON object")
    return StaticStrategyProvider(payload)
