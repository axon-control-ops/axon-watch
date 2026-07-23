# VAXON desktop voice reliability checklist

Updated by `scripts/desktop/prove-packaged-voice.sh` and operator soak notes.

## Automated portion (this host)

- [x] Azure TTS available from live stack (`provider=azure`, voice bytes present) — proven 2026-07-22 via prove harness
- [x] WebKitGTK 4.1 unlock gesture + Azure MP3 playback — `engine=azure` PASS 2026-07-22

## Operator soak (30 minutes on packaged Tauri — still required)

- [ ] Mic permission granted; privacy kill-switch stops capture immediately
- [ ] Session-ready speech: unlock → one spoken greeting or status line
- [ ] One hands-free turn: speak → reply → follow-up window reopens
- [ ] Barge-in: say stop / wake while TTS plays; speech stops and listen resumes
- [ ] Converse watchdog: deep turn either answers or times out with spoken fallback (no stuck thinking)
- [ ] Runtime-unavailable fallback does not latch pending/thinking
- [ ] No restart storm (ambient end backs off; failures use exponential backoff)
- [ ] Sleep/reopen: after wake, hands-free re-arms without duplicate replies

## Diagnostics

Use `listVoiceLoopDiagnostics()` / `summarizeVoiceLoopDiagnostics()` in the
console (state, restart reason, latency, timeout/error counts — never audio/transcripts).

## Honesty

Automated harness proves unlock+TTS engine only. Soak rows require a human operator
on packaged Tauri before claiming continuous desktop reliability. Do not promote
wake-word or Android background claims until soak passes.
