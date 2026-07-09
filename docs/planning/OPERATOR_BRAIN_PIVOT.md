# Operator Brain Pivot

**Status:** Active plan (2026-07-07)  
**Supersedes:** operator-as-run-queue hero; partial revision of `UX-DEF-GALAXY` in [`KAIRO_BRAIN_UI_ARCHITECTURE.md`](KAIRO_BRAIN_UI_ARCHITECTURE.md)  
**Inputs:** Phase G6 dry-run audit, JARVIS Prompt Pack mapping, operator hygiene slice, DashPro monitor slice

---

## Purpose

Pivot OPERATOR mode from **run queue + command wall** to **second brain / situation room**:

- Fleet health across workspaces and integrations (Sentry, PostHog, connectors)
- Unified incident and signal feed
- Prove-source drill-down and handoff to IDE
- Optional **3D brain galaxy** as a cinematic map over the same server-side graph — never alternate truth

IDE mode stays the executor (editor, terminal, Agent Dock). OPERATOR mode is where the operator *understands* what is happening across the fleet.

---

## North star (one sentence)

> OPERATOR = JARVIS situation room over real DTOs; IDE = Cursor-grade executor; runs are a thin action strip, not the hero.

Visual identity remains [`UI_VISUAL_DIRECTION.md`](UI_VISUAL_DIRECTION.md): glass HUD, KAIRO presence, SOC scan order — with an optional 3D brain when the operator wants spatial context.

---

## What G6 dry-run proved

From [`PHASE_G6_DRY_RUN_AUDIT_LOG.md`](../PHASE_G6_DRY_RUN_AUDIT_LOG.md):

| Finding | Lesson for pivot |
|---------|------------------|
| 35+ `review_ready` Git status runs | Verification debt reads as product failure; auto-complete one-shot commands |
| 8–9 zombie `executing` runs | Block `resume from review` on read-only intents |
| 111-thread message wall | Conversation dock is for *human* turns; collapse/dedupe verification spam |
| Global "36 runs ready" vs workspace 17 | Scope briefing and headlines to active workspace + fleet rollup toggle |
| RESUME/ADVISE on one-shot commands | Quick guide + radar CTAs must say COMPLETE or hide for auto-complete intents |
| Stack stable all day | Infrastructure is ready; product narrative is wrong |

**Operator first impression today:** "Broken task manager."  
**Target first impression:** "I see my fleet, what's on fire, and one click to investigate or hand off."

---

## JARVIS pack mapping (revised)

| JARVIS concept | Axon adoption | Authority | Phase |
|----------------|---------------|-----------|-------|
| Watch → notice → advise loop | KAIRO briefing + Attention stack | Server DTOs | **Now** (polish) |
| Personality / presence | KAIRO chip, voice cockpit (G4.4) | Settings + SSE | **Now** |
| Prove-source / jump-to evidence | Signal cards, monitor deep links, IDE handoff | Watch + control-plane | OP-B5 |
| Server-side brain (not local markdown RAG) | `/api/briefing`, signals SQLite, run history | control-plane + watch | **Now** + BRAIN-UI-2 |
| Spatial note galaxy | **3D brain galaxy UI** over `BrainGraphDTO` | **Visualization only** | OP-B6 |
| Keyword markdown RAG | **Reject** as orchestration | Contracted search API later | BRAIN-UI-2 |
| Always-on voice | Event-driven voice (existing) | `kairo_voice.py` | BRAIN-UI-5 |

### 3D brain — scope rules

Adopt the JARVIS galaxy **as presentation**, with hard guardrails from [`UI_REFERENCE_ARCHETYPES.md`](UI_REFERENCE_ARCHETYPES.md):

1. **Not system truth.** Nodes and edges come from `BrainGraphDTO` (same data as list/grid/feed views).
2. **Not a permanent blocker.** Default Operator center may show galaxy when idle; editor handoff or list view always one click away.
3. **Not ambient noise.** Motion on state change (new incident, connector flip, run phase), not idle particle soup.
4. **Meaningful nodes only:** workspaces, connectors, monitor sources (Sentry project, PostHog), open incidents, active runs — not arbitrary markdown files.
5. **Accessibility:** List/feed/grid fallback required; WebGL failure → degraded 2D fleet grid (OP-B1).
6. **Bounded module:** `apps/console-web/src/features/brain-galaxy/` (Three.js or similar); no logic in shell monoliths.

**Color semantics:** reuse `--state-*` tokens; cyan = brand/KAIRO, red/amber = severity, green = healthy connector.

---

## Operator vs IDE (unchanged contract)

