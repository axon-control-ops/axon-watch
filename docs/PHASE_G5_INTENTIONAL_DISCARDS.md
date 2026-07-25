# Phase G5.4 — Intentional Discards (IMPORT_MATRIX)

**Opened:** 2026-07-07  

Every `docs/planning/IMPORT_MATRIX.md` row marked **`discard`** is listed here with rationale. Operator must acknowledge before G6 retirement sign-off.

**Acknowledgment format:** check box when you accept the discard for Axon-X primary operator use (`:4173`).

---

## Frontend / UX patterns

| Capability | Rationale | Operator ack |
|------------|-----------|--------------|
| Alpine boot flow | Vue + Vite stack replaces Alpine bootstrap; no carry-over | [ ] |
| Large HTML shell patterns | Componentized `console-web`; `ui/index.html` shell-only rule | [ ] |
| Inline UI logic inside shell files | Bounded `apps/console-web/src/**` modules only | [ ] |

## Backend architecture

| Capability | Rationale | Operator ack |
|------------|-----------|--------------|
| In-process scheduler monolith | Watch workers + explicit orchestration (`axon-watch` service) | [ ] |
| Giant route modules | Bounded packages under `services/control-plane/app/` | [ ] |
| Hotspot-heavy mixed ownership files | No monolith imports; guardrails in planning FITNESS | [ ] |

## Execution model

| Capability | Rationale | Operator ack |
|------------|-----------|--------------|
| Implicit state from prompt text | Persisted run-state (ADR-004); transcript is not truth | [ ] |

## Runtime / AI orchestration

| Capability | Rationale | Operator ack |
|------------|-----------|--------------|
| Local model bridge / Ollama path | Phase F/G target: Cursor/Codex CLI fabric, not Ollama backbone | [ ] |

## Delivery / notifications

| Capability | Rationale | Operator ack |
|------------|-----------|--------------|
| Ad hoc alert logic in multiple places | Consolidated watch delivery policy + receipts | [ ] |

## KAIRO / operator presence

| Capability | Rationale | Operator ack |
|------------|-----------|--------------|
| Background mobile listening claims | Honest v1: foreground + push only (`KAIRO_MODE.md`) | [ ] |
| Scattered `speakMessage()` as interruption policy | Policy-driven spoken alerts via briefing + `spoken_alert_policy.py` | [ ] |

## Data / persistence

| Capability | Rationale | Operator ack |
|------------|-----------|--------------|
| Hidden direct DB reach-through | Explicit APIs + DTO panels; no Supabase-style table browser | [ ] |

## Developer experience

| Capability | Rationale | Operator ack |
|------------|-----------|--------------|
| Repo-wide planning sprawl | Canonical home `docs/planning/` + MANIFEST (TEST-9) | [ ] |

---

## Operator-approved deferrals (not IMPORT_MATRIX discards)

These are **explicit deferrals** with fallback to `:7734` until replaced or discarded in G5.4 addendum.

| Item | Slice | Rationale | Operator ack |
|------|-------|-----------|--------------|
| WhatsApp Web monitor on Axon-X | G4.2 | Bounded watch slice not shipped; DashPro monitor remains on axon-local | [ ] |
| JARVIS 3D note galaxy | Brain-UI plan | Not system truth; Operator center stays mission control, not spatial graph | [ ] |
| Markdown keyword RAG as brain | Brain-UI plan | Server-side briefing + run history replaces ad hoc note search | [ ] |
| Electron desktop shell | BROWSER_ONLY contract | Browser + Playwright only; packaged desktop deferred | [ ] |
| Full `npm run verify` in TEST-3/TEST-9 step 5 | G5 gate design | Scoped bundles until vault/manifest triage — see `PHASE_G5_GATE_DESIGN.md` | [ ] |

---

## Sign-off

- [ ] I accept the discards above for Axon-X as primary operator surface.
- [ ] I accept the deferrals above with documented `:7734` fallback where noted.

**Operator:** ___________________ **Date:** ___________
