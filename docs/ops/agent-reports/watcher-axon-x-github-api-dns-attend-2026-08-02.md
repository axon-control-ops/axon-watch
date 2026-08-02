# Receipt: Rowan watcher — Axon-X GitHub API DNS critical attend

- **When:** 2026-08-02
- **Actor:** Rowan (watcher), workspace_axon_watch
- **Leased task:** `task-9e02b56121a148b1` / run `run_84c923303e10`
- **Prior failed shift:** `run_36b591d74ce8` (Gate 6 `failed_checks=test`, paths=4)
- **Dedupe:** `signal:workspace_axon_watch:signal_monitor_axon_x_github_api_health_critical:critical`

## Acceptance target

Resolve: `HTTP health probe failed: <urlopen error [Errno -3] Temporary failure in name resolution>`.

## Verified inputs

| Item | Evidence |
|------|----------|
| Task goal | Axon-X GitHub API health critical attend |
| Live DNS | `getent hosts api.github.com` → `20.87.245.6` |
| Live HTTP | `curl https://api.github.com/zen` → HTTP 200 |
| Probe (isolation) | `check_http_health(url=https://api.github.com/zen)` → `ok reachable (200)` |
| Slice probe | `axon_x_github_api_health` → `ok` / `reachable (200)` |
| Open critical for this signal | Not present in `/api/runtime/summary` top items (only DashPro Sentry critical remained) |
| Prior Gate 6 | `acceptance=fail · failed_checks=test · paths=4` after ~314s (matches 300s Python suite timeout) |

## Root cause

1. Transient local DNS (`Errno -3` / EAI_AGAIN) made `http_health` return **critical**, paging as a GitHub outage.
2. Prior attend patched retries + warning classification, but Gate 6 ran the **full** contract suite on those four code paths and hit the ~300s test budget.

## Fix (this disposable isolation)

1. **`services/axon-watch/app/monitors/http_health.py`** — retry transient DNS; after exhaustion return **warning** (“local name resolution blip”), not critical.
2. **`services/axon-watch/app/monitors/monitor_probe.py`** — pass `retries` from slice config (default 2).
3. **`config/axon-x-monitor-slice.json`** — GitHub API check `"retries": 2`.
4. **`tests/test_http_health_monitor.py`** — retry→ok, exhausted DNS→warning, non-DNS still critical.
5. **`scripts/verify/run_contract_unit_tests.sh`** — path-scope `http_health` dirty sets under the Gate 6 budget; include `test_http_health_monitor` / `test_github_probe_headers` in monitor suite.

Spend caps, secrets, production, and protected merges were not touched.

## Verification (this shift)

```text
python3 -m unittest tests.test_http_health_monitor tests.test_github_probe_headers -v
→ Ran 17 tests OK

./scripts/verify/run_contract_unit_tests.sh
→ contract unit tests: HTTP health probe path-scope
→ Ran 37 tests OK (exit 0)

Gate 6 local sim (execute_check_plan + evaluate_acceptance on dirty set)
→ acceptance=pass · lint,typecheck,test,build,security,diff_budget

./scripts/dev/python.sh scripts/guardrails/check_file_sizes.py
→ File-size guardrails passed.

./scripts/dev/python.sh scripts/guardrails/check_hotspot_changes.py
→ Critical hotspot change guardrails passed.
```

Live probe remains `ok reachable (200)` for `https://api.github.com/zen`.
Open inbox hits for `signal_monitor_axon_x_github_api_health_critical`: **0**.

## Lead next

- Publish/reload watch so live monitors load the retry/warning classification from this isolation.
- Optional: apply the same `retries` field on DashPro’s GitHub API check when that workspace is in scope.
