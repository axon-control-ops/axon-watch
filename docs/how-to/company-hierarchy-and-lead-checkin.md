# Company hierarchy, Lead check-in, and monitoring close-out

**Audience:** operator + company Leads (Mira, Dana, Lindi, …)  
**Clock:** continuous worker scheduler tick (`services/control-plane/app/workspace_agents/scheduler.py`)  
**Work source:** `lead_team_checkin` in `config/autonomy-work-sources.json`

---

## Confirmed hierarchy flow

```text
You (Decide)
  ↑↓
VAXON (fleet brain / operator thread)
  ↑↓
Company Lead  (Mira / Dana / Lindi / …)
  ↑↓
Specialists   (watcher · frontend · backend · integrations)
  ↑
Lead rollup → VAXON → You for Decide gates
```

| Layer | Owns |
| --- | --- |
| **You** | Priorities, Decide approvals, production go/no-go |
| **VAXON** | Cross-company routing, spoken alerts, Lead charter intents |
| **Lead** | Team check-in, assign the right specialist, rollup to VAXON |
| **Watcher** | Signals, CI/Fast Gate, Sentry/Vercel health, CRC completion |
| **Frontend** | Console / Expo / UI surfaces |
| **Backend** | APIs, control plane, persistence |
| **Integrations** | Connectors, PostHog/Supabase/email wiring, cross-repo |

Axon-X (`workspace_axon_watch`) coaches other Leads; child companies own their
product trees. EduDash Pro marketing site (`edudashpro.org.za`) is **DashPro**
(Dana / Cass / Priya / Soren) — not EDP Excellence.

---

## Lead team check-in (clocked guardrails)

Same pattern as axon-local’s interval scheduler: the continuous worker **tick**
(~45s) runs explicit work sources. Lead check-in is cooldown-gated (default
**900s / 15 min** per company) so it does not spam Lane B.

Each due company Lead pass:

1. Scans **failed specialist shifts** (roster last outcome).
2. Scans **watch monitors + required connectors** (third-party / public health).
3. **Assigns** the matching specialist via leased ledger tasks (`Lead assigned:`).
4. **Escalates only** (Lead IDE note, no code task) for usage limits, runtime
   auth, restart interrupts, or operator-stopped shifts.
5. Posts a short check-in note into the Lead IDE thread when there is work.

### Assignment guardrails

| Signal | Owner |
| --- | --- |
| Failed watcher / frontend / backend / integrations shift | Same role |
| Sentry / CI / GitHub / Vercel monitor | `watcher` |
| PostHog / Supabase / email / generic connector | `integrations` |
| Control-plane / API HTTP health | `backend` |
| Console / UI HTTP health | `frontend` |
| Usage limit / vault auth / restart interrupt | Escalate to Lead → VAXON (no auto repair task) |

Continuous workers still pick up `Lead assigned:` / `VAXON attend:` tasks when the fleet
scheduler is enabled; Leads stay `on_demand` and do not auto-start as workers.

### VAXON attend loop (Full autonomy)

When Mission Control **AUTONOMOUS ON** (`autonomy_mode=full`), the scheduler also
runs work source `autonomous_attention`:

1. Collects failed shifts, monitors/connectors, inbox warnings, and open handoffs.
2. Classifies each item with a fail-closed safety policy.
3. **Dispatches** auto-safe items as deduped specialist tasks (`VAXON attend:`).
4. Reuses an already-routed handoff target task instead of creating a duplicate.
5. **Escalates** critical/dangerous items into pending autonomy decisions.
6. **Approve exact task** creates one attempt-bounded `risk=approved` task;
   **Reject** resolves the decision without work.
7. High / unclassified task `risk` cannot be claimed by continuous workers.

Emergency stop: Mission Control **Hard-kill** (or **AUTONOMOUS OFF**) demotes
Full → Semi, pauses new starts, and attempts to stop active worker shifts.
Any partial stop failures remain visible for operator review.

Manual fan-out remains available:

```bash
curl -sS -X POST "http://127.0.0.1:8787/api/workspaces/workspace_dashpro/lead/fan-out" \
  -H 'content-type: application/json' \
  -d '{"goal":"Check with all sub-agents on current blockers"}'
```

---

## External + third-party monitoring

| Surface | Config |
| --- | --- |
| DashPro Sentry / PostHog / Supabase + site/GitHub HTTP | `config/dashpro-monitor-slice.json` |
| Axon-X public origin / control plane / GitHub HTTP | `config/axon-x-monitor-slice.json` |
| Connector probes (required + optional third-party) | `config/watch-connectors.json` |
| New check type | `http_health` in `services/axon-watch/app/monitors/http_health.py` |

Inbox still projects non-ok monitor statuses; Lead check-in turns those into
role-owned tasks on the clock.

---

## Continuous specialist → Lead → VAXON

When a specialist finishes an IDE or continuous job (even without a Lead plan):

1. **Specialist** ends with a short handoff: what changed, verified, Blockers / Lead next.
2. **Lead** gets an automatic takeover note in the Lead IDE tab + a follow-up task.
3. **VAXON** gets a short operator-thread flash so `REPORT` / update has live fleet memory.
4. Full Lead **plans** still synthesize into a richer VAXON handoff when all plan tasks finish.

```text
Specialist finishes
  → Lead takeover (Dana tab)
  → VAXON flash (operator thread)
  → You ask REPORT → VAXON uses roster + those handoffs
```

---

## Close-out checklist — monitoring mode with Axon-X in play

Use this when shifting from build/ship into supervised monitoring:

1. **Fast Gate green** on the active Axon-X branch (`./scripts/ops/watch-fast-gate.sh`).
2. **Public origin** healthy (`https://axon.edudashpro.org.za/api/health`).
3. **Worker scheduler** on only when you want continuous specialists + Lead
   check-in assignments to dispatch (Mission Control → fleet scheduler).
4. **CI remediation** webhook or poller live (`docs/how-to/ci-remediation-gate9.md`).
5. **Vault** holds Sentry/PostHog/Supabase tokens so DashPro monitors are not
   stuck in `skipped`.
6. Confirm company roster in `config/workspace-agents.json` matches the hierarchy
   above.
7. Leave Decide gates with you; VAXON + Leads escalate, they do not silently
   ship production.

Proof:

```bash
./scripts/dev/python.sh -m unittest \
  tests.test_lead_team_checkin \
  tests.test_http_health_monitor \
  tests.test_autonomy_guardrails \
  -q
```

**Confidence: 8/10** — clocked Lead assignment + HTTP monitor hardening are
wired and unit-tested; live multi-company assignment under load still depends on
scheduler enablement and vault credentials.
