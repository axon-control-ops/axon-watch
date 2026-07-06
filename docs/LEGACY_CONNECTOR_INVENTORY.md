# Legacy Connector Inventory (axon-local :7734)

**Purpose:** Track unmigrated capabilities that still require axon-local fallback.
Axon-X production operator is `:4173`; axon-local remains explicit fallback only.

**Last updated:** 2026-07-05 (Phase E3.1)

---

## Connector façade status

| Connector ID | Health probe | Axon-X UI | Fallback |
|---|---|---|---|
| `control_plane` | Required · `:8787/api/health` | Mission Control connectors rail | — |
| `console_web` | Required · `:4173/` | Mission Control connectors rail | — |
| `axon_local` | Optional · `:7734/api/health` | Connectors rail + **Open :7734 fallback** | http://127.0.0.1:7734 |

## Child-project workspace (partial migration)

| Workspace | Axon-X binding | axon-local equivalent |
|---|---|---|
| `workspace_dashpro` | `/home/edp/Projectx/product/dashpro` | DashPro office workspace (id 5) |

Files, terminal, and bounded commands (`git status`, `run …`) work in Axon-X for DashPro.
DashPro-specific integrations (WhatsApp monitor, production URLs, mobile app flows) remain on axon-local until migrated.

See `docs/CHILD_PROJECT_WORKSPACE.md`.

---

## Unmigrated capability areas (v1)

These remain on axon-local until a bounded Axon-X slice replaces them:

1. **Full agent ReAct loop** — classic brain/orchestration on `:7734`. **Target:** Phase G G3 — runtime fabric + persisted run truth; ReAct only as in-step technique (`ADR-004`). Not a `brain.py` port.
2. **Voice deck / mobile cockpit** — not wired in Axon-X console-web v1.
3. **Child-project connectors** — WhatsApp, external MCP, tunnel-specific flows still rooted in axon-local.
4. **Legacy console chrome** — Agent Dock parity features not yet extracted (see `config/parity-snapshot.json`).
5. **Classic settings / storage paths** — some keys and SQLite paths differ; no silent merge of truths.

---

## Operator handoff rule

When an operator hits an unmigrated path:

1. Use Mission Control → **Connectors** → **Open :7734 fallback** for `axon_local`.
2. Do **not** assume Axon-X and axon-local share the same run store or chat history.
3. Record blockers in planning docs; do not mark full retirement until E6 sign-off.

---

## Related docs

- `docs/PRODUCTION_OPERATOR_SURFACE.md`
- `docs/CUTOVER_DECISION.md`
- `config/parity-snapshot.json` → `blockers_for_full_retirement`
- `docs/WATCH_CONNECTORS.md`
