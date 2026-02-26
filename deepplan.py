#!/usr/bin/env python3
import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parent
STATE_DIR = ROOT / ".deeplan"
PLAN_PATH = STATE_DIR / "plan.json"
DECISIONS_PATH = STATE_DIR / "decisions.jsonl"
RISKS_PATH = STATE_DIR / "risks.jsonl"
EVENTS_PATH = STATE_DIR / "events.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_state() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    for p in [DECISIONS_PATH, RISKS_PATH, EVENTS_PATH]:
        if not p.exists():
            p.write_text("", encoding="utf-8")
    if not PLAN_PATH.exists():
        PLAN_PATH.write_text(json.dumps(default_plan(), indent=2), encoding="utf-8")


def default_plan() -> Dict:
    return {
        "version": "0.3.0",
        "updated_at": now_iso(),
        "goal": "",
        "success_metric": "",
        "deadline": "",
        "constraints": [],
        "assumptions": [],
        "options": [],
        "selected_option": "",
        "plan_tasks": [],
        "execution_tasks": [],
        "dependencies": [],
        "experiments": [],
        "risks": [],
        "references": [],
        "insights": [],
        "direction_insights": [],
        "market_insights": [],
        "timing_insights": [],
        "differentiation_insights": [],
        "monetization_insights": [],
        "constraint_insights": [],
        "risk_signal_insights": [],
        "evolution_insights": [],
        "definition_of_done": [],
        "evidence": [],
    }


def migrate_plan(plan: Dict) -> Dict:
    if "tasks" in plan and ("plan_tasks" not in plan and "execution_tasks" not in plan):
        tasks = plan.get("tasks", [])
        split = len(tasks) // 2
        plan["plan_tasks"] = tasks[:split]
        plan["execution_tasks"] = tasks[split:]
    plan.pop("tasks", None)

    for key, default in [
        ("version", "0.3.0"),
        ("updated_at", now_iso()),
        ("goal", ""),
        ("success_metric", ""),
        ("deadline", ""),
        ("constraints", []),
        ("assumptions", []),
        ("options", []),
        ("selected_option", ""),
        ("plan_tasks", []),
        ("execution_tasks", []),
        ("dependencies", []),
        ("experiments", []),
        ("risks", []),
        ("references", []),
        ("insights", []),
        ("direction_insights", []),
        ("market_insights", []),
        ("timing_insights", []),
        ("differentiation_insights", []),
        ("monetization_insights", []),
        ("constraint_insights", []),
        ("risk_signal_insights", []),
        ("evolution_insights", []),
        ("definition_of_done", []),
        ("evidence", []),
    ]:
        plan.setdefault(key, default)

    plan["version"] = "0.3.0"
    return plan


def load_plan() -> Dict:
    ensure_state()
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    plan = migrate_plan(plan)
    save_plan(plan)
    return plan


def save_plan(plan: Dict) -> None:
    plan["updated_at"] = now_iso()
    PLAN_PATH.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")


