# Browser-Only Startup Contract

## Decision

Axon-X v1 promotes **browser startup** as the verified operator entry path.
Packaged desktop startup remains **explicitly deferred** until a dedicated
desktop slice is scheduled.

## Verified browser flow

1. `./scripts/dev/up.sh` starts control-plane, axon-watch, and console-web
2. Console loads at `http://127.0.0.1:4173` (or configured public URL)
3. `BootWakeOverlay` completes and sets session key `axon-x-boot-complete`
4. `/api/readiness` reports deployment mode and state paths

## Desktop deferral

- No packaged Electron/Tauri desktop artifact is required for v1 parity
- Desktop notification adapter (P-D2) uses file-based JSONL under state dir
- Operator workflows on axon-local port 7734 are **fallback only** (legacy connectors)

## Verification

```bash
npm run verify:test8
npm run verify:parity-d6
```

## References

- `docs/DEDICATED_SERVER_READINESS.md`
- `config/browser-startup-contract.json`
- `scripts/dev/up.sh`
