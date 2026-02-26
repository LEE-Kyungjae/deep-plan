# DeepPlan (MVP)

DeepPlan is a local, agent-friendly planning engine focused on one thing:
make planning quality a first-class product surface.

## Why DeepPlan

Most AI products are excellent at `task -> implement`.
DeepPlan focuses on the layer before that:

- what to build
- why now
- what not to build
- how to detect failure early

`Plan` is not prompt preparation.
`Plan` is the business and product decision layer.

## Product Thesis

In the AI era, implementation speed is no longer the main bottleneck.
Direction quality is.

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

## Core Loop

DeepPlan uses the full loop:

`plan -> task -> implement -> verify -> replan`

But it treats `plan` as the highest-leverage stage, not a formality.

## What It Provides

- Shared plan format (`schemas/plan.schema.json`)
- CLI (`deepplan.py`)
- Automatic quality checks on `plan` and `replan`
- Local state in `/.deeplan/`

## Quick Start

```bash
python3 deepplan.py init
python3 deepplan.py ideate --profile "solo builder" --interests "automation,creator tools" --count 5
python3 deepplan.py plan \
  --goal "Ship DeepPlan MVP CLI" \
  --success-metric "CLI supports plan/replan/decide/risk by 2026-03-15" \
  --deadline "2026-03-15" \
  --constraints "single developer, local repo only"
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
