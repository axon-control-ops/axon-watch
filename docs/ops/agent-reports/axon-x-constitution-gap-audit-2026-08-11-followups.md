# AXON-X Constitution Audit — 2026-08-11 Follow-up

This follow-up continues the ratcheted 2026-08-09 audit ledger without growing
that historical report beyond its file-size budget.

## Rerun result

`npm run verify:constitution` passed all nine executable checks:

- registry tables and the real `run_history` adapter shape;
- capability seed anchors;
- constitution router registration and required endpoints;
- mutating-auth middleware and route coverage;
- focused registry tests; and
- the implementation handoff ledger.

The gate currently covers 119 mutating routes, with two intentional exemptions.
This is evidence that the implemented constitution spine is intact; it is not
evidence that the full engineering constitution has been completed.

## Progress since the original audit

Implemented and guarded:

- Evidence, Mission, Decision, Capability, ADR, Technical Debt, and Platform
  Health registries.
- Evidence adapters for execution, Lead, autonomy, delivery, and host receipts.
- Persisted runtime-health capture and traceable autonomy/scheduler decisions.
- Lead-plan mission linking, receipt indexing, seed/backfill, and a read-only
  constitution console surface.
- Separate always-on observation scheduling from worker action authority.
- Lead-handoff dispatch rescue and truthful completion/delivery gates.
- Backend-agent execution training, Vault-backed Supabase authentication, and
  validation requirements for implementation work.
- Compact guardrail reporting and deterministic SQLite connection ownership.

## Material gaps still open

1. The Knowledge, Lesson, Pattern, Risk, Architecture, Operator Preference, and
   Governance registries named by the original constitution remain absent as
   first-class domain stores.
2. Mission dependency graphs, portfolio resource allocation, mission-level
   checkpoints, and mission resume/recovery are not yet complete.
3. Decision alternatives, trade-offs, and confidence are not uniformly recorded
   across every decision source.
4. Outcome evaluation and reviewed promotion of lessons/patterns into standards
   remain future learning-layer work.
5. Capability/ADR linkage is seeded and visible but is not yet a universal
   merge-blocking gate for every new route or autonomous capability.
6. True isolated CLI authentication profiles remain unresolved; host-profile
   OAuth logout can still affect another application using the same profile.
7. Full day-to-day readiness still depends on live service health, external
   credentials, CI runner capacity, and workspace-specific tests beyond this
   static constitution gate.

## Audit noise repairs in this rerun

- File-size guardrails now print five representative legacy advisories and a
  count. Set `AXON_GUARDRAIL_VERBOSE=1` to print every advisory.
- The Cursor usage probe now closes its read-only SQLite connection instead of
  relying on transaction-context semantics.
- Control-plane SQLite connections now close when used as context managers,
  with a regression test proving commit-and-close behavior.
- The Watch service uses FastAPI lifespan startup instead of deprecated
  `on_event("startup")` registration.
- Runtime stream pipes and persistent in-memory sidecar stores now release
  handles deterministically during normal completion and module teardown.

These changes remove repeated non-actionable output while retaining real
failures, new file-size growth, and actionable warnings.

## Recommended next constitution slice

Build mission-level checkpoints and recovery on the existing Mission Registry,
then require scheduler, Lead, and VAXON transitions to reference the mission,
decision, and evidence records used to resume. This closes a more operationally
important gap than adding another dashboard or autonomous action type.
