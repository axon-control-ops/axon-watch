## VAXON Desktop

Packaged Linux desktop shell (Tauri 2) with frozen Watch + Control Plane sidecars on loopback `:8787`.

### Verify

```bash
npm run verify:desktop
npm run prove:desktop:clean-install
npm run prove:desktop:voice
```

Evidence: [`docs/VAXON_DESKTOP_VERIFY_EVIDENCE.md`](../VAXON_DESKTOP_VERIFY_EVIDENCE.md).

### Install

```bash
npm run build:desktop:linux
sudo apt-get install -y ./apps/console-desktop/src-tauri/target/release/bundle/deb/VAXON_*.deb
```

Requires Debian-family x86_64 + WebKitGTK 4.1; current sidecars need **glibc ≥ 2.42**. Full first-run / tray / update notes: [`docs/VAXON_DESKTOP_VERIFY_EVIDENCE.md`](../VAXON_DESKTOP_VERIFY_EVIDENCE.md) and [`docs/DUAL_RUNTIME_STARTUP_CONTRACT.md`](../DUAL_RUNTIME_STARTUP_CONTRACT.md).
