# KAIRO Conversation Plan (OP-C) — JARVIS Dialogue Loop

**Status:** Active skeleton (2026-07-08; updated 2026-07-08 PM)
**Parent:** [`OPERATOR_BRAIN_PIVOT.md`](OPERATOR_BRAIN_PIVOT.md) — Wave 5
**Inputs:** JARVIS Prompt Pack (operator PDF) conversational loop, [`KAIRO_MODE.md`](KAIRO_MODE.md) JX-4/JX-5, AI Workshop OS reference ("say Jarvis…", ask → answer → act)

---

## Purpose

Close the gap between *KAIRO speaks at you* (today: event narration, spoken briefing)
and *you converse with KAIRO* (target: ask, answer, follow-up, act) — the JARVIS
loop from the PDF stack:

```text
listen → transcribe → understand → ground in DTOs → answer (voice + text)
       → optionally act (dispatch / navigate / hand off) → remember turn
```

The brain galaxy is the stage; the conversation is the interface. The omnibar at
the bottom of the galaxy and the KAIRO orb become the two ends of one dialogue
channel (typed and spoken).

---

## What exists today (verified in code)

| Capability | Where | State |
|---|---|---|
| TTS output queue, JARVIS voice prefs | `console-web/src/lib/speech-queue.ts` | Working |
| Event-driven spoken lines (start/done/alert/greeting/briefing) | `control-plane/app/kairo_voice.py` + `kairo_voice_prompt.py` | Working; model-backed w/ fallback pools |
| Persona guardrails (tone ≠ truth) | `kairo_persona.py`, `spoken_alert_policy.py` | Working |
| Conversational replies (Lane B, Cursor agent subprocess) | `chat/service.py` `should_use_lane_b` | Working but slow (CLI cold start 20 s+) |
| Command intent classification; questions → not commands | `chat/command_intent.py` `is_question()` | Working |
| Speak-briefing on demand | `shell.speakOperatorBriefing()` + orb tap | Working |
| **Speech input (STT)** | `console-web/src/features/kairo-conversation/` | Working skeleton (hold orb / Space push-to-talk; no wake word) |
| **Fast grounded Q&A** ("what's on fire?", "any approvals?") | `/api/kairo/converse` + `kairo_conversation_reply.py` | Working skeleton (fast DTO path; runtime reserved for deep turns) |
| **Conversation surface in galaxy** (omnibar input) | `KairoConversationBar.vue` | Working skeleton |
| **Voice-initiated actions** ("run health check", "show me DashPro") | local nav intents + command routing | Partial — navigation, command dispatch, and handoff follow-ups exist |
| **Turn memory** | `kairo_conversation.py` (`_TURN_MEMORY`, `_ENTITY_MEMORY`) | Partial — session-scoped turn + entity memory exists |

---

## Design principles (inherited, non-negotiable)

1. **Persona is not truth.** Every answer is grounded in canonical DTOs
   (briefing, fleet health, brain graph, runs, signals). KAIRO never invents
   status.
2. **Approval boundary preserved.** Conversation can *propose* execute-tier
   actions; it cannot bypass approvals. One-shot reads stay auto-complete.
3. **Honest listening.** v1 is push-to-talk (hold orb / hotkey). No fake
   wake-word claims; ambient wake word is a later, explicitly-scoped slice.
4. **Bounded modules.** New code lives in
   `console-web/src/features/kairo-conversation/` and
   `control-plane/app/kairo_conversation.py` — not in `shell.ts` or
   `chat/service.py` monolith growth.
5. **Degradation ladder.** No mic → typed omnibar. No model → template answers
   from DTO context. No TTS → text-only reply. Never a dead surface.

---

## Architecture

```text
┌─ console-web ───────────────────────────────────────────────┐
│ features/kairo-conversation/                                 │
│   use-kairo-conversation.ts   ← turn state machine           │
│   speech-capture.ts           ← PTT + Web Speech API STT     │
│   conversation-intents.ts     ← local nav intents (client)   │
│   KairoConversationBar.vue    ← galaxy omnibar (text + mic)  │
│                                                              │
│ orb: LISTENING / THINKING / SPEAKING states (exists)         │
└──────────────┬───────────────────────────────────────────────┘
               │ POST /api/kairo/converse
┌──────────────▼───────────────────────────────────────────────┐
│ control-plane                                                 │
│ app/kairo_conversation.py                                     │
│   build_context_pack()  ← briefing + fleet + graph + runs     │
│   route_turn()          ← question | command | action | chat  │
│   answer_grounded()     ← consultative CLI, 280-char budget,  │
│                           template fallback (same pattern as  │
│                           kairo_voice.py)                     │
│   session turn memory (per session_id, capped)                │
└──────────────┬───────────────────────────────────────────────┘
               │ commands → existing post_chat_message pipeline
               │ (classification, runs, approvals unchanged)
               ▼
        runs / approvals / receipts (existing truth)
```

**Turn routing (server):**

