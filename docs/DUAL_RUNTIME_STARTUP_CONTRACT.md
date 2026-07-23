# Dual-Runtime Startup Contract

## Decision

Axon-X supports a **verified browser** operator path and a **packaged desktop** path:

1. **Browser** (verified default for development): `http://127.0.0.1:4173`
2. **Desktop (Tauri 2)**: `apps/console-desktop` — builds a Debian `.deb` with SPA + frozen Watch/Control Plane sidecars

Desktop-only controls must remain gated behind `detectDesktopCapabilities()` /
`window.__AXON_DESKTOP__`. Dead controls must not appear in browser mode.

## Verified browser flow

1. `./scripts/dev/up.sh` starts control-plane, axon-watch, and console-web
2. Console loads at `http://127.0.0.1:4173`
3. Capability detection reports `runtime: browser`
4. Host APIs and reminders work without a native shell (ingest/read/pause)

## Desktop flow

Packaged startup (no special env required on the `.deb` Exec line):

1. `axon-console-desktop` detects packaged runtime via sidecar binaries beside the
   exe and/or FHS install paths (`is_packaged_runtime()`), or explicit env flags
2. Creates XDG config/state if missing
3. Starts `axon-watch-sidecar` then `axon-control-plane-sidecar` (no Python/repo fallback unless `AXON_DESKTOP_ALLOW_PYTHON_FALLBACK=1`)
4. Waits for Control Plane health on `127.0.0.1:8787`
5. Bootstraps an HttpOnly desktop session cookie
6. Navigates the webview to the Control Plane origin (SPA via `AXON_WATCH_CONSOLE_DIST` / packaged `console-web-dist`)

Local development without frozen binaries may set `AXON_DESKTOP_ALLOW_PYTHON_FALLBACK=1`.

Still incomplete / host-dependent:

- Full clean-machine *GUI* Tauri session (tray / Galaxy resize) — container clean-install of sidecars+health is recorded in `docs/VAXON_DESKTOP_VERIFY_EVIDENCE.md`
- Real host sensors (windows/media/file watch/thumbnails)
- Signed pairing / keyring identity
- Deep links, autostart, compact HUD window
- Playwright desktop E2E and visual/motion regression suites
- Human-finger Azure voice unlock inside packaged Tauri (in-app unlock banner + queue-until-unlock shipped; WebKitGTK harness gesture + live Azure TTS is recorded; full packaged-window E2E still manual)
- JARVIS proactive duplex (speak→listen follow-up) is implemented in console; enable via Settings → JARVIS duplex

Prove harnesses: `npm run prove:desktop:clean-install`, `npm run prove:desktop:voice`

## Capability matrix (honest)

| Capability | Browser | Desktop |
|---|---|---|
| Briefing / Galaxy | yes | yes (same UI) |
| Due reminders | yes | yes |
| Host APIs | yes | yes |
| Local sensors | no | stub identity snapshot only |
| Open/reveal path | UI gated off | policy + receipt; OS open not fully wired |
| Media control | no | flagged false |
| Pause awareness | yes | yes |
| Frozen sidecars in `.deb` | n/a | yes (verify:desktop asserts) |

See `config/vaxon-desktop-flags.json` for rollout honesty flags.

## Privacy

- Metadata-first records; content/thumbnails must not be logged by control-plane
- `POST /api/host/privacy/pause` pauses ingest
- Retention prune runs on snapshot ingest (`retention_days`, default 14)
- Deny by default: shell, keystroke injection, camera/mic, secrets, home crawl, external upload

## Verification (what actually passes today)

```bash
npm run verify:host-context
npm run verify:desktop
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
- `docs/VAXON_DESKTOP_VERIFY_EVIDENCE.md`
- `docs/BROWSER_ONLY_STARTUP_CONTRACT.md` (superseded pointer)
- `scripts/dev/up.sh`
