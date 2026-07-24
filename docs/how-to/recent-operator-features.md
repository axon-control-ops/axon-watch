# Recent operator features (Gate 3–5 + console UX)

**Updated:** 2026-07-22  
**Audience:** operators and agents who need plain-language “what changed and how to use it.”

Companion to [`docs/HOW-TO-HANDBOOK.md`](../HOW-TO-HANDBOOK.md) and
[`autonomy-gates-and-service-identity.md`](autonomy-gates-and-service-identity.md).

---

## 1. Mission Control task board (Gate 4)

### Where it is (easy to miss)

**Mission Control** is the Operator **center panel** — but only in **Grid** view.

Your Brain Graph starfield (VAXON CORE / DashPro orbs) is Operator too; it **replaces**
the Mission Control title, Fleet health, and Task board until you leave Graph.

| You are here | How to open Task board |
| --- | --- |
| Top nav **OPERATOR** + Brain Graph | Click **Mission Control** in the bottom status chips, **or** **Mission Control · Task board** in the right Intelligence panel |
| Operator Grid already | Scroll under **Fleet health** → section **Task board** |
| Top nav **IDE** | Click **OPERATOR** first, then use Grid / Mission Control as above |

On Grid you should see the heading **Mission Control**, then **GRID | BRAIN**, then
**Fleet health**, then **Task board**.

### What the task board is

A durable **task ledger**. Continuous workers may only start when they **lease** an
open task. Chat in the IDE is separate (see “Talk vs do work” below).

### How to use it

1. Top nav → **OPERATOR**.
2. Leave Brain Graph: **Mission Control** chip (or Intelligence → **Mission Control · Task board**).
3. Under **Fleet health**, use **Task board**.
4. Create a goal + owner role (e.g. `integrations`).
5. Leave the worker scheduler **off** unless you intentionally want continuous shifts.

### Talk vs do work (IDE teammate modes)

In the IDE agent dock, open the mode chip (bottom-right, often **Agent FULL ACCESS**):

| Mode | Use when |
| --- | --- |
| **Ask** | Simple conversation — “thanks”, questions, status — **no** edits/tools |
| **Plan** | Map steps before changing code |
| **Agent** | Do the task — tools, edits, approvals |
| **Debug** | Reproduce and fix with evidence |
| Task board / Lead fan-out | Durable assigned work across specialists (Gate 4–5) |

**Examples**

- “Thank you Dana!” / “I am thinking…” → stay on **Ask** (conversation).
- “Ok proceed with that.” / “Fix the payments race” → **Agent** (task).
- “Check with all sub-agents…” → Lead fan-out (N tasks/runs), not one specialty winner.

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

## 4. Lead planner + fan-out (Gate 5)

### What it is

Dana (Lead) turns one goal + company roster into ordered plan items, **persists**
them as leased `workspace_tasks`, and for fan-out opens **one run per ready
specialist** (not a single specialty-route winner).

| Piece | Module / API |
| --- | --- |
| Pure plan | `build_lead_task_plan` |
| Persist | `persist_lead_task_plan` → Gate 4 ledger |
| Materialize | `materialize_lead_fan_out` → tasks + ready runs |
| HTTP | `POST /api/workspaces/{id}/lead/plan` · `.../lead/fan-out` |

Continuous **dispatch** (Lane B) is still separate — fan-out creates leased tasks
and **queued** runs with `lead_fan_out_assigned` receipts (not fake-executing).
Assignment is posted into each specialist IDE thread. The scheduler (when on)
promotes queued fan-out runs into Lane B; keep it off until Gate 6 is solid.

### Examples

**Fan-out** (all specialists in parallel; path conflicts serialize / defer):

```text
Goal: "Check with all sub-agents whether DashPro quality-gate heap calc is safe"
→ tasks for watcher, frontend, backend, integrations
→ N ready runs with receipts (deferred if exclusive_paths overlap)
```

```bash
curl -sS -X POST "http://127.0.0.1:8787/api/workspaces/workspace_axon_watch/lead/fan-out" \
  -H 'content-type: application/json' \
  -d '{"goal":"Check with all sub-agents whether Gate 5 fan-out is wired"}' \
  | jq '{mode, run_count:(.runs|length), deferred:(.deferred|length), receipt}'
```

**Sequential** (then-chains → dependency task ids):

```text
Goal: "Fix the API quality-gate heap calc then update the Expo confirmation screen"
→ backend task, then frontend task that depends on the backend task_id
```

**Specialty route stays single-winner** for normal prompts; fan-out phrases return
`reason=lead_fan_out` instead of picking one teammate.

Proof:

```bash
./scripts/dev/python.sh -m unittest tests.test_lead_task_plan tests.test_lead_fan_out -q
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

## 6. Workspace company parity (vs DashPro)

DashPro is not a special UI — every bound workspace uses the same Team panel,
Mission Control, and Task board. What differed was **staffing**:

| Workspace | Company |
| --- | --- |
| DashPro / Axon-X / School | Named companies in `config/workspace-agents.json` |
| TPS / Young Eagles / Axon Local | Named companies (same shape as DashPro) |
| Other bound projects | Template staffing with **workspace-stable** names + voices (not Mira clones) |

After switching to **TPS** in IDE → Team, you should see **Noor / Blair / Vera / Hugo / Tess**,
not Mira/Rowan. Mission Control → Grid always keeps the **selected** workspace on the fleet
board even when many projects exist.

---

## 7. What is still off on purpose

| Control | State | Why |
| --- | --- | --- |
| Continuous worker scheduler | **Off** by default | Needs leased tasks + Lead/fan-out before unattended shifts |
| Live-checkout continuous edits | **Forbidden** | Gate 3 isolation — workers use disposable worktrees |
| Gate 5 full fan-out dispatch | **Partial** | Persist + ready runs land; Lane B auto-dispatch still manual / scheduler off |

Check scheduler:

```bash
curl -sS http://127.0.0.1:8787/api/worker-scheduler \
  | jq '{scheduler_enabled, effective_enabled, executing_count}'
```