| Surface | OPERATOR | IDE |
|---------|----------|-----|
| Center | Fleet grid → incident feed → **3D brain** (views of same DTO) | Editor + terminal |
| Right dock | Signals, integrations, KAIRO briefing (hero bottom) | Runs, approvals, Agent Dock |
| Primary action | Acknowledge, drill down, hand off | Edit, run agent, approve execute |
| Lane | A — native command executor | B — Cursor agent subprocess |

See [`KAIRO_BRAIN_UI_ARCHITECTURE.md`](KAIRO_BRAIN_UI_ARCHITECTURE.md) for lane diagram and API ownership.

---

## Target layout (Operator mode)

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ TOPBAR: workspaces | runtime | KAIRO | OPERATOR ◉ IDE                      │
├──────────┬──────────────────────────────────────────────┬──────────────────┤
│ LEFT     │ CENTER — BRAIN (pick one view, same DTO)      │ RIGHT DOCK       │
│ Fleet    │ ┌─────────────────────────────────────────┐  │ Integrations     │
│ list     │ │  OP-B6: 3D brain galaxy (optional)      │  │ Sentry · PostHog │
│          │ │  — or —                                 │  │ Connectors       │
│          │ │  OP-B1: fleet health grid               │  │                  │
│          │ │  — or —                                 │  │ Signals / inbox  │
│          │ │  OP-B2: unified incident feed           │  │                  │
│          │ └─────────────────────────────────────────┘  │ KAIRO briefing   │
│          │ [ thin run strip — collapsible, OP-B3 ]      │ (hero)           │
├──────────┴──────────────────────────────────────────────┴──────────────────┤
│ STATUS: watch health | workspace | active incidents | clock                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

Scan order: **topbar → right dock exception → center brain → run strip (if expanded)**.

---

## Data sources (existing + new DTOs)

| DTO / API | Today | Pivot use |
|-----------|-------|-----------|
| `RuntimeSummary` | Yes | Topbar, status bar |
| `WorkspaceRecord[]` | Yes | Fleet nodes |
| Watch connectors | Yes | Grid health, galaxy nodes |
| `config/dashpro-monitor-slice.json` | Yes | Sentry/PostHog monitor config |
| `dashpro_sentry` monitor | Yes | Incident source OP-B2 |
| Inbox / signals store | Partial | Unified feed OP-B2 |
| `/api/briefing` | Yes | KAIRO hero copy |
| `RunRecord[]` | Yes | Thin strip only OP-B3 |
| **`BrainGraphDTO`** | **New** | Nodes: workspace, connector, monitor, incident, run; edges: depends-on, emitted-by |
| **`FleetHealthDTO`** | **New** | Per-workspace rollup for grid |
| **`IntegrationStatusDTO`** | **New** | Sentry/PostHog/connector card in dock |

All graph layout (3D positions, clustering) is **client-derived** from `BrainGraphDTO` — server never stores x/y/z as truth.

---

## Phased delivery

### Wave 0 — Hygiene (O1–O5) — *in progress / dry-run blockers*

| ID | Slice | Done when |
|----|-------|-----------|
| O1 | Auto-complete one-shot command intents (`git_status`, `health_probe`, `list_files`, `read_file`) | No new `review_ready` from verification |
| O2 | Guard `resume from review` on auto-complete intents | Zombies cannot be recreated |
| O3 | Operator quick guide: COMPLETE not RESUME for read-only commands | Copy + radar CTAs match |
| O4 | Clear queue / Complete all + test run cleanup script | Acceptance tests leave ≤0 parked runs |
| O5 | Workspace-scoped briefing NOTICE + fleet rollup toggle | Headline matches operator mental model |

**Verification:** `./scripts/dev/check-health.sh`, vitest operator-view tests, dry-run monitor tick shows declining `review_ready`.

---

### Wave 1 — Second brain core (OP-B1 – OP-B5)

| ID | Slice | Owner | Depends |
|----|-------|-------|---------|
| **OP-B1** | Fleet health grid (workspace × connector × last signal) | console-web + control-plane projection | Connectors API stable |
| **OP-B2** | Unified incident feed (inbox + monitor events + Sentry) | watch + console-web | DashPro monitor slice |
| **OP-B3** | Demote run queue to collapsible bottom strip | console-web shell | O1–O5 |
| **OP-B4** | Expand monitor slices beyond DashPro (template + vault keys doc) | watch monitors + config | OP-B2 pattern |
| **OP-B5** | Prove-source + "Continue in IDE" handoff card | control-plane handoff DTO + shell | BRAIN-UI-4 |

**Exit criteria:** Operator can open Axon, see fleet green/red, read one combined feed, expand a Sentry issue, hand off to IDE — without scrolling 19× Git status.

---

### Wave 2 — 3D brain galaxy (OP-B6)

