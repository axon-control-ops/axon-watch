# MoveIT MVP verification plan

Captured: 2026-08-25
Owner: Remy (Watcher)
Scope: End-to-end verification of the transport journey before MVP is declared done

## Purpose

This plan defines what I will test, how I will observe it, and what receipts I need before MoveIT MVP can ship. It applies after Priority 0 blockers (workspace delivery, service readiness) are cleared and specialists have landed the minimum schema, APIs, and screens.

## Preconditions (must pass before feature verification)

| # | Gate | Owner | Pass criteria |
|---|---|---|---|
| P0-1 | Workspace delivery | Axon-X / operator | Continuous worker publish succeeds; no "delivery is not configured for MoveIT" |
| P0-2 | Project manifest | Reed / Sol | Real `package.json` (not empty directory); `npm test` runnable |
| P0-3 | Service connection ready | Operator + Sol | `GET .../service-connection` → `ready=true`; Supabase + GitHub + Sentry resolved |
| P0-4 | Headless execution | Remy | `axon-agent-terminal-job --workspace MoveIT -- <cmd>` completes with exit 0 in real project root |
| P0-5 | Schema present | Reed | Customer, Driver, Vehicle, Transport Job, Job Assignment, Quote, Delivery Event, Proof of Delivery, Rating entities exist with tenant boundaries |

**Live status (Lead retry `run_6c72a01d1632`, 2026-08-26):** P0-1 **fail** (delivery still not configured — same error as `run_5f7fd88f9487`), P0-2 **pass on disk** (`package.json` is a file + `tests/smoke.test.js` present; continuous publish still blocked), P0-3 **pass** (`ready=true` via vault; operator `.env` still absent), P0-4 **pass** (`agent-job-8c4b12008fde`), P0-5 **not started**.

## Customer journey — critical workflow tests

Each step must persist state, emit an observable event, and be recoverable after refresh/restart.

| # | Step | Input / action | Expected persisted state | Observable signal |
|---|---|---|---|---|
| C1 | Create request | Customer describes item, pickup, destination (text/voice) | Draft transport request with parsed fields | API record + audit event |
| C2 | Structured job | AI fills missing fields only | Job draft with all required fields | Job status = `draft` |
| C3 | Confirm job | Customer reviews and corrects fields | Confirmed job snapshot | Job status = `confirmed` |
| C4 | Quote | System calculates distance/time/price | Quote record linked to job | Quote amount + validity window |
| C5 | Driver matching | System searches suitable drivers | Assignment attempt / match queue | Job status = `matching` |
| C6 | Driver accepts | Available driver accepts | Job assignment with driver + vehicle | Job status = `assigned` |
| C7 | Track job | Customer opens live job screen | Live location + ETA updates | Job status progresses: `en_route_pickup` → `at_pickup` → `in_transit` |
| C8 | Delivery | Driver completes drop-off | Delivery event recorded | Job status = `delivered` |
| C9 | Proof of delivery | Photo/signature/note captured | Proof-of-delivery artifact linked | PoD record with timestamp |
| C10 | Completion | Final price shown; rating submitted | Closed job + rating | Job status = `completed`; payment/settlement stub if in scope |

### Screen mapping (customer)

| Screen | Covers steps | Fail if |
|---|---|---|
| Home (request input) | C1–C2 | Input accepted but no persisted draft |
| Job confirmation | C3–C4 | Customer cannot edit fields before confirm |
| Driver matching | C5–C6 | UI shows driver without backend assignment |
| Live job | C7 | Map/ETA static or not tied to job id |
| Completion | C8–C10 | Missing PoD, price, or rating persistence |

## Driver journey — critical workflow tests

