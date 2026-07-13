# KAIRO Voice, Context, Continuation & Memory Plan

**Effective:** 2026-07-09  
**Parent:** [`EXECUTION_PLAN.md`](EXECUTION_PLAN.md) — runs after Phase B debt gate, alongside Phase C  
**Inputs:** Vaxon narration audit (2026-07-09), [`KAIRO_CONVERSATION_PLAN.md`](KAIRO_CONVERSATION_PLAN.md) OP-C5

This plan turns the narration audit and the Axon-X context/continuation/memory gaps
into **locked slices** with gates. Follow slice order; do not skip ahead.

---

## Why this plan exists

Two separate problems block a believable JARVIS loop:

1. **Voice narration** — Vaxon speaks bookends and at most one thinking sentence
   during agent work. Settings promise more than the code delivers; errors go
   silent; dead API calls waste latency.
2. **Context / continuation / memory** — KAIRO conversation memory lives in
   process RAM, resets on control-plane restart, and does not flow into IDE
   agent turns. The operator asks "continue what we discussed" and the agent
   starts cold.

Phase C (OP-C1–C5) covers the **converse API** loop. This plan covers **agent
narration hardening** and **cross-channel memory** so voice, conversation, and
IDE agents share one operator story.

---

## Lock rules

1. **Debt gate first.** No voice/memory slice until Phase B clears verification debt.
2. **Truth unchanged.** Persona polish never invents status; memory is
   non-authoritative hints only.
3. **Bounded modules.** Narration policy stays in `kairo-narration-policy.ts`;
   memory stays in `kairo_conversation.py` + a small persistence module — no
   `shell.ts` monolith growth.
4. **One slice per pass.** Gate must pass before the next slice starts.
5. **Append-only log** at the bottom of this file for discoveries.

---

## Part 1 — Voice narration gaps (audit → slices)

Source: narration stack review 2026-07-09 (`kairo-narration-policy.ts`,
`kairo-agent-narration.ts`, `shell.ts`, `kairo_voice.py`).

| Audit # | Gap | Slice |
|---------|-----|-------|
| 1 | "Conversational" name oversells agent-run behavior (bookends only) | **V1** |
| 2 | Only first complete thinking sentence spoken per turn | **V2** |
| 3 | Status strip shows tools; voice never narrates them | **V3** |
| 4 | Minimal thinking uses raw TTS; conversational uses speak API | **V4** |
| 5 | Duplicate policy branches; speak API called for filtered milestones | **V5** |
| 6 | Speak API failure drops line; agent errors never spoken | **V6** |
| 7 | Model paraphrase lags behind fast agent streaming | **V7** |
| 8 | IDE voice gating surprises operators | **V8** |
| 9 | Settings hints out of date (minimal thinking not mentioned) | **V9** |
| 10 | Narration ≠ conversation (separate product slice) | Phase C (OP-C) |
| 11 | Browser TTS quality | **Deferred V11** (cloud TTS, post Phase F) |

### V1 — Honest narration modes (settings + policy)

**Work:**

- Document actual behavior in `OperatorPresenceSettingsForm.vue`:
  - **Minimal:** start, done, alerts, one live thinking sentence (browser TTS).
  - **Conversational:** same events + speak-API persona polish on bookends and
    thinking; still no per-tool chatter unless V3 ships.
- Either rename misleading hint ("JARVIS-style paraphrase for dialogue") or
  scope it to bookends + thinking only.

**Gate:** vitest `kairo-narration-policy.test.ts` PASS; manual: operator reads
settings and behavior match.

### V2 — Throttled mid-run thinking (optional depth)

**Work:**

- After first spoken thinking block, allow one additional sentence every N seconds
  (default 45 s) while agent still streaming — cap at 3 per turn.
- Keep `spokenLiveThinkingBlock` dedupe per block; add time-based gate in
  `kairo-agent-narration.ts`.

**Gate:** vitest `kairo-agent-narration.test.ts` covers throttle; manual: long
agent run gets ≥2 spoken thinking lines without spam.

### V3 — Tool milestone narration (conversational only, opt-in)

**Work:**

- Add `narrate_tool_progress` setting (default off) under operator presence.
- When on + conversational: speak tool milestones at most once per 30 s using
  existing `kairo_voice.py` tool fallback pool.
- Wire `shouldNarrateAgentEvent` to allow `tool:` when setting enabled.

**Gate:** pytest `test_kairo_voice.py` tool path; vitest gate test; manual: strip
and voice both update on Read tool when setting on.

### V4 — Persona parity for minimal thinking

**Work:**

- Route minimal live thinking through `/api/kairo/speak` with `use_model: false`
  (template/fallback only) so tone matches bookends without full model latency.
- Remove raw `speechSynthesis` path for thinking blocks.

**Gate:** vitest `kairo-voice-playback` / narration tests; manual: minimal mode
thinking sounds like Vaxon, not raw browser voice.

### V5 — Plumbing cleanup

**Work:**

