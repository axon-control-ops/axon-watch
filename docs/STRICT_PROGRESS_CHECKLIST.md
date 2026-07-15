# Axon-X Strict Progress Checklist

**Created:** 2026-07-15
**Repo:** `/home/edp/axon-nvme/repos/axon-watch`
**Rule:** Preserve the dirty worktree. Do not reset, discard, or blame failures on the committed baseline without a clean-worktree comparison.

**Related:** `docs/AUTONOMY_RELIABILITY_TRACKER.md` (earlier slice notes). This file is the **operator-authoritative** checklist from the corrected audit summary.

## Correction of prior summary (locked)

- I overstated the Python failure. `python3 -m pytest -q` failed because it resolved the wrong app package; that does not prove the control-plane suite itself is broken. The project runner then failed because its virtualenv lacks pytest, so the intended suite is currently not runnable there.
- The frontend failures are confirmed in the current dirty worktree: `vue-tsc` reports 10 errors; Vitest reports 7 failing tests out of 715.
- `verify:contracts` is confirmed blocked by 25 file-size violations. That is a guardrail failure, not necessarily 25 runtime defects.
- The worktree has extensive uncommitted changes. Therefore, none of these failures can yet be attributed to the committed baseline or a specific earlier change.
- The autonomy findings are source-audit findings, not all runtime-reproduced defects. The strongest candidates for runtime validation are duplicate auto-dispatch, swallowed dispatch/run-state errors, and divergent KAIRO submission paths.
- “All audits complete” was too broad. We reviewed major autonomy, console, and verification surfaces; we did not exhaustively prove every path in Axon‑X.

## Status legend

| Mark  | Meaning                                                         |
| ----- | --------------------------------------------------------------- |
| `[ ]` | Not done / not proven in this tracker                           |
| `[~]` | Claimed done elsewhere; needs re-verify with exit evidence here |
| `[x]` | Done with exit evidence recorded below                          |

Update an item only when its stated evidence is attached.

---

## Strict checklist

### Foundation (0–7)

- [x] **0. Preserve the current dirty worktree**
  - Do not reset, discard, or blame failures on baseline without a clean-worktree comparison.
  - Evidence: 2026-07-15 — branch `dev`, HEAD `fb2737f78af436141da35ed5c285174d5509d666`; dirty worktree (~243 short-status lines at open); `git diff --check` clean at snapshot. No reset/discard performed.

- [x] **1. Make the test environment reproducible**
  - Document one supported Python test command and install the declared dev-test dependencies.
  - Evidence: `README.md` documents `./scripts/verify/run_contract_unit_tests.sh` (not repo-root pytest). Runner uses managed venv via `scripts/dev/ensure-python-deps.sh`.

- [x] **2. Run the supported backend test command successfully**
  - Record exact pass/fail counts.
  - Evidence: 2026-07-15 — via `npm run verify:contracts` → **365** unittest cases across **71** modules, **0** failures (`CONTRACTS_EXIT:0`).

- [x] **3. Fix the 10 confirmed console type errors**
  - Begin with canonical-contract export drift and outdated test fixtures.
  - Evidence: 2026-07-15 — starting residual was 2 (`cli_runtime` on `OperatorBriefing`); fixed by adding `CliRuntimeReadiness` to shared-types. `npm run typecheck -w @axon-watch/console-web` PASS.

- [x] **4. Fix the 7 confirmed Vitest failures**
  - Spoken-reply parsing, narration extraction, voice-playback timeout, and command-catalog expectation drift.
  - Evidence: 2026-07-15 — residual was 2 (speech-session slice move + calendar-day fixture drift). Full Vitest **735/735** PASS.

- [x] **5. Remove the two confirmed whitespace errors from `git diff --check`**
  - Evidence: 2026-07-15 — `git diff --check` clean.

- [x] **6. Bring `verify:contracts` back to green**
  - Extract oversized modules or lower code size; do **not** merely raise ratchet budgets.
  - Evidence: 2026-07-15 — extracted `catalog_identity.py` + `stream_blocks/normalize_transcript.py`; lowered ratchets to current sizes. Also fixed stale KAIRO pack patches, planning MANIFEST hash, and D2 connector-trust fixture. `npm run verify:contracts` PASS.

- [x] **7. Re-run frontend typecheck, Vitest, build, contracts, and the supported backend suite**
  - Capture results as the new baseline.
  - Evidence: see baseline log 2026-07-15 below.

### Autonomy correctness (8–15)

