# Frontend continuous shift retry (Gate 6) — 2026-08-23

- owner: frontend
- scope: bounded retry for the failed console UI/UX, dock, and shell polish shift blocked by missing or failing `acceptance_evidence` (Gate 6)
- root cause: `scripts/dev/ensure-python-deps.sh` reinstalled editable Python deps on every verifier run; in this workspace that rebuild hit `services/axon-watch/axon_watch_service.egg-info` timestamp writes and blocked `verify:console-web` before the actual frontend checks could complete
- code change: `scripts/dev/ensure-python-deps.sh`
  - skip redundant pip bootstrap when the repo venv already contains both editable installs and the requirements hash matches
  - persist the requirements hash under `output/python-bootstrap/requirements.sha256`, a writable workspace path, instead of `.venv`
  - remove the `awk` dependency from the hash read so the guard works on this host
- acceptance receipts:
  - `curl -sf http://127.0.0.1:8787/health` → `{"service":"control-plane","status":"ok","mode":"bootstrap","boot_id":"5017802a33414aeca4c6af913cfa8448"}`
  - `python3 -m unittest tests.test_cli_runtime_agent_sandbox tests.test_gate6_control_plane_owned_paths` → `Ran 37 tests ... OK`
  - `./scripts/dev/python.sh scripts/guardrails/check_css_import_order.py` → `CSS @import order guardrail passed.`
  - `npm run verify:console-web` → `351 passed` test files, `1904 passed` tests, production build completed, `VERIFY-CONSOLE-WEB PASS`
- result: pass for the bounded frontend retry; the Gate 6 path now reaches the real console-web checks and finishes cleanly on this workspace
- blockers: none for this bounded frontend retry
- lead next: treat this retry as the frontend receipt for the prior Gate 6 failure; if a control-plane run record is still needed upstream, attach this report and the successful verifier outputs to that run history instead of rerunning the UI slice

## Addendum — Sunday, August 23, 2026

- retry trigger: a newer bounded shift failed with `Workspace npm toolchain is not ready:` followed by an `npm warn deprecated uuid@7.0.3` line
- finding: the deprecation line was only a warning during install, not the blocker
- verified cause:
  - `npm run verify:console-web` initially failed at `@axon-watch/console-web test` with `sh: 1: vitest: not found`
  - `npm ls uuid --depth=4` showed `uuid@7.0.3` arriving from `expo -> @expo/config-plugins -> xcode`, which explains the warning text but not the failed shift
  - `apps/console-web/package.json` and `package-lock.json` both already included `vitest`, so the local `node_modules` state was incomplete
- bounded recovery:
  - ran `npm ci` at the workspace root; install completed successfully and emitted the same `uuid@7.0.3` deprecation warning as a non-fatal warning
  - reran `npm run verify:console-web`
- acceptance receipts:
  - `npm ci` → `added 602 packages, and audited 607 packages in 39s`
  - rerun `npm run verify:console-web` → `351 passed` test files, `1908 passed` tests, production build completed, `VERIFY-CONSOLE-WEB PASS`
- code changed this addendum: none
- result: pass for the bounded frontend retry after repairing the local npm toolchain from the lockfile
- blockers: none for the frontend bounded retry; remaining npm output is warning-level only
- lead next: if the upstream runtime still reports npm-not-ready for this workspace, treat it as stale or separately rooted from this checkout and attach this addendum as the receipt for the successful local recovery

## Addendum — Sunday, August 23, 2026 (live bounded retry)

- retry trigger: rerun the failed console UI/UX, dock, and shell polish bounded shift from this workspace and verify the current blocker with live receipts
- verified cause before repair:
  - first live `npm run verify:console-web` passed CSS imports, typecheck, and Vitest (`351` files / `1908` tests), then failed in the build step with `sh: 1: vue-tsc: not found`
  - `apps/console-web/package.json` already declared `vue-tsc` in `devDependencies`, so the failure was local install state, not missing source wiring
  - the deprecation line `npm warn deprecated uuid@7.0.3: uuid@10 and below is no longer supported...` appeared during install flow only and was not the blocking error
- bounded recovery:
  - ran `npm ci` at the workspace root to rebuild `node_modules` from `package-lock.json`
  - reran `npm run verify:console-web` after the install completed
- acceptance receipts:
  - first live `npm run verify:console-web` → `Test Files 351 passed (351)`, `Tests 1908 passed (1908)`, then `sh: 1: vue-tsc: not found`
  - `npm ci` → `added 602 packages, and audited 607 packages in 39s`
  - second live `npm run verify:console-web` → `Test Files 351 passed (351)`, `Tests 1908 passed (1908)`, build completed, `VERIFY-CONSOLE-WEB PASS`
- code changed in this addendum: none
- result: pass for the bounded frontend retry on Sunday, August 23, 2026 after repairing the workspace npm install state; the prior `uuid@7.0.3` message remains warning-level only
- blockers: none for the bounded frontend retry
- lead next: use this addendum as the current receipt for the frontend retry; if another runtime still reports npm-not-ready after this pass, investigate that runtime's own workspace cache rather than reopening the console-web slice
