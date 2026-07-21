# Dual-Runtime Startup Contract

## Decision

Axon-X supports a **verified browser** operator path and a **scaffolded desktop** path:

1. **Browser** (verified default): `http://127.0.0.1:4173`
2. **Desktop (Tauri 2 scaffold)**: `apps/console-desktop` — not yet verified to build/run on every host

Desktop-only controls must remain gated behind `detectDesktopCapabilities()` /
`window.__AXON_DESKTOP__`. Dead controls must not appear in browser mode.

## Verified browser flow

1. `./scripts/dev/up.sh` starts control-plane, axon-watch, and console-web
2. Console loads at `http://127.0.0.1:4173`
3. Capability detection reports `runtime: browser`
4. Host APIs and reminders work without a native shell (ingest/read/pause)

## Desktop flow (scaffold status)

Implemented in-tree:

- Tauri 2 project + tray hide-on-close code
- Narrow Rust commands: bootstrap, snapshot stub, action evaluate, snapshot POST
- Control-plane `/api/host/*` policy, receipts, artifacts, reminders

Not yet complete / not verified here:

- Successful `tauri build` / `tauri dev` (needs WebKitGTK + pkg-config + npm deps)
- Real host sensors (windows/media/file watch/thumbnails)
- Signed pairing / keyring identity
- Deep links, autostart, compact HUD window
- Playwright desktop E2E and visual/motion regression suites

## Capability matrix (honest)

| Capability | Browser | Desktop scaffold |
|---|---|---|
| Briefing / Galaxy | yes | yes (same UI) |
| Due reminders | yes | yes |
| Host APIs | yes | yes |
| Local sensors | no | stub identity snapshot only |
| Open/reveal path | UI gated off | policy + receipt; OS open not fully wired |
| Media control | no | flagged false |
| Pause awareness | yes | yes |

See `config/vaxon-desktop-flags.json` for rollout honesty flags.

## Privacy

- Metadata-first records; content/thumbnails must not be logged by control-plane
- `POST /api/host/privacy/pause` pauses ingest
- Retention prune runs on snapshot ingest (`retention_days`, default 14)
- Deny by default: shell, keystroke injection, camera/mic, secrets, home crawl, external upload

## Verification (what actually passes today)

```bash
npm run verify:host-context
npm run test -w @axon-watch/console-web -- \
  src/lib/desktop-capability.test.ts \
  src/features/host-context/motion-orchestrator.test.ts
```

Tauri/Rust tests require:

```bash
sudo apt-get install -y pkg-config libwebkit2gtk-4.1-dev \
  libayatana-appindicator3-dev librsvg2-dev
npm install
cd apps/console-desktop/src-tauri && cargo test
```

## References

- `config/vaxon-desktop-flags.json`
- `apps/console-desktop/README.md`
- `docs/BROWSER_ONLY_STARTUP_CONTRACT.md` (superseded pointer)
- `scripts/dev/up.sh`
