# Full Platform Bug Audit

**Repository:** `axon-watch` (product name "Axon-X") — `/run/media/vaxon/axon-data/repos/axon-nvme/repos/axon-watch`
**Audit date:** 2026-08-25
**Method:** Read-only static inspection (source, config, schema, CI, infra) plus targeted, non-destructive command execution (typecheck, unit tests, `npm audit`, syntax checks). No code, configuration, or database file was modified. No secret values were printed; all sensitive material is redacted or described by category only.
**Audit team:** one coordinating pass plus five parallel deep-dive slices — Frontend/UX, Backend/API, Security/Auth, Database/Data-Integrity, Infrastructure/CI/Self-Healing/Integrations.

---

## 1. Executive Summary

**Overall platform health: functional local-first alpha with two Blocker-severity and four Critical-severity defects.** The core product loop (Vue console ↔ FastAPI control-plane ↔ FastAPI watch service, all backed by local SQLite) works and is covered by a large, mostly-passing test suite (1930/1931 frontend Vitest tests pass; 125/125 targeted backend unittest cases pass in the modules exercised). However, the platform has **no real authentication boundary on its most dangerous surfaces**, and its one first-party production deployment path (the dedicated-server Docker Compose file) **does not actually work** and, if patched naively, would deploy with a publicly-documented placeholder credential.

**Total findings: 46**, spanning every audited layer.

| Severity | Count |
|---|---:|
| Blocker | 2 |
| Critical | 4 |
| High | 9 |
| Medium | 19 |
| Low | 9 |
| Informational | 3 |

**Confirmed: 41 · Highly Probable: 1 · Potential Risk: 3 · Unverified: 1**

### Most dangerous problems

