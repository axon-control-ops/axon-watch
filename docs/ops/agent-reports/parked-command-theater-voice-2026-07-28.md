# PARKED — Command Theater / stand-up voice polish (2026-07-28)

**Status: NOT DONE.** Do not treat stand-up / Mission Control theater voice as finished.

## Critical correction (2026-08-04)

Prior agent claims overstated ship-readiness. Verified gaps:

- Theater was routed onto the Mission Control *delivery hop*, but the last instrumented live stand-up still reported **`channel: "browser"`** for theater turns — Azure neural parity was **not** proven end-to-end.
- Barge-in abort / playback-generation fixes were implemented from log evidence, then **debug instrumentation was removed before a successful post-fix Azure verification run**.
- Display polish (VAXON transcript mapping, shell scrub, wider pulse CSS) landed in code; operator visual confirmation after instrumentation removal was incomplete.
- Commit/push of that polish pack was requested earlier but **must not be assumed done** without checking the active branch tip.

## What landed (partial — code present, soak incomplete)

- Theater turns call `deliverSpokenOperatorAlert` → `speakKairoLine` (MC path), with Voice Deck bypass for employee voices.
- Barge-in aborts in-flight Azure TTS and skips browser fallback when interrupted.
- Display helpers: VAXON (not Vekson) on MC transcript; shell-dump scrub on Lead cards; wider pulse labels.
- Debug ingest instrumentation removed from the tree.

## Still open (resume here)

1. **Prove Azure for every theater turn** — last live evidence was browser fallback; need a clean soak after barge-in abort.
2. **Agent-stream mute while theater is open** — ensure live thinking / progress narration cannot re-enter mid stand-up.
3. **Multi-agent neural parity** — Mira/Jules/Reed/etc. should match MC VAXON Azure quality.
4. **Lead card copy quality** — keep scrubbing terminal laundry; tighten spoken lines without over-truncating.
5. **End-to-end soak** — REPORT → full stand-up → directive execute with voice + panels locked.

## Branch context

Originally tracked on `feat/mission-control-holographic`. Confirm current branch before resuming; do not claim shipped until the open list has receipts.
