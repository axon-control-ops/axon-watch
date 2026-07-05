# Production Operator Surface

**Declared:** 2026-07-05  
**Primary URL:** http://127.0.0.1:4173  
**Fallback URL:** http://127.0.0.1:7734 (axon-local, legacy connectors only)

## Decision

The operator production console is **Axon-X console-web on port 4173**.

Day-to-day operator and IDE work should start here:

```bash
cd ~/axon-nvme/repos/axon-watch
./scripts/dev/up.sh          # start :4173 / :8787 / :8788
./scripts/dev/check-health.sh
```

Open: **http://127.0.0.1:4173**

## What changed

| Before | After |
|---|---|
| axon-local `:7734` = production reference | Axon-X `:4173` = production operator surface |
| Axon-X = primary **development** only | Axon-X = primary **operator** surface |
| Parity blocker: operator sign-off pending | **Resolved** — production declared |

## Fallback (axon-local :7734)

Keep axon-local available for:

- Legacy connector paths not yet bound in Axon-X
- Child-project integration surfaces not migrated
- Capability-scoped rollback per `docs/planning/TRANSITION_ARCHITECTURE.md`

axon-local is **not** the default starting point for operator work anymore.

## How to use it (5 minutes)

### 1. Pick your real workspace

After refresh, the left sidebar shows **axon-watch**, **axon-local**, and **DashPro**
(not the old demo names like `workspace_nlp`). Start with **axon-watch**.

If you still see demo workspaces, hard-refresh the browser (`Ctrl+Shift+R`) to load
the latest console bundle.

### 2. Operator mode (default)

Use this for day-to-day ops:

| Region | What to do |
|---|---|
| **Left → Workspaces** | Select `axon-watch`, `axon-local`, or `DashPro` |
| **Left → Attention** | Signals, approvals, delivery badges |
| **Center** | Mission control — run phase, live feed, **Resume / Complete** |
| **Right → Conversation** | Type **commands** (see below) — not free-form chat yet |
| **Right → KAIRO briefing** | Notice / Advise summary from live API |

### 3. Supported conversation commands

The command seam accepts **exact commands** only. Natural language will fail.

| Command | What it does |
|---|---|
| `git status` | Git status in the bound repo root |
| `health` | Control-plane health probe |
| `check-health` | Shortcut → `run ./scripts/dev/check-health.sh` |
| `verify` | Shortcut → `run npm run verify:production-operator` |
| `run …` | Bounded shell command in workspace root (e.g. `run npm test`) |
| `ls` / `list files` | List workspace files |
| `read README.md` | Read a file |
| `resume from review` | Resume the primary review_ready run |

**Footer → Commands** opens the supported-command list. **Run** submits immediately.

Mission Control includes a **Connectors** rail (`GET /api/connectors`) with **Reprobe**,
**Refresh summary**, and **Open :7734 fallback** for the legacy axon-local connector.

Full guide: `docs/HOW-TO-HANDBOOK.md` → **Quick Start**.

### 4. IDE mode

Top-right **IDE** toggle:

- Monaco editor + terminal on the **real project root** for the selected workspace
- Agent dock on the right with workspace switcher

### 5. Stale runs / "32 runs ready for review"

Dev SQLite may contain old smoke runs. They are harmless but noisy. To clear:

```bash
./scripts/dev/down.sh
rm -f .local/state/control-plane.sqlite3
./scripts/dev/up.sh
```

Or ignore them and focus on the current workspace run in mission control.

## Smoke verification

```bash
npm run verify:production-operator
```

Checks:

1. `./scripts/dev/check-health.sh` — all three services + key APIs
2. TEST-0 live acceptance (`workspace_smoke`)
3. TEST-1 live acceptance (dual-workspace bindings + `git status`)
4. Production config contract (`config/operator-production.json`)

Full regression still available via `npm run verify:phase-d`.

## Stop / switch back

```bash
./scripts/dev/down.sh        # stop Axon-X stack
cd ../axon-local && ./start.sh --no-open   # fallback only if needed
```

## Machine-readable config

`config/operator-production.json`

## References

- `docs/CUTOVER_DECISION.md`
- `docs/BROWSER_ONLY_STARTUP_CONTRACT.md`
- `config/parity-snapshot.json` → `production_operator`
