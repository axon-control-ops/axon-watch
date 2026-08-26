# Legacy Connector Inventory

**Purpose:** Track former `axon-local` dependencies and confirm they are not active fallbacks.
Axon-X production operator is `:4173`; this repo no longer starts, proxies, binds,
or links an `axon-local` runtime.

**Last updated:** 2026-08-25 (axon-local runtime retired)

**Machine-readable source:** `config/legacy-connector-inventory.json`  
**Gate:** `npm run verify:connector-inventory` (`scripts/verify/test21-connector-inventory.sh`)

---

## G4.1 Inventory (Owner · Probe · Removal Criteria)

| ID | Status | Owner | Probe | Phase G | Fallback removal criteria |
|---|---|---|---|---|---|
| `control_plane` | **migrated** | `services/control-plane` | HTTP `${AXON_WATCH_CONTROL_PLANE_BASE_URL}/api/health` · `verify:test3` | — | Native on Axon-X; axon-local not required. |
| `console_web` | **migrated** | `apps/console-web` | HTTP `${AXON_WATCH_CONSOLE_WEB_BASE_URL}/` · `verify:test3` | — | Primary operator is `:4173`; no axon-local UI fallback. |
| `public_ingress` | **migrated** | `services/axon-watch/app/tunnel` | HTTP `${AXON_WATCH_PUBLIC_BASE_URL}/api/health` · optional | — | Cloudflare/public only; not required for local ONLINE. |
| `agent_orchestration` | **replaced** | `cli_runtime` + run store | `verify:agent-orchestration-parity` | G3 | No `:7734` needed for agent file edits. |
| `whatsapp_web_monitor` | **replaced/deferred** | future Axon-X WhatsApp slice | manual | G4.2 | No active runtime dependency remains; revisit later as an Axon-X feature. |
| `cloudflare_tunnel` | **migrated** | `services/axon-watch/app/tunnel` | `verify:tunnel-remote-control` · connectors rail | — | Native Axon-X start/stop/status; no axon-local script or proxy. |
| `voice_deck_mobile_cockpit` | **partial** | `console-web/features/voice-deck` | `verify:voice-cockpit` | G4.4 | Event-driven presence on Axon-X; no axon-local fallback. |
| `agent_dock_legacy_parity` | **partial** | `RightDock` + `AgentDock` | `verify:agent-dock-parity` · `dock-behavior-contract.json` | G4.5 | Accepted Axon-X v1 degradation; no axon-local fallback. |
| `dashpro_external_monitors` | **partial** | `axon-watch/app/monitors` | `verify:dashpro-monitors` · `dashpro-monitor-slice.json` | G4.2 | Sentry/PostHog on watch; WhatsApp deferred separately. |
| `legacy_settings_storage` | **replaced** | Axon-X settings owners or documented discards | manual | G5 | Add Axon-X ownership for reopened settings instead of reading axon-local stores. |

---

## Health-Probe Connectors

Configured in `config/watch-connectors.json` and surfaced on Mission Control → **Connectors**.

| Connector ID | Required | Axon-X UI |
|---|---|---|
| `control_plane` | yes | Connectors rail |
| `console_web` | yes | Connectors rail |
| `public_ingress` | no | Connectors rail (Cloudflare/public) |
| `github_api` | no | Connectors rail |
| `edudashpro_site` | no | Connectors rail |
| `cloudflare_tunnel` | no | Connectors rail, native start/stop |

See `docs/WATCH_CONNECTORS.md`.

---

## Operator Rule

When an operator hits a missing capability, keep the work inside Axon-X:

1. File a native Axon-X feature or explicit discard.
2. Do not open, start, or proxy `axon-local` from this repo.
3. Treat WhatsApp as future work unless the operator reopens it.

---

## Related Docs

- `docs/PRODUCTION_OPERATOR_SURFACE.md`
- `docs/CUTOVER_DECISION.md`
- `config/parity-snapshot.json`
- `docs/WATCH_CONNECTORS.md`
