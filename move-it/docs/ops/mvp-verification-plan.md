# MoveIT MVP verification plan

Captured: 2026-08-26 (refreshed this watcher run)
Owner: Remy (Watcher)
Live run: `run_4d4642fb01ff`
Scope: End-to-end verification of the transport journey before MVP is declared done

## Purpose

This plan defines what I will test, how I will observe it, and what receipts I need before MoveIT MVP can ship. Feature journey tests apply after Priority 0 blockers (workspace delivery + minimum schema/APIs/screens) are cleared.

## Preconditions (must pass before feature verification)

| # | Gate | Owner | Pass criteria |
|---|---|---|---|
| P0-1 | Workspace delivery | Axon-X / host | Continuous worker publish succeeds; no "delivery is not configured for MoveIT" |
| P0-2 | Project manifest | Reed / Sol | Real `package.json`; `npm test` exit 0 |
| P0-3 | Service connection ready | Operator + Sol | `GET .../service-connection` → `ready=true`; required services resolved |
| P0-4 | Headless execution | Remy | `axon-agent-terminal-job --workspace MoveIT -- <cmd>` completes exit 0 in real project root |
| P0-5 | Schema present | Reed | Customer, Driver, Vehicle, Transport Job, Job Assignment, Quote, Delivery Event, Proof of Delivery, Rating with tenant boundaries |

**Live status (`run_4d4642fb01ff`, 2026-08-26):**

| Gate | Status | Receipt |
|---|---|---|
| P0-1 | **fail** | `GET .../delivery` → `{"detail":"Not Found"}`; Reed `run_292eb78b54ba` still blocked: delivery not configured for MoveIT |
| P0-2 | **pass** | `agent-job-f537f010ff44` — `npm test` exit 0 (2 pass / 0 fail) |
| P0-3 | **pass** | `configured=true`, `ready=true`; github/sentry/supabase `services_resolved=true`; operator `.env` absent (vault optional path) |
| P0-4 | **pass** | `agent-job-f537f010ff44`, `agent-job-dfa272b121fc`, `agent-job-5c6fee0ae7c6` — real root cwd |
| P0-5 | **not started** | No `apps/`, `src/`, or `services/` product trees on disk |

Also verified: `git rev-parse --is-inside-work-tree` → `true` (`agent-job-5c6fee0ae7c6`). Remote/branch listing was denied by sandbox policy this turn — cannot assert push remote or base branch from live probe.

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
| C7 | Track job | Customer opens live job screen | Live location + ETA updates | Job status: `en_route_pickup` → `at_pickup` → `in_transit` |
| C8 | Delivery | Driver completes drop-off | Delivery event recorded | Job status = `delivered` |
| C9 | Proof of delivery | Photo/signature/note captured | PoD artifact linked | PoD record with timestamp |
| C10 | Completion | Final price shown; rating submitted | Closed job + rating | Job status = `completed` |

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
| Failed / cancelled | Terminal failure states | Silent drops from matching queue |

## Data integrity checks (per test run)

1. Every job status transition has a corresponding audit/event row.
2. Quote links to the confirmed job version (not stale draft).
3. Assignment is unique per active job (no duplicate accept).
4. PoD references the correct job and driver.
5. Rating references completed job only.
6. Tenant boundary: cross-tenant read/write returns denied, not empty success.

## Test execution method

| Layer | Tool | Notes |
|---|---|---|
| API contracts | Automated tests under `tests/` | Reed owns; Remy runs in CI gate |
| Headless smoke | `axon-agent-terminal-job --workspace MoveIT -- npm test` | Real workspace root only |
| Health probe | `bash scripts/guardrails/check-workspace-health.sh` | Watcher guardrail |
| UI journey | Manual scripted walkthrough + capture in `output/verification/` | Ayesha pairs on first pass |
| Integration health | Service-connection live verify | Sol owns wiring; Remy monitors |
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

## Blockers (current — this run)

1. **P0-1 delivery** — still not configured; continuous publish cannot land specialist work.
2. **P0-5 product surface** — no schema/APIs/screens; C1–C10 and D1–D11 cannot execute yet.
3. **Failed specialist verify tasks** — `task-05d4b1c8b8fe43fe` (backend) and `task-7011efb4fa22459e` (integrations) terminal `failed`; open follow-ups remain for Lead to triage.
4. **Git remote/base branch** — not verifiable this turn (sandbox denied `git remote` / `git branch`).

See `docs/ops/watcher-shift-report-2026-08-26.md` for full receipts.
