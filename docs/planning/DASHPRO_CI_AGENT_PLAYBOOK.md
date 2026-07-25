# Dash Pro — how company agents handle CI work

**Source of truth for the incident:** DashPro ops report
`docs/ops/agent-reports/deploy-failure-triage-2026-07-13.md`
(in the Dash Pro project tree).

**Scope of this playbook:** detection, triage, fix, escalate, and follow-up.
**Not in scope:** committing, pushing, merging, or releasing unless someone explicitly asks.

---

## What Dash Pro said about the CI work

The “deploy failed” alert was a **CI gate failure**, not a live app outage.

On the working branch, the factory line failed in waves:

1. Quality formatting + npm audit hard-blocked the pipeline
2. Invalid Expo prebuild flag (`--clear` → `--clean`)
3. Missing Firebase config file on the runner
4. Android APK build ran out of Java heap (Jetifier + RN 0.81)
5. Runner lost communication / heap too high
6. Disk full mid-build
7. Android SDK path permission after reclaiming disk

**Current state (2026-07-13):** main CI, security scan, and Android APK assemble are green on `development`.
Play Internal publish still only runs from `main` — a green `development` build does **not** mean Play Store publish.

**Open follow-ups (not blocking):**

- Dedicated Prettier pass
- Dependency remediation for high/critical advisories
- Set real `GOOGLE_SERVICES_JSON` secret for non-stub Android CI builds — **done 2026-07-14**

---

## Company roster (agents we already staff)

| Employee                 | Role         | Job on CI work                                                                                          |
| ------------------------ | ------------ | ------------------------------------------------------------------------------------------------------- |
| **DashPro Lead**         | lead         | Prioritize CI red vs product work; decide when firefighting stops; escalate decisions that need a human |
| **DashPro Night Watch**  | watcher      | Detect CI/red-build signals and health digests; never ship product changes alone                        |
| **DashPro Frontend**     | frontend     | Own Expo/Android workflow UI-side breakage (prebuild flags, app config plugins)                         |
| **DashPro Backend**      | backend      | Own quality gate scripts, typecheck/test failures, edge/function breakage that fails CI                 |
| **DashPro Integrations** | integrations | Own GitHub Actions / Android runner / secrets wiring / SDK path / disk reclaim                          |

Dash Pro specialist watchers (already scripted in the Dash Pro project):

| Watcher              | CI-related duty                                                       |
| -------------------- | --------------------------------------------------------------------- |
| **QualityGate**      | Local lint / typecheck / test failure → warn before push              |
| **BranchGuard**      | Wrong branch / dirty tree noise (report only; do not invent commits)  |
| **AndroidToolchain** | Local SDK/adb readiness (separate from cloud Android CI)              |
| **WatcherFleet**     | Daily digest that should include “CI last known green/red” when wired |

Planned responder (documented in Dash Pro autonomous agents plan, not fully wired yet):

| Responder    | Trigger                 | Allowed                                                                           | Must ask first                                                      |
| ------------ | ----------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| **CITriage** | CI red on `development` | Diagnose logs, fix obvious workflow/config/lint issues, write a short triage note | Force-push, merge to `main`, Play promote, secret rotation, DB push |

---

## Playbook — when CI goes red again

### 1. Detect (Night Watch + QualityGate)

- Night Watch surfaces a plain-language alert: “Dash Pro build checks failed,” with workflow name + failing step.
- QualityGate report is attached or linked when the failure is lint/type/test.
- Severity: **P0/P1** if Android assemble or main CI is red on `development`; **P2** if only advisory soft checks.

### 2. Classify (Lead + Integrations)

Lead asks one question: **gate failure vs product outage?**
Integrations confirms which workflow failed (quality CI vs Android pipeline vs security).

### 3. Triage (CITriage / Integrations / Frontend / Backend)

Follow the same wave order the July 13 report used:

1. Read the failing job log (do not guess)
2. Identify the first hard-fail step
3. Assign owner by failure class:
   - format / lint / types / unit tests → Backend (+ Frontend if UI-only)
   - workflow YAML / runner disk / SDK / secrets / Expo flags → Integrations
   - Android Gradle / Jetifier / heap → Integrations + Frontend
4. Apply the smallest fix that unblocks the gate
5. Re-check the same workflow until green, or stop with a clear blocker

### 4. Report (Lead)

One short note with:

- Verdict (CI gate vs outage)
- Failing step
- Fix applied or blocker
- What is still open

No invented chores (including “please commit leftover local files”) unless those files are part of the CI fix and an explicit commit was requested.

