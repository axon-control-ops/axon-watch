# Operator Refresh Policy (Anti-Freeze v1)

**Opened:** 2026-07-07  
**Status:** Documents shipped G4.4 guards — do not re-implement in planning pass  
**Applies to:** http://127.0.0.1:4173 `console-web` + control-plane SSE  

## Problem statement

Axon-Signal (`:7734`) suffered **UI freeze** from Alpine polling, duplicate fetches, and refresh storms. Axon-X G4.4 shipped guards; this doc locks the **v1 policy** so backend/orchestration work does not regress it.

---

## Event-driven vs heartbeat (honest v1)

| Mechanism | Type today | Interval / trigger | Consumer |
|-----------|------------|-------------------|----------|
| `/api/live/events` SSE `runtime_refresh` | **Heartbeat timer** | ~30s poll fallback + SSE from CP | Full run surfaces refresh |
| `/api/live/events` SSE `presence_refresh` | **Heartbeat timer** | ~10s cadence in CP `live_events.py` | Voice cockpit, presence, briefing coalesce |
| User submit / stop / workspace switch | **True event** | Immediate | Run store, thread, composer |
| Watch signal ingestion | **Event** (watch side) | Probe-driven | Inbox/briefing on next projection fetch |
| `visibilitychange` | **True event** | Tab visible/hidden | Skip refresh when hidden |

**Policy:** Heartbeats are **allowed v1** but must obey visibility + in-flight rules below. Future `BRAIN-UI-3` may add operator-only event taxonomy (connector state change, approval created) to reduce timer noise.

---

## Shipped guards (G4.4 — document, don’t redo)

Source: `apps/console-web/src/lib/live-events-session.ts`, shell store briefing coalescing.

| Guard | Behavior |
|-------|----------|
| **Visibility skip** | No refresh when `document.visibilityState !== 'visible'` |
| **In-flight dedupe** | `refreshInFlight` / `presenceRefreshInFlight` — drop overlapping calls |
| **Background briefing skip** | Briefing refresh skipped or deferred when tab hidden |
| **Briefing fetch coalescing** | Duplicate `/api/briefing` collapsed at 10s presence/runtime overlap |

---

## Stale-while-revalidate pattern

| Surface | SWR rule |
|---------|----------|
| Briefing | Show last good DTO while revalidating; do not blank mission control |
| Runtime summary | Topbar chips may lag ≤1 refresh cycle |
| Inbox counts | Prefer briefing projection; avoid separate inbox poll if briefing fresh |
| IDE agent transcript | Stream is source of truth during turn; no full-page refresh |

**Forbidden:** Blocking UI spinner on entire shell for briefing refetch.

---

## Remaining risk (v1 accepted)

When tab **visible**:

- Periodic HTTP ~**5s** briefing-related fetches (presence path)
- Periodic HTTP ~**10s** full surface refresh (runtime path)

**Mitigation backlog (future, not this pass):**

- Increase intervals when idle + no active run
- Event-only briefing invalidation on watch webhook
- Separate Operator vs IDE refresh schedules (`KAIRO_BRAIN_UI_ARCHITECTURE.md`)

---

## Acceptance: “no axon-local-style freeze”

### Soak test definition

| Parameter | Value |
|-----------|-------|
| Duration | 30 minutes minimum |
| Tab state | Visible, single workspace, Operator mode |
| Active run | Optional — one executing run mid-test |
| Network | Throttle none (local) |

**Pass criteria:**

- UI thread: no lockup > 2s (manual: composer typing stays responsive)
- Network: ≤ 12 briefing fetches / 10 min when idle (measure DevTools or log scrape)
- Memory: heap growth < 50MB over soak without navigation
- SSE: single `/api/live/events` connection; reconnect ≤ 3 times / 30 min

### Metrics (optional automation)

- `briefing_fetch_total` counter in dev-only hook (future)
- Playwright `:4173` soak script — **deferred** (`UX-DEF-SCREEN`)

### Regression gates

- `apps/console-web/src/lib/live-events-session.test.ts` — visibility + dedupe
- `verify:voice-cockpit` — presence_refresh wiring
- Manual checklist in G6 dry-run

---

## IDE mode refresh rules (planning)

| Rule | Rationale |
|------|-----------|
| IDE skips Operator mission-control polling | UX-IDE-1 quiet profile |
| IDE still connects SSE but handlers filter non-critical | Avoid missing approvals |
| Full Access agent stream uses fetch/SSE parse — not briefing poll | Lane B path |

---

## Control-plane SSE contract note

`services/control-plane/app/live_events.py` emits timer-based `presence_refresh` / `runtime_refresh`. **Backend agents:** do not add second SSE endpoints without updating this policy doc.

---

## References

- G4.4 append log in `docs/PHASE_G_SIGNAL_PARITY.md`
- `docs/planning/KAIRO_BRAIN_UI_ARCHITECTURE.md`
- `config/voice-cockpit-slice.json`