| ID | Slice | Owner | Depends | Status |
|----|-------|-------|---------|--------|
| **OP-B6a** | `BrainGraphDTO` schema + `/api/operator/brain-graph` | control-plane | OP-B1 fleet rollup | **Done** (`operator_brain_graph.py`, 4 tests) |
| **OP-B6b** | 2D graph fallback (deterministic radial SVG) | console-web | OP-B6a | **Done** (`operator-brain-graph-view.ts`, `OperatorBrainGraphPanel.vue`) |
| **OP-B6c** | 3D galaxy view (WebGL, bounded feature module) | console-web `brain-galaxy/` | OP-B6a | **In progress** (WebGL stage + orb + galaxy HUD landed; prove-source wiring still thin) |
| **OP-B6d** | View switcher: GRID \| BRAIN; persist preference | shell store | OP-B6b,c | **Done** (2D; galaxy joins switcher in OP-B6c) |
| **OP-B6e** | Node click → prove-source panel (reuse OP-B5) | console-web | OP-B5 | Partial (workspace click focuses, signal click opens Attention, converse context + artifact handoff skeleton landed) |

**Performance budget:** initial galaxy load <2s on dev machine; <100 animated nodes default; LOD beyond that.

**Defer if:** WebGL unavailable → OP-B6b only (no regression).

---

### Wave 3 — BRAIN-UI carryover

| ID | Notes |
|----|-------|
| BRAIN-UI-2 | Contracted search over signals + runs (not markdown RAG) |
| BRAIN-UI-3 | Operator-only SSE taxonomy (reduce timer noise) |
| BRAIN-UI-5 | Voice → workspace command (hands-free acknowledge) |
| BRAIN-UI-6 | Delivery receipts in Attention list |

BRAIN-UI-1 is ** absorbed by OP-B6** (DTO + visualization). BRAIN-UI-7 stays IDE-only.

---

## Daily monitoring ritual

Reuse and extend [`scripts/ops/g6-dry-run-monitor.sh`](../scripts/ops/g6-dry-run-monitor.sh):

1. **Morning tick** — `./scripts/dev/check-health.sh`, append run/briefing snapshot to audit log.
2. **Operator smoke** — open `:4173` OPERATOR mode; confirm fleet/grid loads, no run-wall regression.
3. **Integration spot-check** — one Sentry or connector path live (not config-only).
4. **Debt gate** — if `review_ready` > 5 or `executing` zombies > 0, hygiene wave blocks feature work.
5. **Weekly note** — 3 bullets in audit log: shipped slice, operator confusion, next slice.

Duration target: **15–20 min/day** unless actively developing OP-B slices.

---

## Success metrics (4-week pivot)

| Metric | Baseline (G6 dry-run) | Target |
|--------|------------------------|--------|
| Time to first useful insight | Dominated by run wall | <10s to fleet or feed |
| `review_ready` after test run | 35+ | 0 |
| Zombie `executing` | 8–9 | 0 |
| Operator threads with >20 verification msgs | Yes | Deduped / hidden |
| Monitor sources in feed | DashPro only | ≥2 workspaces |
| 3D brain | N/A | Toggle works; 2D fallback |

---

## Implementation order (recommended)

```text
O1–O5 (finish hygiene) → OP-B1 fleet grid → OP-B2 incident feed → OP-B3 run strip
  → OP-B6a BrainGraphDTO → OP-B6b 2D graph → OP-B6c 3D galaxy → OP-B5 handoff polish
  → OP-B4 monitor expansion
```

Parallel safe: OP-B4 config work while OP-B6a is in flight.

---

## Wave 4 — KAIRO voice hero + mobile remote (OP-V1)

**Direction (2026-07-08):** OPERATOR becomes **voice-first control plane**, not a run dashboard. The JARVIS reference (AI Workshop OS brain + voice orb) maps to Axon as:

| Surface | Role |
|---------|------|
| **KAIRO Voice Deck** (left sidebar) | Hero presence — orb, ONLINE/SPEAKING, speak briefing, persona line |
| **Fleet + Brain + Incidents** (center) | Situation awareness when operator looks at screen |
| **IDE handoff** (per workspace) | Signal/monitor → create agent run in bound workspace |
| **KAIRO mobile app** | Same DTOs over tunnel: briefing, fleet, speak, dispatch — remote control only |

### Guardrails

- **Voice for:** status, briefing, acknowledge, dispatch, handoff prompts
- **Approval boundary only for:** deploys, production OTA, destructive shell
- **One-shot commands** (`git status`, `health`, `read`, `ls`): auto-complete, no review ceremony
- **Demo workspaces** (`workspace_smoke`, `workspace_bootstrap`, mockup IDs): hidden from `scope=operator` catalog/fleet/brain

### Slices

