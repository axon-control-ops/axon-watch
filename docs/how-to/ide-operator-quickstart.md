# IDE operator quick start — assigning people and staying in control

**For:** the person operating the Axon-X IDE.
**Updated:** 2026-08-22 after the TPS routing and privacy audit.

This is the practical guide for the screen with the team on the left, files in the middle, and agent conversations on the right.

## The one rule to remember

You set the outcome and approve meaningful risk. Agents investigate, make bounded changes when you explicitly permit it, and return evidence. A status badge is a prompt to inspect evidence, not proof that work succeeded.

```text
You choose priority and approve risk
  → Noor / the Lead turns it into a bounded plan
    → specialist does one owned piece of work
      → Lead checks the result and reports back
        → you decide the next move
```

## What each person is for

| Person / role | Use them for | Do not expect them to do |
| --- | --- | --- |
| **Noor / Lead** | Break a goal into owned tasks, coordinate people, review a specialist handoff, and bring decisions back to you | Quietly ship an important or risky change without your approval |
| **Blair / Watcher** | Diagnose signals, CI, health, connector, quota, and runtime problems; gather evidence for recovery | Edit the product as a substitute for the owning frontend/backend specialist |
| **Frontend** | Console/UI behaviour, browser evidence, layout and interaction fixes | Own API, database, or connector repairs |
| **Backend** | API, control-plane, persistence, and server-side behaviour | Decide business priority or make broad UI changes |
| **Integrations** | Email, third-party services, tokens, and connector wiring | Treat a missing credential as an implementation bug |
| **You / operator** | Priority, scope, sensitive actions, retry/ship/rollback decisions | Reproduce an agent's technical work in chat before assigning it |

The green/amber role labels mean **current operational state**, not seniority. `BUSY` means a shift is already active. `ACTION NEEDED` means there is a decision or recovery item for you; it is not permission to press every button.

## Daily five-minute start

1. Open `http://127.0.0.1:4173`. Use IDE preview `:5173` only when developing the console.
2. Read **Attention** and the workspace team card. Resolve the highest-risk item first.
3. Check runtime status. For an empty shell use `axonhealth`; use `axonrevive` only for an empty/hung shell, then refresh.
4. Pick one outcome: diagnosis, plan, bounded change, verification, or a decision for you. Do not combine all five in one vague message.
5. End by reading the Lead handoff: changed, verified, blocked, and the one decision that belongs to you.

## How to assign Blair safely

Use **Blair** when the question is “what happened?” or “what evidence do we need before retrying?” Examples: a failed shift, connector warning, provider timeout, CI failure, missing report, or an unfamiliar error.

1. Read the failure title, affected agent, and last handoff.
2. Choose **Assign Blair to diagnose** when you need facts. This creates a narrow diagnosis task; it does **not** silently rerun Noor or the failed worker.
3. Ask Blair for a receipt: cause, evidence examined, whether retry is safe, and the exact next owner.
4. For `timeout` or `rate limit`, wait and make at most one bounded retry. For worktree, permissions, or writable-scope issues, do not retry repeatedly: repair the owning runtime/configuration first. For `unknown`, preserve evidence and ask Noor/you for a decision. If work is complete but unverified, assign verification, not another implementation turn.
5. Choose **Dismiss — already recovered** only when you can point to a succeeding run, health check, or other evidence. Dismiss acknowledges; it does not repair.

Use **Open decision in composer** when recovery needs your judgement. It opens an editable draft and does not itself launch a task. Example:

> Blair found a provider timeout. Wait 15 minutes, retry the backend task once, and return the verifier receipt to Noor. Do not change deployment settings.

## How to use Noor / the Lead

Use Noor when a goal involves more than one person, competing priorities, or a result that must be reviewed before you act. Give Noor a concrete charter:

> Noor: restore the TPS email follow-up flow. First ask Blair whether the signal is current. Then assign the smallest appropriate owner. Do not send email, change credentials, or deploy. Return owner, scope, verification, and the decision you need from me.