- [x] **8. Runtime-reproduce and instrument the suspected stale `pending_command` duplicate-dispatch flow**
  - Evidence: 2026-07-15 — TestClient runtime proof sends `health`, then `yes`
    in the same KAIRO session and asserts the follow-up cannot return a second
    `dispatch_command`. See `docs/AUTONOMY_RUNTIME_PROOFS.md`.

- [x] **9. Runtime-reproduce the health versus check health command-tier mismatch**
  - Choose and document one policy.
  - Evidence: 2026-07-15 — `health`, `check health`, `check-health`, and the
    explicit health script all resolve to read-only `reversible_auto` without
    approval. Endpoint, autonomy-tier, and shortcut tests pass.

- [x] **10. Runtime-reproduce run-finalization failures**
  - Guarantee that failed phase transitions create an operator-visible error and receipt.
  - Evidence: 2026-07-15 — isolated SQLite runtime proofs force completion
    failure and double-finalization failure. The first persists `run_failed`;
    the fallback persists `finalization_error` with `success=False`. Targeted
    autonomy set: **38/38 PASS**.

- [x] **11. Consolidate KAIRO turn submission**
  - One awaited dispatch path with consistent context, `action_tier`, routing receipt, model receipt, and error handling.
  - Evidence: 2026-07-15 — app-scoped voice registers the same
    `useKairoConversation().submitTurn` used by typed surfaces; the duplicate
    request/dispatch/error implementation was removed. Shared dispatch records
    action tier, routing receipt, and model receipt. Typecheck PASS; KAIRO
    submission/dispatch set **9/9 PASS**.

- [x] **12. Make autonomy status data-driven**
  - Remove UI literals that claim “Bounded auto” without evaluating execution access, policy, approval state, and workspace constraints.
  - Evidence: 2026-07-15 — evidence autonomy projection now combines live
    action tier, execution access, pending approvals, active run phase, and
    workspace selection. The deprecated boolean bypass was removed; **4/4**
    projector tests cover bounded, full, unknown, workspace, and approval
    gates.

- [x] **13. Make safe-next-action and approval surfaces actionable**
  - Or label them explicitly as informational.
  - Evidence: 2026-07-15 — Briefing and Galaxy Intelligence now label suggested
    actions “guidance only”; pending approvals point explicitly to actionable
    Mission Control controls. Label contract tests **2/2 PASS**.

- [x] **14. Add tests**
  - Dispatch idempotency, action-tier defense in depth, run-state transitions, KAIRO-path parity, evidence projection, and voice persistence failures.
  - Evidence: 2026-07-15 — all six themes have named frontend/backend proofs
    in `docs/AUTONOMY_TEST_COVERAGE.md`. Frontend **744/744 PASS**;
    `npm run verify:contracts` PASS with endpoint, transcript-failure,
    voice-store, and debug-gate modules in the supported runner.

- [x] **15. Remove or feature-gate debug-ingest calls**
  - Only after runtime debugging confirms they are no longer required.
  - Evidence: 2026-07-15 — no live frontend callers remain. Backend ingest and
    helper require `AXON_DEBUG_SESSION_LOG=1`; frontend helper requires a
    non-production build plus `VITE_AXON_DEBUG_SESSION_LOG=1`. Disabled API
    returns `404`; enabled append proof **2/2 PASS**.

### Assurance & platform (16–22)

- [x] **16. Establish CI**
  - PR fast gate plus nightly live-evidence gate; make autonomy-critical tests mandatory.
  - Evidence: 2026-07-15 — fast PR/push and nightly isolated live-evidence
    workflows are implemented and contract-tested; see `docs/CI_GATES.md`.
    Fast Gate run `29406066700` passed on `063cc53`. GitHub branch protection
    on `dev` now strictly requires the `fast-gate` check, applies to admins,
    and forbids force-pushes and deletions.

- [x] **17. Make PENDING verification fail in CI**
  - Or explicitly allowlist each pending metric with owner and expiry.
  - Evidence: 2026-07-15 — both fast and nightly workflows invoke the
    verification harness with `--strict-pending`; nightly additionally rejects
    fixture fallback with `--require-live-evidence`.

- [x] **18. Add dependency-direction and hotspot-change enforcement**
  - Make preflight failures blocking.
  - Evidence: 2026-07-15 — fast CI blocks on dependency directions, file-size
    ratchets, and hotspot-change ratchets. `scripts/sc` now runs
    `npm run verify:preflight`, aborts on failure, and has no quick bypass.
    CI/preflight contract and hotspot policy tests are in the supported suite.

