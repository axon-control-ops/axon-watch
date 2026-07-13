# Axon-X

**Axon-X** is the next-generation Axon product UI and control stack.

The implementation repo folder is still `axon-watch` for now; that is an internal
path/name, not the product name shown to operators.

`axon-watch` is a new integrated local-first operator and coding environment.
This working tree currently combines:

- a shared contract baseline under `packages/shared-types/`
- a real control-plane thin slice with persisted runs, approvals, review-ready,
  runtime summary, and operator briefing
- a watch service with canonical signal production (bootstrap, connector, and
  monitor inbox items), delivery receipts, and multi-factor ranking
- a Vue shell that consumes runs, inbox, runtime summary, briefing, and
  workspace files through dedicated `TopBar`, `LeftSidebar`,
  `CenterWorkbench`, `RightDock`, and `StatusBar` regions, plus Monaco and
  xterm host surfaces, nested file explorer, new-file creation, and active-file rename
- verification and governance scaffolding under `scripts/verify/`, `docs/adr/`,
  and `tests/`

## Source Of Truth

- `PRODUCT.md` defines the product thesis and non-goals.
- `ARCHITECTURE.md` defines service ownership and deployment boundaries.
- `docs/planning/UI_SPEC.md`, `docs/planning/UI_COMPOSITION_SPEC.md`, and
  `docs/planning/UI_VISUAL_DIRECTION.md` define presentation rules inside the
  locked regions
- **`docs/UI_LAYOUT_LOCK.md`** and **`docs/adr/ADR-004-locked-console-shell-layout.md`**
  lock the current five-region shell geometry (authoritative for implementation).
- the frozen planning bundle in **`docs/planning/`** is the canonical
  planning source (migrated from `axon-local/Plans/Axon-Watch/` on 2026-07-05)

## Repo Shape

```text
apps/console-web/        Vue shell, control-plane clients, Monaco/xterm hosts
services/control-plane/  FastAPI run-state, approvals, briefing, summary
services/axon-watch/     FastAPI watch inbox with canonical signal producers
packages/                shared contract package ownership
docs/                    contract and ADR guidance
scripts/                 dev/ops bootstrap plus existing verify helpers
infra/                   deployment skeleton placeholders
tests/                   existing verification harness ownership
```

## Local Bootstrap

Use npm workspaces from the repo root:

1. run `npm install` at the repo root
2. install Python dependencies for the service shells if needed
3. copy `.env.example` to `.env` if custom ports or paths are needed
4. run `./scripts/dev/up.sh`
5. wait for `up.sh` to confirm all three services are ready
6. check service endpoints with `./scripts/dev/check-health.sh`
7. stop local processes with `./scripts/dev/down.sh`

Startup contract:

- ports are fixed at `4173`, `8787`, and `8788` unless overridden in `.env`
- startup fails fast if any configured port is already in use
- `up.sh` rolls the stack back if a service never becomes ready
- `down.sh` is safe to re-run and cleans stale pid files plus orphan listeners on the configured ports

Bootstrap URLs:

- console web: `http://127.0.0.1:4173`
- control plane health: `http://127.0.0.1:8787/api/health`
- watch health: `http://127.0.0.1:8788/internal/watch/health`
- runtime summary: `http://127.0.0.1:8787/api/runtime/summary`
- inbox: `http://127.0.0.1:8787/api/inbox`
- briefing: `http://127.0.0.1:8787/api/briefing` (loaded by shell; see `docs/contracts/BRIEFING-SEAM.md`)
- runs: `http://127.0.0.1:8787/api/runs`
- workspaces: `http://127.0.0.1:8787/api/workspaces`

## Verification

Reproducible verification from the repo root:

```bash
npm install
npm run verify:shared-types
npm run verify:contracts
npm run verify:console-web
npm run verify
python3 -m unittest discover -s tests
./scripts/dev/down.sh
./scripts/dev/up.sh
./scripts/dev/check-health.sh
```

Existing verification entrypoints remain in place:

```bash
python3 -m unittest discover -s tests
python3 scripts/verify/all.py
```

See `scripts/verify/README.md` for the verification contract.

## Branching And Remote

Day-to-day work happens on branch **`dev`**. **`master`** holds the last
known-good bootstrap baseline.

- Branch workflow: `docs/BRANCHING.md`
- Remote `origin` points at **https://github.com/axon-control-ops/axon-watch**
  (see `docs/BRANCHING.md`)

Frozen planning lives in **`docs/planning/`**. Locked layout and
implementation ADRs live in this repo under `docs/`. See
`docs/CROSS_REPO_PLANNING_MIGRATION.md` for the axon-local continuity mirror.
