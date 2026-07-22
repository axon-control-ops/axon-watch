# Recent operator features (Gate 3–5 + console UX)

**Updated:** 2026-07-22  
**Audience:** operators and agents who need plain-language “what changed and how to use it.”

Companion to [`docs/HOW-TO-HANDBOOK.md`](../HOW-TO-HANDBOOK.md) and
[`autonomy-gates-and-service-identity.md`](autonomy-gates-and-service-identity.md).

---

## 1. Mission Control task board (Gate 4)

### What it is

A durable **task ledger**. Continuous workers may only start when they **lease** an
open task. The board lives on Operator → **Grid** (not the Brain Graph starfield).

### How to use it

1. Switch layout to **OPERATOR**.
2. In Mission Control, choose **Grid** (not Brain Graph).
3. Under **Fleet health**, open **Task board**.
4. Create a goal + owner role (e.g. `integrations`).
5. Leave the worker scheduler **off** unless you intentionally want continuous shifts.

### Example — seed work for Soren

```bash
curl -sS -X POST http://127.0.0.1:8787/api/workspaces/workspace_dashpro/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "goal": "Verify quality-gate heap calc does not OOM CI",
    "acceptance_criteria": "Targeted node-heap tests pass with receipts",
    "owner_role": "integrations",
    "attempt_budget": 2
  }' | jq '{task_id, status, owner_role}'
```

Expect `"status": "open"`. When the scheduler is enabled, that role claims/leases it
before `create_run`.

### Example — list open tasks

```bash
curl -sS 'http://127.0.0.1:8787/api/workspaces/workspace_dashpro/tasks?status=open' \
  | jq '.items[] | {task_id, goal, owner_role}'
```

---

## 2. Concurrent IDE conversation tabs

### What changed

Switching conversation tabs **no longer stops** another teammate’s live stream.
Each IDE thread keeps its own SSE session.

### Example

1. Start an agent on **Soren**.
2. Open **Marco** and start (or watch) another run.
3. Switch back to Soren — his stream continues; the busy glow stays on both tabs.

Stop still applies to the **focused** thread only.

---

## 3. Brain Graph workspace labels + colors

### What changed

Every **named workspace** orb shows a label (DashPro included). Orbs get a **muted
stable tint** from `workspace_id` so they are easier to spot. Health tones
(attention / critical) still override.

### Example

Operator → Brain Graph → select DashPro in the left rail → the **DASHPRO** chip
appears on its orb. Unlabeled spheres are usually signals/connectors/runs, not
workspaces.

---

## 4. Lead planner (Gate 5 — started)

### What it is

A pure planner (`build_lead_task_plan`) that turns one goal + company roster into
ordered plan items (owner role, deps, acceptance). **Not yet** auto-persisted to
the ledger or auto-dispatched.

### Examples

**Fan-out** (all specialists in parallel, path conflicts serialized):

```text
Goal: "Check with all sub-agents whether DashPro quality-gate heap calc is safe"
→ plan items for watcher, frontend, backend, integrations (no Lead item)
```

**Sequential** (then-chains):

```text
Goal: "Fix the API quality-gate heap calc then update the Expo confirmation screen"
→ backend item, then frontend item that depends on the backend plan_key
```

Proof:

```bash
./scripts/dev/python.sh -m unittest tests.test_lead_task_plan -q
```

---

## 5. After every push — watch Fast Gate

### Why

`feat/*` and PRs to `dev` must keep **Axon-X Fast Gate** green. A red push blocks
merge and often means file-size ratchets or unit tests.

### Operator / agent command

```bash
# From repo root — polls the latest Fast Gate run for this branch
./scripts/ops/watch-fast-gate.sh
```

Or manually:

```bash
gh run list --branch "$(git branch --show-current)" --workflow "Axon-X Fast Gate" --limit 3
gh run watch   # follows the newest in-progress run
gh run view --log-failed   # when red
```

### Who owns CI for which company

| Workspace | Who watches CI |
| --- | --- |
| **Axon-X** (`workspace_axon_watch`) | **Rowan** (watcher) + **Mira** (Lead triage) — Fast Gate for this repo |
| **DashPro** | **Cass** (watcher) + **Soren** (integrations / Actions) |
| Child workspaces | Watcher role for that company; escalate to Lead |

VAXON / the Axon-X watcher should treat **this repository’s Fast Gate** as part of
runtime health after any push to `origin`.

---

## 6. What is still off on purpose

| Control | State | Why |
| --- | --- | --- |
| Continuous worker scheduler | **Off** by default | Needs leased tasks + Lead/fan-out before unattended shifts |
| Live-checkout continuous edits | **Forbidden** | Gate 3 isolation — workers use disposable worktrees |
| Gate 5 full fan-out dispatch | **In progress** | Planner exists; persist + N-run dispatch next |

Check scheduler:

```bash
curl -sS http://127.0.0.1:8787/api/worker-scheduler \
  | jq '{scheduler_enabled, effective_enabled, executing_count}'
```
