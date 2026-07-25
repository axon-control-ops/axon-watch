# Follow-ups closed / planned (2026-07-25)

Verified against local git on `feat/mission-control-holographic` at review time.
Merge-base with both parked branches: `d219c69`. Neither tip is an ancestor of HEAD.

| Item | Status on this branch |
|---|---|
| 4 — Phase 1 reliability | **Closed as deferred** (do not merge here) |
| 5 — Parked later-phase | **Closed as parked WIP** (do not merge / do not claim shipped) |
| 6 — Cursor parity | **Open as separate project** — see plan below |

---

## 4. What `feat/vaxon-phase1-reliability` actually is

**Plain language:** a side branch with a “hands-free desktop voice reliability” slice
(commits `6a2e40e`, `96ec10a`). It is **not** on `feat/mission-control-holographic`.

**What it contains (from that branch, not from HEAD):**

- Hands-free loop / converse submit extraction, voice-loop diagnostics, quiet-hours tests
- Settings field splits for hands-free / voice tuning
- Docs only on that branch: `docs/VAXON_DESKTOP_VOICE_RELIABILITY_CHECKLIST.md`,
  `docs/VAXON_WAKE_WORD_ENGINE_SELECTION.md`
- Checklist still has **unchecked** operator soak rows (30‑minute packaged Tauri). Automated
  prove harness is not the same as soak sign-off.

**Why it is not merged into this branch:**

- `git merge-tree` against current HEAD shows **multiple real conflicts** (e.g.
  `KairoVoiceDeckPanel.vue`, brain-galaxy orb hosts, `kairo_conversation` / shared-types /
  package-lock, settings forms).
- Overlapping files also exist with holographic voice/HUD work that landed after the
  merge-base — a blind merge would not be a clean “drop in.”

**Close decision for this train:** leave Phase 1 on its branch. Re-open only as a
**dedicated integration PR** (prefer into `dev`) after:

1. Conflict resolution against current tip  
2. `prove:desktop:voice` (or equivalent) green on the target host  
3. Human soak checklist rows filled with operator + date  
4. Fast Gate green on the integration commit  

Until then: **no continuous-reliability product claim** from Phase 1.

---

## 5. What `feat/parked-later-phase` actually is

**Plain language:** a parking branch (`d2f91b7`) for work that is **scaffolded but not
evidenced**. It is also **not** on HEAD.

**What it parks (verified on that branch):**

| Area | Reality on the branch |
|---|---|
| Wake-word | Engine interface + `browser-energy-wake-word-engine` interim; not a proven openwakeword default |
| Streaming STT | `DeferredStreamingSttAdapter` — explicit placeholder returning null finals |
| Android | App shell + FGS stub; `ANDROID_BACKGROUND_WAKE_EVIDENCE.md` checkboxes still empty |
| Device enrollment | Control-plane routes/store + tests on that branch |
| Mission memory | Control-plane module + tests on that branch |

Phase 1 and parked **share some wake-word / duplex / mission_memory paths** — they are not
independent clean stacks. Merging both without a sequenced plan will double-conflict.

**Close decision for this train:** keep the branch; **do not merge**; **do not describe any
of the above as shipped**. Promote only per-feature when that feature’s evidence row is
filled (see table in the parked Android evidence doc and wake-word selection doc on the
branch).

---

## 6. Cursor IDE parity — proper plan (not done)

See [`docs/planning/CURSOR_IDE_PARITY_PLAN.md`](../planning/CURSOR_IDE_PARITY_PLAN.md).

**Honest scope of current holographic IDE work:** Cursor-*inspired* Monaco theme, CSV
Table/Raw, minimap option tweaks, typed tab badges, left-rail agent card. That is
**stylistic alignment**, not Cursor product parity.