- Collapse duplicate branches in `shouldNarrateAgentEvent`.
- In `shell.ts`, call `shouldNarrateAgentEvent` **before** `postKairoSpeak` so
  filtered tool/edit/thinking milestones never hit the network.
- Delete or comment unreachable backend fallback pools only if V3 stays off by
  default (keep pools if V3 wires them).

**Gate:** vitest narration policy tests; network tab shows no speak calls for
filtered milestones during agent run.

### V6 — Failure and error narration

**Work:**

- On speak API failure during milestones: fall back to template line from
  `kairo_voice.py` `_fallback_for_event` (client-side mirror or `use_model: false`
  retry).
- On agent stream `onError`: speak one short alert line (`alert` event) with
  error summary capped at 120 chars.

**Gate:** vitest + pytest failure-path tests; manual: kill speak API → Vaxon still
speaks fallback; force agent error → spoken alert.

### V7 — Stale speak cancellation

**Work:**

- Track in-flight speak request per agent run; cancel or drop result when agent
  phase advances past the milestone that triggered it (new tool before start
  line finishes).
- Expose `abortKairoSpeak` hook in `kairo-playback-control.ts`.

**Gate:** vitest `kairo-playback-control.test.ts`; manual: fast agent run does not
queue overlapping start + thinking paraphrases.

### V8 — IDE voice discoverability

**Work:**

- When IDE layout + narration minimal + voice strip off: show one-time toast or
  settings link — "Voice silent in IDE unless conversational or voice strip on."
- Reuse existing `narrationOverridden` note; ensure it surfaces on first agent
  run in IDE, not only in settings.

**Gate:** manual smoke in IDE layout; operator finds override without digging.

### V9 — Settings copy sync

**Work:** Update minimal/conversational hint strings to match V1 behavior.

**Gate:** visual review of settings form.

### V11 — Cloud TTS (deferred)

Deferred until Phase F exit. Track in `PARITY_LEDGER.md` only; no implementation
in this plan.

---

## Part 2 — Context, continuation & memory gaps

### Problem summary

| Gap | Symptom | Root cause |
|-----|---------|------------|
| **Context** | Agent answers about open file when operator asked about fleet | Voice filters `active_file`; Lane B still injects file preview into agent context |
| **Context** | KAIRO converse answers lack chat thread history | `build_conversation_context_pack` pulls DTOs only, not persisted chat |
| **Continuation** | "Continue the plan we discussed" starts cold agent | IDE agent dispatch does not receive prior KAIRO/conversation turns |
| **Continuation** | Voice ask → IDE handoff loses thread | Handoff card passes task string only, not session memory |
| **Memory** | Follow-up "hand it off" fails after CP restart | `_TURN_MEMORY` / `_ENTITY_MEMORY` are in-process dicts |
| **Memory** | Vaxon repeats phrasing across channels | Recent spoken lines scoped per speak call, not unified session log |
| **Memory** | Stale answers after fleet change | OP-C5 refresh policy (>10 s) not enforced in code |

### M1 — Unified session identity

**Work:**

- Bind `kairoSpeechSessionId()` to active workspace + chat `thread_id` (not a
  standalone `kairo-${Date.now()}` bucket).
- Pass same `session_id` to `/api/kairo/converse`, `/api/kairo/speak`, and
  voice-log reads.

**Gate:** contract test: converse then speak share session key; manual: voice-log
shows both event types under one session.

### M2 — Persist conversation memory

**Work:**

- Extend `voice_transcript_store` or add `kairo_session_memory` SQLite table:
  last N turns + entity map per `session_id`.
- Hydrate `_TURN_MEMORY` / `_ENTITY_MEMORY` from DB on converse/speak startup;
  write-through on each turn.
- Cap: 8 turns, 16 KB total per session (match existing `_MAX_TURN_MEMORY`).

**Gate:** pytest memory survives simulated restart (clear dict, reload from DB);
`test_kairo_conversation.py` follow-up tests still PASS.

### M3 — Converse context pack + chat tail

**Work:**

- Add last 3 persisted chat messages (operator + assistant) for active workspace
  thread into `build_conversation_context_pack`.
- Mark as non-authoritative "recent dialogue" section in pack.

**Gate:** pytest: pack includes chat tail when thread has messages; converse
answer references prior thread topic in template path.

### M4 — Agent continuation from KAIRO

**Work:**

- When dispatching Lane B agent from conversation handoff or when operator prompt
  contains continuation cues ("continue", "as we discussed", "the plan"):
  inject `build_lane_b_context_block` appendix with last N KAIRO turns + entity
  context from M2.
- Limit injected memory to 800 chars.

**Gate:** pytest lane_b context block includes memory appendix; manual: ask KAIRO
a question → "continue that in the IDE" → agent acknowledges prior topic without
re-ask.

### M5 — Stale context refresh (OP-C5)

**Work:**

- Cache `build_conversation_context_pack` per workspace with 10 s TTL; force
  refresh on converse when cache age exceeded or `refresh=true` query flag.

