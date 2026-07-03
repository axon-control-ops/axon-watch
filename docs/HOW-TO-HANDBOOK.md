# Axon-Watch How-To Handbook

This handbook is the practical guide for working with the new `axon-watch`
implementation.

It is written for operators, reviewers, and developers who need to understand:

- what the new repo is
- how it currently works
- how to start it
- how to verify it
- what is real vs still stubbed
- what to do when something goes wrong

This is intentionally simple to read, but detailed enough to be useful during
active implementation.

## What Axon-Watch Is

`axon-watch` is the new implementation repo for the next Axon product shape.

The target product combines:

- an IDE-style shell
- a control plane
- a dedicated watcher service

The implementation repo is here:

- `/home/edp/axon-nvme/repos/axon-watch`

The frozen planning source-of-truth still lives here:

- `/home/edp/axon-nvme/repos/axon-local/Plans/Axon-Watch/`

Important rule:

- read plans from `axon-local`
- implement in `axon-watch`

Do not casually move back and forth inventing new semantics in both places.

## What State The Repo Is In Right Now

The repo is in an early but real bootstrap state.

What already exists:

- repo scaffold
- `console-web` shell skeleton
- `control-plane` FastAPI bootstrap service
- `axon-watch` FastAPI bootstrap service
- shared contract package
- verification harness
- health and readiness scripts

What is already real:

- root workspace scripts
- service startup/shutdown flow
- `/api/runtime/summary` route in the control plane
- shared contract types under `packages/shared-types/`
- shell consumption of a canonical runtime summary

What is still intentionally thin or deferred:

- full run lifecycle behavior
- full approval behavior
- full signal production and ranking
- deep watch summary logic
- full runtime-summary assembly from live probes
- performance evidence for all budgets

So this repo is not a fake mockup, but it is also not feature-complete.

## Source Of Truth Rules

When you are unsure what something should mean, check the planning bundle.

The most important frozen planning docs are:

- `PRODUCT.md`
- `ARCHITECTURE.md`
- `UI_SPEC.md`
- `run-state.md`
- `runtime-summary.md`
- `signal-events.md`
- `watch-api.md`
- `control-api.md`
- `PARITY_LEDGER.md`
- `FITNESS_FUNCTIONS.md`
- `TRANSITION_ARCHITECTURE.md`
- `CONTRACT_TESTING_SPEC.md`

### Things you must not redefine casually

These are serial-only semantics and should not drift:

- canonical run phases
- runtime summary vocabulary
- signal identity, severity, and status
- approval semantics
- transition seams and rollback rules
- parity acceptance rules

If the plan seems wrong or insufficient:

- do not silently change it
- raise a proposed amendment instead

## Repo Layout

Top-level structure:

```text
axon-watch/
  apps/
    console-web/
  services/
    control-plane/
    axon-watch/
  packages/
    shared-types/
  docs/
  scripts/
    dev/
    verify/
  infra/
  tests/
```

### What each part owns

#### `apps/console-web/`

Owns the integrated shell:

- topbar
- left sidebar
- workbench
- bottom panel
- right dock
- status bar

It should consume canonical contracts, not invent backend truth.

#### `services/control-plane/`

Owns interactive backend responsibilities such as:

- UI-facing health/readiness
- runtime summary assembly
- later run-state, approvals, and workspace orchestration

#### `services/axon-watch/`

Owns watcher responsibilities such as:

- monitoring loops
- watch health/readiness
- later signal production
- later inbox/signal summaries

#### `packages/shared-types/`

Owns canonical shared contract types.

This is one of the most important directories in the repo.

If frontend and backend disagree about what a thing means, the fix should start
here, not in ad hoc local types.

#### `scripts/dev/`

Owns local run helpers:

- start
- stop
- health checks

#### `scripts/verify/`

Owns cheap, repeatable verification:

- dependency direction checks
- DTO size checks
- ADR governance checks
- latency-budget check scaffolding

## The Current Architecture In Plain English

Think of the new app as three cooperating parts:

1. the shell the user sees
2. the control plane that serves user-facing APIs
3. the watcher service that will eventually observe and normalize signals

The current implementation is following a thin-slice path:

- bootstrap the shell and services first
- land canonical contracts early
- add real endpoints against those contracts
- then deepen behavior

This is deliberate.

It avoids:

- giant rewrites
- hidden semantic drift
- UI and backend inventing different meanings

## Quick Start

## 1. Go to the repo

```bash
cd /home/edp/axon-nvme/repos/axon-watch
```

## 2. Install JavaScript dependencies

```bash
npm install
```

This is important because root workspace commands now rely on npm workspaces.

## 3. Review environment defaults

Default values are provided in:

- `.env.example`

If you need custom ports or local paths:

```bash
cp .env.example .env
```

Then edit `.env` as needed.

## 4. Start the local stack

