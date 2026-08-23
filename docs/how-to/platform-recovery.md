# Platform recovery, stale runs, and clean baseline

**Updated:** 2026-08-20

This is the operator map for Axon-X recovery. It describes the implementation,
not the mission prompt.

## What is happening

Durable run phases are unchanged (`queued` … `completed` / `failed` / `cancelled`).
Recovery Center **projects** additional buckets:

`ACTIVE`, `STALE`, `ORPHANED`, `RESUMABLE`, `RETRYABLE`, `FAILED`, `BLOCKED`, `HUMAN_REVIEW`

Heartbeat receipts prove the worker process is alive. They do **not** prove
progress. Meaningful progress writes a checkpoint.

## Canonical commands

```bash
./scripts/ops/platform-doctor.sh          # platform doctor
./scripts/ops/platform-reconcile.sh       # dry-run artefact reconcile
./scripts/ops/platform-reconcile.sh --execute
./scripts/verify/clean-baseline.sh        # VERIFY CLEAN BASELINE
```

Aliases:

- `platform doctor` → `./scripts/ops/platform-doctor.sh`
- `platform reconcile` → `./scripts/ops/platform-reconcile.sh`
- `npm run doctor`
- `npm run verify:clean-baseline`

## Restart

These recovery HTTP routes exist only in the process that imported the current
tree. A control-plane started before that code was saved will 404
`GET /api/recovery/center` until that unit is restarted.

Before restarting, call `GET /api/recovery/restart-preview` (after the new
process is loaded) or inspect busy `runs` + whether
`.local/state/control-plane-recovery.sqlite3` has a checkpoint for that
`run_id`.

If a valid checkpoint exists, restart pauses the employee run as `RESUMABLE`
and keeps the lease — including a second restart while already paused.
Resume from Recovery Center or `POST /api/recovery/runs/{run_id}/resume`.

If there is **no** checkpoint, restart still **cancels** the employee run and
reopens the task. systemd `KillMode=mixed` also stops control-plane child
worker sandboxes.

Prefer `systemctl --user restart control-plane.service` over
`scripts/dev/restart.sh` when Watch and console-web should stay up.

## Clear does not mean delete

Recovery Center actions are Reconcile, Resume, Retry, Cancel, Archive,
Acknowledge. Acknowledge never changes operational state; it only marks the
recovery record seen.

## Instructions button

The IDE **Instructions** button converts the composer draft into structured
`# Instructions` markdown (goal, scope, steps). Live recovery state belongs in
Recovery Center (`POST /api/recovery/instructions`), not this button.

## Self-heal ladder

`AXON_WATCH_SELF_HEAL_LEVEL` (default `1`):

| Level | Name |
| --- | --- |
| 0 | Diagnostic only |
| 1 | Auto-reconcile |
| 2 | Auto-retry low-risk |
| 3 | Auto-resume checkpointed work |
| 4 | Auto-repair verified low-risk |
| 5 | Supervised multi-step |

Auth failures and UNKNOWN never auto-retry.

## Sensitive reads

Anonymous `GET /api/vault/secrets`, vault export, and Watch vault/data snapshot
reads require operator or internal-service identity when token mode is on.
