# Desktop local wake-word engine selection (OP-C6)

Evidence-first spike notes. Do **not** ship a proprietary access-key dependency as default.

| Engine | License | Custom “VAXON” | WebKitGTK | Notes |
| --- | --- | --- | --- | --- |
| openwakeword WASM | Apache-2.0 | Yes (train/export) | TBD soak | Preferred open path once packaged false-wake/CPU evidence lands |
| Porcupine | Proprietary | Yes | TBD | Optional adapter only — never default |
| browser-energy-gate | Apache-2.0 (Axon-X) | No (energy + transcript gate) | Yes | **Current interim default** |

## Consent / privacy gates

- `wake_word_listening_consent` must be true before arming
- `wake_word_listening_enabled` is forced off without consent
- Privacy mode immediately stops capture and clears the local ring buffer
- Pre-wake audio never uploads; cloud/browser STT starts only after wake or follow-up window

## Gate before promoting openwakeword to default

Record on packaged Tauri:

- false-wake / hour on TV/music + ambient office corpus
- miss rate for near/far field “VAXON”
- CPU % while armed
- sleep/reopen survival

Until that evidence exists, `selectDefaultWakeWordEngineId()` returns `browser-energy-gate`.
