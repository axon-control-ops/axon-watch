# Axon-X Working State Report — 2026-08-11

## Current branch strategy

- `dev` remains the day-to-day recovery baseline.
- Active edits are isolated on `feat/edits` before further changes.
- `preview` and `main` must not be updated until the feature branch is clean and guardrails pass.

## What was fixed and added

### Task routing and stale objective prevention

- Worker prompts now carry the exact current task ID, title, objective, workspace, and acceptance criteria.
- Stale prior-thread instructions are rejected instead of being silently treated as the current task.
- Lead planning now splits mixed work by capability:
  - Priya/front-end receives UI and screen work.
  - Marco/back-end receives service, Supabase, data cleanup, idempotency, and parent-delivery data work.
  - Dana remains coordinator/QA for cross-role work.

### Completion and synthesis gates

- Implementation workers must provide changed files, validation evidence, and commit evidence before a code-changing task can be marked complete.
- No-change/stale responses are blocked for implementation tasks.
- Dana cannot mark a parent Lead plan complete when a linked specialist failed, cancelled, or lacks delivery evidence.
- Lead synthesis now records concrete blockers instead of summarising a failed/no-evidence response as progress.
- Prior blocked synthesis receipts remain auditable but do not keep a plan stuck forever once current evidence becomes valid.

### Soren / integrations false-failure fix

- Integrations verification/reporting work no longer requires a code diff.
- Actual integrations implementation work still requires a diff, validation, and commit evidence.
- Lead synthesis uses the same implementation-vs-report classification, so a valid Soren verification receipt can satisfy the integrations role without producing files.

### Runtime and sandbox reliability

- Headless CLI environments now include user-local binaries when present.
- Sandboxed agents now receive a read-only bind mount for `~/.local/bin` and include it in PATH.
- This fixes cases where agents reported `gh: command not found` even though GitHub CLI was installed locally at `/home/vaxon/.local/bin/gh`.

### PR path

- PR #89 was repaired and remains green:
  - https://github.com/axon-control-ops/axon-watch/pull/89
  - Head: `codex/dev-working-state-20260811-runtime-guardrails`
  - Base: `dev`
  - Required `fast-gate` checks passed.

## Verification completed

- Focused routing/gate/runtime tests passed:
  - `78 passed, 26 subtests passed`
- Python compile checks passed for touched modules.
- `git diff --check` passed.
- `npm run verify:constitution` passed.
- `npm run verify:hotspot-changes` passed.
- Local GitHub CLI verified:
  - `/home/vaxon/.local/bin/gh`
  - `gh version 2.63.2`

## Still outstanding

### File-size guardrails

`npm run verify:file-sizes` still fails on unrelated dirty/in-flight files:

- `apps/console-web/src/components/conversation/ConversationSeamThreadMessage.vue`
- `apps/console-web/src/components/ide/agent-dock/AgentDockComposerToolbar.vue`
- `apps/console-web/src/composables/agent-dock/use-agent-dock-composer-setup.ts`
- `services/control-plane/app/cli_runtime/router.py`

These must be split/extracted or ratcheted intentionally before merging into protected branches.

### Live browser verification

- `5173` and control-plane APIs were verified.
- A headless browser reached Axon-X first paint.
- Full interactive post-boot browser verification is still not proven.

### Historical receipts

- Old failed worker receipts will remain as audit history.
- Affected tasks need rerun/reconcile after the patched control plane is loaded.

## Next best steps

1. Finish file-size cleanup on `feat/edits`.
2. Run the full guardrail set again:
   - targeted Python tests
   - `npm run verify:constitution`
   - `npm run verify:hotspot-changes`
   - `npm run verify:file-sizes`
   - relevant console web typecheck/test slices
3. Push `feat/edits` and open/refresh a PR into `dev`.
4. Once `dev` is green and stable, merge forward:
   - `dev` → `preview`
   - `preview` → `main`
5. Only after that, clean/reconcile stale team UI state and rerun affected DashPro tasks.

## Safety note

Do not merge this branch to `preview` or `main` until file-size guardrails are green. The branch is useful as a preserved working state, but it is not yet a release candidate.
