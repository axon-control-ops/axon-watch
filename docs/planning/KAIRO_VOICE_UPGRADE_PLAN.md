# KAIRO / VAXON Voice Upgrade Plan

**Effective:** 2026-07-16  
**Parent:** [`EXECUTION_PLAN.md`](EXECUTION_PLAN.md), Phase C  
**Prior voice/memory slices:** [`KAIRO_VOICE_IMPROVEMENT_PLAN.md`](KAIRO_VOICE_IMPROVEMENT_PLAN.md)

## Corrected policy

Earlier summaries used “hardcoded responses” too broadly. Axon-X needs
deterministic operational labels for approvals, failures, and degraded runtime;
those are grounded status templates, not simulated model responses.

The defect is generic conversational filler (for example, “Systems nominal” or
“Describe the next action”) being displayed or spoken without a live fact, or
beside a contradictory live signal.

Rules:

1. Conversational replies come from the live agent/model response.
2. Operational fallbacks may state verified run, signal, approval, or failure
   facts.
3. With no live fact and no model response, VAXON stays quiet.
4. Loading/error/monitoring labels remain deterministic UI copy and must not be
   presented as generated VAXON answers.
5. Each completed voice slice gets a focused green commit and is pushed before
   the next slice starts.

## Why some Agent Dock modes do not narrate

Two independent gates cause silence:

1. `shell.ts` creates progress and milestone narrators only when
   `isToolCapableComposerMode(mode)` is true. That helper allows **Agent** and
   **Debug** only, so **Ask** and **Plan** never attach a narrator.
2. Agent/Debug can still be silent when narration is Off, privacy or delivery
   policy blocks audio, IDE Quiet turns Minimal into effective Off, no complete
   speakable thinking sentence arrives, or the event is a tool/edit milestone
   intentionally excluded by policy.

Ask/Plan must remain non-tool-capable. Their fix is an answer-only narrator, not
granting them linked-run or tool semantics.

## Execution order

### Voice-A — Truthful briefing and response fallbacks

**Status:** implementation complete; verification recorded below.

Work:

- A fully idle briefing emits no canned notice, advise, decide, execute, verify,
  or report sentence.
- Frontend projection suppresses legacy/stale idle filler when live signal/run
  state exists.
- Briefing speech uses a live notice, safe action, or signal title; otherwise
  it emits no line.
- A missing conversation reply emits no synthetic “standing by” response.

Gate:

- backend rhythm + voice fallback tests
- frontend briefing tests
- console typecheck
- planning manifest validation
- repo-wide contracts (may only be marked green when unrelated guardrails are
  also green)

### Voice-B — Ask / Plan answer narration

**Status:** implementation complete; verification recorded below.

Work:

- Attach an answer-only narrator to Ask and Plan streams.
- Speak at most one sanitized final-answer excerpt.
- Reuse narration level, privacy, delivery, dedupe, and barge-in gates.
- Do not create linked runs or tool/edit narration for Ask/Plan.

Gate: focused mode tests plus one manual Ask and Plan turn, each spoken once.

### Voice-C — Narration depth without chatter

Work:

- Add throttled mid-run thinking (maximum three lines per turn).
- Add opt-in tool milestones, conversational only, with a 30-second throttle.
- Cancel stale queued speech when the run advances.
- Surface the IDE Quiet override before the first muted run.

Gate: policy/throttle tests and a long-run manual no-spam proof.

### Voice-D — Real cloud STT

Current fact: `kairo-cloud-stt.ts` ignores `_audioBlob`, sends a GET probe to
`/api/kairo/stt`, and returns `cloud_stt_not_configured`. This is a placeholder,
not transcription.

Work:

- Add a bounded authenticated POST endpoint accepting recorded audio.
- Return transcript, provider, confidence when available, and failure reason.
- Preserve privacy blocking and browser STT fallback.
- Keep Chromium phrase bias disabled until its abort behavior is proven fixed
  on the supported runtime.

Gate: API contract, upload/fallback tests, and an accent/noisy-room comparison.

### Voice-E — Azure / cloud TTS routing

Work:

- Prefer configured Azure TTS for narration and conversation.
- Keep one explicit browser fallback path, never concurrent playback.
- Record provider/reason receipts so fallback is visible.

Gate: provider routing tests and manual Azure success, forced failure,
barge-in, and no-double-speak proofs.

## Verification log

### 2026-07-16 — Voice-A

- Focused backend: `tests.test_operator_briefing_rhythm` +
  `tests.test_kairo_voice` — **30/30 PASS**.
- Focused frontend: `briefing-panel-view.test.ts` +
  `kairo-narration-policy.test.ts` — **12/12 PASS**.
- Console `vue-tsc --noEmit` — **PASS** after two minimal repairs in existing,
  unrelated Plan/composer WIP; those repairs are not part of Voice-A.
- Python compile — **PASS**.
- Planning manifest — **PASS**.
- `verify:contracts` — later cleared on the same dirty tree after size
  extractions + email/inbox fixes (see post-Voice-B note below).
- Direct full contract runner continued through the suite and reported two
  unrelated failures: the same file-size baseline test, plus the current dirty
  email/vault import path causing `WatchInboxUnavailableError` in skeleton E2E.
  All focused Voice-A tests remained green.
- Landed: commit `1c19f77` on `fix/clear-attention-blockers` (pushed).

### 2026-07-16 — Voice-B

- Added Ask/Plan answer-only narration via `composer-answer-narration.ts` and
  `chat-stream-voice-narration.ts`.
- Ask/Plan remain non-tool-capable; only final answer/failure bookends speak.
- Extracted stream voice wiring from `shell.ts` (3734 → 3687) and lowered the
  hotspot ratchet.
- Focused frontend: answer-mode + stream-voice + narration-policy — **12/12 PASS**.
- Console `vue-tsc --noEmit` — **PASS**.

### 2026-07-16 — Contracts unblock (post Voice-B)

- Cleared hard/ratchet file-size FAILs (toolbar/CSS/ide-layout/lane_b/composer
  extractions; budgets lowered).
- Eager-import `fetch_native_email_messages` in `email_signal.py` to avoid
  control-plane/`app.vault` package collision; briefing uses
  `allow_empty_unavailable` so inbox blips degrade instead of 500.
- `npm run verify:contracts` — **PASS**.

## Next slice

Voice-C: throttled mid-run thinking + opt-in tool milestones.
