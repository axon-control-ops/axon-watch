# Gate 0 — Pause and preserve evidence

**Date:** 2026-07-21  
**Plan:** `docs/AXON-X-AUTONOMY-MASTER-PLAN.md` Gate 0  
**Operator action:** Preserve dirty trees; do **not** reset/discard without explicit ask.

---

## Scheduler pause

Captured from `GET /api/worker-scheduler`:

```json
{
  "scheduler_enabled": false,
  "effective_enabled": false,
  "env_allowed": true,
  "max_active": 4,
  "max_starts_per_tick": 1,
  "tick_interval_seconds": 45.0,
  "dispatch_enabled": true,
  "executing_count": 0,
  "active_run_count": 0,
  "employee_enabled": {
    "workspace_dashpro:watcher": true
  },
  "updated_at": "2026-07-20T17:14:58Z"
}
```

**Disposition:** Continuous worker mutation is **paused** (`effective_enabled: false`).  
Leave it off through Gates 0–2 unless the operator explicitly re-enables it.

Note: `dispatch_enabled` remains true (env); that only matters if the scheduler is turned back on.

---

## Active non-employee runs (not continuous workers)

| Run ID | Workspace | Phase | Role | Summary (truncated) | Disposition |
| --- | --- | --- | --- | --- | --- |
| `run_a3a0e0ab2e63` | `workspace_dashpro` | executing | _(none)_ | Publish OTA so Marrion gets the banner on canary… | **KEEP / active** — operator/IDE OTA work; do not cancel during Gate 0 |

Continuous-employee executing count at capture: **0**.

> **Later note (2026-07-21T14:46Z+):** Re-check showed `run_a3a0e0ab2e63` ended as `phase=failed` / `status=error` (ended ~14:15Z). Gate 0’s KEEP disposition still applied while it was live; do not treat it as still executing. A different non-employee run may be active afterward — re-query `/api/runs` before acting.

---

## DashPro dirty-tree inventory

**Root:** `/home/edp/Projectx/product/dashpro`  
**Branch:** `development` (ahead 4, behind 3 vs `origin/development` at capture)

| Path | Status | Likely cluster | Probable owner | Disposition |
| --- | --- | --- | --- | --- |
| `app/_layout.tsx` | modified | OTA / update confirmation | operator IDE runs (`run_a3a0e0ab2e63` + prior OTA canary runs) | **KEEP** |
| `contexts/UpdatesProvider.tsx` | modified | OTA / update confirmation | same | **KEEP** |
| `lib/navigation/safeRouter.ts` | modified | OTA / navigation safety | same | **KEEP** |
| `components/updates/UpdateConfirmationBridge.tsx` | untracked | OTA confirmation UI | same | **KEEP** |
| `lib/ota/` (`pendingUpdateStorage.ts`, `requestUpdateConfirmation.ts`) | untracked | OTA helpers | same | **KEEP** |
| `tests/unit/ota/` | untracked | OTA tests | same | **KEEP** |
| `components/affiliation/` (`AffiliationConfirmationBanner.tsx`, `AffiliationConfirmationBridge.tsx`) | untracked | affiliation confirmation canary | same OTA/canary operator thread | **KEEP** |
| `hooks/useParentAffiliationPending.ts` | untracked | affiliation confirmation | same | **KEEP** |
| `components/pricing/.axon-x-intent-verify.txt` | deleted | Axon-X verify markers | prior agent verify scaffolding | **HOLD** — do not restore unless needed for a verify script |
| `lib/notifications/.axon-x-intent-verify.txt` | deleted | Axon-X verify markers | prior agent verify scaffolding | **HOLD** |
| `lib/payments/.axon-x-intent-verify.txt` | deleted | Axon-X verify markers | prior agent verify scaffolding | **HOLD** |

**Attribution caveat:** Recent DashPro runs with `employee_role: null` dominate the timeline (OTA / canary / fee-check prompts). These are **not** continuous-worker shifts. Exact file↔run blame is incomplete without per-run diff receipts; clusters above are best-effort from run summaries + path names.

**Preserve rule:** No `git reset --hard`, no discard of untracked OTA/affiliation work during Gates 0–2.

---

## Axon-X (`axon-watch`) dirty tree — preserve note

At capture the Axon-X worktree had a large dirty set (~86 short-status lines), including:

- Gate 2 auth modules under `services/control-plane/app/auth/`
- Autonomy plan/readiness/PDF docs
- Unrelated console/desktop/galaxy work in progress

**Disposition:** **PRESERVE entire dirty tree.** Gate 1/2 work continues in-place; do not attribute all Axon-X dirt to autonomy gates.

---

## Gate 0 exit checklist

| Criterion | Status |
| --- | --- |
| Scheduler mutation paused | **Met** (`effective_enabled: false`) |
| Every changed DashPro path has owner + disposition | **Met** (table above; HOLD/KEEP) |
| No continuous worker writing during triage | **Met** (employee executing_count 0) |
| Evidence recorded | **This file** |

**Gate 0 result:** CLOSED for proceeding to Gate 1, with OTA run `run_a3a0e0ab2e63` left running as intentional operator work.
