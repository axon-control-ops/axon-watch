# Cross-Repo Planning Migration

## Purpose

Eliminates split-brain planning between `axon-local` and `axon-watch` by making
`docs/planning/` the canonical home inside the implementation repo.

## What changed

| Before | After |
|---|---|
| Planning lived only in `axon-local/Plans/Axon-Watch/` | Canonical bundle in `axon-watch/docs/planning/` |
| Cutover docs pointed across repos | Cutover + parity defer to `docs/planning/` |
| No integrity gate | `MANIFEST.json` + validate script |

## Canonical vs mirror

- **Canonical:** `axon-watch/docs/planning/`
- **Continuity mirror:** `axon-local/Plans/Axon-Watch/` (updated via sync script)

Implementation specs that record thin-slice truth (`docs/WORKSPACE_*.md`,
`docs/WATCH_*.md`, `docs/OPERATOR_*.md`, etc.) stay in `docs/` outside the
planning bundle.

## Operations

Validate bundle integrity:

```bash
python3 scripts/ops/planning_bundle_manifest.py validate
```

Regenerate manifest after intentional planning edits:

```bash
python3 scripts/ops/planning_bundle_manifest.py write
```

Push canonical planning to axon-local mirror:

```bash
python3 scripts/ops/sync_planning_mirror_to_axon_local.py
```

## Verification

```bash
npm run verify:test9
# or
./scripts/verify/test9-cross-repo-planning-migration.sh
```

## v1 limits

- Mirror sync is manual (no scheduled job)
- Legacy references to `axon-local/Plans/Axon-Watch/` may remain in older docs
  until a later cleanup pass
- Manifest covers `.md` files only

Next locked item: none — cutover checklist complete. See `docs/CUTOVER_DECISION.md`
for operating rules and remaining blockers.