For one small, clearly owned repair, talk directly to the specialist. For a cross-team effort, ask Noor to plan/fan out and wait for the Lead roll-up rather than micromanaging every agent tab.

## Consultative mode versus Full Access

| Mode | Use it for | Do not assume |
| --- | --- | --- |
| **Consultative** | Explain, inspect context, plan, identify the owner, and ask for evidence | It can edit files or run the verification needed to prove a fix |
| **Full Access** | One bounded implementation or diagnosis in the selected workspace, with an explicit expected result and proof | It permits an open-ended cleanup, deployment, credential change, or retry loop |

Before enabling Full Access, state all four: **goal, allowed scope, forbidden actions, and proof**. Example:

> In `apps/console-web` only, fix the named TypeScript error. Do not change authentication, deployment, or unrelated UI. Run the focused typecheck and report changed files and output.

Keep consultative mode for recovery triage, unclear failures, production incidents, and tasks touching secrets, payment, customer communication, or deployment until you have made an explicit decision. Stop a run if its scope expands; create a new bounded task instead.

## Reading the agent dock

- **Tabs** are separate people/threads. A message in Blair's tab has not assigned Noor.
- **Tool activity** proves an attempt, not success. Read the final receipt and verification output.
- **Waiting approval** means a decision boundary. Review effect and scope before approving; do not approve merely to clear a badge.
- **Stop** ends the active agent turn. Use it when scope widens or a sensitive action is imminent.
- **Instructions** turns a rough draft into a structured goal/scope/steps message; it does not grant execution permission.

### Decision cards are not the chat composer

Use the radio button and **Continue** on the current decision card when answering
a numbered decision. Do not type only `1`, `2`, or another option number into the
free-text composer. A composer message is not bound to the card's question ID.
The audited control-plane source fails closed on a bare single-digit composer
message once that build is loaded; the full action in words is still the safest
fallback.

Do not ask a Lead to “route the task” without restating the concrete goal. A
named handoff must include the owner, goal, allowed scope, forbidden actions,
and proof. The Lead must not recover an arbitrary older prompt from thread
history, assign the follow-up back to itself, or claim a handoff without a real
task/run receipt.

### What the status counters mean

The runtime summary can omit background employee shifts while the scheduler
still counts a paused employee run. That is not automatically a contradiction:
inspect the run ledger and `employee_role` before concluding that state is
stale. `paused` is still non-terminal; `completed`, `failed`, and `cancelled`
are terminal.

## Current operating limits

At this handbook update, use Axon-X as a **supervised** operator surface:

- Service health only proves the processes answer. Connector counts, paused employee runs, failed delivery cards, and the task ledger must be checked separately.
- The worktree contains uncommitted operational, auth, recovery, and IDE changes; it is not a clean release baseline.
- Do not call Full verification green unless the current checkout has fresh receipts for the full verification command, console typechecking, Vault/auth checks, file-size guardrails, platform diagnostics, and browser smoke.
- Legacy `:7734` remains the documented fallback for unmigrated capabilities.

Use the console to inspect, plan, assign diagnosis, and make narrow reviewed changes. Do not rely on a green health card alone for broad autonomous work or irreversible operations.

## A good operator message template

```text
Owner: [Blair / Noor / Frontend / Backend / Integrations]
Goal: [one observable outcome]
Scope: [workspace, files or system allowed]
Do not: [deployment, secrets, email sending, unrelated changes]
Proof: [specific test, health endpoint, screenshot, or receipt]
Escalate to me if: [risk/decision boundary]
```

Example:

```text
Owner: Blair
Goal: explain why Noor's last shift failed and whether one retry is safe.
Scope: inspect the run, recovery receipt, health, and relevant logs only.
Do not: retry Noor, edit files, change credentials, or restart services.
Proof: cause, evidence paths, retry recommendation, and next owner.
Escalate to me if the cause is unknown, involves a worktree, or touches data.
```

This keeps you in command while giving the right agent enough room to do useful work.
