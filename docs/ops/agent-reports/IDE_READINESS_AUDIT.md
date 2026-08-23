# IDE Readiness Audit — Axon-X Console (axon-watch)

**Date:** 2026-08-13
**Scope:** `apps/console-web` IDE mode (`layoutMode === 'ide'`)
**Goal:** Stabilize IDE before Teacher-X development
**Status:** Partial readiness — high-impact dead-ends addressed; product decisions remain

---

## 1. IDE Surface Inventory

| Surface | Entry | Primary flows |
|---------|-------|---------------|
| Console `/` | TopBar → IDE toggle | Editor, explorer, agent dock, terminal |
| Activity bar | Left sidebar icons | Team, Explorer, Search, Git, Run, Terminal/Agent stubs |
| Center workbench | Monaco + terminal dock | Open/edit/save files, problems/output/logs |
| Agent dock | Right rail | Composer, thread tabs, approvals, employee retry |
| App surfaces | `/settings`, `/vault`, `/data`, `/skills` | Leave IDE context (full shell swap) |
| Interrupt strip | Top of IDE center | Approvals, degraded runtime, stop/resume run |

**Stack:** Vue 3 SPA (`console-web`), Pinia shell store, pathname routing (`app-surface-route.ts`).
**Native parity:** N/A in this repo — IDE is web-only; `console-desktop` wraps the same SPA.

---

## 2. Triage Summary

### Blockers (fixed this pass)

| Issue | Impact | Fix |
|-------|--------|-----|
| **Problems panel invisible when terminal collapsed** | Save/runtime/briefing/run errors only in hidden PROBLEMS tab | PROBLEMS status bar chip, quick-guide CTA, `revealIdeWorkbenchProblems()` |
| **Empty editor dead-end** | No file open → blank workbench | `CenterWorkbenchEmptyEditor` with progressive steps |
| **Debug ingest spam (`127.0.0.1:7706/ingest`)** | 9× `ERR_CONNECTION_REFUSED` in DevTools on every voice/stream action | Removed all `#region agent log` fetch blocks from shell + voice modules |
| **Three.js clearColor/clearAlpha warning** | Console error on brain-galaxy init | `WebGLRenderer({ alpha: false })` — opaque galaxy background |

### Console ports (corrected)

| Port | Role |
|------|------|
| **5173** | Vite **source edit window** (`scripts/ops/run-5173.sh`) — user's screenshot |
| **4173** | Always-on **daily driver** (systemd / `scripts/dev/up.sh`) |

Both share control-plane `:8787`. Do not conflate them in smoke docs.

### Major (existing mitigations; monitor)

| Issue | Current mitigation | Gap |
|-------|-------------------|-----|
| Agent/Terminal activity-bar stubs | Redirect copy + CTAs to right dock / center terminal | Can feel like empty panel until user learns pattern |
| Settings gear leaves IDE | Full navigation to `/settings` | No inline settings drawer |
| Hidden bound workspaces | TopBar picker / API only | `workspace_axon_watch` not in sidebar catalog |
| Agent dock legacy parity | Contract tests + inline notices | Thread-deck richness vs axon-local |
| IDE mode throttles live refresh | Background runtime summary only | Presence/briefing can lag until mode switch |

### Minor / deferred

| Issue | Reason deferred |
|-------|-----------------|
| Cursor IDE parity (command palette, preview tabs, split editor) | Explicit non-goals in `CURSOR_IDE_PARITY_PLAN.md` |
| Constitution explorer stubs | Product scope — read-only capability/evidence panels not built |
| Fan-out → auto-open IDE threads | Autonomy evidence log — manual follow-through acceptable v1 |
| Doc drift in starter guide | Guide describes old right-dock layout; code uses AgentDock-only |
| Headed smoke limited to layout toggle | Extend to explorer open, agent send, PTY, consent flows |

### Errors / warnings posture (verified 2026-08-13)

