# Legacy Connector Inventory (axon-local :7734)

**Purpose:** Track unmigrated capabilities that still require axon-local fallback.
Axon-X production operator is `:4173`; axon-local remains explicit fallback only.

**Last updated:** 2026-07-07 (Phase G4.1 inventory gate)

**Machine-readable source:** `config/legacy-connector-inventory.json`  
**Gate:** `npm run verify:connector-inventory` (`scripts/verify/test21-connector-inventory.sh`)

---

## G4.1 inventory (owner · probe · removal criteria)

| ID | Status | Owner | Probe | Phase G | Fallback removal criteria |
|---|---|---|---|---|---|
| `control_plane` | **migrated** | `services/control-plane` | HTTP `${AXON_WATCH_CONTROL_PLANE_BASE_URL}/api/health` · `verify:test3` | — | Native on Axon-X; axon-local not required. |
| `console_web` | **migrated** | `apps/console-web` | HTTP `${AXON_WATCH_PUBLIC_BASE_URL}/` · `verify:test3` | — | Primary operator is `:4173`. |
| `axon_local` | **optional fallback** | axon-local `:7734` | HTTP `http://127.0.0.1:7734/api/health` (optional) · `verify:test3` | G6 | Remove rail + probe after G4.2–G4.5 replaced/discarded, G5 matrix green, G6 one-week `:4173`-only sign-off. |
| `agent_orchestration` | **replaced** | `cli_runtime` + run store | `verify:agent-orchestration-parity` | G3 | Blocker cleared when orchestration gate stays green; no `:7734` needed for agent file edits. |
| `whatsapp_web_monitor` | **unmigrated** | axon-local `whatsapp_web_monitor.py` | Manual (scheduler job on `:7734`) | G4.2 | Bounded watch slice + vault auth + inbox signals, or explicit operator discard (G5.4). |
| `cloudflare_tunnel` | **partial** | `services/axon-watch/app/tunnel` | `verify:tunnel-remote-control` · connectors rail | G4.3 | Native start/stop/status is implemented without axon-local. Operator cutover still requires Axon-X auth and retirement of the currently unmanaged process. |
| `voice_deck_mobile_cockpit` | **partial** | `console-web/features/voice-deck` | `verify:voice-cockpit` | G4.4 | Event-driven presence on Axon-X; foreground-only mobile strip; no background listening. |
| `agent_dock_legacy_parity` | **partial** | `RightDock` + `AgentDock` | `verify:agent-dock-parity` · `dock-behavior-contract.json` | G4.5 | Hero mode persistence, collapsible operator thread seam, IDE transcript meta; thread-deck richness still reduced vs axon-local. |
| `dashpro_external_monitors` | **partial** | `axon-watch/app/monitors` | `verify:dashpro-monitors` · `dashpro-monitor-slice.json` | G4.2 | Sentry/PostHog on watch; WhatsApp/tunnel remain separate rows. |
| `legacy_settings_storage` | **unmigrated** | axon-local settings/SQLite | Manual (G5.1 capability matrix) | G5 | Every operator-needed key has Axon-X owner or documented discard; no silent truth merge. |

---

## Health-probe connectors (watch)

Configured in `config/watch-connectors.json` and surfaced on Mission Control → **Connectors**.

| Connector ID | Required | Axon-X UI |
|---|---|---|
| `control_plane` | yes | Connectors rail |
| `console_web` | yes | Connectors rail |
| `axon_local` | no | Connectors rail + **Open :7734 fallback** |

See `docs/WATCH_CONNECTORS.md`.

---

## Child-project workspace (partial migration)

| Workspace | Axon-X binding | axon-local equivalent |
|---|---|---|
| `workspace_dashpro` | `/home/edp/Projectx/product/dashpro` | DashPro office workspace (id 5) |

Files, terminal, and bounded commands (`git status`, agent Full Access) work in Axon-X for DashPro.
DashPro-specific integrations (WhatsApp monitor, tunnel, mobile app flows) remain on axon-local until G4.2–G4.4.

See `docs/CHILD_PROJECT_WORKSPACE.md`.

---

## Replaced on Axon-X (Phase G G3)

1. **Full agent ReAct loop** — **replaced** by control-plane runtime fabric + persisted run truth (`npm run verify:agent-orchestration-parity`). ReAct may still appear inside a Cursor agent turn; `brain.py` is not ported.

---

## Retirement blocker map

`config/parity-snapshot.json` → `blockers_for_full_retirement`:

> Child-project integration and legacy connector surfaces not yet migrated to Axon-X

Mapped inventory IDs: `whatsapp_web_monitor`, `cloudflare_tunnel`, `voice_deck_mobile_cockpit`, `agent_dock_legacy_parity`, `legacy_settings_storage`, `axon_local`.

---

## Operator handoff rule

When an operator hits an unmigrated path:

1. Use Mission Control → **Connectors** → **Open :7734 fallback** for `axon_local`.
2. Do **not** assume Axon-X and axon-local share the same run store or chat history.
3. Record blockers in planning docs; do not mark full retirement until G6 sign-off.

---

## Related docs

- `docs/PRODUCTION_OPERATOR_SURFACE.md`
- `docs/CUTOVER_DECISION.md`
- `config/parity-snapshot.json` → `blockers_for_full_retirement`
- `docs/WATCH_CONNECTORS.md`
- `docs/PHASE_G_SIGNAL_PARITY.md` → G4.1 / G4.6
