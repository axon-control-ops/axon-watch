# Night Watch digest — 2026-07-17

Role: watcher (signals, connectors, runtime health)  
Workspace: workspace_axon_watch  
Shift: always_on

## Runtime health (live)

| Check | Result |
|---|---|
| Console web `:4173` | ok |
| Control plane health/ready | ok / ready |
| Watch health/ready (`:8788`) | ok / ready |
| Connectors | 4 configured, 4 ok, 0 required unavailable |
| Runtime degraded | inactive |
| Inbox | 1 item (Microsoft invoice warning — legitimate follow-up) |

Connector notes:

- Cloudflare tunnel reports **soft cutover**: public health is Axon-X control-plane, while remote ingress still points at `http://localhost:7734`. Status remains `ok` by design; not escalated as a required connector failure.
- Optional `axon_local` on `:7734` is reachable.

## Prior shift (completed)

**Signal quality fix:** promotional / contest email was landing in Attention as **high** urgency because triage treated marketing “deadline” language like an operational incident.

- `services/axon-watch/app/signals/email_triage.py` — promo downrank, modal `may` vs month `May`
- Receipt: `python3 -m unittest tests.test_email_signal -v` → 9 passed; live inbox dropped from 3 items to 1

## Prior shift (completed)

**Connector probe cache CI gap:** TTL cache shipped in `services/axon-watch/app/connectors/summary.py` with unit tests in `tests/test_connector_probe_cache.py`, but the contract runner and TEST-3 gate did not execute those tests.

- `scripts/verify/run_contract_unit_tests.sh` — run `tests.test_connector_probe_cache`
- `scripts/verify/test3-watch-connectors.sh` — include probe-cache module in step `[2/5]`
- Receipt: `python3 -m unittest tests.test_connector_probe_cache -v` → **5 passed**

## Highest-value action this shift

**Watch test isolation bug:** `tests/test_dashpro_monitor_cache.py` cleared all `app.*` modules at import time. When pytest loaded email signal tests first and dashpro monitor tests second, email inbox mocks stopped applying — `email_account_id` / `email_account_address` meta came back empty and two signal tests failed intermittently.

### Change

- `tests/test_dashpro_monitor_cache.py` — match connector probe cache pattern: isolate `app` imports in `setUp`/`tearDown` instead of module-level `sys.modules` wipe

### Receipts

- `python3 -m pytest tests/test_connector_probe_cache.py tests/test_email_signal.py tests/test_dashpro_monitor_cache.py -q` → **19 passed** (3 consecutive runs)
- `PYTHONPATH=services/axon-watch python3 -m unittest tests.test_email_signal tests.test_connector_probe_cache tests.test_dashpro_monitor_cache -v` → **20 passed**
- `./scripts/dev/check-health.sh` → console, control-plane, watch, runtime summary, inbox all ok
- Live runtime: 4 connectors ok, `required_unavailable: 0`, degraded inactive

## Watch items (not acted this shift)

- Soft tunnel cutover still points Cloudflare ingress at legacy `:7734` — ownership sits with integrations for a hard cutover; Night Watch continues to observe.
- Microsoft invoice email remains a legitimate follow-up signal, left open.
