# Browser-Only Startup Contract

> Superseded by [`DUAL_RUNTIME_STARTUP_CONTRACT.md`](./DUAL_RUNTIME_STARTUP_CONTRACT.md).
> Browser `:4173` remains the **verified** operator path. Desktop is a scaffold.

## Verified browser flow

1. `./scripts/dev/up.sh` starts control-plane, axon-watch, and console-web
2. Console loads at `http://127.0.0.1:4173`
3. `BootWakeOverlay` completes and sets session key `axon-x-boot-complete`
4. `/api/readiness` reports deployment mode and state paths

## Desktop status

Desktop deferral: native desktop remains a scaffold; browser-only startup is the verified operator path until dual-runtime readiness is proven.

- Scaffold: `apps/console-desktop`
- Host APIs: `/api/host/*`
- Capability detection: `apps/console-web/src/lib/desktop-capability.ts`
- Honest rollout flags: `config/vaxon-desktop-flags.json`

## Verification

```bash
npm run verify:test8
npm run verify:parity-d6
npm run verify:host-context
```
