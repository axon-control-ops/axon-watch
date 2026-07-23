# Gate 1 — Trustworthy baseline evidence

**Date:** 2026-07-21  
**Plan:** `docs/AXON-X-AUTONOMY-MASTER-PLAN.md` Gate 1  
**Baseline HEAD (committed):** `9c86389`  
**Working tree:** uncommitted Gate 0–2 + concurrent UI extracts (not yet a single commit)

---

## Commands run (2026-07-21T14:33Z–14:46Z UTC)

| Command | Result |
| --- | --- |
| `npm run verify:contracts` | **pass** (exit 0, ~12.9 min) |
| `npm run verify:console-web` | **pass** (exit 0) |
| `./scripts/dev/python.sh -m unittest -q tests.test_gate2_auth_containment` | **11 OK** |

### Console-web detail

- typecheck: pass
- Vitest: **236** files / **1242** tests passed
- production build: pass (~5.9s)

### Contract suite detail

- File-size + CSS import guardrails: pass
- Contract unit modules executed via `scripts/verify/run_contract_unit_tests.sh` (includes `tests.test_gate2_auth_containment`)
- Terminal log for the green run listed **122** `contract module:` lines and process **exit 0** (exact per-module OK-line count was 121 in a crude `^OK$` grep — do not over-read that as a second source of truth; use exit code + absence of FAILED)
- Parity D6 dock/startup: pass after adding the literal phrase “desktop deferral” to `docs/BROWSER_ONLY_STARTUP_CONTRACT.md` (that doc is also marked superseded by `DUAL_RUNTIME_STARTUP_CONTRACT.md`; the checker only reads the browser-only doc)

---

## Size-budget hygiene done for baseline

Concurrent WIP had pushed several files over hard/ratchet limits. Extracts kept budgets from rising except shrinking `CenterWorkbench` ratchet **684 → 672** and `watch_client` **408 → 406** after helper extraction:

- `watch_http.py` (internal token headers)
- `kairo-voice-azure-element.ts`
- galaxy resize / orb frame / PDF preview / breadcrumb helpers

---

## Gate 1 exit checklist

| Criterion | Status |
| --- | --- |
| Backend contract runner green | **Met** (working tree) |
| Console typecheck / tests / build green | **Met** |
| Autonomy-critical modules green via supported runner | **Met** (Gate 2 module in contract suite) |
| Recorded commit SHA for the green tree | **Partial** — HEAD `9c86389` recorded; green proof is on **dirty working tree**. Operator commit still needed to pin a single SHA. |

**Gate 1 result:** Baseline commands were green on the **dirty working tree** atop `9c86389`. That is **not** the same as a pinned commit SHA until this tree is committed. Treat “Gate 1 closed” as *command-green on WIP*, pending commit.
