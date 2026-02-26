---
name: deepplan-plan-intelligence
description: Use when the user wants plan-only collaboration in the DeepPlan repo, especially for long-horizon planning, idea discovery from zero, insight generation, and improving planning quality before any task/implementation work.
---

# DeepPlan Plan Intelligence

## Overview

This skill runs DeepPlan as a plan-only copilot. It improves direction quality, insight depth, and long-horizon planning structure using the local `deepplan.py` CLI.

Use this skill when the user asks to:

- build or refine plans before execution
- find ideas from a zero-idea state
- generate broader viewpoints or references
- set a planning horizon (weeks/months), review cadence, and milestone phases
- improve DeepPlan QA coverage for insight axes

Do not use this skill for implementation workflows, coding tasks after planning, deployment, or debugging app runtime issues.

## Workflow

1. Baseline
- Run `python3 deepplan.py show`
- Run `python3 deepplan.py qa`

2. Horizon setup (required for long-horizon planning)
- Ensure `planning_horizon`, `review_cadence`, `phase_plan` are set
- Example:
```bash
python3 deepplan.py plan \
  --planning-horizon "12 weeks" \
  --review-cadence "weekly" \
  --phase-plan "phase1 framing,phase2 validation,phase3 refinement"
```

3. Insight expansion
- Generate viewpoint expansion and apply to the current plan:
```bash
python3 deepplan.py insight \
  --topic "<topic>" \
  --references "<success_case,fail_case,counter_view>" \
  --apply
```
- Focus on broadening perspective before deciding.

4. QA-driven refinement
- Run `python3 deepplan.py qa`
- If not passing, fill missing fields using `plan`/`replan` arguments, especially:
  - 8 insight axes:
    - `direction_insights`
    - `market_insights`
    - `timing_insights`
    - `differentiation_insights`
    - `monetization_insights`
    - `constraint_insights`
    - `risk_signal_insights`
    - `evolution_insights`
  - horizon fields:
    - `planning_horizon`
    - `review_cadence`
    - `phase_plan`

5. Return concise planning summary
- Direction statement
- Top risks and early signals
- Horizon and review cadence
- 1-3 next planning questions (not implementation tasks)

## Command Reference

- Baseline: `python3 deepplan.py show && python3 deepplan.py qa`
- Idea generation: `python3 deepplan.py ideate --profile "<profile>" --interests "<a,b,c>" --count 5`
- Plan update: `python3 deepplan.py plan --goal "<goal>" --success-metric "<metric>" --deadline "YYYY-MM-DD"`
- Insight pack: `python3 deepplan.py insight --topic "<topic>" --references "<r1,r2,r3>" --apply`
- Replan update: `python3 deepplan.py replan --evidence "<evidence>" --direction-insight "<insight>"`

See [references/prompt-templates.md](references/prompt-templates.md) for ready-to-use invocation prompts.

## Output Rules

- Keep focus on planning decisions and insight quality.
- Do not drift into coding implementation plans unless explicitly requested.
- Prefer evidence-backed and counter-viewpoint-inclusive insight generation.
