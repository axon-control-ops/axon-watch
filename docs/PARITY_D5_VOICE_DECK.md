# P-D5 — Vue Voice Deck

## Deliverable

Register a Vue voice-deck handler at console boot so high-value spoken alerts
route through `voice_deck` before browser TTS fallback.

## v1 scope

### In scope

- `apps/console-web/src/features/voice-deck/` module
- `registerVoiceDeckOnBoot()` wired in `App.vue`
- Handler uses `registerVoiceDeckSpokenAlertHandler` → channel `voice_deck`
- Vitest coverage for deck handler + boot registration

### Acceptable v1 degradation

- Voice deck uses browser `SpeechSynthesis` (same engine as fallback)
- No separate Alpine polling layer

### Out of scope

- OS-native voice subsystem integration
- Push-to-talk conversation deck

## Gate

```bash
npm run verify:parity-d5
```

## Promotion

On gate pass, update `config/parity-closure-order.json` → `P-D5.status = done`,
`next_slice = P-D6`.