**Gate:** pytest TTL behavior; manual: change approval state → answer updates
within 10 s without browser refresh.

### M6 — Unified recent spoken lines

**Work:**

- `kairo_voice_log` returns last 5 lines for session regardless of event type
  (agent, converse, briefing).
- Speak prompt builder always pulls from this unified log for dedup.

**Gate:** pytest voice-log session filter; manual: agent start does not repeat
phrasing from prior converse reply.

---

## Locked implementation order

Runs **after Phase B exit**, interleaved with Phase C:

```text
Phase C1–C2 (converse core) — can start in parallel with V1, V5, V9
  → V5, V6, V9 (plumbing + honesty + errors)
  → V1, V4 (settings truth + persona parity)
  → M1, M2 (session identity + persistence) — blocks M3–M6
  → C3–C5 (PTT, actions, memory gates) + M3, M5, M6 in parallel
  → M4 (agent continuation) — after C4 handoff hook + M2
  → V2, V3, V7, V8 (depth + tool narration + latency + IDE discoverability)
  → V11 deferred
```

**Parallel rule:** M1–M2 should land before C5 exit gate re-test. V2/V3 are
optional depth — do not block Phase D on them.

---

## Verification bundle

After each memory slice (M1–M6):

```bash
python3 -m unittest tests.test_kairo_conversation tests.test_kairo_voice tests.test_lane_b_context_tokens -v
cd apps/console-web && npm test -- --run src/lib/kairo-narration-policy.test.ts src/lib/kairo-agent-narration.test.ts src/features/kairo-conversation/
```

After voice slices V1–V9:

```bash
npm run verify:voice-cockpit
npm run verify:headed-browser-smoke
```

Manual smoke (5 min):

1. Operator mode: ask "any approvals?" → follow-up "hand it off" without re-stating.
2. IDE mode: agent run with conversational narration — start, thinking, done, error path.
3. Restart control-plane → repeat follow-up — memory still resolves.
4. Handoff to IDE → agent continues KAIRO topic.

---

## Append log

### 2026-07-13 — C9 / C10 / M3-M6 landed

- `build_conversation_context_pack()` now carries the latest operator-thread chat
  tail and honors `refresh=true` to bypass the 10-second pack cache when needed.
- Template follow-ups can reuse that recent thread context, so short callbacks can
  reference the prior workspace topic without restating it.
- IDE agent dispatch now receives a compact KAIRO memory appendix on continuation
  and signal-handoff prompts, capped for prompt safety.
- `/api/kairo/speak` writes every spoken line into the shared voice log, and
  dedup now reads the last session-scoped spoken lines across converse, briefing,
  and agent events.
- Gates: `tests.test_kairo_conversation`, `tests.test_kairo_voice`,
  `tests.test_control_plane_chat`, `tests.test_kairo_turn_memory`,
  `tests.test_voice_transcript_store`, `tests.test_lane_b_context_tokens`,
  and console-web conversation/session vitest checks.

### 2026-07-13 — C8 / M1+M2 landed

- `buildKairoSpeechSessionId()` binds voice/conversation to active workspace +
  chat thread (`kairo:workspace:thread`); shell store owns `kairoSpeechSessionId()`.
- Converse, speak, agent milestone, and progress narrators pass the same session id.
- SQLite `kairo_session_memory` persists turn + entity memory with write-through
  hydration; follow-up handoff survives simulated control-plane restart.
- Gates: `test_followup_memory_survives_simulated_restart`,
  `test_persisted_turns_reload_after_cache_clear`, M1 session-key contract tests,
  `kairo-speech-session.test.ts`.
- **Next:** C11 optional depth work (V2, V3, V7, V8); C12 remains deferred.

### 2026-07-13 — C7 / V1+V4+V6 landed

- Settings copy already documents honest Minimal vs Conversational behavior (V1).
- Agent bookends route through `/api/kairo/speak` in both modes; minimal uses
  template/fallback (`use_runtime: false`) for persona tone without model latency (V4).
- `agentMilestoneFallbackLine` mirrors backend fallbacks when speak times out or
  fails; agent `onError` now passes a capped error summary to the failed bookend (V6).
- **Next:** C8 (M1+M2) session identity + SQLite-backed memory — **landed same day**.

### 2026-07-11 — C6 / V5+V9 landed

- Client policy: single bookend gate for minimal + conversational; live thinking
  remains on `shouldSpeakLiveThinkingBlock`.
- Shell already short-circuits filtered milestones before speak network calls.
- Backend tool/edit pools retained (commented) for future opt-in tool narration.
- Operator presence settings copy aligned with actual Minimal / Conversational
  behavior (no oversold “dialogue paraphrase” claim).
- **Next:** V1+V4+V6 (C7).

### 2026-07-09 — Plan published

- Consolidated 11-point Vaxon narration audit into slices V1–V9 (+ deferred V11).
- Added context/continuation/memory slices M1–M6 for cross-channel operator story.
- Wired into `EXECUTION_PLAN.md` as Phase C extensions C6–C12 and V1–V9 references.
