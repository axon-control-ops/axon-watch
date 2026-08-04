# VAXON Cross-Workspace Advice Plan

**Effective:** 2026-07-16  
**Parent:** [`EXECUTION_PLAN.md`](EXECUTION_PLAN.md) (runs beside Phase D; does not replace D1–D4)  
**Prior voice truth rules:** [`KAIRO_VOICE_UPGRADE_PLAN.md`](KAIRO_VOICE_UPGRADE_PLAN.md)  
**Inputs:** Locked product choice — aim for cross-workspace coaching (broader
“super-agent” advice); existing fleet health, briefing rhythm, and workspace
handoff records.

## Locked direction

VAXON Advise must grow from **single-workspace next-safe-action templates** into
**cross-workspace coaching**: one short recommendation that can name which
workspace needs attention next, why, and what to do there — without inventing
strategy when the system has no live fact.

This is the approved product north star for the deferred “super-agent control-plane
advice” note. Richer same-workspace ranking alone is not enough; free-form
strategy without evidence is also rejected.

## What exists today (facts, not wishes)

| Surface | Current behavior |
|---------|------------------|
| Briefing Advise | Fleet-ranked coach line when scope is fleet, or when a hotter workspace wins over a quiet focus; otherwise top `next_safe_action` / review-ready hint; empty when idle |
| Briefing scope | `workspace` when a workspace id is passed; otherwise `fleet`. Notice uses scoped runs/approvals/signals; Advise ranking may still read fleet facts for redirects |
| Fleet health rollup | Per-workspace counts exist (`build_operator_fleet_health`) but are **not** wired into Advise yet — SA-1 reads fleet runs, approvals, signals, and runtime degraded/watch state directly |
| Handoffs | Persisted source → target record + target summary; manual shell follow-through; **not** in Advise ranking yet (next handoff-aware slice) |
| Voice fallback | Briefing event already speaks live notice / advise / top signal title when those strings are present; dedicated spoken-parity tests for cross-workspace lines still open |
| Memory highlights | Keyword hints from notice/advise/signals; non-authoritative |

Remaining gap: open handoffs are still not Advise inputs, and the fleet-health rollup module is not the Advise source. Model paraphrase over the pack is also not built.

## Corrected policy (binds every slice)

Same truth contract as the voice upgrade plan:

1. Conversational coaching lines come from verified operational facts, or from a
   model paraphrase that is only allowed when those facts exist.
2. With no live fact across the fleet (and no grounded model line), Advise stays
   empty — no “systems nominal” filler.
3. Loading / error / monitoring UI copy must never be dressed up as VAXON advice.
4. Memory and history are hints that may refine wording; they never invent a
   priority that runs, signals, approvals, or handoffs do not support.
5. Prove-source and handoff cards remain the evidence trail. Advice may point at
   them; it must not replace them.

## Coaching product shape

One written Advise line (and optional spoken line) that can do all of:

- Prefer the highest-urgency open loop **across workspaces** when scope is fleet,
  or when the active workspace is quiet but another workspace is on fire.
- Name the workspace in plain words (“DashPro”, “axon-local”) when the
  recommendation is not for the current focus.
- Prefer interruptive work first. **Shipped order today:** pending approval →
  critical/high signal → review-ready that needs a human → degraded runtime.
  **Target order (handoff slice):** insert open handoff with incomplete
  follow-through above degraded runtime.
- Stay inside the Notice → Advise → Decide → Execute → Verify → Report rhythm.
  Advise remains one sentence; Decide/Execute still carry the choice and action.

Example grounded lines (illustrative only):

- “Approve the guarded run in DashPro before starting more axon-watch work.”
- “VAXON is attending the critical signal in axon-local; keep working here.”
- “Handoff to DashPro is recorded — open that workspace and finish the listed task.”

Non-examples (forbidden):

- “You should refactor the auth stack next week.” (no live fact)
- “Everything looks good across the fleet.” (idle filler)
- “I think DashPro can wait.” (opinion without ranking evidence)

## Fact pack for coaching

Server builds a small **fleet advice pack** before rendering Advise:

| Fact | Source (as of first build slice) |
|------|--------|
| Pending approvals | Fleet pending-approval records + active runs awaiting approval |
| Critical/high open signals | Fleet inbox projection (first matching critical/high open signal) |
| Review-ready runs | Fleet active runs (skips auto-complete junk summaries) |
| Degraded / watch connectivity | Runtime summary `degraded` + watch connected flag |
| Active scope / focus | Briefing `scope.mode` + focused workspace id |
| Open handoffs (source/target/task) | Planned — not wired yet |
| Per-workspace health tone + counts | Planned optional input — rollup exists but Advise does not call it yet |

Ranking keys (highest first):

1. Pending approval (any workspace) — shipped
2. Critical/high open signal — shipped (first matching open critical/high in the
   fleet inbox list; not a full multi-signal contest)
3. Review-ready run that is not auto-complete junk — shipped (first matching
   non-auto-complete review-ready run)
4. Open handoff with incomplete follow-through — **not shipped**
5. Degraded runtime / watch disconnected — shipped
6. Otherwise empty Advise

