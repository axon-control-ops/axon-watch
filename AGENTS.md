# AGENTS.md

## Cursor Cloud specific instructions

Axon-X (`axon-watch`) is an npm-workspaces monorepo with one Vue frontend and two
FastAPI Python services. Standard commands live in `README.md` and root
`package.json` scripts; the notes below only cover non-obvious caveats.

### Services

| Service | Path | Port | Run (dev) |
| --- | --- | --- | --- |
| console-web (Vue/Vite) | `apps/console-web` | 4173 | `npm run dev:console-web` |
| control-plane (FastAPI) | `services/control-plane` | 8787 | `npm run dev:control-plane` |
| axon-watch (FastAPI) | `services/axon-watch` | 8788 | `npm run dev:axon-watch` |

Run the whole stack with `./scripts/dev/up.sh` (aka `npm run dev`), check it with
`./scripts/dev/check-health.sh`, and stop it with `./scripts/dev/down.sh`.

### Non-obvious caveats

- `up.sh` **fails fast if any of ports 4173/8787/8788 is already in use** and
  rolls the whole stack back if any service does not become ready. If startup
  fails with a port-in-use error, run `./scripts/dev/down.sh` first (it is safe
  to re-run and also cleans stale pid files under `.local/pids`).
- The Python services are launched as `python3 -m uvicorn ...`, so they use the
  interpreter's `site-packages`; no virtualenv activation is required. Deps are
  installed to `~/.local` by the update script.
- The FastAPI `TestClient` used by the Python tests requires `httpx`. Starlette
  prints a `StarletteDeprecationWarning` suggesting `httpx2`; this is harmless
  and the tests pass with `httpx`.
- A `.env` file is optional: `scripts/dev/lib/common.sh` falls back to
  `.env.example` when `.env` is absent. `.env`, `node_modules/`, and `.local/`
  are gitignored.
- Logs for the background stack are written to `.local/logs/<service>.log`.

### Lint / test / build

- Python tests: `python3 -m unittest discover -s tests`
- Full pipeline (contracts + frontend typecheck/test/build + verify scaffold):
  `npm run verify`. The verify scaffold prints `PENDING` for future slices; that
  is expected and does not fail the run (only `FAIL` does).
- Frontend only: `npm run verify:console-web` (vue-tsc typecheck, vitest, build).
