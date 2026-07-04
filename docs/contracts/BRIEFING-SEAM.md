# Operator Briefing Seam

## Status

**Shell-consumed.**

`GET /api/briefing` is implemented in the control-plane and loaded by the
console shell during bootstrap. The right-dock `BriefingPanel` renders canonical
`OperatorBriefing` fields for `top_signals`, `connectivity`, `pending_approvals`,
and `next_safe_actions`.

Approval execution remains on the dedicated run approval seam (`/api/runs`
approve/reject actions). The briefing panel is display-only for operator guidance.

## Contract

Backend owner:

- `services/control-plane/app/operator_briefing.py`

Shared DTO:

- `packages/shared-types/src/briefing.ts`

Shell owner:

- `apps/console-web/src/stores/shell.ts` (`loadOperatorBriefing`)
- `apps/console-web/src/components/BriefingPanel.vue`

Verification:

- `tests/test_control_plane_operator_briefing.py`
- `apps/console-web/src/lib/briefing-panel-view.test.ts`

## Watch/Inbox Gate

When watch connectivity is degraded, briefing must not surface inbox signals that
runtime summary would omit.

Both projections gate inbox-derived top signals on
`runtime_summary.watch.connected`.

## Display Rules

- Render `connectivity`, `top_signals`, `pending_approvals.count`,
  `pending_approvals.items`, and `next_safe_actions` directly from
  `OperatorBriefing`.
- Do not invent alternate labels for briefing projection fields.
- Do not add duplicate approve/reject controls in the briefing panel; use the
  existing approval action seam for mutations.