| # | Step | Expected state | Fail if |
|---|---|---|---|
| D1 | Register | Driver identity linked to tenant | Orphan account, no role |
| D2 | Profile complete | Required profile fields saved | Driver cannot go available |
| D3 | Vehicle info | Vehicle record linked to driver | Accept blocked silently |
| D4 | Become available | Driver status = `available` | Ops cannot see driver |
| D5 | See available jobs | Filtered job list for eligible work | Shows mock/static data |
| D6 | Accept job | Assignment created; job locked to driver | Double-assign possible |
| D7 | View pickup | Pickup address + navigation hook | Wrong job or stale coords |
| D8 | Start transport | Job status → `in_transit` | Status skip with no audit |
| D9 | Complete delivery | Delivery event written | UI success without record |
| D10 | Record PoD | Artifact stored and linked | Missing from ops view |
| D11 | See earnings | Completed job reflected in earnings | Hard-coded totals |

## Operations MVP — observability tests

Ops must identify stuck jobs without database access.

| View | Must show | Stuck-job signal |
|---|---|---|
| Active jobs | In-progress transports with driver + ETA | Status unchanged > threshold |
| Unassigned jobs | Confirmed jobs with no driver | Age + last match attempt |
| Available drivers | Drivers marked available | Count matches driver API |
| Active drivers | Drivers on assigned jobs | Driver status vs job status mismatch |
| Completed jobs | Closed with PoD + final price | Missing PoD on "completed" |
| Failed / cancelled | Terminal failure states | No silent drops from matching queue |

## Data integrity checks (per test run)

After each end-to-end run I will verify:

1. Every job status transition has a corresponding audit/event row.
2. Quote links to the confirmed job version (not stale draft).
3. Assignment is unique per active job (no duplicate accept).
4. PoD references the correct job and driver.
5. Rating references completed job only.
6. Tenant boundary: cross-tenant read/write returns denied, not empty success.

## Test execution method

| Layer | Tool | Notes |
|---|---|---|
| API contracts | Automated tests under `tests/` (once present) | Reed owns; Remy runs in CI gate |
| Headless smoke | `axon-agent-terminal-job --workspace MoveIT -- npm test` | Real workspace root only |
| UI journey | Manual scripted walkthrough + screenshot/log capture in `output/verification/` | Ayesha pairs on first pass |
| Integration health | Service-connection live verify commands | Sol owns wiring; Remy monitors |
| Runtime | Watcher shift reports in `docs/ops/` | This plan + per-run receipts |

## MVP dependency graph (verification order)

```
P0 delivery + services ready
        │
        ▼
Schema + tenant APIs (Reed)
        │
        ├──────────────────┐
        ▼                  ▼
Customer screens      Driver screens
(Ayesha)              (Ayesha)
        │                  │
        └────────┬─────────┘
                 ▼
        Maps / notifications / payments (Sol) — minimum only
                 │
                 ▼
        Ops observability views
                 │
                 ▼
   Remy: full C1–C10 + D1–D11 + ops matrix
                 │
                 ▼
           MVP done gate
```

## MVP done gate (Remy sign-off)

I will not sign off until a **real test customer** completes all ten Definition-of-Done steps in one session with:

- [ ] Persisted records for every major state change
- [ ] Ops can see the same job through completion
- [ ] No mock-only screens on the critical path
- [ ] Failed-run receipts archived under `docs/ops/` or `output/verification/`
- [ ] Publish/delivery succeeds for the verification artifacts

## Out of scope for MVP verification

- Advanced fleet management
- Retailer integrations
- Complex pricing engines
- Multi-category transport workflows
- Load/performance testing beyond single-journey smoke

## Blockers (current)

See `docs/ops/retry-report.md` and `docs/ops/service-connections.md` for 2026-08-26 Lead retry receipts. Summary:

1. **Delivery not configured** — continuous publish still blocked; prior Mira handoffs failed; new handoff POST needs operator bearer token.
2. **No product code** — smoke test only; no APIs or screens for C1–C10 / D1–D11 yet.
3. **Service connection ready via vault** — P0-3 improved (`ready=true`); operator `.env` still optional/absent.
4. **Git delivery path** — prior receipts reported no `.git`; not re-verified with absolute-path probe this turn.