1. **SEC-001 (Blocker):** The workspace terminal WebSocket (`/api/workspaces/{id}/terminal`) has **zero authentication**, for a structural reason — the app's only auth middleware is built on Starlette's `BaseHTTPMiddleware`, which never runs for WebSocket scopes. Anyone who can reach the socket gets an interactive shell with no credentials, regardless of any auth setting.
2. **SEC-002 / SEC-003 (Critical):** Almost every `GET` route (workspace files, chat history, tasks, missions, host artifacts) requires no identity by design, and the flag that's supposed to turn auth on for internet-reachable deployments (`is_remotely_reachable()`) is **not** set automatically when the product's own bundled Cloudflare tunnel (autostart-on-by-default) goes live. A deployment that enables the tunnel through the console — the normal, documented way to do it — can be fully exposed to the internet with authentication silently still "off."
3. **INFRA-001 / INFRA-002 (Blocker/Critical):** `infra/docker-compose.dedicated.yml`, the only containerized deployment path in the repo, has no dependency-install step at all (crash-loops on boot), and its `env_file` points at the checked-in `config/deployment.env.example` rather than the `.env` its own header instructs operators to create — so once someone fixes the install gap without noticing the second bug, the reference deployment path runs with the literal placeholder token `AXON_WATCH_OPERATOR_TOKEN=replace-me` baked in.
4. **FE-001 (Critical):** Every agent/chat markdown render path feeds into Vue's `v-html` through one function that calls `marked.parse()` with **no HTML sanitization** anywhere in the console. Because agents routinely narrate back content fetched from email, Sentry, and the web, this is a real indirect-prompt-injection → stored XSS chain inside an authenticated, Vault-scoped operator session.
5. **DB-002 (High, reproduced):** Two independent, drifted copies of the `workspace_tasks`/`workspace_handoffs` DDL exist (one deliberately inlined to dodge a test-import quirk, one authoritative). A direct repro against a fresh temp database throws `sqlite3.OperationalError: no such column: mission_id` — a real crash, currently masked only by incidental call ordering.
6. **BE-001/BE-002 (High):** The watch command/event pipeline has a genuine check-then-act race (confirmed real because the route handler is a sync `def` on Starlette's thread pool) that lets a retried command execute its side effects twice, and a second race that can throw an unhandled `IntegrityError` on concurrent event appends.

### Most fragile platform areas

- **The authentication/authorization boundary as a whole.** It is not one bug but a systemic pattern: an allowlist-of-what's-protected model for GETs, a WebSocket route no HTTP middleware can reach, a "remote reachability" flag decoupled from actual network exposure, and a hardcoded fallback signing secret — four independent gaps that compound into one severe exposure once any of them individually goes wrong.
- **Self-healing/recovery UI-to-backend wiring.** The Recovery Center — the one surface built specifically for incident response — has 8 of 11 possible action buttons wired to nothing, and two of the platform's own reliability primitives (circuit breaker, retry-fingerprint escalation) are fully-built dead code never called from any real failure path.
- **SQLite schema ownership.** With no migration framework, schema evolution is ~15 independent `_ensure_*`/`ALTER TABLE` guards scattered across modules; DB-002 shows concretely what happens when two of them drift.
- **Deployment packaging.** The only containerized/production reference path in the repo was apparently never run end-to-end.

### Immediate risks

Any operator who has enabled — or will enable — the bundled Cloudflare tunnel (autostart-on by default, `config/tunnel-slice.json` ships `"enabled": true`) without separately, manually setting `AXON_WATCH_REMOTELY_REACHABLE`/`AXON_WATCH_PUBLIC_BASE_URL` is running an unauthenticated remote-shell-plus-full-data-read service on the open internet today. This is the single highest-priority item in this report.

### Areas that could not be verified

Full line-by-line review of `apps/console-mobile/App.tsx` (2,643 lines); live concurrency reproduction of BE-002/DB-004's race conditions under real load; whether `mission.impact[].verification_commands` (SEC-010) has any write path beyond the static config file; real-world exploitability of the DOMPurify/nanoid/postcss transitive vulnerabilities at runtime; behavior of `nightly-verify.yml`'s live-evidence run (not executed, as it starts long-running services); any state outside this repository (deployed instances, if any). See §16 for the full list.

---

## 2. Platform and Architecture Map

Axon-X is a local-first "operator and coding environment" combining an IDE-style console, an AI-agent orchestration layer, and a monitoring/signals watcher.

**Applications**
- `apps/console-web/` — Vue 3 + Vite + Pinia + TypeScript console. Monaco editor and xterm terminal hosts, agent dock, vault/data/settings/skills surfaces, operator/IDE shell (`TopBar`/`LeftSidebar`/`CenterWorkbench`/`RightDock`/`StatusBar`), Recovery Center, Kairo voice/presence.
- `apps/console-mobile/` — Expo/React Native companion app (confirmed substantial and actively developed during this audit — 2,643-line `App.tsx`, real `expo`/`react-native` dependencies; a prior internal audit note calling this "not implemented" is now stale).
- `apps/console-desktop/` — Tauri desktop wrapper with a Rust host-policy/runtime layer for allowlisted host commands.

**Backend services**
- `services/control-plane/app/` — FastAPI interactive backend: auth, chat/agent APIs, run-state, task ledger, workspace catalog/files/terminal, worker scheduling, leads/missions, operator briefing, platform recovery, CLI runtime (Cursor/Codex/Claude adapters + sandbox), vault proxy.
- `services/axon-watch/app/` — FastAPI watch service: connector/monitor probes, signal production, delivery receipts/adapters, watch commands/events, tunnel supervision, its own vault store.

**Persistence:** Local SQLite exclusively (no Postgres/Supabase in active use; `supabase/`, `migrations/`, `db/` directories exist but are empty). Roughly 56 `CREATE TABLE` statements across ~20+ store modules in both services, plus ~5 sidecar SQLite files (fleet self-heal, platform recovery, workspace delivery, CI remediation, vault).

**Shared contracts:** `packages/shared-types/` — TypeScript DTOs for runs, runtime summary, signals, delivery receipts, watch summary, briefing, presence, host context.

**Key workflows:**
- *Operator workflow:* console loads workspaces/runtime summary/runs/briefing/inbox → operator approves/dispatches → control-plane records runs/tasks and may launch a local AI CLI (Cursor/Codex/Claude) as a subprocess, optionally inside a Bubblewrap sandbox.
- *Watch workflow:* axon-watch probes connectors/monitors independently of control-plane, persists signals/events, and control-plane aggregates/projects them into the operator inbox and briefing.
- *Recovery workflow:* `platform_recovery`/`fleet_self_heal` detect stuck runs/CI failures and expose a Recovery Center; see REL-001/002/003 for how much of this is actually wired end-to-end.
- *Remote-access workflow:* a bundled Cloudflare tunnel can expose the console/control-plane publicly; see SEC-003 for why this is currently dangerous.

**Infrastructure:** `infra/systemd/` (system + per-user service units), `infra/caddy/Caddyfile.example` (reverse proxy reference), `infra/docker-compose.dedicated.yml` (reference container topology — see INFRA-001/002). CI: `.github/workflows/fast-gate.yml` (per-push/PR) and `nightly-verify.yml` (cron, live-stack strict verify).

**External integrations:** GitHub Actions/webhooks, Sentry, PostHog, Supabase-monitored external apps, Cloudflare tunnel, IMAP/SMTP, Azure Speech, SearXNG/Google CSE/DuckDuckGo research, generic webhook/Slack/mobile-push delivery adapters, Cursor/Codex/Claude CLIs.

A prior internal architecture audit (`AXON-X-PLATFORM-AUDIT.md`, 2026-08-23, already in this repo) covers product-strategy-level maturity (tenant/company modeling, SaaS readiness) in depth and is a valid complementary reference; this report is scoped to concrete, evidence-based bugs and risks rather than product-architecture strategy. One claim from that document was independently re-verified and found **stale**: build artifacts under `apps/console-web/dist` and the Tauri bundle are **not** currently tracked in git (0 tracked files confirmed via `git ls-files`), so that item is resolved and is not carried forward here.

---

## 3. Verification Performed

| # | Command | Result | Notes |
|---|---|---|---|
| 1 | `cd apps/console-web && npm run typecheck` | **PASS** | `vue-tsc --noEmit` via local wrapper, exit 0 |
| 2 | `cd apps/console-web && npx vitest run` | **1 failed / 1931 total** | Failure traced to FE-002 (pre-existing copy/truncation mismatch, not a test-harness issue) |
| 3 | `PYTHONPATH=services/control-plane python3 -m unittest tests.test_run_stale_reconcile tests.test_reap_stale_interactive_runs tests.test_control_plane_runs -v` | **PASS** (57 tests) | |
| 4 | `PYTHONPATH=services/control-plane python3 -m unittest tests.test_cli_runtime_agent_sandbox tests.test_cli_runtime_agent_sandbox_hook_policy tests.test_agent_sandbox_cleanup tests.test_platform_recovery tests.test_desktop_session -v` | **PASS** (68 tests) | |
| 5 | `npm audit --omit=dev` (repo root) | **14 advisories** (2 high, 12 moderate) | See SEC-008 |
| 6 | `bash -n` on `scripts/dev/up.sh`, `down.sh`, `check-health.sh`, `lib/common.sh`, and 5 spot-checked `scripts/verify/test*.sh` | **PASS**, all syntactically clean | |
| 7 | Direct repro: fresh temp SQLite DB, first call `workspace_mission_store.attach_task_mission()` | **Reproduced failure**: `sqlite3.OperationalError: no such column: mission_id` | See DB-002 |
| 8 | Direct repro: `truncate()` logic against the lengthened failure-copy string | **Reproduced**: output cut mid-word, CTA dropped | See FE-002 |
| 9 | `git ls-files` scans for tracked `.env`, `*.sqlite3`, `dist/`, secret-like filenames | One stray tracked empty `.sqlite3` found (DB-001); no tracked `.env`, no tracked `dist/`, no obvious committed secret files | |
| 10 | `.env` vs `.env.example` key-diff (names only, no values) | 4 real, code-consumed keys present in `.env` but undocumented in `.env.example` | Config-hygiene gap, folded into INFRA findings context |
| 11 | All 82 root `package.json` script path references | All resolve to existing files | No missing-script defects found |
| 12 | Repo-wide grep sweeps: `CREATE TABLE`, `CHECK(`, `PRAGMA foreign_keys`, `journal_mode`, `record_failure(`/`record_success(`/`allow_request(`, `record_retry_attempt`, `sqlite3_backup|.backup(|iterdump`, `TODO|FIXME|HACK|XXX` | See individual findings | Used as evidence throughout §6 |
| 13 | `find . -iname "Dockerfile*"` (repo-wide, excluding `node_modules`) | **Zero real Dockerfiles** | See INFRA-001 |
| 14 | Installed `starlette.middleware.base` source inspection | Confirmed `BaseHTTPMiddleware.__call__` skips non-`"http"` ASGI scopes | Root cause of SEC-001 |

**Deliberately not run:** `npm run verify:contracts` / `npm run verify` (full suite) — per confirmed prior session history, these reliably hang 300s+ on `tests.test_control_plane_runtime_summary`, a real network probe against a watch service not running in this exact invocation context, not a code defect. `scripts/dev/up.sh` was not invoked by any audit slice (services were already running live in this shared environment — see §16); no audit slice started or stopped the shared stack.

---

## 4. Severity Summary

| Severity | Confirmed | Probable | Risks/Unverified | Total |
|---|---:|---:|---:|---:|
| Blocker | 2 | 0 | 0 | **2** |
| Critical | 4 | 0 | 0 | **4** |
| High | 8 | 1 | 0 | **9** |
| Medium | 16 | 0 | 3 | **19** |
| Low | 9 | 0 | 0 | **9** |
| Informational | 2 | 0 | 1 | **3** |
| **Total** | **41** | **1** | **4** | **46** |

---

## 5. Prioritized Findings

### Blocker
- **SEC-001** — Unauthenticated terminal WebSocket → full remote shell (Confirmed)
- **INFRA-001** — `docker-compose.dedicated.yml` has no install step; containers crash-loop (Confirmed)

### Critical
- **SEC-002** — Nearly all GET routes unauthenticated by design (Confirmed)
- **SEC-003** — "Remotely reachable" flag not derived from actual tunnel exposure (Confirmed)
- **INFRA-002** — Compose file loads secrets from the checked-in example file, not `.env` (Confirmed)
- **FE-001** — Unsanitized markdown → `v-html` XSS across all agent output (Confirmed)

### High
- **FE-002** — Live Ops ticker truncates the confidence-failure message, drops the retry CTA (Confirmed)
- **BE-001** — Watch command submission race → duplicate side effects (Confirmed)
- **SEC-004** — Hardcoded fallback secret for desktop session-cookie signing (Confirmed)
- **SEC-005** — Workspace binding allowlist defaults to the operator's entire home directory (Confirmed)
- **DB-002** — `workspace_tasks`/`workspace_handoffs` schema drift; reproduced crash (Confirmed)
- **DB-003** — `run_store.list_runs()` fully unbounded, ~35 hot call sites (Confirmed)
- **DB-006** — No backup/recovery mechanism for any local SQLite state (Confirmed)
- **REL-001** — Recovery Center: 8 of 11 action buttons wired to nothing (Confirmed)
- **BE-002** — Watch event `sequence` race → unhandled `IntegrityError` (Highly Probable)

### Medium
- **FE-003** — Email settings: Signal-bridge UI removed, backing fields/PATCH still live (Confirmed)
- **BE-003** — `GET /api/runs` fully unbounded (Confirmed)
- **BE-004** — CORS origins always include 10 dev-loopback defaults, cannot be locked down (Confirmed)
- **BE-005** — Stale-reconcile "verification test active" check is host-wide, not per-workspace (Confirmed)
- **SEC-006** — Operator chat "run …" uses an easily-bypassed denylist, not the real sandbox (Confirmed)
- **SEC-008** — Known-vulnerable transitive npm dependencies (dompurify/nanoid/postcss/uuid) (Confirmed)
- **DB-001** — Stray tracked, empty `control-plane.sqlite3`; `.gitignore` pattern mismatch (Confirmed)
- **DB-004** — WAL/foreign-key/busy-timeout PRAGMAs set on only 1 of 6 SQLite connection factories (Confirmed)
- **DB-005** — No DB-level `CHECK` constraints on enum-like columns (Confirmed)
- **DB-007** — No migration framework; ~15 ad hoc schema-evolution guards (Confirmed)
- **INFRA-004** — No dependency/security scanning in CI (Confirmed)
- **INFRA-005** — Fast-gate never boots real services; only once-daily nightly does (Confirmed)
- **INFRA-006** — Production systemd units run as root with no hardening, unlike desktop units (Confirmed)
- **REL-002** — Circuit-breaker subsystem is fully unwired dead code (Confirmed)
- **REL-003** — Bounded-retry escalation ladder (`retry_fingerprint`) never invoked (Confirmed)
- **INTEG-001** — Delivery retry has zero backoff between attempts (Confirmed)
- **BE-006** — Terminal task-lease resolution has a check-then-act race (Potential Risk)
- **BE-008** — Sandbox scratch prep can permanently block dispatch on `.agents`/`.codex` dirs (Potential Risk)
- **INTEG-002** — Connector health-probe 750ms default timeout risks false "unavailable" (Potential Risk)

### Low
- **FE-004** — Dead "LEGACY OFFLINE" connector-chip code left over from a rename (Confirmed)
- **BE-007** — Mission-lifecycle notification failures silently swallowed, unlogged (Confirmed)
- **BE-009** — Task list/cancel-batch hard-caps at 500 with no truncation signal (Confirmed)
- **SEC-007** — Desktop bootstrap session cookie always issued `secure=False` (Confirmed)
- **SEC-009** — No security response headers on either FastAPI app (Confirmed)
- **DB-008** — `vault_secrets` has no `UNIQUE` constraint on `name` (Confirmed)
- **INFRA-003** — CI Python version (3.12) matches neither the Docker image (3.13) nor local dev (3.14) (Confirmed)
- **INFRA-007** — `Caddyfile.example` sets no security headers (Confirmed)
- **INTEG-003** — Generic webhook/mobile-push adapters have no outbound signing (Confirmed)

### Informational
- **REL-004** — Fleet self-heal and tunnel supervisor are well-designed with real safeguards (positive finding)
- **FE-005** — `console-mobile` scope correction: substantial real app, prior "not implemented" note is stale
- **SEC-010** — Unsandboxed `shell=True` mission-verification path; reachability unconfirmed (Unverified)

---

## 6. Detailed Findings

The full evidence-backed finding catalog has been moved to [FULL_PLATFORM_BUG_AUDIT_FINDINGS.md](FULL_PLATFORM_BUG_AUDIT_FINDINGS.md) to keep this audit within the repository file-size guardrail. Finding IDs, severities, and recommended fixes are unchanged.

## 7. Broken User Journeys

| Journey | What breaks | Findings |
|---|---|---|
| **Enable remote access via the bundled tunnel** | Operator turns on the tunnel through the console (the normal path). Auth never activates because the tunnel doesn't set the "remotely reachable" flag. Result: unauthenticated shell access (SEC-001) and unauthenticated full data read (SEC-002) exposed to the entire internet, with no warning beyond a startup log line. | SEC-001, SEC-002, SEC-003 |
| **Deploy to a dedicated server via the documented Docker Compose path** | Following the file's own header instructions produces containers that crash-loop (no install step); if that's fixed without also fixing the `env_file` bug, the deployment silently runs with a public placeholder auth token. | INFRA-001, INFRA-002 |
| **Operator sees a stuck/failed run in Recovery Center and tries to act on it** | Clicking Retry, Cancel, Approve, or any "Open X" button silently does nothing — no error, no feedback, just a background list refresh. The two buckets that most need action (STALE, FAILED) offer the most dead buttons. | REL-001 |
| **Operator relies on the platform-doctor "provider availability" status** | Always reports healthy/PASS regardless of actual AI/GitHub/CI provider health, because the circuit-breaker subsystem behind it is never fed real outcomes. | REL-002 |
| **Agent narrates external content back into chat (email, Sentry, web)** | If that content contains HTML with event-handler attributes, it executes in the operator's authenticated session when rendered. | FE-001 |
| **Operator watches the Live Ops ticker to learn why an employee shift failed** | The most common failure explanation is truncated mid-word, and the actionable "Tap Try again" instruction is silently dropped. | FE-002 |
| **Operator disables a previously-enabled Signal email bridge** | The control to see or turn it off has been removed from the UI, but the setting itself is still live and still round-tripped on every save. | FE-003 |
| **New/fresh install, or a maintenance script attaches a task to a mission before any other task operation has run** | Crashes with `no such column: mission_id`. | DB-002 |
| **Client retries a timed-out watch command (reprobe/refresh/acknowledge)** | The action can execute twice instead of returning the cached result; concurrent event appends can crash with an unhandled DB error. | BE-001, BE-002 |
| **Long-running deployment accumulates runs/tasks over time** | Run and task listing endpoints, and the scheduler's own bookkeeping, become increasingly expensive full-table scans with no pagination; operator-initiated runs are never pruned at all. | BE-003, DB-003 |

---

## 8. Alerts and Remediation Navigation

The platform's primary "alert surface" for operational health is the **Recovery Center** panel plus the platform-doctor status. Both have direct navigation/actionability problems:

- **Recovery Center action buttons** (REL-001): 8 of 11 possible action labels the backend can produce have no frontend handler *and* no backend endpoint at all (`Retry`/`Cancel`/`Approve` don't exist as routes). The alert is real, but clicking through it leads nowhere — the single worst finding under this audit phase's specific focus (alerts must route to a working remediation).
- **Platform-doctor "provider_availability" status** (REL-002): Always reports PASS because nothing ever feeds the circuit breaker real failures — an operator trusting this indicator gets a false all-clear regardless of actual GitHub/AI/CI provider health, and there's no UI surface showing circuit state at all (zero references in the console).
- **Connector "unavailable" status** (INTEG-002): Can fire as a false positive purely from network latency (750ms hard timeout, no retry, no distinction between "timed out once" and "confirmed down"), which could train operators to dismiss genuine outage signals as noise.
- **Delivery receipts on 429/5xx** (INTEG-001): Retries happen immediately with no backoff, so a receiver already struggling under rate-limiting is hit again immediately rather than being given room to recover — the retry itself can look like it "worked" from the operator's perspective (no visible alert) while quietly worsening the receiving side's condition.

No alert/popup component was found that routes to an *incorrect* destination (wrong record/section) — the problem in this codebase is specifically that several alert-adjacent controls don't route anywhere at all, or that the underlying signal is structurally incapable of ever firing (permanently-green circuit breaker).

---

## 9. Security Findings Summary

The security posture has one dominant systemic issue: **read/write access to this platform's most sensitive surfaces does not actually depend on authentication being correctly configured, because several independent enforcement points all have gaps that only matter in combination.**

- The one WebSocket route bypasses the only HTTP auth middleware structurally (SEC-001).
- Nearly all GET routes are unauthenticated by explicit design, not accident (SEC-002).
- The flag that's supposed to turn auth on for internet-facing deployments isn't derived from actual exposure, and the product's own bundled remote-access feature (the tunnel) doesn't set it (SEC-003).
- A fallback authentication secret is a literal string baked into the public source (SEC-004).
- The one authorization boundary for file access (workspace root allowlist) defaults broad enough to expose the whole home directory (SEC-005).
- A second, weaker shell-execution security model (denylist) exists in parallel with the platform's well-built primary one (allowlist + sandbox) (SEC-006).
- Supporting findings: known-vulnerable transitive dependencies (SEC-008), a cookie missing `Secure` on one endpoint (SEC-007), no baseline HTTP security headers (SEC-009), and one unconfirmed conditional command-injection path pending a reachability check (SEC-010).

**What was verified as sound:** vault crypto (AES-256-GCM, PBKDF2 480k iterations), vault/watch SQL parameterization (no injection found anywhere), path-traversal defenses in the file-explorer and static-asset routes (correct `resolve()`+`relative_to()` checks, including symlink-escape handling), the Bubblewrap agent sandbox's capability-drop and namespace isolation, CORS default scoping (explicit allowlist, not wildcard), SSRF surface (all outbound webhook targets are operator-configured, not request-controlled), and debug endpoints (`/docs`/`/redoc` correctly disabled in both services).

---

## 10. Data Integrity Findings Summary

- **Schema drift is real and reproducible** (DB-002): two independently-maintained DDL copies for the same tables have already diverged, masked today only by incidental call ordering.
- **No backup mechanism exists at all** (DB-006) for the platform's sole persistence layer — a lost or corrupted state directory has no recovery path.
- **Unbounded queries are the default pattern**, not the exception, for the two largest-growing tables (`runs` via DB-003/BE-003; task listing is capped but with no continuation mechanism, BE-009).
- **Concurrency hygiene is inconsistent**: one connection factory (the main control-plane DB) correctly sets WAL/foreign-keys/busy-timeout; five other SQLite-backed stores across both services do not (DB-004), and two real races were found in the watch service specifically (BE-001, BE-002).
- **No DB-level validation** exists anywhere (DB-005) — all enum/status discipline is Python-side and inconsistently applied (some modules validate on write, some don't).
- **No formal migration tooling** (DB-007) is the structural root cause behind DB-002's drift, and the repo's `migrations/`/`db/`/`supabase/` directories are empty placeholders.
- One git-hygiene finding (DB-001): a stray, currently-harmless tracked empty SQLite file, not currently reachable by any code path but indicative of a `.gitignore` pattern gap.
- **What's verified sound:** WAL/FK setup on the primary connection factory, correct transaction boundaries around sequence allocation (with an explicit comment documenting the race it fixed), correct child-before-parent delete ordering everywhere checked, a correctly-applied optimistic-concurrency task-leasing pattern, no soft-delete/resurrection risk (no soft-delete pattern exists at all), and no dev/seed-data leak risk found.

---

## 11. Integration Findings Summary

| Integration | Finding | Severity |
|---|---|---|
| Watch delivery adapters (webhook/Slack/mobile push/desktop/inbox) | No backoff between retry attempts on 429/5xx/timeout | Medium (INTEG-001) |
| Connector health probes | 750ms hard timeout, no retry, no distinction between transient and confirmed failure | Medium (INTEG-002) |
| Generic webhook/mobile-push adapters | No outbound HMAC signing — receiver can't verify sender authenticity | Low (INTEG-003) |
| Watch command pipeline (internal, but functions as an integration boundary between control-plane and watch) | Retry produces duplicate side effects; concurrent event writes can crash | High (BE-001, BE-002) |
| Cloudflare tunnel | Autostart-on by default; does not itself establish the auth posture its own exposure requires | Critical (SEC-003) |
| CI webhook (GitHub) | Signature verification fails closed, uses timing-safe comparison — verified sound, no finding |  |
| Vault credential resolution (across settings/env/vault/legacy-file/systemd sources) | Verified sound — never hardcodes a real secret, correctly distinguishes vault references from literal tokens |  |
| npm dependency tree (Monaco/DOMPurify, expo/uuid, postcss) | Known-vulnerable transitive versions | Medium (SEC-008) |

No credential-handling bug, API-version incompatibility, or data-mapping error was found in any of the delivery adapters, connector probes, or the vault-mediated credential resolution chain — the integration-layer issues found are entirely about retry/timeout/backoff behavior and outbound authenticity, not correctness of the integration logic itself.

---

## 12. Self-Healing and Reliability Gaps

| Failure class | Current behavior | Should detect | Could safely auto-repair | Needs human approval | Loop-prevention |
|---|---|---|---|---|---|
| Stuck/stale runs | `stale_reconcile.py` reaps stale runs with a host-wide (not per-workspace) "is a test still running" veto (BE-005) | Per-workspace process correlation, not host-global | Yes, once the veto is correctly scoped | No — reaping a genuinely stale run is already the "safe repair" | TTL-bounded already |
| Watch command retries | Can double-execute side effects (BE-001) | Cached-result-on-retry | Yes — atomic claim is a safe, mechanical fix | No | N/A — this is the loop-prevention gap itself |
| Recovery Center actions | 8 of 11 actions are dead ends, including `Retry`/`Cancel`/`Approve` with no backend route at all (REL-001) | N/A (UI/routing gap) | Retry/Cancel are plausibly safe to automate once implemented | Approve is explicitly a human-approval action by name — must stay manual | N/A |
| Provider outages (AI/GitHub/CI/network/DB/worktree) | Circuit breaker exists, fully unwired (REL-002) — nothing is ever protected from hammering a known-bad dependency | Real failure/success outcomes from actual dispatch/probe/delivery call sites | Yes, once wired — `allow_request()` gating is exactly the "safe auto-repair" (stop calling a broken dependency) | No | Already designed with `HALF_OPEN` half-life; just needs the wiring |
| Cross-failure-class retry escalation | `retry_fingerprint` ladder exists, fully unwired (REL-003); actual enforcement runs through the simpler `attempt_budget` mechanism instead | Same fingerprint repeating across attempts | Retry/alternate steps yes; forced `HUMAN_REVIEW` at step 4 already encodes the "stop auto-repairing" boundary correctly | Yes — by design, ladder already escalates to human review | Ladder design already prevents infinite loops; currently just inert |
| Local SQLite state loss | No backup mechanism at all (DB-006) | N/A — this is prevention, not detection | A scheduled `VACUUM INTO` backup is safe to automate | No | N/A |
| Fleet self-heal (VAXON) dispatch | Verified well-designed: scan-interval gate, recency window, task-superseding, attempt budget, regression-exclusion (REL-004) | — | — | Already gated by `AXON_WATCH_SELF_HEAL_LEVEL` autonomy tiers | Confirmed sound |
| Tunnel reconnection | Verified well-designed: real exponential backoff + jitter, respects a deliberate operator stop (REL-004) | — | — | — | Confirmed sound |
| Delivery failures | No backoff on retry (INTEG-001) | Retry-After / backoff timing | Yes, mechanical fix | No | Bounded by existing `retry_max_attempts` (1-5) |

**Overall assessment:** the platform's self-healing *design* (policy gating by autonomy level, refusal to guess on `UNKNOWN` failures, human-approval requirements for auth/config/worktree failures, fleet-repair loop guards) is genuinely sound where it's connected — but two of its three central reliability primitives (circuit breaker, retry-fingerprint escalation) and most of its primary human-facing remediation UI (Recovery Center) are not connected to anything. This is the single most impactful category of "should be automatic but currently requires unnecessary manual intervention (or provides none at all)" in the platform.

---

## 13. Missing Test Coverage

To prevent each High-or-above issue from regressing silently, add:

- **SEC-001:** Integration test opening the terminal WebSocket with auth mode on, no credentials, non-loopback client — assert rejection before any PTY output.
- **SEC-002:** A test iterating every registered GET route under `local_token` mode with no credentials, asserting no data-bearing route outside an explicit public allowlist returns 200.
- **SEC-003:** A test starting a mock tunnel with neither reachability flag set, asserting the service now requires credentials.
- **INFRA-001/002:** A CI job (or scheduled workflow) that runs `docker compose config` + `up --build` against a throwaway `.env`, asserting both services reach `service_healthy` and the effective environment does not contain the placeholder token.
- **FE-001:** A unit test asserting `renderAgentMessageMarkdown()` strips `onerror`/`onload`/`javascript:` from adversarial input.
- **DB-002:** A test that calls `attach_task_mission()` (and the equivalent `workspace_handoffs` path) as the very first DB operation against a fresh temp database, asserting no exception — this test would fail today.
- **DB-003/BE-003:** A test seeding several thousand runs and asserting `list_runs`/`GET /api/runs` are bounded/paginated rather than returning everything.
- **BE-001/BE-002:** Concurrency tests (thread-barrier-forced races) asserting exactly-once execution for duplicate `command_id` submissions and no unhandled exception under concurrent `append_event` calls.
- **REL-001:** A contract test asserting every action label `_actions_for()` can produce has a matching frontend handler, so a newly-added label fails CI until wired.
- **REL-002/REL-003:** Tests asserting at least one real dispatch/probe call site invokes `record_failure`/`record_success`, and that repeated failures actually change `allow_request()`'s answer.
- **General:** a CI-level `npm audit --omit=dev` / `pip-audit` gate (INFRA-004, SEC-008) and a bounded live-boot smoke step in the per-PR fast-gate workflow, not just nightly (INFRA-005).

---

## 14. Recommended Repair Order

**Immediate (before any further deployment, especially any tunnel/remote-access use):**
1. SEC-001 — add auth to the terminal WebSocket.
2. SEC-003 — tie tunnel start to the remote-reachability posture (or refuse to start without a token).
3. SEC-002 — require identity on data-bearing GET routes.
4. SEC-005 — narrow the default workspace-binding allowlist (mitigates SEC-002's blast radius immediately even before the full GET-auth fix lands).
5. SEC-004 — remove the hardcoded desktop-session fallback secret.
6. INFRA-002 — fix the compose `env_file` path (cheap, and currently the only thing standing between INFRA-001 getting fixed and a default-insecure deployment).

**Short term (next development cycle):**
7. FE-001 — add markdown sanitization at the one choke point.
8. INFRA-001 — decide and implement: real Dockerfile, or remove the compose file.
9. DB-002 — add the missing schema-ensure call in `attach_task_mission`/handoff path; add the cross-order regression test.
10. BE-001/BE-002 — atomic command claim; safe sequence allocation.
11. REL-001 — either implement Retry/Cancel/Approve endpoints or disable the dead buttons with explanation.
12. DB-006 — stand up a basic `VACUUM INTO` backup script.
13. SEC-006 — route operator "run" chat through the existing allowlist/sandbox instead of the denylist.
14. SEC-008 / INFRA-004 — dependency audit fixes plus a CI scanning gate.

**Medium term (reliability and architectural improvements):**
15. REL-002/REL-003 — wire the circuit breaker and retry-fingerprint ladder into real call sites, or formally retire them.
16. DB-003/BE-003 — pagination across `list_runs`/`GET /api/runs` and migration of hot call sites to scoped queries.
17. DB-004 — shared PRAGMA-setup helper across all six connection factories.
18. INFRA-005/006 — live-boot smoke step in fast-gate; harden production systemd units.
19. INTEG-001/002 — delivery backoff; connector probe timeout/retry tuning.
20. FE-002/FE-003 — ticker truncation fix; finish or revert the Signal-bridge UI removal.

**Long term (technical-debt reduction):**
21. DB-007 — consolidate ad hoc schema-evolution guards into one ordered, version-tracked migration list.
22. DB-005 — add DB-level `CHECK` constraints as defense-in-depth.
23. SEC-009/INFRA-007 — baseline security headers on both FastAPI apps and the Caddy reference config.
24. SEC-010 — confirm reachability of the mission-verification `shell=True` path and unify its validation with `verification_execution.py`.
25. General repo hygiene: DB-001 (`git rm --cached` the stray tracked SQLite file, broaden the `.gitignore` pattern), FE-004 (delete confirmed-dead connector-chip code), BE-007/BE-009 (logging + truncation-signal polish).

---

## 15. Top 10 Issues to Fix First

| Priority | Bug ID | Issue | Severity | Impact | Recommended Action |
|---:|---|---|---|---|---|
| 1 | SEC-001 | Terminal WebSocket has no authentication | Blocker | Full unauthenticated remote shell | Add identity check before `websocket.accept()` |
| 2 | SEC-003 | Tunnel exposure doesn't trigger the auth posture it requires | Critical | Compounds SEC-001/002 into open-internet exposure | Tie tunnel start to remote-reachability / require a token |
| 3 | SEC-002 | Nearly all GET routes unauthenticated by design | Critical | Full unauthenticated read of files, chat, tasks, missions | Invert default to deny-by-default for GETs |
| 4 | INFRA-002 | Compose file loads secrets from the checked-in example, not `.env` | Critical | Public placeholder token becomes the real deployment credential | Fix `env_file` path; guard against the placeholder value |
| 5 | INFRA-001 | Compose file has no install step | Blocker | Reference deployment path doesn't work at all | Add real Dockerfiles or remove the compose file |
| 6 | FE-001 | Unsanitized markdown → `v-html` XSS | Critical | Indirect-prompt-injection → stored XSS in an authenticated Vault-scoped session | Sanitize `marked.parse()` output at the one choke point |
| 7 | SEC-005 | Workspace binding allowlist defaults to `$HOME` | High | Widens SEC-002's blast radius to the entire home directory | Narrow the default allowlist |
| 8 | DB-002 | `workspace_tasks`/`workspace_handoffs` schema drift | High | Reproduced crash on a real, reachable code path | Call the owning schema-ensure function before writing |
| 9 | SEC-004 | Hardcoded fallback desktop-session secret | High | Full auth bypass on a password-only deployment | Fail closed instead of falling back to a literal string |
| 10 | BE-001 / BE-002 | Watch command/event pipeline races | High | Duplicate side effects; unhandled crash on concurrent writes | Atomic command claim; safe sequence allocation |

---

## 16. Verification Limitations

- **Shared, live working tree.** This repository is actively worked on by concurrent background agents during normal operation (confirmed prior session memory, and directly observed during this audit — the checked-out branch changed twice mid-session, from `fix/run-lifecycle-and-npm-diagnostics` to `fix/remove-axon-local-runtime`, with a large, unrelated diff surface). All five audit slices adapted by re-deriving diffs against `master...HEAD` or reading current on-disk state directly rather than trusting a single `git diff` snapshot, and this is noted at the top of each slice's findings. Findings reflect the codebase as read at inspection time; a small window exists where a concurrently-landing change could shift a specific line number.
- **`npm run verify:contracts` / `npm run verify` were not run to completion.** Per confirmed prior-session history, these reliably hang 300s+ on `tests.test_control_plane_runtime_summary` (a real network probe against a watch instance not reachable in that exact invocation), independent of code changes. Targeted `unittest` batches were run instead (§3); the real authoritative full-suite gate is the `fast-gate`/`nightly-verify` GitHub Actions CI, which run in a clean environment this audit did not have access to trigger.
- **No live concurrency reproduction.** BE-001 was reproduced via direct code+thread-model analysis (route handler confirmed to be a sync `def`, genuinely dispatched to Starlette's thread pool) but not fired under real concurrent load in this session. BE-002, BE-006, DB-004's cross-process contention scenario, and INTEG-002's WAN-latency claim are Highly-Probable/Potential-Risk precisely because live-load reproduction was out of scope for a read-only audit.
- **`apps/console-mobile/App.tsx` (2,643 lines) was not reviewed line-by-line.** Its existence and dependency maturity were confirmed (FE-005), but a dedicated pass for XSS/state/accessibility issues within that file was not completed.
- **SEC-010's reachability question is open.** No public write path to `mission.impact[].verification_commands` was found in the time available, but the full call graph of `workspace_missions/verification.py` and every mission-mutation route was not exhaustively traced.
- **`npm audit` reflects the local lockfile at inspection time**, not a live, continuously-updated CVE feed; real-world runtime exploitability of the flagged DOMPurify chain specifically (whether untrusted HTML actually reaches it at runtime, versus only Monaco's own UI chrome) was not traced end-to-end.
- **No accessibility tooling (axe, Lighthouse) or browser-driven manual QA was run.** The frontend audit's accessibility findings (contrast ratios, aria-labels) were verified by direct code/CSS-token inspection, not automated or in-browser testing, and were limited to a representative sample of components (TopBar, StatusBar) rather than every screen.
- **No live deployment, staging environment, or production instance was observed.** All infrastructure findings (systemd hardening, Docker Compose, Caddy config) are static-file analysis; none were deployed and exercised.
- **`nightly-verify.yml`'s live-evidence CI run was not triggered or observed** — it starts a full live stack and was out of scope for a non-destructive local audit.
- **Prior audit cross-reference:** `AXON-X-PLATFORM-AUDIT.md` (2026-08-23) was used as architectural context and one of its claims (tracked `dist/` build artifacts) was independently re-verified and found stale/resolved; its other architectural claims (tenant/company model maturity, SaaS readiness) were not independently re-verified line-by-line in this pass since they are product-strategy observations rather than reproducible code bugs.

---

## Completion Checklist

- [x] All source directories (apps, services, packages, scripts, infra, config)
- [x] All frontend routes and major components (console-web shell, agent dock, settings, recovery center; console-mobile scope-verified but not line-by-line; console-desktop directory-level)
- [x] All backend endpoints and services (control-plane's 20 route modules; axon-watch's commands/connectors/delivery/events/monitors/signals/tunnel)
- [x] Authentication and authorization (dedicated security slice — 10 findings)
- [x] User roles and permissions (workspace/agent-role model reviewed; no human user/tenant model exists, consistent with prior architecture audit)
- [x] Database schema and migrations (dedicated database slice — 8 findings, including a direct reproduction)
- [x] Background jobs and queues (scheduler, stale-reconcile, retention, fleet self-heal, delivery retry)
- [x] External integrations (GitHub, Sentry, PostHog, Cloudflare tunnel, email, Azure Speech, search providers, delivery adapters)
- [x] Alerts, notifications, and popups (Recovery Center, platform-doctor status, connector status)
- [x] Configuration and environment-variable usage (`.env`/`.env.example` drift, CORS config, deployment topology cross-checks)
- [x] Build, lint, type-check, and test results (typecheck PASS, Vitest 1930/1931, targeted backend unittest 125/125, `npm audit`)
- [x] CI/CD and deployment configuration (both GitHub workflows, both Docker/systemd/Caddy paths)
- [x] Security controls (auth middleware, sandboxing, secrets handling, injection sweeps)
- [x] Accessibility (representative component sample — see limitations)
- [x] Mobile and responsive behaviour (console-mobile scope-corrected; Vue mobile shell reviewed)
- [x] Logging and monitoring (silent-failure and sensitive-logging sweep across both services)
- [x] Self-healing and recovery mechanisms (dedicated reliability slice — circuit breaker, retry fingerprint, fleet self-heal, tunnel supervisor)
- [x] Missing and incomplete features (Recovery Center wiring gap, Signal-bridge partial removal, empty migration/supabase directories)
- [x] Dead code, TODOs, FIXMEs, mocks, and placeholders (repo-wide TODO/FIXME sweep — none found in application code; dead code found and cataloged: FE-004, REL-002, REL-003)
