# ADR-003: Shell Consumes Operator Briefing In The Right Dock

## Status

Accepted

## Context

ADR-002 kept `GET /api/briefing` backend-only during stabilization so run-state,
approval boundaries, and projection ownership could land first without a second
operator-action surface drifting ahead of the run seam.

That stabilization pass is complete:

- persisted run truth and explicit approval boundaries are in place
- `/api/briefing` is implemented with shared DTOs and contract tests
- the console shell now loads briefing at bootstrap and renders it in the right dock

The product still needs a clear rule for how briefing relates to approval mutations.

## Decision

The console shell consumes `OperatorBriefing` at bootstrap and after run
mutations:

- `loadBootstrapData()` fetches `/api/briefing` in parallel with runtime summary,
  inbox, runs, and workspaces
- the right-dock `BriefingPanel` renders `pending_approvals` and
  `next_safe_actions` directly from the canonical DTO
- approve/reject execution remains on the dedicated run approval seam; the
  briefing panel is display-only for operator guidance

Briefing must continue to gate inbox-derived signals consistently with runtime
summary when watch connectivity is degraded.

## Alternatives Considered

### Keep briefing backend-only indefinitely

Rejected because the operator console now needs a canonical guidance surface and
the approval boundary is already locked.

### Add approve/reject buttons inside the briefing panel

Rejected because it would duplicate mutation affordances and blur ownership
between briefing projection and the explicit run approval seam.

### Rewrite ADR-002 in place

Rejected because accepted ADRs are immutable; this ADR supersedes the briefing
portion of ADR-002 without rewriting history.

## Trade-Offs

- Gains operator-visible guidance without inventing local briefing semantics
- Preserves a single mutation surface for approve/reject actions
- Requires doc and ADR hygiene when briefing behavior changes again
- Briefing still renders only a subset of `OperatorBriefing` in the first shell slice

## Consequences

### Positive

- shell boot and run refresh stay aligned with backend briefing truth
- operators can see pending approvals and next safe actions without reading raw JSON
- approval execution remains explicit and testable on `/api/runs` approve/reject routes

### Negative

- two related surfaces now exist in the right dock: briefing guidance and approval actions
- docs and ADRs must track shell consumption going forward
- future KAIRO cards may require another ADR if briefing presentation widens materially

## Reevaluation Triggers

Reevaluate this ADR if:

- briefing actions become executable directly from the briefing panel
- briefing begins owning mutations instead of read-only guidance
- a richer KAIRO card model replaces the current `BriefingPanel` projection

## Notes

Supersedes the backend-only briefing consumption portion of ADR-002.
