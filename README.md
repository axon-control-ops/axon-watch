# Axon-Watch

`axon-watch` is a new integrated local-first operator and coding environment.
This working tree currently combines:

- Lane 1 bootstrap scaffolding for the new repo layout and service shells
- a first real shared contract baseline under `packages/shared-types/`
- existing verification and governance scaffolding under `scripts/verify/`,
  `docs/adr/`, and `tests/`

## Source Of Truth

- `PRODUCT.md` defines the product thesis and non-goals.
- `ARCHITECTURE.md` defines service ownership and deployment boundaries.
- the frozen planning bundle in `axon-local/Plans/Axon-Watch/` remains the
  planning-locked source until later migration slices complete

## Repo Shape

```text
apps/console-web/        existing UI shell worktree
services/control-plane/  FastAPI health/readiness bootstrap stub
services/axon-watch/     FastAPI health/readiness bootstrap stub
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
5. check service endpoints with `./scripts/dev/check-health.sh`
6. stop local processes with `./scripts/dev/down.sh`

Bootstrap URLs:

- console web: `http://127.0.0.1:4173`
- control plane health: `http://127.0.0.1:8787/api/health`
- watch health: `http://127.0.0.1:8788/internal/watch/health`

## Verification

Reproducible verification from the repo root:

```bash
npm install
npm run verify:shared-types
npm run verify:contracts
npm run verify
python3 -m unittest discover -s tests
```

Existing verification entrypoints remain in place:

```bash
python3 -m unittest discover -s tests
python3 scripts/verify/all.py
```

See `scripts/verify/README.md` for the verification contract.

## Boundary Note

Service implementations remain bootstrap-thin, but contract ownership now
exists in `packages/shared-types/` and `docs/contracts/`.
