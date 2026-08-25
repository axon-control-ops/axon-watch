# Child-Project Workspace Binding

**Purpose:** Connect a real operator child project to Axon-X via `workspace_dashpro`.

## Bound project

| Workspace ID | Display name | Project root |
|---|---|---|
| `workspace_dashpro` | DashPro | `/home/edp/Projectx/product/dashpro` |

This matches axon-local's office workspace model (`axon_core/workspace_orchestration_guard.py`).

Configuration: `config/workspace-project-bindings.json`  
Contract: `config/multi-project-bindings-contract.json`

## Operator usage

1. Start stack: `./scripts/dev/up.sh`
2. Hard-refresh `:4173`
3. Left sidebar → **DashPro** workspace
4. Run `git status` or `read package.json` in the Command seam
5. IDE mode opens Monaco + terminal on the DashPro repo root

Handoff proof (contract): `workspace_axon_watch` → `workspace_dashpro`

## Verification

```bash
npm run verify:child-project
./scripts/verify/child-project-workspace.sh
```

Live checks:

- `GET /api/workspaces/workspace_dashpro` → `connection_kind: project_path`
- `POST /api/chat/messages` with `git status` in DashPro workspace
- Handoff from axon-watch → dashpro

## Safety

`project_root` must fall inside `AXON_WATCH_PROJECT_ROOT_ALLOWLIST` (default includes `$HOME`).

## Retirement note

Binding DashPro does **not** automatically add every DashPro-specific integration.
WhatsApp is deferred for a future Axon-X-native revisit. See
`docs/LEGACY_CONNECTOR_INVENTORY.md`.
