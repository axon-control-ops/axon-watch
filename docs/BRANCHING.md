# Branching And Remote Workflow

## Branches

| Branch | Purpose |
|---|---|
| `master` | Last known-good bootstrap baseline. Merge from `dev` only after `npm run verify` and manual smoke on `workspace_smoke`. |
| `dev` | Day-to-day integration branch for Lane B/C/D slices. All feature work lands here first. |

## Daily workflow

```bash
git checkout dev
git pull origin dev   # after remote is configured
# … edit …
npm run verify
./scripts/dev/down.sh && AXON_NO_OPEN=1 ./scripts/dev/up.sh
./scripts/dev/check-health.sh
git add …
git commit -m "…"
git push origin dev
```

When a slice set is stable, open a PR `dev` → `master` or fast-forward merge locally
after verification.

## Remote

`origin` is configured for **https://github.com/axon-control-ops/axon-watch**
(private). Day-to-day pushes use `dev`; merge to `master` after verification.

First-time clone on a new machine:

```bash
git clone git@github.com:axon-control-ops/axon-watch.git
cd axon-watch
git checkout dev
```

If you need to add `origin` on a copy that has no remote yet:

```bash
git remote add origin git@github.com:axon-control-ops/axon-watch.git
git push -u origin master
git push -u origin dev
```

## Planning doc relationship

Canonical planning lives in **`docs/planning/`** in this repo. A continuity
mirror remains in `axon-local/Plans/Axon-Watch/` (sync via
`scripts/ops/sync_planning_mirror_to_axon_local.py`). Locked layout and
implementation ADRs live under `docs/`. See
`docs/CROSS_REPO_PLANNING_MIGRATION.md`.

## Verification gate (required before push)

```bash
npm run verify
python3 -m unittest discover -s tests
```

Optional manual smoke: `http://127.0.0.1:4173`, workspace `workspace_smoke`, terminal
trash + one command + Up-arrow history check.
