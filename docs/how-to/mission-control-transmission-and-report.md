# Mission Control, Transmission, and REPORT (second brain)

**Updated:** 2026-07-27  
**Audience:** operators who want Axon-X as an active second brain — not a quiet dashboard.

Companion to [`docs/HOW-TO-HANDBOOK.md`](../HOW-TO-HANDBOOK.md) and
[`recent-operator-features.md`](recent-operator-features.md).

---

## Confirm what shipped (operator view)

| Claim | Status | How to check |
| --- | --- | --- |
| Mission Control **right dock** = Live Ops (orb + Transmission + talk box) | Shipped | OPERATOR → Mission Control (grid). Brain Graph hides this dock. |
| **Transmission** card holds VAXON replies while you stay on Mission Control | Shipped | Speak/type in the Live Ops box; reply appears under the orb (not only the left chip). |
| **Open DashPro workspace** enters **IDE** | Shipped | Type `Open DashPro workspace` → layout flips to IDE. Reply: `Opening DashPro.` |
| **Show me / focus DashPro** stays on Mission Control | Shipped | Type `Show me DashPro` → Focus · DashPro, reply `DashPro is on deck.` |
| Fleet tiles pulse / say **live** when runs or busy agents exist | Shipped (data-dependent) | Needs active runs or mid-shift teammates; otherwise tiles stay Nominal. |
| Agent “thinking I’ll…” rewritten to action copy | Shipped (UI sanitize) | Captions/chips show e.g. `Reading…` / `Checking…` when thinking leads with that filler. |
| **REPORT** / Status / Update → categorized JARVIS stand-up | Shipped | Type `REPORT` — expect Attention / Work in flight / Next (no semicolon dump; `four Lead-team…` not `4 Lead`) |
| **AUTONOMOUS ON/OFF** on Live Ops orb | Implemented; live drill pending | ON confirms Full; OFF uses hard-kill; effective state reflects host/scheduler gates; guarded items show exact approve/reject controls |

**Confidence on the above table:** **7/10** — code + unit tests verified; live console walkthrough after hard-refresh still recommended.

### AUTONOMOUS control (right dock)

1. OPERATOR → Mission Control → Live Ops (right dock under the orb).
2. **AUTONOMOUS ON** → confirms Full mode; the orb says Running only when the
   scheduler is effective (the host brake may leave it Blocked/configured).
3. VAXON turns safe findings into isolated specialist tasks. Existing routed
   handoffs keep their target task instead of creating a duplicate.
4. Critical / dangerous / secrets / production / protected merge / spend →
   **Needs you**, with the reason/detail and **Approve exact task** / **Reject**.
5. **AUTONOMOUS OFF** and **Hard-kill** demote to Semi, pause new starts, and
   attempt to stop active shifts. The banner reports any stop failures.
6. Receipts use their durable receipt-creation time and are scoped to the
   focused workspace; Last scan shows the actual workspace scan timestamp.
7. Status: `GET /api/operator/autonomy/status`.

See [`auto-loop-and-credits.md`](auto-loop-and-credits.md) and
[`company-hierarchy-and-lead-checkin.md`](company-hierarchy-and-lead-checkin.md).

---

## How to use Axon-X to the fullest (daily)

### 1. Stay on Mission Control for command

1. Top nav → **OPERATOR**.
2. Bottom chips → **Mission Control** (leave Brain Graph).
3. Right dock = your second brain surface: orb, **Transmission**, stream, talk box.
4. Footer workspace should match what you care about (`workspace_dashpro`, `workspace_axon_watch`, …).

### 2. Talk like a mission partner

| You say | What VAXON should do |
| --- | --- |
| `REPORT` / `status report` / `standup` / `where do we stand` | Deep stand-up: risks, busy teammates, approvals, one next move → **Transmission** |
| `Show me DashPro` | Focus DashPro on Mission Control; keep Live Ops open |
| `Open DashPro workspace` | Enter the IDE for DashPro (coding surface) |
| `Open attention` | Jump Attention sidebar for signals |
| `Open VAXON briefing` | Open briefing surface |
| “What is Dana doing?” | Prefer `REPORT` instead — VAXON should name busy leads/specialists from live roster |

### 3. Turn on voice presence (so VAXON is less quiet)

In **Settings → Operator presence**:

- Enable **spoken alerts** for high/critical signals.
- Enable **JARVIS duplex** (`proactive_duplex_enabled`) if you want speak → listen loops.
- Unlock voice / hands-free when the orb offers it.

Without spoken alerts + duplex, Mission Control looks “quiet” even when the fleet is busy — the stream still ticks, but VAXON will not interrupt you.

### 4. Company work vs chat

- **Task board** = durable leased work (Gate 4). Create goals; workers claim when scheduler is on.
- **IDE Ask/Agent** = conversation vs tool work with a named teammate.
- **Lead fan-out** = “check with all sub-agents…” creates multiple tasks/runs — then use **REPORT** for the rollup.

### 5. Fast Gate / signals (example from a live session)

When Attention shows many **Axon-X Fast Gate failed on feat/mission-control-holographic**:

1. Do not panic-click every signal.
2. Say **REPORT** — get the rollup + next move.
3. Or open the failed run URL from the signal DETAILS, fix, push, then `./scripts/ops/watch-fast-gate.sh`.

---

## Examples (copy-paste)

**Stand-up without interrogating each person**

```text
REPORT
```

Expanded under the hood to a status-report prompt so VAXON covers teammates and next move.

**Focus then dig in**

```text
Show me DashPro
REPORT
```

**Leave Mission Control into code**

```text
Open DashPro workspace
```

Then work in IDE; return with top nav **OPERATOR** → Mission Control.

---

## Where we can improve (honest backlog)

| Gap | Why it hurts | Suggested next slice |
| --- | --- | --- |
| No **timed** auto-REPORT | You still must ask or wait for alerts | Cadence: every N minutes while OPERATOR+Mission Control focused, if material_change or busy agents > 0, speak a short rollup into Transmission |
| Quiet when fleet is Nominal | Busy *work* without signals looks idle | Surface Lead check-in / open task counts on fleet tiles even without Sentry |
| Brain Graph evidence panel ≠ Transmission | Replies feel “lost” on Graph | Mirror last Transmission line onto Galaxy speech captions / evidence header |
| Open-workspace leaves Live Ops | `Opening DashPro.` never paints Transmission | Optional: speak reply before IDE switch, or keep a 2s Transmission hold |
| Scheduler off by default | Task board stays “No live work” | Document when to enable continuous workers; optional one-click “engage Lead plans” |
| Stale Fast Gate signals | Attention floods | Auto-dismiss or collapse duplicate branch failures once HEAD is green |

---

## Design opinion: REPORT vs constant chatter

**REPORT as a hotword is the right primary control** — you stay in charge of when VAXON talks.

**Proactive duplex + spoken alerts** should cover interrupts (critical Sentry, approvals, Fast Gate red).

**Cadenced auto-REPORT** (optional setting, e.g. every 10–15 min while Mission Control is focused and something changed) is the missing middle: second-brain energy without becoming a chatterbox. Prefer “material change or busy teammate” gates over a dumb timer.

Until cadence lands: use **REPORT** whenever you would otherwise ask “what are we doing / what is Dana doing.”
