# DeepPlan Strategist Agent

This document captures the product-intelligence agent direction for DeepPlan.
It is based on the premise that a successful service is not only a problem and a solution.
It is a repeatable experience that converts desire, emotion, behavior, and timing into retention or revenue.

## Thesis

DeepPlan should not become a generic planning document generator.

The stronger product direction is:

- attack weak ideas before execution
- prevent LLM agents from producing average AI wrappers
- convert ideas into monetizable user experience loops
- use external behavior references as creative raw material
- preserve the planning state, evidence, and revision trail in DeepPlan

The strategist agent is the layer that turns this into an operating loop.

## Why A Strategist Role

Planner, researcher, and reviewer are necessary but not sufficient.

- `planner` keeps direction state coherent.
- `researcher` captures evidence and references.
- `reviewer` handles human review and restore decisions.
- `strategist` judges whether an idea has product force before anyone builds it.

The strategist asks:

- Is the problem narrow and painful enough?
- Is the solution actually matched to that problem?
- Which desire or emotion creates buying or returning behavior?
- Is there a real experience loop, not just a feature list?
- Where is the monetization moment?
- Is this another generic LLM-generated service?
- What external references produced the core insight?
- What ethical, trust, community, or regulatory risk comes from the emotional loop?

## Core Evaluation Frame

The strategist evaluates ideas through these axes:

| Axis | Question |
| --- | --- |
| Problem-Solution | Who has the problem, how painful is it, what current alternative exists, and why is this solution the right response? |
| Desire-Emotion | Which desire or emotion moves the user: fear, greed, control, status, belonging, envy, anger, relief, or achievement? |
| Experience Loop | What is the trigger, emotional state, action, reward, monetization moment, and return reason? |
| Monetization Trigger | What exact moment makes payment feel natural or urgent? |
| Anti-Generic | Is this just another AI dashboard, todo app, CRM, assistant, or productivity wrapper? |
| Reference-to-Insight | Which behavior data, papers, reviews, success cases, or failure cases created the insight? |
| Risk Boundary | Does the loop rely on exploitation, toxic conflict, resentment, or fragile trust? |

## Product Loop

The intended loop is:

```text
idea
  -> strategist evaluation
  -> reference discovery if evidence is weak
  -> plan update if the direction is sharp
  -> review request if the decision is risky
  -> build only after the idea survives the gate
```

The strategist does not replace DeepPlan's kernel.
It reads the current plan, produces a strategy report, and may request review.
It should not bypass host capabilities or mutate plan state directly.

## First Runnable Scaffold

The scaffold includes:

- role: `strategist`
- profile: `strategist_product`
- action: `evaluate_experience_strategy`
- skills:
  - `problem-solution-pressure`
  - `desire-emotion-map`
  - `experience-loop-design`
  - `anti-generic-insight`
  - `reference-to-insight`

Run it locally:

```bash
PYTHONPATH=scaffolds/deepplan_agents/src \
python3 -m deepplan_agents.console run \
  --role strategist \
  --action evaluate_experience_strategy \
  --payload-json '{"idea":"AI productivity dashboard","target_user":"solo builder","solution":"dashboard"}'
```

Expected behavior:

- generic service patterns are detected
- weak problem-solution structure is flagged
- missing emotional demand and repeat loop are called out
- missing evidence is converted into concrete research questions
- the agent proposes a sharper positioning rewrite
- monetization is tied to a specific trigger and emotional state
- negative emotional loops are surfaced as risk boundaries
- output recommends `revise_before_build` or `stop_and_research`

## Strategy Report Shape

The first scaffold returns a deterministic report with these fields:

- `overall_score`
- `decision`
- `axes`
- `emotion_drivers`
- `risk_boundaries`
- `generic_patterns`
- `missing_fields`
- `risks`
- `recommendations`
- `research_questions`
- `next_actions`
- `positioning_rewrite`
- `monetization_moment`

The future LLM-backed strategist should preserve this shape.
The model can improve judgment quality, but hosts should still receive stable fields that can drive gates.

`next_actions` is the bridge from judgment to execution.
The strategist does not execute actions directly.
It recommends host-understood actions such as:

- `update_plan` when an idea should be sharpened or preserved
- `capture_evidence_cycle` when research is required before build
- `request_review` when a risk boundary needs human judgment

Each next action includes:

- `target_role`: the agent role that should execute it
- `action`: the host action name
- `priority`: `low`, `medium`, or `high`
- `reason`
- `payload`

## LLM Reasoning Contract

The scaffold now includes a provider-neutral prompt bundle for the future LLM strategist:

- system prompt: `scaffolds/deepplan_agents/src/deepplan_agents/prompts/strategist-system.md`
- output schema: `scaffolds/deepplan_agents/src/deepplan_agents/schemas/strategy-report.schema.json`
- prompt builder: `scaffolds/deepplan_agents/src/deepplan_agents/strategy_prompt.py`
- provider boundary: `scaffolds/deepplan_agents/src/deepplan_agents/strategy_llm.py`

The prompt bundle includes:

- the idea payload
- the current DeepPlan snapshot
- the required JSON schema

Generate it without calling a model:

```bash
PYTHONPATH=scaffolds/deepplan_agents/src \
python3 -m deepplan_agents.console prompt
```

This keeps provider integration separate from the product reasoning contract.
Any future OpenAI, local model, or hosted agent adapter should preserve the same report shape.

The provider boundary is intentionally small:

```python
class StrategyLLMProvider(Protocol):
    def complete_json(self, *, messages, schema) -> dict:
        ...
```

That means the first real adapter only needs to:

1. receive the prompt messages and report schema
2. call the model with structured JSON output
3. return a JSON object
4. let `run_strategy_llm` validate the report shape before the host consumes it

The scaffold includes a static provider for tests and local contract checks.

## Routing Next Actions

The scaffold also includes a route validator:

- route helper: `scaffolds/deepplan_agents/src/deepplan_agents/strategy_routes.py`
- console command: `deepplan-agents route`

It checks each `next_actions` item against the local host action contract.
For example, a `target_role` of `researcher` can receive `capture_evidence_cycle`, but a `reviewer` cannot receive `update_plan`.

This keeps LLM output useful without letting it bypass role capabilities.

## Design Rule

DeepPlan should not make the user feel that planning is paperwork.
It should make the user feel that weak ideas are being attacked before they waste build time.

The emotional promise of the product is:

- less anxiety about building the wrong thing
- more confidence that the direction has market and emotional force
- higher odds of finding non-generic service ideas
- a stronger sense of control over AI-driven execution
