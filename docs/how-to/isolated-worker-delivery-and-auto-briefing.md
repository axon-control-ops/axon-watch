# Isolated worker delivery and the morning AUTO briefing

Use this page when company agents worked while you were away, when an isolated
worker says it finished, or before asking a Lead to commit, push, merge, or run
an OTA.

## The one rule to remember

An isolated worker never copies files into the real dirty checkout. It starts
from a committed baseline, makes a bounded change, proves it, and publishes that
change on a worker branch/draft PR. Git—not manual file copying—is the handoff.

This separation prevents two agents from overwriting each other. It also means
an isolated worker cannot review or commit uncommitted files that existed only
in the host checkout before its shift.

## The normal delivery lifecycle

1. **Assign one bounded objective.** Include the user-visible outcome, expected
   paths, and validation commands. Do not combine implementation and OTA.
2. **Worker isolation is created.** The worker receives the committed baseline
   plus its task ID, objective, acceptance criteria, role scope, and allowed
   paths.
3. **Worker implements and validates.** A code task cannot pass with no changed
   files. A verification task cannot pass without command evidence.
4. **Axon-X checks the delivery.** Changed files must map to the objective;
   validation and completion receipts must exist.
5. **The publisher creates or updates a worker branch and draft PR.** The draft
   PR is the durable bridge out of isolation. A chat statement is not delivery.
6. **Review the PR, not the disposable directory.** Confirm objective, files,
   commit, checks, and base branch all match.
7. **Merge only a green, correctly scoped PR.** The integration branch receives
   the proven commit through GitHub. Do not copy the worker files by hand.
8. **Sync the real checkout.** Only with a clean host tree, fetch and update the
   integration branch. If the host tree is dirty, first classify and commit its
   changes on separate feature branches; never pull/merge over unknown WIP.
9. **Run release operations separately.** OTA, migrations, and production
   actions require a clean tree, exact commit, green checks, explicit target,
   and a terminal receipt.

## Morning checklist after leaving AUTO on

Treat the briefing as an index. Verify the underlying receipts before acting.

1. Run `axonhealth`; stop if control plane, watch, or console is unhealthy.
2. Open the company panel. A historical red badge is not proof of a current
   blocker; check whether an active run or open task still exists.
3. Read the Lead rollup and record each claimed task ID, run ID, branch, PR,
   commit, validation result, and deployment receipt.
4. Open every draft PR claimed as delivery. Confirm its title/objective, files,
   commits, base branch, and latest required checks.
5. Reject these false-success patterns:
   - worker responded, but no objective-matching diff exists;
   - verification says evidence is missing;
   - PR contains only a report when product changes were requested;
   - worker inspected `/tmp/axon-si-run-*` while asked about existing host WIP;
   - checks are queued/pending but the rollup says ready;
   - an OTA receipt has no update group/channel/commit.
6. Check the real workspace with `git status --short --branch`. If dirty, do not
   ask a continuous worker to "commit everything." Use the audited operator
   delivery lane and explicit paths after reviewing ownership.
7. Merge proven worker PRs one at a time. Re-run relevant checks after conflicts
   or integration changes.
8. Reconcile stale tasks only after recording why each is obsolete. Preserve
   genuine unfinished product tasks.
9. Start the next company task only when the workspace and ledger tell the same
   story.

## Clean host versus dirty host

### Clean host

Merge the green worker PR, then update the real checkout normally. Confirm the
checkout is clean and at the expected commit before the next task.

### Dirty host

Do not merge, pull, reset, stash-pop, or run a blind `git add -A`. Instead:

1. List all changed and untracked paths.
2. Group them by feature and originating task/agent.
3. Review each group’s diff and identify generated files, secrets, or unrelated
   artifacts.
4. Run targeted validation for that group.
5. Commit only that group on a feature branch using explicit paths.
6. Repeat until every path is owned or intentionally discarded with operator
   approval.
7. Push/open PRs, obtain green checks, merge, and then make the host clean.

Axon-X intentionally refuses a blind commit when a tree spans many files and
top-level areas. `commit all` is an explicit override, not a routine recovery
command.

## What belongs in each lane

| Work | Correct lane |
|---|---|
| New bounded UI/API/CI implementation | Isolated company worker |
| Read-only health observation | Watcher |
| Existing host dirty-tree review or consolidation | Audited operator/real-worktree lane |
| Commit/push explicit reviewed host paths | Workspace-git/operator lane |
| Merge a green PR | Operator merge lane |
| OTA, database push, or production action | Separate approved terminal-job lane |

## DashPro worked recovery example (12 August 2026)

The real DashPro checkout had 29 modified files across messaging, workflows,
tests, and a migration. Dana’s isolated Lead run could not see that WIP and
opened draft PR #87 containing documentation only. The safe recovery was:

1. Block OTA and leave PR #87 draft/unmerged.
2. Preserve the real checkout unchanged.
3. Cancel five stale/misrouted open ledger tasks with an operator consolidation
   reason; preserve the genuine frontend messaging task.
4. Add guards so host-WIP delivery requests cannot be delegated into isolation,
   out-of-scope control-plane work cannot reach product agents, and verification
   cannot pass without evidence.
5. Continue by grouping and proving the 29 host changes before any commit.

## Copy-paste prompts

Safe implementation prompt:

```text
Implement <one outcome> in <workspace>. Expected paths: <paths>. Acceptance:
<criteria>. Run <commands>. Do not deploy. Report changed files, validation,
worker branch, draft PR, and commit hash.
```

Safe morning Lead prompt:

```text
Summarise only receipt-backed work since the last briefing. For each item give
task ID, run ID, objective, changed files, validation, branch, PR, commit, and
current checks. Label missing evidence BLOCKED. Do not merge, deploy, retry, or
claim completion from a worker response alone.
```

Do not send this to a continuous worker when the real host is dirty:

```text
Review the existing working tree, commit everything, push, and run OTA.
```

