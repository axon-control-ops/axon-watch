# KAIRO Mode — Research And AXON-X Integration

## Purpose

This document closes a gap in the frozen planning bundle: how the current
**JARVIS** implementation in Axon works, what it means architecturally, and how
that capability should evolve into **KAIRO** inside the new **AXON-X** product
without becoming another monolith.

`KAIRO` stands for **Knowledge-Augmented Intelligence for Response and
Oversight**.

KAIRO is **not** a single toggle or a chatbot skin. In AXON-X it is a
cross-cutting **operator presence layer** built from watching, advising,
interrupting, speaking, and executing with receipts.

## Executive Summary

Current Axon is already **partway JARVIS-capable**:

- persona wiring exists and is enabled by default
- voice playback, companion voice, and spoken attention cues exist
- proactive watch rules (`observe`, `advise`, `approval`, `execute`) exist
- delivery receipts across desktop, push, voice eligibility, Slack, and
  webhooks exist
- mobile operator cockpit and native companion paths exist

Current Axon is **not yet a full always-on JARVIS**:

- mobile listening remains foreground-first, not background-always-armed
- delivery maturity is uneven across channels
- persona, voice UI, watch loop, and delivery policy are spread across many
  modules
- there is no single bounded owner for operator presence in the new
  architecture

For **AXON-X**, this capability should be treated as **KAIRO**: an operator
experience composed from bounded services, not a mode implemented inside one
process.

## What KAIRO Means In AXON-X

The current Axon docs describe the target operator loop honestly in
[`docs/architecture/axon-jarvis-readiness-plan.md`](../../docs/architecture/axon-jarvis-readiness-plan.md):

```text
watch
  -> notice
  -> summarize
  -> advise
  -> ask / approve
  -> execute
  -> verify
  -> remember
```

That loop maps cleanly onto the new architecture:

| KAIRO step | AXON-X owner |
|---|---|
| `watch` | `axon-watch` |
| `notice` / `summarize` | `axon-watch` signals + correlation |
| `advise` | `control-plane` recommendations / briefing projection |
| `ask / approve` | `control-plane` approvals + run-state `awaiting_approval` |
| `execute` | `control-plane` dispatch + bounded tool execution |
| `verify` | run receipts + fitness functions |
| `remember` | persisted signal history + run history |

## Current Axon Implementation Surfaces Researched

These are the current **JARVIS**-named source surfaces that inform the KAIRO
design.

### 1. Persona layer

- [`axon_data/jarvis_personality.py`](../../axon_data/jarvis_personality.py) —
  JARVIS system prompt builder
- [`axon_data/default_settings_seed.py`](../../axon_data/default_settings_seed.py) —
  `jarvis_mode`, `jarvis_operator_title`, `jarvis_voice_identity`
- [`brain.py`](../../brain.py) — prepends JARVIS persona when enabled
- [`axon_api/services/companion_runtime.py`](../../axon_api/services/companion_runtime.py) —
  JARVIS-aware voice context

**New owner:** `packages/prompt-contracts/` + control-plane voice/chat
orchestration

**Rule:** persona affects wording and tone, not system truth.

### 2. Voice and spoken-alert layer

- [`ui/js/voice-conversation.js`](../../ui/js/voice-conversation.js) —
  `toggleJarvisMode()` enables hands-free + ambient desktop + voice mode
- [`ui/js/voice-attention-monitor.js`](../../ui/js/voice-attention-monitor.js) —
  polls attention/proactive summaries and speaks alerts
- [`ui/js/voice-playback.js`](../../ui/js/voice-playback.js) — TTS playback with
  JARVIS mode awareness
- [`axon_api/services/axon_tts.py`](../../axon_api/services/axon_tts.py) —
  server-side TTS with JARVIS settings
- [`axon_api/routes/companion_voice_stream.py`](../../axon_api/routes/companion_voice_stream.py) —
  streaming companion voice turns

**New owner:** `console-web` voice/presence features + control-plane voice APIs

**Rule:** spoken alerts consume canonical watch/control DTOs; they do not invent
signal truth.

### 3. Voice Command Deck / operator presence UI

- [`ui/js/vcd-jarvis-orchestrator.js`](../../ui/js/vcd-jarvis-orchestrator.js) —
  maps live Axon state into the VCD deck
- [`ui/js/voice-command-center.js`](../../ui/js/voice-command-center.js) — voice
  command center orchestration
