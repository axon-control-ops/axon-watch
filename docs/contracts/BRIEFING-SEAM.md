# Operator Briefing Seam

## Status

**Shell-consumed.**

`GET /api/briefing` is implemented in the control-plane and loaded by the
console shell during bootstrap. The shell uses that projection across the right
dock: approvals and signals seams read briefing-backed summaries, while the
KAIRO briefing card stays a summary / CTA surface rather than a raw DTO dump.

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

- Keep `OperatorBriefing` as the canonical projection source for dock summaries.
- It is acceptable to present briefing data across multiple seams (approvals,
  signals, KAIRO card) rather than rendering one raw field-by-field DTO panel.
- Do not invent alternate labels for briefing projection fields.
- Do not add duplicate approve/reject controls in the briefing panel; use the
  existing approval action seam for mutations.
