#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from deepplan_agents.adapters.deepplan_adapter import DeepPlanAdapter
from deepplan_agents.bootstrap import ClientConfig, build_client
from deepplan_agents.runtime.host_step import HostStep, action_contract
from deepplan_agents.skills.registry import build_runtime_session
from deepplan_agents.strategy_llm import run_strategy_llm, static_provider_from_json
from deepplan_agents.strategy_prompt import build_strategy_prompt_bundle
from deepplan_agents.strategy_routes import route_strategy_next_actions


DEFAULT_PAYLOADS: Dict[str, Dict[str, Any]] = {
    "evaluate_experience_strategy": {
        "idea": "AI planning checkpoint for builders before they ask agents to build.",
        "target_user": "solo AI builders and early founders",
        "problem": "They build generic services quickly before validating problem, desire, differentiation, and repeat value.",
        "current_alternative": "They ask a coding agent to build immediately or use generic planning prompts.",
        "pain_frequency": "Every new product idea or major feature decision creates this risk.",
        "solution": "Evaluate problem-solution fit, emotional demand, experience loop, monetization trigger, and genericness before build.",
        "desire": "avoid wasted work and find a sharper money-making direction",
        "emotion": "anxiety, greed, control, status",
        "trigger": "before starting a build session",
        "action": "submit an idea and receive a continue, revise, or stop decision",
        "reward": "a sharper plan and clear reasons to continue, revise, or stop",
        "monetization": "paid planning intelligence for builders who want better odds before spending build time",
        "repeat_loop": "review each new idea, weekly planning cycle, and post-launch evidence cycle",
        "references": ["successful service loops", "failed AI wrappers", "user behavior data"],
        "behavior_signals": ["users ask AI agents for the same dashboards and AI wrappers", "successful services convert emotional demand into repeat behavior"],
        "differentiation": "pre-build product intelligence rather than another task or notes tool"
    },
    "update_plan": {
        "goal": "Agent console planning pass",
        "success_metric": "Produce one reviewable planning cycle",
        "deadline": "2026-05-31",
    },
    "capture_evidence_cycle": {
        "claim": "Agent console can capture a planning signal and replan from it.",
        "source": "agent-console",
        "confidence": 70,
        "axis": "direction",
    },
    "run_reference_discovery": {
        "question": "Which references prove or disprove this product direction?",
        "context": "Strategy evaluation needs external behavior evidence before build.",
        "references": ["successful service loops", "failed AI wrappers"],
        "rejected": ["generic AI dashboard examples"],
        "apply": True,
    },
    "request_review": {
        "scope": "plan",
        "reason": "Agent console routed this planning cycle for human review.",
        "requested_by": "agent-console",
        "priority": "medium",
    },
    "resolve_review": {
        "request_id": "",
        "status": "resolved",
        "resolution": "Resolved from agent console.",
        "resolved_by": "agent-console",
    },
    "preview_restore_previous": {},
    "restore_previous": {},
}