- [`ui/js/mobile-voice-jarvis-controller.js`](../../ui/js/mobile-voice-jarvis-controller.js) —
  mobile/PWA field unit controller
- CSS surfaces: `voice-jarvis-hud.css`, `vcd-jarvis.css`,
  `voice-mobile-jarvis-controller.css`

**New owner:** `console-web/features/operator-presence/` and
`console-web/features/voice-deck/`

**Rule:** deck/HUD is presentation only; it reads run-state and signal DTOs.

### 4. Watch / interruption / delivery layer

- [`axon_api/services/proactive_watcher.py`](../../axon_api/services/proactive_watcher.py) —
  ambient watch loop
- [`axon_api/services/proactive_next_actions.py`](../../axon_api/services/proactive_next_actions.py) —
  `watch_rule_for_item()` with `observe`, `advise`, `approval`, `execute`
- [`axon_api/services/operator_notification_policy.py`](../../axon_api/services/operator_notification_policy.py) —
  channel routing, quiet hours, interruption explanation
- [`axon_api/services/mobile_push.py`](../../axon_api/services/mobile_push.py) —
  mobile push delivery
- JR tracks in [`docs/architecture/axon-jarvis-readiness-plan.md`](../../docs/architecture/axon-jarvis-readiness-plan.md)

**New owner:** primarily `axon-watch` for watch + delivery; `control-plane` for
inbox projection and operator-facing briefing

**Rule:** KAIRO's always-watching continuity belongs in Watch, not in the
interactive control-plane process.

### 5. Executive operator workflow

- [`axon_api/services/executive_operator_workflow.py`](../../axon_api/services/executive_operator_workflow.py) —
  Notice / Advise / Decide / Execute / Verify / Report rhythm

**New owner:** `control-plane` orchestration layer

**Rule:** this is the human workflow contract above raw signals.

## What KAIRO Mode Should Mean In AXON-X

Do **not** port the old toggle as one boolean that turns on everything.

In AXON-X, split KAIRO into explicit operator-presence settings:

| Setting | Meaning | Owner |
|---|---|---|
| `operator_persona_enabled` | Use KAIRO-style phrasing in voice/chat copy | `prompt-contracts` + presentation layer |
| `spoken_alerts_enabled` | Speak high-value watch/control events when allowed | `console-web` voice layer |
| `hands_free_enabled` | Continuous voice command loop | `console-web` voice layer |
| `ambient_presence_enabled` | Desktop/mobile operator deck stays live and visible | `console-web` operator-presence UI |
| `continuous_watch_enabled` | Background watch service remains active | `axon-watch` service supervision |
| `privacy_mode` | Gates listening/speech/interruption behavior | shared operator policy |

The old `toggleJarvisMode()` behavior becomes a **KAIRO preset** that enables a
safe bundle of these settings, not a hidden global mode switch.

## Recommended AXON-X Architecture

```text
axon-watch
  watch workers
  signal normalization + correlation
  interruption policy inputs
  delivery router + receipts
        |
        v
control-plane
  inbox + briefing projection
  run-state + approvals
  executive operator workflow
  voice/chat orchestration
        |
        v
console-web
  operator cockpit
  voice deck / spoken alerts
  agent dock + runtime strip
  operator/IDE layout modes
        |
        v
packages/prompt-contracts
  KAIRO persona module
  spoken-alert phrasing templates
  executive operator response rules
```

## Integration Principles

1. **Watch owns continuity.** If AXON-X is KAIRO-like, the always-on part
   belongs in `axon-watch`, not in Axon's main server process.
2. **Control plane owns decisions.** Approvals, dispatch, run phases, and
   handoffs stay interactive and explicit.
3. **UI owns presence.** VCD, spoken alerts, mobile cockpit, and deck/HUD are
   presentation layers over canonical DTOs.
4. **Persona is not truth.** KAIRO tone must not override run-state, signal
   severity, or approval boundaries.
5. **Interruption must be policy-driven.** Use watch rules and delivery policy,
   not ad hoc `speakMessage()` calls scattered in UI modules.
6. **Foreground mobile honesty remains.** Do not overclaim background listening
   in v1; document `foreground + push` as the safe model until proven otherwise.

## Migration Slices For KAIRO

### JX-1 — Watch rule metadata in canonical signals

Move watch-rule semantics into the new signal envelope:

- `watch_rule.mode`: `observe` | `advise` | `approval` | `execute`
- `watch_rule.interrupts`
- `watch_rule.reason`

