# VAXON fleet self-heal — detect → classify → fix → verify → prevent

**Added:** 2026-08-06

When axon-watch's own dispatch/sandbox/runtime code breaks (not a product bug
in a customer workspace — a bug in the control plane itself, the kind that
makes agents "constantly error out and get stuck"), control-plane can detect
the failure pattern from its own run history, classify it as fleet-infra,
dispatch a real repair task to Rowan (watcher), verify the fix through the
same Gate 6 + Critical Review machinery every leased task already goes
through, and remember it so a regression is recognized immediately instead
of being re-diagnosed from scratch.

Mirrors Gate 9 CI remediation's shape (`app/ci_remediation/`) closely, and
closes the one gap Gate 9 has: no persistent "don't retry this the same
broken way again" memory.

## What is wired

| Stage | Behavior |
|---|---|
| Detect | Scheduler-tick scan of `run_store` failed runs (`config/autonomy-work-sources.json` → `fleet_self_heal_detect`, default every 5 min, 6h rolling window) — not gated by per-workspace `autonomy_mode`, same as Gate 9 |
| Classify | `app/fleet_self_heal/classify.py` — defers to the existing usage/billing/auth/shift-continuation gates first; a Python traceback frame inside `services/control-plane/app/` or a known marker phrase (recursion, sandbox path, stale MCP config, ...) is fleet-infra |
| Dispatch | Real `task_store` task, goal prefix `VAXON fleet repair [<fingerprint>]`, **always** targets `workspace_axon_watch` regardless of which workspace's run surfaced the failure — a bug in axon-watch's own code can't be fixed from inside a customer workspace's checkout |
| Verify | Free — any task-bound run automatically requires Gate 6 acceptance evidence + Critical Review Confidence before it can complete (`verifier_contract.py`); acceptance criteria additionally require a regression test and a green Fast Gate on a throwaway branch |
| Report | Worker posts `POST /api/fleet-self-heal/report-outcome` (fingerprint, success, commit_ref, detail) → signal + spoken line; scheduler-tick reconciliation recovers the outcome from task completion if the callback is missed |
| Prevent | `fleet_repair_events` state machine: `observed → dispatched → repairing → verified_fixed`; a fingerprint reoccurring after `verified_fixed` is a **regression** (dispatches immediately, flagged so the repair agent doesn't just resubmit the same diff); `max_dispatch_cycles` exhausted → `blocked` + Lead escalation ticket |

**Still human-gated:** merge to `dev`/`master` (branch-protected, requires a
green `fast-gate` PR check — see `config/vaxon-fleet-repair.json`'s
`push_policy: "draft_pr"`), force-push, secrets.

**`dispatch_enabled`** in `config/vaxon-fleet-repair.json` starts `false` —
detect stays in dry-run (populates the store, logs what it would dispatch)
until the threshold numbers (`repeat_occurrence_threshold`,
`breadth_pair_threshold`) have been sanity-checked against real fleet
history. Flip it once a dry-run observation period confirms the thresholds
aren't too eager or too quiet.

## Config

[`config/vaxon-fleet-repair.json`](../../config/vaxon-fleet-repair.json):

- `target_workspace_id` — always `workspace_axon_watch`
- `defaults.owner_role` — `watcher` (Rowan already owns "runtime health and
  Axon-X Fast Gate" per `config/workspace-agents.json`); `subsystem_role_overrides`
  can route specific subsystems (e.g. persistence/scheduler internals) to `backend`
- `defaults.max_dispatch_cycles` — full dispatch cycles (each up to
  `attempt_budget_per_dispatch` leases) before a fingerprint goes `blocked`
  and escalates to Lead instead of retrying forever
- `defaults.window_hours` / `repeat_occurrence_threshold` / `breadth_pair_threshold` —
  when an observed cluster becomes dispatchable: either the same
  `(workspace, role)` failing repeatedly, or the same fingerprint appearing
  across ≥2 distinct `(workspace, role)` pairs

## Double-dispatch guard

`app/workspace_agents/lead_checkin_assign.py::assign_owner_role_for_failed_shift`
already turns most failed shifts into a generic `VAXON attend:` auto-dispatch
task assigned to the *same* role, in the *same* workspace that failed — correct
for a product bug, wrong for a fleet-infra bug (that workspace's specialist
can't fix a bug that isn't in their repo). A `quick_fleet_infra_marker_match`
check routes fleet-infra failures to `escalate_only=True` instead, so the
generic loop still surfaces it to a human but doesn't spawn a dead-end fix task.

## Operator surfaces

- **Attention / inbox** — signal source `fleet_self_heal`, merged in control-plane
  inbox projection (`app/inbox_projection.py`); `high`/`critical` severity interrupts
- **Task board** — leased `VAXON fleet repair [...]` task for Rowan (escalate role `lead`)
- **Voice** — report-outcome returns a `spoken` line

## Local verify

```bash
./scripts/dev/python.sh -m unittest \
  tests.test_fleet_self_heal_classify \
  tests.test_fleet_self_heal_store \
  tests.test_fleet_self_heal_config \
  tests.test_fleet_self_heal_detect \
  tests.test_fleet_self_heal_dispatch \
  tests.test_fleet_self_heal_wiring \
  tests.test_fleet_self_heal_gate6_enforcement \
  tests.test_fleet_self_heal_report \
  tests.test_run_store_list_failed_runs_since \
  -v
```

Manual dry-run drill: leave `dispatch_enabled: false`, trigger a known
fleet-infra failure signature, confirm it shows up in
`fleet_repair_events` (observed, not dispatched) with the expected
fingerprint/subsystem. Never flip `dispatch_enabled: true` without an
observation period first.
