# Agent polish notes (internal)

Post-cutover parity closure: **`docs/PARITY_CLOSURE_ROADMAP.md`** (locked slice order).

Side notes for future slices — not operator-facing. Keep concise and actionable.

---

## Watch connectors (2026-07-05, TEST-3)

### Shipped in v1

- Config file `config/watch-connectors.json` with HTTP health probes
- Watch routes: `/internal/watch/connectors`, `/internal/watch/summary`
- Control-plane: `/api/connectors`, runtime summary `connectors` block
- Required connector failures → inbox signals (`source: connector`)
- Optional `axon_local` probe when classic Axon is down (informational only)

### Polish later (priority order)

1. **UI surface** — No connector panel in shell yet. `/api/connectors` is API-only.
   Add Attention sidebar or Mission Control rail cell bound to live connector DTOs.

2. **Inbox ranking for optional connectors** — Optional failures hidden from inbox by
   design. Consider a lower-severity “glance” chip in status bar when `axon_local`
   is down but Axon-X stack is healthy.

3. **Replace bootstrap degraded signal** — `signal_runtime_summary_degraded` still
   emits with bootstrap copy. Once connector truth is trusted, narrow or remove this
   placeholder signal (coordinate with signal-consistency lane).

4. **Probe caching / TTL** — Every summary/connectors/inbox hit re-probes all URLs.
   Add short TTL cache in watch service to reduce dev-stack probe storms.

5. **Reprobe command** — Shipped in TEST-4 via `POST /internal/watch/commands`
   (`reprobe_connector`). UI trigger still missing.

---

## Watch command / event / status depth (2026-07-05, TEST-4)

### Shipped in v1

- Commands: `reprobe_connector`, `refresh_summary`
- Routes: watch `POST/GET /internal/watch/commands`, `GET /internal/watch/events`,
  `GET /internal/watch/events/stream`
- Control-plane proxy: `/api/watch/commands`, `/api/watch/events`
- Summary `observation` block (events + last command metadata)
- In-memory bounded command/event stores (200 events)

### Polish later

1. **Persistent command/event store** — in-memory resets on watch restart; move to
   SQLite under `AXON_WATCH_STATE_DIR` for dedicated-server slice.

2. **UI command triggers** — reprobe connector / refresh summary buttons in
   Attention or Mission Control (API-only today).

3. **Additional command types** — `acknowledge_signal`, `suppress_signal`,
   `rescan` per frozen watch-api.md (defer until signal depth + delivery receipts).

4. **Real event stream** — v1 SSE polls every 2s; replace with push on append or
   shared bus when watch command/event depth grows.

5. **Command async queue** — v1 executes synchronously in request thread; long probes
   could block; add worker queue if probe targets multiply.

6. **Auth on watch internal routes** — loopback-trusted only; dedicated-server slice
   must add service-to-service auth.

7. **Connector probe cache invalidation** — reprobe updates receipt but inbox/summary
   still re-probe all connectors on next read; tie reprobe result into short TTL cache.

8. **Starter guide** — add “Watch commands” section with curl examples once UI exists.

### Do not regress

- TEST-3 connector semantics unchanged
- Ephemeral watch server tests: restore modules only in tearDown
- Idempotent command_id reuse returns existing record

---

## Delivery receipts (2026-07-05, TEST-5)

### Shipped in v1

- `app/delivery/` — policy, in-memory receipt store, inbox enrichment
- Routes: watch `GET /internal/watch/delivery/receipts`, CP `GET /api/delivery/receipts`
- Inbox items: `delivery_state`, `latest_receipt_id`, `delivery_receipt_count`
- Summary `observation`: receipt counts
- Delivery lifecycle events on watch events log
- Attention sidebar delivery badge (`DELIVERED` / state chip)

### Polish later

1. **Persistent receipt store** — in-memory resets on watch restart; SQLite under
   `AXON_WATCH_STATE_DIR` for dedicated-server slice.

2. **Real channel adapters** — v1 simulates inbox/desktop; wire chat, push, Slack,
   webhook when operator notification preferences migrate from axon-local.

3. **Operator preferences** — severity routing currently uses static defaults in
   `delivery/policy.py`; migrate `operator_notification_preferences` semantics.

4. **Quiet hours / interrupt policy** — defer to KAIRO watch rules slice (TEST-6).

5. **Receipt detail panel** — badge only today; add Attention drill-down listing
   receipts per signal.

6. **Failed delivery retry** — v1 dedupes successful channels only; add retry command
   or automatic backoff for `delivery_failed`.

---

## Prior slices (quick reminders)

### Real project connection (TEST-1)

- Bound workspaces not in sidebar — need catalog unification or “Connected projects” list
- Bindings file manual edit only

### Workspace handoff (TEST-2)

- No UI for handoff create/list — API only
- No auto workspace switch after handoff

### Mission control (TEST-0)

- Feed is receipt-depth only; no full agent transcript in center
- Terminal Operator default hidden — polish reopen discoverability in onboarding

---

*Append new sections per slice. Do not reorder cutover checklist here.*
