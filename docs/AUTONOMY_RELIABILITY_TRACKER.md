# Axon-X Autonomy Reliability Tracker

**Status:** Superseded for progress tracking by [`STRICT_PROGRESS_CHECKLIST.md`](./STRICT_PROGRESS_CHECKLIST.md) (operator-authoritative 0–22 checklist, 2026-07-15).
**Created:** 2026-07-14
**Scope:** Reliability and safety work discovered during the autonomy audit.

Keep this file as historical notes from the first vertical slice. Update day-to-day progress on the strict checklist.

This tracker records remediation work; it does not replace the locked Phase G
plan or authorize retirement. Update an item only with its stated evidence.

## Evidence policy

- Preserve the existing dirty worktree until a separate clean-baseline comparison
  is agreed and recorded.
- A failing command in a dirty worktree is a current-worktree finding, not proof
  of a committed-baseline regression.
- Mark runtime defects only after reproduction evidence identifies the failing
  path and outcome.
- Do not raise file-size ratchets merely to make a gate pass; extract bounded
  modules instead.

## Work items

- [x] **0. Preserve and characterize the current worktree**
  - [x] Record `git status --short`.
  - [x] Record `git diff --check`.
  - [x] Record the current branch and HEAD commit.
  - [x] Do not reset, discard, stash-pop, or attribute failures to baseline
        before a clean-worktree comparison.
  - **Captured 2026-07-14:** branch `dev`, HEAD
    `fb2737f78af436141da35ed5c285174d5509d666`; the worktree contains extensive
    modified and untracked work. `git diff --check` reports two whitespace
    errors: `apps/console-web/src/main.ts:17` and
    `apps/console-web/src/styles/shell/mockup-shell-31.css:85`.
  - **Exit evidence:** timestamped status/whitespace/HEAD snapshot — captured;
    preservation remains ongoing. Session `2d7c56` debug instrumentation removed
    after post-fix verification.

- [x] **1. Make the Python test environment reproducible**
  - [x] Confirm and document the supported `unittest` command instead of
        treating an unsupported repo-root `pytest` invocation as authoritative.
  - [x] Ensure the supported command isolates the control-plane and watch
        top-level `app` packages where required.
  - [x] Prove the supported command begins execution.
  - [x] Identify the test that prevents the aggregate main suite from
        completing, then record final pass/fail counts
        separately from the current dirty-worktree baseline.
  - **Exit evidence:** documented `unittest` command selects the intended
    service package and begins its named test modules.
  - **Captured 2026-07-14:** The contract runner now executes every named
    module in a separate interpreter process. Post-fix verification completed
    **343 tests in 308 seconds** with **7 current-worktree failures** across five
    modules; the runner no longer stalls. `README.md` documents
    `./scripts/verify/run_contract_unit_tests.sh` as the supported backend
    command.

- [x] **2. Restore console type safety**
  - [x] Reconcile canonical DTO exports and frontend imports.
  - [x] Update required-field fixtures and stale type expectations.
  - **Exit evidence:** `npm run typecheck -w @axon-watch/console-web` passes
    (verified 2026-07-14).
  - **Fix notes:** re-exported `BriefingAction`, `RuntimeSummaryActiveRun`, and
    `WorkspaceAgentListSnapshot` from `contracts/canonical.ts`; updated presence
    fixtures for new voice fields; tightened narration and thread-map typing.

- [x] **3. Restore frontend test reliability**
  - [x] Diagnose spoken-reply parser regressions.
  - [x] Diagnose narration extraction regression.
  - [x] Diagnose mixed Azure/browser voice-playback timeout.
  - [x] Reconcile command-catalog test expectation.
  - [x] Operator confirms targeted Vitest suite green.
  - **Exit evidence:** full console Vitest **720/720 pass** (2026-07-14).
  - **Fix notes:** `:::tool` headers are single-line skips; voice playback
    fake timers include `HAVE_FUTURE_DATA` + ≥3500ms advance; catalog includes
    `move_voice_orb`. Session `2d7c56` sanitize instrumentation removed.

- [x] **4. Restore structural gates**
  - [x] Remove whitespace errors reported by `git diff --check`.
  - [x] Clear the seven previously failing backend contract assertions
        (`memory_highlights` shape + email-stub inbox ranking expectations).
  - [x] Clear tiny/hard-limit one-line overruns: `control-plane.ts`,
        `mockup-shell.css`, `app.css`, `main.py` (extracted lifespan stub),
        `AgentDockComposerToolbar.vue`, `WorkbenchTerminalDock.vue`.
  - [x] Extract remaining oversized hotspots into bounded modules; lower
        ratchets (never raise). Repair extraction regressions (research
        import, ConversationSeamPanel paths, shell TDZ, stream activity
        typing, workspace-agent imports).
  - [x] Regenerate `docs/planning/MANIFEST.json` for untracked
        `DASHPRO_CI_AGENT_PLAYBOOK.md` hash drift.
  - **Exit evidence:** `npm run verify:contracts` PASS (`VERIFY_CONTRACTS:0`,
    2026-07-14) without budget increases.
  - **Captured 2026-07-14:** size gate PASS; typecheck PASS after extraction
    repairs; planning manifest regenerated for playbook hash drift;
    ConversationSeamPanel root-template mismatch fixed (Vite overlay).

