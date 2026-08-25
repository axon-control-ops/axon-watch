# Integrations continuous shift retry — 2026-08-25

- owner: integrations (Quinn)
- prior failure: `WARNING: proceeding, even though we could not create PATH aliases: CODEX_HOME points to "/run/axon-agent-home/.codex", but that path does…` (environment dispatch warning; delivery also blocked on `output/python-bootstrap/requirements.sha256` vs `**/output/**` private-material glob)
- scope: bounded retry — connectors/watch bootstrap wiring, clear private-company delivery blocker, attach `npm test` stdout receipts

## Root cause triage

| Check | Result | Evidence |
| --- | --- | --- |
| CODEX_HOME PATH-alias warning | Not integrations-owned | Lead retry (`lead-continuous-shift-retry-2026-08-25.md`) root-caused missing `generated_home/.codex` in `agent_sandbox_material.py` → Reed (backend) |
| Private-company delivery block | Fixed (integrations) | `ensure-python-deps.sh` now writes stamp to `scripts/.cache/python-bootstrap/`; migrates legacy `output/python-bootstrap/requirements.sha256`; `.gitignore` ignores `scripts/.cache/` |
| Legacy stamp on disk | Cleared | No files under `output/python-bootstrap/`; glob search empty |
| Bootstrap guard | Pass | `check_python_bootstrap_stamp.py` → `PASS: python bootstrap stamp stays outside output/ and scripts/.cache/ is ignored` |

## Code changed this shift

1. **`scripts/dev/ensure-python-deps.sh`** — stamp dir moved to `scripts/.cache/python-bootstrap`; legacy `output/` migration; inline guard via `check_python_bootstrap_stamp.py` on every run
2. **`scripts/verify/check_python_bootstrap_stamp.py`** — regression guard that stamp config stays out of `output/` and cache dir is gitignored
3. **`.gitignore`** — `scripts/.cache/` ignore entry (present before this retry; verified by guard)

## Commands run

```text
axon-agent-terminal-job --workspace workspace_axon_watch -- ./scripts/dev/python.sh scripts/verify/check_python_bootstrap_stamp.py
  → job agent-job-b0250d51718a, exit_code=0 (2026-08-25T19:45:06Z)
  → PASS: python bootstrap stamp stays outside output/ and scripts/.cache/ is ignored

axon-agent-terminal-job --workspace workspace_axon_watch -- npm test
  → job agent-job-37084713a034, exit_code=0 (2026-08-25T19:45:39Z)
  → Test Files 356 passed (356); Tests 1932 passed (1932); Duration 27.67s
```

Prior attempt in this worker checkout failed (`vitest: not found`) because isolated checkout lacks installed node_modules; real-workspace jobs above are authoritative. Run id for this retry: `run_bcd10a1d5ca7`.

## Acceptance evidence

```text
acceptance=pass · intent=integrations_continuous_shift_retry · actor=quinn
summary=Retried bounded integrations shift; cleared private-company delivery blocker by moving python bootstrap stamp from output/ to scripts/.cache/; wired inline guard; npm test green in real workspace (356 files / 1932 tests). CODEX_HOME PATH-alias fix remains Reed-owned.
receipt=docs/ops/agent-reports/integrations-continuous-shift-retry-2026-08-25.md
```

## Blockers / Lead next

- **Reed:** Materialize `generated_home/.codex` in sandbox home policy to close CODEX_HOME PATH-alias warning at source.
- **Delivery:** Safe to retry worker delivery once this diff lands — changed paths no longer include `output/**`.
- **Fast Gate:** Not probed this turn (no push requested; `GH_TOKEN` still missing per Lead retry).
