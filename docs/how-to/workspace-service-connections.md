# Workspace service connections (DashPro / Supabase bridge)

Fleet agents run in sandboxes that **hide `.env`** and default to **no network**.
Humans operating Young Eagles or DashPro run live checks from a bound project
root with credentials on disk. **Workspace service connections** close that gap
without committing secrets to git or logging them in run receipts.

## Three layers

| Layer | File | Purpose |
| --- | --- | --- |
| Project binding | `config/workspace-project-bindings.json` | Maps `workspace_young_eagles_day_care` → on-disk repo root |
| Service connection | `config/workspace-service-connections.json` | Whitelisted env keys + approved live verify commands |
| Operator materialization | `<project_root>/.env` (gitignored) | Same keys a human uses for `npm run check-supabase` |

Vault may **fill gaps** when the operator `.env` is incomplete and `/vault` is
unlocked (e.g. shared `SUPABASE_URL`).

## What the control plane does

1. **Policy widen** — For configured workspaces, backend / integrations / watcher
   (and Young Eagles lead) receive extra approved prefixes such as
   `npm run check-supabase`, and `network_mode` upgrades from `none` → `audited`
   when live verify commands exist.
2. **Env bridge** — At agent dispatch, whitelisted keys are merged into
   subprocess env and passed into Bubblewrap via `--setenv` so scripts work even
   when `.env` is overlay-hidden in the sandbox.
3. **Posture API** — `GET /api/workspaces/{id}/service-connection` returns
   readiness (keys resolved: yes/no) **without secret values**.

## Young Eagles example

Binding root:

```text
/run/media/vaxon/axon-data/projectx/client/young-eagles-day-care
```

Operator check (human or fleet after bridge):

```bash
npm run check-supabase
```

Approved fleet wrapper (from bound root context):

```bash
workspace-live-verify check-supabase
```

Expected receipt path after a live count:

```text
data/exports/enrolment-headcount-receipt.json
```

## Adding a new tenant workspace

1. Add `workspace-project-bindings.json` entry → client ops repo root.
2. Add `workspace-service-connections.json` profile:
   - `env_keys` — only keys the workspace scripts read
   - `live_verify_command_prefixes` — exact npm/script prefixes
   - `dashpro_tenant_id` — when using shared DashPro Supabase
3. Copy `.env.example` → `.env` on the operator machine; never commit.
4. Confirm posture: `curl -fsS http://127.0.0.1:8787/api/workspaces/<id>/service-connection | jq .ready`
5. Restart control plane after changing connection config.

## Security notes

- Forbidden path globs still block agents from **reading** `.env` in the sandbox.
- Bridge injection is **whitelist-only** per workspace profile.
- Database migrations and deploys still require explicit operator approval.
- Do not store service-role keys in chat, receipts, or git.

## Related

- Young Eagles handoff: `young-eagles-day-care/docs/ops/sol-electron-desktop-install-handoff.md`
- Vault consumers: `/vault` snapshot → **Young Eagles DashPro tenant bridge**
