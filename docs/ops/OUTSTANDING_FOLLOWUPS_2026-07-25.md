# Outstanding follow-ups (2026-07-25)

Decision record for items that remain after IDE/agent-card work on
`feat/mission-control-holographic`. These are **not** silent merges into HEAD.

## 4. VAXON Phase 1 reliability (`feat/vaxon-phase1-reliability`)

**Decision: do not merge into this branch yet.**

- Branch tip: `96ec10a` / `6a2e40e` (hands-free voice reliability + gate fixes).
- Not in current HEAD ancestry; merge-base is older (`d219c69` era).
- Checklist on that branch (`docs/VAXON_DESKTOP_VOICE_RELIABILITY_CHECKLIST.md`) still
  requires a human 30-minute packaged Tauri soak before continuous reliability claims.
- **Merge path:** open a dedicated PR into `dev` (or this branch after soak) with:
  1. Packaged voice prove harness green on target host.
  2. Operator soak checklist rows marked with date/operator.
  3. Fast Gate green on the merge commit.
- Until then, treat Phase 1 as an integration candidate, not shipped product.

## 5. Parked later-phase (`feat/parked-later-phase`)

**Decision: keep as WIP. Do not promote.**

Branch tip `d2f91b7` parks wake-word scaffolding, Android app shell, streaming STT
placeholder, mission memory, and device enrollment. Evidence gates before any merge:

| Claim | Required evidence |
|---|---|
| Wake-word | Real engine selection doc + on-device false-accept/reject notes |
| Streaming STT | Non-placeholder adapter + latency/accuracy soak |
| Android background | `apps/vaxon-android/docs/ANDROID_BACKGROUND_WAKE_EVIDENCE.md` filled |
| Push / device enrollment | Control-plane routes + enrollment soak + security review |
| Mission memory | Persistence tests + privacy/retention note |

Until those receipts exist, language must stay “parked WIP,” not “shipped.”

## 6. Literal Cursor IDE parity

**Decision: separate follow-on project.**

Current IDE work on this branch is **stylistic alignment** only (Cursor-inspired Monaco
theme, CSV Table/Raw, minimap scale, typed tab badges). It is **not** Cursor product
parity (extensions, AI chat, multi-root workspace UX, full editor chrome, etc.).

Track literal parity as its own planning slice / ADR when product wants it; do not
expand holographic mission-control PRs into that scope.
