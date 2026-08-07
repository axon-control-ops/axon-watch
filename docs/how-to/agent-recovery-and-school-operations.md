# Recovering a stuck agent and running School Operations Phase 1

**Updated:** 2026-08-07

This chapter answers two practical questions:

1. What should happen when an Axon-X employee agent is stuck or failed?
2. How should the first Young Eagles homework workflow operate safely?

It is written for an operator. VAXON should explain the reason and recommend
the next safe action; it should not turn an Ask-mode conversation into work or
retry a failure blindly.

---

## A stuck agent: read the reason before retrying

Open the agent's report and use the exact failure text to choose the next step.
The label **FAILED** tells you the outcome, not the cause.

| What the report says | What it means | Your next action | What VAXON should do |
| --- | --- | --- | --- |
| `control-plane restart`, `cancelled after restart`, or a run vanished while the service restarted | The platform interrupted the shift; it is not evidence that the agent's work failed. | Wait for health to return, then check that the task is **Open**, not stuck **Leased**. Retry only after that. | Preserve the cancelled-run receipt; release the exact interrupted lease without using up an attempt; explain that the retry is safe. |
| `sandbox mount`, `approved writable root`, or read-only filesystem | The worker did not get the workspace/scope it needed. | Do not keep pressing **Try again**. Report the exact error or ask VAXON to diagnose it. | Classify it as a runtime/configuration fault; repair or route the task to an editing specialist with a narrow writable scope, then retry once. |
| `consultative-only`, no tool access, or no files changed | The task was sent to a conversational/observer context rather than an execution-capable specialist. | Keep **Ask** for advice; use **Assign** or an execution task for implementation. | Explain the distinction, preserve the advice as a plan, and route the bounded implementation to the right role. |
| `Confidence: N/10` missing, missing receipt, or Gate 6/critical review failure | The evidence is incomplete or the result is not trustworthy yet. | Review the named check and the changed files. Do not approve it just to clear the card. | State the missing proof, request a concrete correction, and retry only when the evidence requirement is satisfiable. |
| missing credential, approval, parent decision, or external service failure | An authorised human or external system must act. | Supply the missing approval/credential through the approved channel, or decide to stop the task. | Mark the task `awaiting_input`/`waiting_external`, name exactly what is needed, and avoid speculative retries. |
| a real test/assertion failure | The implementation needs repair. | Use **Explain** first if the failure is unclear; use **Try again** only after the agent identifies a changed, testable fix. | Summarise the failing check, propose a bounded fix and test, then hand it to the owning specialist. |

### Restart decision: do not restart by default

Run `axonhealth` first. If it reports healthy and the UI is merely showing a
failed agent card, restarting the control plane is usually the wrong first
action: it interrupts other in-flight work.

Restart only when one of these is true:

- health/API is unavailable or the shell is genuinely empty/hung;
- a deployed backend change explicitly needs a reload; or
- VAXON's diagnosis identifies a control-plane fault and there are no active
  shifts that must be allowed to finish.

On this host:

```bash
axonhealth       # inspect first
axonrestart      # controlled soft restart when the service is the problem
axonrevive       # only for a wedged/unavailable runtime
```

After a restart, wait for `axonhealth` to return healthy, refresh the browser,
then verify the affected task's state before retrying it. A restart-interrupted
role task should return to **Open** with its retry budget intact. If it remains
**Leased**, stop retrying and report the task ID and run ID to VAXON: that is a
runtime recovery defect, not operator error.

### VAXON's recovery contract

For every failed or stuck employee, VAXON should provide a short report in this
order:

1. **What happened** — the exact class of failure in plain language.
2. **What changed / did not change** — files, tests, and receipts; never claim
   evidence it did not obtain.
3. **Who acts next** — operator, named specialist, or external owner.
4. **One safe next action** — explain, repair, request input, or retry.
5. **Confidence: N/10** — only after the summary.

It should not create a loop of retries. Two genuine, corrected attempts are a
reasonable escalation point; infrastructure interruptions do not count as a
genuine agent attempt.

---

## Young Eagles Phase 1: daily homework with human approval

Phase 1 is deliberately narrow: publish daily homework safely. It is not an
authorisation for an AI to issue grades, send parent messages, or make child
welfare decisions on its own.

### Daily operating flow

1. The teacher prepares the room-specific homework in **Teacher Workspace** and
   selects **Submit homework**.
2. The post enters **pending approval**. Parents must not receive it at this
   stage.
3. The principal or authorised administrator checks age group, wording, date,
   learning activity, and any attached practice material.
4. Approval changes the post to **posted** for the relevant room/age group.
5. At close of day, the team records what was posted and prepares the next
   draft; missed posts go onto the next opening checklist.

The existing Young Eagles Command Centre implementation follows this shape:
homework posts create approval entries, and an approved homework entry is
published for its room. Its current test suite covers syntax, role navigation,
login/RBAC, API behaviour, and the related operations flows. It does **not**
prove that an AI-generated message is educationally appropriate; the approving
human remains accountable.

### What Imani may do in this phase

Imani can act as a school-operations coordinator:

- prepare drafts from the teacher's supplied lesson plan;
- remind staff about missing homework, approvals, and weekly updates;
- prepare a practice-test or report draft from approved source records;
- summarise trends for a teacher, principal, or parent meeting; and
- suggest aftercare activities from the approved programme.

Imani must not, without the named human approval path:

- publish homework or parent communications;
- assign final marks, diagnose a child, or make promotion/disciplinary decisions;
- expose another child's information in a report or message; or
- make safety, pickup, medical, or safeguarding decisions.

### Ready-for-Phase-2 checklist

Do not automate grading, reports, parent updates, or aftercare decisions until
the centre has named owners, approval checkpoints, record-retention rules, and
a clear parent escalation route for each of them. Start with one supervised
room and review a week's audit trail before extending the workflow.
