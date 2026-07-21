# VAXON desktop package verification (2026-07-21)

## Automated gate (`npm run verify:desktop`)

**Result: PASS** (re-confirmed 2026-07-21 ~21:39 after launch-path fix)

- Frontend desktop unit tests: 6 files / 19 tests
- Python host + desktop session tests: 10 tests
- Rust desktop unit tests: 5 tests (includes `packaged_runtime_honors_explicit_env_flag`)
- Deb artifact:
  - Path: `apps/console-desktop/src-tauri/target/release/bundle/deb/VAXON_0.1.0_amd64.deb`
  - Size: ~59 MB (`61812638` bytes)
  - Contains `usr/bin/axon-console-desktop`
  - Contains `usr/bin/axon-watch-sidecar`
  - Contains `usr/bin/axon-control-plane-sidecar`
  - Contains `usr/lib/VAXON/resources/console-web-dist/index.html`

## Critical launch-path fix (2026-07-21 evening)

Earlier packaged installs could skip sidecar spawn because `VAXON.desktop` only
runs `Exec=axon-console-desktop` and does **not** set `AXON_DESKTOP_PACKAGED=1`.

`apps/console-desktop/src-tauri/src/runtime.rs` now exports `is_packaged_runtime()`
which returns true when:

- `AXON_DESKTOP_PACKAGED=1` / `AXON_DESKTOP_SPAWN_SIDECARS=1` / `AXON_WATCH_CONSOLE_DIST` is set, **or**
- both sidecar binaries are found beside the executable (FHS `/usr/bin/*-sidecar`), **or**
- the executable path is under `/usr/bin/axon-console-desktop` or `/usr/lib/VAXON/`

`lib.rs` uses that helper to start sidecars and navigate to `:8787`.

## Clean-machine install (container)

**Result: PASS** — see [Clean Debian/Kali container install](#clean-debiankali-container-install-2026-07-21t2004z) below.

Harness: `scripts/desktop/clean-install-prove.sh` (default image `kalilinux/kali-rolling`; frozen sidecars need **glibc ≥ 2.42**, so Bookworm/Ubuntu 24.04 images fail).

Still open before claiming a fully proven clean-machine *GUI* product:

1. Full GTK/Tauri window session on a clean machine (tray reopen, Galaxy panel resize).
2. Human finger unlock of Azure speech inside the packaged Tauri window (harness gesture proof is recorded separately).
3. Cursor-backed agent execution still requires a separately authenticated Cursor CLI on the host.

## External prerequisites (honest)

- Azure Speech credentials must be entered/unlocked for non-robotic TTS.
- Cursor CLI auth is separate from the desktop package.
- Local development without frozen sidecars requires `AXON_DESKTOP_ALLOW_PYTHON_FALLBACK=1` (packaged builds do not use that fallback).
- Current frozen sidecars require **glibc ≥ 2.42** (Kali rolling / newer Debian); older LTS bases are not supported without rebuilding sidecars on that base.

## Clean Debian/Kali container install (2026-07-21T20:04Z)

**Result: PASS**

- Image: `kalilinux/kali-rolling:latest` (no axon-watch checkout / Node / host venv inside container)
- Installed: `VAXON_0.1.0_amd64.deb`
- Binaries present: `axon-console-desktop`, both sidecars, `console-web-dist/index.html`
- Sidecars started; Control Plane `/api/health` responded:

```json
{
    "service": "control-plane",
    "status": "ok",
    "mode": "bootstrap",
    "boot_id": "0651be03b22d4c6c88946267c89124b2"
}
```

Note: full GTK/WebKitGTK GUI launch inside the container was not required for this gate;
this proves the packaged binaries run without the development checkout.

## Packaged WebKitGTK Azure voice gesture (2026-07-21T20:10Z)

**Result: PASS**

- Live Azure TTS via `http://127.0.0.1:4173/api/kairo/tts` (`provider=azure`, voice bytes present)
- System **WebKitGTK 4.1** (PyGObject / system `python3`) with `media-playback-requires-user-gesture=true`
- Harness unlock click (GDK button + JS fallback) then Azure MP3 `file://` playback
- Assertion: `engine=azure`

Harness: `scripts/desktop/prove-packaged-voice.sh`

Honesty note: unlock click is injected by the harness (not a human finger). This still proves
WebKitGTK on this host can unlock audio and play a live Azure TTS payload — same engine family
as packaged Tauri on Linux. It is not a full Tauri window E2E of the in-app unlock UX.
