# DeepPlan Agents Bootstrap

This document is for the separate repo that will orchestrate DeepPlan inside a multi-agent runtime.

The goal is not to move DeepPlan logic into that repo.
The goal is to build around DeepPlan while keeping planning state authoritative in one place.

## Repo Thesis

Recommended split:

- `deep-plan`: planning kernel, QA, revisions, restore, planning memory
- `deepplan-agents`: orchestration, agent roles, runtime coordination, host-side event model

DeepPlan should remain `plan-only`.
The integration repo should own execution orchestration.

## Suggested Repo Shape

```text
deepplan-agents/
  pyproject.toml
  README.md
  src/
    deepplan_agents/
      adapters/
        deepplan_adapter.py
      workflows/
        planner_loop.py
        research_loop.py
        review_loop.py
      agents/
        planner_agent.py
        researcher_agent.py
        reviewer_agent.py
      runtime/
        host_events.py
        policies.py
        decision_gate.py
      config/
        settings.py
  tests/
    test_adapter.py
    test_planner_loop.py
```

## Minimal Runtime Contract

The host repo should treat DeepPlan as one dependency with one main boundary:

```python
from deepplan_sdk import DeepPlanClient
```

The host runtime should not mutate DeepPlan state ad hoc.
All writes should go through one adapter layer.

## First Adapter Responsibilities

`deepplan_adapter.py` should own:

- `snapshot()`
- `apply_plan_update()`
- `capture_evidence_cycle()`
- `preview_restore_previous()`
- `restore_previous()`
- error translation from DeepPlan exceptions into host events

The adapter should be the only place that knows:

- retry policy
- health gate policy
- idempotency key policy
- history window policy

## First Workflow

Start with one narrow loop:

1. planner reads `get_cycle()`
2. planner proposes one plan update
3. adapter applies `apply_and_get_cycle_with_retry("update_plan", ...)`
4. runtime checks:
   - `qa.result`
   - `qa.score`
   - `health.status`
   - `changed_fields`
5. if planning quality drops, stop and route to reviewer
6. if planning quality improves, allow next agent step

## Recommended Agent Order

Phase 1:

- `Planner`
- `Reviewer`

Phase 2:

- `Planner`
- `Researcher`
- `Reviewer`

Phase 3:

- `Planner`
- `Researcher`
- `Reviewer`
- optional execution-facing host agent

Do not start with too many agents.
The first integration should prove that planning state stays coherent under repeated writes.

## Decision Policy

Use simple gates first:

- if `health.status != "ok"`: block autonomous writes
- if `qa.result == "CRITICAL_FAILURE"`: stop and route to reviewer
- if `qa.score` improves and no critical signal appears: continue
- if stale write conflict occurs twice: stop and refresh the planning step

## Idempotency Policy

The integration repo should generate stable host-side keys for append-style flows.

Examples:

- `session-42:research-3:evidence-cycle`
- `session-42:review-1:replan`

Then pass that key into:

- `capture_evidence_cycle(..., idempotency_key=...)`
- append-style direct mutations when needed

## First Success Criteria

The integration repo is good enough for a first working milestone when:

- planner updates can run through the adapter end-to-end
- append flows do not duplicate writes on retry
- review can preview and restore previous revisions
- host runtime can branch cleanly on conflict vs health vs operation failure
- all planning state still lives in DeepPlan

## Non-Goals

The first integration repo should not try to solve:

- generalized agent memory
- distributed queues
- multi-tenant auth
- channel bots
- full operator dashboard

Keep the first repo small enough to prove the kernel boundary, not to build the whole company OS in one step.
