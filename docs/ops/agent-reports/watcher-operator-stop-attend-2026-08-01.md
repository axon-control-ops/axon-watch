# Receipt: Rowan watcher operator-stop attend

- **When:** 2026-08-01
- **Actor:** Rowan (watcher), workspace_axon_watch
- **Leased task:** `task-4ecc3ef8623f4dd8` / run `run_dab2404c8d25`
- **Failed shift under investigation:** `run_318bb58a2c5d` (dedupe `failed_shift:workspace_axon_watch:watcher`)
- **Prior failed retry:** `run_810f37fbf248` (same dedupe; also operator-stopped)
- **Upstream root failure:** `run_cc61ce4419f8` — transient DNS `getaddrinfo EAI_AGAIN api2.cursor.sh`

## Verified inputs

| Item | Evidence |
|------|----------|
| Failed run status | `GET http://127.0.0.1:8787/api/runs/run_318bb58a2c5d` → `phase=failed`, role=`watcher`, task=`task-acad6bcd58454d4f`, duration ≈61s (16:31:48–16:32:49Z) |
| Failure detail | `current_step`: `Lane B agent fallback reply generated (Runtime execution stopped by operator before the CLI finished.)` |
| History terminal receipt | `runtime_dispatch` · `success=False` · intent=`lane_b_agent` at 16:32:49Z |
| Upstream attend target | `task-acad6bcd58454d4f` acceptance cited `run_cc61ce4419f8` DNS `EAI_AGAIN api2.cursor.sh` |
| Upstream run | `GET …/api/runs/run_cc61ce4419f8` → failed in ~3s with Cursor CLI DNS error |
| Stale-reap ruled out | Default watcher stale TTL is 720s (`stale_reconcile.py`); run lasted 61s |
| CP restart ruled out | `GET /health` boot_id stable; CP uptime >30m at investigation time |
| DNS now healthy | `getent hosts api2.cursor.sh` → 8 A records; Cursor CLI auth logged-in (`GET /api/runtime/status`) |
| Watch / connectors | `GET /api/runtime/summary` → watch `ok/connected`; connectors 6/6 ok at 16:46:35Z |
| Fast Gate | `gh run list --limit 3` → success on pushes/PRs at 16:33–16:34Z |

## Root cause

1. **Upstream (`run_cc61ce4419f8`):** Transient DNS resolution failure reaching `api2.cursor.sh` — environmental, not a repo defect.
2. **`run_318bb58a2c5d`:** Cursor CLI subprocess exited on signal (`returncode < 0`), surfaced as `RuntimeProcessStoppedError` via `raise_if_operator_stopped` in `subprocess_runner.py`. This is a **shift-continuation** interrupt (`is_operator_stopped_failure` / `is_shift_continuation_failure`), not a Gate 6 or acceptance defect. The attend shift was killed before it could finish investigating the upstream DNS blip.
3. **`run_810f37fbf248`:** Same interrupt class on the retry (~10.5 min); also continuation, not stale-reap.

## Resolution (this shift)

No code change required for the operator-stop class — remediation is verified investigation plus successful attend completion:

- Confirmed upstream DNS blip is cleared (DNS + Cursor auth green).
- Confirmed watch service and all six connectors healthy.
- Documented failure chain and ruled out stale-reap / CP-restart misclassification.
- Cleared `failed_shift:workspace_axon_watch:watcher` for `run_318bb58a2c5d` with this receipt.

Spend caps, secrets, protected merges, and production were not touched.

## Lead next

- No deploy needed — environmental/transient upstream + operator interrupt, not a control-plane bug.
- Optional hardening (out of this attend scope): add transient DNS retry in `cursor_agent`/`router.py` for `EAI_AGAIN` to reduce cascade into failed_shift attends.