### 5. Follow-ups (scheduled, not emergency)

After green:

- Prettier pass → Frontend + Backend
- npm advisory remediation → Backend + Integrations
- Real Firebase CI secret → Integrations — **done 2026-07-14** (`GOOGLE_SERVICES_JSON`)

---

## Live demo (2026-07-14)

To see idle vs working in the console:

1. Open **Axon-X** — only **Night Watch** should be on duty (`watching`); others idle when no Axon-X job is active.
2. Switch to **DashPro** — only the **Lead** mirrors the active run (`executing` / `verifying`); **Night Watch** stays `watching`; Frontend / Backend / Integrations stay `idle` until a role-tagged job exists.
3. Evidence and board live in the DashPro tree:
   `docs/ops/agent-reports/assignment-board-2026-07-14.md`
   plus today’s Night Watch JSON reports under the same folder.

**Wave 1 (done):** Prettier diagnosis, npm advisory triage, Android toolchain plan, EnvDrift plan.
**Wave 2 (done, local):** `.prettierignore` + `.env.example` placeholder sync (`run_6cfae356af02`).
**Wave 3 (done, local):** env mode → development, safe `npm audit fix`, Android SDK path wiring.
**Firebase CI secret (done):** `GOOGLE_SERVICES_JSON` set from local `google-services.json` on 2026-07-14T12:58Z.
**Validation run (2026-07-14):** GitHub does not auto-run workflows when a secret is added — only scheduled jobs (e.g. Voice Benchmark Nightly) show as “today” until someone re-runs or pushes. Android CI/CD Pipeline **#29267191322** was re-run after the secret landed; watch it on the Actions tab (≈1h for the full Android build).

**CI history (2026-07-14):** On the **CI** workflow tab, runs **#81–#91** stay red — they failed before the Jul 13 fixes (Prettier hard-block, npm audit gate, etc.). That is expected history; GitHub keeps failed runs red and re-running those old commits would still use the broken workflow. **Current factory line is green:** CI **#92–#103** passed on `development`. **CI #103** was re-run on 2026-07-14 (~20:00 UTC+2) and finished green — [run #29267191364](https://github.com/axon-control-ops/dashpro/actions/runs/29267191364). Refresh the Actions page: the top entry should now show a green check; only the older #81–#91 rows stay red.

## After CI is green (no babysitting)

When the factory is healthy again — as on 2026-07-13 — agents stay at work while the stack is running. They do **not** invent “clear the desk / commit leftover files” chores unless someone explicitly asks.

| Priority after green   | Owner                  | Autonomous action                                                                                                                    | Needs a human                              |
| ---------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------ |
| Treat CI win as closed | Lead + Night Watch     | Stop firefighting; watch for a _new_ red run only                                                                                    | —                                          |
| Dirty local tree noise | BranchGuard → Lead     | Report file list + options (finish / discard / hold). **Never auto-commit.**                                                         | Any write to git history                   |
| Next company work      | Lead assigns           | Pick one open product priority from the backlog (salvage leftovers, Android toolchain, env safety, preview slice) and start that job | Release / Play / secrets / merge to `main` |
| Ongoing health         | Night Watch + watchers | Keep writing digests under `docs/ops/agent-reports/`                                                                                 | Only P0/P1 escalations                     |

Operating model (already documented in Dash Pro’s autonomous agents plan):

1. **Watchers** run on a schedule and write JSON reports.
2. **Responders** (e.g. CITriage) only wake on a new red CI run.
3. **Builders** (Frontend / Backend / Integrations) take the Lead’s chosen priority and work continuously while the server is up.
4. **Lead** turns reports into a short digest — green / needs attention / decision needed — so a human is not needed for every tick.

---

## Hard gates (never autonomous)

- Merge to `main`
- Play Store / internal track promote
- Secret rotation or writing production secrets
- `supabase db push` on production
- Bulk delete of user-data storage
- Committing or pushing unless someone explicitly asked for that

Workers may prepare a PR or draft fix. A human must approve those gates.

---

## Instruction-taking rule (for every Dash Pro employee)

Before acting on a plain-language request:

1. Convert it into **Instructions** markdown (Goal / In scope / Out of scope / Steps / Constraints).
2. Treat “Out of scope” as binding — if commit/push/release was not asked for, do not add it.
3. Do the listed steps only.
4. Reply with what changed, in plain language.

Use the console composer **Instructions** control, or the `plain-text-to-instructions` skill, to produce that markdown.