def append_jsonl(path: Path, payload: Dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def non_empty(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, list):
        return len(v) > 0
    if isinstance(v, dict):
        return len(v) > 0
    return True


def parse_csv(v: str) -> List[str]:
    return [x.strip() for x in v.split(",") if x.strip()]


def default_deadline(days: int = 14) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def generate_ideas(args: argparse.Namespace) -> List[Dict]:
    interests = parse_csv(args.interests) if args.interests else []
    skills = parse_csv(args.skills) if args.skills else []
    profile = args.profile.strip() if args.profile else "solo builder"
    horizon = args.deadline.strip() if args.deadline else default_deadline(14)
    time_limit = args.time_per_day.strip() if args.time_per_day else "1h/day"
    budget = args.budget.strip() if args.budget else "$0"
    focus_terms = interests if interests else ["your workflow", "your learning", "your output quality"]

    templates = [
        {
            "name": "Workflow Automation",
            "goal": "Automate one repetitive {focus} task end-to-end",
            "metric": "Reduce manual time on {focus} by 30% by {deadline}",
            "plan_tasks": [
                "Map the current manual workflow and baseline time.",
                "Select one high-friction step to automate first.",
            ],
            "execution_tasks": [
                "Build the smallest working automation script/tool.",
                "Run for one week and compare baseline vs after metrics.",
            ],
        },
        {
            "name": "Portfolio Artifact",
            "goal": "Ship a public mini-project around {focus}",
            "metric": "Publish a working demo and one write-up by {deadline}",
            "plan_tasks": [
                "Define MVP scope and success criteria for the demo.",
                "Collect 3 references from similar projects.",
            ],
            "execution_tasks": [
                "Implement MVP with one differentiating feature.",
                "Publish demo, doc, and changelog.",
            ],
        },
        {
            "name": "Learning Sprint",
            "goal": "Complete a focused sprint to improve {focus} capability",
            "metric": "Deliver 3 practical outputs proving {focus} improvement by {deadline}",
            "plan_tasks": [
                "Choose a narrow syllabus and output format.",
                "Define weekly checkpoints with explicit evidence.",
            ],
            "execution_tasks": [
                "Produce output #1 and gather feedback.",
                "Produce output #2/#3 and review gaps.",
            ],
        },
        {
            "name": "Insight Pipeline",
            "goal": "Build a repeatable system to collect and summarize {focus} insights",
            "metric": "Generate 10 curated insights and 3 actions by {deadline}",
            "plan_tasks": [
                "Define sources and capture format.",
                "Set quality bar for actionable insights.",
            ],
            "execution_tasks": [
                "Run weekly collection and summarization loop.",
                "Apply top 3 insights and measure outcomes.",
            ],
        },
    ]

    ideas: List[Dict] = []
    for i in range(max(1, min(args.count, 10))):
        t = templates[i % len(templates)]
        focus = focus_terms[i % len(focus_terms)]
        goal = t["goal"].format(focus=focus, deadline=horizon)
        metric = t["metric"].format(focus=focus, deadline=horizon)
        assumptions = [
            f"{profile} can sustain {time_limit} for this project.",
            f"Budget stays within {budget} without external paid tooling.",
        ]
        if skills:
            assumptions.append(f"Existing skills ({', '.join(skills[:3])}) are enough for MVP delivery.")
        constraints = [f"time: {time_limit}", f"budget: {budget}", "scope: single focused outcome"]
        ideas.append(
            {
                "title": t["name"],
                "goal": goal,
                "success_metric": metric,
                "deadline": horizon,
                "constraints": constraints,
                "assumptions": assumptions,
                "plan_tasks": t["plan_tasks"],
                "execution_tasks": t["execution_tasks"],
                "definition_of_done": [
                    "Primary success metric is measured with before/after evidence.",
                    "At least one artifact (code/doc/demo) is published.",
                ],
                "experiments": ["Run a 7-day pilot and log outcomes."],
            }
        )
    return ideas


def task_balance_ok(plan: Dict) -> bool:
    p = len(plan.get("plan_tasks", []))
    e = len(plan.get("execution_tasks", []))
    total = p + e
    if total < 4 or p == 0 or e == 0:
        return False
    ratio = p / total
    return 0.4 <= ratio <= 0.6


def insight_axes_covered(plan: Dict) -> bool:
    axes = [
        "direction_insights",
        "market_insights",
        "timing_insights",
        "differentiation_insights",
        "monetization_insights",
        "constraint_insights",
        "risk_signal_insights",
        "evolution_insights",
    ]
    return all(non_empty(plan.get(k)) for k in axes)


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    weight: int
    critical: bool = False


def run_qa(plan: Dict) -> Tuple[int, List[CheckResult], bool]:
    checks: List[CheckResult] = []

    checks.append(CheckResult("goal_clarity", non_empty(plan.get("goal")), "Goal is present and outcome-oriented.", 10, True))
    checks.append(
        CheckResult(
            "measurability",
            non_empty(plan.get("success_metric")) and non_empty(plan.get("deadline")),
            "Success metric and deadline are both defined.",
            10,
            True,
        )
    )
    checks.append(CheckResult("constraints", non_empty(plan.get("constraints")), "Constraints are explicitly listed.", 8))
    checks.append(CheckResult("assumptions", non_empty(plan.get("assumptions")), "Core assumptions are extracted.", 8))
    checks.append(
        CheckResult(
            "options_comparison",
            len(plan.get("options", [])) >= 2 and non_empty(plan.get("selected_option")),
            "At least two options and one selected option exist.",
            8,
        )
    )
    checks.append(
        CheckResult(
            "references_coverage",
            len(plan.get("references", [])) >= 3,
            "Plan includes at least three references (docs, cases, benchmarks).",
            10,
        )
    )
    checks.append(
        CheckResult(
            "insight_axes_coverage",
            insight_axes_covered(plan),
            "Eight long-horizon insight axes are all covered.",
            10,
        )
    )
    checks.append(
        CheckResult(
            "plan_execution_balance",
            task_balance_ok(plan),
            "Plan/Execution task split is balanced near 50:50 (40-60% range).",
            10,
            True,
        )
    )
    checks.append(
        CheckResult(
            "verification_loop",
            non_empty(plan.get("experiments")),
            "Validation experiments exist for key assumptions.",
            8,
        )
    )
    checks.append(
        CheckResult(
            "risk_coverage",
            non_empty(plan.get("risks")),
            "Top risks include early signals and mitigations.",
            8,
        )
    )
    checks.append(
        CheckResult(
            "dependencies",
            non_empty(plan.get("dependencies")),
            "External dependencies/blockers are documented.",
            5,
        )
    )
    checks.append(
        CheckResult(
            "definition_of_done",
            non_empty(plan.get("definition_of_done")),
            "Definition of done exists.",
            5,
            True,
        )
    )

    score = 0
    critical_failure = False
    for c in checks:
        if c.passed:
            score += c.weight
        if c.critical and not c.passed:
            critical_failure = True
    return score, checks, critical_failure


def print_qa(score: int, checks: List[CheckResult], critical_failure: bool) -> None:
    print(f"QA score: {score}/100")
    for c in checks:
        icon = "PASS" if c.passed else "FAIL"
        critical = " [CRITICAL]" if c.critical else ""
        print(f"- {icon} {c.name}{critical}: {c.detail}")
    if critical_failure:
        print("Result: CRITICAL_FAILURE")
    elif score < 70:
        print("Result: NEEDS_REPLAN (score < 70)")
    else:
        print("Result: PASS")


def auto_replan_stub(plan: Dict, checks: List[CheckResult]) -> Dict:
    failed = [c.name for c in checks if not c.passed]
    if "constraints" in failed and not plan.get("constraints"):
        plan["constraints"] = ["Define practical limits for time, budget, and staffing."]
    if "assumptions" in failed and not plan.get("assumptions"):
        plan["assumptions"] = ["Key assumptions need explicit validation."]
    if "options_comparison" in failed and len(plan.get("options", [])) < 2:
        plan["options"] = [
            "Conservative option: narrow scope and faster delivery.",
            "Balanced option: medium scope with staged rollout.",
            "Aggressive option: broad scope with higher risk.",
        ]
        if not plan.get("selected_option"):
            plan["selected_option"] = "Balanced option: medium scope with staged rollout."
    if "references_coverage" in failed and len(plan.get("references", [])) < 3:
        plan["references"] = [
            "Spec-driven planning examples",
            "Agent workflow docs",
            "Postmortem of failed planning cases",
        ]
    if "insight_axes_coverage" in failed and len(plan.get("insights", [])) < 3:
        plan["insights"] = [
            "Treat planning as first-class work, not overhead.",
            "Require evidence links for every critical decision.",
            "Replan from execution signals, not intuition.",
        ]
    if "insight_axes_coverage" in failed:
        if not plan.get("direction_insights"):
            plan["direction_insights"] = ["State why this initiative matters now and what outcome it must create."]
        if not plan.get("market_insights"):
            plan["market_insights"] = ["Identify the highest-pain user segment and current alternatives."]
        if not plan.get("timing_insights"):
            plan["timing_insights"] = ["Define why this timing is favorable now and what delay would cost."]
        if not plan.get("differentiation_insights"):
            plan["differentiation_insights"] = ["Describe one clear strategic difference versus existing options."]
        if not plan.get("monetization_insights"):
            plan["monetization_insights"] = ["Link user value to a concrete monetization path."]
        if not plan.get("constraint_insights"):
            plan["constraint_insights"] = ["List execution constraints and the intended workaround strategy."]
        if not plan.get("risk_signal_insights"):
            plan["risk_signal_insights"] = ["Define one early failure signal and the immediate response."]
        if not plan.get("evolution_insights"):
            plan["evolution_insights"] = ["Define how the plan will be revised on a weekly or monthly cadence."]
    if "plan_execution_balance" in failed:
        if len(plan.get("plan_tasks", [])) == 0:
            plan["plan_tasks"] = [
                "Collect references and extract constraints.",
                "Generate and compare three strategy options.",
            ]
        if len(plan.get("execution_tasks", [])) == 0:
            plan["execution_tasks"] = [
                "Implement minimal CLI flow for plan/qa/replan.",
                "Run pilot and collect evidence against success metric.",
            ]
    if "verification_loop" in failed and not plan.get("experiments"):
        plan["experiments"] = ["Run one pilot iteration and compare against success metric."]
    if "risk_coverage" in failed and not plan.get("risks"):
        plan["risks"] = [
            {
                "risk": "Scope drift",
                "signal": "New requirements added mid-cycle",
                "mitigation": "Freeze sprint scope and defer extras",
            }
        ]
    if "dependencies" in failed and not plan.get("dependencies"):
        plan["dependencies"] = ["Agent runtime support (Codex/Claude Code)"]
    if "definition_of_done" in failed and not plan.get("definition_of_done"):
        plan["definition_of_done"] = ["All core commands work and QA >= 70."]
    return plan


def cmd_init(_: argparse.Namespace) -> None:
    ensure_state()
    print(f"Initialized state in {STATE_DIR}")


def cmd_plan(args: argparse.Namespace) -> None:
    plan = load_plan()
    plan["goal"] = args.goal or plan.get("goal", "")
    plan["success_metric"] = args.success_metric or plan.get("success_metric", "")
    plan["deadline"] = args.deadline or plan.get("deadline", "")

    if args.constraints:
        plan["constraints"] = parse_csv(args.constraints)
    if args.assumptions:
        plan["assumptions"] = parse_csv(args.assumptions)
    if args.options:
        plan["options"] = parse_csv(args.options)
    if args.selected_option:
        plan["selected_option"] = args.selected_option.strip()
    if args.plan_tasks:
        plan["plan_tasks"] = parse_csv(args.plan_tasks)
    if args.execution_tasks:
        plan["execution_tasks"] = parse_csv(args.execution_tasks)
    if args.references:
        plan["references"] = parse_csv(args.references)
    if args.insights:
        plan["insights"] = parse_csv(args.insights)
    if args.direction_insights:
        plan["direction_insights"] = parse_csv(args.direction_insights)
    if args.market_insights:
        plan["market_insights"] = parse_csv(args.market_insights)
    if args.timing_insights:
        plan["timing_insights"] = parse_csv(args.timing_insights)
    if args.differentiation_insights:
        plan["differentiation_insights"] = parse_csv(args.differentiation_insights)
    if args.monetization_insights:
        plan["monetization_insights"] = parse_csv(args.monetization_insights)
    if args.constraint_insights:
        plan["constraint_insights"] = parse_csv(args.constraint_insights)
    if args.risk_signal_insights:
        plan["risk_signal_insights"] = parse_csv(args.risk_signal_insights)
    if args.evolution_insights:
        plan["evolution_insights"] = parse_csv(args.evolution_insights)
    if args.dependencies:
        plan["dependencies"] = parse_csv(args.dependencies)
    if args.experiments:
        plan["experiments"] = parse_csv(args.experiments)
    if args.definition_of_done:
        plan["definition_of_done"] = parse_csv(args.definition_of_done)

    save_plan(plan)
    append_jsonl(EVENTS_PATH, {"ts": now_iso(), "type": "plan_updated", "source": "cmd_plan", "goal": plan["goal"]})

    score, checks, critical_failure = run_qa(plan)
    print_qa(score, checks, critical_failure)

    if not critical_failure and score < 70:
        print("Auto replan triggered.")
        plan = auto_replan_stub(plan, checks)
        save_plan(plan)
        score2, checks2, critical_failure2 = run_qa(plan)
        print("Post-replan QA:")
        print_qa(score2, checks2, critical_failure2)


def cmd_replan(args: argparse.Namespace) -> None:
    plan = load_plan()
    if args.evidence:
        plan.setdefault("evidence", []).append(args.evidence.strip())
    if args.plan_task:
        plan.setdefault("plan_tasks", []).append(args.plan_task.strip())
    if args.execution_task:
        plan.setdefault("execution_tasks", []).append(args.execution_task.strip())
    if args.reference:
        plan.setdefault("references", []).append(args.reference.strip())
    if args.insight:
        plan.setdefault("insights", []).append(args.insight.strip())
    if args.direction_insight:
        plan.setdefault("direction_insights", []).append(args.direction_insight.strip())
    if args.market_insight:
        plan.setdefault("market_insights", []).append(args.market_insight.strip())
    if args.timing_insight:
        plan.setdefault("timing_insights", []).append(args.timing_insight.strip())
    if args.differentiation_insight:
        plan.setdefault("differentiation_insights", []).append(args.differentiation_insight.strip())
    if args.monetization_insight:
        plan.setdefault("monetization_insights", []).append(args.monetization_insight.strip())
    if args.constraint_insight:
        plan.setdefault("constraint_insights", []).append(args.constraint_insight.strip())
    if args.risk_signal_insight:
        plan.setdefault("risk_signal_insights", []).append(args.risk_signal_insight.strip())
    if args.evolution_insight:
        plan.setdefault("evolution_insights", []).append(args.evolution_insight.strip())

    save_plan(plan)
    append_jsonl(EVENTS_PATH, {"ts": now_iso(), "type": "replan", "source": "cmd_replan", "evidence": args.evidence or ""})

    score, checks, critical_failure = run_qa(plan)
    print_qa(score, checks, critical_failure)
    if not critical_failure and score < 70:
        print("Auto replan triggered.")
        plan = auto_replan_stub(plan, checks)
        save_plan(plan)
        score2, checks2, critical_failure2 = run_qa(plan)
        print("Post-replan QA:")
        print_qa(score2, checks2, critical_failure2)


def cmd_decide(args: argparse.Namespace) -> None:
    ensure_state()
    payload = {
        "ts": now_iso(),
        "title": args.title.strip(),
        "chosen": args.chosen.strip(),
        "reason": args.reason.strip(),
        "rejected": [r.strip() for r in args.rejected.split(",") if r.strip()] if args.rejected else [],
    }
    append_jsonl(DECISIONS_PATH, payload)
    print("Decision recorded.")


def cmd_risk(args: argparse.Namespace) -> None:
    ensure_state()
    payload = {"ts": now_iso(), "risk": args.risk.strip(), "signal": args.signal.strip(), "mitigation": args.mitigation.strip()}
    append_jsonl(RISKS_PATH, payload)
    print("Risk recorded.")


def cmd_qa(_: argparse.Namespace) -> None:
    plan = load_plan()
    score, checks, critical_failure = run_qa(plan)
    print_qa(score, checks, critical_failure)


def cmd_show(_: argparse.Namespace) -> None:
    plan = load_plan()
    p = len(plan.get("plan_tasks", []))
    e = len(plan.get("execution_tasks", []))
    total = p + e
    ratio = f"{(p / total * 100):.1f}%" if total > 0 else "n/a"
    print(f"Goal: {plan.get('goal')}")
    print(f"Success Metric: {plan.get('success_metric')}")
    print(f"Deadline: {plan.get('deadline')}")
    print(f"Updated: {plan.get('updated_at')}")
    print(f"Plan Tasks: {p}")
    print(f"Execution Tasks: {e}")
    print(f"Plan Ratio: {ratio}")
    print(f"References: {len(plan.get('references', []))}")
    print(f"Insights: {len(plan.get('insights', []))}")
    covered = sum(
        1
        for key in [
            "direction_insights",
            "market_insights",
            "timing_insights",
            "differentiation_insights",
            "monetization_insights",
            "constraint_insights",
            "risk_signal_insights",
            "evolution_insights",
        ]
        if non_empty(plan.get(key))
    )
    print(f"Insight Axes Covered: {covered}/8")
    print(f"Risks: {len(plan.get('risks', []))}")


def cmd_ideate(args: argparse.Namespace) -> None:
    ensure_state()
    ideas = generate_ideas(args)
    append_jsonl(
        EVENTS_PATH,
        {
            "ts": now_iso(),
            "type": "ideate",
            "source": "cmd_ideate",
            "count": len(ideas),
            "profile": args.profile or "",
        },
    )

    if args.json:
        print(json.dumps(ideas, indent=2, ensure_ascii=False))
    else:
        for idx, idea in enumerate(ideas, start=1):
            print(f"[{idx}] {idea['title']}")
            print(f"  Goal: {idea['goal']}")
            print(f"  Success Metric: {idea['success_metric']}")
            print(f"  Deadline: {idea['deadline']}")
            print(f"  Constraints: {', '.join(idea['constraints'])}")
            print("")

    if args.apply:
        choice = args.apply - 1
        if choice < 0 or choice >= len(ideas):
            raise SystemExit(f"--apply must be between 1 and {len(ideas)}")

        selected = ideas[choice]
        plan = load_plan()
        plan["goal"] = selected["goal"]
        plan["success_metric"] = selected["success_metric"]
        plan["deadline"] = selected["deadline"]
        plan["constraints"] = selected["constraints"]
        plan["assumptions"] = selected["assumptions"]
        plan["plan_tasks"] = selected["plan_tasks"]
        plan["execution_tasks"] = selected["execution_tasks"]
        plan["experiments"] = selected["experiments"]
        plan["definition_of_done"] = selected["definition_of_done"]
        save_plan(plan)

        append_jsonl(
            EVENTS_PATH,
            {
                "ts": now_iso(),
                "type": "idea_applied",
                "source": "cmd_ideate",
                "selected_index": args.apply,
                "goal": selected["goal"],
            },
        )
        print(f"Applied idea #{args.apply} to current plan.")
        score, checks, critical_failure = run_qa(plan)
        print_qa(score, checks, critical_failure)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DeepPlan local planning engine (MVP)")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("init")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("plan")
    s.add_argument("--goal", type=str, default="")
    s.add_argument("--success-metric", type=str, default="")
    s.add_argument("--deadline", type=str, default="")
    s.add_argument("--constraints", type=str, default="")
    s.add_argument("--assumptions", type=str, default="")
    s.add_argument("--options", type=str, default="")
    s.add_argument("--selected-option", type=str, default="")
    s.add_argument("--plan-tasks", type=str, default="")
    s.add_argument("--execution-tasks", type=str, default="")
    s.add_argument("--references", type=str, default="")
    s.add_argument("--insights", type=str, default="")
    s.add_argument("--direction-insights", type=str, default="")
    s.add_argument("--market-insights", type=str, default="")
    s.add_argument("--timing-insights", type=str, default="")
    s.add_argument("--differentiation-insights", type=str, default="")
    s.add_argument("--monetization-insights", type=str, default="")
    s.add_argument("--constraint-insights", type=str, default="")
    s.add_argument("--risk-signal-insights", type=str, default="")
    s.add_argument("--evolution-insights", type=str, default="")
    s.add_argument("--dependencies", type=str, default="")
    s.add_argument("--experiments", type=str, default="")
    s.add_argument("--definition-of-done", type=str, default="")
    s.set_defaults(func=cmd_plan)

    s = sub.add_parser("replan")
    s.add_argument("--evidence", type=str, default="")
    s.add_argument("--plan-task", type=str, default="")
    s.add_argument("--execution-task", type=str, default="")
    s.add_argument("--reference", type=str, default="")
    s.add_argument("--insight", type=str, default="")
    s.add_argument("--direction-insight", type=str, default="")
    s.add_argument("--market-insight", type=str, default="")
    s.add_argument("--timing-insight", type=str, default="")
    s.add_argument("--differentiation-insight", type=str, default="")
    s.add_argument("--monetization-insight", type=str, default="")
    s.add_argument("--constraint-insight", type=str, default="")
    s.add_argument("--risk-signal-insight", type=str, default="")
    s.add_argument("--evolution-insight", type=str, default="")
    s.set_defaults(func=cmd_replan)

    s = sub.add_parser("decide")
    s.add_argument("--title", type=str, required=True)
    s.add_argument("--chosen", type=str, required=True)
    s.add_argument("--reason", type=str, required=True)
    s.add_argument("--rejected", type=str, default="")
    s.set_defaults(func=cmd_decide)

    s = sub.add_parser("risk")
    s.add_argument("--risk", type=str, required=True)
    s.add_argument("--signal", type=str, required=True)
    s.add_argument("--mitigation", type=str, required=True)
    s.set_defaults(func=cmd_risk)

    s = sub.add_parser("qa")
    s.set_defaults(func=cmd_qa)

    s = sub.add_parser("show")
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("ideate")
    s.add_argument("--profile", type=str, default="")
    s.add_argument("--interests", type=str, default="")
    s.add_argument("--skills", type=str, default="")
    s.add_argument("--time-per-day", type=str, default="1h/day")
    s.add_argument("--budget", type=str, default="$0")
    s.add_argument("--deadline", type=str, default="")
    s.add_argument("--count", type=int, default=5)
    s.add_argument("--json", action="store_true")
    s.add_argument("--apply", type=int, default=0, help="Apply selected idea index to current plan (1-based).")
    s.set_defaults(func=cmd_ideate)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