- [x] **5. Prove and repair autonomy dispatch correctness**
  - [x] Runtime-reproduce stale `pending_command` duplicate dispatch.
  - [x] Runtime-reproduce `health` versus `check health` tier behavior.
  - [x] Runtime-reproduce surfaced run-finalization failures.
  - [x] Add targeted regression coverage after each proof.
  - **Fix notes (2026-07-14):**
    - Auto-dispatch commands clear `pending_command` (no stale `yes` re-dispatch).
    - `check health` / `check-health` are reversible_auto allowlisted shell.
    - `RunLifecycleError` on finalize → `fail_run` (or error receipt), not silent pass.
  - **Evidence:** session `2d7c56` NDJSON P1/P2/P3 before/after; unit tests OK
    (`test_voice_autonomy`, `test_command_shortcuts`, `test_chat_orchestration`,
    `test_auto_dispatch_command_does_not_leave_stale_pending`).

- [x] **6. Unify KAIRO execution and operator receipts**
  - [x] One awaited dispatch path for typed and voice turns (slice 1:
        `kairo-conversation-dispatch.ts`; both omnibar + app-voice await).
  - [x] Consistent context, action tier, routing receipt, model receipt, and errors
        (followup `dispatch_command` now emits tier + receipts; typed path sets
        `kairoLastActionTier` / routing receipt).
  - [x] Truthful autonomy status based on live policy and run state
        (removed hardcoded `:auto-allowed="true"`; projector uses `actionTier`).
  - [x] Hands-free no longer disables KAIRO typing (manual PTT only).
  - **Exit evidence (2026-07-14):** operator screenshots show typed KAIRO input
    while voice surface active; inspector wired to live tier; Vitest projector +
    dispatch tests green.

- [x] **7. Establish closed-loop assurance**
  - [x] CI fast gate for contracts, unit tests, typecheck, and build
        (`.github/workflows/fast-gate.yml` → contracts + console + scaffold).
  - [x] Nightly live-evidence gate with strict pending policy
        (`.github/workflows/nightly-verify.yml` +
        `verify-with-evidence.sh --strict-pending`;
        `npm run verify:nightly:strict`).
  - [x] Include autonomy-critical tests in required verification
        (`test_voice_autonomy`, `test_command_shortcuts`, `test_kairo_conversation_turns`
        added to `run_contract_unit_tests.sh`).
  - [x] Enforce import boundaries (scaffold dependency rules in fast gate /
        nightly; added `services/axon-watch/app/domain` for strict seam).
  - [x] Hotspot-change-on-PR policy (axon-local-style diff ratchet)
        (`scripts/guardrails/check_hotspot_changes.py` + waiver register;
        wired in `fast-gate.yml` with `fetch-depth: 0`;
        `npm run verify:hotspot-changes`).

- [x] **8. Implement safe improvement capability**
  - [x] Trace and evaluation data model
        (`safe_improvement/models.py` + SQLite store).
  - [x] Verifier and regression thresholds
        (`safe_improvement/verifier.py`; failing delta blocks promotion).
  - [x] Isolated proposal execution with receipts and rollback
        (`isolated_executor.py` disposable worktree/clone + `proposal_service.py`).
  - [x] Exact approval for policy, secrets, production, and merge effects
        (fingerprint-bound `eap_*` approvals; mismatch rejected).
  - **Exit evidence (2026-07-14; sandbox upgrade 2026-07-15):**
    `tests.test_safe_improvement` + gate PASS; disposable `axon-si-…` worktree/clone
    isolation; API under `/api/safe-improvement`; docs in
    `docs/SAFE_IMPROVEMENT_SLICE.md` + `docs/SELF_IMPROVEMENT_CONTRACT.md`.

## Current findings snapshot

- Items **0–8** closed for the first safe-improvement vertical slice.
- Typing while LISTENING verified (operator screenshot with draft text).
- Autonomy inspector shows Manual until a converse tier is recorded.
- Fast gate + nightly strict workflows added under `.github/workflows/`.
- Hotspot-change gate catches non-shrinking critical edits (session `2d7c56`).
- Safe improvement executes only in disposable worktree/clone roots; exact-effect
  approval required; live bound roots stay untouched.
