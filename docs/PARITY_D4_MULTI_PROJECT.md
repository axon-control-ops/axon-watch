# P-D4 — Multi-Project / Second Bound Workspace

## Deliverable

Prove continuous development across two bound project workspaces (axon-watch +
axon-local) with cross-bound handoff summaries.

## v1 scope

### In scope

- Default bindings include `workspace_axon_watch` and `workspace_axon_local`
- Control-plane handoff from watch → local returns `project_path` summary
- Optional live acceptance: `git status` in both bound repos when dev stack is up
- Contract checker: `scripts/verify/check_multi_project_bindings.py`

### Acceptable v1 degradation

- Live git-status proof skipped when dev stack or sibling axon-local repo absent
- Handoff + bindings proof runs in default verify gate without live stack

### Out of scope

- Third child-project workspace beyond the two default bindings

## Gate

```bash
npm run verify:parity-d4
```

## Promotion

On gate pass, update `config/parity-closure-order.json` → `P-D4.status = done`,
`next_slice = P-D5`.
