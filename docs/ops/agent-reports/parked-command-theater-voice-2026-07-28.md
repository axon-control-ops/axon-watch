# PARKED — Command Theater / stand-up voice polish (2026-07-28)

**Status: NOT DONE.** Do not treat stand-up / Mission Control theater voice as finished.

## What landed (partial)

- Theater turns route through Mission Control delivery (`deliverSpokenOperatorAlert` → Azure queue).
- Barge-in aborts in-flight Azure TTS and skips browser fallback for interrupted jobs.
- Display polish: VAXON (not Vekson) on MC transcript; shell-dump scrub on Lead cards; wider pulse labels.
- Debug ingest instrumentation removed from this tree.

## Still open (resume here)

1. **Prove Azure for every theater turn** — last live run still fell to browser when agent stream owned the lane; barge-in abort needs operator confirmation after a hard refresh.
2. **Agent-stream mute while theater is open** — ensure live thinking / progress narration cannot re-enter mid stand-up.
3. **Multi-agent neural parity** — Mira/Jules/Reed/etc. should sound as crisp as MC VAXON (Azure), not browser TTS.
4. **Lead card copy quality** — keep scrubbing terminal laundry; tighten spoken lines without over-truncating.
5. **End-to-end soak** — REPORT → full stand-up → directive execute with voice + panels locked.

## Branch context

Work lives on `feat/mission-control-holographic`. Park and continue later; do not claim shipped until the open list above has receipts.