```bash
./scripts/dev/up.sh
```

This starts:

- `console-web`
- `control-plane`
- `axon-watch`

## 5. Check health

```bash
./scripts/dev/check-health.sh
```

Expected endpoints:

- console web: `http://127.0.0.1:4173`
- control plane health: `http://127.0.0.1:8787/api/health`
- watch health: `http://127.0.0.1:8788/internal/watch/health`

## 6. Stop the stack

```bash
./scripts/dev/down.sh
```

## What The Current App Does On Boot

Right now, the shell boots and loads a runtime summary from the control plane.

That flow looks like this:

1. `apps/console-web/src/main.ts` creates the Vue app
2. the shell store initializes
3. `loadRuntimeSummary()` is called
4. the frontend fetches `/api/runtime/summary`
5. the control plane returns a canonical runtime summary payload
6. the shell renders runtime identity, active run count, signal count, and degraded state

Important limitation:

- this is currently a thin bootstrap runtime summary
- it is not yet a full live assembler from all real subsystems

That is okay for this stage.

## The Most Important Files Right Now

If you need to understand the current implementation quickly, read these first:

### Shared contracts

- `packages/shared-types/src/index.ts`
- `packages/shared-types/src/run.ts`
- `packages/shared-types/src/runtime.ts`
- `packages/shared-types/src/signals.ts`
- `packages/shared-types/src/control-plane.ts`
- `packages/shared-types/src/watch.ts`

### Fixture payloads

- `packages/shared-types/fixtures/runtime-summary.example.json`
- `packages/shared-types/fixtures/watch-summary.example.json`
- `packages/shared-types/fixtures/run-record.example.json`
- `packages/shared-types/fixtures/signal-event.example.json`

### Control plane

- `services/control-plane/app/main.py`
- `services/control-plane/app/runtime_summary.py`

### Frontend shell

- `apps/console-web/src/main.ts`
- `apps/console-web/src/api/control-plane.ts`
- `apps/console-web/src/stores/shell.ts`
- `apps/console-web/src/App.vue`

### Verification

- `scripts/verify/README.md`
- `scripts/verify/verification_config.json`
- `tests/test_shared_contract_fixtures.py`
- `tests/test_control_plane_runtime_summary.py`
- `tests/test_verify_harness.py`

## Verification Commands

Use these from the repo root:

## Shared contract verification

```bash
npm run verify:shared-types
```

This confirms the shared-types package typechecks.

## Contract verification

```bash
npm run verify:contracts
```

This verifies:

- shared contract package typing
- shared fixture tests
- control-plane runtime summary endpoint shape

## Full current verification bundle

```bash
npm run verify
```

This runs:

- contract verification
- verify harness checks
- DTO size checks using representative fixtures

## Frontend checks

```bash
npm run typecheck -w @axon-watch/console-web
npm run build -w @axon-watch/console-web
```

## Python syntax checks

```bash
python3 -m py_compile services/control-plane/app/main.py services/control-plane/app/runtime_summary.py
```

## Service tests

```bash
python3 -m unittest discover -s tests
```

## What PASS / PENDING / FAIL Mean In Verification

The verify harness uses explicit states.

### `PASS`

The supplied evidence met the rule.

Examples:

- DTO payload fits its size budget
- dependency direction rule is respected

### `PENDING`

The check exists, but the slice does not provide enough real implementation or
evidence yet.

Examples:

- shell boot timing evidence not supplied yet
- runtime summary latency budget not yet measured
- no numbered ADR yet exists

`PENDING` is not automatically bad at this stage.

It means the governance has been created ahead of the full implementation.

### `FAIL`

The rule was violated or the harness itself is broken.

This is the one that should stop you.

## Common Working Patterns

## When adding frontend work

Use real shared types from `packages/shared-types/`.

Do not:

- invent local copies of DTOs
- widen semantics casually in component code
- hide backend meaning in placeholder strings

Good pattern:

- define or refine contract in shared-types
- use it in store/API layer
- render it in Vue components

## When adding control-plane work

Prefer:

- canonical DTO assembly
- light endpoint handlers
- explicit payload validation

Avoid:

- stuffing frontend-specific assumptions into the backend
- returning huge boot payloads
- redefining contract shapes inline

## When adding watch work

Prefer:

- narrow, owned summaries
- canonical signal/event identities
- explicit watch responsibilities

Avoid:

- pulling UI logic into the watch service
- importing control-plane domain semantics directly
- inventing competing signal vocabulary

## Troubleshooting

## Problem: `./scripts/dev/up.sh` fails or the frontend does not start

Check:

1. Did you run `npm install` at repo root?
2. Are ports `4173`, `8787`, and `8788` free?

Current expected path:

- root install: `npm install`
- root startup: `./scripts/dev/up.sh`
- frontend dev server: `npm run dev -w @axon-watch/console-web`

If startup fails, inspect:

- `.local/logs/console-web.log`
- `.local/logs/control-plane.log`
- `.local/logs/axon-watch.log`

## Problem: `check-health.sh` fails

This usually means one or more services never started.

Steps:

1. stop everything:

```bash
./scripts/dev/down.sh
```

2. start again:

```bash
./scripts/dev/up.sh
```

3. inspect logs:

- `.local/logs/control-plane.log`
- `.local/logs/axon-watch.log`
- `.local/logs/console-web.log`

4. re-run:

```bash
./scripts/dev/check-health.sh
```

## Problem: stale pid files block startup

`up.sh` will refuse to start if it finds existing pid files under `.local/pids`.

First try:

```bash
./scripts/dev/down.sh
```

If that is not enough, inspect:

- `.local/pids/`

Only remove stale pid files if you are sure those processes are not actually
running anymore.

## Problem: the shell loads but runtime summary is unavailable

Check:

1. Is control-plane running?
2. Does this endpoint work?

```bash
curl -fsS http://127.0.0.1:8787/api/runtime/summary | python3 -m json.tool
```

3. If running through Vite dev server, is `/api` proxied to control-plane?

Current dev proxy lives in:

- `apps/console-web/vite.config.ts`

You can also override the target with:

- `VITE_CONTROL_PLANE_BASE_URL`

## Problem: `npm run verify` shows `PENDING`

That is often expected at this stage.

Examples of currently expected pending checks:

- shell boot readiness
- runtime summary latency
- watch summary latency
- numbered ADR presence

Treat `PENDING` as:

- “scaffold exists, evidence not landed yet”

Treat `FAIL` as:

- “something is wrong right now”

## Problem: dependency direction checks fail

Check for forbidden imports across boundaries.

The current verify harness guards things like:

- watch service must not depend on UI internals
- frontend must not depend on watch internals
- future domain-layer cross-imports must stay clean

If a dependency check fails:

1. remove the cross-boundary import
2. move shared meaning into `packages/shared-types/` if appropriate
3. use an adapter or API boundary instead of direct reach-through

## Problem: contract tests fail after changing fixtures or DTOs

This usually means one of three things:

1. you changed a canonical field name
2. you widened/narrowed a type without updating the fixture
3. you changed semantics without updating the contract layer first

Fix sequence:

1. check the frozen planning doc
2. check the shared contract type
3. check the fixture
4. check the consumer/provider test

Do not patch the frontend alone and ignore the canonical contract.

## Problem: you are unsure whether something should become a new ADR

Ask:

1. Is this a real architecture or process decision?
2. Is it broader than one small implementation detail?
3. Would future readers need to know why this choice was made?

If yes, use ADR governance.

Current ADR process docs live in:

- `docs/adr/README.md`
- `docs/adr/_TEMPLATE.md`

Note:

- accepted ADRs should be numbered
- accepted ADRs should not be rewritten materially
- changed decisions should be superseded, not silently edited

## Tips And Tricks

## Tip 1: Read the planning bundle before expanding semantics

The planning bundle is not optional context. It is the definition of intended
meaning.

## Tip 2: Treat `packages/shared-types/` as sacred

If the frontend and backend disagree, fix it here first.

## Tip 3: Keep slices narrow

The repo is intentionally growing by thin slices.

If you are touching:

- run-state
- runtime summary
- signals
- approvals

then keep the slice tightly bounded and verifiable.

## Tip 4: Prefer fixtures early

Fixtures are useful in early slices because they:

- keep contracts concrete
- make DTO size checks easy
- let frontend and backend agree before deeper logic exists

## Tip 5: Use the verify harness even when it is not strict

`PENDING` today becomes `PASS` or `FAIL` tomorrow.

The harness is part of how this repo avoids drifting back into a monolith.

## Tip 6: Distinguish “bootstrap-real” from “feature-real”

Something can be real enough to run and still be intentionally shallow.

Current examples:

- runtime summary endpoint is real
- runtime summary assembly is still bootstrap-thin

That distinction matters during review.

## Tip 7: Do not overreact to incomplete polish

At this stage, review should focus on:

- boundaries
- ownership
- contracts
- verification

Not whether the shell is already pretty or feature-rich.

## What A Good Next Slice Looks Like

A good next slice should:

- keep shared contract semantics stable
- improve one owned behavior
- preserve boot simplicity
- come with verification

Examples:

- deepen runtime summary assembly
- add first watch-produced signal path
- add first real shell surface that consumes canonical payloads

Bad next slices:

- broad UI rewrite
- expanding multiple semantic families at once
- changing run-state and signal-state in one uncontrolled pass
- skipping verification because “it is still early”

## Final Guidance

If you are unsure what to do next, choose the smaller move that:

- preserves ownership
- strengthens verification
- reduces placeholders
- keeps the shell boot-safe

That is the design center of this repo right now.