def _json_dumps(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _load_payload(args: argparse.Namespace) -> Dict[str, Any]:
    if args.payload_json and args.payload_file:
        raise ValueError("use either --payload-json or --payload-file, not both")
    if args.payload_json:
        payload = json.loads(args.payload_json)
    elif args.payload_file:
        payload = json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
    else:
        payload = dict(DEFAULT_PAYLOADS.get(args.action, {}))
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    return payload


def _client_config(args: argparse.Namespace) -> ClientConfig:
    mode = "http" if args.base_url else "in-process"
    return ClientConfig(
        mode=mode,
        base_url=str(args.base_url or ""),
        history_limit=int(args.history_limit),
        require_healthy_writes=not bool(args.allow_unhealthy_writes),
    )


def build_adapter(args: argparse.Namespace) -> DeepPlanAdapter:
    config = _client_config(args)
    return DeepPlanAdapter(
        build_client(config),
        history_limit=config.history_limit,
        require_healthy_writes=config.require_healthy_writes,
    )


def cmd_agents(_: argparse.Namespace) -> int:
    roles = ["planner", "strategist", "researcher", "reviewer"]
    payload = {"ok": True, "roles": []}
    for role in roles:
        contract = action_contract(role)
        session = build_runtime_session(role)
        payload["roles"].append(
            {
                "role": role,
                "profile": contract["profile"],
                "capabilities": contract["capabilities"],
                "allowed_actions": contract["allowed_actions"],
                "skills": session["actual_skills"],
            }
        )
    print(_json_dumps(payload))
    return 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    adapter = build_adapter(args)
    snapshot = adapter.snapshot()
    print(_json_dumps({"ok": True, "type": "snapshot", "snapshot": snapshot}))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    payload = _load_payload(args)
    options: Dict[str, Any] = {}
    if args.session_id:
        options["session_id"] = args.session_id
    if args.step_id:
        options["step_id"] = args.step_id

    adapter = build_adapter(args)
    event = HostStep(adapter, role=args.role).run_event(
        {
            "action": args.action,
            "payload": payload,
            "options": options,
        }
    )
    print(_json_dumps(event))
    return 0 if event.get("ok") else 1


def cmd_prompt(args: argparse.Namespace) -> int:
    payload = _load_payload(args)
    adapter = build_adapter(args)
    snapshot = adapter.snapshot()
    bundle = build_strategy_prompt_bundle(payload, snapshot)
    print(_json_dumps({"ok": True, "type": "strategy_prompt", "bundle": bundle}))
    return 0


def cmd_llm(args: argparse.Namespace) -> int:
    payload = _load_payload(args)
    if not args.static_report_json and not args.static_report_file:
        raise ValueError("llm command currently requires --static-report-json or --static-report-file")
    if args.static_report_json and args.static_report_file:
        raise ValueError("use either --static-report-json or --static-report-file, not both")
    raw_report = args.static_report_json or Path(args.static_report_file).read_text(encoding="utf-8")
    provider = static_provider_from_json(raw_report)
    adapter = build_adapter(args)
    snapshot = adapter.snapshot()
    result = run_strategy_llm(provider, payload=payload, snapshot=snapshot)
    print(_json_dumps(result))
    return 0


def _load_report(args: argparse.Namespace) -> Dict[str, Any]:
    if args.report_json and args.report_file:
        raise ValueError("use either --report-json or --report-file, not both")
    if args.report_json:
        report = json.loads(args.report_json)
    elif args.report_file:
        report = json.loads(Path(args.report_file).read_text(encoding="utf-8"))
    else:
        raise ValueError("route command requires --report-json or --report-file")
    if not isinstance(report, dict):
        raise ValueError("report must be a JSON object")
    return report


def cmd_route(args: argparse.Namespace) -> int:
    report = _load_report(args)
    result = route_strategy_next_actions(report)
    print(_json_dumps(result))
    return 0 if result.get("ok") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run DeepPlan agents against a local planning workspace.")
    parser.add_argument("--base-url", default="", help="Optional DeepPlan HTTP base URL, e.g. http://127.0.0.1:8787")
    parser.add_argument("--history-limit", type=int, default=5)
    parser.add_argument("--allow-unhealthy-writes", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    agents = sub.add_parser("agents", help="List available agent roles, profiles, actions, and skills.")
    agents.set_defaults(func=cmd_agents)

    snapshot = sub.add_parser("snapshot", help="Read the current DeepPlan cycle snapshot.")
    snapshot.set_defaults(func=cmd_snapshot)

    run = sub.add_parser("run", help="Run one role-aware agent action.")
    run.add_argument("--role", choices=["planner", "strategist", "researcher", "reviewer"], required=True)
    run.add_argument(
        "--action",
        choices=sorted(DEFAULT_PAYLOADS.keys()),
        required=True,
    )
    run.add_argument("--payload-json", default="")
    run.add_argument("--payload-file", default="")
    run.add_argument("--session-id", default="")
    run.add_argument("--step-id", default="")
    run.set_defaults(func=cmd_run)

    prompt = sub.add_parser("prompt", help="Build the strategist LLM prompt bundle without calling a provider.")
    prompt.add_argument(
        "--action",
        choices=["evaluate_experience_strategy"],
        default="evaluate_experience_strategy",
    )
    prompt.add_argument("--payload-json", default="")
    prompt.add_argument("--payload-file", default="")
    prompt.set_defaults(func=cmd_prompt)

    llm = sub.add_parser("llm", help="Run the strategist LLM boundary with a static JSON provider.")
    llm.add_argument(
        "--action",
        choices=["evaluate_experience_strategy"],
        default="evaluate_experience_strategy",
    )
    llm.add_argument("--payload-json", default="")
    llm.add_argument("--payload-file", default="")
    llm.add_argument("--static-report-json", default="")
    llm.add_argument("--static-report-file", default="")
    llm.set_defaults(func=cmd_llm)

    route = sub.add_parser("route", help="Validate and route strategist next_actions to target roles.")
    route.add_argument("--report-json", default="")
    route.add_argument("--report-file", default="")
    route.set_defaults(func=cmd_route)

    return parser


def main(argv: Any = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(_json_dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
