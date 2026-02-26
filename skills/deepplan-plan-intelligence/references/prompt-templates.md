# Prompt Templates

Use these when invoking `$deepplan-plan-intelligence`.

## Codex Prompt

Use `$deepplan-plan-intelligence` in this repo and keep the work plan-only.
Run `python3 deepplan.py show` and `python3 deepplan.py qa` first.
Then improve long-horizon plan quality using:
- `planning_horizon`, `review_cadence`, `phase_plan`
- 8 insight axes coverage
Generate and apply an insight pack if needed:
`python3 deepplan.py insight --topic "<topic>" --references "<r1,r2,r3>" --apply`
Return only planning summary, risk signals, and next planning questions.

## Claude Prompt

Use `$deepplan-plan-intelligence` for planning only.
Do not provide implementation steps.
Start with `show` and `qa`, then improve plan quality and long-horizon structure.
If insight depth is low, run the insight command and apply results.
Finish with: direction statement, horizon/cadence, top risks, and unresolved planning questions.