| Turn kind | Detector | Handling |
|---|---|---|
| Operator command (`git status`, `run …`) | existing `classify_command` | Dispatch through existing pipeline; KAIRO ack line; auto-complete rules apply |
| Status question ("what's on fire?", "any approvals?") | `is_question()` + status keyword map | Answer from context pack directly — **no CLI call** — < 300 ms |
| Open question ("why did the Sentry run fail?") | `is_question()` fallback | Consultative CLI with context pack; 30 s budget; fallback = best-effort DTO summary |
| Navigation ("show me DashPro", "open attention") | client-side intent match | Handled in browser: `focusNode`, `setCurrentWorkspace`, `focusAttentionSidebar` — no server round-trip |
| Action proposal ("deploy DashPro") | execute-tier intent | KAIRO answers with the approval path; never dispatches directly |

---

## Slices

### OP-C1 — Conversation contract + `/api/kairo/converse`

- `kairo_conversation.py`: context pack (briefing, fleet health DTO, brain graph
  summary, active runs, pending approvals), turn router, grounded answerer with
  template fallback, capped session memory.
- Status-question fast path answers **without** the CLI (dialogue must feel
  instant for "what's my status?" class).
- Contract tests: question vs command routing, fallback answers, memory cap,
  approval-tier refusal.

**Done when:** `curl /api/kairo/converse` answers "any approvals?" from DTOs in
under 1 s with no model dependency.

### OP-C2 — Galaxy conversation bar (typed first)

- `KairoConversationBar.vue` replaces the display-only omnibar in the galaxy
  stage: text input + send + mic button (mic disabled until OP-C3).
- Turn flow: input → converse API → reply rendered as KAIRO line under the bar
  **and** spoken via `speech-queue` (respecting narration/privacy settings).
- Commands typed here go through the existing command pipeline (same as right
  dock) — one input, two lanes, no duplicated composer logic.
- Orb reflects state: LISTENING (input focused) → THINKING (in flight) →
  SPEAKING (TTS active).

**Done when:** typing "what needs my attention?" in the galaxy returns a spoken
+ written grounded answer; typing "git status" dispatches a run as today.

### OP-C3 — Push-to-talk STT *(absorbs OP-V1e)*

- `speech-capture.ts`: hold-to-talk on the orb + `Space` hold hotkey (galaxy
  focused); Web Speech API `SpeechRecognition`; Chrome-first, feature-detected.
- Transcript lands in the conversation bar for visible confirmation before
  auto-submit (600 ms grace to correct) — no silent mis-fires.
- Degradation: no `SpeechRecognition` → mic button hidden, typed path intact.
- Privacy: `privacy_mode` or `hands_free_enabled=false` blocks capture, orb
  shows MUTED.

**Done when:** hold orb → speak "any approvals?" → release → KAIRO answers
aloud; privacy mode blocks the mic entirely.

### OP-C4 — Conversation actions

- `conversation-intents.ts`: navigation intents resolved client-side
  ("show/focus \<workspace>", "open attention", "grid view", "brain view").
- Dispatch confirmations for execute-tier proposals: KAIRO answers with what it
  *would* run and the approval path; a follow-up "yes" (within the session turn
  memory window) submits through the normal pipeline.
- Handoff hook: "hand this to the IDE" on a discussed signal triggers the
  OP-B5/OP-V1f handoff card flow.

**Done when:** "show me DashPro" focuses the galaxy node + switches workspace;
"run the health check" → confirm → run dispatched with receipt.

### OP-C5 — Turn memory + follow-ups

- Server session memory: last N turns (question + answer + referenced entity
  ids) so "why?" / "and the other one?" resolve against prior context.
- Context pack refresh policy: re-pull DTOs when stale (> 10 s) so answers never
  describe a dead world.
- Memory is per-session, capped, non-authoritative, never persisted as truth.

**Done when:** "what's wrong with DashPro?" → answer → "hand it off" works
without re-stating the workspace.

### OP-C6 — Wake word (deferred, explicit)

- "KAIRO…" ambient wake word. Only after OP-C3 proves the loop; requires an
  in-browser keyword spotter (or native shell) and an explicit
  always-listening setting. Do not fake it before then.

---

## Verification per slice

- `pytest` contract tests for `kairo_conversation.py` (routing, grounding,
  fallbacks, memory cap)
- vitest for conversation bar state machine, intents, speech-capture
  degradation
- Manual smoke in the galaxy at `:4173` — typed turn, spoken turn, command
  turn, navigation turn
- Fitness additions (per [`KAIRO_MODE.md`](KAIRO_MODE.md)): status-question
  answer latency < 1 s; privacy-mode gating correctness; dispatched-action
  receipt completeness

---

## Revised next-steps order (supersedes previous list)

```text
1. OP-C1  converse API + grounded answers        ← conversation core (server)
2. OP-C2  galaxy conversation bar (typed)        ← conversation core (UI)
3. OP-V1f / OP-B5  incident → "Hand off to IDE"  ← needs OP-C4 hook later
4. OP-B4 / OP-V1h  real Sentry/PostHog signals   ← makes conversation useful
5. OP-C3  push-to-talk voice                     ← absorbs OP-V1e
6. OP-C4  conversation actions + handoff hook
7. OP-C5  turn memory / follow-ups
8. OP-V1g KAIRO mobile shell (reuses converse API over tunnel)
9. OP-C6  wake word (only if the loop earns it)
```

Rationale: conversation core first (1–2) so every later surface (handoff,
signals, voice, mobile) plugs into one dialogue channel instead of growing
parallel one-off UIs. Real signals (4) before voice (5) so KAIRO has something
worth saying.