- **298 vitest tests** pass on touched IDE + voice modules (not full repo typecheck).
- **Live smoke on `:5173`:** 7/7 checks pass — see `.local/verify/ide-live-smoke/ide-live-smoke-report.json`
- **Prior audit error:** claimed "no console noise" — missed debug `fetch()` to `:7706/ingest` (now removed).
- **`AlertModal`** does not exist in axon-watch (DashPro rule does not apply here).
- **ScriptProcessorNode deprecation** in `cloud-audio-capture.ts` — browser warning only; not fixed this pass.

---

## 3. Fixes Implemented (this pass)

1. **`buildIdeEditorStatusProblemsChip`** — surfaces workbench problem count when terminal is hidden.
2. **`revealIdeWorkbenchProblems()`** — shell action + token; WorkbenchTerminalDock switches to PROBLEMS tab.
3. **Quick guide** — `show-problems` action when `problemCount > 0` and terminal collapsed.
4. **`CenterWorkbenchEmptyEditor`** — welcome state with clickable steps and keyboard hints.
5. **Tests** — status chip, quick guide, empty editor view, chrome slice, CSS contract.
6. **Empty editor “New file”** — `requestIdeExplorerInlineCreate('file')` opens Explorer and starts inline create; non-actionable steps show blocking copy instead of silent no-ops.
7. **Agent dispatch guardrails** — per-run writable Cursor `cli-config.json` / `agent-cli-state.json` copies (fixes `EBUSY` on shared ro-bind mounts); `validate_agent_dispatch_preflight()` fails fast on missing `bwrap`/`rg`; `./scripts/dev/check-health.sh` probes both.
8. **Team Panel dead clicks** — `1 FAILED` badge / alert hint open the failed teammate's dock and focus the composer; failure beat is a button that submits **Try again** / **Continue**; **Review decision →** seeds the composer with the pending decision draft (operator still sends).
9. **Young Eagles Frontend write scope** — `_ops_frontend_write_paths_for_workspace()` grants Frontend `command-centre` + intersected `output/*` when the workspace contract includes `command-centre/` (fixes consultative-only worker runs despite operator Full Access on the Lead thread).

### Control-plane agent error root causes (2026-08-13)

| Symptom | Root cause | Fix | Notes |
|---------|------------|-----|-------|
| `EBUSY` renaming `cli-config.json` | Host Cursor state read-only bind-mounted into shared agent home | Per-run writable copies in `materialize_cursor_hook_policy()` | Observed on DashPro + Young Eagles worker runs |
| Completion gate — no changed files | Worker shift produced no deliverable diff | Retry after sandbox + write-scope fixes; gate clears on successful shift with file changes | **Not an IDE bug** — persisted `last_outcome=failed` until retry succeeds |
| Frontend consultative on Young Eagles | Role defaults (`apps/`, `src/…`) intersected empty with contract (`command-centre/`, `output/…`) | Ops frontend write-path expansion in `execution_policy.py` | **Operator Full Access in composer does not propagate** to Lead-decomposed worker runs |
| `ripgrep (rg) is required…` | Self-hosted runner missing `rg` in PATH | Install `ripgrep` on runner host; preflight blocks dispatch early | DashPro runner ops — not fixed in this repo |

---

## 4. Progressive UX Coverage (post-fix)

| Flow | Empty state | Loading | Error | Recovery |
|------|-------------|---------|-------|----------|
| Open file | ✅ Empty editor guide | File tree loading | SEARCH ERR chip + quick guide | Retry in Search panel |
| Save file | — | — | Problems tab + chip | Edit and save again |
| Agent shift fail | Team roster + dock banner | Streaming chips | Badge/hint opens dock; beat submits Try again / Continue | Quick guide + review strip |
| Connectors down | Run panel notice | Probe loading | WATCH/LEGACY chips | Open connectors |
| Approvals | Interrupt strip + dock | — | Attention panel | Approve/reject in dock |
| Run lifecycle | Terminal auto-peek | Executing chips | Problems + composer footer | Stop/resume/continue |
| No workspace | Empty editor guide | Bootstrap | TopBar picker | Select workspace |

