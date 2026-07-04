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

## Remote setup (first time)

This repo ships without a configured `origin`. Suggested layout alongside
`axon-local` (`github.com/axon-control-ops/axon`):

```bash
cd /home/edp/axon-nvme/repos/axon-watch
git remote add origin git@github.com:axon-control-ops/axon-watch.git
git push -u origin master
git push -u origin dev
```

Use HTTPS if SSH keys are not configured:

```bash
git remote add origin https://github.com/axon-control-ops/axon-watch.git
```

Create the empty GitHub repository first, then push both branches.

## Planning doc relationship

Frozen planning lives in `axon-local/Plans/Axon-Watch/`. Implementation authority
for layout and ADRs lives in this repo under `docs/`. Update both when a slice
changes contracts or locked geometry.

## Verification gate (required before push)

```bash
npm run verify
python3 -m unittest discover -s tests
```

Optional manual smoke: `http://127.0.0.1:4173`, workspace `workspace_smoke`, terminal
trash + one command + Up-arrow history check.
