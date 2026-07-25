# P-D6 — Dock Behavior + Browser Startup

## Deliverable

Promote `dock_behavior` and `desktop_and_browser_startup` to verified with
contract checkers, Vitest dock behavior proof, and explicit browser-only
startup decision.

## v1 scope

### In scope

- `config/dock-behavior-contract.json` + `check_dock_behavior_contract.py`
- `config/browser-startup-contract.json` + `check_browser_startup_contract.py`
- `docs/BROWSER_ONLY_STARTUP_CONTRACT.md` (explicit desktop deferral)
- `apps/console-web/src/lib/agent-dock-behavior.test.ts`
- Snapshot promotion → `partially_verified: 0`

### Acceptable v1 degradation

- Browser-only startup verified; packaged desktop explicitly deferred
- Agent dock uses persisted collapse + viewport-safe width (not full thread parity)

### Out of scope

- Packaged desktop Electron/Tauri artifact
- Full axon-local agent-dock thread visual parity

## Gate

```bash
npm run verify:parity-d6
```

## Promotion

On gate pass, update `config/parity-closure-order.json` → `P-D6.status = done`,
`next_slice = complete`.
