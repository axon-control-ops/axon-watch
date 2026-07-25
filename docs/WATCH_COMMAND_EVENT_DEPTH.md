# Watch Command / Event / Status Depth

## Purpose

The watch service needs richer **command**, **event**, and **summary observation**
behavior for ongoing operator observation — not just passive connector probes.

This slice adds bounded watch commands, an observation event log, summary
`observation` metadata, and control-plane proxy routes.

## Watch commands

`POST /internal/watch/commands`

Supported `command_type` values (v1):

| Type | Target | Action |
|---|---|---|
| `reprobe_connector` | `target_id` = connector id | Re-run HTTP probe for one connector |
| `refresh_summary` | none | Rebuild watch summary snapshot (clears connector + monitor probe caches) |

Request shape matches frozen planning (`command_id`, `command_type`, `target_type`,
`target_id`, `requested_by`, `payload`, `requested_at`).

Response (`WatchCommandReceipt`):

```json
{
  "accepted": true,
  "command_id": "cmd-…",
  "status": "completed",
  "receipt": {
    "command_type": "reprobe_connector",
    "result": { "connector_status": "ok", "latency_ms": 12 },
    "completed_at": "…"
  }
}
```

`GET /internal/watch/commands/{command_id}` returns full command record + receipt.

Unknown command types → HTTP 400. Unknown connector on reprobe → `status: failed`
with error receipt (HTTP 200, `accepted: false`).

## Watch events

`GET /internal/watch/events?limit=20&cursor=…`

Returns newest-first observation events:

- `command_accepted`
- `connector_reprobed` / `summary_refreshed`
- `command_completed` / `command_failed`

`GET /internal/watch/events/stream` — SSE stream emitting `watch_event` payloads
when new events arrive (2s poll loop in v1).

## Summary observation depth

`GET /internal/watch/summary` now includes:

```json
"observation": {
  "events_count": 4,
  "last_event_at": "…",
  "last_event_type": "command_completed",
  "last_command_id": "cmd-…",
  "last_command_status": "completed",
  "last_command_at": "…"
}
```

## Control-plane proxy

| Route | Proxies |
|---|---|
| `POST /api/watch/commands` | watch command submission |
| `GET /api/watch/commands/{command_id}` | command status |
| `GET /api/watch/events` | observation event log |

## Implementation modules

- `services/axon-watch/app/commands/` — store, executor, service
- `services/axon-watch/app/events/` — store, SSE stream
- `services/axon-watch/app/watch_summary.py` — `observation` block
- `services/control-plane/app/adapters/watch_client.py` — HTTP client helpers

Shared DTOs: `packages/shared-types/src/watch.ts`

## Verification

```bash
python3 -m unittest tests.test_watch_commands_events tests.test_control_plane_watch_commands -v
PYTHONPATH=services/axon-watch python3 -m unittest \
  tests.test_connector_probe_cache.ConnectorProbeCacheTests.test_execute_reprobe_connector_seeds_cold_cache \
  tests.test_connector_probe_cache.ConnectorProbeCacheTests.test_execute_reprobe_tunnel_seeds_cold_cache \
  tests.test_connector_probe_cache.ConnectorProbeCacheTests.test_execute_reprobe_connector_updates_warm_cache \
  tests.test_connector_probe_cache.ConnectorProbeCacheTests.test_execute_reprobe_tunnel_updates_warm_cache \
  tests.test_connector_probe_cache.ConnectorProbeCacheTests.test_execute_refresh_summary_clears_connector_cache \
  tests.test_dashpro_monitor_cache.DashProMonitorCacheTests.test_execute_refresh_summary_clears_monitor_cache \
  -v
./scripts/verify/test4-watch-command-event-depth.sh
npm run verify:test4
```

Live proof:

1. `POST /api/watch/commands` reprobe `control_plane` → `status: completed`
2. `GET /api/watch/events` lists `connector_reprobed` / `command_completed`
3. `GET /internal/watch/summary` → `observation.last_command_status`

Restart **watch** and **control-plane** after route changes. TEST-4 restarts both
when the dev stack is already running.

## Cutover status

Locked cutover item **Watch command / event / status depth** — verified by TEST-4.

Next locked item: **Delivery receipts for operator attention**.

## Polish backlog

See `docs/internal/AGENT-POLISH-NOTES.md` → Watch command/event depth section.
