# Phase G6 `:4173`-only dry run — 2026-07-15

Status: **in progress**  
Window: 2026-07-15 through 2026-07-21  
Integration branch: `dev`

This is an evidence log, not a retirement acknowledgment. Only the operator may
attest that no unrecorded `:7734` fallback occurred or sign the retirement and
discard decisions.

## Entry rules

Each day requires:

1. `./scripts/dev/check-health.sh`
2. normal operator work through `http://127.0.0.1:4173`
3. the headed browser and connector-parity gates from
   `PHASE_G6_RETIREMENT_READINESS.md`
4. an operator fallback attestation with any `:7734` use and reason

Do not mark a day complete from automated health evidence alone.

## Daily ledger

| Day | Date | Automated health | Operator workflow | Required gates | `:7734` attestation |
|---|---|---|---|---|---|
| 1 | 2026-07-15 | PASS | pending | partial PASS | pending |
| 2 | 2026-07-16 | pending | pending | pending | pending |
| 3 | 2026-07-17 | pending | pending | pending | pending |
| 4 | 2026-07-18 | pending | pending | pending | pending |
| 5 | 2026-07-19 | pending | pending | pending | pending |
| 6 | 2026-07-20 | pending | pending | pending | pending |
| 7 | 2026-07-21 | pending | pending | pending | pending |

## Day 1 — automated prerequisite evidence

Recorded on 2026-07-15 after commit `022415d`.

- Console `http://127.0.0.1:4173/`: OK
- Control-plane health/readiness: OK / ready
- Watch health/readiness: OK / ready
- Required connectors unavailable: 0
- Runtime summary, inbox, briefing, runs, workspaces, and live events: OK
- Required PR Fast Gate: PASS

Open operator evidence:

- [ ] Complete a normal operator workflow on `:4173`
- [x] Run the Day 1 headed-browser and connector-parity gates
- [ ] Attest whether `:7734` was used

## Day 1 — automated gate evidence (2026-07-15 afternoon)

Recorded after local verification on `dev` (`0e813e6`).

- `./scripts/dev/check-health.sh`: PASS
- `npm run verify:headed-browser-smoke`: PASS (7.8s; report at
  `.local/verify/headed-smoke/headed-browser-smoke-report.json`)
- `npm run verify:connector-parity`: PASS (TEST-25 bundle)

Gate repairs in this slice:

- Headed smoke now pins operator center view to `grid` so the conversation seam
  is visible under the default brain-galaxy operator layout.
- Headed smoke fails fast when Vite CSS compilation is stale after settings
  stylesheet extraction.
- Connector acceptance retries runtime-summary connector projection for 20s
  after watch/control-plane restarts.

## Cutover evidence (2026-07-15 afternoon)

- `cloudflared.service` disabled and inactive; exclusive Axon-X managed PID only.
- Soft public cutover: Cloudflare remote ingress still `http://localhost:7734`,
  but local `:7734` reverse-proxies to Axon-X `:4173`. Public
  `https://axon.edudashpro.org.za/api/health` returns Axon-X `control-plane`.
- Legacy axon-local soft-rollback listens on `:7735` for WhatsApp / unmigrated
  paths (`AXON_PORT=7735`, tunnel start disabled).
- Optional hard cutover later:
  `CF_API_TOKEN=... ./scripts/ops/set-tunnel-ingress-4173.sh`
- Verify: `./scripts/verify/verify-attention-blockers.sh`

## Known retirement blockers

- WhatsApp monitoring remains explicitly deferred with `:7735` soft-rollback
  (operator previously chose defer; retirement still blocked until migrate or
  G5.4 discard ack).
- No retirement or discard acknowledgment is signed in this log.
- Day 1 operator workflow / `:7734` attestation checkboxes remain human-only.
