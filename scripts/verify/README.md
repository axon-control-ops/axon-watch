# Verification Harness

This directory holds the Lane 3 verification scaffold for Axon-Watch.

It is intentionally narrow:

- cheap CI-friendly entrypoints
- explicit pending placeholders where thin slices do not exist yet
- governance checks for ADR lifecycle discipline

## Commands

Run TEST-0 acceptance (dev stack required):

```bash
./scripts/verify/test0-workspace-smoke.sh
# alias:
npm run verify:test0
```

Run parity closure gates (post-cutover):

```bash
npm run verify:parity-a1   # P-A1 run stop/resume cross-surface parity
npm run verify:parity-a2   # P-A2 approval boundaries cross-surface parity
npm run verify:parity-a3   # P-A3 review-ready cross-surface parity
npm run verify:parity-a4   # P-A4 signal/inbox consistency cross-surface parity
npm run verify:phase-a     # Phase A E2E (P-A1 … P-A4; no full verify monolith)
npm run verify:signal-parity-matrix  # G5 composite gate (TEST-26)
npm run verify:headed-browser-smoke  # Playwright shell/operator/IDE smoke + screenshots
npm run verify:retirement-readiness  # TEST-17 (G6.4; requires dry-run + discard acks)
# see docs/PARITY_CLOSURE_ROADMAP.md for P-A2 … P-D6
```

Run the full scaffold:

```bash
python3 scripts/verify/all.py
```

Run a single check:

```bash
python3 scripts/verify/check_dependency_directions.py
python3 scripts/verify/check_adr_governance.py
python3 scripts/verify/check_dto_sizes.py --runtime-payload path/to/runtime-summary.json --watch-payload path/to/watch-summary.json
python3 scripts/verify/check_latency_budget.py runtime_summary_latency --samples-file path/to/runtime-latency.json
python3 scripts/verify/check_latency_budget.py watch_summary_latency --samples-file path/to/watch-latency.json
python3 scripts/verify/check_latency_budget.py shell_boot_readiness --samples-file path/to/shell-boot-report.json
```

## Exit Semantics

- `PASS` means the supplied evidence satisfied the rule.
- `FAIL` means the rule was violated or the scaffold itself is broken.
- `PENDING` means the check exists but future slices still need to provide code,
  payload fixtures, or timing evidence.

`PENDING` does not fail the process by default. Use `--strict-pending` once the
repo has enough thin slices to make missing evidence merge-blocking.

## Environment Variables

These variables let CI or local scripts supply evidence without patching repo
root wiring:

- `AXON_WATCH_RUNTIME_SUMMARY_PAYLOAD`
- `AXON_WATCH_WATCH_SUMMARY_PAYLOAD`
- `AXON_WATCH_SHELL_BOOT_REPORT`
- `AXON_WATCH_RUNTIME_SUMMARY_URL`
- `AXON_WATCH_WATCH_SUMMARY_URL`

`all.py` also accepts explicit CLI flags for the same inputs.

## Known Placeholder Limits

- dependency direction checks use token scanning, not language-aware import graphs yet
- shell boot readiness expects a captured browser automation report, not a browser runner
- latency budgets rely on sample files or live URLs provided by future service slices
- DTO size checks require representative payload captures from future runtime and watch slices