- [ ] **19. Implement native tunnel control**
  - Resolve, migrate, or explicitly discard WhatsApp monitoring before retirement.
  - Progress: 2026-07-15 — Axon-X now owns bounded native cloudflared
    start/stop/status control with state-dir process ownership, token-safe
    arguments, and refusal to kill unmanaged processes. Vault-backed tunnel
    auth (`cloudflare_tunnel_token`) and zero-byte `cloudflared` stub skipping
    landed via PR #5. The `verify:tunnel-remote-control` gate passes. Live
    cutover is in progress: Axon-X started a managed cloudflared
    (`managed: true`), but root `cloudflared.service` (PID 2237) still needs
    `sudo systemctl disable --now cloudflared` so only Axon-X owns the tunnel.
    WhatsApp remains explicitly deferred and is still a retirement blocker.

- [x] **20. Define the actual self-improvement contract**
  - Trace store, evaluation dataset, verifier, regression thresholds, proposal workflow, isolated execution, approval, and rollback.
  - Evidence: 2026-07-15 — `docs/SELF_IMPROVEMENT_CONTRACT.md` defines all
    required subsystems, state transitions, exact-effect approval, forbidden
    real effects, default-off enablement, evidence requirements, and rollback.

- [x] **21. Implement self-improvement only after items 0–18 are green**
  - No agent may alter policy, secrets, approval rules, or production state autonomously.
  - Evidence: 2026-07-15 — items 0–18 are green, including server-side
    `fast-gate` enforcement. Safe-improvement routes remain default-off and
    require `AXON_SAFE_IMPROVEMENT_ENABLED=1`; exact-effect approvals expire,
    and policy, secret, approval-rule, and production effects cannot execute.
    The supported contract suite passed on `063cc53`.

- [ ] **22. Complete the one-week `:4173`-only dry run**
  - Sign retirement/discard acknowledgments only after all required gates pass.
  - Progress: 2026-07-15 — a fresh seven-day evidence ledger is open at
    `docs/PHASE_G6_DRY_RUN_2026-07-15.md`. Day 1 automated stack health passed;
    headed-browser and connector-parity gates now pass locally after smoke and
    acceptance repairs. Operator workflow, `:7734` attestation, and all
    signatures remain pending. No retirement acknowledgment has been inferred or
    signed.

---

## Parallel track: vision / scanned-workbook reliability

Axon-X previously missed Unit 13855 **Set A** because the workbook was image-only and the agent inventoried only Learning Unit 1 (Set B). See:

- `/home/edp/Documents/Annatjie-Level_5/13855/WHY_AXON_X_MISSED_SET_A.md`

| Item                                                | Status | Notes                                                                                                           |
| --------------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------- |
| Diagnose miss                                       | [x]    | Documented 2026-07-15                                                                                           |
| Assignment skill update (OCR/inventory-first rule)  | [x]    | `~/.claude/skills/assignment-completion/SKILL.md` — mandatory full-page inventory before answering scanned PDFs |
| Durable product/agent fix in Axon-X control plane   | [ ]    | Not shipped yet (skill-level gate only)                                                                         |
| Regression test / fixture for multi-set scanned PDF | [ ]    | Pending                                                                                                         |

---

## Baseline results log

Append dated runs here. Do not overwrite; add a new block each time.

### Template

```
### YYYY-MM-DD HH:MM
- worktree: dirty | clean-comparison
- HEAD: <sha>
- typecheck: PASS/FAIL
- vitest: N pass / N fail / N total
- build: PASS/FAIL
- verify:contracts: PASS/FAIL (details)
- backend suite: N pass / N fail / N total (command: …)
- notes:
```

### 2026-07-15 — tracker created

- Confidence stated by operator for checklist correctness: **9/10**
- Prior tracker (`AUTONOMY_RELIABILITY_TRACKER.md`) claimed items 0–8 closed on 2026-07-14; those claims are **not** auto-imported as `[x]` here until re-verified under this numbering.
- Vision product fix: **not done** at tracker creation.

### 2026-07-15 ~09:20 (dirty worktree baseline)

- worktree: dirty (preserved)
- HEAD: `fb2737f78af436141da35ed5c285174d5509d666` (+ local uncommitted fixes)
- typecheck: PASS
- vitest: 735 pass / 0 fail / 735 total
- build: PASS
- verify:contracts: PASS (file-sizes + shared-types + **365** backend unittests / 0 failures)
- backend suite: included in `verify:contracts` via `./scripts/verify/run_contract_unit_tests.sh`
- notes: residual gate debt from earlier summary was already reduced; this session closed remaining type/vitest/size/contract failures and added scanned-PDF inventory rule to assignment skill. Items **8–22** still open under this tracker.
