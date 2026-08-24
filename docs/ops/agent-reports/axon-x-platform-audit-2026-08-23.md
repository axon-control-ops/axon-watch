# AXON-X Platform Audit — 2026-08-23

Auditor: Codex

Scope: rerun of the AXON-X constitution/platform audit, following the 2026-08-09
gap audit and 2026-08-11 follow-up. This is an evidence snapshot, not a claim
that the complete Engineering Constitution is delivered.

## Verdict

**Platform status: WARN.** The live control plane, Watch service, and console
are reachable; the initial constitution registry spine and its focused tests
are present. The audit is not clean because the mutating-route-auth gate fails,
file-size guardrails have 49 failures, and Recovery Center has four actionable
items.

## Evidence run

| Check | Result | Evidence |
| --- | --- | --- |
| Constitution implementation gate | FAIL | 8 checks pass; `mutating_methods_guarded` fails for `/api/auth/session`. |
| Focused constitution + recovery tests | PASS | 39 tests: registry, platform doctor, recovery, and recovery signals. |
| Console typecheck | PASS | `vue-tsc --noEmit` completed without diagnostics. |
| Preflight layering/DTO checks | PARTIAL | Dependency directions and DTO budgets pass. File-size guardrail fails with 49 violations. |
| Live health | PASS | `GET /api/health` and Watch health returned `status: ok`; doctor reports the control plane, Watch, and frontend listening. |
| Live recovery posture | WARN | Recovery Center reports 4 actionable items: 2 retryable and 2 failed. |
| Provider circuits | PASS | All listed circuit breakers are closed. |

## Confirmed implementation progress

The original audit’s first registry slice is materially implemented and
operationally visible:

- Durable evidence, mission, decision, capability, ADR, technical-debt, and
  platform-health registry tables are declared and exposed through the
  constitution routes.
- The constitution endpoint reports live indexed records: 1,506 evidence,
  47 missions, and 1,400 decisions.
- Evidence adapters use the real run-history shape
  (`history_ref`, `sequence`, and `transition_json`).
- The mutating-auth middleware is installed, and the doctor reports a remotely
  reachable `local_token` deployment with an operator token configured.
- Recovery Center, platform doctor, circuit breakers, and safe retry/inspect
  classifications are implemented and covered by the focused test suite.

## Findings requiring action

### P0 — restore the mutating-auth audit gate

`npm run verify:constitution` fails because `/api/auth/session` is included in
the middleware exemption list but not in the gate’s intentional exemptions.
There are both `POST` (token-to-session exchange) and `DELETE` (logout) routes
under that path. The POST route verifies the supplied operator token itself;
the DELETE route only clears an HttpOnly cookie. That can be a legitimate
session-bootstrap exception, but it must be explicit in the audit allowlist
and be covered by route-level security tests. Until then, the code and audit
policy disagree.

Recommended fix: list `/api/auth/session` once in the constitution gate’s
allowlist, document its self-authentication constraint, and add tests for
invalid login tokens, cross-origin mutation rejection, and logout behavior.

### P1 — reduce accumulated file-size guardrail debt

The preflight gate reports **49** ratchet/hard-limit violations. The most
material concentrations are:

- console shell/composer and CSS surfaces (`shell.ts`, VAXON composer styles,
  Live Operations styles, Agent Dock);
- agent dispatch/scheduler/prompt and delivery publishing;
- runtime router/sandbox and stale-run reconciliation; and
- several large legacy test files.

This is maintainability debt rather than proof of a runtime fault, but it
prevents the standard preflight from passing. Split the hard-limit files first,
then ratchet the rest only alongside real extraction work; do not simply raise
budgets to make the audit green.

### P1 — reconcile the four current recovery items

The live Recovery Center has two safe-to-review retryables and two failures:

1. DashPro Lead run `run_0d2b18750659` was cancelled after a provider timeout;
   it has a `paused_after_restart` checkpoint and one retry remaining.
2. TPS Lead run `run_a45b7d281a8d` was cancelled after a control-plane restart;
   the cause is unknown and requires human review before retry.
3. TPS Integrations run `run_2be36ad0cc77` failed Gate 6 acceptance evidence
   for diff-budget/forbidden-path/out-of-scope policy reasons.
4. TPS Frontend run `run_9751f68f3220` failed because delivery lacked passing
   acceptance evidence.

The platform correctly distinguishes retryable work from verification failures,
but these items should be inspected/acknowledged through Recovery Center before
new autonomous dispatch is expanded.

### P2 — constitution registries are still incomplete

The following original-construction registries remain absent as first-class
stores in the Control Plane source: Knowledge, Lesson, Pattern, Risk,
Architecture, Operator Preference, and Governance. Mission checkpoints are now
route-supported, but mission dependency graphs, portfolio resource allocation,
and a complete mission-resume engine remain incomplete. Decision alternatives,
trade-offs, and confidence are also not yet uniform across all decision
producers.

## Recommended sequence

1. Repair the session-route audit allowlist and tests so
   `verify:constitution` is trustworthy again.
2. Reconcile the four live recovery items according to their existing
   authority classifications; do not bulk retry the verification failures.
3. Extract the hard-limit files blocking preflight, beginning with VAXON
   composer/Live Operations and scheduler/dispatch/delivery seams.
4. Build mission dependency and recovery links on the existing Mission,
   Decision, and Evidence registries.
5. Add the remaining knowledge/learning/governance registries only after the
   execution and recovery trace is complete.

## Commands and outcome

```text
npm run verify:constitution
  FAIL: mutating_methods_guarded (/api/auth/session exemption)

npm run verify:preflight
  PASS: dependency directions, runtime-summary DTO, watch-summary DTO
  FAIL: 49 file-size guardrail violations

npm run typecheck -w @axon-watch/console-web
  PASS

./scripts/dev/python.sh -m unittest -q \
  tests.test_constitution_registry tests.test_platform_doctor \
  tests.test_platform_recovery tests.test_platform_recovery_signals
  PASS: 39 tests

npm run doctor
  WARN: 4 recovery items; core services listening; provider circuits closed
```

Confidence: 9/10