| ID | Slice | Status |
|----|-------|--------|
| **OP-V1a** | Replace WORKSPACE STATUS with `KairoVoiceDeckPanel` | **Done** |
| **OP-V1b** | `speakOperatorBriefing()` + `briefing` speak event | **Done** |
| **OP-V1c** | `scope=operator` workspace catalog (drop demo/bootstrap) | **Done** |
| **OP-V1d** | `operator-run-cleanup.sh` for verification debt | **Done** |
| **OP-V1e** | Voice capture → dispatch command (hands-free) | **Absorbed by OP-C3** (Wave 5) |
| **OP-V1f** | Signal → IDE handoff card (OP-B5) | Partial (conversation artifacts now carry a Continue in IDE handoff action) |
| **OP-V1g** | KAIRO mobile shell (tunnel + compact voice UI) | Pending |
| **OP-V1h** | Real monitor signals in inbox (Sentry/PostHog beyond bootstrap) | **In progress** (OP-B4: live monitor precedence, actionable counts, `/api/monitors`) |

Mobile contract: reuse `/api/briefing`, `/api/operator/fleet-health`, `/api/operator/brain-graph`, `/api/kairo/speak`, `/api/chat/messages` — no second brain on the phone.

---

## Wave 5 — KAIRO conversation loop (OP-C)

**Direction (2026-07-08):** close the JARVIS dialogue gap — from *KAIRO speaks
at you* to *you converse with KAIRO* (ask → grounded answer → optionally act).
Full plan: [`KAIRO_CONVERSATION_PLAN.md`](KAIRO_CONVERSATION_PLAN.md).

| ID | Slice | Status |
|----|-------|--------|
| **OP-C1** | `/api/kairo/converse` — context pack, turn router, grounded answers (fast status path, no CLI) | **In progress** (fast/deep tiers, DTO fast path, artifacts, voice-log timings) |
| **OP-C2** | Galaxy conversation bar (typed) — one input, command + question lanes, spoken replies | **In progress** (live omnibar, spoken replies, thinking line, command/results split) |
| **OP-C3** | Push-to-talk STT (hold orb / Space) — **absorbs OP-V1e** | **In progress** (orb hold + Space PTT implemented; no wake word) |
| **OP-C4** | Conversation actions — navigation intents, confirmed dispatch, handoff hook | Pending |
| **OP-C5** | Turn memory + follow-ups (session-scoped, non-authoritative) | Pending |
| **OP-C6** | Wake word "KAIRO…" (deferred until loop proven) | Deferred |

Guardrails: answers grounded in DTOs only; approval boundary preserved;
push-to-talk before wake word; bounded modules
(`features/kairo-conversation/`, `kairo_conversation.py`).

### Revised implementation order (2026-07-08)

```text
1. OP-C1  converse API (server core)
2. OP-C2  galaxy conversation bar (typed)
3. OP-V1f / OP-B5  incident → "Hand off to IDE"
4. OP-B4 / OP-V1h  real Sentry/PostHog signals in inbox
5. OP-C3  push-to-talk voice (absorbs OP-V1e)
6. OP-C4  conversation actions + handoff hook
7. OP-C5  turn memory / follow-ups
8. OP-V1g KAIRO mobile shell (reuses converse API over tunnel)
9. OP-C6  wake word (only if the loop earns it)
```

---

## References

- [`KAIRO_BRAIN_UI_ARCHITECTURE.md`](KAIRO_BRAIN_UI_ARCHITECTURE.md) — lanes, APIs, personality
- [`UI_COMPOSITION_SPEC.md`](UI_COMPOSITION_SPEC.md) — shell regions (Operator center ownership **amended** by this doc)
- [`UI_VISUAL_DIRECTION.md`](UI_VISUAL_DIRECTION.md) — tokens, JARVIS guardrails
- [`PHASE_G6_DRY_RUN_AUDIT_LOG.md`](../PHASE_G6_DRY_RUN_AUDIT_LOG.md) — evidence
- [`PHASE_G6_RETIREMENT_READINESS.md`](../PHASE_G6_RETIREMENT_READINESS.md) — G6 gate
- JARVIS Prompt Pack (operator PDF) — spatial brain metaphor
- `config/dashpro-monitor-slice.json`, `services/axon-watch/app/monitors/dashpro_sentry.py`

---

## ADR note (galaxy reversal)

Previous register entry `UX-DEF-GALAXY` deferred 3D galaxy as "not Axon-shaped." This pivot **reopens** galaxy as **OP-B6 visualization** while keeping the rejection of galaxy-as-authority and markdown-RAG-as-orchestration. Update [`PHASE_G5_INTENTIONAL_DISCARDS.md`](../PHASE_G5_INTENTIONAL_DISCARDS.md) when OP-B6 ships — move row from discard to "viz-only adoption."