Source to adapt:

- `proactive_next_actions.watch_rule_for_item()`
- `operator_notification_policy.explain_operator_interruption()`

### JX-2 — Delivery policy and receipts in Watch

Make Watch the upstream producer of delivery attempts and receipts for
watch-born events.

Source to adapt:

- `operator_notification_policy.py`
- `mobile_push.py`
- delivery status/receipt patterns from JR-002

### JX-3 — Operator briefing projection in control plane

Expose a stable briefing/summary API for UI and voice:

- top signals
- pending approvals
- active runs
- next safe actions
- degraded/connectivity state

Source to adapt:

- `/api/proactive/briefing`
- executive operator workflow summaries

### JX-4 — Vue operator presence shell

Rebuild the operator presence surfaces in the new frontend:

- operator cockpit first screen
- voice deck / command center
- spoken-alert hook bound to watch SSE/events
- mobile-friendly compact layout

Source to adapt:

- VCD/JARVIS orchestrator behavior
- mobile operator cockpit from JR-001

### JX-5 — Persona and spoken-alert contracts

Extract persona and phrasing into bounded contracts:

- `build_jarvis_system_message()`
- compact spoken-alert templates
- executive operator plain-language rules

Source to adapt:

- `jarvis_personality.py`
- `executive_operator_workflow.py`
- voice alert copy rules from JARVIS readiness plan

## What To Adopt, Adapt, Rewrite, Discard

| Current surface | Action | New owner |
|---|---|---|
| JARVIS operator loop docs | `adopt` | `KAIRO_MODE.md`, `PRODUCT.md` |
| `watch_rule_for_item()` semantics | `adapt` | `axon-watch` signal ranking/policy |
| Delivery receipts / quiet hours | `adapt` | `axon-watch/delivery` |
| Executive operator workflow | `adapt` | `control-plane` orchestration |
| `jarvis_personality.py` | `adapt` | `packages/prompt-contracts` |
| VCD / mobile JARVIS UI behavior | `adapt` | `console-web/features/operator-presence` |
| Alpine voice-attention polling | `rewrite` | Vue store + watch/control event stream |
| In-process proactive watcher as JARVIS backbone | `discard` | replaced by `axon-watch` |
| Background mobile listening claims | `discard` until proven | document honest foreground + push model |
| Scattered `speakMessage()` as policy | `discard` | replace with policy-driven spoken alerts |

## Parity Requirements

KAIRO-related behaviors that must survive migration:

- spoken high-value alerts when privacy mode allows
- watch rules that distinguish observe/advise/approval/execute
- delivery receipts visible to the operator
- executive operator daily rhythm: Notice, Advise, Decide, Execute, Verify,
  Report
- mobile/PWA operator cockpit compactness
- honest foreground mobile monitoring scope

See [`PARITY_LEDGER.md`](PARITY_LEDGER.md) for the ledger entries added for
these.

## Fitness Functions For KAIRO

Add to [`FITNESS_FUNCTIONS.md`](FITNESS_FUNCTIONS.md):

- spoken alert latency from signal event to UI/voice eligibility
- interruption dedupe rate for repeated low-value signals
- delivery receipt completeness for critical signals
- briefing API latency budget
- privacy-mode gating correctness for spoken alerts

## Transition Seam

During strangler migration:

- old Axon may continue to own live voice/companion paths initially
- new Watch may produce canonical signals first
- new control plane may expose briefing/inbox projections
- new Vue shell may consume new DTOs through ACL/façade adapters

Do not attempt to enable the **KAIRO preset** in AXON-X until:

1. watch signals are canonical
2. delivery receipts exist
3. briefing/runtime summaries are stable
4. operator presence UI reads those DTOs

See [`TRANSITION_ARCHITECTURE.md`](TRANSITION_ARCHITECTURE.md).

## Recommended ADR

Add **`ADR-005-kairo-as-operator-presence-layer.md`** with decision:

- KAIRO is an operator-presence composition, not a monolithic mode
- Watch owns continuous observation and delivery
- Control plane owns decision/actuation workflow
- persona/presentation are bounded modules, not orchestration truth

## Acceptance Criteria

This research is complete enough when:

- KAIRO is mapped to explicit AXON-X owners
- the old scattered implementation surfaces are classified
- migration slices exist
- parity, transition, and fitness docs reference KAIRO explicitly
- the plan no longer treats operator presence as an undocumented product pillar
