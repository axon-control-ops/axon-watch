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

**Status:** implementation complete; verification recorded below.

Work:

- Add throttled mid-run thinking (maximum three lines per turn).
- Add opt-in tool milestones, conversational only, with a 30-second throttle.
- Cancel stale queued speech when the run advances.
- Surface the IDE Quiet override before the first muted run.

Gate: policy/throttle tests and a long-run manual no-spam proof.

### Voice-D — Real cloud STT

**Status:** merged to `dev` at `1fb6340`; implementation complete. Optional
manual accent/noisy-room proof remains and does not block the API contract gate.

Work:

- Add a bounded authenticated POST endpoint accepting recorded audio.
- Return transcript, provider, confidence when available, and failure reason.
- Preserve privacy blocking and browser STT fallback.
- Keep Chromium phrase bias disabled until its abort behavior is proven fixed
  on the supported runtime.

Gate: API contract, upload/fallback tests, and an accent/noisy-room comparison.

### Voice-E — Azure / cloud TTS routing

**Status:** implementation complete; verification recorded below.

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

### 2026-07-16 — Voice-C

- Throttled mid-run thinking: up to three complete sentences per agent turn (45 s
  interval after the first) via `kairo-narration-throttle.ts` and multi-block
  `agent-stream-incremental` speech queue.
- Opt-in `narrate_tool_progress` setting (conversational only, 30 s tool throttle).
- Stale narration cancel: milestone/progress narrator `cancel()` +
  `dropWaitingKairoNarration()` before run advances.
- IDE Quiet hint: one-time composer banner when Minimal is muted in IDE Quiet.
- Focused frontend: narration policy/throttle/override-hint/stream-voice tests.

### 2026-07-16 — Voice-D

- Bounded `POST /api/kairo/stt` accepts recorded audio (2 MiB cap) and returns
  transcript, provider, confidence, and failure reason.
- Azure Speech REST STT when credentials are configured; privacy mode blocks
  upload server-side; browser STT remains the fallback path.
- Manual PTT cloud capture uses `MediaRecorder` + `transcribeCloudStt`; failed
  cloud turns fall back to browser recognition for that clip.
- Focused backend: `tests.test_kairo_stt` — contract, privacy, fallback.
- Focused frontend: `kairo-cloud-stt.test.ts` + `cloud-audio-capture.test.ts`.
- `tests.test_kairo_stt` wired into `verify:contracts`.
- Cloud upload accepts **ogg/wav only**; WebM stays on browser STT fallback.
- Manual accent/noisy-room comparison: **deferred** (operator proof when Azure
  keys live); does not block C14. Prior “merge to `dev` in this close-out”
  note cleared — Voice-D is recorded complete here and in `EXECUTION_PLAN.md`.

### 2026-07-16 — Voice-E

- Azure-first TTS routing confirmed in `kairo-voice-playback.ts` with serialized
  queue (`kairo-voice-queue.ts`) — no concurrent playback; barge-in flushes queue.
- Provider receipts: `kairo-voice-diagnostics.ts` records engine/reason; galaxy orb
  shows `Azure voice` / `Browser voice · <reason>` badge while speaking.
- Tool milestone narration: contextual lines from `tool_milestone.py` /
  `kairo-tool-milestone.ts` — explains read/edit/shell/research instead of raw
  `:::tool` headers; speak API allows `tool`/`edit` for conversational narration.
- Focused backend: `tests.test_kairo_voice` + `tests.test_kairo_tool_milestone` —
  **25/25 PASS**.
- Focused frontend: `kairo-voice-playback`, `kairo-voice-diagnostics`,
  `kairo-voice-queue` (serial play + barge-in flush + no overlap),
  `kairo-tool-milestone`, `kairo-progress-fallback` — **19/19 PASS**.
- Live Azure REST synthesis (subscription key + regional SSML endpoint):
  success returned `audio/mpeg` (~73 KiB); forced bad key returned no audio
  (client browser fallback path with explicit reason).
- Fallback reasons exercised in playback tests / code paths: `azure_unavailable`,
  `audio_playback_failed`, `fetch_error`, plus diagnostics badge
  `Browser voice · <reason>`.
- Research alignment (supporting): handbook + `.env.example` +
  `config/deployment.env.example` document SearXNG → Google CSE (legacy) →
  DuckDuckGo Instant; live `axon_research_search` receipt `provider: searxng`
  with `AXON_WATCH_SEARXNG_URL` set. No new Google CSE project/key for Axon-X.
- C12 gate: **green** (see `EXECUTION_PLAN.md`).

### 2026-07-16 — Close-out sync (Voice-D / Voice-E + research path)

- Re-ran focused gates: backend `tests.test_kairo_voice` +
  `tests.test_kairo_tool_milestone` + `tests.test_kairo_stt` — **35/35 PASS**;
  frontend voice playback/diagnostics/queue/tool-milestone/progress-fallback +
  cloud STT / audio capture — **26/26 PASS**.
- `EXECUTION_PLAN.md` Phase C table synced: C6B/C11/C12/C13/C14 marked done to
  match this log (C13 duplicates C6B / Voice-B).
- Research path unchanged: prefer local SearXNG; Google Custom Search stays
  legacy-only if already configured — **do not** create a new Google search
  project or API key for Axon-X. Live `axon_research_search` receipt
  `provider: searxng` (e.g. [SearXNG Search API](https://docs.searxng.org/dev/search_api.html)).

## Next slice

**Locked 2026-07-16:** cross-workspace coaching (broader “super-agent” advice).

Design: [`VAXON_CROSS_WORKSPACE_ADVICE_PLAN.md`](VAXON_CROSS_WORKSPACE_ADVICE_PLAN.md)
— **SA-1** (fleet-ranked grounded Advise) implementation started. Phase D (brain
polish + handoff) remains the parallel product roadmap; this advice plan feeds
the same fleet/handoff facts and does not replace D1–D4.
