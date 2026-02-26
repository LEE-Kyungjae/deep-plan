# DeepPlan (MVP)

DeepPlan is a local, agent-friendly **Plan Intelligence** engine.
It focuses on one thing: making planning quality the core value.

## Why DeepPlan

Most AI products are excellent at `task -> implement`.
DeepPlan intentionally focuses on the only layer before that:

- what to build
- why now
- what not to build
- how to detect failure early

`Plan` is not prompt preparation.
`Plan` is the business and product decision layer.
DeepPlan is `Plan-only` by design.

## Product Thesis

In the AI era, execution is increasingly commoditized.
Direction quality is not.

If planning is weak, faster execution only accelerates the wrong path.
DeepPlan exists to reduce that failure mode.

## Target User

DeepPlan supports users with existing ideas, but its core strength is:

- users in a zero-idea state
- users who only know: "I want to build something, but I have not decided what"

DeepPlan should guide this ultra-early stage into a concrete, testable plan.

## Planning Philosophy

Humans bring context from life, experience, and intent.
AI should provide insight to elevate thinking quality, not just generate tasks.

Because model outputs can drift toward average patterns, DeepPlan planning should
force higher-signal inputs:

1. Strong references
2. Actionable insights
3. Audience interest detection
4. Need intensity detection
5. High information density
6. Multiple viewpoints

## First 10-Minute Outputs

For zero-idea users, DeepPlan should produce these quickly:

1. Problem/User hypothesis (who has what pain)
2. Three direction options with one explicit choice
3. A testable initial plan (metric, deadline, first tasks)

## Product Boundary

DeepPlan handles:

- idea discovery
- direction setting
- planning logic
- success/failure criteria definition

DeepPlan does not handle:

- task execution orchestration
- implementation workflows
- post-task delivery automation

Those layers are already saturated by other AI tools.
DeepPlan is the layer that decides what deserves execution.

## Value Thesis

In this thesis:

- `Plan` is where strategic value and monetization leverage live
- `Task+` layers are increasingly low-differentiation
- future advantage comes from building better plans, not faster generic execution

## What It Provides

- Shared plan format (`schemas/plan.schema.json`)
- CLI (`deepplan.py`)
- Automatic quality checks on `plan` and `replan`
- Local state in `/.deeplan/`

## Insight Axes (Long-Horizon Planning)

DeepPlan maps planning insight into eight required axes:

1. `direction_insights`
2. `market_insights`
3. `timing_insights`
4. `differentiation_insights`
5. `monetization_insights`
6. `constraint_insights`
7. `risk_signal_insights`
8. `evolution_insights`

`qa` checks whether all 8 axes are covered.

## Messaging Drafts

### Slogans

1. Plan is the product.
2. Decide what matters before AI builds it.
3. In the AI era, direction is alpha.

### Landing Copy (Short)

DeepPlan is a Plan Intelligence tool for the AI era.
Execution is cheap. Direction is expensive.
When you do not know what to build yet, DeepPlan helps you turn ambiguity
into a focused, testable, monetizable plan.

## Quick Start

```bash
python3 deepplan.py init
python3 deepplan.py ideate --profile "solo builder" --interests "automation,creator tools" --count 5
python3 deepplan.py plan \
  --goal "Ship DeepPlan MVP CLI" \
  --success-metric "CLI supports plan/replan/decide/risk by 2026-03-15" \
  --deadline "2026-03-15" \
  --constraints "single developer, local repo only" \
  --direction-insights "Why this initiative matters now" \
  --market-insights "Who has the strongest pain and why" \
  --timing-insights "Why now is the right timing" \
  --differentiation-insights "How this is strategically different" \
  --monetization-insights "How value turns into revenue" \
  --constraint-insights "Key constraints and workaround strategy" \
  --risk-signal-insights "Earliest failure signal and response" \
  --evolution-insights "How the plan evolves weekly"
python3 deepplan.py qa
python3 deepplan.py show
```

## Commands

- `init`: create `/.deeplan/` files
- `plan`: create/update plan and run automatic QA
- `replan`: append execution evidence and re-run automatic QA
- `decide`: add decision record
- `risk`: add risk record
- `qa`: run QA checks manually
- `show`: print current plan summary
- `ideate`: generate plan ideas from lightweight user context and optionally apply one

## Slash Command Mapping

If your agent supports slash commands, map them to CLI:
- `/deepplan` -> `python3 deepplan.py plan ...`
- `/deepplan.replan` -> `python3 deepplan.py replan ...`
- `/deepplan.decide` -> `python3 deepplan.py decide ...`
- `/deepplan.risk` -> `python3 deepplan.py risk ...`
- `/deepplan.qa` -> `python3 deepplan.py qa`

## Storage

- `/.deeplan/plan.json`
- `/.deeplan/decisions.jsonl`
- `/.deeplan/risks.jsonl`
- `/.deeplan/events.jsonl`

This is intentionally minimal and meant to be used by AI agents (Codex/Claude Code) as a common local planning primitive.
