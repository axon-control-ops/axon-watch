# Operator Briefing Seam

## Status

**Backend-only for the stabilization pass.**

`GET /api/briefing` is implemented and verified in the control-plane, but the
console shell does not consume it yet.

## Why Deferred In The Shell

The shell already has dedicated seams for:

- run controls (`/api/runs`, runtime summary active runs)
- approvals (`/api/runs/{run_id}/approve|reject`, runtime summary approvals)
- signals (`/api/inbox`, runtime summary signals)

Wiring `/api/briefing` into the shell before the approval boundary was locked
would have introduced a second operator-action projection surface and increased
drift risk.

## Current Contract

Backend owner:

- `services/control-plane/app/operator_briefing.py`

Shared DTO:

- `packages/shared-types/src/briefing.ts`

Verification:

- `tests/test_control_plane_operator_briefing.py`

## Watch/Inbox Gate

When watch connectivity is degraded, briefing must not surface inbox signals that
runtime summary would omit.

Both projections now gate inbox-derived top signals on
`runtime_summary.watch.connected`.

## Next Slice Trigger

Wire briefing into the shell only when:

1. approval boundary is locked (`awaiting_approval` is not generic-resumable)
2. approval seam targets the dedicated approval run
3. a single operator-action projection strategy is chosen explicitly

Until then, treat `/api/briefing` as a backend contract and verification seam,
not a live shell dependency.