---

## 5. Smoke Checklist

### Automated (run 2026-08-13 against live `:5173`)

```bash
node scripts/verify/ide-live-smoke.mjs --port 5173
# Requires: npm install -D playwright -w @axon-watch/console-web && npx playwright install chromium
```

| Check | Result |
|-------|--------|
| HTTP boot | PASS |
| Shell render | PASS |
| IDE mode toggle | PASS |
| Editor surface (file open or empty guide) | PASS (file open — README persisted) |
| Agent dock | PASS |
| No `:7706/ingest` console errors | PASS |
| No Three.js clearColor errors | PASS |

**Not live-verified this pass:** PROBLEMS chip with an active error (requires inducing save/runtime failure); empty editor guide with all tabs closed (persisted README tab prevented).

### Manual (operator)

- [ ] Toggle Operator ↔ IDE — no layout break
- [ ] IDE with no file open — empty editor guide visible, Explorer step works
- [ ] Open file from Explorer — Monaco loads, save works
- [ ] Trigger save error (e.g. disconnect) — PROBLEMS chip appears, opens Problems tab
- [ ] Collapsed agent dock during streaming — AGENT chip + quick guide
- [ ] Employee failure — tap `1 FAILED` badge (opens dock) then failure beat **Try again** / **Continue**
- [ ] Pending decision — **Review decision →** seeds composer; operator sends decision
- [ ] Ctrl/Cmd+J terminal, Ctrl/Cmd+\\ agent dock
- [ ] Settings gear — confirm intentional full-page navigation (document for users)

---

## 6. Vaxon Decisions Required

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | **Teacher-X gate** | Block until smoke checklist signed off | Require manual smoke + hidden workspace catalog fix |
| 2 | **Hidden workspaces** | Add to sidebar catalog vs keep TopBar-only | Add `workspace_axon_watch` to catalog for dogfooding |
| 3 | **Settings in IDE** | Keep full-page `/settings` vs inline drawer | Defer drawer; add “Return to IDE” breadcrumb if keeping full-page |
| 4 | **Agent dock parity** | Invest in thread-deck vs accept v1 degradation | Accept v1 per parity ledger; schedule P1 dock slice separately |
| 5 | **Cursor parity claims** | ADR + honest checklist vs marketing “Cursor-like” | Follow `CURSOR_IDE_PARITY_PLAN.md` P0 honesty gate |
| 6 | **Starter guide refresh** | Update `AXON-X-STARTER-GUIDE.md` IDE section | Yes — align with activity-bar + AgentDock architecture |

---

## 7. Readiness Sign-Off

| Category | Status |
|----------|--------|
| Blocker dead-ends | **Addressed** (problems visibility, empty editor) |
| Major UX gaps | **Mitigated** — stubs/connectors/settings need product calls |
| Automated tests | **Green** (298 vitest on touched modules) |
| Live smoke `:5173` | **7/7 pass** (ingest + Three.js clean; empty guide / problems chip not induced) |
| Manual smoke | **Partial** — see §5 |
| Teacher-X start | **Not recommended** until Vaxon signs §6 + problems-chip manual proof |

**Confidence:** 6/10 for IDE v1 dogfooding (up from prior 7/10 after correcting overclaims); 4/10 for Teacher-X gate until workspace catalog + induced-error smoke complete.

---

## 8. Suggested Next PR Slices

1. Extend headed browser smoke (`scripts/verify/headed_browser_smoke.py`) — explorer + problems chip.
2. Surface hidden workspaces in IDE workspace picker.
3. Starter guide IDE section refresh.
4. Auto-open Problems tab once when new problem items appear (optional — may be noisy).