When scope is `workspace` and a higher-ranked fact exists **outside** that
workspace, Advise may still surface it as a **cross-workspace redirect** (the
coaching behavior). Notice can remain scoped; Advise is allowed to look up.

## Delivery slices

Follow order. Gate each slice before the next.

### SA-1 — Fleet-ranked grounded Advise

**Work:**

- Extend briefing Advise construction to consume the fleet advice pack.
- Add a deterministic coach line builder (workspace display name + action kind +
  short reason) used when the winning fact is outside the focused workspace, or
  when scope is already fleet.
- Keep idle silence: no fact → empty string.
- Contract/tests: multi-workspace fixtures where focused workspace is quiet and
  another has approval/signal/handoff.

**Gate:** backend unit tests for ranking + quiet-idle; briefing DTO still validates
against shared types; manual: fleet view Advise names the hot workspace.

### SA-2 — Handoff-aware coaching

**Work:**

- Include open handoff records in the pack and ranking.
- Advise may recommend opening the target workspace and completing the handoff
  task text (already persisted — do not invent a new task).
- Optional UI affordance: Advise line links/focuses target workspace the same way
  existing handoff summary does (no new alternate truth).

**Gate:** handoff unit/API tests + one briefing test where handoff outranks a
low-severity local signal; `verify:test2` still green.

### SA-3 — Spoken coaching parity

**Work:**

- Voice fallback speaks the new Advise line when present (same quiet rules).
- Diagnostics badge / receipts unchanged; no double-speak with Notice.
- Prefer Azure-first TTS path already shipped; browser fallback remains.

**Gate:** voice fallback tests for cross-workspace advise text; manual barge-in
still flushes queue.

### SA-4 — Optional short model paraphrase (only over facts)

**Work:**

- Allow one short model paraphrase of the fleet advice pack **only when** SA-1/SA-2
  already produced a non-empty grounded Advise.
- If the model fails or returns empty, keep the deterministic coach line.
- Never call the model for idle fleet silence.

**Gate:** unit tests for “facts present → paraphrase allowed”, “no facts → no
model call”; privacy/settings respect existing voice policy.

## Out of scope (strict)

- Automatic agent migration or auto-switching workspaces without an explicit
  human action (handoff remains record + summary + optional focus).
- Replacing prove-source / Attention cards with chatty strategy essays.
- New Google search / research product work (research path stays SearXNG-first).
- Wake word, WhatsApp monitor, or mobile shell work.
- Commit, push, merge, or release steps unless separately requested.

## Relationship to Phase D

Phase D (brain polish + handoff UI) remains the default product roadmap for
prove-source and Continue-in-IDE. This plan **feeds** those surfaces:

- SA-1/SA-2 make Advise point at the same fleet and handoff facts D1/D2 expose.
- Do not block D1–D4 on SA-4.
- If D2 handoff card and SA-2 coach line disagree, the handoff record and signal
  DTOs win; fix the coach builder.

## Verification checklist (plan-level)

- [x] Multi-workspace quiet-focus / hot-other case produces redirect Advise (unit + briefing API tests)
- [x] Idle fleet produces empty Advise (no filler) (unit tests)
- [ ] Manual console check: fleet / quiet-focus Advise names the hot workspace in the live UI
- [ ] Handoff task text is quoted or summarized from the record, not invented
- [ ] Spoken path matches written Advise or stays quiet (dedicated cross-workspace coverage; briefing voice already reads advise when present)
- [ ] Model paraphrase never runs without a grounded base line

## Append-only log

### 2026-07-16 — Second critical review

- Ranking list still mixed target handoff priority with shipped order; labeled
  shipped vs not-shipped, and noted signal/review-ready selection is “first
  match,” not a full contest.
- Prior review said “17 related tests”; re-count is **14** in
  `test_operator_fleet_advice` + `test_control_plane_operator_briefing` (all OK).
- Coach templates still say “guarded run” for approvals — wording convenience,
  not a separate guardedness check beyond approval/awaiting-approval state.

### 2026-07-16 — Critical review corrections

- Corrected “what exists today” and fact-pack sources: first build uses fleet
  runs / approvals / signals / degraded state, not `build_operator_fleet_health`.
- Split verification: unit/API redirect + idle silence proven; live UI manual
  check and handoff/spoken/model slices still open.
- Clarified voice: briefing fallback already speaks advise text when present;
  dedicated spoken-parity gate remains separate.

### 2026-07-16 — SA-1 implementation started

- Added `operator_fleet_advice.py`: fleet advice pack, urgency ranking, coach lines.
- Briefing Advise now consumes the pack (fleet scope names the hot workspace;
  quiet focused workspace can redirect to a hotter workspace).
- Idle silence preserved; handoffs deferred to the next slice.
- Tests: `tests/test_operator_fleet_advice.py` + quiet-focus briefing case.

### 2026-07-16 — Direction locked

- Product choice: cross-workspace coaching (broader “super-agent” advice).
- Design published; implementation not started in that close-out (later same day:
  first build slice started — see above).
- First build slice when authorized: fleet-ranked grounded Advise.
