# Watch Connectors

## Purpose

Axon-X needs **real connector/runtime awareness**, not only local shell behavior.
This slice adds configured HTTP health probes in the watch service, surfaces them
through watch summary/connectors routes, projects counts into runtime summary, and
raises inbox signals when **required** connectors fail.

Optional connectors (for example legacy `axon-local` on `:7734`) appear in probe
results but do not block runtime degradation unless marked `required: true`.

## Configuration

Default connectors file:

`config/watch-connectors.json`

Override path:

`AXON_WATCH_CONNECTORS_FILE`

Example entry:

```json
{
  "connectors": {
    "control_plane": {
      "display_name": "Control plane",
      "health_url": "${AXON_WATCH_CONTROL_PLANE_BASE_URL}/api/health",
      "required": true,
      "workspace_id": "workspace_axon_watch"
    }
  }
}
```

`health_url` values expand environment variables via `os.path.expandvars`.

Default connectors:

| ID | Target | Required |
|---|---|---|
| `control_plane` | `${AXON_WATCH_CONTROL_PLANE_BASE_URL}/api/health` | yes |
| `console_web` | `${AXON_WATCH_PUBLIC_BASE_URL}/` | yes |
| `axon_local` | `http://127.0.0.1:7734/api/health` | no |

## Watch service routes

| Route | Purpose |
|---|---|
| `GET /internal/watch/connectors` | Full probe records + aggregate summary |
| `GET /internal/watch/summary` | Watch summary DTO including connector counts |
| `GET /internal/watch/inbox` | Inbox now includes connector signals for failed **required** probes |

## Control-plane routes

| Route | Purpose |
|---|---|
| `GET /api/connectors` | Proxies watch connector snapshot for operator tooling |
| `GET /api/runtime/summary` | Adds `connectors` block with aggregate counts |

Runtime summary marks `degraded.active` when `required_unavailable > 0`.

## Probe caching

Watch connector probes use a short in-process TTL cache (default **15 seconds**) so
summary, connectors, and inbox reads do not re-hit every health URL on each request.

- Override: `AXON_WATCH_CONNECTOR_CACHE_TTL_SECONDS` (set `0` to disable)
- `refresh_summary` clears the cache so the next summary rebuild probes live
- `reprobe_connector` upserts the live result into the TTL cache (seeds a full snapshot first when cold)

## Signal behavior

- Source: `connector`
- Emitted only for **required** connectors with status `degraded` or `unavailable`
- Optional connector failures remain visible in `/api/connectors` only (v1)

## Verification

```bash
python3 -m unittest tests.test_watch_connectors tests.test_control_plane_connectors -v
PYTHONPATH=services/axon-watch python3 -m unittest \
  tests.test_connector_probe_cache \
  tests.test_connector_signal \
  tests.test_connector_inbox_integration \
  tests.test_actionable_inbox_signals \
  tests.test_watch_inbox_assembly \
  -v
python3 -m unittest \
  tests.test_parity_a4_signal_inbox_consistency \
  tests.test_signal_consistency \
  -v
PYTHONPATH=services/axon-watch python3 -m unittest \
  tests.test_connector_probe_cache.ConnectorProbeCacheTests.test_execute_reprobe_connector_seeds_cold_cache \
  tests.test_connector_probe_cache.ConnectorProbeCacheTests.test_execute_reprobe_tunnel_seeds_cold_cache \
  tests.test_connector_probe_cache.ConnectorProbeCacheTests.test_execute_reprobe_connector_updates_warm_cache \
  tests.test_connector_probe_cache.ConnectorProbeCacheTests.test_execute_reprobe_tunnel_updates_warm_cache \
  -v
./scripts/verify/test3-watch-connectors.sh
npm run verify:test3
```

Live proof (stack up):

1. `GET /internal/watch/connectors` — `control_plane` and `console_web` status `ok`
2. `GET /api/runtime/summary` — `connectors.ok >= 2`, `required_unavailable == 0`
3. `GET /api/connectors` — same probe records via control-plane proxy

Restart **watch** and **control-plane** after connector code or config changes.
TEST-3 restarts both when the dev stack is already running.

## Cutover status

Locked cutover item **Watch connectors** — verified by TEST-3.

Next locked item: **Delivery receipts for operator attention**.

## Polish backlog

See `docs/internal/AGENT-POLISH-NOTES.md` → Watch connectors section.
