# Workspace Project Connection

## Purpose

Axon-X workspaces are normally thin identifiers backed by isolated directories
under `.local/workspaces/{workspace_id}`. Continuous development against real
repos requires a verified bridge from those workspace identifiers to existing
project roots on disk (for example DashPro or other sibling project repos).

This slice adds that bridge without changing isolated workspace behavior for
unbound identifiers.

## Configuration

Default bindings file:

`config/workspace-project-bindings.json`

Override path:

`AXON_WATCH_WORKSPACE_BINDINGS_FILE`

Example shape:

```json
{
  "bindings": {
    "workspace_axon_watch": {
      "project_root": ".",
      "display_name": "axon-watch"
    },
    "workspace_dashpro": {
      "project_root": "../dashpro",
      "display_name": "DashPro"
    }
  }
}
```

Relative `project_root` values resolve against the Axon-X repository root.

## Safety

Every bound `project_root` must fall inside
`AXON_WATCH_PROJECT_ROOT_ALLOWLIST`. Default allowlist:

1. Axon-X repository root
2. Parent directory of Axon-X repository root
3. Operator home directory

Colon-separated override example:

```bash
export AXON_WATCH_PROJECT_ROOT_ALLOWLIST="/home/edp/projects:/tmp/axon-dev"
```

Missing bindings file is valid and yields zero bindings.

## Runtime behavior

| Surface | Unbound workspace | Bound workspace |
|---|---|---|
| `/api/workspaces` | `connection_kind: isolated_root` | `connection_kind: project_path`, `project_root`, optional `display_name` |
| Terminal PTY cwd | `.local/workspaces/{id}` (created if needed) | bound `project_root` (must already exist; no mkdir) |
| Monaco file host | isolated root | bound project tree |
| Command executor (`git status`, etc.) | isolated root | bound project tree |

Implementation modules:

- `services/control-plane/app/workspace_project_bindings.py`
- `services/control-plane/app/workspace_catalog.py`
- `services/control-plane/app/terminal/workspace_roots.py`

Shared DTO (`packages/shared-types/src/control-plane.ts`):

```ts
export interface WorkspaceRecord {
  workspace_id: string;
  connection_kind?: 'isolated_root' | 'project_path';
  project_root?: string;
  display_name?: string;
}
```

## Verification

Unit and integration:

```bash
python3 -m unittest tests.test_workspace_project_bindings tests.test_control_plane_workspaces tests.test_control_plane_terminal -v
```

Live acceptance (dev stack required):

```bash
./scripts/verify/test1-workspace-project-connection.sh
npm run verify:test1
```

Live proof checks:

1. `workspace_axon_watch` and `workspace_dashpro` appear in `/api/workspaces`
2. Bound records expose `connection_kind: project_path` and resolved `project_root`
3. `workspace_alpha` remains `connection_kind: isolated_root`
4. `git status` via chat in `workspace_axon_watch` executes against the real repo

Restart control-plane after changing bindings or binding code. The TEST-1 gate
restarts control-plane automatically when the dev stack is already running.

## Cutover status

Locked cutover item **Real project/workspace connection** — verified by TEST-1.

Next locked item: **Watch connectors**.
